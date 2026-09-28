from pathlib import Path
import ast
import json
import unittest

from trust_robot.se4_physical_configuration_discovery import (
    AUTHORIZATION_ACKNOWLEDGEMENT,
    AUTHORIZATION_SCHEMA,
    DISCOVERY_SCHEMA,
    MANUFACTURER_FACTORY_HTTP_PORT_CANDIDATE,
    MANUFACTURER_FACTORY_MEASUREMENT_PORT_CANDIDATE,
    MANUFACTURER_FACTORY_POSITION_PORT_CANDIDATE,
    MANUFACTURER_FACTORY_SENSOR_IPV4_CANDIDATE,
    MAX_HTTP_REQUEST_COUNT,
    MINIMUM_REQUEST_SPACING_SECONDS,
    PROTOCOL_SCHEMA,
    SE4PhysicalConfigurationDiscoveryError,
    TEMPORARY_HOST_IPV4_CANDIDATE,
    authorization_content_sha256,
    build_discovery_authorization_candidate,
    build_discovery_candidate,
    build_physical_configuration_discovery_protocol,
    discovery_content_sha256,
    protocol_content_sha256,
    validate_discovery_authorization_candidate,
    validate_discovery_candidate,
    validate_physical_configuration_discovery_protocol,
)


ROOT = Path(
    __file__
).resolve().parents[2]

MODULE = (
    ROOT
    / "src/trust_robot/"
    "se4_physical_configuration_discovery.py"
)

CONFIG = (
    ROOT
    / "configs/trust_robot/"
    "se4_physical_configuration_discovery_protocol_v1.json"
)


def candidate():
    return build_discovery_candidate(
        discovery_id="vlp32c_discovery_001",
        interface="eno1",
        temporary_host_ipv4="192.168.1.100",
        candidate_sensor_ipv4="192.168.1.201",
        candidate_http_port=80,
        connect_timeout_seconds=2,
        total_timeout_seconds=5,
    )


def authorization(
    discovery,
    *,
    granted=True,
):
    return build_discovery_authorization_candidate(
        authorization_id="discovery_auth_001",
        discovery_sha256=
            discovery[
                "discovery_sha256"
            ],
        authorization_record_sha256=
            "a" * 64,
        authorized_for_configuration_discovery=
            granted,
        declared_before_discovery=True,
    )


class SE4PhysicalConfigurationDiscoveryTests(
    unittest.TestCase
):
    def test_01_protocol_schema(self):
        self.assertEqual(
            build_physical_configuration_discovery_protocol()[
                "schema"
            ],
            PROTOCOL_SCHEMA,
        )

    def test_02_protocol_config_is_canonical(self):
        payload = json.loads(
            CONFIG.read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(
            payload,
            build_physical_configuration_discovery_protocol(),
        )

        validate_physical_configuration_discovery_protocol(
            payload
        )

    def test_03_protocol_content_hash(self):
        payload = (
            build_physical_configuration_discovery_protocol()
        )

        self.assertEqual(
            payload[
                "content_sha256"
            ],
            protocol_content_sha256(
                payload
            ),
        )

    def test_04_discovery_schema(self):
        self.assertEqual(
            candidate()[
                "schema"
            ],
            DISCOVERY_SCHEMA,
        )

    def test_05_factory_sensor_IP_is_candidate(self):
        self.assertEqual(
            MANUFACTURER_FACTORY_SENSOR_IPV4_CANDIDATE,
            "192.168.1.201",
        )

    def test_06_factory_HTTP_port_is_candidate(self):
        self.assertEqual(
            MANUFACTURER_FACTORY_HTTP_PORT_CANDIDATE,
            80,
        )

    def test_07_factory_measurement_port_is_candidate(self):
        self.assertEqual(
            MANUFACTURER_FACTORY_MEASUREMENT_PORT_CANDIDATE,
            2368,
        )

    def test_08_factory_position_port_is_candidate(self):
        self.assertEqual(
            MANUFACTURER_FACTORY_POSITION_PORT_CANDIDATE,
            8308,
        )

    def test_09_temporary_host_candidate(self):
        self.assertEqual(
            TEMPORARY_HOST_IPV4_CANDIDATE,
            "192.168.1.100",
        )

    def test_10_allowed_paths_are_identity_and_snapshot_only(self):
        self.assertEqual(
            candidate()[
                "allowed_paths"
            ],
            [
                "/cgi/info.json",
                "/cgi/snapshot.hdl",
            ],
        )

    def test_11_GET_only(self):
        self.assertEqual(
            candidate()[
                "HTTP_method"
            ],
            "GET",
        )

    def test_12_at_most_two_requests(self):
        self.assertEqual(
            MAX_HTTP_REQUEST_COUNT,
            2,
        )

    def test_13_request_spacing_at_least_one_second(self):
        self.assertGreaterEqual(
            MINIMUM_REQUEST_SPACING_SECONDS,
            1,
        )

    def test_14_active_discovery_scans_are_forbidden(self):
        controls = candidate()[
            "network_controls"
        ]

        self.assertFalse(
            controls[
                "ping_allowed"
            ]
        )

        self.assertFalse(
            controls[
                "port_scan_allowed"
            ]
        )

        self.assertFalse(
            controls[
                "ARP_scan_allowed"
            ]
        )

        self.assertFalse(
            controls[
                "subnet_scan_allowed"
            ]
        )

    def test_15_HTTP_write_methods_are_forbidden(self):
        controls = candidate()[
            "network_controls"
        ]

        for key in (
            "HTTP_POST_allowed",
            "HTTP_PUT_allowed",
            "HTTP_PATCH_allowed",
            "HTTP_DELETE_allowed",
        ):
            self.assertFalse(
                controls[
                    key
                ]
            )

    def test_16_factory_defaults_are_not_binding_truth(self):
        interpretation = candidate()[
            "interpretation"
        ]

        self.assertFalse(
            interpretation[
                "manufacturer_defaults_are_current_sensor_configuration"
            ]
        )

        self.assertFalse(
            interpretation[
                "manufacturer_defaults_are_runtime_binding"
            ]
        )

    def test_17_discovery_is_not_runtime_binding(self):
        self.assertFalse(
            candidate()[
                "interpretation"
            ][
                "successful_discovery_is_real_TRAIN_runtime_binding"
            ]
        )

    def test_18_repository_state_has_zero_network_execution(self):
        state = (
            build_physical_configuration_discovery_protocol()[
                "current_state"
            ]
        )

        self.assertFalse(
            state[
                "real_sensor_network_IO_executed"
            ]
        )

        self.assertFalse(
            state[
                "real_sensor_contact"
            ]
        )

    def test_19_scientific_boundary_remains_closed(self):
        boundary = candidate()[
            "scientific_boundary"
        ]

        self.assertFalse(
            boundary[
                "source_acceptance_authorized"
            ]
        )

        self.assertFalse(
            boundary[
                "health_label_generation_authorized"
            ]
        )

        self.assertFalse(
            boundary[
                "SE4_complete"
            ]
        )

        self.assertFalse(
            boundary[
                "SE5_may_proceed"
            ]
        )

    def test_20_discovery_hash_is_canonical(self):
        payload = candidate()

        self.assertEqual(
            payload[
                "discovery_sha256"
            ],
            discovery_content_sha256(
                payload
            ),
        )

        validate_discovery_candidate(
            payload
        )

    def test_21_same_host_and_sensor_IP_rejected(self):
        with self.assertRaises(
            SE4PhysicalConfigurationDiscoveryError
        ):
            build_discovery_candidate(
                discovery_id="bad",
                interface="eno1",
                temporary_host_ipv4="192.168.1.201",
                candidate_sensor_ipv4="192.168.1.201",
                candidate_http_port=80,
                connect_timeout_seconds=2,
                total_timeout_seconds=5,
            )

    def test_22_timeout_order_rejected(self):
        with self.assertRaises(
            SE4PhysicalConfigurationDiscoveryError
        ):
            build_discovery_candidate(
                discovery_id="bad",
                interface="eno1",
                temporary_host_ipv4="192.168.1.100",
                candidate_sensor_ipv4="192.168.1.201",
                candidate_http_port=80,
                connect_timeout_seconds=5,
                total_timeout_seconds=2,
            )

    def test_23_unsafe_identifier_rejected(self):
        with self.assertRaises(
            SE4PhysicalConfigurationDiscoveryError
        ):
            build_discovery_candidate(
                discovery_id="../bad",
                interface="eno1",
                temporary_host_ipv4="192.168.1.100",
                candidate_sensor_ipv4="192.168.1.201",
                candidate_http_port=80,
                connect_timeout_seconds=2,
                total_timeout_seconds=5,
            )

    def test_24_authorization_schema(self):
        discovery = candidate()

        self.assertEqual(
            authorization(
                discovery
            )[
                "schema"
            ],
            AUTHORIZATION_SCHEMA,
        )

    def test_25_authorization_hash_binds_discovery(self):
        discovery = candidate()

        auth = authorization(
            discovery
        )

        self.assertEqual(
            auth[
                "discovery_sha256"
            ],
            discovery[
                "discovery_sha256"
            ],
        )

        self.assertEqual(
            auth[
                "authorization_sha256"
            ],
            authorization_content_sha256(
                auth
            ),
        )

        validate_discovery_authorization_candidate(
            auth,
            expected_discovery_sha256=
                discovery[
                    "discovery_sha256"
                ],
        )

    def test_26_ungranted_authorization_rejected(self):
        discovery = candidate()

        with self.assertRaises(
            SE4PhysicalConfigurationDiscoveryError
        ):
            validate_discovery_authorization_candidate(
                authorization(
                    discovery,
                    granted=False,
                ),
                expected_discovery_sha256=
                    discovery[
                        "discovery_sha256"
                    ],
            )

    def test_27_authorization_cannot_open_scientific_boundary(self):
        discovery = candidate()

        auth = authorization(
            discovery
        )

        self.assertFalse(
            auth[
                "real_TRAIN_execution_authorized"
            ]
        )

        self.assertFalse(
            auth[
                "source_acceptance_authorized"
            ]
        )

        self.assertFalse(
            auth[
                "health_label_generation_authorized"
            ]
        )

        self.assertEqual(
            auth[
                "required_operator_acknowledgement"
            ],
            AUTHORIZATION_ACKNOWLEDGEMENT,
        )

    def test_28_protocol_module_has_no_network_executor_imports(self):
        tree = ast.parse(
            MODULE.read_text(
                encoding="utf-8"
            ),
            filename=str(
                MODULE
            ),
        )

        imported = set()

        for node in ast.walk(
            tree
        ):
            if isinstance(
                node,
                ast.Import,
            ):
                imported.update(
                    item.name.split(
                        "."
                    )[0]
                    for item
                    in node.names
                )

            elif isinstance(
                node,
                ast.ImportFrom,
            ) and node.module:
                imported.add(
                    node.module.split(
                        "."
                    )[0]
                )

        for forbidden in (
            "socket",
            "subprocess",
            "requests",
            "urllib",
            "http",
        ):
            self.assertNotIn(
                forbidden,
                imported,
            )


if __name__ == "__main__":
    unittest.main()
