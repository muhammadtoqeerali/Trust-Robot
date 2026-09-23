from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Tuple
import json

from .health_semantics import (
    HealthLabelProvenance,
    HealthState,
    validate_health_label_provenance_shape,
)


HEALTH_SUPERVISION_PROTOCOL_SCHEMA = (
    "TRUST_ROBOT_PHASE5_HEALTH_SUPERVISION_PROTOCOL_V1"
)

HEALTH_SUPERVISION_PROTOCOL_ID = (
    "trust_robot_phase5_health_supervision_source_protocol_v1"
)


class HealthSupervisionContractError(ValueError):
    """Raised when a proposed health-supervision source is inadmissible."""


def _require_nonempty_string(
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
        raise HealthSupervisionContractError(
            f"{name} must be a non-empty string"
        )

    return value


def _require_exact_bool(
    value: object,
    *,
    name: str,
) -> bool:
    if type(value) is not bool:
        raise HealthSupervisionContractError(
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
class HealthSupervisionSourceCandidate:
    """Prospective source declaration. Construction assigns no health label."""

    source_id: str
    modality: str
    measurement_role: str
    source_kind: str
    evidence_description: str
    protocol_version: str

    supported_states: Tuple[HealthState, ...]
    state_criteria: Tuple[Tuple[HealthState, str], ...]

    prospectively_declared: bool
    measurement_role_grounded: bool
    independent_of_final_estimator_scoring: bool
    independent_of_confirmation_test: bool

    derived_only_from_clean_identity: bool = False
    derived_only_from_corruption_identity: bool = False
    derived_only_from_diagnostic_value_or_threshold: bool = False

    uses_reference_trajectory_metric: bool = False
    uses_ate_or_rpe: bool = False
    historical_imu_reliability_policy_adopted: bool = False
    classifier_output_used_as_supervision: bool = False
    numeric_diagnostic_threshold_selected: bool = False

    def __post_init__(self) -> None:
        for name in (
            "source_id",
            "modality",
            "measurement_role",
            "source_kind",
            "evidence_description",
            "protocol_version",
        ):
            _require_nonempty_string(
                getattr(
                    self,
                    name,
                ),
                name=name,
            )

        for name in (
            "prospectively_declared",
            "measurement_role_grounded",
            "independent_of_final_estimator_scoring",
            "independent_of_confirmation_test",
            "derived_only_from_clean_identity",
            "derived_only_from_corruption_identity",
            "derived_only_from_diagnostic_value_or_threshold",
            "uses_reference_trajectory_metric",
            "uses_ate_or_rpe",
            "historical_imu_reliability_policy_adopted",
            "classifier_output_used_as_supervision",
            "numeric_diagnostic_threshold_selected",
        ):
            _require_exact_bool(
                getattr(
                    self,
                    name,
                ),
                name=name,
            )

        if not isinstance(
            self.supported_states,
            tuple,
        ):
            raise HealthSupervisionContractError(
                "supported_states must be a tuple"
            )

        if not self.supported_states:
            raise HealthSupervisionContractError(
                "supported_states must not be empty"
            )

        for state in self.supported_states:
            if not isinstance(
                state,
                HealthState,
            ):
                raise HealthSupervisionContractError(
                    "supported_states entries must be HealthState"
                )

        if len(
            set(
                self.supported_states
            )
        ) != len(
            self.supported_states
        ):
            raise HealthSupervisionContractError(
                "supported_states must not contain duplicates"
            )

        if not isinstance(
            self.state_criteria,
            tuple,
        ):
            raise HealthSupervisionContractError(
                "state_criteria must be a tuple"
            )

        criterion_states = []

        for item in self.state_criteria:
            if (
                not isinstance(
                    item,
                    tuple,
                )
                or len(item) != 2
            ):
                raise HealthSupervisionContractError(
                    "state_criteria entries must be (HealthState, text)"
                )

            state, criterion = item

            if not isinstance(
                state,
                HealthState,
            ):
                raise HealthSupervisionContractError(
                    "state criterion key must be HealthState"
                )

            _require_nonempty_string(
                criterion,
                name=(
                    f"criterion[{state.value}]"
                ),
            )

            criterion_states.append(
                state
            )

        if len(
            set(
                criterion_states
            )
        ) != len(
            criterion_states
        ):
            raise HealthSupervisionContractError(
                "state_criteria must not duplicate a state"
            )

        if set(
            criterion_states
        ) != set(
            self.supported_states
        ):
            raise HealthSupervisionContractError(
                "state_criteria states must exactly match supported_states"
            )

        if self.prospectively_declared is not True:
            raise HealthSupervisionContractError(
                "source must be prospectively declared"
            )

        if self.measurement_role_grounded is not True:
            raise HealthSupervisionContractError(
                "source evidence must be grounded in the modality's "
                "declared measurement role"
            )

        if self.independent_of_final_estimator_scoring is not True:
            raise HealthSupervisionContractError(
                "source must be independent of final estimator scoring"
            )

        if self.independent_of_confirmation_test is not True:
            raise HealthSupervisionContractError(
                "source must be independent of confirmation-test outcomes"
            )

        if self.derived_only_from_clean_identity:
            raise HealthSupervisionContractError(
                "clean identity alone is insufficient health supervision"
            )

        if self.derived_only_from_corruption_identity:
            raise HealthSupervisionContractError(
                "corruption identity alone is insufficient health supervision"
            )

        if self.derived_only_from_diagnostic_value_or_threshold:
            raise HealthSupervisionContractError(
                "diagnostic value or threshold alone is insufficient "
                "health supervision"
            )

        if self.uses_reference_trajectory_metric:
            raise HealthSupervisionContractError(
                "reference trajectory metrics are not permitted "
                "health-label supervision"
            )

        if self.uses_ate_or_rpe:
            raise HealthSupervisionContractError(
                "ATE/RPE are not permitted health-label supervision"
            )

        if self.historical_imu_reliability_policy_adopted:
            raise HealthSupervisionContractError(
                "historical imu_reliability policy is not adopted"
            )

        if self.classifier_output_used_as_supervision:
            raise HealthSupervisionContractError(
                "classifier output cannot serve as its own supervision"
            )

        if self.numeric_diagnostic_threshold_selected:
            raise HealthSupervisionContractError(
                "candidate source declaration cannot select a numeric "
                "diagnostic threshold"
            )

    def to_dict(
        self,
    ) -> dict[str, object]:
        return {
            "source_id":
                self.source_id,

            "modality":
                self.modality,

            "measurement_role":
                self.measurement_role,

            "source_kind":
                self.source_kind,

            "evidence_description":
                self.evidence_description,

            "protocol_version":
                self.protocol_version,

            "supported_states": [
                state.value
                for state
                in self.supported_states
            ],

            "state_criteria": [
                {
                    "state":
                        state.value,

                    "criterion":
                        criterion,
                }
                for state, criterion
                in self.state_criteria
            ],

            "prospectively_declared":
                self.prospectively_declared,

            "measurement_role_grounded":
                self.measurement_role_grounded,

            "independent_of_final_estimator_scoring":
                self.independent_of_final_estimator_scoring,

            "independent_of_confirmation_test":
                self.independent_of_confirmation_test,

            "derived_only_from_clean_identity":
                self.derived_only_from_clean_identity,

            "derived_only_from_corruption_identity":
                self.derived_only_from_corruption_identity,

            "derived_only_from_diagnostic_value_or_threshold":
                self.derived_only_from_diagnostic_value_or_threshold,

            "uses_reference_trajectory_metric":
                self.uses_reference_trajectory_metric,

            "uses_ate_or_rpe":
                self.uses_ate_or_rpe,

            "historical_imu_reliability_policy_adopted":
                self.historical_imu_reliability_policy_adopted,

            "classifier_output_used_as_supervision":
                self.classifier_output_used_as_supervision,

            "numeric_diagnostic_threshold_selected":
                self.numeric_diagnostic_threshold_selected,
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

    def to_provenance_shape(
        self,
    ) -> HealthLabelProvenance:
        provenance = HealthLabelProvenance(
            source_id=self.source_id,
            source_kind=self.source_kind,
            justification=self.evidence_description,
            prospectively_declared=self.prospectively_declared,
            independent_of_final_estimator_scoring=(
                self.independent_of_final_estimator_scoring
            ),
            independent_of_confirmation_test=(
                self.independent_of_confirmation_test
            ),
            derived_only_from_clean_identity=(
                self.derived_only_from_clean_identity
            ),
            derived_only_from_corruption_identity=(
                self.derived_only_from_corruption_identity
            ),
            derived_only_from_diagnostic_value_or_threshold=(
                self.derived_only_from_diagnostic_value_or_threshold
            ),
        )

        return validate_health_label_provenance_shape(
            provenance
        )


def validate_health_supervision_source_candidate(
    source: HealthSupervisionSourceCandidate,
) -> HealthSupervisionSourceCandidate:
    """Validate a candidate source declaration without accepting it."""

    if not isinstance(
        source,
        HealthSupervisionSourceCandidate,
    ):
        raise HealthSupervisionContractError(
            "source must be HealthSupervisionSourceCandidate"
        )

    source.to_provenance_shape()

    return source


def build_empty_health_supervision_registry_manifest() -> dict[str, object]:
    """Return the prospective protocol state before any source is accepted."""

    payload: dict[str, object] = {
        "schema":
            HEALTH_SUPERVISION_PROTOCOL_SCHEMA,

        "protocol_id":
            HEALTH_SUPERVISION_PROTOCOL_ID,

        "state_vocabulary": [
            HealthState.HEALTHY.value,
            HealthState.DEGRADED.value,
            HealthState.UNUSABLE.value,
        ],

        "source_requirements": {
            "prospectively_declared":
                True,

            "measurement_role_grounded":
                True,

            "independent_of_final_estimator_scoring":
                True,

            "independent_of_confirmation_test":
                True,

            "explicit_state_criteria":
                True,
        },

        "prohibited_label_basis": {
            "clean_identity_alone":
                True,

            "corruption_identity_alone":
                True,

            "diagnostic_value_or_threshold_alone":
                True,

            "reference_trajectory_metric":
                True,

            "ate_or_rpe":
                True,

            "historical_imu_reliability_policy":
                True,

            "classifier_output_as_own_supervision":
                True,
        },

        "registry": {
            "candidate_source_declared":
                False,

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
            "classifier_implemented":
                False,

            "classifier_selected":
                False,

            "threshold_selected":
                False,

            "model_trained":
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
