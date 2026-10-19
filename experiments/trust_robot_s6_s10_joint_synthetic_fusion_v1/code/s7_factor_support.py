"""S7 numerical support and perturbation of manufactured factors.

All results are local synthetic-development diagnostics.
No physical sensor timing, noise independence, or pose accuracy
is qualified by this work.
"""

import argparse
import dataclasses
import hashlib
import json
import math
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np

from trust_robot.clean_backbone import PoseSE3
from trust_robot.analytic_inertial_15d import (
    initial_state,
    make_fixture,
    predict_imu,
)
from trust_robot.analytic_preintegrated_fusion import make_factors
from trust_robot.analytic_three_modality_bridge import (
    manufactured_camera_packets,
)

from s6_joint_fusion import (
    JointFactor,
    assemble_joint,
    canonical,
    estimate_joint,
    whitened_pose_residual,
)

SCHEMA = "TRUST_ROBOT_S7_SYNTHETIC_FACTOR_SUPPORT_V1"

EPS = 1e-6
PERTURBATION_M = 0.08
COVARIANCE_INFLATION = 25.0


def need(ok, reason):
    if not ok:
        raise ValueError("S7_INVALID:" + reason)


def sha(path):
    return hashlib.sha256(
        Path(path).read_bytes()
    ).hexdigest()


def load(path):
    return json.loads(
        Path(path).read_text(encoding="utf-8")
    )


def write(path, data):
    with Path(path).open(
        "x",
        encoding="utf-8",
    ) as f:
        json.dump(
            data,
            f,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        f.write("\n")


def perturb_camera(packet, displacement=PERTURBATION_M):
    """Replace one manufactured camera measurement, never its origin."""

    need(
        packet.modality == "camera"
        and packet.origin == "ANALYTIC_FIXTURE"
        and math.isfinite(displacement)
        and 0 < displacement <= 0.2,
        "INVALID_MANUFACTURED_PERTURBATION",
    )

    original = packet.measurement

    new_position = np.asarray(
        original.translation_m,
        dtype=np.float64,
    ).copy()

    new_position[0] += displacement

    modified = PoseSE3(
        translation_m=tuple(
            float(v) for v in new_position
        ),
        quaternion_wxyz=original.quaternion_wxyz,
    )

    return dataclasses.replace(
        packet,
        measurement=modified,
    )


def camera_lidar_pair():
    """Return manufactured factors sharing the edge (0,1)."""

    fixture, truth = make_fixture("clean")

    inertial, lidar, counts = make_factors(fixture)

    packets = manufactured_camera_packets(
        truth,
        seed=13,
    )

    factors = assemble_joint(lidar, packets)

    pair = {
        factor.packet.modality: factor
        for factor in factors
        if factor.packet.edge == (0, 1)
    }

    need(
        set(pair) == {"camera", "lidar"}
        and pair["camera"].key != pair["lidar"].key
        and len(factors) == 9
        and len(inertial) == 4,
        "SHARED_EDGE_FACTOR_OWNERSHIP",
    )

    return fixture, packets, pair, counts


def comparison_states(fixture):
    """Initial synthetic inertial propagation, no truth input."""

    xi = initial_state()

    xj = xi.copy()

    for sample in fixture["imu"][:2]:
        xj = predict_imu(
            xj,
            sample,
        )

    need(
        np.shape(xi) == (15,)
        and np.shape(xj) == (15,)
        and np.isfinite(xi).all()
        and np.isfinite(xj).all(),
        "COMPARISON_STATES",
    )

    return xi, xj


def jacobian_on_edge(xi, xj, factor):
    """Central finite-difference 6D camera/LiDAR residual Jacobian.

    Only the second synthetic state's pose coordinates are varied.
    The initial state and synthetic inertial propagation are fixed.
    """

    jac = np.empty((6, 6), dtype=np.float64)

    for k in range(6):
        forward = xj.copy()
        backward = xj.copy()

        forward[k] += EPS
        backward[k] -= EPS

        rf = whitened_pose_residual(
            xi,
            forward,
            factor,
        )

        rb = whitened_pose_residual(
            xi,
            backward,
            factor,
        )

        jac[:, k] = (
            rf - rb
        ) / (2.0 * EPS)

    need(
        np.isfinite(jac).all()
        and np.linalg.matrix_rank(jac) == 6,
        "POSE_JACOBIAN_UNSUPPORTED",
    )

    return jac


def information_experiment():
    fixture, packets, pair, _ = camera_lidar_pair()

    xi, xj = comparison_states(fixture)

    jc = jacobian_on_edge(
        xi,
        xj,
        pair["camera"],
    )

    jl = jacobian_on_edge(
        xi,
        xj,
        pair["lidar"],
    )

    ic = jc.T @ jc
    il = jl.T @ jl

    joint = ic + il

    need(
        np.linalg.eigvalsh(ic)[0] > 0
        and np.linalg.eigvalsh(il)[0] > 0
        and np.linalg.eigvalsh(joint)[0] > 0,
        "INSUFFICIENT_LOCAL_NUMERICAL_INFORMATION",
    )

    need(
        np.allclose(
            joint - il,
            ic,
            atol=1e-8,
            rtol=1e-10,
        ),
        "CAMERA_INFORMATION_NOT_ADDITIVE",
    )

    need(
        np.allclose(
            joint - ic,
            il,
            atol=1e-8,
            rtol=1e-10,
        ),
        "LIDAR_INFORMATION_NOT_ADDITIVE",
    )

    camera = pair["camera"]

    relaxed = JointFactor(
        camera.packet,
        np.asarray(camera.covariance)
        * COVARIANCE_INFLATION,
    )

    r0 = whitened_pose_residual(
        xi,
        xj,
        camera,
    )

    rw = whitened_pose_residual(
        xi,
        xj,
        relaxed,
    )

    need(
        np.allclose(
            rw,
            r0 / math.sqrt(
                COVARIANCE_INFLATION
            ),
            atol=1e-10,
            rtol=1e-10,
        ),
        "COVARIANCE_RESIDUAL_SCALING",
    )

    corrupted_packet = perturb_camera(
        camera.packet
    )

    corrupted = JointFactor(
        corrupted_packet,
        camera.covariance,
    )

    original_norm = float(
        np.linalg.norm(r0)
    )

    corrupted_norm = float(
        np.linalg.norm(
            whitened_pose_residual(
                xi,
                xj,
                corrupted,
            )
        )
    )

    need(
        corrupted_norm > original_norm,
        "CAMERA_PERTURBATION_NOT_VISIBLE",
    )

    return {
        "shared_edge": [0, 1],
        "camera_measurement_id": camera.key,
        "lidar_measurement_id": pair["lidar"].key,
        "camera_information_matrix": ic.tolist(),
        "lidar_information_matrix": il.tolist(),
        "joint_information_matrix": joint.tolist(),
        "camera_information_trace": float(np.trace(ic)),
        "lidar_information_trace": float(np.trace(il)),
        "joint_information_trace": float(np.trace(joint)),
        "camera_min_information_eigenvalue":
            float(np.linalg.eigvalsh(ic)[0]),
        "lidar_min_information_eigenvalue":
            float(np.linalg.eigvalsh(il)[0]),
        "joint_min_information_eigenvalue":
            float(np.linalg.eigvalsh(joint)[0]),
        "camera_jacobian_rank": 6,
        "lidar_jacobian_rank": 6,
        "joint_jacobian_rank": 6,
        "covariance_inflation": COVARIANCE_INFLATION,
        "camera_baseline_whitened_norm": original_norm,
        "camera_inflated_whitened_norm":
            float(np.linalg.norm(rw)),
        "camera_corrupted_whitened_norm": corrupted_norm,
        "camera_translation_perturbation_m": PERTURBATION_M,
        "assumed_residual_independence_for_additive_information":
            True,
        "empirical_cross_modality_noise_independence_verified":
            False,
        "physically_supported_information_matrix":
            False,
    }


def nonlinear_perturbation_experiment():
    fixture, truth = make_fixture("clean")

    camera = manufactured_camera_packets(
        truth,
        seed=13,
    )

    need(
        len(camera) == 2
        and camera[0].edge == (0, 1),
        "EXPECTED_CAMERA_PACKET_SEQUENCE",
    )

    disturbed = (
        perturb_camera(camera[0]),
        camera[1],
    )

    baseline_states, baseline_audit = estimate_joint(
        fixture,
        camera,
    )

    disturbed_states, disturbed_audit = estimate_joint(
        fixture,
        disturbed,
    )

    need(
        len(baseline_states)
        == len(disturbed_states)
        == 5,
        "INCOMPLETE_ESTIMATION",
    )

    for audit in (
        baseline_audit,
        disturbed_audit,
    ):
        need(
            audit["accepted_window_count"] == 4
            and audit["schur_elimination_count"] == 3
            and audit["camera_factor_count"] == 2
            and audit["lidar_factor_count"] == 7
            and audit["same_edge_camera_lidar_count"] == 2
            and audit["unaccounted_factor_count"] == 0
            and audit["factor_reuse_after_marginalization"]
            is False,
            "SCHUR_FACTOR_ACCOUNTING",
        )

    baseline_ids = {
        item["measurement_id"]
        for item in baseline_audit["factor_ledger"]
    }

    disturbed_ids = {
        item["measurement_id"]
        for item in disturbed_audit["factor_ledger"]
    }

    need(
        baseline_ids == disturbed_ids
        and len(baseline_ids) == 9,
        "MEASUREMENT_OWNERSHIP_CHANGED",
    )

    position_deltas = [
        float(np.linalg.norm(
            np.asarray(a["position_m"])
            - np.asarray(b["position_m"])
        ))
        for a, b in zip(
            baseline_states,
            disturbed_states,
        )
    ]

    need(
        np.isfinite(position_deltas).all()
        and max(position_deltas) > 1e-6,
        "ESTIMATOR_INSENSITIVE_TO_CAMERA_PERTURBATION",
    )

    return {
        "baseline_states_sha256":
            hashlib.sha256(
                canonical(baseline_states)
            ).hexdigest(),
        "disturbed_states_sha256":
            hashlib.sha256(
                canonical(disturbed_states)
            ).hexdigest(),
        "synthetic_camera_perturbation_m":
            PERTURBATION_M,
        "max_trajectory_position_change_m":
            max(position_deltas),
        "position_change_per_node_m":
            position_deltas,
        "baseline_pose_factor_count":
            baseline_audit["total_pose_factor_count"],
        "disturbed_pose_factor_count":
            disturbed_audit["total_pose_factor_count"],
        "shared_edges_preserved": True,
        "measurement_id_set_preserved": True,
        "camera_disturbance_detectable": True,
        "state_response_is_physical_accuracy_metric": False,
        "reference_passed_to_estimator": False,
        "factor_reuse_after_marginalization": False,
    }


def test_count(xml):
    cases = list(
        ET.parse(xml).getroot().iter(
            "testcase"
        )
    )

    need(
        len(cases) >= 15
        and len({
            (
                x.get("classname"),
                x.get("name"),
            )
            for x in cases
        }) == len(cases),
        "TEST_COVERAGE",
    )

    need(
        all(
            not any(
                child.tag in (
                    "failure",
                    "error",
                    "skipped",
                )
                for child in case
            )
            for case in cases
        ),
        "TEST_FAILURE_OR_SKIP",
    )

    return len(cases)


def execute(xml, s6_report, s6_validation):
    prior = load(s6_report)
    verified = load(s6_validation)

    need(
        prior["scenario_count"] == 4
        and prior["test_cases_passed"] == 23
        and verified[
            "nonlinear_joint_scenarios_verified"
        ] == 4
        and verified["real_sensor_factor_execution_authorized"]
        is False,
        "S6_EVIDENCE_NOT_VALIDATED",
    )

    info = information_experiment()

    nonlinear = nonlinear_perturbation_experiment()

    return {
        "schema": SCHEMA,
        "parent_commit":
            "ebe97e3ee3d3c9872b2b5643de5124bb0cfacf43",
        "engine_sha256": sha(__file__),
        "s6_report_sha256": sha(s6_report),
        "s6_validation_sha256": sha(s6_validation),
        "junit_sha256": sha(xml),
        "unit_tests_passed": test_count(xml),
        "information_experiment": info,
        "nonlinear_perturbation": nonlinear,
        "physical_capture_time_verified": False,
        "cross_modal_sensor_noise_independence_verified":
            False,
        "camera_motion_measured_from_images": False,
        "empirical_covariance_calibration": False,
        "independent_real_6dof_reference_scored": False,
        "real_sensor_factor_admission": False,
        "m2dgr_estimator_scoring_authorized": False,
        "health_model_training_authorized": False,
        "live_simulator_launch_authorized": False,
        "raw_sensor_records_read": False,
        "new_sensor_acquisitions": 0,
        "scientific_pose_factors": 0,
        "health_labels": 0,
        "github_commit_or_push": False,
        "next":
            "S8_SYNTHETIC_CORRELATED_NOISE_AND_CONFLICT_HANDLING",
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser()

    for name in (
        "xml",
        "s6_report",
        "s6_validation",
        "report",
    ):
        p.add_argument(
            "--" + name.replace("_", "-"),
            dest=name,
            required=True,
        )

    a = p.parse_args()

    result = execute(
        a.xml,
        a.s6_report,
        a.s6_validation,
    )

    write(
        a.report,
        result,
    )

    print(
        f"S7_UNIT_TESTS="
        f"{result['unit_tests_passed']}_PASSED"
    )
    print("S7_CAMERA_LIDAR_SHARED_EDGE=VERIFIED")
    print("S7_SEPARATE_INFORMATION_MATRICES=VERIFIED")
    print("S7_ASSUMED_COVARIANCE_SCALING=VERIFIED")
    print("S7_CAMERA_PERTURBATION=DETECTED")
    print("S7_NONLINEAR_SOLVER_RESPONSE=VERIFIED")
    print("S7_SCHUR_FACTOR_OWNERSHIP=PRESERVED")
    print("S7_NUMERICAL_SUPPORT_AND_PERTURBATION=PASS")
