from __future__ import annotations

from math import isfinite, sqrt
from pathlib import Path
from statistics import median

from .m2dgr_reference import audit_m2dgr_reference
from .reference_quality import (
    build_reference_quality_payload,
    write_immutable_reference_quality_artifact,
)


def _percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = fraction * (len(ordered) - 1)
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _read_rows(path: Path) -> tuple[tuple[float, ...], ...]:
    rows: list[tuple[float, ...]] = []

    with path.open("r", encoding="ascii", errors="strict") as handle:
        for line_number, raw in enumerate(handle, start=1):
            raw = raw.strip()
            if not raw:
                continue

            fields = raw.split()
            if len(fields) != 8:
                raise ValueError(f"{path}: line {line_number}: expected 8 fields")

            try:
                rows.append(tuple(float(value) for value in fields))
            except ValueError as exc:
                raise ValueError(
                    f"{path}: line {line_number}: non-numeric field"
                ) from exc

    return tuple(rows)


def _translation_diagnostics(
    rows: tuple[tuple[float, ...], ...],
) -> dict[str, float | None]:
    steps: list[float] = []
    speeds: list[float] = []

    for left, right in zip(rows, rows[1:]):
        left_position = left[1:4]
        right_position = right[1:4]

        if not all(isfinite(value) for value in (*left_position, *right_position)):
            continue

        distance = sqrt(
            sum(
                (right_position[index] - left_position[index]) ** 2
                for index in range(3)
            )
        )
        steps.append(distance)

        dt = right[0] - left[0]
        if dt > 0:
            speeds.append(distance / dt)

    return {
        "translation_step_median": median(steps) if steps else None,
        "translation_step_p95": _percentile(steps, 0.95),
        "translation_step_max": max(steps) if steps else None,
        "translation_speed_mps_median": median(speeds) if speeds else None,
        "translation_speed_mps_p95": _percentile(speeds, 0.95),
        "translation_speed_mps_max": max(speeds) if speeds else None,
    }


def build_m2dgr_reference_quality_payload(
    path: str | Path,
    *,
    trajectory_id: str | None = None,
    qnorm_tolerance: float = 1e-3,
) -> dict[str, object]:
    source = Path(path)
    audit = audit_m2dgr_reference(
        source,
        trajectory_id=trajectory_id,
        qnorm_tolerance=qnorm_tolerance,
    )
    rows = _read_rows(source)
    timestamps = tuple(row[0] for row in rows)

    if len(rows) != audit.row_count:
        raise RuntimeError("M2DGR structural audit row-count mismatch")

    invalid_translation = set(audit.invalid_translation_sample_indices)
    translation_mask = tuple(
        index not in invalid_translation
        for index in range(audit.row_count)
    )

    if audit.rotation_supported:
        invalid_rotation = set(audit.invalid_rotation_sample_indices)
        rotation_mask = tuple(
            index not in invalid_rotation
            for index in range(audit.row_count)
        )
    else:
        rotation_mask = None

    translation_diagnostics = _translation_diagnostics(rows)

    return build_reference_quality_payload(
        trajectory_id=audit.trajectory_id,
        reference_source=audit.family.value,
        source_relative_path=f"raw/ground_truth/{source.name}",
        source_sha256=audit.source_sha256,
        timestamps_seconds=timestamps,
        translation_valid_mask=translation_mask,
        rotation_supported=audit.rotation_supported,
        rotation_valid_mask=rotation_mask,
        timestamp_checks={
            "finite": True,
            "strictly_increasing": True,
            "min_dt_seconds": audit.min_dt_seconds,
            "median_dt_seconds": audit.median_dt_seconds,
            "max_dt_seconds": audit.max_dt_seconds,
            "gap_rejection_threshold_seconds": None,
            "gap_classification_performed": False,
        },
        continuity_checks={
            **translation_diagnostics,
            "translation_rejection_threshold": None,
            "translation_continuity_is_diagnostic_only": True,
            "rotation_step_median_deg": audit.rotation_step_median_deg,
            "rotation_step_p95_deg": audit.rotation_step_p95_deg,
            "rotation_step_max_deg": audit.rotation_step_max_deg,
            "rotation_step_rejection_threshold_deg": None,
            "rotation_continuity_is_diagnostic_only": True,
            "qnorm_tolerance": audit.qnorm_tolerance,
        },
        physical_quality_verified=False,
        physical_quality_evidence=None,
        synchronization_verified=False,
        continuous_time_coverage_verified=False,
        continuous_time_coverage_evidence=None,
    )


def audit_m2dgr_reference_directory(
    dataset_root: str | Path,
    *,
    output_root: str | Path | None = None,
    qnorm_tolerance: float = 1e-3,
) -> tuple[Path, ...]:
    root = Path(dataset_root)
    gt_root = root / "raw" / "ground_truth"

    if output_root is None:
        output = root / "audit" / "reference_quality"
    else:
        output = Path(output_root)

    sources = sorted(gt_root.glob("*.txt"))
    if not sources:
        raise FileNotFoundError(
            f"no M2DGR ground-truth files found under {gt_root}"
        )

    written: list[Path] = []

    for source in sources:
        payload = build_m2dgr_reference_quality_payload(
            source,
            trajectory_id=source.stem,
            qnorm_tolerance=qnorm_tolerance,
        )
        destination = output / f"{source.stem}_reference_quality.json"
        write_immutable_reference_quality_artifact(destination, payload)
        written.append(destination)

    return tuple(written)
