"""L44 isolated synthetic capture and fault injection harness."""

import argparse
import copy
import hashlib
import json
import shutil
import sqlite3
import subprocess
import sys

from pathlib import Path
import l44_capture_boundary as b


def need(ok, message):
    if not ok:
        raise AssertionError(message)


def sha(path):
    return hashlib.sha256(
        Path(path).read_bytes()
    ).hexdigest()


def dump(path, obj):
    Path(path).write_text(
        json.dumps(obj, sort_keys=True, indent=2) + "\n"
    )


def backup(source, destination):
    origin = sqlite3.connect(
        f"file:{Path(source).resolve()}?mode=ro",
        uri=True,
    )

    try:
        target = sqlite3.connect(destination)

        try:
            origin.backup(target)
        finally:
            target.close()

    finally:
        origin.close()


def run(core, action, db, receipt=None, expect_fail=False, n=0):
    args = [
        sys.executable,
        "-B",
        str(core),
        action,
        str(db),
        str(n),
    ]

    if receipt is not None:
        args.append(str(receipt))

    result = subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=25,
    )

    need(
        (
            result.returncode != 0
            if expect_fail
            else result.returncode == 0
        ),
        f"{action} unexpected return: "
        f"{result.returncode}: {result.stderr}",
    )

    return result.stdout.strip()


def mutate_event(base, k):
    rows = copy.deepcopy(base)

    at = (0, 6, 12)[k // 12]

    field = (
        "schema",
        "mode",
        "session_id",
        "nonce_sha256",
        "l43_manifest_sha256",
        "candidate_sha256",
        "sensor",
        "counter",
        "event_index",
        "read_tick_ns_untrusted",
        "payload_sha256",
        "event_digest",
    )[k % 12]

    row = rows[at]

    row[field] = (
        "FORGED"
        if isinstance(row[field], str)
        else -1
    )

    return rows


def main(args):
    root = Path(args.out)

    need(
        not root.exists(),
        "SCENARIOS_COLLISION",
    )

    root.mkdir(mode=0o700)

    core = Path(args.core)

    partial = (0, 1, 3, 5, 6, 12, 100)
    records = []

    for i, n in enumerate((142,) + partial):
        folder = root / f"case_{i:02d}"
        folder.mkdir(mode=0o700)

        db = folder / "session.sqlite"
        receipt = folder / "decision.json"

        if i == 0:
            # Complete session uses fresh processes.
            run(core, "create", db)
            run(core, "capture", db, n=n)
            run(core, "finalize", db)

        else:
            # Incomplete cases use the same verified module.
            b.create(db)
            b.capture(db, n)
            b.finalize(db)

        need(
            not receipt.exists(),
            "PUBLISHED_TOO_EARLY",
        )

        connection = sqlite3.connect(db)

        try:
            before = connection.execute(
                "SELECT state FROM session"
            ).fetchone()[0]

            blob, digest, published = connection.execute(
                "SELECT payload,digest,published FROM outbox"
            ).fetchone()

            need(
                published == 0 and b.h(blob) == digest,
                "NOT_ATOMIC_OUTBOX",
            )

        finally:
            connection.close()

        if i == 0:
            # Simulated crash window between SQLite commit
            # and receipt file publication.
            run(core, "publish", db, receipt)
            run(core, "publish", db, receipt)

            observed = run(
                core,
                "verify",
                db,
                receipt,
            )

            run(
                core,
                "finalize",
                db,
                expect_fail=True,
            )

        else:
            b.publish(db, receipt)
            observed = b.verify(db, receipt)

            try:
                b.finalize(db)
            except ValueError:
                pass
            else:
                raise AssertionError(
                    "PARTIAL_SESSION_REENTRY_ALLOWED"
                )

        expected = (
            "COMPLETE_SYNTHETIC"
            if i == 0
            else "REVIEW_REQUIRED"
        )

        need(
            expected == before == observed,
            "INCORRECT_COMPLETENESS_DECISION",
        )

        records.append({
            "case": i,
            "synthetic_event_count": n,
            "decision": observed,
            "database_sha256": sha(db),
            "receipt_sha256": sha(receipt),
        })

    main_db = root / "case_00/session.sqlite"
    main_receipt = root / "case_00/decision.json"

    with sqlite3.connect(main_db) as connection:
        sid, nonce, _ = connection.execute(
            "SELECT id,nonce,state FROM session"
        ).fetchone()

    full = b.events_for(sid, nonce)

    mutation_cases = []

    for i in range(36):
        result, _ = b.assess(
            mutate_event(full, i),
            sid,
            nonce,
        )

        need(
            result == "QUARANTINED",
            f"MUTATION_ACCEPTED_{i}",
        )

        mutation_cases.append(f"mutation_{i:02d}")

    def db_mutation(db, kind):
        connection = sqlite3.connect(db)

        try:
            if kind == "event_tamper":
                connection.execute(
                    "UPDATE events SET payload=? WHERE pos=0",
                    ("BAD",),
                )

            if kind == "outbox_blob":
                connection.execute(
                    "UPDATE outbox SET payload=?",
                    (b"BAD",),
                )

            if kind == "outbox_hash":
                connection.execute(
                    "UPDATE outbox SET digest=?",
                    ("0" * 64,),
                )

            if kind == "outbox_missing":
                connection.execute(
                    "DELETE FROM outbox"
                )

            if kind == "nonce_changed":
                connection.execute(
                    "UPDATE session SET nonce=?",
                    ("1" * 64,),
                )

            if kind == "wrong_state":
                connection.execute(
                    "UPDATE session SET state='RECORDING'"
                )

            connection.commit()

        finally:
            connection.close()

    fault_kinds = [
        "event_tamper",
        "outbox_blob",
        "outbox_hash",
        "outbox_missing",
        "nonce_changed",
        "wrong_state",
        "missing_receipt",
        "tampered_receipt",
    ]

    faults = []

    for kind in fault_kinds:
        folder = root / ("fault_" + kind)
        folder.mkdir(mode=0o700)

        db = folder / "session.sqlite"
        receipt = folder / "decision.json"

        backup(main_db, db)
        shutil.copyfile(main_receipt, receipt)

        if kind in fault_kinds[:6]:
            db_mutation(db, kind)

        if kind == "missing_receipt":
            receipt.unlink()

        if kind == "tampered_receipt":
            receipt.write_bytes(b"FORGED\n")

        try:
            b.verify(db, receipt)

        except (
            ValueError,
            sqlite3.DatabaseError,
            KeyError,
            TypeError,
        ):
            pass

        else:
            raise AssertionError(
                "FAULT_ACCEPTED_" + kind
            )

        faults.append(kind)

    # Simulate rename succeeded but DB publication marker
    # had not been committed.
    recover = root / "rename_before_mark"
    recover.mkdir(mode=0o700)

    db = recover / "session.sqlite"
    receipt = recover / "decision.json"

    backup(main_db, db)
    shutil.copyfile(main_receipt, receipt)

    with sqlite3.connect(db) as connection:
        connection.execute(
            "UPDATE outbox SET published=0"
        )

    b.publish(db, receipt)

    need(
        b.verify(db, receipt) == "COMPLETE_SYNTHETIC",
        "RECOVERY_FAILED",
    )

    report = {
        "schema":
            "TRUST_ROBOT_L44_SYNTHETIC_CAPTURE_BOUNDARY_VALIDATION_V1",
        "parent_commit": b.BASE,
        "core_source_sha256": sha(core),
        "test_source_sha256": sha(__file__),
        "l43_manifest_sha256": b.L43,
        "case_results": records,
        "completed_cases": 1,
        "partial_review_cases": 7,
        "event_mutations_rejected": mutation_cases,
        "event_mutation_count": 36,
        "faults_rejected": faults,
        "fault_count": 8,
        "publication_recovery_verified": True,
        "actual_sensor_acquisition_binding": False,
        "simulator_launch_authorized": False,
        "physical_sync_verified": False,
        "scientific_pose_factors": 0,
        "health_labels": 0,
        "git_changes_performed": False,
    }

    dump(args.report, report)

    print("L44_COMPLETED_SYNTHETIC_SESSIONS=1")
    print("L44_PARTIAL_CAPTURE_REVIEW_CASES=7")
    print("L44_MUTATED_EVENTS_QUARANTINED=36")
    print("L44_DATABASE_FAULTS_DENIED=8")
    print("L44_ATOMIC_RECEIPT_PUBLICATION_RECOVERY=PASS")


if __name__ == "__main__":
    p = argparse.ArgumentParser()

    for name in ("core", "out", "report"):
        p.add_argument("--" + name, required=True)

    main(p.parse_args())
