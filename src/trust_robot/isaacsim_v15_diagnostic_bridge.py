"""Offline V15 synthetic diagnostics; not synchronization or health inference."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image
from trust_robot.se3_multimodal_feature_contract import (
    extract_camera_features_from_gray,
    extract_imu_features,
)

CAMERA_NAMES = (
    "gray_mean_intensity_8bit",
    "gray_std_intensity_8bit",
    "gray_mean_abs_neighbor_difference_8bit",
)
IMU_NAMES = (
    "angular_speed_norm_rad_s",
    "linear_acceleration_norm_m_s2",
)
SCHEMA = "TRUST_ROBOT_ISAACSIM_V15_OFFLINE_DIAGNOSTIC_BRIDGE_V1"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_regular(path: Path) -> None:
    if not path.is_file() or path.is_symlink():
        raise ValueError("Missing/unsafe input: " + path.name)


def require_hash(path: Path, expected: str) -> None:
    require_regular(path)
    if digest(path) != expected:
        raise ValueError("Modified recorded input: " + path.name)


def load_records(path: Path) -> list[dict]:
    require_regular(path)
    return [
        json.loads(line)
        for line in path.read_text().splitlines()
        if line.strip()
    ]


def camera_features(rgba: np.ndarray) -> dict[str, float]:
    if rgba.shape != (120, 160, 4) or rgba.dtype != np.uint8:
        raise ValueError("Expected uint8 120x160x4 camera capture")

    gray = np.asarray(
        Image.fromarray(rgba[:, :, :3], "RGB").convert("L")
    )
    values = extract_camera_features_from_gray(gray)
    return dict(zip(CAMERA_NAMES, map(float, values)))


def imu_features(record: dict) -> dict:
    angular = record.get("angular_velocity")
    linear = record.get("linear_acceleration")

    if angular is None or linear is None:
        return {
            "availability": "observed_absent",
            "features": None,
        }

    values = extract_imu_features(angular, linear)
    return {
        "availability": "observed_present",
        "features": dict(zip(IMU_NAMES, map(float, values))),
    }


def lidar_structure(xyz: np.ndarray) -> dict:
    if xyz.ndim != 2 or xyz.shape[1] != 3 or len(xyz) == 0:
        raise ValueError("Expected nonempty Nx3 LiDAR XYZ")

    if xyz.dtype != np.float32 or not np.isfinite(xyz).all():
        raise ValueError("Expected finite float32 LiDAR XYZ")

    return {
        "point_count": int(len(xyz)),
        "centroid_xyz_m": [
            float(x) for x in xyz.mean(axis=0, dtype=np.float64)
        ],
        "axis_span_xyz_m": [
            float(x) for x in
            np.ptp(xyz.astype(np.float64), axis=0)
        ],
        "contract": "SYNTHETIC_STRUCTURAL_ONLY_NOT_PHASE4_ICP",
    }


def canonical_line(record: dict) -> bytes:
    return (
        json.dumps(
            record,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ) + "\n"
    ).encode("utf-8")


def construct(
    data: Path,
    evidence: dict,
    intervention: bool,
) -> tuple[dict, dict]:
    summary = json.loads((data / "summary_v1.json").read_text())
    frames = json.loads((data / "capture_index_v15.json").read_text())
    imu = load_records(data / "imu_v1.jsonl")
    poses = load_records(data / "base_pose_series_v15.jsonl")

    if not (
        summary["data_origin"] == "SYNTHETIC"
        and summary["cross_sensor_synchronization_verified"] is False
        and summary["independent_ground_truth_verified"] is False
        and len(frames) == 6
        and len(imu) == 90
        and len(poses) == 90
    ):
        raise ValueError("Unexpected V15 scientific evidence state")

    if [r["step"] for r in poses] != list(range(1, 91)):
        raise ValueError("Unexpected pose step sequence")

    if [r["step"] for r in imu] != list(range(1, 91)):
        raise ValueError("Unexpected IMU step sequence")

    streams = {"camera": [], "lidar": [], "imu": []}
    applied = {
        "camera_blackout_frame": None,
        "lidar_half_sample_frame": None,
        "imu_accel_bias_step": None,
    }

    for i, row in enumerate(frames, 1):
        if row["step"] != 21 + 10 * i:
            raise ValueError("Unexpected frame step")

        if (
            row["cross_sensor_synchronization_verified"] is not False
            or row["acquisition_timing_verified"] is not False
        ):
            raise ValueError("Unexpected timing verification flag")

        for modality in ("camera", "lidar"):
            relative = f"frames_v15/{modality}_{i:03d}.npy"

            if row[f"{modality}_file"] != relative:
                raise ValueError("Unexpected frame path")

            path = data / relative
            require_hash(
                path,
                evidence["frame_files"][relative]["sha256"],
            )
            array = np.load(path, allow_pickle=False)

            if modality == "camera":
                if intervention and i == 3:
                    array = array.copy()
                    array[:, :, :3] = 0
                    applied["camera_blackout_frame"] = i
                features = camera_features(array)
            else:
                if intervention and i == 3:
                    array = array[::2].copy()
                    applied["lidar_half_sample_frame"] = i
                features = lidar_structure(array)

            streams[modality].append({
                "frame_index": i,
                "step": row["step"],
                "simulation_read_step_time_s": (
                    row[f"{modality}_read_step_time_s"]
                ),
                "timing_semantics": (
                    "UNVERIFIED_SIMULATION_READ_STEP_ONLY"
                ),
                "features": features,
                "origin": "ISAAC_SIM_SYNTHETIC",
                "intervention": intervention,
            })

    for row in imu:
        item = dict(row)
        step = item["step"]

        if (
            intervention
            and step >= 45
            and applied["imu_accel_bias_step"] is None
        ):
            linear = item.get("linear_acceleration")
            if linear is not None and len(linear) == 3:
                item["linear_acceleration"] = [
                    float(x) for x in linear
                ]
                item["linear_acceleration"][0] += 3.0
                applied["imu_accel_bias_step"] = step

        streams["imu"].append({
            "step": step,
            "simulation_step_time_s": (
                item["simulation_step_time_s"]
            ),
            "sensor_reported_time_raw": (
                item["sensor_reported_time"]
            ),
            "timing_semantics": "UNVERIFIED",
            "sensor_identity": (
                "ISAAC_SIM_SINGLE_SYNTHETIC_IMU_NOT_M2DGR"
            ),
            "origin": "ISAAC_SIM_SYNTHETIC",
            "intervention": intervention,
            **imu_features(item),
        })

    if intervention and (
        applied["camera_blackout_frame"] != 3
        or applied["lidar_half_sample_frame"] != 3
        or applied["imu_accel_bias_step"] is None
    ):
        raise ValueError("Synthetic intervention not applied")

    return streams, applied


def run(
    data: Path,
    evidence_file: Path,
    destination: Path,
) -> dict:
    if destination.exists() or destination.is_symlink():
        raise ValueError("Output already exists")

    if (
        not destination.parent.is_dir()
        or destination.parent.is_symlink()
    ):
        raise ValueError("Unsafe output parent")

    require_regular(evidence_file)
    evidence = json.loads(evidence_file.read_text())

    for key, name in (
        ("summary_sha256", "summary_v1.json"),
        ("capture_index_sha256", "capture_index_v15.json"),
        ("imu_series_sha256", "imu_v1.jsonl"),
        ("pose_series_sha256", "base_pose_series_v15.jsonl"),
    ):
        require_hash(data / name, evidence[key])

    clean, _ = construct(data, evidence, False)
    altered, applied = construct(data, evidence, True)

    # Verify intervention effects without inferring sensor health.
    assert (
        clean["camera"][2]["features"]["gray_mean_intensity_8bit"]
        > 0.0
    )
    assert (
        altered["camera"][2]["features"]["gray_mean_intensity_8bit"]
        == 0.0
    )
    assert (
        altered["lidar"][2]["features"]["point_count"]
        < clean["lidar"][2]["features"]["point_count"]
    )

    target_step = applied["imu_accel_bias_step"]
    assert target_step is not None
    clean_imu = clean["imu"][target_step - 1]["features"]
    changed_imu = altered["imu"][target_step - 1]["features"]
    assert clean_imu != changed_imu

    output_bytes = {}

    for condition, streams in (
        ("clean", clean),
        ("intervention", altered),
    ):
        for modality, records in streams.items():
            name = f"{condition}_{modality}.jsonl"
            output_bytes[name] = b"".join(
                canonical_line(record) for record in records
            )

    manifest = {
        "schema": SCHEMA,
        "source_evidence_sha256": digest(evidence_file),
        "source_data_origin": "ISAAC_SIM_SYNTHETIC",
        "stream_record_counts": {
            name: len(records)
            for name, records in clean.items()
        },
        "interventions": applied,
        "intervention_truth_is_empirical_health_supervision": False,
        "se3_camera_imu_contract_reused": True,
        "phase4_lidar_icp_features_computed": False,
        "sensor_synchronization_verified": False,
        "independent_ground_truth_used": False,
        "health_label_generated": False,
        "model_trained": False,
        "generated_files_sha256": {
            name: hashlib.sha256(blob).hexdigest()
            for name, blob in sorted(output_bytes.items())
        },
    }

    # Derive again independently before writing any output.
    again_clean, _ = construct(data, evidence, False)
    again_altered, again_applied = construct(data, evidence, True)
    assert applied == again_applied

    for condition, streams in (
        ("clean", again_clean),
        ("intervention", again_altered),
    ):
        for modality, records in streams.items():
            name = f"{condition}_{modality}.jsonl"
            derived = b"".join(
                canonical_line(record) for record in records
            )
            if output_bytes[name] != derived:
                raise ValueError("Non-deterministic diagnostic output")

    destination.mkdir(mode=0o700)

    for name, blob in sorted(output_bytes.items()):
        (destination / name).write_bytes(blob)

    (destination / "bridge_manifest_v1.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )

    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("recording", type=Path)
    parser.add_argument("evidence", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()

    manifest = run(
        args.recording,
        args.evidence,
        args.destination,
    )

    print(
        "CLEAN_AND_INTERVENTION_RECORDS=",
        manifest["stream_record_counts"],
    )
    print(
        "SYNTHETIC_INTERVENTIONS=",
        manifest["interventions"],
    )
    print("DETERMINISM_CHECK=PASS")
    print("ISAACSIM_V15_SE3_DIAGNOSTIC_BRIDGE=PASS")


if __name__ == "__main__":
    main()
