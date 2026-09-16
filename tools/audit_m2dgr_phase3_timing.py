#!/usr/bin/env python3
from __future__ import annotations

from argparse import ArgumentParser
from array import array
from collections import Counter
from importlib.metadata import version
from pathlib import Path
import json
import os
import tempfile
import traceback

import numpy as np
from rosbags.highlevel import AnyReader


SCHEMA = "trust_robot.m2dgr_phase3_stream_timing"
SCHEMA_VERSION = 1

TOPICS = (
    "/camera/color/image_raw/compressed",
    "/camera/imu",
    "/handsfree/imu",
    "/velodyne_points",
)

PAIRS = (
    (
        "/camera/color/image_raw/compressed",
        "/camera/imu",
    ),
    (
        "/camera/color/image_raw/compressed",
        "/handsfree/imu",
    ),
    (
        "/camera/imu",
        "/handsfree/imu",
    ),
    (
        "/velodyne_points",
        "/camera/imu",
    ),
    (
        "/velodyne_points",
        "/handsfree/imu",
    ),
)

TOP_K = 20


def percentile(values: np.ndarray, q: float):
    if values.size == 0:
        return None

    try:
        return float(
            np.percentile(
                values,
                q,
                method="linear",
            )
        )
    except TypeError:
        return float(
            np.percentile(
                values,
                q,
                interpolation="linear",
            )
        )


def summarize_ms(values_ns: np.ndarray):
    if values_ns.size == 0:
        return {
            "count": 0,
            "min": None,
            "median": None,
            "p05": None,
            "p95": None,
            "p99": None,
            "max": None,
        }

    values = (
        values_ns.astype(
            np.float64
        )
        / 1_000_000.0
    )

    return {
        "count": int(values.size),
        "min": float(values.min()),
        "median": percentile(values, 50),
        "p05": percentile(values, 5),
        "p95": percentile(values, 95),
        "p99": percentile(values, 99),
        "max": float(values.max()),
    }


def top_abs_indices(
    values: np.ndarray,
    k: int,
):
    n = int(values.size)

    if n == 0:
        return np.empty(
            0,
            dtype=np.int64,
        )

    k = min(
        k,
        n,
    )

    absolute = np.abs(
        values
    )

    if k == n:
        indices = np.arange(
            n,
            dtype=np.int64,
        )
    else:
        indices = np.argpartition(
            absolute,
            -k,
        )[-k:]

    return indices[
        np.argsort(
            absolute[
                indices
            ]
        )[::-1]
    ]


def top_largest_indices(
    values: np.ndarray,
    k: int,
):
    n = int(values.size)

    if n == 0:
        return np.empty(
            0,
            dtype=np.int64,
        )

    k = min(
        k,
        n,
    )

    if k == n:
        indices = np.arange(
            n,
            dtype=np.int64,
        )
    else:
        indices = np.argpartition(
            values,
            -k,
        )[-k:]

    return indices[
        np.argsort(
            values[
                indices
            ]
        )[::-1]
    ]


def stamp_to_ns(stamp) -> int:
    sec = None
    nsec = None

    for name in (
        "sec",
        "secs",
    ):
        if hasattr(
            stamp,
            name,
        ):
            sec = int(
                getattr(
                    stamp,
                    name,
                )
            )
            break

    for name in (
        "nanosec",
        "nsec",
        "nsecs",
    ):
        if hasattr(
            stamp,
            name,
        ):
            nsec = int(
                getattr(
                    stamp,
                    name,
                )
            )
            break

    if sec is None or nsec is None:
        raise AttributeError(
            "timestamp has no supported second/nanosecond fields"
        )

    return (
        sec * 1_000_000_000
        + nsec
    )


def read_checksum_sidecar(
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
            f"malformed checksum sidecar: {path}"
        )

    digest = fields[0]
    source = fields[1]

    if not source.endswith(
        f"/raw/rosbags/{trajectory_id}.bag"
    ):
        raise RuntimeError(
            f"{trajectory_id}: checksum source path mismatch"
        )

    return (
        digest,
        path,
    )


def atomic_json_write(
    destination: Path,
    payload: dict,
):
    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    content = (
        json.dumps(
            payload,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        + "\n"
    )

    fd, temporary_name = (
        tempfile.mkstemp(
            prefix=f".{destination.name}.",
            suffix=".tmp",
            dir=destination.parent,
            text=True,
        )
    )

    temporary = Path(
        temporary_name
    )

    try:
        with os.fdopen(
            fd,
            "w",
            encoding="utf-8",
            newline="\n",
        ) as handle:
            handle.write(
                content
            )
            handle.flush()
            os.fsync(
                handle.fileno()
            )

        os.replace(
            temporary,
            destination,
        )

    finally:
        temporary.unlink(
            missing_ok=True
        )


def as_np(values: array):
    if not values:
        return np.empty(
            0,
            dtype=np.int64,
        )

    return np.frombuffer(
        values,
        dtype=np.int64,
    )


def stream_summary(
    headers: array,
    records: array,
    frame_ids: Counter,
    message_types: set[str],
    message_count: int,
    decode_error_count: int,
):
    h = as_np(
        headers
    )

    r = as_np(
        records
    )

    if h.size != r.size:
        raise RuntimeError(
            "header/record length mismatch"
        )

    if h.size == 0:
        return {
            "message_count":
                message_count,
            "header_count":
                0,
            "decode_error_count":
                decode_error_count,
            "message_types":
                sorted(
                    message_types
                ),
            "frame_ids":
                dict(
                    sorted(
                        frame_ids.items()
                    )
                ),
            "header_time":
                None,
            "record_time":
                None,
            "record_minus_header_ms":
                None,
            "largest_header_intervals":
                [],
            "largest_absolute_record_header_offsets":
                [],
        }

    header_diff = np.diff(
        h
    )

    record_diff = np.diff(
        r
    )

    positive_header = (
        header_diff[
            header_diff > 0
        ]
    )

    positive_record = (
        record_diff[
            record_diff > 0
        ]
    )

    record_minus_header = (
        r - h
    )

    largest_intervals = []

    for index in top_largest_indices(
        header_diff,
        TOP_K,
    ):
        index = int(
            index
        )

        largest_intervals.append(
            {
                "previous_index":
                    index,
                "current_index":
                    index + 1,
                "previous_header_ns":
                    int(
                        h[
                            index
                        ]
                    ),
                "current_header_ns":
                    int(
                        h[
                            index + 1
                        ]
                    ),
                "delta_ns":
                    int(
                        header_diff[
                            index
                        ]
                    ),
                "delta_ms":
                    float(
                        header_diff[
                            index
                        ]
                    )
                    / 1_000_000.0,
            }
        )

    largest_offsets = []

    for index in top_abs_indices(
        record_minus_header,
        TOP_K,
    ):
        index = int(
            index
        )

        largest_offsets.append(
            {
                "index":
                    index,
                "header_ns":
                    int(
                        h[
                            index
                        ]
                    ),
                "record_ns":
                    int(
                        r[
                            index
                        ]
                    ),
                "record_minus_header_ns":
                    int(
                        record_minus_header[
                            index
                        ]
                    ),
                "record_minus_header_ms":
                    float(
                        record_minus_header[
                            index
                        ]
                    )
                    / 1_000_000.0,
            }
        )

    return {
        "message_count":
            int(
                message_count
            ),
        "header_count":
            int(
                h.size
            ),
        "decode_error_count":
            int(
                decode_error_count
            ),
        "message_types":
            sorted(
                message_types
            ),
        "frame_ids":
            dict(
                sorted(
                    frame_ids.items()
                )
            ),
        "header_time": {
            "first_ns":
                int(
                    h[0]
                ),
            "last_ns":
                int(
                    h[-1]
                ),
            "min_ns":
                int(
                    h.min()
                ),
            "max_ns":
                int(
                    h.max()
                ),
            "duplicate_count":
                int(
                    np.count_nonzero(
                        header_diff == 0
                    )
                ),
            "reverse_count":
                int(
                    np.count_nonzero(
                        header_diff < 0
                    )
                ),
            "positive_interval_ms":
                summarize_ms(
                    positive_header
                ),
        },
        "record_time": {
            "first_ns":
                int(
                    r[0]
                ),
            "last_ns":
                int(
                    r[-1]
                ),
            "duplicate_count":
                int(
                    np.count_nonzero(
                        record_diff == 0
                    )
                ),
            "reverse_count":
                int(
                    np.count_nonzero(
                        record_diff < 0
                    )
                ),
            "positive_interval_ms":
                summarize_ms(
                    positive_record
                ),
        },
        "record_minus_header_ms":
            summarize_ms(
                record_minus_header
            ),
        "record_minus_header_sign_counts": {
            "negative":
                int(
                    np.count_nonzero(
                        record_minus_header < 0
                    )
                ),
            "zero":
                int(
                    np.count_nonzero(
                        record_minus_header == 0
                    )
                ),
            "positive":
                int(
                    np.count_nonzero(
                        record_minus_header > 0
                    )
                ),
        },
        "largest_header_intervals":
            largest_intervals,
        "largest_absolute_record_header_offsets":
            largest_offsets,
    }


def nearest_delta_ns(
    source: np.ndarray,
    target: np.ndarray,
):
    if (
        source.size == 0
        or target.size == 0
    ):
        return np.empty(
            0,
            dtype=np.int64,
        )

    target_sorted = np.sort(
        target
    )

    positions = np.searchsorted(
        target_sorted,
        source,
        side="left",
    )

    right_index = np.clip(
        positions,
        0,
        target_sorted.size - 1,
    )

    left_index = np.clip(
        positions - 1,
        0,
        target_sorted.size - 1,
    )

    right_delta = (
        target_sorted[
            right_index
        ]
        - source
    )

    left_delta = (
        target_sorted[
            left_index
        ]
        - source
    )

    choose_left = (
        np.abs(
            left_delta
        )
        <= np.abs(
            right_delta
        )
    )

    return np.where(
        choose_left,
        left_delta,
        right_delta,
    )


def pair_summary(
    source: np.ndarray,
    target: np.ndarray,
):
    delta = nearest_delta_ns(
        source,
        target,
    )

    if delta.size == 0:
        return {
            "count": 0,
            "signed_target_minus_source_ms": None,
            "absolute_delta_ms": None,
            "negative_signed_count": 0,
            "zero_signed_count": 0,
            "positive_signed_count": 0,
            "largest_absolute_deltas": [],
        }

    absolute = np.abs(
        delta
    )

    anomalies = []

    for index in top_abs_indices(
        delta,
        TOP_K,
    ):
        index = int(
            index
        )

        anomalies.append(
            {
                "source_index":
                    index,
                "source_header_ns":
                    int(
                        source[
                            index
                        ]
                    ),
                "nearest_target_minus_source_ns":
                    int(
                        delta[
                            index
                        ]
                    ),
                "absolute_delta_ns":
                    int(
                        absolute[
                            index
                        ]
                    ),
                "absolute_delta_ms":
                    float(
                        absolute[
                            index
                        ]
                    )
                    / 1_000_000.0,
            }
        )

    return {
        "count":
            int(
                delta.size
            ),
        "signed_target_minus_source_ms":
            summarize_ms(
                delta
            ),
        "absolute_delta_ms":
            summarize_ms(
                absolute
            ),
        "negative_signed_count":
            int(
                np.count_nonzero(
                    delta < 0
                )
            ),
        "zero_signed_count":
            int(
                np.count_nonzero(
                    delta == 0
                )
            ),
        "positive_signed_count":
            int(
                np.count_nonzero(
                    delta > 0
                )
            ),
        "largest_absolute_deltas":
            anomalies,
    }


def scan_trajectory(
    dataset_root: Path,
    trajectory_id: str,
    output_root: Path,
):
    bag_path = (
        dataset_root
        / "raw"
        / "rosbags"
        / f"{trajectory_id}.bag"
    )

    digest, sidecar = (
        read_checksum_sidecar(
            dataset_root,
            trajectory_id,
        )
    )

    output = (
        output_root
        / (
            trajectory_id
            + "_phase3_stream_timing_v1.json"
        )
    )

    data = {}

    for topic in TOPICS:
        data[
            topic
        ] = {
            "headers":
                array(
                    "q"
                ),
            "records":
                array(
                    "q"
                ),
            "frame_ids":
                Counter(),
            "message_types":
                set(),
            "message_count":
                0,
            "decode_error_count":
                0,
            "decode_error_examples":
                [],
        }

    print(
        f"[SCAN] {trajectory_id}: "
        f"{bag_path.stat().st_size} bytes",
        flush=True,
    )

    with AnyReader(
        [
            bag_path
        ]
    ) as reader:
        selected = [
            connection
            for connection
            in reader.connections
            if connection.topic
            in TOPICS
        ]

        available_topics = sorted(
            {
                connection.topic
                for connection
                in selected
            }
        )

        missing_topics = sorted(
            set(
                TOPICS
            )
            - set(
                available_topics
            )
        )

        print(
            f"[INFO] {trajectory_id}: "
            f"available={available_topics} "
            f"missing={missing_topics}",
            flush=True,
        )

        for (
            connection,
            record_ns,
            rawdata,
        ) in reader.messages(
            connections=selected
        ):
            topic = (
                connection.topic
            )

            bucket = data[
                topic
            ]

            bucket[
                "message_count"
            ] += 1

            bucket[
                "message_types"
            ].add(
                connection.msgtype
            )

            try:
                message = (
                    reader.deserialize(
                        rawdata,
                        connection.msgtype,
                    )
                )

                header = getattr(
                    message,
                    "header",
                )

                header_ns = (
                    stamp_to_ns(
                        header.stamp
                    )
                )

                frame_id = str(
                    getattr(
                        header,
                        "frame_id",
                        "",
                    )
                )

            except Exception as exc:
                bucket[
                    "decode_error_count"
                ] += 1

                if len(
                    bucket[
                        "decode_error_examples"
                    ]
                ) < 5:
                    bucket[
                        "decode_error_examples"
                    ].append(
                        {
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

            bucket[
                "headers"
            ].append(
                int(
                    header_ns
                )
            )

            bucket[
                "records"
            ].append(
                int(
                    record_ns
                )
            )

            bucket[
                "frame_ids"
            ][
                frame_id
            ] += 1

    stream_arrays = {}
    stream_payload = {}
    total_messages = 0
    total_decode_errors = 0

    for topic in TOPICS:
        bucket = data[
            topic
        ]

        headers = as_np(
            bucket[
                "headers"
            ]
        )

        stream_arrays[
            topic
        ] = headers

        total_messages += (
            bucket[
                "message_count"
            ]
        )

        total_decode_errors += (
            bucket[
                "decode_error_count"
            ]
        )

        stream_payload[
            topic
        ] = stream_summary(
            bucket[
                "headers"
            ],
            bucket[
                "records"
            ],
            bucket[
                "frame_ids"
            ],
            bucket[
                "message_types"
            ],
            bucket[
                "message_count"
            ],
            bucket[
                "decode_error_count"
            ],
        )

        stream_payload[
            topic
        ][
            "decode_error_examples"
        ] = bucket[
            "decode_error_examples"
        ]

    nonempty = [
        stream_arrays[
            topic
        ]
        for topic in TOPICS
        if stream_arrays[
            topic
        ].size
    ]

    if len(
        nonempty
    ) == len(
        TOPICS
    ):
        common_start = max(
            int(
                values.min()
            )
            for values
            in nonempty
        )

        common_end = min(
            int(
                values.max()
            )
            for values
            in nonempty
        )

        if (
            common_end
            < common_start
        ):
            common_start = None
            common_end = None

    else:
        common_start = None
        common_end = None

    common_payload = {
        "start_ns":
            common_start,
        "end_ns":
            common_end,
        "interpretation":
            "numeric_header_range_intersection_only",
        "synchronization_claim":
            False,
    }

    for topic in TOPICS:
        values = stream_arrays[
            topic
        ]

        if (
            common_start
            is None
            or values.size == 0
        ):
            before = None
            after = None
            outside = None
        else:
            before = int(
                np.count_nonzero(
                    values
                    < common_start
                )
            )

            after = int(
                np.count_nonzero(
                    values
                    > common_end
                )
            )

            outside = (
                before
                + after
            )

        stream_payload[
            topic
        ][
            "common_header_range_diagnostic"
        ] = {
            "samples_before":
                before,
            "samples_after":
                after,
            "samples_outside":
                outside,
            "sample_exclusion_rule":
                False,
        }

    pairs = {}

    for (
        source_topic,
        target_topic,
    ) in PAIRS:
        source = stream_arrays[
            source_topic
        ]

        target = stream_arrays[
            target_topic
        ]

        label = (
            source_topic
            + " -> nearest "
            + target_topic
        )

        all_stats = pair_summary(
            source,
            target,
        )

        if (
            common_start
            is not None
            and source.size
            and target.size
        ):
            source_mask = (
                (source >= common_start)
                & (source <= common_end)
            )

            target_mask = (
                (target >= common_start)
                & (target <= common_end)
            )

            common_stats = pair_summary(
                source[
                    source_mask
                ],
                target[
                    target_mask
                ],
            )
        else:
            common_stats = None

        pairs[
            label
        ] = {
            "source_topic":
                source_topic,
            "target_topic":
                target_topic,
            "all_source_samples":
                all_stats,
            "common_header_range_only":
                common_stats,
            "interpretation":
                "nearest_sample_characterization_only",
            "threshold_decision":
                None,
        }

    payload = {
        "schema":
            SCHEMA,
        "version":
            SCHEMA_VERSION,
        "trajectory_id":
            trajectory_id,
        "source": {
            "relative_path":
                bag_path
                .relative_to(
                    dataset_root
                )
                .as_posix(),
            "size_bytes":
                int(
                    bag_path.stat().st_size
                ),
            "recorded_sha256":
                digest,
            "checksum_sidecar":
                sidecar
                .relative_to(
                    dataset_root
                )
                .as_posix(),
            "raw_modified":
                False,
        },
        "reader": {
            "package":
                "rosbags",
            "version":
                version(
                    "rosbags"
                ),
            "message_deserialization":
                True,
            "targeted_stream_scan":
                True,
            "image_pixels_decoded":
                False,
            "pointcloud_points_interpreted":
                False,
            "scan_completed":
                True,
        },
        "policy": {
            "characterization_only":
                True,
            "measurement_time_basis":
                "sensor_header_stamp",
            "bag_record_time_role":
                "transport_provenance_diagnostic_only",
            "nearest_neighbor_is_sync_proof":
                False,
            "common_range_is_sync_proof":
                False,
            "automatic_sample_exclusion_rule_created":
                False,
            "fixed_time_offset_estimated":
                False,
            "fixed_time_offset_applied":
                False,
            "synchronization_tolerance_frozen":
                False,
            "synchronization_verified":
                False,
        },
        "available_target_topics":
            available_topics,
        "missing_target_topics":
            missing_topics,
        "total_target_messages":
            int(
                total_messages
            ),
        "total_decode_errors":
            int(
                total_decode_errors
            ),
        "common_header_range":
            common_payload,
        "streams":
            stream_payload,
        "pairs":
            pairs,
    }

    atomic_json_write(
        output,
        payload,
    )

    print(
        f"[DONE] {trajectory_id}: "
        f"messages={total_messages} "
        f"decode_errors={total_decode_errors}",
        flush=True,
    )

    return output


def parse_args():
    parser = ArgumentParser(
        description=(
            "Audit M2DGR sensor header timing for TRUST-ROBOT Phase 3. "
            "This scanner characterizes timing only; it does not verify "
            "synchronization or select tolerances."
        )
    )

    parser.add_argument(
        "--dataset-root",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--output-root",
        type=Path,
    )

    parser.add_argument(
        "--trajectory",
        action="append",
        dest="trajectories",
        help=(
            "Trajectory ID to scan. Repeat for multiple IDs. "
            "Omit to scan all discovered bags."
        ),
    )

    return parser.parse_args()


def main():
    args = parse_args()

    dataset_root = args.dataset_root.resolve()

    output_root = (
        args.output_root
        if args.output_root is not None
        else (
            dataset_root
            / "audit"
            / "phase3_staging"
            / "stream_timing_v1"
        )
    )

    if args.trajectories:
        trajectories = sorted(
            set(
                args.trajectories
            )
        )
    else:
        trajectories = sorted(
            path.stem
            for path in (
                dataset_root
                / "raw"
                / "rosbags"
            ).glob("*.bag")
        )

    if not trajectories:
        raise RuntimeError(
            "no M2DGR trajectories discovered"
        )

    output_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    print(
        f"[START] trajectories={len(trajectories)}",
        flush=True,
    )

    for position, trajectory_id in enumerate(
        trajectories,
        start=1,
    ):
        print(
            "",
            flush=True,
        )

        print(
            f"[PROGRESS] "
            f"{position}/{len(trajectories)} "
            f"{trajectory_id}",
            flush=True,
        )

        scan_trajectory(
            dataset_root,
            trajectory_id,
            output_root,
        )

    print(
        "",
        flush=True,
    )

    print(
        "[COMPLETE] timing characterization finished",
        flush=True,
    )

    print(
        "synchronization_verified = FALSE",
        flush=True,
    )

    print(
        "fixed_time_offset_estimated = FALSE",
        flush=True,
    )

    print(
        "synchronization_tolerance_frozen = FALSE",
        flush=True,
    )


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        raise
