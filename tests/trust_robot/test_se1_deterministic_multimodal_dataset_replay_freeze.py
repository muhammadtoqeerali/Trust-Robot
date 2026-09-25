from hashlib import sha256
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]

MANIFEST = (
    ROOT
    / "manifests"
    / "trust_robot_se1_deterministic_multimodal_dataset_replay_freeze_v1.json"
)

PROJECT_STATE = (
    ROOT
    / "docs"
    / "TRUST_ROBOT_PROJECT_STATE.md"
)


def file_sha256(path: Path) -> str:
    digest = sha256()

    with path.open("rb") as handle:
        for block in iter(
            lambda: handle.read(
                1024 * 1024
            ),
            b"",
        ):
            digest.update(block)

    return digest.hexdigest()


def content_sha256(payload) -> str:
    value = dict(payload)
    value.pop(
        "content_sha256",
        None,
    )

    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")

    return sha256(raw).hexdigest()


class TestSE1DeterministicMultimodalDatasetReplayFreeze(unittest.TestCase):

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
            "TRUST_ROBOT_SE1_DETERMINISTIC_MULTIMODAL_DATASET_REPLAY_FREEZE_V1",
        )

    def test_02_stage_identity(self):
        checkpoint = self.payload[
            "checkpoint_semantics"
        ]

        self.assertEqual(
            checkpoint["stage"],
            "SE1",
        )

        self.assertEqual(
            checkpoint["stage_name"],
            "deterministic_multimodal_dataset_replay",
        )

        self.assertEqual(
            checkpoint["track"],
            "software_evidence_completion",
        )

    def test_03_stage_complete(self):
        checkpoint = self.payload[
            "checkpoint_semantics"
        ]

        self.assertTrue(
            checkpoint[
                "train_replay_implemented"
            ]
        )

        self.assertTrue(
            checkpoint[
                "train_replay_executed"
            ]
        )

        self.assertTrue(
            checkpoint[
                "empirical_artifact_verification_passed"
            ]
        )

    def test_04_parent_frontier(self):
        parent = self.payload[
            "parent_frontier"
        ]

        self.assertEqual(
            parent["commit"],
            "4a0dbddfcc0bc610a79e91a60ae587cc6ad19976",
        )

        self.assertEqual(
            parent["tree"],
            "50fafbfcf82e3b4d89d6e32608f955b82d1e9d7a",
        )

    def test_05_source_bindings(self):
        bindings = self.payload[
            "source_bindings"
        ]

        self.assertEqual(
            bindings[
                "se0_freeze_manifest_sha256"
            ],
            "62838e41f0ffb47c02c517ac302a127b4cc2aba13ef86b7979c4d1e92bc20b33",
        )

        self.assertEqual(
            bindings[
                "split_manifest_sha256"
            ],
            "017a388ef1ce4ad30812669632a022ca37c084871bc949693fd9c0541014238f",
        )

    def test_06_implementation_hashes(self):
        expected = {
            "replay_module_sha256":
                (
                    ROOT
                    / "src"
                    / "trust_robot"
                    / "deterministic_multimodal_dataset_replay.py",
                    "0f73282a65367a22b49b38c5de0012172873f59d4744ac781edda218e3a25d28",
                ),

            "replay_run_module_sha256":
                (
                    ROOT
                    / "src"
                    / "trust_robot"
                    / "deterministic_multimodal_dataset_replay_run.py",
                    "599bbbf9626279d3841c5459ebca3d31a6c342bf72adfea236ff65e05b889ac5",
                ),

            "runner_sha256":
                (
                    ROOT
                    / "scripts"
                    / "trust_robot"
                    / "run_se1_deterministic_multimodal_dataset_replay_v1.py",
                    "2ea62d94f7cc44024b7d5c6c7d8c8e5c045367746ef59a7cbbc26e766a7e776a",
                ),

            "replay_tests_sha256":
                (
                    ROOT
                    / "tests"
                    / "trust_robot"
                    / "test_deterministic_multimodal_dataset_replay.py",
                    "b656d181e09ea0e457b5223584f75ed21711bb6c558214825f854c7bae263584",
                ),

            "replay_run_tests_sha256":
                (
                    ROOT
                    / "tests"
                    / "trust_robot"
                    / "test_deterministic_multimodal_dataset_replay_run.py",
                    "086711637f75465ed33e9c34df7bd5f7f41583c1f4b831a53cc9949d18247589",
                ),
        }

        frozen = self.payload[
            "implementation_artifacts"
        ]

        for key, (path, digest) in expected.items():
            self.assertEqual(
                frozen[key],
                digest,
            )

            self.assertEqual(
                file_sha256(path),
                digest,
            )

    def test_07_empirical_artifact_hashes(self):
        empirical = self.payload[
            "empirical_run"
        ]

        self.assertEqual(
            empirical[
                "candidate_contract_file_sha256"
            ],
            "866059a3f15a05b21f76acc9fafffa531aa460f55c4e4447a04ff2ad4b2ca53d",
        )

        self.assertEqual(
            empirical[
                "run_manifest_file_sha256"
            ],
            "3fcb3ce8a6698545be7b18774d3cf666bb3a8174e08321ca3a868ecd9f351d0f",
        )

        self.assertEqual(
            empirical[
                "success_file_sha256"
            ],
            "4ec6ec05aa51188d1aa2938815f3da2c4e817b2f046bcd1187010b9c2a6d9d07",
        )

    def test_08_empirical_content_hashes(self):
        empirical = self.payload[
            "empirical_run"
        ]

        self.assertEqual(
            empirical[
                "candidate_contract_content_sha256"
            ],
            "3766fe64942f0d0c41890a46bb2b3fffeb9a3a7ddb78329be127530f3c259c14",
        )

        self.assertEqual(
            empirical[
                "run_manifest_content_sha256"
            ],
            "1eeb1704a16631e9a47f4263a659ffcbdd6c8e3e6496f1d1f7924fb6559f7e37",
        )

        self.assertEqual(
            empirical[
                "aggregate_trajectory_record_sha256"
            ],
            "28812bc95af309184aaa3530d4fbfa5ebcc83713589f81b143047cf1e544be3d",
        )

    def test_09_train_population(self):
        empirical = self.payload[
            "empirical_run"
        ]

        self.assertEqual(
            empirical[
                "trajectory_count"
            ],
            22,
        )

        self.assertEqual(
            len(
                empirical[
                    "trajectory_order"
                ]
            ),
            22,
        )

    def test_10_execution_totals(self):
        empirical = self.payload[
            "empirical_run"
        ]

        self.assertEqual(
            empirical[
                "total_selected_replay_messages"
            ],
            2_907_971,
        )

        self.assertEqual(
            empirical[
                "total_selected_serialized_payload_bytes"
            ],
            103_450_808_700,
        )

    def test_11_atomic_completion(self):
        empirical = self.payload[
            "empirical_run"
        ]

        self.assertTrue(
            empirical[
                "atomic_final_output_present"
            ]
        )

        self.assertTrue(
            empirical[
                "partial_output_absent_after_success"
            ]
        )

        self.assertTrue(
            empirical[
                "success_marker_present"
            ]
        )

    def test_12_availability_population(self):
        availability = self.payload[
            "stream_availability_contract"
        ]

        self.assertEqual(
            availability[
                "full_four_stream_trajectory_count"
            ],
            20,
        )

        self.assertEqual(
            availability[
                "reduced_two_stream_trajectory_count"
            ],
            2,
        )

        self.assertEqual(
            availability[
                "reduced_two_stream_trajectories"
            ],
            [
                "street_010",
                "street_09",
            ],
        )

    def test_13_availability_not_health(self):
        availability = self.payload[
            "stream_availability_contract"
        ]

        self.assertFalse(
            availability[
                "availability_is_health_label"
            ]
        )

        self.assertFalse(
            availability[
                "missing_measurement_is_zero_feature_vector"
            ]
        )

        self.assertFalse(
            availability[
                "fabricated_missing_streams"
            ]
        )

    def test_14_reader_order_preserved(self):
        replay = self.payload[
            "replay_semantics"
        ]

        self.assertTrue(
            replay[
                "reader_emission_order_preserved"
            ]
        )

        self.assertFalse(
            replay[
                "timestamp_sort_performed"
            ]
        )

    def test_15_timestamps_remain_nonphysical_proof(self):
        replay = self.payload[
            "replay_semantics"
        ]

        self.assertTrue(
            replay[
                "bag_record_time_preserved_as_transport_provenance"
            ]
        )

        self.assertFalse(
            replay[
                "bag_record_time_proves_physical_capture_time"
            ]
        )

        self.assertFalse(
            replay[
                "header_stamp_proves_shared_physical_clock"
            ]
        )

    def test_16_no_synchronization_or_association(self):
        replay = self.payload[
            "replay_semantics"
        ]

        self.assertFalse(
            replay[
                "cross_stream_synchronization_performed"
            ]
        )

        self.assertFalse(
            replay[
                "fixed_time_offset_selected"
            ]
        )

        self.assertFalse(
            replay[
                "interpolation_performed"
            ]
        )

        self.assertFalse(
            replay[
                "reference_association_performed"
            ]
        )

    def test_17_partition_access(self):
        status = self.payload[
            "execution_status"
        ]

        self.assertTrue(
            status[
                "train_partition_opened"
            ]
        )

        self.assertFalse(
            status[
                "validation_partition_opened"
            ]
        )

        self.assertFalse(
            status[
                "confirmation_partition_opened"
            ]
        )

    def test_18_no_reference_or_health_execution(self):
        status = self.payload[
            "execution_status"
        ]

        for key in (
            "reference_data_read",
            "feature_selection_executed",
            "feature_extraction_executed",
            "health_supervision_executed",
            "health_label_assignment_executed",
            "health_probability_inference_executed",
            "model_training_executed",
            "probability_calibration_executed",
            "threshold_selection_executed",
        ):
            self.assertFalse(
                status[key]
            )

    def test_19_no_scoring(self):
        status = self.payload[
            "execution_status"
        ]

        self.assertFalse(
            status[
                "ate_rpe_computed"
            ]
        )

        self.assertFalse(
            status[
                "final_score_computed"
            ]
        )

    def test_20_health_supervision_boundary(self):
        boundary = self.payload[
            "health_supervision_boundary"
        ]

        self.assertFalse(
            boundary[
                "availability_is_health_label"
            ]
        )

        self.assertFalse(
            boundary[
                "clean_data_automatically_means_healthy"
            ]
        )

        self.assertFalse(
            boundary[
                "synthetic_corruption_identity_automatically_means_health_label"
            ]
        )

        self.assertFalse(
            boundary[
                "final_localization_error_may_define_health_label"
            ]
        )

        self.assertTrue(
            boundary[
                "SE2_required_before_health_model_training"
            ]
        )

    def test_21_se2_is_next_train_only_stage(self):
        gate = self.payload[
            "SE2_entry_gate"
        ]

        self.assertEqual(
            gate[
                "scope"
            ],
            "health_supervision_protocol",
        )

        self.assertTrue(
            gate[
                "SE2_may_proceed"
            ]
        )

        self.assertTrue(
            gate[
                "train_access_authorized"
            ]
        )

        self.assertFalse(
            gate[
                "validation_access_authorized"
            ]
        )

        self.assertFalse(
            gate[
                "confirmation_access_authorized"
            ]
        )

        self.assertFalse(
            gate[
                "model_training_authorized"
            ]
        )

    def test_22_se9_remains_closed(self):
        gate = self.payload[
            "SE9_opening_gate"
        ]

        self.assertEqual(
            gate[
                "status"
            ],
            "closed",
        )

        self.assertFalse(
            gate[
                "confirmation_execution_authorized"
            ]
        )

        self.assertFalse(
            gate[
                "confirmation_may_reopen_selection_after_results"
            ]
        )

    def test_23_project_state_contains_se1_freeze(self):
        text = PROJECT_STATE.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "## SE1 deterministic multimodal dataset replay freeze V1",
            text,
        )

        self.assertIn(
            "2,907,971 selected replay messages",
            text,
        )

        self.assertIn(
            "SE2 `health_supervision_protocol` is the next software-evidence stage.",
            text,
        )

    def test_24_manifest_content_sha256(self):
        self.assertEqual(
            self.payload[
                "content_sha256"
            ],
            content_sha256(
                self.payload
            ),
        )


if __name__ == "__main__":
    unittest.main()
