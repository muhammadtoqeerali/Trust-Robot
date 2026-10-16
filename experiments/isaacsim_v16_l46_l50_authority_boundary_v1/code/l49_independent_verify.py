"""L49 read-only verification of synthetic quarantine evidence."""

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path

import l49_recovery as core


def need(ok, msg):
    if not ok:
        raise AssertionError(msg)


def sha(path):
    return hashlib.sha256(
        Path(path).read_bytes()
    ).hexdigest()


def read(path):
    return json.loads(
        Path(path).read_text()
    )


def main(a):
    contract = read(a.contract)
    report = read(a.report)

    need(
        contract["schema"]
        == "TRUST_ROBOT_L49_AUTHORITY_FAILURE_CONTRACT_V1"
        and report["schema"]
        == "TRUST_ROBOT_L49_AUTHORITY_FAILURE_FALSIFICATION_V1",
        "SCHEMAS",
    )

    need(
        contract["engine_sha256"]
        == report["engine_sha256"]
        == sha(a.engine),
        "ENGINE_PIN",
    )

    need(
        contract["l47_report_sha256"]
        == sha(a.l47_report),
        "L47_PIN",
    )

    need(
        contract["l48_report_sha256"]
        == report["l48_report_sha256"]
        == sha(a.l48_report),
        "L48_PIN",
    )

    need(
        contract["l48_validation_sha256"]
        == sha(a.l48_validation),
        "L48_VALIDATION_PIN",
    )

    need(
        report["contract_sha256"] == sha(a.contract),
        "CONTRACT_BIND",
    )

    need(
        contract["policy"] == core.DENY,
        "QUARANTINE_POLICY",
    )

    records, requesthash = core.sources(
        a.l47_synthetic,
        a.l47_report,
        a.l48_report,
    )

    need(
        records == report["source_ledgers"]
        and requesthash == report["l47_request_sha256"],
        "SOURCE_RECOMPUTATION",
    )

    need(
        core.matrix(records) == report["scenarios"]
        and report["scenario_count"]
        == report["quarantine_decisions"]
        == 18,
        "MATRIX",
    )

    need(
        report["negative_claims_rejected"]
        == core.negative_claims(
            core.receipt_body(
                "A" * 64,
                "B" * 64,
                records,
            )
        )
        and report["negative_claim_count"] == 12,
        "UNTRUSTED_PROMOTIONS",
    )

    need(
        report["recovery_windows"] == [
            "commit_before_publication",
            "file_before_mark",
            "idempotent_republish",
        ],
        "RECOVERY_LIST",
    )

    need(
        report["receipt_fault_names"] == list(core.FAULTS)
        and report["receipt_fault_count"] == 10,
        "FAULT_LIST",
    )

    for name in (
        "issuer_authenticated_externally",
        "independent_witness_present",
        "global_nonce_ledger_present",
        "automatic_reconciliation_authorized",
        "real_power_failure_tested",
        "trusted_clock_proven",
    ):
        need(
            contract[name] is False,
            "CONTRACT_FALSE_CLAIM:" + name,
        )

    for name in (
        "global_replay_prevention_verified",
        "physical_witness_verified",
        "real_power_failure_tested",
        "autonomous_merge_performed",
        "git_push_performed",
    ):
        need(
            report[name] is False,
            "FALSE_CLAIM:" + name,
        )

    for name in (
        "new_sensor_measurements",
        "scientific_pose_factors",
        "health_labels",
    ):
        need(
            type(report[name]) is int
            and report[name] == 0,
            "SCIENTIFIC_GATE:" + name,
        )

    root = Path(a.session)

    def audit_journal(db, receipt):
        p = Path(db)

        need(
            p.is_file() and not p.is_symlink(),
            "JOURNAL_FILE",
        )

        con = sqlite3.connect(
            "file:" + str(p.resolve()) + "?mode=ro",
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
                "SELECT id,state,nonce_sha,report_sha,"
                "receipt,receipt_sha,published FROM decision"
            ).fetchall()

        finally:
            con.close()

        need(
            len(rows) == 1,
            "EXACTLY_ONE_JOURNAL_ROW",
        )

        rid, state, nonce, reporthash, body, digest, mark = rows[0]

        expected = {
            "schema":
                "TRUST_ROBOT_L49_QUARANTINE_RECEIPT_V1",
            "parent_commit": core.BASE,
            "state": core.DENY,
            "contract_sha256": sha(a.contract),
            "report_sha256": sha(a.report),
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

        raw = (
            json.dumps(
                expected,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ) + "\n"
        ).encode()

        need(
            rid == 1
            and state == core.DENY
            and nonce == expected["nonce_sha256"]
            and reporthash == sha(a.report),
            "STATE_LINK",
        )

        need(
            type(body) is bytes
            and body == raw
            and hashlib.sha256(body).hexdigest() == digest,
            "BYTE_EXACT_JOURNAL",
        )

        need(
            mark == 1,
            "NOT_PUBLISHED",
        )

        ep = Path(receipt)

        need(
            ep.is_file()
            and not ep.is_symlink()
            and ep.read_bytes() == raw,
            "BAD_EXPORTED_RECEIPT",
        )

        return True

    for folder in (
        root,
        root / "file_before_mark",
        root / "commit_before_publication",
    ):
        need(
            audit_journal(
                folder / "quarantine.sqlite",
                folder / "quarantine_receipt.json",
            ),
            "EXPORTED_JOURNAL",
        )

    for name in core.FAULTS:
        folder = root / ("fault_" + name)

        try:
            audit_journal(
                folder / "quarantine.sqlite",
                folder / "quarantine_receipt.json",
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
                "FAULT_ALLOWED:" + name
            )

    data = {
        "schema":
            "TRUST_ROBOT_L49_INDEPENDENT_VALIDATION_V1",
        "engine_sha256": sha(a.engine),
        "verifier_sha256": sha(__file__),
        "contract_sha256": sha(a.contract),
        "report_sha256": sha(a.report),
        "verified_source_ledgers": 3,
        "verified_outage_scenarios": 18,
        "verified_false_promotions": 12,
        "verified_publication_paths": 3,
        "verified_fault_denials": 10,
        "global_replay_security_verified": False,
        "physical_source_witness_verified": False,
        "real_power_loss_durability_verified": False,
        "live_simulator_launch_authorized": False,
        "new_sensor_measurements": 0,
        "scientific_pose_factors": 0,
        "health_labels": 0,
    }

    core.save(a.validation, data)

    print("L49_INDEPENDENT_LEDGER_LINEAGE=3_VERIFIED")
    print("L49_INDEPENDENT_OUTAGE_CASES=18_QUARANTINED")
    print("L49_INDEPENDENT_FAULT_CASES=10_DENIED")
    print("L49_INDEPENDENT_VALIDATION=PASS")


if __name__ == "__main__":
    p = argparse.ArgumentParser()

    for field in (
        "engine",
        "l47_synthetic",
        "l47_report",
        "l48_report",
        "l48_validation",
        "session",
        "contract",
        "report",
        "validation",
    ):
        p.add_argument(
            "--" + field.replace("_", "-"),
            dest=field,
            required=True,
        )

    main(p.parse_args())
