import copy
import json
from pathlib import Path
import unittest

from trust_robot.attack_threat_model import (
    CURRENT_PHASE12_GATE,
    ThreatModelContractError,
    Phase12Lifecycle,
    assert_attack_evaluation_authorized,
    assert_physical_attack_execution_authorized,
    assert_synthetic_attack_execution_authorized,
    planned_attack_identities,
    required_attack_protocol_fields,
    rq3_attack_classes,
    validate_contract_manifest,
)


ROOT = Path(__file__).resolve().parents[2]

CONFIG = (
    ROOT
    / "configs"
    / "trust_robot"
    / "phase12_threat_model_contract_candidate_v1.json"
)


class TestAttackThreatModelContract(unittest.TestCase):

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
            "TRUST_ROBOT_PHASE12_THREAT_MODEL_CONTRACT_V1",
        )

    def test_02_lifecycle(self):
        self.assertEqual(
            self.payload["lifecycle_status"],
            Phase12Lifecycle
            .CONTRACT_IMPLEMENTED_PROTOCOLS_UNINSTANTIATED
            .value,
        )

    def test_03_phase(self):
        self.assertEqual(
            self.payload[
                "phase_scope"
            ][
                "phase"
            ],
            12,
        )

    def test_04_scope(self):
        self.assertEqual(
            self.payload[
                "phase_scope"
            ][
                "name"
            ],
            "explicit_attack_evaluation",
        )

    def test_05_evidence_role(self):
        self.assertEqual(
            self.payload[
                "phase_scope"
            ][
                "evidence_role"
            ],
            "threat_model_bounded_RQ3_evidence",
        )

    def test_06_fault_attack_separate(self):
        self.assertTrue(
            self.payload[
                "evidence_category_separation"
            ][
                "fault_evaluation_separate_from_attack_evaluation"
            ]
        )

    def test_07_environment_attack_separate(self):
        self.assertTrue(
            self.payload[
                "evidence_category_separation"
            ][
                "environmental_nonattack_degradation_separate_from_attack_evaluation"
            ]
        )

    def test_08_controlled_fault_truth_not_attack_truth(self):
        self.assertFalse(
            self.payload[
                "evidence_category_separation"
            ][
                "controlled_fault_truth_is_attack_truth"
            ]
        )

    def test_09_six_planned_attacks(self):
        self.assertEqual(
            len(
                planned_attack_identities()
            ),
            6,
        )

    def test_10_planned_attack_identity_exact(self):
        self.assertEqual(
            planned_attack_identities(),
            (
                "false-data injection / spoofing",
                "bounded adversarial image or point-cloud perturbation",
                "replay",
                "timestamp manipulation",
                "coordinated two-modality corruption",
                "adaptive white-box digital evasion",
            ),
        )

    def test_11_taxonomy_not_threat_model(self):
        self.assertFalse(
            self.payload[
                "planned_attack_taxonomy"
            ][
                "taxonomy_is_selected_threat_model"
            ]
        )

    def test_12_taxonomy_not_protocol(self):
        self.assertFalse(
            self.payload[
                "planned_attack_taxonomy"
            ][
                "taxonomy_identity_is_executable_attack_protocol"
            ]
        )

    def test_13_eight_required_protocol_fields(self):
        self.assertEqual(
            len(
                required_attack_protocol_fields()
            ),
            8,
        )

    def test_14_protocol_fields_exact(self):
        self.assertEqual(
            required_attack_protocol_fields(),
            (
                "attacker knowledge",
                "writable modality/modalities",
                "writable fields",
                "attack duration",
                "magnitude/rate/norm budget",
                "objective",
                "protected-source assumptions",
                "identifiability assumptions",
            ),
        )

    def test_15_zero_instantiated_protocols(self):
        protocol = self.payload[
            "attack_protocol_schema"
        ]

        self.assertEqual(
            protocol[
                "instantiated_protocols"
            ],
            [],
        )

        self.assertEqual(
            protocol[
                "instantiated_protocol_count"
            ],
            0,
        )

    def test_16_explicit_threat_model_required(self):
        self.assertTrue(
            self.payload[
                "attack_protocol_schema"
            ][
                "complete_explicit_threat_model_required_before_execution"
            ]
        )

    def test_17_rq3_classes_exact(self):
        self.assertEqual(
            rq3_attack_classes(),
            (
                "single_sensor",
                "coordinated",
                "adaptive",
            ),
        )

    def test_18_rq3_identifiability_required(self):
        self.assertTrue(
            self.payload[
                "rq3_boundary"
            ][
                "identifiability_assumptions_required"
            ]
        )

    def test_19_rq3_classes_unselected(self):
        rq3 = self.payload[
            "rq3_boundary"
        ]

        self.assertFalse(
            rq3[
                "single_sensor_operational_definition_selected"
            ]
        )

        self.assertFalse(
            rq3[
                "coordinated_operational_definition_selected"
            ]
        )

        self.assertFalse(
            rq3[
                "adaptive_operational_definition_selected"
            ]
        )

    def test_20_rq3_not_executable(self):
        rq3 = self.payload[
            "rq3_boundary"
        ]

        self.assertFalse(
            rq3[
                "rq3_executable"
            ]
        )

        self.assertFalse(
            rq3[
                "rq3_answer_available"
            ]
        )

    def test_21_source_attribution_closed(self):
        self.assertEqual(
            set(
                self.payload[
                    "source_attribution_boundary"
                ].values()
            ),
            {
                False,
            },
        )

    def test_22_no_threat_model_selected(self):
        boundary = self.payload[
            "selection_boundary"
        ]

        self.assertIsNone(
            boundary[
                "threat_model"
            ]
        )

        self.assertFalse(
            boundary[
                "threat_model_selected"
            ]
        )

    def test_23_no_attacker_knowledge_selected(self):
        boundary = self.payload[
            "selection_boundary"
        ]

        self.assertIsNone(
            boundary[
                "attacker_knowledge_model"
            ]
        )

        self.assertFalse(
            boundary[
                "attacker_knowledge_model_selected"
            ]
        )

    def test_24_no_writable_modalities_fields_selected(self):
        boundary = self.payload[
            "selection_boundary"
        ]

        self.assertEqual(
            boundary[
                "writable_modalities"
            ],
            [],
        )

        self.assertEqual(
            boundary[
                "writable_fields"
            ],
            [],
        )

    def test_25_no_identifiability_assumptions_selected(self):
        boundary = self.payload[
            "selection_boundary"
        ]

        self.assertEqual(
            boundary[
                "identifiability_assumptions"
            ],
            [],
        )

        self.assertFalse(
            boundary[
                "identifiability_assumptions_selected"
            ]
        )

    def test_26_no_attack_family_selected(self):
        boundary = self.payload[
            "selection_boundary"
        ]

        self.assertIsNone(
            boundary[
                "attack_family"
            ]
        )

        self.assertFalse(
            boundary[
                "attack_family_selected"
            ]
        )

    def test_27_no_attack_budget_selected(self):
        boundary = self.payload[
            "attack_operating_point_boundary"
        ]

        self.assertIsNone(
            boundary[
                "attack_budget"
            ]
        )

        self.assertFalse(
            boundary[
                "attack_budget_selected"
            ]
        )

    def test_28_no_attack_duration_selected(self):
        boundary = self.payload[
            "attack_operating_point_boundary"
        ]

        self.assertIsNone(
            boundary[
                "attack_duration"
            ]
        )

        self.assertFalse(
            boundary[
                "attack_duration_selected"
            ]
        )

    def test_29_no_attack_schedule_selected(self):
        boundary = self.payload[
            "attack_operating_point_boundary"
        ]

        self.assertIsNone(
            boundary[
                "attack_schedule"
            ]
        )

        self.assertFalse(
            boundary[
                "attack_schedule_selected"
            ]
        )

    def test_30_budget_freeze_rule(self):
        boundary = self.payload[
            "attack_operating_point_boundary"
        ]

        self.assertTrue(
            boundary[
                "budgets_and_thresholds_must_be_fixed_before_held_out_testing"
            ]
        )

        self.assertFalse(
            boundary[
                "held_out_testing_may_select_attack_budget"
            ]
        )

    def test_31_native_phase3_exact(self):
        self.assertEqual(
            self.payload[
                "phase3_reuse_boundary"
            ][
                "currently_frozen_native_families"
            ],
            [
                "EVENT_GAP",
                "EVENT_REPEAT",
                "TIMESTAMP_STEP_SHIFT",
            ],
        )

    def test_32_phase3_future_attack_candidates_not_implemented(self):
        self.assertEqual(
            self.payload[
                "phase3_reuse_boundary"
            ][
                "future_attack_related_candidate_mechanisms_not_implemented"
            ],
            [
                "lidar_geometric_perturbation",
                "replay",
                "calibration_perturbation",
                "threat_model_bounded_spoofing",
            ],
        )

    def test_33_phase3_reuse_not_authorized(self):
        boundary = self.payload[
            "phase3_reuse_boundary"
        ]

        self.assertFalse(
            boundary[
                "phase3_corruption_reuse_authorized"
            ]
        )

        self.assertFalse(
            boundary[
                "native_phase3_family_execution_authorized_for_phase12"
            ]
        )

    def test_34_phase10_reuse_closed(self):
        self.assertEqual(
            set(
                self.payload[
                    "phase10_reuse_boundary"
                ].values()
            ),
            {
                False,
            },
        )

    def test_35_synthetic_attack_guard_raises(self):
        with self.assertRaises(
            ThreatModelContractError
        ):
            assert_synthetic_attack_execution_authorized()

    def test_36_physical_attack_guard_raises(self):
        with self.assertRaises(
            ThreatModelContractError
        ):
            assert_physical_attack_execution_authorized()

    def test_37_attack_evaluation_guard_raises(self):
        with self.assertRaises(
            ThreatModelContractError
        ):
            assert_attack_evaluation_authorized()

    def test_38_execution_gate_closed(self):
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

    def test_39_manifest_validates(self):
        validate_contract_manifest(
            self.payload
        )

    def test_40_instantiated_protocol_rejected(self):
        modified = copy.deepcopy(
            self.payload
        )

        modified[
            "attack_protocol_schema"
        ][
            "instantiated_protocols"
        ] = [
            {
                "attack": "replay",
            }
        ]

        modified[
            "attack_protocol_schema"
        ][
            "instantiated_protocol_count"
        ] = 1

        with self.assertRaises(
            ThreatModelContractError
        ):
            validate_contract_manifest(
                modified
            )


if __name__ == "__main__":
    unittest.main()
