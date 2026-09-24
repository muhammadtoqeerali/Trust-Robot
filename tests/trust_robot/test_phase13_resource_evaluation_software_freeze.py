import copy
from hashlib import sha256
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]

MANIFEST = (
    ROOT
    / "manifests"
    / "trust_robot_phase13_resource_evaluation_software_freeze_v1.json"
)


class TestPhase13ResourceEvaluationSoftwareFreeze(unittest.TestCase):

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
            "TRUST_ROBOT_PHASE13_RESOURCE_EVALUATION_SOFTWARE_FREEZE_V1",
        )

    def test_02_phase(self):
        self.assertEqual(
            self.payload[
                "checkpoint_semantics"
            ][
                "phase"
            ],
            13,
        )

    def test_03_architecture_implemented(self):
        self.assertTrue(
            self.payload[
                "checkpoint_semantics"
            ][
                "software_architecture_implemented"
            ]
        )

    def test_04_empirical_resource_evidence_incomplete(self):
        self.assertFalse(
            self.payload[
                "checkpoint_semantics"
            ][
                "empirical_resource_evidence_complete"
            ]
        )

    def test_05_measurement_policy_incomplete(self):
        self.assertFalse(
            self.payload[
                "checkpoint_semantics"
            ][
                "resource_measurement_policy_complete"
            ]
        )

    def test_06_measurement_environment_unfrozen(self):
        self.assertFalse(
            self.payload[
                "checkpoint_semantics"
            ][
                "resource_measurement_environment_frozen"
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

    def test_08_two_cost_views(self):
        self.assertEqual(
            self.payload[
                "authoritative_cost_views"
            ][
                "values"
            ],
            [
                "complete_system_cost",
                "incremental_trust_layer_overhead",
            ],
        )

    def test_09_cost_view_count(self):
        self.assertEqual(
            self.payload[
                "authoritative_cost_views"
            ][
                "count"
            ],
            2,
        )

    def test_10_cost_measurements_unavailable(self):
        self.assertFalse(
            self.payload[
                "authoritative_cost_views"
            ][
                "measurements_available"
            ]
        )

    def test_11_ten_evidence_families(self):
        self.assertEqual(
            self.payload[
                "authoritative_resource_evidence"
            ][
                "family_count"
            ],
            10,
        )

    def test_12_evidence_names_not_results(self):
        boundary = self.payload[
            "authoritative_resource_evidence"
        ]

        self.assertFalse(
            boundary[
                "families_are_measurement_results"
            ]
        )

        self.assertTrue(
            boundary[
                "families_define_required_future_evidence"
            ]
        )

    def test_13_seven_metadata_fields(self):
        self.assertEqual(
            self.payload[
                "required_measurement_metadata"
            ][
                "field_count"
            ],
            7,
        )

    def test_14_metadata_not_frozen(self):
        self.assertFalse(
            self.payload[
                "required_measurement_metadata"
            ][
                "values_currently_frozen"
            ]
        )

    def test_15_policy_all_unselected(self):
        self.assertEqual(
            set(
                self.payload[
                    "measurement_policy_boundary"
                ].values()
            ),
            {
                False,
            },
        )

    def test_16_environment_all_unfrozen(self):
        self.assertEqual(
            set(
                self.payload[
                    "measurement_environment_boundary"
                ].values()
            ),
            {
                False,
            },
        )

    def test_17_historical_policy_not_adopted(self):
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

    def test_18_host_not_target_evidence(self):
        boundary = self.payload[
            "platform_claim_boundary"
        ]

        self.assertFalse(
            boundary[
                "reference_host_equals_onboard_robot"
            ]
        )

        self.assertFalse(
            boundary[
                "reference_host_equals_stm32"
            ]
        )

        self.assertFalse(
            boundary[
                "host_measurement_may_be_relabelled_as_stm32"
            ]
        )

    def test_19_target_claim_requires_target_measurement(self):
        boundary = self.payload[
            "platform_claim_boundary"
        ]

        self.assertTrue(
            boundary[
                "target_specific_claim_requires_target_specific_measurement"
            ]
        )

        self.assertTrue(
            boundary[
                "onboard_robot_claim_requires_onboard_robot_measurement"
            ]
        )

    def test_20_rq4_phase_separation(self):
        rq4 = self.payload[
            "rq4_boundary"
        ]

        self.assertTrue(
            rq4[
                "resource_component_in_phase13"
            ]
        )

        self.assertTrue(
            rq4[
                "closed_loop_safety_component_deferred_to_phase14"
            ]
        )

    def test_21_rq4_unanswered(self):
        rq4 = self.payload[
            "rq4_boundary"
        ]

        self.assertFalse(
            rq4[
                "onboard_resource_constraints_instantiated"
            ]
        )

        self.assertFalse(
            rq4[
                "fallback_thresholds_frozen"
            ]
        )

        self.assertFalse(
            rq4[
                "resource_answer_available"
            ]
        )

    def test_22_execution_gate_closed(self):
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

    def test_23_protected_boundaries_closed(self):
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
