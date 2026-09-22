#!/usr/bin/env python3

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import argparse
import json

from trust_robot.paired_diagnostic_artifacts import (
    build_phase3_paired_diagnostic_artifact,
)


def file_sha256(
    path,
):
    digest = sha256()

    with Path(
        path
    ).open(
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


def canonical_sha256(
    payload,
):
    value = dict(
        payload
    )

    value.pop(
        "content_sha256",
        None,
    )

    return sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def immutable_write(
    path,
    content,
):
    path = Path(
        path
    )

    if path.exists():
        existing = path.read_text(
            encoding="utf-8"
        )

        if existing != content:
            raise RuntimeError(
                f"immutable artifact differs: {path}"
            )

        return

    temporary = path.with_suffix(
        path.suffix
        + ".tmp"
    )

    if temporary.exists():
        raise RuntimeError(
            f"stale temporary artifact exists: {temporary}"
        )

    temporary.write_text(
        content,
        encoding="utf-8",
    )

    temporary.replace(
        path
    )


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--config",
        required=True,
    )

    parser.add_argument(
        "--phase3-receipt",
        required=True,
    )

    parser.add_argument(
        "--output-dir",
        required=True,
    )

    return parser.parse_args()


def main():
    args = parse_args()

    config_path = Path(
        args.config
    )

    receipt_path = Path(
        args.phase3_receipt
    )

    output_dir = Path(
        args.output_dir
    )

    config = json.loads(
        config_path.read_text(
            encoding="utf-8"
        )
    )

    if canonical_sha256(
        config
    ) != config[
        "content_sha256"
    ]:
        raise RuntimeError(
            "paired diagnostic config content digest mismatch"
        )

    expected_source_sha = config[
        "source"
    ][
        "file_sha256"
    ]

    actual_source_sha = file_sha256(
        receipt_path
    )

    if actual_source_sha != expected_source_sha:
        raise RuntimeError(
            "Phase-3 paired receipt file hash mismatch"
        )

    receipt = json.loads(
        receipt_path.read_text(
            encoding="utf-8"
        )
    )

    if (
        receipt[
            "content_sha256"
        ]
        != config[
            "source"
        ][
            "receipt_content_sha256"
        ]
    ):
        raise RuntimeError(
            "Phase-3 paired receipt content identity mismatch"
        )

    first = build_phase3_paired_diagnostic_artifact(
        receipt
    )

    second = build_phase3_paired_diagnostic_artifact(
        receipt
    )

    if first != second:
        raise RuntimeError(
            "paired diagnostic extraction was not deterministic"
        )

    expected = config[
        "expected_registration_topology"
    ]

    if first[
        "clean"
    ][
        "origin_pairs"
    ] != expected[
        "clean_origin_pairs"
    ]:
        raise RuntimeError(
            "clean diagnostic topology mismatch"
        )

    if first[
        "corrupt"
    ][
        "origin_pairs"
    ] != expected[
        "corrupt_origin_pairs"
    ]:
        raise RuntimeError(
            "corrupt diagnostic topology mismatch"
        )

    if first[
        "clean"
    ][
        "registration_count"
    ] != expected[
        "clean_registration_count"
    ]:
        raise RuntimeError(
            "clean diagnostic record-count mismatch"
        )

    if first[
        "corrupt"
    ][
        "registration_count"
    ] != expected[
        "corrupt_registration_count"
    ]:
        raise RuntimeError(
            "corrupt diagnostic record-count mismatch"
        )

    if first[
        "corruption"
    ][
        "spec_id"
    ] != config[
        "source"
    ][
        "corruption_spec_id"
    ]:
        raise RuntimeError(
            "corruption spec identity mismatch"
        )

    if first[
        "corruption"
    ][
        "injection_id"
    ] != config[
        "source"
    ][
        "corruption_injection_id"
    ]:
        raise RuntimeError(
            "corruption injection identity mismatch"
        )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    run_manifest = {
        "schema":
            "TRUST_ROBOT_PHASE4_LIDAR_PAIRED_DIAGNOSTICS_RUN_MANIFEST_V1",

        "schema_version":
            1,

        "status":
            "completed_from_existing_phase3_receipt",

        "config": {
            "file_sha256":
                file_sha256(
                    config_path
                ),

            "content_sha256":
                config[
                    "content_sha256"
                ],
        },

        "source": {
            "phase3_receipt_file_sha256":
                actual_source_sha,

            "phase3_receipt_content_sha256":
                receipt[
                    "content_sha256"
                ],

            "ros_bag_opened":
                False,

            "pointcloud_decoded":
                False,

            "registration_rerun":
                False,

            "corruption_rerun":
                False,
        },

        "output": {
            "clean_registration_count":
                first[
                    "clean"
                ][
                    "registration_count"
                ],

            "corrupt_registration_count":
                first[
                    "corrupt"
                ][
                    "registration_count"
                ],

            "paired_diagnostic_artifact_content_sha256":
                first[
                    "content_sha256"
                ],
        },

        "scientific_scope": {
            "descriptive_statistics_computed":
                False,

            "clean_corrupt_numeric_difference_computed":
                False,

            "threshold_applied":
                False,

            "health_label_emitted":
                False,

            "fault_label_emitted":
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
    ] = canonical_sha256(
        run_manifest
    )

    summary = {
        "schema":
            "TRUST_ROBOT_PHASE4_LIDAR_PAIRED_DIAGNOSTICS_SUMMARY_V1",

        "schema_version":
            1,

        "clean_registration_count":
            first[
                "clean"
            ][
                "registration_count"
            ],

        "corrupt_registration_count":
            first[
                "corrupt"
            ][
                "registration_count"
            ],

        "clean_origin_pairs":
            first[
                "clean"
            ][
                "origin_pairs"
            ],

        "corrupt_origin_pairs":
            first[
                "corrupt"
            ][
                "origin_pairs"
            ],

        "corruption_spec_id":
            first[
                "corruption"
            ][
                "spec_id"
            ],

        "corruption_injection_id":
            first[
                "corruption"
            ][
                "injection_id"
            ],

        "paired_diagnostic_artifact_content_sha256":
            first[
                "content_sha256"
            ],

        "interpretation": {
            "same_extractor_used_for_clean_and_corrupt":
                True,

            "clean_corrupt_numeric_difference_computed":
                False,

            "descriptive_statistics_computed":
                False,

            "threshold_applied":
                False,

            "health_label_emitted":
                False,

            "fault_label_emitted":
                False,

            "accuracy_score_emitted":
                False,
        },
    }

    summary[
        "content_sha256"
    ] = canonical_sha256(
        summary
    )

    immutable_write(
        output_dir
        / "run_manifest.json",
        json.dumps(
            run_manifest,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
    )

    immutable_write(
        output_dir
        / "paired_diagnostics.json",
        json.dumps(
            first,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n",
    )

    immutable_write(
        output_dir
        / "summary.json",
        json.dumps(
            summary,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
    )

    immutable_write(
        output_dir
        / "SUCCESS",
        (
            "TRUST_ROBOT_PHASE4_LIDAR_PAIRED_DIAGNOSTICS_V1=PASS\n"
        ),
    )

    print(
        "clean_registration_count=",
        first[
            "clean"
        ][
            "registration_count"
        ],
    )

    print(
        "corrupt_registration_count=",
        first[
            "corrupt"
        ][
            "registration_count"
        ],
    )

    print(
        "clean_origin_pairs=",
        first[
            "clean"
        ][
            "origin_pairs"
        ],
    )

    print(
        "corrupt_origin_pairs=",
        first[
            "corrupt"
        ][
            "origin_pairs"
        ],
    )

    print(
        "corruption_spec_id=",
        first[
            "corruption"
        ][
            "spec_id"
        ],
    )

    print(
        "corruption_injection_id=",
        first[
            "corruption"
        ][
            "injection_id"
        ],
    )

    print(
        "paired_diagnostic_artifact_content_sha256=",
        first[
            "content_sha256"
        ],
    )

    print(
        "paired_extraction_repeated_exactly=true"
    )

    print(
        "same_extractor_used_for_clean_and_corrupt=true"
    )

    print(
        "registration_rerun=false"
    )

    print(
        "corruption_rerun=false"
    )

    print(
        "clean_corrupt_numeric_difference_computed=false"
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
        "TRUST_ROBOT_PHASE4_LIDAR_PAIRED_DIAGNOSTICS_V1=PASS"
    )


if __name__ == "__main__":
    main()
