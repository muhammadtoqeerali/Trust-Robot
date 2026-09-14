from __future__ import annotations

import ast
import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(
    __file__
).resolve().parents[1]

EXPORTER = (
    ROOT
    / "experiments/05_embedded/"
      "export_protected_model_onnx_v1.py"
)

ONNX_ARTIFACT = (
    ROOT
    / "artifacts/embedded/prospective/"
      "date2025_cnn400_fp32_v1.onnx"
)

RESULT = (
    ROOT
    / "results/raw/"
      "prospective_model_export_v1_candidate.json"
)

RECEIPT = (
    ROOT
    / "data/manifests/"
      "prospective_model_export_result_receipt_v1.json"
)


SPEC = importlib.util.spec_from_file_location(
    "export_protected_model_onnx_v1",
    EXPORTER,
)

if SPEC is None or SPEC.loader is None:
    raise RuntimeError(
        "Unable to import exporter implementation"
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


class ProspectiveFP32ONNXExporterV1Tests(
    unittest.TestCase
):

    def test_protocol_and_git_anchors(
        self,
    ):
        MOD.verify_git_anchors()

        protocol = MOD.verify_protocol()

        self.assertEqual(
            protocol[
                "protocol_id"
            ],
            "PROSPECTIVE_PROTECTED_MODEL_EXPORT_PROTOCOL_V1",
        )

    def test_source_anchors_static_only(
        self,
    ):
        MOD.verify_source_anchors()

    def test_export_outputs_absent_before_execution(
        self,
    ):
        self.assertFalse(
            ONNX_ARTIFACT.exists()
        )

        self.assertFalse(
            RESULT.exists()
        )

        self.assertFalse(
            RECEIPT.exists()
        )

    def test_import_does_not_require_onnx_packages(
        self,
    ):
        self.assertTrue(
            hasattr(
                MOD,
                "load_export_dependencies",
            )
        )

    def test_no_direct_unpinned_torch_load(
        self,
    ):
        source = EXPORTER.read_text(
            encoding="utf-8"
        )

        self.assertNotIn(
            "torch.load(",
            source,
        )

        self.assertIn(
            "module.load_protected_model()",
            source,
        )

    def test_no_dataset_loading(
        self,
    ):
        source = EXPORTER.read_text(
            encoding="utf-8"
        )

        self.assertNotIn(
            "np.load(",
            source,
        )

        self.assertNotIn(
            "segments.npy",
            source,
        )

        self.assertNotIn(
            "labels.npy",
            source,
        )

    def test_exact_export_configuration(
        self,
    ):
        source = EXPORTER.read_text(
            encoding="utf-8"
        )

        for term in (
            "opset_version=OPSET_VERSION",
            "dynamic_axes=None",
            "keep_initializers_as_inputs=False",
            "dynamo=False",
            "external_data=False",
            "do_constant_folding=True",
            "TrainingMode",
            "EVAL",
        ):
            self.assertIn(
                term,
                source,
            )

    def test_fixed_shapes(
        self,
    ):
        self.assertEqual(
            MOD.INPUT_SHAPE,
            (
                1,
                40,
                9,
            ),
        )

        self.assertEqual(
            MOD.OUTPUT_SHAPE,
            (
                1,
                2,
            ),
        )

    def test_exact_vector_counts(
        self,
    ):
        self.assertEqual(
            MOD.STRUCTURED_VECTOR_COUNT,
            4,
        )

        self.assertEqual(
            MOD.MODULAR_VECTOR_COUNT,
            64,
        )

        self.assertEqual(
            MOD.TOTAL_VECTOR_COUNT,
            68,
        )

        vectors = (
            MOD.parity_vectors()
        )

        self.assertEqual(
            len(
                vectors
            ),
            68,
        )

    def test_frozen_tolerances(
        self,
    ):
        self.assertEqual(
            MOD.ATOL,
            1.0e-5,
        )

        self.assertEqual(
            MOD.RTOL,
            1.0e-5,
        )

    def test_graph_checker_required(
        self,
    ):
        source = EXPORTER.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "onnx.checker.check_model(",
            source,
        )

        self.assertIn(
            "InferenceSession(",
            source,
        )

        self.assertIn(
            "CPUExecutionProvider",
            source,
        )

    def test_external_data_forbidden(
        self,
    ):
        source = EXPORTER.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "TensorProto.EXTERNAL",
            source,
        )

        self.assertIn(
            "external_data_used",
            source,
        )

    def test_exact_decision_parity_checks(
        self,
    ):
        source = EXPORTER.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "decision_from_logits(",
            source,
        )

        self.assertIn(
            "decide_from_logits(",
            source,
        )

        self.assertIn(
            "historical_task_mismatches",
            source,
        )

        self.assertIn(
            "ood_trust_mismatches",
            source,
        )

    def test_no_integrity_model_graph_input(
        self,
    ):
        self.assertEqual(
            MOD.INPUT_NAME,
            "imu_window",
        )

        self.assertEqual(
            MOD.OUTPUT_NAME,
            "logits",
        )

    def test_result_written_only_after_validation(
        self,
    ):
        source = EXPORTER.read_text(
            encoding="utf-8"
        )

        tree = ast.parse(
            source
        )

        main_node = None

        for node in tree.body:
            if (
                isinstance(
                    node,
                    ast.FunctionDef,
                )
                and node.name
                == "main"
            ):
                main_node = node
                break

        self.assertIsNotNone(
            main_node
        )

        main_text = ast.get_source_segment(
            source,
            main_node,
        )

        self.assertLess(
            main_text.index(
                "validate_graph("
            ),
            main_text.index(
                "RESULT.write_text("
            ),
        )

        self.assertLess(
            main_text.index(
                "validate_numerical_parity("
            ),
            main_text.index(
                "RESULT.write_text("
            ),
        )

    def test_no_quantization(
        self,
    ):
        source = EXPORTER.read_text(
            encoding="utf-8"
        )

        self.assertNotIn(
            "quantize_dynamic",
            source,
        )

        self.assertNotIn(
            "quantize_static",
            source,
        )

    def test_no_stm32_claim(
        self,
    ):
        source = EXPORTER.read_text(
            encoding="utf-8"
        )

        for term in (
            '"stm32_importability_claimed":\n                False',
            '"stm32_numerical_parity_claimed":\n                False',
            '"stm32_latency_claimed":\n                False',
            '"stm32_flash_claimed":\n                False',
            '"stm32_ram_claimed":\n                False',
        ):
            self.assertIn(
                term,
                source,
            )


if __name__ == "__main__":
    unittest.main()
