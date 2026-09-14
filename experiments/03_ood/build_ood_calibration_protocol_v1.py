from __future__ import annotations

import json
import math
import subprocess
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from typing import Iterable, Mapping, Sequence


ROOT = Path(
    __file__
).resolve().parents[2]

OUT = (
    ROOT
    / "configs/ood/"
      "ood_calibration_protocol_v1.json"
)

REGISTRY = (
    ROOT
    / "data/manifests/"
      "reliability_eval_registry_v1.json"
)

MODEL_SOURCE = (
    ROOT
    / "src/imu_reliability/baseline/"
      "date2025_cnn400.py"
)

PROJECT_CONFIG = (
    ROOT
    / "configs/project.yaml"
)

CHECKPOINT = Path(
    "/mnt/hdd16T/protechto/checkpoints/CNN/400ms/"
    "2025-02-25_12_24_47/best-checkpoint.ckpt"
)


EXPECTED_PRE_PROTOCOL_HEAD = (
    "b1aaa28a5cd2222bd3acc7d5d86289ba9fd71c74"
)

EXPECTED_INTEGRITY_RESULT_COMMIT = (
    "b1aaa28a5cd2222bd3acc7d5d86289ba9fd71c74"
)

EXPECTED_BASELINE_COMMIT = (
    "d6fe744b292139d18fd4dee37c96066bcf2d38c6"
)

EXPECTED_REGISTRY_COMMIT = (
    "416cc9d8895646c38edc6b7be1dfdc042d0c2219"
)

EXPECTED_LINEAGE_COMMIT = (
    "4b32a68cec9f88e73b5f09e22ff3335e1d590962"
)

EXPECTED_CHECKPOINT_SHA256 = (
    "ee7c0079bfb8555bff45c3077cc24eaa"
    "4373c57729045d92a831a1d7a3ea9bb1"
)

EXPECTED_MODEL_SOURCE_RAW_SHA256 = (
    "def71b3cebc0649c0d909e4ffd5dc04f"
    "177fcb795ff6ebfd13f90e214c67581d"
)

EXPECTED_CALIBRATION_TRIAL_ROWS = {
    "KFALL":
        314,
    "UNIVRFALL":
        132,
    "ONFIELD":
        1,
}

EXPECTED_CALIBRATION_WINDOWS = {
    "KFALL":
        9585,
    "UNIVRFALL":
        5951,
    "ONFIELD":
        74332,
}

EXPECTED_CALIBRATION_STRATA = (
    {
        "dataset":
            "KFALL",
        "class":
            "Activity",
        "n":
            9342,
    },
    {
        "dataset":
            "KFALL",
        "class":
            "Falling",
        "n":
            243,
    },
    {
        "dataset":
            "UNIVRFALL",
        "class":
            "Activity",
        "n":
            5870,
    },
    {
        "dataset":
            "UNIVRFALL",
        "class":
            "Falling",
        "n":
            81,
    },
    {
        "dataset":
            "ONFIELD",
        "class":
            "Activity",
        "n":
            74332,
    },
)

EXPECTED_FINAL_TEST_TRIAL_ROWS = {
    "KFALL":
        932,
    "UNIVRFALL":
        176,
    "ONFIELD":
        8,
}

EXPECTED_FINAL_TEST_WINDOWS = {
    "KFALL":
        27068,
    "UNIVRFALL":
        7532,
    "ONFIELD":
        331907,
}

CANDIDATE_METHODS = (
    "maximum_softmax_probability",
    "top_two_logit_margin",
    "energy",
    "prototype_cosine",
    "diagonal_standardized_feature_distance",
    "tcuq",
)

SELECTED_METHOD = (
    "top_two_logit_margin"
)

CLEAN_ID_ACCEPTANCE_TARGET = (
    0.99
)


def canonical_digest(
    payload,
):
    normalized = json.loads(
        json.dumps(
            payload,
            separators=(",", ":"),
            allow_nan=False,
        )
    )

    return sha256(
        json.dumps(
            normalized,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def file_sha256(
    path: Path,
) -> str:
    return sha256(
        path.read_bytes()
    ).hexdigest()


def git(
    *args: str,
) -> str:
    return subprocess.check_output(
        [
            "git",
            *args,
        ],
        cwd=ROOT,
        text=True,
    ).strip()


def stratum_rank(
    n: int,
    rejection_fraction: float = 0.01,
) -> int:
    if n <= 0:
        raise ValueError(
            "Stratum must be nonempty"
        )

    if not (
        0.0
        <= rejection_fraction
        < 1.0
    ):
        raise ValueError(
            "Invalid rejection fraction"
        )

    return int(
        math.floor(
            rejection_fraction
            * n
        )
    )


def stratum_boundary(
    margins: Sequence[float],
    rejection_fraction: float = 0.01,
) -> float:
    if not margins:
        raise ValueError(
            "Margins must be nonempty"
        )

    ordered = sorted(
        float(
            value
        )
        for value in margins
    )

    rank = stratum_rank(
        len(
            ordered
        ),
        rejection_fraction,
    )

    return float(
        ordered[
            rank
        ]
    )


def finite_sample_global_threshold(
    strata: Mapping[
        str,
        Sequence[float],
    ],
    rejection_fraction: float = 0.01,
) -> float:
    if not strata:
        raise ValueError(
            "At least one stratum is required"
        )

    boundaries = [
        stratum_boundary(
            values,
            rejection_fraction,
        )
        for values
        in strata.values()
        if len(
            values
        ) > 0
    ]

    if not boundaries:
        raise ValueError(
            "At least one nonempty stratum is required"
        )

    return float(
        min(
            boundaries
        )
    )


def empirical_acceptance(
    margins: Iterable[float],
    threshold: float,
) -> float:
    values = [
        float(
            value
        )
        for value in margins
    ]

    if not values:
        raise ValueError(
            "Margins must be nonempty"
        )

    accepted = sum(
        value
        >= threshold
        for value in values
    )

    return (
        accepted
        / len(
            values
        )
    )


def verify_score_blind_anchors():
    if git(
        "rev-parse",
        "HEAD",
    ) != EXPECTED_PRE_PROTOCOL_HEAD:
        raise RuntimeError(
            "HEAD moved before OOD protocol freeze"
        )

    expected_refs = {
        "integrity-final-test-result-v1^{commit}":
            EXPECTED_INTEGRITY_RESULT_COMMIT,

        "baseline-date2025-cnn400-v1^{commit}":
            EXPECTED_BASELINE_COMMIT,

        "reliability-eval-registry-v1^{commit}":
            EXPECTED_REGISTRY_COMMIT,

        "reliability-lineage-v2^{commit}":
            EXPECTED_LINEAGE_COMMIT,
    }

    for ref, expected in expected_refs.items():
        observed = git(
            "rev-parse",
            ref,
        )

        if observed != expected:
            raise RuntimeError(
                f"Frozen ref moved: "
                f"{ref}: {observed}"
            )

    if not CHECKPOINT.is_file():
        raise RuntimeError(
            "Protected checkpoint absent"
        )

    checkpoint_sha = file_sha256(
        CHECKPOINT
    )

    if (
        checkpoint_sha
        != EXPECTED_CHECKPOINT_SHA256
    ):
        raise RuntimeError(
            "Protected checkpoint SHA changed"
        )

    model_sha = file_sha256(
        MODEL_SOURCE
    )

    if (
        model_sha
        != EXPECTED_MODEL_SOURCE_RAW_SHA256
    ):
        raise RuntimeError(
            "Protected model source changed"
        )

    baseline_diff = subprocess.run(
        [
            "git",
            "diff",
            "--quiet",
            "baseline-date2025-cnn400-v1",
            "HEAD",
            "--",
            str(
                MODEL_SOURCE.relative_to(
                    ROOT
                )
            ),
        ],
        cwd=ROOT,
        check=False,
    ).returncode

    if baseline_diff != 0:
        raise RuntimeError(
            "Protected model differs from baseline freeze"
        )

    registry_diff = subprocess.run(
        [
            "git",
            "diff",
            "--quiet",
            "reliability-eval-registry-v1",
            "HEAD",
            "--",
            str(
                REGISTRY.relative_to(
                    ROOT
                )
            ),
        ],
        cwd=ROOT,
        check=False,
    ).returncode

    if registry_diff != 0:
        raise RuntimeError(
            "Reliability registry differs from its freeze"
        )

    project_text = PROJECT_CONFIG.read_text(
        encoding="utf-8"
    )

    if (
        "- top_two_logit_margin"
        not in project_text
    ):
        raise RuntimeError(
            "Selected score is absent from declared "
            "project OOD candidate list"
        )

    return {
        "checkpoint_raw_sha256":
            checkpoint_sha,

        "model_source_raw_sha256":
            model_sha,

        "registry_raw_sha256":
            file_sha256(
                REGISTRY
            ),

        "project_config_raw_sha256":
            file_sha256(
                PROJECT_CONFIG
            ),
    }


def verify_registry_boundaries():
    registry = json.loads(
        REGISTRY.read_text()
    )

    rows = registry[
        "records"
    ]

    calibration = [
        row
        for row in rows
        if row[
            "partition"
        ]
        == "calibration"
    ]

    final_test = [
        row
        for row in rows
        if row[
            "partition"
        ]
        == "final_test"
    ]

    if len(
        calibration
    ) != 447:
        raise RuntimeError(
            "Calibration trial-row count changed"
        )

    if len(
        final_test
    ) != 1116:
        raise RuntimeError(
            "Final-test trial-row count changed"
        )

    calibration_trial_counts = {}

    calibration_window_counts = {}

    final_trial_counts = {}

    final_window_counts = {}

    for dataset in (
        "KFALL",
        "UNIVRFALL",
        "ONFIELD",
    ):
        calibration_rows = [
            row
            for row in calibration
            if row[
                "dataset"
            ]
            == dataset
        ]

        final_rows = [
            row
            for row in final_test
            if row[
                "dataset"
            ]
            == dataset
        ]

        calibration_trial_counts[
            dataset
        ] = len(
            calibration_rows
        )

        calibration_window_counts[
            dataset
        ] = sum(
            int(
                row[
                    "historical_windows"
                ]
            )
            for row
            in calibration_rows
        )

        final_trial_counts[
            dataset
        ] = len(
            final_rows
        )

        final_window_counts[
            dataset
        ] = sum(
            int(
                row[
                    "historical_windows"
                ]
            )
            for row
            in final_rows
        )

    if (
        calibration_trial_counts
        != EXPECTED_CALIBRATION_TRIAL_ROWS
    ):
        raise RuntimeError(
            "Calibration dataset trial counts changed"
        )

    if (
        calibration_window_counts
        != EXPECTED_CALIBRATION_WINDOWS
    ):
        raise RuntimeError(
            "Calibration dataset window counts changed"
        )

    if (
        final_trial_counts
        != EXPECTED_FINAL_TEST_TRIAL_ROWS
    ):
        raise RuntimeError(
            "Final-test dataset trial counts changed"
        )

    if (
        final_window_counts
        != EXPECTED_FINAL_TEST_WINDOWS
    ):
        raise RuntimeError(
            "Final-test dataset window counts changed"
        )

    for row in calibration:
        permission = (
            row[
                "prospective_constraints"
            ][
                "may_select_ood_operating_point"
            ]
        )

        if permission is not True:
            raise RuntimeError(
                "Calibration OOD-selection permission changed"
            )

    for row in final_test:
        permission = (
            row[
                "prospective_constraints"
            ][
                "may_select_ood_operating_point"
            ]
        )

        if permission is not False:
            raise RuntimeError(
                "Final-test OOD-selection permission changed"
            )

    return {
        "calibration_trial_rows":
            calibration_trial_counts,

        "calibration_windows":
            calibration_window_counts,

        "final_test_trial_rows":
            final_trial_counts,

        "final_test_windows":
            final_window_counts,
    }


def build_protocol():
    anchors = (
        verify_score_blind_anchors()
    )

    registry_boundary = (
        verify_registry_boundaries()
    )

    stratum_rows = []

    for row in EXPECTED_CALIBRATION_STRATA:
        n = int(
            row[
                "n"
            ]
        )

        r = stratum_rank(
            n,
            rejection_fraction=0.01,
        )

        stratum_rows.append(
            {
                "dataset":
                    row[
                        "dataset"
                    ],

                "class":
                    row[
                        "class"
                    ],

                "n":
                    n,

                "maximum_strictly_below_threshold_count":
                    r,

                "order_statistic_zero_based_index":
                    r,

                "minimum_empirical_acceptance_guaranteed":
                    (
                        1.0
                        - (
                            r
                            / n
                        )
                    ),
            }
        )

    protocol = {
        "protocol_id":
            "OOD_CALIBRATION_PROTOCOL_V1",

        "status":
            "frozen_before_first_ood_calibration_model_output_exposure",

        "scientific_role": {
            "trust_state":
                "OOD_UNKNOWN",

            "interpretation":
                (
                    "coverage-controlled residual task-model "
                    "unfamiliarity on an integrity-valid window"
                ),

            "not_claimed_as":
                [
                    "proof_of_novel_activity_class",
                    "proof_of_sensor_failure",
                    "qualified_integrity_cause",
                    "calibrated_true_ood_probability",
                ],

            "ood_positive_calibration_population_required":
                False,

            "reason_no_positive_population_used":
                (
                    "No prospectively justified OOD-positive "
                    "calibration corpus exists in the frozen project "
                    "lineage. Method and threshold are therefore fixed "
                    "from clean-ID coverage only."
                ),
        },

        "protected_model": {
            "baseline_id":
                "DATE2025_CNN_400MS_RECONSTRUCTED_V1",

            "baseline_tag":
                "baseline-date2025-cnn400-v1",

            "baseline_tag_commit":
                EXPECTED_BASELINE_COMMIT,

            "checkpoint_path":
                str(
                    CHECKPOINT
                ),

            "checkpoint_sha256":
                EXPECTED_CHECKPOINT_SHA256,

            "model_source":
                str(
                    MODEL_SOURCE.relative_to(
                        ROOT
                    )
                ),

            "model_source_raw_sha256":
                EXPECTED_MODEL_SOURCE_RAW_SHA256,

            "window_samples":
                40,

            "stored_channels":
                9,

            "effective_task_channels":
                6,

            "task_classes":
                [
                    "Activity",
                    "Falling",
                ],

            "task_model_forwards_per_window":
                1,

            "classifier_bypass_enabled":
                False,
        },

        "score": {
            "selected_method":
                SELECTED_METHOD,

            "selected_prospectively_before_ood_model_outputs":
                True,

            "formula_binary":
                "abs(logit_0 - logit_1)",

            "logit_class_order":
                [
                    "Activity",
                    "Falling",
                ],

            "direction":
                "smaller_margin_is_more_unfamiliar",

            "runtime_unknown_rule":
                "margin < threshold",

            "runtime_accept_rule":
                "margin >= threshold",

            "ties_at_threshold":
                "accepted",

            "requires_feature_vector":
                False,

            "requires_softmax":
                False,

            "requires_exp_or_log":
                False,

            "requires_second_task_model_forward":
                False,

            "candidate_methods_declared_before_selection":
                list(
                    CANDIDATE_METHODS
                ),

            "candidate_scores_evaluated_before_method_selection":
                False,

            "data_dependent_method_comparison_allowed":
                False,

            "selection_basis":
                [
                    (
                        "Already declared in configs/project.yaml "
                        "before OOD output exposure."
                    ),
                    (
                        "For a binary classifier the absolute top-two "
                        "logit margin is monotonic with maximum-softmax "
                        "confidence, so it preserves the same confidence "
                        "ranking without requiring softmax/exp."
                    ),
                    (
                        "It reuses task logits from the single protected "
                        "task-model forward and requires no prototype, "
                        "covariance, feature-distance, or additional "
                        "network computation."
                    ),
                    (
                        "Selection is aligned with the study's "
                        "resource-efficiency objective and is not "
                        "conditioned on calibration or final-test scores."
                    ),
                ],
        },

        "calibration_population": {
            "partition":
                "calibration",

            "historical_role":
                "validation",

            "registry_tag":
                "reliability-eval-registry-v1",

            "registry_tag_commit":
                EXPECTED_REGISTRY_COMMIT,

            "trial_row_count":
                447,

            "window_count":
                89868,

            "dataset_trial_rows":
                registry_boundary[
                    "calibration_trial_rows"
                ],

            "dataset_windows":
                registry_boundary[
                    "calibration_windows"
                ],

            "class_totals": {
                "Activity":
                    89544,
                "Falling":
                    324,
            },

            "nonempty_dataset_class_strata":
                stratum_rows,

            "empty_dataset_class_strata": [
                {
                    "dataset":
                        "ONFIELD",
                    "class":
                        "Falling",
                    "n":
                        0,
                    "included_in_threshold_constraint":
                        False,
                }
            ],

            "protected_array_shape":
                [
                    40,
                    9,
                ],

            "all_windows_treated_as_clean_id_for_threshold_selection":
                True,

            "integrity_corruptions_used":
                False,

            "external_domain_shift_data_used":
                False,

            "final_test_data_used":
                False,
        },

        "threshold_selection": {
            "single_global_threshold":
                True,

            "clean_id_acceptance_target":
                CLEAN_ID_ACCEPTANCE_TARGET,

            "constraint_scope":
                (
                    "every nonempty dataset_x_task_class "
                    "calibration stratum"
                ),

            "rejection_fraction":
                0.01,

            "per_stratum_rule": {
                "n_s":
                    "number of calibration margins in stratum s",

                "r_s":
                    "floor(0.01 * n_s)",

                "q_s":
                    "sorted_margin_s[r_s] using zero-based indexing",
            },

            "global_threshold_rule":
                "min(q_s over all nonempty strata)",

            "unknown_comparison":
                "strict_less_than",

            "accepted_comparison":
                "greater_than_or_equal",

            "tie_policy":
                "accept_equal_to_threshold",

            "guarantee":
                (
                    "At least 99% empirical clean-ID acceptance "
                    "in every nonempty protected calibration "
                    "dataset_x_class stratum."
                ),

            "threshold_selected_before_protocol_freeze":
                False,

            "threshold_selected_only_after_protocol_freeze":
                True,

            "threshold_may_be_modified_after_calibration_review":
                False,

            "threshold_may_be_modified_after_final_test_review":
                False,
        },

        "runtime_contract": {
            "decision_precedence": [
                "qualified_integrity_hard_cause",
                "ood_margin_gate",
                "valid",
            ],

            "qualified_integrity_hard_cause_state":
                "INTEGRITY_ALERT(C_t)",

            "ood_state_if_no_integrity_alert_and_margin_below_threshold":
                "OOD_UNKNOWN",

            "otherwise_state":
                "VALID",

            "suspect_only_integrity_indicator_populates_hard_cause_set":
                False,

            "ood_unknown_populates_integrity_cause_set":
                False,

            "task_prediction_still_computed":
                True,

            "task_prediction_still_returned":
                True,

            "classifier_bypass_enabled":
                False,

            "second_full_task_forward_allowed":
                False,

            "selected_ood_score_reuses":
                "task_logits_from_same_single_forward",
        },

        "calibration_outputs_predeclared": {
            "required": [
                "selected_threshold",
                "per_stratum_order_statistic_q_s",
                "per_stratum_r_s",
                "per_stratum_window_count",
                "per_stratum_accepted_count",
                "per_stratum_rejected_count",
                "per_stratum_empirical_acceptance",
                "overall_clean_id_acceptance",
                "dataset_clean_id_acceptance",
                "class_clean_id_acceptance",
                "task_prediction_metrics_descriptive_only",
                "checkpoint_and_source_hash_anchors",
                "access_audit",
            ],

            "method_comparison_table_required":
                False,

            "true_ood_detection_metrics_allowed":
                False,

            "auroc_claim_allowed":
                False,

            "ood_recall_claim_allowed":
                False,

            "tnr_at_tpr_claim_allowed":
                False,
        },

        "final_test_contract": {
            "partition":
                "final_test",

            "registry_trial_row_count":
                1116,

            "historical_window_count":
                366507,

            "dataset_trial_rows":
                registry_boundary[
                    "final_test_trial_rows"
                ],

            "dataset_windows":
                registry_boundary[
                    "final_test_windows"
                ],

            "may_select_method":
                False,

            "may_select_threshold":
                False,

            "may_modify_threshold":
                False,

            "may_modify_integrity_operating_point":
                False,

            "predeclared_metrics": [
                "overall_id_acceptance_rate",
                "overall_ood_unknown_rate",
                "dataset_id_acceptance_rate",
                "dataset_ood_unknown_rate",
                "task_class_id_acceptance_rate",
                "task_class_ood_unknown_rate",
                "dataset_x_class_id_acceptance_rate",
                "dataset_x_class_ood_unknown_rate",
                "task_metrics_overall",
                "task_metrics_conditioned_on_valid",
                "task_metrics_conditioned_on_ood_unknown",
            ],

            "interpretation_of_ood_unknown_rate":
                (
                    "ID rejection/unfamiliarity rate on the protected "
                    "historical test population, not true-OOD recall."
                ),
        },

        "external_domain_shift_contract": {
            "extra_recordings_used_for_calibration":
                False,

            "extra_recordings_used_for_method_selection":
                False,

            "extra_recordings_used_for_threshold_selection":
                False,

            "current_processed_extra_recordings_shape":
                [
                    30,
                    9,
                ],

            "protected_model_required_shape":
                [
                    40,
                    9,
                ],

            "current_extra_recordings_direct_model_compatibility":
                False,

            "future_external_evaluation_allowed":
                True,

            "future_requirement":
                (
                    "A separate score-blind 400-ms preprocessing/"
                    "resegmentation specification must be frozen "
                    "before model outputs are computed on "
                    "ExtraRecordings."
                ),

            "future_claim_boundary":
                (
                    "Report as external/domain-shift unfamiliarity "
                    "behavior unless stronger semantic OOD ground "
                    "truth is independently established."
                ),
        },

        "freeze_anchors": {
            "source_head_before_protocol_freeze":
                EXPECTED_PRE_PROTOCOL_HEAD,

            "integrity_final_test_result_tag":
                "integrity-final-test-result-v1",

            "integrity_final_test_result_commit":
                EXPECTED_INTEGRITY_RESULT_COMMIT,

            "baseline_tag":
                "baseline-date2025-cnn400-v1",

            "baseline_commit":
                EXPECTED_BASELINE_COMMIT,

            "registry_tag":
                "reliability-eval-registry-v1",

            "registry_commit":
                EXPECTED_REGISTRY_COMMIT,

            "lineage_tag":
                "reliability-lineage-v2",

            "lineage_commit":
                EXPECTED_LINEAGE_COMMIT,

            "checkpoint_raw_sha256":
                anchors[
                    "checkpoint_raw_sha256"
                ],

            "model_source_raw_sha256":
                anchors[
                    "model_source_raw_sha256"
                ],

            "registry_raw_sha256":
                anchors[
                    "registry_raw_sha256"
                ],

            "project_config_raw_sha256":
                anchors[
                    "project_config_raw_sha256"
                ],
        },

        "pre_freeze_exposure_boundary": {
            "checkpoint_bytes_hashed":
                True,

            "checkpoint_deserialized_for_ood":
                False,

            "model_weights_loaded_for_ood":
                False,

            "model_forward_executed_for_ood":
                False,

            "task_logits_read_for_ood":
                False,

            "task_features_read_for_ood":
                False,

            "ood_scores_computed":
                False,

            "ood_threshold_selected":
                False,

            "final_test_ood_outputs_read":
                False,

            "integrity_operating_point_reopened":
                False,

            "integrity_final_result_modified":
                False,
        },
    }

    protocol[
        "content_sha256"
    ] = canonical_digest(
        protocol
    )

    return protocol


def main():
    protocol = build_protocol()

    OUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUT.write_text(
        json.dumps(
            protocol,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        "OOD_CALIBRATION_PROTOCOL_V1_WRITTEN = True"
    )

    print(
        "PROTOCOL_PATH =",
        OUT,
    )

    print(
        "PROTOCOL_CONTENT_SHA256 =",
        protocol[
            "content_sha256"
        ],
    )

    print(
        "CALIBRATION_WINDOW_COUNT =",
        protocol[
            "calibration_population"
        ][
            "window_count"
        ],
    )

    print(
        "NONEMPTY_STRATUM_COUNT =",
        len(
            protocol[
                "calibration_population"
            ][
                "nonempty_dataset_class_strata"
            ]
        ),
    )

    print(
        "SELECTED_METHOD =",
        protocol[
            "score"
        ][
            "selected_method"
        ],
    )

    print(
        "CHECKPOINT_DESERIALIZED_FOR_OOD = False"
    )

    print(
        "MODEL_FORWARD_EXECUTED_FOR_OOD = False"
    )

    print(
        "OOD_SCORES_COMPUTED = False"
    )

    print(
        "OOD_THRESHOLD_SELECTED = False"
    )


if __name__ == "__main__":
    main()
