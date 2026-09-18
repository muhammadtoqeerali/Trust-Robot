from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from typing import Mapping
import json
import re


SCHEMA = (
    "TRUST_ROBOT_M2DGR_TRAJECTORY_ASSOCIATION_"
    "EVALUATION_PROTOCOL_CANDIDATE_V2"
)

SCHEMA_VERSION = 2

HEX64 = re.compile(
    r"^[0-9a-f]{64}$"
)


class M2DGREvaluationProtocolV2Error(
    ValueError
):
    pass


def evaluation_protocol_v2_content_sha256(
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
        allow_nan=False,
    ).encode("utf-8")

    return sha256(raw).hexdigest()


def _mapping(
    value,
    label,
):
    if not isinstance(
        value,
        Mapping,
    ):
        raise M2DGREvaluationProtocolV2Error(
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
        raise M2DGREvaluationProtocolV2Error(
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
        or HEX64.fullmatch(value)
        is None
    ):
        raise M2DGREvaluationProtocolV2Error(
            f"{label} must be SHA256"
        )


def validate_m2dgr_evaluation_protocol_v2(
    payload: Mapping[str, object],
) -> None:
    root = _mapping(
        payload,
        "root",
    )

    if root.get("schema") != SCHEMA:
        raise M2DGREvaluationProtocolV2Error(
            "unexpected schema"
        )

    if root.get(
        "schema_version"
    ) != SCHEMA_VERSION:
        raise M2DGREvaluationProtocolV2Error(
            "unexpected schema version"
        )

    if root.get(
        "dataset_id"
    ) != "M2DGR":
        raise M2DGREvaluationProtocolV2Error(
            "unexpected dataset"
        )

    if root.get(
        "status"
    ) != "blocked_pending_physical_evidence":
        raise M2DGREvaluationProtocolV2Error(
            "protocol V2 must remain blocked"
        )

    actual = root.get(
        "content_sha256"
    )

    _expect_sha(
        actual,
        "content_sha256",
    )

    expected = (
        evaluation_protocol_v2_content_sha256(
            root
        )
    )

    if actual != expected:
        raise M2DGREvaluationProtocolV2Error(
            "content digest mismatch"
        )

    observed = _mapping(
        root.get(
            "observed_dataset_state"
        ),
        "observed_dataset_state",
    )

    if observed.get(
        "split_counts"
    ) != {
        "train": 22,
        "validation_calibration": 7,
        "confirmation_test": 7,
    }:
        raise M2DGREvaluationProtocolV2Error(
            "unexpected frozen split counts"
        )

    _expect_bool(
        observed,
        "split_frozen",
        True,
        "observed_dataset_state",
    )

    _expect_bool(
        observed,
        "validation_calibration_partition_available",
        True,
        "observed_dataset_state",
    )

    _expect_bool(
        observed,
        "confirmation_partition_closed_to_selection",
        True,
        "observed_dataset_state",
    )

    if observed.get(
        "reference_frame_counts"
    ) != {
        "unknown": 36,
    }:
        raise M2DGREvaluationProtocolV2Error(
            "reference-frame uncertainty must remain explicit"
        )

    metrics = _mapping(
        root.get(
            "metric_families"
        ),
        "metric_families",
    )

    for name, metric in metrics.items():
        metric = _mapping(
            metric,
            f"metric_families.{name}",
        )

        _expect_bool(
            metric,
            "enabled",
            False,
            name,
        )

        if metric.get(
            "association_policy"
        ) != "unselected":
            raise M2DGREvaluationProtocolV2Error(
                f"{name}: association selected"
            )

        if metric.get(
            "alignment_policy"
        ) != "unselected":
            raise M2DGREvaluationProtocolV2Error(
                f"{name}: alignment selected"
            )

    temporal = _mapping(
        root.get(
            "temporal_association"
        ),
        "temporal_association",
    )

    if temporal.get(
        "selection_partition"
    ) != "validation_calibration":
        raise M2DGREvaluationProtocolV2Error(
            "association selection partition must be validation_calibration"
        )

    _expect_bool(
        temporal,
        "selection_partition_available",
        True,
        "temporal_association",
    )

    _expect_bool(
        temporal,
        "selection_authorized_now",
        False,
        "temporal_association",
    )

    if temporal.get(
        "selected_method"
    ) != "unselected":
        raise M2DGREvaluationProtocolV2Error(
            "association method must remain unselected"
        )

    if temporal.get(
        "association_tolerance_seconds"
    ) is not None:
        raise M2DGREvaluationProtocolV2Error(
            "association tolerance must remain null"
        )

    if temporal.get(
        "fixed_reference_to_estimator_offset_seconds"
    ) is not None:
        raise M2DGREvaluationProtocolV2Error(
            "fixed offset must remain null"
        )

    for key in (
        "nearest_neighbor_authorized",
        "reference_interpolation_authorized",
        "lag_search_authorized",
        "train_may_select_association_parameters",
        "confirmation_test_may_select_association_parameters",
    ):
        _expect_bool(
            temporal,
            key,
            False,
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
        raise M2DGREvaluationProtocolV2Error(
            "evaluation interval selected"
        )

    _expect_bool(
        interval,
        "created",
        False,
        "evaluation_interval",
    )

    _expect_bool(
        interval,
        "selection_authorized_now",
        False,
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
        raise M2DGREvaluationProtocolV2Error(
            "alignment mode must remain unselected"
        )

    if alignment.get(
        "selection_partition"
    ) != "validation_calibration":
        raise M2DGREvaluationProtocolV2Error(
            "alignment partition must be validation_calibration"
        )

    _expect_bool(
        alignment,
        "selection_partition_available",
        True,
        "frame_alignment",
    )

    _expect_bool(
        alignment,
        "selection_authorized_now",
        False,
        "frame_alignment",
    )

    _expect_bool(
        alignment,
        "confirmation_test_may_select_alignment",
        False,
        "frame_alignment",
    )

    _expect_bool(
        alignment,
        "reference_frame_semantics_verified",
        False,
        "frame_alignment",
    )

    selection = _mapping(
        root.get(
            "selection_policy"
        ),
        "selection_policy",
    )

    _expect_bool(
        selection,
        "validation_calibration_partition_frozen",
        True,
        "selection_policy",
    )

    _expect_bool(
        selection,
        "confirmation_test_partition_frozen",
        True,
        "selection_policy",
    )

    _expect_bool(
        selection,
        "confirmation_test_closed_to_future_selection",
        True,
        "selection_policy",
    )

    _expect_bool(
        selection,
        "physical_fact_cannot_be_created_by_validation_selection",
        True,
        "selection_policy",
    )

    for key in (
        "current_split_alone_authorizes_association_choice",
        "current_split_alone_authorizes_alignment_choice",
        "current_split_alone_authorizes_evaluation",
    ):
        _expect_bool(
            selection,
            key,
            False,
            "selection_policy",
        )

    authorization = _mapping(
        root.get(
            "authorization"
        ),
        "authorization",
    )

    for key in (
        "split_selection_complete",
        "validation_calibration_partition_available",
        "confirmation_test_partition_closed",
        "protocol_schema_definition_authorized",
        "metric_family_definition_authorized",
        "dimension_gating_definition_authorized",
        "provenance_requirement_definition_authorized",
    ):
        _expect_bool(
            authorization,
            key,
            True,
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
        "association_tolerance_frozen",
        "evaluation_interval_authorized",
        "alignment_mode_selected",
        "dataset_calibration_verified",
        "synchronization_verified",
        "evaluation_ready",
    ):
        _expect_bool(
            authorization,
            key,
            False,
            "authorization",
        )

    semantics = _mapping(
        root.get(
            "manifest_semantics"
        ),
        "manifest_semantics",
    )

    _expect_bool(
        semantics,
        "frozen_split_manifest_is_authoritative",
        True,
        "manifest_semantics",
    )

    _expect_bool(
        semantics,
        "trajectory_manifest_modified_by_protocol_v2",
        False,
        "manifest_semantics",
    )

    _expect_bool(
        semantics,
        "successor_manifest_created_by_protocol_v2",
        False,
        "manifest_semantics",
    )

    for key in (
        "split_freeze_does_not_upgrade_timing",
        "split_freeze_does_not_upgrade_calibration",
        "split_freeze_does_not_upgrade_reference_frame_semantics",
        "split_freeze_does_not_upgrade_evaluation_readiness",
    ):
        _expect_bool(
            semantics,
            key,
            True,
            "manifest_semantics",
        )
