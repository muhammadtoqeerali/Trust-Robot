from hashlib import sha256
from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]

FREEZE = (
    ROOT
    / "manifests/"
    "trust_robot_se4_real_train_runtime_input_binding_freeze_v1.json"
)

MODULE = (
    ROOT
    / "src/trust_robot/"
    "se4_real_train_runtime_input_binding.py"
)

CONFIG = (
    ROOT
    / "configs/trust_robot/"
    "se4_real_train_runtime_input_binding_v1.json"
)

IMPLEMENTATION_TEST = (
    ROOT
    / "tests/trust_robot/"
    "test_se4_real_train_runtime_input_binding.py"
)

PROJECT_STATE = (
    ROOT
    / "docs/TRUST_ROBOT_PROJECT_STATE.md"
)

EXPECTED_FREEZE_SHA = "28bf88aa87f6c527f16fa3144e94d70fadc64379f0e90529f04c46e7364d6afc"
EXPECTED_CONTENT_SHA = "ad55f7f6e17766aa3f994d83d178823db6ee8cdc4bec436a919172a09ae2ae39"


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


class SE4RealTrainRuntimeInputBindingFreezeTests(
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
            self.payload["content_sha256"],
            EXPECTED_CONTENT_SHA,
        )

        self.assertEqual(
            canonical_sha(self.payload),
            EXPECTED_CONTENT_SHA,
        )

    def test_03_schema(self):
        self.assertEqual(
            self.payload["schema"],
            "TRUST_ROBOT_SE4_REAL_TRAIN_RUNTIME_INPUT_BINDING_FREEZE_V1",
        )

    def test_04_stage_remains_SE4_incomplete(self):
        stage = self.payload[
            "stage_context"
        ]

        self.assertEqual(
            stage["stage_id"],
            "SE4",
        )

        self.assertFalse(
            stage["SE4_complete"]
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
            implementation["module_sha256"],
        )

        self.assertEqual(
            file_sha(CONFIG),
            implementation["config_sha256"],
        )

        self.assertEqual(
            file_sha(IMPLEMENTATION_TEST),
            implementation["test_sha256"],
        )

    def test_06_train_only(self):
        self.assertEqual(
            self.payload[
                "binding_contract"
            ][
                "split"
            ],
            "TRAIN",
        )

    def test_07_operator_values_required(self):
        contract = self.payload[
            "binding_contract"
        ]

        self.assertTrue(
            contract[
                "operator_supplied_values_required"
            ]
        )

        self.assertFalse(
            contract[
                "protocol_supplies_physical_defaults"
            ]
        )

    def test_08_binding_required_before_execution(self):
        self.assertTrue(
            self.payload[
                "binding_contract"
            ][
                "binding_required_before_network_execution"
            ]
        )

    def test_09_binding_is_not_execution_authorization(self):
        self.assertFalse(
            self.payload[
                "binding_contract"
            ][
                "binding_is_execution_authorization"
            ]
        )

        self.assertFalse(
            self.payload[
                "scientific_boundary"
            ][
                "runtime_binding_is_execution_authorization"
            ]
        )

    def test_10_real_binding_count_zero(self):
        self.assertEqual(
            self.payload[
                "current_real_binding_state"
            ][
                "real_runtime_binding_count"
            ],
            0,
        )

    def test_11_real_runtime_values_unbound(self):
        state = self.payload[
            "current_real_binding_state"
        ]

        self.assertFalse(
            state[
                "real_runtime_values_bound"
            ]
        )

        self.assertIsNone(
            state[
                "real_binding_sha256"
            ]
        )

    def test_12_no_bind_ipv4_selected(self):
        self.assertIsNone(
            self.payload[
                "current_real_binding_state"
            ][
                "bind_ipv4"
            ]
        )

    def test_13_no_udp_ports_selected(self):
        state = self.payload[
            "current_real_binding_state"
        ]

        self.assertIsNone(
            state[
                "measurement_udp_port"
            ]
        )

        self.assertIsNone(
            state[
                "position_udp_port"
            ]
        )

    def test_14_no_sensor_ipv4_selected(self):
        self.assertIsNone(
            self.payload[
                "current_real_binding_state"
            ][
                "sensor_ipv4"
            ]
        )

    def test_15_no_duration_or_output_root_selected(self):
        state = self.payload[
            "current_real_binding_state"
        ]

        self.assertIsNone(
            state[
                "capture_duration_seconds"
            ]
        )

        self.assertIsNone(
            state[
                "absolute_output_root"
            ]
        )

    def test_16_no_session_or_timeout_values_selected(self):
        state = self.payload[
            "current_real_binding_state"
        ]

        self.assertIsNone(
            state[
                "acquisition_session_id"
            ]
        )

        self.assertIsNone(
            state[
                "http_connect_timeout_seconds"
            ]
        )

        self.assertIsNone(
            state[
                "http_total_timeout_seconds"
            ]
        )

    def test_17_destination_configuration_not_verified(self):
        state = self.payload[
            "current_real_binding_state"
        ]

        self.assertFalse(
            state[
                "vlp32c_destination_configuration_verified"
            ]
        )

        self.assertIsNone(
            state[
                "vlp32c_destination_ipv4"
            ]
        )

    def test_18_no_network_or_sensor_execution(self):
        empirical = self.payload[
            "empirical_state"
        ]

        self.assertFalse(
            empirical[
                "network_IO_executed"
            ]
        )

        self.assertFalse(
            empirical[
                "sensor_contact_executed"
            ]
        )

    def test_19_zero_real_capture_artifacts(self):
        self.assertEqual(
            self.payload[
                "empirical_state"
            ][
                "raw_real_sensor_capture_artifact_count"
            ],
            0,
        )

    def test_20_zero_accepted_sources(self):
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

    def test_21_zero_real_health_labels(self):
        self.assertEqual(
            self.payload[
                "empirical_state"
            ][
                "real_health_label_count"
            ],
            0,
        )

    def test_22_no_interval_or_measurement_time_claim(self):
        empirical = self.payload[
            "empirical_state"
        ]

        self.assertFalse(
            empirical[
                "interval_binding_established"
            ]
        )

        self.assertFalse(
            empirical[
                "physical_measurement_time_established"
            ]
        )

    def test_23_runtime_binding_not_physical_evidence(self):
        science = self.payload[
            "scientific_boundary"
        ]

        self.assertFalse(
            science[
                "runtime_binding_is_physical_evidence"
            ]
        )

        self.assertFalse(
            science[
                "runtime_binding_is_source_acceptance"
            ]
        )

        self.assertFalse(
            science[
                "runtime_binding_is_health_label"
            ]
        )

    def test_24_execution_and_source_acceptance_closed(self):
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
                "source_acceptance_authorized"
            ]
        )

        self.assertFalse(
            transition[
                "health_label_generation_authorized"
            ]
        )

    def test_25_SE4_SE5_validation_confirmation_closed(self):
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

    def test_26_project_state_records_binding_freeze(self):
        text = PROJECT_STATE.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "## SE4 real TRAIN runtime-input binding freeze V1",
            text,
        )

        self.assertIn(
            "Real runtime bindings remain 0",
            text,
        )

    def test_27_project_state_keeps_execution_and_SE5_closed(self):
        text = PROJECT_STATE.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "Real-sensor execution remains unauthorized",
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

    def test_28_no_physical_values_fabricated(self):
        closure = self.payload[
            "closure_interpretation"
        ]

        self.assertTrue(
            closure[
                "this_is_not_a_real_runtime_binding"
            ]
        )

        self.assertTrue(
            closure[
                "this_is_not_live_execution"
            ]
        )

        self.assertFalse(
            closure[
                "physical_values_fabricated"
            ]
        )


if __name__ == "__main__":
    unittest.main()
