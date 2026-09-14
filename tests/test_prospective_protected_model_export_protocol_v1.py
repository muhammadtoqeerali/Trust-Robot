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
      "build_prospective_protected_model_export_protocol_v1.py"
)

PROTOCOL = (
    ROOT
    / "configs/embedded/"
      "prospective_protected_model_export_protocol_v1.json"
)


SPEC = importlib.util.spec_from_file_location(
    "build_prospective_protected_model_export_protocol_v1",
    BUILDER,
)

if SPEC is None or SPEC.loader is None:
    raise RuntimeError(
        "Unable to import export protocol builder"
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


class ProspectiveProtectedModelExportProtocolV1Tests(
    unittest.TestCase
):

    @classmethod
    def setUpClass(
        cls,
    ):
        cls.p = json.loads(
            PROTOCOL.read_text()
        )

    def test_git_anchors(
        self,
    ):
        MOD.verify_git_anchors()

    def test_frozen_inputs(
        self,
    ):
        MOD.verify_frozen_inputs()

    def test_future_outputs_absent(
        self,
    ):
        MOD.verify_future_outputs_absent()

    def test_content_hash_roundtrip(
        self,
    ):
        payload = deepcopy(
            self.p
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
        lineage = self.p[
            "lineage"
        ]

        self.assertEqual(
            lineage[
                "artifact_label"
            ],
            "prospective_protected_model_export",
        )

        self.assertFalse(
            lineage[
                "exact_historical_deployment_artifact"
            ]
        )

        self.assertTrue(
            lineage[
                "source_checkpoint_is_surviving_historical_checkpoint"
            ]
        )

    def test_float32_onnx_only(
        self,
    ):
        scope = self.p[
            "export_scope"
        ]

        self.assertEqual(
            scope[
                "format"
            ],
            "ONNX",
        )

        self.assertEqual(
            scope[
                "precision"
            ],
            "float32",
        )

        self.assertEqual(
            scope[
                "opset_version"
            ],
            13,
        )

        self.assertFalse(
            scope[
                "quantization_included"
            ]
        )

        self.assertTrue(
            scope[
                "quantization_deferred_to_separate_protocol"
            ]
        )

    def test_fixed_tensor_contract(
        self,
    ):
        tensor = self.p[
            "tensor_contract"
        ]

        self.assertEqual(
            tensor[
                "input_shape"
            ],
            [1, 40, 9],
        )

        self.assertEqual(
            tensor[
                "output_shape"
            ],
            [1, 2],
        )

        self.assertEqual(
            tensor[
                "input_name"
            ],
            "imu_window",
        )

        self.assertEqual(
            tensor[
                "output_name"
            ],
            "logits",
        )

    def test_no_feature_output(
        self,
    ):
        scope = self.p[
            "export_scope"
        ]

        self.assertFalse(
            scope[
                "feature_output_included"
            ]
        )

        self.assertTrue(
            scope[
                "logits_only_output"
            ]
        )

    def test_pinned_checkpoint_loader(
        self,
    ):
        loading = self.p[
            "checkpoint_loading_contract"
        ]

        self.assertTrue(
            loading[
                "checkpoint_sha256_must_be_verified_before_deserialization"
            ]
        )

        self.assertFalse(
            loading[
                "direct_unpinned_torch_load_allowed"
            ]
        )

        self.assertTrue(
            loading[
                "model_must_be_eval_mode"
            ]
        )

    def test_deterministic_synthetic_vectors_only(
        self,
    ):
        parity = self.p[
            "deterministic_parity_input_contract"
        ]

        for key in (
            "protected_dataset_used",
            "calibration_dataset_used",
            "final_test_dataset_used",
            "external_recording_dataset_used",
        ):
            self.assertFalse(
                parity[
                    key
                ]
            )

        self.assertEqual(
            parity[
                "structured_vector_count"
            ],
            4,
        )

        self.assertEqual(
            parity[
                "modular_vector_count"
            ],
            64,
        )

        self.assertEqual(
            parity[
                "total_vector_count"
            ],
            68,
        )

        self.assertTrue(
            parity[
                "no_random_generator_required"
            ]
        )

    def test_numerical_tolerances_fixed_before_export(
        self,
    ):
        parity = self.p[
            "numerical_parity_contract"
        ]

        self.assertEqual(
            parity[
                "absolute_tolerance"
            ],
            1.0e-5,
        )

        self.assertEqual(
            parity[
                "relative_tolerance"
            ],
            1.0e-5,
        )

        self.assertTrue(
            parity[
                "all_logit_elements_must_pass"
            ]
        )

        self.assertFalse(
            parity[
                "tolerance_may_change_after_export_outputs_are_seen"
            ]
        )

    def test_decision_parity_exact(
        self,
    ):
        decision = self.p[
            "decision_parity_contract"
        ]

        self.assertTrue(
            decision[
                "historical_task_prediction_exact_match_required"
            ]
        )

        self.assertTrue(
            decision[
                "ood_trust_state_exact_match_required"
            ]
        )

        self.assertEqual(
            decision[
                "decision_mismatch_tolerance"
            ],
            0,
        )

        self.assertEqual(
            decision[
                "ood_threshold"
            ],
            0.00914505124092102,
        )

        self.assertTrue(
            decision[
                "ood_threshold_equality_accepted"
            ]
        )

    def test_graph_validation(
        self,
    ):
        graph = self.p[
            "graph_validation_contract"
        ]

        self.assertTrue(
            graph[
                "onnx_checker_required"
            ]
        )

        self.assertTrue(
            graph[
                "onnx_runtime_cpu_execution_required"
            ]
        )

        self.assertTrue(
            graph[
                "single_graph_output_required"
            ]
        )

        self.assertTrue(
            graph[
                "feature_output_forbidden"
            ]
        )

        self.assertTrue(
            graph[
                "dynamic_dimension_forbidden"
            ]
        )

    def test_one_forward_boundary(
        self,
    ):
        boundary = self.p[
            "single_forward_runtime_boundary"
        ]

        self.assertTrue(
            boundary[
                "exported_model_represents_one_task_forward"
            ]
        )

        self.assertFalse(
            boundary[
                "second_model_forward_for_ood_forbidden"
            ]
            is False
        )

        self.assertTrue(
            boundary[
                "feature_vector_for_ood_forbidden"
            ]
        )

    def test_failure_cannot_retune_science(
        self,
    ):
        failure = self.p[
            "failure_policy"
        ]

        for key in (
            "failed_export_may_change_ood_threshold",
            "failed_export_may_change_historical_task_rule",
            "failed_export_may_change_integrity_operating_point",
            "failed_export_may_reopen_protected_final_test",
            "failed_parity_may_loosen_tolerance_after_outputs_seen",
        ):
            self.assertFalse(
                failure[
                    key
                ]
            )

    def test_no_stm32_claim_from_onnx(
        self,
    ):
        claims = self.p[
            "claim_boundary"
        ]

        for key in (
            "validated_onnx_may_be_called_exact_historical_deployed_model",
            "validated_onnx_may_be_called_exact_historical_firmware",
            "onnx_validation_alone_proves_stm32_importability",
            "onnx_validation_alone_proves_stm32_numerical_parity",
            "onnx_validation_alone_proves_stm32_latency",
            "onnx_validation_alone_proves_stm32_flash",
            "onnx_validation_alone_proves_stm32_ram",
            "onnx_validation_alone_proves_stm32_energy",
        ):
            self.assertFalse(
                claims[
                    key
                ]
            )

    def test_scientific_boundary_closed(
        self,
    ):
        science = self.p[
            "scientific_boundary"
        ]

        for key in (
            "ood_threshold_may_change",
            "ood_method_may_change",
            "historical_prediction_bias_may_change",
            "integrity_operating_point_may_change",
            "classifier_bypass_allowed",
            "second_task_forward_allowed",
            "protected_final_test_may_be_reopened",
            "host_resource_benchmark_may_be_rerun",
            "export_result_may_be_used_for_scientific_selection",
        ):
            self.assertFalse(
                science[
                    key
                ]
            )


if __name__ == "__main__":
    unittest.main()
