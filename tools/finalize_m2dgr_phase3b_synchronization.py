#!/usr/bin/env python3
from __future__ import annotations

from argparse import ArgumentParser
from hashlib import sha256
from pathlib import Path
import json
import sys


REPOSITORY_ROOT = (
    Path(__file__).resolve().parents[1]
)

SOURCE_ROOT = (
    REPOSITORY_ROOT
    / "src"
)

if str(
    SOURCE_ROOT
) not in sys.path:
    sys.path.insert(
        0,
        str(
            SOURCE_ROOT
        ),
    )


from trust_robot.m2dgr_manifest_builder import (
    build_phase3b_synchronization_successor_payload,
)
from trust_robot.m2dgr_synchronization_evidence import (
    CONSERVATIVE_CLOCK_DOMAINS,
    load_m2dgr_synchronization_evidence,
    verify_synchronization_evidence_sources,
)
from trust_robot.trajectory_manifest import (
    load_manifest,
)


def sha256_file(
    path: Path,
) -> str:
    digest = sha256()

    with path.open(
        "rb"
    ) as handle:
        while True:
            block = handle.read(
                1024 * 1024
            )

            if not block:
                break

            digest.update(
                block
            )

    return digest.hexdigest()


def immutable_text_write(
    path: Path,
    content: str,
) -> None:
    if path.exists():
        existing = path.read_text(
            encoding="utf-8"
        )

        if existing != content:
            raise FileExistsError(
                "immutable artifact already exists "
                f"with different content: {path}"
            )

        return

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "x",
        encoding="utf-8",
        newline="\n",
    ) as handle:
        handle.write(
            content
        )

        handle.flush()


def parse_args():
    parser = ArgumentParser(
        description=(
            "Finalize the conservative M2DGR Phase-3B "
            "synchronization-evidence artifact and successor manifest."
        )
    )

    parser.add_argument(
        "--dataset-root",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--phase3-manifest",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--input-evidence",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--output-evidence",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--output-manifest",
        required=True,
        type=Path,
    )

    return parser.parse_args()


def main():
    args = parse_args()

    dataset_root = (
        args.dataset_root
        .resolve()
    )

    phase3 = load_manifest(
        args.phase3_manifest
    )

    evidence = (
        load_m2dgr_synchronization_evidence(
            args.input_evidence
        )
    )

    verify_synchronization_evidence_sources(
        dataset_root,
        evidence,
    )

    successor = (
        build_phase3b_synchronization_successor_payload(
            phase3,
            evidence,
        )
    )

    evidence_text = (
        args.input_evidence
        .read_text(
            encoding="utf-8"
        )
    )

    successor_text = (
        json.dumps(
            successor,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        + "\n"
    )

    immutable_text_write(
        args.output_evidence,
        evidence_text,
    )

    immutable_text_write(
        args.output_manifest,
        successor_text,
    )

    stream_count = sum(
        len(
            row[
                "streams"
            ]
        )
        for row in successor[
            "records"
        ]
    )

    sync_count = sum(
        len(
            row[
                "synchronization"
            ]
        )
        for row in successor[
            "records"
        ]
    )

    for row in successor[
        "records"
    ]:
        stream_domain = {
            item[
                "stream_id"
            ]:
                item[
                    "clock_domain"
                ]
            for item in row[
                "streams"
            ]
        }

        sync_domain = {
            item[
                "stream_id"
            ]:
                item[
                    "clock_domain"
                ]
            for item in row[
                "synchronization"
            ]
        }

        if stream_domain != sync_domain:
            raise RuntimeError(
                f"{row['trajectory_id']}: "
                "stream/synchronization clock domains disagree"
            )

        for stream_id, domain in stream_domain.items():
            if domain != CONSERVATIVE_CLOCK_DOMAINS[
                stream_id
            ]:
                raise RuntimeError(
                    f"{row['trajectory_id']}: "
                    f"unexpected conservative domain for "
                    f"{stream_id}"
                )

        for sync in row[
            "synchronization"
        ]:
            if sync[
                "verification_status"
            ] != "unverified":
                raise RuntimeError(
                    "Phase-3B successor must remain unverified"
                )

            if sync[
                "measurement_time_basis"
            ] != "sensor_header_stamp":
                raise RuntimeError(
                    "Phase-3B successor must preserve header measurement basis"
                )

            if sync[
                "fixed_offset_seconds"
            ] is not None:
                raise RuntimeError(
                    "Phase-3B successor must not freeze a fixed offset"
                )

            if sync[
                "tolerance_seconds"
            ] is not None:
                raise RuntimeError(
                    "Phase-3B successor must not freeze a tolerance"
                )

    print(
        "trajectory_count:",
        len(
            successor[
                "records"
            ]
        ),
    )

    print(
        "stream_entries:",
        stream_count,
    )

    print(
        "synchronization_entries:",
        sync_count,
    )

    print(
        "phase3_source_manifest_content_sha256:",
        phase3[
            "manifest_content_sha256"
        ],
    )

    print(
        "phase3b_evidence_content_sha256:",
        evidence[
            "content_sha256"
        ],
    )

    print(
        "phase3b_evidence_file_sha256:",
        sha256_file(
            args.output_evidence
        ),
    )

    print(
        "phase3b_manifest_content_sha256:",
        successor[
            "manifest_content_sha256"
        ],
    )

    print(
        "phase3b_manifest_file_sha256:",
        sha256_file(
            args.output_manifest
        ),
    )

    print(
        "clock_domain_verified:",
        False,
    )

    print(
        "synchronization_verified:",
        False,
    )

    print(
        "fixed_offset_estimated:",
        False,
    )

    print(
        "synchronization_tolerance_frozen:",
        False,
    )

    print(
        "evaluation_ready:",
        False,
    )


if __name__ == "__main__":
    main()
