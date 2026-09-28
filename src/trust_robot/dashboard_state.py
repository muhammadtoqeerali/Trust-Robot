"""Read-only TRUST-ROBOT dashboard state projection.

This module converts already-existing repository evidence into a stable,
dashboard-friendly DTO.

It deliberately does not:

* contact sensors;
* execute acquisition;
* manufacture authorization;
* manufacture health labels;
* open validation or confirmation data;
* select scientific parameters;
* change thresholds or calibration;
* perform ATE/RPE;
* modify repository evidence.

The dashboard is a presentation/observability layer only.
"""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping
import json
import subprocess


SNAPSHOT_SCHEMA = (
    "TRUST_ROBOT_DASHBOARD_READ_ONLY_SNAPSHOT_V1"
)

API_VERSION = "v1"

FRONTEND_PROGRAM_ID = (
    "TRUST_ROBOT_FRONT_SIDE_OPERATIONS_DASHBOARD_V1"
)

E2E_FREEZE_RELATIVE = (
    "manifests/"
    "trust_robot_se4_software_only_end_to_end_qualification_freeze_v1.json"
)

SPLIT_MANIFEST_RELATIVE = (
    "manifests/"
    "m2dgr_trajectory_manifest_v1_split_freeze_v1.json"
)

SOFTWARE_PLAN_RELATIVE = (
    "configs/trust_robot/"
    "software_evidence_completion_plan_v1.json"
)

HEALTH_RESOLUTION_RELATIVE = (
    "configs/trust_robot/"
    "se4_health_model_training_resolution_v1.json"
)

RUNTIME_BINDING_RELATIVE = (
    "configs/trust_robot/"
    "se4_real_train_runtime_input_binding_v2.json"
)

EXPECTED_E2E_FREEZE_SHA256 = (
    "0017b8036c4fbf0627eb93bad34a5070de02082707959348dff3be8a7d81a2d1"
)

EXPECTED_SPLIT_MANIFEST_SHA256 = (
    "017a388ef1ce4ad30812669632a022ca37c084871bc949693fd9c0541014238f"
)


class DashboardStateError(
    ValueError
):
    """Dashboard state cannot be built without violating its contract."""


def canonical_json_bytes(
    payload: object,
) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode(
        "utf-8"
    )


def content_sha256(
    payload: Mapping[str, object],
    *,
    digest_field: str = "content_sha256",
) -> str:
    body = dict(
        payload
    )

    body.pop(
        digest_field,
        None,
    )

    return sha256(
        canonical_json_bytes(
            body
        )
    ).hexdigest()


def file_sha256(
    path: str | Path,
) -> str:
    digest = sha256()

    with Path(
        path
    ).open(
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


def _load_json(
    path: Path,
) -> dict[str, Any]:
    if not path.is_file():
        raise DashboardStateError(
            f"required dashboard evidence file missing: {path}"
        )

    try:
        payload = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
    except Exception as exc:
        raise DashboardStateError(
            f"cannot parse dashboard evidence JSON: {path}"
        ) from exc

    if not isinstance(
        payload,
        dict,
    ):
        raise DashboardStateError(
            f"dashboard evidence root must be an object: {path}"
        )

    return payload


def _git_text(
    repo_root: Path,
    *args: str,
) -> str:
    result = subprocess.run(
        [
            "git",
            *args,
        ],
        cwd=repo_root,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    return result.stdout.strip()


def _git_metadata(
    repo_root: Path,
) -> dict[str, object]:
    head = _git_text(
        repo_root,
        "rev-parse",
        "HEAD",
    )

    tree = _git_text(
        repo_root,
        "rev-parse",
        "HEAD^{tree}",
    )

    branch = _git_text(
        repo_root,
        "branch",
        "--show-current",
    )

    porcelain = _git_text(
        repo_root,
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
    )

    return {
        "branch":
            branch,

        "head":
            head,

        "tree":
            tree,

        "worktree_clean":
            porcelain == "",

        "value_origin":
            "local_git_repository",
    }


def _source_record(
    repo_root: Path,
    relative_path: str,
) -> dict[str, object]:
    path = (
        repo_root
        / relative_path
    )

    return {
        "path":
            relative_path,

        "sha256":
            file_sha256(
                path
            ),

        "exists":
            True,
    }


def _split_projection(
    split_manifest: Mapping[str, Any],
) -> dict[str, object]:
    records = split_manifest.get(
        "records"
    )

    if not isinstance(
        records,
        list,
    ):
        raise DashboardStateError(
            "frozen split manifest records must be a list"
        )

    buckets: dict[
        str,
        list[str],
    ] = {
        "TRAIN":
            [],

        "VALIDATION":
            [],

        "CONFIRMATION":
            [],
    }

    for record in records:
        if not isinstance(
            record,
            Mapping,
        ):
            raise DashboardStateError(
                "frozen split manifest record must be an object"
            )

        trajectory_id = record.get(
            "trajectory_id"
        )

        split = record.get(
            "split"
        )

        if not isinstance(
            trajectory_id,
            str,
        ):
            raise DashboardStateError(
                "trajectory_id must be text"
            )

        if not isinstance(
            split,
            str,
        ):
            raise DashboardStateError(
                "split must be text"
            )

        source_to_dashboard_split = {
            "train":
                "TRAIN",

            "validation_calibration":
                "VALIDATION",

            "confirmation_test":
                "CONFIRMATION",
        }

        normalized = source_to_dashboard_split.get(
            split
        )

        if normalized is None:
            raise DashboardStateError(
                f"unexpected frozen split: {split}"
            )

        buckets[
            normalized
        ].append(
            trajectory_id
        )

    for values in buckets.values():
        values.sort()

    if {
        key:
            len(
                values
            )
        for key, values
        in buckets.items()
    } != {
        "TRAIN":
            22,

        "VALIDATION":
            7,

        "CONFIRMATION":
            7,
    }:
        raise DashboardStateError(
            "frozen split counts differ from 22/7/7"
        )

    return {
        "counts": {
            key:
                len(
                    values
                )
            for key, values
            in buckets.items()
        },

        "trajectories":
            buckets,

        "validation_open":
            False,

        "confirmation_open":
            False,

        "dashboard_allows_opening_closed_partitions":
            False,
    }


def _feature_projection(
    freeze: Mapping[str, Any],
) -> dict[str, object]:
    observations = freeze.get(
        "real_feature_observations"
    )

    if not isinstance(
        observations,
        Mapping,
    ):
        raise DashboardStateError(
            "E2E freeze lacks real_feature_observations"
        )

    return {
        "evidence_class":
            "real_M2DGR_TRAIN_software_evidence",

        "representative_trajectory":
            freeze[
                "real_data_lane"
            ][
                "representative_trajectory"
            ],

        "camera":
            observations[
                "camera"
            ],

        "d435i_imu":
            observations[
                "camera_imu"
            ],

        "handsfree_imu":
            observations[
                "handsfree_imu"
            ],

        "velodyne":
            observations[
                "velodyne"
            ],

        "feature_values_are_health_labels":
            False,

        "feature_values_are_health_predictions":
            False,

        "feature_values_are_ground_truth_error":
            False,
    }


def _acquisition_projection(
    freeze: Mapping[str, Any],
) -> dict[str, object]:
    live = freeze[
        "synthetic_live_lane"
    ]

    science = freeze[
        "scientific_boundary"
    ]

    return {
        "dashboard_mode":
            "software_only_evidence_shell",

        "real_sensor_connection_state":
            "not_executed",

        "real_sensor_connected":
            False,

        "real_sensor_network_IO_executed":
            science[
                "real_sensor_network_IO_executed"
            ],

        "real_sensor_contact":
            science[
                "real_sensor_contact"
            ],

        "real_runtime_binding_count":
            science[
                "real_runtime_binding_count"
            ],

        "real_execution_authorization_count":
            science[
                "real_execution_authorization_count"
            ],

        "grounded_authorization_record_count":
            science[
                "grounded_authorization_record_count"
            ],

        "synthetic_live_stack": {
            "qualified":
                True,

            "execution_order":
                live[
                    "execution_order"
                ],

            "UDP_receipt_produced":
                live[
                    "synthetic_UDP_receipt_produced"
                ],

            "HTTP_identity_receipt_produced":
                live[
                    "synthetic_HTTP_identity_receipt_produced"
                ],

            "HTTP_status_receipt_produced":
                live[
                    "synthetic_HTTP_status_receipt_produced"
                ],

            "HTTP_diagnostic_receipt_produced":
                live[
                    "synthetic_HTTP_diagnostic_receipt_produced"
                ],

            "composite_receipt_produced":
                live[
                    "synthetic_composite_receipt_produced"
                ],

            "real_sensor_evidence":
                False,
        },

        "real_execution_controls_exposed":
            False,

        "sensor_configuration_controls_exposed":
            False,

        "authorization_controls_exposed":
            False,

        "health_label_controls_exposed":
            False,
    }


def _session_history_projection(
    freeze: Mapping[str, Any],
) -> dict[str, object]:
    real = freeze[
        "real_data_lane"
    ]

    observed = freeze[
        "observed_qualification_receipt"
    ]

    live = freeze[
        "synthetic_live_lane"
    ]

    records = [
        {
            "id":
                "software_only_E2E_qualification",

            "display_name":
                "Software-only E2E qualification",

            "kind":
                "software_qualification",

            "state":
                "passed",

            "evidence_class":
                "real_M2DGR_TRAIN_software_evidence",

            "trajectory_id":
                real[
                    "representative_trajectory"
                ],

            "synthetic":
                False,

            "real_sensor_session":
                False,

            "execution_timestamp":
                None,

            "time_basis":
                "execution_time_not_claimed",

            "receipt_sha256":
                observed[
                    "receipt_file_sha256"
                ],
        },

        {
            "id":
                "synthetic_live_stack_qualification",

            "display_name":
                "Synthetic live-stack qualification",

            "kind":
                "synthetic_live_stack",

            "state":
                "passed",

            "evidence_class":
                "synthetic_live_stack_evidence",

            "trajectory_id":
                None,

            "synthetic":
                True,

            "real_sensor_session":
                False,

            "execution_timestamp":
                None,

            "time_basis":
                "execution_time_not_claimed",

            "receipt_sha256":
                live[
                    "run_specific_composite_receipt_sha256"
                ],
        },
    ]

    return {
        "record_count":
            len(
                records
            ),

        "real_sensor_session_count":
            0,

        "real_sensor_session_history_available":
            False,

        "records":
            records,

        "history_is_real_sensor_history":
            False,

        "history_creates_new_scientific_evidence":
            False,
    }


def _receipt_projection(
    freeze: Mapping[str, Any],
) -> dict[str, object]:
    observed = freeze[
        "observed_qualification_receipt"
    ]

    live = freeze[
        "synthetic_live_lane"
    ]

    return {
        "registry": [
            {
                "id":
                    "software_only_E2E_qualification_receipt",

                "display_name":
                    "Software-only E2E qualification receipt",

                "evidence_class":
                    "software_qualification_receipt",

                "availability":
                    "available",

                "synthetic":
                    False,

                "real_sensor_evidence":
                    False,

                "run_specific":
                    True,

                "file_sha256":
                    observed[
                        "receipt_file_sha256"
                    ],

                "content_sha256":
                    observed[
                        "receipt_content_sha256"
                    ],

                "stability_requirement":
                    False,
            },

            {
                "id":
                    "synthetic_composite_session_receipt",

                "display_name":
                    "Synthetic composite session receipt",

                "evidence_class":
                    "synthetic_live_stack_evidence",

                "availability":
                    "available_synthetic",

                "synthetic":
                    True,

                "real_sensor_evidence":
                    False,

                "run_specific":
                    True,

                "receipt_sha256":
                    live[
                        "run_specific_composite_receipt_sha256"
                    ],

                "stability_requirement":
                    live[
                        "run_specific_hash_is_replay_stability_requirement"
                    ],
            },
        ],

        "receipt_count":
            2,

        "run_specific_receipt_count":
            2,

        "real_sensor_receipt_count":
            0,

        "real_sensor_runtime_evidence_available":
            False,

        "receipt_hashes_are_scientific_truth_by_themselves":
            False,
    }


def _health_supervision_projection(
    freeze: Mapping[str, Any],
) -> dict[str, object]:
    science = freeze[
        "scientific_boundary"
    ]

    guards = freeze[
        "training_and_stage_guards"
    ]

    blockers = [
        {
            "id":
                "baseline_nominality_source",

            "display_name":
                "Accepted baseline nominality source",

            "resolved":
                science[
                    "accepted_baseline_nominality_source_count"
                ] > 0,

            "current_count":
                science[
                    "accepted_baseline_nominality_source_count"
                ],

            "required":
                True,
        },

        {
            "id":
                "health_supervision_source",

            "display_name":
                "Accepted health supervision source",

            "resolved":
                science[
                    "accepted_health_supervision_source_count"
                ] > 0,

            "current_count":
                science[
                    "accepted_health_supervision_source_count"
                ],

            "required":
                True,
        },

        {
            "id":
                "real_health_labels",

            "display_name":
                "Real health labels",

            "resolved":
                science[
                    "real_health_label_count"
                ] > 0,

            "current_count":
                science[
                    "real_health_label_count"
                ],

            "required":
                True,
        },

        {
            "id":
                "interval_binding",

            "display_name":
                "Interval binding",

            "resolved":
                science[
                    "interval_binding_established"
                ],

            "current_count":
                None,

            "required":
                True,
        },

        {
            "id":
                "physical_measurement_time",

            "display_name":
                "Physical measurement time",

            "resolved":
                science[
                    "physical_measurement_time_established"
                ],

            "current_count":
                None,

            "required":
                True,
        },
    ]

    return {
        "status":
            "blocked_pending_accepted_health_supervision",

        "accepted_baseline_nominality_source_count":
            science[
                "accepted_baseline_nominality_source_count"
            ],

        "accepted_health_supervision_source_count":
            science[
                "accepted_health_supervision_source_count"
            ],

        "real_health_label_count":
            science[
                "real_health_label_count"
            ],

        "health_label_generated":
            guards[
                "health_label_generated"
            ],

        "interval_binding_established":
            science[
                "interval_binding_established"
            ],

        "physical_measurement_time_established":
            science[
                "physical_measurement_time_established"
            ],

        "SE2_health_model_training_blocked":
            guards[
                "SE2_health_model_training_blocked"
            ],

        "SE4_training_execution_blocked":
            guards[
                "SE4_training_execution_blocked"
            ],

        "SE4_complete":
            science[
                "SE4_complete"
            ],

        "SE4_training_authorized":
            science[
                "SE4_training_authorized"
            ],

        "SE5_entry_blocked":
            guards[
                "SE5_entry_blocked"
            ],

        "SE5_may_proceed":
            science[
                "SE5_may_proceed"
            ],

        "training_ready":
            False,

        "blockers":
            blockers,

        "unresolved_blocker_count":
            sum(
                1
                for blocker
                in blockers
                if blocker[
                    "resolved"
                ] is False
            ),

        "feature_values_may_be_used_as_health_labels":
            False,

        "feature_values_may_be_used_as_health_predictions":
            False,

        "dashboard_controls": {
            "create_health_label":
                False,

            "accept_supervision_source":
                False,

            "authorize_training":
                False,

            "override_blocker":
                False,
        },
    }


def _operations_projection(
    freeze: Mapping[str, Any],
) -> dict[str, object]:
    science = freeze[
        "scientific_boundary"
    ]

    live = freeze[
        "synthetic_live_lane"
    ]

    required_binding_fields = [
        "acquisition_session_id",
        "split",
        "bind_ipv4",
        "measurement_udp_port",
        "position_udp_port",
        "sensor_ipv4",
        "capture_duration_seconds",
        "http_port",
        "absolute_output_root",
        "http_connect_timeout_seconds",
        "http_total_timeout_seconds",
        "vlp32c_destination_ipv4",
        "vlp32c_measurement_destination_udp_port",
        "vlp32c_position_destination_udp_port",
        "vlp32c_destination_configuration_verified",
        "declared_before_execution",
    ]

    channels = [
        {
            "id":
                "measurement_udp",

            "display_name":
                "Measurement UDP",

            "protocol":
                "UDP",

            "purpose":
                "VLP-32C measurement datagrams",

            "bind_value_source":
                "bind_ipv4",

            "endpoint_value_source":
                "measurement_udp_port",

            "real_endpoint_available":
                False,

            "execution_state":
                "not_executed",

            "real_sensor_evidence_available":
                False,
        },

        {
            "id":
                "position_udp",

            "display_name":
                "Position UDP",

            "protocol":
                "UDP",

            "purpose":
                "VLP-32C position datagrams",

            "bind_value_source":
                "bind_ipv4",

            "endpoint_value_source":
                "position_udp_port",

            "real_endpoint_available":
                False,

            "execution_state":
                "not_executed",

            "real_sensor_evidence_available":
                False,
        },

        {
            "id":
                "identity_http",

            "display_name":
                "Identity HTTP",

            "protocol":
                "HTTP GET",

            "purpose":
                "Sensor identity evidence",

            "path":
                "/cgi/info.json",

            "real_endpoint_available":
                False,

            "execution_state":
                "not_executed",

            "real_sensor_evidence_available":
                False,
        },

        {
            "id":
                "status_http",

            "display_name":
                "Status HTTP",

            "protocol":
                "HTTP GET",

            "purpose":
                "Sensor status evidence",

            "path":
                "/cgi/status.json",

            "real_endpoint_available":
                False,

            "execution_state":
                "not_executed",

            "real_sensor_evidence_available":
                False,
        },

        {
            "id":
                "diagnostic_http",

            "display_name":
                "Diagnostic HTTP",

            "protocol":
                "HTTP GET",

            "purpose":
                "Sensor diagnostic evidence",

            "path":
                "/cgi/diag.json",

            "real_endpoint_available":
                False,

            "execution_state":
                "not_executed",

            "real_sensor_evidence_available":
                False,
        },
    ]

    lifecycle = [
        {
            "id":
                "runtime_binding",

            "display_name":
                "Real runtime binding",

            "state":
                "waiting",

            "evidence_available":
                False,
        },

        {
            "id":
                "grounded_authorization",

            "display_name":
                "Grounded authorization",

            "state":
                "waiting",

            "evidence_available":
                False,
        },

        {
            "id":
                "udp_capture",

            "display_name":
                "UDP capture",

            "state":
                "not_executed",

            "evidence_available":
                False,
        },

        {
            "id":
                "identity_http",

            "display_name":
                "Identity read",

            "state":
                "not_executed",

            "evidence_available":
                False,
        },

        {
            "id":
                "status_http",

            "display_name":
                "Status read",

            "state":
                "not_executed",

            "evidence_available":
                False,
        },

        {
            "id":
                "diagnostic_http",

            "display_name":
                "Diagnostic read",

            "state":
                "not_executed",

            "evidence_available":
                False,
        },

        {
            "id":
                "composite_receipt",

            "display_name":
                "Composite evidence receipt",

            "state":
                "not_executed",

            "evidence_available":
                False,
        },
    ]

    return {
        "mode":
            "software_only",

        "workspace_kind":
            "future_real_sensor_observability",

        "live_real_runtime_activated":
            False,

        "real_sensor_connection_state":
            "not_executed",

        "real_sensor_connected":
            False,

        "real_network_IO_executed":
            science[
                "real_sensor_network_IO_executed"
            ],

        "real_sensor_contact":
            science[
                "real_sensor_contact"
            ],

        "session": {
            "real_session_started":
                False,

            "real_session_id":
                None,

            "real_session_id_state":
                "unavailable",

            "reason":
                "no_real_sensor_session_executed",
        },

        "runtime_binding": {
            "required_field_count":
                len(
                    required_binding_fields
                ),

            "required_fields":
                required_binding_fields,

            "real_bound_field_count":
                0,

            "values_available":
                False,

            "state":
                "awaiting_external_real_values",
        },

        "authorization": {
            "real_execution_authorization_count":
                science[
                    "real_execution_authorization_count"
                ],

            "grounded_authorization_record_count":
                science[
                    "grounded_authorization_record_count"
                ],

            "authorization_available":
                False,

            "state":
                "awaiting_grounded_authorization",
        },

        "channels":
            channels,

        "lifecycle":
            lifecycle,

        "synthetic_qualification": {
            "qualified":
                True,

            "execution_order":
                live[
                    "execution_order"
                ],

            "UDP_receipt_produced":
                live[
                    "synthetic_UDP_receipt_produced"
                ],

            "identity_receipt_produced":
                live[
                    "synthetic_HTTP_identity_receipt_produced"
                ],

            "status_receipt_produced":
                live[
                    "synthetic_HTTP_status_receipt_produced"
                ],

            "diagnostic_receipt_produced":
                live[
                    "synthetic_HTTP_diagnostic_receipt_produced"
                ],

            "composite_receipt_produced":
                live[
                    "synthetic_composite_receipt_produced"
                ],

            "real_sensor_evidence":
                False,
        },

        "controls": {
            "execute_real_sensor":
                False,

            "edit_runtime_binding":
                False,

            "create_authorization":
                False,

            "create_health_label":
                False,

            "modify_scientific_parameters":
                False,
        },
    }


def _scientific_projection(
    freeze: Mapping[str, Any],
) -> dict[str, object]:
    science = dict(
        freeze[
            "scientific_boundary"
        ]
    )

    guards = freeze[
        "training_and_stage_guards"
    ]

    return {
        **science,

        "SE2_health_model_training_blocked":
            guards[
                "SE2_health_model_training_blocked"
            ],

        "SE4_training_execution_blocked":
            guards[
                "SE4_training_execution_blocked"
            ],

        "SE5_entry_blocked":
            guards[
                "SE5_entry_blocked"
            ],

        "health_label_generated":
            guards[
                "health_label_generated"
            ],

        "dashboard_may_override_boundary":
            False,
    }


def _dashboard_policy_projection(
    software_plan: Mapping[str, Any],
) -> dict[str, object]:
    boundary = software_plan.get(
        "dashboard_boundary"
    )

    if not isinstance(
        boundary,
        Mapping,
    ):
        raise DashboardStateError(
            "software evidence plan lacks dashboard_boundary"
        )

    expected = {
        "dashboard_may_display_only_real_or_explicitly_unavailable_values":
            True,

        "dashboard_may_modify_frozen_thresholds_or_calibration":
            False,

        "dashboard_may_select_scientific_parameters":
            False,

        "dashboard_work_begins_after_real_runtime_outputs_exist":
            True,
    }

    for key, value in expected.items():
        if boundary.get(
            key
        ) is not value:
            raise DashboardStateError(
                f"frozen dashboard boundary changed: {key}"
            )

    return {
        "frozen_legacy_boundary":
            dict(
                boundary
            ),

        "current_UI_program_scope": {
            "software_only_evidence_shell":
                True,

            "live_runtime_activation":
                False,

            "claims_real_runtime_dashboard":
                False,

            "future_real_runtime_adapter_reserved":
                True,
        },

        "dashboard_write_capability":
            False,

        "dashboard_scientific_parameter_selection":
            False,

        "dashboard_threshold_or_calibration_modification":
            False,
    }


def build_dashboard_snapshot(
    repo_root: str | Path,
) -> dict[str, object]:
    root = Path(
        repo_root
    ).resolve()

    if not root.is_dir():
        raise DashboardStateError(
            "repo_root must resolve to an existing directory"
        )

    freeze_path = (
        root
        / E2E_FREEZE_RELATIVE
    )

    split_path = (
        root
        / SPLIT_MANIFEST_RELATIVE
    )

    if file_sha256(
        freeze_path
    ) != EXPECTED_E2E_FREEZE_SHA256:
        raise DashboardStateError(
            "software-only E2E freeze differs from dashboard source contract"
        )

    if file_sha256(
        split_path
    ) != EXPECTED_SPLIT_MANIFEST_SHA256:
        raise DashboardStateError(
            "split manifest differs from dashboard source contract"
        )

    freeze = _load_json(
        freeze_path
    )

    split_manifest = _load_json(
        split_path
    )

    software_plan = _load_json(
        root
        / SOFTWARE_PLAN_RELATIVE
    )

    if freeze.get(
        "schema"
    ) != (
        "TRUST_ROBOT_SE4_SOFTWARE_ONLY_END_TO_END_QUALIFICATION_FREEZE_V1"
    ):
        raise DashboardStateError(
            "unexpected software-only E2E freeze schema"
        )

    conclusion = freeze[
        "qualification_conclusion"
    ]

    if conclusion[
        "software_level_qualification_passed"
    ] is not True:
        raise DashboardStateError(
            "dashboard cannot claim software qualification without evidence"
        )

    real = freeze[
        "real_data_lane"
    ]

    snapshot: dict[str, object] = {
        "schema":
            SNAPSHOT_SCHEMA,

        "api_version":
            API_VERSION,

        "frontend_program_id":
            FRONTEND_PROGRAM_ID,

        "read_only":
            True,

        "overview": {
            "system_name":
                "TRUST-ROBOT",

            "mode":
                "software_only",

            "software_level_end_to_end_qualification":
                "passed",

            "current_scientific_frontier":
                "SE4_training_blocked_pending_accepted_health_supervision",

            "representative_real_data_trajectory":
                real[
                    "representative_trajectory"
                ],

            "real_stream_count":
                real[
                    "real_stream_count"
                ],

            "bounded_replay_message_count":
                real[
                    "bounded_replay_message_count"
                ],

            "bounded_replay_digest_sha256":
                real[
                    "bounded_replay_digest_sha256"
                ],

            "bounded_replay_deterministic":
                real[
                    "bounded_replay_deterministic"
                ],

            "physical_or_health_evidence_fabricated":
                conclusion[
                    "physical_or_health_evidence_fabricated"
                ],

            "proves_real_sensor_operation":
                conclusion[
                    "proves_real_sensor_operation"
                ],

            "proves_health_model":
                conclusion[
                    "proves_health_model"
                ],
        },

        "repository":
            _git_metadata(
                root
            ),

        "dataset":
            _split_projection(
                split_manifest
            ),

        "replay": {
            "split":
                real[
                    "split"
                ],

            "trajectory_id":
                real[
                    "representative_trajectory"
                ],

            "bag_relative_path":
                real[
                    "bag_relative_path"
                ],

            "bag_file_size_bytes":
                real[
                    "bag_file_size_bytes"
                ],

            "bounded_replay_message_count":
                real[
                    "bounded_replay_message_count"
                ],

            "bounded_replay_digest_sha256":
                real[
                    "bounded_replay_digest_sha256"
                ],

            "bounded_replay_deterministic":
                real[
                    "bounded_replay_deterministic"
                ],

            "real_stream_count":
                real[
                    "real_stream_count"
                ],

            "real_stream_ids":
                list(
                    real[
                        "real_stream_ids"
                    ]
                ),

            "reference_trajectory_accessed":
                freeze[
                    "scientific_boundary"
                ][
                    "reference_trajectory_accessed"
                ],

            "ATE_RPE_computed":
                freeze[
                    "scientific_boundary"
                ][
                    "ATE_RPE_computed"
                ],
        },

        "features":
            _feature_projection(
                freeze
            ),

        "acquisition":
            _acquisition_projection(
                freeze
            ),

        "operations":
            _operations_projection(
                freeze
            ),

        "receipts":
            _receipt_projection(
                freeze
            ),

        "health_supervision":
            _health_supervision_projection(
                freeze
            ),

        "session_history":
            _session_history_projection(
                freeze
            ),

        "scientific_boundary":
            _scientific_projection(
                freeze
            ),

        "dashboard_policy":
            _dashboard_policy_projection(
                software_plan
            ),

        "evidence": {
            "sources": [
                _source_record(
                    root,
                    E2E_FREEZE_RELATIVE,
                ),
                _source_record(
                    root,
                    SPLIT_MANIFEST_RELATIVE,
                ),
                _source_record(
                    root,
                    SOFTWARE_PLAN_RELATIVE,
                ),
                _source_record(
                    root,
                    HEALTH_RESOLUTION_RELATIVE,
                ),
                _source_record(
                    root,
                    RUNTIME_BINDING_RELATIVE,
                ),
            ],

            "all_values_traceable_to_repository_evidence":
                True,

            "runtime_sensor_evidence_available":
                False,

            "accepted_health_supervision_available":
                False,
        },

        "capabilities": {
            "view_project_state":
                True,

            "view_dataset_splits":
                True,

            "view_real_feature_observations":
                True,

            "view_synthetic_live_stack_qualification":
                True,

            "view_evidence_hashes":
                True,

            "view_scientific_blockers":
                True,

            "execute_real_sensor_acquisition":
                False,

            "create_execution_authorization":
                False,

            "create_health_labels":
                False,

            "open_validation":
                False,

            "open_confirmation":
                False,

            "run_ATE_RPE":
                False,

            "modify_scientific_parameters":
                False,
        },
    }

    snapshot[
        "content_sha256"
    ] = content_sha256(
        snapshot
    )

    return snapshot


def validate_dashboard_snapshot(
    snapshot: Mapping[str, object],
) -> Mapping[str, object]:
    if snapshot.get(
        "schema"
    ) != SNAPSHOT_SCHEMA:
        raise DashboardStateError(
            "dashboard snapshot schema mismatch"
        )

    if snapshot.get(
        "read_only"
    ) is not True:
        raise DashboardStateError(
            "dashboard snapshot must be read-only"
        )

    if content_sha256(
        snapshot
    ) != snapshot.get(
        "content_sha256"
    ):
        raise DashboardStateError(
            "dashboard snapshot content digest mismatch"
        )

    capabilities = snapshot.get(
        "capabilities"
    )

    if not isinstance(
        capabilities,
        Mapping,
    ):
        raise DashboardStateError(
            "dashboard capabilities missing"
        )

    prohibited = (
        "execute_real_sensor_acquisition",
        "create_execution_authorization",
        "create_health_labels",
        "open_validation",
        "open_confirmation",
        "run_ATE_RPE",
        "modify_scientific_parameters",
    )

    for capability in prohibited:
        if capabilities.get(
            capability
        ) is not False:
            raise DashboardStateError(
                f"prohibited dashboard capability opened: {capability}"
            )

    return snapshot
