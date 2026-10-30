"""Synthetic A29-4 scheduler tests; no ROS, dataset or physical evidence."""

import copy
import unittest

from trust_robot.physical_ros_bag_envelope_v1 import (
    EnvelopeValidationError,
)
from trust_robot.physical_ros_replay_scheduler_v1 import (
    SCHEMA,
    simulate_replay,
    scenario_matrix,
    to_estimator_factors,
)


def sample(stream="imu", sequence=0, timestamp=100, **extra):
    item = {
        "stream": stream,
        "sequence": sequence,
        "recorder_stamp_ns": timestamp,
        "serialized_bytes": 128,
        "source_kind": "PHYSICAL_UNQUALIFIED",
        "header_stamp_ns": None,
        "frame_id": None,
    }
    item.update(extra)
    return item


def rows():
    return [
        sample("imu", 0, 100),
        sample("lidar", 0, 100),
        sample("imu", 1, 100),
        sample("lidar", 1, 200),
        sample("imu", 2, 200),
        sample("left_image", 0, 300),
    ]


class ReplaySchedulerTests(unittest.TestCase):

    def test_01_schema(self):
        self.assertIn("A29_4", SCHEMA)

    def test_02_preserve_equal_timestamp_source_order(self):
        result = simulate_replay(
            rows(),
            queue_capacity=6,
            ingress_per_tick=6,
            delivery_per_tick=6,
        )
        self.assertEqual(
            result["delivered_input_ordinals"],
            list(range(6)),
        )
        self.assertTrue(
            result["equal_recorder_stamp_source_order_preserved"]
        )

    def test_03_deterministic_trace(self):
        a = simulate_replay(rows())
        b = simulate_replay(copy.deepcopy(rows()))
        self.assertEqual(a, b)

    def test_04_software_ticks_not_sensor_time(self):
        result = simulate_replay(rows())
        self.assertIn("NOT_PHYSICAL", result["time_axis"])
        self.assertFalse(result["header_timestamp_inferred"])
        self.assertFalse(result["frame_id_inferred"])

    def test_05_capacity_never_exceeded(self):
        result = simulate_replay(
            rows(),
            queue_capacity=2,
            ingress_per_tick=6,
            delivery_per_tick=1,
        )
        self.assertEqual(result["peak_queued_envelopes"], 2)
        self.assertEqual(
            sum(result["queue_overflow_counts"].values()),
            4,
        )
        self.assertEqual(
            len(result["delivered_input_ordinals"]),
            2,
        )

    def test_06_dropouts_distinct_from_overflows(self):
        result = simulate_replay(
            rows(),
            queue_capacity=6,
            ingress_per_tick=6,
            delivery_per_tick=6,
            suppressed_streams=("lidar",),
        )
        self.assertEqual(
            result["synthetic_suppressed_counts"]["lidar"],
            2,
        )
        self.assertEqual(
            sum(result["queue_overflow_counts"].values()),
            0,
        )
        self.assertEqual(
            result["delivered_input_ordinals"],
            [0, 2, 4, 5],
        )

    def test_07_all_stream_suppression(self):
        result = simulate_replay(
            rows(),
            suppressed_streams=(
                "imu", "lidar", "left_image",
            ),
        )
        self.assertEqual(
            result["delivered_input_ordinals"], []
        )
        self.assertEqual(
            sum(result["synthetic_suppressed_counts"].values()),
            6,
        )

    def test_08_reject_unknown_suppression(self):
        with self.assertRaises(EnvelopeValidationError):
            simulate_replay(
                rows(),
                suppressed_streams=("cmd_vel",),
            )

    def test_09_reject_duplicate_suppression(self):
        with self.assertRaises(EnvelopeValidationError):
            simulate_replay(
                rows(),
                suppressed_streams=("imu", "imu"),
            )

    def test_10_reject_boolean_capacity(self):
        with self.assertRaises(EnvelopeValidationError):
            simulate_replay(rows(), queue_capacity=True)

    def test_11_reject_zero_capacity(self):
        with self.assertRaises(EnvelopeValidationError):
            simulate_replay(rows(), queue_capacity=0)

    def test_12_reject_oversized_capacity(self):
        with self.assertRaises(EnvelopeValidationError):
            simulate_replay(rows(), queue_capacity=513)

    def test_13_reject_zero_ingress(self):
        with self.assertRaises(EnvelopeValidationError):
            simulate_replay(rows(), ingress_per_tick=0)

    def test_14_reject_zero_delivery(self):
        with self.assertRaises(EnvelopeValidationError):
            simulate_replay(rows(), delivery_per_tick=0)

    def test_15_reject_fabricated_header(self):
        bad = rows()
        bad[0]["header_stamp_ns"] = bad[0]["recorder_stamp_ns"]

        with self.assertRaises(EnvelopeValidationError):
            simulate_replay(bad)

    def test_16_reject_assumed_frame(self):
        bad = rows()
        bad[0]["frame_id"] = "bmi088_frame"

        with self.assertRaises(EnvelopeValidationError):
            simulate_replay(bad)

    def test_17_reject_unordered_recorder_stamps(self):
        bad = rows()
        bad[3]["recorder_stamp_ns"] = 1

        with self.assertRaises(EnvelopeValidationError):
            simulate_replay(bad)

    def test_18_reject_invalid_sequence(self):
        bad = rows()
        bad[2]["sequence"] = 5

        with self.assertRaises(EnvelopeValidationError):
            simulate_replay(bad)

    def test_19_accounting_identity(self):
        result = simulate_replay(
            rows(),
            queue_capacity=2,
            ingress_per_tick=3,
            delivery_per_tick=1,
            suppressed_streams=("lidar",),
        )

        accounted = (
            sum(result["delivered_counts"].values())
            + sum(
                result["synthetic_suppressed_counts"].values()
            )
            + sum(result["queue_overflow_counts"].values())
        )

        self.assertEqual(result["input_count"], accounted)

    def test_20_five_scenarios(self):
        matrix = scenario_matrix(rows())
        self.assertEqual(matrix["scenario_count"], 5)
        self.assertFalse(
            matrix["physical_health_recovery_measured"]
        )
        self.assertEqual(
            matrix["real_factor_admission"], "DENIED"
        )

    def test_21_matrix_reproducible(self):
        self.assertEqual(
            scenario_matrix(rows()),
            scenario_matrix(rows()),
        )

    def test_22_factor_conversion_denied(self):
        with self.assertRaises(EnvelopeValidationError):
            to_estimator_factors(rows())

    def test_23_empty_input_rejected(self):
        with self.assertRaises(EnvelopeValidationError):
            simulate_replay([])

    def test_24_nonlist_input_rejected(self):
        with self.assertRaises(EnvelopeValidationError):
            simulate_replay(tuple(rows()))

    def test_25_pressure_accounting(self):
        item = scenario_matrix(rows())["scenarios"][
            "synthetic_queue_pressure"
        ]

        self.assertEqual(
            sum(item["delivered_counts"].values())
            + sum(item["queue_overflow_counts"].values()),
            6,
        )

    def test_26_output_stays_denied(self):
        item = simulate_replay(rows())

        self.assertEqual(item["m2dgr_gates"], "11_CLOSED")
        self.assertEqual(item["real_factor_count"], 0)
        self.assertFalse(item["estimator_invoked"])


if __name__ == "__main__":
    unittest.main()
