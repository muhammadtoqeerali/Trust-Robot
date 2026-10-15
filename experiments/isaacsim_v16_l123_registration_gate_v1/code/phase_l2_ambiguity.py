"""L2 synthetic LiDAR registration ambiguity diagnostic.

Frozen Phase-2 and Phase-4 algorithms remain unchanged.
No localization scoring, health supervision or factor authorization.
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

EXPECTED_L1 = (
    "a120e376d7055a19fe5948f0df9b15b8b824399e967583e745da3258c55c553b"
)

FEATURES = (
    "source_point_count",
    "target_point_count",
    "fixed_point_iterations",
    "final_correspondence_count",
    "final_nearest_neighbor_rmse_m",
)

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def load_json(p):
    assert p.is_file() and not p.is_symlink(), str(p)
    return json.loads(p.read_text())

def canonical(value):
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ) + "\n"
    ).encode()

def read_jsonl(p):
    assert p.is_file() and not p.is_symlink(), str(p)
    return [
        json.loads(line)
        for line in p.read_text().splitlines()
        if line.strip()
    ]

def spectrum(xyz):
    q = np.asarray(xyz, dtype=np.float64)

    assert q.ndim == 2 and q.shape[1] == 3
    assert len(q) >= 3 and np.all(np.isfinite(q))

    q = q - q.mean(axis=0)

    singular = np.linalg.svd(
        q, compute_uv=False
    )

    # Rotational normal matrix for locally linearized
    # rigid point-to-point residuals with fixed
    # correspondences. NOT a calibrated covariance.
    h = (
        np.eye(3) * np.sum(q * q)
        - q.T @ q
    )

    eigen = np.linalg.eigvalsh(
        (h + h.T) / 2
    )

    assert eigen[-1] > 0
    assert eigen[0] >= -1e-10

    eigen = np.maximum(eigen, 0.0)

    return {
        "spatial_singular_values_m": [
            float(x) for x in singular
        ],
        "spatial_smallest_to_largest_ratio":
            float(singular[-1] / singular[0]),
        "rotational_information_eigenvalues_m2": [
            float(x) for x in eigen
        ],
        "rotational_information_min_to_max_ratio":
            float(eigen[0] / eigen[-1]),
        "spatial_numeric_rank":
            int(np.linalg.matrix_rank(q)),
        "physical_noise_covariance_known": False,
        "rotation_information_is_calibrated_covariance":
            False,
        "six_dof_observability_verified": False,
    }

def selftest():
    line = np.array([
        [i, 0, 0]
        for i in (-2.0, -1.0, 1.0, 2.0)
    ])

    cube = np.array([
        [x, y, z]
        for x in (-1.0, 1.0)
        for y in (-1.0, 1.0)
        for z in (-1.0, 1.0)
    ])

    a = spectrum(line)
    b = spectrum(cube)

    assert (
        a["rotational_information_min_to_max_ratio"]
        < 1e-12
    )
    assert (
        b["rotational_information_min_to_max_ratio"]
        > 0.9
    )
    assert a["spatial_numeric_rank"] == 1
    assert b["spatial_numeric_rank"] == 3

    print("ROTATIONAL_GEOMETRY_SELFTEST=PASS", flush=True)

def register(previous, current):
    def handler(_signum, _frame):
        raise TimeoutError(
            "bounded frozen registration expired"
        )

    old = signal.signal(
        signal.SIGALRM, handler
    )

    signal.setitimer(
        signal.ITIMER_REAL, 6.0
    )

    try:
        result = register_current_scan_to_previous(
            previous, current
        )

        feat = extract_lidar_registration_diagnostics(
            result.diagnostics
        )

        assert tuple(
            f.name for f in feat.features
        ) == FEATURES

        return {
            "status": "DIAGNOSTIC_AVAILABLE",
            "pose":
                result.previous_lidar_T_current_lidar.to_dict(),
            "features": {
                f.name: f.value
                for f in feat.features
            },
            "error_type": None,
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
            "error_type": type(exc).__name__,
        }

    finally:
        signal.setitimer(
            signal.ITIMER_REAL, 0.0
        )
        signal.signal(
            signal.SIGALRM, old
        )

def perturb(points, amplitude_m):
    x = np.asarray(
        points, dtype=np.float64
    )

    i = (
        np.arange(len(x), dtype=np.float64)[:, None]
        + 1
    )
    k = (
        np.arange(3, dtype=np.float64)[None, :]
        + 1
    )

    pattern = (
        np.sin(i * k * 1.61803398875)
        + 0.5 * np.cos(
            i * (k + 1) * 0.754877666
        )
    )

    pattern -= pattern.mean(
        axis=0, keepdims=True
    )
    pattern /= np.max(np.abs(pattern))

    assert np.max(np.abs(pattern)) <= 1.00000000001

    return (
        x + float(amplitude_m) * pattern
    )

def delta_pose(a, b):
    ta = np.array(
        a["translation_m"], dtype=np.float64
    )
    tb = np.array(
        b["translation_m"], dtype=np.float64
    )

    qa = np.array(
        a["quaternion_wxyz"], dtype=np.float64
    )
    qb = np.array(
        b["quaternion_wxyz"], dtype=np.float64
    )

    assert abs(np.linalg.norm(qa) - 1) < 1e-5
    assert abs(np.linalg.norm(qb) - 1) < 1e-5

    qdot = float(np.clip(
        abs(np.dot(qa, qb)), 0, 1
    ))

    return {
        "translation_change_m":
            float(np.linalg.norm(tb - ta)),
        "rotation_change_deg":
            float(math.degrees(
                2 * math.acos(qdot)
            )),
    }

def derive(clouds, poses, l1):
    baseline = {
        (
            r["previous_step"],
            r["current_step"],
        ): r
        for r in l1["paired_registration"]
        if r["condition"] == "clean"
    }

    assert len(baseline) == 5

    rows = []

    # First four pairs have 16 points per endpoint.
    # The final 4-point endpoint remains rejected.
    for i in range(1, 5):
        prev = clouds[i - 1]
        curr = clouds[i]

        steps = (
            STEPS[i - 1], STEPS[i]
        )

        old = baseline[steps]

        assert old["registration"]["status"] == (
            "FROZEN_DIAGNOSTICS_AVAILABLE"
        )

        clean = register(prev, curr)

        assert clean["status"] == (
            "DIAGNOSTIC_AVAILABLE"
        )

        old_pose = old["registration"][
            "relative_pose_candidate"
        ]

        delta = delta_pose(
            old_pose, clean["pose"]
        )

        assert delta["translation_change_m"] < 1e-9
        assert delta["rotation_change_deg"] < 0.00001

        assert clean["features"][
            "source_point_count"
        ] == len(curr)

        assert clean["features"][
            "target_point_count"
        ] == len(prev)

        usd_prev = np.array(
            poses[steps[0] - 1]["usd_world_position_m"],
            dtype=float,
        )
        usd_curr = np.array(
            poses[steps[1] - 1]["usd_world_position_m"],
            dtype=float,
        )

        challenges = []

        # Synthetic coordinate perturbations for
        # numeric sensitivity only. These amplitudes
        # are NOT measured sensor-noise statistics.
        for amplitude in (0.0005, 0.002):
            outcome = register(
                prev,
                perturb(curr, amplitude),
            )

            change = (
                delta_pose(
                    clean["pose"], outcome["pose"]
                )
                if outcome["pose"] is not None
                else None
            )

            challenges.append({
                "max_per_coordinate_perturbation_m":
                    amplitude,
                "outcome_status": outcome["status"],
                "error_type": outcome["error_type"],
                "candidate_change": change,
                "diagnostic_nearest_neighbor_rmse_m": (
                    float(outcome["features"][
                        "final_nearest_neighbor_rmse_m"
                    ])
                    if outcome["features"] is not None
                    else None
                ),
                "noise_distribution_calibrated": False,
                "pose_factor_authorized": False,
            })

        rows.append({
            "previous_step": steps[0],
            "current_step": steps[1],
            "previous_points": len(prev),
            "current_points": len(curr),
            "rotation_information_previous":
                spectrum(prev),
            "rotation_information_current":
                spectrum(curr),
            "frozen_frontend_baseline_reproduced": True,
            "baseline_icp_rmse_m": float(
                clean["features"][
                    "final_nearest_neighbor_rmse_m"
                ]
            ),
            "baseline_translation_norm_m":
                float(np.linalg.norm(
                    clean["pose"]["translation_m"]
                )),
            "usd_scripted_base_displacement_norm_m":
                float(np.linalg.norm(
                    usd_curr - usd_prev
                )),
            "usd_is_independent_reference": False,
            "sensitivity_challenges": challenges,
            "rigid_transform_scientifically_qualified":
                False,
            "pose_factor_authorized": False,
        })

    return rows

def main():
    assert len(sys.argv) == 5, (
        "usage: L2.py RUN L1_REPORT SOURCE_REPORT NEW_OUT"
    )

    run, l1_path, source_report, out = map(
        Path, sys.argv[1:]
    )

    assert run.is_dir() and not run.is_symlink()
    assert out.is_dir() and not out.is_symlink()

    assert sha(l1_path) == EXPECTED_L1

    l1 = load_json(l1_path)
    evidence = load_json(source_report)

    assert l1["offline_implementation_pass"]
    assert l1["repeat_derivation_identical"]
    assert l1["source_steps"] == STEPS
    assert l1["source_point_counts"] == COUNTS
    assert l1["pair_attempts"] == 10
    assert l1["frozen_diagnostics_available"] == 8
    assert l1["sparse_pairs_rejected"] == 2
    assert l1["health_labels_generated"] is False

    assert evidence[
        "offline_sensor_file_validation_pass"
    ] is True

    assert evidence["selected_steps"] == STEPS

    root = run / "multimodal_probe_results_v15"

    frames = load_json(
        root / "capture_index_v15.json"
    )
    poses = read_jsonl(
        root / "base_pose_series_v15.jsonl"
    )

    assert len(frames) == 6
    assert len(poses) == 130
    assert [f["step"] for f in frames] == STEPS

    reference = {
        r["step"]: r
        for r in l1["scan_geometry"]
    }

    clouds = []

    for i, (step, n) in enumerate(
        zip(STEPS, COUNTS), start=1
    ):
        assert frames[i - 1]["lidar_file"] == (
            f"frames_v15/lidar_{i:03d}.npy"
        )

        path = root / frames[i - 1]["lidar_file"]

        assert path.is_file() and not path.is_symlink()
        assert sha(path) == reference[step][
            "lidar_file_sha256"
        ]

        xyz = np.load(
            path, allow_pickle=False
        )

        assert xyz.shape == (n, 3)
        assert np.isfinite(xyz).all()

        clouds.append(xyz)

    selftest()

    first = derive(clouds, poses, l1)
    second = derive(clouds, poses, l1)

    assert canonical(first) == canonical(second)
    assert len(first) == 4
    assert all(
        not r["pose_factor_authorized"]
        for r in first
    )

    sparse = {
        "step_pair": [91, 101],
        "status": "REJECTED_BY_L1_SPARSE_ENDPOINT",
        "current_point_count": 4,
        "pose_factor_authorized": False,
    }

    report = {
        "schema":
            "TRUST_ROBOT_L2_V16_SYNTHETIC_REGISTRATION_AMBIGUITY_V1",
        "source_l1_report_sha256": sha(l1_path),
        "source_v16_evidence_sha256":
            sha(source_report),
        "implementation_sha256":
            sha(Path(__file__)),
        "geometry_summary": [
            {"step": step, **spectrum(xyz)}
            for step, xyz in zip(STEPS, clouds)
        ],
        "clean_pairs_analyzed": first,
        "sparse_pair": sparse,
        "deterministic_two_derivations_identical":
            True,
        "frozen_phase2_and_phase4_unchanged": True,
        "synthetic_perturbations_are_calibrated_noise":
            False,
        "pose_factors_accepted": 0,
        "health_supervision_labels_emitted": 0,
        "model_training_authorized": False,
        "cross_sensor_sync_verified": False,
        "independent_ground_truth_verified": False,
        "localization_ate_rpe_computed": False,
        "engineering_audit_complete": True,
    }

    dest = out / "l2_registration_ambiguity_report_v1.json"

    with dest.open("x") as f:
        json.dump(
            report, f,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        f.write("\n")

    for row in report["geometry_summary"]:
        print(
            "GEOMETRY_INFORMATION=",
            json.dumps({
                "step": row["step"],
                "point_count": COUNTS[
                    STEPS.index(row["step"])
                ],
                "singular_ratio":
                    row["spatial_smallest_to_largest_ratio"],
                "rotation_information_ratio":
                    row["rotational_information_min_to_max_ratio"],
            }, sort_keys=True),
        )

    for row in first:
        print(
            "L2_PAIR=",
            json.dumps({
                "steps": [
                    row["previous_step"],
                    row["current_step"],
                ],
                "baseline_icp_rmse_m":
                    row["baseline_icp_rmse_m"],
                "baseline_translation_norm_m":
                    row["baseline_translation_norm_m"],
                "scripted_usd_base_displacement_norm_m":
                    row["usd_scripted_base_displacement_norm_m"],
                "stress": row["sensitivity_challenges"],
            }, sort_keys=True),
        )

    print("FROZEN_L1_BASELINES_REPRODUCED=4")
    print("SPARSE_FINAL_PAIR=NOT_REGISTERED")
    print("REPEAT_DERIVATION_IDENTICAL=PASS")
    print("QUALIFIED_POSE_FACTORS=0")
    print("L2_OFFLINE_AUDIT=PASS")
    print("L2_REPORT_SHA256=", sha(dest))

if __name__ == "__main__":
    main()
