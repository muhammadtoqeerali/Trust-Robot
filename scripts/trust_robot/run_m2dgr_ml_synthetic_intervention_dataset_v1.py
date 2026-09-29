#!/usr/bin/env python3
"""Materialize the TRAIN-only synthetic-intervention development dataset."""

from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
from pathlib import Path
from typing import Any
import json
import os
import shutil

from trust_robot.ml_synthetic_intervention_dataset import (
    DEVELOPMENT_CHECK,
    DEVELOPMENT_TRAIN,
    build_contract,
    build_selection_binding,
    canonical_json_bytes,
    content_sha256,
    iter_trajectory_samples,
    selection_binding_sha256,
    validate_config,
)


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

    dataset_root = args.dataset_root.resolve()
    config_path = args.config.resolve()
    output_dir = args.output_dir.resolve()

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

    try:
        output_records: dict[
            str,
            dict[str, Any],
        ] = {}

        total_samples = 0
        total_class_counts = Counter()

        partition_specs = (
            (
                "development_train",
                DEVELOPMENT_TRAIN,
                "development_train.jsonl",
            ),
            (
                "development_check",
                DEVELOPMENT_CHECK,
                "development_check.jsonl",
            ),
        )

        for (
            partition,
            trajectories,
            output_name,
        ) in partition_specs:
            destination = (
                staging
                / output_name
            )

            digest = sha256()
            sample_count = 0
            class_counts = Counter()
            trajectory_counts = Counter()

            with destination.open(
                "wb"
            ) as output_handle:
                for trajectory in trajectories:
                    source = config[
                        "source_files"
                    ][
                        trajectory
                    ]

                    source_path = (
                        dataset_root
                        / source[
                            "relative_path"
                        ]
                    )

                    if not source_path.is_file():
                        raise RuntimeError(
                            "source artifact missing: "
                            + str(
                                source_path
                            )
                        )

                    actual_source_sha = sha256_file(
                        source_path
                    )

                    if actual_source_sha != source[
                        "sha256"
                    ]:
                        raise RuntimeError(
                            "source artifact SHA mismatch: "
                            + trajectory
                        )

                    for sample in iter_trajectory_samples(
                        source_path,
                        trajectory=
                            trajectory,
                        development_partition=
                            partition,
                    ):
                        line = (
                            json.dumps(
                                sample,
                                sort_keys=True,
                                separators=(",", ":"),
                                ensure_ascii=False,
                                allow_nan=False,
                            )
                            + "\n"
                        ).encode(
                            "utf-8"
                        )

                        output_handle.write(
                            line
                        )

                        digest.update(
                            line
                        )

                        sample_count += 1

                        class_counts[
                            str(
                                sample[
                                    "label"
                                ]
                            )
                        ] += 1

                        trajectory_counts[
                            trajectory
                        ] += 1

            expected = config[
                (
                    "expected_development_train_samples"
                    if partition == "development_train"
                    else "expected_development_check_samples"
                )
            ]

            if sample_count != expected:
                raise RuntimeError(
                    partition
                    + " sample count mismatch"
                )

            if class_counts[
                "0"
            ] != class_counts[
                "1"
            ]:
                raise RuntimeError(
                    partition
                    + " class balance changed"
                )

            output_records[
                partition
            ] = {
                "file":
                    output_name,

                "sha256":
                    digest.hexdigest(),

                "sample_count":
                    sample_count,

                "class_counts":
                    dict(
                        sorted(
                            class_counts.items()
                        )
                    ),

                "trajectory_sample_counts":
                    dict(
                        sorted(
                            trajectory_counts.items()
                        )
                    ),
            }

            total_samples += sample_count
            total_class_counts.update(
                class_counts
            )

        if total_samples != config[
            "expected_total_samples"
        ]:
            raise RuntimeError(
                "total sample count mismatch"
            )

        if total_class_counts[
            "0"
        ] != total_class_counts[
            "1"
        ]:
            raise RuntimeError(
                "overall classes are not balanced"
            )

        source_files = {}

        for trajectory in (
            DEVELOPMENT_TRAIN
            + DEVELOPMENT_CHECK
        ):
            item = dict(
                config[
                    "source_files"
                ][
                    trajectory
                ]
            )

            item[
                "development_partition"
            ] = (
                "development_train"
                if trajectory
                in DEVELOPMENT_TRAIN
                else "development_check"
            )

            source_files[
                trajectory
            ] = item

        manifest = {
            "schema":
                "TRUST_ROBOT_M2DGR_ML_SYNTHETIC_INTERVENTION_DATASET_RUN_V1",

            "schema_version":
                1,

            "dataset_contract":
                build_contract(),

            "dataset_config_file":
                str(
                    args.config
                ),

            "dataset_config_sha256":
                sha256_file(
                    config_path
                ),

            "dataset_config_content_sha256":
                config[
                    "content_sha256"
                ],

            "selection_binding":
                build_selection_binding(),

            "selection_binding_sha256":
                selection_binding_sha256(),

            "source_files":
                source_files,

            "outputs":
                output_records,

            "total_sample_count":
                total_samples,

            "total_class_counts":
                dict(
                    sorted(
                        total_class_counts.items()
                    )
                ),

            "scientific_boundary": {
                "synthetic_intervention_labels_only":
                    True,

                "real_physical_health_truth":
                    False,

                "health_model_training_executed":
                    False,

                "model_fit_executed":
                    False,

                "validation_access":
                    False,

                "confirmation_access":
                    False,

                "reference_data_access":
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

        summary = {
            "schema":
                "TRUST_ROBOT_M2DGR_ML_SYNTHETIC_INTERVENTION_DATASET_SUMMARY_V1",

            "development_train_trajectory_count":
                len(
                    DEVELOPMENT_TRAIN
                ),

            "development_check_trajectory_count":
                len(
                    DEVELOPMENT_CHECK
                ),

            "development_train_sample_count":
                output_records[
                    "development_train"
                ][
                    "sample_count"
                ],

            "development_check_sample_count":
                output_records[
                    "development_check"
                ][
                    "sample_count"
                ],

            "total_sample_count":
                total_samples,

            "class_0_count":
                total_class_counts[
                    "0"
                ],

            "class_1_count":
                total_class_counts[
                    "1"
                ],

            "intervention_family":
                "EVENT_REPEAT",

            "label_semantics":
                "synthetic_intervention_truth_only",

            "real_physical_health_truth":
                False,

            "model_training_executed":
                False,
        }

        summary_path = (
            staging
            / "summary.json"
        )

        summary_path.write_text(
            json.dumps(
                summary,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        success = {
            "schema":
                "TRUST_ROBOT_M2DGR_ML_SYNTHETIC_INTERVENTION_DATASET_SUCCESS_V1",

            "run_manifest_sha256":
                sha256_file(
                    manifest_path
                ),

            "summary_sha256":
                sha256_file(
                    summary_path
                ),

            "development_train_sha256":
                output_records[
                    "development_train"
                ][
                    "sha256"
                ],

            "development_check_sha256":
                output_records[
                    "development_check"
                ][
                    "sha256"
                ],

            "total_sample_count":
                total_samples,

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
        "dataset_output_dir="
        + str(
            output_dir
        )
    )

    print(
        "development_train_samples="
        + str(
            output_records[
                "development_train"
            ][
                "sample_count"
            ]
        )
    )

    print(
        "development_check_samples="
        + str(
            output_records[
                "development_check"
            ][
                "sample_count"
            ]
        )
    )

    print(
        "total_samples="
        + str(
            total_samples
        )
    )

    print(
        "class_0_samples="
        + str(
            total_class_counts[
                "0"
            ]
        )
    )

    print(
        "class_1_samples="
        + str(
            total_class_counts[
                "1"
            ]
        )
    )

    print(
        "model_training_executed=false"
    )

    print(
        "dataset_generation=PASS"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
