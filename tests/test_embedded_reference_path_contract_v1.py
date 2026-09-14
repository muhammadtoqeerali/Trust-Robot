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
      "build_embedded_reference_path_contract_v1.py"
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


SPEC = importlib.util.spec_from_file_location(
    "build_embedded_reference_path_contract_v1",
    BUILDER,
)

if (
    SPEC is None
    or SPEC.loader is None
):
    raise RuntimeError(
        "Unable to import embedded path builder"
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


def verify_content_hash(
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

    return stored, computed


class EmbeddedReferencePathContractV1Tests(
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

    def test_git_and_frozen_inputs(
        self,
    ):
        MOD.verify_git_anchors()
        MOD.verify_frozen_inputs()

    def test_live_archaeology_still_supports_decision(
        self,
    ):
        evidence = (
            MOD.collect_archaeology()
        )

        MOD.validate_archaeology(
            evidence
        )

    def test_receipt_content_hash(
        self,
    ):
        stored, computed = (
            verify_content_hash(
                self.receipt
            )
        )

        self.assertEqual(
            stored,
            computed,
        )

    def test_contract_content_hash(
        self,
    ):
        stored, computed = (
            verify_content_hash(
                self.contract
            )
        )

        self.assertEqual(
            stored,
            computed,
        )

    def test_protected_run_has_no_embedded_export(
        self,
    ):
        observed = self.receipt[
            "observations"
        ]

        self.assertEqual(
            observed[
                "protected_run_file_count"
            ],
            8,
        )

        self.assertEqual(
            observed[
                "protected_run_onnx_count"
            ],
            0,
        )

        self.assertEqual(
            observed[
                "protected_run_ioc_count"
            ],
            0,
        )

        self.assertEqual(
            observed[
                "protected_run_embedded_file_count"
            ],
            0,
        )

    def test_broader_archaeology_strong_counts_zero(
        self,
    ):
        observed = self.receipt[
            "observations"
        ]

        for key in (
            "exact_timestamp_path_hit_count_in_historical_home",
            "cube_project_marker_count",
            "strong_stm32_firmware_file_count",
            "model_to_mcu_generated_file_count",
            "stm32_source_symbol_hit_count",
            "protected_400ms_export_candidate_count",
        ):
            self.assertEqual(
                observed[
                    key
                ],
                0,
            )

    def test_absence_claim_is_narrow(
        self,
    ):
        text = self.contract[
            "historical_recovery_decision"
        ][
            "absence_interpretation"
        ]

        self.assertIn(
            "searched workstation evidence",
            text,
        )

        self.assertIn(
            "does not prove",
            text,
        )

    def test_exact_historical_deployment_claim_forbidden(
        self,
    ):
        decision = self.contract[
            "historical_recovery_decision"
        ]

        self.assertFalse(
            decision[
                "exact_historical_deployed_firmware_claim_allowed"
            ]
        )

        self.assertFalse(
            decision[
                "exact_historical_embedded_model_claim_allowed"
            ]
        )

    def test_prospective_reference_required(
        self,
    ):
        prospective = self.contract[
            "prospective_reference_path"
        ]

        self.assertTrue(
            prospective[
                "required"
            ]
        )

        self.assertEqual(
            prospective[
                "lineage_label"
            ],
            "prospective_embedded_reference_implementation",
        )

        self.assertFalse(
            prospective[
                "may_be_described_as_exact_historical_deployment"
            ]
        )

    def test_exact_frozen_runtime_semantics(
        self,
    ):
        semantics = self.contract[
            "runtime_semantics_to_preserve"
        ]

        self.assertEqual(
            semantics[
                "window_shape"
            ],
            [1, 40, 9],
        )

        self.assertEqual(
            semantics[
                "full_task_model_invocations_per_window"
            ],
            1,
        )

        self.assertFalse(
            semantics[
                "second_full_task_model_forward_allowed"
            ]
        )

        self.assertEqual(
            semantics[
                "historical_prediction_bias"
            ],
            0.9,
        )

        self.assertEqual(
            semantics[
                "ood_threshold"
            ],
            0.00914505124092102,
        )

        self.assertFalse(
            semantics[
                "ood_feature_vector_used"
            ]
        )

    def test_first_c_stage_is_semantic_core_only(
        self,
    ):
        stage = self.contract[
            "first_embedded_implementation_stage"
        ]

        self.assertTrue(
            stage[
                "host_compiled_semantic_parity_allowed"
            ]
        )

        self.assertFalse(
            stage[
                "full_cnn_export_included"
            ]
        )

        self.assertFalse(
            stage[
                "stm32_hal_integration_included"
            ]
        )

        self.assertFalse(
            stage[
                "hardware_flash_included"
            ]
        )

    def test_new_model_export_requires_separate_validation(
        self,
    ):
        boundary = self.contract[
            "future_model_embedding_boundary"
        ]

        self.assertFalse(
            boundary[
                "surviving_400ms_embedded_export_available"
            ]
        )

        self.assertTrue(
            boundary[
                "new_model_export_must_be_labeled_prospective"
            ]
        )

        self.assertTrue(
            boundary[
                "new_model_export_requires_numerical_parity_validation"
            ]
        )

    def test_no_stm32_resource_claim_yet(
        self,
    ):
        boundary = self.contract[
            "resource_claim_boundary"
        ]

        for key in (
            "stm32_latency_currently_claimable",
            "stm32_cycles_currently_claimable",
            "stm32_flash_currently_claimable",
            "stm32_ram_currently_claimable",
            "stm32_energy_currently_claimable",
        ):
            self.assertFalse(
                boundary[
                    key
                ]
            )

        self.assertTrue(
            boundary[
                "real_target_evidence_required_before_stm32_claim"
            ]
        )

    def test_scientific_selection_remains_closed(
        self,
    ):
        boundary = self.contract[
            "scientific_boundary"
        ]

        self.assertFalse(
            boundary[
                "ood_threshold_may_change"
            ]
        )

        self.assertFalse(
            boundary[
                "ood_method_may_change"
            ]
        )

        self.assertFalse(
            boundary[
                "integrity_operating_point_may_change"
            ]
        )

        self.assertFalse(
            boundary[
                "protected_final_test_may_be_reopened"
            ]
        )

        self.assertFalse(
            boundary[
                "classifier_bypass_allowed"
            ]
        )


if __name__ == "__main__":
    unittest.main()
