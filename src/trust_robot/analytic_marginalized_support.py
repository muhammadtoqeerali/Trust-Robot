"""Development-only numerical audit of real marginalized estimator windows.

Operates on SciPy's fitted, whitened residual Jacobian.

Separates the existing Schur prior, active IMU preintegration factors,
and LiDAR registration factors without modifying their weights.

Measurement ownership is represented by synthetic IMU sample indices,
LiDAR graph-edge identifiers and the historical marginalized ledger.

Numerical support does not establish physical observability or
a calibrated posterior covariance.
"""
from __future__ import annotations

import numpy as np

from trust_robot.analytic_factor_support import (
    FactorSupportError,
    analyze_factor_support,
    make_linear_factor,
)
from trust_robot.analytic_inertial_15d import lidar_residual
from trust_robot.analytic_preintegrated_fusion import (
    whitened_inertial_residual,
)

STATE_DIM = 15


def _edge(key, node_frames):
    if (
        not isinstance(key, tuple)
        or len(key) != 2
        or any(
            isinstance(k, bool)
            or not isinstance(k, (int, np.integer))
            for k in key
        )
    ):
        raise FactorSupportError("Invalid graph-edge identity")

    i, j = map(int, key)

    if not (0 <= i < j < len(node_frames)):
        raise FactorSupportError("Invalid graph-edge chronology")

    return i, j


def _imu_ids(key, node_frames):
    i, j = _edge(key, node_frames)

    if j != i + 1:
        raise FactorSupportError(
            "IMU preintegration must connect adjacent estimator nodes"
        )

    a, b = node_frames[i], node_frames[j]

    if (
        isinstance(a, bool)
        or isinstance(b, bool)
        or not isinstance(a, (int, np.integer))
        or not isinstance(b, (int, np.integer))
        or a < 0
        or b <= a
    ):
        raise FactorSupportError("Invalid IMU sample interval")

    return tuple(f"imu_sample:{k}" for k in range(a, b))


def _lidar_id(key, node_frames):
    i, j = _edge(key, node_frames)
    return f"lidar_edge:{i}:{j}"


def audit_marginalized_window(
    fitted_jacobian,
    fitted_state,
    live_nodes,
    node_frames,
    prior,
    active_imu,
    active_lidar,
    consumed_imu,
    consumed_lidar,
    *,
    relative_rank_tolerance=1e-12,
    maximum_condition=1e14,
):
    """Split an actual solved Jacobian into owned factor contributions."""
    live = tuple(live_nodes)
    frames = tuple(node_frames)

    if (
        not live
        or len(set(live)) != len(live)
        or tuple(sorted(live)) != live
        or any(k < 0 or k >= len(frames) for k in live)
    ):
        raise FactorSupportError("Invalid live estimator nodes")

    width = STATE_DIM * len(live)
    x = np.asarray(fitted_state, dtype=np.float64)
    J = np.asarray(fitted_jacobian, dtype=np.float64)

    if (
        x.shape != (width,)
        or J.ndim != 2
        or J.shape[1] != width
        or not np.isfinite(x).all()
        or not np.isfinite(J).all()
    ):
        raise FactorSupportError("Invalid fitted optimizer state/Jacobian")

    states = {
        k: x[i*STATE_DIM:(i+1)*STATE_DIM]
        for i, k in enumerate(live)
    }

    if not set(prior.node_ids).issubset(states):
        raise FactorSupportError("Prior references absent live state")

    historical = {"synthetic_initial_anchor"}

    for key in consumed_imu:
        historical.update(_imu_ids(key, frames))

    for key in consumed_lidar:
        historical.add(_lidar_id(key, frames))

    blocks = []
    cursor = 0

    def add_block(name, observations, residual):
        nonlocal cursor

        vector = np.asarray(residual, dtype=np.float64)

        if vector.ndim != 1 or not np.isfinite(vector).all():
            raise FactorSupportError("Invalid factor residual block")

        rows = vector.size

        if rows < 1 or cursor + rows > J.shape[0]:
            raise FactorSupportError("Jacobian block boundary mismatch")

        blocks.append(make_linear_factor(
            name,
            tuple(sorted(observations)),
            J[cursor:cursor + rows],
        ))
        cursor += rows

    add_block(
        "marginal_prior",
        historical,
        prior.residual(states),
    )

    for key, factor in sorted(active_imu.items()):
        i, j = _edge(key, frames)

        if i not in states or j not in states:
            raise FactorSupportError("IMU factor outside live window")

        add_block(
            f"imu:{i}:{j}",
            _imu_ids(key, frames),
            whitened_inertial_residual(
                states[i], states[j], factor
            ),
        )

    for key, observation in sorted(active_lidar.items()):
        i, j = _edge(key, frames)

        if i not in states or j not in states:
            raise FactorSupportError("LiDAR factor outside live window")

        add_block(
            f"lidar:{i}:{j}",
            (_lidar_id(key, frames),),
            lidar_residual(
                states[i], states[j], observation
            ),
        )

    if cursor != J.shape[0]:
        raise FactorSupportError(
            "Not all fitted residual rows have an owning factor"
        )

    report = analyze_factor_support(
        width,
        blocks,
        relative_rank_tolerance=relative_rank_tolerance,
        maximum_condition=maximum_condition,
    )

    lidar_present = bool(active_lidar)

    report.update({
        "active_imu_factor_count": len(active_imu),
        "active_lidar_factor_count": len(active_lidar),
        "current_lidar_factor_available": lidar_present,
        "historical_measurements_in_prior": len(historical),
        "availability_diagnostic": (
            "NUMERICALLY_UNAVAILABLE"
            if report["status"] != "NUMERICALLY_SUPPORTED"
            else (
                "CURRENT_LIDAR_SUPPORTED"
                if lidar_present
                else "NO_CURRENT_LIDAR_FACTOR"
            )
        ),
        "fitted_nonlinear_jacobian_used": True,
        "schur_prior_represents_historical_measurements": True,
        "synthetic_initial_anchor_is_physical": False,
        "physical_observability_verified": False,
        "calibrated_uncertainty_available": False,
        "operational_safety_availability_verified": False,
    })

    return report
