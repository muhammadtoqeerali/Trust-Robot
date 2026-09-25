from hashlib import sha256
from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]

FREEZE = (
    ROOT
    / "manifests/"
    "trust_robot_se4_http_evidence_executor_freeze_v1.json"
)

MODULE = (
    ROOT
    / "src/trust_robot/"
    "se4_http_evidence_executor.py"
)

CONFIG = (
    ROOT
    / "configs/trust_robot/"
    "se4_http_evidence_executor_resolution_v1.json"
)

IMPLEMENTATION_TEST = (
    ROOT
    / "tests/trust_robot/"
    "test_se4_http_evidence_executor.py"
)

PROJECT_STATE = (
    ROOT
    / "docs/TRUST_ROBOT_PROJECT_STATE.md"
)

EXPECTED_FREEZE_SHA = "29639601503a8d7c0b9db879939a8960b2f0a69ca10e378fc07f0b031aeadc10"
EXPECTED_CONTENT_SHA = "3eaba4fa7b25be4343ca42533ff2e1aeddebda8d03209aa6812569c5ed4bd559"


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


class SE4HTTPEvidenceExecutorFreezeTests(
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
            "TRUST_ROBOT_SE4_HTTP_EVIDENCE_EXECUTOR_FREEZE_V1",
        )

    def test_04_stage_remains_incomplete(self):
        stage = self.payload[
            "stage_context"
        ]

        self.assertEqual(
            stage[
                "stage_id"
            ],
            "SE4",
        )

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
            file_sha(
                IMPLEMENTATION_TEST
            ),
            implementation[
                "test_sha256"
            ],
        )

    def test_06_HTTP_software_implemented(self):
        self.assertTrue(
            self.payload[
                "transition_policy"
            ][
                "HTTP_execution_software_implemented"
            ]
        )

    def test_07_loopback_verified(self):
        verification = self.payload[
            "software_verification"
        ]

        self.assertTrue(
            verification[
                "loopback_execution_verified"
            ]
        )

        self.assertTrue(
            verification[
                "loopback_only"
            ]
        )

    def test_08_real_sensor_not_verified(self):
        self.assertFalse(
            self.payload[
                "software_verification"
            ][
                "real_sensor_execution_verified"
            ]
        )

    def test_09_GET_only(self):
        contract = self.payload[
            "HTTP_execution_contract"
        ]

        self.assertEqual(
            contract[
                "method"
            ],
            "GET",
        )

        self.assertTrue(
            contract[
                "read_only"
            ]
        )

    def test_10_exact_endpoints(self):
        contract = self.payload[
            "HTTP_execution_contract"
        ]

        self.assertEqual(
            contract[
                "identity_path"
            ],
            "/cgi/info.json",
        )

        self.assertEqual(
            contract[
                "status_path"
            ],
            "/cgi/status.json",
        )

        self.assertEqual(
            contract[
                "diagnostic_path"
            ],
            "/cgi/diag.json",
        )

    def test_11_explicit_HTTP_port_required(self):
        contract = self.payload[
            "HTTP_execution_contract"
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

        self.assertIsNone(
            contract[
                "HTTP_port_default_sentinel"
            ]
        )

    def test_12_loopback_port_is_not_real_selection(self):
        verification = self.payload[
            "software_verification"
        ]

        self.assertTrue(
            verification[
                "loopback_HTTP_port_is_ephemeral_test_value"
            ]
        )

        self.assertFalse(
            verification[
                "loopback_HTTP_port_is_real_runtime_selection"
            ]
        )

    def test_13_no_real_HTTP_port_selected(self):
        self.assertIsNone(
            self.payload[
                "real_runtime_state"
            ][
                "real_sensor_HTTP_port"
            ]
        )

    def test_14_zero_real_runtime_bindings(self):
        state = self.payload[
            "real_runtime_state"
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

    def test_15_no_real_sensor_network_execution(self):
        empirical = self.payload[
            "empirical_state"
        ]

        self.assertFalse(
            empirical[
                "real_sensor_network_IO_executed"
            ]
        )

        self.assertFalse(
            empirical[
                "real_sensor_contact_executed"
            ]
        )

    def test_16_zero_real_HTTP_artifacts(self):
        empirical = self.payload[
            "empirical_state"
        ]

        self.assertEqual(
            empirical[
                "raw_real_sensor_HTTP_artifact_count"
            ],
            0,
        )

        self.assertEqual(
            empirical[
                "real_device_identity_receipt_count"
            ],
            0,
        )

    def test_17_zero_accepted_sources(self):
        empirical = self.payload[
            "empirical_state"
        ]

        self.assertEqual(
            empirical[
                "accepted_baseline_nominality_source_count"
            ],
            0,
        )

        self.assertEqual(
            empirical[
                "accepted_health_supervision_source_count"
            ],
            0,
        )

    def test_18_zero_real_labels(self):
        self.assertEqual(
            self.payload[
                "empirical_state"
            ][
                "real_health_label_count"
            ],
            0,
        )

    def test_19_no_interval_binding(self):
        self.assertFalse(
            self.payload[
                "empirical_state"
            ][
                "interval_binding_established"
            ]
        )

    def test_20_no_physical_measurement_time(self):
        self.assertFalse(
            self.payload[
                "empirical_state"
            ][
                "physical_measurement_time_established"
            ]
        )

    def test_21_HTTP_not_health_truth(self):
        science = self.payload[
            "scientific_boundary"
        ]

        self.assertFalse(
            science[
                "HTTP_response_is_physical_health_truth"
            ]
        )

        self.assertFalse(
            science[
                "HTTP_status_is_health_label"
            ]
        )

        self.assertFalse(
            science[
                "HTTP_diagnostic_is_health_label"
            ]
        )

    def test_22_HTTP_implementation_not_authorization(self):
        self.assertFalse(
            self.payload[
                "scientific_boundary"
            ][
                "HTTP_software_implementation_is_execution_authorization"
            ]
        )

    def test_23_loopback_not_physical_evidence(self):
        self.assertFalse(
            self.payload[
                "scientific_boundary"
            ][
                "loopback_verification_is_physical_sensor_evidence"
            ]
        )

    def test_24_real_sensor_execution_closed(self):
        self.assertFalse(
            self.payload[
                "transition_policy"
            ][
                "real_sensor_execution_authorized"
            ]
        )

    def test_25_source_acceptance_and_labels_closed(self):
        transition = self.payload[
            "transition_policy"
        ]

        self.assertFalse(
            transition[
                "source_acceptance_authorized"
            ]
        )

        self.assertFalse(
            transition[
                "health_label_generation_authorized"
            ]
        )

    def test_26_SE4_SE5_validation_confirmation_closed(self):
        transition = self.payload[
            "transition_policy"
        ]

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

    def test_27_project_state_records_HTTP_freeze(self):
        text = PROJECT_STATE.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "## SE4 HTTP evidence executor freeze V1",
            text,
        )

        self.assertIn(
            "HTTP execution software implemented and loopback verified",
            text,
        )

    def test_28_project_state_records_no_real_port_or_execution(self):
        text = PROJECT_STATE.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "No real HTTP port is selected",
            text,
        )

        self.assertIn(
            "Real-sensor HTTP execution remains unauthorized",
            text,
        )

    def test_29_no_physical_runtime_values_fabricated(self):
        closure = self.payload[
            "closure_interpretation"
        ]

        self.assertTrue(
            closure[
                "this_is_not_real_sensor_execution"
            ]
        )

        self.assertTrue(
            closure[
                "this_is_not_a_real_runtime_binding"
            ]
        )

        self.assertFalse(
            closure[
                "physical_runtime_values_fabricated"
            ]
        )


if __name__ == "__main__":
    unittest.main()
