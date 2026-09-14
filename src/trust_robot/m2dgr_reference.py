from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from math import acos, degrees, isfinite, sqrt
from pathlib import Path
from statistics import median


class M2DGRReferenceError(ValueError):
    """Raised when an M2DGR reference file violates a structural contract."""


class M2DGRReferenceFamily(str, Enum):
    RTK_INS = "rtk_ins"
    LEICA = "leica"
    MOCAP = "mocap"


def infer_reference_family(
    trajectory_id: str,
) -> M2DGRReferenceFamily:
    """
    Infer the released M2DGR reference family from the sequence name.

    This maps only the scenario families documented by M2DGR. It does not
    infer coordinate-frame semantics.
    """

    if not isinstance(trajectory_id, str) or not trajectory_id.strip():
        raise M2DGRReferenceError(
            "trajectory_id must be a non-empty string"
        )

    name = Path(trajectory_id).stem.lower()

    if name.startswith(
        (
            "street_",
            "circle_",
            "gate_",
            "walk_",
        )
    ):
        return M2DGRReferenceFamily.RTK_INS

    if name.startswith(
        (
            "hall_",
            "door_",
            "lift_",
        )
    ):
        return M2DGRReferenceFamily.LEICA

    if name.startswith(
        (
            "room_",
            "roomdark_",
        )
    ):
        return M2DGRReferenceFamily.MOCAP

    raise M2DGRReferenceError(
        f"unknown M2DGR trajectory family for {trajectory_id!r}"
    )


def _sha256_file(path: Path) -> str:
    digest = sha256()

    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)

            if not chunk:
                break

            digest.update(chunk)

    return digest.hexdigest()


def _percentile(
    values: list[float],
    fraction: float,
) -> float | None:
    """
    Linear-interpolated percentile used only for diagnostics.

    It is not a reference-validity rule.
    """

    if not values:
        return None

    if not 0.0 <= fraction <= 1.0:
        raise ValueError(
            "fraction must lie in [0, 1]"
        )

    ordered = sorted(values)

    if len(ordered) == 1:
        return ordered[0]

    position = fraction * (len(ordered) - 1)

    lower = int(position)
    upper = min(
        lower + 1,
        len(ordered) - 1,
    )

    weight = position - lower

    return (
        ordered[lower] * (1.0 - weight)
        + ordered[upper] * weight
    )


@dataclass(frozen=True)
class M2DGRReferenceAudit:
    trajectory_id: str
    family: M2DGRReferenceFamily
    source_sha256: str

    row_count: int

    timestamp_start: float
    timestamp_end: float

    min_dt_seconds: float | None
    median_dt_seconds: float | None
    max_dt_seconds: float | None

    translation_supported: bool
    rotation_supported: bool

    invalid_translation_sample_indices: tuple[int, ...]
    invalid_rotation_sample_indices: tuple[int, ...]

    rotation_step_median_deg: float | None
    rotation_step_p95_deg: float | None
    rotation_step_max_deg: float | None

    qnorm_tolerance: float

    @property
    def translation_valid_count(self) -> int:
        return (
            self.row_count
            - len(
                self.invalid_translation_sample_indices
            )
        )

    @property
    def rotation_valid_count(self) -> int | None:
        if not self.rotation_supported:
            return None

        return (
            self.row_count
            - len(
                self.invalid_rotation_sample_indices
            )
        )

    def to_dict(self) -> dict[str, object]:
        """
        JSON-compatible representation.

        Artifact writing is intentionally kept outside this Phase-1F-A
        structural auditor.
        """

        return {
            "trajectory_id": self.trajectory_id,
            "family": self.family.value,
            "source_sha256": self.source_sha256,
            "row_count": self.row_count,
            "timestamp_start": self.timestamp_start,
            "timestamp_end": self.timestamp_end,
            "min_dt_seconds": self.min_dt_seconds,
            "median_dt_seconds": self.median_dt_seconds,
            "max_dt_seconds": self.max_dt_seconds,
            "translation_supported": self.translation_supported,
            "rotation_supported": self.rotation_supported,
            "invalid_translation_sample_indices": list(
                self.invalid_translation_sample_indices
            ),
            "invalid_rotation_sample_indices": list(
                self.invalid_rotation_sample_indices
            ),
            "translation_valid_count": self.translation_valid_count,
            "rotation_valid_count": self.rotation_valid_count,
            "rotation_step_median_deg": self.rotation_step_median_deg,
            "rotation_step_p95_deg": self.rotation_step_p95_deg,
            "rotation_step_max_deg": self.rotation_step_max_deg,
            "qnorm_tolerance": self.qnorm_tolerance,
        }


def audit_m2dgr_reference(
    path: str | Path,
    *,
    trajectory_id: str | None = None,
    qnorm_tolerance: float = 1e-3,
) -> M2DGRReferenceAudit:
    """
    Audit one released M2DGR eight-column reference file.

    Expected columns:

        timestamp x y z qx qy qz qw

    Structural policy:

    - exactly eight numeric fields are required;
    - timestamp must be finite and strictly increasing;
    - translation validity is evaluated independently from rotation;
    - Leica rotation is unsupported rather than counted as invalid;
    - supported rotation is structurally valid only when all four
      quaternion values are finite and quaternion norm is within the
      explicit qnorm tolerance;
    - quaternion continuity statistics are diagnostic only and never
      invalidate a sample here;
    - raw source data are never normalized, changed, imputed, or written.
    """

    source = Path(path)

    if not source.is_file():
        raise M2DGRReferenceError(
            f"reference file does not exist: {source}"
        )

    if not isfinite(qnorm_tolerance) or qnorm_tolerance < 0:
        raise M2DGRReferenceError(
            "qnorm_tolerance must be finite and non-negative"
        )

    if trajectory_id is None:
        trajectory_id = source.stem

    family = infer_reference_family(
        trajectory_id
    )

    translation_supported = True
    rotation_supported = (
        family
        is not M2DGRReferenceFamily.LEICA
    )

    invalid_translation: list[int] = []
    invalid_rotation: list[int] = []

    dts: list[float] = []
    rotation_steps_deg: list[float] = []

    previous_timestamp: float | None = None

    previous_valid_q: (
        tuple[float, float, float, float]
        | None
    ) = None

    previous_valid_q_index: int | None = None

    timestamp_start: float | None = None
    timestamp_end: float | None = None

    row_count = 0

    with source.open(
        "r",
        encoding="ascii",
        errors="strict",
    ) as f:

        for source_line_number, raw in enumerate(
            f,
            start=1,
        ):
            raw = raw.strip()

            if not raw:
                continue

            fields = raw.split()

            if len(fields) != 8:
                raise M2DGRReferenceError(
                    f"{source}: line {source_line_number}: "
                    f"expected 8 fields, got {len(fields)}"
                )

            try:
                values = tuple(
                    float(value)
                    for value in fields
                )
            except ValueError as exc:
                raise M2DGRReferenceError(
                    f"{source}: line {source_line_number}: "
                    "non-numeric field"
                ) from exc

            sample_index = row_count

            timestamp = values[0]

            if not isfinite(timestamp):
                raise M2DGRReferenceError(
                    f"{source}: line {source_line_number}: "
                    "timestamp is non-finite"
                )

            if previous_timestamp is not None:
                if timestamp <= previous_timestamp:
                    raise M2DGRReferenceError(
                        f"{source}: line {source_line_number}: "
                        "timestamps are not strictly increasing"
                    )

                dts.append(
                    timestamp - previous_timestamp
                )

            if timestamp_start is None:
                timestamp_start = timestamp

            timestamp_end = timestamp
            previous_timestamp = timestamp

            x, y, z = values[1:4]

            translation_valid = all(
                isfinite(component)
                for component in (x, y, z)
            )

            if not translation_valid:
                invalid_translation.append(
                    sample_index
                )

            if rotation_supported:
                q = values[4:8]

                q_finite = all(
                    isfinite(component)
                    for component in q
                )

                q_valid = False
                q_unit: (
                    tuple[
                        float,
                        float,
                        float,
                        float,
                    ]
                    | None
                ) = None

                if q_finite:
                    qnorm = sqrt(
                        sum(
                            component * component
                            for component in q
                        )
                    )

                    if (
                        qnorm > 0.0
                        and abs(qnorm - 1.0)
                        <= qnorm_tolerance
                    ):
                        q_valid = True

                        q_unit = tuple(
                            component / qnorm
                            for component in q
                        )

                if not q_valid:
                    invalid_rotation.append(
                        sample_index
                    )

                    previous_valid_q = None
                    previous_valid_q_index = None

                else:
                    assert q_unit is not None

                    if (
                        previous_valid_q is not None
                        and previous_valid_q_index
                        == sample_index - 1
                    ):
                        dot = sum(
                            a * b
                            for a, b in zip(
                                previous_valid_q,
                                q_unit,
                            )
                        )

                        # q and -q encode the same orientation.
                        sign_invariant_dot = abs(dot)

                        sign_invariant_dot = max(
                            0.0,
                            min(
                                1.0,
                                sign_invariant_dot,
                            ),
                        )

                        angle_deg = degrees(
                            2.0
                            * acos(
                                sign_invariant_dot
                            )
                        )

                        rotation_steps_deg.append(
                            angle_deg
                        )

                    previous_valid_q = q_unit
                    previous_valid_q_index = (
                        sample_index
                    )

            row_count += 1

    if row_count == 0:
        raise M2DGRReferenceError(
            f"reference file is empty: {source}"
        )

    assert timestamp_start is not None
    assert timestamp_end is not None

    return M2DGRReferenceAudit(
        trajectory_id=trajectory_id,
        family=family,
        source_sha256=_sha256_file(source),
        row_count=row_count,
        timestamp_start=timestamp_start,
        timestamp_end=timestamp_end,
        min_dt_seconds=(
            min(dts)
            if dts
            else None
        ),
        median_dt_seconds=(
            median(dts)
            if dts
            else None
        ),
        max_dt_seconds=(
            max(dts)
            if dts
            else None
        ),
        translation_supported=translation_supported,
        rotation_supported=rotation_supported,
        invalid_translation_sample_indices=tuple(
            invalid_translation
        ),
        invalid_rotation_sample_indices=tuple(
            invalid_rotation
        ),
        rotation_step_median_deg=(
            median(rotation_steps_deg)
            if rotation_steps_deg
            else None
        ),
        rotation_step_p95_deg=_percentile(
            rotation_steps_deg,
            0.95,
        ),
        rotation_step_max_deg=(
            max(rotation_steps_deg)
            if rotation_steps_deg
            else None
        ),
        qnorm_tolerance=qnorm_tolerance,
    )


REFERENCE_VALIDITY_SCHEMA = (
    "trust_robot.m2dgr_reference_validity"
)
REFERENCE_VALIDITY_VERSION = 1


def reference_validity_artifact_dict(
    audit: M2DGRReferenceAudit,
    *,
    source_relpath: str,
) -> dict[str, object]:
    """
    Deterministic machine-readable structural validity artifact.

    This artifact records structural evidence only. It does not claim
    physical tracking quality or apply a motion-discontinuity threshold.
    """

    if (
        not isinstance(source_relpath, str)
        or not source_relpath.strip()
    ):
        raise M2DGRReferenceError(
            "source_relpath must be a non-empty string"
        )

    if Path(source_relpath).is_absolute():
        raise M2DGRReferenceError(
            "source_relpath must be repository/dataset relative"
        )

    return {
        "schema": REFERENCE_VALIDITY_SCHEMA,
        "version": REFERENCE_VALIDITY_VERSION,
        "trajectory_id": audit.trajectory_id,
        "reference_family": audit.family.value,
        "source": {
            "relative_path": source_relpath,
            "sha256": audit.source_sha256,
        },
        "policy": {
            "kind": "structural_reference_validity",
            "qnorm_tolerance": audit.qnorm_tolerance,
            "rotation_continuity_is_diagnostic_only": True,
            "raw_source_modified": False,
        },
        "samples": {
            "count": audit.row_count,
            "timestamp_start": audit.timestamp_start,
            "timestamp_end": audit.timestamp_end,
            "dt_seconds": {
                "min": audit.min_dt_seconds,
                "median": audit.median_dt_seconds,
                "max": audit.max_dt_seconds,
            },
        },
        "translation": {
            "supported": audit.translation_supported,
            "valid_count": audit.translation_valid_count,
            "invalid_sample_indices": list(
                audit.invalid_translation_sample_indices
            ),
        },
        "rotation": {
            "supported": audit.rotation_supported,
            "valid_count": audit.rotation_valid_count,
            "invalid_sample_indices": list(
                audit.invalid_rotation_sample_indices
            ),
            "step_diagnostics_deg": {
                "median": audit.rotation_step_median_deg,
                "p95": audit.rotation_step_p95_deg,
                "max": audit.rotation_step_max_deg,
            },
        },
    }


def write_reference_validity_artifact(
    audit: M2DGRReferenceAudit,
    destination: str | Path,
    *,
    source_relpath: str,
) -> Path:
    """
    Write one canonical JSON artifact atomically.
    """

    import json
    import os
    import tempfile

    destination = Path(destination)

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    payload = reference_validity_artifact_dict(
        audit,
        source_relpath=source_relpath,
    )

    serialized = (
        json.dumps(
            payload,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        + "\n"
    )

    fd, temporary_name = tempfile.mkstemp(
        prefix=destination.name + ".",
        suffix=".tmp",
        dir=destination.parent,
        text=True,
    )

    temporary = Path(temporary_name)

    try:
        with os.fdopen(
            fd,
            "w",
            encoding="utf-8",
            newline="\n",
        ) as f:
            f.write(serialized)
            f.flush()
            os.fsync(f.fileno())

        temporary.replace(
            destination
        )

    except Exception:
        temporary.unlink(
            missing_ok=True
        )
        raise

    return destination
