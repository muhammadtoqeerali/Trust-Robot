from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from ipaddress import ip_address
from pathlib import Path, PurePath
import json
import os
import re
import struct

from .baseline_nominality import BaselineNominalitySplit
from .live_acquisition_plan import Vlp32cLiveAcquisitionPlanCandidate


LIVE_EXECUTOR_SAFETY_SCHEMA = (
    "TRUST_ROBOT_PHASE5_LIVE_EXECUTOR_SAFETY_V1"
)

LIVE_EXECUTOR_SAFETY_PROTOCOL_ID = (
    "trust_robot_phase5_vlp32c_live_executor_safety_v1"
)

_SESSION_ID_RE = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9._-]*$"
)

_PCAP_MAGIC = {
    b"\xd4\xc3\xb2\xa1":
        ("little", "microsecond"),

    b"\xa1\xb2\xc3\xd4":
        ("big", "microsecond"),

    b"\x4d\x3c\xb2\xa1":
        ("little", "nanosecond"),

    b"\xa1\xb2\x3c\x4d":
        ("big", "nanosecond"),
}


class LiveExecutorSafetyError(ValueError):
    """Raised when the offline executor-safety contract is violated."""


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
        raise LiveExecutorSafetyError(
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
        type(value) is not int
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

        raise LiveExecutorSafetyError(
            f"{name} must be an exact int >= 1{suffix}"
        )

    return value


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


def _sha256_file(
    path: Path,
) -> str:
    hasher = sha256()

    with path.open(
        "rb"
    ) as handle:
        for chunk in iter(
            lambda: handle.read(
                1024 * 1024
            ),
            b"",
        ):
            hasher.update(
                chunk
            )

    return hasher.hexdigest()


@dataclass(frozen=True)
class Vlp32cLiveExecutorSafetyPlanCandidate:
    """Non-executing safe argv and publication plan.

    This object performs no network I/O and no subprocess execution.
    Engineering timeout values are explicit future invocation parameters;
    they are not physical sensor timing tolerances.
    """

    acquisition_session_id: str
    split: BaselineNominalitySplit

    sensor_ipv4: str
    capture_interface: str

    data_udp_port: int
    telemetry_udp_port: int
    capture_duration_seconds: int

    absolute_output_root: str

    http_connect_timeout_seconds: int
    http_total_timeout_seconds: int
    capture_shutdown_grace_seconds: int

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
            raise LiveExecutorSafetyError(
                "acquisition_session_id must be a safe path component"
            )

        if not isinstance(
            self.split,
            BaselineNominalitySplit,
        ):
            raise LiveExecutorSafetyError(
                "split must be BaselineNominalitySplit"
            )

        _text(
            self.sensor_ipv4,
            name="sensor_ipv4",
        )

        try:
            parsed_ip = ip_address(
                self.sensor_ipv4
            )
        except ValueError as exc:
            raise LiveExecutorSafetyError(
                "sensor_ipv4 must be a valid IPv4 address"
            ) from exc

        if parsed_ip.version != 4:
            raise LiveExecutorSafetyError(
                "sensor_ipv4 must be IPv4"
            )

        _text(
            self.capture_interface,
            name="capture_interface",
        )

        _positive_int(
            self.data_udp_port,
            name="data_udp_port",
            maximum=65535,
        )

        _positive_int(
            self.telemetry_udp_port,
            name="telemetry_udp_port",
            maximum=65535,
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
            raise LiveExecutorSafetyError(
                "absolute_output_root must be absolute"
            )

        _positive_int(
            self.http_connect_timeout_seconds,
            name="http_connect_timeout_seconds",
        )

        _positive_int(
            self.http_total_timeout_seconds,
            name="http_total_timeout_seconds",
        )

        if (
            self.http_total_timeout_seconds
            < self.http_connect_timeout_seconds
        ):
            raise LiveExecutorSafetyError(
                "http_total_timeout_seconds must be >= "
                "http_connect_timeout_seconds"
            )

        _positive_int(
            self.capture_shutdown_grace_seconds,
            name="capture_shutdown_grace_seconds",
        )

    @property
    def session_directory(
        self,
    ) -> str:
        return str(
            PurePath(
                self.absolute_output_root
            )
            / self.acquisition_session_id
        )

    def _temp(
        self,
        final_name: str,
    ) -> str:
        return str(
            PurePath(
                self.session_directory
            )
            / (
                "."
                + final_name
                + ".partial"
            )
        )

    def _final(
        self,
        final_name: str,
    ) -> str:
        return str(
            PurePath(
                self.session_directory
            )
            / final_name
        )

    def publication_targets(
        self,
    ) -> dict[str, dict[str, str]]:
        names = {
            "info_body":
                "info.json",

            "info_headers":
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

        return {
            key: {
                "temporary":
                    self._temp(
                        final_name
                    ),

                "final":
                    self._final(
                        final_name
                    ),
            }
            for key, final_name
            in names.items()
        }

    def _http_argv(
        self,
        *,
        endpoint: str,
        body_key: str,
        header_key: str,
    ) -> list[str]:
        targets = self.publication_targets()

        return [
            "curl",
            "--fail-with-body",
            "--silent",
            "--show-error",
            "--connect-timeout",
            str(
                self.http_connect_timeout_seconds
            ),
            "--max-time",
            str(
                self.http_total_timeout_seconds
            ),
            "--dump-header",
            targets[
                header_key
            ][
                "temporary"
            ],
            "--output",
            targets[
                body_key
            ][
                "temporary"
            ],
            (
                f"http://{self.sensor_ipv4}"
                f"{endpoint}"
            ),
        ]

    def _pcap_argv(
        self,
        *,
        port: int,
        artifact_key: str,
    ) -> list[str]:
        targets = self.publication_targets()

        return [
            "timeout",
            "--signal=INT",
            (
                "--kill-after="
                f"{self.capture_shutdown_grace_seconds}s"
            ),
            f"{self.capture_duration_seconds}s",
            "tcpdump",
            "-i",
            self.capture_interface,
            "-nn",
            "-s",
            "0",
            "-w",
            targets[
                artifact_key
            ][
                "temporary"
            ],
            (
                f"host {self.sensor_ipv4} "
                f"and udp port {port}"
            ),
        ]

    def command_argv(
        self,
    ) -> dict[str, list[str]]:
        return {
            "identity_http":
                self._http_argv(
                    endpoint="/cgi/info.json",
                    body_key="info_body",
                    header_key="info_headers",
                ),

            "status_http":
                self._http_argv(
                    endpoint="/cgi/status.json",
                    body_key="status_body",
                    header_key="status_headers",
                ),

            "diagnostic_http":
                self._http_argv(
                    endpoint="/cgi/diag.json",
                    body_key="diagnostic_body",
                    header_key="diagnostic_headers",
                ),

            "measurement_packet_capture":
                self._pcap_argv(
                    port=self.data_udp_port,
                    artifact_key="measurement_packets",
                ),

            "position_packet_capture":
                self._pcap_argv(
                    port=self.telemetry_udp_port,
                    artifact_key="position_packets",
                ),
        }

    def to_dict(
        self,
    ) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema":
                LIVE_EXECUTOR_SAFETY_SCHEMA,

            "protocol_id":
                LIVE_EXECUTOR_SAFETY_PROTOCOL_ID,

            "acquisition_session_id":
                self.acquisition_session_id,

            "split":
                self.split.value,

            "session_directory":
                self.session_directory,

            "explicit_engineering_parameters": {
                "sensor_ipv4":
                    self.sensor_ipv4,

                "capture_interface":
                    self.capture_interface,

                "data_udp_port":
                    self.data_udp_port,

                "telemetry_udp_port":
                    self.telemetry_udp_port,

                "capture_duration_seconds":
                    self.capture_duration_seconds,

                "absolute_output_root":
                    self.absolute_output_root,

                "http_connect_timeout_seconds":
                    self.http_connect_timeout_seconds,

                "http_total_timeout_seconds":
                    self.http_total_timeout_seconds,

                "capture_shutdown_grace_seconds":
                    self.capture_shutdown_grace_seconds,
            },

            "publication_targets":
                self.publication_targets(),

            "commands":
                self.command_argv(),

            "execution_boundary": {
                "argv_plan_only":
                    True,

                "filesystem_publication_primitives_available":
                    True,

                "network_io_performed":
                    False,

                "subprocess_executed":
                    False,

                "packet_capture_performed":
                    False,

                "sensor_probe_performed":
                    False,

                "live_execution_authorized":
                    False,
            },

            "scientific_nonclaims": {
                "engineering_http_timeout_is_sensor_timing_tolerance":
                    False,

                "host_time_is_physical_measurement_time":
                    False,

                "interval_binding_established":
                    False,

                "baseline_nominality_established":
                    False,

                "supervision_source_accepted":
                    False,

                "health_label_assigned":
                    False,
            },
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


def reserve_fresh_session_directory(
    absolute_output_root: str,
    acquisition_session_id: str,
) -> Path:
    """Reserve one fresh session directory, rejecting collisions."""

    _text(
        absolute_output_root,
        name="absolute_output_root",
    )

    root = Path(
        absolute_output_root
    )

    if not root.is_absolute():
        raise LiveExecutorSafetyError(
            "absolute_output_root must be absolute"
        )

    if not root.exists():
        raise LiveExecutorSafetyError(
            "absolute_output_root must already exist"
        )

    if not root.is_dir():
        raise LiveExecutorSafetyError(
            "absolute_output_root must be a directory"
        )

    _text(
        acquisition_session_id,
        name="acquisition_session_id",
    )

    if (
        _SESSION_ID_RE.fullmatch(
            acquisition_session_id
        )
        is None
    ):
        raise LiveExecutorSafetyError(
            "acquisition_session_id must be a safe path component"
        )

    session = (
        root
        / acquisition_session_id
    )

    try:
        session.mkdir(
            exist_ok=False
        )
    except FileExistsError as exc:
        raise LiveExecutorSafetyError(
            "session directory already exists"
        ) from exc

    parent_fd = os.open(
        root,
        os.O_RDONLY,
    )

    try:
        os.fsync(
            parent_fd
        )
    finally:
        os.close(
            parent_fd
        )

    return session


def publish_same_directory_partial_file(
    temporary_path: str | Path,
    final_path: str | Path,
) -> dict[str, object]:
    """Hash, fsync and atomically publish one already-written temp file."""

    temporary = Path(
        temporary_path
    )

    final = Path(
        final_path
    )

    if temporary.parent != final.parent:
        raise LiveExecutorSafetyError(
            "temporary and final files must share one parent directory"
        )

    if not temporary.exists():
        raise LiveExecutorSafetyError(
            "temporary file does not exist"
        )

    if not temporary.is_file():
        raise LiveExecutorSafetyError(
            "temporary path must be a regular file"
        )

    if final.exists():
        raise LiveExecutorSafetyError(
            "final artifact already exists"
        )

    byte_count = temporary.stat().st_size

    if byte_count < 1:
        raise LiveExecutorSafetyError(
            "temporary artifact must be non-empty"
        )

    with temporary.open(
        "rb"
    ) as handle:
        os.fsync(
            handle.fileno()
        )

    prepublish_sha256 = _sha256_file(
        temporary
    )

    os.replace(
        temporary,
        final,
    )

    directory_fd = os.open(
        final.parent,
        os.O_RDONLY,
    )

    try:
        os.fsync(
            directory_fd
        )
    finally:
        os.close(
            directory_fd
        )

    postpublish_sha256 = _sha256_file(
        final
    )

    if (
        prepublish_sha256
        != postpublish_sha256
    ):
        raise LiveExecutorSafetyError(
            "artifact SHA-256 changed across publication"
        )

    return {
        "temporary_path":
            str(
                temporary
            ),

        "final_path":
            str(
                final
            ),

        "byte_count":
            byte_count,

        "prepublish_sha256":
            prepublish_sha256,

        "postpublish_sha256":
            postpublish_sha256,

        "same_directory":
            True,

        "file_fsync_before_publish":
            True,

        "atomic_replace_performed":
            True,

        "directory_fsync_after_publish":
            True,

        "sha256_stable_across_publish":
            True,
    }


def validate_classic_pcap_file(
    path: str | Path,
) -> dict[str, object]:
    """Structurally validate a classic libpcap savefile without executing tools."""

    file_path = Path(
        path
    )

    if not file_path.exists():
        raise LiveExecutorSafetyError(
            "PCAP file does not exist"
        )

    data = file_path.read_bytes()

    result: dict[str, object] = {
        "recognized_magic":
            False,

        "complete_global_header":
            False,

        "structurally_complete":
            False,

        "packet_count":
            0,

        "contains_at_least_one_packet":
            False,

        "eligible_for_raw_evidence_publication":
            False,
    }

    if len(
        data
    ) < 24:
        return result

    magic = data[
        :4
    ]

    if magic not in _PCAP_MAGIC:
        return result

    byte_order, resolution = _PCAP_MAGIC[
        magic
    ]

    endian = (
        "<"
        if byte_order == "little"
        else ">"
    )

    (
        version_major,
        version_minor,
        _thiszone,
        _sigfigs,
        snaplen,
        linktype,
    ) = struct.unpack(
        endian + "HHiIII",
        data[
            4:24
        ],
    )

    result.update(
        {
            "recognized_magic":
                True,

            "byte_order":
                byte_order,

            "timestamp_resolution":
                resolution,

            "version_major":
                version_major,

            "version_minor":
                version_minor,

            "snaplen":
                snaplen,

            "linktype":
                linktype,

            "complete_global_header":
                True,
        }
    )

    if (
        snaplen < 1
        or version_major != 2
        or version_minor != 4
    ):
        return result

    offset = 24
    packet_count = 0

    while offset < len(
        data
    ):
        if (
            len(
                data
            )
            - offset
            < 16
        ):
            return result

        (
            _ts_sec,
            _ts_fraction,
            included_length,
            original_length,
        ) = struct.unpack(
            endian + "IIII",
            data[
                offset:
                offset + 16
            ],
        )

        offset += 16

        if (
            included_length > snaplen
            or included_length > original_length
        ):
            return result

        end = (
            offset
            + included_length
        )

        if end > len(
            data
        ):
            return result

        offset = end
        packet_count += 1

    structurally_complete = (
        offset
        == len(
            data
        )
    )

    contains_packets = (
        packet_count > 0
    )

    result.update(
        {
            "structurally_complete":
                structurally_complete,

            "packet_count":
                packet_count,

            "contains_at_least_one_packet":
                contains_packets,

            "eligible_for_raw_evidence_publication":
                (
                    structurally_complete
                    and contains_packets
                ),
        }
    )

    return result


def build_pcap_finalization_receipt(
    path: str | Path,
    *,
    process_return_code: int,
    timeout_expired: bool,
    sigint_requested: bool,
    kill_after_grace_triggered: bool,
) -> dict[str, object]:
    if type(
        process_return_code
    ) is not int:
        raise LiveExecutorSafetyError(
            "process_return_code must be an exact int"
        )

    for name, value in (
        (
            "timeout_expired",
            timeout_expired,
        ),
        (
            "sigint_requested",
            sigint_requested,
        ),
        (
            "kill_after_grace_triggered",
            kill_after_grace_triggered,
        ),
    ):
        if type(
            value
        ) is not bool:
            raise LiveExecutorSafetyError(
                f"{name} must be an exact bool"
            )

    validation = validate_classic_pcap_file(
        path
    )

    return {
        "path":
            str(
                Path(
                    path
                )
            ),

        "process_return_code":
            process_return_code,

        "process_terminal_state_recorded":
            True,

        "timeout_expired":
            timeout_expired,

        "sigint_requested":
            sigint_requested,

        "kill_after_grace_triggered":
            kill_after_grace_triggered,

        "pcap_validation":
            validation,

        "timeout_return_code_alone_determines_validity":
            False,

        "timeout_124_alone_determines_failure":
            False,

        "timeout_124_alone_determines_success":
            False,

        "sensor_health_inferred":
            False,

        "baseline_nominality_inferred":
            False,
    }


def build_empty_live_executor_safety_registry(
) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema":
            LIVE_EXECUTOR_SAFETY_SCHEMA,

        "protocol_id":
            LIVE_EXECUTOR_SAFETY_PROTOCOL_ID,

        "real_output_root_selected":
            False,

        "capture_interface_selected":
            False,

        "sensor_network_address_selected":
            False,

        "actual_packet_capture_permission_verified":
            False,

        "live_execution_authorized":
            False,

        "raw_capture_artifact_count":
            0,

        "accepted_baseline_nominality_source_count":
            0,

        "accepted_health_supervision_source_count":
            0,

        "real_health_label_count":
            0,

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
