"""Controlled registration comparison of two synthetic LiDAR layouts.

Engineering diagnostics only.
No calibrated noise, physical synchronization, localization scoring,
health supervision or pose-factor authorization.
"""

import hashlib
import json
import math
import signal
import statistics
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

COUNTS = {
    "original": [16, 16, 16, 16, 16, 4],
    "candidate": [16, 16, 16, 16, 16, 2],
}

AMPLITUDES_M = (0.0005, 0.002)

FEATURES = (
    "source_point_count",
    "target_point_count",
    "fixed_point_iterations",
    "final_correspondence_count",
    "final_nearest_neighbor_rmse_m",
)


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
    ).encode("utf-8")


def load_scans(run, expected_hashes, counts):
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

    assert [f["step"] for f in expected_hashes] == STEPS

    result = []

    for i, (frame, digest_row, count) in enumerate(
        zip(frames, expected_hashes, counts),
        1,
    ):
        step = STEPS[i - 1]

        relative = f"frames_v15/lidar_{i:03d}.npy"

        assert frame["lidar_file"] == relative
        assert frame["lidar_points"] == count

        path = folder / relative

        assert sha(path) == digest_row["cloud_sha256"]

        with path.open("rb") as file:
            cloud = np.load(
                file,
                allow_pickle=False,
            )

        assert cloud.shape == (count, 3)
        assert np.isfinite(cloud).all()

        source = (
            run / "qualified_xyz_v1"
            / f"lidar_xyz_step_{step:03d}.npz"
        )

        with np.load(
            source,
            allow_pickle=False,
        ) as raw:
            assert np.array_equal(
                raw["xyz"],
                cloud,
            )

            flags = raw["flags"].astype(
                np.uint64
            )

            stamp = int(
                raw["timestamp_ns"][0]
            )

            assert len(flags) == count
            assert np.all((flags & 64) != 0)

        assert frame["lidar_rendering_time_raw"] == (
            "GMO_SENSOR_TIMESTAMP_NS:" + str(stamp)
        )

        result.append(cloud.copy())

    return result


def perturb(current, amplitude_m):
    # Same perturbation rule as the frozen L2 experiment.

    x = np.asarray(
        current,
        dtype=np.float64,
    )

    i = (
        np.arange(
            len(x),
            dtype=np.float64,
        )[:, None] + 1
    )

    k = (
        np.arange(
            3,
            dtype=np.float64,
        )[None, :] + 1
    )

    pattern = (
        np.sin(i * k * 1.61803398875)
        + 0.5 * np.cos(
            i * (k + 1) * 0.754877666
        )
    )

    pattern -= pattern.mean(
        axis=0,
        keepdims=True,
    )

    pattern /= np.max(
        np.abs(pattern)
    )

    return x + amplitude_m * pattern


def pose_delta(a, b):
    ta = np.array(
        a["translation_m"],
        dtype=float,
    )

    tb = np.array(
        b["translation_m"],
        dtype=float,
    )

    qa = np.array(
        a["quaternion_wxyz"],
        dtype=float,
    )

    qb = np.array(
        b["quaternion_wxyz"],
        dtype=float,
    )

    assert abs(np.linalg.norm(qa) - 1) < 1e-5
    assert abs(np.linalg.norm(qb) - 1) < 1e-5

    qdot = float(
        np.clip(
            abs(np.dot(qa, qb)),
            0,
            1,
        )
    )

    return {
        "translation_change_m":
            float(np.linalg.norm(tb - ta)),

        "rotation_change_deg":
            float(
                math.degrees(
                    2 * math.acos(qdot)
                )
            ),
    }


def bounded_registration(previous, current):
    def handler(_signum, _frame):
        raise TimeoutError(
            "Frozen registration timed out"
        )

    old = signal.signal(
        signal.SIGALRM,
        handler,
    )

    signal.setitimer(
        signal.ITIMER_REAL,
        6,
    )

    try:
        result = register_current_scan_to_previous(
            previous,
            current,
        )

        diagnostics = (
            extract_lidar_registration_diagnostics(
                result.diagnostics
            )
        )

        assert tuple(
            f.name for f in diagnostics.features
        ) == FEATURES

        return {
            "status": "DIAGNOSTIC_AVAILABLE",

            "pose":
                result.previous_lidar_T_current_lidar.to_dict(),

            "features": {
                f.name: f.value
                for f in diagnostics.features
            },

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
            "features": None,
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


def condition_rows(scans):
    rows = []

    # First four pairs only.
    # The last pair has an insufficient-point endpoint.

    for i in range(1, 5):
        previous = scans[i - 1]
        current = scans[i]

        baseline = bounded_registration(
            previous,
            current,
        )

        perturbations = []

        for amplitude in AMPLITUDES_M:
            altered = bounded_registration(
                previous,
                perturb(current, amplitude),
            )

            if (
                baseline["pose"] is not None
                and altered["pose"] is not None
            ):
                change = pose_delta(
                    baseline["pose"],
                    altered["pose"],
                )
            else:
                change = None

            perturbations.append({
                "per_coordinate_max_perturbation_m":
                    amplitude,

                "status": altered["status"],
                "error": altered["error"],

                "candidate_change": change,

                "nearest_neighbor_rmse_m": (
                    float(
                        altered["features"][
                            "final_nearest_neighbor_rmse_m"
                        ]
                    )
                    if altered["features"] is not None
                    else None
                ),

                "calibrated_noise": False,
            })

        rows.append({
            "previous_step": STEPS[i - 1],
            "current_step": STEPS[i],

            "previous_points": len(previous),
            "current_points": len(current),

            "baseline_status": baseline["status"],
            "baseline_error": baseline["error"],

            "baseline_rmse_m": (
                float(
                    baseline["features"][
                        "final_nearest_neighbor_rmse_m"
                    ]
                )
                if baseline["features"] is not None
                else None
            ),

            "baseline_translation_norm_m": (
                float(
                    np.linalg.norm(
                        baseline["pose"]["translation_m"]
                    )
                )
                if baseline["pose"] is not None
                else None
            ),

            "baseline_pose": baseline["pose"],

            "synthetic_challenges": perturbations,

            "scientific_pose_validity_verified": False,
            "pose_factor_authorized": False,
        })

    return rows


def verify_original_control(rows, l1, l2):
    originals = [
        row
        for row in l1["paired_registration"]
        if row["condition"] == "clean"
    ]

    frozen = l2["clean_pairs_analyzed"]

    assert len(originals) == 5
    assert len(frozen) == 4

    for i, row in enumerate(rows):
        prior = originals[i]["registration"]
        earlier = frozen[i]

        assert row["baseline_status"] == (
            "DIAGNOSTIC_AVAILABLE"
        )

        assert prior["status"] == (
            "FROZEN_DIAGNOSTICS_AVAILABLE"
        )

        assert earlier[
            "frozen_frontend_baseline_reproduced"
        ] is True

        assert math.isclose(
            row["baseline_rmse_m"],
            earlier["baseline_icp_rmse_m"],
            rel_tol=1e-8,
            abs_tol=1e-10,
        )

        difference = pose_delta(
            row["baseline_pose"],
            prior["relative_pose_candidate"],
        )

        assert difference["translation_change_m"] < 1e-8
        assert difference["rotation_change_deg"] < 0.0001

        for actual, expected in zip(
            row["synthetic_challenges"],
            earlier["sensitivity_challenges"],
        ):
            assert (
                actual["per_coordinate_max_perturbation_m"]
                == expected[
                    "max_per_coordinate_perturbation_m"
                ]
            )

            status = (
                "DIAGNOSTIC_AVAILABLE"
                if expected["outcome_status"]
                == "DIAGNOSTIC_AVAILABLE"
                else "REGISTRATION_UNAVAILABLE"
            )

            assert actual["status"] == status

            if expected["candidate_change"] is not None:
                assert actual["candidate_change"] is not None

                for key in (
                    "translation_change_m",
                    "rotation_change_deg",
                ):
                    assert math.isclose(
                        actual["candidate_change"][key],
                        expected["candidate_change"][key],
                        rel_tol=1e-6,
                        abs_tol=1e-5,
                    )

    return True


def median_or_none(values):
    return (
        float(statistics.median(values))
        if values
        else None
    )


def summarize(original, candidate):
    results = []

    for j, magnitude in enumerate(AMPLITUDES_M):
        comparable = []

        for a, b in zip(original, candidate):
            x = a["synthetic_challenges"][j][
                "candidate_change"
            ]

            y = b["synthetic_challenges"][j][
                "candidate_change"
            ]

            if x is not None and y is not None:
                comparable.append({
                    "steps": [
                        a["previous_step"],
                        a["current_step"],
                    ],

                    "original_rotation_change_deg":
                        x["rotation_change_deg"],

                    "candidate_rotation_change_deg":
                        y["rotation_change_deg"],

                    "original_translation_change_m":
                        x["translation_change_m"],

                    "candidate_translation_change_m":
                        y["translation_change_m"],
                })

        original_changes = [
            x["original_rotation_change_deg"]
            for x in comparable
        ]

        candidate_changes = [
            x["candidate_rotation_change_deg"]
            for x in comparable
        ]

        results.append({
            "perturbation_max_per_coordinate_m":
                magnitude,

            "comparable_pairs": len(comparable),

            "paired_observations": comparable,

            "original_median_rotation_change_deg":
                median_or_none(original_changes),

            "candidate_median_rotation_change_deg":
                median_or_none(candidate_changes),

            "candidate_lower_rotation_change_pair_count":
                sum(
                    x["candidate_rotation_change_deg"]
                    < x["original_rotation_change_deg"]
                    for x in comparable
                ),

            "all_pairs_comparable":
                len(comparable) == 4,
        })

    return results


def main():
    assert len(sys.argv) == 7, (
        "L7.py ORIGINAL CANDIDATE L1 L2 L6 OUTPUT"
    )

    original, candidate, l1p, l2p, l6p, out = map(
        Path,
        sys.argv[1:],
    )

    assert out.is_dir() and not out.is_symlink()

    l1 = load(l1p)
    l2 = load(l2p)
    l6 = load(l6p)

    assert l1["source_steps"] == STEPS

    assert l1["source_point_counts"] == (
        COUNTS["original"]
    )

    assert l6["actual_lidar_point_counts"] == (
        COUNTS["candidate"]
    )

    assert l6["repeated_derivation_identical"] is True
    assert l6["pose_factors_authorized"] == 0

    assert l6[
        "candidate_structural_ratio_higher"
    ] is True

    assert l2["pose_factors_accepted"] == 0
    assert l1["health_labels_generated"] is False

    original_hashes = [
        {
            "step": row["step"],
            "cloud_sha256": row["lidar_file_sha256"],
        }
        for row in l1["scan_geometry"]
    ]

    first_set = load_scans(
        original,
        original_hashes,
        COUNTS["original"],
    )

    second_set = load_scans(
        candidate,
        l6["actual_frames"],
        COUNTS["candidate"],
    )

    assert sum(map(len, first_set)) == 84
    assert sum(map(len, second_set)) == 82

    def derive():
        original_rows = condition_rows(first_set)
        candidate_rows = condition_rows(second_set)

        verify_original_control(
            original_rows,
            l1,
            l2,
        )

        return {
            "original_pairs": original_rows,
            "candidate_pairs": candidate_rows,

            "sensitivity_comparisons": summarize(
                original_rows,
                candidate_rows,
            ),
        }

    first = derive()
    second = derive()

    assert canonical(first) == canonical(second)

    report = {
        "schema":
            "TRUST_ROBOT_L7_PAIRED_SYNTHETIC_REGISTRATION_COMPARISON_V1",

        "implementation_sha256":
            sha(Path(__file__)),

        "l1_evidence_sha256": sha(l1p),
        "l2_evidence_sha256": sha(l2p),
        "l6_evidence_sha256": sha(l6p),

        "original_frame_counts": COUNTS["original"],
        "candidate_frame_counts": COUNTS["candidate"],

        "analyzed_step_pairs": [
            [STEPS[i - 1], STEPS[i]]
            for i in range(1, 5)
        ],

        "sparse_last_pair_original_and_candidate":
            "NOT_REGISTERED",

        "frozen_original_l2_control_reproduced": True,

        "deterministic_rederivation_identical": True,

        "frozen_phase2_registration_reused": True,
        "frozen_phase4_diagnostics_reused": True,

        "synthetic_perturbations_are_calibrated_noise":
            False,

        "reference_ground_truth_used": False,
        "cross_sensor_synchronization_verified": False,

        "localization_ate_rpe_scored": False,
        "health_labels_emitted": 0,

        "scientifically_qualified_pose_factors": 0,

        **first,
    }

    target = (
        out / "l7_registration_comparison_v1.json"
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

    for a, b in zip(
        first["original_pairs"],
        first["candidate_pairs"],
    ):
        print(
            "L7_PAIR=",
            json.dumps({
                "steps": [
                    a["previous_step"],
                    a["current_step"],
                ],

                "original_status":
                    a["baseline_status"],

                "candidate_status":
                    b["baseline_status"],

                "original_rmse_m":
                    a["baseline_rmse_m"],

                "candidate_rmse_m":
                    b["baseline_rmse_m"],

                "original_2mm_change":
                    a["synthetic_challenges"][1][
                        "candidate_change"
                    ],

                "candidate_2mm_change":
                    b["synthetic_challenges"][1][
                        "candidate_change"
                    ],
            }, sort_keys=True),
        )

    for result in first["sensitivity_comparisons"]:
        print(
            "L7_SENSITIVITY_SUMMARY=",
            json.dumps({
                key: value
                for key, value in result.items()
                if key != "paired_observations"
            }, sort_keys=True),
        )

    print("ORIGINAL_L2_CONTROL=REPRODUCED")
    print("L7_REPEATED_DERIVATION=PASS")

    print(
        "SPARSE_FINAL_PAIR=EXCLUDED_IN_BOTH_CONDITIONS"
    )

    print("QUALIFIED_POSE_FACTORS=0")
    print("L7_OFFLINE_IMPLEMENTATION=PASS")
    print("L7_REPORT_SHA256=", sha(target))


if __name__ == "__main__":
    main()
