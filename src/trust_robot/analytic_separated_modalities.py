"""Independent synthetic camera/LiDAR residuals in a 15D estimator.

Uses the existing IMU preintegration and Schur marginalizer.

Unlike the original compatibility adapter, camera and LiDAR
may both contribute relative-pose measurements on the same edge.

Each modality has separate measurement identities, residual
blocks, consumption ledgers, and historical-prior bookkeeping.

Camera relative poses are MANUFACTURED, not estimated from images.
The fixed residual scales are numerical development assumptions,
not calibrated modality reliability or runtime health weighting.

Real recorded inputs are not authorized by this implementation.
"""
from __future__ import annotations

import hashlib
import json
import math

import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation

from trust_robot.clean_backbone import PoseSE3
from trust_robot.analytic_inertial_15d import (
    DT,
    SIGMA_LIDAR_P,
    SIGMA_LIDAR_R,
    as_pose,
    initial_state,
    lidar_residual,
    make_fixture,
    predict_imu,
)
from trust_robot.analytic_preintegrated_fusion import (
    NODE_FRAMES,
    make_factors,
    whitened_inertial_residual,
)
from trust_robot.analytic_marginalized_fusion import (
    WINDOW,
    MAX_NFEV,
    INITIAL_ANCHOR_SIGMA,
    active_factors,
)
from trust_robot.analytic_schur_marginalization import (
    STATE_DIM,
    synthetic_initial_anchor,
    marginalize_one,
)
from trust_robot.analytic_estimator_robustness import (
    validate_fixture,
)
from trust_robot.analytic_factor_support import (
    analyze_factor_support,
    make_linear_factor,
)
from trust_robot.multimodal_factor_interface import (
    SyntheticPoseFactor,
)
from trust_robot.analytic_three_modality_bridge import (
    manufactured_camera_packets,
)

SCHEMA = "TRUST_ROBOT_ANALYTIC_SEPARATED_MODALITIES_DEV_V1"

# Fixed manufactured numerical residual scales.
# These are not fitted, calibrated or health-conditioned.
CAMERA_POSITION_SCALE_M = 0.03
CAMERA_ROTATION_SCALE_RAD = 0.04

SEEDS = (13, 31, 71)


def camera_residual(previous, current, observed):
    """Six-dimensional manufactured visual-motion residual.

    It shares the existing relative-body-pose convention
    with the LiDAR residual but uses a separately declared
    numerical scale for this synthetic development fixture.
    """
    if not isinstance(observed, PoseSE3):
        raise ValueError("Invalid manufactured camera pose")

    predicted = (
        as_pose(previous)
        .inverse()
        .compose(as_pose(current))
    )

    error = observed.inverse().compose(predicted)
    q = error.quaternion_wxyz

    rotation = Rotation.from_quat(
        [q[1], q[2], q[3], q[0]]
    )

    answer = np.concatenate((
        np.asarray(error.translation_m, dtype=float)
        / CAMERA_POSITION_SCALE_M,
        rotation.as_rotvec()
        / CAMERA_ROTATION_SCALE_RAD,
    ))

    if answer.shape != (6,) or not np.isfinite(answer).all():
        raise ValueError("Invalid camera residual")

    return answer


def camera_factor_map(packets):
    """Validate synthetic camera provenance and factor identity."""
    result = {}
    ids = set()

    for packet in packets:
        if not isinstance(packet, SyntheticPoseFactor):
            raise ValueError("Unexpected camera factor type")

        if packet.modality != "camera":
            raise ValueError("Only camera packets belong here")

        edge = packet.edge

        if (
            edge[1] >= len(NODE_FRAMES)
            or edge[1]-edge[0] > 2
        ):
            raise ValueError("Invalid camera estimator edge")

        if packet.measurement_id in ids:
            raise ValueError("Duplicate camera measurement identity")

        if edge in result:
            raise ValueError("Duplicate camera graph-edge factor")

        ids.add(packet.measurement_id)
        result[edge] = packet

    return dict(sorted(result.items()))


def selected_residuals_separated(
    states,
    prior,
    imu,
    lidar,
    camera,
):
    """Order prior/IMU/LiDAR/camera independently and exactly once."""
    if not set(prior.node_ids).issubset(states):
        raise ValueError("Schur prior references absent states")

    pieces = [prior.residual(states)]

    for (i, j), factor in sorted(imu.items()):
        pieces.append(
            whitened_inertial_residual(
                states[i], states[j], factor
            )
        )

    for (i, j), observed in sorted(lidar.items()):
        pieces.append(
            lidar_residual(
                states[i], states[j], observed
            )
        )

    for (i, j), packet in sorted(camera.items()):
        pieces.append(
            camera_residual(
                states[i],
                states[j],
                packet.measurement,
            )
        )

    result = np.concatenate(pieces)

    if not np.isfinite(result).all():
        raise ValueError("Nonfinite separated factor residual")

    return result


def audit_window_support(
    fitted,
    live,
    prior,
    imu,
    lidar,
    camera,
    consumed_imu,
    consumed_lidar,
    consumed_camera,
):
    """Audit Jacobian rows with source-specific ownership.

    The Schur prior owns historical measurements, rather than
    treating those historical inputs as new active factors.
    """
    width = STATE_DIM*len(live)
    x = fitted.x
    J = fitted.jac

    states = {
        k: x[i*STATE_DIM:(i+1)*STATE_DIM]
        for i, k in enumerate(live)
    }

    history = {"synthetic_initial_anchor"}

    for i, j in consumed_imu:
        history.update(
            f"imu_sample:{sample}"
            for sample in range(
                NODE_FRAMES[i], NODE_FRAMES[j]
            )
        )

    for i, j in consumed_lidar:
        history.add(f"lidar_edge:{i}:{j}")

    history.update(consumed_camera.values())

    factors = []
    cursor = 0

    def append_block(name, identities, residual):
        nonlocal cursor
        size = len(residual)

        if cursor + size > J.shape[0]:
            raise ValueError("Factor/Jacobian row mismatch")

        factors.append(make_linear_factor(
            name,
            tuple(sorted(identities)),
            J[cursor:cursor+size],
        ))

        cursor += size

    append_block(
        "historical_schur_prior",
        history,
        prior.residual(states),
    )

    for (i, j), factor in sorted(imu.items()):
        append_block(
            f"imu:{i}:{j}",
            (
                f"imu_sample:{sample}"
                for sample in range(
                    NODE_FRAMES[i], NODE_FRAMES[j]
                )
            ),
            whitened_inertial_residual(
                states[i], states[j], factor
            ),
        )

    for (i, j), observed in sorted(lidar.items()):
        append_block(
            f"lidar:{i}:{j}",
            (f"lidar_edge:{i}:{j}",),
            lidar_residual(
                states[i], states[j], observed
            ),
        )

    for (i, j), packet in sorted(camera.items()):
        append_block(
            f"camera:{i}:{j}",
            (packet.measurement_id,),
            camera_residual(
                states[i], states[j],
                packet.measurement,
            ),
        )

    if cursor != J.shape[0]:
        raise ValueError("Unowned factor/Jacobian rows")

    report = analyze_factor_support(
        width,
        factors,
        relative_rank_tolerance=1e-12,
        maximum_condition=1e14,
    )

    report.update({
        "active_imu_factors": len(imu),
        "active_lidar_factors": len(lidar),
        "active_camera_factors": len(camera),
        "prior_represents_historical_measurements": True,
        "separate_source_residual_blocks": True,
        "real_sensor_noise_calibrated": False,
        "physical_observability_verified": False,
        "runtime_health_weighting_enabled": False,
    })

    return report


def estimate_separated(
    fixture,
    camera_packets=(),
    *,
    require_camera=False,
    require_numerical_support=False,
):
    """Run the existing mathematical optimizer with separate sources.

    This is a synthetic-only sibling of the published estimator.
    The published estimator's public API and implementation remain
    unchanged.

    Camera factors are not allowed to replace or overwrite LiDAR
    factors, even when they use the same graph edge.
    """
    if (
        type(require_camera) is not bool
        or type(require_numerical_support) is not bool
    ):
        raise ValueError("Invalid numerical admission policy")

    validate_fixture(fixture, node_frames=NODE_FRAMES)

    inertial_all, lidar_all, counts = make_factors(fixture)
    camera_all = camera_factor_map(camera_packets)

    states = {0: initial_state()}

    prior = synthetic_initial_anchor(
        states[0], sigma=INITIAL_ANCHOR_SIGMA
    )

    live = [0]

    consumed_imu = set()
    consumed_lidar = set()
    consumed_camera = {}

    windows = []
    eliminations = []

    for end in range(1, len(NODE_FRAMES)):
        predicted = states[end-1].copy()

        for sample in range(
            NODE_FRAMES[end-1], NODE_FRAMES[end]
        ):
            predicted = predict_imu(
                predicted, fixture["imu"][sample]
            )

        states[end] = predicted
        live.append(end)

        if len(live) > WINDOW:
            raise ValueError("Rolling window capacity exceeded")

        active_imu = active_factors(
            inertial_all, live, consumed_imu
        )
        active_lidar = active_factors(
            lidar_all, live, consumed_lidar
        )
        active_camera = active_factors(
            camera_all, live, set(consumed_camera)
        )

        if len(active_imu) != len(live)-1:
            raise ValueError("Incomplete active IMU chain")

        if require_camera and not active_camera:
            raise ValueError(
                "Camera factor unavailable in current window"
            )

        x0 = np.concatenate([
            states[k].copy() for k in live
        ])

        def objective(flat):
            if np.shape(flat) != (len(x0),):
                raise ValueError(
                    "Invalid nonlinear optimizer state dimension"
                )

            candidate = {
                k: flat[i*STATE_DIM:(i+1)*STATE_DIM]
                for i, k in enumerate(live)
            }

            return selected_residuals_separated(
                candidate,
                prior,
                active_imu,
                active_lidar,
                active_camera,
            )

        fitted = least_squares(
            objective,
            x0,
            method="trf",
            loss="linear",
            max_nfev=MAX_NFEV,
            ftol=1e-9,
            xtol=1e-9,
            gtol=1e-9,
        )

        rank = int(np.linalg.matrix_rank(
            fitted.jac, tol=1e-7
        ))

        if not (
            fitted.success
            and np.isfinite(fitted.x).all()
            and math.isfinite(float(fitted.cost))
            and rank == len(x0)
        ):
            raise ValueError(
                f"Separated nonlinear solve failed at {end}"
            )

        support = audit_window_support(
            fitted,
            live,
            prior,
            active_imu,
            active_lidar,
            active_camera,
            consumed_imu,
            consumed_lidar,
            consumed_camera,
        )

        if (
            require_numerical_support
            and support["status"] != "NUMERICALLY_SUPPORTED"
        ):
            raise ValueError(
                "Separated numerical support unavailable"
            )

        for i, node in enumerate(live):
            states[node] = fitted.x[
                i*STATE_DIM:(i+1)*STATE_DIM
            ].copy()

        windows.append({
            "end_node": end,
            "nodes_optimized": list(live),
            "accepted": True,
            "active_imu_factors": len(active_imu),
            "active_lidar_factors": len(active_lidar),
            "active_camera_factors": len(active_camera),
            "jacobian_rank": rank,
            "required_rank": len(x0),
            "cost": float(fitted.cost),
            "source_specific_support": support,
            "physical_observability_proven": False,
        })

        if len(live) == WINDOW:
            oldest = live[0]

            incident_imu = {
                k: v for k, v in active_imu.items()
                if oldest in k
            }
            incident_lidar = {
                k: v for k, v in active_lidar.items()
                if oldest in k
            }
            incident_camera = {
                k: v for k, v in active_camera.items()
                if oldest in k
            }

            if not incident_imu:
                raise ValueError(
                    "Departing state missing IMU factor"
                )

            for collection in (
                inertial_all, lidar_all, camera_all
            ):
                for edge in collection:
                    if oldest in edge and max(edge) > end:
                        raise ValueError(
                            "Premature marginalization"
                        )

            previous_prior = prior

            def eliminate_residual(candidate):
                return selected_residuals_separated(
                    candidate,
                    previous_prior,
                    incident_imu,
                    incident_lidar,
                    incident_camera,
                )

            next_prior, details = marginalize_one(
                tuple(live),
                {k: states[k].copy() for k in live},
                eliminate_residual,
                oldest,
            )

            new_imu = set(incident_imu)
            new_lidar = set(incident_lidar)
            new_camera = set(incident_camera)

            if (
                new_imu & consumed_imu
                or new_lidar & consumed_lidar
                or new_camera & set(consumed_camera)
            ):
                raise ValueError(
                    "Duplicate historical factor consumption"
                )

            consumed_imu.update(new_imu)
            consumed_lidar.update(new_lidar)

            consumed_camera.update({
                edge: packet.measurement_id
                for edge, packet in incident_camera.items()
            })

            live.pop(0)
            prior = next_prior

            if set(prior.node_ids) != set(live):
                raise ValueError("Schur prior ownership mismatch")

            eliminations.append({
                "eliminated_node": oldest,
                "consumed_imu_edges": [
                    list(k) for k in sorted(new_imu)
                ],
                "consumed_lidar_edges": [
                    list(k) for k in sorted(new_lidar)
                ],
                "consumed_camera_measurement_ids": [
                    incident_camera[k].measurement_id
                    for k in sorted(new_camera)
                ],
                "retained_prior_nodes": list(prior.node_ids),
                "information_summary": details,
            })

    remaining_imu = active_factors(
        inertial_all, live, consumed_imu
    )
    remaining_lidar = active_factors(
        lidar_all, live, consumed_lidar
    )
    remaining_camera = active_factors(
        camera_all, live, set(consumed_camera)
    )

    for all_factors, consumed, active in (
        (inertial_all, consumed_imu, remaining_imu),
        (lidar_all, consumed_lidar, remaining_lidar),
        (camera_all, set(consumed_camera), remaining_camera),
    ):
        if (
            consumed & set(active)
            or consumed | set(active) != set(all_factors)
        ):
            raise ValueError(
                "Unaccounted or duplicated modality factor"
            )

    if (
        len(windows) != len(NODE_FRAMES)-1
        or len(eliminations) != len(NODE_FRAMES)-2
        or live != [3, 4]
    ):
        raise ValueError(
            "Unexpected marginalized estimator chronology"
        )

    records = []

    for node, frame in enumerate(NODE_FRAMES):
        x = states[node]
        records.append({
            "node_index": node,
            "source_frame_index": frame,
            "synthetic_time_s": frame*DT,
            "position_m": x[:3].tolist(),
            "orientation_quaternion_wxyz": list(
                as_pose(x).quaternion_wxyz
            ),
            "velocity_m_s": x[6:9].tolist(),
            "gyro_bias_rad_s": x[9:12].tolist(),
            "accel_bias_m_s2": x[12:15].tolist(),
            "state_dimension": STATE_DIM,
            "reference_pose": None,
        })

    audit = {
        "schema": SCHEMA,
        **counts,
        "camera_factor_count": len(camera_all),
        "lidar_factor_count": len(lidar_all),
        "imu_factor_count": len(inertial_all),
        "accepted_window_count": len(windows),
        "schur_elimination_count": len(eliminations),
        "windows": windows,
        "eliminations": eliminations,
        "consumed_imu_keys": [
            list(k) for k in sorted(consumed_imu)
        ],
        "consumed_lidar_keys": [
            list(k) for k in sorted(consumed_lidar)
        ],
        "consumed_camera_ids": [
            consumed_camera[k]
            for k in sorted(consumed_camera)
        ],
        "remaining_imu_keys": [
            list(k) for k in sorted(remaining_imu)
        ],
        "remaining_lidar_keys": [
            list(k) for k in sorted(remaining_lidar)
        ],
        "remaining_camera_ids": [
            remaining_camera[k].measurement_id
            for k in sorted(remaining_camera)
        ],
        "final_prior_nodes": list(prior.node_ids),
        "factor_reuse_after_marginalization": False,
        "unaccounted_factor_count": 0,
        "independent_source_residual_blocks": True,
        "same_edge_camera_and_lidar_supported": True,
        "synthetic_initial_anchor": True,
        "physical_observability_verified": False,
        "real_sensor_factor_execution_authorized": False,
        "health_factor_conditioning_executed": False,
        "empirical_covariance_calibrated": False,
    }

    return records, audit


def execute_case(condition, seed, *, camera_enabled=True):
    if condition not in ("clean", "lidar_dropout"):
        raise ValueError("Invalid synthetic condition")

    if type(seed) is not int or seed < 0:
        raise ValueError("Invalid seed")

    if type(camera_enabled) is not bool:
        raise ValueError("Invalid camera toggle")

    fixture, truth = make_fixture(condition)

    packets = (
        manufactured_camera_packets(truth, seed=seed)
        if camera_enabled else ()
    )

    records, audit = estimate_separated(fixture, packets)

    state_bytes = canonical(records)

    return {
        "schema": SCHEMA,
        "condition": condition,
        "seed": seed,
        "camera_enabled": camera_enabled,
        "camera_factor_count": audit["camera_factor_count"],
        "lidar_factor_count": audit["lidar_factor_count"],
        "imu_factor_count": audit["imu_factor_count"],
        "accepted_window_count": audit["accepted_window_count"],
        "schur_elimination_count": audit[
            "schur_elimination_count"
        ],
        "camera_and_lidar_same_edge_count": (
            2 if camera_enabled and condition == "clean"
            else 1 if camera_enabled else 0
        ),
        "trajectory_sha256": hashlib.sha256(
            state_bytes
        ).hexdigest(),
        "factor_accounting_complete": (
            audit["unaccounted_factor_count"] == 0
            and not audit[
                "factor_reuse_after_marginalization"
            ]
        ),
        "physical_sensor_measurements": False,
        "independent_reference_used": False,
        "health_weighting_executed": False,
    }


def execute():
    cases = [
        execute_case(
            condition, seed, camera_enabled=enabled
        )
        for condition in ("clean", "lidar_dropout")
        for seed in SEEDS
        for enabled in (False, True)
    ]

    assert len(cases) == 12

    return {
        "schema": SCHEMA,
        "status": "SYNTHETIC_SEPARATED_MODALITY_SOLVES_COMPLETED",
        "case_count": len(cases),
        "cases": cases,
        "camera_visual_frontend_implemented": False,
        "real_three_modality_localization_verified": False,
        "real_sensor_scoring_authorized": False,
        "existing_estimator_modified": False,
        "frozen_protocols_modified": False,
    }


def canonical(value):
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ) + "\n"
    ).encode("utf-8")
