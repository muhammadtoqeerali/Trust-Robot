"""L10: offline GMO element-count and analytic ray audit.

Analytic intersections are model predictions, not actual
RTX per-emitter visibility or physical calibration.
No pose factors or health labels are generated.
"""

import hashlib
import json
import math
import re
import sys
from pathlib import Path

import numpy as np

STEPS = [51, 61, 71, 81, 91, 101]

COUNTS = {
    "original": [16, 16, 16, 16, 16, 4],
    "candidate": [16, 16, 16, 16, 16, 2],
}

SCENE_SHA = {
    "original":
        "950a84720a4304fd293cd5d5e8297d56b19dae178d127cf9db390d2da5e7a7ea",
    "candidate":
        "08d7f96b249e56cf53a53593b4f7e09cfe3c5e37b08b06a6361403438888c4b0",
}

L9_SHA = (
    "9309a3f9896144996366f7743ae9fca9bcacec827f5c6046d06d8ba13c280af7"
)


def sha(path):
    assert path.is_file() and not path.is_symlink(), str(path)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path):
    sha(path)
    return json.loads(path.read_text())


def canonical(value):
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ) + "\n"
    ).encode()


def scene_parameters(path, condition):
    assert sha(path) == SCENE_SHA[condition]

    text = path.read_text()

    assert 'metersPerUnit = 1' in text
    assert 'upAxis = "Z"' in text

    def array(key):
        match = re.search(
            re.escape(key) + r'\s*=\s*\[([^\]]+)\]',
            text,
        )
        assert match, key

        return np.array([
            float(v.strip())
            for v in match.group(1).split(",")
        ])

    def scalar(key):
        match = re.search(
            re.escape(key) + r'\s*=\s*([0-9.]+)',
            text,
        )
        assert match, key
        return float(match.group(1))

    def vec(block, key):
        match = re.search(
            re.escape(key) + r'\s*=\s*\(([^)]+)\)',
            block,
        )
        assert match, key

        return np.array([
            float(x.strip())
            for x in match.group(1).split(",")
        ])

    front = (
        text.split('def Cube "Front"', 1)[1]
        .split('def Cube "Left"', 1)[0]
    )

    center = vec(front, "xformOp:translate")

    match = re.search(
        r'\bdouble size\s*=\s*([0-9.]+)',
        front,
    )
    assert match

    side = float(match.group(1))

    assert np.allclose(center, [2.0, 0.0, 0.75])
    assert side == 1.5

    az = array("emitterState:s001:azimuthDeg")
    el = array("emitterState:s001:elevationDeg")

    assert az.shape == el.shape == (16,)
    assert np.isfinite(az).all()
    assert np.isfinite(el).all()

    near = scalar("omni:sensor:Core:nearRangeM")
    far = scalar("omni:sensor:Core:farRangeM")

    assert near == 0.2
    assert far == 10.0

    return (
        az,
        el,
        center - side / 2,
        center + side / 2,
        near,
        far,
    )


def ray_box_distance(origin, direction, lower, upper):
    near = 0.0
    far = float("inf")

    for axis in range(3):
        if abs(direction[axis]) < 1e-12:
            if (
                origin[axis] < lower[axis]
                or origin[axis] > upper[axis]
            ):
                return None

        else:
            a = (
                (lower[axis] - origin[axis])
                / direction[axis]
            )
            b = (
                (upper[axis] - origin[axis])
                / direction[axis]
            )

            near = max(near, min(a, b))
            far = min(far, max(a, b))

            if near > far:
                return None

    if not math.isfinite(near) or near <= 0:
        return None

    return float(near)


def geometry_selftest():
    low = np.array([1.0, -1.0, -1.0])
    high = np.array([2.0, 1.0, 1.0])
    origin = np.zeros(3)

    assert abs(
        ray_box_distance(
            origin,
            np.array([1.0, 0.0, 0.0]),
            low,
            high,
        ) - 1.0
    ) < 1e-12

    assert ray_box_distance(
        origin,
        np.array([-1.0, 0.0, 0.0]),
        low,
        high,
    ) is None

    assert ray_box_distance(
        origin,
        np.array([0.0, 1.0, 0.0]),
        low,
        high,
    ) is None

    print("ANALYTIC_RAY_BOX_SELFTEST=PASS")


def analytic(origin, az, el, lower, upper, near, far):
    intersections = []

    for a, e in zip(az, el):
        a = math.radians(float(a))
        e = math.radians(float(e))

        direction = np.array([
            math.cos(e) * math.cos(a),
            math.cos(e) * math.sin(a),
            math.sin(e),
        ])

        distance = ray_box_distance(
            origin,
            direction,
            lower,
            upper,
        )

        if (
            distance is not None
            and near <= distance <= far
        ):
            intersections.append(distance)
        else:
            intersections.append(None)

    valid = [
        d for d in intersections
        if d is not None
    ]

    return {
        "front_cube_ray_intersections_predicted":
            len(valid),

        "predicted_distances_m": [
            None if d is None else float(d)
            for d in intersections
        ],

        "minimum_predicted_distance_m":
            min(valid) if valid else None,

        "maximum_predicted_distance_m":
            max(valid) if valid else None,

        "model_near_range_m": near,
        "model_far_range_m": far,
    }


def snapshot_rows(logpath):
    sha(logpath)

    rows = {}

    with logpath.open(errors="replace") as stream:
        for line in stream:
            token = "PRE_GMO_SNAPSHOT "

            if token not in line:
                continue

            value = json.loads(
                line.split(token, 1)[1].strip()
            )

            step = int(value["step"])

            assert step not in rows
            rows[step] = value

    assert all(step in rows for step in STEPS)

    return rows


def read_run(run, condition):
    az, el, lower, upper, near, far = (
        scene_parameters(
            run / "multimodal_scene_v5.usda",
            condition,
        )
    )

    root = run / "multimodal_probe_results_v15"

    frames = read_json(
        root / "capture_index_v15.json"
    )

    summary = read_json(
        root / "summary_v1.json"
    )

    assert len(frames) == 6
    assert [r["step"] for r in frames] == STEPS
    assert summary["sequence_lidar_frames"] == 6

    pose_path = (
        root / "base_pose_series_v15.jsonl"
    )

    sha(pose_path)

    poses = [
        json.loads(line)
        for line in pose_path.read_text().splitlines()
        if line.strip()
    ]

    assert len(poses) == 130
    assert [
        p["step"] for p in poses
    ] == list(range(1, 131))

    results = []

    for index, (item, count) in enumerate(
        zip(frames, COUNTS[condition]),
        start=1,
    ):
        step = STEPS[index - 1]

        name = (
            f"frames_v15/lidar_{index:03d}.npy"
        )

        assert item["lidar_file"] == name
        assert item["lidar_points"] == count

        path = root / name
        recording_hash = sha(path)

        with path.open("rb") as stream:
            xyz = np.load(
                stream,
                allow_pickle=False,
            )

        assert xyz.shape == (count, 3)
        assert np.isfinite(xyz).all()

        raw_path = (
            run / "qualified_xyz_v1"
            / f"lidar_xyz_step_{step:03d}.npz"
        )

        raw_hash = sha(raw_path)

        with np.load(
            raw_path,
            allow_pickle=False,
        ) as data:
            assert np.array_equal(
                xyz,
                data["xyz"],
            )

            flags = np.asarray(
                data["flags"],
                dtype=np.uint64,
            )

            assert len(flags) == count
            assert np.all((flags & 64) != 0)

            frame_id = int(
                data["frame_id"][0]
            )

            timestamp = int(
                data["timestamp_ns"][0]
            )

            sensor_from_gmo = np.asarray(
                data["sensor_world_xyz"],
                dtype=float,
            )

        sensor_from_usd = np.asarray(
            poses[step - 1][
                "lidar_usd_world_position_m"
            ],
            dtype=float,
        )

        assert (
            sensor_from_gmo.shape
            == sensor_from_usd.shape
            == (3,)
        )

        # The acquisition recorder saved the preceding
        # iteration's lidar_xyz bookkeeping variable.
        # This is NOT a qualified GMO exposure pose.
        previous_usd = np.asarray(
            poses[step - 2][
                "lidar_usd_world_position_m"
            ],
            dtype=float,
        )

        assert previous_usd.shape == (3,)
        assert np.isfinite(sensor_from_gmo).all()
        assert np.isfinite(sensor_from_usd).all()

        assert np.allclose(
            sensor_from_gmo,
            previous_usd,
            rtol=0,
            atol=1e-8,
        ), "Unexpected recorder bookkeeping provenance"

        bookkeeping_lag_m = float(
            np.linalg.norm(
                sensor_from_gmo - sensor_from_usd
            )
        )

        assert item["lidar_rendering_time_raw"] == (
            "GMO_SENSOR_TIMESTAMP_NS:"
            + str(timestamp)
        )

        modeled = analytic(
            sensor_from_usd,
            az,
            el,
            lower,
            upper,
            near,
            far,
        )

        results.append({
            "step": step,
            "gmo_valid_points": count,
            "frame_id": frame_id,
            "timestamp_ns": timestamp,

            "usd_sensor_world_m":
                sensor_from_usd.tolist(),

            "saved_recorder_bookkeeping_world_m":
                sensor_from_gmo.tolist(),

            "saved_bookkeeping_matches_previous_usd_step":
                True,

            "bookkeeping_to_current_usd_offset_m":
                bookkeeping_lag_m,

            "bookkeeping_is_qualified_exposure_pose":
                False,

            "recording_sha256": recording_hash,
            "qualified_raw_sha256": raw_hash,

            **modeled,
        })

    assert [
        row["gmo_valid_points"]
        for row in results
    ] == COUNTS[condition]

    return results


def inspect_raw(run, recorded, logpath):
    snapshots = snapshot_rows(logpath)

    output = []

    for row in recorded:
        step = row["step"]
        metadata = snapshots[step]

        assert int(
            metadata["valid_elements"]
        ) == row["gmo_valid_points"]

        assert int(
            metadata["frame_id"]
        ) == row["frame_id"]

        assert int(
            metadata["timestamp_ns"]
        ) == row["timestamp_ns"]

        total = int(
            metadata["num_elements"]
        )

        assert (
            row["gmo_valid_points"]
            <= total <= 2048
        )

        path = (
            run / "pre_gmo_samples_v1"
            / f"gmo_pre_step_{step:03d}.npz"
        )

        digest = sha(path)

        with np.load(
            path,
            allow_pickle=False,
        ) as packet:

            assert int(
                packet["frame_id"][0]
            ) == row["frame_id"]

            assert int(
                packet["timestamp_ns"][0]
            ) == row["timestamp_ns"]

            assert all(
                len(packet[key]) == total
                for key in ("x", "y", "z")
            )

            ranges = {
                key: [
                    float(np.min(packet[key])),
                    float(np.max(packet[key])),
                ]
                for key in ("x", "y", "z")
            }

        output.append({
            "step": step,

            "gmo_raw_elements": total,

            "gmo_valid_elements":
                row["gmo_valid_points"],

            "gmo_invalid_or_unqualified_elements":
                total - row["gmo_valid_points"],

            "raw_spherical_ranges": ranges,

            "pre_gmo_file_sha256": digest,

            "reported_valid_flag_bit":
                metadata.get("valid_flag_bit"),

            "reported_coordinate_semantics":
                metadata.get("coordinate_semantics"),

            "capture_state":
                metadata.get("state"),
        })

        print(
            "L10_GMO_CAPTURE=",
            json.dumps({
                key: output[-1][key]
                for key in (
                    "step",
                    "gmo_raw_elements",
                    "gmo_valid_elements",
                    "gmo_invalid_or_unqualified_elements",
                    "capture_state",
                )
            }, sort_keys=True),
            flush=True,
        )

    return output


def main():
    assert len(sys.argv) == 6

    original, candidate, logpath, l9path, out = (
        map(Path, sys.argv[1:])
    )

    assert out.is_dir() and not out.is_symlink()
    assert sha(l9path) == L9_SHA

    l9 = read_json(l9path)

    assert l9["pose_factors_authorized"] == 0
    assert l9["sparse_final_pair_not_used"] is True

    geometry_selftest()

    def derive():
        original_rows = read_run(
            original,
            "original",
        )

        candidate_rows = read_run(
            candidate,
            "candidate",
        )

        captured = inspect_raw(
            candidate,
            candidate_rows,
            logpath,
        )

        return {
            "original": original_rows,
            "candidate": candidate_rows,
            "candidate_raw_gmo": captured,
        }

    first = derive()
    second = derive()

    assert canonical(first) == canonical(second)

    final = first["candidate_raw_gmo"][-1]

    assert final["gmo_valid_elements"] == 2

    model_hits = first["candidate"][-1][
        "front_cube_ray_intersections_predicted"
    ]

    report = {
        "schema":
            "TRUST_ROBOT_L10_SPARSE_ENDPOINT_TRIAGE_V1",

        "implementation_sha256":
            sha(Path(__file__)),

        "l9_report_sha256":
            sha(l9path),

        "candidate_log_sha256":
            sha(logpath),

        "deterministic_rederivation_identical":
            True,

        "analytic_model_is_not_rtx_emitter_observation":
            True,

        "raw_invalid_flags_per_emitter_preserved":
            False,

        "missing_return_cause_conclusively_identified":
            False,

        "candidate_last_frame_raw_element_count":
            final["gmo_raw_elements"],

        "candidate_last_frame_valid_element_count":
            2,

        "candidate_last_frame_model_ray_hits":
            model_hits,

        "candidate_last_frame_raw_minus_valid":
            final[
                "gmo_invalid_or_unqualified_elements"
            ],

        "independent_ground_truth_verified":
            False,

        "synchronization_verified":
            False,

        "health_labels_generated": 0,
        "pose_factors_authorized": 0,

        **first,
    }

    destination = (
        out / "l10_sparse_endpoint_diagnostic_v1.json"
    )

    with destination.open("x") as stream:
        json.dump(
            report,
            stream,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        stream.write("\n")

    for condition in ("original", "candidate"):
        for frame in first[condition]:
            print(
                "L10_MODEL_VS_CAPTURE=",
                json.dumps({
                    "condition": condition,
                    "step": frame["step"],

                    "model_front_cube_hits":
                        frame[
                            "front_cube_ray_intersections_predicted"
                        ],

                    "gmo_valid_points":
                        frame["gmo_valid_points"],

                    "minimum_modeled_ray_m":
                        frame["minimum_predicted_distance_m"],

                    "maximum_modeled_ray_m":
                        frame["maximum_predicted_distance_m"],
                }, sort_keys=True),
                flush=True,
            )

    print(
        "L10_LAST_FRAME_RAW_ELEMENTS=",
        final["gmo_raw_elements"],
    )

    print("L10_LAST_FRAME_VALID_ELEMENTS=2")

    print(
        "L10_LAST_FRAME_MODEL_INTERSECTIONS=",
        model_hits,
    )

    print("REPEATED_DERIVATION=PASS")
    print("SCIENTIFIC_POSE_FACTORS=0")
    print("L10_OFFLINE_TRIAGE=PASS")

    print(
        "L10_REPORT_SHA256=",
        sha(destination),
    )


if __name__ == "__main__":
    main()
