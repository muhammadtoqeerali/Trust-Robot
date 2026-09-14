from __future__ import annotations

import ast
import importlib.util
import json
import sys
import unittest
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

import numpy as np


ROOT = Path(
    __file__
).resolve().parents[1]

MODULE_PATH = (
    ROOT
    / "experiments/03_ood/"
      "evaluate_ood_calibration_v1.py"
)

SPEC = importlib.util.spec_from_file_location(
    "evaluate_ood_calibration_v1",
    MODULE_PATH,
)

if (
    SPEC is None
    or SPEC.loader is None
):
    raise RuntimeError(
        "Unable to import OOD calibration evaluator"
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


class OODCalibrationEvaluatorV1Tests(
    unittest.TestCase
):

    def test_protocol_frozen_anchor(
        self,
    ):
        data = MOD.load_protocol()

        self.assertEqual(
            data[
                "content_sha256"
            ],
            MOD.PROTOCOL_CONTENT_SHA256,
        )

        self.assertEqual(
            MOD.file_sha256(
                MOD.PROTOCOL
            ),
            MOD.PROTOCOL_RAW_SHA256,
        )

    def test_frozen_inputs(
        self,
    ):
        MOD.verify_frozen_inputs()

    def test_exact_calibration_registry_population(
        self,
    ):
        rows = MOD.calibration_rows()

        self.assertEqual(
            len(
                rows
            ),
            447,
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
            89868,
        )

    def test_finite_sample_small_stratum(
        self,
    ):
        values = [
            float(
                value
            )
            for value in range(
                81
            )
        ]

        self.assertEqual(
            MOD.stratum_rank(
                81
            ),
            0,
        )

        self.assertEqual(
            MOD.stratum_boundary(
                values
            ),
            0.0,
        )

    def test_finite_sample_global_constraint(
        self,
    ):
        strata = {
            (
                "A",
                "Activity",
            ):
                [
                    float(
                        value
                    )
                    for value in range(
                        100
                    )
                ],

            (
                "B",
                "Falling",
            ):
                [
                    float(
                        value
                    )
                    for value in range(
                        50,
                        250,
                    )
                ],
        }

        threshold, boundaries = (
            MOD.finite_sample_threshold(
                strata
            )
        )

        self.assertEqual(
            threshold,
            min(
                boundaries.values()
            ),
        )

        for values in strata.values():
            self.assertGreaterEqual(
                MOD.empirical_acceptance(
                    values,
                    threshold,
                ),
                0.99,
            )

    def test_threshold_equality_is_accepted(
        self,
    ):
        self.assertEqual(
            MOD.empirical_acceptance(
                [
                    0.1,
                    0.2,
                    0.2,
                    0.3,
                ],
                0.2,
            ),
            0.75,
        )

    def test_task_metric_bucket(
        self,
    ):
        bucket = (
            MOD.empty_task_bucket()
        )

        MOD.update_task_bucket(
            bucket,
            np.asarray(
                [
                    0,
                    0,
                    1,
                    1,
                ],
                dtype=np.int64,
            ),
            np.asarray(
                [
                    0,
                    1,
                    0,
                    1,
                ],
                dtype=np.int64,
            ),
        )

        metrics = (
            MOD.finalize_task_bucket(
                bucket
            )
        )

        self.assertEqual(
            metrics[
                "confusion_matrix_activity_falling"
            ],
            [
                [
                    1,
                    1,
                ],
                [
                    1,
                    1,
                ],
            ],
        )

        self.assertEqual(
            metrics[
                "accuracy"
            ],
            0.5,
        )

    def test_exact_single_forward_api_call(
        self,
    ):
        source = MODULE_PATH.read_text()

        tree = ast.parse(
            source
        )

        forward_with_features_calls = []

        forbidden_forward_calls = []

        for node in ast.walk(
            tree
        ):
            if not isinstance(
                node,
                ast.Call,
            ):
                continue

            func = node.func

            if isinstance(
                func,
                ast.Attribute,
            ):
                if (
                    func.attr
                    == "forward_with_features"
                ):
                    forward_with_features_calls.append(
                        node
                    )

                if func.attr == "forward":
                    forbidden_forward_calls.append(
                        node
                    )

        self.assertEqual(
            len(
                forward_with_features_calls
            ),
            1,
        )

        self.assertEqual(
            len(
                forbidden_forward_calls
            ),
            0,
        )

    def test_evaluator_source_has_no_candidate_score_search(
        self,
    ):
        source = MODULE_PATH.read_text()

        forbidden = (
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

    def test_output_artifacts_absent_before_first_run(
        self,
    ):
        self.assertFalse(
            MOD.RESULT.exists()
        )

        self.assertFalse(
            MOD.OPERATING_POINT_CANDIDATE.exists()
        )

    def test_evaluator_tag_name(
        self,
    ):
        self.assertEqual(
            MOD.EVALUATOR_TAG,
            "ood-calibration-evaluator-v1",
        )

    def test_synthetic_result_hash_roundtrip(
        self,
    ):
        payload = {
            "a":
                1,
            "b":
                [
                    2,
                    3,
                ],
        }

        digest = (
            MOD.canonical_digest(
                payload
            )
        )

        normalized = json.loads(
            json.dumps(
                deepcopy(
                    payload
                ),
                separators=(",", ":"),
                allow_nan=False,
            )
        )

        expected = sha256(
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
            digest,
            expected,
        )


if __name__ == "__main__":
    unittest.main()
