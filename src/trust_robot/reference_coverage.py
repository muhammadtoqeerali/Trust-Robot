
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CoverageError(Exception):
    pass


class ReferenceDimension(str, Enum):
    TRANSLATION = "translation"
    ROTATION = "rotation"


@dataclass(frozen=True)
class ValidInterval:
    start_ns: int
    end_ns: int

    def __post_init__(self):
        if self.start_ns < 0:
            raise CoverageError(
                "interval start must be non-negative"
            )

        if self.end_ns <= self.start_ns:
            raise CoverageError(
                "interval end must exceed start"
            )


@dataclass(frozen=True)
class ReferenceCoverageArtifact:

    trajectory_id: str
    reference_source: str

    translation_valid: bool
    rotation_valid: bool

    valid_intervals: tuple[ValidInterval, ...]

    reason: str | None = None


def validate_reference_dimension(
    artifact: ReferenceCoverageArtifact,
    dimension: ReferenceDimension,
):

    if not artifact.valid_intervals:
        raise CoverageError(
            "reference has no valid intervals"
        )

    if dimension == ReferenceDimension.TRANSLATION:

        if not artifact.translation_valid:
            raise CoverageError(
                "translation reference unavailable"
            )

    elif dimension == ReferenceDimension.ROTATION:

        if not artifact.rotation_valid:
            raise CoverageError(
                "rotation reference unavailable"
            )

    else:
        raise CoverageError(
            "unknown reference dimension"
        )


def validate_leica_reference(
    artifact: ReferenceCoverageArtifact,
):

    if artifact.reference_source.lower() == "leica":

        if artifact.rotation_valid:
            raise CoverageError(
                "Leica position reference cannot validate rotation"
            )
