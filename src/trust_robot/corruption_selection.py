from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from hashlib import sha256
from types import MappingProxyType
from typing import Any, Mapping
import json

from .corruption import CorruptionSpec


SELECTION_SCHEMA = (
    "TRUST_ROBOT_PHASE3_CORRUPTION_SELECTION_RECORD_V1"
)


class CorruptionSelectionError(ValueError):
    """Raised when corruption-selection provenance is inadmissible."""


class TargetSelectionSource(str, Enum):
    EXPLICIT_PRE_EXECUTION_LITERAL = (
        "explicit_pre_execution_literal"
    )

    DETERMINISTIC_TRAIN_METADATA_RULE = (
        "deterministic_train_metadata_rule"
    )

    EXTERNAL_INDEPENDENT_SPECIFICATION = (
        "external_independent_specification"
    )


class MagnitudeSelectionSource(str, Enum):
    EXPLICIT_PRE_EXECUTION_LITERAL = (
        "explicit_pre_execution_literal"
    )

    EXTERNAL_INDEPENDENT_SPECIFICATION = (
        "external_independent_specification"
    )


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


def _mapping(
    value: Mapping[str, Any] | None,
) -> Mapping[str, Any]:
    copied = {
        str(
            key
        ):
            item
        for key, item
        in dict(
            value
            or {}
        ).items()
    }

    _canonical_json(
        copied
    )

    return MappingProxyType(
        copied
    )


def _text(
    value,
    *,
    name,
):
    result = str(
        value
    ).strip()

    if not result:
        raise CorruptionSelectionError(
            f"{name} cannot be empty"
        )

    return result


@dataclass(
    frozen=True,
)
class CorruptionSelectionRecord:
    plan_name: str

    target_selection_source: TargetSelectionSource
    target_selection_rationale: str

    magnitude_selection_source: MagnitudeSelectionSource
    magnitude_selection_rationale: str

    selection_locked_before_execution: bool = True

    estimator_output_used: bool = False
    registration_diagnostic_used: bool = False
    reference_data_used: bool = False
    ground_truth_metric_used: bool = False
    validation_metric_used: bool = False
    confirmation_test_used: bool = False

    source_artifacts: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "plan_name",
            _text(
                self.plan_name,
                name="plan_name",
            ),
        )

        object.__setattr__(
            self,
            "target_selection_source",
            TargetSelectionSource(
                self.target_selection_source
            ),
        )

        object.__setattr__(
            self,
            "magnitude_selection_source",
            MagnitudeSelectionSource(
                self.magnitude_selection_source
            ),
        )

        object.__setattr__(
            self,
            "target_selection_rationale",
            _text(
                self.target_selection_rationale,
                name="target_selection_rationale",
            ),
        )

        object.__setattr__(
            self,
            "magnitude_selection_rationale",
            _text(
                self.magnitude_selection_rationale,
                name="magnitude_selection_rationale",
            ),
        )

        if self.selection_locked_before_execution is not True:
            raise CorruptionSelectionError(
                "selection must be locked before execution"
            )

        forbidden_flags = {
            "estimator_output_used":
                self.estimator_output_used,

            "registration_diagnostic_used":
                self.registration_diagnostic_used,

            "reference_data_used":
                self.reference_data_used,

            "ground_truth_metric_used":
                self.ground_truth_metric_used,

            "validation_metric_used":
                self.validation_metric_used,

            "confirmation_test_used":
                self.confirmation_test_used,
        }

        enabled = [
            name
            for name, value
            in forbidden_flags.items()
            if value is not False
        ]

        if enabled:
            raise CorruptionSelectionError(
                "forbidden corruption-selection inputs were used: "
                + ", ".join(
                    enabled
                )
            )

        artifacts = tuple(
            _text(
                item,
                name="source_artifact",
            )
            for item
            in self.source_artifacts
        )

        object.__setattr__(
            self,
            "source_artifacts",
            artifacts,
        )

        object.__setattr__(
            self,
            "metadata",
            _mapping(
                self.metadata
            ),
        )

    def canonical_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "schema":
                SELECTION_SCHEMA,

            "plan_name":
                self.plan_name,

            "target_selection_source":
                self.target_selection_source.value,

            "target_selection_rationale":
                self.target_selection_rationale,

            "magnitude_selection_source":
                self.magnitude_selection_source.value,

            "magnitude_selection_rationale":
                self.magnitude_selection_rationale,

            "selection_locked_before_execution":
                self.selection_locked_before_execution,

            "estimator_output_used":
                self.estimator_output_used,

            "registration_diagnostic_used":
                self.registration_diagnostic_used,

            "reference_data_used":
                self.reference_data_used,

            "ground_truth_metric_used":
                self.ground_truth_metric_used,

            "validation_metric_used":
                self.validation_metric_used,

            "confirmation_test_used":
                self.confirmation_test_used,

            "source_artifacts":
                list(
                    self.source_artifacts
                ),

            "metadata":
                dict(
                    self.metadata
                ),
        }

    @property
    def selection_id(
        self,
    ) -> str:
        raw = _canonical_json(
            self.canonical_dict()
        ).encode(
            "utf-8"
        )

        return (
            "TRC_SEL_"
            + sha256(
                raw
            ).hexdigest()[
                :24
            ]
        )


def bind_spec_to_selection(
    spec: CorruptionSpec,
    selection: CorruptionSelectionRecord,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema":
            "TRUST_ROBOT_PHASE3_PROSPECTIVE_CORRUPTION_BINDING_V1",

        "spec_id":
            spec.spec_id,

        "spec":
            spec.canonical_dict(),

        "selection_id":
            selection.selection_id,

        "selection":
            selection.canonical_dict(),

        "execution_authorization": {
            "selection_locked_before_execution":
                True,

            "missing_parameter_default_allowed":
                False,

            "engine_parameter_selection_allowed":
                False,

            "output_driven_spec_modification_allowed":
                False,
        },

        "scientific_scope": {
            "estimator_output_used_for_selection":
                False,

            "registration_diagnostic_used_for_selection":
                False,

            "reference_data_used_for_selection":
                False,

            "ground_truth_metric_used_for_selection":
                False,

            "validation_metric_used_for_selection":
                False,

            "confirmation_test_used_for_selection":
                False,

            "ate_or_rpe_authorized":
                False,

            "estimator_scoring_authorized":
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
