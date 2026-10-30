"""Toy trust-selection tests using synthetic metadata fixtures."""

import copy
import unittest

from trust_robot.synthetic_trust_gate_v1 import (
    SyntheticTrustGateError,
    screen_toy_candidate,
    apply_real_trust_policy,
)

from trust_robot.synthetic_15d_innovation_v1 import (
    SyntheticInnovationError,
)

from trust_robot.replay_observability_v1 import (
    ReplayObservabilityError,
)

from trust_robot.physical_ros_replay_scheduler_v1 import (
    simulate_replay,
)


def rows():
    result = []

    for i in range(8):
        result.append({
            "stream": "imu",
            "sequence": i,
            "recorder_stamp_ns": 1000 + i,
            "serialized_bytes": 128,
            "source_kind": "PHYSICAL_UNQUALIFIED",
            "header_stamp_ns": None,
            "frame_id": None,
        })

    for i in range(2):
        result.append({
            "stream": "lidar",
            "sequence": i,
            "recorder_stamp_ns": 2000 + i,
            "serialized_bytes": 128,
            "source_kind": "PHYSICAL_UNQUALIFIED",
            "header_stamp_ns": None,
            "frame_id": None,
        })

    return result


def descriptor(measurement=(1, 0, 0), stream="imu"):
    return {
        "source_kind": "SYNTHETIC_ONLY",
        "stream": stream,
        "factor_kind": "toy_attitude_xyz",
        "sequence": 0,
        "clock_domain": "synthetic_clock",
        "event_stamp_ns": 10**18,
        "measurement_xyz": list(measurement),
        "noise_covariance_3x3": [
            [1 if i == j else 0 for j in range(3)]
            for i in range(3)
        ],
    }


def scenario(**kwargs):
    return simulate_replay(
        rows(),
        queue_capacity=8,
        ingress_per_tick=8,
        delivery_per_tick=8,
        **kwargs,
    )


class ToyTrustTests(unittest.TestCase):

    def test_01_eligible_toy(self):
        r = screen_toy_candidate(
            [0] * 15, descriptor(), scenario()
        )
        self.assertEqual(
            r["toy_decision"],
            "ELIGIBLE_TOY_DIAGNOSTIC_ONLY",
        )

    def test_02_high_innovation_withheld(self):
        r = screen_toy_candidate(
            [0] * 15,
            descriptor((3, 0, 0)),
            scenario(),
        )
        self.assertEqual(
            r["toy_decision"],
            "WITHHELD_TOY_INNOVATION",
        )

    def test_03_inclusive_nis(self):
        r = screen_toy_candidate(
            [0] * 15, descriptor(), scenario(),
            nis_limit_num=1,
        )
        self.assertTrue(r["toy_selection_only"])

    def test_04_strict_nis(self):
        r = screen_toy_candidate(
            [0] * 15, descriptor(), scenario(),
            nis_limit_num=0,
        )
        self.assertFalse(r["toy_selection_only"])

    def test_05_imu_suppression(self):
        r = screen_toy_candidate(
            [0] * 15,
            descriptor(),
            scenario(suppressed_streams=("imu",)),
        )
        self.assertEqual(
            r["toy_decision"],
            "WITHHELD_SIMULATED_DELIVERY",
        )

    def test_06_other_stream_suppression(self):
        r = screen_toy_candidate(
            [0] * 15,
            descriptor(),
            scenario(suppressed_streams=("lidar",)),
        )
        self.assertTrue(r["toy_selection_only"])

    def test_07_imu_queue_overflow(self):
        s = simulate_replay(
            rows(),
            queue_capacity=1,
            ingress_per_tick=8,
            delivery_per_tick=1,
        )
        r = screen_toy_candidate(
            [0] * 15, descriptor(), s
        )
        self.assertEqual(
            r["toy_decision"],
            "WITHHELD_SIMULATED_DELIVERY",
        )

    def test_08_missing_lidar(self):
        s = scenario(
            suppressed_streams=("lidar",)
        )
        r = screen_toy_candidate(
            [0] * 15,
            descriptor(stream="lidar"),
            s,
        )
        self.assertFalse(r["toy_selection_only"])

    def test_09_determinism(self):
        s = scenario()

        self.assertEqual(
            screen_toy_candidate(
                [0] * 15, descriptor(), s
            ),
            screen_toy_candidate(
                [0] * 15,
                copy.deepcopy(descriptor()),
                copy.deepcopy(s),
            ),
        )

    def test_10_reject_boolean_limit(self):
        with self.assertRaises(SyntheticTrustGateError):
            screen_toy_candidate(
                [0] * 15,
                descriptor(),
                scenario(),
                nis_limit_num=True,
            )

    def test_11_reject_zero_denominator(self):
        with self.assertRaises(SyntheticTrustGateError):
            screen_toy_candidate(
                [0] * 15,
                descriptor(),
                scenario(),
                nis_limit_den=0,
            )

    def test_12_reject_forged_replay_factor(self):
        s = scenario()
        s["real_factor_count"] = 1

        with self.assertRaises(ReplayObservabilityError):
            screen_toy_candidate(
                [0] * 15, descriptor(), s
            )

    def test_13_reject_forged_replay_time(self):
        s = scenario()
        s["header_timestamp_inferred"] = True

        with self.assertRaises(ReplayObservabilityError):
            screen_toy_candidate(
                [0] * 15, descriptor(), s
            )

    def test_14_reject_physical_factor(self):
        d = descriptor()
        d["source_kind"] = "PHYSICAL_UNQUALIFIED"

        with self.assertRaises(SyntheticInnovationError):
            screen_toy_candidate(
                [0] * 15, d, scenario()
            )

    def test_15_real_policy_denied(self):
        with self.assertRaises(SyntheticTrustGateError):
            apply_real_trust_policy()

    def test_16_no_weight_probability_or_estimator(self):
        r = screen_toy_candidate(
            [0] * 15, descriptor(), scenario()
        )

        self.assertIsNone(r["factor_weight"])
        self.assertIsNone(
            r["physical_sensor_health_probability"]
        )
        self.assertFalse(r["estimator_invoked"])
        self.assertEqual(r["real_factor_count"], 0)
        self.assertEqual(
            r["real_factor_admission"], "DENIED"
        )


if __name__ == "__main__":
    unittest.main()
