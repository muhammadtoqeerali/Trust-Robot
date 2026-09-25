"""SE4 file-driven real TRAIN execution runner.

This module consumes, but never manufactures:

* one externally supplied V2 runtime-binding JSON file;
* one externally supplied execution-authorization JSON file;
* one external authorization-record file.

Validation establishes file integrity and contract consistency only. It does
not establish that an authorization record came from a trustworthy authority.

Real network execution additionally requires an explicit execution switch and
an exact network-I/O acknowledgement. Repository state contains no real input
files and no execution authorization.
"""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Callable, Mapping
import json

from .se4_composite_live_session_orchestrator import (
    SE4CompositeLiveSessionOrchestratorError,
    execute_composite_live_session,
    validate_execution_authorization_candidate,
)

from .se4_real_train_runtime_input_binding import (
    SE4RuntimeInputBindingError,
)

from .se4_real_train_runtime_input_binding_v2 import (
    validate_runtime_binding_candidate_v2,
)


RESOLUTION_SCHEMA = (
    "TRUST_ROBOT_SE4_REAL_TRAIN_EXECUTION_RUNNER_RESOLUTION_V1"
)

RESOLUTION_ID = (
    "trust_robot_se4_real_train_execution_runner_resolution_v1"
)

INPUT_VALIDATION_SCHEMA = (
    "TRUST_ROBOT_SE4_REAL_TRAIN_EXECUTION_INPUT_VALIDATION_V1"
)

NETWORK_IO_ACKNOWLEDGEMENT = (
    "I_AUTHORIZE_THIS_BOUND_REAL_SENSOR_NETWORK_IO"
)

FROZEN_INPUT_SHA256 = {
    "runtime_binding_v2_module":
        "f00fb0571a9fb4ac1a078a6789941741b68bbf066a7a6f01028f2450bc820212",

    "runtime_binding_v2_freeze":
        "81f1d22674a4ca1ef4a8b5c9c4d16e446423eb3e6a76981fa7d6f99b08477388",

    "composite_orchestrator_module":
        "ca23e6a2cca37c3af5ebeeae39bfdf6cc4ba4b9669b4a25135e6e15810081b2d",

    "composite_orchestrator_config":
        "1564aaa7c261d37219ede56d42daa428a754c089a420d988b2cfb5c818eb41ff",

    "composite_orchestrator_freeze":
        "7ee319bc88c33541923df1d73971a8703af29d177f98a05160a99655a9b51e04",
}


class SE4RealTrainExecutionRunnerError(
    ValueError
):
    """Raised when file-driven execution prerequisites are not satisfied."""


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


def validation_content_sha256(
    payload: Mapping[str, object],
) -> str:
    return _content_sha256(
        payload,
        digest_field="validation_sha256",
    )


def file_sha256(
    path: str | Path,
) -> str:
    candidate = Path(
        path
    )

    digest = sha256()

    with candidate.open(
        "rb"
    ) as handle:
        while True:
            chunk = handle.read(
                1024 * 1024
            )

            if not chunk:
                break

            digest.update(
                chunk
            )

    return digest.hexdigest()


def _absolute_regular_file(
    value: str | Path,
    *,
    name: str,
) -> Path:
    path = Path(
        value
    )

    if not path.is_absolute():
        raise SE4RealTrainExecutionRunnerError(
            f"{name} must be an absolute path"
        )

    if path.is_symlink():
        raise SE4RealTrainExecutionRunnerError(
            f"{name} must not be a symbolic link"
        )

    if not path.exists():
        raise SE4RealTrainExecutionRunnerError(
            f"{name} does not exist"
        )

    if not path.is_file():
        raise SE4RealTrainExecutionRunnerError(
            f"{name} must be a regular file"
        )

    return path


def _load_json_mapping_once(
    path: Path,
    *,
    name: str,
) -> tuple[
    Mapping[str, object],
    str,
]:
    raw = path.read_bytes()

    digest = sha256(
        raw
    ).hexdigest()

    try:
        value = json.loads(
            raw.decode(
                "utf-8"
            )
        )
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as exc:
        raise SE4RealTrainExecutionRunnerError(
            f"{name} must be one UTF-8 JSON document"
        ) from exc

    if not isinstance(
        value,
        Mapping,
    ):
        raise SE4RealTrainExecutionRunnerError(
            f"{name} JSON root must be an object"
        )

    return (
        value,
        digest,
    )


def validate_real_execution_inputs_from_files(
    *,
    runtime_binding_file: str | Path,
    execution_authorization_file: str | Path,
    authorization_record_file: str | Path,
) -> dict[str, object]:
    """Validate externally supplied files without network execution."""

    binding_path = _absolute_regular_file(
        runtime_binding_file,
        name="runtime_binding_file",
    )

    authorization_path = _absolute_regular_file(
        execution_authorization_file,
        name="execution_authorization_file",
    )

    record_path = _absolute_regular_file(
        authorization_record_file,
        name="authorization_record_file",
    )

    resolved_paths = {
        binding_path,
        authorization_path,
        record_path,
    }

    if len(
        resolved_paths
    ) != 3:
        raise SE4RealTrainExecutionRunnerError(
            "binding, authorization and authorization-record files must be distinct"
        )

    binding, binding_file_sha = _load_json_mapping_once(
        binding_path,
        name="runtime_binding_file",
    )

    authorization, authorization_file_sha = _load_json_mapping_once(
        authorization_path,
        name="execution_authorization_file",
    )

    try:
        validate_runtime_binding_candidate_v2(
            binding
        )
    except SE4RuntimeInputBindingError as exc:
        raise SE4RealTrainExecutionRunnerError(
            "runtime binding failed V2 validation: "
            + str(
                exc
            )
        ) from exc

    try:
        validate_execution_authorization_candidate(
            authorization,
            expected_binding_sha256=
                binding[
                    "binding_sha256"
                ],
        )
    except SE4CompositeLiveSessionOrchestratorError as exc:
        raise SE4RealTrainExecutionRunnerError(
            "execution authorization failed validation: "
            + str(
                exc
            )
        ) from exc

    record_file_sha = file_sha256(
        record_path
    )

    if record_file_sha != authorization[
        "authorization_record_sha256"
    ]:
        raise SE4RealTrainExecutionRunnerError(
            "authorization-record file SHA-256 does not match execution authorization"
        )

    payload: dict[str, object] = {
        "schema":
            INPUT_VALIDATION_SCHEMA,

        "schema_version":
            1,

        "runtime_binding_file":
            str(
                binding_path
            ),

        "runtime_binding_file_sha256":
            binding_file_sha,

        "runtime_binding_sha256":
            binding[
                "binding_sha256"
            ],

        "execution_authorization_file":
            str(
                authorization_path
            ),

        "execution_authorization_file_sha256":
            authorization_file_sha,

        "execution_authorization_sha256":
            authorization[
                "authorization_sha256"
            ],

        "authorization_record_file":
            str(
                record_path
            ),

        "authorization_record_file_sha256":
            record_file_sha,

        "authorization_record_digest_matches":
            True,

        "runtime_binding_valid":
            True,

        "execution_authorization_valid":
            True,

        "authorization_hash_bound_to_runtime_binding":
            True,

        "declared_before_execution":
            authorization[
                "declared_before_execution"
            ],

        "authorized_for_real_sensor_execution":
            authorization[
                "authorized_for_real_sensor_execution"
            ],

        "validation_performs_network_IO":
            False,

        "validation_contacts_sensor":
            False,

        "authorization_record_digest_proves_authority_or_trust":
            False,

        "source_acceptance_authorized":
            False,

        "health_label_generation_authorized":
            False,
    }

    payload[
        "validation_sha256"
    ] = validation_content_sha256(
        payload
    )

    return {
        "runtime_binding":
            dict(
                binding
            ),

        "execution_authorization":
            dict(
                authorization
            ),

        "input_validation":
            payload,
    }


def execute_real_session_from_files(
    *,
    runtime_binding_file: str | Path,
    execution_authorization_file: str | Path,
    authorization_record_file: str | Path,
    execute_real: bool,
    network_io_acknowledgement: str,
    orchestrator_fn: Callable[..., Mapping[str, object]] | None = None,
) -> dict[str, object]:
    """Validate external files, then execute only under two explicit gates."""

    if type(
        execute_real
    ) is not bool:
        raise SE4RealTrainExecutionRunnerError(
            "execute_real must be bool"
        )

    if execute_real is not True:
        raise SE4RealTrainExecutionRunnerError(
            "real execution blocked: execute_real must be explicitly true"
        )

    if network_io_acknowledgement != NETWORK_IO_ACKNOWLEDGEMENT:
        raise SE4RealTrainExecutionRunnerError(
            "real execution blocked: exact network-I/O acknowledgement is required"
        )

    prepared = validate_real_execution_inputs_from_files(
        runtime_binding_file=
            runtime_binding_file,

        execution_authorization_file=
            execution_authorization_file,

        authorization_record_file=
            authorization_record_file,
    )

    function = (
        execute_composite_live_session
        if orchestrator_fn is None
        else orchestrator_fn
    )

    result = function(
        runtime_binding=
            prepared[
                "runtime_binding"
            ],

        execution_authorization=
            prepared[
                "execution_authorization"
            ],
    )

    if not isinstance(
        result,
        Mapping,
    ):
        raise SE4RealTrainExecutionRunnerError(
            "composite orchestrator result must be a mapping"
        )

    return {
        "input_validation":
            prepared[
                "input_validation"
            ],

        "execution_result":
            dict(
                result
            ),
    }


def build_real_train_execution_runner_resolution(
) -> dict[str, object]:
    """Build repository state for the file-driven execution runner."""

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
                "file_driven_real_TRAIN_live_execution_runner",

            "status":
                "software_implemented_validation_only_verified_real_inputs_absent",

            "SE4_complete":
                False,

            "SE4_training_authorized":
                False,
        },

        "input_contract": {
            "required_external_files": [
                "runtime_binding_file",
                "execution_authorization_file",
                "authorization_record_file",
            ],

            "runtime_binding_must_validate_as_V2":
                True,

            "execution_authorization_must_validate":
                True,

            "execution_authorization_must_bind_exact_runtime_binding":
                True,

            "authorization_record_file_SHA256_must_match_authorization":
                True,

            "authorization_record_digest_alone_proves_authority_or_trust":
                False,

            "input_files_must_be_absolute_regular_non_symlink_files":
                True,

            "input_files_must_be_distinct":
                True,

            "runner_manufactures_runtime_values":
                False,

            "runner_manufactures_execution_authorization":
                False,
        },

        "execution_gates": {
            "default_mode":
                "validation_only",

            "validation_only_performs_network_IO":
                False,

            "validation_only_contacts_sensor":
                False,

            "explicit_execute_real_switch_required":
                True,

            "exact_network_IO_acknowledgement_required":
                True,

            "network_IO_acknowledgement":
                NETWORK_IO_ACKNOWLEDGEMENT,

            "validated_external_execution_authorization_still_required":
                True,
        },

        "verification_state": {
            "file_input_validation_software_verified":
                True,

            "injected_execution_dispatch_verified":
                True,

            "injected_execution_dispatch_is_real_sensor_execution":
                False,

            "real_file_input_set_count":
                0,

            "real_sensor_execution_verified":
                False,

            "real_sensor_network_IO_executed":
                False,

            "real_sensor_contact_executed":
                False,
        },

        "current_real_state": {
            "real_runtime_binding_count":
                0,

            "real_runtime_values_bound":
                False,

            "real_execution_authorization_count":
                0,

            "grounded_authorization_record_count":
                0,

            "real_sensor_execution_authorized":
                False,

            "real_session_execution_count":
                0,

            "raw_real_sensor_capture_artifact_count":
                0,
        },

        "scientific_boundary": {
            "host_discovery_is_runtime_binding":
                False,

            "authorization_record_hash_match_is_proof_of_authority":
                False,

            "runner_software_is_execution_authorization":
                False,

            "successful_execution_is_automatic_source_acceptance":
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
            "file_driven_real_execution_runner_software_resolved":
                True,

            "real_input_source_resolved":
                False,

            "grounded_execution_authorization_resolved":
                False,

            "real_runtime_binding_count":
                0,

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
                    "Obtain externally grounded real TRAIN V2 runtime values "
                    "and a trustworthy authorization record; construct their "
                    "separate hash-bound JSON artifacts before any real run."
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


def validate_real_train_execution_runner_resolution(
    payload: Mapping[str, object],
) -> Mapping[str, object]:
    if not isinstance(
        payload,
        Mapping,
    ):
        raise SE4RealTrainExecutionRunnerError(
            "runner resolution must be a mapping"
        )

    expected = (
        build_real_train_execution_runner_resolution()
    )

    if dict(
        payload
    ) != expected:
        raise SE4RealTrainExecutionRunnerError(
            "runner resolution differs from canonical state"
        )

    return payload


def assert_repository_real_inputs_available(
    payload: Mapping[str, object],
) -> None:
    validate_real_train_execution_runner_resolution(
        payload
    )

    state = payload[
        "current_real_state"
    ]

    if (
        state[
            "real_runtime_binding_count"
        ] <= 0
        or state[
            "real_execution_authorization_count"
        ] <= 0
        or state[
            "grounded_authorization_record_count"
        ] <= 0
    ):
        raise SE4RealTrainExecutionRunnerError(
            "real execution inputs remain unavailable: repository has no real "
            "V2 binding, no real execution authorization and no grounded "
            "authorization record"
        )
