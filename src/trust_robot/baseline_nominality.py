from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json
import re


BASELINE_NOMINALITY_SCHEMA = (
    "TRUST_ROBOT_PHASE5_BASELINE_NOMINALITY_CANDIDATE_V1"
)

BASELINE_NOMINALITY_PROTOCOL_ID = (
    "trust_robot_phase5_vlp32c_interval_bound_baseline_nominality_v1"
)

EXPECTED_MODALITY = "lidar"
EXPECTED_VENDOR = "Velodyne"
EXPECTED_MODEL = "VLP-32C"

EXPECTED_MOTOR_STATE = "ON"
EXPECTED_LASER_STATE = "ON"
EXPECTED_THERMAL_STATUS = "Ok"

_SHA256_RE = re.compile(
    r"^[0-9a-f]{64}$"
)


class BaselineNominalityError(ValueError):
    """Raised when nominality candidate provenance violates the protocol."""


class BaselineNominalitySplit(str, Enum):
    TRAIN = "train"
    VALIDATION = "validation"


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
        raise BaselineNominalityError(
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
        raise BaselineNominalityError(
            f"{name} must be a lowercase SHA-256 digest"
        )

    return value


def _exact_bool(
    value: object,
    *,
    name: str,
) -> bool:
    if type(value) is not bool:
        raise BaselineNominalityError(
            f"{name} must be an exact bool"
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
class Vlp32cBaselineNominalityCandidate:
    """Candidate interval-bound nominality evidence.

    A valid object means only that the prospective evidence shape satisfies
    this protocol. Construction does not accept a supervision source and does
    not assign a health state to any real record.
    """

    candidate_id: str
    acquisition_session_id: str
    measurement_interval_id: str
    source_measurement_id: str

    split: BaselineNominalitySplit

    modality: str
    hardware_vendor: str
    hardware_model: str

    source_measurement_sha256: str
    raw_operational_status_sha256: str
    interval_binding_receipt_sha256: str
    no_intervention_receipt_sha256: str

    motor_state: str
    laser_state: str
    thermal_status: str

    operational_status_observed: bool
    operational_status_interval_bound: bool
    interval_binding_semantics_explicit: bool
    no_deliberate_availability_intervention_verified: bool
    manufacturer_semantics_bound: bool
    prospective: bool

    independent_of_phase4_features: bool
    independent_of_final_estimator_scoring: bool
    independent_of_reference_trajectory: bool
    independent_of_confirmation_test: bool

    timing_tolerance_selected: bool = False
    timing_offset_selected: bool = False
    interpolation_selected: bool = False

    def __post_init__(
        self,
    ) -> None:
        for name in (
            "candidate_id",
            "acquisition_session_id",
            "measurement_interval_id",
            "source_measurement_id",
            "modality",
            "hardware_vendor",
            "hardware_model",
            "motor_state",
            "laser_state",
            "thermal_status",
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
            raise BaselineNominalityError(
                "split must be BaselineNominalitySplit"
            )

        if self.modality != EXPECTED_MODALITY:
            raise BaselineNominalityError(
                "baseline nominality candidate is LiDAR-only"
            )

        if self.hardware_vendor != EXPECTED_VENDOR:
            raise BaselineNominalityError(
                "unexpected hardware vendor"
            )

        if self.hardware_model != EXPECTED_MODEL:
            raise BaselineNominalityError(
                "unexpected hardware model"
            )

        for name in (
            "source_measurement_sha256",
            "raw_operational_status_sha256",
            "interval_binding_receipt_sha256",
            "no_intervention_receipt_sha256",
        ):
            _digest(
                getattr(
                    self,
                    name,
                ),
                name=name,
            )

        for name in (
            "operational_status_observed",
            "operational_status_interval_bound",
            "interval_binding_semantics_explicit",
            "no_deliberate_availability_intervention_verified",
            "manufacturer_semantics_bound",
            "prospective",
            "independent_of_phase4_features",
            "independent_of_final_estimator_scoring",
            "independent_of_reference_trajectory",
            "independent_of_confirmation_test",
            "timing_tolerance_selected",
            "timing_offset_selected",
            "interpolation_selected",
        ):
            _exact_bool(
                getattr(
                    self,
                    name,
                ),
                name=name,
            )

        if self.motor_state != EXPECTED_MOTOR_STATE:
            raise BaselineNominalityError(
                "candidate requires manufacturer Motor State=ON"
            )

        if self.laser_state != EXPECTED_LASER_STATE:
            raise BaselineNominalityError(
                "candidate requires manufacturer Laser State=ON"
            )

        if self.thermal_status != EXPECTED_THERMAL_STATUS:
            raise BaselineNominalityError(
                "candidate requires manufacturer Thermal Status=Ok"
            )

        for name in (
            "operational_status_observed",
            "operational_status_interval_bound",
            "interval_binding_semantics_explicit",
            "no_deliberate_availability_intervention_verified",
            "manufacturer_semantics_bound",
            "prospective",
            "independent_of_phase4_features",
            "independent_of_final_estimator_scoring",
            "independent_of_reference_trajectory",
            "independent_of_confirmation_test",
        ):
            if getattr(
                self,
                name,
            ) is not True:
                raise BaselineNominalityError(
                    f"{name} must be true"
                )

        if self.timing_tolerance_selected:
            raise BaselineNominalityError(
                "this protocol does not select a timing tolerance"
            )

        if self.timing_offset_selected:
            raise BaselineNominalityError(
                "this protocol does not select a timing offset"
            )

        if self.interpolation_selected:
            raise BaselineNominalityError(
                "this protocol does not select interpolation"
            )

    def to_dict(
        self,
    ) -> dict[str, object]:
        return {
            "schema":
                BASELINE_NOMINALITY_SCHEMA,

            "protocol_id":
                BASELINE_NOMINALITY_PROTOCOL_ID,

            "candidate_id":
                self.candidate_id,

            "acquisition_session_id":
                self.acquisition_session_id,

            "measurement_interval_id":
                self.measurement_interval_id,

            "source_measurement_id":
                self.source_measurement_id,

            "split":
                self.split.value,

            "modality":
                self.modality,

            "hardware_vendor":
                self.hardware_vendor,

            "hardware_model":
                self.hardware_model,

            "source_measurement_sha256":
                self.source_measurement_sha256,

            "raw_operational_status_sha256":
                self.raw_operational_status_sha256,

            "interval_binding_receipt_sha256":
                self.interval_binding_receipt_sha256,

            "no_intervention_receipt_sha256":
                self.no_intervention_receipt_sha256,

            "motor_state":
                self.motor_state,

            "laser_state":
                self.laser_state,

            "thermal_status":
                self.thermal_status,

            "operational_status_observed":
                self.operational_status_observed,

            "operational_status_interval_bound":
                self.operational_status_interval_bound,

            "interval_binding_semantics_explicit":
                self.interval_binding_semantics_explicit,

            "no_deliberate_availability_intervention_verified":
                self.no_deliberate_availability_intervention_verified,

            "manufacturer_semantics_bound":
                self.manufacturer_semantics_bound,

            "prospective":
                self.prospective,

            "independent_of_phase4_features":
                self.independent_of_phase4_features,

            "independent_of_final_estimator_scoring":
                self.independent_of_final_estimator_scoring,

            "independent_of_reference_trajectory":
                self.independent_of_reference_trajectory,

            "independent_of_confirmation_test":
                self.independent_of_confirmation_test,

            "timing_tolerance_selected":
                self.timing_tolerance_selected,

            "timing_offset_selected":
                self.timing_offset_selected,

            "interpolation_selected":
                self.interpolation_selected,

            "candidate_shape_valid":
                True,

            "source_accepted":
                False,

            "healthy_label_assigned":
                False,

            "real_record_label_assignment":
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


def build_empty_baseline_nominality_registry_manifest(
) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema":
            BASELINE_NOMINALITY_SCHEMA,

        "protocol_id":
            BASELINE_NOMINALITY_PROTOCOL_ID,

        "required_operational_states": {
            "motor_state":
                EXPECTED_MOTOR_STATE,

            "laser_state":
                EXPECTED_LASER_STATE,

            "thermal_status":
                EXPECTED_THERMAL_STATUS,
        },

        "selection_status": {
            "prospective_acquisition_mechanism_selected":
                False,

            "interval_binding_mechanism_selected":
                False,

            "timing_tolerance_selected":
                False,

            "timing_offset_selected":
                False,

            "interpolation_selected":
                False,
        },

        "registry": {
            "candidate_count":
                0,

            "accepted_baseline_nominality_source_count":
                0,

            "accepted_baseline_nominality_source_ids":
                [],

            "accepted_health_supervision_source_count":
                0,

            "real_health_label_count":
                0,
        },

        "authorization": {
            "controlled_corruption_generation":
                False,

            "health_label_generation":
                False,

            "classifier_training":
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
