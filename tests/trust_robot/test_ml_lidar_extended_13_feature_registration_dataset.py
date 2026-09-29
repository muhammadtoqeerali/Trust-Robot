from types import SimpleNamespace
import unittest

from trust_robot.lidar_noise_sensitive_diagnostics import (
    COMBINED_FEATURE_NAMES,
    LidarNoiseSensitiveDiagnostics,
)

from trust_robot.ml_lidar_extended_13_feature_registration_dataset import (
    ALL_TRAIN,
    DEVELOPMENT_CHECK,
    DEVELOPMENT_TRAIN,
    EXPECTED_DIAGNOSTIC_COUNTS,
    FAMILIES,
    LEGACY_RMSE_ABS_TOL,
    LEGACY_RMSE_REL_TOL,
    assert_parent_legacy_identity,
    build_corruption_specs,
    build_extended_sample,
    evenly_spaced_two_scan_starts,
    legacy_features_from_registration,
    partition_for_trajectory,
)


def diagnostics():
    return (
        LidarNoiseSensitiveDiagnostics(
            final_nearest_neighbor_mean_m=
                0.05,

            final_nearest_neighbor_std_m=
                0.02,

            final_nearest_neighbor_median_m=
                0.04,

            final_nearest_neighbor_mad_m=
                0.01,

            final_nearest_neighbor_p75_m=
                0.06,

            final_nearest_neighbor_p90_m=
                0.08,

            final_nearest_neighbor_p95_m=
                0.09,

            final_nearest_neighbor_max_m=
                0.20,
        )
    )


def parent_sample():
    return {
        "outer_split":
            "TRAIN",

        "development_partition":
            "development_train",

        "trajectory":
            "Circle_01",

        "window_start_scan_index":
            0,

        "degradation_family":
            "CLEAN",

        "sample_id":
            "sample-test",

        "binary_degraded_label":
            0,

        "feature_names": [
            "source_point_count",
            "target_point_count",
            "fixed_point_iterations",
            "final_correspondence_count",
            "final_nearest_neighbor_rmse_m",
        ],

        "feature_values": [
            100,
            90,
            7,
            100,
            0.05,
        ],

        "label_is_real_physical_health_truth":
            False,
    }


class Extended13FeatureDatasetTests(
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

    def test_03_all_train_count(self):
        self.assertEqual(
            len(ALL_TRAIN),
            22,
        )

    def test_04_split_disjoint(self):
        self.assertFalse(
            set(DEVELOPMENT_TRAIN)
            & set(DEVELOPMENT_CHECK)
        )

    def test_05_family_count(self):
        self.assertEqual(
            len(FAMILIES),
            4,
        )

    def test_06_clean_first(self):
        self.assertEqual(
            FAMILIES[0],
            "CLEAN",
        )

    def test_07_three_corruption_specs(self):
        self.assertEqual(
            len(
                build_corruption_specs()
            ),
            3,
        )

    def test_08_combined_feature_count(self):
        self.assertEqual(
            len(
                COMBINED_FEATURE_NAMES
            ),
            13,
        )

    def test_09_rmse_rel_tol(self):
        self.assertEqual(
            LEGACY_RMSE_REL_TOL,
            1.0e-12,
        )

    def test_10_rmse_abs_tol(self):
        self.assertEqual(
            LEGACY_RMSE_ABS_TOL,
            1.0e-12,
        )

    def test_11_partition_train(self):
        self.assertEqual(
            partition_for_trajectory(
                "Circle_01"
            ),
            "development_train",
        )

    def test_12_partition_check(self):
        self.assertEqual(
            partition_for_trajectory(
                "street_09"
            ),
            "development_check",
        )

    def test_13_room02_window_count(self):
        self.assertEqual(
            len(
                evenly_spaced_two_scan_starts(
                    EXPECTED_DIAGNOSTIC_COUNTS[
                        "room_02"
                    ]
                )
            ),
            50,
        )

    def test_14_total_windows(self):
        self.assertEqual(
            len(ALL_TRAIN)
            * 50,
            1100,
        )

    def test_15_total_registrations(self):
        self.assertEqual(
            len(ALL_TRAIN)
            * 50
            * 4,
            4400,
        )

    def test_16_legacy_identity_accepts_equal(self):
        assert_parent_legacy_identity(
            [
                100,
                90,
                7,
                100,
                0.05,
            ],
            [
                100,
                90,
                7,
                100,
                0.05,
            ],
        )

    def test_17_legacy_identity_rejects_count_change(self):
        with self.assertRaises(
            ValueError
        ):
            assert_parent_legacy_identity(
                [
                    101,
                    90,
                    7,
                    100,
                    0.05,
                ],
                [
                    100,
                    90,
                    7,
                    100,
                    0.05,
                ],
            )

    def test_18_legacy_identity_rejects_rmse_change(self):
        with self.assertRaises(
            ValueError
        ):
            assert_parent_legacy_identity(
                [
                    100,
                    90,
                    7,
                    100,
                    0.06,
                ],
                [
                    100,
                    90,
                    7,
                    100,
                    0.05,
                ],
            )

    def test_19_registration_feature_extraction(self):
        fake = SimpleNamespace(
            diagnostics=
                SimpleNamespace(
                    source_point_count=
                        100,

                    target_point_count=
                        90,

                    fixed_point_iterations=
                        7,

                    final_correspondence_count=
                        100,

                    final_nearest_neighbor_rmse_m=
                        0.05,
                )
        )

        self.assertEqual(
            legacy_features_from_registration(
                fake
            ),
            (
                100.0,
                90.0,
                7.0,
                100.0,
                0.05,
            ),
        )

    def test_20_extended_sample_count(self):
        result = build_extended_sample(
            parent_sample=
                parent_sample(),

            observed_legacy_features=[
                100,
                90,
                7,
                100,
                0.05,
            ],

            extended_diagnostics=
                diagnostics(),
        )

        self.assertEqual(
            len(
                result[
                    "feature_values"
                ]
            ),
            13,
        )

    def test_21_extended_preserves_sample_id(self):
        result = build_extended_sample(
            parent_sample=
                parent_sample(),

            observed_legacy_features=[
                100,
                90,
                7,
                100,
                0.05,
            ],

            extended_diagnostics=
                diagnostics(),
        )

        self.assertEqual(
            result[
                "sample_id"
            ],
            "sample-test",
        )

        self.assertEqual(
            result[
                "parent_sample_id"
            ],
            "sample-test",
        )

    def test_22_extended_population_unchanged(self):
        result = build_extended_sample(
            parent_sample=
                parent_sample(),

            observed_legacy_features=[
                100,
                90,
                7,
                100,
                0.05,
            ],

            extended_diagnostics=
                diagnostics(),
        )

        self.assertFalse(
            result[
                "parent_sample_population_changed"
            ]
        )

    def test_23_extended_registration_not_modified(self):
        result = build_extended_sample(
            parent_sample=
                parent_sample(),

            observed_legacy_features=[
                100,
                90,
                7,
                100,
                0.05,
            ],

            extended_diagnostics=
                diagnostics(),
        )

        self.assertFalse(
            result[
                "registration_algorithm_modified"
            ]
        )

    def test_24_all_trajectories_nonoverlapping_windows(self):
        for trajectory in ALL_TRAIN:
            starts = (
                evenly_spaced_two_scan_starts(
                    EXPECTED_DIAGNOSTIC_COUNTS[
                        trajectory
                    ]
                )
            )

            self.assertGreaterEqual(
                min(
                    right - left
                    for left, right
                    in zip(
                        starts,
                        starts[1:],
                    )
                ),
                2,
            )


if __name__ == "__main__":
    unittest.main()
