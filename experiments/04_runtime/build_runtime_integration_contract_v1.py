from __future__ import annotations

import ast
import json
import subprocess
from copy import deepcopy
from hashlib import sha256
from pathlib import Path


ROOT = Path(
    __file__
).resolve().parents[2]


EXPECTED_PRE_CONTRACT_HEAD = (
    "7d7db3d1efec177830239597803410384c154f07"
)

OOD_FINAL_RESULT_COMMIT = (
    "7d7db3d1efec177830239597803410384c154f07"
)

OOD_OPERATING_POINT_COMMIT = (
    "fea9316d8510a5841baba48d273973e0267e4b28"
)

INTEGRITY_FINAL_RESULT_COMMIT = (
    "b1aaa28a5cd2222bd3acc7d5d86289ba9fd71c74"
)

INTEGRITY_OPERATING_POINT_COMMIT = (
    "9ac878ea6a40e8c01a60e42e602a1fa9fc688d3b"
)

BASELINE_COMMIT = (
    "d6fe744b292139d18fd4dee37c96066bcf2d38c6"
)


HISTORICAL_DECISION = (
    ROOT
    / "src/imu_reliability/baseline/"
      "historical_decision.py"
)

MODEL_SOURCE = (
    ROOT
    / "src/imu_reliability/baseline/"
      "date2025_cnn400.py"
)

INTEGRITY_INIT = (
    ROOT
    / "src/imu_reliability/integrity/"
      "__init__.py"
)

INTEGRITY_EVIDENCE = (
    ROOT
    / "src/imu_reliability/integrity/"
      "evidence.py"
)

FRAME_GAP = (
    ROOT
    / "src/imu_reliability/integrity/"
      "frame_gap.py"
)

TIMING = (
    ROOT
    / "src/imu_reliability/integrity/"
      "timing.py"
)

FLATNESS = (
    ROOT
    / "src/imu_reliability/integrity/"
      "flatness.py"
)

INTEGRITY_MONITOR = (
    ROOT
    / "src/imu_reliability/integrity/"
      "monitor.py"
)

INTEGRITY_OP = (
    ROOT
    / "configs/integrity/"
      "integrity_operating_point_v1.json"
)

OOD_OP = (
    ROOT
    / "configs/ood/"
      "ood_operating_point_v1.json"
)

OUTPUT = (
    ROOT
    / "configs/runtime/"
      "runtime_integration_contract_v1.json"
)


SOURCE_HASHES = {
    HISTORICAL_DECISION:
        "4badaf73460402447ac5c4253017db15de07964d7182f098a4d335f1670ed9ab",

    MODEL_SOURCE:
        "def71b3cebc0649c0d909e4ffd5dc04f177fcb795ff6ebfd13f90e214c67581d",

    INTEGRITY_INIT:
        "05ecb0410c041d4a345830d71ebbb131a67b065a5ea3676dd23bc7cee03dff58",

    INTEGRITY_EVIDENCE:
        "170443ff777f20da338415f6d2cbbfc1cece5067d22aa38fb4572243d885e560",

    FRAME_GAP:
        "7ff5e113005e3c3ba31e1500e25d649e10566fd81fc529d7548930587703ddfb",

    TIMING:
        "6dce01804e4557a4390ecc61fb5b2d04d7a5733aaa65ffafa30d4ce45f4664de",

    FLATNESS:
        "fec5874bc61fc5995606b5bd7dabcc64f25bc35d08b335510959ba06740f88fc",

    INTEGRITY_MONITOR:
        "09c4f18ba03981747cfb9ff417501f68570e8108c4f0b390d80b7960a24f6c87",
}


INTEGRITY_OP_CONTENT_SHA = (
    "02c7d6dabb5951409dd34491384fc2a8"
    "00ef02a7b1ad0006098845925d847f59"
)

OOD_OP_RAW_SHA = (
    "46e343b5d44898f17942f8ba28257cd1"
    "389fc8bacf3f09026aeb226099ff3081"
)

OOD_OP_CONTENT_SHA = (
    "0f23b8e152058d4f160861348e7fb295"
    "566af6be55083242db783a9a8e387747"
)

OOD_THRESHOLD = (
    0.00914505124092102
)

HISTORICAL_PREDICTION_BIAS = (
    0.9
)


PLANNED_IMPLEMENTATION_TARGETS = (
    ROOT
    / "src/imu_reliability/runtime/__init__.py",

    ROOT
    / "src/imu_reliability/runtime/decision.py",

    ROOT
    / "src/imu_reliability/runtime/reliability.py",

    ROOT
    / "tests/test_runtime_reliability.py",
)


def file_sha256(
    path: Path,
) -> str:
    return sha256(
        path.read_bytes()
    ).hexdigest()


def canonical_digest(
    payload,
) -> str:
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
            "Frozen canonical content hash mismatch"
        )

    if stored != expected:
        raise RuntimeError(
            "Frozen content anchor changed"
        )


def git(
    *args,
):
    return subprocess.check_output(
        [
            "/usr/bin/git",
            *args,
        ],
        cwd=ROOT,
        text=True,
    ).strip()


def verify_git_anchors():
    if git(
        "rev-parse",
        "HEAD",
    ) != EXPECTED_PRE_CONTRACT_HEAD:
        raise RuntimeError(
            "HEAD changed before runtime contract freeze"
        )

    refs = {
        "ood-final-test-result-v1^{commit}":
            OOD_FINAL_RESULT_COMMIT,

        "ood-operating-point-v1^{commit}":
            OOD_OPERATING_POINT_COMMIT,

        "integrity-final-test-result-v1^{commit}":
            INTEGRITY_FINAL_RESULT_COMMIT,

        "integrity-operating-point-v1^{commit}":
            INTEGRITY_OPERATING_POINT_COMMIT,

        "baseline-date2025-cnn400-v1^{commit}":
            BASELINE_COMMIT,
    }

    for ref, expected in refs.items():
        observed = git(
            "rev-parse",
            ref,
        )

        if observed != expected:
            raise RuntimeError(
                f"Frozen ref moved: {ref}: {observed}"
            )

    for ref in (
        "ood-final-test-result-v1",
        "ood-operating-point-v1",
        "integrity-final-test-result-v1",
        "integrity-operating-point-v1",
        "baseline-date2025-cnn400-v1",
    ):
        rc = subprocess.run(
            [
                "/usr/bin/git",
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


def verify_source_anchors():
    for path, expected in SOURCE_HASHES.items():
        if not path.is_file():
            raise RuntimeError(
                f"Frozen source absent: {path}"
            )

        observed = file_sha256(
            path
        )

        if observed != expected:
            raise RuntimeError(
                f"Frozen source changed: {path}"
            )


def verify_historical_decision_api():
    source = HISTORICAL_DECISION.read_text(
        encoding="utf-8"
    )

    tree = ast.parse(
        source
    )

    constants = {}

    functions = {}

    for node in tree.body:
        if isinstance(
            node,
            ast.Assign,
        ):
            if len(
                node.targets
            ) != 1:
                continue

            target = node.targets[0]

            if isinstance(
                target,
                ast.Name,
            ):
                try:
                    constants[
                        target.id
                    ] = ast.literal_eval(
                        node.value
                    )
                except Exception:
                    pass

        if isinstance(
            node,
            ast.FunctionDef,
        ):
            functions[
                node.name
            ] = node

    if constants.get(
        "HISTORICAL_PREDICTION_BIAS"
    ) != 0.9:
        raise RuntimeError(
            "Historical prediction bias changed"
        )

    if constants.get(
        "ACTIVITY_CLASS"
    ) != 0:
        raise RuntimeError(
            "Historical Activity class changed"
        )

    if constants.get(
        "FALLING_CLASS"
    ) != 1:
        raise RuntimeError(
            "Historical Falling class changed"
        )

    if (
        "decision_from_probabilities"
        not in functions
        or "decision_from_logits"
        not in functions
    ):
        raise RuntimeError(
            "Historical decision APIs changed"
        )

    if (
        "accepted = max_prob > prediction_bias"
        not in source
    ):
        raise RuntimeError(
            "Historical strict decision boundary changed"
        )

    if (
        "torch.softmax"
        not in source
    ):
        raise RuntimeError(
            "Historical logits-to-probability path changed"
        )


def verify_model_api():
    source = MODEL_SOURCE.read_text(
        encoding="utf-8"
    )

    tree = ast.parse(
        source
    )

    model_class = None

    for node in tree.body:
        if (
            isinstance(
                node,
                ast.ClassDef,
            )
            and node.name
            == "Date2025CNN400"
        ):
            model_class = node
            break

    if model_class is None:
        raise RuntimeError(
            "Date2025CNN400 class absent"
        )

    methods = {
        node.name:
            node
        for node in model_class.body
        if isinstance(
            node,
            ast.FunctionDef,
        )
    }

    for required in (
        "_backbone",
        "forward",
        "forward_with_features",
    ):
        if required not in methods:
            raise RuntimeError(
                f"Protected model API absent: {required}"
            )

    forward_source = ast.get_source_segment(
        source,
        methods[
            "forward"
        ],
    )

    if (
        "self._backbone(x)"
        not in forward_source
    ):
        raise RuntimeError(
            "Protected task forward changed"
        )


def verify_frozen_operating_points():
    integrity = json.loads(
        INTEGRITY_OP.read_text()
    )

    verify_content_hash(
        integrity,
        INTEGRITY_OP_CONTENT_SHA,
    )

    if (
        integrity[
            "operating_point_id"
        ]
        != "INTEGRITY_OPERATING_POINT_V1"
    ):
        raise RuntimeError(
            "Integrity operating point identity changed"
        )

    supported = (
        integrity[
            "hard_cause_set_contract"
        ][
            "historical_p0_v1_supported_external_causes"
        ]
    )

    if supported != [
        "FRAME_GAP"
    ]:
        raise RuntimeError(
            "V1 supported hard-cause set changed"
        )

    if (
        integrity[
            "FRAME_GAP"
        ][
            "KFALL"
        ][
            "enabled"
        ]
        is not True
    ):
        raise RuntimeError(
            "Qualified FRAME_GAP operating point changed"
        )

    if (
        integrity[
            "FRAME_GAP"
        ][
            "UNIVRFALL"
        ][
            "hard_detection_enabled"
        ]
        is not False
    ):
        raise RuntimeError(
            "Unqualified UniVR counter was hard-promoted"
        )

    if (
        integrity[
            "CHANNEL_FREEZE_SUSPECT"
        ][
            "enters_hard_cause_set"
        ]
        is not False
    ):
        raise RuntimeError(
            "Channel freeze suspect was hard-promoted"
        )

    for dataset in (
        "KFALL",
        "UNIVRFALL",
    ):
        if (
            integrity[
                "TIMING_OBSERVATION_ENVELOPE"
            ][
                dataset
            ][
                "hard_cause_promotion"
            ]
            is not False
        ):
            raise RuntimeError(
                "Timing was hard-promoted"
            )

    if file_sha256(
        OOD_OP
    ) != OOD_OP_RAW_SHA:
        raise RuntimeError(
            "Frozen OOD operating-point raw bytes changed"
        )

    ood = json.loads(
        OOD_OP.read_text()
    )

    verify_content_hash(
        ood,
        OOD_OP_CONTENT_SHA,
    )

    if (
        ood[
            "selected_method"
        ]
        != "top_two_logit_margin"
    ):
        raise RuntimeError(
            "OOD method changed"
        )

    if float(
        ood[
            "threshold"
        ]
    ) != OOD_THRESHOLD:
        raise RuntimeError(
            "OOD threshold changed"
        )

    if (
        ood[
            "ties_at_threshold_accepted"
        ]
        is not True
    ):
        raise RuntimeError(
            "OOD equality rule changed"
        )

    runtime = ood[
        "runtime_contract"
    ]

    if runtime[
        "decision_precedence"
    ] != [
        "qualified_integrity_hard_cause",
        "ood_margin_gate",
        "valid",
    ]:
        raise RuntimeError(
            "Runtime precedence changed"
        )

    if (
        runtime[
            "task_model_forwards_per_window"
        ]
        != 1
    ):
        raise RuntimeError(
            "One-forward invariant changed"
        )

    if (
        runtime[
            "second_full_task_forward_allowed"
        ]
        is not False
    ):
        raise RuntimeError(
            "Second task forward unexpectedly allowed"
        )

    if (
        runtime[
            "feature_vector_used_by_selected_score"
        ]
        is not False
    ):
        raise RuntimeError(
            "Feature vector unexpectedly selected for OOD"
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
        runtime[
            "task_prediction_still_returned"
        ]
        is not True
    ):
        raise RuntimeError(
            "Task prediction return invariant changed"
        )


def verify_implementation_absent():
    for path in PLANNED_IMPLEMENTATION_TARGETS:
        if path.exists():
            raise RuntimeError(
                f"Runtime implementation unexpectedly preexists: {path}"
            )


def build_contract():
    verify_git_anchors()
    verify_source_anchors()
    verify_historical_decision_api()
    verify_model_api()
    verify_frozen_operating_points()
    verify_implementation_absent()

    payload = {
        "contract_id":
            "RUNTIME_INTEGRATION_CONTRACT_V1",

        "status":
            "frozen_before_runtime_wrapper_implementation",

        "purpose":
            (
                "Reference runtime integration of the frozen historical "
                "task decision, evidence-qualified integrity state, and "
                "frozen OOD_UNKNOWN gate without statistical reopening."
            ),

        "source_anchors": {
            "ood_final_test_result": {
                "tag":
                    "ood-final-test-result-v1",

                "tag_commit":
                    OOD_FINAL_RESULT_COMMIT,
            },

            "ood_operating_point": {
                "tag":
                    "ood-operating-point-v1",

                "tag_commit":
                    OOD_OPERATING_POINT_COMMIT,

                "raw_sha256":
                    OOD_OP_RAW_SHA,

                "content_sha256":
                    OOD_OP_CONTENT_SHA,
            },

            "integrity_final_test_result": {
                "tag":
                    "integrity-final-test-result-v1",

                "tag_commit":
                    INTEGRITY_FINAL_RESULT_COMMIT,
            },

            "integrity_operating_point": {
                "tag":
                    "integrity-operating-point-v1",

                "tag_commit":
                    INTEGRITY_OPERATING_POINT_COMMIT,

                "content_sha256":
                    INTEGRITY_OP_CONTENT_SHA,
            },

            "protected_baseline": {
                "tag":
                    "baseline-date2025-cnn400-v1",

                "tag_commit":
                    BASELINE_COMMIT,
            },

            "runtime_dependency_source_sha256": {
                str(
                    path.relative_to(
                        ROOT
                    )
                ):
                    digest
                for path, digest
                in SOURCE_HASHES.items()
            },
        },

        "input_contract": {
            "reference_execution_unit":
                "one_400ms_window",

            "model_input_shape":
                [
                    1,
                    40,
                    9,
                ],

            "window_samples":
                40,

            "stored_input_channels":
                9,

            "batch_size":
                1,

            "integrity_input":
                "IntegrityAssessment",

            "integrity_assessment_is_constructed_from_evidence":
                True,

            "runtime_wrapper_does_not_invent_integrity_evidence":
                True,
        },

        "task_model_contract": {
            "model_class":
                "Date2025CNN400",

            "reference_runtime_model_call":
                "model(window)",

            "selected_python_model_api":
                "Date2025CNN400.forward",

            "full_task_model_invocations_per_window":
                1,

            "second_full_task_model_forward_allowed":
                False,

            "model_must_already_be_in_inference_mode":
                True,

            "ood_requires_additional_model":
                False,

            "ood_requires_penultimate_feature":
                False,
        },

        "historical_task_decision_contract": {
            "function":
                "decision_from_logits",

            "prediction_bias":
                HISTORICAL_PREDICTION_BIAS,

            "activity_class":
                0,

            "falling_class":
                1,

            "probability_transform":
                "softmax(logits, dim=1)",

            "historical_acceptance_test":
                "max_probability > 0.9",

            "comparison_is_strict":
                True,

            "binary_equivalent":
                "Falling iff P(Falling) > 0.9; Activity otherwise",

            "plain_argmax_may_replace_historical_decision":
                False,

            "task_prediction_always_computed":
                True,

            "task_prediction_always_returned":
                True,
        },

        "integrity_runtime_contract": {
            "assessment_type":
                "IntegrityAssessment",

            "hard_alert_test":
                "assessment.has_hard_alert",

            "supported_v1_hard_cause_mask":
                [
                    "FRAME_GAP",
                ],

            "frame_gap_requires":
                "HARD_QUALIFIED provenance-qualified direct acquisition counter evidence",

            "unverified_or_derived_counter_gap_enters_hard_set":
                False,

            "channel_freeze_enters_hard_set":
                False,

            "timing_observation_enters_hard_set":
                False,

            "frame_repeat_inferred_from_duplicate_counter":
                False,

            "buffer_stall_inferred_from_duplicate_counter":
                False,

            "unsupported_hard_cause_mask_policy":
                "runtime_contract_violation_do_not_silently_promote_or_drop",

            "multiple_supported_qualified_causes_are_retained":
                True,

            "suspects_may_be_returned_for_diagnostics":
                True,

            "suspects_change_primary_trust_state":
                False,

            "observation_only_evidence_changes_primary_trust_state":
                False,
        },

        "ood_runtime_contract": {
            "method":
                "top_two_logit_margin",

            "binary_score_formula":
                "abs(logit_0 - logit_1)",

            "score_source":
                "task_logits_from_the_same_single_task_forward",

            "threshold":
                OOD_THRESHOLD,

            "unknown_rule":
                "margin < threshold",

            "accepted_rule":
                "margin >= threshold",

            "ties_at_threshold_accepted":
                True,

            "feature_vector_used":
                False,

            "second_model_forward_used":
                False,

            "threshold_may_change":
                False,

            "method_may_change":
                False,

            "true_ood_probability_claimed":
                False,
        },

        "decision_precedence": [
            {
                "priority":
                    1,

                "condition":
                    "supported qualified integrity hard-cause set is non-empty",

                "trust_state":
                    "INTEGRITY_ALERT",
            },
            {
                "priority":
                    2,

                "condition":
                    "no hard integrity cause and margin < 0.00914505124092102",

                "trust_state":
                    "OOD_UNKNOWN",
            },
            {
                "priority":
                    3,

                "condition":
                    "otherwise",

                "trust_state":
                    "VALID",
            },
        ],

        "output_contract": {
            "trust_states": [
                "VALID",
                "OOD_UNKNOWN",
                "INTEGRITY_ALERT",
            ],

            "task_prediction":
                "always_present",

            "integrity_cause_mask":
                "always_present",

            "ood_margin":
                "always_present_from_same_logits",

            "ood_threshold":
                OOD_THRESHOLD,

            "suspect_indicators":
                "diagnostic_only",

            "integrity_alert_does_not_suppress_task_prediction":
                True,

            "ood_unknown_does_not_suppress_task_prediction":
                True,
        },

        "planned_python_reference_api": {
            "package":
                "imu_reliability.runtime",

            "decision_module":
                "src/imu_reliability/runtime/decision.py",

            "reliability_module":
                "src/imu_reliability/runtime/reliability.py",

            "trust_state_enum":
                "TrustState",

            "decision_record":
                "ReliabilityDecision",

            "pure_decision_function":
                "decide_from_logits",

            "integrated_single_window_function":
                "run_reliability_window",

            "integrated_function_behavior":
                (
                    "perform exactly one protected task-model forward, "
                    "derive the historical task prediction and frozen "
                    "logit-margin score from those logits, then apply "
                    "integrity > OOD > VALID precedence"
                ),
        },

        "implementation_safety_contract": {
            "may_modify_integrity_operating_point":
                False,

            "may_modify_ood_threshold":
                False,

            "may_modify_ood_method":
                False,

            "may_rerun_integrity_final_evaluator":
                False,

            "may_rerun_ood_calibration_evaluator":
                False,

            "may_rerun_ood_final_test_evaluator":
                False,

            "may_use_final_outputs_for_new_selection":
                False,

            "classifier_bypass_allowed":
                False,

            "additional_task_model_forward_allowed":
                False,
        },

        "resource_evidence_boundary": {
            "exact_stm32_latency_claimed_at_contract_freeze":
                False,

            "exact_stm32_flash_overhead_claimed_at_contract_freeze":
                False,

            "exact_stm32_ram_overhead_claimed_at_contract_freeze":
                False,

            "exact_stm32_energy_overhead_claimed_at_contract_freeze":
                False,

            "tracked_embedded_firmware_present_at_contract_freeze":
                False,

            "required_next_evidence_after_reference_runtime":
                [
                    "reference_runtime_functional_tests",
                    "single_forward_call-count evidence",
                    "runtime_wrapper CPU overhead",
                    "runtime wrapper memory overhead",
                    "embedded translation or recovered firmware integration path",
                    "target-specific flash RAM latency measurements before deployment claims",
                ],
        },

        "freeze_boundary": {
            "torch_imported_by_builder":
                False,

            "checkpoint_deserialized":
                False,

            "dataset_arrays_opened":
                False,

            "model_forward_executed":
                False,

            "scientific_selection_reopened":
                False,

            "runtime_implementation_created":
                False,
        },
    }

    payload[
        "content_sha256"
    ] = canonical_digest(
        payload
    )

    return payload


def main():
    contract = build_contract()

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if OUTPUT.exists():
        raise RuntimeError(
            "Refusing to overwrite runtime integration contract"
        )

    OUTPUT.write_text(
        json.dumps(
            contract,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        "RUNTIME_INTEGRATION_CONTRACT_V1_WRITTEN = True"
    )

    print(
        "CONTRACT_CONTENT_SHA256 =",
        contract[
            "content_sha256"
        ],
    )

    print(
        "MODEL_CALLS_PER_WINDOW =",
        contract[
            "task_model_contract"
        ][
            "full_task_model_invocations_per_window"
        ],
    )

    print(
        "HISTORICAL_DECISION =",
        contract[
            "historical_task_decision_contract"
        ][
            "function"
        ],
    )

    print(
        "HISTORICAL_PREDICTION_BIAS =",
        contract[
            "historical_task_decision_contract"
        ][
            "prediction_bias"
        ],
    )

    print(
        "OOD_THRESHOLD =",
        contract[
            "ood_runtime_contract"
        ][
            "threshold"
        ],
    )

    print(
        "SUPPORTED_HARD_CAUSES =",
        contract[
            "integrity_runtime_contract"
        ][
            "supported_v1_hard_cause_mask"
        ],
    )

    print(
        "MODEL_FORWARD_EXECUTED = False"
    )

    print(
        "SCIENTIFIC_SELECTION_REOPENED = False"
    )


if __name__ == "__main__":
    main()
