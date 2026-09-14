from __future__ import annotations

import json
import subprocess
from copy import deepcopy
from hashlib import sha256
from pathlib import Path


ROOT = Path(
    __file__
).resolve().parents[2]


PRE_LEDGER_HEAD = (
    "2d858320ba0122f483f759a50755a711c2c9ea78"
)

TOOLCHAIN_BLOCKER_COMMIT = (
    "2d858320ba0122f483f759a50755a711c2c9ea78"
)

ONNX_ENV_BLOCKER_COMMIT = (
    "ea2653fe08a6b684ad652e0a0ad8ff8191e2632b"
)

EXPORTER_COMMIT = (
    "4050f610bc037aa854a066af5ad935df8dd22b45"
)

EXPORT_PROTOCOL_COMMIT = (
    "7229081206d0b4cfe3249792282f0aa87abb9220"
)

PORTABLE_C_COMMIT = (
    "3f0db77158cc59e4273f75b076fef53aa6b1f413"
)

PORTABLE_C_SEMANTIC_COMMIT = (
    "552e2255a812e73b2782b1f8d697a94f03a15752"
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

BASELINE_COMMIT = (
    "d6fe744b292139d18fd4dee37c96066bcf2d38c6"
)


TOOLCHAIN_BLOCKER = (
    ROOT
    / "configs/embedded/"
      "prospective_embedded_build_toolchain_blocker_v1.json"
)

TOOLCHAIN_RECEIPT = (
    ROOT
    / "data/manifests/"
      "embedded_build_toolchain_archaeology_receipt_v1.json"
)

ONNX_ENV_CONTRACT = (
    ROOT
    / "configs/embedded/"
      "prospective_model_export_execution_environment_contract_v1.json"
)

ONNX_BLOCKER = (
    ROOT
    / "data/manifests/"
      "prospective_model_export_dependency_blocker_v1.json"
)

EXPORT_PROTOCOL = (
    ROOT
    / "configs/embedded/"
      "prospective_protected_model_export_protocol_v1.json"
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

HOST_RESOURCE_RESULT = (
    ROOT
    / "results/raw/"
      "runtime_resource_overhead_v1_candidate.json"
)

LEDGER = (
    ROOT
    / "configs/embedded/"
      "embedded_evidence_convergence_ledger_v1.json"
)


EXPECTED_RAW_HASHES = {
    TOOLCHAIN_BLOCKER:
        "b8ee7a7e1d568c3d4ea0b46cb0c5434a73edeafaae1d72410e36422d7e1d4c58",

    TOOLCHAIN_RECEIPT:
        "3b180cfc64f08ef2965e4be4f3ece41989892922c421d922a557d571dc205c1b",

    ONNX_ENV_CONTRACT:
        "3f9f5f80886e09f8c04535c9fc253c8f98cd4cd6221d35e6229719503266a957",

    ONNX_BLOCKER:
        "33c07b0f2a5bc1422ce849fa680934c0d7a77bcfa2dfdbe59a4872ee8f67ee29",

    EXPORT_PROTOCOL:
        "5574278d42584f03ec39274c287c48329b2dbbad49f25e77024d1b17ad94fdf3",

    C_SEMANTIC_CONTRACT:
        "bfe2d56e998150b5109462ae81be5e788c9fed28b1a290a9ef3adbebe6dbd831",

    EMBEDDED_PATH_CONTRACT:
        "175059822fa16314e5117fa56557280aec831ed8b1c551cee1163e627d1d9d4f",

    RUNTIME_CONTRACT:
        "332beb6b99c73f6c4c153bcc21a05ab38e42516d1505c2c4f5f28f6ee5b3cf11",

    HOST_RESOURCE_RESULT:
        "1fe4ed729b4ae23d4104616e1450fb4143d7ea51cdedf0fce70aeb025b18b71e",
}


EXPECTED_CONTENT_HASHES = {
    TOOLCHAIN_BLOCKER:
        "18786157fb29cf00859310e7d89b7289f1c8a2308984e60fb209b0f8b89f3c34",

    TOOLCHAIN_RECEIPT:
        "06bfb916d67d8e6ac69b9b30c659a417c748d0f9970144a5f7855e880e245c8c",

    ONNX_ENV_CONTRACT:
        "331bbfba1105c9075adb3206f1afaa65b7373f3376b3081f2d66f9ea4a196c10",

    ONNX_BLOCKER:
        "96c865871201ca77daf5dcec620e2d732134b44c49e8f8807ec8550f555657b9",

    EXPORT_PROTOCOL:
        "714eda4d82caf56de2b023cfc04bac0de0f400323a3cefc9077db3ecfdc122ee",

    C_SEMANTIC_CONTRACT:
        "965765b678220d8297b4c930533570b30fa43d2cc681e5fe91ca2431b009efda",

    EMBEDDED_PATH_CONTRACT:
        "eacbc717d36ff12dd6b2873c5d1bfae59d73abd9175c142ef824ad14ea34bcec",

    RUNTIME_CONTRACT:
        "ffacdf7303738208d280f2f21f0d26fc7856a8dcf0946e34d88f133412467ca3",

    HOST_RESOURCE_RESULT:
        "155f880ee5f4d82ed6c03d511fc1401afbdcf8bfff9c8e1a8f2be43901f2e734",
}


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
    ) != PRE_LEDGER_HEAD:
        raise RuntimeError(
            "HEAD changed before convergence ledger freeze"
        )

    expected = {
        "prospective-embedded-build-toolchain-blocker-v1^{commit}":
            TOOLCHAIN_BLOCKER_COMMIT,

        "prospective-model-export-execution-environment-contract-v1^{commit}":
            ONNX_ENV_BLOCKER_COMMIT,

        "prospective-fp32-onnx-exporter-v1^{commit}":
            EXPORTER_COMMIT,

        "prospective-protected-model-export-protocol-v1^{commit}":
            EXPORT_PROTOCOL_COMMIT,

        "portable-c-runtime-implementation-v1^{commit}":
            PORTABLE_C_COMMIT,

        "portable-c-runtime-semantic-contract-v1^{commit}":
            PORTABLE_C_SEMANTIC_COMMIT,

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


def verify_frozen_inputs() -> dict[str, dict]:
    records = {}

    for path, expected in EXPECTED_RAW_HASHES.items():
        if not path.is_file():
            raise RuntimeError(
                f"Frozen evidence absent: {path}"
            )

        if raw_hash(
            path
        ) != expected:
            raise RuntimeError(
                f"Frozen evidence bytes changed: {path}"
            )

        data = json.loads(
            path.read_text()
        )

        if (
            canonical_existing(
                path
            )
            != EXPECTED_CONTENT_HASHES[
                path
            ]
        ):
            raise RuntimeError(
                f"Frozen evidence content changed: {path}"
            )

        records[
            str(
                path.relative_to(
                    ROOT
                )
            )
        ] = data

    return records


def validate_semantic_state(
    records: dict[str, dict],
) -> None:
    toolchain = records[
        "configs/embedded/"
        "prospective_embedded_build_toolchain_blocker_v1.json"
    ]

    onnx_blocker = records[
        "data/manifests/"
        "prospective_model_export_dependency_blocker_v1.json"
    ]

    onnx_env = records[
        "configs/embedded/"
        "prospective_model_export_execution_environment_contract_v1.json"
    ]

    c_contract = records[
        "configs/embedded/"
        "portable_c_runtime_semantic_contract_v1.json"
    ]

    embedded_path = records[
        "configs/embedded/"
        "embedded_reference_path_contract_v1.json"
    ]

    runtime = records[
        "configs/runtime/"
        "runtime_integration_contract_v1.json"
    ]

    if toolchain[
        "status"
    ] != "active":
        raise RuntimeError(
            "Embedded build blocker no longer active"
        )

    if (
        toolchain[
            "resource_claim_boundary"
        ][
            "host_native_c_semantic_parity_already_supported"
        ]
        is not True
    ):
        raise RuntimeError(
            "Portable-C host parity evidence changed"
        )

    for key in (
        "stm32_flash_claim_allowed",
        "stm32_ram_claim_allowed",
        "stm32_cycles_claim_allowed",
        "stm32_latency_claim_allowed",
        "stm32_energy_claim_allowed",
    ):
        if (
            toolchain[
                "resource_claim_boundary"
            ][
                key
            ]
            is not False
        ):
            raise RuntimeError(
                f"STM32 claim boundary changed: {key}"
            )

    if (
        onnx_blocker[
            "status"
        ]
        != "active"
    ):
        raise RuntimeError(
            "ONNX blocker no longer active"
        )

    if (
        onnx_blocker[
            "effect"
        ][
            "exporter_execution_allowed"
        ]
        is not False
    ):
        raise RuntimeError(
            "ONNX exporter execution unexpectedly allowed"
        )

    if (
        onnx_env[
            "current_environment_selection"
        ][
            "selected_interpreter"
        ]
        is not None
    ):
        raise RuntimeError(
            "ONNX execution environment unexpectedly selected"
        )

    if (
        c_contract[
            "ood_contract"
        ][
            "threshold"
        ]
        != 0.00914505124092102
    ):
        raise RuntimeError(
            "Frozen OOD threshold changed"
        )

    if (
        c_contract[
            "historical_task_decision_contract"
        ][
            "threshold"
        ]
        != 0.9
    ):
        raise RuntimeError(
            "Frozen historical prediction bias changed"
        )

    if (
        c_contract[
            "integrity_mask_contract"
        ][
            "IR_SUPPORTED_HARD_CAUSE_MASK"
        ]
        != 1
    ):
        raise RuntimeError(
            "Frozen hard-cause mask changed"
        )

    if (
        embedded_path[
            "prospective_reference_path"
        ][
            "required"
        ]
        is not True
    ):
        raise RuntimeError(
            "Prospective reference lineage changed"
        )

    if (
        embedded_path[
            "historical_recovery_decision"
        ][
            "exact_historical_deployed_firmware_claim_allowed"
        ]
        is not False
    ):
        raise RuntimeError(
            "Historical deployment claim boundary changed"
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
            "One-forward runtime invariant changed"
        )


def build_ledger() -> dict:
    verify_git_anchors()

    records = verify_frozen_inputs()

    validate_semantic_state(
        records
    )

    payload = {
        "ledger_id":
            "EMBEDDED_EVIDENCE_CONVERGENCE_LEDGER_V1",

        "status":
            "workstation_evidence_converged_with_external_infrastructure_gates",

        "target_family":
            "STM32F722",

        "implementation_lineage":
            "prospective_embedded_reference_implementation",

        "convergence_statement":
            (
                "Scientific/runtime semantics and the portable C post-logit "
                "reference implementation are frozen. Further target-model "
                "conversion and STM32 build/resource evidence require "
                "infrastructure not recovered from the searched workstation."
            ),

        "frozen_anchors": {
            "embedded_build_toolchain_blocker": {
                "tag":
                    "prospective-embedded-build-toolchain-blocker-v1",

                "commit":
                    TOOLCHAIN_BLOCKER_COMMIT,

                "raw_sha256":
                    EXPECTED_RAW_HASHES[
                        TOOLCHAIN_BLOCKER
                    ],

                "content_sha256":
                    EXPECTED_CONTENT_HASHES[
                        TOOLCHAIN_BLOCKER
                    ],
            },

            "onnx_execution_environment_blocker": {
                "tag":
                    "prospective-model-export-execution-environment-contract-v1",

                "commit":
                    ONNX_ENV_BLOCKER_COMMIT,

                "raw_sha256":
                    EXPECTED_RAW_HASHES[
                        ONNX_ENV_CONTRACT
                    ],

                "content_sha256":
                    EXPECTED_CONTENT_HASHES[
                        ONNX_ENV_CONTRACT
                    ],
            },

            "onnx_exporter": {
                "tag":
                    "prospective-fp32-onnx-exporter-v1",

                "commit":
                    EXPORTER_COMMIT,
            },

            "onnx_export_protocol": {
                "tag":
                    "prospective-protected-model-export-protocol-v1",

                "commit":
                    EXPORT_PROTOCOL_COMMIT,

                "raw_sha256":
                    EXPECTED_RAW_HASHES[
                        EXPORT_PROTOCOL
                    ],

                "content_sha256":
                    EXPECTED_CONTENT_HASHES[
                        EXPORT_PROTOCOL
                    ],
            },

            "portable_c_runtime": {
                "tag":
                    "portable-c-runtime-implementation-v1",

                "commit":
                    PORTABLE_C_COMMIT,
            },

            "portable_c_semantics": {
                "tag":
                    "portable-c-runtime-semantic-contract-v1",

                "commit":
                    PORTABLE_C_SEMANTIC_COMMIT,

                "raw_sha256":
                    EXPECTED_RAW_HASHES[
                        C_SEMANTIC_CONTRACT
                    ],

                "content_sha256":
                    EXPECTED_CONTENT_HASHES[
                        C_SEMANTIC_CONTRACT
                    ],
            },

            "embedded_reference_path": {
                "tag":
                    "embedded-reference-path-contract-v1",

                "commit":
                    EMBEDDED_PATH_COMMIT,

                "raw_sha256":
                    EXPECTED_RAW_HASHES[
                        EMBEDDED_PATH_CONTRACT
                    ],

                "content_sha256":
                    EXPECTED_CONTENT_HASHES[
                        EMBEDDED_PATH_CONTRACT
                    ],
            },

            "reference_host_resource_result": {
                "tag":
                    "runtime-resource-overhead-result-v1",

                "commit":
                    HOST_RESOURCE_COMMIT,

                "raw_sha256":
                    EXPECTED_RAW_HASHES[
                        HOST_RESOURCE_RESULT
                    ],

                "content_sha256":
                    EXPECTED_CONTENT_HASHES[
                        HOST_RESOURCE_RESULT
                    ],
            },

            "python_reference_runtime": {
                "tag":
                    "runtime-reference-implementation-v1",

                "commit":
                    REFERENCE_RUNTIME_COMMIT,
            },

            "runtime_integration_contract": {
                "tag":
                    "runtime-integration-contract-v1",

                "commit":
                    RUNTIME_CONTRACT_COMMIT,
            },

            "ood_operating_point": {
                "tag":
                    "ood-operating-point-v1",

                "commit":
                    OOD_OPERATING_POINT_COMMIT,
            },

            "integrity_operating_point": {
                "tag":
                    "integrity-operating-point-v1",

                "commit":
                    INTEGRITY_OPERATING_POINT_COMMIT,
            },
        },

        "completed_evidence": {
            "historical_target_archaeology": {
                "complete":
                    True,

                "exact_historical_stm32_firmware_recovered":
                    False,

                "exact_historical_400ms_export_recovered":
                    False,

                "absence_interpretation":
                    "bounded_to_searched_workstation_evidence",
            },

            "runtime_semantics": {
                "frozen":
                    True,

                "task_prediction_always_returned":
                    True,

                "one_full_task_forward_per_window":
                    True,

                "second_full_task_forward_allowed":
                    False,

                "ood_uses_features":
                    False,

                "ood_method":
                    "top_two_logit_margin",

                "ood_threshold":
                    0.00914505124092102,

                "ood_unknown_condition":
                    "margin < threshold",

                "integrity_hard_cause_mask":
                    1,

                "hard_cause":
                    "FRAME_GAP",

                "precedence": [
                    "INTEGRITY_ALERT",
                    "OOD_UNKNOWN",
                    "VALID",
                ],
            },

            "portable_c_reference": {
                "implemented":
                    True,

                "lineage":
                    "prospective_embedded_reference_implementation",

                "native_c_test_count":
                    13,

                "python_c_parity_test_count":
                    9,

                "deterministic_float32_grid_case_count":
                    162,

                "host_semantic_parity_supported":
                    True,

                "checkpoint_required_for_c_parity":
                    False,

                "protected_dataset_required_for_c_parity":
                    False,
            },

            "reference_host_resource_evidence": {
                "frozen":
                    True,

                "scope":
                    "x86_64_reference_host_only",

                "protected_dataset_used":
                    False,

                "may_be_relabelled_as_stm32_resource_evidence":
                    False,

                "benchmark_v1_may_be_rerun":
                    False,
            },

            "prospective_onnx_method": {
                "protocol_frozen":
                    True,

                "exporter_frozen":
                    True,

                "format":
                    "ONNX",

                "precision":
                    "float32",

                "opset":
                    13,

                "input_shape":
                    [1, 40, 9],

                "output_shape":
                    [1, 2],

                "parity_vector_count":
                    68,

                "absolute_tolerance":
                    1.0e-5,

                "relative_tolerance":
                    1.0e-5,

                "decision_mismatch_tolerance":
                    0,

                "quantization_included":
                    False,
            },
        },

        "active_infrastructure_gates": {
            "GATE_A_ONNX_EXECUTION_ENVIRONMENT": {
                "status":
                    "BLOCKED",

                "reason":
                    (
                        "No qualified existing single Python interpreter "
                        "providing torch + onnx + onnxruntime with required "
                        "CPU execution provider was recovered."
                    ),

                "current_selected_interpreter":
                    None,

                "checkpoint_deserialization_allowed":
                    False,

                "model_forward_allowed":
                    False,

                "onnx_export_allowed":
                    False,

                "minimum_release_requirements": [
                    "single qualified Python interpreter",
                    "torch importable",
                    "onnx importable",
                    "onnxruntime importable",
                    "CPUExecutionProvider available",
                    "torch.onnx.export API audited against frozen exporter",
                    "exact environment qualification frozen before first export",
                ],
            },

            "GATE_B_ARM_STM32_BUILD_TOOLCHAIN": {
                "status":
                    "BLOCKED",

                "reason":
                    (
                        "No qualified ARM GNU bare-metal compiler/binutils, "
                        "STM32 SDK, offline archive/cache, or equivalent "
                        "target build toolchain was recovered."
                    ),

                "arm_none_eabi_gcc_available":
                    False,

                "stm32_sdk_available":
                    False,

                "target_cross_compile_allowed":
                    False,

                "firmware_build_allowed":
                    False,

                "minimum_release_requirements": [
                    "qualified ARM GNU bare-metal compiler",
                    "qualified binutils",
                    "exact compiler version and executable hashes",
                    "Cortex-M target verification",
                    "toolchain qualification frozen before first cross-compile",
                ],
            },

            "GATE_C_STM32_TARGET_INTEGRATION_AND_MEASUREMENT": {
                "status":
                    "BLOCKED",

                "reason":
                    (
                        "No full prospective firmware integration path or "
                        "connected STM32F722/ST-LINK target was recovered."
                    ),

                "prerequisites": [
                    "Gate B released",
                    "STM32F722 target definition",
                    "startup/runtime support",
                    "linker memory map",
                    "CMSIS or equivalent target headers",
                    "prospective firmware integration",
                    "qualified measurement hardware/path",
                ],

                "required_for_cycles_latency_energy":
                    True,
            },
        },

        "currently_supported_claims": [
            "Exact surviving historical checkpoint is available.",
            "Training/runtime lineage is high-confidence reconstructed, not exact deployed firmware.",
            "Frozen reliability semantics are implemented in Python reference runtime.",
            "Portable C post-logit reliability semantics match the frozen Python reference on host validation.",
            "Portable C implementation is a prospective embedded reference implementation.",
            "Reference-host runtime overhead evidence is valid only for the frozen x86-64 host benchmark.",
            "Only FRAME_GAP is a selected V1 hard integrity cause.",
            "OOD_UNKNOWN is residual model unfamiliarity and is not proof of sensor failure.",
        ],

        "currently_prohibited_claims": [
            "exact historical deployed STM32 firmware recovered",
            "exact historical deployed embedded model/export recovered",
            "prospective ONNX export validated",
            "STM32 importability validated",
            "STM32 model numerical parity validated",
            "full STM32F722 firmware built",
            "STM32 flash footprint measured",
            "STM32 RAM footprint measured",
            "STM32 cycle count measured",
            "STM32 latency measured",
            "STM32 energy measured",
            "host Python/native measurements are equivalent to STM32 resource measurements",
        ],

        "closed_scientific_boundaries": {
            "ood_threshold_may_change":
                False,

            "ood_method_may_change":
                False,

            "historical_task_rule_may_change":
                False,

            "integrity_operating_point_may_change":
                False,

            "protected_final_test_may_be_reopened":
                False,

            "final_ood_evaluator_may_be_rerun":
                False,

            "host_resource_benchmark_v1_may_be_rerun":
                False,

            "classifier_bypass_allowed":
                False,

            "second_full_task_forward_allowed":
                False,
        },

        "workstation_convergence_policy": {
            "repeat_historical_embedded_archaeology_without_new_evidence":
                False,

            "repeat_onnx_runtime_archaeology_without_new_evidence":
                False,

            "repeat_arm_toolchain_archaeology_without_new_evidence":
                False,

            "install_packages_or_toolchains_as_part_of_this_ledger":
                False,

            "execute_exporter_as_part_of_this_ledger":
                False,

            "deserialize_checkpoint_as_part_of_this_ledger":
                False,

            "build_firmware_as_part_of_this_ledger":
                False,

            "measure_stm32_hardware_as_part_of_this_ledger":
                False,
        },

        "next_decision_boundary": {
            "workstation_only_embedded_engineering_exhausted":
                True,

            "further_target_evidence_requires_external_infrastructure_change":
                True,

            "allowed_next_planning_branches": [
                "controlled isolated ONNX execution environment acquisition plan",
                "controlled ARM GNU STM32 build-toolchain acquisition plan",
                "paper/evidence synthesis that preserves current claim boundaries",
            ],

            "automatic_environment_or_toolchain_installation_allowed":
                False,
        },

        "freeze_boundary": {
            "package_install_performed":
                False,

            "toolchain_installed":
                False,

            "exporter_executed":
                False,

            "checkpoint_deserialized":
                False,

            "model_forward_executed":
                False,

            "onnx_export_executed":
                False,

            "cross_compiler_executed":
                False,

            "firmware_built":
                False,

            "stm32_device_measured":
                False,

            "protected_dataset_opened":
                False,

            "final_test_reopened":
                False,

            "resource_benchmark_rerun":
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
    if LEDGER.exists():
        raise RuntimeError(
            "Refusing to overwrite embedded convergence ledger"
        )

    ledger = build_ledger()

    LEDGER.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    LEDGER.write_text(
        json.dumps(
            ledger,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        "EMBEDDED_EVIDENCE_CONVERGENCE_LEDGER_V1_WRITTEN = True"
    )

    print(
        "LEDGER_CONTENT_SHA256 =",
        ledger[
            "content_sha256"
        ],
    )

    print(
        "STATUS =",
        ledger[
            "status"
        ],
    )

    print(
        "TARGET_FAMILY =",
        ledger[
            "target_family"
        ],
    )

    for name, gate in ledger[
        "active_infrastructure_gates"
    ].items():
        print(
            name,
            "=",
            gate[
                "status"
            ],
        )

    print(
        "WORKSTATION_ONLY_EMBEDDED_ENGINEERING_EXHAUSTED =",
        ledger[
            "next_decision_boundary"
        ][
            "workstation_only_embedded_engineering_exhausted"
        ],
    )

    print(
        "PACKAGE_INSTALL_PERFORMED = False"
    )

    print(
        "EXPORTER_EXECUTED = False"
    )

    print(
        "CHECKPOINT_DESERIALIZED = False"
    )

    print(
        "CROSS_COMPILER_EXECUTED = False"
    )

    print(
        "FIRMWARE_BUILT = False"
    )


if __name__ == "__main__":
    main()
