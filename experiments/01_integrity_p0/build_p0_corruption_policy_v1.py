from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import json
import subprocess


ROOT = Path.home() / "toqeer" / "IMU_Reliability"

DEV_INPUTS = (
    ROOT
    / "data/provenance/"
      "p0_dev_policy_inputs_v1.json"
)

REGISTRY = (
    ROOT
    / "data/manifests/"
      "reliability_eval_registry_v1.json"
)

OUTPUT = (
    ROOT
    / "configs/integrity/"
      "p0_corruption_policy_v1_candidate.json"
)


EXPECTED_DEV_INPUT_SHA = (
    "6081ad317032c7dc5ea063a0296bf354f698773e5054eec51dc98a51a58ce489"
)

EXPECTED_REGISTRY_TAG_COMMIT = (
    "416cc9d8895646c38edc6b7be1dfdc042d0c2219"
)

EXPECTED_REGISTRY_CONTENT_SHA = (
    "a99f3031e2efd388b8dcbf26673c41ae142a3ef3ea1eb8c2a4b609b819a13d71"
)


SEVERITIES = (
    "low",
    "medium",
    "high",
)

RANGE_QUANTILES = {
    "low": "q0.999",
    "medium": "q0.995",
    "high": "q0.990",
}

FRAME_GAP_SAMPLES = {
    "low": 1,
    "medium": 4,
    "high": 8,
}

FRAME_REPEAT_SAMPLES = {
    "low": 2,
    "medium": 5,
    "high": 10,
}

CHANNEL_FREEZE_SAMPLES = {
    "low": 5,
    "medium": 10,
    "high": 20,
}

TIMING_EXTRA_DELAY_MS = {
    "low": 10.0,
    "medium": 40.0,
    "high": 90.0,
}


TASK_CHANNELS = (
    "acc_x",
    "acc_y",
    "acc_z",
    "gyr_x",
    "gyr_y",
    "gyr_z",
)


def canonical_digest(payload):
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")

    return sha256(raw).hexdigest()


def verify_hash(data):
    payload = deepcopy(data)

    stored = payload.pop(
        "content_sha256"
    )

    computed = canonical_digest(
        payload
    )

    if stored != computed:
        raise RuntimeError(
            "Content hash mismatch: "
            f"stored={stored}, "
            f"computed={computed}"
        )

    return stored


def git(*args):
    return subprocess.check_output(
        ["git", *args],
        cwd=ROOT,
        text=True,
    ).strip()


def derive_range_levels(
    dev_inputs,
):
    result = {}

    stats = dev_inputs[
        "dataset_statistics"
    ]

    for dataset in (
        "UNIVRFALL",
        "KFALL",
    ):
        result[
            dataset
        ] = {}

        for severity in SEVERITIES:
            qkey = RANGE_QUANTILES[
                severity
            ]

            channel_levels = {}

            for channel in TASK_CHANNELS:
                level = float(
                    stats[
                        dataset
                    ][
                        "sensor_absolute_statistics"
                    ][
                        channel
                    ][
                        "absolute_quantiles"
                    ][
                        qkey
                    ]
                )

                if not (
                    level > 0
                ):
                    raise RuntimeError(
                        "Nonpositive range clamp "
                        f"{dataset} "
                        f"{channel} "
                        f"{severity}: "
                        f"{level}"
                    )

                channel_levels[
                    channel
                ] = {
                    "absolute_clamp_level":
                        level,

                    "low":
                        -level,

                    "high":
                        level,

                    "source_quantile":
                        qkey,

                    "interpretation":
                        "synthetic_dev_quantile_clamp_not_physical_rail",
                }

            result[
                dataset
            ][severity] = (
                channel_levels
            )

    return result


def main():
    dev_inputs = json.loads(
        DEV_INPUTS.read_text(
            encoding="utf-8"
        )
    )

    dev_sha = verify_hash(
        dev_inputs
    )

    if dev_sha != EXPECTED_DEV_INPUT_SHA:
        raise RuntimeError(
            "Development policy input differs "
            "from reviewed audit"
        )


    if dev_inputs[
        "partition_used"
    ] != "development":
        raise RuntimeError(
            "Policy input did not use development partition"
        )


    if dev_inputs[
        "calibration_records_read_for_statistics"
    ] != 0:
        raise RuntimeError(
            "Calibration data entered policy statistics"
        )


    if dev_inputs[
        "final_test_records_read_for_statistics"
    ] != 0:
        raise RuntimeError(
            "Final-test data entered policy statistics"
        )


    registry = json.loads(
        REGISTRY.read_text(
            encoding="utf-8"
        )
    )

    registry_sha = verify_hash(
        registry
    )

    if (
        registry_sha
        != EXPECTED_REGISTRY_CONTENT_SHA
    ):
        raise RuntimeError(
            "Frozen registry content changed"
        )


    registry_tag_commit = git(
        "rev-parse",
        "reliability-eval-registry-v1^{}",
    )

    if (
        registry_tag_commit
        != EXPECTED_REGISTRY_TAG_COMMIT
    ):
        raise RuntimeError(
            "Registry tag moved: "
            f"{registry_tag_commit}"
        )


    if registry[
        "status"
    ] != (
        "frozen_before_p0_corruption_policy_definition"
    ):
        raise RuntimeError(
            "Registry is not frozen at the expected stage"
        )


    development_counts = (
        dev_inputs[
            "development_acquisition_trial_counts"
        ]
    )

    if development_counts != {
        "KFALL": 3829,
        "UNIVRFALL": 792,
    }:
        raise RuntimeError(
            "Development acquisition population changed"
        )


    for dataset in (
        "UNIVRFALL",
        "KFALL",
    ):
        median = float(
            dev_inputs[
                "dataset_statistics"
            ][dataset][
                "timestamp_delta_ms"
            ][
                "positive_quantiles"
            ][
                "q0.500"
            ]
        )

        if abs(
            median - 10.0
        ) > 1e-6:
            raise RuntimeError(
                "Unexpected development median "
                f"timestamp delta for "
                f"{dataset}: {median}"
            )


    range_levels = derive_range_levels(
        dev_inputs
    )


    payload = {
        "policy_id":
            "P0_CORRUPTION_POLICY_V1",

        "status":
            "candidate_for_freeze_before_calibration_and_final_test_generation",

        "source_evidence": {
            "development_policy_inputs":
                str(
                    DEV_INPUTS.relative_to(
                        ROOT
                    )
                ),

            "development_policy_inputs_content_sha256":
                dev_sha,

            "frozen_evaluation_registry":
                str(
                    REGISTRY.relative_to(
                        ROOT
                    )
                ),

            "frozen_evaluation_registry_content_sha256":
                registry_sha,

            "frozen_evaluation_registry_tag":
                "reliability-eval-registry-v1",

            "frozen_evaluation_registry_tag_commit":
                registry_tag_commit,

            "statistics_partition":
                "development",

            "calibration_statistics_used":
                False,

            "final_test_statistics_used":
                False,
        },

        "sampling_context": {
            "nominal_sampling_rate_hz":
                100,

            "nominal_sample_period_ms":
                10.0,

            "nominal_period_evidence":
                (
                    "Development positive timestamp median is "
                    "10 ms in both UniVRFall and KFall."
                ),

            "runtime_timing_threshold_frozen_here":
                False,
        },

        "severity_order": list(
            SEVERITIES
        ),

        "instance_generation": {
            "instances_materialized_as_full_corrupted_files":
                False,

            "manifest_specs_only":
                True,

            "regenerate_corruption_deterministically_at_evaluation":
                True,

            "instances_per_trial_family_severity":
                1,

            "master_seed_material":
                (
                    "P0_CORRUPTION_POLICY_V1|"
                    "reliability-eval-registry-v1|"
                    "416cc9d8895646c38edc6b7be1dfdc042d0c2219"
                ),

            "seed_derivation":
                (
                    "SHA256(master_seed_material || trial_id || "
                    "family || severity || replicate_index)"
                ),

            "candidate_selection":
                (
                    "Enumerate admissible candidates in canonical "
                    "order and select index from the first 64 bits "
                    "of a domain-separated SHA256 digest modulo the "
                    "candidate count."
                ),

            "no_op_instances_allowed":
                False,

            "failed_admissibility_handling":
                (
                    "Record NOT_ADMISSIBLE with reason; "
                    "do not replace with a different severity."
                ),

            "paired_clean_corrupt_required":
                True,

            "corrupt_after_partitioning":
                True,
        },

        "channel_policy": {
            "task_channels": list(
                TASK_CHANNELS
            ),

            "FRAME_REPEAT":
                "repeat the complete six-channel sensor row",

            "CHANNEL_FREEZE":
                (
                    "one task channel per instance; choose "
                    "deterministically among channels with at least "
                    "one mutating admissible placement"
                ),

            "RANGE_CLIP":
                (
                    "one task channel per instance; choose "
                    "deterministically among channels with at least "
                    "one admissible clamp-changing placement"
                ),
        },

        "families": {
            "FRAME_GAP": {
                "kind":
                    "FRAME_GAP",

                "severity_parameter":
                    "removed_sample_count",

                "severity_values":
                    FRAME_GAP_SAMPLES,

                "placement_constraints": {
                    "start_min":
                        1,

                    "must_leave_post_gap_sample":
                        True,

                    "metadata_behavior":
                        (
                            "remove sensor row and retain surrounding "
                            "timestamps/counters so discontinuity is "
                            "observable when provenance qualifies"
                        ),
                },

                "runtime_attribution_constraints": {
                    "KFALL":
                        "hard-qualified from raw FrameCounter discontinuity",

                    "UNIVRFALL":
                        (
                            "synthetic truth only; derived counter "
                            "does not qualify a hard runtime cause"
                        ),
                },
            },

            "FRAME_REPEAT": {
                "kind":
                    "FRAME_REPEAT",

                "severity_parameter":
                    "repeated_sample_count",

                "severity_values":
                    FRAME_REPEAT_SAMPLES,

                "placement_constraints": {
                    "start_min":
                        1,

                    "copy_source":
                        "immediately preceding sensor row",

                    "timestamps_and_counters_continue":
                        True,

                    "must_mutate_sensor_values":
                        True,
                },

                "runtime_attribution_constraints": {
                    "all_datasets":
                        (
                            "P0 truth does not qualify FRAME_REPEAT "
                            "as a hard runtime cause without independent "
                            "data-path evidence"
                        ),
                },
            },

            "CHANNEL_FREEZE": {
                "kind":
                    "CHANNEL_FREEZE",

                "severity_parameter":
                    "frozen_sample_count",

                "severity_values":
                    CHANNEL_FREEZE_SAMPLES,

                "placement_constraints": {
                    "start_min":
                        1,

                    "freeze_value_source":
                        "selected channel value immediately before start",

                    "must_mutate_selected_channel":
                        True,

                    "single_channel_per_instance":
                        True,
                },

                "runtime_attribution_constraints": {
                    "all_datasets":
                        "CHANNEL_FREEZE_SUSPECT only",
                },
            },

            "TIMING_PERTURBATION": {
                "kind":
                    "TIMING_PERTURBATION",

                "severity_parameter":
                    "extra_delay_ms",

                "severity_values":
                    TIMING_EXTRA_DELAY_MS,

                "nominal_boundary_delta_ms":
                    10.0,

                "affected_boundary_delta_if_nominal_ms": {
                    severity:
                        (
                            10.0
                            + TIMING_EXTRA_DELAY_MS[
                                severity
                            ]
                        )
                    for severity
                    in SEVERITIES
                },

                "placement_constraints": {
                    "single_internal_boundary":
                        True,

                    "step_shift_all_later_timestamps":
                        True,

                    "offset_must_be_nonzero":
                        True,
                },

                "runtime_attribution_constraints": {
                    "KFALL":
                        (
                            "candidate acquisition evidence, but hard "
                            "ACQ_TIMING_VIOLATION still requires a "
                            "separately frozen development-derived "
                            "runtime timing envelope"
                        ),

                    "UNIVRFALL":
                        (
                            "synthetic timing truth does not upgrade "
                            "timestamp provenance; runtime hard cause "
                            "remains unavailable unless provenance and "
                            "envelope requirements are independently met"
                        ),
                },
            },

            "RANGE_CLIP": {
                "kind":
                    "RANGE_CLIP",

                "severity_parameter":
                    "development_absolute_quantile_clamp",

                "severity_to_quantile":
                    RANGE_QUANTILES,

                "per_dataset_channel_levels":
                    range_levels,

                "placement_constraints": {
                    "single_channel_per_instance":
                        True,

                    "symmetric_low_high_clamp":
                        True,

                    "candidate_span_samples":
                        40,

                    "candidate_must_contain_value_exceeding_clamp":
                        True,

                    "must_mutate_selected_channel":
                        True,
                },

                "runtime_attribution_constraints": {
                    "all_datasets":
                        (
                            "synthetic clamp truth only; levels are "
                            "development empirical quantiles and are "
                            "not verified physical sensor rails"
                        ),
                },
            },
        },

        "benchmark_scope": {
            "datasets":
                [
                    "UNIVRFALL",
                    "KFALL",
                ],

            "onfield_acquisition_p0_enabled":
                False,

            "onfield_exclusion_reason":
                "raw trial mapping unverified",

            "historical_zero_window_trials":
                [
                    "106/27/1",
                    "106/27/5",
                ],

            "zero_window_trials_acquisition_only_allowed":
                True,

            "zero_window_trials_model_coupled_allowed":
                False,
        },

        "prospective_constraints": {
            "development_defines_policy":
                True,

            "calibration_may_modify_policy":
                False,

            "final_test_may_modify_policy":
                False,

            "calibration_corruption_instances_generated_at_policy_freeze":
                False,

            "final_test_corruption_instances_generated_at_policy_freeze":
                False,

            "synthetic_truth_may_upgrade_runtime_evidence":
                False,

            "physical_range_rail_claim":
                False,

            "classifier_bypass_enabled":
                False,
        },
    }


    payload[
        "content_sha256"
    ] = canonical_digest(
        payload
    )


    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


    print("=" * 100)
    print("P0 CORRUPTION POLICY V1 CANDIDATE")
    print("=" * 100)

    print(
        "dev_input_sha256 =",
        dev_sha,
    )

    print(
        "registry_sha256 =",
        registry_sha,
    )

    print(
        "registry_tag_commit =",
        registry_tag_commit,
    )

    print()
    print("severity values:")

    for severity in SEVERITIES:
        print(
            " ",
            severity,
            {
                "frame_gap_samples":
                    FRAME_GAP_SAMPLES[
                        severity
                    ],

                "frame_repeat_samples":
                    FRAME_REPEAT_SAMPLES[
                        severity
                    ],

                "channel_freeze_samples":
                    CHANNEL_FREEZE_SAMPLES[
                        severity
                    ],

                "timing_extra_delay_ms":
                    TIMING_EXTRA_DELAY_MS[
                        severity
                    ],

                "range_quantile":
                    RANGE_QUANTILES[
                        severity
                    ],
            },
        )


    print()
    print("range clamp levels:")

    for dataset in (
        "UNIVRFALL",
        "KFALL",
    ):
        print()
        print(" ", dataset)

        for severity in SEVERITIES:
            print(
                "   ",
                severity,
            )

            for channel in TASK_CHANNELS:
                value = (
                    range_levels[
                        dataset
                    ][severity][
                        channel
                    ][
                        "absolute_clamp_level"
                    ]
                )

                print(
                    "     ",
                    channel,
                    "=",
                    value,
                )


    print()
    print(
        "CONTENT_SHA256 =",
        payload[
            "content_sha256"
        ],
    )

    print(
        "OUTPUT =",
        OUTPUT,
    )

    print(
        "P0_CORRUPTION_POLICY_V1_CANDIDATE_PASS = True"
    )


if __name__ == "__main__":
    main()
