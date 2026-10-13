"""Development-only numerical support diagnostic for linearized factors.

This module reasons about supplied, already-whitened Jacobians.
It does not infer physical observability, estimate empirical covariance,
calibrate health probabilities, or authorize factor conditioning.

Factors have explicit identities and owned observation identifiers.
The same measurement may not enter the ledger twice.

This is a diagnostic, not a replacement for nonlinear optimization.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


SCHEMA = "TRUST_ROBOT_ANALYTIC_FACTOR_SUPPORT_V1"


class FactorSupportError(ValueError):
    """Invalid factor ledger or unsafe numerical diagnostic."""


@dataclass(frozen=True)
class LinearFactor:
    factor_id: str
    measurement_ids: tuple[str, ...]
    jacobian: np.ndarray


def _check_matrix(value, width):
    a = np.asarray(value, dtype=np.float64)
    if (
        a.ndim != 2
        or a.shape[0] == 0
        or a.shape[1] != width
        or not np.isfinite(a).all()
    ):
        raise FactorSupportError("Invalid linear factor Jacobian")
    return a.copy()


def analyze_factor_support(
    state_dimension: int,
    factors,
    *,
    relative_rank_tolerance: float = 1e-10,
    maximum_condition: float = 1e10,
):
    """Audit factor ownership and numerical information support.

    Numerical thresholds describe this diagnostic only. They are not
    trained health thresholds, physical observability guarantees,
    or validation-selected safety operating points.

    Factor IDs and measurement IDs must be globally unique.
    An empty factor sequence returns unavailable status.
    """
    if (
        isinstance(state_dimension, bool)
        or not isinstance(state_dimension, (int, np.integer))
        or state_dimension < 1
        or state_dimension > 3000
    ):
        raise FactorSupportError("Invalid state dimension")

    for value in (relative_rank_tolerance, maximum_condition):
        if not np.isscalar(value):
            raise FactorSupportError("Invalid numerical tolerance")
        try:
            valid = np.isfinite(float(value))
        except (TypeError, ValueError, OverflowError) as exc:
            raise FactorSupportError(
                "Invalid numerical tolerance"
            ) from exc
        if not valid:
            raise FactorSupportError("Nonfinite numerical tolerance")

    if not (0 < relative_rank_tolerance < 1):
        raise FactorSupportError("Invalid rank tolerance")
    if maximum_condition <= 1:
        raise FactorSupportError("Invalid condition limit")

    factor_list = list(factors)
    ids = set()
    measurements = set()
    blocks = []

    if len(factor_list) > 10000:
        raise FactorSupportError("Excessive factor count")

    rows = 0

    for factor in factor_list:
        if not isinstance(factor, LinearFactor):
            raise FactorSupportError("Unexpected factor type")

        fid = factor.factor_id
        owned = factor.measurement_ids

        if not isinstance(fid, str) or not fid.strip():
            raise FactorSupportError("Invalid factor identity")
        if fid in ids:
            raise FactorSupportError("Duplicate factor identity")
        ids.add(fid)

        if not isinstance(owned, tuple) or not owned:
            raise FactorSupportError("Missing measurement ownership")

        if len(owned) != len(set(owned)):
            raise FactorSupportError("Repeated owned measurement")

        for mid in owned:
            if not isinstance(mid, str) or not mid.strip():
                raise FactorSupportError("Invalid measurement identity")
            if mid in measurements:
                raise FactorSupportError("Measurement double counted")
            measurements.add(mid)

        J = _check_matrix(factor.jacobian, state_dimension)
        rows += J.shape[0]
        if rows > 30000:
            raise FactorSupportError("Excessive Jacobian rows")
        blocks.append(J)

    if not blocks:
        return {
            "schema": SCHEMA,
            "status": "NUMERICALLY_UNAVAILABLE",
            "state_dimension": int(state_dimension),
            "factor_count": 0,
            "measurement_count": 0,
            "jacobian_rows": 0,
            "numerical_rank": 0,
            "nullity": int(state_dimension),
            "condition_number": None,
            "smallest_retained_singular_value": None,
            "numerical_information_psd": True,
            "physical_observability_verified": False,
            "calibrated_uncertainty_available": False,
        }

    J = np.vstack(blocks)

    # SVD of the whitened Jacobian avoids unnecessarily squaring
    # its condition number through normal equations.
    try:
        singular = np.linalg.svd(J, compute_uv=False)
    except np.linalg.LinAlgError as exc:
        raise FactorSupportError("Jacobian SVD failed") from exc

    if not np.isfinite(singular).all():
        raise FactorSupportError("Invalid singular spectrum")

    largest = float(singular[0])
    threshold = max(
        float(relative_rank_tolerance) * largest,
        np.finfo(np.float64).eps
        * max(J.shape) * largest,
    )

    retained = singular[singular > threshold]
    rank = int(len(retained))
    nullity = int(state_dimension - rank)

    if rank:
        smallest = float(retained[-1])
        condition = largest / smallest
    else:
        smallest = None
        condition = None

    supported = (
        rank == state_dimension
        and condition is not None
        and np.isfinite(condition)
        and condition <= maximum_condition
    )

    return {
        "schema": SCHEMA,
        "status": (
            "NUMERICALLY_SUPPORTED"
            if supported else "NUMERICALLY_UNAVAILABLE"
        ),
        "state_dimension": int(state_dimension),
        "factor_count": len(blocks),
        "measurement_count": len(measurements),
        "jacobian_rows": int(J.shape[0]),
        "numerical_rank": rank,
        "nullity": nullity,
        "condition_number": (
            float(condition)
            if condition is not None and np.isfinite(condition)
            else None
        ),
        "smallest_retained_singular_value": smallest,
        "numerical_information_psd": True,
        "physical_observability_verified": False,
        "calibrated_uncertainty_available": False,
    }


def make_linear_factor(factor_id, measurement_ids, jacobian):
    """Construct an immutable-identity factor with owned observations."""
    return LinearFactor(
        factor_id=factor_id,
        measurement_ids=tuple(measurement_ids),
        jacobian=np.asarray(jacobian, dtype=float).copy(),
    )
