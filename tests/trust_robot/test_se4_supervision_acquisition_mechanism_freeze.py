from hashlib import sha256
from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]

FREEZE = (
    ROOT
    / "manifests/"
    "trust_robot_se4_supervision_acquisition_mechanism_freeze_v1.json"
)

MODULE = (
    ROOT
    / "src/trust_robot/"
    "se4_supervision_acquisition_mechanism_resolution.py"
)

CONFIG = (
    ROOT
    / "configs/trust_robot/"
    "se4_supervision_acquisition_mechanism_resolution_v1.json"
)

IMPLEMENTATION_TEST = (
    ROOT
    / "tests/trust_robot/"
    "test_se4_supervision_acquisition_mechanism_resolution.py"
)

PROJECT_STATE = (
    ROOT
    / "docs/TRUST_ROBOT_PROJECT_STATE.md"
)

EXPECTED_FREEZE_SHA = "18df2dd2a88d60939f31b844f584a21d090f3a15026369e511c2cb4d39dd20f4"
EXPECTED_CONTENT_SHA = "5e78f33ee30ed2be3af23401d3ac25059a8bb372ab71558ac0502f83742eb6e7"


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


class SE4SupervisionAcquisitionMechanismFreezeTests(
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
            "TRUST_ROBOT_SE4_SUPERVISION_ACQUISITION_MECHANISM_FREEZE_V1",
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

    def test_06_identity_HTTP_selected(self):
        self.assertEqual(
            self.payload[
                "selected_acquisition_mechanisms"
            ][
                "device_identity_HTTP_GET"
            ],
            "/cgi/info.json",
        )

    def test_07_status_HTTP_selected(self):
        self.assertEqual(
            self.payload[
                "selected_acquisition_mechanisms"
            ][
                "sensor_status_HTTP_GET"
            ],
            "/cgi/status.json",
        )

    def test_08_diagnostic_HTTP_selected(self):
        self.assertEqual(
            self.payload[
                "selected_acquisition_mechanisms"
            ][
                "sensor_diagnostic_HTTP_GET"
            ],
            "/cgi/diag.json",
        )

    def test_09_measurement_pcap_selected(self):
        self.assertEqual(
            self.payload[
                "selected_acquisition_mechanisms"
            ][
                "measurement_UDP_preservation"
            ],
            "classic_pcap",
        )

    def test_10_position_pcap_selected(self):
        self.assertEqual(
            self.payload[
                "selected_acquisition_mechanisms"
            ][
                "position_UDP_preservation"
            ],
            "classic_pcap",
        )

    def test_11_runtime_environment_values_unselected(self):
        values = self.payload[
            "runtime_values_intentionally_unselected"
        ]

        self.assertTrue(
            all(
                value is None
                for value
                in values.values()
            )
        )

    def test_12_zero_network_execution(self):
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
                "subprocess_executed"
            ]
        )

        self.assertFalse(
            empirical[
                "live_sensor_probe_executed"
            ]
        )

    def test_13_zero_raw_artifacts(self):
        self.assertEqual(
            self.payload[
                "empirical_state"
            ][
                "raw_capture_artifact_count"
            ],
            0,
        )

    def test_14_zero_identity_receipts(self):
        self.assertEqual(
            self.payload[
                "empirical_state"
            ][
                "device_identity_receipt_count"
            ],
            0,
        )

    def test_15_zero_accepted_baseline_sources(self):
        self.assertEqual(
            self.payload[
                "empirical_state"
            ][
                "accepted_baseline_nominality_source_count"
            ],
            0,
        )

    def test_16_zero_accepted_supervision_sources(self):
        self.assertEqual(
            self.payload[
                "empirical_state"
            ][
                "accepted_health_supervision_source_count"
            ],
            0,
        )

    def test_17_zero_real_labels(self):
        self.assertEqual(
            self.payload[
                "empirical_state"
            ][
                "real_health_label_count"
            ],
            0,
        )

    def test_18_no_interval_binding(self):
        self.assertFalse(
            self.payload[
                "empirical_state"
            ][
                "interval_binding_established"
            ]
        )

    def test_19_raw_capture_not_health_truth(self):
        science = self.payload[
            "scientific_boundary"
        ]

        self.assertFalse(
            science[
                "raw_packet_capture_is_baseline_nominality"
            ]
        )

        self.assertFalse(
            science[
                "raw_packet_capture_is_health_supervision"
            ]
        )

    def test_20_host_time_not_physical_measurement_time(self):
        self.assertFalse(
            self.payload[
                "scientific_boundary"
            ][
                "host_capture_time_is_physical_measurement_time"
            ]
        )

    def test_21_live_execution_blocked(self):
        self.assertFalse(
            self.payload[
                "transition_policy"
            ][
                "live_execution_authorized"
            ]
        )

    def test_22_SE4_and_training_remain_blocked(self):
        transition = self.payload[
            "transition_policy"
        ]

        self.assertFalse(
            transition["SE4_complete"]
        )

        self.assertFalse(
            transition[
                "SE4_training_authorized"
            ]
        )

    def test_23_SE5_validation_confirmation_closed(self):
        transition = self.payload[
            "transition_policy"
        ]

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

    def test_24_not_live_execution_or_source_acceptance(self):
        closure = self.payload[
            "closure_interpretation"
        ]

        self.assertTrue(
            closure[
                "this_is_not_live_execution"
            ]
        )

        self.assertTrue(
            closure[
                "this_is_not_source_acceptance"
            ]
        )

        self.assertFalse(
            closure[
                "physical_evidence_fabricated"
            ]
        )

    def test_25_project_state_records_mechanism_freeze(self):
        text = PROJECT_STATE.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "## SE4 supervision acquisition mechanism freeze V1",
            text,
        )

        self.assertIn(
            "Live execution remains unauthorized",
            text,
        )

        self.assertIn(
            "SE4 remains incomplete",
            text,
        )

    def test_26_project_state_keeps_SE5_closed(self):
        text = PROJECT_STATE.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "SE5 remains blocked",
            text,
        )


if __name__ == "__main__":
    unittest.main()
