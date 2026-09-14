from __future__ import annotations

import json
import shutil
import subprocess
from copy import deepcopy
from hashlib import sha256
from pathlib import Path


ROOT = Path(
    __file__
).resolve().parents[2]


PRE_BLOCKER_HEAD = (
    "ea2653fe08a6b684ad652e0a0ad8ff8191e2632b"
)

EXPORT_ENVIRONMENT_COMMIT = (
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

ONNX_BLOCKER = (
    ROOT
    / "data/manifests/"
      "prospective_model_export_dependency_blocker_v1.json"
)

ONNX_ENV_CONTRACT = (
    ROOT
    / "configs/embedded/"
      "prospective_model_export_execution_environment_contract_v1.json"
)

RECEIPT = (
    ROOT
    / "data/manifests/"
      "embedded_build_toolchain_archaeology_receipt_v1.json"
)

CONTRACT = (
    ROOT
    / "configs/embedded/"
      "prospective_embedded_build_toolchain_blocker_v1.json"
)


EXPECTED_RAW_HASHES = {
    PORTABLE_C_HEADER:
        "0162556076334f8ff1323788fd133a33a7e110daba41c7aaba12967fbe3d858e",

    PORTABLE_C_SOURCE:
        "1b7e7fd97f993bb63396a72912f5d5b8bc2b5bb68864e9c556db8dddf6617fa6",

    ONNX_BLOCKER:
        "33c07b0f2a5bc1422ce849fa680934c0d7a77bcfa2dfdbe59a4872ee8f67ee29",

    ONNX_ENV_CONTRACT:
        "3f9f5f80886e09f8c04535c9fc253c8f98cd4cd6221d35e6229719503266a957",
}


EXPECTED_ABSENT_COMMANDS = (
    "arm-none-eabi-gcc",
    "arm-none-eabi-g++",
    "arm-none-eabi-as",
    "arm-none-eabi-ld",
    "arm-none-eabi-ar",
    "arm-none-eabi-nm",
    "arm-none-eabi-size",
    "arm-none-eabi-objcopy",
    "arm-none-eabi-objdump",
    "arm-none-eabi-readelf",
    "openocd",
    "st-flash",
    "st-info",
    "STM32_Programmer_CLI",
    "STM32CubeProgrammer_CLI",
    "STM32CubeMX",
    "stm32cubemx",
    "stm32cubeide",
)


ARCHAEOLOGY_OBSERVATIONS = {
    "common_arm_gnu_command_count":
        0,

    "common_stm32_tool_command_count":
        0,

    "make_available":
        True,

    "make_path":
        "/usr/bin/make",

    "cmake_available":
        False,

    "ninja_available":
        False,

    "installed_arm_or_stm32_package_count":
        0,

    "apt_cached_arm_or_stm32_package_count":
        0,

    "discovered_arm_toolchain_executable_count":
        0,

    "discovered_stm32_sdk_or_toolchain_marker_count":
        0,

    "offline_arm_or_stm32_toolchain_archive_count":
        0,

    "conda_or_micromamba_arm_toolchain_cache_count":
        0,

    "serial_device_candidate_count":
        0,

    "stm32_or_stlink_usb_device_count":
        0,

    "audit_rc":
        0,
}


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


def canonical_existing(
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


def verify_git_anchors() -> None:
    if git(
        "rev-parse",
        "HEAD",
    ) != PRE_BLOCKER_HEAD:
        raise RuntimeError(
            "HEAD changed before embedded-build blocker freeze"
        )

    expected = {
        "prospective-model-export-execution-environment-contract-v1^{commit}":
            EXPORT_ENVIRONMENT_COMMIT,

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


def verify_frozen_inputs() -> tuple[dict, dict]:
    for p, expected in EXPECTED_RAW_HASHES.items():
        if not p.is_file():
            raise RuntimeError(
                f"Frozen input missing: {p}"
            )

        if raw_hash(
            p
        ) != expected:
            raise RuntimeError(
                f"Frozen input changed: {p}"
            )

    onnx_blocker = json.loads(
        ONNX_BLOCKER.read_text()
    )

    onnx_contract = json.loads(
        ONNX_ENV_CONTRACT.read_text()
    )

    if (
        onnx_blocker[
            "status"
        ]
        != "active"
    ):
        raise RuntimeError(
            "ONNX infrastructure blocker is no longer active"
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
            "ONNX exporter execution boundary changed"
        )

    if (
        onnx_contract[
            "current_environment_selection"
        ][
            "selected_interpreter"
        ]
        is not None
    ):
        raise RuntimeError(
            "ONNX export interpreter unexpectedly selected"
        )

    return (
        onnx_blocker,
        onnx_contract,
    )


def verify_live_common_toolchain_state() -> None:
    for command in EXPECTED_ABSENT_COMMANDS:
        observed = shutil.which(
            command
        )

        if observed is not None:
            raise RuntimeError(
                f"Toolchain command appeared: {command} -> {observed}"
            )

    if shutil.which(
        "make"
    ) != "/usr/bin/make":
        raise RuntimeError(
            "GNU make availability changed"
        )

    if shutil.which(
        "cmake"
    ) is not None:
        raise RuntimeError(
            "CMake unexpectedly appeared"
        )

    if shutil.which(
        "ninja"
    ) is not None:
        raise RuntimeError(
            "Ninja unexpectedly appeared"
        )


def build_receipt() -> dict:
    payload = {
        "receipt_id":
            "EMBEDDED_BUILD_TOOLCHAIN_ARCHAEOLOGY_RECEIPT_V1",

        "status":
            "completed_read_only_no_target_toolchain_recovered",

        "target_family":
            "STM32F722",

        "observation_scope":
            (
                "available workstation commands, installed Debian packages, "
                "APT cache, searched filesystem roots, STM32/Cube markers, "
                "offline archives, Conda/Micromamba caches, serial devices, "
                "and USB ST-LINK/STM32 candidates"
            ),

        "observations":
            dict(
                ARCHAEOLOGY_OBSERVATIONS
            ),

        "interpretation": {
            "usable_arm_gnu_toolchain_recovered":
                False,

            "usable_stm32_sdk_or_cube_toolchain_recovered":
                False,

            "offline_toolchain_archive_recovered":
                False,

            "offline_toolchain_package_cache_recovered":
                False,

            "connected_stm32_or_stlink_device_recovered":
                False,

            "absence_is_bounded_to_searched_workstation_evidence":
                True,

            "absence_proves_toolchain_never_existed":
                False,
        },

        "read_only_boundary": {
            "package_install_performed":
                False,

            "toolchain_installed":
                False,

            "toolchain_archive_extracted":
                False,

            "cross_compiler_executed":
                False,

            "firmware_built":
                False,

            "device_programmed":
                False,

            "device_measured":
                False,

            "checkpoint_deserialized":
                False,

            "model_forward_executed":
                False,

            "onnx_export_executed":
                False,

            "protected_dataset_opened":
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


def build_contract(
    receipt: dict,
) -> dict:
    payload = {
        "contract_id":
            "PROSPECTIVE_EMBEDDED_BUILD_TOOLCHAIN_BLOCKER_V1",

        "status":
            "active",

        "target_family":
            "STM32F722",

        "source_receipt": {
            "path":
                "data/manifests/"
                "embedded_build_toolchain_archaeology_receipt_v1.json",

            "receipt_id":
                receipt[
                    "receipt_id"
                ],

            "content_sha256":
                receipt[
                    "content_sha256"
                ],
        },

        "frozen_lineage": {
            "portable_c_runtime_tag":
                "portable-c-runtime-implementation-v1",

            "portable_c_runtime_commit":
                PORTABLE_C_COMMIT,

            "portable_c_header_raw_sha256":
                EXPECTED_RAW_HASHES[
                    PORTABLE_C_HEADER
                ],

            "portable_c_source_raw_sha256":
                EXPECTED_RAW_HASHES[
                    PORTABLE_C_SOURCE
                ],

            "embedded_reference_path_tag":
                "embedded-reference-path-contract-v1",

            "embedded_reference_path_commit":
                EMBEDDED_PATH_COMMIT,
        },

        "current_target_build_state": {
            "arm_none_eabi_gcc_available":
                False,

            "arm_none_eabi_binutils_available":
                False,

            "cmake_available":
                False,

            "ninja_available":
                False,

            "make_available":
                True,

            "stm32_cube_sdk_available":
                False,

            "stm32_programming_tool_available":
                False,

            "openocd_or_stlink_tool_available":
                False,

            "connected_stm32_or_stlink_device_available":
                False,

            "target_cross_compile_allowed":
                False,

            "firmware_build_allowed":
                False,

            "target_resource_measurement_allowed":
                False,
        },

        "portable_c_cross_compile_requirements": {
            "required_before_cross_compile": [
                "qualified ARM GNU bare-metal compiler",
                "qualified ARM GNU assembler/linker/binutils",
                "exact compiler version and executable hashes recorded",
                "compiler target verified as ARM Cortex-M compatible",
            ],

            "minimum_required_commands": [
                "arm-none-eabi-gcc",
                "arm-none-eabi-ar",
                "arm-none-eabi-nm",
                "arm-none-eabi-size",
                "arm-none-eabi-objdump",
                "arm-none-eabi-readelf",
            ],

            "cross_compile_may_start_before_toolchain_qualification":
                False,
        },

        "full_stm32_firmware_requirements": {
            "portable_c_cross_compile_alone_is_full_firmware":
                False,

            "additional_target_integration_inputs_required": [
                "STM32F722 target definition",
                "startup/runtime support",
                "linker memory map",
                "CMSIS or equivalent target headers",
                "HAL/board integration only if required by prospective firmware",
            ],

            "historical_firmware_recovered":
                False,

            "prospective_firmware_must_be_labeled_prospective":
                True,
        },

        "blocker_release_rule": {
            "release_requires_toolchain_candidate":
                True,

            "candidate_must_be_qualified_and_frozen_before_use":
                True,

            "toolchain_discovery_alone_allows_cross_compile":
                False,

            "package_archive_discovery_alone_allows_installation":
                False,

            "toolchain_installation_is_part_of_this_contract":
                False,

            "future_installation_requires_separate_explicit_control_step":
                True,
        },

        "resource_claim_boundary": {
            "host_native_c_semantic_parity_already_supported":
                True,

            "stm32_compilation_completed":
                False,

            "stm32_link_completed":
                False,

            "stm32_text_rodata_footprint_measured":
                False,

            "stm32_data_bss_footprint_measured":
                False,

            "stm32_cycles_measured":
                False,

            "stm32_latency_measured":
                False,

            "stm32_energy_measured":
                False,

            "stm32_flash_claim_allowed":
                False,

            "stm32_ram_claim_allowed":
                False,

            "stm32_cycles_claim_allowed":
                False,

            "stm32_latency_claim_allowed":
                False,

            "stm32_energy_claim_allowed":
                False,
        },

        "scientific_boundary": {
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

            "host_resource_benchmark_may_be_rerun":
                False,

            "classifier_bypass_allowed":
                False,

            "second_task_model_forward_allowed":
                False,
        },

        "parallel_infrastructure_state": {
            "onnx_export_blocker_active":
                True,

            "onnx_exporter_execution_allowed":
                False,

            "checkpoint_deserialization_allowed_for_onnx_branch":
                False,
        },

        "freeze_boundary": {
            "package_install_performed":
                False,

            "toolchain_installed":
                False,

            "toolchain_archive_extracted":
                False,

            "cross_compiler_executed":
                False,

            "firmware_built":
                False,

            "stm32_device_programmed":
                False,

            "stm32_device_measured":
                False,

            "checkpoint_deserialized":
                False,

            "model_forward_executed":
                False,

            "onnx_export_executed":
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
    if RECEIPT.exists():
        raise RuntimeError(
            "Refusing to overwrite toolchain archaeology receipt"
        )

    if CONTRACT.exists():
        raise RuntimeError(
            "Refusing to overwrite embedded-build blocker"
        )

    verify_git_anchors()
    verify_frozen_inputs()
    verify_live_common_toolchain_state()

    receipt = build_receipt()

    contract = build_contract(
        receipt
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
            receipt,
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

    print(
        "EMBEDDED_BUILD_TOOLCHAIN_ARCHAEOLOGY_RECEIPT_V1_WRITTEN = True"
    )

    print(
        "PROSPECTIVE_EMBEDDED_BUILD_TOOLCHAIN_BLOCKER_V1_WRITTEN = True"
    )

    print(
        "RECEIPT_CONTENT_SHA256 =",
        receipt[
            "content_sha256"
        ],
    )

    print(
        "CONTRACT_CONTENT_SHA256 =",
        contract[
            "content_sha256"
        ],
    )

    print(
        "BLOCKER_ACTIVE =",
        contract[
            "status"
        ]
        == "active",
    )

    print(
        "ARM_GNU_TOOLCHAIN_AVAILABLE =",
        contract[
            "current_target_build_state"
        ][
            "arm_none_eabi_gcc_available"
        ],
    )

    print(
        "STM32_SDK_AVAILABLE =",
        contract[
            "current_target_build_state"
        ][
            "stm32_cube_sdk_available"
        ],
    )

    print(
        "TARGET_CROSS_COMPILE_ALLOWED =",
        contract[
            "current_target_build_state"
        ][
            "target_cross_compile_allowed"
        ],
    )

    print(
        "STM32_RESOURCE_CLAIMS_ALLOWED = False"
    )

    print(
        "TOOLCHAIN_INSTALLED = False"
    )

    print(
        "CROSS_COMPILER_EXECUTED = False"
    )

    print(
        "FIRMWARE_BUILT = False"
    )


if __name__ == "__main__":
    main()
