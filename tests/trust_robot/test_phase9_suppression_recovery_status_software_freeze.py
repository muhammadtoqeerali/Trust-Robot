import copy
from hashlib import sha256
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]

MANIFEST = (
    ROOT
    / "manifests"
    / "trust_robot_phase9_suppression_recovery_status_software_freeze_v1.json"
)


class TestPhase9SuppressionRecoveryStatusSoftwareFreeze(unittest.TestCase):

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
            "TRUST_ROBOT_PHASE9_SUPPRESSION_RECOVERY_STATUS_SOFTWARE_FREEZE_V1",
        )

    def test_02_phase(self):
        self.assertEqual(
            self.payload[
                "checkpoint_semantics"
            ][
                "phase"
            ],
            9,
        )

    def test_03_architecture_implemented(self):
        self.assertTrue(
            self.payload[
                "checkpoint_semantics"
            ][
                "software_architecture_implemented"
            ]
        )

    def test_04_runtime_suppression_incomplete(self):
        self.assertFalse(
            self.payload[
                "checkpoint_semantics"
            ][
                "runtime_suppression_complete"
            ]
        )

    def test_05_runtime_recovery_incomplete(self):
        self.assertFalse(
            self.payload[
                "checkpoint_semantics"
            ][
                "runtime_recovery_complete"
            ]
        )

    def test_06_runtime_status_incomplete(self):
        self.assertFalse(
            self.payload[
                "checkpoint_semantics"
            ][
                "runtime_estimator_status_complete"
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

    def test_08_single_frame_suppression_forbidden(self):
        self.assertFalse(
            self.payload[
                "authoritative_hysteresis"
            ][
                "single_frame_hard_suppression_allowed"
            ]
        )

    def test_09_entry_signal(self):
        self.assertEqual(
            self.payload[
                "authoritative_hysteresis"
            ][
                "entry_signal"
            ],
            "unusable_probability",
        )

    def test_10_entry_threshold_unselected(self):
        h = self.payload[
            "authoritative_hysteresis"
        ]

        self.assertIsNone(
            h[
                "entry_threshold"
            ]
        )

        self.assertFalse(
            h[
                "entry_threshold_selected"
            ]
        )

    def test_11_entry_window_unselected(self):
        h = self.payload[
            "authoritative_hysteresis"
        ]

        self.assertIsNone(
            h[
                "entry_consecutive_window_count"
            ]
        )

        self.assertFalse(
            h[
                "entry_consecutive_window_count_selected"
            ]
        )

    def test_12_recovery_lower_than_entry_semantics(self):
        self.assertEqual(
            self.payload[
                "authoritative_hysteresis"
            ][
                "recovery_threshold_relation_to_entry"
            ],
            "lower",
        )

    def test_13_recovery_unselected(self):
        h = self.payload[
            "authoritative_hysteresis"
        ]

        self.assertIsNone(
            h[
                "recovery_threshold"
            ]
        )

        self.assertFalse(
            h[
                "recovery_threshold_selected"
            ]
        )

    def test_14_recovery_window_unselected(self):
        h = self.payload[
            "authoritative_hysteresis"
        ]

        self.assertIsNone(
            h[
                "recovery_consecutive_window_count"
            ]
        )

        self.assertFalse(
            h[
                "recovery_consecutive_window_count_selected"
            ]
        )

    def test_15_support_assessment_required(self):
        self.assertTrue(
            self.payload[
                "remaining_factor_support"
            ][
                "assessment_required_before_hard_suppression"
            ]
        )

    def test_16_support_rule_unselected(self):
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

    def test_17_no_observability_guarantee(self):
        self.assertFalse(
            self.payload[
                "remaining_factor_support"
            ][
                "unsupported_observability_guarantee_allowed"
            ]
        )

    def test_18_reporting_options(self):
        self.assertEqual(
            self.payload[
                "insufficient_support_reporting"
            ][
                "reporting_options"
            ],
            [
                "degraded_estimator_state",
                "unavailable_estimator_state",
            ],
        )

    def test_19_status_rule_unselected(self):
        self.assertFalse(
            self.payload[
                "insufficient_support_reporting"
            ][
                "degraded_vs_unavailable_rule_selected"
            ]
        )

    def test_20_no_forced_nominal(self):
        self.assertFalse(
            self.payload[
                "insufficient_support_reporting"
            ][
                "nominal_estimate_may_be_forced_when_support_insufficient"
            ]
        )

    def test_21_runtime_execution_blocked(self):
        self.assertEqual(
            set(
                self.payload[
                    "runtime_execution_gate"
                ].values()
            ),
            {
                False,
            },
        )

    def test_22_fallback_unselected(self):
        fallback = self.payload[
            "fallback_boundary"
        ]

        self.assertFalse(
            fallback[
                "fallback_defined_by_authoritative_phase9_section"
            ]
        )

        self.assertEqual(
            fallback[
                "fallback_policy"
            ],
            "unselected",
        )

        self.assertFalse(
            fallback[
                "fallback_execution_authorized"
            ]
        )

    def test_23_phase10_cannot_assume_runtime(self):
        policy = self.payload[
            "next_phase_policy"
        ]

        self.assertFalse(
            policy[
                "phase10_may_assume_phase9_runtime_suppression_available"
            ]
        )

        self.assertFalse(
            policy[
                "phase10_may_assume_phase9_runtime_recovery_available"
            ]
        )

        self.assertFalse(
            policy[
                "phase10_may_assume_phase9_estimator_status_execution_available"
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
