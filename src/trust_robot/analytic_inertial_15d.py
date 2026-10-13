"""Development-only 15D rolling-state LiDAR/inertial prototype.

State = position(3), SO3 rotation-vector(3), velocity(3),
        gyro bias(3), accelerometer bias(3).

Inertial factors use discrete start-orientation integration.
They are not covariance-propagated IMU preintegration.

The initial velocity and zero-bias calibration are declared
synthetic development assumptions, not physical observations.
No independent sensor reference or real health labels.
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
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation

from trust_robot.clean_backbone import PoseSE3
from trust_robot.analytic_se3_geometry_benchmark import (
    register_bounded,
)
from trust_robot.diagnostics import (
    extract_lidar_registration_diagnostics,
)
from trust_robot.factor_conditioning import (
    assert_factor_scale_execution_authorized,
    FactorConditioningContractError,
)
from trust_robot.auxiliary_consistency import (
    assert_consistency_execution_authorized,
    AuxiliaryConsistencyContractError,
)

SCHEMA = "TRUST_ROBOT_ANALYTIC_INERTIAL_15D_V1"

N = 9
DT = 0.1
WINDOW = 3
LANDMARKS = 80
SEED = 20261012
CONDITIONS = ("clean", "accel_bias", "lidar_dropout")

G = np.array([0.0, 0.0, -9.81])
V0 = np.array([0.25, 0.04, -0.02])
A = np.array([0.025, 0.015, 0.035])
OMEGA = np.array([0.025, -0.020, 0.045])
ACCEL_BIAS_INJECTION = np.array([0.35, -0.10, 0.20])

# Fixed mathematical test residual scales, not learned weights
# or independently measured covariance estimates.
SIGMA_LIDAR_P = 0.02
SIGMA_LIDAR_R = 0.02
SIGMA_IMU_P = 0.05
SIGMA_IMU_V = 0.10
SIGMA_IMU_R = 0.08
SIGMA_GYRO_BIAS_CONTINUITY = 0.20
SIGMA_ACCEL_BIAS_CONTINUITY = 0.50


def canonical(obj):
    return (
        json.dumps(
            obj,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ) + "\n"
    ).encode("utf-8")


def as_rotation(x):
    return Rotation.from_rotvec(
        np.asarray(x[3:6], dtype=np.float64)
    )


def as_pose(x):
    qx, qy, qz, qw = as_rotation(x).as_quat()
    return PoseSE3(
        tuple(float(v) for v in x[:3]),
        (float(qw), float(qx), float(qy), float(qz)),
    )


def initial_state():
    x = np.zeros(15, dtype=np.float64)
    x[6:9] = V0
    return x


def analytic_truth(k):
    """Manufactured state; never accepted as estimator input."""
    t = k * DT
    x = np.zeros(15, dtype=np.float64)
    x[:3] = V0 * t + 0.5 * A * t * t
    x[3:6] = OMEGA * t
    x[6:9] = V0 + A * t
    return x


def make_fixture(condition):
    if condition not in CONDITIONS:
        raise ValueError("Invalid fixture condition")

    rng = np.random.default_rng(SEED)
    landmarks = rng.uniform(
        -4.0, 4.0, size=(LANDMARKS, 3)
    )
    landmarks[:, 2] += 1.0

    truth = [analytic_truth(k) for k in range(N)]

    scans = []
    for x in truth:
        R = as_rotation(x)
        scans.append(
            np.ascontiguousarray(
                (landmarks - x[:3]) @ R.as_matrix(),
                dtype=np.float64,
            )
        )

    imu = []
    for k in range(N - 1):
        x = truth[k]
        R = as_rotation(x)

        gyro = OMEGA.copy()
        specific_force = R.inv().apply(A - G)

        if condition == "accel_bias" and 3 <= k <= 5:
            specific_force = (
                specific_force + ACCEL_BIAS_INJECTION
            )

        imu.append({
            "interval_index": k,
            "dt_s": DT,
            "gyro_rad_s": gyro.tolist(),
            "specific_force_m_s2": specific_force.tolist(),
            "physical_clock_verified": False,
            "measurement_origin": "ANALYTIC_FIXTURE",
        })

    available = [True] * N
    if condition == "lidar_dropout":
        available[4] = False

    return {
        "scans": scans,
        "imu": imu,
        "available": available,
    }, truth


def predict_imu(previous, measurement):
    """First-order discrete synthetic inertial propagation."""
    previous = np.asarray(previous, dtype=np.float64)
    if previous.shape != (15,):
        raise ValueError("Invalid previous state")

    dt = float(measurement["dt_s"])
    if not 0 < dt <= 0.2:
        raise ValueError("Invalid inertial interval")

    gyro = np.asarray(
        measurement["gyro_rad_s"], dtype=np.float64
    )
    accel = np.asarray(
        measurement["specific_force_m_s2"], dtype=np.float64
    )

    if (
        gyro.shape != (3,) or accel.shape != (3,)
        or not np.isfinite(gyro).all()
        or not np.isfinite(accel).all()
    ):
        raise ValueError("Invalid IMU measurement")

    R = as_rotation(previous)
    omega_unbiased = gyro - previous[9:12]
    accel_world = R.apply(
        accel - previous[12:15]
    ) + G

    updated = previous.copy()
    updated[:3] = (
        previous[:3]
        + previous[6:9] * dt
        + 0.5 * accel_world * dt * dt
    )
    updated[6:9] = (
        previous[6:9] + accel_world * dt
    )
    updated[3:6] = (
        R * Rotation.from_rotvec(omega_unbiased * dt)
    ).as_rotvec()

    return updated


def imu_residual(previous, current, measurement):
    dt = float(measurement["dt_s"])
    expected = predict_imu(previous, measurement)

    expected_R = as_rotation(expected)
    current_R = as_rotation(current)

    rotation_error = (
        expected_R.inv() * current_R
    ).as_rotvec()

    return np.concatenate((
        (current[:3] - expected[:3]) / SIGMA_IMU_P,
        (current[6:9] - expected[6:9]) / SIGMA_IMU_V,
        rotation_error / SIGMA_IMU_R,
        (current[9:12] - previous[9:12])
        / SIGMA_GYRO_BIAS_CONTINUITY,
        (current[12:15] - previous[12:15])
        / SIGMA_ACCEL_BIAS_CONTINUITY,
    ))


def lidar_residual(previous, current, observed):
    predicted = (
        as_pose(previous).inverse().compose(as_pose(current))
    )
    error = observed.inverse().compose(predicted)
    q = error.quaternion_wxyz
    rotation = Rotation.from_quat(
        [q[1], q[2], q[3], q[0]]
    )
    return np.concatenate((
        np.asarray(error.translation_m) / SIGMA_LIDAR_P,
        rotation.as_rotvec() / SIGMA_LIDAR_R,
    ))


def build_lidar_factors(scans, available):
    factors = {}
    diagnostic_count = 0

    for j in range(1, len(scans)):
        for i in range(max(0, j - 2), j):
            if not (available[i] and available[j]):
                continue

            result = register_bounded(
                scans[i], scans[j], seconds=3.0
            )
            diagnostics = (
                extract_lidar_registration_diagnostics(
                    result.diagnostics
                )
            )
            names = tuple(f.name for f in diagnostics.features)

            if names != (
                "source_point_count",
                "target_point_count",
                "fixed_point_iterations",
                "final_correspondence_count",
                "final_nearest_neighbor_rmse_m",
            ):
                raise ValueError("Frozen LiDAR contract mismatch")

            factors[(i, j)] = (
                result.previous_lidar_T_current_lidar
            )
            diagnostic_count += 1

    return factors, diagnostic_count


def residuals(values, start, end, boundary, imu, lidar):
    if values.shape != (15 * (end - start),):
        raise ValueError("Invalid rolling optimizer dimensions")

    states = {start: boundary}

    for j in range(start + 1, end + 1):
        offset = 15 * (j - start - 1)
        states[j] = values[offset:offset + 15]

    pieces = []

    for j in range(start + 1, end + 1):
        pieces.append(
            imu_residual(states[j-1], states[j], imu[j-1])
        )

    for (i, j), measurement in sorted(lidar.items()):
        if start <= i and j <= end:
            pieces.append(
                lidar_residual(
                    states[i], states[j], measurement
                )
            )

    return np.concatenate(pieces)


def estimate(fixture):
    """Estimator inputs: scans, IMU and declared initial calibration."""
    scans = fixture["scans"]
    imu = fixture["imu"]
    available = fixture["available"]

    if len(scans) != N or len(imu) != N - 1:
        raise ValueError("Incomplete synthetic sensor fixture")

    lidar, lidar_count = build_lidar_factors(
        scans, available
    )

    states = {0: initial_state()}
    windows = []

    for end in range(1, N):
        states[end] = predict_imu(
            states[end-1], imu[end-1]
        )

        start = max(0, end - WINDOW + 1)

        variables = np.concatenate([
            states[j].copy()
            for j in range(start + 1, end + 1)
        ])

        boundary = states[start].copy()

        def objective(v):
            return residuals(
                v, start, end, boundary, imu, lidar
            )

        fit = least_squares(
            objective,
            variables,
            method="trf",
            loss="linear",
            max_nfev=45,
            ftol=1e-10,
            xtol=1e-10,
            gtol=1e-10,
        )

        local_rank = int(
            np.linalg.matrix_rank(fit.jac, tol=1e-7)
        )
        required_rank = len(variables)

        if (
            not fit.success
            or not np.isfinite(fit.x).all()
            or not math.isfinite(float(fit.cost))
            or local_rank != required_rank
        ):
            raise ValueError(
                f"15D numerical window not accepted at {end}"
            )

        for j in range(start + 1, end + 1):
            offset = 15 * (j - start - 1)
            states[j] = fit.x[offset:offset + 15].copy()

        windows.append({
            "window_end_index": end,
            "window_start_index": start,
            "local_jacobian_rank": local_rank,
            "required_rank": required_rank,
            "cost": float(fit.cost),
            "nfev": int(fit.nfev),
            "oldest_state_fixed": True,
            "schur_marginalization_performed": False,
            "local_rank_proves_physical_observability": False,
        })

    outputs = []
    for k in range(N):
        x = states[k]
        outputs.append({
            "index": k,
            "synthetic_time_s": k * DT,
            "position_m": x[:3].tolist(),
            "orientation_quaternion_wxyz": list(
                as_pose(x).quaternion_wxyz
            ),
            "velocity_m_s": x[6:9].tolist(),
            "gyro_bias_rad_s": x[9:12].tolist(),
            "accel_bias_m_s2": x[12:15].tolist(),
            "state_dimension": 15,
            "reference_pose": None,
        })

    return outputs, {
        "window_count": len(windows),
        "accepted_window_count": len(windows),
        "lidar_factor_count": lidar_count,
        "windows": windows,
        "initial_velocity_source": (
            "DECLARED_SYNTHETIC_STARTUP_CALIBRATION"
        ),
        "initial_bias_source": (
            "DECLARED_ZERO_BIAS_DEVELOPMENT_ANCHOR"
        ),
    }


def score(outputs, truth):
    """Fixture truth enters only this post-estimation scoring."""
    p_errors = []
    r_errors = []
    v_errors = []

    for estimated, actual in zip(
        outputs, truth, strict=True
    ):
        p_errors.append(
            float(np.linalg.norm(
                np.asarray(estimated["position_m"])
                - actual[:3]
            ))
        )

        q = estimated["orientation_quaternion_wxyz"]
        R_est = Rotation.from_quat(
            [q[1], q[2], q[3], q[0]]
        )
        r_errors.append(
            float(
                (R_est.inv() * as_rotation(actual)).magnitude()
                * 180.0 / math.pi
            )
        )

        v_errors.append(
            float(np.linalg.norm(
                np.asarray(estimated["velocity_m_s"])
                - actual[6:9]
            ))
        )

    return {
        "fixture_position_rmse_m": float(
            np.sqrt(np.mean(np.square(p_errors)))
        ),
        "fixture_rotation_rmse_deg": float(
            np.sqrt(np.mean(np.square(r_errors)))
        ),
        "fixture_velocity_rmse_m_s": float(
            np.sqrt(np.mean(np.square(v_errors)))
        ),
        "independent_reference": False,
    }


def execute():
    artifacts = {}
    results = {}

    for condition in CONDITIONS:
        fixture, truth = make_fixture(condition)

        estimates, solver = estimate(fixture)
        metrics = score(estimates, truth)

        if len(estimates) != N:
            raise ValueError("Incomplete 15D state sequence")

        if solver["accepted_window_count"] != N - 1:
            raise ValueError("Incomplete optimization sequence")

        artifacts[f"{condition}_15d_states.jsonl"] = (
            b"".join(canonical(x) for x in estimates)
        )
        results[condition] = {
            "fixture_metrics": metrics,
            "solver": solver,
        }

    clean = results["clean"]["fixture_metrics"]

    if (
        clean["fixture_position_rmse_m"] > 1e-4
        or clean["fixture_rotation_rmse_deg"] > 1e-4
        or clean["fixture_velocity_rmse_m_s"] > 1e-4
    ):
        raise ValueError(
            "Clean inertial state fixture regression failed"
        )

    # Frozen scientific permission gates must remain closed.
    try:
        assert_factor_scale_execution_authorized()
    except FactorConditioningContractError:
        pass
    else:
        raise ValueError("Factor authorization unexpectedly opened")

    try:
        assert_consistency_execution_authorized()
    except AuxiliaryConsistencyContractError:
        pass
    else:
        raise ValueError("Consistency authorization unexpectedly opened")

    manifest = {
        "schema": SCHEMA,
        "status": "ANALYTIC_15D_ROLLING_DEVELOPMENT_PASS",
        "state_dimension": 15,
        "state_components": [
            "position_xyz",
            "orientation_rotvec_xyz",
            "velocity_xyz",
            "gyro_bias_xyz",
            "accel_bias_xyz",
        ],
        "frames_per_condition": N,
        "window_length": WINDOW,
        "synthetic_sample_dt_s": DT,
        "landmark_count": LANDMARKS,
        "conditions": list(CONDITIONS),
        "accel_bias_injection_m_s2": (
            ACCEL_BIAS_INJECTION.tolist()
        ),
        "lidar_missing_frame_index": 4,
        "results": results,
        "numeric_environment": {
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "scipy": scipy.__version__,
        },
        "artifact_sha256": {
            name: hashlib.sha256(blob).hexdigest()
            for name, blob in sorted(artifacts.items())
        },
        "frozen_lidar_registration_reused": True,
        "frozen_lidar_diagnostics_reused": True,
        "discrete_imu_factors_implemented": True,
        "bias_continuity_factors_implemented": True,
        "pose_velocity_bias_jointly_optimized": True,
        "initial_velocity_is_externally_observed": False,
        "initial_bias_is_independently_calibrated": False,
        "covariance_aware_preintegration_implemented": False,
        "schur_marginalization_implemented": False,
        "physical_bias_observability_proven": False,
        "real_sensor_calibration_verified": False,
        "real_sensor_synchronization_verified": False,
        "independent_ground_truth_used": False,
        "fixture_reference_passed_to_estimator": False,
        "health_model_trained": False,
        "factor_conditioning_executed": False,
        "physical_robot_contacted": False,
        "full_trust_robot_estimator_complete": False,
    }
    return artifacts, manifest


def run(destination):
    if destination.exists() or destination.is_symlink():
        raise ValueError("Destination already exists")
    if (
        not destination.parent.is_dir()
        or destination.parent.is_symlink()
    ):
        raise ValueError("Unsafe output parent")

    files, manifest = execute()
    files_again, manifest_again = execute()

    if files != files_again or manifest != manifest_again:
        raise ValueError("Non-deterministic 15D development run")

    manifest["repeat_derivation_identical"] = True
    destination.mkdir(mode=0o700)

    for name, blob in sorted(files.items()):
        (destination / name).write_bytes(blob)

    (destination / "inertial_15d_manifest_v1.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
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
            condition.upper() + "_POSITION_RMSE_M=",
            round(
                row["fixture_metrics"][
                    "fixture_position_rmse_m"
                ], 8
            ),
        )
        print(
            condition.upper() + "_ROTATION_RMSE_DEG=",
            round(
                row["fixture_metrics"][
                    "fixture_rotation_rmse_deg"
                ], 8
            ),
        )

    print("FROZEN_LIDAR_FRONTEND=REUSED")
    print("DISCRETE_INERTIAL_FACTORS=PASS")
    print("JOINT_15D_STATE_OPTIMIZATION=PASS")
    print("TRUST_LAYER_GATES=UNCHANGED")
    print("DETERMINISTIC_REPEAT=PASS")
    print("ANALYTIC_INERTIAL_15D=PASS")


if __name__ == "__main__":
    main()
