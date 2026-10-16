"""L45: coherent software-forgery falsification, offline only."""

import argparse
import copy
import hashlib
import importlib.util
import json
import shutil
import sqlite3
from pathlib import Path


def need(value, reason):
    if not value:
        raise AssertionError(reason)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, data):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(
            data, stream,
            sort_keys=True, indent=2,
            allow_nan=False,
        )
        stream.write("\n")


def module(path):
    spec = importlib.util.spec_from_file_location(
        "frozen_l44_core", path
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def baseline(dbpath, receipt, report, b):
    prior = json.loads(Path(report).read_text())

    first = next(
        x for x in prior["case_results"]
        if x["case"] == 0
    )

    need(
        sha(dbpath) == first["database_sha256"],
        "BASELINE_DB_HASH",
    )
    need(
        sha(receipt) == first["receipt_sha256"],
        "BASELINE_RECEIPT_HASH",
    )

    con = sqlite3.connect(
        "file:" + str(Path(dbpath).resolve()) + "?mode=ro",
        uri=True,
    )

    try:
        con.execute("PRAGMA query_only=ON")

        need(
            con.execute("PRAGMA quick_check").fetchone()[0]
            == "ok",
            "BASELINE_DB_INTEGRITY",
        )

        state = con.execute(
            "SELECT id,nonce,state FROM session"
        ).fetchall()

        need(
            len(state) == 1
            and state[0][2] == "COMPLETE_SYNTHETIC",
            "BASELINE_STATE",
        )

        sid, nonce, _ = state[0]

        rows = [
            json.loads(x[0])
            for x in con.execute(
                "SELECT payload FROM events ORDER BY pos"
            )
        ]

        outbox = con.execute(
            "SELECT payload,digest,published FROM outbox"
        ).fetchall()

    finally:
        con.close()

    need(
        len(rows) == 142
        and b.assess(rows, sid, nonce)[0]
        == "COMPLETE_SYNTHETIC",
        "BASELINE_EVENTS",
    )

    need(len(outbox) == 1, "BASELINE_OUTBOX_COUNT")

    body, digest, published = outbox[0]

    need(
        published == 1
        and b.h(body) == digest
        and body == Path(receipt).read_bytes(),
        "BASELINE_RECEIPT",
    )

    return sid, nonce, rows, first


def back_up(source, destination):
    original = sqlite3.connect(
        "file:" + str(Path(source).resolve()) + "?mode=ro",
        uri=True,
    )

    try:
        target = sqlite3.connect(destination)
        try:
            original.backup(target)
        finally:
            target.close()
    finally:
        original.close()


def mutate_db(path, sql, params=()):
    con = sqlite3.connect(path)
    try:
        con.execute(sql, params)
        con.commit()
    finally:
        con.close()


def assess_coherent(b, sid, nonce, original_tip):
    items = []

    for category in (
        "session_only",
        "nonce_only",
        "both",
    ):
        for index in range(4):
            tag = category + "_" + str(index)

            new_sid = (
                sid + "_L45_" + tag
                if category != "nonce_only"
                else sid
            )

            new_nonce = (
                hashlib.sha256(
                    (sid + nonce + tag).encode()
                ).hexdigest()
                if category != "session_only"
                else nonce
            )

            rows = b.events_for(
                new_sid, new_nonce
            )

            decision, counts = b.assess(
                rows, new_sid, new_nonce
            )

            need(
                decision == "COMPLETE_SYNTHETIC"
                and counts == b.COUNTS,
                "COHERENT_INTERNAL_REJECTION",
            )

            need(
                rows[-1]["event_digest"] != original_tip,
                "ROOT_NOT_CHANGED",
            )

            need(
                (new_sid, new_nonce) != (sid, nonce),
                "NO_IDENTITY_CHANGE",
            )

            items.append({
                "scenario": tag,
                "internal_l44_decision": decision,
                "original_session_pin_matches":
                    new_sid == sid,
                "original_nonce_pin_matches":
                    new_nonce == nonce,
                "original_event_tip_pin_matches":
                    rows[-1]["event_digest"] == original_tip,
                "trusted_source_authenticity_verified":
                    False,
            })

    need(len(items) == 12, "COHERENT_TEST_COUNT")

    return items


def assess_single_event_mutations(
    b, sid, nonce, original
):
    cases = []

    for position in (0, 6, 12, 129, 141):
        for field in (
            "session_id",
            "event_index",
            "payload_sha256",
            "event_digest",
        ):
            rows = copy.deepcopy(original)

            rows[position][field] = (
                -1
                if type(rows[position][field]) is int
                else "ALTERED_WITHOUT_REHASH"
            )

            decision, _ = b.assess(
                rows, sid, nonce
            )

            need(
                decision == "QUARANTINED",
                "EVENT_MUTATION_ACCEPTED",
            )

            cases.append(
                f"{position}:{field}"
            )

    need(
        len(cases) == len(set(cases)) == 20,
        "EVENT_MUTATION_COUNT",
    )

    return cases


def run(args):
    b = module(args.core)

    root = Path(args.scenarios)

    need(
        not root.exists(),
        "SCENARIO_COLLISION",
    )
    root.mkdir(mode=0o700)

    sid, nonce, original, original_entry = baseline(
        args.db,
        args.receipt,
        args.l44report,
        b,
    )

    original_tip = original[-1]["event_digest"]

    coherent = assess_coherent(
        b, sid, nonce, original_tip
    )

    incoherent = assess_single_event_mutations(
        b, sid, nonce, original
    )

    # A locally fabricated software-only session may
    # pass L44 without an actual sensor acquisition.
    forged = root / "coherent_local_generation"
    forged.mkdir(mode=0o700)

    fdb = forged / "session.sqlite"
    freceipt = forged / "decision.json"

    b.create(fdb)
    b.capture(fdb, 142)

    need(
        b.finalize(fdb) == "COMPLETE_SYNTHETIC",
        "FORGED_FINALIZE",
    )

    b.publish(fdb, freceipt)

    need(
        b.verify(fdb, freceipt)
        == "COMPLETE_SYNTHETIC",
        "FORGED_RECEIPT",
    )

    need(
        sha(fdb) != original_entry["database_sha256"],
        "FORGE_MATCHED_ORIGINAL_DB",
    )

    need(
        sha(freceipt)
        != original_entry["receipt_sha256"],
        "FORGE_MATCHED_ORIGINAL_RECEIPT",
    )

    # Two simulated receipt publication interruptions.
    recoveries = []

    for name in (
        "rename_before_publication_mark",
        "committed_outbox_missing_file",
    ):
        folder = root / name
        folder.mkdir(mode=0o700)

        db = folder / "session.sqlite"
        receipt = folder / "decision.json"

        back_up(args.db, db)
        shutil.copyfile(args.receipt, receipt)

        mutate_db(
            db,
            "UPDATE outbox SET published=0",
        )

        if name == "committed_outbox_missing_file":
            receipt.unlink()

        b.publish(db, receipt)

        need(
            b.verify(db, receipt)
            == "COMPLETE_SYNTHETIC",
            "RECOVERY_FAILED_" + name,
        )

        need(
            sha(receipt)
            == original_entry["receipt_sha256"],
            "RECOVERY_CHANGED_RECEIPT",
        )

        recoveries.append(name)

    fault_names = [
        "receipt_missing",
        "receipt_corrupted",
        "cross_session_receipt",
        "database_corrupted",
        "outbox_deleted",
        "outbox_payload_changed",
        "outbox_digest_changed",
        "outbox_published_invalid",
        "session_nonce_changed",
        "session_id_changed",
        "final_event_deleted",
        "event_position_gap",
    ]

    for name in fault_names:
        folder = root / ("fault_" + name)
        folder.mkdir(mode=0o700)

        db = folder / "session.sqlite"
        receipt = folder / "decision.json"

        back_up(args.db, db)
        shutil.copyfile(args.receipt, receipt)

        if name == "receipt_missing":
            receipt.unlink()

        elif name == "receipt_corrupted":
            receipt.write_bytes(
                b"CORRUPTED_RECEIPT\n"
            )

        elif name == "cross_session_receipt":
            shutil.copyfile(
                freceipt, receipt
            )

        elif name == "database_corrupted":
            db.write_bytes(
                b"NOT_A_SQLITE_DATABASE\n"
            )

        elif name == "outbox_deleted":
            mutate_db(
                db, "DELETE FROM outbox"
            )

        elif name == "outbox_payload_changed":
            mutate_db(
                db,
                "UPDATE outbox SET payload=?",
                (b"FORGED",),
            )

        elif name == "outbox_digest_changed":
            mutate_db(
                db,
                "UPDATE outbox SET digest=?",
                ("1" * 64,),
            )

        elif name == "outbox_published_invalid":
            mutate_db(
                db,
                "UPDATE outbox SET published=2",
            )

        elif name == "session_nonce_changed":
            mutate_db(
                db,
                "UPDATE session SET nonce=?",
                ("2" * 64,),
            )

        elif name == "session_id_changed":
            mutate_db(
                db,
                "UPDATE session SET id=?",
                ("KIOS_L45_DIFFERENT_ID",),
            )

        elif name == "final_event_deleted":
            mutate_db(
                db,
                "DELETE FROM events WHERE pos=141",
            )

        elif name == "event_position_gap":
            mutate_db(
                db,
                "UPDATE events SET pos=500 WHERE pos=70",
            )

        try:
            b.verify(db, receipt)

        except (
            ValueError,
            sqlite3.DatabaseError,
            KeyError,
            TypeError,
            OSError,
        ):
            pass

        else:
            raise AssertionError(
                "FAULT_ACCEPTED_" + name
            )

    need(
        sha(args.db)
        == original_entry["database_sha256"],
        "BASELINE_DB_CHANGED",
    )

    need(
        sha(args.receipt)
        == original_entry["receipt_sha256"],
        "BASELINE_RECEIPT_CHANGED",
    )

    contract = {
        "schema":
            "TRUST_ROBOT_L45_COHERENT_FORGERY_BOUNDARY_CONTRACT_V1",
        "parent_commit": b.BASE,
        "l44_core_sha256": sha(args.core),
        "l44_report_sha256": sha(args.l44report),
        "assessment_source_sha256": sha(__file__),
        "independent_verifier_sha256":
            sha(args.verifier),
        "threat_model":
            "Attacker controls locally generated metadata and can recompute content digests; external witness is absent",
        "baseline_pin_scope":
            "Previously recorded software-session identity and root, not physically trusted attestation",
        "actual_external_trusted_witness": False,
        "actual_source_authenticity_verified": False,
        "live_simulator_launch_authorized": False,
        "scientific_pose_factors": 0,
    }

    save(args.contract, contract)

    report = {
        "schema":
            "TRUST_ROBOT_L45_COHERENT_FORGERY_FALSIFICATION_REPORT_V1",
        "contract_sha256": sha(args.contract),
        "l44_source_sha256": sha(args.core),
        "l44_report_sha256": sha(args.l44report),
        "baseline_database_sha256":
            original_entry["database_sha256"],
        "baseline_receipt_sha256":
            original_entry["receipt_sha256"],
        "original_session_tip_sha256":
            original_tip,
        "coherent_rekey_cases": coherent,
        "coherent_rekey_count": len(coherent),
        "coherent_cases_internally_accepted":
            len(coherent),
        "coherent_cases_with_trusted_provenance": 0,
        "incoherent_event_mutations_rejected":
            incoherent,
        "incoherent_rejection_count":
            len(incoherent),
        "new_local_fabricated_session": {
            "internal_l44_result":
                "COMPLETE_SYNTHETIC",
            "database_sha256": sha(fdb),
            "receipt_sha256": sha(freceipt),
            "real_sensor_measurements": 0,
            "independent_capture_witness": False,
        },
        "recovery_cases": recoveries,
        "recovery_count": len(recoveries),
        "fault_cases": fault_names,
        "faults_rejected_count": len(fault_names),
        "actual_sensor_acquisition_binding": False,
        "independent_source_authenticity_verified":
            False,
        "trusted_physical_timing_verified": False,
        "hardware_attestation_verified": False,
        "real_power_failure_tested": False,
        "live_simulator_launch_authorized": False,
        "new_sensor_measurements": 0,
        "pose_factors_authorized": 0,
        "health_labels_generated": 0,
        "git_commit_or_push": False,
    }

    save(args.report, report)

    print(
        "L45_COHERENT_SELF_REHASHED_CASES="
        "12_INTERNALLY_ACCEPTED"
    )
    print(
        "L45_TRUSTED_PROVENANCE_FOR_COHERENT_CASES=0"
    )
    print(
        "L45_INCOHERENT_EVENT_MUTATIONS=20_REJECTED"
    )
    print(
        "L45_RECEIPT_RECOVERY_WINDOWS=2_PASS"
    )
    print(
        "L45_DATABASE_AND_RECEIPT_FAULTS=12_DENIED"
    )
    print("L45_OFFLINE_FALSIFICATION=PASS")


if __name__ == "__main__":
    p = argparse.ArgumentParser()

    for arg in (
        "core",
        "db",
        "receipt",
        "l44report",
        "verifier",
        "scenarios",
        "contract",
        "report",
    ):
        p.add_argument(
            "--" + arg, required=True
        )

    run(p.parse_args())
