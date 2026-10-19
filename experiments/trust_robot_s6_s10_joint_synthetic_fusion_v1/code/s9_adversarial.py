"""S9 adversarial manufactured camera/LiDAR disagreement study.

The diagnostic is not a calibrated physical test or runtime supervisor.
No recorded-source admission, health inference, or automatic suppression.
"""
import argparse
import dataclasses
import hashlib
import json
import math
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
from scipy.stats import chi2

from trust_robot.clean_backbone import PoseSE3
from trust_robot.analytic_inertial_15d import make_fixture
from trust_robot.analytic_three_modality_bridge import manufactured_camera_packets
from s6_joint_fusion import JointFactor, estimate_joint, validate_factors, canonical
from s7_factor_support import camera_lidar_pair
from s8_correlated_conflict import paired_covariance, disagreement_diagnostic, require_runtime_conflict_action

SCHEMA = "TRUST_ROBOT_S9_ADVERSARIAL_CONFLICT_STRESS_V1"
RHOS = (-0.25, 0.0, 0.35)
SHIFTS = (-0.2, -0.1, 0.0, 0.1, 0.2)
DENIALS = ("drop_camera", "drop_lidar", "infer_unusable", "weight_camera")


def need(condition, reason):
    if not condition:
        raise ValueError("S9_FAIL_CLOSED:" + reason)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def changed_camera(packet, shift):
    need(type(shift) in (int, float) and math.isfinite(shift) and abs(shift) <= 0.2,
         "INVALID_INJECTED_SHIFT")
    need(packet.modality == "camera" and packet.origin == "ANALYTIC_FIXTURE" and packet.edge == (0, 1),
         "INVALID_SYNTHETIC_ORIGIN")
    original = packet.measurement
    vector = np.asarray(original.translation_m, dtype=float).copy()
    vector[0] += shift
    return dataclasses.replace(packet, measurement=PoseSE3(
        translation_m=tuple(float(x) for x in vector),
        quaternion_wxyz=original.quaternion_wxyz,
    ))


def stress_grid():
    fixture, packets, pair, _ = camera_lidar_pair()
    camera, lidar = pair["camera"], pair["lidar"]
    rows = []
    for rho in RHOS:
        cov, cross = paired_covariance(camera, lidar, rho)
        need(cov.shape == (12, 12) and np.linalg.eigvalsh(cov)[0] > 0,
             "NON_SPD_ASSUMED_COVARIANCE")
        entries = []
        for offset in SHIFTS:
            changed = JointFactor(changed_camera(camera.packet, offset), camera.covariance)
            result = disagreement_diagnostic(changed, lidar, rho)
            need(result["handling"] == "DIAGNOSTIC_ONLY_RETAIN_BOTH_NO_RUNTIME_ACTION" and
                 result["sensor_auto_suppression_executed"] is False and
                 result["health_state_inferred"] is False and
                 result["physical_false_alarm_probability_established"] is False,
                 "UNAUTHORIZED_RUNTIME_BEHAVIOR")
            entries.append({
                "camera_shift_m": float(offset),
                "normalized_squared_disagreement": result["squared_normalized_disagreement"],
                "nominal_chi_square_reference": result["nominal_chi_square_reference"],
                "flagged": result["flagged_synthetic_disagreement"],
                "camera_measurement_id": changed.key,
                "lidar_measurement_id": lidar.key,
                "automatic_action": False,
            })
        need(entries[2]["flagged"] is False and entries[0]["flagged"] is True and
             entries[4]["flagged"] is True and
             entries[0]["normalized_squared_disagreement"] > entries[2]["normalized_squared_disagreement"] and
             entries[4]["normalized_squared_disagreement"] > entries[2]["normalized_squared_disagreement"],
             "ENDPOINT_STRESS_SEPARATION")
        rows.append({
            "assumed_cross_correlation": float(rho),
            "paired_covariance_min_eigenvalue": float(np.linalg.eigvalsh(cov)[0]),
            "cross_covariance_frobenius": float(np.linalg.norm(cross)),
            "disagreement_grid": entries,
            "physical_detection_rate_claimed": False,
        })
    return rows, packets


def require_runtime_action(action):
    need(action in DENIALS, "UNKNOWN_ACTION")
    try:
        require_runtime_conflict_action(**{action: True})
    except ValueError:
        return "DENIED"
    raise AssertionError("S9_RUNTIME_ACTION_BYPASS")


def solver_stress():
    fixture, manufactured_truth = make_fixture("clean")
    packets = manufactured_camera_packets(manufactured_truth, seed=13)
    rows = []
    previous_ids = None
    states_by_shift = {}
    for offset in (-0.2, 0.0, 0.2):
        modified = (changed_camera(packets[0], offset), packets[1])
        states, audit = estimate_joint(fixture, modified)
        ledger = audit["factor_ledger"]
        ids = {row["measurement_id"] for row in ledger}
        consumed = set(audit["consumed_pose_ids"])
        remaining = set(audit["remaining_pose_ids"])
        need(len(states) == 5 and len(ledger) == len(ids) == 9 and
             consumed.isdisjoint(remaining) and consumed | remaining == ids and
             audit["accepted_window_count"] == 4 and audit["schur_elimination_count"] == 3 and
             audit["same_edge_camera_lidar_count"] == 2 and
             audit["unaccounted_factor_count"] == 0 and
             audit["factor_reuse_after_marginalization"] is False and
             audit["real_sensor_factor_admitted"] is False,
             "SOLVER_FACTOR_OWNERSHIP")
        if previous_ids is None:
            previous_ids = ids
        need(previous_ids == ids, "FACTOR_IDENTITIES_CHANGED")
        states_by_shift[offset] = states
        rows.append({
            "camera_shift_m": float(offset),
            "estimated_trajectory_sha256": hashlib.sha256(canonical(states)).hexdigest(),
            "factor_count": len(ledger),
            "accepted_window_solves": audit["accepted_window_count"],
            "schur_eliminations": audit["schur_elimination_count"],
            "consumed_factor_count": len(consumed),
            "remaining_factor_count": len(remaining),
            "measurement_ids": sorted(ids),
            "state_delta_from_unperturbed_m": None,
            "real_sensor_data_used": False,
        })
    original_states = states_by_shift[0.0]
    for row in rows:
        if row["camera_shift_m"] == 0.0:
            row["state_delta_from_unperturbed_m"] = 0.0
            continue
        changed_states = states_by_shift[row["camera_shift_m"]]
        delta = max(float(np.linalg.norm(np.asarray(a["position_m"]) - np.asarray(b["position_m"])))
                    for a, b in zip(changed_states, original_states))
        need(delta > 1e-6 and math.isfinite(delta), "SOLVER_PERTURBATION_NOT_VISIBLE")
        row["state_delta_from_unperturbed_m"] = delta
    need(len({row["estimated_trajectory_sha256"] for row in rows}) == 3,
         "SOLVER_STATES_NOT_DISTINCT")
    return rows


def test_count(xml):
    cases = list(ET.parse(xml).getroot().iter("testcase"))
    need(len(cases) >= 24 and
         len({(c.get("classname"), c.get("name")) for c in cases}) == len(cases) and
         not any(child.tag in ("failure", "error", "skipped") for case in cases for child in case),
         "JUNIT_NOT_ALL_PASSED")
    return len(cases)


def execute(args):
    s8 = json.loads(Path(args.s8_report).read_text())
    v8 = json.loads(Path(args.s8_validation).read_text())
    need(s8["unit_tests_passed"] == v8["unit_tests_verified"] == 27 and
         s8["scenario_count"] == 3 and
         v8["independent_conflict_recomputation"] is True and
         v8["real_sensor_factor_admission"] is False,
         "S8_FROZEN_LINEAGE")
    grid, _ = stress_grid()
    solves = solver_stress()
    denials = {action: require_runtime_action(action) for action in DENIALS}
    need(all(s == "DENIED" for s in denials.values()), "RUNTIME_ACTION_NOT_DENIED")
    return {
        "schema": SCHEMA,
        "parent_commit": "ebe97e3ee3d3c9872b2b5643de5124bb0cfacf43",
        "engine_sha256": sha(__file__),
        "test_sha256": sha(args.test),
        "junit_sha256": sha(args.xml),
        "s8_report_sha256": sha(args.s8_report),
        "s8_validation_sha256": sha(args.s8_validation),
        "unit_tests_passed": test_count(args.xml),
        "correlation_grid": grid,
        "correlation_count": len(grid),
        "perturbation_count_per_correlation": len(SHIFTS),
        "total_diagnostic_cases": len(grid) * len(SHIFTS),
        "nonlinear_synthetic_scenarios": solves,
        "runtime_action_denials": denials,
        "manufactured_chi_square_reference_only": True,
        "physical_false_alarm_probability_calibrated": False,
        "true_fault_detection_rate_established": False,
        "empirical_noise_cross_correlation_established": False,
        "independent_real_reference_scored": False,
        "automatic_sensor_suppression_executed": False,
        "health_state_inference_executed": False,
        "real_sensor_factor_execution_authorized": False,
        "m2dgr_scoring_authorized": False,
        "health_model_training_authorized": False,
        "live_simulator_launch_authorized": False,
        "raw_sensor_records_read": False,
        "new_sensor_acquisitions": 0,
        "scientific_pose_factors": 0,
        "health_labels": 0,
        "git_commit_or_push": False,
        "next": "S10_SYNTHETIC_REGRESSION_AND_CHECKPOINT_REVIEW",
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    for name in ("test", "xml", "s8_report", "s8_validation", "report"):
        p.add_argument("--" + name.replace("_", "-"), dest=name, required=True)
    a = p.parse_args()
    report = execute(a)
    with Path(a.report).open("x", encoding="utf-8") as f:
        json.dump(report, f, indent=2, sort_keys=True, allow_nan=False)
        f.write("\n")
    print(f"S9_ADVERSARIAL_UNIT_TESTS={report['unit_tests_passed']}_PASSED")
    print("S9_CORRELATION_PERTURBATION_GRID=15_CASES")
    print("S9_EXTREME_SYNTHETIC_CONFLICTS=FLAGGED")
    print("S9_NONLINEAR_SCHUR_STRESS=3_SCENARIOS")
    print("S9_RUNTIME_SENSOR_ACTIONS=4_DENIED")
    print("S9_SCIENTIFIC_GATES=CLOSED")
    print("S9_ADVERSARIAL_CONFLICT_STRESS=PASS")
