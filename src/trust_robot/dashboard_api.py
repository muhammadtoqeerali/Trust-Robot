"""aiohttp read-only API for the TRUST-ROBOT dashboard."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Awaitable, Callable
import json

from aiohttp import web

from .dashboard_state import (
    API_VERSION,
    DashboardStateError,
    build_dashboard_snapshot,
    validate_dashboard_snapshot,
)


API_PREFIX = (
    f"/api/{API_VERSION}"
)

REPO_ROOT_KEY = web.AppKey(
    "repo_root",
    Path,
)

WEB_ROOT_KEY = web.AppKey(
    "web_root",
    Path,
)


@web.middleware
async def no_store_and_error_middleware(
    request: web.Request,
    handler: Callable[
        [web.Request],
        Awaitable[
            web.StreamResponse
        ],
    ],
) -> web.StreamResponse:
    try:
        response = await handler(
            request
        )
    except DashboardStateError as exc:
        response = web.json_response(
            {
                "error":
                    "dashboard_state_unavailable",

                "detail":
                    str(
                        exc
                    ),
            },
            status=503,
        )

    response.headers[
        "Cache-Control"
    ] = (
        "no-store, max-age=0"
    )

    response.headers[
        "X-Trust-Robot-Dashboard-Mode"
    ] = (
        "read-only"
    )

    response.headers[
        "X-Content-Type-Options"
    ] = "nosniff"

    response.headers[
        "X-Frame-Options"
    ] = "DENY"

    response.headers[
        "Referrer-Policy"
    ] = "no-referrer"

    response.headers[
        "Content-Security-Policy"
    ] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self'; "
        "connect-src 'self'; "
        "img-src 'self' data:; "
        "font-src 'self'; "
        "base-uri 'none'; "
        "frame-ancestors 'none'; "
        "form-action 'none'"
    )

    return response


def _snapshot(
    request: web.Request,
) -> dict[str, object]:
    snapshot = build_dashboard_snapshot(
        request.app[
            REPO_ROOT_KEY
        ]
    )

    validate_dashboard_snapshot(
        snapshot
    )

    return snapshot


async def index_handler(
    request: web.Request,
) -> web.StreamResponse:
    return web.FileResponse(
        request.app[
            WEB_ROOT_KEY
        ]
        / "index.html"
    )


async def styles_handler(
    request: web.Request,
) -> web.StreamResponse:
    return web.FileResponse(
        request.app[
            WEB_ROOT_KEY
        ]
        / "styles.css"
    )


async def app_js_handler(
    request: web.Request,
) -> web.StreamResponse:
    return web.FileResponse(
        request.app[
            WEB_ROOT_KEY
        ]
        / "app.js"
    )


async def health_handler(
    request: web.Request,
) -> web.Response:
    snapshot = _snapshot(
        request
    )

    return web.json_response(
        {
            "status":
                "ok",

            "api_version":
                API_VERSION,

            "read_only":
                True,

            "dashboard_mode":
                snapshot[
                    "overview"
                ][
                    "mode"
                ],

            "real_sensor_execution_available":
                False,
        }
    )


async def snapshot_handler(
    request: web.Request,
) -> web.Response:
    return web.json_response(
        _snapshot(
            request
        )
    )


async def events_handler(
    request: web.Request,
) -> web.Response:
    snapshot = _snapshot(
        request
    )

    transport_observed_at_utc = (
        datetime.now(
            timezone.utc
        )
        .isoformat(
            timespec="milliseconds"
        )
        .replace(
            "+00:00",
            "Z",
        )
    )

    payload = {
        "schema":
            "TRUST_ROBOT_DASHBOARD_LIVE_EVENT_V1",

        "transport_observed_at_utc":
            transport_observed_at_utc,

        "transport_time_is_sensor_measurement_time":
            False,

        "snapshot":
            snapshot,
    }

    body = (
        "retry: 5000\n"
        + "data: "
        + json.dumps(
            payload,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n\n"
    )

    return web.Response(
        text=body,
        content_type="text/event-stream",
        headers={
            "X-Trust-Robot-Event-Mode":
                "single-event-reconnect",

            "X-Accel-Buffering":
                "no",
        },
    )


def _section_handler(
    section: str,
) -> Callable[
    [web.Request],
    Awaitable[
        web.Response
    ],
]:
    async def handler(
        request: web.Request,
    ) -> web.Response:
        snapshot = _snapshot(
            request
        )

        return web.json_response(
            snapshot[
                section
            ]
        )

    return handler


def create_dashboard_app(
    repo_root: str | Path,
) -> web.Application:
    root = Path(
        repo_root
    ).resolve()

    # Fail before opening a listener if the repository state cannot be
    # represented without violating dashboard rules.
    snapshot = build_dashboard_snapshot(
        root
    )

    validate_dashboard_snapshot(
        snapshot
    )

    app = web.Application(
        middlewares=[
            no_store_and_error_middleware,
        ]
    )

    web_root = (
        root
        / "src/trust_robot/dashboard_web"
    )

    required_frontend_files = (
        web_root
        / "index.html",

        web_root
        / "styles.css",

        web_root
        / "app.js",
    )

    for frontend_file in required_frontend_files:
        if not frontend_file.is_file():
            raise DashboardStateError(
                f"required dashboard frontend file missing: {frontend_file}"
            )

    app[
        REPO_ROOT_KEY
    ] = root

    app[
        WEB_ROOT_KEY
    ] = web_root

    app.router.add_get(
        "/",
        index_handler,
    )

    app.router.add_get(
        "/assets/styles.css",
        styles_handler,
    )

    app.router.add_get(
        "/assets/app.js",
        app_js_handler,
    )

    app.router.add_get(
        f"{API_PREFIX}/health",
        health_handler,
    )

    app.router.add_get(
        f"{API_PREFIX}/snapshot",
        snapshot_handler,
    )

    app.router.add_get(
        f"{API_PREFIX}/events",
        events_handler,
    )

    for section in (
        "overview",
        "repository",
        "dataset",
        "replay",
        "features",
        "acquisition",
        "operations",
        "receipts",
        "health_supervision",
        "scientific_boundary",
        "dashboard_policy",
        "evidence",
        "capabilities",
    ):
        app.router.add_get(
            f"{API_PREFIX}/{section.replace('_', '-')}",
            _section_handler(
                section
            ),
        )

    return app


def live_route_contract(
) -> tuple[str, ...]:
    return (
        f"GET {API_PREFIX}/events",
    )


def frontend_route_contract(
) -> tuple[str, ...]:
    return (
        "GET /",
        "GET /assets/styles.css",
        "GET /assets/app.js",
    )


def route_contract(
) -> tuple[str, ...]:
    return (
        f"GET {API_PREFIX}/health",
        f"GET {API_PREFIX}/snapshot",
        f"GET {API_PREFIX}/overview",
        f"GET {API_PREFIX}/repository",
        f"GET {API_PREFIX}/dataset",
        f"GET {API_PREFIX}/replay",
        f"GET {API_PREFIX}/features",
        f"GET {API_PREFIX}/acquisition",
        f"GET {API_PREFIX}/operations",
        f"GET {API_PREFIX}/receipts",
        f"GET {API_PREFIX}/health-supervision",
        f"GET {API_PREFIX}/scientific-boundary",
        f"GET {API_PREFIX}/dashboard-policy",
        f"GET {API_PREFIX}/evidence",
        f"GET {API_PREFIX}/capabilities",
    )
