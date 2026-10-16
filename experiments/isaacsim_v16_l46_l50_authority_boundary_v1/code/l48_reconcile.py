"""L48 offline reconciliation and quarantine.

No distributed transaction, independent physical witness,
trusted source authentication or live sensor capture.
"""

import argparse
import copy
import hashlib
import json
import shutil
import sqlite3

from pathlib import Path

BASE = "c2e013f549b87e8646a8e51095a3372df0d09581"

CAND = (
    "4384b085f79dff51af5dbbf8a4c4bf4cae6deffc906bfbcaf8a8ef00a7e05dec"
)

L46 = (
    "183bf08ffdf467294027af058ab8e627bcec7d35192c612accff78735c1c7e40"
)

LABELS = ("central", "split_left", "split_right")
DENY = "QUARANTINE_REVIEW_REQUIRED"


def need(ok, why):
    if not ok:
        raise ValueError(why)


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha(path):
    return sha_bytes(Path(path).read_bytes())


def canon(value):
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ) + "\n"
    ).encode()


def read_file(path):
    p = Path(path)

    need(
        p.is_file()
        and not p.is_symlink()
        and p.stat().st_nlink == 1
        and p.stat().st_size <= 2000000,
        "UNSAFE_FILE",
    )

    return p.read_bytes()


def jsonfile(path):
    return json.loads(read_file(path))


def write(path, obj):
    with Path(path).open("x", encoding="utf8") as f:
        json.dump(
            obj,
            f,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        f.write("\n")


def request_check(raw):
    r = json.loads(raw)

    fields = {
        "schema",
        "session_id",
        "nonce_hex",
        "candidate_sha256",
        "l46_report_sha256",
        "parent_commit",
        "mode",
        "issuer_role",
        "not_before_tick",
        "deadline_tick",
        "source_origin_verified",
        "physical_sync_verified",
        "attestation_verified",
        "new_sensor_measurements",
        "pose_factors_authorized",
        "health_labels_generated",
    }

    need(
        type(r) is dict
        and set(r) == fields
        and raw == canon(r),
        "REQUEST_CANONICAL",
    )

    need(
        r["schema"] == "TRUST_ROBOT_L47_TEST_REQUEST_V1",
        "REQUEST_SCHEMA",
    )

    need(
        type(r["session_id"]) is str
        and r["session_id"].startswith("L47_SYNTH_"),
        "REQUEST_SESSION",
    )

    need(
        type(r["nonce_hex"]) is str
        and len(r["nonce_hex"]) == 64
        and len(bytes.fromhex(r["nonce_hex"])) == 32,
        "REQUEST_NONCE",
    )

    need(
        r["candidate_sha256"] == CAND
        and r["l46_report_sha256"] == L46
        and r["parent_commit"] == BASE,
        "REQUEST_LINEAGE",
    )

    need(
        r["mode"]
        == "OFFLINE_SINGLE_HOST_SYNTHETIC_NONCE_REPLAY_TEST"
        and r["issuer_role"] == "UNTRUSTED_TEST_GENERATOR",
        "REQUEST_MODE",
    )

    need(
        type(r["not_before_tick"]) is int
        and r["not_before_tick"] == 0
        and type(r["deadline_tick"]) is int
        and r["deadline_tick"] == 100,
        "UNTRUSTED_TICKS",
    )

    for field in (
        "source_origin_verified",
        "physical_sync_verified",
        "attestation_verified",
    ):
        need(
            r[field] is False,
            "FALSE_CLAIM_" + field,
        )

    for field in (
        "new_sensor_measurements",
        "pose_factors_authorized",
        "health_labels_generated",
    ):
        need(
            type(r[field]) is int and r[field] == 0,
            "FALSE_SCIENCE_" + field,
        )

    return r


def expected_receipt(r, request_digest, nonce_hash):
    return {
        "schema":
            "TRUST_ROBOT_L47_LOCAL_ADMISSION_RECEIPT_V1",
        "session_id": r["session_id"],
        "nonce_sha256": nonce_hash,
        "request_sha256": request_digest,
        "candidate_sha256": CAND,
        "l46_report_sha256": L46,
        "parent_commit": BASE,
        "decision": "LOCALLY_ADMITTED",
        "independent_physical_witness": False,
        "cross_host_replay_qualified": False,
        "new_sensor_measurements": 0,
        "pose_factors_authorized": 0,
        "health_labels_generated": 0,
    }


def audit(db, receipt, request_raw, label):
    need(label in LABELS, "UNEXPECTED_LABEL")

    r = request_check(request_raw)

    database_bytes = read_file(db)
    receipt_bytes = read_file(receipt)

    con = sqlite3.connect(
        "file:" + str(Path(db).resolve()) + "?mode=ro",
        uri=True,
    )

    try:
        con.execute("PRAGMA query_only=ON")

        need(
            con.execute("PRAGMA quick_check").fetchone()[0]
            == "ok",
            "SQLITE_INTEGRITY",
        )

        rows = con.execute(
            "SELECT nonce_hash,session_id,"
            "request_digest,receipt,receipt_digest "
            "FROM admissions"
        ).fetchall()

    finally:
        con.close()

    need(len(rows) == 1, "ADMISSION_CARDINALITY")

    n, sid, rd, body, digest = rows[0]

    expected_nonce = sha_bytes(
        bytes.fromhex(r["nonce_hex"])
    )

    expected_request = sha_bytes(request_raw)

    need(
        n == expected_nonce
        and sid == r["session_id"]
        and rd == expected_request,
        "ADMISSION_LINK",
    )

    need(
        type(body) is bytes
        and body == canon(
            expected_receipt(r, rd, n)
        ),
        "RECEIPT_CONTENT",
    )

    need(
        digest == sha_bytes(body)
        and receipt_bytes == body,
        "RECEIPT_DIGEST_OR_EXPORT",
    )

    return {
        "label": label,
        "scope": "LOCAL_SQLITE_NOT_DISTRIBUTED",
        "session_id": sid,
        "nonce_sha256": n,
        "request_sha256": rd,
        "database_sha256": sha_bytes(database_bytes),
        "receipt_sha256": sha_bytes(receipt_bytes),
        "decision": "LOCALLY_ADMITTED",
        "origin_attested": False,
    }


def check_reconciliation(entries, baseline):
    need(
        type(entries) is list and len(entries) == 3,
        "THREE_LEDGER_RECORDS_REQUIRED",
    )

    need(
        all(type(x) is dict for x in entries),
        "LEDGER_RECORD_SHAPE",
    )

    need(
        [x.get("label") for x in entries]
        == list(LABELS),
        "LEDGER_ORDER",
    )

    need(
        entries == baseline,
        "FROZEN_LEDGER_COMMITMENT_MISMATCH",
    )

    need(
        len({
            x["nonce_sha256"]
            for x in entries
        }) == 1,
        "EXPECT_DEMONSTRATED_CONFLICT",
    )

    need(
        len({
            x["session_id"]
            for x in entries
        }) == 1,
        "SESSION_LINK",
    )

    need(
        all(
            x["origin_attested"] is False
            for x in entries
        ),
        "UNTRUSTED_ORIGIN",
    )

    return DENY


def mutations(baseline):
    specs = (
        ("database_sha256", "0" * 64),
        ("receipt_sha256", "1" * 64),
        ("nonce_sha256", "2" * 64),
        ("session_id", "FORGED"),
        ("request_sha256", "3" * 64),
        ("scope", "INDEPENDENT_TRUSTED_GLOBAL"),
        ("origin_attested", True),
        ("decision", "APPROVED_GLOBAL"),
    )

    out = []

    for label_index, label in enumerate(LABELS):
        for field, value in specs:
            case = copy.deepcopy(baseline)

            case[label_index][field] = value

            name = f"{label}_{field}"

            try:
                check_reconciliation(
                    case,
                    baseline,
                )

            except ValueError:
                out.append(name)

            else:
                raise AssertionError(
                    "MUTATION_ADMITTED:" + name
                )

    need(len(out) == 24, "MUTATION_COUNT")

    return out


FAULTS = (
    (
        "central_receipt_truncated",
        "central",
        "receipt_truncate",
    ),
    (
        "left_receipt_missing",
        "split_left",
        "receipt_missing",
    ),
    (
        "right_receipt_appended",
        "split_right",
        "receipt_append",
    ),
    (
        "central_nonce_changed",
        "central",
        "nonce_changed",
    ),
    (
        "left_session_changed",
        "split_left",
        "session_changed",
    ),
    (
        "right_request_changed",
        "split_right",
        "request_changed",
    ),
    (
        "central_digest_changed",
        "central",
        "digest_changed",
    ),
    (
        "left_receipt_changed",
        "split_left",
        "receipt_blob_changed",
    ),
    (
        "right_row_removed",
        "split_right",
        "row_removed",
    ),
    (
        "central_db_corrupted",
        "central",
        "db_corrupted",
    ),
)


def fault_apply(db, receipt, fault):
    if fault == "receipt_truncate":
        receipt.write_bytes(b"BAD\n")

    elif fault == "receipt_missing":
        receipt.unlink()

    elif fault == "receipt_append":
        receipt.write_bytes(
            receipt.read_bytes() + b"BAD"
        )

    elif fault == "db_corrupted":
        db.write_bytes(b"NOT_SQLITE\n")

    else:
        sql, args = {
            "nonce_changed": (
                "UPDATE admissions SET nonce_hash=?",
                ("f" * 64,),
            ),
            "session_changed": (
                "UPDATE admissions SET session_id=?",
                ("FORGED_SESSION",),
            ),
            "request_changed": (
                "UPDATE admissions SET request_digest=?",
                ("e" * 64,),
            ),
            "digest_changed": (
                "UPDATE admissions SET receipt_digest=?",
                ("a" * 64,),
            ),
            "receipt_blob_changed": (
                "UPDATE admissions SET receipt=?",
                (b"FORGED",),
            ),
            "row_removed": (
                "DELETE FROM admissions",
                (),
            ),
        }[fault]

        con = sqlite3.connect(db)

        try:
            con.execute(sql, args)
            con.commit()

        finally:
            con.close()


def exercise_faults(root, request_raw, cases_root):
    cases_root.mkdir(mode=0o700)

    verified = []

    for name, label, kind in FAULTS:
        case = cases_root / name
        case.mkdir(mode=0o700)

        db = case / "ledger.sqlite"
        receipt = case / "receipt.json"

        shutil.copyfile(
            root / (label + ".sqlite"),
            db,
        )

        shutil.copyfile(
            root / (label + "_receipt.json"),
            receipt,
        )

        fault_apply(
            db,
            receipt,
            kind,
        )

        try:
            audit(
                db,
                receipt,
                request_raw,
                label,
            )

        except (
            ValueError,
            sqlite3.DatabaseError,
            OSError,
            TypeError,
            KeyError,
        ):
            verified.append(name)

        else:
            raise AssertionError(
                "FAULT_ACCEPTED:" + name
            )

    need(len(verified) == 10, "FAULT_COUNT")

    return verified


def main(a):
    root = Path(a.synthetic)

    report47 = jsonfile(a.l47_report)
    val47 = jsonfile(a.l47_validation)
    contract47 = jsonfile(a.l47_contract)

    need(
        report47["schema"]
        == "TRUST_ROBOT_L47_SPLIT_REGISTRY_FALSIFICATION_V1",
        "L47_REPORT_SCHEMA",
    )

    need(
        report47["central_single_host_successes"] == 1
        and report47["central_single_host_replays_denied"] == 7
        and report47["split_registry_same_nonce_admissions"] == 2,
        "L47_RESULTS",
    )

    need(
        report47["globally_unique_admission_proven"] is False
        and contract47["cross_host_replay_security_verified"]
        is False,
        "L47_TRUST_LIMIT",
    )

    need(
        val47["rechecked_split_registries"] == 2
        and val47["globally_unique_admission_proven"] is False,
        "L47_VALIDATION",
    )

    request_raw = read_file(
        root / "synthetic_request.json"
    )

    need(
        sha_bytes(request_raw)
        == report47["request_sha256"],
        "L47_REQUEST_PIN",
    )

    baseline = [
        audit(
            root / (label + ".sqlite"),
            root / (label + "_receipt.json"),
            request_raw,
            label,
        )
        for label in LABELS
    ]

    for record, old in zip(
        baseline,
        [report47["central"], *report47["split"]],
    ):
        need(
            all(
                record[k] == old[k]
                for k in (
                    "session_id",
                    "nonce_sha256",
                    "database_sha256",
                    "receipt_sha256",
                )
            ),
            "L47_RECEIPT_LINEAGE",
        )

    decision = check_reconciliation(
        baseline,
        baseline,
    )

    rejected = mutations(baseline)

    fault_list = exercise_faults(
        root,
        request_raw,
        Path(a.out) / "fault_cases",
    )

    contract = {
        "schema":
            "TRUST_ROBOT_L48_OFFLINE_RECONCILIATION_CONTRACT_V1",
        "parent_commit": BASE,
        "source_sha256": sha(__file__),
        "l47_report_sha256": sha(a.l47_report),
        "l47_validation_sha256": sha(a.l47_validation),
        "authoritative_distributed_issuer_available": False,
        "independent_source_attestation_available": False,
        "globally_consistent_nonce_state_available": False,
        "conflict_resolution_authorized": False,
        "quarantine_policy": DENY,
        "required_future_evidence": [
            "authenticated independent source witness",
            "single authoritative or consensus-backed nonce ledger",
            "independent durable receipt publication",
            "physical timestamp and sensor provenance validation",
        ],
    }

    write(a.contract, contract)

    result = {
        "schema":
            "TRUST_ROBOT_L48_QUARANTINE_FALSIFICATION_V1",
        "contract_sha256": sha(a.contract),
        "source_sha256": sha(__file__),
        "l47_report_sha256": sha(a.l47_report),
        "l47_request_sha256": sha_bytes(request_raw),
        "ledgers": baseline,
        "verified_local_receipts": 3,
        "competing_isolated_registries": 2,
        "same_nonce_local_admissions": 3,
        "detected_duplicate_nonce": True,
        "quarantine_decision": decision,
        "automatic_reconciliation_performed": False,
        "capture_promotion_authorized": False,
        "live_capture_authorized": False,
        "event_source_provenance_verified": False,
        "globally_unique_nonce_proven": False,
        "metadata_mutations_rejected": rejected,
        "metadata_mutation_count": len(rejected),
        "ledger_faults_rejected": fault_list,
        "ledger_fault_count": len(fault_list),
        "real_sensor_measurements": 0,
        "scientific_pose_factors": 0,
        "health_labels": 0,
        "git_commit_or_push": False,
    }

    write(a.report, result)

    print("L48_LOCAL_LEDGER_RECEIPTS=3_VERIFIED")
    print("L48_TWO_ISOLATED_REGISTRIES=CONFLICT_DETECTED")
    print("L48_CONFLICT_DECISION=QUARANTINE_REVIEW_REQUIRED")
    print("L48_METADATA_FALSIFICATIONS=24_DENIED")
    print("L48_DATABASE_AND_RECEIPT_FAULTS=10_DENIED")
    print("L48_OFFLINE_RECONCILIATION=PASS")


if __name__ == "__main__":
    p = argparse.ArgumentParser()

    for arg in (
        "synthetic",
        "l47_report",
        "l47_validation",
        "l47_contract",
        "out",
        "contract",
        "report",
    ):
        p.add_argument(
            "--" + arg.replace("_", "-"),
            dest=arg,
            required=True,
        )

    main(p.parse_args())
