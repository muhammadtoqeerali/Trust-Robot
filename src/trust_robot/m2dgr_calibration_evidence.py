from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from typing import Mapping
import json
import re


SCHEMA = "TRUST_ROBOT_M2DGR_CALIBRATION_EVIDENCE_V1"
SCHEMA_VERSION = 1

HEX64 = re.compile(
    r"^[0-9a-f]{64}$"
)


class M2DGRCalibrationEvidenceError(
    ValueError
):
    pass


def calibration_evidence_content_sha256(
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


def _require_mapping(
    value: object,
    label: str,
) -> Mapping[str, object]:
    if not isinstance(
        value,
        Mapping,
    ):
        raise M2DGRCalibrationEvidenceError(
            f"{label} must be a mapping"
        )

    return value


def _require_bool(
    mapping: Mapping[str, object],
    key: str,
    expected: bool,
    label: str,
) -> None:
    if mapping.get(
        key
    ) is not expected:
        raise M2DGRCalibrationEvidenceError(
            f"{label}.{key} must be {expected}"
        )


def _require_sha256(
    value: object,
    label: str,
) -> str:
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
        raise M2DGRCalibrationEvidenceError(
            f"{label} must be lowercase SHA256"
        )

    return value


def validate_m2dgr_calibration_evidence(
    payload: Mapping[str, object],
) -> None:
    root = _require_mapping(
        payload,
        "root",
    )

    if root.get(
        "schema"
    ) != SCHEMA:
        raise M2DGRCalibrationEvidenceError(
            "unexpected calibration evidence schema"
        )

    if root.get(
        "schema_version"
    ) != SCHEMA_VERSION:
        raise M2DGRCalibrationEvidenceError(
            "unexpected calibration evidence schema version"
        )

    if root.get(
        "dataset_id"
    ) != "M2DGR":
        raise M2DGRCalibrationEvidenceError(
            "unexpected dataset"
        )

    expected_digest = (
        calibration_evidence_content_sha256(
            root
        )
    )

    actual_digest = _require_sha256(
        root.get(
            "content_sha256"
        ),
        "content_sha256",
    )

    if (
        actual_digest
        != expected_digest
    ):
        raise M2DGRCalibrationEvidenceError(
            "calibration evidence content digest mismatch"
        )

    sources = _require_mapping(
        root.get(
            "source_artifacts"
        ),
        "source_artifacts",
    )

    expected_sources = {
        "phase3d_trajectory_manifest",
        "phase3e_reference_temporal_evidence",
        "calibration_source_provenance",
        "rotation_hypothesis_challenge",
        "calibration_requirements_inventory",
    }

    if set(
        sources
    ) != expected_sources:
        raise M2DGRCalibrationEvidenceError(
            "unexpected calibration source artifacts"
        )

    for name in sorted(
        expected_sources
    ):
        source = _require_mapping(
            sources[
                name
            ],
            f"source_artifacts.{name}",
        )

        _require_sha256(
            source.get(
                "content_sha256"
            ),
            f"{name}.content_sha256",
        )

        _require_sha256(
            source.get(
                "file_sha256"
            ),
            f"{name}.file_sha256",
        )

    observations = _require_mapping(
        root.get(
            "observations"
        ),
        "observations",
    )

    rotation = _require_mapping(
        observations.get(
            "d435i_imu_relative_rotation"
        ),
        "observations.d435i_imu_relative_rotation",
    )

    if rotation.get(
        "frozen_trajectory_count"
    ) != 28:
        raise M2DGRCalibrationEvidenceError(
            "expected frozen 28-trajectory rotation cohort"
        )

    if rotation.get(
        "published_greater_than_identity_count"
    ) != 28:
        raise M2DGRCalibrationEvidenceError(
            "expected published rotation > identity on 28/28"
        )

    if rotation.get(
        "published_greater_than_transpose_count"
    ) != 28:
        raise M2DGRCalibrationEvidenceError(
            "expected published rotation > transpose on 28/28"
        )

    if rotation.get(
        "published_greater_than_both_fixed_alternatives_count"
    ) != 28:
        raise M2DGRCalibrationEvidenceError(
            "expected published rotation > both alternatives on 28/28"
        )

    _require_bool(
        rotation,
        "rotation_fitted",
        False,
        "rotation",
    )

    _require_bool(
        rotation,
        "lag_fitted",
        False,
        "rotation",
    )

    _require_bool(
        rotation,
        "motion_threshold_created",
        False,
        "rotation",
    )

    _require_bool(
        rotation,
        "score_threshold_created",
        False,
        "rotation",
    )

    _require_bool(
        rotation,
        "sensor_content_support_observed",
        True,
        "rotation",
    )

    _require_bool(
        rotation,
        "full_extrinsic_verified",
        False,
        "rotation",
    )

    requirements = _require_mapping(
        observations.get(
            "requirements"
        ),
        "observations.requirements",
    )

    expected_zero = (
        "full_extrinsic_calibrations_independently_verified",
        "intrinsic_calibrations_independently_verified",
        "reference_families_with_verified_sensor_origin_to_lidar_transform",
    )

    for key in expected_zero:
        if requirements.get(
            key
        ) != 0:
            raise M2DGRCalibrationEvidenceError(
                f"requirements.{key} must remain zero"
            )

    if requirements.get(
        "relative_rotations_with_strong_fixed_hypothesis_sensor_content_support"
    ) != 1:
        raise M2DGRCalibrationEvidenceError(
            "expected exactly one supported relative rotation"
        )

    if requirements.get(
        "relative_rotation_supported_requirement_ids"
    ) != [
        "d435i_imu_relative_rotation",
    ]:
        raise M2DGRCalibrationEvidenceError(
            "unexpected supported calibration requirement IDs"
        )

    _require_bool(
        requirements,
        "mocap_published_sensor_origin_to_lidar_transform_found",
        False,
        "requirements",
    )

    _require_bool(
        requirements,
        "dataset_calibration_verified",
        False,
        "requirements",
    )

    legacy = _require_mapping(
        observations.get(
            "legacy_manifest_calibration_artifacts"
        ),
        "legacy_manifest_calibration_artifacts",
    )

    if legacy.get(
        "artifact_count"
    ) != 36:
        raise M2DGRCalibrationEvidenceError(
            "expected 36 legacy manifest integrity artifacts"
        )

    for key in (
        "all_are_raw_bag_integrity_artifacts",
        "all_have_empty_applies_to_stream_ids",
        "all_have_empty_applies_to_frame_ids",
    ):
        _require_bool(
            legacy,
            key,
            True,
            "legacy",
        )

    _require_bool(
        legacy,
        "establish_sensor_calibration",
        False,
        "legacy",
    )

    contract = _require_mapping(
        root.get(
            "contract_semantics"
        ),
        "contract_semantics",
    )

    if contract.get(
        "legacy_calibration_artifact_default_role"
    ) != "artifact_integrity":
        raise M2DGRCalibrationEvidenceError(
            "legacy calibration artifact role must be artifact_integrity"
        )

    _require_bool(
        contract,
        "artifact_integrity_establishes_sensor_calibration",
        False,
        "contract",
    )

    _require_bool(
        contract,
        "calibration_provenance_establishes_sensor_calibration",
        False,
        "contract",
    )

    _require_bool(
        contract,
        "sensor_calibration_verification_role_requires_verified_status",
        True,
        "contract",
    )

    _require_bool(
        contract,
        "sensor_calibration_verification_role_requires_stream_or_frame_scope",
        True,
        "contract",
    )

    _require_bool(
        contract,
        "historical_manifest_representation_preserved",
        True,
        "contract",
    )

    _require_bool(
        contract,
        "historical_manifest_role_field_injected",
        False,
        "contract",
    )

    semantics = _require_mapping(
        root.get(
            "manifest_semantics"
        ),
        "manifest_semantics",
    )

    _require_sha256(
        semantics.get(
            "source_trajectory_manifest_file_sha256"
        ),
        "manifest_semantics.source_trajectory_manifest_file_sha256",
    )

    _require_bool(
        semantics,
        "trajectory_manifest_modified",
        False,
        "manifest_semantics",
    )

    _require_bool(
        semantics,
        "successor_manifest_created",
        False,
        "manifest_semantics",
    )

    interpretation = _require_mapping(
        root.get(
            "interpretation"
        ),
        "interpretation",
    )

    _require_bool(
        interpretation,
        "author_calibration_provenance_established",
        True,
        "interpretation",
    )

    _require_bool(
        interpretation,
        "author_cross_file_consistency_established",
        True,
        "interpretation",
    )

    _require_bool(
        interpretation,
        "d435i_imu_relative_rotation_has_independent_released_sensor_content_support",
        True,
        "interpretation",
    )

    false_interpretations = (
        "d435i_imu_relative_rotation_support_is_full_extrinsic_verification",
        "translation_verified",
        "camera_intrinsics_verified",
        "camera_lidar_extrinsic_verified",
        "handsfree_lidar_full_extrinsic_verified",
        "reference_lever_arms_verified",
        "dataset_calibration_verified",
        "synchronization_verified",
        "evaluation_ready",
    )

    for key in false_interpretations:
        _require_bool(
            interpretation,
            key,
            False,
            "interpretation",
        )

    policy = _require_mapping(
        root.get(
            "policy"
        ),
        "policy",
    )

    _require_bool(
        policy,
        "characterization_only",
        True,
        "policy",
    )

    false_policy = (
        "raw_data_modified",
        "author_calibration_modified",
        "historical_manifest_modified",
        "successor_manifest_created",
        "new_calibration_fit_performed",
        "new_rotation_fit_performed",
        "new_translation_fit_performed",
        "new_lag_fit_performed",
        "new_motion_threshold_created",
        "new_score_threshold_created",
        "new_calibration_acceptance_tolerance_created",
        "automatic_sample_exclusion_rule_created",
        "manifest_calibration_status_upgraded",
        "dataset_calibration_verified",
        "synchronization_verified",
        "evaluation_ready",
    )

    for key in false_policy:
        _require_bool(
            policy,
            key,
            False,
            "policy",
        )
