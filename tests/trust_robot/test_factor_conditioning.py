import copy
import json
from pathlib import Path
import unittest

from trust_robot.factor_conditioning import (
    CURRENT_FACTOR_CONDITIONING_GATE,
    FINAL_FACTOR_SCALE_FORMULA,
    HEALTH_WEIGHT_FORMULA,
    FactorConditioningContractError,
    FactorConditioningLifecycle,
    assert_covariance_inflation_authorized,
    assert_factor_scale_execution_authorized,
    assert_information_rescaling_authorized,
    pathway_names,
    validate_contract_manifest,
)


ROOT = Path(__file__).resolve().parents[2]

CONFIG = (
    ROOT
    / "configs"
    / "trust_robot"
    / "phase8_factor_conditioning_contract_candidate_v1.json"
)


class TestFactorConditioningContract(unittest.TestCase):

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
            "TRUST_ROBOT_PHASE8_FACTOR_CONDITIONING_CONTRACT_V1",
        )

    def test_02_lifecycle(self):
        self.assertEqual(
            self.payload[
                "lifecycle_status"
            ],
            FactorConditioningLifecycle
            .CONTRACT_IMPLEMENTED_INPUTS_UNAVAILABLE
            .value,
        )

    def test_03_phase(self):
        self.assertEqual(
            self.payload[
                "phase_scope"
            ][
                "phase"
            ],
            8,
        )

    def test_04_scope_name(self):
        self.assertEqual(
            self.payload[
                "phase_scope"
            ][
                "name"
            ],
            "factor_conditioning",
        )

    def test_05_health_weight_formula(self):
        self.assertEqual(
            self.payload[
                "authoritative_equations"
            ][
                "health_weight"
            ],
            HEALTH_WEIGHT_FORMULA,
        )

    def test_06_factor_scale_formula(self):
        self.assertEqual(
            self.payload[
                "authoritative_equations"
            ][
                "final_factor_scale"
            ],
            FINAL_FACTOR_SCALE_FORMULA,
        )

    def test_07_numeric_execution_blocked(self):
        self.assertFalse(
            self.payload[
                "authoritative_equations"
            ][
                "numeric_execution_authorized"
            ]
        )

    def test_08_two_pathways(self):
        self.assertEqual(
            pathway_names(),
            (
                "persistent_health",
                "current_innovation",
            ),
        )

    def test_09_health_path_distinct(self):
        self.assertTrue(
            self.payload[
                "pathway_separation"
            ][
                "persistent_health_pathway_distinct"
            ]
        )

    def test_10_innovation_path_distinct(self):
        self.assertTrue(
            self.payload[
                "pathway_separation"
            ][
                "current_innovation_pathway_distinct"
            ]
        )

    def test_11_no_reliability_score_collapse(self):
        self.assertFalse(
            self.payload[
                "pathway_separation"
            ][
                "collapse_to_single_unexplained_reliability_score_allowed"
            ]
        )

    def test_12_alpha_validation_partition(self):
        self.assertEqual(
            self.payload[
                "persistent_health_pathway"
            ][
                "alpha_selection_partition"
            ],
            "validation",
        )

    def test_13_alpha_unselected(self):
        health = self.payload[
            "persistent_health_pathway"
        ]

        self.assertIsNone(
            health[
                "alpha_value"
            ]
        )

        self.assertFalse(
            health[
                "alpha_selected"
            ]
        )

    def test_14_no_default_alpha(self):
        self.assertFalse(
            self.payload[
                "persistent_health_pathway"
            ][
                "default_alpha_created"
            ]
        )

    def test_15_health_probability_input_absent(self):
        self.assertFalse(
            CURRENT_FACTOR_CONDITIONING_GATE
            .health_probability_input_available
        )

    def test_16_calibrated_probability_input_absent(self):
        self.assertFalse(
            CURRENT_FACTOR_CONDITIONING_GATE
            .calibrated_health_probability_input_available
        )

    def test_17_standardized_innovation_named(self):
        self.assertTrue(
            self.payload[
                "current_innovation_pathway"
            ][
                "standardized_innovation_named_by_project"
            ]
        )

    def test_18_standardized_innovation_unselected(self):
        innovation = self.payload[
            "current_innovation_pathway"
        ]

        self.assertEqual(
            innovation[
                "standardized_innovation_definition"
            ],
            "unselected",
        )

        self.assertFalse(
            innovation[
                "standardized_innovation_definition_selected"
            ]
        )

    def test_19_q_definition_unselected(self):
        innovation = self.payload[
            "current_innovation_pathway"
        ]

        self.assertEqual(
            innovation[
                "q_definition"
            ],
            "unselected",
        )

        self.assertFalse(
            innovation[
                "q_definition_selected"
            ]
        )

    def test_20_q_value_absent(self):
        self.assertIsNone(
            self.payload[
                "current_innovation_pathway"
            ][
                "q_value"
            ]
        )

    def test_21_no_default_q(self):
        self.assertFalse(
            self.payload[
                "current_innovation_pathway"
            ][
                "default_q_created"
            ]
        )

    def test_22_epsilon_policy_unselected(self):
        self.assertEqual(
            self.payload[
                "factor_scale"
            ][
                "epsilon_selection_policy"
            ],
            "unselected",
        )

    def test_23_epsilon_unselected(self):
        scale = self.payload[
            "factor_scale"
        ]

        self.assertIsNone(
            scale[
                "epsilon_value"
            ]
        )

        self.assertFalse(
            scale[
                "epsilon_selected"
            ]
        )

    def test_24_upper_clip_bound_is_authoritative_one(self):
        self.assertEqual(
            self.payload[
                "factor_scale"
            ][
                "upper_clip_bound_from_authoritative_equation"
            ],
            1,
        )

    def test_25_factor_scale_execution_blocked(self):
        self.assertFalse(
            CURRENT_FACTOR_CONDITIONING_GATE
            .factor_scale_execution_authorized
        )

    def test_26_factor_scale_guard_raises(self):
        with self.assertRaises(
            FactorConditioningContractError
        ):
            assert_factor_scale_execution_authorized()

    def test_27_information_rescaling_blocked(self):
        self.assertFalse(
            CURRENT_FACTOR_CONDITIONING_GATE
            .information_rescaling_authorized
        )

    def test_28_information_rescaling_guard_raises(self):
        with self.assertRaises(
            FactorConditioningContractError
        ):
            assert_information_rescaling_authorized()

    def test_29_covariance_inflation_blocked(self):
        self.assertFalse(
            CURRENT_FACTOR_CONDITIONING_GATE
            .covariance_inflation_authorized
        )

    def test_30_covariance_guard_raises(self):
        with self.assertRaises(
            FactorConditioningContractError
        ):
            assert_covariance_inflation_authorized()

    def test_31_phase7_numeric_auxiliary_unavailable(self):
        self.assertFalse(
            self.payload[
                "upstream_evidence_gate"
            ][
                "phase7_numeric_auxiliary_evidence_available"
            ]
        )

    def test_32_phase5_empirical_health_incomplete(self):
        self.assertFalse(
            self.payload[
                "upstream_evidence_gate"
            ][
                "phase5_empirical_health_model_complete"
            ]
        )

    def test_33_phase6_empirical_calibration_incomplete(self):
        self.assertFalse(
            self.payload[
                "upstream_evidence_gate"
            ][
                "phase6_empirical_probability_calibration_complete"
            ]
        )

    def test_34_validation_not_opened(self):
        self.assertFalse(
            self.payload[
                "selection_boundary"
            ][
                "validation_data_opened"
            ]
        )

    def test_35_confirmation_not_used(self):
        self.assertFalse(
            self.payload[
                "selection_boundary"
            ][
                "confirmation_data_used"
            ]
        )

    def test_36_confirmation_cannot_select_parameters(self):
        selection = self.payload[
            "selection_boundary"
        ]

        self.assertFalse(
            selection[
                "confirmation_may_select_alpha"
            ]
        )

        self.assertFalse(
            selection[
                "confirmation_may_select_epsilon"
            ]
        )

        self.assertFalse(
            selection[
                "confirmation_may_select_q_definition"
            ]
        )

    def test_37_no_phase9_behavior(self):
        self.assertEqual(
            set(
                self.payload[
                    "phase9_boundary"
                ].values()
            ),
            {
                False,
            },
        )

    def test_38_no_ate_rpe_or_final_score(self):
        boundary = self.payload[
            "scientific_boundary"
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

    def test_39_manifest_validates(self):
        validate_contract_manifest(
            self.payload
        )

    def test_40_parameter_injection_rejected(self):
        modified = copy.deepcopy(
            self.payload
        )

        modified[
            "persistent_health_pathway"
        ][
            "alpha_value"
        ] = 0.5

        modified[
            "persistent_health_pathway"
        ][
            "alpha_selected"
        ] = True

        with self.assertRaises(
            FactorConditioningContractError
        ):
            validate_contract_manifest(
                modified
            )


if __name__ == "__main__":
    unittest.main()
