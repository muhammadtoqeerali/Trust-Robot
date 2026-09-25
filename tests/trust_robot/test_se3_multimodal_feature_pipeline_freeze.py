from hashlib import sha256
from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]

MANIFEST = (
    ROOT
    / "manifests/trust_robot_se3_multimodal_feature_pipeline_freeze_v1.json"
)

CONTRACT_CONFIG = (
    ROOT
    / "configs/trust_robot/se3_multimodal_feature_contract_v1.json"
)

CONTRACT_MODULE = (
    ROOT
    / "src/trust_robot/se3_multimodal_feature_contract.py"
)

CONTRACT_TEST = (
    ROOT
    / "tests/trust_robot/test_se3_multimodal_feature_contract.py"
)

EXTRACTION_MODULE = (
    ROOT
    / "src/trust_robot/se3_multimodal_feature_extraction.py"
)

EXTRACTION_RUNNER = (
    ROOT
    / "scripts/trust_robot/run_se3_multimodal_feature_extraction_v1.py"
)

EXTRACTION_TEST = (
    ROOT
    / "tests/trust_robot/test_se3_multimodal_feature_extraction.py"
)

SE2_FREEZE = (
    ROOT
    / "manifests/trust_robot_se2_health_supervision_protocol_freeze_v1.json"
)

LIDAR_FREEZE = (
    ROOT
    / "manifests/trust_robot_phase4_validated_diagnostic_feature_extraction_freeze_v1.json"
)

SOURCE_EVIDENCE = (
    ROOT
    / "manifests/trust_robot_phase5_camera_imu_train_source_evidence_v1.json"
)

SPLIT_MANIFEST = (
    ROOT
    / "manifests/m2dgr_trajectory_manifest_v1_split_freeze_v1.json"
)

PROJECT_STATE = (
    ROOT
    / "docs/TRUST_ROBOT_PROJECT_STATE.md"
)

EXPECTED_MANIFEST_FILE_SHA = "a987f9793b60ea674991577a189711f2e535961796b1d74dfd6454e60de8e994"
EXPECTED_MANIFEST_CONTENT_SHA = "ce68cfa263e31b20060d92af48b4eba6f82cc5b706bc7f3108c3ac2c6448bb90"


def file_sha(path):
    return sha256(
        path.read_bytes()
    ).hexdigest()


def canonical_sha(payload):
    value = dict(
        payload
    )

    value.pop(
        "content_sha256",
        None,
    )

    return sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode(
            "utf-8"
        )
    ).hexdigest()


class SE3MultimodalFeaturePipelineFreezeTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(
            MANIFEST.read_text(
                encoding="utf-8"
            )
        )

    def test_01_manifest_file_sha(self):
        self.assertEqual(
            file_sha(
                MANIFEST
            ),
            EXPECTED_MANIFEST_FILE_SHA,
        )

    def test_02_manifest_content_sha(self):
        self.assertEqual(
            self.payload[
                "content_sha256"
            ],
            EXPECTED_MANIFEST_CONTENT_SHA,
        )

        self.assertEqual(
            canonical_sha(
                self.payload
            ),
            EXPECTED_MANIFEST_CONTENT_SHA,
        )

    def test_03_schema(self):
        self.assertEqual(
            self.payload[
                "schema"
            ],
            "TRUST_ROBOT_SE3_MULTIMODAL_FEATURE_PIPELINE_FREEZE_V1",
        )

    def test_04_stage_identity(self):
        stage = self.payload[
            "stage"
        ]

        self.assertEqual(
            stage[
                "stage_id"
            ],
            "SE3",
        )

        self.assertEqual(
            stage[
                "stage_name"
            ],
            "multimodal_feature_pipeline",
        )

    def test_05_parent_frontier(self):
        parent = self.payload[
            "parent_frontier"
        ]

        self.assertEqual(
            parent[
                "commit"
            ],
            "48c334f161783ffbbba76c39fae7e083526804a4",
        )

        self.assertEqual(
            parent[
                "tree"
            ],
            "9fa29880729cadcfe1029a9535d2d465b11117c5",
        )

    def test_06_repository_implementation_hashes(self):
        implementation = self.payload[
            "implementation"
        ]

        expected = (
            (
                CONTRACT_MODULE,
                "feature_contract_module_sha256",
            ),
            (
                CONTRACT_CONFIG,
                "feature_contract_config_sha256",
            ),
            (
                CONTRACT_TEST,
                "feature_contract_test_sha256",
            ),
            (
                EXTRACTION_MODULE,
                "feature_extraction_module_sha256",
            ),
            (
                EXTRACTION_RUNNER,
                "feature_extraction_runner_sha256",
            ),
            (
                EXTRACTION_TEST,
                "feature_extraction_test_sha256",
            ),
        )

        for path, key in expected:
            self.assertEqual(
                file_sha(
                    path
                ),
                implementation[
                    key
                ],
            )

    def test_07_source_freeze_hashes(self):
        bindings = self.payload[
            "source_bindings"
        ]

        self.assertEqual(
            file_sha(
                SE2_FREEZE
            ),
            bindings[
                "SE2_health_supervision_freeze"
            ][
                "file_sha256"
            ],
        )

        self.assertEqual(
            file_sha(
                LIDAR_FREEZE
            ),
            bindings[
                "phase4_lidar_feature_freeze"
            ][
                "file_sha256"
            ],
        )

        self.assertEqual(
            file_sha(
                SOURCE_EVIDENCE
            ),
            bindings[
                "phase5_camera_imu_train_source_evidence"
            ][
                "file_sha256"
            ],
        )

        self.assertEqual(
            file_sha(
                SPLIT_MANIFEST
            ),
            bindings[
                "frozen_split_manifest"
            ][
                "file_sha256"
            ],
        )

    def test_08_camera_feature_contract_exact(self):
        camera = self.payload[
            "feature_contracts"
        ][
            "camera"
        ]

        self.assertEqual(
            [
                item[
                    "name"
                ]
                for item
                in camera[
                    "features"
                ]
            ],
            [
                "gray_mean_intensity_8bit",
                "gray_std_intensity_8bit",
                "gray_mean_abs_neighbor_difference_8bit",
            ],
        )

        self.assertFalse(
            camera[
                "temporal_aggregation"
            ]
        )

        self.assertFalse(
            camera[
                "normalization"
            ]
        )

        self.assertIsNone(
            camera[
                "threshold"
            ]
        )

    def test_09_imu_feature_contract_exact(self):
        imu = self.payload[
            "feature_contracts"
        ][
            "imu"
        ]

        self.assertEqual(
            imu[
                "streams"
            ],
            [
                "/camera/imu",
                "/handsfree/imu",
            ],
        )

        self.assertEqual(
            [
                item[
                    "name"
                ]
                for item
                in imu[
                    "features"
                ]
            ],
            [
                "angular_speed_norm_rad_s",
                "linear_acceleration_norm_m_s2",
            ],
        )

        self.assertTrue(
            imu[
                "orientation_excluded"
            ]
        )

        self.assertTrue(
            imu[
                "covariance_excluded"
            ]
        )

    def test_10_lidar_contract_preserved(self):
        lidar = self.payload[
            "feature_contracts"
        ][
            "lidar"
        ]

        self.assertEqual(
            lidar[
                "features_in_order"
            ],
            [
                "source_point_count",
                "target_point_count",
                "fixed_point_iterations",
                "final_correspondence_count",
                "final_nearest_neighbor_rmse_m",
            ],
        )

        self.assertTrue(
            lidar[
                "frozen_phase4_contract_unchanged"
            ]
        )

    def test_11_train_empirical_totals(self):
        empirical = self.payload[
            "empirical_train_validation"
        ]

        self.assertEqual(
            empirical[
                "train_trajectory_count"
            ],
            22,
        )

        self.assertEqual(
            empirical[
                "total_feature_records"
            ],
            2816957,
        )

        self.assertEqual(
            empirical[
                "total_source_serialized_payload_bytes"
            ],
            4320203720,
        )

    def test_12_stream_record_totals(self):
        empirical = self.payload[
            "empirical_train_validation"
        ]

        self.assertEqual(
            empirical[
                "camera_feature_records"
            ],
            107675,
        )

        self.assertEqual(
            empirical[
                "D435i_IMU_feature_records"
            ],
            1404805,
        )

        self.assertEqual(
            empirical[
                "HandsFree_IMU_feature_records"
            ],
            1304477,
        )

        self.assertEqual(
            empirical[
                "total_IMU_feature_records"
            ],
            2709282,
        )

    def test_13_empirical_integrity_validation_complete(self):
        empirical = self.payload[
            "empirical_train_validation"
        ]

        for key in (
            "all_feature_records_finite",
            "all_feature_file_hashes_verified",
            "all_JSONL_line_counts_verified",
            "phase5_source_message_totals_match",
            "phase5_source_payload_byte_totals_match",
        ):
            self.assertTrue(
                empirical[
                    key
                ]
            )

    def test_14_missing_camera_and_d435i_preserved(self):
        policy = self.payload[
            "missing_measurement_policy"
        ]

        self.assertEqual(
            policy[
                "missing_camera_train_trajectories"
            ],
            [
                "street_010",
                "street_09",
            ],
        )

        self.assertEqual(
            policy[
                "missing_D435i_IMU_train_trajectories"
            ],
            [
                "street_010",
                "street_09",
            ],
        )

        self.assertEqual(
            policy[
                "missing_HandsFree_IMU_train_trajectories"
            ],
            [],
        )

    def test_15_missing_is_not_zero_vector_or_imputation(self):
        policy = self.payload[
            "missing_measurement_policy"
        ]

        self.assertTrue(
            policy[
                "preserve_observed_absence"
            ]
        )

        self.assertFalse(
            policy[
                "missing_measurement_is_zero_feature_vector"
            ]
        )

        self.assertFalse(
            policy[
                "cross_modal_imputation"
            ]
        )

    def test_16_health_supervision_still_absent(self):
        health = self.payload[
            "health_supervision_state"
        ]

        self.assertEqual(
            health[
                "accepted_baseline_nominality_source_count"
            ],
            0,
        )

        self.assertEqual(
            health[
                "accepted_health_supervision_source_count"
            ],
            0,
        )

        self.assertEqual(
            health[
                "real_health_label_count"
            ],
            0,
        )

        self.assertFalse(
            health[
                "empirical_health_supervision_available"
            ]
        )

    def test_17_train_only_access(self):
        execution = self.payload[
            "execution_status"
        ]

        self.assertTrue(
            execution[
                "train_access"
            ]
        )

        self.assertFalse(
            execution[
                "validation_access"
            ]
        )

        self.assertFalse(
            execution[
                "confirmation_access"
            ]
        )

    def test_18_no_reference_or_cross_modal_alignment(self):
        execution = self.payload[
            "execution_status"
        ]

        self.assertFalse(
            execution[
                "reference_trajectory_access"
            ]
        )

        self.assertFalse(
            execution[
                "cross_modal_alignment_executed"
            ]
        )

    def test_19_no_supervised_feature_selection(self):
        self.assertFalse(
            self.payload[
                "execution_status"
            ][
                "supervised_feature_selection_executed"
            ]
        )

    def test_20_no_health_labels_or_training(self):
        execution = self.payload[
            "execution_status"
        ]

        self.assertFalse(
            execution[
                "health_label_assignment_executed"
            ]
        )

        self.assertFalse(
            execution[
                "model_training_executed"
            ]
        )

    def test_21_no_calibration_threshold_or_scoring(self):
        execution = self.payload[
            "execution_status"
        ]

        for key in (
            "probability_calibration_executed",
            "threshold_selection_executed",
            "ate_rpe_computed",
            "final_scoring_executed",
        ):
            self.assertFalse(
                execution[
                    key
                ]
            )

    def test_22_no_physical_timing_inference(self):
        resolution = self.payload[
            "scientific_resolution"
        ]

        self.assertFalse(
            resolution[
                "physical_capture_synchronization_inferred"
            ]
        )

        self.assertFalse(
            resolution[
                "bag_record_time_used_as_physical_capture_time"
            ]
        )

        self.assertFalse(
            resolution[
                "header_timestamp_presence_used_as_shared_clock_proof"
            ]
        )

    def test_23_se3_complete(self):
        transition = self.payload[
            "transition_policy"
        ]

        self.assertTrue(
            transition[
                "SE3_complete"
            ]
        )

        self.assertEqual(
            transition[
                "next_stage"
            ],
            "SE4",
        )

    def test_24_se4_training_still_blocked(self):
        transition = self.payload[
            "transition_policy"
        ]

        self.assertFalse(
            transition[
                "SE4_model_training_authorized"
            ]
        )

        self.assertTrue(
            transition[
                "SE4_blocked_pending_admissible_train_supervision"
            ]
        )

        self.assertTrue(
            transition[
                "SE4_requires_real_health_labels"
            ]
        )

    def test_25_validation_confirmation_se9_closed(self):
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

    def test_26_component_historical_gate_not_rewritten(self):
        closure = self.payload[
            "closure_interpretation"
        ]

        self.assertTrue(
            closure[
                "component_contract_historical_SE3_complete_false_is_preserved"
            ]
        )

        self.assertTrue(
            closure[
                "aggregate_freeze_manifest_is_authoritative_stage_closure"
            ]
        )

        component = json.loads(
            CONTRACT_CONFIG.read_text(
                encoding="utf-8"
            )
        )

        self.assertFalse(
            component[
                "empirical_status"
            ][
                "SE3_complete"
            ]
        )

    def test_27_freeze_does_not_authorize_physical_validation(self):
        self.assertFalse(
            self.payload[
                "closure_interpretation"
            ][
                "software_success_equals_physical_validation"
            ]
        )

    def test_28_project_state_has_se3_closure_section(self):
        text = PROJECT_STATE.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "## SE3 multimodal feature pipeline freeze V1",
            text,
        )

        self.assertIn(
            "2,816,957",
            text,
        )

        self.assertIn(
            "SE4 health-model training remains blocked",
            text,
        )


if __name__ == "__main__":
    unittest.main()
