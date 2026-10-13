"""Analytic development-only covariance-whitened LiDAR-IMU fusion.

Uses existing frozen LiDAR registration and newly implemented IMU
preintegration in a rolling 15D nonlinear state estimator.

Estimator nodes are synthetic frames 0,2,4,6,8.
Each two-sample IMU interval is used exactly once per factor.

Full 15x15 inertial covariance whitening is performed with
an explicit numerical covariance floor.

The previous window's oldest state becomes a fixed boundary.
There is no Schur-complement marginalization.

No physical synchronization, measured covariance calibration,
learned reliability weighting, or independent reference.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import scipy

from scipy.linalg import solve_triangular
from scipy.optimize import least_squares

from trust_robot.analytic_inertial_15d import (
    DT,
    G,
    as_pose,
    as_rotation,
    build_lidar_factors,
    initial_state,
    lidar_residual,
    make_fixture,
    predict_imu,
    score,
)

from trust_robot.analytic_imu_preintegration import (
    bias_correct,
    preintegrate,
)

from trust_robot.factor_conditioning import (
    assert_factor_scale_execution_authorized,
    FactorConditioningContractError,
)

from trust_robot.auxiliary_consistency import (
    assert_consistency_execution_authorized,
    AuxiliaryConsistencyContractError,
)

SCHEMA = "TRUST_ROBOT_ANALYTIC_PREINTEGRATED_FUSION_V1"

NODE_FRAMES = (0, 2, 4, 6, 8)
WINDOW_NODES = 3
MAX_NFEV = 60
COVARIANCE_FLOOR_STD = 1e-4

CONDITIONS = (
    "clean",
    "accel_bias",
    "lidar_dropout",
)


def canonical(value):
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ) + "\n"
    ).encode("utf-8")


def factor_whitener(pre):
    """Regularized covariance Cholesky for all 15 error components."""
    P = np.asarray(pre["covariance"], dtype=np.float64)

    if (
        P.shape != (15, 15)
        or not np.isfinite(P).all()
        or not np.allclose(P, P.T, atol=1e-12)
    ):
        raise ValueError("Invalid preintegrated covariance")

    if np.linalg.eigvalsh(P).min() < -1e-12:
        raise ValueError("Indefinite preintegrated covariance")

    regularized = (
        P
        + COVARIANCE_FLOOR_STD**2 * np.eye(15)
    )

    try:
        L = np.linalg.cholesky(regularized)
    except np.linalg.LinAlgError as exc:
        raise ValueError(
            "Cannot whiten inertial factor"
        ) from exc

    return L


def make_factors(fixture):
    """Nonoverlapping inertial intervals plus frozen LiDAR factors."""
    scans = fixture["scans"]
    imu = fixture["imu"]
    available = fixture["available"]

    if (
        len(scans) != 9
        or len(imu) != 8
        or len(available) != 9
    ):
        raise ValueError("Unexpected analytic fixture length")

    node_scans = [scans[k] for k in NODE_FRAMES]
    node_available = [available[k] for k in NODE_FRAMES]

    lidar, lidar_count = build_lidar_factors(
        node_scans,
        node_available,
    )

    inertial = {}
    sample_indices = []

    for node in range(1, len(NODE_FRAMES)):
        first = NODE_FRAMES[node - 1]
        last = NODE_FRAMES[node]

        readings = imu[first:last]

        if len(readings) != 2:
            raise ValueError("Invalid IMU integration interval")

        if [
            reading["interval_index"]
            for reading in readings
        ] != list(range(first, last)):
            raise ValueError("IMU interval sequence mismatch")

        pre = preintegrate(readings)

        if (
            pre["samples"] != 2
            or not math.isclose(
                pre["total_dt"], 2 * DT,
                abs_tol=1e-12,
            )
        ):
            raise ValueError("Unexpected preintegration duration")

        inertial[node-1, node] = (
            pre,
            factor_whitener(pre),
        )

        sample_indices.extend(range(first, last))

    if sample_indices != list(range(8)):
        raise ValueError("IMU sample reuse or omission")

    if len(inertial) != 4:
        raise ValueError("Incomplete inertial factor set")

    return inertial, lidar, {
        "imu_intervals": len(inertial),
        "unique_imu_sample_count": len(sample_indices),
        "imu_samples_reused": False,
        "lidar_factor_count": lidar_count,
    }


def whitened_inertial_residual(xi, xj, factor):
    """Correlated 15D residual in dp,dv,dtheta,dbg,dba order."""
    xi = np.asarray(xi, dtype=np.float64)
    xj = np.asarray(xj, dtype=np.float64)

    if (
        xi.shape != (15,)
        or xj.shape != (15,)
        or not np.isfinite(xi).all()
        or not np.isfinite(xj).all()
    ):
        raise ValueError("Invalid 15D inertial states")

    pre, lower = factor

    corrected = bias_correct(
        pre,
        xi[9:12],
        xi[12:15],
    )

    Ri = as_rotation(xi)
    Rj = as_rotation(xj)
    T = float(pre["total_dt"])

    observed_dp = Ri.inv().apply(
        xj[:3]
        - xi[:3]
        - xi[6:9]*T
        - 0.5*G*T*T
    )

    observed_dv = Ri.inv().apply(
        xj[6:9]
        - xi[6:9]
        - G*T
    )

    observed_dR = Ri.inv() * Rj

    residual = np.concatenate((
        observed_dp - corrected["delta_p"],
        observed_dv - corrected["delta_v"],
        (
            corrected["delta_R"].inv() * observed_dR
        ).as_rotvec(),
        xj[9:12] - xi[9:12],
        xj[12:15] - xi[12:15],
    ))

    if lower.shape != (15, 15):
        raise ValueError("Invalid covariance whitener")

    answer = solve_triangular(
        lower,
        residual,
        lower=True,
        check_finite=False,
    )

    if not np.isfinite(answer).all():
        raise ValueError("Nonfinite whitened residual")

    return answer


def window_residuals(
    variables,
    start,
    end,
    boundary,
    inertial,
    lidar,
):
    n = end - start

    if (
        n < 1
        or n >= WINDOW_NODES
        or np.shape(variables) != (15*n,)
    ):
        raise ValueError("Invalid optimizer state dimension")

    states = {start: boundary}

    for node in range(start+1, end+1):
        offset = 15 * (node-start-1)
        states[node] = variables[
            offset:offset+15
        ]

    residuals = []

    for node in range(start+1, end+1):
        residuals.append(
            whitened_inertial_residual(
                states[node-1],
                states[node],
                inertial[node-1, node],
            )
        )

    for (i, j), measurement in sorted(lidar.items()):
        if i >= start and j <= end:
            residuals.append(
                lidar_residual(
                    states[i],
                    states[j],
                    measurement,
                )
            )

    return np.concatenate(residuals)


def estimate_preintegrated(fixture):
    """Estimator consumes only fixture sensor fields, not truth poses."""
    inertial, lidar, counts = make_factors(fixture)

    states = {0: initial_state()}
    windows = []

    for end in range(1, len(NODE_FRAMES)):
        previous = states[end-1].copy()

        # Previous-state propagation initializes the nonlinear solve.
        # No analytic reference state is read.
        for sample_index in range(
            NODE_FRAMES[end-1],
            NODE_FRAMES[end],
        ):
            previous = predict_imu(
                previous,
                fixture["imu"][sample_index],
            )

        states[end] = previous

        start = max(
            0,
            end - WINDOW_NODES + 1,
        )

        x0 = np.concatenate([
            states[node].copy()
            for node in range(start+1, end+1)
        ])

        boundary = states[start].copy()

        def objective(values):
            return window_residuals(
                values,
                start,
                end,
                boundary,
                inertial,
                lidar,
            )

        fit = least_squares(
            objective,
            x0,
            method="trf",
            loss="linear",
            max_nfev=MAX_NFEV,
            ftol=1e-9,
            xtol=1e-9,
            gtol=1e-9,
        )

        rank = int(
            np.linalg.matrix_rank(
                fit.jac,
                tol=1e-7,
            )
        )

        required_rank = len(x0)

        accepted = (
            bool(fit.success)
            and np.isfinite(fit.x).all()
            and math.isfinite(float(fit.cost))
            and rank == required_rank
        )

        if not accepted:
            raise ValueError(
                f"Preintegrated 15D window unavailable at {end}"
            )

        for node in range(start+1, end+1):
            offset = 15 * (node-start-1)
            states[node] = fit.x[
                offset:offset+15
            ].copy()

        windows.append({
            "end_node": end,
            "start_node": start,
            "accepted": True,
            "jacobian_rank": rank,
            "required_rank": required_rank,
            "cost": float(fit.cost),
            "function_evaluations": int(fit.nfev),
            "boundary_state_fixed": True,
            "schur_marginalization_performed": False,
            "local_rank_proves_physical_observability": False,
        })

    records = []

    for node, frame in enumerate(NODE_FRAMES):
        x = states[node]

        records.append({
            "node_index": node,
            "source_frame_index": frame,
            "synthetic_time_s": frame*DT,
            "position_m": x[:3].tolist(),
            "orientation_quaternion_wxyz": list(
                as_pose(x).quaternion_wxyz
            ),
            "velocity_m_s": x[6:9].tolist(),
            "gyro_bias_rad_s": x[9:12].tolist(),
            "accel_bias_m_s2": x[12:15].tolist(),
            "state_dimension": 15,
            "reference_pose": None,
            "sensor_frame_calibrated": False,
        })

    return records, {
        **counts,
        "window_count": len(windows),
        "accepted_window_count": len(windows),
        "windows": windows,
    }


def execute():
    files = {}
    conditions = {}

    for condition in CONDITIONS:
        fixture, truth = make_fixture(condition)

        estimated, solver = estimate_preintegrated(fixture)
        metrics = score(
            estimated,
            [truth[k] for k in NODE_FRAMES],
        )

        if len(estimated) != len(NODE_FRAMES):
            raise ValueError("Incomplete 15D node trajectory")

        if solver["accepted_window_count"] != 4:
            raise ValueError("Incomplete nonlinear optimization")

        if (
            solver["imu_intervals"] != 4
            or solver["unique_imu_sample_count"] != 8
            or solver["imu_samples_reused"] is not False
        ):
            raise ValueError("Invalid inertial factor provenance")

        name = f"{condition}_preintegrated_states.jsonl"

        files[name] = b"".join(
            canonical(row)
            for row in estimated
        )

        conditions[condition] = {
            "fixture_metrics": metrics,
            "solver": solver,
        }

    clean = conditions["clean"]["fixture_metrics"]

    if (
        clean["fixture_position_rmse_m"] > 1e-4
        or clean["fixture_rotation_rmse_deg"] > 1e-4
        or clean["fixture_velocity_rmse_m_s"] > 1e-4
    ):
        raise ValueError("Clean analytic closure failed")

    assert (
        conditions["lidar_dropout"]["solver"][
            "lidar_factor_count"
        ]
        < conditions["clean"]["solver"][
            "lidar_factor_count"
        ]
    )

    for gate, error_type in (
        (
            assert_factor_scale_execution_authorized,
            FactorConditioningContractError,
        ),
        (
            assert_consistency_execution_authorized,
            AuxiliaryConsistencyContractError,
        ),
    ):
        try:
            gate()
        except error_type:
            pass
        else:
            raise ValueError(
                "Frozen scientific authorization gate changed"
            )

    manifest = {
        "schema": SCHEMA,
        "status": "ANALYTIC_PREINTEGRATED_FUSION_VALIDATED",
        "conditions": list(CONDITIONS),
        "node_frames": list(NODE_FRAMES),
        "node_count_per_condition": len(NODE_FRAMES),
        "window_length_nodes": WINDOW_NODES,
        "imu_samples_per_preintegrated_factor": 2,
        "covariance_floor_std": COVARIANCE_FLOOR_STD,
        "covariance_floor_empirically_calibrated": False,
        "results": conditions,
        "numeric_environment": {
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "scipy": scipy.__version__,
        },
        "artifact_sha256": {
            name: hashlib.sha256(blob).hexdigest()
            for name, blob in sorted(files.items())
        },
        "frozen_lidar_frontend_reused": True,
        "covariance_aware_preintegration_integrated": True,
        "full_correlated_15d_factor_whitening": True,
        "first_order_bias_correction_integrated": True,
        "joint_pose_velocity_bias_optimization": True,
        "nonoverlapping_imu_intervals": True,
        "initial_velocity_independently_observed": False,
        "initial_bias_independently_calibrated": False,
        "independent_ground_truth_used": False,
        "reference_passed_to_estimator": False,
        "physical_synchronization_verified": False,
        "sensor_extrinsics_independently_verified": False,
        "probabilistic_schur_marginalization_implemented": False,
        "health_probabilities_estimated": False,
        "factor_conditioning_executed": False,
        "real_hardware_tested": False,
        "full_trust_robot_estimator_complete": False,
    }

    return files, manifest


def run(destination):
    if (
        destination.exists()
        or destination.is_symlink()
        or not destination.parent.is_dir()
        or destination.parent.is_symlink()
    ):
        raise ValueError("Unsafe output destination")

    first, manifest = execute()
    again, manifest_again = execute()

    if first != again or manifest != manifest_again:
        raise ValueError("Non-deterministic fusion outputs")

    manifest["repeat_derivation_identical"] = True

    destination.mkdir(mode=0o700)

    for filename, content in sorted(first.items()):
        (destination / filename).write_bytes(content)

    (destination / "fusion_manifest_v1.json").write_text(
        json.dumps(
            manifest,
            sort_keys=True,
            indent=2,
        ) + "\n"
    )

    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    result = run(args.output)

    for condition in CONDITIONS:
        row = result["results"][condition]

        print(
            condition.upper() + "_WINDOW_SOLVES=",
            row["solver"]["accepted_window_count"],
        )

        print(
            condition.upper() + "_LIDAR_FACTORS=",
            row["solver"]["lidar_factor_count"],
        )

        print(
            condition.upper() + "_POSITION_RMSE_M=",
            round(
                row["fixture_metrics"]["fixture_position_rmse_m"],
                8,
            ),
        )

        print(
            condition.upper() + "_ROTATION_RMSE_DEG=",
            round(
                row["fixture_metrics"]["fixture_rotation_rmse_deg"],
                8,
            ),
        )

    print("NONOVERLAPPING_IMU_PREINTEGRATION=PASS")
    print("CORRELATED_COVARIANCE_WHITENING=PASS")
    print("BIAS_CORRECTION_IN_OPTIMIZER=PASS")
    print("DETERMINISTIC_REPEAT=PASS")
    print("ANALYTIC_PREINTEGRATED_FUSION=PASS")


if __name__ == "__main__":
    main()
