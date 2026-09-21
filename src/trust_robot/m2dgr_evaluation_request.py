from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from .m2dgr_evaluation_plan import (
    validate_nonexecut_m2dgr_evaluation_plan,
)
from .m2dgr_evaluation_readiness import (
    build_execution_readiness_report,
    build_provenance_completeness_report,
)


REFERENCE_FAMILIES = (
    "rtk_ins",
    "leica",
    "mocap",
)


class M2DGREvaluationInspectionError(
    ValueError
):
    """Raised for an invalid metadata-only evaluation inspection request."""


@dataclass(
    frozen=True,
)
class EvaluationInspectionRequest:
    """A metadata-only request.

    It deliberately carries no trajectory path, trajectory samples, timestamp,
    offset, tolerance, transform, alignment parameter, or metric value.
    """

    reference_family: str
    metric_name: str
    present_provenance_fields: tuple[str, ...] = ()

    def to_dict(
        self,
    ) -> dict[str, object]:
        return {
            "reference_family":
                self.reference_family,

            "metric_name":
                self.metric_name,

            "present_provenance_fields":
                list(
                    self.present_provenance_fields
                ),
        }


@dataclass(
    frozen=True,
)
class EvaluationInspectionReport:
    status: str

    reference_family: str
    metric_name: str
    short_name: str
    required_dimensions: tuple[str, ...]

    structural_dimensions_supported: bool
    metric_enabled: bool
    execution_authorized: bool
    scoring_authorized: bool

    provenance_schema_complete: bool
    provenance_semantics_verified: bool
    missing_provenance_fields: tuple[str, ...]
    unknown_provenance_fields: tuple[str, ...]

    association_method: str
    association_tolerance_seconds: float | None
    fixed_reference_to_estimator_offset_seconds: float | None
    interpolation_method: str
    evaluation_interval_policy: str
    alignment_mode: str

    confirmation_test_partition_closed: bool
    confirmation_test_used_for_selection: bool
    confirmation_test_raw_data_accessed: bool

    evaluation_ready: bool
    blockers: tuple[str, ...]

    def to_dict(
        self,
    ) -> dict[str, object]:
        return {
            "status":
                self.status,

            "request": {
                "reference_family":
                    self.reference_family,

                "metric_name":
                    self.metric_name,

                "short_name":
                    self.short_name,

                "required_dimensions":
                    list(
                        self.required_dimensions
                    ),
            },

            "metric_gate": {
                "structural_dimensions_supported":
                    self.structural_dimensions_supported,

                "metric_enabled":
                    self.metric_enabled,

                "execution_authorized":
                    self.execution_authorized,

                "scoring_authorized":
                    self.scoring_authorized,
            },

            "provenance": {
                "schema_complete":
                    self.provenance_schema_complete,

                "semantics_verified":
                    self.provenance_semantics_verified,

                "missing_fields":
                    list(
                        self.missing_provenance_fields
                    ),

                "unknown_fields":
                    list(
                        self.unknown_provenance_fields
                    ),
            },

            "execution_contract": {
                "association_method":
                    self.association_method,

                "association_tolerance_seconds":
                    self.association_tolerance_seconds,

                "fixed_reference_to_estimator_offset_seconds":
                    self.fixed_reference_to_estimator_offset_seconds,

                "interpolation_method":
                    self.interpolation_method,

                "evaluation_interval_policy":
                    self.evaluation_interval_policy,

                "alignment_mode":
                    self.alignment_mode,
            },

            "confirmation_test_policy": {
                "partition_closed_to_selection":
                    self.confirmation_test_partition_closed,

                "used_for_selection":
                    self.confirmation_test_used_for_selection,

                "raw_data_accessed":
                    self.confirmation_test_raw_data_accessed,
            },

            "evaluation_ready":
                self.evaluation_ready,

            "blockers":
                list(
                    self.blockers
                ),
        }


def _normalize_names(
    values: Iterable[str],
) -> tuple[str, ...]:
    normalized = set()

    for value in values:
        if (
            not isinstance(
                value,
                str,
            )
            or not value.strip()
        ):
            raise M2DGREvaluationInspectionError(
                "present provenance field names must be non-empty strings"
            )

        normalized.add(
            value
        )

    return tuple(
        sorted(
            normalized
        )
    )


def _dedupe_strings(
    values: Iterable[str],
) -> tuple[str, ...]:
    result = []
    seen = set()

    for value in values:
        if value not in seen:
            seen.add(
                value
            )

            result.append(
                value
            )

    return tuple(
        result
    )


def inspect_nonexecut_m2dgr_evaluation_request(
    plan_payload: Mapping[str, object],
    request: EvaluationInspectionRequest,
) -> EvaluationInspectionReport:
    """Inspect a family/metric request without loading or evaluating trajectories."""

    validate_nonexecut_m2dgr_evaluation_plan(
        plan_payload
    )

    if request.reference_family not in REFERENCE_FAMILIES:
        raise M2DGREvaluationInspectionError(
            f"unknown reference family: {request.reference_family}"
        )

    present_fields = _normalize_names(
        request.present_provenance_fields
    )

    matches = [
        item
        for item in plan_payload[
            "metrics"
        ]
        if (
            item[
                "reference_family"
            ]
            == request.reference_family
            and item[
                "metric_name"
            ]
            == request.metric_name
        )
    ]

    if len(matches) != 1:
        raise M2DGREvaluationInspectionError(
            "requested family/metric pair is not defined exactly once"
        )

    metric = matches[0]

    if metric[
        "execution_authorized"
    ] is not False:
        raise M2DGREvaluationInspectionError(
            "current inspection interface cannot expose an executable metric"
        )

    if metric[
        "scoring_authorized"
    ] is not False:
        raise M2DGREvaluationInspectionError(
            "current inspection interface cannot expose a scoreable metric"
        )

    provenance = build_provenance_completeness_report(
        plan_payload,
        present_fields=present_fields,
    )

    readiness = build_execution_readiness_report(
        plan_payload,
        provenance_report=provenance,
    )

    if readiness.ready is not False:
        raise M2DGREvaluationInspectionError(
            "current frozen plan unexpectedly became evaluation-ready"
        )

    execution = plan_payload[
        "execution_contract"
    ]

    confirmation = plan_payload[
        "confirmation_test_policy"
    ]

    blockers = _dedupe_strings(
        (
            *metric[
                "blockers"
            ],
            *readiness.global_blockers,
        )
    )

    return EvaluationInspectionReport(
        status=plan_payload[
            "status"
        ],

        reference_family=request.reference_family,
        metric_name=request.metric_name,
        short_name=metric[
            "short_name"
        ],

        required_dimensions=tuple(
            metric[
                "required_dimensions"
            ]
        ),

        structural_dimensions_supported=metric[
            "structural_dimensions_supported"
        ],

        metric_enabled=metric[
            "metric_enabled"
        ],

        execution_authorized=False,
        scoring_authorized=False,

        provenance_schema_complete=
            provenance.schema_complete,

        provenance_semantics_verified=False,

        missing_provenance_fields=
            provenance.missing_fields,

        unknown_provenance_fields=
            provenance.unknown_fields,

        association_method=execution[
            "association_method"
        ],

        association_tolerance_seconds=execution[
            "association_tolerance_seconds"
        ],

        fixed_reference_to_estimator_offset_seconds=execution[
            "fixed_reference_to_estimator_offset_seconds"
        ],

        interpolation_method=execution[
            "interpolation_method"
        ],

        evaluation_interval_policy=execution[
            "evaluation_interval_policy"
        ],

        alignment_mode=execution[
            "alignment_mode"
        ],

        confirmation_test_partition_closed=confirmation[
            "partition_closed_to_selection"
        ],

        confirmation_test_used_for_selection=confirmation[
            "used_for_selection"
        ],

        confirmation_test_raw_data_accessed=confirmation[
            "raw_data_accessed"
        ],

        evaluation_ready=False,

        blockers=blockers,
    )


def render_evaluation_inspection_report(
    report: EvaluationInspectionReport,
) -> str:
    """Render deterministic human-readable blocked-state diagnostics."""

    lines = [
        "M2DGR EVALUATION INSPECTION",
        "=" * 80,
        "",
        f"status: {report.status}",
        f"reference_family: {report.reference_family}",
        f"metric_name: {report.metric_name}",
        f"metric_short_name: {report.short_name}",
        (
            "required_dimensions: "
            + ", ".join(
                report.required_dimensions
            )
        ),
        "",
        "Metric gate:",
        (
            "  structural_dimensions_supported: "
            f"{report.structural_dimensions_supported}"
        ),
        (
            "  metric_enabled: "
            f"{report.metric_enabled}"
        ),
        (
            "  execution_authorized: "
            f"{report.execution_authorized}"
        ),
        (
            "  scoring_authorized: "
            f"{report.scoring_authorized}"
        ),
        "",
        "Provenance:",
        (
            "  schema_complete: "
            f"{report.provenance_schema_complete}"
        ),
        (
            "  semantics_verified: "
            f"{report.provenance_semantics_verified}"
        ),
        (
            "  missing_field_count: "
            f"{len(report.missing_provenance_fields)}"
        ),
        (
            "  unknown_field_count: "
            f"{len(report.unknown_provenance_fields)}"
        ),
    ]

    for field in report.missing_provenance_fields:
        lines.append(
            f"  missing: {field}"
        )

    for field in report.unknown_provenance_fields:
        lines.append(
            f"  unknown: {field}"
        )

    lines.extend(
        [
            "",
            "Frozen execution contract:",
            (
                "  association_method: "
                f"{report.association_method}"
            ),
            (
                "  association_tolerance_seconds: "
                f"{report.association_tolerance_seconds}"
            ),
            (
                "  fixed_reference_to_estimator_offset_seconds: "
                f"{report.fixed_reference_to_estimator_offset_seconds}"
            ),
            (
                "  interpolation_method: "
                f"{report.interpolation_method}"
            ),
            (
                "  evaluation_interval_policy: "
                f"{report.evaluation_interval_policy}"
            ),
            (
                "  alignment_mode: "
                f"{report.alignment_mode}"
            ),
            "",
            "Confirmation-test policy:",
            (
                "  partition_closed_to_selection: "
                f"{report.confirmation_test_partition_closed}"
            ),
            (
                "  used_for_selection: "
                f"{report.confirmation_test_used_for_selection}"
            ),
            (
                "  raw_data_accessed: "
                f"{report.confirmation_test_raw_data_accessed}"
            ),
            "",
            (
                "evaluation_ready: "
                f"{report.evaluation_ready}"
            ),
            "",
            f"Blockers ({len(report.blockers)}):",
        ]
    )

    for blocker in report.blockers:
        lines.append(
            f"  - {blocker}"
        )

    lines.extend(
        [
            "",
            "RESULT: BLOCKED",
            (
                "This is metadata-only inspection. "
                "No trajectory data or metric value was processed."
            ),
        ]
    )

    return "\n".join(
        lines
    ) + "\n"
