import copy
import json
from pathlib import Path
import unittest

from trust_robot.multimodal_diagnostic_foundation import (
    AVAILABILITY_RECEIPT_SCHEMA,
    FOUNDATION_CONTRACT_ID,
    FOUNDATION_SCHEMA,
    HEALTH_STATES,
    LIDAR_FEATURE_SPECS,
    PHASE4_LIDAR_FEATURE_CONTRACT_ID,
    PHASE4_LIDAR_FREEZE_SHA256,
    AvailabilityState,
    FeatureContractStatus,
    Modality,
    ModalityRole,
    MultimodalDiagnosticFoundationError,
    SplitRole,
    adapter_contract_for,
    build_foundation_manifest,
    build_measurement_availability_receipt,
    camera_adapter_contract,
    canonical_content_sha256,
    gnss_adapter_contract,
    imu_adapter_contract,
    lidar_adapter_contract,
    measurement_availability_receipt_content_sha256,
    measurement_availability_receipt_payload,
    modality_adapter_contracts,
    validate_foundation_manifest,
    validate_measurement_availability_receipt_payload,
)


ROOT = Path(__file__).resolve().parents[2]

CONFIG = (
    ROOT
    / "configs"
    / "trust_robot"
    / "phase5_multimodal_diagnostic_foundation_candidate_v1.json"
)

VALID_SHA = "a" * 64


class TestMultimodalDiagnosticFoundation(unittest.TestCase):

    def test_01_schema(self):
        self.assertEqual(
            FOUNDATION_SCHEMA,
            "TRUST_ROBOT_PHASE5_MULTIMODAL_DIAGNOSTIC_FOUNDATION_V1",
        )

    def test_02_contract_id(self):
        self.assertEqual(
            FOUNDATION_CONTRACT_ID,
            "trust_robot_phase5_multimodal_diagnostic_foundation_v1",
        )

    def test_03_shared_health_states(self):
        self.assertEqual(
            HEALTH_STATES,
            ("healthy", "degraded", "unusable"),
        )

    def test_04_core_modalities(self):
        manifest = build_foundation_manifest()

        self.assertEqual(
            manifest["scope"]["core_modalities"],
            ["camera", "imu", "lidar"],
        )

    def test_05_optional_modalities(self):
        manifest = build_foundation_manifest()

        self.assertEqual(
            manifest["scope"]["optional_modalities"],
            ["gnss"],
        )

    def test_06_missing_modalities_are_not_fabricated(self):
        manifest = build_foundation_manifest()

        self.assertTrue(
            manifest["scope"][
                "do_not_fabricate_missing_modalities"
            ]
        )

    def test_07_availability_is_not_health_label(self):
        manifest = build_foundation_manifest()

        self.assertFalse(
            manifest["scope"][
                "availability_is_health_label"
            ]
        )

    def test_08_camera_is_core(self):
        self.assertIs(
            camera_adapter_contract().role,
            ModalityRole.CORE,
        )

    def test_09_camera_feature_contract_unselected(self):
        contract = camera_adapter_contract()

        self.assertIs(
            contract.feature_contract_status,
            FeatureContractStatus.INTERFACE_ONLY,
        )
        self.assertIsNone(
            contract.feature_contract_id
        )
        self.assertEqual(
            contract.feature_specs,
            (),
        )

    def test_10_camera_source_not_selected(self):
        contract = camera_adapter_contract()

        self.assertIsNone(
            contract.selected_source_stream_id
        )

    def test_11_camera_known_stream_inventory(self):
        self.assertEqual(
            camera_adapter_contract().known_source_stream_candidates,
            (
                "/camera/color/image_raw/compressed",
            ),
        )

    def test_12_imu_is_core(self):
        self.assertIs(
            imu_adapter_contract().role,
            ModalityRole.CORE,
        )

    def test_13_imu_feature_contract_unselected(self):
        contract = imu_adapter_contract()

        self.assertIs(
            contract.feature_contract_status,
            FeatureContractStatus.INTERFACE_ONLY,
        )
        self.assertIsNone(
            contract.feature_contract_id
        )
        self.assertEqual(
            contract.feature_specs,
            (),
        )

    def test_14_imu_source_not_selected(self):
        self.assertIsNone(
            imu_adapter_contract().selected_source_stream_id
        )

    def test_15_imu_known_stream_inventory(self):
        self.assertEqual(
            imu_adapter_contract().known_source_stream_candidates,
            (
                "/camera/imu",
                "/handsfree/imu",
            ),
        )

    def test_16_lidar_is_core(self):
        self.assertIs(
            lidar_adapter_contract().role,
            ModalityRole.CORE,
        )

    def test_17_lidar_binds_phase4_freeze(self):
        self.assertEqual(
            PHASE4_LIDAR_FREEZE_SHA256,
            "09a05d8491c7af7cd8122ee58d9f485d21f03d2cd50f44764d57d48726d08e88",
        )

    def test_18_lidar_feature_contract_id(self):
        self.assertEqual(
            lidar_adapter_contract().feature_contract_id,
            PHASE4_LIDAR_FEATURE_CONTRACT_ID,
        )

    def test_19_lidar_source_remains_velodyne(self):
        self.assertEqual(
            lidar_adapter_contract().selected_source_stream_id,
            "/velodyne_points",
        )

    def test_20_lidar_feature_order_exact(self):
        self.assertEqual(
            tuple(
                feature.name
                for feature in LIDAR_FEATURE_SPECS
            ),
            (
                "source_point_count",
                "target_point_count",
                "fixed_point_iterations",
                "final_correspondence_count",
                "final_nearest_neighbor_rmse_m",
            ),
        )

    def test_21_lidar_feature_units_exact(self):
        self.assertEqual(
            tuple(
                feature.unit
                for feature in LIDAR_FEATURE_SPECS
            ),
            (
                "count",
                "count",
                "count",
                "count",
                "m",
            ),
        )

    def test_22_gnss_is_optional(self):
        self.assertIs(
            gnss_adapter_contract().role,
            ModalityRole.OPTIONAL,
        )

    def test_23_gnss_feature_contract_unselected(self):
        contract = gnss_adapter_contract()

        self.assertIs(
            contract.feature_contract_status,
            FeatureContractStatus.INTERFACE_ONLY,
        )
        self.assertIsNone(
            contract.feature_contract_id
        )
        self.assertEqual(
            contract.feature_specs,
            (),
        )

    def test_24_gnss_source_not_selected(self):
        self.assertIsNone(
            gnss_adapter_contract().selected_source_stream_id
        )

    def test_25_all_health_training_unauthorized(self):
        self.assertTrue(
            all(
                contract.health_training_authorized is False
                for contract in modality_adapter_contracts()
            )
        )

    def test_26_adapter_lookup(self):
        self.assertIs(
            adapter_contract_for("camera").modality,
            Modality.CAMERA,
        )
        self.assertIs(
            adapter_contract_for(Modality.LIDAR).modality,
            Modality.LIDAR,
        )

    def test_27_adapter_lookup_rejects_unknown(self):
        with self.assertRaises(
            MultimodalDiagnosticFoundationError
        ):
            adapter_contract_for("radar")

    def test_28_manifest_config_exact(self):
        payload = json.loads(
            CONFIG.read_text(
                encoding="utf-8"
            )
        )

        validate_foundation_manifest(
            payload
        )

        self.assertEqual(
            payload,
            build_foundation_manifest(),
        )

    def test_29_manifest_rejects_camera_feature_selection(self):
        payload = build_foundation_manifest()

        modified = copy.deepcopy(
            payload
        )

        modified[
            "scientific_boundary"
        ][
            "camera_feature_contract_selected"
        ] = True

        with self.assertRaises(
            MultimodalDiagnosticFoundationError
        ):
            validate_foundation_manifest(
                modified
            )

    def test_30_manifest_rejects_health_output_enable(self):
        payload = build_foundation_manifest()

        modified = copy.deepcopy(
            payload
        )

        modified[
            "scientific_boundary"
        ][
            "health_state_output_enabled"
        ] = True

        with self.assertRaises(
            MultimodalDiagnosticFoundationError
        ):
            validate_foundation_manifest(
                modified
            )

    def test_31_camera_present_availability_receipt(self):
        receipt = build_measurement_availability_receipt(
            modality="camera",
            source_id="/camera/color/image_raw/compressed",
            trajectory_or_session_id="Circle_01",
            split_role="train",
            availability_state="observed_present",
            evidence_sha256=VALID_SHA,
        )

        self.assertIs(
            receipt.availability_state,
            AvailabilityState.OBSERVED_PRESENT,
        )

    def test_32_camera_absent_availability_receipt(self):
        receipt = build_measurement_availability_receipt(
            modality="camera",
            source_id="/camera/color/image_raw/compressed",
            trajectory_or_session_id="example_missing_stream",
            split_role="train",
            availability_state="observed_absent",
            evidence_sha256=VALID_SHA,
        )

        self.assertIs(
            receipt.availability_state,
            AvailabilityState.OBSERVED_ABSENT,
        )

    def test_33_imu_unresolved_availability_receipt(self):
        receipt = build_measurement_availability_receipt(
            modality="imu",
            source_id="/handsfree/imu",
            trajectory_or_session_id="session_x",
            split_role="unspecified",
            availability_state="unresolved",
            evidence_sha256=VALID_SHA,
        )

        self.assertIs(
            receipt.availability_state,
            AvailabilityState.UNRESOLVED,
        )

    def test_34_confirmation_receipt_does_not_authorize_selection(self):
        receipt = build_measurement_availability_receipt(
            modality="lidar",
            source_id="/velodyne_points",
            trajectory_or_session_id="Circle_02",
            split_role="confirmation_test",
            availability_state="observed_present",
            evidence_sha256=VALID_SHA,
        )

        payload = measurement_availability_receipt_payload(
            receipt
        )

        self.assertEqual(
            payload["split_role"],
            SplitRole.CONFIRMATION.value,
        )

        self.assertFalse(
            payload["confirmation_used_for_selection"]
        )

        self.assertFalse(
            payload["classifier_training_authorized"]
        )

    def test_35_availability_payload_has_no_health_state(self):
        receipt = build_measurement_availability_receipt(
            modality="gnss",
            source_id="/ublox/fix",
            trajectory_or_session_id="session_x",
            split_role="unspecified",
            availability_state="observed_present",
            evidence_sha256=VALID_SHA,
        )

        payload = measurement_availability_receipt_payload(
            receipt
        )

        self.assertNotIn(
            "health_state",
            payload,
        )

        self.assertFalse(
            payload["health_label_assigned"]
        )

        self.assertFalse(
            payload["health_probability_emitted"]
        )

    def test_36_availability_payload_validation(self):
        receipt = build_measurement_availability_receipt(
            modality="imu",
            source_id="/camera/imu",
            trajectory_or_session_id="session_x",
            split_role="validation",
            availability_state="observed_present",
            evidence_sha256=VALID_SHA,
        )

        payload = measurement_availability_receipt_payload(
            receipt
        )

        validate_measurement_availability_receipt_payload(
            payload
        )

        self.assertEqual(
            payload["schema"],
            AVAILABILITY_RECEIPT_SCHEMA,
        )

    def test_37_availability_payload_rejects_health_label(self):
        receipt = build_measurement_availability_receipt(
            modality="lidar",
            source_id="/velodyne_points",
            trajectory_or_session_id="Circle_01",
            split_role="train",
            availability_state="observed_present",
            evidence_sha256=VALID_SHA,
        )

        payload = measurement_availability_receipt_payload(
            receipt
        )

        payload["health_label_assigned"] = True

        with self.assertRaises(
            MultimodalDiagnosticFoundationError
        ):
            validate_measurement_availability_receipt_payload(
                payload
            )

    def test_38_availability_payload_rejects_extra_threshold(self):
        receipt = build_measurement_availability_receipt(
            modality="camera",
            source_id="/camera/color/image_raw/compressed",
            trajectory_or_session_id="Circle_01",
            split_role="train",
            availability_state="observed_present",
            evidence_sha256=VALID_SHA,
        )

        payload = measurement_availability_receipt_payload(
            receipt
        )

        payload["threshold"] = 0.5

        with self.assertRaises(
            MultimodalDiagnosticFoundationError
        ):
            validate_measurement_availability_receipt_payload(
                payload
            )

    def test_39_invalid_sha_rejected(self):
        with self.assertRaises(
            MultimodalDiagnosticFoundationError
        ):
            build_measurement_availability_receipt(
                modality="camera",
                source_id="/camera/color/image_raw/compressed",
                trajectory_or_session_id="Circle_01",
                split_role="train",
                availability_state="observed_present",
                evidence_sha256="not-a-sha",
            )

    def test_40_empty_source_rejected(self):
        with self.assertRaises(
            MultimodalDiagnosticFoundationError
        ):
            build_measurement_availability_receipt(
                modality="imu",
                source_id="",
                trajectory_or_session_id="Circle_01",
                split_role="train",
                availability_state="observed_present",
                evidence_sha256=VALID_SHA,
            )

    def test_41_receipt_digest_deterministic(self):
        receipt = build_measurement_availability_receipt(
            modality="lidar",
            source_id="/velodyne_points",
            trajectory_or_session_id="Circle_01",
            split_role="train",
            availability_state="observed_present",
            evidence_sha256=VALID_SHA,
        )

        first = measurement_availability_receipt_content_sha256(
            receipt
        )

        second = canonical_content_sha256(
            measurement_availability_receipt_payload(
                receipt
            )
        )

        self.assertEqual(
            first,
            second,
        )

        self.assertEqual(
            len(first),
            64,
        )

    def test_42_no_classifier_or_threshold_selected(self):
        manifest = build_foundation_manifest()

        boundary = manifest[
            "scientific_boundary"
        ]

        self.assertFalse(
            boundary["classifier_model_selected"]
        )

        self.assertFalse(
            boundary["classifier_training_authorized"]
        )

        self.assertFalse(
            boundary["health_threshold_selected"]
        )

        self.assertFalse(
            boundary["calibration_temperature_selected"]
        )

    def test_43_no_ate_rpe_authorization(self):
        manifest = build_foundation_manifest()

        self.assertFalse(
            manifest[
                "scientific_boundary"
            ][
                "ate_rpe_computation_authorized"
            ]
        )

    def test_44_final_error_not_health_supervision(self):
        manifest = build_foundation_manifest()

        self.assertFalse(
            manifest[
                "scientific_boundary"
            ][
                "final_localization_error_used_as_health_supervision"
            ]
        )


if __name__ == "__main__":
    unittest.main()
