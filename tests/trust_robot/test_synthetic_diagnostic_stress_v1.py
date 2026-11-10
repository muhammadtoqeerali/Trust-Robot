"""Synthetic-only falsification checks for A40-1. No raw bag or device read."""
from __future__ import annotations
import copy
import json
import unittest
from trust_robot.synthetic_diagnostic_stress_v1 import CASES, _characterize, apply_case, manufactured_baseline, run_matrix


class SyntheticInterventionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = run_matrix()
        cls.rows = {r["case_id"]: r for r in cls.out["rows"]}

    def test_manifest_cardinality_and_unique_case_ids(self):
        self.assertEqual(len(CASES), 14)
        self.assertEqual(len(self.rows), len(CASES))
        self.assertEqual(self.out["scenario_count"], 14)
        self.assertEqual(self.out["expected_rejections"], 3)

    def test_manufactured_source_and_gates(self):
        self.assertEqual(self.out["source_role"], "SYNTHETIC_MANUFACTURED_FIXTURES_ONLY")
        self.assertEqual(self.out["physical_health_labels_accepted"], 0)
        self.assertEqual(self.out["real_estimator_factors"], "DENIED")
        self.assertEqual(self.out["robot_control"], "DENIED")
        self.assertEqual(self.out["m2dgr_train_validation_sealed"], "NO_DATASET_ACCESS")

    def test_repeatability_byte_exact(self):
        a = json.dumps(run_matrix(), sort_keys=True, separators=(",", ":"), allow_nan=False)
        b = json.dumps(run_matrix(), sort_keys=True, separators=(",", ":"), allow_nan=False)
        self.assertEqual(a, b)

    def test_no_mutation_of_baseline(self):
        initial = manufactured_baseline()
        baseline = copy.deepcopy(initial)
        for row in CASES:
            apply_case(baseline, row[0])
        self.assertEqual(initial, baseline)

    def test_zero_payload_observed(self):
        self.assertEqual(self.rows["camera_zero_benign"]["aggregate_deltas"]["left_zero_payload_delta"], 3)
        self.assertEqual(self.rows["camera_startup_zero"]["aggregate_deltas"]["left_zero_payload_delta"], 3)

    def test_causal_intent_not_inferred(self):
        a = self.rows["camera_zero_benign"]
        b = self.rows["camera_zero_adversarial"]
        self.assertEqual(a["aggregate_deltas"], b["aggregate_deltas"])
        self.assertNotEqual(a["scenario_intent_design_only"], b["scenario_intent_design_only"])
        self.assertEqual(self.out["attack_attribution_from_features"], "DENIED")

    def test_delivery_burst_observable_on_recorder_axis_only(self):
        row = self.rows["camera_delivery_burst"]["aggregate_deltas"]
        self.assertEqual(row["right_short_interarrival_delta"], 1)
        self.assertEqual(row["right_long_interarrival_delta"], 1)
        self.assertEqual(row["numeric_equal_headers_delta"], 0)

    def test_removal_descriptive_not_actual_dropped_frame(self):
        d = self.rows["camera_message_removal"]["aggregate_deltas"]
        self.assertEqual(d["right_frame_count_delta"], -1)
        self.assertEqual(d["numeric_equal_headers_delta"], -1)

    def test_header_offset_not_sync_estimate(self):
        row = self.rows["camera_header_perturbation"]
        self.assertEqual(row["aggregate_deltas"]["numeric_equal_headers_delta"], -4)
        self.assertEqual(self.out["physical_sync"], "NOT_QUALIFIED")

    def test_imu_bias_noise_and_stuck(self):
        self.assertGreater(self.rows["imu_bias"]["aggregate_deltas"]["imu_accel_norm_mean_delta"], 0.3)
        self.assertGreater(self.rows["imu_noise"]["aggregate_deltas"]["imu_gyro_norm_mean_delta"], 0.03)
        self.assertEqual(self.rows["imu_stuck"]["outcome"], "DESCRIPTIVE_CHANGE")

    def test_lidar_layout_and_slots(self):
        self.assertEqual(self.rows["lidar_slots_zeroed"]["aggregate_deltas"]["lidar_point_slots_delta"], -240)
        self.assertEqual(self.rows["lidar_layout_shift"]["aggregate_deltas"]["lidar_layout_count_delta"], 1)

    def test_malformed_interventions_rejected(self):
        for label in ("camera_duplicate_header", "imu_nonfinite", "lidar_invalid_field_count"):
            self.assertEqual(self.rows[label]["outcome"], "EXPECTED_INPUT_REJECTION")
            self.assertIsNone(self.rows[label]["aggregate_deltas"])

    def test_unknown_intervention_rejected(self):
        with self.assertRaises(ValueError):
            apply_case(manufactured_baseline(), "physical_stop_command")

    def test_control_counts_and_clean_inputs(self):
        x = _characterize(manufactured_baseline())
        self.assertEqual(x["safe"]["camera"]["numeric_equal_header_count"], 12)
        self.assertEqual(x["safe"]["imu_sample_count"], 16)
        self.assertEqual(x["safe"]["lidar_reported_point_slots"], 480)

    def test_privacy_allowlist_no_raw_times_or_payloads(self):
        exported = json.dumps(self.out, sort_keys=True)
        for forbidden in ("header_ns", "recorder_ns", "accel_xyz", "gyro_xyz", "point_step_bytes", "raw_payload", "nvidia@", "/mnt/nova_ssd", "172.20."):
            self.assertNotIn(forbidden, exported)

    def test_unobserved_features_are_explicit(self):
        self.assertIn("camera_blur", self.out["uncaptured_features"])
        self.assertIn("lidar_return_geometry", self.out["uncaptured_features"])
        self.assertNotIn("camera_blur", {row[2] for row in CASES})

if __name__ == "__main__":
    unittest.main()
