#!/usr/bin/env python3
from __future__ import annotations

from argparse import ArgumentParser
from hashlib import sha256
from pathlib import Path
import json
import re
import sys


REPOSITORY_ROOT = (
    Path(__file__).resolve().parents[1]
)

SOURCE_ROOT = (
    REPOSITORY_ROOT
    / "src"
)

if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(SOURCE_ROOT),
    )


from trust_robot.m2dgr_manifest_builder import (
    build_phase3_timing_successor_payload,
)
from trust_robot.m2dgr_timing_evidence import (
    build_m2dgr_timing_evidence_index,
    canonical_m2dgr_timing_evidence_index_json,
    load_m2dgr_stream_timing_for_trajectory,
    validate_m2dgr_timing_evidence_index,
)
from trust_robot.trajectory_manifest import (
    load_manifest,
)


HEX64 = re.compile(
    r"^[0-9a-f]{64}$"
)


def sha256_file(
    path: Path,
) -> str:
    digest = sha256()

    with path.open("rb") as handle:
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


def read_sidecar(
    path: Path,
) -> tuple[str, str]:
    fields = (
        path.read_text(
            encoding="utf-8"
        )
        .strip()
        .split(
            maxsplit=1
        )
    )

    if len(fields) != 2:
        raise RuntimeError(
            f"malformed checksum sidecar: {path}"
        )

    digest = fields[0].lower()
    source = fields[1].strip()

    if not HEX64.fullmatch(
        digest
    ):
        raise RuntimeError(
            f"invalid SHA256 in {path}"
        )

    return (
        digest,
        source,
    )


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


def validate_bag_checksum_bindings(
    dataset_root: Path,
    phase2_payload: dict,
    timing_index: dict,
) -> None:
    phase2_by_id = {
        record[
            "trajectory_id"
        ]: record
        for record in phase2_payload[
            "records"
        ]
    }

    index_by_id = {
        item[
            "trajectory_id"
        ]: item
        for item in timing_index[
            "artifacts"
        ]
    }

    for trajectory_id, record in (
        phase2_by_id.items()
    ):
        sidecar = (
            dataset_root
            / "checksums"
            / f"{trajectory_id}.bag.sha256"
        )

        sidecar_sha, source = read_sidecar(
            sidecar
        )

        if not source.endswith(
            f"/raw/rosbags/{trajectory_id}.bag"
        ):
            raise RuntimeError(
                f"{trajectory_id}: checksum sidecar path mismatch"
            )

        matching = [
            artifact
            for artifact in record[
                "calibration_artifacts"
            ]
            if artifact[
                "source_path"
            ] == (
                f"raw/rosbags/"
                f"{trajectory_id}.bag"
            )
        ]

        if len(matching) != 1:
            raise RuntimeError(
                f"{trajectory_id}: expected exactly one "
                "bag-integrity artifact in Phase-2 manifest"
            )

        timing = (
            load_m2dgr_stream_timing_for_trajectory(
                dataset_root,
                trajectory_id,
            )
        )

        values = (
            sidecar_sha,
            matching[0][
                "sha256"
            ],
            timing[
                "source"
            ][
                "recorded_sha256"
            ],
            index_by_id[
                trajectory_id
            ][
                "raw_bag_sha256"
            ],
        )

        if len(
            set(
                values
            )
        ) != 1:
            raise RuntimeError(
                f"{trajectory_id}: bag checksum provenance mismatch"
            )


def parse_args():
    parser = ArgumentParser(
        description=(
            "Build the conservative Phase-3 M2DGR timing-evidence "
            "index and successor manifest without rehashing bag payloads."
        )
    )

    parser.add_argument(
        "--dataset-root",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--phase2-manifest",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--output-index",
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

    phase2 = load_manifest(
        args.phase2_manifest
    )

    trajectory_ids = sorted(
        record[
            "trajectory_id"
        ]
        for record in phase2[
            "records"
        ]
    )

    index = (
        build_m2dgr_timing_evidence_index(
            dataset_root,
            trajectory_ids,
        )
    )

    validate_m2dgr_timing_evidence_index(
        index
    )

    validate_bag_checksum_bindings(
        dataset_root,
        phase2,
        index,
    )

    successor = (
        build_phase3_timing_successor_payload(
            dataset_root,
            phase2,
        )
    )

    index_text = (
        canonical_m2dgr_timing_evidence_index_json(
            index
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
        args.output_index,
        index_text,
    )

    immutable_text_write(
        args.output_manifest,
        successor_text,
    )

    print(
        "trajectory_count:",
        len(
            trajectory_ids
        )
    )

    print(
        "timing_index_content_sha256:",
        index[
            "index_content_sha256"
        ],
    )

    print(
        "timing_index_file_sha256:",
        sha256_file(
            args.output_index
        ),
    )

    print(
        "phase3_manifest_content_sha256:",
        successor[
            "manifest_content_sha256"
        ],
    )

    print(
        "phase3_manifest_file_sha256:",
        sha256_file(
            args.output_manifest
        ),
    )

    print(
        "bag_content_rehashed:",
        False,
    )

    print(
        "synchronization_verified:",
        False,
    )

    print(
        "fixed_time_offset_estimated:",
        False,
    )

    print(
        "synchronization_tolerance_frozen:",
        False,
    )


if __name__ == "__main__":
    main()
