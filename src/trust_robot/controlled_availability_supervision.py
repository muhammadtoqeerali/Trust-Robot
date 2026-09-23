from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json
import re

from .health_semantics import HealthState


CONTROLLED_AVAILABILITY_SCHEMA = (
    "TRUST_ROBOT_PHASE5_CONTROLLED_AVAILABILITY_SUPERVISION_V1"
)

CONTROLLED_AVAILABILITY_PROTOCOL_ID = (
    "trust_robot_phase5_controlled_measurement_availability_supervision_v1"
)

FROZEN_FRONTEND_MINIMUM_POINT_COUNT = 3

_SHA256_RE = re.compile(
    r"^[0-9a-f]{64}$"
)


class ControlledAvailabilityError(ValueError):
    """Raised when controlled availability provenance violates the protocol."""


class ControlledAvailabilityCondition(str, Enum):
    FULL = "full"
    PARTIAL = "partial"
    ABSENT = "absent"


class MeasurementEvidenceRelation(str, Enum):
    IDENTICAL = "identical"
    STRICT_PROPER_SUBSET = "strict_proper_subset"
    NONE = "none"


class ControlledAvailabilitySplit(str, Enum):
    TRAIN = "train"
    VALIDATION = "validation"


_STATE_BY_CONDITION = {
    ControlledAvailabilityCondition.FULL:
        HealthState.HEALTHY,

    ControlledAvailabilityCondition.PARTIAL:
        HealthState.DEGRADED,

    ControlledAvailabilityCondition.ABSENT:
        HealthState.UNUSABLE,
}


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
        raise ControlledAvailabilityError(
            f"{name} must be a non-empty string"
        )

    return value


def _require_sha256(
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
        raise ControlledAvailabilityError(
            f"{name} must be a lowercase SHA-256 hex digest"
        )

    return value


def _require_exact_bool(
    value: object,
    *,
    name: str,
) -> bool:
    if type(value) is not bool:
        raise ControlledAvailabilityError(
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
        raise ControlledAvailabilityError(
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
class ControlledAvailabilityReceipt:
    """Prospective controlled-supervision receipt.

    Construction validates experimental provenance only. It does not accept
    the supervision source for TRUST-ROBOT and does not label any real record.
    """

    receipt_id: str
    source_measurement_id: str
    interval_provenance_id: str
    modality: str

    split: ControlledAvailabilitySplit
    condition: ControlledAvailabilityCondition
    evidence_relation: MeasurementEvidenceRelation

    source_point_count: int
    retained_point_count: int | None

    source_measurement_sha256: str
    retained_measurement_sha256: str | None

    baseline_nominality_receipt_sha256: str
    intervention_execution_receipt_sha256: str
    relation_verification_receipt_sha256: str

    baseline_nominality_verified: bool
    intervention_execution_verified: bool
    relation_verified: bool

    independent_of_phase4_features: bool
    independent_of_final_estimator_scoring: bool
    independent_of_confirmation_test: bool

    zero_vector_substitution_used: bool = False

    def __post_init__(
        self,
    ) -> None:
        for name in (
            "receipt_id",
            "source_measurement_id",
            "interval_provenance_id",
            "modality",
        ):
            _require_text(
                getattr(
                    self,
                    name,
                ),
                name=name,
            )

        if self.modality != "lidar":
            raise ControlledAvailabilityError(
                "current controlled-availability protocol is LiDAR-only"
            )

        if not isinstance(
            self.split,
            ControlledAvailabilitySplit,
        ):
            raise ControlledAvailabilityError(
                "split must be ControlledAvailabilitySplit"
            )

        if not isinstance(
            self.condition,
            ControlledAvailabilityCondition,
        ):
            raise ControlledAvailabilityError(
                "condition must be ControlledAvailabilityCondition"
            )

        if not isinstance(
            self.evidence_relation,
            MeasurementEvidenceRelation,
        ):
            raise ControlledAvailabilityError(
                "evidence_relation must be MeasurementEvidenceRelation"
            )

        source_count = _require_exact_int(
            self.source_point_count,
            name="source_point_count",
            minimum=FROZEN_FRONTEND_MINIMUM_POINT_COUNT,
        )

        _require_sha256(
            self.source_measurement_sha256,
            name="source_measurement_sha256",
        )

        _require_sha256(
            self.baseline_nominality_receipt_sha256,
            name="baseline_nominality_receipt_sha256",
        )

        _require_sha256(
            self.intervention_execution_receipt_sha256,
            name="intervention_execution_receipt_sha256",
        )

        _require_sha256(
            self.relation_verification_receipt_sha256,
            name="relation_verification_receipt_sha256",
        )

        for name in (
            "baseline_nominality_verified",
            "intervention_execution_verified",
            "relation_verified",
            "independent_of_phase4_features",
            "independent_of_final_estimator_scoring",
            "independent_of_confirmation_test",
            "zero_vector_substitution_used",
        ):
            _require_exact_bool(
                getattr(
                    self,
                    name,
                ),
                name=name,
            )

        if self.baseline_nominality_verified is not True:
            raise ControlledAvailabilityError(
                "independent baseline nominality must be verified"
            )

        if self.intervention_execution_verified is not True:
            raise ControlledAvailabilityError(
                "intervention/control execution must be independently verified"
            )

        if self.relation_verified is not True:
            raise ControlledAvailabilityError(
                "measurement-evidence relation must be independently verified"
            )

        if self.independent_of_phase4_features is not True:
            raise ControlledAvailabilityError(
                "controlled condition cannot be defined from Phase-4 features"
            )

        if self.independent_of_final_estimator_scoring is not True:
            raise ControlledAvailabilityError(
                "controlled condition must be independent of final estimator scoring"
            )

        if self.independent_of_confirmation_test is not True:
            raise ControlledAvailabilityError(
                "controlled condition must be independent of confirmation-test data"
            )

        if self.zero_vector_substitution_used:
            raise ControlledAvailabilityError(
                "missing measurement must not be represented as a zero "
                "Phase-4 feature vector"
            )

        if self.condition is ControlledAvailabilityCondition.FULL:
            if self.evidence_relation is not MeasurementEvidenceRelation.IDENTICAL:
                raise ControlledAvailabilityError(
                    "FULL condition requires IDENTICAL evidence relation"
                )

            retained_count = _require_exact_int(
                self.retained_point_count,
                name="retained_point_count",
                minimum=FROZEN_FRONTEND_MINIMUM_POINT_COUNT,
            )

            if retained_count != source_count:
                raise ControlledAvailabilityError(
                    "FULL condition must retain the complete source point set"
                )

            retained_sha = _require_sha256(
                self.retained_measurement_sha256,
                name="retained_measurement_sha256",
            )

            if retained_sha != self.source_measurement_sha256:
                raise ControlledAvailabilityError(
                    "FULL condition must preserve the exact measurement object"
                )

        elif self.condition is ControlledAvailabilityCondition.PARTIAL:
            if (
                self.evidence_relation
                is not MeasurementEvidenceRelation.STRICT_PROPER_SUBSET
            ):
                raise ControlledAvailabilityError(
                    "PARTIAL condition requires STRICT_PROPER_SUBSET relation"
                )

            retained_count = _require_exact_int(
                self.retained_point_count,
                name="retained_point_count",
                minimum=FROZEN_FRONTEND_MINIMUM_POINT_COUNT,
            )

            if retained_count >= source_count:
                raise ControlledAvailabilityError(
                    "PARTIAL condition must retain a strict proper subset"
                )

            retained_sha = _require_sha256(
                self.retained_measurement_sha256,
                name="retained_measurement_sha256",
            )

            if retained_sha == self.source_measurement_sha256:
                raise ControlledAvailabilityError(
                    "PARTIAL retained measurement cannot equal source digest"
                )

        else:
            if self.evidence_relation is not MeasurementEvidenceRelation.NONE:
                raise ControlledAvailabilityError(
                    "ABSENT condition requires NONE evidence relation"
                )

            if self.retained_point_count is not None:
                raise ControlledAvailabilityError(
                    "ABSENT condition must have retained_point_count=None"
                )

            if self.retained_measurement_sha256 is not None:
                raise ControlledAvailabilityError(
                    "ABSENT condition must have no retained measurement digest"
                )

    def to_dict(
        self,
    ) -> dict[str, object]:
        return {
            "schema":
                CONTROLLED_AVAILABILITY_SCHEMA,

            "protocol_id":
                CONTROLLED_AVAILABILITY_PROTOCOL_ID,

            "receipt_id":
                self.receipt_id,

            "source_measurement_id":
                self.source_measurement_id,

            "interval_provenance_id":
                self.interval_provenance_id,

            "modality":
                self.modality,

            "split":
                self.split.value,

            "condition":
                self.condition.value,

            "prospective_health_state":
                _STATE_BY_CONDITION[
                    self.condition
                ].value,

            "evidence_relation":
                self.evidence_relation.value,

            "source_point_count":
                self.source_point_count,

            "retained_point_count":
                self.retained_point_count,

            "source_measurement_sha256":
                self.source_measurement_sha256,

            "retained_measurement_sha256":
                self.retained_measurement_sha256,

            "baseline_nominality_receipt_sha256":
                self.baseline_nominality_receipt_sha256,

            "intervention_execution_receipt_sha256":
                self.intervention_execution_receipt_sha256,

            "relation_verification_receipt_sha256":
                self.relation_verification_receipt_sha256,

            "baseline_nominality_verified":
                self.baseline_nominality_verified,

            "intervention_execution_verified":
                self.intervention_execution_verified,

            "relation_verified":
                self.relation_verified,

            "independent_of_phase4_features":
                self.independent_of_phase4_features,

            "independent_of_final_estimator_scoring":
                self.independent_of_final_estimator_scoring,

            "independent_of_confirmation_test":
                self.independent_of_confirmation_test,

            "zero_vector_substitution_used":
                self.zero_vector_substitution_used,

            "source_accepted":
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


def prospective_health_state_for_receipt(
    receipt: ControlledAvailabilityReceipt,
) -> HealthState:
    """Return the prospectively declared state for a valid receipt.

    This function does not accept a supervision source and must not be used
    as a runtime classifier.
    """

    if not isinstance(
        receipt,
        ControlledAvailabilityReceipt,
    ):
        raise ControlledAvailabilityError(
            "receipt must be ControlledAvailabilityReceipt"
        )

    return _STATE_BY_CONDITION[
        receipt.condition
    ]


def build_empty_controlled_availability_registry_manifest(
) -> dict[str, object]:
    """Return protocol state before any controlled source is accepted."""

    payload: dict[str, object] = {
        "schema":
            CONTROLLED_AVAILABILITY_SCHEMA,

        "protocol_id":
            CONTROLLED_AVAILABILITY_PROTOCOL_ID,

        "state_mapping": {
            ControlledAvailabilityCondition.FULL.value:
                HealthState.HEALTHY.value,

            ControlledAvailabilityCondition.PARTIAL.value:
                HealthState.DEGRADED.value,

            ControlledAvailabilityCondition.ABSENT.value:
                HealthState.UNUSABLE.value,
        },

        "baseline_nominality": {
            "independent_receipt_required":
                True,

            "clean_identity_alone_sufficient":
                False,
        },

        "structural_boundary": {
            "minimum_point_count":
                FROZEN_FRONTEND_MINIMUM_POINT_COUNT,

            "minimum_point_count_is_health_threshold":
                False,

            "missing_measurement_zero_vector_permitted":
                False,
        },

        "selection_status": {
            "baseline_nominality_source_selected":
                False,

            "specific_partial_intervention_selected":
                False,

            "specific_absence_intervention_selected":
                False,

            "numeric_severity_selected":
                False,
        },

        "registry": {
            "accepted_source_count":
                0,

            "accepted_source_ids":
                [],

            "real_health_label_count":
                0,

            "real_dataset_health_labels_assigned":
                False,
        },

        "classifier_status": {
            "classifier_selected":
                False,

            "health_threshold_selected":
                False,

            "model_trained":
                False,

            "calibration_performed":
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
