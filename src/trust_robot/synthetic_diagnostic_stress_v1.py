"""Offline deterministic *synthetic condition* stress of published unlabelled diagnostics.

Manufactured fixtures ONLY. No recorded data, health labels, sync, pose factors,
actuator interface, or causal attack attribution. Intent is a scenario-design tag.
"""
from __future__ import annotations

from copy import deepcopy
from math import isfinite
from typing import Any

from trust_robot import unlabelled_multimodal_diagnostics_v1 as diag

SCHEMA = "trust_robot_synthetic_diagnostic_stress_v1"
SOURCE_ROLE = "SYNTHETIC_MANUFACTURED_FIXTURES_ONLY"
CASES = (
    ("camera_zero_benign", "camera", "zero_payload", "BENIGN_FAULT_SCENARIO", False),
    ("camera_zero_adversarial", "camera", "zero_payload", "ADVERSARIAL_SCENARIO", False),
    ("camera_startup_zero", "camera", "startup_zero", "BENIGN_FAULT_SCENARIO", False),
    ("camera_delivery_burst", "camera", "delivery_burst", "BENIGN_FAULT_SCENARIO", False),
    ("camera_message_removal", "camera", "message_removal", "BENIGN_FAULT_SCENARIO", False),
    ("camera_header_perturbation", "camera", "header_offset", "ADVERSARIAL_SCENARIO", False),
    ("camera_duplicate_header", "camera", "duplicate_header", "ADVERSARIAL_SCENARIO", True),
    ("imu_bias", "imu", "bias", "BENIGN_FAULT_SCENARIO", False),
    ("imu_noise", "imu", "deterministic_noise", "BENIGN_FAULT_SCENARIO", False),
    ("imu_stuck", "imu", "stuck_vector", "BENIGN_FAULT_SCENARIO", False),
    ("imu_nonfinite", "imu", "nonfinite_vector", "ADVERSARIAL_SCENARIO", True),
    ("lidar_slots_zeroed", "lidar", "slot_zeroing", "BENIGN_FAULT_SCENARIO", False),
    ("lidar_layout_shift", "lidar", "layout_shift", "BENIGN_FAULT_SCENARIO", False),
    ("lidar_invalid_field_count", "lidar", "invalid_layout", "ADVERSARIAL_SCENARIO", True),
)


def manufactured_baseline() -> dict[str, Any]:
    """Fixed, nonrandom signals unrelated to any physical bag or dataset split."""
    return {
        "left": [{"header_ns": 1_000_000_000+i*33_333_333,
                  "recorder_ns": 5_000_000_000+i*33_333_333,
                  "zero_payload": False} for i in range(12)],
        "right": [{"header_ns": 1_000_000_000+i*33_333_333,
                   "recorder_ns": 5_002_000_000+i*33_333_333,
                   "zero_payload": False} for i in range(12)],
        "imu": [{"accel_xyz": [0.02*(i % 4), 0.0, 9.70],
                 "gyro_xyz": [0.001*(i % 4), 0.003, 0.004]} for i in range(16)],
        "lidar": [{"point_slots": 120, "point_step_bytes": 26, "field_count": 6}
                  for _ in range(4)],
    }


def apply_case(baseline: dict, case_id: str) -> dict:
    """Apply a one-modality intervention to a deep copy; never mutate control."""
    identifiers = {row[0] for row in CASES}
    if case_id not in identifiers:
        raise ValueError("unknown synthetic intervention")
    x = deepcopy(baseline)
    if case_id in ("camera_zero_benign", "camera_zero_adversarial"):
        for i in (5, 6, 7):
            x["left"][i]["zero_payload"] = True
    elif case_id == "camera_startup_zero":
        for i in (0, 1, 2):
            x["left"][i]["zero_payload"] = True
    elif case_id == "camera_delivery_burst":
        x["right"][6]["recorder_ns"] = x["right"][5]["recorder_ns"] + 1_000_000
    elif case_id == "camera_message_removal":
        del x["right"][5]
    elif case_id == "camera_header_perturbation":
        for i in (4, 5, 6, 7):
            x["right"][i]["header_ns"] += 3_000_000
    elif case_id == "camera_duplicate_header":
        x["right"][4]["header_ns"] = x["right"][3]["header_ns"]
    elif case_id == "imu_bias":
        for v in x["imu"]:
            v["accel_xyz"][2] += 0.4
    elif case_id == "imu_noise":
        for i, v in enumerate(x["imu"]):
            v["gyro_xyz"][0] += 0.06 if i % 2 == 0 else -0.06
    elif case_id == "imu_stuck":
        for i in (3, 4, 5, 6):
            x["imu"][i] = deepcopy(x["imu"][2])
    elif case_id == "imu_nonfinite":
        x["imu"][4]["gyro_xyz"][0] = float("nan")
    elif case_id == "lidar_slots_zeroed":
        for i in (1, 2):
            x["lidar"][i]["point_slots"] = 0
    elif case_id == "lidar_layout_shift":
        x["lidar"][2]["field_count"] = 5
    elif case_id == "lidar_invalid_field_count":
        x["lidar"][2]["field_count"] = diag.MAX_FIELDS + 1
    return x


def _characterize(x: dict) -> dict:
    left = diag.camera_diagnostics(x["left"])
    right = diag.camera_diagnostics(x["right"])
    joined = diag.numeric_header_join(x["left"], x["right"])
    imu = diag.imu_descriptive_diagnostics(x["imu"])
    lidar = diag.lidar_structural_diagnostics(x["lidar"])
    safe = diag.public_summary_only(left, right, joined, imu, lidar)
    if safe["physical_sensor_health_labels_accepted"] != 0 or safe["real_factor_admission"] != "CLOSED" or safe["physical_sync_qualified"] is not False:
        raise AssertionError("published evidence gates unexpectedly opened")
    return {"safe": safe, "left": left, "right": right, "join": joined, "imu": imu, "lidar": lidar}


def _bounded_delta(a: float | int | None, b: float | int | None) -> float | int | None:
    if a is None or b is None:
        return None
    delta = b - a
    if isinstance(delta, float):
        if not isfinite(delta):
            raise ValueError("nonfinite diagnostic delta")
        return round(delta, 10)
    return delta


def _deltas(base: dict, current: dict) -> dict:
    """Only reviewed aggregate deltas. No frame, time, vector, or sensor payload export."""
    return {
        "left_zero_payload_delta": _bounded_delta(base["left"]["zero_payload_count"], current["left"]["zero_payload_count"]),
        "right_frame_count_delta": _bounded_delta(base["right"]["count"], current["right"]["count"]),
        "numeric_equal_headers_delta": _bounded_delta(base["join"]["numeric_equal_header_count"], current["join"]["numeric_equal_header_count"]),
        "right_short_interarrival_delta": _bounded_delta(base["right"]["recorder_burst_lt_10ms"], current["right"]["recorder_burst_lt_10ms"]),
        "right_long_interarrival_delta": _bounded_delta(base["right"]["recorder_gap_ge_50ms"], current["right"]["recorder_gap_ge_50ms"]),
        "imu_accel_norm_mean_delta": _bounded_delta(base["imu"]["acceleration_norm_m_s2"]["mean"], current["imu"]["acceleration_norm_m_s2"]["mean"]),
        "imu_gyro_norm_mean_delta": _bounded_delta(base["imu"]["angular_speed_norm_rad_s"]["mean"], current["imu"]["angular_speed_norm_rad_s"]["mean"]),
        "lidar_point_slots_delta": _bounded_delta(base["lidar"]["reported_point_slots"], current["lidar"]["reported_point_slots"]),
        "lidar_layout_count_delta": _bounded_delta(len(base["lidar"]["layouts"]), len(current["lidar"]["layouts"])),
    }


def run_matrix() -> dict:
    """Paired control/treatment comparisons, with expected schema denials counted."""
    baseline = manufactured_baseline()
    control = _characterize(baseline)
    rows = []
    for case_id, modality, mechanism, scenario_intent, expected_rejection in CASES:
        altered = apply_case(baseline, case_id)
        try:
            observed = _characterize(altered)
        except ValueError:
            if not expected_rejection:
                raise
            rows.append({"case_id": case_id, "modality": modality, "mechanism": mechanism,
                         "scenario_intent_design_only": scenario_intent,
                         "outcome": "EXPECTED_INPUT_REJECTION", "aggregate_deltas": None})
        else:
            if expected_rejection:
                raise AssertionError("malformed synthetic fixture unexpectedly accepted")
            delta = _deltas(control, observed)
            rows.append({"case_id": case_id, "modality": modality, "mechanism": mechanism,
                         "scenario_intent_design_only": scenario_intent,
                         "outcome": "DESCRIPTIVE_CHANGE" if any(v != 0 for v in delta.values() if v is not None) else "NO_FEATURE_CHANGE",
                         "aggregate_deltas": delta})
    return {"schema": SCHEMA, "source_role": SOURCE_ROLE,
            "baseline": "FROZEN_MANUFACTURED_CONTROL", "seed": "NONE_FIXED_ARITHMETIC",
            "scenario_count": len(rows),
            "expected_rejections": sum(row["outcome"] == "EXPECTED_INPUT_REJECTION" for row in rows),
            "physical_health_labels_accepted": 0, "real_estimator_factors": "DENIED",
            "trained_health_model": "NOT_QUALIFIED", "physical_sync": "NOT_QUALIFIED",
            "robot_control": "DENIED", "attack_attribution_from_features": "DENIED",
            "m2dgr_train_validation_sealed": "NO_DATASET_ACCESS",
            "uncaptured_features": ["camera_blur", "camera_stale_content", "lidar_return_geometry", "physical_clock_binding"],
            "interpretation": "Synthetic interventions are NOT independently measured health labels, physical faults, or attack identification",
            "rows": rows}
