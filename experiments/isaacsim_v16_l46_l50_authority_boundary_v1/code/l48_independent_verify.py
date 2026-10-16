"""L48 second-process SQLite and quarantine verifier."""

import argparse
import hashlib
import json
import sqlite3

from pathlib import Path

import l48_reconcile as source


def need(ok, why):
    if not ok:
        raise AssertionError(why)


def digest(path):
    return hashlib.sha256(
        Path(path).read_bytes()
    ).hexdigest()


def jsonread(path):
    return json.loads(
        Path(path).read_text()
    )


def independent_read(db, receipt, raw, label):
    r = json.loads(raw)

    nonce = hashlib.sha256(
        bytes.fromhex(r["nonce_hex"])
    ).hexdigest()

    requesthash = hashlib.sha256(
        raw
    ).hexdigest()

    con = sqlite3.connect(
        "file:" + str(Path(db).resolve()) + "?mode=ro",
        uri=True,
    )

    try:
        con.execute("PRAGMA query_only=ON")

        need(
            con.execute("PRAGMA quick_check").fetchone()[0]
            == "ok",
            "SQLITE_BAD",
        )

        rows = con.execute(
            "SELECT nonce_hash,session_id,"
            "request_digest,receipt,receipt_digest "
            "FROM admissions"
        ).fetchall()

    finally:
        con.close()

    need(len(rows) == 1, "ROWS")

    n, sid, rd, body, hashdb = rows[0]

    need(
        n == nonce
        and sid == r["session_id"]
        and rd == requesthash,
        "IDENTITY",
    )

    need(
        isinstance(body, bytes)
        and hashlib.sha256(body).hexdigest() == hashdb,
        "BODY_HASH",
    )

    obj = json.loads(body)

    need(
        body == source.canon(obj),
        "CANONICAL_RECEIPT",
    )

    expected = source.expected_receipt(
        r,
        requesthash,
        nonce,
    )

    need(
        set(obj) == set(expected)
        and obj == expected,
        "RECEIPT_CONTENT",
    )

    need(
        body == Path(receipt).read_bytes(),
        "RECEIPT_EXPORT",
    )

    return {
        "label": label,
        "scope": "LOCAL_SQLITE_NOT_DISTRIBUTED",
        "session_id": sid,
        "nonce_sha256": nonce,
        "request_sha256": rd,
        "database_sha256": digest(db),
        "receipt_sha256": digest(receipt),
        "decision": "LOCALLY_ADMITTED",
        "origin_attested": False,
    }


def main(a):
    c = jsonread(a.contract)
    r = jsonread(a.report)

    need(
        c["schema"]
        == "TRUST_ROBOT_L48_OFFLINE_RECONCILIATION_CONTRACT_V1",
        "CONTRACT",
    )

    need(
        r["schema"]
        == "TRUST_ROBOT_L48_QUARANTINE_FALSIFICATION_V1",
        "REPORT",
    )

    need(
        c["source_sha256"]
        == r["source_sha256"]
        == digest(a.engine),
        "ENGINE_SHA",
    )

    need(
        c["l47_report_sha256"]
        == r["l47_report_sha256"]
        == digest(a.l47_report),
        "LINEAGE_REPORT",
    )

    need(
        c["l47_validation_sha256"]
        == digest(a.l47_validation),
        "LINEAGE_VALIDATION",
    )

    need(
        r["contract_sha256"] == digest(a.contract),
        "CONTRACT_SHA",
    )

    for flag in (
        "authoritative_distributed_issuer_available",
        "independent_source_attestation_available",
        "globally_consistent_nonce_state_available",
        "conflict_resolution_authorized",
    ):
        need(
            c[flag] is False,
            "MISSING_TRUST_BOUNDARY_" + flag,
        )

    for flag in (
        "automatic_reconciliation_performed",
        "capture_promotion_authorized",
        "live_capture_authorized",
        "event_source_provenance_verified",
        "globally_unique_nonce_proven",
        "git_commit_or_push",
    ):
        need(
            r[flag] is False,
            "FALSE_CLAIM_" + flag,
        )

    raw = (
        Path(a.synthetic) / "synthetic_request.json"
    ).read_bytes()

    source.request_check(raw)

    need(
        r["l47_request_sha256"]
        == digest(
            Path(a.synthetic) / "synthetic_request.json"
        ),
        "REQUEST_SHA",
    )

    rows = [
        independent_read(
            Path(a.synthetic) / (label + ".sqlite"),
            Path(a.synthetic) / (label + "_receipt.json"),
            raw,
            label,
        )
        for label in source.LABELS
    ]

    need(
        rows == r["ledgers"],
        "INDEPENDENT_ROWS",
    )

    need(
        len({
            x["nonce_sha256"]
            for x in rows
        }) == 1,
        "SAME_NONCE",
    )

    need(
        r["verified_local_receipts"] == 3
        and r["competing_isolated_registries"] == 2
        and r["same_nonce_local_admissions"] == 3,
        "COUNTS",
    )

    need(
        r["detected_duplicate_nonce"] is True
        and r["quarantine_decision"]
        == "QUARANTINE_REVIEW_REQUIRED",
        "QUARANTINE",
    )

    independent_controls = source.mutations(rows)

    need(
        independent_controls
        == r["metadata_mutations_rejected"]
        and r["metadata_mutation_count"] == 24,
        "CONTROL_NAMES",
    )

    need(
        r["ledger_fault_count"] == 10
        and [
            x[0] for x in source.FAULTS
        ] == r["ledger_faults_rejected"],
        "FAULT_NAMES",
    )

    for name, label, kind in source.FAULTS:
        case = (
            Path(a.out) / "fault_cases" / name
        )

        try:
            independent_read(
                case / "ledger.sqlite",
                case / "receipt.json",
                raw,
                label,
            )

        except (
            AssertionError,
            ValueError,
            sqlite3.DatabaseError,
            OSError,
            TypeError,
            KeyError,
        ):
            pass

        else:
            raise AssertionError(
                "INDEPENDENT_FAULT_ACCEPTED_" + name
            )

    for key in (
        "real_sensor_measurements",
        "scientific_pose_factors",
        "health_labels",
    ):
        need(
            type(r[key]) is int
            and r[key] == 0,
            "SCIENCE_ZERO_" + key,
        )

    validation = {
        "schema":
            "TRUST_ROBOT_L48_INDEPENDENT_VALIDATION_V1",
        "engine_sha256": digest(a.engine),
        "verifier_sha256": digest(__file__),
        "contract_sha256": digest(a.contract),
        "report_sha256": digest(a.report),
        "verified_local_receipts": 3,
        "verified_split_registry_conflict": True,
        "verified_quarantine_policy": True,
        "verified_mutations_denied": 24,
        "verified_ledger_faults_denied": 10,
        "global_replay_security_established": False,
        "physical_sensor_provenance_established": False,
        "simulator_launch_authorized": False,
        "new_sensor_measurements": 0,
        "scientific_pose_factors": 0,
        "health_labels": 0,
    }

    source.write(
        a.validation,
        validation,
    )

    print("L48_INDEPENDENT_LOCAL_RECEIPTS=3_VERIFIED")
    print("L48_INDEPENDENT_SPLIT_REGISTRY_CONFLICT=VERIFIED")
    print("L48_INDEPENDENT_FAULTS=10_DENIED")
    print("L48_INDEPENDENT_VALIDATION=PASS")


if __name__ == "__main__":
    p = argparse.ArgumentParser()

    for arg in (
        "engine",
        "synthetic",
        "out",
        "l47_report",
        "l47_validation",
        "contract",
        "report",
        "validation",
    ):
        p.add_argument(
            "--" + arg.replace("_", "-"),
            dest=arg,
            required=True,
        )

    main(p.parse_args())
