import copy
import unittest

import numpy as np

import r84_gap_frontend as gap
import r90_prior_guard as guard
import r96_joint as m

class Tests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.report = m.execute()

    def sample(self):
        return m.make_unaries(0, 0, "both")

    def reject_mutation(self, fn):
        data = list(copy.deepcopy(self.sample()))
        fn(data)

        with self.assertRaises(m.IntegrationError):
            m.validate_unaries(
                tuple(data), 0, 0, "both"
            )

    def test_schema(self):
        self.assertEqual(
            self.report["schema"], m.SCHEMA
        )

    def test_status(self):
        self.assertEqual(
            self.report["status"],
            "PASS_SYNTHETIC_SOFTWARE_ONLY",
        )

    def test_four_scenarios(self):
        self.assertEqual(
            len(self.report["cases"]), 4
        )

    def test_prefix_count(self):
        self.assertEqual(
            self.report["total_prefix_evaluations"],
            28,
        )

    def test_marginalizations(self):
        self.assertEqual(
            self.report["total_eliminated_old_states"],
            20,
        )

    def test_gap_reset(self):
        self.assertEqual(
            self.report["cases"]["single_gap"][
                "segments"
            ], 2
        )

    def test_no_cross_gap_prior(self):
        for case in self.report["cases"].values():
            self.assertEqual(
                case["cross_gap_prior_carries"], 0
            )

    def test_fresh_anchors(self):
        for case in self.report["cases"].values():
            for segment in case["rows"]:
                self.assertTrue(
                    segment["new_manufactured_anchor"]
                )

    def test_camera_lidar_separate(self):
        result = self.report["cases"]["continuous"]
        modes = result["rows"][0]["windows"][0][
            "modalities"
        ]

        self.assertEqual(
            modes, ["camera", "lidar"]
        )

    def test_distinct_measurement_ids(self):
        factors = self.sample()

        self.assertNotEqual(
            factors[0]["measurement_id"],
            factors[1]["measurement_id"],
        )

    def test_distinct_covariances(self):
        factors = self.sample()

        self.assertFalse(
            np.array_equal(
                factors[0]["covariance"],
                factors[1]["covariance"],
            )
        )

    def test_batch_numerical_agreement(self):
        for case in self.report["cases"].values():
            for segment in case["rows"]:
                for window in segment["windows"]:
                    self.assertLess(
                        window["state_l2_error"], 1e-4
                    )
                    self.assertLess(
                        window["cost_abs_error"], 1e-5
                    )

    def test_covariance_agreement(self):
        for case in self.report["cases"].values():
            for segment in case["rows"]:
                for window in segment["windows"]:
                    self.assertLess(
                        window[
                            "covariance_relative_error"
                        ], 2e-3
                    )

    def test_information_order(self):
        self.assertTrue(
            self.report["information_order_check"]
        )

    def test_no_real_sensor_claim(self):
        self.assertFalse(
            self.report[
                "real_sensor_factors_executed"
            ]
        )

    def test_no_s6_nonlinear_claim(self):
        self.assertFalse(
            self.report[
                "s6_nonlinear_pose_factors_executed"
            ]
        )

    def test_invalid_scenario_denied(self):
        with self.assertRaises(m.IntegrationError):
            m.run_case("room_02")

    def test_invalid_mode_denied(self):
        with self.assertRaises(m.IntegrationError):
            m.run_case("continuous", "physical")

    def test_recorded_imu_denied(self):
        packets = copy.deepcopy(
            gap.fixture("continuous")
        )

        packets[0]["source_id"] = "/handsfree/imu"

        with self.assertRaises(
            gap.InertialAdmissionError
        ):
            m.run_case(
                "continuous", packets=packets
            )

    def test_confirmation_denied(self):
        packets = copy.deepcopy(
            gap.fixture("continuous")
        )

        packets[0][
            "confirmation_test_accessed"
        ] = True

        with self.assertRaises(
            gap.InertialAdmissionError
        ):
            m.run_case(
                "continuous", packets=packets
            )

    def test_clock_claim_denied(self):
        packets = copy.deepcopy(
            gap.fixture("continuous")
        )

        packets[0][
            "physical_clock_verified"
        ] = True

        with self.assertRaises(
            gap.InertialAdmissionError
        ):
            m.run_case(
                "continuous", packets=packets
            )

    def test_wrong_origin_denied(self):
        self.reject_mutation(
            lambda x: x[0].update(
                origin="ROS_BAG"
            )
        )

    def test_wrong_source_denied(self):
        self.reject_mutation(
            lambda x: x[0].update(
                source_id="/camera/imu"
            )
        )

    def test_wrong_frame_denied(self):
        self.reject_mutation(
            lambda x: x[0].update(
                frame_id="physical_base"
            )
        )

    def test_wrong_window_denied(self):
        self.reject_mutation(
            lambda x: x[0].update(step=99)
        )

    def test_duplicate_factor_denied(self):
        self.reject_mutation(
            lambda x: x.__setitem__(
                1, copy.deepcopy(x[0])
            )
        )

    def test_extra_field_denied(self):
        self.reject_mutation(
            lambda x: x[0].update(
                real_gt_verified=True
            )
        )

    def test_physical_factor_denied(self):
        self.reject_mutation(
            lambda x: x[0].update(
                physical_factor_authorized=True
            )
        )

    def test_nonfinite_measurement_denied(self):
        self.reject_mutation(
            lambda x: x[0]["observation"].__setitem__(
                0, float("nan")
            )
        )

    def test_covariance_mutation_denied(self):
        self.reject_mutation(
            lambda x: x[0]["covariance"].__setitem__(
                (0, 0), 0.0
            )
        )

    def test_stale_prior_denied(self):
        record = guard.make_record(
            np.eye(15), np.zeros(15), 0., 0
        )

        with self.assertRaises(
            guard.PriorAdmissionError
        ):
            guard.admit(
                record, 0, "STALE", np.zeros(15)
            )

    def test_cross_gap_reuse_denied(self):
        record = guard.make_record(
            np.eye(15), np.zeros(15), 0., 0
        )

        with self.assertRaises(
            guard.PriorAdmissionError
        ):
            guard.admit(
                record, 1,
                guard.token(0),
                np.zeros(15),
            )

    def test_repeat_determinism(self):
        self.assertEqual(
            m.canonical(self.report),
            m.canonical(m.execute()),
        )

if __name__ == "__main__":
    unittest.main(verbosity=2)
