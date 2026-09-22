#!/usr/bin/env python3

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import argparse
import json

from rosbags.highlevel import AnyReader

from trust_robot.corruption import (
    CorruptionSpec,
    apply_corruption,
)
from trust_robot.lidar_corruption_adapter import (
    adapt_m2dgr_velodyne_messages,
)
from trust_robot.lidar_corruption_estimator import (
    run_paired_frozen_lidar_registration,
)
from trust_robot.lidar_frontend import (
    EXPECTED_MSGTYPE,
    EXPECTED_TOPIC,
)


def canonical_sha(
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
        if path.read_text(
            encoding="utf-8"
        ) != content:
            raise RuntimeError(
                f"immutable output differs: {path}"
            )

        return

    temporary = path.with_suffix(
        path.suffix
        + ".tmp"
    )

    if temporary.exists():
        raise RuntimeError(
            f"stale temporary output exists: {temporary}"
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
        "--gap-config",
        required=True,
    )

    parser.add_argument(
        "--execution-config",
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

    gap_path = Path(
        args.gap_config
    )

    execution_path = Path(
        args.execution_config
    )

    output_dir = Path(
        args.output_dir
    )

    gap = json.loads(
        gap_path.read_text(
            encoding="utf-8"
        )
    )

    execution = json.loads(
        execution_path.read_text(
            encoding="utf-8"
        )
    )

    if canonical_sha(
        gap
    ) != gap[
        "content_sha256"
    ]:
        raise RuntimeError(
            "gap config content digest mismatch"
        )

    if canonical_sha(
        execution
    ) != execution[
        "content_sha256"
    ]:
        raise RuntimeError(
            "paired estimator config content digest mismatch"
        )

    if bag.name != "Circle_01.bag":
        raise RuntimeError(
            "paired estimator smoke is frozen to TRAIN Circle_01"
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
                "expected exactly one Velodyne PointCloud2 connection"
            )

        for connection, _bag_time, rawdata in reader.messages(
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
            "could not read exact frozen three-event slice"
        )

    clean = adapt_m2dgr_velodyne_messages(
        messages
    ).stream

    pair = apply_corruption(
        clean,
        CorruptionSpec(
            **gap[
                "corruption_spec"
            ]
        ),
    )

    clean_before = pair.clean.fingerprint()
    corrupt_before = pair.corrupt.fingerprint()

    first = run_paired_frozen_lidar_registration(
        pair
    )

    second = run_paired_frozen_lidar_registration(
        pair
    )

    if first != second:
        raise RuntimeError(
            "paired frozen registration execution was not deterministic"
        )

    if pair.clean.fingerprint() != clean_before:
        raise RuntimeError(
            "clean stream mutated during estimator execution"
        )

    if pair.corrupt.fingerprint() != corrupt_before:
        raise RuntimeError(
            "corrupt stream mutated during estimator execution"
        )

    expected_topology = execution[
        "expected_path_topology"
    ]

    if (
        first[
            "path_topology"
        ][
            "clean_origin_pairs"
        ]
        != expected_topology[
            "clean_origin_pairs"
        ]
    ):
        raise RuntimeError(
            "clean estimator path topology differs from frozen contract"
        )

    if (
        first[
            "path_topology"
        ][
            "corrupt_origin_pairs"
        ]
        != expected_topology[
            "corrupt_origin_pairs"
        ]
    ):
        raise RuntimeError(
            "corrupt estimator path topology differs from frozen contract"
        )

    if not first[
        "path_topology"
    ][
        "registration_path_changed_by_corruption"
    ]:
        raise RuntimeError(
            "EVENT_GAP did not change registration path topology"
        )

    receipt = {
        "schema":
            "TRUST_ROBOT_PHASE3_LIDAR_PAIRED_ESTIMATOR_REGISTRATION_RECEIPT_V1",

        "schema_version":
            1,

        "status":
            "completed",

        "source": {
            "dataset_id":
                "M2DGR",

            "split":
                "train",

            "trajectory":
                "Circle_01",

            "topic":
                EXPECTED_TOPIC,

            "event_slice":
                "first_three_velodyne_messages_in_bag_order",
        },

        "corruption": {
            "family":
                "EVENT_GAP",

            "spec_id":
                pair.truths[
                    0
                ].spec.spec_id,

            "injection_id":
                pair.truths[
                    0
                ].injection_id,

            "clean_origin_indices":
                [
                    0,
                    1,
                    2,
                ],

            "corrupt_origin_indices":
                [
                    int(
                        value
                    )
                    for value
                    in pair.corrupt.origin_indices
                ],
        },

        "registration_execution":
            first,

        "determinism": {
            "paired_execution_repeated_exactly":
                True,

            "clean_stream_unchanged":
                True,

            "corrupt_stream_unchanged":
                True,
        },

        "interpretation": {
            "mechanical_estimator_input_path_proof":
                True,

            "localization_accuracy_comparison":
                False,

            "clean_corrupt_error_metric":
                None,

            "observed_output_may_modify_corruption_spec":
                False,

            "observed_output_may_select_future_severity":
                False,
        },

        "scientific_scope": {
            "real_train_data_used":
                True,

            "controlled_corruption_used":
                True,

            "frozen_phase2_registration_kernel_used":
                True,

            "reference_data_used":
                False,

            "confirmation_test_data_used":
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

            "accuracy_comparison_performed":
                False,

            "severity_selection_performed":
                False,

            "phase3_exit_evidence_satisfied":
                False,
        },
    }

    receipt[
        "content_sha256"
    ] = canonical_sha(
        receipt
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
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
        / "paired_registration_receipt.json",
        receipt_text,
    )

    immutable_write(
        output_dir
        / "SUCCESS",
        (
            "TRUST_ROBOT_PHASE3_LIDAR_PAIRED_ESTIMATOR_REGISTRATION_V1=PASS\n"
        ),
    )

    print(
        "clean_origin_pairs=",
        first[
            "path_topology"
        ][
            "clean_origin_pairs"
        ],
    )

    print(
        "corrupt_origin_pairs=",
        first[
            "path_topology"
        ][
            "corrupt_origin_pairs"
        ],
    )

    print(
        "clean_registration_count=",
        first[
            "clean"
        ][
            "increment_count"
        ],
    )

    print(
        "corrupt_registration_count=",
        first[
            "corrupt"
        ][
            "increment_count"
        ],
    )

    for branch in (
        "clean",
        "corrupt",
    ):
        for record in first[
            branch
        ][
            "records"
        ]:
            print(
                (
                    f"{branch}.origin_pair="
                    f"[{record['previous_clean_origin_index']}, "
                    f"{record['current_clean_origin_index']}]"
                )
            )

            print(
                (
                    f"{branch}.translation_m="
                    f"{record['previous_lidar_T_current_lidar']['translation_m']}"
                )
            )

            print(
                (
                    f"{branch}.quaternion_wxyz="
                    f"{record['previous_lidar_T_current_lidar']['quaternion_wxyz']}"
                )
            )

            print(
                (
                    f"{branch}.fixed_point_iterations="
                    f"{record['diagnostics']['fixed_point_iterations']}"
                )
            )

            print(
                (
                    f"{branch}.nearest_neighbor_rmse_m="
                    f"{record['diagnostics']['final_nearest_neighbor_rmse_m']}"
                )
            )

            print(
                (
                    f"{branch}.diagnostic_interpretation="
                    f"{record['diagnostics']['interpretation']}"
                )
            )

    print(
        "registration_path_changed_by_corruption=true"
    )

    print(
        "paired_execution_repeated_exactly=true"
    )

    print(
        "clean_stream_unchanged=true"
    )

    print(
        "corrupt_stream_unchanged=true"
    )

    print(
        "observed_output_may_modify_corruption_spec=false"
    )

    print(
        "observed_output_may_select_future_severity=false"
    )

    print(
        "clean_corrupt_error_metric_computed=false"
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
        "estimator_scoring_performed=false"
    )

    print(
        "paired_registration_receipt_content_sha256=",
        receipt[
            "content_sha256"
        ],
    )

    print(
        "TRUST_ROBOT_PHASE3_LIDAR_PAIRED_ESTIMATOR_REGISTRATION_V1=PASS"
    )


if __name__ == "__main__":
    main()
