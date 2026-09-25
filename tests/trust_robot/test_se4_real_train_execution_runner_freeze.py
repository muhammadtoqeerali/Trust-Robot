from hashlib import sha256
from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]

FREEZE = (
    ROOT
    / "manifests/"
    "trust_robot_se4_real_train_execution_runner_freeze_v1.json"
)

MODULE = (
    ROOT
    / "src/trust_robot/"
    "se4_real_train_execution_runner.py"
)

RUNNER = (
    ROOT
    / "scripts/trust_robot/"
    "run_se4_real_train_live_session_v1.py"
)

CONFIG = (
    ROOT
    / "configs/trust_robot/"
    "se4_real_train_execution_runner_resolution_v1.json"
)

IMPLEMENTATION_TEST = (
    ROOT
    / "tests/trust_robot/"
    "test_se4_real_train_execution_runner.py"
)

PROJECT_STATE = (
    ROOT
    / "docs/TRUST_ROBOT_PROJECT_STATE.md"
)

EXPECTED_FREEZE_SHA = "f4b3e59947f49ecc1c4581e4514dfed123605c34df1b377bb92a7fbbc5fb04d3"
EXPECTED_CONTENT_SHA = "aa554dbdf0b4adbe94d3d9b88aab9be3c20fa642bfeda587b5ea9d5f00783031"


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


class SE4RealTrainExecutionRunnerFreezeTests(
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
            "TRUST_ROBOT_SE4_REAL_TRAIN_EXECUTION_RUNNER_FREEZE_V1",
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
            file_sha(RUNNER),
            implementation[
                "runner_sha256"
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

    def test_06_three_external_files_required(self):
        self.assertEqual(
            self.payload[
                "input_contract"
            ][
                "required_external_files"
            ],
            [
                "runtime_binding_file",
                "execution_authorization_file",
                "authorization_record_file",
            ],
        )

    def test_07_binding_and_authorization_validated(self):
        contract = self.payload[
            "input_contract"
        ]

        self.assertTrue(
            contract[
                "runtime_binding_must_validate_as_frozen_V2"
            ]
        )

        self.assertTrue(
            contract[
                "execution_authorization_must_validate"
            ]
        )

        self.assertTrue(
            contract[
                "execution_authorization_must_bind_exact_runtime_binding"
            ]
        )

    def test_08_record_digest_must_match(self):
        self.assertTrue(
            self.payload[
                "input_contract"
            ][
                "authorization_record_SHA256_must_match_authorization"
            ]
        )

    def test_09_hash_match_not_authority(self):
        self.assertFalse(
            self.payload[
                "input_contract"
            ][
                "authorization_record_SHA256_match_proves_authority_or_trust"
            ]
        )

    def test_10_runner_selects_no_physical_values(self):
        contract = self.payload[
            "input_contract"
        ]

        self.assertFalse(
            contract[
                "runner_selects_or_infers_physical_runtime_values"
            ]
        )

        self.assertFalse(
            contract[
                "runner_creates_execution_authorization"
            ]
        )

    def test_11_default_validation_only(self):
        self.assertEqual(
            self.payload[
                "execution_gate"
            ][
                "default_mode"
            ],
            "validation_only",
        )

    def test_12_validation_only_has_no_IO(self):
        gate = self.payload[
            "execution_gate"
        ]

        self.assertFalse(
            gate[
                "validation_only_network_IO"
            ]
        )

        self.assertFalse(
            gate[
                "validation_only_sensor_contact"
            ]
        )

    def test_13_explicit_real_execution_gates(self):
        gate = self.payload[
            "execution_gate"
        ]

        self.assertTrue(
            gate[
                "explicit_execute_real_switch_required"
            ]
        )

        self.assertTrue(
            gate[
                "exact_network_IO_acknowledgement_required"
            ]
        )

    def test_14_injected_dispatch_not_real_execution(self):
        verification = self.payload[
            "software_verification"
        ]

        self.assertTrue(
            verification[
                "injected_orchestrator_dispatch_verified"
            ]
        )

        self.assertFalse(
            verification[
                "injected_orchestrator_dispatch_is_real_sensor_execution"
            ]
        )

    def test_15_real_file_input_count_zero(self):
        self.assertEqual(
            self.payload[
                "software_verification"
            ][
                "real_file_input_set_count"
            ],
            0,
        )

    def test_16_external_blockers_remain(self):
        blockers = self.payload[
            "remaining_external_blockers"
        ]

        self.assertEqual(
            blockers[
                "real_V2_runtime_input_values"
            ],
            "unresolved",
        )

        self.assertEqual(
            blockers[
                "grounded_authorization_record_source"
            ],
            "unresolved",
        )

        self.assertEqual(
            blockers[
                "software_file_driven_runner"
            ],
            "resolved",
        )

    def test_17_zero_real_binding_and_authorization(self):
        state = self.payload[
            "current_real_state"
        ]

        self.assertEqual(
            state[
                "real_runtime_binding_count"
            ],
            0,
        )

        self.assertEqual(
            state[
                "real_execution_authorization_count"
            ],
            0,
        )

        self.assertEqual(
            state[
                "grounded_authorization_record_count"
            ],
            0,
        )

    def test_18_no_real_sensor_execution(self):
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

    def test_19_zero_real_capture_artifacts(self):
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

    def test_20_zero_sources_and_labels(self):
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

    def test_21_no_interval_or_measurement_time(self):
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

    def test_22_no_reference_scoring(self):
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

    def test_23_runner_software_transition_resolved(self):
        transition = self.payload[
            "transition_policy"
        ]

        self.assertTrue(
            transition[
                "file_driven_real_execution_runner_software_resolved"
            ]
        )

        self.assertFalse(
            transition[
                "real_input_source_resolved"
            ]
        )

        self.assertFalse(
            transition[
                "grounded_execution_authorization_resolved"
            ]
        )

    def test_24_execution_training_SE5_closed(self):
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

    def test_25_validation_confirmation_closed(self):
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

    def test_26_project_state_records_runner_freeze(self):
        text = PROJECT_STATE.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "## SE4 file-driven real TRAIN execution runner freeze V1",
            text,
        )

        self.assertIn(
            "The file-driven real TRAIN execution runner software is resolved",
            text,
        )

    def test_27_project_state_records_external_blockers(self):
        text = PROJECT_STATE.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "Real runtime bindings remain 0",
            text,
        )

        self.assertIn(
            "Grounded authorization records remain 0",
            text,
        )

    def test_28_project_state_keeps_SE4_SE5_closed(self):
        text = PROJECT_STATE.read_text(
            encoding="utf-8"
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
