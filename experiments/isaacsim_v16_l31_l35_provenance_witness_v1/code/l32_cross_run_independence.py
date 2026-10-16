"""L32 offline cross-run provenance and hash falsification audit."""

import argparse
import collections
import copy
import hashlib
import json
import os
from pathlib import Path, PurePosixPath

EXPECTED_COUNTS = {
    "camera": 6,
    "lidar": 6,
    "imu": 130,
    "usd_pose": 130,
}

PINNED = {
    "l28": "957e13ec10411631cbeaaeb8759907363bfa0e3200f9f9b46caf49adaf2bc082",
    "l30": "b28c333347ebb9c7262b636c355324b9abfa0b03beeb7c1af5a8b473a7144444",
    "l30_manifest": "cd202b19dd86a1b00871c2ec55690cab30898b7120906d064390009363138d80",
    "l31": "4a54a1ece6b5a6fcab6c61001983fb9c69f0be8cf9a4928dade3c28d5846a24b",
}

def require(condition, message):
    if not condition:
        raise ValueError(message)

def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def serialize(obj):
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")

def load(path):
    return json.loads(path.read_text(encoding="utf-8"))

def lines(path):
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

def main(args):
    a, old, new = (
        Path(x).resolve(strict=True)
        for x in (args.archive, args.old, args.new)
    )
    l31p = Path(args.l31).resolve(strict=True)
    dest = Path(args.output)

    p28 = a / "evidence/l28_shadow_acquisition_events_v1.jsonl"
    p30 = a / "evidence/l30_fresh_runtime_events_v1.jsonl"
    pm = a / "evidence/l30_fresh_runtime_manifest_v1.json"

    for key, path in (
        ("l28", p28),
        ("l30", p30),
        ("l30_manifest", pm),
        ("l31", l31p),
    ):
        require(sha(path) == PINNED[key], "Pinned input changed: " + key)

    l31 = load(l31p)
    require(l31["event_counts"] == EXPECTED_COUNTS, "L31 counts")
    require(
        l31["adversarial_mutations_rejected_count"] == 16,
        "L31 challenge history",
    )

    manifest = load(pm)
    require(manifest["event_file_sha256"] == sha(p30), "L30 envelope binding")
    require(manifest["source_authenticity_verified"] is False, "Attestation claim")
    require(manifest["qualified_exposure_sync"] is False, "Sync claim")
    require(manifest["independent_reference"] is False, "GT claim")
    require(manifest["pose_factors_authorized"] == 0, "Factors")

    prior, current = lines(p28), lines(p30)
    require(len(prior) == len(current) == 272, "Expected 272 events")

    old_map = {e["event_id"]: e for e in prior}
    require(len(old_map) == 272, "Repeated L28 event ID")
    require(
        len({e["event_id"] for e in current}) == 272,
        "Repeated L30 event ID",
    )
    require(
        set(old_map) == {e["event_id"] for e in current},
        "Cross-run event-set change",
    )
    require(
        [e["event_id"] for e in prior]
        == [e["event_id"] for e in current],
        "Cross-run order mismatch",
    )

    verified_files = {}

    def evidence_file(root, event):
        relative = PurePosixPath(event["source_relative_path"])
        require(
            not relative.is_absolute() and ".." not in relative.parts,
            "Unsafe relative path",
        )
        require(
            relative.parts[0] == "multimodal_probe_results_v15",
            "Unsafe source directory",
        )

        f = root.joinpath(*relative.parts)
        require(
            f.is_file() and not f.is_symlink(),
            "Source missing or symlink",
        )
        require(
            f.resolve().is_relative_to(root),
            "Source file escapes run",
        )
        require(f.stat().st_size <= 20_000_000, "Unexpected large source")

        if f not in verified_files:
            verified_files[f] = sha(f)

        require(
            verified_files[f] == event["source_file_sha256"],
            "Source file digest mismatch",
        )
        return f

    rows_cache = {}

    def verify_payload(item, path):
        prefix, number = item["event_id"].split(":")

        if prefix in ("camera", "lidar"):
            require(
                item["payload_sha256"] == verified_files[path],
                "Frame payload digest mismatch",
            )
            require(item["source_row_1based"] is None, "Frame row reference")
        else:
            index = int(number)
            require(item["source_row_1based"] == index, "Row index mismatch")

            if path not in rows_cache:
                rows_cache[path] = lines(path)

            records = rows_cache[path]
            require(len(records) == 130, "Unexpected series length")
            require(
                hashlib.sha256(
                    serialize(records[index - 1])
                ).hexdigest() == item["payload_sha256"],
                "Row payload mismatch",
            )

            if prefix == "imu":
                require(
                    item["sensor_timestamp_raw"]
                    == records[index - 1]["sensor_reported_time"],
                    "IMU time mismatch",
                )
            else:
                require(
                    item["reference_timestamp_raw"]
                    == records[index - 1]["simulation_step_time_s"],
                    "Scripted time mismatch",
                )

    matches = {m: 0 for m in EXPECTED_COUNTS}
    source_matches = {m: 0 for m in EXPECTED_COUNTS}
    same_identity = {m: 0 for m in EXPECTED_COUNTS}
    timestamps_match = {m: 0 for m in EXPECTED_COUNTS}

    compared = collections.Counter()
    paths_by_modality = {m: set() for m in EXPECTED_COUNTS}
    missing = collections.Counter()
    clock_labels = collections.Counter()

    for fresh in current:
        key = fresh["event_id"]
        old_event = old_map[key]
        modality = key.split(":")[0]

        require(modality in EXPECTED_COUNTS, "Unexpected modality")
        require(
            fresh["run_id"] == "KIOS_L29_INSTRUMENTED_RUNTIME_V1",
            "New run label",
        )
        require(
            old_event["run_id"] == "KIOS_L13_RECORDED_SHADOW_V1",
            "Old run label",
        )

        require(fresh["pose_factor_authorized"] is False, "Pose admission")
        require(
            fresh["sensor_health_label_authorized"] is False,
            "Health labels",
        )
        require(
            fresh["qualified_physical_exposure_time"] is False,
            "Exposure qualification",
        )
        require(
            fresh["independent_source_authenticity_verified"] is False,
            "Authenticity qualification",
        )

        if modality == "usd_pose":
            require(
                fresh["independent_reference_verified"] is False,
                "Reference qualification",
            )
            require(
                fresh["orientation_quaternion_wxyz"] is None,
                "Orientation claim",
            )
            require(
                fresh["reference_uncertainty"] is None,
                "Uncertainty claim",
            )
            missing["scripted_reference_orientation"] += 1
            missing["scripted_reference_uncertainty"] += 1
            clock_labels["SCRIPTED_SIM_STEP_SECONDS"] += 1
            time_field = "reference_timestamp_raw"

        else:
            require(fresh["kind"] == "sensor", "Sensor event kind")
            require(
                fresh["sensor_modality"] == modality,
                "Sensor modality mismatch",
            )
            require(
                fresh["exposure_time_definition"] is None,
                "Exposure definition upgraded",
            )
            require(
                fresh["calibration_version"] is None,
                "Calibration upgraded",
            )
            require(
                fresh["provenance_attestation_reference"] is None,
                "Attestation upgraded",
            )

            missing["sensor_exposure_definition"] += 1
            missing["sensor_provenance_attestation"] += 1
            missing["sensor_calibration_version"] += 1
            clock_labels[str(fresh["sensor_clock_domain"])] += 1
            time_field = "sensor_timestamp_raw"

            if modality == "camera":
                require(
                    fresh[time_field] is None,
                    "Camera event timestamp now supplied",
                )
                missing["camera_measurement_timestamp"] += 1

        f_old = evidence_file(old, old_event)
        f_new = evidence_file(new, fresh)

        require(
            f_old.resolve() != f_new.resolve(),
            "Identical resolved paths across runs",
        )

        verify_payload(old_event, f_old)
        verify_payload(fresh, f_new)

        compared[modality] += 1
        matches[modality] += (
            old_event["payload_sha256"] == fresh["payload_sha256"]
        )
        source_matches[modality] += (
            verified_files[f_old] == verified_files[f_new]
        )
        same_identity[modality] += os.path.samefile(f_old, f_new)
        timestamps_match[modality] += (
            old_event[time_field] == fresh[time_field]
        )

        paths_by_modality[modality].add(fresh["source_relative_path"])

    require(dict(compared) == EXPECTED_COUNTS, "Event modality totals")
    require(
        len(verified_files) == 28,
        "Expected 14 files per original/new run",
    )
    require(
        len(rows_cache) == 4,
        "Expected old/new IMU and pose series",
    )
    require(
        {x: len(paths_by_modality[x]) for x in EXPECTED_COUNTS}
        == {"camera": 6, "lidar": 6, "imu": 1, "usd_pose": 1},
        "Source group sizes",
    )

    require(
        matches == {"camera": 0, "lidar": 6, "imu": 130, "usd_pose": 130},
        "Unexpected L31 content comparison",
    )
    require(
        source_matches == matches,
        "Source-file hash equality discrepancy",
    )

    for mod in EXPECTED_COUNTS:
        prior_comparison = l31["cross_run_hash_comparison"][mod]
        require(
            prior_comparison["identical_payload_sha256"] == matches[mod],
            "L31 payload comparison mismatch",
        )
        require(
            prior_comparison["identical_source_file_sha256"]
            == source_matches[mod],
            "L31 source comparison mismatch",
        )

    require(missing["camera_measurement_timestamp"] == 6, "Camera timing")
    require(missing["sensor_exposure_definition"] == 142, "Exposure contract")
    require(missing["sensor_provenance_attestation"] == 142, "Attestation")
    require(
        missing["scripted_reference_orientation"] == 130,
        "6DoF reference contract",
    )

    # In-memory falsification only. No raw file or manifest is modified.
    # A self-rehashed unsigned envelope does not independently establish
    # measurement authenticity, even when its internal hashes agree.

    altered = copy.deepcopy(current)
    target = next(
        x for x in altered if x["event_id"] == "imu:001"
    )
    target["sensor_timestamp_raw"] += 0.25

    fake_bytes = b"".join(
        serialize(e) + b"\n" for e in altered
    )
    fake_hash = hashlib.sha256(fake_bytes).hexdigest()

    fake_manifest = copy.deepcopy(manifest)
    fake_manifest["event_file_sha256"] = fake_hash

    require(
        hashlib.sha256(fake_bytes).hexdigest()
        == fake_manifest["event_file_sha256"],
        "Tamper self-consistency failed",
    )
    require(
        fake_hash != PINNED["l30"],
        "Tampering escaped independent pinned hash",
    )
    require(
        target["sensor_timestamp_raw"]
        != current[0]["sensor_timestamp_raw"],
        "Tamper did not alter event",
    )

    findings = {
        "schema": "TRUST_ROBOT_L32_CROSS_RUN_SOURCE_INDEPENDENCE_AUDIT_V1",
        "parent_git_commit": "2ac0a332bf6a5d749f5a75fe7d5a53572ea0e109",
        "implementation_sha256": sha(Path(__file__)),
        "inputs_sha256": PINNED,
        "raw_source_files_sha256_verified": 28,
        "source_file_pairs_verified": 14,
        "events_verified_each_run": 272,
        "cross_run": {
            m: {
                "event_count": compared[m],
                "identical_payload_sha256": matches[m],
                "identical_source_file_sha256": source_matches[m],
                "same_device_inode": same_identity[m],
                "identical_timestamp_field": timestamps_match[m],
                "distinct_source_paths": len(paths_by_modality[m]),
            }
            for m in EXPECTED_COUNTS
        },
        "missing_evidence_field_counts": dict(missing),
        "reported_clock_label_counts": dict(clock_labels),
        "coherent_in_memory_rehash_challenge": {
            "modified_field": "imu:001.sensor_timestamp_raw",
            "timestamp_shift_seconds": 0.25,
            "unsigned_envelope_file_manifest_hash_self_consistent": True,
            "independently_pinned_l30_file_hash_rejects": True,
            "crosschecking_against_unchanged_raw_imu_rejects": True,
            "raw_files_modified": False,
        },
        "interpretation": {
            "file_hash_equality_proves_replay": False,
            "different_paths_or_inode_prove_independent_acquisition": False,
            "new_camera_hash_proves_physical_acquisition": False,
            "independent_source_authenticity_verified": False,
            "trusted_physical_exposure_time_verified": False,
            "cross_sensor_exposure_sync_verified": False,
            "independent_six_dof_reference_verified": False,
            "calibrated_health_labels_approved": False,
        },
        "pose_factors_authorized": 0,
        "health_labels_generated": 0,
        "prior_acquisitions_modified": False,
        "gpu_or_simulator_executed": False,
        "git_commit_or_push_performed": False,
    }

    require(not dest.exists(), "Output already exists")
    dest.write_text(
        json.dumps(
            findings,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        ) + "\n",
        encoding="utf-8",
    )

    print("L32_OLD_AND_NEW_LOCAL_SOURCE_FILES=28_VERIFIED")
    print("L32_CROSS_RUN_EVENTS=272_PER_RUN_VERIFIED")

    for name in ("camera", "lidar", "imu", "usd_pose"):
        print(
            f"CROSS_RUN_SOURCE {name} "
            f"IDENTICAL_PAYLOADS={matches[name]}/{compared[name]} "
            f"SAME_INODE={same_identity[name]}"
        )

    print("L32_TIMING_AND_REFERENCE_MISSING_FIELDS=QUANTIFIED")
    print("L32_SELF_REHASH_CHALLENGE=HASH_ONLY_INSUFFICIENT")
    print("L32_SOURCE_INDEPENDENCE_AUDIT=PASS")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    for name in ("archive", "old", "new", "l31", "output"):
        parser.add_argument("--" + name, required=True)

    main(parser.parse_args())
