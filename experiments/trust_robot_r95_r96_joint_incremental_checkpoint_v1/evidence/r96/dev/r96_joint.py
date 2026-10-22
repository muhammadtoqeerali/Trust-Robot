"""R96 guarded synthetic Gaussian joint-prior integration.

Reuses R95/R88 inertial linearizations and the manufactured
camera/LiDAR covariance scales from S6.

Camera and LiDAR constraints here are artificial 6D endpoint
tangent-space observations. They are not S6 nonlinear SE(3)
relative-pose measurements or real sensor factors.

Each prefix is recomputed for independent audit. This does
not establish an online real-time nonlinear estimator.
"""

import json
import math
import numpy as np

import r84_gap_frontend as gap
import r88_schur as schur
import r90_prior_guard as guard
import r95_incremental as r95

from s6_joint_fusion import CAMERA_STD, LIDAR_STD
from trust_robot.multimodal_factor_interface import (
    ANALYTIC_ORIGIN,
    ANALYTIC_FRAME,
    CAMERA_SOURCE,
    LIDAR_SOURCE,
)

SCHEMA = "TRUST_ROBOT_R96_SYNTHETIC_JOINT_INCREMENTAL_GAUSSIAN_V1"

N = 15
K = 6
B = np.eye(N)[:K, :]

MODES = {
    "both": ("camera", "lidar"),
    "camera": ("camera",),
    "lidar": ("lidar",),
    "imu": (),
}

STD = {
    "camera": np.asarray(CAMERA_STD, dtype=float),
    "lidar": np.asarray(LIDAR_STD, dtype=float),
}

SOURCES = {
    "camera": CAMERA_SOURCE,
    "lidar": LIDAR_SOURCE,
}

class IntegrationError(ValueError):
    pass

def need(ok, reason):
    if not ok:
        raise IntegrationError(reason)

def canonical(obj):
    return (
        json.dumps(
            obj,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        ) + "\n"
    ).encode()

def make_unaries(segment_id, step, mode):
    need(mode in MODES, "UNKNOWN_MODE")
    need(
        type(segment_id) is int
        and type(step) is int
        and 0 <= segment_id <= 100
        and 0 <= step <= 100,
        "WINDOW_ID",
    )

    result = []

    for modality in MODES[mode]:
        std = STD[modality]

        need(
            std.shape == (K,)
            and np.isfinite(std).all()
            and np.all(std > 0),
            "INVALID_ASSUMED_NOISE",
        )

        axis = np.arange(K, dtype=float)

        if modality == "camera":
            z = 0.055 * np.sin(
                axis + step + segment_id
            )
        else:
            z = 0.035 * np.cos(
                axis + step + segment_id
            )

        result.append({
            "modality": modality,
            "measurement_id":
                f"analytic_{modality}_{segment_id}_{step}",
            "source_id": SOURCES[modality],
            "origin": ANALYTIC_ORIGIN,
            "frame_id": ANALYTIC_FRAME,
            "segment_id": segment_id,
            "step": step,
            "observation": z,
            "covariance": np.diag(std * std),
            "physical_factor_authorized": False,
        })

    return tuple(result)

def validate_unaries(items, segment_id, step, mode):
    need(mode in MODES, "UNKNOWN_MODE")
    need(type(items) is tuple, "FACTOR_CONTAINER")
    need(len(items) == len(MODES[mode]), "FACTOR_COUNT")

    required = {
        "modality",
        "measurement_id",
        "source_id",
        "origin",
        "frame_id",
        "segment_id",
        "step",
        "observation",
        "covariance",
        "physical_factor_authorized",
    }

    seen = set()
    modalities = []

    for f in items:
        need(
            type(f) is dict and set(f) == required,
            "FACTOR_FIELDS",
        )

        m = f["modality"]

        need(m in MODES[mode], "MODALITY")
        need(f["source_id"] == SOURCES[m], "SOURCE")
        need(f["origin"] == ANALYTIC_ORIGIN, "ORIGIN")
        need(f["frame_id"] == ANALYTIC_FRAME, "FRAME")

        need(
            type(f["segment_id"]) is int
            and type(f["step"]) is int
            and f["segment_id"] == segment_id
            and f["step"] == step,
            "WINDOW_OWNERSHIP",
        )

        need(
            f["physical_factor_authorized"] is False,
            "PHYSICAL_FACTOR_DENIED",
        )

        ident = f["measurement_id"]

        need(
            type(ident) is str
            and ident == f"analytic_{m}_{segment_id}_{step}"
            and ident not in seen,
            "MEASUREMENT_ID",
        )

        seen.add(ident)
        modalities.append(m)

        z = f["observation"]
        C = f["covariance"]

        need(
            type(z) is np.ndarray
            and z.shape == (K,)
            and np.isfinite(z).all(),
            "OBSERVATION",
        )

        need(
            type(C) is np.ndarray
            and C.shape == (K, K)
            and np.isfinite(C).all()
            and np.array_equal(
                C, np.diag(STD[m] * STD[m])
            ),
            "COVARIANCE",
        )

    need(
        tuple(modalities) == MODES[mode],
        "MODALITY_ORDER",
    )

    return True

def incremental_prefix(factors, segment_id, mode):
    need(bool(factors), "EMPTY_PREFIX")

    H = None
    g = None
    c = None

    for step, (Ai, Aj, y, _) in enumerate(factors):
        unaries = make_unaries(segment_id, step, mode)
        validate_unaries(
            unaries, segment_id, step, mode
        )

        if step == 0:
            H = schur.require_spd(
                Aj.T @ Aj + schur.RIDGE**2 * np.eye(N)
            )
            g = Aj.T @ y
            c = 0.5 * float(y @ y)
        else:
            H, g, c = schur.schur(
                H, g, c, Ai, Aj, y
            )

        for f in unaries:
            L = np.linalg.cholesky(f["covariance"])
            U = np.linalg.solve(L, B)
            v = np.linalg.solve(L, f["observation"])

            H = H + U.T @ U
            g = g + U.T @ v
            c = c + 0.5 * float(v @ v)

        record = guard.make_record(
            H, g, c, segment_id
        )

        shift = 3e-5 * np.sin(
            np.arange(N, dtype=float)
            + segment_id + step
        )

        admitted = guard.admit(
            record,
            segment_id,
            guard.token(segment_id),
            shift,
        )

        need(
            admitted["real_sensor_factor_executable"]
            is False,
            "REAL_FACTOR_ADMISSION",
        )

        need(
            admitted["frozen_jacobians_modified"]
            is False,
            "NONLINEAR_REFRESH",
        )

    return H, g, c

def independent_batch(factors, segment_id, mode):
    """Independent full-batch Gaussian assembly."""

    m = len(factors)
    active = MODES[mode]

    stride = 2 * N + K * len(active)

    A = np.zeros((stride * m, N * m))
    b = np.zeros(stride * m)

    for step, (Ai, Aj, y, _) in enumerate(factors):
        row = stride * step
        col = N * step

        A[row:row+N, col:col+N] = Aj

        if step:
            A[row:row+N, col-N:col] = Ai

        b[row:row+N] = y

        A[
            row+N:row+2*N,
            col:col+N
        ] = schur.RIDGE * np.eye(N)

        cursor = row + 2*N

        unaries = make_unaries(segment_id, step, mode)

        validate_unaries(
            unaries, segment_id, step, mode
        )

        for f in unaries:
            inv = 1.0 / np.sqrt(
                np.diag(f["covariance"])
            )

            A[
                cursor:cursor+K,
                col:col+N
            ] = inv[:, None] * B

            b[cursor:cursor+K] = (
                inv * f["observation"]
            )

            cursor += K

        need(
            cursor == row + stride,
            "BATCH_ROW_ACCOUNTING",
        )

    solution = np.linalg.lstsq(
        A, b, rcond=None
    )[0]

    H = schur.require_spd(A.T @ A)

    covariance = np.linalg.solve(
        H, np.eye(N*m)
    )[-N:, -N:]

    cost = 0.5 * float(
        np.linalg.norm(A @ solution - b)**2
    )

    return solution[-N:], covariance, cost

def run_case(name, mode="both", packets=None):
    need(name in r95.CASES, "UNKNOWN_SCENARIO")
    need(mode in MODES, "UNKNOWN_MODE")

    if packets is None:
        packets = gap.fixture(name)

    segments, gap_count = schur.segment_groups(packets)

    rows = []
    previous_end = None
    prefix_count = 0
    eliminated = 0

    for sid, groups in enumerate(segments):
        if previous_end is not None:
            need(
                groups[0][0] > previous_end,
                "CROSS_GAP_CONTINUITY",
            )

        factors = schur.synthetic_factors(groups, sid)

        windows = []

        for step in range(len(factors)):
            prefix = factors[:step+1]

            H, g, c = incremental_prefix(
                prefix, sid, mode
            )

            x = np.linalg.solve(H, g)
            cov = np.linalg.solve(H, np.eye(N))

            xb, covb, batch_cost = independent_batch(
                prefix, sid, mode
            )

            state_error = float(
                np.linalg.norm(x-xb)
            )

            covariance_error = float(
                np.linalg.norm(cov-covb)
                / max(1e-12, np.linalg.norm(covb))
            )

            prior_cost = float(
                0.5*x@H@x - g@x + c
            )

            cost_error = abs(
                prior_cost - batch_cost
            )

            need(
                state_error < 1e-4
                and covariance_error < 2e-3
                and cost_error < 1e-5,
                "INCREMENTAL_BATCH_MISMATCH",
            )

            windows.append({
                "step": step,
                "modalities": list(MODES[mode]),
                "pose_unary_count":
                    len(MODES[mode]) * (step+1),
                "state_l2_error": state_error,
                "covariance_relative_error":
                    covariance_error,
                "cost_abs_error": cost_error,
                "covariance_trace":
                    float(np.trace(cov)),
                "real_factors_executed": False,
            })

            prefix_count += 1

            if step:
                eliminated += 1

        rows.append({
            "segment_id": sid,
            "windows": windows,
            "new_manufactured_anchor": True,
            "prior_carried_across_gap": False,
        })

        previous_end = groups[-1][1]

    return {
        "scenario": name,
        "mode": mode,
        "segments": len(segments),
        "timestamp_gaps": gap_count,
        "prefix_windows": prefix_count,
        "eliminated_old_states": eliminated,
        "cross_gap_prior_carries": 0,
        "rows": rows,
    }

def execute():
    upstream = r95.execute()

    need(
        upstream["incremental_prefix_windows"] == 16
        and upstream["scientific_gates_closed"] == 11,
        "R95_LINEAGE",
    )

    cases = {
        name: run_case(name)
        for name in r95.CASES
    }

    ablations = {
        mode: run_case("continuous", mode)
        for mode in ("camera", "lidar", "imu")
    }

    joint = cases["continuous"]["rows"][0][
        "windows"
    ][-1]["covariance_trace"]

    traces = {
        mode: result["rows"][0]["windows"][-1][
            "covariance_trace"
        ]
        for mode, result in ablations.items()
    }

    need(
        joint <= traces["camera"] + 1e-9
        and joint <= traces["lidar"] + 1e-9
        and traces["camera"] <= traces["imu"] + 1e-9
        and traces["lidar"] <= traces["imu"] + 1e-9,
        "ASSUMED_INFORMATION_ORDER",
    )

    reports = list(cases.values()) + list(
        ablations.values()
    )

    prefixes = sum(
        row["prefix_windows"] for row in reports
    )

    eliminated = sum(
        row["eliminated_old_states"]
        for row in reports
    )

    need(
        prefixes == 28
        and eliminated == 20
        and sum(
            row["timestamp_gaps"]
            for row in cases.values()
        ) == 1,
        "PREFIX_ACCOUNTING",
    )

    return {
        "schema": SCHEMA,
        "status": "PASS_SYNTHETIC_SOFTWARE_ONLY",
        "cases": cases,
        "ablations": ablations,
        "total_prefix_evaluations": prefixes,
        "total_eliminated_old_states": eliminated,
        "information_order_check": True,
        "separate_camera_lidar_covariances": True,
        "measurement_type":
            "MANUFACTURED_6D_TANGENT_SPACE_UNARY",
        "s6_nonlinear_pose_factors_executed": False,
        "real_sensor_factors_executed": False,
        "physical_clock_verified": False,
        "physical_extrinsics_verified": False,
        "physical_covariance_verified": False,
        "health_training_authorized": False,
        "ate_rpe_authorized": False,
        "confirmation_test_accessed": False,
        "raw_gt_or_rosbags_opened": False,
        "scientific_gates_closed": 11,
    }

if __name__ == "__main__":
    import sys

    result = execute()

    with open(
        sys.argv[1], "x", encoding="utf-8"
    ) as f:
        f.write(canonical(result).decode())

    print("R96_JOINT_GAUSSIAN_INTEGRATION=PASS")
    print("R96_SYNTHETIC_CASES=4")
    print("R96_PREFIX_EVALUATIONS=28")
    print("R96_OLD_STATE_ELIMINATIONS=20")
    print("R96_CAMERA_LIDAR_IMU_ABLATIONS=PASS")
    print("R96_REAL_SENSOR_FACTORS=DENIED")
