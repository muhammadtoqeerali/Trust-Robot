from hashlib import sha256
from pathlib import Path
import json
import math
import unittest


ROOT = Path(__file__).resolve().parents[2]

FREEZE = (
    ROOT
    / "manifests/"
    "trust_robot_se4_software_only_end_to_end_qualification_freeze_v1.json"
)

MODULE = (
    ROOT
    / "src/trust_robot/"
    "se4_software_only_end_to_end_qualification.py"
)

RUNNER = (
    ROOT
    / "scripts/trust_robot/"
    "run_se4_software_only_end_to_end_qualification_v1.py"
)

CONFIG = (
    ROOT
    / "configs/trust_robot/"
    "se4_software_only_end_to_end_qualification_resolution_v1.json"
)

IMPLEMENTATION_TEST = (
    ROOT
    / "tests/trust_robot/"
    "test_se4_software_only_end_to_end_qualification.py"
)

PROJECT_STATE = (
    ROOT
    / "docs/TRUST_ROBOT_PROJECT_STATE.md"
)

EXPECTED_FREEZE_SHA = "0017b8036c4fbf0627eb93bad34a5070de02082707959348dff3be8a7d81a2d1"
EXPECTED_CONTENT_SHA = "0f099e5f7afe04d45c9ac4c1d58404e34f12f03991614ee9bcab25b2b85e69f1"


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


class SE4SoftwareOnlyEndToEndQualificationFreezeTests(
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

    def test_02_freeze_content_sha(self):
        self.assertEqual(
            self.payload[
                "content_sha256"
            ],
            EXPECTED_CONTENT_SHA,
        )

        self.assertEqual(
            canonical_sha(
                self.payload
            ),
            EXPECTED_CONTENT_SHA,
        )

    def test_03_schema(self):
        self.assertEqual(
            self.payload[
                "schema"
            ],
            "TRUST_ROBOT_SE4_SOFTWARE_ONLY_END_TO_END_QUALIFICATION_FREEZE_V1",
        )

    def test_04_parent_frontier(self):
        self.assertEqual(
            self.payload[
                "parent_frontier"
            ][
                "commit"
            ],
            "1ff236023c4c5ca717d8fa7655dc4a3a775db8e9",
        )

    def test_05_implementation_hashes(self):
        implementation = self.payload[
            "implementation"
        ]

        self.assertEqual(
            file_sha(MODULE),
            implementation[
                "module_sha256"
            ],
        )

        self.assertEqual(
            file_sha(RUNNER),
            implementation[
                "runner_sha256"
            ],
        )

        self.assertEqual(
            file_sha(CONFIG),
            implementation[
                "config_sha256"
            ],
        )

        self.assertEqual(
            file_sha(IMPLEMENTATION_TEST),
            implementation[
                "test_sha256"
            ],
        )

    def test_06_implementation_test_count(self):
        self.assertEqual(
            self.payload[
                "implementation"
            ][
                "implementation_test_count"
            ],
            48,
        )

    def test_07_real_data_lane_is_TRAIN(self):
        real = self.payload[
            "real_data_lane"
        ]

        self.assertEqual(
            real["split"],
            "TRAIN",
        )

        self.assertEqual(
            real[
                "representative_trajectory"
            ],
            "room_02",
        )

    def test_08_representative_is_not_sampling_claim(self):
        self.assertFalse(
            self.payload[
                "real_data_lane"
            ][
                "representative_selection_is_scientific_sampling_claim"
            ]
        )

    def test_09_bag_size(self):
        self.assertEqual(
            self.payload[
                "real_data_lane"
            ][
                "bag_file_size_bytes"
            ],
            15162620712,
        )

    def test_10_replay_count(self):
        self.assertEqual(
            self.payload[
                "real_data_lane"
            ][
                "bounded_replay_message_count"
            ],
            45,
        )

    def test_11_replay_digest(self):
        self.assertEqual(
            self.payload[
                "real_data_lane"
            ][
                "bounded_replay_digest_sha256"
            ],
            "68cda190573e34204567407a7783b7ba028696f9d21d10e72a149c7508e2904e",
        )

    def test_12_replay_deterministic(self):
        self.assertTrue(
            self.payload[
                "real_data_lane"
            ][
                "bounded_replay_deterministic"
            ]
        )

    def test_13_four_real_streams(self):
        self.assertEqual(
            set(
                self.payload[
                    "real_data_lane"
                ][
                    "real_stream_ids"
                ]
            ),
            {
                "/camera/color/image_raw/compressed",
                "/camera/imu",
                "/handsfree/imu",
                "/velodyne_points",
            },
        )

    def test_14_camera_features(self):
        camera = self.payload[
            "real_feature_observations"
        ][
            "camera"
        ]

        self.assertEqual(
            camera[
                "feature_names"
            ],
            [
                "gray_mean_intensity_8bit",
                "gray_std_intensity_8bit",
                "gray_mean_abs_neighbor_difference_8bit",
            ],
        )

        self.assertTrue(
            math.isclose(
                camera[
                    "feature_values"
                ][0],
                118.984404296875,
                rel_tol=0.0,
                abs_tol=1e-12,
            )
        )

    def test_15_camera_imu_features(self):
        values = self.payload[
            "real_feature_observations"
        ][
            "camera_imu"
        ][
            "feature_values"
        ]

        self.assertTrue(
            math.isclose(
                values[0],
                0.0034743013743035868,
                rel_tol=0.0,
                abs_tol=1e-12,
            )
        )

        self.assertTrue(
            math.isclose(
                values[1],
                9.76639145189828,
                rel_tol=0.0,
                abs_tol=1e-12,
            )
        )

    def test_16_handsfree_imu_features(self):
        values = self.payload[
            "real_feature_observations"
        ][
            "handsfree_imu"
        ][
            "feature_values"
        ]

        self.assertTrue(
            math.isclose(
                values[0],
                0.0021029424511825835,
                rel_tol=0.0,
                abs_tol=1e-12,
            )
        )

        self.assertTrue(
            math.isclose(
                values[1],
                10.04871765839132,
                rel_tol=0.0,
                abs_tol=1e-12,
            )
        )

    def test_17_lidar_payload(self):
        lidar = self.payload[
            "real_feature_observations"
        ][
            "velodyne"
        ]

        self.assertEqual(
            lidar[
                "serialized_payload_bytes"
            ],
            1121202,
        )

        self.assertEqual(
            lidar[
                "serialized_payload_sha256"
            ],
            "adc13ce9db806b74574053e9697e33edf85286c9be9767aa345c0aada915e0cd",
        )

    def test_18_lidar_contract_not_rerun(self):
        lidar = self.payload[
            "real_feature_observations"
        ][
            "velodyne"
        ]

        self.assertEqual(
            lidar[
                "frozen_SE3_lidar_feature_contract"
            ],
            [
                "source_point_count",
                "target_point_count",
                "fixed_point_iterations",
                "final_correspondence_count",
                "final_nearest_neighbor_rmse_m",
            ],
        )

        self.assertFalse(
            lidar[
                "full_lidar_registration_rerun"
            ]
        )

    def test_19_live_execution_order(self):
        self.assertEqual(
            self.payload[
                "synthetic_live_lane"
            ][
                "execution_order"
            ],
            [
                "UDP",
                "HTTP:identity",
                "HTTP:status",
                "HTTP:diagnostic",
            ],
        )

    def test_20_live_lane_no_real_IO(self):
        live = self.payload[
            "synthetic_live_lane"
        ]

        self.assertFalse(
            live[
                "real_network_IO_executed"
            ]
        )

        self.assertFalse(
            live[
                "real_sensor_contact"
            ]
        )

    def test_21_synthetic_authorization_not_grounded(self):
        self.assertFalse(
            self.payload[
                "synthetic_live_lane"
            ][
                "authorization_record_is_grounded_real_authorization"
            ]
        )

    def test_22_run_hash_not_replay_requirement(self):
        live = self.payload[
            "synthetic_live_lane"
        ]

        self.assertFalse(
            live[
                "run_specific_hash_is_replay_stability_requirement"
            ]
        )

        receipt = self.payload[
            "observed_qualification_receipt"
        ]

        self.assertFalse(
            receipt[
                "receipt_hashes_are_required_to_repeat_across_future_runs"
            ]
        )

    def test_23_training_guards_blocked(self):
        guards = self.payload[
            "training_and_stage_guards"
        ]

        self.assertTrue(
            guards[
                "SE2_health_model_training_blocked"
            ]
        )

        self.assertTrue(
            guards[
                "SE4_training_execution_blocked"
            ]
        )

        self.assertTrue(
            guards[
                "SE5_entry_blocked"
            ]
        )

    def test_24_no_health_label(self):
        self.assertFalse(
            self.payload[
                "training_and_stage_guards"
            ][
                "health_label_generated"
            ]
        )

    def test_25_real_counts_zero(self):
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

    def test_26_sources_and_labels_zero(self):
        science = self.payload[
            "scientific_boundary"
        ]

        self.assertEqual(
            science[
                "accepted_baseline_nominality_source_count"
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

    def test_27_no_interval_reference_or_scoring(self):
        science = self.payload[
            "scientific_boundary"
        ]

        self.assertFalse(
            science[
                "interval_binding_established"
            ]
        )

        self.assertFalse(
            science[
                "reference_trajectory_accessed"
            ]
        )

        self.assertFalse(
            science[
                "ATE_RPE_computed"
            ]
        )

    def test_28_SE4_SE5_closed(self):
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

    def test_29_qualification_conclusion(self):
        conclusion = self.payload[
            "qualification_conclusion"
        ]

        self.assertTrue(
            conclusion[
                "current_implementable_software_stack_operates_end_to_end"
            ]
        )

        self.assertTrue(
            conclusion[
                "software_level_qualification_passed"
            ]
        )

        self.assertFalse(
            conclusion[
                "physical_or_health_evidence_fabricated"
            ]
        )

    def test_30_project_state_records_freeze(self):
        text = PROJECT_STATE.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "## SE4 software-only end-to-end qualification freeze V1",
            text,
        )

        self.assertIn(
            "current implementable software stack operates end-to-end",
            text,
        )


if __name__ == "__main__":
    unittest.main()
