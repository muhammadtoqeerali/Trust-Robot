from __future__ import annotations

import ast
import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(
    __file__
).resolve().parents[1]

MODULE_PATH = (
    ROOT
    / "experiments/03_ood/"
      "evaluate_ood_final_test_v1.py"
)

SPEC = importlib.util.spec_from_file_location(
    "evaluate_ood_final_test_v1",
    MODULE_PATH,
)

if (
    SPEC is None
    or SPEC.loader is None
):
    raise RuntimeError(
        "Unable to import OOD final-test evaluator"
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


class OODFinalTestEvaluatorV1Tests(
    unittest.TestCase
):

    def test_frozen_inputs(
        self,
    ):
        MOD.verify_frozen_inputs()

    def test_protocol_anchor(
        self,
    ):
        protocol = (
            MOD.load_final_test_protocol()
        )

        self.assertEqual(
            protocol[
                "content_sha256"
            ],
            MOD.FINAL_TEST_PROTOCOL_CONTENT_SHA256,
        )

        self.assertEqual(
            MOD.file_sha256(
                MOD.FINAL_TEST_PROTOCOL
            ),
            MOD.FINAL_TEST_PROTOCOL_RAW_SHA256,
        )

    def test_operating_point_is_immutable(
        self,
    ):
        op = (
            MOD.load_frozen_operating_point()
        )

        self.assertEqual(
            op[
                "selected_method"
            ],
            "top_two_logit_margin",
        )

        self.assertEqual(
            op[
                "threshold"
            ],
            0.00914505124092102,
        )

    def test_exact_final_registry_population(
        self,
    ):
        rows = MOD.final_test_rows()

        self.assertEqual(
            len(
                rows
            ),
            1116,
        )

        self.assertEqual(
            sum(
                int(
                    row[
                        "historical_windows"
                    ]
                )
                for row in rows
            ),
            366507,
        )

    def test_exact_dataset_denominators(
        self,
    ):
        rows = MOD.final_test_rows()

        observed = {}

        for dataset in (
            "KFALL",
            "UNIVRFALL",
            "ONFIELD",
        ):
            observed[
                dataset
            ] = sum(
                int(
                    row[
                        "historical_windows"
                    ]
                )
                for row in rows
                if row[
                    "dataset"
                ]
                == dataset
            )

        self.assertEqual(
            observed,
            {
                "KFALL":
                    27068,

                "UNIVRFALL":
                    7532,

                "ONFIELD":
                    331907,
            },
        )

    def test_v1b_dependency_is_pinned(
        self,
    ):
        self.assertEqual(
            MOD.file_sha256(
                MOD.V1B_SOURCE
            ),
            MOD.OOD_CALIBRATION_EVALUATOR_V1B_RAW_SHA256,
        )

        v1b = MOD.load_v1b_module()

        self.assertTrue(
            hasattr(
                v1b,
                "load_protected_model",
            )
        )

        self.assertTrue(
            hasattr(
                v1b,
                "normalize_label",
            )
        )

    def test_final_output_artifacts_absent_before_run(
        self,
    ):
        self.assertFalse(
            MOD.RESULT.exists()
        )

        self.assertFalse(
            MOD.FINAL_RECEIPT.exists()
        )

    def test_no_threshold_selection_algorithm(
        self,
    ):
        source = MODULE_PATH.read_text()

        forbidden = (
            "finite_sample_threshold",
            "stratum_boundary",
            "stratum_rank",
            "minimum_q",
            "min(q_s)",
            "maximum_softmax_probability",
            "prototype_cosine",
            "diagonal_standardized_feature_distance",
            "tcuq",
        )

        for term in forbidden:
            self.assertNotIn(
                term,
                source,
            )

    def test_exact_single_task_forward_call_site(
        self,
    ):
        source = MODULE_PATH.read_text()

        tree = ast.parse(
            source
        )

        calls = []

        for node in ast.walk(
            tree
        ):
            if not isinstance(
                node,
                ast.Call,
            ):
                continue

            if (
                isinstance(
                    node.func,
                    ast.Attribute,
                )
                and node.func.attr
                == "forward_with_features"
            ):
                calls.append(
                    node
                )

        self.assertEqual(
            len(
                calls
            ),
            1,
        )

    def test_final_evaluator_does_not_directly_deserialize_checkpoint(
        self,
    ):
        source = MODULE_PATH.read_text()

        self.assertNotIn(
            "torch.load(",
            source,
        )

        self.assertIn(
            "v1b.load_protected_model()",
            source,
        )

    def test_score_is_fixed_margin_only(
        self,
    ):
        source = MODULE_PATH.read_text()

        tree = ast.parse(
            source
        )

        fixed_margin_comparisons = []

        for node in ast.walk(
            tree
        ):
            if not isinstance(
                node,
                ast.Compare,
            ):
                continue

            if len(
                node.ops
            ) != 1:
                continue

            if len(
                node.comparators
            ) != 1:
                continue

            if not isinstance(
                node.ops[0],
                ast.Lt,
            ):
                continue

            if not isinstance(
                node.left,
                ast.Name,
            ):
                continue

            if node.left.id != "margin_np":
                continue

            comparator = node.comparators[
                0
            ]

            if not isinstance(
                comparator,
                ast.Name,
            ):
                continue

            if comparator.id != "FROZEN_THRESHOLD":
                continue

            fixed_margin_comparisons.append(
                node
            )

        self.assertEqual(
            len(
                fixed_margin_comparisons
            ),
            1,
        )

        self.assertEqual(
            MOD.FROZEN_THRESHOLD,
            0.00914505124092102,
        )

        self.assertIn(
            "top_two_logit_margin",
            source,
        )

    def test_evaluator_tag_name(
        self,
    ):
        self.assertEqual(
            MOD.EVALUATOR_TAG,
            "ood-final-test-evaluator-v1",
        )


if __name__ == "__main__":
    unittest.main()
