from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .reference_coverage import (
    ReferenceCoverageArtifact,
)
from typing import Iterable


class ContractError(ValueError):
    """Raised when a Phase-1 TRUST-ROBOT data invariant is violated."""


class VerificationStatus(str, Enum):
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    CONDITIONAL = "conditional"
    NOT_APPLICABLE = "not_applicable"


class ReferenceCoverage(str, Enum):
    FULL = "full"
    PARTIAL = "partial"
    ENDPOINT_ONLY = "endpoint_only"
    UNKNOWN = "unknown"


class SplitRole(str, Enum):
    TRAIN = "train"
    VALIDATION_CALIBRATION = "validation_calibration"
    CONFIRMATION_TEST = "confirmation_test"


class MeasurementTimeBasis(str, Enum):
    SENSOR_HEADER_STAMP = "sensor_header_stamp"
    BAG_RECORD_TIME = "bag_record_time"
    DATASET_NATIVE = "dataset_native"


class DerivativeKind(str, Enum):
    CLEAN = "clean"
    CORRUPTED = "corrupted"
    NATURAL = "natural"


def _require_text(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{name} must be a non-empty string")


@dataclass(frozen=True)
class StreamSpec:
    """Describe one data stream.

    ``clock_domain`` is a nominal timestamp-domain label. Equality of this
    label across streams MUST NOT be interpreted as synchronization or proof
    of a shared physical oscillator. SynchronizationSpec.verification_status
    and its evidence are authoritative for synchronization claims.
    """

    stream_id: str
    modality: str
    frame_id: str
    clock_domain: str
    timestamp_unit: str
    estimator_input: bool = False
    reference_only: bool = False

    def __post_init__(self) -> None:
        for name in (
            "stream_id",
            "modality",
            "frame_id",
            "clock_domain",
            "timestamp_unit",
        ):
            _require_text(name, getattr(self, name))

        if self.estimator_input and self.reference_only:
            raise ContractError(
                f"stream {self.stream_id!r} cannot be both an evaluated "
                "estimator input and reference-only"
            )


@dataclass(frozen=True)
class ReferenceSpec:
    source_id: str
    frame_id: str
    coverage: ReferenceCoverage
    supports_translation: bool
    supports_rotation: bool
    translation_coverage: ReferenceCoverage | None = None
    rotation_coverage: ReferenceCoverage | None = None
    translation_validity_artifact: str | None = None
    rotation_validity_artifact: str | None = None
    derived_from_stream_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_text("source_id", self.source_id)
        _require_text("frame_id", self.frame_id)

        object.__setattr__(
            self,
            "coverage",
            ReferenceCoverage(self.coverage),
        )

        object.__setattr__(
            self,
            "derived_from_stream_ids",
            tuple(self.derived_from_stream_ids),
        )

        if not (self.supports_translation or self.supports_rotation):
            raise ContractError(
                f"reference {self.source_id!r} supports neither translation "
                "nor rotation"
            )

        for dimension, supported in (
            ("translation", self.supports_translation),
            ("rotation", self.supports_rotation),
        ):
            coverage_name = f"{dimension}_coverage"
            artifact_name = f"{dimension}_validity_artifact"

            dimension_coverage = getattr(
                self,
                coverage_name,
            )
            validity_artifact = getattr(
                self,
                artifact_name,
            )

            if not supported:
                if (
                    dimension_coverage is not None
                    or validity_artifact is not None
                ):
                    raise ContractError(
                        f"reference {self.source_id!r} declares "
                        f"{dimension} validity metadata although "
                        f"{dimension} is unsupported"
                    )
                continue

            if dimension_coverage is None:
                dimension_coverage = self.coverage

            dimension_coverage = ReferenceCoverage(
                dimension_coverage
            )

            object.__setattr__(
                self,
                coverage_name,
                dimension_coverage,
            )

            if validity_artifact is not None:
                _require_text(
                    artifact_name,
                    validity_artifact,
                )

            if dimension_coverage in (
                ReferenceCoverage.PARTIAL,
                ReferenceCoverage.ENDPOINT_ONLY,
            ):
                if validity_artifact is None:
                    raise ContractError(
                        f"reference {self.source_id!r} has "
                        f"{dimension} coverage "
                        f"{dimension_coverage.value!r} but no "
                        f"machine-readable validity artifact"
                    )

        for stream_id in self.derived_from_stream_ids:
            _require_text(
                "derived_from_stream_id",
                stream_id,
            )


@dataclass(frozen=True)
class FrameSpec:
    frame_id: str
    parent_frame_id: str | None
    verification_status: VerificationStatus
    transform_source: str | None = None

    def __post_init__(self) -> None:
        _require_text("frame_id", self.frame_id)
        object.__setattr__(
            self,
            "verification_status",
            VerificationStatus(self.verification_status),
        )

        if self.parent_frame_id is not None:
            _require_text("parent_frame_id", self.parent_frame_id)
            if self.parent_frame_id == self.frame_id:
                raise ContractError("a frame cannot be its own parent")

        if self.verification_status is VerificationStatus.VERIFIED:
            if self.parent_frame_id is not None:
                if not self.transform_source or not self.transform_source.strip():
                    raise ContractError(
                        f"verified frame {self.frame_id!r} requires "
                        "transform_source provenance"
                    )


@dataclass(frozen=True)
class SynchronizationSpec:
    """Record synchronization evidence and decisions for one stream.

    A matching ``clock_domain`` string is not itself evidence that two streams
    share a physical clock or synchronized capture time.
    """

    stream_id: str
    clock_domain: str
    verification_status: VerificationStatus
    method: str | None = None
    tolerance_seconds: float | None = None
    measurement_time_basis: MeasurementTimeBasis | None = None
    fixed_offset_seconds: float | None = None
    fixed_offset_method: str | None = None
    tolerance_evidence: str | None = None
    tolerance_selected_on_split: SplitRole | None = None

    def __post_init__(self) -> None:
        _require_text("stream_id", self.stream_id)
        _require_text("clock_domain", self.clock_domain)

        object.__setattr__(
            self,
            "verification_status",
            VerificationStatus(self.verification_status),
        )

        if self.measurement_time_basis is not None:
            object.__setattr__(
                self,
                "measurement_time_basis",
                MeasurementTimeBasis(self.measurement_time_basis),
            )

        if self.tolerance_selected_on_split is not None:
            object.__setattr__(
                self,
                "tolerance_selected_on_split",
                SplitRole(self.tolerance_selected_on_split),
            )

        if self.verification_status is VerificationStatus.VERIFIED:
            if not self.method or not self.method.strip():
                raise ContractError(
                    f"verified synchronization for {self.stream_id!r} "
                    "requires an explicit method/evidence description"
                )

            if self.measurement_time_basis is None:
                raise ContractError(
                    f"verified synchronization for {self.stream_id!r} "
                    "requires an explicit measurement_time_basis"
                )

        if self.fixed_offset_seconds is not None:
            if not self.fixed_offset_method or not self.fixed_offset_method.strip():
                raise ContractError(
                    "fixed_offset_seconds requires explicit "
                    "fixed_offset_method evidence"
                )

        elif self.fixed_offset_method is not None:
            raise ContractError(
                "fixed_offset_method cannot be declared when "
                "fixed_offset_seconds is unset"
            )

        if self.tolerance_seconds is not None:
            if self.tolerance_seconds < 0:
                raise ContractError(
                    "tolerance_seconds must be non-negative"
                )

            if not self.tolerance_evidence or not self.tolerance_evidence.strip():
                raise ContractError(
                    "tolerance_seconds requires explicit "
                    "tolerance_evidence"
                )

        else:
            if self.tolerance_evidence is not None:
                raise ContractError(
                    "tolerance_evidence cannot be declared when "
                    "tolerance_seconds is unset"
                )

            if self.tolerance_selected_on_split is not None:
                raise ContractError(
                    "tolerance_selected_on_split cannot be declared "
                    "when tolerance_seconds is unset"
                )

        if (
            self.tolerance_selected_on_split is not None
            and self.tolerance_selected_on_split
            is not SplitRole.VALIDATION_CALIBRATION
        ):
            raise ContractError(
                "data-selected synchronization tolerance must be "
                "selected only on validation_calibration data"
            )


@dataclass(frozen=True)
class DatasetReadiness:
    dataset_id: str
    local_path_configured: bool = False
    file_integrity_verified: bool = False
    required_streams_verified: bool = False
    timestamps_verified: bool = False
    calibration_verified: bool = False
    synchronization_verified: bool = False
    reference_coverage_verified: bool = False
    reference_input_independence_verified: bool = False
    trajectory_identity_verified: bool = False

    def __post_init__(self) -> None:
        _require_text("dataset_id", self.dataset_id)

    @property
    def ready_for_use(self) -> bool:
        return all(
            (
                self.local_path_configured,
                self.file_integrity_verified,
                self.required_streams_verified,
                self.timestamps_verified,
                self.calibration_verified,
                self.synchronization_verified,
                self.reference_coverage_verified,
                self.reference_input_independence_verified,
                self.trajectory_identity_verified,
            )
        )



@dataclass(frozen=True)
class CalibrationArtifactSpec:
    artifact_id: str
    source_path: str
    sha256: str
    verification_status: VerificationStatus
    applies_to_stream_ids: tuple[str, ...] = ()
    applies_to_frame_ids: tuple[str, ...] = ()
    notes: str | None = None

    def __post_init__(self):

        if not self.artifact_id:
            raise ContractError(
                "calibration artifact requires artifact_id"
            )

        if not self.source_path:
            raise ContractError(
                "calibration artifact requires source_path"
            )

        if self.source_path.startswith("/"):
            raise ContractError(
                "calibration artifact path must be relative"
            )

        if not self.sha256:
            raise ContractError(
                "calibration artifact requires sha256"
            )

        if (
            self.verification_status
            == VerificationStatus.VERIFIED
            and not self.artifact_id
        ):
            raise ContractError(
                "verified calibration requires provenance"
            )


@dataclass(frozen=True)
class TrajectoryRecord:
    dataset_id: str
    trajectory_id: str
    base_trajectory_id: str
    split: SplitRole
    streams: tuple[StreamSpec, ...]
    references: tuple[ReferenceSpec, ...]
    calibration_artifacts: tuple[CalibrationArtifactSpec, ...] = ()
    reference_coverage_artifacts: tuple[ReferenceCoverageArtifact, ...] = ()
    derivative_kind: DerivativeKind = DerivativeKind.CLEAN
    corruption_seed: int | None = None

    def __post_init__(self) -> None:
        for name in ("dataset_id", "trajectory_id", "base_trajectory_id"):
            _require_text(name, getattr(self, name))

        object.__setattr__(self, "split", SplitRole(self.split))
        object.__setattr__(
            self,
            "derivative_kind",
            DerivativeKind(self.derivative_kind),
        )
        object.__setattr__(self, "streams", tuple(self.streams))
        object.__setattr__(self, "references", tuple(self.references))
        object.__setattr__(
            self,
            "reference_coverage_artifacts",
            tuple(self.reference_coverage_artifacts),
        )

        stream_ids = [stream.stream_id for stream in self.streams]
        if len(stream_ids) != len(set(stream_ids)):
            raise ContractError(
                f"trajectory {self.trajectory_id!r} contains duplicate stream IDs"
            )

        reference_ids = [reference.source_id for reference in self.references]
        if len(reference_ids) != len(set(reference_ids)):
            raise ContractError(
                f"trajectory {self.trajectory_id!r} contains duplicate reference IDs"
            )

        if self.derivative_kind is DerivativeKind.CORRUPTED:
            if self.corruption_seed is None:
                raise ContractError(
                    "corrupted derivative requires an explicit corruption_seed"
                )
        elif self.corruption_seed is not None:
            raise ContractError(
                "corruption_seed is only valid for corrupted derivatives"
            )

        input_stream_ids = {
            stream.stream_id
            for stream in self.streams
            if stream.estimator_input
        }

        for reference in self.references:
            overlap = input_stream_ids.intersection(
                reference.derived_from_stream_ids
            )
            if overlap:
                raise ContractError(
                    "reference/input leakage in trajectory "
                    f"{self.trajectory_id!r}: reference "
                    f"{reference.source_id!r} derives from evaluated input "
                    f"stream(s) {sorted(overlap)!r}"
                )


def validate_trajectory_records(
    records: Iterable[TrajectoryRecord],
) -> tuple[TrajectoryRecord, ...]:
    """Validate split, lineage, seed, and identity invariants as a set."""

    records = tuple(records)
    if not records:
        raise ContractError("at least one trajectory record is required")

    trajectory_ids: set[tuple[str, str]] = set()
    split_by_base: dict[tuple[str, str], SplitRole] = {}
    split_by_corruption_seed: dict[int, SplitRole] = {}

    for record in records:
        trajectory_key = (record.dataset_id, record.trajectory_id)
        if trajectory_key in trajectory_ids:
            raise ContractError(
                f"duplicate trajectory record {trajectory_key!r}"
            )
        trajectory_ids.add(trajectory_key)

        base_key = (record.dataset_id, record.base_trajectory_id)
        previous_split = split_by_base.get(base_key)
        if previous_split is None:
            split_by_base[base_key] = record.split
        elif previous_split is not record.split:
            raise ContractError(
                "base trajectory derivatives cross split boundaries: "
                f"{base_key!r} appears in {previous_split.value!r} and "
                f"{record.split.value!r}"
            )

        if record.corruption_seed is not None:
            previous_seed_split = split_by_corruption_seed.get(
                record.corruption_seed
            )
            if previous_seed_split is None:
                split_by_corruption_seed[record.corruption_seed] = record.split
            elif previous_seed_split is not record.split:
                raise ContractError(
                    f"corruption seed {record.corruption_seed} is reused "
                    f"across {previous_seed_split.value!r} and "
                    f"{record.split.value!r}"
                )

    return records
