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

from trust_robot.lidar_corruption_adapter import (
    adapt_m2dgr_velodyne_messages,
)

from trust_robot.lidar_frontend import (
    register_current_scan_to_previous,
)

from trust_robot.lidar_noise_sensitive_diagnostics import (
    extract_lidar_noise_sensitive_diagnostics,
)

from trust_robot.lidar_point_level_corruption import (
    apply_lidar_point_corruption,
)

from trust_robot.ml_lidar_extended_13_feature_registration_dataset import (
    ALL_TRAIN,
    DEVELOPMENT_CHECK,
    DEVELOPMENT_TRAIN,
    EXPECTED_DIAGNOSTIC_COUNTS,
    FAMILIES,
    build_corruption_specs,
    build_extended_sample,
    content_sha256,
    evenly_spaced_two_scan_starts,
    legacy_features_from_registration,
    partition_for_trajectory,
    validate_config,
    validate_parent_sample,
)


TOPIC = "/velodyne_points"


def file_sha(
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


def load_parent_samples(
    train_path: Path,
    check_path: Path,
):
    records = {}

    for path in (
        train_path,
        check_path,
    ):
        with path.open(
            "r",
            encoding="utf-8",
        ) as handle:
            for raw_line in handle:
                if not raw_line.strip():
                    raise RuntimeError(
                        "blank parent dataset line"
                    )

                item = json.loads(
                    raw_line
                )

                key = (
                    item[
                        "trajectory"
                    ],
                    item[
                        "window_start_scan_index"
                    ],
                    item[
                        "degradation_family"
                    ],
                )

                if key in records:
                    raise RuntimeError(
                        "duplicate parent semantic sample"
                    )

                records[
                    key
                ] = item

    if len(
        records
    ) != 4400:
        raise RuntimeError(
            "parent sample count mismatch"
        )

    return records


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
            "window_count"
        ) != 50:
            return None

        if receipt.get(
            "sample_count"
        ) != 200:
            return None

        if receipt.get(
            "registration_count"
        ) != 200:
            return None

        if receipt.get(
            "selected_deserialized_scan_count"
        ) != 100:
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
    parent_records,
    trajectory: str,
    work_dir: Path,
):
    partition = partition_for_trajectory(
        trajectory
    )

    bag_info = config[
        "bags"
    ][
        trajectory
    ]

    bag_path = (
        dataset_root
        / bag_info[
            "relative_path"
        ]
    )

    if not bag_path.is_file():
        raise RuntimeError(
            "bag missing: "
            + trajectory
        )

    if bag_path.stat().st_size != bag_info[
        "size_bytes"
    ]:
        raise RuntimeError(
            "bag size changed: "
            + trajectory
        )

    starts = (
        evenly_spaced_two_scan_starts(
            EXPECTED_DIAGNOSTIC_COUNTS[
                trajectory
            ]
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
            + " windows=50 samples=200 registrations=200",
            flush=True,
        )

        return completed

    sample_tmp = sample_path.with_suffix(
        ".jsonl.tmp"
    )

    provenance_tmp = (
        provenance_path.with_suffix(
            ".jsonl.tmp"
        )
    )

    receipt_tmp = (
        receipt_path.with_suffix(
            ".json.tmp"
        )
    )

    for path in (
        sample_tmp,
        provenance_tmp,
        receipt_tmp,
    ):
        if path.exists():
            path.unlink()

    start_pointer = 0
    selected_messages = []

    total_velodyne_messages = 0
    selected_deserialized_scans = 0
    completed_windows = 0
    registration_count = 0

    family_counts = Counter()

    trajectory_started = (
        time.time()
    )

    specs = build_corruption_specs()

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
                active_start + 1
            ):
                raise RuntimeError(
                    "selected window skipped"
                )

            if (
                active_start
                <= scan_index
                <= active_start + 1
            ):
                selected_messages.append(
                    reader.deserialize(
                        rawdata,
                        connection.msgtype,
                    )
                )

                selected_deserialized_scans += 1

            if scan_index == (
                active_start + 1
            ):
                if len(
                    selected_messages
                ) != 2:
                    raise RuntimeError(
                        "selected window message count != 2"
                    )

                adapted = (
                    adapt_m2dgr_velodyne_messages(
                        tuple(
                            selected_messages
                        )
                    )
                )

                clean_stream = (
                    adapted.stream
                )

                window_key = (
                    "M2DGR:TRAIN:"
                    + trajectory
                    + ":two_scan_start:"
                    + str(
                        active_start
                    )
                )

                variants = [
                    (
                        "CLEAN",
                        clean_stream,
                        None,
                    )
                ]

                for spec in specs:
                    result = (
                        apply_lidar_point_corruption(
                            clean_stream,
                            spec,
                            window_key=
                                window_key,
                        )
                    )

                    variants.append(
                        (
                            spec.family.value,
                            result.corrupt,
                            dict(
                                result.truth
                            ),
                        )
                    )

                if tuple(
                    item[
                        0
                    ]
                    for item
                    in variants
                ) != FAMILIES:
                    raise RuntimeError(
                        "family order changed"
                    )

                window_provenance = {
                    "trajectory":
                        trajectory,

                    "development_partition":
                        partition,

                    "window_start_scan_index":
                        active_start,

                    "window_scan_indices": [
                        active_start,
                        active_start + 1,
                    ],

                    "window_key":
                        window_key,

                    "families":
                        [],
                }

                for (
                    family,
                    stream,
                    truth,
                ) in variants:
                    parent_key = (
                        trajectory,
                        active_start,
                        family,
                    )

                    parent = parent_records.get(
                        parent_key
                    )

                    if parent is None:
                        raise RuntimeError(
                            "parent semantic sample missing: "
                            + repr(
                                parent_key
                            )
                        )

                    validate_parent_sample(
                        parent,
                        trajectory=
                            trajectory,
                        window_start=
                            active_start,
                        family=
                            family,
                    )

                    registration = (
                        register_current_scan_to_previous(
                            stream.payloads[
                                0
                            ],
                            stream.payloads[
                                1
                            ],
                        )
                    )

                    registration_count += 1

                    legacy = (
                        legacy_features_from_registration(
                            registration
                        )
                    )

                    extended = (
                        extract_lidar_noise_sensitive_diagnostics(
                            stream.payloads[
                                0
                            ],
                            stream.payloads[
                                1
                            ],
                            registration,
                        )
                    )

                    sample = (
                        build_extended_sample(
                            parent_sample=
                                parent,

                            observed_legacy_features=
                                legacy,

                            extended_diagnostics=
                                extended,
                        )
                    )

                    sample_handle.write(
                        canonical_line(
                            sample
                        )
                    )

                    family_counts[
                        family
                    ] += 1

                    window_provenance[
                        "families"
                    ].append(
                        {
                            "family":
                                family,

                            "parent_sample_id":
                                parent[
                                    "sample_id"
                                ],

                            "output_sample_id":
                                sample[
                                    "sample_id"
                                ],

                            "legacy_feature_identity":
                                True,

                            "observational_RMSE_identity":
                                True,

                            "extended_diagnostics":
                                extended.to_dict(),

                            "synthetic_corruption_truth":
                                truth,
                        }
                    )

                provenance_handle.write(
                    canonical_line(
                        window_provenance
                    )
                )

                completed_windows += 1
                selected_messages = []
                start_pointer += 1

                if (
                    completed_windows % 10
                    == 0
                    or completed_windows
                    == 50
                ):
                    print(
                        "TRAJECTORY_PROGRESS="
                        + trajectory
                        + " windows="
                        + str(
                            completed_windows
                        )
                        + "/50 registrations="
                        + str(
                            registration_count
                        )
                        + "/200 elapsed_seconds="
                        + f"{time.time() - trajectory_started:.1f}",
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
            + " Velodyne count mismatch"
        )

    if completed_windows != 50:
        raise RuntimeError(
            trajectory
            + " window count mismatch"
        )

    if selected_deserialized_scans != 100:
        raise RuntimeError(
            trajectory
            + " selected scan count mismatch"
        )

    if registration_count != 200:
        raise RuntimeError(
            trajectory
            + " registration count mismatch"
        )

    expected_family_counts = {
        family:
            50
        for family
        in FAMILIES
    }

    if dict(
        family_counts
    ) != expected_family_counts:
        raise RuntimeError(
            trajectory
            + " family count mismatch"
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
            "TRUST_ROBOT_M2DGR_LIDAR_EXTENDED_13_FEATURE_TRAJECTORY_RECEIPT_V1",

        "trajectory":
            trajectory,

        "development_partition":
            partition,

        "window_count":
            50,

        "selected_deserialized_scan_count":
            100,

        "registration_count":
            200,

        "sample_count":
            200,

        "family_counts":
            expected_family_counts,

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
        + " windows=50"
        + " samples=200"
        + " registrations=200"
        + " elapsed_seconds="
        + f"{receipt['elapsed_seconds']:.1f}",
        flush=True,
    )

    return receipt


def concatenate_files(
    paths,
    output,
):
    tmp = output.with_suffix(
        output.suffix
        + ".tmp"
    )

    with tmp.open(
        "wb"
    ) as destination:
        for path in paths:
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
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--config",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--parent-train",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--parent-check",
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

    parent_train = (
        args.parent_train.resolve()
    )

    parent_check = (
        args.parent_check.resolve()
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

    parent_config = config[
        "parent_dataset"
    ]

    if file_sha(
        parent_train
    ) != parent_config[
        "development_train_sha256"
    ]:
        raise RuntimeError(
            "parent development_train hash mismatch"
        )

    if file_sha(
        parent_check
    ) != parent_config[
        "development_check_sha256"
    ]:
        raise RuntimeError(
            "parent development_check hash mismatch"
        )

    parent_records = (
        load_parent_samples(
            parent_train,
            parent_check,
        )
    )

    if output_dir.exists():
        raise RuntimeError(
            "final output already exists"
        )

    work_dir = (
        output_dir.with_name(
            output_dir.name
            + ".partial"
        )
    )

    work_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    run_started = time.time()

    print(
        "LONG_REPLAY_START"
        " trajectories=22"
        " windows=1100"
        " registrations=4400"
        " samples=4400"
        " feature_count=13",
        flush=True,
    )

    receipts = []

    for index, trajectory in enumerate(
        ALL_TRAIN,
        start=1,
    ):
        print(
            "TRAJECTORY_BEGIN="
            + trajectory
            + " index="
            + str(index)
            + "/22 partition="
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

            parent_records=
                parent_records,

            trajectory=
                trajectory,

            work_dir=
                work_dir,
        )

        receipts.append(
            receipt
        )

        completed_registrations = sum(
            item[
                "registration_count"
            ]
            for item
            in receipts
        )

        print(
            "GLOBAL_PROGRESS="
            + str(
                len(
                    receipts
                )
            )
            + "/22 trajectories"
            + " registrations="
            + str(
                completed_registrations
            )
            + "/4400"
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
            "TRUST_ROBOT_M2DGR_LIDAR_EXTENDED_13_FEATURE_REGISTRATION_DATASET_RUN_V1",

        "schema_version":
            1,

        "config_file_sha256":
            file_sha(
                config_path
            ),

        "config_content_sha256":
            config[
                "content_sha256"
            ],

        "parent_dataset": {
            "development_train_sha256":
                file_sha(
                    parent_train
                ),

            "development_check_sha256":
                file_sha(
                    parent_check
                ),

            "population_changed":
                False,
        },

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

            "registration_count":
                4400,

            "sample_count":
                4400,

            "legacy_feature_count":
                5,

            "new_residual_feature_count":
                8,

            "combined_feature_count":
                13,

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

            "same_parent_benchmark_population":
                True,

            "synthetic_intervention_truth":
                True,

            "real_physical_health_truth":
                False,

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
            "TRUST_ROBOT_M2DGR_LIDAR_EXTENDED_13_FEATURE_REGISTRATION_DATASET_SUCCESS_V1",

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

        "registration_count":
            4400,

        "sample_count":
            4400,

        "combined_feature_count":
            13,

        "parent_sample_population_changed":
            False,

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
        " registrations=4400"
        " samples=4400"
        " feature_count=13"
        " elapsed_seconds="
        + f"{time.time() - run_started:.1f}",
        flush=True,
    )

    print(
        "TRUST_ROBOT_M2DGR_LIDAR_EXTENDED_13_FEATURE_REGISTRATION_DATASET_V1=PASS",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
