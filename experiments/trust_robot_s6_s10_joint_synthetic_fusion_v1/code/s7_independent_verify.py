"""Independent S7 matrix, perturbation and JUnit verification."""

import argparse
import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np

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
    assemble_joint,
    whitened_pose_residual,
)


def need(ok, reason):
    if not ok:
        raise AssertionError(
            "S7_INDEPENDENT_FAIL:" + reason
        )


def sha(path):
    return hashlib.sha256(
        Path(path).read_bytes()
    ).hexdigest()


def load(path):
    return json.loads(
        Path(path).read_text()
    )


def main(a):
    report = load(a.report)
    s6 = load(a.s6_report)
    s6_validation = load(a.s6_validation)

    need(
        report["schema"]
        == "TRUST_ROBOT_S7_SYNTHETIC_FACTOR_SUPPORT_V1",
        "SCHEMA",
    )

    for key, path in (
        ("engine_sha256", a.engine),
        ("s6_report_sha256", a.s6_report),
        ("s6_validation_sha256", a.s6_validation),
        ("junit_sha256", a.xml),
    ):
        need(
            report[key] == sha(path),
            "SOURCE_HASH:" + key,
        )

    need(
        s6["test_cases_passed"] == 23
        and s6["scenario_count"] == 4
        and s6_validation[
            "nonlinear_joint_scenarios_verified"
        ] == 4,
        "S6_FROZEN_LINEAGE",
    )

    cases = list(
        ET.parse(a.xml).getroot().iter(
            "testcase"
        )
    )

    need(
        len(cases) >= 15
        and len(cases) == report["unit_tests_passed"]
        and all(
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
        "UNIT_TEST_EVIDENCE",
    )

    info = report["information_experiment"]

    cam = np.asarray(
        info["camera_information_matrix"],
        dtype=float,
    )

    lidar = np.asarray(
        info["lidar_information_matrix"],
        dtype=float,
    )

    joint = np.asarray(
        info["joint_information_matrix"],
        dtype=float,
    )

    need(
        all(
            mat.shape == (6, 6)
            and np.isfinite(mat).all()
            and np.allclose(mat, mat.T)
            and np.linalg.eigvalsh(mat)[0] > 0
            for mat in (cam, lidar, joint)
        ),
        "INFORMATION_MATRIX_SUPPORT",
    )

    need(
        np.allclose(
            joint,
            cam + lidar,
            atol=1e-8,
            rtol=1e-10,
        ),
        "JOINT_INFORMATION_NOT_ADDITIVE",
    )

    for name, mat in (
        ("camera", cam),
        ("lidar", lidar),
        ("joint", joint),
    ):
        need(
            np.isclose(
                info[name + "_information_trace"],
                np.trace(mat),
            ),
            "INFORMATION_TRACE",
        )

        need(
            np.isclose(
                info[name + "_min_information_eigenvalue"],
                np.linalg.eigvalsh(mat)[0],
            ),
            "INFORMATION_EIGENVALUE",
        )

        need(
            info[name + "_jacobian_rank"] == 6,
            "INFORMATION_RANK",
        )

    need(
        info["shared_edge"] == [0, 1]
        and info["camera_measurement_id"]
        != info["lidar_measurement_id"]
        and info["covariance_inflation"] == 25.0
        and np.isclose(
            info["camera_inflated_whitened_norm"],
            info["camera_baseline_whitened_norm"] / 5,
            atol=1e-10,
            rtol=1e-9,
        ),
        "OWNERSHIP_OR_SCALING",
    )

    need(
        info["camera_corrupted_whitened_norm"]
        > info["camera_baseline_whitened_norm"]
        and info[
            "empirical_cross_modality_noise_independence_verified"
        ] is False
        and info[
            "physically_supported_information_matrix"
        ] is False,
        "PERTURBATION_OR_SCIENCE_GATE",
    )

    # Independent local numerical recomputation from the
    # pinned S6 implementation, not from the S7 engine.
    fixture, truth = make_fixture("clean")
    _, lidar_raw, _ = make_factors(fixture)

    camera_packets = manufactured_camera_packets(
        truth,
        seed=13,
    )

    factors = assemble_joint(
        lidar_raw,
        camera_packets,
    )

    selected = {
        f.packet.modality: f
        for f in factors
        if f.packet.edge == (0, 1)
    }

    need(
        set(selected) == {"camera", "lidar"},
        "MISSING_SOURCE",
    )

    xi = initial_state()
    xj = xi.copy()

    for sample in fixture["imu"][:2]:
        xj = predict_imu(xj, sample)

    recalculated = {}

    for modality in ("camera", "lidar"):
        j = np.empty((6, 6))
        factor = selected[modality]

        for k in range(6):
            xp = xj.copy()
            xm = xj.copy()

            xp[k] += 1e-6
            xm[k] -= 1e-6

            j[:, k] = (
                whitened_pose_residual(
                    xi, xp, factor
                )
                - whitened_pose_residual(
                    xi, xm, factor
                )
            ) / (2e-6)

        recalculated[modality] = j.T @ j

    need(
        np.allclose(
            recalculated["camera"],
            cam,
            atol=1e-7,
            rtol=1e-8,
        )
        and np.allclose(
            recalculated["lidar"],
            lidar,
            atol=1e-7,
            rtol=1e-8,
        ),
        "INDEPENDENT_JACOBIAN_RECALCULATION",
    )

    nonlinear = report["nonlinear_perturbation"]

    need(
        nonlinear["baseline_pose_factor_count"] == 9
        and nonlinear["disturbed_pose_factor_count"] == 9
        and nonlinear["shared_edges_preserved"] is True
        and nonlinear["measurement_id_set_preserved"] is True
        and nonlinear[
            "factor_reuse_after_marginalization"
        ] is False
        and nonlinear["reference_passed_to_estimator"]
        is False
        and nonlinear[
            "state_response_is_physical_accuracy_metric"
        ] is False,
        "NONLINEAR_FACTOR_AUDIT",
    )

    deltas = nonlinear[
        "position_change_per_node_m"
    ]

    need(
        len(deltas) == 5
        and all(
            np.isfinite(x) and x >= 0
            for x in deltas
        )
        and max(deltas) > 1e-6
        and np.isclose(
            max(deltas),
            nonlinear["max_trajectory_position_change_m"],
        )
        and nonlinear["baseline_states_sha256"]
        != nonlinear["disturbed_states_sha256"],
        "NONLINEAR_PERTURBATION_RESPONSE",
    )

    for key in (
        "physical_capture_time_verified",
        "cross_modal_sensor_noise_independence_verified",
        "camera_motion_measured_from_images",
        "empirical_covariance_calibration",
        "independent_real_6dof_reference_scored",
        "real_sensor_factor_admission",
        "m2dgr_estimator_scoring_authorized",
        "health_model_training_authorized",
        "live_simulator_launch_authorized",
        "raw_sensor_records_read",
        "github_commit_or_push",
    ):
        need(
            report[key] is False,
            "UNSUPPORTED_CLAIM:" + key,
        )

    for key in (
        "new_sensor_acquisitions",
        "scientific_pose_factors",
        "health_labels",
    ):
        need(
            type(report[key]) is int
            and report[key] == 0,
            "NONZERO_SCIENTIFIC_COUNT",
        )

    result = {
        "schema":
            "TRUST_ROBOT_S7_INDEPENDENT_VALIDATION_V1",
        "engine_sha256": sha(a.engine),
        "test_sha256": sha(a.test),
        "verifier_sha256": sha(__file__),
        "junit_sha256": sha(a.xml),
        "report_sha256": sha(a.report),
        "unit_tests_verified": len(cases),
        "separate_modality_information_verified": True,
        "independent_s6_jacobian_recomputation": True,
        "assumed_covariance_scaling_verified": True,
        "nonlinear_camera_perturbation_detected": True,
        "schur_factor_ownership_preserved": True,
        "physical_noise_independence_verified": False,
        "real_sensor_factor_admission": False,
        "new_sensor_acquisitions": 0,
        "scientific_pose_factors": 0,
        "health_labels": 0,
    }

    with Path(a.validation).open(
        "x",
        encoding="utf-8",
    ) as f:
        json.dump(
            result,
            f,
            indent=2,
            sort_keys=True,
        )
        f.write("\n")

    print(
        f"S7_INDEPENDENT_TESTS="
        f"{len(cases)}_VERIFIED"
    )
    print("S7_INDEPENDENT_INFORMATION_MATRICES=VERIFIED")
    print("S7_INDEPENDENT_JACOBIAN_RECOMPUTATION=PASS")
    print("S7_INDEPENDENT_PERTURBATION=VERIFIED")
    print("S7_INDEPENDENT_VALIDATION=PASS")


if __name__ == "__main__":
    p = argparse.ArgumentParser()

    for name in (
        "engine",
        "test",
        "xml",
        "s6_report",
        "s6_validation",
        "report",
        "validation",
    ):
        p.add_argument(
            "--" + name.replace("_", "-"),
            dest=name,
            required=True,
        )

    main(p.parse_args())
