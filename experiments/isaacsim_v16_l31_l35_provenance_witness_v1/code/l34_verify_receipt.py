"""Independent L34 receipt verification and in-memory falsification."""

import argparse
import copy
import hashlib
import json
import time

from pathlib import Path, PurePosixPath

BASE = "2ac0a332bf6a5d749f5a75fe7d5a53572ea0e109"
C_SHA = "24e71f94c8acfc3aa59184c49a811d62f54fc93d90178bbebef6c8239912467b"
EV_SHA = "b28c333347ebb9c7262b636c355324b9abfa0b03beeb7c1af5a8b473a7144444"
M_SHA = "cd202b19dd86a1b00871c2ec55690cab30898b7120906d064390009363138d80"

def check(value, message):
    if not value:
        raise ValueError(message)

def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()

def sourcehash(root, relative):
    p = PurePosixPath(relative)

    check(
        not p.is_absolute()
        and ".." not in p.parts
        and p.parts[0] == "multimodal_probe_results_v15",
        "Unsafe source path",
    )

    path = root.joinpath(*p.parts)

    check(
        path.resolve(strict=True).is_relative_to(root.resolve()),
        "Source escaped root",
    )
    check(
        path.is_file() and not path.is_symlink(),
        "Invalid source file",
    )
    check(
        path.stat().st_size <= 20_000_000,
        "Oversized source",
    )

    return sha(path), path.stat().st_size

def main(a):
    raw = Path(a.raw).resolve(strict=True)

    challenge_path = Path(a.challenge)
    receipt_path = Path(a.receipt)
    event_path = Path(a.events)
    manifest_path = Path(a.manifest)
    contract_path = Path(a.contract)

    challenge = json.loads(challenge_path.read_text())
    receipt = json.loads(receipt_path.read_text())

    check(
        sha(event_path) == EV_SHA
        and sha(manifest_path) == M_SHA
        and sha(contract_path) == C_SHA,
        "Pinned inputs",
    )

    manifest = json.loads(manifest_path.read_text())
    events = [
        json.loads(line)
        for line in event_path.read_text().splitlines()
    ]

    check(len(events) == 272, "Event count")

    expected = {}

    for event in events:
        key = event["source_relative_path"]
        digest = event["source_file_sha256"]

        check(
            key not in expected or expected[key] == digest,
            "Conflicting source hashes",
        )
        expected[key] = digest

    for key, filename in (
        ("capture_index", "capture_index_v15.json"),
        ("summary", "summary_v1.json"),
        ("imu_series", "imu_v1.jsonl"),
        ("usd_pose_series", "base_pose_series_v15.jsonl"),
    ):
        relative = "multimodal_probe_results_v15/" + filename
        digest = manifest["runtime_file_sha256"][key]

        check(
            relative not in expected
            or expected[relative] == digest,
            "Manifest source conflict",
        )
        expected[relative] = digest

    check(len(expected) == 16, "Expected files")

    known = {
        relative: sourcehash(raw, relative)
        for relative in expected
    }

    check(
        all(
            known[key][0] == digest
            for key, digest in expected.items()
        ),
        "Raw source hashes",
    )

    check(
        challenge["schema"] == "TRUST_ROBOT_L34_LOCAL_CHALLENGE_V1",
        "Challenge schema",
    )
    check(
        challenge["purpose"] == "POST_CAPTURE_OFFLINE_DRYRUN",
        "Challenge purpose",
    )
    check(
        len(bytes.fromhex(challenge["nonce_hex"])) == 32,
        "Challenge nonce",
    )
    check(
        challenge["physical_sensor_attestation"] is False
        and challenge["l33_contract_sha256"] == C_SHA,
        "Challenge scientific flags",
    )

    challenge_sha = sha(challenge_path)

    def validate(r):
        check(
            r["schema"]
            == "TRUST_ROBOT_L34_POST_CAPTURE_WITNESS_RECEIPT_V1",
            "Receipt schema",
        )
        check(
            r["parent_commit"] == BASE
            and r["mode"] == "POST_CAPTURE_OFFLINE_DRYRUN",
            "Receipt mode",
        )
        check(
            r["challenge_file_sha256"] == challenge_sha,
            "Challenge binding",
        )
        check(
            r["challenge_nonce_sha256"]
            == hashlib.sha256(
                bytes.fromhex(challenge["nonce_hex"])
            ).hexdigest(),
            "Nonce binding",
        )
        check(
            r["l33_contract_sha256"] == C_SHA
            and r["l30_events_sha256"] == EV_SHA
            and r["l30_manifest_sha256"] == M_SHA,
            "Provenance lineage",
        )
        check(
            r["run_id"] == manifest["run_id"],
            "Run identity",
        )
        check(
            r["event_count"] == 272
            and r["event_counts"] == {
                "camera": 6,
                "lidar": 6,
                "imu": 130,
                "usd_pose": 130,
            },
            "Event counts",
        )
        check(
            r["file_count"] == len(r["files"]) == 16,
            "File counts",
        )
        check(
            [x["path"] for x in r["files"]]
            == sorted(expected),
            "Ledger paths",
        )

        for row in r["files"]:
            check(
                set(row) == {
                    "path", "sha256", "size_bytes"
                },
                "Ledger schema",
            )
            check(
                row["sha256"]
                == expected[row["path"]]
                == known[row["path"]][0],
                "Ledger hash",
            )
            check(
                row["size_bytes"]
                == known[row["path"]][1],
                "Ledger file size",
            )

        check(
            challenge["issued_monotonic_ns_unqualified"]
            <= r["witness_start_monotonic_ns_unqualified"]
            <= r["witness_end_monotonic_ns_unqualified"]
            <= time.monotonic_ns(),
            "Unqualified local timing order",
        )

        check(
            r["separate_process_untrusted_host"] is True
            and r["post_capture_only"] is True,
            "Witness role",
        )

        for flag in (
            "independent_source_authenticity_verified",
            "physical_exposure_synchronization_verified",
            "independent_6dof_reference_verified",
            "hardware_attestation_verified",
        ):
            check(r[flag] is False, "Scientific gate: " + flag)

        check(
            r["pose_factors_authorized"] == 0
            and r["health_labels_generated"] == 0,
            "Estimator/health admission",
        )

    validate(receipt)

    cases = [
        ("wrong_challenge", lambda r: r.update(
            challenge_file_sha256="0" * 64)),
        ("wrong_nonce", lambda r: r.update(
            challenge_nonce_sha256="0" * 64)),
        ("wrong_contract", lambda r: r.update(
            l33_contract_sha256="1" * 64)),
        ("wrong_event_sha", lambda r: r.update(
            l30_events_sha256="1" * 64)),
        ("wrong_manifest_sha", lambda r: r.update(
            l30_manifest_sha256="1" * 64)),
        ("wrong_run_id", lambda r: r.update(
            run_id="FORGED")),
        ("missing_file", lambda r: r["files"].pop()),
        ("duplicate_file", lambda r: r["files"].append(
            copy.deepcopy(r["files"][0]))),
        ("wrong_file_digest", lambda r: r["files"][0].update(
            sha256="0" * 64)),
        ("wrong_file_size", lambda r: r["files"][0].update(
            size_bytes=-1)),
        ("path_traversal", lambda r: r["files"][0].update(
            path="../escape")),
        ("late_challenge", lambda r: r.update(
            witness_start_monotonic_ns_unqualified=0)),
        ("forged_authenticity", lambda r: r.update(
            independent_source_authenticity_verified=True)),
        ("forged_physical_sync", lambda r: r.update(
            physical_exposure_synchronization_verified=True)),
        ("forged_reference", lambda r: r.update(
            independent_6dof_reference_verified=True)),
        ("forged_factor", lambda r: r.update(
            pose_factors_authorized=1)),
    ]

    rejected = []

    for name, change in cases:
        trial = copy.deepcopy(receipt)
        change(trial)

        try:
            validate(trial)
        except (ValueError, KeyError, IndexError, TypeError):
            rejected.append(name)
        else:
            raise RuntimeError(
                "Adversarial mutation accepted: " + name
            )

    check(len(rejected) == 16, "Challenge suite")

    report = {
        "schema": "TRUST_ROBOT_L34_LOCAL_WITNESS_VALIDATION_V1",
        "parent_git_commit": BASE,
        "challenge_sha256": challenge_sha,
        "receipt_sha256": sha(receipt_path),
        "l30_events_sha256": EV_SHA,
        "l30_manifest_sha256": M_SHA,
        "l33_contract_sha256": C_SHA,
        "witness_source_sha256": sha(
            Path(a.witness_script)
        ),
        "verifier_source_sha256": sha(
            Path(__file__)
        ),
        "source_files_rehashed": 16,
        "event_count": 272,
        "adversarial_mutations_rejected": rejected,
        "adversarial_mutations_rejected_count":
            len(rejected),
        "post_capture_only": True,
        "independent_source_authenticity_verified": False,
        "hardware_attestation_verified": False,
        "physical_exposure_synchronization_verified": False,
        "independent_6dof_reference_verified": False,
        "pose_factors_authorized": 0,
        "health_labels_generated": 0,
        "raw_files_modified": False,
        "new_simulator_capture_performed": False,
        "github_commit_performed": False,
    }

    with Path(a.output).open("x") as f:
        json.dump(report, f, indent=2, sort_keys=True)
        f.write("\n")

    print("L34_INDEPENDENT_16_FILE_REHASH=PASS")
    print("L34_NEGATIVE_CONTROLS=16_PASS")
    print("L34_WITNESS_VERIFICATION=PASS")

if __name__ == "__main__":
    p = argparse.ArgumentParser()

    for name in (
        "raw", "challenge", "receipt",
        "events", "manifest", "contract",
        "witness_script", "output",
    ):
        p.add_argument(
            "--" + name.replace("_", "-"),
            dest=name,
            required=True,
        )

    main(p.parse_args())
