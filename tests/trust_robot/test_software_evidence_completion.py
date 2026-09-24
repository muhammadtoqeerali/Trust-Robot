import copy
import json
from pathlib import Path
import unittest

from trust_robot.software_evidence_completion import (
    CONFIRMATION_TRAJECTORIES,
    EvidencePlanError,
    STAGE_ORDER,
    TRAIN_TRAJECTORIES,
    VALIDATION_TRAJECTORIES,
    assert_ate_rpe_authorized,
    assert_confirmation_execution_authorized,
    assert_confirmation_selection_forbidden,
    stage_definition,
    stage_ids,
    validate_disjoint_split,
    validate_plan_manifest,
)


ROOT = Path(__file__).resolve().parents[2]

CONFIG = (
    ROOT
    / "configs"
    / "trust_robot"
    / "software_evidence_completion_plan_v1.json"
)


class TestSoftwareEvidenceCompletionPlan(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(
            CONFIG.read_text(
                encoding="utf-8"
            )
        )

    def test_01_schema(self):
        self.assertEqual(
            self.payload["schema"],
            "TRUST_ROBOT_SOFTWARE_EVIDENCE_COMPLETION_PLAN_V1",
        )

    def test_02_track(self):
        self.assertEqual(
            self.payload["track"],
            "software_evidence_completion",
        )

    def test_03_baseline_tests(self):
        self.assertEqual(
            self.payload[
                "baseline"
            ][
                "trust_robot_test_count"
            ],
            1400,
        )

    def test_04_phase_architecture_frozen(self):
        self.assertTrue(
            self.payload[
                "baseline"
            ][
                "phase5_through_phase14_software_architecture_frozen"
            ]
        )

    def test_05_train_count(self):
        self.assertEqual(
            len(TRAIN_TRAJECTORIES),
            22,
        )

    def test_06_validation_count(self):
        self.assertEqual(
            len(VALIDATION_TRAJECTORIES),
            7,
        )

    def test_07_confirmation_count(self):
        self.assertEqual(
            len(CONFIRMATION_TRAJECTORIES),
            7,
        )

    def test_08_split_disjoint(self):
        validate_disjoint_split()

    def test_09_total_trajectory_count(self):
        self.assertEqual(
            len(
                set(TRAIN_TRAJECTORIES)
                | set(VALIDATION_TRAJECTORIES)
                | set(CONFIRMATION_TRAJECTORIES)
            ),
            36,
        )

    def test_10_derivatives_stay_with_base(self):
        self.assertTrue(
            self.payload[
                "partition_contract"
            ][
                "all_clean_and_corrupt_derivatives_stay_with_base_trajectory"
            ]
        )

    def test_11_no_cross_partition_seed_reuse(self):
        self.assertFalse(
            self.payload[
                "partition_contract"
            ][
                "corruption_seeds_may_be_reused_across_partitions"
            ]
        )

    def test_12_reference_independence(self):
        self.assertFalse(
            self.payload[
                "partition_contract"
            ][
                "reference_stream_may_be_estimator_input_when_used_as_ground_truth_without_independent_instance"
            ]
        )

    def test_13_train_for_construction(self):
        self.assertTrue(
            self.payload[
                "selection_contract"
            ][
                "train_for_model_construction"
            ]
        )

    def test_14_validation_authorized_selection_only(self):
        self.assertTrue(
            self.payload[
                "selection_contract"
            ][
                "validation_for_authorized_selection_only"
            ]
        )

    def test_15_confirmation_never_selection(self):
        selection = self.payload[
            "selection_contract"
        ]

        for key, value in selection.items():
            if key.startswith(
                "confirmation_"
            ):
                self.assertFalse(
                    value
                )

    def test_16_availability_not_label(self):
        self.assertFalse(
            self.payload[
                "health_supervision_boundary"
            ][
                "availability_is_health_label"
            ]
        )

    def test_17_missing_not_zero_vector(self):
        self.assertFalse(
            self.payload[
                "health_supervision_boundary"
            ][
                "missing_measurement_is_zero_feature_vector"
            ]
        )

    def test_18_clean_not_automatic_healthy(self):
        self.assertFalse(
            self.payload[
                "health_supervision_boundary"
            ][
                "clean_dataset_branch_automatically_means_healthy"
            ]
        )

    def test_19_corruption_not_automatic_label(self):
        self.assertFalse(
            self.payload[
                "health_supervision_boundary"
            ][
                "synthetic_corruption_identity_automatically_means_health_label"
            ]
        )

    def test_20_error_not_health_label(self):
        boundary = self.payload[
            "health_supervision_boundary"
        ]

        self.assertFalse(
            boundary[
                "final_localization_error_may_define_health_label"
            ]
        )

        self.assertTrue(
            boundary[
                "health_labels_must_be_independent_from_final_localization_error"
            ]
        )

    def test_21_evaluator_closed(self):
        self.assertEqual(
            set(
                self.payload[
                    "current_evaluator_boundary"
                ].values()
            ),
            {
                False,
            },
        )

    def test_22_stage_order(self):
        self.assertEqual(
            stage_ids(),
            STAGE_ORDER,
        )

    def test_23_eleven_stages(self):
        self.assertEqual(
            len(STAGE_ORDER),
            11,
        )

    def test_24_se1_next(self):
        self.assertEqual(
            self.payload[
                "current_track_state"
            ][
                "next_stage_after_se0_checkpoint"
            ],
            "SE1",
        )

    def test_25_se1_train_access(self):
        stage = stage_definition("SE1")

        self.assertTrue(
            stage.train_access
        )

        self.assertFalse(
            stage.validation_access
        )

        self.assertFalse(
            stage.confirmation_access
        )

    def test_26_se1_no_training(self):
        stage = stage_definition("SE1")

        self.assertFalse(
            stage.executes_model_training
        )

    def test_27_se4_trains(self):
        self.assertTrue(
            stage_definition(
                "SE4"
            ).executes_model_training
        )

    def test_28_se5_validation_access(self):
        stage = stage_definition("SE5")

        self.assertTrue(
            stage.validation_access
        )

        self.assertTrue(
            stage.executes_parameter_selection
        )

        self.assertFalse(
            stage.confirmation_access
        )

    def test_29_se9_closed(self):
        stage = stage_definition("SE9")

        self.assertEqual(
            stage.current_status,
            "closed",
        )

        self.assertFalse(
            stage.confirmation_access
        )

    def test_30_all_current_confirmation_access_false(self):
        for stage in self.payload["stages"]:
            self.assertFalse(
                stage[
                    "confirmation_access"
                ]
            )

    def test_31_se1_entry_ready(self):
        gate = self.payload[
            "SE1_entry_gate"
        ]

        for key in (
            "recorded_dataset_root_present",
            "m2dgr_split_frozen",
            "phase4_real_lidar_diagnostics_present",
            "phase5_real_camera_imu_ingestion_present",
            "phase5_through_phase14_architecture_frozen",
            "confirmation_closed",
            "SE1_may_execute_on_train_partition",
        ):
            self.assertTrue(
                gate[
                    key
                ]
            )

    def test_32_se1_forbidden_actions(self):
        gate = self.payload[
            "SE1_entry_gate"
        ]

        for key in (
            "SE1_may_open_validation",
            "SE1_may_open_confirmation",
            "SE1_may_train_health_model",
            "SE1_may_select_scientific_thresholds",
            "SE1_may_compute_final_localization_scores",
        ):
            self.assertFalse(
                gate[
                    key
                ]
            )

    def test_33_se9_requires_all_upstream_freezes(self):
        gate = self.payload[
            "SE9_opening_gate"
        ]

        self.assertFalse(
            gate[
                "currently_open"
            ]
        )

        for key, value in gate.items():
            if key.startswith(
                "requires_"
            ):
                self.assertTrue(
                    value
                )

    def test_34_confirmation_cannot_reopen_selection(self):
        self.assertFalse(
            self.payload[
                "SE9_opening_gate"
            ][
                "confirmation_may_reopen_selection_after_results"
            ]
        )

    def test_35_software_track_no_hardware_required(self):
        boundary = self.payload[
            "hardware_boundary"
        ]

        self.assertFalse(
            boundary[
                "software_evidence_track_requires_hardware_to_begin"
            ]
        )

        self.assertTrue(
            boundary[
                "recorded_datasets_are_virtual_sensor_inputs"
            ]
        )

    def test_36_software_not_physical_proof(self):
        boundary = self.payload[
            "hardware_boundary"
        ]

        self.assertFalse(
            boundary[
                "software_success_equals_physical_hardware_validation"
            ]
        )

        self.assertFalse(
            boundary[
                "physical_sensor_or_robot_claims_authorized"
            ]
        )

    def test_37_dashboard_cannot_modify_science(self):
        boundary = self.payload[
            "dashboard_boundary"
        ]

        self.assertFalse(
            boundary[
                "dashboard_may_select_scientific_parameters"
            ]
        )

        self.assertFalse(
            boundary[
                "dashboard_may_modify_frozen_thresholds_or_calibration"
            ]
        )

    def test_38_fail_closed_guards(self):
        for guard in (
            assert_confirmation_selection_forbidden,
            assert_confirmation_execution_authorized,
            assert_ate_rpe_authorized,
        ):
            with self.assertRaises(
                EvidencePlanError
            ):
                guard()

    def test_39_manifest_validates(self):
        validate_plan_manifest(
            self.payload
        )

    def test_40_confirmation_mutation_rejected(self):
        modified = copy.deepcopy(
            self.payload
        )

        modified[
            "selection_contract"
        ][
            "confirmation_may_select_model"
        ] = True

        with self.assertRaises(
            EvidencePlanError
        ):
            validate_plan_manifest(
                modified
            )


if __name__ == "__main__":
    unittest.main()
