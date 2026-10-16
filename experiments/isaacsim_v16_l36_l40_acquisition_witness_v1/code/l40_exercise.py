"""Exercise L40 outbox transitions in isolated child processes."""

import argparse
import hashlib
import json
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path


def need(value, message):
    if not value:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(
        Path(path).read_bytes()
    ).hexdigest()


def backup(source, destination):
    original = sqlite3.connect(
        "file:" + str(source.resolve()) + "?mode=ro",
        uri=True,
    )

    try:
        copy = sqlite3.connect(destination)
        try:
            original.backup(copy)
        finally:
            copy.close()
    finally:
        original.close()


def main(args):
    root = Path(args.output)
    need(not root.exists(), "OUTPUT_EXISTS")
    root.mkdir(mode=0o700)

    primary = root / "primary"
    primary.mkdir(mode=0o700)

    receipts = primary / "receipts"
    receipts.mkdir(mode=0o700)

    db = primary / "registry.sqlite"

    protocol = Path(args.protocol).resolve(strict=True)

    executable = [
        sys.executable,
        "-B",
        str(protocol),
    ]

    inputs = [
        "--candidate", args.candidate,
        "--contract", args.contract,
        "--fixture", args.fixture,
    ]

    def call(action, database, folder, expect_success=True):
        result = subprocess.run(
            executable
            + [
                action,
                "--db", str(database),
                "--receipts", str(folder),
            ]
            + inputs,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if expect_success:
            need(
                result.returncode == 0,
                "UNEXPECTED_FAILURE_"
                + action + ":" + result.stdout
                + result.stderr,
            )
        else:
            need(
                result.returncode == 3
                and "L40_FAIL_CLOSED=" in result.stdout,
                "INVALID_OPERATION_NOT_DENIED_"
                + action + ":" + result.stdout
                + result.stderr,
            )

        return result.stdout.strip()

    checks = []

    checks.append((
        "issue_before_publication",
        call("issue", db, receipts),
    ))

    need(
        not any(receipts.iterdir()),
        "ISSUER_PUBLISHED_EARLY",
    )

    checks.append((
        "challenge_recovery",
        call("publish", db, receipts),
    ))

    checks.append((
        "admission_before_publication",
        call("admit", db, receipts),
    ))

    need(
        not (receipts / "admission_v1.json").exists(),
        "ADMISSION_PUBLISHED_EARLY",
    )

    checks.append((
        "restart_replay_denied",
        call("admit", db, receipts, False),
    ))

    checks.append((
        "admission_recovery",
        call("publish", db, receipts),
    ))

    checks.append((
        "seal_before_publication",
        call("seal", db, receipts),
    ))

    need(
        not (receipts / "seal_v1.json").exists(),
        "SEAL_PUBLISHED_EARLY",
    )

    checks.append((
        "seal_recovery",
        call("publish", db, receipts),
    ))

    checks.append((
        "second_seal_denied",
        call("seal", db, receipts, False),
    ))

    checks.append((
        "idempotent_publication",
        call("publish", db, receipts),
    ))

    checks.append((
        "sealed_final_state",
        call("status", db, receipts),
    ))

    def mutate_db(path, operation):
        connection = sqlite3.connect(path)
        try:
            operation(connection)
        finally:
            connection.close()

    def mark_pending(connection, stage):
        connection.execute(
            "UPDATE outbox SET published=0 WHERE stage=?",
            (stage,),
        )
        connection.commit()

    def copy_primary(name):
        destination = root / name
        destination.mkdir(mode=0o700)

        folder = destination / "receipts"
        shutil.copytree(receipts, folder)

        cloned_db = destination / "registry.sqlite"
        backup(db, cloned_db)

        return cloned_db, folder

    # Interrupted between successful file rename and
    # the database publication-flag update.
    def rename_before_mark(database, folder):
        mutate_db(
            database,
            lambda c: mark_pending(c, 2),
        )

    # Committed receipt BLOB exists, file publication absent.
    def missing_pending_file(database, folder):
        (folder / "seal_v1.json").unlink()
        mutate_db(
            database,
            lambda c: mark_pending(c, 2),
        )

    recoveries = []

    for name, mutation in (
        ("rename_before_mark", rename_before_mark),
        ("pending_file_missing", missing_pending_file),
    ):
        copied_db, copied_folder = copy_primary(name)
        mutation(copied_db, copied_folder)

        outcome = call(
            "publish", copied_db, copied_folder
        )

        need(
            call("status", copied_db, copied_folder)
            == "L40_FINAL_STATE=SEALED",
            "RECOVERY_STATE",
        )

        recoveries.append((name, outcome))

    def corrupt_receipt(database, folder):
        (folder / "seal_v1.json").write_bytes(
            b"CORRUPTED\n"
        )

    def remove_published(database, folder):
        (folder / "seal_v1.json").unlink()

    def corrupt_outbox(database, folder):
        def edit(connection):
            connection.execute(
                "UPDATE outbox SET payload=? WHERE stage=2",
                (b"BAD\n",),
            )
            connection.commit()
        mutate_db(database, edit)

    def remove_outbox(database, folder):
        def edit(connection):
            connection.execute(
                "DELETE FROM outbox WHERE stage=2"
            )
            connection.commit()
        mutate_db(database, edit)

    def wrong_nonce(database, folder):
        def edit(connection):
            connection.execute(
                "UPDATE sessions SET nonce_hash=?",
                ("0" * 64,),
            )
            connection.commit()
        mutate_db(database, edit)

    def wrong_stage(database, folder):
        def edit(connection):
            connection.execute(
                "UPDATE sessions SET state='ADMITTED'"
            )
            connection.commit()
        mutate_db(database, edit)

    def pending_tampered(database, folder):
        mutate_db(
            database,
            lambda c: mark_pending(c, 1),
        )
        (folder / "admission_v1.json").write_bytes(
            b"WRONG_RECEIPT\n"
        )

    faults = [
        ("tampered_receipt", corrupt_receipt),
        ("missing_published_receipt", remove_published),
        ("corrupt_outbox_blob", corrupt_outbox),
        ("missing_outbox_entry", remove_outbox),
        ("wrong_registry_nonce", wrong_nonce),
        ("state_outbox_mismatch", wrong_stage),
        ("pending_but_tampered", pending_tampered),
    ]

    denied = []

    for name, mutation in faults:
        copied_db, copied_folder = copy_primary(name)
        mutation(copied_db, copied_folder)

        denied.append((
            name,
            call(
                "publish",
                copied_db,
                copied_folder,
                False,
            ),
        ))

    receipt_hashes = {
        name: sha(receipts / name)
        for name in (
            "challenge_v1.json",
            "admission_v1.json",
            "seal_v1.json",
        )
    }

    report = {
        "schema":
            "TRUST_ROBOT_L40_CRASH_SAFE_OUTBOX_OFFLINE_VALIDATION_V1",
        "parent_commit":
            "0b542e8644f3c4b98ed92c0f83a7c82a4635ae52",
        "protocol_source_sha256": sha(protocol),
        "orchestrator_source_sha256": sha(__file__),
        "input_sha256": {
            "candidate": sha(args.candidate),
            "contract": sha(args.contract),
            "fixture": sha(args.fixture),
        },
        "primary_registry_sha256": sha(db),
        "primary_receipts_sha256": receipt_hashes,
        "subprocess_checks": checks,
        "recovery_cases": recoveries,
        "quarantined_faults": denied,
        "recovery_count": len(recoveries),
        "faults_rejected_count": len(denied),
        "nonce_replay_rejected": True,
        "nonce_state_final": "SEALED",
        "automatic_nonce_reset": False,
        "missing_receipts_recovered_only_from_committed_outbox":
            True,
        "replaced_existing_tampered_receipts": False,
        "actual_power_failure_tested": False,
        "physical_source_authenticity_verified": False,
        "hardware_attestation_verified": False,
        "physical_sync_verified": False,
        "sensor_measurements_acquired": 0,
        "live_simulator_launch_authorized": False,
        "pose_factors_authorized": 0,
        "health_labels_generated": 0,
        "git_commit_or_push_performed": False,
    }

    destination = Path(args.report)
    need(not destination.exists(), "REPORT_EXISTS")

    destination.write_text(
        json.dumps(
            report, indent=2, sort_keys=True
        ) + "\n",
        encoding="utf-8",
    )

    print("L40_TRANSACTIONAL_OUTBOX=PASS")
    print("L40_PROCESS_RESTART_REPLAY=REJECTED")
    print(
        "L40_MISSING_RECEIPTS_RECOVERED="
        + str(len(recoveries))
    )
    print(
        "L40_CORRUPTION_FAULTS_DENIED="
        + str(len(denied))
    )
    print("L40_OFFLINE_RECOVERY_TEST=PASS")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    for name in (
        "protocol",
        "candidate",
        "contract",
        "fixture",
        "output",
        "report",
    ):
        parser.add_argument("--" + name, required=True)

    main(parser.parse_args())
