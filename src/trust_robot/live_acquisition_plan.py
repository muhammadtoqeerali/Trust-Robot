from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from ipaddress import ip_address
import json
from pathlib import PurePath

from .baseline_nominality import BaselineNominalitySplit


LIVE_ACQUISITION_PLAN_SCHEMA = (
    "TRUST_ROBOT_PHASE5_LIVE_ACQUISITION_PLAN_V1"
)

LIVE_ACQUISITION_PLAN_PROTOCOL_ID = (
    "trust_robot_phase5_vlp32c_nonexecuting_live_acquisition_plan_v1"
)

EXPECTED_MODALITY = "lidar"
EXPECTED_VENDOR = "Velodyne"
EXPECTED_MODEL = "VLP-32C"

INFO_PATH = "/cgi/info.json"
STATUS_PATH = "/cgi/status.json"
DIAGNOSTIC_PATH = "/cgi/diag.json"


class LiveAcquisitionPlanError(ValueError):
    """Raised when a non-executing acquisition plan is malformed."""


def _text(
    value: object,
    *,
    name: str,
) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
    ):
        raise LiveAcquisitionPlanError(
            f"{name} must be a non-empty string"
        )

    return value


def _exact_int(
    value: object,
    *,
    name: str,
    minimum: int,
    maximum: int | None = None,
) -> int:
    if (
        type(value) is not int
        or value < minimum
        or (
            maximum is not None
            and value > maximum
        )
    ):
        maximum_text = (
            ""
            if maximum is None
            else f" and <= {maximum}"
        )

        raise LiveAcquisitionPlanError(
            f"{name} must be an exact int >= {minimum}{maximum_text}"
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


@dataclass(frozen=True)
class Vlp32cLiveAcquisitionPlanCandidate:
    """Pure, deterministic command plan.

    Construction performs no subprocess call, network I/O, socket operation,
    sensor probe, filesystem capture, source acceptance, or health labeling.
    """

    acquisition_session_id: str
    split: BaselineNominalitySplit

    sensor_ipv4: str
    capture_interface: str
    data_udp_port: int
    telemetry_udp_port: int
    capture_duration_seconds: int
    output_directory: str

    modality: str = EXPECTED_MODALITY
    hardware_vendor: str = EXPECTED_VENDOR
    hardware_model: str = EXPECTED_MODEL

    def __post_init__(
        self,
    ) -> None:
        for name in (
            "acquisition_session_id",
            "sensor_ipv4",
            "capture_interface",
            "output_directory",
            "modality",
            "hardware_vendor",
            "hardware_model",
        ):
            _text(
                getattr(self, name),
                name=name,
            )

        if not isinstance(
            self.split,
            BaselineNominalitySplit,
        ):
            raise LiveAcquisitionPlanError(
                "split must be BaselineNominalitySplit"
            )

        try:
            parsed_ip = ip_address(
                self.sensor_ipv4
            )
        except ValueError as exc:
            raise LiveAcquisitionPlanError(
                "sensor_ipv4 must be a valid IPv4 address"
            ) from exc

        if parsed_ip.version != 4:
            raise LiveAcquisitionPlanError(
                "sensor_ipv4 must be IPv4"
            )

        _exact_int(
            self.data_udp_port,
            name="data_udp_port",
            minimum=1,
            maximum=65535,
        )

        _exact_int(
            self.telemetry_udp_port,
            name="telemetry_udp_port",
            minimum=1,
            maximum=65535,
        )

        _exact_int(
            self.capture_duration_seconds,
            name="capture_duration_seconds",
            minimum=1,
        )

        if self.modality != EXPECTED_MODALITY:
            raise LiveAcquisitionPlanError(
                "plan is LiDAR-only"
            )

        if self.hardware_vendor != EXPECTED_VENDOR:
            raise LiveAcquisitionPlanError(
                "unexpected hardware vendor"
            )

        if self.hardware_model != EXPECTED_MODEL:
            raise LiveAcquisitionPlanError(
                "unexpected hardware model"
            )

    def _output(
        self,
        name: str,
    ) -> str:
        return str(
            PurePath(
                self.output_directory
            )
            / name
        )

    def _http_argv(
        self,
        *,
        endpoint: str,
        body_name: str,
        header_name: str,
    ) -> list[str]:
        return [
            "curl",
            "--fail-with-body",
            "--silent",
            "--show-error",
            "--dump-header",
            self._output(header_name),
            "--output",
            self._output(body_name),
            f"http://{self.sensor_ipv4}{endpoint}",
        ]

    def _packet_argv(
        self,
        *,
        port: int,
        output_name: str,
    ) -> list[str]:
        return [
            "timeout",
            "--signal=INT",
            f"{self.capture_duration_seconds}s",
            "tcpdump",
            "-i",
            self.capture_interface,
            "-nn",
            "-s",
            "0",
            "-w",
            self._output(output_name),
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
                    endpoint=INFO_PATH,
                    body_name="info.json",
                    header_name="info.headers",
                ),

            "status_http":
                self._http_argv(
                    endpoint=STATUS_PATH,
                    body_name="status.json",
                    header_name="status.headers",
                ),

            "diagnostic_http":
                self._http_argv(
                    endpoint=DIAGNOSTIC_PATH,
                    body_name="diagnostic.json",
                    header_name="diagnostic.headers",
                ),

            "measurement_packet_capture":
                self._packet_argv(
                    port=self.data_udp_port,
                    output_name="measurement_packets.pcap",
                ),

            "position_packet_capture":
                self._packet_argv(
                    port=self.telemetry_udp_port,
                    output_name="position_packets.pcap",
                ),
        }

    def to_dict(
        self,
    ) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema":
                LIVE_ACQUISITION_PLAN_SCHEMA,

            "protocol_id":
                LIVE_ACQUISITION_PLAN_PROTOCOL_ID,

            "acquisition_session_id":
                self.acquisition_session_id,

            "split":
                self.split.value,

            "hardware": {
                "modality":
                    self.modality,

                "vendor":
                    self.hardware_vendor,

                "model":
                    self.hardware_model,
            },

            "explicit_runtime_parameters": {
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

                "output_directory":
                    self.output_directory,
            },

            "commands":
                self.command_argv(),

            "execution_boundary": {
                "argv_plan_only":
                    True,

                "subprocess_executed":
                    False,

                "network_io_performed":
                    False,

                "sensor_probe_performed":
                    False,

                "filesystem_capture_performed":
                    False,

                "command_order_selected":
                    False,

                "status_polling_period_selected":
                    False,
            },

            "scientific_nonclaims": {
                "host_capture_time_is_physical_measurement_time":
                    False,

                "interval_binding_established":
                    False,

                "baseline_nominality_established":
                    False,

                "supervision_source_accepted":
                    False,

                "health_label_assigned":
                    False,

                "timing_tolerance_selected":
                    False,

                "fixed_offset_selected":
                    False,

                "interpolation_selected":
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


def build_empty_live_acquisition_plan_registry(
) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema":
            LIVE_ACQUISITION_PLAN_SCHEMA,

        "protocol_id":
            LIVE_ACQUISITION_PLAN_PROTOCOL_ID,

        "live_plan_instance_count":
            0,

        "sensor_network_address_selected":
            False,

        "live_sensor_probe_performed":
            False,

        "raw_capture_artifact_count":
            0,

        "accepted_baseline_nominality_source_count":
            0,

        "accepted_health_supervision_source_count":
            0,

        "real_health_label_count":
            0,

        "live_execution_authorized":
            False,

        "health_label_generation_authorized":
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
