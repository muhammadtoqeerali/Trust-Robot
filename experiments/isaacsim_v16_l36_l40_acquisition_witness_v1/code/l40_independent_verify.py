"""Independent L40 database, outbox and receipt verification."""

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path


def sha(path):
    return hashlib.sha256(
        Path(path).read_bytes()
    ).hexdigest()


def need(ok, message):
    if not ok:
        raise ValueError(message)


def main(args):
    report = json.loads(
        Path(args.report).read_text(encoding="utf-8")
    )

    root = Path(args.output) / "primary"
    database = root / "registry.sqlite"
    folder = root / "receipts"

    need(
        report["schema"]
        == "TRUST_ROBOT_L40_CRASH_SAFE_OUTBOX_OFFLINE_VALIDATION_V1",
        "Report schema",
    )

    need(
        report["protocol_source_sha256"]
        == sha(args.protocol),
        "Protocol source hash",
    )
    need(
        report["orchestrator_source_sha256"]
        == sha(args.orchestrator),
        "Orchestrator source hash",
    )
    need(
        report["primary_registry_sha256"]
        == sha(database),
        "Database hash",
    )

    need(
        report["input_sha256"]
        == {
            key: sha(getattr(args, key))
            for key in (
                "candidate", "contract", "fixture"
            )
        },
        "Frozen input hashes",
    )

    con = sqlite3.connect(
        "file:" + str(database.resolve()) + "?mode=ro",
        uri=True,
    )

    try:
        con.execute("PRAGMA query_only=ON")

        need(
            con.execute(
                "PRAGMA quick_check"
            ).fetchone()[0] == "ok",
            "SQLite integrity",
        )

        sessions = con.execute(
            """
            SELECT session_id,nonce_hash,state
            FROM sessions
            """
        ).fetchall()

        rows = con.execute(
            """
            SELECT stage,payload,digest,published
            FROM outbox ORDER BY stage
            """
        ).fetchall()

    finally:
        con.close()

    need(
        len(sessions) == 1
        and sessions[0][2] == "SEALED",
        "Final session state",
    )

    need(
        len(rows) == 3
        and [x[0] for x in rows] == [0, 1, 2],
        "Outbox stages",
    )

    names = [
        "challenge_v1.json",
        "admission_v1.json",
        "seal_v1.json",
    ]

    for (
        stage, payload, digest, published
    ), name in zip(rows, names):
        path = folder / name

        need(
            path.is_file() and not path.is_symlink(),
            "Missing receipt",
        )
        need(
            published == 1
            and digest == sha(path)
            and payload == path.read_bytes(),
            "Receipt byte equality",
        )

        obj = json.loads(payload)

        need(
            obj["session_id"] == sessions[0][0]
            and obj["nonce_hash"] == sessions[0][1],
            "Receipt session binding",
        )

        need(
            obj["new_sensor_measurements"] == 0
            and obj["simulator_launch_authorized"] is False
            and obj["pose_factors_authorized"] == 0,
            "Scientific restrictions",
        )

        need(
            report["primary_receipts_sha256"][name]
            == digest,
            "Report receipt binding",
        )

    need(
        len(report["subprocess_checks"]) == 10,
        "Process coverage",
    )
    need(
        report["recovery_count"]
        == len(report["recovery_cases"]) == 2,
        "Recovery count",
    )
    need(
        report["faults_rejected_count"]
        == len(report["quarantined_faults"]) == 7,
        "Fault count",
    )

    need(
        report["nonce_replay_rejected"] is True
        and report["nonce_state_final"] == "SEALED",
        "Replay protection",
    )

    for flag in (
        "automatic_nonce_reset",
        "replaced_existing_tampered_receipts",
        "actual_power_failure_tested",
        "physical_source_authenticity_verified",
        "hardware_attestation_verified",
        "physical_sync_verified",
        "live_simulator_launch_authorized",
        "git_commit_or_push_performed",
    ):
        need(
            report[flag] is False,
            "Unsupported claim: " + flag,
        )

    need(
        report["sensor_measurements_acquired"] == 0
        and report["pose_factors_authorized"] == 0
        and report["health_labels_generated"] == 0,
        "Scientific admission",
    )

    result = {
        "schema":
            "TRUST_ROBOT_L40_INDEPENDENT_VALIDATION_V1",
        "assessment_sha256": sha(args.report),
        "protocol_source_sha256": sha(args.protocol),
        "orchestrator_source_sha256": sha(args.orchestrator),
        "verifier_source_sha256": sha(__file__),
        "verified_outbox_rows": 3,
        "verified_recoveries": 2,
        "verified_denied_faults": 7,
        "baseline_state": "SEALED",
        "scientific_pose_factors": 0,
        "live_gpu_launch": False,
        "physical_durability_qualified": False,
    }

    destination = Path(args.validation)

    with destination.open("x", encoding="utf-8") as f:
        json.dump(
            result, f, indent=2, sort_keys=True
        )
        f.write("\n")

    print("L40_INDEPENDENT_SQLITE_RECEIPTS=PASS")
    print("L40_INDEPENDENT_VALIDATION=PASS")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    for name in (
        "report", "protocol", "orchestrator",
        "candidate", "contract", "fixture",
        "output", "validation"
    ):
        parser.add_argument("--" + name, required=True)

    main(parser.parse_args())
