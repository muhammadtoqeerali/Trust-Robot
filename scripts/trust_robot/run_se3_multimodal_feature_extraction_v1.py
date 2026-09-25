#!/usr/bin/env python3

from __future__ import annotations

import argparse
from contextlib import ExitStack
from pathlib import Path
import json
import os
import shutil
import sys

from rosbags.highlevel import AnyReader

from trust_robot.deterministic_multimodal_dataset_replay import (
    load_train_replay_source_from_manifest_file,
    resolve_train_bag_path,
)

from trust_robot.se3_multimodal_feature_contract import (
    extract_camera_features,
    extract_imu_features,
)

from trust_robot.se3_multimodal_feature_extraction import (
    CAMERA_STREAM,
    CANDIDATE_SCHEMA,
    FEATURE_CONTRACT_CONFIG_SHA256,
    FROZEN_SPLIT_SHA256,
    FeatureRecord,
    FeatureStreamAccumulator,
    IMU_STREAMS,
    RUN_ID,
    RUN_SCHEMA,
    SUCCESS_SCHEMA,
    SUPPORTED_STREAMS,
    TRAIN_TRAJECTORIES,
    TRAJECTORY_SCHEMA,
    build_candidate_manifest,
    canonical_json_bytes,
    content_sha256,
    feature_record_line,
    file_sha256,
    stream_file_name,
)


REPO_ROOT = (
    Path(__file__).resolve().parents[2]
)

SPLIT_MANIFEST = (
    REPO_ROOT
    / "manifests"
    / "m2dgr_trajectory_manifest_v1_split_freeze_v1.json"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--dataset-root",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--output-root",
        required=True,
        type=Path,
    )

    return parser.parse_args()


def write_json(
    path: Path,
    payload: dict[str, object],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def header_stamp_ns(
    message: object,
) -> int | None:
    header = getattr(
        message,
        "header",
        None,
    )

    if header is None:
        return None

    stamp = getattr(
        header,
        "stamp",
        None,
    )

    if stamp is None:
        return None

    sec = getattr(
        stamp,
        "sec",
        None,
    )

    nanosec = getattr(
        stamp,
        "nanosec",
        None,
    )

    if (
        type(sec) is not int
        or type(nanosec) is not int
    ):
        return None

    if sec < 0 or nanosec < 0:
        return None

    return (
        sec * 1_000_000_000
        + nanosec
    )


def features_for_message(
    *,
    stream_id: str,
    message: object,
) -> tuple[float, ...]:
    if stream_id == CAMERA_STREAM:
        return tuple(
            float(value)
            for value in extract_camera_features(
                bytes(
                    message.data
                )
            )
        )

    if stream_id in IMU_STREAMS:
        angular = message.angular_velocity
        acceleration = message.linear_acceleration

        return tuple(
            float(value)
            for value in extract_imu_features(
                (
                    angular.x,
                    angular.y,
                    angular.z,
                ),
                (
                    acceleration.x,
                    acceleration.y,
                    acceleration.z,
                ),
            )
        )

    raise RuntimeError(
        f"unsupported stream {stream_id!r}"
    )


def main() -> int:
    args = parse_args()

    dataset_root = (
        args.dataset_root.resolve()
    )

    output_root = (
        args.output_root.resolve()
    )

    partial_root = Path(
        str(
            output_root
        )
        + ".partial"
    )

    if not dataset_root.is_dir():
        raise RuntimeError(
            f"dataset root does not exist: {dataset_root}"
        )

    if output_root.exists():
        raise RuntimeError(
            f"output root already exists: {output_root}"
        )

    if partial_root.exists():
        raise RuntimeError(
            f"partial output already exists: {partial_root}"
        )

    partial_root.mkdir(
        parents=True
    )

    try:
        candidate = (
            build_candidate_manifest()
        )

        candidate_path = (
            partial_root
            / "candidate_contract.json"
        )

        write_json(
            candidate_path,
            candidate,
        )

        trajectory_records = []

        total_feature_records = 0
        total_camera_records = 0
        total_imu_records = 0
        total_source_bytes = 0

        aggregate_trajectory_digest = __import__(
            "hashlib"
        ).sha256()

        for trajectory_id in TRAIN_TRAJECTORIES:
            source = (
                load_train_replay_source_from_manifest_file(
                    SPLIT_MANIFEST,
                    trajectory_id,
                    expected_file_sha256=FROZEN_SPLIT_SHA256,
                )
            )

            bag_path = resolve_train_bag_path(
                dataset_root,
                source,
            )

            actual_bag_sha256 = file_sha256(
                bag_path
            )

            if (
                actual_bag_sha256
                != source.bag_sha256
            ):
                raise RuntimeError(
                    "TRAIN bag SHA-256 differs from frozen split manifest: "
                    f"{trajectory_id}"
                )

            print(
                "SE3_TRAJECTORY_START "
                f"trajectory={trajectory_id} "
                f"bag={bag_path}",
                flush=True,
            )

            accumulators = {
                stream_id:
                    FeatureStreamAccumulator(
                        trajectory_id=trajectory_id,
                        source_stream_id=stream_id,
                    )
                for stream_id in SUPPORTED_STREAMS
            }

            feature_dir = (
                partial_root
                / "features"
                / trajectory_id
            )

            stream_handles = {}
            selected_reader_index = 0

            with ExitStack() as stack:
                with AnyReader(
                    [
                        bag_path
                    ]
                ) as reader:
                    connections = [
                        connection
                        for connection in reader.connections
                        if connection.topic in SUPPORTED_STREAMS
                    ]

                    connection_topics = {
                        connection.topic
                        for connection in connections
                    }

                    unsupported_selected = (
                        connection_topics
                        - set(
                            SUPPORTED_STREAMS
                        )
                    )

                    if unsupported_selected:
                        raise RuntimeError(
                            "unexpected selected streams: "
                            + repr(
                                unsupported_selected
                            )
                        )

                    for (
                        connection,
                        timestamp,
                        rawdata,
                    ) in reader.messages(
                        connections=connections
                    ):
                        stream_id = (
                            connection.topic
                        )

                        accumulator = (
                            accumulators[
                                stream_id
                            ]
                        )

                        message = reader.deserialize(
                            rawdata,
                            connection.msgtype,
                        )

                        values = (
                            features_for_message(
                                stream_id=stream_id,
                                message=message,
                            )
                        )

                        record = FeatureRecord(
                            trajectory_id=trajectory_id,
                            source_stream_id=stream_id,
                            selected_reader_index=selected_reader_index,
                            stream_index=accumulator.record_count,
                            bag_record_time_ns=int(
                                timestamp
                            ),
                            header_stamp_ns=header_stamp_ns(
                                message
                            ),
                            feature_values=values,
                        )

                        line = feature_record_line(
                            record
                        )

                        if stream_id not in stream_handles:
                            feature_dir.mkdir(
                                parents=True,
                                exist_ok=True,
                            )

                            feature_path = (
                                feature_dir
                                / stream_file_name(
                                    stream_id
                                )
                            )

                            stream_handles[
                                stream_id
                            ] = stack.enter_context(
                                feature_path.open(
                                    "wb"
                                )
                            )

                        stream_handles[
                            stream_id
                        ].write(
                            line
                        )

                        accumulator.add(
                            raw_serialized_payload=bytes(
                                rawdata
                            ),
                            record=record,
                            serialized_line=line,
                        )

                        selected_reader_index += 1

            stream_summaries = {}

            for stream_id in SUPPORTED_STREAMS:
                accumulator = (
                    accumulators[
                        stream_id
                    ]
                )

                if accumulator.record_count:
                    relative_path = (
                        Path(
                            "features"
                        )
                        / trajectory_id
                        / stream_file_name(
                            stream_id
                        )
                    )

                    feature_path = (
                        partial_root
                        / relative_path
                    )

                    expected_digest = (
                        accumulator.summary(
                            feature_file_relative_path=str(
                                relative_path
                            )
                        )[
                            "feature_file_sha256"
                        ]
                    )

                    actual_digest = file_sha256(
                        feature_path
                    )

                    if (
                        expected_digest
                        != actual_digest
                    ):
                        raise RuntimeError(
                            "feature file digest mismatch"
                        )

                    summary = accumulator.summary(
                        feature_file_relative_path=str(
                            relative_path
                        )
                    )

                else:
                    summary = accumulator.summary(
                        feature_file_relative_path=None
                    )

                stream_summaries[
                    stream_id
                ] = summary

                total_feature_records += (
                    accumulator.record_count
                )

                total_source_bytes += (
                    accumulator.source_serialized_payload_bytes
                )

                if stream_id == CAMERA_STREAM:
                    total_camera_records += (
                        accumulator.record_count
                    )
                else:
                    total_imu_records += (
                        accumulator.record_count
                    )

            trajectory_payload = {
                "schema":
                    TRAJECTORY_SCHEMA,

                "run_id":
                    RUN_ID,

                "trajectory_id":
                    trajectory_id,

                "split_role":
                    "train",

                "source_bag_relative_path":
                    source.bag_relative_path,

                "source_bag_sha256":
                    actual_bag_sha256,

                "selected_feature_record_count":
                    selected_reader_index,

                "streams":
                    stream_summaries,

                "scientific_boundary": {
                    "health_labels_assigned":
                        False,

                    "model_training_performed":
                        False,

                    "validation_data_used":
                        False,

                    "confirmation_data_used":
                        False,

                    "reference_data_used":
                        False,

                    "cross_modal_alignment_performed":
                        False,

                    "ate_rpe_computed":
                        False,

                    "final_score_computed":
                        False,
                },
            }

            trajectory_payload[
                "content_sha256"
            ] = content_sha256(
                trajectory_payload
            )

            trajectory_path = (
                partial_root
                / "trajectories"
                / f"{trajectory_id}.json"
            )

            write_json(
                trajectory_path,
                trajectory_payload,
            )

            trajectory_file_sha = file_sha256(
                trajectory_path
            )

            trajectory_record = {
                "trajectory_id":
                    trajectory_id,

                "feature_record_count":
                    selected_reader_index,

                "trajectory_content_sha256":
                    trajectory_payload[
                        "content_sha256"
                    ],

                "trajectory_file_sha256":
                    trajectory_file_sha,
            }

            aggregate_trajectory_digest.update(
                canonical_json_bytes(
                    trajectory_record
                )
            )

            trajectory_records.append(
                trajectory_record
            )

            print(
                "SE3_TRAJECTORY_COMPLETE "
                f"trajectory={trajectory_id} "
                f"records={selected_reader_index}",
                flush=True,
            )

        candidate_file_sha = file_sha256(
            candidate_path
        )

        run_manifest = {
            "schema":
                RUN_SCHEMA,

            "run_id":
                RUN_ID,

            "dataset_root":
                str(
                    dataset_root
                ),

            "split_role":
                "train",

            "train_trajectory_count":
                len(
                    TRAIN_TRAJECTORIES
                ),

            "candidate_schema":
                CANDIDATE_SCHEMA,

            "candidate_content_sha256":
                candidate[
                    "content_sha256"
                ],

            "candidate_file_sha256":
                candidate_file_sha,

            "feature_contract_config_sha256":
                FEATURE_CONTRACT_CONFIG_SHA256,

            "aggregate_trajectory_record_sha256":
                aggregate_trajectory_digest.hexdigest(),

            "total_feature_records":
                total_feature_records,

            "total_camera_feature_records":
                total_camera_records,

            "total_imu_feature_records":
                total_imu_records,

            "total_source_serialized_payload_bytes":
                total_source_bytes,

            "trajectory_records":
                trajectory_records,

            "scientific_boundary": {
                "train_only":
                    True,

                "validation_bags_opened":
                    False,

                "confirmation_bags_opened":
                    False,

                "reference_data_read":
                    False,

                "health_labels_assigned":
                    False,

                "health_probabilities_emitted":
                    False,

                "model_training_performed":
                    False,

                "supervised_feature_selection_performed":
                    False,

                "calibration_performed":
                    False,

                "cross_modal_alignment_performed":
                    False,

                "ate_rpe_computed":
                    False,

                "final_score_computed":
                    False,
            },
        }

        run_manifest[
            "content_sha256"
        ] = content_sha256(
            run_manifest
        )

        run_path = (
            partial_root
            / "run_manifest.json"
        )

        write_json(
            run_path,
            run_manifest,
        )

        run_file_sha = file_sha256(
            run_path
        )

        success = {
            "schema":
                SUCCESS_SCHEMA,

            "run_id":
                RUN_ID,

            "run_manifest_content_sha256":
                run_manifest[
                    "content_sha256"
                ],

            "run_manifest_file_sha256":
                run_file_sha,

            "feature_contract_config_sha256":
                FEATURE_CONTRACT_CONFIG_SHA256,

            "train_trajectory_count":
                len(
                    TRAIN_TRAJECTORIES
                ),

            "total_feature_records":
                total_feature_records,

            "total_camera_feature_records":
                total_camera_records,

            "total_imu_feature_records":
                total_imu_records,

            "model_training_authorized":
                False,

            "validation_bags_opened":
                False,

            "confirmation_bags_opened":
                False,
        }

        success_path = (
            partial_root
            / "SUCCESS.json"
        )

        write_json(
            success_path,
            success,
        )

        os.replace(
            partial_root,
            output_root,
        )

        print(
            "TRUST_ROBOT_SE3_MULTIMODAL_FEATURE_EXTRACTION_V1=PASS",
            flush=True,
        )

        print(
            f"OUTPUT_ROOT={output_root}",
            flush=True,
        )

        print(
            f"TOTAL_FEATURE_RECORDS={total_feature_records}",
            flush=True,
        )

        return 0

    except Exception:
        if partial_root.exists():
            shutil.rmtree(
                partial_root,
                ignore_errors=True,
            )

        raise


if __name__ == "__main__":
    sys.exit(
        main()
    )
