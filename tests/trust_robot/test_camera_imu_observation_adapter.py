import copy
import json
from pathlib import Path
import unittest

from trust_robot.camera_imu_observation_adapter import (
    ADAPTER_ID,
    CAMERA_STREAM_ID,
    IMU_STREAM_IDS,
    SCHEMA,
    CameraImuObservationAdapterError,
    build_adapter_manifest,
    build_raw_observation_receipt,
    content_sha256,
    modality_for_stream,
    receipt_content_sha256,
    receipt_payload,
    validate_adapter_manifest,
    validate_receipt_payload,
)
from trust_robot.multimodal_diagnostic_foundation import (
    Modality,
    SplitRole,
)


ROOT = Path(__file__).resolve().parents[2]

CONFIG = (
    ROOT
    / "configs"
    / "trust_robot"
    / "phase5_camera_imu_observation_adapter_candidate_v1.json"
)


class TestCameraImuObservationAdapter(unittest.TestCase):

    def camera_receipt(self, **overrides):
        kwargs = {
            "source_stream_id":
                CAMERA_STREAM_ID,

            "trajectory_or_session_id":
                "Circle_01",

            "split_role":
                "train",

            "message_index":
                0,

            "serialized_payload":
                b"camera-payload",

            "bag_record_time_ns":
                123456789,

            "header_stamp_ns":
                123450000,

            "message_type":
                "sensor_msgs/msg/CompressedImage",
        }

        kwargs.update(
            overrides
        )

        return build_raw_observation_receipt(
            **kwargs
        )

    def imu_receipt(self, **overrides):
        kwargs = {
            "source_stream_id":
                "/handsfree/imu",

            "trajectory_or_session_id":
                "Circle_01",

            "split_role":
                "train",

            "message_index":
                0,

            "serialized_payload":
                b"imu-payload",

            "bag_record_time_ns":
                123456789,

            "header_stamp_ns":
                123450000,

            "message_type":
                "sensor_msgs/msg/Imu",
        }

        kwargs.update(
            overrides
        )

        return build_raw_observation_receipt(
            **kwargs
        )

    def test_01_schema(self):
        self.assertEqual(
            SCHEMA,
            "TRUST_ROBOT_PHASE5_CAMERA_IMU_RAW_OBSERVATION_RECEIPT_V1",
        )

    def test_02_adapter_id(self):
        self.assertEqual(
            ADAPTER_ID,
            "trust_robot_phase5_m2dgr_camera_imu_raw_observation_adapter_v1",
        )

    def test_03_camera_stream_exact(self):
        self.assertEqual(
            CAMERA_STREAM_ID,
            "/camera/color/image_raw/compressed",
        )

    def test_04_imu_streams_exact(self):
        self.assertEqual(
            IMU_STREAM_IDS,
            (
                "/camera/imu",
                "/handsfree/imu",
            ),
        )

    def test_05_camera_modality_mapping(self):
        self.assertIs(
            modality_for_stream(
                CAMERA_STREAM_ID
            ),
            Modality.CAMERA,
        )

    def test_06_camera_imu_modality_mapping(self):
        self.assertIs(
            modality_for_stream(
                "/camera/imu"
            ),
            Modality.IMU,
        )

    def test_07_handsfree_modality_mapping(self):
        self.assertIs(
            modality_for_stream(
                "/handsfree/imu"
            ),
            Modality.IMU,
        )

    def test_08_unknown_stream_rejected(self):
        with self.assertRaises(
            CameraImuObservationAdapterError
        ):
            modality_for_stream(
                "/unknown"
            )

    def test_09_camera_receipt_payload_size(self):
        receipt = self.camera_receipt()

        self.assertEqual(
            receipt.serialized_payload_size_bytes,
            len(b"camera-payload"),
        )

    def test_10_camera_payload_hash(self):
        receipt = self.camera_receipt()

        self.assertEqual(
            len(
                receipt.serialized_payload_sha256
            ),
            64,
        )

    def test_11_imu_payload_hash(self):
        receipt = self.imu_receipt()

        self.assertEqual(
            len(
                receipt.serialized_payload_sha256
            ),
            64,
        )

    def test_12_payload_requires_bytes(self):
        with self.assertRaises(
            CameraImuObservationAdapterError
        ):
            self.camera_receipt(
                serialized_payload="not-bytes"
            )

    def test_13_negative_message_index_rejected(self):
        with self.assertRaises(
            CameraImuObservationAdapterError
        ):
            self.camera_receipt(
                message_index=-1
            )

    def test_14_bool_message_index_rejected(self):
        with self.assertRaises(
            CameraImuObservationAdapterError
        ):
            self.camera_receipt(
                message_index=True
            )

    def test_15_negative_record_time_rejected(self):
        with self.assertRaises(
            CameraImuObservationAdapterError
        ):
            self.camera_receipt(
                bag_record_time_ns=-1
            )

    def test_16_header_stamp_can_be_absent(self):
        receipt = self.camera_receipt(
            header_stamp_ns=None
        )

        payload = receipt_payload(
            receipt
        )

        self.assertFalse(
            payload[
                "timing_semantics"
            ][
                "header_stamp_present"
            ]
        )

    def test_17_negative_header_stamp_rejected(self):
        with self.assertRaises(
            CameraImuObservationAdapterError
        ):
            self.camera_receipt(
                header_stamp_ns=-1
            )

    def test_18_empty_message_type_rejected(self):
        with self.assertRaises(
            CameraImuObservationAdapterError
        ):
            self.camera_receipt(
                message_type=""
            )

    def test_19_split_train_preserved(self):
        receipt = self.camera_receipt()

        self.assertIs(
            receipt.split_role,
            SplitRole.TRAIN,
        )

    def test_20_split_validation_preserved(self):
        receipt = self.camera_receipt(
            split_role="validation"
        )

        self.assertIs(
            receipt.split_role,
            SplitRole.VALIDATION,
        )

    def test_21_confirmation_preserved_but_not_selected(self):
        receipt = self.camera_receipt(
            split_role="confirmation_test"
        )

        payload = receipt_payload(
            receipt
        )

        self.assertEqual(
            payload["split_role"],
            "confirmation_test",
        )

        self.assertFalse(
            payload[
                "health_boundary"
            ][
                "confirmation_used_for_selection"
            ]
        )

    def test_22_bag_record_time_is_transport_only(self):
        payload = receipt_payload(
            self.camera_receipt()
        )

        self.assertEqual(
            payload[
                "timing_semantics"
            ][
                "bag_record_time_role"
            ],
            "transport_or_container_time_only",
        )

    def test_23_header_physical_semantics_unverified(self):
        payload = receipt_payload(
            self.camera_receipt()
        )

        self.assertFalse(
            payload[
                "timing_semantics"
            ][
                "header_stamp_physical_capture_semantics_verified"
            ]
        )

    def test_24_shared_clock_domain_unverified(self):
        payload = receipt_payload(
            self.imu_receipt()
        )

        self.assertFalse(
            payload[
                "timing_semantics"
            ][
                "shared_clock_domain_verified"
            ]
        )

    def test_25_no_offset_selected(self):
        payload = receipt_payload(
            self.imu_receipt()
        )

        self.assertFalse(
            payload[
                "timing_semantics"
            ][
                "fixed_offset_selected"
            ]
        )

    def test_26_no_interpolation_selected(self):
        payload = receipt_payload(
            self.imu_receipt()
        )

        self.assertFalse(
            payload[
                "timing_semantics"
            ][
                "interpolation_rule_selected"
            ]
        )

    def test_27_no_feature_contract_selected(self):
        payload = receipt_payload(
            self.camera_receipt()
        )

        self.assertFalse(
            payload[
                "diagnostic_boundary"
            ][
                "feature_contract_selected"
            ]
        )

    def test_28_no_feature_vector_emitted(self):
        payload = receipt_payload(
            self.imu_receipt()
        )

        self.assertFalse(
            payload[
                "diagnostic_boundary"
            ][
                "feature_vector_emitted"
            ]
        )

    def test_29_no_aggregation(self):
        payload = receipt_payload(
            self.imu_receipt()
        )

        self.assertFalse(
            payload[
                "diagnostic_boundary"
            ][
                "aggregation_performed"
            ]
        )

    def test_30_no_normalization(self):
        payload = receipt_payload(
            self.imu_receipt()
        )

        self.assertFalse(
            payload[
                "diagnostic_boundary"
            ][
                "normalization_performed"
            ]
        )

    def test_31_no_health_label(self):
        payload = receipt_payload(
            self.camera_receipt()
        )

        self.assertFalse(
            payload[
                "health_boundary"
            ][
                "health_label_assigned"
            ]
        )

    def test_32_no_health_probability(self):
        payload = receipt_payload(
            self.camera_receipt()
        )

        self.assertFalse(
            payload[
                "health_boundary"
            ][
                "health_probability_emitted"
            ]
        )

    def test_33_training_unauthorized(self):
        payload = receipt_payload(
            self.imu_receipt()
        )

        self.assertFalse(
            payload[
                "health_boundary"
            ][
                "classifier_training_authorized"
            ]
        )

    def test_34_receipt_payload_validates(self):
        payload = receipt_payload(
            self.camera_receipt()
        )

        validate_receipt_payload(
            payload
        )

    def test_35_timing_claim_mutation_rejected(self):
        payload = receipt_payload(
            self.camera_receipt()
        )

        payload = copy.deepcopy(
            payload
        )

        payload[
            "timing_semantics"
        ][
            "shared_clock_domain_verified"
        ] = True

        with self.assertRaises(
            CameraImuObservationAdapterError
        ):
            validate_receipt_payload(
                payload
            )

    def test_36_health_label_mutation_rejected(self):
        payload = receipt_payload(
            self.imu_receipt()
        )

        payload = copy.deepcopy(
            payload
        )

        payload[
            "health_boundary"
        ][
            "health_label_assigned"
        ] = True

        with self.assertRaises(
            CameraImuObservationAdapterError
        ):
            validate_receipt_payload(
                payload
            )

    def test_37_extra_feature_rejected(self):
        payload = receipt_payload(
            self.imu_receipt()
        )

        payload = copy.deepcopy(
            payload
        )

        payload["features"] = {
            "invented": 1.0
        }

        with self.assertRaises(
            CameraImuObservationAdapterError
        ):
            validate_receipt_payload(
                payload
            )

    def test_38_digest_deterministic(self):
        receipt = self.camera_receipt()

        self.assertEqual(
            receipt_content_sha256(
                receipt
            ),
            content_sha256(
                receipt_payload(
                    receipt
                )
            ),
        )

    def test_39_manifest_matches_config(self):
        payload = json.loads(
            CONFIG.read_text(
                encoding="utf-8"
            )
        )

        validate_adapter_manifest(
            payload
        )

        self.assertEqual(
            payload,
            build_adapter_manifest(),
        )

    def test_40_manifest_camera_feature_unselected(self):
        manifest = build_adapter_manifest()

        self.assertFalse(
            manifest[
                "diagnostic_boundary"
            ][
                "camera_feature_contract_selected"
            ]
        )

    def test_41_manifest_imu_feature_unselected(self):
        manifest = build_adapter_manifest()

        self.assertFalse(
            manifest[
                "diagnostic_boundary"
            ][
                "imu_feature_contract_selected"
            ]
        )

    def test_42_manifest_no_health_state(self):
        manifest = build_adapter_manifest()

        self.assertFalse(
            manifest[
                "health_boundary"
            ][
                "health_state_output_enabled"
            ]
        )

    def test_43_manifest_no_training(self):
        manifest = build_adapter_manifest()

        self.assertFalse(
            manifest[
                "health_boundary"
            ][
                "classifier_training_authorized"
            ]
        )

    def test_44_manifest_mutation_rejected(self):
        manifest = build_adapter_manifest()

        modified = copy.deepcopy(
            manifest
        )

        modified[
            "diagnostic_boundary"
        ][
            "camera_feature_contract_selected"
        ] = True

        with self.assertRaises(
            CameraImuObservationAdapterError
        ):
            validate_adapter_manifest(
                modified
            )


if __name__ == "__main__":
    unittest.main()
