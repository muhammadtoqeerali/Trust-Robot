import copy
import unittest
from pathlib import Path

from trust_robot.m2dgr_sensor_admission import (
    CAMERA,
    CAMERA_IMU,
    BODY_IMU,
    LIDAR,
    RECORD_FIELDS,
    SensorAdmissionError,
    audit_feature_records,
    inventory,
    load_frozen_snapshot,
    require_real_factor_execution,
)
from trust_robot.se3_multimodal_feature_extraction import (
    FEATURE_RECORD_SCHEMA,
)


REPO = Path(__file__).resolve().parents[2]


def record(
    trajectory="gate_01",
    stream=CAMERA,
    index=0,
    header=100,
):
    is_camera = stream == CAMERA
    return {
        "schema": FEATURE_RECORD_SCHEMA,
        "trajectory_id": trajectory,
        "split_role": "train",
        "source_stream_id": stream,
        "modality": "camera" if is_camera else "imu",
        "selected_reader_index": index,
        "stream_index": index,
        "bag_record_time_ns": 1000 + index,
        "header_stamp_ns": header,
        "feature_values": (
            [80.0, 20.0, 10.0]
            if is_camera else [0.2, 9.8]
        ),
    }


class M2DGRSensorAdmissionTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.snapshot = load_frozen_snapshot(REPO)

    def test_frozen_36_trajectory_inventory(self):
        result = inventory(self.snapshot)
        self.assertEqual(result["trajectory_count"], 36)
        self.assertEqual(
            result["frozen_split_counts"],
            {
                "train": 22,
                "validation_calibration": 7,
                "confirmation_test": 7,
            },
        )

    def test_original_modality_inventory(self):
        result = inventory(self.snapshot)
        self.assertEqual(
            result["modality_trajectory_counts"]["lidar"], 36
        )
        self.assertEqual(
            result["modality_trajectory_counts"]["camera"], 34
        )
        self.assertEqual(
            result["stream_trajectory_counts"][BODY_IMU], 36
        )
        self.assertEqual(
            result["stream_trajectory_counts"][CAMERA_IMU], 34
        )
        self.assertIn(
            "street_09", result["camera_missing_trajectories"]
        )

    def test_real_factor_execution_closed(self):
        for name in self.snapshot["by_id"]:
            with self.assertRaises(SensorAdmissionError):
                require_real_factor_execution(self.snapshot, name)

    def test_no_cross_modal_alignment_claim(self):
        result = inventory(self.snapshot)
        self.assertFalse(
            result["cross_modal_alignment_performed"]
        )
        self.assertFalse(
            result["real_sensor_factors_constructed"]
        )
        self.assertFalse(
            result["independent_reference_scored"]
        )

    def test_single_camera_feature_packet(self):
        result = audit_feature_records(
            self.snapshot, "gate_01", CAMERA, [record()]
        )
        self.assertEqual(result["record_count"], 1)
        self.assertEqual(result["header_present_count"], 1)
        self.assertFalse(
            result["relative_motion_factor_created"]
        )
        self.assertFalse(result["ground_truth_used"])

    def test_single_imu_feature_packet(self):
        result = audit_feature_records(
            self.snapshot,
            "gate_01",
            BODY_IMU,
            [record(stream=BODY_IMU)],
        )
        self.assertEqual(result["modality"], "imu")
        self.assertEqual(len(result["feature_names"]), 2)

    def test_strict_header_reversal_is_descriptive(self):
        a = record(index=0, header=120)
        b = record(index=1, header=100)
        result = audit_feature_records(
            self.snapshot, "gate_01", CAMERA, [a, b]
        )
        self.assertEqual(
            result["header_strict_reversal_count"], 1
        )
        self.assertFalse(
            result["cross_modal_temporal_association_performed"]
        )

    def test_missing_header_does_not_use_transport_time(self):
        a = record(header=None)
        result = audit_feature_records(
            self.snapshot, "gate_01", CAMERA, [a]
        )
        self.assertEqual(result["header_missing_count"], 1)
        self.assertIsNone(
            result["first_observed_header_ns"]
        )
        self.assertFalse(
            result["bag_record_time_used_as_measurement_time"]
        )

    def test_duplicate_stream_index_rejected(self):
        a = record(index=0)
        b = record(index=0)
        with self.assertRaises(SensorAdmissionError):
            audit_feature_records(
                self.snapshot, "gate_01", CAMERA, [a, b]
            )

    def test_nonfinite_feature_rejected(self):
        a = record()
        a["feature_values"][0] = float("nan")
        with self.assertRaises(SensorAdmissionError):
            audit_feature_records(
                self.snapshot, "gate_01", CAMERA, [a]
            )

    def test_reference_injection_rejected(self):
        a = record()
        a["ground_truth_pose"] = [0, 0, 0]
        with self.assertRaises(SensorAdmissionError):
            audit_feature_records(
                self.snapshot, "gate_01", CAMERA, [a]
            )

    def test_holdout_protected(self):
        # room_01 belongs to the frozen confirmation test split.
        a = record(trajectory="room_01")
        with self.assertRaises(SensorAdmissionError):
            audit_feature_records(
                self.snapshot, "room_01", CAMERA, [a]
            )

    def test_absent_camera_stream_rejected(self):
        with self.assertRaises(SensorAdmissionError):
            audit_feature_records(
                self.snapshot,
                "street_09",
                CAMERA,
                [record(trajectory="street_09")],
            )

    def test_lidar_cannot_masquerade_as_se3_feature(self):
        with self.assertRaises(SensorAdmissionError):
            audit_feature_records(
                self.snapshot,
                "gate_01",
                LIDAR,
                [record(stream=LIDAR)],
            )

    def test_mixed_trajectory_rejected(self):
        with self.assertRaises(SensorAdmissionError):
            audit_feature_records(
                self.snapshot,
                "gate_01",
                CAMERA,
                [record(trajectory="hall_01")],
            )

    def test_wrong_modality_rejected(self):
        a = record()
        a["modality"] = "lidar"
        with self.assertRaises(SensorAdmissionError):
            audit_feature_records(
                self.snapshot, "gate_01", CAMERA, [a]
            )

    def test_nonmonotone_reader_identity_rejected(self):
        a = record(index=0)
        b = record(index=1)
        b["selected_reader_index"] = 0
        with self.assertRaises(SensorAdmissionError):
            audit_feature_records(
                self.snapshot, "gate_01", CAMERA, [a, b]
            )

    def test_repeat_is_deterministic(self):
        rows = [record(index=0), record(index=1)]
        first = audit_feature_records(
            self.snapshot, "gate_01", CAMERA, rows
        )
        second = audit_feature_records(
            self.snapshot, "gate_01", CAMERA,
            copy.deepcopy(rows),
        )
        self.assertEqual(first, second)

    def test_record_field_contract_is_exact(self):
        self.assertEqual(set(record()), RECORD_FIELDS)


if __name__ == "__main__":
    unittest.main(verbosity=2)
