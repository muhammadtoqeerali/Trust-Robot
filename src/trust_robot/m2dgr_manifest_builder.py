
from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from .reference_coverage import (
    ReferenceCoverageArtifact,
    ValidInterval,
)

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
from .trajectory_manifest import (
    build_trajectory_manifest,
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


def discover_trajectories(
    root: Path,
) -> list[str]:
    bags = sorted(
        root.joinpath(
            "raw",
            "rosbags",
        ).glob(
            "*.bag"
        )
    )

    return [
        bag.stem
        for bag in bags
    ]


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


def build_reference(
    gt_path: Path,
    trajectory_id: str,
) -> ReferenceSpec:

    family = infer_reference_family(
        trajectory_id
    )

    return ReferenceSpec(
        source_id=f"{trajectory_id}_reference",
        frame_id="unknown",
        coverage=ReferenceCoverage.FULL,
        supports_translation=True,
        supports_rotation=(
            family
            is not M2DGRReferenceFamily.LEICA
        ),
        derived_from_stream_ids=(),
        translation_validity_artifact=str(
            gt_path
        ),
        rotation_validity_artifact=(
            str(gt_path)
            if family is not M2DGRReferenceFamily.LEICA
            else None
        ),
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

    for trajectory_id in discover_trajectories(
        dataset_root
    ):

        bag = bag_root / f"{trajectory_id}.bag"
        gt = gt_root / f"{trajectory_id}.txt"

        if not gt.exists():
            raise FileNotFoundError(
                gt
            )

        family = infer_reference_family(
            trajectory_id
        )

        record = TrajectoryRecord(
            dataset_id=DATASET_ID,
            trajectory_id=trajectory_id,
            base_trajectory_id=trajectory_id,
            split=SplitRole.TRAIN,
            streams=streams,
            references=(
                build_reference(
                    gt,
                    trajectory_id,
                ),
            ),
            reference_coverage_artifacts=(
                ReferenceCoverageArtifact(
                    trajectory_id=trajectory_id,
                    reference_source=(
                        "Leica"
                        if family is M2DGRReferenceFamily.LEICA
                        else "independent_reference"
                    ),
                    translation_valid=True,
                    rotation_valid=(
                        family is not M2DGRReferenceFamily.LEICA
                    ),
                    valid_intervals=(
                        ValidInterval(
                            0,
                            1,
                        ),
                    ),
                    reason=(
                        "position-only Leica reference"
                        if family is M2DGRReferenceFamily.LEICA
                        else None
                    ),
                ),
            ),
            calibration_artifacts=(
                CalibrationArtifactSpec(
                    artifact_id=f"{trajectory_id}_bag_sha256",
                    source_path=str(
                        bag.relative_to(dataset_root)
                    ),
                    sha256=sha256_file(bag),
                    verification_status=VerificationStatus.VERIFIED,
                    notes="raw bag integrity artifact",
                ),
            ),
        )

        records.append(
            record
        )

        sync[trajectory_id] = tuple(
            SynchronizationSpec(
                stream_id=s.stream_id,
                clock_domain=s.clock_domain,
                verification_status=VerificationStatus.UNVERIFIED,
                method=None,
            )
            for s in streams
        )

    return tuple(records), sync


def build_m2dgr_manifest(
    dataset_root: str | Path,
    output_path: str | Path,
) -> dict:

    dataset_root = Path(
        dataset_root
    )

    records, sync = build_records(
        dataset_root
    )

    return write_immutable_manifest(
        output_path,
        records,
        sync,
    )
