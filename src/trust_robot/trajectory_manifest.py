from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from typing import Mapping, Sequence
import json
import os
import tempfile

from .reference_coverage import (
    ReferenceCoverageArtifact,
    ValidInterval,
)

from .data_contracts import (
    CalibrationArtifactRole,
    CalibrationArtifactSpec,
    ContractError,
    DerivativeKind,
    MeasurementTimeBasis,
    ReferenceCoverage,
    ReferenceSpec,
    SplitRole,
    StreamSpec,
    SynchronizationSpec,
    TrajectoryRecord,
    VerificationStatus,
    validate_trajectory_records,
)


SCHEMA = "TRUST_ROBOT_TRAJECTORY_MANIFEST_V1"
SCHEMA_VERSION = 1


def canonical_digest(payload: object) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")

    return sha256(raw).hexdigest()


def _stream_dict(stream: StreamSpec) -> dict:
    return {
        "stream_id": stream.stream_id,
        "modality": stream.modality,
        "frame_id": stream.frame_id,
        "clock_domain": stream.clock_domain,
        "timestamp_unit": stream.timestamp_unit,
        "estimator_input": stream.estimator_input,
        "reference_only": stream.reference_only,
    }


def _reference_dict(reference: ReferenceSpec) -> dict:
    return {
        "source_id": reference.source_id,
        "frame_id": reference.frame_id,
        "coverage": reference.coverage.value,
        "supports_translation": reference.supports_translation,
        "supports_rotation": reference.supports_rotation,
        "translation_coverage": (
            reference.translation_coverage.value
            if reference.translation_coverage is not None
            else None
        ),
        "rotation_coverage": (
            reference.rotation_coverage.value
            if reference.rotation_coverage is not None
            else None
        ),
        "translation_validity_artifact": (
            reference.translation_validity_artifact
        ),
        "rotation_validity_artifact": (
            reference.rotation_validity_artifact
        ),
        "derived_from_stream_ids": list(
            reference.derived_from_stream_ids
        ),
    }


def _sync_dict(sync: SynchronizationSpec) -> dict:
    return {
        "stream_id": sync.stream_id,
        "clock_domain": sync.clock_domain,
        "verification_status": sync.verification_status.value,
        "method": sync.method,
        "tolerance_seconds": sync.tolerance_seconds,
        "measurement_time_basis": (
            sync.measurement_time_basis.value
            if sync.measurement_time_basis is not None
            else None
        ),
        "fixed_offset_seconds": sync.fixed_offset_seconds,
        "fixed_offset_method": sync.fixed_offset_method,
        "tolerance_evidence": sync.tolerance_evidence,
        "tolerance_selected_on_split": (
            sync.tolerance_selected_on_split.value
            if sync.tolerance_selected_on_split is not None
            else None
        ),
    }



def _calibration_dict(
    artifact: CalibrationArtifactSpec,
) -> dict:
    payload = {
        "artifact_id": artifact.artifact_id,
        "source_path": artifact.source_path,
        "sha256": artifact.sha256,
        "verification_status":
            artifact.verification_status.value,
        "applies_to_stream_ids":
            list(artifact.applies_to_stream_ids),
        "applies_to_frame_ids":
            list(artifact.applies_to_frame_ids),
        "notes": artifact.notes,
    }

    # Preserve the exact historical V1 representation for legacy
    # integrity-only artifacts. Role-aware calibration evidence is additive.
    if (
        artifact.role
        is not CalibrationArtifactRole.ARTIFACT_INTEGRITY
    ):
        payload[
            "role"
        ] = artifact.role.value

    return payload




def _coverage_dict(
    artifact,
):
    return {
        "trajectory_id": artifact.trajectory_id,
        "reference_source": artifact.reference_source,
        "translation_valid": artifact.translation_valid,
        "rotation_valid": artifact.rotation_valid,
        "valid_intervals": [
            {
                "start_ns": item.start_ns,
                "end_ns": item.end_ns,
            }
            for item in artifact.valid_intervals
        ],
        "reason": artifact.reason,
    }


def _record_dict(
    record: TrajectoryRecord,
    synchronization: Sequence[SynchronizationSpec],
) -> dict:
    return {
        "dataset_id": record.dataset_id,
        "trajectory_id": record.trajectory_id,
        "base_trajectory_id": record.base_trajectory_id,
        "split": record.split.value,
        "derivative_kind": record.derivative_kind.value,
        "corruption_seed": record.corruption_seed,
        "streams": [
            _stream_dict(stream)
            for stream in sorted(
                record.streams,
                key=lambda item: item.stream_id,
            )
        ],
        "references": [
            _reference_dict(reference)
            for reference in sorted(
                record.references,
                key=lambda item: item.source_id,
            )
        ],
        "calibration_artifacts": [
            _calibration_dict(item)
            for item in sorted(
                record.calibration_artifacts,
                key=lambda item: item.artifact_id,
            )
        ],
        "reference_coverage_artifacts": [
            _coverage_dict(item)
            for item in record.reference_coverage_artifacts
        ],
        "synchronization": [
            _sync_dict(sync)
            for sync in sorted(
                synchronization,
                key=lambda item: item.stream_id,
            )
        ],
    }


def _validate_sync_for_record(
    record: TrajectoryRecord,
    synchronization: Sequence[SynchronizationSpec],
) -> tuple[SynchronizationSpec, ...]:
    synchronization = tuple(synchronization)

    sync_ids = [
        sync.stream_id
        for sync in synchronization
    ]

    if len(sync_ids) != len(set(sync_ids)):
        raise ContractError(
            f"trajectory {record.trajectory_id!r} contains "
            "duplicate synchronization stream IDs"
        )

    stream_by_id = {
        stream.stream_id: stream
        for stream in record.streams
    }

    expected = set(stream_by_id)
    observed = set(sync_ids)

    if observed != expected:
        missing = sorted(
            expected - observed
        )
        extra = sorted(
            observed - expected
        )

        raise ContractError(
            f"trajectory {record.trajectory_id!r} synchronization "
            f"coverage mismatch: missing={missing!r}, extra={extra!r}"
        )

    for sync in synchronization:
        stream = stream_by_id[
            sync.stream_id
        ]

        if (
            sync.clock_domain
            != stream.clock_domain
        ):
            raise ContractError(
                f"trajectory {record.trajectory_id!r} stream "
                f"{sync.stream_id!r} clock-domain mismatch: "
                f"{sync.clock_domain!r} != "
                f"{stream.clock_domain!r}"
            )

    return synchronization


def build_trajectory_manifest(
    records: Sequence[TrajectoryRecord],
    synchronization_by_trajectory: Mapping[
        str,
        Sequence[SynchronizationSpec],
    ],
) -> dict:
    records = validate_trajectory_records(
        records
    )

    dataset_ids = {
        record.dataset_id
        for record in records
    }

    if len(dataset_ids) != 1:
        raise ContractError(
            "one trajectory manifest must contain exactly "
            "one dataset_id"
        )

    trajectory_ids = {
        record.trajectory_id
        for record in records
    }

    supplied_ids = set(
        synchronization_by_trajectory
    )

    if supplied_ids != trajectory_ids:
        missing = sorted(
            trajectory_ids - supplied_ids
        )
        extra = sorted(
            supplied_ids - trajectory_ids
        )

        raise ContractError(
            "synchronization trajectory-key mismatch: "
            f"missing={missing!r}, extra={extra!r}"
        )

    normalized_sync = {}

    for record in records:
        normalized_sync[
            record.trajectory_id
        ] = _validate_sync_for_record(
            record,
            synchronization_by_trajectory[
                record.trajectory_id
            ],
        )

    ordered_records = sorted(
        records,
        key=lambda item: item.trajectory_id,
    )

    payload = {
        "schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "dataset_id": next(
            iter(dataset_ids)
        ),
        "records": [
            _record_dict(
                record,
                normalized_sync[
                    record.trajectory_id
                ],
            )
            for record in ordered_records
        ],
    }

    payload[
        "manifest_content_sha256"
    ] = canonical_digest(
        payload
    )

    return payload


def manifest_json(
    records: Sequence[TrajectoryRecord],
    synchronization_by_trajectory: Mapping[
        str,
        Sequence[SynchronizationSpec],
    ],
) -> str:
    return json.dumps(
        build_trajectory_manifest(
            records,
            synchronization_by_trajectory,
        ),
        sort_keys=True,
        indent=2,
        allow_nan=False,
    ) + "\n"


def _require_exact_keys(
    payload: dict,
    expected: set[str],
    label: str,
) -> None:
    actual = set(payload)

    if actual != expected:
        raise ContractError(
            f"{label} keys mismatch: "
            f"missing={sorted(expected - actual)!r}, "
            f"extra={sorted(actual - expected)!r}"
        )


def _decode_stream(payload: dict) -> StreamSpec:
    _require_exact_keys(
        payload,
        {
            "stream_id",
            "modality",
            "frame_id",
            "clock_domain",
            "timestamp_unit",
            "estimator_input",
            "reference_only",
        },
        "stream",
    )

    return StreamSpec(
        **payload
    )


def _decode_reference(
    payload: dict,
) -> ReferenceSpec:
    _require_exact_keys(
        payload,
        {
            "source_id",
            "frame_id",
            "coverage",
            "supports_translation",
            "supports_rotation",
            "translation_coverage",
            "rotation_coverage",
            "translation_validity_artifact",
            "rotation_validity_artifact",
            "derived_from_stream_ids",
        },
        "reference",
    )

    translation_coverage = payload[
        "translation_coverage"
    ]

    rotation_coverage = payload[
        "rotation_coverage"
    ]

    return ReferenceSpec(
        source_id=payload[
            "source_id"
        ],
        frame_id=payload[
            "frame_id"
        ],
        coverage=ReferenceCoverage(
            payload[
                "coverage"
            ]
        ),
        supports_translation=payload[
            "supports_translation"
        ],
        supports_rotation=payload[
            "supports_rotation"
        ],
        translation_coverage=(
            ReferenceCoverage(
                translation_coverage
            )
            if translation_coverage is not None
            else None
        ),
        rotation_coverage=(
            ReferenceCoverage(
                rotation_coverage
            )
            if rotation_coverage is not None
            else None
        ),
        translation_validity_artifact=payload[
            "translation_validity_artifact"
        ],
        rotation_validity_artifact=payload[
            "rotation_validity_artifact"
        ],
        derived_from_stream_ids=tuple(
            payload[
                "derived_from_stream_ids"
            ]
        ),
    )



def _decode_calibration_artifact(
    payload: dict,
) -> CalibrationArtifactSpec:

    legacy_keys = {
        "artifact_id",
        "source_path",
        "sha256",
        "verification_status",
        "applies_to_stream_ids",
        "applies_to_frame_ids",
        "notes",
    }

    role_aware_keys = (
        legacy_keys
        | {
            "role",
        }
    )

    observed_keys = set(
        payload
    )

    if observed_keys not in (
        legacy_keys,
        role_aware_keys,
    ):
        missing = sorted(
            legacy_keys
            - observed_keys
        )

        extra = sorted(
            observed_keys
            - role_aware_keys
        )

        raise ContractError(
            "calibration_artifact has invalid keys; "
            f"missing={missing}, extra={extra}"
        )

    role = (
        CalibrationArtifactRole(
            payload[
                "role"
            ]
        )
        if "role" in payload
        else CalibrationArtifactRole.ARTIFACT_INTEGRITY
    )

    return CalibrationArtifactSpec(
        artifact_id=payload["artifact_id"],
        source_path=payload["source_path"],
        sha256=payload["sha256"],
        verification_status=VerificationStatus(
            payload["verification_status"]
        ),
        applies_to_stream_ids=tuple(
            payload["applies_to_stream_ids"]
        ),
        applies_to_frame_ids=tuple(
            payload["applies_to_frame_ids"]
        ),
        notes=payload["notes"],
        role=role,
    )



def _decode_coverage(
    payload: dict,
) -> ReferenceCoverageArtifact:

    _require_exact_keys(
        payload,
        {
            "trajectory_id",
            "reference_source",
            "translation_valid",
            "rotation_valid",
            "valid_intervals",
            "reason",
        },
        "reference coverage",
    )

    return ReferenceCoverageArtifact(
        trajectory_id=payload["trajectory_id"],
        reference_source=payload["reference_source"],
        translation_valid=payload["translation_valid"],
        rotation_valid=payload["rotation_valid"],
        valid_intervals=tuple(
            ValidInterval(
                item["start_ns"],
                item["end_ns"],
            )
            for item in payload["valid_intervals"]
        ),
        reason=payload["reason"],
    )


def _decode_sync(
    payload: dict,
) -> SynchronizationSpec:
    _require_exact_keys(
        payload,
        {
            "stream_id",
            "clock_domain",
            "verification_status",
            "method",
            "tolerance_seconds",
            "measurement_time_basis",
            "fixed_offset_seconds",
            "fixed_offset_method",
            "tolerance_evidence",
            "tolerance_selected_on_split",
        },
        "synchronization",
    )

    basis = payload[
        "measurement_time_basis"
    ]

    selected_split = payload[
        "tolerance_selected_on_split"
    ]

    return SynchronizationSpec(
        stream_id=payload[
            "stream_id"
        ],
        clock_domain=payload[
            "clock_domain"
        ],
        verification_status=VerificationStatus(
            payload[
                "verification_status"
            ]
        ),
        method=payload[
            "method"
        ],
        tolerance_seconds=payload[
            "tolerance_seconds"
        ],
        measurement_time_basis=(
            MeasurementTimeBasis(
                basis
            )
            if basis is not None
            else None
        ),
        fixed_offset_seconds=payload[
            "fixed_offset_seconds"
        ],
        fixed_offset_method=payload[
            "fixed_offset_method"
        ],
        tolerance_evidence=payload[
            "tolerance_evidence"
        ],
        tolerance_selected_on_split=(
            SplitRole(
                selected_split
            )
            if selected_split is not None
            else None
        ),
    )


def validate_manifest_payload(
    payload: dict,
) -> tuple[TrajectoryRecord, ...]:
    if not isinstance(payload, dict):
        raise ContractError(
            "manifest root must be a mapping"
        )

    _require_exact_keys(
        payload,
        {
            "schema",
            "schema_version",
            "dataset_id",
            "records",
            "manifest_content_sha256",
        },
        "manifest",
    )

    if payload[
        "schema"
    ] != SCHEMA:
        raise ContractError(
            "unexpected trajectory manifest schema"
        )

    if payload[
        "schema_version"
    ] != SCHEMA_VERSION:
        raise ContractError(
            "unexpected trajectory manifest schema_version"
        )

    stored = payload[
        "manifest_content_sha256"
    ]

    unhashed = deepcopy(
        payload
    )

    unhashed.pop(
        "manifest_content_sha256"
    )

    computed = canonical_digest(
        unhashed
    )

    if stored != computed:
        raise ContractError(
            "trajectory manifest content hash mismatch"
        )

    raw_records = payload[
        "records"
    ]

    if not isinstance(
        raw_records,
        list,
    ):
        raise ContractError(
            "manifest records must be a list"
        )

    records = []
    synchronization_by_trajectory = {}

    expected_record_keys = {
        "dataset_id",
        "trajectory_id",
        "base_trajectory_id",
        "split",
        "derivative_kind",
        "corruption_seed",
        "streams",
        "references",
        "calibration_artifacts",
        "reference_coverage_artifacts",
        "synchronization",
    }

    for raw_record in raw_records:
        if not isinstance(
            raw_record,
            dict,
        ):
            raise ContractError(
                "manifest trajectory record must be a mapping"
            )

        _require_exact_keys(
            raw_record,
            expected_record_keys,
            "trajectory record",
        )

        streams = tuple(
            _decode_stream(item)
            for item in raw_record[
                "streams"
            ]
        )

        references = tuple(
            _decode_reference(item)
            for item in raw_record[
                "references"
            ]
        )

        synchronization = tuple(
            _decode_sync(item)
            for item in raw_record[
                "synchronization"
            ]
        )

        reference_coverage_artifacts = tuple(
            _decode_coverage(item)
            for item in raw_record[
                "reference_coverage_artifacts"
            ]
        )

        calibration_artifacts = tuple(
            _decode_calibration_artifact(item)
            for item in raw_record[
                "calibration_artifacts"
            ]
        )

        record = TrajectoryRecord(
            dataset_id=raw_record[
                "dataset_id"
            ],
            trajectory_id=raw_record[
                "trajectory_id"
            ],
            base_trajectory_id=raw_record[
                "base_trajectory_id"
            ],
            split=SplitRole(
                raw_record[
                    "split"
                ]
            ),
            streams=streams,
            references=references,
            calibration_artifacts=calibration_artifacts,
            reference_coverage_artifacts=reference_coverage_artifacts,
            derivative_kind=DerivativeKind(
                raw_record[
                    "derivative_kind"
                ]
            ),
            corruption_seed=raw_record[
                "corruption_seed"
            ],
        )

        records.append(
            record
        )

        synchronization_by_trajectory[
            record.trajectory_id
        ] = synchronization

    rebuilt = build_trajectory_manifest(
        records,
        synchronization_by_trajectory,
    )

    if rebuilt != payload:
        raise ContractError(
            "manifest is valid but not in canonical "
            "TRUST-ROBOT representation"
        )

    return tuple(records)


def load_manifest(
    path: str | Path,
) -> dict:
    path = Path(path)

    payload = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    validate_manifest_payload(
        payload
    )

    return payload


def write_immutable_manifest(
    path: str | Path,
    records: Sequence[TrajectoryRecord],
    synchronization_by_trajectory: Mapping[
        str,
        Sequence[SynchronizationSpec],
    ],
) -> Path:
    path = Path(path)

    content = manifest_json(
        records,
        synchronization_by_trajectory,
    )

    if path.exists():
        existing = path.read_text(
            encoding="utf-8"
        )

        if existing != content:
            raise FileExistsError(
                "immutable TRUST-ROBOT trajectory manifest "
                f"already exists with different content: {path}"
            )

        return path

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fd, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
        text=True,
    )

    temp = Path(
        temp_name
    )

    try:
        with os.fdopen(
            fd,
            "w",
            encoding="utf-8",
        ) as handle:
            handle.write(
                content
            )

            handle.flush()
            os.fsync(
                handle.fileno()
            )

        try:
            os.link(
                temp,
                path,
            )
        except FileExistsError:
            existing = path.read_text(
                encoding="utf-8"
            )

            if existing != content:
                raise FileExistsError(
                    "immutable TRUST-ROBOT trajectory manifest "
                    "was concurrently created with "
                    f"different content: {path}"
                )

    finally:
        try:
            temp.unlink()
        except FileNotFoundError:
            pass

    return path
