from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from pathlib import Path

from .data_contracts import (
    CalibrationArtifactSpec,
    MeasurementTimeBasis,
    ReferenceCoverage,
    ReferenceSpec,
    SplitRole,
    StreamSpec,
    SynchronizationSpec,
    TrajectoryRecord,
    VerificationStatus,
)
from .m2dgr_reference import (
    M2DGRReferenceFamily,
    infer_reference_family,
)
from .m2dgr_timing_evidence import (
    available_stream_ids,
    load_m2dgr_stream_timing_for_trajectory,
    timing_artifact_path,
)
from .m2dgr_synchronization_evidence import (
    CONSERVATIVE_CLOCK_DOMAINS,
    validate_m2dgr_synchronization_evidence,
)
from .reference_quality import (
    load_reference_quality_artifact,
)
from .trajectory_manifest import (
    canonical_digest,
    validate_manifest_payload,
    write_immutable_manifest,
)


DATASET_ID = "M2DGR"


def sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def discover_trajectories(root: Path) -> list[str]:
    bags = sorted((root / "raw" / "rosbags").glob("*.bag"))
    return [bag.stem for bag in bags]


def build_streams() -> tuple[StreamSpec, ...]:
    """Return the M2DGR candidate stream catalog."""
    return (
        StreamSpec(
            stream_id="/handsfree/imu",
            modality="imu",
            frame_id="base_link",
            clock_domain="sensor_clock",
            timestamp_unit="nanoseconds",
            estimator_input=True,
            reference_only=False,
        ),
        StreamSpec(
            stream_id="/camera/imu",
            modality="imu",
            frame_id="camera_imu_optical_frame",
            clock_domain="sensor_clock",
            timestamp_unit="nanoseconds",
            estimator_input=True,
            reference_only=False,
        ),
        StreamSpec(
            stream_id="/velodyne_points",
            modality="lidar",
            frame_id="velodyne",
            clock_domain="sensor_clock",
            timestamp_unit="nanoseconds",
            estimator_input=True,
            reference_only=False,
        ),
        StreamSpec(
            stream_id="/camera/color/image_raw/compressed",
            modality="camera",
            frame_id="camera_color_optical_frame",
            clock_domain="sensor_clock",
            timestamp_unit="nanoseconds",
            estimator_input=True,
            reference_only=False,
        ),
    )


def build_streams_for_trajectory(
    dataset_root: Path,
    trajectory_id: str,
) -> tuple[StreamSpec, ...]:
    """Admit only streams observed in the Phase-3 header-timing audit."""
    timing = load_m2dgr_stream_timing_for_trajectory(
        dataset_root,
        trajectory_id,
    )
    available = set(available_stream_ids(timing))

    streams = tuple(
        stream
        for stream in build_streams()
        if stream.stream_id in available
    )
    if not streams:
        raise ValueError(
            f"M2DGR trajectory {trajectory_id!r} has no "
            "admissible estimator streams"
        )
    return streams


def build_synchronization_for_trajectory(
    dataset_root: Path,
    trajectory_id: str,
    streams: tuple[StreamSpec, ...],
) -> tuple[SynchronizationSpec, ...]:
    """Record the observed measurement-time basis without verifying sync."""
    timing_path = timing_artifact_path(
        dataset_root,
        trajectory_id,
    )
    timing = load_m2dgr_stream_timing_for_trajectory(
        dataset_root,
        trajectory_id,
    )

    admitted = {stream.stream_id for stream in streams}
    observed = set(available_stream_ids(timing))
    if admitted != observed:
        raise ValueError(
            f"{trajectory_id!r} synchronization stream set does not "
            "match the audited stream inventory"
        )

    evidence_relpath = (
        timing_path.relative_to(dataset_root).as_posix()
    )
    method = (
        "Phase-3 sensor-header timing characterization from "
        f"{evidence_relpath}; measurement-time basis observed, "
        "cross-stream synchronization not yet verified"
    )

    return tuple(
        SynchronizationSpec(
            stream_id=stream.stream_id,
            clock_domain=stream.clock_domain,
            verification_status=VerificationStatus.UNVERIFIED,
            method=method,
            measurement_time_basis=(
                MeasurementTimeBasis.SENSOR_HEADER_STAMP
            ),
            tolerance_seconds=None,
            fixed_offset_seconds=None,
            fixed_offset_method=None,
            tolerance_evidence=None,
            tolerance_selected_on_split=None,
        )
        for stream in streams
    )


def _quality_artifact_path(
    dataset_root: Path,
    trajectory_id: str,
) -> Path:
    return (
        dataset_root
        / "audit"
        / "reference_quality"
        / f"{trajectory_id}_reference_quality.json"
    )


def build_reference(
    dataset_root: Path,
    gt_path: Path,
    trajectory_id: str,
) -> ReferenceSpec:
    """Build an M2DGR reference spec from validated audit evidence."""
    family = infer_reference_family(trajectory_id)
    quality_path = _quality_artifact_path(
        dataset_root,
        trajectory_id,
    )

    if not quality_path.is_file():
        raise FileNotFoundError(
            "M2DGR reference-quality artifact is required before manifest "
            f"admission: {quality_path}"
        )

    quality = load_reference_quality_artifact(quality_path)
    if quality["trajectory_id"] != trajectory_id:
        raise ValueError(
            f"reference-quality trajectory mismatch for {trajectory_id!r}"
        )
    if quality["reference_source"] != family.value:
        raise ValueError(
            f"reference-quality family mismatch for {trajectory_id!r}"
        )

    expected_source_relpath = (
        gt_path.relative_to(dataset_root).as_posix()
    )
    source = quality["source"]
    if source["relative_path"] != expected_source_relpath:
        raise ValueError(
            f"reference-quality source-path mismatch for {trajectory_id!r}"
        )
    if source["sha256"] != sha256_file(gt_path):
        raise ValueError(
            f"reference-quality source hash mismatch for {trajectory_id!r}"
        )

    quality_relpath = (
        quality_path.relative_to(dataset_root).as_posix()
    )
    supports_rotation = (
        family is not M2DGRReferenceFamily.LEICA
    )

    return ReferenceSpec(
        source_id=f"{trajectory_id}_reference",
        frame_id="unknown",
        coverage=ReferenceCoverage.UNKNOWN,
        supports_translation=True,
        supports_rotation=supports_rotation,
        translation_coverage=ReferenceCoverage.UNKNOWN,
        rotation_coverage=(
            ReferenceCoverage.UNKNOWN
            if supports_rotation
            else None
        ),
        translation_validity_artifact=quality_relpath,
        rotation_validity_artifact=(
            quality_relpath
            if supports_rotation
            else None
        ),
        derived_from_stream_ids=(),
    )



def _stream_dict(
    stream: StreamSpec,
) -> dict:
    return {
        "stream_id": stream.stream_id,
        "modality": stream.modality,
        "frame_id": stream.frame_id,
        "clock_domain": stream.clock_domain,
        "timestamp_unit": stream.timestamp_unit,
        "estimator_input": stream.estimator_input,
        "reference_only": stream.reference_only,
    }


def _sync_dict(
    sync: SynchronizationSpec,
) -> dict:
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


def build_phase3_timing_successor_payload(
    dataset_root: str | Path,
    phase2_payload: dict,
) -> dict:
    """Migrate an audited Phase-2 M2DGR manifest using Phase-3 timing evidence.

    This migration is metadata-only. It does not read bag payloads, select a
    synchronization tolerance, estimate a fixed offset, create an exclusion
    rule, or mark synchronization verified.
    """

    dataset_root = Path(
        dataset_root
    )

    # Require the source manifest to be valid in the current manifest schema
    # before using it as migration input.
    validate_manifest_payload(
        phase2_payload
    )

    if phase2_payload[
        "dataset_id"
    ] != DATASET_ID:
        raise ValueError(
            "Phase-3 M2DGR successor requires an M2DGR source manifest"
        )

    new = deepcopy(
        phase2_payload
    )

    old_by_id = {
        record["trajectory_id"]: record
        for record in phase2_payload[
            "records"
        ]
    }

    unchanged_fields = (
        "dataset_id",
        "trajectory_id",
        "base_trajectory_id",
        "split",
        "derivative_kind",
        "corruption_seed",
        "references",
        "calibration_artifacts",
        "reference_coverage_artifacts",
    )

    for record in new[
        "records"
    ]:
        trajectory_id = record[
            "trajectory_id"
        ]

        old_record = old_by_id[
            trajectory_id
        ]

        streams = build_streams_for_trajectory(
            dataset_root,
            trajectory_id,
        )

        expected_streams = {
            stream.stream_id:
                _stream_dict(
                    stream
                )
            for stream in streams
        }

        old_streams = {
            stream["stream_id"]:
                stream
            for stream in old_record[
                "streams"
            ]
        }

        for stream_id, expected in (
            expected_streams.items()
        ):
            if stream_id not in old_streams:
                raise ValueError(
                    f"{trajectory_id!r}: audited stream "
                    f"{stream_id!r} is absent from the source manifest"
                )

            if old_streams[
                stream_id
            ] != expected:
                raise ValueError(
                    f"{trajectory_id!r}: stream metadata changed "
                    f"unexpectedly for {stream_id!r}"
                )

        admitted_ids = set(
            expected_streams
        )

        record[
            "streams"
        ] = [
            stream
            for stream in old_record[
                "streams"
            ]
            if stream[
                "stream_id"
            ] in admitted_ids
        ]

        synchronization = (
            build_synchronization_for_trajectory(
                dataset_root,
                trajectory_id,
                streams,
            )
        )

        record[
            "synchronization"
        ] = [
            _sync_dict(
                item
            )
            for item in sorted(
                synchronization,
                key=lambda item:
                    item.stream_id,
            )
        ]

        for field in unchanged_fields:
            if (
                record[field]
                != old_record[field]
            ):
                raise ValueError(
                    f"{trajectory_id!r}: Phase-3 migration "
                    f"unexpectedly changed {field!r}"
                )

    new.pop(
        "manifest_content_sha256",
        None,
    )

    new[
        "manifest_content_sha256"
    ] = canonical_digest(
        new
    )

    validate_manifest_payload(
        new
    )

    return new


def build_phase3b_synchronization_successor_payload(
    phase3_payload: dict,
    synchronization_evidence: dict,
    evidence_relative_path: str = (
        "manifests/m2dgr_synchronization_evidence_v1.json"
    ),
) -> dict:
    """Apply conservative Phase-3B clock-domain semantics.

    This successor does not verify a common physical clock, estimate or apply
    an offset, select a tolerance, create an exclusion rule, or alter stream
    inventory. Equality of clock-domain labels is never synchronization proof.
    """

    validate_manifest_payload(
        phase3_payload
    )

    validate_m2dgr_synchronization_evidence(
        synchronization_evidence
    )

    if phase3_payload[
        "dataset_id"
    ] != DATASET_ID:
        raise ValueError(
            "Phase-3B synchronization successor requires M2DGR"
        )

    expected_source_sha = (
        synchronization_evidence[
            "manifest_semantics"
        ][
            "phase3_source_manifest_content_sha256"
        ]
    )

    if phase3_payload[
        "manifest_content_sha256"
    ] != expected_source_sha:
        raise ValueError(
            "Phase-3B evidence is not bound to the supplied "
            "Phase-3 manifest"
        )

    domains = (
        synchronization_evidence[
            "manifest_semantics"
        ][
            "recommended_conservative_clock_domains"
        ]
    )

    if domains != CONSERVATIVE_CLOCK_DOMAINS:
        raise ValueError(
            "Phase-3B evidence contains unexpected clock domains"
        )

    if (
        not evidence_relative_path
        or Path(
            evidence_relative_path
        ).is_absolute()
    ):
        raise ValueError(
            "Phase-3B evidence path must be non-empty and relative"
        )

    new = deepcopy(
        phase3_payload
    )

    old_by_id = {
        record[
            "trajectory_id"
        ]:
            record
        for record in phase3_payload[
            "records"
        ]
    }

    unchanged_record_fields = (
        "dataset_id",
        "trajectory_id",
        "base_trajectory_id",
        "split",
        "derivative_kind",
        "corruption_seed",
        "references",
        "calibration_artifacts",
        "reference_coverage_artifacts",
    )

    sync_method = (
        "Phase-3B synchronization evidence from "
        f"{evidence_relative_path}; sensor headers show host/system-epoch "
        "behavior and IMU content shows near-zero temporal association, "
        "but common physical clock and capture synchronization remain "
        "unverified; no fixed offset or tolerance selected"
    )

    for record in new[
        "records"
    ]:
        trajectory_id = record[
            "trajectory_id"
        ]

        old_record = old_by_id[
            trajectory_id
        ]

        old_stream_by_id = {
            item[
                "stream_id"
            ]:
                item
            for item in old_record[
                "streams"
            ]
        }

        old_sync_by_id = {
            item[
                "stream_id"
            ]:
                item
            for item in old_record[
                "synchronization"
            ]
        }

        if set(
            old_stream_by_id
        ) != set(
            old_sync_by_id
        ):
            raise ValueError(
                f"{trajectory_id!r}: Phase-3 stream/sync inventory mismatch"
            )

        for stream in record[
            "streams"
        ]:
            stream_id = stream[
                "stream_id"
            ]

            if stream_id not in domains:
                raise ValueError(
                    f"{trajectory_id!r}: unexpected stream "
                    f"{stream_id!r}"
                )

            old_stream = old_stream_by_id[
                stream_id
            ]

            if old_stream[
                "clock_domain"
            ] != "sensor_clock":
                raise ValueError(
                    f"{trajectory_id!r}: expected Phase-3A nominal "
                    f"sensor_clock label for {stream_id!r}"
                )

            for key, value in old_stream.items():
                if key == "clock_domain":
                    continue

                if stream[
                    key
                ] != value:
                    raise ValueError(
                        f"{trajectory_id!r}: unexpected stream metadata "
                        f"change for {stream_id!r}/{key!r}"
                    )

            stream[
                "clock_domain"
            ] = domains[
                stream_id
            ]

        for sync in record[
            "synchronization"
        ]:
            stream_id = sync[
                "stream_id"
            ]

            old_sync = old_sync_by_id[
                stream_id
            ]

            if old_sync[
                "clock_domain"
            ] != "sensor_clock":
                raise ValueError(
                    f"{trajectory_id!r}: unexpected Phase-3A sync "
                    f"clock label for {stream_id!r}"
                )

            if old_sync[
                "verification_status"
            ] != "unverified":
                raise ValueError(
                    f"{trajectory_id!r}: source synchronization is "
                    "not unverified"
                )

            if old_sync[
                "measurement_time_basis"
            ] != "sensor_header_stamp":
                raise ValueError(
                    f"{trajectory_id!r}: source measurement-time "
                    "basis is not sensor_header_stamp"
                )

            if (
                old_sync[
                    "fixed_offset_seconds"
                ] is not None
                or old_sync[
                    "fixed_offset_method"
                ] is not None
                or old_sync[
                    "tolerance_seconds"
                ] is not None
                or old_sync[
                    "tolerance_evidence"
                ] is not None
                or old_sync[
                    "tolerance_selected_on_split"
                ] is not None
            ):
                raise ValueError(
                    f"{trajectory_id!r}: source manifest unexpectedly "
                    "contains offset/tolerance decisions"
                )

            for key, value in old_sync.items():
                if key in (
                    "clock_domain",
                    "method",
                ):
                    continue

                if sync[
                    key
                ] != value:
                    raise ValueError(
                        f"{trajectory_id!r}: unexpected synchronization "
                        f"change for {stream_id!r}/{key!r}"
                    )

            sync[
                "clock_domain"
            ] = domains[
                stream_id
            ]

            sync[
                "method"
            ] = sync_method

        for field in unchanged_record_fields:
            if record[
                field
            ] != old_record[
                field
            ]:
                raise ValueError(
                    f"{trajectory_id!r}: Phase-3B migration "
                    f"unexpectedly changed {field!r}"
                )

    new.pop(
        "manifest_content_sha256",
        None,
    )

    new[
        "manifest_content_sha256"
    ] = canonical_digest(
        new
    )

    validate_manifest_payload(
        new
    )

    return new


def build_records(
    dataset_root: Path,
) -> tuple[
    tuple[TrajectoryRecord, ...],
    dict[str, tuple[SynchronizationSpec, ...]],
]:
    records = []
    sync = {}

    bag_root = dataset_root / "raw" / "rosbags"
    gt_root = dataset_root / "raw" / "ground_truth"

    for trajectory_id in discover_trajectories(dataset_root):
        bag = bag_root / f"{trajectory_id}.bag"
        gt = gt_root / f"{trajectory_id}.txt"
        if not gt.exists():
            raise FileNotFoundError(gt)

        streams = build_streams_for_trajectory(
            dataset_root,
            trajectory_id,
        )

        record = TrajectoryRecord(
            dataset_id=DATASET_ID,
            trajectory_id=trajectory_id,
            base_trajectory_id=trajectory_id,
            split=SplitRole.TRAIN,
            streams=streams,
            references=(
                build_reference(
                    dataset_root,
                    gt,
                    trajectory_id,
                ),
            ),
            reference_coverage_artifacts=(),
            calibration_artifacts=(
                CalibrationArtifactSpec(
                    artifact_id=f"{trajectory_id}_bag_sha256",
                    source_path=(
                        bag.relative_to(dataset_root).as_posix()
                    ),
                    sha256=sha256_file(bag),
                    verification_status=VerificationStatus.VERIFIED,
                    notes="raw bag integrity artifact",
                ),
            ),
        )
        records.append(record)

        sync[trajectory_id] = build_synchronization_for_trajectory(
            dataset_root,
            trajectory_id,
            streams,
        )

    return tuple(records), sync


def build_m2dgr_manifest(
    dataset_root: str | Path,
    output_path: str | Path,
):
    dataset_root = Path(dataset_root)
    records, sync = build_records(dataset_root)
    return write_immutable_manifest(
        output_path,
        records,
        sync,
    )
