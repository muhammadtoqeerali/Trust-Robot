import copy
import unittest

from trust_robot.synthetic_15d_trajectory_v1 import (
    ToyTrajectoryError,
    predict_toy_15d,
    run_toy_trajectory,
    apply_real_trajectory,
)

from trust_robot.synthetic_truth_consistency_v1 import (
    ToyConsistencyError,
)


def eye(n):
    return [
        [1.0 if i == j else 0.0 for j in range(n)]
        for i in range(n)
    ]


def make_truth(position):
    x = [0.0] * 15
    x[0] = position
    x[3] = 1.0

    return {
        "source_kind": "SYNTHETIC_TRUTH_ONLY",
        "state_15": x,
        "reference_protocol": "DECLARED_TOY_KINEMATICS_V1",
    }


def steps():
    measurements = [1, 2, 20, 20, 5, 6]

    return [
        {
            "index": i,
            "dt_ns": 10**9,
            "software_available": i not in (2, 3),
            "synthetic_truth": make_truth(i + 1),
            "candidate": {
                "source_kind": "SYNTHETIC_ONLY",
                "stream": "imu",
                "factor_kind": "toy_position_xyz",
                "sequence": i,
                "clock_domain": "synthetic_clock",
                "event_stamp_ns": 10**18 + i,
                "measurement_xyz": [value, 0, 0],
                "noise_covariance_3x3": eye(3),
            },
        }
        for i, value in enumerate(measurements)
    ]


def run(items=None):
    return run_toy_trajectory(
        [0.0] * 15,
        eye(15),
        steps() if items is None else items,
    )


class TrajectoryTests(unittest.TestCase):

    def test_01_velocity_prediction(self):
        x = [0.0] * 15
        x[3] = 1.0

        result = predict_toy_15d(
            x, eye(15), dt_ns=10**9
        )
        self.assertEqual(
            result["predicted_state_15"][0], 1
        )

    def test_02_process_noise_increases_covariance(self):
        a = predict_toy_15d(
            [0] * 15, eye(15),
            dt_ns=10**9,
            acceleration_noise=0,
        )
        b = predict_toy_15d(
            [0] * 15, eye(15),
            dt_ns=10**9,
            acceleration_noise=0.1,
        )

        self.assertGreater(
            b["predicted_covariance_15x15"][0][0],
            a["predicted_covariance_15x15"][0][0],
        )

    def test_03_four_policies(self):
        self.assertEqual(len(run()["variants"]), 4)

    def test_04_counterfactual_all(self):
        self.assertEqual(
            run()["variants"]["counterfactual_all_candidates"][
                "accepted_toy_updates"
            ], 6
        )

    def test_05_scheduled_dropouts(self):
        self.assertEqual(
            run()["variants"]["scheduled_delivery_only"][
                "accepted_toy_updates"
            ], 4
        )

    def test_06_two_consecutive_dropouts(self):
        trace = run()["variants"]["scheduled_delivery_only"][
            "toy_trajectory_trace"
        ]
        self.assertEqual(
            [trace[i]["decision"] for i in (2, 3)],
            [
                "WITHHELD_SYNTHETIC_DELIVERY",
                "WITHHELD_SYNTHETIC_DELIVERY",
            ],
        )

    def test_07_recovery_resumes_updates(self):
        trace = run()["variants"]["scheduled_delivery_only"][
            "toy_trajectory_trace"
        ]
        self.assertEqual(
            trace[4]["decision"],
            "APPLIED_SYNTHETIC_UPDATE",
        )

    def test_08_combined_not_more_than_delivery(self):
        result = run()["variants"]
        self.assertLessEqual(
            result["combined_toy_screening"][
                "accepted_toy_updates"
            ],
            result["scheduled_delivery_only"][
                "accepted_toy_updates"
            ],
        )

    def test_09_determinism(self):
        self.assertEqual(
            run(),
            run(copy.deepcopy(steps())),
        )

    def test_10_reject_boolean_dt(self):
        with self.assertRaises(ToyTrajectoryError):
            predict_toy_15d(
                [0] * 15, eye(15), dt_ns=True
            )

    def test_11_reject_zero_dt(self):
        with self.assertRaises(ToyTrajectoryError):
            predict_toy_15d(
                [0] * 15, eye(15), dt_ns=0
            )

    def test_12_reject_negative_noise(self):
        with self.assertRaises(ToyTrajectoryError):
            predict_toy_15d(
                [0] * 15, eye(15),
                dt_ns=10**9,
                acceleration_noise=-1,
            )

    def test_13_reject_nonordered_sequence(self):
        items = steps()
        items[2]["candidate"]["sequence"] = 0

        with self.assertRaises(ToyTrajectoryError):
            run(items)

    def test_14_reject_mixed_clock(self):
        items = steps()
        items[1]["candidate"]["clock_domain"] = "other"

        with self.assertRaises(ToyTrajectoryError):
            run(items)

    def test_15_reject_physical_candidate_during_dropout(self):
        items = steps()
        items[2]["candidate"]["source_kind"] = "PHYSICAL"

        with self.assertRaises(ToyTrajectoryError):
            run(items)

    def test_16_reject_physical_truth_during_dropout(self):
        items = steps()
        items[2]["synthetic_truth"]["source_kind"] = "PHYSICAL"

        with self.assertRaises(ToyConsistencyError):
            run(items)

    def test_17_reject_fake_availability(self):
        items = steps()
        items[0]["software_available"] = 1

        with self.assertRaises(ToyTrajectoryError):
            run(items)

    def test_18_reject_bad_threshold(self):
        with self.assertRaises(ToyTrajectoryError):
            run_toy_trajectory(
                [0] * 15, eye(15), steps(),
                nis_limit_num=True,
            )

    def test_19_no_physical_state_estimate(self):
        result = run()
        self.assertFalse(
            result["physical_ground_truth_verified"]
        )
        self.assertFalse(result["estimator_invoked"])
        self.assertEqual(result["real_factor_count"], 0)
        self.assertEqual(
            result["real_factor_admission"], "DENIED"
        )

    def test_20_physical_execution_denied(self):
        with self.assertRaises(ToyTrajectoryError):
            apply_real_trajectory()


if __name__ == "__main__":
    unittest.main()
