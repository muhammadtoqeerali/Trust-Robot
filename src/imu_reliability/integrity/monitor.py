from __future__ import annotations

from dataclasses import dataclass

from .evidence import (
    EvidenceStatus,
    IntegrityCause,
    IntegrityEvidence,
    SuspectIndicator,
)


@dataclass(frozen=True)
class IntegrityAssessment:
    """
    Result of evidence qualification for one acquisition update/window.
    """

    cause_mask: IntegrityCause
    hard_causes: frozenset[IntegrityCause]
    suspects: frozenset[SuspectIndicator]
    evidence: tuple[IntegrityEvidence, ...]

    @property
    def has_hard_alert(self) -> bool:
        return self.cause_mask != IntegrityCause.NONE


def assess_evidence(
    evidence_items,
) -> IntegrityAssessment:
    """
    Construct C_t from evidence.

    Only HARD_QUALIFIED evidence is allowed into C_t.
    """

    items = tuple(evidence_items)

    mask = IntegrityCause.NONE
    causes: set[IntegrityCause] = set()
    suspects: set[SuspectIndicator] = set()

    for item in items:

        if not isinstance(
            item,
            IntegrityEvidence,
        ):
            raise TypeError(
                "All items must be IntegrityEvidence"
            )

        if (
            item.status
            is EvidenceStatus.HARD_QUALIFIED
        ):
            cause = item.qualified_cause()

            mask |= cause
            causes.add(cause)

        if (
            item.status
            is EvidenceStatus.SUSPECT_ONLY
            and item.suspect is not None
        ):
            suspects.add(
                item.suspect
            )

    return IntegrityAssessment(
        cause_mask=mask,
        hard_causes=frozenset(causes),
        suspects=frozenset(suspects),
        evidence=items,
    )
