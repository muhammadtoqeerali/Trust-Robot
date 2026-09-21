from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from .m2dgr_evaluation_plan import (
    validate_nonexecut_m2dgr_evaluation_plan,
)


class M2DGREvaluationReadinessError(
    ValueError
):
    """Raised when readiness diagnostics receive an invalid plan or field set."""


class M2DGREvaluationExecutionBlocked(
    RuntimeError
):
    """Raised when execution is requested from a non-executable plan."""


@dataclass(
    frozen=True,
)
class ProvenanceCompletenessReport:
    required_fields: tuple[str, ...]
    present_fields: tuple[str, ...]
    missing_fields: tuple[str, ...]
    unknown_fields: tuple[str, ...]
    schema_complete: bool
    semantic_validation_performed: bool

    def to_dict(
        self,
    ) -> dict[str, object]:
        return {
            "required_fields":
                list(
                    self.required_fields
                ),

            "present_fields":
                list(
                    self.present_fields
                ),

            "missing_fields":
                list(
                    self.missing_fields
                ),

            "unknown_fields":
                list(
                    self.unknown_fields
                ),

            "schema_complete":
                self.schema_complete,

            "semantic_validation_performed":
                self.semantic_validation_performed,
        }


@dataclass(
    frozen=True,
)
class ExecutionReadinessReport:
    status: str
    ready: bool
    association_execution_authorized: bool
    evaluation_interval_authorized: bool
    alignment_execution_authorized: bool
    metric_computation_authorized: bool
    trajectory_scoring_authorized: bool
    estimator_scoring_authorized: bool
    metric_entry_count: int
    executable_metric_entry_count: int
    scoreable_metric_entry_count: int
    global_blockers: tuple[str, ...]
    provenance_schema_complete: bool | None
    provenance_semantics_verified: bool

    def to_dict(
        self,
    ) -> dict[str, object]:
        return {
            "status":
                self.status,

            "ready":
                self.ready,

            "association_execution_authorized":
                self.association_execution_authorized,

            "evaluation_interval_authorized":
                self.evaluation_interval_authorized,

            "alignment_execution_authorized":
                self.alignment_execution_authorized,

            "metric_computation_authorized":
                self.metric_computation_authorized,

            "trajectory_scoring_authorized":
                self.trajectory_scoring_authorized,

            "estimator_scoring_authorized":
                self.estimator_scoring_authorized,

            "metric_entry_count":
                self.metric_entry_count,

            "executable_metric_entry_count":
                self.executable_metric_entry_count,

            "scoreable_metric_entry_count":
                self.scoreable_metric_entry_count,

            "global_blockers":
                list(
                    self.global_blockers
                ),

            "provenance_schema_complete":
                self.provenance_schema_complete,

            "provenance_semantics_verified":
                self.provenance_semantics_verified,
        }


def _normalized_field_names(
    fields: Iterable[str],
) -> tuple[str, ...]:
    result = set()

    for field in fields:
        if (
            not isinstance(
                field,
                str,
            )
            or not field.strip()
        ):
            raise M2DGREvaluationReadinessError(
                "provenance field names must be non-empty strings"
            )

        result.add(
            field
        )

    return tuple(
        sorted(
            result
        )
    )


def build_provenance_completeness_report(
    plan_payload: Mapping[str, object],
    *,
    present_fields: Iterable[str],
) -> ProvenanceCompletenessReport:
    """Report field-name completeness only.

    This function deliberately does not accept provenance values. It therefore
    cannot select an association method, alignment mode, timing value, frame
    transform, interval, or any other physical/evaluation parameter.
    """

    validate_nonexecut_m2dgr_evaluation_plan(
        plan_payload
    )

    provenance = plan_payload[
        "provenance"
    ]

    required = tuple(
        sorted(
            provenance[
                "required_per_evaluation_fields"
            ]
        )
    )

    present = _normalized_field_names(
        present_fields
    )

    required_set = set(
        required
    )

    present_set = set(
        present
    )

    missing = tuple(
        sorted(
            required_set
            - present_set
        )
    )

    unknown = tuple(
        sorted(
            present_set
            - required_set
        )
    )

    schema_complete = (
        not missing
        and not unknown
    )

    return ProvenanceCompletenessReport(
        required_fields=required,
        present_fields=present,
        missing_fields=missing,
        unknown_fields=unknown,
        schema_complete=schema_complete,

        # Presence of a field name is never treated as verification of its
        # physical or scientific meaning.
        semantic_validation_performed=False,
    )


def build_execution_readiness_report(
    plan_payload: Mapping[str, object],
    *,
    provenance_report: ProvenanceCompletenessReport | None = None,
) -> ExecutionReadinessReport:
    validate_nonexecut_m2dgr_evaluation_plan(
        plan_payload
    )

    authorization = plan_payload[
        "execution_authorization"
    ]

    metrics = plan_payload[
        "metrics"
    ]

    executable_count = sum(
        item[
            "execution_authorized"
        ]
        is True
        for item in metrics
    )

    scoreable_count = sum(
        item[
            "scoring_authorized"
        ]
        is True
        for item in metrics
    )

    ready = authorization[
        "evaluation_ready"
    ]

    if ready is not False:
        raise M2DGREvaluationReadinessError(
            "current frozen plan unexpectedly reports evaluation readiness"
        )

    if executable_count != 0:
        raise M2DGREvaluationReadinessError(
            "current frozen plan unexpectedly contains executable metrics"
        )

    if scoreable_count != 0:
        raise M2DGREvaluationReadinessError(
            "current frozen plan unexpectedly contains scoreable metrics"
        )

    provenance_complete = (
        None
        if provenance_report is None
        else provenance_report.schema_complete
    )

    return ExecutionReadinessReport(
        status=plan_payload[
            "status"
        ],

        ready=False,

        association_execution_authorized=
            authorization[
                "association_execution_authorized"
            ],

        evaluation_interval_authorized=
            authorization[
                "evaluation_interval_authorized"
            ],

        alignment_execution_authorized=
            authorization[
                "alignment_execution_authorized"
            ],

        metric_computation_authorized=
            authorization[
                "metric_computation_authorized"
            ],

        trajectory_scoring_authorized=
            authorization[
                "trajectory_scoring_authorized"
            ],

        estimator_scoring_authorized=
            authorization[
                "estimator_scoring_authorized"
            ],

        metric_entry_count=len(
            metrics
        ),

        executable_metric_entry_count=
            executable_count,

        scoreable_metric_entry_count=
            scoreable_count,

        global_blockers=tuple(
            plan_payload[
                "remaining_blockers"
            ]
        ),

        provenance_schema_complete=
            provenance_complete,

        # Completeness of names is not semantic verification.
        provenance_semantics_verified=False,
    )


def require_execution_ready(
    plan_payload: Mapping[str, object],
    *,
    provenance_report: ProvenanceCompletenessReport | None = None,
) -> None:
    report = build_execution_readiness_report(
        plan_payload,
        provenance_report=provenance_report,
    )

    if not report.ready:
        raise M2DGREvaluationExecutionBlocked(
            "M2DGR evaluation execution remains blocked by the frozen "
            "non-executable plan and Protocol V2"
        )
