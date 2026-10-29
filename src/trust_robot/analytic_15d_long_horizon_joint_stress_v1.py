"""R135-A19: manufactured 12-node combined sensor-fault study.

Crosses three existing IMU conditions with five frozen
LiDAR availability patterns on the published 12-node
Schur-marginalized synthetic trajectory.

Only the published long_fixture and long_factors
provide measurements. The existing estimator, prior,
residual scales and numeric support policy are unchanged.

Numerical support and active LiDAR availability are
diagnostics, not calibrated uncertainty, physical
observability, safety assurance or recovery evidence.

No recorded data, independent GT, health labels,
probability inference, or real factor execution.
"""
from __future__ import annotations

import hashlib
import json
import math

import numpy as np

from trust_robot.analytic_marginalized_horizon import (
    NODE_FRAMES,
    long_fixture,
    long_factors,
    GYRO_BIAS_INJECTION,
)

from trust_robot.analytic_inertial_15d import (
    ACCEL_BIAS_INJECTION,
)

from trust_robot.analytic_marginalized_fusion import (
    estimate_marginalized_with_support,
)

SCHEMA = "TRUST_ROBOT_R135_A19_LONG_HORIZON_JOINT_STRESS_V1"
STATUS = "UNTRUSTED_SYNTHETIC_LONG_HORIZON_DIAGNOSTIC_ONLY"

IMU_MODES = ("clean", "accel_bias", "gyro_bias")

OUTAGE_SCHEDULES = (
    ("none", ()),
    ("mid_four", (8, 10, 12, 14)),
    ("mid_six", (8, 10, 12, 14, 16, 18)),
    ("late_five", (14, 16, 18, 20, 22)),
    ("complete", tuple(NODE_FRAMES)),
)

SCHEDULES = dict(OUTAGE_SCHEDULES)

DENIALS = (
    "physical_observability_verified",
    "calibrated_uncertainty_available",
    "physical_localization_accuracy_established",
    "physical_localization_recovery_demonstrated",
    "health_inference_executed",
    "health_label_assigned",
    "factor_weights_modified",
    "camera_factors_injected",
    "recorded_sensor_data_accessed",
    "recorded_ground_truth_accessed",
    "real_factor_execution_authorized",
    "confirmation_test_accessed",
)


class LongHorizonStressError(ValueError):
    """Unexpected manufactured experiment state."""


def _require(condition, message):
    if not condition:
        raise LongHorizonStressError(message)


def _digest(records):
    return hashlib.sha256(
        json.dumps(
            records,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _expected_lidar_edges(outage_frames):
    unavailable = set(outage_frames)

    return {
        (i, j)
        for j in range(1, len(NODE_FRAMES))
        for i in range(max(0, j - 2), j)
        if (
            NODE_FRAMES[i] not in unavailable
            and NODE_FRAMES[j] not in unavailable
        )
    }


def make_condition(imu_mode, outage_name):
    """Build an exclusively manufactured condition.

    Never accepts external sensor readings or references.
    """
    if (
        type(imu_mode) is not str
        or imu_mode not in IMU_MODES
        or type(outage_name) is not str
        or outage_name not in SCHEDULES
    ):
        raise LongHorizonStressError(
            "Unapproved IMU mode or LiDAR outage schedule"
        )

    _require(
        NODE_FRAMES == tuple(range(0, 24, 2))
        and len(OUTAGE_SCHEDULES) == 5,
        "Frozen long-horizon chronology changed",
    )

    fixture, manufactured_reference = long_fixture(
        imu_mode
    )

    # Never pass the manufactured reference to the solver
    # or use it as a localization scoring target.
    del manufactured_reference

    outage = SCHEDULES[outage_name]

    _require(
        len(fixture["imu"]) == 22
        and len(fixture["scans"]) == 23
        and len(fixture["available"]) == 23
        and all(fixture["available"])
        and all(
            type(frame) is int
            and frame in NODE_FRAMES
            for frame in outage
        ),
        "Unexpected manufactured sensor fixture",
    )

    for frame in outage:
        fixture["available"][frame] = False

    return fixture


def verify_manufactured_interventions():
    """Check exactly which original IMU fields change."""
    clean = make_condition("clean", "none")
    accel = make_condition("accel_bias", "none")
    gyro = make_condition("gyro_bias", "none")

    _require(
        all(
            np.array_equal(a, b)
            and np.array_equal(a, c)
            for a, b, c in zip(
                clean["scans"],
                accel["scans"],
                gyro["scans"],
            )
        ),
        "Manufactured LiDAR geometry differs by IMU mode",
    )

    accel_changed = []
    gyro_changed = []

    for k in range(22):
        a = clean["imu"][k]
        b = accel["imu"][k]
        c = gyro["imu"][k]

        _require(
            a["interval_index"] ==
            b["interval_index"] ==
            c["interval_index"] == k
            and a["dt_s"] == b["dt_s"] == c["dt_s"]
            and a["measurement_origin"]
            == b["measurement_origin"]
            == c["measurement_origin"]
            == "ANALYTIC_FIXTURE"
            and a["physical_clock_verified"] is False
            and b["physical_clock_verified"] is False
            and c["physical_clock_verified"] is False,
            "Unexpected IMU provenance or timing",
        )

        d_accel = (
            np.asarray(
                b["specific_force_m_s2"], dtype=float
            )
            - np.asarray(
                a["specific_force_m_s2"], dtype=float
            )
        )

        d_gyro = (
            np.asarray(
                c["gyro_rad_s"], dtype=float
            )
            - np.asarray(
                a["gyro_rad_s"], dtype=float
            )
        )

        if 6 <= k < 15:
            _require(
                np.allclose(
                    d_accel,
                    ACCEL_BIAS_INJECTION,
                    atol=1e-12,
                    rtol=0,
                ),
                "Accelerometer intervention changed",
            )
            accel_changed.append(k)
        else:
            _require(
                np.allclose(
                    d_accel,
                    0.0,
                    atol=1e-12,
                    rtol=0,
                ),
                "Unexpected acceleration corruption",
            )

        if 8 <= k < 18:
            _require(
                np.allclose(
                    d_gyro,
                    GYRO_BIAS_INJECTION,
                    atol=1e-12,
                    rtol=0,
                ),
                "Gyroscope intervention changed",
            )
            gyro_changed.append(k)
        else:
            _require(
                np.allclose(
                    d_gyro,
                    0.0,
                    atol=1e-12,
                    rtol=0,
                ),
                "Unexpected gyroscope corruption",
            )

        _require(
            np.array_equal(
                a["gyro_rad_s"],
                b["gyro_rad_s"],
            )
            and np.array_equal(
                a["specific_force_m_s2"],
                c["specific_force_m_s2"],
            ),
            "Unintended cross-modality IMU change",
        )

    _require(
        accel_changed == list(range(6, 15))
        and gyro_changed == list(range(8, 18)),
        "Unexpected manufactured IMU intervention",
    )

    return {
        "accelerometer_changed_samples": accel_changed,
        "gyroscope_changed_samples": gyro_changed,
        "physical_fault_calibration_verified": False,
        "health_label_generated": False,
        "recorded_data_accessed": False,
    }


def run_case(imu_mode, outage_name):
    """Execute one of 15 frozen 12-node synthetic conditions."""
    fixture = make_condition(imu_mode, outage_name)
    outage = SCHEDULES[outage_name]
    expected_lidar = _expected_lidar_edges(outage)

    captured = []

    def factory(internal_fixture):
        _require(
            internal_fixture is fixture and not captured,
            "Unexpected factor-factory invocation",
        )

        inertial, lidar, counts = long_factors(
            internal_fixture
        )

        _require(
            set(inertial) == {
                (k, k + 1) for k in range(11)
            }
            and set(lidar) == expected_lidar
            and counts["imu_intervals"] == 11
            and counts["unique_imu_sample_count"] == 22
            and counts["imu_samples_reused"] is False
            and counts["lidar_factor_count"]
            == len(expected_lidar),
            "Long-horizon factor ownership changed",
        )

        captured.append({
            "imu_factor_count": len(inertial),
            "lidar_factor_count": len(lidar),
            "lidar_edge_keys": sorted(lidar),
        })

        return inertial, lidar, counts

    outcome = "ACCEPTED"
    rejection = None
    records = None
    audit = None

    try:
        records, audit = estimate_marginalized_with_support(
            fixture,
            node_frames=NODE_FRAMES,
            factor_factory=factory,
            support_policy="report",
        )

    except ValueError as exc:
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
        "Factor factory not called exactly once",
    )

    chosen = captured[0]

    support_windows = []
    total_cost = None
    final_position = None
    digest = None

    if outcome == "ACCEPTED":
        _require(
            len(records) == 12
            and audit["accepted_window_count"] == 11
            and audit["schur_elimination_count"] == 10
            and audit["unaccounted_factor_count"] == 0
            and audit["factor_reuse_after_marginalization"]
            is False
            and audit["imu_samples_reused"] is False
            and audit["lidar_factor_count"]
            == chosen["lidar_factor_count"],
            "Long-horizon estimator accounting failed",
        )

        consumed_imu = {
            tuple(k) for k in audit["consumed_imu_keys"]
        }
        remaining_imu = {
            tuple(k) for k in audit["remaining_imu_keys"]
        }

        consumed_lidar = {
            tuple(k) for k in audit["consumed_lidar_keys"]
        }
        remaining_lidar = {
            tuple(k) for k in audit["remaining_lidar_keys"]
        }

        _require(
            not (consumed_imu & remaining_imu)
            and len(consumed_imu | remaining_imu) == 11
            and not (consumed_lidar & remaining_lidar)
            and consumed_lidar | remaining_lidar
            == expected_lidar,
            "Lost or reused synthetic measurement factor",
        )

        for window in audit["windows"]:
            support = window["factor_support"]

            _require(
                window["accepted"] is True
                and window["jacobian_rank"]
                == window["required_rank"]
                and math.isfinite(float(window["cost"]))
                and float(window["cost"]) >= 0.0
                and support["state_dimension"]
                == window["required_rank"]
                and support["active_imu_factor_count"]
                == window["active_imu_factor_count"]
                and support["active_lidar_factor_count"]
                == window["active_lidar_factor_count"]
                and support["current_lidar_factor_available"]
                is (window["active_lidar_factor_count"] > 0)
                and support["status"] in (
                    "NUMERICALLY_SUPPORTED",
                    "NUMERICALLY_UNAVAILABLE",
                )
                and support["physical_observability_verified"]
                is False
                and support["calibrated_uncertainty_available"]
                is False
                and support[
                    "operational_safety_availability_verified"
                ] is False,
                "Long-horizon numerical support invalid",
            )

            support_windows.append({
                "end_node": window["end_node"],
                "active_lidar_factor_count":
                    support["active_lidar_factor_count"],
                "active_imu_factor_count":
                    support["active_imu_factor_count"],
                "current_lidar_factor_available":
                    support["current_lidar_factor_available"],
                "status": support["status"],
                "availability_diagnostic":
                    support["availability_diagnostic"],
                "numerical_rank": support["numerical_rank"],
                "required_rank": support["state_dimension"],
                "condition_number":
                    support["condition_number"],
            })

        _require(
            len(support_windows) == 11,
            "Missing long-horizon support windows",
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
                "Nonfinite or unauthorized synthetic state",
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
            and all(
                math.isfinite(x) for x in final_position
            ),
            "Invalid long-horizon numerical result",
        )

        digest = _digest(records)

    result = {
        "schema": SCHEMA,
        "status": STATUS,
        "imu_mode": imu_mode,
        "outage_name": outage_name,
        "outage_frame_indices": list(outage),
        "node_count": 12,
        "state_dimension": 15,
        "imu_factor_count": chosen["imu_factor_count"],
        "unique_imu_sample_count": 22,
        "lidar_factor_count": chosen["lidar_factor_count"],
        "lidar_edge_keys": [
            list(e) for e in chosen["lidar_edge_keys"]
        ],
        "solver_outcome": outcome,
        "numerical_rejection": rejection,
        "accepted_window_count": (
            11 if outcome == "ACCEPTED" else None
        ),
        "schur_elimination_count": (
            10 if outcome == "ACCEPTED" else None
        ),
        "support_windows": support_windows,
        "windows_without_current_lidar": (
            sum(
                not w["current_lidar_factor_available"]
                for w in support_windows
            )
            if outcome == "ACCEPTED" else None
        ),
        "numerically_supported_windows": sum(
            w["status"] == "NUMERICALLY_SUPPORTED"
            for w in support_windows
        ),
        "total_window_cost_diagnostic": total_cost,
        "synthetic_final_position_m": final_position,
        "synthetic_state_sha256": digest,
        "manufactured_sensor_origin": True,
        "shared_analytic_motion_model": True,
        "physical_observability_established": False,
    }

    result.update({key: False for key in DENIALS})

    return result


def run_matrix():
    """Execute and compare all 15 manufactured conditions."""
    intervention = verify_manufactured_interventions()

    _require(
        intervention["physical_fault_calibration_verified"]
        is False
        and intervention["health_label_generated"] is False,
        "Unauthorized physical fault interpretation",
    )

    rows = [
        run_case(mode, outage)
        for mode in IMU_MODES
        for outage in SCHEDULES
    ]

    _require(
        len(rows) == 15
        and len({
            (row["imu_mode"], row["outage_name"])
            for row in rows
        }) == 15,
        "Incomplete long-horizon experiment matrix",
    )

    baselines = {
        mode: next(
            row for row in rows
            if row["imu_mode"] == mode
            and row["outage_name"] == "none"
        )
        for mode in IMU_MODES
    }

    _require(
        all(
            row["solver_outcome"] == "ACCEPTED"
            for row in baselines.values()
        ),
        "Manufactured full-LiDAR baseline not accepted",
    )

    clean_reference = baselines["clean"][
        "synthetic_final_position_m"
    ]

    clean_by_outage = {
        row["outage_name"]: row
        for row in rows
        if row["imu_mode"] == "clean"
    }

    for row in rows:
        row["delta_from_same_imu_baseline_m"] = None
        row["delta_from_clean_full_lidar_baseline_m"] = None
        row["delta_from_clean_same_outage_m"] = None

        if row["solver_outcome"] != "ACCEPTED":
            continue

        p = row["synthetic_final_position_m"]

        row["delta_from_same_imu_baseline_m"] = math.dist(
            p,
            baselines[
                row["imu_mode"]
            ]["synthetic_final_position_m"],
        )

        row[
            "delta_from_clean_full_lidar_baseline_m"
        ] = math.dist(p, clean_reference)

        clean_match = clean_by_outage[row["outage_name"]]

        if clean_match["solver_outcome"] == "ACCEPTED":
            row["delta_from_clean_same_outage_m"] = (
                math.dist(
                    p,
                    clean_match["synthetic_final_position_m"],
                )
            )

    return tuple(rows)
