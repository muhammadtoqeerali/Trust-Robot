"""L39 offline crash-window and incomplete-session recovery assessment.

All failure injections operate on private L39 SQLite copies.
The historical L38 registry and receipts remain read-only.

This does not simulate an actual power outage, nor qualify
hardware durability, independent source authenticity, or
physical measurement timing.
"""

import argparse
import collections
import hashlib
import json
import shutil
import sqlite3
from pathlib import Path

BASE = (
    "0b542e8644f3c4b98ed92c0f83a7c82a4635ae52"
)

PINS = {
    "db":
        "cd77cabf882de91cace96c2d3cb5130a7d7877e39301eb2fbf0167422c97a240",
    "challenge":
        "2a20c6b86f79472003a0187dc3d6d9fc520092743d8343aeb2412556c8f770db",
    "admission":
        "2f8a0f3be28eb0b2b139f9f36836160cf05775917c313982b0f666e930588a61",
    "seal":
        "4d380b175c62401d404169d1611f8c332203c53506b79474673e68a118771bdd",
    "l38_report":
        "d3ec936ccc7ebeb1aeb7d629d90b0767a8fc15d9ff6e772637a4c2c9ca7adba8",
}

SOURCE_CANDIDATE = (
    "4384b085f79dff51af5dbbf8a4c4bf4cae6deffc906bfbcaf8a8ef00a7e05dec"
)

CONTRACT_SHA = (
    "ee8dfaa3a0f95813d29efa68f65a3222a39cce5e12cf855c4c3508791dcc05f9"
)

FIXTURE_SHA = (
    "b2fa0728d1aa867d162bae7e463f7bf353b058222d2700eaf392cd271ed97736"
)

MODE = "OFFLINE_L35_FIXTURE_NO_SENSOR_ACQUISITION"

COLUMNS = [
    "session_id",
    "nonce_sha",
    "challenge_sha",
    "stage",
    "admission_sha",
    "seal_sha",
    "issued_ns",
]


def need(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(
        Path(path).read_bytes()
    ).hexdigest()


def load(path):
    return json.loads(
        Path(path).read_text(encoding="utf-8")
    )


def safe(path):
    p = Path(path)

    need(
        p.is_file() and not p.is_symlink(),
        "MISSING_OR_SYMLINKED_EVIDENCE",
    )

    need(
        p.stat().st_nlink == 1
        and p.stat().st_size <= 4_000_000,
        "UNSAFE_EVIDENCE_FILE",
    )

    return p


def read_registry(db_path):
    db_path = safe(db_path)

    db = sqlite3.connect(
        "file:" + str(db_path.resolve()) + "?mode=ro",
        uri=True,
        timeout=5,
    )

    try:
        db.execute("PRAGMA query_only=ON")

        need(
            db.execute(
                "PRAGMA quick_check"
            ).fetchone()[0] == "ok",
            "SQLITE_INTEGRITY_FAILURE",
        )

        cols = [
            row[1]
            for row in db.execute(
                "PRAGMA table_info(sessions)"
            ).fetchall()
        ]

        need(
            cols == COLUMNS,
            "UNEXPECTED_DATABASE_SCHEMA",
        )

        db.row_factory = sqlite3.Row

        rows = db.execute(
            "SELECT * FROM sessions"
        ).fetchall()

        need(
            len(rows) == 1,
            "UNEXPECTED_SESSION_COUNT",
        )

        return dict(rows[0])

    finally:
        db.close()


def check_challenge(path, row):
    safe(path)

    need(
        sha(path) == PINS["challenge"],
        "CHALLENGE_HASH_MISMATCH",
    )

    ch = load(path)

    need(
        ch["schema"] ==
        "TRUST_ROBOT_L38_LOCAL_CHALLENGE_V1",
        "CHALLENGE_SCHEMA",
    )

    need(
        ch["parent_commit"] == BASE
        and ch["mode"] == MODE,
        "CHALLENGE_LINEAGE",
    )

    need(
        ch["candidate_sha256"] == SOURCE_CANDIDATE
        and ch["l36_contract_sha256"]
        == CONTRACT_SHA
        and ch["l35_transcript_sha256"]
        == FIXTURE_SHA,
        "CHALLENGE_SOURCE_BINDING",
    )

    need(
        ch["trusted_hardware_attestation"] is False
        and ch["physical_time_verified"] is False,
        "CHALLENGE_UNSUPPORTED_CLAIM",
    )

    nonce = ch["nonce_hex"]

    need(
        type(nonce) is str
        and len(nonce) == 64
        and all(
            c in "0123456789abcdef"
            for c in nonce
        ),
        "NONCE_FORMAT",
    )

    nonce_digest = hashlib.sha256(
        bytes.fromhex(nonce)
    ).hexdigest()

    need(
        row["session_id"] == ch["session_id"]
        and row["nonce_sha"] == nonce_digest
        and row["challenge_sha"] == sha(path)
        and row["issued_ns"]
        == ch["issued_monotonic_ns_untrusted"],
        "CHALLENGE_REGISTRY_BINDING",
    )

    return ch, nonce_digest


def check_admission(path, ch, nonce_digest):
    safe(path)

    need(
        sha(path) == PINS["admission"],
        "ADMISSION_HASH_MISMATCH",
    )

    rec = load(path)

    need(
        rec["schema"]
        == "TRUST_ROBOT_L38_OFFLINE_ADMISSION_V1",
        "ADMISSION_SCHEMA",
    )

    need(
        rec["session_id"] == ch["session_id"]
        and rec["mode"] == MODE,
        "ADMISSION_SESSION",
    )

    need(
        rec["challenge_file_sha256"]
        == PINS["challenge"]
        and rec["nonce_sha256"]
        == nonce_digest,
        "ADMISSION_CHALLENGE_BINDING",
    )

    need(
        rec["candidate_sha256"]
        == SOURCE_CANDIDATE
        and rec["l36_contract_sha256"]
        == CONTRACT_SHA
        and rec["l35_transcript_sha256"]
        == FIXTURE_SHA,
        "ADMISSION_SOURCE_LINEAGE",
    )

    need(
        rec["offline_admission"] is True
        and rec["simulator_launch_authorized"] is False
        and rec["new_sensor_measurements"] == 0
        and rec["pose_factors_authorized"] == 0,
        "ADMISSION_SCOPE",
    )

    need(
        rec["independent_source_authenticity_verified"]
        is False
        and rec["physical_sync_verified"] is False,
        "ADMISSION_SCIENTIFIC_CLAIM",
    )

    need(
        type(rec["admitted_monotonic_ns_untrusted"]) is int
        and ch["issued_monotonic_ns_untrusted"]
        < rec["admitted_monotonic_ns_untrusted"],
        "ADMISSION_ORDER",
    )

    return rec


def check_seal(path, ch, admission, nonce_digest):
    safe(path)

    need(
        sha(path) == PINS["seal"],
        "SEAL_HASH_MISMATCH",
    )

    rec = load(path)

    need(
        rec["schema"]
        == "TRUST_ROBOT_L38_LOCAL_SEAL_V1",
        "SEAL_SCHEMA",
    )

    need(
        rec["session_id"] == ch["session_id"]
        and rec["mode"] == MODE,
        "SEAL_SESSION",
    )

    need(
        rec["challenge_file_sha256"]
        == PINS["challenge"]
        and rec["admission_file_sha256"]
        == PINS["admission"]
        and rec["nonce_sha256"] == nonce_digest,
        "SEAL_RECEIPT_BINDING",
    )

    need(
        rec["fixture_sha256"] == FIXTURE_SHA
        and rec["fixture_records"] == 12,
        "SEAL_FIXTURE_BINDING",
    )

    for field in (
        "independent_hardware_witness",
        "independent_source_authenticity_verified",
        "physical_sync_verified",
        "independent_6dof_reference_verified",
        "simulator_launch_authorized",
    ):
        need(
            rec[field] is False,
            "SEAL_UNSUPPORTED_CLAIM",
        )

    need(
        rec["new_sensor_measurements"] == 0
        and rec["pose_factors_authorized"] == 0
        and rec["health_labels_generated"] == 0,
        "SEAL_SCIENTIFIC_ADMISSION",
    )

    need(
        type(rec["sealed_monotonic_ns_untrusted"]) is int
        and admission["admitted_monotonic_ns_untrusted"]
        < rec["sealed_monotonic_ns_untrusted"],
        "SEAL_ORDER",
    )


def assess(db, challenge, admission, seal):
    """Classify without modifying any database or receipt."""

    try:
        row = read_registry(db)

        ch, nonce_digest = check_challenge(
            challenge, row
        )

        stage = row["stage"]

        need(
            stage in ("ISSUED", "ADMITTED", "SEALED"),
            "UNKNOWN_REGISTRY_STATE",
        )

        if stage == "ISSUED":
            need(
                row["admission_sha"] is None
                and row["seal_sha"] is None
                and admission is None
                and seal is None,
                "ISSUED_WITH_CONFLICTING_EVIDENCE",
            )

            return {
                "decision": "ISSUED_REVIEW_REQUIRED",
                "reason": "NO_AUTOMATIC_ADMISSION",
                "live_launch_allowed": False,
                "automatic_repair_allowed": False,
            }

        need(
            admission is not None,
            "MISSING_ADMISSION_RECEIPT",
        )

        ad = check_admission(
            admission, ch, nonce_digest
        )

        need(
            row["admission_sha"] == sha(admission),
            "REGISTRY_ADMISSION_MISMATCH",
        )

        if stage == "ADMITTED":
            need(
                row["seal_sha"] is None
                and seal is None,
                "ADMITTED_WITH_CONFLICTING_SEAL",
            )

            return {
                "decision": "ADMITTED_REVIEW_REQUIRED",
                "reason": "NO_AUTOMATIC_SEAL_RECOVERY",
                "live_launch_allowed": False,
                "automatic_repair_allowed": False,
            }

        need(
            seal is not None,
            "MISSING_SEAL_RECEIPT",
        )

        check_seal(
            seal, ch, ad, nonce_digest
        )

        need(
            row["seal_sha"] == sha(seal),
            "REGISTRY_SEAL_MISMATCH",
        )

        return {
            "decision": "VERIFIED_SEALED",
            "reason": "COMPLETED_SESSION_NO_REENTRY",
            "live_launch_allowed": False,
            "automatic_repair_allowed": False,
        }

    except (
        ValueError,
        KeyError,
        TypeError,
        IndexError,
        OSError,
        sqlite3.DatabaseError,
        OverflowError,
    ) as error:
        return {
            "decision": "QUARANTINED",
            "reason": type(error).__name__,
            "live_launch_allowed": False,
            "automatic_repair_allowed": False,
        }


def main(args):
    inputs = {
        "db": Path(args.db),
        "challenge": Path(args.challenge),
        "admission": Path(args.admission),
        "seal": Path(args.seal),
        "l38_report": Path(args.l38report),
    }

    for name, path in inputs.items():
        safe(path)

        need(
            sha(path) == PINS[name],
            "FROZEN_INPUT_MISMATCH_" + name,
        )

    prior = load(inputs["l38_report"])

    need(
        prior["schema"]
        == "TRUST_ROBOT_L38_PERSISTENT_SESSION_BINDING_VALIDATION_V1",
        "L38_REPORT_SCHEMA",
    )

    need(
        prior["final_registry_state"] == "SEALED"
        and prior["adversarial_mutations_count"] == 20,
        "L38_PRIOR_VALIDATION",
    )

    scratch = Path(args.scratch)
    report_path = Path(args.report)

    need(
        not scratch.exists()
        and not report_path.exists(),
        "OUTPUT_COLLISION",
    )

    scratch.mkdir(mode=0o700)

    # name, simulated DB stage, included receipts,
    # database fault, file tamper, expected classification.
    cases = [
        (
            "sealed_complete", "SEALED",
            (True, True, True),
            None, None, "VERIFIED_SEALED",
        ),
        (
            "issued_after_commit", "ISSUED",
            (True, False, False),
            None, None, "ISSUED_REVIEW_REQUIRED",
        ),
        (
            "issued_missing_challenge", "ISSUED",
            (False, False, False),
            None, None, "QUARANTINED",
        ),
        (
            "issued_unexpected_admission", "ISSUED",
            (True, True, False),
            None, None, "QUARANTINED",
        ),
        (
            "issued_wrong_nonce", "ISSUED",
            (True, False, False),
            "wrong_nonce", None, "QUARANTINED",
        ),
        (
            "admitted_receipt_present", "ADMITTED",
            (True, True, False),
            None, None, "ADMITTED_REVIEW_REQUIRED",
        ),
        (
            "admitted_receipt_missing", "ADMITTED",
            (True, False, False),
            None, None, "QUARANTINED",
        ),
        (
            "admitted_wrong_hash", "ADMITTED",
            (True, True, False),
            "wrong_admission", None, "QUARANTINED",
        ),
        (
            "admitted_unexpected_seal", "ADMITTED",
            (True, True, True),
            None, None, "QUARANTINED",
        ),
        (
            "sealed_receipt_missing", "SEALED",
            (True, True, False),
            None, None, "QUARANTINED",
        ),
        (
            "sealed_wrong_hash", "SEALED",
            (True, True, True),
            "wrong_seal", None, "QUARANTINED",
        ),
        (
            "sealed_admission_missing", "SEALED",
            (True, False, True),
            None, None, "QUARANTINED",
        ),
        (
            "sealed_challenge_missing", "SEALED",
            (False, True, True),
            None, None, "QUARANTINED",
        ),
        (
            "sealed_receipt_tampered", "SEALED",
            (True, True, True),
            None, "seal", "QUARANTINED",
        ),
        (
            "sealed_challenge_tampered", "SEALED",
            (True, True, True),
            None, "challenge", "QUARANTINED",
        ),
        (
            "sealed_admission_tampered", "SEALED",
            (True, True, True),
            None, "admission", "QUARANTINED",
        ),
        (
            "registry_missing", "SEALED",
            (True, True, True),
            "missing_db", None, "QUARANTINED",
        ),
        (
            "registry_corrupted", "SEALED",
            (True, True, True),
            "corrupt_db", None, "QUARANTINED",
        ),
        (
            "registry_no_sessions", "SEALED",
            (True, True, True),
            "empty_db", None, "QUARANTINED",
        ),
        (
            "registry_extra_session", "SEALED",
            (True, True, True),
            "extra_session", None, "QUARANTINED",
        ),
    ]

    results = []

    try:
        for (
            name, stage, included,
            db_fault, tamper, expected
        ) in cases:
            folder = scratch / name
            folder.mkdir(mode=0o700)

            sample_db = folder / "registry.sqlite"

            if db_fault != "missing_db":
                shutil.copyfile(
                    inputs["db"],
                    sample_db,
                )

            if db_fault == "corrupt_db":
                sample_db.write_bytes(
                    b"NOT_A_VALID_SQLITE_DATABASE"
                )

            elif db_fault != "missing_db":
                con = sqlite3.connect(
                    str(sample_db)
                )

                try:
                    if stage == "ISSUED":
                        con.execute(
                            """
                            UPDATE sessions
                            SET stage='ISSUED',
                                admission_sha=NULL,
                                seal_sha=NULL
                            """
                        )

                    elif stage == "ADMITTED":
                        con.execute(
                            """
                            UPDATE sessions
                            SET stage='ADMITTED',
                                seal_sha=NULL
                            """
                        )

                    if db_fault == "wrong_nonce":
                        con.execute(
                            "UPDATE sessions SET nonce_sha=?",
                            ("0" * 64,),
                        )

                    elif db_fault == "wrong_admission":
                        con.execute(
                            "UPDATE sessions SET admission_sha=?",
                            ("0" * 64,),
                        )

                    elif db_fault == "wrong_seal":
                        con.execute(
                            "UPDATE sessions SET seal_sha=?",
                            ("0" * 64,),
                        )

                    elif db_fault == "empty_db":
                        con.execute(
                            "DELETE FROM sessions"
                        )

                    elif db_fault == "extra_session":
                        con.execute(
                            """
                            INSERT INTO sessions
                            VALUES (?,?,?,?,?,?,?)
                            """,
                            (
                                "KIOS_L39_UNTRUSTED_EXTRA",
                                "f" * 64,
                                "e" * 64,
                                "ISSUED",
                                None,
                                None,
                                1,
                            ),
                        )

                    con.commit()

                finally:
                    con.close()

            paths = {}

            for key, present in zip(
                ("challenge", "admission", "seal"),
                included,
            ):
                paths[key] = (
                    inputs[key] if present else None
                )

            if tamper is not None:
                modified = folder / (
                    tamper + "_tampered.json"
                )

                data = load(inputs[tamper])

                if tamper == "challenge":
                    data["nonce_hex"] = "0" * 64

                elif tamper == "admission":
                    data["offline_admission"] = False

                elif tamper == "seal":
                    data["fixture_records"] = 13

                modified.write_text(
                    json.dumps(
                        data,
                        indent=2,
                        sort_keys=True,
                    ) + "\n",
                    encoding="utf-8",
                )

                paths[tamper] = modified

            outcome = assess(
                sample_db,
                paths["challenge"],
                paths["admission"],
                paths["seal"],
            )

            need(
                outcome["decision"] == expected,
                "CASE_FAILED_" + name
                + "_GOT_" + outcome["decision"],
            )

            need(
                outcome["live_launch_allowed"] is False
                and outcome["automatic_repair_allowed"]
                is False,
                "UNSAFE_RECOVERY_DECISION",
            )

            results.append({
                "case": name,
                "expected": expected,
                "observed": outcome["decision"],
                "reason": outcome["reason"],
                "live_launch_allowed": False,
                "automatic_repair_allowed": False,
            })

    finally:
        # Remove only L39's newly created fault copies.
        shutil.rmtree(scratch)

    need(len(results) == 20, "CASE_COUNT")

    totals = dict(
        collections.Counter(
            item["observed"]
            for item in results
        )
    )

    need(
        totals == {
            "VERIFIED_SEALED": 1,
            "ISSUED_REVIEW_REQUIRED": 1,
            "ADMITTED_REVIEW_REQUIRED": 1,
            "QUARANTINED": 17,
        },
        "UNEXPECTED_DECISION_DISTRIBUTION",
    )

    # Confirm the original evidence remains valid.
    baseline = assess(
        inputs["db"],
        inputs["challenge"],
        inputs["admission"],
        inputs["seal"],
    )

    need(
        baseline["decision"]
        == "VERIFIED_SEALED",
        "ORIGINAL_L38_BASELINE_CHANGED",
    )

    for name, path in inputs.items():
        need(
            sha(path) == PINS[name],
            "FROZEN_INPUT_CHANGED_" + name,
        )

    report = {
        "schema":
            "TRUST_ROBOT_L39_CRASH_WINDOW_RECOVERY_ASSESSMENT_V1",
        "parent_git_commit": BASE,
        "implementation_sha256": sha(__file__),
        "input_sha256": PINS,
        "simulated_failure_cases": results,
        "case_count": len(results),
        "decision_counts": totals,
        "original_l38_final_state":
            "VERIFIED_SEALED",
        "replay_after_consumption_permitted": False,
        "automatic_receipt_recreation_permitted": False,
        "automatic_database_rollback_permitted": False,
        "live_simulator_launch_authorized": False,
        "real_power_failure_experiment_performed": False,
        "database_power_loss_durability_qualified": False,
        "tamper_resistant_storage_verified": False,
        "independent_source_authenticity_verified": False,
        "physical_exposure_sync_verified": False,
        "independent_6dof_reference_verified": False,
        "pose_factors_authorized": 0,
        "health_labels_generated": 0,
        "new_sensor_acquisitions": 0,
        "historical_inputs_modified": False,
        "git_commit_or_push_performed": False,
        "next":
            "L40_CRASH_SAFE_RECEIPT_RECOVERY_DESIGN_AND_OFFLINE_TEST",
    }

    report_path.write_text(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        ) + "\n",
        encoding="utf-8",
    )

    print("L39_ORIGINAL_SEALED_REGISTRY=VERIFIED")
    print("L39_FAILURE_CASES=20_PASS")
    print("L39_QUARANTINED_SCENARIOS=17")
    print("L39_INCOMPLETE_REVIEW_STATES=2")
    print("L39_COMPLETE_SESSION_STATES=1")
    print("L39_AUTOMATIC_UNSAFE_RECOVERY=DENIED")
    print("L39_OFFLINE_CRASH_WINDOW_ASSESSMENT=PASS")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    for name in (
        "db",
        "challenge",
        "admission",
        "seal",
        "l38report",
        "scratch",
        "report",
    ):
        parser.add_argument(
            "--" + name,
            required=True,
        )

    main(parser.parse_args())
