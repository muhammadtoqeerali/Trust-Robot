"""L34 post-capture witness: frozen-file hashing in a separate process.

Independent hardware provenance and physical synchronization
are not established by this userspace witness.
"""

import argparse
import collections
import hashlib
import json
import os
import stat
import time

from pathlib import Path, PurePosixPath

BASE = "2ac0a332bf6a5d749f5a75fe7d5a53572ea0e109"
C_SHA = "24e71f94c8acfc3aa59184c49a811d62f54fc93d90178bbebef6c8239912467b"
EV_SHA = "b28c333347ebb9c7262b636c355324b9abfa0b03beeb7c1af5a8b473a7144444"
M_SHA = "cd202b19dd86a1b00871c2ec55690cab30898b7120906d064390009363138d80"

def need(value, message):
    if not value:
        raise ValueError(message)

def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1048576), b""):
            h.update(block)
    return h.hexdigest()

def guarded_hash(root, relative):
    rel = PurePosixPath(relative)

    need(
        not rel.is_absolute()
        and ".." not in rel.parts
        and len(rel.parts) > 1,
        "Unsafe relative file",
    )
    need(
        rel.parts[0] == "multimodal_probe_results_v15",
        "Unexpected source root",
    )

    path = root.joinpath(*rel.parts)

    need(
        path.resolve(strict=True).is_relative_to(root.resolve()),
        "Source path escaped capture directory",
    )

    parent = root
    for component in rel.parts[:-1]:
        parent = parent / component
        need(
            parent.is_dir() and not parent.is_symlink(),
            "Symlink source parent",
        )

    fd = os.open(
        path,
        os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
    )

    with os.fdopen(fd, "rb") as f:
        before = os.fstat(f.fileno())

        need(
            stat.S_ISREG(before.st_mode)
            and before.st_size <= 20_000_000,
            "Unexpected source file",
        )

        h = hashlib.sha256()

        for block in iter(lambda: f.read(1048576), b""):
            h.update(block)

        after = os.fstat(f.fileno())

    fields_before = (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
        before.st_ctime_ns,
    )
    fields_after = (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
        after.st_ctime_ns,
    )

    need(
        fields_before == fields_after,
        "Source metadata changed during reading",
    )

    return {
        "path": relative,
        "sha256": h.hexdigest(),
        "size_bytes": before.st_size,
    }

def main(a):
    start_ns = time.monotonic_ns()

    raw = Path(a.raw).resolve(strict=True)
    challenge_file = Path(a.challenge)
    challenge = json.loads(challenge_file.read_text())

    need(
        challenge["schema"]
        == "TRUST_ROBOT_L34_LOCAL_CHALLENGE_V1",
        "Challenge schema",
    )
    need(
        challenge["purpose"] == "POST_CAPTURE_OFFLINE_DRYRUN",
        "Challenge mode",
    )
    need(
        len(bytes.fromhex(challenge["nonce_hex"])) == 32,
        "Challenge entropy length",
    )
    need(
        challenge["physical_sensor_attestation"] is False,
        "False attestation claim",
    )
    need(
        challenge["l33_contract_sha256"] == C_SHA,
        "Contract lineage",
    )
    need(
        challenge["issued_monotonic_ns_unqualified"] <= start_ns,
        "Challenge not issued before witness",
    )

    events_path = Path(a.events)
    manifest_path = Path(a.manifest)
    contract_path = Path(a.contract)

    need(
        sha(events_path) == EV_SHA
        and sha(manifest_path) == M_SHA
        and sha(contract_path) == C_SHA,
        "Pinned input hashes",
    )

    manifest = json.loads(manifest_path.read_text())
    events = [
        json.loads(line)
        for line in events_path.read_text().splitlines()
    ]

    need(
        manifest["event_file_sha256"] == EV_SHA,
        "Event-manifest binding",
    )
    need(
        manifest["event_count"] == 272
        and manifest["negative_controls_rejected"] == 6,
        "L30 evidence count",
    )
    need(
        manifest["source_authenticity_verified"] is False,
        "Unqualified authenticity promoted",
    )
    need(
        len(events) == 272
        and len({e["event_id"] for e in events}) == 272,
        "Event IDs",
    )

    counts = collections.Counter()
    sources = {}

    for event in events:
        modality = event["event_id"].split(":")[0]
        counts[modality] += 1

        need(
            event["independent_source_authenticity_verified"]
            is False,
            "Authenticity flag",
        )
        need(
            event["qualified_physical_exposure_time"]
            is False,
            "Exposure flag",
        )
        need(
            event["pose_factor_authorized"] is False
            and event["sensor_health_label_authorized"] is False,
            "Estimator or health admission",
        )

        relative = event["source_relative_path"]
        digest = event["source_file_sha256"]

        need(
            relative not in sources
            or sources[relative] == digest,
            "Conflicting source digests",
        )
        sources[relative] = digest

        if modality in ("camera", "lidar"):
            need(
                event["payload_sha256"] == digest,
                "Frame payload-file mismatch",
            )

    need(
        dict(counts) == {
            "camera": 6,
            "lidar": 6,
            "imu": 130,
            "usd_pose": 130,
        },
        "Modality counts",
    )
    need(len(sources) == 14, "Event source-file count")

    for key, filename in (
        ("capture_index", "capture_index_v15.json"),
        ("summary", "summary_v1.json"),
        ("imu_series", "imu_v1.jsonl"),
        ("usd_pose_series", "base_pose_series_v15.jsonl"),
    ):
        relative = (
            "multimodal_probe_results_v15/" + filename
        )
        digest = manifest["runtime_file_sha256"][key]

        need(
            relative not in sources
            or sources[relative] == digest,
            "Runtime manifest conflict",
        )
        sources[relative] = digest

    need(len(sources) == 16, "Witness file count")

    ledger = [
        guarded_hash(raw, relative)
        for relative in sorted(sources)
    ]

    need(
        all(
            row["sha256"] == sources[row["path"]]
            for row in ledger
        ),
        "On-disk hashes disagree with frozen provenance",
    )

    receipt = {
        "schema":
            "TRUST_ROBOT_L34_POST_CAPTURE_WITNESS_RECEIPT_V1",
        "parent_commit": BASE,
        "mode": "POST_CAPTURE_OFFLINE_DRYRUN",
        "challenge_file_sha256": sha(challenge_file),
        "challenge_nonce_sha256": hashlib.sha256(
            bytes.fromhex(challenge["nonce_hex"])
        ).hexdigest(),
        "l33_contract_sha256": C_SHA,
        "l30_events_sha256": EV_SHA,
        "l30_manifest_sha256": M_SHA,
        "run_id": manifest["run_id"],
        "event_count": len(events),
        "event_counts": dict(counts),
        "files": ledger,
        "file_count": len(ledger),
        "witness_start_monotonic_ns_unqualified": start_ns,
        "witness_end_monotonic_ns_unqualified":
            time.monotonic_ns(),
        "separate_process_untrusted_host": True,
        "post_capture_only": True,
        "independent_source_authenticity_verified": False,
        "physical_exposure_synchronization_verified": False,
        "independent_6dof_reference_verified": False,
        "hardware_attestation_verified": False,
        "pose_factors_authorized": 0,
        "health_labels_generated": 0,
    }

    with Path(a.output).open("x") as f:
        json.dump(receipt, f, indent=2, sort_keys=True)
        f.write("\n")

    print("L34_WITNESS_16_SOURCE_FILES=PASS")
    print("L34_WITNESS_RECEIPT=CREATED")

if __name__ == "__main__":
    p = argparse.ArgumentParser()

    for name in (
        "raw", "challenge", "events",
        "manifest", "contract", "output",
    ):
        p.add_argument("--" + name, required=True)

    main(p.parse_args())
