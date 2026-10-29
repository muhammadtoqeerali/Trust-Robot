"""R135-A16: manufactured simultaneous two-edge failure study.

85 configurations:
  one LiDAR baseline;
  21 pairs of removed LiDAR relative-pose factors;
  63 dual-depth-camera restorations in three fixed modes.

Synthetic metric-depth observations do not copy LiDAR
measurements. Both manufactured sources share an analytic
motion model and are not independent physical evidence.

No real data, recorded GT, health inference, information
weight selection, real-factor admission, or held-out access.

Numerical rank rejection may be recorded; contract violations
and unexpected solver errors are not treated as valid outcomes.
"""
from __future__ import annotations

from itertools import combinations
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

SCHEMA = "TRUST_ROBOT_R135_A16_PAIR_FAULT_STRESS_V1"
STATUS = "UNTRUSTED_SYNTHETIC_NUMERICAL_STRESS_ONLY"

PAIRS = tuple(combinations(EDGES, 2))

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
    "independent_camera_information_weighting",
    "factor_weights_modified",
    "ground_truth_scoring_performed",
    "physical_localization_accuracy_established",
    "physical_recovery_demonstrated",
    "health_probability_generated",
    "health_label_assigned",
    "recorded_data_accessed",
    "real_factor_execution_authorized",
    "confirmation_test_accessed",
)


class SyntheticPairFaultError(ValueError):
    """Unexpected synthetic pairing or scientific contract."""


def _require(value, message):
    if not value:
        raise SyntheticPairFaultError(message)


def _digest(value):
    data = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _valid_pair(pair):
    if type(pair) is not tuple or len(pair) != 2:
        return False

    if not all(
        type(edge) is tuple
        and len(edge) == 2
        and all(type(n) is int for n in edge)
        for edge in pair
    ):
        return False

    return pair in PAIRS


def run_case(pair=None, mode=None):
    """Execute one fixed synthetic double-fault configuration.

    pair=None, mode=None: LiDAR baseline.
    pair=two valid edges, mode=None: remove both LiDAR factors.
    pair=two valid edges, mode in MODES: restore both with camera.

    No external sensor input, weights, callbacks or labels.
    """
    if pair is None:
        valid = mode is None
    else:
        valid = (
            _valid_pair(pair)
            and (
                mode is None
                or (type(mode) is str and mode in MODES)
            )
        )

    if not valid:
        raise SyntheticPairFaultError(
            "Only frozen two-edge configurations are allowed"
        )

    _require(
        NODE_FRAMES == (0, 2, 4, 6, 8)
        and set(EDGES) == EXPECTED_EDGES
        and len(EDGES) == 7
        and MODES == ("ideal", "noisy", "biased")
        and len(PAIRS) == 21,
        "Frozen graph, frames or camera modes changed",
    )

    fixture, synthetic_reference = make_fixture("clean")

    # Explicitly exclude synthetic reference scoring.
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
            "Original synthetic factor graph changed",
        )

        remaining = dict(baseline)
        packets = []
        source_receipts = []

        if pair is not None:
            for edge in pair:
                del remaining[edge]

        if mode is not None:
            for edge in pair:
                packet, receipt = generate_packet(
                    edge, mode
                )

                _require(
                    packet.edge == edge
                    and packet.modality == "camera"
                    and packet.origin == "ANALYTIC_FIXTURE"
                    and packet.source_id == CAMERA_SOURCE
                    and receipt["lidar_pose_factor_copied"]
                    is False
                    and receipt[
                        "independent_physical_sensor_evidence"
                    ] is False
                    and receipt["factor_weight_selected"]
                    is False
                    and receipt[
                        "real_factor_execution_authorized"
                    ] is False,
                    "Camera source provenance violation",
                )

                packets.append(packet)
                source_receipts.append(receipt)

        selected, ledger = assemble_synthetic_pose_slot(
            remaining,
            packets,
            NODE_FRAMES,
        )

        missing = (
            set(pair)
            if pair is not None and mode is None
            else set()
        )

        expected = EXPECTED_EDGES - missing

        _require(
            set(selected) == expected
            and ledger["total_relative_pose_factor_count"]
            == len(expected)
            and ledger["synthetic_camera_factor_count"]
            == len(packets)
            and ledger["synthetic_lidar_factor_count"]
            == len(selected) - len(packets)
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
            "Synthetic pose-slot ownership violation",
        )

        rows = ledger["factor_ledger"]

        _require(
            len(rows) == len(selected)
            and len({
                tuple(r["edge"]) for r in rows
            }) == len(selected)
            and len({
                r["measurement_id"] for r in rows
            }) == len(rows)
            and all(
                r["origin"] == "ANALYTIC_FIXTURE"
                and r["source_id"] == (
                    CAMERA_SOURCE
                    if r["modality"] == "camera"
                    else LIDAR_SOURCE
                )
                for r in rows
            ),
            "Duplicate or invalid factor provenance",
        )

        _require(
            len([
                r for r in rows
                if r["modality"] == "camera"
            ]) == len(packets),
            "Camera factor count mismatch",
        )

        # The backend's historical lidar_factor_count
        # field actually counts all pose-factor slots.
        metadata = dict(counts)
        metadata["lidar_factor_count"] = len(selected)

        captured.append({
            "factor_ledger": rows,
            "camera_receipts": source_receipts,
            "pose_slots": len(selected),
            "camera_slots": len(packets),
            "lidar_slots": len(selected) - len(packets),
        })

        return inertial, selected, metadata

    outcome = "ACCEPTED"
    rejection = None
    records = None
    audit = None

    try:
        records, audit = estimate_marginalized(
            fixture,
            node_frames=NODE_FRAMES,
            factor_factory=factor_factory,
        )
    except ValueError as exc:
        # Only this explicitly recognized numerical solve
        # rejection is a reportable stress-test result.
        # All other errors, including contract failures,
        # must stop the phase.
        message = str(exc)

        if (
            type(exc) is not ValueError
            or not message.startswith(
                "Marginalized window solve failed at "
            )
        ):
            raise

        outcome = "NUMERICALLY_REJECTED"
        rejection = message

    _require(
        len(captured) == 1,
        "Missing or duplicated factor-factory invocation",
    )

    chosen = captured[0]

    position = None
    cost = None
    digest = None
    accepted_windows = None
    schur_count = None

    if outcome == "ACCEPTED":
        _require(
            len(records) == 5
            and audit["accepted_window_count"] == 4
            and audit["schur_elimination_count"] == 3
            and audit["unaccounted_factor_count"] == 0
            and audit["factor_reuse_after_marginalization"]
            is False
            and audit["imu_samples_reused"] is False
            and audit["lidar_factor_count"]
            == chosen["pose_slots"],
            "Schur estimator accounting violation",
        )

        used = {
            tuple(k) for k in audit["consumed_lidar_keys"]
        }

        live = {
            tuple(k) for k in audit["remaining_lidar_keys"]
        }

        _require(
            not (used & live)
            and len(used | live) == chosen["pose_slots"],
            "Lost or reused pose-factor ownership",
        )

        _require(
            len(audit["windows"]) == 4
            and all(
                w["accepted"] is True
                and w["jacobian_rank"] == w["required_rank"]
                and math.isfinite(float(w["cost"]))
                for w in audit["windows"]
            ),
            "Window acceptance or rank violation",
        )

        for record in records:
            _require(
                record["state_dimension"] == 15
                and record["reference_pose"] is None
                and all(
                    np.isfinite(np.asarray(
                        record[key], dtype=np.float64
                    )).all()
                    for key in (
                        "position_m",
                        "orientation_quaternion_wxyz",
                        "velocity_m_s",
                        "gyro_bias_rad_s",
                        "accel_bias_m_s2",
                    )
                ),
                "Invalid manufactured state output",
            )

        position = [
            float(x) for x in records[-1]["position_m"]
        ]

        cost = math.fsum(
            float(w["cost"]) for w in audit["windows"]
        )

        _require(
            math.isfinite(cost)
            and cost >= 0.0
            and all(math.isfinite(x) for x in position),
            "Nonfinite synthetic numerical output",
        )

        digest = _digest(records)
        accepted_windows = audit["accepted_window_count"]
        schur_count = audit["schur_elimination_count"]

    result = {
        "schema": SCHEMA,
        "status": STATUS,
        "pair": (
            [list(x) for x in pair]
            if pair is not None else None
        ),
        "camera_mode": mode,
        "configuration": (
            "baseline" if pair is None
            else (
                "two_lidar_removed"
                if mode is None
                else "two_camera_restored"
            )
        ),
        "solver_outcome": outcome,
        "numerical_rejection": rejection,
        "node_count": 5,
        "state_dimension": 15,
        "synthetic_imu_factor_count": 4,
        "selected_lidar_slot_count": chosen["lidar_slots"],
        "selected_camera_slot_count": chosen["camera_slots"],
        "total_pose_slot_count": chosen["pose_slots"],
        "factor_ledger": chosen["factor_ledger"],
        "camera_source_receipts": chosen["camera_receipts"],
        "accepted_window_count": accepted_windows,
        "schur_elimination_count": schur_count,
        "total_window_cost_diagnostic": cost,
        "synthetic_final_position_m": position,
        "synthetic_state_sha256": digest,
        "shared_analytic_motion_model": True,
        "metric_depth_is_manufactured": True,
        "numerical_rank_proves_physical_observability": False,
        "final_position_delta_from_baseline_m": None,
    }

    result.update({
        key: False for key in DENIALS
    })

    return result


def run_matrix():
    """Return the 85 frozen scenarios and their diagnostics."""
    rows = [run_case()]

    for pair in PAIRS:
        rows.append(run_case(pair))

        for mode in MODES:
            rows.append(run_case(pair, mode))

    _require(
        len(rows) == 85,
        "Incomplete pair-fault experiment matrix",
    )

    baseline = rows[0]

    _require(
        baseline["solver_outcome"] == "ACCEPTED",
        "Synthetic baseline was not accepted",
    )

    reference = baseline["synthetic_final_position_m"]

    for row in rows:
        if row["solver_outcome"] == "ACCEPTED":
            row[
                "final_position_delta_from_baseline_m"
            ] = math.dist(
                row["synthetic_final_position_m"],
                reference,
            )

    return tuple(rows)
