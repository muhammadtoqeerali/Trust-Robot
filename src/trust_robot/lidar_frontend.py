from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Mapping
import json
import math

import numpy as np
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation

from .clean_backbone import (
    PoseSE3,
    RelativePoseIncrement,
)


CONFIG_SCHEMA = "TRUST_ROBOT_PHASE2_CLEAN_LIDAR_FRONTEND_CANDIDATE_V1"

EXPECTED_TOPIC = "/velodyne_points"
EXPECTED_MSGTYPE = "sensor_msgs/msg/PointCloud2"
EXPECTED_FRAME_ID = "velodyne"
EXPECTED_FIELDS = (
    "x",
    "y",
    "z",
    "intensity",
    "ring",
    "time",
)
EXPECTED_POINT_STEP = 22

SOURCE_ID = "m2dgr_velodyne_exact_nn_fixed_point_v1"

_POINT_FIELD_DTYPES = {
    1: "i1",
    2: "u1",
    3: "i2",
    4: "u2",
    5: "i4",
    6: "u4",
    7: "f4",
    8: "f8",
}


class LidarFrontendError(ValueError):
    """Raised when the fixed LiDAR frontend contract is violated."""


@dataclass(
    frozen=True,
)
class LidarRegistrationDiagnostics:
    source_point_count: int
    target_point_count: int
    fixed_point_iterations: int
    final_correspondence_count: int
    final_nearest_neighbor_rmse_m: float
    convergence_rule: str
    correspondence_rejection_used: bool
    voxel_downsampling_used: bool

    def to_dict(
        self,
    ) -> dict[str, object]:
        return {
            "source_point_count":
                self.source_point_count,

            "target_point_count":
                self.target_point_count,

            "fixed_point_iterations":
                self.fixed_point_iterations,

            "final_correspondence_count":
                self.final_correspondence_count,

            "final_nearest_neighbor_rmse_m":
                self.final_nearest_neighbor_rmse_m,

            "convergence_rule":
                self.convergence_rule,

            "correspondence_rejection_used":
                self.correspondence_rejection_used,

            "voxel_downsampling_used":
                self.voxel_downsampling_used,
        }


@dataclass(
    frozen=True,
)
class LidarRegistrationResult:
    previous_lidar_T_current_lidar: PoseSE3
    diagnostics: LidarRegistrationDiagnostics


def _canonical_json_sha256(
    payload: Mapping[str, object],
) -> str:
    value = dict(
        payload
    )

    value.pop(
        "content_sha256",
        None,
    )

    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")

    return sha256(
        raw
    ).hexdigest()


def validate_lidar_frontend_config(
    payload: Mapping[str, object],
) -> None:
    if payload.get(
        "schema"
    ) != CONFIG_SCHEMA:
        raise LidarFrontendError(
            "unexpected LiDAR frontend config schema"
        )

    stored = payload.get(
        "content_sha256"
    )

    if (
        not isinstance(
            stored,
            str,
        )
        or stored
        != _canonical_json_sha256(
            payload
        )
    ):
        raise LidarFrontendError(
            "LiDAR frontend config content digest mismatch"
        )

    input_contract = payload[
        "input_contract"
    ]

    if input_contract != {
        "topic":
            EXPECTED_TOPIC,

        "msgtype":
            EXPECTED_MSGTYPE,

        "frame_id":
            EXPECTED_FRAME_ID,

        "height":
            1,

        "is_bigendian":
            False,

        "is_dense":
            True,

        "point_step_bytes":
            EXPECTED_POINT_STEP,

        "expected_field_names":
            list(
                EXPECTED_FIELDS
            ),
    }:
        raise LidarFrontendError(
            "LiDAR input contract differs from the frozen candidate"
        )

    registration = payload[
        "registration_contract"
    ]

    required_exact = {
        "method":
            "exact_nearest_neighbor_fixed_point_kabsch",

        "target_scan":
            "previous",

        "source_scan":
            "current",

        "initialization":
            "identity",

        "uses_all_points":
            True,

        "voxel_downsampling":
            None,

        "correspondence_distance_threshold":
            None,

        "outlier_rejection":
            None,

        "keyframe_rule":
            None,

        "numeric_convergence_tolerance":
            None,

        "max_iterations":
            None,

        "convergence_rule":
            "exact_nearest_neighbor_assignment_unchanged",

        "cycle_policy":
            "raise_error",

        "nearest_neighbor_workers":
            1,
    }

    if registration != required_exact:
        raise LidarFrontendError(
            "LiDAR registration contract differs from the frozen candidate"
        )

    scope = payload[
        "scientific_scope"
    ]

    for key in (
        "frontend_finalized",
        "phase2_exit_evidence_satisfied",
        "reference_data_used",
        "confirmation_test_data_used",
        "alignment_used",
        "ate_computed",
        "rpe_computed",
        "trajectory_scoring_performed",
    ):
        if scope[
            key
        ] is not False:
            raise LidarFrontendError(
                f"candidate scope must remain false: {key}"
            )


def _header_stamp_ns(
    message,
) -> int:
    header = getattr(
        message,
        "header",
        None,
    )

    if header is None:
        raise LidarFrontendError(
            "PointCloud2 message has no header"
        )

    stamp = getattr(
        header,
        "stamp",
        None,
    )

    if stamp is None:
        raise LidarFrontendError(
            "PointCloud2 header has no stamp"
        )

    sec = None
    nanosec = None

    for name in (
        "sec",
        "secs",
    ):
        value = getattr(
            stamp,
            name,
            None,
        )

        if value is not None:
            sec = int(
                value
            )
            break

    for name in (
        "nanosec",
        "nsec",
        "nsecs",
    ):
        value = getattr(
            stamp,
            name,
            None,
        )

        if value is not None:
            nanosec = int(
                value
            )
            break

    if (
        sec is None
        or nanosec is None
    ):
        raise LidarFrontendError(
            "PointCloud2 header timestamp fields are unavailable"
        )

    if not (
        0
        <= nanosec
        < 1_000_000_000
    ):
        raise LidarFrontendError(
            "PointCloud2 header nanoseconds are invalid"
        )

    return (
        sec * 1_000_000_000
        + nanosec
    )


def pointcloud_header_stamp_ns(
    message,
) -> int:
    return _header_stamp_ns(
        message
    )


def pointcloud_field_descriptors(
    message,
) -> tuple[
    tuple[str, int, int, int],
    ...,
]:
    result = []

    for field in getattr(
        message,
        "fields",
        (),
    ):
        result.append(
            (
                str(
                    getattr(
                        field,
                        "name",
                        "",
                    )
                ),
                int(
                    getattr(
                        field,
                        "offset",
                    )
                ),
                int(
                    getattr(
                        field,
                        "datatype",
                    )
                ),
                int(
                    getattr(
                        field,
                        "count",
                    )
                ),
            )
        )

    return tuple(
        result
    )


def decode_m2dgr_velodyne_xyz(
    message,
) -> np.ndarray:
    header = getattr(
        message,
        "header",
        None,
    )

    if header is None:
        raise LidarFrontendError(
            "PointCloud2 message has no header"
        )

    frame_id = str(
        getattr(
            header,
            "frame_id",
            "",
        )
    )

    if frame_id != EXPECTED_FRAME_ID:
        raise LidarFrontendError(
            f"unexpected PointCloud2 frame_id: {frame_id!r}"
        )

    if int(
        getattr(
            message,
            "height",
            -1,
        )
    ) != 1:
        raise LidarFrontendError(
            "M2DGR Velodyne candidate requires unorganized height=1 clouds"
        )

    width = int(
        getattr(
            message,
            "width",
            -1,
        )
    )

    if width < 3:
        raise LidarFrontendError(
            "PointCloud2 must contain at least 3 points"
        )

    point_step = int(
        getattr(
            message,
            "point_step",
            -1,
        )
    )

    if point_step != EXPECTED_POINT_STEP:
        raise LidarFrontendError(
            "unexpected M2DGR Velodyne point_step"
        )

    row_step = int(
        getattr(
            message,
            "row_step",
            -1,
        )
    )

    if row_step != width * point_step:
        raise LidarFrontendError(
            "candidate requires contiguous unorganized PointCloud2 rows"
        )

    if bool(
        getattr(
            message,
            "is_bigendian",
            True,
        )
    ):
        raise LidarFrontendError(
            "candidate requires little-endian PointCloud2 data"
        )

    if not bool(
        getattr(
            message,
            "is_dense",
            False,
        )
    ):
        raise LidarFrontendError(
            "candidate refuses a non-dense PointCloud2 message"
        )

    descriptors = pointcloud_field_descriptors(
        message
    )

    names = tuple(
        item[0]
        for item in descriptors
    )

    if names != EXPECTED_FIELDS:
        raise LidarFrontendError(
            f"unexpected PointCloud2 fields: {names!r}"
        )

    by_name = {
        name:
            (
                offset,
                datatype,
                count,
            )
        for (
            name,
            offset,
            datatype,
            count,
        )
        in descriptors
    }

    raw = memoryview(
        getattr(
            message,
            "data",
        )
    ).cast(
        "B"
    )

    required_bytes = (
        width
        * point_step
    )

    if len(
        raw
    ) < required_bytes:
        raise LidarFrontendError(
            "PointCloud2 data buffer is shorter than row_step"
        )

    coordinates = []

    for name in (
        "x",
        "y",
        "z",
    ):
        offset, datatype, count = by_name[
            name
        ]

        if count != 1:
            raise LidarFrontendError(
                f"{name} field must have count=1"
            )

        dtype_code = _POINT_FIELD_DTYPES.get(
            datatype
        )

        if dtype_code not in {
            "f4",
            "f8",
        }:
            raise LidarFrontendError(
                f"{name} field must be floating-point"
            )

        dtype = np.dtype(
            "<" + dtype_code
        )

        item_size = dtype.itemsize

        if (
            offset < 0
            or offset + item_size > point_step
        ):
            raise LidarFrontendError(
                f"{name} field offset is outside point_step"
            )

        coordinate = np.ndarray(
            shape=(
                width,
            ),
            dtype=dtype,
            buffer=raw,
            offset=offset,
            strides=(
                point_step,
            ),
        )

        coordinates.append(
            np.asarray(
                coordinate,
                dtype=np.float64,
            )
        )

    xyz = np.column_stack(
        coordinates
    )

    if xyz.shape != (
        width,
        3,
    ):
        raise LidarFrontendError(
            "decoded XYZ shape is invalid"
        )

    if not np.isfinite(
        xyz
    ).all():
        raise LidarFrontendError(
            "candidate refuses non-finite XYZ samples instead of filtering them"
        )

    return np.ascontiguousarray(
        xyz,
        dtype=np.float64,
    )


def _validate_xyz(
    value,
    *,
    name: str,
) -> np.ndarray:
    array = np.asarray(
        value,
        dtype=np.float64,
    )

    if (
        array.ndim != 2
        or array.shape[1] != 3
        or array.shape[0] < 3
    ):
        raise LidarFrontendError(
            f"{name} must have shape (N, 3) with N >= 3"
        )

    if not np.isfinite(
        array
    ).all():
        raise LidarFrontendError(
            f"{name} must contain only finite values"
        )

    return np.ascontiguousarray(
        array
    )


def rigid_transform_kabsch(
    source_xyz,
    target_xyz,
) -> PoseSE3:
    source = _validate_xyz(
        source_xyz,
        name="source_xyz",
    )

    target = _validate_xyz(
        target_xyz,
        name="target_xyz",
    )

    if source.shape != target.shape:
        raise LidarFrontendError(
            "Kabsch correspondences must have identical shapes"
        )

    source_centroid = np.mean(
        source,
        axis=0,
    )

    target_centroid = np.mean(
        target,
        axis=0,
    )

    centered_source = (
        source
        - source_centroid
    )

    centered_target = (
        target
        - target_centroid
    )

    covariance = (
        centered_source.T
        @ centered_target
    )

    u, _singular_values, vt = np.linalg.svd(
        covariance,
        full_matrices=False,
    )

    rotation = (
        vt.T
        @ u.T
    )

    if np.linalg.det(
        rotation
    ) < 0.0:
        vt = vt.copy()
        vt[-1, :] *= -1.0

        rotation = (
            vt.T
            @ u.T
        )

    if not np.isfinite(
        rotation
    ).all():
        raise LidarFrontendError(
            "Kabsch produced a non-finite rotation"
        )

    translation = (
        target_centroid
        - rotation
        @ source_centroid
    )

    quaternion_xyzw = Rotation.from_matrix(
        rotation
    ).as_quat()

    pose = PoseSE3(
        translation_m=tuple(
            float(value)
            for value in translation
        ),
        quaternion_wxyz=(
            float(
                quaternion_xyzw[3]
            ),
            float(
                quaternion_xyzw[0]
            ),
            float(
                quaternion_xyzw[1]
            ),
            float(
                quaternion_xyzw[2]
            ),
        ),
    )

    return pose


def transform_xyz(
    pose: PoseSE3,
    xyz,
) -> np.ndarray:
    points = _validate_xyz(
        xyz,
        name="xyz",
    )

    w, x, y, z = pose.quaternion_wxyz

    rotation = Rotation.from_quat(
        [
            x,
            y,
            z,
            w,
        ]
    ).as_matrix()

    translation = np.asarray(
        pose.translation_m,
        dtype=np.float64,
    )

    return (
        points
        @ rotation.T
        + translation
    )


def register_current_scan_to_previous(
    previous_xyz,
    current_xyz,
) -> LidarRegistrationResult:
    """Estimate previous_lidar_T_current_lidar.

    No points are downsampled or rejected. The exact NN assignment itself is
    the fixed-point state. Convergence means that assignment is exactly
    unchanged on two consecutive iterations.
    """

    target = _validate_xyz(
        previous_xyz,
        name="previous_xyz",
    )

    source = _validate_xyz(
        current_xyz,
        name="current_xyz",
    )

    tree = cKDTree(
        target
    )

    estimate = PoseSE3.identity()

    previous_indices = None
    seen_assignment_digests = set()
    iteration = 0

    while True:
        transformed = transform_xyz(
            estimate,
            source,
        )

        _distances, indices = tree.query(
            transformed,
            k=1,
            workers=1,
        )

        indices = np.asarray(
            indices,
            dtype=np.int64,
        )

        if (
            previous_indices is not None
            and np.array_equal(
                indices,
                previous_indices,
            )
        ):
            corresponded_target = target[
                indices
            ]

            final_pose = rigid_transform_kabsch(
                source,
                corresponded_target,
            )

            final_transformed = transform_xyz(
                final_pose,
                source,
            )

            final_distances, _ = tree.query(
                final_transformed,
                k=1,
                workers=1,
            )

            rmse = math.sqrt(
                float(
                    np.mean(
                        np.square(
                            final_distances,
                            dtype=np.float64,
                        )
                    )
                )
            )

            if not math.isfinite(
                rmse
            ):
                raise LidarFrontendError(
                    "final nearest-neighbor RMSE is non-finite"
                )

            return LidarRegistrationResult(
                previous_lidar_T_current_lidar=
                    final_pose,

                diagnostics=
                    LidarRegistrationDiagnostics(
                        source_point_count=
                            int(
                                source.shape[0]
                            ),

                        target_point_count=
                            int(
                                target.shape[0]
                            ),

                        fixed_point_iterations=
                            iteration,

                        final_correspondence_count=
                            int(
                                indices.size
                            ),

                        final_nearest_neighbor_rmse_m=
                            rmse,

                        convergence_rule=
                            "exact_nearest_neighbor_assignment_unchanged",

                        correspondence_rejection_used=
                            False,

                        voxel_downsampling_used=
                            False,
                    ),
            )

        digest = sha256(
            indices.tobytes()
        ).digest()

        if digest in seen_assignment_digests:
            raise LidarFrontendError(
                "nearest-neighbor assignment entered a repeated non-consecutive state"
            )

        seen_assignment_digests.add(
            digest
        )

        corresponded_target = target[
            indices
        ]

        estimate = rigid_transform_kabsch(
            source,
            corresponded_target,
        )

        previous_indices = indices.copy()

        iteration += 1


def build_relative_pose_increment(
    *,
    previous_message,
    current_message,
) -> tuple[
    RelativePoseIncrement,
    LidarRegistrationDiagnostics,
]:
    previous_timestamp = pointcloud_header_stamp_ns(
        previous_message
    )

    current_timestamp = pointcloud_header_stamp_ns(
        current_message
    )

    if current_timestamp <= previous_timestamp:
        raise LidarFrontendError(
            "PointCloud2 header timestamps must be strictly increasing"
        )

    previous_xyz = decode_m2dgr_velodyne_xyz(
        previous_message
    )

    current_xyz = decode_m2dgr_velodyne_xyz(
        current_message
    )

    result = register_current_scan_to_previous(
        previous_xyz,
        current_xyz,
    )

    increment = RelativePoseIncrement(
        timestamp_ns=current_timestamp,
        body_frame_id=EXPECTED_FRAME_ID,
        source_id=SOURCE_ID,
        delta_prev_body_T_current_body=
            result.previous_lidar_T_current_lidar,
    )

    return (
        increment,
        result.diagnostics,
    )
