"""SE4 real TRAIN runtime-input binding protocol.

This module defines how externally supplied real acquisition runtime values
must be bound into one deterministic, hash-addressed candidate record.

The protocol deliberately supplies no sensor address, host address, UDP port,
duration, filesystem path, session identity, timeout, or device destination
configuration itself.

A valid runtime binding is still not execution authorization, health
supervision, a health label, interval binding, or SE4 completion.
"""

from __future__ import annotations

from hashlib import sha256
from ipaddress import IPv4Address, ip_address
from pathlib import PurePath
from typing import Mapping
import json
import re


SCHEMA = (
    "TRUST_ROBOT_SE4_REAL_TRAIN_RUNTIME_INPUT_BINDING_PROTOCOL_V1"
)

BINDING_SCHEMA = (
    "TRUST_ROBOT_SE4_REAL_TRAIN_RUNTIME_INPUT_BINDING_CANDIDATE_V1"
)

SCHEMA_VERSION = 1

PROTOCOL_ID = (
    "trust_robot_se4_real_train_runtime_input_binding_v1"
)

_SESSION_RE = re.compile(
    r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}"
)

FROZEN_INPUT_SHA256 = {
    "SE4_live_execution_transport_freeze":
        "c086398420cf9187aba0defaa3fce54a34eb5f57dbef457aa30e3fae290cd0b0",

    "SE4_live_execution_transport_config":
        "ee737340b0b6d2d262b39ce05bd3a23dc9bf2b082e3ad974a5c7e413a044ee64",

    "phase5_unprivileged_udp_receiver_config":
        "96cd1be3cf9ec3a55721cb496cac32a61279682bdf2d11d16b479568435c3b90",

    "unprivileged_udp_receiver_module":
        "05e40722e15434b92d0f8aad93e4a6a9aef71a38dcd8d97e8bddc4f5ec3a385d",

    "phase5_live_executor_safety":
        "9370692895bc156552a664b23fd84445a32a3b20ead8c1d1c4f495c31e6dca6a",

    "live_executor_safety_module":
        "6dcb292355ba17ec8a563b1183e0279b40559ec0467dd8dc9fbba5a2e674e26a",

    "phase5_live_acquisition_plan":
        "9988bf72a341a045831b2efe49d393f6886075ca179034ceecf4a191b4f8992d",

    "live_acquisition_plan_module":
        "196a88bde3f96c98985121c13444190984c1622dceb648817ead8ef3320956a6",

    "phase5_acquisition_session_provenance":
        "08b691bcc0eb3db7d9b0059608f8134b7b6086f526b6c11e64cf03ac3efa763b",
}


class SE4RuntimeInputBindingError(
    ValueError
):
    """Raised when a runtime binding violates the frozen protocol."""


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
    body = dict(
        payload
    )

    body.pop(
        digest_field,
        None,
    )

    return sha256(
        _canonical_json(
            body
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def protocol_content_sha256(
    payload: Mapping[str, object],
) -> str:
    return _content_sha256(
        payload,
        digest_field="content_sha256",
    )


def binding_content_sha256(
    payload: Mapping[str, object],
) -> str:
    return _content_sha256(
        payload,
        digest_field="binding_sha256",
    )


def _exact_positive_int(
    value: object,
    *,
    name: str,
    upper: int | None = None,
) -> int:
    if type(
        value
    ) is not int:
        raise SE4RuntimeInputBindingError(
            f"{name} must be an exact int"
        )

    if value < 1:
        raise SE4RuntimeInputBindingError(
            f"{name} must be positive"
        )

    if (
        upper is not None
        and value > upper
    ):
        raise SE4RuntimeInputBindingError(
            f"{name} exceeds allowed maximum"
        )

    return value


def _ipv4(
    value: object,
    *,
    name: str,
    allow_unspecified: bool,
) -> str:
    if not isinstance(
        value,
        str,
    ) or not value:
        raise SE4RuntimeInputBindingError(
            f"{name} must be a non-empty IPv4 string"
        )

    try:
        parsed = ip_address(
            value
        )
    except ValueError as exc:
        raise SE4RuntimeInputBindingError(
            f"{name} must be a valid IPv4 address"
        ) from exc

    if not isinstance(
        parsed,
        IPv4Address,
    ):
        raise SE4RuntimeInputBindingError(
            f"{name} must be IPv4"
        )

    if (
        parsed.is_unspecified
        and not allow_unspecified
    ):
        raise SE4RuntimeInputBindingError(
            f"{name} may not be unspecified"
        )

    if (
        parsed.is_multicast
        or parsed.is_loopback
    ) and not (
        allow_unspecified
        and parsed.is_unspecified
    ):
        raise SE4RuntimeInputBindingError(
            f"{name} must represent a non-loopback, non-multicast IPv4 endpoint"
        )

    return str(
        parsed
    )


def _absolute_path(
    value: object,
    *,
    name: str,
) -> str:
    if not isinstance(
        value,
        str,
    ) or not value:
        raise SE4RuntimeInputBindingError(
            f"{name} must be a non-empty string"
        )

    path = PurePath(
        value
    )

    if not path.is_absolute():
        raise SE4RuntimeInputBindingError(
            f"{name} must be absolute"
        )

    if ".." in path.parts:
        raise SE4RuntimeInputBindingError(
            f"{name} may not contain parent traversal"
        )

    return str(
        path
    )


def _session_id(
    value: object,
) -> str:
    if not isinstance(
        value,
        str,
    ) or _SESSION_RE.fullmatch(
        value
    ) is None:
        raise SE4RuntimeInputBindingError(
            "acquisition_session_id must be one safe path component"
        )

    return value


def build_runtime_binding_candidate(
    *,
    acquisition_session_id: str,
    split: str,
    bind_ipv4: str,
    measurement_udp_port: int,
    position_udp_port: int,
    sensor_ipv4: str,
    capture_duration_seconds: int,
    absolute_output_root: str,
    http_connect_timeout_seconds: int,
    http_total_timeout_seconds: int,
    vlp32c_destination_ipv4: str,
    vlp32c_measurement_destination_udp_port: int,
    vlp32c_position_destination_udp_port: int,
    vlp32c_destination_configuration_verified: bool,
    declared_before_execution: bool,
) -> dict[str, object]:
    """Build one explicit runtime binding without authorizing execution."""

    if split != "TRAIN":
        raise SE4RuntimeInputBindingError(
            "split must be exactly TRAIN"
        )

    session_id = _session_id(
        acquisition_session_id
    )

    bind_ip = _ipv4(
        bind_ipv4,
        name="bind_ipv4",
        allow_unspecified=True,
    )

    sensor_ip = _ipv4(
        sensor_ipv4,
        name="sensor_ipv4",
        allow_unspecified=False,
    )

    destination_ip = _ipv4(
        vlp32c_destination_ipv4,
        name="vlp32c_destination_ipv4",
        allow_unspecified=False,
    )

    measurement_port = _exact_positive_int(
        measurement_udp_port,
        name="measurement_udp_port",
        upper=65535,
    )

    position_port = _exact_positive_int(
        position_udp_port,
        name="position_udp_port",
        upper=65535,
    )

    if measurement_port == position_port:
        raise SE4RuntimeInputBindingError(
            "measurement and position UDP ports must be distinct"
        )

    measurement_destination_port = _exact_positive_int(
        vlp32c_measurement_destination_udp_port,
        name="vlp32c_measurement_destination_udp_port",
        upper=65535,
    )

    position_destination_port = _exact_positive_int(
        vlp32c_position_destination_udp_port,
        name="vlp32c_position_destination_udp_port",
        upper=65535,
    )

    if (
        measurement_destination_port
        != measurement_port
    ):
        raise SE4RuntimeInputBindingError(
            "VLP-32C measurement destination port must match receiver port"
        )

    if (
        position_destination_port
        != position_port
    ):
        raise SE4RuntimeInputBindingError(
            "VLP-32C position destination port must match receiver port"
        )

    if (
        bind_ip != "0.0.0.0"
        and destination_ip != bind_ip
    ):
        raise SE4RuntimeInputBindingError(
            "when bind_ipv4 is specific, the VLP-32C destination IPv4 "
            "must match that bound host address"
        )

    duration = _exact_positive_int(
        capture_duration_seconds,
        name="capture_duration_seconds",
    )

    connect_timeout = _exact_positive_int(
        http_connect_timeout_seconds,
        name="http_connect_timeout_seconds",
    )

    total_timeout = _exact_positive_int(
        http_total_timeout_seconds,
        name="http_total_timeout_seconds",
    )

    if total_timeout < connect_timeout:
        raise SE4RuntimeInputBindingError(
            "http_total_timeout_seconds must be >= "
            "http_connect_timeout_seconds"
        )

    output_root = _absolute_path(
        absolute_output_root,
        name="absolute_output_root",
    )

    if type(
        vlp32c_destination_configuration_verified
    ) is not bool or not vlp32c_destination_configuration_verified:
        raise SE4RuntimeInputBindingError(
            "VLP-32C destination configuration must be explicitly verified"
        )

    if type(
        declared_before_execution
    ) is not bool or not declared_before_execution:
        raise SE4RuntimeInputBindingError(
            "runtime binding must be declared before execution"
        )

    payload: dict[str, object] = {
        "schema":
            BINDING_SCHEMA,

        "schema_version":
            SCHEMA_VERSION,

        "protocol_id":
            PROTOCOL_ID,

        "split":
            "TRAIN",

        "acquisition_session_id":
            session_id,

        "UDP_receiver_binding": {
            "bind_ipv4":
                bind_ip,

            "measurement_udp_port":
                measurement_port,

            "position_udp_port":
                position_port,

            "capture_duration_seconds":
                duration,
        },

        "sensor_binding": {
            "sensor_ipv4":
                sensor_ip,

            "vlp32c_destination_ipv4":
                destination_ip,

            "vlp32c_measurement_destination_udp_port":
                measurement_destination_port,

            "vlp32c_position_destination_udp_port":
                position_destination_port,

            "vlp32c_destination_configuration_verified":
                True,
        },

        "filesystem_binding": {
            "absolute_output_root":
                output_root,

            "fresh_session_directory_required":
                True,

            "existing_final_artifact_overwrite_allowed":
                False,
        },

        "HTTP_binding": {
            "http_connect_timeout_seconds":
                connect_timeout,

            "http_total_timeout_seconds":
                total_timeout,

            "timeout_values_are_engineering_controls_not_sensor_timing_tolerances":
                True,
        },

        "declaration": {
            "declared_before_execution":
                True,

            "runtime_values_operator_supplied":
                True,

            "protocol_supplied_physical_defaults":
                False,
        },

        "scientific_boundary": {
            "execution_authorized":
                False,

            "network_IO_executed":
                False,

            "sensor_contact_executed":
                False,

            "source_acceptance_authorized":
                False,

            "health_label_generation_authorized":
                False,

            "interval_binding_established":
                False,

            "physical_measurement_time_established":
                False,

            "accepted_health_supervision_source_count":
                0,

            "real_health_label_count":
                0,
        },

        "parent_transport_freeze_sha256":
            FROZEN_INPUT_SHA256[
                "SE4_live_execution_transport_freeze"
            ],
    }

    payload[
        "binding_sha256"
    ] = binding_content_sha256(
        payload
    )

    return payload


def validate_runtime_binding_candidate(
    payload: Mapping[str, object],
) -> Mapping[str, object]:
    """Validate one externally supplied runtime binding candidate."""

    if not isinstance(
        payload,
        Mapping,
    ):
        raise SE4RuntimeInputBindingError(
            "runtime binding must be a mapping"
        )

    required_top = {
        "schema",
        "schema_version",
        "protocol_id",
        "split",
        "acquisition_session_id",
        "UDP_receiver_binding",
        "sensor_binding",
        "filesystem_binding",
        "HTTP_binding",
        "declaration",
        "scientific_boundary",
        "parent_transport_freeze_sha256",
        "binding_sha256",
    }

    if set(
        payload
    ) != required_top:
        raise SE4RuntimeInputBindingError(
            "runtime binding top-level fields differ from protocol"
        )

    if payload[
        "schema"
    ] != BINDING_SCHEMA:
        raise SE4RuntimeInputBindingError(
            "runtime binding schema mismatch"
        )

    if payload[
        "schema_version"
    ] != SCHEMA_VERSION:
        raise SE4RuntimeInputBindingError(
            "runtime binding schema version mismatch"
        )

    if payload[
        "protocol_id"
    ] != PROTOCOL_ID:
        raise SE4RuntimeInputBindingError(
            "runtime binding protocol mismatch"
        )

    if payload[
        "parent_transport_freeze_sha256"
    ] != FROZEN_INPUT_SHA256[
        "SE4_live_execution_transport_freeze"
    ]:
        raise SE4RuntimeInputBindingError(
            "runtime binding parent transport freeze mismatch"
        )

    rebuilt = build_runtime_binding_candidate(
        acquisition_session_id=payload[
            "acquisition_session_id"
        ],
        split=payload[
            "split"
        ],
        bind_ipv4=payload[
            "UDP_receiver_binding"
        ][
            "bind_ipv4"
        ],
        measurement_udp_port=payload[
            "UDP_receiver_binding"
        ][
            "measurement_udp_port"
        ],
        position_udp_port=payload[
            "UDP_receiver_binding"
        ][
            "position_udp_port"
        ],
        sensor_ipv4=payload[
            "sensor_binding"
        ][
            "sensor_ipv4"
        ],
        capture_duration_seconds=payload[
            "UDP_receiver_binding"
        ][
            "capture_duration_seconds"
        ],
        absolute_output_root=payload[
            "filesystem_binding"
        ][
            "absolute_output_root"
        ],
        http_connect_timeout_seconds=payload[
            "HTTP_binding"
        ][
            "http_connect_timeout_seconds"
        ],
        http_total_timeout_seconds=payload[
            "HTTP_binding"
        ][
            "http_total_timeout_seconds"
        ],
        vlp32c_destination_ipv4=payload[
            "sensor_binding"
        ][
            "vlp32c_destination_ipv4"
        ],
        vlp32c_measurement_destination_udp_port=payload[
            "sensor_binding"
        ][
            "vlp32c_measurement_destination_udp_port"
        ],
        vlp32c_position_destination_udp_port=payload[
            "sensor_binding"
        ][
            "vlp32c_position_destination_udp_port"
        ],
        vlp32c_destination_configuration_verified=payload[
            "sensor_binding"
        ][
            "vlp32c_destination_configuration_verified"
        ],
        declared_before_execution=payload[
            "declaration"
        ][
            "declared_before_execution"
        ],
    )

    if dict(
        payload
    ) != rebuilt:
        raise SE4RuntimeInputBindingError(
            "runtime binding differs from canonical protocol representation"
        )

    if payload[
        "binding_sha256"
    ] != binding_content_sha256(
        payload
    ):
        raise SE4RuntimeInputBindingError(
            "runtime binding digest mismatch"
        )

    return payload


def build_runtime_input_binding_protocol(
) -> dict[str, object]:
    """Build the current empty/no-default binding protocol state."""

    required_fields = [
        "acquisition_session_id",
        "split",
        "bind_ipv4",
        "measurement_udp_port",
        "position_udp_port",
        "sensor_ipv4",
        "capture_duration_seconds",
        "absolute_output_root",
        "http_connect_timeout_seconds",
        "http_total_timeout_seconds",
        "vlp32c_destination_ipv4",
        "vlp32c_measurement_destination_udp_port",
        "vlp32c_position_destination_udp_port",
        "vlp32c_destination_configuration_verified",
        "declared_before_execution",
    ]

    payload: dict[str, object] = {
        "schema":
            SCHEMA,

        "schema_version":
            SCHEMA_VERSION,

        "protocol_id":
            PROTOCOL_ID,

        "stage_context": {
            "stage_id":
                "SE4",

            "sub_frontier":
                "real_TRAIN_runtime_input_binding",

            "SE4_complete":
                False,

            "SE4_training_authorized":
                False,
        },

        "binding_contract": {
            "binding_schema":
                BINDING_SCHEMA,

            "required_fields":
                required_fields,

            "all_required_fields_have_no_protocol_default":
                True,

            "split_must_be_exactly":
                "TRAIN",

            "runtime_values_must_be_externally_supplied":
                True,

            "binding_must_exist_before_network_execution":
                True,

            "binding_is_hash_addressed":
                True,

            "binding_is_execution_authorization":
                False,
        },

        "validation_rules": {
            "bind_ipv4":
                "valid IPv4; 0.0.0.0 permitted",

            "sensor_ipv4":
                "valid non-loopback non-multicast non-unspecified IPv4",

            "UDP_ports":
                "exact integers 1..65535 and distinct",

            "capture_duration_seconds":
                "positive exact integer",

            "absolute_output_root":
                "absolute path with no parent traversal",

            "acquisition_session_id":
                "safe single path component",

            "HTTP_timeouts":
                "positive exact integers; total >= connect",

            "VLP32C_destination_ports":
                "must equal selected receiver measurement/position ports",

            "VLP32C_destination_IP":
                (
                    "must equal specific bind IPv4; if bind is 0.0.0.0, "
                    "a concrete non-loopback destination IPv4 is required"
                ),

            "VLP32C_destination_configuration_verified":
                "explicit true required",

            "declared_before_execution":
                "explicit true required",
        },

        "current_binding_state": {
            "real_runtime_binding_count":
                0,

            "real_runtime_values_bound":
                False,

            "acquisition_session_id":
                None,

            "bind_ipv4":
                None,

            "measurement_udp_port":
                None,

            "position_udp_port":
                None,

            "sensor_ipv4":
                None,

            "capture_duration_seconds":
                None,

            "absolute_output_root":
                None,

            "http_connect_timeout_seconds":
                None,

            "http_total_timeout_seconds":
                None,

            "vlp32c_destination_ipv4":
                None,

            "vlp32c_measurement_destination_udp_port":
                None,

            "vlp32c_position_destination_udp_port":
                None,

            "vlp32c_destination_configuration_verified":
                False,
        },

        "scientific_boundary": {
            "protocol_selects_physical_runtime_values":
                False,

            "network_IO_executed":
                False,

            "sensor_contact_executed":
                False,

            "raw_real_sensor_capture_artifact_count":
                0,

            "accepted_baseline_nominality_source_count":
                0,

            "accepted_health_supervision_source_count":
                0,

            "real_health_label_count":
                0,

            "interval_binding_established":
                False,

            "physical_measurement_time_established":
                False,

            "reference_data_used":
                False,

            "ATE_RPE_computed":
                False,

            "validation_access":
                False,

            "confirmation_access":
                False,
        },

        "transition_policy": {
            "runtime_input_binding_protocol_resolved":
                True,

            "real_runtime_values_bound":
                False,

            "real_sensor_execution_authorized":
                False,

            "HTTP_execution_implemented":
                False,

            "source_acceptance_authorized":
                False,

            "health_label_generation_authorized":
                False,

            "SE4_complete":
                False,

            "SE4_training_authorized":
                False,

            "SE5_may_proceed":
                False,

            "validation_remains_closed":
                True,

            "confirmation_remains_closed":
                True,

            "next_required_event":
                (
                    "Create one real operator-supplied TRAIN runtime binding "
                    "under this protocol. The binding itself still does not "
                    "authorize execution; a separate execution-authorization "
                    "step remains required."
                ),
        },

        "frozen_input_sha256":
            dict(
                FROZEN_INPUT_SHA256
            ),
    }

    payload[
        "content_sha256"
    ] = protocol_content_sha256(
        payload
    )

    return payload


def validate_runtime_input_binding_protocol(
    payload: Mapping[str, object],
) -> Mapping[str, object]:
    if not isinstance(
        payload,
        Mapping,
    ):
        raise SE4RuntimeInputBindingError(
            "protocol payload must be a mapping"
        )

    expected = (
        build_runtime_input_binding_protocol()
    )

    if dict(
        payload
    ) != expected:
        raise SE4RuntimeInputBindingError(
            "runtime-input binding protocol differs from frozen state"
        )

    return payload


def assert_real_sensor_execution_authorized(
    payload: Mapping[str, object],
) -> None:
    validate_runtime_input_binding_protocol(
        payload
    )

    if payload[
        "transition_policy"
    ][
        "real_sensor_execution_authorized"
    ] is not True:
        raise SE4RuntimeInputBindingError(
            "real-sensor execution remains blocked: no real TRAIN runtime "
            "binding and no separate execution authorization exist"
        )


def assert_health_supervision_available(
    payload: Mapping[str, object],
) -> None:
    validate_runtime_input_binding_protocol(
        payload
    )

    boundary = payload[
        "scientific_boundary"
    ]

    if (
        boundary[
            "accepted_health_supervision_source_count"
        ] <= 0
        or boundary[
            "real_health_label_count"
        ] <= 0
    ):
        raise SE4RuntimeInputBindingError(
            "health supervision remains unavailable: runtime binding is not "
            "source acceptance or a health label"
        )
