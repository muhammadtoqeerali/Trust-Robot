"""Bounded, offline, label-free diagnostics; no ROS, capture, estimator, or actuator dependency.

All numeric header and recorder axes are distinct and physically unqualified.
All status terms refer ONLY to observation/data integrity, never sensor health.
"""
from __future__ import annotations
from collections import Counter
from math import isfinite, sqrt
from statistics import median, mean, pstdev
from typing import Any

MAX_ITEMS = 20000
MAX_POINTS = 2000000
MAX_FIELDS = 32


def _seq(values: Any, name: str) -> list:
    if not isinstance(values, list) or len(values) > MAX_ITEMS:
        raise ValueError(f"{name}: expected bounded list")
    return values


def _number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise ValueError(f"{name}: numeric required")
    result = float(value)
    if not isfinite(result):
        raise ValueError(f"{name}: nonfinite")
    return result


def _summary(values: list[float]) -> dict:
    if not values:
        return {"count": 0, "mean": None, "median": None, "min": None, "max": None, "population_std": None}
    return {"count": len(values), "mean": mean(values), "median": median(values),
            "min": min(values), "max": max(values), "population_std": pstdev(values)}


def camera_diagnostics(frames: list[dict]) -> dict:
    """Frames: ordered per lane; bool zero_payload, integer header_ns/recorder_ns.

    This measures numerical clock differences without establishing clock equivalence.
    A fully zero payload is not itself evidence of physical sensor failure.
    """
    _seq(frames, "frames")
    if not frames:
        return {"count": 0, "zero_payload_count": 0, "first_nonzero_ordinal": None,
                "zero_after_first_nonzero": 0, "header_intervals_ms": _summary([]),
                "recorder_intervals_ms": _summary([]), "recorder_burst_lt_10ms": 0,
                "recorder_gap_ge_50ms": 0, "observation_flags": ["NO_OBSERVATIONS"]}
    for i, f in enumerate(frames):
        if not isinstance(f, dict) or set(f) != {"zero_payload", "header_ns", "recorder_ns"}:
            raise ValueError("frame schema must be exact")
        if type(f["zero_payload"]) is not bool:
            raise ValueError("zero_payload must be bool")
        for axis in ("header_ns", "recorder_ns"):
            if type(f[axis]) is not int or f[axis] < 0 or f[axis] > 2**63 - 1:
                raise ValueError(f"{axis} invalid")
    first = next((i for i, f in enumerate(frames) if not f["zero_payload"]), None)
    hi = [(b["header_ns"]-a["header_ns"])/1e6 for a, b in zip(frames, frames[1:])]
    ri = [(b["recorder_ns"]-a["recorder_ns"])/1e6 for a, b in zip(frames, frames[1:])]
    flags = []
    if any(f["zero_payload"] for f in frames):
        flags.append("ZERO_IMAGE_PAYLOAD_OBSERVED")
    if any(v < 0 for v in hi):
        flags.append("HEADER_NUMERIC_REVERSAL")
    if any(v < 0 for v in ri):
        flags.append("RECORDER_NUMERIC_REVERSAL")
    if any(v < 10 for v in ri):
        flags.append("RECORDER_SHORT_INTERARRIVAL_OBSERVED")
    if any(v >= 50 for v in ri):
        flags.append("RECORDER_LONG_INTERARRIVAL_OBSERVED")
    return {"count": len(frames), "zero_payload_count": sum(f["zero_payload"] for f in frames),
            "first_nonzero_ordinal": first,
            "zero_after_first_nonzero": sum(f["zero_payload"] for f in frames[first+1:]) if first is not None else 0,
            "header_intervals_ms": _summary(hi), "recorder_intervals_ms": _summary(ri),
            "recorder_burst_lt_10ms": sum(v < 10 for v in ri),
            "recorder_gap_ge_50ms": sum(v >= 50 for v in ri),
            "observation_flags": flags}


def numeric_header_join(left: list[dict], right: list[dict]) -> dict:
    """Pure numerical equality only; NOT physical sync or calibrated stereo pairing."""
    _seq(left, "left")
    _seq(right, "right")
    l, r = camera_diagnostics(left), camera_diagnostics(right)
    for lane in (left, right):
        stamps = [f["header_ns"] for f in lane]
        if len(stamps) != len(set(stamps)):
            raise ValueError("duplicate numeric header stamp")
    li = {f["header_ns"]: (i, f) for i, f in enumerate(left)}
    ri = {f["header_ns"]: (i, f) for i, f in enumerate(right)}
    matched = sorted(li.keys() & ri.keys())
    delta = [(ri[t][1]["recorder_ns"] - li[t][1]["recorder_ns"])/1e6 for t in matched]
    return {"left_count": l["count"], "right_count": r["count"],
            "numeric_equal_header_count": len(matched),
            "left_only_header_count": len(li.keys() - ri.keys()),
            "right_only_header_count": len(ri.keys() - li.keys()),
            "both_zero": sum(li[t][1]["zero_payload"] and ri[t][1]["zero_payload"] for t in matched),
            "both_nonzero": sum(not li[t][1]["zero_payload"] and not ri[t][1]["zero_payload"] for t in matched),
            "one_sided_zero": sum(li[t][1]["zero_payload"] != ri[t][1]["zero_payload"] for t in matched),
            "right_recorder_minus_left_ms": _summary(delta),
            "matched_arrival_delta_abs_gt_20ms": sum(abs(v) > 20 for v in delta),
            "interpretation": "NUMERIC_HEADER_EQUALITY_ONLY_NO_PHYSICAL_SYNCHRONIZATION_CLAIM"}


def imu_descriptive_diagnostics(samples: list[dict]) -> dict:
    """Vector magnitudes are descriptive. No gravity, calibration, or health claim."""
    _seq(samples, "imu_samples")
    norms = {"acceleration_norm_m_s2": [], "angular_speed_norm_rad_s": []}
    for sample in samples:
        if not isinstance(sample, dict) or set(sample) != {"accel_xyz", "gyro_xyz"}:
            raise ValueError("IMU sample schema invalid")
        for key, output in (("accel_xyz", "acceleration_norm_m_s2"), ("gyro_xyz", "angular_speed_norm_rad_s")):
            xyz = sample[key]
            if not isinstance(xyz, list) or len(xyz) != 3:
                raise ValueError("IMU requires 3-vector")
            vals = [_number(v, key) for v in xyz]
            magnitude = sqrt(sum(v*v for v in vals))
            if not isfinite(magnitude):
                raise ValueError("IMU norm overflow")
            norms[output].append(magnitude)
    return {name: _summary(values) for name, values in norms.items()} | {
        "interpretation": "DESCRIPTIVE_ONLY_NO_INDEPENDENT_HEALTH_LABEL"}


def lidar_structural_diagnostics(samples: list[dict]) -> dict:
    """Declared PointCloud2-like layout only; no geometry, model, or return validity."""
    _seq(samples, "lidar_samples")
    slots = 0
    layouts = Counter()
    for sample in samples:
        if not isinstance(sample, dict) or set(sample) != {"point_slots", "point_step_bytes", "field_count"}:
            raise ValueError("LiDAR layout schema invalid")
        p, step, fields = (sample[k] for k in ("point_slots", "point_step_bytes", "field_count"))
        if any(type(v) is not int for v in (p, step, fields)) or not (0 <= p <= MAX_POINTS) or not (1 <= step <= 4096) or not (1 <= fields <= MAX_FIELDS):
            raise ValueError("LiDAR reported structure out of bounds")
        slots += p
        if slots > MAX_ITEMS * MAX_POINTS:
            raise ValueError("LiDAR cumulative point bound")
        layouts[(step, fields)] += 1
    return {"message_count": len(samples), "reported_point_slots": slots,
            "layouts": [{"point_step_bytes": a, "field_count": b, "message_count": count}
                        for (a, b), count in sorted(layouts.items())],
            "interpretation": "REPORTED_STRUCTURE_ONLY_NOT_GEOMETRY_OR_LIDAR_HEALTH"}


def public_summary_only(camera_left: dict, camera_right: dict, joined: dict, imu: dict, lidar: dict) -> dict:
    """Explicit allowlist prevents raw frames, timestamps, and private payload escape."""
    return {"schema": "trust_robot_unlabelled_diagnostics_v1", "source": "OFFLINE_ENGINEERING",
            "physical_sensor_health_labels_accepted": 0,
            "real_factor_admission": "CLOSED", "physical_sync_qualified": False,
            "camera": {"left_count": camera_left["count"], "right_count": camera_right["count"],
                       "left_zero_payload_count": camera_left["zero_payload_count"],
                       "right_zero_payload_count": camera_right["zero_payload_count"],
                       "numeric_equal_header_count": joined["numeric_equal_header_count"],
                       "left_only_header_count": joined["left_only_header_count"],
                       "right_only_header_count": joined["right_only_header_count"],
                       "one_sided_zero": joined["one_sided_zero"],
                       "matched_arrival_delta_abs_gt_20ms": joined["matched_arrival_delta_abs_gt_20ms"]},
            "imu_sample_count": imu["angular_speed_norm_rad_s"]["count"],
            "lidar_message_count": lidar["message_count"],
            "lidar_reported_point_slots": lidar["reported_point_slots"],
            "caveat": "unlabelled observations; no physical fault, attack, stereo synchronization, or pose accuracy inference"}
