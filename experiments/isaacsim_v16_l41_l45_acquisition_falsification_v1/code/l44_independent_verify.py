"""Read-only L44 evidence and SQLite receipt verifier."""

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path
import l44_capture_boundary as b


def need(ok, message):
    if not ok:
        raise AssertionError(message)


def sha(path):
    return hashlib.sha256(
        Path(path).read_bytes()
    ).hexdigest()


def main(args):
    report = json.loads(
        Path(args.report).read_text()
    )

    need(
        report["schema"]
        == "TRUST_ROBOT_L44_SYNTHETIC_CAPTURE_BOUNDARY_VALIDATION_V1",
        "SCHEMA",
    )

    need(
        report["parent_commit"] == b.BASE
        and report["core_source_sha256"] == sha(args.core),
        "SOURCE",
    )

    need(
        report["test_source_sha256"] == sha(args.test)
        and report["l43_manifest_sha256"] == b.L43,
        "LINEAGE",
    )

    need(
        report["completed_cases"] == 1
        and report["partial_review_cases"] == 7,
        "COUNTS",
    )

    need(
        report["event_mutation_count"] == 36
        and len(set(report["event_mutations_rejected"])) == 36,
        "MUTATIONS",
    )

    need(
        report["fault_count"] == 8
        and len(set(report["faults_rejected"])) == 8,
        "FAULTS",
    )

    need(
        report["publication_recovery_verified"] is True,
        "RECOVERY",
    )

    for flag in (
        "actual_sensor_acquisition_binding",
        "simulator_launch_authorized",
        "physical_sync_verified",
        "git_changes_performed",
    ):
        need(
            report[flag] is False,
            "SCIENTIFIC_FLAG",
        )

    need(
        report["scientific_pose_factors"] == 0
        and report["health_labels"] == 0,
        "SCIENTIFIC_RESTRICTIONS",
    )

    root = Path(args.scenarios)

    for item in report["case_results"]:
        i = item["case"]
        folder = root / f"case_{i:02d}"

        db = folder / "session.sqlite"
        receipt = folder / "decision.json"

        need(
            sha(db) == item["database_sha256"]
            and sha(receipt) == item["receipt_sha256"],
            "FILE_DIGEST",
        )

        need(
            b.verify(db, receipt) == item["decision"],
            "SQLITE_RECEIPT_CHAIN",
        )

        connection = sqlite3.connect(
            f"file:{db.resolve()}?mode=ro",
            uri=True,
        )

        try:
            session = connection.execute(
                "SELECT id,nonce FROM session"
            ).fetchone()

            rows = [
                json.loads(value[0])
                for value in connection.execute(
                    "SELECT payload FROM events ORDER BY pos"
                )
            ]

            need(
                len(rows) == item["synthetic_event_count"],
                "EVENT_COUNT",
            )

            result, counts = b.assess(
                rows,
                *session,
            )

            need(
                result == item["decision"],
                "EVENT_INTEGRITY",
            )

            if i == 0:
                need(
                    counts == b.COUNTS,
                    "COMPLETE_SENSOR_COUNTS",
                )

        finally:
            connection.close()

    need(
        len(report["case_results"]) == 8,
        "CASE_COUNT",
    )

    result = {
        "schema":
            "TRUST_ROBOT_L44_INDEPENDENT_VALIDATION_V1",
        "core_sha256": sha(args.core),
        "test_sha256": sha(args.test),
        "verifier_sha256": sha(__file__),
        "report_sha256": sha(args.report),
        "verified_complete": 1,
        "verified_partial": 7,
        "verified_event_mutations": 36,
        "verified_faults": 8,
        "receipt_chains_verified": 8,
        "simulator_launch_authorized": False,
        "new_sensor_measurements": 0,
        "pose_factors_authorized": 0,
        "health_labels_generated": 0,
    }

    Path(args.validation).write_text(
        json.dumps(
            result,
            sort_keys=True,
            indent=2,
        ) + "\n"
    )

    print("L44_INDEPENDENT_VALIDATION=PASS")


if __name__ == "__main__":
    p = argparse.ArgumentParser()

    for name in (
        "core",
        "test",
        "report",
        "scenarios",
        "validation",
    ):
        p.add_argument("--" + name, required=True)

    main(p.parse_args())
