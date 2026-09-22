from __future__ import annotations

from hashlib import sha256
from typing import Any, Mapping
import json
import re

from .diagnostics import (
    LIDAR_REGISTRATION_FEATURE_ORDER,
    extract_lidar_registration_diagnostics,
)
from .lidar_frontend import (
    LidarRegistrationDiagnostics,
)


ARTIFACT_RECORD_SCHEMA = (
    "TRUST_ROBOT_PHASE4_LIDAR_DIAGNOSTIC_ARTIFACT_RECORD_V1"
)

PAIR_RECORD_KEYS = frozenset(
    {
        "record_type",
        "trajectory",
        "scan_index",
        "previous_header_stamp_ns",
        "current_header_stamp_ns",
        "header_delta_ns",
        "delta_prev_lidar_T_current_lidar",
        "state_world_T_lidar",
        "diagnostics",
        "scientific_scope",
    }
)

DIAGNOSTIC_KEYS = frozenset(
    {
        "source_point_count",
        "target_point_count",
        "fixed_point_iterations",
        "final_correspondence_count",
        "final_nearest_neighbor_rmse_m",
        "convergence_rule",
        "correspondence_rejection_used",
        "voxel_downsampling_used",
    }
)

SOURCE_SCOPE_KEYS = frozenset(
    {
        "reference_data_used",
        "confirmation_test_data_used",
        "scan_temporal_reference_verified",
        "per_point_time_used",
        "deskew_performed",
        "correspondence_rejection_used",
        "voxel_downsampling_used",
        "ate_computed",
        "rpe_computed",
        "trajectory_scoring_performed",
    }
)


class DiagnosticArtifactError(ValueError):
    """Raised when a frozen Phase-2 pair record violates the adapter contract."""


def canonical_json(
    value: object,
) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def content_sha256(
    payload: Mapping[str, Any],
) -> str:
    value = dict(payload)
    value.pop("content_sha256", None)

    return sha256(
        canonical_json(value).encode("utf-8")
    ).hexdigest()


def _exact_int(
    value,
    *,
    name: str,
    minimum: int,
) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise DiagnosticArtifactError(
            f"{name} must be an exact integer"
        )

    if value < minimum:
        raise DiagnosticArtifactError(
            f"{name} must be >= {minimum}"
        )

    return value


def _nonempty_text(
    value,
    *,
    name: str,
) -> str:
    result = str(value).strip()

    if not result:
        raise DiagnosticArtifactError(
            f"{name} cannot be empty"
        )

    return result


def _validate_sha256(
    value,
    *,
    name: str,
) -> str:
    value = str(value)

    if re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise DiagnosticArtifactError(
            f"{name} must be a lowercase SHA256 hex digest"
        )

    return value


def validate_phase2_relative_pose_record(
    record: Mapping[str, Any],
) -> None:
    if not isinstance(record, Mapping):
        raise DiagnosticArtifactError(
            "Phase-2 pair record must be a mapping"
        )

    if frozenset(record) != PAIR_RECORD_KEYS:
        raise DiagnosticArtifactError(
            "Phase-2 relative_pose top-level schema changed"
        )

    if record["record_type"] != "relative_pose":
        raise DiagnosticArtifactError(
            "Phase-2 pair record must have record_type=relative_pose"
        )

    _nonempty_text(
        record["trajectory"],
        name="trajectory",
    )

    _exact_int(
        record["scan_index"],
        name="scan_index",
        minimum=1,
    )

    previous = _exact_int(
        record["previous_header_stamp_ns"],
        name="previous_header_stamp_ns",
        minimum=0,
    )

    current = _exact_int(
        record["current_header_stamp_ns"],
        name="current_header_stamp_ns",
        minimum=0,
    )

    delta = _exact_int(
        record["header_delta_ns"],
        name="header_delta_ns",
        minimum=1,
    )

    if current <= previous:
        raise DiagnosticArtifactError(
            "current header stamp must be strictly greater than previous"
        )

    if delta != current - previous:
        raise DiagnosticArtifactError(
            "header_delta_ns does not equal current - previous"
        )

    diagnostics = record["diagnostics"]

    if not isinstance(diagnostics, Mapping):
        raise DiagnosticArtifactError(
            "diagnostics must be a mapping"
        )

    if frozenset(diagnostics) != DIAGNOSTIC_KEYS:
        raise DiagnosticArtifactError(
            "Phase-2 diagnostic schema changed"
        )

    scope = record["scientific_scope"]

    if not isinstance(scope, Mapping):
        raise DiagnosticArtifactError(
            "scientific_scope must be a mapping"
        )

    if frozenset(scope) != SOURCE_SCOPE_KEYS:
        raise DiagnosticArtifactError(
            "Phase-2 scientific_scope schema changed"
        )

    for key in SOURCE_SCOPE_KEYS:
        if scope[key] is not False:
            raise DiagnosticArtifactError(
                f"frozen Phase-2 scientific_scope must remain false: {key}"
            )


def build_lidar_diagnostic_artifact_record(
    source_record: Mapping[str, Any],
    *,
    source_line_number: int,
    source_raw_line_sha256: str,
) -> dict[str, Any]:
    validate_phase2_relative_pose_record(
        source_record
    )

    line_number = _exact_int(
        source_line_number,
        name="source_line_number",
        minimum=1,
    )

    raw_sha = _validate_sha256(
        source_raw_line_sha256,
        name="source_raw_line_sha256",
    )

    diagnostics_payload = dict(
        source_record["diagnostics"]
    )

    diagnostics = LidarRegistrationDiagnostics(
        **diagnostics_payload
    )

    feature_record = extract_lidar_registration_diagnostics(
        diagnostics
    )

    if feature_record.feature_names != LIDAR_REGISTRATION_FEATURE_ORDER:
        raise DiagnosticArtifactError(
            "diagnostic feature order changed"
        )

    payload: dict[str, Any] = {
        "schema":
            ARTIFACT_RECORD_SCHEMA,

        "record_type":
            "diagnostic_features",

        "trajectory":
            source_record["trajectory"],

        "scan_index":
            source_record["scan_index"],

        "source_line_number":
            line_number,

        "previous_header_stamp_ns":
            source_record["previous_header_stamp_ns"],

        "current_header_stamp_ns":
            source_record["current_header_stamp_ns"],

        "header_delta_ns":
            source_record["header_delta_ns"],

        "feature_values": [
            feature.value
            for feature
            in feature_record.features
        ],

        "feature_record_fingerprint_sha256":
            feature_record.fingerprint_sha256,

        "source_raw_line_sha256":
            raw_sha,

        "source_pair_record_content_sha256":
            sha256(
                canonical_json(
                    source_record
                ).encode("utf-8")
            ).hexdigest(),

        "scientific_scope": {
            "identity_direct_feature_extraction":
                True,

            "threshold_applied":
                False,

            "health_label_emitted":
                False,

            "fault_label_emitted":
                False,

            "reliability_score_emitted":
                False,

            "accuracy_score_emitted":
                False,

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
        },
    }

    payload["content_sha256"] = content_sha256(
        payload
    )

    return payload


def validate_lidar_diagnostic_artifact_record(
    payload: Mapping[str, Any],
) -> None:
    if payload.get("schema") != ARTIFACT_RECORD_SCHEMA:
        raise DiagnosticArtifactError(
            "unexpected diagnostic artifact record schema"
        )

    if payload.get("record_type") != "diagnostic_features":
        raise DiagnosticArtifactError(
            "unexpected diagnostic artifact record type"
        )

    stored = payload.get("content_sha256")

    if (
        not isinstance(stored, str)
        or stored != content_sha256(payload)
    ):
        raise DiagnosticArtifactError(
            "diagnostic artifact record content digest mismatch"
        )

    values = payload.get("feature_values")

    if not isinstance(values, list) or len(values) != 5:
        raise DiagnosticArtifactError(
            "diagnostic artifact must contain exactly five feature values"
        )

    _validate_sha256(
        payload.get("feature_record_fingerprint_sha256"),
        name="feature_record_fingerprint_sha256",
    )

    _validate_sha256(
        payload.get("source_raw_line_sha256"),
        name="source_raw_line_sha256",
    )

    _validate_sha256(
        payload.get("source_pair_record_content_sha256"),
        name="source_pair_record_content_sha256",
    )

    scope = payload.get("scientific_scope")

    if not isinstance(scope, Mapping):
        raise DiagnosticArtifactError(
            "artifact scientific_scope must be a mapping"
        )

    if scope.get("identity_direct_feature_extraction") is not True:
        raise DiagnosticArtifactError(
            "artifact must declare identity/direct extraction"
        )

    for key in (
        "threshold_applied",
        "health_label_emitted",
        "fault_label_emitted",
        "reliability_score_emitted",
        "accuracy_score_emitted",
        "reference_data_used",
        "confirmation_test_data_used",
        "ate_computed",
        "rpe_computed",
        "estimator_scoring_performed",
    ):
        if scope.get(key) is not False:
            raise DiagnosticArtifactError(
                f"diagnostic artifact scientific boundary changed: {key}"
            )
