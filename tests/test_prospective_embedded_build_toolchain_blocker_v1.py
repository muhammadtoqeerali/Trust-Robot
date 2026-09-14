from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from copy import deepcopy
from hashlib import sha256
from pathlib import Path


ROOT = Path(
    __file__
).resolve().parents[1]

BUILDER = (
    ROOT
    / "experiments/05_embedded/"
      "build_embedded_build_toolchain_blocker_v1.py"
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


SPEC = importlib.util.spec_from_file_location(
    "build_embedded_build_toolchain_blocker_v1",
    BUILDER,
)

if SPEC is None or SPEC.loader is None:
    raise RuntimeError(
        "Unable to import embedded-build blocker builder"
    )

MOD = importlib.util.module_from_spec(
    SPEC
)

sys.modules[
    SPEC.name
] = MOD

SPEC.loader.exec_module(
    MOD
)


def hash_roundtrip(
    data,
):
    payload = deepcopy(
        data
    )

    stored = payload.pop(
        "content_sha256"
    )

    normalized = json.loads(
        json.dumps(
            payload,
            separators=(",", ":"),
            allow_nan=False,
        )
    )

    computed = sha256(
        json.dumps(
            normalized,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode(
            "utf-8"
        )
    ).hexdigest()

    return (
        stored,
        computed,
    )


class ProspectiveEmbeddedBuildToolchainBlockerV1Tests(
    unittest.TestCase
):

    @classmethod
    def setUpClass(
        cls,
    ):
        cls.receipt = json.loads(
            RECEIPT.read_text()
        )

        cls.contract = json.loads(
            CONTRACT.read_text()
        )

    def test_git_anchors(
        self,
    ):
        MOD.verify_git_anchors()

    def test_frozen_inputs(
        self,
    ):
        MOD.verify_frozen_inputs()

    def test_live_common_toolchain_state(
        self,
    ):
        MOD.verify_live_common_toolchain_state()

    def test_receipt_hash(
        self,
    ):
        stored, computed = hash_roundtrip(
            self.receipt
        )

        self.assertEqual(
            stored,
            computed,
        )

    def test_contract_hash(
        self,
    ):
        stored, computed = hash_roundtrip(
            self.contract
        )

        self.assertEqual(
            stored,
            computed,
        )

    def test_target_family(
        self,
    ):
        self.assertEqual(
            self.contract[
                "target_family"
            ],
            "STM32F722",
        )

    def test_all_strong_archaeology_counts_zero(
        self,
    ):
        observed = self.receipt[
            "observations"
        ]

        for key in (
            "common_arm_gnu_command_count",
            "common_stm32_tool_command_count",
            "installed_arm_or_stm32_package_count",
            "apt_cached_arm_or_stm32_package_count",
            "discovered_arm_toolchain_executable_count",
            "discovered_stm32_sdk_or_toolchain_marker_count",
            "offline_arm_or_stm32_toolchain_archive_count",
            "conda_or_micromamba_arm_toolchain_cache_count",
            "serial_device_candidate_count",
            "stm32_or_stlink_usb_device_count",
        ):
            self.assertEqual(
                observed[
                    key
                ],
                0,
            )

        self.assertEqual(
            observed[
                "audit_rc"
            ],
            0,
        )

    def test_make_only_build_tool_present(
        self,
    ):
        observed = self.receipt[
            "observations"
        ]

        self.assertTrue(
            observed[
                "make_available"
            ]
        )

        self.assertEqual(
            observed[
                "make_path"
            ],
            "/usr/bin/make",
        )

        self.assertFalse(
            observed[
                "cmake_available"
            ]
        )

        self.assertFalse(
            observed[
                "ninja_available"
            ]
        )

    def test_absence_claim_is_bounded(
        self,
    ):
        interpretation = self.receipt[
            "interpretation"
        ]

        self.assertTrue(
            interpretation[
                "absence_is_bounded_to_searched_workstation_evidence"
            ]
        )

        self.assertFalse(
            interpretation[
                "absence_proves_toolchain_never_existed"
            ]
        )

    def test_blocker_active(
        self,
    ):
        self.assertEqual(
            self.contract[
                "status"
            ],
            "active",
        )

    def test_target_build_blocked(
        self,
    ):
        state = self.contract[
            "current_target_build_state"
        ]

        self.assertFalse(
            state[
                "arm_none_eabi_gcc_available"
            ]
        )

        self.assertFalse(
            state[
                "target_cross_compile_allowed"
            ]
        )

        self.assertFalse(
            state[
                "firmware_build_allowed"
            ]
        )

        self.assertFalse(
            state[
                "target_resource_measurement_allowed"
            ]
        )

    def test_toolchain_must_be_qualified_before_use(
        self,
    ):
        rule = self.contract[
            "blocker_release_rule"
        ]

        self.assertTrue(
            rule[
                "candidate_must_be_qualified_and_frozen_before_use"
            ]
        )

        self.assertFalse(
            rule[
                "toolchain_discovery_alone_allows_cross_compile"
            ]
        )

        self.assertFalse(
            rule[
                "package_archive_discovery_alone_allows_installation"
            ]
        )

    def test_full_firmware_requires_more_than_portable_core(
        self,
    ):
        firmware = self.contract[
            "full_stm32_firmware_requirements"
        ]

        self.assertFalse(
            firmware[
                "portable_c_cross_compile_alone_is_full_firmware"
            ]
        )

        self.assertFalse(
            firmware[
                "historical_firmware_recovered"
            ]
        )

        self.assertTrue(
            firmware[
                "prospective_firmware_must_be_labeled_prospective"
            ]
        )

    def test_no_stm32_resource_claim(
        self,
    ):
        claims = self.contract[
            "resource_claim_boundary"
        ]

        for key in (
            "stm32_compilation_completed",
            "stm32_link_completed",
            "stm32_text_rodata_footprint_measured",
            "stm32_data_bss_footprint_measured",
            "stm32_cycles_measured",
            "stm32_latency_measured",
            "stm32_energy_measured",
            "stm32_flash_claim_allowed",
            "stm32_ram_claim_allowed",
            "stm32_cycles_claim_allowed",
            "stm32_latency_claim_allowed",
            "stm32_energy_claim_allowed",
        ):
            self.assertFalse(
                claims[
                    key
                ]
            )

    def test_host_semantic_parity_remains_valid_scope(
        self,
    ):
        claims = self.contract[
            "resource_claim_boundary"
        ]

        self.assertTrue(
            claims[
                "host_native_c_semantic_parity_already_supported"
            ]
        )

    def test_scientific_boundary_closed(
        self,
    ):
        science = self.contract[
            "scientific_boundary"
        ]

        for key in (
            "ood_threshold_may_change",
            "ood_method_may_change",
            "historical_task_rule_may_change",
            "integrity_operating_point_may_change",
            "protected_final_test_may_be_reopened",
            "host_resource_benchmark_may_be_rerun",
            "classifier_bypass_allowed",
            "second_task_model_forward_allowed",
        ):
            self.assertFalse(
                science[
                    key
                ]
            )

    def test_onnx_blocker_still_parallel(
        self,
    ):
        parallel = self.contract[
            "parallel_infrastructure_state"
        ]

        self.assertTrue(
            parallel[
                "onnx_export_blocker_active"
            ]
        )

        self.assertFalse(
            parallel[
                "onnx_exporter_execution_allowed"
            ]
        )


if __name__ == "__main__":
    unittest.main()
