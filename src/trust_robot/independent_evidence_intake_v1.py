"""A30-4: SHA-bound candidate evidence intake preflight.

No signature, independent identity, physical timing,
calibration, or reference trajectory is verified.
A candidate artifact is never a qualifying receipt.
"""

from __future__ import annotations

import hashlib

from trust_robot.m2dgr_prospective_evidence_packet_v1 import (
    REQUEST_SPECS,
    validate_packet,
)

SCHEMA = "TRUST_ROBOT_R135_A30_4_EVIDENCE_INTAKE_V1"

TIMING_REQUESTS = frozenset({
    "B04", "B05", "B06", "C01", "C02",
})

REQUEST_IDS = frozenset(row[0] for row in REQUEST_SPECS)

FIELDS = frozenset({
    "request_id",
    "capture_session_reference",
    "acquisition_actor_token",
    "witness_actor_token",
    "method_version",
    "declared_artifact_sha256",
    "clock_domain",
    "physical_event_definition",
    "uncertainty_method",
    "transform_direction",
    "independent_review_status",
    "witness_independence_verified",
    "scientific_gate_opened",
})


class EvidenceIntakeError(ValueError):
    pass


def require(ok, message):
    if not ok:
        raise EvidenceIntakeError(message)


def _text(value):
    return (
        type(value) is str
        and 0 < len(value) <= 256
        and all(32 <= ord(ch) <= 126 for ch in value)
    )


def blank_intake_ledger(packet):
    """Produce empty intake slots for the frozen A23 requests."""
    try:
        validate_packet(packet)
    except Exception as exc:
        raise EvidenceIntakeError(
            "Frozen A23 packet invalid"
        ) from exc

    return {
        "schema": SCHEMA,
        "status": "EMPTY_PROSPECTIVE_INTAKE_ONLY",
        "request_count": 13,
        "requests": [
            {
                "request_id": row[0],
                "stage": row[1],
                "candidate_count": 0,
                "qualifying_receipt_count": 0,
                "status": "UNSUBMITTED",
            }
            for row in REQUEST_SPECS
        ],
        "real_independent_witnesses_verified": 0,
        "qualified_evidence_receipts": 0,
        "physical_measurements_qualified": False,
        "real_factor_count": 0,
        "real_factor_admission": "DENIED",
        "m2dgr_gates": "11_CLOSED",
    }


def preflight_candidate(candidate, artifact_bytes):
    """Verify candidate format and source-byte SHA only.

    Distinct self-declared actor tokens do not establish
    independent witnessing. No approved physical values
    are returned.
    """
    require(
        type(candidate) is dict
        and set(candidate) == FIELDS,
        "Unexpected evidence candidate fields",
    )

    require(
        type(artifact_bytes) is bytes
        and 0 < len(artifact_bytes) <= 2_000_000,
        "Invalid candidate artifact byte bound",
    )

    require(
        candidate["request_id"] in REQUEST_IDS,
        "Unknown A23 request ID",
    )

    for name in (
        "capture_session_reference",
        "acquisition_actor_token",
        "witness_actor_token",
        "method_version",
    ):
        require(
            _text(candidate[name]),
            "Invalid provenance token: " + name,
        )

    require(
        candidate["acquisition_actor_token"]
        != candidate["witness_actor_token"],
        "Self-declared acquisition and witness actors coincide",
    )

    expected = hashlib.sha256(artifact_bytes).hexdigest()

    require(
        candidate["declared_artifact_sha256"] == expected,
        "Candidate artifact SHA mismatch",
    )

    require(
        candidate["independent_review_status"] == "UNREVIEWED"
        and candidate["witness_independence_verified"] is False
        and candidate["scientific_gate_opened"] is False,
        "Unsupported independent evidence qualification",
    )

    for name in (
        "clock_domain",
        "physical_event_definition",
        "uncertainty_method",
        "transform_direction",
    ):
        require(
            candidate[name] is None or _text(candidate[name]),
            "Malformed optional field: " + name,
        )

    request_id = candidate["request_id"]

    if request_id in TIMING_REQUESTS:
        require(
            all(
                _text(candidate[name])
                for name in (
                    "clock_domain",
                    "physical_event_definition",
                    "uncertainty_method",
                )
            ),
            "Timing evidence lacks explicit event semantics",
        )

    if request_id in {"B03", "C03"}:
        require(
            candidate["transform_direction"]
            == "T_target_source",
            "Transform direction is unspecified",
        )

    return {
        "schema": SCHEMA,
        "status": "CANDIDATE_ARTIFACT_SHA_MATCH_ONLY",
        "request_id": request_id,
        "candidate_artifact_sha256": expected,
        "candidate_artifact_bytes": len(artifact_bytes),
        "actor_tokens_differ": True,
        "witness_independence_verified": False,
        "physical_event_definition_verified": False,
        "physical_clock_accuracy_verified": False,
        "metric_calibration_verified": False,
        "independent_reference_verified": False,
        "qualifying_receipt_created": False,
        "physical_measurements_qualified": False,
        "estimator_invoked": False,
        "real_factor_count": 0,
        "real_factor_admission": "DENIED",
        "m2dgr_gates": "11_CLOSED",
    }


def accept_as_qualified_receipt(*args, **kwargs):
    raise EvidenceIntakeError(
        "Candidate preflight cannot authorize independent evidence"
    )
