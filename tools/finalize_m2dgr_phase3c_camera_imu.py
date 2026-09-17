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


from trust_robot.m2dgr_camera_imu_synchronization_evidence import (
    CAMERA_IMU_STREAM_IDS,
    build_m2dgr_camera_imu_synchronization_evidence,
    load_phase3c_camera_imu_staging_evidence,
    verify_phase3c_camera_imu_staging_sources,
)
from trust_robot.m2dgr_manifest_builder import (
    build_phase3c_camera_imu_successor_payload,
)
from trust_robot.trajectory_manifest import (
    load_manifest,
)


EXPECTED_PHASE3B_CONTENT_SHA256 = (
    "5cf660327636174912d5d304972758c1"
    "b230fa4446ab584ca4549c76fdd6f4db"
)

EXPECTED_TRAJECTORY_COUNT = 36
EXPECTED_STREAM_COUNT = 140
EXPECTED_SYNCHRONIZATION_COUNT = 140
EXPECTED_CAMERA_IMU_METHOD_UPDATE_COUNT = 68


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
            "Finalize M2DGR Phase-3C camera/IMU "
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
        "--phase3b-manifest",
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

    phase3b = load_manifest(
        args.phase3b_manifest
    )

    if (
        phase3b[
            "manifest_content_sha256"
        ]
        != EXPECTED_PHASE3B_CONTENT_SHA256
    ):
        raise RuntimeError(
            "unexpected Phase-3B source manifest "
            "content SHA256"
        )

    staging = (
        load_phase3c_camera_imu_staging_evidence(
            args.staging_evidence
        )
    )

    verify_phase3c_camera_imu_staging_sources(
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
        build_m2dgr_camera_imu_synchronization_evidence(
            phase3b,
            staging,
            staging_relative_path=
                staging_relative_path,
            staging_file_sha256=
                sha256_file(
                    args.staging_evidence
                ),
            staging_size_bytes=
                args.staging_evidence
                .stat()
                .st_size,
        )
    )

    successor = (
        build_phase3c_camera_imu_successor_payload(
            phase3b,
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
        for row in phase3b[
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
                "Phase-3C changed stream metadata"
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
                    f"Phase-3C changed record field {key}"
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
                    "Phase-3C successor must remain unverified"
                )

            if (
                current[
                    "measurement_time_basis"
                ]
                != "sensor_header_stamp"
            ):
                raise RuntimeError(
                    "Phase-3C successor must preserve "
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
                    "Phase-3C successor must not freeze "
                    "offset/tolerance decisions"
                )

            if (
                stream_id
                not in CAMERA_IMU_STREAM_IDS
            ):
                if current != previous:
                    raise RuntimeError(
                        f"{trajectory_id}: non-camera "
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
                        f"{trajectory_id}: camera/IMU "
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
                    f"{trajectory_id}: expected Phase-3C "
                    f"method update for {stream_id}"
                )

            if (
                "Phase-3C camera/IMU synchronization evidence"
                not in current[
                    "method"
                ]
            ):
                raise RuntimeError(
                    f"{trajectory_id}: Phase-3C method "
                    f"does not cite Phase-3C evidence"
                )

            if (
                evidence_relative_path
                not in current[
                    "method"
                ]
            ):
                raise RuntimeError(
                    f"{trajectory_id}: Phase-3C method "
                    f"does not bind evidence path"
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
        != EXPECTED_CAMERA_IMU_METHOD_UPDATE_COUNT
    ):
        raise RuntimeError(
            "unexpected Phase-3C camera/IMU method-update count"
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
        "camera_imu_method_updates:",
        updated_count,
    )

    print(
        "phase3b_source_manifest_content_sha256:",
        phase3b[
            "manifest_content_sha256"
        ],
    )

    print(
        "phase3c_staging_content_sha256:",
        staging[
            "content_sha256"
        ],
    )

    print(
        "phase3c_staging_file_sha256:",
        sha256_file(
            args.staging_evidence
        ),
    )

    print(
        "phase3c_evidence_content_sha256:",
        permanent_evidence[
            "content_sha256"
        ],
    )

    print(
        "phase3c_evidence_file_sha256:",
        sha256_file(
            args.output_evidence
        ),
    )

    print(
        "phase3c_manifest_content_sha256:",
        successor[
            "manifest_content_sha256"
        ],
    )

    print(
        "phase3c_manifest_file_sha256:",
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
        "PHASE3C_FINALIZATION=PASS"
    )


if __name__ == "__main__":
    main()
