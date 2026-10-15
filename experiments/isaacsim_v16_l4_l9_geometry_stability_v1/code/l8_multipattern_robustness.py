"""L8: multi-pattern deterministic sensitivity and scripted-motion diagnostics.

No independent ground truth, calibrated sensor noise, localization score,
health supervision, or estimator factor admission.
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
MAGNITUDES = (0.0005, 0.002)
PATTERN_IDS = tuple(range(1, 13))


def sha(path):
    assert path.is_file() and not path.is_symlink(), str(path)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path):
    sha(path)
    return json.loads(path.read_text())


def canonical(value):
    return (
        json.dumps(
            value, sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ) + "\n"
    ).encode()


def pose_change(a, b):
    ta = np.asarray(a["translation_m"], dtype=np.float64)
    tb = np.asarray(b["translation_m"], dtype=np.float64)
    qa = np.asarray(a["quaternion_wxyz"], dtype=np.float64)
    qb = np.asarray(b["quaternion_wxyz"], dtype=np.float64)

    assert ta.shape == tb.shape == (3,)
    assert qa.shape == qb.shape == (4,)
    assert np.isfinite(ta).all() and np.isfinite(tb).all()
    assert abs(float(np.linalg.norm(qa)) - 1) < 1e-5
    assert abs(float(np.linalg.norm(qb)) - 1) < 1e-5

    dot = float(np.clip(abs(float(np.dot(qa, qb))), 0., 1.))

    return {
        "rotation_change_deg":
            float(math.degrees(2. * math.acos(dot))),
        "translation_change_m":
            float(np.linalg.norm(ta - tb)),
    }


def pattern_perturbation(xyz, amplitude, pattern_id):
    """Predeclared deterministic patterns, not measured sensor noise."""
    xyz = np.asarray(xyz, dtype=np.float64)

    i = np.arange(
        1, len(xyz) + 1, dtype=np.float64
    )[:, None]

    j = np.arange(
        1, 4, dtype=np.float64
    )[None, :]

    p = (
        np.sin(i * j * (pattern_id + 1) * 0.311)
        + 0.55 * np.cos(
            (i + pattern_id * 1.7)
            * (j + 0.4) * 0.679
        )
    )

    p -= p.mean(axis=0, keepdims=True)

    size = float(np.max(np.abs(p)))
    assert size > 0 and np.isfinite(size)

    p /= size
    assert np.max(np.abs(p)) <= 1.00000000001

    return xyz + float(amplitude) * p


def register(previous, current):
    def alarm(_signum, _frame):
        raise TimeoutError(
            "Frozen registration exceeded 5s"
        )

    old = signal.signal(
        signal.SIGALRM, alarm
    )

    signal.setitimer(
        signal.ITIMER_REAL, 5.0
    )

    try:
        result = register_current_scan_to_previous(
            previous, current
        )

        diag = extract_lidar_registration_diagnostics(
            result.diagnostics
        )

        features = {
            f.name: f.value
            for f in diag.features
        }

        assert tuple(features) == (
            "source_point_count",
            "target_point_count",
            "fixed_point_iterations",
            "final_correspondence_count",
            "final_nearest_neighbor_rmse_m",
        )

        return {
            "status": "DIAGNOSTIC_AVAILABLE",
            "pose":
                result.previous_lidar_T_current_lidar.to_dict(),
            "rmse_m":
                float(features[
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
            signal.ITIMER_REAL, 0
        )
        signal.signal(
            signal.SIGALRM, old
        )


def read_run(run, counts, hash_rows):
    root = run / "multimodal_probe_results_v15"

    index = load_json(
        root / "capture_index_v15.json"
    )

    posefile = root / "base_pose_series_v15.jsonl"
    sha(posefile)

    poses = [
        json.loads(line)
        for line in posefile.read_text().splitlines()
        if line.strip()
    ]

    assert len(poses) == 130
    assert [p["step"] for p in poses] == list(range(1, 131))
    assert [r["step"] for r in index] == STEPS
    assert [r["step"] for r in hash_rows] == STEPS
    assert len(index) == len(hash_rows) == 6

    clouds = []

    for i, (row, expected_count, hash_row) in enumerate(
        zip(index, counts, hash_rows), 1
    ):
        step = STEPS[i - 1]
        relative = f"frames_v15/lidar_{i:03d}.npy"

        assert row["lidar_file"] == relative
        assert int(row["lidar_points"]) == expected_count

        path = root / relative

        assert sha(path) == hash_row["cloud_sha256"]

        with path.open("rb") as f:
            xyz = np.load(
                f, allow_pickle=False
            )

        assert xyz.shape == (expected_count, 3)
        assert np.isfinite(xyz).all()

        rawpath = (
            run / "qualified_xyz_v1"
            / f"lidar_xyz_step_{step:03d}.npz"
        )

        sha(rawpath)

        with np.load(
            rawpath, allow_pickle=False
        ) as raw:
            assert np.array_equal(
                xyz, raw["xyz"]
            )

            flags = raw["flags"].astype(np.uint64)

            assert len(flags) == expected_count
            assert np.all((flags & 64) != 0)

            stamp = int(
                raw["timestamp_ns"][0]
            )

        assert row["lidar_rendering_time_raw"] == (
            "GMO_SENSOR_TIMESTAMP_NS:" + str(stamp)
        )

        clouds.append(xyz.copy())

    for row in poses:
        assert row["pose_source"] == (
            "USD_COMPOSED_WORLD_TRANSFORM"
        )
        assert row[
            "physics_pose_independently_verified"
        ] is False

    return clouds, poses


def describe(xs):
    if not xs:
        return {
            "count": 0,
            "median": None,
            "maximum": None,
            "p90": None,
        }

    a = np.asarray(xs, dtype=float)

    assert np.isfinite(a).all()
    assert np.all(a >= 0)

    return {
        "count": len(xs),
        "median": float(statistics.median(xs)),
        "maximum": float(np.max(a)),
        "p90": float(np.percentile(a, 90)),
    }


def derive(clouds_by_type, poses_by_type, l7):
    data = {}

    for condition in ("original", "candidate"):
        clouds = clouds_by_type[condition]
        scripted = poses_by_type[condition]

        baseline_rows = l7[f"{condition}_pairs"]
        assert len(baseline_rows) == 4

        records = []

        for i in range(1, 5):
            steps = [
                STEPS[i - 1], STEPS[i]
            ]

            previous = clouds[i - 1]
            current = clouds[i]

            existing = baseline_rows[i - 1]

            assert [
                existing["previous_step"],
                existing["current_step"],
            ] == steps

            assert existing["baseline_status"] == (
                "DIAGNOSTIC_AVAILABLE"
            )

            base = register(
                previous, current
            )

            assert base["status"] == (
                "DIAGNOSTIC_AVAILABLE"
            )

            original_pose = existing[
                "baseline_pose"
            ]

            comparison = pose_change(
                original_pose, base["pose"]
            )

            assert (
                comparison["translation_change_m"]
                < 1e-8
            )
            assert (
                comparison["rotation_change_deg"]
                < 0.0001
            )

            assert math.isclose(
                base["rmse_m"],
                existing["baseline_rmse_m"],
                rel_tol=1e-8,
                abs_tol=1e-10,
            )

            p0 = np.asarray(
                scripted[steps[0] - 1][
                    "lidar_usd_world_position_m"
                ],
                dtype=float,
            )

            p1 = np.asarray(
                scripted[steps[1] - 1][
                    "lidar_usd_world_position_m"
                ],
                dtype=float,
            )

            assert p0.shape == p1.shape == (3,)
            assert np.isfinite(p0).all()
            assert np.isfinite(p1).all()

            scripted_norm = float(
                np.linalg.norm(p1 - p0)
            )

            candidate_norm = float(
                np.linalg.norm(
                    np.asarray(
                        base["pose"]["translation_m"],
                        dtype=float,
                    )
                )
            )

            challenges = []

            for amplitude in MAGNITUDES:
                for pattern_id in PATTERN_IDS:
                    outcome = register(
                        previous,
                        pattern_perturbation(
                            current,
                            amplitude,
                            pattern_id,
                        ),
                    )

                    change = (
                        pose_change(
                            base["pose"],
                            outcome["pose"],
                        )
                        if outcome["pose"] is not None
                        else None
                    )

                    challenges.append({
                        "amplitude_m": amplitude,
                        "pattern_id": pattern_id,
                        "status": outcome["status"],
                        "error_type": outcome["error"],
                        "pose_delta": change,
                        "nearest_neighbor_rmse_m":
                            outcome["rmse_m"],
                        "noise_calibrated": False,
                    })

            records.append({
                "steps": steps,
                "baseline_rmse_m": base["rmse_m"],
                "baseline_translation_norm_m":
                    candidate_norm,
                "scripted_usd_lidar_displacement_norm_m":
                    scripted_norm,
                "scripted_usd_is_independent_ground_truth":
                    False,
                "challenges": challenges,
                "factor_authorized": False,
            })

        data[condition] = records

    summaries = []

    for amplitude in MAGNITUDES:
        pair_records = []

        for i in range(4):
            a = data["original"][i]
            b = data["candidate"][i]

            for row in (a, b):
                assert len(
                    row["challenges"]
                ) == (
                    len(MAGNITUDES)
                    * len(PATTERN_IDS)
                )

            changes_a = {
                c["pattern_id"]: c
                for c in a["challenges"]
                if c["amplitude_m"] == amplitude
            }

            changes_b = {
                c["pattern_id"]: c
                for c in b["challenges"]
                if c["amplitude_m"] == amplitude
            }

            assert set(changes_a) == set(changes_b) == (
                set(PATTERN_IDS)
            )

            comparable = []
            original_failure = 0
            candidate_failure = 0

            for pattern_id in PATTERN_IDS:
                x = changes_a[pattern_id]
                y = changes_b[pattern_id]

                if x["pose_delta"] is None:
                    original_failure += 1

                if y["pose_delta"] is None:
                    candidate_failure += 1

                if (
                    x["pose_delta"] is not None
                    and y["pose_delta"] is not None
                ):
                    comparable.append({
                        "pattern_id": pattern_id,
                        "original_rotation_deg":
                            x["pose_delta"][
                                "rotation_change_deg"
                            ],
                        "candidate_rotation_deg":
                            y["pose_delta"][
                                "rotation_change_deg"
                            ],
                        "original_translation_m":
                            x["pose_delta"][
                                "translation_change_m"
                            ],
                        "candidate_translation_m":
                            y["pose_delta"][
                                "translation_change_m"
                            ],
                    })

            pair_records.append({
                "steps": a["steps"],
                "comparable_count": len(comparable),
                "original_failures": original_failure,
                "candidate_failures": candidate_failure,
                "original_rotation": describe([
                    x["original_rotation_deg"]
                    for x in comparable
                ]),
                "candidate_rotation": describe([
                    x["candidate_rotation_deg"]
                    for x in comparable
                ]),
                "original_translation": describe([
                    x["original_translation_m"]
                    for x in comparable
                ]),
                "candidate_translation": describe([
                    x["candidate_translation_m"]
                    for x in comparable
                ]),
                "candidate_lower_rotation_count": sum(
                    x["candidate_rotation_deg"]
                    < x["original_rotation_deg"]
                    for x in comparable
                ),
            })

        summaries.append({
            "amplitude_m": amplitude,
            "pairs": pair_records,
        })

    return {
        "records": data,
        "pair_summaries": summaries,
    }


def main():
    assert len(sys.argv) == 7

    original, candidate, l1p, l6p, l7p, out = map(
        Path, sys.argv[1:]
    )

    assert out.is_dir() and not out.is_symlink()

    l1 = load_json(l1p)
    l6 = load_json(l6p)
    l7 = load_json(l7p)

    assert l1["source_steps"] == STEPS
    assert l1["source_point_counts"] == (
        COUNTS["original"]
    )
    assert l6["actual_lidar_point_counts"] == (
        COUNTS["candidate"]
    )
    assert l6["pose_factors_authorized"] == 0
    assert l7[
        "scientifically_qualified_pose_factors"
    ] == 0
    assert l7[
        "deterministic_rederivation_identical"
    ] is True
    assert l7[
        "frozen_original_l2_control_reproduced"
    ] is True

    original_hashes = [
        {
            "step": r["step"],
            "cloud_sha256": r["lidar_file_sha256"],
        }
        for r in l1["scan_geometry"]
    ]

    candidate_hashes = l6["actual_frames"]

    clouds0, poses0 = read_run(
        original,
        COUNTS["original"],
        original_hashes,
    )

    clouds1, poses1 = read_run(
        candidate,
        COUNTS["candidate"],
        candidate_hashes,
    )

    def run_once():
        return derive(
            {
                "original": clouds0,
                "candidate": clouds1,
            },
            {
                "original": poses0,
                "candidate": poses1,
            },
            l7,
        )

    first = run_once()
    second = run_once()

    assert canonical(first) == canonical(second)
    assert len(first["records"]["original"]) == 4
    assert len(first["records"]["candidate"]) == 4
    assert len(first["pair_summaries"]) == 2

    report = {
        "schema":
            "TRUST_ROBOT_L8_V16_MULTIPATTERN_REGISTRATION_DIAGNOSTICS_V1",
        "source_l1_sha256": sha(l1p),
        "source_l6_sha256": sha(l6p),
        "source_l7_sha256": sha(l7p),
        "implementation_sha256":
            sha(Path(__file__)),
        "pattern_ids": list(PATTERN_IDS),
        "synthetic_perturbations_m":
            list(MAGNITUDES),
        "total_perturbation_registrations_per_derivation":
            192,
        "repeated_derivations_identical": True,
        "scripted_usd_is_independent_reference": False,
        "sensor_noise_calibrated": False,
        "cross_sensor_sync_verified": False,
        "ate_or_rpe_computed": False,
        "health_supervision_generated": False,
        "pose_factors_authorized": 0,
        "sparse_final_pair_registered": False,
        **first,
    }

    target = (
        out / "l8_multipattern_registration_report_v1.json"
    )

    with target.open("x") as f:
        json.dump(
            report,
            f,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        f.write("\n")

    for condition in ("original", "candidate"):
        for item in first["records"][condition]:
            print(
                "L8_SCRIPTED_MOTION_DIAGNOSTIC=",
                json.dumps({
                    "condition": condition,
                    "steps": item["steps"],
                    "icp_translation_norm_m":
                        item[
                            "baseline_translation_norm_m"
                        ],
                    "usd_scripted_lidar_displacement_norm_m":
                        item[
                            "scripted_usd_lidar_displacement_norm_m"
                        ],
                    "independent_reference": False,
                }, sort_keys=True),
                flush=True,
            )

    for summary in first["pair_summaries"]:
        for item in summary["pairs"]:
            print(
                "L8_PATTERN_PAIR=",
                json.dumps({
                    "amplitude_m":
                        summary["amplitude_m"],
                    **item,
                }, sort_keys=True),
                flush=True,
            )

    print(
        "MULTIPATTERN_CHALLENGES_PER_DERIVATION=192",
        flush=True,
    )
    print(
        "ORIGINAL_AND_CANDIDATE_BASELINES=REPRODUCED",
        flush=True,
    )
    print(
        "REPEATED_DERIVATION=PASS",
        flush=True,
    )
    print(
        "SPARSE_FINAL_PAIR=NOT_REGISTERED",
        flush=True,
    )
    print(
        "QUALIFIED_POSE_FACTORS=0",
        flush=True,
    )
    print(
        "L8_OFFLINE_DIAGNOSTIC=PASS",
        flush=True,
    )
    print(
        "L8_REPORT_SHA256=",
        sha(target),
        flush=True,
    )


if __name__ == "__main__":
    main()
