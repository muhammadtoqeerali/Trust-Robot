"""SE4 live-execution transport resolution.

This prospective resolution selects the already-implemented unprivileged
AF_INET/SOCK_DGRAM dual UDP receiver as the intended executable transport for
future VLP-32C measurement and position UDP payload acquisition.

The earlier passive classic-PCAP/tcpdump mechanism remains historical and
hash-frozen; it is not rewritten. This resolution supersedes it only for the
future executable UDP transport path.

Nothing here contacts a sensor, chooses real environment values, accepts
health supervision, assigns labels, or authorizes SE4 model training.
"""

from __future__ import annotations

from hashlib import sha256
from typing import Mapping
import json


SCHEMA = (
    "TRUST_ROBOT_SE4_LIVE_EXECUTION_TRANSPORT_RESOLUTION_V1"
)

SCHEMA_VERSION = 1

RESOLUTION_ID = (
    "trust_robot_se4_live_execution_transport_resolution_v1"
)

FROZEN_INPUT_SHA256 = {
    "SE4_acquisition_mechanism_freeze":
        "18df2dd2a88d60939f31b844f584a21d090f3a15026369e511c2cb4d39dd20f4",

    "SE4_acquisition_mechanism_config":
        "6150971b4a16e5ba2ad51c754174a7fd37df287763559f1fc4f60b481758e464",

    "phase5_unprivileged_udp_receiver_config":
        "96cd1be3cf9ec3a55721cb496cac32a61279682bdf2d11d16b479568435c3b90",

    "unprivileged_udp_receiver_module":
        "05e40722e15434b92d0f8aad93e4a6a9aef71a38dcd8d97e8bddc4f5ec3a385d",

    "unprivileged_udp_receiver_test":
        "a3b04c6e2c6b82388c02f2e57ac303d5bf1f1bc30871f5fd84165a922e967e68",

    "unprivileged_udp_receiver_audit":
        "e1e1c10f77eef88f48800e21c12157f2b3e6cd4f3e4bcdfa68fb7aa2c3981183",

    "phase5_live_executor_safety":
        "9370692895bc156552a664b23fd84445a32a3b20ead8c1d1c4f495c31e6dca6a",

    "live_executor_safety_module":
        "6dcb292355ba17ec8a563b1183e0279b40559ec0467dd8dc9fbba5a2e674e26a",
}


class SE4LiveExecutionTransportResolutionError(
    ValueError
):
    """Raised when the frozen prospective transport resolution is violated."""


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


def build_se4_live_execution_transport_resolution(
) -> dict[str, object]:
    """Build the exact non-executing SE4 transport resolution."""

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

            "sub_frontier":
                "future_live_execution_transport",

            "SE4_complete":
                False,

            "SE4_training_authorized":
                False,
        },

        "historical_transport": {
            "prior_mechanism":
                "passive_classic_pcap_via_tcpdump",

            "historical_freeze_rewritten":
                False,

            "historical_freeze_remains_hash_frozen":
                True,

            "selected_for_future_executable_UDP_path":
                False,

            "reason_not_selected_for_future_executable_UDP_path":
                (
                    "An already-implemented ordinary user-space dual UDP "
                    "receiver provides the prospective executable payload "
                    "transport without passive packet-sniffing privileges."
                ),
        },

        "selected_future_UDP_transport": {
            "transport_id":
                "phase5_unprivileged_dual_udp_receiver_v1",

            "selected":
                True,

            "implementation_exists":
                True,

            "loopback_execution_verified":
                True,

            "real_sensor_execution_verified":
                False,

            "socket_family":
                "AF_INET",

            "socket_type":
                "SOCK_DGRAM",

            "passive_interface_sniffing":
                False,

            "raw_packet_socket":
                False,

            "uses_tcpdump":
                False,

            "requires_root":
                False,

            "requires_sudo":
                False,

            "requires_CAP_NET_RAW":
                False,

            "receives_only_datagrams_delivered_to_bound_UDP_socket":
                True,
        },

        "preserved_UDP_evidence": {
            "exact_UDP_payload_bytes":
                True,

            "per_datagram_boundaries_preserved":
                True,

            "per_datagram_SHA256_required":
                True,

            "stream_identity_preserved":
                True,

            "datagram_index_preserved":
                True,

            "payload_offset_preserved":
                True,

            "payload_length_preserved":
                True,

            "source_IPv4_preserved":
                True,

            "source_UDP_port_preserved":
                True,

            "destination_bind_IPv4_preserved":
                True,

            "destination_UDP_port_preserved":
                True,

            "host_userspace_monotonic_receive_ns_preserved":
                True,

            "host_userspace_wall_time_ns_preserved":
                True,
        },

        "not_preserved_by_selected_UDP_transport": {
            "ethernet_headers":
                False,

            "IP_headers":
                False,

            "UDP_headers":
                False,

            "passively_observed_interface_packets":
                False,

            "proof_of_zero_packet_loss":
                False,
        },

        "future_UDP_output_contract": {
            "measurement_payload_archive":
                "measurement_payloads.bin",

            "measurement_metadata":
                "measurement_datagrams.jsonl",

            "position_payload_archive":
                "position_payloads.bin",

            "position_metadata":
                "position_datagrams.jsonl",

            "capture_receipt":
                "capture_receipt.json",
        },

        "publication_contract": {
            "absolute_output_root_required":
                True,

            "fresh_session_directory_required":
                True,

            "same_directory_partial_files_required":
                True,

            "existing_final_artifact_overwrite_allowed":
                False,

            "atomic_publication_required":
                True,

            "SHA256_before_publication_required":
                True,

            "SHA256_after_publication_required":
                True,

            "pre_post_SHA256_equality_required":
                True,
        },

        "HTTP_transport": {
            "identity_path":
                "/cgi/info.json",

            "status_path":
                "/cgi/status.json",

            "diagnostic_path":
                "/cgi/diag.json",

            "one_shot_requests_selected":
                True,

            "HTTP_execution_implemented_by_this_resolution":
                False,

            "HTTP_execution_authorized":
                False,
        },

        "runtime_values_intentionally_unselected": {
            "bind_IPv4":
                None,

            "measurement_UDP_port":
                None,

            "position_UDP_port":
                None,

            "sensor_IPv4":
                None,

            "capture_duration_seconds":
                None,

            "absolute_output_root":
                None,

            "acquisition_session_id":
                None,

            "HTTP_connect_timeout_seconds":
                None,

            "HTTP_total_timeout_seconds":
                None,

            "VLP32C_destination_configuration":
                None,
        },

        "scientific_boundary": {
            "network_IO_executed":
                False,

            "sensor_contact_executed":
                False,

            "real_sensor_receiver_execution_verified":
                False,

            "raw_real_sensor_capture_artifact_count":
                0,

            "device_identity_receipt_count":
                0,

            "accepted_baseline_nominality_source_count":
                0,

            "accepted_health_supervision_source_count":
                0,

            "real_health_label_count":
                0,

            "interval_binding_established":
                False,

            "userspace_receive_time_is_physical_measurement_time":
                False,

            "UDP_receive_establishes_baseline_nominality":
                False,

            "UDP_receive_establishes_sensor_health":
                False,

            "UDP_receive_establishes_health_supervision":
                False,

            "UDP_receive_proves_no_packet_loss":
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
            "future_UDP_execution_transport_resolved":
                True,

            "unprivileged_receiver_selected":
                True,

            "tcpdump_required_for_selected_UDP_transport":
                False,

            "packet_sniffing_permission_required_for_selected_UDP_transport":
                False,

            "runtime_environment_values_resolved":
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

            "next_required_event":
                (
                    "Resolve explicit real TRAIN bind address, VLP-32C UDP "
                    "destination ports, sensor address, acquisition duration, "
                    "output root and session identity, then separately "
                    "authorize and verify real-sensor acquisition."
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


def validate_se4_live_execution_transport_resolution(
    payload: Mapping[str, object],
) -> Mapping[str, object]:
    """Accept only the exact frozen prospective transport resolution."""

    if not isinstance(
        payload,
        Mapping,
    ):
        raise SE4LiveExecutionTransportResolutionError(
            "payload must be a mapping"
        )

    expected = (
        build_se4_live_execution_transport_resolution()
    )

    if dict(payload) != expected:
        raise SE4LiveExecutionTransportResolutionError(
            "live-execution transport resolution differs from the "
            "frozen prospective state"
        )

    return payload


def assert_real_sensor_execution_authorized(
    payload: Mapping[str, object],
) -> None:
    """Fail closed until real runtime parameters and authorization exist."""

    validate_se4_live_execution_transport_resolution(
        payload
    )

    if payload[
        "transition_policy"
    ][
        "real_sensor_execution_authorized"
    ] is not True:
        raise SE4LiveExecutionTransportResolutionError(
            "real VLP-32C execution remains blocked: explicit physical "
            "runtime values and separate execution authorization are absent"
        )


def assert_health_supervision_available(
    payload: Mapping[str, object],
) -> None:
    """Fail closed: transport implementation does not create health truth."""

    validate_se4_live_execution_transport_resolution(
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
        raise SE4LiveExecutionTransportResolutionError(
            "health supervision remains unavailable: transport selection "
            "does not accept a source or create real health labels"
        )
