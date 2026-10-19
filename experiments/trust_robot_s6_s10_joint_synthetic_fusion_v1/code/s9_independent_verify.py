"""Independent S9 check from verified S6/S7 sources, not S9 routines."""
import argparse
import dataclasses
import hashlib
import json
import math
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation
from scipy.stats import chi2

from trust_robot.clean_backbone import PoseSE3
from trust_robot.analytic_inertial_15d import make_fixture
from trust_robot.analytic_three_modality_bridge import manufactured_camera_packets
from s6_joint_fusion import JointFactor, estimate_joint, canonical
from s7_factor_support import camera_lidar_pair


def need(ok, reason):
    if not ok:
        raise AssertionError("S9_INDEPENDENT_FAIL:" + reason)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def modified_packet(packet, delta):
    p = packet.measurement
    v = np.asarray(p.translation_m, dtype=float).copy()
    v[0] += delta
    return dataclasses.replace(packet, measurement=PoseSE3(
        translation_m=tuple(float(x) for x in v),
        quaternion_wxyz=p.quaternion_wxyz,
    ))


def recomputed_grid():
    _, _, pair, _ = camera_lidar_pair()
    cam, lidar = pair["camera"], pair["lidar"]
    cc, ll = np.asarray(cam.covariance), np.asarray(lidar.covariance)
    lc, ld = np.linalg.cholesky(cc), np.linalg.cholesky(ll)
    results = []
    for rho in (-.25, 0., .35):
        cross = rho * lc @ ld.T
        block = np.block([[cc, cross], [cross.T, ll]])
        diff_cov = cc + ll - cross - cross.T
        need(np.linalg.eigvalsh(block)[0] > 0 and np.linalg.eigvalsh(diff_cov)[0] > 0,
             "RECOMPUTED_COVARIANCE_NOT_SPD")
        entries = []
        for delta in (-.2, -.1, 0., .1, .2):
            packet = modified_packet(cam.packet, delta)
            difference = lidar.packet.measurement.inverse().compose(packet.measurement)
            q = difference.quaternion_wxyz
            rot = Rotation.from_quat([q[1], q[2], q[3], q[0]]).as_rotvec()
            vector = np.r_[difference.translation_m, rot]
            stat = float(vector @ np.linalg.solve(diff_cov, vector))
            threshold = float(chi2.ppf(.95, 6))
            entries.append((delta, stat, threshold, stat > threshold))
        results.append((rho, float(np.linalg.eigvalsh(block)[0]),
                        float(np.linalg.norm(cross)), entries, cam.key, lidar.key))
    return results


def recomputed_solver():
    fixture, truth = make_fixture("clean")
    packets = manufactured_camera_packets(truth, seed=13)
    states = {}
    audits = {}
    for shift in (-.2, 0., .2):
        result, audit = estimate_joint(fixture, (modified_packet(packets[0], shift), packets[1]))
        states[shift] = result
        audits[shift] = audit
    return states, audits


def main(a):
    report = load(a.report)
    prior = load(a.s8_report)
    vp = load(a.s8_validation)
    need(report["schema"] == "TRUST_ROBOT_S9_ADVERSARIAL_CONFLICT_STRESS_V1" and
         report["parent_commit"] == "ebe97e3ee3d3c9872b2b5643de5124bb0cfacf43",
         "SCHEMA_LINEAGE")
    for field, path in (("engine_sha256", a.engine), ("test_sha256", a.test),
                        ("junit_sha256", a.xml), ("s8_report_sha256", a.s8_report),
                        ("s8_validation_sha256", a.s8_validation)):
        need(report[field] == sha(path), "HASH_" + field)
    need(prior["unit_tests_passed"] == vp["unit_tests_verified"] == 27 and
         vp["real_sensor_factor_admission"] is False, "S8_BOUNDARY")
    cases = list(ET.parse(a.xml).getroot().iter("testcase"))
    need(len(cases) >= 40 and len(cases) == report["unit_tests_passed"] and
         not any(c.tag in ("failure", "error", "skipped") for row in cases for c in row),
         "JUNIT_VERIFICATION")
    grid = recomputed_grid()
    need(len(grid) == report["correlation_count"] == 3 and
         report["perturbation_count_per_correlation"] == 5 and
         report["total_diagnostic_cases"] == 15, "GRID_DIMENSIONS")
    for stored, (rho, min_eigen, cross_norm, recomputed, cam_id, lidar_id) in zip(report["correlation_grid"], grid):
        need(math.isclose(stored["assumed_cross_correlation"], rho, abs_tol=1e-14) and
             np.isclose(stored["paired_covariance_min_eigenvalue"], min_eigen) and
             np.isclose(stored["cross_covariance_frobenius"], cross_norm) and
             stored["physical_detection_rate_claimed"] is False,
             "COVARIANCE_GRID_RECALC")
        for row, (offset, stat, threshold, flag) in zip(stored["disagreement_grid"], recomputed):
            need(row["camera_shift_m"] == offset and
                 np.isclose(row["normalized_squared_disagreement"], stat, atol=1e-10, rtol=1e-10) and
                 np.isclose(row["nominal_chi_square_reference"], threshold) and
                 row["flagged"] is bool(flag) and
                 row["camera_measurement_id"] == cam_id and
                 row["lidar_measurement_id"] == lidar_id and
                 row["automatic_action"] is False,
                 "INDEPENDENT_GRID_RECALC")
    states, audits = recomputed_solver()
    solver_rows = report["nonlinear_synthetic_scenarios"]
    need(len(solver_rows) == 3 and [x["camera_shift_m"] for x in solver_rows] == [-.2, 0., .2],
         "SOLVER_ROW_COUNT")
    original = states[0.]
    for row in solver_rows:
        shift = row["camera_shift_m"]
        audit, actual = audits[shift], states[shift]
        ids = {entry["measurement_id"] for entry in audit["factor_ledger"]}
        consumed = set(audit["consumed_pose_ids"])
        remaining = set(audit["remaining_pose_ids"])
        delta = max(float(np.linalg.norm(np.asarray(x["position_m"]) - np.asarray(y["position_m"])))
                    for x, y in zip(actual, original))
        need(row["estimated_trajectory_sha256"] == hashlib.sha256(canonical(actual)).hexdigest() and
             row["factor_count"] == len(ids) == 9 and
             row["accepted_window_solves"] == audit["accepted_window_count"] == 4 and
             row["schur_eliminations"] == audit["schur_elimination_count"] == 3 and
             row["consumed_factor_count"] == len(consumed) and
             row["remaining_factor_count"] == len(remaining) and
             row["measurement_ids"] == sorted(ids) and
             consumed.isdisjoint(remaining) and consumed | remaining == ids and
             np.isclose(row["state_delta_from_unperturbed_m"], delta, atol=1e-10, rtol=1e-8) and
             row["real_sensor_data_used"] is False,
             "SOLVER_RECALCULATION")
    need(report["runtime_action_denials"] == {
        "drop_camera": "DENIED", "drop_lidar": "DENIED",
        "infer_unusable": "DENIED", "weight_camera": "DENIED",
    }, "RUNTIME_ACTION_DENIALS")
    for flag in (
        "physical_false_alarm_probability_calibrated", "true_fault_detection_rate_established",
        "empirical_noise_cross_correlation_established", "independent_real_reference_scored",
        "automatic_sensor_suppression_executed", "health_state_inference_executed",
        "real_sensor_factor_execution_authorized", "m2dgr_scoring_authorized",
        "health_model_training_authorized", "live_simulator_launch_authorized",
        "raw_sensor_records_read", "git_commit_or_push",
    ):
        need(report[flag] is False, "CLOSED_SCIENCE_GATE_" + flag)
    for key in ("new_sensor_acquisitions", "scientific_pose_factors", "health_labels"):
        need(type(report[key]) is int and report[key] == 0, "SCIENCE_COUNT_" + key)
    result = {
        "schema": "TRUST_ROBOT_S9_INDEPENDENT_VALIDATION_V1",
        "engine_sha256": sha(a.engine), "test_sha256": sha(a.test),
        "verifier_sha256": sha(__file__), "junit_sha256": sha(a.xml),
        "report_sha256": sha(a.report), "unit_tests_verified": len(cases),
        "independent_grid_cases_recomputed": 15,
        "independent_nonlinear_scenarios_recomputed": 3,
        "synthetic_conflict_extremes_detected": True,
        "factor_ownership_verified": True,
        "runtime_actions_denied": 4,
        "empirical_conflict_threshold_calibrated": False,
        "real_sensor_factor_admission": False,
        "new_sensor_acquisitions": 0, "scientific_pose_factors": 0, "health_labels": 0,
    }
    with Path(a.validation).open("x", encoding="utf-8") as f:
        json.dump(result, f, indent=2, sort_keys=True)
        f.write("\n")
    print(f"S9_INDEPENDENT_UNIT_TESTS={len(cases)}_VERIFIED")
    print("S9_INDEPENDENT_CONFLICT_GRID=15_RECOMPUTED")
    print("S9_INDEPENDENT_NONLINEAR_SOLVES=3_RECOMPUTED")
    print("S9_INDEPENDENT_RUNTIME_ACTIONS=4_DENIED")
    print("S9_INDEPENDENT_VALIDATION=PASS")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    for name in ("engine", "test", "xml", "s8_report", "s8_validation", "report", "validation"):
        p.add_argument("--" + name.replace("_", "-"), dest=name, required=True)
    main(p.parse_args())
