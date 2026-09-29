from types import SimpleNamespace
import inspect
import unittest

import numpy as np

from trust_robot.lidar_frontend import (
    register_current_scan_to_previous,
)

from trust_robot.lidar_noise_sensitive_diagnostics import (
    COMBINED_FEATURE_NAMES,
    LEGACY_PHASE4_FEATURE_NAMES,
    NOISE_SENSITIVE_FEATURE_NAMES,
    NOISE_SENSITIVE_FEATURE_UNITS,
    RMSE_IDENTITY_ABS_TOL,
    RMSE_IDENTITY_REL_TOL,
    LidarNoiseSensitiveDiagnosticError,
    LidarNoiseSensitiveDiagnostics,
    combine_legacy_and_noise_sensitive_features,
    extract_lidar_noise_sensitive_diagnostics,
)


def point_cloud(
    count=720,
):
    angles = np.linspace(
        -np.pi,
        np.pi,
        count,
        endpoint=False,
    )

    radius = (
        8.0
        + 0.7
        * np.sin(
            angles * 4.0
        )
        + 0.2
        * np.cos(
            angles * 11.0
        )
    )

    return np.column_stack(
        (
            radius
            * np.cos(
                angles
            ),

            radius
            * np.sin(
                angles
            ),

            0.6
            * np.sin(
                angles * 2.0
            ),
        )
    ).astype(
        np.float64
    )


def clean_pair():
    previous = point_cloud()

    current = (
        previous
        + np.asarray(
            [
                0.03,
                -0.02,
                0.01,
            ],
            dtype=np.float64,
        )
    )

    return (
        previous,
        current,
    )


def noisy_pair():
    previous, current = (
        clean_pair()
    )

    rng = np.random.Generator(
        np.random.PCG64(
            20260929
        )
    )

    noisy = (
        current
        + rng.normal(
            0.0,
            0.05,
            size=current.shape,
        )
    )

    return (
        previous,
        noisy,
    )


def extract_pair(
    pair,
):
    previous, current = pair

    registration = (
        register_current_scan_to_previous(
            previous,
            current,
        )
    )

    extended = (
        extract_lidar_noise_sensitive_diagnostics(
            previous,
            current,
            registration,
        )
    )

    return (
        registration,
        extended,
    )


class LidarNoiseSensitiveDiagnosticsTests(
    unittest.TestCase
):
    def test_01_legacy_feature_count(self):
        self.assertEqual(
            len(
                LEGACY_PHASE4_FEATURE_NAMES
            ),
            5,
        )

    def test_02_new_feature_count(self):
        self.assertEqual(
            len(
                NOISE_SENSITIVE_FEATURE_NAMES
            ),
            8,
        )

    def test_03_combined_feature_count(self):
        self.assertEqual(
            len(
                COMBINED_FEATURE_NAMES
            ),
            13,
        )

    def test_04_all_new_units_are_metres(self):
        self.assertEqual(
            NOISE_SENSITIVE_FEATURE_UNITS,
            (
                "m",
                "m",
                "m",
                "m",
                "m",
                "m",
                "m",
                "m",
            ),
        )

    def test_05_identity_tolerances(self):
        self.assertEqual(
            RMSE_IDENTITY_REL_TOL,
            1.0e-12,
        )

        self.assertEqual(
            RMSE_IDENTITY_ABS_TOL,
            1.0e-12,
        )

    def test_06_clean_extraction_count(self):
        _, result = extract_pair(
            clean_pair()
        )

        self.assertEqual(
            len(
                result.feature_values()
            ),
            8,
        )

    def test_07_noisy_extraction_count(self):
        _, result = extract_pair(
            noisy_pair()
        )

        self.assertEqual(
            len(
                result.feature_values()
            ),
            8,
        )

    def test_08_clean_values_finite(self):
        _, result = extract_pair(
            clean_pair()
        )

        self.assertTrue(
            all(
                np.isfinite(
                    value
                )
                for value
                in result.feature_values()
            )
        )

    def test_09_noisy_values_finite(self):
        _, result = extract_pair(
            noisy_pair()
        )

        self.assertTrue(
            all(
                np.isfinite(
                    value
                )
                for value
                in result.feature_values()
            )
        )

    def test_10_noisy_std_exceeds_clean(self):
        _, clean = extract_pair(
            clean_pair()
        )

        _, noisy = extract_pair(
            noisy_pair()
        )

        self.assertGreater(
            noisy.final_nearest_neighbor_std_m,
            clean.final_nearest_neighbor_std_m,
        )

    def test_11_noisy_median_exceeds_clean(self):
        _, clean = extract_pair(
            clean_pair()
        )

        _, noisy = extract_pair(
            noisy_pair()
        )

        self.assertGreater(
            noisy.final_nearest_neighbor_median_m,
            clean.final_nearest_neighbor_median_m,
        )

    def test_12_noisy_p95_exceeds_clean(self):
        _, clean = extract_pair(
            clean_pair()
        )

        _, noisy = extract_pair(
            noisy_pair()
        )

        self.assertGreater(
            noisy.final_nearest_neighbor_p95_m,
            clean.final_nearest_neighbor_p95_m,
        )

    def test_13_max_ge_p95(self):
        _, result = extract_pair(
            noisy_pair()
        )

        self.assertGreaterEqual(
            result.final_nearest_neighbor_max_m,
            result.final_nearest_neighbor_p95_m,
        )

    def test_14_p95_ge_p90(self):
        _, result = extract_pair(
            noisy_pair()
        )

        self.assertGreaterEqual(
            result.final_nearest_neighbor_p95_m,
            result.final_nearest_neighbor_p90_m,
        )

    def test_15_p90_ge_p75(self):
        _, result = extract_pair(
            noisy_pair()
        )

        self.assertGreaterEqual(
            result.final_nearest_neighbor_p90_m,
            result.final_nearest_neighbor_p75_m,
        )

    def test_16_p75_ge_median(self):
        _, result = extract_pair(
            noisy_pair()
        )

        self.assertGreaterEqual(
            result.final_nearest_neighbor_p75_m,
            result.final_nearest_neighbor_median_m,
        )

    def test_17_mad_nonnegative(self):
        _, result = extract_pair(
            noisy_pair()
        )

        self.assertGreaterEqual(
            result.final_nearest_neighbor_mad_m,
            0.0,
        )

    def test_18_to_dict_exact_names(self):
        _, result = extract_pair(
            noisy_pair()
        )

        self.assertEqual(
            tuple(
                result.to_dict()
            ),
            NOISE_SENSITIVE_FEATURE_NAMES,
        )

    def test_19_combined_values_have_13_entries(self):
        _, result = extract_pair(
            noisy_pair()
        )

        combined = (
            combine_legacy_and_noise_sensitive_features(
                [
                    720,
                    720,
                    5,
                    720,
                    0.1,
                ],
                result,
            )
        )

        self.assertEqual(
            len(
                combined
            ),
            13,
        )

    def test_20_invalid_previous_shape_rejected(self):
        previous, current = clean_pair()

        registration = (
            register_current_scan_to_previous(
                previous,
                current,
            )
        )

        with self.assertRaises(
            LidarNoiseSensitiveDiagnosticError
        ):
            extract_lidar_noise_sensitive_diagnostics(
                previous[:, :2],
                current,
                registration,
            )

    def test_21_invalid_current_shape_rejected(self):
        previous, current = clean_pair()

        registration = (
            register_current_scan_to_previous(
                previous,
                current,
            )
        )

        with self.assertRaises(
            LidarNoiseSensitiveDiagnosticError
        ):
            extract_lidar_noise_sensitive_diagnostics(
                previous,
                current[:, :2],
                registration,
            )

    def test_22_nonfinite_previous_rejected(self):
        previous, current = clean_pair()

        registration = (
            register_current_scan_to_previous(
                previous,
                current,
            )
        )

        bad = previous.copy()

        bad[
            0,
            0
        ] = np.nan

        with self.assertRaises(
            LidarNoiseSensitiveDiagnosticError
        ):
            extract_lidar_noise_sensitive_diagnostics(
                bad,
                current,
                registration,
            )

    def test_23_nonfinite_current_rejected(self):
        previous, current = clean_pair()

        registration = (
            register_current_scan_to_previous(
                previous,
                current,
            )
        )

        bad = current.copy()

        bad[
            0,
            0
        ] = np.inf

        with self.assertRaises(
            LidarNoiseSensitiveDiagnosticError
        ):
            extract_lidar_noise_sensitive_diagnostics(
                previous,
                bad,
                registration,
            )

    def test_24_missing_registration_pose_rejected(self):
        previous, current = clean_pair()

        fake = SimpleNamespace(
            diagnostics=
                SimpleNamespace(
                    final_nearest_neighbor_rmse_m=
                        0.0,
                )
        )

        with self.assertRaises(
            LidarNoiseSensitiveDiagnosticError
        ):
            extract_lidar_noise_sensitive_diagnostics(
                previous,
                current,
                fake,
            )

    def test_25_tampered_frozen_rmse_rejected(self):
        previous, current = noisy_pair()

        registration = (
            register_current_scan_to_previous(
                previous,
                current,
            )
        )

        fake = SimpleNamespace(
            previous_lidar_T_current_lidar=
                registration
                .previous_lidar_T_current_lidar,

            diagnostics=
                SimpleNamespace(
                    final_nearest_neighbor_rmse_m=
                        (
                            registration
                            .diagnostics
                            .final_nearest_neighbor_rmse_m
                            + 0.001
                        ),
                ),
        )

        with self.assertRaises(
            LidarNoiseSensitiveDiagnosticError
        ):
            extract_lidar_noise_sensitive_diagnostics(
                previous,
                current,
                fake,
            )

    def test_26_inputs_not_mutated(self):
        previous, current = noisy_pair()

        previous_before = previous.copy()
        current_before = current.copy()

        registration = (
            register_current_scan_to_previous(
                previous,
                current,
            )
        )

        extract_lidar_noise_sensitive_diagnostics(
            previous,
            current,
            registration,
        )

        np.testing.assert_array_equal(
            previous,
            previous_before,
        )

        np.testing.assert_array_equal(
            current,
            current_before,
        )

    def test_27_extraction_deterministic(self):
        previous, current = noisy_pair()

        registration = (
            register_current_scan_to_previous(
                previous,
                current,
            )
        )

        first = (
            extract_lidar_noise_sensitive_diagnostics(
                previous,
                current,
                registration,
            )
        )

        second = (
            extract_lidar_noise_sensitive_diagnostics(
                previous,
                current,
                registration,
            )
        )

        self.assertEqual(
            first,
            second,
        )

    def test_28_public_extractor_does_not_refit_registration(self):
        source = inspect.getsource(
            extract_lidar_noise_sensitive_diagnostics
        )

        self.assertNotIn(
            "register_current_scan_to_previous",
            source,
        )

        self.assertNotIn(
            "rigid_transform_kabsch",
            source,
        )

    def test_29_no_threshold_features_selected(self):
        self.assertFalse(
            any(
                "fraction_"
                in name
                or "threshold"
                in name
                for name
                in NOISE_SENSITIVE_FEATURE_NAMES
            )
        )

    def test_30_no_convergence_history_features_selected(self):
        forbidden = (
            "update",
            "history",
            "iteration",
            "rotation",
            "translation",
        )

        self.assertFalse(
            any(
                token in name
                for name
                in NOISE_SENSITIVE_FEATURE_NAMES
                for token
                in forbidden
            )
        )


if __name__ == "__main__":
    unittest.main()
