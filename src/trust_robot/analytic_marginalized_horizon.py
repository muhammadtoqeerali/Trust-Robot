"""Development-only longer-horizon marginalized LiDAR-IMU benchmark.

Extends the existing 15D Schur rolling estimator to 12 nodes.
Tests clean, accelerometer-bias, gyro-bias, and multi-frame
LiDAR-outage conditions.

Also compares factor-preserving incremental Schur
elimination against independently assembled linear
full-batch normal equations.

All trajectories and sensor inputs are analytic fixtures.
No measured reference, physical synchronization or health
classification is claimed.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys

from pathlib import Path

import numpy as np
import scipy

from trust_robot.analytic_inertial_15d import (
    A,
    DT,
    G,
    LANDMARKS,
    OMEGA,
    SEED,
    ACCEL_BIAS_INJECTION,
    analytic_truth,
    as_rotation,
    build_lidar_factors,
    score,
)

from trust_robot.analytic_imu_preintegration import preintegrate

from trust_robot.analytic_preintegrated_fusion import (
    factor_whitener,
)

from trust_robot.analytic_marginalized_fusion import (
    canonical,
    estimate_marginalized,
)

from trust_robot.analytic_schur_marginalization import (
    synthetic_initial_anchor,
    marginalize_one,
    finite_difference_linearization,
)

SCHEMA = "TRUST_ROBOT_ANALYTIC_MARGINALIZED_HORIZON_DEV_V1"

NODE_FRAMES = tuple(range(0, 24, 2))
CONDITIONS = (
    "clean",
    "accel_bias",
    "gyro_bias",
    "lidar_outage",
)

GYRO_BIAS_INJECTION = np.array(
    [0.02, -0.012, 0.01],
    dtype=float,
)


def long_fixture(condition):
    if condition not in CONDITIONS:
        raise ValueError("Unknown synthetic condition")

    final_frame = NODE_FRAMES[-1]

    rng = np.random.default_rng(SEED)
    landmarks = rng.uniform(
        -4.0, 4.0, size=(LANDMARKS, 3)
    )
    landmarks[:, 2] += 1.0

    truth = [
        analytic_truth(k)
        for k in range(final_frame + 1)
    ]

    scans = [
        np.ascontiguousarray(
            (landmarks - x[:3])
            @ as_rotation(x).as_matrix(),
            dtype=np.float64,
        )
        for x in truth
    ]

    imu = []

    for k in range(final_frame):
        x = truth[k]
        gyro = OMEGA.copy()
        accel = as_rotation(x).inv().apply(A-G)

        if condition == "accel_bias" and 6 <= k < 15:
            accel = accel + ACCEL_BIAS_INJECTION

        if condition == "gyro_bias" and 8 <= k < 18:
            gyro = gyro + GYRO_BIAS_INJECTION

        imu.append({
            "interval_index": k,
            "dt_s": DT,
            "gyro_rad_s": gyro.tolist(),
            "specific_force_m_s2": accel.tolist(),
            "physical_clock_verified": False,
            "measurement_origin": "ANALYTIC_FIXTURE",
        })

    available = [True] * (final_frame + 1)

    if condition == "lidar_outage":
        for frame in (8, 10, 12, 14):
            available[frame] = False

    fixture = {
        "scans": scans,
        "imu": imu,
        "available": available,
    }

    return fixture, [
        truth[k] for k in NODE_FRAMES
    ]


def long_factors(fixture):
    frames = NODE_FRAMES

    scans = fixture["scans"]
    imu = fixture["imu"]
    available = fixture["available"]

    if (
        len(scans) != frames[-1] + 1
        or len(imu) != frames[-1]
        or len(available) != len(scans)
    ):
        raise ValueError("Incomplete longer-horizon fixture")

    lidar, lidar_count = build_lidar_factors(
        [scans[k] for k in frames],
        [available[k] for k in frames],
    )

    inertial = {}
    indices = []

    for node in range(1, len(frames)):
        a, b = frames[node-1:node+1]
        readings = imu[a:b]

        if len(readings) != b-a:
            raise ValueError("Missing IMU samples")

        if [
            row["interval_index"]
            for row in readings
        ] != list(range(a, b)):
            raise ValueError("IMU sequence gap or duplication")

        pre = preintegrate(readings)

        if not math.isclose(
            pre["total_dt"],
            (b-a)*DT,
            abs_tol=1e-12,
        ):
            raise ValueError("Unexpected IMU time accumulation")

        inertial[node-1, node] = (
            pre,
            factor_whitener(pre),
        )

        indices.extend(range(a, b))

    if indices != list(range(frames[-1])):
        raise ValueError("IMU sample reuse or loss")

    return inertial, lidar, {
        "imu_intervals": len(inertial),
        "unique_imu_sample_count": len(indices),
        "imu_samples_reused": False,
        "lidar_factor_count": lidar_count,
    }


def linear_fullbatch_equivalence():
    """Independent normal-equation comparison with exact linear factors."""
    ids = tuple(range(5))
    step = np.linspace(0.005, 0.05, 15)

    reference = {
        k: k*step for k in ids
    }

    anchor = synthetic_initial_anchor(
        reference[0],
        sigma=0.2,
    )

    edges = {}

    for j in range(1, len(ids)):
        for i in range(max(0, j-2), j):
            shift = (j-i)*step

            if (i, j) == (1, 3):
                shift = shift + 0.015

            edges[i, j] = (
                shift,
                0.3 + 0.05*(j-i),
            )

    def edge_residual(states, key):
        i, j = key
        displacement, sigma = edges[key]

        return (
            states[j] - states[i] - displacement
        ) / sigma

    def from_vector(z):
        return {
            k: z[15*k:15*(k+1)]
            for k in ids
        }

    def full_residual(z):
        states = from_vector(z)

        return np.concatenate(
            [anchor.residual(states)]
            + [
                edge_residual(states, key)
                for key in sorted(edges)
            ]
        )

    linearization = np.concatenate([
        reference[k] for k in ids
    ])

    r, J = finite_difference_linearization(
        full_residual,
        linearization,
    )

    H = J.T @ J
    g = J.T @ r

    # Eliminate nodes 0,1,2 in the independent full batch.
    removed = np.arange(45)
    retained = np.arange(45, 75)

    Hmm = H[np.ix_(removed, removed)]
    Hkm = H[np.ix_(retained, removed)]
    Hmk = H[np.ix_(removed, retained)]

    H_reference = (
        H[np.ix_(retained, retained)]
        - Hkm @ np.linalg.solve(Hmm, Hmk)
    )

    g_reference = (
        g[retained]
        - Hkm @ np.linalg.solve(
            Hmm, g[removed]
        )
    )

    # Independently build incremental priors and account for
    # every consumed / still-active factor exactly once.
    prior = anchor
    live = [0]
    consumed = set()

    for end in range(1, len(ids)):
        live.append(end)

        if len(live) != 3:
            continue

        oldest = live[0]

        incident = [
            key for key in sorted(edges)
            if (
                oldest in key
                and key not in consumed
                and key[1] <= end
            )
        ]

        previous_prior = prior

        def residual_fn(states):
            return np.concatenate(
                [previous_prior.residual(states)]
                + [
                    edge_residual(states, key)
                    for key in incident
                ]
            )

        prior, _ = marginalize_one(
            tuple(live),
            reference,
            residual_fn,
            oldest,
        )

        consumed.update(incident)
        live.pop(0)

    assert live == [3, 4]

    remaining = [
        key for key in sorted(edges)
        if key not in consumed
    ]

    assert remaining == [(3, 4)]

    def final_residual(z):
        states = {
            3: z[:15],
            4: z[15:],
        }

        return np.concatenate(
            [prior.residual(states)]
            + [
                edge_residual(states, key)
                for key in remaining
            ]
        )

    r2, J2 = finite_difference_linearization(
        final_residual,
        np.r_[reference[3], reference[4]],
    )

    H_incremental = J2.T @ J2
    g_incremental = J2.T @ r2

    information_error = float(
        np.max(np.abs(
            H_incremental - H_reference
        ))
    )
    gradient_error = float(
        np.max(np.abs(
            g_incremental - g_reference
        ))
    )

    if information_error > 1e-5 or gradient_error > 1e-5:
        raise ValueError(
            "Incremental Schur differs from full-batch reference"
        )

    return {
        "information_max_abs_error": information_error,
        "gradient_max_abs_error": gradient_error,
        "exact_linear_fullbatch_equivalence": True,
        "consumed_factor_count": len(consumed),
        "remaining_factor_count": len(remaining),
    }


def execute():
    artifacts = {}
    results = {}

    for condition in CONDITIONS:
        fixture, truth = long_fixture(condition)

        records, audit = estimate_marginalized(
            fixture,
            node_frames=NODE_FRAMES,
            factor_factory=long_factors,
        )

        metrics = score(records, truth)

        if len(records) != len(NODE_FRAMES):
            raise ValueError("Incomplete long-horizon trajectory")

        if (
            audit["accepted_window_count"]
            != len(NODE_FRAMES)-1
            or audit["schur_elimination_count"]
            != len(NODE_FRAMES)-2
            or audit["unaccounted_factor_count"] != 0
            or audit["factor_reuse_after_marginalization"]
            is not False
        ):
            raise ValueError(
                "Long-horizon factor ledger mismatch"
            )

        consumed_i = {
            tuple(x) for x in audit["consumed_imu_keys"]
        }
        active_i = {
            tuple(x) for x in audit["remaining_imu_keys"]
        }

        consumed_l = {
            tuple(x) for x in audit["consumed_lidar_keys"]
        }
        active_l = {
            tuple(x) for x in audit["remaining_lidar_keys"]
        }

        original_i, original_l, _ = long_factors(fixture)

        if (
            consumed_i & active_i
            or consumed_l & active_l
            or consumed_i | active_i != set(original_i)
            or consumed_l | active_l != set(original_l)
        ):
            raise ValueError(
                "Independent factor-conservation audit failed"
            )

        if audit["final_live_nodes"] != [
            len(NODE_FRAMES)-2,
            len(NODE_FRAMES)-1,
        ]:
            raise ValueError(
                "Unexpected marginalization tail states"
            )

        filename = (
            f"{condition}_long_horizon_states.jsonl"
        )

        artifacts[filename] = b"".join(
            canonical(row) for row in records
        )

        results[condition] = {
            "fixture_metrics": metrics,
            "accepted_windows": audit[
                "accepted_window_count"
            ],
            "schur_eliminations": audit[
                "schur_elimination_count"
            ],
            "lidar_factors": audit["lidar_factor_count"],
            "imu_factors": audit["imu_intervals"],
            "factor_reuse": False,
            "factor_loss": False,
        }

    if results["clean"]["fixture_metrics"][
        "fixture_position_rmse_m"
    ] >= 1e-3:
        raise ValueError(
            "Clean long-horizon analytic closure failed"
        )

    if (
        results["lidar_outage"]["lidar_factors"]
        >= results["clean"]["lidar_factors"]
    ):
        raise ValueError("LiDAR outage not reflected in factors")

    linear_check = linear_fullbatch_equivalence()

    return artifacts, {
        "schema": SCHEMA,
        "status": "LOCAL_LONG_HORIZON_DEVELOPMENT_VALIDATED",
        "node_frames": list(NODE_FRAMES),
        "condition_names": list(CONDITIONS),
        "window_max_nodes": 3,
        "state_dimension": 15,
        "results": results,
        "fullbatch_linear_schur_check": linear_check,
        "source_hashes_are_development_only": True,
        "analytic_fixture_only": True,
        "reference_passed_to_estimator": False,
        "physical_synchronization_verified": False,
        "sensor_extrinsics_verified": False,
        "physical_observability_proven": False,
        "nonlinear_posterior_consistency_proven": False,
        "health_model_trained": False,
        "factor_conditioning_executed": False,
        "hardware_tested": False,
        "output_sha256": {
            name: hashlib.sha256(blob).hexdigest()
            for name, blob in sorted(artifacts.items())
        },
        "numeric_environment": {
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "scipy": scipy.__version__,
        },
    }


def run(destination):
    if (
        destination.exists()
        or destination.is_symlink()
        or not destination.parent.is_dir()
        or destination.parent.is_symlink()
    ):
        raise ValueError("Unsafe output destination")

    files, manifest = execute()
    again, again_manifest = execute()

    if files != again or manifest != again_manifest:
        raise ValueError(
            "Long-horizon derivation was not deterministic"
        )

    manifest["repeat_derivation_identical"] = True

    destination.mkdir(mode=0o700)

    for name, blob in sorted(files.items()):
        (destination / name).write_bytes(blob)

    (destination / "horizon_manifest_v1.json").write_text(
        json.dumps(
            manifest, indent=2, sort_keys=True
        ) + "\n"
    )

    return manifest


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    manifest = run(args.output)

    for condition in CONDITIONS:
        result = manifest["results"][condition]

        print(
            condition.upper() + "_WINDOW_SOLVES=",
            result["accepted_windows"]
        )
        print(
            condition.upper() + "_SCHUR_ELIMINATIONS=",
            result["schur_eliminations"]
        )
        print(
            condition.upper() + "_POSITION_RMSE_M=",
            round(
                result["fixture_metrics"][
                    "fixture_position_rmse_m"
                ], 8
            )
        )

    print("FULLBATCH_INFORMATION_COMPARISON=PASS")
    print("LONG_HORIZON_FACTOR_CONSERVATION=PASS")
    print("DETERMINISTIC_REPEAT=PASS")
    print("ANALYTIC_MARGINALIZED_HORIZON=PASS")


if __name__ == "__main__":
    main()
