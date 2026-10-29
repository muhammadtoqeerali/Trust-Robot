"""R135-A18: coupled IMU corruption and LiDAR dropout.

All 128 subsets of the frozen synthetic LiDAR graph are
crossed with two fixed manufactured IMU conditions through
the unchanged 15D Schur-marginalized estimator.

Opt-in numerical support reporting uses the fitted Jacobian,
Schur prior and existing factor-ownership diagnostics.

A successful nonlinear solve is NOT evidence of active
LiDAR support, physical observability or localization safety.

No camera factors are injected in this phase.
No real sensor data, GT scoring, health inference, factor
weight modifications or held-out test access.
"""
from __future__ import annotations

from itertools import combinations
import hashlib
import json
import math

import numpy as np

from trust_robot.analytic_inertial_15d import (
    make_fixture,
    ACCEL_BIAS_INJECTION,
)
from trust_robot.analytic_preintegrated_fusion import (
    NODE_FRAMES,
    make_factors,
)
from trust_robot.analytic_marginalized_fusion import (
    estimate_marginalized_with_support,
)
from trust_robot.analytic_depth_camera_source_v1 import EDGES

SCHEMA = "TRUST_ROBOT_R135_A18_JOINT_IMU_LIDAR_STRESS_V1"
STATUS = "UNTRUSTED_SYNTHETIC_JOINT_SENSOR_STRESS_ONLY"
IMU_MODES = ("clean", "accel_bias")

DROPSETS = tuple(
    subset
    for count in range(len(EDGES) + 1)
    for subset in combinations(EDGES, count)
)

EXPECTED_EDGES = frozenset((
    (0, 1), (0, 2), (1, 2), (1, 3),
    (2, 3), (2, 4), (3, 4),
))

EXPECTED_IMU = frozenset((
    (0, 1), (1, 2), (2, 3), (3, 4),
))

DENIALS = (
    "physical_observability_established",
    "physical_accuracy_established",
    "physical_recovery_demonstrated",
    "real_sensor_support_established",
    "calibrated_covariance_available",
    "health_inference_executed",
    "health_label_assigned",
    "factor_weights_modified",
    "camera_factor_injected",
    "recorded_sensor_data_accessed",
    "recorded_ground_truth_accessed",
    "real_factor_execution_authorized",
    "confirmation_test_accessed",
)


class SyntheticDropoutError(ValueError):
    """Invalid frozen dropout selection or scientific contract."""


def _require(ok, message):
    if not ok:
        raise SyntheticDropoutError(message)


def _digest(value):
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _validate_drop_set(removed_edges):
    if type(removed_edges) is not tuple:
        return False

    for edge in removed_edges:
        if (
            type(edge) is not tuple
            or len(edge) != 2
            or any(type(index) is not int for index in edge)
        ):
            return False

    return removed_edges in DROPSETS


def run_case(removed_edges=(), imu_mode="clean"):
    """Run one frozen LiDAR-removal combination.

    No external fixture, measurements, model weights,
    probabilities, ground truth or callbacks are accepted.
    """
    if (
        not _validate_drop_set(removed_edges)
        or type(imu_mode) is not str
        or imu_mode not in IMU_MODES
    ):
        raise SyntheticDropoutError(
            "Invalid or noncanonical LiDAR dropout set"
        )

    _require(
        NODE_FRAMES == (0, 2, 4, 6, 8)
        and tuple(EDGES) == (
            (0, 1), (0, 2), (1, 2), (1, 3),
            (2, 3), (2, 4), (3, 4),
        )
        and len(DROPSETS) == 128,
        "Frozen synthetic topology changed",
    )

    fixture, synthetic_reference = make_fixture(imu_mode)
    del synthetic_reference

    selected_holder = []

    def factory(internal_fixture):
        _require(
            internal_fixture is fixture
            and not selected_holder,
            "Unexpected factor-factory invocation",
        )

        inertial, lidar, counts = make_factors(
            internal_fixture
        )

        _require(
            set(inertial) == EXPECTED_IMU
            and set(lidar) == EXPECTED_EDGES
            and counts["imu_intervals"] == 4
            and counts["lidar_factor_count"] == 7
            and counts["imu_samples_reused"] is False,
            "Frozen synthetic factor set changed",
        )

        selected = {
            edge: measurement
            for edge, measurement in lidar.items()
            if edge not in removed_edges
        }

        _require(
            len(selected) == 7 - len(removed_edges)
            and set(selected) == (
                EXPECTED_EDGES - set(removed_edges)
            ),
            "Unexpected factor-removal result",
        )

        metadata = dict(counts)
        metadata["lidar_factor_count"] = len(selected)

        selected_holder.append({
            "selected_edges": tuple(sorted(selected)),
            "selected_count": len(selected),
        })

        return inertial, selected, metadata

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

        # Only the solver's already-published numerical
        # window rejection may be recorded as an outcome.
        # Any other ValueError or FactorSupportError
        # propagates and stops publication.
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
        len(selected_holder) == 1,
        "Factor factory not invoked exactly once",
    )

    selected = selected_holder[0]

    window_reports = []
    final_position = None
    total_cost = None
    state_digest = None

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
            == selected["selected_count"],
            "Estimator accounting or output violated",
        )

        consumed = {
            tuple(x) for x in audit["consumed_lidar_keys"]
        }

        live = {
            tuple(x) for x in audit["remaining_lidar_keys"]
        }

        _require(
            not (consumed & live)
            and consumed | live
            == set(selected["selected_edges"]),
            "LiDAR factor reuse or omission",
        )

        _require(
            len(audit["windows"]) == 4,
            "Unexpected estimator window chronology",
        )

        for window in audit["windows"]:
            support = window["factor_support"]

            _require(
                window["accepted"] is True
                and window["jacobian_rank"]
                == window["required_rank"]
                and math.isfinite(float(window["cost"]))
                and support["state_dimension"]
                == window["required_rank"]
                and support["active_imu_factor_count"]
                == window["active_imu_factor_count"]
                and support["active_lidar_factor_count"]
                == window["active_lidar_factor_count"]
                and support["current_lidar_factor_available"]
                is (
                    window["active_lidar_factor_count"] > 0
                )
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
                "Numerical support contract failed",
            )

            condition = support["condition_number"]

            _require(
                condition is None
                or (
                    math.isfinite(float(condition))
                    and float(condition) >= 1.0
                ),
                "Invalid numerical condition diagnostic",
            )

            availability = support["availability_diagnostic"]

            _require(
                availability in (
                    "CURRENT_LIDAR_SUPPORTED",
                    "NO_CURRENT_LIDAR_FACTOR",
                    "NUMERICALLY_UNAVAILABLE",
                ),
                "Unexpected support availability category",
            )

            window_reports.append({
                "end_node": window["end_node"],
                "status": support["status"],
                "availability_diagnostic": availability,
                "active_lidar_factor_count":
                    support["active_lidar_factor_count"],
                "active_imu_factor_count":
                    support["active_imu_factor_count"],
                "current_lidar_factor_available":
                    support["current_lidar_factor_available"],
                "numerical_rank": support["numerical_rank"],
                "required_rank": support["state_dimension"],
                "condition_number": condition,
                "physical_observability_verified": False,
                "calibrated_uncertainty_available": False,
                "operational_safety_availability_verified":
                    False,
            })

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
                "Nonfinite or unauthorized state output",
            )

        final_position = [
            float(x) for x in records[-1]["position_m"]
        ]

        total_cost = math.fsum(
            float(w["cost"]) for w in audit["windows"]
        )

        _require(
            math.isfinite(total_cost)
            and total_cost >= 0.0
            and all(math.isfinite(x) for x in final_position),
            "Nonfinite synthetic solver result",
        )

        state_digest = _digest(records)

    result = {
        "schema": SCHEMA,
        "imu_mode": imu_mode,
        "manufactured_accel_bias_injected": (
            imu_mode == "accel_bias"
        ),
        "status": STATUS,
        "removed_edges": [
            list(edge) for edge in removed_edges
        ],
        "removed_lidar_factor_count": len(removed_edges),
        "remaining_lidar_factor_count":
            selected["selected_count"],
        "synthetic_imu_factor_count": 4,
        "node_count": 5,
        "state_dimension": 15,
        "solver_outcome": outcome,
        "numerical_rejection": rejection,
        "support_windows": window_reports,
        "accepted_window_count": (
            4 if outcome == "ACCEPTED" else None
        ),
        "schur_elimination_count": (
            3 if outcome == "ACCEPTED" else None
        ),
        "total_window_cost_diagnostic": total_cost,
        "synthetic_final_position_m": final_position,
        "synthetic_state_sha256": state_digest,
        "all_windows_have_current_lidar": (
            all(
                w["current_lidar_factor_available"]
                and w["status"] == "NUMERICALLY_SUPPORTED"
                for w in window_reports
            )
            if outcome == "ACCEPTED" else False
        ),
        "numerically_supported_window_count": sum(
            w["status"] == "NUMERICALLY_SUPPORTED"
            for w in window_reports
        ),
        "windows_without_current_lidar": sum(
            not w["current_lidar_factor_available"]
            for w in window_reports
        ),
        "synthetic_initial_anchor_only": True,
        "physical_observability_verified": False,
    }

    result.update({name: False for name in DENIALS})

    return result



def manufactured_imu_intervention():
    """Verify the original frozen IMU intervention inputs.

    This compares synthetic sensor fields, not estimator
    performance against generated reference poses.
    """
    clean, clean_reference = make_fixture("clean")
    biased, biased_reference = make_fixture("accel_bias")

    del clean_reference, biased_reference

    _require(
        len(clean["imu"]) == len(biased["imu"]) == 8,
        "Unexpected synthetic IMU sample count",
    )

    _require(
        all(
            np.array_equal(a, b)
            for a, b in zip(
                clean["scans"], biased["scans"]
            )
        ),
        "Manufactured LiDAR scans changed with IMU mode",
    )

    changed = []

    for index, (a, b) in enumerate(
        zip(clean["imu"], biased["imu"])
    ):
        _require(
            a["interval_index"] == b["interval_index"]
            == index
            and a["dt_s"] == b["dt_s"]
            and a["gyro_rad_s"] == b["gyro_rad_s"]
            and a["measurement_origin"] == "ANALYTIC_FIXTURE"
            and b["measurement_origin"] == "ANALYTIC_FIXTURE"
            and a["physical_clock_verified"] is False
            and b["physical_clock_verified"] is False,
            "Unexpected manufactured IMU provenance",
        )

        difference = (
            np.asarray(
                b["specific_force_m_s2"], dtype=float
            )
            - np.asarray(
                a["specific_force_m_s2"], dtype=float
            )
        )

        if index in (3, 4, 5):
            _require(
                np.allclose(
                    difference,
                    ACCEL_BIAS_INJECTION,
                    rtol=0,
                    atol=1e-12,
                ),
                "Frozen accelerometer bias magnitude changed",
            )
            changed.append(index)
        else:
            _require(
                np.allclose(
                    difference,
                    np.zeros(3),
                    rtol=0,
                    atol=1e-12,
                ),
                "Unexpected IMU sample modification",
            )

    _require(
        changed == [3, 4, 5],
        "Unexpected manufactured corruption interval",
    )

    return {
        "changed_imu_sample_indices": changed,
        "manufactured_specific_force_offset_m_s2": [
            float(x) for x in ACCEL_BIAS_INJECTION
        ],
        "original_imu_samples": 8,
        "physical_health_label_assigned": False,
        "physical_calibration_verified": False,
        "recorded_data_accessed": False,
    }


def run_matrix():
    """Execute 256 frozen joint IMU/LiDAR configurations."""
    intervention = manufactured_imu_intervention()

    _require(
        intervention["changed_imu_sample_indices"]
        == [3, 4, 5],
        "Frozen IMU intervention not verified",
    )

    rows = tuple(
        run_case(subset, mode)
        for mode in IMU_MODES
        for subset in DROPSETS
    )

    _require(
        len(rows) == 256
        and len({
            (
                row["imu_mode"],
                tuple(
                    tuple(edge)
                    for edge in row["removed_edges"]
                ),
            )
            for row in rows
        }) == 256,
        "Incomplete joint sensor-fault matrix",
    )

    baselines = {
        mode: rows[i * len(DROPSETS)]
        for i, mode in enumerate(IMU_MODES)
    }

    _require(
        all(
            row["solver_outcome"] == "ACCEPTED"
            for row in baselines.values()
        ),
        "Manufactured full-LiDAR baselines unavailable",
    )

    clean_reference = baselines["clean"][
        "synthetic_final_position_m"
    ]

    for row in rows:
        row[
            "final_position_delta_from_same_imu_baseline_m"
        ] = None

        row[
            "final_position_delta_from_clean_baseline_m"
        ] = None

        if row["solver_outcome"] == "ACCEPTED":
            current = row["synthetic_final_position_m"]

            same_reference = baselines[
                row["imu_mode"]
            ]["synthetic_final_position_m"]

            row[
                "final_position_delta_from_same_imu_baseline_m"
            ] = math.dist(current, same_reference)

            row[
                "final_position_delta_from_clean_baseline_m"
            ] = math.dist(current, clean_reference)

    return rows
