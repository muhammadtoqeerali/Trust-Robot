from __future__ import annotations

from .evidence import (
    EvidenceStatus,
    IntegrityCause,
    IntegrityEvidence,
)


def observe_frame_counter(
    previous_counter: int,
    current_counter: int,
    *,
    provenance_qualified: bool,
    source: str,
) -> IntegrityEvidence | None:
    """
    Evaluate a pair of acquisition-sequence counters.

    Only a positive discontinuity greater than one is a FRAME_GAP
    candidate.

    A derived/unverified counter may reveal a numerical discontinuity,
    but cannot produce a hard external cause.

    Duplicate or backwards counters are recorded as observations only;
    they are NOT automatically FRAME_REPEAT or BUFFER_STALL.
    """

    previous_counter = int(previous_counter)
    current_counter = int(current_counter)

    delta = current_counter - previous_counter

    if delta == 1:
        return None

    if delta > 1:
        status = (
            EvidenceStatus.HARD_QUALIFIED
            if provenance_qualified
            else EvidenceStatus.OBSERVATION_ONLY
        )

        return IntegrityEvidence(
            indicator="FRAME_COUNTER_GAP",
            status=status,
            candidate_cause=IntegrityCause.FRAME_GAP,
            source=source,
            details={
                "previous_counter": previous_counter,
                "current_counter": current_counter,
                "delta": delta,
                "estimated_missing_frames": delta - 1,
                "counter_provenance_qualified": provenance_qualified,
            },
        )

    # delta <= 0.
    #
    # This is real sequence evidence, but our frozen taxonomy does not
    # allow us to claim FRAME_REPEAT or BUFFER_STALL merely from this cue.
    return IntegrityEvidence(
        indicator="FRAME_COUNTER_NONMONOTONIC",
        status=EvidenceStatus.OBSERVATION_ONLY,
        source=source,
        details={
            "previous_counter": previous_counter,
            "current_counter": current_counter,
            "delta": delta,
            "counter_provenance_qualified": provenance_qualified,
        },
    )
