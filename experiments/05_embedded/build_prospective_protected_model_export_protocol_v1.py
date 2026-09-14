from __future__ import annotations

import json
import subprocess
from copy import deepcopy
from hashlib import sha256
from pathlib import Path


ROOT = Path(
    __file__
).resolve().parents[2]


PRE_EXPORT_HEAD = (
    "3f0db77158cc59e4273f75b076fef53aa6b1f413"
)

PORTABLE_C_IMPLEMENTATION_COMMIT = (
    "3f0db77158cc59e4273f75b076fef53aa6b1f413"
)

PORTABLE_C_SEMANTIC_COMMIT = (
    "552e2255a812e73b2782b1f8d697a94f03a15752"
)

EMBEDDED_PATH_COMMIT = (
    "c36a60aed60766162fb7cd3755c1f5040d9a072c"
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

BASELINE_COMMIT = (
    "d6fe744b292139d18fd4dee37c96066bcf2d38c6"
)


PORTABLE_C_HEADER = (
    ROOT
    / "embedded/reference_runtime/include/"
      "imu_reliability_runtime.h"
)

PORTABLE_C_SOURCE = (
    ROOT
    / "embedded/reference_runtime/src/"
      "imu_reliability_runtime.c"
)

C_SEMANTIC_CONTRACT = (
    ROOT
    / "configs/embedded/"
      "portable_c_runtime_semantic_contract_v1.json"
)

EMBEDDED_PATH_CONTRACT = (
    ROOT
    / "configs/embedded/"
      "embedded_reference_path_contract_v1.json"
)

RUNTIME_CONTRACT = (
    ROOT
    / "configs/runtime/"
      "runtime_integration_contract_v1.json"
)

MODEL_SOURCE = (
    ROOT
    / "src/imu_reliability/baseline/"
      "date2025_cnn400.py"
)

V1B_LOADER = (
    ROOT
    / "experiments/03_ood/"
      "evaluate_ood_calibration_v1b.py"
)

CHECKPOINT = Path(
    "/mnt/hdd16T/protechto/checkpoints/CNN/400ms/"
    "2025-02-25_12_24_47/best-checkpoint.ckpt"
)


OUTPUT = (
    ROOT
    / "configs/embedded/"
      "prospective_protected_model_export_protocol_v1.json"
)


FUTURE_OUTPUTS = (
    ROOT
    / "experiments/05_embedded/"
      "export_protected_model_onnx_v1.py",

    ROOT
    / "tests/"
      "test_protected_model_onnx_export_v1.py",

    ROOT
    / "artifacts/embedded/prospective/"
      "date2025_cnn400_fp32_v1.onnx",

    ROOT
    / "results/raw/"
      "prospective_model_export_v1_candidate.json",

    ROOT
    / "data/manifests/"
      "prospective_model_export_result_receipt_v1.json",
)


EXPECTED_RAW_HASHES = {
    PORTABLE_C_HEADER:
        "0162556076334f8ff1323788fd133a33a7e110daba41c7aaba12967fbe3d858e",

    PORTABLE_C_SOURCE:
        "1b7e7fd97f993bb63396a72912f5d5b8bc2b5bb68864e9c556db8dddf6617fa6",

    C_SEMANTIC_CONTRACT:
        "bfe2d56e998150b5109462ae81be5e788c9fed28b1a290a9ef3adbebe6dbd831",

    EMBEDDED_PATH_CONTRACT:
        "175059822fa16314e5117fa56557280aec831ed8b1c551cee1163e627d1d9d4f",

    RUNTIME_CONTRACT:
        "332beb6b99c73f6c4c153bcc21a05ab38e42516d1505c2c4f5f28f6ee5b3cf11",

    MODEL_SOURCE:
        "def71b3cebc0649c0d909e4ffd5dc04f177fcb795ff6ebfd13f90e214c67581d",

    V1B_LOADER:
        "6462829b7ffee3ca19dc25b7a605a3b7dd38ddf6bfb10a34ca8d098c0ae415df",

    CHECKPOINT:
        "ee7c0079bfb8555bff45c3077cc24eaa4373c57729045d92a831a1d7a3ea9bb1",
}


C_SEMANTIC_CONTENT_SHA256 = (
    "965765b678220d8297b4c930533570b3"
    "0fa43d2cc681e5fe91ca2431b009efda"
)

EMBEDDED_PATH_CONTENT_SHA256 = (
    "eacbc717d36ff12dd6b2873c5d1bfae5"
    "9d73abd9175c142ef824ad14ea34bcec"
)

RUNTIME_CONTRACT_CONTENT_SHA256 = (
    "ffacdf7303738208d280f2f21f0d26fc"
    "7856a8dcf0946e34d88f133412467ca3"
)


OOD_THRESHOLD = 0.00914505124092102
HISTORICAL_PREDICTION_BIAS = 0.9

ONNX_OPSET_VERSION = 13

PARITY_ATOL = 1.0e-5
PARITY_RTOL = 1.0e-5

MODULAR_VECTOR_COUNT = 64
STRUCTURED_VECTOR_COUNT = 4

TOTAL_PARITY_VECTOR_COUNT = (
    MODULAR_VECTOR_COUNT
    + STRUCTURED_VECTOR_COUNT
)


def raw_hash(
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


def canonical_existing(
    path: Path,
) -> str:
    data = json.loads(
        path.read_text()
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
            f"Canonical content mismatch: {path}"
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


def verify_git_anchors() -> None:
    if git(
        "rev-parse",
        "HEAD",
    ) != PRE_EXPORT_HEAD:
        raise RuntimeError(
            "HEAD changed before prospective export protocol freeze"
        )

    expected = {
        "portable-c-runtime-implementation-v1^{commit}":
            PORTABLE_C_IMPLEMENTATION_COMMIT,

        "portable-c-runtime-semantic-contract-v1^{commit}":
            PORTABLE_C_SEMANTIC_COMMIT,

        "embedded-reference-path-contract-v1^{commit}":
            EMBEDDED_PATH_COMMIT,

        "runtime-reference-implementation-v1^{commit}":
            REFERENCE_RUNTIME_COMMIT,

        "runtime-integration-contract-v1^{commit}":
            RUNTIME_CONTRACT_COMMIT,

        "ood-operating-point-v1^{commit}":
            OOD_OPERATING_POINT_COMMIT,

        "integrity-operating-point-v1^{commit}":
            INTEGRITY_OPERATING_POINT_COMMIT,

        "baseline-date2025-cnn400-v1^{commit}":
            BASELINE_COMMIT,
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
    for path, expected in EXPECTED_RAW_HASHES.items():
        if not path.is_file():
            raise RuntimeError(
                f"Frozen input missing: {path}"
            )

        observed = raw_hash(
            path
        )

        if observed != expected:
            raise RuntimeError(
                f"Frozen input changed: {path}"
            )

    c_semantic = json.loads(
        C_SEMANTIC_CONTRACT.read_text()
    )

    embedded = json.loads(
        EMBEDDED_PATH_CONTRACT.read_text()
    )

    runtime = json.loads(
        RUNTIME_CONTRACT.read_text()
    )

    if (
        canonical_existing(
            C_SEMANTIC_CONTRACT
        )
        != C_SEMANTIC_CONTENT_SHA256
    ):
        raise RuntimeError(
            "Portable-C semantic contract content changed"
        )

    if (
        canonical_existing(
            EMBEDDED_PATH_CONTRACT
        )
        != EMBEDDED_PATH_CONTENT_SHA256
    ):
        raise RuntimeError(
            "Embedded-path contract content changed"
        )

    if (
        canonical_existing(
            RUNTIME_CONTRACT
        )
        != RUNTIME_CONTRACT_CONTENT_SHA256
    ):
        raise RuntimeError(
            "Runtime integration contract content changed"
        )

    if (
        runtime[
            "ood_runtime_contract"
        ][
            "threshold"
        ]
        != OOD_THRESHOLD
    ):
        raise RuntimeError(
            "OOD threshold changed"
        )

    if (
        runtime[
            "historical_task_decision_contract"
        ][
            "prediction_bias"
        ]
        != HISTORICAL_PREDICTION_BIAS
    ):
        raise RuntimeError(
            "Historical task rule changed"
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
            "Prospective embedded lineage changed"
        )

    return (
        c_semantic,
        embedded,
        runtime,
    )


def verify_future_outputs_absent() -> None:
    for path in FUTURE_OUTPUTS:
        if path.exists():
            raise RuntimeError(
                f"Export output already exists: {path}"
            )


def build_protocol() -> dict:
    (
        c_semantic,
        embedded,
        runtime,
    ) = verify_frozen_inputs()

    verify_git_anchors()
    verify_future_outputs_absent()

    payload = {
        "protocol_id":
            "PROSPECTIVE_PROTECTED_MODEL_EXPORT_PROTOCOL_V1",

        "status":
            "frozen_before_checkpoint_deserialization_or_model_export",

        "lineage": {
            "artifact_label":
                "prospective_protected_model_export",

            "intended_target_family":
                "STM32F722",

            "exact_historical_deployment_artifact":
                False,

            "exact_historical_400ms_export_recovered":
                False,

            "source_checkpoint_is_surviving_historical_checkpoint":
                True,

            "source_checkpoint_path":
                str(
                    CHECKPOINT
                ),

            "source_checkpoint_sha256":
                EXPECTED_RAW_HASHES[
                    CHECKPOINT
                ],

            "source_model_raw_sha256":
                EXPECTED_RAW_HASHES[
                    MODEL_SOURCE
                ],

            "pinned_loader_raw_sha256":
                EXPECTED_RAW_HASHES[
                    V1B_LOADER
                ],

            "portable_c_runtime_tag":
                "portable-c-runtime-implementation-v1",

            "portable_c_runtime_commit":
                PORTABLE_C_IMPLEMENTATION_COMMIT,

            "embedded_path_tag":
                "embedded-reference-path-contract-v1",

            "embedded_path_commit":
                EMBEDDED_PATH_COMMIT,
        },

        "export_scope": {
            "format":
                "ONNX",

            "precision":
                "float32",

            "opset_version":
                ONNX_OPSET_VERSION,

            "exporter_family":
                "torch.onnx.export",

            "model_mode":
                "eval",

            "export_full_frozen_forward":
                True,

            "manual_layer_reimplementation_allowed":
                False,

            "parameter_retraining_allowed":
                False,

            "parameter_finetuning_allowed":
                False,

            "quantization_included":
                False,

            "quantization_deferred_to_separate_protocol":
                True,

            "dynamic_axes_allowed":
                False,

            "fixed_batch_size":
                1,

            "model_parameters_embedded_in_artifact":
                True,

            "constant_folding_allowed":
                True,

            "feature_output_included":
                False,

            "logits_only_output":
                True,

            "external_dataset_required":
                False,
        },

        "tensor_contract": {
            "input_name":
                "imu_window",

            "input_dtype":
                "float32",

            "input_shape":
                [
                    1,
                    40,
                    9,
                ],

            "output_name":
                "logits",

            "output_dtype":
                "float32",

            "output_shape":
                [
                    1,
                    2,
                ],

            "activity_logit_index":
                0,

            "falling_logit_index":
                1,
        },

        "future_export_artifacts": {
            "exporter_script":
                "experiments/05_embedded/"
                "export_protected_model_onnx_v1.py",

            "export_test":
                "tests/test_protected_model_onnx_export_v1.py",

            "onnx_artifact":
                "artifacts/embedded/prospective/"
                "date2025_cnn400_fp32_v1.onnx",

            "candidate_result":
                "results/raw/"
                "prospective_model_export_v1_candidate.json",

            "result_receipt":
                "data/manifests/"
                "prospective_model_export_result_receipt_v1.json",
        },

        "checkpoint_loading_contract": {
            "loader_source":
                "experiments/03_ood/"
                "evaluate_ood_calibration_v1b.py",

            "loader_raw_sha256":
                EXPECTED_RAW_HASHES[
                    V1B_LOADER
                ],

            "checkpoint_sha256_must_be_verified_before_deserialization":
                True,

            "direct_unpinned_torch_load_allowed":
                False,

            "legacy_compatibility_source_may_only_be_used_via_pinned_loader":
                True,

            "model_must_be_eval_mode":
                True,
        },

        "deterministic_parity_input_contract": {
            "protected_dataset_used":
                False,

            "calibration_dataset_used":
                False,

            "final_test_dataset_used":
                False,

            "external_recording_dataset_used":
                False,

            "structured_vector_count":
                STRUCTURED_VECTOR_COUNT,

            "structured_vectors": [
                "all_zero",
                "all_one",
                "all_minus_one",
                "linear_minus_one_to_plus_one",
            ],

            "modular_vector_count":
                MODULAR_VECTOR_COUNT,

            "modular_formula":
                (
                    "x[i,t,c] = "
                    "(((i*37 + t*17 + c*13) % 257) - 128) / 64"
                ),

            "modular_values_are_exact_binary_fractions":
                True,

            "total_vector_count":
                TOTAL_PARITY_VECTOR_COUNT,

            "window_shape":
                [
                    1,
                    40,
                    9,
                ],

            "batching_for_validation":
                "one_window_at_a_time",

            "no_random_generator_required":
                True,
        },

        "numerical_parity_contract": {
            "reference":
                "protected reconstructed PyTorch model from same checkpoint",

            "candidate":
                "prospective float32 ONNX export",

            "comparison_dtype":
                "float32",

            "absolute_tolerance":
                PARITY_ATOL,

            "relative_tolerance":
                PARITY_RTOL,

            "elementwise_acceptance":
                (
                    "abs(candidate-reference) <= "
                    "atol + rtol*abs(reference)"
                ),

            "all_logit_elements_must_pass":
                True,

            "record_max_absolute_error":
                True,

            "record_max_relative_error":
                True,

            "record_worst_vector_index":
                True,

            "tolerance_may_change_after_export_outputs_are_seen":
                False,
        },

        "decision_parity_contract": {
            "historical_task_prediction_exact_match_required":
                True,

            "historical_prediction_bias":
                HISTORICAL_PREDICTION_BIAS,

            "ood_method":
                "top_two_logit_margin",

            "ood_threshold":
                OOD_THRESHOLD,

            "ood_unknown_condition":
                "margin < threshold",

            "ood_threshold_equality_accepted":
                True,

            "ood_trust_state_exact_match_required":
                True,

            "decision_mismatch_tolerance":
                0,

            "decision_parity_may_not_be_repaired_by_threshold_change":
                True,

            "integrity_state_not_part_of_model_export_validation":
                True,

            "reason_integrity_state_not_part_of_export_validation":
                (
                    "integrity evidence is external to model graph and "
                    "already validated by frozen portable C runtime"
                ),
        },

        "graph_validation_contract": {
            "onnx_checker_required":
                True,

            "onnx_runtime_cpu_execution_required":
                True,

            "fixed_input_shape_required":
                [
                    1,
                    40,
                    9,
                ],

            "fixed_output_shape_required":
                [
                    1,
                    2,
                ],

            "single_graph_output_required":
                True,

            "graph_output_must_be_logits":
                True,

            "feature_output_forbidden":
                True,

            "dynamic_dimension_forbidden":
                True,

            "training_mode_operation_forbidden":
                True,

            "external_data_file_forbidden":
                True,
        },

        "single_forward_runtime_boundary": {
            "exported_model_represents_one_task_forward":
                True,

            "runtime_reliability_core_consumes_exported_logits":
                True,

            "second_model_forward_for_ood_forbidden":
                True,

            "feature_vector_for_ood_forbidden":
                True,
        },

        "failure_policy": {
            "failed_export_may_change_ood_threshold":
                False,

            "failed_export_may_change_historical_task_rule":
                False,

            "failed_export_may_change_integrity_operating_point":
                False,

            "failed_export_may_reopen_protected_final_test":
                False,

            "failed_parity_may_loosen_tolerance_after_outputs_seen":
                False,

            "failed_parity_requires_new_prospective_export_method_or_revision":
                True,

            "failed_export_artifact_may_be_called_validated":
                False,
        },

        "claim_boundary": {
            "validated_onnx_may_be_called_prospective_model_export":
                True,

            "validated_onnx_may_be_called_exact_historical_deployed_model":
                False,

            "validated_onnx_may_be_called_exact_historical_firmware":
                False,

            "onnx_validation_alone_proves_stm32_importability":
                False,

            "onnx_validation_alone_proves_stm32_numerical_parity":
                False,

            "onnx_validation_alone_proves_stm32_latency":
                False,

            "onnx_validation_alone_proves_stm32_flash":
                False,

            "onnx_validation_alone_proves_stm32_ram":
                False,

            "onnx_validation_alone_proves_stm32_energy":
                False,

            "downstream_embedded_toolchain_validation_required":
                True,
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

            "classifier_bypass_allowed":
                False,

            "second_task_forward_allowed":
                False,

            "protected_final_test_may_be_reopened":
                False,

            "host_resource_benchmark_may_be_rerun":
                False,

            "export_result_may_be_used_for_scientific_selection":
                False,
        },

        "freeze_boundary": {
            "checkpoint_deserialized":
                False,

            "model_instantiated":
                False,

            "model_forward_executed":
                False,

            "onnx_export_executed":
                False,

            "onnx_artifact_created":
                False,

            "onnxruntime_inference_executed":
                False,

            "protected_dataset_opened":
                False,

            "calibration_dataset_opened":
                False,

            "final_test_dataset_opened":
                False,

            "quantization_executed":
                False,

            "arm_toolchain_used":
                False,

            "stm32_hardware_measured":
                False,
        },
    }

    if (
        c_semantic[
            "ood_contract"
        ][
            "threshold"
        ]
        != OOD_THRESHOLD
    ):
        raise RuntimeError(
            "C semantic OOD threshold mismatch"
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
            "One-forward runtime contract changed"
        )

    if (
        embedded[
            "future_model_embedding_boundary"
        ][
            "new_model_export_must_be_labeled_prospective"
        ]
        is not True
    ):
        raise RuntimeError(
            "Prospective export lineage changed"
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
            "Refusing to overwrite prospective export protocol"
        )

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
        "PROSPECTIVE_PROTECTED_MODEL_EXPORT_PROTOCOL_V1_WRITTEN = True"
    )

    print(
        "PROTOCOL_CONTENT_SHA256 =",
        protocol[
            "content_sha256"
        ],
    )

    print(
        "FORMAT =",
        protocol[
            "export_scope"
        ][
            "format"
        ],
    )

    print(
        "PRECISION =",
        protocol[
            "export_scope"
        ][
            "precision"
        ],
    )

    print(
        "ONNX_OPSET_VERSION =",
        protocol[
            "export_scope"
        ][
            "opset_version"
        ],
    )

    print(
        "INPUT_SHAPE =",
        protocol[
            "tensor_contract"
        ][
            "input_shape"
        ],
    )

    print(
        "OUTPUT_SHAPE =",
        protocol[
            "tensor_contract"
        ][
            "output_shape"
        ],
    )

    print(
        "PARITY_VECTOR_COUNT =",
        protocol[
            "deterministic_parity_input_contract"
        ][
            "total_vector_count"
        ],
    )

    print(
        "ATOL =",
        protocol[
            "numerical_parity_contract"
        ][
            "absolute_tolerance"
        ],
    )

    print(
        "RTOL =",
        protocol[
            "numerical_parity_contract"
        ][
            "relative_tolerance"
        ],
    )

    print(
        "OOD_THRESHOLD =",
        protocol[
            "decision_parity_contract"
        ][
            "ood_threshold"
        ],
    )

    print(
        "CHECKPOINT_DESERIALIZED = False"
    )

    print(
        "MODEL_FORWARD_EXECUTED = False"
    )

    print(
        "ONNX_ARTIFACT_CREATED = False"
    )

    print(
        "QUANTIZATION_EXECUTED = False"
    )

    print(
        "STM32_PERFORMANCE_CLAIMED = False"
    )


if __name__ == "__main__":
    main()
