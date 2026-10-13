"""Development-only covariance-aware IMU preintegration.

State-error ordering:
  delta_position(3), delta_velocity(3), delta_rotation(3),
  delta_gyro_bias(3), delta_accel_bias(3).

SO(3) rotation error uses a right-multiplicative convention.

Noise parameters are declared per-sample / per-sqrt-second
development assumptions. They are NOT empirical physical
sensor calibration results.

This is a reusable inertial mathematics component, not a
complete fixed-lag multimodal estimator.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation

from trust_robot.analytic_inertial_15d import (
    G,
    N,
    analytic_truth,
    as_rotation,
    make_fixture,
)

SCHEMA = "TRUST_ROBOT_ANALYTIC_IMU_PREINTEGRATION_V1"

GYRO_INJECTION = np.array([0.02, -0.012, 0.01])

SIGMAS = {
    "gyro_per_sample": 0.003,
    "accel_per_sample": 0.04,
    "gyro_bias_walk_per_sqrt_s": 0.0001,
    "accel_bias_walk_per_sqrt_s": 0.001,
}

REGULARIZER_STD = 1e-6


def cross(x):
    x = np.asarray(x, dtype=float)

    return np.array([
        [0, -x[2], x[1]],
        [x[2], 0, -x[0]],
        [-x[1], x[0], 0],
    ], dtype=float)


def right_jacobian(phi):
    phi = np.asarray(phi, dtype=float)
    theta = float(np.linalg.norm(phi))
    h = cross(phi)

    if theta < 1e-5:
        return np.eye(3) - 0.5*h + (1.0/6.0)*h@h

    return (
        np.eye(3)
        - (1.0-math.cos(theta))/theta**2*h
        + (theta-math.sin(theta))/theta**3*h@h
    )


def vector3(value, name):
    a = np.asarray(value, dtype=float)

    if a.shape != (3,) or not np.isfinite(a).all():
        raise ValueError("Invalid finite 3-vector: " + name)

    return a


def preintegrate(readings, bg=None, ba=None, sigmas=None):
    """Propagate delta motion, bias Jacobian and covariance.

    The Jacobian ordering is:
      rows = delta_p, delta_v, delta_theta
      cols = delta_bg, delta_ba

    Delta rotation is defined in the starting IMU frame.
    """

    if not readings:
        raise ValueError("Empty IMU integration interval")

    bg = vector3(
        np.zeros(3) if bg is None else bg, "bg"
    )
    ba = vector3(
        np.zeros(3) if ba is None else ba, "ba"
    )

    sigmas = dict(
        SIGMAS if sigmas is None else sigmas
    )

    if (
        set(sigmas) != set(SIGMAS)
        or any(
            not math.isfinite(float(v))
            or float(v) <= 0
            for v in sigmas.values()
        )
    ):
        raise ValueError("Invalid positive IMU noise configuration")

    R = Rotation.identity()
    dv = np.zeros(3)
    dp = np.zeros(3)

    J = np.zeros((9, 6))
    P = np.zeros((15, 15))
    total = 0.0

    for measurement in readings:
        dt = float(measurement["dt_s"])

        if not math.isfinite(dt) or not 0 < dt <= 0.2:
            raise ValueError("Invalid IMU time increment")

        if (
            measurement.get("measurement_origin")
            != "ANALYTIC_FIXTURE"
            or measurement.get("physical_clock_verified")
            is not False
        ):
            raise ValueError(
                "Unqualified physical clock or source"
            )

        gyro = vector3(
            measurement["gyro_rad_s"], "gyro"
        ) - bg

        accel = vector3(
            measurement["specific_force_m_s2"], "accel"
        ) - ba

        rotation = R.as_matrix()
        angle = gyro * dt
        jr = right_jacobian(angle)

        # Linearized error-state propagation matrix.
        A = np.eye(15)

        A[0:3, 3:6] = np.eye(3) * dt
        A[0:3, 6:9] = (
            -0.5 * rotation @ cross(accel) * dt**2
        )
        A[0:3, 12:15] = -0.5 * rotation * dt**2

        A[3:6, 6:9] = (
            -rotation @ cross(accel) * dt
        )
        A[3:6, 12:15] = -rotation * dt

        A[6:9, 6:9] = Rotation.from_rotvec(
            -angle
        ).as_matrix()

        A[6:9, 9:12] = -jr * dt

        # Measurement and bias random-walk noise injection.
        H = np.zeros((15, 12))

        H[0:3, 3:6] = 0.5 * rotation * dt**2
        H[3:6, 3:6] = rotation * dt
        H[6:9, 0:3] = jr * dt

        H[9:12, 6:9] = np.eye(3) * math.sqrt(dt)
        H[12:15, 9:12] = np.eye(3) * math.sqrt(dt)

        q = (
            [sigmas["gyro_per_sample"]**2] * 3
            + [sigmas["accel_per_sample"]**2] * 3
            + [sigmas["gyro_bias_walk_per_sqrt_s"]**2] * 3
            + [sigmas["accel_bias_walk_per_sqrt_s"]**2] * 3
        )

        P = (
            A @ P @ A.T
            + (H * np.asarray(q)[None, :]) @ H.T
        )

        P = 0.5 * (P + P.T)

        # Sensitivity to the two bias linearization points.
        J = A[:9, :9] @ J + A[:9, 9:15]

        dp = (
            dp + dv*dt
            + 0.5*rotation@accel*dt**2
        )
        dv = dv + rotation@accel*dt

        R = R * Rotation.from_rotvec(angle)
        total += dt

    if np.linalg.eigvalsh(P).min() < -1e-12:
        raise ValueError(
            "Nonpositive propagated covariance"
        )

    return {
        "delta_p": dp,
        "delta_v": dv,
        "delta_R": R,
        "jacobian_bias": J,
        "covariance": P,
        "total_dt": total,
        "samples": len(readings),
        "linearization_bg": bg,
        "linearization_ba": ba,
    }


def bias_correct(pre, bg, ba):
    """First-order correction around stored bias linearization."""
    db = np.r_[
        vector3(bg, "bg") - pre["linearization_bg"],
        vector3(ba, "ba") - pre["linearization_ba"],
    ]

    change = pre["jacobian_bias"] @ db

    return {
        "delta_p": pre["delta_p"] + change[:3],
        "delta_v": pre["delta_v"] + change[3:6],
        "delta_R": (
            pre["delta_R"]
            * Rotation.from_rotvec(change[6:9])
        ),
    }


def error_and_whiten(
    pre, state_i, state_j, bg=None, ba=None
):
    """Return 15 residual components.

    Motion residual uses the 9x9 marginal covariance.
    Six bias-walk residuals are whitened separately.

    This is not full correlated 15x15 factor whitening.
    """

    xi = np.asarray(state_i, dtype=float)
    xj = np.asarray(state_j, dtype=float)

    if (
        xi.shape != (15,)
        or xj.shape != (15,)
        or not np.isfinite(xi).all()
        or not np.isfinite(xj).all()
    ):
        raise ValueError("Invalid 15D inertial states")

    bg = xi[9:12] if bg is None else bg
    ba = xi[12:15] if ba is None else ba

    corrected = bias_correct(pre, bg, ba)

    Ri = as_rotation(xi)
    Rj = as_rotation(xj)
    T = pre["total_dt"]

    observed_dp = Ri.inv().apply(
        xj[:3] - xi[:3] - xi[6:9]*T - 0.5*G*T*T
    )

    observed_dv = Ri.inv().apply(
        xj[6:9] - xi[6:9] - G*T
    )

    observed_dR = Ri.inv() * Rj

    residual = np.r_[
        observed_dp - corrected["delta_p"],
        observed_dv - corrected["delta_v"],
        (
            corrected["delta_R"].inv() * observed_dR
        ).as_rotvec(),
    ]

    # Explicit numerical regularizer for short integration
    # intervals whose marginal covariance may be singular.
    C = (
        pre["covariance"][:9, :9]
        + REGULARIZER_STD**2 * np.eye(9)
    )

    whitened = np.linalg.solve(
        np.linalg.cholesky(C), residual
    )

    bias_rw = np.r_[
        (xj[9:12] - xi[9:12])
        / (
            SIGMAS["gyro_bias_walk_per_sqrt_s"]
            * math.sqrt(T)
        ),
        (xj[12:15] - xi[12:15])
        / (
            SIGMAS["accel_bias_walk_per_sqrt_s"]
            * math.sqrt(T)
        ),
    ]

    return np.r_[whitened, bias_rw]


def finite_difference_jacobian(readings, eps=1e-6):
    """Independently differentiate the nonlinear integration."""
    nominal = preintegrate(readings)

    numeric = np.zeros((9, 6))

    for j in range(6):
        plus = np.zeros(6)
        minus = np.zeros(6)

        plus[j] = eps
        minus[j] = -eps

        up = preintegrate(
            readings, plus[:3], plus[3:]
        )
        down = preintegrate(
            readings, minus[:3], minus[3:]
        )

        numeric[:3, j] = (
            up["delta_p"] - down["delta_p"]
        ) / (2*eps)

        numeric[3:6, j] = (
            up["delta_v"] - down["delta_v"]
        ) / (2*eps)

        numeric[6:9, j] = (
            (
                nominal["delta_R"].inv()
                * up["delta_R"]
            ).as_rotvec()
            -
            (
                nominal["delta_R"].inv()
                * down["delta_R"]
            ).as_rotvec()
        ) / (2*eps)

    return float(np.max(np.abs(
        numeric - nominal["jacobian_bias"]
    )))


def canonical(obj):
    return (
        json.dumps(
            obj,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ) + "\n"
    ).encode()


def execute():
    """Score analytic fixture only after preintegration."""
    files = {}
    results = {}

    for condition in (
        "clean", "accel_bias", "gyro_bias"
    ):
        fixture, truth = make_fixture(
            "clean" if condition == "gyro_bias"
            else condition
        )

        imu = [dict(x) for x in fixture["imu"]]

        if condition == "gyro_bias":
            for i in range(3, 6):
                imu[i]["gyro_rad_s"] = (
                    np.asarray(imu[i]["gyro_rad_s"])
                    + GYRO_INJECTION
                ).tolist()

        rows = []
        norms = []
        covariance_traces = []

        for i in range(0, N - 1, 2):
            group = imu[i:i+2]
            pre = preintegrate(group)

            residual = error_and_whiten(
                pre, truth[i], truth[i+2]
            )

            norm = float(
                np.linalg.norm(residual[:9])
            )

            norms.append(norm)
            covariance_traces.append(
                float(np.trace(pre["covariance"]))
            )

            rows.append({
                "condition": condition,
                "start": i,
                "end": i+2,
                "samples": 2,
                "dt_s": pre["total_dt"],
                "delta_position_m": (
                    pre["delta_p"].tolist()
                ),
                "delta_velocity_m_s": (
                    pre["delta_v"].tolist()
                ),
                "delta_rotation_quaternion_xyzw": (
                    pre["delta_R"].as_quat().tolist()
                ),
                "jacobian_bias_9x6": (
                    pre["jacobian_bias"].tolist()
                ),
                "covariance_15x15": (
                    pre["covariance"].tolist()
                ),
                "whitened_motion_residual_norm_at_analytic_truth":
                    norm,
                "analytic_truth_used_by_preintegration":
                    False,
                "analytic_truth_used_for_diagnostic_scoring":
                    True,
            })

        files[condition + "_factors.jsonl"] = (
            b"".join(canonical(r) for r in rows)
        )

        results[condition] = {
            "factors": len(rows),
            "mean_whitened_motion_residual": float(
                np.mean(norms)
            ),
            "max_whitened_motion_residual": float(
                max(norms)
            ),
            "covariance_trace_mean": float(
                np.mean(covariance_traces)
            ),
        }

    if (
        results["clean"]["max_whitened_motion_residual"]
        >= 1e-5
    ):
        raise ValueError(
            "Clean preintegration does not close fixture"
        )

    for condition in ("accel_bias", "gyro_bias"):
        if (
            results[condition][
                "mean_whitened_motion_residual"
            ]
            <= results["clean"][
                "mean_whitened_motion_residual"
            ] + 0.1
        ):
            raise ValueError(
                "Controlled bias effect not observed"
            )

    fixture, _ = make_fixture("clean")
    group = fixture["imu"][:4]

    jac_error = finite_difference_jacobian(group)

    if jac_error > 2e-4:
        raise ValueError(
            "Bias Jacobian finite-difference mismatch"
        )

    p = preintegrate(group)

    sigma4 = {
        key: 4*value
        for key, value in SIGMAS.items()
    }

    larger = preintegrate(
        group, sigmas=sigma4
    )

    covariance_scale_error = float(
        np.max(np.abs(
            larger["covariance"]
            - 16*p["covariance"]
        ))
    )

    if covariance_scale_error > 1e-8:
        raise ValueError(
            "Covariance noise scaling mismatch"
        )

    bias_vector = np.r_[
        GYRO_INJECTION,
        [0.06, -0.02, 0.03],
    ]

    exact = preintegrate(
        group,
        bias_vector[:3],
        bias_vector[3:],
    )

    approximate = bias_correct(
        p,
        bias_vector[:3],
        bias_vector[3:],
    )

    correction_error = float(max(
        np.linalg.norm(
            exact["delta_p"]
            - approximate["delta_p"]
        ),
        np.linalg.norm(
            exact["delta_v"]
            - approximate["delta_v"]
        ),
        (
            exact["delta_R"].inv()
            * approximate["delta_R"]
        ).magnitude(),
    ))

    if correction_error >= 5e-4:
        raise ValueError(
            "First-order bias correction inaccurate"
        )

    manifest = {
        "schema": SCHEMA,
        "status": (
            "SYNTHETIC_PREINTEGRATION_MATHEMATICS_VALIDATED"
        ),
        "results": results,
        "finite_difference_max_abs_jacobian_error":
            jac_error,
        "bias_correction_max_difference":
            correction_error,
        "noise_covariance_scale_max_abs_error":
            covariance_scale_error,
        "parameters": {
            "sample_noise_std_development_only":
                SIGMAS,
            "regularizer_std": REGULARIZER_STD,
            "group_size": 2,
            "gyro_bias_injection_rad_s":
                GYRO_INJECTION.tolist(),
        },
        "numeric_environment": {
            "python": sys.version.split()[0],
            "numpy": np.__version__,
        },
        "output_sha256": {
            key: hashlib.sha256(value).hexdigest()
            for key, value in sorted(files.items())
        },
        "reference_used_by_preintegrator": False,
        "analytic_truth_scoring_only": True,
        "covariance_propagation_15x15": True,
        "first_order_bias_jacobian_9x6": True,
        "physical_noise_calibrated": False,
        "real_sensor_timestamps_verified": False,
        "factor_graph_solver_integrated": False,
        "schur_marginalization_implemented": False,
        "health_model_trained": False,
        "factor_conditioning_executed": False,
        "physical_robot_contacted": False,
        "full_estimator_complete": False,
    }

    return files, manifest


def run(destination):
    if (
        destination.exists()
        or destination.is_symlink()
        or not destination.parent.is_dir()
        or destination.parent.is_symlink()
    ):
        raise ValueError(
            "Unsafe or existing output directory"
        )

    first, manifest = execute()
    second, second_manifest = execute()

    if (
        first != second
        or manifest != second_manifest
    ):
        raise ValueError(
            "Non-deterministic preintegration output"
        )

    manifest["repeat_derivation_identical"] = True

    destination.mkdir(mode=0o700)

    for name, blob in sorted(first.items()):
        (destination / name).write_bytes(blob)

    (destination / "preintegration_manifest_v1.json").write_text(
        json.dumps(
            manifest,
            indent=2,
            sort_keys=True,
        ) + "\n"
    )

    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    result = run(args.output)

    for condition, row in result["results"].items():
        print(
            condition.upper()
            + "_MEAN_WHITENED_RESIDUAL=",
            row["mean_whitened_motion_residual"]
        )

    print("FINITE_DIFFERENCE_BIAS_JACOBIAN=PASS")
    print("COVARIANCE_PROPAGATION=PASS")
    print("BIAS_CORRECTION=PASS")
    print("DETERMINISTIC_REPEAT=PASS")
    print("ANALYTIC_IMU_PREINTEGRATION=PASS")


if __name__ == "__main__":
    main()
