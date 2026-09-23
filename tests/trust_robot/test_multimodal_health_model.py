import copy
import json
from pathlib import Path
import unittest

from trust_robot.multimodal_health_model import (
    CAMERA_IMU_CHANNELS,
    CURRENT_EVIDENCE_GATE,
    LIDAR_PHASE4_FEATURES,
    HealthModelInterfaceError,
    HealthModelLifecycle,
    assert_inference_authorized,
    assert_training_authorized,
    emit_health_state,
    health_state_order,
    validate_manifest,
)


ROOT = Path(__file__).resolve().parents[2]

CONFIG = (
    ROOT
    / "configs"
    / "trust_robot"
    / "phase5_multimodal_health_model_interface_candidate_v1.json"
)


class TestMultimodalHealthModelInterface(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(
            CONFIG.read_text(
                encoding="utf-8"
            )
        )

    def test_01_health_states_exact(self):
        self.assertEqual(
            health_state_order(),
            (
                "healthy",
                "degraded",
                "unusable",
            ),
        )

    def test_02_lifecycle_blocked(self):
        self.assertEqual(
            self.payload[
                "lifecycle_status"
            ],
            HealthModelLifecycle
            .INTERFACE_IMPLEMENTED_EVIDENCE_BLOCKED
            .value,
        )

    def test_03_core_modalities(self):
        self.assertEqual(
            self.payload[
                "modalities"
            ]["core"],
            [
                "camera",
                "imu",
                "lidar",
            ],
        )

    def test_04_gnss_optional(self):
        self.assertEqual(
            self.payload[
                "modalities"
            ]["optional"],
            ["gnss"],
        )

    def test_05_camera_channels_exact(self):
        self.assertEqual(
            tuple(
                self.payload[
                    "diagnostic_inputs"
                ]["camera"][
                    "required_channel_kinds"
                ]
            ),
            CAMERA_IMU_CHANNELS,
        )

    def test_06_imu_channels_exact(self):
        self.assertEqual(
            tuple(
                self.payload[
                    "diagnostic_inputs"
                ]["imu"][
                    "required_channel_kinds"
                ]
            ),
            CAMERA_IMU_CHANNELS,
        )

    def test_07_camera_features_empty(self):
        self.assertEqual(
            self.payload[
                "diagnostic_inputs"
            ]["camera"][
                "exact_feature_names"
            ],
            [],
        )

    def test_08_imu_features_empty(self):
        self.assertEqual(
            self.payload[
                "diagnostic_inputs"
            ]["imu"][
                "exact_feature_names"
            ],
            [],
        )

    def test_09_camera_contract_unselected(self):
        self.assertFalse(
            self.payload[
                "diagnostic_inputs"
            ]["camera"][
                "feature_contract_selected"
            ]
        )

    def test_10_imu_contract_unselected(self):
        self.assertFalse(
            self.payload[
                "diagnostic_inputs"
            ]["imu"][
                "feature_contract_selected"
            ]
        )

    def test_11_lidar_feature_count(self):
        self.assertEqual(
            len(
                self.payload[
                    "diagnostic_inputs"
                ]["lidar"][
                    "features"
                ]
            ),
            5,
        )

    def test_12_lidar_exact_features(self):
        actual = tuple(
            (
                item["name"],
                item["unit"],
            )
            for item in self.payload[
                "diagnostic_inputs"
            ]["lidar"][
                "features"
            ]
        )

        self.assertEqual(
            actual,
            LIDAR_PHASE4_FEATURES,
        )

    def test_13_lidar_not_reopened(self):
        self.assertFalse(
            self.payload[
                "diagnostic_inputs"
            ]["lidar"][
                "phase4_feature_contract_reopened"
            ]
        )

    def test_14_gnss_features_empty(self):
        self.assertEqual(
            self.payload[
                "diagnostic_inputs"
            ]["gnss"][
                "exact_feature_names"
            ],
            [],
        )

    def test_15_availability_not_health(self):
        self.assertFalse(
            self.payload[
                "availability_boundary"
            ][
                "availability_is_health_label"
            ]
        )

    def test_16_missing_not_zero_vector(self):
        self.assertFalse(
            self.payload[
                "availability_boundary"
            ][
                "missing_measurement_encoded_as_zero_feature_vector"
            ]
        )

    def test_17_architecture_unselected(self):
        self.assertFalse(
            self.payload[
                "model_selection"
            ][
                "classifier_architecture_selected"
            ]
        )

    def test_18_threshold_unselected(self):
        self.assertIsNone(
            self.payload[
                "model_selection"
            ][
                "health_threshold"
            ]
        )

    def test_19_calibration_unselected(self):
        self.assertIsNone(
            self.payload[
                "model_selection"
            ][
                "calibration_parameter"
            ]
        )

    def test_20_no_model_artifact(self):
        self.assertIsNone(
            self.payload[
                "model_selection"
            ][
                "trained_model_artifact_sha256"
            ]
        )

    def test_21_state_output_disabled(self):
        self.assertEqual(
            self.payload[
                "runtime_output"
            ][
                "health_state_output"
            ],
            "disabled",
        )

    def test_22_probability_output_disabled(self):
        self.assertEqual(
            self.payload[
                "runtime_output"
            ][
                "health_probability_output"
            ],
            "disabled",
        )

    def test_23_training_unauthorized(self):
        self.assertFalse(
            CURRENT_EVIDENCE_GATE
            .classifier_training_authorized
        )

    def test_24_inference_unauthorized(self):
        self.assertFalse(
            CURRENT_EVIDENCE_GATE
            .health_inference_authorized
        )

    def test_25_training_guard_raises(self):
        with self.assertRaises(
            HealthModelInterfaceError
        ):
            assert_training_authorized()

    def test_26_inference_guard_raises(self):
        with self.assertRaises(
            HealthModelInterfaceError
        ):
            assert_inference_authorized()

    def test_27_emit_guard_raises(self):
        with self.assertRaises(
            HealthModelInterfaceError
        ):
            emit_health_state()

    def test_28_zero_baseline_sources(self):
        self.assertEqual(
            CURRENT_EVIDENCE_GATE
            .accepted_baseline_nominality_source_count,
            0,
        )

    def test_29_zero_supervision_sources(self):
        self.assertEqual(
            CURRENT_EVIDENCE_GATE
            .accepted_health_supervision_source_count,
            0,
        )

    def test_30_zero_real_labels(self):
        self.assertEqual(
            CURRENT_EVIDENCE_GATE
            .real_health_label_count,
            0,
        )

    def test_31_confirmation_closed(self):
        self.assertTrue(
            CURRENT_EVIDENCE_GATE
            .confirmation_closed
        )

    def test_32_confirmation_selection_forbidden(self):
        self.assertFalse(
            CURRENT_EVIDENCE_GATE
            .confirmation_selection_authorized
        )

    def test_33_physical_validation_deferred(self):
        self.assertTrue(
            CURRENT_EVIDENCE_GATE
            .physical_validation_deferred
        )

    def test_34_manifest_validates(self):
        validate_manifest(
            self.payload
        )

    def test_35_feature_injection_rejected(self):
        modified = copy.deepcopy(
            self.payload
        )

        modified[
            "diagnostic_inputs"
        ]["camera"][
            "exact_feature_names"
        ] = [
            "invented_feature"
        ]

        with self.assertRaises(
            HealthModelInterfaceError
        ):
            validate_manifest(
                modified
            )

    def test_36_training_enable_rejected(self):
        modified = copy.deepcopy(
            self.payload
        )

        modified[
            "runtime_output"
        ][
            "training_authorized"
        ] = True

        with self.assertRaises(
            HealthModelInterfaceError
        ):
            validate_manifest(
                modified
            )


if __name__ == "__main__":
    unittest.main()
