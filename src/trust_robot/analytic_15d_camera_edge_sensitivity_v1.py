"""R135-A15: reproducible synthetic seven-edge 15D sensitivity.

29 frozen configurations: one baseline, seven single-edge
LiDAR removals, and 21 ideal/noisy/biased depth-camera
restorations.

Uses only manufactured sensor fixtures. Synthetic camera
pose packets originate from simulated metric-depth observations,
not copied LiDAR factors.

Shared analytic motion is not independent physical evidence.
The legacy backend has one pose slot per edge and inherited
LiDAR numeric residual weighting. No camera-specific factor
weight or health policy is authorized.

No recorded sensor input, GT scoring, health probabilities,
real factor execution or held-out data access.
"""
from __future__ import annotations

import hashlib
import json
import math

import numpy as np

from trust_robot.analytic_inertial_15d import make_fixture
from trust_robot.analytic_preintegrated_fusion import (
    NODE_FRAMES,
    make_factors,
)
from trust_robot.analytic_marginalized_fusion import (
    estimate_marginalized,
)
from trust_robot.analytic_depth_camera_source_v1 import (
    EDGES,
    MODES,
    generate_packet,
)
from trust_robot.multimodal_factor_interface import (
    CAMERA_SOURCE,
    LIDAR_SOURCE,
    assemble_synthetic_pose_slot,
)

SCHEMA = "TRUST_ROBOT_R135_A15_SEVEN_EDGE_SENSITIVITY_V1"
STATUS = "UNTRUSTED_SYNTHETIC_NUMERICAL_DIAGNOSTIC_ONLY"

EXPECTED_EDGES = frozenset((
    (0, 1), (0, 2), (1, 2), (1, 3),
    (2, 3), (2, 4), (3, 4),
))

EXPECTED_IMU = frozenset((
    (0, 1), (1, 2), (2, 3), (3, 4),
))

DENIALS = (
    "camera_factor_copied_from_lidar",
    "independent_physical_sensor_evidence",
    "independent_camera_weighting_supported",
    "factor_weights_modified",
    "ground_truth_scoring_performed",
    "physical_accuracy_established",
    "physical_recovery_demonstrated",
    "health_probabilities_generated",
    "health_labels_assigned",
    "recorded_data_accessed",
    "real_factor_execution_authorized",
    "confirmation_test_accessed",
)


class SyntheticSensitivityError(ValueError):
    """Invalid or inconsistent synthetic experiment state."""


def _require(condition, message):
    if not condition:
        raise SyntheticSensitivityError(message)


def _digest(records):
    return hashlib.sha256(
        json.dumps(
            records,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def run_case(edge=None, mode=None):
    """Execute one frozen manufactured estimator configuration.

    None/None: LiDAR-only baseline.
    edge/None: remove one LiDAR pose edge.
    edge/mode: substitute synthetic depth-camera observation.

    No external fixtures, callbacks, health labels,
    factor weights or sensor records are accepted.
    """
    if edge is None:
        valid = mode is None
    else:
        valid = (
            type(edge) is tuple
            and len(edge) == 2
            and all(type(node) is int for node in edge)
            and edge in EXPECTED_EDGES
            and (
                mode is None
                or (type(mode) is str and mode in MODES)
            )
        )

    if not valid:
        raise SyntheticSensitivityError(
            "Only frozen edge and mode combinations are allowed"
        )

    _require(
        NODE_FRAMES == (0, 2, 4, 6, 8)
        and tuple(EDGES) == (
            (0, 1), (0, 2), (1, 2), (1, 3),
            (2, 3), (2, 4), (3, 4),
        )
        and MODES == ("ideal", "noisy", "biased"),
        "Frozen analytic topology or camera modes changed",
    )

    fixture, synthetic_reference = make_fixture("clean")

    # The synthetic reference is deliberately discarded;
    # no reference trajectory is used for estimation or
    # numerical accuracy scoring.
    del synthetic_reference

    captured = []

    def factor_factory(internal_fixture):
        _require(
            internal_fixture is fixture and not captured,
            "Unexpected factor-factory invocation",
        )

        inertial, baseline, counts = make_factors(
            internal_fixture
        )

        _require(
            set(inertial) == EXPECTED_IMU
            and set(baseline) == EXPECTED_EDGES
            and counts["imu_intervals"] == 4
            and counts["lidar_factor_count"] == 7
            and counts["imu_samples_reused"] is False,
            "Frozen analytic IMU/LiDAR factor set changed",
        )

        remaining = dict(baseline)
        packets = []
        camera_metadata = None

        if edge is not None:
            del remaining[edge]

        if mode is not None:
            packet, camera_metadata = generate_packet(
                edge, mode
            )

            _require(
                packet.edge == edge
                and packet.modality == "camera"
                and packet.origin == "ANALYTIC_FIXTURE"
                and packet.source_id == CAMERA_SOURCE
                and camera_metadata["lidar_pose_factor_copied"]
                is False
                and camera_metadata[
                    "independent_physical_sensor_evidence"
                ] is False
                and camera_metadata["factor_weight_selected"]
                is False
                and camera_metadata[
                    "real_factor_execution_authorized"
                ] is False
                and camera_metadata[
                    "confirmation_test_accessed"
                ] is False,
                "Camera origin or authorization changed",
            )

            packets.append(packet)

        selected, ledger = assemble_synthetic_pose_slot(
            remaining, packets, NODE_FRAMES
        )

        expected_selected = (
            EXPECTED_EDGES - {edge}
            if edge is not None and mode is None
            else EXPECTED_EDGES
        )

        _require(
            set(selected) == expected_selected
            and ledger["synthetic_camera_factor_count"]
            == len(packets)
            and ledger["synthetic_lidar_factor_count"]
            == len(selected) - len(packets)
            and ledger["total_relative_pose_factor_count"]
            == len(selected)
            and ledger["replaced_lidar_edges"] == []
            and ledger[
                "same_edge_measurements_double_counted"
            ] is False
            and ledger[
                "backend_can_independently_weight_camera"
            ] is False
            and ledger["real_visual_frontend_used"]
            is False
            and ledger[
                "real_sensor_factor_execution_authorized"
            ] is False,
            "Pose-slot assembly contract changed",
        )

        rows = ledger["factor_ledger"]
        actual_edges = {
            tuple(row["edge"]) for row in rows
        }

        _require(
            len(rows) == len(selected)
            and len(actual_edges) == len(selected)
            and all(
                row["origin"] == "ANALYTIC_FIXTURE"
                and row["source_id"] == (
                    CAMERA_SOURCE
                    if row["modality"] == "camera"
                    else LIDAR_SOURCE
                )
                for row in rows
            ),
            "Invalid factor ownership or source ledger",
        )

        if mode is not None:
            camera_rows = [
                row for row in rows
                if row["modality"] == "camera"
            ]

            _require(
                len(camera_rows) == 1
                and tuple(camera_rows[0]["edge"]) == edge,
                "Synthetic camera edge mismatched",
            )

        # Historical backend field counts all pose slots,
        # not solely LiDAR-origin measurements.
        metadata = dict(counts)
        metadata["lidar_factor_count"] = len(selected)

        captured.append({
            "ledger": ledger,
            "camera_metadata": camera_metadata,
            "lidar_inputs": len(remaining),
            "camera_inputs": len(packets),
            "pose_slots": len(selected),
        })

        return inertial, selected, metadata

    records, audit = estimate_marginalized(
        fixture,
        node_frames=NODE_FRAMES,
        factor_factory=factor_factory,
    )

    _require(
        len(captured) == 1,
        "Factor factory not called exactly once",
    )

    selection = captured[0]

    _require(
        len(records) == 5
        and audit["accepted_window_count"] == 4
        and audit["schur_elimination_count"] == 3
        and audit["unaccounted_factor_count"] == 0
        and audit["factor_reuse_after_marginalization"]
        is False
        and audit["imu_samples_reused"] is False
        and audit["lidar_factor_count"]
        == selection["pose_slots"],
        "Schur estimator factor accounting failed",
    )

    consumed = {
        tuple(k) for k in audit["consumed_lidar_keys"]
    }

    live = {
        tuple(k) for k in audit["remaining_lidar_keys"]
    }

    _require(
        not (consumed & live)
        and len(consumed | live) == selection["pose_slots"],
        "Pose factors lost or reused",
    )

    _require(
        len(audit["windows"]) == 4
        and all(
            w["accepted"] is True
            and w["jacobian_rank"] == w["required_rank"]
            and math.isfinite(float(w["cost"]))
            and float(w["cost"]) >= 0.0
            for w in audit["windows"]
        ),
        "Synthetic optimizer window failure",
    )

    for record in records:
        _require(
            record["state_dimension"] == 15
            and record["reference_pose"] is None
            and all(
                np.isfinite(
                    np.asarray(
                        record[key], dtype=np.float64
                    )
                ).all()
                for key in (
                    "position_m",
                    "orientation_quaternion_wxyz",
                    "velocity_m_s",
                    "gyro_bias_rad_s",
                    "accel_bias_m_s2",
                )
            ),
            "Nonfinite or unauthorized estimator state",
        )

    total_cost = math.fsum(
        float(w["cost"])
        for w in audit["windows"]
    )

    final_position = [
        float(x) for x in records[-1]["position_m"]
    ]

    _require(
        math.isfinite(total_cost)
        and all(math.isfinite(x) for x in final_position),
        "Nonfinite numerical diagnostic",
    )

    result = {
        "schema": SCHEMA,
        "status": STATUS,
        "edge": list(edge) if edge is not None else None,
        "camera_mode": mode,
        "configuration": (
            "baseline"
            if edge is None
            else ("lidar_removed" if mode is None
                  else "camera_restored")
        ),
        "node_count": 5,
        "state_dimension": 15,
        "synthetic_imu_factor_count": 4,
        "input_lidar_factor_count":
            selection["lidar_inputs"],
        "selected_lidar_slot_count":
            selection["ledger"][
                "synthetic_lidar_factor_count"
            ],
        "selected_camera_slot_count":
            selection["camera_inputs"],
        "total_pose_slot_count":
            selection["pose_slots"],
        "factor_ledger":
            selection["ledger"]["factor_ledger"],
        "camera_source_metadata":
            selection["camera_metadata"],
        "accepted_window_count":
            audit["accepted_window_count"],
        "schur_elimination_count":
            audit["schur_elimination_count"],
        "unaccounted_factor_count":
            audit["unaccounted_factor_count"],
        "factor_reuse_after_marginalization":
            audit["factor_reuse_after_marginalization"],
        "imu_samples_reused": audit["imu_samples_reused"],
        "all_windows_numerically_full_rank": True,
        "total_window_cost_diagnostic": total_cost,
        "synthetic_final_position_m": final_position,
        "synthetic_state_sha256": _digest(records),
        "manufactured_metric_depth": True,
        "shared_analytic_motion_model": True,
    }

    result.update({name: False for name in DENIALS})

    return result


def run_matrix():
    """Run 29 configurations; return baseline-relative diagnostics.

    The reference is a synthetic estimator output,
    not independent ground truth.
    """
    rows = [run_case()]

    for edge in EDGES:
        rows.append(run_case(edge, None))
        for mode in MODES:
            rows.append(run_case(edge, mode))

    _require(len(rows) == 29, "Incomplete synthetic matrix")

    baseline = rows[0]["synthetic_final_position_m"]

    for row in rows:
        distance = math.dist(
            row["synthetic_final_position_m"],
            baseline,
        )

        _require(
            math.isfinite(distance),
            "Nonfinite baseline-relative diagnostic",
        )

        row[
            "final_position_delta_from_synthetic_baseline_m"
        ] = distance

    return tuple(rows)
