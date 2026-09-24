import copy
from hashlib import sha256
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]

MANIFEST = (
    ROOT
    / "manifests"
    / "trust_robot_phase10_controlled_fault_ablation_software_freeze_v1.json"
)


class TestPhase10ControlledFaultAblationSoftwareFreeze(unittest.TestCase):

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
            "TRUST_ROBOT_PHASE10_CONTROLLED_FAULT_ABLATION_SOFTWARE_FREEZE_V1",
        )

    def test_02_phase(self):
        self.assertEqual(
            self.payload[
                "checkpoint_semantics"
            ][
                "phase"
            ],
            10,
        )

    def test_03_architecture_implemented(self):
        self.assertTrue(
            self.payload[
                "checkpoint_semantics"
            ][
                "software_architecture_implemented"
            ]
        )

    def test_04_empirical_incomplete(self):
        self.assertFalse(
            self.payload[
                "checkpoint_semantics"
            ][
                "empirical_controlled_fault_evidence_complete"
            ]
        )

    def test_05_rq1_unanswered(self):
        self.assertFalse(
            self.payload[
                "checkpoint_semantics"
            ][
                "rq1_answer_available"
            ]
        )

    def test_06_rq2_unanswered(self):
        self.assertFalse(
            self.payload[
                "checkpoint_semantics"
            ][
                "rq2_answer_available"
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

    def test_08_scope(self):
        self.assertEqual(
            self.payload[
                "phase_scope"
            ][
                "name"
            ],
            "causal_ablations_and_controlled_faults",
        )

    def test_09_evidence_role(self):
        self.assertEqual(
            self.payload[
                "phase_scope"
            ][
                "evidence_role"
            ],
            "same_backbone_RQ1_RQ2_evidence",
        )

    def test_10_same_backbone_unselected(self):
        boundary = self.payload[
            "same_backbone_boundary"
        ]

        self.assertEqual(
            boundary[
                "operational_definition"
            ],
            "unselected",
        )

        self.assertFalse(
            boundary[
                "operational_definition_selected"
            ]
        )

    def test_11_ablation_variants_unselected(self):
        boundary = self.payload[
            "same_backbone_boundary"
        ]

        self.assertEqual(
            boundary[
                "ablation_variants"
            ],
            [],
        )

        self.assertFalse(
            boundary[
                "ablation_variants_selected"
            ]
        )

    def test_12_rq1_proxy_unselected(self):
        rq1 = self.payload[
            "rq1_boundary"
        ]

        self.assertEqual(
            rq1[
                "proxy_reliability_definition"
            ],
            "unselected",
        )

        self.assertFalse(
            rq1[
                "proxy_reliability_definition_selected"
            ]
        )

    def test_13_rq1_not_executable(self):
        self.assertFalse(
            self.payload[
                "rq1_boundary"
            ][
                "rq1_executable"
            ]
        )

    def test_14_rq2_not_executable(self):
        self.assertFalse(
            self.payload[
                "rq2_boundary"
            ][
                "rq2_executable"
            ]
        )

    def test_15_native_family_set(self):
        self.assertEqual(
            self.payload[
                "native_phase3_binding"
            ][
                "families"
            ],
            [
                "EVENT_GAP",
                "EVENT_REPEAT",
                "TIMESTAMP_STEP_SHIFT",
            ],
        )

    def test_16_native_execution_blocked(self):
        self.assertFalse(
            self.payload[
                "native_phase3_binding"
            ][
                "execution_authorized"
            ]
        )

    def test_17_synthetic_truth_boundaries(self):
        native = self.payload[
            "native_phase3_binding"
        ]

        self.assertFalse(
            native[
                "synthetic_truth_is_health_label"
            ]
        )

        self.assertFalse(
            native[
                "synthetic_truth_is_physical_fault_proof"
            ]
        )

        self.assertFalse(
            native[
                "synthetic_truth_is_runtime_causal_evidence"
            ]
        )

    def test_18_numeric_fault_parameters_unselected(self):
        fault = self.payload[
            "fault_parameter_boundary"
        ]

        for key in (
            "numeric_fault_severity",
            "severity_grid",
            "attack_budget",
            "fault_schedule",
            "fault_duration",
            "fault_probability",
            "partition_seed_schedule",
        ):
            self.assertIsNone(
                fault[
                    key
                ]
            )

    def test_19_fault_selection_flags_false(self):
        fault = self.payload[
            "fault_parameter_boundary"
        ]

        for key in (
            "numeric_fault_severity_selected",
            "severity_grid_selected",
            "attack_budget_selected",
            "fault_schedule_selected",
            "fault_duration_selected",
            "fault_probability_selected",
            "partition_seed_schedule_selected",
        ):
            self.assertFalse(
                fault[
                    key
                ]
            )

    def test_20_fault_scientific_rules(self):
        rules = self.payload[
            "fault_injection_rules"
        ]

        self.assertTrue(
            rules[
                "scientifically_appropriate_layer_required"
            ]
        )

        self.assertFalse(
            rules[
                "raw_sensor_and_factor_level_corruption_equivalent"
            ]
        )

        self.assertTrue(
            rules[
                "clean_and_corrupted_derivatives_remain_same_partition"
            ]
        )

        self.assertFalse(
            rules[
                "random_seeds_may_be_reused_across_partitions"
            ]
        )

    def test_21_controlled_availability_not_supervision(self):
        boundary = self.payload[
            "controlled_availability_boundary"
        ]

        self.assertFalse(
            boundary[
                "accepted_health_supervision_source"
            ]
        )

        self.assertEqual(
            boundary[
                "real_health_label_count"
            ],
            0,
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

    def test_23_phase11_cannot_assume_phase10_results(self):
        policy = self.payload[
            "next_phase_policy"
        ]

        self.assertFalse(
            policy[
                "phase11_may_assume_phase10_controlled_fault_experiments_executed"
            ]
        )

        self.assertFalse(
            policy[
                "phase11_may_assume_phase10_rq1_answer_available"
            ]
        )

        self.assertFalse(
            policy[
                "phase11_may_assume_phase10_rq2_answer_available"
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
