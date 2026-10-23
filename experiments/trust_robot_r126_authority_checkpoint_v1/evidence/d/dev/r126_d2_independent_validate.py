"""Independent R126-D2 evidence validator.

Uses only Python standard library. Does not import the authority,
fault-matrix generator or archived R122 implementation.
"""
import copy
import hashlib
import json
from pathlib import Path
import re
import sys

ACTIONS = ("cancel", "retire")
STAGES = (
    "candidate_create_pre",
    "candidate_create_post",
    "registry_pre",
    "registry_post",
    "receipt_pre",
    "receipt_post",
    "verification_pre",
    "verification_post",
    "publication_pre",
    "publication_post",
    "ack_pre",
)
POST = frozenset(("publication_post", "ack_pre"))
GENESIS = "0" * 64


def need(condition, reason):
    if not condition:
        raise ValueError("R126_D2_VALIDATION_FAIL:" + reason)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(
        (
            json.dumps(
                value, sort_keys=True,
                indent=2, allow_nan=False
            ) + "\n"
        ).encode("utf-8")
    ).hexdigest()


def chain(items, tip, kind):
    previous = GENESIS

    for ordinal, item in enumerate(items, 1):
        need(type(item) is dict, "CHAIN_ITEM_TYPE:" + kind)

        if kind != "retirement":
            need(
                item["ordinal"] == ordinal,
                "CHAIN_ORDINAL:" + kind,
            )

        need(
            item["previous_sha256"] == previous,
            "CHAIN_PREVIOUS:" + kind,
        )

        payload = {
            key: value
            for key, value in item.items()
            if key != "linked_sha256"
        }

        need(
            item["linked_sha256"] == digest(payload),
            "CHAIN_DIGEST:" + kind,
        )

        previous = item["linked_sha256"]

    need(previous == tip, "CHAIN_TIP:" + kind)


def evidence(row, action):
    retired = action == "retire"
    count = 2 if retired else 1

    need(
        row["phase"] == ("RETIRED" if retired else "CANCELLED"),
        "PHASE",
    )
    need(row["terminal_count"] == count, "TERMINAL_COUNT")
    need(row["active_count"] == (0 if retired else 1),
         "ACTIVE_COUNT")
    need(row["retired_count"] == int(retired),
         "RETIRED_COUNT")
    need(row["retirement_count"] == int(retired),
         "RETIREMENT_COUNT")
    need(row["denial_count"] == 1, "DENIAL_COUNT")

    terminals = row["terminal_receipts"]
    retirements = row["retirement_receipts"]
    denials = row["denial_receipts"]

    need(len(terminals) == count, "TERMINAL_LENGTH")
    need(len(retirements) == int(retired),
         "RETIREMENT_LENGTH")
    need(len(denials) == 1, "DENIAL_LENGTH")

    chain(terminals, row["terminal_tip"], "terminal")
    chain(retirements, row["retirement_tip"], "retirement")
    chain(denials, row["denial_tip"], "denial")

    need(
        denials[0]["reason"] == "OWNER_MISMATCH",
        "DENIAL_REASON",
    )

    for index, receipt in enumerate(terminals):
        need(
            receipt["event"] == (
                "terminal_cancel" if index == 0
                else "terminal_retire"
            ),
            "TERMINAL_EVENT",
        )
        need(
            receipt["acknowledged"] is False,
            "TERMINAL_INTERNAL_ACK",
        )

    first = terminals[0]
    need(first["before"]["phase"] == "ACTIVE",
         "CANCEL_BEFORE_PHASE")
    need(first["after"]["phase"] == "CANCELLED",
         "CANCEL_AFTER_PHASE")

    for field in (
        "attempted_work_units",
        "committed_work_units",
        "committed_digest",
    ):
        need(
            first["before"][field] == first["after"][field],
            "CANCEL_WORK_PRESERVATION:" + field,
        )

    if retired:
        last = terminals[1]
        receipt = retirements[0]

        need(last["terminal_phase"] == "CANCELLED",
             "RETIRE_TERMINAL_PHASE")
        need(receipt["terminal_phase"] == "CANCELLED",
             "RETIRE_REGISTRY_PHASE")
        need(receipt["retired"] is True,
             "RETIRE_RECEIPT_STATUS")
        need(
            last["issued_index"] == receipt["issued_index"],
            "RETIRE_INDEX_LINK",
        )
        for field in (
            "attempted_work_units",
            "committed_work_units",
            "committed_digest",
        ):
            need(
                last[field] == receipt[field],
                "RETIRE_WORK_LINK:" + field,
            )


def validate(report):
    need(type(report) is dict, "REPORT_TYPE")
    need(
        report["schema"]
        == "trust_robot_r126_d2_authority_fault_matrix_v1",
        "SCHEMA",
    )
    need(report["pass"] is True, "REPORT_PASS")
    need(report["actual_archived_r122_objects"] is True,
         "SOURCE_SCOPE")
    need(report["fault_cases"] == 22, "FAULT_COUNT")
    need(report["prepublication_cases"] == 18,
         "PREPUBLICATION_COUNT")
    need(
        report["postpublication_acknowledgement_ambiguities"]
        == 4,
        "POSTPUBLICATION_COUNT",
    )
    need(report["scientific_gates_closed"] == 11,
         "SCIENTIFIC_GATES")

    need(
        report["supported_api_exposes_raw_backend"] is False,
        "SUPPORTED_API_BOUNDARY",
    )
    need(
        report["private_backend_accessible_by_python_introspection"]
        is True,
        "INTROSPECTION_LIMITATION",
    )

    for field in (
        "arbitrary_python_mutation_prevented",
        "old_facade_revocation_proven",
        "exhaustive_alias_isolation_proven",
        "actual_r122_source_modified",
        "actual_r117_r122_atomicity_proven",
        "concurrent_linearizability_proven",
        "durable_recovery_proven",
        "cryptographic_authentication_proven",
        "physical_robot_safety_proven",
        "real_sensor_factors_executed",
        "sealed_confirmation_test_accessed",
    ):
        need(report[field] is False, "NONCLAIM:" + field)

    normal = report["normal_cases"]
    need(set(normal) == set(ACTIONS), "NORMAL_CASES")

    for action in ACTIONS:
        row = normal[action]
        need(row["action"] == action, "NORMAL_ACTION")
        need(row["acknowledged"] is True, "NORMAL_ACK")
        need(row["before_phase"] == (
            "ACTIVE" if action == "cancel" else "CANCELLED"
        ), "NORMAL_BEFORE_PHASE")
        evidence(row, action)

    rows = report["fault_witnesses"]
    need(type(rows) is list and len(rows) == 22,
         "FAULT_WITNESSES")

    expected_pairs = [
        (action, stage)
        for action in ACTIONS
        for stage in STAGES
    ]

    need(
        [(row["action"], row["stage"]) for row in rows]
        == expected_pairs,
        "FAULT_MATRIX_PAIRS",
    )

    for row in rows:
        action = row["action"]
        stage = row["stage"]
        post = stage in POST

        before_phase = (
            "ACTIVE" if action == "cancel" else "CANCELLED"
        )
        final_phase = (
            "CANCELLED" if action == "cancel" else "RETIRED"
        )
        before_count = 0 if action == "cancel" else 1
        final_count = 1 if action == "cancel" else 2

        need(row["exception_observed"] is True,
             "INJECTION_WITNESS")
        need(row["caller_acknowledged_at_fault"] is False,
             "FAULT_ACK")
        need(row["published_before_exception"] is post,
             "PUBLICATION_FLAG")
        need(
            row["published_observation_unchanged_at_fault"]
            is (not post),
            "OBSERVATION_FLAG",
        )
        need(row["pointer_unchanged_at_fault"] is (not post),
             "POINTER_FLAG")

        need(row["before_phase"] == before_phase,
             "BEFORE_PHASE")
        need(row["phase_at_fault"] == (
            final_phase if post else before_phase
        ), "FAULT_PHASE")
        need(row["before_terminal_count"] == before_count,
             "BEFORE_RECEIPT_COUNT")
        need(row["terminal_count_at_fault"] == (
            final_count if post else before_count
        ), "FAULT_RECEIPT_COUNT")

        need(
            (row["fault_observation_sha256"]
             == row["before_observation_sha256"])
            is (not post),
            "FAULT_OBSERVATION_HASH_BOUNDARY",
        )
        need(
            row["final_observation_sha256"]
            != row["before_observation_sha256"],
            "FINAL_NOT_PUBLISHED",
        )
        if post:
            need(
                row["final_observation_sha256"]
                == row["fault_observation_sha256"],
                "POSTFAULT_OBSERVATION_CHANGED",
            )

        need(
            row["recovery"] == (
                "duplicate_denied" if post
                else "safe_retry_succeeded"
            ),
            "RECOVERY_SEMANTICS",
        )

        evidence(row, action)

    return True


def negative_controls(report):
    # Receipt hash mutation must be independently detected.
    mutated = copy.deepcopy(report)
    mutated["normal_cases"]["cancel"][
        "terminal_receipts"
    ][0]["event"] = "tampered"
    try:
        validate(mutated)
    except ValueError:
        pass
    else:
        raise ValueError("NEGATIVE_TERMINAL_TAMPER_ACCEPTED")

    # Retirement ledger hash mutation must be independently detected.
    mutated = copy.deepcopy(report)
    mutated["normal_cases"]["retire"][
        "retirement_receipts"
    ][0]["committed_work_units"] = -100
    try:
        validate(mutated)
    except ValueError:
        pass
    else:
        raise ValueError("NEGATIVE_RETIREMENT_TAMPER_ACCEPTED")

    # False publication classification must be rejected.
    mutated = copy.deepcopy(report)
    mutated["fault_witnesses"][0][
        "published_before_exception"
    ] = True
    try:
        validate(mutated)
    except ValueError:
        pass
    else:
        raise ValueError("NEGATIVE_PUBLICATION_TAMPER_ACCEPTED")

    return 3


def main(dev, result):
    log = result / "r126_d2_unittest_v1.log"
    audit = result / "r126_d2_fault_audit_v1.json"
    destination = result / "r126_d2_independent_validation_v1.json"

    need(not destination.exists(), "DESTINATION_EXISTS")
    need(log.is_file() and audit.is_file(), "EVIDENCE_MISSING")

    text = log.read_text()
    need(
        re.search(r"(?m)^Ran 45 tests in ", text)
        is not None,
        "TEST_COUNT",
    )
    need(
        re.search(r"(?m)^OK$", text) is not None,
        "TEST_RESULT",
    )
    need(
        "FAILED" not in text and "Traceback" not in text,
        "TEST_LOG_ERRORS",
    )

    report = json.loads(audit.read_text())
    validate(report)

    controls = negative_controls(report)

    names = (
        "r126_single_authority.py",
        "r126_single_authority_contract_v1.md",
        "test_r126_authority.py",
        "r126_d2_fault_matrix.py",
        "test_r126_authority_faults.py",
        "r126_d2_fault_matrix_contract_v1.md",
        "r126_d2_independent_validate.py",
    )

    for name in names:
        need((dev / name).is_file(), "SOURCE_MISSING:" + name)

    evidence = {
        "schema": "trust_robot_r126_d2_independent_validation_v1",
        "pass": True,
        "validator_imported_engine": False,
        "total_unit_tests_passed": 45,
        "d1_unit_tests_retained": 11,
        "new_d2_unit_tests_passed": 34,
        "fault_witnesses_verified": 22,
        "prepublication_cases_verified": 18,
        "postpublication_ambiguities_verified": 4,
        "terminal_denial_retirement_chains_verified": True,
        "negative_controls_passed": controls,
        "private_python_introspection_still_possible": True,
        "actual_r117_r122_atomicity_proven": False,
        "concurrent_or_durable_safety_proven": False,
        "scientific_gates_closed": 11,
        "audit_sha256": sha(audit),
        "test_log_sha256": sha(log),
        "source_sha256": {
            name: sha(dev / name)
            for name in names
        },
    }

    with destination.open("x", encoding="utf-8") as f:
        json.dump(evidence, f, indent=2, sort_keys=True)
        f.write("\n")

    print("R126_D2_INDEPENDENT_VALIDATION=PASS")
    print("R126_D2_UNIT_TESTS=45_PASS")
    print("R126_D2_FAULT_WITNESSES=22_PASS")
    print("R126_D2_PREPUBLICATION=18_PASS")
    print("R126_D2_POSTPUBLICATION=4_PASS")
    print("R126_D2_RECEIPT_RECONSTRUCTION=PASS")
    print("R126_D2_NEGATIVE_CONTROLS=3_PASS")
    print("R126_D2_REAL_R117_R122_ATOMICITY=NOT_PROVEN")
    print("R126_D2_SCIENTIFIC_GATES=11_CLOSED")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Usage: validator DEV RESULT")
    main(Path(sys.argv[1]), Path(sys.argv[2]))
