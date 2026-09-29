import unittest

from trust_robot.ml_lidar_point_level_registration_dataset import (
    ALL_TRAIN,
    DEVELOPMENT_CHECK,
    DEVELOPMENT_TRAIN,
    EXPECTED_DIAGNOSTIC_COUNTS,
    FAMILY_CLASS_ID,
    FEATURE_NAMES,
    WINDOWS_PER_TRAJECTORY,
    MLLidarPointLevelDatasetError,
    build_corruption_specs,
    evenly_spaced_two_scan_starts,
    partition_for_trajectory,
)


class MLLidarPointLevelRegistrationDatasetTests(
    unittest.TestCase
):
    def test_01_train_count(self):
        self.assertEqual(
            len(DEVELOPMENT_TRAIN),
            17,
        )

    def test_02_check_count(self):
        self.assertEqual(
            len(DEVELOPMENT_CHECK),
            5,
        )

    def test_03_all_count(self):
        self.assertEqual(
            len(ALL_TRAIN),
            22,
        )

    def test_04_split_disjoint(self):
        self.assertFalse(
            set(DEVELOPMENT_TRAIN)
            & set(DEVELOPMENT_CHECK)
        )

    def test_05_windows_per_trajectory(self):
        self.assertEqual(
            WINDOWS_PER_TRAJECTORY,
            50,
        )

    def test_06_feature_count(self):
        self.assertEqual(
            len(FEATURE_NAMES),
            5,
        )

    def test_07_family_count(self):
        self.assertEqual(
            len(FAMILY_CLASS_ID),
            4,
        )

    def test_08_clean_class_id(self):
        self.assertEqual(
            FAMILY_CLASS_ID["CLEAN"],
            0,
        )

    def test_09_point_dropout_class_id(self):
        self.assertEqual(
            FAMILY_CLASS_ID[
                "POINT_DROPOUT"
            ],
            1,
        )

    def test_10_noise_class_id(self):
        self.assertEqual(
            FAMILY_CLASS_ID[
                "XYZ_GAUSSIAN_NOISE"
            ],
            2,
        )

    def test_11_occlusion_class_id(self):
        self.assertEqual(
            FAMILY_CLASS_ID[
                "AZIMUTH_SECTOR_OCCLUSION"
            ],
            3,
        )

    def test_12_three_corruption_specs(self):
        self.assertEqual(
            len(
                build_corruption_specs()
            ),
            3,
        )

    def test_13_dropout_parameter(self):
        specs = build_corruption_specs()

        self.assertEqual(
            specs[0].remove_fraction,
            0.30,
        )

    def test_14_noise_parameter(self):
        specs = build_corruption_specs()

        self.assertEqual(
            specs[1].sigma_m,
            0.05,
        )

    def test_15_occlusion_parameter(self):
        specs = build_corruption_specs()

        self.assertEqual(
            specs[2].sector_width_degrees,
            60.0,
        )

    def test_16_partition_train(self):
        self.assertEqual(
            partition_for_trajectory(
                "Circle_01"
            ),
            "development_train",
        )

    def test_17_partition_check(self):
        self.assertEqual(
            partition_for_trajectory(
                "street_09"
            ),
            "development_check",
        )

    def test_18_validation_rejected(self):
        with self.assertRaises(
            MLLidarPointLevelDatasetError
        ):
            partition_for_trajectory(
                "door_02"
            )

    def test_19_room02_window_count(self):
        starts = (
            evenly_spaced_two_scan_starts(
                EXPECTED_DIAGNOSTIC_COUNTS[
                    "room_02"
                ]
            )
        )

        self.assertEqual(
            len(starts),
            50,
        )

    def test_20_room02_first_window(self):
        starts = (
            evenly_spaced_two_scan_starts(
                EXPECTED_DIAGNOSTIC_COUNTS[
                    "room_02"
                ]
            )
        )

        self.assertEqual(
            starts[0],
            0,
        )

    def test_21_room02_last_window(self):
        starts = (
            evenly_spaced_two_scan_starts(
                EXPECTED_DIAGNOSTIC_COUNTS[
                    "room_02"
                ]
            )
        )

        self.assertEqual(
            starts[-1],
            750,
        )

    def test_22_room02_nonoverlap(self):
        starts = (
            evenly_spaced_two_scan_starts(
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
                    starts,
                    starts[1:],
                )
            ),
            2,
        )

    def test_23_all_trajectories_have_50_windows(self):
        for trajectory in ALL_TRAIN:
            self.assertEqual(
                len(
                    evenly_spaced_two_scan_starts(
                        EXPECTED_DIAGNOSTIC_COUNTS[
                            trajectory
                        ]
                    )
                ),
                50,
            )

    def test_24_total_expected_new_registrations(self):
        self.assertEqual(
            len(ALL_TRAIN)
            * WINDOWS_PER_TRAJECTORY
            * 3,
            3300,
        )


if __name__ == "__main__":
    unittest.main()
