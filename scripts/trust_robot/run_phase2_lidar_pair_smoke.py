#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path
import argparse
import json

from rosbags.highlevel import AnyReader

from trust_robot.clean_backbone import (
    CleanBackboneConfig,
    FixedCleanBackbone,
    PoseSE3,
)
from trust_robot.lidar_frontend import (
    EXPECTED_MSGTYPE,
    EXPECTED_TOPIC,
    SOURCE_ID,
    build_relative_pose_increment,
    pointcloud_field_descriptors,
    pointcloud_header_stamp_ns,
    validate_lidar_frontend_config,
)


ALLOWED_TRAIN = {
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
}


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--dataset-root",
        required=True,
    )

    parser.add_argument(
        "--trajectory",
        required=True,
        choices=sorted(
            ALLOWED_TRAIN
        ),
    )

    parser.add_argument(
        "--config",
        required=True,
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    config_payload = json.loads(
        Path(
            args.config
        ).read_text(
            encoding="utf-8"
        )
    )

    validate_lidar_frontend_config(
        config_payload
    )

    bag = (
        Path(
            args.dataset_root
        )
        / "raw"
        / "rosbags"
        / f"{args.trajectory}.bag"
    )

    if not bag.is_file():
        raise RuntimeError(
            f"missing TRAIN bag: {bag}"
        )

    messages = []

    with AnyReader(
        [
            bag
        ]
    ) as reader:
        connections = [
            connection
            for connection
            in reader.connections
            if (
                connection.topic
                == EXPECTED_TOPIC
                and connection.msgtype
                == EXPECTED_MSGTYPE
            )
        ]

        if not connections:
            raise RuntimeError(
                "expected Velodyne PointCloud2 connection not found"
            )

        for connection, _bag_time, rawdata in reader.messages(
            connections=connections
        ):
            message = reader.deserialize(
                rawdata,
                connection.msgtype,
            )

            messages.append(
                message
            )

            if len(
                messages
            ) == 2:
                break

    if len(
        messages
    ) != 2:
        raise RuntimeError(
            "could not obtain two Velodyne scans"
        )

    previous_message, current_message = messages

    previous_timestamp = pointcloud_header_stamp_ns(
        previous_message
    )

    current_timestamp = pointcloud_header_stamp_ns(
        current_message
    )

    print(
        "trajectory=",
        args.trajectory,
    )

    print(
        "bag=",
        bag,
    )

    print(
        "previous_header_stamp_ns=",
        previous_timestamp,
    )

    print(
        "current_header_stamp_ns=",
        current_timestamp,
    )

    print(
        "header_delta_ns=",
        current_timestamp
        - previous_timestamp,
    )

    print(
        "field_descriptors=",
        pointcloud_field_descriptors(
            previous_message
        ),
    )

    print(
        "previous_width=",
        int(
            previous_message.width
        ),
    )

    print(
        "current_width=",
        int(
            current_message.width
        ),
    )

    increment, diagnostics = (
        build_relative_pose_increment(
            previous_message=
                previous_message,

            current_message=
                current_message,
        )
    )

    backbone = FixedCleanBackbone(
        CleanBackboneConfig(
            world_frame_id=
                "phase2_lidar_first_scan_origin",

            body_frame_id=
                "velodyne",

            relative_pose_source_id=
                SOURCE_ID,

            initial_timestamp_ns=
                previous_timestamp,

            initial_pose_world_T_body=
                PoseSE3.identity(),
        )
    )

    state = backbone.apply(
        increment
    )

    print(
        "fixed_point_iterations=",
        diagnostics.fixed_point_iterations,
    )

    print(
        "source_point_count=",
        diagnostics.source_point_count,
    )

    print(
        "target_point_count=",
        diagnostics.target_point_count,
    )

    print(
        "final_correspondence_count=",
        diagnostics.final_correspondence_count,
    )

    print(
        "final_nearest_neighbor_rmse_m=",
        diagnostics.final_nearest_neighbor_rmse_m,
    )

    print(
        "delta_prev_lidar_T_current_lidar.translation_m=",
        increment.delta_prev_body_T_current_body.translation_m,
    )

    print(
        "delta_prev_lidar_T_current_lidar.quaternion_wxyz=",
        increment.delta_prev_body_T_current_body.quaternion_wxyz,
    )

    print(
        "backbone_state.translation_m=",
        state.pose_world_T_body.translation_m,
    )

    print(
        "backbone_state.quaternion_wxyz=",
        state.pose_world_T_body.quaternion_wxyz,
    )

    print(
        "reference_data_used=false"
    )

    print(
        "confirmation_test_data_used=false"
    )

    print(
        "scan_temporal_reference_verified=false"
    )

    print(
        "per_point_time_used=false"
    )

    print(
        "deskew_performed=false"
    )

    print(
        "correspondence_rejection_used=false"
    )

    print(
        "voxel_downsampling_used=false"
    )

    print(
        "ate_computed=false"
    )

    print(
        "rpe_computed=false"
    )

    print(
        "trajectory_scoring_performed=false"
    )

    print(
        "phase2_real_lidar_pair_smoke=PASS"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
