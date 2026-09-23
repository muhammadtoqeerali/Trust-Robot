from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import re

from .baseline_nominality import BaselineNominalitySplit


SESSION_PROVENANCE_SCHEMA = (
    "TRUST_ROBOT_PHASE5_ACQUISITION_SESSION_PROVENANCE_V1"
)

SESSION_PROVENANCE_PROTOCOL_ID = (
    "trust_robot_phase5_vlp32c_session_provenance_v1"
)

EXPECTED_MODALITY = "lidar"
EXPECTED_VENDOR = "Velodyne"
EXPECTED_MODEL = "VLP-32C"
EXPECTED_INFO_PATH = "/cgi/info.json"
EXPECTED_BASELINE_CONDITION = "full"

_SHA256_RE = re.compile(
    r"^[0-9a-f]{64}$"
)


class AcquisitionSessionProvenanceError(ValueError):
    """Raised when session provenance violates the frozen format."""


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
        raise AcquisitionSessionProvenanceError(
            f"{name} must be a non-empty string"
        )

    return value


def _digest(
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
        raise AcquisitionSessionProvenanceError(
            f"{name} must be a lowercase SHA-256 digest"
        )

    return value


def _exact_bool(
    value: object,
    *,
    name: str,
) -> bool:
    if type(value) is not bool:
        raise AcquisitionSessionProvenanceError(
            f"{name} must be an exact bool"
        )

    return value


def _exact_int(
    value: object,
    *,
    name: str,
    minimum: int,
) -> int:
    if (
        type(value) is not int
        or value < minimum
    ):
        raise AcquisitionSessionProvenanceError(
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
class Vlp32cDeviceIdentityReceiptCandidate:
    """Future manufacturer-grounded physical-device identity receipt.

    Validity means only that the candidate has the required provenance shape.
    It does not establish baseline nominality or any health state.
    """

    receipt_id: str
    acquisition_session_id: str
    split: BaselineNominalitySplit

    modality: str
    hardware_vendor: str
    hardware_model: str

    info_endpoint_path: str

    raw_info_json_sha256: str
    raw_info_json_byte_count: int
    capture_metadata_sha256: str

    parsed_model: str
    parsed_serial: str
    top_firmware_version: str
    bottom_firmware_version: str

    host_clock_id: str
    host_capture_start_ns: int
    host_capture_end_ns: int

    raw_info_bytes_preserved: bool
    serial_unique_factory_assigned_semantics_bound: bool
    serial_not_user_changeable_semantics_bound: bool
    active_mac_used_as_primary_identity: bool
    network_address_used_as_primary_identity: bool
    host_times_transport_provenance_only: bool

    baseline_nominality_claimed: bool = False
    source_acceptance_claimed: bool = False
    health_label_claimed: bool = False

    def __post_init__(
        self,
    ) -> None:
        for name in (
            "receipt_id",
            "acquisition_session_id",
            "modality",
            "hardware_vendor",
            "hardware_model",
            "info_endpoint_path",
            "parsed_model",
            "parsed_serial",
            "top_firmware_version",
            "bottom_firmware_version",
            "host_clock_id",
        ):
            _text(
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
            raise AcquisitionSessionProvenanceError(
                "split must be BaselineNominalitySplit"
            )

        if self.modality != EXPECTED_MODALITY:
            raise AcquisitionSessionProvenanceError(
                "session identity receipt is LiDAR-only"
            )

        if self.hardware_vendor != EXPECTED_VENDOR:
            raise AcquisitionSessionProvenanceError(
                "unexpected hardware vendor"
            )

        if self.hardware_model != EXPECTED_MODEL:
            raise AcquisitionSessionProvenanceError(
                "unexpected hardware model"
            )

        if self.parsed_model != EXPECTED_MODEL:
            raise AcquisitionSessionProvenanceError(
                "parsed model must be VLP-32C"
            )

        if self.info_endpoint_path != EXPECTED_INFO_PATH:
            raise AcquisitionSessionProvenanceError(
                "device identity source must be /cgi/info.json"
            )

        _digest(
            self.raw_info_json_sha256,
            name="raw_info_json_sha256",
        )

        _digest(
            self.capture_metadata_sha256,
            name="capture_metadata_sha256",
        )

        _exact_int(
            self.raw_info_json_byte_count,
            name="raw_info_json_byte_count",
            minimum=1,
        )

        start = _exact_int(
            self.host_capture_start_ns,
            name="host_capture_start_ns",
            minimum=0,
        )

        end = _exact_int(
            self.host_capture_end_ns,
            name="host_capture_end_ns",
            minimum=0,
        )

        if end < start:
            raise AcquisitionSessionProvenanceError(
                "host_capture_end_ns must be >= host_capture_start_ns"
            )

        for name in (
            "raw_info_bytes_preserved",
            "serial_unique_factory_assigned_semantics_bound",
            "serial_not_user_changeable_semantics_bound",
            "active_mac_used_as_primary_identity",
            "network_address_used_as_primary_identity",
            "host_times_transport_provenance_only",
            "baseline_nominality_claimed",
            "source_acceptance_claimed",
            "health_label_claimed",
        ):
            _exact_bool(
                getattr(
                    self,
                    name,
                ),
                name=name,
            )

        for name in (
            "raw_info_bytes_preserved",
            "serial_unique_factory_assigned_semantics_bound",
            "serial_not_user_changeable_semantics_bound",
            "host_times_transport_provenance_only",
        ):
            if getattr(
                self,
                name,
            ) is not True:
                raise AcquisitionSessionProvenanceError(
                    f"{name} must be true"
                )

        for name in (
            "active_mac_used_as_primary_identity",
            "network_address_used_as_primary_identity",
            "baseline_nominality_claimed",
            "source_acceptance_claimed",
            "health_label_claimed",
        ):
            if getattr(
                self,
                name,
            ) is not False:
                raise AcquisitionSessionProvenanceError(
                    f"{name} must be false"
                )

    def to_dict(
        self,
    ) -> dict[str, object]:
        return {
            "schema":
                SESSION_PROVENANCE_SCHEMA,

            "protocol_id":
                SESSION_PROVENANCE_PROTOCOL_ID,

            "receipt_id":
                self.receipt_id,

            "acquisition_session_id":
                self.acquisition_session_id,

            "split":
                self.split.value,

            "modality":
                self.modality,

            "hardware_vendor":
                self.hardware_vendor,

            "hardware_model":
                self.hardware_model,

            "info_endpoint_path":
                self.info_endpoint_path,

            "raw_info_json_sha256":
                self.raw_info_json_sha256,

            "raw_info_json_byte_count":
                self.raw_info_json_byte_count,

            "capture_metadata_sha256":
                self.capture_metadata_sha256,

            "parsed_model":
                self.parsed_model,

            "parsed_serial":
                self.parsed_serial,

            "top_firmware_version":
                self.top_firmware_version,

            "bottom_firmware_version":
                self.bottom_firmware_version,

            "host_clock_id":
                self.host_clock_id,

            "host_capture_start_ns":
                self.host_capture_start_ns,

            "host_capture_end_ns":
                self.host_capture_end_ns,

            "raw_info_bytes_preserved":
                True,

            "primary_physical_device_identity_field":
                "serial",

            "serial_unique_factory_assigned_semantics_bound":
                True,

            "serial_not_user_changeable_semantics_bound":
                True,

            "active_mac_used_as_primary_identity":
                False,

            "network_address_used_as_primary_identity":
                False,

            "firmware_versions_are_runtime_context_only":
                True,

            "host_times_transport_provenance_only":
                True,

            "baseline_nominality_claimed":
                False,

            "source_acceptance_claimed":
                False,

            "health_label_claimed":
                False,
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


@dataclass(frozen=True)
class NoInterventionDeclarationCandidate:
    """Prospective procedural declaration for the future baseline session.

    This declaration is not physical sensor health truth and cannot establish
    baseline nominality by itself.
    """

    declaration_id: str
    acquisition_session_id: str
    split: BaselineNominalitySplit

    declaration_artifact_sha256: str

    baseline_condition: str

    deliberate_availability_intervention_applied: bool
    prospective_before_controlled_intervention_phase: bool

    declaration_is_physical_sensor_health_truth: bool
    declaration_alone_establishes_baseline_nominality: bool

    reference_data_used: bool
    confirmation_test_data_used: bool

    def __post_init__(
        self,
    ) -> None:
        _text(
            self.declaration_id,
            name="declaration_id",
        )

        _text(
            self.acquisition_session_id,
            name="acquisition_session_id",
        )

        if not isinstance(
            self.split,
            BaselineNominalitySplit,
        ):
            raise AcquisitionSessionProvenanceError(
                "split must be BaselineNominalitySplit"
            )

        _digest(
            self.declaration_artifact_sha256,
            name="declaration_artifact_sha256",
        )

        _text(
            self.baseline_condition,
            name="baseline_condition",
        )

        if (
            self.baseline_condition
            != EXPECTED_BASELINE_CONDITION
        ):
            raise AcquisitionSessionProvenanceError(
                "baseline_condition must be full"
            )

        for name in (
            "deliberate_availability_intervention_applied",
            "prospective_before_controlled_intervention_phase",
            "declaration_is_physical_sensor_health_truth",
            "declaration_alone_establishes_baseline_nominality",
            "reference_data_used",
            "confirmation_test_data_used",
        ):
            _exact_bool(
                getattr(
                    self,
                    name,
                ),
                name=name,
            )

        if self.deliberate_availability_intervention_applied:
            raise AcquisitionSessionProvenanceError(
                "baseline declaration cannot contain a deliberate "
                "availability intervention"
            )

        if (
            self.prospective_before_controlled_intervention_phase
            is not True
        ):
            raise AcquisitionSessionProvenanceError(
                "declaration must be prospective"
            )

        for name in (
            "declaration_is_physical_sensor_health_truth",
            "declaration_alone_establishes_baseline_nominality",
            "reference_data_used",
            "confirmation_test_data_used",
        ):
            if getattr(
                self,
                name,
            ):
                raise AcquisitionSessionProvenanceError(
                    f"{name} must be false"
                )

    def to_dict(
        self,
    ) -> dict[str, object]:
        return {
            "schema":
                SESSION_PROVENANCE_SCHEMA,

            "protocol_id":
                SESSION_PROVENANCE_PROTOCOL_ID,

            "declaration_id":
                self.declaration_id,

            "acquisition_session_id":
                self.acquisition_session_id,

            "split":
                self.split.value,

            "declaration_artifact_sha256":
                self.declaration_artifact_sha256,

            "baseline_condition":
                self.baseline_condition,

            "deliberate_availability_intervention_applied":
                False,

            "prospective_before_controlled_intervention_phase":
                True,

            "declaration_is_physical_sensor_health_truth":
                False,

            "declaration_alone_establishes_baseline_nominality":
                False,

            "reference_data_used":
                False,

            "confirmation_test_data_used":
                False,

            "source_accepted":
                False,

            "health_label_assigned":
                False,
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


def build_session_provenance_bundle(
    identity: Vlp32cDeviceIdentityReceiptCandidate,
    declaration: NoInterventionDeclarationCandidate,
) -> dict[str, object]:
    if not isinstance(
        identity,
        Vlp32cDeviceIdentityReceiptCandidate,
    ):
        raise AcquisitionSessionProvenanceError(
            "identity must be Vlp32cDeviceIdentityReceiptCandidate"
        )

    if not isinstance(
        declaration,
        NoInterventionDeclarationCandidate,
    ):
        raise AcquisitionSessionProvenanceError(
            "declaration must be NoInterventionDeclarationCandidate"
        )

    if (
        identity.acquisition_session_id
        != declaration.acquisition_session_id
    ):
        raise AcquisitionSessionProvenanceError(
            "identity and declaration must share acquisition_session_id"
        )

    if identity.split is not declaration.split:
        raise AcquisitionSessionProvenanceError(
            "identity and declaration must share split"
        )

    payload: dict[str, object] = {
        "schema":
            SESSION_PROVENANCE_SCHEMA,

        "protocol_id":
            SESSION_PROVENANCE_PROTOCOL_ID,

        "acquisition_session_id":
            identity.acquisition_session_id,

        "split":
            identity.split.value,

        "device_identity":
            identity.to_dict(),

        "no_intervention_declaration":
            declaration.to_dict(),

        "session_provenance_candidate_complete":
            True,

        "scientific_nonclaims": {
            "physical_measurement_interval_binding_established":
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


def build_empty_session_provenance_registry_manifest(
) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema":
            SESSION_PROVENANCE_SCHEMA,

        "protocol_id":
            SESSION_PROVENANCE_PROTOCOL_ID,

        "primary_device_identity_field":
            "serial",

        "identity_observation_interface":
            EXPECTED_INFO_PATH,

        "device_identity_receipt_count":
            0,

        "no_intervention_declaration_count":
            0,

        "session_provenance_bundle_count":
            0,

        "accepted_baseline_nominality_source_count":
            0,

        "accepted_health_supervision_source_count":
            0,

        "real_health_label_count":
            0,

        "live_sensor_probe_authorized":
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
