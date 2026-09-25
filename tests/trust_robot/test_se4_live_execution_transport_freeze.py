from hashlib import sha256
from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]

FREEZE = (
    ROOT
    / "manifests/"
    "trust_robot_se4_live_execution_transport_freeze_v1.json"
)

MODULE = (
    ROOT
    / "src/trust_robot/"
    "se4_live_execution_transport_resolution.py"
)

CONFIG = (
    ROOT
    / "configs/trust_robot/"
    "se4_live_execution_transport_resolution_v1.json"
)

IMPLEMENTATION_TEST = (
    ROOT
    / "tests/trust_robot/"
    "test_se4_live_execution_transport_resolution.py"
)

PROJECT_STATE = (
    ROOT
    / "docs/TRUST_ROBOT_PROJECT_STATE.md"
)

EXPECTED_FREEZE_SHA = "c086398420cf9187aba0defaa3fce54a34eb5f57dbef457aa30e3fae290cd0b0"
EXPECTED_CONTENT_SHA = "4d2fc5c00728e96329c8519927b0b6cb219516d28e4a6a1334963ab887ecacbb"


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


class SE4LiveExecutionTransportFreezeTests(
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
            "TRUST_ROBOT_SE4_LIVE_EXECUTION_TRANSPORT_FREEZE_V1",
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

    def test_06_historical_pcap_not_rewritten(self):
        historical = self.payload[
            "historical_passive_capture"
        ]

        self.assertFalse(
            historical[
                "historical_freeze_rewritten"
            ]
        )

        self.assertTrue(
            historical[
                "historical_freeze_remains_valid"
            ]
        )

    def test_07_unprivileged_udp_selected(self):
        transport = self.payload[
            "selected_future_UDP_transport"
        ]

        self.assertEqual(
            transport[
                "transport"
            ],
            "ordinary_user_space_dual_UDP_receiver",
        )

        self.assertEqual(
            transport[
                "socket_family"
            ],
            "AF_INET",
        )

        self.assertEqual(
            transport[
                "socket_type"
            ],
            "SOCK_DGRAM",
        )

    def test_08_loopback_verified_real_sensor_not_verified(self):
        transport = self.payload[
            "selected_future_UDP_transport"
        ]

        self.assertTrue(
            transport[
                "loopback_execution_verified"
            ]
        )

        self.assertFalse(
            transport[
                "real_sensor_execution_verified"
            ]
        )

    def test_09_no_packet_sniffing_privilege(self):
        transport = self.payload[
            "selected_future_UDP_transport"
        ]

        self.assertFalse(
            transport[
                "tcpdump_required"
            ]
        )

        self.assertFalse(
            transport[
                "root_required"
            ]
        )

        self.assertFalse(
            transport[
                "sudo_required"
            ]
        )

        self.assertFalse(
            transport[
                "CAP_NET_RAW_required"
            ]
        )

    def test_10_payload_and_datagram_boundaries_preserved(self):
        evidence = self.payload[
            "UDP_payload_evidence_contract"
        ]

        self.assertTrue(
            evidence[
                "exact_payload_bytes_preserved"
            ]
        )

        self.assertTrue(
            evidence[
                "datagram_boundaries_preserved"
            ]
        )

        self.assertTrue(
            evidence[
                "per_datagram_SHA256_required"
            ]
        )

    def test_11_network_headers_not_preserved(self):
        evidence = self.payload[
            "UDP_payload_evidence_contract"
        ]

        self.assertFalse(
            evidence[
                "ethernet_headers_preserved"
            ]
        )

        self.assertFalse(
            evidence[
                "IP_headers_preserved"
            ]
        )

        self.assertFalse(
            evidence[
                "UDP_headers_preserved"
            ]
        )

    def test_12_zero_packet_loss_not_claimed(self):
        self.assertFalse(
            self.payload[
                "UDP_payload_evidence_contract"
            ][
                "zero_packet_loss_proven"
            ]
        )

    def test_13_publication_integrity_required(self):
        publication = self.payload[
            "publication_contract"
        ]

        self.assertTrue(
            publication[
                "atomic_publication_required"
            ]
        )

        self.assertTrue(
            publication[
                "pre_post_SHA256_equality_required"
            ]
        )

        self.assertFalse(
            publication[
                "existing_final_artifact_overwrite_allowed"
            ]
        )

    def test_14_http_execution_not_opened(self):
        http = self.payload[
            "HTTP_transport_state"
        ]

        self.assertFalse(
            http[
                "execution_implemented_by_this_freeze"
            ]
        )

        self.assertFalse(
            http[
                "execution_authorized"
            ]
        )

    def test_15_runtime_values_unselected(self):
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

    def test_16_no_real_sensor_execution(self):
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

        self.assertFalse(
            empirical[
                "real_sensor_receiver_execution_verified"
            ]
        )

    def test_17_zero_raw_artifacts(self):
        self.assertEqual(
            self.payload[
                "empirical_state"
            ][
                "raw_real_sensor_capture_artifact_count"
            ],
            0,
        )

    def test_18_zero_accepted_sources(self):
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

    def test_19_zero_real_health_labels(self):
        self.assertEqual(
            self.payload[
                "empirical_state"
            ][
                "real_health_label_count"
            ],
            0,
        )

    def test_20_no_interval_binding(self):
        self.assertFalse(
            self.payload[
                "empirical_state"
            ][
                "interval_binding_established"
            ]
        )

    def test_21_udp_receive_not_health_truth(self):
        science = self.payload[
            "scientific_boundary"
        ]

        self.assertFalse(
            science[
                "UDP_receive_establishes_baseline_nominality"
            ]
        )

        self.assertFalse(
            science[
                "UDP_receive_establishes_sensor_health"
            ]
        )

        self.assertFalse(
            science[
                "UDP_receive_establishes_health_supervision"
            ]
        )

    def test_22_receive_time_not_physical_measurement_time(self):
        self.assertFalse(
            self.payload[
                "scientific_boundary"
            ][
                "userspace_receive_time_is_physical_measurement_time"
            ]
        )

    def test_23_packet_sniffing_gate_removed_only_for_selected_transport(self):
        transition = self.payload[
            "transition_policy"
        ]

        self.assertTrue(
            transition[
                "packet_sniffing_permission_gate_removed_from_selected_transport"
            ]
        )

        self.assertTrue(
            transition[
                "future_UDP_execution_transport_resolved"
            ]
        )

    def test_24_real_execution_and_source_acceptance_closed(self):
        transition = self.payload[
            "transition_policy"
        ]

        self.assertFalse(
            transition[
                "runtime_environment_values_resolved"
            ]
        )

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

    def test_26_project_state_records_transport_freeze(self):
        text = PROJECT_STATE.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "## SE4 live-execution transport freeze V1",
            text,
        )

        self.assertIn(
            "SE4 remains incomplete",
            text,
        )

        self.assertIn(
            "Real-sensor execution remains unauthorized",
            text,
        )

    def test_27_closure_does_not_fabricate_evidence(self):
        closure = self.payload[
            "closure_interpretation"
        ]

        self.assertTrue(
            closure[
                "this_is_software_transport_resolution"
            ]
        )

        self.assertTrue(
            closure[
                "this_is_not_real_sensor_execution"
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


if __name__ == "__main__":
    unittest.main()
