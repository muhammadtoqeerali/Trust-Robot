import copy
import json
from pathlib import Path
import unittest

from trust_robot.camera_imu_train_source_evidence import (
    CAMERA_STREAM,
    D435I_IMU_STREAM,
    FINDING,
    HANDSFREE_IMU_STREAM,
    SCHEMA,
    TRAIN_TRAJECTORIES,
    CameraImuTrainSourceEvidenceError,
    validate_source_evidence,
)


ROOT = Path(__file__).resolve().parents[2]

MANIFEST = (
    ROOT
    / "manifests"
    / "trust_robot_phase5_camera_imu_train_source_evidence_v1.json"
)


class TestCameraImuTrainSourceEvidence(unittest.TestCase):

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
            SCHEMA,
        )

    def test_02_finding(self):
        self.assertEqual(
            self.payload["finding"],
            FINDING,
        )

    def test_03_train_count(self):
        self.assertEqual(
            self.payload[
                "train_population"
            ][
                "trajectory_count"
            ],
            22,
        )

    def test_04_train_ids_exact(self):
        self.assertEqual(
            tuple(
                self.payload[
                    "train_population"
                ][
                    "trajectory_ids"
                ]
            ),
            TRAIN_TRAJECTORIES,
        )

    def test_05_total_messages(self):
        self.assertEqual(
            self.payload[
                "ingestion_totals"
            ][
                "selected_stream_messages"
            ],
            2816957,
        )

    def test_06_total_bytes(self):
        self.assertEqual(
            self.payload[
                "ingestion_totals"
            ][
                "selected_serialized_payload_bytes"
            ],
            4320203720,
        )

    def test_07_camera_presence(self):
        item = self.payload[
            "stream_evidence"
        ][CAMERA_STREAM]

        self.assertEqual(
            item["present_trajectory_count"],
            20,
        )

    def test_08_camera_absence(self):
        item = self.payload[
            "stream_evidence"
        ][CAMERA_STREAM]

        self.assertEqual(
            item["absent_trajectories"],
            ["street_010", "street_09"],
        )

    def test_09_camera_messages(self):
        self.assertEqual(
            self.payload[
                "stream_evidence"
            ][CAMERA_STREAM][
                "message_count"
            ],
            107675,
        )

    def test_10_camera_bytes(self):
        self.assertEqual(
            self.payload[
                "stream_evidence"
            ][CAMERA_STREAM][
                "serialized_payload_bytes"
            ],
            3429452123,
        )

    def test_11_camera_headers(self):
        item = self.payload[
            "stream_evidence"
        ][CAMERA_STREAM]

        self.assertEqual(
            item[
                "header_stamp_present_count"
            ],
            item[
                "message_count"
            ],
        )

    def test_12_d435i_presence(self):
        self.assertEqual(
            self.payload[
                "stream_evidence"
            ][D435I_IMU_STREAM][
                "present_trajectory_count"
            ],
            20,
        )

    def test_13_d435i_absence(self):
        self.assertEqual(
            self.payload[
                "stream_evidence"
            ][D435I_IMU_STREAM][
                "absent_trajectories"
            ],
            ["street_010", "street_09"],
        )

    def test_14_d435i_messages(self):
        self.assertEqual(
            self.payload[
                "stream_evidence"
            ][D435I_IMU_STREAM][
                "message_count"
            ],
            1404805,
        )

    def test_15_handsfree_presence(self):
        self.assertEqual(
            self.payload[
                "stream_evidence"
            ][HANDSFREE_IMU_STREAM][
                "present_trajectory_count"
            ],
            22,
        )

    def test_16_handsfree_no_absence(self):
        self.assertEqual(
            self.payload[
                "stream_evidence"
            ][HANDSFREE_IMU_STREAM][
                "absent_trajectory_count"
            ],
            0,
        )

    def test_17_handsfree_messages(self):
        self.assertEqual(
            self.payload[
                "stream_evidence"
            ][HANDSFREE_IMU_STREAM][
                "message_count"
            ],
            1304477,
        )

    def test_18_stream_message_sum(self):
        total = sum(
            item["message_count"]
            for item in self.payload[
                "stream_evidence"
            ].values()
        )

        self.assertEqual(
            total,
            2816957,
        )

    def test_19_stream_byte_sum(self):
        total = sum(
            item[
                "serialized_payload_bytes"
            ]
            for item in self.payload[
                "stream_evidence"
            ].values()
        )

        self.assertEqual(
            total,
            4320203720,
        )

    def test_20_camera_library_state(self):
        camera = self.payload[
            "representative_feasibility"
        ]["camera"]

        self.assertTrue(
            camera["pillow_available"]
        )
        self.assertFalse(
            camera["opencv_available"]
        )

    def test_21_camera_format(self):
        self.assertEqual(
            self.payload[
                "representative_feasibility"
            ]["camera"][
                "format_values"
            ],
            ["rgb8; jpeg compressed bgr8"],
        )

    def test_22_camera_decode_success(self):
        camera = self.payload[
            "representative_feasibility"
        ]["camera"]

        self.assertEqual(
            camera["decode_attempt_count"],
            20,
        )
        self.assertEqual(
            camera["decode_success_count"],
            20,
        )

    def test_23_camera_feature_unselected(self):
        self.assertFalse(
            self.payload[
                "scientific_boundary"
            ][
                "camera_feature_contract_selected"
            ]
        )

    def test_24_imu_feature_unselected(self):
        self.assertFalse(
            self.payload[
                "scientific_boundary"
            ][
                "imu_feature_contract_selected"
            ]
        )

    def test_25_no_health_training(self):
        boundary = self.payload[
            "scientific_boundary"
        ]

        self.assertFalse(
            boundary[
                "health_label_assigned"
            ]
        )
        self.assertFalse(
            boundary[
                "classifier_training_authorized"
            ]
        )

    def test_26_no_eval_leakage(self):
        boundary = self.payload[
            "scientific_boundary"
        ]

        self.assertFalse(
            boundary[
                "validation_data_used"
            ]
        )
        self.assertFalse(
            boundary[
                "confirmation_data_used"
            ]
        )
        self.assertFalse(
            boundary[
                "reference_data_used"
            ]
        )

    def test_27_content_digest_validates(self):
        validate_source_evidence(
            self.payload
        )

    def test_28_mutation_rejected(self):
        modified = copy.deepcopy(
            self.payload
        )

        modified[
            "scientific_boundary"
        ][
            "camera_feature_contract_selected"
        ] = True

        with self.assertRaises(
            CameraImuTrainSourceEvidenceError
        ):
            validate_source_evidence(
                modified
            )


if __name__ == "__main__":
    unittest.main()
