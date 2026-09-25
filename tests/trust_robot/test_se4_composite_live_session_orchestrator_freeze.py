from hashlib import sha256
from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]

FREEZE = (
    ROOT
    / "manifests/"
    "trust_robot_se4_composite_live_session_orchestrator_freeze_v1.json"
)

MODULE = (
    ROOT
    / "src/trust_robot/"
    "se4_composite_live_session_orchestrator.py"
)

CONFIG = (
    ROOT
    / "configs/trust_robot/"
    "se4_composite_live_session_orchestrator_resolution_v1.json"
)

IMPLEMENTATION_TEST = (
    ROOT
    / "tests/trust_robot/"
    "test_se4_composite_live_session_orchestrator.py"
)

PROJECT_STATE = (
    ROOT
    / "docs/TRUST_ROBOT_PROJECT_STATE.md"
)

EXPECTED_FREEZE_SHA = "7ee319bc88c33541923df1d73971a8703af29d177f98a05160a99655a9b51e04"
EXPECTED_CONTENT_SHA = "6b7433f7f75642c37fdfc5720826dd0ee12dff9c83be60c0d08a70fa0f69e2f8"


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


class SE4CompositeLiveSessionOrchestratorFreezeTests(
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
            "TRUST_ROBOT_SE4_COMPOSITE_LIVE_SESSION_ORCHESTRATOR_FREEZE_V1",
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

    def test_06_validated_V2_binding_required(self):
        self.assertTrue(
            self.payload[
                "composition_contract"
            ][
                "validated_V2_runtime_binding_required"
            ]
        )

    def test_07_authorization_precedes_UDP(self):
        contract = self.payload[
            "composition_contract"
        ]

        self.assertTrue(
            contract[
                "separate_hash_bound_execution_authorization_required"
            ]
        )

        self.assertTrue(
            contract[
                "authorization_must_precede_UDP_invocation"
            ]
        )

    def test_08_UDP_owns_session_directory(self):
        contract = self.payload[
            "composition_contract"
        ]

        self.assertTrue(
            contract[
                "UDP_receiver_owns_session_directory_creation"
            ]
        )

        self.assertFalse(
            contract[
                "HTTP_orchestrator_precreates_session_directory"
            ]
        )

    def test_09_HTTP_uses_returned_session(self):
        self.assertTrue(
            self.payload[
                "composition_contract"
            ][
                "HTTP_executor_consumes_returned_existing_session_directory"
            ]
        )

    def test_10_exact_HTTP_order(self):
        self.assertEqual(
            self.payload[
                "composition_contract"
            ][
                "HTTP_evidence_order"
            ],
            [
                "identity",
                "status",
                "diagnostic",
            ],
        )

    def test_11_concurrency_not_required(self):
        self.assertFalse(
            self.payload[
                "composition_contract"
            ][
                "HTTP_UDP_concurrency_required"
            ]
        )

    def test_12_authorization_format_selected(self):
        auth = self.payload[
            "authorization_contract"
        ]

        self.assertTrue(
            auth[
                "authorization_format_selected"
            ]
        )

        self.assertTrue(
            auth[
                "authorization_must_be_hash_bound_to_runtime_binding"
            ]
        )

    def test_13_zero_real_authorizations(self):
        auth = self.payload[
            "authorization_contract"
        ]

        self.assertEqual(
            auth[
                "repository_real_execution_authorization_artifact_count"
            ],
            0,
        )

        self.assertFalse(
            auth[
                "repository_real_sensor_execution_authorized"
            ]
        )

    def test_14_success_and_failure_receipts_selected(self):
        receipt = self.payload[
            "receipt_contract"
        ]

        self.assertEqual(
            receipt[
                "success_receipt"
            ],
            "composite_session_receipt.json",
        )

        self.assertEqual(
            receipt[
                "failure_receipt"
            ],
            "composite_session_failure.json",
        )

    def test_15_success_receipt_binds_inputs(self):
        receipt = self.payload[
            "receipt_contract"
        ]

        self.assertTrue(
            receipt[
                "success_receipt_hash_binds_runtime_binding"
            ]
        )

        self.assertTrue(
            receipt[
                "success_receipt_hash_binds_execution_authorization"
            ]
        )

    def test_16_injected_verification_only(self):
        verification = self.payload[
            "software_verification"
        ]

        self.assertTrue(
            verification[
                "component_injection_orchestration_verified"
            ]
        )

        self.assertFalse(
            verification[
                "component_injection_network_IO_executed"
            ]
        )

        self.assertFalse(
            verification[
                "component_injection_sensor_contact_executed"
            ]
        )

    def test_17_no_literal_loopback_contract_bypass(self):
        verification = self.payload[
            "software_verification"
        ]

        self.assertFalse(
            verification[
                "literal_loopback_composite_execution_used"
            ]
        )

        self.assertFalse(
            verification[
                "real_sensor_execution_verified"
            ]
        )

    def test_18_zero_real_runtime_state(self):
        state = self.payload[
            "current_real_state"
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

        self.assertEqual(
            state[
                "real_execution_authorization_count"
            ],
            0,
        )

    def test_19_no_real_sensor_execution(self):
        state = self.payload[
            "current_real_state"
        ]

        self.assertFalse(
            state[
                "real_sensor_execution_authorized"
            ]
        )

        self.assertFalse(
            state[
                "real_sensor_network_IO_executed"
            ]
        )

        self.assertFalse(
            state[
                "real_sensor_contact_executed"
            ]
        )

    def test_20_zero_real_artifacts_and_sessions(self):
        state = self.payload[
            "current_real_state"
        ]

        self.assertEqual(
            state[
                "raw_real_sensor_capture_artifact_count"
            ],
            0,
        )

        self.assertEqual(
            state[
                "real_composite_session_receipt_count"
            ],
            0,
        )

    def test_21_zero_sources_and_labels(self):
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

    def test_22_no_interval_or_measurement_time(self):
        science = self.payload[
            "scientific_boundary"
        ]

        self.assertFalse(
            science[
                "interval_binding_established"
            ]
        )

        self.assertFalse(
            science[
                "physical_measurement_time_established"
            ]
        )

    def test_23_no_reference_scoring(self):
        science = self.payload[
            "scientific_boundary"
        ]

        self.assertFalse(
            science[
                "reference_data_used"
            ]
        )

        self.assertFalse(
            science[
                "ATE_RPE_computed"
            ]
        )

        self.assertFalse(
            science[
                "final_localization_scoring_performed"
            ]
        )

    def test_24_transition_orchestrator_resolved(self):
        transition = self.payload[
            "transition_policy"
        ]

        self.assertTrue(
            transition[
                "composite_live_session_orchestrator_software_resolved"
            ]
        )

        self.assertTrue(
            transition[
                "component_injection_orchestration_verified"
            ]
        )

    def test_25_execution_training_SE5_closed(self):
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

    def test_26_validation_confirmation_closed(self):
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

    def test_27_project_state_records_orchestrator_freeze(self):
        text = PROJECT_STATE.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "## SE4 composite live-session orchestrator freeze V1",
            text,
        )

        self.assertIn(
            "The composite binding + HTTP + UDP orchestration software is resolved",
            text,
        )

    def test_28_project_state_preserves_physical_boundary(self):
        text = PROJECT_STATE.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "Real execution authorizations remain 0",
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
