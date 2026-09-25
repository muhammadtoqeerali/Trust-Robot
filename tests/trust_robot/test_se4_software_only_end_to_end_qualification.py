from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from trust_robot.se4_software_only_end_to_end_qualification import (
    CAMERA_FEATURE_NAMES,
    EXPECTED_SPLIT_MANIFEST_SHA256,
    IMU_FEATURE_NAMES,
    QUALIFICATION_SCHEMA,
    REPRESENTATIVE_TRAJECTORY,
    RESOLUTION_SCHEMA,
    SE4SoftwareOnlyE2EQualificationError,
    build_qualification_resolution,
    canonical_json_bytes,
    content_sha256,
    file_sha256,
    run_synthetic_live_lane,
    validate_qualification_resolution,
)


ROOT = Path(__file__).resolve().parents[2]

CONFIG = (
    ROOT
    / "configs/trust_robot/"
    "se4_software_only_end_to_end_qualification_resolution_v1.json"
)

SPLIT = (
    ROOT
    / "manifests/"
    "m2dgr_trajectory_manifest_v1_split_freeze_v1.json"
)


class SE4SoftwareOnlyEndToEndQualificationTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(
        cls,
    ):
        cls.payload = json.loads(
            CONFIG.read_text(
                encoding="utf-8"
            )
        )

    def test_01_resolution_schema(self):
        self.assertEqual(
            self.payload[
                "schema"
            ],
            RESOLUTION_SCHEMA,
        )

    def test_02_resolution_content_digest(self):
        self.assertEqual(
            self.payload[
                "content_sha256"
            ],
            content_sha256(
                self.payload
            ),
        )

    def test_03_builder_matches_config(self):
        self.assertEqual(
            self.payload,
            build_qualification_resolution(),
        )

    def test_04_validator_accepts_config(self):
        self.assertIs(
            validate_qualification_resolution(
                self.payload
            ),
            self.payload,
        )

    def test_05_software_only(self):
        self.assertTrue(
            self.payload[
                "qualification_scope"
            ][
                "software_only"
            ]
        )

    def test_06_real_data_lane_required(self):
        self.assertTrue(
            self.payload[
                "qualification_scope"
            ][
                "representative_real_data_lane"
            ]
        )

    def test_07_synthetic_live_lane_required(self):
        self.assertTrue(
            self.payload[
                "qualification_scope"
            ][
                "synthetic_live_software_lane"
            ]
        )

    def test_08_no_real_network_allowed(self):
        self.assertFalse(
            self.payload[
                "qualification_scope"
            ][
                "real_network_IO_allowed"
            ]
        )

    def test_09_no_real_sensor_contact_allowed(self):
        self.assertFalse(
            self.payload[
                "qualification_scope"
            ][
                "real_sensor_contact_allowed"
            ]
        )

    def test_10_representative_trajectory(self):
        self.assertEqual(
            REPRESENTATIVE_TRAJECTORY,
            "room_02",
        )

    def test_11_representative_not_sampling_claim(self):
        self.assertFalse(
            self.payload[
                "qualification_scope"
            ][
                "representative_selection_is_scientific_sampling_claim"
            ]
        )

    def test_12_split_manifest_hash_exact(self):
        self.assertEqual(
            file_sha256(
                SPLIT
            ),
            EXPECTED_SPLIT_MANIFEST_SHA256,
        )

    def test_13_camera_feature_names_exact(self):
        self.assertEqual(
            CAMERA_FEATURE_NAMES,
            (
                "gray_mean_intensity_8bit",
                "gray_std_intensity_8bit",
                "gray_mean_abs_neighbor_difference_8bit",
            ),
        )

    def test_14_imu_feature_names_exact(self):
        self.assertEqual(
            IMU_FEATURE_NAMES,
            (
                "angular_speed_norm_rad_s",
                "linear_acceleration_norm_m_s2",
            ),
        )

    def test_15_lane_A_uses_SE1(self):
        self.assertTrue(
            self.payload[
                "lane_A_contract"
            ][
                "uses_SE1_deterministic_replay"
            ]
        )

    def test_16_lane_A_replay_twice(self):
        self.assertTrue(
            self.payload[
                "lane_A_contract"
            ][
                "replay_is_run_twice_for_bounded_digest_comparison"
            ]
        )

    def test_17_lane_A_real_camera_features(self):
        self.assertTrue(
            self.payload[
                "lane_A_contract"
            ][
                "real_camera_feature_extraction"
            ]
        )

    def test_18_lane_A_real_imu_features(self):
        lane = self.payload[
            "lane_A_contract"
        ]

        self.assertTrue(
            lane[
                "real_D435i_IMU_feature_extraction"
            ]
        )

        self.assertTrue(
            lane[
                "real_HandsFree_IMU_feature_extraction"
            ]
        )

    def test_19_lane_A_lidar_replay(self):
        self.assertTrue(
            self.payload[
                "lane_A_contract"
            ][
                "real_LiDAR_replay_observation"
            ]
        )

    def test_20_lane_A_does_not_rerun_full_lidar_registration(self):
        self.assertFalse(
            self.payload[
                "lane_A_contract"
            ][
                "reruns_full_SE3_LiDAR_registration_pipeline"
            ]
        )

    def test_21_lane_A_guards(self):
        lane = self.payload[
            "lane_A_contract"
        ]

        self.assertTrue(
            lane[
                "invokes_SE2_training_guard"
            ]
        )

        self.assertTrue(
            lane[
                "invokes_SE4_training_guard"
            ]
        )

        self.assertTrue(
            lane[
                "invokes_SE5_entry_guard"
            ]
        )

    def test_22_lane_B_documentation_networks(self):
        self.assertTrue(
            self.payload[
                "lane_B_contract"
            ][
                "uses_synthetic_documentation_only_network_values"
            ]
        )

    def test_23_lane_B_authorization_not_real(self):
        lane = self.payload[
            "lane_B_contract"
        ]

        self.assertTrue(
            lane[
                "uses_synthetic_authorization_record"
            ]
        )

        self.assertFalse(
            lane[
                "authorization_record_is_real_grounded_authorization"
            ]
        )

    def test_24_lane_B_uses_V2_and_authorization(self):
        lane = self.payload[
            "lane_B_contract"
        ]

        self.assertTrue(
            lane[
                "uses_V2_binding_builder"
            ]
        )

        self.assertTrue(
            lane[
                "uses_hash_bound_authorization_builder"
            ]
        )

    def test_25_lane_B_uses_file_runner(self):
        lane = self.payload[
            "lane_B_contract"
        ]

        self.assertTrue(
            lane[
                "uses_file_input_validator"
            ]
        )

        self.assertTrue(
            lane[
                "uses_file_driven_dispatch_gate"
            ]
        )

    def test_26_lane_B_injected_components(self):
        lane = self.payload[
            "lane_B_contract"
        ]

        self.assertTrue(
            lane[
                "uses_injected_composite_orchestrator"
            ]
        )

        self.assertTrue(
            lane[
                "uses_synthetic_UDP_component"
            ]
        )

        self.assertTrue(
            lane[
                "uses_synthetic_HTTP_component"
            ]
        )

    def test_27_lane_B_no_real_IO(self):
        lane = self.payload[
            "lane_B_contract"
        ]

        self.assertFalse(
            lane[
                "real_network_IO"
            ]
        )

        self.assertFalse(
            lane[
                "real_sensor_contact"
            ]
        )

    def test_28_synthetic_live_lane_executes_end_to_end(self):
        with TemporaryDirectory() as temp:
            root = (
                Path(
                    temp
                )
                / "lane"
            )

            result = run_synthetic_live_lane(
                working_root=
                    root
            )

            self.assertEqual(
                result[
                    "execution_order"
                ],
                [
                    "UDP",
                    "HTTP:identity",
                    "HTTP:status",
                    "HTTP:diagnostic",
                ],
            )

    def test_29_synthetic_lane_no_real_IO(self):
        with TemporaryDirectory() as temp:
            result = run_synthetic_live_lane(
                working_root=
                    Path(
                        temp
                    )
                    / "lane"
            )

            self.assertFalse(
                result[
                    "real_network_IO_executed"
                ]
            )

            self.assertFalse(
                result[
                    "real_sensor_contact"
                ]
            )

    def test_30_synthetic_lane_no_real_binding_or_auth(self):
        with TemporaryDirectory() as temp:
            result = run_synthetic_live_lane(
                working_root=
                    Path(
                        temp
                    )
                    / "lane"
            )

            self.assertFalse(
                result[
                    "real_runtime_binding_created"
                ]
            )

            self.assertFalse(
                result[
                    "grounded_execution_authorization_created"
                ]
            )

    def test_31_synthetic_lane_no_health_label(self):
        with TemporaryDirectory() as temp:
            result = run_synthetic_live_lane(
                working_root=
                    Path(
                        temp
                    )
                    / "lane"
            )

            self.assertFalse(
                result[
                    "health_supervision_source_accepted"
                ]
            )

            self.assertFalse(
                result[
                    "health_label_generated"
                ]
            )

    def test_32_science_counts_zero(self):
        science = self.payload[
            "scientific_boundary"
        ]

        self.assertEqual(
            science[
                "real_runtime_binding_count"
            ],
            0,
        )

        self.assertEqual(
            science[
                "real_execution_authorization_count"
            ],
            0,
        )

        self.assertEqual(
            science[
                "grounded_authorization_record_count"
            ],
            0,
        )

        self.assertEqual(
            science[
                "accepted_health_supervision_source_count"
            ],
            0,
        )

        self.assertEqual(
            science[
                "real_health_label_count"
            ],
            0,
        )

    def test_33_interval_binding_false(self):
        self.assertFalse(
            self.payload[
                "scientific_boundary"
            ][
                "interval_binding_established"
            ]
        )

    def test_34_SE4_SE5_closed(self):
        science = self.payload[
            "scientific_boundary"
        ]

        self.assertFalse(
            science[
                "SE4_complete"
            ]
        )

        self.assertFalse(
            science[
                "SE4_training_authorized"
            ]
        )

        self.assertFalse(
            science[
                "SE5_may_proceed"
            ]
        )

    def test_35_validation_confirmation_closed(self):
        science = self.payload[
            "scientific_boundary"
        ]

        self.assertFalse(
            science[
                "validation_open"
            ]
        )

        self.assertFalse(
            science[
                "confirmation_open"
            ]
        )

    def test_36_no_ATE_RPE(self):
        self.assertFalse(
            self.payload[
                "scientific_boundary"
            ][
                "ATE_RPE_computed"
            ]
        )

    def test_37_demonstrates_stack_integration(self):
        self.assertTrue(
            self.payload[
                "qualification_interpretation"
            ][
                "demonstrates_current_software_stack_integration"
            ]
        )

    def test_38_not_real_sensor_proof(self):
        interpretation = self.payload[
            "qualification_interpretation"
        ]

        self.assertFalse(
            interpretation[
                "proves_real_sensor_system"
            ]
        )

        self.assertFalse(
            interpretation[
                "replaces_future_hardware_validation"
            ]
        )

    def test_39_not_health_model_proof(self):
        interpretation = self.payload[
            "qualification_interpretation"
        ]

        self.assertFalse(
            interpretation[
                "proves_health_model"
            ]
        )

        self.assertFalse(
            interpretation[
                "proves_health_labels"
            ]
        )

    def test_40_canonical_json_deterministic(self):
        first = {
            "b":
                2,

            "a":
                1,
        }

        second = {
            "a":
                1,

            "b":
                2,
        }

        self.assertEqual(
            sha256(
                canonical_json_bytes(
                    first
                )
            ).hexdigest(),
            sha256(
                canonical_json_bytes(
                    second
                )
            ).hexdigest(),
        )


    def test_41_stream_id_is_ros_topic(self):
        from trust_robot.se4_software_only_end_to_end_qualification import (
            _topic_to_stream_id,
        )

        manifest = json.loads(
            SPLIT.read_text(
                encoding="utf-8"
            )
        )

        record = next(
            record
            for record
            in manifest[
                "records"
            ]
            if record[
                "trajectory_id"
            ] == "room_02"
        )

        mapping = _topic_to_stream_id(
            record
        )

        self.assertEqual(
            mapping,
            {
                "/camera/color/image_raw/compressed":
                    "/camera/color/image_raw/compressed",

                "/camera/imu":
                    "/camera/imu",

                "/handsfree/imu":
                    "/handsfree/imu",

                "/velodyne_points":
                    "/velodyne_points",
            },
        )

    def test_42_replay_envelope_uses_source_stream_id(self):
        from types import SimpleNamespace

        from trust_robot.se4_software_only_end_to_end_qualification import (
            _stream_id_from_envelope,
        )

        envelope = SimpleNamespace(
            source_stream_id=
                "/camera/imu"
        )

        self.assertEqual(
            _stream_id_from_envelope(
                envelope
            ),
            "/camera/imu",
        )


    def test_43_camera_imu_is_not_camera_image_branch(self):
        module_path = (
            ROOT
            / "src/trust_robot/"
            "se4_software_only_end_to_end_qualification.py"
        )

        text = module_path.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            'if stream_id == "/camera/color/image_raw/compressed":',
            text,
        )

        self.assertIn(
            '"/camera/imu",',
            text,
        )

        self.assertNotIn(
            'if "camera" in lower:',
            text,
        )

    def test_44_handsfree_imu_uses_imu_branch(self):
        module_path = (
            ROOT
            / "src/trust_robot/"
            "se4_software_only_end_to_end_qualification.py"
        )

        text = module_path.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            '"/handsfree/imu",',
            text,
        )

        self.assertIn(
            'elif stream_id in {',
            text,
        )

    def test_45_velodyne_uses_exact_lidar_branch(self):
        module_path = (
            ROOT
            / "src/trust_robot/"
            "se4_software_only_end_to_end_qualification.py"
        )

        text = module_path.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            'elif stream_id == "/velodyne_points":',
            text,
        )

        self.assertNotIn(
            'elif "lidar" in lower:',
            text,
        )


    def test_46_wanted_streams_include_velodyne(self):
        module_path = (
            ROOT
            / "src/trust_robot/"
            "se4_software_only_end_to_end_qualification.py"
        )

        text = module_path.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "wanted_streams = set(",
            text,
        )

        self.assertIn(
            "topic_to_stream.values()",
            text,
        )

    def test_47_lidar_summary_uses_velodyne_stream_id(self):
        module_path = (
            ROOT
            / "src/trust_robot/"
            "se4_software_only_end_to_end_qualification.py"
        )

        text = module_path.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            '"LiDAR_real_replay_observed":',
            text,
        )

        self.assertIn(
            '"/velodyne_points"',
            text,
        )

        self.assertNotIn(
            '"lidar" in stream_id.lower()',
            text,
        )

    def test_48_imu_summary_requires_both_imu_streams(self):
        module_path = (
            ROOT
            / "src/trust_robot/"
            "se4_software_only_end_to_end_qualification.py"
        )

        text = module_path.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            '"/camera/imu"',
            text,
        )

        self.assertIn(
            '"/handsfree/imu"',
            text,
        )


if __name__ == "__main__":
    unittest.main()
