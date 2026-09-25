"""SE4 real TRAIN runtime-input binding protocol V2.

V2 is a post-freeze extension of the promoted V1 protocol.

The only physical runtime-field delta is the explicit HTTP port required by
the promoted SE4 HTTP evidence executor. V1 remains historical and unchanged.

V2 still supplies no physical runtime defaults, creates no real binding,
authorizes no execution, accepts no supervision source, creates no health
label, and does not complete SE4.
"""

from __future__ import annotations

from hashlib import sha256
from typing import Mapping
import json

from .se4_real_train_runtime_input_binding import (
    SE4RuntimeInputBindingError,
    build_runtime_binding_candidate as build_v1_runtime_binding_candidate,
    build_runtime_input_binding_protocol as build_v1_protocol,
)


SCHEMA = (
    "TRUST_ROBOT_SE4_REAL_TRAIN_RUNTIME_INPUT_BINDING_PROTOCOL_V2"
)

BINDING_SCHEMA = (
    "TRUST_ROBOT_SE4_REAL_TRAIN_RUNTIME_INPUT_BINDING_CANDIDATE_V2"
)

SCHEMA_VERSION = 2

PROTOCOL_ID = (
    "trust_robot_se4_real_train_runtime_input_binding_v2"
)

FROZEN_INPUT_SHA256 = {
    "runtime_binding_v1_module":
        "1c9626481d4f01be63c4c7e9d833cc32dcc4b17c07c90611be2a6a671c47597f",

    "runtime_binding_v1_config":
        "ff293fa62bab7d1ce72f8a2f130130c5b66826c74a8d1853a7f1ac63e9fc14e7",

    "runtime_binding_v1_freeze":
        "28bf88aa87f6c527f16fa3144e94d70fadc64379f0e90529f04c46e7364d6afc",

    "HTTP_executor_module":
        "98d82acca2308aea76537de4a9cc4fa0eb94e8fd9bc4aa9bde048382f5b69dd9",

    "HTTP_executor_config":
        "51f98b3424d1db7bd2706f49e399954b007dfd8c2897d495462c7c7edd921aac",

    "HTTP_executor_freeze":
        "29639601503a8d7c0b9db879939a8960b2f0a69ca10e378fc07f0b031aeadc10",
}


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


def _http_port(
    value: object,
) -> int:
    if type(
        value
    ) is not int:
        raise SE4RuntimeInputBindingError(
            "http_port must be an exact int"
        )

    if value < 1 or value > 65535:
        raise SE4RuntimeInputBindingError(
            "http_port must be in 1..65535"
        )

    return value


def build_runtime_binding_candidate_v2(
    *,
    acquisition_session_id: str,
    split: str,
    bind_ipv4: str,
    measurement_udp_port: int,
    position_udp_port: int,
    sensor_ipv4: str,
    capture_duration_seconds: int,
    absolute_output_root: str,
    http_port: int,
    http_connect_timeout_seconds: int,
    http_total_timeout_seconds: int,
    vlp32c_destination_ipv4: str,
    vlp32c_measurement_destination_udp_port: int,
    vlp32c_position_destination_udp_port: int,
    vlp32c_destination_configuration_verified: bool,
    declared_before_execution: bool,
) -> dict[str, object]:
    """Build one V2 candidate without authorizing execution."""

    port = _http_port(
        http_port
    )

    v1 = build_v1_runtime_binding_candidate(
        acquisition_session_id=
            acquisition_session_id,

        split=
            split,

        bind_ipv4=
            bind_ipv4,

        measurement_udp_port=
            measurement_udp_port,

        position_udp_port=
            position_udp_port,

        sensor_ipv4=
            sensor_ipv4,

        capture_duration_seconds=
            capture_duration_seconds,

        absolute_output_root=
            absolute_output_root,

        http_connect_timeout_seconds=
            http_connect_timeout_seconds,

        http_total_timeout_seconds=
            http_total_timeout_seconds,

        vlp32c_destination_ipv4=
            vlp32c_destination_ipv4,

        vlp32c_measurement_destination_udp_port=
            vlp32c_measurement_destination_udp_port,

        vlp32c_position_destination_udp_port=
            vlp32c_position_destination_udp_port,

        vlp32c_destination_configuration_verified=
            vlp32c_destination_configuration_verified,

        declared_before_execution=
            declared_before_execution,
    )

    payload = dict(
        v1
    )

    payload[
        "schema"
    ] = BINDING_SCHEMA

    payload[
        "schema_version"
    ] = SCHEMA_VERSION

    payload[
        "protocol_id"
    ] = PROTOCOL_ID

    payload[
        "HTTP_binding"
    ] = dict(
        v1[
            "HTTP_binding"
        ]
    )

    payload[
        "HTTP_binding"
    ][
        "http_port"
    ] = port

    payload[
        "compatibility"
    ] = {
        "runtime_binding_v1_binding_sha256":
            v1[
                "binding_sha256"
            ],

        "runtime_binding_v1_freeze_sha256":
            FROZEN_INPUT_SHA256[
                "runtime_binding_v1_freeze"
            ],

        "HTTP_executor_freeze_sha256":
            FROZEN_INPUT_SHA256[
                "HTTP_executor_freeze"
            ],

        "contract_delta":
            "explicit_http_port_required_no_default",

        "V1_rewritten":
            False,
    }

    payload.pop(
        "binding_sha256",
        None,
    )

    payload[
        "binding_sha256"
    ] = binding_content_sha256(
        payload
    )

    return payload


def validate_runtime_binding_candidate_v2(
    payload: Mapping[str, object],
) -> Mapping[str, object]:
    """Validate one V2 candidate against the canonical representation."""

    if not isinstance(
        payload,
        Mapping,
    ):
        raise SE4RuntimeInputBindingError(
            "V2 runtime binding must be a mapping"
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
        "compatibility",
        "binding_sha256",
    }

    if set(
        payload
    ) != required_top:
        raise SE4RuntimeInputBindingError(
            "V2 runtime binding top-level fields differ from protocol"
        )

    if payload[
        "schema"
    ] != BINDING_SCHEMA:
        raise SE4RuntimeInputBindingError(
            "V2 binding schema mismatch"
        )

    if payload[
        "schema_version"
    ] != SCHEMA_VERSION:
        raise SE4RuntimeInputBindingError(
            "V2 binding schema version mismatch"
        )

    if payload[
        "protocol_id"
    ] != PROTOCOL_ID:
        raise SE4RuntimeInputBindingError(
            "V2 binding protocol mismatch"
        )

    http_binding = payload[
        "HTTP_binding"
    ]

    if not isinstance(
        http_binding,
        Mapping,
    ):
        raise SE4RuntimeInputBindingError(
            "HTTP_binding must be a mapping"
        )

    if set(
        http_binding
    ) != {
        "http_port",
        "http_connect_timeout_seconds",
        "http_total_timeout_seconds",
        "timeout_values_are_engineering_controls_not_sensor_timing_tolerances",
    }:
        raise SE4RuntimeInputBindingError(
            "V2 HTTP_binding fields differ from protocol"
        )

    compatibility = payload[
        "compatibility"
    ]

    if not isinstance(
        compatibility,
        Mapping,
    ):
        raise SE4RuntimeInputBindingError(
            "compatibility must be a mapping"
        )

    rebuilt = build_runtime_binding_candidate_v2(
        acquisition_session_id=
            payload[
                "acquisition_session_id"
            ],

        split=
            payload[
                "split"
            ],

        bind_ipv4=
            payload[
                "UDP_receiver_binding"
            ][
                "bind_ipv4"
            ],

        measurement_udp_port=
            payload[
                "UDP_receiver_binding"
            ][
                "measurement_udp_port"
            ],

        position_udp_port=
            payload[
                "UDP_receiver_binding"
            ][
                "position_udp_port"
            ],

        sensor_ipv4=
            payload[
                "sensor_binding"
            ][
                "sensor_ipv4"
            ],

        capture_duration_seconds=
            payload[
                "UDP_receiver_binding"
            ][
                "capture_duration_seconds"
            ],

        absolute_output_root=
            payload[
                "filesystem_binding"
            ][
                "absolute_output_root"
            ],

        http_port=
            http_binding[
                "http_port"
            ],

        http_connect_timeout_seconds=
            http_binding[
                "http_connect_timeout_seconds"
            ],

        http_total_timeout_seconds=
            http_binding[
                "http_total_timeout_seconds"
            ],

        vlp32c_destination_ipv4=
            payload[
                "sensor_binding"
            ][
                "vlp32c_destination_ipv4"
            ],

        vlp32c_measurement_destination_udp_port=
            payload[
                "sensor_binding"
            ][
                "vlp32c_measurement_destination_udp_port"
            ],

        vlp32c_position_destination_udp_port=
            payload[
                "sensor_binding"
            ][
                "vlp32c_position_destination_udp_port"
            ],

        vlp32c_destination_configuration_verified=
            payload[
                "sensor_binding"
            ][
                "vlp32c_destination_configuration_verified"
            ],

        declared_before_execution=
            payload[
                "declaration"
            ][
                "declared_before_execution"
            ],
    )

    if dict(
        payload
    ) != rebuilt:
        raise SE4RuntimeInputBindingError(
            "V2 runtime binding differs from canonical representation"
        )

    if payload[
        "binding_sha256"
    ] != binding_content_sha256(
        payload
    ):
        raise SE4RuntimeInputBindingError(
            "V2 runtime binding digest mismatch"
        )

    return payload


def build_runtime_input_binding_protocol_v2(
) -> dict[str, object]:
    """Build the zero-real-binding V2 protocol state."""

    v1_protocol = (
        build_v1_protocol()
    )

    v1_required = list(
        v1_protocol[
            "binding_contract"
        ][
            "required_fields"
        ]
    )

    if "http_port" in v1_required:
        raise SE4RuntimeInputBindingError(
            "historical V1 unexpectedly already contains http_port"
        )

    required_fields = (
        v1_required[
            :7
        ]
        + [
            "http_port"
        ]
        + v1_required[
            7:
        ]
    )

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
                "real_TRAIN_runtime_input_binding_V2",

            "status":
                "HTTP_port_cross_contract_gap_resolved_zero_real_bindings",

            "SE4_complete":
                False,

            "SE4_training_authorized":
                False,
        },

        "parent_contract": {
            "runtime_binding_V1_freeze_sha256":
                FROZEN_INPUT_SHA256[
                    "runtime_binding_v1_freeze"
                ],

            "HTTP_executor_freeze_sha256":
                FROZEN_INPUT_SHA256[
                    "HTTP_executor_freeze"
                ],

            "V1_preserved_unchanged":
                True,

            "V2_contract_delta":
                [
                    "http_port",
                ],
        },

        "binding_contract": {
            "binding_schema":
                BINDING_SCHEMA,

            "required_fields":
                required_fields,

            "required_field_count":
                len(
                    required_fields
                ),

            "all_required_fields_have_no_protocol_default":
                True,

            "runtime_values_must_be_externally_supplied":
                True,

            "split_must_be_exactly":
                "TRAIN",

            "binding_must_exist_before_network_execution":
                True,

            "binding_is_hash_addressed":
                True,

            "binding_is_execution_authorization":
                False,

            "explicit_HTTP_port_required":
                True,

            "protocol_supplies_physical_HTTP_port_default":
                False,
        },

        "validation_rules": {
            "http_port":
                "exact integer 1..65535; required; no physical default",

            "HTTP_timeouts":
                "positive exact integers; total >= connect",

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

            "http_port":
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

            "real_binding_sha256":
                None,
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
            "runtime_input_binding_V2_resolved":
                True,

            "HTTP_port_cross_contract_gap_resolved":
                True,

            "HTTP_execution_software_implemented":
                True,

            "real_runtime_binding_count":
                0,

            "real_runtime_values_bound":
                False,

            "real_sensor_execution_authorized":
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

            "next_required_software_event":
                (
                    "Resolve the composite real TRAIN live-session "
                    "orchestrator against this V2 binding contract."
                ),

            "next_required_physical_event":
                (
                    "After software orchestration is frozen, provide one "
                    "real operator-supplied TRAIN V2 binding and separately "
                    "authorize bounded real-sensor execution."
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


def validate_runtime_input_binding_protocol_v2(
    payload: Mapping[str, object],
) -> Mapping[str, object]:
    if not isinstance(
        payload,
        Mapping,
    ):
        raise SE4RuntimeInputBindingError(
            "V2 protocol payload must be a mapping"
        )

    expected = (
        build_runtime_input_binding_protocol_v2()
    )

    if dict(
        payload
    ) != expected:
        raise SE4RuntimeInputBindingError(
            "V2 runtime-input protocol differs from canonical state"
        )

    return payload


def assert_real_sensor_execution_authorized_v2(
    payload: Mapping[str, object],
) -> None:
    validate_runtime_input_binding_protocol_v2(
        payload
    )

    if payload[
        "transition_policy"
    ][
        "real_sensor_execution_authorized"
    ] is not True:
        raise SE4RuntimeInputBindingError(
            "real-sensor execution remains blocked: V2 resolves the HTTP-port "
            "schema gap but no real TRAIN V2 binding or separate execution "
            "authorization exists"
        )


def assert_health_supervision_available_v2(
    payload: Mapping[str, object],
) -> None:
    validate_runtime_input_binding_protocol_v2(
        payload
    )

    science = payload[
        "scientific_boundary"
    ]

    if (
        science[
            "accepted_health_supervision_source_count"
        ] <= 0
        or science[
            "real_health_label_count"
        ] <= 0
    ):
        raise SE4RuntimeInputBindingError(
            "health supervision remains unavailable: V2 runtime binding "
            "resolution neither accepts a supervision source nor creates "
            "real health labels"
        )
