"""Analytic rolling-estimator robustness and information checks.

Adds strict synthetic sensor-input qualification, controlled
failure injection, a local full-batch nonlinear comparison,
and LiDAR-dropout information diagnostics.

Local inverse-Hessian quantities are regularized linearized
information proxies, NOT calibrated posterior covariances.

All evaluation inputs are synthetic. No independent measured
reference, health classifier or physical robot operation.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import scipy
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation

from trust_robot.analytic_inertial_15d import (
    DT,
    initial_state,
    make_fixture,
    predict_imu,
    lidar_residual,
)
from trust_robot.analytic_preintegrated_fusion import (
    NODE_FRAMES,
    make_factors,
)
from trust_robot.analytic_marginalized_fusion import (
    INITIAL_ANCHOR_SIGMA,
    estimate_marginalized,
    selected_residuals,
)
from trust_robot.analytic_marginalized_horizon import (
    NODE_FRAMES as LONG_FRAMES,
    long_fixture,
    long_factors,
)
from trust_robot.analytic_schur_marginalization import (
    synthetic_initial_anchor,
    finite_difference_linearization,
)

SCHEMA = "TRUST_ROBOT_ANALYTIC_ESTIMATOR_ROBUSTNESS_DEV_V1"

FULL_BATCH_CONDITIONS = ("clean", "accel_bias")
LOCAL_INFORMATION_RIDGE_RELATIVE = 1e-9
MAX_FULL_BATCH_NFEV = 80


def canonical(obj):
    return (
        json.dumps(
            obj,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ) + "\n"
    ).encode("utf-8")


def validate_fixture(
    fixture,
    *,
    node_frames=NODE_FRAMES,
):
    """Fail closed on malformed synthetic sensor records.

    This is a development-fixture admission guard.
    It does NOT validate real-world sensor authenticity.
    """
    if not isinstance(fixture, dict) or set(fixture) != {
        "scans", "imu", "available"
    }:
        raise ValueError("Unexpected fixture fields")

    frames = tuple(node_frames)

    if (
        len(frames) < 3
        or frames[0] != 0
        or any(
            not isinstance(k, int) or k < 0
            for k in frames
        )
        or any(
            b <= a for a, b in zip(frames, frames[1:])
        )
    ):
        raise ValueError("Invalid estimator node chronology")

    scans = fixture["scans"]
    imu = fixture["imu"]
    available = fixture["available"]

    if (
        len(scans) != frames[-1] + 1
        or len(imu) != frames[-1]
        or len(available) != len(scans)
    ):
        raise ValueError("Missing or duplicated sensor records")

    if not all(type(flag) is bool for flag in available):
        raise ValueError("Invalid LiDAR availability indicator")

    for index, cloud in enumerate(scans):
        points = np.asarray(cloud)

        if (
            points.ndim != 2
            or points.shape[1] != 3
            or not np.issubdtype(
                points.dtype,
                np.floating,
            )
            or not np.isfinite(points).all()
        ):
            raise ValueError(
                f"Malformed LiDAR point cloud {index}"
            )

        if available[index] and len(points) < 3:
            raise ValueError(
                f"Insufficient LiDAR points {index}"
            )

    for index, measurement in enumerate(imu):
        if not isinstance(measurement, dict):
            raise ValueError("Malformed IMU record")

        if measurement.get("interval_index") != index:
            raise ValueError("IMU record sequence mismatch")

        dt = float(measurement.get("dt_s", float("nan")))

        if (
            not math.isfinite(dt)
            or not math.isclose(
                dt, DT, rel_tol=0, abs_tol=1e-12
            )
        ):
            raise ValueError("Invalid synthetic IMU time step")

        if (
            measurement.get("physical_clock_verified") is not False
            or measurement.get("measurement_origin")
            != "ANALYTIC_FIXTURE"
        ):
            raise ValueError(
                "Unqualified IMU clock or source"
            )

        for key in ("gyro_rad_s", "specific_force_m_s2"):
            vector = np.asarray(
                measurement.get(key),
                dtype=np.float64,
            )

            if (
                vector.shape != (3,)
                or not np.isfinite(vector).all()
            ):
                raise ValueError(
                    f"Malformed IMU {key} at {index}"
                )

    usable_pairs = [
        (i, j)
        for j in range(1, len(frames))
        for i in range(max(0, j-2), j)
        if available[frames[i]] and available[frames[j]]
    ]

    if not usable_pairs:
        raise ValueError(
            "No usable LiDAR registration pair"
        )

    return {
        "node_count": len(frames),
        "imu_sample_count": len(imu),
        "available_lidar_nodes": sum(
            available[k] for k in frames
        ),
        "potential_lidar_pairs": len(usable_pairs),
        "real_sensor_admission_authorized": False,
    }


def guarded_estimate(
    fixture,
    *,
    node_frames=NODE_FRAMES,
    factor_factory=make_factors,
):
    """Validate before invoking the existing Schur estimator."""
    admission = validate_fixture(
        fixture,
        node_frames=node_frames,
    )

    records, audit = estimate_marginalized(
        fixture,
        node_frames=node_frames,
        factor_factory=factor_factory,
    )

    if (
        len(records) != len(node_frames)
        or audit["unaccounted_factor_count"] != 0
        or audit["factor_reuse_after_marginalization"]
        is not False
    ):
        raise ValueError("Estimator accounting invalid")

    return records, audit, admission


def initial_guess(fixture, frames=NODE_FRAMES):
    """Propagate measured IMU only; no fixture truth input."""
    states = [initial_state()]

    for previous, current in zip(frames, frames[1:]):
        propagated = states[-1].copy()

        for sample in range(previous, current):
            propagated = predict_imu(
                propagated,
                fixture["imu"][sample],
            )

        states.append(propagated)

    return np.concatenate(states)


def unpack(z, frames=NODE_FRAMES):
    array = np.asarray(z, dtype=np.float64)

    if array.shape != (15 * len(frames),):
        raise ValueError("Invalid full-batch state vector")

    return {
        i: array[15*i:15*(i+1)]
        for i in range(len(frames))
    }


def full_batch_problem(fixture):
    """Use the same factors and declared anchor as rolling fusion."""
    validate_fixture(fixture)

    inertial, lidar, count = make_factors(fixture)

    anchor = synthetic_initial_anchor(
        initial_state(),
        sigma=INITIAL_ANCHOR_SIGMA,
    )

    x0 = initial_guess(fixture)

    def objective(z):
        return selected_residuals(
            unpack(z),
            anchor,
            inertial,
            lidar,
        )

    return x0, objective, inertial, lidar, count


def full_batch_comparison(condition):
    """Independent solver schedule on the same manufactured data."""
    fixture, _ = make_fixture(condition)

    x0, objective, _, _, counts = full_batch_problem(
        fixture
    )

    result = least_squares(
        objective,
        x0,
        method="trf",
        loss="linear",
        max_nfev=MAX_FULL_BATCH_NFEV,
        ftol=1e-9,
        xtol=1e-9,
        gtol=1e-9,
    )

    if (
        not result.success
        or not np.isfinite(result.x).all()
        or not math.isfinite(float(result.cost))
    ):
        raise ValueError(
            f"Full-batch solver did not converge: {condition}"
        )

    records, audit, _ = guarded_estimate(fixture)

    final_estimate = records[-1]
    final_reference = unpack(result.x)[len(NODE_FRAMES)-1]

    translation_gap = float(np.linalg.norm(
        np.asarray(final_estimate["position_m"])
        - final_reference[:3]
    ))

    q = final_estimate["orientation_quaternion_wxyz"]

    rolling_rotation = Rotation.from_quat([
        q[1], q[2], q[3], q[0]
    ])

    batch_rotation = Rotation.from_rotvec(
        final_reference[3:6]
    )

    rotation_gap = float(
        (rolling_rotation.inv() * batch_rotation).magnitude()
    )

    if condition == "clean" and (
        translation_gap >= 1e-3
        or rotation_gap >= 1e-3
    ):
        raise ValueError(
            "Clean full-batch/rolling result inconsistency"
        )

    return {
        "condition": condition,
        "full_batch_solver_converged": True,
        "full_batch_cost": float(result.cost),
        "full_batch_nfev": int(result.nfev),
        "rolling_window_solves": audit[
            "accepted_window_count"
        ],
        "rolling_vs_fullbatch_final_translation_gap_m":
            translation_gap,
        "rolling_vs_fullbatch_final_rotation_gap_rad":
            rotation_gap,
        "factors_from_same_synthetic_fixture": True,
        "full_batch_is_independent_measured_reference": False,
        "nonlinear_posterior_consistency_proven": False,
    }


def dropout_information_diagnostic():
    """Compare clean/dropout Jacobians at one common state.

    This isolates removed LiDAR factor information.
    It is NOT a coverage or calibrated uncertainty test.
    """
    clean, _ = make_fixture("clean")
    dropout, _ = make_fixture("lidar_dropout")

    x0, clean_objective, clean_imu, clean_lidar, _ = (
        full_batch_problem(clean)
    )

    other_x0, dropout_objective, other_imu, dropout_lidar, _ = (
        full_batch_problem(dropout)
    )

    if not np.array_equal(x0, other_x0):
        raise ValueError("Unmatched IMU linearization states")

    if set(clean_imu) != set(other_imu):
        raise ValueError("Inconsistent IMU factor topology")

    if not set(dropout_lidar).issubset(clean_lidar):
        raise ValueError("Unexpected dropout factor topology")

    missing = sorted(
        set(clean_lidar) - set(dropout_lidar)
    )

    if not missing:
        raise ValueError("No missing LiDAR information")

    _, J_clean = finite_difference_linearization(
        clean_objective, x0
    )
    _, J_dropout = finite_difference_linearization(
        dropout_objective, x0
    )

    def missing_residual(z):
        states = unpack(z)
        return np.concatenate([
            lidar_residual(
                states[i],
                states[j],
                clean_lidar[i, j],
            )
            for i, j in missing
        ])

    _, J_missing = finite_difference_linearization(
        missing_residual, x0
    )

    H_clean = J_clean.T @ J_clean
    H_dropout = J_dropout.T @ J_dropout

    expected_removed = J_missing.T @ J_missing

    discrepancy = (
        H_clean - H_dropout - expected_removed
    )

    max_abs_error = float(
        np.max(np.abs(discrepancy))
    )

    information_scale = max(
        1.0,
        float(np.max(np.abs(H_clean))),
    )

    if max_abs_error > 1e-6 * information_scale:
        raise ValueError(
            "LiDAR factor information conservation failed"
        )

    # Identical numerical ridge in both conditions.
    # This is not an empirically calibrated prior.
    ridge = max(
        1e-5,
        LOCAL_INFORMATION_RIDGE_RELATIVE
        * float(np.linalg.eigvalsh(H_clean)[-1])
    )

    identity = np.eye(len(x0))

    clean_proxy = np.linalg.solve(
        H_clean + ridge * identity,
        identity,
    )

    dropout_proxy = np.linalg.solve(
        H_dropout + ridge * identity,
        identity,
    )

    clean_trace = float(np.trace(clean_proxy))
    dropout_trace = float(np.trace(dropout_proxy))

    tolerance = 1e-8 * max(
        1.0, abs(clean_trace)
    )

    if dropout_trace + tolerance < clean_trace:
        raise ValueError(
            "Linearized dropout uncertainty proxy decreased"
        )

    return {
        "common_linearization": True,
        "missing_lidar_factor_keys": [
            list(key) for key in missing
        ],
        "removed_information_identity_max_abs_error":
            max_abs_error,
        "local_information_ridge": ridge,
        "clean_regularized_inverse_hessian_trace":
            clean_trace,
        "dropout_regularized_inverse_hessian_trace":
            dropout_trace,
        "linearized_information_conservation": True,
        "covariance_is_empirically_calibrated": False,
        "posterior_coverage_tested": False,
        "physical_observability_proven": False,
    }


def corruption_trials():
    """Demonstrate fail-closed behavior before estimation."""
    clean, _ = make_fixture("clean")

    cases = {}

    for name in (
        "missing_imu",
        "duplicate_imu_index",
        "negative_imu_dt",
        "nonfinite_gyro",
        "nonfinite_accel",
        "forged_physical_clock",
        "wrong_imu_origin",
        "nonfinite_lidar",
        "all_lidar_missing",
    ):
        altered = copy.deepcopy(clean)

        if name == "missing_imu":
            altered["imu"].pop()

        elif name == "duplicate_imu_index":
            altered["imu"][3]["interval_index"] = 2

        elif name == "negative_imu_dt":
            altered["imu"][3]["dt_s"] = -0.1

        elif name == "nonfinite_gyro":
            altered["imu"][3]["gyro_rad_s"][0] = float("nan")

        elif name == "nonfinite_accel":
            altered["imu"][3][
                "specific_force_m_s2"
            ][1] = float("inf")

        elif name == "forged_physical_clock":
            altered["imu"][3][
                "physical_clock_verified"
            ] = True

        elif name == "wrong_imu_origin":
            altered["imu"][3][
                "measurement_origin"
            ] = "REAL_SENSOR"

        elif name == "nonfinite_lidar":
            altered["scans"][4][0, 0] = float("nan")

        elif name == "all_lidar_missing":
            altered["available"] = [
                False
            ] * len(altered["available"])

        try:
            validate_fixture(altered)
        except (ValueError, TypeError, KeyError):
            cases[name] = "REJECTED_BEFORE_ESTIMATION"
        else:
            raise ValueError(
                f"Unsafe input was accepted: {name}"
            )

    return cases


def execute():
    # A valid dropout must be tolerated with remaining
    # usable LiDAR factors and a complete IMU sequence.
    outage_fixture, _ = long_fixture("lidar_outage")

    admission = validate_fixture(
        outage_fixture,
        node_frames=LONG_FRAMES,
    )

    if admission["node_count"] != 12:
        raise ValueError("Long-horizon validation failed")

    comparisons = {
        condition: full_batch_comparison(condition)
        for condition in FULL_BATCH_CONDITIONS
    }

    information = dropout_information_diagnostic()
    rejected = corruption_trials()

    if len(rejected) != 9:
        raise ValueError(
            "Incomplete corruption rejection matrix"
        )

    report = {
        "schema": SCHEMA,
        "status": "LOCAL_DEVELOPMENT_ROBUSTNESS_VALIDATED",
        "nonlinear_fullbatch_comparisons": comparisons,
        "dropout_linearized_information": information,
        "long_outage_input_admission": admission,
        "invalid_sensor_cases": rejected,
        "numeric_environment": {
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "scipy": scipy.__version__,
        },
        "reuses_existing_marginalized_15d_estimator": True,
        "changes_frozen_liDAR_or_trust_contracts": False,
        "local_linearized_information_only": True,
        "fullbatch_comparison_uses_same_synthetic_data": True,
        "independent_ground_truth_used": False,
        "calibrated_posterior_covariance_computed": False,
        "nonlinear_posterior_consistency_proven": False,
        "physical_sensor_observability_proven": False,
        "health_supervision_generated": False,
        "factor_conditioning_executed": False,
        "physical_robot_contacted": False,
    }

    return report


def run(destination):
    if (
        destination.exists()
        or destination.is_symlink()
        or not destination.parent.is_dir()
        or destination.parent.is_symlink()
    ):
        raise ValueError("Unsafe output location")

    first = execute()
    second = execute()

    if first != second:
        raise ValueError(
            "Non-deterministic robustness diagnostics"
        )

    first["repeat_derivation_identical"] = True

    blob = canonical(first)

    destination.mkdir(mode=0o700)

    (destination / "robustness_results_v1.json").write_bytes(
        blob
    )

    (destination / "robustness_sha256.txt").write_text(
        hashlib.sha256(blob).hexdigest() + "\n"
    )

    return first


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    result = run(args.output)

    for condition, comparison in (
        result["nonlinear_fullbatch_comparisons"].items()
    ):
        print(
            condition.upper() + "_FULLBATCH_GAP_M=",
            comparison[
                "rolling_vs_fullbatch_final_translation_gap_m"
            ],
        )

    print(
        "REJECTED_CORRUPTIONS=",
        len(result["invalid_sensor_cases"])
    )
    print("COMMON_LINEARIZATION_INFORMATION=PASS")
    print("FULLBATCH_DEVELOPMENT_COMPARISON=PASS")
    print("SENSOR_INPUT_FAIL_CLOSED=PASS")
    print("DETERMINISTIC_REPEAT=PASS")
    print("ESTIMATOR_ROBUSTNESS_DEVELOPMENT=PASS")


if __name__ == "__main__":
    main()
