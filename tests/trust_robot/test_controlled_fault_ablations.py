import copy
import json
from pathlib import Path
import unittest

from trust_robot.controlled_fault_ablations import (
    CURRENT_PHASE10_GATE,
    ControlledFaultAblationContractError,
    Phase10Lifecycle,
    assert_native_fault_execution_authorized,
    assert_phase10_experiment_execution_authorized,
    assert_physical_fault_execution_authorized,
    native_phase3_family_names,
    validate_contract_manifest,
)


ROOT = Path(__file__).resolve().parents[2]

CONFIG = (
    ROOT
    / "configs"
    / "trust_robot"
    / "phase10_controlled_fault_ablation_contract_candidate_v1.json"
)


class TestControlledFaultAblationsContract(unittest.TestCase):

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
            "TRUST_ROBOT_PHASE10_CONTROLLED_FAULT_ABLATION_CONTRACT_V1",
        )

    def test_02_lifecycle(self):
        self.assertEqual(
            self.payload["lifecycle_status"],
            Phase10Lifecycle
            .CONTRACT_IMPLEMENTED_EXPERIMENTS_UNSELECTED
            .value,
        )

    def test_03_phase(self):
        self.assertEqual(
            self.payload["phase_scope"]["phase"],
            10,
        )

    def test_04_phase_scope_name(self):
        self.assertEqual(
            self.payload["phase_scope"]["name"],
            "causal_ablations_and_controlled_faults",
        )

    def test_05_same_backbone_evidence_role(self):
        self.assertEqual(
            self.payload["phase_scope"]["evidence_role"],
            "same_backbone_RQ1_RQ2_evidence",
        )

    def test_06_numbered_section_not_phase10(self):
        self.assertFalse(
            self.payload[
                "phase_scope"
            ][
                "numbered_master_section_10_is_phase_plan_phase10"
            ]
        )

    def test_07_rq1_present(self):
        self.assertIn(
            "healthy/degraded/unusable",
            self.payload[
                "research_questions"
            ][
                "RQ1"
            ],
        )

    def test_08_rq2_present(self):
        self.assertIn(
            "increasing fault severity",
            self.payload[
                "research_questions"
            ][
                "RQ2"
            ],
        )

    def test_09_same_backbone_definition_unselected(self):
        boundary = self.payload[
            "same_backbone_boundary"
        ]

        self.assertEqual(
            boundary[
                "operational_definition"
            ],
            "unselected",
        )

        self.assertFalse(
            boundary[
                "operational_definition_selected"
            ]
        )

    def test_10_ablation_variants_unselected(self):
        boundary = self.payload[
            "same_backbone_boundary"
        ]

        self.assertEqual(
            boundary[
                "ablation_variants"
            ],
            [],
        )

        self.assertFalse(
            boundary[
                "ablation_variants_selected"
            ]
        )

    def test_11_undeclared_changes_forbidden(self):
        self.assertFalse(
            self.payload[
                "same_backbone_boundary"
            ][
                "undeclared_pipeline_changes_allowed"
            ]
        )

    def test_12_rq1_proxy_unselected(self):
        rq1 = self.payload[
            "rq1_ablation_boundary"
        ]

        self.assertEqual(
            rq1[
                "proxy_reliability_definition"
            ],
            "unselected",
        )

        self.assertFalse(
            rq1[
                "proxy_reliability_definition_selected"
            ]
        )

    def test_13_rq1_not_executable(self):
        self.assertFalse(
            self.payload[
                "rq1_ablation_boundary"
            ][
                "rq1_executable"
            ]
        )

    def test_14_rq2_not_executable(self):
        self.assertFalse(
            self.payload[
                "rq2_ablation_boundary"
            ][
                "rq2_executable"
            ]
        )

    def test_15_native_families_exact(self):
        self.assertEqual(
            native_phase3_family_names(),
            (
                "EVENT_GAP",
                "EVENT_REPEAT",
                "TIMESTAMP_STEP_SHIFT",
            ),
        )

    def test_16_no_family_expansion(self):
        self.assertFalse(
            self.payload[
                "native_phase3_binding"
            ][
                "native_family_expansion_selected"
            ]
        )

    def test_17_selection_policy_bound(self):
        self.assertTrue(
            self.payload[
                "native_phase3_binding"
            ][
                "selection_policy_bound"
            ]
        )

    def test_18_synthetic_truth_not_health_label(self):
        self.assertFalse(
            self.payload[
                "native_phase3_binding"
            ][
                "synthetic_truth_is_health_label"
            ]
        )

    def test_19_synthetic_truth_not_physical_proof(self):
        self.assertFalse(
            self.payload[
                "native_phase3_binding"
            ][
                "synthetic_truth_is_physical_fault_proof"
            ]
        )

    def test_20_synthetic_truth_not_runtime_causal_evidence(self):
        self.assertFalse(
            self.payload[
                "native_phase3_binding"
            ][
                "synthetic_truth_is_runtime_causal_evidence"
            ]
        )

    def test_21_numeric_severity_unselected(self):
        fault = self.payload[
            "fault_parameter_boundary"
        ]

        self.assertIsNone(
            fault[
                "numeric_fault_severity"
            ]
        )

        self.assertFalse(
            fault[
                "numeric_fault_severity_selected"
            ]
        )

    def test_22_severity_grid_unselected(self):
        fault = self.payload[
            "fault_parameter_boundary"
        ]

        self.assertIsNone(
            fault[
                "severity_grid"
            ]
        )

        self.assertFalse(
            fault[
                "severity_grid_selected"
            ]
        )

    def test_23_attack_budget_unselected(self):
        fault = self.payload[
            "fault_parameter_boundary"
        ]

        self.assertIsNone(
            fault[
                "attack_budget"
            ]
        )

        self.assertFalse(
            fault[
                "attack_budget_selected"
            ]
        )

    def test_24_schedule_unselected(self):
        fault = self.payload[
            "fault_parameter_boundary"
        ]

        self.assertIsNone(
            fault[
                "fault_schedule"
            ]
        )

        self.assertFalse(
            fault[
                "fault_schedule_selected"
            ]
        )

    def test_25_seed_schedule_unselected(self):
        fault = self.payload[
            "fault_parameter_boundary"
        ]

        self.assertIsNone(
            fault[
                "partition_seed_schedule"
            ]
        )

        self.assertFalse(
            fault[
                "partition_seed_schedule_selected"
            ]
        )

    def test_26_no_silent_defaults(self):
        fault = self.payload[
            "fault_parameter_boundary"
        ]

        self.assertFalse(
            fault[
                "silent_severity_default_allowed"
            ]
        )

        self.assertFalse(
            fault[
                "silent_attack_budget_default_allowed"
            ]
        )

    def test_27_fault_layer_required(self):
        self.assertTrue(
            self.payload[
                "fault_injection_rules"
            ][
                "scientifically_appropriate_layer_required"
            ]
        )

    def test_28_raw_and_factor_not_equivalent(self):
        self.assertFalse(
            self.payload[
                "fault_injection_rules"
            ][
                "raw_sensor_and_factor_level_corruption_equivalent"
            ]
        )

    def test_29_derivatives_same_partition(self):
        self.assertTrue(
            self.payload[
                "fault_injection_rules"
            ][
                "clean_and_corrupted_derivatives_remain_same_partition"
            ]
        )

    def test_30_seed_reuse_forbidden_across_partitions(self):
        self.assertFalse(
            self.payload[
                "fault_injection_rules"
            ][
                "random_seeds_may_be_reused_across_partitions"
            ]
        )

    def test_31_controlled_availability_not_accepted_supervision(self):
        self.assertFalse(
            self.payload[
                "controlled_availability_binding"
            ][
                "accepted_health_supervision_source"
            ]
        )

    def test_32_real_health_label_count_zero(self):
        self.assertEqual(
            self.payload[
                "controlled_availability_binding"
            ][
                "real_health_label_count"
            ],
            0,
        )

    def test_33_experiment_execution_blocked(self):
        self.assertFalse(
            CURRENT_PHASE10_GATE
            .phase10_experiment_execution_authorized
        )

    def test_34_experiment_guard_raises(self):
        with self.assertRaises(
            ControlledFaultAblationContractError
        ):
            assert_phase10_experiment_execution_authorized()

    def test_35_native_fault_guard_raises(self):
        with self.assertRaises(
            ControlledFaultAblationContractError
        ):
            assert_native_fault_execution_authorized()

    def test_36_physical_fault_guard_raises(self):
        with self.assertRaises(
            ControlledFaultAblationContractError
        ):
            assert_physical_fault_execution_authorized()

    def test_37_validation_and_confirmation_closed(self):
        boundary = self.payload[
            "data_selection_boundary"
        ]

        self.assertFalse(
            boundary[
                "validation_data_opened"
            ]
        )

        self.assertFalse(
            boundary[
                "confirmation_data_used"
            ]
        )

    def test_38_no_aggregate_score_or_ate_rpe(self):
        boundary = self.payload[
            "evaluation_boundary"
        ]

        self.assertFalse(
            boundary[
                "single_undocumented_aggregate_score_allowed"
            ]
        )

        self.assertFalse(
            boundary[
                "ate_rpe_computation_authorized"
            ]
        )

        self.assertFalse(
            boundary[
                "final_scoring_authorized"
            ]
        )

    def test_39_manifest_validates(self):
        validate_contract_manifest(
            self.payload
        )

    def test_40_severity_injection_rejected(self):
        modified = copy.deepcopy(
            self.payload
        )

        modified[
            "fault_parameter_boundary"
        ][
            "numeric_fault_severity"
        ] = 0.5

        modified[
            "fault_parameter_boundary"
        ][
            "numeric_fault_severity_selected"
        ] = True

        with self.assertRaises(
            ControlledFaultAblationContractError
        ):
            validate_contract_manifest(
                modified
            )


if __name__ == "__main__":
    unittest.main()
