"""Exploratory V15 LiDAR-to-pose chain, without localization scoring.

Reuses the frozen Phase-2 registration, Phase-4 diagnostics and
FixedCleanBackbone mathematical pose-composition implementation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import signal
import sys
from pathlib import Path

import numpy as np
import scipy

from trust_robot.clean_backbone import (
    CleanBackboneConfig,
    FixedCleanBackbone,
    PoseSE3,
    RelativePoseIncrement,
)
from trust_robot.diagnostics import (
    extract_lidar_registration_diagnostics,
)
from trust_robot.lidar_frontend import (
    register_current_scan_to_previous,
)
from trust_robot.isaacsim_v15_diagnostic_bridge import (
    require_hash,
)

SCHEMA = "TRUST_ROBOT_ISAACSIM_V15_EXPLORATORY_ODOMETRY_CHAIN_V1"
BODY_FRAME = "V15_GENERIC_LIDAR_UNVERIFIED_FRAME"
ODOM_FRAME = "V15_ARBITRARY_LIDAR_ODOMETRY"
SOURCE = "V15_FROZEN_LIDAR_PAIRWISE_REGISTRATION"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def json_line(value):
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ) + "\n"
    ).encode("utf-8")


def read_jsonl(path):
    if not path.is_file() or path.is_symlink():
        raise ValueError("Missing/unsafe JSONL")
    return [
        json.loads(line)
        for line in path.read_text().splitlines()
        if line.strip()
    ]


def logical_time_ns(frame):
    """Simulation read-step time; NOT physical sensor measurement time."""
    value = float(frame["lidar_read_step_time_s"])
    if not math.isfinite(value) or value < 0.0:
        raise ValueError("Invalid simulation read-step time")
    return int(round(value * 1_000_000_000))


def register_bounded(previous, current, seconds=6.0):
    if seconds <= 0.0:
        raise ValueError("Nonpositive registration budget")

    def timeout_handler(_signal, _frame):
        raise TimeoutError("Registration time budget exceeded")

    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.setitimer(signal.ITIMER_REAL, seconds)

    try:
        return register_current_scan_to_previous(previous, current)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0.0)
        signal.signal(signal.SIGALRM, old_handler)


def load_clouds(data, evidence, frames):
    clouds = []
    for i, frame in enumerate(frames, 1):
        name = f"frames_v15/lidar_{i:03d}.npy"
        if frame["lidar_file"] != name:
            raise ValueError("Unexpected LiDAR file path")

        path = data / name
        require_hash(path, evidence["frame_files"][name]["sha256"])
        xyz = np.load(path, allow_pickle=False)

        if (
            xyz.dtype != np.float32
            or xyz.ndim != 2
            or xyz.shape[1] != 3
            or len(xyz) < 3
            or not np.isfinite(xyz).all()
        ):
            raise ValueError("Invalid recorded LiDAR scan")

        clouds.append(xyz)

    return clouds


def run_condition(condition, frames, clouds, prior_pairs):
    if condition not in ("clean", "intervention"):
        raise ValueError("Unknown condition")

    if len(frames) != 6 or len(clouds) != 6:
        raise ValueError("Unexpected scan count")

    times = [logical_time_ns(f) for f in frames]
    if any(b <= a for a, b in zip(times, times[1:])):
        raise ValueError("Nonmonotonic simulation time")

    config = CleanBackboneConfig(
        world_frame_id=ODOM_FRAME,
        body_frame_id=BODY_FRAME,
        relative_pose_source_id=SOURCE,
        initial_timestamp_ns=times[0],
        initial_pose_world_T_body=PoseSE3.identity(),
    )
    backbone = FixedCleanBackbone(config)

    records = [{
        "condition": condition,
        "frame_index": 1,
        "status": "ARBITRARY_ODOMETRY_ORIGIN",
        "simulation_read_step_time_ns": times[0],
        "pose": backbone.state.pose_world_T_body.to_dict(),
        "registration_features": None,
        "reference_pose": None,
    }]

    differences = 0

    for i in range(1, 6):
        previous = clouds[i-1]
        current = clouds[i]

        if condition == "intervention" and i == 2:
            current = current[::2].copy()

        if condition == "intervention" and i == 3:
            previous = previous[::2].copy()

        result = register_bounded(previous, current)
        diagnostics = extract_lidar_registration_diagnostics(
            result.diagnostics
        )

        features = {
            feature.name: feature.value
            for feature in diagnostics.features
        }

        old = prior_pairs[(condition, i)]
        previous_features = old["registration"]["features"]

        if previous_features is None:
            raise ValueError("Previously unavailable registration")

        if set(features) != set(previous_features):
            raise ValueError("Frozen diagnostic feature mismatch")

        if (
            features["source_point_count"]
            != old["scan_points_current"]
            or features["target_point_count"]
            != old["scan_points_previous"]
        ):
            raise ValueError("Registration point-count mismatch")

        # Numeric differences are reported, never silently treated
        # as exact cross-environment agreement.
        if any(
            not math.isclose(
                float(features[key]),
                float(previous_features[key]),
                rel_tol=1e-7,
                abs_tol=1e-8,
            )
            for key in features
        ):
            differences += 1

        increment = RelativePoseIncrement(
            timestamp_ns=times[i],
            body_frame_id=BODY_FRAME,
            source_id=SOURCE,
            delta_prev_body_T_current_body=(
                result.previous_lidar_T_current_lidar
            ),
        )

        state = backbone.apply(increment)

        records.append({
            "condition": condition,
            "frame_index": i + 1,
            "status": "EXPLORATORY_LIDAR_POSE_CHAIN",
            "simulation_read_step_time_ns": times[i],
            "relative_pose": (
                increment.delta_prev_body_T_current_body.to_dict()
            ),
            "pose": state.pose_world_T_body.to_dict(),
            "registration_features": features,
            "reference_pose": None,
        })

    assert len(records) == 6

    return records, differences


def execute(data, previous_dir, evidence_file):
    evidence = json.loads(evidence_file.read_text())

    for key, filename in (
        ("summary_sha256", "summary_v1.json"),
        ("capture_index_sha256", "capture_index_v15.json"),
        ("imu_series_sha256", "imu_v1.jsonl"),
        ("pose_series_sha256", "base_pose_series_v15.jsonl"),
    ):
        require_hash(data / filename, evidence[key])

    summary = json.loads((data / "summary_v1.json").read_text())
    if not (
        summary["data_origin"] == "SYNTHETIC"
        and summary["independent_ground_truth_verified"] is False
        and summary["cross_sensor_synchronization_verified"] is False
        and summary["calibration_verified"] is False
    ):
        raise ValueError("Unexpected scientific readiness state")

    frames = json.loads(
        (data / "capture_index_v15.json").read_text()
    )

    if [f["step"] for f in frames] != [31, 41, 51, 61, 71, 81]:
        raise ValueError("Unexpected frame progression")

    if not all(
        f["acquisition_timing_verified"] is False
        and f["cross_sensor_synchronization_verified"] is False
        for f in frames
    ):
        raise ValueError("Unexpected timing provenance")

    prior_manifest_path = (
        previous_dir / "qualification_manifest_v1.json"
    )
    prior_rows_path = previous_dir / "paired_registration_v1.jsonl"

    if (
        not prior_manifest_path.is_file()
        or prior_manifest_path.is_symlink()
    ):
        raise ValueError("Missing registration qualification")

    prior_manifest = json.loads(prior_manifest_path.read_text())
    require_hash(
        prior_rows_path,
        prior_manifest["paired_records_sha256"],
    )

    if (
        prior_manifest["attempted_registration_pairs"] != 10
        or prior_manifest["registration_features_available_count"] != 10
        or prior_manifest["source_evidence_sha256"] != sha(evidence_file)
    ):
        raise ValueError("Prior milestone lineage mismatch")

    prior_records = read_jsonl(prior_rows_path)
    prior_pairs = {
        (row["condition"], row["previous_frame_index"]): row
        for row in prior_records
    }
    if len(prior_pairs) != 10:
        raise ValueError("Incomplete previous registration pairs")

    clouds = load_clouds(data, evidence, frames)

    clean, difference_clean = run_condition(
        "clean", frames, clouds, prior_pairs
    )
    altered, difference_altered = run_condition(
        "intervention", frames, clouds, prior_pairs
    )

    return {
        "clean": clean,
        "intervention": altered,
    }, {
        "cross_environment_feature_difference_pairs": (
            difference_clean + difference_altered
        ),
        "prior_registration_manifest_sha256": sha(prior_manifest_path),
    }


def run(data, previous_dir, evidence_file, destination):
    if destination.exists() or destination.is_symlink():
        raise ValueError("Output exists")

    if (
        not destination.parent.is_dir()
        or destination.parent.is_symlink()
    ):
        raise ValueError("Unsafe output parent")

    if not evidence_file.is_file() or evidence_file.is_symlink():
        raise ValueError("Unsafe compact evidence")

    first, provenance = execute(data, previous_dir, evidence_file)
    second, again_provenance = execute(
        data, previous_dir, evidence_file
    )

    if provenance != again_provenance:
        raise ValueError("Non-deterministic provenance")

    artifacts = {}

    for condition in ("clean", "intervention"):
        first_bytes = b"".join(
            json_line(row) for row in first[condition]
        )
        second_bytes = b"".join(
            json_line(row) for row in second[condition]
        )
        if first_bytes != second_bytes:
            raise ValueError("Non-deterministic pose chain")
        artifacts[f"{condition}_pose_chain.jsonl"] = first_bytes

    result = {
        "schema": SCHEMA,
        "data_origin": "ISAAC_SIM_SYNTHETIC",
        "frozen_phase2_registration_reused": True,
        "frozen_phase4_diagnostics_reused": True,
        "fixed_clean_backbone_pose_chain_reused": True,
        "fixed_lag_nonlinear_optimizer_executed": False,
        "pose_chains": {
            "clean": len(first["clean"]),
            "intervention": len(first["intervention"]),
        },
        "registration_pairs_per_condition": 5,
        "intervention": "FRAME_3_EVERY_OTHER_LIDAR_POINT",
        "previous_milestone_sha256": (
            provenance["prior_registration_manifest_sha256"]
        ),
        "compact_evidence_sha256": sha(evidence_file),
        "numeric_environment": {
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "scipy": scipy.__version__,
        },
        "cross_environment_feature_difference_pairs": (
            provenance["cross_environment_feature_difference_pairs"]
        ),
        "derived_file_sha256": {
            name: hashlib.sha256(blob).hexdigest()
            for name, blob in sorted(artifacts.items())
        },
        "repeat_derivation_identical": True,
        "pose_frame_independently_calibrated": False,
        "physical_capture_synchronization_verified": False,
        "independent_ground_truth_used": False,
        "ate_rpe_computed": False,
        "health_probabilities_computed": False,
        "factor_conditioning_executed": False,
        "physical_robot_tested": False,
    }

    destination.mkdir(mode=0o700)

    for name, blob in artifacts.items():
        (destination / name).write_bytes(blob)

    (destination / "odometry_manifest_v1.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n"
    )
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("recording", type=Path)
    p.add_argument("registration_qualification", type=Path)
    p.add_argument("compact_evidence", type=Path)
    p.add_argument("output", type=Path)
    args = p.parse_args()

    result = run(
        args.recording,
        args.registration_qualification,
        args.compact_evidence,
        args.output,
    )
    print("CLEAN_POSES=", result["pose_chains"]["clean"])
    print(
        "INTERVENTION_POSES=",
        result["pose_chains"]["intervention"]
    )
    print(
        "CROSS_ENVIRONMENT_FEATURE_DIFFERENCES=",
        result["cross_environment_feature_difference_pairs"]
    )
    print("DETERMINISTIC_REPEAT=PASS")
    print("INDEPENDENT_GROUND_TRUTH=NOT_AVAILABLE")
    print("FIXED_LAG_OPTIMIZER=NOT_IMPLEMENTED_IN_THIS_RUN")
    print("V15_EXPLORATORY_ODOMETRY_CHAIN=PASS")


if __name__ == "__main__":
    main()
