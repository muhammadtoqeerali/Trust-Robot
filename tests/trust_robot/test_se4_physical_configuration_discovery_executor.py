from pathlib import Path
from unittest.mock import patch
import hashlib
import json
import unittest

from trust_robot.se4_physical_configuration_discovery import (
    AUTHORIZATION_ACKNOWLEDGEMENT,
    build_discovery_authorization_candidate,
    build_discovery_candidate,
)

from trust_robot.se4_physical_configuration_discovery_executor import (
    EXECUTOR_CONTRACT_SCHEMA,
    EXTERNAL_AUTHORIZATION_RECORD_SCHEMA,
    SE4PhysicalConfigurationDiscoveryExecutionError,
    build_executor_contract,
    execute_bounded_configuration_discovery,
    validate_execution_inputs,
    validate_external_authorization_record,
)


ROOT = Path(
    __file__
).resolve().parents[2]

CONFIG = (
    ROOT
    / "configs/trust_robot/"
    "se4_physical_configuration_discovery_executor_v1.json"
)


def discovery():
    return build_discovery_candidate(
        discovery_id="discovery_test",
        interface="eno1",
        temporary_host_ipv4="192.168.1.100",
        candidate_sensor_ipv4="192.168.1.201",
        candidate_http_port=80,
        connect_timeout_seconds=2,
        total_timeout_seconds=5,
    )


def record(
    candidate,
):
    return {
        "schema":
            EXTERNAL_AUTHORIZATION_RECORD_SCHEMA,

        "schema_version":
            1,

        "record_source":
            "test",

        "authority_basis":
            "test authority",

        "authority_basis_independently_verified_by_software":
            False,

        "scope":
            "read_only_physical_configuration_discovery",

        "discovery_sha256":
            candidate[
                "discovery_sha256"
            ],

        "authorization_statement":
            AUTHORIZATION_ACKNOWLEDGEMENT,

        "authorized_for_configuration_discovery":
            True,

        "declared_before_discovery":
            True,

        "real_TRAIN_execution_authorized":
            False,

        "source_acceptance_authorized":
            False,

        "health_label_generation_authorized":
            False,

        "SE4_training_authorized":
            False,

        "SE5_may_proceed":
            False,

        "record_created_utc":
            "2026-01-01T00:00:00Z",

        "record_time_is_sensor_measurement_time":
            False,
    }


def record_bytes(
    value,
):
    return (
        json.dumps(
            value,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode(
        "utf-8"
    )


def inputs():
    candidate = discovery()

    authorization_record = record(
        candidate
    )

    record_sha = hashlib.sha256(
        record_bytes(
            authorization_record
        )
    ).hexdigest()

    authorization = (
        build_discovery_authorization_candidate(
            authorization_id="auth_test",
            discovery_sha256=
                candidate[
                    "discovery_sha256"
                ],
            authorization_record_sha256=
                record_sha,
            authorized_for_configuration_discovery=
                True,
            declared_before_discovery=
                True,
        )
    )

    return (
        candidate,
        authorization_record,
        record_sha,
        authorization,
    )


class FakeResponse:
    def __init__(
        self,
        *,
        status=200,
        body=b"{}",
        reason="OK",
    ):
        self.status = status
        self.reason = reason
        self._body = body

    def read(
        self,
        size,
    ):
        return self._body[
            :size
        ]


class FakeConnection:
    instances = []
    responses = []

    def __init__(
        self,
        *,
        host,
        port,
        timeout,
        source_address,
    ):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.source_address = source_address
        self.requests = []
        self.closed = False

        type(
            self
        ).instances.append(
            self
        )

    def request(
        self,
        *,
        method,
        url,
        headers,
    ):
        self.requests.append(
            (
                method,
                url,
                headers,
            )
        )

    def getresponse(
        self,
    ):
        return type(
            self
        ).responses.pop(
            0
        )

    def close(
        self,
    ):
        self.closed = True


class SE4PhysicalConfigurationDiscoveryExecutorTests(
    unittest.TestCase
):
    def setUp(
        self,
    ):
        FakeConnection.instances = []
        FakeConnection.responses = []

    def test_01_contract_schema(self):
        self.assertEqual(
            build_executor_contract()[
                "schema"
            ],
            EXECUTOR_CONTRACT_SCHEMA,
        )

    def test_02_checked_in_contract(self):
        self.assertEqual(
            json.loads(
                CONFIG.read_text(
                    encoding="utf-8"
                )
            ),
            build_executor_contract(),
        )

    def test_03_GET_only(self):
        self.assertEqual(
            build_executor_contract()[
                "HTTP_method"
            ],
            "GET",
        )

    def test_04_two_request_maximum(self):
        self.assertEqual(
            build_executor_contract()[
                "maximum_HTTP_request_count"
            ],
            2,
        )

    def test_05_no_retries(self):
        self.assertFalse(
            build_executor_contract()[
                "retry_allowed"
            ]
        )

    def test_06_no_redirects(self):
        self.assertFalse(
            build_executor_contract()[
                "redirect_following_allowed"
            ]
        )

    def test_07_no_fallback_search(self):
        self.assertFalse(
            build_executor_contract()[
                "fallback_endpoint_search_allowed"
            ]
        )

    def test_08_no_sensor_writes(self):
        self.assertFalse(
            build_executor_contract()[
                "sensor_configuration_write_allowed"
            ]
        )

    def test_09_no_UDP_acquisition(self):
        self.assertFalse(
            build_executor_contract()[
                "UDP_measurement_acquisition_allowed"
            ]
        )

    def test_10_no_TRAIN_authorization(self):
        self.assertFalse(
            build_executor_contract()[
                "real_TRAIN_execution_authorized"
            ]
        )

    def test_11_no_source_acceptance(self):
        self.assertFalse(
            build_executor_contract()[
                "source_acceptance_authorized"
            ]
        )

    def test_12_no_health_labels(self):
        self.assertFalse(
            build_executor_contract()[
                "health_label_generation_authorized"
            ]
        )

    def test_13_external_record_validation(self):
        candidate, external, _, _ = inputs()

        validate_external_authorization_record(
            external,
            expected_discovery_sha256=
                candidate[
                    "discovery_sha256"
                ],
            expected_acknowledgement=
                AUTHORIZATION_ACKNOWLEDGEMENT,
        )

    def test_14_wrong_external_binding_rejected(self):
        candidate, external, _, _ = inputs()

        external[
            "discovery_sha256"
        ] = "0" * 64

        with self.assertRaises(
            SE4PhysicalConfigurationDiscoveryExecutionError
        ):
            validate_external_authorization_record(
                external,
                expected_discovery_sha256=
                    candidate[
                        "discovery_sha256"
                    ],
                expected_acknowledgement=
                    AUTHORIZATION_ACKNOWLEDGEMENT,
            )

    def test_15_wrong_ack_rejected_before_execution(self):
        candidate, external, record_sha, authorization = inputs()

        with self.assertRaises(
            SE4PhysicalConfigurationDiscoveryExecutionError
        ):
            validate_execution_inputs(
                discovery_candidate=
                    candidate,
                discovery_authorization=
                    authorization,
                external_authorization_record=
                    external,
                external_authorization_record_sha256=
                    record_sha,
                operator_acknowledgement=
                    "WRONG",
            )

    def test_16_record_digest_mismatch_rejected(self):
        candidate, external, _, authorization = inputs()

        with self.assertRaises(
            SE4PhysicalConfigurationDiscoveryExecutionError
        ):
            validate_execution_inputs(
                discovery_candidate=
                    candidate,
                discovery_authorization=
                    authorization,
                external_authorization_record=
                    external,
                external_authorization_record_sha256=
                    "f" * 64,
                operator_acknowledgement=
                    AUTHORIZATION_ACKNOWLEDGEMENT,
            )

    def test_17_success_uses_two_GETs(self):
        candidate, external, record_sha, authorization = inputs()

        FakeConnection.responses = [
            FakeResponse(
                body=b'{"model":"VLP-32C"}'
            ),
            FakeResponse(
                body=b'{"config":{}}'
            ),
        ]

        with patch(
            "trust_robot.se4_physical_configuration_discovery_executor."
            "http.client.HTTPConnection",
            FakeConnection,
        ), patch(
            "trust_robot.se4_physical_configuration_discovery_executor."
            "time.sleep",
        ):
            result = execute_bounded_configuration_discovery(
                discovery_candidate=
                    candidate,
                discovery_authorization=
                    authorization,
                external_authorization_record=
                    external,
                external_authorization_record_sha256=
                    record_sha,
                operator_acknowledgement=
                    AUTHORIZATION_ACKNOWLEDGEMENT,
            )

        self.assertTrue(
            result[
                "execution_completed"
            ]
        )

        self.assertEqual(
            result[
                "request_count_attempted"
            ],
            2,
        )

        methods = [
            request[
                0
            ]
            for connection
            in FakeConnection.instances
            for request
            in connection.requests
        ]

        self.assertEqual(
            methods,
            [
                "GET",
                "GET",
            ],
        )

    def test_18_exact_paths_only(self):
        candidate, external, record_sha, authorization = inputs()

        FakeConnection.responses = [
            FakeResponse(),
            FakeResponse(),
        ]

        with patch(
            "trust_robot.se4_physical_configuration_discovery_executor."
            "http.client.HTTPConnection",
            FakeConnection,
        ), patch(
            "trust_robot.se4_physical_configuration_discovery_executor."
            "time.sleep",
        ):
            execute_bounded_configuration_discovery(
                discovery_candidate=
                    candidate,
                discovery_authorization=
                    authorization,
                external_authorization_record=
                    external,
                external_authorization_record_sha256=
                    record_sha,
                operator_acknowledgement=
                    AUTHORIZATION_ACKNOWLEDGEMENT,
            )

        paths = [
            request[
                1
            ]
            for connection
            in FakeConnection.instances
            for request
            in connection.requests
        ]

        self.assertEqual(
            paths,
            [
                "/cgi/info.json",
                "/cgi/snapshot.hdl",
            ],
        )

    def test_19_source_address_bound(self):
        candidate, external, record_sha, authorization = inputs()

        FakeConnection.responses = [
            FakeResponse(),
            FakeResponse(),
        ]

        with patch(
            "trust_robot.se4_physical_configuration_discovery_executor."
            "http.client.HTTPConnection",
            FakeConnection,
        ), patch(
            "trust_robot.se4_physical_configuration_discovery_executor."
            "time.sleep",
        ):
            execute_bounded_configuration_discovery(
                discovery_candidate=
                    candidate,
                discovery_authorization=
                    authorization,
                external_authorization_record=
                    external,
                external_authorization_record_sha256=
                    record_sha,
                operator_acknowledgement=
                    AUTHORIZATION_ACKNOWLEDGEMENT,
            )

        self.assertTrue(
            all(
                item.source_address[
                    0
                ] == "192.168.1.100"
                for item
                in FakeConnection.instances
            )
        )

    def test_20_HTTP_endpoint_bound(self):
        candidate, external, record_sha, authorization = inputs()

        FakeConnection.responses = [
            FakeResponse(),
            FakeResponse(),
        ]

        with patch(
            "trust_robot.se4_physical_configuration_discovery_executor."
            "http.client.HTTPConnection",
            FakeConnection,
        ), patch(
            "trust_robot.se4_physical_configuration_discovery_executor."
            "time.sleep",
        ):
            execute_bounded_configuration_discovery(
                discovery_candidate=
                    candidate,
                discovery_authorization=
                    authorization,
                external_authorization_record=
                    external,
                external_authorization_record_sha256=
                    record_sha,
                operator_acknowledgement=
                    AUTHORIZATION_ACKNOWLEDGEMENT,
            )

        self.assertTrue(
            all(
                item.host == "192.168.1.201"
                and item.port == 80
                for item
                in FakeConnection.instances
            )
        )

    def test_21_non_200_stops_after_first(self):
        candidate, external, record_sha, authorization = inputs()

        FakeConnection.responses = [
            FakeResponse(
                status=404,
                reason="Not Found",
            ),
            FakeResponse(),
        ]

        with patch(
            "trust_robot.se4_physical_configuration_discovery_executor."
            "http.client.HTTPConnection",
            FakeConnection,
        ), patch(
            "trust_robot.se4_physical_configuration_discovery_executor."
            "time.sleep",
        ):
            result = execute_bounded_configuration_discovery(
                discovery_candidate=
                    candidate,
                discovery_authorization=
                    authorization,
                external_authorization_record=
                    external,
                external_authorization_record_sha256=
                    record_sha,
                operator_acknowledgement=
                    AUTHORIZATION_ACKNOWLEDGEMENT,
            )

        self.assertFalse(
            result[
                "execution_completed"
            ]
        )

        self.assertEqual(
            result[
                "request_count_attempted"
            ],
            1,
        )

        self.assertTrue(
            result[
                "sensor_contact_confirmed"
            ]
        )

    def test_22_connection_failure_stops_after_first(self):
        candidate, external, record_sha, authorization = inputs()

        class FailingConnection(
            FakeConnection
        ):
            def getresponse(
                self,
            ):
                raise TimeoutError(
                    "test timeout"
                )

        with patch(
            "trust_robot.se4_physical_configuration_discovery_executor."
            "http.client.HTTPConnection",
            FailingConnection,
        ), patch(
            "trust_robot.se4_physical_configuration_discovery_executor."
            "time.sleep",
        ):
            result = execute_bounded_configuration_discovery(
                discovery_candidate=
                    candidate,
                discovery_authorization=
                    authorization,
                external_authorization_record=
                    external,
                external_authorization_record_sha256=
                    record_sha,
                operator_acknowledgement=
                    AUTHORIZATION_ACKNOWLEDGEMENT,
            )

        self.assertFalse(
            result[
                "execution_completed"
            ]
        )

        self.assertEqual(
            result[
                "request_count_attempted"
            ],
            1,
        )

        self.assertFalse(
            result[
                "sensor_contact_confirmed"
            ]
        )

    def test_23_connections_closed(self):
        candidate, external, record_sha, authorization = inputs()

        FakeConnection.responses = [
            FakeResponse(),
            FakeResponse(),
        ]

        with patch(
            "trust_robot.se4_physical_configuration_discovery_executor."
            "http.client.HTTPConnection",
            FakeConnection,
        ), patch(
            "trust_robot.se4_physical_configuration_discovery_executor."
            "time.sleep",
        ):
            execute_bounded_configuration_discovery(
                discovery_candidate=
                    candidate,
                discovery_authorization=
                    authorization,
                external_authorization_record=
                    external,
                external_authorization_record_sha256=
                    record_sha,
                operator_acknowledgement=
                    AUTHORIZATION_ACKNOWLEDGEMENT,
            )

        self.assertTrue(
            all(
                item.closed
                for item
                in FakeConnection.instances
            )
        )

    def test_24_success_does_not_change_scientific_authority(self):
        contract = build_executor_contract()

        self.assertFalse(
            contract[
                "real_TRAIN_execution_authorized"
            ]
        )

        self.assertFalse(
            contract[
                "source_acceptance_authorized"
            ]
        )

        self.assertFalse(
            contract[
                "health_label_generation_authorized"
            ]
        )

        self.assertFalse(
            contract[
                "SE4_training_authorized"
            ]
        )

        self.assertFalse(
            contract[
                "SE5_may_proceed"
            ]
        )


if __name__ == "__main__":
    unittest.main()
