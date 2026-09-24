import copy
from hashlib import sha256
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]

MANIFEST = (
    ROOT
    / "manifests"
    / "trust_robot_se0_software_evidence_completion_plan_freeze_v1.json"
)


class TestSE0SoftwareEvidenceCompletionPlanFreeze(unittest.TestCase):

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
            "TRUST_ROBOT_SE0_SOFTWARE_EVIDENCE_COMPLETION_PLAN_FREEZE_V1",
        )

    def test_02_stage(self):
        boundary = self.payload[
            "checkpoint_semantics"
        ]

        self.assertEqual(
            boundary[
                "stage"
            ],
            "SE0",
        )

        self.assertEqual(
            boundary[
                "stage_name"
            ],
            "scientific_readiness_and_plan_freeze",
        )

    def test_03_plan_implemented(self):
        self.assertTrue(
            self.payload[
                "checkpoint_semantics"
            ][
                "software_evidence_completion_plan_implemented"
            ]
        )

    def test_04_actual_schema_validated(self):
        self.assertTrue(
            self.payload[
                "checkpoint_semantics"
            ][
                "actual_plan_schema_validated"
            ]
        )

    def test_05_stage_count(self):
        self.assertEqual(
            self.payload[
                "checkpoint_semantics"
            ][
                "stage_count"
            ],
            11,
        )

    def test_06_stage_order(self):
        self.assertEqual(
            self.payload[
                "stage_order"
            ],
            [
                "SE0",
                "SE1",
                "SE2",
                "SE3",
                "SE4",
                "SE5",
                "SE6",
                "SE7",
                "SE8",
                "SE9",
                "SE10",
            ],
        )

    def test_07_actual_stage_names(self):
        self.assertEqual(
            self.payload[
                "stage_names"
            ][0],
            "scientific_readiness_and_plan_freeze",
        )

        self.assertEqual(
            self.payload[
                "stage_names"
            ][5],
            "validation_selection_and_probability_calibration",
        )

    def test_08_split_counts(self):
        partition = self.payload[
            "partition_contract"
        ]

        self.assertEqual(
            partition[
                "train_count"
            ],
            22,
        )

        self.assertEqual(
            partition[
                "validation_count"
            ],
            7,
        )

        self.assertEqual(
            partition[
                "confirmation_count"
            ],
            7,
        )

    def test_09_split_roles(self):
        partition = self.payload[
            "partition_contract"
        ]

        self.assertEqual(
            partition[
                "train_role"
            ],
            "train",
        )

        self.assertEqual(
            partition[
                "validation_role"
            ],
            "validation_calibration",
        )

        self.assertEqual(
            partition[
                "confirmation_role"
            ],
            "confirmation_test",
        )

    def test_10_no_partition_overlap(self):
        self.assertFalse(
            self.payload[
                "partition_contract"
            ][
                "partition_overlap"
            ]
        )

    def test_11_derivatives_stay_with_partition(self):
        self.assertTrue(
            self.payload[
                "partition_contract"
            ][
                "base_trajectory_derivatives_remain_with_base_partition"
            ]
        )

    def test_12_seeds_not_reused_across_partitions(self):
        self.assertFalse(
            self.payload[
                "partition_contract"
            ][
                "corruption_seeds_may_be_reused_across_partitions"
            ]
        )

    def test_13_se1_scope(self):
        self.assertEqual(
            self.payload[
                "SE1_entry_gate"
            ][
                "scope"
            ],
            "deterministic_multimodal_dataset_replay",
        )

    def test_14_se1_train_only(self):
        gate = self.payload[
            "SE1_entry_gate"
        ]

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

    def test_15_se1_no_training_or_selection(self):
        gate = self.payload[
            "SE1_entry_gate"
        ]

        self.assertFalse(
            gate[
                "model_training_authorized"
            ]
        )

        self.assertFalse(
            gate[
                "feature_selection_authorized"
            ]
        )

        self.assertFalse(
            gate[
                "threshold_selection_authorized"
            ]
        )

        self.assertFalse(
            gate[
                "probability_calibration_authorized"
            ]
        )

    def test_16_se1_no_scoring(self):
        gate = self.payload[
            "SE1_entry_gate"
        ]

        self.assertFalse(
            gate[
                "ate_rpe_authorized"
            ]
        )

        self.assertFalse(
            gate[
                "final_scoring_authorized"
            ]
        )

    def test_17_real_train_foundations_present(self):
        gate = self.payload[
            "SE1_entry_gate"
        ]

        self.assertTrue(
            gate[
                "phase4_real_lidar_diagnostics_present"
            ]
        )

        self.assertTrue(
            gate[
                "phase5_real_camera_imu_ingestion_present"
            ]
        )

    def test_18_confirmation_not_for_selection(self):
        selection = self.payload[
            "selection_contract"
        ]

        self.assertFalse(
            selection[
                "confirmation_for_selection"
            ]
        )

        for key in (
            "confirmation_may_select_model",
            "confirmation_may_select_features",
            "confirmation_may_select_thresholds",
            "confirmation_may_select_calibration",
            "confirmation_may_select_fault_severity",
            "confirmation_may_select_attack_budget",
            "confirmation_may_select_alignment",
            "confirmation_may_select_association",
            "confirmation_may_select_interpolation",
            "confirmation_may_select_evaluation_interval",
            "confirmation_may_select_metric_operating_choices",
        ):
            self.assertFalse(
                selection[
                    key
                ]
            )

    def test_19_health_labels_not_assumed(self):
        boundary = self.payload[
            "health_supervision_boundary"
        ]

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

    def test_20_se2_required_before_training(self):
        self.assertTrue(
            self.payload[
                "health_supervision_boundary"
            ][
                "SE2_required_before_health_model_training"
            ]
        )

    def test_21_se9_closed(self):
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

    def test_22_no_empirical_execution(self):
        self.assertEqual(
            set(
                self.payload[
                    "execution_status"
                ].values()
            ),
            {
                False,
            },
        )

    def test_23_hardware_and_next_stage_boundary(self):
        hardware = self.payload[
            "hardware_boundary"
        ]

        self.assertFalse(
            hardware[
                "software_evidence_track_requires_hardware_to_begin"
            ]
        )

        self.assertFalse(
            hardware[
                "software_success_equals_physical_hardware_validation"
            ]
        )

        next_stage = self.payload[
            "next_stage_policy"
        ]

        self.assertEqual(
            next_stage[
                "next_stage"
            ],
            "SE1",
        )

        self.assertTrue(
            next_stage[
                "SE1_may_proceed"
            ]
        )

        self.assertTrue(
            next_stage[
                "SE1_may_read_train_partition"
            ]
        )

        self.assertFalse(
            next_stage[
                "SE1_may_read_validation_partition"
            ]
        )

        self.assertFalse(
            next_stage[
                "SE1_may_read_confirmation_partition"
            ]
        )

        self.assertFalse(
            next_stage[
                "SE1_may_train_health_model"
            ]
        )

    def test_24_content_digest(self):
        value = copy.deepcopy(
            self.payload
        )

        stored = value.pop(
            "content_sha256"
        )

        canonical = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode(
            "utf-8"
        )

        self.assertEqual(
            stored,
            sha256(
                canonical
            ).hexdigest(),
        )


if __name__ == "__main__":
    unittest.main()
