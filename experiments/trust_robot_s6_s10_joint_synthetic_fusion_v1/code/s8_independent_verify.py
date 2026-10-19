"""Independently recalculate S8 covariance and disagreement.

Uses pinned S6/S7 synthetic factor sources, without
importing the S8 analysis engine.
"""

import argparse
import hashlib
import json
import xml.etree.ElementTree as ET

import numpy as np
from scipy.stats import chi2
from scipy.spatial.transform import Rotation

from s7_factor_support import (
    camera_lidar_pair,
    comparison_states,
    jacobian_on_edge,
    perturb_camera,
)


def need(ok, reason):
    if not ok:
        raise AssertionError(
            "S8_INDEPENDENT_FAIL:" + reason
        )


def sha(path):
    return hashlib.sha256(
        open(path, "rb").read()
    ).hexdigest()


def load(path):
    return json.loads(
        open(path, encoding="utf-8").read()
    )


def independent_recalculation(rho, camera, lidar, xi, xj):
    cc = np.asarray(
        camera.covariance,
        dtype=float,
    )

    ll = np.asarray(
        lidar.covariance,
        dtype=float,
    )

    lc = np.linalg.cholesky(cc)
    ld = np.linalg.cholesky(ll)

    cross = rho * (lc @ ld.T)

    full = np.block([
        [cc, cross],
        [cross.T, ll],
    ])

    j = np.vstack([
        lc @ jacobian_on_edge(
            xi, xj, camera
        ),
        ld @ jacobian_on_edge(
            xi, xj, lidar
        ),
    ])

    information = (
        j.T @ np.linalg.solve(full, j)
    )

    independent_covariance = np.block([
        [cc, np.zeros((6, 6))],
        [np.zeros((6, 6)), ll],
    ])

    independent_info = (
        j.T @ np.linalg.solve(
            independent_covariance, j
        )
    )

    conflict_cov = cc + ll - cross - cross.T

    return (
        information,
        independent_info,
        conflict_cov,
    )


def discrepancy(camera, lidar, covariance):
    relative = (
        lidar.packet.measurement.inverse()
        .compose(camera.packet.measurement)
    )

    q = relative.quaternion_wxyz

    rotvec = Rotation.from_quat(
        [q[1], q[2], q[3], q[0]]
    ).as_rotvec()

    delta = np.r_[
        relative.translation_m,
        rotvec,
    ]

    return float(
        delta @ np.linalg.solve(
            covariance, delta
        )
    )


def main(a):
    report = load(a.report)
    s7 = load(a.s7_report)
    validation7 = load(a.s7_validation)

    need(
        report["schema"]
        == "TRUST_ROBOT_S8_SYNTHETIC_CORRELATED_CONFLICT_V1",
        "SCHEMA",
    )

    for key, path in (
        ("engine_sha256", a.engine),
        ("test_sha256", a.test),
        ("junit_sha256", a.xml),
        ("s7_report_sha256", a.s7_report),
        ("s7_validation_sha256", a.s7_validation),
    ):
        need(
            report[key] == sha(path),
            "SOURCE_SHA:" + key,
        )

    need(
        s7["unit_tests_passed"] == 22
        and validation7[
            "unit_tests_verified"
        ] == 22
        and validation7[
            "real_sensor_factor_admission"
        ] is False,
        "S7_LINEAGE",
    )

    cases = list(
        ET.parse(a.xml).getroot().iter(
            "testcase"
        )
    )

    need(
        len(cases) >= 20
        and len(cases) == report["unit_tests_passed"]
        and all(
            not any(
                child.tag in ("failure", "error", "skipped")
                for child in case
            )
            for case in cases
        ),
        "TESTS",
    )

    fixture, packets, factors, _ = camera_lidar_pair()

    camera = factors["camera"]
    lidar = factors["lidar"]

    xi, xj = comparison_states(fixture)

    from s6_joint_fusion import JointFactor

    altered_camera = JointFactor(
        perturb_camera(
            camera.packet, 0.2
        ),
        camera.covariance,
    )

    rows = report["correlation_scenarios"]

    need(
        len(rows) == report["scenario_count"] == 3
        and [r["rho"] for r in rows]
        == [0.0, 0.35, -0.25],
        "CORRELATION_SCENARIOS",
    )

    reference_threshold = float(
        chi2.ppf(0.95, 6)
    )

    for row in rows:
        rho = row["rho"]

        calculated, independent, diffcov = (
            independent_recalculation(
                rho,
                camera,
                lidar,
                xi,
                xj,
            )
        )

        stored_info = row["information"]

        need(
            np.allclose(
                calculated,
                stored_info[
                    "correlated_information_matrix"
                ],
                atol=1e-7,
                rtol=1e-8,
            )
            and np.allclose(
                independent,
                stored_info[
                    "independent_information_matrix"
                ],
                atol=1e-7,
                rtol=1e-8,
            ),
            "INDEPENDENT_INFORMATION_RECOMPUTATION",
        )

        need(
            np.linalg.eigvalsh(
                calculated
            )[0] > 0
            and np.linalg.eigvalsh(
                diffcov
            )[0] > 0,
            "SPD_REQUIREMENT",
        )

        nominal = discrepancy(
            camera,
            lidar,
            diffcov,
        )

        disturbed = discrepancy(
            altered_camera,
            lidar,
            diffcov,
        )

        need(
            np.isclose(
                nominal,
                row["baseline"][
                    "squared_normalized_disagreement"
                ],
                atol=1e-8,
                rtol=1e-8,
            )
            and np.isclose(
                disturbed,
                row["corrupted"][
                    "squared_normalized_disagreement"
                ],
                atol=1e-8,
                rtol=1e-8,
            ),
            "INDEPENDENT_DISAGREEMENT_RECOMPUTATION",
        )

        need(
            nominal < reference_threshold < disturbed
            and row["baseline"][
                "flagged_synthetic_disagreement"
            ] is False
            and row["corrupted"][
                "flagged_synthetic_disagreement"
            ] is True,
            "SYNTHETIC_CONFLICT_CLASSIFICATION",
        )

        for key in ("baseline", "corrupted"):
            diagnostic = row[key]

            need(
                np.isclose(
                    diagnostic[
                        "nominal_chi_square_reference"
                    ],
                    reference_threshold,
                )
                and diagnostic["handling"]
                == "DIAGNOSTIC_ONLY_RETAIN_BOTH_NO_RUNTIME_ACTION"
                and diagnostic[
                    "sensor_auto_suppression_executed"
                ] is False
                and diagnostic[
                    "health_state_inferred"
                ] is False
                and diagnostic[
                    "physical_false_alarm_probability_established"
                ] is False,
                "POLICY_SCOPE",
            )

    first = np.asarray(
        rows[0]["information"][
            "correlated_information_matrix"
        ]
    )

    second = np.asarray(
        rows[1]["information"][
            "correlated_information_matrix"
        ]
    )

    need(
        not np.allclose(
            first, second,
            rtol=1e-5,
        ),
        "CORRELATION_INFORMATION_SENSITIVITY",
    )

    retention = report[
        "nonlinear_factor_retention"
    ]

    need(
        retention["baseline_factor_count"] == 9
        and retention["disturbed_factor_count"] == 9
        and retention["shared_edge_factor_pairs"] == 2
        and retention["accepted_window_solves"] == 8
        and retention["schur_eliminations"] == 6
        and retention["factor_ids_preserved"] is True
        and retention[
            "automatic_sensor_suppression_executed"
        ] is False
        and retention[
            "real_factor_execution_authorized"
        ] is False,
        "NONLINEAR_FACTOR_RETENTION",
    )

    for key in (
        "conflict_triggered_sensor_suppression",
        "conflict_triggered_health_classification",
        "runtime_health_weighting_authorized",
        "empirical_camera_lidar_noise_independence_verified",
        "physical_conflict_threshold_calibrated",
        "cross_modal_synchronization_verified",
        "physical_sensor_extrinsics_verified",
        "real_sensor_factor_execution_authorized",
        "m2dgr_scoring_authorized",
        "health_model_training_authorized",
        "live_simulator_launch_authorized",
        "raw_sensor_recordings_read",
        "git_commit_or_push",
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
            "NONZERO_SCIENCE_COUNT",
        )

    result = {
        "schema":
            "TRUST_ROBOT_S8_INDEPENDENT_VALIDATION_V1",
        "engine_sha256": sha(a.engine),
        "test_sha256": sha(a.test),
        "verifier_sha256": sha(__file__),
        "junit_sha256": sha(a.xml),
        "report_sha256": sha(a.report),
        "unit_tests_verified": len(cases),
        "correlation_scenarios_verified": 3,
        "paired_covariance_numerically_spd": True,
        "independent_information_recomputation": True,
        "independent_conflict_recomputation": True,
        "nonlinear_schur_factor_retention_verified": True,
        "automatic_conflict_suppression_authorized": False,
        "physical_noise_independence_verified": False,
        "real_sensor_factor_admission": False,
        "new_sensor_acquisitions": 0,
        "scientific_pose_factors": 0,
        "health_labels": 0,
    }

    with open(
        a.validation,
        "x",
        encoding="utf-8",
    ) as f:
        json.dump(
            result,
            f,
            sort_keys=True,
            indent=2,
        )
        f.write("\n")

    print(
        "S8_INDEPENDENT_UNIT_TESTS="
        f"{len(cases)}_VERIFIED"
    )
    print("S8_INDEPENDENT_CORRELATED_COVARIANCE=VERIFIED")
    print("S8_INDEPENDENT_INFORMATION_RECOMPUTATION=PASS")
    print("S8_INDEPENDENT_CONFLICT_RECOMPUTATION=PASS")
    print("S8_INDEPENDENT_SENSOR_SUPPRESSION=DENIED")
    print("S8_INDEPENDENT_VALIDATION=PASS")


if __name__ == "__main__":
    p = argparse.ArgumentParser()

    for name in (
        "engine",
        "test",
        "xml",
        "s7_report",
        "s7_validation",
        "report",
        "validation",
    ):
        p.add_argument(
            "--" + name.replace("_", "-"),
            dest=name,
            required=True,
        )

    main(p.parse_args())
