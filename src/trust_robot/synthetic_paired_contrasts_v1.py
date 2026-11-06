"""A31-11: structural and paired-seed audit of toy ensembles.

Identical synthetic delivery masks are replicated conditions,
not independent failure experiments.

All differences and win counts are descriptive only.
"""

import math

from trust_robot.synthetic_trajectory_ensemble_v1 import (
    SCHEMA as ENSEMBLE_SCHEMA,
    SCENARIOS,
    VARIANTS,
    STEPS,
)

SCHEMA = "TRUST_ROBOT_R135_A31_11_PAIRED_CONTRASTS_V1"


class PairedContrastError(ValueError):
    pass


def require(ok, message):
    if not ok:
        raise PairedContrastError(message)


def finite(value):
    return (
        type(value) in (int, float)
        and math.isfinite(value)
    )


def audit_paired_ensemble(ensemble):
    require(
        type(ensemble) is dict
        and ensemble.get("schema") == ENSEMBLE_SCHEMA
        and ensemble.get("status")
        == "FIXED_MULTI_SEED_SYNTHETIC_EXPERIMENT_ONLY",
        "Unexpected ensemble source",
    )

    require(
        ensemble.get("real_factor_count") == 0
        and type(ensemble.get("real_factor_count")) is int
        and ensemble.get("real_factor_admission") == "DENIED"
        and ensemble.get("m2dgr_gates") == "11_CLOSED"
        and ensemble.get("estimator_invoked") is False
        and ensemble.get("physical_reference_verified") is False
        and ensemble.get("physical_clock_verified") is False
        and ensemble.get("statistical_calibration_established")
        is False
        and ensemble.get("time_axis_consistency_required") is True,
        "Ensemble scientific boundary invalid",
    )

    seeds = ensemble.get("seeds")

    require(
        type(seeds) is list
        and 2 <= len(seeds) <= 16
        and all(
            type(s) is int and 0 <= s <= 65535
            for s in seeds
        )
        and seeds == sorted(set(seeds)),
        "Invalid fixed seed cohort",
    )

    scenarios = ensemble.get("scenarios")

    require(
        type(scenarios) is dict
        and set(scenarios) == SCENARIOS
        and ensemble.get("scenario_count") == len(SCENARIOS)
        and ensemble.get("steps_per_seed") == STEPS,
        "Unexpected scenario inventory",
    )

    verified = {}
    grouped = {}

    for name in sorted(scenarios):
        scenario = scenarios[name]

        require(
            type(scenario) is dict,
            "Invalid scenario object",
        )

        mask = scenario.get("synthetic_delivery_mask")
        trials = scenario.get("trials")
        summaries = scenario.get("summary")

        require(
            type(mask) is list
            and len(mask) == STEPS
            and all(type(x) is bool for x in mask)
            and type(trials) is list
            and len(trials) == len(seeds)
            and scenario.get("seed_count") == len(seeds)
            and type(summaries) is dict
            and set(summaries) == set(VARIANTS),
            "Scenario format or mask invalid",
        )

        for index, trial in enumerate(trials):
            require(
                type(trial) is dict
                and trial.get("synthetic_seed") == seeds[index]
                and trial.get("time_axis_consistent") is True
                and trial.get("real_factor_count") == 0
                and type(trial.get("real_factor_count")) is int
                and type(trial.get("policies")) is dict
                and set(trial["policies"]) == set(VARIANTS),
                "Unmatched or invalid paired trial",
            )

            for variant in VARIANTS:
                record = trial["policies"][variant]

                require(
                    type(record) is dict
                    and set(record) == {
                        "accepted_synthetic_updates",
                        "toy_position_rmse",
                        "mean_toy_nees_15d",
                    },
                    "Unexpected toy policy metric fields",
                )

                count = record["accepted_synthetic_updates"]

                require(
                    type(count) is int
                    and 0 <= count <= STEPS
                    and finite(record["toy_position_rmse"])
                    and record["toy_position_rmse"] >= 0
                    and finite(record["mean_toy_nees_15d"])
                    and record["mean_toy_nees_15d"] >= 0,
                    "Malformed descriptive toy metrics",
                )

            require(
                trial["policies"][
                    "counterfactual_all_candidates"
                ]["accepted_synthetic_updates"] == STEPS,
                "Counterfactual toy accounting differs",
            )

            require(
                trial["policies"][
                    "scheduled_delivery_only"
                ]["accepted_synthetic_updates"] == sum(mask),
                "Scheduled synthetic delivery accounting differs",
            )

            require(
                trial["policies"][
                    "combined_toy_screening"
                ]["accepted_synthetic_updates"] <= sum(mask),
                "Combined screening accounting differs",
            )

        for variant in VARIANTS:
            aggregate = summaries[variant]

            require(
                type(aggregate) is dict
                and set(aggregate) == {
                    "mean_toy_position_rmse",
                    "mean_toy_nees_15d",
                    "mean_synthetic_updates",
                },
                "Invalid ensemble aggregate",
            )

            for field, source_field in (
                ("mean_toy_position_rmse", "toy_position_rmse"),
                ("mean_toy_nees_15d", "mean_toy_nees_15d"),
                ("mean_synthetic_updates",
                 "accepted_synthetic_updates"),
            ):
                recomputed = sum(
                    trial["policies"][variant][source_field]
                    for trial in trials
                ) / len(trials)

                require(
                    finite(aggregate[field])
                    and math.isclose(
                        aggregate[field],
                        recomputed,
                        rel_tol=1e-12,
                        abs_tol=1e-12,
                    ),
                    "Aggregate mismatches its paired trials",
                )

        contrasts = {}

        for comparator in (
            "scheduled_delivery_only",
            "counterfactual_all_candidates",
        ):
            rmse_differences = []
            nees_differences = []
            update_differences = []

            for trial in trials:
                combined = trial["policies"][
                    "combined_toy_screening"
                ]
                other = trial["policies"][comparator]

                rmse_differences.append(
                    combined["toy_position_rmse"]
                    - other["toy_position_rmse"]
                )
                nees_differences.append(
                    combined["mean_toy_nees_15d"]
                    - other["mean_toy_nees_15d"]
                )
                update_differences.append(
                    combined["accepted_synthetic_updates"]
                    - other["accepted_synthetic_updates"]
                )

            contrasts[comparator] = {
                "mean_paired_rmse_difference":
                    sum(rmse_differences) / len(seeds),
                "mean_paired_nees_difference":
                    sum(nees_differences) / len(seeds),
                "mean_update_count_difference":
                    sum(update_differences) / len(seeds),
                "combined_lower_rmse_seed_count": sum(
                    x < 0 for x in rmse_differences
                ),
                "combined_equal_rmse_seed_count": sum(
                    x == 0 for x in rmse_differences
                ),
                "paired_seed_count": len(seeds),
                "inferential_significance_claim": False,
            }

        verified[name] = {
            "synthetic_delivery_mask": list(mask),
            "seed_count": len(seeds),
            "paired_contrasts": contrasts,
        }

        key = tuple(mask)
        grouped.setdefault(key, []).append(name)

    condition_groups = []

    for mask, names in sorted(grouped.items()):
        names = sorted(names)

        # Same seed, same mask, same declared synthetic noise:
        # repeated labels must not be counted as independent data.
        anchor = scenarios[names[0]]["trials"]

        for name in names[1:]:
            require(
                scenarios[name]["trials"] == anchor,
                "Identical synthetic mask unexpectedly "
                "produced different paired trial outcomes",
            )

        condition_groups.append({
            "synthetic_delivery_mask": list(mask),
            "scenario_names": names,
            "scenario_label_count": len(names),
            "unique_experimental_condition_count": 1,
        })

    return {
        "schema": SCHEMA,
        "status": "DESCRIPTIVE_PAIRED_TOY_AUDIT_ONLY",
        "seed_count": len(seeds),
        "scenario_label_count": len(scenarios),
        "unique_mask_condition_count":
            len(condition_groups),
        "synthetic_mask_condition_groups":
            condition_groups,
        "paired_scenario_contrasts": verified,
        "independent_physical_trials": 0,
        "statistical_significance_established": False,
        "statistical_calibration_established": False,
        "physical_localization_accuracy_verified": False,
        "real_factor_count": 0,
        "real_factor_admission": "DENIED",
        "m2dgr_gates": "11_CLOSED",
    }


def claim_physical_replication(*args, **kwargs):
    raise PairedContrastError(
        "Synthetic masks are not independent physical trials"
    )
