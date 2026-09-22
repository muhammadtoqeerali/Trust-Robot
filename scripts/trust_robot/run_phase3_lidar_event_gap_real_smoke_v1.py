#!/usr/bin/env python3

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import argparse
import json

import numpy as np
from rosbags.highlevel import AnyReader

from trust_robot.corruption import (
    CorruptionSpec,
    apply_corruption,
    build_pair_manifest,
)
from trust_robot.lidar_corruption_adapter import (
    adapt_m2dgr_velodyne_messages,
    validate_m2dgr_velodyne_clean_adapter_receipt,
)
from trust_robot.lidar_frontend import (
    EXPECTED_MSGTYPE,
    EXPECTED_TOPIC,
)


def canonical_content_sha256(
    payload,
):
    value = dict(
        payload
    )

    value.pop(
        "content_sha256",
        None,
    )

    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode(
        "utf-8"
    )

    return sha256(
        raw
    ).hexdigest()


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


def raw_pointcloud_sha256(
    message,
):
    raw = memoryview(
        message.data
    ).cast(
        "B"
    )

    return sha256(
        raw.tobytes()
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
        "--bag",
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


def main():
    args = parse_args()

    bag = Path(
        args.bag
    )

    config_path = Path(
        args.config
    )

    output_dir = Path(
        args.output_dir
    )

    config = json.loads(
        config_path.read_text(
            encoding="utf-8"
        )
    )

    stored_config_content_sha = config[
        "content_sha256"
    ]

    if (
        canonical_content_sha256(
            config
        )
        != stored_config_content_sha
    ):
        raise RuntimeError(
            "prospective corruption config content digest mismatch"
        )

    source = config[
        "source"
    ]

    if bag.name != (
        source[
            "trajectory"
        ]
        + ".bag"
    ):
        raise RuntimeError(
            "bag does not match prospectively frozen trajectory"
        )

    if source[
        "split"
    ] != "train":
        raise RuntimeError(
            "real corruption smoke is TRAIN-only"
        )

    messages = []

    with AnyReader(
        [
            bag
        ]
    ) as reader:
        connections = [
            connection
            for connection
            in reader.connections
            if (
                connection.topic
                == EXPECTED_TOPIC
                and connection.msgtype
                == EXPECTED_MSGTYPE
            )
        ]

        if len(
            connections
        ) != 1:
            raise RuntimeError(
                "expected exactly one frozen Velodyne connection"
            )

        for connection, _bag_stamp, rawdata in reader.messages(
            connections=connections
        ):
            messages.append(
                reader.deserialize(
                    rawdata,
                    connection.msgtype,
                )
            )

            if len(
                messages
            ) == 3:
                break

    if len(
        messages
    ) != 3:
        raise RuntimeError(
            "failed to read prospectively frozen three-event slice"
        )

    raw_hashes_before = [
        raw_pointcloud_sha256(
            message
        )
        for message
        in messages
    ]

    if raw_hashes_before != source[
        "expected_raw_pointcloud_data_sha256"
    ]:
        raise RuntimeError(
            "source PointCloud2 raw hashes differ from prospective config"
        )

    clean_first = adapt_m2dgr_velodyne_messages(
        messages
    )

    clean_second = adapt_m2dgr_velodyne_messages(
        messages
    )

    if (
        clean_first.stream.fingerprint()
        != clean_second.stream.fingerprint()
    ):
        raise RuntimeError(
            "clean adapter fingerprint was not deterministic"
        )

    if (
        clean_first.receipt_json
        != clean_second.receipt_json
    ):
        raise RuntimeError(
            "clean adapter receipt was not deterministic"
        )

    adapter_receipt = clean_first.receipt_dict()

    validate_m2dgr_velodyne_clean_adapter_receipt(
        adapter_receipt
    )

    observed_stamps = [
        int(
            value
        )
        for value
        in clean_first.stream.timestamps_ns
    ]

    if observed_stamps != source[
        "expected_header_stamps_ns"
    ]:
        raise RuntimeError(
            "source header stamps differ from prospective config"
        )

    spec = CorruptionSpec(
        **config[
            "corruption_spec"
        ]
    )

    clean_fingerprint_before = (
        clean_first.stream.fingerprint()
    )

    first_pair = apply_corruption(
        clean_first.stream,
        spec,
    )

    second_pair = apply_corruption(
        clean_second.stream,
        spec,
    )

    clean_fingerprint_after = (
        clean_first.stream.fingerprint()
    )

    if (
        clean_fingerprint_before
        != clean_fingerprint_after
    ):
        raise RuntimeError(
            "clean EventStream changed during corruption"
        )

    first_manifest = build_pair_manifest(
        first_pair
    )

    second_manifest = build_pair_manifest(
        second_pair
    )

    if first_manifest != second_manifest:
        raise RuntimeError(
            "real corruption pair manifest was not deterministic"
        )

    if (
        first_pair.corrupt.fingerprint()
        != second_pair.corrupt.fingerprint()
    ):
        raise RuntimeError(
            "corrupted EventStream fingerprint was not deterministic"
        )

    if first_pair.clean.n_events != 3:
        raise RuntimeError(
            "unexpected clean event count"
        )

    if first_pair.corrupt.n_events != 2:
        raise RuntimeError(
            "unexpected corrupt event count"
        )

    expected_origins = np.asarray(
        [
            0,
            2,
        ],
        dtype=np.int64,
    )

    np.testing.assert_array_equal(
        first_pair.corrupt.origin_indices,
        expected_origins,
    )

    np.testing.assert_array_equal(
        first_pair.corrupt.timestamps_ns,
        first_pair.clean.timestamps_ns[
            [
                0,
                2,
            ]
        ],
    )

    np.testing.assert_array_equal(
        first_pair.corrupt.payloads[
            0
        ],
        first_pair.clean.payloads[
            0
        ],
    )

    np.testing.assert_array_equal(
        first_pair.corrupt.payloads[
            1
        ],
        first_pair.clean.payloads[
            2
        ],
    )

    truth = first_pair.truths[
        0
    ]

    if truth.spec.family.value != "EVENT_GAP":
        raise RuntimeError(
            "unexpected corruption family"
        )

    if truth.affected_clean_start != 1:
        raise RuntimeError(
            "unexpected affected clean start"
        )

    if truth.affected_clean_end_exclusive != 2:
        raise RuntimeError(
            "unexpected affected clean end"
        )

    removed = truth.details[
        "clean_origin_indices_removed"
    ]

    if removed != [
        1
    ]:
        raise RuntimeError(
            "unexpected removed clean origin"
        )

    raw_hashes_after = [
        raw_pointcloud_sha256(
            message
        )
        for message
        in messages
    ]

    if raw_hashes_before != raw_hashes_after:
        raise RuntimeError(
            "source PointCloud2 bytes changed"
        )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    clean_receipt_text = clean_first.receipt_json

    pair_manifest_text = (
        json.dumps(
            first_manifest,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    )

    receipt = {
        "schema":
            "TRUST_ROBOT_PHASE3_LIDAR_EVENT_GAP_REAL_SMOKE_RECEIPT_V1",

        "schema_version":
            1,

        "status":
            "completed",

        "prospective_config": {
            "file_sha256":
                file_sha256(
                    config_path
                ),

            "content_sha256":
                stored_config_content_sha,
        },

        "source": {
            "dataset_id":
                source[
                    "dataset_id"
                ],

            "split":
                source[
                    "split"
                ],

            "trajectory":
                source[
                    "trajectory"
                ],

            "topic":
                source[
                    "topic"
                ],

            "event_count":
                3,

            "header_stamps_ns":
                observed_stamps,

            "raw_pointcloud_data_sha256":
                raw_hashes_before,
        },

        "clean": {
            "event_count":
                first_pair.clean.n_events,

            "eventstream_fingerprint_sha256":
                first_pair.clean.fingerprint(),

            "adapter_receipt_content_sha256":
                adapter_receipt[
                    "content_sha256"
                ],
        },

        "corrupt": {
            "family":
                "EVENT_GAP",

            "event_count":
                first_pair.corrupt.n_events,

            "eventstream_fingerprint_sha256":
                first_pair.corrupt.fingerprint(),

            "origin_indices":
                [
                    int(
                        value
                    )
                    for value
                    in first_pair.corrupt.origin_indices
                ],

            "timestamps_ns":
                [
                    int(
                        value
                    )
                    for value
                    in first_pair.corrupt.timestamps_ns
                ],
        },

        "truth": {
            "spec_id":
                truth.spec.spec_id,

            "injection_id":
                truth.injection_id,

            "affected_clean_start":
                truth.affected_clean_start,

            "affected_clean_end_exclusive":
                truth.affected_clean_end_exclusive,

            "removed_clean_origin_indices":
                removed,
        },

        "determinism": {
            "clean_adapter_repeated_exactly":
                True,

            "corruption_manifest_repeated_exactly":
                True,

            "corrupt_eventstream_repeated_exactly":
                True,

            "clean_stream_unchanged":
                True,

            "raw_source_bytes_unchanged":
                True,
        },

        "scientific_scope": {
            "real_train_data_used":
                True,

            "reference_data_used":
                False,

            "confirmation_test_data_used":
                False,

            "estimator_executed":
                False,

            "ground_truth_association_performed":
                False,

            "alignment_performed":
                False,

            "ate_computed":
                False,

            "rpe_computed":
                False,

            "trajectory_scoring_performed":
                False,

            "estimator_scoring_performed":
                False,

            "severity_selected":
                False,

            "attack_budget_selected":
                False,

            "physical_scan_timestamp_reference_verified":
                False,

            "deskew_performed":
                False,

            "phase3_exit_evidence_satisfied":
                False,
        },
    }

    receipt[
        "content_sha256"
    ] = canonical_content_sha256(
        receipt
    )

    receipt_text = (
        json.dumps(
            receipt,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    )

    immutable_write(
        output_dir
        / "clean_adapter_receipt.json",
        clean_receipt_text,
    )

    immutable_write(
        output_dir
        / "corruption_pair_manifest.json",
        pair_manifest_text,
    )

    immutable_write(
        output_dir
        / "smoke_receipt.json",
        receipt_text,
    )

    success_text = (
        "TRUST_ROBOT_PHASE3_LIDAR_EVENT_GAP_REAL_SMOKE_V1=PASS\n"
    )

    immutable_write(
        output_dir
        / "SUCCESS",
        success_text,
    )

    print(
        "source_header_stamps_ns=",
        observed_stamps,
    )

    print(
        "source_raw_pointcloud_data_sha256=",
        raw_hashes_before,
    )

    print(
        "clean_event_count=",
        first_pair.clean.n_events,
    )

    print(
        "corrupt_event_count=",
        first_pair.corrupt.n_events,
    )

    print(
        "surviving_clean_origin_indices=",
        [
            int(
                value
            )
            for value
            in first_pair.corrupt.origin_indices
        ],
    )

    print(
        "removed_clean_origin_indices=",
        removed,
    )

    print(
        "clean_eventstream_fingerprint_sha256=",
        first_pair.clean.fingerprint(),
    )

    print(
        "corrupt_eventstream_fingerprint_sha256=",
        first_pair.corrupt.fingerprint(),
    )

    print(
        "corruption_spec_id=",
        truth.spec.spec_id,
    )

    print(
        "corruption_injection_id=",
        truth.injection_id,
    )

    print(
        "smoke_receipt_content_sha256=",
        receipt[
            "content_sha256"
        ],
    )

    print(
        "raw_source_bytes_unchanged=true"
    )

    print(
        "clean_stream_unchanged=true"
    )

    print(
        "corruption_manifest_repeated_exactly=true"
    )

    print(
        "corrupt_eventstream_repeated_exactly=true"
    )

    print(
        "corruption_applied=true"
    )

    print(
        "corruption_family=EVENT_GAP"
    )

    print(
        "severity_selected=false"
    )

    print(
        "reference_data_used=false"
    )

    print(
        "confirmation_test_data_used=false"
    )

    print(
        "estimator_executed=false"
    )

    print(
        "ate_computed=false"
    )

    print(
        "rpe_computed=false"
    )

    print(
        "phase3_exit_evidence_satisfied=false"
    )

    print(
        "TRUST_ROBOT_PHASE3_LIDAR_EVENT_GAP_REAL_SMOKE_V1=PASS"
    )


if __name__ == "__main__":
    main()
