"""SE4 prospective supervision-acquisition mechanism resolution.

This module resolves only software acquisition mechanisms for future
admissible TRAIN health-supervision evidence.

It does not:
- contact any sensor;
- choose a real network address or capture interface;
- choose UDP ports, capture duration, output root or HTTP timeout values;
- establish physical measurement time or interval binding;
- accept a baseline or supervision source;
- assign health labels;
- authorize model training;
- open validation or confirmation.
"""

from __future__ import annotations

from hashlib import sha256
from typing import Mapping
import json


SCHEMA = (
    "TRUST_ROBOT_SE4_SUPERVISION_ACQUISITION_MECHANISM_RESOLUTION_V1"
)

SCHEMA_VERSION = 1

RESOLUTION_ID = (
    "trust_robot_se4_supervision_acquisition_mechanism_resolution_v1"
)

FROZEN_INPUT_SHA256 = {
    "SE4_blocked_frontier_freeze":
        "8ced2b97595a541fb152b5fd012d83c6c8d8b99a770a0cd1e1a6e7c55d6f248d",

    "phase5_live_acquisition_plan":
        "9988bf72a341a045831b2efe49d393f6886075ca179034ceecf4a191b4f8992d",

    "live_acquisition_plan_module":
        "196a88bde3f96c98985121c13444190984c1622dceb648817ead8ef3320956a6",

    "phase5_live_executor_safety":
        "9370692895bc156552a664b23fd84445a32a3b20ead8c1d1c4f495c31e6dca6a",

    "live_executor_safety_module":
        "6dcb292355ba17ec8a563b1183e0279b40559ec0467dd8dc9fbba5a2e674e26a",

    "phase5_acquisition_session_provenance":
        "08b691bcc0eb3db7d9b0059608f8134b7b6086f526b6c11e64cf03ac3efa763b",

    "phase5_baseline_nominality_raw_capture":
        "9d71073e3620e1b3447a9bc11952c1a3a909ec7b14fa14cfda075f8d3fdbc5a7",
}

HTTP_PATHS = {
    "identity":
        "/cgi/info.json",

    "status":
        "/cgi/status.json",

    "diagnostic":
        "/cgi/diag.json",
}

RAW_OUTPUT_NAMES = {
    "identity_body":
        "info.json",

    "identity_headers":
        "info.headers",

    "status_body":
        "status.json",

    "status_headers":
        "status.headers",

    "diagnostic_body":
        "diagnostic.json",

    "diagnostic_headers":
        "diagnostic.headers",

    "measurement_packets":
        "measurement_packets.pcap",

    "position_packets":
        "position_packets.pcap",
}


class SE4SupervisionAcquisitionMechanismResolutionError(
    ValueError
):
    """Raised when the prospective acquisition mechanism is violated."""


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


def content_sha256(
    payload: Mapping[str, object],
) -> str:
    body = dict(
        payload
    )

    body.pop(
        "content_sha256",
        None,
    )

    return sha256(
        _canonical_json(
            body
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def build_se4_supervision_acquisition_mechanism_resolution(
) -> dict[str, object]:
    """Build the exact prospective, non-executing acquisition resolution."""

    payload: dict[str, object] = {
        "schema":
            SCHEMA,

        "schema_version":
            SCHEMA_VERSION,

        "resolution_id":
            RESOLUTION_ID,

        "stage_context": {
            "stage_id":
                "SE4",

            "SE4_complete":
                False,

            "SE4_training_authorized":
                False,

            "purpose":
                (
                    "Resolve deterministic prospective raw-evidence "
                    "acquisition mechanisms needed before admissible "
                    "TRAIN health supervision can exist."
                ),
        },

        "hardware_scope": {
            "vendor":
                "Velodyne",

            "model":
                "VLP-32C",

            "modality":
                "lidar",
        },

        "selected_acquisition_mechanisms": {
            "device_identity": {
                "selected":
                    True,

                "transport":
                    "HTTP",

                "method":
                    "GET",

                "request_path":
                    HTTP_PATHS[
                        "identity"
                    ],

                "execution_shape":
                    "one_shot",

                "raw_body_preserved":
                    True,

                "raw_headers_preserved":
                    True,

                "primary_identity_field":
                    "serial",
            },

            "sensor_status": {
                "selected":
                    True,

                "transport":
                    "HTTP",

                "method":
                    "GET",

                "request_path":
                    HTTP_PATHS[
                        "status"
                    ],

                "execution_shape":
                    "one_shot",

                "raw_body_preserved":
                    True,

                "raw_headers_preserved":
                    True,

                "establishes_health_label":
                    False,
            },

            "sensor_diagnostic": {
                "selected":
                    True,

                "transport":
                    "HTTP",

                "method":
                    "GET",

                "request_path":
                    HTTP_PATHS[
                        "diagnostic"
                    ],

                "execution_shape":
                    "one_shot",

                "raw_body_preserved":
                    True,

                "raw_headers_preserved":
                    True,

                "establishes_health_label":
                    False,
            },

            "measurement_packets": {
                "selected":
                    True,

                "transport":
                    "UDP",

                "preservation":
                    "classic_pcap",

                "capture_tool":
                    "tcpdump",

                "bounded_process_tool":
                    "timeout",

                "duration_bounded":
                    True,

                "port_value_selected":
                    False,

                "capture_interface_selected":
                    False,

                "at_least_one_packet_required_for_publication":
                    True,
            },

            "position_packets": {
                "selected":
                    True,

                "transport":
                    "UDP",

                "preservation":
                    "classic_pcap",

                "capture_tool":
                    "tcpdump",

                "bounded_process_tool":
                    "timeout",

                "duration_bounded":
                    True,

                "port_value_selected":
                    False,

                "capture_interface_selected":
                    False,

                "at_least_one_packet_required_for_publication":
                    True,
            },
        },

        "raw_output_contract": {
            **RAW_OUTPUT_NAMES,
        },

        "executor_safety_binding": {
            "absolute_output_root_required":
                True,

            "fresh_session_directory_required":
                True,

            "existing_final_artifact_overwrite_allowed":
                False,

            "same_directory_partial_file_required":
                True,

            "file_fsync_before_publish_required":
                True,

            "directory_fsync_after_publish_required":
                True,

            "sha256_before_publish_required":
                True,

            "sha256_after_publish_required":
                True,

            "pre_and_post_publish_sha256_must_match":
                True,

            "pcap_structural_validation_required":
                True,

            "process_terminal_state_receipt_required":
                True,

            "sigint_request_receipt_required":
                True,

            "kill_after_grace_receipt_required":
                True,
        },

        "required_future_runtime_parameters": {
            "acquisition_session_id":
                "required_no_default",

            "split":
                "required_must_be_TRAIN",

            "sensor_ipv4":
                "required_no_default",

            "capture_interface":
                "required_no_default",

            "data_udp_port":
                "required_no_default",

            "telemetry_udp_port":
                "required_no_default",

            "capture_duration_seconds":
                "required_no_default",

            "absolute_output_root":
                "required_no_default",

            "http_connect_timeout_seconds":
                "required_no_default",

            "http_total_timeout_seconds":
                "required_no_default",

            "capture_shutdown_grace_seconds":
                "required_no_default",
        },

        "explicitly_unselected_runtime_values": {
            "sensor_ipv4":
                None,

            "capture_interface":
                None,

            "data_udp_port":
                None,

            "telemetry_udp_port":
                None,

            "capture_duration_seconds":
                None,

            "absolute_output_root":
                None,

            "http_connect_timeout_seconds":
                None,

            "http_total_timeout_seconds":
                None,

            "capture_shutdown_grace_seconds":
                None,

            "status_polling_period_seconds":
                None,

            "retry_policy":
                None,

            "capture_order":
                None,

            "timing_tolerance":
                None,

            "fixed_time_offset":
                None,

            "interpolation":
                None,

            "physical_interval_binding_mechanism":
                None,
        },

        "provenance_requirements": {
            "acquisition_session_identity_required":
                True,

            "split_role_required":
                True,

            "device_serial_identity_required":
                True,

            "raw_info_response_required":
                True,

            "raw_info_response_sha256_required":
                True,

            "raw_artifact_sha256_required":
                True,

            "capture_metadata_sha256_required":
                True,

            "host_capture_start_ns_required":
                True,

            "host_capture_end_ns_required":
                True,

            "host_times_transport_provenance_only":
                True,

            "prospective_no_intervention_declaration_required":
                True,
        },

        "scientific_boundary": {
            "network_IO_executed":
                False,

            "subprocess_executed":
                False,

            "live_sensor_probe_executed":
                False,

            "raw_capture_artifact_count":
                0,

            "device_identity_receipt_count":
                0,

            "baseline_nominality_source_accepted":
                False,

            "health_supervision_source_accepted":
                False,

            "real_health_label_count":
                0,

            "health_label_generation_authorized":
                False,

            "classifier_training_authorized":
                False,

            "physical_measurement_time_selected":
                False,

            "interval_binding_established":
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
            "acquisition_mechanism_resolved":
                True,

            "live_execution_authorized":
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

            "next_unresolved_runtime_inputs_include_physical_environment_values":
                True,

            "next_required_evidence":
                (
                    "Explicit real TRAIN acquisition runtime values and "
                    "authorized execution producing raw provenance-preserved "
                    "evidence; raw capture alone still does not establish "
                    "baseline nominality or health supervision."
                ),
        },

        "frozen_input_sha256":
            dict(
                FROZEN_INPUT_SHA256
            ),
    }

    payload[
        "content_sha256"
    ] = content_sha256(
        payload
    )

    return payload


def validate_se4_supervision_acquisition_mechanism_resolution(
    payload: Mapping[str, object],
) -> Mapping[str, object]:
    """Accept only the exact fail-closed prospective resolution."""

    if not isinstance(
        payload,
        Mapping,
    ):
        raise SE4SupervisionAcquisitionMechanismResolutionError(
            "payload must be a mapping"
        )

    expected = (
        build_se4_supervision_acquisition_mechanism_resolution()
    )

    if dict(payload) != expected:
        raise SE4SupervisionAcquisitionMechanismResolutionError(
            "prospective acquisition mechanism differs from the "
            "frozen resolution"
        )

    return payload


def assert_live_execution_authorized(
    payload: Mapping[str, object],
) -> None:
    """Fail closed: mechanism selection does not authorize live execution."""

    validate_se4_supervision_acquisition_mechanism_resolution(
        payload
    )

    if payload[
        "transition_policy"
    ][
        "live_execution_authorized"
    ] is not True:
        raise SE4SupervisionAcquisitionMechanismResolutionError(
            "live acquisition remains blocked: physical/runtime values and "
            "separate execution authorization are still absent"
        )


def assert_health_supervision_available(
    payload: Mapping[str, object],
) -> None:
    """Fail closed: raw acquisition mechanism is not health truth."""

    validate_se4_supervision_acquisition_mechanism_resolution(
        payload
    )

    boundary = payload[
        "scientific_boundary"
    ]

    if (
        boundary[
            "health_supervision_source_accepted"
        ] is not True
        or boundary[
            "real_health_label_count"
        ] <= 0
    ):
        raise SE4SupervisionAcquisitionMechanismResolutionError(
            "health supervision remains unavailable: no admissible source "
            "has been accepted and no real health labels exist"
        )
