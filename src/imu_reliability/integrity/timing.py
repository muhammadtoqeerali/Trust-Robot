from __future__ import annotations

from dataclasses import dataclass

from .evidence import (
    EvidenceStatus,
    IntegrityCause,
    IntegrityEvidence,
)


@dataclass(frozen=True)
class TimingEnvelope:
    """
    Development-calibrated acquisition timing envelope.

    A TimingEnvelope is not sufficient by itself for hard attribution.
    `frozen=True` must explicitly record that the operating point was
    fixed before final testing.
    """

    minimum_delta: float
    maximum_delta: float
    unit: str
    frozen: bool = False

    def __post_init__(self) -> None:
        if self.maximum_delta < self.minimum_delta:
            raise ValueError(
                "maximum_delta must be >= minimum_delta"
            )


def observe_timing_delta(
    previous_timestamp: float,
    current_timestamp: float,
    *,
    unit: str,
    source: str,
) -> IntegrityEvidence:
    """
    Record timing evidence without making a causal claim.
    """

    delta = float(current_timestamp) - float(previous_timestamp)

    return IntegrityEvidence(
        indicator="ACQ_TIMING_DELTA",
        status=EvidenceStatus.OBSERVATION_ONLY,
        source=source,
        details={
            "previous_timestamp": float(previous_timestamp),
            "current_timestamp": float(current_timestamp),
            "delta": delta,
            "unit": unit,
        },
    )


def evaluate_timing_envelope(
    previous_timestamp: float,
    current_timestamp: float,
    *,
    envelope: TimingEnvelope,
    timestamp_provenance_qualified: bool,
    source: str,
) -> IntegrityEvidence | None:
    """
    Evaluate a timing interval.

    A hard ACQ_TIMING_VIOLATION is permitted only when BOTH:
      1. the timestamp provenance is qualified, and
      2. the timing envelope has been explicitly frozen.

    This keeps the current primary UniVR path from being promoted before
    development calibration is complete.
    """

    delta = float(current_timestamp) - float(previous_timestamp)

    inside = (
        envelope.minimum_delta
        <= delta
        <= envelope.maximum_delta
    )

    if inside:
        return None

    hard_qualified = (
        timestamp_provenance_qualified
        and envelope.frozen
    )

    return IntegrityEvidence(
        indicator="ACQ_TIMING_OUTSIDE_ENVELOPE",
        status=(
            EvidenceStatus.HARD_QUALIFIED
            if hard_qualified
            else EvidenceStatus.OBSERVATION_ONLY
        ),
        candidate_cause=IntegrityCause.ACQ_TIMING_VIOLATION,
        source=source,
        details={
            "previous_timestamp": float(previous_timestamp),
            "current_timestamp": float(current_timestamp),
            "delta": delta,
            "minimum_delta": envelope.minimum_delta,
            "maximum_delta": envelope.maximum_delta,
            "unit": envelope.unit,
            "timestamp_provenance_qualified":
                timestamp_provenance_qualified,
            "envelope_frozen": envelope.frozen,
        },
    )
