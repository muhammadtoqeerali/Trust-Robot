import copy
import json
from pathlib import Path
import unittest

from trust_robot.camera_imu_diagnostic_channels import (
    CAMERA_CHANNELS,
    CAMERA_CONTROLLED_STRESSOR_FAMILIES,
    CURRENT_INNOVATION_CONTRACT,
    IMU_CHANNELS,
    IMU_CONTROLLED_STRESSOR_FAMILIES,
    ChannelImplementationStatus,
    DiagnosticChannelContractError,
    DiagnosticChannelKind,
    EvidenceUseRole,
    channel_specs_for,
    validate_contract_manifest,
)
from trust_robot.multimodal_diagnostic_foundation import (
    Modality,
)


ROOT = Path(__file__).resolve().parents[2]

CONFIG = (
    ROOT
    / "configs"
    / "trust_robot"
    / "phase5_camera_imu_diagnostic_channel_contract_candidate_v1.json"
)


class TestCameraImuDiagnosticChannels(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(
            CONFIG.read_text(
                encoding="utf-8"
            )
        )

    def test_01_camera_has_three_channels(self):
        self.assertEqual(
            len(CAMERA_CHANNELS),
            3,
        )

    def test_02_imu_has_three_channels(self):
        self.assertEqual(
            len(IMU_CHANNELS),
            3,
        )

    def test_03_required_channel_order_camera(self):
        self.assertEqual(
            tuple(
                item.channel_kind
                for item in CAMERA_CHANNELS
            ),
            (
                DiagnosticChannelKind.LOW_LEVEL_SIGNAL_SUMMARY,
                DiagnosticChannelKind.FRONTEND_DIAGNOSTIC,
                DiagnosticChannelKind.RESIDUAL_HISTORY,
            ),
        )

    def test_04_required_channel_order_imu(self):
        self.assertEqual(
            tuple(
                item.channel_kind
                for item in IMU_CHANNELS
            ),
            (
                DiagnosticChannelKind.LOW_LEVEL_SIGNAL_SUMMARY,
                DiagnosticChannelKind.FRONTEND_DIAGNOSTIC,
                DiagnosticChannelKind.RESIDUAL_HISTORY,
            ),
        )

    def test_05_camera_low_level_features_unselected(self):
        self.assertIs(
            CAMERA_CHANNELS[0].implementation_status,
            ChannelImplementationStatus
            .BASIS_SUPPORTED_FEATURES_UNSELECTED,
        )

    def test_06_imu_low_level_features_unselected(self):
        self.assertIs(
            IMU_CHANNELS[0].implementation_status,
            ChannelImplementationStatus
            .BASIS_SUPPORTED_FEATURES_UNSELECTED,
        )

    def test_07_camera_frontend_not_implemented(self):
        self.assertIs(
            CAMERA_CHANNELS[1].implementation_status,
            ChannelImplementationStatus
            .REQUIRED_INTERFACE_NOT_IMPLEMENTED,
        )

    def test_08_imu_frontend_not_implemented(self):
        self.assertIs(
            IMU_CHANNELS[1].implementation_status,
            ChannelImplementationStatus
            .REQUIRED_INTERFACE_NOT_IMPLEMENTED,
        )

    def test_09_camera_residual_not_implemented(self):
        self.assertIs(
            CAMERA_CHANNELS[2].implementation_status,
            ChannelImplementationStatus
            .REQUIRED_INTERFACE_NOT_IMPLEMENTED,
        )

    def test_10_imu_residual_not_implemented(self):
        self.assertIs(
            IMU_CHANNELS[2].implementation_status,
            ChannelImplementationStatus
            .REQUIRED_INTERFACE_NOT_IMPLEMENTED,
        )

    def test_11_no_camera_exact_features(self):
        self.assertTrue(
            all(
                not item.exact_feature_names
                for item in CAMERA_CHANNELS
            )
        )

    def test_12_no_imu_exact_features(self):
        self.assertTrue(
            all(
                not item.exact_feature_names
                for item in IMU_CHANNELS
            )
        )

    def test_13_camera_specs_lookup(self):
        self.assertEqual(
            channel_specs_for(
                Modality.CAMERA
            ),
            CAMERA_CHANNELS,
        )

    def test_14_imu_specs_lookup(self):
        self.assertEqual(
            channel_specs_for(
                Modality.IMU
            ),
            IMU_CHANNELS,
        )

    def test_15_lidar_lookup_rejected(self):
        with self.assertRaises(
            DiagnosticChannelContractError
        ):
            channel_specs_for(
                Modality.LIDAR
            )

    def test_16_gnss_lookup_rejected(self):
        with self.assertRaises(
            DiagnosticChannelContractError
        ):
            channel_specs_for(
                Modality.GNSS
            )

    def test_17_camera_stressors_exact(self):
        self.assertEqual(
            CAMERA_CONTROLLED_STRESSOR_FAMILIES,
            (
                "camera_blur",
                "camera_exposure_degradation",
            ),
        )

    def test_18_imu_stressor_exact(self):
        self.assertEqual(
            IMU_CONTROLLED_STRESSOR_FAMILIES,
            (
                "bias_or_drift",
            ),
        )

    def test_19_stressors_not_features(self):
        for modality in (
            "camera",
            "imu",
        ):
            for item in self.payload[
                "controlled_stressor_families"
            ][modality]:
                self.assertFalse(
                    item[
                        "is_diagnostic_feature"
                    ]
                )

    def test_20_stressors_not_labels(self):
        for modality in (
            "camera",
            "imu",
        ):
            for item in self.payload[
                "controlled_stressor_families"
            ][modality]:
                self.assertFalse(
                    item[
                        "is_health_label"
                    ]
                )

    def test_21_current_innovation_role(self):
        self.assertEqual(
            CURRENT_INNOVATION_CONTRACT[
                "role"
            ],
            EvidenceUseRole
            .SHORT_HORIZON_FACTOR_CONDITIONING_ONLY
            .value,
        )

    def test_22_current_innovation_separate(self):
        self.assertTrue(
            CURRENT_INNOVATION_CONTRACT[
                "separation_required"
            ]
        )

    def test_23_current_innovation_not_health_selected(self):
        self.assertFalse(
            CURRENT_INNOVATION_CONTRACT[
                "persistent_health_input_selected"
            ]
        )

    def test_24_bias_state_not_health_feature(self):
        self.assertFalse(
            self.payload[
                "estimator_state_concepts"
            ][
                "bias_state_is_automatically_health_feature"
            ]
        )

    def test_25_bias_state_not_health_label(self):
        self.assertFalse(
            self.payload[
                "estimator_state_concepts"
            ][
                "bias_state_is_automatically_health_label"
            ]
        )

    def test_26_imu_preintegration_basis_present(self):
        self.assertTrue(
            self.payload[
                "estimator_state_concepts"
            ][
                "imu_preintegration_named_by_project"
            ]
        )

    def test_27_visual_reprojection_basis_present(self):
        self.assertTrue(
            self.payload[
                "estimator_state_concepts"
            ][
                "visual_relative_motion_reprojection_named_by_project"
            ]
        )

    def test_28_camera_contract_unselected(self):
        self.assertFalse(
            self.payload[
                "feature_selection_boundary"
            ][
                "camera_feature_contract_selected"
            ]
        )

    def test_29_imu_contract_unselected(self):
        self.assertFalse(
            self.payload[
                "feature_selection_boundary"
            ][
                "imu_feature_contract_selected"
            ]
        )

    def test_30_visual_frontend_not_implemented(self):
        self.assertFalse(
            self.payload[
                "feature_selection_boundary"
            ][
                "visual_frontend_diagnostics_implemented"
            ]
        )

    def test_31_imu_preintegration_not_implemented(self):
        self.assertFalse(
            self.payload[
                "feature_selection_boundary"
            ][
                "imu_preintegration_diagnostics_implemented"
            ]
        )

    def test_32_no_health_label(self):
        self.assertFalse(
            self.payload[
                "scientific_boundary"
            ][
                "health_label_assigned"
            ]
        )

    def test_33_no_classifier_training(self):
        self.assertFalse(
            self.payload[
                "scientific_boundary"
            ][
                "classifier_training_authorized"
            ]
        )

    def test_34_no_validation_data(self):
        self.assertFalse(
            self.payload[
                "scientific_boundary"
            ][
                "validation_data_used"
            ]
        )

    def test_35_no_confirmation_data(self):
        self.assertFalse(
            self.payload[
                "scientific_boundary"
            ][
                "confirmation_data_used"
            ]
        )

    def test_36_no_reference_data(self):
        self.assertFalse(
            self.payload[
                "scientific_boundary"
            ][
                "reference_data_used"
            ]
        )

    def test_37_no_ate_rpe(self):
        self.assertFalse(
            self.payload[
                "scientific_boundary"
            ][
                "ate_rpe_computed"
            ]
        )

    def test_38_contract_validates(self):
        validate_contract_manifest(
            self.payload
        )

    def test_39_feature_injection_rejected(self):
        modified = copy.deepcopy(
            self.payload
        )

        modified[
            "persistent_health_evidence_channels"
        ][
            "camera"
        ][0][
            "exact_feature_names"
        ] = [
            "invented_brightness"
        ]

        with self.assertRaises(
            DiagnosticChannelContractError
        ):
            validate_contract_manifest(
                modified
            )

    def test_40_innovation_health_leakage_rejected(self):
        modified = copy.deepcopy(
            self.payload
        )

        modified[
            "current_innovation_separation"
        ][
            "persistent_health_input_selected"
        ] = True

        with self.assertRaises(
            DiagnosticChannelContractError
        ):
            validate_contract_manifest(
                modified
            )


if __name__ == "__main__":
    unittest.main()
