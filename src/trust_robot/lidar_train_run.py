from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Mapping
import json
import os
import tempfile

from .clean_backbone import (
    CleanBackboneState,
    RelativePoseIncrement,
)
from .lidar_frontend import (
    LidarRegistrationDiagnostics,
)


RUN_SCHEMA = "TRUST_ROBOT_PHASE2_CLEAN_LIDAR_TRAIN_RUN_V1"
RUN_SCHEMA_VERSION = 1

TRAIN_TRAJECTORIES = (
    "Circle_01",
    "door_01",
    "gate_01",
    "hall_01",
    "hall_03",
    "hall_04",
    "hall_05",
    "lift_02",
    "lift_04",
    "room_02",
    "room_dark_01",
    "room_dark_02",
    "room_dark_03",
    "room_dark_04",
    "street_01",
    "street_010",
    "street_03",
    "street_04",
    "street_05",
    "street_07",
    "street_09",
    "walk_01",
)


class LidarTrainRunError(ValueError):
    """Raised when the frozen TRAIN execution contract is violated."""


def sha256_file(
    path: Path,
) -> str:
    digest = sha256()

    with path.open(
        "rb"
    ) as handle:
        for block in iter(
            lambda: handle.read(
                1024 * 1024
            ),
            b"",
        ):
            digest.update(
                block
            )

    return digest.hexdigest()


def canonical_content_sha256(
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
    ).encode(
        "utf-8"
    )

    return sha256(
        raw
    ).hexdigest()


def build_train_run_manifest(
    *,
    split_manifest_sha256: str,
    frontend_config_file_sha256: str,
    frontend_config_content_sha256: str,
    repo_component_hashes: Mapping[str, str],
    bag_file_sizes_bytes: Mapping[str, int],
) -> dict[str, object]:
    if tuple(
        bag_file_sizes_bytes.keys()
    ) != TRAIN_TRAJECTORIES:
        raise LidarTrainRunError(
            "bag size mapping must follow the exact frozen TRAIN order"
        )

    for trajectory, size in bag_file_sizes_bytes.items():
        if (
            not isinstance(
                size,
                int,
            )
            or isinstance(
                size,
                bool,
            )
            or size <= 0
        ):
            raise LidarTrainRunError(
                f"invalid bag size for {trajectory}"
            )

    manifest: dict[str, object] = {
        "schema":
            RUN_SCHEMA,

        "schema_version":
            RUN_SCHEMA_VERSION,

        "status":
            "train_execution_candidate",

        "dataset_id":
            "M2DGR",

        "split_scope":
            "train",

        "trajectory_order":
            list(
                TRAIN_TRAJECTORIES
            ),

        "trajectory_count":
            len(
                TRAIN_TRAJECTORIES
            ),

        "input_contract": {
            "topic":
                "/velodyne_points",

            "msgtype":
                "sensor_msgs/msg/PointCloud2",

            "frame_id":
                "velodyne",

            "bag_relative_paths": [
                (
                    "raw/rosbags/"
                    + trajectory
                    + ".bag"
                )
                for trajectory
                in TRAIN_TRAJECTORIES
            ],

            "bag_file_sizes_bytes":
                dict(
                    bag_file_sizes_bytes
                ),

            "bag_content_sha256_computed_by_this_runner":
                False,
        },

        "binding": {
            "split_manifest_sha256":
                split_manifest_sha256,

            "frontend_config_file_sha256":
                frontend_config_file_sha256,

            "frontend_config_content_sha256":
                frontend_config_content_sha256,

            "repo_component_hashes":
                dict(
                    sorted(
                        repo_component_hashes.items()
                    )
                ),
        },

        "execution_contract": {
            "trajectory_processing":
                "sequential",

            "scan_processing":
                "consecutive",

            "registration_error_policy":
                "fail_closed",

            "scan_skip_policy":
                "none",

            "trajectory_skip_policy":
                "none",

            "registration_timeout":
                None,

            "automatic_residual_threshold":
                None,

            "automatic_iteration_limit":
                None,

            "automatic_exclusion_rule":
                None,
        },

        "scientific_scope": {
            "reference_data_used":
                False,

            "confirmation_test_data_used":
                False,

            "ground_truth_association_performed":
                False,

            "alignment_performed":
                False,

            "ate_computed":
                False,

            "rpe_computed":
                False,

            "trajectory_scoring_performed":
                False,

            "estimator_scoring_performed":
                False,

            "scan_temporal_reference_verified":
                False,

            "per_point_time_used":
                False,

            "deskew_performed":
                False,

            "phase2_exit_evidence_satisfied":
                False,
        },
    }

    manifest[
        "content_sha256"
    ] = canonical_content_sha256(
        manifest
    )

    return manifest


def trajectory_header_record(
    *,
    trajectory: str,
    initial_timestamp_ns: int,
) -> dict[str, object]:
    if trajectory not in TRAIN_TRAJECTORIES:
        raise LidarTrainRunError(
            "trajectory is not in the frozen TRAIN set"
        )

    return {
        "record_type":
            "trajectory_header",

        "trajectory":
            trajectory,

        "bag_relative_path":
            f"raw/rosbags/{trajectory}.bag",

        "world_frame_id":
            "phase2_lidar_first_scan_origin",

        "body_frame_id":
            "velodyne",

        "relative_pose_source_id":
            "m2dgr_velodyne_exact_nn_fixed_point_v1",

        "initial_timestamp_ns":
            int(
                initial_timestamp_ns
            ),

        "initial_pose_world_T_body": {
            "translation_m":
                [
                    0.0,
                    0.0,
                    0.0,
                ],

            "quaternion_wxyz":
                [
                    1.0,
                    0.0,
                    0.0,
                    0.0,
                ],
        },

        "reference_data_used":
            False,

        "confirmation_test_data_used":
            False,
    }


def pair_record(
    *,
    trajectory: str,
    scan_index: int,
    previous_timestamp_ns: int,
    increment: RelativePoseIncrement,
    state: CleanBackboneState,
    diagnostics: LidarRegistrationDiagnostics,
) -> dict[str, object]:
    if trajectory not in TRAIN_TRAJECTORIES:
        raise LidarTrainRunError(
            "trajectory is not in the frozen TRAIN set"
        )

    if scan_index < 1:
        raise LidarTrainRunError(
            "scan_index must be at least 1 for a pair record"
        )

    return {
        "record_type":
            "relative_pose",

        "trajectory":
            trajectory,

        "scan_index":
            int(
                scan_index
            ),

        "previous_header_stamp_ns":
            int(
                previous_timestamp_ns
            ),

        "current_header_stamp_ns":
            int(
                increment.timestamp_ns
            ),

        "header_delta_ns":
            int(
                increment.timestamp_ns
                - previous_timestamp_ns
            ),

        "delta_prev_lidar_T_current_lidar":
            increment.delta_prev_body_T_current_body.to_dict(),

        "state_world_T_lidar":
            state.pose_world_T_body.to_dict(),

        "diagnostics":
            diagnostics.to_dict(),

        "scientific_scope": {
            "reference_data_used":
                False,

            "confirmation_test_data_used":
                False,

            "scan_temporal_reference_verified":
                False,

            "per_point_time_used":
                False,

            "deskew_performed":
                False,

            "correspondence_rejection_used":
                False,

            "voxel_downsampling_used":
                False,

            "ate_computed":
                False,

            "rpe_computed":
                False,

            "trajectory_scoring_performed":
                False,
        },
    }


def trajectory_complete_record(
    *,
    trajectory: str,
    scan_count: int,
    final_state: CleanBackboneState,
) -> dict[str, object]:
    if trajectory not in TRAIN_TRAJECTORIES:
        raise LidarTrainRunError(
            "trajectory is not in the frozen TRAIN set"
        )

    if scan_count < 1:
        raise LidarTrainRunError(
            "completed trajectory must contain at least one scan"
        )

    return {
        "record_type":
            "trajectory_complete",

        "trajectory":
            trajectory,

        "scan_count":
            int(
                scan_count
            ),

        "increment_count":
            int(
                scan_count
                - 1
            ),

        "final_timestamp_ns":
            int(
                final_state.timestamp_ns
            ),

        "final_state_world_T_lidar":
            final_state.pose_world_T_body.to_dict(),

        "reference_data_used":
            False,

        "confirmation_test_data_used":
            False,

        "trajectory_scoring_performed":
            False,
    }


def atomic_write_json(
    path: Path,
    payload: Mapping[str, object],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    text = (
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    )

    fd, temporary_name = tempfile.mkstemp(
        prefix=(
            "."
            + path.name
            + "."
        ),
        suffix=".tmp",
        dir=str(
            path.parent
        ),
        text=True,
    )

    temporary = Path(
        temporary_name
    )

    try:
        with os.fdopen(
            fd,
            "w",
            encoding="utf-8",
        ) as handle:
            handle.write(
                text
            )

            handle.flush()

            os.fsync(
                handle.fileno()
            )

        os.replace(
            temporary,
            path,
        )

    finally:
        if temporary.exists():
            temporary.unlink()
