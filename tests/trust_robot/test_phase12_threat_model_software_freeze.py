import copy
from hashlib import sha256
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]

MANIFEST = (
    ROOT
    / "manifests"
    / "trust_robot_phase12_threat_model_software_freeze_v1.json"
)


class TestPhase12ThreatModelSoftwareFreeze(unittest.TestCase):

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
            "TRUST_ROBOT_PHASE12_THREAT_MODEL_SOFTWARE_FREEZE_V1",
        )

    def test_02_phase(self):
        self.assertEqual(
            self.payload[
                "checkpoint_semantics"
            ][
                "phase"
            ],
            12,
        )

    def test_03_architecture_implemented(self):
        self.assertTrue(
            self.payload[
                "checkpoint_semantics"
            ][
                "software_architecture_implemented"
            ]
        )

    def test_04_empirical_attack_evidence_incomplete(self):
        self.assertFalse(
            self.payload[
                "checkpoint_semantics"
            ][
                "empirical_attack_evidence_complete"
            ]
        )

    def test_05_zero_instantiated_protocols(self):
        self.assertEqual(
            self.payload[
                "checkpoint_semantics"
            ][
                "instantiated_attack_protocol_count"
            ],
            0,
        )

    def test_06_rq3_unanswered(self):
        self.assertFalse(
            self.payload[
                "checkpoint_semantics"
            ][
                "rq3_answer_available"
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

    def test_08_planned_attack_count(self):
        self.assertEqual(
            self.payload[
                "planned_attack_taxonomy"
            ][
                "identity_count"
            ],
            6,
        )

    def test_09_planned_attacks_exact(self):
        self.assertEqual(
            self.payload[
                "planned_attack_taxonomy"
            ][
                "identities"
            ],
            [
                "false-data injection / spoofing",
                "bounded adversarial image or point-cloud perturbation",
                "replay",
                "timestamp manipulation",
                "coordinated two-modality corruption",
                "adaptive white-box digital evasion",
            ],
        )

    def test_10_taxonomy_not_protocol(self):
        self.assertFalse(
            self.payload[
                "planned_attack_taxonomy"
            ][
                "taxonomy_identity_is_executable_attack_protocol"
            ]
        )

    def test_11_required_field_count(self):
        self.assertEqual(
            self.payload[
                "attack_protocol_schema"
            ][
                "required_field_count"
            ],
            8,
        )

    def test_12_zero_protocol_instances(self):
        schema = self.payload[
            "attack_protocol_schema"
        ]

        self.assertEqual(
            schema[
                "instantiated_protocols"
            ],
            [],
        )

        self.assertEqual(
            schema[
                "instantiated_protocol_count"
            ],
            0,
        )

    def test_13_rq3_classes(self):
        self.assertEqual(
            self.payload[
                "rq3_boundary"
            ][
                "attack_classes"
            ],
            [
                "single_sensor",
                "coordinated",
                "adaptive",
            ],
        )

    def test_14_identifiability_required(self):
        self.assertTrue(
            self.payload[
                "rq3_boundary"
            ][
                "identifiability_assumptions_required"
            ]
        )

    def test_15_rq3_operational_definitions_unselected(self):
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

    def test_16_phase7_numeric_auxiliary_unavailable(self):
        self.assertFalse(
            self.payload[
                "rq3_boundary"
            ][
                "phase7_numeric_auxiliary_consistency_available"
            ]
        )

    def test_17_no_threat_model_selected(self):
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

    def test_18_no_writable_sources_selected(self):
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

    def test_19_operating_points_unselected(self):
        boundary = self.payload[
            "attack_operating_point_boundary"
        ]

        for key in (
            "attack_duration",
            "attack_budget",
            "attack_magnitude",
            "attack_rate",
            "attack_norm",
            "attack_schedule",
            "attack_seed_schedule",
            "attack_threshold",
        ):
            self.assertIsNone(
                boundary[
                    key
                ]
            )

    def test_20_preheldout_freeze_rule(self):
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

    def test_21_phase3_reuse_closed(self):
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

    def test_22_phase10_reuse_closed(self):
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

    def test_23_execution_and_protected_boundaries_closed(self):
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

        self.assertEqual(
            set(
                self.payload[
                    "protected_boundaries"
                ].values()
            ),
            {
                False,
            },
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
