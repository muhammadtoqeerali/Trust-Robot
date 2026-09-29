from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
import unittest

from trust_robot.ml_synthetic_intervention_dataset import (
    ALL_TRAIN,
    DATASET_SCHEMA,
    DEVELOPMENT_CHECK,
    DEVELOPMENT_TRAIN,
    FEATURE_NAMES,
    INTERVENTION_FAMILY,
    MLSyntheticInterventionDatasetError,
    WINDOW_FEATURE_NAMES,
    build_contract,
    build_selection_binding,
    build_window_samples_from_vectors,
    iter_trajectory_samples,
    partition_for_trajectory,
    selection_binding_sha256,
    validate_sample,
)


SHA_A = "a" * 64
SHA_B = "b" * 64
SHA_C = "c" * 64


def samples():
    return build_window_samples_from_vectors(
        trajectory=
            "Circle_01",

        development_partition=
            "development_train",

        source_scan_index=
            2,

        previous_feature_values=(
            100.0,
            101.0,
            5.0,
            90.0,
            0.10,
        ),

        current_feature_values=(
            110.0,
            111.0,
            6.0,
            95.0,
            0.20,
        ),

        previous_source_record_sha256=
            SHA_A,

        current_source_record_sha256=
            SHA_B,
    )


class MLSyntheticInterventionDatasetTests(
    unittest.TestCase
):
    def test_01_contract_schema(self):
        self.assertEqual(
            build_contract()[
                "schema"
            ],
            DATASET_SCHEMA,
        )

    def test_02_development_train_count(self):
        self.assertEqual(
            len(
                DEVELOPMENT_TRAIN
            ),
            17,
        )

    def test_03_development_check_count(self):
        self.assertEqual(
            len(
                DEVELOPMENT_CHECK
            ),
            5,
        )

    def test_04_development_split_disjoint(self):
        self.assertFalse(
            set(
                DEVELOPMENT_TRAIN
            )
            & set(
                DEVELOPMENT_CHECK
            )
        )

    def test_05_all_train_count(self):
        self.assertEqual(
            len(
                ALL_TRAIN
            ),
            22,
        )

    def test_06_five_frozen_base_features(self):
        self.assertEqual(
            len(
                FEATURE_NAMES
            ),
            5,
        )

    def test_07_two_event_window_has_ten_features(self):
        self.assertEqual(
            len(
                WINDOW_FEATURE_NAMES
            ),
            10,
        )

    def test_08_intervention_is_event_repeat(self):
        self.assertEqual(
            INTERVENTION_FAMILY.value,
            "EVENT_REPEAT",
        )

    def test_09_partition_resolution(self):
        self.assertEqual(
            partition_for_trajectory(
                "Circle_01"
            ),
            "development_train",
        )

        self.assertEqual(
            partition_for_trajectory(
                "street_09"
            ),
            "development_check",
        )

    def test_10_outside_train_rejected(self):
        with self.assertRaises(
            MLSyntheticInterventionDatasetError
        ):
            partition_for_trajectory(
                "door_02"
            )

    def test_11_clean_sample_label(self):
        clean, _ = samples()

        self.assertEqual(
            clean[
                "label"
            ],
            0,
        )

        self.assertFalse(
            clean[
                "synthetic_intervention_applied"
            ]
        )

    def test_12_corrupt_sample_label(self):
        _, corrupt = samples()

        self.assertEqual(
            corrupt[
                "label"
            ],
            1,
        )

        self.assertTrue(
            corrupt[
                "synthetic_intervention_applied"
            ]
        )

    def test_13_clean_window_preserves_current(self):
        clean, _ = samples()

        self.assertEqual(
            clean[
                "feature_values"
            ][
                5:
            ],
            [
                110.0,
                111.0,
                6.0,
                95.0,
                0.20,
            ],
        )

    def test_14_corrupt_window_repeats_previous(self):
        _, corrupt = samples()

        self.assertEqual(
            corrupt[
                "feature_values"
            ][
                :5
            ],
            corrupt[
                "feature_values"
            ][
                5:
            ],
        )

    def test_15_sample_ids_are_deterministic(self):
        first = samples()
        second = samples()

        self.assertEqual(
            first[
                0
            ][
                "sample_id"
            ],
            second[
                0
            ][
                "sample_id"
            ],
        )

        self.assertEqual(
            first[
                1
            ][
                "sample_id"
            ],
            second[
                1
            ][
                "sample_id"
            ],
        )

    def test_16_bad_feature_length_rejected(self):
        with self.assertRaises(
            MLSyntheticInterventionDatasetError
        ):
            build_window_samples_from_vectors(
                trajectory=
                    "Circle_01",

                development_partition=
                    "development_train",

                source_scan_index=
                    2,

                previous_feature_values=(
                    1,
                    2,
                ),

                current_feature_values=(
                    1,
                    2,
                    3,
                    4,
                    5,
                ),

                previous_source_record_sha256=
                    SHA_A,

                current_source_record_sha256=
                    SHA_B,
            )

    def test_17_samples_explicitly_deny_real_health_truth(self):
        clean, corrupt = samples()

        self.assertFalse(
            clean[
                "label_is_real_physical_health_truth"
            ]
        )

        self.assertFalse(
            corrupt[
                "label_is_real_physical_health_truth"
            ]
        )

    def test_18_selection_binding_is_deterministic(self):
        self.assertEqual(
            build_selection_binding(),
            build_selection_binding(),
        )

        self.assertEqual(
            len(
                selection_binding_sha256()
            ),
            64,
        )

    def test_19_iterator_emits_two_samples_per_adjacent_pair(self):
        records = [
            {
                "trajectory":
                    "Circle_01",

                "scan_index":
                    1,

                "feature_values":
                    [
                        1,
                        2,
                        3,
                        4,
                        0.1,
                    ],

                "content_sha256":
                    SHA_A,
            },
            {
                "trajectory":
                    "Circle_01",

                "scan_index":
                    2,

                "feature_values":
                    [
                        2,
                        3,
                        4,
                        5,
                        0.2,
                    ],

                "content_sha256":
                    SHA_B,
            },
            {
                "trajectory":
                    "Circle_01",

                "scan_index":
                    3,

                "feature_values":
                    [
                        3,
                        4,
                        5,
                        6,
                        0.3,
                    ],

                "content_sha256":
                    SHA_C,
            },
        ]

        with TemporaryDirectory() as temporary:
            path = (
                Path(
                    temporary
                )
                / "features.jsonl"
            )

            path.write_text(
                "".join(
                    json.dumps(
                        record
                    )
                    + "\n"
                    for record
                    in records
                ),
                encoding="utf-8",
            )

            with patch(
                "trust_robot.ml_synthetic_intervention_dataset."
                "validate_lidar_diagnostic_artifact_record"
            ):
                result = list(
                    iter_trajectory_samples(
                        path,
                        trajectory=
                            "Circle_01",
                        development_partition=
                            "development_train",
                    )
                )

        self.assertEqual(
            len(
                result
            ),
            4,
        )

    def test_20_iterator_rejects_nonconsecutive_scans(self):
        records = [
            {
                "trajectory":
                    "Circle_01",

                "scan_index":
                    1,

                "feature_values":
                    [
                        1,
                        2,
                        3,
                        4,
                        0.1,
                    ],

                "content_sha256":
                    SHA_A,
            },
            {
                "trajectory":
                    "Circle_01",

                "scan_index":
                    3,

                "feature_values":
                    [
                        2,
                        3,
                        4,
                        5,
                        0.2,
                    ],

                "content_sha256":
                    SHA_B,
            },
        ]

        with TemporaryDirectory() as temporary:
            path = (
                Path(
                    temporary
                )
                / "features.jsonl"
            )

            path.write_text(
                "".join(
                    json.dumps(
                        record
                    )
                    + "\n"
                    for record
                    in records
                ),
                encoding="utf-8",
            )

            with patch(
                "trust_robot.ml_synthetic_intervention_dataset."
                "validate_lidar_diagnostic_artifact_record"
            ):
                with self.assertRaises(
                    MLSyntheticInterventionDatasetError
                ):
                    list(
                        iter_trajectory_samples(
                            path,
                            trajectory=
                                "Circle_01",
                            development_partition=
                                "development_train",
                        )
                    )


if __name__ == "__main__":
    unittest.main()
