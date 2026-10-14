"""TRUST-ROBOT cross-workstation source boundary V1.

Distinguishes historically verified real M2DGR TRAIN
evidence from synthetic Isaac Sim V15 evidence.

This is a checkpoint-specific, fail-closed provenance
review. It is NOT permission to execute physical fusion,
train a health classifier, open held-out data, or interpret
synthetic calibration as physical calibration.
"""

from __future__ import annotations

import json
from typing import Mapping


SCHEMA = "TRUST_ROBOT_DUAL_WORKSTATION_SOURCE_BOUNDARY_V1"


class SourceBoundaryError(ValueError):
    pass


def require(condition, explanation):
    if not condition:
        raise SourceBoundaryError(explanation)


def review_source_boundary(
    train_config: Mapping,
    train_evidence: Mapping,
    se3_freeze: Mapping,
    se2_freeze: Mapping,
    se4_freeze: Mapping,
    calibration: Mapping,
    simulation: Mapping,
):
    """Review already-frozen evidence; never open datasets."""

    require(
        train_config.get("split_role") == "train",
        "TRAIN partition is not frozen",
    )

    train_ids = train_config.get(
        "train_trajectories"
    )

    require(
        isinstance(train_ids, list)
        and len(train_ids) == 22
        and len(set(train_ids)) == 22
        and all(isinstance(x, str) for x in train_ids),
        "Unexpected real TRAIN population",
    )

    population = train_evidence.get(
        "train_population", {}
    )

    require(
        population.get("split_role") == "train"
        and population.get("trajectory_count") == 22
        and population.get("trajectory_ids") == train_ids,
        "Real TRAIN source population does not match",
    )

    require(
        population.get("validation_data_used") is False
        and population.get("confirmation_data_used") is False,
        "Unqualified TRAIN partition provenance",
    )

    totals = train_evidence.get(
        "ingestion_totals", {}
    )

    require(
        totals.get("selected_stream_messages") == 2816957
        and totals.get("selected_serialized_payload_bytes")
            == 4320203720,
        "Real TRAIN ingestion totals differ",
    )

    empirical = se3_freeze.get(
        "empirical_train_validation", {}
    )

    require(
        se3_freeze.get("stage", {}).get("stage_id")
            == "SE3"
        and empirical.get("train_trajectory_count") == 22
        and empirical.get("total_feature_records")
            == 2816957
        and empirical.get("camera_feature_records")
            == 107675
        and empirical.get("D435i_IMU_feature_records")
            == 1404805
        and empirical.get("HandsFree_IMU_feature_records")
            == 1304477,
        "SE3 real TRAIN feature evidence differs",
    )

    require(
        empirical.get("all_feature_file_hashes_verified")
            is True
        and empirical.get("all_JSONL_line_counts_verified")
            is True
        and empirical.get("all_feature_records_finite")
            is True,
        "Previously frozen SE3 validation is incomplete",
    )

    binding = se3_freeze.get(
        "source_bindings", {}
    ).get(
        "phase5_camera_imu_train_source_evidence", {}
    )

    require(
        binding.get("content_sha256")
        == train_evidence.get("content_sha256"),
        "Real source evidence does not match SE3 binding",
    )

    execution = se3_freeze.get(
        "execution_status", {}
    )

    require(
        execution.get("cross_modal_alignment_executed")
            is False
        and execution.get("health_label_assignment_executed")
            is False
        and execution.get("model_training_executed")
            is False
        and execution.get("validation_access") is False
        and execution.get("confirmation_access") is False,
        "Historical SE3 execution boundary changed",
    )

    readiness = se2_freeze.get(
        "current_empirical_readiness", {}
    )

    require(
        readiness.get(
            "accepted_baseline_nominality_source_count"
        ) == 0
        and readiness.get(
            "accepted_health_supervision_source_count"
        ) == 0
        and readiness.get("real_health_label_count") == 0
        and readiness.get(
            "empirical_health_supervision_available"
        ) is False
        and readiness.get(
            "health_label_generation_authorized"
        ) is False,
        "Existing SE2 health-supervision blocker changed",
    )

    model = se4_freeze.get(
        "model_state", {}
    )

    require(
        se4_freeze.get("stage", {}).get("SE4_complete")
            is False
        and model.get("classifier_training_authorized")
            is False
        and model.get("model_training_executed")
            is False
        and model.get("health_probability_output_enabled")
            is False
        and model.get("health_inference_authorized")
            is False,
        "Existing SE4 blocked frontier changed",
    )

    require(
        calibration.get("policy", {}).get(
            "dataset_calibration_verified"
        ) is False
        and calibration.get("interpretation", {}).get(
            "camera_intrinsics_verified"
        ) is False
        and calibration.get("interpretation", {}).get(
            "camera_lidar_extrinsic_verified"
        ) is False,
        "Physical calibration evidence was promoted",
    )

    require(
        simulation.get("schema")
        == "TRUST_ROBOT_ISAACSIM_V15_COMPACT_EVIDENCE_V1"
        and simulation.get("source_origin")
            == "FIRST_PARTY_SIMPLIFIED_PROXY"
        and simulation.get("data_origin") == "SYNTHETIC"
        and simulation.get("camera_frames") == 6
        and simulation.get("lidar_scans") == 6
        and simulation.get("imu_records") == 90,
        "Simulation source has lost its synthetic identity",
    )

    return {
        "schema": SCHEMA,
        "status": "TWO_SOURCE_PROVENANCE_BOUND",
        "real_train_source": {
            "role": "VERONA_REAL_RECORDED_TRAIN",
            "source_class": "REAL_DATASET_RECORDING",
            "trajectory_count": 22,
            "frozen_feature_records": 2816957,
            "frozen_camera_records": 107675,
            "frozen_d435i_imu_records": 1404805,
            "frozen_handsfree_imu_records": 1304477,
            "historical_receipts_qualified": True,
            "current_raw_bag_contents_rehashed": False,
            "physical_camera_calibration_verified": False,
            "cross_sensor_capture_time_verified": False,
            "health_labels_available": False,
        },
        "simulation_source": {
            "role": "KIOS_SIMULATION_DEVELOPMENT",
            "source_class": "ISAAC_SIM_SYNTHETIC",
            "source_origin": simulation["source_origin"],
            "camera_frame_count": 6,
            "lidar_scan_count": 6,
            "imu_record_count": 90,
            "physical_sensor_capture": False,
            "physical_calibration_verified": False,
            "metric_real_camera_factor_authorized": False,
        },
        "authorization": {
            "real_health_model_training": False,
            "health_probability_inference": False,
            "physical_camera_factor_fusion": False,
            "simulation_as_real_training_evidence": False,
            "validation_partition_access": False,
            "confirmation_partition_access": False,
            "independent_reference_scoring": False,
            "automatic_health_label_generation": False,
        },
        "source_separation_enforced": True,
        "raw_bag_payloads_opened": False,
        "feature_jsonl_payloads_opened": False,
        "simulator_launched": False,
        "robot_contact_performed": False,
        "scientific_thresholds_selected": False,
        "checkpoint_specific_review_only": True,
    }


def require_physical_factor_authorization(result):
    raise SourceBoundaryError(
        "The current frozen source evidence does not "
        "authorize physical camera factors or metric fusion"
    )


def require_health_training_authorization(result):
    raise SourceBoundaryError(
        "The current frozen SE2/SE4 evidence does not "
        "authorize supervised sensor-health training"
    )


def canonical(value):
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ) + "\n"
    ).encode("utf-8")
