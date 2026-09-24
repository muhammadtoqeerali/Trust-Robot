import copy
import json
from pathlib import Path
import unittest

from trust_robot.supervisory_physical_integration import (
    Phase14Lifecycle,
    SupervisoryPhysicalIntegrationContractError,
    assert_closed_loop_safety_claim_authorized,
    assert_closed_loop_safety_measurement_authorized,
    assert_physical_test_execution_authorized,
    assert_robot_integration_execution_authorized,
    planned_policy_comparison_identities,
    supervisor_input_identities,
    validate_contract_manifest,
)


ROOT = Path(__file__).resolve().parents[2]

CONFIG = (
    ROOT
    / "configs"
    / "trust_robot"
    / "phase14_supervisory_physical_integration_contract_candidate_v1.json"
)


class TestSupervisoryPhysicalIntegrationContract(unittest.TestCase):

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
            "TRUST_ROBOT_PHASE14_SUPERVISORY_PHYSICAL_INTEGRATION_CONTRACT_V1",
        )

    def test_02_lifecycle(self):
        self.assertEqual(
            self.payload[
                "lifecycle_status"
            ],
            Phase14Lifecycle
            .CONTRACT_IMPLEMENTED_ROBOT_SEMANTICS_UNSELECTED
            .value,
        )

    def test_03_phase(self):
        self.assertEqual(
            self.payload[
                "phase_scope"
            ][
                "phase"
            ],
            14,
        )

    def test_04_phase_scope(self):
        self.assertEqual(
            self.payload[
                "phase_scope"
            ][
                "name"
            ],
            "guarded_real_robot_integration_and_supervisory_testing",
        )

    def test_05_health_model_not_controller(self):
        self.assertFalse(
            self.payload[
                "supervisor_architecture"
            ][
                "learned_health_model_is_robot_controller"
            ]
        )

    def test_06_separate_rule_based_supervisor(self):
        self.assertTrue(
            self.payload[
                "supervisor_architecture"
            ][
                "separate_rule_based_supervisory_layer_required"
            ]
        )

    def test_07_physical_experiments_guarded(self):
        architecture = self.payload[
            "supervisor_architecture"
        ]

        self.assertTrue(
            architecture[
                "physical_experiments_must_remain_guarded"
            ]
        )

        self.assertTrue(
            architecture[
                "physical_experiments_must_be_progressively_validated"
            ]
        )

    def test_08_six_supervisor_inputs(self):
        self.assertEqual(
            len(
                supervisor_input_identities()
            ),
            6,
        )

    def test_09_supervisor_inputs_exact(self):
        self.assertEqual(
            supervisor_input_identities(),
            (
                "calibrated modality-health probabilities",
                "estimator covariance/status",
                "tracking availability",
                "residual consistency",
                "solver validity",
                "frozen validation-selected thresholds",
            ),
        )

    def test_10_input_identity_not_runtime_readiness(self):
        schema = self.payload[
            "supervisor_input_schema"
        ]

        self.assertFalse(
            schema[
                "candidate_input_identity_implies_runtime_readiness"
            ]
        )

        self.assertFalse(
            schema[
                "all_candidate_inputs_runtime_verified"
            ]
        )

    def test_11_four_policy_identities(self):
        self.assertEqual(
            len(
                planned_policy_comparison_identities()
            ),
            4,
        )

    def test_12_policy_identities_exact(self):
        self.assertEqual(
            planned_policy_comparison_identities(),
            (
                "nominal continuation",
                "always-stop",
                "health-triggered policy",
                "oracle-health policy",
            ),
        )

    def test_13_policy_names_not_operational_policy(self):
        policies = self.payload[
            "planned_policy_comparisons"
        ]

        self.assertFalse(
            policies[
                "identities_are_selected_operational_policy"
            ]
        )

        self.assertFalse(
            policies[
                "identities_define_robot_command_semantics"
            ]
        )

    def test_14_oracle_health_comparison_only(self):
        policies = self.payload[
            "planned_policy_comparisons"
        ]

        self.assertFalse(
            policies[
                "oracle_health_is_runtime_available_signal"
            ]
        )

        self.assertTrue(
            policies[
                "oracle_health_role_is_planned_comparison_only"
            ]
        )

    def test_15_no_action_semantics_selected(self):
        boundary = self.payload[
            "robot_action_semantics_boundary"
        ]

        for key, value in boundary.items():
            if key.endswith(
                "_selected"
            ):
                self.assertFalse(
                    value
                )
            else:
                self.assertIsNone(
                    value
                )

    def test_16_eventual_platform_role(self):
        platform = self.payload[
            "physical_platform_boundary"
        ]

        self.assertEqual(
            platform[
                "eventual_platform_role"
            ],
            "local_quadruped_robot",
        )

    def test_17_physical_dataset_provisional(self):
        platform = self.payload[
            "physical_platform_boundary"
        ]

        self.assertEqual(
            platform[
                "provisional_dataset_identity"
            ],
            "KIOS_QUADRUPED",
        )

        self.assertEqual(
            platform[
                "local_readiness"
            ],
            "not_collected",
        )

    def test_18_robot_identity_unfrozen(self):
        platform = self.payload[
            "physical_platform_boundary"
        ]

        self.assertIsNone(
            platform[
                "actual_robot_identity"
            ]
        )

        self.assertFalse(
            platform[
                "actual_robot_identity_frozen"
            ]
        )

    def test_19_compute_and_sensor_suite_unfrozen(self):
        platform = self.payload[
            "physical_platform_boundary"
        ]

        self.assertIsNone(
            platform[
                "compute_hardware"
            ]
        )

        self.assertFalse(
            platform[
                "compute_hardware_frozen"
            ]
        )

        self.assertIsNone(
            platform[
                "sensor_suite"
            ]
        )

        self.assertFalse(
            platform[
                "sensor_suite_frozen"
            ]
        )

    def test_20_calibration_sync_reference_unfrozen(self):
        platform = self.payload[
            "physical_platform_boundary"
        ]

        for key in (
            "calibration_frozen",
            "synchronization_frozen",
            "reference_instrumentation_frozen",
        ):
            self.assertFalse(
                platform[
                    key
                ]
            )

    def test_21_controller_semantics_unverified(self):
        platform = self.payload[
            "physical_platform_boundary"
        ]

        self.assertFalse(
            platform[
                "controller_interface_verified"
            ]
        )

        self.assertFalse(
            platform[
                "control_command_semantics_verified"
            ]
        )

    def test_22_proprioception_unverified(self):
        self.assertFalse(
            self.payload[
                "physical_platform_boundary"
            ][
                "proprioception_available_and_verified"
            ]
        )

    def test_23_physical_execution_not_ready(self):
        self.assertFalse(
            self.payload[
                "physical_platform_boundary"
            ][
                "physical_execution_ready"
            ]
        )

    def test_24_physical_partition_separation(self):
        boundary = self.payload[
            "physical_partition_boundary"
        ]

        self.assertTrue(
            boundary[
                "development_calibration_runs_separate_from_final_held_out_physical_tests"
            ]
        )

        self.assertTrue(
            boundary[
                "base_trajectory_derivatives_remain_in_one_partition"
            ]
        )

    def test_25_heldout_physical_selects_nothing(self):
        boundary = self.payload[
            "physical_partition_boundary"
        ]

        for key, value in boundary.items():
            if key in {
                "development_calibration_runs_separate_from_final_held_out_physical_tests",
                "base_trajectory_derivatives_remain_in_one_partition",
            }:
                continue

            self.assertFalse(
                value
            )

    def test_26_phase9_does_not_define_fallback(self):
        boundary = self.payload[
            "fallback_and_threshold_boundary"
        ]

        self.assertFalse(
            boundary[
                "fallback_defined_by_authoritative_phase9_section"
            ]
        )

        self.assertFalse(
            boundary[
                "phase9_fallback_policy_selected"
            ]
        )

    def test_27_fallback_threshold_not_selected(self):
        boundary = self.payload[
            "fallback_and_threshold_boundary"
        ]

        self.assertFalse(
            boundary[
                "fallback_threshold_selected"
            ]
        )

        self.assertFalse(
            boundary[
                "safety_threshold_selected"
            ]
        )

    def test_28_thresholds_freeze_before_physical_test(self):
        boundary = self.payload[
            "fallback_and_threshold_boundary"
        ]

        self.assertTrue(
            boundary[
                "fallback_thresholds_must_be_frozen_before_physical_tests"
            ]
        )

        self.assertTrue(
            boundary[
                "threshold_role_is_validation_selected"
            ]
        )

    def test_29_final_physical_test_cannot_select_threshold(self):
        boundary = self.payload[
            "fallback_and_threshold_boundary"
        ]

        self.assertFalse(
            boundary[
                "final_physical_test_may_select_threshold"
            ]
        )

        self.assertFalse(
            boundary[
                "confirmation_may_select_threshold"
            ]
        )

    def test_30_physical_safety_metrics_unselected(self):
        self.assertEqual(
            set(
                self.payload[
                    "physical_safety_metric_boundary"
                ].values()
            ),
            {
                False,
            },
        )

    def test_31_historical_safety_not_adopted(self):
        self.assertEqual(
            set(
                self.payload[
                    "historical_reuse_boundary"
                ].values()
            ),
            {
                False,
            },
        )

    def test_32_upstream_runtime_evidence_not_assumed(self):
        self.assertEqual(
            set(
                self.payload[
                    "upstream_evidence_boundary"
                ].values()
            ),
            {
                False,
            },
        )

    def test_33_rq4_closed_loop_component_here(self):
        rq4 = self.payload[
            "rq4_boundary"
        ]

        self.assertTrue(
            rq4[
                "closed_loop_safety_component_in_phase14"
            ]
        )

    def test_34_rq4_still_unanswered(self):
        rq4 = self.payload[
            "rq4_boundary"
        ]

        for key in (
            "resource_component_answer_available",
            "onboard_resource_constraints_verified",
            "fallback_thresholds_frozen",
            "guarded_physical_test_executed",
            "closed_loop_safety_answer_available",
            "full_rq4_answer_available",
        ):
            self.assertFalse(
                rq4[
                    key
                ]
            )

    def test_35_execution_gate_closed(self):
        self.assertEqual(
            set(
                self.payload[
                    "execution_gate"
                ].values()
            ),
            {
                False,
            },
        )

    def test_36_protected_scientific_boundaries_closed(self):
        self.assertEqual(
            set(
                self.payload[
                    "protected_scientific_boundaries"
                ].values()
            ),
            {
                False,
            },
        )

    def test_37_robot_and_physical_guards_raise(self):
        with self.assertRaises(
            SupervisoryPhysicalIntegrationContractError
        ):
            assert_robot_integration_execution_authorized()

        with self.assertRaises(
            SupervisoryPhysicalIntegrationContractError
        ):
            assert_physical_test_execution_authorized()

    def test_38_safety_guards_raise(self):
        with self.assertRaises(
            SupervisoryPhysicalIntegrationContractError
        ):
            assert_closed_loop_safety_measurement_authorized()

        with self.assertRaises(
            SupervisoryPhysicalIntegrationContractError
        ):
            assert_closed_loop_safety_claim_authorized()

    def test_39_phase15_preparation_only(self):
        boundary = self.payload[
            "next_phase_policy"
        ]

        self.assertTrue(
            boundary[
                "phase15_software_preparation_may_proceed_after_phase14_checkpoint"
            ]
        )

        self.assertFalse(
            boundary[
                "final_confirmation_execution_authorized"
            ]
        )

    def test_40_manifest_validates_and_mutation_rejected(self):
        validate_contract_manifest(
            self.payload
        )

        modified = copy.deepcopy(
            self.payload
        )

        modified[
            "robot_action_semantics_boundary"
        ][
            "stop_command"
        ] = "zero_velocity"

        modified[
            "robot_action_semantics_boundary"
        ][
            "stop_command_selected"
        ] = True

        with self.assertRaises(
            SupervisoryPhysicalIntegrationContractError
        ):
            validate_contract_manifest(
                modified
            )


if __name__ == "__main__":
    unittest.main()
