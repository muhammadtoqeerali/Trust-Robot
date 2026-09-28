#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path
import json

from aiohttp import web

from trust_robot.dashboard_api import (
    create_dashboard_app,
    route_contract,
)

from trust_robot.dashboard_state import (
    build_dashboard_snapshot,
    validate_dashboard_snapshot,
)


LOOPBACK_HOSTS = {
    "127.0.0.1",
    "localhost",
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run the TRUST-ROBOT UI1 read-only dashboard API. "
            "UI1 is loopback-only and exposes no real sensor execution."
        )
    )

    parser.add_argument(
        "--repo-root",
        default=str(
            Path(
                __file__
            ).resolve().parents[2]
        ),
    )

    parser.add_argument(
        "--host",
        default="127.0.0.1",
    )

    parser.add_argument(
        "--port",
        type=int,
        default=8765,
    )

    parser.add_argument(
        "--print-snapshot",
        action="store_true",
    )

    parser.add_argument(
        "--print-routes",
        action="store_true",
    )

    args = parser.parse_args()

    repo_root = Path(
        args.repo_root
    ).resolve()

    if args.print_routes:
        for route in route_contract():
            print(
                route
            )

        return 0

    if args.print_snapshot:
        snapshot = build_dashboard_snapshot(
            repo_root
        )

        validate_dashboard_snapshot(
            snapshot
        )

        print(
            json.dumps(
                snapshot,
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
                allow_nan=False,
            )
        )

        return 0

    if args.host not in LOOPBACK_HOSTS:
        parser.error(
            "UI1 is loopback-only; non-loopback binding is intentionally blocked"
        )

    if not (
        1
        <= args.port
        <= 65535
    ):
        parser.error(
            "port must be in 1..65535"
        )

    app = create_dashboard_app(
        repo_root
    )

    print(
        "TRUST_ROBOT_UI1_DASHBOARD_API=STARTING"
    )

    print(
        f"dashboard_url=http://{args.host}:{args.port}"
    )

    print(
        "dashboard_mode=read-only"
    )

    print(
        "real_sensor_execution_available=false"
    )

    print(
        "real_sensor_contact_performed_by_dashboard=false"
    )

    web.run_app(
        app,
        host=args.host,
        port=args.port,
        print=None,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
