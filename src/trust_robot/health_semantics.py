from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from types import MappingProxyType
from typing import Mapping
import json


HEALTH_SEMANTIC_SCHEMA = (
    "TRUST_ROBOT_PHASE5_HEALTH_SEMANTICS_V1"
)

HEALTH_SEMANTIC_CONTRACT_ID = (
    "trust_robot_phase5_three_state_health_semantics_v1"
)


class HealthSemanticContractError(ValueError):
    """Raised when Phase-5 health-semantic provenance violates the contract."""


class HealthState(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNUSABLE = "unusable"


@dataclass(frozen=True)
class HealthStateDefinition:
    state: HealthState
    definition: str
    is_localization_accuracy_score: bool = False
    is_suppression_command: bool = False

    def __post_init__(self) -> None:
        if not isinstance(
            self.state,
            HealthState,
        ):
            raise HealthSemanticContractError(
                "state must be HealthState"
            )

        if (
            not isinstance(
                self.definition,
                str,
            )
            or not self.definition.strip()
        ):
            raise HealthSemanticContractError(
                "definition must be non-empty"
            )

        if self.is_localization_accuracy_score is not False:
            raise HealthSemanticContractError(
                "health state cannot be an accuracy score"
            )

        if self.is_suppression_command is not False:
            raise HealthSemanticContractError(
                "Phase-5 state cannot itself authorize suppression"
            )


HEALTH_STATE_DEFINITIONS: Mapping[
    HealthState,
    HealthStateDefinition,
] = MappingProxyType(
    {
        HealthState.HEALTHY:
            HealthStateDefinition(
                state=HealthState.HEALTHY,
                definition=(
                    "An accepted, prospectively declared health-label "
                    "provenance source identifies the modality as nominal "
                    "for its declared measurement role during the labeled "
                    "interval."
                ),
            ),

        HealthState.DEGRADED:
            HealthStateDefinition(
                state=HealthState.DEGRADED,
                definition=(
                    "An accepted, prospectively declared health-label "
                    "provenance source identifies a non-nominal impairment "
                    "of the modality's declared measurement role, without "
                    "identifying that role as unusable during the labeled "
                    "interval."
                ),
            ),

        HealthState.UNUSABLE:
            HealthStateDefinition(
                state=HealthState.UNUSABLE,
                definition=(
                    "An accepted, prospectively declared health-label "
                    "provenance source identifies the modality as unable "
                    "to provide measurement information suitable for its "
                    "declared measurement role during the labeled interval."
                ),
            ),
    }
)


def _require_exact_bool(
    value: object,
    *,
    name: str,
) -> bool:
    if type(
        value
    ) is not bool:
        raise HealthSemanticContractError(
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
class HealthLabelProvenance:
    """Candidate provenance shape; this object does not assign a health state."""

    source_id: str
    source_kind: str
    justification: str

    prospectively_declared: bool
    independent_of_final_estimator_scoring: bool
    independent_of_confirmation_test: bool

    derived_only_from_clean_identity: bool = False
    derived_only_from_corruption_identity: bool = False
    derived_only_from_diagnostic_value_or_threshold: bool = False

    def __post_init__(self) -> None:
        for name in (
            "source_id",
            "source_kind",
            "justification",
        ):
            value = getattr(
                self,
                name,
            )

            if (
                not isinstance(
                    value,
                    str,
                )
                or not value.strip()
            ):
                raise HealthSemanticContractError(
                    f"{name} must be a non-empty string"
                )

        for name in (
            "prospectively_declared",
            "independent_of_final_estimator_scoring",
            "independent_of_confirmation_test",
            "derived_only_from_clean_identity",
            "derived_only_from_corruption_identity",
            "derived_only_from_diagnostic_value_or_threshold",
        ):
            _require_exact_bool(
                getattr(
                    self,
                    name,
                ),
                name=name,
            )

        if self.prospectively_declared is not True:
            raise HealthSemanticContractError(
                "health-label provenance must be prospectively declared"
            )

        if self.independent_of_final_estimator_scoring is not True:
            raise HealthSemanticContractError(
                "health-label provenance must be independent of final "
                "estimator scoring"
            )

        if self.independent_of_confirmation_test is not True:
            raise HealthSemanticContractError(
                "health-label provenance must be independent of "
                "confirmation-test data"
            )

        if self.derived_only_from_clean_identity:
            raise HealthSemanticContractError(
                "clean-branch identity alone is not a health label"
            )

        if self.derived_only_from_corruption_identity:
            raise HealthSemanticContractError(
                "corruption identity alone is not a health label"
            )

        if self.derived_only_from_diagnostic_value_or_threshold:
            raise HealthSemanticContractError(
                "diagnostic value or threshold alone is not a health label"
            )

    def to_dict(
        self,
    ) -> dict[str, object]:
        return {
            "source_id":
                self.source_id,

            "source_kind":
                self.source_kind,

            "justification":
                self.justification,

            "prospectively_declared":
                self.prospectively_declared,

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


def validate_health_label_provenance_shape(
    provenance: HealthLabelProvenance,
) -> HealthLabelProvenance:
    """Validate provenance structure without assigning any health state."""

    if not isinstance(
        provenance,
        HealthLabelProvenance,
    ):
        raise HealthSemanticContractError(
            "provenance must be HealthLabelProvenance"
        )

    return provenance


def build_health_semantic_manifest() -> dict[str, object]:
    """Return deterministic state semantics with no classifier or data labels."""

    payload: dict[str, object] = {
        "schema":
            HEALTH_SEMANTIC_SCHEMA,

        "contract_id":
            HEALTH_SEMANTIC_CONTRACT_ID,

        "state_order": [
            state.value
            for state
            in (
                HealthState.HEALTHY,
                HealthState.DEGRADED,
                HealthState.UNUSABLE,
            )
        ],

        "states": {
            state.value: {
                "definition":
                    HEALTH_STATE_DEFINITIONS[
                        state
                    ].definition,

                "is_localization_accuracy_score":
                    False,

                "is_suppression_command":
                    False,
            }
            for state
            in (
                HealthState.HEALTHY,
                HealthState.DEGRADED,
                HealthState.UNUSABLE,
            )
        },

        "label_provenance_policy": {
            "explicit_provenance_required":
                True,

            "prospective_declaration_required":
                True,

            "final_estimator_scoring_independence_required":
                True,

            "confirmation_test_independence_required":
                True,

            "clean_identity_alone_sufficient":
                False,

            "corruption_identity_alone_sufficient":
                False,

            "diagnostic_value_or_threshold_alone_sufficient":
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

            "real_dataset_health_labels_assigned":
                False,
        },

        "scientific_scope": {
            "reference_data_used":
                False,

            "confirmation_test_data_used":
                False,

            "ate_computed":
                False,

            "rpe_computed":
                False,

            "estimator_scoring_performed":
                False,

            "suppression_authorized":
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
