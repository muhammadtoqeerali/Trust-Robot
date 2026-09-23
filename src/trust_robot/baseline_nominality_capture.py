from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json
import re
from typing import Iterable

from .baseline_nominality import BaselineNominalitySplit


RAW_CAPTURE_SCHEMA = (
    "TRUST_ROBOT_PHASE5_BASELINE_NOMINALITY_RAW_CAPTURE_V1"
)

RAW_CAPTURE_PROTOCOL_ID = (
    "trust_robot_phase5_vlp32c_raw_evidence_capture_v1"
)

EXPECTED_MODALITY = "lidar"
EXPECTED_VENDOR = "Velodyne"
EXPECTED_MODEL = "VLP-32C"

_SHA256_RE = re.compile(
    r"^[0-9a-f]{64}$"
)


class RawCaptureError(ValueError):
    """Raised when raw acquisition provenance violates the format."""


class RawEvidenceKind(str, Enum):
    MEASUREMENT = "measurement"
    SENSOR_STATUS = "sensor_status"
    SENSOR_DIAGNOSTIC = "sensor_diagnostic"
    POSITION_PACKET = "position_packet"


def _require_text(
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
        raise RawCaptureError(
            f"{name} must be a non-empty string"
        )

    return value


def _require_digest(
    value: object,
    *,
    name: str,
) -> str:
    if (
        not isinstance(
            value,
            str,
        )
        or _SHA256_RE.fullmatch(
            value
        ) is None
    ):
        raise RawCaptureError(
            f"{name} must be a lowercase SHA-256 digest"
        )

    return value


def _require_exact_bool(
    value: object,
    *,
    name: str,
) -> bool:
    if type(value) is not bool:
        raise RawCaptureError(
            f"{name} must be an exact bool"
        )

    return value


def _require_exact_int(
    value: object,
    *,
    name: str,
    minimum: int,
) -> int:
    if (
        type(value) is not int
        or value < minimum
    ):
        raise RawCaptureError(
            f"{name} must be an exact int >= {minimum}"
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
class RawAcquisitionArtifactReceipt:
    """Raw-evidence preservation receipt.

    Host timestamps are transport/provenance observations only.

    A valid receipt does not establish physical measurement time, interval
    binding, nominality, source acceptance, or any health state.
    """

    artifact_id: str
    acquisition_session_id: str

    split: BaselineNominalitySplit
    evidence_kind: RawEvidenceKind

    source_identifier: str

    modality: str
    hardware_vendor: str
    hardware_model: str

    raw_sha256: str
    raw_byte_count: int
    capture_metadata_sha256: str

    host_clock_id: str
    host_capture_start_ns: int
    host_capture_end_ns: int

    raw_bytes_preserved: bool
    capture_metadata_preserved: bool
    host_times_transport_provenance_only: bool

    interval_binding_claimed: bool = False
    physical_measurement_time_claimed: bool = False
    baseline_nominality_claimed: bool = False
    source_acceptance_claimed: bool = False
    health_label_claimed: bool = False

    def __post_init__(
        self,
    ) -> None:
        for name in (
            "artifact_id",
            "acquisition_session_id",
            "source_identifier",
            "modality",
            "hardware_vendor",
            "hardware_model",
            "host_clock_id",
        ):
            _require_text(
                getattr(
                    self,
                    name,
                ),
                name=name,
            )

        if not isinstance(
            self.split,
            BaselineNominalitySplit,
        ):
            raise RawCaptureError(
                "split must be BaselineNominalitySplit"
            )

        if not isinstance(
            self.evidence_kind,
            RawEvidenceKind,
        ):
            raise RawCaptureError(
                "evidence_kind must be RawEvidenceKind"
            )

        if self.modality != EXPECTED_MODALITY:
            raise RawCaptureError(
                "raw-capture format is LiDAR-only"
            )

        if self.hardware_vendor != EXPECTED_VENDOR:
            raise RawCaptureError(
                "unexpected hardware vendor"
            )

        if self.hardware_model != EXPECTED_MODEL:
            raise RawCaptureError(
                "unexpected hardware model"
            )

        _require_digest(
            self.raw_sha256,
            name="raw_sha256",
        )

        _require_digest(
            self.capture_metadata_sha256,
            name="capture_metadata_sha256",
        )

        _require_exact_int(
            self.raw_byte_count,
            name="raw_byte_count",
            minimum=1,
        )

        start = _require_exact_int(
            self.host_capture_start_ns,
            name="host_capture_start_ns",
            minimum=0,
        )

        end = _require_exact_int(
            self.host_capture_end_ns,
            name="host_capture_end_ns",
            minimum=0,
        )

        if end < start:
            raise RawCaptureError(
                "host_capture_end_ns must be >= host_capture_start_ns"
            )

        for name in (
            "raw_bytes_preserved",
            "capture_metadata_preserved",
            "host_times_transport_provenance_only",
            "interval_binding_claimed",
            "physical_measurement_time_claimed",
            "baseline_nominality_claimed",
            "source_acceptance_claimed",
            "health_label_claimed",
        ):
            _require_exact_bool(
                getattr(
                    self,
                    name,
                ),
                name=name,
            )

        if self.raw_bytes_preserved is not True:
            raise RawCaptureError(
                "raw bytes must be preserved"
            )

        if self.capture_metadata_preserved is not True:
            raise RawCaptureError(
                "capture metadata must be preserved"
            )

        if self.host_times_transport_provenance_only is not True:
            raise RawCaptureError(
                "host timestamps must remain transport/provenance only"
            )

        for name in (
            "interval_binding_claimed",
            "physical_measurement_time_claimed",
            "baseline_nominality_claimed",
            "source_acceptance_claimed",
            "health_label_claimed",
        ):
            if getattr(
                self,
                name,
            ):
                raise RawCaptureError(
                    f"{name} must remain false in the raw-capture layer"
                )

    def to_dict(
        self,
    ) -> dict[str, object]:
        return {
            "schema":
                RAW_CAPTURE_SCHEMA,

            "protocol_id":
                RAW_CAPTURE_PROTOCOL_ID,

            "artifact_id":
                self.artifact_id,

            "acquisition_session_id":
                self.acquisition_session_id,

            "split":
                self.split.value,

            "evidence_kind":
                self.evidence_kind.value,

            "source_identifier":
                self.source_identifier,

            "modality":
                self.modality,

            "hardware_vendor":
                self.hardware_vendor,

            "hardware_model":
                self.hardware_model,

            "raw_sha256":
                self.raw_sha256,

            "raw_byte_count":
                self.raw_byte_count,

            "capture_metadata_sha256":
                self.capture_metadata_sha256,

            "host_clock_id":
                self.host_clock_id,

            "host_capture_start_ns":
                self.host_capture_start_ns,

            "host_capture_end_ns":
                self.host_capture_end_ns,

            "raw_bytes_preserved":
                self.raw_bytes_preserved,

            "capture_metadata_preserved":
                self.capture_metadata_preserved,

            "host_times_transport_provenance_only":
                self.host_times_transport_provenance_only,

            "interval_binding_claimed":
                False,

            "physical_measurement_time_claimed":
                False,

            "baseline_nominality_claimed":
                False,

            "source_acceptance_claimed":
                False,

            "health_label_claimed":
                False,

            "raw_capture_only":
                True,
        }

    @property
    def fingerprint_sha256(
        self,
    ) -> str:
        return sha256(
            _canonical_json(
                self.to_dict()
            ).encode(
                "utf-8"
            )
        ).hexdigest()


def build_raw_capture_bundle_manifest(
    artifacts: Iterable[RawAcquisitionArtifactReceipt],
) -> dict[str, object]:
    """Build a deterministic raw-capture bundle without interval semantics."""

    items = tuple(
        artifacts
    )

    if not items:
        raise RawCaptureError(
            "raw-capture bundle must contain at least one artifact"
        )

    for item in items:
        if not isinstance(
            item,
            RawAcquisitionArtifactReceipt,
        ):
            raise RawCaptureError(
                "all bundle items must be RawAcquisitionArtifactReceipt"
            )

    artifact_ids = [
        item.artifact_id
        for item in items
    ]

    if len(
        artifact_ids
    ) != len(
        set(
            artifact_ids
        )
    ):
        raise RawCaptureError(
            "artifact_id values must be unique within a bundle"
        )

    session_ids = {
        item.acquisition_session_id
        for item in items
    }

    if len(
        session_ids
    ) != 1:
        raise RawCaptureError(
            "all artifacts must share one acquisition_session_id"
        )

    splits = {
        item.split
        for item in items
    }

    if len(
        splits
    ) != 1:
        raise RawCaptureError(
            "all artifacts must share one split role"
        )

    hardware = {
        (
            item.modality,
            item.hardware_vendor,
            item.hardware_model,
        )
        for item in items
    }

    if len(
        hardware
    ) != 1:
        raise RawCaptureError(
            "all artifacts must share one modality/hardware identity"
        )

    ordered = sorted(
        items,
        key=lambda item: item.artifact_id,
    )

    counts = {
        kind.value:
            sum(
                item.evidence_kind is kind
                for item in ordered
            )
        for kind in RawEvidenceKind
    }

    payload: dict[str, object] = {
        "schema":
            RAW_CAPTURE_SCHEMA,

        "protocol_id":
            RAW_CAPTURE_PROTOCOL_ID,

        "acquisition_session_id":
            ordered[
                0
            ].acquisition_session_id,

        "split":
            ordered[
                0
            ].split.value,

        "hardware": {
            "modality":
                ordered[
                    0
                ].modality,

            "vendor":
                ordered[
                    0
                ].hardware_vendor,

            "model":
                ordered[
                    0
                ].hardware_model,
        },

        "artifact_count":
            len(
                ordered
            ),

        "artifact_kind_counts":
            counts,

        "artifacts": [
            item.to_dict()
            for item in ordered
        ],

        "scientific_nonclaims": {
            "interval_binding_established":
                False,

            "physical_measurement_time_established":
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


def build_empty_raw_capture_registry_manifest(
) -> dict[str, object]:
    """Return the current no-capture/no-acceptance protocol state."""

    payload: dict[str, object] = {
        "schema":
            RAW_CAPTURE_SCHEMA,

        "protocol_id":
            RAW_CAPTURE_PROTOCOL_ID,

        "raw_artifact_count":
            0,

        "live_sensor_probe_performed":
            False,

        "sensor_network_address_selected":
            False,

        "capture_mechanism_selected":
            False,

        "interval_binding_mechanism_selected":
            False,

        "accepted_baseline_nominality_source_count":
            0,

        "accepted_health_supervision_source_count":
            0,

        "real_health_label_count":
            0,

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
