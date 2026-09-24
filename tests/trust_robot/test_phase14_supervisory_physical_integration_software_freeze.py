import copy
from hashlib import sha256
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]

MANIFEST = (
    ROOT
    / "manifests"
    / "trust_robot_phase14_supervisory_physical_integration_software_freeze_v1.json"
)


class TestPhase14SupervisoryPhysicalIntegrationSoftwareFreeze(unittest.TestCase):

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
            "TRUST_ROBOT_PHASE14_SUPERVISORY_PHYSICAL_INTEGRATION_SOFTWARE_FREEZE_V1",
        )

    def test_02_phase(self):
        self.assertEqual(
            self.payload[
                "checkpoint_semantics"
            ][
                "phase"
            ],
            14,
        )

    def test_03_architecture_implemented(self):
        self.assertTrue(
            self.payload[
                "checkpoint_semantics"
            ][
                "software_architecture_implemented"
            ]
        )

    def test_04_empirical_physical_evidence_incomplete(self):
        self.assertFalse(
            self.payload[
                "checkpoint_semantics"
            ][
                "empirical_physical_evidence_complete"
            ]
        )

    def test_05_final_confirmation_closed(self):
        semantics = self.payload[
            "checkpoint_semantics"
        ]

        self.assertTrue(
            semantics[
                "confirmation_remains_closed"
            ]
        )

        self.assertFalse(
            semantics[
                "final_confirmation_execution_authorized"
            ]
        )

    def test_06_rule_based_supervisor_separate(self):
        boundary = self.payload[
            "supervisor_architecture"
        ]

        self.assertFalse(
            boundary[
                "learned_health_model_is_robot_controller"
            ]
        )

        self.assertTrue(
            boundary[
                "separate_rule_based_supervisory_layer_required"
            ]
        )

    def test_07_physical_experiments_guarded(self):
        boundary = self.payload[
            "supervisor_architecture"
        ]

        self.assertTrue(
            boundary[
                "physical_experiments_must_remain_guarded"
            ]
        )

        self.assertTrue(
            boundary[
                "physical_experiments_must_be_progressively_validated"
            ]
        )

    def test_08_six_supervisor_inputs(self):
        self.assertEqual(
            self.payload[
                "authoritative_supervisor_inputs"
            ][
                "identity_count"
            ],
            6,
        )

    def test_09_supervisor_inputs_not_commands(self):
        boundary = self.payload[
            "authoritative_supervisor_inputs"
        ]

        self.assertFalse(
            boundary[
                "identities_imply_runtime_readiness"
            ]
        )

        self.assertFalse(
            boundary[
                "identities_are_robot_commands"
            ]
        )

    def test_10_four_policy_comparisons(self):
        self.assertEqual(
            self.payload[
                "planned_policy_comparisons"
            ][
                "identity_count"
            ],
            4,
        )

    def test_11_policy_names_not_operational_semantics(self):
        boundary = self.payload[
            "planned_policy_comparisons"
        ]

        self.assertFalse(
            boundary[
                "identities_are_selected_operational_policy"
            ]
        )

        self.assertFalse(
            boundary[
                "identities_define_robot_command_semantics"
            ]
        )

    def test_12_oracle_health_comparison_only(self):
        boundary = self.payload[
            "planned_policy_comparisons"
        ]

        self.assertFalse(
            boundary[
                "oracle_health_is_runtime_available_signal"
            ]
        )

        self.assertTrue(
            boundary[
                "oracle_health_role_is_planned_comparison_only"
            ]
        )

    def test_13_action_semantics_unselected(self):
        self.assertEqual(
            set(
                self.payload[
                    "robot_action_semantics_boundary"
                ].values()
            ),
            {
                False,
            },
        )

    def test_14_platform_role_and_readiness(self):
        boundary = self.payload[
            "physical_platform_boundary"
        ]

        self.assertEqual(
            boundary[
                "eventual_platform_role"
            ],
            "local_quadruped_robot",
        )

        self.assertEqual(
            boundary[
                "provisional_dataset_identity"
            ],
            "KIOS_QUADRUPED",
        )

        self.assertEqual(
            boundary[
                "local_readiness"
            ],
            "not_collected",
        )

    def test_15_platform_evidence_unfrozen(self):
        boundary = self.payload[
            "physical_platform_boundary"
        ]

        for key, value in boundary.items():
            if key in {
                "eventual_platform_role",
                "provisional_dataset_identity",
                "local_readiness",
            }:
                continue

            self.assertFalse(
                value
            )

    def test_16_physical_partition_separation(self):
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

    def test_17_heldout_physical_selects_nothing(self):
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

    def test_18_fallback_threshold_rule(self):
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

    def test_19_final_physical_and_confirmation_cannot_select_threshold(self):
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

    def test_20_physical_safety_metrics_unselected(self):
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

    def test_21_upstream_evidence_unavailable(self):
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

    def test_22_execution_and_protected_boundaries_closed(self):
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

    def test_23_phase15_is_preparation_only(self):
        boundary = self.payload[
            "next_phase_policy"
        ]

        self.assertTrue(
            boundary[
                "phase15_software_preparation_may_proceed"
            ]
        )

        self.assertTrue(
            boundary[
                "deferred_phase5_through_phase14_empirical_obligations_remain_binding"
            ]
        )

        self.assertFalse(
            boundary[
                "phase15_may_assume_phase14_physical_tests_executed"
            ]
        )

        self.assertFalse(
            boundary[
                "phase15_may_assume_closed_loop_safety_answer_available"
            ]
        )

        self.assertFalse(
            boundary[
                "phase15_may_assume_full_rq4_answer_available"
            ]
        )

        self.assertFalse(
            boundary[
                "final_confirmation_execution_authorized"
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
