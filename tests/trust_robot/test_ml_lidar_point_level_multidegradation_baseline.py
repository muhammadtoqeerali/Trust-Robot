from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

import numpy as np

from trust_robot.ml_lidar_point_level_multidegradation_baseline import (
    CONFIG_SCHEMA,
    DEGRADATION_FAMILIES,
    DEVELOPMENT_CHECK,
    DEVELOPMENT_TRAIN,
    FEATURE_COUNT,
    FEATURE_NAMES,
    MODEL_NAMES,
    PROBABILITY_THRESHOLD,
    RESULT_SCHEMA,
    MLLidarPointLevelBaselineError,
    balanced_binary_sample_weights,
    binary_metrics,
    build_models,
    fit_with_binary_class_weights,
    load_dataset,
    per_family_metrics,
    positive_probability,
)


def sample(
    *,
    partition,
    trajectory,
    start,
    family,
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

        "window_start_scan_index":
            start,

        "sample_id":
            sample_id,

        "degradation_family":
            family,

        "binary_degraded_label":
            (
                0
                if family
                == "CLEAN"
                else 1
            ),

        "feature_names":
            list(
                FEATURE_NAMES
            ),

        "feature_values":
            list(
                features
            ),

        "trajectory_identity_is_model_feature":
            False,

        "window_index_is_model_feature":
            False,

        "corruption_family_is_model_feature":
            False,

        "corruption_parameters_are_model_features":
            False,

        "timestamps_are_model_features":
            False,

        "reference_data_used":
            False,

        "validation_data_used":
            False,

        "confirmation_data_used":
            False,

        "label_is_real_physical_health_truth":
            False,
    }


def complete_window_records():
    families = (
        "CLEAN",
        "POINT_DROPOUT",
        "XYZ_GAUSSIAN_NOISE",
        "AZIMUTH_SECTOR_OCCLUSION",
    )

    result = []

    for index, family in enumerate(
        families
    ):
        result.append(
            sample(
                partition=
                    "development_train",

                trajectory=
                    "Circle_01",

                start=
                    0,

                family=
                    family,

                sample_id=
                    "sample-"
                    + str(index),

                features=[
                    100 + index,
                    90,
                    5 + index,
                    80,
                    0.1 + index * 0.01,
                ],
            )
        )

    return result


class MLLidarPointLevelBaselineTests(
    unittest.TestCase
):
    def test_01_config_schema(self):
        self.assertEqual(
            CONFIG_SCHEMA,
            "TRUST_ROBOT_M2DGR_LIDAR_POINT_LEVEL_MULTIDEGRADATION_BASELINE_CONFIG_V1",
        )

    def test_02_result_schema(self):
        self.assertEqual(
            RESULT_SCHEMA,
            "TRUST_ROBOT_M2DGR_LIDAR_POINT_LEVEL_MULTIDEGRADATION_BASELINE_RESULTS_V1",
        )

    def test_03_feature_count(self):
        self.assertEqual(
            FEATURE_COUNT,
            5,
        )

    def test_04_feature_names(self):
        self.assertEqual(
            len(FEATURE_NAMES),
            5,
        )

    def test_05_three_degradation_families(self):
        self.assertEqual(
            len(
                DEGRADATION_FAMILIES
            ),
            3,
        )

    def test_06_dropout_present(self):
        self.assertIn(
            "POINT_DROPOUT",
            DEGRADATION_FAMILIES,
        )

    def test_07_noise_present(self):
        self.assertIn(
            "XYZ_GAUSSIAN_NOISE",
            DEGRADATION_FAMILIES,
        )

    def test_08_occlusion_present(self):
        self.assertIn(
            "AZIMUTH_SECTOR_OCCLUSION",
            DEGRADATION_FAMILIES,
        )

    def test_09_three_models(self):
        self.assertEqual(
            len(MODEL_NAMES),
            3,
        )

    def test_10_train_trajectory_count(self):
        self.assertEqual(
            len(DEVELOPMENT_TRAIN),
            17,
        )

    def test_11_check_trajectory_count(self):
        self.assertEqual(
            len(DEVELOPMENT_CHECK),
            5,
        )

    def test_12_splits_disjoint(self):
        self.assertFalse(
            set(DEVELOPMENT_TRAIN)
            & set(DEVELOPMENT_CHECK)
        )

    def test_13_threshold(self):
        self.assertEqual(
            PROBABILITY_THRESHOLD,
            0.5,
        )

    def test_14_models_exact(self):
        self.assertEqual(
            tuple(
                build_models().keys()
            ),
            MODEL_NAMES,
        )

    def test_15_balanced_weights(self):
        y = np.asarray(
            [
                0,
                1,
                1,
                1,
            ]
        )

        weights = (
            balanced_binary_sample_weights(
                y
            )
        )

        self.assertAlmostEqual(
            weights[0],
            2.0,
        )

        self.assertAlmostEqual(
            weights[1],
            2.0 / 3.0,
        )

    def test_16_balanced_weight_total_per_class(self):
        y = np.asarray(
            [
                0,
                1,
                1,
                1,
            ]
        )

        weights = (
            balanced_binary_sample_weights(
                y
            )
        )

        self.assertAlmostEqual(
            float(
                weights[
                    y == 0
                ].sum()
            ),
            float(
                weights[
                    y == 1
                ].sum()
            ),
        )

    def test_17_perfect_metrics(self):
        result = binary_metrics(
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

    def test_18_bad_probability_rejected(self):
        with self.assertRaises(
            MLLidarPointLevelBaselineError
        ):
            binary_metrics(
                [
                    0,
                    1,
                ],
                [
                    -0.1,
                    1.0,
                ],
            )

    def test_19_loader_accepts_complete_window(self):
        records = (
            complete_window_records()
        )

        with TemporaryDirectory() as temporary:
            path = (
                Path(temporary)
                / "data.jsonl"
            )

            path.write_text(
                "".join(
                    json.dumps(item)
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
                4,
                5,
            ),
        )

    def test_20_loader_labels_one_clean_three_degraded(self):
        records = (
            complete_window_records()
        )

        with TemporaryDirectory() as temporary:
            path = (
                Path(temporary)
                / "data.jsonl"
            )

            path.write_text(
                "".join(
                    json.dumps(item)
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
            int(
                np.sum(
                    loaded.y == 0
                )
            ),
            1,
        )

        self.assertEqual(
            int(
                np.sum(
                    loaded.y == 1
                )
            ),
            3,
        )

    def test_21_loader_rejects_missing_family(self):
        records = (
            complete_window_records()[
                :-1
            ]
        )

        with TemporaryDirectory() as temporary:
            path = (
                Path(temporary)
                / "data.jsonl"
            )

            path.write_text(
                "".join(
                    json.dumps(item)
                    + "\n"
                    for item
                    in records
                ),
                encoding="utf-8",
            )

            with self.assertRaises(
                MLLidarPointLevelBaselineError
            ):
                load_dataset(
                    path,
                    expected_partition=
                        "development_train",
                )

    def test_22_loader_rejects_check_trajectory_in_train(self):
        records = (
            complete_window_records()
        )

        for item in records:
            item[
                "trajectory"
            ] = "hall_05"

        with TemporaryDirectory() as temporary:
            path = (
                Path(temporary)
                / "data.jsonl"
            )

            path.write_text(
                "".join(
                    json.dumps(item)
                    + "\n"
                    for item
                    in records
                ),
                encoding="utf-8",
            )

            with self.assertRaises(
                MLLidarPointLevelBaselineError
            ):
                load_dataset(
                    path,
                    expected_partition=
                        "development_train",
                )

    def test_23_logistic_weighted_fit(self):
        model = build_models()[
            "logistic_regression"
        ]

        X = np.asarray(
            [
                [0, 0, 0, 0, 0],
                [1, 0, 1, 0, 1],
                [2, 0, 2, 0, 2],
                [3, 0, 3, 0, 3],
            ],
            dtype=float,
        )

        y = np.asarray(
            [
                0,
                1,
                1,
                1,
            ]
        )

        fit_with_binary_class_weights(
            model,
            X,
            y,
        )

        self.assertEqual(
            positive_probability(
                model,
                X,
            ).shape,
            (
                4,
            ),
        )

    def test_24_random_forest_weighted_fit(self):
        model = build_models()[
            "random_forest"
        ]

        X = np.asarray(
            [
                [0, 0, 0, 0, 0],
                [1, 0, 1, 0, 1],
                [2, 0, 2, 0, 2],
                [3, 0, 3, 0, 3],
            ],
            dtype=float,
        )

        y = np.asarray(
            [
                0,
                1,
                1,
                1,
            ]
        )

        fit_with_binary_class_weights(
            model,
            X,
            y,
        )

        self.assertEqual(
            positive_probability(
                model,
                X,
            ).shape,
            (
                4,
            ),
        )

    def test_25_hist_gradient_weighted_fit(self):
        model = build_models()[
            "histogram_gradient_boosting"
        ]

        X = np.asarray(
            [
                [0, 0, 0, 0, 0],
                [1, 0, 1, 0, 1],
                [2, 0, 2, 0, 2],
                [3, 0, 3, 0, 3],
            ],
            dtype=float,
        )

        y = np.asarray(
            [
                0,
                1,
                1,
                1,
            ]
        )

        fit_with_binary_class_weights(
            model,
            X,
            y,
        )

        self.assertEqual(
            positive_probability(
                model,
                X,
            ).shape,
            (
                4,
            ),
        )

    def test_26_per_family_reports_three_families(self):
        records = (
            complete_window_records()
        )

        with TemporaryDirectory() as temporary:
            path = (
                Path(temporary)
                / "data.jsonl"
            )

            path.write_text(
                "".join(
                    json.dumps(item)
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

        probability = np.asarray(
            [
                0.1,
                0.9,
                0.9,
                0.9,
            ]
        )

        result = per_family_metrics(
            loaded,
            probability,
        )

        self.assertEqual(
            set(result),
            set(
                DEGRADATION_FAMILIES
            ),
        )

    def test_27_per_family_perfect_probabilities(self):
        records = (
            complete_window_records()
        )

        with TemporaryDirectory() as temporary:
            path = (
                Path(temporary)
                / "data.jsonl"
            )

            path.write_text(
                "".join(
                    json.dumps(item)
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

        result = per_family_metrics(
            loaded,
            np.asarray(
                [
                    0.0,
                    1.0,
                    1.0,
                    1.0,
                ]
            ),
        )

        for metrics in (
            result.values()
        ):
            self.assertEqual(
                metrics[
                    "balanced_accuracy"
                ],
                1.0,
            )

    def test_28_loader_rejects_real_health_claim(self):
        records = (
            complete_window_records()
        )

        records[0][
            "label_is_real_physical_health_truth"
        ] = True

        with TemporaryDirectory() as temporary:
            path = (
                Path(temporary)
                / "data.jsonl"
            )

            path.write_text(
                "".join(
                    json.dumps(item)
                    + "\n"
                    for item
                    in records
                ),
                encoding="utf-8",
            )

            with self.assertRaises(
                MLLidarPointLevelBaselineError
            ):
                load_dataset(
                    path,
                    expected_partition=
                        "development_train",
                )


if __name__ == "__main__":
    unittest.main()
