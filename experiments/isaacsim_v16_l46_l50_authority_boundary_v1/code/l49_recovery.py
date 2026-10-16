"""L49 offline authority failure and fail-closed quarantine recovery."""

import argparse
import copy
import hashlib
import json
import os
import secrets
import shutil
import sqlite3
from pathlib import Path

BASE = "c2e013f549b87e8646a8e51095a3372df0d09581"
DENY = "QUARANTINE_REVIEW_REQUIRED"

NAMES = ("central", "split_left", "split_right")

CONDITIONS = (
    "observed_three_way_nonce_collision",
    "issuer_unreachable",
    "witness_unreachable",
    "central_ledger_unreachable",
    "left_ledger_unreachable",
    "right_ledger_unreachable",
    "central_receipt_unavailable",
    "left_receipt_unavailable",
    "right_receipt_unavailable",
    "stale_authority_epoch",
    "untrusted_logical_clock",
    "unilateral_merge_requested",
    "pose_factor_promotion_requested",
    "divergent_session_claim",
    "forged_physical_witness_claim",
    "unsigned_resolution_override",
    "publication_interrupted",
    "incomplete_authority_inventory",
)

FAULTS = (
    "receipt_missing",
    "receipt_tamper",
    "row_receipt_tamper",
    "row_digest_tamper",
    "source_report_digest_tamper",
    "nonce_digest_tamper",
    "state_promoted",
    "published_reset",
    "db_corrupted",
    "row_deleted",
)


def need(ok, why):
    if not ok:
        raise ValueError(why)


def h(data):
    return hashlib.sha256(data).hexdigest()


def hb(path):
    return h(Path(path).read_bytes())


def canonical(obj):
    return (
        json.dumps(
            obj,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ) + "\n"
    ).encode()


def save(path, obj):
    with Path(path).open("xb") as f:
        f.write(
            (
                json.dumps(
                    obj,
                    indent=2,
                    sort_keys=True,
                    allow_nan=False,
                ) + "\n"
            ).encode()
        )


def jsonread(path):
    return json.loads(Path(path).read_bytes())


def regular(path):
    p = Path(path)

    need(
        p.is_file()
        and not p.is_symlink()
        and p.stat().st_nlink == 1
        and p.stat().st_size < 2000000,
        "UNSAFE_FILE:" + str(path),
    )

    return p


def sources(root, report47, report48):
    r47 = jsonread(report47)
    r48 = jsonread(report48)

    need(
        r47["central_single_host_successes"] == 1
        and r47["central_single_host_replays_denied"] == 7
        and r47["split_registry_same_nonce_admissions"] == 2,
        "L47_RESULTS",
    )

    need(
        r48["quarantine_decision"] == DENY
        and r48["detected_duplicate_nonce"] is True
        and r48["metadata_mutation_count"] == 24
        and r48["ledger_fault_count"] == 10,
        "L48_RESULTS",
    )

    request = regular(
        Path(root) / "synthetic_request.json"
    ).read_bytes()

    req = json.loads(request)

    need(
        request == canonical(req)
        and r47["request_sha256"] == h(request),
        "REQUEST",
    )

    nonce = h(bytes.fromhex(req["nonce_hex"]))
    sid = req["session_id"]
    digest = h(request)
    records = []

    for label in NAMES:
        db = regular(Path(root) / (label + ".sqlite"))
        rec = regular(Path(root) / (label + "_receipt.json"))

        con = sqlite3.connect(
            "file:" + str(db.resolve()) + "?mode=ro",
            uri=True,
        )

        try:
            con.execute("PRAGMA query_only=ON")

            need(
                con.execute("PRAGMA quick_check").fetchone()[0]
                == "ok",
                "SQLITE_CHECK",
            )

            rows = con.execute(
                "SELECT nonce_hash,session_id,"
                "request_digest,receipt,receipt_digest "
                "FROM admissions"
            ).fetchall()

        finally:
            con.close()

        need(len(rows) == 1, "LEDGER_CARDINALITY")

        n, s, rd, body, d = rows[0]

        need(
            (n, s, rd) == (nonce, sid, digest),
            "LEDGER_IDENTITY",
        )

        need(
            type(body) is bytes
            and h(body) == d
            and body == rec.read_bytes(),
            "RECEIPT_BYTES",
        )

        obj = json.loads(body)

        need(
            body == canonical(obj),
            "RECEIPT_CANONICAL",
        )

        need(
            obj["nonce_sha256"] == nonce
            and obj["request_sha256"] == digest
            and obj["decision"] == "LOCALLY_ADMITTED"
            and obj["cross_host_replay_qualified"] is False
            and obj["independent_physical_witness"] is False,
            "RECEIPT_TRUST",
        )

        evidence = {
            "label": label,
            "session_id": s,
            "nonce_sha256": n,
            "request_sha256": rd,
            "database_sha256": hb(db),
            "receipt_sha256": hb(rec),
        }

        old = next(
            x for x in r48["ledgers"]
            if x["label"] == label
        )

        need(
            all(
                evidence[k] == old[k]
                for k in evidence
            ),
            "L48_LEDGER_SNAPSHOT",
        )

        records.append(evidence)

    need(
        len(set(x["nonce_sha256"] for x in records)) == 1
        and len(set(x["session_id"] for x in records)) == 1,
        "NOT_DUPLICATE_NONCE",
    )

    return records, h(request)


def matrix(records):
    need(
        len(records) == 3
        and [x["label"] for x in records] == list(NAMES),
        "MATRIX_INPUT",
    )

    result = []

    for condition in CONDITIONS:
        gate = {
            "issuer_available":
                condition != "issuer_unreachable",
            "witness_available":
                condition != "witness_unreachable",
            "authority_inventory_complete":
                condition != "incomplete_authority_inventory",
            "fresh_authority_epoch":
                condition != "stale_authority_epoch",
            "trusted_clock": False,
            "globally_unique_nonce": False,
            "physical_witness": False,
            "capture_admission_authorized": False,
        }

        gate["requested_unsafe_promotion"] = (
            condition in (
                "unilateral_merge_requested",
                "pose_factor_promotion_requested",
                "forged_physical_witness_claim",
                "unsigned_resolution_override",
            )
        )

        result.append({
            "scenario": condition,
            "decision": DENY,
            "reconciliation_performed": False,
            "promoted_capture": False,
            "gate": gate,
        })

    need(len(result) == 18, "MATRIX_COUNT")

    return result


def receipt_body(contract_hash, report_hash, records):
    return {
        "schema": "TRUST_ROBOT_L49_QUARANTINE_RECEIPT_V1",
        "parent_commit": BASE,
        "state": DENY,
        "contract_sha256": contract_hash,
        "report_sha256": report_hash,
        "session_id": records[0]["session_id"],
        "nonce_sha256": records[0]["nonce_sha256"],
        "source_receipts_sha256": {
            x["label"]: x["receipt_sha256"]
            for x in records
        },
        "autonomous_merge_authorized": False,
        "physical_sensor_origin_verified": False,
        "distributed_consensus_verified": False,
        "sensor_measurements": 0,
        "scientific_pose_factors": 0,
        "health_labels": 0,
    }


def initialize(db, body):
    need(
        not Path(db).exists(),
        "EXISTING_DB",
    )

    c = sqlite3.connect(
        db,
        timeout=15,
        isolation_level=None,
    )

    try:
        c.execute("PRAGMA synchronous=FULL")
        c.execute("BEGIN IMMEDIATE")

        c.execute(
            "CREATE TABLE decision ("
            "id INTEGER PRIMARY KEY CHECK (id=1),"
            "state TEXT NOT NULL,"
            "nonce_sha TEXT NOT NULL,"
            "report_sha TEXT NOT NULL,"
            "receipt BLOB NOT NULL,"
            "receipt_sha TEXT NOT NULL,"
            "published INTEGER NOT NULL)"
        )

        obj = json.loads(body)

        c.execute(
            "INSERT INTO decision VALUES(1,?,?,?,?,?,0)",
            (
                DENY,
                obj["nonce_sha256"],
                obj["report_sha256"],
                body,
                h(body),
            ),
        )

        c.commit()

    except BaseException:
        c.rollback()
        raise

    finally:
        c.close()


def journal(
    db,
    receipt,
    contract,
    report,
    source_records,
    require_published=True,
):
    c = sqlite3.connect(
        "file:" + str(Path(db).resolve()) + "?mode=ro",
        uri=True,
    )

    try:
        c.execute("PRAGMA query_only=ON")

        need(
            c.execute("PRAGMA quick_check").fetchone()[0]
            == "ok",
            "SQLITE_CORRUPT",
        )

        rows = c.execute(
            "SELECT id,state,nonce_sha,report_sha,"
            "receipt,receipt_sha,published FROM decision"
        ).fetchall()

    finally:
        c.close()

    need(len(rows) == 1, "JOURNAL_CARDINALITY")

    rid, state, nonce, rh, body, dh, mark = rows[0]

    expected = canonical(
        receipt_body(
            hb(contract),
            hb(report),
            source_records,
        )
    )

    need(
        rid == 1
        and state == DENY
        and nonce == source_records[0]["nonce_sha256"]
        and rh == hb(report),
        "QUARANTINE_BINDING",
    )

    need(
        type(body) is bytes
        and body == expected
        and h(body) == dh,
        "JOURNAL_RECEIPT_INTEGRITY",
    )

    need(
        mark in (0, 1),
        "PUBLISHED_MARKER",
    )

    if require_published:
        need(mark == 1, "NOT_PUBLISHED")

        need(
            regular(receipt).read_bytes() == body,
            "EXPORTED_RECEIPT",
        )

    return body, mark


def publish(db, receipt, contract, report, records):
    body, mark = journal(
        db,
        receipt,
        contract,
        report,
        records,
        False,
    )

    p = Path(receipt)

    if p.exists() or p.is_symlink():
        need(
            regular(p).read_bytes() == body,
            "CONFLICTING_PUBLICATION",
        )

    else:
        need(
            mark == 0,
            "PUBLISHED_RECEIPT_MISSING",
        )

        tmp = p.parent / (
            ".pending_" + secrets.token_hex(8)
        )

        with tmp.open("xb") as f:
            f.write(body)
            f.flush()
            os.fsync(f.fileno())

        try:
            os.link(
                tmp,
                p,
                follow_symlinks=False,
            )

            fd = os.open(
                p.parent,
                os.O_RDONLY | os.O_DIRECTORY,
            )

            try:
                os.fsync(fd)
            finally:
                os.close(fd)

        finally:
            tmp.unlink(missing_ok=True)

    if mark == 0:
        c = sqlite3.connect(
            db,
            timeout=15,
            isolation_level=None,
        )

        try:
            c.execute("BEGIN IMMEDIATE")

            changed = c.execute(
                "UPDATE decision SET published=1 "
                "WHERE id=1 AND published=0 "
                "AND receipt_sha=?",
                (h(body),),
            )

            need(
                changed.rowcount == 1,
                "PUBLISH_RACE",
            )

            c.commit()

        except BaseException:
            c.rollback()
            raise

        finally:
            c.close()

    journal(
        db,
        receipt,
        contract,
        report,
        records,
        True,
    )


def backup(db, copyto):
    src = sqlite3.connect(
        "file:" + str(Path(db).resolve()) + "?mode=ro",
        uri=True,
    )

    try:
        dst = sqlite3.connect(copyto)

        try:
            src.backup(dst)
        finally:
            dst.close()

    finally:
        src.close()


def check_claim(receipt, expected):
    need(
        type(receipt) is dict
        and set(receipt) == set(expected),
        "CLAIM_FIELDS",
    )

    for key, value in expected.items():
        need(
            type(receipt[key]) is type(value)
            and receipt[key] == value,
            "INVALID_CLAIM:" + key,
        )

    return True


def negative_claims(original):
    need(
        check_claim(original, original),
        "POSITIVE_CLAIM_BASELINE",
    )

    names = []

    fields = {
        "state": "CAPTURE_APPROVED",
        "autonomous_merge_authorized": True,
        "physical_sensor_origin_verified": True,
        "distributed_consensus_verified": True,
        "sensor_measurements": 1,
        "scientific_pose_factors": 1,
        "health_labels": 1,
        "nonce_sha256": "0" * 64,
        "report_sha256": "1" * 64,
        "contract_sha256": "2" * 64,
        "session_id": "FORGED",
        "parent_commit": "3" * 64,
    }

    for k, v in fields.items():
        changed = copy.deepcopy(original)
        changed[k] = v

        need(
            changed != original,
            "INVALID_NEGATIVE_CASE",
        )

        try:
            check_claim(changed, original)

        except ValueError:
            names.append("forged_" + k)

        else:
            raise AssertionError(
                "FORGED_CLAIM_ACCEPTED:" + k
            )

    need(len(names) == 12, "NEGATIVE_COUNT")

    return names


def main(a):
    root = Path(a.session)

    need(
        not root.exists(),
        "OUTPUT_COLLISION",
    )

    root.mkdir(mode=0o700)

    records, reqsha = sources(
        a.l47_synthetic,
        a.l47_report,
        a.l48_report,
    )

    cases = matrix(records)

    rejected = negative_claims(
        receipt_body(
            "A" * 64,
            "B" * 64,
            records,
        )
    )

    contract = {
        "schema":
            "TRUST_ROBOT_L49_AUTHORITY_FAILURE_CONTRACT_V1",
        "parent_commit": BASE,
        "engine_sha256": hb(__file__),
        "l47_report_sha256": hb(a.l47_report),
        "l48_report_sha256": hb(a.l48_report),
        "l48_validation_sha256": hb(a.l48_validation),
        "issuer_authenticated_externally": False,
        "independent_witness_present": False,
        "global_nonce_ledger_present": False,
        "automatic_reconciliation_authorized": False,
        "real_power_failure_tested": False,
        "trusted_clock_proven": False,
        "policy": DENY,
        "future_exit_requires_external_evidence": True,
    }

    save(a.contract, contract)

    report = {
        "schema":
            "TRUST_ROBOT_L49_AUTHORITY_FAILURE_FALSIFICATION_V1",
        "contract_sha256": hb(a.contract),
        "engine_sha256": hb(__file__),
        "l47_request_sha256": reqsha,
        "l48_report_sha256": hb(a.l48_report),
        "source_ledgers": records,
        "scenarios": cases,
        "scenario_count": len(cases),
        "quarantine_decisions": 18,
        "negative_claims_rejected": rejected,
        "negative_claim_count": 12,
        "recovery_windows": [
            "commit_before_publication",
            "file_before_mark",
            "idempotent_republish",
        ],
        "receipt_fault_names": list(FAULTS),
        "receipt_fault_count": len(FAULTS),
        "global_replay_prevention_verified": False,
        "physical_witness_verified": False,
        "real_power_failure_tested": False,
        "autonomous_merge_performed": False,
        "new_sensor_measurements": 0,
        "scientific_pose_factors": 0,
        "health_labels": 0,
        "git_push_performed": False,
    }

    save(a.report, report)

    body = canonical(
        receipt_body(
            hb(a.contract),
            hb(a.report),
            records,
        )
    )

    db = root / "quarantine.sqlite"
    rec = root / "quarantine_receipt.json"

    initialize(db, body)

    need(
        not rec.exists()
        and journal(
            db,
            rec,
            a.contract,
            a.report,
            records,
            False,
        )[1] == 0,
        "PREPUB_WINDOW",
    )

    publish(
        db,
        rec,
        a.contract,
        a.report,
        records,
    )

    publish(
        db,
        rec,
        a.contract,
        a.report,
        records,
    )

    for kind in (
        "file_before_mark",
        "commit_before_publication",
    ):
        p = root / kind
        p.mkdir(mode=0o700)

        d = p / "quarantine.sqlite"
        r = p / "quarantine_receipt.json"

        backup(db, d)

        c = sqlite3.connect(d)

        try:
            c.execute(
                "UPDATE decision SET published=0"
            )
            c.commit()
        finally:
            c.close()

        if kind == "file_before_mark":
            shutil.copyfile(rec, r)

        publish(
            d,
            r,
            a.contract,
            a.report,
            records,
        )

        need(
            journal(
                d,
                r,
                a.contract,
                a.report,
                records,
                True,
            )[1] == 1,
            "RECOVERY",
        )

    for name in FAULTS:
        p = root / ("fault_" + name)
        p.mkdir(mode=0o700)

        d = p / "quarantine.sqlite"
        r = p / "quarantine_receipt.json"

        backup(db, d)
        shutil.copyfile(rec, r)

        if name == "receipt_missing":
            r.unlink()

        elif name == "receipt_tamper":
            r.write_bytes(b"FORGED\n")

        elif name == "db_corrupted":
            d.write_bytes(b"NOT_SQLITE\n")

        else:
            modifications = {
                "row_receipt_tamper": (
                    "UPDATE decision SET receipt=?",
                    (b"FORGED",),
                ),
                "row_digest_tamper": (
                    "UPDATE decision SET receipt_sha=?",
                    ("a" * 64,),
                ),
                "source_report_digest_tamper": (
                    "UPDATE decision SET report_sha=?",
                    ("b" * 64,),
                ),
                "nonce_digest_tamper": (
                    "UPDATE decision SET nonce_sha=?",
                    ("c" * 64,),
                ),
                "state_promoted": (
                    "UPDATE decision SET state=?",
                    ("AUTHORIZED",),
                ),
                "published_reset": (
                    "UPDATE decision SET published=?",
                    (0,),
                ),
                "row_deleted": (
                    "DELETE FROM decision",
                    (),
                ),
            }

            sql, params = modifications[name]

            c = sqlite3.connect(d)

            try:
                c.execute(sql, params)
                c.commit()
            finally:
                c.close()

        try:
            journal(
                d,
                r,
                a.contract,
                a.report,
                records,
                True,
            )

        except (
            ValueError,
            sqlite3.DatabaseError,
            OSError,
            KeyError,
            TypeError,
        ):
            pass

        else:
            raise AssertionError(
                "FAULT_ACCEPTED:" + name
            )

    need(
        journal(
            db,
            rec,
            a.contract,
            a.report,
            records,
            True,
        )[1] == 1,
        "ROOT_JOURNAL",
    )

    print(
        "L49_SYNTHETIC_AUTHORITY_FAILURE_SCENARIOS="
        "18_QUARANTINED"
    )
    print("L49_FALSE_PROMOTION_CLAIMS=12_DENIED")
    print(
        "L49_SIMULATED_PUBLICATION_WINDOWS="
        "3_RECOVERED_OR_IDEMPOTENT"
    )
    print("L49_JOURNAL_AND_RECEIPT_FAULTS=10_DENIED")
    print("L49_OUTAGE_QUARANTINE_EXERCISE=PASS")


if __name__ == "__main__":
    p = argparse.ArgumentParser()

    for field in (
        "l47_synthetic",
        "l47_report",
        "l48_report",
        "l48_validation",
        "session",
        "contract",
        "report",
    ):
        p.add_argument(
            "--" + field.replace("_", "-"),
            dest=field,
            required=True,
        )

    main(p.parse_args())
