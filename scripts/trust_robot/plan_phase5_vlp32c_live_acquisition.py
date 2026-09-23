#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json

from trust_robot.baseline_nominality import (
    BaselineNominalitySplit,
)

from trust_robot.live_acquisition_plan import (
    Vlp32cLiveAcquisitionPlanCandidate,
)


def build_parser(
) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a non-executing VLP-32C raw-acquisition argv plan. "
            "This command performs no network or sensor operation."
        )
    )

    parser.add_argument(
        "--session-id",
        required=True,
    )

    parser.add_argument(
        "--split",
        required=True,
        choices=(
            "train",
            "validation",
        ),
    )

    parser.add_argument(
        "--sensor-ipv4",
        required=True,
    )

    parser.add_argument(
        "--capture-interface",
        required=True,
    )

    parser.add_argument(
        "--data-port",
        required=True,
        type=int,
    )

    parser.add_argument(
        "--telemetry-port",
        required=True,
        type=int,
    )

    parser.add_argument(
        "--duration-seconds",
        required=True,
        type=int,
    )

    parser.add_argument(
        "--output-directory",
        required=True,
    )

    return parser


def main(
) -> int:
    args = build_parser().parse_args()

    plan = Vlp32cLiveAcquisitionPlanCandidate(
        acquisition_session_id=
            args.session_id,

        split=
            BaselineNominalitySplit(
                args.split
            ),

        sensor_ipv4=
            args.sensor_ipv4,

        capture_interface=
            args.capture_interface,

        data_udp_port=
            args.data_port,

        telemetry_udp_port=
            args.telemetry_port,

        capture_duration_seconds=
            args.duration_seconds,

        output_directory=
            args.output_directory,
    )

    print(
        json.dumps(
            plan.to_dict(),
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
