from __future__ import annotations

import json
import struct
import subprocess
from copy import deepcopy
from hashlib import sha256
from pathlib import Path


ROOT = Path(
    __file__
).resolve().parents[2]


EXPECTED_PRE_CONTRACT_HEAD = (
    "c36a60aed60766162fb7cd3755c1f5040d9a072c"
)

EMBEDDED_PATH_COMMIT = (
    "c36a60aed60766162fb7cd3755c1f5040d9a072c"
)

HOST_RESOURCE_COMMIT = (
    "d97403737804eeaeeecd009b4407949b52fe6d48"
)

REFERENCE_RUNTIME_COMMIT = (
    "4755a74fe558021576934674e338865a36df5b55"
)

RUNTIME_CONTRACT_COMMIT = (
    "c2b7ae52b163afb33c828218e5c76f0686ad391a"
)

OOD_OPERATING_POINT_COMMIT = (
    "fea9316d8510a5841baba48d273973e0267e4b28"
)

INTEGRITY_OPERATING_POINT_COMMIT = (
    "9ac878ea6a40e8c01a60e42e602a1fa9fc688d3b"
)


EMBEDDED_PATH_CONTRACT = (
    ROOT
    / "configs/embedded/"
      "embedded_reference_path_contract_v1.json"
)

ARCHAEOLOGY_RECEIPT = (
    ROOT
    / "data/manifests/"
      "embedded_target_archaeology_receipt_v1.json"
)

RUNTIME_CONTRACT = (
    ROOT
    / "configs/runtime/"
      "runtime_integration_contract_v1.json"
)

HISTORICAL_DECISION = (
    ROOT
    / "src/imu_reliability/baseline/"
      "historical_decision.py"
)

PY_RUNTIME_DECISION = (
    ROOT
    / "src/imu_reliability/runtime/"
      "decision.py"
)

OUTPUT = (
    ROOT
    / "configs/embedded/"
      "portable_c_runtime_semantic_contract_v1.json"
)


PLANNED_C_FILES = (
    ROOT
    / "embedded/reference_runtime/include/"
      "imu_reliability_runtime.h",

    ROOT
    / "embedded/reference_runtime/src/"
      "imu_reliability_runtime.c",

    ROOT
    / "embedded/reference_runtime/tests/"
      "test_imu_reliability_runtime.c",

    ROOT
    / "tests/"
      "test_portable_c_runtime_parity_v1.py",
)


EXPECTED_RAW_HASHES = {
    EMBEDDED_PATH_CONTRACT:
        "175059822fa16314e5117fa56557280aec831ed8b1c551cee1163e627d1d9d4f",

    ARCHAEOLOGY_RECEIPT:
        "14b10131c11f88d94f93dc09597d07ff94b6c94668168f822e6d39a8fe27c2df",

    RUNTIME_CONTRACT:
        "332beb6b99c73f6c4c153bcc21a05ab38e42516d1505c2c4f5f28f6ee5b3cf11",

    HISTORICAL_DECISION:
        "4badaf73460402447ac5c4253017db15de07964d7182f098a4d335f1670ed9ab",

    PY_RUNTIME_DECISION:
        "00391737a5f2d167ded6e302031b2a354baf2eeb41ee3bc49a1f055e3a40e384",
}


EMBEDDED_PATH_CONTENT_SHA256 = (
    "eacbc717d36ff12dd6b2873c5d1bfae5"
    "9d73abd9175c142ef824ad14ea34bcec"
)

ARCHAEOLOGY_CONTENT_SHA256 = (
    "e1d151d9837eedf1f4bc6aa71df6a166"
    "9e3d865b826fd6c9cf98706619286da7"
)

RUNTIME_CONTRACT_CONTENT_SHA256 = (
    "ffacdf7303738208d280f2f21f0d26fc"
    "7856a8dcf0946e34d88f133412467ca3"
)

OOD_THRESHOLD = 0.00914505124092102
HISTORICAL_BIAS = 0.9

OOD_THRESHOLD_F32_BITS = 0x3C15D520
HISTORICAL_BIAS_F32_BITS = 0x3F666666


def raw_hash(
    p: Path,
) -> str:
    return sha256(
        p.read_bytes()
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


def canonical_existing_content(
    p: Path,
) -> str:
    data = json.loads(
        p.read_text()
    )

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
            f"Canonical hash mismatch: {p}"
        )

    return stored


def git(
    *args: str,
) -> str:
    return subprocess.check_output(
        [
            "/usr/bin/git",
            *args,
        ],
        cwd=ROOT,
        text=True,
    ).strip()


def f32_bits(
    value: float,
) -> int:
    return struct.unpack(
        "<I",
        struct.pack(
            "<f",
            value,
        ),
    )[0]


def f32_value(
    value: float,
) -> float:
    return struct.unpack(
        "<f",
        struct.pack(
            "<f",
            value,
        ),
    )[0]


def verify_git_anchors() -> None:
    if git(
        "rev-parse",
        "HEAD",
    ) != EXPECTED_PRE_CONTRACT_HEAD:
        raise RuntimeError(
            "HEAD changed before portable-C semantic contract freeze"
        )

    expected = {
        "embedded-reference-path-contract-v1^{commit}":
            EMBEDDED_PATH_COMMIT,

        "runtime-resource-overhead-result-v1^{commit}":
            HOST_RESOURCE_COMMIT,

        "runtime-reference-implementation-v1^{commit}":
            REFERENCE_RUNTIME_COMMIT,

        "runtime-integration-contract-v1^{commit}":
            RUNTIME_CONTRACT_COMMIT,

        "ood-operating-point-v1^{commit}":
            OOD_OPERATING_POINT_COMMIT,

        "integrity-operating-point-v1^{commit}":
            INTEGRITY_OPERATING_POINT_COMMIT,
    }

    for ref, expected_commit in expected.items():
        observed = git(
            "rev-parse",
            ref,
        )

        if observed != expected_commit:
            raise RuntimeError(
                f"Frozen ref moved: {ref}"
            )


def verify_frozen_inputs() -> tuple[dict, dict, dict]:
    for p, expected in EXPECTED_RAW_HASHES.items():
        if not p.is_file():
            raise RuntimeError(
                f"Frozen input absent: {p}"
            )

        if raw_hash(
            p
        ) != expected:
            raise RuntimeError(
                f"Frozen input bytes changed: {p}"
            )

    embedded = json.loads(
        EMBEDDED_PATH_CONTRACT.read_text()
    )

    archaeology = json.loads(
        ARCHAEOLOGY_RECEIPT.read_text()
    )

    runtime = json.loads(
        RUNTIME_CONTRACT.read_text()
    )

    if (
        canonical_existing_content(
            EMBEDDED_PATH_CONTRACT
        )
        != EMBEDDED_PATH_CONTENT_SHA256
    ):
        raise RuntimeError(
            "Embedded-path contract content changed"
        )

    if (
        canonical_existing_content(
            ARCHAEOLOGY_RECEIPT
        )
        != ARCHAEOLOGY_CONTENT_SHA256
    ):
        raise RuntimeError(
            "Archaeology receipt content changed"
        )

    if (
        canonical_existing_content(
            RUNTIME_CONTRACT
        )
        != RUNTIME_CONTRACT_CONTENT_SHA256
    ):
        raise RuntimeError(
            "Runtime integration contract content changed"
        )

    if (
        embedded[
            "prospective_reference_path"
        ][
            "required"
        ]
        is not True
    ):
        raise RuntimeError(
            "Prospective embedded path no longer required"
        )

    if (
        embedded[
            "historical_recovery_decision"
        ][
            "exact_historical_deployed_firmware_claim_allowed"
        ]
        is not False
    ):
        raise RuntimeError(
            "Historical deployment claim boundary changed"
        )

    observations = archaeology[
        "observations"
    ]

    for key in (
        "protected_run_onnx_count",
        "protected_run_ioc_count",
        "protected_run_embedded_file_count",
        "cube_project_marker_count",
        "strong_stm32_firmware_file_count",
        "model_to_mcu_generated_file_count",
        "stm32_source_symbol_hit_count",
        "protected_400ms_export_candidate_count",
    ):
        if observations[
            key
        ] != 0:
            raise RuntimeError(
                f"Historical embedded evidence changed: {key}"
            )

    return (
        embedded,
        archaeology,
        runtime,
    )


def verify_constants() -> None:
    if f32_bits(
        OOD_THRESHOLD
    ) != OOD_THRESHOLD_F32_BITS:
        raise RuntimeError(
            "OOD threshold float32 bits changed"
        )

    if f32_value(
        OOD_THRESHOLD
    ) != OOD_THRESHOLD:
        raise RuntimeError(
            "OOD threshold is no longer exactly float32"
        )

    if f32_bits(
        HISTORICAL_BIAS
    ) != HISTORICAL_BIAS_F32_BITS:
        raise RuntimeError(
            "Historical bias float32 bits changed"
        )


def verify_implementation_absent() -> None:
    for p in PLANNED_C_FILES:
        if p.exists():
            raise RuntimeError(
                f"Portable-C implementation already exists: {p}"
            )


def build_contract() -> dict:
    (
        embedded,
        archaeology,
        runtime,
    ) = verify_frozen_inputs()

    verify_git_anchors()
    verify_constants()
    verify_implementation_absent()

    payload = {
        "contract_id":
            "PORTABLE_C_RUNTIME_SEMANTIC_CONTRACT_V1",

        "status":
            "frozen_before_portable_c_source_implementation",

        "lineage": {
            "implementation_label":
                "prospective_embedded_reference_implementation",

            "intended_target_family":
                "STM32F722",

            "exact_historical_deployment":
                False,

            "exact_historical_firmware_recovered":
                False,

            "exact_historical_400ms_export_recovered":
                False,

            "source_embedded_path_contract_tag":
                "embedded-reference-path-contract-v1",

            "source_embedded_path_contract_commit":
                EMBEDDED_PATH_COMMIT,

            "source_embedded_path_contract_raw_sha256":
                EXPECTED_RAW_HASHES[
                    EMBEDDED_PATH_CONTRACT
                ],

            "source_embedded_path_contract_content_sha256":
                EMBEDDED_PATH_CONTENT_SHA256,

            "source_archaeology_receipt_raw_sha256":
                EXPECTED_RAW_HASHES[
                    ARCHAEOLOGY_RECEIPT
                ],

            "source_archaeology_receipt_content_sha256":
                ARCHAEOLOGY_CONTENT_SHA256,
        },

        "scope": {
            "component":
                "portable_post_logit_reliability_decision_core",

            "model_inference_included":
                False,

            "model_export_included":
                False,

            "feature_vector_input_included":
                False,

            "raw_sensor_integrity_qualification_included":
                False,

            "stm32_hal_integration_included":
                False,

            "heap_allocation_allowed":
                False,

            "filesystem_io_allowed":
                False,

            "network_io_allowed":
                False,

            "global_mutable_state_allowed":
                False,

            "host_compiled_semantic_validation_allowed":
                True,
        },

        "planned_source_files": {
            "header":
                "embedded/reference_runtime/include/"
                "imu_reliability_runtime.h",

            "implementation":
                "embedded/reference_runtime/src/"
                "imu_reliability_runtime.c",

            "native_c_tests":
                "embedded/reference_runtime/tests/"
                "test_imu_reliability_runtime.c",

            "python_parity_tests":
                "tests/test_portable_c_runtime_parity_v1.py",
        },

        "language_contract": {
            "language":
                "ISO C",

            "minimum_standard":
                "C11",

            "required_standard_headers": [
                "math.h",
                "stdint.h",
            ],

            "dynamic_allocation":
                False,

            "exceptions":
                False,

            "threads":
                False,
        },

        "public_api": {
            "function_name":
                "ir_decide_from_logits",

            "function_signature":
                (
                    "ir_status_t ir_decide_from_logits("
                    "float logit_activity, "
                    "float logit_falling, "
                    "uint32_t hard_cause_mask, "
                    "uint32_t suspect_mask, "
                    "ir_decision_t *out)"
                ),

            "inputs": {
                "logit_activity":
                    "IEEE-754 binary32 task logit for Activity/class 0",

                "logit_falling":
                    "IEEE-754 binary32 task logit for Falling/class 1",

                "hard_cause_mask":
                    (
                        "already-qualified hard-cause mask supplied by "
                        "upstream integrity qualification"
                    ),

                "suspect_mask":
                    (
                        "opaque diagnostic suspect bitmask; "
                        "must not change primary trust state"
                    ),
            },

            "output_struct": {
                "task_prediction":
                    "uint8_t",

                "trust_state":
                    "ir_trust_state_t",

                "integrity_cause_mask":
                    "uint32_t",

                "suspect_mask":
                    "uint32_t",

                "ood_margin":
                    "float",

                "ood_threshold":
                    "float",
            },

            "successful_decision_always_returns_task_prediction":
                True,

            "function_invokes_task_model":
                False,

            "function_uses_feature_vector":
                False,
        },

        "enum_contract": {
            "task_classes": {
                "IR_CLASS_ACTIVITY":
                    0,

                "IR_CLASS_FALLING":
                    1,
            },

            "trust_states": {
                "IR_TRUST_VALID":
                    0,

                "IR_TRUST_OOD_UNKNOWN":
                    1,

                "IR_TRUST_INTEGRITY_ALERT":
                    2,
            },

            "statuses": {
                "IR_STATUS_OK":
                    0,

                "IR_STATUS_NULL_OUTPUT":
                    1,

                "IR_STATUS_NONFINITE_LOGIT":
                    2,

                "IR_STATUS_UNSUPPORTED_HARD_CAUSE":
                    3,
            },
        },

        "integrity_mask_contract": {
            "IR_CAUSE_NONE":
                0,

            "IR_CAUSE_FRAME_GAP":
                1,

            "IR_SUPPORTED_HARD_CAUSE_MASK":
                1,

            "frame_gap_bit":
                0,

            "frame_gap_input_is_already_hard_qualified":
                True,

            "portable_c_core_may_qualify_raw_counter_evidence":
                False,

            "any_hard_cause_bit_outside_supported_mask":
                "IR_STATUS_UNSUPPORTED_HARD_CAUSE",

            "unsupported_bits_may_be_silently_dropped":
                False,

            "unsupported_bits_may_be_promoted":
                False,

            "channel_freeze_enters_hard_mask":
                False,

            "timing_observation_enters_hard_mask":
                False,
        },

        "suspect_contract": {
            "representation":
                "opaque_uint32_passthrough",

            "changes_primary_trust_state":
                False,

            "returned_unchanged_on_success":
                True,
        },

        "numeric_contract": {
            "input_logit_type":
                "IEEE-754 binary32",

            "historical_prediction_bias_decimal":
                HISTORICAL_BIAS,

            "historical_prediction_bias_float32_bits":
                "0x3f666666",

            "ood_threshold_decimal":
                OOD_THRESHOLD,

            "ood_threshold_float32_bits":
                "0x3c15d520",

            "ood_threshold_exactly_representable_in_binary32":
                True,

            "ood_margin_type":
                "IEEE-754 binary32",

            "ood_margin_operation":
                "fabsf(logit_activity - logit_falling)",

            "finite_logit_precondition":
                True,
        },

        "historical_task_decision_contract": {
            "semantic_source":
                "frozen historical binary decision rule",

            "activity_class":
                0,

            "falling_class":
                1,

            "binary_equivalent_rule":
                (
                    "Falling iff P(Falling) > 0.9; "
                    "Activity otherwise"
                ),

            "probability_computation":
                (
                    "stable float32 binary softmax using expf after "
                    "subtracting max(logit_activity, logit_falling)"
                ),

            "comparison_operator":
                "strict_greater_than",

            "threshold":
                HISTORICAL_BIAS,

            "threshold_float32_bits":
                "0x3f666666",

            "uncertain_argmax_falling_may_still_return_activity":
                True,

            "tie_returns_activity":
                True,

            "plain_argmax_may_replace_historical_rule":
                False,
        },

        "ood_contract": {
            "method":
                "top_two_logit_margin",

            "binary_score":
                "fabsf(logit_activity - logit_falling)",

            "threshold":
                OOD_THRESHOLD,

            "threshold_float32_bits":
                "0x3c15d520",

            "unknown_condition":
                "ood_margin < threshold",

            "accepted_condition":
                "ood_margin >= threshold",

            "equality_at_threshold_accepted":
                True,

            "feature_vector_used":
                False,

            "additional_model_forward_required":
                False,
        },

        "decision_precedence": [
            {
                "priority":
                    1,

                "condition":
                    (
                        "hard_cause_mask contains one or more supported "
                        "qualified hard-cause bits"
                    ),

                "trust_state":
                    "IR_TRUST_INTEGRITY_ALERT",
            },
            {
                "priority":
                    2,

                "condition":
                    "ood_margin < frozen threshold",

                "trust_state":
                    "IR_TRUST_OOD_UNKNOWN",
            },
            {
                "priority":
                    3,

                "condition":
                    "otherwise",

                "trust_state":
                    "IR_TRUST_VALID",
            },
        ],

        "error_contract": {
            "null_output":
                "IR_STATUS_NULL_OUTPUT",

            "nonfinite_logit":
                "IR_STATUS_NONFINITE_LOGIT",

            "unsupported_hard_cause_bit":
                "IR_STATUS_UNSUPPORTED_HARD_CAUSE",

            "errors_are_trust_states":
                False,

            "output_on_non_ok_status":
                "must_remain_unmodified",
        },

        "predeclared_semantic_cases": [
            {
                "id":
                    "VALID_ACTIVITY_CONFIDENT",

                "logits":
                    [1.0, 0.0],

                "hard_cause_mask":
                    0,

                "expected_task_prediction":
                    0,

                "expected_trust_state":
                    "IR_TRUST_VALID",
            },
            {
                "id":
                    "OOD_EQUAL_LOGITS",

                "logits":
                    [0.0, 0.0],

                "hard_cause_mask":
                    0,

                "expected_task_prediction":
                    0,

                "expected_trust_state":
                    "IR_TRUST_OOD_UNKNOWN",
            },
            {
                "id":
                    "HISTORICAL_RULE_NOT_ARGMAX",

                "logits":
                    [0.0, 2.0],

                "hard_cause_mask":
                    0,

                "expected_task_prediction":
                    0,

                "expected_trust_state":
                    "IR_TRUST_VALID",
            },
            {
                "id":
                    "CONFIDENT_FALLING",

                "logits":
                    [0.0, 3.0],

                "hard_cause_mask":
                    0,

                "expected_task_prediction":
                    1,

                "expected_trust_state":
                    "IR_TRUST_VALID",
            },
            {
                "id":
                    "OOD_THRESHOLD_EQUALITY",

                "logits":
                    [0.0, OOD_THRESHOLD],

                "hard_cause_mask":
                    0,

                "expected_task_prediction":
                    0,

                "expected_trust_state":
                    "IR_TRUST_VALID",

                "expected_ood_margin":
                    OOD_THRESHOLD,
            },
            {
                "id":
                    "INTEGRITY_PRECEDES_OOD",

                "logits":
                    [0.0, 0.0],

                "hard_cause_mask":
                    1,

                "expected_task_prediction":
                    0,

                "expected_trust_state":
                    "IR_TRUST_INTEGRITY_ALERT",
            },
        ],

        "future_parity_validation_contract": {
            "native_c_unit_tests_required":
                True,

            "python_reference_parity_required":
                True,

            "frozen_python_reference_function":
                "imu_reliability.runtime.decide_from_logits",

            "checkpoint_required_for_parity":
                False,

            "dataset_required_for_parity":
                False,

            "synthetic_float32_logits_only":
                True,

            "must_test_threshold_equality":
                True,

            "must_test_float32_value_immediately_below_ood_threshold":
                True,

            "must_test_float32_value_immediately_above_ood_threshold":
                True,

            "must_test_historical_non_argmax_case":
                True,

            "must_test_integrity_precedence":
                True,

            "must_test_suspect_passthrough":
                True,

            "must_test_unsupported_hard_bit_error":
                True,

            "must_test_nonfinite_error":
                True,

            "must_test_output_unmodified_on_error":
                True,
        },

        "upstream_model_contract": {
            "portable_c_core_calls_model":
                False,

            "logits_must_come_from_exactly_one_task_model_forward":
                True,

            "second_task_model_forward_allowed":
                False,

            "feature_vector_needed":
                False,

            "model_export_or_translation_deferred":
                True,
        },

        "claim_boundary": {
            "portable_c_semantic_parity_claim_allowed_after_tests":
                True,

            "historical_firmware_claim_allowed":
                False,

            "historical_embedded_model_claim_allowed":
                False,

            "stm32_latency_claim_allowed":
                False,

            "stm32_cycles_claim_allowed":
                False,

            "stm32_flash_claim_allowed":
                False,

            "stm32_ram_claim_allowed":
                False,

            "stm32_energy_claim_allowed":
                False,

            "host_native_c_timing_may_be_relabelled_stm32_timing":
                False,
        },

        "scientific_boundary": {
            "ood_threshold_may_change":
                False,

            "ood_method_may_change":
                False,

            "historical_prediction_bias_may_change":
                False,

            "integrity_operating_point_may_change":
                False,

            "protected_final_test_may_be_reopened":
                False,

            "host_resource_benchmark_may_be_rerun_for_tuning":
                False,

            "classifier_bypass_allowed":
                False,

            "second_task_model_forward_allowed":
                False,
        },

        "freeze_boundary": {
            "c_header_created":
                False,

            "c_source_created":
                False,

            "native_c_tests_created":
                False,

            "python_c_parity_tests_created":
                False,

            "c_compiler_invoked":
                False,

            "arm_toolchain_installed":
                False,

            "checkpoint_deserialized":
                False,

            "model_forward_executed":
                False,

            "protected_dataset_opened":
                False,

            "stm32_hardware_measured":
                False,
        },
    }

    if (
        runtime[
            "ood_runtime_contract"
        ][
            "threshold"
        ]
        != OOD_THRESHOLD
    ):
        raise RuntimeError(
            "Runtime OOD threshold mismatch"
        )

    if (
        runtime[
            "historical_task_decision_contract"
        ][
            "prediction_bias"
        ]
        != HISTORICAL_BIAS
    ):
        raise RuntimeError(
            "Runtime historical bias mismatch"
        )

    if (
        runtime[
            "task_model_contract"
        ][
            "full_task_model_invocations_per_window"
        ]
        != 1
    ):
        raise RuntimeError(
            "Runtime one-forward invariant changed"
        )

    if (
        embedded[
            "prospective_reference_path"
        ][
            "lineage_label"
        ]
        != "prospective_embedded_reference_implementation"
    ):
        raise RuntimeError(
            "Prospective lineage changed"
        )

    payload[
        "content_sha256"
    ] = canonical_digest(
        payload
    )

    return payload


def main() -> None:
    if OUTPUT.exists():
        raise RuntimeError(
            "Refusing to overwrite portable-C semantic contract"
        )

    contract = build_contract()

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
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
        "PORTABLE_C_RUNTIME_SEMANTIC_CONTRACT_V1_WRITTEN = True"
    )

    print(
        "CONTRACT_CONTENT_SHA256 =",
        contract[
            "content_sha256"
        ],
    )

    print(
        "PUBLIC_API =",
        contract[
            "public_api"
        ][
            "function_signature"
        ],
    )

    print(
        "OOD_THRESHOLD =",
        contract[
            "ood_contract"
        ][
            "threshold"
        ],
    )

    print(
        "OOD_THRESHOLD_FLOAT32_BITS =",
        contract[
            "ood_contract"
        ][
            "threshold_float32_bits"
        ],
    )

    print(
        "HISTORICAL_PREDICTION_BIAS =",
        contract[
            "historical_task_decision_contract"
        ][
            "threshold"
        ],
    )

    print(
        "HISTORICAL_BIAS_FLOAT32_BITS =",
        contract[
            "historical_task_decision_contract"
        ][
            "threshold_float32_bits"
        ],
    )

    print(
        "SUPPORTED_HARD_CAUSE_MASK =",
        contract[
            "integrity_mask_contract"
        ][
            "IR_SUPPORTED_HARD_CAUSE_MASK"
        ],
    )

    print(
        "C_IMPLEMENTATION_CREATED = False"
    )

    print(
        "MODEL_EXPORT_CREATED = False"
    )

    print(
        "MODEL_FORWARD_EXECUTED = False"
    )

    print(
        "STM32_PERFORMANCE_CLAIMED = False"
    )


if __name__ == "__main__":
    main()
