#!/usr/bin/env python3

from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
from pathlib import Path
from typing import Any
import json
import os
import shutil

from rosbags.highlevel import AnyReader

from trust_robot.ml_lidar_event_gap_registration_dataset import (
    ALL_TRAIN,
    DEVELOPMENT_CHECK,
    DEVELOPMENT_TRAIN,
    EXPECTED_DIAGNOSTIC_COUNTS,
    FEATURE_NAMES,
    build_paired_samples_from_messages,
    build_selection_binding,
    content_sha256,
    evenly_spaced_window_starts,
    partition_for_trajectory,
    validate_config,
)


TOPIC = "/velodyne_points"


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


def canonical_line(
    payload: dict[str, Any],
) -> bytes:
    return (
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode(
        "utf-8"
    )


def process_trajectory(
    *,
    dataset_root: Path,
    trajectory: str,
    output_handle,
    provenance_handle,
) -> dict[str, Any]:
    partition = partition_for_trajectory(
        trajectory
    )

    diagnostic_count = (
        EXPECTED_DIAGNOSTIC_COUNTS[
            trajectory
        ]
    )

    expected_scan_count = (
        diagnostic_count
        + 1
    )

    starts = evenly_spaced_window_starts(
        diagnostic_count
    )

    start_pointer = 0
    active_start = starts[
        start_pointer
    ]

    current_messages = []

    total_velodyne_messages = 0
    selected_deserialized_messages = 0
    completed_windows = 0
    written_samples = 0
    class_counts = Counter()

    output_digest = sha256()
    provenance_digest = sha256()

    bag = (
        dataset_root
        / "raw"
        / "rosbags"
        / (
            trajectory
            + ".bag"
        )
    )

    if not bag.is_file():
        raise RuntimeError(
            "missing TRAIN bag: "
            + str(
                bag
            )
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
            if connection.topic
            == TOPIC
        ]

        if not connections:
            raise RuntimeError(
                trajectory
                + " has no "
                + TOPIC
            )

        for (
            connection,
            _record_time,
            rawdata,
        ) in reader.messages(
            connections=
                connections
        ):
            scan_index = (
                total_velodyne_messages
            )

            total_velodyne_messages += 1

            if start_pointer >= len(
                starts
            ):
                continue

            active_start = starts[
                start_pointer
            ]

            if scan_index < active_start:
                continue

            if scan_index > (
                active_start
                + 2
            ):
                raise RuntimeError(
                    "selected window was skipped before completion"
                )

            if (
                active_start
                <= scan_index
                <= active_start + 2
            ):
                message = reader.deserialize(
                    rawdata,
                    connection.msgtype,
                )

                current_messages.append(
                    message
                )

                selected_deserialized_messages += 1

            if scan_index == (
                active_start
                + 2
            ):
                if len(
                    current_messages
                ) != 3:
                    raise RuntimeError(
                        "selected window did not contain exactly three messages"
                    )

                (
                    clean_sample,
                    gap_sample,
                    provenance,
                ) = build_paired_samples_from_messages(
                    trajectory=
                        trajectory,

                    window_start_scan_index=
                        active_start,

                    messages=
                        tuple(
                            current_messages
                        ),
                )

                for sample in (
                    clean_sample,
                    gap_sample,
                ):
                    line = canonical_line(
                        sample
                    )

                    output_handle.write(
                        line
                    )

                    output_digest.update(
                        line
                    )

                    written_samples += 1

                    class_counts[
                        str(
                            sample[
                                "label"
                            ]
                        )
                    ] += 1

                provenance_line = canonical_line(
                    provenance
                )

                provenance_handle.write(
                    provenance_line
                )

                provenance_digest.update(
                    provenance_line
                )

                completed_windows += 1

                current_messages = []

                start_pointer += 1

    if total_velodyne_messages != expected_scan_count:
        raise RuntimeError(
            trajectory
            + " Velodyne scan count mismatch: "
            + str(
                total_velodyne_messages
            )
            + " != "
            + str(
                expected_scan_count
            )
        )

    if start_pointer != len(
        starts
    ):
        raise RuntimeError(
            trajectory
            + " did not complete every selected window"
        )

    if completed_windows != 100:
        raise RuntimeError(
            trajectory
            + " selected window count changed"
        )

    if selected_deserialized_messages != 300:
        raise RuntimeError(
            trajectory
            + " selected deserialized scan count changed"
        )

    if written_samples != 200:
        raise RuntimeError(
            trajectory
            + " paired sample count changed"
        )

    if class_counts != Counter(
        {
            "0": 100,
            "1": 100,
        }
    ):
        raise RuntimeError(
            trajectory
            + " class balance changed"
        )

    return {
        "trajectory":
            trajectory,

        "development_partition":
            partition,

        "bag_relative_path":
            "raw/rosbags/"
            + trajectory
            + ".bag",

        "total_velodyne_messages":
            total_velodyne_messages,

        "selected_window_count":
            completed_windows,

        "selected_deserialized_scan_count":
            selected_deserialized_messages,

        "sample_count":
            written_samples,

        "class_counts":
            dict(
                sorted(
                    class_counts.items()
                )
            ),

        "first_selected_window_start":
            starts[
                0
            ],

        "last_selected_window_start":
            starts[
                -1
            ],

        "minimum_selected_window_start_gap":
            min(
                right - left
                for left, right
                in zip(
                    starts,
                    starts[
                        1:
                    ],
                )
            ),

        "sample_stream_incremental_sha256":
            output_digest.hexdigest(),

        "provenance_stream_incremental_sha256":
            provenance_digest.hexdigest(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--dataset-root",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--config",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
    )

    args = parser.parse_args()

    dataset_root = (
        args.dataset_root.resolve()
    )

    config_path = (
        args.config.resolve()
    )

    output_dir = (
        args.output_dir.resolve()
    )

    config = json.loads(
        config_path.read_text(
            encoding="utf-8"
        )
    )

    validate_config(
        config
    )

    if output_dir.exists():
        raise RuntimeError(
            "output directory already exists"
        )

    staging = output_dir.with_name(
        "."
        + output_dir.name
        + ".partial"
    )

    if staging.exists():
        raise RuntimeError(
            "staging directory already exists"
        )

    staging.mkdir(
        parents=True,
        exist_ok=False,
    )

    train_samples_path = (
        staging
        / "development_train.jsonl"
    )

    check_samples_path = (
        staging
        / "development_check.jsonl"
    )

    provenance_path = (
        staging
        / "window_provenance.jsonl"
    )

    trajectory_records = []

    try:
        with train_samples_path.open(
            "wb"
        ) as train_handle, \
        check_samples_path.open(
            "wb"
        ) as check_handle, \
        provenance_path.open(
            "wb"
        ) as provenance_handle:

            for trajectory in ALL_TRAIN:
                partition = (
                    partition_for_trajectory(
                        trajectory
                    )
                )

                output_handle = (
                    train_handle
                    if partition
                    == "development_train"
                    else check_handle
                )

                print(
                    "TRAJECTORY_BEGIN="
                    + trajectory
                    + " partition="
                    + partition,
                    flush=True,
                )

                record = process_trajectory(
                    dataset_root=
                        dataset_root,

                    trajectory=
                        trajectory,

                    output_handle=
                        output_handle,

                    provenance_handle=
                        provenance_handle,
                )

                trajectory_records.append(
                    record
                )

                print(
                    "TRAJECTORY_COMPLETE="
                    + trajectory
                    + " windows="
                    + str(
                        record[
                            "selected_window_count"
                        ]
                    )
                    + " samples="
                    + str(
                        record[
                            "sample_count"
                        ]
                    ),
                    flush=True,
                )

        development_train_samples = sum(
            record[
                "sample_count"
            ]
            for record
            in trajectory_records
            if record[
                "development_partition"
            ]
            == "development_train"
        )

        development_check_samples = sum(
            record[
                "sample_count"
            ]
            for record
            in trajectory_records
            if record[
                "development_partition"
            ]
            == "development_check"
        )

        total_windows = sum(
            record[
                "selected_window_count"
            ]
            for record
            in trajectory_records
        )

        if development_train_samples != 3400:
            raise RuntimeError(
                "development-train sample count mismatch"
            )

        if development_check_samples != 1000:
            raise RuntimeError(
                "development-check sample count mismatch"
            )

        if total_windows != 2200:
            raise RuntimeError(
                "total window count mismatch"
            )

        manifest = {
            "schema":
                "TRUST_ROBOT_M2DGR_LIDAR_EVENT_GAP_REGISTRATION_DATASET_RUN_V1",

            "schema_version":
                1,

            "config_file":
                str(
                    args.config
                ),

            "config_file_sha256":
                sha256_file(
                    config_path
                ),

            "config_content_sha256":
                config[
                    "content_sha256"
                ],

            "selection_binding":
                build_selection_binding(),

            "trajectory_records":
                trajectory_records,

            "outputs": {
                "development_train": {
                    "file":
                        train_samples_path.name,

                    "sha256":
                        sha256_file(
                            train_samples_path
                        ),

                    "sample_count":
                        development_train_samples,
                },

                "development_check": {
                    "file":
                        check_samples_path.name,

                    "sha256":
                        sha256_file(
                            check_samples_path
                        ),

                    "sample_count":
                        development_check_samples,
                },

                "window_provenance": {
                    "file":
                        provenance_path.name,

                    "sha256":
                        sha256_file(
                            provenance_path
                        ),

                    "record_count":
                        total_windows,
                },
            },

            "totals": {
                "trajectory_count":
                    22,

                "development_train_trajectory_count":
                    17,

                "development_check_trajectory_count":
                    5,

                "selected_window_count":
                    total_windows,

                "selected_deserialized_scan_count":
                    sum(
                        record[
                            "selected_deserialized_scan_count"
                        ]
                        for record
                        in trajectory_records
                    ),

                "sample_count":
                    (
                        development_train_samples
                        + development_check_samples
                    ),

                "class_0_count":
                    2200,

                "class_1_count":
                    2200,
            },

            "scientific_boundary": {
                "TRAIN_only":
                    True,

                "synthetic_intervention_truth":
                    True,

                "real_physical_health_truth":
                    False,

                "model_fit_executed":
                    False,

                "health_state_assignment":
                    False,

                "VALIDATION_open":
                    False,

                "CONFIRMATION_open":
                    False,

                "reference_data_used":
                    False,

                "ATE_RPE":
                    False,
            },
        }

        manifest[
            "content_sha256"
        ] = content_sha256(
            manifest
        )

        manifest_path = (
            staging
            / "run_manifest.json"
        )

        manifest_path.write_text(
            json.dumps(
                manifest,
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

        success = {
            "schema":
                "TRUST_ROBOT_M2DGR_LIDAR_EVENT_GAP_REGISTRATION_DATASET_SUCCESS_V1",

            "run_manifest_sha256":
                sha256_file(
                    manifest_path
                ),

            "development_train_sha256":
                sha256_file(
                    train_samples_path
                ),

            "development_check_sha256":
                sha256_file(
                    check_samples_path
                ),

            "window_provenance_sha256":
                sha256_file(
                    provenance_path
                ),

            "selected_window_count":
                total_windows,

            "sample_count":
                (
                    development_train_samples
                    + development_check_samples
                ),

            "real_physical_health_truth":
                False,

            "model_fit_executed":
                False,

            "complete":
                True,
        }

        (
            staging
            / "SUCCESS.json"
        ).write_text(
            json.dumps(
                success,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        os.replace(
            staging,
            output_dir,
        )

    except Exception:
        if staging.exists():
            shutil.rmtree(
                staging
            )

        raise

    print(
        "development_train_samples=3400"
    )

    print(
        "development_check_samples=1000"
    )

    print(
        "total_selected_windows=2200"
    )

    print(
        "total_selected_deserialized_scans=6600"
    )

    print(
        "total_samples=4400"
    )

    print(
        "class_0_clean_samples=2200"
    )

    print(
        "class_1_EVENT_GAP_samples=2200"
    )

    print(
        "model_fit_executed=false"
    )

    print(
        "event_gap_registration_dataset_generation=PASS"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
