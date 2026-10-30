"""A31-3: toy linear 15D measurement innovation diagnostics.

The synthetic 15-vector is organized as five XYZ triples. Factor
kinds select XYZ triples at indices 0, 3, or 6. These are NOT
physical LiDAR, camera or IMU measurement models. No estimator
is called and no real factor is constructed.
"""

from __future__ import annotations

import math

SCHEMA = "TRUST_ROBOT_R135_A31_3_SYNTHETIC_15D_INNOVATION_V1"

KINDS = {
    "toy_position_xyz": 0,
    "toy_velocity_xyz": 3,
    "toy_attitude_xyz": 6,
}

STREAMS = frozenset({
    "imu", "lidar", "left_image", "right_image",
})

FIELDS = frozenset({
    "source_kind",
    "stream",
    "factor_kind",
    "sequence",
    "clock_domain",
    "event_stamp_ns",
    "measurement_xyz",
    "noise_covariance_3x3",
})


class SyntheticInnovationError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise SyntheticInnovationError(message)


def finite_number(value):
    return (
        type(value) in (int, float)
        and math.isfinite(value)
    )


def vector(value, count):
    require(
        type(value) in (tuple, list)
        and len(value) == count
        and all(finite_number(x) for x in value),
        "Expected finite vector",
    )
    return [float(x) for x in value]


def cholesky_3(cov):
    """Validate strictly positive-definite 3x3 covariance."""

    require(
        type(cov) in (tuple, list)
        and len(cov) == 3,
        "Expected 3x3 covariance",
    )

    a = [vector(row, 3) for row in cov]

    require(
        all(
            abs(a[i][j] - a[j][i]) <= 1e-9
            for i in range(3)
            for j in range(3)
        ),
        "Covariance not symmetric",
    )

    l = [[0.0] * 3 for _ in range(3)]

    for i in range(3):
        for j in range(i + 1):
            value = a[i][j] - sum(
                l[i][k] * l[j][k]
                for k in range(j)
            )

            require(
                math.isfinite(value),
                "Nonfinite covariance Schur residual",
            )

            if i == j:
                require(
                    value > 1e-12,
                    "Covariance not strictly SPD",
                )
                l[i][j] = math.sqrt(value)
            else:
                l[i][j] = value / l[j][j]

    return l


def innovation(state, descriptor):
    """Compute toy residual, 3x15 Jacobian and Mahalanobis NIS."""

    x = vector(state, 15)

    require(
        type(descriptor) is dict
        and set(descriptor) == FIELDS,
        "Unexpected synthetic descriptor fields",
    )

    require(
        descriptor["source_kind"] == "SYNTHETIC_ONLY"
        and type(descriptor["stream"]) is str
        and descriptor["stream"] in STREAMS
        and type(descriptor["factor_kind"]) is str
        and descriptor["factor_kind"] in KINDS,
        "Unqualified source, stream or toy factor kind",
    )

    require(
        type(descriptor["sequence"]) is int
        and descriptor["sequence"] >= 0
        and type(descriptor["event_stamp_ns"]) is int
        and descriptor["event_stamp_ns"] >= 0,
        "Invalid synthetic event identity",
    )

    domain = descriptor["clock_domain"]

    require(
        type(domain) is str
        and 0 < len(domain) <= 128
        and all(33 <= ord(c) <= 126 for c in domain),
        "Invalid synthetic clock domain",
    )

    z = vector(descriptor["measurement_xyz"], 3)
    l = cholesky_3(descriptor["noise_covariance_3x3"])

    start = KINDS[descriptor["factor_kind"]]

    residual = [
        z[i] - x[start + i]
        for i in range(3)
    ]

    require(
        all(math.isfinite(v) for v in residual),
        "Nonfinite toy innovation",
    )

    jacobian = [[0.0] * 15 for _ in range(3)]

    for i in range(3):
        jacobian[i][start + i] = 1.0

    # Solve L*y = residual.
    # NIS = y^T*y, without explicitly inverting covariance.

    y = []

    for i in range(3):
        y.append(
            (
                residual[i] - sum(
                    l[i][j] * y[j]
                    for j in range(i)
                )
            ) / l[i][i]
        )

    nis = sum(v * v for v in y)

    require(
        math.isfinite(nis) and nis >= 0,
        "Invalid toy normalized innovation squared",
    )

    return {
        "schema": SCHEMA,
        "status": "TOY_LINEAR_INNOVATION_ONLY",
        "stream": descriptor["stream"],
        "factor_kind": descriptor["factor_kind"],
        "event_stamp_ns": descriptor["event_stamp_ns"],
        "clock_domain": domain,
        "residual_xyz": residual,
        "jacobian_3x15": jacobian,
        "normalized_innovation_squared": nis,
        "real_measurement_model_verified": False,
        "physical_noise_covariance_verified": False,
        "estimator_invoked": False,
        "real_factor_count": 0,
        "real_factor_admission": "DENIED",
        "m2dgr_gates": "11_CLOSED",
    }


def make_real_factor(*args, **kwargs):
    raise SyntheticInnovationError(
        "Toy innovation cannot create physical estimator factors"
    )
