from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

import joblib
import numpy as np

from trust_robot.ml_synthetic_intervention_baseline import (
    CONFIG_SCHEMA,
    DEVELOPMENT_CHECK_TRAJECTORIES,
    DEVELOPMENT_TRAIN_TRAJECTORIES,
    FEATURE_COUNT,
    MODEL_NAMES,
    PROBABILITY_THRESHOLD,
    RESULT_SCHEMA,
    MLSyntheticInterventionBaselineError,
    build_models,
    build_result_contract,
    compute_binary_metrics,
    compute_per_trajectory_metrics,
    load_dataset,
    mechanism_signature_probability,
    predict_positive_probability,
)


def sample(
    *,
    partition,
    trajectory,
    label,
    sample_id,
    features,
):
    return {
        "outer_split":
            "TRAIN",

        "development_partition":
            partition,

        "trajectory":
            trajectory,

        "sample_id":
            sample_id,

        "label":
            label,

        "feature_values":
            list(
                features
            ),

        "label_is_real_physical_health_truth":
            False,

        "reference_data_used":
            False,

        "validation_data_used":
            False,

        "confirmation_data_used":
            False,

        "physical_measurement_time_used":
            False,

        "cross_modal_alignment_used":
            False,
    }


class MLSyntheticInterventionBaselineTests(
    unittest.TestCase
):
    def test_01_config_schema_constant(self):
        self.assertEqual(
            CONFIG_SCHEMA,
            "TRUST_ROBOT_M2DGR_SYNTHETIC_INTERVENTION_BASELINE_CONFIG_V1",
        )

    def test_02_result_schema_constant(self):
        self.assertEqual(
            RESULT_SCHEMA,
            "TRUST_ROBOT_M2DGR_SYNTHETIC_INTERVENTION_BASELINE_RESULTS_V1",
        )

    def test_03_three_model_names(self):
        self.assertEqual(
            len(
                MODEL_NAMES
            ),
            3,
        )

    def test_04_train_trajectory_count(self):
        self.assertEqual(
            len(
                DEVELOPMENT_TRAIN_TRAJECTORIES
            ),
            17,
        )

    def test_05_check_trajectory_count(self):
        self.assertEqual(
            len(
                DEVELOPMENT_CHECK_TRAJECTORIES
            ),
            5,
        )

    def test_06_trajectory_groups_disjoint(self):
        self.assertFalse(
            set(
                DEVELOPMENT_TRAIN_TRAJECTORIES
            )
            & set(
                DEVELOPMENT_CHECK_TRAJECTORIES
            )
        )

    def test_07_feature_count(self):
        self.assertEqual(
            FEATURE_COUNT,
            10,
        )

    def test_08_probability_threshold(self):
        self.assertEqual(
            PROBABILITY_THRESHOLD,
            0.5,
        )

    def test_09_models_build_exact_names(self):
        self.assertEqual(
            tuple(
                build_models().keys()
            ),
            MODEL_NAMES,
        )

    def test_10_result_contract_denies_real_health(self):
        contract = build_result_contract()

        self.assertFalse(
            contract[
                "scientific_boundary"
            ][
                "real_health_truth"
            ]
        )

    def test_11_result_contract_keeps_validation_closed(self):
        contract = build_result_contract()

        self.assertFalse(
            contract[
                "scientific_boundary"
            ][
                "VALIDATION_open"
            ]
        )

    def test_12_result_contract_keeps_confirmation_closed(self):
        contract = build_result_contract()

        self.assertFalse(
            contract[
                "scientific_boundary"
            ][
                "CONFIRMATION_open"
            ]
        )

    def test_13_mechanism_signature_detects_repeat(self):
        X = np.asarray(
            [
                [
                    1, 2, 3, 4, 5,
                    1, 2, 3, 4, 5,
                ],
                [
                    1, 2, 3, 4, 5,
                    1, 2, 3, 4, 6,
                ],
            ],
            dtype=float,
        )

        result = mechanism_signature_probability(
            X
        )

        np.testing.assert_array_equal(
            result,
            [
                1.0,
                0.0,
            ],
        )

    def test_14_perfect_metrics(self):
        result = compute_binary_metrics(
            [
                0,
                1,
            ],
            [
                0.0,
                1.0,
            ],
        )

        self.assertEqual(
            result[
                "balanced_accuracy"
            ],
            1.0,
        )

        self.assertEqual(
            result[
                "f1"
            ],
            1.0,
        )

        self.assertEqual(
            result[
                "brier_score"
            ],
            0.0,
        )

    def test_15_confusion_matrix_layout(self):
        result = compute_binary_metrics(
            [
                0,
                0,
                1,
                1,
            ],
            [
                0.1,
                0.9,
                0.2,
                0.8,
            ],
        )

        self.assertEqual(
            result[
                "confusion_matrix"
            ],
            {
                "tn": 1,
                "fp": 1,
                "fn": 1,
                "tp": 1,
            },
        )

    def test_16_probability_range_guard(self):
        with self.assertRaises(
            MLSyntheticInterventionBaselineError
        ):
            compute_binary_metrics(
                [
                    0,
                    1,
                ],
                [
                    -0.1,
                    1.0,
                ],
            )

    def test_17_per_trajectory_metrics(self):
        result = compute_per_trajectory_metrics(
            np.asarray(
                [
                    0,
                    1,
                    0,
                    1,
                ]
            ),
            np.asarray(
                [
                    0.0,
                    1.0,
                    0.0,
                    1.0,
                ]
            ),
            [
                "a",
                "a",
                "b",
                "b",
            ],
        )

        self.assertEqual(
            set(
                result
            ),
            {
                "a",
                "b",
            },
        )

    def test_18_loader_accepts_train_partition(self):
        records = [
            sample(
                partition=
                    "development_train",
                trajectory=
                    "Circle_01",
                label=
                    0,
                sample_id=
                    "a",
                features=
                    range(10),
            ),
            sample(
                partition=
                    "development_train",
                trajectory=
                    "Circle_01",
                label=
                    1,
                sample_id=
                    "b",
                features=
                    range(
                        10,
                        20,
                    ),
            ),
        ]

        with TemporaryDirectory() as temporary:
            path = (
                Path(
                    temporary
                )
                / "data.jsonl"
            )

            path.write_text(
                "".join(
                    json.dumps(
                        item
                    )
                    + "\n"
                    for item
                    in records
                ),
                encoding="utf-8",
            )

            loaded = load_dataset(
                path,
                expected_partition=
                    "development_train",
            )

        self.assertEqual(
            loaded.X.shape,
            (
                2,
                10,
            ),
        )

    def test_19_loader_rejects_partition_crossing(self):
        records = [
            sample(
                partition=
                    "development_train",
                trajectory=
                    "hall_05",
                label=
                    0,
                sample_id=
                    "a",
                features=
                    range(10),
            ),
            sample(
                partition=
                    "development_train",
                trajectory=
                    "hall_05",
                label=
                    1,
                sample_id=
                    "b",
                features=
                    range(
                        10,
                        20,
                    ),
            ),
        ]

        with TemporaryDirectory() as temporary:
            path = (
                Path(
                    temporary
                )
                / "data.jsonl"
            )

            path.write_text(
                "".join(
                    json.dumps(
                        item
                    )
                    + "\n"
                    for item
                    in records
                ),
                encoding="utf-8",
            )

            with self.assertRaises(
                MLSyntheticInterventionBaselineError
            ):
                load_dataset(
                    path,
                    expected_partition=
                        "development_train",
                )

    def test_20_loader_rejects_real_health_claim(self):
        record_a = sample(
            partition=
                "development_train",
            trajectory=
                "Circle_01",
            label=
                0,
            sample_id=
                "a",
            features=
                range(10),
        )

        record_b = sample(
            partition=
                "development_train",
            trajectory=
                "Circle_01",
            label=
                1,
            sample_id=
                "b",
            features=
                range(
                    10,
                    20,
                ),
        )

        record_a[
            "label_is_real_physical_health_truth"
        ] = True

        with TemporaryDirectory() as temporary:
            path = (
                Path(
                    temporary
                )
                / "data.jsonl"
            )

            path.write_text(
                json.dumps(
                    record_a
                )
                + "\n"
                + json.dumps(
                    record_b
                )
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaises(
                MLSyntheticInterventionBaselineError
            ):
                load_dataset(
                    path,
                    expected_partition=
                        "development_train",
                )

    def test_21_logistic_small_fit(self):
        model = build_models()[
            "logistic_regression"
        ]

        X = np.asarray(
            [
                [0] * 10,
                [1] * 10,
                [0.1] * 10,
                [0.9] * 10,
            ],
            dtype=float,
        )

        y = np.asarray(
            [
                0,
                1,
                0,
                1,
            ]
        )

        model.fit(
            X,
            y,
        )

        probability = (
            predict_positive_probability(
                model,
                X,
            )
        )

        self.assertEqual(
            probability.shape,
            (
                4,
            ),
        )

    def test_22_random_forest_small_fit(self):
        model = build_models()[
            "random_forest"
        ]

        X = np.asarray(
            [
                [0] * 10,
                [1] * 10,
                [0.1] * 10,
                [0.9] * 10,
            ],
            dtype=float,
        )

        y = np.asarray(
            [
                0,
                1,
                0,
                1,
            ]
        )

        model.fit(
            X,
            y,
        )

        probability = (
            predict_positive_probability(
                model,
                X,
            )
        )

        self.assertEqual(
            probability.shape,
            (
                4,
            ),
        )

    def test_23_hist_gradient_boosting_small_fit(self):
        model = build_models()[
            "histogram_gradient_boosting"
        ]

        X = np.asarray(
            [
                [0] * 10,
                [1] * 10,
                [0.1] * 10,
                [0.9] * 10,
            ],
            dtype=float,
        )

        y = np.asarray(
            [
                0,
                1,
                0,
                1,
            ]
        )

        model.fit(
            X,
            y,
        )

        probability = (
            predict_positive_probability(
                model,
                X,
            )
        )

        self.assertEqual(
            probability.shape,
            (
                4,
            ),
        )

    def test_24_joblib_roundtrip(self):
        model = build_models()[
            "logistic_regression"
        ]

        X = np.asarray(
            [
                [0] * 10,
                [1] * 10,
                [0.1] * 10,
                [0.9] * 10,
            ],
            dtype=float,
        )

        y = np.asarray(
            [
                0,
                1,
                0,
                1,
            ]
        )

        model.fit(
            X,
            y,
        )

        before = (
            predict_positive_probability(
                model,
                X,
            )
        )

        with TemporaryDirectory() as temporary:
            path = (
                Path(
                    temporary
                )
                / "model.joblib"
            )

            joblib.dump(
                model,
                path,
            )

            loaded = joblib.load(
                path
            )

        after = (
            predict_positive_probability(
                loaded,
                X,
            )
        )

        np.testing.assert_allclose(
            before,
            after,
        )


if __name__ == "__main__":
    unittest.main()
