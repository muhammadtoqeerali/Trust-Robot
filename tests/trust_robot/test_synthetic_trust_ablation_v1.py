import copy
import unittest

from trust_robot.synthetic_trust_ablation_v1 import (
    SyntheticAblationError,
    run_toy_ablation,
    apply_real_ablation_policy,
)

from trust_robot.physical_ros_replay_scheduler_v1 import (
    simulate_replay,
)

from trust_robot.synthetic_15d_innovation_v1 import (
    SyntheticInnovationError,
)


def eye(n):
    return [
        [1.0 if i == j else 0.0 for j in range(n)]
        for i in range(n)
    ]


def rows():
    result = []

    for i in range(10):
        stream = "imu" if i < 8 else "lidar"
        seq = i if i < 8 else i - 8

        result.append({
            "stream": stream,
            "sequence": seq,
            "recorder_stamp_ns": 1000 + i,
            "serialized_bytes": 128,
            "source_kind": "PHYSICAL_UNQUALIFIED",
            "header_stamp_ns": None,
            "frame_id": None,
        })

    return result


def descriptors():
    return [
        {
            "source_kind": "SYNTHETIC_ONLY",
            "stream": "imu",
            "factor_kind": "toy_attitude_xyz",
            "sequence": i,
            "clock_domain": "synthetic_clock",
            "event_stamp_ns": 10**18 + i,
            "measurement_xyz": [value, 0, 0],
            "noise_covariance_3x3": eye(3),
        }
        for i, value in enumerate((1, 3))
    ]


def scenario(**kwargs):
    return simulate_replay(
        rows(),
        queue_capacity=8,
        ingress_per_tick=8,
        delivery_per_tick=8,
        **kwargs,
    )


def run(s=None, d=None):
    return run_toy_ablation(
        [0] * 15,
        eye(15),
        descriptors() if d is None else d,
        scenario() if s is None else s,
    )


class AblationTests(unittest.TestCase):

    def test_01_four_variants(self):
        self.assertEqual(len(run()["variants"]), 4)

    def test_02_unscreened_toy_count(self):
        self.assertEqual(
            run()["variants"]["unscreened_toy"][
                "accepted_synthetic_updates"
            ], 2
        )

    def test_03_nis_only(self):
        self.assertEqual(
            run()["variants"]["toy_nis_only"][
                "accepted_synthetic_updates"
            ], 1
        )

    def test_04_delivery_only(self):
        self.assertEqual(
            run()["variants"]["software_delivery_only"][
                "accepted_synthetic_updates"
            ], 2
        )

    def test_05_combined(self):
        self.assertEqual(
            run()["variants"]["combined_toy_screening"][
                "accepted_synthetic_updates"
            ], 1
        )

    def test_06_imu_suppression(self):
        r = run(scenario(suppressed_streams=("imu",)))
        self.assertEqual(
            r["variants"]["combined_toy_screening"][
                "accepted_synthetic_updates"
            ], 0
        )

    def test_07_lidar_suppression(self):
        r = run(scenario(suppressed_streams=("lidar",)))
        self.assertEqual(
            r["variants"]["combined_toy_screening"][
                "accepted_synthetic_updates"
            ], 1
        )

    def test_08_queue_overflow(self):
        s = simulate_replay(
            rows(),
            queue_capacity=1,
            ingress_per_tick=8,
            delivery_per_tick=1,
        )
        r = run(s)
        self.assertEqual(
            r["variants"]["combined_toy_screening"][
                "accepted_synthetic_updates"
            ], 0
        )

    def test_09_reproducible(self):
        self.assertEqual(
            run(),
            run_toy_ablation(
                copy.deepcopy([0] * 15),
                copy.deepcopy(eye(15)),
                copy.deepcopy(descriptors()),
                copy.deepcopy(scenario()),
            ),
        )

    def test_10_reject_reordered_descriptors(self):
        d = descriptors()
        d.reverse()
        with self.assertRaises(SyntheticAblationError):
            run(d=d)

    def test_11_reject_duplicate_sequences(self):
        d = descriptors()
        d[1]["sequence"] = 0
        with self.assertRaises(SyntheticAblationError):
            run(d=d)

    def test_12_reject_mixed_clocks(self):
        d = descriptors()
        d[1]["clock_domain"] = "another_clock"
        with self.assertRaises(SyntheticAblationError):
            run(d=d)

    def test_13_reject_physical_measurement(self):
        d = descriptors()
        d[0]["source_kind"] = "PHYSICAL_UNQUALIFIED"
        with self.assertRaises(SyntheticAblationError):
            run(d=d)

    def test_14_reject_boolean_threshold(self):
        with self.assertRaises(SyntheticAblationError):
            run_toy_ablation(
                [0] * 15,
                eye(15),
                descriptors(),
                scenario(),
                nis_limit_num=True,
            )

    def test_15_real_ablation_denied(self):
        with self.assertRaises(SyntheticAblationError):
            apply_real_ablation_policy()

    def test_16_no_real_factors(self):
        r = run()
        self.assertEqual(r["real_factor_count"], 0)
        self.assertFalse(r["estimator_invoked"])
        self.assertFalse(r["real_robot_state_updated"])
        self.assertEqual(
            r["m2dgr_gates"], "11_CLOSED"
        )


if __name__ == "__main__":
    unittest.main()
