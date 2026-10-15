"""L9: two-way and skip-frame SE(3) consistency diagnostics.

Engineering diagnostics only.
No independent reference, calibrated noise, health supervision,
scientific pose accuracy or estimator factor admission.
"""

import hashlib
import json
import math
import signal
import statistics
import sys
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation

from trust_robot.lidar_frontend import (
    LidarFrontendError,
    register_current_scan_to_previous,
)
from trust_robot.diagnostics import (
    DiagnosticFeatureError,
    extract_lidar_registration_diagnostics,
)

STEPS = [51, 61, 71, 81, 91, 101]

COUNTS = {
    "original": [16, 16, 16, 16, 16, 4],
    "candidate": [16, 16, 16, 16, 16, 2],
}

FEATURES = (
    "source_point_count",
    "target_point_count",
    "fixed_point_iterations",
    "final_correspondence_count",
    "final_nearest_neighbor_rmse_m",
)


def sha(path):
    assert path.is_file() and not path.is_symlink(), str(path)
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


def pose_to_matrix(pose):
    xyz = np.asarray(
        pose["translation_m"],
        dtype=np.float64,
    )
    qwxyz = np.asarray(
        pose["quaternion_wxyz"],
        dtype=np.float64,
    )

    assert xyz.shape == (3,)
    assert qwxyz.shape == (4,)
    assert np.isfinite(xyz).all()
    assert np.isfinite(qwxyz).all()
    assert abs(float(np.linalg.norm(qwxyz)) - 1.0) < 1e-5

    rotation = Rotation.from_quat([
        qwxyz[1],
        qwxyz[2],
        qwxyz[3],
        qwxyz[0],
    ]).as_matrix()

    matrix = np.eye(4)
    matrix[:3, :3] = rotation
    matrix[:3, 3] = xyz

    return matrix


def invert(matrix):
    result = np.eye(4)
    result[:3, :3] = matrix[:3, :3].T
    result[:3, 3] = (
        -result[:3, :3] @ matrix[:3, 3]
    )
    return result


def residual(matrix):
    assert np.isfinite(matrix).all()

    return {
        "translation_closure_m":
            float(np.linalg.norm(matrix[:3, 3])),

        "rotation_closure_deg":
            float(np.degrees(
                Rotation.from_matrix(
                    matrix[:3, :3]
                ).magnitude()
            )),
    }


def selftest():
    q = Rotation.from_euler(
        "xyz", [0.2, -0.3, 0.5]
    ).as_quat()

    sample = {
        "translation_m": [0.4, -0.7, 0.9],
        "quaternion_wxyz": [
            float(q[3]),
            float(q[0]),
            float(q[1]),
            float(q[2]),
        ],
    }

    matrix = pose_to_matrix(sample)

    forward = residual(
        matrix @ invert(matrix)
    )
    reverse = residual(
        invert(matrix) @ matrix
    )

    for item in (forward, reverse):
        assert item["translation_closure_m"] < 1e-12
        assert item["rotation_closure_deg"] < 1e-8

    print(
        "SE3_COMPOSITION_INVERSE_SELFTEST=PASS",
        flush=True,
    )


def bounded(previous, current):
    def alarm(_signum, _frame):
        raise TimeoutError(
            "Registration exceeded time budget"
        )

    old = signal.signal(
        signal.SIGALRM,
        alarm,
    )

    signal.setitimer(
        signal.ITIMER_REAL,
        5.0,
    )

    try:
        result = register_current_scan_to_previous(
            previous,
            current,
        )

        diagnostic = (
            extract_lidar_registration_diagnostics(
                result.diagnostics
            )
        )

        features = {
            f.name: f.value
            for f in diagnostic.features
        }

        assert tuple(features) == FEATURES

        return {
            "status": "DIAGNOSTIC_AVAILABLE",
            "pose":
                result.previous_lidar_T_current_lidar.to_dict(),
            "rmse_m": float(features[
                "final_nearest_neighbor_rmse_m"
            ]),
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
            "pose": None,
            "rmse_m": None,
            "error": type(exc).__name__,
        }

    finally:
        signal.setitimer(
            signal.ITIMER_REAL,
            0,
        )
        signal.signal(
            signal.SIGALRM,
            old,
        )


def read_scans(run, hashes, counts):
    root = (
        run / "multimodal_probe_results_v15"
    )

    index = load(
        root / "capture_index_v15.json"
    )
    summary = load(
        root / "summary_v1.json"
    )

    assert len(index) == len(hashes) == 6
    assert [r["step"] for r in index] == STEPS
    assert [r["step"] for r in hashes] == STEPS

    assert summary["sequence_lidar_frames"] == 6
    assert summary["sequence_camera_frames"] == 6

    clouds = []

    for i, (row, hashed, n) in enumerate(
        zip(index, hashes, counts),
        start=1,
    ):
        relative = f"frames_v15/lidar_{i:03d}.npy"

        assert row["lidar_file"] == relative
        assert row["lidar_points"] == n

        path = root / relative

        assert sha(path) == hashed["cloud_sha256"]

        with path.open("rb") as stream:
            cloud = np.load(
                stream,
                allow_pickle=False,
            )

        assert cloud.shape == (n, 3)
        assert np.isfinite(cloud).all()

        raw_path = (
            run / "qualified_xyz_v1"
            / f"lidar_xyz_step_{STEPS[i-1]:03d}.npz"
        )

        sha(raw_path)

        with np.load(
            raw_path,
            allow_pickle=False,
        ) as raw:
            assert np.array_equal(
                raw["xyz"], cloud
            )

            flags = np.asarray(
                raw["flags"],
                dtype=np.uint64,
            )

            assert len(flags) == n
            assert np.all(
                (flags & 64) != 0
            )

        clouds.append(cloud)

    return clouds


def pose_difference(a, b):
    return residual(
        invert(pose_to_matrix(a))
        @ pose_to_matrix(b)
    )


def characterize(clouds, historical):
    assert len(historical) == 4

    forwards = []
    bidirectional = []
    skips = []

    for j in range(4):
        first = STEPS[j]
        second = STEPS[j + 1]

        expected = historical[j]

        assert [
            expected["previous_step"],
            expected["current_step"],
        ] == [first, second]

        forward = bounded(
            clouds[j],
            clouds[j + 1],
        )

        assert (
            forward["status"]
            == expected["baseline_status"]
            == "DIAGNOSTIC_AVAILABLE"
        )

        assert math.isclose(
            forward["rmse_m"],
            expected["baseline_rmse_m"],
            rel_tol=1e-8,
            abs_tol=1e-10,
        )

        delta = pose_difference(
            forward["pose"],
            expected["baseline_pose"],
        )

        assert delta["translation_closure_m"] < 1e-8
        assert delta["rotation_closure_deg"] < 0.0001

        forwards.append(forward)

        backward = bounded(
            clouds[j + 1],
            clouds[j],
        )

        cycle = (
            residual(
                pose_to_matrix(forward["pose"])
                @ pose_to_matrix(backward["pose"])
            )
            if backward["pose"] is not None
            else None
        )

        bidirectional.append({
            "steps": [first, second],
            "forward_rmse_m": forward["rmse_m"],
            "reverse_status": backward["status"],
            "reverse_rmse_m": backward["rmse_m"],
            "reverse_error": backward["error"],
            "forward_reverse_cycle": cycle,
            "pose_factor_authorized": False,
        })

    for j in range(3):
        direct = bounded(
            clouds[j],
            clouds[j + 2],
        )

        chained = (
            pose_to_matrix(forwards[j]["pose"])
            @ pose_to_matrix(forwards[j + 1]["pose"])
        )

        gap = (
            residual(
                invert(pose_to_matrix(direct["pose"]))
                @ chained
            )
            if direct["pose"] is not None
            else None
        )

        skips.append({
            "steps": [
                STEPS[j],
                STEPS[j + 1],
                STEPS[j + 2],
            ],
            "direct_registration_status":
                direct["status"],
            "direct_registration_rmse_m":
                direct["rmse_m"],
            "direct_registration_error":
                direct["error"],
            "direct_vs_two_step_composition":
                gap,
            "pose_factor_authorized": False,
        })

    return {
        "bidirectional_pairs": bidirectional,
        "two_step_comparisons": skips,
    }


def stats(rows, field):
    values = [
        row[field]
        for row in rows
    ]

    return {
        "count": len(values),

        "median": (
            float(statistics.median(values))
            if values else None
        ),

        "maximum": (
            float(max(values))
            if values else None
        ),
    }


def main():
    assert len(sys.argv) == 8

    original, candidate, l1p, l6p, l7p, l8p, out = map(
        Path,
        sys.argv[1:],
    )

    assert out.is_dir() and not out.is_symlink()

    l1, l6, l7, l8 = (
        load(path)
        for path in (
            l1p, l6p, l7p, l8p
        )
    )

    assert l8["source_l1_sha256"] == sha(l1p)
    assert l8["source_l6_sha256"] == sha(l6p)
    assert l8["source_l7_sha256"] == sha(l7p)

    assert l8["repeated_derivations_identical"] is True
    assert l8["pose_factors_authorized"] == 0

    assert l8[
        "total_perturbation_registrations_per_derivation"
    ] == 192

    assert l7[
        "scientifically_qualified_pose_factors"
    ] == 0

    assert l6["pose_factors_authorized"] == 0

    assert l1["source_point_counts"] == (
        COUNTS["original"]
    )

    assert l6["actual_lidar_point_counts"] == (
        COUNTS["candidate"]
    )

    original_hashes = [
        {
            "step": row["step"],
            "cloud_sha256": row["lidar_file_sha256"],
        }
        for row in l1["scan_geometry"]
    ]

    scans = {
        "original": read_scans(
            original,
            original_hashes,
            COUNTS["original"],
        ),
        "candidate": read_scans(
            candidate,
            l6["actual_frames"],
            COUNTS["candidate"],
        ),
    }

    selftest()

    def derive():
        return {
            condition: characterize(
                scans[condition],
                l7[f"{condition}_pairs"],
            )
            for condition in (
                "original",
                "candidate",
            )
        }

    first = derive()
    second = derive()

    assert canonical(first) == canonical(second)

    report = {
        "schema":
            "TRUST_ROBOT_L9_V16_BIDIRECTIONAL_SKIP_PAIR_DIAGNOSTIC_V1",

        "implementation_sha256":
            sha(Path(__file__)),

        "l1_sha256": sha(l1p),
        "l6_sha256": sha(l6p),
        "l7_sha256": sha(l7p),
        "l8_sha256": sha(l8p),

        "bidirectional_pair_attempts": 8,
        "two_step_direct_attempts": 6,

        "original_and_candidate_l7_baselines_reproduced":
            True,

        "repeated_derivation_identical":
            True,

        "sparse_final_pair_not_used":
            True,

        "independent_reference_verified":
            False,

        "physical_synchronization_verified":
            False,

        "scientific_accuracy_scored":
            False,

        "health_labels_generated": 0,
        "pose_factors_authorized": 0,

        "note": (
            "Closure is internal geometric consistency, "
            "not independently validated localization accuracy"
        ),

        "results": first,
    }

    target = (
        out / "l9_bidirectional_skip_pair_report_v1.json"
    )

    with target.open("x") as file:
        json.dump(
            report,
            file,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        file.write("\n")

    for condition, result in first.items():
        for row in result["bidirectional_pairs"]:
            print(
                "L9_BIDIRECTIONAL=",
                json.dumps({
                    "condition": condition,
                    **row,
                }, sort_keys=True),
                flush=True,
            )

        for row in result["two_step_comparisons"]:
            print(
                "L9_SKIP_PAIR=",
                json.dumps({
                    "condition": condition,
                    **row,
                }, sort_keys=True),
                flush=True,
            )

        for kind, key in (
            ("REVERSE", "forward_reverse_cycle"),
            ("SKIP", "direct_vs_two_step_composition"),
        ):
            source_rows = (
                result["bidirectional_pairs"]
                if kind == "REVERSE"
                else result["two_step_comparisons"]
            )

            values = [
                row[key]
                for row in source_rows
                if row[key] is not None
            ]

            summary = {
                "condition": condition,
                "comparison": kind,

                "translation_m": stats(
                    values,
                    "translation_closure_m",
                ),

                "rotation_deg": stats(
                    values,
                    "rotation_closure_deg",
                ),
            }

            print(
                "L9_CLOSURE_SUMMARY=",
                json.dumps(
                    summary,
                    sort_keys=True,
                ),
                flush=True,
            )

    print("L7_BASELINES_REPRODUCED=8")
    print("REVERSE_REGISTRATIONS_ATTEMPTED=8")
    print("TWO_STEP_DIRECT_REGISTRATIONS_ATTEMPTED=6")
    print("REPEATED_DERIVATION=PASS")
    print("QUALIFIED_POSE_FACTORS=0")
    print("L9_OFFLINE_DIAGNOSTIC=PASS")
    print("L9_REPORT_SHA256=", sha(target))


if __name__ == "__main__":
    main()
