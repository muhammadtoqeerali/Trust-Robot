import copy
from hashlib import sha256
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]

MANIFEST = (
    ROOT
    / "manifests"
    / "trust_robot_phase7_auxiliary_consistency_software_freeze_v1.json"
)


class TestPhase7AuxiliaryConsistencySoftwareFreeze(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(
            MANIFEST.read_text(
                encoding="utf-8"
            )
        )

    def test_01_schema(self):
        self.assertEqual(
            self.payload[
                "schema"
            ],
            "TRUST_ROBOT_PHASE7_AUXILIARY_CONSISTENCY_SOFTWARE_FREEZE_V1",
        )

    def test_02_phase(self):
        self.assertEqual(
            self.payload[
                "checkpoint_semantics"
            ][
                "phase"
            ],
            7,
        )

    def test_03_software_architecture_implemented(self):
        self.assertTrue(
            self.payload[
                "checkpoint_semantics"
            ][
                "software_architecture_implemented"
            ]
        )

    def test_04_registry_implemented(self):
        self.assertTrue(
            self.payload[
                "checkpoint_semantics"
            ][
                "six_family_prerequisite_registry_implemented"
            ]
        )

    def test_05_empirical_consistency_incomplete(self):
        self.assertFalse(
            self.payload[
                "checkpoint_semantics"
            ][
                "empirical_consistency_evidence_complete"
            ]
        )

    def test_06_no_numeric_execution(self):
        self.assertFalse(
            self.payload[
                "checkpoint_semantics"
            ][
                "numeric_consistency_execution_performed"
            ]
        )

    def test_07_no_empirical_completion_claim(self):
        self.assertFalse(
            self.payload[
                "checkpoint_semantics"
            ][
                "empirical_completion_claimed"
            ]
        )

    def test_08_confirmation_closed(self):
        self.assertTrue(
            self.payload[
                "checkpoint_semantics"
            ][
                "confirmation_remains_closed"
            ]
        )

    def test_09_six_families(self):
        self.assertEqual(
            len(
                self.payload[
                    "authoritative_evidence_families"
                ]
            ),
            6,
        )

    def test_10_exact_family_order(self):
        self.assertEqual(
            self.payload[
                "authoritative_evidence_families"
            ],
            [
                "visual_motion_vs_lidar_motion",
                "inertial_propagation_vs_exteroceptive_odometry",
                "temporal_pose_continuity",
                "kinematic_proprioceptive_motion",
                "platform_motion_bounds",
                "residual_histories",
            ],
        )

    def test_11_zero_execution_ready(self):
        self.assertEqual(
            self.payload[
                "prerequisite_registry"
            ][
                "execution_ready_family_count"
            ],
            0,
        )

    def test_12_zero_numeric_measures(self):
        self.assertEqual(
            self.payload[
                "prerequisite_registry"
            ][
                "numeric_measure_selected_family_count"
            ],
            0,
        )

    def test_13_attribution_blocked(self):
        self.assertFalse(
            self.payload[
                "prerequisite_registry"
            ][
                "source_attribution_authorized"
            ]
        )

    def test_14_pairwise_disagreement_not_attribution(self):
        self.assertFalse(
            self.payload[
                "inconsistency_and_attribution_semantics"
            ][
                "pairwise_disagreement_alone_identifies_responsible_modality"
            ]
        )

    def test_15_ambiguity_explicit(self):
        self.assertTrue(
            self.payload[
                "inconsistency_and_attribution_semantics"
            ][
                "ambiguous_case_must_remain_explicit"
            ]
        )

    def test_16_no_sync_selection(self):
        self.assertFalse(
            self.payload[
                "current_prerequisite_gate"
            ][
                "synchronization_selected"
            ]
        )

    def test_17_no_alignment_authorization(self):
        self.assertFalse(
            self.payload[
                "current_prerequisite_gate"
            ][
                "alignment_execution_authorized"
            ]
        )

    def test_18_no_kinematic_model(self):
        self.assertFalse(
            self.payload[
                "current_prerequisite_gate"
            ][
                "kinematic_model_selected"
            ]
        )

    def test_19_no_platform_bound(self):
        self.assertFalse(
            self.payload[
                "current_prerequisite_gate"
            ][
                "trusted_platform_motion_bound_selected"
            ]
        )

    def test_20_no_residual_history_definition(self):
        self.assertFalse(
            self.payload[
                "current_prerequisite_gate"
            ][
                "residual_history_definition_selected"
            ]
        )

    def test_21_no_numeric_adapter(self):
        self.assertFalse(
            self.payload[
                "implementation_decision"
            ][
                "new_numeric_consistency_adapter_implemented"
            ]
        )

    def test_22_no_phase8_or_phase9_behavior(self):
        boundary = self.payload[
            "protected_scientific_boundaries"
        ]

        self.assertFalse(
            boundary[
                "phase8_factor_conditioning_implemented"
            ]
        )

        self.assertFalse(
            boundary[
                "phase9_suppression_recovery_status_implemented"
            ]
        )

    def test_23_phase8_cannot_assume_aux_evidence(self):
        self.assertFalse(
            self.payload[
                "next_phase_policy"
            ][
                "phase8_may_assume_phase7_numeric_consistency_evidence_available"
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
