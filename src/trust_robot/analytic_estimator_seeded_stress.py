"""Seeded synthetic IMU perturbations through the actual 15D estimator.

Not raw-sensor physics, calibrated noise, posterior coverage, or
independently referenced localization evaluation.

The unperturbed estimator run is used ONLY as a numerical sensitivity
baseline. It must not be interpreted as independently measured truth.
"""
from __future__ import annotations

import copy
import json
import math

import numpy as np
from scipy.spatial.transform import Rotation

from trust_robot.analytic_inertial_15d import make_fixture
from trust_robot.analytic_preintegrated_fusion import (
    NODE_FRAMES as FIVE_FRAMES,
    make_factors,
)
from trust_robot.analytic_marginalized_horizon import (
    NODE_FRAMES as LONG_FRAMES,
    long_fixture,
    long_factors,
)
from trust_robot.analytic_marginalized_fusion import (
    estimate_marginalized_with_support,
)

SCHEMA = "TRUST_ROBOT_ANALYTIC_ESTIMATOR_SEEDED_STRESS_DEV_V1"
SEEDS = (3, 17, 29, 61, 83, 127)
SCALES = {"mild": 1.0, "severe": 8.0}
GYRO_NOISE_STD = 0.001
ACCEL_NOISE_STD = 0.01


def perturb_imu(fixture, seed, scale):
    """Apply paired manufactured random IMU perturbations.

    The input fixture is deep-copied. Index, timing, source-origin and
    clock-qualification metadata must remain unchanged.
    """
    if (
        isinstance(seed, bool)
        or not isinstance(seed, (int, np.integer))
        or int(seed) < 0
        or isinstance(scale, bool)
        or not isinstance(scale, (int, float, np.number))
        or not math.isfinite(float(scale))
        or float(scale) < 0
        or float(scale) > 100
    ):
        raise ValueError("Invalid manufactured perturbation settings")

    altered = copy.deepcopy(fixture)
    rng = np.random.default_rng(int(seed))

    for index, row in enumerate(altered["imu"]):
        if (
            row["interval_index"] != index
            or row["measurement_origin"] != "ANALYTIC_FIXTURE"
            or row["physical_clock_verified"] is not False
        ):
            raise ValueError("Unqualified synthetic IMU input")

        for key, std in (
            ("gyro_rad_s", GYRO_NOISE_STD),
            ("specific_force_m_s2", ACCEL_NOISE_STD),
        ):
            original = np.asarray(row[key], dtype=float)
            if original.shape != (3,) or not np.isfinite(original).all():
                raise ValueError("Malformed synthetic IMU vector")

            changed = (
                original
                + float(scale)*std*rng.standard_normal(3)
            )
            row[key] = changed.tolist()

    return altered


def get_problem(horizon, condition):
    if horizon == "five":
        if condition not in ("clean", "lidar_dropout"):
            raise ValueError("Invalid five-node condition")
        fixture, _ = make_fixture(condition)
        return fixture, FIVE_FRAMES, make_factors

    if horizon == "twelve":
        if condition not in ("clean", "lidar_outage"):
            raise ValueError("Invalid twelve-node condition")
        generated = long_fixture(condition)
        fixture = (
            generated[0]
            if isinstance(generated, tuple)
            else generated
        )
        return fixture, LONG_FRAMES, long_factors

    raise ValueError("Unknown estimator horizon")


def solve(fixture, frames, factory):
    return estimate_marginalized_with_support(
        fixture,
        node_frames=frames,
        factor_factory=factory,
        support_policy="report",
    )


def baseline_drift(reference, predicted):
    """Difference relative to unperturbed ESTIMATOR, not truth."""
    if len(reference) != len(predicted):
        raise ValueError("Unequal estimated trajectory lengths")

    position_errors = []
    rotation_errors = []

    for a, b in zip(reference, predicted):
        pa = np.asarray(a["position_m"], dtype=float)
        pb = np.asarray(b["position_m"], dtype=float)

        qa = np.asarray(
            a["orientation_quaternion_wxyz"], dtype=float
        )
        qb = np.asarray(
            b["orientation_quaternion_wxyz"], dtype=float
        )

        if (
            pa.shape != (3,) or pb.shape != (3,)
            or qa.shape != (4,) or qb.shape != (4,)
            or not np.isfinite(pa).all()
            or not np.isfinite(pb).all()
            or not np.isfinite(qa).all()
            or not np.isfinite(qb).all()
        ):
            raise ValueError("Invalid estimator trajectory record")

        ra = Rotation.from_quat(np.r_[qa[1:], qa[0]])
        rb = Rotation.from_quat(np.r_[qb[1:], qb[0]])

        position_errors.append(float(np.sum((pa-pb)**2)))
        rotation_errors.append(float(
            (ra.inv()*rb).magnitude()**2
        ))

    return {
        "position_rmse_from_unperturbed_estimate_m": float(
            np.sqrt(np.mean(position_errors))
        ),
        "rotation_rmse_from_unperturbed_estimate_deg": float(
            np.rad2deg(np.sqrt(np.mean(rotation_errors)))
        ),
    }


def condition_study(horizon, condition, seeds=SEEDS):
    fixture, frames, factory = get_problem(horizon, condition)

    reference, baseline_info = solve(fixture, frames, factory)

    if len(reference) != len(frames):
        raise ValueError("Incomplete unperturbed state trajectory")

    baseline_support = [
        row["factor_support"]
        for row in baseline_info["windows"]
    ]

    trials = []

    for seed in seeds:
        for label, scale in SCALES.items():
            modified = perturb_imu(fixture, seed, scale)

            try:
                predicted, result = solve(
                    modified, frames, factory
                )
            except ValueError as exc:
                # An explicitly rejected solve is recorded, never
                # relabelled as a successfully estimated trajectory.
                trials.append({
                    "seed": int(seed),
                    "noise_level": label,
                    "scale": float(scale),
                    "status": "SOLVER_UNAVAILABLE",
                    "error_type": type(exc).__name__,
                    "error_detail": str(exc)[:180],
                })
                continue

            metrics = baseline_drift(reference, predicted)
            supports = [
                row["factor_support"]
                for row in result["windows"]
            ]

            trials.append({
                "seed": int(seed),
                "noise_level": label,
                "scale": float(scale),
                "status": "SOLVED",
                **metrics,
                "windows": len(supports),
                "numerically_supported_windows": sum(
                    s["status"] == "NUMERICALLY_SUPPORTED"
                    for s in supports
                ),
                "windows_without_current_lidar": sum(
                    not s["current_lidar_factor_available"]
                    for s in supports
                ),
                "physical_observability_verified": False,
            })

    solved = [
        row for row in trials
        if row["status"] == "SOLVED"
    ]

    for row in solved:
        for key in (
            "position_rmse_from_unperturbed_estimate_m",
            "rotation_rmse_from_unperturbed_estimate_deg",
        ):
            if not np.isfinite(row[key]) or row[key] < 0:
                raise ValueError("Invalid sensitivity metric")

    return {
        "horizon": horizon,
        "condition": condition,
        "node_count": len(frames),
        "baseline_windows": len(baseline_support),
        "baseline_numerically_supported_windows": sum(
            s["status"] == "NUMERICALLY_SUPPORTED"
            for s in baseline_support
        ),
        "baseline_windows_without_current_lidar": sum(
            not s["current_lidar_factor_available"]
            for s in baseline_support
        ),
        "trial_count": len(trials),
        "solved_count": len(solved),
        "unavailable_count": len(trials)-len(solved),
        "trials": trials,
        "baseline_is_independent_ground_truth": False,
    }


def execute():
    scenarios = [
        condition_study("five", "clean"),
        condition_study("five", "lidar_dropout"),
        condition_study("twelve", "clean"),
        condition_study("twelve", "lidar_outage"),
    ]

    if any(
        row["trial_count"] != 2*len(SEEDS)
        for row in scenarios
    ):
        raise ValueError("Incomplete seeded synthetic experiment")

    if not all(
        row["baseline_windows"] == row["node_count"]-1
        for row in scenarios
    ):
        raise ValueError("Incomplete baseline estimator")

    return {
        "schema": SCHEMA,
        "status": "SEEDED_SYNTHETIC_ESTIMATOR_STUDY_EXECUTED",
        "seeds": list(SEEDS),
        "manufactured_noise": {
            "gyro_std_rad_s": GYRO_NOISE_STD,
            "specific_force_std_m_s2": ACCEL_NOISE_STD,
            "scales": SCALES,
            "empirically_calibrated": False,
        },
        "scenarios": scenarios,
        "seeding_partition": "synthetic_development_only",
        "unperturbed_estimate_is_truth": False,
        "real_sensor_data_used": False,
        "posterior_coverage_assessed": False,
        "physical_observability_verified": False,
        "trust_conditioning_executed": False,
        "physical_robot_used": False,
    }


def canonical(obj):
    return (
        json.dumps(
            obj, sort_keys=True,
            separators=(",", ":"), allow_nan=False,
        ) + "\n"
    ).encode("utf-8")
