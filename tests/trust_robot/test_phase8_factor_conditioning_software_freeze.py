import copy
from hashlib import sha256
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]

MANIFEST = (
    ROOT
    / "manifests"
    / "trust_robot_phase8_factor_conditioning_software_freeze_v1.json"
)


class TestPhase8FactorConditioningSoftwareFreeze(unittest.TestCase):

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
            "TRUST_ROBOT_PHASE8_FACTOR_CONDITIONING_SOFTWARE_FREEZE_V1",
        )

    def test_02_phase(self):
        self.assertEqual(
            self.payload[
                "checkpoint_semantics"
            ][
                "phase"
            ],
            8,
        )

    def test_03_architecture_implemented(self):
        self.assertTrue(
            self.payload[
                "checkpoint_semantics"
            ][
                "software_architecture_implemented"
            ]
        )

    def test_04_numeric_incomplete(self):
        self.assertFalse(
            self.payload[
                "checkpoint_semantics"
            ][
                "numeric_factor_conditioning_complete"
            ]
        )

    def test_05_numeric_not_executed(self):
        self.assertFalse(
            self.payload[
                "checkpoint_semantics"
            ][
                "numeric_factor_conditioning_executed"
            ]
        )

    def test_06_estimator_unmodified(self):
        self.assertFalse(
            self.payload[
                "checkpoint_semantics"
            ][
                "estimator_factor_modified"
            ]
        )

    def test_07_confirmation_closed(self):
        self.assertTrue(
            self.payload[
                "checkpoint_semantics"
            ][
                "confirmation_remains_closed"
            ]
        )

    def test_08_health_equation(self):
        self.assertEqual(
            self.payload[
                "authoritative_equations"
            ][
                "health_weight"
            ],
            "w_m(t) = p_H_m(t) + alpha_m * p_D_m(t)",
        )

    def test_09_scale_equation(self):
        self.assertEqual(
            self.payload[
                "authoritative_equations"
            ][
                "factor_scale"
            ],
            "lambda_m = clip(w_m * q_m, epsilon_m, 1)",
        )

    def test_10_pathways_separate(self):
        separation = self.payload[
            "pathway_separation"
        ]

        self.assertTrue(
            separation[
                "persistent_health_pathway"
            ]
        )

        self.assertTrue(
            separation[
                "current_innovation_pathway"
            ]
        )

    def test_11_no_reliability_collapse(self):
        self.assertFalse(
            self.payload[
                "pathway_separation"
            ][
                "collapse_to_single_unexplained_reliability_score_allowed"
            ]
        )

    def test_12_alpha_validation_only(self):
        self.assertEqual(
            self.payload[
                "parameter_semantics"
            ][
                "alpha_selection_partition"
            ],
            "validation",
        )

    def test_13_alpha_unselected(self):
        self.assertIsNone(
            self.payload[
                "parameter_semantics"
            ][
                "alpha_value"
            ]
        )

        self.assertFalse(
            self.payload[
                "current_numeric_gate"
            ][
                "alpha_selected"
            ]
        )

    def test_14_innovation_unselected(self):
        self.assertEqual(
            self.payload[
                "parameter_semantics"
            ][
                "standardized_innovation_definition"
            ],
            "unselected",
        )

    def test_15_q_unselected(self):
        self.assertEqual(
            self.payload[
                "parameter_semantics"
            ][
                "q_definition"
            ],
            "unselected",
        )

        self.assertIsNone(
            self.payload[
                "parameter_semantics"
            ][
                "q_value"
            ]
        )

    def test_16_epsilon_unselected(self):
        self.assertEqual(
            self.payload[
                "parameter_semantics"
            ][
                "epsilon_selection_policy"
            ],
            "unselected",
        )

        self.assertIsNone(
            self.payload[
                "parameter_semantics"
            ][
                "epsilon_value"
            ]
        )

    def test_17_clip_upper_one(self):
        self.assertEqual(
            self.payload[
                "parameter_semantics"
            ][
                "upper_clip_bound_from_authoritative_equation"
            ],
            1,
        )

    def test_18_factor_scale_blocked(self):
        self.assertFalse(
            self.payload[
                "current_numeric_gate"
            ][
                "factor_scale_execution_authorized"
            ]
        )

    def test_19_information_rescaling_blocked(self):
        self.assertFalse(
            self.payload[
                "current_numeric_gate"
            ][
                "information_rescaling_authorized"
            ]
        )

    def test_20_covariance_inflation_blocked(self):
        self.assertFalse(
            self.payload[
                "current_numeric_gate"
            ][
                "covariance_inflation_authorized"
            ]
        )

    def test_21_no_phase9_behavior(self):
        self.assertFalse(
            self.payload[
                "protected_boundaries"
            ][
                "phase9_suppression_recovery_status_implemented"
            ]
        )

    def test_22_no_validation_or_confirmation(self):
        boundary = self.payload[
            "protected_boundaries"
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

    def test_23_phase9_cannot_assume_scale(self):
        self.assertFalse(
            self.payload[
                "next_phase_policy"
            ][
                "phase9_may_assume_phase8_numeric_factor_scale_available"
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
