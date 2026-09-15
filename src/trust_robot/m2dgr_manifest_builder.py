from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from .data_contracts import (
    CalibrationArtifactSpec,
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
from .reference_quality import (
    load_reference_quality_artifact,
)
from .trajectory_manifest import (
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
    """Build an M2DGR reference spec from validated audit evidence.

    Phase 2 intentionally leaves continuous-time coverage UNKNOWN. Structural
    sample validity is carried by the reference-quality artifact, while
    synchronization/association and interpolation policy remain separate work.
    """

    family = infer_reference_family(trajectory_id)
    quality_path = _quality_artifact_path(dataset_root, trajectory_id)

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

    expected_source_relpath = gt_path.relative_to(dataset_root).as_posix()
    source = quality["source"]

    if source["relative_path"] != expected_source_relpath:
        raise ValueError(
            f"reference-quality source-path mismatch for {trajectory_id!r}"
        )

    if source["sha256"] != sha256_file(gt_path):
        raise ValueError(
            f"reference-quality source hash mismatch for {trajectory_id!r}"
        )

    quality_relpath = quality_path.relative_to(dataset_root).as_posix()
    supports_rotation = family is not M2DGRReferenceFamily.LEICA

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


def build_records(
    dataset_root: Path,
) -> tuple[
    tuple[TrajectoryRecord, ...],
    dict[str, tuple[SynchronizationSpec, ...]],
]:
    streams = build_streams()
    records = []
    sync = {}

    bag_root = dataset_root / "raw" / "rosbags"
    gt_root = dataset_root / "raw" / "ground_truth"

    for trajectory_id in discover_trajectories(dataset_root):
        bag = bag_root / f"{trajectory_id}.bag"
        gt = gt_root / f"{trajectory_id}.txt"

        if not gt.exists():
            raise FileNotFoundError(gt)

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
            # The Phase-1 ReferenceCoverageArtifact represented continuous-time
            # intervals and previously carried a dummy [0, 1] ns placeholder.
            # Phase 2 removes that placeholder. Continuous-time coverage remains
            # unknown until synchronization/association evidence is established.
            reference_coverage_artifacts=(),
            calibration_artifacts=(
                CalibrationArtifactSpec(
                    artifact_id=f"{trajectory_id}_bag_sha256",
                    source_path=bag.relative_to(dataset_root).as_posix(),
                    sha256=sha256_file(bag),
                    verification_status=VerificationStatus.VERIFIED,
                    notes="raw bag integrity artifact",
                ),
            ),
        )

        records.append(record)

        sync[trajectory_id] = tuple(
            SynchronizationSpec(
                stream_id=stream.stream_id,
                clock_domain=stream.clock_domain,
                verification_status=VerificationStatus.UNVERIFIED,
                method=None,
            )
            for stream in streams
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
