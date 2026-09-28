"""Bounded SE4 physical-configuration discovery executor.

This module is intentionally separate from real TRAIN execution.

It may perform only the explicitly authorized read-only configuration
discovery represented by a canonical discovery candidate and its separate
hash-bound authorization record.

It does not:
* scan a network;
* search alternate sensor addresses;
* write sensor configuration;
* receive TRAIN UDP measurements;
* authorize source acceptance;
* authorize health labels;
* authorize SE4 training.
"""

from __future__ import annotations

from hashlib import sha256
import http.client
import json
import time
from typing import Mapping

from trust_robot.se4_physical_configuration_discovery import (
    ALLOWED_READ_ONLY_PATHS,
    AUTHORIZATION_ACKNOWLEDGEMENT,
    DISCOVERY_SCOPE,
    MAX_HTTP_REQUEST_COUNT,
    MINIMUM_REQUEST_SPACING_SECONDS,
    validate_discovery_authorization_candidate,
    validate_discovery_candidate,
)


EXECUTOR_CONTRACT_SCHEMA = (
    "TRUST_ROBOT_SE4_PHYSICAL_CONFIGURATION_DISCOVERY_EXECUTOR_V1"
)

EXTERNAL_AUTHORIZATION_RECORD_SCHEMA = (
    "TRUST_ROBOT_SE4_EXTERNAL_CONFIGURATION_DISCOVERY_AUTHORIZATION_RECORD_V1"
)

MAX_RESPONSE_BYTES = 4 * 1024 * 1024


class SE4PhysicalConfigurationDiscoveryExecutionError(
    RuntimeError
):
    """Raised before network I/O when execution inputs are invalid."""


def file_sha256_bytes(
    data: bytes,
) -> str:
    return sha256(
        data
    ).hexdigest()


def validate_external_authorization_record(
    payload: Mapping[str, object],
    *,
    expected_discovery_sha256: str,
    expected_acknowledgement: str,
) -> Mapping[str, object]:
    if not isinstance(
        payload,
        Mapping,
    ):
        raise SE4PhysicalConfigurationDiscoveryExecutionError(
            "external authorization record must be mapping"
        )

    required = {
        "schema",
        "schema_version",
        "record_source",
        "authority_basis",
        "authority_basis_independently_verified_by_software",
        "scope",
        "discovery_sha256",
        "authorization_statement",
        "authorized_for_configuration_discovery",
        "declared_before_discovery",
        "real_TRAIN_execution_authorized",
        "source_acceptance_authorized",
        "health_label_generation_authorized",
        "SE4_training_authorized",
        "SE5_may_proceed",
        "record_created_utc",
        "record_time_is_sensor_measurement_time",
    }

    if set(
        payload
    ) != required:
        raise SE4PhysicalConfigurationDiscoveryExecutionError(
            "external authorization record fields differ from contract"
        )

    if payload[
        "schema"
    ] != EXTERNAL_AUTHORIZATION_RECORD_SCHEMA:
        raise SE4PhysicalConfigurationDiscoveryExecutionError(
            "external authorization record schema mismatch"
        )

    if payload[
        "schema_version"
    ] != 1:
        raise SE4PhysicalConfigurationDiscoveryExecutionError(
            "external authorization schema version mismatch"
        )

    if payload[
        "scope"
    ] != DISCOVERY_SCOPE:
        raise SE4PhysicalConfigurationDiscoveryExecutionError(
            "external authorization scope mismatch"
        )

    if payload[
        "discovery_sha256"
    ] != expected_discovery_sha256:
        raise SE4PhysicalConfigurationDiscoveryExecutionError(
            "external authorization is not bound to discovery candidate"
        )

    if payload[
        "authorization_statement"
    ] != expected_acknowledgement:
        raise SE4PhysicalConfigurationDiscoveryExecutionError(
            "operator acknowledgement mismatch"
        )

    if payload[
        "authorized_for_configuration_discovery"
    ] is not True:
        raise SE4PhysicalConfigurationDiscoveryExecutionError(
            "configuration discovery not externally authorized"
        )

    if payload[
        "declared_before_discovery"
    ] is not True:
        raise SE4PhysicalConfigurationDiscoveryExecutionError(
            "authorization must precede discovery"
        )

    if payload[
        "authority_basis_independently_verified_by_software"
    ] is not False:
        raise SE4PhysicalConfigurationDiscoveryExecutionError(
            "software may not claim independent authority verification"
        )

    for field in (
        "real_TRAIN_execution_authorized",
        "source_acceptance_authorized",
        "health_label_generation_authorized",
        "SE4_training_authorized",
        "SE5_may_proceed",
        "record_time_is_sensor_measurement_time",
    ):
        if payload[
            field
        ] is not False:
            raise SE4PhysicalConfigurationDiscoveryExecutionError(
                field
                + " must remain false"
            )

    return payload


def validate_execution_inputs(
    *,
    discovery_candidate: Mapping[str, object],
    discovery_authorization: Mapping[str, object],
    external_authorization_record: Mapping[str, object],
    external_authorization_record_sha256: str,
    operator_acknowledgement: str,
) -> None:
    validate_discovery_candidate(
        discovery_candidate
    )

    validate_discovery_authorization_candidate(
        discovery_authorization,
        expected_discovery_sha256=
            discovery_candidate[
                "discovery_sha256"
            ],
    )

    validate_external_authorization_record(
        external_authorization_record,
        expected_discovery_sha256=
            discovery_candidate[
                "discovery_sha256"
            ],
        expected_acknowledgement=
            operator_acknowledgement,
    )

    if operator_acknowledgement != AUTHORIZATION_ACKNOWLEDGEMENT:
        raise SE4PhysicalConfigurationDiscoveryExecutionError(
            "exact operator acknowledgement required"
        )

    if (
        discovery_authorization[
            "authorization_record_sha256"
        ]
        != external_authorization_record_sha256
    ):
        raise SE4PhysicalConfigurationDiscoveryExecutionError(
            "authorization record digest mismatch"
        )


def build_executor_contract(
) -> dict[str, object]:
    return {
        "schema":
            EXECUTOR_CONTRACT_SCHEMA,

        "schema_version":
            1,

        "scope":
            DISCOVERY_SCOPE,

        "HTTP_method":
            "GET",

        "allowed_paths":
            list(
                ALLOWED_READ_ONLY_PATHS
            ),

        "maximum_HTTP_request_count":
            MAX_HTTP_REQUEST_COUNT,

        "minimum_request_spacing_seconds":
            MINIMUM_REQUEST_SPACING_SECONDS,

        "maximum_response_bytes":
            MAX_RESPONSE_BYTES,

        "redirect_following_allowed":
            False,

        "retry_allowed":
            False,

        "fallback_endpoint_search_allowed":
            False,

        "sensor_configuration_write_allowed":
            False,

        "UDP_measurement_acquisition_allowed":
            False,

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
    }


def execute_bounded_configuration_discovery(
    *,
    discovery_candidate: Mapping[str, object],
    discovery_authorization: Mapping[str, object],
    external_authorization_record: Mapping[str, object],
    external_authorization_record_sha256: str,
    operator_acknowledgement: str,
) -> dict[str, object]:
    """Perform at most the two canonical read-only GET requests.

    There are no retries, redirects, alternate endpoints, or write requests.

    A failed first request stops execution before request two.
    """

    validate_execution_inputs(
        discovery_candidate=
            discovery_candidate,

        discovery_authorization=
            discovery_authorization,

        external_authorization_record=
            external_authorization_record,

        external_authorization_record_sha256=
            external_authorization_record_sha256,

        operator_acknowledgement=
            operator_acknowledgement,
    )

    candidate = dict(
        discovery_candidate
    )

    host = candidate[
        "candidate_sensor_ipv4"
    ]

    port = candidate[
        "candidate_http_port"
    ]

    source_address = (
        candidate[
            "temporary_host_ipv4"
        ],
        0,
    )

    timeout = candidate[
        "total_timeout_seconds"
    ]

    paths = tuple(
        candidate[
            "allowed_paths"
        ]
    )

    if paths != ALLOWED_READ_ONLY_PATHS:
        raise SE4PhysicalConfigurationDiscoveryExecutionError(
            "candidate paths differ from frozen protocol"
        )

    if len(
        paths
    ) > MAX_HTTP_REQUEST_COUNT:
        raise SE4PhysicalConfigurationDiscoveryExecutionError(
            "request count exceeds frozen maximum"
        )

    responses = []
    attempted_paths = []

    for index, path in enumerate(
        paths,
        start=1,
    ):
        attempted_paths.append(
            path
        )

        connection = None

        try:
            connection = http.client.HTTPConnection(
                host=
                    host,

                port=
                    port,

                timeout=
                    timeout,

                source_address=
                    source_address,
            )

            connection.request(
                method="GET",
                url=path,
                headers={
                    "Accept":
                        "application/json,text/plain,*/*",

                    "Connection":
                        "close",

                    "User-Agent":
                        "TRUST-ROBOT-SE4-ConfigurationDiscovery/1",
                },
            )

            response = connection.getresponse()

            body = response.read(
                MAX_RESPONSE_BYTES + 1
            )

            if len(
                body
            ) > MAX_RESPONSE_BYTES:
                return {
                    "execution_completed":
                        False,

                    "network_IO_executed":
                        True,

                    "sensor_contact_confirmed":
                        True,

                    "request_count_attempted":
                        index,

                    "attempted_paths":
                        attempted_paths,

                    "responses":
                        responses,

                    "failure_reason":
                        "response_exceeded_maximum_size",
                }

            response_record = {
                "path":
                    path,

                "HTTP_status":
                    response.status,

                "HTTP_reason":
                    response.reason,

                "body_bytes":
                    len(
                        body
                    ),

                "body_sha256":
                    file_sha256_bytes(
                        body
                    ),

                "body":
                    body,
            }

            responses.append(
                response_record
            )

            if response.status != 200:
                return {
                    "execution_completed":
                        False,

                    "network_IO_executed":
                        True,

                    "sensor_contact_confirmed":
                        True,

                    "request_count_attempted":
                        index,

                    "attempted_paths":
                        attempted_paths,

                    "responses":
                        responses,

                    "failure_reason":
                        "unexpected_HTTP_status_"
                        + str(
                            response.status
                        ),
                }

        except Exception as exc:
            return {
                "execution_completed":
                    False,

                "network_IO_executed":
                    True,

                "sensor_contact_confirmed":
                    bool(
                        responses
                    ),

                "request_count_attempted":
                    index,

                "attempted_paths":
                    attempted_paths,

                "responses":
                    responses,

                "failure_reason":
                    type(
                        exc
                    ).__name__
                    + ": "
                    + str(
                        exc
                    ),
            }

        finally:
            if connection is not None:
                try:
                    connection.close()
                except Exception:
                    pass

        if index < len(
            paths
        ):
            time.sleep(
                MINIMUM_REQUEST_SPACING_SECONDS
            )

    return {
        "execution_completed":
            True,

        "network_IO_executed":
            True,

        "sensor_contact_confirmed":
            True,

        "request_count_attempted":
            len(
                paths
            ),

        "attempted_paths":
            attempted_paths,

        "responses":
            responses,

        "failure_reason":
            None,
    }
