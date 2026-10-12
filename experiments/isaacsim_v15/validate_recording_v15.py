#!/usr/bin/env python3
"""Offline V15 recording structural and USD-motion consistency checks."""
import ast
import hashlib
import json
import math
import struct
import sys
from pathlib import Path

def load_npy(p):
    assert p.is_file() and not p.is_symlink()
    with p.open("rb") as f:
        assert f.read(6) == b"\x93NUMPY"
        major, minor = f.read(2)
        assert major in (1, 2, 3)
        length = struct.unpack(
            "<H" if major == 1 else "<I",
            f.read(2 if major == 1 else 4)
        )[0]
        header = ast.literal_eval(f.read(length).decode("latin1"))
        payload = f.read()
    assert header["fortran_order"] is False
    return tuple(header["shape"]), header["descr"], payload

def main():
    assert len(sys.argv) == 2, "usage: validate_recording_v15.py RESULT_DIR"
    out = Path(sys.argv[1])
    summary = json.loads((out / "summary_v1.json").read_text())
    index = json.loads((out / "capture_index_v15.json").read_text())
    poses = [
        json.loads(x)
        for x in (out / "base_pose_series_v15.jsonl").read_text().splitlines()
        if x.strip()
    ]
    imu = [
        json.loads(x)
        for x in (out / "imu_v1.jsonl").read_text().splitlines()
        if x.strip()
    ]
    assert summary["data_origin"] == "SYNTHETIC"
    assert summary["lidar_mounted_to_robot"] is True
    assert summary["usd_mount_motion_consistency_verified"] is True
    assert summary["physical_motion_equivalence_verified"] is False
    assert summary["independent_ground_truth_verified"] is False
    assert len(index) == 6 and len(poses) == 90 and len(imu) == 90
    assert [p["step"] for p in poses] == list(range(1, 91))

    cameras, scans = [], []
    for i, record in enumerate(index, 1):
        assert record["step"] == 21 + 10 * i
        cp = out / f"frames_v15/camera_{i:03d}.npy"
        lp = out / f"frames_v15/lidar_{i:03d}.npy"
        assert record["camera_file"] == cp.relative_to(out).as_posix()
        assert record["lidar_file"] == lp.relative_to(out).as_posix()

        shape, dtype, rgba = load_npy(cp)
        assert shape == (120, 160, 4) and dtype in ("|u1", "<u1")
        assert len(rgba) == 76800
        visible = sum(
            any(rgba[j:j+3]) for j in range(0, len(rgba), 4)
        ) / 19200
        assert visible >= 0.01
        cameras.append(hashlib.sha256(rgba).hexdigest())

        shape, dtype, cloud = load_npy(lp)
        assert len(shape) == 2 and shape[1] == 3 and shape[0] > 0
        assert dtype in ("<f4", "=f4")
        assert len(cloud) == shape[0] * 12
        assert record["lidar_points"] == shape[0]
        assert all(
            math.isfinite(v)
            for point in struct.iter_unpack("<fff", cloud)
            for v in point
        )
        scans.append(hashlib.sha256(cloud).hexdigest())

    base = [p["usd_world_position_m"] for p in poses]
    lidar = [p["lidar_usd_world_position_m"] for p in poses]
    offsets = [p["base_to_lidar_usd_offset_m"] for p in poses]
    assert all(
        len(v) == 3 and all(math.isfinite(x) for x in v)
        for v in base + lidar + offsets
    )

    robot_dx = base[-1][0] - base[0][0]
    lidar_dx = lidar[-1][0] - lidar[0][0]
    drift = max(math.dist(v, offsets[0]) for v in offsets)

    assert 0.20 <= robot_dx <= 0.37
    assert abs(robot_dx - lidar_dx) < 0.01
    assert drift < 0.001
    assert abs(robot_dx - summary["kinematic_robot_dx_m"]) < 1e-5
    assert abs(lidar_dx - summary["lidar_usd_dx_m"]) < 1e-5
    assert abs(drift - summary["relative_offset_max_drift_m"]) < 1e-5

    print("CAMERA_FRAMES=", len(cameras))
    print("LIDAR_SCANS=", len(scans))
    print("IMU_RECORDS=", len(imu))
    print("POSE_SAMPLES=", len(poses))
    print("ROBOT_DX_M=", round(robot_dx, 6))
    print("LIDAR_DX_M=", round(lidar_dx, 6))
    print("OFFSET_DRIFT_M=", round(drift, 9))
    print("V15_OFFLINE_RECORDING_VALIDATION=PASS")

if __name__ == "__main__":
    main()
