from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, IntFlag
from typing import Any, Mapping


class IntegrityCause(IntFlag):
    """
    Qualified external integrity causes.

    IntFlag is intentional: several independently qualified causes may
    coexist and must not be collapsed to a single label.
    """

    NONE = 0
    FRAME_GAP = 1 << 0
    FIFO_OVERRUN = 1 << 1
    FRAME_REPEAT = 1 << 2
    BUFFER_STALL = 1 << 3
    ACQ_TIMING_VIOLATION = 1 << 4
    RANGE_CLIP = 1 << 5


class SuspectIndicator(str, Enum):
    CHANNEL_FREEZE_SUSPECT = "CHANNEL_FREEZE_SUSPECT"


class EvidenceStatus(str, Enum):
    """
    HARD_QUALIFIED:
        May populate the external hard-cause set C_t.

    SUSPECT_ONLY:
        Diagnostic/internal evidence only.

    OBSERVATION_ONLY:
        Measured cue with insufficient causal qualification.

    SYNTHETIC_GROUND_TRUTH:
        What an experiment injected. Never automatically becomes a
        runtime hard cause.
    """

    HARD_QUALIFIED = "HARD_QUALIFIED"
    SUSPECT_ONLY = "SUSPECT_ONLY"
    OBSERVATION_ONLY = "OBSERVATION_ONLY"
    SYNTHETIC_GROUND_TRUTH = "SYNTHETIC_GROUND_TRUTH"


@dataclass(frozen=True)
class IntegrityEvidence:
    indicator: str
    status: EvidenceStatus

    candidate_cause: IntegrityCause = IntegrityCause.NONE
    suspect: SuspectIndicator | None = None

    source: str = ""
    details: Mapping[str, Any] = field(default_factory=dict)

    @property
    def can_enter_hard_cause_set(self) -> bool:
        return (
            self.status is EvidenceStatus.HARD_QUALIFIED
            and self.candidate_cause is not IntegrityCause.NONE
        )

    def qualified_cause(self) -> IntegrityCause:
        """
        Return the external cause represented by this evidence.

        Raises if a caller tries to promote an unqualified observation,
        suspect, or synthetic injection label into C_t.
        """
        if not self.can_enter_hard_cause_set:
            raise ValueError(
                "Evidence is not qualified for the external hard-cause set: "
                f"indicator={self.indicator!r}, status={self.status.value!r}, "
                f"candidate_cause={self.candidate_cause!r}"
            )

        return self.candidate_cause
