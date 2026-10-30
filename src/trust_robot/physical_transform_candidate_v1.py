"""A27-8: structural preflight of proposed SE(3) evidence.

This module accepts candidate coordinate transforms for
structural inspection only. Algebraic consistency is not
physical calibration or independent frame qualification.
"""

from __future__ import annotations

import hashlib
import json
import math

SCHEMA = "TRUST_ROBOT_R135_A27_8_TRANSFORM_CANDIDATE_V1"

FIELDS = frozenset({
    "source_frame",
    "target_frame",
    "direction_convention",
    "T_target_source",
    "covariance_6x6",
    "evidence_request_id",
    "candidate_origin",
    "source_artifact_sha256",
    "physical_qualification_claim",
})

REQUEST_IDS = frozenset({"B01", "B03", "C03"})

class TransformCandidateError(ValueError):
    pass


def require(ok, message):
    if not ok:
        raise TransformCandidateError(message)


def _finite_number(value):
    return type(value) in (int, float) and math.isfinite(value)


def _matrix(value, dimension):
    require(
        type(value) in (list, tuple)
        and len(value) == dimension,
        "Incorrect matrix dimensions",
    )

    result = []

    for row in value:
        require(
            type(row) in (list, tuple)
            and len(row) == dimension
            and all(_finite_number(x) for x in row),
            "Invalid matrix entry",
        )
        result.append([float(x) for x in row])

    return result


def _covariance_psd(value):
    """Symmetric PSD check by pivoted-free Schur reductions.

    Negative pivots or nonzero off-diagonals at a zero
    pivot are rejected. This is structural numerical
    validation, not uncertainty provenance.
    """
    a = _matrix(value, 6)
    tol = 1e-9

    for i in range(6):
        for j in range(6):
            require(
                abs(a[i][j] - a[j][i]) <= tol,
                "Covariance is not symmetric",
            )

    w = [row[:] for row in a]

    for k in range(6):
        pivot = w[k][k]

        require(
            pivot >= -tol,
            "Covariance has negative pivot",
        )

        if pivot <= tol:
            require(
                all(
                    abs(w[j][k]) <= tol
                    for j in range(k + 1, 6)
                ),
                "Zero covariance pivot has coupling",
            )
            continue

        for i in range(k + 1, 6):
            for j in range(k + 1, 6):
                w[i][j] -= (
                    w[i][k] * w[k][j] / pivot
                )

    return True


def review_transform_candidate(candidate, nominal_links):
    require(
        type(candidate) is dict
        and set(candidate) == FIELDS,
        "Unexpected candidate transform fields",
    )

    require(
        type(nominal_links) in (list, tuple)
        and len(nominal_links) <= 512
        and len(set(nominal_links)) == len(nominal_links)
        and all(
            type(x) is str and 0 < len(x) <= 256
            for x in nominal_links
        ),
        "Invalid nominal link inventory",
    )

    for key in ("source_frame", "target_frame"):
        value = candidate[key]
        require(
            type(value) is str
            and 0 < len(value) <= 256
            and all(ord(ch) >= 33 for ch in value),
            "Invalid frame identity",
        )

    require(
        candidate["source_frame"] != candidate["target_frame"],
        "Source and target frames must differ",
    )

    require(
        candidate["direction_convention"] == "T_target_source",
        "Transform direction is not explicit",
    )

    require(
        candidate["evidence_request_id"] in REQUEST_IDS,
        "Unknown geometry evidence request",
    )

    require(
        candidate["candidate_origin"] in (
            "NOMINAL_URDF",
            "PROSPECTIVE_EXTERNAL",
        ),
        "Unknown candidate provenance class",
    )

    require(
        candidate["physical_qualification_claim"] is False,
        "Physical qualification cannot be declared",
    )

    digest = candidate["source_artifact_sha256"]

    require(
        digest is None
        or (
            type(digest) is str
            and len(digest) == 64
            and all(ch in "0123456789abcdef" for ch in digest)
        ),
        "Invalid source artifact digest",
    )

    m = _matrix(candidate["T_target_source"], 4)

    require(
        all(abs(m[3][i]) <= 1e-9 for i in range(3))
        and abs(m[3][3] - 1.0) <= 1e-9,
        "Invalid homogeneous transform row",
    )

    r = [row[:3] for row in m[:3]]

    maximum_orthogonality_error = max(
        abs(
            sum(r[k][i] * r[k][j] for k in range(3))
            - (1.0 if i == j else 0.0)
        )
        for i in range(3)
        for j in range(3)
    )

    determinant = (
        r[0][0] * (
            r[1][1] * r[2][2] - r[1][2] * r[2][1]
        )
        - r[0][1] * (
            r[1][0] * r[2][2] - r[1][2] * r[2][0]
        )
        + r[0][2] * (
            r[1][0] * r[2][1] - r[1][1] * r[2][0]
        )
    )

    require(
        maximum_orthogonality_error <= 1e-6
        and abs(determinant - 1.0) <= 1e-6,
        "Matrix is not a proper SO(3) rotation",
    )

    covariance = candidate["covariance_6x6"]

    if covariance is not None:
        _covariance_psd(covariance)

    canonical = json.dumps(
        candidate,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("ascii")

    return {
        "schema": SCHEMA,
        "status": "STRUCTURAL_TRANSFORM_CANDIDATE_ONLY",
        "source_frame": candidate["source_frame"],
        "target_frame": candidate["target_frame"],
        "source_in_nominal_urdf":
            candidate["source_frame"] in nominal_links,
        "target_in_nominal_urdf":
            candidate["target_frame"] in nominal_links,
        "candidate_origin": candidate["candidate_origin"],
        "evidence_request_id":
            candidate["evidence_request_id"],
        "candidate_sha256":
            hashlib.sha256(canonical).hexdigest(),
        "proper_rotation_checked": True,
        "covariance_structurally_checked":
            covariance is not None,
        "covariance_independently_verified": False,
        "physical_frame_equivalence_verified": False,
        "physical_extrinsics_qualified": False,
        "estimator_invoked": False,
        "real_factor_count": 0,
        "real_factor_admission": "DENIED",
        "m2dgr_gates": "11_CLOSED",
    }


def admit_physical_transform(*args, **kwargs):
    raise TransformCandidateError(
        "Structural SE3 inspection is not physical qualification"
    )
