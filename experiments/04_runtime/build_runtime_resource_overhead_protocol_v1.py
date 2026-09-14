from __future__ import annotations

import json
import platform
import subprocess
from copy import deepcopy
from hashlib import sha256
from pathlib import Path


ROOT = Path(
    __file__
).resolve().parents[2]


EXPECTED_PRE_PROTOCOL_HEAD = (
    "4755a74fe558021576934674e338865a36df5b55"
)

REFERENCE_RUNTIME_COMMIT = (
    "4755a74fe558021576934674e338865a36df5b55"
)

RUNTIME_CONTRACT_COMMIT = (
    "c2b7ae52b163afb33c828218e5c76f0686ad391a"
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


RUNTIME_INIT = (
    ROOT
    / "src/imu_reliability/runtime/"
      "__init__.py"
)

DECISION_SOURCE = (
    ROOT
    / "src/imu_reliability/runtime/"
      "decision.py"
)

RELIABILITY_SOURCE = (
    ROOT
    / "src/imu_reliability/runtime/"
      "reliability.py"
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

MODEL_SOURCE = (
    ROOT
    / "src/imu_reliability/baseline/"
      "date2025_cnn400.py"
)

OUTPUT = (
    ROOT
    / "configs/runtime/"
      "runtime_resource_overhead_protocol_v1.json"
)

BENCHMARK = (
    ROOT
    / "experiments/04_runtime/"
      "benchmark_runtime_resource_overhead_v1.py"
)

BENCHMARK_TEST = (
    ROOT
    / "tests/"
      "test_runtime_resource_overhead_benchmark_v1.py"
)

RESULT = (
    ROOT
    / "results/raw/"
      "runtime_resource_overhead_v1_candidate.json"
)

RECEIPT = (
    ROOT
    / "data/manifests/"
      "runtime_resource_overhead_result_receipt_v1.json"
)


EXPECTED_SOURCE_HASHES = {
    RUNTIME_INIT:
        "f8b125ffb9e1c217bc2eb0c2aac197e64ca8cfc47d6f31ddf92068af575ef3e0",

    DECISION_SOURCE:
        "00391737a5f2d167ded6e302031b2a354baf2eeb41ee3bc49a1f055e3a40e384",

    RELIABILITY_SOURCE:
        "aa8fe189301c4dd2b67f501872d060a29e8e5e8e5cc518590e028a79068eda7b",

    RUNTIME_CONTRACT:
        "332beb6b99c73f6c4c153bcc21a05ab38e42516d1505c2c4f5f28f6ee5b3cf11",

    HISTORICAL_DECISION:
        "4badaf73460402447ac5c4253017db15de07964d7182f098a4d335f1670ed9ab",

    MODEL_SOURCE:
        "def71b3cebc0649c0d909e4ffd5dc04f177fcb795ff6ebfd13f90e214c67581d",
}


RUNTIME_CONTRACT_CONTENT_SHA256 = (
    "ffacdf7303738208d280f2f21f0d26fc"
    "7856a8dcf0946e34d88f133412467ca3"
)

CHECKPOINT_PATH = (
    "/mnt/hdd16T/protechto/checkpoints/CNN/400ms/"
    "2025-02-25_12_24_47/best-checkpoint.ckpt"
)

CHECKPOINT_SHA256 = (
    "ee7c0079bfb8555bff45c3077cc24eaa"
    "4373c57729045d92a831a1d7a3ea9bb1"
)

OOD_THRESHOLD = (
    0.00914505124092102
)

HISTORICAL_PREDICTION_BIAS = (
    0.9
)

WARMUP_ITERATIONS = (
    500
)

MEASURED_ITERATIONS_PER_BLOCK = (
    1000
)

MEASUREMENT_BLOCKS = (
    7
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


def verify_runtime_contract_content():
    data = json.loads(
        RUNTIME_CONTRACT.read_text()
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

    if not (
        stored
        == computed
        == RUNTIME_CONTRACT_CONTENT_SHA256
    ):
        raise RuntimeError(
            "Frozen runtime integration contract changed"
        )

    if (
        data[
            "task_model_contract"
        ][
            "full_task_model_invocations_per_window"
        ]
        != 1
    ):
        raise RuntimeError(
            "One-forward runtime invariant changed"
        )

    if (
        data[
            "ood_runtime_contract"
        ][
            "threshold"
        ]
        != OOD_THRESHOLD
    ):
        raise RuntimeError(
            "Frozen OOD threshold changed"
        )

    if (
        data[
            "historical_task_decision_contract"
        ][
            "prediction_bias"
        ]
        != HISTORICAL_PREDICTION_BIAS
    ):
        raise RuntimeError(
            "Historical prediction bias changed"
        )


def verify_anchors():
    if git(
        "rev-parse",
        "HEAD",
    ) != EXPECTED_PRE_PROTOCOL_HEAD:
        raise RuntimeError(
            "HEAD changed before resource protocol freeze"
        )

    refs = {
        "runtime-reference-implementation-v1^{commit}":
            REFERENCE_RUNTIME_COMMIT,

        "runtime-integration-contract-v1^{commit}":
            RUNTIME_CONTRACT_COMMIT,

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
                f"Frozen ref moved: {ref}"
            )

    for ref in (
        "runtime-reference-implementation-v1",
        "runtime-integration-contract-v1",
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

    for path, expected in EXPECTED_SOURCE_HASHES.items():
        if not path.is_file():
            raise RuntimeError(
                f"Frozen source absent: {path}"
            )

        if raw_hash(
            path
        ) != expected:
            raise RuntimeError(
                f"Frozen source changed: {path}"
            )

    verify_runtime_contract_content()


def verify_measurement_not_started():
    for path in (
        BENCHMARK,
        BENCHMARK_TEST,
        RESULT,
        RECEIPT,
    ):
        if path.exists():
            raise RuntimeError(
                f"Resource measurement artifact already exists: {path}"
            )


def build_protocol():
    verify_anchors()
    verify_measurement_not_started()

    payload = {
        "protocol_id":
            "RUNTIME_RESOURCE_OVERHEAD_PROTOCOL_V1",

        "status":
            "frozen_before_reference_host_resource_measurement",

        "purpose":
            (
                "Quantify incremental engineering overhead of the frozen "
                "reference reliability runtime without reopening scientific "
                "selection and without making target-MCU claims."
            ),

        "source_anchors": {
            "reference_runtime": {
                "tag":
                    "runtime-reference-implementation-v1",

                "tag_commit":
                    REFERENCE_RUNTIME_COMMIT,

                "runtime_init_raw_sha256":
                    EXPECTED_SOURCE_HASHES[
                        RUNTIME_INIT
                    ],

                "decision_raw_sha256":
                    EXPECTED_SOURCE_HASHES[
                        DECISION_SOURCE
                    ],

                "reliability_raw_sha256":
                    EXPECTED_SOURCE_HASHES[
                        RELIABILITY_SOURCE
                    ],
            },

            "runtime_integration_contract": {
                "tag":
                    "runtime-integration-contract-v1",

                "tag_commit":
                    RUNTIME_CONTRACT_COMMIT,

                "raw_sha256":
                    EXPECTED_SOURCE_HASHES[
                        RUNTIME_CONTRACT
                    ],

                "content_sha256":
                    RUNTIME_CONTRACT_CONTENT_SHA256,
            },

            "protected_baseline": {
                "tag":
                    "baseline-date2025-cnn400-v1",

                "tag_commit":
                    BASELINE_COMMIT,

                "model_source_raw_sha256":
                    EXPECTED_SOURCE_HASHES[
                        MODEL_SOURCE
                    ],

                "historical_decision_raw_sha256":
                    EXPECTED_SOURCE_HASHES[
                        HISTORICAL_DECISION
                    ],
            },

            "checkpoint": {
                "path":
                    CHECKPOINT_PATH,

                "sha256":
                    CHECKPOINT_SHA256,

                "loading_time_included_in_latency_measurement":
                    False,
            },

            "ood_operating_point": {
                "tag":
                    "ood-operating-point-v1",

                "tag_commit":
                    OOD_OPERATING_POINT_COMMIT,

                "threshold":
                    OOD_THRESHOLD,
            },

            "integrity_operating_point": {
                "tag":
                    "integrity-operating-point-v1",

                "tag_commit":
                    INTEGRITY_OPERATING_POINT_COMMIT,

                "supported_v1_hard_causes":
                    [
                        "FRAME_GAP",
                    ],
            },
        },

        "measurement_scope": {
            "scope":
                "reference_host_engineering_measurement",

            "device":
                "CPU",

            "batch_size":
                1,

            "window_shape":
                [
                    1,
                    40,
                    9,
                ],

            "protected_dataset_used":
                False,

            "calibration_dataset_used":
                False,

            "final_test_dataset_used":
                False,

            "external_domain_shift_dataset_used":
                False,

            "input_source":
                "deterministic_synthetic_only",

            "scientific_selection_allowed":
                False,

            "ood_threshold_may_change":
                False,

            "integrity_operating_point_may_change":
                False,
        },

        "synthetic_input_contract": {
            "primary_pattern":
                "deterministic_linspace",

            "construction":
                (
                    "torch.linspace(-1.0, 1.0, steps=360, "
                    "dtype=torch.float32).reshape(1,40,9)"
                ),

            "random_input_used":
                False,

            "protected_sensor_sample_used":
                False,

            "input_values_used_for_accuracy_or_selection":
                False,
        },

        "execution_environment_contract": {
            "torch_device":
                "cpu",

            "torch_num_threads":
                1,

            "torch_num_interop_threads":
                1,

            "model_eval_mode":
                True,

            "timed_model_calls_under_inference_mode":
                True,

            "garbage_collection_policy":
                (
                    "disable_gc_inside_each_timed_block_and_restore_after"
                ),

            "wall_clock":
                "time.perf_counter_ns",

            "environment_metadata_to_record": [
                "python_version",
                "torch_version",
                "numpy_version",
                "platform",
                "machine",
                "processor",
                "cpu_count",
                "torch_num_threads",
                "torch_num_interop_threads",
            ],
        },

        "latency_protocol": {
            "warmup_iterations":
                WARMUP_ITERATIONS,

            "measurement_blocks":
                MEASUREMENT_BLOCKS,

            "measured_iterations_per_block":
                MEASURED_ITERATIONS_PER_BLOCK,

            "total_measured_calls_per_variant":
                (
                    MEASUREMENT_BLOCKS
                    * MEASURED_ITERATIONS_PER_BLOCK
                ),

            "variants": {
                "task_only_reference": {
                    "definition":
                        (
                            "exactly one model(window) call followed by "
                            "historical decision_from_logits(logits)"
                        ),

                    "full_task_model_calls_per_iteration":
                        1,

                    "reliability_wrapper_called":
                        False,
                },

                "integrated_reliability": {
                    "definition":
                        (
                            "run_reliability_window(model, window, "
                            "empty_integrity_assessment)"
                        ),

                    "full_task_model_calls_per_iteration":
                        1,

                    "reliability_wrapper_called":
                        True,
                },

                "post_logit_valid": {
                    "definition":
                        (
                            "decide_from_logits on fixed logits producing VALID "
                            "with an empty IntegrityAssessment"
                        ),

                    "full_task_model_calls_per_iteration":
                        0,
                },

                "post_logit_ood_unknown": {
                    "definition":
                        (
                            "decide_from_logits on equal fixed logits producing "
                            "OOD_UNKNOWN with an empty IntegrityAssessment"
                        ),

                    "full_task_model_calls_per_iteration":
                        0,
                },

                "post_logit_integrity_alert": {
                    "definition":
                        (
                            "decide_from_logits on fixed logits with a "
                            "preconstructed qualified FRAME_GAP assessment"
                        ),

                    "full_task_model_calls_per_iteration":
                        0,
                },
            },

            "block_order":
                (
                    "alternate task-only-first and integrated-first across "
                    "successive blocks to reduce fixed ordering bias"
                ),

            "per_iteration_latency_recorded":
                True,

            "reported_latency_statistics": [
                "count",
                "minimum_ns",
                "median_ns",
                "mean_ns",
                "p95_ns",
                "p99_ns",
                "maximum_ns",
            ],

            "primary_incremental_latency_definition":
                (
                    "median_integrated_reliability_ns "
                    "- median_task_only_reference_ns"
                ),

            "primary_relative_overhead_definition":
                (
                    "primary_incremental_latency_ns "
                    "/ median_task_only_reference_ns"
                ),

            "negative_measured_increment":
                (
                    "retain_as_observed_and_interpret_as_measurement_noise; "
                    "do_not_clamp_to_zero"
                ),
        },

        "memory_protocol": {
            "scope":
                "reference_host_only",

            "python_allocator_measurement":
                "tracemalloc",

            "measure_post_logit_variants":
                True,

            "measure_end_to_end_variants":
                True,

            "reported_python_allocation_fields": [
                "current_bytes",
                "peak_bytes",
            ],

            "host_process_peak_rss":
                True,

            "host_process_peak_rss_method":
                (
                    "resource.getrusage(resource.RUSAGE_SELF).ru_maxrss "
                    "recorded with platform/unit metadata"
                ),

            "model_parameter_memory_counted_as_incremental_reliability_overhead":
                False,

            "checkpoint_loading_peak_memory_counted_as_runtime_overhead":
                False,

            "python_allocation_or_rss_may_be_called_stm32_ram":
                False,
        },

        "static_footprint_protocol": {
            "report_runtime_source_raw_bytes":
                True,

            "files": [
                "src/imu_reliability/runtime/__init__.py",
                "src/imu_reliability/runtime/decision.py",
                "src/imu_reliability/runtime/reliability.py",
            ],

            "python_source_bytes_may_be_called_embedded_flash":
                False,

            "python_source_bytes_may_be_called_mcu_code_size":
                False,
        },

        "functional_invariants_rechecked_during_benchmark": {
            "one_full_task_model_call_per_end_to_end_iteration":
                True,

            "historical_prediction_bias":
                HISTORICAL_PREDICTION_BIAS,

            "ood_threshold":
                OOD_THRESHOLD,

            "ood_score":
                "abs(logit_0 - logit_1)",

            "feature_vector_used_by_ood":
                False,

            "second_task_forward_used":
                False,

            "task_prediction_always_returned":
                True,

            "integrity_precedes_ood":
                True,
        },

        "claim_boundary": {
            "allowed_after_successful_reference_measurement": [
                "reference_host_task_only_latency",
                "reference_host_integrated_runtime_latency",
                "reference_host_incremental_latency",
                "reference_host_relative_latency_overhead",
                "reference_host_python_allocation_evidence",
                "reference_host_process_peak_rss_observation",
                "runtime_python_source_byte_count",
            ],

            "not_allowed_from_this_protocol": [
                "stm32f722_latency",
                "stm32f722_cycle_count",
                "stm32f722_flash_overhead",
                "stm32f722_ram_overhead",
                "stm32f722_energy_overhead",
                "deployed_firmware_latency",
                "deployed_firmware_memory",
                "exact_embedded_real_time_deadline_claim",
            ],

            "target_mcu_measurement_required_before_embedded_claims":
                True,
        },

        "result_contract": {
            "candidate_result_path":
                "results/raw/runtime_resource_overhead_v1_candidate.json",

            "result_must_record_environment":
                True,

            "result_must_record_all_protocol_statistics":
                True,

            "result_must_record_runtime_source_hashes":
                True,

            "result_must_record_checkpoint_hash":
                True,

            "result_may_modify_runtime_algorithm":
                False,

            "result_may_modify_scientific_operating_points":
                False,
        },

        "freeze_boundary": {
            "benchmark_implementation_created":
                False,

            "benchmark_executed":
                False,

            "torch_imported_by_protocol_builder":
                False,

            "checkpoint_deserialized":
                False,

            "model_forward_executed":
                False,

            "dataset_array_opened":
                False,

            "final_test_output_recomputed":
                False,

            "final_test_evaluator_rerun":
                False,
        },

        "builder_environment_note": {
            "python_platform_string":
                platform.platform(),

            "environment_values_are_not_measurement_results":
                True,
        },
    }

    payload[
        "content_sha256"
    ] = canonical_digest(
        payload
    )

    return payload


def main():
    protocol = build_protocol()

    if OUTPUT.exists():
        raise RuntimeError(
            "Refusing to overwrite resource-overhead protocol"
        )

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
        "RUNTIME_RESOURCE_OVERHEAD_PROTOCOL_V1_WRITTEN = True"
    )

    print(
        "PROTOCOL_CONTENT_SHA256 =",
        protocol[
            "content_sha256"
        ],
    )

    print(
        "WARMUP_ITERATIONS =",
        protocol[
            "latency_protocol"
        ][
            "warmup_iterations"
        ],
    )

    print(
        "MEASUREMENT_BLOCKS =",
        protocol[
            "latency_protocol"
        ][
            "measurement_blocks"
        ],
    )

    print(
        "ITERATIONS_PER_BLOCK =",
        protocol[
            "latency_protocol"
        ][
            "measured_iterations_per_block"
        ],
    )

    print(
        "TOTAL_MEASURED_CALLS_PER_VARIANT =",
        protocol[
            "latency_protocol"
        ][
            "total_measured_calls_per_variant"
        ],
    )

    print(
        "PROTECTED_DATASET_USED = False"
    )

    print(
        "MODEL_FORWARD_EXECUTED = False"
    )

    print(
        "STM32_PERFORMANCE_CLAIMED = False"
    )


if __name__ == "__main__":
    main()
