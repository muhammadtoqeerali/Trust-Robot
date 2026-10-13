import unittest

from trust_robot.clean_backbone import PoseSE3
from trust_robot.m2dgr_sensor_admission import (
    CAMERA, BODY_IMU, LIDAR, load_frozen_snapshot
)
from trust_robot.multimodal_factor_interface import (
    ANALYTIC_FRAME,
    CAMERA_SOURCE,
    MultimodalFactorError,
    SyntheticPoseFactor,
    assemble_synthetic_pose_slot,
    describe_recorded_claim,
    require_recorded_factor_execution,
)

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def camera(edge=(0, 1), mid="camera-01"):
    return SyntheticPoseFactor(
        modality="camera",
        edge=edge,
        measurement_id=mid,
        source_id=CAMERA_SOURCE,
        frame_id=ANALYTIC_FRAME,
        measurement=PoseSE3.identity(),
    )


class MultimodalFactorInterfaceTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.snapshot = load_frozen_snapshot(REPO)

    def test_synthetic_packet_identity(self):
        self.assertEqual(camera().modality, "camera")
        self.assertEqual(camera().origin, "ANALYTIC_FIXTURE")

    def test_real_origin_rejected(self):
        with self.assertRaises(MultimodalFactorError):
            SyntheticPoseFactor(
                modality="camera",
                edge=(0, 1),
                measurement_id="bad",
                source_id=CAMERA_SOURCE,
                frame_id=ANALYTIC_FRAME,
                measurement=PoseSE3.identity(),
                origin="M2DGR",
            )

    def test_invalid_edge_rejected(self):
        for edge in ((1, 1), (-1, 2), (True, 2)):
            with self.subTest(edge=edge):
                with self.assertRaises(MultimodalFactorError):
                    camera(edge=edge)

    def test_double_camera_edge_rejected(self):
        with self.assertRaises(MultimodalFactorError):
            assemble_synthetic_pose_slot(
                {},
                [camera(mid="one"), camera(mid="two")],
                (0, 2, 4, 6, 8),
            )

    def test_duplicate_measurement_identity_rejected(self):
        with self.assertRaises(MultimodalFactorError):
            assemble_synthetic_pose_slot(
                {},
                [
                    camera((0, 1), "same"),
                    camera((2, 3), "same"),
                ],
                (0, 2, 4, 6, 8),
            )

    def test_disjoint_pose_ledger(self):
        lidar = {
            (0, 1): PoseSE3.identity(),
            (1, 2): PoseSE3.identity(),
        }

        merged, ledger = assemble_synthetic_pose_slot(
            lidar,
            [camera()],
            (0, 2, 4, 6, 8),
        )

        self.assertEqual(len(merged), 2)
        self.assertEqual(
            ledger["synthetic_camera_factor_count"], 1
        )
        self.assertEqual(
            ledger["synthetic_lidar_factor_count"], 1
        )
        self.assertFalse(
            ledger["same_edge_measurements_double_counted"]
        )

    def test_recorded_source_metadata_only(self):
        for stream in (CAMERA, BODY_IMU, LIDAR):
            claim = describe_recorded_claim(
                self.snapshot, "gate_01", stream, 100
            )
            self.assertFalse(
                claim["factor_execution_authorized"]
            )
            self.assertFalse(
                claim["header_timestamp_is_sync_proof"]
            )
            self.assertFalse(claim["relative_pose_available"])

    def test_held_out_source_rejected(self):
        with self.assertRaises(MultimodalFactorError):
            describe_recorded_claim(
                self.snapshot, "room_01", CAMERA, 100
            )

    def test_absent_camera_rejected(self):
        with self.assertRaises(MultimodalFactorError):
            describe_recorded_claim(
                self.snapshot, "street_09", CAMERA, 100
            )

    def test_invalid_header_rejected(self):
        for value in (True, -1, 1.5, None):
            with self.subTest(value=value):
                with self.assertRaises(MultimodalFactorError):
                    describe_recorded_claim(
                        self.snapshot, "gate_01", CAMERA, value
                    )

    def test_recorded_factor_execution_blocked(self):
        with self.assertRaises(MultimodalFactorError):
            require_recorded_factor_execution(
                self.snapshot, "gate_01"
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
