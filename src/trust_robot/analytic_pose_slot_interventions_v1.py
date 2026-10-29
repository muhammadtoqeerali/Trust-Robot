"""Deterministic analytic pose-slot intervention diagnostics.

Internal synthetic fixtures only. No external measurements,
datasets, pose solve, real health labels, probabilities,
factor weights, calibrated covariance or ground truth.

The legacy estimator has a single relative-pose slot.
Camera substitution is not independent camera/LiDAR fusion.
"""
from __future__ import annotations

from trust_robot.clean_backbone import PoseSE3
from trust_robot.multimodal_factor_interface import (
    ANALYTIC_ORIGIN,
    ANALYTIC_FRAME,
    CAMERA_SOURCE,
    LIDAR_SOURCE,
    SyntheticPoseFactor,
    assemble_synthetic_pose_slot,
)

SCHEMA = (
    "TRUST_ROBOT_R135_A3_SYNTHETIC_POSE_SLOT_INTERVENTIONS_V1"
)

STATUS = "UNTRUSTED_SYNTHETIC_GRAPH_DIAGNOSTIC_ONLY"

NODE_FRAMES = (0, 1, 2, 3)

BASE_EDGES = ((0, 1), (1, 2), (2, 3))

REMOVED_EDGE = (1, 2)

SCENARIOS = (
    "baseline",
    "lidar_edge_removed",
    "camera_substitutes_lidar",
    "camera_on_removed_lidar_edge",
)


class SyntheticInterventionError(ValueError):
    """Invalid analytic graph scenario selection."""


def _pose(x):
    """Fixed non-physical numeric fixture; not a measurement."""
    return PoseSE3(
        translation_m=(float(x), 0.0, 0.0),
        quaternion_wxyz=(1.0, 0.0, 0.0, 0.0),
    )


def _camera_packet():
    return SyntheticPoseFactor(
        modality="camera",
        edge=REMOVED_EDGE,
        measurement_id="r135-a3-analytic-camera-1-2",
        source_id=CAMERA_SOURCE,
        frame_id=ANALYTIC_FRAME,
        measurement=_pose(7.0),
    )


def _assemble(name):
    if type(name) is not str or name not in SCENARIOS:
        raise SyntheticInterventionError(
            "Only four frozen analytic graph scenarios are allowed"
        )

    lidar = {
        (0, 1): _pose(1.0),
        (1, 2): _pose(2.0),
        (2, 3): _pose(3.0),
    }

    removed = name in (
        "lidar_edge_removed",
        "camera_on_removed_lidar_edge",
    )

    with_camera = name in (
        "camera_substitutes_lidar",
        "camera_on_removed_lidar_edge",
    )

    if removed:
        del lidar[REMOVED_EDGE]

    packets = [_camera_packet()] if with_camera else []

    merged, ledger = assemble_synthetic_pose_slot(
        lidar, packets, NODE_FRAMES
    )

    return lidar, packets, merged, ledger


def run_scenario(name):
    """Describe a frozen analytic graph without solving any pose.

    Does not accept a sensor record, factor object,
    health-state label, calibrated probability or weight.
    """
    lidar, packets, merged, ledger = _assemble(name)

    rows = ledger["factor_ledger"]

    selected = {
        tuple(row["edge"]): row["modality"]
        for row in rows
    }

    if len(selected) != len(rows):
        raise SyntheticInterventionError(
            "Repeated graph slot in analytic ledger"
        )

    for row in rows:
        expected_source = (
            CAMERA_SOURCE
            if row["modality"] == "camera"
            else LIDAR_SOURCE
        )

        if (
            row["modality"] not in ("camera", "lidar")
            or row["origin"] != ANALYTIC_ORIGIN
            or row["source_id"] != expected_source
        ):
            raise SyntheticInterventionError(
                "Invalid analytic ledger provenance"
            )

    if (
        len(merged) != len(rows)
        or ledger["same_edge_measurements_double_counted"]
        is not False
        or ledger["backend_can_independently_weight_camera"]
        is not False
        or ledger["real_sensor_factor_execution_authorized"]
        is not False
    ):
        raise SyntheticInterventionError(
            "Legacy slot / scientific boundary changed"
        )

    expected = (
        set(BASE_EDGES) - {REMOVED_EDGE}
        if name == "lidar_edge_removed"
        else set(BASE_EDGES)
    )

    if set(merged) != expected:
        raise SyntheticInterventionError(
            "Unexpected graph topology"
        )

    if packets and merged[REMOVED_EDGE] != packets[0].measurement:
        raise SyntheticInterventionError(
            "Synthetic camera substitution did not occupy slot"
        )

    missing = sorted(set(BASE_EDGES) - set(merged))

    camera_only = (
        bool(packets)
        and REMOVED_EDGE not in lidar
    )

    return {
        "schema": SCHEMA,
        "status": STATUS,
        "scenario": name,
        "synthetic_lidar_input_edges": len(lidar),
        "synthetic_camera_input_packets": len(packets),
        "selected_lidar_slots":
            ledger["synthetic_lidar_factor_count"],
        "selected_camera_slots":
            ledger["synthetic_camera_factor_count"],
        "total_pose_slots":
            ledger["total_relative_pose_factor_count"],
        "missing_graph_edges": [list(x) for x in missing],
        "camera_replaced_lidar_edges":
            ledger["replaced_lidar_edges"],
        "camera_on_edge_without_lidar": camera_only,
        "factor_ledger": rows,
        "same_edge_double_counted": False,
        "independent_camera_weighting_supported": False,
        "physical_camera_measurement_used": False,
        "pose_estimation_performed": False,
        "covariance_estimated": False,
        "health_probabilities_generated": False,
        "health_labels_assigned": False,
        "factor_weights_selected": False,
        "fault_severity_calibrated": False,
        "localization_recovery_demonstrated": False,
        "real_factor_execution_authorized": False,
        "confirmation_test_accessed": False,
    }


def run_all_scenarios():
    """Return four deterministic diagnostic summaries."""
    return tuple(
        run_scenario(name)
        for name in SCENARIOS
    )
