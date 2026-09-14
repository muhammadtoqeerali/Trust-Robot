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
      "build_embedded_evidence_convergence_ledger_v1.py"
)

LEDGER = (
    ROOT
    / "configs/embedded/"
      "embedded_evidence_convergence_ledger_v1.json"
)


SPEC = importlib.util.spec_from_file_location(
    "build_embedded_evidence_convergence_ledger_v1",
    BUILDER,
)

if SPEC is None or SPEC.loader is None:
    raise RuntimeError(
        "Unable to import convergence-ledger builder"
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


class EmbeddedEvidenceConvergenceLedgerV1Tests(
    unittest.TestCase
):

    @classmethod
    def setUpClass(
        cls,
    ):
        cls.ledger = json.loads(
            LEDGER.read_text()
        )

    def test_git_anchors(
        self,
    ):
        MOD.verify_git_anchors()

    def test_frozen_inputs(
        self,
    ):
        records = MOD.verify_frozen_inputs()

        MOD.validate_semantic_state(
            records
        )

    def test_content_hash(
        self,
    ):
        payload = deepcopy(
            self.ledger
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

        self.assertEqual(
            stored,
            computed,
        )

    def test_converged_status(
        self,
    ):
        self.assertEqual(
            self.ledger[
                "status"
            ],
            "workstation_evidence_converged_with_external_infrastructure_gates",
        )

    def test_target_and_lineage(
        self,
    ):
        self.assertEqual(
            self.ledger[
                "target_family"
            ],
            "STM32F722",
        )

        self.assertEqual(
            self.ledger[
                "implementation_lineage"
            ],
            "prospective_embedded_reference_implementation",
        )

    def test_historical_target_claim_boundary(
        self,
    ):
        historical = self.ledger[
            "completed_evidence"
        ][
            "historical_target_archaeology"
        ]

        self.assertFalse(
            historical[
                "exact_historical_stm32_firmware_recovered"
            ]
        )

        self.assertFalse(
            historical[
                "exact_historical_400ms_export_recovered"
            ]
        )

    def test_runtime_semantics_closed(
        self,
    ):
        runtime = self.ledger[
            "completed_evidence"
        ][
            "runtime_semantics"
        ]

        self.assertTrue(
            runtime[
                "frozen"
            ]
        )

        self.assertEqual(
            runtime[
                "ood_threshold"
            ],
            0.00914505124092102,
        )

        self.assertEqual(
            runtime[
                "integrity_hard_cause_mask"
            ],
            1,
        )

        self.assertFalse(
            runtime[
                "second_full_task_forward_allowed"
            ]
        )

    def test_portable_c_host_parity_supported(
        self,
    ):
        c = self.ledger[
            "completed_evidence"
        ][
            "portable_c_reference"
        ]

        self.assertTrue(
            c[
                "implemented"
            ]
        )

        self.assertTrue(
            c[
                "host_semantic_parity_supported"
            ]
        )

        self.assertEqual(
            c[
                "native_c_test_count"
            ],
            13,
        )

        self.assertEqual(
            c[
                "python_c_parity_test_count"
            ],
            9,
        )

        self.assertEqual(
            c[
                "deterministic_float32_grid_case_count"
            ],
            162,
        )

    def test_host_resource_scope_only(
        self,
    ):
        resource = self.ledger[
            "completed_evidence"
        ][
            "reference_host_resource_evidence"
        ]

        self.assertTrue(
            resource[
                "frozen"
            ]
        )

        self.assertEqual(
            resource[
                "scope"
            ],
            "x86_64_reference_host_only",
        )

        self.assertFalse(
            resource[
                "may_be_relabelled_as_stm32_resource_evidence"
            ]
        )

    def test_onnx_method_frozen_but_not_executed(
        self,
    ):
        onnx = self.ledger[
            "completed_evidence"
        ][
            "prospective_onnx_method"
        ]

        self.assertTrue(
            onnx[
                "protocol_frozen"
            ]
        )

        self.assertTrue(
            onnx[
                "exporter_frozen"
            ]
        )

        self.assertEqual(
            onnx[
                "format"
            ],
            "ONNX",
        )

        self.assertFalse(
            onnx[
                "quantization_included"
            ]
        )

    def test_gate_a_blocked(
        self,
    ):
        gate = self.ledger[
            "active_infrastructure_gates"
        ][
            "GATE_A_ONNX_EXECUTION_ENVIRONMENT"
        ]

        self.assertEqual(
            gate[
                "status"
            ],
            "BLOCKED",
        )

        self.assertFalse(
            gate[
                "checkpoint_deserialization_allowed"
            ]
        )

        self.assertFalse(
            gate[
                "onnx_export_allowed"
            ]
        )

    def test_gate_b_blocked(
        self,
    ):
        gate = self.ledger[
            "active_infrastructure_gates"
        ][
            "GATE_B_ARM_STM32_BUILD_TOOLCHAIN"
        ]

        self.assertEqual(
            gate[
                "status"
            ],
            "BLOCKED",
        )

        self.assertFalse(
            gate[
                "arm_none_eabi_gcc_available"
            ]
        )

        self.assertFalse(
            gate[
                "target_cross_compile_allowed"
            ]
        )

    def test_gate_c_blocked(
        self,
    ):
        gate = self.ledger[
            "active_infrastructure_gates"
        ][
            "GATE_C_STM32_TARGET_INTEGRATION_AND_MEASUREMENT"
        ]

        self.assertEqual(
            gate[
                "status"
            ],
            "BLOCKED",
        )

        self.assertTrue(
            gate[
                "required_for_cycles_latency_energy"
            ]
        )

    def test_no_stm32_resource_claims(
        self,
    ):
        prohibited = set(
            self.ledger[
                "currently_prohibited_claims"
            ]
        )

        for claim in (
            "STM32 flash footprint measured",
            "STM32 RAM footprint measured",
            "STM32 cycle count measured",
            "STM32 latency measured",
            "STM32 energy measured",
        ):
            self.assertIn(
                claim,
                prohibited,
            )

    def test_scientific_boundaries_remain_closed(
        self,
    ):
        closed = self.ledger[
            "closed_scientific_boundaries"
        ]

        for value in closed.values():
            self.assertFalse(
                value
            )

    def test_no_repeat_archaeology_without_new_evidence(
        self,
    ):
        policy = self.ledger[
            "workstation_convergence_policy"
        ]

        self.assertFalse(
            policy[
                "repeat_historical_embedded_archaeology_without_new_evidence"
            ]
        )

        self.assertFalse(
            policy[
                "repeat_onnx_runtime_archaeology_without_new_evidence"
            ]
        )

        self.assertFalse(
            policy[
                "repeat_arm_toolchain_archaeology_without_new_evidence"
            ]
        )

    def test_no_side_effects_in_ledger_stage(
        self,
    ):
        boundary = self.ledger[
            "freeze_boundary"
        ]

        for value in boundary.values():
            self.assertFalse(
                value
            )

    def test_workstation_engineering_converged(
        self,
    ):
        decision = self.ledger[
            "next_decision_boundary"
        ]

        self.assertTrue(
            decision[
                "workstation_only_embedded_engineering_exhausted"
            ]
        )

        self.assertTrue(
            decision[
                "further_target_evidence_requires_external_infrastructure_change"
            ]
        )

        self.assertFalse(
            decision[
                "automatic_environment_or_toolchain_installation_allowed"
            ]
        )


if __name__ == "__main__":
    unittest.main()
