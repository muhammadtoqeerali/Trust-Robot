import unittest

import numpy as np

from trust_robot.corruption import (
    EventStream,
    SensorModality,
)

from trust_robot.lidar_point_level_corruption import (
    LidarPointCorruptionError,
    LidarPointCorruptionFamily,
    LidarPointCorruptionSpec,
    apply_lidar_point_corruption,
)


def full_circle_points(
    count=360,
):
    angles = np.linspace(
        -np.pi,
        np.pi,
        count,
        endpoint=False,
    )

    radii = (
        5.0
        + 0.5
        * np.sin(
            angles
            * 3.0
        )
    )

    return np.column_stack(
        (
            radii
            * np.cos(
                angles
            ),

            radii
            * np.sin(
                angles
            ),

            np.linspace(
                -1.0,
                1.0,
                count,
            ),
        )
    ).astype(
        np.float64
    )


def make_stream():
    previous = full_circle_points(
        360
    )

    current = (
        previous
        + np.asarray(
            [
                0.01,
                -0.02,
                0.005,
            ],
            dtype=np.float64,
        )
    )

    return EventStream(
        modality=
            SensorModality.LIDAR,

        source_id=
            "synthetic_test",

        timestamps_ns=
            np.asarray(
                [
                    100,
                    200,
                ],
                dtype=np.int64,
            ),

        payloads=(
            previous,
            current,
        ),

        metadata={
            "test":
                True,
        },
    )


def dropout_spec():
    return LidarPointCorruptionSpec(
        family=
            LidarPointCorruptionFamily.POINT_DROPOUT,

        target_event_index=
            1,

        remove_fraction=
            0.30,
    )


def noise_spec():
    return LidarPointCorruptionSpec(
        family=
            LidarPointCorruptionFamily.XYZ_GAUSSIAN_NOISE,

        target_event_index=
            1,

        sigma_m=
            0.05,
    )


def occlusion_spec():
    return LidarPointCorruptionSpec(
        family=
            LidarPointCorruptionFamily.AZIMUTH_SECTOR_OCCLUSION,

        target_event_index=
            1,

        sector_width_degrees=
            60.0,
    )


class LidarPointLevelCorruptionTests(
    unittest.TestCase
):
    def test_01_three_families(self):
        self.assertEqual(
            {
                item.value
                for item
                in LidarPointCorruptionFamily
            },
            {
                "POINT_DROPOUT",
                "XYZ_GAUSSIAN_NOISE",
                "AZIMUTH_SECTOR_OCCLUSION",
            },
        )

    def test_02_dropout_is_deterministic(self):
        first = apply_lidar_point_corruption(
            make_stream(),
            dropout_spec(),
            window_key=
                "window-A",
        )

        second = apply_lidar_point_corruption(
            make_stream(),
            dropout_spec(),
            window_key=
                "window-A",
        )

        np.testing.assert_array_equal(
            first.corrupt.payloads[
                1
            ],
            second.corrupt.payloads[
                1
            ],
        )

    def test_03_dropout_removes_expected_count(self):
        result = apply_lidar_point_corruption(
            make_stream(),
            dropout_spec(),
            window_key=
                "window-A",
        )

        self.assertEqual(
            result.truth[
                "before_point_count"
            ],
            360,
        )

        self.assertEqual(
            result.truth[
                "removed_point_count"
            ],
            108,
        )

        self.assertEqual(
            result.truth[
                "after_point_count"
            ],
            252,
        )

    def test_04_dropout_actual_fraction(self):
        result = apply_lidar_point_corruption(
            make_stream(),
            dropout_spec(),
            window_key=
                "window-A",
        )

        self.assertAlmostEqual(
            result.truth[
                "remove_fraction_actual"
            ],
            0.30,
        )

    def test_05_dropout_retained_points_are_original_points(self):
        stream = make_stream()

        result = apply_lidar_point_corruption(
            stream,
            dropout_spec(),
            window_key=
                "window-A",
        )

        original = {
            tuple(
                row
            )
            for row
            in stream.payloads[
                1
            ]
        }

        for row in result.corrupt.payloads[
            1
        ]:
            self.assertIn(
                tuple(
                    row
                ),
                original,
            )

    def test_06_dropout_different_window_changes_selection(self):
        first = apply_lidar_point_corruption(
            make_stream(),
            dropout_spec(),
            window_key=
                "window-A",
        )

        second = apply_lidar_point_corruption(
            make_stream(),
            dropout_spec(),
            window_key=
                "window-B",
        )

        self.assertFalse(
            np.array_equal(
                first.corrupt.payloads[
                    1
                ],
                second.corrupt.payloads[
                    1
                ],
            )
        )

    def test_07_noise_is_deterministic(self):
        first = apply_lidar_point_corruption(
            make_stream(),
            noise_spec(),
            window_key=
                "window-A",
        )

        second = apply_lidar_point_corruption(
            make_stream(),
            noise_spec(),
            window_key=
                "window-A",
        )

        np.testing.assert_array_equal(
            first.corrupt.payloads[
                1
            ],
            second.corrupt.payloads[
                1
            ],
        )

    def test_08_noise_preserves_point_count(self):
        result = apply_lidar_point_corruption(
            make_stream(),
            noise_spec(),
            window_key=
                "window-A",
        )

        self.assertEqual(
            result.truth[
                "before_point_count"
            ],
            result.truth[
                "after_point_count"
            ],
        )

    def test_09_noise_changes_xyz(self):
        stream = make_stream()

        result = apply_lidar_point_corruption(
            stream,
            noise_spec(),
            window_key=
                "window-A",
        )

        self.assertFalse(
            np.array_equal(
                stream.payloads[
                    1
                ],
                result.corrupt.payloads[
                    1
                ],
            )
        )

    def test_10_noise_sigma_recorded(self):
        result = apply_lidar_point_corruption(
            make_stream(),
            noise_spec(),
            window_key=
                "window-A",
        )

        self.assertEqual(
            result.truth[
                "sigma_m"
            ],
            0.05,
        )

    def test_11_noise_different_window_changes_noise(self):
        first = apply_lidar_point_corruption(
            make_stream(),
            noise_spec(),
            window_key=
                "window-A",
        )

        second = apply_lidar_point_corruption(
            make_stream(),
            noise_spec(),
            window_key=
                "window-B",
        )

        self.assertFalse(
            np.array_equal(
                first.corrupt.payloads[
                    1
                ],
                second.corrupt.payloads[
                    1
                ],
            )
        )

    def test_12_occlusion_is_deterministic(self):
        first = apply_lidar_point_corruption(
            make_stream(),
            occlusion_spec(),
            window_key=
                "window-A",
        )

        second = apply_lidar_point_corruption(
            make_stream(),
            occlusion_spec(),
            window_key=
                "window-A",
        )

        np.testing.assert_array_equal(
            first.corrupt.payloads[
                1
            ],
            second.corrupt.payloads[
                1
            ],
        )

        self.assertEqual(
            first.truth[
                "sector_center_degrees"
            ],
            second.truth[
                "sector_center_degrees"
            ],
        )

    def test_13_occlusion_removes_points(self):
        result = apply_lidar_point_corruption(
            make_stream(),
            occlusion_spec(),
            window_key=
                "window-A",
        )

        self.assertGreater(
            result.truth[
                "removed_point_count"
            ],
            0,
        )

        self.assertLess(
            result.truth[
                "after_point_count"
            ],
            result.truth[
                "before_point_count"
            ],
        )

    def test_14_occlusion_width_recorded(self):
        result = apply_lidar_point_corruption(
            make_stream(),
            occlusion_spec(),
            window_key=
                "window-A",
        )

        self.assertEqual(
            result.truth[
                "sector_width_degrees"
            ],
            60.0,
        )

    def test_15_occlusion_center_within_range(self):
        result = apply_lidar_point_corruption(
            make_stream(),
            occlusion_spec(),
            window_key=
                "window-A",
        )

        center = result.truth[
            "sector_center_degrees"
        ]

        self.assertGreaterEqual(
            center,
            -180.0,
        )

        self.assertLess(
            center,
            180.0,
        )

    def test_16_all_operators_preserve_previous_event(self):
        stream = make_stream()

        for spec in (
            dropout_spec(),
            noise_spec(),
            occlusion_spec(),
        ):
            result = apply_lidar_point_corruption(
                stream,
                spec,
                window_key=
                    "window-A",
            )

            np.testing.assert_array_equal(
                result.corrupt.payloads[
                    0
                ],
                stream.payloads[
                    0
                ],
            )

    def test_17_all_operators_preserve_timestamps(self):
        stream = make_stream()

        for spec in (
            dropout_spec(),
            noise_spec(),
            occlusion_spec(),
        ):
            result = apply_lidar_point_corruption(
                stream,
                spec,
                window_key=
                    "window-A",
            )

            np.testing.assert_array_equal(
                result.corrupt.timestamps_ns,
                stream.timestamps_ns,
            )

    def test_18_clean_stream_not_mutated(self):
        stream = make_stream()

        before_previous = stream.payloads[
            0
        ].copy()

        before_current = stream.payloads[
            1
        ].copy()

        for spec in (
            dropout_spec(),
            noise_spec(),
            occlusion_spec(),
        ):
            apply_lidar_point_corruption(
                stream,
                spec,
                window_key=
                    "window-A",
            )

        np.testing.assert_array_equal(
            stream.payloads[
                0
            ],
            before_previous,
        )

        np.testing.assert_array_equal(
            stream.payloads[
                1
            ],
            before_current,
        )

    def test_19_truth_denies_real_health(self):
        for spec in (
            dropout_spec(),
            noise_spec(),
            occlusion_spec(),
        ):
            result = apply_lidar_point_corruption(
                make_stream(),
                spec,
                window_key=
                    "window-A",
            )

            self.assertFalse(
                result.truth[
                    "synthetic_truth_is_real_physical_health_truth"
                ]
            )

    def test_20_truth_denies_physical_cause(self):
        result = apply_lidar_point_corruption(
            make_stream(),
            dropout_spec(),
            window_key=
                "window-A",
        )

        self.assertFalse(
            result.truth[
                "synthetic_truth_is_physical_cause_evidence"
            ]
        )

    def test_21_corrupt_metadata_marks_synthetic(self):
        result = apply_lidar_point_corruption(
            make_stream(),
            dropout_spec(),
            window_key=
                "window-A",
        )

        self.assertTrue(
            result.corrupt.metadata[
                "synthetic_point_level_corruption"
            ]
        )

    def test_22_bad_dropout_fraction_rejected(self):
        with self.assertRaises(
            LidarPointCorruptionError
        ):
            apply_lidar_point_corruption(
                make_stream(),
                LidarPointCorruptionSpec(
                    family=
                        LidarPointCorruptionFamily.POINT_DROPOUT,

                    remove_fraction=
                        1.0,
                ),
                window_key=
                    "window-A",
            )

    def test_23_bad_noise_sigma_rejected(self):
        with self.assertRaises(
            LidarPointCorruptionError
        ):
            apply_lidar_point_corruption(
                make_stream(),
                LidarPointCorruptionSpec(
                    family=
                        LidarPointCorruptionFamily.XYZ_GAUSSIAN_NOISE,

                    sigma_m=
                        0.0,
                ),
                window_key=
                    "window-A",
            )

    def test_24_bad_occlusion_width_rejected(self):
        with self.assertRaises(
            LidarPointCorruptionError
        ):
            apply_lidar_point_corruption(
                make_stream(),
                LidarPointCorruptionSpec(
                    family=
                        LidarPointCorruptionFamily.AZIMUTH_SECTOR_OCCLUSION,

                    sector_width_degrees=
                        360.0,
                ),
                window_key=
                    "window-A",
            )

    def test_25_empty_window_key_rejected(self):
        with self.assertRaises(
            LidarPointCorruptionError
        ):
            apply_lidar_point_corruption(
                make_stream(),
                dropout_spec(),
                window_key=
                    "",
            )

    def test_26_invalid_target_event_rejected(self):
        with self.assertRaises(
            LidarPointCorruptionError
        ):
            apply_lidar_point_corruption(
                make_stream(),
                LidarPointCorruptionSpec(
                    family=
                        LidarPointCorruptionFamily.POINT_DROPOUT,

                    target_event_index=
                        2,

                    remove_fraction=
                        0.30,
                ),
                window_key=
                    "window-A",
            )

    def test_27_non_lidar_modality_rejected(self):
        points = full_circle_points(
            360
        )

        stream = EventStream(
            modality=
                SensorModality.CAMERA,

            source_id=
                "wrong_modality",

            timestamps_ns=
                np.asarray(
                    [
                        100,
                        200,
                    ],
                    dtype=np.int64,
                ),

            payloads=(
                points,
                points.copy(),
            ),
        )

        with self.assertRaises(
            LidarPointCorruptionError
        ):
            apply_lidar_point_corruption(
                stream,
                dropout_spec(),
                window_key=
                    "window-A",
            )

    def test_28_nonfinite_payload_rejected(self):
        stream = make_stream()

        bad_current = stream.payloads[
            1
        ].copy()

        bad_current[
            0,
            0
        ] = np.nan

        bad = EventStream(
            modality=
                SensorModality.LIDAR,

            source_id=
                stream.source_id,

            timestamps_ns=
                stream.timestamps_ns.copy(),

            payloads=(
                stream.payloads[
                    0
                ].copy(),
                bad_current,
            ),
        )

        with self.assertRaises(
            LidarPointCorruptionError
        ):
            apply_lidar_point_corruption(
                bad,
                dropout_spec(),
                window_key=
                    "window-A",
            )

    def test_29_truth_digest_is_deterministic(self):
        first = apply_lidar_point_corruption(
            make_stream(),
            noise_spec(),
            window_key=
                "window-A",
        )

        second = apply_lidar_point_corruption(
            make_stream(),
            noise_spec(),
            window_key=
                "window-A",
        )

        self.assertEqual(
            first.truth[
                "truth_content_sha256"
            ],
            second.truth[
                "truth_content_sha256"
            ],
        )

    def test_30_three_families_produce_distinct_truth_digests(self):
        digests = set()

        for spec in (
            dropout_spec(),
            noise_spec(),
            occlusion_spec(),
        ):
            result = apply_lidar_point_corruption(
                make_stream(),
                spec,
                window_key=
                    "window-A",
            )

            digests.add(
                result.truth[
                    "truth_content_sha256"
                ]
            )

        self.assertEqual(
            len(
                digests
            ),
            3,
        )


if __name__ == "__main__":
    unittest.main()
