from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import ast
import json
import unittest

from trust_robot.se4_live_execution_transport_resolution import (
    FROZEN_INPUT_SHA256,
    SCHEMA,
    SE4LiveExecutionTransportResolutionError,
    assert_health_supervision_available,
    assert_real_sensor_execution_authorized,
    build_se4_live_execution_transport_resolution,
    content_sha256,
    validate_se4_live_execution_transport_resolution,
)


ROOT = Path(__file__).resolve().parents[2]

CONFIG = (
    ROOT
    / "configs/trust_robot/"
    "se4_live_execution_transport_resolution_v1.json"
)

MODULE = (
    ROOT
    / "src/trust_robot/"
    "se4_live_execution_transport_resolution.py"
)

INPUT_PATHS = {
    "SE4_acquisition_mechanism_freeze":
        ROOT
        / "manifests/"
        "trust_robot_se4_supervision_acquisition_mechanism_freeze_v1.json",

    "SE4_acquisition_mechanism_config":
        ROOT
        / "configs/trust_robot/"
        "se4_supervision_acquisition_mechanism_resolution_v1.json",

    "phase5_unprivileged_udp_receiver_config":
        ROOT
        / "configs/trust_robot/"
        "phase5_unprivileged_udp_receiver_candidate_v1.json",

    "unprivileged_udp_receiver_module":
        ROOT
        / "src/trust_robot/"
        "unprivileged_udp_receiver.py",

    "unprivileged_udp_receiver_test":
        ROOT
        / "tests/trust_robot/"
        "test_unprivileged_udp_receiver.py",

    "unprivileged_udp_receiver_audit":
        ROOT
        / "docs/audits/trust_robot/"
        "TRUST_ROBOT_PHASE5_UNPRIVILEGED_UDP_RECEIVER_V1.md",

    "phase5_live_executor_safety":
        ROOT
        / "configs/trust_robot/"
        "phase5_live_executor_safety_candidate_v1.json",

    "live_executor_safety_module":
        ROOT
        / "src/trust_robot/"
        "live_executor_safety.py",
}


def file_sha(path):
    return sha256(
        path.read_bytes()
    ).hexdigest()


class SE4LiveExecutionTransportResolutionTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(
            CONFIG.read_text(
                encoding="utf-8"
            )
        )

    def test_01_schema(self):
        self.assertEqual(
            self.payload[
                "schema"
            ],
            SCHEMA,
        )

    def test_02_content_digest(self):
        self.assertEqual(
            self.payload[
                "content_sha256"
            ],
            content_sha256(
                self.payload
            ),
        )

    def test_03_builder_matches_config(self):
        self.assertEqual(
            self.payload,
            build_se4_live_execution_transport_resolution(),
        )

    def test_04_stage_remains_SE4_incomplete(self):
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

    def test_05_historical_pcap_freeze_not_rewritten(self):
        historical = self.payload[
            "historical_transport"
        ]

        self.assertTrue(
            historical[
                "historical_freeze_remains_hash_frozen"
            ]
        )

        self.assertFalse(
            historical[
                "historical_freeze_rewritten"
            ]
        )

    def test_06_historical_tcpdump_not_future_execution_path(self):
        self.assertFalse(
            self.payload[
                "historical_transport"
            ][
                "selected_for_future_executable_UDP_path"
            ]
        )

    def test_07_unprivileged_receiver_selected(self):
        transport = self.payload[
            "selected_future_UDP_transport"
        ]

        self.assertTrue(
            transport[
                "selected"
            ]
        )

        self.assertEqual(
            transport[
                "transport_id"
            ],
            "phase5_unprivileged_dual_udp_receiver_v1",
        )

    def test_08_receiver_implementation_and_loopback_verified(self):
        transport = self.payload[
            "selected_future_UDP_transport"
        ]

        self.assertTrue(
            transport[
                "implementation_exists"
            ]
        )

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

    def test_09_socket_semantics_exact(self):
        transport = self.payload[
            "selected_future_UDP_transport"
        ]

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

    def test_10_no_passive_sniffing_or_raw_socket(self):
        transport = self.payload[
            "selected_future_UDP_transport"
        ]

        self.assertFalse(
            transport[
                "passive_interface_sniffing"
            ]
        )

        self.assertFalse(
            transport[
                "raw_packet_socket"
            ]
        )

    def test_11_no_tcpdump_root_sudo_or_cap_net_raw(self):
        transport = self.payload[
            "selected_future_UDP_transport"
        ]

        self.assertFalse(
            transport[
                "uses_tcpdump"
            ]
        )

        self.assertFalse(
            transport[
                "requires_root"
            ]
        )

        self.assertFalse(
            transport[
                "requires_sudo"
            ]
        )

        self.assertFalse(
            transport[
                "requires_CAP_NET_RAW"
            ]
        )

    def test_12_payload_bytes_and_boundaries_preserved(self):
        evidence = self.payload[
            "preserved_UDP_evidence"
        ]

        self.assertTrue(
            evidence[
                "exact_UDP_payload_bytes"
            ]
        )

        self.assertTrue(
            evidence[
                "per_datagram_boundaries_preserved"
            ]
        )

        self.assertTrue(
            evidence[
                "per_datagram_SHA256_required"
            ]
        )

    def test_13_source_endpoint_preserved_but_not_identity_truth(self):
        evidence = self.payload[
            "preserved_UDP_evidence"
        ]

        self.assertTrue(
            evidence[
                "source_IPv4_preserved"
            ]
        )

        self.assertTrue(
            evidence[
                "source_UDP_port_preserved"
            ]
        )

    def test_14_headers_not_preserved(self):
        missing = self.payload[
            "not_preserved_by_selected_UDP_transport"
        ]

        self.assertFalse(
            missing[
                "ethernet_headers"
            ]
        )

        self.assertFalse(
            missing[
                "IP_headers"
            ]
        )

        self.assertFalse(
            missing[
                "UDP_headers"
            ]
        )

    def test_15_no_packet_loss_proof(self):
        self.assertFalse(
            self.payload[
                "not_preserved_by_selected_UDP_transport"
            ][
                "proof_of_zero_packet_loss"
            ]
        )

        self.assertFalse(
            self.payload[
                "scientific_boundary"
            ][
                "UDP_receive_proves_no_packet_loss"
            ]
        )

    def test_16_output_contract_exact(self):
        outputs = self.payload[
            "future_UDP_output_contract"
        ]

        self.assertEqual(
            outputs[
                "measurement_payload_archive"
            ],
            "measurement_payloads.bin",
        )

        self.assertEqual(
            outputs[
                "measurement_metadata"
            ],
            "measurement_datagrams.jsonl",
        )

        self.assertEqual(
            outputs[
                "position_payload_archive"
            ],
            "position_payloads.bin",
        )

        self.assertEqual(
            outputs[
                "position_metadata"
            ],
            "position_datagrams.jsonl",
        )

    def test_17_atomic_publication_contract_preserved(self):
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

    def test_18_HTTP_paths_preserved_but_not_executed(self):
        http = self.payload[
            "HTTP_transport"
        ]

        self.assertEqual(
            http[
                "identity_path"
            ],
            "/cgi/info.json",
        )

        self.assertEqual(
            http[
                "status_path"
            ],
            "/cgi/status.json",
        )

        self.assertEqual(
            http[
                "diagnostic_path"
            ],
            "/cgi/diag.json",
        )

        self.assertFalse(
            http[
                "HTTP_execution_implemented_by_this_resolution"
            ]
        )

        self.assertFalse(
            http[
                "HTTP_execution_authorized"
            ]
        )

    def test_19_all_real_runtime_values_unselected(self):
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

    def test_20_no_network_or_sensor_execution(self):
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

        self.assertFalse(
            science[
                "real_sensor_receiver_execution_verified"
            ]
        )

    def test_21_zero_real_empirical_evidence(self):
        science = self.payload[
            "scientific_boundary"
        ]

        self.assertEqual(
            science[
                "raw_real_sensor_capture_artifact_count"
            ],
            0,
        )

        self.assertEqual(
            science[
                "device_identity_receipt_count"
            ],
            0,
        )

    def test_22_zero_accepted_sources_and_labels(self):
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

    def test_23_host_receive_time_not_physical_measurement_time(self):
        self.assertFalse(
            self.payload[
                "scientific_boundary"
            ][
                "userspace_receive_time_is_physical_measurement_time"
            ]
        )

    def test_24_udp_receive_not_health_truth(self):
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

    def test_25_transport_resolution_removes_packet_sniffing_permission_gate(self):
        transition = self.payload[
            "transition_policy"
        ]

        self.assertFalse(
            transition[
                "tcpdump_required_for_selected_UDP_transport"
            ]
        )

        self.assertFalse(
            transition[
                "packet_sniffing_permission_required_for_selected_UDP_transport"
            ]
        )

    def test_26_real_sensor_execution_remains_blocked(self):
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

        with self.assertRaises(
            SE4LiveExecutionTransportResolutionError
        ):
            assert_real_sensor_execution_authorized(
                self.payload
            )

    def test_27_health_supervision_remains_blocked(self):
        with self.assertRaises(
            SE4LiveExecutionTransportResolutionError
        ):
            assert_health_supervision_available(
                self.payload
            )

    def test_28_SE4_SE5_validation_confirmation_remain_closed(self):
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

    def test_29_input_hashes_exact(self):
        for key, path in INPUT_PATHS.items():
            self.assertEqual(
                file_sha(path),
                FROZEN_INPUT_SHA256[
                    key
                ],
            )

    def test_30_validator_rejects_fake_runtime_value(self):
        changed = deepcopy(
            self.payload
        )

        changed[
            "runtime_values_intentionally_unselected"
        ][
            "bind_IPv4"
        ] = "0.0.0.0"

        with self.assertRaises(
            SE4LiveExecutionTransportResolutionError
        ):
            validate_se4_live_execution_transport_resolution(
                changed
            )

    def test_31_validator_rejects_fake_real_sensor_authorization(self):
        changed = deepcopy(
            self.payload
        )

        changed[
            "transition_policy"
        ][
            "real_sensor_execution_authorized"
        ] = True

        with self.assertRaises(
            SE4LiveExecutionTransportResolutionError
        ):
            validate_se4_live_execution_transport_resolution(
                changed
            )

    def test_32_resolution_module_performs_no_network_execution(self):
        tree = ast.parse(
            MODULE.read_text(
                encoding="utf-8"
            ),
            filename=str(
                MODULE
            ),
        )

        imported = []

        for node in ast.walk(
            tree
        ):
            if isinstance(
                node,
                ast.Import,
            ):
                imported.extend(
                    alias.name
                    for alias
                    in node.names
                )

            elif isinstance(
                node,
                ast.ImportFrom,
            ):
                imported.append(
                    node.module
                    or ""
                )

        for forbidden in (
            "socket",
            "subprocess",
            "requests",
            "urllib",
            "http.client",
        ):
            self.assertFalse(
                any(
                    forbidden
                    in module.lower()
                    for module
                    in imported
                ),
                (
                    forbidden,
                    imported,
                ),
            )

    def test_33_no_execute_accept_label_or_train_API(self):
        tree = ast.parse(
            MODULE.read_text(
                encoding="utf-8"
            ),
            filename=str(
                MODULE
            ),
        )

        names = {
            node.name.lower()
            for node
            in tree.body
            if isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                ),
            )
        }

        for forbidden in (
            "execute",
            "capture",
            "run_capture",
            "accept_source",
            "accept_supervision_source",
            "assign_health_label",
            "train",
            "fit",
            "predict",
        ):
            self.assertNotIn(
                forbidden,
                names,
            )


if __name__ == "__main__":
    unittest.main()
