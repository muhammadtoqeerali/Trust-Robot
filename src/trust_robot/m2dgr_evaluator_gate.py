from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Mapping
import json
import re

from .m2dgr_evaluation_protocol_v2 import (
    validate_m2dgr_evaluation_protocol_v2,
)


BOUNDARY_SCHEMA = (
    "TRUST_ROBOT_M2DGR_REFERENCE_FAMILY_"
    "PROTOCOL_BOUNDARY_EVIDENCE_V1"
)

BOUNDARY_SCHEMA_VERSION = 1

REFERENCE_FAMILIES = (
    "rtk_ins",
    "leica",
    "mocap",
)

REFERENCE_DIMENSIONS = (
    "translation",
    "rotation",
)

HEX64 = re.compile(
    r"^[0-9a-f]{64}$"
)


class M2DGREvaluationGateError(
    ValueError
):
    """Raised when frozen gate inputs violate their declared contract."""


class M2DGRMetricExecutionBlocked(
    RuntimeError
):
    """Raised when metric execution is requested while the gate is closed."""


class M2DGREstimatorScoringBlocked(
    RuntimeError
):
    """Raised when estimator scoring is requested while the gate is closed."""


@dataclass(
    frozen=True,
)
class MetricFamilyDefinition:
    name: str
    short_name: str
    required_dimensions: tuple[str, ...]


@dataclass(
    frozen=True,
)
class DimensionGate:
    reference_family: str
    dimension: str
    structural_dimension_present: bool
    audited_invalid_sample_count_total: int | None
    all_audited_samples_structurally_valid: bool
    scoring_admissible: bool
    blockers: tuple[str, ...]


@dataclass(
    frozen=True,
)
class MetricGate:
    reference_family: str
    metric_name: str
    short_name: str
    required_dimensions: tuple[str, ...]
    definition_authorized: bool
    structural_dimensions_supported: bool
    metric_enabled: bool
    execution_authorized: bool
    scoring_authorized: bool
    blockers: tuple[str, ...]


def reference_family_protocol_boundary_content_sha256(
    payload: Mapping[str, object],
) -> str:
    value = deepcopy(
        dict(payload)
    )

    value.pop(
        "content_sha256",
        None,
    )

    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")

    return sha256(
        raw
    ).hexdigest()


def _mapping(
    value,
    label,
):
    if not isinstance(
        value,
        Mapping,
    ):
        raise M2DGREvaluationGateError(
            f"{label} must be a mapping"
        )

    return value


def _expect_bool(
    mapping,
    key,
    expected,
    label,
):
    if mapping.get(key) is not expected:
        raise M2DGREvaluationGateError(
            f"{label}.{key} must be {expected}"
        )


def _expect_sha(
    value,
    label,
):
    if (
        not isinstance(
            value,
            str,
        )
        or HEX64.fullmatch(
            value
        )
        is None
    ):
        raise M2DGREvaluationGateError(
            f"{label} must be lowercase SHA256"
        )


def _string_tuple(
    value,
    label,
) -> tuple[str, ...]:
    if not isinstance(
        value,
        list,
    ):
        raise M2DGREvaluationGateError(
            f"{label} must be a list"
        )

    result = []

    for item in value:
        if not isinstance(
            item,
            str,
        ):
            raise M2DGREvaluationGateError(
                f"{label} items must be strings"
            )

        result.append(
            item
        )

    return tuple(
        result
    )


def validate_m2dgr_reference_family_protocol_boundary(
    payload: Mapping[str, object],
) -> None:
    root = _mapping(
        payload,
        "root",
    )

    if root.get(
        "schema"
    ) != BOUNDARY_SCHEMA:
        raise M2DGREvaluationGateError(
            "unexpected boundary schema"
        )

    if root.get(
        "schema_version"
    ) != BOUNDARY_SCHEMA_VERSION:
        raise M2DGREvaluationGateError(
            "unexpected boundary schema version"
        )

    if root.get(
        "dataset_id"
    ) != "M2DGR":
        raise M2DGREvaluationGateError(
            "unexpected boundary dataset"
        )

    if root.get(
        "status"
    ) != "blocked_pending_physical_evidence":
        raise M2DGREvaluationGateError(
            "boundary must remain blocked"
        )

    actual_digest = root.get(
        "content_sha256"
    )

    _expect_sha(
        actual_digest,
        "content_sha256",
    )

    expected_digest = (
        reference_family_protocol_boundary_content_sha256(
            root
        )
    )

    if actual_digest != expected_digest:
        raise M2DGREvaluationGateError(
            "boundary content digest mismatch"
        )

    inventory = _mapping(
        root.get(
            "mechanical_inventory"
        ),
        "mechanical_inventory",
    )

    if inventory.get(
        "trajectory_count"
    ) != 36:
        raise M2DGREvaluationGateError(
            "unexpected trajectory count"
        )

    if inventory.get(
        "reference_family_counts"
    ) != {
        "rtk_ins": 16,
        "leica": 11,
        "mocap": 9,
    }:
        raise M2DGREvaluationGateError(
            "unexpected reference-family counts"
        )

    if inventory.get(
        "structural_dimension_counts"
    ) != {
        "translation_and_rotation": 25,
        "translation_only": 11,
    }:
        raise M2DGREvaluationGateError(
            "unexpected structural dimension counts"
        )

    _expect_bool(
        inventory,
        "continuous_time_coverage_verified",
        False,
        "mechanical_inventory",
    )

    common = _mapping(
        root.get(
            "common_frozen_protocol_boundary"
        ),
        "common_frozen_protocol_boundary",
    )

    if common.get(
        "temporal_association_method"
    ) != "unselected":
        raise M2DGREvaluationGateError(
            "association method must remain unselected"
        )

    if common.get(
        "association_tolerance_seconds"
    ) is not None:
        raise M2DGREvaluationGateError(
            "association tolerance must remain null"
        )

    if common.get(
        "fixed_reference_to_estimator_offset_seconds"
    ) is not None:
        raise M2DGREvaluationGateError(
            "fixed reference offset must remain null"
        )

    if common.get(
        "interpolation_method"
    ) != "unselected":
        raise M2DGREvaluationGateError(
            "interpolation method must remain unselected"
        )

    if common.get(
        "evaluation_interval_policy"
    ) != "unselected":
        raise M2DGREvaluationGateError(
            "evaluation interval must remain unselected"
        )

    if common.get(
        "alignment_mode"
    ) != "unselected":
        raise M2DGREvaluationGateError(
            "alignment mode must remain unselected"
        )

    for key in (
        "reference_frame_semantics_verified",
        "reference_frame_transform_verified",
        "association_execution_authorized",
        "metric_computation_authorized",
        "trajectory_scoring_authorized",
        "estimator_scoring_authorized",
        "dataset_calibration_verified",
        "synchronization_verified",
        "evaluation_ready",
    ):
        _expect_bool(
            common,
            key,
            False,
            "common_frozen_protocol_boundary",
        )

    for key in (
        "metric_family_definition_authorized",
        "dimension_gating_definition_authorized",
        "protocol_schema_definition_authorized",
    ):
        _expect_bool(
            common,
            key,
            True,
            "common_frozen_protocol_boundary",
        )

    matrix = _mapping(
        root.get(
            "family_dimension_matrix"
        ),
        "family_dimension_matrix",
    )

    if set(
        matrix
    ) != set(
        REFERENCE_FAMILIES
    ):
        raise M2DGREvaluationGateError(
            "unexpected reference-family matrix"
        )

    expected_structural = {
        "rtk_ins": {
            "translation": True,
            "rotation": True,
        },
        "leica": {
            "translation": True,
            "rotation": False,
        },
        "mocap": {
            "translation": True,
            "rotation": True,
        },
    }

    for family in REFERENCE_FAMILIES:
        family_entry = _mapping(
            matrix[family],
            f"family_dimension_matrix.{family}",
        )

        for dimension in REFERENCE_DIMENSIONS:
            entry = _mapping(
                family_entry.get(
                    dimension
                ),
                (
                    "family_dimension_matrix."
                    f"{family}.{dimension}"
                ),
            )

            if entry.get(
                "dimension"
            ) != dimension:
                raise M2DGREvaluationGateError(
                    f"{family}.{dimension}: dimension mismatch"
                )

            if entry.get(
                "structural_dimension_present"
            ) is not expected_structural[
                family
            ][
                dimension
            ]:
                raise M2DGREvaluationGateError(
                    f"{family}.{dimension}: structural status changed"
                )

            _expect_bool(
                entry,
                "continuous_time_coverage_verified",
                False,
                f"{family}.{dimension}",
            )

            _expect_bool(
                entry,
                "exact_reference_physical_origin_verified",
                False,
                f"{family}.{dimension}",
            )

            _expect_bool(
                entry,
                "reference_transform_applicability_verified",
                False,
                f"{family}.{dimension}",
            )

            _expect_bool(
                entry,
                "reference_timestamp_physical_event_verified",
                False,
                f"{family}.{dimension}",
            )

            _expect_bool(
                entry,
                "reference_timestamp_export_timebase_verified",
                False,
                f"{family}.{dimension}",
            )

            _expect_bool(
                entry,
                "temporal_association_verified",
                False,
                f"{family}.{dimension}",
            )

            _expect_bool(
                entry,
                "scoring_admissible_under_frozen_protocol_v2_now",
                False,
                f"{family}.{dimension}",
            )

            _string_tuple(
                entry.get(
                    "blockers"
                ),
                f"{family}.{dimension}.blockers",
            )

    mocap_rotation = _mapping(
        matrix["mocap"].get(
            "rotation"
        ),
        "mocap.rotation",
    )

    if mocap_rotation.get(
        "audited_invalid_sample_count_total"
    ) != 1274:
        raise M2DGREvaluationGateError(
            "unexpected mocap invalid-rotation count"
        )

    _expect_bool(
        mocap_rotation,
        "all_audited_samples_structurally_valid",
        False,
        "mocap.rotation",
    )

    leica_rotation = _mapping(
        matrix["leica"].get(
            "rotation"
        ),
        "leica.rotation",
    )

    _expect_bool(
        leica_rotation,
        "structural_dimension_present",
        False,
        "leica.rotation",
    )

    conclusion = _mapping(
        root.get(
            "protocol_boundary_conclusion"
        ),
        "protocol_boundary_conclusion",
    )

    for key in (
        "any_reference_family_translation_scoring_admissible_now",
        "any_reference_family_rotation_scoring_admissible_now",
        "any_reference_family_ate_or_rpe_admissible_now",
        "rtk_ins_restricted_scoring_admissible_now",
        "leica_translation_only_restricted_scoring_admissible_now",
        "mocap_translation_only_restricted_scoring_admissible_now",
        "mocap_rotation_restricted_scoring_admissible_now",
        "physical_evaluation_objective_can_be_completed_from_current_frozen_evidence",
        "this_artifact_authorizes_protocol_v3_selection",
        "this_artifact_authorizes_any_new_association_or_alignment_choice",
        "confirmation_test_may_be_used_to_choose_that_future_protocol",
    ):
        _expect_bool(
            conclusion,
            key,
            False,
            "protocol_boundary_conclusion",
        )

    for key in (
        "non_scoring_structural_inventory_and_provenance_analysis_admissible",
        "metric_schema_definition_admissible",
        "dimension_gating_definition_admissible",
        "protocol_v2_should_remain_byte_identical",
        "future_physical_evidence_could_change_boundary",
        "a_differently_scoped_nonphysical_author_benchmark_replication_would_require_separate_predeclared_protocol",
    ):
        _expect_bool(
            conclusion,
            key,
            True,
            "protocol_boundary_conclusion",
        )

    policy = _mapping(
        root.get(
            "policy"
        ),
        "policy",
    )

    for key in (
        "raw_data_modified",
        "frozen_evidence_modified",
        "confirmation_test_raw_data_inspected",
        "confirmation_test_used_for_selection",
        "new_calibration_value_created",
        "new_frame_transform_created",
        "new_timing_offset_created",
        "new_timing_tolerance_created",
        "new_interpolation_rule_created",
        "new_evaluation_interval_created",
        "new_alignment_rule_created",
        "new_mocap_filter_created",
        "reference_interpolation_authorized",
        "nearest_neighbor_pose_association_authorized",
        "association_execution_authorized",
        "metric_computation_authorized",
        "trajectory_scoring_authorized",
        "estimator_scoring_authorized",
        "dataset_calibration_verified",
        "synchronization_verified",
        "evaluation_ready",
    ):
        _expect_bool(
            policy,
            key,
            False,
            "policy",
        )


class M2DGRFailClosedEvaluationGate:
    """Definition-only evaluation gate for frozen M2DGR Protocol V2.

    This class intentionally contains no temporal association, interpolation,
    frame alignment, ATE, RPE, aggregation, trajectory scoring, or estimator
    scoring implementation.

    It exposes only protocol-defined metric metadata and fail-closed
    admissibility decisions.
    """

    def __init__(
        self,
        protocol: Mapping[str, object],
        boundary: Mapping[str, object],
    ):
        validate_m2dgr_evaluation_protocol_v2(
            protocol
        )

        validate_m2dgr_reference_family_protocol_boundary(
            boundary
        )

        self._protocol = deepcopy(
            dict(protocol)
        )

        self._boundary = deepcopy(
            dict(boundary)
        )

    @property
    def metric_definitions(
        self,
    ) -> tuple[MetricFamilyDefinition, ...]:
        metrics = self._protocol[
            "metric_families"
        ]

        definitions = []

        for name in sorted(
            metrics
        ):
            metric = metrics[name]

            definitions.append(
                MetricFamilyDefinition(
                    name=name,
                    short_name=metric[
                        "short_name"
                    ],
                    required_dimensions=tuple(
                        metric[
                            "required_reference_dimensions"
                        ]
                    ),
                )
            )

        return tuple(
            definitions
        )

    def metric_definition(
        self,
        metric_name: str,
    ) -> MetricFamilyDefinition:
        for definition in self.metric_definitions:
            if definition.name == metric_name:
                return definition

        raise M2DGREvaluationGateError(
            f"unknown metric family: {metric_name}"
        )

    def dimension_gate(
        self,
        reference_family: str,
        dimension: str,
    ) -> DimensionGate:
        if reference_family not in REFERENCE_FAMILIES:
            raise M2DGREvaluationGateError(
                f"unknown reference family: {reference_family}"
            )

        if dimension not in REFERENCE_DIMENSIONS:
            raise M2DGREvaluationGateError(
                f"unknown reference dimension: {dimension}"
            )

        entry = (
            self._boundary[
                "family_dimension_matrix"
            ][
                reference_family
            ][
                dimension
            ]
        )

        return DimensionGate(
            reference_family=reference_family,
            dimension=dimension,
            structural_dimension_present=entry[
                "structural_dimension_present"
            ],
            audited_invalid_sample_count_total=entry[
                "audited_invalid_sample_count_total"
            ],
            all_audited_samples_structurally_valid=entry[
                "all_audited_samples_structurally_valid"
            ],
            scoring_admissible=entry[
                "scoring_admissible_under_frozen_protocol_v2_now"
            ],
            blockers=tuple(
                entry[
                    "blockers"
                ]
            ),
        )

    def metric_gate(
        self,
        reference_family: str,
        metric_name: str,
    ) -> MetricGate:
        definition = self.metric_definition(
            metric_name
        )

        metric = self._protocol[
            "metric_families"
        ][
            metric_name
        ]

        dimension_gates = tuple(
            self.dimension_gate(
                reference_family,
                dimension,
            )
            for dimension
            in definition.required_dimensions
        )

        structural_dimensions_supported = all(
            gate.structural_dimension_present
            for gate in dimension_gates
        )

        auth = self._protocol[
            "authorization"
        ]

        definition_authorized = (
            auth[
                "metric_family_definition_authorized"
            ]
            and auth[
                "dimension_gating_definition_authorized"
            ]
        )

        metric_enabled = (
            metric["enabled"]
        )

        execution_authorized = all(
            (
                metric_enabled,
                auth[
                    "association_execution_authorized"
                ],
                auth[
                    "evaluation_interval_authorized"
                ],
                auth[
                    "alignment_execution_authorized"
                ],
                auth[
                    "metric_computation_authorized"
                ],
                structural_dimensions_supported,
                all(
                    gate.scoring_admissible
                    for gate in dimension_gates
                ),
            )
        )

        scoring_authorized = all(
            (
                execution_authorized,
                auth[
                    "trajectory_scoring_authorized"
                ],
                auth[
                    "estimator_scoring_authorized"
                ],
                auth[
                    "evaluation_ready"
                ],
            )
        )

        blockers = []

        for gate in dimension_gates:
            blockers.extend(
                gate.blockers
            )

        if not structural_dimensions_supported:
            blockers.append(
                "required reference dimension structurally unavailable"
            )

        if not metric_enabled:
            blockers.append(
                "metric family disabled by frozen Protocol V2"
            )

        if not auth[
            "association_execution_authorized"
        ]:
            blockers.append(
                "association execution not authorized"
            )

        if not auth[
            "evaluation_interval_authorized"
        ]:
            blockers.append(
                "evaluation interval not authorized"
            )

        if not auth[
            "alignment_execution_authorized"
        ]:
            blockers.append(
                "alignment execution not authorized"
            )

        if not auth[
            "metric_computation_authorized"
        ]:
            blockers.append(
                "metric computation not authorized"
            )

        if not auth[
            "trajectory_scoring_authorized"
        ]:
            blockers.append(
                "trajectory scoring not authorized"
            )

        if not auth[
            "estimator_scoring_authorized"
        ]:
            blockers.append(
                "estimator scoring not authorized"
            )

        unique_blockers = tuple(
            dict.fromkeys(
                blockers
            )
        )

        return MetricGate(
            reference_family=reference_family,
            metric_name=metric_name,
            short_name=definition.short_name,
            required_dimensions=definition.required_dimensions,
            definition_authorized=definition_authorized,
            structural_dimensions_supported=structural_dimensions_supported,
            metric_enabled=metric_enabled,
            execution_authorized=execution_authorized,
            scoring_authorized=scoring_authorized,
            blockers=unique_blockers,
        )

    def require_metric_execution_authorized(
        self,
        reference_family: str,
        metric_name: str,
    ) -> MetricGate:
        gate = self.metric_gate(
            reference_family,
            metric_name,
        )

        if not gate.execution_authorized:
            blocker_text = "; ".join(
                gate.blockers
            )

            raise M2DGRMetricExecutionBlocked(
                f"{reference_family}/{metric_name} execution blocked: "
                f"{blocker_text}"
            )

        return gate

    def require_estimator_scoring_authorized(
        self,
    ) -> None:
        auth = self._protocol[
            "authorization"
        ]

        if not (
            auth[
                "estimator_scoring_authorized"
            ]
            and auth[
                "evaluation_ready"
            ]
        ):
            raise M2DGREstimatorScoringBlocked(
                "M2DGR estimator scoring is blocked by frozen Protocol V2"
            )


def load_fail_closed_m2dgr_evaluation_gate(
    protocol_path: Path,
    boundary_path: Path,
) -> M2DGRFailClosedEvaluationGate:
    protocol = json.loads(
        Path(
            protocol_path
        ).read_text(
            encoding="utf-8"
        )
    )

    boundary = json.loads(
        Path(
            boundary_path
        ).read_text(
            encoding="utf-8"
        )
    )

    return M2DGRFailClosedEvaluationGate(
        protocol=protocol,
        boundary=boundary,
    )
