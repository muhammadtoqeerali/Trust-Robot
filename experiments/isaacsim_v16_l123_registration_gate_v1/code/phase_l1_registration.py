"""L1: offline, synthetic, diagnostic-only LiDAR registration transfer.

Reuse frozen Phase-2 and Phase-4 algorithms unchanged.
Never authorize pose accuracy, health labels, or physical synchronization.
"""
import hashlib
import json
import math
import signal
import sys
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

STEPS = [51, 61, 71, 81, 91, 101]
COUNTS = [16, 16, 16, 16, 16, 4]

FEATURES = (
    "source_point_count",
    "target_point_count",
    "fixed_point_iterations",
    "final_correspondence_count",
    "final_nearest_neighbor_rmse_m",
)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def canonical(obj):
    return (
        json.dumps(
            obj, sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ) + "\n"
    ).encode()

def load_json(path):
    assert path.is_file() and not path.is_symlink()
    return json.loads(path.read_text())

def load_jsonl(path):
    assert path.is_file() and not path.is_symlink()
    return [
        json.loads(line)
        for line in path.read_text().splitlines()
        if line.strip()
    ]

def bounded_register(previous, current):
    def handler(_signum, _frame):
        raise TimeoutError("Registration exceeded time budget")

    old = signal.signal(signal.SIGALRM, handler)
    signal.setitimer(signal.ITIMER_REAL, 6.0)

    try:
        result = register_current_scan_to_previous(
            previous, current
        )
        extracted = extract_lidar_registration_diagnostics(
            result.diagnostics
        )
        names = tuple(f.name for f in extracted.features)
        assert names == FEATURES

        values = {
            f.name: f.value for f in extracted.features
        }

        return {
            "status": "FROZEN_DIAGNOSTICS_AVAILABLE",
            "features": values,
            "relative_pose_candidate": (
                result.previous_lidar_T_current_lidar.to_dict()
            ),
            "relative_pose_scientifically_qualified": False,
            "error": None,
        }

    except (
        LidarFrontendError,
        DiagnosticFeatureError,
        TimeoutError,
        np.linalg.LinAlgError,
    ) as exc:
        return {
            "status": "REGISTRATION_UNAVAILABLE",
            "features": None,
            "relative_pose_candidate": None,
            "relative_pose_scientifically_qualified": False,
            "error": type(exc).__name__,
        }

    finally:
        signal.setitimer(signal.ITIMER_REAL, 0.0)
        signal.signal(signal.SIGALRM, old)

def load_data(recording, evidence_path):
    evidence = load_json(evidence_path)
    assert evidence["runtime_pass"] is True
    assert evidence["offline_sensor_file_validation_pass"] is True
    assert evidence["selected_steps"] == STEPS
    assert evidence["validation_issues"] == []

    root = recording / "multimodal_probe_results_v15"

    frames = load_json(root / "capture_index_v15.json")
    poses = load_jsonl(root / "base_pose_series_v15.jsonl")
    imu = load_jsonl(root / "imu_v1.jsonl")

    assert len(frames) == 6
    assert len(poses) == len(imu) == 130
    assert [f["step"] for f in frames] == STEPS
    assert [p["step"] for p in poses] == list(range(1, 131))
    assert [p["step"] for p in imu] == list(range(1, 131))

    evidence_frames = {
        f["step"]: f
        for f in evidence["validated_frames"]
    }
    assert set(evidence_frames) == set(STEPS)

    clouds = []
    inventory = []

    for index, frame in enumerate(frames, 1):
        step = STEPS[index - 1]
        assert frame["step"] == step

        relative = f"frames_v15/lidar_{index:03d}.npy"
        assert frame["lidar_file"] == relative

        path = root / relative
        assert path.is_file() and not path.is_symlink()
        assert sha(path) == evidence_frames[step]["lidar_sha256"]

        cloud = np.load(path, allow_pickle=False)
        assert cloud.shape == (COUNTS[index - 1], 3)
        assert np.all(np.isfinite(cloud))

        source_path = (
            recording / "qualified_xyz_v1"
            / f"lidar_xyz_step_{step:03d}.npz"
        )

        assert source_path.is_file()
        assert not source_path.is_symlink()

        with np.load(
            source_path, allow_pickle=False
        ) as raw:
            original = raw["xyz"]
            flags = raw["flags"]
            stamp = int(raw["timestamp_ns"][0])

        assert np.array_equal(original, cloud)
        assert len(flags) == len(cloud)
        assert np.all(
            (flags.astype(np.uint64) & 64) != 0
        )
        assert stamp == evidence_frames[step]["timestamp_ns"]

        center = cloud.astype(np.float64)
        center -= np.mean(center, axis=0)

        singular = np.linalg.svd(
            center, compute_uv=False
        )

        relative_smallest = (
            float(singular[-1] / singular[0])
            if singular[0] > 0 else 0.0
        )

        # Structural geometry only: this is NOT proof
        # of 6-DoF observability or localization accuracy.
        inventory.append({
            "step": step,
            "points": len(cloud),
            "lidar_file_sha256": sha(path),
            "raw_xyz_source_sha256": sha(source_path),
            "singular_values": [
                float(x) for x in singular
            ],
            "smallest_to_largest_singular_ratio":
                relative_smallest,
            "spatial_rank": int(
                np.linalg.matrix_rank(center)
            ),
            "full_6dof_observability_proven": False,
        })

        clouds.append(cloud.copy())

    return clouds, inventory

def derive(clouds):
    results = []

    for condition in (
        "clean",
        "frame_3_half_sampled",
    ):
        modified = [c.copy() for c in clouds]

        if condition == "frame_3_half_sampled":
            modified[2] = modified[2][::2].copy()
            assert len(modified[2]) == 8

        for i in range(1, 6):
            previous = modified[i - 1]
            current = modified[i]

            # Prospective engineering availability gate
            # for this test only; NOT a frozen physical
            # health-classification threshold.
            sparse = min(
                len(previous), len(current)
            ) < 8

            if sparse:
                registration = {
                    "status": "SPARSE_ENDPOINT_UNAVAILABLE",
                    "features": None,
                    "relative_pose_candidate": None,
                    "relative_pose_scientifically_qualified": False,
                    "error": "INSUFFICIENT_STRUCTURAL_POINTS",
                }
            else:
                registration = bounded_register(
                    previous, current
                )

            results.append({
                "condition": condition,
                "previous_step": STEPS[i - 1],
                "current_step": STEPS[i],
                "previous_points": len(previous),
                "current_points": len(current),
                "registration": registration,
                "source_frame": "GMO_SENSOR_CARTESIAN",
                "camera_lidar_synchronized": False,
                "independent_ground_truth_used": False,
                "health_label_generated": False,
                "localization_accuracy_scored": False,
            })

    return results

def main():
    assert len(sys.argv) == 4

    recording = Path(sys.argv[1])
    evidence_path = Path(sys.argv[2])
    output = Path(sys.argv[3])

    assert recording.is_dir() and not recording.is_symlink()
    assert output.is_dir() and not output.is_symlink()

    assert not (
        output / "registration_transfer_report_v1.json"
    ).exists()

    clouds, inventory = load_data(
        recording, evidence_path
    )

    first = derive(clouds)
    second = derive(clouds)

    assert canonical(first) == canonical(second)
    assert len(first) == 10

    sparse_records = [
        x for x in first
        if x["registration"]["status"]
        == "SPARSE_ENDPOINT_UNAVAILABLE"
    ]
    assert len(sparse_records) == 2
    assert all(x["current_step"] == 101
               for x in sparse_records)

    available = sum(
        x["registration"]["status"]
        == "FROZEN_DIAGNOSTICS_AVAILABLE"
        for x in first
    )

    unavailable = len(first) - available

    print("SOURCE_LIDAR_FRAMES=", len(clouds))
    print("SOURCE_LIDAR_POINTS=", sum(map(len, clouds)))

    for item in inventory:
        print(
            "GEOMETRY_FRAME=",
            json.dumps(item, sort_keys=True)
        )

    for item in first:
        print(
            "REGISTRATION_PAIR=",
            json.dumps(item, sort_keys=True)
        )

    report = {
        "schema":
            "TRUST_ROBOT_L1_V16_REGISTRATION_TRANSFER_V1",
        "source": "V16_28_SYNTHETIC_GMO_XYZ",
        "source_evidence_sha256": sha(evidence_path),
        "implementation_sha256": sha(Path(__file__)),
        "source_steps": STEPS,
        "source_point_counts": COUNTS,
        "scan_geometry": inventory,
        "paired_registration": first,
        "pair_attempts": len(first),
        "frozen_diagnostics_available": available,
        "registration_unavailable": unavailable,
        "sparse_pairs_rejected": len(sparse_records),
        "repeat_derivation_identical": True,
        "frozen_phase2_frontend_reused": True,
        "frozen_phase4_extractor_reused": True,
        "engineering_point_gate_minimum": 8,
        "engineering_gate_is_health_threshold": False,
        "camera_exposure_synchronization_verified": False,
        "independent_ground_truth_verified": False,
        "six_dof_observability_verified": False,
        "ate_rpe_computed": False,
        "health_labels_generated": False,
        "model_training_authorized": False,
        "scientific_localization_score": None,
        "offline_implementation_pass": True,
    }

    target = output / "registration_transfer_report_v1.json"

    with target.open("x") as f:
        json.dump(
            report, f,
            sort_keys=True, indent=2,
            allow_nan=False
        )
        f.write("\n")

    print("REGISTRATION_PAIR_ATTEMPTS=", len(first))
    print("FROZEN_DIAGNOSTICS_AVAILABLE=", available)
    print("REGISTRATION_UNAVAILABLE=", unavailable)
    print("SPARSE_PAIRS_REJECTED=", len(sparse_records))
    print("DETERMINISTIC_REDERIVATION=PASS")
    print("L1_OFFLINE_IMPLEMENTATION=PASS")
    print("REPORT_SHA256=", sha(target))
    print("PHYSICAL_VALIDATION_CLAIM=NO")

if __name__ == "__main__":
    main()
