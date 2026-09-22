#!/usr/bin/env python3

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import argparse
import json
import shutil
import tempfile

from trust_robot.diagnostic_artifacts import (
    build_lidar_diagnostic_artifact_record,
    canonical_json,
    content_sha256,
    validate_lidar_diagnostic_artifact_record,
)


def file_sha256(
    path: Path,
) -> str:
    digest = sha256()

    with path.open("rb") as handle:
        for block in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(block)

    return digest.hexdigest()


def canonical_content_sha256(
    payload,
) -> str:
    value = dict(payload)
    value.pop("content_sha256", None)

    return sha256(
        canonical_json(value).encode("utf-8")
    ).hexdigest()


def write_json(
    path: Path,
    payload,
) -> None:
    path.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        ) + "\n",
        encoding="utf-8",
    )


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--source-run-dir",
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


def main() -> int:
    args = parse_args()

    source_run_dir = Path(
        args.source_run_dir
    )

    config_path = Path(
        args.config
    )

    output_dir = Path(
        args.output_dir
    )

    if output_dir.exists():
        raise RuntimeError(
            "output directory already exists"
        )

    config = json.loads(
        config_path.read_text(
            encoding="utf-8"
        )
    )

    if (
        canonical_content_sha256(config)
        != config["content_sha256"]
    ):
        raise RuntimeError(
            "configuration content digest mismatch"
        )

    source = config["source"]
    source_core = config[
        "source_core_artifact_sha256"
    ]

    for name, expected in source_core.items():
        actual = file_sha256(
            source_run_dir
            / name
        )

        if actual != expected:
            raise RuntimeError(
                f"source core artifact hash mismatch: {name}"
            )

    trajectory_dir = (
        source_run_dir
        / "trajectories"
    )

    expected_counts = source[
        "per_trajectory_diagnostic_counts"
    ]

    expected_names = sorted(
        expected_counts
    )

    source_files = sorted(
        trajectory_dir.glob(
            "*.jsonl"
        )
    )

    actual_names = [
        path.stem
        for path
        in source_files
    ]

    if actual_names != expected_names:
        raise RuntimeError(
            "source trajectory file set differs from frozen contract"
        )

    parent = output_dir.parent

    parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = Path(
        tempfile.mkdtemp(
            prefix=
                output_dir.name
                + ".tmp.",
            dir=parent,
        )
    )

    try:
        feature_dir = (
            temporary
            / "features"
        )

        feature_dir.mkdir()

        aggregate = sha256()
        total_record_count = 0
        trajectory_summaries = []

        for source_path in source_files:
            trajectory = source_path.stem

            destination = (
                feature_dir
                / f"{trajectory}.jsonl"
            )

            count = 0
            first_type = None
            last_type = None
            previous_current_stamp = None

            output_digest = sha256()

            with (
                source_path.open(
                    "rb"
                ) as source_handle,
                destination.open(
                    "wb"
                ) as output_handle,
            ):
                for line_number, raw_line in enumerate(
                    source_handle,
                    start=1,
                ):
                    if not raw_line.strip():
                        raise RuntimeError(
                            (
                                f"blank source line: "
                                f"{source_path}:{line_number}"
                            )
                        )

                    record = json.loads(
                        raw_line
                    )

                    record_type = record.get(
                        "record_type"
                    )

                    if first_type is None:
                        first_type = record_type

                    last_type = record_type

                    if record_type != "relative_pose":
                        continue

                    if record.get(
                        "trajectory"
                    ) != trajectory:
                        raise RuntimeError(
                            (
                                "trajectory field does not match source "
                                f"filename: {source_path}:{line_number}"
                            )
                        )

                    expected_scan_index = (
                        count
                        + 1
                    )

                    if record.get(
                        "scan_index"
                    ) != expected_scan_index:
                        raise RuntimeError(
                            (
                                "non-contiguous scan_index in "
                                f"{source_path}:{line_number}"
                            )
                        )

                    if (
                        previous_current_stamp
                        is not None
                        and record[
                            "previous_header_stamp_ns"
                        ]
                        != previous_current_stamp
                    ):
                        raise RuntimeError(
                            (
                                "consecutive pair timestamp chain broke in "
                                f"{source_path}:{line_number}"
                            )
                        )

                    raw_line_sha = sha256(
                        raw_line
                    ).hexdigest()

                    artifact = (
                        build_lidar_diagnostic_artifact_record(
                            record,
                            source_line_number=
                                line_number,
                            source_raw_line_sha256=
                                raw_line_sha,
                        )
                    )

                    validate_lidar_diagnostic_artifact_record(
                        artifact
                    )

                    encoded = (
                        canonical_json(
                            artifact
                        )
                        + "\n"
                    ).encode(
                        "utf-8"
                    )

                    output_handle.write(
                        encoded
                    )

                    output_digest.update(
                        encoded
                    )

                    aggregate.update(
                        (
                            trajectory
                            + "\0"
                            + str(
                                line_number
                            )
                            + "\0"
                            + artifact[
                                "feature_record_fingerprint_sha256"
                            ]
                            + "\n"
                        ).encode(
                            "utf-8"
                        )
                    )

                    previous_current_stamp = record[
                        "current_header_stamp_ns"
                    ]

                    count += 1
                    total_record_count += 1

            if first_type != "trajectory_header":
                raise RuntimeError(
                    f"{trajectory}: first record is not trajectory_header"
                )

            if last_type != "trajectory_complete":
                raise RuntimeError(
                    f"{trajectory}: last record is not trajectory_complete"
                )

            expected_count = expected_counts[
                trajectory
            ]

            if count != expected_count:
                raise RuntimeError(
                    (
                        f"{trajectory}: diagnostic count {count} "
                        f"!= expected {expected_count}"
                    )
                )

            trajectory_summaries.append(
                {
                    "trajectory":
                        trajectory,

                    "diagnostic_record_count":
                        count,

                    "source_jsonl_sha256":
                        file_sha256(
                            source_path
                        ),

                    "feature_jsonl_sha256":
                        output_digest.hexdigest(),
                }
            )

            print(
                (
                    f"extracted_trajectory={trajectory} "
                    f"diagnostic_records={count} "
                    f"feature_jsonl_sha256={output_digest.hexdigest()}"
                )
            )

        if total_record_count != source[
            "diagnostic_record_count"
        ]:
            raise RuntimeError(
                "total diagnostic record count mismatch"
            )

        aggregate_sha = aggregate.hexdigest()

        expected_aggregate = config[
            "preflight_binding"
        ][
            "expected_feature_extraction_aggregate_sha256"
        ]

        if aggregate_sha != expected_aggregate:
            raise RuntimeError(
                (
                    "real TRAIN extraction aggregate differs from "
                    "read-only preflight"
                )
            )

        run_manifest = {
            "schema":
                "TRUST_ROBOT_PHASE4_LIDAR_TRAIN_DIAGNOSTIC_RUN_MANIFEST_V1",

            "schema_version":
                1,

            "status":
                "completed",

            "source_run_id":
                source[
                    "phase2_run_id"
                ],

            "dataset_id":
                source[
                    "dataset_id"
                ],

            "split":
                source[
                    "split"
                ],

            "extractor_id":
                config[
                    "extractor_binding"
                ][
                    "extractor_id"
                ],

            "feature_order":
                config[
                    "extractor_binding"
                ][
                    "feature_order"
                ],

            "feature_units":
                config[
                    "extractor_binding"
                ][
                    "feature_units"
                ],

            "configuration": {
                "file_sha256":
                    file_sha256(
                        config_path
                    ),

                "content_sha256":
                    config[
                        "content_sha256"
                    ],
            },

            "record_count":
                total_record_count,

            "trajectory_count":
                len(
                    trajectory_summaries
                ),

            "feature_extraction_aggregate_sha256":
                aggregate_sha,

            "scientific_scope": {
                "source_phase2_artifacts_reused":
                    True,

                "ros_bags_opened":
                    False,

                "new_pointcloud_decoding_performed":
                    False,

                "estimator_rerun":
                    False,

                "corruption_executed":
                    False,

                "descriptive_statistics_computed":
                    False,

                "normalization_applied":
                    False,

                "temporal_window_aggregation_applied":
                    False,

                "threshold_applied":
                    False,

                "health_label_emitted":
                    False,

                "fault_label_emitted":
                    False,

                "reliability_score_emitted":
                    False,

                "accuracy_score_emitted":
                    False,

                "reference_data_used":
                    False,

                "confirmation_test_data_used":
                    False,

                "ate_computed":
                    False,

                "rpe_computed":
                    False,

                "estimator_scoring_performed":
                    False,
            },
        }

        run_manifest[
            "content_sha256"
        ] = content_sha256(
            run_manifest
        )

        summary = {
            "schema":
                "TRUST_ROBOT_PHASE4_LIDAR_TRAIN_DIAGNOSTIC_SUMMARY_V1",

            "schema_version":
                1,

            "status":
                "completed",

            "trajectory_count":
                len(
                    trajectory_summaries
                ),

            "diagnostic_record_count":
                total_record_count,

            "feature_extraction_aggregate_sha256":
                aggregate_sha,

            "trajectories":
                trajectory_summaries,

            "interpretation": {
                "aggregate_is_provenance_identity_only":
                    True,

                "aggregate_is_performance_metric":
                    False,

                "aggregate_is_health_score":
                    False,

                "aggregate_is_fault_score":
                    False,

                "feature_statistics_computed":
                    False,

                "threshold_selected":
                    False,
            },
        }

        summary[
            "content_sha256"
        ] = content_sha256(
            summary
        )

        write_json(
            temporary
            / "run_manifest.json",
            run_manifest,
        )

        write_json(
            temporary
            / "summary.json",
            summary,
        )

        (
            temporary
            / "SUCCESS"
        ).write_text(
            (
                "TRUST_ROBOT_PHASE4_LIDAR_TRAIN_DIAGNOSTIC_ARTIFACTS_V1=PASS\n"
            ),
            encoding="utf-8",
        )

        temporary.replace(
            output_dir
        )

    except Exception:
        shutil.rmtree(
            temporary,
            ignore_errors=True,
        )

        raise

    print(
        "trajectory_count=",
        len(
            trajectory_summaries
        ),
    )

    print(
        "diagnostic_record_count=",
        total_record_count,
    )

    print(
        "feature_extraction_aggregate_sha256=",
        aggregate_sha,
    )

    print(
        "estimator_rerun=false"
    )

    print(
        "ros_bags_opened=false"
    )

    print(
        "descriptive_statistics_computed=false"
    )

    print(
        "threshold_applied=false"
    )

    print(
        "health_label_emitted=false"
    )

    print(
        "fault_label_emitted=false"
    )

    print(
        "reference_data_used=false"
    )

    print(
        "confirmation_test_data_used=false"
    )

    print(
        "ate_computed=false"
    )

    print(
        "rpe_computed=false"
    )

    print(
        "TRUST_ROBOT_PHASE4_LIDAR_TRAIN_DIAGNOSTIC_ARTIFACTS_V1=PASS"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
