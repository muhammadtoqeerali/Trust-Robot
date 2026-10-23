"""R126 independent JSON/receipt validator; does not import R126 engine."""
import copy
import hashlib
import json
from pathlib import Path
import re
import sys

ACTIONS = ("cancel", "retire")
STAGES = (
    "registry_pre", "registry_post",
    "receipt_pre", "receipt_post",
    "publication_post",
)


def need(ok, reason):
    if not ok:
        raise ValueError("R126_VALIDATION_FAIL:" + reason)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def receipt_digest(payload):
    encoded = (
        json.dumps(
            payload, sort_keys=True,
            indent=2, allow_nan=False
        ) + "\n"
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate(report):
    need(type(report) is dict, "REPORT_TYPE")
    need(report.get("schema") ==
         "trust_robot_r126_identity_shadow_feasibility_v1",
         "REPORT_SCHEMA")
    need(report.get("pass") is True, "REPORT_PASS")
    need(report.get("fault_count") == 10, "FAULT_COUNT")
    need(report.get("prepublication_faults") == 8,
         "PREPUBLICATION_COUNT")
    need(report.get("postpublication_ack_ambiguities") == 2,
         "POSTPUBLICATION_COUNT")
    need(report.get("scientific_gates_closed") == 11,
         "SCIENTIFIC_GATES")

    need(report.get("original_facades_unchanged") is True,
         "ORIGINAL_REFERENCE_ASSERTION")
    need(report.get("external_old_references_remain_usable") is True,
         "OLD_REFERENCE_LIMITATION")
    need(report.get("all_mutable_aliases_exhaustively_excluded") is False,
         "ALIAS_EXHAUSTIVENESS_NONCLAIM")

    for field in (
        "actual_r122_source_modified",
        "drop_in_atomic_backend_proven",
        "concurrent_publication_proven",
        "durable_crash_recovery_proven",
        "physical_safety_proven",
        "real_sensor_factors_executed",
        "confirmation_test_accessed",
    ):
        need(report.get(field) is False, "NONCLAIM:" + field)

    expected = [
        (action, stage)
        for action in ACTIONS
        for stage in STAGES
    ]

    rows = report.get("fault_witnesses")
    need(type(rows) is list and len(rows) == 10,
         "WITNESS_TYPE_COUNT")

    need(
        [(x.get("action"), x.get("stage")) for x in rows]
        == expected,
        "WITNESS_MATRIX",
    )

    for row in rows:
        post = row["stage"] == "publication_post"

        need(row["published_before_exception"] is post,
             "PUBLICATION_BOUNDARY")
        need(row["caller_acknowledged"] is False,
             "FAULT_ACKNOWLEDGEMENT")
        need(row["visible_state_unchanged_at_fault"] is (not post),
             "FAULT_OBSERVATION")
        need(row["old_reference_unchanged"] is True,
             "OLD_REFERENCE_CHANGED")

        need(
            row["recovery"] == (
                "duplicate_denied" if post
                else "safe_retry_succeeded"
            ),
            "FAULT_RECOVERY",
        )

        need(
            row["final_terminal_receipts"] == (
                1 if row["action"] == "cancel" else 2
            ),
            "FINAL_RECEIPT_COUNT",
        )

    normal = report.get("normal_cases")
    need(type(normal) is dict and set(normal) == set(ACTIONS),
         "NORMAL_CASES")

    for action in ACTIONS:
        row = normal[action]

        need(row["acknowledged"] is True,
             "NORMAL_ACK")
        need(row["original_reference_unchanged"] is True,
             "ORIGINAL_CHANGED")
        need(row["old_reference_remains_accessible"] is True,
             "OLD_REF_NONCLAIM")

        expected_count = 1 if action == "cancel" else 2

        need(row["terminal_receipt_count"] == expected_count,
             "NORMAL_RECEIPT_COUNT")

        need(
            row["registry_active_count"] == (
                1 if action == "cancel" else 0
            ),
            "ACTIVE_REGISTRY_COUNT",
        )
        need(
            row["registry_retired_count"] == (
                0 if action == "cancel" else 1
            ),
            "RETIRED_REGISTRY_COUNT",
        )

        receipts = row["terminal_receipts"]

        need(type(receipts) is list
             and len(receipts) == expected_count,
             "NORMAL_RECEIPT_LIST")

        previous = "0" * 64

        for index, item in enumerate(receipts):
            need(
                item["event"] == (
                    "terminal_cancel"
                    if index == 0 else "terminal_retire"
                ),
                "RECEIPT_EVENT",
            )

            payload = {
                k: v for k, v in item.items()
                if k != "linked_sha256"
            }

            need(item["previous_sha256"] == previous,
                 "RECEIPT_PREVIOUS")
            need(
                item["linked_sha256"] == receipt_digest(payload),
                "RECEIPT_DIGEST",
            )

            previous = item["linked_sha256"]

        need(row["terminal_chain_tip"] == previous,
             "TERMINAL_CHAIN_TIP")

    return True


def negative_controls(report):
    damaged = copy.deepcopy(report)
    damaged["normal_cases"]["retire"][
        "terminal_receipts"
    ][-1]["committed_work_units"] = -999

    try:
        validate(damaged)
    except ValueError:
        pass
    else:
        raise ValueError("RECEIPT_TAMPER_NOT_DETECTED")

    damaged = copy.deepcopy(report)
    damaged["fault_witnesses"][0][
        "published_before_exception"
    ] = True

    try:
        validate(damaged)
    except ValueError:
        pass
    else:
        raise ValueError("FAULT_TAMPER_NOT_DETECTED")

    return 2


def main(dev, result):
    log = result / "r126_unittest_v1.log"
    report_path = result / "r126_identity_shadow_audit_v1.json"
    destination = result / "r126_independent_validation_v1.json"

    need(not destination.exists(), "VALIDATION_ALREADY_EXISTS")
    need(log.is_file() and report_path.is_file(),
         "EVIDENCE_MISSING")

    raw_log = log.read_text()
    need(
        re.search(r"(?m)^Ran 18 tests in ", raw_log)
        is not None,
        "UNIT_TEST_COUNT",
    )
    need(
        re.search(r"(?m)^OK$", raw_log)
        is not None,
        "UNIT_TEST_FAILURE",
    )
    need("FAILED" not in raw_log and "Traceback" not in raw_log,
         "UNIT_LOG_ERRORS")

    report = json.loads(report_path.read_text())

    validate(report)
    controls = negative_controls(report)

    sources = [
        "r126_identity_shadow.py",
        "test_r126.py",
        "r126_identity_shadow_contract_v1.md",
        "r126_identity_shadow_before_b1_fix_v1.txt",
        "r126_independent_validate.py",
    ]

    for name in sources:
        need((dev / name).is_file(),
             "SOURCE_MISSING:" + name)

    validation = {
        "schema": "trust_robot_r126_independent_validation_v1",
        "pass": True,
        "validator_does_not_import_engine": True,
        "unit_tests_passed": 18,
        "fault_cases_verified": 10,
        "prepublication_cases_verified": 8,
        "postpublication_ambiguities_verified": 2,
        "terminal_receipt_chains_verified": True,
        "negative_controls_passed": controls,
        "original_failed_log_preserved": True,
        "scientific_gates_closed": 11,
        "actual_backend_atomicity_proven": False,
        "concurrent_or_durable_safety_proven": False,
        "audit_sha256": sha(report_path),
        "unit_log_sha256": sha(log),
        "source_sha256": {
            name: sha(dev / name) for name in sources
        },
    }

    with destination.open("x", encoding="utf-8") as f:
        json.dump(validation, f, indent=2, sort_keys=True)
        f.write("\n")

    print("R126_INDEPENDENT_VALIDATION=PASS")
    print("R126_UNIT_TESTS=18_PASS")
    print("R126_FAULT_MATRIX=10_PASS")
    print("R126_RECEIPT_CHAINS=PASS")
    print("R126_NEGATIVE_CONTROLS=2_PASS")
    print("R126_BACKEND_ATOMICITY=NOT_PROVEN")
    print("R126_SCIENTIFIC_GATES=11_CLOSED")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Usage: validator DEV_DIR RESULT_DIR")
    main(Path(sys.argv[1]), Path(sys.argv[2]))
