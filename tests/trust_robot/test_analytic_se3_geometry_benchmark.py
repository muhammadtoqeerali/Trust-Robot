import inspect
import math
import unittest

import numpy as np

from trust_robot.analytic_se3_geometry_benchmark import (
    CONDITIONS,
    FRAMES,
    POINTS,
    analytic_pose,
    canonical,
    estimate,
    evaluate,
    execute,
    make_fixture,
)
from trust_robot.factor_conditioning import (
    FactorConditioningContractError,
    assert_factor_scale_execution_authorized,
)
from trust_robot.auxiliary_consistency import (
    AuxiliaryConsistencyContractError,
    assert_consistency_execution_authorized,
)


class AnalyticGeometryTests(unittest.TestCase):
    def test_reference_is_not_estimator_argument(self):
        self.assertEqual(
            list(inspect.signature(estimate).parameters),
            ["clouds"],
        )

    def test_landmark_geometry_is_three_dimensional(self):
        scans, reference, landmarks = make_fixture()

        self.assertEqual(landmarks.shape, (POINTS, 3))
        self.assertEqual(np.linalg.matrix_rank(
            landmarks - landmarks.mean(axis=0)
        ), 3)
        self.assertEqual(len(reference), FRAMES)
        self.assertEqual(tuple(scans), CONDITIONS)

    def test_nontrivial_translation_and_rotation(self):
        t0, r0 = analytic_pose(0)
        t1, r1 = analytic_pose(FRAMES - 1)

        self.assertGreater(
            float(np.linalg.norm(t1-t0)), 0.3
        )
        self.assertGreater(
            float((r0.inv() * r1).magnitude()), 0.05
        )

    def test_fixture_does_not_change_clean_clouds(self):
        scans, _, _ = make_fixture()

        self.assertTrue(np.array_equal(
            scans["clean"][0], scans["noise"][0]
        ))
        self.assertTrue(np.array_equal(
            scans["clean"][0], scans["offset"][0]
        ))

        self.assertFalse(np.array_equal(
            scans["clean"][8], scans["noise"][8]
        ))
        self.assertFalse(np.array_equal(
            scans["clean"][8], scans["offset"][8]
        ))

        self.assertEqual(len(scans["sparse"][8]), POINTS // 3)

    def test_frozen_frontend_and_pose_backbone(self):
        scans, reference, _ = make_fixture()
        trajectory = estimate(scans["clean"][:4])
        score = evaluate(trajectory, reference[:4])

        self.assertEqual(len(trajectory), 4)
        self.assertLess(
            score["fixture_translation_rmse_m"],
            1e-6,
        )
        self.assertLess(
            score["fixture_rotation_rmse_deg"],
            1e-6,
        )

        names = tuple(
            trajectory[1]["registration_features"]
        )
        self.assertEqual(names, (
            "source_point_count",
            "target_point_count",
            "fixed_point_iterations",
            "final_correspondence_count",
            "final_nearest_neighbor_rmse_m",
        ))

    def test_estimator_requires_multiple_scans(self):
        scans, _, _ = make_fixture()
        with self.assertRaises(ValueError):
            estimate(scans["clean"][:1])

    def test_reference_length_is_checked(self):
        scans, reference, _ = make_fixture()
        trajectory = estimate(scans["clean"][:3])

        with self.assertRaises(ValueError):
            evaluate(trajectory, reference[:2])

    def test_full_fixture_conditions(self):
        _, manifest = execute()

        self.assertEqual(
            manifest["estimated_pose_count_per_condition"],
            20,
        )
        self.assertEqual(
            manifest["conditions"],
            list(CONDITIONS),
        )

        metrics = manifest["metrics_by_condition"]
        clean = metrics["clean"]

        self.assertLess(
            clean["fixture_translation_rmse_m"],
            1e-6,
        )

        for condition in ("sparse", "noise", "offset"):
            self.assertGreater(
                metrics[condition]["fixture_translation_rmse_m"],
                clean["fixture_translation_rmse_m"] + 1e-5,
            )

        self.assertFalse(
            manifest["reference_passed_to_estimator"]
        )

    def test_nonfinite_json_rejected(self):
        with self.assertRaises(ValueError):
            canonical({"x": float("nan")})

    def test_health_conditioning_still_blocked(self):
        with self.assertRaises(FactorConditioningContractError):
            assert_factor_scale_execution_authorized()

    def test_cross_modal_consistency_still_blocked(self):
        with self.assertRaises(AuxiliaryConsistencyContractError):
            assert_consistency_execution_authorized()


if __name__ == "__main__":
    unittest.main()
