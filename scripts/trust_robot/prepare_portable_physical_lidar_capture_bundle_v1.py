#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json

from trust_robot.portable_physical_lidar_capture_bundle import (
    PhysicalLidarInventoryDeclaration,
    build_bound_bundle,
    build_inventory_only_bundle,
    write_portable_bundle_directory,
)


def add_inventory_arguments(
    parser: argparse.ArgumentParser,
) -> None:
    parser.add_argument(
        "--bundle-directory",
        required=True,
    )

    parser.add_argument(
        "--session-id",
        required=True,
    )

    parser.add_argument(
        "--acquisition-host-id",
        required=True,
    )

    parser.add_argument(
        "--sensor-vendor",
        required=True,
    )

    parser.add_argument(
        "--sensor-model",
        required=True,
    )

    parser.add_argument(
        "--sensor-serial",
        required=True,
    )

    parser.add_argument(
        "--connection-path",
        required=True,
    )

    parser.add_argument(
        "--declared-condition",
        required=True,
    )


def inventory_from_args(
    args: argparse.Namespace,
) -> PhysicalLidarInventoryDeclaration:
    return PhysicalLidarInventoryDeclaration(
        acquisition_session_id=
            args.session_id,

        acquisition_host_id=
            args.acquisition_host_id,

        sensor_vendor=
            args.sensor_vendor,

        sensor_model=
            args.sensor_model,

        sensor_serial=
            args.sensor_serial,

        connection_path=
            args.connection_path,

        declared_condition=
            args.declared_condition,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Prepare a non-executing portable TRUST-ROBOT physical-LiDAR "
            "bundle. This command performs no network or sensor I/O."
        )
    )

    subparsers = parser.add_subparsers(
        dest="mode",
        required=True,
    )

    inventory_parser = (
        subparsers.add_parser(
            "inventory"
        )
    )

    add_inventory_arguments(
        inventory_parser
    )

    bind_parser = (
        subparsers.add_parser(
            "bind"
        )
    )

    add_inventory_arguments(
        bind_parser
    )

    bind_parser.add_argument(
        "--split",
        required=True,
    )

    bind_parser.add_argument(
        "--capture-interface",
        required=True,
    )

    bind_parser.add_argument(
        "--bind-ipv4",
        required=True,
    )

    bind_parser.add_argument(
        "--measurement-port",
        type=int,
        required=True,
    )

    bind_parser.add_argument(
        "--position-port",
        type=int,
        required=True,
    )

    bind_parser.add_argument(
        "--sensor-ipv4",
        required=True,
    )

    bind_parser.add_argument(
        "--duration-seconds",
        type=int,
        required=True,
    )

    bind_parser.add_argument(
        "--capture-output-root",
        required=True,
    )

    bind_parser.add_argument(
        "--http-port",
        type=int,
        required=True,
    )

    bind_parser.add_argument(
        "--http-connect-timeout-seconds",
        type=int,
        required=True,
    )

    bind_parser.add_argument(
        "--http-total-timeout-seconds",
        type=int,
        required=True,
    )

    bind_parser.add_argument(
        "--vlp32c-destination-ipv4",
        required=True,
    )

    bind_parser.add_argument(
        "--vlp32c-measurement-destination-port",
        type=int,
        required=True,
    )

    bind_parser.add_argument(
        "--vlp32c-position-destination-port",
        type=int,
        required=True,
    )

    bind_parser.add_argument(
        "--destination-configuration-verified",
        action="store_true",
    )

    bind_parser.add_argument(
        "--declared-before-execution",
        action="store_true",
    )

    args = parser.parse_args()

    inventory = inventory_from_args(
        args
    )

    if args.mode == "inventory":
        payload = (
            build_inventory_only_bundle(
                inventory
            )
        )

    else:
        payload = build_bound_bundle(
            inventory=
                inventory,

            split=
                args.split,

            capture_interface=
                args.capture_interface,

            bind_ipv4=
                args.bind_ipv4,

            measurement_udp_port=
                args.measurement_port,

            position_udp_port=
                args.position_port,

            sensor_ipv4=
                args.sensor_ipv4,

            capture_duration_seconds=
                args.duration_seconds,

            absolute_output_root=
                args.capture_output_root,

            http_port=
                args.http_port,

            http_connect_timeout_seconds=
                args.http_connect_timeout_seconds,

            http_total_timeout_seconds=
                args.http_total_timeout_seconds,

            vlp32c_destination_ipv4=
                args.vlp32c_destination_ipv4,

            vlp32c_measurement_destination_udp_port=
                args.vlp32c_measurement_destination_port,

            vlp32c_position_destination_udp_port=
                args.vlp32c_position_destination_port,

            vlp32c_destination_configuration_verified=
                args.destination_configuration_verified,

            declared_before_execution=
                args.declared_before_execution,
        )

    receipt = (
        write_portable_bundle_directory(
            bundle_directory=
                args.bundle_directory,

            payload=
                payload,
        )
    )

    print(
        json.dumps(
            receipt,
            indent=2,
            sort_keys=True,
        )
    )

    print(
        "TRUST_ROBOT_PORTABLE_PHYSICAL_LIDAR_CAPTURE_BUNDLE_PREPARATION_V1=PASS"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
