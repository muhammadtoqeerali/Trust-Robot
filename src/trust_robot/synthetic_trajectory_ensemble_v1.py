"""A31-10: fixed-seed synthetic trajectory ablation ensemble.

Four declared toy trust policies are evaluated against
the same synthetic trial data for each seed.

Physical ground truth, sensor calibration, clock
accuracy, confidence calibration and localization
performance are not established by these simulations.
"""

from __future__ import annotations

import math
import random

from trust_robot.synthetic_event_axis_v1 import (
    check_synthetic_event_axis,
)

from trust_robot.synthetic_15d_trajectory_v1 import (
    run_toy_trajectory,
)

SCHEMA = "TRUST_ROBOT_R135_A31_10_TOY_ENSEMBLE_V1"

ANCHOR_NS = 10**18
STEP_NS = 10**9
STEPS = 6

SCENARIOS = frozenset({
    "lossless_reference",
    "synthetic_lidar_suppression",
    "synthetic_stereo_image_suppression",
    "synthetic_imu_suppression",
    "synthetic_queue_pressure",
})

VARIANTS = (
    "counterfactual_all_candidates",
    "toy_nis_counterfactual",
    "scheduled_delivery_only",
    "combined_toy_screening",
)


class SyntheticEnsembleError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise SyntheticEnsembleError(message)


def eye(n, diagonal):
    return [
        [float(diagonal) if i == j else 0.0
         for j in range(n)]
        for i in range(n)
    ]


def check_mask(mask):
    require(
        type(mask) is list
        and len(mask) == STEPS
        and all(type(x) is bool for x in mask),
        "Invalid fixed six-step synthetic delivery mask",
    )


def build_seeded_trial(seed, mask):
    """Generate one declared synthetic truth/noise realization."""

    require(
        type(seed) is int
        and 0 <= seed <= 65535,
        "Invalid fixed synthetic seed",
    )

    check_mask(mask)

    rng = random.Random(seed)
    steps = []

    for i in range(STEPS):
        truth = [0.0] * 15

        # Synthetic constant-velocity trajectory.
        truth[0] = float(i + 1)
        truth[3] = 1.0

        # Declared synthetic measurement noise.
        noise = rng.gauss(0.0, 0.25)

        # Fixed injected outlier at recovery.
        outlier = 6.0 if i == 4 else 0.0

        measurement = truth[0] + noise + outlier

        steps.append({
            "index": i,
            "dt_ns": STEP_NS,
            "software_available": mask[i],
            "synthetic_truth": {
                "source_kind": "SYNTHETIC_TRUTH_ONLY",
                "state_15": truth,
                "reference_protocol":
                    "DECLARED_TOY_KINEMATICS_V1",
            },
            "candidate": {
                "source_kind": "SYNTHETIC_ONLY",
                "stream": "imu",
                "factor_kind": "toy_position_xyz",
                "sequence": i,
                "clock_domain": "synthetic_ensemble_clock",
                "event_stamp_ns":
                    ANCHOR_NS + (i + 1) * STEP_NS,
                "measurement_xyz": [
                    measurement, 0.0, 0.0
                ],
                "noise_covariance_3x3":
                    eye(3, 0.0625),
            },
        })

    check_synthetic_event_axis(
        steps,
        anchor_ns=ANCHOR_NS,
    )

    return steps


def evaluate_seeded_ensemble(
    seeds,
    scenario_masks,
    *,
    nis_limit_num=9,
    nis_limit_den=1,
):
    """Compare fixed toy policies with paired seed realizations."""

    require(
        type(seeds) is list
        and 2 <= len(seeds) <= 16
        and all(
            type(s) is int and 0 <= s <= 65535
            for s in seeds
        )
        and seeds == sorted(set(seeds)),
        "Seed list must be unique, sorted and bounded",
    )

    require(
        type(scenario_masks) is dict
        and set(scenario_masks) == SCENARIOS,
        "Unexpected software scenario inventory",
    )

    require(
        type(nis_limit_num) is int
        and type(nis_limit_den) is int
        and 0 <= nis_limit_num <= 1000000
        and 1 <= nis_limit_den <= 1000000,
        "Invalid predeclared NIS threshold",
    )

    for mask in scenario_masks.values():
        check_mask(mask)

    results = {}

    for name in sorted(SCENARIOS):
        mask = scenario_masks[name]
        trials = []

        for seed in seeds:
            steps = build_seeded_trial(seed, mask)

            axis = check_synthetic_event_axis(
                steps,
                anchor_ns=ANCHOR_NS,
            )

            if not axis["time_axis_consistent"]:
                raise SyntheticEnsembleError(
                    "Synthetic time-axis validation failed"
                )

            result = run_toy_trajectory(
                [0.0] * 15,
                eye(15, 1.0),
                steps,
                nis_limit_num=nis_limit_num,
                nis_limit_den=nis_limit_den,
                acceleration_noise=0.0,
            )

            require(
                result["real_factor_count"] == 0
                and result["real_factor_admission"] == "DENIED"
                and result["m2dgr_gates"] == "11_CLOSED"
                and result["estimator_invoked"] is False,
                "Physical estimator boundary changed",
            )

            per_policy = {}

            for variant in VARIANTS:
                row = result["variants"][variant]
                statistics = row["toy_consistency"]

                rmse = statistics["toy_position_rmse"]
                nees = statistics["mean_toy_nees_15d"]
                accepted = row["accepted_toy_updates"]

                require(
                    math.isfinite(rmse)
                    and math.isfinite(nees)
                    and rmse >= 0
                    and nees >= 0
                    and type(accepted) is int
                    and 0 <= accepted <= STEPS,
                    "Invalid descriptive toy metric",
                )

                per_policy[variant] = {
                    "accepted_synthetic_updates": accepted,
                    "toy_position_rmse": rmse,
                    "mean_toy_nees_15d": nees,
                }

            require(
                per_policy[
                    "counterfactual_all_candidates"
                ]["accepted_synthetic_updates"] == STEPS,
                "Counterfactual accounting mismatch",
            )

            require(
                per_policy[
                    "scheduled_delivery_only"
                ]["accepted_synthetic_updates"] == sum(mask),
                "Synthetic delivery accounting mismatch",
            )

            require(
                per_policy[
                    "combined_toy_screening"
                ]["accepted_synthetic_updates"] <= sum(mask),
                "Combined policy violates simulated delivery",
            )

            trials.append({
                "synthetic_seed": seed,
                "time_axis_consistent": True,
                "policies": per_policy,
                "real_factor_count": 0,
            })

        summaries = {}

        for variant in VARIANTS:
            records = [
                item["policies"][variant]
                for item in trials
            ]

            summaries[variant] = {
                "mean_toy_position_rmse": sum(
                    r["toy_position_rmse"]
                    for r in records
                ) / len(records),
                "mean_toy_nees_15d": sum(
                    r["mean_toy_nees_15d"]
                    for r in records
                ) / len(records),
                "mean_synthetic_updates": sum(
                    r["accepted_synthetic_updates"]
                    for r in records
                ) / len(records),
            }

        results[name] = {
            "synthetic_delivery_mask": list(mask),
            "seed_count": len(seeds),
            "trials": trials,
            "summary": summaries,
        }

    return {
        "schema": SCHEMA,
        "status": "FIXED_MULTI_SEED_SYNTHETIC_EXPERIMENT_ONLY",
        "seeds": list(seeds),
        "scenario_count": len(results),
        "steps_per_seed": STEPS,
        "synthetic_anchor_ns": ANCHOR_NS,
        "synthetic_propagation_interval_ns": STEP_NS,
        "synthetic_measurement_noise_std": 0.25,
        "synthetic_injected_outlier_step": 4,
        "synthetic_injected_outlier_value": 6.0,
        "declared_toy_nis_limit": [
            nis_limit_num, nis_limit_den,
        ],
        "scenarios": results,
        "time_axis_consistency_required": True,
        "counterfactual_undelivered_updates_not_physical": True,
        "statistical_calibration_established": False,
        "physical_reference_verified": False,
        "physical_clock_verified": False,
        "physical_health_probabilities_generated": False,
        "real_factor_weights_generated": False,
        "estimator_invoked": False,
        "real_factor_count": 0,
        "real_factor_admission": "DENIED",
        "m2dgr_gates": "11_CLOSED",
    }


def evaluate_real_robot_ensemble(*args, **kwargs):
    raise SyntheticEnsembleError(
        "Synthetic seeded evaluations cannot qualify "
        "real robot localization"
    )
