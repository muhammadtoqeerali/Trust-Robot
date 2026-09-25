"""SE4 one-shot HTTP raw-evidence executor.

This module implements the software execution path for the three frozen,
read-only VLP-32C HTTP evidence endpoints:

- /cgi/info.json
- /cgi/status.json
- /cgi/diag.json

The executor preserves response bodies and response-header output separately,
uses explicit engineering timeouts, publishes only into an already-created
fresh session directory, and never overwrites final artifacts.

There are two execution scopes:

1. loopback_test
   Software verification only. Requires an explicit loopback-test
   authorization and a loopback IPv4 address.

2. real_sensor
   Future physical execution. Requires explicit real-sensor execution
   authorization and a non-loopback sensor IPv4 address.

The repository resolution state does not grant real-sensor authorization.
"""

from __future__ import annotations

from hashlib import sha256
from ipaddress import IPv4Address, ip_address
from pathlib import Path
from typing import Mapping
import json
import os
import subprocess
import time


SCHEMA = (
    "TRUST_ROBOT_SE4_HTTP_EVIDENCE_EXECUTOR_RESOLUTION_V1"
)

SCHEMA_VERSION = 1

RESOLUTION_ID = (
    "trust_robot_se4_http_evidence_executor_resolution_v1"
)

EXECUTION_SCOPE_LOOPBACK = (
    "loopback_test"
)

EXECUTION_SCOPE_REAL_SENSOR = (
    "real_sensor"
)

ENDPOINTS = {
    "identity": {
        "path":
            "/cgi/info.json",

        "body_filename":
            "info.json",

        "headers_filename":
            "info.headers",
    },

    "status": {
        "path":
            "/cgi/status.json",

        "body_filename":
            "status.json",

        "headers_filename":
            "status.headers",
    },

    "diagnostic": {
        "path":
            "/cgi/diag.json",

        "body_filename":
            "diagnostic.json",

        "headers_filename":
            "diagnostic.headers",
    },
}

FROZEN_INPUT_SHA256 = {
    "SE4_runtime_binding_freeze":
        "28bf88aa87f6c527f16fa3144e94d70fadc64379f0e90529f04c46e7364d6afc",

    "SE4_runtime_binding_config":
        "ff293fa62bab7d1ce72f8a2f130130c5b66826c74a8d1853a7f1ac63e9fc14e7",

    "phase5_live_acquisition_plan":
        "9988bf72a341a045831b2efe49d393f6886075ca179034ceecf4a191b4f8992d",

    "live_acquisition_plan_module":
        "196a88bde3f96c98985121c13444190984c1622dceb648817ead8ef3320956a6",

    "phase5_live_executor_safety":
        "9370692895bc156552a664b23fd84445a32a3b20ead8c1d1c4f495c31e6dca6a",

    "live_executor_safety_module":
        "6dcb292355ba17ec8a563b1183e0279b40559ec0467dd8dc9fbba5a2e674e26a",

    "phase5_acquisition_session_provenance":
        "08b691bcc0eb3db7d9b0059608f8134b7b6086f526b6c11e64cf03ac3efa763b",

    "acquisition_session_provenance_module":
        "ff79ccf0ea68355028ef9fd3fa76f431479a9a7f2fba6b60a34d75bd9bf3cf20",
}


class SE4HTTPEvidenceExecutorError(
    RuntimeError
):
    """Raised when HTTP evidence execution or validation fails."""


def _canonical_json(
    value: object,
) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def content_sha256(
    payload: Mapping[str, object],
) -> str:
    body = dict(
        payload
    )

    body.pop(
        "content_sha256",
        None,
    )

    return sha256(
        _canonical_json(
            body
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def _file_sha256(
    path: Path,
) -> str:
    hasher = sha256()

    with path.open(
        "rb"
    ) as handle:
        for chunk in iter(
            lambda: handle.read(
                1024 * 1024
            ),
            b"",
        ):
            hasher.update(
                chunk
            )

    return hasher.hexdigest()


def _positive_exact_int(
    value: object,
    *,
    name: str,
) -> int:
    if type(
        value
    ) is not int:
        raise SE4HTTPEvidenceExecutorError(
            f"{name} must be an exact int"
        )

    if value < 1:
        raise SE4HTTPEvidenceExecutorError(
            f"{name} must be positive"
        )

    return value


def _port(
    value: object,
) -> int:
    if type(
        value
    ) is not int:
        raise SE4HTTPEvidenceExecutorError(
            "http_port must be an exact int"
        )

    if value < 1 or value > 65535:
        raise SE4HTTPEvidenceExecutorError(
            "http_port must be in 1..65535"
        )

    return value


def _ipv4(
    value: object,
) -> IPv4Address:
    if not isinstance(
        value,
        str,
    ) or not value:
        raise SE4HTTPEvidenceExecutorError(
            "sensor_ipv4 must be a non-empty IPv4 string"
        )

    try:
        parsed = ip_address(
            value
        )
    except ValueError as exc:
        raise SE4HTTPEvidenceExecutorError(
            "sensor_ipv4 must be valid IPv4"
        ) from exc

    if not isinstance(
        parsed,
        IPv4Address,
    ):
        raise SE4HTTPEvidenceExecutorError(
            "sensor_ipv4 must be IPv4"
        )

    return parsed


def _session_directory(
    value: object,
) -> Path:
    if not isinstance(
        value,
        (
            str,
            os.PathLike,
        ),
    ):
        raise SE4HTTPEvidenceExecutorError(
            "session_directory must be a path"
        )

    path = Path(
        value
    )

    if not path.is_absolute():
        raise SE4HTTPEvidenceExecutorError(
            "session_directory must be absolute"
        )

    if not path.exists():
        raise SE4HTTPEvidenceExecutorError(
            "session_directory must already exist"
        )

    if not path.is_dir():
        raise SE4HTTPEvidenceExecutorError(
            "session_directory must be a directory"
        )

    return path


def _fsync_file(
    path: Path,
) -> None:
    with path.open(
        "rb"
    ) as handle:
        os.fsync(
            handle.fileno()
        )


def _fsync_directory(
    path: Path,
) -> None:
    fd = os.open(
        str(
            path
        ),
        os.O_RDONLY,
    )

    try:
        os.fsync(
            fd
        )
    finally:
        os.close(
            fd
        )


def _cleanup(
    paths: tuple[Path, ...],
) -> None:
    for path in paths:
        try:
            path.unlink()
        except FileNotFoundError:
            pass


def build_http_evidence_executor_resolution(
) -> dict[str, object]:
    """Build the promoted-software state without real-sensor authorization."""

    payload: dict[str, object] = {
        "schema":
            SCHEMA,

        "schema_version":
            SCHEMA_VERSION,

        "resolution_id":
            RESOLUTION_ID,

        "stage_context": {
            "stage_id":
                "SE4",

            "sub_frontier":
                "HTTP_evidence_execution_software",

            "SE4_complete":
                False,

            "SE4_training_authorized":
                False,
        },

        "HTTP_execution_software": {
            "implemented":
                True,

            "implementation_transport":
                "curl_subprocess",

            "shell_execution":
                False,

            "read_only_GET_only":
                True,

            "redirect_following_enabled":
                False,

            "endpoint_allowlist_enforced":
                True,

            "explicit_connect_timeout_required":
                True,

            "explicit_total_timeout_required":
                True,

            "explicit_http_port_required":
                True,

            "protocol_supplies_http_port_default":
                False,

            "body_and_headers_preserved_separately":
                True,

            "same_directory_partial_files":
                True,

            "existing_final_overwrite_allowed":
                False,

            "file_fsync_before_publish":
                True,

            "directory_fsync_after_publish":
                True,

            "pre_post_publish_SHA256_equality_required":
                True,
        },

        "endpoints": {
            key:
                dict(
                    value
                )
            for key, value
            in ENDPOINTS.items()
        },

        "verification_state": {
            "loopback_execution_verified":
                True,

            "real_sensor_execution_verified":
                False,

            "real_sensor_network_IO_executed":
                False,

            "real_sensor_contact_executed":
                False,

            "real_device_identity_receipt_count":
                0,

            "raw_real_sensor_HTTP_artifact_count":
                0,
        },

        "authorization_boundary": {
            "loopback_test_requires_explicit_authorization":
                True,

            "real_sensor_execution_requires_explicit_authorization":
                True,

            "real_sensor_execution_authorized":
                False,

            "runtime_binding_required_before_real_sensor_execution":
                True,

            "HTTP_implementation_is_execution_authorization":
                False,
        },

        "scientific_boundary": {
            "HTTP_response_is_physical_health_truth":
                False,

            "HTTP_status_is_health_label":
                False,

            "HTTP_diagnostic_is_health_label":
                False,

            "HTTP_identity_is_baseline_nominality":
                False,

            "HTTP_timeout_is_sensor_timing_tolerance":
                False,

            "HTTP_receive_time_is_physical_measurement_time":
                False,

            "HTTP_execution_establishes_interval_binding":
                False,

            "accepted_baseline_nominality_source_count":
                0,

            "accepted_health_supervision_source_count":
                0,

            "real_health_label_count":
                0,

            "reference_data_used":
                False,

            "ATE_RPE_computed":
                False,

            "validation_access":
                False,

            "confirmation_access":
                False,
        },

        "transition_policy": {
            "HTTP_execution_software_implemented":
                True,

            "loopback_HTTP_execution_verified":
                True,

            "real_runtime_values_bound":
                False,

            "real_sensor_execution_authorized":
                False,

            "source_acceptance_authorized":
                False,

            "health_label_generation_authorized":
                False,

            "SE4_complete":
                False,

            "SE4_training_authorized":
                False,

            "SE5_may_proceed":
                False,

            "validation_remains_closed":
                True,

            "confirmation_remains_closed":
                True,

            "next_required_event":
                (
                    "Create one real operator-supplied TRAIN runtime binding "
                    "and separately authorize a bounded real-sensor execution. "
                    "HTTP software implementation alone does not authorize "
                    "network access or create health supervision."
                ),
        },

        "frozen_input_sha256":
            dict(
                FROZEN_INPUT_SHA256
            ),
    }

    payload[
        "content_sha256"
    ] = content_sha256(
        payload
    )

    return payload


def validate_http_evidence_executor_resolution(
    payload: Mapping[str, object],
) -> Mapping[str, object]:
    if not isinstance(
        payload,
        Mapping,
    ):
        raise SE4HTTPEvidenceExecutorError(
            "resolution payload must be a mapping"
        )

    expected = (
        build_http_evidence_executor_resolution()
    )

    if dict(
        payload
    ) != expected:
        raise SE4HTTPEvidenceExecutorError(
            "HTTP executor resolution differs from frozen software state"
        )

    return payload


def execute_one_shot_http_evidence_read(
    *,
    evidence_kind: str,
    sensor_ipv4: str,
    session_directory: str | os.PathLike[str],
    http_connect_timeout_seconds: int,
    http_total_timeout_seconds: int,
    execution_scope: str,
    real_sensor_execution_authorized: bool = False,
    loopback_test_authorized: bool = False,
    http_port: int | None = None,
    curl_path: str = "/usr/bin/curl",
) -> dict[str, object]:
    """Execute one authorized GET and atomically publish body and headers.

    A loopback test is software verification only.
    A real-sensor request requires a separate explicit authorization.

    ``http_port`` has no physical default. ``None`` is only a fail-closed
    sentinel and is rejected before any network execution.
    """

    if evidence_kind not in ENDPOINTS:
        raise SE4HTTPEvidenceExecutorError(
            "evidence_kind must be identity, status or diagnostic"
        )

    connect_timeout = _positive_exact_int(
        http_connect_timeout_seconds,
        name="http_connect_timeout_seconds",
    )

    total_timeout = _positive_exact_int(
        http_total_timeout_seconds,
        name="http_total_timeout_seconds",
    )

    if total_timeout < connect_timeout:
        raise SE4HTTPEvidenceExecutorError(
            "http_total_timeout_seconds must be >= "
            "http_connect_timeout_seconds"
        )

    port = _port(
        http_port
    )

    parsed_ip = _ipv4(
        sensor_ipv4
    )

    if execution_scope == EXECUTION_SCOPE_LOOPBACK:
        if not parsed_ip.is_loopback:
            raise SE4HTTPEvidenceExecutorError(
                "loopback_test execution requires a loopback IPv4 address"
            )

        if type(
            loopback_test_authorized
        ) is not bool or not loopback_test_authorized:
            raise SE4HTTPEvidenceExecutorError(
                "loopback_test execution requires explicit authorization"
            )

        if real_sensor_execution_authorized:
            raise SE4HTTPEvidenceExecutorError(
                "loopback_test may not assert real-sensor authorization"
            )

    elif execution_scope == EXECUTION_SCOPE_REAL_SENSOR:
        if (
            parsed_ip.is_loopback
            or parsed_ip.is_unspecified
            or parsed_ip.is_multicast
        ):
            raise SE4HTTPEvidenceExecutorError(
                "real_sensor execution requires a concrete non-loopback "
                "non-multicast IPv4 address"
            )

        if type(
            real_sensor_execution_authorized
        ) is not bool or not real_sensor_execution_authorized:
            raise SE4HTTPEvidenceExecutorError(
                "real_sensor HTTP execution requires explicit authorization"
            )

    else:
        raise SE4HTTPEvidenceExecutorError(
            "execution_scope must be loopback_test or real_sensor"
        )

    session = _session_directory(
        session_directory
    )

    curl = Path(
        curl_path
    )

    if not curl.is_absolute():
        raise SE4HTTPEvidenceExecutorError(
            "curl_path must be absolute"
        )

    if not curl.exists():
        raise SE4HTTPEvidenceExecutorError(
            "curl executable does not exist"
        )

    if not os.access(
        curl,
        os.X_OK,
    ):
        raise SE4HTTPEvidenceExecutorError(
            "curl_path is not executable"
        )

    endpoint = ENDPOINTS[
        evidence_kind
    ]

    body_final = (
        session
        / endpoint[
            "body_filename"
        ]
    )

    headers_final = (
        session
        / endpoint[
            "headers_filename"
        ]
    )

    body_partial = (
        session
        / (
            "."
            + endpoint[
                "body_filename"
            ]
            + ".partial"
        )
    )

    headers_partial = (
        session
        / (
            "."
            + endpoint[
                "headers_filename"
            ]
            + ".partial"
        )
    )

    for final in (
        body_final,
        headers_final,
    ):
        if final.exists():
            raise SE4HTTPEvidenceExecutorError(
                f"refusing to overwrite existing final artifact: {final}"
            )

    for partial in (
        body_partial,
        headers_partial,
    ):
        if partial.exists():
            raise SE4HTTPEvidenceExecutorError(
                f"refusing pre-existing partial artifact: {partial}"
            )

    url = (
        f"http://{parsed_ip}"
        + (
            ""
            if port == 80
            else f":{port}"
        )
        + endpoint[
            "path"
        ]
    )

    argv = [
        str(
            curl
        ),
        "--silent",
        "--show-error",
        "--fail-with-body",
        "--request",
        "GET",
        "--connect-timeout",
        str(
            connect_timeout
        ),
        "--max-time",
        str(
            total_timeout
        ),
        "--dump-header",
        str(
            headers_partial
        ),
        "--output",
        str(
            body_partial
        ),
        url,
    ]

    host_start_wall_ns = time.time_ns()
    host_start_monotonic_ns = time.monotonic_ns()

    try:
        completed = subprocess.run(
            argv,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            shell=False,
        )
    except OSError as exc:
        _cleanup(
            (
                body_partial,
                headers_partial,
            )
        )

        raise SE4HTTPEvidenceExecutorError(
            "failed to start curl"
        ) from exc

    host_end_monotonic_ns = time.monotonic_ns()
    host_end_wall_ns = time.time_ns()

    if completed.returncode != 0:
        stderr_text = completed.stderr.decode(
            "utf-8",
            errors="replace",
        )

        _cleanup(
            (
                body_partial,
                headers_partial,
            )
        )

        raise SE4HTTPEvidenceExecutorError(
            "curl HTTP read failed with return code "
            f"{completed.returncode}: {stderr_text.strip()}"
        )

    for partial, label in (
        (
            body_partial,
            "body",
        ),
        (
            headers_partial,
            "headers",
        ),
    ):
        if not partial.is_file():
            _cleanup(
                (
                    body_partial,
                    headers_partial,
                )
            )

            raise SE4HTTPEvidenceExecutorError(
                f"curl did not produce {label} artifact"
            )

        if partial.stat().st_size < 1:
            _cleanup(
                (
                    body_partial,
                    headers_partial,
                )
            )

            raise SE4HTTPEvidenceExecutorError(
                f"curl produced empty {label} artifact"
            )

    body_sha_before = _file_sha256(
        body_partial
    )

    headers_sha_before = _file_sha256(
        headers_partial
    )

    body_bytes = body_partial.stat().st_size
    headers_bytes = headers_partial.stat().st_size

    try:
        _fsync_file(
            body_partial
        )

        _fsync_file(
            headers_partial
        )

        os.replace(
            body_partial,
            body_final,
        )

        os.replace(
            headers_partial,
            headers_final,
        )

        _fsync_directory(
            session
        )
    except Exception:
        _cleanup(
            (
                body_partial,
                headers_partial,
            )
        )
        raise

    body_sha_after = _file_sha256(
        body_final
    )

    headers_sha_after = _file_sha256(
        headers_final
    )

    if body_sha_before != body_sha_after:
        raise SE4HTTPEvidenceExecutorError(
            "body SHA-256 changed across publication"
        )

    if headers_sha_before != headers_sha_after:
        raise SE4HTTPEvidenceExecutorError(
            "headers SHA-256 changed across publication"
        )

    receipt: dict[str, object] = {
        "schema":
            "TRUST_ROBOT_SE4_HTTP_EVIDENCE_EXECUTION_RECEIPT_V1",

        "evidence_kind":
            evidence_kind,

        "execution_scope":
            execution_scope,

        "endpoint_path":
            endpoint[
                "path"
            ],

        "sensor_ipv4":
            str(
                parsed_ip
            ),

        "http_port":
            port,

        "request_method":
            "GET",

        "curl_return_code":
            completed.returncode,

        "body_filename":
            body_final.name,

        "headers_filename":
            headers_final.name,

        "body_sha256":
            body_sha_after,

        "headers_sha256":
            headers_sha_after,

        "body_byte_count":
            body_bytes,

        "headers_byte_count":
            headers_bytes,

        "host_request_start_wall_ns":
            host_start_wall_ns,

        "host_request_end_wall_ns":
            host_end_wall_ns,

        "host_request_start_monotonic_ns":
            host_start_monotonic_ns,

        "host_request_end_monotonic_ns":
            host_end_monotonic_ns,

        "host_times_transport_provenance_only":
            True,

        "physical_measurement_time_established":
            False,

        "sensor_health_inferred":
            False,

        "health_label_generated":
            False,

        "interval_binding_established":
            False,

        "real_sensor_execution_authorized":
            (
                execution_scope
                == EXECUTION_SCOPE_REAL_SENSOR
                and real_sensor_execution_authorized
            ),

        "loopback_test_authorized":
            (
                execution_scope
                == EXECUTION_SCOPE_LOOPBACK
                and loopback_test_authorized
            ),
    }

    receipt[
        "receipt_sha256"
    ] = sha256(
        _canonical_json(
            receipt
        ).encode(
            "utf-8"
        )
    ).hexdigest()

    return receipt


def assert_repository_real_sensor_execution_authorized(
    payload: Mapping[str, object],
) -> None:
    """Fail closed for the repository's current promoted resolution state."""

    validate_http_evidence_executor_resolution(
        payload
    )

    if payload[
        "authorization_boundary"
    ][
        "real_sensor_execution_authorized"
    ] is not True:
        raise SE4HTTPEvidenceExecutorError(
            "real-sensor HTTP execution remains blocked: the executor is "
            "implemented but no real TRAIN runtime binding and separate "
            "execution authorization have been accepted"
        )


def assert_health_supervision_available(
    payload: Mapping[str, object],
) -> None:
    """Fail closed: HTTP execution software is not health truth."""

    validate_http_evidence_executor_resolution(
        payload
    )

    science = payload[
        "scientific_boundary"
    ]

    if (
        science[
            "accepted_health_supervision_source_count"
        ] <= 0
        or science[
            "real_health_label_count"
        ] <= 0
    ):
        raise SE4HTTPEvidenceExecutorError(
            "health supervision remains unavailable: HTTP executor "
            "implementation does not accept a supervision source or create "
            "real health labels"
        )
