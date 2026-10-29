import ast
import json
import unittest
from pathlib import Path

from trust_robot.clean_backbone import PoseSE3

from trust_robot.multimodal_factor_interface import (
    ANALYTIC_FRAME,
    CAMERA_SOURCE,
    MultimodalFactorError,
    SyntheticPoseFactor,
    assemble_synthetic_pose_slot,
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

from trust_robot.analytic_pose_slot_interventions_v1 import (
    SCHEMA,
    STATUS,
    SCENARIOS,
    NODE_FRAMES,
    SyntheticInterventionError,
    _assemble,
    _camera_packet,
    run_scenario,
    run_all_scenarios,
)

ROOT = Path(__file__).resolve().parents[2]


class SyntheticPoseSlotInterventionTests(unittest.TestCase):

    def test_01_frozen_scenarios(self):
        self.assertEqual(
            SCENARIOS,
            (
                "baseline",
                "lidar_edge_removed",
                "camera_substitutes_lidar",
                "camera_on_removed_lidar_edge",
            ),
        )

    def test_02_schema_and_status(self):
        r = run_scenario("baseline")
        self.assertEqual(r["schema"], SCHEMA)
        self.assertEqual(r["status"], STATUS)

    def test_03_lidar_baseline(self):
        r = run_scenario("baseline")
        self.assertEqual(r["synthetic_lidar_input_edges"], 3)
        self.assertEqual(r["selected_lidar_slots"], 3)
        self.assertEqual(r["selected_camera_slots"], 0)
        self.assertEqual(r["total_pose_slots"], 3)

    def test_04_lidar_edge_removed(self):
        r = run_scenario("lidar_edge_removed")
        self.assertEqual(r["synthetic_lidar_input_edges"], 2)
        self.assertEqual(r["selected_lidar_slots"], 2)
        self.assertEqual(r["total_pose_slots"], 2)
        self.assertEqual(r["missing_graph_edges"], [[1, 2]])

    def test_05_camera_substitutes_lidar(self):
        r = run_scenario("camera_substitutes_lidar")
        self.assertEqual(r["synthetic_lidar_input_edges"], 3)
        self.assertEqual(r["selected_camera_slots"], 1)
        self.assertEqual(r["selected_lidar_slots"], 2)
        self.assertEqual(
            r["camera_replaced_lidar_edges"],
            [[1, 2]],
        )
        self.assertFalse(r["camera_on_edge_without_lidar"])

    def test_06_camera_on_missing_lidar_edge(self):
        r = run_scenario("camera_on_removed_lidar_edge")
        self.assertEqual(r["synthetic_lidar_input_edges"], 2)
        self.assertEqual(r["synthetic_camera_input_packets"], 1)
        self.assertEqual(r["total_pose_slots"], 3)
        self.assertEqual(r["missing_graph_edges"], [])
        self.assertEqual(r["camera_replaced_lidar_edges"], [])
        self.assertTrue(r["camera_on_edge_without_lidar"])

    def test_07_camera_measurement_occupies_slot(self):
        lidar, packets, merged, _ = _assemble(
            "camera_substitutes_lidar"
        )
        self.assertNotEqual(
            lidar[(1, 2)],
            packets[0].measurement,
        )
        self.assertEqual(
            merged[(1, 2)],
            packets[0].measurement,
        )

    def test_08_ledger_provenance(self):
        for r in run_all_scenarios():
            for row in r["factor_ledger"]:
                self.assertEqual(
                    row["origin"],
                    "ANALYTIC_FIXTURE",
                )
                self.assertIn(
                    row["modality"],
                    ("camera", "lidar"),
                )

    def test_09_no_duplicate_selected_edges(self):
        for r in run_all_scenarios():
            edges = [
                tuple(row["edge"])
                for row in r["factor_ledger"]
            ]
            self.assertEqual(len(edges), len(set(edges)))
            self.assertFalse(r["same_edge_double_counted"])

    def test_10_reports_deterministic(self):
        first = json.dumps(
            run_all_scenarios(),
            sort_keys=True,
            allow_nan=False,
        )
        second = json.dumps(
            run_all_scenarios(),
            sort_keys=True,
            allow_nan=False,
        )
        self.assertEqual(first, second)

    def test_11_reject_unknown_scenarios(self):
        for invalid in (
            "M2DGR",
            "healthy",
            "camera",
            "",
            None,
            True,
            0,
        ):
            with self.subTest(invalid=invalid):
                with self.assertRaises(
                    SyntheticInterventionError
                ):
                    run_scenario(invalid)

    def test_12_recorded_origin_rejected(self):
        with self.assertRaises(MultimodalFactorError):
            SyntheticPoseFactor(
                modality="camera",
                edge=(1, 2),
                measurement_id="forged",
                source_id=CAMERA_SOURCE,
                frame_id=ANALYTIC_FRAME,
                measurement=PoseSE3.identity(),
                origin="RECORDED_SENSOR",
            )

    def test_13_duplicate_camera_rejected(self):
        packet = _camera_packet()

        with self.assertRaises(MultimodalFactorError):
            assemble_synthetic_pose_slot(
                {},
                [packet, packet],
                NODE_FRAMES,
            )

    def test_14_wrong_source_identity_rejected(self):
        with self.assertRaises(MultimodalFactorError):
            SyntheticPoseFactor(
                modality="camera",
                edge=(1, 2),
                measurement_id="wrong-source",
                source_id="recorded_camera",
                frame_id=ANALYTIC_FRAME,
                measurement=PoseSE3.identity(),
            )

    def test_15_no_estimator_or_health_outputs(self):
        for r in run_all_scenarios():
            for key in (
                "independent_camera_weighting_supported",
                "physical_camera_measurement_used",
                "pose_estimation_performed",
                "covariance_estimated",
                "health_probabilities_generated",
                "health_labels_assigned",
                "factor_weights_selected",
                "fault_severity_calibrated",
                "localization_recovery_demonstrated",
                "real_factor_execution_authorized",
                "confirmation_test_accessed",
            ):
                self.assertIs(r[key], False, key)

        source = ROOT / (
            "src/trust_robot/"
            "analytic_pose_slot_interventions_v1.py"
        )

        tree = ast.parse(source.read_text())

        modules = {
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        }

        self.assertEqual(
            modules,
            {
                "__future__",
                "trust_robot.clean_backbone",
                "trust_robot.multimodal_factor_interface",
            },
        )

    def test_16_existing_execution_gates_closed(self):
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
