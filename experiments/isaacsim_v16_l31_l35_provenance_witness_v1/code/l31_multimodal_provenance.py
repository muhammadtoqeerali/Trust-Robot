"""L31 offline audit of fresh synthetic multimodal event provenance.

No simulator execution, physical synchronization claims, estimator
factors, supervised health labels, or independent GT promotion.
"""

import argparse
import collections
import copy
import hashlib
import json
import math
import pathlib
import statistics

STEPS = (51, 61, 71, 81, 91, 101)
COUNTS = {"camera": 6, "lidar": 6, "imu": 130, "usd_pose": 130}

def need(condition, message):
    if not condition:
        raise ValueError(message)

def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def compact(obj):
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")

def load(path):
    return json.loads(path.read_text(encoding="utf-8"))

def rows(path):
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

def stats(values):
    need(bool(values), "Empty timing series")
    need(all(math.isfinite(float(x)) for x in values), "Non-finite time")
    return {
        "count": len(values),
        "min": min(values),
        "median": statistics.median(values),
        "max": max(values),
        "spread": max(values) - min(values),
    }

def main(args):
    archive = pathlib.Path(args.archive).resolve(strict=True)
    raw = pathlib.Path(args.raw).resolve(strict=True)
    out = pathlib.Path(args.output)

    root = raw / "multimodal_probe_results_v15"

    l28path = archive / "evidence/l28_shadow_acquisition_events_v1.jsonl"
    l30path = archive / "evidence/l30_fresh_runtime_events_v1.jsonl"
    manifest_path = archive / "evidence/l30_fresh_runtime_manifest_v1.json"
    report_path = archive / "evidence/l30_instrumented_acquisition_validation_v1.json"
    contract_path = archive / "evidence/l27_acquisition_contract_v1.json"

    pinned = {
        l28path: "957e13ec10411631cbeaaeb8759907363bfa0e3200f9f9b46caf49adaf2bc082",
        l30path: "b28c333347ebb9c7262b636c355324b9abfa0b03beeb7c1af5a8b473a7144444",
        manifest_path: "cd202b19dd86a1b00871c2ec55690cab30898b7120906d064390009363138d80",
        report_path: "d358563fa3e08523c2aa86fb42e8d39b51bd33ffc5fa1cf87ad348075a1adc67",
        contract_path: "7078da5e5c9ba0db5052f2ecb8d02544379b4d70cb319a3d7cab3e6a8fd52931",
    }

    for path, digest in pinned.items():
        need(path.is_file() and not path.is_symlink(), str(path))
        need(sha(path) == digest, "Pinned evidence mismatch")

    manifest = load(manifest_path)
    l30report = load(report_path)
    contract = load(contract_path)
    old = rows(l28path)
    fresh = rows(l30path)

    need(len(old) == len(fresh) == 272, "Event count")
    need(manifest["event_count"] == 272, "Manifest event count")
    need(manifest["event_file_sha256"] == sha(l30path), "Event binding")
    need(manifest["event_counts_by_modality"] == COUNTS, "Modality count")
    need(manifest["negative_controls_rejected"] == 6, "L30 controls")
    need(manifest["run_id"] == "KIOS_L29_INSTRUMENTED_RUNTIME_V1", "Run ID")
    need(manifest["capture_mode"] == "SIMULATOR_POST_CAPTURE_UNQUALIFIED", "Mode")

    need(l30report["event_count"] == 272, "L30 report count")
    need(l30report["instrumented_events_sha256"] == sha(l30path), "L30 events")
    need(l30report["instrumented_manifest_sha256"] == sha(manifest_path), "L30 manifest")
    need(l30report["pose_factors_authorized"] == 0, "Factor admission")
    need(l30report["health_labels_generated"] == 0, "Health labels")

    need(len(contract["scientific_requirements"]) == 11, "Evidence contract")
    need(all(
        x["currently_independently_qualified"] is False
        for x in contract["scientific_requirements"]
    ), "Unqualified requirements")
    need(len(contract["current_readiness_denials"]) == 4, "Gate count")
    need(all(
        x["decision"] == "DENIED_INSUFFICIENT_EVIDENCE"
        for x in contract["current_readiness_denials"]
    ), "Readiness denial")

    script_path = raw / "multimodal_probe_candidate_v15.py"
    scene_path = raw / "multimodal_scene_v5.usda"

    need(
        sha(script_path) == manifest["source_acquisition_script_sha256"],
        "Acquisition script mismatch",
    )
    need(sha(scene_path) == manifest["scene_sha256"], "Scene mismatch")

    raw_files = {
        "capture_index": root / "capture_index_v15.json",
        "summary": root / "summary_v1.json",
        "imu_series": root / "imu_v1.jsonl",
        "usd_pose_series": root / "base_pose_series_v15.jsonl",
    }
    for key, path in raw_files.items():
        need(path.is_file() and not path.is_symlink(), key)
        need(
            sha(path) == manifest["runtime_file_sha256"][key],
            "Runtime source mismatch: " + key,
        )

    index = load(raw_files["capture_index"])
    need(len(index) == 6, "Capture index length")
    need([x["step"] for x in index] == list(STEPS), "Capture steps")

    frame_report = {
        x["step"]: x for x in l30report["frame_provenance"]
    }
    need(set(frame_report) == set(STEPS), "Frame provenance")

    file_cache = {}
    row_cache = {}

    def source(event):
        relative = pathlib.PurePosixPath(event["source_relative_path"])
        need(not relative.is_absolute(), "Absolute sensor path")
        need(".." not in relative.parts, "Traversal")
        need(
            relative.parts[0] == "multimodal_probe_results_v15",
            "Source prefix",
        )
        path = raw.joinpath(*relative.parts)
        need(path.is_file() and not path.is_symlink(), "Missing sensor source")
        need(path.resolve().is_relative_to(root.resolve()), "Source escaped")
        need(path.stat().st_size <= 20_000_000, "Source too large")
        if path not in file_cache:
            file_cache[path] = sha(path)
        need(
            event["source_file_sha256"] == file_cache[path],
            "Event source-file hash mismatch",
        )
        return path

    expected = []
    for step in range(1, 131):
        expected.extend((f"imu:{step:03d}", f"usd_pose:{step:03d}"))
        if step in STEPS:
            number = STEPS.index(step) + 1
            expected.extend((
                f"camera:{number:03d}",
                f"lidar:{number:03d}",
            ))

    def validate(events):
        need(len(events) == 272, "Expected 272 events")
        need(
            [x["event_id"] for x in events] == expected,
            "Duplicate, omitted, reordered or mislabeled event",
        )
        count = collections.Counter()

        for item in events:
            event_id = item["event_id"]
            modality, number_text = event_id.split(":")
            number = int(number_text)

            need(
                item["run_id"] == "KIOS_L29_INSTRUMENTED_RUNTIME_V1",
                "Unexpected run identity",
            )
            need(item["pose_factor_authorized"] is False, "Pose factor")
            need(
                item["sensor_health_label_authorized"] is False,
                "Health label",
            )
            need(
                item["qualified_physical_exposure_time"] is False,
                "Exposure qualification",
            )
            need(
                item["independent_source_authenticity_verified"] is False,
                "Unverified authenticity promoted",
            )
            need(
                len(item["payload_sha256"]) == 64,
                "Missing payload digest",
            )

            path = source(item)
            count[modality] += 1

            if modality == "usd_pose":
                need(item["kind"] == "scripted_reference", "Pose kind")
                need(item["independent_reference_verified"] is False, "Reference claim")
                need(item["orientation_quaternion_wxyz"] is None, "Orientation claim")
                need(item["reference_uncertainty"] is None, "Reference uncertainty")
                need(item["reference_calibration_reference"] is None, "Reference calibration")
                need(item["reference_clock_domain"] == "SCRIPTED_SIM_STEP_SECONDS", "Reference clock")
                need(item["source_row_1based"] == number, "Pose row")

                if path not in row_cache:
                    row_cache[path] = rows(path)
                original = row_cache[path][number - 1]

                need(
                    hashlib.sha256(compact(original)).hexdigest()
                    == item["payload_sha256"],
                    "Pose row hash",
                )
                need(
                    item["position_xyz_m"] == original["usd_world_position_m"],
                    "Pose position",
                )
                need(
                    item["reference_timestamp_raw"]
                    == original["simulation_step_time_s"],
                    "Pose timestamp",
                )
                continue

            need(item["kind"] == "sensor", "Sensor event kind")
            need(item["sensor_modality"] == modality, "Sensor modality")
            need(item["sequence_number"] == number, "Sequence number")
            need(
                item["sensor_id"] == f"L29_RECORDED_{modality.upper()}",
                "Sensor identity",
            )
            need(item["exposure_time_definition"] is None, "Exposure semantics")
            need(item["calibration_version"] is None, "Calibration qualification")
            need(item["provenance_attestation_reference"] is None, "Attestation qualification")

            if modality == "imu":
                need(item["scripted_step"] == number, "IMU step")
                need(item["source_row_1based"] == number, "IMU row")
                need(item["sensor_clock_domain"] == "IMU_REPORTED_CLOCK_UNQUALIFIED", "IMU clock")
                if path not in row_cache:
                    row_cache[path] = rows(path)
                original = row_cache[path][number - 1]
                need(
                    hashlib.sha256(compact(original)).hexdigest()
                    == item["payload_sha256"],
                    "IMU payload hash",
                )
                need(
                    item["sensor_timestamp_raw"]
                    == original["sensor_reported_time"],
                    "IMU timestamp",
                )
                need(
                    item["scripted_read_step_time_s"]
                    == original["simulation_step_time_s"],
                    "IMU scripted time",
                )

            else:
                need(modality in ("camera", "lidar"), "Unexpected modality")
                step = STEPS[number - 1]
                need(item["scripted_step"] == step, "Frame step")
                need(item["source_row_1based"] is None, "Frame row")
                need(
                    item["payload_sha256"] == file_cache[path],
                    "Frame payload hash",
                )
                capture = index[number - 1]
                need(
                    item["scripted_read_step_time_s"]
                    == capture[f"{modality}_read_step_time_s"],
                    "Frame read time",
                )
                need(
                    item["source_relative_path"].endswith(
                        capture[f"{modality}_file"]
                    ),
                    "Frame filename mismatch",
                )

                if modality == "camera":
                    need(item["sensor_timestamp_raw"] is None, "Camera timestamp")
                    need(item["sensor_frame_id"] is None, "Camera frame ID")
                else:
                    frame = frame_report[step]
                    need(
                        item["payload_sha256"]
                        == frame["lidar_file_sha256"],
                        "LiDAR source provenance",
                    )
                    need(
                        item["sensor_timestamp_raw"]
                        == frame["gmo_timestamp_ns_unqualified"],
                        "LiDAR GMO timestamp",
                    )
                    need(
                        item["sensor_frame_id"]
                        == "GMO_ID:" + str(frame["gmo_frame_id"]),
                        "LiDAR frame identity",
                    )

        need(dict(count) == COUNTS, "Actual modality count")
        return dict(count)

    counts = validate(fresh)
    need(len(file_cache) == 14, "Expected 14 unique sensor-source files")

    old_index = {item["event_id"]: item for item in old}
    need(len(old_index) == 272, "L28 duplicate event IDs")
    need(set(old_index) == set(expected), "Cross-run identity coverage")

    cross_run = {}
    for modality in ("camera", "lidar", "imu", "usd_pose"):
        current = [x for x in fresh if x["event_id"].startswith(modality + ":")]
        previous = [old_index[x["event_id"]] for x in current]
        cross_run[modality] = {
            "compared": len(current),
            "identical_payload_sha256": sum(
                a["payload_sha256"] == b["payload_sha256"]
                for a, b in zip(current, previous)
            ),
            "identical_source_file_sha256": sum(
                a["source_file_sha256"] == b["source_file_sha256"]
                for a, b in zip(current, previous)
            ),
            "identical_reported_timestamp_field": sum(
                a.get("sensor_timestamp_raw", a.get("reference_timestamp_raw"))
                == b.get("sensor_timestamp_raw", b.get("reference_timestamp_raw"))
                for a, b in zip(current, previous)
            ),
        }

    imu = [x for x in fresh if x["event_id"].startswith("imu:")]
    lidar = [x for x in fresh if x["event_id"].startswith("lidar:")]
    camera = [x for x in fresh if x["event_id"].startswith("camera:")]
    pose = [x for x in fresh if x["event_id"].startswith("usd_pose:")]

    imu_offsets = [
        x["scripted_read_step_time_s"] - x["sensor_timestamp_raw"]
        for x in imu
    ]
    lidar_offsets = [
        x["sensor_timestamp_raw"] / 1e9
        - x["scripted_read_step_time_s"]
        for x in lidar
    ]
    frame_read_differences = [
        a["scripted_read_step_time_s"]
        - b["scripted_read_step_time_s"]
        for a, b in zip(camera, lidar)
    ]

    for series in (
        [x["sensor_timestamp_raw"] for x in imu],
        [x["sensor_timestamp_raw"] for x in lidar],
        [x["reference_timestamp_raw"] for x in pose],
    ):
        need(
            all(b > a for a, b in zip(series, series[1:])),
            "Nonmonotonic raw timestamp series",
        )

    need(
        all(x["orientation_quaternion_wxyz"] is None for x in pose),
        "Scripted reference orientation falsely supplied",
    )

    # In-memory challenge suite. No raw files are modified.
    challenges = [
        ("duplicate_event", lambda e: e[1].update(event_id=e[0]["event_id"])),
        ("truncated_sequence", lambda e: e.pop()),
        ("payload_hash_forgery", lambda e: e[0].update(payload_sha256="0"*64)),
        ("source_hash_forgery", lambda e: e[0].update(source_file_sha256="1"*64)),
        ("run_id_forgery", lambda e: e[0].update(run_id="UNTRUSTED_RUN")),
        ("sequence_replay", lambda e: e[0].update(sequence_number=999)),
        ("timestamp_mutation", lambda e: e[0].update(sensor_timestamp_raw=99.0)),
        ("forged_physical_exposure", lambda e: e[0].update(qualified_physical_exposure_time=True)),
        ("forged_authenticity", lambda e: e[0].update(independent_source_authenticity_verified=True)),
        ("forged_pose_factor", lambda e: e[0].update(pose_factor_authorized=True)),
        ("forged_health_label", lambda e: e[0].update(sensor_health_label_authorized=True)),
        ("forged_reference", lambda e: e[1].update(independent_reference_verified=True)),
        ("reordered_events", lambda e: e.__setitem__(slice(0,2), [e[1],e[0]])),
        ("imu_clock_relabel", lambda e: e[0].update(sensor_clock_domain="SCRIPTED_SIM_STEP_SECONDS")),
        ("pose_orientation_forgery", lambda e: e[1].update(orientation_quaternion_wxyz=[1,0,0,0])),
        ("source_row_replay", lambda e: e[0].update(source_row_1based=2)),
    ]

    rejected = []
    for name, mutate in challenges:
        trial = copy.deepcopy(fresh)
        mutate(trial)
        try:
            validate(trial)
        except (ValueError, KeyError, IndexError, TypeError):
            rejected.append(name)
        else:
            raise ValueError("Adversarial challenge accepted: " + name)

    need(len(rejected) == len(challenges), "Negative control suite incomplete")

    result = {
        "schema": "TRUST_ROBOT_L31_OFFLINE_MULTIMODAL_PROVENANCE_TIMING_V1",
        "implementation_sha256": sha(pathlib.Path(__file__)),
        "parent_git_commit": "2ac0a332bf6a5d749f5a75fe7d5a53572ea0e109",
        "input_sha256": {
            "l28_events": sha(l28path),
            "l30_events": sha(l30path),
            "l30_manifest": sha(manifest_path),
            "l30_report": sha(report_path),
            "l27_contract": sha(contract_path),
            "candidate_script": sha(script_path),
            "scene": sha(scene_path),
        },
        "capture_mode": manifest["capture_mode"],
        "event_counts": counts,
        "unique_raw_source_files_verified": len(file_cache),
        "source_payload_integrity": "VERIFIED_AGAINST_KIOS_LOCAL_FILES",
        "cross_run_hash_comparison": cross_run,
        "timing_diagnostics_unqualified": {
            "imu_scripted_read_minus_reported_seconds": stats(imu_offsets),
            "lidar_gmo_minus_scripted_read_seconds": stats(lidar_offsets),
            "camera_minus_lidar_scripted_read_seconds": stats(frame_read_differences),
            "imu_reported_timestamps_monotonic": True,
            "lidar_gmo_timestamps_monotonic": True,
            "scripted_pose_times_monotonic": True,
        },
        "adversarial_mutations_rejected": rejected,
        "adversarial_mutations_rejected_count": len(rejected),
        "limitations": {
            "matching_cross_run_hashes_prove_replay": False,
            "hashes_establish_independent_source_authenticity": False,
            "physical_exposure_synchronization_verified": False,
            "sensor_clock_alignment_uncertainty_measured": False,
            "extrinsics_independently_verified": False,
            "independent_six_dof_reference_verified": False,
            "scientific_ate_rpe_qualified": False,
            "health_detection_error_rates_validated": False,
        },
        "pose_factors_authorized": 0,
        "health_labels_generated": 0,
        "raw_recordings_modified": False,
        "new_simulator_acquisition_performed": False,
        "git_commit_performed": False,
    }

    need(not out.exists(), "Report already exists")
    out.write_text(
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )

    print("L31_RAW_SOURCE_HASHES=VERIFIED")
    print("L31_272_EVENTS_AND_PAYLOADS=VERIFIED")
    print("L31_ADVERSARIAL_NEGATIVE_CONTROLS=", len(rejected))
    for modality, comparison in cross_run.items():
        print(
            "CROSS_RUN",
            modality,
            "PAYLOAD_HASH_MATCHES=",
            comparison["identical_payload_sha256"],
            "OF",
            comparison["compared"],
            "SOURCE_HASH_MATCHES=",
            comparison["identical_source_file_sha256"],
        )
    print("L31_TIMING_DIAGNOSTICS=COMPUTED_UNQUALIFIED")
    print("L31_OFFLINE_AUDIT=PASS")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", required=True)
    parser.add_argument("--raw", required=True)
    parser.add_argument("--output", required=True)
    main(parser.parse_args())
