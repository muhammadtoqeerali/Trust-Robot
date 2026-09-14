from __future__ import annotations

from imu_reliability.integrity import (
    EvidenceStatus,
    IntegrityCause,
    IntegrityEvidence,
    SuspectIndicator,
)

from .types import (
    P0CorruptionKind,
    P0Truth,
)


_CAUSE_MAP = {
    P0CorruptionKind.FRAME_GAP:
        IntegrityCause.FRAME_GAP,

    P0CorruptionKind.FRAME_REPEAT:
        IntegrityCause.FRAME_REPEAT,

    P0CorruptionKind.TIMING_PERTURBATION:
        IntegrityCause.ACQ_TIMING_VIOLATION,

    P0CorruptionKind.RANGE_CLIP:
        IntegrityCause.RANGE_CLIP,
}


def p0_truth_to_evidence(
    truth: P0Truth,
) -> IntegrityEvidence:
    """
    Convert injected truth to an evaluation evidence record.

    Crucially, status remains SYNTHETIC_GROUND_TRUTH. Therefore this
    record cannot populate runtime C_t even if its label corresponds to
    an IntegrityCause.
    """

    candidate = _CAUSE_MAP.get(
        truth.spec.kind,
        IntegrityCause.NONE,
    )

    suspect = None

    if (
        truth.spec.kind
        is P0CorruptionKind.CHANNEL_FREEZE
    ):
        suspect = (
            SuspectIndicator
            .CHANNEL_FREEZE_SUSPECT
        )

    return IntegrityEvidence(
        indicator=(
            "P0_INJECTED_"
            + truth.spec.kind.value
        ),
        status=(
            EvidenceStatus
            .SYNTHETIC_GROUND_TRUTH
        ),
        candidate_cause=candidate,
        suspect=suspect,
        source="p0_injector",
        details={
            "injection_id":
                truth.injection_id,
            "spec_id":
                truth.spec.spec_id,
            "severity":
                truth.spec.severity,
            "affected_clean_start":
                truth.affected_clean_start,
            "affected_clean_end_exclusive":
                truth.affected_clean_end_exclusive,
        },
    )
