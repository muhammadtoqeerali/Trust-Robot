from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Awaitable, Callable
import json
import os

from fastapi import (
    FastAPI,
    Request,
)
from fastapi.responses import (
    FileResponse,
    JSONResponse,
    Response,
)
from fastapi.staticfiles import StaticFiles


ROOT = Path(
    __file__
).resolve().parent

WEB_ROOT = (
    ROOT
    / "src/trust_robot/dashboard_web"
)

SNAPSHOT_PATH = (
    ROOT
    / "deploy/vercel/dashboard_snapshot_v1.json"
)

API_PREFIX = "/api/v1"

SECTION_ROUTES = {
    "overview":
        "overview",

    "repository":
        "repository",

    "dataset":
        "dataset",

    "replay":
        "replay",

    "features":
        "features",

    "acquisition":
        "acquisition",

    "operations":
        "operations",

    "receipts":
        "receipts",

    "health-supervision":
        "health_supervision",

    "scientific-boundary":
        "scientific_boundary",

    "dashboard-policy":
        "dashboard_policy",

    "evidence":
        "evidence",

    "capabilities":
        "capabilities",
}


def _canonical_json(
    payload: Any,
) -> str:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _load_base_snapshot(
) -> dict[str, Any]:
    payload = json.loads(
        SNAPSHOT_PATH.read_text(
            encoding="utf-8"
        )
    )

    if payload.get(
        "read_only"
    ) is not True:
        raise RuntimeError(
            "deployment snapshot is not read-only"
        )

    if payload.get(
        "overview",
        {},
    ).get(
        "mode"
    ) != "software_only":
        raise RuntimeError(
            "deployment snapshot is not software-only"
        )

    return payload


BASE_SNAPSHOT = _load_base_snapshot()


def deployment_snapshot(
) -> dict[str, Any]:
    payload = deepcopy(
        BASE_SNAPSHOT
    )

    repository = payload[
        "repository"
    ]

    runtime_head = os.getenv(
        "VERCEL_GIT_COMMIT_SHA"
    )

    runtime_branch = os.getenv(
        "VERCEL_GIT_COMMIT_REF"
    )

    if runtime_head:
        repository[
            "head"
        ] = runtime_head

    if runtime_branch:
        repository[
            "branch"
        ] = runtime_branch

    repository[
        "tree"
    ] = None

    repository[
        "worktree_clean"
    ] = None

    repository[
        "deployment_metadata_source"
    ] = "vercel_runtime_environment"

    deployment = payload[
        "deployment"
    ]

    deployment[
        "runtime_commit_available"
    ] = bool(
        runtime_head
    )

    deployment[
        "runtime_branch_available"
    ] = bool(
        runtime_branch
    )

    deployment[
        "production_environment"
    ] = (
        os.getenv(
            "VERCEL_ENV"
        )
        == "production"
    )

    payload.pop(
        "content_sha256",
        None,
    )

    payload[
        "content_sha256"
    ] = sha256(
        _canonical_json(
            payload
        ).encode(
            "utf-8"
        )
    ).hexdigest()

    return payload


app = FastAPI(
    title="TRUST-ROBOT Dashboard",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


@app.middleware(
    "http"
)
async def dashboard_security_headers(
    request: Request,
    call_next: Callable[
        [Request],
        Awaitable[
            Response
        ],
    ],
) -> Response:
    response = await call_next(
        request
    )

    response.headers[
        "Cache-Control"
    ] = "no-store, max-age=0"

    response.headers[
        "X-Trust-Robot-Dashboard-Mode"
    ] = "read-only"

    response.headers[
        "X-Trust-Robot-Deployment-Platform"
    ] = "vercel"

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


@app.get(
    "/",
    include_in_schema=False,
)
async def dashboard_index(
) -> FileResponse:
    return FileResponse(
        WEB_ROOT
        / "index.html"
    )


@app.get(
    API_PREFIX,
)
async def api_root(
) -> JSONResponse:
    return JSONResponse(
        {
            "schema":
                "TRUST_ROBOT_DASHBOARD_VERCEL_API_V1",

            "api_version":
                "v1",

            "read_only":
                True,

            "mode":
                "software_only",

            "platform":
                "vercel",
        }
    )


@app.get(
    f"{API_PREFIX}/health",
)
async def health(
) -> JSONResponse:
    return JSONResponse(
        {
            "ok":
                True,

            "read_only":
                True,

            "mode":
                "software_only",

            "platform":
                "vercel",
        }
    )


@app.get(
    f"{API_PREFIX}/snapshot",
)
async def snapshot(
) -> JSONResponse:
    return JSONResponse(
        deployment_snapshot()
    )


@app.get(
    f"{API_PREFIX}/events",
)
async def events(
) -> Response:
    observed_at = (
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
            observed_at,

        "transport_time_is_sensor_measurement_time":
            False,

        "snapshot":
            deployment_snapshot(),
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

    return Response(
        content=body,
        media_type="text/event-stream",
        headers={
            "X-Trust-Robot-Event-Mode":
                "single-event-reconnect",
        },
    )


def _make_section_handler(
    section_key: str,
):
    async def handler(
    ) -> JSONResponse:
        snapshot_payload = (
            deployment_snapshot()
        )

        return JSONResponse(
            snapshot_payload[
                section_key
            ]
        )

    return handler


for route_name, section_key in SECTION_ROUTES.items():
    app.add_api_route(
        f"{API_PREFIX}/{route_name}",
        _make_section_handler(
            section_key
        ),
        methods=[
            "GET"
        ],
        include_in_schema=False,
    )


app.mount(
    "/assets",
    StaticFiles(
        directory=str(
            WEB_ROOT
        ),
        html=False,
        check_dir=True,
    ),
    name="dashboard-assets",
)
