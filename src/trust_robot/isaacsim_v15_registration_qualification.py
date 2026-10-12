"""Bounded offline registration on sparse V15 synthetic LiDAR scans.

Reuses frozen TRUST-ROBOT Phase-2 registration and Phase-4 extraction.
No physical timing, sensor-frame or localization-accuracy claim.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import signal
from pathlib import Path

import numpy as np

from trust_robot.lidar_frontend import (
    LidarFrontendError,
    register_current_scan_to_previous,
)
from trust_robot.diagnostics import (
    DiagnosticFeatureError,
    extract_lidar_registration_diagnostics,
)
from trust_robot.isaacsim_v15_diagnostic_bridge import (
    lidar_structure,
    require_hash,
)

SCHEMA = "TRUST_ROBOT_ISAACSIM_V15_REGISTRATION_QUALIFICATION_V1"
FEATURE_ORDER = (
    "source_point_count",
    "target_point_count",
    "fixed_point_iterations",
    "final_correspondence_count",
    "final_nearest_neighbor_rmse_m",
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def json_bytes(value):
    return (
        json.dumps(
            value, sort_keys=True, separators=(",", ":"),
            allow_nan=False,
        ) + "\n"
    ).encode()


def records(path):
    return [
        json.loads(x)
        for x in path.read_text().splitlines()
        if x.strip()
    ]


def timing_readiness(frames, poses, imu):
    if len(frames) != 6 or len(poses) != 90 or len(imu) != 90:
        raise ValueError("Unexpected V15 stream lengths")

    if [p["step"] for p in poses] != list(range(1, 91)):
        raise ValueError("Invalid USD pose-step sequence")

    if [p["step"] for p in imu] != list(range(1, 91)):
        raise ValueError("Invalid IMU step sequence")

    if [r["step"] for r in frames] != [31, 41, 51, 61, 71, 81]:
        raise ValueError("Invalid camera/LiDAR read-step sequence")

    for key in ("camera", "lidar"):
        times = [
            float(row[f"{key}_read_step_time_s"])
            for row in frames
        ]
        if not all(map(math.isfinite, times)):
            raise ValueError("Nonfinite simulation read-step times")
        if not all(b > a for a, b in zip(times, times[1:])):
            raise ValueError("Nonmonotonic simulation read-step times")

    ptimes = [
        float(p["simulation_step_time_s"])
        for p in poses
    ]
    if not all(map(math.isfinite, ptimes)):
        raise ValueError("Nonfinite pose-step times")
    if not all(b > a for a, b in zip(ptimes, ptimes[1:])):
        raise ValueError("Nonmonotonic pose-step times")

    if not all(
        p.get("pose_source") == "USD_COMPOSED_WORLD_TRANSFORM"
        and p.get("physics_pose_independently_verified") is False
        for p in poses
    ):
        raise ValueError("Unexpected pose provenance")

    if not all(
        r.get("timestamp_semantics_verified") is False
        for r in imu
    ):
        raise ValueError("Unexpected IMU timestamp provenance")

    if not all(
        r.get("acquisition_timing_verified") is False
        and r.get("cross_sensor_synchronization_verified") is False
        for r in frames
    ):
        raise ValueError("Unexpected capture timing provenance")

    matching = all(
        a["camera_read_step_time_s"] == a["lidar_read_step_time_s"]
        for a in frames
    )

    return {
        "read_step_order_monotonic": True,
        "usd_pose_step_order_monotonic": True,
        "same_step_camera_lidar_read_time_values_equal": matching,
        "same_step_read_time_values_prove_synchronization": False,
        "sensor_physical_capture_time_verified": False,
        "sensor_common_clock_verified": False,
        "extrinsic_calibration_independently_verified": False,
        "lidar_cloud_coordinate_frame_independently_verified": False,
        "usd_pose_independent_ground_truth": False,
        "fixed_lidar_imu_offset_estimated": False,
        "reference_to_estimator_association_verified": False,
    }


def load_scans(data, evidence, frames, bridge):
    scans = {"clean": [], "intervention": []}
    clean_rows = records(bridge / "clean_lidar.jsonl")
    altered_rows = records(bridge / "intervention_lidar.jsonl")

    if len(clean_rows) != 6 or len(altered_rows) != 6:
        raise ValueError("Unexpected prior LiDAR diagnostics")

    for i, row in enumerate(frames, 1):
        relative = f"frames_v15/lidar_{i:03d}.npy"
        if row["lidar_file"] != relative:
            raise ValueError("Unexpected LiDAR frame path")

        path = data / relative
        require_hash(path, evidence["frame_files"][relative]["sha256"])

        cloud = np.load(path, allow_pickle=False)
        clean = lidar_structure(cloud)

        if clean_rows[i-1]["features"]["point_count"] != clean["point_count"]:
            raise ValueError("Clean bridge point-count mismatch")

        altered = cloud[::2].copy() if i == 3 else cloud.copy()
        corrupt = lidar_structure(altered)

        if altered_rows[i-1]["features"]["point_count"] != corrupt["point_count"]:
            raise ValueError("Intervention bridge point-count mismatch")

        if clean_rows[i-1]["step"] != row["step"]:
            raise ValueError("Clean bridge step mismatch")
        if altered_rows[i-1]["step"] != row["step"]:
            raise ValueError("Intervention bridge step mismatch")

        scans["clean"].append(cloud)
        scans["intervention"].append(altered)

    return scans


def spatial_rank(xyz):
    centered = np.asarray(xyz, dtype=np.float64)
    centered = centered - centered.mean(axis=0)
    return int(np.linalg.matrix_rank(centered))


def bounded_registration(previous, current, limit_seconds=6.0):
    if limit_seconds <= 0:
        raise ValueError("Invalid registration time budget")

    def timeout_handler(_signum, _frame):
        raise TimeoutError("Registration diagnostic time limit")

    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.setitimer(signal.ITIMER_REAL, limit_seconds)
    try:
        result = register_current_scan_to_previous(
            previous, current
        )
        extracted = extract_lidar_registration_diagnostics(
            result.diagnostics
        )
        feature_map = {
            f.name: f.value
            for f in extracted.features
        }
        if tuple(feature_map) != FEATURE_ORDER:
            raise ValueError("Frozen LiDAR feature order changed")
        return {
            "status": "FROZEN_REGISTRATION_DIAGNOSTICS_AVAILABLE",
            "features": feature_map,
            "error_code": None,
            "registration_estimate_is_reference_truth": False,
        }
    except (LidarFrontendError, DiagnosticFeatureError,
            TimeoutError, np.linalg.LinAlgError) as exc:
        return {
            "status": "REGISTRATION_UNAVAILABLE",
            "features": None,
            "error_code": type(exc).__name__,
            "registration_estimate_is_reference_truth": False,
        }
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old_handler)


def pair_records(scans, frames):
    output = []
    for condition in ("clean", "intervention"):
        for i in range(1, 6):
            previous = scans[condition][i-1]
            current = scans[condition][i]
            result = bounded_registration(previous, current)

            output.append({
                "condition": condition,
                "previous_frame_index": i,
                "current_frame_index": i + 1,
                "previous_read_step": frames[i-1]["step"],
                "current_read_step": frames[i]["step"],
                "scan_points_previous": len(previous),
                "scan_points_current": len(current),
                "source_spatial_rank": spatial_rank(current),
                "target_spatial_rank": spatial_rank(previous),
                "spatial_rank_is_observability_proof": False,
                "registration": result,
                "sensor_frame_provenance": "UNVERIFIED",
                "physical_synchronization_verified": False,
                "data_origin": "ISAAC_SIM_SYNTHETIC",
            })

    return output


def run(data, bridge, evidence_file, destination):
    if destination.exists() or destination.is_symlink():
        raise ValueError("Output already exists")
    if not destination.parent.is_dir() or destination.parent.is_symlink():
        raise ValueError("Unsafe output parent")

    if not evidence_file.is_file() or evidence_file.is_symlink():
        raise ValueError("Missing compact evidence")

    evidence = json.loads(evidence_file.read_text())
    required = {
        "summary_sha256": "summary_v1.json",
        "capture_index_sha256": "capture_index_v15.json",
        "pose_series_sha256": "base_pose_series_v15.jsonl",
        "imu_series_sha256": "imu_v1.jsonl",
    }

    for key, filename in required.items():
        require_hash(data / filename, evidence[key])

    old_manifest_path = bridge / "bridge_manifest_v1.json"
    if not old_manifest_path.is_file() or old_manifest_path.is_symlink():
        raise ValueError("Missing prior bridge manifest")

    old_manifest = json.loads(old_manifest_path.read_text())
    if old_manifest["source_evidence_sha256"] != digest(evidence_file):
        raise ValueError("Prior bridge lineage mismatch")

    for filename, expected in old_manifest["generated_files_sha256"].items():
        require_hash(bridge / filename, expected)

    frames = json.loads((data / "capture_index_v15.json").read_text())
    poses = records(data / "base_pose_series_v15.jsonl")
    imu = records(data / "imu_v1.jsonl")

    readiness = timing_readiness(frames, poses, imu)
    scans = load_scans(data, evidence, frames, bridge)

    first = pair_records(scans, frames)
    second = pair_records(scans, frames)

    if [json_bytes(x) for x in first] != [json_bytes(x) for x in second]:
        raise ValueError("Registration diagnostic outputs not deterministic")

    serialized = b"".join(json_bytes(x) for x in first)

    available = sum(
        r["registration"]["features"] is not None
        for r in first
    )
    unavailable = len(first) - available

    manifest = {
        "schema": SCHEMA,
        "source_evidence_sha256": digest(evidence_file),
        "prior_bridge_manifest_sha256": digest(old_manifest_path),
        "data_origin": "ISAAC_SIM_SYNTHETIC",
        "paired_conditions": ["clean", "intervention"],
        "expected_scan_pairs_per_condition": 5,
        "attempted_registration_pairs": len(first),
        "registration_features_available_count": available,
        "registration_unavailable_count": unavailable,
        "frozen_phase2_registration_reused": True,
        "frozen_phase4_feature_extractor_reused": True,
        "physical_equivalence_to_m2dgr_verified": False,
        "diagnostic_rmse_is_localization_accuracy": False,
        "timing_calibration_readiness": readiness,
        "paired_records_sha256": hashlib.sha256(serialized).hexdigest(),
        "repeat_derivation_identical": True,
        "health_labels_generated": False,
        "health_classifier_trained": False,
        "independent_ground_truth_used": False,
        "localization_ate_rpe_computed": False,
    }

    destination.mkdir(mode=0o700)
    (destination / "paired_registration_v1.jsonl").write_bytes(serialized)
    (destination / "qualification_manifest_v1.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )

    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("recording", type=Path)
    parser.add_argument("prior_bridge", type=Path)
    parser.add_argument("compact_evidence", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()

    result = run(
        args.recording, args.prior_bridge,
        args.compact_evidence, args.destination,
    )

    print("REGISTRATION_PAIRS=", result["attempted_registration_pairs"])
    print(
        "FEATURE_PAIRS_AVAILABLE=",
        result["registration_features_available_count"]
    )
    print(
        "FEATURE_PAIRS_UNAVAILABLE=",
        result["registration_unavailable_count"]
    )
    print("TIMING_ORDER_CHARACTERIZATION=PASS")
    print("CROSS_SENSOR_PHYSICAL_SYNCHRONIZATION=UNVERIFIED")
    print("INDEPENDENT_EXTRINSIC_CALIBRATION=UNVERIFIED")
    print("DETERMINISTIC_REPEAT=PASS")
    print("V15_REGISTRATION_QUALIFICATION=PASS")


if __name__ == "__main__":
    main()
