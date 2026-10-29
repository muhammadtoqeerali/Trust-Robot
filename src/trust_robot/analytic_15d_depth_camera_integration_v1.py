"""R135-A12: synthetic depth-camera / 15D estimator integration.

This module runs six frozen manufactured factor-slot scenarios
using the unchanged Schur-marginalized 15D estimator.

Camera factors come from manufactured pixel and metric-depth
observations, not copied LiDAR registration measurements.

The camera and LiDAR development fixtures share an analytic
motion model. They are not independent physical sensor evidence.

The legacy estimator supports one relative-pose factor per
edge and one inherited numerical residual model. This module
does not authorize modality-specific weighting.

No real data, recorded GT, health inference or factor
conditioning is admitted.
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
    assemble_synthetic_pose_slot,
)

SCHEMA = (
    "TRUST_ROBOT_R135_A12_ANALYTIC_15D_DEPTH_CAMERA_INTEGRATION_V1"
)

STATUS = "UNTRUSTED_SYNTHETIC_SOLVER_DIAGNOSTIC_ONLY"

EDGE = (1, 2)

SCENARIOS = (
    "baseline_lidar",
    "lidar_edge_removed",
    "depth_camera_ideal_restore",
    "depth_camera_noisy_restore",
    "depth_camera_biased_restore",
    "depth_camera_noisy_replace",
)

_CONFIGURATION = {
    "baseline_lidar": (None, "retain"),
    "lidar_edge_removed": (None, "remove"),
    "depth_camera_ideal_restore": ("ideal", "restore"),
    "depth_camera_noisy_restore": ("noisy", "restore"),
    "depth_camera_biased_restore": ("biased", "restore"),
    "depth_camera_noisy_replace": ("noisy", "replace"),
}

EXPECTED_LIDAR = frozenset((
    (0, 1),
    (0, 2),
    (1, 2),
    (1, 3),
    (2, 3),
    (2, 4),
    (3, 4),
))

EXPECTED_IMU = frozenset((
    (0, 1),
    (1, 2),
    (2, 3),
    (3, 4),
))


class SyntheticDepth15DIntegrationError(ValueError):
    """Unexpected frozen synthetic integration state."""


def _require(condition, message):
    if not condition:
        raise SyntheticDepth15DIntegrationError(message)


def _digest(records):
    blob = json.dumps(
        records,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")

    return hashlib.sha256(blob).hexdigest()


def run_scenario(name):
    """Execute one frozen synthetic scenario.

    Accepts no external fixture, sensor record, ground truth,
    probability, health state or factor weight.
    """
    if type(name) is not str or name not in _CONFIGURATION:
        raise SyntheticDepth15DIntegrationError(
            "Only six frozen analytic scenarios are authorized"
        )

    _require(
        NODE_FRAMES == (0, 2, 4, 6, 8)
        and EDGE in EDGES
        and MODES == ("ideal", "noisy", "biased"),
        "Frozen analytic camera chronology changed",
    )

    mode, operation = _CONFIGURATION[name]

    fixture, manufactured_reference = make_fixture("clean")

    # The generated fixture reference is not passed to the
    # estimator, used to select factors, or used to score output.
    del manufactured_reference

    captured = []

    def factory(internal_fixture):
        _require(
            internal_fixture is fixture and not captured,
            "Unexpected factor-factory invocation",
        )

        inertial, baseline, counts = make_factors(
            internal_fixture
        )

        _require(
            set(inertial) == EXPECTED_IMU
            and set(baseline) == EXPECTED_LIDAR
            and counts["imu_intervals"] == 4
            and counts["lidar_factor_count"] == 7
            and counts["imu_samples_reused"] is False,
            "Frozen analytic factor topology changed",
        )

        remaining = dict(baseline)
        packets = []
        camera_metadata = None

        if operation in ("remove", "restore"):
            del remaining[EDGE]

        if mode is not None:
            packet, camera_metadata = generate_packet(
                EDGE, mode
            )

            _require(
                packet.edge == EDGE
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
                ] is False,
                "Synthetic camera provenance changed",
            )

            packets = [packet]

        selected, ledger = assemble_synthetic_pose_slot(
            remaining,
            packets,
            NODE_FRAMES,
        )

        expected_edges = (
            EXPECTED_LIDAR - {EDGE}
            if operation == "remove"
            else EXPECTED_LIDAR
        )

        expected_replaced = (
            [[1, 2]]
            if operation == "replace"
            else []
        )

        _require(
            set(selected) == expected_edges
            and ledger["replaced_lidar_edges"]
            == expected_replaced
            and ledger["synthetic_camera_factor_count"]
            == len(packets)
            and ledger["synthetic_lidar_factor_count"]
            == len(selected) - len(packets)
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
            "Synthetic pose-slot or scientific contract changed",
        )

        ledger_rows = ledger["factor_ledger"]

        _require(
            len(ledger_rows) == len(selected)
            and len({
                tuple(row["edge"])
                for row in ledger_rows
            }) == len(selected)
            and all(
                row["origin"] == "ANALYTIC_FIXTURE"
                for row in ledger_rows
            ),
            "Duplicate or non-analytic factor ledger",
        )

        # Legacy solver field name refers to its single
        # relative-pose slot, not physical LiDAR provenance.
        metadata = dict(counts)
        metadata["lidar_factor_count"] = len(selected)

        captured.append({
            "ledger": ledger,
            "camera_metadata": camera_metadata,
            "input_lidar_count": len(remaining),
            "pose_slot_count": len(selected),
            "camera_count": len(packets),
        })

        return inertial, selected, metadata

    records, audit = estimate_marginalized(
        fixture,
        node_frames=NODE_FRAMES,
        factor_factory=factory,
    )

    _require(
        len(captured) == 1,
        "Factor factory not invoked exactly once",
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
        == selection["pose_slot_count"],
        "15D estimator factor accounting failed",
    )

    consumed = {
        tuple(x) for x in audit["consumed_lidar_keys"]
    }

    remaining = {
        tuple(x) for x in audit["remaining_lidar_keys"]
    }

    _require(
        not (consumed & remaining)
        and len(consumed | remaining)
        == selection["pose_slot_count"],
        "Pose factors reused or unaccounted",
    )

    windows = audit["windows"]

    _require(
        len(windows) == 4
        and all(
            w["accepted"] is True
            and w["jacobian_rank"] == w["required_rank"]
            and math.isfinite(float(w["cost"]))
            and float(w["cost"]) >= 0.0
            for w in windows
        ),
        "Unaccepted or nonfinite synthetic window",
    )

    for record in records:
        _require(
            record["state_dimension"] == 15
            and record["reference_pose"] is None
            and all(
                np.isfinite(
                    np.asarray(record[key], dtype=np.float64)
                ).all()
                for key in (
                    "position_m",
                    "orientation_quaternion_wxyz",
                    "velocity_m_s",
                    "gyro_bias_rad_s",
                    "accel_bias_m_s2",
                )
            ),
            "Invalid synthetic 15D state record",
        )

    total_window_cost = math.fsum(
        float(w["cost"]) for w in windows
    )

    final_position = [
        float(x) for x in records[-1]["position_m"]
    ]

    _require(
        math.isfinite(total_window_cost)
        and all(math.isfinite(x) for x in final_position),
        "Nonfinite synthetic solver diagnostic",
    )

    return {
        "schema": SCHEMA,
        "status": STATUS,
        "scenario": name,
        "camera_mode": mode,
        "operation": operation,
        "state_dimension": 15,
        "node_count": 5,
        "original_lidar_factor_count": 7,
        "synthetic_imu_factor_count": 4,
        "input_lidar_factor_count":
            selection["input_lidar_count"],
        "selected_lidar_slot_count":
            selection["ledger"][
                "synthetic_lidar_factor_count"
            ],
        "selected_camera_slot_count":
            selection["camera_count"],
        "total_pose_slot_count":
            selection["pose_slot_count"],
        "replaced_lidar_edges":
            selection["ledger"]["replaced_lidar_edges"],
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
        "imu_samples_reused":
            audit["imu_samples_reused"],
        "all_windows_numerically_full_rank": True,
        "total_window_cost_diagnostic":
            total_window_cost,
        "synthetic_final_position_m":
            final_position,
        "synthetic_state_sha256": _digest(records),
        "camera_factor_copied_from_lidar": False,
        "camera_metric_depth_is_manufactured": True,
        "shared_analytic_motion_model": True,
        "independent_physical_camera_evidence": False,
        "independent_camera_weighting_supported": False,
        "factor_weights_modified": False,
        "physical_localization_accuracy_established": False,
        "physical_localization_recovery_demonstrated": False,
        "ground_truth_scoring_performed": False,
        "health_probabilities_generated": False,
        "health_labels_assigned": False,
        "recorded_data_accessed": False,
        "real_factor_execution_authorized": False,
        "confirmation_test_accessed": False,
    }


def run_all_scenarios():
    """Run all six fixed conditions and report baseline deltas.

    The reference for reported deltas is another manufactured
    estimator output, never recorded or independent ground truth.
    """
    rows = [
        run_scenario(name)
        for name in SCENARIOS
    ]

    baseline = rows[0]["synthetic_final_position_m"]

    for row in rows:
        row["final_position_delta_from_synthetic_baseline_m"] = (
            math.dist(
                row["synthetic_final_position_m"],
                baseline,
            )
        )

        _require(
            math.isfinite(
                row[
                    "final_position_delta_from_synthetic_baseline_m"
                ]
            ),
            "Nonfinite baseline-relative numerical diagnostic",
        )

    return tuple(rows)
