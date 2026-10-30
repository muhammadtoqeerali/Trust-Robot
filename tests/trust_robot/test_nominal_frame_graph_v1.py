"""Synthetic SE(3) geometry tests without physical calibration."""

import copy
import math
import unittest

from trust_robot.nominal_frame_graph_v1 import (
    FrameGraphError,
    relative_transform,
    validate_graph,
    nominal_inventory,
    qualify_physical_transform,
)


def joint(name, parent, child, xyz=(0, 0, 0),
          rpy=(0, 0, 0), kind="fixed"):
    return {
        "name": name,
        "type": kind,
        "parent": parent,
        "child": child,
        "xyz": list(xyz),
        "rpy": list(rpy),
    }


def graph():
    return {
        "links": ["root", "camera", "lidar"],
        "joints": [
            joint("camera_joint", "root", "camera",
                  (1, 0, 0)),
            joint("lidar_joint", "camera", "lidar",
                  (0, 2, 0)),
        ],
    }


class FrameGraphTests(unittest.TestCase):

    def test_01_graph_root(self):
        root, _ = validate_graph(graph())
        self.assertEqual(root, "root")

    def test_02_identity(self):
        m = relative_transform(graph(), "root", "root")
        self.assertEqual(m[0][0], 1)
        self.assertEqual(m[0][3], 0)

    def test_03_chain_translation(self):
        m = relative_transform(graph(), "lidar", "root")
        self.assertAlmostEqual(m[0][3], 1)
        self.assertAlmostEqual(m[1][3], 2)

    def test_04_inverse_translation(self):
        m = relative_transform(graph(), "root", "lidar")
        self.assertAlmostEqual(m[0][3], -1)
        self.assertAlmostEqual(m[1][3], -2)

    def test_05_relative_camera_lidar(self):
        m = relative_transform(graph(), "lidar", "camera")
        self.assertAlmostEqual(m[1][3], 2)

    def test_06_yaw_rotation(self):
        g = graph()
        g["joints"][0]["rpy"] = [0, 0, math.pi / 2]
        m = relative_transform(g, "camera", "root")
        self.assertAlmostEqual(m[0][0], 0, places=10)
        self.assertAlmostEqual(m[1][0], 1, places=10)

    def test_07_reject_dynamic_joint(self):
        g = graph()
        g["joints"][0]["type"] = "revolute"
        with self.assertRaises(FrameGraphError):
            relative_transform(g, "camera", "root")

    def test_08_reject_unknown_frame(self):
        with self.assertRaises(FrameGraphError):
            relative_transform(graph(), "bmi088_frame", "root")

    def test_09_reject_cycle(self):
        g = graph()
        g["joints"][0]["parent"] = "lidar"
        with self.assertRaises(FrameGraphError):
            validate_graph(g)

    def test_10_reject_duplicate_link(self):
        g = graph()
        g["links"][2] = "camera"
        with self.assertRaises(FrameGraphError):
            validate_graph(g)

    def test_11_reject_multiple_parents(self):
        g = graph()
        g["joints"][1]["child"] = "camera"
        with self.assertRaises(FrameGraphError):
            validate_graph(g)

    def test_12_reject_nonfinite(self):
        g = graph()
        g["joints"][0]["xyz"] = [float("nan"), 0, 0]
        with self.assertRaises(FrameGraphError):
            validate_graph(g)

    def test_13_reject_boolean_position(self):
        g = graph()
        g["joints"][0]["xyz"] = [True, 0, 0]
        with self.assertRaises(FrameGraphError):
            validate_graph(g)

    def test_14_reject_extra_joint_field(self):
        g = graph()
        g["joints"][0]["assumed_calibration"] = True
        with self.assertRaises(FrameGraphError):
            validate_graph(g)

    def test_15_deterministic_inventory(self):
        a = nominal_inventory(
            graph(), ["camera", "lidar"]
        )
        b = nominal_inventory(
            copy.deepcopy(graph()), ["camera", "lidar"]
        )
        self.assertEqual(a, b)
        self.assertEqual(a["real_factor_admission"], "DENIED")

    def test_16_dynamic_inventory_unavailable(self):
        g = graph()
        g["joints"][0]["type"] = "revolute"
        result = nominal_inventory(g, ["camera"])
        self.assertEqual(
            result["selected_frames"]["camera"]["status"],
            "UNAVAILABLE_DYNAMIC_PATH",
        )

    def test_17_reject_physical_qualification(self):
        with self.assertRaises(FrameGraphError):
            qualify_physical_transform(graph())

    def test_18_no_metric_accuracy_claim(self):
        result = nominal_inventory(
            graph(), ["camera"]
        )
        self.assertEqual(
            result["metric_extrinsic_accuracy"],
            "UNVERIFIED",
        )
        self.assertEqual(result["m2dgr_gates"], "11_CLOSED")


if __name__ == "__main__":
    unittest.main()
