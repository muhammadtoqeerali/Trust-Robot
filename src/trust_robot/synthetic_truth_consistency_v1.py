"""Toy-only 15D truth-error and covariance consistency diagnostics.

Single-trajectory NEES is descriptive, not a statistical
calibration claim. The reference is declared synthetic truth.
"""

import math

from trust_robot.synthetic_15d_innovation_v1 import vector
from trust_robot.synthetic_15d_kalman_v1 import (
    matrix,
    cholesky,
    solve_cholesky,
)

SCHEMA = "TRUST_ROBOT_R135_A31_8_TOY_TRUTH_CONSISTENCY_V1"

TRUTH_FIELDS = {
    "source_kind",
    "state_15",
    "reference_protocol",
}


class ToyConsistencyError(ValueError):
    pass


def require(ok, message):
    if not ok:
        raise ToyConsistencyError(message)


def check_truth(truth):
    require(
        type(truth) is dict
        and set(truth) == TRUTH_FIELDS,
        "Invalid truth object",
    )

    require(
        truth["source_kind"] == "SYNTHETIC_TRUTH_ONLY"
        and truth["reference_protocol"]
        == "DECLARED_TOY_KINEMATICS_V1",
        "Physical reference truth prohibited",
    )

    return vector(truth["state_15"], 15)


def review_toy_consistency(state, covariance, truth):
    x = vector(state, 15)
    target = check_truth(truth)

    p = matrix(covariance, 15)
    lower = cholesky(p)

    error = [
        x[i] - target[i]
        for i in range(15)
    ]

    solved = solve_cholesky(lower, error)

    nees = sum(
        error[i] * solved[i]
        for i in range(15)
    )

    position_squared_error = sum(
        error[i] ** 2 for i in range(3)
    )

    require(
        math.isfinite(nees)
        and nees >= -1e-8
        and math.isfinite(position_squared_error),
        "Invalid numerical consistency",
    )

    nees = max(0.0, nees)

    return {
        "schema": SCHEMA,
        "status": "SINGLE_TOY_TRUTH_DIAGNOSTIC_ONLY",
        "toy_nees_15d": nees,
        "toy_normalized_nees_15d": nees / 15.0,
        "toy_position_squared_error": position_squared_error,
        "toy_covariance_trace": sum(
            p[i][i] for i in range(15)
        ),
        "statistical_calibration_established": False,
        "physical_ground_truth_verified": False,
        "physical_pose_accuracy_measured": False,
        "real_factor_count": 0,
        "real_factor_admission": "DENIED",
        "m2dgr_gates": "11_CLOSED",
    }


def summarize_toy_consistency(rows):
    require(
        type(rows) is list
        and 1 <= len(rows) <= 64,
        "Invalid bounded toy trajectory",
    )

    for item in rows:
        require(
            type(item) is dict
            and item.get("schema") == SCHEMA
            and item.get("status")
            == "SINGLE_TOY_TRUTH_DIAGNOSTIC_ONLY"
            and item.get("real_factor_count") == 0
            and item.get("real_factor_admission") == "DENIED"
            and item.get("statistical_calibration_established")
            is False,
            "Invalid toy consistency record",
        )

        for field in (
            "toy_nees_15d",
            "toy_position_squared_error",
        ):
            value = item.get(field)

            require(
                type(value) in (int, float)
                and math.isfinite(value)
                and value >= 0,
                "Invalid finite metric",
            )

    n = len(rows)

    return {
        "schema": SCHEMA,
        "status": "DESCRIPTIVE_TOY_SEQUENCE_ONLY",
        "step_count": n,
        "mean_toy_nees_15d": sum(
            item["toy_nees_15d"]
            for item in rows
        ) / n,
        "toy_position_rmse": math.sqrt(
            sum(
                item["toy_position_squared_error"]
                for item in rows
            ) / n
        ),
        "statistical_calibration_established": False,
        "physical_ground_truth_verified": False,
        "real_factor_count": 0,
        "real_factor_admission": "DENIED",
        "m2dgr_gates": "11_CLOSED",
    }


def certify_physical_consistency(*args, **kwargs):
    raise ToyConsistencyError(
        "Synthetic truth cannot qualify physical pose error"
    )
