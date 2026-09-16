#!/usr/bin/env python3
from __future__ import annotations

from argparse import ArgumentParser
from importlib.metadata import version
from pathlib import Path
import json
import os
import tempfile

from rosbags.highlevel import AnyReader


SCHEMA = "trust_robot.m2dgr_exact_header_anomaly"
SCHEMA_VERSION = 1


def stamp_to_ns(stamp) -> int:
    sec = None
    nsec = None

    for name in ("sec", "secs"):
        if hasattr(stamp, name):
            sec = int(getattr(stamp, name))
            break

    for name in ("nanosec", "nsec", "nsecs"):
        if hasattr(stamp, name):
            nsec = int(getattr(stamp, name))
            break

    if sec is None or nsec is None:
        raise RuntimeError(
            "unable to decode ROS header timestamp"
        )

    return sec * 1_000_000_000 + nsec


def read_checksum(
    dataset_root: Path,
    trajectory_id: str,
):
    path = (
        dataset_root
        / "checksums"
        / f"{trajectory_id}.bag.sha256"
    )

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
            f"malformed bag checksum sidecar: {path}"
        )

    digest, source = fields

    if not source.endswith(
        f"/raw/rosbags/{trajectory_id}.bag"
    ):
        raise RuntimeError(
            "checksum source path mismatch"
        )

    return digest, path


def write_json_atomic(
    path: Path,
    payload: dict,
):
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    content = (
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n"
    )

    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
        text=True,
    )

    temporary = Path(temporary_name)

    try:
        with os.fdopen(
            fd,
            "w",
            encoding="utf-8",
            newline="\n",
        ) as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())

        os.replace(
            temporary,
            path,
        )
    finally:
        temporary.unlink(
            missing_ok=True
        )


def sample_dict(
    index: int,
    header_ns: int,
    record_ns: int,
    frame_id: str,
):
    return {
        "index": index,
        "header_ns": header_ns,
        "record_ns": record_ns,
        "record_minus_header_ns": (
            record_ns
            - header_ns
        ),
        "record_minus_header_ms": (
            record_ns
            - header_ns
        )
        / 1_000_000.0,
        "frame_id": frame_id,
    }


def parse_args():
    parser = ArgumentParser(
        description=(
            "Locate exact reversed header timestamp pairs for one M2DGR topic. "
            "Detection is structural and threshold-free."
        )
    )

    parser.add_argument(
        "--dataset-root",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--trajectory",
        required=True,
    )

    parser.add_argument(
        "--topic",
        required=True,
    )

    parser.add_argument(
        "--aggregate-artifact",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--output",
        required=True,
        type=Path,
    )

    return parser.parse_args()


def main():
    args = parse_args()

    dataset_root = args.dataset_root.resolve()
    trajectory_id = args.trajectory
    topic = args.topic

    bag = (
        dataset_root
        / "raw"
        / "rosbags"
        / f"{trajectory_id}.bag"
    )

    digest, checksum_path = (
        read_checksum(
            dataset_root,
            trajectory_id,
        )
    )

    aggregate = json.loads(
        args.aggregate_artifact.read_text(
            encoding="utf-8"
        )
    )

    expected_reverse_count = (
        aggregate[
            "streams"
        ][
            topic
        ][
            "header_time"
        ][
            "reverse_count"
        ]
    )

    headers = []
    records = []
    frame_ids = []
    message_types = []
    decode_errors = []

    print(
        f"[SCAN] {bag}",
        flush=True,
    )

    with AnyReader(
        [bag]
    ) as reader:
        selected = [
            connection
            for connection in reader.connections
            if connection.topic == topic
        ]

        if not selected:
            raise RuntimeError(
                f"{topic} is absent"
            )

        for (
            connection,
            record_ns,
            rawdata,
        ) in reader.messages(
            connections=selected
        ):
            index = len(
                headers
            )

            try:
                message = reader.deserialize(
                    rawdata,
                    connection.msgtype,
                )

                header = message.header

                header_ns = stamp_to_ns(
                    header.stamp
                )

                frame_id = str(
                    getattr(
                        header,
                        "frame_id",
                        "",
                    )
                )

            except Exception as exc:
                if len(
                    decode_errors
                ) < 10:
                    decode_errors.append(
                        {
                            "index":
                                index,
                            "exception_type":
                                type(
                                    exc
                                ).__name__,
                            "message":
                                str(
                                    exc
                                ),
                        }
                    )

                continue

            headers.append(
                int(
                    header_ns
                )
            )

            records.append(
                int(
                    record_ns
                )
            )

            frame_ids.append(
                frame_id
            )

            message_types.append(
                connection.msgtype
            )

    if decode_errors:
        raise RuntimeError(
            f"unexpected decode errors: {decode_errors}"
        )

    reversals = []
    duplicates = []

    for index in range(
        1,
        len(headers),
    ):
        previous = headers[
            index - 1
        ]

        current = headers[
            index
        ]

        delta = (
            current
            - previous
        )

        if delta < 0:
            start = max(
                0,
                index - 5,
            )

            stop = min(
                len(headers),
                index + 6,
            )

            context = [
                sample_dict(
                    j,
                    headers[j],
                    records[j],
                    frame_ids[j],
                )
                for j in range(
                    start,
                    stop,
                )
            ]

            reversals.append(
                {
                    "previous_index":
                        index - 1,
                    "current_index":
                        index,
                    "previous_header_ns":
                        previous,
                    "current_header_ns":
                        current,
                    "delta_ns":
                        delta,
                    "delta_ms":
                        float(delta)
                        / 1_000_000.0,
                    "previous_record_ns":
                        records[
                            index - 1
                        ],
                    "current_record_ns":
                        records[
                            index
                        ],
                    "previous_record_minus_header_ns":
                        records[
                            index - 1
                        ]
                        - previous,
                    "current_record_minus_header_ns":
                        records[
                            index
                        ]
                        - current,
                    "context":
                        context,
                }
            )

        elif delta == 0:
            duplicates.append(
                {
                    "previous_index":
                        index - 1,
                    "current_index":
                        index,
                    "header_ns":
                        current,
                }
            )

    if (
        len(reversals)
        != expected_reverse_count
    ):
        raise RuntimeError(
            "targeted reversal count does not match aggregate evidence: "
            f"targeted={len(reversals)} "
            f"aggregate={expected_reverse_count}"
        )

    payload = {
        "schema":
            SCHEMA,
        "version":
            SCHEMA_VERSION,
        "trajectory_id":
            trajectory_id,
        "topic":
            topic,
        "source": {
            "relative_path":
                bag
                .relative_to(
                    dataset_root
                )
                .as_posix(),
            "recorded_sha256":
                digest,
            "checksum_sidecar":
                checksum_path
                .relative_to(
                    dataset_root
                )
                .as_posix(),
            "raw_modified":
                False,
        },
        "reader": {
            "message_deserialization":
                True,
            "package":
                "rosbags",
            "scan_completed":
                True,
            "targeted_topic_scan":
                True,
            "version":
                version(
                    "rosbags"
                ),
        },
        "stream": {
            "duplicate_count":
                len(
                    duplicates
                ),
            "first_header_ns":
                headers[0],
            "frame_ids":
                sorted(
                    set(
                        frame_ids
                    )
                ),
            "last_header_ns":
                headers[-1],
            "message_count":
                len(
                    headers
                ),
            "message_types":
                sorted(
                    set(
                        message_types
                    )
                ),
            "reverse_count":
                len(
                    reversals
                ),
        },
        "reversals":
            reversals,
        "duplicates":
            duplicates,
        "comparison": {
            "aggregate_artifact":
                args.aggregate_artifact
                .relative_to(
                    dataset_root
                )
                .as_posix(),
            "aggregate_reverse_count":
                expected_reverse_count,
            "counts_match":
                (
                    len(reversals)
                    == expected_reverse_count
                ),
            "targeted_reverse_count":
                len(
                    reversals
                ),
        },
        "policy": {
            "automatic_sample_exclusion_rule_created":
                False,
            "automatic_sample_repair":
                False,
            "fixed_time_offset_estimated":
                False,
            "structural_reverse_timestamp":
                True,
            "synchronization_tolerance_frozen":
                False,
            "synchronization_verified":
                False,
            "threshold_required_to_detect":
                False,
        },
    }

    write_json_atomic(
        args.output,
        payload,
    )

    print(
        f"[DONE] messages={len(headers)} "
        f"reversals={len(reversals)} "
        f"duplicates={len(duplicates)}",
        flush=True,
    )

    for reversal in reversals:
        print(
            "[REVERSAL] "
            f"previous_index={reversal['previous_index']} "
            f"current_index={reversal['current_index']} "
            f"delta_ms={reversal['delta_ms']}",
            flush=True,
        )

    print(
        f"[OUTPUT] {args.output}",
        flush=True,
    )

    print(
        "automatic_sample_exclusion_rule_created = FALSE",
        flush=True,
    )


if __name__ == "__main__":
    main()
