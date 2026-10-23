#!/usr/bin/env python3
"""Standalone SHA256, lineage and synthetic semantic checkpoint verifier."""
import hashlib
import json
from pathlib import Path
import re
import sys


def need(condition, label):
    if not condition:
        raise ValueError("R125_VERIFY_FAIL:" + label)


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha_file(path):
    return sha_bytes(path.read_bytes())


def digest(value):
    return sha_bytes(json.dumps(
        value, sort_keys=True, separators=(",", ":"),
        allow_nan=False
    ).encode("utf-8"))


def verify(root):
    root = root.resolve()
    manifest_path = root / "checkpoint_manifest_v1.json"
    need(manifest_path.is_file(), "MANIFEST_MISSING")

    m = json.loads(manifest_path.read_text())

    need(m["schema"] == "trust_robot_r125_checkpoint_manifest_v1",
         "MANIFEST_SCHEMA")
    need(m["base_commit"] ==
         "447326f489a101782f6ce6914664abf31d5c0aa7",
         "BASE_COMMIT")
    need(m["branch"] == "kios-isaacsim-v15-integration",
         "BRANCH")
    need(m["scientific_gates_closed"] == 11,
         "SCIENTIFIC_GATES")
    need(m["synthetic_only"] is True, "SYNTHETIC_SCOPE")
    need(m["test_counts"] == {
        "r122": 72, "r123": 78, "r124": 51
    }, "TEST_COUNTS")

    pins = m["file_sha256"]
    need(type(pins) is dict and len(pins) == 25,
         "FILE_PIN_COUNT")

    actual_paths = set()
    for path in root.rglob("*"):
        need(not path.is_symlink(), "SYMLINK")
        if path.is_file():
            actual_paths.add(path.relative_to(root).as_posix())

    need(actual_paths == set(pins) | {
        "checkpoint_manifest_v1.json"
    }, "FILE_ALLOWLIST_MISMATCH")

    for relative, expected in pins.items():
        path = root / relative
        need(path.is_file(), "FILE_MISSING:" + relative)
        need(len(expected) == 64, "SHA_FORMAT:" + relative)
        need(sha_file(path) == expected,
             "SHA_MISMATCH:" + relative)

    for phase, count in (("r122", 72),
                         ("r123", 78),
                         ("r124", 51)):
        log = (root / f"r125_{phase}_regression.log").read_text()
        need(re.search(
            rf"(?m)^Ran {count} tests? in ",
            log
        ) is not None, "REGRESSION_COUNT:" + phase)
        need(re.search(r"(?m)^OK$", log) is not None,
             "REGRESSION_STATUS:" + phase)
        need("FAILED" not in log and "Traceback" not in log,
             "REGRESSION_FAILURE:" + phase)

    def source(phase, role, name):
        return root / "evidence" / phase / role / name

    # Original R122/R123 result documents remain pinned independently
    # by their original 10 known SHA256 fingerprints at archive creation.
    for phase, names in {
        "r122": (
            "r122_terminal_path_v1.json",
            "r122_independent_validation_v1.json",
        ),
        "r123": (
            "r123_terminal_fault_audit_v1.json",
            "r123_independent_validation_v1.json",
        ),
    }.items():
        for name in names:
            obj = json.loads(source(phase, "result", name).read_text())
            need(type(obj) is dict,
                 "PREDECESSOR_RESULT_TYPE:" + name)

    report_path = source(
        "r124", "result", "r124_shadow_terminal_audit_v1.json"
    )
    validation_path = source(
        "r124", "result", "r124_independent_validation_v1.json"
    )
    repair_path = source(
        "r124", "result", "r124_c1_repair_lineage_v1.json"
    )

    report = json.loads(report_path.read_text())
    v = json.loads(validation_path.read_text())
    repair = json.loads(repair_path.read_text())

    need(report["pass"] is True, "R124_ENGINE_PASS")
    need(report["fault_cases"] == 22, "R124_FAULT_COUNT")
    need(report["prepublication_cases"] == 18,
         "R124_PREPUBLICATION_COUNT")
    need(report["postpublication_ambiguous_cases"] == 4,
         "R124_POSTPUBLICATION_COUNT")
    need(report["scientific_gates_closed"] == 11,
         "R124_GATES")
    need(report["full_r117_r122_integration_proven"] is False,
         "R124_INTEGRATION_NONCLAIM")

    for key in (
        "recorded_sensor_data_accessed",
        "sealed_test_accessed",
        "physical_factor_admitted",
        "physical_gt_scored",
        "estimator_or_hardware_executed",
        "full_r117_r122_integration_proven",
        "concurrent_publication_proven",
        "durable_recovery_proven",
        "cryptographically_authenticated_ledger",
        "physical_safety_proven",
    ):
        need(report[key] is False, "SCIENCE_FLAG:" + key)

    stages = (
        "candidate_create_pre", "candidate_create_post",
        "mutation_pre", "mutation_post",
        "receipt_pre", "receipt_post",
        "validation_pre", "validation_post",
        "publication_pre", "publication_post",
        "ack_pre",
    )

    witnesses = report["fault_witnesses"]
    need(len(witnesses) == 22, "WITNESS_COUNT")
    for row, (action, stage) in zip(
        witnesses,
        ((a, s) for a in ("cancel", "retire") for s in stages),
    ):
        post = stage in ("publication_post", "ack_pre")
        need(row["action"] == action and row["stage"] == stage,
             "WITNESS_ORDER")
        need(row["publication_occurred_before_exception"] is post,
             "WITNESS_PUBLICATION")
        need(row["caller_acknowledged"] is False,
             "WITNESS_ACK")
        need(row["observation_unchanged_after_fault"] is not post,
             "WITNESS_PRESERVATION")
        need(row["retry_result"] ==
             ("duplicate_denied" if post else "safe_success"),
             "WITNESS_RETRY")

    for action, state in report["normal_final_states"].items():
        need(action in ("cancel", "retire"), "NORMAL_ACTION")
        need(state["phase"] ==
             ("CANCELLED" if action == "cancel" else "RETIRED"),
             "NORMAL_PHASE")
        stamped = dict(state)
        claimed = stamped.pop("diagnostic_sha256")
        need(digest(stamped) == claimed,
             "OBSERVATION_DIGEST")

        previous = "0" * 64
        for item in state["terminal_receipts"]:
            payload = {k: val for k, val in item.items()
                       if k != "linked_sha256"}
            need(item["previous_sha256"] == previous,
                 "TERMINAL_CHAIN")
            need(digest(payload) == item["linked_sha256"],
                 "TERMINAL_RECEIPT_HASH")
            previous = item["linked_sha256"]
        need(previous == state["terminal_tip"],
             "TERMINAL_TIP")

        if action == "retire":
            need(len(state["registry_receipts"]) == 1,
                 "RETIREMENT_RECEIPT_COUNT")
            rr = state["registry_receipts"][0]
            payload = {k: val for k, val in rr.items()
                       if k != "linked_sha256"}
            need(digest(payload) == rr["linked_sha256"],
                 "REGISTRY_RECEIPT_HASH")
            need(state["registry_tip"] == rr["linked_sha256"],
                 "REGISTRY_TIP")
            need(state["terminal_receipts"][-1][
                "registry_linked_sha256"
            ] == rr["linked_sha256"], "CROSS_CHAIN_LINK")

    need(v["pass"] is True, "R124_INDEPENDENT_PASS")
    need(v["auditor_imported_engine"] is False,
         "R124_INDEPENDENT_BOUNDARY")
    need(v["unit_tests_passed"] == 51,
         "R124_UNIT_COUNT")
    need(v["fault_witnesses_verified"] == 22,
         "R124_WITNESS_VALIDATION")
    need(v["independent_negative_controls_passed"] == 2,
         "R124_NEGATIVE_CONTROLS")
    need(v["scientific_gates_closed"] == 11,
         "R124_VALIDATION_GATES")
    need(v["full_r117_r122_integration_proven"] is False,
         "R124_VALIDATION_NONCLAIM")

    need(v["audit_sha256"] == sha_file(report_path),
         "AUDIT_VALIDATION_LINK")

    for name, expected in v["file_sha256"].items():
        need(sha_file(source("r124", "dev", name)) == expected,
             "R124_SOURCE_VALIDATION_LINK:" + name)

    backup = source(
        "r124", "dev",
        "r124_independent_validate_before_casefold_fix_v1.txt"
    )
    current = source(
        "r124", "dev", "r124_independent_validate.py"
    )
    need(repair["original_validator_sha256"] == sha_file(backup),
         "REPAIR_ORIGINAL_LINK")
    need(repair["repaired_validator_sha256"] == sha_file(current),
         "REPAIR_CORRECTED_LINK")
    need(repair["scientific_gates_closed"] == 11,
         "REPAIR_GATES")

    print("R125_STANDALONE_CHECKPOINT_VERIFIER=PASS")
    print("R125_FILE_SHA256=25_PASS")
    print("R125_REGRESSION_TEST_COUNTS=72_78_51_PASS")
    print("R125_R124_RECEIPT_CHAIN=PASS")
    print("R125_R124_REPAIR_LINEAGE=PASS")
    print("R125_SCIENTIFIC_GATES=11_CLOSED")
    print("R125_ACTUAL_R117_R122_ATOMICITY=NOT_PROVEN")


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] != "verify":
        raise SystemExit("Usage: verify_checkpoint.py verify DIR")
    verify(Path(sys.argv[2]))
