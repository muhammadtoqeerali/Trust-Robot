from __future__ import annotations

import importlib.util
import json
import struct
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
      "build_portable_c_runtime_semantic_contract_v1.py"
)

CONTRACT = (
    ROOT
    / "configs/embedded/"
      "portable_c_runtime_semantic_contract_v1.json"
)


SPEC = importlib.util.spec_from_file_location(
    "build_portable_c_runtime_semantic_contract_v1",
    BUILDER,
)

if (
    SPEC is None
    or SPEC.loader is None
):
    raise RuntimeError(
        "Unable to import portable-C semantic contract builder"
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


class PortableCRuntimeSemanticContractV1Tests(
    unittest.TestCase
):

    @classmethod
    def setUpClass(
        cls,
    ):
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

    def test_implementation_absent(
        self,
    ):
        MOD.verify_implementation_absent()

    def test_content_hash_roundtrip(
        self,
    ):
        payload = deepcopy(
            self.contract
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

    def test_prospective_lineage(
        self,
    ):
        lineage = self.contract[
            "lineage"
        ]

        self.assertEqual(
            lineage[
                "implementation_label"
            ],
            "prospective_embedded_reference_implementation",
        )

        self.assertFalse(
            lineage[
                "exact_historical_deployment"
            ]
        )

    def test_exact_public_api(
        self,
    ):
        api = self.contract[
            "public_api"
        ]

        self.assertEqual(
            api[
                "function_name"
            ],
            "ir_decide_from_logits",
        )

        self.assertFalse(
            api[
                "function_invokes_task_model"
            ]
        )

        self.assertFalse(
            api[
                "function_uses_feature_vector"
            ]
        )

    def test_enum_values(
        self,
    ):
        enums = self.contract[
            "enum_contract"
        ]

        self.assertEqual(
            enums[
                "task_classes"
            ],
            {
                "IR_CLASS_ACTIVITY":
                    0,

                "IR_CLASS_FALLING":
                    1,
            },
        )

        self.assertEqual(
            enums[
                "trust_states"
            ][
                "IR_TRUST_VALID"
            ],
            0,
        )

        self.assertEqual(
            enums[
                "trust_states"
            ][
                "IR_TRUST_OOD_UNKNOWN"
            ],
            1,
        )

        self.assertEqual(
            enums[
                "trust_states"
            ][
                "IR_TRUST_INTEGRITY_ALERT"
            ],
            2,
        )

    def test_ood_threshold_float32_bits(
        self,
    ):
        numeric = self.contract[
            "numeric_contract"
        ]

        self.assertEqual(
            numeric[
                "ood_threshold_decimal"
            ],
            0.00914505124092102,
        )

        self.assertEqual(
            numeric[
                "ood_threshold_float32_bits"
            ],
            "0x3c15d520",
        )

        bits = struct.unpack(
            "<I",
            struct.pack(
                "<f",
                numeric[
                    "ood_threshold_decimal"
                ],
            ),
        )[0]

        self.assertEqual(
            bits,
            0x3C15D520,
        )

    def test_historical_bias_float32_bits(
        self,
    ):
        task = self.contract[
            "historical_task_decision_contract"
        ]

        self.assertEqual(
            task[
                "threshold"
            ],
            0.9,
        )

        self.assertEqual(
            task[
                "threshold_float32_bits"
            ],
            "0x3f666666",
        )

    def test_historical_task_rule_not_argmax(
        self,
    ):
        task = self.contract[
            "historical_task_decision_contract"
        ]

        self.assertEqual(
            task[
                "binary_equivalent_rule"
            ],
            "Falling iff P(Falling) > 0.9; Activity otherwise",
        )

        self.assertTrue(
            task[
                "uncertain_argmax_falling_may_still_return_activity"
            ]
        )

        self.assertFalse(
            task[
                "plain_argmax_may_replace_historical_rule"
            ]
        )

    def test_ood_rule_and_equality(
        self,
    ):
        ood = self.contract[
            "ood_contract"
        ]

        self.assertEqual(
            ood[
                "unknown_condition"
            ],
            "ood_margin < threshold",
        )

        self.assertEqual(
            ood[
                "accepted_condition"
            ],
            "ood_margin >= threshold",
        )

        self.assertTrue(
            ood[
                "equality_at_threshold_accepted"
            ]
        )

        self.assertFalse(
            ood[
                "feature_vector_used"
            ]
        )

    def test_integrity_mask_exact(
        self,
    ):
        integrity = self.contract[
            "integrity_mask_contract"
        ]

        self.assertEqual(
            integrity[
                "IR_CAUSE_FRAME_GAP"
            ],
            1,
        )

        self.assertEqual(
            integrity[
                "IR_SUPPORTED_HARD_CAUSE_MASK"
            ],
            1,
        )

        self.assertTrue(
            integrity[
                "frame_gap_input_is_already_hard_qualified"
            ]
        )

        self.assertFalse(
            integrity[
                "portable_c_core_may_qualify_raw_counter_evidence"
            ]
        )

        self.assertFalse(
            integrity[
                "channel_freeze_enters_hard_mask"
            ]
        )

        self.assertFalse(
            integrity[
                "timing_observation_enters_hard_mask"
            ]
        )

    def test_precedence_exact(
        self,
    ):
        observed = [
            row[
                "trust_state"
            ]
            for row in self.contract[
                "decision_precedence"
            ]
        ]

        self.assertEqual(
            observed,
            [
                "IR_TRUST_INTEGRITY_ALERT",
                "IR_TRUST_OOD_UNKNOWN",
                "IR_TRUST_VALID",
            ],
        )

    def test_suspects_diagnostic_only(
        self,
    ):
        suspect = self.contract[
            "suspect_contract"
        ]

        self.assertFalse(
            suspect[
                "changes_primary_trust_state"
            ]
        )

        self.assertTrue(
            suspect[
                "returned_unchanged_on_success"
            ]
        )

    def test_error_contract(
        self,
    ):
        errors = self.contract[
            "error_contract"
        ]

        self.assertEqual(
            errors[
                "unsupported_hard_cause_bit"
            ],
            "IR_STATUS_UNSUPPORTED_HARD_CAUSE",
        )

        self.assertFalse(
            errors[
                "errors_are_trust_states"
            ]
        )

        self.assertEqual(
            errors[
                "output_on_non_ok_status"
            ],
            "must_remain_unmodified",
        )

    def test_predeclared_cases(
        self,
    ):
        cases = {
            row[
                "id"
            ]:
                row
            for row in self.contract[
                "predeclared_semantic_cases"
            ]
        }

        self.assertEqual(
            cases[
                "HISTORICAL_RULE_NOT_ARGMAX"
            ][
                "expected_task_prediction"
            ],
            0,
        )

        self.assertEqual(
            cases[
                "CONFIDENT_FALLING"
            ][
                "expected_task_prediction"
            ],
            1,
        )

        self.assertEqual(
            cases[
                "OOD_THRESHOLD_EQUALITY"
            ][
                "expected_trust_state"
            ],
            "IR_TRUST_VALID",
        )

        self.assertEqual(
            cases[
                "INTEGRITY_PRECEDES_OOD"
            ][
                "expected_trust_state"
            ],
            "IR_TRUST_INTEGRITY_ALERT",
        )

    def test_future_parity_scope(
        self,
    ):
        parity = self.contract[
            "future_parity_validation_contract"
        ]

        self.assertTrue(
            parity[
                "python_reference_parity_required"
            ]
        )

        self.assertFalse(
            parity[
                "checkpoint_required_for_parity"
            ]
        )

        self.assertFalse(
            parity[
                "dataset_required_for_parity"
            ]
        )

        self.assertTrue(
            parity[
                "must_test_threshold_equality"
            ]
        )

        self.assertTrue(
            parity[
                "must_test_output_unmodified_on_error"
            ]
        )

    def test_upstream_model_boundary(
        self,
    ):
        upstream = self.contract[
            "upstream_model_contract"
        ]

        self.assertFalse(
            upstream[
                "portable_c_core_calls_model"
            ]
        )

        self.assertTrue(
            upstream[
                "logits_must_come_from_exactly_one_task_model_forward"
            ]
        )

        self.assertFalse(
            upstream[
                "second_task_model_forward_allowed"
            ]
        )

        self.assertFalse(
            upstream[
                "feature_vector_needed"
            ]
        )

    def test_no_stm32_claim_yet(
        self,
    ):
        boundary = self.contract[
            "claim_boundary"
        ]

        for key in (
            "historical_firmware_claim_allowed",
            "historical_embedded_model_claim_allowed",
            "stm32_latency_claim_allowed",
            "stm32_cycles_claim_allowed",
            "stm32_flash_claim_allowed",
            "stm32_ram_claim_allowed",
            "stm32_energy_claim_allowed",
            "host_native_c_timing_may_be_relabelled_stm32_timing",
        ):
            self.assertFalse(
                boundary[
                    key
                ]
            )

    def test_scientific_boundary_closed(
        self,
    ):
        boundary = self.contract[
            "scientific_boundary"
        ]

        for key in (
            "ood_threshold_may_change",
            "ood_method_may_change",
            "historical_prediction_bias_may_change",
            "integrity_operating_point_may_change",
            "protected_final_test_may_be_reopened",
            "host_resource_benchmark_may_be_rerun_for_tuning",
            "classifier_bypass_allowed",
            "second_task_model_forward_allowed",
        ):
            self.assertFalse(
                boundary[
                    key
                ]
            )


if __name__ == "__main__":
    unittest.main()
