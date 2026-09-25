from hashlib import sha256
from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]

FREEZE = (
    ROOT
    / "manifests/"
    "trust_robot_se4_health_model_training_blocked_frontier_freeze_v1.json"
)

MODULE = (
    ROOT
    / "src/trust_robot/"
    "se4_health_model_training_resolution.py"
)

CONFIG = (
    ROOT
    / "configs/trust_robot/"
    "se4_health_model_training_resolution_v1.json"
)

IMPLEMENTATION_TEST = (
    ROOT
    / "tests/trust_robot/"
    "test_se4_health_model_training_resolution.py"
)

LEGACY_INTERFACE = (
    ROOT
    / "configs/trust_robot/"
    "phase5_multimodal_health_model_interface_candidate_v1.json"
)

PROJECT_STATE = (
    ROOT
    / "docs/TRUST_ROBOT_PROJECT_STATE.md"
)

EXPECTED_FREEZE_SHA = "8ced2b97595a541fb152b5fd012d83c6c8d8b99a770a0cd1e1a6e7c55d6f248d"
EXPECTED_CONTENT_SHA = "a1cba866967ed7da07b9603b7f0fc1f7a1e59a2d588b933078e6a03b5985f852"


def file_sha(path):
    return sha256(
        path.read_bytes()
    ).hexdigest()


def canonical_sha(payload):
    body = dict(payload)
    body.pop(
        "content_sha256",
        None,
    )

    return sha256(
        json.dumps(
            body,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode(
            "utf-8"
        )
    ).hexdigest()


class SE4HealthModelTrainingBlockedFrontierFreezeTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(
            FREEZE.read_text(
                encoding="utf-8"
            )
        )

    def test_01_freeze_file_sha(self):
        self.assertEqual(
            file_sha(FREEZE),
            EXPECTED_FREEZE_SHA,
        )

    def test_02_content_digest(self):
        self.assertEqual(
            self.payload["content_sha256"],
            EXPECTED_CONTENT_SHA,
        )

        self.assertEqual(
            canonical_sha(self.payload),
            EXPECTED_CONTENT_SHA,
        )

    def test_03_schema(self):
        self.assertEqual(
            self.payload["schema"],
            "TRUST_ROBOT_SE4_HEALTH_MODEL_TRAINING_BLOCKED_FRONTIER_FREEZE_V1",
        )

    def test_04_stage_identity(self):
        self.assertEqual(
            self.payload["stage"]["stage_id"],
            "SE4",
        )

        self.assertEqual(
            self.payload["stage"]["stage_name"],
            "health_model_training",
        )

    def test_05_SE4_not_complete(self):
        self.assertFalse(
            self.payload["stage"]["SE4_complete"]
        )

        self.assertFalse(
            self.payload[
                "transition_policy"
            ]["SE4_complete"]
        )

    def test_06_implementation_hashes(self):
        implementation = self.payload[
            "implementation"
        ]

        self.assertEqual(
            file_sha(MODULE),
            implementation["module_sha256"],
        )

        self.assertEqual(
            file_sha(CONFIG),
            implementation["config_sha256"],
        )

        self.assertEqual(
            file_sha(IMPLEMENTATION_TEST),
            implementation["test_sha256"],
        )

    def test_07_camera_binding_exact(self):
        self.assertEqual(
            self.payload[
                "diagnostic_input_binding"
            ]["camera"]["feature_names"],
            [
                "gray_mean_intensity_8bit",
                "gray_std_intensity_8bit",
                "gray_mean_abs_neighbor_difference_8bit",
            ],
        )

    def test_08_imu_binding_exact(self):
        self.assertEqual(
            self.payload[
                "diagnostic_input_binding"
            ]["imu"]["feature_names"],
            [
                "angular_speed_norm_rad_s",
                "linear_acceleration_norm_m_s2",
            ],
        )

    def test_09_lidar_binding_exact(self):
        lidar = self.payload[
            "diagnostic_input_binding"
        ]["lidar"]

        self.assertEqual(
            lidar["feature_names"],
            [
                "source_point_count",
                "target_point_count",
                "fixed_point_iterations",
                "final_correspondence_count",
                "final_nearest_neighbor_rmse_m",
            ],
        )

        self.assertFalse(
            lidar["phase4_contract_reopened"]
        )

    def test_10_zero_baseline_sources(self):
        self.assertEqual(
            self.payload[
                "supervision_state"
            ][
                "accepted_baseline_nominality_source_count"
            ],
            0,
        )

    def test_11_zero_supervision_sources(self):
        self.assertEqual(
            self.payload[
                "supervision_state"
            ][
                "accepted_health_supervision_source_count"
            ],
            0,
        )

    def test_12_zero_real_health_labels(self):
        self.assertEqual(
            self.payload[
                "supervision_state"
            ][
                "real_health_label_count"
            ],
            0,
        )

    def test_13_training_unauthorized(self):
        self.assertFalse(
            self.payload[
                "model_state"
            ][
                "classifier_training_authorized"
            ]
        )

        self.assertFalse(
            self.payload[
                "transition_policy"
            ][
                "SE4_training_may_execute"
            ]
        )

    def test_14_architecture_unselected(self):
        self.assertEqual(
            self.payload[
                "model_state"
            ][
                "classifier_architecture"
            ],
            "unselected",
        )

        self.assertFalse(
            self.payload[
                "model_state"
            ][
                "classifier_architecture_selected"
            ]
        )

    def test_15_no_trained_model(self):
        self.assertFalse(
            self.payload[
                "model_state"
            ][
                "model_training_executed"
            ]
        )

        self.assertIsNone(
            self.payload[
                "model_state"
            ][
                "trained_model_artifact_sha256"
            ]
        )

    def test_16_no_health_output(self):
        self.assertFalse(
            self.payload[
                "model_state"
            ][
                "health_inference_authorized"
            ]
        )

        self.assertFalse(
            self.payload[
                "model_state"
            ][
                "health_probability_output_enabled"
            ]
        )

        self.assertFalse(
            self.payload[
                "model_state"
            ][
                "health_state_output_enabled"
            ]
        )

    def test_17_train_only_access(self):
        access = self.payload[
            "execution_status"
        ]

        self.assertTrue(
            access["train_access"]
        )

        self.assertFalse(
            access["validation_access"]
        )

        self.assertFalse(
            access["confirmation_access"]
        )

        self.assertFalse(
            access["reference_trajectory_access"]
        )

    def test_18_no_training_calibration_scoring(self):
        execution = self.payload[
            "execution_status"
        ]

        for key in (
            "health_label_assignment_executed",
            "supervised_feature_selection_executed",
            "model_training_executed",
            "probability_calibration_executed",
            "health_threshold_selection_executed",
            "reference_association_executed",
            "ate_rpe_computed",
            "final_scoring_executed",
        ):
            self.assertFalse(
                execution[key]
            )

    def test_19_SE5_blocked(self):
        transition = self.payload[
            "transition_policy"
        ]

        self.assertFalse(
            transition["SE5_may_proceed"]
        )

        self.assertTrue(
            transition[
                "SE5_blocked_pending_frozen_train_model_output"
            ]
        )

    def test_20_validation_confirmation_SE9_closed(self):
        transition = self.payload[
            "transition_policy"
        ]

        self.assertTrue(
            transition[
                "validation_remains_closed"
            ]
        )

        self.assertTrue(
            transition[
                "confirmation_remains_closed"
            ]
        )

        self.assertTrue(
            transition[
                "SE9_remains_closed"
            ]
        )

    def test_21_historical_interface_unchanged(self):
        binding = self.payload[
            "frozen_input_bindings"
        ][
            "historical_phase5_health_model_interface"
        ]

        self.assertFalse(
            binding["rewritten"]
        )

        self.assertEqual(
            file_sha(LEGACY_INTERFACE),
            binding["file_sha256"],
        )

    def test_22_blocked_freeze_not_completion(self):
        closure = self.payload[
            "closure_interpretation"
        ]

        self.assertTrue(
            closure[
                "this_is_a_blocked_frontier_freeze"
            ]
        )

        self.assertTrue(
            closure[
                "this_is_not_SE4_completion"
            ]
        )

    def test_23_no_SE5_authorization_claim(self):
        self.assertTrue(
            self.payload[
                "closure_interpretation"
            ][
                "this_does_not_authorize_SE5"
            ]
        )

    def test_24_no_physical_validation_claim(self):
        self.assertFalse(
            self.payload[
                "closure_interpretation"
            ][
                "software_success_equals_physical_validation"
            ]
        )

    def test_25_future_grouping_requirements(self):
        future = self.payload[
            "future_training_requirements"
        ]

        self.assertTrue(
            future[
                "trajectory_grouping_required"
            ]
        )

        self.assertTrue(
            future[
                "derivative_lineage_grouping_required"
            ]
        )

        self.assertTrue(
            future[
                "cross_partition_training_forbidden"
            ]
        )

    def test_26_project_state_records_blocked_frontier(self):
        text = PROJECT_STATE.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "## SE4 health-model training blocked-frontier freeze V1",
            text,
        )

        self.assertIn(
            "SE4 remains incomplete",
            text,
        )

        self.assertIn(
            "SE5 remains blocked",
            text,
        )


if __name__ == "__main__":
    unittest.main()
