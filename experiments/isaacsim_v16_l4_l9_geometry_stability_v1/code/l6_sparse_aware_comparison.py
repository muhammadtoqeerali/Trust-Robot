"""L6 offline geometry comparison with sparse-frame handling.

Structural geometry diagnostics only. No independent ground truth,
physical sensor calibration, health labels or pose-factor admission.
"""

import hashlib
import json
import statistics
import sys
from pathlib import Path

import numpy as np

STEPS = [51, 61, 71, 81, 91, 101]
COUNTS = [16, 16, 16, 16, 16, 2]


def sha(path):
    assert path.is_file() and not path.is_symlink(), path
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    sha(path)
    return json.loads(path.read_text())


def canonical(value):
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ) + "\n"
    ).encode()


def geometry(cloud):
    cloud = np.asarray(cloud, dtype=np.float64)

    assert cloud.ndim == 2
    assert cloud.shape[1] == 3
    assert np.isfinite(cloud).all()

    result = {
        "point_count": int(len(cloud)),
        "spatial_singular_ratio": None,
        "rotational_information_ratio": None,
        "spatial_rank": None,
        "physical_six_dof_observability_verified": False,
        "calibrated_sensor_noise_model": False,
    }

    # A two-point cloud must not be passed into
    # the three-dimensional geometry calculation.
    if len(cloud) < 3:
        result["status"] = (
            "INSUFFICIENT_POINTS_FOR_3D_GEOMETRY"
        )
        return result

    centered = cloud - cloud.mean(axis=0)

    singular = np.linalg.svd(
        centered,
        compute_uv=False,
    )

    assert len(singular) == 3
    assert singular[0] > 0

    h = (
        np.eye(3) * np.sum(centered * centered)
        - centered.T @ centered
    )

    eigen = np.linalg.eigvalsh(
        (h + h.T) / 2
    )

    assert np.isfinite(eigen).all()
    assert eigen[-1] > 0
    assert eigen[0] >= -1e-10

    eigen = np.maximum(eigen, 0)

    result.update({
        "status":
            "STRUCTURAL_GEOMETRY_COMPUTED_NOT_QUALIFIED",

        "spatial_singular_ratio":
            float(singular[-1] / singular[0]),

        "rotational_information_ratio":
            float(eigen[0] / eigen[-1]),

        "spatial_rank":
            int(np.linalg.matrix_rank(centered)),
    })

    return result


def analyze(run, baseline):
    folder = run / "multimodal_probe_results_v15"

    frames = load(
        folder / "capture_index_v15.json"
    )

    summary = load(
        folder / "summary_v1.json"
    )

    assert len(frames) == 6
    assert [int(f["step"]) for f in frames] == STEPS

    assert summary["sequence_camera_frames"] == 6
    assert summary["sequence_lidar_frames"] == 6
    assert summary["usd_pose_samples"] == 130

    old_geometry = baseline["geometry_summary"]

    assert len(old_geometry) == 6
    assert [g["step"] for g in old_geometry] == STEPS

    rows = []

    for index, (step, expected_count) in enumerate(
        zip(STEPS, COUNTS),
        start=1,
    ):
        item = frames[index - 1]

        relative = (
            f"frames_v15/lidar_{index:03d}.npy"
        )

        assert item["lidar_file"] == relative
        assert item["lidar_points"] == expected_count

        path = folder / relative

        assert path.is_file()
        assert not path.is_symlink()

        with path.open("rb") as file:
            cloud = np.load(
                file,
                allow_pickle=False,
            )

        assert cloud.shape == (expected_count, 3)
        assert np.isfinite(cloud).all()

        raw_path = (
            run / "qualified_xyz_v1"
            / f"lidar_xyz_step_{step:03d}.npz"
        )

        assert raw_path.is_file()
        assert not raw_path.is_symlink()

        with np.load(
            raw_path,
            allow_pickle=False,
        ) as raw:
            assert np.array_equal(
                raw["xyz"],
                cloud,
            )

            flags = raw["flags"].astype(
                np.uint64
            )

            assert len(flags) == expected_count
            assert np.all((flags & 64) != 0)

        row = {
            "step": step,
            "cloud_sha256": sha(path),
            "gmo_xyz_source_sha256": sha(raw_path),
            **geometry(cloud),
        }

        rows.append(row)

    expected_statuses = (
        ["STRUCTURAL_GEOMETRY_COMPUTED_NOT_QUALIFIED"] * 5
        + ["INSUFFICIENT_POINTS_FOR_3D_GEOMETRY"]
    )

    assert [
        row["status"] for row in rows
    ] == expected_statuses

    original_ratios = [
        float(
            item[
                "rotational_information_min_to_max_ratio"
            ]
        )
        for item in old_geometry[:5]
    ]

    candidate_ratios = [
        row["rotational_information_ratio"]
        for row in rows[:5]
    ]

    assert all(np.isfinite(original_ratios))
    assert all(np.isfinite(candidate_ratios))

    original_median = float(
        statistics.median(original_ratios)
    )

    candidate_median = float(
        statistics.median(candidate_ratios)
    )

    assert original_median > 0

    return {
        "selected_steps": STEPS,
        "actual_frames": rows,
        "actual_lidar_point_counts": COUNTS,

        "total_actual_lidar_points": sum(COUNTS),
        "original_total_lidar_points": 84,

        "usable_geometry_frames": 5,
        "sparse_final_frame_excluded_from_geometry_median":
            True,

        "original_first_five_median_rotational_ratio":
            original_median,

        "candidate_first_five_median_rotational_ratio":
            candidate_median,

        "median_ratio_factor_diagnostic_only":
            candidate_median / original_median,

        "candidate_structural_ratio_higher":
            bool(candidate_median > original_median),

        "pose_factors_authorized": 0,
        "registration_accuracy_scored": False,
        "cross_sensor_synchronization_verified": False,
        "independent_ground_truth_verified": False,
        "health_labels_generated": 0,
        "simulation_is_synthetic": True,
        "physical_sensor_performance_verified": False,
    }


def main():
    assert len(sys.argv) == 5

    run, l2_path, receipt_path, out = map(
        Path,
        sys.argv[1:],
    )

    assert run.is_dir() and not run.is_symlink()
    assert out.is_dir() and not out.is_symlink()

    baseline = load(l2_path)
    receipt = load(receipt_path)

    assert receipt["simulator_executed"] is False
    assert receipt["calibrated_pose_factors"] == 0

    first = analyze(run, baseline)
    second = analyze(run, baseline)

    assert canonical(first) == canonical(second)

    report = {
        "schema":
            "TRUST_ROBOT_L6_SPARSE_AWARE_GEOMETRY_COMPARISON_V1",

        "l2_baseline_sha256": sha(l2_path),
        "l5_preparation_receipt_sha256":
            sha(receipt_path),

        "implementation_sha256":
            sha(Path(__file__)),

        "repeated_derivation_identical": True,

        **first,
    }

    destination = (
        out / "l6_sparse_aware_geometry_comparison_v1.json"
    )

    with destination.open("x") as file:
        json.dump(
            report,
            file,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        file.write("\n")

    for row in report["actual_frames"]:
        print(
            "L6_FRAME=",
            json.dumps({
                "step": row["step"],
                "points": row["point_count"],
                "status": row["status"],
                "rotation_ratio":
                    row["rotational_information_ratio"],
            }, sort_keys=True),
        )

    print(
        "ORIGINAL_MEDIAN_ROTATION_RATIO=",
        report["original_first_five_median_rotational_ratio"],
    )

    print(
        "CANDIDATE_MEDIAN_ROTATION_RATIO=",
        report["candidate_first_five_median_rotational_ratio"],
    )

    print(
        "ROTATIONAL_RATIO_FACTOR_DIAGNOSTIC_ONLY=",
        report["median_ratio_factor_diagnostic_only"],
    )

    print("ACTUAL_LIDAR_POINTS=82")
    print("ORIGINAL_LIDAR_POINTS=84")
    print("LAST_SCAN=INSUFFICIENT_POINTS_FOR_3D_GEOMETRY")
    print("QUALIFIED_POSE_FACTORS=0")
    print("REPEATED_DERIVATION=PASS")
    print("L6_OFFLINE_REANALYSIS=PASS")

    print(
        "L6_REANALYSIS_SHA256=",
        sha(destination),
    )


if __name__ == "__main__":
    main()
