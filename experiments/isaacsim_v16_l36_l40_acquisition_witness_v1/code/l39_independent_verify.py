"""Independent L39 report and frozen SQLite baseline verification."""

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path


def sha(path):
    return hashlib.sha256(
        Path(path).read_bytes()
    ).hexdigest()


def need(value, message):
    if not value:
        raise ValueError(message)


def main(args):
    source = Path(args.source)
    report_path = Path(args.report)
    db_path = Path(args.db)

    report = json.loads(
        report_path.read_text(encoding="utf-8")
    )

    need(
        report["schema"]
        == "TRUST_ROBOT_L39_CRASH_WINDOW_RECOVERY_ASSESSMENT_V1",
        "Report schema",
    )

    need(
        report["parent_git_commit"]
        == "0b542e8644f3c4b98ed92c0f83a7c82a4635ae52",
        "Git lineage",
    )

    need(
        report["implementation_sha256"]
        == sha(source),
        "Implementation lineage",
    )

    expected_inputs = {
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

    need(
        report["input_sha256"]
        == expected_inputs,
        "Input provenance",
    )

    need(
        sha(db_path) == expected_inputs["db"],
        "Original registry modified",
    )

    cases = report["simulated_failure_cases"]

    expected = {
        "sealed_complete": "VERIFIED_SEALED",
        "issued_after_commit": "ISSUED_REVIEW_REQUIRED",
        "issued_missing_challenge": "QUARANTINED",
        "issued_unexpected_admission": "QUARANTINED",
        "issued_wrong_nonce": "QUARANTINED",
        "admitted_receipt_present": "ADMITTED_REVIEW_REQUIRED",
        "admitted_receipt_missing": "QUARANTINED",
        "admitted_wrong_hash": "QUARANTINED",
        "admitted_unexpected_seal": "QUARANTINED",
        "sealed_receipt_missing": "QUARANTINED",
        "sealed_wrong_hash": "QUARANTINED",
        "sealed_admission_missing": "QUARANTINED",
        "sealed_challenge_missing": "QUARANTINED",
        "sealed_receipt_tampered": "QUARANTINED",
        "sealed_challenge_tampered": "QUARANTINED",
        "sealed_admission_tampered": "QUARANTINED",
        "registry_missing": "QUARANTINED",
        "registry_corrupted": "QUARANTINED",
        "registry_no_sessions": "QUARANTINED",
        "registry_extra_session": "QUARANTINED",
    }

    need(
        report["case_count"] == len(cases) == 20,
        "Scenario count",
    )

    need(
        {row["case"] for row in cases}
        == set(expected),
        "Scenario coverage",
    )

    for row in cases:
        need(
            row["expected"]
            == row["observed"]
            == expected[row["case"]],
            "Scenario mismatch",
        )

        need(
            row["live_launch_allowed"] is False
            and row["automatic_repair_allowed"]
            is False,
            "Unsafe recovery",
        )

    need(
        report["decision_counts"] == {
            "VERIFIED_SEALED": 1,
            "ISSUED_REVIEW_REQUIRED": 1,
            "ADMITTED_REVIEW_REQUIRED": 1,
            "QUARANTINED": 17,
        },
        "Decision distribution",
    )

    db = sqlite3.connect(
        "file:" + str(db_path.resolve()) + "?mode=ro",
        uri=True,
    )

    try:
        db.execute("PRAGMA query_only=ON")

        need(
            db.execute(
                "PRAGMA quick_check"
            ).fetchone()[0] == "ok",
            "Original SQLite integrity",
        )

        rows = db.execute(
            """
            SELECT stage, admission_sha, seal_sha
            FROM sessions
            """
        ).fetchall()

    finally:
        db.close()

    need(len(rows) == 1, "Original registry size")
    need(rows[0][0] == "SEALED", "Original registry state")

    need(
        rows[0][1] == expected_inputs["admission"]
        and rows[0][2] == expected_inputs["seal"],
        "Original registry receipt bindings",
    )

    for key in (
        "replay_after_consumption_permitted",
        "automatic_receipt_recreation_permitted",
        "automatic_database_rollback_permitted",
        "live_simulator_launch_authorized",
        "real_power_failure_experiment_performed",
        "database_power_loss_durability_qualified",
        "tamper_resistant_storage_verified",
        "independent_source_authenticity_verified",
        "physical_exposure_sync_verified",
        "independent_6dof_reference_verified",
        "historical_inputs_modified",
        "git_commit_or_push_performed",
    ):
        need(
            report[key] is False,
            "Invalid scientific or recovery claim: " + key,
        )

    need(
        report["pose_factors_authorized"] == 0
        and report["health_labels_generated"] == 0
        and report["new_sensor_acquisitions"] == 0,
        "Scientific admission",
    )

    result = {
        "schema":
            "TRUST_ROBOT_L39_INDEPENDENT_VALIDATION_V1",
        "parent_git_commit":
            "0b542e8644f3c4b98ed92c0f83a7c82a4635ae52",
        "assessment_source_sha256": sha(source),
        "verifier_source_sha256": sha(__file__),
        "assessment_report_sha256": sha(report_path),
        "frozen_l38_database_sha256": sha(db_path),
        "verified_case_count": 20,
        "verified_quarantine_cases": 17,
        "baseline_registry_state": "SEALED",
        "fail_closed_policy_verified": True,
        "live_launch_authorized": False,
        "power_loss_durability_verified": False,
        "pose_factors_authorized": 0,
        "health_labels_generated": 0,
    }

    with Path(args.output).open(
        "x", encoding="utf-8"
    ) as stream:
        json.dump(
            result,
            stream,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        stream.write("\n")

    print("L39_INDEPENDENT_SCENARIO_VALIDATION=PASS")
    print("L39_FROZEN_SQLITE_INTEGRITY=PASS")
    print("L39_SCIENTIFIC_RESTRICTIONS=ENFORCED")
    print("L39_INDEPENDENT_VALIDATION=PASS")


if __name__ == "__main__":
    p = argparse.ArgumentParser()

    for name in (
        "source", "report", "db", "output"
    ):
        p.add_argument("--" + name, required=True)

    main(p.parse_args())
