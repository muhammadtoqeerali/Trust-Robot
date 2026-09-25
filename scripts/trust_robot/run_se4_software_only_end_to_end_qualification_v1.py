#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json

from trust_robot.se4_software_only_end_to_end_qualification import (
    REPRESENTATIVE_TRAJECTORY,
    run_software_only_end_to_end_qualification,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run the TRUST-ROBOT software-only end-to-end qualification. "
            "No real network I/O or sensor contact is performed."
        )
    )

    parser.add_argument(
        "--dataset-root",
        required=True,
    )

    parser.add_argument(
        "--split-manifest",
        required=True,
    )

    parser.add_argument(
        "--output-root",
        required=True,
    )

    parser.add_argument(
        "--trajectory-id",
        default=REPRESENTATIVE_TRAJECTORY,
    )

    parser.add_argument(
        "--max-replay-messages",
        type=int,
        default=20000,
    )

    args = parser.parse_args()

    result = run_software_only_end_to_end_qualification(
        dataset_root=
            args.dataset_root,

        split_manifest=
            args.split_manifest,

        output_root=
            args.output_root,

        trajectory_id=
            args.trajectory_id,

        max_replay_messages=
            args.max_replay_messages,
    )

    receipt = result[
        "receipt"
    ]

    real_lane = receipt[
        "real_data_lane"
    ]

    live_lane = receipt[
        "synthetic_live_lane"
    ]

    print(
        "TRUST_ROBOT_SE4_SOFTWARE_ONLY_END_TO_END_QUALIFICATION_V1=PASS"
    )

    print(
        "trajectory_id="
        + real_lane[
            "trajectory_id"
        ]
    )

    print(
        "real_bag_path="
        + real_lane[
            "bag_path"
        ]
    )

    print(
        "real_bag_file_size_bytes="
        + str(
            real_lane[
                "bag_file_size_bytes"
            ]
        )
    )

    print(
        "bounded_replay_message_count="
        + str(
            real_lane[
                "bounded_replay_first_pass"
            ][
                "message_count"
            ]
        )
    )

    print(
        "bounded_replay_digest_sha256="
        + real_lane[
            "bounded_replay_first_pass"
        ][
            "reader_order_digest_sha256"
        ]
    )

    print(
        "bounded_replay_deterministic="
        + str(
            real_lane[
                "bounded_replay_deterministic"
            ]
        ).lower()
    )

    print(
        "real_feature_stream_count="
        + str(
            real_lane[
                "real_feature_demonstration"
            ][
                "stream_count"
            ]
        )
    )

    print(
        "synthetic_live_execution_order="
        + ",".join(
            live_lane[
                "execution_order"
            ]
        )
    )

    print(
        "real_network_IO_executed=false"
    )

    print(
        "real_sensor_contact=false"
    )

    print(
        "health_label_generated=false"
    )

    print(
        "SE4_training_execution_blocked=true"
    )

    print(
        "SE5_entry_blocked=true"
    )

    print(
        "qualification_receipt="
        + result[
            "receipt_path"
        ]
    )

    print(
        "qualification_receipt_file_sha256="
        + result[
            "receipt_file_sha256"
        ]
    )

    print(
        "qualification_receipt_content_sha256="
        + result[
            "receipt_content_sha256"
        ]
    )

    print(
        "outcome="
        + receipt[
            "outcome"
        ]
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
