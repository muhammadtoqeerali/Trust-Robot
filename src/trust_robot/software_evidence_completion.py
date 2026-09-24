"""TRUST-ROBOT software evidence completion governance.

This track converts the already-frozen Phase-5 through Phase-14 software
architecture into empirical software evidence before physical hardware
integration and before final confirmation.

It does not itself select scientific parameters or execute experiments.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping


SCHEMA = "TRUST_ROBOT_SOFTWARE_EVIDENCE_COMPLETION_PLAN_V1"


class EvidencePlanError(ValueError):
    """Raised when the software-evidence governance contract is violated."""


class PartitionRole(str, Enum):
    TRAIN = "train"
    VALIDATION = "validation_calibration"
    CONFIRMATION = "confirmation_test"


class StageId(str, Enum):
    SE0 = "SE0"
    SE1 = "SE1"
    SE2 = "SE2"
    SE3 = "SE3"
    SE4 = "SE4"
    SE5 = "SE5"
    SE6 = "SE6"
    SE7 = "SE7"
    SE8 = "SE8"
    SE9 = "SE9"
    SE10 = "SE10"


STAGE_ORDER = tuple(
    stage.value
    for stage in StageId
)


TRAIN_TRAJECTORIES = (
    "Circle_01",
    "door_01",
    "gate_01",
    "hall_01",
    "hall_03",
    "hall_04",
    "hall_05",
    "lift_02",
    "lift_04",
    "room_02",
    "room_dark_01",
    "room_dark_02",
    "room_dark_03",
    "room_dark_04",
    "street_01",
    "street_010",
    "street_03",
    "street_04",
    "street_05",
    "street_07",
    "street_09",
    "walk_01",
)


VALIDATION_TRAJECTORIES = (
    "door_02",
    "gate_03",
    "lift_03",
    "room_03",
    "room_dark_06",
    "street_02",
    "street_08",
)


CONFIRMATION_TRAJECTORIES = (
    "Circle_02",
    "gate_02",
    "hall_02",
    "lift_01",
    "room_01",
    "room_dark_05",
    "street_06",
)


@dataclass(frozen=True)
class StageDefinition:
    stage_id: str
    name: str
    purpose: str
    current_status: str
    train_access: bool
    validation_access: bool
    confirmation_access: bool
    executes_model_training: bool
    executes_parameter_selection: bool
    executes_final_confirmation: bool


STAGES = (
    StageDefinition(
        stage_id="SE0",
        name="scientific_readiness_and_plan_freeze",
        purpose=(
            "Reconcile proposal, frozen phases, split roles, empirical debt, "
            "and software-evidence sequencing."
        ),
        current_status="active_plan_freeze",
        train_access=False,
        validation_access=False,
        confirmation_access=False,
        executes_model_training=False,
        executes_parameter_selection=False,
        executes_final_confirmation=False,
    ),
    StageDefinition(
        stage_id="SE1",
        name="deterministic_multimodal_dataset_replay",
        purpose=(
            "Build deterministic recorded-dataset virtual-sensor replay with "
            "trajectory, partition, provenance, and lineage enforcement."
        ),
        current_status="next_after_se0_checkpoint",
        train_access=True,
        validation_access=False,
        confirmation_access=False,
        executes_model_training=False,
        executes_parameter_selection=False,
        executes_final_confirmation=False,
    ),
    StageDefinition(
        stage_id="SE2",
        name="health_supervision_protocol",
        purpose=(
            "Resolve admissible healthy/degraded/unusable supervision without "
            "equating availability, final localization error, or corruption "
            "identity with a health label."
        ),
        current_status="blocked_until_scientific_supervision_resolution",
        train_access=True,
        validation_access=False,
        confirmation_access=False,
        executes_model_training=False,
        executes_parameter_selection=False,
        executes_final_confirmation=False,
    ),
    StageDefinition(
        stage_id="SE3",
        name="multimodal_feature_pipeline",
        purpose=(
            "Preserve the frozen LiDAR feature contract and prospectively "
            "resolve reproducible camera and IMU diagnostic feature contracts."
        ),
        current_status="partially_ready",
        train_access=True,
        validation_access=False,
        confirmation_access=False,
        executes_model_training=False,
        executes_parameter_selection=False,
        executes_final_confirmation=False,
    ),
    StageDefinition(
        stage_id="SE4",
        name="health_model_training",
        purpose=(
            "Train the actual modality-health model using admissible TRAIN "
            "evidence and leakage-safe trajectory grouping."
        ),
        current_status="blocked_until_se2_and_se3_complete",
        train_access=True,
        validation_access=False,
        confirmation_access=False,
        executes_model_training=True,
        executes_parameter_selection=False,
        executes_final_confirmation=False,
    ),
    StageDefinition(
        stage_id="SE5",
        name="validation_selection_and_probability_calibration",
        purpose=(
            "Use validation/calibration only for choices explicitly authorized "
            "by the frozen scientific protocol, including permitted model, "
            "calibration, threshold, and operating-point decisions."
        ),
        current_status="blocked_until_frozen_train_outputs_exist",
        train_access=True,
        validation_access=True,
        confirmation_access=False,
        executes_model_training=False,
        executes_parameter_selection=True,
        executes_final_confirmation=False,
    ),
    StageDefinition(
        stage_id="SE6",
        name="end_to_end_runtime_assembly",
        purpose=(
            "Connect trained health inference, calibration, auxiliary "
            "consistency, factor conditioning, suppression/recovery/status, "
            "and supervisory shadow outputs under frozen upstream choices."
        ),
        current_status="blocked_until_required_numeric_evidence_is_frozen",
        train_access=True,
        validation_access=True,
        confirmation_access=False,
        executes_model_training=False,
        executes_parameter_selection=False,
        executes_final_confirmation=False,
    ),
    StageDefinition(
        stage_id="SE7",
        name="controlled_fault_attack_and_ablation_evaluation",
        purpose=(
            "Execute prospectively frozen controlled faults, causal ablations, "
            "and threat-model-bounded software attacks for RQ1/RQ2/RQ3."
        ),
        current_status="frameworks_exist_protocol_resolution_required",
        train_access=True,
        validation_access=True,
        confirmation_access=False,
        executes_model_training=False,
        executes_parameter_selection=False,
        executes_final_confirmation=False,
    ),
    StageDefinition(
        stage_id="SE8",
        name="localization_cross_dataset_and_resource_evaluation",
        purpose=(
            "Complete scientifically authorized localization evaluation, "
            "compatible cross-dataset stress testing, and software-level "
            "resource profiling without inventing missing physical facts."
        ),
        current_status="partially_ready_with_independent_blockers",
        train_access=True,
        validation_access=True,
        confirmation_access=False,
        executes_model_training=False,
        executes_parameter_selection=False,
        executes_final_confirmation=False,
    ),
    StageDefinition(
        stage_id="SE9",
        name="frozen_software_confirmation",
        purpose=(
            "Open the prospectively held-out software confirmation partition "
            "only after every permitted upstream choice and evaluation rule "
            "has been frozen."
        ),
        current_status="closed",
        train_access=False,
        validation_access=False,
        confirmation_access=False,
        executes_model_training=False,
        executes_parameter_selection=False,
        executes_final_confirmation=False,
    ),
    StageDefinition(
        stage_id="SE10",
        name="dashboard_and_reproducibility_package",
        purpose=(
            "Package real frozen outputs, provenance, model details, metrics, "
            "status histories, and experiment evidence for GitHub/Vercel "
            "presentation without altering scientific decisions."
        ),
        current_status="deferred_until_real_runtime_outputs_exist",
        train_access=False,
        validation_access=False,
        confirmation_access=False,
        executes_model_training=False,
        executes_parameter_selection=False,
        executes_final_confirmation=False,
    ),
)


def stage_ids() -> tuple[str, ...]:
    return STAGE_ORDER


def stage_definition(stage_id: str) -> StageDefinition:
    for stage in STAGES:
        if stage.stage_id == stage_id:
            return stage

    raise EvidencePlanError(
        f"unknown software-evidence stage: {stage_id}"
    )


def validate_disjoint_split() -> None:
    train = set(TRAIN_TRAJECTORIES)
    validation = set(VALIDATION_TRAJECTORIES)
    confirmation = set(CONFIRMATION_TRAJECTORIES)

    if len(train) != 22:
        raise EvidencePlanError("TRAIN count changed")

    if len(validation) != 7:
        raise EvidencePlanError("VALIDATION count changed")

    if len(confirmation) != 7:
        raise EvidencePlanError("CONFIRMATION count changed")

    if train & validation:
        raise EvidencePlanError("TRAIN/VALIDATION overlap")

    if train & confirmation:
        raise EvidencePlanError("TRAIN/CONFIRMATION overlap")

    if validation & confirmation:
        raise EvidencePlanError("VALIDATION/CONFIRMATION overlap")

    if len(
        train
        | validation
        | confirmation
    ) != 36:
        raise EvidencePlanError(
            "unexpected total M2DGR trajectory count"
        )


def assert_confirmation_selection_forbidden() -> None:
    raise EvidencePlanError(
        "confirmation_test may not be used for feature, model, calibration, "
        "threshold, fault/attack operating-point, or evaluation-protocol "
        "selection"
    )


def assert_confirmation_execution_authorized() -> None:
    raise EvidencePlanError(
        "SE9 confirmation execution is currently closed"
    )


def assert_ate_rpe_authorized() -> None:
    raise EvidencePlanError(
        "ATE/RPE are currently unauthorized because the evaluator protocol "
        "is not yet evaluation-ready"
    )


def build_plan_manifest(
    *,
    baseline_head: str,
    baseline_tree: str,
    project_state_sha256: str,
    master_context_sha256: str,
    phase_plan_sha256: str,
    data_protocol_sha256: str,
    split_manifest_sha256: str,
    split_evidence_sha256: str,
    evaluator_protocol_sha256: str,
    phase14_freeze_sha256: str,
    se0_report_sha256: str,
    se0_json_sha256: str,
) -> dict[str, Any]:
    validate_disjoint_split()

    return {
        "schema":
            SCHEMA,

        "track":
            "software_evidence_completion",

        "objective":
            (
                "Complete the empirically deferred software obligations from "
                "Phases 5 through 14 using recorded datasets as virtual "
                "sensors, while preserving the frozen train/validation/"
                "confirmation split and preventing confirmation leakage."
            ),

        "baseline": {
            "commit":
                baseline_head,

            "tree":
                baseline_tree,

            "trust_robot_test_count":
                1400,

            "phase5_through_phase14_software_architecture_frozen":
                True,
        },

        "partition_contract": {
            "train_role":
                PartitionRole.TRAIN.value,

            "validation_role":
                PartitionRole.VALIDATION.value,

            "confirmation_role":
                PartitionRole.CONFIRMATION.value,

            "train_trajectories":
                list(TRAIN_TRAJECTORIES),

            "validation_trajectories":
                list(VALIDATION_TRAJECTORIES),

            "confirmation_trajectories":
                list(CONFIRMATION_TRAJECTORIES),

            "train_count":
                22,

            "validation_count":
                7,

            "confirmation_count":
                7,

            "trajectory_disjoint":
                True,

            "all_clean_and_corrupt_derivatives_stay_with_base_trajectory":
                True,

            "corruption_seeds_may_be_reused_across_partitions":
                False,

            "reference_stream_may_be_estimator_input_when_used_as_ground_truth_without_independent_instance":
                False,
        },

        "selection_contract": {
            "train_for_model_construction":
                True,

            "train_internal_grouped_selection_may_be_defined_where_scientifically_authorized":
                True,

            "validation_for_authorized_selection_only":
                True,

            "validation_access_before_authorized_stage":
                False,

            "confirmation_for_selection":
                False,

            "confirmation_may_select_features":
                False,

            "confirmation_may_select_model":
                False,

            "confirmation_may_select_calibration":
                False,

            "confirmation_may_select_thresholds":
                False,

            "confirmation_may_select_fault_severity":
                False,

            "confirmation_may_select_attack_budget":
                False,

            "confirmation_may_select_association":
                False,

            "confirmation_may_select_alignment":
                False,

            "confirmation_may_select_interpolation":
                False,

            "confirmation_may_select_evaluation_interval":
                False,

            "confirmation_may_select_metric_operating_choices":
                False,
        },

        "health_supervision_boundary": {
            "availability_is_health_label":
                False,

            "missing_measurement_is_zero_feature_vector":
                False,

            "clean_dataset_branch_automatically_means_healthy":
                False,

            "synthetic_corruption_identity_automatically_means_health_label":
                False,

            "final_localization_error_may_define_health_label":
                False,

            "health_labels_must_be_independent_from_final_localization_error":
                True,
        },

        "current_evaluator_boundary": {
            "evaluation_ready":
                False,

            "association_selected":
                False,

            "association_tolerance_frozen":
                False,

            "interpolation_selected":
                False,

            "alignment_selected":
                False,

            "reference_frame_semantics_verified":
                False,

            "metric_computation_authorized":
                False,

            "trajectory_scoring_authorized":
                False,

            "ate_rpe_authorized":
                False,

            "final_scoring_authorized":
                False,
        },

        "stage_order":
            list(
                stage_ids()
            ),

        "stages": [
            {
                "stage_id":
                    stage.stage_id,

                "name":
                    stage.name,

                "purpose":
                    stage.purpose,

                "current_status":
                    stage.current_status,

                "train_access":
                    stage.train_access,

                "validation_access":
                    stage.validation_access,

                "confirmation_access":
                    stage.confirmation_access,

                "executes_model_training":
                    stage.executes_model_training,

                "executes_parameter_selection":
                    stage.executes_parameter_selection,

                "executes_final_confirmation":
                    stage.executes_final_confirmation,
            }
            for stage in STAGES
        ],

        "current_track_state": {
            "current_stage":
                "SE0",

            "next_stage_after_se0_checkpoint":
                "SE1",

            "model_training_executed":
                False,

            "validation_selection_executed":
                False,

            "probability_calibration_executed":
                False,

            "threshold_selection_executed":
                False,

            "end_to_end_numeric_pipeline_executed":
                False,

            "fault_ablation_experiments_executed":
                False,

            "attack_experiments_executed":
                False,

            "cross_dataset_evaluation_executed":
                False,

            "resource_benchmark_executed":
                False,

            "confirmation_opened":
                False,

            "confirmation_execution_authorized":
                False,

            "ate_rpe_computed":
                False,

            "final_score_computed":
                False,

            "physical_hardware_required_before_SE1":
                False,
        },

        "SE1_entry_gate": {
            "recorded_dataset_root_present":
                True,

            "m2dgr_split_frozen":
                True,

            "phase4_real_lidar_diagnostics_present":
                True,

            "phase5_real_camera_imu_ingestion_present":
                True,

            "phase5_through_phase14_architecture_frozen":
                True,

            "confirmation_closed":
                True,

            "SE1_may_execute_on_train_partition":
                True,

            "SE1_may_open_validation":
                False,

            "SE1_may_open_confirmation":
                False,

            "SE1_may_train_health_model":
                False,

            "SE1_may_select_scientific_thresholds":
                False,

            "SE1_may_compute_final_localization_scores":
                False,
        },

        "SE9_opening_gate": {
            "currently_open":
                False,

            "requires_feature_contracts_frozen":
                True,

            "requires_health_supervision_protocol_frozen":
                True,

            "requires_model_training_complete":
                True,

            "requires_model_selection_complete":
                True,

            "requires_probability_calibration_complete":
                True,

            "requires_thresholds_and_operating_points_frozen":
                True,

            "requires_fault_protocols_frozen":
                True,

            "requires_attack_protocols_frozen":
                True,

            "requires_evaluator_protocol_frozen_for_claimed_metrics":
                True,

            "requires_all_confirmation_visible_choices_frozen":
                True,

            "confirmation_may_reopen_selection_after_results":
                False,
        },

        "hardware_boundary": {
            "software_evidence_track_requires_hardware_to_begin":
                False,

            "recorded_datasets_are_virtual_sensor_inputs":
                True,

            "software_success_equals_physical_hardware_validation":
                False,

            "later_hardware_integration_should_reuse_core_pipeline":
                True,

            "physical_sensor_or_robot_claims_authorized":
                False,
        },

        "dashboard_boundary": {
            "target":
                "github_plus_vercel",

            "dashboard_may_display_only_real_or_explicitly_unavailable_values":
                True,

            "dashboard_may_select_scientific_parameters":
                False,

            "dashboard_may_modify_frozen_thresholds_or_calibration":
                False,

            "dashboard_work_begins_after_real_runtime_outputs_exist":
                True,
        },

        "source_bindings": {
            "project_state_sha256":
                project_state_sha256,

            "master_context_sha256":
                master_context_sha256,

            "phase_plan_sha256":
                phase_plan_sha256,

            "data_protocol_sha256":
                data_protocol_sha256,

            "split_manifest_sha256":
                split_manifest_sha256,

            "split_evidence_sha256":
                split_evidence_sha256,

            "evaluator_protocol_v2_sha256":
                evaluator_protocol_sha256,

            "phase14_freeze_sha256":
                phase14_freeze_sha256,

            "se0_readiness_report_sha256":
                se0_report_sha256,

            "se0_readiness_json_sha256":
                se0_json_sha256,
        },
    }


def validate_plan_manifest(
    payload: Mapping[str, Any],
) -> None:
    if not isinstance(
        payload,
        Mapping,
    ):
        raise EvidencePlanError(
            "software evidence plan must be a mapping"
        )

    if payload.get(
        "schema"
    ) != SCHEMA:
        raise EvidencePlanError(
            "unexpected software evidence plan schema"
        )

    if payload[
        "track"
    ] != "software_evidence_completion":
        raise EvidencePlanError(
            "unexpected evidence track"
        )

    baseline = payload[
        "baseline"
    ]

    if baseline[
        "trust_robot_test_count"
    ] != 1400:
        raise EvidencePlanError(
            "unexpected promoted baseline test count"
        )

    if baseline[
        "phase5_through_phase14_software_architecture_frozen"
    ] is not True:
        raise EvidencePlanError(
            "Phase 5–14 freeze chain lost"
        )

    split = payload[
        "partition_contract"
    ]

    if split[
        "train_trajectories"
    ] != list(
        TRAIN_TRAJECTORIES
    ):
        raise EvidencePlanError(
            "TRAIN split changed"
        )

    if split[
        "validation_trajectories"
    ] != list(
        VALIDATION_TRAJECTORIES
    ):
        raise EvidencePlanError(
            "VALIDATION split changed"
        )

    if split[
        "confirmation_trajectories"
    ] != list(
        CONFIRMATION_TRAJECTORIES
    ):
        raise EvidencePlanError(
            "CONFIRMATION split changed"
        )

    if (
        split[
            "train_count"
        ],
        split[
            "validation_count"
        ],
        split[
            "confirmation_count"
        ],
    ) != (
        22,
        7,
        7,
    ):
        raise EvidencePlanError(
            "split counts changed"
        )

    if split[
        "trajectory_disjoint"
    ] is not True:
        raise EvidencePlanError(
            "trajectory-disjoint requirement lost"
        )

    if split[
        "corruption_seeds_may_be_reused_across_partitions"
    ] is not False:
        raise EvidencePlanError(
            "cross-partition corruption seed reuse forbidden"
        )

    validate_disjoint_split()

    selection = payload[
        "selection_contract"
    ]

    if selection[
        "train_for_model_construction"
    ] is not True:
        raise EvidencePlanError(
            "TRAIN construction role lost"
        )

    if selection[
        "validation_for_authorized_selection_only"
    ] is not True:
        raise EvidencePlanError(
            "VALIDATION role changed"
        )

    for key, value in selection.items():
        if key.startswith(
            "confirmation_"
        ) and value is not False:
            raise EvidencePlanError(
                f"{key} must remain false"
            )

    supervision = payload[
        "health_supervision_boundary"
    ]

    true_supervision = {
        "health_labels_must_be_independent_from_final_localization_error",
    }

    for key, value in supervision.items():
        if key in true_supervision:
            if value is not True:
                raise EvidencePlanError(
                    f"{key} must remain true"
                )
        elif value is not False:
            raise EvidencePlanError(
                f"{key} must remain false"
            )

    evaluator = payload[
        "current_evaluator_boundary"
    ]

    if set(
        evaluator.values()
    ) != {
        False,
    }:
        raise EvidencePlanError(
            "current evaluator gate must remain closed"
        )

    if payload[
        "stage_order"
    ] != list(
        STAGE_ORDER
    ):
        raise EvidencePlanError(
            "SE stage order changed"
        )

    stages = payload[
        "stages"
    ]

    if [
        stage[
            "stage_id"
        ]
        for stage in stages
    ] != list(
        STAGE_ORDER
    ):
        raise EvidencePlanError(
            "SE stage definitions changed order"
        )

    for stage in stages:
        if stage[
            "confirmation_access"
        ] is not False:
            raise EvidencePlanError(
                "confirmation must remain closed in the current plan"
            )

        if stage[
            "executes_final_confirmation"
        ] is not False:
            raise EvidencePlanError(
                "final confirmation is not yet authorized"
            )

    se1 = payload[
        "SE1_entry_gate"
    ]

    for key in (
        "recorded_dataset_root_present",
        "m2dgr_split_frozen",
        "phase4_real_lidar_diagnostics_present",
        "phase5_real_camera_imu_ingestion_present",
        "phase5_through_phase14_architecture_frozen",
        "confirmation_closed",
        "SE1_may_execute_on_train_partition",
    ):
        if se1[
            key
        ] is not True:
            raise EvidencePlanError(
                f"{key} must remain true"
            )

    for key in (
        "SE1_may_open_validation",
        "SE1_may_open_confirmation",
        "SE1_may_train_health_model",
        "SE1_may_select_scientific_thresholds",
        "SE1_may_compute_final_localization_scores",
    ):
        if se1[
            key
        ] is not False:
            raise EvidencePlanError(
                f"{key} must remain false"
            )

    se9 = payload[
        "SE9_opening_gate"
    ]

    if se9[
        "currently_open"
    ] is not False:
        raise EvidencePlanError(
            "SE9 must remain closed"
        )

    if se9[
        "confirmation_may_reopen_selection_after_results"
    ] is not False:
        raise EvidencePlanError(
            "confirmation cannot reopen selection"
        )

    for key, value in se9.items():
        if key.startswith(
            "requires_"
        ) and value is not True:
            raise EvidencePlanError(
                f"{key} must remain required"
            )

    hardware = payload[
        "hardware_boundary"
    ]

    if hardware[
        "software_evidence_track_requires_hardware_to_begin"
    ] is not False:
        raise EvidencePlanError(
            "software evidence track may begin without hardware"
        )

    if hardware[
        "recorded_datasets_are_virtual_sensor_inputs"
    ] is not True:
        raise EvidencePlanError(
            "virtual-sensor dataset role lost"
        )

    if hardware[
        "software_success_equals_physical_hardware_validation"
    ] is not False:
        raise EvidencePlanError(
            "software evidence cannot equal physical validation"
        )

    if hardware[
        "physical_sensor_or_robot_claims_authorized"
    ] is not False:
        raise EvidencePlanError(
            "physical claims remain unauthorized"
        )
