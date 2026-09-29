from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

import numpy as np

from trust_robot.lidar_noise_sensitive_diagnostics import (
    COMBINED_FEATURE_NAMES,
    LEGACY_PHASE4_FEATURE_NAMES,
    NOISE_SENSITIVE_FEATURE_NAMES,
)

from trust_robot.ml_lidar_extended_13_feature_multidegradation_baseline import (
    DEGRADATION_FAMILIES,
    DEVELOPMENT_CHECK,
    DEVELOPMENT_TRAIN,
    FEATURE_COUNT,
    FEATURE_NAMES,
    MODEL_NAMES,
    PROBABILITY_THRESHOLD,
    RANDOM_SEED,
    Extended13FeatureBaselineError,
    assert_exact_parent_pairing,
    balanced_binary_sample_weights,
    build_models,
    fit_with_binary_class_weights,
    load_extended_dataset,
    load_parent_five_feature_index,
    positive_probability,
)


def extended_record(
    *,
    family,
    sample_id,
):
    return {
        "outer_split":
            "TRAIN",

        "development_partition":
            "development_train",

        "trajectory":
            "Circle_01",

        "window_start_scan_index":
            0,

        "sample_id":
            sample_id,

        "parent_sample_id":
            sample_id,

        "degradation_family":
            family,

        "binary_degraded_label":
            (
                0
                if family == "CLEAN"
                else 1
            ),

        "feature_names":
            list(
                COMBINED_FEATURE_NAMES
            ),

        "feature_values": [
            100,
            90,
            7,
            100,
            0.05,
            0.04,
            0.02,
            0.035,
            0.01,
            0.05,
            0.07,
            0.08,
            0.20,
        ],

        "combined_feature_count":
            13,

        "legacy_feature_count":
            5,

        "new_residual_feature_count":
            8,

        "parent_sample_population_changed":
            False,

        "registration_algorithm_modified":
            False,

        "registration_refit_inside_extended_extractor":
            False,

        "label_is_real_physical_health_truth":
            False,
    }


def four_extended_records():
    return [
        extended_record(
            family=
                family,

            sample_id=
                "sample-"
                + str(index),
        )
        for index, family
        in enumerate(
            (
                "CLEAN",
                "POINT_DROPOUT",
                "XYZ_GAUSSIAN_NOISE",
                "AZIMUTH_SECTOR_OCCLUSION",
            )
        )
    ]


def parent_from_extended(
    item,
):
    return {
        "outer_split":
            "TRAIN",

        "development_partition":
            item[
                "development_partition"
            ],

        "trajectory":
            item[
                "trajectory"
            ],

        "window_start_scan_index":
            item[
                "window_start_scan_index"
            ],

        "sample_id":
            item[
                "sample_id"
            ],

        "degradation_family":
            item[
                "degradation_family"
            ],

        "binary_degraded_label":
            item[
                "binary_degraded_label"
            ],

        "feature_names":
            list(
                LEGACY_PHASE4_FEATURE_NAMES
            ),

        "feature_values":
            item[
                "feature_values"
            ][
                :5
            ],

        "label_is_real_physical_health_truth":
            False,
    }


class Extended13FeatureBaselineTests(
    unittest.TestCase
):
    def test_01_feature_count(self):
        self.assertEqual(
            FEATURE_COUNT,
            13,
        )

    def test_02_feature_names_count(self):
        self.assertEqual(
            len(FEATURE_NAMES),
            13,
        )

    def test_03_legacy_count(self):
        self.assertEqual(
            len(
                LEGACY_PHASE4_FEATURE_NAMES
            ),
            5,
        )

    def test_04_new_count(self):
        self.assertEqual(
            len(
                NOISE_SENSITIVE_FEATURE_NAMES
            ),
            8,
        )

    def test_05_three_models(self):
        self.assertEqual(
            len(MODEL_NAMES),
            3,
        )

    def test_06_three_degradation_families(self):
        self.assertEqual(
            len(
                DEGRADATION_FAMILIES
            ),
            3,
        )

    def test_07_train_count(self):
        self.assertEqual(
            len(
                DEVELOPMENT_TRAIN
            ),
            17,
        )

    def test_08_check_count(self):
        self.assertEqual(
            len(
                DEVELOPMENT_CHECK
            ),
            5,
        )

    def test_09_split_disjoint(self):
        self.assertFalse(
            set(
                DEVELOPMENT_TRAIN
            )
            & set(
                DEVELOPMENT_CHECK
            )
        )

    def test_10_threshold_same(self):
        self.assertEqual(
            PROBABILITY_THRESHOLD,
            0.5,
        )

    def test_11_seed_same(self):
        self.assertEqual(
            RANDOM_SEED,
            20260928,
        )

    def test_12_model_names_exact(self):
        self.assertEqual(
            tuple(
                build_models().keys()
            ),
            MODEL_NAMES,
        )

    def test_13_balanced_weights(self):
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

    def test_14_loader_accepts_four_family_window(self):
        records = (
            four_extended_records()
        )

        with TemporaryDirectory() as temporary:
            path = (
                Path(temporary)
                / "extended.jsonl"
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

            loaded = (
                load_extended_dataset(
                    path,
                    expected_partition=
                        "development_train",
                )
            )

        self.assertEqual(
            loaded.X.shape,
            (
                4,
                13,
            ),
        )

    def test_15_loader_one_clean_three_degraded(self):
        records = (
            four_extended_records()
        )

        with TemporaryDirectory() as temporary:
            path = (
                Path(temporary)
                / "extended.jsonl"
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

            loaded = (
                load_extended_dataset(
                    path,
                    expected_partition=
                        "development_train",
                )
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

    def test_16_loader_rejects_missing_family(self):
        records = (
            four_extended_records()[
                :-1
            ]
        )

        with TemporaryDirectory() as temporary:
            path = (
                Path(temporary)
                / "extended.jsonl"
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
                Extended13FeatureBaselineError
            ):
                load_extended_dataset(
                    path,
                    expected_partition=
                        "development_train",
                )

    def test_17_loader_rejects_parent_id_change(self):
        records = (
            four_extended_records()
        )

        records[0][
            "parent_sample_id"
        ] = "different"

        with TemporaryDirectory() as temporary:
            path = (
                Path(temporary)
                / "extended.jsonl"
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
                Extended13FeatureBaselineError
            ):
                load_extended_dataset(
                    path,
                    expected_partition=
                        "development_train",
                )

    def test_18_loader_rejects_five_feature_vector(self):
        records = (
            four_extended_records()
        )

        records[0][
            "feature_values"
        ] = records[0][
            "feature_values"
        ][
            :5
        ]

        with TemporaryDirectory() as temporary:
            path = (
                Path(temporary)
                / "extended.jsonl"
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
                Extended13FeatureBaselineError
            ):
                load_extended_dataset(
                    path,
                    expected_partition=
                        "development_train",
                )

    def test_19_parent_index_count(self):
        records = (
            four_extended_records()
        )

        parent_records = [
            parent_from_extended(
                item
            )
            for item
            in records
        ]

        with TemporaryDirectory() as temporary:
            path = (
                Path(temporary)
                / "parent.jsonl"
            )

            path.write_text(
                "".join(
                    json.dumps(item)
                    + "\n"
                    for item
                    in parent_records
                ),
                encoding="utf-8",
            )

            index = (
                load_parent_five_feature_index(
                    path
                )
            )

        self.assertEqual(
            len(index),
            4,
        )

    def test_20_exact_parent_pairing_passes(self):
        records = (
            four_extended_records()
        )

        parent_records = [
            parent_from_extended(
                item
            )
            for item
            in records
        ]

        with TemporaryDirectory() as temporary:
            extended = (
                Path(temporary)
                / "extended.jsonl"
            )

            parent = (
                Path(temporary)
                / "parent.jsonl"
            )

            extended.write_text(
                "".join(
                    json.dumps(item)
                    + "\n"
                    for item
                    in records
                ),
                encoding="utf-8",
            )

            parent.write_text(
                "".join(
                    json.dumps(item)
                    + "\n"
                    for item
                    in parent_records
                ),
                encoding="utf-8",
            )

            loaded = (
                load_extended_dataset(
                    extended,
                    expected_partition=
                        "development_train",
                )
            )

            index = (
                load_parent_five_feature_index(
                    parent
                )
            )

            assert_exact_parent_pairing(
                loaded,
                index,
            )

    def test_21_parent_pairing_rejects_legacy_change(self):
        records = (
            four_extended_records()
        )

        parent_records = [
            parent_from_extended(
                item
            )
            for item
            in records
        ]

        parent_records[0][
            "feature_values"
        ][0] += 1

        with TemporaryDirectory() as temporary:
            extended = (
                Path(temporary)
                / "extended.jsonl"
            )

            parent = (
                Path(temporary)
                / "parent.jsonl"
            )

            extended.write_text(
                "".join(
                    json.dumps(item)
                    + "\n"
                    for item
                    in records
                ),
                encoding="utf-8",
            )

            parent.write_text(
                "".join(
                    json.dumps(item)
                    + "\n"
                    for item
                    in parent_records
                ),
                encoding="utf-8",
            )

            loaded = (
                load_extended_dataset(
                    extended,
                    expected_partition=
                        "development_train",
                )
            )

            index = (
                load_parent_five_feature_index(
                    parent
                )
            )

            with self.assertRaises(
                Extended13FeatureBaselineError
            ):
                assert_exact_parent_pairing(
                    loaded,
                    index,
                )

    def test_22_logistic_fit_13_features(self):
        model = build_models()[
            "logistic_regression"
        ]

        X = np.vstack(
            (
                np.zeros(
                    13
                ),
                np.ones(
                    13
                ),
                np.full(
                    13,
                    2.0,
                ),
                np.full(
                    13,
                    3.0,
                ),
            )
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

    def test_23_rf_fit_13_features(self):
        model = build_models()[
            "random_forest"
        ]

        X = np.vstack(
            (
                np.zeros(
                    13
                ),
                np.ones(
                    13
                ),
                np.full(
                    13,
                    2.0,
                ),
                np.full(
                    13,
                    3.0,
                ),
            )
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

    def test_24_hgb_fit_13_features(self):
        model = build_models()[
            "histogram_gradient_boosting"
        ]

        X = np.vstack(
            (
                np.zeros(
                    13
                ),
                np.ones(
                    13
                ),
                np.full(
                    13,
                    2.0,
                ),
                np.full(
                    13,
                    3.0,
                ),
            )
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

    def test_25_registration_algorithm_flag_required_false(self):
        records = (
            four_extended_records()
        )

        records[0][
            "registration_algorithm_modified"
        ] = True

        with TemporaryDirectory() as temporary:
            path = (
                Path(temporary)
                / "extended.jsonl"
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
                Extended13FeatureBaselineError
            ):
                load_extended_dataset(
                    path,
                    expected_partition=
                        "development_train",
                )

    def test_26_real_health_claim_rejected(self):
        records = (
            four_extended_records()
        )

        records[0][
            "label_is_real_physical_health_truth"
        ] = True

        with TemporaryDirectory() as temporary:
            path = (
                Path(temporary)
                / "extended.jsonl"
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
                Extended13FeatureBaselineError
            ):
                load_extended_dataset(
                    path,
                    expected_partition=
                        "development_train",
                )

    def test_27_combined_prefix_is_legacy(self):
        self.assertEqual(
            tuple(
                FEATURE_NAMES[
                    :5
                ]
            ),
            tuple(
                LEGACY_PHASE4_FEATURE_NAMES
            ),
        )

    def test_28_combined_suffix_is_new_residual(self):
        self.assertEqual(
            tuple(
                FEATURE_NAMES[
                    5:
                ]
            ),
            tuple(
                NOISE_SENSITIVE_FEATURE_NAMES
            ),
        )


if __name__ == "__main__":
    unittest.main()
