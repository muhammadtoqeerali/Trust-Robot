import unittest

from trust_robot.ml_lidar_event_gap_registration_dataset import (
    ALL_TRAIN,
    CONFIG_SCHEMA,
    DATASET_SCHEMA,
    DEVELOPMENT_CHECK,
    DEVELOPMENT_TRAIN,
    EXPECTED_DIAGNOSTIC_COUNTS,
    FEATURE_NAMES,
    MLLidarEventGapDatasetError,
    WINDOWS_PER_TRAJECTORY,
    build_event_gap_spec,
    build_selection_binding,
    evenly_spaced_window_starts,
    partition_for_trajectory,
)


class MLLidarEventGapRegistrationDatasetTests(
    unittest.TestCase
):
    def test_01_config_schema(self):
        self.assertEqual(
            CONFIG_SCHEMA,
            "TRUST_ROBOT_M2DGR_LIDAR_EVENT_GAP_REGISTRATION_DATASET_CONFIG_V1",
        )

    def test_02_dataset_schema(self):
        self.assertEqual(
            DATASET_SCHEMA,
            "TRUST_ROBOT_M2DGR_LIDAR_EVENT_GAP_REGISTRATION_DATASET_V1",
        )

    def test_03_train_count(self):
        self.assertEqual(
            len(
                DEVELOPMENT_TRAIN
            ),
            17,
        )

    def test_04_check_count(self):
        self.assertEqual(
            len(
                DEVELOPMENT_CHECK
            ),
            5,
        )

    def test_05_total_train_count(self):
        self.assertEqual(
            len(
                ALL_TRAIN
            ),
            22,
        )

    def test_06_groups_disjoint(self):
        self.assertFalse(
            set(
                DEVELOPMENT_TRAIN
            )
            & set(
                DEVELOPMENT_CHECK
            )
        )

    def test_07_windows_per_trajectory(self):
        self.assertEqual(
            WINDOWS_PER_TRAJECTORY,
            100,
        )

    def test_08_five_features(self):
        self.assertEqual(
            len(
                FEATURE_NAMES
            ),
            5,
        )

    def test_09_feature_order(self):
        self.assertEqual(
            FEATURE_NAMES,
            (
                "source_point_count",
                "target_point_count",
                "fixed_point_iterations",
                "final_correspondence_count",
                "final_nearest_neighbor_rmse_m",
            ),
        )

    def test_10_partition_train(self):
        self.assertEqual(
            partition_for_trajectory(
                "Circle_01"
            ),
            "development_train",
        )

    def test_11_partition_check(self):
        self.assertEqual(
            partition_for_trajectory(
                "street_09"
            ),
            "development_check",
        )

    def test_12_partition_rejects_validation(self):
        with self.assertRaises(
            MLLidarEventGapDatasetError
        ):
            partition_for_trajectory(
                "door_02"
            )

    def test_13_spec_family(self):
        self.assertEqual(
            build_event_gap_spec().family.value,
            "EVENT_GAP",
        )

    def test_14_spec_modality(self):
        self.assertEqual(
            build_event_gap_spec().modality.value,
            "lidar",
        )

    def test_15_spec_start_index(self):
        self.assertEqual(
            build_event_gap_spec().start_index,
            1,
        )

    def test_16_spec_length(self):
        self.assertEqual(
            build_event_gap_spec().length,
            1,
        )

    def test_17_selection_binding_exists(self):
        self.assertTrue(
            build_selection_binding()
        )

    def test_18_selection_binding_deterministic(self):
        self.assertEqual(
            build_selection_binding(),
            build_selection_binding(),
        )

    def test_19_room02_selection_count(self):
        result = (
            evenly_spaced_window_starts(
                EXPECTED_DIAGNOSTIC_COUNTS[
                    "room_02"
                ]
            )
        )

        self.assertEqual(
            len(
                result
            ),
            100,
        )

    def test_20_room02_selection_boundaries(self):
        result = (
            evenly_spaced_window_starts(
                EXPECTED_DIAGNOSTIC_COUNTS[
                    "room_02"
                ]
            )
        )

        self.assertEqual(
            result[
                0
            ],
            0,
        )

        self.assertEqual(
            result[
                -1
            ],
            749,
        )

    def test_21_room02_windows_nonoverlap(self):
        result = (
            evenly_spaced_window_starts(
                EXPECTED_DIAGNOSTIC_COUNTS[
                    "room_02"
                ]
            )
        )

        self.assertGreaterEqual(
            min(
                b - a
                for a, b
                in zip(
                    result,
                    result[
                        1:
                    ],
                )
            ),
            3,
        )

    def test_22_every_trajectory_has_100_windows(self):
        for count in (
            EXPECTED_DIAGNOSTIC_COUNTS.values()
        ):
            self.assertEqual(
                len(
                    evenly_spaced_window_starts(
                        count
                    )
                ),
                100,
            )

    def test_23_bad_diagnostic_count_rejected(self):
        with self.assertRaises(
            MLLidarEventGapDatasetError
        ):
            evenly_spaced_window_starts(
                50
            )

    def test_24_expected_total_selected_windows(self):
        self.assertEqual(
            len(
                ALL_TRAIN
            )
            * WINDOWS_PER_TRAJECTORY,
            2200,
        )


if __name__ == "__main__":
    unittest.main()
