import unittest
from dataclasses import replace

import numpy as np

from trust_robot.clean_backbone import PoseSE3
from trust_robot.analytic_inertial_15d import (
    SIGMA_LIDAR_P,
    initial_state,
    lidar_residual,
    make_fixture,
)
from trust_robot.analytic_marginalized_fusion import (
    estimate_marginalized,
)
from trust_robot.analytic_three_modality_bridge import (
    manufactured_camera_packets,
)
from trust_robot.analytic_separated_modalities import (
    CAMERA_POSITION_SCALE_M,
    camera_residual,
    camera_factor_map,
    estimate_separated,
    execute,
    execute_case,
)


class SeparatedModalityTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.fixture, cls.truth = make_fixture("clean")
        cls.camera = manufactured_camera_packets(
            cls.truth, seed=13
        )

    def test_camera_zero_residual(self):
        x = initial_state()
        actual = camera_residual(
            x, x, PoseSE3.identity()
        )
        np.testing.assert_allclose(actual, 0, atol=1e-12)

    def test_camera_lidar_separate_scales(self):
        a = initial_state()
        b = initial_state()
        b[0] = CAMERA_POSITION_SCALE_M

        camera = camera_residual(
            a, b, PoseSE3.identity()
        )
        lidar = lidar_residual(
            a, b, PoseSE3.identity()
        )

        self.assertAlmostEqual(camera[0], 1.0)
        self.assertAlmostEqual(
            lidar[0], CAMERA_POSITION_SCALE_M/SIGMA_LIDAR_P
        )
        self.assertNotAlmostEqual(camera[0], lidar[0])

    def test_legacy_camera_disabled_parity(self):
        legacy, old_audit = estimate_marginalized(
            self.fixture
        )
        separated, new_audit = estimate_separated(
            self.fixture, ()
        )

        self.assertEqual(legacy, separated)
        self.assertEqual(
            old_audit["schur_elimination_count"],
            new_audit["schur_elimination_count"],
        )
        self.assertEqual(new_audit["camera_factor_count"], 0)

    def test_same_edge_factors_preserved(self):
        _, audit = estimate_separated(
            self.fixture, self.camera
        )

        self.assertEqual(audit["camera_factor_count"], 2)
        self.assertEqual(audit["lidar_factor_count"], 7)
        self.assertEqual(audit["imu_factor_count"], 4)
        self.assertEqual(audit["accepted_window_count"], 4)
        self.assertEqual(audit["schur_elimination_count"], 3)

        self.assertTrue(
            audit["same_edge_camera_and_lidar_supported"]
        )

    def test_separate_consumption_ledgers(self):
        _, audit = estimate_separated(
            self.fixture, self.camera
        )

        camera_total = (
            len(audit["consumed_camera_ids"])
            + len(audit["remaining_camera_ids"])
        )
        lidar_total = (
            len(audit["consumed_lidar_keys"])
            + len(audit["remaining_lidar_keys"])
        )

        self.assertEqual(camera_total, 2)
        self.assertEqual(lidar_total, 7)
        self.assertFalse(
            audit["factor_reuse_after_marginalization"]
        )
        self.assertEqual(
            audit["unaccounted_factor_count"], 0
        )

    def test_dropout_retains_camera_source(self):
        fixture, truth = make_fixture("lidar_dropout")
        packets = manufactured_camera_packets(
            truth, seed=13
        )

        _, audit = estimate_separated(fixture, packets)

        self.assertEqual(audit["lidar_factor_count"], 3)
        self.assertEqual(audit["camera_factor_count"], 2)
        self.assertEqual(audit["accepted_window_count"], 4)

    def test_duplicate_camera_id_rejected(self):
        duplicate = replace(
            self.camera[1],
            measurement_id=self.camera[0].measurement_id,
        )

        with self.assertRaises(ValueError):
            camera_factor_map(
                (self.camera[0], duplicate)
            )

    def test_duplicate_camera_edge_rejected(self):
        duplicate = replace(
            self.camera[0],
            measurement_id="independent_duplicate_id",
        )

        with self.assertRaises(ValueError):
            camera_factor_map(
                (self.camera[0], duplicate)
            )

    def test_missing_camera_requirement_fails_closed(self):
        with self.assertRaisesRegex(
            ValueError, "Camera factor unavailable"
        ):
            estimate_separated(
                self.fixture,
                (),
                require_camera=True,
            )

    def test_invalid_policy_rejected(self):
        with self.assertRaises(ValueError):
            estimate_separated(
                self.fixture,
                self.camera,
                require_numerical_support="yes",
            )

    def test_seeded_repeat(self):
        self.assertEqual(
            execute_case("clean", 31),
            execute_case("clean", 31),
        )

    def test_complete_scientific_scope(self):
        report = execute()
        self.assertEqual(report["case_count"], 12)
        self.assertFalse(
            report["camera_visual_frontend_implemented"]
        )
        self.assertFalse(
            report["real_three_modality_localization_verified"]
        )
        self.assertFalse(
            report["real_sensor_scoring_authorized"]
        )
        self.assertFalse(
            report["existing_estimator_modified"]
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
