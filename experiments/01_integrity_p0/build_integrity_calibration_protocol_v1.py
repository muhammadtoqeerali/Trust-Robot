from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import json
import subprocess

import yaml


ROOT = Path.home() / "toqeer" / "IMU_Reliability"

CAL_RECEIPT = (
    ROOT
    / "data/manifests/"
      "p0_calibration_spec_receipt_v1.json"
)

POLICY = (
    ROOT
    / "configs/integrity/"
      "p0_corruption_policy_v1.json"
)

DEV_INPUTS = (
    ROOT
    / "data/provenance/"
      "p0_dev_policy_inputs_v1.json"
)

EVIDENCE_CONTRACT = (
    ROOT
    / "data/provenance/"
      "integrity_evidence_contract_v1.yaml"
)

TAXONOMY = (
    ROOT
    / "docs/taxonomy.md"
)

PROVENANCE = (
    ROOT
    / "docs/provenance.md"
)

OUTPUT = (
    ROOT
    / "configs/integrity/"
      "integrity_calibration_protocol_v1_candidate.json"
)


EXPECTED_HEAD = (
    "2bbd0c771601fcc9ced578e389deb42df46ffc33"
)

EXPECTED_CAL_TAG = EXPECTED_HEAD

EXPECTED_CAL_RECEIPT_SHA = (
    "104d14aaa013ce0782c76d44255cb2b0a55ad791daea78a11aa8da131c445b6b"
)

EXPECTED_POLICY_SHA = (
    "cb33c32951930453db550dfd02deab67a9eb51e851edf1a186e7faa4a5432220"
)

EXPECTED_DEV_INPUT_SHA = (
    "6081ad317032c7dc5ea063a0296bf354f698773e5054eec51dc98a51a58ce489"
)


def canonical_digest(payload):
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")

    return sha256(raw).hexdigest()


def verify_content_hash(data):
    payload = deepcopy(
        data
    )

    stored = payload.pop(
        "content_sha256"
    )

    computed = canonical_digest(
        payload
    )

    if stored != computed:
        raise RuntimeError(
            "Internal content hash mismatch: "
            f"{stored} != {computed}"
        )

    return stored


def file_sha256(path):
    return sha256(
        Path(path).read_bytes()
    ).hexdigest()


def git(*args):
    return subprocess.check_output(
        ["git", *args],
        cwd=ROOT,
        text=True,
    ).strip()


def main():
    head = git(
        "rev-parse",
        "HEAD",
    )

    if head != EXPECTED_HEAD:
        raise RuntimeError(
            "Repository HEAD changed before protocol definition: "
            f"{head}"
        )


    cal_tag = git(
        "rev-parse",
        "p0-calibration-spec-v1^{}",
    )

    if cal_tag != EXPECTED_CAL_TAG:
        raise RuntimeError(
            "Calibration specification tag moved"
        )


    cal_receipt = json.loads(
        CAL_RECEIPT.read_text(
            encoding="utf-8"
        )
    )

    cal_receipt_sha = (
        verify_content_hash(
            cal_receipt
        )
    )

    if (
        cal_receipt_sha
        != EXPECTED_CAL_RECEIPT_SHA
    ):
        raise RuntimeError(
            "Frozen calibration receipt changed"
        )


    if cal_receipt[
        "freeze_contract"
    ][
        "integrity_detector_thresholds_selected_at_freeze"
    ] is not False:
        raise RuntimeError(
            "Detector thresholds were already selected"
        )

    if cal_receipt[
        "freeze_contract"
    ][
        "persistence_selected_at_freeze"
    ] is not False:
        raise RuntimeError(
            "Persistence was already selected"
        )

    if cal_receipt[
        "freeze_contract"
    ][
        "final_test_corruption_instances_generated_at_freeze"
    ] is not False:
        raise RuntimeError(
            "Final-test corruptions already exist"
        )


    policy = json.loads(
        POLICY.read_text(
            encoding="utf-8"
        )
    )

    policy_sha = verify_content_hash(
        policy
    )

    if policy_sha != EXPECTED_POLICY_SHA:
        raise RuntimeError(
            "Frozen P0 corruption policy changed"
        )


    dev_inputs = json.loads(
        DEV_INPUTS.read_text(
            encoding="utf-8"
        )
    )

    dev_input_sha = verify_content_hash(
        dev_inputs
    )

    if (
        dev_input_sha
        != EXPECTED_DEV_INPUT_SHA
    ):
        raise RuntimeError(
            "Development policy-input artifact changed"
        )


    evidence = yaml.safe_load(
        EVIDENCE_CONTRACT.read_text(
            encoding="utf-8"
        )
    )


    if evidence[
        "status"
    ] != "frozen_before_detector_threshold_calibration":
        raise RuntimeError(
            "Unexpected evidence-contract status"
        )


    hard = evidence[
        "hard_causes"
    ]

    if hard[
        "FRAME_GAP"
    ][
        "enabled_where_provenance_qualified"
    ] is not True:
        raise RuntimeError(
            "FRAME_GAP qualification contract changed"
        )


    for cause in (
        "FIFO_OVERRUN",
        "FRAME_REPEAT",
        "BUFFER_STALL",
    ):
        if hard[
            cause
        ][
            "enabled"
        ] is not False:
            raise RuntimeError(
                f"{cause} unexpectedly enabled"
            )


    if hard[
        "RANGE_CLIP"
    ][
        "enabled_primary"
    ] is not False:
        raise RuntimeError(
            "Primary RANGE_CLIP unexpectedly enabled"
        )


    if evidence[
        "suspects"
    ][
        "CHANNEL_FREEZE_SUSPECT"
    ][
        "external_hard_cause"
    ] is not False:
        raise RuntimeError(
            "CHANNEL_FREEZE_SUSPECT became a hard cause"
        )


    repeat_path = (
        ROOT
        / "src/imu_reliability/integrity/"
          "repeat_stall.py"
    )

    range_path = (
        ROOT
        / "src/imu_reliability/integrity/"
          "range_clip.py"
    )

    if repeat_path.exists():
        raise RuntimeError(
            "repeat_stall.py appeared after reviewed API inspection"
        )

    if range_path.exists():
        raise RuntimeError(
            "range_clip.py appeared after reviewed API inspection"
        )


    timing_stats = (
        dev_inputs[
            "dataset_statistics"
        ]
    )


    kfall_timing = (
        timing_stats[
            "KFALL"
        ][
            "timestamp_delta_ms"
        ]
    )

    univr_timing = (
        timing_stats[
            "UNIVRFALL"
        ][
            "timestamp_delta_ms"
        ]
    )


    if abs(
        float(
            kfall_timing[
                "positive_quantiles"
            ][
                "q0.500"
            ]
        )
        - 10.0
    ) > 1e-6:
        raise RuntimeError(
            "Unexpected KFall development timing median"
        )


    if (
        float(
            univr_timing[
                "positive_quantiles"
            ][
                "q0.500"
            ]
        )
        != 10.0
    ):
        raise RuntimeError(
            "Unexpected UniVR development timing median"
        )


    payload = {
        "protocol_id":
            "INTEGRITY_CALIBRATION_PROTOCOL_V1",

        "status":
            "candidate_frozen_search_space_before_calibration_detector_outcome_evaluation",

        "scope": {
            "partition_used_for_operating_point_selection":
                "calibration",

            "development_used_only_for_prior_characterization_and_grid_definition":
                True,

            "final_test_data_allowed":
                False,

            "final_test_corruption_generation_allowed":
                False,

            "task_model_outcomes_allowed_during_integrity_calibration":
                False,

            "ood_outcomes_allowed_during_integrity_calibration":
                False,

            "corruption_policy_modification_allowed":
                False,

            "calibration_specification_modification_allowed":
                False,
        },

        "source_anchors": {
            "repository_head":
                head,

            "p0_calibration_spec_tag":
                "p0-calibration-spec-v1",

            "p0_calibration_spec_tag_commit":
                cal_tag,

            "calibration_receipt_content_sha256":
                cal_receipt_sha,

            "p0_policy_content_sha256":
                policy_sha,

            "development_policy_inputs_content_sha256":
                dev_input_sha,

            "integrity_evidence_contract_file_sha256":
                file_sha256(
                    EVIDENCE_CONTRACT
                ),

            "taxonomy_file_sha256":
                file_sha256(
                    TAXONOMY
                ),

            "provenance_file_sha256":
                file_sha256(
                    PROVENANCE
                ),
        },

        "runtime_evidence_boundary": {
            "FRAME_GAP": {
                "proposed_runtime_role":
                    "qualified_hard_cause_where_direct_counter_provenance_exists",

                "historical_p0_dataset_behavior": {
                    "KFALL":
                        "HARD_QUALIFIED_FROM_RAW_FRAMECOUNTER",

                    "UNIVRFALL":
                        "NO_HARD_FRAME_GAP_FROM_UNVERIFIED_DERIVED_COUNTER",
                },

                "tunable_parameters":
                    [],
            },

            "FIFO_OVERRUN": {
                "proposed_runtime_role":
                    "DISABLED",

                "reason":
                    "no_fifo_or_overrun_status_evidence",
            },

            "FRAME_REPEAT": {
                "proposed_runtime_role":
                    "NO_HARD_CAUSE_IN_V1_HISTORICAL_P0",

                "reason":
                    "sensor_value_repetition_is_not_independent_data_path_evidence",

                "main_operating_point_tuned":
                    False,

                "optional_later_baseline":
                    "exact_full_vector_repeat_observation_only",
            },

            "BUFFER_STALL": {
                "proposed_runtime_role":
                    "DISABLED",

                "reason":
                    "no_independent_stall_evidence",
            },

            "ACQ_TIMING_VIOLATION": {
                "proposed_runtime_role":
                    "OBSERVATION_ONLY_IN_HISTORICAL_P0_V1",

                "hard_promotion_during_this_calibration":
                    False,

                "reason":
                    (
                        "timestamp fields are characterized but acquisition-"
                        "boundary generation provenance is not upgraded by P0; "
                        "calibration selects diagnostic envelopes only"
                    ),

                "future_hard_promotion_requires":
                    (
                        "separate documented provenance revision or P1-P3 "
                        "acquisition-boundary evidence plus frozen envelope"
                    ),
            },

            "RANGE_CLIP": {
                "proposed_runtime_role":
                    "NO_HARD_CAUSE_IN_V1_HISTORICAL_P0",

                "reason":
                    "configured physical measurement rail is not verified",

                "synthetic_p0_clamps_are_physical_rails":
                    False,

                "main_operating_point_tuned":
                    False,

                "optional_later_baseline":
                    "p0_boundary_hit_diagnostic_only",
            },

            "CHANNEL_FREEZE_SUSPECT": {
                "proposed_runtime_role":
                    "SUSPECT_ONLY",

                "enters_hard_cause_set":
                    False,

                "may_change_three_state_trust_state":
                    False,

                "parameter_search_enabled":
                    True,
            },
        },

        "canonical_timing_unit":
            "ms",

        "timing_preprocessing_contract": {
            "KFALL": {
                "raw_timestamp_unit":
                    "s",

                "multiply_raw_timestamp_by":
                    1000.0,
            },

            "UNIVRFALL": {
                "raw_timestamp_unit":
                    "ms",

                "multiply_raw_timestamp_by":
                    1.0,
            },

            "conversion_occurs_before_evaluate_timing_envelope":
                True,
        },

        "search_spaces": {
            "CHANNEL_FREEZE_SUSPECT": {
                "absolute_tolerance":
                    [
                        0.0,
                    ],

                "absolute_tolerance_interpretation":
                    "exact_digital_code_equality_only",

                "consecutive_deltas":
                    [
                        2,
                        3,
                        4,
                        5,
                        8,
                        10,
                        15,
                        20,
                    ],

                "same_operating_point_across_KFALL_and_UNIVRFALL":
                    True,

                "grid_rationale":
                    (
                        "100 Hz stream; grid spans 20-200 ms and brackets "
                        "the frozen P0 freeze durations 5/10/20 samples "
                        "without introducing unit-specific value tolerances"
                    ),
            },

            "TIMING_OBSERVATION_ENVELOPE": {
                "KFALL": [
                    {
                        "minimum_delta_ms": 9.9,
                        "maximum_delta_ms": 10.1,
                    },
                    {
                        "minimum_delta_ms": 9.5,
                        "maximum_delta_ms": 10.5,
                    },
                    {
                        "minimum_delta_ms": 9.0,
                        "maximum_delta_ms": 11.0,
                    },
                    {
                        "minimum_delta_ms": 8.0,
                        "maximum_delta_ms": 12.0,
                    },
                    {
                        "minimum_delta_ms": 5.0,
                        "maximum_delta_ms": 15.0,
                    },
                ],

                "UNIVRFALL": [
                    {
                        "minimum_delta_ms": -0.5,
                        "maximum_delta_ms": 20.5,
                    },
                    {
                        "minimum_delta_ms": -0.5,
                        "maximum_delta_ms": 30.5,
                    },
                    {
                        "minimum_delta_ms": -0.5,
                        "maximum_delta_ms": 40.5,
                    },
                    {
                        "minimum_delta_ms": -0.5,
                        "maximum_delta_ms": 50.5,
                    },
                    {
                        "minimum_delta_ms": -0.5,
                        "maximum_delta_ms": 60.5,
                    },
                    {
                        "minimum_delta_ms": -0.5,
                        "maximum_delta_ms": 100.5,
                    },
                    {
                        "minimum_delta_ms": -0.5,
                        "maximum_delta_ms": 110.5,
                    },
                    {
                        "minimum_delta_ms": -0.5,
                        "maximum_delta_ms": 500.5,
                    },
                ],

                "dataset_specific_operating_points":
                    True,

                "envelope_frozen_flag_during_candidate_evaluation":
                    False,

                "evidence_status_during_candidate_evaluation":
                    "OBSERVATION_ONLY",
            },
        },

        "clean_constraints": {
            "hard_cause_set": {
                "require_zero_clean_hard_alerts":
                    True,

                "note":
                    (
                        "In historical P0 V1, the only proposed hard "
                        "dataset cause is provenance-qualified KFall "
                        "FRAME_GAP."
                    ),
            },

            "CHANNEL_FREEZE_SUSPECT": {
                "maximum_onsets_per_hour_per_dataset":
                    1.0,

                "maximum_time_in_suspect_fraction_per_dataset":
                    0.005,

                "maximum_fraction_of_clean_trials_with_any_suspect_per_dataset":
                    0.05,

                "constraints_apply_separately_to_each_dataset":
                    True,
            },

            "TIMING_OBSERVATION_ENVELOPE": {
                "maximum_outside_intervals_per_hour_per_dataset":
                    3.0,

                "maximum_fraction_of_clean_trials_with_any_outside_interval_per_dataset":
                    0.05,

                "note":
                    (
                        "This is an observation-quality budget, not a "
                        "hard-alert budget. Timing remains outside C_t."
                    ),
            },
        },

        "calibration_metrics": {
            "clean_stream": [
                "hours_observed",
                "hard_alert_count",
                "hard_alerts_per_hour",
                "suspect_onset_count",
                "suspect_onsets_per_hour",
                "time_in_suspect_fraction",
                "fraction_trials_with_any_suspect",
                "timing_outside_interval_count",
                "timing_outside_intervals_per_hour",
                "fraction_trials_with_any_timing_outside",
            ],

            "paired_corruption": [
                "event_detection_recall",
                "confirmation_latency_samples",
                "confirmation_latency_ms",
                "severity_stratified_recall",
                "dataset_stratified_recall",
            ],

            "attribution": [
                "qualified_hard_cause_precision",
                "qualified_hard_cause_coverage",
                "unsupported_cause_emission_count",
                "synthetic_truth_vs_runtime_evidence_confusion",
            ],
        },

        "selection_rules": {
            "CHANNEL_FREEZE_SUSPECT": {
                "feasibility":
                    "all_clean_constraints_must_hold_on_each_dataset",

                "primary_objective":
                    (
                        "maximize equal-dataset-weighted macro event recall "
                        "over low/medium/high CHANNEL_FREEZE P0 episodes"
                    ),

                "tie_break_1":
                    "minimize median confirmation latency_ms",

                "tie_break_2":
                    "choose larger consecutive_deltas",

                "tie_break_3":
                    "lexicographically_smallest_serialized_candidate",
            },

            "TIMING_OBSERVATION_ENVELOPE": {
                "selection_is_separate_by_dataset":
                    True,

                "feasibility":
                    "all_dataset_clean_timing_constraints_must_hold",

                "primary_objective":
                    (
                        "maximize macro event recall over low/medium/high "
                        "TIMING_PERTURBATION P0 episodes"
                    ),

                "tie_break_1":
                    "choose_wider_envelope",

                "tie_break_2":
                    "lexicographically_smallest_serialized_candidate",

                "hard_cause_promotion_after_selection":
                    False,
            },

            "FRAME_GAP": {
                "search_required":
                    False,

                "rule":
                    "direct_counter_delta_greater_than_one_with_qualified_provenance",
            },
        },

        "failure_policy": {
            "if_no_CHANNEL_FREEZE_candidate_is_feasible":
                (
                    "do_not_relax_clean_constraints; keep suspect disabled "
                    "in main operating point and report best diagnostic "
                    "candidate separately"
                ),

            "if_no_TIMING_candidate_is_feasible":
                (
                    "do_not_relax_clean constraints; timing remains raw "
                    "observation-only without selected envelope"
                ),

            "calibration_may_change_search_grid":
                False,

            "calibration_may_change_clean_constraints":
                False,

            "calibration_may_enable_unsupported_hard_cause":
                False,

            "calibration_may_change_P0_policy":
                False,
        },

        "evaluation_semantics": {
            "one_injected_episode_per_admissible_pair":
                True,

            "event_detected_only_if_evidence_overlaps_or_confirms_within_injected_episode":
                True,

            "clean_and_corrupt_streams_paired":
                True,

            "NOT_ADMISSIBLE_instances_excluded_from_detection_denominator":
                True,

            "NOT_ADMISSIBLE_counts_reported_separately":
                True,

            "dataset_and_severity_stratification_required":
                True,

            "P0_truth_never_upgrades_runtime_evidence_status":
                True,
        },

        "operating_point_freeze_sequence": [
            "freeze_this_protocol",
            "implement_or_verify_calibration_evaluator",
            "evaluate_clean_and_frozen_calibration_pairs",
            "select_operating_points_by_predeclared_rules",
            "write_integrity_operating_point_v1",
            "freeze_selected_operating_point",
            "only_then_generate_final_test_P0_specifications",
        ],

        "outcomes_read_while_defining_this_protocol": {
            "calibration_detector_outputs":
                False,

            "calibration_task_model_outputs":
                False,

            "final_test_outputs":
                False,
        },
    }


    payload[
        "content_sha256"
    ] = canonical_digest(
        payload
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


    print("=" * 104)
    print(
        "INTEGRITY CALIBRATION PROTOCOL V1 CANDIDATE"
    )
    print("=" * 104)

    print(
        "repository_head =",
        head,
    )

    print(
        "calibration_receipt_sha256 =",
        cal_receipt_sha,
    )

    print(
        "evidence_contract_sha256 =",
        payload[
            "source_anchors"
        ][
            "integrity_evidence_contract_file_sha256"
        ],
    )

    print()
    print(
        "runtime hard FRAME_GAP KFall = True"
    )

    print(
        "runtime hard FRAME_REPEAT = False"
    )

    print(
        "runtime hard BUFFER_STALL = False"
    )

    print(
        "runtime hard RANGE_CLIP = False"
    )

    print(
        "historical P0 timing hard promotion = False"
    )

    print(
        "CHANNEL_FREEZE enters C_t = False"
    )

    print()
    print(
        "freeze persistence grid =",
        payload[
            "search_spaces"
        ][
            "CHANNEL_FREEZE_SUSPECT"
        ][
            "consecutive_deltas"
        ],
    )

    print(
        "KFall timing candidates =",
        len(
            payload[
                "search_spaces"
            ][
                "TIMING_OBSERVATION_ENVELOPE"
            ][
                "KFALL"
            ]
        ),
    )

    print(
        "UniVR timing candidates =",
        len(
            payload[
                "search_spaces"
            ][
                "TIMING_OBSERVATION_ENVELOPE"
            ][
                "UNIVRFALL"
            ]
        ),
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
        "INTEGRITY_CALIBRATION_PROTOCOL_V1_CANDIDATE_PASS = True"
    )


if __name__ == "__main__":
    main()
