"""S8 manufactured cross-modal covariance and conflict study.

The 12D paired covariance is a synthetic assumption, not
calibrated camera/LiDAR measurement noise.

Local six-dimensional relative-pose tangent approximations
are used for the information and disagreement diagnostics.

Disagreement never authorizes automatic rejection, weighting,
health classification, physical factor admission or safety action.
"""

import argparse
import hashlib
import json
import math
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
from scipy.stats import chi2
from scipy.spatial.transform import Rotation

from trust_robot.analytic_inertial_15d import make_fixture
from trust_robot.analytic_three_modality_bridge import (
    manufactured_camera_packets,
)

from s6_joint_fusion import (
    JointFactor,
    estimate_joint,
)

from s7_factor_support import (
    camera_lidar_pair,
    comparison_states,
    jacobian_on_edge,
    perturb_camera,
)

SCHEMA = "TRUST_ROBOT_S8_SYNTHETIC_CORRELATED_CONFLICT_V1"

RHOS = (0.0, 0.35, -0.25)
DISPLACEMENT_M = 0.2
THRESHOLD_QUANTILE = 0.95
DEGREES_OF_FREEDOM = 6


def need(ok, reason):
    if not ok:
        raise ValueError("S8_FAIL_CLOSED:" + reason)


def sha(path):
    return hashlib.sha256(
        Path(path).read_bytes()
    ).hexdigest()


def load(path):
    return json.loads(
        Path(path).read_text()
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


def paired_covariance(camera, lidar, rho):
    """Manufacture a symmetric positive-definite 12D covariance."""

    need(
        type(camera) is JointFactor
        and type(lidar) is JointFactor
        and camera.packet.modality == "camera"
        and lidar.packet.modality == "lidar"
        and camera.packet.edge == lidar.packet.edge
        and camera.key != lidar.key,
        "INVALID_SHARED_EDGE",
    )

    need(
        type(rho) in (int, float)
        and math.isfinite(rho)
        and abs(rho) <= 0.75,
        "INVALID_ASSUMED_CORRELATION",
    )

    cc = np.asarray(
        camera.covariance,
        dtype=np.float64,
    )
    ll = np.asarray(
        lidar.covariance,
        dtype=np.float64,
    )

    lc = np.linalg.cholesky(cc)
    llower = np.linalg.cholesky(ll)

    cross = float(rho) * lc @ llower.T

    paired = np.block([
        [cc, cross],
        [cross.T, ll],
    ])

    need(
        paired.shape == (12, 12)
        and np.isfinite(paired).all()
        and np.allclose(
            paired,
            paired.T,
            atol=1e-12,
        )
        and np.linalg.eigvalsh(paired)[0] > 0,
        "PAIRED_COVARIANCE_NOT_SPD",
    )

    return paired, cross


def relative_disagreement(camera, lidar):
    """Compare manufactured poses in a shared local tangent convention."""

    need(
        camera.packet.edge == lidar.packet.edge,
        "DISAGREEMENT_EDGE_MISMATCH",
    )

    relative = (
        lidar.packet.measurement
        .inverse()
        .compose(camera.packet.measurement)
    )

    q = relative.quaternion_wxyz

    rv = Rotation.from_quat(
        [q[1], q[2], q[3], q[0]]
    ).as_rotvec()

    delta = np.r_[
        np.asarray(
            relative.translation_m,
            dtype=np.float64,
        ),
        rv,
    ]

    need(
        delta.shape == (6,)
        and np.isfinite(delta).all(),
        "INVALID_DISAGREEMENT",
    )

    return delta


def disagreement_diagnostic(camera, lidar, rho):
    """Informational diagnostic; no physical false-alarm calibration."""

    paired, cross = paired_covariance(
        camera,
        lidar,
        rho,
    )

    cc = paired[:6, :6]
    ll = paired[6:, 6:]

    # Local-tangent covariance approximation for
    # the difference between two relative-pose measurements.
    difference_covariance = (
        cc + ll - cross - cross.T
    )

    need(
        np.linalg.eigvalsh(
            difference_covariance
        )[0] > 0,
        "DISAGREEMENT_COVARIANCE_NOT_SPD",
    )

    delta = relative_disagreement(
        camera,
        lidar,
    )

    statistic = float(
        delta @ np.linalg.solve(
            difference_covariance,
            delta,
        )
    )

    threshold = float(
        chi2.ppf(
            THRESHOLD_QUANTILE,
            DEGREES_OF_FREEDOM,
        )
    )

    need(
        math.isfinite(statistic)
        and statistic >= 0
        and math.isfinite(threshold),
        "INVALID_DIAGNOSTIC",
    )

    flagged = bool(
        statistic > threshold
    )

    return {
        "assumed_correlation": float(rho),
        "squared_normalized_disagreement": statistic,
        "nominal_chi_square_reference": threshold,
        "degrees_of_freedom": DEGREES_OF_FREEDOM,
        "reference_quantile": THRESHOLD_QUANTILE,
        "flagged_synthetic_disagreement": flagged,
        "status": (
            "SYNTHETIC_DISAGREEMENT_FLAGGED"
            if flagged
            else "SYNTHETIC_DISAGREEMENT_NOT_FLAGGED"
        ),
        "handling":
            "DIAGNOSTIC_ONLY_RETAIN_BOTH_NO_RUNTIME_ACTION",
        "sensor_auto_suppression_executed": False,
        "health_state_inferred": False,
        "physical_false_alarm_probability_established":
            False,
    }


def require_runtime_conflict_action(*args, **kwargs):
    """No software toggle can make this diagnostic a trust decision."""

    raise ValueError(
        "S8_RUNTIME_CONFLICT_ACTION_NOT_AUTHORIZED"
    )


def information_diagnostic(camera, lidar, rho, xi, xj):
    """Compare local information with or without synthetic correlation."""

    paired, cross = paired_covariance(
        camera,
        lidar,
        rho,
    )

    jc_white = jacobian_on_edge(
        xi, xj, camera
    )
    jl_white = jacobian_on_edge(
        xi, xj, lidar
    )

    lc = np.linalg.cholesky(
        np.asarray(camera.covariance)
    )
    llower = np.linalg.cholesky(
        np.asarray(lidar.covariance)
    )

    raw_jacobian = np.vstack((
        lc @ jc_white,
        llower @ jl_white,
    ))

    independent = np.block([
        [
            np.asarray(camera.covariance),
            np.zeros((6, 6)),
        ],
        [
            np.zeros((6, 6)),
            np.asarray(lidar.covariance),
        ],
    ])

    independent_information = (
        raw_jacobian.T
        @ np.linalg.solve(
            independent,
            raw_jacobian,
        )
    )

    correlated_information = (
        raw_jacobian.T
        @ np.linalg.solve(
            paired,
            raw_jacobian,
        )
    )

    need(
        all(
            np.isfinite(x).all()
            and np.allclose(
                x, x.T,
                atol=1e-7,
            )
            and np.linalg.eigvalsh(x)[0] > 0
            for x in (
                independent_information,
                correlated_information,
            )
        ),
        "NUMERICAL_INFORMATION_UNSUPPORTED",
    )

    return {
        "assumed_correlation": float(rho),
        "cross_covariance_frobenius":
            float(np.linalg.norm(cross)),
        "paired_covariance_min_eigenvalue":
            float(np.linalg.eigvalsh(paired)[0]),
        "independent_information_matrix":
            independent_information.tolist(),
        "correlated_information_matrix":
            correlated_information.tolist(),
        "independent_information_trace":
            float(np.trace(independent_information)),
        "correlated_information_trace":
            float(np.trace(correlated_information)),
        "local_jacobian_dimension": [12, 6],
        "cross_modal_noise_empirically_verified": False,
        "physically_calibrated_information": False,
    }


def conflict_scenarios():
    fixture, packets, pair, _ = camera_lidar_pair()

    xi, xj = comparison_states(
        fixture
    )

    camera = pair["camera"]
    lidar = pair["lidar"]

    modified_packet = perturb_camera(
        camera.packet,
        DISPLACEMENT_M,
    )

    corrupted_camera = JointFactor(
        modified_packet,
        camera.covariance,
    )

    rows = []

    for rho in RHOS:
        baseline = disagreement_diagnostic(
            camera,
            lidar,
            rho,
        )

        corrupted = disagreement_diagnostic(
            corrupted_camera,
            lidar,
            rho,
        )

        information = information_diagnostic(
            camera,
            lidar,
            rho,
            xi,
            xj,
        )

        need(
            baseline[
                "flagged_synthetic_disagreement"
            ] is False
            and corrupted[
                "flagged_synthetic_disagreement"
            ] is True
            and corrupted[
                "squared_normalized_disagreement"
            ] > baseline[
                "squared_normalized_disagreement"
            ],
            "SYNTHETIC_CONFLICT_NOT_SEPARATED",
        )

        need(
            baseline["handling"]
            == corrupted["handling"]
            == "DIAGNOSTIC_ONLY_RETAIN_BOTH_NO_RUNTIME_ACTION",
            "UNAUTHORIZED_SENSOR_HANDLING",
        )

        rows.append({
            "rho": rho,
            "baseline": baseline,
            "corrupted": corrupted,
            "information": information,
        })

    independent = np.asarray(
        rows[0]["information"][
            "independent_information_matrix"
        ]
    )

    zero = np.asarray(
        rows[0]["information"][
            "correlated_information_matrix"
        ]
    )

    positive = np.asarray(
        rows[1]["information"][
            "correlated_information_matrix"
        ]
    )

    negative = np.asarray(
        rows[2]["information"][
            "correlated_information_matrix"
        ]
    )

    need(
        np.allclose(
            independent,
            zero,
            atol=1e-7,
            rtol=1e-9,
        ),
        "ZERO_CORRELATION_BASELINE",
    )

    need(
        not np.allclose(
            positive, independent,
            rtol=1e-5,
        )
        and not np.allclose(
            negative, independent,
            rtol=1e-5,
        ),
        "CORRELATION_NO_EFFECT",
    )

    return rows, packets


def nonlinear_factor_retention(packets):
    """Confirm disturbed measurement remains in the S6 solver."""

    fixture, _ = make_fixture("clean")

    modified = (
        perturb_camera(
            packets[0],
            DISPLACEMENT_M,
        ),
        packets[1],
    )

    _, baseline = estimate_joint(
        fixture,
        packets,
    )

    _, disturbed = estimate_joint(
        fixture,
        modified,
    )

    ids = {
        x["measurement_id"]
        for x in baseline["factor_ledger"]
    }

    altered_ids = {
        x["measurement_id"]
        for x in disturbed["factor_ledger"]
    }

    for audit in (baseline, disturbed):
        need(
            audit["accepted_window_count"] == 4
            and audit["schur_elimination_count"] == 3
            and audit["total_pose_factor_count"] == 9
            and audit["same_edge_camera_lidar_count"] == 2
            and audit["unaccounted_factor_count"] == 0
            and audit["factor_reuse_after_marginalization"]
            is False,
            "SCHUR_FACTOR_ACCOUNTING",
        )

    need(
        ids == altered_ids
        and len(ids) == 9
        and set(baseline["consumed_pose_ids"])
        .isdisjoint(baseline["remaining_pose_ids"])
        and set(disturbed["consumed_pose_ids"])
        .isdisjoint(disturbed["remaining_pose_ids"]),
        "MEASUREMENT_OWNERSHIP_CHANGED",
    )

    return {
        "baseline_factor_count": 9,
        "disturbed_factor_count": 9,
        "shared_edge_factor_pairs": 2,
        "accepted_window_solves": 8,
        "schur_eliminations": 6,
        "factor_ids_preserved": True,
        "automatic_sensor_suppression_executed": False,
        "health_weighting_executed": False,
        "real_factor_execution_authorized": False,
    }


def junit_count(xml):
    cases = list(
        ET.parse(xml).getroot().iter(
            "testcase"
        )
    )

    need(
        len(cases) >= 20
        and len({
            (
                x.get("classname"),
                x.get("name"),
            )
            for x in cases
        }) == len(cases),
        "TEST_CASE_COUNT",
    )

    need(
        all(
            not any(
                y.tag in (
                    "failure",
                    "error",
                    "skipped",
                )
                for y in x
            )
            for x in cases
        ),
        "TESTS_FAILED_OR_SKIPPED",
    )

    return len(cases)


def execute(a):
    s7 = load(a.s7_report)
    s7_validation = load(
        a.s7_validation
    )

    need(
        s7["unit_tests_passed"] == 22
        and s7_validation[
            "unit_tests_verified"
        ] == 22
        and s7_validation[
            "independent_s6_jacobian_recomputation"
        ] is True
        and s7_validation[
            "real_sensor_factor_admission"
        ] is False,
        "S7_LINEAGE",
    )

    rows, packets = conflict_scenarios()

    retention = nonlinear_factor_retention(
        packets
    )

    return {
        "schema": SCHEMA,
        "parent_commit":
            "ebe97e3ee3d3c9872b2b5643de5124bb0cfacf43",
        "engine_sha256": sha(__file__),
        "test_sha256": sha(a.test),
        "junit_sha256": sha(a.xml),
        "s7_report_sha256": sha(a.s7_report),
        "s7_validation_sha256": sha(a.s7_validation),
        "unit_tests_passed": junit_count(a.xml),
        "correlation_scenarios": rows,
        "scenario_count": len(rows),
        "nonlinear_factor_retention": retention,
        "synthetic_correlated_covariance_evaluated": True,
        "synthetic_camera_conflict_flagged": True,
        "conflict_triggered_sensor_suppression": False,
        "conflict_triggered_health_classification": False,
        "runtime_health_weighting_authorized": False,
        "empirical_camera_lidar_noise_independence_verified":
            False,
        "physical_conflict_threshold_calibrated": False,
        "cross_modal_synchronization_verified": False,
        "physical_sensor_extrinsics_verified": False,
        "real_sensor_factor_execution_authorized": False,
        "m2dgr_scoring_authorized": False,
        "health_model_training_authorized": False,
        "live_simulator_launch_authorized": False,
        "raw_sensor_recordings_read": False,
        "new_sensor_acquisitions": 0,
        "scientific_pose_factors": 0,
        "health_labels": 0,
        "git_commit_or_push": False,
        "next":
            "S9_SYNTHETIC_FACTOR_CONFLICT_ADVERSARIAL_STRESS",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    for name in (
        "test",
        "xml",
        "s7_report",
        "s7_validation",
        "report",
    ):
        parser.add_argument(
            "--" + name.replace("_", "-"),
            dest=name,
            required=True,
        )

    args = parser.parse_args()

    result = execute(args)

    write(args.report, result)

    print(
        "S8_UNIT_TESTS="
        f"{result['unit_tests_passed']}_PASSED"
    )
    print("S8_CORRELATION_SCENARIOS=3_VERIFIED")
    print("S8_PAIRED_12D_COVARIANCE=SPD")
    print("S8_INDEPENDENT_VS_CORRELATED_INFORMATION=VERIFIED")
    print("S8_CONTROLLED_CAMERA_CONFLICT=FLAGGED")
    print("S8_RUNTIME_SENSOR_SUPPRESSION=DENIED")
    print("S8_SCHUR_FACTOR_OWNERSHIP=PRESERVED")
    print("S8_SYNTHETIC_CORRELATED_NOISE_AND_CONFLICT=PASS")
