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

MODULE_PATH = (
    ROOT
    / "experiments/04_runtime/"
      "build_runtime_integration_contract_v1.py"
)

SPEC = importlib.util.spec_from_file_location(
    "build_runtime_integration_contract_v1",
    MODULE_PATH,
)

if (
    SPEC is None
    or SPEC.loader is None
):
    raise RuntimeError(
        "Unable to import runtime contract builder"
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


class RuntimeIntegrationContractV1Tests(
    unittest.TestCase
):

    def test_git_and_source_anchors(
        self,
    ):
        MOD.verify_git_anchors()
        MOD.verify_source_anchors()

    def test_historical_decision_api(
        self,
    ):
        MOD.verify_historical_decision_api()

    def test_model_api(
        self,
    ):
        MOD.verify_model_api()

    def test_frozen_operating_points(
        self,
    ):
        MOD.verify_frozen_operating_points()

    def test_implementation_is_not_created_yet(
        self,
    ):
        MOD.verify_implementation_absent()

    def test_exact_historical_task_rule(
        self,
    ):
        contract = MOD.build_contract()

        task = contract[
            "historical_task_decision_contract"
        ]

        self.assertEqual(
            task[
                "function"
            ],
            "decision_from_logits",
        )

        self.assertEqual(
            task[
                "prediction_bias"
            ],
            0.9,
        )

        self.assertTrue(
            task[
                "comparison_is_strict"
            ]
        )

        self.assertFalse(
            task[
                "plain_argmax_may_replace_historical_decision"
            ]
        )

    def test_exact_integrity_boundary(
        self,
    ):
        contract = MOD.build_contract()

        integrity = contract[
            "integrity_runtime_contract"
        ]

        self.assertEqual(
            integrity[
                "supported_v1_hard_cause_mask"
            ],
            [
                "FRAME_GAP",
            ],
        )

        self.assertFalse(
            integrity[
                "channel_freeze_enters_hard_set"
            ]
        )

        self.assertFalse(
            integrity[
                "timing_observation_enters_hard_set"
            ]
        )

        self.assertFalse(
            integrity[
                "unverified_or_derived_counter_gap_enters_hard_set"
            ]
        )

    def test_exact_ood_gate(
        self,
    ):
        contract = MOD.build_contract()

        ood = contract[
            "ood_runtime_contract"
        ]

        self.assertEqual(
            ood[
                "method"
            ],
            "top_two_logit_margin",
        )

        self.assertEqual(
            ood[
                "threshold"
            ],
            0.00914505124092102,
        )

        self.assertEqual(
            ood[
                "unknown_rule"
            ],
            "margin < threshold",
        )

        self.assertTrue(
            ood[
                "ties_at_threshold_accepted"
            ]
        )

        self.assertFalse(
            ood[
                "feature_vector_used"
            ]
        )

        self.assertFalse(
            ood[
                "second_model_forward_used"
            ]
        )

    def test_decision_precedence(
        self,
    ):
        contract = MOD.build_contract()

        states = [
            item[
                "trust_state"
            ]
            for item in contract[
                "decision_precedence"
            ]
        ]

        self.assertEqual(
            states,
            [
                "INTEGRITY_ALERT",
                "OOD_UNKNOWN",
                "VALID",
            ],
        )

    def test_task_prediction_always_returned(
        self,
    ):
        contract = MOD.build_contract()

        output = contract[
            "output_contract"
        ]

        self.assertEqual(
            output[
                "task_prediction"
            ],
            "always_present",
        )

        self.assertTrue(
            output[
                "integrity_alert_does_not_suppress_task_prediction"
            ]
        )

        self.assertTrue(
            output[
                "ood_unknown_does_not_suppress_task_prediction"
            ]
        )

    def test_one_forward_contract(
        self,
    ):
        contract = MOD.build_contract()

        model = contract[
            "task_model_contract"
        ]

        self.assertEqual(
            model[
                "full_task_model_invocations_per_window"
            ],
            1,
        )

        self.assertFalse(
            model[
                "second_full_task_model_forward_allowed"
            ]
        )

        self.assertEqual(
            model[
                "selected_python_model_api"
            ],
            "Date2025CNN400.forward",
        )

    def test_no_deployment_claim_yet(
        self,
    ):
        contract = MOD.build_contract()

        boundary = contract[
            "resource_evidence_boundary"
        ]

        self.assertFalse(
            boundary[
                "exact_stm32_latency_claimed_at_contract_freeze"
            ]
        )

        self.assertFalse(
            boundary[
                "exact_stm32_flash_overhead_claimed_at_contract_freeze"
            ]
        )

        self.assertFalse(
            boundary[
                "exact_stm32_ram_overhead_claimed_at_contract_freeze"
            ]
        )

        self.assertFalse(
            boundary[
                "tracked_embedded_firmware_present_at_contract_freeze"
            ]
        )

    def test_content_hash_roundtrip(
        self,
    ):
        contract = MOD.build_contract()

        stored = contract[
            "content_sha256"
        ]

        payload = deepcopy(
            contract
        )

        payload.pop(
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


if __name__ == "__main__":
    unittest.main()
