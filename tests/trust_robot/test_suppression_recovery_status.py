import copy
import json
from pathlib import Path
import unittest

from trust_robot.suppression_recovery_status import (
    CURRENT_SUPPRESSION_RECOVERY_GATE,
    SuppressionRecoveryContractError,
    SuppressionRecoveryLifecycle,
    assert_fallback_execution_authorized,
    assert_recovery_execution_authorized,
    assert_runtime_status_execution_authorized,
    assert_suppression_execution_authorized,
    insufficient_support_report_names,
    validate_contract_manifest,
)


ROOT = Path(__file__).resolve().parents[2]

CONFIG = (
    ROOT
    / "configs"
    / "trust_robot"
    / "phase9_suppression_recovery_status_contract_candidate_v1.json"
)


class TestSuppressionRecoveryStatusContract(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(
            CONFIG.read_text(
                encoding="utf-8"
            )
        )

    def test_01_schema(self):
        self.assertEqual(
            self.payload[
                "schema"
            ],
            "TRUST_ROBOT_PHASE9_SUPPRESSION_RECOVERY_STATUS_CONTRACT_V1",
        )

    def test_02_lifecycle(self):
        self.assertEqual(
            self.payload[
                "lifecycle_status"
            ],
            SuppressionRecoveryLifecycle
            .CONTRACT_IMPLEMENTED_PARAMETERS_UNSELECTED
            .value,
        )

    def test_03_phase(self):
        self.assertEqual(
            self.payload[
                "phase_scope"
            ][
                "phase"
            ],
            9,
        )

    def test_04_scope_name(self):
        self.assertEqual(
            self.payload[
                "phase_scope"
            ][
                "name"
            ],
            "suppression_recovery_status",
        )

    def test_05_single_frame_suppression_forbidden(self):
        self.assertFalse(
            self.payload[
                "hysteresis_architecture"
            ][
                "single_frame_hard_suppression_allowed"
            ]
        )

    def test_06_entry_signal_unusable_probability(self):
        self.assertEqual(
            self.payload[
                "hysteresis_architecture"
            ][
                "entry_signal"
            ],
            "unusable_probability",
        )

    def test_07_entry_threshold_unselected(self):
        hysteresis = self.payload[
            "hysteresis_architecture"
        ]

        self.assertIsNone(
            hysteresis[
                "entry_threshold_value"
            ]
        )

        self.assertFalse(
            hysteresis[
                "entry_threshold_selected"
            ]
        )

    def test_08_entry_window_unselected(self):
        hysteresis = self.payload[
            "hysteresis_architecture"
        ]

        self.assertIsNone(
            hysteresis[
                "entry_consecutive_window_count"
            ]
        )

        self.assertFalse(
            hysteresis[
                "entry_consecutive_window_count_selected"
            ]
        )

    def test_09_recovery_threshold_lower(self):
        self.assertEqual(
            self.payload[
                "hysteresis_architecture"
            ][
                "recovery_threshold_relation_to_entry"
            ],
            "lower",
        )

    def test_10_recovery_threshold_unselected(self):
        hysteresis = self.payload[
            "hysteresis_architecture"
        ]

        self.assertIsNone(
            hysteresis[
                "recovery_threshold_value"
            ]
        )

        self.assertFalse(
            hysteresis[
                "recovery_threshold_selected"
            ]
        )

    def test_11_recovery_window_unselected(self):
        hysteresis = self.payload[
            "hysteresis_architecture"
        ]

        self.assertIsNone(
            hysteresis[
                "recovery_consecutive_window_count"
            ]
        )

        self.assertFalse(
            hysteresis[
                "recovery_consecutive_window_count_selected"
            ]
        )

    def test_12_no_default_threshold(self):
        self.assertFalse(
            self.payload[
                "hysteresis_architecture"
            ][
                "default_threshold_created"
            ]
        )

    def test_13_no_default_window_count(self):
        self.assertFalse(
            self.payload[
                "hysteresis_architecture"
            ][
                "default_window_count_created"
            ]
        )

    def test_14_support_assessment_required(self):
        self.assertTrue(
            self.payload[
                "remaining_factor_support"
            ][
                "assessment_required_before_hard_suppression"
            ]
        )

    def test_15_support_definition_unselected(self):
        support = self.payload[
            "remaining_factor_support"
        ]

        self.assertEqual(
            support[
                "assessment_definition"
            ],
            "unselected",
        )

        self.assertFalse(
            support[
                "assessment_definition_selected"
            ]
        )

    def test_16_minimum_modality_count_unselected(self):
        support = self.payload[
            "remaining_factor_support"
        ]

        self.assertIsNone(
            support[
                "minimum_active_modality_count"
            ]
        )

        self.assertFalse(
            support[
                "minimum_active_modality_count_selected"
            ]
        )

    def test_17_observability_test_unselected(self):
        support = self.payload[
            "remaining_factor_support"
        ]

        self.assertEqual(
            support[
                "observability_test"
            ],
            "unselected",
        )

        self.assertFalse(
            support[
                "observability_test_selected"
            ]
        )

    def test_18_no_unsupported_observability_guarantee(self):
        self.assertFalse(
            self.payload[
                "remaining_factor_support"
            ][
                "unsupported_observability_guarantee_allowed"
            ]
        )

    def test_19_exact_insufficient_support_options(self):
        self.assertEqual(
            insufficient_support_report_names(),
            (
                "degraded_estimator_state",
                "unavailable_estimator_state",
            ),
        )

    def test_20_status_rule_unselected(self):
        reporting = self.payload[
            "insufficient_support_reporting"
        ]

        self.assertEqual(
            reporting[
                "degraded_vs_unavailable_rule"
            ],
            "unselected",
        )

        self.assertFalse(
            reporting[
                "degraded_vs_unavailable_rule_selected"
            ]
        )

    def test_21_cannot_force_nominal(self):
        self.assertFalse(
            self.payload[
                "insufficient_support_reporting"
            ][
                "nominal_estimate_may_be_forced_when_support_insufficient"
            ]
        )

    def test_22_suppression_blocked(self):
        self.assertFalse(
            CURRENT_SUPPRESSION_RECOVERY_GATE
            .suppression_execution_authorized
        )

    def test_23_suppression_guard_raises(self):
        with self.assertRaises(
            SuppressionRecoveryContractError
        ):
            assert_suppression_execution_authorized()

    def test_24_recovery_blocked(self):
        self.assertFalse(
            CURRENT_SUPPRESSION_RECOVERY_GATE
            .recovery_execution_authorized
        )

    def test_25_recovery_guard_raises(self):
        with self.assertRaises(
            SuppressionRecoveryContractError
        ):
            assert_recovery_execution_authorized()

    def test_26_status_blocked(self):
        self.assertFalse(
            CURRENT_SUPPRESSION_RECOVERY_GATE
            .runtime_status_execution_authorized
        )

    def test_27_status_guard_raises(self):
        with self.assertRaises(
            SuppressionRecoveryContractError
        ):
            assert_runtime_status_execution_authorized()

    def test_28_phase8_scale_unavailable(self):
        self.assertFalse(
            self.payload[
                "execution_gate"
            ][
                "phase8_numeric_factor_scale_available"
            ]
        )

    def test_29_health_state_not_suppression_command(self):
        self.assertFalse(
            self.payload[
                "health_availability_separation"
            ][
                "phase5_health_state_is_suppression_command"
            ]
        )

    def test_30_availability_not_health_label(self):
        self.assertFalse(
            self.payload[
                "health_availability_separation"
            ][
                "availability_is_health_label"
            ]
        )

    def test_31_fallback_not_in_authoritative_section(self):
        self.assertFalse(
            self.payload[
                "phase_scope"
            ][
                "fallback_policy_defined_by_authoritative_phase9_section"
            ]
        )

    def test_32_fallback_unselected(self):
        fallback = self.payload[
            "fallback_boundary"
        ]

        self.assertEqual(
            fallback[
                "fallback_policy"
            ],
            "unselected",
        )

        self.assertFalse(
            fallback[
                "fallback_policy_selected"
            ]
        )

    def test_33_fallback_guard_raises(self):
        with self.assertRaises(
            SuppressionRecoveryContractError
        ):
            assert_fallback_execution_authorized()

    def test_34_no_validation_opened(self):
        self.assertFalse(
            self.payload[
                "selection_boundary"
            ][
                "validation_data_opened"
            ]
        )

    def test_35_confirmation_closed_for_selection(self):
        selection = self.payload[
            "selection_boundary"
        ]

        self.assertFalse(
            selection[
                "confirmation_data_used"
            ]
        )

        self.assertFalse(
            selection[
                "confirmation_may_select_suppression_threshold"
            ]
        )

        self.assertFalse(
            selection[
                "confirmation_may_select_recovery_threshold"
            ]
        )

    def test_36_timeout_unselected(self):
        self.assertFalse(
            self.payload[
                "protected_scientific_boundaries"
            ][
                "timeout_selected"
            ]
        )

    def test_37_no_ate_rpe_or_final_score(self):
        boundary = self.payload[
            "protected_scientific_boundaries"
        ]

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

    def test_38_runtime_outputs_disabled(self):
        self.assertEqual(
            set(
                self.payload[
                    "runtime_outputs"
                ].values()
            ),
            {
                "disabled",
            },
        )

    def test_39_manifest_validates(self):
        validate_contract_manifest(
            self.payload
        )

    def test_40_threshold_injection_rejected(self):
        modified = copy.deepcopy(
            self.payload
        )

        modified[
            "hysteresis_architecture"
        ][
            "entry_threshold_value"
        ] = 0.8

        modified[
            "hysteresis_architecture"
        ][
            "entry_threshold_selected"
        ] = True

        with self.assertRaises(
            SuppressionRecoveryContractError
        ):
            validate_contract_manifest(
                modified
            )


if __name__ == "__main__":
    unittest.main()
