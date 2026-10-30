"""R135-A30-2: prospective independent measurement work orders.

Exact A23 request identities are frozen. This produces
engineering acquisition instructions, NOT qualifying receipts.
No physical measurements, timestamps, thresholds, frame
aliases, dataset reads, or real factors are admitted.
"""

from __future__ import annotations

from trust_robot.m2dgr_prospective_evidence_packet_v1 import (
    REQUEST_SPECS,
    validate_packet,
)

SCHEMA = "TRUST_ROBOT_R135_A30_2_ACQUISITION_WORK_ORDERS_V1"


class AcquisitionPlanError(ValueError):
    pass


# Each work order specifies the independent measurement
# output needed; no numeric value or threshold is selected.

METHODS = {
    "A01": (
        "Pre-capture external challenge and immutable source binding",
        "Independent challenge and capture-byte binding record",
    ),
    "A02": (
        "Review device serials, firmware, wiring and acquisition setup",
        "Independent physical-device identity and configuration record",
    ),
    "B01": (
        "Measure capture-applicable sensor geometry with uncertainty",
        "Metric calibration report, axes, units, uncertainty",
    ),
    "B02": (
        "Independently calibrate camera intrinsics at capture settings",
        "Optical model, coefficients, settings and uncertainty",
    ),
    "B03": (
        "Measure camera-to-LiDAR transform with explicit direction",
        "T_target_source, axes, units, covariance and reviewer",
    ),
    "B04": (
        "Witness physical clock domains and exact event definitions",
        "Clock mapping, event origin, uncertainty and independent timing",
    ),
    "B05": (
        "Measure camera exposure event versus inertial sample event",
        "Independent exposure-to-IMU event association and uncertainty",
    ),
    "B06": (
        "Measure LiDAR firing event versus inertial sample event",
        "Independent firing-to-IMU event association and uncertainty",
    ),
    "C01": (
        "Validate reference-to-estimator event-time correspondence",
        "Independent temporal association method and uncertainty",
    ),
    "C02": (
        "Document exact physical reference timestamp event and origin",
        "Reference event, clock domain, axis convention and reviewer",
    ),
    "C03": (
        "Measure tracked-body-to-LiDAR rigid transform independently",
        "Verified reference extrinsic direction and uncertainty",
    ),
    "D01": (
        "Predeclare scoring before exposing held-out measurements",
        "Version-pinned evaluation, alignment and association protocol",
    ),
    "D02": (
        "Independently review complete evaluation provenance and splits",
        "Signed protocol review with locked prospective separation",
    ),
}

RECEIPT_FIELDS = (
    "capture_session_identity",
    "independent_witness_identity",
    "independent_witness_role",
    "measurement_method_version",
    "artifact_identity_sha256",
    "time_event_definition",
    "coordinate_frame_direction",
    "uncertainty_method",
    "independent_review_record",
)


def build_work_orders(packet):
    """Generate immutable-protocol proposals from frozen A23."""
    try:
        validate_packet(packet)
    except Exception as exc:
        raise AcquisitionPlanError(
            "Frozen A23 packet validation failed"
        ) from exc

    if set(METHODS) != {
        row[0] for row in REQUEST_SPECS
    }:
        raise AcquisitionPlanError(
            "Work-order coverage differs from A23"
        )

    requests = packet["requests"]
    results = []

    for record, spec in zip(requests, REQUEST_SPECS):
        ident, stage, blocker, fact, witness, substitute = spec

        if (
            record["request_id"] != ident
            or record["stage"] != stage
            or record["qualifying_receipt_received"] is not False
            or record["scientific_gate_opened"] is not False
        ):
            raise AcquisitionPlanError(
                "Unexpected independent evidence admission"
            )

        method, expected_output = METHODS[ident]

        results.append({
            "request_id": ident,
            "stage": stage,
            "a22_diagnostic_blocker": blocker,
            "physical_fact_required": fact,
            "independent_witness_required": witness,
            "insufficient_substitute": substitute,
            "proposed_acquisition_method": method,
            "expected_independent_artifact": expected_output,
            "prospective_receipt_field_names":
                list(RECEIPT_FIELDS),
            "received_receipt": None,
            "measurement_value": None,
            "uncertainty_value": None,
            "independent_review_completed": False,
            "physical_qualification": "NOT_ESTABLISHED",
            "request_status": "UNFULFILLED",
            "scientific_gate_opened": False,
        })

    return {
        "schema": SCHEMA,
        "status": "INDEPENDENT_ACQUISITION_PLAN_ONLY",
        "source_packet_schema": packet["schema"],
        "request_count": 13,
        "stage_counts": {
            stage: sum(
                row["stage"] == stage for row in results
            )
            for stage in ("A", "B", "C", "D")
        },
        "work_orders": results,
        "physical_measurements_performed": False,
        "receipt_admission_enabled": False,
        "independent_qualified_receipts": 0,
        "retroactive_m2dgr_qualification": False,
        "confirmation_test_accessed": False,
        "physical_clock_accuracy": "UNVERIFIED",
        "physical_sensor_calibration": "UNVERIFIED",
        "independent_ground_truth": "UNVERIFIED",
        "estimator_invoked": False,
        "real_factor_count": 0,
        "real_factor_admission": "DENIED",
        "m2dgr_gates": "11_CLOSED",
    }


def accept_independent_receipt(*args, **kwargs):
    raise AcquisitionPlanError(
        "Independent receipts require a separately reviewed "
        "scientific-admission protocol"
    )
