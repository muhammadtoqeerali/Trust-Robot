#!/usr/bin/env python3
from __future__ import annotations

from argparse import ArgumentParser
from hashlib import sha256
from pathlib import Path
import json
import sys


REPOSITORY_ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
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


from trust_robot.m2dgr_lidar_imu_synchronization_evidence import (
    LIDAR_SYNC_STREAM_IDS,
    build_m2dgr_lidar_imu_synchronization_evidence,
    load_phase3d_lidar_imu_staging_evidence,
    verify_phase3d_lidar_imu_staging_sources,
)
from trust_robot.m2dgr_manifest_builder import (
    build_phase3d_lidar_imu_successor_payload,
)
from trust_robot.trajectory_manifest import (
    load_manifest,
)


EXPECTED_PHASE3C_CONTENT_SHA256 = (
    "f599be5bb1b4d009fe77ff8eb3314888"
    "0122f92f4bfe00f885ec18015d715387"
)

EXPECTED_PHASE3C_FILE_SHA256 = (
    "4453544d437b31cb0ab16b090dfa2e71"
    "0fab19cb1b90cb65b53d7651166eb156"
)

EXPECTED_STAGING_CONTENT_SHA256 = (
    "0d274f0defdc1a2eaeb28c2a7dafe1d"
    "e1355408dcf8481756fdbd439cbe036f9"
)

EXPECTED_STAGING_FILE_SHA256 = (
    "6ae8e201d0b18a8f9a20f169b9ec431"
    "5496d6bde0e86eea3fbc15d1cc835e08c"
)

EXPECTED_TRAJECTORY_COUNT = 36
EXPECTED_STREAM_COUNT = 140
EXPECTED_SYNCHRONIZATION_COUNT = 140
EXPECTED_LIDAR_METHOD_UPDATE_COUNT = 36


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


def relative_to_dataset(
    path: Path,
    dataset_root: Path,
    label: str,
) -> str:
    resolved = path.resolve()

    try:
        relative = resolved.relative_to(
            dataset_root
        )
    except ValueError as exc:
        raise ValueError(
            f"{label} must be inside dataset root"
        ) from exc

    return relative.as_posix()


def parse_args():
    parser = ArgumentParser(
        description=(
            "Finalize M2DGR Phase-3D LiDAR/IMU "
            "synchronization evidence and conservative "
            "manifest successor."
        )
    )

    parser.add_argument(
        "--dataset-root",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--phase3c-manifest",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--staging-evidence",
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

    phase3c = load_manifest(
        args.phase3c_manifest
    )

    if (
        phase3c[
            "manifest_content_sha256"
        ]
        != EXPECTED_PHASE3C_CONTENT_SHA256
    ):
        raise RuntimeError(
            "unexpected Phase-3C source manifest "
            "content SHA256"
        )

    actual_phase3c_file_sha = (
        sha256_file(
            args.phase3c_manifest
        )
    )

    if (
        actual_phase3c_file_sha
        != EXPECTED_PHASE3C_FILE_SHA256
    ):
        raise RuntimeError(
            "unexpected Phase-3C source manifest file SHA256"
        )

    staging = (
        load_phase3d_lidar_imu_staging_evidence(
            args.staging_evidence
        )
    )

    if (
        staging[
            "content_sha256"
        ]
        != EXPECTED_STAGING_CONTENT_SHA256
    ):
        raise RuntimeError(
            "unexpected Phase-3D staging content SHA256"
        )

    actual_staging_file_sha = (
        sha256_file(
            args.staging_evidence
        )
    )

    if (
        actual_staging_file_sha
        != EXPECTED_STAGING_FILE_SHA256
    ):
        raise RuntimeError(
            "unexpected Phase-3D staging file SHA256"
        )

    verify_phase3d_lidar_imu_staging_sources(
        dataset_root,
        staging,
    )

    staging_relative_path = (
        relative_to_dataset(
            args.staging_evidence,
            dataset_root,
            "staging evidence",
        )
    )

    evidence_relative_path = (
        relative_to_dataset(
            args.output_evidence,
            dataset_root,
            "output evidence",
        )
    )

    relative_to_dataset(
        args.output_manifest,
        dataset_root,
        "output manifest",
    )

    permanent_evidence = (
        build_m2dgr_lidar_imu_synchronization_evidence(
            phase3c,
            staging,
            staging_relative_path=
                staging_relative_path,
            staging_file_sha256=
                actual_staging_file_sha,
            staging_size_bytes=
                args.staging_evidence
                .stat()
                .st_size,
        )
    )

    successor = (
        build_phase3d_lidar_imu_successor_payload(
            phase3c,
            permanent_evidence,
            evidence_relative_path=
                evidence_relative_path,
        )
    )

    evidence_text = (
        json.dumps(
            permanent_evidence,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        + "\n"
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

    old_by_id = {
        row[
            "trajectory_id"
        ]:
            row
        for row in phase3c[
            "records"
        ]
    }

    updated_count = 0
    stream_count = 0
    sync_count = 0

    for new_row in successor[
        "records"
    ]:
        trajectory_id = new_row[
            "trajectory_id"
        ]

        old_row = old_by_id[
            trajectory_id
        ]

        stream_count += len(
            new_row[
                "streams"
            ]
        )

        sync_count += len(
            new_row[
                "synchronization"
            ]
        )

        if (
            new_row[
                "streams"
            ]
            != old_row[
                "streams"
            ]
        ):
            raise RuntimeError(
                f"{trajectory_id}: "
                "Phase-3D changed stream metadata"
            )

        for key, value in (
            old_row.items()
        ):
            if key == "synchronization":
                continue

            if new_row[
                key
            ] != value:
                raise RuntimeError(
                    f"{trajectory_id}: "
                    f"Phase-3D changed record field {key}"
                )

        old_sync = {
            item[
                "stream_id"
            ]:
                item
            for item in old_row[
                "synchronization"
            ]
        }

        new_sync = {
            item[
                "stream_id"
            ]:
                item
            for item in new_row[
                "synchronization"
            ]
        }

        if set(
            old_sync
        ) != set(
            new_sync
        ):
            raise RuntimeError(
                f"{trajectory_id}: "
                "synchronization inventory changed"
            )

        for stream_id in old_sync:
            previous = old_sync[
                stream_id
            ]

            current = new_sync[
                stream_id
            ]

            if (
                current[
                    "verification_status"
                ]
                != "unverified"
            ):
                raise RuntimeError(
                    "Phase-3D successor must remain unverified"
                )

            if (
                current[
                    "measurement_time_basis"
                ]
                != "sensor_header_stamp"
            ):
                raise RuntimeError(
                    "Phase-3D successor must preserve "
                    "sensor_header_stamp basis"
                )

            if (
                current[
                    "fixed_offset_seconds"
                ] is not None
                or current[
                    "fixed_offset_method"
                ] is not None
                or current[
                    "tolerance_seconds"
                ] is not None
                or current[
                    "tolerance_evidence"
                ] is not None
                or current[
                    "tolerance_selected_on_split"
                ] is not None
            ):
                raise RuntimeError(
                    "Phase-3D successor must not freeze "
                    "offset/tolerance decisions"
                )

            if (
                stream_id
                not in LIDAR_SYNC_STREAM_IDS
            ):
                if current != previous:
                    raise RuntimeError(
                        f"{trajectory_id}: non-LiDAR "
                        f"synchronization changed for {stream_id}"
                    )

                continue

            for key, value in (
                previous.items()
            ):
                if key == "method":
                    continue

                if current[
                    key
                ] != value:
                    raise RuntimeError(
                        f"{trajectory_id}: LiDAR "
                        f"field changed for {stream_id}/{key}"
                    )

            if (
                current[
                    "method"
                ]
                == previous[
                    "method"
                ]
            ):
                raise RuntimeError(
                    f"{trajectory_id}: expected Phase-3D "
                    f"method update for {stream_id}"
                )

            if (
                "Phase-3D LiDAR/IMU synchronization evidence"
                not in current[
                    "method"
                ]
            ):
                raise RuntimeError(
                    f"{trajectory_id}: Phase-3D method "
                    "does not cite Phase-3D evidence"
                )

            if (
                evidence_relative_path
                not in current[
                    "method"
                ]
            ):
                raise RuntimeError(
                    f"{trajectory_id}: Phase-3D method "
                    "does not bind evidence path"
                )

            updated_count += 1

    if (
        len(
            successor[
                "records"
            ]
        )
        != EXPECTED_TRAJECTORY_COUNT
    ):
        raise RuntimeError(
            "unexpected successor trajectory count"
        )

    if (
        stream_count
        != EXPECTED_STREAM_COUNT
    ):
        raise RuntimeError(
            "unexpected successor stream count"
        )

    if (
        sync_count
        != EXPECTED_SYNCHRONIZATION_COUNT
    ):
        raise RuntimeError(
            "unexpected successor synchronization count"
        )

    if (
        updated_count
        != EXPECTED_LIDAR_METHOD_UPDATE_COUNT
    ):
        raise RuntimeError(
            "unexpected Phase-3D LiDAR method-update count"
        )

    immutable_text_write(
        args.output_evidence,
        evidence_text,
    )

    immutable_text_write(
        args.output_manifest,
        successor_text,
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
        "lidar_method_updates:",
        updated_count,
    )

    print(
        "phase3c_source_manifest_content_sha256:",
        phase3c[
            "manifest_content_sha256"
        ],
    )

    print(
        "phase3c_source_manifest_file_sha256:",
        actual_phase3c_file_sha,
    )

    print(
        "phase3d_staging_content_sha256:",
        staging[
            "content_sha256"
        ],
    )

    print(
        "phase3d_staging_file_sha256:",
        actual_staging_file_sha,
    )

    print(
        "phase3d_evidence_content_sha256:",
        permanent_evidence[
            "content_sha256"
        ],
    )

    print(
        "phase3d_evidence_file_sha256:",
        sha256_file(
            args.output_evidence
        ),
    )

    print(
        "phase3d_manifest_content_sha256:",
        successor[
            "manifest_content_sha256"
        ],
    )

    print(
        "phase3d_manifest_file_sha256:",
        sha256_file(
            args.output_manifest
        ),
    )

    print(
        "clock_domains_modified:",
        False,
    )

    print(
        "fixed_offset_estimated:",
        False,
    )

    print(
        "fixed_offset_applied:",
        False,
    )

    print(
        "synchronization_tolerance_frozen:",
        False,
    )

    print(
        "physical_capture_synchronization_verified:",
        False,
    )

    print(
        "synchronization_verified:",
        False,
    )

    print(
        "evaluation_ready:",
        False,
    )

    print(
        "PHASE3D_FINALIZATION=PASS"
    )


if __name__ == "__main__":
    main()
