from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

import numpy as np

from trust_robot.ml_lidar_event_gap_baseline import (
    CONFIG_SCHEMA,
    DEVELOPMENT_CHECK,
    DEVELOPMENT_TRAIN,
    FEATURE_COUNT,
    FEATURE_NAMES,
    MODEL_NAMES,
    MLLidarEventGapBaselineError,
    PROBABILITY_THRESHOLD,
    RESULT_SCHEMA,
    binary_metrics,
    build_models,
    load_dataset,
    per_trajectory_metrics,
    positive_probability,
)


def sample(
    partition,
    trajectory,
    label,
    sample_id,
    fingerprint,
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

        "window_fingerprint_sha256":
            fingerprint,

        "label":
            label,

        "feature_names":
            list(
                FEATURE_NAMES
            ),

        "feature_values":
            list(
                features
            ),

        "header_stamps_are_model_features":
            False,

        "trajectory_identity_is_model_feature":
            False,

        "corruption_truth_is_model_feature":
            False,

        "physical_measurement_time_verified":
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


class MLLidarEventGapBaselineTests(
    unittest.TestCase
):
    def test_01_config_schema(self):
        self.assertEqual(
            CONFIG_SCHEMA,
            "TRUST_ROBOT_M2DGR_LIDAR_EVENT_GAP_BASELINE_CONFIG_V1",
        )

    def test_02_result_schema(self):
        self.assertEqual(
            RESULT_SCHEMA,
            "TRUST_ROBOT_M2DGR_LIDAR_EVENT_GAP_BASELINE_RESULTS_V1",
        )

    def test_03_feature_count(self):
        self.assertEqual(
            FEATURE_COUNT,
            5,
        )

    def test_04_feature_names(self):
        self.assertEqual(
            len(
                FEATURE_NAMES
            ),
            5,
        )

    def test_05_model_count(self):
        self.assertEqual(
            len(
                MODEL_NAMES
            ),
            3,
        )

    def test_06_train_trajectory_count(self):
        self.assertEqual(
            len(
                DEVELOPMENT_TRAIN
            ),
            17,
        )

    def test_07_check_trajectory_count(self):
        self.assertEqual(
            len(
                DEVELOPMENT_CHECK
            ),
            5,
        )

    def test_08_trajectory_sets_disjoint(self):
        self.assertFalse(
            set(
                DEVELOPMENT_TRAIN
            )
            & set(
                DEVELOPMENT_CHECK
            )
        )

    def test_09_threshold(self):
        self.assertEqual(
            PROBABILITY_THRESHOLD,
            0.5,
        )

    def test_10_model_names_exact(self):
        self.assertEqual(
            tuple(
                build_models().keys()
            ),
            MODEL_NAMES,
        )

    def test_11_perfect_metrics(self):
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

    def test_12_chance_metrics(self):
        result = binary_metrics(
            [
                0,
                1,
            ],
            [
                0.5,
                0.5,
            ],
        )

        self.assertEqual(
            result[
                "roc_auc"
            ],
            0.5,
        )

    def test_13_invalid_probability_rejected(self):
        with self.assertRaises(
            MLLidarEventGapBaselineError
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

    def test_14_per_trajectory_metrics(self):
        result = per_trajectory_metrics(
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

    def test_15_loader_accepts_complete_pair(self):
        fingerprint = (
            "a" * 64
        )

        records = [
            sample(
                "development_train",
                "Circle_01",
                0,
                "s0",
                fingerprint,
                [
                    1,
                    2,
                    3,
                    4,
                    0.1,
                ],
            ),
            sample(
                "development_train",
                "Circle_01",
                1,
                "s1",
                fingerprint,
                [
                    1,
                    3,
                    5,
                    4,
                    0.2,
                ],
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
                5,
            ),
        )

    def test_16_loader_rejects_incomplete_pair(self):
        fingerprint = (
            "a" * 64
        )

        record = sample(
            "development_train",
            "Circle_01",
            0,
            "s0",
            fingerprint,
            [
                1,
                2,
                3,
                4,
                0.1,
            ],
        )

        with TemporaryDirectory() as temporary:
            path = (
                Path(
                    temporary
                )
                / "data.jsonl"
            )

            path.write_text(
                json.dumps(
                    record
                )
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaises(
                MLLidarEventGapBaselineError
            ):
                load_dataset(
                    path,
                    expected_partition=
                        "development_train",
                )

    def test_17_loader_rejects_check_trajectory_in_train(self):
        fingerprint = (
            "a" * 64
        )

        records = [
            sample(
                "development_train",
                "hall_05",
                0,
                "s0",
                fingerprint,
                [
                    1,
                    2,
                    3,
                    4,
                    0.1,
                ],
            ),
            sample(
                "development_train",
                "hall_05",
                1,
                "s1",
                fingerprint,
                [
                    1,
                    3,
                    5,
                    4,
                    0.2,
                ],
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
                MLLidarEventGapBaselineError
            ):
                load_dataset(
                    path,
                    expected_partition=
                        "development_train",
                )

    def test_18_loader_rejects_real_health_claim(self):
        fingerprint = (
            "a" * 64
        )

        records = [
            sample(
                "development_train",
                "Circle_01",
                0,
                "s0",
                fingerprint,
                [
                    1,
                    2,
                    3,
                    4,
                    0.1,
                ],
            ),
            sample(
                "development_train",
                "Circle_01",
                1,
                "s1",
                fingerprint,
                [
                    1,
                    3,
                    5,
                    4,
                    0.2,
                ],
            ),
        ]

        records[
            0
        ][
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
                MLLidarEventGapBaselineError
            ):
                load_dataset(
                    path,
                    expected_partition=
                        "development_train",
                )

    def test_19_loader_rejects_corruption_truth_feature_flag(self):
        fingerprint = (
            "a" * 64
        )

        records = [
            sample(
                "development_train",
                "Circle_01",
                0,
                "s0",
                fingerprint,
                [
                    1,
                    2,
                    3,
                    4,
                    0.1,
                ],
            ),
            sample(
                "development_train",
                "Circle_01",
                1,
                "s1",
                fingerprint,
                [
                    1,
                    3,
                    5,
                    4,
                    0.2,
                ],
            ),
        ]

        records[
            1
        ][
            "corruption_truth_is_model_feature"
        ] = True

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
                MLLidarEventGapBaselineError
            ):
                load_dataset(
                    path,
                    expected_partition=
                        "development_train",
                )

    def test_20_logistic_fit(self):
        model = build_models()[
            "logistic_regression"
        ]

        X = np.asarray(
            [
                [
                    1,
                    1,
                    1,
                    1,
                    0.1,
                ],
                [
                    1,
                    2,
                    3,
                    1,
                    0.5,
                ],
                [
                    2,
                    2,
                    2,
                    2,
                    0.2,
                ],
                [
                    2,
                    3,
                    4,
                    2,
                    0.6,
                ],
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

        p = positive_probability(
            model,
            X,
        )

        self.assertEqual(
            p.shape,
            (
                4,
            ),
        )

    def test_21_random_forest_fit(self):
        model = build_models()[
            "random_forest"
        ]

        X = np.asarray(
            [
                [1, 1, 1, 1, 0.1],
                [1, 2, 3, 1, 0.5],
                [2, 2, 2, 2, 0.2],
                [2, 3, 4, 2, 0.6],
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

        self.assertEqual(
            positive_probability(
                model,
                X,
            ).shape,
            (
                4,
            ),
        )

    def test_22_hist_gradient_fit(self):
        model = build_models()[
            "histogram_gradient_boosting"
        ]

        X = np.asarray(
            [
                [1, 1, 1, 1, 0.1],
                [1, 2, 3, 1, 0.5],
                [2, 2, 2, 2, 0.2],
                [2, 3, 4, 2, 0.6],
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

        self.assertEqual(
            positive_probability(
                model,
                X,
            ).shape,
            (
                4,
            ),
        )

    def test_23_source_point_count_is_first_feature(self):
        self.assertEqual(
            FEATURE_NAMES[
                0
            ],
            "source_point_count",
        )

    def test_24_rmse_is_final_feature(self):
        self.assertEqual(
            FEATURE_NAMES[
                -1
            ],
            "final_nearest_neighbor_rmse_m",
        )


if __name__ == "__main__":
    unittest.main()
