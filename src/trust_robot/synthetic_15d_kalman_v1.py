"""R135-A31-5: synthetic linear 15D Kalman update mathematics.

Uses the A31-3 toy 3x15 selection Jacobian.

S = H P H^T + R
K = P H^T S^-1

P_post = (I-KH) P (I-KH)^T + K R K^T

The Joseph form is used for numerical covariance stability.

This is a mathematical toy update, not the robot's physical
15D estimator. No real factors or measurements are accepted.
"""

from __future__ import annotations

import math

from trust_robot.synthetic_15d_innovation_v1 import (
    innovation,
)

SCHEMA = "TRUST_ROBOT_R135_A31_5_SYNTHETIC_KALMAN_V1"


class SyntheticKalmanError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise SyntheticKalmanError(message)


def finite(value):
    return (
        type(value) in (int, float)
        and math.isfinite(value)
    )


def matrix(value, n):
    require(
        type(value) in (list, tuple)
        and len(value) == n,
        "Incorrect covariance dimension",
    )

    result = []

    for row in value:
        require(
            type(row) in (list, tuple)
            and len(row) == n
            and all(finite(x) for x in row),
            "Nonfinite covariance entry",
        )
        result.append([float(x) for x in row])

    return result


def transpose(a):
    return [list(row) for row in zip(*a)]


def multiply(a, b):
    return [
        [
            sum(a[i][k] * b[k][j] for k in range(len(b)))
            for j in range(len(b[0]))
        ]
        for i in range(len(a))
    ]


def add(a, b):
    return [
        [a[i][j] + b[i][j] for j in range(len(a[0]))]
        for i in range(len(a))
    ]


def identity(n):
    return [
        [1.0 if i == j else 0.0 for j in range(n)]
        for i in range(n)
    ]


def cholesky(a):
    n = len(a)

    require(
        all(
            abs(a[i][j] - a[j][i]) <= 1e-9
            for i in range(n)
            for j in range(n)
        ),
        "Covariance is asymmetric",
    )

    lower = [[0.0] * n for _ in range(n)]

    for i in range(n):
        for j in range(i + 1):
            value = a[i][j] - sum(
                lower[i][k] * lower[j][k]
                for k in range(j)
            )

            require(
                math.isfinite(value),
                "Nonfinite covariance residual",
            )

            if i == j:
                require(
                    value > 1e-12,
                    "Covariance is not strictly positive definite",
                )
                lower[i][j] = math.sqrt(value)
            else:
                lower[i][j] = value / lower[j][j]

    return lower


def solve_cholesky(lower, rhs):
    n = len(lower)
    y = [0.0] * n

    for i in range(n):
        y[i] = (
            rhs[i] - sum(
                lower[i][j] * y[j]
                for j in range(i)
            )
        ) / lower[i][i]

    x = [0.0] * n

    for i in reversed(range(n)):
        x[i] = (
            y[i] - sum(
                lower[j][i] * x[j]
                for j in range(i + 1, n)
            )
        ) / lower[i][i]

    require(
        all(math.isfinite(v) for v in x),
        "Nonfinite covariance solve",
    )

    return x


def propose_toy_kalman_update(
    state_15,
    prior_covariance_15x15,
    descriptor,
):
    """Perform exactly one synthetic linear state update."""

    diagnostic = innovation(state_15, descriptor)

    require(
        diagnostic["status"] == "TOY_LINEAR_INNOVATION_ONLY"
        and diagnostic["real_factor_count"] == 0
        and diagnostic["real_factor_admission"] == "DENIED",
        "Toy innovation provenance changed",
    )

    x = [float(v) for v in state_15]
    p = matrix(prior_covariance_15x15, 15)

    cholesky(p)

    r = matrix(descriptor["noise_covariance_3x3"], 3)
    h = diagnostic["jacobian_3x15"]
    residual = diagnostic["residual_xyz"]

    hp = multiply(h, p)
    s = add(multiply(hp, transpose(h)), r)

    l = cholesky(s)

    inverse_columns = []

    for j in range(3):
        rhs = [
            1.0 if i == j else 0.0
            for i in range(3)
        ]
        inverse_columns.append(solve_cholesky(l, rhs))

    sinv = transpose(inverse_columns)

    pht = multiply(p, transpose(h))
    gain = multiply(pht, sinv)

    delta = [
        sum(gain[i][j] * residual[j] for j in range(3))
        for i in range(15)
    ]

    posterior_state = [
        x[i] + delta[i] for i in range(15)
    ]

    nis_vector = solve_cholesky(l, residual)

    nis = sum(
        residual[i] * nis_vector[i]
        for i in range(3)
    )

    require(
        math.isfinite(nis) and nis >= 0,
        "Invalid full innovation covariance NIS",
    )

    kh = multiply(gain, h)
    correction = identity(15)

    for i in range(15):
        for j in range(15):
            correction[i][j] -= kh[i][j]

    joseph_first = multiply(
        multiply(correction, p),
        transpose(correction),
    )

    joseph_second = multiply(
        multiply(gain, r),
        transpose(gain),
    )

    posterior = add(joseph_first, joseph_second)

    # Remove tiny floating-point asymmetry.
    posterior = [
        [
            (posterior[i][j] + posterior[j][i]) / 2.0
            for j in range(15)
        ]
        for i in range(15)
    ]

    cholesky(posterior)

    require(
        all(math.isfinite(v) for v in posterior_state),
        "Nonfinite toy posterior state",
    )

    return {
        "schema": SCHEMA,
        "status": "SYNTHETIC_LINEAR_KALMAN_ONLY",
        "state_dimension": 15,
        "residual_dimension": 3,
        "toy_stream": diagnostic["stream"],
        "toy_factor_kind": diagnostic["factor_kind"],
        "toy_full_innovation_nis": nis,
        "toy_measurement_only_nis":
            diagnostic["normalized_innovation_squared"],
        "toy_gain_15x3": gain,
        "posterior_state_15": posterior_state,
        "posterior_covariance_15x15": posterior,
        "prior_covariance_trace":
            sum(p[i][i] for i in range(15)),
        "posterior_covariance_trace":
            sum(posterior[i][i] for i in range(15)),
        "joseph_covariance_used": True,
        "physical_observation_model_verified": False,
        "physical_prior_uncertainty_verified": False,
        "physical_state_estimated": False,
        "physical_factor_created": False,
        "estimator_invoked": False,
        "real_factor_count": 0,
        "real_factor_admission": "DENIED",
        "m2dgr_gates": "11_CLOSED",
    }


def apply_physical_state_update(*args, **kwargs):
    raise SyntheticKalmanError(
        "Synthetic Kalman algebra cannot update a real robot state"
    )
