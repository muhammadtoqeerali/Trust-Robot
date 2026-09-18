from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from typing import Mapping
import json
import re


SCHEMA = (
    "TRUST_ROBOT_M2DGR_SPLIT_FREEZE_EVIDENCE_V1"
)

SCHEMA_VERSION = 1

HEX64 = re.compile(
    r"^[0-9a-f]{64}$"
)


class M2DGRSplitFreezeEvidenceError(
    ValueError
):
    pass


def split_freeze_evidence_content_sha256(
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
        raise M2DGRSplitFreezeEvidenceError(
            f"{label} must be a mapping"
        )

    return value


def _require_bool(
    mapping,
    key,
    expected,
    label,
):
    if mapping.get(
        key
    ) is not expected:
        raise M2DGRSplitFreezeEvidenceError(
            f"{label}.{key} must be {expected}"
        )


def _require_sha(
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
        raise M2DGRSplitFreezeEvidenceError(
            f"{label} must be SHA256"
        )


def validate_m2dgr_split_freeze_evidence(
    payload: Mapping[str, object],
) -> None:
    root = _mapping(
        payload,
        "root",
    )

    if root.get(
        "schema"
    ) != SCHEMA:
        raise M2DGRSplitFreezeEvidenceError(
            "unexpected schema"
        )

    if root.get(
        "schema_version"
    ) != SCHEMA_VERSION:
        raise M2DGRSplitFreezeEvidenceError(
            "unexpected schema version"
        )

    if root.get(
        "dataset_id"
    ) != "M2DGR":
        raise M2DGRSplitFreezeEvidenceError(
            "unexpected dataset"
        )

    if root.get(
        "status"
    ) != "frozen_prospective_split":
        raise M2DGRSplitFreezeEvidenceError(
            "split must be frozen prospectively"
        )

    actual = root.get(
        "content_sha256"
    )

    _require_sha(
        actual,
        "content_sha256",
    )

    expected = (
        split_freeze_evidence_content_sha256(
            root
        )
    )

    if actual != expected:
        raise M2DGRSplitFreezeEvidenceError(
            "content digest mismatch"
        )

    assignment = _mapping(
        root.get(
            "split_assignment"
        ),
        "split_assignment",
    )

    expected_roles = {
        "train",
        "validation_calibration",
        "confirmation_test",
    }

    if set(
        assignment
    ) != expected_roles:
        raise M2DGRSplitFreezeEvidenceError(
            "unexpected split roles"
        )

    counts = {
        role:
            len(
                assignment[
                    role
                ]
            )
        for role in expected_roles
    }

    if counts != {
        "train":
            22,

        "validation_calibration":
            7,

        "confirmation_test":
            7,
    }:
        raise M2DGRSplitFreezeEvidenceError(
            f"unexpected split counts: {counts}"
        )

    all_ids = [
        trajectory_id
        for role in expected_roles
        for trajectory_id in assignment[
            role
        ]
    ]

    if (
        len(all_ids)
        != 36
        or len(set(all_ids))
        != 36
    ):
        raise M2DGRSplitFreezeEvidenceError(
            "split must contain 36 unique trajectories"
        )

    selection = _mapping(
        root.get(
            "selection_policy"
        ),
        "selection_policy",
    )

    _require_bool(
        selection,
        "selected_before_estimator_outcomes",
        True,
        "selection_policy",
    )

    for key in (
        "estimator_outputs_used",
        "ATE_used",
        "RPE_used",
        "timing_correlation_used",
        "calibration_score_used",
        "reference_pose_values_used",
        "author_reporting_subset_membership_used",
        "future_confirmation_outcomes_used",
    ):
        _require_bool(
            selection,
            key,
            False,
            "selection_policy",
        )

    _require_bool(
        selection,
        "holdouts_require_complete_current_estimator_inputs",
        True,
        "selection_policy",
    )

    _require_bool(
        selection,
        "train_retains_all_observed_scenarios",
        True,
        "selection_policy",
    )

    _require_bool(
        selection,
        "train_retains_all_observed_collection_dates",
        True,
        "selection_policy",
    )

    prospective = _mapping(
        root.get(
            "prospective_holdout_policy"
        ),
        "prospective_holdout_policy",
    )

    _require_bool(
        prospective,
        "confirmation_test_pristine_from_all_prior_dataset_inspection",
        False,
        "prospective_holdout_policy",
    )

    _require_bool(
        prospective,
        "confirmation_test_used_for_prior_estimator_score_selection",
        False,
        "prospective_holdout_policy",
    )

    for key in (
        "confirmation_test_available_for_future_model_selection",
        "confirmation_test_available_for_future_threshold_selection",
        "confirmation_test_available_for_future_association_selection",
        "confirmation_test_available_for_future_alignment_selection",
        "confirmation_test_available_for_future_protocol_selection",
    ):
        _require_bool(
            prospective,
            key,
            False,
            "prospective_holdout_policy",
        )

    manifest = _mapping(
        root.get(
            "manifest_semantics"
        ),
        "manifest_semantics",
    )

    _require_bool(
        manifest,
        "source_manifest_remains_immutable",
        True,
        "manifest_semantics",
    )

    _require_bool(
        manifest,
        "successor_manifest_created",
        True,
        "manifest_semantics",
    )

    _require_bool(
        manifest,
        "only_split_fields_changed",
        True,
        "manifest_semantics",
    )

    for key in (
        "synchronization_changed",
        "calibration_changed",
        "reference_semantics_changed",
        "stream_inventory_changed",
        "reference_coverage_changed",
    ):
        _require_bool(
            manifest,
            key,
            False,
            "manifest_semantics",
        )

    if manifest.get(
        "changed_trajectory_split_count"
    ) != 14:
        raise M2DGRSplitFreezeEvidenceError(
            "expected 14 changed split fields"
        )

    _require_sha(
        manifest.get(
            "successor_manifest_content_sha256"
        ),
        "successor manifest content SHA",
    )

    _require_sha(
        manifest.get(
            "successor_manifest_file_sha256"
        ),
        "successor manifest file SHA",
    )

    authorization = _mapping(
        root.get(
            "authorization"
        ),
        "authorization",
    )

    _require_bool(
        authorization,
        "split_frozen",
        True,
        "authorization",
    )

    _require_bool(
        authorization,
        "successor_manifest_authorized",
        True,
        "authorization",
    )

    for key in (
        "reference_interpolation_authorized",
        "nearest_neighbor_pose_association_authorized",
        "association_tolerance_frozen",
        "evaluation_interval_created",
        "alignment_mode_selected",
        "estimator_scoring_authorized",
        "dataset_calibration_verified",
        "synchronization_verified",
        "evaluation_ready",
    ):
        _require_bool(
            authorization,
            key,
            False,
            "authorization",
        )
