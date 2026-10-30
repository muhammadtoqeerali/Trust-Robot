"""A27-9: SE(3) left-perturbation covariance mathematics.

Convention:
T_target_source maps source coordinates into target.
Twist order is [translation_rho_xyz, rotation_phi_xyz].
Perturbation acts on the left in target coordinates.

For independent perturbations:
Sigma_AC = Sigma_AB + Ad(T_AB) Sigma_BC Ad(T_AB)^T.

This is numerical engineering mathematics, not a physical
calibration claim. No physical independence is inferred.
"""

from __future__ import annotations

import math

SCHEMA = "TRUST_ROBOT_R135_A27_9_SE3_COVARIANCE_V1"

POSE_FIELDS = frozenset({
    "target_frame", "source_frame", "T_target_source",
    "covariance_6x6", "origin",
})

ORIGINS = frozenset({
    "SYNTHETIC_ONLY",
    "NOMINAL_URDF_UNQUALIFIED",
    "MATHEMATICAL_ONLY",
})


class CovarianceError(ValueError):
    pass


def require(ok, message):
    if not ok:
        raise CovarianceError(message)


def matrix(value, dim):
    require(
        type(value) in (tuple, list)
        and len(value) == dim,
        "Invalid matrix dimensions",
    )
    result = []

    for row in value:
        require(
            type(row) in (tuple, list)
            and len(row) == dim
            and all(
                type(x) in (int, float) and math.isfinite(x)
                for x in row
            ),
            "Invalid finite matrix entries",
        )
        result.append([float(x) for x in row])

    return result


def mm(a, b):
    return [
        [
            sum(a[i][k] * b[k][j] for k in range(len(b)))
            for j in range(len(b[0]))
        ]
        for i in range(len(a))
    ]


def tr(a):
    return [list(row) for row in zip(*a)]


def add(a, b):
    return [
        [a[i][j] + b[i][j] for j in range(len(a))]
        for i in range(len(a))
    ]


def check_covariance(value):
    c = matrix(value, 6)
    tol = 1e-9

    require(
        all(
            abs(c[i][j] - c[j][i]) <= tol
            for i in range(6)
            for j in range(6)
        ),
        "Covariance not symmetric",
    )

    # Semidefinite Schur reduction: zero pivots cannot
    # carry nonzero residual cross-covariance.
    w = [row[:] for row in c]

    for k in range(6):
        pivot = w[k][k]

        require(
            pivot >= -tol,
            "Covariance not positive semidefinite",
        )

        if pivot <= tol:
            require(
                all(
                    abs(w[i][k]) <= tol
                    for i in range(k + 1, 6)
                ),
                "Singular covariance has residual coupling",
            )
            continue

        for i in range(k + 1, 6):
            for j in range(k + 1, 6):
                w[i][j] -= w[i][k] * w[k][j] / pivot

        for i in range(k + 1, 6):
            w[i][k] = 0.0
            w[k][i] = 0.0

    return c


def check_pose(p):
    require(
        type(p) is dict and set(p) == POSE_FIELDS,
        "Unexpected pose fields",
    )

    for key in ("target_frame", "source_frame"):
        value = p[key]
        require(
            type(value) is str
            and 0 < len(value) <= 256
            and all(33 <= ord(ch) <= 126 for ch in value),
            "Invalid frame name",
        )

    require(p["origin"] in ORIGINS, "Unknown pose provenance")

    t = matrix(p["T_target_source"], 4)
    r = [row[:3] for row in t[:3]]

    require(
        all(abs(t[3][i]) <= 1e-9 for i in range(3))
        and abs(t[3][3] - 1) <= 1e-9,
        "Invalid SE3 homogeneous row",
    )

    orth = max(
        abs(
            sum(r[k][i] * r[k][j] for k in range(3))
            - (1.0 if i == j else 0.0)
        )
        for i in range(3)
        for j in range(3)
    )

    det = (
        r[0][0] * (r[1][1] * r[2][2] - r[1][2] * r[2][1])
        - r[0][1] * (r[1][0] * r[2][2] - r[1][2] * r[2][0])
        + r[0][2] * (r[1][0] * r[2][1] - r[1][1] * r[2][0])
    )

    require(
        orth <= 1e-6 and abs(det - 1.0) <= 1e-6,
        "Not a proper SO3 rotation",
    )

    c = check_covariance(p["covariance_6x6"])
    return t, c


def inverse_matrix(t):
    result = [
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]

    for i in range(3):
        for j in range(3):
            result[i][j] = t[j][i]

    for i in range(3):
        result[i][3] = -sum(
            result[i][j] * t[j][3] for j in range(3)
        )

    return result


def adjoint(t):
    r = [row[:3] for row in t[:3]]
    x, y, z = [t[i][3] for i in range(3)]

    skew = [
        [0.0, -z, y],
        [z, 0.0, -x],
        [-y, x, 0.0],
    ]

    sr = mm(skew, r)
    a = [[0.0] * 6 for _ in range(6)]

    for i in range(3):
        for j in range(3):
            a[i][j] = r[i][j]
            a[i][j + 3] = sr[i][j]
            a[i + 3][j + 3] = r[i][j]

    return a


def _result(pose):
    check_pose(pose)

    return {
        "schema": SCHEMA,
        "status": "MATHEMATICAL_COVARIANCE_ONLY",
        "pose": pose,
        "perturbation_convention":
            "LEFT_RHO_PHI_TARGET_FRAME",
        "physical_error_independence_verified": False,
        "physical_calibration_qualified": False,
        "physical_frame_equivalence_verified": False,
        "estimator_invoked": False,
        "real_factor_count": 0,
        "real_factor_admission": "DENIED",
        "m2dgr_gates": "11_CLOSED",
    }


def invert_uncertain_pose(p):
    t, c = check_pose(p)
    inv = inverse_matrix(t)
    a = adjoint(inv)

    propagated = mm(mm(a, c), tr(a))

    return _result({
        "target_frame": p["source_frame"],
        "source_frame": p["target_frame"],
        "T_target_source": inv,
        "covariance_6x6": propagated,
        "origin": "MATHEMATICAL_ONLY",
    })


def compose_independent_poses(a, b, *, independent_errors=False):
    require(
        independent_errors is True,
        "Independent perturbation assumption must be explicit",
    )

    ta, ca = check_pose(a)
    tb, cb = check_pose(b)

    require(
        a["source_frame"] == b["target_frame"],
        "Transform frame directions do not compose",
    )

    result_t = mm(ta, tb)
    adj = adjoint(ta)
    result_c = add(ca, mm(mm(adj, cb), tr(adj)))

    return _result({
        "target_frame": a["target_frame"],
        "source_frame": b["source_frame"],
        "T_target_source": result_t,
        "covariance_6x6": result_c,
        "origin": "MATHEMATICAL_ONLY",
    })


def admit_real_covariance(*args, **kwargs):
    raise CovarianceError(
        "Numerical covariance propagation is not "
        "independent physical uncertainty evidence"
    )
