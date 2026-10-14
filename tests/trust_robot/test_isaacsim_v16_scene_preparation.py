import unittest
from pathlib import Path

from trust_robot.isaacsim_v16_scene_preparation import (
    ANCHOR,
    V16SceneError,
    build_v16_scene,
    validate_output_destination,
)

ROOT = Path(__file__).resolve().parents[2]
SOURCE = (
    ROOT / "experiments/isaacsim_v15/"
    "multimodal_scene_v5.usda"
)


class V16ScenePreparationTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.original = SOURCE.read_text()
        cls.generated = build_v16_scene(cls.original)

    def test_imu_created_by_original_runtime_script(self):
        runtime_script = (
            ROOT / "experiments/isaacsim_v15/"
            "multimodal_probe_candidate_v15.py"
        ).read_text()

        self.assertIn(
            'prim_path=base + "/PilotIMU"',
            runtime_script,
        )
        self.assertIn(
            "IMUSensor(",
            runtime_script,
        )
        self.assertIn(
            '"IMUMount"',
            self.original,
        )
        self.assertNotIn(
            '"PilotIMU"',
            self.original,
        )

    def test_original_header_preserved(self):
        self.assertTrue(
            self.generated.startswith("#usda 1.0")
        )

    def test_original_scene_unchanged_in_memory(self):
        self.assertNotIn(
            '"V16FeatureTargets"',
            self.original,
        )

    def test_generated_exactly_eighty_markers(self):
        self.assertEqual(
            self.generated.count('def Cube "Marker_'),
            80,
        )

    def test_original_calibration_targets_preserved(self):
        self.assertEqual(
            self.generated.count(ANCHOR),
            1,
        )

    def test_original_camera_and_lidar_preserved(self):
        for name in (
            '"FrontCamera"',
            '"PilotRTX"',
            '"IMUMount"',
            '"RobotProxy"',
        ):
            self.assertIn(name, self.generated)

    def test_multiple_depth_levels_present(self):
        self.assertIn(
            "(1.1200, ",
            self.generated,
        )
        self.assertIn(
            "(1.1500, ",
            self.generated,
        )
        self.assertIn(
            "(1.1800, ",
            self.generated,
        )

    def test_black_and_white_materials_exist(self):
        self.assertIn(
            'def Material "Light"',
            self.generated,
        )
        self.assertIn(
            'def Material "Dark"',
            self.generated,
        )

    def test_generation_is_deterministic(self):
        self.assertEqual(
            self.generated,
            build_v16_scene(self.original),
        )

    def test_second_generation_is_rejected(self):
        with self.assertRaises(V16SceneError):
            build_v16_scene(self.generated)

    def test_missing_anchor_is_rejected(self):
        with self.assertRaises(V16SceneError):
            build_v16_scene(
                self.original.replace(
                    ANCHOR,
                    '    def Xform "Other"',
                )
            )

    def test_outside_workspace_rejected(self):
        with self.assertRaises(V16SceneError):
            validate_output_destination(
                Path("/home/kios/TRUST_ROBOT_ALI"),
                Path("/tmp/isaacsim_v16_forbidden"),
            )

    def test_shared_installation_rejected(self):
        with self.assertRaises(V16SceneError):
            validate_output_destination(
                Path("/home/kios/TRUST_ROBOT_ALI"),
                Path("/home/kios/isaacsim/"
                     "isaacsim_v16_forbidden"),
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
