from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Sequence
import json
import os
import tempfile


REFERENCE_QUALITY_SCHEMA = "TRUST_ROBOT_REFERENCE_QUALITY_V1"
REFERENCE_QUALITY_VERSION = 1


class ReferenceQualityError(ValueError):
    """Raised when reference-quality evidence violates its contract."""


@dataclass(frozen=True)
class SampleRun:
    """A contiguous run in sample-index space, not a continuous-time interval."""

    start_sample_index: int
    end_sample_index: int
    start_timestamp_seconds: float
    end_timestamp_seconds: float

    def __post_init__(self) -> None:
        if self.start_sample_index < 0:
            raise ReferenceQualityError("sample run start must be non-negative")
        if self.end_sample_index < self.start_sample_index:
            raise ReferenceQualityError("sample run end precedes start")
        if self.end_timestamp_seconds < self.start_timestamp_seconds:
            raise ReferenceQualityError("sample run timestamps are reversed")

    def to_dict(self) -> dict[str, object]:
        return {
            "start_sample_index": self.start_sample_index,
            "end_sample_index": self.end_sample_index,
            "start_timestamp_seconds": self.start_timestamp_seconds,
            "end_timestamp_seconds": self.end_timestamp_seconds,
        }


def _validate_timestamps(timestamps: Sequence[float]) -> tuple[float, ...]:
    normalized = tuple(float(value) for value in timestamps)
    if not normalized:
        raise ReferenceQualityError("reference quality requires at least one sample")
    for left, right in zip(normalized, normalized[1:]):
        if right <= left:
            raise ReferenceQualityError("timestamps must be strictly increasing")
    return normalized


def _validate_mask(name: str, mask: Sequence[bool], count: int) -> tuple[bool, ...]:
    normalized = tuple(bool(value) for value in mask)
    if len(normalized) != count:
        raise ReferenceQualityError(
            f"{name} mask length {len(normalized)} does not match sample count {count}"
        )
    return normalized


def _runs(
    mask: Sequence[bool],
    timestamps: Sequence[float],
    target: bool,
) -> tuple[SampleRun, ...]:
    result: list[SampleRun] = []
    start: int | None = None

    for index, value in enumerate(mask):
        if value == target and start is None:
            start = index

        is_last = index == len(mask) - 1
        if start is not None and (value != target or is_last):
            end = index if value == target and is_last else index - 1
            result.append(
                SampleRun(
                    start_sample_index=start,
                    end_sample_index=end,
                    start_timestamp_seconds=timestamps[start],
                    end_timestamp_seconds=timestamps[end],
                )
            )
            start = None

    return tuple(result)


def _dimension_payload(
    *,
    supported: bool,
    mask: Sequence[bool] | None,
    timestamps: Sequence[float],
) -> dict[str, object]:
    if not supported:
        if mask is not None:
            raise ReferenceQualityError(
                "unsupported dimension cannot carry a validity mask"
            )
        return {
            "supported": False,
            "valid_count": None,
            "invalid_count": None,
            "valid_sample_runs": [],
            "invalid_sample_runs": [],
        }

    if mask is None:
        raise ReferenceQualityError("supported dimension requires a validity mask")

    normalized = _validate_mask("dimension", mask, len(timestamps))
    valid_count = sum(normalized)

    return {
        "supported": True,
        "valid_count": valid_count,
        "invalid_count": len(normalized) - valid_count,
        "valid_sample_runs": [
            run.to_dict() for run in _runs(normalized, timestamps, True)
        ],
        "invalid_sample_runs": [
            run.to_dict() for run in _runs(normalized, timestamps, False)
        ],
    }


def _canonical_digest_payload(payload: dict[str, object]) -> str:
    unhashed = deepcopy(payload)
    unhashed.pop("reference_quality_content_sha256", None)
    raw = json.dumps(
        unhashed,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return sha256(raw).hexdigest()


def build_reference_quality_payload(
    *,
    trajectory_id: str,
    reference_source: str,
    source_relative_path: str,
    source_sha256: str,
    timestamps_seconds: Sequence[float],
    translation_valid_mask: Sequence[bool],
    rotation_supported: bool,
    rotation_valid_mask: Sequence[bool] | None,
    timestamp_checks: dict[str, object],
    continuity_checks: dict[str, object],
    physical_quality_verified: bool = False,
    physical_quality_evidence: str | None = None,
    synchronization_verified: bool = False,
    continuous_time_coverage_verified: bool = False,
    continuous_time_coverage_evidence: str | None = None,
) -> dict[str, object]:
    """Build a deterministic, conservative reference-quality artifact.

    Sample runs describe structural validity of observations. They MUST NOT be
    interpreted as permission to interpolate between their endpoint timestamps.
    Continuous-time coverage and measurement association are separate evidence.
    """

    if not trajectory_id.strip() or not reference_source.strip():
        raise ReferenceQualityError(
            "trajectory_id and reference_source are required"
        )

    if Path(source_relative_path).is_absolute() or not source_relative_path.strip():
        raise ReferenceQualityError(
            "source_relative_path must be non-empty and relative"
        )

    if len(source_sha256) != 64:
        raise ReferenceQualityError("source_sha256 must be a SHA256 hex digest")
    try:
        int(source_sha256, 16)
    except ValueError as exc:
        raise ReferenceQualityError("source_sha256 must be hexadecimal") from exc

    if physical_quality_verified and not physical_quality_evidence:
        raise ReferenceQualityError(
            "physical_quality_verified requires explicit evidence"
        )

    if continuous_time_coverage_verified and not continuous_time_coverage_evidence:
        raise ReferenceQualityError(
            "continuous_time_coverage_verified requires explicit evidence"
        )

    timestamps = _validate_timestamps(timestamps_seconds)
    translation_mask = _validate_mask(
        "translation_valid",
        translation_valid_mask,
        len(timestamps),
    )

    translation = _dimension_payload(
        supported=True,
        mask=translation_mask,
        timestamps=timestamps,
    )
    rotation = _dimension_payload(
        supported=rotation_supported,
        mask=rotation_valid_mask,
        timestamps=timestamps,
    )

    blockers: list[str] = []

    if not physical_quality_verified:
        blockers.append("physical_reference_quality_not_independently_verified")
    if not synchronization_verified:
        blockers.append("reference_to_estimator_synchronization_not_verified")
    if not continuous_time_coverage_verified:
        blockers.append("continuous_time_reference_coverage_not_verified")
    if translation["invalid_count"]:
        blockers.append("translation_contains_structurally_invalid_samples")
    if rotation_supported and rotation["invalid_count"]:
        blockers.append("rotation_contains_structurally_invalid_samples")

    payload: dict[str, object] = {
        "schema": REFERENCE_QUALITY_SCHEMA,
        "schema_version": REFERENCE_QUALITY_VERSION,
        "trajectory_id": trajectory_id,
        "reference_source": reference_source,
        "source": {
            "relative_path": source_relative_path,
            "sha256": source_sha256.lower(),
        },
        "sample_run_semantics": (
            "contiguous sample-index runs only; endpoint timestamps do not imply "
            "valid interpolation, association, or continuous-time coverage"
        ),
        "sample_count": len(timestamps),
        "timestamp_start_seconds": timestamps[0],
        "timestamp_end_seconds": timestamps[-1],
        "translation_validity": translation,
        "rotation_validity": rotation,
        "timestamp_checks": dict(timestamp_checks),
        "continuity_checks": dict(continuity_checks),
        "continuous_time_coverage": {
            "verified": continuous_time_coverage_verified,
            "evidence": continuous_time_coverage_evidence,
        },
        "quality_summary": {
            "structural_quality_audited": True,
            "physical_quality_verified": physical_quality_verified,
            "physical_quality_evidence": physical_quality_evidence,
            "synchronization_verified": synchronization_verified,
            "evaluation_ready": not blockers,
            "subset_evaluation_requires_explicit_mask_and_association_policy": True,
            "blockers": blockers,
        },
    }

    payload["reference_quality_content_sha256"] = _canonical_digest_payload(payload)
    return payload


def reference_quality_sha256(payload: dict[str, object]) -> str:
    """Digest the logical artifact content, excluding its stored digest field."""

    return _canonical_digest_payload(payload)


def validate_reference_quality_payload(payload: dict[str, object]) -> None:
    if not isinstance(payload, dict):
        raise ReferenceQualityError("reference-quality artifact root must be a mapping")

    expected_root = {
        "schema",
        "schema_version",
        "trajectory_id",
        "reference_source",
        "source",
        "sample_run_semantics",
        "sample_count",
        "timestamp_start_seconds",
        "timestamp_end_seconds",
        "translation_validity",
        "rotation_validity",
        "timestamp_checks",
        "continuity_checks",
        "continuous_time_coverage",
        "quality_summary",
        "reference_quality_content_sha256",
    }

    actual_root = set(payload)
    if actual_root != expected_root:
        raise ReferenceQualityError(
            "reference-quality root keys mismatch: "
            f"missing={sorted(expected_root - actual_root)!r}, "
            f"extra={sorted(actual_root - expected_root)!r}"
        )

    if payload["schema"] != REFERENCE_QUALITY_SCHEMA:
        raise ReferenceQualityError("unexpected reference-quality schema")
    if payload["schema_version"] != REFERENCE_QUALITY_VERSION:
        raise ReferenceQualityError("unexpected reference-quality schema_version")

    stored_digest = payload["reference_quality_content_sha256"]
    if stored_digest != _canonical_digest_payload(payload):
        raise ReferenceQualityError("reference-quality content hash mismatch")

    if not isinstance(payload["sample_count"], int) or payload["sample_count"] <= 0:
        raise ReferenceQualityError("sample_count must be a positive integer")

    source = payload["source"]
    if not isinstance(source, dict) or set(source) != {"relative_path", "sha256"}:
        raise ReferenceQualityError("invalid reference-quality source block")

    relative_path = source["relative_path"]
    if not isinstance(relative_path, str) or not relative_path.strip():
        raise ReferenceQualityError("source relative_path must be non-empty")
    if Path(relative_path).is_absolute():
        raise ReferenceQualityError("source relative_path must be relative")

    source_sha = source["sha256"]
    if not isinstance(source_sha, str) or len(source_sha) != 64:
        raise ReferenceQualityError("source sha256 must be a SHA256 digest")
    try:
        int(source_sha, 16)
    except ValueError as exc:
        raise ReferenceQualityError("source sha256 must be hexadecimal") from exc

    sample_count = payload["sample_count"]
    for name in ("translation_validity", "rotation_validity"):
        dimension = payload[name]
        if not isinstance(dimension, dict):
            raise ReferenceQualityError(f"{name} must be a mapping")

        expected_dimension = {
            "supported",
            "valid_count",
            "invalid_count",
            "valid_sample_runs",
            "invalid_sample_runs",
        }
        if set(dimension) != expected_dimension:
            raise ReferenceQualityError(f"{name} keys mismatch")

        if dimension["supported"]:
            valid_count = dimension["valid_count"]
            invalid_count = dimension["invalid_count"]
            if not isinstance(valid_count, int) or not isinstance(invalid_count, int):
                raise ReferenceQualityError(f"{name} counts must be integers")
            if valid_count < 0 or invalid_count < 0:
                raise ReferenceQualityError(f"{name} counts must be non-negative")
            if valid_count + invalid_count != sample_count:
                raise ReferenceQualityError(
                    f"{name} counts do not sum to sample_count"
                )
        else:
            if dimension["valid_count"] is not None or dimension["invalid_count"] is not None:
                raise ReferenceQualityError(
                    f"unsupported {name} must not carry counts"
                )
            if dimension["valid_sample_runs"] or dimension["invalid_sample_runs"]:
                raise ReferenceQualityError(
                    f"unsupported {name} must not carry sample runs"
                )

    coverage = payload["continuous_time_coverage"]
    if not isinstance(coverage, dict) or set(coverage) != {"verified", "evidence"}:
        raise ReferenceQualityError("invalid continuous_time_coverage block")
    if coverage["verified"] and not coverage["evidence"]:
        raise ReferenceQualityError(
            "verified continuous-time coverage requires evidence"
        )

    quality = payload["quality_summary"]
    if not isinstance(quality, dict):
        raise ReferenceQualityError("quality_summary must be a mapping")
    if quality.get("evaluation_ready") != (not quality.get("blockers")):
        raise ReferenceQualityError(
            "evaluation_ready must agree with the blocker set"
        )


def canonical_reference_quality_json(payload: dict[str, object]) -> str:
    validate_reference_quality_payload(payload)
    return json.dumps(payload, sort_keys=True, indent=2, allow_nan=False) + "\n"


def load_reference_quality_artifact(path: str | Path) -> dict[str, object]:
    source = Path(path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    validate_reference_quality_payload(payload)
    return payload


def write_immutable_reference_quality_artifact(
    path: str | Path,
    payload: dict[str, object],
) -> Path:
    destination = Path(path)
    content = canonical_reference_quality_json(payload)

    if destination.exists():
        if destination.read_text(encoding="utf-8") != content:
            raise FileExistsError(
                "immutable reference-quality artifact already exists with "
                f"different content: {destination}"
            )
        return destination

    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{destination.name}.",
        suffix=".tmp",
        dir=destination.parent,
        text=True,
    )
    temp = Path(temp_name)

    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())

        try:
            os.link(temp, destination)
        except FileExistsError:
            if destination.read_text(encoding="utf-8") != content:
                raise
    finally:
        temp.unlink(missing_ok=True)

    return destination
