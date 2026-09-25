from hashlib import sha256
from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]

FREEZE = (
    ROOT
    / "manifests/"
    "trust_robot_se4_real_train_runtime_input_binding_v2_freeze_v1.json"
)

MODULE = (
    ROOT
    / "src/trust_robot/"
    "se4_real_train_runtime_input_binding_v2.py"
)

CONFIG = (
    ROOT
    / "configs/trust_robot/"
    "se4_real_train_runtime_input_binding_v2.json"
)

IMPLEMENTATION_TEST = (
    ROOT
    / "tests/trust_robot/"
    "test_se4_real_train_runtime_input_binding_v2.py"
)

PROJECT_STATE = (
    ROOT
    / "docs/TRUST_ROBOT_PROJECT_STATE.md"
)

EXPECTED_FREEZE_SHA = "81f1d22674a4ca1ef4a8b5c9c4d16e446423eb3e6a76981fa7d6f99b08477388"
EXPECTED_CONTENT_SHA = "d24957ec3b3bac688793d0a8ffe167a9e7810e710f25a9d4b8c01c4b256b5fe9"


def file_sha(path):
    return sha256(
        path.read_bytes()
    ).hexdigest()


def canonical_sha(payload):
    body = dict(payload)

    body.pop(
        "content_sha256",
        None,
    )

    return sha256(
        json.dumps(
            body,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode(
            "utf-8"
        )
    ).hexdigest()


class SE4RealTrainRuntimeInputBindingV2FreezeTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(
            FREEZE.read_text(
                encoding="utf-8"
            )
        )

    def test_01_freeze_file_sha(self):
        self.assertEqual(
            file_sha(FREEZE),
            EXPECTED_FREEZE_SHA,
        )

    def test_02_content_digest(self):
        self.assertEqual(
            self.payload[
                "content_sha256"
            ],
            EXPECTED_CONTENT_SHA,
        )

        self.assertEqual(
            canonical_sha(
                self.payload
            ),
            EXPECTED_CONTENT_SHA,
        )

    def test_03_schema(self):
        self.assertEqual(
            self.payload[
                "schema"
            ],
            "TRUST_ROBOT_SE4_REAL_TRAIN_RUNTIME_INPUT_BINDING_V2_FREEZE_V1",
        )

    def test_04_stage_remains_incomplete(self):
        stage = self.payload[
            "stage_context"
        ]

        self.assertFalse(
            stage[
                "SE4_complete"
            ]
        )

        self.assertFalse(
            stage[
                "SE4_training_authorized"
            ]
        )

    def test_05_implementation_hashes(self):
        implementation = self.payload[
            "implementation"
        ]

        self.assertEqual(
            file_sha(MODULE),
            implementation[
                "module_sha256"
            ],
        )

        self.assertEqual(
            file_sha(CONFIG),
            implementation[
                "config_sha256"
            ],
        )

        self.assertEqual(
            file_sha(IMPLEMENTATION_TEST),
            implementation[
                "test_sha256"
            ],
        )

    def test_06_V1_preserved(self):
        self.assertTrue(
            self.payload[
                "historical_V1"
            ][
                "preserved_unchanged"
            ]
        )

    def test_07_exact_contract_delta(self):
        delta = self.payload[
            "contract_delta"
        ]

        self.assertEqual(
            delta[
                "added_required_fields"
            ],
            [
                "http_port",
            ],
        )

        self.assertEqual(
            delta[
                "removed_required_fields"
            ],
            [],
        )

        self.assertEqual(
            delta[
                "other_physical_runtime_contract_changes"
            ],
            [],
        )

    def test_08_V2_has_16_fields(self):
        contract = self.payload[
            "V2_binding_contract"
        ]

        self.assertEqual(
            contract[
                "required_field_count"
            ],
            16,
        )

        self.assertEqual(
            contract[
                "required_fields"
            ].count(
                "http_port"
            ),
            1,
        )

    def test_09_HTTP_port_required_without_default(self):
        contract = self.payload[
            "V2_binding_contract"
        ]

        self.assertTrue(
            contract[
                "explicit_HTTP_port_required"
            ]
        )

        self.assertFalse(
            contract[
                "protocol_supplies_physical_HTTP_port_default"
            ]
        )

    def test_10_binding_not_execution_authorization(self):
        self.assertFalse(
            self.payload[
                "V2_binding_contract"
            ][
                "binding_is_execution_authorization"
            ]
        )

    def test_11_zero_real_bindings(self):
        state = self.payload[
            "current_real_binding_state"
        ]

        self.assertEqual(
            state[
                "real_runtime_binding_count"
            ],
            0,
        )

        self.assertFalse(
            state[
                "real_runtime_values_bound"
            ]
        )

    def test_12_no_real_HTTP_port_selected(self):
        self.assertIsNone(
            self.payload[
                "current_real_binding_state"
            ][
                "http_port"
            ]
        )

    def test_13_no_real_sensor_execution(self):
        science = self.payload[
            "scientific_boundary"
        ]

        self.assertFalse(
            science[
                "network_IO_executed"
            ]
        )

        self.assertFalse(
            science[
                "sensor_contact_executed"
            ]
        )

    def test_14_zero_sources_and_labels(self):
        science = self.payload[
            "scientific_boundary"
        ]

        self.assertEqual(
            science[
                "accepted_baseline_nominality_source_count"
            ],
            0,
        )

        self.assertEqual(
            science[
                "accepted_health_supervision_source_count"
            ],
            0,
        )

        self.assertEqual(
            science[
                "real_health_label_count"
            ],
            0,
        )

    def test_15_orchestrator_remains_unresolved(self):
        frontier = self.payload[
            "remaining_orchestration_frontier"
        ]

        self.assertFalse(
            frontier[
                "composite_binding_HTTP_UDP_live_session_orchestrator_resolved"
            ]
        )

        self.assertFalse(
            frontier[
                "composite_live_session_execution_authorized"
            ]
        )

    def test_16_transition_gap_resolved(self):
        transition = self.payload[
            "transition_policy"
        ]

        self.assertTrue(
            transition[
                "runtime_input_binding_V2_resolved"
            ]
        )

        self.assertTrue(
            transition[
                "HTTP_port_cross_contract_gap_resolved"
            ]
        )

    def test_17_execution_and_training_closed(self):
        transition = self.payload[
            "transition_policy"
        ]

        self.assertFalse(
            transition[
                "real_sensor_execution_authorized"
            ]
        )

        self.assertFalse(
            transition[
                "SE4_complete"
            ]
        )

        self.assertFalse(
            transition[
                "SE4_training_authorized"
            ]
        )

        self.assertFalse(
            transition[
                "SE5_may_proceed"
            ]
        )

    def test_18_validation_confirmation_closed(self):
        transition = self.payload[
            "transition_policy"
        ]

        self.assertTrue(
            transition[
                "validation_remains_closed"
            ]
        )

        self.assertTrue(
            transition[
                "confirmation_remains_closed"
            ]
        )

    def test_19_project_state_records_V2_freeze(self):
        text = PROJECT_STATE.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "## SE4 real TRAIN runtime-input binding V2 freeze V1",
            text,
        )

        self.assertIn(
            "The V2 required-field count is 16",
            text,
        )

    def test_20_project_state_keeps_orchestrator_and_SE4_closed(self):
        text = PROJECT_STATE.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "The composite binding + HTTP + UDP live-session orchestrator remains unresolved",
            text,
        )

        self.assertIn(
            "SE4 remains incomplete",
            text,
        )

        self.assertIn(
            "SE5 remains blocked",
            text,
        )


if __name__ == "__main__":
    unittest.main()
