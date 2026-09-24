import copy
import json
from pathlib import Path
import unittest

from trust_robot.auxiliary_consistency import (
    ATTRIBUTION_BASES,
    CURRENT_AUXILIARY_GATE,
    EVIDENCE_FAMILIES,
    AttributionBasis,
    AuxiliaryConsistencyContractError,
    AuxiliaryConsistencyLifecycle,
    AuxiliaryEvidenceFamily,
    assert_consistency_execution_authorized,
    assert_source_attribution_authorized,
    attribution_basis_names,
    evidence_family_names,
    validate_contract_manifest,
)


ROOT = Path(__file__).resolve().parents[2]

CONFIG = (
    ROOT
    / "configs"
    / "trust_robot"
    / "phase7_auxiliary_consistency_contract_candidate_v1.json"
)


class TestAuxiliaryConsistencyContract(unittest.TestCase):

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
            "TRUST_ROBOT_PHASE7_AUXILIARY_CONSISTENCY_CONTRACT_V1",
        )

    def test_02_lifecycle(self):
        self.assertEqual(
            self.payload[
                "lifecycle_status"
            ],
            AuxiliaryConsistencyLifecycle
            .CONTRACT_IMPLEMENTED_MEASURES_UNSELECTED
            .value,
        )

    def test_03_phase(self):
        self.assertEqual(
            self.payload[
                "phase_scope"
            ]["phase"],
            7,
        )

    def test_04_evidence_only(self):
        self.assertTrue(
            self.payload[
                "phase_scope"
            ]["evidence_only"]
        )

    def test_05_six_evidence_families(self):
        self.assertEqual(
            len(
                EVIDENCE_FAMILIES
            ),
            6,
        )

    def test_06_exact_family_names(self):
        self.assertEqual(
            evidence_family_names(),
            (
                "visual_motion_vs_lidar_motion",
                "inertial_propagation_vs_exteroceptive_odometry",
                "temporal_pose_continuity",
                "kinematic_proprioceptive_motion",
                "platform_motion_bounds",
                "residual_histories",
            ),
        )

    def test_07_visual_lidar_family(self):
        self.assertIn(
            AuxiliaryEvidenceFamily
            .VISUAL_MOTION_VS_LIDAR_MOTION,
            EVIDENCE_FAMILIES,
        )

    def test_08_inertial_exteroceptive_family(self):
        self.assertIn(
            AuxiliaryEvidenceFamily
            .INERTIAL_PROPAGATION_VS_EXTEROCEPTIVE_ODOMETRY,
            EVIDENCE_FAMILIES,
        )

    def test_09_temporal_continuity_family(self):
        self.assertIn(
            AuxiliaryEvidenceFamily
            .TEMPORAL_POSE_CONTINUITY,
            EVIDENCE_FAMILIES,
        )

    def test_10_kinematic_family(self):
        self.assertIn(
            AuxiliaryEvidenceFamily
            .KINEMATIC_PROPRIOCEPTIVE_MOTION,
            EVIDENCE_FAMILIES,
        )

    def test_11_platform_bounds_family(self):
        self.assertIn(
            AuxiliaryEvidenceFamily
            .PLATFORM_MOTION_BOUNDS,
            EVIDENCE_FAMILIES,
        )

    def test_12_residual_history_family(self):
        self.assertIn(
            AuxiliaryEvidenceFamily
            .RESIDUAL_HISTORIES,
            EVIDENCE_FAMILIES,
        )

    def test_13_all_families_where_applicable(self):
        self.assertTrue(
            all(
                item[
                    "applicability"
                ] == "where_applicable"
                for item in self.payload[
                    "evidence_families"
                ]
            )
        )

    def test_14_no_numeric_family_measures(self):
        self.assertTrue(
            all(
                item[
                    "numeric_measure"
                ] is None
                for item in self.payload[
                    "evidence_families"
                ]
            )
        )

    def test_15_disagreement_establishes_inconsistency(self):
        self.assertTrue(
            self.payload[
                "inconsistency_semantics"
            ][
                "pairwise_disagreement_establishes_inconsistency"
            ]
        )

    def test_16_disagreement_not_source_attribution(self):
        self.assertFalse(
            self.payload[
                "inconsistency_semantics"
            ][
                "pairwise_disagreement_alone_identifies_responsible_modality"
            ]
        )

    def test_17_disagreement_not_health_label(self):
        self.assertFalse(
            self.payload[
                "inconsistency_semantics"
            ][
                "pairwise_disagreement_is_health_label"
            ]
        )

    def test_18_disagreement_not_suppression(self):
        self.assertFalse(
            self.payload[
                "inconsistency_semantics"
            ][
                "pairwise_disagreement_is_suppression_command"
            ]
        )

    def test_19_three_attribution_bases(self):
        self.assertEqual(
            len(
                ATTRIBUTION_BASES
            ),
            3,
        )

    def test_20_exact_attribution_bases(self):
        self.assertEqual(
            attribution_basis_names(),
            (
                "modality_specific_diagnostics",
                "another_sufficiently_informative_modality",
                "trusted_physical_constraint",
            ),
        )

    def test_21_modality_diagnostics_basis(self):
        self.assertIn(
            AttributionBasis
            .MODALITY_SPECIFIC_DIAGNOSTICS,
            ATTRIBUTION_BASES,
        )

    def test_22_another_modality_basis(self):
        self.assertIn(
            AttributionBasis
            .ANOTHER_SUFFICIENTLY_INFORMATIVE_MODALITY,
            ATTRIBUTION_BASES,
        )

    def test_23_physical_constraint_basis(self):
        self.assertIn(
            AttributionBasis
            .TRUSTED_PHYSICAL_CONSTRAINT,
            ATTRIBUTION_BASES,
        )

    def test_24_ambiguous_case_explicit(self):
        self.assertTrue(
            self.payload[
                "attribution_semantics"
            ][
                "ambiguous_case_must_remain_explicit"
            ]
        )

    def test_25_no_fabricated_confident_label(self):
        self.assertFalse(
            self.payload[
                "attribution_semantics"
            ][
                "fabricated_confident_label_allowed"
            ]
        )

    def test_26_numeric_measure_unselected(self):
        self.assertFalse(
            CURRENT_AUXILIARY_GATE
            .numeric_consistency_measure_selected
        )

    def test_27_temporal_tolerance_unselected(self):
        self.assertFalse(
            CURRENT_AUXILIARY_GATE
            .temporal_tolerance_selected
        )

    def test_28_time_offset_unselected(self):
        self.assertFalse(
            CURRENT_AUXILIARY_GATE
            .time_offset_selected
        )

    def test_29_interpolation_unselected(self):
        self.assertFalse(
            CURRENT_AUXILIARY_GATE
            .interpolation_selected
        )

    def test_30_transform_unselected(self):
        self.assertFalse(
            CURRENT_AUXILIARY_GATE
            .cross_modal_transform_selected
        )

    def test_31_kinematic_model_unselected(self):
        self.assertFalse(
            CURRENT_AUXILIARY_GATE
            .kinematic_model_selected
        )

    def test_32_platform_bound_unselected(self):
        self.assertFalse(
            CURRENT_AUXILIARY_GATE
            .trusted_platform_motion_bound_selected
        )

    def test_33_residual_history_definition_unselected(self):
        self.assertFalse(
            CURRENT_AUXILIARY_GATE
            .residual_history_definition_selected
        )

    def test_34_execution_guard_raises(self):
        with self.assertRaises(
            AuxiliaryConsistencyContractError
        ):
            assert_consistency_execution_authorized()

    def test_35_attribution_guard_raises(self):
        with self.assertRaises(
            AuxiliaryConsistencyContractError
        ):
            assert_source_attribution_authorized()

    def test_36_ood_not_in_scope(self):
        self.assertFalse(
            self.payload[
                "phase_scope"
            ][
                "ood_method_in_scope"
            ]
        )

    def test_37_gnss_remains_optional(self):
        self.assertTrue(
            self.payload[
                "phase_scope"
            ][
                "gnss_remains_optional"
            ]
        )

    def test_38_phase8_and_phase9_not_implemented(self):
        self.assertFalse(
            self.payload[
                "phase_scope"
            ][
                "phase8_factor_conditioning_in_scope"
            ]
        )

        self.assertFalse(
            self.payload[
                "phase_scope"
            ][
                "phase9_suppression_recovery_status_in_scope"
            ]
        )

    def test_39_manifest_validates(self):
        validate_contract_manifest(
            self.payload
        )

    def test_40_numeric_measure_injection_rejected(self):
        modified = copy.deepcopy(
            self.payload
        )

        modified[
            "evidence_families"
        ][0][
            "numeric_measure"
        ] = "invented_metric"

        modified[
            "evidence_families"
        ][0][
            "numeric_measure_selected"
        ] = True

        with self.assertRaises(
            AuxiliaryConsistencyContractError
        ):
            validate_contract_manifest(
                modified
            )


if __name__ == "__main__":
    unittest.main()
