from __future__ import annotations

import json
import subprocess
from collections import Counter
from copy import deepcopy
from hashlib import sha256
from pathlib import Path


ROOT = Path(
    __file__
).resolve().parents[2]


EXPECTED_PRE_PROTOCOL_HEAD = (
    "fea9316d8510a5841baba48d273973e0267e4b28"
)

OOD_OPERATING_POINT_TAG = (
    "ood-operating-point-v1"
)

OOD_OPERATING_POINT_COMMIT = (
    "fea9316d8510a5841baba48d273973e0267e4b28"
)

OOD_CALIBRATION_RESULT_TAG = (
    "ood-calibration-result-v1"
)

OOD_CALIBRATION_RESULT_COMMIT = (
    "fea9316d8510a5841baba48d273973e0267e4b28"
)

OOD_CALIBRATION_EVALUATOR_TAG = (
    "ood-calibration-evaluator-v1b"
)

OOD_CALIBRATION_EVALUATOR_COMMIT = (
    "d879fbbfa512194b67f6a5087d0f76c7baa50227"
)

OOD_CALIBRATION_PROTOCOL_TAG = (
    "ood-calibration-protocol-v1"
)

OOD_CALIBRATION_PROTOCOL_COMMIT = (
    "9297a81411df9cfb3b3812f8eecd3b630c45bae4"
)

INTEGRITY_FINAL_RESULT_TAG = (
    "integrity-final-test-result-v1"
)

INTEGRITY_FINAL_RESULT_COMMIT = (
    "b1aaa28a5cd2222bd3acc7d5d86289ba9fd71c74"
)

BASELINE_TAG = (
    "baseline-date2025-cnn400-v1"
)

BASELINE_COMMIT = (
    "d6fe744b292139d18fd4dee37c96066bcf2d38c6"
)

REGISTRY_TAG = (
    "reliability-eval-registry-v1"
)

REGISTRY_COMMIT = (
    "416cc9d8895646c38edc6b7be1dfdc042d0c2219"
)

FINAL_OP = (
    ROOT
    / "configs/ood/"
      "ood_operating_point_v1.json"
)

CALIBRATION_RECEIPT = (
    ROOT
    / "data/manifests/"
      "ood_calibration_result_receipt_v1.json"
)

REGISTRY = (
    ROOT
    / "data/manifests/"
      "reliability_eval_registry_v1.json"
)

OUTPUT = (
    ROOT
    / "configs/ood/"
      "ood_final_test_protocol_v1.json"
)

FINAL_RESULT = (
    ROOT
    / "results/raw/"
      "ood_final_test_v1_candidate.json"
)

FINAL_RECEIPT = (
    ROOT
    / "data/manifests/"
      "ood_final_test_result_receipt_v1.json"
)

FINAL_EVALUATOR = (
    ROOT
    / "experiments/03_ood/"
      "evaluate_ood_final_test_v1.py"
)


FINAL_OP_RAW_SHA256 = (
    "46e343b5d44898f17942f8ba28257cd1"
    "389fc8bacf3f09026aeb226099ff3081"
)

FINAL_OP_CONTENT_SHA256 = (
    "0f23b8e152058d4f160861348e7fb295"
    "566af6be55083242db783a9a8e387747"
)

CALIBRATION_RECEIPT_RAW_SHA256 = (
    "523a128f2401371786400023167aca9c"
    "067267a10208d7885c21753afe76871c"
)

CALIBRATION_RECEIPT_CONTENT_SHA256 = (
    "3585507d2c70e4bf9c05c7d783933482"
    "41d4f1688b5bf67ccacb582193457f94"
)

FROZEN_THRESHOLD = (
    0.00914505124092102
)

EXPECTED_FINAL_ROWS = (
    1116
)

EXPECTED_FINAL_WINDOWS = (
    366507
)

EXPECTED_DATASET_ROWS = {
    "KFALL":
        932,

    "UNIVRFALL":
        176,

    "ONFIELD":
        8,
}

EXPECTED_DATASET_WINDOWS = {
    "KFALL":
        27068,

    "UNIVRFALL":
        7532,

    "ONFIELD":
        331907,
}


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
    file_path: Path,
) -> str:
    return sha256(
        file_path.read_bytes()
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


def verify_content_hash(
    data,
    expected,
):
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
            "Canonical content hash mismatch"
        )

    if stored != expected:
        raise RuntimeError(
            "Frozen canonical content changed"
        )

    return stored


def load_frozen_operating_point():
    if not FINAL_OP.is_file():
        raise RuntimeError(
            "Frozen OOD operating point absent"
        )

    if (
        file_sha256(
            FINAL_OP
        )
        != FINAL_OP_RAW_SHA256
    ):
        raise RuntimeError(
            "Frozen OOD operating-point raw bytes changed"
        )

    data = json.loads(
        FINAL_OP.read_text()
    )

    verify_content_hash(
        data,
        FINAL_OP_CONTENT_SHA256,
    )

    if (
        data[
            "operating_point_id"
        ]
        != "OOD_OPERATING_POINT_V1"
    ):
        raise RuntimeError(
            "Unexpected frozen operating-point identity"
        )

    if (
        data[
            "selected_method"
        ]
        != "top_two_logit_margin"
    ):
        raise RuntimeError(
            "Frozen OOD method changed"
        )

    if float(
        data[
            "threshold"
        ]
    ) != FROZEN_THRESHOLD:
        raise RuntimeError(
            "Frozen OOD threshold changed"
        )

    if (
        data[
            "ties_at_threshold_accepted"
        ]
        is not True
    ):
        raise RuntimeError(
            "Frozen threshold equality rule changed"
        )

    runtime = data[
        "runtime_contract"
    ]

    if (
        runtime[
            "task_model_forwards_per_window"
        ]
        != 1
    ):
        raise RuntimeError(
            "Frozen one-forward invariant changed"
        )

    if (
        runtime[
            "feature_vector_used_by_selected_score"
        ]
        is not False
    ):
        raise RuntimeError(
            "Feature vector unexpectedly used by OOD score"
        )

    if (
        runtime[
            "classifier_bypass_enabled"
        ]
        is not False
    ):
        raise RuntimeError(
            "Classifier bypass unexpectedly enabled"
        )

    if (
        data[
            "final_test_contract"
        ][
            "threshold_may_change_after_final_test"
        ]
        is not False
    ):
        raise RuntimeError(
            "Final-test threshold modification unexpectedly allowed"
        )

    if (
        data[
            "final_test_contract"
        ][
            "method_may_change_after_final_test"
        ]
        is not False
    ):
        raise RuntimeError(
            "Final-test method modification unexpectedly allowed"
        )

    return data


def load_calibration_receipt():
    if not CALIBRATION_RECEIPT.is_file():
        raise RuntimeError(
            "Frozen OOD calibration receipt absent"
        )

    if (
        file_sha256(
            CALIBRATION_RECEIPT
        )
        != CALIBRATION_RECEIPT_RAW_SHA256
    ):
        raise RuntimeError(
            "Calibration receipt raw bytes changed"
        )

    data = json.loads(
        CALIBRATION_RECEIPT.read_text()
    )

    verify_content_hash(
        data,
        CALIBRATION_RECEIPT_CONTENT_SHA256,
    )

    if (
        data[
            "scientific_boundary"
        ][
            "final_test_ood_outputs_read"
        ]
        is not False
    ):
        raise RuntimeError(
            "Calibration receipt claims final output exposure"
        )

    if (
        data[
            "scientific_boundary"
        ][
            "threshold_or_method_modified_after_output_review"
        ]
        is not False
    ):
        raise RuntimeError(
            "Calibration freeze boundary changed"
        )

    return data


def final_registry_rows():
    data = json.loads(
        REGISTRY.read_text()
    )

    rows = [
        row
        for row in data[
            "records"
        ]
        if row[
            "partition"
        ]
        == "final_test"
    ]

    rows.sort(
        key=lambda row:
            (
                row[
                    "dataset"
                ],
                row[
                    "trial_id"
                ],
            )
    )

    if len(
        rows
    ) != EXPECTED_FINAL_ROWS:
        raise RuntimeError(
            "Protected final-test trial count changed"
        )

    row_counts = Counter(
        row[
            "dataset"
        ]
        for row in rows
    )

    if dict(
        row_counts
    ) != EXPECTED_DATASET_ROWS:
        raise RuntimeError(
            "Protected final-test dataset trial counts changed"
        )

    window_counts = Counter()

    for row in rows:
        if (
            row[
                "prospective_constraints"
            ][
                "may_select_ood_operating_point"
            ]
            is not False
        ):
            raise RuntimeError(
                "Final-test OOD tuning permission unexpectedly enabled"
            )

        window_counts[
            row[
                "dataset"
            ]
        ] += int(
            row[
                "historical_windows"
            ]
        )

    if dict(
        window_counts
    ) != EXPECTED_DATASET_WINDOWS:
        raise RuntimeError(
            "Protected final-test window counts changed"
        )

    if sum(
        window_counts.values()
    ) != EXPECTED_FINAL_WINDOWS:
        raise RuntimeError(
            "Protected final-test total windows changed"
        )

    return rows


def verify_frozen_anchors():
    expected_refs = {
        "ood-operating-point-v1^{commit}":
            OOD_OPERATING_POINT_COMMIT,

        "ood-calibration-result-v1^{commit}":
            OOD_CALIBRATION_RESULT_COMMIT,

        "ood-calibration-evaluator-v1b^{commit}":
            OOD_CALIBRATION_EVALUATOR_COMMIT,

        "ood-calibration-protocol-v1^{commit}":
            OOD_CALIBRATION_PROTOCOL_COMMIT,

        "integrity-final-test-result-v1^{commit}":
            INTEGRITY_FINAL_RESULT_COMMIT,

        "baseline-date2025-cnn400-v1^{commit}":
            BASELINE_COMMIT,

        "reliability-eval-registry-v1^{commit}":
            REGISTRY_COMMIT,
    }

    for ref, expected in expected_refs.items():
        observed = git(
            "rev-parse",
            ref,
        )

        if observed != expected:
            raise RuntimeError(
                f"Frozen ref moved: {ref}: {observed}"
            )

    if git(
        "rev-parse",
        "HEAD",
    ) != EXPECTED_PRE_PROTOCOL_HEAD:
        raise RuntimeError(
            "HEAD changed before final-test protocol freeze"
        )

    for ref in (
        "ood-operating-point-v1",
        "ood-calibration-result-v1",
        "ood-calibration-evaluator-v1b",
        "ood-calibration-protocol-v1",
        "integrity-final-test-result-v1",
        "baseline-date2025-cnn400-v1",
        "reliability-eval-registry-v1",
    ):
        rc = subprocess.run(
            [
                "git",
                "merge-base",
                "--is-ancestor",
                ref,
                "HEAD",
            ],
            cwd=ROOT,
            check=False,
        ).returncode

        if rc != 0:
            raise RuntimeError(
                f"Frozen ref is not ancestor: {ref}"
            )

    for frozen_file in (
        FINAL_OP,
        CALIBRATION_RECEIPT,
        REGISTRY,
    ):
        rc = subprocess.run(
            [
                "git",
                "diff",
                "--quiet",
                "--",
                str(
                    frozen_file.relative_to(
                        ROOT
                    )
                ),
            ],
            cwd=ROOT,
            check=False,
        ).returncode

        if rc != 0:
            raise RuntimeError(
                f"Frozen input modified in worktree: {frozen_file}"
            )

    load_frozen_operating_point()
    load_calibration_receipt()
    final_registry_rows()


def build_protocol():
    verify_frozen_anchors()

    for target in (
        FINAL_RESULT,
        FINAL_RECEIPT,
        FINAL_EVALUATOR,
    ):
        if target.exists():
            raise RuntimeError(
                f"Protected final-test target already exists: {target}"
            )

    op = load_frozen_operating_point()

    payload = {
        "protocol_id":
            "OOD_FINAL_TEST_PROTOCOL_V1",

        "status":
            "frozen_before_first_final_test_ood_model_output_exposure",

        "purpose":
            (
                "Single-use protected historical-ID evaluation of the "
                "already-frozen OOD_UNKNOWN operating point."
            ),

        "source_anchors": {
            "ood_operating_point": {
                "tag":
                    OOD_OPERATING_POINT_TAG,

                "tag_commit":
                    OOD_OPERATING_POINT_COMMIT,

                "raw_sha256":
                    FINAL_OP_RAW_SHA256,

                "content_sha256":
                    FINAL_OP_CONTENT_SHA256,
            },

            "ood_calibration_result": {
                "tag":
                    OOD_CALIBRATION_RESULT_TAG,

                "tag_commit":
                    OOD_CALIBRATION_RESULT_COMMIT,
            },

            "ood_calibration_evaluator": {
                "tag":
                    OOD_CALIBRATION_EVALUATOR_TAG,

                "tag_commit":
                    OOD_CALIBRATION_EVALUATOR_COMMIT,
            },

            "ood_calibration_protocol": {
                "tag":
                    OOD_CALIBRATION_PROTOCOL_TAG,

                "tag_commit":
                    OOD_CALIBRATION_PROTOCOL_COMMIT,
            },

            "integrity_final_test_result": {
                "tag":
                    INTEGRITY_FINAL_RESULT_TAG,

                "tag_commit":
                    INTEGRITY_FINAL_RESULT_COMMIT,
            },

            "protected_baseline": {
                "tag":
                    BASELINE_TAG,

                "tag_commit":
                    BASELINE_COMMIT,
            },

            "reliability_registry": {
                "tag":
                    REGISTRY_TAG,

                "tag_commit":
                    REGISTRY_COMMIT,
            },

            "ood_calibration_receipt": {
                "raw_sha256":
                    CALIBRATION_RECEIPT_RAW_SHA256,

                "content_sha256":
                    CALIBRATION_RECEIPT_CONTENT_SHA256,
            },
        },

        "frozen_ood_operating_point": {
            "selected_method":
                "top_two_logit_margin",

            "score_formula":
                "abs(logit_0 - logit_1)",

            "threshold":
                FROZEN_THRESHOLD,

            "unknown_rule":
                "margin < threshold",

            "accepted_rule":
                "margin >= threshold",

            "ties_at_threshold_accepted":
                True,

            "threshold_may_change":
                False,

            "method_may_change":
                False,

            "feature_vector_used_by_selected_score":
                False,

            "second_full_task_model_forward_allowed":
                False,
        },

        "protected_final_test_population": {
            "partition":
                "final_test",

            "trial_rows":
                EXPECTED_FINAL_ROWS,

            "historical_windows":
                EXPECTED_FINAL_WINDOWS,

            "dataset_trial_rows":
                dict(
                    EXPECTED_DATASET_ROWS
                ),

            "dataset_historical_windows":
                dict(
                    EXPECTED_DATASET_WINDOWS
                ),

            "ood_operating_point_selection_permission":
                False,

            "threshold_tuning_permission":
                False,

            "method_selection_permission":
                False,
        },

        "single_use_execution_contract": {
            "successful_final_test_model_output_exposure_runs_allowed":
                1,

            "rerun_after_success_allowed":
                False,

            "pre_output_technical_failure_may_be_corrected_only_with_new_frozen_evaluator_revision":
                True,

            "failed_attempt_provenance_must_be_preserved":
                True,

            "final_test_outputs_may_not_change_threshold":
                True,

            "final_test_outputs_may_not_change_method":
                True,

            "final_test_outputs_may_not_change_integrity_operating_point":
                True,
        },

        "runtime_contract": {
            "decision_precedence": [
                "qualified_integrity_hard_cause",
                "ood_margin_gate",
                "valid",
            ],

            "integrity_alert_state":
                "INTEGRITY_ALERT(C_t)",

            "ood_state":
                "OOD_UNKNOWN",

            "valid_state":
                "VALID",

            "task_model_forwards_per_window":
                1,

            "task_logits_source":
                "same_single_task_forward",

            "selected_ood_score_uses":
                "task_logits_only",

            "feature_vector_used_by_selected_ood_score":
                False,

            "second_full_task_forward_allowed":
                False,

            "classifier_bypass_enabled":
                False,

            "task_prediction_still_computed":
                True,

            "task_prediction_still_returned":
                True,

            "integrity_operating_point_reopened":
                False,
        },

        "predeclared_final_outputs": {
            "overall": [
                "protected_id_window_count",
                "accepted_count",
                "ood_unknown_count",
                "empirical_acceptance",
                "empirical_ood_unknown_rate",
            ],

            "by_dataset": [
                "window_count",
                "accepted_count",
                "ood_unknown_count",
                "empirical_acceptance",
                "empirical_ood_unknown_rate",
            ],

            "by_task_class": [
                "window_count",
                "accepted_count",
                "ood_unknown_count",
                "empirical_acceptance",
                "empirical_ood_unknown_rate",
            ],

            "task_metrics_descriptive_only": [
                "argmax_confusion_matrix_activity_falling",
                "accuracy",
                "macro_precision",
                "macro_recall",
                "macro_f1",
                "fall_precision",
                "fall_recall",
                "fall_f1",
                "fall_false_negative_rate",
            ],

            "access_audit_required":
                True,

            "true_ood_auroc_allowed":
                False,

            "true_ood_recall_allowed":
                False,

            "true_ood_precision_allowed":
                False,

            "tnr_at_tpr_allowed":
                False,

            "threshold_selection_metric_allowed":
                False,

            "method_comparison_allowed":
                False,
        },

        "scientific_interpretation": {
            "population_role":
                "protected_historical_ID_generalization_evaluation",

            "ood_unknown_rate_means":
                (
                    "protected historical-ID rejection / residual "
                    "task-model unfamiliarity rate under the already-frozen gate"
                ),

            "ood_unknown_rate_does_not_mean":
                [
                    "true_ood_recall",
                    "novel_activity_detection_probability",
                    "sensor_failure_probability",
                    "qualified_integrity_cause_rate",
                ],

            "absence_of_ood_unknown_does_not_establish":
                "ability_to_detect_true_unknown_activity",

            "true_ood_positive_population_present":
                False,

            "extra_recordings_used":
                False,

            "external_domain_shift_evaluation_part_of_this_protocol":
                False,
        },

        "task_metric_boundary": {
            "task_metrics_are":
                "descriptive_argmax_metrics_from_the_same_task_logits",

            "task_metrics_are_not":
                "a_redefinition_of_the_historical_deployed_falling_event_rule",

            "task_metrics_may_not_select_ood_threshold":
                True,

            "task_metrics_may_not_select_ood_method":
                True,
        },

        "exposure_boundary_at_protocol_freeze": {
            "final_test_registry_metadata_read":
                True,

            "final_test_sensor_arrays_opened":
                False,

            "final_test_label_arrays_opened":
                False,

            "checkpoint_deserialized_for_final_test_ood":
                False,

            "protected_model_loaded_for_final_test_ood":
                False,

            "protected_model_forward_executed_for_final_test_ood":
                False,

            "final_test_task_logits_read":
                False,

            "final_test_features_read":
                False,

            "final_test_ood_margins_computed":
                False,

            "final_test_ood_states_computed":
                False,

            "final_test_ood_outputs_read":
                False,
        },

        "next_required_freeze":
            (
                "A final-test evaluator implementation must be frozen "
                "before the first protected final-test array or model-output exposure."
            ),
    }

    payload[
        "content_sha256"
    ] = canonical_digest(
        payload
    )

    return payload


def main():
    protocol = build_protocol()

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT.write_text(
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
        "OOD_FINAL_TEST_PROTOCOL_V1_WRITTEN = True"
    )

    print(
        "PROTOCOL_PATH =",
        OUTPUT,
    )

    print(
        "PROTOCOL_CONTENT_SHA256 =",
        protocol[
            "content_sha256"
        ],
    )

    print(
        "FINAL_TEST_TRIAL_ROWS =",
        protocol[
            "protected_final_test_population"
        ][
            "trial_rows"
        ],
    )

    print(
        "FINAL_TEST_WINDOWS =",
        protocol[
            "protected_final_test_population"
        ][
            "historical_windows"
        ],
    )

    print(
        "FROZEN_METHOD =",
        protocol[
            "frozen_ood_operating_point"
        ][
            "selected_method"
        ],
    )

    print(
        "FROZEN_THRESHOLD =",
        protocol[
            "frozen_ood_operating_point"
        ][
            "threshold"
        ],
    )

    print(
        "FINAL_TEST_SENSOR_ARRAYS_OPENED = False"
    )

    print(
        "FINAL_TEST_LABEL_ARRAYS_OPENED = False"
    )

    print(
        "MODEL_FORWARD_EXECUTED_FOR_FINAL_TEST_OOD = False"
    )

    print(
        "FINAL_TEST_OOD_OUTPUTS_READ = False"
    )


if __name__ == "__main__":
    main()
