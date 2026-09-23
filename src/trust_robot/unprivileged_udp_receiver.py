from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from ipaddress import ip_address
from pathlib import Path
import json
import os
import re
import select
import socket
import time

from .baseline_nominality import BaselineNominalitySplit
from .live_executor_safety import (
    LiveExecutorSafetyError,
    publish_same_directory_partial_file,
    reserve_fresh_session_directory,
)


UNPRIVILEGED_UDP_RECEIVER_SCHEMA = (
    "TRUST_ROBOT_PHASE5_UNPRIVILEGED_UDP_RECEIVER_V1"
)

UNPRIVILEGED_UDP_RECEIVER_PROTOCOL_ID = (
    "trust_robot_phase5_vlp32c_unprivileged_dual_udp_receiver_v1"
)

_SESSION_ID_RE = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9._-]*$"
)

_STREAM_NAMES = (
    "measurement",
    "position",
)


class UnprivilegedUdpReceiverError(ValueError):
    """Raised when the user-space UDP receiver contract is violated."""


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


def _text(
    value: object,
    *,
    name: str,
) -> str:
    if (
        not isinstance(
            value,
            str,
        )
        or not value.strip()
    ):
        raise UnprivilegedUdpReceiverError(
            f"{name} must be a non-empty string"
        )

    return value


def _positive_int(
    value: object,
    *,
    name: str,
    maximum: int | None = None,
) -> int:
    if (
        type(
            value
        )
        is not int
        or value < 1
        or (
            maximum is not None
            and value > maximum
        )
    ):
        suffix = (
            ""
            if maximum is None
            else f" and <= {maximum}"
        )

        raise UnprivilegedUdpReceiverError(
            f"{name} must be an exact int >= 1{suffix}"
        )

    return value


def _validate_ipv4(
    value: object,
    *,
    name: str,
) -> str:
    _text(
        value,
        name=name,
    )

    try:
        parsed = ip_address(
            value
        )
    except ValueError as exc:
        raise UnprivilegedUdpReceiverError(
            f"{name} must be a valid IPv4 address"
        ) from exc

    if parsed.version != 4:
        raise UnprivilegedUdpReceiverError(
            f"{name} must be IPv4"
        )

    return str(
        parsed
    )


@dataclass(frozen=True)
class Vlp32cUnprivilegedUdpReceiverCandidate:
    acquisition_session_id: str
    split: BaselineNominalitySplit

    bind_ipv4: str
    measurement_udp_port: int
    position_udp_port: int

    capture_duration_seconds: int
    absolute_output_root: str

    def __post_init__(
        self,
    ) -> None:
        _text(
            self.acquisition_session_id,
            name="acquisition_session_id",
        )

        if (
            _SESSION_ID_RE.fullmatch(
                self.acquisition_session_id
            )
            is None
        ):
            raise UnprivilegedUdpReceiverError(
                "acquisition_session_id must be a safe path component"
            )

        if not isinstance(
            self.split,
            BaselineNominalitySplit,
        ):
            raise UnprivilegedUdpReceiverError(
                "split must be BaselineNominalitySplit"
            )

        _validate_ipv4(
            self.bind_ipv4,
            name="bind_ipv4",
        )

        _positive_int(
            self.measurement_udp_port,
            name="measurement_udp_port",
            maximum=65535,
        )

        _positive_int(
            self.position_udp_port,
            name="position_udp_port",
            maximum=65535,
        )

        if (
            self.measurement_udp_port
            == self.position_udp_port
        ):
            raise UnprivilegedUdpReceiverError(
                "measurement and position UDP ports must be distinct"
            )

        _positive_int(
            self.capture_duration_seconds,
            name="capture_duration_seconds",
        )

        _text(
            self.absolute_output_root,
            name="absolute_output_root",
        )

        if not Path(
            self.absolute_output_root
        ).is_absolute():
            raise UnprivilegedUdpReceiverError(
                "absolute_output_root must be absolute"
            )

    def to_dict(
        self,
    ) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema":
                UNPRIVILEGED_UDP_RECEIVER_SCHEMA,

            "protocol_id":
                UNPRIVILEGED_UDP_RECEIVER_PROTOCOL_ID,

            "acquisition_session_id":
                self.acquisition_session_id,

            "split":
                self.split.value,

            "bind_ipv4":
                self.bind_ipv4,

            "measurement_udp_port":
                self.measurement_udp_port,

            "position_udp_port":
                self.position_udp_port,

            "capture_duration_seconds":
                self.capture_duration_seconds,

            "absolute_output_root":
                self.absolute_output_root,

            "receiver_semantics": {
                "socket_family":
                    "AF_INET",

                "socket_type":
                    "SOCK_DGRAM",

                "requires_root":
                    False,

                "requires_sudo":
                    False,

                "requires_cap_net_raw":
                    False,

                "passive_interface_sniffing":
                    False,
            },

            "scientific_nonclaims": {
                "host_userspace_receive_time_is_physical_measurement_time":
                    False,

                "no_packet_loss_established":
                    False,

                "interval_binding_established":
                    False,

                "baseline_nominality_established":
                    False,

                "sensor_health_established":
                    False,

                "health_label_assigned":
                    False,
            },

            "real_sensor_execution_authorized":
                False,
        }

        payload[
            "content_sha256"
        ] = sha256(
            _canonical_json(
                payload
            ).encode(
                "utf-8"
            )
        ).hexdigest()

        return payload


def _stream_paths(
    session_directory: Path,
    stream_name: str,
) -> dict[str, Path]:
    if stream_name not in _STREAM_NAMES:
        raise UnprivilegedUdpReceiverError(
            "unexpected stream name"
        )

    return {
        "payload_partial":
            (
                session_directory
                / f".{stream_name}_payloads.bin.partial"
            ),

        "payload_final":
            (
                session_directory
                / f"{stream_name}_payloads.bin"
            ),

        "metadata_partial":
            (
                session_directory
                / f".{stream_name}_datagrams.jsonl.partial"
            ),

        "metadata_final":
            (
                session_directory
                / f"{stream_name}_datagrams.jsonl"
            ),
    }


def _bind_udp_socket(
    bind_ipv4: str,
    port: int,
) -> socket.socket:
    receiver = socket.socket(
        socket.AF_INET,
        socket.SOCK_DGRAM,
    )

    try:
        receiver.bind(
            (
                bind_ipv4,
                port,
            )
        )

        receiver.setblocking(
            False
        )

    except Exception:
        receiver.close()
        raise

    return receiver


def capture_dual_udp_payload_streams(
    candidate: Vlp32cUnprivilegedUdpReceiverCandidate,
) -> dict[str, object]:
    """Capture two delivered UDP payload streams as an ordinary user.

    This preserves UDP payload bytes and per-datagram boundaries. It does not
    passively sniff an interface and does not preserve Ethernet/IP/UDP headers.
    """

    if not isinstance(
        candidate,
        Vlp32cUnprivilegedUdpReceiverCandidate,
    ):
        raise UnprivilegedUdpReceiverError(
            "candidate must be Vlp32cUnprivilegedUdpReceiverCandidate"
        )

    measurement_socket = None
    position_socket = None

    try:
        measurement_socket = _bind_udp_socket(
            candidate.bind_ipv4,
            candidate.measurement_udp_port,
        )

        position_socket = _bind_udp_socket(
            candidate.bind_ipv4,
            candidate.position_udp_port,
        )

        try:
            session_directory = reserve_fresh_session_directory(
                candidate.absolute_output_root,
                candidate.acquisition_session_id,
            )
        except LiveExecutorSafetyError as exc:
            raise UnprivilegedUdpReceiverError(
                str(
                    exc
                )
            ) from exc

        paths = {
            stream_name:
                _stream_paths(
                    session_directory,
                    stream_name,
                )
            for stream_name
            in _STREAM_NAMES
        }

        payload_handles = {}
        metadata_handles = {}

        try:
            for stream_name in _STREAM_NAMES:
                payload_handles[
                    stream_name
                ] = paths[
                    stream_name
                ][
                    "payload_partial"
                ].open(
                    "xb"
                )

                metadata_handles[
                    stream_name
                ] = paths[
                    stream_name
                ][
                    "metadata_partial"
                ].open(
                    "x",
                    encoding="utf-8",
                    newline="\n",
                )

            sockets = {
                measurement_socket:
                    "measurement",

                position_socket:
                    "position",
            }

            counts = {
                stream_name:
                    0
                for stream_name
                in _STREAM_NAMES
            }

            byte_counts = {
                stream_name:
                    0
                for stream_name
                in _STREAM_NAMES
            }

            start_monotonic_ns = time.monotonic_ns()
            start_wall_time_ns = time.time_ns()

            deadline_monotonic_ns = (
                start_monotonic_ns
                + candidate.capture_duration_seconds
                * 1_000_000_000
            )

            while True:
                now_ns = time.monotonic_ns()

                if now_ns >= deadline_monotonic_ns:
                    break

                timeout_seconds = (
                    deadline_monotonic_ns
                    - now_ns
                ) / 1_000_000_000

                readable, _, _ = select.select(
                    list(
                        sockets
                    ),
                    [],
                    [],
                    timeout_seconds,
                )

                if not readable:
                    continue

                for receiver in readable:
                    payload, source = receiver.recvfrom(
                        65535
                    )

                    host_receive_monotonic_ns = time.monotonic_ns()
                    host_receive_wall_time_ns = time.time_ns()

                    stream_name = sockets[
                        receiver
                    ]

                    offset = byte_counts[
                        stream_name
                    ]

                    payload_handles[
                        stream_name
                    ].write(
                        payload
                    )

                    record = {
                        "stream":
                            stream_name,

                        "datagram_index":
                            counts[
                                stream_name
                            ],

                        "payload_offset":
                            offset,

                        "payload_byte_count":
                            len(
                                payload
                            ),

                        "payload_sha256":
                            sha256(
                                payload
                            ).hexdigest(),

                        "source_ipv4":
                            source[
                                0
                            ],

                        "source_udp_port":
                            source[
                                1
                            ],

                        "destination_bind_ipv4":
                            candidate.bind_ipv4,

                        "destination_udp_port":
                            (
                                candidate.measurement_udp_port
                                if stream_name
                                == "measurement"
                                else candidate.position_udp_port
                            ),

                        "host_userspace_receive_monotonic_ns":
                            host_receive_monotonic_ns,

                        "host_userspace_receive_wall_time_ns":
                            host_receive_wall_time_ns,

                        "host_receive_times_transport_provenance_only":
                            True,

                        "physical_measurement_time_claimed":
                            False,

                        "interval_binding_claimed":
                            False,

                        "health_label_claimed":
                            False,
                    }

                    metadata_handles[
                        stream_name
                    ].write(
                        _canonical_json(
                            record
                        )
                        + "\n"
                    )

                    counts[
                        stream_name
                    ] += 1

                    byte_counts[
                        stream_name
                    ] += len(
                        payload
                    )

            end_monotonic_ns = time.monotonic_ns()
            end_wall_time_ns = time.time_ns()

            for handle in (
                *payload_handles.values(),
                *metadata_handles.values(),
            ):
                handle.flush()

                os.fsync(
                    handle.fileno()
                )

        finally:
            for handle in payload_handles.values():
                handle.close()

            for handle in metadata_handles.values():
                handle.close()

        if any(
            counts[
                stream_name
            ]
            == 0
            for stream_name
            in _STREAM_NAMES
        ):
            raise UnprivilegedUdpReceiverError(
                "each stream must contain at least one datagram before "
                "raw evidence publication"
            )

        publications = {}

        for stream_name in _STREAM_NAMES:
            publications[
                stream_name
            ] = {
                "payload":
                    publish_same_directory_partial_file(
                        paths[
                            stream_name
                        ][
                            "payload_partial"
                        ],
                        paths[
                            stream_name
                        ][
                            "payload_final"
                        ],
                    ),

                "metadata":
                    publish_same_directory_partial_file(
                        paths[
                            stream_name
                        ][
                            "metadata_partial"
                        ],
                        paths[
                            stream_name
                        ][
                            "metadata_final"
                        ],
                    ),
            }

        receipt = {
            "schema":
                UNPRIVILEGED_UDP_RECEIVER_SCHEMA,

            "protocol_id":
                UNPRIVILEGED_UDP_RECEIVER_PROTOCOL_ID,

            "acquisition_session_id":
                candidate.acquisition_session_id,

            "split":
                candidate.split.value,

            "bind_ipv4":
                candidate.bind_ipv4,

            "measurement_udp_port":
                candidate.measurement_udp_port,

            "position_udp_port":
                candidate.position_udp_port,

            "capture_duration_seconds":
                candidate.capture_duration_seconds,

            "host_capture_start_monotonic_ns":
                start_monotonic_ns,

            "host_capture_end_monotonic_ns":
                end_monotonic_ns,

            "host_capture_start_wall_time_ns":
                start_wall_time_ns,

            "host_capture_end_wall_time_ns":
                end_wall_time_ns,

            "host_times_transport_provenance_only":
                True,

            "streams": {
                stream_name: {
                    "datagram_count":
                        counts[
                            stream_name
                        ],

                    "payload_byte_count":
                        byte_counts[
                            stream_name
                        ],

                    "payload_artifact":
                        publications[
                            stream_name
                        ][
                            "payload"
                        ],

                    "metadata_artifact":
                        publications[
                            stream_name
                        ][
                            "metadata"
                        ],
                }
                for stream_name
                in _STREAM_NAMES
            },

            "receiver_semantics": {
                "ordinary_udp_socket":
                    True,

                "passive_interface_sniffing":
                    False,

                "ethernet_headers_preserved":
                    False,

                "ip_headers_preserved":
                    False,

                "udp_headers_preserved":
                    False,

                "udp_payload_bytes_preserved":
                    True,
            },

            "scientific_nonclaims": {
                "physical_measurement_time_established":
                    False,

                "absence_of_packet_loss_established":
                    False,

                "interval_binding_established":
                    False,

                "baseline_nominality_established":
                    False,

                "health_supervision_source_accepted":
                    False,

                "health_label_assigned":
                    False,
            },

            "real_sensor_execution_authorized":
                False,
        }

        receipt[
            "content_sha256"
        ] = sha256(
            _canonical_json(
                receipt
            ).encode(
                "utf-8"
            )
        ).hexdigest()

        receipt_partial = (
            session_directory
            / ".capture_receipt.json.partial"
        )

        receipt_final = (
            session_directory
            / "capture_receipt.json"
        )

        with receipt_partial.open(
            "x",
            encoding="utf-8",
            newline="\n",
        ) as handle:
            handle.write(
                json.dumps(
                    receipt,
                    indent=2,
                    sort_keys=True,
                )
                + "\n"
            )

            handle.flush()

            os.fsync(
                handle.fileno()
            )

        receipt_publication = (
            publish_same_directory_partial_file(
                receipt_partial,
                receipt_final,
            )
        )

        return {
            "session_directory":
                str(
                    session_directory
                ),

            "capture_receipt":
                receipt,

            "capture_receipt_publication":
                receipt_publication,
        }

    finally:
        if measurement_socket is not None:
            measurement_socket.close()

        if position_socket is not None:
            position_socket.close()


def build_empty_unprivileged_udp_receiver_registry(
) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema":
            UNPRIVILEGED_UDP_RECEIVER_SCHEMA,

        "protocol_id":
            UNPRIVILEGED_UDP_RECEIVER_PROTOCOL_ID,

        "loopback_receiver_execution_verified":
            True,

        "real_sensor_receiver_execution_verified":
            False,

        "real_sensor_execution_authorized":
            False,

        "actual_bind_ipv4_selected":
            False,

        "actual_measurement_udp_port_selected":
            False,

        "actual_position_udp_port_selected":
            False,

        "raw_capture_artifact_count":
            0,

        "accepted_baseline_nominality_source_count":
            0,

        "accepted_health_supervision_source_count":
            0,

        "real_health_label_count":
            0,

        "interval_binding_selected":
            False,

        "classifier_training_authorized":
            False,
    }

    payload[
        "content_sha256"
    ] = sha256(
        _canonical_json(
            payload
        ).encode(
            "utf-8"
        )
    ).hexdigest()

    return payload
