from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from typing import Mapping
import json
import re


SCHEMA = (
    "TRUST_ROBOT_M2DGR_TRAJECTORY_ASSOCIATION_"
    "EVALUATION_PROTOCOL_CANDIDATE_V1"
)

SCHEMA_VERSION = 1

HEX64 = re.compile(
    r"^[0-9a-f]{64}$"
)


class M2DGREvaluationProtocolError(
    ValueError
):
    pass


def evaluation_protocol_content_sha256(
    payload: Mapping[str, object],
) -> str:
    value = deepcopy(
        dict(
            payload
        )
    )

    value.pop(
        "content_sha256",
        None,
    )

    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode(
        "utf-8"
    )

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
        raise M2DGREvaluationProtocolError(
            f"{label} must be a mapping"
        )

    return value


def _false(
    mapping,
    key,
    label,
):
    if mapping.get(
        key
    ) is not False:
        raise M2DGREvaluationProtocolError(
            f"{label}.{key} must be false"
        )


def _true(
    mapping,
    key,
    label,
):
    if mapping.get(
        key
    ) is not True:
        raise M2DGREvaluationProtocolError(
            f"{label}.{key} must be true"
        )


def _sha(
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
        raise M2DGREvaluationProtocolError(
            f"{label} must be lowercase SHA256"
        )

    return value


def validate_m2dgr_evaluation_protocol(
    payload: Mapping[str, object],
) -> None:
    root = _mapping(
        payload,
        "root",
    )

    if root.get(
        "schema"
    ) != SCHEMA:
        raise M2DGREvaluationProtocolError(
            "unexpected schema"
        )

    if root.get(
        "schema_version"
    ) != SCHEMA_VERSION:
        raise M2DGREvaluationProtocolError(
            "unexpected schema version"
        )

    if root.get(
        "dataset_id"
    ) != "M2DGR":
        raise M2DGREvaluationProtocolError(
            "unexpected dataset"
        )

    if root.get(
        "status"
    ) != "blocked_pending_evidence":
        raise M2DGREvaluationProtocolError(
            "evaluation protocol must remain blocked"
        )

    expected_digest = (
        evaluation_protocol_content_sha256(
            root
        )
    )

    actual_digest = _sha(
        root.get(
            "content_sha256"
        ),
        "content_sha256",
    )

    if actual_digest != expected_digest:
        raise M2DGREvaluationProtocolError(
            "content digest mismatch"
        )

    sources = _mapping(
        root.get(
            "source_artifacts"
        ),
        "source_artifacts",
    )

    expected_sources = {
        "phase3d_trajectory_manifest",
        "phase3e_reference_temporal_association_evidence",
        "calibration_evidence",
        "reference_quality_index",
    }

    if set(
        sources
    ) != expected_sources:
        raise M2DGREvaluationProtocolError(
            "unexpected source artifacts"
        )

    for name in expected_sources:
        source = _mapping(
            sources[
                name
            ],
            f"source_artifacts.{name}",
        )

        _sha(
            source.get(
                "content_sha256"
            ),
            f"{name}.content_sha256",
        )

        _sha(
            source.get(
                "file_sha256"
            ),
            f"{name}.file_sha256",
        )

    observed = _mapping(
        root.get(
            "observed_dataset_state"
        ),
        "observed_dataset_state",
    )

    if observed.get(
        "trajectory_count"
    ) != 36:
        raise M2DGREvaluationProtocolError(
            "expected 36 trajectories"
        )

    if observed.get(
        "split_counts"
    ) != {
        "train":
            36,

        "validation_calibration":
            0,

        "confirmation_test":
            0,
    }:
        raise M2DGREvaluationProtocolError(
            "unexpected split inventory"
        )

    if observed.get(
        "reference_frame_counts"
    ) != {
        "unknown":
            36,
    }:
        raise M2DGREvaluationProtocolError(
            "reference frame uncertainty must be preserved"
        )

    metrics = _mapping(
        root.get(
            "metric_families"
        ),
        "metric_families",
    )

    expected_metrics = {
        "absolute_translation_trajectory_error",
        "absolute_rotation_trajectory_error",
        "relative_translation_pose_error",
        "relative_rotation_pose_error",
    }

    if set(
        metrics
    ) != expected_metrics:
        raise M2DGREvaluationProtocolError(
            "unexpected metric families"
        )

    for name in expected_metrics:
        metric = _mapping(
            metrics[
                name
            ],
            f"metric_families.{name}",
        )

        _false(
            metric,
            "enabled",
            name,
        )

        if metric.get(
            "association_policy"
        ) != "unselected":
            raise M2DGREvaluationProtocolError(
                f"{name} association policy must remain unselected"
            )

        if metric.get(
            "alignment_policy"
        ) != "unselected":
            raise M2DGREvaluationProtocolError(
                f"{name} alignment policy must remain unselected"
            )

        if metric.get(
            "aggregation"
        ) != "unselected":
            raise M2DGREvaluationProtocolError(
                f"{name} aggregation must remain unselected"
            )

    temporal = _mapping(
        root.get(
            "temporal_association"
        ),
        "temporal_association",
    )

    if temporal.get(
        "selected_method"
    ) != "unselected":
        raise M2DGREvaluationProtocolError(
            "association method must remain unselected"
        )

    if temporal.get(
        "association_tolerance_seconds"
    ) is not None:
        raise M2DGREvaluationProtocolError(
            "association tolerance must remain null"
        )

    if temporal.get(
        "fixed_reference_to_estimator_offset_seconds"
    ) is not None:
        raise M2DGREvaluationProtocolError(
            "fixed offset must remain null"
        )

    if temporal.get(
        "interpolation_method"
    ) != "unselected":
        raise M2DGREvaluationProtocolError(
            "interpolation method must remain unselected"
        )

    for key in (
        "nearest_neighbor_authorized",
        "reference_interpolation_authorized",
        "lag_search_authorized",
        "selection_from_train_split_authorized",
        "selection_from_confirmation_test_authorized",
    ):
        _false(
            temporal,
            key,
            "temporal_association",
        )

    interval = _mapping(
        root.get(
            "evaluation_interval"
        ),
        "evaluation_interval",
    )

    if interval.get(
        "selected_policy"
    ) != "unselected":
        raise M2DGREvaluationProtocolError(
            "evaluation interval policy must remain unselected"
        )

    _false(
        interval,
        "created",
        "evaluation_interval",
    )

    _false(
        interval,
        "numeric_header_range_intersection_is_evaluation_interval",
        "evaluation_interval",
    )

    _false(
        interval,
        "reference_sensor_numeric_overlap_is_evaluation_interval",
        "evaluation_interval",
    )

    _false(
        interval,
        "sample_run_endpoints_imply_continuous_time_coverage",
        "evaluation_interval",
    )

    alignment = _mapping(
        root.get(
            "frame_alignment"
        ),
        "frame_alignment",
    )

    if alignment.get(
        "selected_mode"
    ) != "unselected":
        raise M2DGREvaluationProtocolError(
            "frame alignment mode must remain unselected"
        )

    for key in (
        "reference_frame_semantics_verified",
        "reference_frame_transform_verified",
        "selection_from_train_split_authorized",
        "selection_from_confirmation_test_authorized",
    ):
        _false(
            alignment,
            key,
            "frame_alignment",
        )

    _true(
        alignment,
        "sim3_requires_explicit_scale_gauge_justification",
        "frame_alignment",
    )

    _true(
        alignment,
        "test_error_based_alignment_policy_selection_forbidden",
        "frame_alignment",
    )

    selection = _mapping(
        root.get(
            "selection_policy"
        ),
        "selection_policy",
    )

    if selection.get(
        "current_validation_calibration_trajectory_count"
    ) != 0:
        raise M2DGREvaluationProtocolError(
            "validation-calibration split must remain absent"
        )

    _false(
        selection,
        "confirmation_test_may_select_protocol_choices",
        "selection_policy",
    )

    _false(
        selection,
        "current_train_data_may_select_blocked_choices",
        "selection_policy",
    )

    authorization = _mapping(
        root.get(
            "authorization"
        ),
        "authorization",
    )

    for key in (
        "protocol_schema_definition_authorized",
        "metric_family_definition_authorized",
        "dimension_gating_definition_authorized",
        "provenance_requirement_definition_authorized",
        "validation_only_selection_rule_definition_authorized",
    ):
        _true(
            authorization,
            key,
            "authorization",
        )

    for key in (
        "trajectory_scoring_authorized",
        "estimator_scoring_authorized",
        "metric_computation_authorized",
        "association_execution_authorized",
        "alignment_execution_authorized",
        "reference_interpolation_authorized",
        "nearest_neighbor_pose_association_authorized",
        "evaluation_interval_authorized",
        "protocol_choice_selection_from_current_data_authorized",
        "evaluation_ready",
    ):
        _false(
            authorization,
            key,
            "authorization",
        )

    semantics = _mapping(
        root.get(
            "manifest_semantics"
        ),
        "manifest_semantics",
    )

    _false(
        semantics,
        "trajectory_manifest_modified",
        "manifest_semantics",
    )

    _false(
        semantics,
        "successor_manifest_created",
        "manifest_semantics",
    )
