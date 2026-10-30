"""R135-A30-1: fail-closed Nova physical-measurement readiness.

Reuses the exact A23 independent evidence requests. It never
qualifies measurements, accepts witness receipts, opens M2DGR,
creates estimator factors or authorizes physical localization.
"""

from __future__ import annotations

from trust_robot.m2dgr_prospective_evidence_packet_v1 import (
    REQUEST_SPECS,
    SCHEMA as A23_SCHEMA,
    STATUS as A23_STATUS,
)
from trust_robot.analytic_15d_evidence_review_v1 import (
    BLOCKED_CAPABILITIES,
)

SCHEMA = "TRUST_ROBOT_R135_A30_1_MEASUREMENT_READINESS_V1"

EXPECTED_PINS = {
    "calibration_json":
        "c10abfc83037103630ae2df5c02a19b07fccbf1a81f00669649562bdbdab60fd",
    "nominal_urdf":
        "93f054d186bd90384cd1018b1d1522ff0b7a62bceb65f59a5e62d733099a14e7",
    "imu_launch":
        "b1826dde384116a83436d7c0d184e6238ebd7da58edfb1cb26d8da3bbb3ff196",
    "hawk_launch":
        "cf81ebd68c2f7d29a3e613c17deda2d7bb60f8e3e75981e5265ed0322a93b51c",
    "clock_launch":
        "e06fd8b93c6f0aa627bb0927ca4ae3925fe9e7acded2c2187782ed5b148510a8",
}

EXPECTED_STAGES = {
    "A": 2,
    "B": 6,
    "C": 3,
    "D": 2,
}


class MeasurementReadinessError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise MeasurementReadinessError(message)


def review_readiness(packet, frame, installed):
    """Review only the present closed-gate evidence state."""

    require(
        type(packet) is dict
        and packet.get("schema") == A23_SCHEMA
        and packet.get("status") == A23_STATUS,
        "A23 packet identity mismatch",
    )

    require(
        packet.get("original_m2dgr_gates_closed") == 11
        and type(packet.get("qualified_physical_receipt_count")) is int
        and packet["qualified_physical_receipt_count"] == 0,
        "Original M2DGR admission changed",
    )

    require(
        packet.get("frozen_m2dgr_split") == {
            "train": 22,
            "validation_calibration": 7,
            "confirmation_test": 7,
        }
        and packet.get(
            "confirmation_test_pristine_from_prior_inspection"
        ) is False
        and packet.get("confirmation_test_prospectively_closed") is True,
        "Frozen dataset boundary changed",
    )

    permissions = packet.get("scientific_permissions")

    require(
        type(permissions) is dict
        and set(permissions) == set(BLOCKED_CAPABILITIES)
        and all(x == "BLOCKED" for x in permissions.values()),
        "Scientific permissions altered",
    )

    requests = packet.get("requests")

    require(
        type(requests) is list
        and len(requests) == len(REQUEST_SPECS) == 13,
        "Incorrect evidence request count",
    )

    actual_ids = []

    counts = {stage: 0 for stage in EXPECTED_STAGES}

    for row in requests:
        require(type(row) is dict, "Invalid A23 request")

        ident = row.get("request_id")
        stage = row.get("stage")

        actual_ids.append(ident)

        require(stage in counts, "Unknown evidence stage")
        counts[stage] += 1

        require(
            row.get("request_status") == "UNFULFILLED"
            and row.get("independent_review_status") ==
            "NOT_YET_VERIFIED"
            and row.get("qualifying_receipt_received") is False
            and row.get("scientific_gate_opened") is False
            and row.get("evidence_artifact_sha256") is None
            and row.get("physical_parameter_value") is None,
            "A23 request unexpectedly qualified",
        )

    require(
        actual_ids == [item[0] for item in REQUEST_SPECS]
        and counts == EXPECTED_STAGES
        and all(
            row["stage"] == spec[1]
            for row, spec in zip(requests, REQUEST_SPECS)
        ),
        "Frozen A23 request identities changed",
    )

    stages = packet.get("stages")

    require(
        type(stages) is list and len(stages) == 4
        and {x.get("stage") for x in stages} ==
        set(EXPECTED_STAGES),
        "Invalid A23 stage structure",
    )

    require(
        all(
            row.get("stage_authorized") is False
            and row.get("completed_independent_receipts") == 0
            and row.get("l33_qualification") == "NOT_YET_VERIFIED"
            for row in stages
        ),
        "A23 stage qualification altered",
    )

    require(
        type(frame) is dict
        and frame.get("status") == "FRAME_IDENTITY_REVIEW_ONLY"
        and frame.get("physical_imu_frame_id") == "bmi088_frame"
        and frame.get("physical_imu_frame_in_nominal_urdf") is False
        and frame.get("bmi088_to_platform_transform") is None
        and frame.get("bmi088_to_front_stereo_imu_equivalence")
        == "UNVERIFIED"
        and frame.get("real_factor_admission") == "DENIED"
        and frame.get("m2dgr_gates") == "11_CLOSED",
        "Unqualified physical IMU mapping was altered",
    )

    require(
        type(installed) is dict
        and installed.get("schema") ==
        "TRUST_ROBOT_R135_A27_5_STATIC_SOURCE_INSPECTION_V1"
        and installed.get("status") ==
        "STATIC_PINNED_FILE_INSPECTION_ONLY"
        and installed.get("pinned_sha256") == EXPECTED_PINS
        and installed.get("urdf_links") == 37
        and installed.get("urdf_joints") == 36
        and installed.get("calibration_sensor_count") == 12,
        "Installed source inspection contract mismatch",
    )

    require(
        installed.get("bmi088_frame_declared_in_nominal_urdf")
        is False
        and installed.get("frame_alias_proven") is False
        and installed.get("metric_extrinsic_qualified") is False
        and installed.get("timestamp_event_semantics_qualified")
        is False
        and installed.get("physical_clock_accuracy") == "UNVERIFIED"
        and installed.get("real_factor_admission") == "DENIED"
        and installed.get("m2dgr_gates") == "11_CLOSED",
        "Source inspection was incorrectly promoted to qualification",
    )

    return {
        "schema": SCHEMA,
        "status": "REQUEST_ONLY_NO_PHYSICAL_ADMISSION",
        "a23_request_count": len(actual_ids),
        "a23_request_ids": actual_ids,
        "request_counts_by_stage": counts,
        "independent_qualifying_receipts": 0,
        "installed_source_sha256_verified_by_caller": True,
        "frame_identity_mapping": "UNRESOLVED",
        "physical_transform_direction": "UNVERIFIED",
        "physical_camera_imu_time": "UNVERIFIED",
        "physical_lidar_imu_time": "UNVERIFIED",
        "cross_clock_accuracy": "UNVERIFIED",
        "metric_calibration_uncertainty": "UNVERIFIED",
        "independent_6dof_reference": "UNVERIFIED",
        "physical_scoring_protocol": "NOT_AUTHORIZED",
        "confirmation_test_accessed": False,
        "physical_measurements_qualified": False,
        "estimator_invoked": False,
        "real_factor_count": 0,
        "real_factor_admission": "DENIED",
        "m2dgr_gates": "11_CLOSED",
    }


def admit_physical_measurements(*args, **kwargs):
    raise MeasurementReadinessError(
        "No independently qualified physical measurement receipt"
    )
