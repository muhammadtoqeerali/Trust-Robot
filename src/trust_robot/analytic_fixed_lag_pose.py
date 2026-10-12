"""Development-only rolling nonlinear SE(3) pose-window benchmark.

Input: synthetic LiDAR scans.
Measurements: frozen Phase-2 relative scan registrations.
Backend: fixed-size pose-only nonlinear least squares.

The analytic fixture reference is used for scoring only.
No calibrated health weights, marginal covariance, physical
synchronization, IMU preintegration or independent reference.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import scipy
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation

from trust_robot.clean_backbone import PoseSE3
from trust_robot.lidar_frontend import LidarFrontendError
from trust_robot.diagnostics import (
    DiagnosticFeatureError,
    extract_lidar_registration_diagnostics,
)
from trust_robot.analytic_se3_geometry_benchmark import (
    CONDITIONS,
    FRAMES,
    estimate,
    evaluate,
    make_fixture,
    register_bounded,
)

SCHEMA = "TRUST_ROBOT_ANALYTIC_FIXED_LAG_POSE_V1"
WINDOW_LENGTH = 5
MAX_FACTOR_GAP = 2
TRANSLATION_SCALE_M = 1.0
ROTATION_SCALE_RAD = 1.0
MAX_NFEV = 60

# These are fixed development residual scales, not measured
# sensor covariances or calibrated trust-layer factor weights.


def canonical(value):
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ) + "\n"
    ).encode("utf-8")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def rotation_from_pose(pose):
    w, x, y, z = pose.quaternion_wxyz
    return Rotation.from_quat([x, y, z, w])


def pose_to_parameters(pose):
    return np.r_[
        np.asarray(pose.translation_m, dtype=np.float64),
        rotation_from_pose(pose).as_rotvec(),
    ]


def parameters_to_pose(values):
    values = np.asarray(values, dtype=np.float64)

    if values.shape != (6,) or not np.isfinite(values).all():
        raise ValueError("Invalid SE3 pose parameter vector")

    qx, qy, qz, qw = Rotation.from_rotvec(
        values[3:]
    ).as_quat()

    return PoseSE3(
        translation_m=tuple(float(x) for x in values[:3]),
        quaternion_wxyz=(
            float(qw),
            float(qx),
            float(qy),
            float(qz),
        ),
    )


def relative_residual(previous, current, observed):
    """Six-dimensional right-invariant relative-pose residual."""
    predicted = previous.inverse().compose(current)
    error = observed.inverse().compose(predicted)

    translation = np.asarray(
        error.translation_m, dtype=np.float64
    ) / TRANSLATION_SCALE_M

    rotation = rotation_from_pose(
        error
    ).as_rotvec() / ROTATION_SCALE_RAD

    return np.r_[translation, rotation]


def make_measurements(clouds):
    """Build only adjacent and lag-two frozen LiDAR factors."""
    if len(clouds) < 2:
        raise ValueError("At least two scans required")

    factors = {}
    failures = []

    for current in range(1, len(clouds)):
        for previous in range(
            max(0, current - MAX_FACTOR_GAP),
            current,
        ):
            try:
                registered = register_bounded(
                    clouds[previous],
                    clouds[current],
                    seconds=3.0,
                )

                diagnostic = extract_lidar_registration_diagnostics(
                    registered.diagnostics
                )

            except (
                LidarFrontendError,
                DiagnosticFeatureError,
                TimeoutError,
                np.linalg.LinAlgError,
            ) as exc:
                failures.append({
                    "previous": previous,
                    "current": current,
                    "error_type": type(exc).__name__,
                })
                continue

            values = {
                f.name: f.value
                for f in diagnostic.features
            }

            if values["source_point_count"] != len(
                clouds[current]
            ):
                raise ValueError("Source scan count mismatch")

            if values["target_point_count"] != len(
                clouds[previous]
            ):
                raise ValueError("Target scan count mismatch")

            factors[previous, current] = {
                "previous": previous,
                "current": current,
                "measurement": (
                    registered.previous_lidar_T_current_lidar
                ),
                "diagnostic_features": values,
            }

        if (current - 1, current) not in factors:
            raise ValueError(
                "Required adjacent scan factor unavailable"
            )

    return factors, failures


def window_residuals(
    variables,
    first_index,
    fixed_boundary_pose,
    factors,
):
    """No reference poses enter this optimization function."""
    n = len(variables) // 6

    if len(variables) != n * 6 or n < 1:
        raise ValueError("Unexpected nonlinear state dimension")

    poses = {first_index: fixed_boundary_pose}

    for j in range(n):
        poses[first_index + j + 1] = parameters_to_pose(
            variables[j * 6:(j + 1) * 6]
        )

    output = []

    for factor in factors:
        output.extend(relative_residual(
            poses[factor["previous"]],
            poses[factor["current"]],
            factor["measurement"],
        ))

    return np.asarray(output, dtype=np.float64)


def refine_window(
    poses,
    start,
    end,
    included_factors,
):
    """Hold the oldest pose fixed; optimize newer window poses."""
    if end <= start or end - start >= WINDOW_LENGTH:
        raise ValueError("Invalid rolling pose window")

    boundary = poses[start]

    x0 = np.concatenate([
        pose_to_parameters(poses[k])
        for k in range(start + 1, end + 1)
    ])

    required_rank = len(x0)

    if len(included_factors) * 6 < required_rank:
        return None, {
            "status": "INSUFFICIENT_FACTOR_CONSTRAINTS",
            "jacobian_rank": None,
            "required_rank": required_rank,
        }

    def residual(x):
        return window_residuals(
            x, start, boundary, included_factors
        )

    fitted = least_squares(
        residual,
        x0,
        method="trf",
        loss="linear",
        max_nfev=MAX_NFEV,
        ftol=1e-10,
        xtol=1e-10,
        gtol=1e-10,
    )

    rank = int(np.linalg.matrix_rank(
        np.asarray(fitted.jac),
        tol=1e-7,
    ))

    accepted = (
        bool(fitted.success)
        and rank == required_rank
        and np.isfinite(fitted.x).all()
        and math.isfinite(float(fitted.cost))
    )

    detail = {
        "status": (
            "OPTIMIZED_FULL_LOCAL_JACOBIAN_RANK"
            if accepted
            else "OPTIMIZATION_NOT_ACCEPTED"
        ),
        "jacobian_rank": rank,
        "required_rank": required_rank,
        "factor_count": len(included_factors),
        "cost": float(fitted.cost),
        "function_evaluations": int(fitted.nfev),
        "local_rank_is_physical_sensor_observability": False,
    }

    if not accepted:
        return None, detail

    updated = {
        start + i + 1: parameters_to_pose(
            fitted.x[i * 6:(i + 1) * 6]
        )
        for i in range(end - start)
    }

    return updated, detail


def estimate_fixed_lag(clouds):
    """Pose-only rolling optimizer; never consumes fixture truth."""
    factors, failures = make_measurements(clouds)

    states = {0: PoseSE3.identity()}
    windows = []

    for current in range(1, len(clouds)):
        adjacent = factors[current - 1, current]["measurement"]

        # Deterministic scan-chain initialization.
        states[current] = states[current - 1].compose(adjacent)

        start = max(0, current - WINDOW_LENGTH + 1)

        included = [
            factor
            for (previous, latest), factor in sorted(factors.items())
            if previous >= start and latest <= current
        ]

        updated, status = refine_window(
            states, start, current, included
        )

        if updated is not None:
            states.update(updated)

        windows.append({
            "end_frame_index": current,
            "start_frame_index": start,
            "oldest_pose_fixed": True,
            "boundary_information_marginalized": False,
            **status,
        })

    output = [
        {
            "sample_index": i,
            "synthetic_time_ns": i * 100_000_000,
            "pose": states[i].to_dict(),
            "pose_source": (
                "FROZEN_LIDAR_FACTORS_AND_ROLLING_POSE_OPTIMIZATION"
            ),
            "reference_pose": None,
        }
        for i in range(len(clouds))
    ]

    return output, {
        "factor_count": len(factors),
        "failed_optional_factors": failures,
        "windows": windows,
        "optimized_window_count": sum(
            w["status"] == "OPTIMIZED_FULL_LOCAL_JACOBIAN_RANK"
            for w in windows
        ),
        "window_count": len(windows),
    }


def execute():
    """Fixture truth goes only to evaluate(), after estimation."""
    lanes, analytic_reference, _ = make_fixture()

    if tuple(lanes) != CONDITIONS:
        raise ValueError("Unexpected analytic fixture conditions")

    results = {}
    artifacts = {}

    for condition in CONDITIONS:
        clouds = lanes[condition]

        baseline = estimate(clouds)
        optimized, solver = estimate_fixed_lag(clouds)

        if len(optimized) != FRAMES:
            raise ValueError("Incomplete pose-window output")

        baseline_metrics = evaluate(
            baseline, analytic_reference
        )
        window_metrics = evaluate(
            optimized, analytic_reference
        )

        results[condition] = {
            "fixed_chain": baseline_metrics,
            "rolling_window": window_metrics,
            "solver": solver,
        }

        name = f"{condition}_rolling_window_poses.jsonl"
        artifacts[name] = b"".join(
            canonical(record) for record in optimized
        )

    clean = results["clean"]

    if (
        clean["solver"]["optimized_window_count"] != FRAMES - 1
        or clean["rolling_window"]["fixture_translation_rmse_m"]
        >= 1e-5
        or clean["rolling_window"]["fixture_rotation_rmse_deg"]
        >= 1e-5
    ):
        raise ValueError(
            "Clean rolling-window mathematical regression failed"
        )

    summary = {
        "schema": SCHEMA,
        "status": "DEVELOPMENT_ONLY_POSE_WINDOW_EXECUTION_PASSED",
        "conditions": list(CONDITIONS),
        "pose_count_per_condition": FRAMES,
        "window_length": WINDOW_LENGTH,
        "maximum_scan_pair_gap": MAX_FACTOR_GAP,
        "solver": "scipy_least_squares_trf",
        "pose_parameterization": "translation_xyz_and_SO3_rotvec",
        "fixed_residual_scales": {
            "translation_m": TRANSLATION_SCALE_M,
            "rotation_rad": ROTATION_SCALE_RAD,
            "chosen_from_sensor_covariance": False,
        },
        "max_function_evaluations_per_window": MAX_NFEV,
        "metrics_by_condition": results,
        "numeric_environment": {
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "scipy": scipy.__version__,
        },
        "derived_output_sha256": {
            name: sha(blob)
            for name, blob in sorted(artifacts.items())
        },
        "frozen_phase2_registration_reused": True,
        "frozen_phase4_diagnostics_reused": True,
        "rolling_nonlinear_SE3_pose_window_executed": True,
        "full_multimodal_fixed_lag_state_estimator_complete": False,
        "probabilistic_marginalization_implemented": False,
        "IMU_velocity_and_bias_states_implemented": False,
        "health_aware_factor_weighting_executed": False,
        "cross_modal_consistency_executed": False,
        "reference_passed_to_estimator": False,
        "reference_origin": "MANUFACTURED_ANALYTIC_FIXTURE",
        "independent_measured_ground_truth": False,
        "physical_synchronization_verified": False,
        "held_out_dataset_evaluation": False,
        "health_model_trained": False,
        "physical_robot_contacted": False,
    }

    return artifacts, summary


def run(destination):
    if destination.exists() or destination.is_symlink():
        raise ValueError("Output already exists")

    if (
        not destination.parent.is_dir()
        or destination.parent.is_symlink()
    ):
        raise ValueError("Unsafe destination parent")

    first_files, first_summary = execute()
    second_files, second_summary = execute()

    if first_files != second_files:
        raise ValueError("Non-deterministic optimizer output")

    if first_summary != second_summary:
        raise ValueError("Non-deterministic optimizer summary")

    first_summary["repeat_derivation_identical"] = True

    destination.mkdir(mode=0o700)

    for name, data in sorted(first_files.items()):
        (destination / name).write_bytes(data)

    (destination / "fixed_lag_manifest_v1.json").write_text(
        json.dumps(first_summary, sort_keys=True, indent=2) + "\n"
    )

    return first_summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()

    m = run(args.destination)

    for condition in CONDITIONS:
        item = m["metrics_by_condition"][condition]

        print(
            condition.upper() + "_WINDOW_SOLVES=",
            item["solver"]["optimized_window_count"],
            "/",
            item["solver"]["window_count"],
        )
        print(
            condition.upper() + "_CHAIN_TRANSLATION_RMSE_M=",
            round(
                item["fixed_chain"]["fixture_translation_rmse_m"],
                8,
            ),
        )
        print(
            condition.upper() + "_WINDOW_TRANSLATION_RMSE_M=",
            round(
                item["rolling_window"]["fixture_translation_rmse_m"],
                8,
            ),
        )

    print("ANALYTIC_REFERENCE_NOT_ESTIMATOR_INPUT=PASS")
    print("REPEATED_DERIVATION=PASS")
    print("FULL_MULTIMODAL_ESTIMATOR=NOT_YET_COMPLETE")
    print("ANALYTIC_FIXED_LAG_POSE_WINDOW=PASS")


if __name__ == "__main__":
    main()
