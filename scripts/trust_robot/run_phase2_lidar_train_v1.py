#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path
from hashlib import sha256
import argparse
import json
import traceback

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
    pointcloud_header_stamp_ns,
    validate_lidar_frontend_config,
)
from trust_robot.lidar_train_run import (
    TRAIN_TRAJECTORIES,
    atomic_write_json,
    build_train_run_manifest,
    pair_record,
    sha256_file,
    trajectory_complete_record,
    trajectory_header_record,
)


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Run the frozen Phase-2 LiDAR frontend sequentially over the "
            "22 frozen M2DGR TRAIN trajectories. No reference data are read."
        )
    )

    parser.add_argument(
        "--repo-root",
        required=True,
    )

    parser.add_argument(
        "--dataset-root",
        required=True,
    )

    parser.add_argument(
        "--config",
        required=True,
    )

    parser.add_argument(
        "--output-dir",
        required=True,
    )

    return parser.parse_args()


def append_json_line(
    handle,
    payload,
):
    handle.write(
        json.dumps(
            payload,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        )
        + "\n"
    )

    handle.flush()


def main() -> int:
    args = parse_args()

    repo_root = Path(
        args.repo_root
    ).resolve()

    dataset_root = Path(
        args.dataset_root
    ).resolve()

    config_path = Path(
        args.config
    ).resolve()

    output_dir = Path(
        args.output_dir
    ).resolve()

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    scientific_outputs = (
        "run_manifest.json",
        "progress.json",
        "summary.json",
        "failure.json",
        "SUCCESS",
    )

    for name in scientific_outputs:
        if (
            output_dir
            / name
        ).exists():
            raise RuntimeError(
                f"refusing to overwrite existing run artifact: {name}"
            )

    trajectory_dir = (
        output_dir
        / "trajectories"
    )

    if trajectory_dir.exists():
        raise RuntimeError(
            "refusing to overwrite existing trajectories directory"
        )

    trajectory_dir.mkdir(
        parents=True,
        exist_ok=False,
    )

    config_payload = json.loads(
        config_path.read_text(
            encoding="utf-8"
        )
    )

    validate_lidar_frontend_config(
        config_payload
    )

    split_path = (
        repo_root
        / "manifests/"
          "m2dgr_trajectory_manifest_v1_split_freeze_v1.json"
    )

    component_paths = {
        "clean_backbone":
            repo_root
            / "src/trust_robot/clean_backbone.py",

        "lidar_frontend":
            repo_root
            / "src/trust_robot/lidar_frontend.py",

        "lidar_train_run":
            repo_root
            / "src/trust_robot/lidar_train_run.py",

        "run_script":
            Path(
                __file__
            ).resolve(),
    }

    component_hashes = {
        name:
            sha256_file(
                path
            )
        for name, path
        in component_paths.items()
    }

    bag_paths = {
        trajectory:
            (
                dataset_root
                / "raw"
                / "rosbags"
                / f"{trajectory}.bag"
            )
        for trajectory
        in TRAIN_TRAJECTORIES
    }

    for trajectory, path in bag_paths.items():
        if not path.is_file():
            raise RuntimeError(
                f"missing frozen TRAIN bag {trajectory}: {path}"
            )

    bag_sizes = {
        trajectory:
            path.stat().st_size
        for trajectory, path
        in bag_paths.items()
    }

    manifest = build_train_run_manifest(
        split_manifest_sha256=
            sha256_file(
                split_path
            ),

        frontend_config_file_sha256=
            sha256_file(
                config_path
            ),

        frontend_config_content_sha256=
            config_payload[
                "content_sha256"
            ],

        repo_component_hashes=
            component_hashes,

        bag_file_sizes_bytes=
            bag_sizes,
    )

    atomic_write_json(
        output_dir
        / "run_manifest.json",
        manifest,
    )

    completed = []

    current_trajectory = None
    current_scan_index = None
    current_previous_timestamp = None
    current_timestamp = None

    try:
        for trajectory_index, trajectory in enumerate(
            TRAIN_TRAJECTORIES,
            start=1,
        ):
            current_trajectory = trajectory
            current_scan_index = 0
            current_previous_timestamp = None
            current_timestamp = None

            bag = bag_paths[
                trajectory
            ]

            output_jsonl = (
                trajectory_dir
                / f"{trajectory}.jsonl"
            )

            if output_jsonl.exists():
                raise RuntimeError(
                    f"trajectory output unexpectedly exists: {output_jsonl}"
                )

            print(
                (
                    "TRAJECTORY_START "
                    f"index={trajectory_index}/"
                    f"{len(TRAIN_TRAJECTORIES)} "
                    f"trajectory={trajectory} "
                    f"bag={bag}"
                ),
                flush=True,
            )

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

                if len(
                    connections
                ) != 1:
                    raise RuntimeError(
                        (
                            f"{trajectory}: expected exactly one "
                            f"{EXPECTED_TOPIC} {EXPECTED_MSGTYPE} connection; "
                            f"found {len(connections)}"
                        )
                    )

                message_iterator = reader.messages(
                    connections=connections
                )

                try:
                    (
                        first_connection,
                        _first_bag_time,
                        first_rawdata,
                    ) = next(
                        message_iterator
                    )

                except StopIteration as exc:
                    raise RuntimeError(
                        f"{trajectory}: Velodyne stream is empty"
                    ) from exc

                previous_message = reader.deserialize(
                    first_rawdata,
                    first_connection.msgtype,
                )

                initial_timestamp = (
                    pointcloud_header_stamp_ns(
                        previous_message
                    )
                )

                current_timestamp = initial_timestamp

                backbone = FixedCleanBackbone(
                    CleanBackboneConfig(
                        world_frame_id=
                            "phase2_lidar_first_scan_origin",

                        body_frame_id=
                            "velodyne",

                        relative_pose_source_id=
                            SOURCE_ID,

                        initial_timestamp_ns=
                            initial_timestamp,

                        initial_pose_world_T_body=
                            PoseSE3.identity(),
                    )
                )

                scan_count = 1

                with output_jsonl.open(
                    "x",
                    encoding="utf-8",
                    buffering=1,
                ) as handle:
                    append_json_line(
                        handle,
                        trajectory_header_record(
                            trajectory=
                                trajectory,

                            initial_timestamp_ns=
                                initial_timestamp,
                        ),
                    )

                    atomic_write_json(
                        output_dir
                        / "progress.json",
                        {
                            "status":
                                "running",

                            "trajectory_index":
                                trajectory_index,

                            "trajectory_count":
                                len(
                                    TRAIN_TRAJECTORIES
                                ),

                            "trajectory":
                                trajectory,

                            "scan_count":
                                scan_count,

                            "pair_count":
                                0,

                            "last_header_stamp_ns":
                                initial_timestamp,

                            "completed_trajectories":
                                list(
                                    completed
                                ),

                            "reference_data_used":
                                False,

                            "confirmation_test_data_used":
                                False,
                        },
                    )

                    for (
                        connection,
                        _bag_time,
                        rawdata,
                    ) in message_iterator:
                        current_message = reader.deserialize(
                            rawdata,
                            connection.msgtype,
                        )

                        current_scan_index = scan_count

                        current_previous_timestamp = (
                            pointcloud_header_stamp_ns(
                                previous_message
                            )
                        )

                        current_timestamp = (
                            pointcloud_header_stamp_ns(
                                current_message
                            )
                        )

                        increment, diagnostics = (
                            build_relative_pose_increment(
                                previous_message=
                                    previous_message,

                                current_message=
                                    current_message,
                            )
                        )

                        state = backbone.apply(
                            increment
                        )

                        scan_count += 1

                        record = pair_record(
                            trajectory=
                                trajectory,

                            scan_index=
                                current_scan_index,

                            previous_timestamp_ns=
                                current_previous_timestamp,

                            increment=
                                increment,

                            state=
                                state,

                            diagnostics=
                                diagnostics,
                        )

                        append_json_line(
                            handle,
                            record,
                        )

                        atomic_write_json(
                            output_dir
                            / "progress.json",
                            {
                                "status":
                                    "running",

                                "trajectory_index":
                                    trajectory_index,

                                "trajectory_count":
                                    len(
                                        TRAIN_TRAJECTORIES
                                    ),

                                "trajectory":
                                    trajectory,

                                "scan_count":
                                    scan_count,

                                "pair_count":
                                    scan_count
                                    - 1,

                                "last_header_stamp_ns":
                                    current_timestamp,

                                "last_fixed_point_iterations":
                                    diagnostics.fixed_point_iterations,

                                "last_nearest_neighbor_rmse_m":
                                    diagnostics.final_nearest_neighbor_rmse_m,

                                "completed_trajectories":
                                    list(
                                        completed
                                    ),

                                "reference_data_used":
                                    False,

                                "confirmation_test_data_used":
                                    False,
                            },
                        )

                        print(
                            (
                                "PROGRESS "
                                f"trajectory={trajectory} "
                                f"scan_count={scan_count} "
                                f"pair_count={scan_count - 1} "
                                f"fixed_point_iterations="
                                f"{diagnostics.fixed_point_iterations} "
                                f"nn_rmse_m="
                                f"{diagnostics.final_nearest_neighbor_rmse_m}"
                            ),
                            flush=True,
                        )

                        previous_message = current_message

                    append_json_line(
                        handle,
                        trajectory_complete_record(
                            trajectory=
                                trajectory,

                            scan_count=
                                scan_count,

                            final_state=
                                backbone.state,
                        ),
                    )

            trajectory_sha = sha256_file(
                output_jsonl
            )

            trajectory_summary = {
                "trajectory":
                    trajectory,

                "bag_relative_path":
                    f"raw/rosbags/{trajectory}.bag",

                "bag_file_size_bytes":
                    bag_sizes[
                        trajectory
                    ],

                "scan_count":
                    scan_count,

                "increment_count":
                    scan_count
                    - 1,

                "first_header_stamp_ns":
                    initial_timestamp,

                "last_header_stamp_ns":
                    backbone.state.timestamp_ns,

                "trajectory_jsonl_sha256":
                    trajectory_sha,

                "final_state_world_T_lidar":
                    backbone.state.pose_world_T_body.to_dict(),

                "reference_data_used":
                    False,

                "confirmation_test_data_used":
                    False,

                "trajectory_scoring_performed":
                    False,
            }

            atomic_write_json(
                trajectory_dir
                / f"{trajectory}.summary.json",
                trajectory_summary,
            )

            completed.append(
                trajectory
            )

            atomic_write_json(
                output_dir
                / "progress.json",
                {
                    "status":
                        "running",

                    "trajectory_index":
                        trajectory_index,

                    "trajectory_count":
                        len(
                            TRAIN_TRAJECTORIES
                        ),

                    "trajectory":
                        trajectory,

                    "scan_count":
                        scan_count,

                    "pair_count":
                        scan_count
                        - 1,

                    "completed_trajectories":
                        list(
                            completed
                        ),

                    "reference_data_used":
                        False,

                    "confirmation_test_data_used":
                        False,
                },
            )

            print(
                (
                    "TRAJECTORY_COMPLETE "
                    f"index={trajectory_index}/"
                    f"{len(TRAIN_TRAJECTORIES)} "
                    f"trajectory={trajectory} "
                    f"scan_count={scan_count} "
                    f"trajectory_jsonl_sha256={trajectory_sha}"
                ),
                flush=True,
            )

        summaries = []

        for trajectory in TRAIN_TRAJECTORIES:
            summary_path = (
                trajectory_dir
                / f"{trajectory}.summary.json"
            )

            summaries.append(
                json.loads(
                    summary_path.read_text(
                        encoding="utf-8"
                    )
                )
            )

        summary: dict[str, object] = {
            "schema":
                "TRUST_ROBOT_PHASE2_CLEAN_LIDAR_TRAIN_SUMMARY_V1",

            "schema_version":
                1,

            "status":
                "completed",

            "run_manifest_content_sha256":
                manifest[
                    "content_sha256"
                ],

            "trajectory_count":
                len(
                    summaries
                ),

            "trajectory_order":
                list(
                    TRAIN_TRAJECTORIES
                ),

            "total_scan_count":
                sum(
                    item[
                        "scan_count"
                    ]
                    for item
                    in summaries
                ),

            "total_increment_count":
                sum(
                    item[
                        "increment_count"
                    ]
                    for item
                    in summaries
                ),

            "trajectories":
                summaries,

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

        raw = json.dumps(
            summary,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode(
            "utf-8"
        )

        summary[
            "content_sha256"
        ] = sha256(
            raw
        ).hexdigest()

        atomic_write_json(
            output_dir
            / "summary.json",
            summary,
        )

        atomic_write_json(
            output_dir
            / "progress.json",
            {
                "status":
                    "completed",

                "trajectory_count":
                    len(
                        TRAIN_TRAJECTORIES
                    ),

                "completed_trajectories":
                    list(
                        TRAIN_TRAJECTORIES
                    ),

                "total_scan_count":
                    summary[
                        "total_scan_count"
                    ],

                "total_increment_count":
                    summary[
                        "total_increment_count"
                    ],

                "reference_data_used":
                    False,

                "confirmation_test_data_used":
                    False,
            },
        )

        (
            output_dir
            / "SUCCESS"
        ).write_text(
            (
                "TRUST_ROBOT_PHASE2_CLEAN_LIDAR_FULL_TRAIN_RUN_V1=PASS\n"
                "reference_data_used=false\n"
                "confirmation_test_data_used=false\n"
                "ate_computed=false\n"
                "rpe_computed=false\n"
                "trajectory_scoring_performed=false\n"
            ),
            encoding="utf-8",
        )

        print(
            (
                "TRAIN_RUN_COMPLETE "
                f"trajectory_count={len(TRAIN_TRAJECTORIES)} "
                f"total_scan_count={summary['total_scan_count']} "
                f"total_increment_count="
                f"{summary['total_increment_count']}"
            ),
            flush=True,
        )

        print(
            "TRUST_ROBOT_PHASE2_CLEAN_LIDAR_FULL_TRAIN_RUN_V1=PASS",
            flush=True,
        )

        return 0

    except Exception as exc:
        failure = {
            "schema":
                "TRUST_ROBOT_PHASE2_CLEAN_LIDAR_TRAIN_FAILURE_V1",

            "status":
                "failed_closed",

            "trajectory":
                current_trajectory,

            "scan_index":
                current_scan_index,

            "previous_header_stamp_ns":
                current_previous_timestamp,

            "current_header_stamp_ns":
                current_timestamp,

            "exception_type":
                type(
                    exc
                ).__name__,

            "exception_message":
                str(
                    exc
                ),

            "completed_trajectories":
                list(
                    completed
                ),

            "scientific_scope": {
                "scan_skipped":
                    False,

                "trajectory_skipped":
                    False,

                "reference_data_used":
                    False,

                "confirmation_test_data_used":
                    False,

                "ate_computed":
                    False,

                "rpe_computed":
                    False,

                "trajectory_scoring_performed":
                    False,
            },
        }

        atomic_write_json(
            output_dir
            / "failure.json",
            failure,
        )

        atomic_write_json(
            output_dir
            / "progress.json",
            {
                "status":
                    "failed_closed",

                "trajectory":
                    current_trajectory,

                "scan_index":
                    current_scan_index,

                "completed_trajectories":
                    list(
                        completed
                    ),

                "reference_data_used":
                    False,

                "confirmation_test_data_used":
                    False,
            },
        )

        print(
            "TRAIN_RUN_FAILED_CLOSED",
            flush=True,
        )

        traceback.print_exc()

        raise


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
