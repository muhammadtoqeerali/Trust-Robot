"""L24 offline content/clock/frame provenance and replay challenges.

An engineering consistency audit, not exposure synchronization,
source authenticity, physical fault labels, or approved pose factors.
"""

import copy
import hashlib
import io
import json
import sys
from pathlib import Path

import numpy as np

STEPS = [51, 61, 71, 81, 91, 101]

CASES = [
    "lidar_payload_replay_fresh_header",
    "lidar_payload_replay_old_header",
    "camera_payload_replay",
    "gmo_timestamp_rewind",
    "gmo_frame_id_rewind",
    "out_of_order_packet",
    "missing_last_packet",
    "read_step_clock_shift",
    "forged_reported_digest",
    "coherent_xyz_shift_rehashed",
    "plausible_new_header_relabel",
]


def sha(path):
    assert path.is_file() and not path.is_symlink(), str(path)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def load(path):
    sha(path)
    return json.loads(path.read_text())


def jsonl(path):
    sha(path)
    return [
        json.loads(line)
        for line in path.read_text().splitlines()
        if line.strip()
    ]


def canonical(data):
    return (
        json.dumps(
            data,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ) + "\n"
    ).encode()


def recording(run, l15, l14):
    root = run / "multimodal_probe_results_v15"

    capture = load(root / "capture_index_v15.json")
    summary = load(root / "summary_v1.json")
    poses = jsonl(root / "base_pose_series_v15.jsonl")
    imus = jsonl(root / "imu_v1.jsonl")

    proof = l15["scan_file_provenance"]

    assert len(capture) == len(proof) == 6
    assert len(poses) == len(imus) == 130

    assert [
        p["step"] for p in poses
    ] == list(range(1, 131))

    assert [
        p["step"] for p in imus
    ] == list(range(1, 131))

    assert summary["sequence_camera_frames"] == 6
    assert summary["sequence_lidar_frames"] == 6
    assert summary["usd_pose_samples"] == 130

    assert [
        int(x["step"]) for x in capture
    ] == STEPS

    assert [
        int(x["step"]) for x in proof
    ] == STEPS

    pose_times = [
        float(x["simulation_step_time_s"])
        for x in poses
    ]

    imu_times = [
        float(x["simulation_step_time_s"])
        for x in imus
    ]

    assert all(np.isfinite(pose_times))

    assert all(
        a < b
        for a, b in zip(
            pose_times,
            pose_times[1:],
        )
    )

    assert pose_times == imu_times

    packets = []

    for i, (step, row, p) in enumerate(
        zip(STEPS, capture, proof),
        start=1,
    ):
        assert int(row["lidar_points"]) == p["count"] == 16

        assert row["lidar_file"] == (
            f"frames_v15/lidar_{i:03d}.npy"
        )

        lidar_path = root / row["lidar_file"]
        camera_path = root / row["camera_file"]

        raw_path = (
            run / "qualified_xyz_v1"
            / f"lidar_xyz_step_{step:03d}.npz"
        )

        cloud_hash = sha(lidar_path)
        camera_hash = sha(camera_path)

        assert cloud_hash == p["cloud_sha256"]
        assert sha(raw_path) == p["qualified_xyz_sha256"]

        with lidar_path.open("rb") as stream:
            cloud = np.load(
                stream,
                allow_pickle=False,
            )

        with camera_path.open("rb") as stream:
            camera = np.load(
                stream,
                allow_pickle=False,
            )

        assert cloud.shape == (16, 3)
        assert np.isfinite(cloud).all()
        assert camera.shape == (120, 160, 4)

        with np.load(
            raw_path,
            allow_pickle=False,
        ) as raw:
            assert np.array_equal(raw["xyz"], cloud)

            flags = raw["flags"].astype(np.uint64)

            assert np.all((flags & 64) != 0)

            frame_id = int(raw["frame_id"][0])
            stamp = int(raw["timestamp_ns"][0])

        assert frame_id == p["gmo_frame_id"]

        assert stamp == p[
            "gmo_timestamp_ns_unqualified"
        ]

        assert row["lidar_rendering_time_raw"] == (
            f"GMO_SENSOR_TIMESTAMP_NS:{stamp}"
        )

        step_time = pose_times[step - 1]

        assert abs(
            float(row["camera_read_step_time_s"])
            - step_time
        ) < 1e-5

        assert abs(
            float(row["lidar_read_step_time_s"])
            - step_time
        ) < 1e-5

        packets.append({
            "step": step,

            "gmo_frame_id": frame_id,
            "gmo_stamp_ns": stamp,

            "lidar_payload_sha256": cloud_hash,
            "lidar_claimed_sha256": cloud_hash,

            "camera_payload_sha256": camera_hash,
            "camera_claimed_sha256": camera_hash,

            "lidar_read_step_time_s":
                float(row["lidar_read_step_time_s"]),

            "camera_read_step_time_s":
                float(row["camera_read_step_time_s"]),

            "pose_step_time_s": step_time,

            "imu_step_time_s":
                imu_times[step - 1],
        })

    assert all(
        a["gmo_frame_id"] < b["gmo_frame_id"]
        for a, b in zip(packets, packets[1:])
    )

    assert all(
        a["gmo_stamp_ns"] < b["gmo_stamp_ns"]
        for a, b in zip(packets, packets[1:])
    )

    timeline = {
        int(x["step"]): x
        for x in l14["timeline_steps88_110"]
    }

    for step, count in (
        (91, 16),
        (92, 0),
        (93, 16),
        (101, 16),
        (102, 0),
        (103, 16),
    ):
        assert int(
            timeline[step]["shifted_target_raw"]
        ) == count

    context = {
        "selected_capture_steps": STEPS,

        "recorded_imu_rows": 130,
        "recorded_usd_pose_rows": 130,

        "baseline_lidar_unique_payload_count":
            len({
                p["lidar_payload_sha256"]
                for p in packets
            }),

        "observed_zero_raw_return_steps": [92, 102],

        "zero_return_mechanism_verified": False,

        "verified_cross_sensor_exposure_sync": False,

        "recorded_frame_id_gaps_allowed": True,

        "camera_payload_hashes_self_baselined_not_independently_attested":
            True,

        "gmo_timestamps_unqualified_as_physical_exposure_times":
            True,

        "capture_index_sha256":
            sha(root / "capture_index_v15.json"),

        "imu_jsonl_sha256":
            sha(root / "imu_v1.jsonl"),

        "pose_jsonl_sha256":
            sha(root / "base_pose_series_v15.jsonl"),
    }

    return packets, context


def check(packets, baseline, pinned):
    issues = set()

    if len(packets) != 6:
        issues.add("MISSING_OR_EXTRA_CAPTURE")

    for i, row in enumerate(packets):
        expected = (
            baseline[i]
            if i < len(baseline)
            else None
        )

        if (
            expected is None
            or row["step"] != expected["step"]
        ):
            issues.add("CAPTURE_STEP_SEQUENCE_MISMATCH")

        if row["lidar_payload_sha256"] != (
            row["lidar_claimed_sha256"]
        ):
            issues.add("LIDAR_REPORTED_DIGEST_MISMATCH")

        if row["camera_payload_sha256"] != (
            row["camera_claimed_sha256"]
        ):
            issues.add("CAMERA_REPORTED_DIGEST_MISMATCH")

        if abs(
            row["lidar_read_step_time_s"]
            - row["pose_step_time_s"]
        ) > 1e-5:
            issues.add(
                "LIDAR_READ_VS_SCRIPTED_STEP_TIME_MISMATCH"
            )

        if abs(
            row["camera_read_step_time_s"]
            - row["pose_step_time_s"]
        ) > 1e-5:
            issues.add(
                "CAMERA_READ_VS_SCRIPTED_STEP_TIME_MISMATCH"
            )

        if abs(
            row["imu_step_time_s"]
            - row["pose_step_time_s"]
        ) > 1e-5:
            issues.add(
                "IMU_VS_SCRIPTED_STEP_TIME_MISMATCH"
            )

        if pinned and expected is not None:
            if row["lidar_payload_sha256"] != (
                expected["lidar_payload_sha256"]
            ):
                issues.add(
                    "PINNED_LIDAR_FILE_HASH_MISMATCH"
                )

            if row["camera_payload_sha256"] != (
                expected["camera_payload_sha256"]
            ):
                issues.add(
                    "LOCAL_BASELINE_CAMERA_FILE_HASH_MISMATCH"
                )

            if row["gmo_frame_id"] != (
                expected["gmo_frame_id"]
            ):
                issues.add(
                    "PINNED_GMO_FRAME_ID_MISMATCH"
                )

            if row["gmo_stamp_ns"] != (
                expected["gmo_stamp_ns"]
            ):
                issues.add(
                    "PINNED_GMO_TIMESTAMP_MISMATCH"
                )

        if i > 0:
            before = packets[i - 1]

            if row["step"] <= before["step"]:
                issues.add(
                    "NONINCREASING_CAPTURE_STEP"
                )

            if row["gmo_frame_id"] <= (
                before["gmo_frame_id"]
            ):
                issues.add(
                    "NONINCREASING_GMO_FRAME_ID"
                )

            if row["gmo_stamp_ns"] <= (
                before["gmo_stamp_ns"]
            ):
                issues.add(
                    "NONINCREASING_GMO_TIMESTAMP"
                )

            if row["lidar_payload_sha256"] == (
                before["lidar_payload_sha256"]
            ):
                issues.add(
                    "CONSECUTIVE_IDENTICAL_LIDAR_CONTENT_REVIEW"
                )

    return {
        "decision": (
            "REVIEW_REQUIRED"
            if issues
            else "NOT_FLAGGED_DIAGNOSTIC_ONLY"
        ),

        "trigger_codes": sorted(issues),

        "pose_factor_authorized": False,
    }


def mutate(label, baseline, original_last_cloud):
    packets = copy.deepcopy(baseline)

    last = packets[-1]
    prev = packets[-2]

    if label == "lidar_payload_replay_fresh_header":
        last["lidar_payload_sha256"] = (
            prev["lidar_payload_sha256"]
        )

        last["lidar_claimed_sha256"] = (
            prev["lidar_payload_sha256"]
        )

    elif label == "lidar_payload_replay_old_header":
        last["lidar_payload_sha256"] = (
            prev["lidar_payload_sha256"]
        )

        last["lidar_claimed_sha256"] = (
            prev["lidar_payload_sha256"]
        )

        last["gmo_frame_id"] = prev["gmo_frame_id"]
        last["gmo_stamp_ns"] = prev["gmo_stamp_ns"]

    elif label == "camera_payload_replay":
        last["camera_payload_sha256"] = (
            prev["camera_payload_sha256"]
        )

        last["camera_claimed_sha256"] = (
            prev["camera_payload_sha256"]
        )

    elif label == "gmo_timestamp_rewind":
        last["gmo_stamp_ns"] = prev["gmo_stamp_ns"]

    elif label == "gmo_frame_id_rewind":
        last["gmo_frame_id"] = (
            prev["gmo_frame_id"]
        )

    elif label == "out_of_order_packet":
        packets[-2], packets[-1] = (
            packets[-1],
            packets[-2],
        )

    elif label == "missing_last_packet":
        packets.pop()

    elif label == "read_step_clock_shift":
        last["lidar_read_step_time_s"] += 0.1

    elif label == "forged_reported_digest":
        last["lidar_claimed_sha256"] = "0" * 64

    elif label == "coherent_xyz_shift_rehashed":
        assert original_last_cloud.shape == (16, 3)

        altered = original_last_cloud.copy()
        altered[:, 0] += 0.080

        buffer = io.BytesIO()

        np.save(
            buffer,
            altered,
            allow_pickle=False,
        )

        digest = sha_bytes(buffer.getvalue())

        assert digest != last["lidar_payload_sha256"]

        last["lidar_payload_sha256"] = digest
        last["lidar_claimed_sha256"] = digest

    elif label == "plausible_new_header_relabel":
        last["gmo_frame_id"] += 3
        last["gmo_stamp_ns"] += 1_000_000

    else:
        raise ValueError(label)

    return packets


def derive(baseline, last_cloud):
    clean_pinned = check(
        baseline,
        baseline,
        pinned=True,
    )

    clean_sequence = check(
        baseline,
        baseline,
        pinned=False,
    )

    assert clean_pinned["trigger_codes"] == []
    assert clean_sequence["trigger_codes"] == []

    cases = []

    for name in CASES:
        altered = mutate(
            name,
            baseline,
            last_cloud,
        )

        pinned = check(
            altered,
            baseline,
            pinned=True,
        )

        sequence = check(
            altered,
            baseline,
            pinned=False,
        )

        assert pinned["decision"] == (
            "REVIEW_REQUIRED"
        ), name

        if name in (
            "coherent_xyz_shift_rehashed",
            "plausible_new_header_relabel",
        ):
            assert sequence["decision"] == (
                "NOT_FLAGGED_DIAGNOSTIC_ONLY"
            ), name

        if name in (
            "lidar_payload_replay_fresh_header",
            "lidar_payload_replay_old_header",
            "gmo_timestamp_rewind",
            "gmo_frame_id_rewind",
            "out_of_order_packet",
            "missing_last_packet",
            "read_step_clock_shift",
            "forged_reported_digest",
        ):
            assert sequence["decision"] == (
                "REVIEW_REQUIRED"
            ), name

        cases.append({
            "challenge": name,

            "pinned_recording_check": pinned,

            "incoming_sequence_check": sequence,

            "all_corruptions_in_memory": True,

            "physical_sensor_failure_label": False,
        })

    return {
        "challenges": cases,
        "challenge_count": len(cases),

        "pinned_review_count": sum(
            case["pinned_recording_check"]["decision"]
            == "REVIEW_REQUIRED"
            for case in cases
        ),

        "incoming_sequence_review_count": sum(
            case["incoming_sequence_check"]["decision"]
            == "REVIEW_REQUIRED"
            for case in cases
        ),

        "clean_pinned_baseline": clean_pinned,
        "clean_incoming_sequence_baseline":
            clean_sequence,

        "coherent_rehashed_geometry_unflagged_without_anchor":
            True,

        "plausible_relabel_unflagged_without_anchor":
            True,
    }


def main():
    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--run",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--l15",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--l14",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--out",
        type=Path,
        required=True,
    )

    args = parser.parse_args()

    assert args.run.is_dir()
    assert not args.run.is_symlink()

    assert args.out.is_dir()
    assert not args.out.is_symlink()

    l15 = load(args.l15)
    l14 = load(args.l14)

    assert l15["upstream_l14_sha256"] == (
        sha(args.l14)
    )

    assert (
        l15["pose_factors_authorized"]
        == l14["pose_factors_authorized"]
        == 0
    )

    assert l14["shifted_selected_valid_counts"] == (
        [16] * 6
    )

    baseline, context = recording(
        args.run,
        l15,
        l14,
    )

    last_path = (
        args.run
        / "multimodal_probe_results_v15"
        / "frames_v15/lidar_006.npy"
    )

    with last_path.open("rb") as stream:
        last_cloud = np.load(
            stream,
            allow_pickle=False,
        )

    first = derive(
        baseline,
        last_cloud,
    )

    second = derive(
        baseline,
        last_cloud,
    )

    assert canonical(first) == canonical(second)

    report = {
        "schema":
            "TRUST_ROBOT_L24_OFFLINE_SENSOR_FRESHNESS_PROVENANCE_DIAGNOSTIC_V1",

        "implementation_sha256":
            sha(Path(__file__)),

        "l15_report_sha256":
            sha(args.l15),

        "l14_report_sha256":
            sha(args.l14),

        "baseline_context": context,

        "independent_source_authenticity_verified":
            False,

        "camera_hashes_independently_attested":
            False,

        "physical_exposure_sync_verified":
            False,

        "physical_ground_truth_verified":
            False,

        "proven_sensor_failure_detection":
            False,

        "note_identical_content_may_be_legitimate_in_static_scene":
            True,

        "repeated_derivation_identical": True,

        "original_recordings_modified": False,

        "health_labels_generated": 0,
        "pose_factors_authorized": 0,

        **first,
    }

    target = (
        args.out
        / "l24_freshness_provenance_diagnostic_v1.json"
    )

    with target.open("x") as stream:
        json.dump(
            report,
            stream,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )

        stream.write("\n")

    for case in first["challenges"]:
        print(
            "L24_CHALLENGE=",
            json.dumps({
                "name": case["challenge"],

                "pinned":
                    case["pinned_recording_check"]["decision"],

                "pinned_triggers":
                    case["pinned_recording_check"]["trigger_codes"],

                "sequence":
                    case["incoming_sequence_check"]["decision"],

                "sequence_triggers":
                    case["incoming_sequence_check"]["trigger_codes"],
            }, sort_keys=True),
            flush=True,
        )

    print("L24_FROZEN_BASELINE=PASS")
    print("L24_REPEATED_DERIVATION=PASS")

    print(
        "L24_PINNED_REVIEW_COUNT=",
        first["pinned_review_count"],
    )

    print(
        "L24_SEQUENCE_REVIEW_COUNT=",
        first["incoming_sequence_review_count"],
    )

    print(
        "L24_REPORT_SHA256=",
        sha(target),
    )

    print("L24_OFFLINE_AUDIT=PASS")


if __name__ == "__main__":
    main()
