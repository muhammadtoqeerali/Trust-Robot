"""Development-only marginalized 15D LiDAR-IMU fusion.

Uses the existing frozen LiDAR frontend, covariance-aware IMU
preintegration and 15D Schur information-prior engine.

A factor absorbed into a Schur prior is removed from the
active factor pool. The same evidence cannot be reused as
a new independent measurement.

Schur priors use fixed first-estimate linearization.
The initial anchor and noise values are synthetic assumptions.

No physical calibration, independent reference, health
probability or real robot operation is claimed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import scipy
from scipy.optimize import least_squares

from trust_robot.analytic_inertial_15d import (
    DT,
    as_pose,
    initial_state,
    make_fixture,
    predict_imu,
    lidar_residual,
    score,
)
from trust_robot.analytic_preintegrated_fusion import (
    CONDITIONS,
    NODE_FRAMES,
    make_factors,
    whitened_inertial_residual,
)
from trust_robot.analytic_schur_marginalization import (
    STATE_DIM,
    synthetic_initial_anchor,
    marginalize_one,
)
from trust_robot.factor_conditioning import (
    assert_factor_scale_execution_authorized,
    FactorConditioningContractError,
)
from trust_robot.auxiliary_consistency import (
    assert_consistency_execution_authorized,
    AuxiliaryConsistencyContractError,
)

SCHEMA = "TRUST_ROBOT_ANALYTIC_MARGINALIZED_FUSION_DEV_V1"
WINDOW = 3
INITIAL_ANCHOR_SIGMA = 0.01
MAX_NFEV = 70


def canonical(value):
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ) + "\n"
    ).encode("utf-8")


def active_factors(factors, live_nodes, consumed):
    """Select only unused factors fully inside the active window."""
    live = set(live_nodes)

    return {
        key: value
        for key, value in sorted(factors.items())
        if (
            key not in consumed
            and key[0] in live
            and key[1] in live
        )
    }


def selected_residuals(
    states,
    prior,
    inertial,
    lidar,
):
    """One prior plus one occurrence of each active factor."""
    if not set(prior.node_ids).issubset(states):
        raise ValueError(
            "Prior references a state outside the window"
        )

    pieces = [prior.residual(states)]

    for (i, j), factor in sorted(inertial.items()):
        pieces.append(
            whitened_inertial_residual(
                states[i],
                states[j],
                factor,
            )
        )

    for (i, j), observed in sorted(lidar.items()):
        pieces.append(
            lidar_residual(
                states[i],
                states[j],
                observed,
            )
        )

    result = np.concatenate(pieces)

    if not np.isfinite(result).all():
        raise ValueError(
            "Nonfinite factor-graph residual"
        )

    return result


def estimate_marginalized(
    fixture, *, node_frames=NODE_FRAMES, factor_factory=make_factors
):
    """Preserved three-argument public estimator entry point.

    Legacy estimator behavior is retained without an added support
    policy or a change to its original calling convention.
    """
    return _estimate_marginalized_impl(
        fixture,
        node_frames=node_frames,
        factor_factory=factor_factory,
    )


def estimate_marginalized_with_support(
    fixture, *, node_frames=NODE_FRAMES, factor_factory=make_factors,
    support_policy="report",
    support_max_condition=1e14,
    support_relative_rank_tolerance=1e-12,
    require_active_lidar=False,
):
    """Explicit opt-in numerical support reporting and admission.

    No physical observability, calibrated covariance or trust-layer
    authorization is inferred by this diagnostic interface.
    """
    return _estimate_marginalized_impl(
        fixture,
        node_frames=node_frames,
        factor_factory=factor_factory,
        support_policy=support_policy,
        support_max_condition=support_max_condition,
        support_relative_rank_tolerance=(
            support_relative_rank_tolerance
        ),
        require_active_lidar=require_active_lidar,
    )


def _estimate_marginalized_impl(
    fixture, *, node_frames=NODE_FRAMES, factor_factory=make_factors,
    support_policy="legacy",
    support_max_condition=1e14,
    support_relative_rank_tolerance=1e-12,
    require_active_lidar=False,
):
    """Estimator consumes synthetic sensor fields, never truth."""

    if (
        len(node_frames) < 3
        or node_frames[0] != 0
        or any(b <= a for a, b in zip(node_frames, node_frames[1:]))
    ):
        raise ValueError('Invalid estimator node chronology')

    if support_policy not in ("legacy", "report", "require"):
        raise ValueError("Invalid estimator support policy")
    if not isinstance(require_active_lidar, bool):
        raise ValueError("Invalid current-LiDAR requirement")

    inertial_all, lidar_all, source_counts = factor_factory(
        fixture
    )

    states = {0: initial_state()}
    prior = synthetic_initial_anchor(
        states[0],
        sigma=INITIAL_ANCHOR_SIGMA,
    )

    live = [0]

    consumed_imu = set()
    consumed_lidar = set()

    windows = []
    eliminations = []

    for end in range(1, len(node_frames)):

        # Initialize the new state exclusively from IMU readings.
        predicted = states[end-1].copy()

        for sample in range(
            node_frames[end-1],
            node_frames[end],
        ):
            predicted = predict_imu(
                predicted,
                fixture["imu"][sample],
            )

        states[end] = predicted
        live.append(end)

        if len(live) > WINDOW:
            raise ValueError(
                "Rolling window exceeded its size limit"
            )

        active_imu = active_factors(
            inertial_all,
            live,
            consumed_imu,
        )
        active_lidar = active_factors(
            lidar_all,
            live,
            consumed_lidar,
        )

        if len(active_imu) != len(live) - 1:
            raise ValueError(
                "Missing active inertial chain factor"
            )

        expected_shape = (
            STATE_DIM * len(live),
        )

        x0 = np.concatenate([
            states[k].copy() for k in live
        ])

        def objective(flat):
            if np.shape(flat) != expected_shape:
                raise ValueError(
                    "Invalid optimizer variable dimension"
                )

            candidate = {
                k: flat[
                    i*STATE_DIM:(i+1)*STATE_DIM
                ]
                for i, k in enumerate(live)
            }

            return selected_residuals(
                candidate,
                prior,
                active_imu,
                active_lidar,
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

        local_rank = int(
            np.linalg.matrix_rank(
                fitted.jac,
                tol=1e-7,
            )
        )
        required_rank = len(x0)

        if not (
            fitted.success
            and np.isfinite(fitted.x).all()
            and math.isfinite(float(fitted.cost))
            and local_rank == required_rank
        ):
            raise ValueError(
                f"Marginalized window solve failed at {end}"
            )

        window_support = None

        if support_policy != "legacy":
            from trust_robot.analytic_marginalized_support import (
                audit_marginalized_window,
            )

            window_support = audit_marginalized_window(
                fitted.jac,
                fitted.x,
                live,
                node_frames,
                prior,
                active_imu,
                active_lidar,
                consumed_imu,
                consumed_lidar,
                relative_rank_tolerance=(
                    support_relative_rank_tolerance
                ),
                maximum_condition=support_max_condition,
            )

            if support_policy == "require" and (
                window_support["status"]
                != "NUMERICALLY_SUPPORTED"
                or (
                    require_active_lidar
                    and not window_support[
                        "current_lidar_factor_available"
                    ]
                )
            ):
                raise ValueError(
                    f"Marginalized window support unavailable at {end}: "
                    f"{window_support['availability_diagnostic']}"
                )

        for i, k in enumerate(live):
            states[k] = fitted.x[
                i*STATE_DIM:(i+1)*STATE_DIM
            ].copy()

        windows.append({
            "end_node": end,
            "nodes_optimized": list(live),
            "accepted": True,
            "jacobian_rank": local_rank,
            "required_rank": required_rank,
            "active_imu_factor_count": len(active_imu),
            "active_lidar_factor_count": len(active_lidar),
            "cost": float(fitted.cost),
            "function_evaluations": int(fitted.nfev),
            "initial_anchor_is_physical_measurement": False,
            "local_rank_proves_physical_observability": False,
        })

        if window_support is not None:
            windows[-1]["factor_support"] = window_support

        # Eliminate the oldest node only when the window is full.
        if len(live) == WINDOW:

            oldest = live[0]

            incident_imu = {
                key: value
                for key, value in active_imu.items()
                if oldest in key
            }

            incident_lidar = {
                key: value
                for key, value in active_lidar.items()
                if oldest in key
            }

            if not incident_imu:
                raise ValueError(
                    "No inertial factor for departing state"
                )

            # No future factor may still depend on this node.
            for key in (
                list(inertial_all)
                + list(lidar_all)
            ):
                if (
                    oldest in key
                    and max(key) > end
                ):
                    raise ValueError(
                        "Attempted premature marginalization"
                    )

            previous_prior = prior

            def elimination_residual(candidate):
                return selected_residuals(
                    candidate,
                    previous_prior,
                    incident_imu,
                    incident_lidar,
                )

            next_prior, details = marginalize_one(
                tuple(live),
                {
                    k: states[k].copy()
                    for k in live
                },
                elimination_residual,
                oldest,
            )

            new_imu = set(incident_imu)
            new_lidar = set(incident_lidar)

            if (
                new_imu & consumed_imu
                or new_lidar & consumed_lidar
            ):
                raise ValueError(
                    "Measurement included in prior twice"
                )

            consumed_imu.update(new_imu)
            consumed_lidar.update(new_lidar)

            live.pop(0)
            prior = next_prior

            if set(prior.node_ids) != set(live):
                raise ValueError(
                    "Schur prior node ownership mismatch"
                )

            eliminations.append({
                **details,
                "consumed_imu_factor_keys": [
                    list(k) for k in sorted(new_imu)
                ],
                "consumed_lidar_factor_keys": [
                    list(k) for k in sorted(new_lidar)
                ],
                "prior_nodes_after_elimination":
                    list(prior.node_ids),
            })

        # Factor bookkeeping is checked after each solve.
        if consumed_imu & set(
            active_factors(
                inertial_all,
                live,
                consumed_imu,
            )
        ):
            raise ValueError(
                "Active IMU factor double counted"
            )

        if consumed_lidar & set(
            active_factors(
                lidar_all,
                live,
                consumed_lidar,
            )
        ):
            raise ValueError(
                "Active LiDAR factor double counted"
            )

    final_active_imu = active_factors(
        inertial_all,
        live,
        consumed_imu,
    )
    final_active_lidar = active_factors(
        lidar_all,
        live,
        consumed_lidar,
    )

    if (
        consumed_imu | set(final_active_imu)
    ) != set(inertial_all):
        raise ValueError(
            "Lost or unaccounted inertial factors"
        )

    if (
        consumed_lidar | set(final_active_lidar)
    ) != set(lidar_all):
        raise ValueError(
            "Lost or unaccounted LiDAR factors"
        )

    if (
        consumed_imu & set(final_active_imu)
        or consumed_lidar & set(final_active_lidar)
    ):
        raise ValueError(
            "Consumed measurements still active"
        )

    records = []

    for node, frame in enumerate(node_frames):
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
        **source_counts,
        "accepted_window_count": len(windows),
        "window_count": len(windows),
        "window_max_nodes": WINDOW,
        "schur_elimination_count": len(eliminations),
        "windows": windows,
        "eliminations": eliminations,
        "consumed_imu_keys": [
            list(k) for k in sorted(consumed_imu)
        ],
        "consumed_lidar_keys": [
            list(k) for k in sorted(consumed_lidar)
        ],
        "remaining_imu_keys": [
            list(k) for k in sorted(final_active_imu)
        ],
        "remaining_lidar_keys": [
            list(k) for k in sorted(final_active_lidar)
        ],
        "final_live_nodes": list(live),
        "final_prior_nodes": list(prior.node_ids),
        "final_prior_information_rank": int(
            prior.square_root_information.shape[0]
        ),
        "factor_reuse_after_marginalization": False,
        "unaccounted_factor_count": 0,
        "synthetic_initial_anchor": True,
        "first_estimate_linearized_prior": True,
        "nonlinear_posterior_consistency_proven": False,
    }

    if not (
        len(windows) == len(node_frames) - 1
        and len(eliminations) == len(node_frames) - 2
        and live == list(range(len(node_frames)-2, len(node_frames)))
    ):
        raise ValueError(
            "Unexpected rolling-window chronology"
        )

    return records, audit


def execute():
    outputs = {}
    results = {}

    for condition in CONDITIONS:

        fixture, truth = make_fixture(condition)

        records, audit = estimate_marginalized(
            fixture
        )

        metrics = score(
            records,
            [truth[k] for k in NODE_FRAMES],
        )

        if len(records) != 5:
            raise ValueError(
                "Missing marginalized trajectory nodes"
            )

        if not (
            audit["accepted_window_count"] == 4
            and audit["schur_elimination_count"] == 3
            and audit["unaccounted_factor_count"] == 0
            and audit["factor_reuse_after_marginalization"]
            is False
        ):
            raise ValueError(
                "Marginalization accounting failed"
            )

        filename = (
            f"{condition}_marginalized_states.jsonl"
        )

        outputs[filename] = b"".join(
            canonical(record)
            for record in records
        )

        results[condition] = {
            "fixture_metrics": metrics,
            "solver": audit,
        }

    clean = results["clean"]["fixture_metrics"]

    if (
        clean["fixture_position_rmse_m"] >= 1e-3
        or clean["fixture_rotation_rmse_deg"] >= 1e-3
        or clean["fixture_velocity_rmse_m_s"] >= 1e-3
    ):
        raise ValueError(
            "Clean synthetic mathematical closure failed"
        )

    for gate, error_type in (
        (
            assert_factor_scale_execution_authorized,
            FactorConditioningContractError,
        ),
        (
            assert_consistency_execution_authorized,
            AuxiliaryConsistencyContractError,
        ),
    ):
        try:
            gate()
        except error_type:
            pass
        else:
            raise ValueError(
                "Frozen authorization gate unexpectedly opened"
            )

    manifest = {
        "schema": SCHEMA,
        "status": (
            "LOCAL_ANALYTIC_MARGINALIZED_FUSION_VALIDATED"
        ),
        "conditions": list(CONDITIONS),
        "node_frames": list(NODE_FRAMES),
        "state_dimension": STATE_DIM,
        "window_max_nodes": WINDOW,
        "results": results,
        "numeric_environment": {
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "scipy": scipy.__version__,
        },
        "artifact_sha256": {
            name: hashlib.sha256(blob).hexdigest()
            for name, blob in sorted(outputs.items())
        },
        "covariance_aware_imu_preintegration_reused": True,
        "frozen_lidar_frontend_reused": True,
        "schur_marginalization_integrated": True,
        "factor_ownership_checked": True,
        "first_estimate_linearization": True,
        "independent_reference_used": False,
        "physical_observability_proven": False,
        "posterior_consistency_proven": False,
        "sensor_timing_calibrated": False,
        "physical_extrinsics_calibrated": False,
        "health_probabilities_inferred": False,
        "factor_conditioning_executed": False,
        "real_robot_contacted": False,
        "full_trust_robot_system_complete": False,
    }

    return outputs, manifest


def run(destination):
    if (
        destination.exists()
        or destination.is_symlink()
        or not destination.parent.is_dir()
        or destination.parent.is_symlink()
    ):
        raise ValueError(
            "Unsafe or existing output destination"
        )

    first, manifest = execute()
    second, repeated_manifest = execute()

    if (
        first != second
        or manifest != repeated_manifest
    ):
        raise ValueError(
            "Non-deterministic marginalization results"
        )

    manifest["repeat_derivation_identical"] = True
    destination.mkdir(mode=0o700)

    for filename, content in sorted(first.items()):
        (destination / filename).write_bytes(content)

    (destination / "marginalized_manifest_v1.json").write_text(
        json.dumps(
            manifest,
            sort_keys=True,
            indent=2,
        ) + "\n"
    )

    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    result = run(args.output)

    for condition in CONDITIONS:
        row = result["results"][condition]

        print(
            condition.upper() + "_WINDOW_SOLVES=",
            row["solver"]["accepted_window_count"]
        )
        print(
            condition.upper() + "_SCHUR_ELIMINATIONS=",
            row["solver"]["schur_elimination_count"]
        )
        print(
            condition.upper() + "_POSITION_RMSE_M=",
            round(
                row["fixture_metrics"][
                    "fixture_position_rmse_m"
                ],
                8,
            ),
        )
        print(
            condition.upper() + "_ROTATION_RMSE_DEG=",
            round(
                row["fixture_metrics"][
                    "fixture_rotation_rmse_deg"
                ],
                8,
            ),
        )

    print("MEASUREMENT_OWNERSHIP=PASS")
    print("NO_FACTOR_DOUBLE_COUNTING=PASS")
    print("DETERMINISTIC_REPEAT=PASS")
    print("MARGINALIZED_15D_FUSION=PASS")


if __name__ == "__main__":
    main()
