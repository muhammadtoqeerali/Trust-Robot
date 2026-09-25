"""SE4 composite real-TRAIN live-session orchestrator.

The orchestrator composes the already-frozen components without weakening
their scientific boundaries:

1. validate one V2 TRAIN runtime binding;
2. validate one separate execution-authorization artifact hash-bound to it;
3. perform all filesystem preflight checks before invoking the UDP receiver;
4. invoke the ordinary unprivileged dual-UDP receiver;
5. use the receiver-created session directory;
6. execute identity, status and diagnostic HTTP GET evidence sequentially;
7. atomically publish one composite session receipt.

The repository resolution state contains no real binding and no real execution
authorization. Tests verify orchestration through injected non-network
component functions because the real V2 binding contract intentionally rejects
loopback physical runtime values.
"""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Callable, Mapping
import json
import os
import time

from .baseline_nominality import (
    BaselineNominalitySplit,
)

from .live_executor_safety import (
    publish_same_directory_partial_file,
)

from .se4_http_evidence_executor import (
    EXECUTION_SCOPE_REAL_SENSOR,
    execute_one_shot_http_evidence_read,
)

from .se4_real_train_runtime_input_binding import (
    SE4RuntimeInputBindingError,
)

from .se4_real_train_runtime_input_binding_v2 import (
    validate_runtime_binding_candidate_v2,
)

from .unprivileged_udp_receiver import (
    Vlp32cUnprivilegedUdpReceiverCandidate,
    capture_dual_udp_payload_streams,
)


RESOLUTION_SCHEMA = (
    "TRUST_ROBOT_SE4_COMPOSITE_LIVE_SESSION_ORCHESTRATOR_RESOLUTION_V1"
)

AUTHORIZATION_SCHEMA = (
    "TRUST_ROBOT_SE4_LIVE_SESSION_EXECUTION_AUTHORIZATION_V1"
)

RECEIPT_SCHEMA = (
    "TRUST_ROBOT_SE4_COMPOSITE_LIVE_SESSION_RECEIPT_V1"
)

FAILURE_SCHEMA = (
    "TRUST_ROBOT_SE4_COMPOSITE_LIVE_SESSION_FAILURE_RECEIPT_V1"
)

RESOLUTION_ID = (
    "trust_robot_se4_composite_live_session_orchestrator_resolution_v1"
)

AUTHORIZATION_SCOPE = (
    "real_sensor"
)

HTTP_ORDER = (
    "identity",
    "status",
    "diagnostic",
)

COMPOSITE_RECEIPT_NAME = (
    "composite_session_receipt.json"
)

FAILURE_RECEIPT_NAME = (
    "composite_session_failure.json"
)

FROZEN_INPUT_SHA256 = {
    "runtime_binding_v2_module":
        "f00fb0571a9fb4ac1a078a6789941741b68bbf066a7a6f01028f2450bc820212",

    "runtime_binding_v2_config":
        "740705b97fa088f31efe3e603e9c25d3c005d9cae1b757479377cc7aabe517fb",

    "runtime_binding_v2_freeze":
        "81f1d22674a4ca1ef4a8b5c9c4d16e446423eb3e6a76981fa7d6f99b08477388",

    "HTTP_executor_module":
        "98d82acca2308aea76537de4a9cc4fa0eb94e8fd9bc4aa9bde048382f5b69dd9",

    "HTTP_executor_config":
        "51f98b3424d1db7bd2706f49e399954b007dfd8c2897d495462c7c7edd921aac",

    "HTTP_executor_freeze":
        "29639601503a8d7c0b9db879939a8960b2f0a69ca10e378fc07f0b031aeadc10",

    "UDP_receiver_module":
        "05e40722e15434b92d0f8aad93e4a6a9aef71a38dcd8d97e8bddc4f5ec3a385d",

    "UDP_receiver_config":
        "96cd1be3cf9ec3a55721cb496cac32a61279682bdf2d11d16b479568435c3b90",

    "live_executor_safety_module":
        "6dcb292355ba17ec8a563b1183e0279b40559ec0467dd8dc9fbba5a2e674e26a",
}


class SE4CompositeLiveSessionOrchestratorError(
    ValueError
):
    """Raised when the composite live-session contract is violated."""


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


def _content_sha256(
    payload: Mapping[str, object],
    *,
    digest_field: str,
) -> str:
    body = dict(
        payload
    )

    body.pop(
        digest_field,
        None,
    )

    return sha256(
        _canonical_json(
            body
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def resolution_content_sha256(
    payload: Mapping[str, object],
) -> str:
    return _content_sha256(
        payload,
        digest_field="content_sha256",
    )


def authorization_content_sha256(
    payload: Mapping[str, object],
) -> str:
    return _content_sha256(
        payload,
        digest_field="authorization_sha256",
    )


def receipt_content_sha256(
    payload: Mapping[str, object],
) -> str:
    return _content_sha256(
        payload,
        digest_field="receipt_sha256",
    )


def _artifact_sha256(
    value: Mapping[str, object],
) -> str:
    return sha256(
        _canonical_json(
            value
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def _text(
    value: object,
    *,
    name: str,
) -> str:
    if not isinstance(
        value,
        str,
    ):
        raise SE4CompositeLiveSessionOrchestratorError(
            f"{name} must be a string"
        )

    stripped = value.strip()

    if not stripped:
        raise SE4CompositeLiveSessionOrchestratorError(
            f"{name} must be non-empty"
        )

    return stripped


def _digest(
    value: object,
    *,
    name: str,
) -> str:
    text = _text(
        value,
        name=name,
    ).lower()

    if len(
        text
    ) != 64:
        raise SE4CompositeLiveSessionOrchestratorError(
            f"{name} must be one SHA-256 hex digest"
        )

    if any(
        character
        not in "0123456789abcdef"
        for character
        in text
    ):
        raise SE4CompositeLiveSessionOrchestratorError(
            f"{name} must be lowercase SHA-256 hex"
        )

    return text


def build_execution_authorization_candidate(
    *,
    authorization_id: str,
    binding_sha256: str,
    authorization_record_sha256: str,
    authorized_for_real_sensor_execution: bool,
    declared_before_execution: bool,
) -> dict[str, object]:
    """Build one explicit authorization artifact.

    This function defines the format only. The repository resolution does not
    contain an accepted real authorization artifact.
    """

    identifier = _text(
        authorization_id,
        name="authorization_id",
    )

    if (
        "/" in identifier
        or "\\" in identifier
        or identifier in {
            ".",
            "..",
        }
    ):
        raise SE4CompositeLiveSessionOrchestratorError(
            "authorization_id must be one safe path component"
        )

    binding_digest = _digest(
        binding_sha256,
        name="binding_sha256",
    )

    record_digest = _digest(
        authorization_record_sha256,
        name="authorization_record_sha256",
    )

    if type(
        authorized_for_real_sensor_execution
    ) is not bool:
        raise SE4CompositeLiveSessionOrchestratorError(
            "authorized_for_real_sensor_execution must be bool"
        )

    if type(
        declared_before_execution
    ) is not bool:
        raise SE4CompositeLiveSessionOrchestratorError(
            "declared_before_execution must be bool"
        )

    payload: dict[str, object] = {
        "schema":
            AUTHORIZATION_SCHEMA,

        "schema_version":
            1,

        "authorization_id":
            identifier,

        "execution_scope":
            AUTHORIZATION_SCOPE,

        "binding_sha256":
            binding_digest,

        "authorization_record_sha256":
            record_digest,

        "authorized_for_real_sensor_execution":
            authorized_for_real_sensor_execution,

        "declared_before_execution":
            declared_before_execution,

        "source_acceptance_authorized":
            False,

        "health_label_generation_authorized":
            False,

        "authorization_is_health_truth":
            False,

        "authorization_is_runtime_binding":
            False,
    }

    payload[
        "authorization_sha256"
    ] = authorization_content_sha256(
        payload
    )

    return payload


def validate_execution_authorization_candidate(
    payload: Mapping[str, object],
    *,
    expected_binding_sha256: str,
) -> Mapping[str, object]:
    if not isinstance(
        payload,
        Mapping,
    ):
        raise SE4CompositeLiveSessionOrchestratorError(
            "execution authorization must be a mapping"
        )

    required = {
        "schema",
        "schema_version",
        "authorization_id",
        "execution_scope",
        "binding_sha256",
        "authorization_record_sha256",
        "authorized_for_real_sensor_execution",
        "declared_before_execution",
        "source_acceptance_authorized",
        "health_label_generation_authorized",
        "authorization_is_health_truth",
        "authorization_is_runtime_binding",
        "authorization_sha256",
    }

    if set(
        payload
    ) != required:
        raise SE4CompositeLiveSessionOrchestratorError(
            "execution authorization fields differ from contract"
        )

    expected = build_execution_authorization_candidate(
        authorization_id=
            payload[
                "authorization_id"
            ],

        binding_sha256=
            payload[
                "binding_sha256"
            ],

        authorization_record_sha256=
            payload[
                "authorization_record_sha256"
            ],

        authorized_for_real_sensor_execution=
            payload[
                "authorized_for_real_sensor_execution"
            ],

        declared_before_execution=
            payload[
                "declared_before_execution"
            ],
    )

    if dict(
        payload
    ) != expected:
        raise SE4CompositeLiveSessionOrchestratorError(
            "execution authorization differs from canonical representation"
        )

    expected_binding = _digest(
        expected_binding_sha256,
        name="expected_binding_sha256",
    )

    if payload[
        "binding_sha256"
    ] != expected_binding:
        raise SE4CompositeLiveSessionOrchestratorError(
            "execution authorization is not bound to this runtime binding"
        )

    if payload[
        "execution_scope"
    ] != AUTHORIZATION_SCOPE:
        raise SE4CompositeLiveSessionOrchestratorError(
            "execution authorization scope must be real_sensor"
        )

    if payload[
        "authorized_for_real_sensor_execution"
    ] is not True:
        raise SE4CompositeLiveSessionOrchestratorError(
            "real-sensor execution authorization is not granted"
        )

    if payload[
        "declared_before_execution"
    ] is not True:
        raise SE4CompositeLiveSessionOrchestratorError(
            "execution authorization must be declared before execution"
        )

    if payload[
        "source_acceptance_authorized"
    ] is not False:
        raise SE4CompositeLiveSessionOrchestratorError(
            "execution authorization may not authorize source acceptance"
        )

    if payload[
        "health_label_generation_authorized"
    ] is not False:
        raise SE4CompositeLiveSessionOrchestratorError(
            "execution authorization may not authorize health labels"
        )

    return payload


def build_composite_orchestrator_resolution(
) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema":
            RESOLUTION_SCHEMA,

        "schema_version":
            1,

        "resolution_id":
            RESOLUTION_ID,

        "stage_context": {
            "stage_id":
                "SE4",

            "sub_frontier":
                "composite_binding_HTTP_UDP_live_session_orchestration",

            "status":
                "software_implemented_injected_execution_verified_real_execution_blocked",

            "SE4_complete":
                False,

            "SE4_training_authorized":
                False,
        },

        "composition_contract": {
            "validated_V2_binding_required":
                True,

            "separate_hash_bound_execution_authorization_required":
                True,

            "authorization_must_precede_UDP_invocation":
                True,

            "UDP_receiver_owns_session_directory_creation":
                True,

            "HTTP_executor_requires_returned_existing_session_directory":
                True,

            "HTTP_order": [
                "identity",
                "status",
                "diagnostic",
            ],

            "HTTP_UDP_concurrency_required":
                False,

            "selected_execution_order": [
                "validate_V2_binding",
                "validate_execution_authorization",
                "filesystem_preflight",
                "invoke_UDP_receiver",
                "validate_returned_session_directory",
                "execute_identity_HTTP",
                "execute_status_HTTP",
                "execute_diagnostic_HTTP",
                "publish_composite_session_receipt",
            ],

            "component_dependency_injection_supported_for_software_tests":
                True,

            "software_test_injection_is_real_sensor_execution":
                False,
        },

        "filesystem_contract": {
            "absolute_output_root_must_exist_before_UDP_invocation":
                True,

            "expected_session_directory_must_not_exist_before_UDP_invocation":
                True,

            "returned_session_directory_must_equal_binding_derived_path":
                True,

            "composite_receipt":
                COMPOSITE_RECEIPT_NAME,

            "failure_receipt":
                FAILURE_RECEIPT_NAME,

            "receipt_publication_uses_same_directory_atomic_helper":
                True,

            "existing_final_overwrite_allowed":
                False,

            "HTTP_orchestrator_precreates_session_directory":
                False,
        },

        "authorization_contract": {
            "schema":
                AUTHORIZATION_SCHEMA,

            "authorization_artifact_format_selected":
                True,

            "authorization_hash_bound_to_V2_binding":
                True,

            "external_authorization_record_digest_required":
                True,

            "repository_real_authorization_artifact_count":
                0,

            "real_sensor_execution_authorized":
                False,

            "authorization_is_source_acceptance":
                False,

            "authorization_is_health_label":
                False,
        },

        "verification_state": {
            "component_injection_orchestration_verified":
                True,

            "real_sensor_execution_verified":
                False,

            "real_sensor_network_IO_executed":
                False,

            "real_sensor_contact_executed":
                False,

            "raw_real_sensor_capture_artifact_count":
                0,

            "real_composite_session_receipt_count":
                0,
        },

        "current_real_state": {
            "real_runtime_binding_count":
                0,

            "real_runtime_values_bound":
                False,

            "real_execution_authorization_count":
                0,

            "real_sensor_execution_authorized":
                False,

            "real_session_execution_count":
                0,
        },

        "scientific_boundary": {
            "orchestration_software_is_execution_authorization":
                False,

            "component_injection_test_is_physical_sensor_evidence":
                False,

            "HTTP_evidence_is_automatically_health_supervision":
                False,

            "UDP_capture_is_automatically_baseline_nominality":
                False,

            "session_order_establishes_interval_binding":
                False,

            "host_times_are_physical_measurement_time":
                False,

            "accepted_baseline_nominality_source_count":
                0,

            "accepted_health_supervision_source_count":
                0,

            "real_health_label_count":
                0,

            "interval_binding_established":
                False,

            "physical_measurement_time_established":
                False,

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
            "composite_live_session_orchestrator_software_implemented":
                True,

            "component_injection_orchestration_verified":
                True,

            "real_runtime_binding_count":
                0,

            "real_runtime_values_bound":
                False,

            "real_execution_authorization_count":
                0,

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
                    "Freeze and promote this orchestrator software. After that, "
                    "obtain one trustworthy operator-supplied real TRAIN V2 "
                    "runtime binding plus a separately grounded execution "
                    "authorization before any real sensor network I/O."
                ),
        },

        "frozen_input_sha256":
            dict(
                FROZEN_INPUT_SHA256
            ),
    }

    payload[
        "content_sha256"
    ] = resolution_content_sha256(
        payload
    )

    return payload


def validate_composite_orchestrator_resolution(
    payload: Mapping[str, object],
) -> Mapping[str, object]:
    if not isinstance(
        payload,
        Mapping,
    ):
        raise SE4CompositeLiveSessionOrchestratorError(
            "orchestrator resolution must be a mapping"
        )

    expected = (
        build_composite_orchestrator_resolution()
    )

    if dict(
        payload
    ) != expected:
        raise SE4CompositeLiveSessionOrchestratorError(
            "orchestrator resolution differs from canonical state"
        )

    return payload


def _expected_session_directory(
    binding: Mapping[str, object],
) -> Path:
    return (
        Path(
            binding[
                "filesystem_binding"
            ][
                "absolute_output_root"
            ]
        )
        / binding[
            "acquisition_session_id"
        ]
    )


def _filesystem_preflight(
    binding: Mapping[str, object],
) -> Path:
    output_root = Path(
        binding[
            "filesystem_binding"
        ][
            "absolute_output_root"
        ]
    )

    if not output_root.is_absolute():
        raise SE4CompositeLiveSessionOrchestratorError(
            "absolute_output_root must remain absolute at execution"
        )

    if not output_root.exists():
        raise SE4CompositeLiveSessionOrchestratorError(
            "absolute_output_root must exist before UDP invocation"
        )

    if not output_root.is_dir():
        raise SE4CompositeLiveSessionOrchestratorError(
            "absolute_output_root must be a directory"
        )

    session = _expected_session_directory(
        binding
    )

    if session.exists():
        raise SE4CompositeLiveSessionOrchestratorError(
            "expected fresh session directory already exists"
        )

    return session


def _udp_candidate_from_binding(
    binding: Mapping[str, object],
) -> Vlp32cUnprivilegedUdpReceiverCandidate:
    return Vlp32cUnprivilegedUdpReceiverCandidate(
        acquisition_session_id=
            binding[
                "acquisition_session_id"
            ],

        split=
            BaselineNominalitySplit.TRAIN,

        bind_ipv4=
            binding[
                "UDP_receiver_binding"
            ][
                "bind_ipv4"
            ],

        measurement_udp_port=
            binding[
                "UDP_receiver_binding"
            ][
                "measurement_udp_port"
            ],

        position_udp_port=
            binding[
                "UDP_receiver_binding"
            ][
                "position_udp_port"
            ],

        capture_duration_seconds=
            binding[
                "UDP_receiver_binding"
            ][
                "capture_duration_seconds"
            ],

        absolute_output_root=
            binding[
                "filesystem_binding"
            ][
                "absolute_output_root"
            ],
    )


def _write_json_receipt(
    *,
    session_directory: Path,
    final_name: str,
    payload: Mapping[str, object],
) -> dict[str, object]:
    final = (
        session_directory
        / final_name
    )

    partial = (
        session_directory
        / (
            "."
            + final_name
            + ".partial"
        )
    )

    if final.exists():
        raise SE4CompositeLiveSessionOrchestratorError(
            f"refusing to overwrite existing final artifact: {final}"
        )

    if partial.exists():
        raise SE4CompositeLiveSessionOrchestratorError(
            f"refusing pre-existing partial artifact: {partial}"
        )

    encoded = (
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode(
        "utf-8"
    )

    with partial.open(
        "xb"
    ) as handle:
        handle.write(
            encoded
        )

        handle.flush()

        os.fsync(
            handle.fileno()
        )

    return publish_same_directory_partial_file(
        partial,
        final,
    )


def _validate_udp_result(
    *,
    result: object,
    expected_session_directory: Path,
) -> tuple[
    Mapping[str, object],
    Path,
]:
    if not isinstance(
        result,
        Mapping,
    ):
        raise SE4CompositeLiveSessionOrchestratorError(
            "UDP receiver result must be a mapping"
        )

    for field in (
        "session_directory",
        "capture_receipt",
        "capture_receipt_publication",
    ):
        if field not in result:
            raise SE4CompositeLiveSessionOrchestratorError(
                f"UDP receiver result missing {field}"
            )

    returned = Path(
        result[
            "session_directory"
        ]
    )

    if returned != expected_session_directory:
        raise SE4CompositeLiveSessionOrchestratorError(
            "UDP receiver returned unexpected session directory"
        )

    if not returned.is_dir():
        raise SE4CompositeLiveSessionOrchestratorError(
            "UDP receiver returned session directory does not exist"
        )

    receipt = result[
        "capture_receipt"
    ]

    if not isinstance(
        receipt,
        Mapping,
    ):
        raise SE4CompositeLiveSessionOrchestratorError(
            "UDP capture_receipt must be a mapping"
        )

    return (
        receipt,
        returned,
    )


def _validate_http_receipt(
    *,
    receipt: object,
    evidence_kind: str,
) -> Mapping[str, object]:
    if not isinstance(
        receipt,
        Mapping,
    ):
        raise SE4CompositeLiveSessionOrchestratorError(
            f"{evidence_kind} HTTP receipt must be a mapping"
        )

    if receipt.get(
        "evidence_kind"
    ) != evidence_kind:
        raise SE4CompositeLiveSessionOrchestratorError(
            f"{evidence_kind} HTTP receipt kind mismatch"
        )

    return receipt


def execute_composite_live_session(
    *,
    runtime_binding: Mapping[str, object],
    execution_authorization: Mapping[str, object],
    udp_capture_fn: Callable[
        [Vlp32cUnprivilegedUdpReceiverCandidate],
        Mapping[str, object],
    ] = capture_dual_udp_payload_streams,
    http_read_fn: Callable[..., Mapping[str, object]] = (
        execute_one_shot_http_evidence_read
    ),
) -> dict[str, object]:
    """Execute one authorized sequential composite session.

    Default component functions are the frozen real UDP receiver and HTTP
    executor. Tests may inject non-network component functions; injection does
    not alter the binding or authorization validation rules.
    """

    try:
        validate_runtime_binding_candidate_v2(
            runtime_binding
        )
    except SE4RuntimeInputBindingError as exc:
        raise SE4CompositeLiveSessionOrchestratorError(
            "invalid V2 runtime binding: "
            + str(
                exc
            )
        ) from exc

    binding_sha = runtime_binding[
        "binding_sha256"
    ]

    validate_execution_authorization_candidate(
        execution_authorization,
        expected_binding_sha256=
            binding_sha,
    )

    expected_session = _filesystem_preflight(
        runtime_binding
    )

    udp_candidate = _udp_candidate_from_binding(
        runtime_binding
    )

    phase = (
        "invoke_UDP_receiver"
    )

    session_directory: Path | None = None

    orchestration_start_wall_ns = (
        time.time_ns()
    )

    orchestration_start_monotonic_ns = (
        time.monotonic_ns()
    )

    try:
        udp_result = udp_capture_fn(
            udp_candidate
        )

        udp_receipt, session_directory = (
            _validate_udp_result(
                result=
                    udp_result,

                expected_session_directory=
                    expected_session,
            )
        )

        http_receipts: dict[
            str,
            Mapping[str, object],
        ] = {}

        for evidence_kind in HTTP_ORDER:
            phase = (
                "execute_"
                + evidence_kind
                + "_HTTP"
            )

            receipt = http_read_fn(
                evidence_kind=
                    evidence_kind,

                sensor_ipv4=
                    runtime_binding[
                        "sensor_binding"
                    ][
                        "sensor_ipv4"
                    ],

                session_directory=
                    session_directory,

                http_connect_timeout_seconds=
                    runtime_binding[
                        "HTTP_binding"
                    ][
                        "http_connect_timeout_seconds"
                    ],

                http_total_timeout_seconds=
                    runtime_binding[
                        "HTTP_binding"
                    ][
                        "http_total_timeout_seconds"
                    ],

                execution_scope=
                    EXECUTION_SCOPE_REAL_SENSOR,

                real_sensor_execution_authorized=
                    True,

                loopback_test_authorized=
                    False,

                http_port=
                    runtime_binding[
                        "HTTP_binding"
                    ][
                        "http_port"
                    ],
            )

            http_receipts[
                evidence_kind
            ] = _validate_http_receipt(
                receipt=
                    receipt,

                evidence_kind=
                    evidence_kind,
            )

        phase = (
            "publish_composite_session_receipt"
        )

        orchestration_end_monotonic_ns = (
            time.monotonic_ns()
        )

        orchestration_end_wall_ns = (
            time.time_ns()
        )

        composite: dict[str, object] = {
            "schema":
                RECEIPT_SCHEMA,

            "schema_version":
                1,

            "acquisition_session_id":
                runtime_binding[
                    "acquisition_session_id"
                ],

            "split":
                runtime_binding[
                    "split"
                ],

            "binding_sha256":
                binding_sha,

            "execution_authorization_sha256":
                execution_authorization[
                    "authorization_sha256"
                ],

            "execution_authorization_record_sha256":
                execution_authorization[
                    "authorization_record_sha256"
                ],

            "session_directory":
                str(
                    session_directory
                ),

            "execution_order": [
                "UDP_capture",
                "identity_HTTP",
                "status_HTTP",
                "diagnostic_HTTP",
                "composite_receipt_publication",
            ],

            "UDP_capture_receipt":
                dict(
                    udp_receipt
                ),

            "UDP_capture_receipt_sha256":
                _artifact_sha256(
                    udp_receipt
                ),

            "HTTP_receipts": {
                key:
                    dict(
                        value
                    )
                for key, value
                in http_receipts.items()
            },

            "HTTP_receipt_sha256": {
                key:
                    _artifact_sha256(
                        value
                    )
                for key, value
                in http_receipts.items()
            },

            "orchestration_host_start_wall_time_ns":
                orchestration_start_wall_ns,

            "orchestration_host_end_wall_time_ns":
                orchestration_end_wall_ns,

            "orchestration_host_start_monotonic_ns":
                orchestration_start_monotonic_ns,

            "orchestration_host_end_monotonic_ns":
                orchestration_end_monotonic_ns,

            "host_times_transport_provenance_only":
                True,

            "scientific_nonclaims": {
                "baseline_nominality_established":
                    False,

                "health_supervision_source_accepted":
                    False,

                "health_label_generated":
                    False,

                "interval_binding_established":
                    False,

                "physical_measurement_time_established":
                    False,

                "no_packet_loss_established":
                    False,

                "ATE_RPE_computed":
                    False,
            },
        }

        composite[
            "receipt_sha256"
        ] = receipt_content_sha256(
            composite
        )

        publication = _write_json_receipt(
            session_directory=
                session_directory,

            final_name=
                COMPOSITE_RECEIPT_NAME,

            payload=
                composite,
        )

        return {
            "session_directory":
                str(
                    session_directory
                ),

            "composite_session_receipt":
                composite,

            "composite_session_receipt_publication":
                publication,
        }

    except Exception as exc:
        if (
            session_directory is not None
            and session_directory.is_dir()
        ):
            failure_final = (
                session_directory
                / FAILURE_RECEIPT_NAME
            )

            composite_final = (
                session_directory
                / COMPOSITE_RECEIPT_NAME
            )

            if (
                not failure_final.exists()
                and not composite_final.exists()
            ):
                failure: dict[str, object] = {
                    "schema":
                        FAILURE_SCHEMA,

                    "schema_version":
                        1,

                    "acquisition_session_id":
                        runtime_binding[
                            "acquisition_session_id"
                        ],

                    "binding_sha256":
                        binding_sha,

                    "execution_authorization_sha256":
                        execution_authorization[
                            "authorization_sha256"
                        ],

                    "failed_phase":
                        phase,

                    "exception_type":
                        type(
                            exc
                        ).__name__,

                    "exception_message":
                        str(
                            exc
                        ),

                    "host_failure_wall_time_ns":
                        time.time_ns(),

                    "host_failure_time_is_transport_provenance_only":
                        True,

                    "source_acceptance_authorized":
                        False,

                    "health_label_generation_authorized":
                        False,

                    "interval_binding_established":
                        False,
                }

                failure[
                    "receipt_sha256"
                ] = receipt_content_sha256(
                    failure
                )

                try:
                    _write_json_receipt(
                        session_directory=
                            session_directory,

                        final_name=
                            FAILURE_RECEIPT_NAME,

                        payload=
                            failure,
                    )
                except Exception:
                    pass

        raise


def assert_repository_real_execution_authorized(
    payload: Mapping[str, object],
) -> None:
    validate_composite_orchestrator_resolution(
        payload
    )

    if payload[
        "current_real_state"
    ][
        "real_sensor_execution_authorized"
    ] is not True:
        raise SE4CompositeLiveSessionOrchestratorError(
            "real composite live-session execution remains blocked: no "
            "accepted real TRAIN V2 binding and no grounded execution "
            "authorization artifact exist"
        )


def assert_health_supervision_available(
    payload: Mapping[str, object],
) -> None:
    validate_composite_orchestrator_resolution(
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
        raise SE4CompositeLiveSessionOrchestratorError(
            "health supervision remains unavailable: orchestration software "
            "does not accept a supervision source or generate health labels"
        )
