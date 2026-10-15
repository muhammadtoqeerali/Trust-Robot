"""Offline 6-scan all-pairs ICP and scripted trajectory consistency.

Synthetic engineering only. No independent ground truth,
calibrated noise, verified exposure time, health labels,
or estimator factor authorization.
"""

import hashlib
import json
import math
import signal
import statistics
import sys
from itertools import combinations
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


def stable(value):
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ) + "\n"
    ).encode()


def mat(pose):
    t = np.asarray(
        pose["translation_m"],
        dtype=float,
    )

    q = np.asarray(
        pose["quaternion_wxyz"],
        dtype=float,
    )

    assert t.shape == (3,)
    assert q.shape == (4,)

    assert np.isfinite(t).all()
    assert np.isfinite(q).all()

    assert abs(
        float(np.linalg.norm(q)) - 1
    ) < 1e-5

    a = np.eye(4)

    a[:3, :3] = Rotation.from_quat([
        q[1], q[2], q[3], q[0]
    ]).as_matrix()

    a[:3, 3] = t

    return a


def inv(a):
    b = np.eye(4)

    b[:3, :3] = a[:3, :3].T
    b[:3, 3] = -b[:3, :3] @ a[:3, 3]

    return b


def error(a):
    assert np.isfinite(a).all()

    return {
        "translation_m": float(
            np.linalg.norm(a[:3, 3])
        ),

        "rotation_deg": float(
            np.degrees(
                Rotation.from_matrix(
                    a[:3, :3]
                ).magnitude()
            )
        ),
    }


def selftest():
    q = Rotation.from_euler(
        "xyz",
        [0.13, 0.24, -0.17],
    ).as_quat()

    a = mat({
        "translation_m": [0.17, -0.06, 0.23],
        "quaternion_wxyz": [
            q[3], q[0], q[1], q[2]
        ],
    })

    identity = error(a @ inv(a))

    assert identity["translation_m"] < 1e-12
    assert identity["rotation_deg"] < 1e-8

    altered = a.copy()
    altered[0, 3] += 0.025

    detected = error(
        inv(a) @ altered
    )

    assert abs(
        detected["translation_m"] - 0.025
    ) < 1e-12

    print(
        "L16_SE3_SELFTEST_AND_NEGATIVE_CONTROL=PASS",
        flush=True,
    )


def register(previous, current):
    def alarm(_signum, _frame):
        raise TimeoutError(
            "Registration time exceeded"
        )

    old = signal.signal(
        signal.SIGALRM,
        alarm,
    )

    signal.setitimer(
        signal.ITIMER_REAL,
        5,
    )

    try:
        result = register_current_scan_to_previous(
            previous,
            current,
        )

        diag = (
            extract_lidar_registration_diagnostics(
                result.diagnostics
            )
        )

        features = {
            f.name: f.value
            for f in diag.features
        }

        assert tuple(features) == FEATURES

        return {
            "status": "DIAGNOSTIC_AVAILABLE",

            "pose":
                result.previous_lidar_T_current_lidar.to_dict(),

            "rmse_m": float(
                features[
                    "final_nearest_neighbor_rmse_m"
                ]
            ),

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


def inputs(run, l15):
    root = (
        run / "multimodal_probe_results_v15"
    )

    index = load(
        root / "capture_index_v15.json"
    )

    summary = load(
        root / "summary_v1.json"
    )

    assert summary["sequence_lidar_frames"] == 6
    assert summary["sequence_camera_frames"] == 6
    assert summary["usd_pose_samples"] == 130

    assert [
        int(f["step"]) for f in index
    ] == STEPS

    assert [
        int(f["lidar_points"]) for f in index
    ] == [16] * 6

    provenance = l15["scan_file_provenance"]

    assert [
        p["step"] for p in provenance
    ] == STEPS

    scans = []

    for i, (step, row, p) in enumerate(
        zip(STEPS, index, provenance),
        start=1,
    ):
        assert p["count"] == 16

        assert row["lidar_file"] == (
            f"frames_v15/lidar_{i:03d}.npy"
        )

        path = root / row["lidar_file"]

        assert sha(path) == p["cloud_sha256"]

        with path.open("rb") as stream:
            cloud = np.load(
                stream,
                allow_pickle=False,
            )

        assert cloud.shape == (16, 3)
        assert np.isfinite(cloud).all()

        rawpath = (
            run / "qualified_xyz_v1"
            / f"lidar_xyz_step_{step:03d}.npz"
        )

        assert sha(rawpath) == (
            p["qualified_xyz_sha256"]
        )

        with np.load(
            rawpath,
            allow_pickle=False,
        ) as raw:
            assert np.array_equal(
                raw["xyz"],
                cloud,
            )

            flags = raw["flags"].astype(
                np.uint64
            )

            assert len(flags) == 16
            assert np.all((flags & 64) != 0)

            assert int(
                raw["frame_id"][0]
            ) == p["gmo_frame_id"]

            assert int(
                raw["timestamp_ns"][0]
            ) == p["gmo_timestamp_ns_unqualified"]

        scans.append(cloud)

    posepath = (
        root / "base_pose_series_v15.jsonl"
    )

    pose_sha = sha(posepath)

    rows = [
        json.loads(line)
        for line in posepath.read_text().splitlines()
        if line.strip()
    ]

    assert len(rows) == 130

    assert [
        int(x["step"]) for x in rows
    ] == list(range(1, 131))

    assert all(
        x["pose_source"]
        == "USD_COMPOSED_WORLD_TRANSFORM"
        for x in rows
    )

    assert all(
        x["physics_pose_independently_verified"]
        is False
        for x in rows
    )

    usd = []

    for step in STEPS:
        xyz = np.asarray(
            rows[step - 1][
                "lidar_usd_world_position_m"
            ],
            dtype=float,
        )

        assert xyz.shape == (3,)
        assert np.isfinite(xyz).all()

        usd.append(xyz)

    return scans, usd, pose_sha


def derive(scans, usd, l15):
    attempts = {}

    # 6 scans produce 15 unordered pairs.
    for i, j in combinations(range(6), 2):
        attempts[(i, j)] = register(
            scans[i],
            scans[j],
        )

    assert len(attempts) == 15

    # Reproduce the five validated L15 baselines.
    for i in range(5):
        actual = attempts[(i, i + 1)]
        prior = l15["forward"][i]

        assert actual["status"] == (
            prior["status"]
        ) == "DIAGNOSTIC_AVAILABLE"

        assert math.isclose(
            actual["rmse_m"],
            prior["rmse_m"],
            rel_tol=1e-8,
            abs_tol=1e-10,
        )

        delta = error(
            inv(mat(prior["pose"]))
            @ mat(actual["pose"])
        )

        assert delta["translation_m"] < 1e-8
        assert delta["rotation_deg"] < 1e-4

    # Compose the five relative transforms,
    # anchoring the synthetic chain at step 51.
    chain = [np.eye(4)]

    for i in range(5):
        chain.append(
            chain[-1]
            @ mat(
                attempts[(i, i + 1)]["pose"]
            )
        )

    cumulative = []

    for j in range(1, 6):
        norm = float(
            np.linalg.norm(
                chain[j][:3, 3]
            )
        )

        usd_norm = float(
            np.linalg.norm(
                usd[j] - usd[0]
            )
        )

        cumulative.append({
            "from_step": STEPS[0],
            "to_step": STEPS[j],

            "chain_translation_norm_m": norm,

            "scripted_usd_displacement_norm_m":
                usd_norm,

            "absolute_norm_difference_m":
                abs(norm - usd_norm),

            "chain_rotation_relative_to_initial_deg":
                error(chain[j])["rotation_deg"],

            "scripted_usd_is_independent_ground_truth":
                False,
        })

    records = []

    for (i, j), reg in attempts.items():
        composed = (
            chain[j]
            if i == 0
            else inv(chain[i]) @ chain[j]
        )

        discrepancy = (
            error(
                inv(mat(reg["pose"]))
                @ composed
            )
            if reg["pose"] is not None
            else None
        )

        scripted_norm = float(
            np.linalg.norm(
                usd[j] - usd[i]
            )
        )

        direct_norm = (
            float(np.linalg.norm(
                mat(reg["pose"])[:3, 3]
            ))
            if reg["pose"] is not None
            else None
        )

        records.append({
            "steps": [
                STEPS[i],
                STEPS[j],
            ],

            "hop_count": j - i,

            "status": reg["status"],
            "error_type": reg["error"],

            "rmse_m": reg["rmse_m"],

            "direct_translation_norm_m":
                direct_norm,

            "scripted_usd_displacement_norm_m":
                scripted_norm,

            "absolute_translation_norm_difference_m":
                (
                    abs(direct_norm - scripted_norm)
                    if direct_norm is not None
                    else None
                ),

            "direct_vs_composed_se3": (
                discrepancy
                if j - i > 1
                else None
            ),

            "pose_factor_authorized": False,
        })

    by_hop = []

    for hop in range(1, 6):
        group = [
            r for r in records
            if r["hop_count"] == hop
        ]

        available = [
            r for r in group
            if r["status"]
            == "DIAGNOSTIC_AVAILABLE"
        ]

        closures = [
            r["direct_vs_composed_se3"]
            for r in available
            if r["direct_vs_composed_se3"] is not None
        ]

        by_hop.append({
            "hop_count": hop,

            "attempts": len(group),

            "diagnostic_available":
                len(available),

            "registration_unavailable":
                len(group) - len(available),

            "median_rotation_closure_deg": (
                float(statistics.median(
                    x["rotation_deg"]
                    for x in closures
                ))
                if closures else None
            ),

            "max_rotation_closure_deg": (
                float(max(
                    x["rotation_deg"]
                    for x in closures
                ))
                if closures else None
            ),

            "median_translation_closure_m": (
                float(statistics.median(
                    x["translation_m"]
                    for x in closures
                ))
                if closures else None
            ),
        })

    return {
        "all_pairs": records,
        "hop_summaries": by_hop,

        "cumulative_scripted_comparison":
            cumulative,

        "fully_composed_translation_norm_m":
            cumulative[-1][
                "chain_translation_norm_m"
            ],

        "scripted_step51_to101_displacement_norm_m":
            cumulative[-1][
                "scripted_usd_displacement_norm_m"
            ],
    }


def main():
    assert len(sys.argv) == 5

    run, l15path, l14path, out = map(
        Path,
        sys.argv[1:],
    )

    assert run.is_dir() and not run.is_symlink()
    assert out.is_dir() and not out.is_symlink()

    l15 = load(l15path)
    l14 = load(l14path)

    assert l15["upstream_l14_sha256"] == sha(
        l14path
    )

    assert l15[
        "deterministic_two_derivations_identical"
    ] is True

    assert l15["pose_factors_authorized"] == 0
    assert l15["health_labels_generated"] == 0

    assert l14["shifted_selected_valid_counts"] == (
        [16] * 6
    )

    assert l14["step101_outcome"] == "RESTORED_16"
    assert l14["pose_factors_authorized"] == 0

    scans, usd, usd_sha = inputs(
        run,
        l15,
    )

    selftest()

    first = derive(
        scans, usd, l15
    )

    second = derive(
        scans, usd, l15
    )

    assert stable(first) == stable(second)

    report = {
        "schema":
            "TRUST_ROBOT_L16_SIX_SCAN_ALL_PAIRS_TRAJECTORY_DIAGNOSTIC_V1",

        "implementation_sha256":
            sha(Path(__file__)),

        "l15_report_sha256":
            sha(l15path),

        "l14_report_sha256":
            sha(l14path),

        "recorded_usd_pose_series_sha256":
            usd_sha,

        "all_pair_attempts_per_derivation": 15,
        "nonadjacent_pair_attempts_per_derivation": 10,

        "consecutive_l15_baselines_reproduced": 5,
        "repeated_derivation_identical": True,

        "kinematic_usd_is_independent_ground_truth":
            False,

        "physical_exposure_synchronization_verified":
            False,

        "calibrated_sensor_noise": False,

        "scientific_localization_ate_rpe_computed":
            False,

        "health_labels_generated": 0,
        "pose_factors_authorized": 0,

        **first,
    }

    target = (
        out / "l16_six_scan_trajectory_diagnostic_v1.json"
    )

    with target.open("x") as stream:
        json.dump(
            report,
            stream,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        stream.write("\n")

    for row in first["hop_summaries"]:
        print(
            "L16_HOP_SUMMARY=",
            json.dumps(row, sort_keys=True),
            flush=True,
        )

    for row in first["all_pairs"]:
        if row["hop_count"] > 1:
            print(
                "L16_DIRECT_VS_CHAIN=",
                json.dumps(row, sort_keys=True),
                flush=True,
            )

    for row in first[
        "cumulative_scripted_comparison"
    ]:
        print(
            "L16_CHAIN_VS_SCRIPTED=",
            json.dumps(row, sort_keys=True),
            flush=True,
        )

    print("L16_TOTAL_PAIR_ATTEMPTS=15")
    print("L16_L15_CONTROLS_REPRODUCED=5")
    print("L16_DETERMINISTIC_REDERIVATION=PASS")
    print("QUALIFIED_POSE_FACTORS=0")
    print("L16_OFFLINE_TRAJECTORY_AUDIT=PASS")

    print(
        "L16_REPORT_SHA256=",
        sha(target),
    )


if __name__ == "__main__":
    main()
