import copy
from hashlib import sha256
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]

MANIFEST = (
    ROOT
    / "manifests"
    / "trust_robot_phase6_probabilistic_calibration_software_freeze_v1.json"
)


class TestPhase6ProbabilisticCalibrationSoftwareFreeze(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(
            MANIFEST.read_text(
                encoding="utf-8"
            )
        )

    def test_01_schema(self):
        self.assertEqual(
            self.payload["schema"],
            "TRUST_ROBOT_PHASE6_PROBABILISTIC_CALIBRATION_SOFTWARE_FREEZE_V1",
        )

    def test_02_phase(self):
        self.assertEqual(
            self.payload[
                "checkpoint_semantics"
            ]["phase"],
            6,
        )

    def test_03_software_architecture_implemented(self):
        self.assertTrue(
            self.payload[
                "checkpoint_semantics"
            ][
                "software_architecture_implemented"
            ]
        )

    def test_04_empirical_calibration_incomplete(self):
        self.assertFalse(
            self.payload[
                "checkpoint_semantics"
            ][
                "empirical_calibration_complete"
            ]
        )

    def test_05_no_empirical_completion_claim(self):
        self.assertFalse(
            self.payload[
                "checkpoint_semantics"
            ][
                "empirical_completion_claimed"
            ]
        )

    def test_06_temperature_scaling_mechanism(self):
        self.assertEqual(
            self.payload[
                "calibration_contract"
            ][
                "proposal_mechanism"
            ],
            "temperature_scaling",
        )

    def test_07_temperature_unselected(self):
        self.assertFalse(
            self.payload[
                "calibration_contract"
            ][
                "temperature_parameter_selected"
            ]
        )

    def test_08_temperature_none(self):
        self.assertIsNone(
            self.payload[
                "calibration_contract"
            ][
                "temperature_parameter"
            ]
        )

    def test_09_no_parameter_fit(self):
        self.assertFalse(
            self.payload[
                "calibration_contract"
            ][
                "parameter_fit_performed"
            ]
        )

    def test_10_objective_unselected(self):
        self.assertEqual(
            self.payload[
                "calibration_contract"
            ][
                "optimization_objective"
            ],
            "unselected",
        )

    def test_11_metrics_unselected(self):
        self.assertEqual(
            self.payload[
                "calibration_contract"
            ][
                "calibration_quality_metrics"
            ],
            [],
        )

    def test_12_temperature_scope_unselected(self):
        self.assertEqual(
            self.payload[
                "calibration_contract"
            ][
                "temperature_scope"
            ],
            "unselected",
        )

    def test_13_validation_partition(self):
        self.assertEqual(
            self.payload[
                "selection_partition"
            ][
                "partition"
            ],
            "validation_calibration",
        )

    def test_14_validation_count(self):
        self.assertEqual(
            self.payload[
                "selection_partition"
            ][
                "trajectory_count"
            ],
            7,
        )

    def test_15_validation_bags_unopened(self):
        self.assertFalse(
            self.payload[
                "selection_partition"
            ][
                "bags_opened"
            ]
        )

    def test_16_calibration_execution_blocked(self):
        self.assertFalse(
            self.payload[
                "selection_partition"
            ][
                "calibration_execution_authorized"
            ]
        )

    def test_17_no_trained_health_model(self):
        self.assertFalse(
            self.payload[
                "current_empirical_gate"
            ][
                "trained_health_model_available"
            ]
        )

    def test_18_no_uncalibrated_outputs(self):
        self.assertFalse(
            self.payload[
                "current_empirical_gate"
            ][
                "uncalibrated_health_outputs_available"
            ]
        )

    def test_19_no_admissible_labels(self):
        self.assertFalse(
            self.payload[
                "current_empirical_gate"
            ][
                "admissible_health_labels_available"
            ]
        )

    def test_20_health_threshold_unselected(self):
        self.assertFalse(
            self.payload[
                "operating_point_separation"
            ][
                "health_threshold_selected"
            ]
        )

    def test_21_confirmation_closed(self):
        self.assertTrue(
            self.payload[
                "confirmation_boundary"
            ][
                "closed"
            ]
        )

    def test_22_confirmation_selection_forbidden(self):
        self.assertFalse(
            self.payload[
                "confirmation_boundary"
            ][
                "selection_authorized"
            ]
        )

    def test_23_phase7_cannot_assume_empirical_completion(self):
        self.assertFalse(
            self.payload[
                "next_phase_policy"
            ][
                "phase7_may_assume_empirical_phase6_calibration_complete"
            ]
        )

    def test_24_content_digest(self):
        value = copy.deepcopy(
            self.payload
        )

        stored = value.pop(
            "content_sha256"
        )

        canonical = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode(
            "utf-8"
        )

        self.assertEqual(
            stored,
            sha256(
                canonical
            ).hexdigest(),
        )


if __name__ == "__main__":
    unittest.main()
