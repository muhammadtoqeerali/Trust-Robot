from __future__ import annotations

import json
import os
import shutil
import subprocess
from copy import deepcopy
from hashlib import sha256
from pathlib import Path


ROOT = Path(
    __file__
).resolve().parents[2]


EXPECTED_HEAD = (
    "d97403737804eeaeeecd009b4407949b52fe6d48"
)

HOST_RESULT_COMMIT = (
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

BASELINE_COMMIT = (
    "d6fe744b292139d18fd4dee37c96066bcf2d38c6"
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

HISTORICAL_DECISION = (
    ROOT
    / "src/imu_reliability/baseline/"
      "historical_decision.py"
)

CHECKPOINT = Path(
    "/mnt/hdd16T/protechto/checkpoints/CNN/400ms/"
    "2025-02-25_12_24_47/best-checkpoint.ckpt"
)

PROTECTED_RESULT_DIR = Path(
    "/mnt/hdd16T/protechto/results/Backup/"
    "CNN/400ms/2025-02-25_12_24_47"
)

HISTORICAL_HOME = Path(
    "/mnt/hdd16T/ToqeerHomeBackup/toqeer"
)

PROTECHTO_ROOT = Path(
    "/mnt/hdd16T/protechto"
)


RECEIPT = (
    ROOT
    / "data/manifests/"
      "embedded_target_archaeology_receipt_v1.json"
)

CONTRACT = (
    ROOT
    / "configs/embedded/"
      "embedded_reference_path_contract_v1.json"
)


EXPECTED_RAW_HASHES = {
    RUNTIME_CONTRACT:
        "332beb6b99c73f6c4c153bcc21a05ab38e42516d1505c2c4f5f28f6ee5b3cf11",

    MODEL_SOURCE:
        "def71b3cebc0649c0d909e4ffd5dc04f177fcb795ff6ebfd13f90e214c67581d",

    HISTORICAL_DECISION:
        "4badaf73460402447ac5c4253017db15de07964d7182f098a4d335f1670ed9ab",

    CHECKPOINT:
        "ee7c0079bfb8555bff45c3077cc24eaa4373c57729045d92a831a1d7a3ea9bb1",
}


RUNTIME_CONTRACT_CONTENT_SHA256 = (
    "ffacdf7303738208d280f2f21f0d26fc"
    "7856a8dcf0946e34d88f133412467ca3"
)

OOD_THRESHOLD = (
    0.00914505124092102
)

HISTORICAL_PREDICTION_BIAS = (
    0.9
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


def verify_git_anchors() -> None:
    if git(
        "rev-parse",
        "HEAD",
    ) != EXPECTED_HEAD:
        raise RuntimeError(
            "HEAD changed before embedded path contract freeze"
        )

    expected = {
        "runtime-resource-overhead-result-v1^{commit}":
            HOST_RESULT_COMMIT,

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


def verify_frozen_inputs() -> dict:
    for path, expected in EXPECTED_RAW_HASHES.items():
        if not path.is_file():
            raise RuntimeError(
                f"Frozen input absent: {path}"
            )

        observed = raw_hash(
            path
        )

        if observed != expected:
            raise RuntimeError(
                f"Frozen input changed: {path}"
            )

    runtime = json.loads(
        RUNTIME_CONTRACT.read_text()
    )

    payload = deepcopy(
        runtime
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
            "Frozen runtime contract content changed"
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
            "One-forward contract changed"
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
            "Historical decision bias changed"
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
            "Frozen OOD threshold changed"
        )

    return runtime


def protected_result_inventory() -> list[dict]:
    if not PROTECTED_RESULT_DIR.is_dir():
        raise RuntimeError(
            "Protected historical result directory is absent"
        )

    records = []

    for path in PROTECTED_RESULT_DIR.rglob(
        "*"
    ):
        if not path.is_file():
            continue

        records.append(
            {
                "relative_path":
                    str(
                        path.relative_to(
                            PROTECTED_RESULT_DIR
                        )
                    ),

                "suffix":
                    path.suffix.lower(),

                "bytes":
                    path.stat().st_size,

                "raw_sha256":
                    raw_hash(
                        path
                    ),
            }
        )

    records.sort(
        key=lambda row: row[
            "relative_path"
        ]
    )

    return records


def scan_historical_home() -> dict:
    excluded = {
        ".git",
        ".cache",
        "__pycache__",
        "node_modules",
        ".venv",
        "venv",
        "site-packages",
        "dist-packages",
        "wandb",
        "lightning_logs",
        "ThirdPartyDatasets",
        "data",
        "results",
        "checkpoints",
        "external",
    }

    cube_project_markers = []

    strong_firmware_files = []

    generated_model_files = []

    stm32_source_symbol_hits = []

    strong_names = {
        "startup_stm32f722xx.s",
        "stm32f722xx.h",
        "stm32f7xx_hal_conf.h",
        "stm32f7xx_it.c",
        "stm32f7xx_it.h",
        "system_stm32f7xx.c",
    }

    generated_terms = (
        "network.c",
        "network.h",
        "network_data.c",
        "network_data.h",
        "ai_network",
        "ai_model",
        "model_data.cc",
        "model_data.c",
        "model_data.h",
    )

    source_suffixes = {
        ".c",
        ".h",
        ".cc",
        ".cpp",
        ".hpp",
        ".s",
        ".asm",
        ".ld",
    }

    symbol_terms = (
        "HAL_Init(",
        "SystemClock_Config(",
        "stm32f7xx_hal.h",
        "STM32F722",
        "STM32F7",
        "DWT->CYCCNT",
        "CoreDebug->DEMCR",
        "SCB_EnableICache",
        "SCB_EnableDCache",
        "ai_network_",
        "ai_network",
        "arm_convolve",
        "arm_fully_connected",
        "arm_nn",
        "CMSIS_NN",
        "tflite::MicroInterpreter",
    )

    if not HISTORICAL_HOME.is_dir():
        raise RuntimeError(
            "Historical Toqeer home is absent"
        )

    for current, dirs, files in os.walk(
        HISTORICAL_HOME
    ):
        dirs[:] = [
            name
            for name in dirs
            if name not in excluded
        ]

        current_path = Path(
            current
        )

        lowered_current = str(
            current_path
        ).lower()

        for filename in files:
            path = (
                current_path
                / filename
            )

            lowered = (
                filename
                .lower()
            )

            suffix = (
                path
                .suffix
                .lower()
            )

            if (
                suffix == ".ioc"
                or filename in {
                    ".project",
                    ".cproject",
                    "STM32Make.make",
                }
            ):
                cube_project_markers.append(
                    str(path)
                )

            reasons = []

            if lowered in strong_names:
                reasons.append(
                    "STM32F7_STRONG_FILENAME"
                )

            if (
                lowered == "main.c"
                and (
                    "/core/src"
                    in lowered_current
                    or "stm32"
                    in lowered_current
                    or "cube"
                    in lowered_current
                    or "firmware"
                    in lowered_current
                )
            ):
                reasons.append(
                    "LIKELY_STM32_MAIN"
                )

            if (
                suffix == ".ld"
                and (
                    "stm32"
                    in lowered
                    or "f722"
                    in lowered
                    or "flash"
                    in lowered
                )
            ):
                reasons.append(
                    "STM32_LINKER_SCRIPT"
                )

            if reasons:
                strong_firmware_files.append(
                    {
                        "path":
                            str(path),

                        "reasons":
                            reasons,
                    }
                )

            if any(
                term in lowered
                for term in generated_terms
            ):
                generated_model_files.append(
                    str(path)
                )

            if (
                suffix
                not in source_suffixes
            ):
                continue

            try:
                if (
                    path.stat().st_size
                    > 3_000_000
                ):
                    continue

                lines = path.read_text(
                    encoding="utf-8",
                    errors="ignore",
                ).splitlines()

            except (
                PermissionError,
                OSError,
            ):
                continue

            for lineno, line in enumerate(
                lines,
                start=1,
            ):
                matched = [
                    term
                    for term in symbol_terms
                    if term.lower()
                    in line.lower()
                ]

                if not matched:
                    continue

                stm32_source_symbol_hits.append(
                    {
                        "path":
                            str(path),

                        "line":
                            lineno,

                        "matched":
                            matched,

                        "text":
                            line.strip()[:250],
                    }
                )

    return {
        "cube_project_markers":
            sorted(
                cube_project_markers
            ),

        "strong_stm32_firmware_files":
            sorted(
                strong_firmware_files,
                key=lambda row: row[
                    "path"
                ],
            ),

        "model_to_mcu_generated_files":
            sorted(
                generated_model_files
            ),

        "stm32_source_symbol_hits":
            sorted(
                stm32_source_symbol_hits,
                key=lambda row: (
                    row[
                        "path"
                    ],
                    row[
                        "line"
                    ],
                ),
            ),
    }


def scan_400ms_exports() -> list[dict]:
    roots = [
        PROTECHTO_ROOT,
        HISTORICAL_HOME,
    ]

    excluded = {
        ".git",
        ".cache",
        "__pycache__",
        "node_modules",
        ".venv",
        "venv",
        "site-packages",
        "dist-packages",
        "wandb",
        "ThirdPartyDatasets",
        "data",
        "lightning_logs",
    }

    records = []

    seen = set()

    for root in roots:
        if not root.is_dir():
            continue

        for current, dirs, files in os.walk(
            root
        ):
            dirs[:] = [
                name
                for name in dirs
                if name not in excluded
            ]

            current_path = Path(
                current
            )

            for filename in files:
                path = (
                    current_path
                    / filename
                )

                lowered_path = (
                    str(path)
                    .lower()
                )

                lowered_name = (
                    filename
                    .lower()
                )

                is_export = (
                    path.suffix.lower()
                    in {
                        ".onnx",
                        ".tflite",
                        ".tflm",
                    }
                    or "quantized"
                    in lowered_name
                )

                if not is_export:
                    continue

                if (
                    "400ms"
                    not in lowered_path
                    and "2025-02-25_12_24_47"
                    not in lowered_path
                ):
                    continue

                try:
                    resolved = str(
                        path.resolve()
                    )
                except OSError:
                    resolved = str(
                        path
                    )

                if resolved in seen:
                    continue

                seen.add(
                    resolved
                )

                records.append(
                    {
                        "path":
                            resolved,

                        "suffix":
                            path.suffix.lower(),

                        "bytes":
                            path.stat().st_size,
                    }
                )

    records.sort(
        key=lambda row: row[
            "path"
        ]
    )

    return records


def exact_timestamp_path_hits() -> list[str]:
    needle = (
        "2025-02-25_12_24_47"
    )

    excluded = {
        ".git",
        ".cache",
        "__pycache__",
        "node_modules",
        ".venv",
        "venv",
        "site-packages",
        "dist-packages",
        "wandb",
    }

    hits = set()

    for current, dirs, files in os.walk(
        HISTORICAL_HOME
    ):
        dirs[:] = [
            name
            for name in dirs
            if name not in excluded
        ]

        current_path = Path(
            current
        )

        if needle in str(
            current_path
        ):
            hits.add(
                str(
                    current_path
                )
            )

        for filename in files:
            path = (
                current_path
                / filename
            )

            if (
                needle in filename
                or needle in str(path)
            ):
                hits.add(
                    str(path)
                )

    return sorted(
        hits
    )


def tool_snapshot() -> dict:
    tools = (
        "arm-none-eabi-gcc",
        "arm-none-eabi-g++",
        "arm-none-eabi-size",
        "arm-none-eabi-objcopy",
        "arm-none-eabi-objdump",
        "openocd",
        "st-flash",
        "STM32_Programmer_CLI",
        "STM32CubeProgrammer_CLI",
        "STM32CubeMX",
        "stm32cubemx",
        "make",
    )

    return {
        tool:
            shutil.which(
                tool
            )
        for tool in tools
    }


def collect_archaeology() -> dict:
    protected = (
        protected_result_inventory()
    )

    historical = (
        scan_historical_home()
    )

    exports = (
        scan_400ms_exports()
    )

    timestamp_hits = (
        exact_timestamp_path_hits()
    )

    embedded_suffixes = {
        ".c",
        ".h",
        ".cc",
        ".cpp",
        ".hpp",
        ".s",
        ".asm",
        ".ld",
        ".ioc",
        ".elf",
        ".axf",
        ".map",
        ".hex",
    }

    protected_onnx = [
        row
        for row in protected
        if row[
            "suffix"
        ] == ".onnx"
    ]

    protected_ioc = [
        row
        for row in protected
        if row[
            "suffix"
        ] == ".ioc"
    ]

    protected_embedded = [
        row
        for row in protected
        if row[
            "suffix"
        ] in embedded_suffixes
    ]

    evidence = {
        "archaeology_id":
            "EMBEDDED_TARGET_ARCHAEOLOGY_V1",

        "status":
            "read_only_search_complete",

        "search_boundary": {
            "exact_protected_result_directory":
                str(
                    PROTECTED_RESULT_DIR
                ),

            "historical_home_root":
                str(
                    HISTORICAL_HOME
                ),

            "protechto_root":
                str(
                    PROTECHTO_ROOT
                ),

            "claim_scope":
                (
                    "available workstation evidence only; "
                    "absence from searched evidence is not proof that "
                    "historical firmware never existed"
                ),
        },

        "protected_run_inventory":
            protected,

        "observations": {
            "protected_run_file_count":
                len(
                    protected
                ),

            "protected_run_onnx_count":
                len(
                    protected_onnx
                ),

            "protected_run_ioc_count":
                len(
                    protected_ioc
                ),

            "protected_run_embedded_file_count":
                len(
                    protected_embedded
                ),

            "exact_timestamp_path_hit_count_in_historical_home":
                len(
                    timestamp_hits
                ),

            "cube_project_marker_count":
                len(
                    historical[
                        "cube_project_markers"
                    ]
                ),

            "strong_stm32_firmware_file_count":
                len(
                    historical[
                        "strong_stm32_firmware_files"
                    ]
                ),

            "model_to_mcu_generated_file_count":
                len(
                    historical[
                        "model_to_mcu_generated_files"
                    ]
                ),

            "stm32_source_symbol_hit_count":
                len(
                    historical[
                        "stm32_source_symbol_hits"
                    ]
                ),

            "protected_400ms_export_candidate_count":
                len(
                    exports
                ),
        },

        "timestamp_path_hits":
            timestamp_hits,

        "cube_project_markers":
            historical[
                "cube_project_markers"
            ],

        "strong_stm32_firmware_files":
            historical[
                "strong_stm32_firmware_files"
            ],

        "model_to_mcu_generated_files":
            historical[
                "model_to_mcu_generated_files"
            ],

        "stm32_source_symbol_hits":
            historical[
                "stm32_source_symbol_hits"
            ],

        "protected_400ms_export_candidates":
            exports,

        "tool_snapshot":
            tool_snapshot(),

        "read_only_boundary": {
            "torch_imported":
                False,

            "checkpoint_deserialized":
                False,

            "model_forward_executed":
                False,

            "protected_dataset_opened":
                False,

            "calibration_dataset_opened":
                False,

            "final_test_dataset_opened":
                False,

            "host_resource_benchmark_rerun":
                False,

            "scientific_operating_point_modified":
                False,

            "source_file_modified_by_archaeology":
                False,

            "stm32_performance_claimed":
                False,
        },
    }

    evidence[
        "content_sha256"
    ] = canonical_digest(
        evidence
    )

    return evidence


def validate_archaeology(
    evidence: dict,
) -> None:
    observed = evidence[
        "observations"
    ]

    expected_zero = (
        "protected_run_onnx_count",
        "protected_run_ioc_count",
        "protected_run_embedded_file_count",
        "exact_timestamp_path_hit_count_in_historical_home",
        "cube_project_marker_count",
        "strong_stm32_firmware_file_count",
        "model_to_mcu_generated_file_count",
        "stm32_source_symbol_hit_count",
        "protected_400ms_export_candidate_count",
    )

    if (
        observed[
            "protected_run_file_count"
        ]
        != 8
    ):
        raise RuntimeError(
            "Protected historical result inventory changed"
        )

    for key in expected_zero:
        if observed[
            key
        ] != 0:
            raise RuntimeError(
                f"Historical embedded evidence appeared: "
                f"{key}={observed[key]}"
            )


def build_contract(
    evidence: dict,
    runtime: dict,
) -> dict:
    payload = {
        "contract_id":
            "EMBEDDED_REFERENCE_PATH_CONTRACT_V1",

        "status":
            "frozen_before_prospective_embedded_reference_implementation",

        "evidence_receipt": {
            "path":
                str(
                    RECEIPT.relative_to(
                        ROOT
                    )
                ),

            "archaeology_id":
                evidence[
                    "archaeology_id"
                ],

            "content_sha256":
                evidence[
                    "content_sha256"
                ],
        },

        "frozen_software_lineage": {
            "host_resource_result_tag":
                "runtime-resource-overhead-result-v1",

            "host_resource_result_commit":
                HOST_RESULT_COMMIT,

            "reference_runtime_tag":
                "runtime-reference-implementation-v1",

            "reference_runtime_commit":
                REFERENCE_RUNTIME_COMMIT,

            "runtime_integration_contract_tag":
                "runtime-integration-contract-v1",

            "runtime_integration_contract_commit":
                RUNTIME_CONTRACT_COMMIT,

            "runtime_integration_contract_raw_sha256":
                EXPECTED_RAW_HASHES[
                    RUNTIME_CONTRACT
                ],

            "runtime_integration_contract_content_sha256":
                RUNTIME_CONTRACT_CONTENT_SHA256,

            "baseline_tag":
                "baseline-date2025-cnn400-v1",

            "baseline_commit":
                BASELINE_COMMIT,

            "protected_checkpoint_path":
                str(
                    CHECKPOINT
                ),

            "protected_checkpoint_sha256":
                EXPECTED_RAW_HASHES[
                    CHECKPOINT
                ],

            "protected_model_source_raw_sha256":
                EXPECTED_RAW_HASHES[
                    MODEL_SOURCE
                ],

            "historical_decision_source_raw_sha256":
                EXPECTED_RAW_HASHES[
                    HISTORICAL_DECISION
                ],
        },

        "historical_recovery_decision": {
            "exact_historical_stm32_firmware_recovered":
                False,

            "exact_historical_cube_project_recovered":
                False,

            "exact_historical_400ms_model_export_recovered":
                False,

            "historical_mcu_generated_model_code_recovered":
                False,

            "historical_deployment_build_artifact_recovered":
                False,

            "exact_historical_deployed_firmware_claim_allowed":
                False,

            "exact_historical_embedded_model_claim_allowed":
                False,

            "absence_interpretation":
                (
                    "No exact historical embedded target path was recovered "
                    "from the searched workstation evidence. "
                    "This does not prove such firmware never existed."
                ),
        },

        "prospective_reference_path": {
            "required":
                True,

            "lineage_label":
                "prospective_embedded_reference_implementation",

            "intended_target_family":
                "STM32F722",

            "may_be_described_as_exact_historical_deployment":
                False,

            "may_be_described_as_exact_deployed_firmware":
                False,

            "may_be_described_as_reference_implementation":
                True,

            "must_preserve_frozen_runtime_semantics":
                True,

            "must_be_validated_against_frozen_reference_runtime":
                True,

            "model_export_or_translation_requires_separate_frozen_protocol":
                True,

            "target_resource_measurement_requires_separate_frozen_protocol":
                True,
        },

        "runtime_semantics_to_preserve": {
            "window_shape":
                [
                    1,
                    40,
                    9,
                ],

            "full_task_model_invocations_per_window":
                runtime[
                    "task_model_contract"
                ][
                    "full_task_model_invocations_per_window"
                ],

            "second_full_task_model_forward_allowed":
                runtime[
                    "task_model_contract"
                ][
                    "second_full_task_model_forward_allowed"
                ],

            "historical_task_decision_function":
                runtime[
                    "historical_task_decision_contract"
                ][
                    "function"
                ],

            "historical_prediction_bias":
                runtime[
                    "historical_task_decision_contract"
                ][
                    "prediction_bias"
                ],

            "task_prediction_always_returned":
                runtime[
                    "historical_task_decision_contract"
                ][
                    "task_prediction_always_returned"
                ],

            "ood_method":
                runtime[
                    "ood_runtime_contract"
                ][
                    "method"
                ],

            "ood_threshold":
                runtime[
                    "ood_runtime_contract"
                ][
                    "threshold"
                ],

            "ood_feature_vector_used":
                runtime[
                    "ood_runtime_contract"
                ][
                    "feature_vector_used"
                ],

            "supported_v1_hard_cause_mask":
                runtime[
                    "integrity_runtime_contract"
                ][
                    "supported_v1_hard_cause_mask"
                ],

            "decision_precedence":
                [
                    row[
                        "trust_state"
                    ]
                    for row in runtime[
                        "decision_precedence"
                    ]
                ],
        },

        "first_embedded_implementation_stage": {
            "scope":
                (
                    "portable C reliability decision core implementing "
                    "post-logit task decision, frozen OOD gate, qualified "
                    "integrity hard-cause precedence, and task prediction return"
                ),

            "full_cnn_export_included":
                False,

            "full_cnn_translation_included":
                False,

            "stm32_hal_integration_included":
                False,

            "hardware_flash_included":
                False,

            "target_cycle_measurement_included":
                False,

            "host_compiled_semantic_parity_allowed":
                True,

            "synthetic_deterministic_test_vectors_only":
                True,

            "protected_dataset_required":
                False,
        },

        "future_model_embedding_boundary": {
            "protected_checkpoint_is_surviving_model_source":
                True,

            "surviving_400ms_embedded_export_available":
                False,

            "new_model_export_must_be_labeled_prospective":
                True,

            "new_model_export_requires_numerical_parity_validation":
                True,

            "model_conversion_may_not_change_scientific_operating_points":
                True,
        },

        "resource_claim_boundary": {
            "stm32_latency_currently_claimable":
                False,

            "stm32_cycles_currently_claimable":
                False,

            "stm32_flash_currently_claimable":
                False,

            "stm32_ram_currently_claimable":
                False,

            "stm32_energy_currently_claimable":
                False,

            "host_resource_result_may_be_relabelled_as_stm32_result":
                False,

            "real_target_evidence_required_before_stm32_claim":
                True,
        },

        "scientific_boundary": {
            "ood_threshold_may_change":
                False,

            "ood_method_may_change":
                False,

            "integrity_operating_point_may_change":
                False,

            "protected_final_test_may_be_reopened":
                False,

            "host_resource_benchmark_may_be_rerun_for_tuning":
                False,

            "classifier_bypass_allowed":
                False,

            "second_full_task_model_forward_allowed":
                False,
        },

        "freeze_boundary": {
            "embedded_c_source_created":
                False,

            "new_model_export_created":
                False,

            "arm_toolchain_installed":
                False,

            "firmware_built":
                False,

            "stm32_hardware_measured":
                False,

            "model_forward_executed":
                False,

            "checkpoint_deserialized":
                False,

            "protected_dataset_opened":
                False,
        },
    }

    payload[
        "content_sha256"
    ] = canonical_digest(
        payload
    )

    return payload


def main() -> None:
    verify_git_anchors()

    runtime = verify_frozen_inputs()

    if RECEIPT.exists():
        raise RuntimeError(
            "Refusing to overwrite archaeology receipt"
        )

    if CONTRACT.exists():
        raise RuntimeError(
            "Refusing to overwrite embedded path contract"
        )

    evidence = collect_archaeology()

    validate_archaeology(
        evidence
    )

    contract = build_contract(
        evidence,
        runtime,
    )

    RECEIPT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    CONTRACT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    RECEIPT.write_text(
        json.dumps(
            evidence,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )

    CONTRACT.write_text(
        json.dumps(
            contract,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )

    observations = evidence[
        "observations"
    ]

    print(
        "EMBEDDED_TARGET_ARCHAEOLOGY_RECEIPT_V1_WRITTEN = True"
    )

    print(
        "EMBEDDED_REFERENCE_PATH_CONTRACT_V1_WRITTEN = True"
    )

    print(
        "ARCHAEOLOGY_CONTENT_SHA256 =",
        evidence[
            "content_sha256"
        ],
    )

    print(
        "CONTRACT_CONTENT_SHA256 =",
        contract[
            "content_sha256"
        ],
    )

    for key, value in observations.items():
        print(
            key,
            "=",
            value,
        )

    print(
        "EXACT_HISTORICAL_STM32_PATH_RECOVERED = False"
    )

    print(
        "PROSPECTIVE_REFERENCE_IMPLEMENTATION_REQUIRED = True"
    )

    print(
        "EXACT_HISTORICAL_DEPLOYMENT_CLAIM_ALLOWED = False"
    )

    print(
        "EMBEDDED_C_CREATED = False"
    )

    print(
        "NEW_MODEL_EXPORT_CREATED = False"
    )

    print(
        "MODEL_FORWARD_EXECUTED = False"
    )

    print(
        "STM32_PERFORMANCE_CLAIMED = False"
    )


if __name__ == "__main__":
    main()
