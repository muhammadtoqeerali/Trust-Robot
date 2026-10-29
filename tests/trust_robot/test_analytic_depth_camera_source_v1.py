import ast
import inspect
import json
import unittest
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation

from trust_robot.analytic_inertial_15d import (
    analytic_truth,
    as_rotation,
)
from trust_robot.analytic_preintegrated_fusion import (
    NODE_FRAMES,
)
from trust_robot.multimodal_factor_interface import (
    ANALYTIC_FRAME,
    CAMERA_SOURCE,
    SyntheticPoseFactor,
)
from trust_robot.multimodal_health_model import (
    HealthModelInterfaceError,
    assert_training_authorized,
    assert_inference_authorized,
)
from trust_robot.factor_conditioning import (
    FactorConditioningContractError,
    assert_factor_scale_execution_authorized,
)
from trust_robot.analytic_depth_camera_source_v1 import (
    SCHEMA,
    STATUS,
    EDGES,
    MODES,
    SCENE_POINTS,
    SyntheticDepthCameraError,
    generate_packet,
    summarize_all_pairs,
)

ROOT = Path(__file__).resolve().parents[2]


def nominal_pose(edge):
    i, j = edge

    pi = analytic_truth(NODE_FRAMES[i])
    pj = analytic_truth(NODE_FRAMES[j])

    Ri = as_rotation(pi).as_matrix()
    Rj = as_rotation(pj).as_matrix()

    return (
        (pj[:3] - pi[:3]) @ Ri,
        Rotation.from_matrix(Ri.T @ Rj),
    )


def translation_error(packet, edge):
    reference, _ = nominal_pose(edge)

    return float(np.linalg.norm(
        np.asarray(packet.measurement.translation_m)
        - reference
    ))


class SyntheticDepthCameraSourceTests(unittest.TestCase):

    def test_01_frozen_edges_and_modes(self):
        self.assertEqual(len(EDGES), 7)
        self.assertEqual(MODES, ("ideal", "noisy", "biased"))
        self.assertEqual(NODE_FRAMES, (0, 2, 4, 6, 8))

    def test_02_schema_and_evidence_role(self):
        _, r = generate_packet((0, 1), "ideal")
        self.assertEqual(r["schema"], SCHEMA)
        self.assertEqual(r["status"], STATUS)

    def test_03_twenty_one_pairs(self):
        rows = summarize_all_pairs()
        self.assertEqual(len(rows), 21)
        self.assertEqual(
            len(set(
                (tuple(r["edge"]), r["observation_mode"])
                for r in rows
            )),
            21,
        )

    def test_04_ideal_manufactured_geometry(self):
        for edge in EDGES:
            packet, _ = generate_packet(edge, "ideal")
            t, rotation = nominal_pose(edge)

            error_t = float(np.linalg.norm(
                np.asarray(packet.measurement.translation_m)
                - t
            ))

            q = packet.measurement.quaternion_wxyz

            fitted = Rotation.from_quat((
                q[1], q[2], q[3], q[0]
            ))

            error_r = float(
                (rotation.inv() * fitted).magnitude()
            )

            self.assertLess(error_t, 1e-8)
            self.assertLess(error_r, 1e-8)

    def test_05_ideal_correspondence_closure(self):
        for edge in EDGES:
            _, r = generate_packet(edge, "ideal")
            self.assertLess(
                r["mean_3d_correspondence_residual_m"],
                1e-8,
            )

    def test_06_noisy_correspondence_residual(self):
        for edge in EDGES:
            _, r = generate_packet(edge, "noisy")
            self.assertGreater(
                r["mean_3d_correspondence_residual_m"],
                1e-4,
            )

    def test_07_noisy_motion_distinct_from_nominal(self):
        for edge in EDGES:
            packet, _ = generate_packet(edge, "noisy")
            error = translation_error(packet, edge)
            self.assertGreater(error, 0.0)
            self.assertLess(error, 0.02)

    def test_08_pair_local_bias_distinguishable(self):
        for edge in EDGES:
            noisy, _ = generate_packet(edge, "noisy")
            biased, _ = generate_packet(edge, "biased")

            self.assertGreater(
                translation_error(biased, edge),
                translation_error(noisy, edge) + 0.008,
            )

    def test_09_measurement_id_uniqueness(self):
        ids = [
            generate_packet(edge, mode)[0].measurement_id
            for edge in EDGES
            for mode in MODES
        ]
        self.assertEqual(len(ids), 21)
        self.assertEqual(len(ids), len(set(ids)))

    def test_10_packet_determinism(self):
        a, _ = generate_packet((1, 2), "noisy")
        b, _ = generate_packet((1, 2), "noisy")
        self.assertEqual(a, b)

    def test_11_report_determinism(self):
        a = json.dumps(
            summarize_all_pairs(),
            sort_keys=True,
            allow_nan=False,
        )
        b = json.dumps(
            summarize_all_pairs(),
            sort_keys=True,
            allow_nan=False,
        )
        self.assertEqual(a, b)

    def test_12_typed_analytic_source_identity(self):
        for edge in EDGES:
            for mode in MODES:
                packet, r = generate_packet(edge, mode)
                self.assertIsInstance(
                    packet, SyntheticPoseFactor
                )
                self.assertEqual(packet.origin, "ANALYTIC_FIXTURE")
                self.assertEqual(packet.source_id, CAMERA_SOURCE)
                self.assertEqual(packet.frame_id, ANALYTIC_FRAME)
                self.assertEqual(r["measurement_id"],
                                 packet.measurement_id)

    def test_13_api_accepts_no_external_sensor_input(self):
        sig = inspect.signature(generate_packet)
        self.assertEqual(
            tuple(sig.parameters),
            ("edge", "mode"),
        )
        self.assertEqual(
            len(tuple(sig.parameters.values())),
            2,
        )

    def test_14_invalid_edge_rejected(self):
        for edge in (
            None, "0,1", [0, 1],
            (False, 1), (0, True),
            (-1, 2), (0, 3), (2, 2),
        ):
            with self.subTest(edge=edge):
                with self.assertRaises(
                    SyntheticDepthCameraError
                ):
                    generate_packet(edge, "ideal")

    def test_15_invalid_mode_rejected(self):
        for mode in (
            None, True, 1, "",
            "real", "healthy", "recorded",
        ):
            with self.subTest(mode=mode):
                with self.assertRaises(
                    SyntheticDepthCameraError
                ):
                    generate_packet((0, 1), mode)

    def test_16_scientific_denials(self):
        denied = (
            "monocular_metric_scale_established",
            "lidar_pose_factor_copied",
            "independent_physical_sensor_evidence",
            "physical_calibration_verified",
            "physical_clock_verified",
            "health_probability_generated",
            "health_label_assigned",
            "factor_weight_selected",
            "estimator_executed",
            "real_factor_execution_authorized",
            "confirmation_test_accessed",
        )

        for r in summarize_all_pairs():
            self.assertEqual(
                r["manufactured_correspondence_count"],
                SCENE_POINTS,
            )
            self.assertIs(
                r["metric_depth_manufactured"],
                True,
            )
            for key in denied:
                self.assertIs(r[key], False, key)

    def test_17_no_lidar_or_estimator_dependency(self):
        path = ROOT / (
            "src/trust_robot/"
            "analytic_depth_camera_source_v1.py"
        )

        tree = ast.parse(path.read_text())

        imports = {
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
            and node.module
        }

        for name in imports:
            self.assertNotIn("lidar", name.lower())
            self.assertNotIn("marginalized", name.lower())
            self.assertNotIn("estimator", name.lower())

        self.assertNotIn(
            "trust_robot.analytic_15d_pose_slot_integration_v1",
            imports,
        )

    def test_18_health_and_conditioning_still_denied(self):
        with self.assertRaises(
            HealthModelInterfaceError
        ):
            assert_training_authorized()

        with self.assertRaises(
            HealthModelInterfaceError
        ):
            assert_inference_authorized()

        with self.assertRaises(
            FactorConditioningContractError
        ):
            assert_factor_scale_execution_authorized()


if __name__ == "__main__":
    unittest.main(verbosity=2)
