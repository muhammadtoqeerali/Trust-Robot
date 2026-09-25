#!/usr/bin/env python3
"""Validate or explicitly execute one externally supplied SE4 real TRAIN session."""

from __future__ import annotations

import argparse
import json

from trust_robot.se4_real_train_execution_runner import (
    NETWORK_IO_ACKNOWLEDGEMENT,
    execute_real_session_from_files,
    validate_real_execution_inputs_from_files,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate externally supplied real TRAIN binding/authorization "
            "files. Network execution is disabled unless --execute-real and "
            "the exact acknowledgement are both supplied."
        )
    )

    parser.add_argument(
        "--runtime-binding-file",
        required=True,
    )

    parser.add_argument(
        "--execution-authorization-file",
        required=True,
    )

    parser.add_argument(
        "--authorization-record-file",
        required=True,
    )

    parser.add_argument(
        "--execute-real",
        action="store_true",
        help=(
            "Permit dispatch to the promoted real composite orchestrator "
            "after all file validation succeeds."
        ),
    )

    parser.add_argument(
        "--network-io-acknowledgement",
        default=None,
        help=(
            "Required only with --execute-real. Exact value: "
            + NETWORK_IO_ACKNOWLEDGEMENT
        ),
    )

    return parser


def main() -> int:
    args = build_parser().parse_args()

    if not args.execute_real:
        result = validate_real_execution_inputs_from_files(
            runtime_binding_file=
                args.runtime_binding_file,

            execution_authorization_file=
                args.execution_authorization_file,

            authorization_record_file=
                args.authorization_record_file,
        )

        print(
            json.dumps(
                {
                    "mode":
                        "validation_only",

                    "network_IO_executed":
                        False,

                    "sensor_contact_executed":
                        False,

                    "input_validation":
                        result[
                            "input_validation"
                        ],
                },
                indent=2,
                sort_keys=True,
            )
        )

        return 0

    result = execute_real_session_from_files(
        runtime_binding_file=
            args.runtime_binding_file,

        execution_authorization_file=
            args.execution_authorization_file,

        authorization_record_file=
            args.authorization_record_file,

        execute_real=
            True,

        network_io_acknowledgement=
            args.network_io_acknowledgement,
    )

    print(
        json.dumps(
            {
                "mode":
                    "real_execution",

                "result":
                    result,
            },
            indent=2,
            sort_keys=True,
            default=str,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
