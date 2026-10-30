"""Synthetic-only tests; no hardware, dataset or real bag reads."""

import copy
import unittest

from trust_robot.physical_ros_fusion_boundary_v1 import (
    SCHEMA,
    FusionBoundaryError,
    validate_descriptor,
    review_batch,
    admit_real_factors,
    score_physical_localization,
)


def sample(**updates):
    row = {
        "stream": "imu",
        "sequence": 1,
        "header_stamp_ns": 1000000000,
        "recorder_stamp_ns": 1000000050,
        "frame_id": "synthetic_imu",
        "payload_bytes": 128,
        "source_kind": "SYNTHETIC",
    }
    row.update(updates)
    return row


class FusionBoundaryTests(unittest.TestCase):

    def test_01_schema(self):
        self.assertEqual(
            SCHEMA,
            "TRUST_ROBOT_R135_A29_1_FUSION_BOUNDARY_V1",
        )

    def test_02_valid_synthetic_descriptor(self):
        result = validate_descriptor(sample())
        self.assertTrue(result["descriptor_valid"])
        self.assertFalse(result["estimator_factor_created"])
        self.assertEqual(result["real_factor_admission"], "DENIED")

    def test_03_physical_descriptor_never_admitted(self):
        result = validate_descriptor(
            sample(source_kind="PHYSICAL")
        )
        self.assertFalse(result["physical_timing_verified"])
        self.assertFalse(result["physical_extrinsics_verified"])
        self.assertEqual(result["m2dgr_gates"], "11_CLOSED")

    def test_04_reject_raw_sensor_payload(self):
        with self.assertRaises(FusionBoundaryError):
            validate_descriptor(sample(data=[1, 2, 3]))

    def test_05_reject_factor_weights(self):
        with self.assertRaises(FusionBoundaryError):
            validate_descriptor(sample(weight=0.95))

    def test_06_reject_unrecognized_stream(self):
        with self.assertRaises(FusionBoundaryError):
            validate_descriptor(sample(stream="cmd_vel"))

    def test_07_reject_negative_timestamp(self):
        with self.assertRaises(FusionBoundaryError):
            validate_descriptor(sample(header_stamp_ns=-1))

    def test_08_reject_boolean_timestamp(self):
        with self.assertRaises(FusionBoundaryError):
            validate_descriptor(sample(header_stamp_ns=True))

    def test_09_reject_float_timestamp(self):
        with self.assertRaises(FusionBoundaryError):
            validate_descriptor(sample(header_stamp_ns=1.25))

    def test_10_reject_missing_field(self):
        row = sample()
        del row["frame_id"]
        with self.assertRaises(FusionBoundaryError):
            validate_descriptor(row)

    def test_11_reject_unknown_source(self):
        with self.assertRaises(FusionBoundaryError):
            validate_descriptor(sample(source_kind="QUALIFIED_REAL"))

    def test_12_batch_counts_without_factors(self):
        rows = [
            sample(),
            sample(sequence=2, header_stamp_ns=1010000000),
            sample(
                stream="lidar",
                sequence=1,
                frame_id="synthetic_lidar",
            ),
        ]
        result = review_batch(rows)
        self.assertEqual(result["descriptor_count"], 3)
        self.assertEqual(result["stream_counts"]["imu"], 2)
        self.assertEqual(result["stream_counts"]["lidar"], 1)
        self.assertEqual(result["real_factor_count"], 0)
        self.assertFalse(result["estimator_invoked"])

    def test_13_reject_repeated_sequence(self):
        with self.assertRaises(FusionBoundaryError):
            review_batch([sample(), sample()])

    def test_14_reject_reversed_header(self):
        with self.assertRaises(FusionBoundaryError):
            review_batch([
                sample(header_stamp_ns=200),
                sample(sequence=2, header_stamp_ns=100),
            ])

    def test_15_denies_factor_creation(self):
        with self.assertRaises(FusionBoundaryError):
            admit_real_factors(sample(source_kind="PHYSICAL"))

    def test_16_denies_ground_truth_scoring(self):
        with self.assertRaises(FusionBoundaryError):
            score_physical_localization([])

    def test_17_empty_batch_still_denies(self):
        result = review_batch([])
        self.assertEqual(result["real_factor_admission"], "DENIED")
        self.assertEqual(result["m2dgr_gates"], "11_CLOSED")

    def test_18_mixed_source_never_invokes_estimator(self):
        result = review_batch([
            sample(),
            sample(
                source_kind="PHYSICAL",
                frame_id="bmi088_frame",
            ),
        ])
        self.assertFalse(result["synthetic_descriptor_test_only"])
        self.assertFalse(result["physical_pose_estimated"])
        self.assertEqual(result["real_factor_count"], 0)

    def test_19_malformed_frame_rejected(self):
        with self.assertRaises(FusionBoundaryError):
            validate_descriptor(sample(frame_id="bad\nframe"))

    def test_20_empty_frame_rejected(self):
        with self.assertRaises(FusionBoundaryError):
            validate_descriptor(sample(frame_id=""))


if __name__ == "__main__":
    unittest.main()
