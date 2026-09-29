#!/usr/bin/env python3

from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
from pathlib import Path
import json
import os
import shutil
import time

from rosbags.highlevel import AnyReader

from trust_robot.diagnostic_artifacts import (
    validate_lidar_diagnostic_artifact_record,
)
from trust_robot.lidar_corruption_adapter import (
    adapt_m2dgr_velodyne_messages,
)
from trust_robot.ml_lidar_point_level_registration_dataset import (
    ALL_TRAIN,
    DEVELOPMENT_CHECK,
    DEVELOPMENT_TRAIN,
    EXPECTED_DIAGNOSTIC_COUNTS,
    build_window_samples,
    content_sha256,
    evenly_spaced_two_scan_starts,
    partition_for_trajectory,
    validate_config,
)


TOPIC = "/velodyne_points"


def file_sha(
    path: Path,
) -> str:
    digest = sha256()

    with path.open("rb") as handle:
        for block in iter(
            lambda: handle.read(
                1024 * 1024
            ),
            b"",
        ):
            digest.update(block)

    return digest.hexdigest()


def canonical_line(
    payload,
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
    ).encode("utf-8")


def load_selected_phase4_records(
    path: Path,
    *,
    trajectory: str,
    starts,
):
    required_scan_indices = {
        start + 1
        for start in starts
    }

    selected = {}

    with path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        for raw_line in handle:
            if not raw_line.strip():
                raise RuntimeError(
                    "blank Phase-4 line"
                )

            record = json.loads(
                raw_line
            )

            validate_lidar_diagnostic_artifact_record(
                record
            )

            if record.get(
                "trajectory"
            ) != trajectory:
                raise RuntimeError(
                    "Phase-4 trajectory mismatch"
                )

            scan_index = record.get(
                "scan_index"
            )

            if scan_index in required_scan_indices:
                selected[
                    scan_index
                ] = record

    if set(
        selected
    ) != required_scan_indices:
        missing = sorted(
            required_scan_indices
            - set(
                selected
            )
        )

        raise RuntimeError(
            "missing selected Phase-4 records: "
            + repr(
                missing
            )
        )

    return selected


def valid_completed_receipt(
    *,
    receipt_path: Path,
    sample_path: Path,
    provenance_path: Path,
):
    if not (
        receipt_path.is_file()
        and sample_path.is_file()
        and provenance_path.is_file()
    ):
        return None

    try:
        receipt = json.loads(
            receipt_path.read_text(
                encoding="utf-8"
            )
        )

        if receipt.get(
            "complete"
        ) is not True:
            return None

        if receipt.get(
            "sample_count"
        ) != 200:
            return None

        if receipt.get(
            "window_count"
        ) != 50:
            return None

        if receipt.get(
            "new_corrupted_registration_count"
        ) != 150:
            return None

        if file_sha(
            sample_path
        ) != receipt.get(
            "sample_file_sha256"
        ):
            return None

        if file_sha(
            provenance_path
        ) != receipt.get(
            "provenance_file_sha256"
        ):
            return None

        return receipt

    except Exception:
        return None


def process_trajectory(
    *,
    dataset_root: Path,
    config,
    trajectory: str,
    work_dir: Path,
):
    partition = partition_for_trajectory(
        trajectory
    )

    source = config[
        "source_files"
    ][
        trajectory
    ]

    phase4_path = (
        dataset_root
        / source[
            "phase4_relative_path"
        ]
    )

    bag_path = (
        dataset_root
        / source[
            "bag_relative_path"
        ]
    )

    if file_sha(
        phase4_path
    ) != source[
        "phase4_sha256"
    ]:
        raise RuntimeError(
            trajectory
            + " Phase-4 SHA mismatch"
        )

    if bag_path.stat().st_size != source[
        "bag_size_bytes"
    ]:
        raise RuntimeError(
            trajectory
            + " bag size changed"
        )

    starts = evenly_spaced_two_scan_starts(
        EXPECTED_DIAGNOSTIC_COUNTS[
            trajectory
        ]
    )

    phase4_records = (
        load_selected_phase4_records(
            phase4_path,
            trajectory=
                trajectory,
            starts=
                starts,
        )
    )

    samples_dir = (
        work_dir
        / "trajectory_samples"
    )

    provenance_dir = (
        work_dir
        / "trajectory_provenance"
    )

    receipts_dir = (
        work_dir
        / "trajectory_receipts"
    )

    for directory in (
        samples_dir,
        provenance_dir,
        receipts_dir,
    ):
        directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    sample_path = (
        samples_dir
        / (
            trajectory
            + ".jsonl"
        )
    )

    provenance_path = (
        provenance_dir
        / (
            trajectory
            + ".jsonl"
        )
    )

    receipt_path = (
        receipts_dir
        / (
            trajectory
            + ".json"
        )
    )

    completed = valid_completed_receipt(
        receipt_path=
            receipt_path,

        sample_path=
            sample_path,

        provenance_path=
            provenance_path,
    )

    if completed is not None:
        print(
            "TRAJECTORY_RESUME_SKIP="
            + trajectory
            + " sample_count=200 windows=50",
            flush=True,
        )

        return completed

    sample_tmp = sample_path.with_suffix(
        ".jsonl.tmp"
    )

    provenance_tmp = provenance_path.with_suffix(
        ".jsonl.tmp"
    )

    receipt_tmp = receipt_path.with_suffix(
        ".json.tmp"
    )

    for path in (
        sample_tmp,
        provenance_tmp,
        receipt_tmp,
    ):
        if path.exists():
            path.unlink()

    start_pointer = 0
    current_messages = []

    total_velodyne_messages = 0
    selected_deserialized_scans = 0
    completed_windows = 0
    new_corrupted_registrations = 0

    family_counts = Counter()

    trajectory_started = time.time()

    with sample_tmp.open(
        "wb"
    ) as sample_handle, \
    provenance_tmp.open(
        "wb"
    ) as provenance_handle, \
    AnyReader(
        [
            bag_path
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
                + 1
            ):
                raise RuntimeError(
                    trajectory
                    + " selected two-scan window skipped"
                )

            if (
                active_start
                <= scan_index
                <= active_start + 1
            ):
                message = reader.deserialize(
                    rawdata,
                    connection.msgtype,
                )

                current_messages.append(
                    message
                )

                selected_deserialized_scans += 1

            if scan_index == (
                active_start
                + 1
            ):
                if len(
                    current_messages
                ) != 2:
                    raise RuntimeError(
                        "selected window message count !=2"
                    )

                adapted = (
                    adapt_m2dgr_velodyne_messages(
                        tuple(
                            current_messages
                        )
                    )
                )

                phase4_record = (
                    phase4_records[
                        active_start
                        + 1
                    ]
                )

                samples, provenance = (
                    build_window_samples(
                        clean_stream=
                            adapted.stream,

                        clean_feature_values=
                            phase4_record[
                                "feature_values"
                            ],

                        clean_phase4_record_sha256=
                            phase4_record[
                                "content_sha256"
                            ],

                        trajectory=
                            trajectory,

                        window_start_scan_index=
                            active_start,
                    )
                )

                for sample in samples:
                    sample_handle.write(
                        canonical_line(
                            sample
                        )
                    )

                    family_counts[
                        sample[
                            "degradation_family"
                        ]
                    ] += 1

                provenance_handle.write(
                    canonical_line(
                        provenance
                    )
                )

                completed_windows += 1
                new_corrupted_registrations += 3

                current_messages = []
                start_pointer += 1

                if (
                    completed_windows % 10
                    == 0
                    or completed_windows
                    == 50
                ):
                    elapsed = (
                        time.time()
                        - trajectory_started
                    )

                    print(
                        "TRAJECTORY_PROGRESS="
                        + trajectory
                        + " windows="
                        + str(
                            completed_windows
                        )
                        + "/50"
                        + " registrations="
                        + str(
                            new_corrupted_registrations
                        )
                        + "/150"
                        + " elapsed_seconds="
                        + f"{elapsed:.1f}",
                        flush=True,
                    )

    expected_scan_count = (
        EXPECTED_DIAGNOSTIC_COUNTS[
            trajectory
        ]
        + 1
    )

    if total_velodyne_messages != expected_scan_count:
        raise RuntimeError(
            trajectory
            + " Velodyne scan count mismatch "
            + str(
                total_velodyne_messages
            )
            + " != "
            + str(
                expected_scan_count
            )
        )

    if completed_windows != 50:
        raise RuntimeError(
            trajectory
            + " completed window count mismatch"
        )

    if selected_deserialized_scans != 100:
        raise RuntimeError(
            trajectory
            + " selected scan count mismatch"
        )

    if new_corrupted_registrations != 150:
        raise RuntimeError(
            trajectory
            + " corrupted registration count mismatch"
        )

    expected_family_counts = {
        "CLEAN": 50,
        "POINT_DROPOUT": 50,
        "XYZ_GAUSSIAN_NOISE": 50,
        "AZIMUTH_SECTOR_OCCLUSION": 50,
    }

    if dict(
        family_counts
    ) != expected_family_counts:
        raise RuntimeError(
            trajectory
            + " family sample counts changed: "
            + repr(
                dict(
                    family_counts
                )
            )
        )

    os.replace(
        sample_tmp,
        sample_path,
    )

    os.replace(
        provenance_tmp,
        provenance_path,
    )

    receipt = {
        "schema":
            "TRUST_ROBOT_M2DGR_LIDAR_POINT_LEVEL_TRAJECTORY_RECEIPT_V1",

        "trajectory":
            trajectory,

        "development_partition":
            partition,

        "window_count":
            50,

        "selected_deserialized_scan_count":
            100,

        "sample_count":
            200,

        "family_counts":
            expected_family_counts,

        "new_corrupted_registration_count":
            150,

        "total_velodyne_messages":
            total_velodyne_messages,

        "sample_file_sha256":
            file_sha(
                sample_path
            ),

        "provenance_file_sha256":
            file_sha(
                provenance_path
            ),

        "elapsed_seconds":
            float(
                time.time()
                - trajectory_started
            ),

        "complete":
            True,
    }

    receipt[
        "content_sha256"
    ] = content_sha256(
        receipt
    )

    receipt_tmp.write_text(
        json.dumps(
            receipt,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    os.replace(
        receipt_tmp,
        receipt_path,
    )

    print(
        "TRAJECTORY_COMPLETE="
        + trajectory
        + " windows=50 samples=200"
        + " registrations=150"
        + " elapsed_seconds="
        + f"{receipt['elapsed_seconds']:.1f}",
        flush=True,
    )

    return receipt


def concatenate_files(
    inputs,
    output,
):
    tmp = output.with_suffix(
        output.suffix
        + ".tmp"
    )

    with tmp.open(
        "wb"
    ) as destination:
        for path in inputs:
            with path.open(
                "rb"
            ) as source:
                shutil.copyfileobj(
                    source,
                    destination,
                    length=
                        1024 * 1024,
                )

    os.replace(
        tmp,
        output,
    )


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--dataset-root",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--config",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
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
            "final output already exists"
        )

    work_dir = output_dir.with_name(
        output_dir.name
        + ".partial"
    )

    work_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    print(
        "LONG_REPLAY_START"
        " total_trajectories=22"
        " total_windows=1100"
        " expected_new_corrupted_registrations=3300",
        flush=True,
    )

    run_started = time.time()

    receipts = []

    for number, trajectory in enumerate(
        ALL_TRAIN,
        start=1,
    ):
        print(
            "TRAJECTORY_BEGIN="
            + trajectory
            + " index="
            + str(
                number
            )
            + "/22"
            + " partition="
            + partition_for_trajectory(
                trajectory
            ),
            flush=True,
        )

        receipt = process_trajectory(
            dataset_root=
                dataset_root,

            config=
                config,

            trajectory=
                trajectory,

            work_dir=
                work_dir,
        )

        receipts.append(
            receipt
        )

        completed_trajectories = len(
            receipts
        )

        completed_registrations = sum(
            int(
                item[
                    "new_corrupted_registration_count"
                ]
            )
            for item
            in receipts
        )

        print(
            "GLOBAL_PROGRESS="
            + str(
                completed_trajectories
            )
            + "/22 trajectories"
            + " corrupted_registrations="
            + str(
                completed_registrations
            )
            + "/3300"
            + " total_elapsed_seconds="
            + f"{time.time() - run_started:.1f}",
            flush=True,
        )

    samples_dir = (
        work_dir
        / "trajectory_samples"
    )

    provenance_dir = (
        work_dir
        / "trajectory_provenance"
    )

    train_output = (
        work_dir
        / "development_train.jsonl"
    )

    check_output = (
        work_dir
        / "development_check.jsonl"
    )

    provenance_output = (
        work_dir
        / "window_provenance.jsonl"
    )

    concatenate_files(
        [
            samples_dir
            / (
                trajectory
                + ".jsonl"
            )
            for trajectory
            in DEVELOPMENT_TRAIN
        ],
        train_output,
    )

    concatenate_files(
        [
            samples_dir
            / (
                trajectory
                + ".jsonl"
            )
            for trajectory
            in DEVELOPMENT_CHECK
        ],
        check_output,
    )

    concatenate_files(
        [
            provenance_dir
            / (
                trajectory
                + ".jsonl"
            )
            for trajectory
            in ALL_TRAIN
        ],
        provenance_output,
    )

    manifest = {
        "schema":
            "TRUST_ROBOT_M2DGR_LIDAR_POINT_LEVEL_REGISTRATION_DATASET_RUN_V1",

        "schema_version":
            1,

        "config_file":
            str(
                args.config
            ),

        "config_file_sha256":
            file_sha(
                config_path
            ),

        "config_content_sha256":
            config[
                "content_sha256"
            ],

        "trajectory_receipts":
            receipts,

        "outputs": {
            "development_train": {
                "file":
                    train_output.name,

                "sha256":
                    file_sha(
                        train_output
                    ),

                "sample_count":
                    3400,
            },

            "development_check": {
                "file":
                    check_output.name,

                "sha256":
                    file_sha(
                        check_output
                    ),

                "sample_count":
                    1000,
            },

            "window_provenance": {
                "file":
                    provenance_output.name,

                "sha256":
                    file_sha(
                        provenance_output
                    ),

                "record_count":
                    1100,
            },
        },

        "totals": {
            "trajectory_count":
                22,

            "selected_window_count":
                1100,

            "selected_raw_scan_count":
                2200,

            "new_corrupted_registration_count":
                3300,

            "sample_count":
                4400,

            "CLEAN":
                1100,

            "POINT_DROPOUT":
                1100,

            "XYZ_GAUSSIAN_NOISE":
                1100,

            "AZIMUTH_SECTOR_OCCLUSION":
                1100,
        },

        "runtime": {
            "elapsed_seconds":
                float(
                    time.time()
                    - run_started
                ),

            "resumable":
                True,
        },

        "scientific_boundary": {
            "TRAIN_only":
                True,

            "synthetic_intervention_truth":
                True,

            "real_physical_health_truth":
                False,

            "real_health_label_count":
                0,

            "model_fit_executed":
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
        work_dir
        / "run_manifest.json"
    )

    manifest_path.write_text(
        json.dumps(
            manifest,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    success = {
        "schema":
            "TRUST_ROBOT_M2DGR_LIDAR_POINT_LEVEL_REGISTRATION_DATASET_SUCCESS_V1",

        "run_manifest_sha256":
            file_sha(
                manifest_path
            ),

        "development_train_sha256":
            file_sha(
                train_output
            ),

        "development_check_sha256":
            file_sha(
                check_output
            ),

        "window_provenance_sha256":
            file_sha(
                provenance_output
            ),

        "selected_window_count":
            1100,

        "new_corrupted_registration_count":
            3300,

        "sample_count":
            4400,

        "real_physical_health_truth":
            False,

        "model_fit_executed":
            False,

        "complete":
            True,
    }

    (
        work_dir
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
        work_dir,
        output_dir,
    )

    print(
        "LONG_REPLAY_COMPLETE"
        " windows=1100"
        " registrations=3300"
        " samples=4400"
        " elapsed_seconds="
        + f"{time.time() - run_started:.1f}",
        flush=True,
    )

    print(
        "TRUST_ROBOT_M2DGR_LIDAR_POINT_LEVEL_REGISTRATION_DATASET_V1=PASS",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
