#!/usr/bin/env python3
"""Run Phase-5 camera/IMU raw-observation ingestion over frozen M2DGR TRAIN.

Only the exact 22 TRAIN bags are opened.

Only:
- /camera/color/image_raw/compressed
- /camera/imu
- /handsfree/imu

are read.

No validation or confirmation-test bag is opened.
No reference, GT, GNSS, pose, odometry or TF stream is read.
"""

from __future__ import annotations

import argparse
from hashlib import sha256
from pathlib import Path
from typing import Any
import json
import os
import shutil
import sys

from rosbags.highlevel import AnyReader

from trust_robot.camera_imu_observation_adapter import (
    build_raw_observation_receipt,
)
from trust_robot.camera_imu_train_ingestion import (
    RUN_ID,
    SCHEMA,
    SUPPORTED_STREAMS,
    TRAIN_TRAJECTORIES,
    build_candidate_manifest,
    content_sha256,
    empty_stream_builders,
    header_stamp_ns_from_message,
)


def canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def file_sha256(path: Path) -> str:
    h = sha256()

    with path.open("rb") as handle:
        for block in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            h.update(block)

    return h.hexdigest()


def atomic_json(path: Path, payload: Any) -> None:
    temporary = path.with_name(
        path.name + ".partial"
    )

    temporary.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    os.replace(
        temporary,
        path,
    )


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--dataset-root",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
    )

    args = parser.parse_args()

    dataset_root = args.dataset_root.resolve()
    output_dir = args.output_dir.resolve()

    bag_root = (
        dataset_root
        / "raw"
        / "rosbags"
    )

    if not bag_root.is_dir():
        raise RuntimeError(
            f"bag root does not exist: {bag_root}"
        )

    if output_dir.exists():
        raise RuntimeError(
            f"output directory already exists: {output_dir}"
        )

    staging = output_dir.with_name(
        output_dir.name + ".partial"
    )

    if staging.exists():
        raise RuntimeError(
            f"partial output already exists: {staging}"
        )

    staging.mkdir(
        parents=True,
        exist_ok=False,
    )

    trajectory_dir = (
        staging
        / "trajectories"
    )

    trajectory_dir.mkdir()

    try:
        candidate = build_candidate_manifest()

        atomic_json(
            staging / "candidate_contract.json",
            candidate,
        )

        run_trajectory_records = []

        total_messages = 0
        total_payload_bytes = 0

        aggregate_run_digest = sha256()

        for trajectory_id in TRAIN_TRAJECTORIES:
            bag_path = (
                bag_root
                / f"{trajectory_id}.bag"
            )

            if not bag_path.is_file():
                raise RuntimeError(
                    f"TRAIN bag missing: {bag_path}"
                )

            print(
                f"trajectory_start={trajectory_id}",
                flush=True,
            )

            builders = empty_stream_builders(
                trajectory_id
            )

            per_stream_index = {
                stream: 0
                for stream in SUPPORTED_STREAMS
            }

            with AnyReader(
                [bag_path]
            ) as reader:
                selected = [
                    connection
                    for connection in reader.connections
                    if connection.topic in SUPPORTED_STREAMS
                ]

                for connection, timestamp, rawdata in reader.messages(
                    connections=selected
                ):
                    source_stream_id = (
                        connection.topic
                    )

                    raw_bytes = bytes(
                        rawdata
                    )

                    message = reader.deserialize(
                        rawdata,
                        connection.msgtype,
                    )

                    header_stamp_ns = (
                        header_stamp_ns_from_message(
                            message
                        )
                    )

                    receipt = build_raw_observation_receipt(
                        source_stream_id=source_stream_id,
                        trajectory_or_session_id=trajectory_id,
                        split_role="train",
                        message_index=per_stream_index[
                            source_stream_id
                        ],
                        serialized_payload=raw_bytes,
                        bag_record_time_ns=int(
                            timestamp
                        ),
                        header_stamp_ns=header_stamp_ns,
                        message_type=connection.msgtype,
                    )

                    builders[
                        source_stream_id
                    ].add(
                        receipt
                    )

                    per_stream_index[
                        source_stream_id
                    ] += 1

            stream_payloads = [
                builders[
                    stream
                ].payload()
                for stream in SUPPORTED_STREAMS
            ]

            trajectory_payload = {
                "schema":
                    SCHEMA,

                "run_id":
                    RUN_ID,

                "trajectory_id":
                    trajectory_id,

                "split_role":
                    "train",

                "bag_relative_path":
                    (
                        f"raw/rosbags/"
                        f"{trajectory_id}.bag"
                    ),

                "bag_size_bytes":
                    bag_path.stat().st_size,

                "streams":
                    stream_payloads,

                "scientific_boundary": {
                    "feature_extraction_performed":
                        False,

                    "health_label_assigned":
                        False,

                    "classifier_training_authorized":
                        False,

                    "physical_measurement_time_selected":
                        False,

                    "reference_data_read":
                        False,

                    "confirmation_data_read":
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
                trajectory_dir
                / f"{trajectory_id}.json"
            )

            atomic_json(
                trajectory_path,
                trajectory_payload,
            )

            trajectory_file_sha = file_sha256(
                trajectory_path
            )

            trajectory_messages = sum(
                stream[
                    "message_count"
                ]
                for stream in stream_payloads
            )

            trajectory_bytes = sum(
                stream[
                    "total_serialized_payload_bytes"
                ]
                for stream in stream_payloads
            )

            total_messages += (
                trajectory_messages
            )

            total_payload_bytes += (
                trajectory_bytes
            )

            digest_record = {
                "trajectory_id":
                    trajectory_id,

                "trajectory_file_sha256":
                    trajectory_file_sha,

                "trajectory_content_sha256":
                    trajectory_payload[
                        "content_sha256"
                    ],

                "message_count":
                    trajectory_messages,

                "total_serialized_payload_bytes":
                    trajectory_bytes,
            }

            aggregate_run_digest.update(
                canonical_json_bytes(
                    digest_record
                )
            )
            aggregate_run_digest.update(
                b"\n"
            )

            run_trajectory_records.append(
                digest_record
            )

            print(
                "trajectory_complete="
                f"{trajectory_id} "
                f"messages={trajectory_messages} "
                f"bytes={trajectory_bytes}",
                flush=True,
            )

        run_manifest = {
            "schema":
                "TRUST_ROBOT_PHASE5_CAMERA_IMU_TRAIN_INGESTION_RUN_V1",

            "run_id":
                RUN_ID,

            "candidate_contract_sha256":
                content_sha256(
                    candidate
                ),

            "dataset_root":
                str(
                    dataset_root
                ),

            "train_trajectory_count":
                len(
                    TRAIN_TRAJECTORIES
                ),

            "trajectory_records":
                run_trajectory_records,

            "aggregate_trajectory_record_sha256":
                aggregate_run_digest.hexdigest(),

            "total_selected_stream_messages":
                total_messages,

            "total_selected_serialized_payload_bytes":
                total_payload_bytes,

            "scientific_boundary": {
                "train_only":
                    True,

                "validation_bags_opened":
                    False,

                "confirmation_bags_opened":
                    False,

                "reference_data_read":
                    False,

                "feature_extraction_performed":
                    False,

                "health_labels_assigned":
                    False,

                "classifier_training_authorized":
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

        atomic_json(
            staging / "run_manifest.json",
            run_manifest,
        )

        success_payload = {
            "run_id":
                RUN_ID,

            "run_manifest_file_sha256":
                file_sha256(
                    staging
                    / "run_manifest.json"
                ),

            "run_manifest_content_sha256":
                run_manifest[
                    "content_sha256"
                ],

            "train_trajectory_count":
                len(
                    TRAIN_TRAJECTORIES
                ),

            "total_selected_stream_messages":
                total_messages,

            "classifier_training_authorized":
                False,

            "confirmation_bags_opened":
                False,
        }

        atomic_json(
            staging / "SUCCESS.json",
            success_payload,
        )

        os.replace(
            staging,
            output_dir,
        )

        print(
            "TRAIN_CAMERA_IMU_INGESTION=PASS",
            flush=True,
        )

        print(
            f"output_dir={output_dir}",
            flush=True,
        )

        return 0

    except BaseException:
        if staging.exists():
            shutil.rmtree(
                staging
            )

        raise


if __name__ == "__main__":
    sys.exit(
        main()
    )
