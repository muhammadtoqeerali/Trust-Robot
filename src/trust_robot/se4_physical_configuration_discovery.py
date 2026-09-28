"""SE4 bounded physical-configuration discovery protocol.

This module resolves a bootstrap boundary only.

The promoted real-TRAIN runtime-binding contract requires externally grounded
physical values before real TRAIN network execution. Manufacturer-documented
factory defaults can be used only as bounded discovery candidates; they are not
runtime-binding truth.

This module defines and validates:
* one read-only configuration-discovery candidate;
* one separate hash-bound discovery authorization artifact;
* one zero-execution repository protocol state.

It contains no network execution implementation.
"""

from __future__ import annotations

from hashlib import sha256
from ipaddress import IPv4Address
import json
import re
from typing import Mapping


PROTOCOL_SCHEMA = (
    "TRUST_ROBOT_SE4_PHYSICAL_CONFIGURATION_DISCOVERY_PROTOCOL_V1"
)

DISCOVERY_SCHEMA = (
    "TRUST_ROBOT_SE4_PHYSICAL_CONFIGURATION_DISCOVERY_CANDIDATE_V1"
)

AUTHORIZATION_SCHEMA = (
    "TRUST_ROBOT_SE4_PHYSICAL_CONFIGURATION_DISCOVERY_AUTHORIZATION_V1"
)

PROTOCOL_ID = (
    "trust_robot_se4_physical_configuration_discovery_v1"
)

DISCOVERY_SCOPE = (
    "read_only_physical_configuration_discovery"
)

AUTHORIZATION_ACKNOWLEDGEMENT = (
    "I_AUTHORIZE_READ_ONLY_VLP32C_CONFIGURATION_DISCOVERY"
)

MANUFACTURER_FACTORY_SENSOR_IPV4_CANDIDATE = "192.168.1.201"
MANUFACTURER_FACTORY_HTTP_PORT_CANDIDATE = 80
MANUFACTURER_FACTORY_MEASUREMENT_PORT_CANDIDATE = 2368
MANUFACTURER_FACTORY_POSITION_PORT_CANDIDATE = 8308
MANUFACTURER_FACTORY_DESTINATION_IPV4_CANDIDATE = "255.255.255.255"

TEMPORARY_HOST_IPV4_CANDIDATE = "192.168.1.100"

ALLOWED_READ_ONLY_PATHS = (
    "/cgi/info.json",
    "/cgi/snapshot.hdl",
)

MAX_HTTP_REQUEST_COUNT = 2
MINIMUM_REQUEST_SPACING_SECONDS = 1


class SE4PhysicalConfigurationDiscoveryError(
    RuntimeError
):
    """Raised when the bounded discovery contract is violated."""


def _canonical_json(
    value: object,
) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _content_sha256(
    payload: Mapping[str, object],
    *,
    digest_field: str,
) -> str:
    content = dict(
        payload
    )

    content.pop(
        digest_field,
        None,
    )

    return sha256(
        _canonical_json(
            content
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def discovery_content_sha256(
    payload: Mapping[str, object],
) -> str:
    return _content_sha256(
        payload,
        digest_field="discovery_sha256",
    )


def authorization_content_sha256(
    payload: Mapping[str, object],
) -> str:
    return _content_sha256(
        payload,
        digest_field="authorization_sha256",
    )


def protocol_content_sha256(
    payload: Mapping[str, object],
) -> str:
    return _content_sha256(
        payload,
        digest_field="content_sha256",
    )


def _safe_identifier(
    value: object,
    *,
    name: str,
) -> str:
    if not isinstance(
        value,
        str,
    ):
        raise SE4PhysicalConfigurationDiscoveryError(
            f"{name} must be str"
        )

    if not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}",
        value,
    ):
        raise SE4PhysicalConfigurationDiscoveryError(
            f"{name} must be one safe path component"
        )

    return value


def _interface(
    value: object,
) -> str:
    if not isinstance(
        value,
        str,
    ):
        raise SE4PhysicalConfigurationDiscoveryError(
            "interface must be str"
        )

    if not re.fullmatch(
        r"[A-Za-z0-9_.:-]{1,64}",
        value,
    ):
        raise SE4PhysicalConfigurationDiscoveryError(
            "interface contains unsupported characters"
        )

    return value


def _physical_ipv4(
    value: object,
    *,
    name: str,
) -> str:
    if not isinstance(
        value,
        str,
    ):
        raise SE4PhysicalConfigurationDiscoveryError(
            f"{name} must be str"
        )

    try:
        address = IPv4Address(
            value
        )
    except Exception as exc:
        raise SE4PhysicalConfigurationDiscoveryError(
            f"{name} must be valid IPv4"
        ) from exc

    if (
        address.is_loopback
        or address.is_multicast
        or address.is_unspecified
    ):
        raise SE4PhysicalConfigurationDiscoveryError(
            f"{name} must be concrete non-loopback unicast IPv4"
        )

    return str(
        address
    )


def _positive_exact_int(
    value: object,
    *,
    name: str,
) -> int:
    if type(
        value
    ) is not int:
        raise SE4PhysicalConfigurationDiscoveryError(
            f"{name} must be exact int"
        )

    if value <= 0:
        raise SE4PhysicalConfigurationDiscoveryError(
            f"{name} must be positive"
        )

    return value


def _port(
    value: object,
    *,
    name: str,
) -> int:
    port = _positive_exact_int(
        value,
        name=name,
    )

    if port > 65535:
        raise SE4PhysicalConfigurationDiscoveryError(
            f"{name} must be in 1..65535"
        )

    return port


def _digest(
    value: object,
    *,
    name: str,
) -> str:
    if not isinstance(
        value,
        str,
    ) or not re.fullmatch(
        r"[0-9a-f]{64}",
        value,
    ):
        raise SE4PhysicalConfigurationDiscoveryError(
            f"{name} must be lowercase SHA-256"
        )

    return value


def build_discovery_candidate(
    *,
    discovery_id: str,
    interface: str,
    temporary_host_ipv4: str,
    candidate_sensor_ipv4: str,
    candidate_http_port: int,
    connect_timeout_seconds: int,
    total_timeout_seconds: int,
) -> dict[str, object]:
    """Build one non-authorizing bounded discovery candidate."""

    identifier = _safe_identifier(
        discovery_id,
        name="discovery_id",
    )

    interface_name = _interface(
        interface
    )

    host_ipv4 = _physical_ipv4(
        temporary_host_ipv4,
        name="temporary_host_ipv4",
    )

    sensor_ipv4 = _physical_ipv4(
        candidate_sensor_ipv4,
        name="candidate_sensor_ipv4",
    )

    if host_ipv4 == sensor_ipv4:
        raise SE4PhysicalConfigurationDiscoveryError(
            "temporary host IPv4 must differ from candidate sensor IPv4"
        )

    http_port = _port(
        candidate_http_port,
        name="candidate_http_port",
    )

    connect_timeout = _positive_exact_int(
        connect_timeout_seconds,
        name="connect_timeout_seconds",
    )

    total_timeout = _positive_exact_int(
        total_timeout_seconds,
        name="total_timeout_seconds",
    )

    if total_timeout < connect_timeout:
        raise SE4PhysicalConfigurationDiscoveryError(
            "total timeout must be >= connect timeout"
        )

    payload: dict[str, object] = {
        "schema":
            DISCOVERY_SCHEMA,

        "schema_version":
            1,

        "protocol_id":
            PROTOCOL_ID,

        "discovery_id":
            identifier,

        "scope":
            DISCOVERY_SCOPE,

        "interface":
            interface_name,

        "temporary_host_ipv4":
            host_ipv4,

        "candidate_sensor_ipv4":
            sensor_ipv4,

        "candidate_http_port":
            http_port,

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

        "connect_timeout_seconds":
            connect_timeout,

        "total_timeout_seconds":
            total_timeout,

        "network_controls": {
            "ping_allowed":
                False,

            "port_scan_allowed":
                False,

            "ARP_scan_allowed":
                False,

            "subnet_scan_allowed":
                False,

            "HTTP_POST_allowed":
                False,

            "HTTP_PUT_allowed":
                False,

            "HTTP_PATCH_allowed":
                False,

            "HTTP_DELETE_allowed":
                False,

            "redirect_following_allowed":
                False,

            "only_exact_candidate_sensor_endpoint_allowed":
                True,

            "temporary_host_address_must_be_removed_after_discovery":
                True,
        },

        "interpretation": {
            "manufacturer_defaults_are_current_sensor_configuration":
                False,

            "manufacturer_defaults_are_runtime_binding":
                False,

            "successful_discovery_is_real_TRAIN_runtime_binding":
                False,

            "successful_discovery_is_source_acceptance":
                False,

            "successful_discovery_is_health_supervision":
                False,

            "successful_discovery_is_health_label":
                False,

            "successful_discovery_completes_SE4":
                False,
        },

        "scientific_boundary": {
            "real_TRAIN_execution_authorized":
                False,

            "source_acceptance_authorized":
                False,

            "health_label_generation_authorized":
                False,

            "interval_binding_established":
                False,

            "physical_measurement_time_established":
                False,

            "ATE_RPE_computed":
                False,

            "SE4_complete":
                False,

            "SE4_training_authorized":
                False,

            "SE5_may_proceed":
                False,
        },
    }

    payload[
        "discovery_sha256"
    ] = discovery_content_sha256(
        payload
    )

    return payload


def validate_discovery_candidate(
    payload: Mapping[str, object],
) -> Mapping[str, object]:
    if not isinstance(
        payload,
        Mapping,
    ):
        raise SE4PhysicalConfigurationDiscoveryError(
            "discovery candidate must be mapping"
        )

    required = {
        "schema",
        "schema_version",
        "protocol_id",
        "discovery_id",
        "scope",
        "interface",
        "temporary_host_ipv4",
        "candidate_sensor_ipv4",
        "candidate_http_port",
        "HTTP_method",
        "allowed_paths",
        "maximum_HTTP_request_count",
        "minimum_request_spacing_seconds",
        "connect_timeout_seconds",
        "total_timeout_seconds",
        "network_controls",
        "interpretation",
        "scientific_boundary",
        "discovery_sha256",
    }

    if set(
        payload
    ) != required:
        raise SE4PhysicalConfigurationDiscoveryError(
            "discovery candidate fields differ from contract"
        )

    rebuilt = build_discovery_candidate(
        discovery_id=
            payload[
                "discovery_id"
            ],

        interface=
            payload[
                "interface"
            ],

        temporary_host_ipv4=
            payload[
                "temporary_host_ipv4"
            ],

        candidate_sensor_ipv4=
            payload[
                "candidate_sensor_ipv4"
            ],

        candidate_http_port=
            payload[
                "candidate_http_port"
            ],

        connect_timeout_seconds=
            payload[
                "connect_timeout_seconds"
            ],

        total_timeout_seconds=
            payload[
                "total_timeout_seconds"
            ],
    )

    if dict(
        payload
    ) != rebuilt:
        raise SE4PhysicalConfigurationDiscoveryError(
            "discovery candidate differs from canonical representation"
        )

    return payload


def build_discovery_authorization_candidate(
    *,
    authorization_id: str,
    discovery_sha256: str,
    authorization_record_sha256: str,
    authorized_for_configuration_discovery: bool,
    declared_before_discovery: bool,
) -> dict[str, object]:
    """Build one authorization format without performing discovery."""

    identifier = _safe_identifier(
        authorization_id,
        name="authorization_id",
    )

    discovery_digest = _digest(
        discovery_sha256,
        name="discovery_sha256",
    )

    record_digest = _digest(
        authorization_record_sha256,
        name="authorization_record_sha256",
    )

    if type(
        authorized_for_configuration_discovery
    ) is not bool:
        raise SE4PhysicalConfigurationDiscoveryError(
            "authorized_for_configuration_discovery must be bool"
        )

    if type(
        declared_before_discovery
    ) is not bool:
        raise SE4PhysicalConfigurationDiscoveryError(
            "declared_before_discovery must be bool"
        )

    payload: dict[str, object] = {
        "schema":
            AUTHORIZATION_SCHEMA,

        "schema_version":
            1,

        "authorization_id":
            identifier,

        "scope":
            DISCOVERY_SCOPE,

        "discovery_sha256":
            discovery_digest,

        "authorization_record_sha256":
            record_digest,

        "authorized_for_configuration_discovery":
            authorized_for_configuration_discovery,

        "declared_before_discovery":
            declared_before_discovery,

        "required_operator_acknowledgement":
            AUTHORIZATION_ACKNOWLEDGEMENT,

        "real_TRAIN_execution_authorized":
            False,

        "source_acceptance_authorized":
            False,

        "health_label_generation_authorized":
            False,

        "authorization_is_runtime_binding":
            False,

        "authorization_is_health_truth":
            False,
    }

    payload[
        "authorization_sha256"
    ] = authorization_content_sha256(
        payload
    )

    return payload


def validate_discovery_authorization_candidate(
    payload: Mapping[str, object],
    *,
    expected_discovery_sha256: str,
) -> Mapping[str, object]:
    if not isinstance(
        payload,
        Mapping,
    ):
        raise SE4PhysicalConfigurationDiscoveryError(
            "discovery authorization must be mapping"
        )

    required = {
        "schema",
        "schema_version",
        "authorization_id",
        "scope",
        "discovery_sha256",
        "authorization_record_sha256",
        "authorized_for_configuration_discovery",
        "declared_before_discovery",
        "required_operator_acknowledgement",
        "real_TRAIN_execution_authorized",
        "source_acceptance_authorized",
        "health_label_generation_authorized",
        "authorization_is_runtime_binding",
        "authorization_is_health_truth",
        "authorization_sha256",
    }

    if set(
        payload
    ) != required:
        raise SE4PhysicalConfigurationDiscoveryError(
            "discovery authorization fields differ from contract"
        )

    rebuilt = build_discovery_authorization_candidate(
        authorization_id=
            payload[
                "authorization_id"
            ],

        discovery_sha256=
            payload[
                "discovery_sha256"
            ],

        authorization_record_sha256=
            payload[
                "authorization_record_sha256"
            ],

        authorized_for_configuration_discovery=
            payload[
                "authorized_for_configuration_discovery"
            ],

        declared_before_discovery=
            payload[
                "declared_before_discovery"
            ],
    )

    if dict(
        payload
    ) != rebuilt:
        raise SE4PhysicalConfigurationDiscoveryError(
            "discovery authorization differs from canonical representation"
        )

    expected = _digest(
        expected_discovery_sha256,
        name="expected_discovery_sha256",
    )

    if payload[
        "discovery_sha256"
    ] != expected:
        raise SE4PhysicalConfigurationDiscoveryError(
            "discovery authorization is not bound to this candidate"
        )

    if payload[
        "authorized_for_configuration_discovery"
    ] is not True:
        raise SE4PhysicalConfigurationDiscoveryError(
            "configuration discovery authorization is not granted"
        )

    if payload[
        "declared_before_discovery"
    ] is not True:
        raise SE4PhysicalConfigurationDiscoveryError(
            "configuration discovery must be authorized before contact"
        )

    if payload[
        "real_TRAIN_execution_authorized"
    ] is not False:
        raise SE4PhysicalConfigurationDiscoveryError(
            "configuration discovery may not authorize real TRAIN execution"
        )

    if payload[
        "source_acceptance_authorized"
    ] is not False:
        raise SE4PhysicalConfigurationDiscoveryError(
            "configuration discovery may not authorize source acceptance"
        )

    if payload[
        "health_label_generation_authorized"
    ] is not False:
        raise SE4PhysicalConfigurationDiscoveryError(
            "configuration discovery may not authorize health labels"
        )

    return payload


def build_physical_configuration_discovery_protocol(
) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema":
            PROTOCOL_SCHEMA,

        "schema_version":
            1,

        "protocol_id":
            PROTOCOL_ID,

        "purpose":
            (
                "Resolve the bootstrap gap between a zero-contact repository "
                "state and the externally grounded physical values required "
                "for one real TRAIN V2 runtime binding."
            ),

        "manufacturer_documented_discovery_candidates": {
            "candidate_sensor_ipv4":
                MANUFACTURER_FACTORY_SENSOR_IPV4_CANDIDATE,

            "candidate_http_port":
                MANUFACTURER_FACTORY_HTTP_PORT_CANDIDATE,

            "candidate_measurement_udp_port":
                MANUFACTURER_FACTORY_MEASUREMENT_PORT_CANDIDATE,

            "candidate_position_udp_port":
                MANUFACTURER_FACTORY_POSITION_PORT_CANDIDATE,

            "candidate_destination_ipv4":
                MANUFACTURER_FACTORY_DESTINATION_IPV4_CANDIDATE,

            "candidate_temporary_host_ipv4":
                TEMPORARY_HOST_IPV4_CANDIDATE,

            "factory_values_are_current_unit_configuration":
                False,

            "factory_values_are_runtime_binding":
                False,
        },

        "discovery_contract": {
            "candidate_schema":
                DISCOVERY_SCHEMA,

            "authorization_schema":
                AUTHORIZATION_SCHEMA,

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

            "separate_hash_bound_authorization_required":
                True,

            "external_authorization_record_digest_required":
                True,

            "exact_operator_acknowledgement_required":
                AUTHORIZATION_ACKNOWLEDGEMENT,

            "ping_allowed":
                False,

            "port_scan_allowed":
                False,

            "ARP_scan_allowed":
                False,

            "subnet_scan_allowed":
                False,

            "HTTP_write_methods_allowed":
                False,

            "sensor_configuration_changes_allowed":
                False,
        },

        "current_state": {
            "real_configuration_discovery_candidate_count":
                0,

            "real_configuration_discovery_authorization_count":
                0,

            "grounded_configuration_discovery_record_count":
                0,

            "real_configuration_discovery_execution_count":
                0,

            "real_sensor_network_IO_executed":
                False,

            "real_sensor_contact":
                False,

            "real_runtime_binding_count":
                0,
        },

        "scientific_boundary": {
            "configuration_discovery_is_real_TRAIN_execution":
                False,

            "configuration_discovery_is_runtime_binding":
                False,

            "configuration_discovery_is_source_acceptance":
                False,

            "configuration_discovery_is_health_supervision":
                False,

            "configuration_discovery_is_health_label":
                False,

            "configuration_discovery_establishes_interval_binding":
                False,

            "configuration_discovery_establishes_physical_measurement_time":
                False,

            "ATE_RPE_computed":
                False,

            "SE4_complete":
                False,

            "SE4_training_authorized":
                False,

            "SE5_may_proceed":
                False,
        },

        "transition_policy": {
            "software_protocol_resolved":
                True,

            "network_execution_implemented_by_this_module":
                False,

            "configuration_discovery_authorized":
                False,

            "next_required_event":
                (
                    "Construct one explicit bounded discovery candidate, one "
                    "external operator authorization record, and one separate "
                    "hash-bound discovery authorization. Only then may the "
                    "documented candidate endpoint receive at most two GET "
                    "requests for identity and configuration snapshot."
                ),

            "after_successful_discovery":
                (
                    "Treat observed sensor settings as configuration evidence "
                    "only, then separately construct and validate the 16-field "
                    "real TRAIN V2 runtime binding."
                ),
        },
    }

    payload[
        "content_sha256"
    ] = protocol_content_sha256(
        payload
    )

    return payload


def validate_physical_configuration_discovery_protocol(
    payload: Mapping[str, object],
) -> Mapping[str, object]:
    expected = (
        build_physical_configuration_discovery_protocol()
    )

    if not isinstance(
        payload,
        Mapping,
    ):
        raise SE4PhysicalConfigurationDiscoveryError(
            "protocol must be mapping"
        )

    if dict(
        payload
    ) != expected:
        raise SE4PhysicalConfigurationDiscoveryError(
            "physical configuration discovery protocol differs from canonical state"
        )

    return payload
