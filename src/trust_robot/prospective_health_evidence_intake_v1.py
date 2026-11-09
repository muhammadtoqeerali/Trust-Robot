"""Prospective health-supervision evidence intake: SHAPE and GAP CHECKS ONLY.

This module never accepts a supervision source, creates a health label, or
issues a robot decision. SHA-256-shaped identifiers are never proof that the
referenced artifacts exist or independently support a physical claim.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Mapping

SCHEMA = "TRUST_ROBOT_R135_A37_2_PROSPECTIVE_HEALTH_EVIDENCE_INTAKE_V1"
_ID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,95}$")
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")
MODALITIES = ("camera", "imu", "lidar")
LIDAR_PROTOCOL = "vlp32c_controlled_availability_prospective"
UNSELECTED_PROTOCOL = "source_protocol_unselected"
LIDAR_ROLES = (
    "source_measurement_sha256",
    "raw_operational_status_sha256",
    "interval_binding_receipt_sha256",
    "no_intervention_receipt_sha256",
    "baseline_nominality_review_receipt_sha256",
    "intervention_execution_receipt_sha256",
    "measurement_relation_verification_receipt_sha256",
)
GENERIC_ROLES = (
    "prospective_source_declaration_sha256",
    "independent_measurement_role_evidence_sha256",
    "independent_interval_provenance_sha256",
    "independent_state_criteria_evidence_sha256",
)


class HealthIntakeError(ValueError):
    """Candidate is malformed, not evidence that a sensor is bad."""


def _require(condition: bool, why: str) -> None:
    if not condition:
        raise HealthIntakeError(why)


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def content_sha256(payload: Mapping[str, object]) -> str:
    value = dict(payload)
    value.pop("content_sha256", None)
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def build_empty_candidate(source_id: str, modality: str) -> dict[str, object]:
    _require(type(source_id) is str and _ID_RE.fullmatch(source_id) is not None,
             "source_id must be a bounded public-safe identifier")
    _require(modality in MODALITIES, "unknown modality")
    roles = LIDAR_ROLES if modality == "lidar" else GENERIC_ROLES
    return {
        "schema": SCHEMA,
        "source_id": source_id,
        "modality": modality,
        "split_role": "train",
        "source_protocol": (LIDAR_PROTOCOL if modality == "lidar"
                            else UNSELECTED_PROTOCOL),
        "independent_artifact_sha256_by_role": {role: None for role in roles},
        "source_accepted": False,
        "real_health_labels_assigned": False,
        "physical_action_authorized": False,
    }


def audit_candidate(candidate: Mapping[str, object]) -> dict[str, object]:
    """Check only shape/gaps. Full hashes remain unverified and unaccepted."""
    _require(type(candidate) is dict, "candidate must be an exact dictionary")
    _require(set(candidate) == {
        "schema", "source_id", "modality", "split_role", "source_protocol",
        "independent_artifact_sha256_by_role", "source_accepted",
        "real_health_labels_assigned", "physical_action_authorized",
    }, "candidate has missing or extra keys")
    _require(candidate["schema"] == SCHEMA, "schema mismatch")
    source_id = candidate["source_id"]
    _require(type(source_id) is str and _ID_RE.fullmatch(source_id) is not None,
             "invalid bounded source_id")
    modality = candidate["modality"]
    _require(type(modality) is str and modality in MODALITIES,
             "modality not declared")
    _require(candidate["split_role"] == "train", "only TRAIN prospective candidates")
    expected_protocol = (LIDAR_PROTOCOL if modality == "lidar"
                         else UNSELECTED_PROTOCOL)
    _require(candidate["source_protocol"] == expected_protocol,
             "protocol does not apply to this sensor")
    for field in ("source_accepted", "real_health_labels_assigned",
                  "physical_action_authorized"):
        _require(candidate[field] is False, "candidate cannot assert " + field)
    roles = LIDAR_ROLES if modality == "lidar" else GENERIC_ROLES
    values = candidate["independent_artifact_sha256_by_role"]
    _require(type(values) is dict and set(values) == set(roles),
             "artifact role set differs from prospective protocol")
    present = []
    for role in roles:
        digest = values[role]
        if digest is None:
            continue
        _require(type(digest) is str and _SHA_RE.fullmatch(digest) is not None,
                 "invalid SHA-256 shape: " + role)
        present.append(digest)
    _require(len(present) == len(set(present)),
             "different evidence roles must not reuse an artifact digest")
    missing = [role for role in roles if values[role] is None]
    report: dict[str, object] = {
        "schema": SCHEMA,
        "source_id": source_id,
        "modality": modality,
        "split_role": "train",
        "required_artifact_roles": list(roles),
        "evidence_digest_shapes_present": len(present),
        "evidence_roles_missing": missing,
        "candidate_shape_status": (
            "MISSING_PROSPECTIVE_ARTIFACTS" if missing else
            "DIGEST_SHAPES_PRESENT_PENDING_INDEPENDENT_EVIDENCE_REVIEW"
        ),
        "source_specific_protocol_status": (
            "EXISTING_LIDAR_VLP32C_PROSPECTIVE_ONLY" if modality == "lidar" else
            "CAMERA_OR_IMU_ACCEPTANCE_PROTOCOL_NOT_RESOLVED"
        ),
        "artifact_bytes_verified": False,
        "evidence_independence_verified": False,
        "measurement_role_verified": False,
        "health_supervision_source_accepted": False,
        "real_health_labels_assigned": False,
        "model_training_authorized": False,
        "real_factor_admission_authorized": False,
        "robot_action_authorized": False,
    }
    report["content_sha256"] = content_sha256(report)
    return report


def build_three_modality_gap_report() -> dict[str, object]:
    """Deterministic, empty prospective source catalog; NEVER an admission."""
    records = [
        audit_candidate(build_empty_candidate("prospective_" + m, m))
        for m in MODALITIES
    ]
    report: dict[str, object] = {
        "schema": SCHEMA,
        "catalog_kind": "PROSPECTIVE_EMPTY_INDEPENDENT_SUPERVISION_GAP_REPORT",
        "candidate_reviews": records,
        "accepted_baseline_nominality_sources": 0,
        "accepted_health_supervision_sources": 0,
        "real_health_labels": 0,
        "health_model_training": "BLOCKED",
        "calibration_and_validation": "BLOCKED",
        "real_sensor_factor_admission": "DENIED",
        "operational_supervisor_execution": "DENIED",
        "confirmation_access": False,
    }
    report["content_sha256"] = content_sha256(report)
    return report
