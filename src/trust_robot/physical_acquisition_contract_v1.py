"""R135-A32-1: prospective physical evidence acquisition contracts.

Provides technical requirements for independent acquisition.
Does not create measurements, independent witnesses, valid
receipts, calibration, ground truth or factor permissions.
"""

from trust_robot.m2dgr_prospective_evidence_packet_v1 import (
    REQUEST_SPECS,
    validate_packet,
)
from trust_robot.independent_acquisition_plan_v1 import (
    build_work_orders,
)

SCHEMA = "TRUST_ROBOT_R135_A32_1_ACQUISITION_CONTRACT_V1"

# These are REQUIRED FIELD NAMES, not collected physical values.

FIELD_REQUIREMENTS = {
    "A01": (
        "pre_capture_challenge",
        "independent_challenge_issuer",
        "session_byte_binding",
    ),
    "A02": (
        "device_identity",
        "firmware_configuration",
        "independent_device_review",
    ),
    "B01": (
        "capture_configuration_identity",
        "metric_frame_inventory",
        "calibration_method",
        "uncertainty_budget",
    ),
    "B02": (
        "camera_optical_model",
        "capture_settings",
        "intrinsic_parameter_uncertainty",
    ),
    "B03": (
        "source_target_frame_identity",
        "T_target_source",
        "metric_units",
        "transform_uncertainty",
    ),
    "B04": (
        "physical_event_definition",
        "clock_domain_mapping",
        "clock_mapping_uncertainty",
        "independent_clock_reference",
    ),
    "B05": (
        "exposure_event_definition",
        "imu_sample_event_definition",
        "cross_clock_measurement",
        "timing_uncertainty",
    ),
    "B06": (
        "lidar_firing_event_definition",
        "imu_sample_event_definition",
        "cross_clock_measurement",
        "timing_uncertainty",
    ),
    "C01": (
        "reference_event_association",
        "estimator_event_association",
        "independent_time_validation",
    ),
    "C02": (
        "reference_timestamp_definition",
        "reference_clock_domain",
        "reference_event_origin",
    ),
    "C03": (
        "tracked_body_frame",
        "lidar_frame",
        "T_target_source",
        "reference_geometry_uncertainty",
    ),
    "D01": (
        "predeclared_scoring_protocol",
        "alignment_policy",
        "independent_protocol_review",
    ),
    "D02": (
        "locked_selection_protocol",
        "source_provenance_review",
        "independent_evaluation_review",
    ),
}

PRIORITY_REQUESTS = (
    "B01", "B02", "B03",
    "B04", "B05", "B06", "C03",
)


class AcquisitionContractError(ValueError):
    pass


def build_acquisition_contract(packet):
    try:
        validate_packet(packet)
        orders = build_work_orders(packet)
    except Exception as exc:
        raise AcquisitionContractError(
            "Frozen A23 acquisition inputs differ"
        ) from exc

    expected_ids = tuple(x[0] for x in REQUEST_SPECS)

    if (
        tuple(FIELD_REQUIREMENTS) != expected_ids
        or orders["request_count"] != 13
        or orders["real_factor_count"] != 0
        or orders["real_factor_admission"] != "DENIED"
        or orders["independent_qualified_receipts"] != 0
    ):
        raise AcquisitionContractError(
            "Independent acquisition inventory differs"
        )

    tasks = []

    for spec, order in zip(
        REQUEST_SPECS, orders["work_orders"]
    ):
        ident, stage, blocker, fact, witness, substitute = spec

        if (
            order["request_id"] != ident
            or order["stage"] != stage
            or order["request_status"] != "UNFULFILLED"
            or order["received_receipt"] is not None
            or order["scientific_gate_opened"] is not False
        ):
            raise AcquisitionContractError(
                "Prospective work order changed"
            )

        tasks.append({
            "request_id": ident,
            "stage": stage,
            "diagnostic_blocker": blocker,
            "fact_to_measure": fact,
            "required_independent_witness": witness,
            "insufficient_substitute": substitute,
            "proposed_method":
                order["proposed_acquisition_method"],
            "expected_output":
                order["expected_independent_artifact"],
            "required_field_names":
                list(FIELD_REQUIREMENTS[ident]),
            "capture_session_identity": None,
            "independent_artifact_sha256": None,
            "measurement_values": None,
            "measurement_uncertainty": None,
            "witness_independence_verified": False,
            "request_status": "NOT_ACQUIRED",
            "physical_qualification": False,
        })

    return {
        "schema": SCHEMA,
        "status": "PROSPECTIVE_ACQUISITION_CONTRACT_ONLY",
        "task_count": len(tasks),
        "priority_task_ids": list(PRIORITY_REQUESTS),
        "stage_counts": {
            stage: sum(t["stage"] == stage for t in tasks)
            for stage in ("A", "B", "C", "D")
        },
        "tasks": tasks,
        "prospective_capture_session_assigned": False,
        "measurements_acquired": False,
        "independent_receipts_verified": 0,
        "physical_calibration_verified": False,
        "physical_clock_verified": False,
        "independent_reference_verified": False,
        "physical_factor_admission_enabled": False,
        "real_factor_count": 0,
        "real_factor_admission": "DENIED",
        "m2dgr_gates": "11_CLOSED",
    }


def admit_acquisition_result(*args, **kwargs):
    raise AcquisitionContractError(
        "A planning contract cannot admit physical evidence"
    )
