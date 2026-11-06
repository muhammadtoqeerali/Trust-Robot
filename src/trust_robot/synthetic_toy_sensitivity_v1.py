"""A31-12: paired, controlled toy algorithm sensitivity grid.

Varies synthetic outlier severity, toy NIS threshold,
and synthetic acceleration process variance.

Each seed reuses the same declared synthetic noise draw.
No physical data, sensor factors, or holdout scores are used.
"""

from __future__ import annotations

import math

from trust_robot.synthetic_event_axis_v1 import (
    check_synthetic_event_axis,
)

from trust_robot.synthetic_trajectory_ensemble_v1 import (
    ANCHOR_NS,
    VARIANTS,
    STEPS,
    build_seeded_trial,
)

from trust_robot.synthetic_15d_trajectory_v1 import (
    run_toy_trajectory,
)

SCHEMA = "TRUST_ROBOT_R135_A31_12_TOY_SENSITIVITY_V1"

# These are three explicitly synthetic delivery experiments,
# not three independent empirical sensor recordings.
PROFILES = {
    "continuous_toy_delivery": [True] * STEPS,
    "injected_toy_dropout_recovery": [
        True, True, False, False, True, True,
    ],
    "fully_withheld_toy_delivery": [False] * STEPS,
}

BASE_OUTLIER = 6.0
OUTLIER_STEP = 4


class ToySensitivityError(ValueError):
    pass


def require(ok, message):
    if not ok:
        raise ToySensitivityError(message)


def finite(value):
    return (
        type(value) in (int, float)
        and math.isfinite(value)
    )


def ordered_unique(values):
    return values == sorted(set(values))


def evaluate_toy_sensitivity(
    seeds,
    outlier_magnitudes,
    nis_limits,
    process_variances,
):
    require(
        type(seeds) is list
        and 2 <= len(seeds) <= 8
        and all(
            type(s) is int and 0 <= s <= 65535
            for s in seeds
        )
        and ordered_unique(seeds),
        "Invalid paired synthetic seed inventory",
    )

    require(
        type(outlier_magnitudes) is list
        and 1 <= len(outlier_magnitudes) <= 4
        and all(
            finite(v) and 0 <= v <= 100
            for v in outlier_magnitudes
        )
        and ordered_unique(outlier_magnitudes),
        "Invalid synthetic outlier magnitudes",
    )

    require(
        type(nis_limits) is list
        and 1 <= len(nis_limits) <= 4
        and all(
            type(x) is int and 0 <= x <= 1000000
            for x in nis_limits
        )
        and ordered_unique(nis_limits),
        "Invalid declared toy NIS limits",
    )

    require(
        type(process_variances) is list
        and 1 <= len(process_variances) <= 4
        and all(
            finite(x) and 0 <= x <= 100
            for x in process_variances
        )
        and ordered_unique(process_variances),
        "Invalid synthetic process variances",
    )

    experiments = (
        len(PROFILES)
        * len(outlier_magnitudes)
        * len(nis_limits)
        * len(process_variances)
        * len(seeds)
    )

    require(
        experiments <= 256,
        "Synthetic experiment grid exceeds bounded budget",
    )

    cells = []

    for profile in sorted(PROFILES):
        mask = PROFILES[profile]

        for outlier in outlier_magnitudes:
            for limit in nis_limits:
                for process_noise in process_variances:
                    trials = []

                    for seed in seeds:
                        # Generation is reseeded for each condition.
                        # Therefore paired seeds retain identical
                        # random-noise realizations across the grid.
                        steps = build_seeded_trial(
                            seed,
                            list(mask),
                        )

                        original = steps[OUTLIER_STEP][
                            "candidate"
                        ]["measurement_xyz"][0]

                        steps[OUTLIER_STEP]["candidate"][
                            "measurement_xyz"
                        ][0] = (
                            original - BASE_OUTLIER + outlier
                        )

                        axis = check_synthetic_event_axis(
                            steps,
                            anchor_ns=ANCHOR_NS,
                        )

                        require(
                            axis["time_axis_consistent"] is True
                            and axis["real_factor_count"] == 0,
                            "Toy event axis changed",
                        )

                        result = run_toy_trajectory(
                            [0.0] * 15,
                            [
                                [
                                    1.0 if i == j else 0.0
                                    for j in range(15)
                                ]
                                for i in range(15)
                            ],
                            steps,
                            nis_limit_num=limit,
                            nis_limit_den=1,
                            acceleration_noise=process_noise,
                        )

                        require(
                            result["real_factor_count"] == 0
                            and result["real_factor_admission"]
                            == "DENIED"
                            and result["m2dgr_gates"]
                            == "11_CLOSED"
                            and result["physical_ground_truth_verified"]
                            is False
                            and result[
                                "statistical_calibration_established"
                            ] is False,
                            "Toy trajectory scientific boundary changed",
                        )

                        per_policy = {}

                        for variant in VARIANTS:
                            row = result["variants"][variant]
                            summary = row["toy_consistency"]

                            per_policy[variant] = {
                                "toy_position_rmse":
                                    summary["toy_position_rmse"],
                                "mean_toy_nees_15d":
                                    summary["mean_toy_nees_15d"],
                                "accepted_toy_updates":
                                    row["accepted_toy_updates"],
                            }

                        require(
                            per_policy[
                                "scheduled_delivery_only"
                            ]["accepted_toy_updates"] == sum(mask),
                            "Synthetic delivery accounting mismatch",
                        )

                        require(
                            per_policy[
                                "combined_toy_screening"
                            ]["accepted_toy_updates"] <= sum(mask),
                            "Synthetic combined policy accounting mismatch",
                        )

                        trials.append({
                            "synthetic_seed": seed,
                            "policies": per_policy,
                        })

                    summaries = {}

                    for variant in VARIANTS:
                        summaries[variant] = {
                            "mean_toy_position_rmse": sum(
                                t["policies"][variant][
                                    "toy_position_rmse"
                                ]
                                for t in trials
                            ) / len(trials),
                            "mean_toy_nees_15d": sum(
                                t["policies"][variant][
                                    "mean_toy_nees_15d"
                                ]
                                for t in trials
                            ) / len(trials),
                            "mean_accepted_toy_updates": sum(
                                t["policies"][variant][
                                    "accepted_toy_updates"
                                ]
                                for t in trials
                            ) / len(trials),
                        }

                    cells.append({
                        "synthetic_profile": profile,
                        "delivery_mask": list(mask),
                        "outlier_magnitude": outlier,
                        "toy_nis_limit": limit,
                        "synthetic_process_variance":
                            process_noise,
                        "paired_seed_count": len(seeds),
                        "trials": trials,
                        "summary": summaries,
                    })

    require(
        len(cells) * len(seeds) == experiments,
        "Synthetic grid trial accounting differs",
    )

    return {
        "schema": SCHEMA,
        "status": "PAIRED_SYNTHETIC_SENSITIVITY_ONLY",
        "seeds": list(seeds),
        "toy_profile_count": len(PROFILES),
        "grid_cell_count": len(cells),
        "toy_trajectory_run_count": experiments,
        "fixed_injected_outlier_step": OUTLIER_STEP,
        "outlier_magnitudes": list(outlier_magnitudes),
        "toy_nis_limits": list(nis_limits),
        "synthetic_process_variances":
            list(process_variances),
        "cells": cells,
        "same_synthetic_noise_per_seed_across_conditions":
            True,
        "physical_reference_verified": False,
        "statistical_calibration_established": False,
        "physical_localization_accuracy_verified": False,
        "real_factor_weights_generated": False,
        "estimator_invoked": False,
        "real_factor_count": 0,
        "real_factor_admission": "DENIED",
        "m2dgr_gates": "11_CLOSED",
    }


def infer_real_robot_sensitivity(*args, **kwargs):
    raise ToySensitivityError(
        "Synthetic sensitivity cannot determine physical "
        "estimator performance or sensor trust"
    )
