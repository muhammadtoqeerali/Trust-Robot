"""L47 separately executed SQLite and receipt verifier.

Software-only verification. No independently trusted physical witness.
"""

import argparse
import hashlib
import json
import sqlite3

from pathlib import Path

import l47_ledger as core


def sha(path):
    return hashlib.sha256(
        Path(path).read_bytes()
    ).hexdigest()


def need(cond, msg):
    if not cond:
        raise AssertionError(msg)


def independent_audit(db, request_file, receipt_file):
    for name in (
        db,
        request_file,
        receipt_file,
    ):
        p = Path(name)

        need(
            p.is_file() and not p.is_symlink(),
            "UNSAFE_INPUT",
        )

    request_bytes = Path(
        request_file
    ).read_bytes()

    r = json.loads(request_bytes)

    need(
        type(r) is dict
        and request_bytes == core.canonical(r),
        "REQUEST_BYTES",
    )

    need(
        r["schema"] == "TRUST_ROBOT_L47_TEST_REQUEST_V1",
        "REQUEST_SCHEMA",
    )

    nonce = hashlib.sha256(
        bytes.fromhex(r["nonce_hex"])
    ).hexdigest()

    request_digest = hashlib.sha256(
        request_bytes
    ).hexdigest()

    c = sqlite3.connect(
        f"file:{Path(db).resolve()}?mode=ro",
        uri=True,
    )

    try:
        c.execute("PRAGMA query_only=ON")

        need(
            c.execute(
                "PRAGMA quick_check"
            ).fetchone()[0] == "ok",
            "DB_QUICK_CHECK",
        )

        rows = c.execute(
            "SELECT nonce_hash,session_id,request_digest,"
            "receipt,receipt_digest FROM admissions"
        ).fetchall()

    finally:
        c.close()

    need(
        len(rows) == 1,
        "ROW_COUNT",
    )

    n, sid, req_digest, body, digest = rows[0]

    need(
        n == nonce
        and sid == r["session_id"]
        and req_digest == request_digest,
        "ROW_BINDING",
    )

    expected = {
        "schema":
            "TRUST_ROBOT_L47_LOCAL_ADMISSION_RECEIPT_V1",
        "session_id": r["session_id"],
        "nonce_sha256": nonce,
        "request_sha256": request_digest,
        "candidate_sha256": core.CAND,
        "l46_report_sha256": core.L46_REPORT,
        "parent_commit": core.BASE,
        "decision": "LOCALLY_ADMITTED",
        "independent_physical_witness": False,
        "cross_host_replay_qualified": False,
        "new_sensor_measurements": 0,
        "pose_factors_authorized": 0,
        "health_labels_generated": 0,
    }

    expected_bytes = (
        json.dumps(
            expected,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ) + "\n"
    ).encode()

    need(
        type(body) is bytes
        and body == expected_bytes
        and hashlib.sha256(body).hexdigest() == digest,
        "BYTE_EXACT_RECEIPT",
    )

    need(
        Path(receipt_file).read_bytes() == expected_bytes,
        "EXPORTED_RECEIPT",
    )

    return {
        "nonce_sha256": nonce,
        "session_id": sid,
        "database_sha256": sha(db),
        "receipt_sha256": sha(receipt_file),
    }


def main(a):
    c = json.loads(
        Path(a.contract).read_text()
    )

    r = json.loads(
        Path(a.report).read_text()
    )

    need(
        c["schema"]
        == "TRUST_ROBOT_L47_SINGLE_HOST_NONCE_AUTHORITY_CONTRACT_V1",
        "CONTRACT",
    )

    need(
        r["schema"]
        == "TRUST_ROBOT_L47_SPLIT_REGISTRY_FALSIFICATION_V1",
        "REPORT",
    )

    need(
        c["parent_commit"] == core.BASE
        and c["engine_sha256"] == sha(a.engine),
        "ENGINE_PIN",
    )

    need(
        r["contract_sha256"] == sha(a.contract)
        and r["engine_sha256"] == sha(a.engine),
        "REPORT_PINS",
    )

    need(
        c["l46_contract_sha256"] == sha(a.l46_contract)
        and c["l46_report_sha256"] == sha(a.l46_report)
        and c["l46_validation_sha256"] == sha(a.l46_validation),
        "L46_LINEAGE",
    )

    req = Path(a.synthetic) / "synthetic_request.json"

    request = json.loads(
        req.read_text()
    )

    need(
        core.canonical(request) == req.read_bytes()
        and core.request_validate(request),
        "REQUEST_CANONICAL",
    )

    need(
        r["request_sha256"] == sha(req),
        "REQUEST_SHA",
    )

    independently_blocked = []

    for name, modified, tick in core.invalid_requests(request):
        try:
            core.request_validate(
                modified,
                expected=(
                    request["session_id"],
                    request["nonce_hex"],
                ),
                tick=tick,
            )

        except (
            ValueError,
            TypeError,
            KeyError,
        ):
            independently_blocked.append(name)

        else:
            raise AssertionError(
                "MUTATION_ACCEPTED:" + name
            )

    need(
        independently_blocked
        == r["invalid_request_controls_rejected"]
        and r["invalid_request_control_count"] == 20,
        "NEGATIVE_CONTROLS",
    )

    results = []

    for dbname, receiptname in (
        ("central.sqlite", "central_receipt.json"),
        ("split_left.sqlite", "split_left_receipt.json"),
        ("split_right.sqlite", "split_right_receipt.json"),
    ):
        summary = independent_audit(
            Path(a.synthetic) / dbname,
            req,
            Path(a.synthetic) / receiptname,
        )

        results.append(summary)

    need(
        results[0] == r["central"]
        and results[1:] == r["split"],
        "DB_RECEIPT_RECOMPUTE",
    )

    need(
        results[0]["nonce_sha256"]
        == results[1]["nonce_sha256"]
        == results[2]["nonce_sha256"],
        "SPLIT_NONCE",
    )

    need(
        r["central_single_host_successes"] == 1
        and r["central_single_host_replays_denied"] == 7
        and r["split_registry_same_nonce_admissions"] == 2,
        "ADMISSION_COUNTS",
    )

    need(
        r["split_registry_detected_unsafe"]
        == "DUPLICATE_NONCE_REQUIRES_QUARANTINE"
        and r["globally_unique_admission_proven"] is False,
        "GLOBAL_LIMITATION",
    )

    fault_names = [
        "receipt_missing",
        "receipt_altered",
        "db_receipt_payload",
        "db_receipt_digest",
        "db_nonce",
        "db_session",
        "db_request_digest",
        "db_row_deleted",
    ]

    need(
        r["faults_rejected"] == fault_names
        and r["fault_count"] == 8,
        "FAULT_LIST",
    )

    for name in fault_names:
        folder = Path(a.synthetic) / (
            "fault_" + name
        )

        try:
            independent_audit(
                folder / "ledger.sqlite",
                req,
                folder / "receipt.json",
            )

        except (
            AssertionError,
            ValueError,
            sqlite3.DatabaseError,
            OSError,
            KeyError,
            TypeError,
        ):
            pass

        else:
            raise AssertionError(
                "FAULT_RECHECK_ACCEPTED:" + name
            )

    for flag in (
        "issuer_independently_trusted",
        "quorum_or_distributed_consensus_implemented",
        "cross_host_replay_security_verified",
        "trusted_clock_established",
        "independent_sensor_provenance_established",
        "live_simulator_launch_authorized",
    ):
        need(
            c[flag] is False,
            "CONTRACT_FALSE_CLAIM:" + flag,
        )

    for flag in (
        "globally_unique_admission_proven",
        "synthetic_request_issuer_trusted",
        "physical_source_authenticity_verified",
        "live_simulator_launch_authorized",
        "git_commit_or_push",
    ):
        need(
            r[flag] is False,
            "REPORT_FALSE_CLAIM:" + flag,
        )

    for field in (
        "new_sensor_measurements",
        "pose_factors_authorized",
        "health_labels_generated",
    ):
        need(
            r[field] == 0,
            "SCIENCE_ZERO:" + field,
        )

    result = {
        "schema":
            "TRUST_ROBOT_L47_INDEPENDENT_VALIDATION_V1",
        "engine_sha256": sha(a.engine),
        "verifier_sha256": sha(__file__),
        "contract_sha256": sha(a.contract),
        "report_sha256": sha(a.report),
        "request_sha256": sha(req),
        "rechecked_central_admissions": 1,
        "rechecked_central_replays_denied": 7,
        "rechecked_split_registries": 2,
        "rechecked_bad_request_controls": 20,
        "rechecked_ledger_faults": 8,
        "globally_unique_admission_proven": False,
        "trusted_independent_source_origin_proven": False,
        "live_simulator_launch_authorized": False,
        "new_sensor_measurements": 0,
        "pose_factors_authorized": 0,
        "health_labels_generated": 0,
    }

    core.jsonsave(
        a.validation,
        result,
    )

    print("L47_INDEPENDENT_LEDGER_RECEIPTS=3_VERIFIED")
    print("L47_INDEPENDENT_NEGATIVE_CONTROLS=20_REJECTED")
    print("L47_INDEPENDENT_FAULT_CHECKS=8_REJECTED")
    print("L47_INDEPENDENT_VALIDATION=PASS")


if __name__ == "__main__":
    p = argparse.ArgumentParser()

    for n in (
        "engine",
        "contract",
        "report",
        "validation",
        "synthetic",
        "l46_contract",
        "l46_report",
        "l46_validation",
    ):
        p.add_argument(
            "--" + n.replace("_", "-"),
            dest=n,
            required=True,
        )

    main(
        p.parse_args()
    )
