"""S6 opt-in 15D joint synthetic camera/LiDAR/IMU estimator.

Retains two independent *software factor identities* on the
same edge and distinct assumed six-dimensional covariances.

Sensor-noise independence is not empirically demonstrated.
No recorded M2DGR data or physically qualified pose factors
may enter this solver.
"""

from dataclasses import dataclass
import argparse
import hashlib
import json
import math
import xml.etree.ElementTree as ET

import numpy as np
from scipy.linalg import solve_triangular
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation

from trust_robot.clean_backbone import PoseSE3
from trust_robot.analytic_inertial_15d import (
    as_pose,
    initial_state,
    make_fixture,
    predict_imu,
)
from trust_robot.analytic_preintegrated_fusion import (
    NODE_FRAMES,
    make_factors,
    whitened_inertial_residual,
)
from trust_robot.analytic_schur_marginalization import (
    STATE_DIM,
    synthetic_initial_anchor,
    marginalize_one,
)
from trust_robot.analytic_three_modality_bridge import (
    manufactured_camera_packets,
)
from trust_robot.multimodal_factor_interface import (
    ANALYTIC_ORIGIN,
    ANALYTIC_FRAME,
    CAMERA_SOURCE,
    LIDAR_SOURCE,
    SyntheticPoseFactor,
)

SCHEMA = "TRUST_ROBOT_S6_JOINT_SYNTHETIC_FUSION_V1"
WINDOW = 3

# Explicit manufactured assumptions, not calibrated noise.
CAMERA_STD = (0.04, 0.04, 0.04, 0.03, 0.03, 0.03)
LIDAR_STD = (0.02, 0.02, 0.02, 0.015, 0.015, 0.015)


def need(ok, message):
    if not ok:
        raise ValueError("S6_JOINT_FAIL:" + message)


def sha(path):
    return hashlib.sha256(
        open(path, "rb").read()
    ).hexdigest()


def canonical(obj):
    return (
        json.dumps(
            obj,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ) + "\n"
    ).encode()


def diag_cov(std):
    return np.diag(np.square(std))


@dataclass(frozen=True)
class JointFactor:
    packet: SyntheticPoseFactor
    covariance: tuple

    def __post_init__(self):
        p = self.packet

        need(
            type(p) is SyntheticPoseFactor
            and p.origin == ANALYTIC_ORIGIN
            and p.frame_id == ANALYTIC_FRAME
            and p.modality in ("camera", "lidar")
            and p.source_id == {
                "camera": CAMERA_SOURCE,
                "lidar": LIDAR_SOURCE,
            }[p.modality]
            and type(p.measurement_id) is str
            and bool(p.measurement_id)
            and type(p.measurement) is PoseSE3,
            "UNTRUSTED_OR_INVALID_FACTOR",
        )

        i, j = p.edge

        need(
            type(i) is int
            and type(j) is int
            and 0 <= i < j < len(NODE_FRAMES)
            and j - i <= 2,
            "INVALID_LOCAL_EDGE",
        )

        try:
            c = np.asarray(
                self.covariance,
                dtype=np.float64,
            )
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "S6_JOINT_FAIL:INVALID_COVARIANCE"
            ) from exc

        need(
            c.shape == (6, 6)
            and np.isfinite(c).all()
            and np.allclose(
                c, c.T,
                atol=1e-12,
                rtol=1e-12,
            ),
            "INVALID_COVARIANCE_MATRIX",
        )

        # Reject indefiniteness, singularity and extreme
        # conditioning, without silently adding information.
        eigen = np.linalg.eigvalsh(c)

        need(
            eigen[0] > 0
            and eigen[-1] / eigen[0] < 1e12,
            "UNUSABLE_COVARIANCE",
        )

        object.__setattr__(
            self,
            "covariance",
            tuple(
                tuple(float(x) for x in row)
                for row in c
            ),
        )

    @property
    def key(self):
        return self.packet.measurement_id


def validate_factors(factors):
    need(
        type(factors) is tuple,
        "FACTOR_SEQUENCE_MUST_BE_TUPLE",
    )

    ids = set()
    owner_edges = set()

    for factor in factors:
        need(
            type(factor) is JointFactor,
            "NON_SYNTHETIC_FACTOR",
        )

        p = factor.packet
        owner = (p.modality, p.edge)

        need(
            factor.key not in ids,
            "REUSED_MEASUREMENT_ID",
        )

        need(
            owner not in owner_edges,
            "DUPLICATE_MODALITY_EDGE",
        )

        ids.add(factor.key)
        owner_edges.add(owner)

    return True


def assemble_joint(lidar, camera_packets):
    """Retain both modalities rather than substitute a pose."""

    need(
        isinstance(lidar, dict)
        and type(camera_packets) in (list, tuple),
        "INVALID_FACTOR_COLLECTION",
    )

    factors = []

    for edge, measurement in sorted(lidar.items()):
        need(
            type(edge) is tuple
            and len(edge) == 2
            and type(measurement) is PoseSE3,
            "INVALID_SYNTHETIC_LIDAR",
        )

        packet = SyntheticPoseFactor(
            modality="lidar",
            edge=edge,
            measurement_id=(
                f"analytic_lidar_edge:{edge[0]}:{edge[1]}"
            ),
            source_id=LIDAR_SOURCE,
            frame_id=ANALYTIC_FRAME,
            measurement=measurement,
        )

        factors.append(
            JointFactor(
                packet,
                diag_cov(LIDAR_STD),
            )
        )

    for packet in camera_packets:
        need(
            type(packet) is SyntheticPoseFactor
            and packet.modality == "camera"
            and packet.source_id == CAMERA_SOURCE
            and packet.origin == ANALYTIC_ORIGIN,
            "INVALID_CAMERA_ORIGIN",
        )

        factors.append(
            JointFactor(
                packet,
                diag_cov(CAMERA_STD),
            )
        )

    factors = tuple(
        sorted(
            factors,
            key=lambda f: (
                f.packet.edge,
                f.packet.modality,
                f.key,
            ),
        )
    )

    validate_factors(factors)
    return factors


def whitened_pose_residual(xi, xj, factor):
    """Left-whitened 6D relative-pose residual."""

    need(
        type(factor) is JointFactor,
        "UNAUTHORIZED_POSE_FACTOR",
    )

    predicted = (
        as_pose(xi)
        .inverse()
        .compose(as_pose(xj))
    )

    error = (
        factor.packet.measurement
        .inverse()
        .compose(predicted)
    )

    q = error.quaternion_wxyz

    rotation = Rotation.from_quat(
        [q[1], q[2], q[3], q[0]]
    ).as_rotvec()

    raw = np.r_[
        np.asarray(
            error.translation_m,
            dtype=float,
        ),
        rotation,
    ]

    lower = np.linalg.cholesky(
        np.asarray(factor.covariance)
    )

    whitened = solve_triangular(
        lower,
        raw,
        lower=True,
        check_finite=False,
    )

    need(
        whitened.shape == (6,)
        and np.isfinite(whitened).all(),
        "INVALID_POSE_RESIDUAL",
    )

    return whitened


def selected_residuals(states, prior, inertial, pose):
    need(
        set(prior.node_ids).issubset(states),
        "PRIOR_NODE_MISSING",
    )

    pieces = [prior.residual(states)]

    for (i, j), factor in sorted(inertial.items()):
        pieces.append(
            whitened_inertial_residual(
                states[i],
                states[j],
                factor,
            )
        )

    for key, factor in sorted(pose.items()):
        i, j = factor.packet.edge

        pieces.append(
            whitened_pose_residual(
                states[i],
                states[j],
                factor,
            )
        )

    return np.concatenate(pieces)


def active_pose(all_pose, live, consumed):
    live = set(live)

    return {
        f.key: f
        for f in all_pose
        if f.key not in consumed
        and set(f.packet.edge).issubset(live)
    }


def active_imu(all_imu, live, consumed):
    live = set(live)

    return {
        key: value
        for key, value in all_imu.items()
        if key not in consumed
        and set(key).issubset(live)
    }


def estimate_joint(fixture, camera_packets=()):
    """Run the nonlinear 15D Schur solver without any truth input."""

    need(
        type(camera_packets) in (tuple, list),
        "INVALID_CAMERA_PACKETS",
    )

    inertial, lidar, source_counts = make_factors(
        fixture
    )

    pose_factors = assemble_joint(
        lidar,
        camera_packets,
    )

    states = {0: initial_state()}

    prior = synthetic_initial_anchor(
        states[0],
        sigma=0.01,
    )

    live = [0]
    consumed_imu = set()
    consumed_pose = set()

    windows = []
    elimination_count = 0

    for end in range(1, len(NODE_FRAMES)):
        predicted = states[end - 1].copy()

        for sample in range(
            NODE_FRAMES[end - 1],
            NODE_FRAMES[end],
        ):
            predicted = predict_imu(
                predicted,
                fixture["imu"][sample],
            )

        states[end] = predicted
        live.append(end)

        need(
            len(live) <= WINDOW,
            "WINDOW_OVERFLOW",
        )

        ai = active_imu(
            inertial,
            live,
            consumed_imu,
        )

        ap = active_pose(
            pose_factors,
            live,
            consumed_pose,
        )

        need(
            len(ai) == len(live) - 1,
            "INERTIAL_CHAIN_MISSING",
        )

        n = STATE_DIM * len(live)

        x0 = np.concatenate([
            states[k] for k in live
        ])

        def make_states(x):
            need(
                np.shape(x) == (n,),
                "OPTIMIZER_DIMENSION",
            )

            return {
                node: x[
                    index * STATE_DIM:
                    (index + 1) * STATE_DIM
                ]
                for index, node in enumerate(live)
            }

        def objective(x):
            return selected_residuals(
                make_states(x),
                prior,
                ai,
                ap,
            )

        fit = least_squares(
            objective,
            x0,
            method="trf",
            loss="linear",
            max_nfev=80,
            ftol=1e-9,
            xtol=1e-9,
            gtol=1e-9,
        )

        rank = int(
            np.linalg.matrix_rank(
                fit.jac,
                tol=1e-7,
            )
        )

        need(
            fit.success
            and np.isfinite(fit.x).all()
            and math.isfinite(float(fit.cost))
            and rank == n,
            "NONLINEAR_WINDOW_NOT_SUPPORTED",
        )

        for index, node in enumerate(live):
            states[node] = fit.x[
                index * STATE_DIM:
                (index + 1) * STATE_DIM
            ].copy()

        windows.append({
            "end_node": end,
            "accepted": True,
            "rank": rank,
            "state_dimension": n,
            "camera_factor_count": sum(
                f.packet.modality == "camera"
                for f in ap.values()
            ),
            "lidar_factor_count": sum(
                f.packet.modality == "lidar"
                for f in ap.values()
            ),
            "joint_factor_ids": sorted(ap),
            "inertial_factor_count": len(ai),
        })

        if len(live) == WINDOW:
            oldest = live[0]

            ii = {
                k: v for k, v in ai.items()
                if oldest in k
            }

            pp = {
                k: f for k, f in ap.items()
                if oldest in f.packet.edge
            }

            need(
                len(ii) >= 1,
                "DEPARTING_STATE_NO_IMU",
            )

            for key in inertial:
                need(
                    not (
                        oldest in key
                        and max(key) > end
                    ),
                    "PREMATURE_IMU_ELIMINATION",
                )

            for f in pose_factors:
                need(
                    not (
                        oldest in f.packet.edge
                        and max(f.packet.edge) > end
                    ),
                    "PREMATURE_POSE_ELIMINATION",
                )

            previous = prior

            def eliminate(candidate):
                return selected_residuals(
                    candidate,
                    previous,
                    ii,
                    pp,
                )

            prior, _ = marginalize_one(
                tuple(live),
                {
                    node: states[node].copy()
                    for node in live
                },
                eliminate,
                oldest,
            )

            need(
                not (set(ii) & consumed_imu)
                and not (set(pp) & consumed_pose),
                "FACTOR_REUSED_IN_SCHUR",
            )

            consumed_imu.update(ii)
            consumed_pose.update(pp)

            live.pop(0)
            elimination_count += 1

            need(
                set(prior.node_ids) == set(live),
                "PRIOR_OWNERSHIP",
            )

    remaining_imu = active_imu(
        inertial,
        live,
        consumed_imu,
    )

    remaining_pose = active_pose(
        pose_factors,
        live,
        consumed_pose,
    )

    all_pose_ids = {
        f.key for f in pose_factors
    }

    need(
        consumed_pose.isdisjoint(remaining_pose)
        and consumed_imu.isdisjoint(remaining_imu)
        and consumed_pose | set(remaining_pose)
        == all_pose_ids
        and consumed_imu | set(remaining_imu)
        == set(inertial),
        "FACTOR_OWNERSHIP_UNACCOUNTED",
    )

    need(
        len(windows) == 4
        and elimination_count == 3
        and live == [3, 4],
        "FIXED_LAG_CHRONOLOGY",
    )

    overlap_edges = sorted(
        set(f.packet.edge for f in pose_factors
            if f.packet.modality == "camera")
        &
        set(f.packet.edge for f in pose_factors
            if f.packet.modality == "lidar")
    )

    records = [
        {
            "node": k,
            "position_m":
                states[k][:3].tolist(),
            "rotation_vector_rad":
                states[k][3:6].tolist(),
            "velocity_m_s":
                states[k][6:9].tolist(),
            "gyro_bias":
                states[k][9:12].tolist(),
            "accel_bias":
                states[k][12:15].tolist(),
        }
        for k in range(len(NODE_FRAMES))
    ]

    return records, {
        "source_counts": source_counts,
        "windows": windows,
        "accepted_window_count": len(windows),
        "schur_elimination_count": elimination_count,
        "total_pose_factor_count":
            len(pose_factors),
        "camera_factor_count": sum(
            f.packet.modality == "camera"
            for f in pose_factors
        ),
        "lidar_factor_count": sum(
            f.packet.modality == "lidar"
            for f in pose_factors
        ),
        "same_edge_camera_lidar_count":
            len(overlap_edges),
        "same_edge_camera_lidar_edges": [
            list(edge) for edge in overlap_edges
        ],
        "factor_ledger": [
            {
                "measurement_id": f.key,
                "modality": f.packet.modality,
                "edge": list(f.packet.edge),
                "source_id": f.packet.source_id,
                "origin": f.packet.origin,
                "covariance_diagonal": list(
                    np.diag(
                        np.asarray(f.covariance)
                    )
                ),
            }
            for f in pose_factors
        ],
        "consumed_pose_ids": sorted(
            consumed_pose
        ),
        "remaining_pose_ids": sorted(
            remaining_pose
        ),
        "unaccounted_factor_count": 0,
        "factor_reuse_after_marginalization": False,
        "physical_measurements_used": False,
        "real_sensor_factor_admitted": False,
    }


def junit(path):
    cases = list(
        ET.parse(path).getroot().iter(
            "testcase"
        )
    )

    need(len(cases) >= 12, "TOO_FEW_TESTS")

    need(
        all(
            not any(
                child.tag in (
                    "failure", "error", "skipped"
                )
                for child in case
            )
            for case in cases
        ),
        "TESTS_NOT_ALL_PASSED",
    )

    return len(cases)


def execute(test_xml, s5_matrix):
    s5 = json.loads(
        open(s5_matrix, encoding="utf-8").read()
    )

    need(
        s5["next_implementation"]["work_id"]
        == "S6_CPU_ONLY_INDEPENDENT_CAMERA_LIDAR_SAME_EDGE_FUSION"
        and s5["next_implementation"]["real_sensor_admission"]
        is False,
        "S5_SCIENTIFIC_LINEAGE",
    )

    scenarios = []

    for condition in (
        "clean",
        "lidar_dropout",
    ):
        fixture, manufactured_truth = make_fixture(
            condition
        )

        for camera_enabled in (False, True):
            camera = (
                manufactured_camera_packets(
                    manufactured_truth,
                    seed=13,
                )
                if camera_enabled else ()
            )

            records, audit = estimate_joint(
                fixture,
                camera,
            )

            need(
                len(records) == 5
                and audit["accepted_window_count"] == 4
                and audit["schur_elimination_count"] == 3
                and audit["camera_factor_count"]
                == (2 if camera_enabled else 0)
                and audit["unaccounted_factor_count"] == 0
                and audit["factor_reuse_after_marginalization"]
                is False,
                "SCENARIO_RESULT",
            )

            scenarios.append({
                "condition": condition,
                "camera_enabled": camera_enabled,
                "estimated_states_sha256": hashlib.sha256(
                    canonical(records)
                ).hexdigest(),
                "factor_audit": audit,
                "reference_passed_to_solver": False,
                "camera_measurements_manufactured_from_truth":
                    camera_enabled,
                "scientific_pose_accuracy_claim": False,
            })

    report = {
        "schema": SCHEMA,
        "status":
            "DEVELOPMENT_ONLY_SYNTHETIC_JOINT_FUSION",
        "parent_commit":
            "ebe97e3ee3d3c9872b2b5643de5124bb0cfacf43",
        "source_sha256": sha(__file__),
        "junit_sha256": sha(test_xml),
        "s5_matrix_sha256": sha(s5_matrix),
        "test_cases_passed": junit(test_xml),
        "scenarios": scenarios,
        "scenario_count": len(scenarios),
        "separate_camera_and_lidar_factor_ownership": True,
        "same_edge_factors_individually_retained": True,
        "distinct_assumed_covariances": True,
        "assumed_cross_modal_noise_independence_verified":
            False,
        "camera_motion_from_real_images": False,
        "physical_sensor_time_verified": False,
        "real_sensor_extrinsics_verified": False,
        "empirical_noise_covariance_calibrated": False,
        "real_sensor_factor_execution_authorized": False,
        "independent_real_6dof_truth_scored": False,
        "health_model_trained": False,
        "raw_sensor_recordings_read": False,
        "new_sensor_acquisitions": 0,
        "scientific_pose_factors": 0,
        "health_labels": 0,
        "git_commit_or_push": False,
    }

    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--test-xml", required=True)
    p.add_argument("--s5-matrix", required=True)
    p.add_argument("--report", required=True)
    args = p.parse_args()

    report = execute(
        args.test_xml,
        args.s5_matrix,
    )

    with open(
        args.report,
        "x",
        encoding="utf-8",
    ) as f:
        json.dump(
            report,
            f,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        f.write("\n")

    print("S6_JOINT_NONLINEAR_SOLVER_SCENARIOS=4_PASSED")
    print("S6_SCHUR_WINDOW_SOLVES=16_ACCEPTED")
    print("S6_SAME_EDGE_CAMERA_LIDAR=INDEPENDENT_SLOTS")
    print("S6_MODALITY_COVARIANCES=SEPARATE_ASSUMED")
    print("S6_FACTOR_REUSE_AFTER_MARGINALIZATION=NONE")
    print("S6_SYNTHETIC_JOINT_FUSION=PASS")


if __name__ == "__main__":
    main()
