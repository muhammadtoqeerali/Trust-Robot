"""Standalone R127 checkpoint verification.

Usage:
    python3 -B verify_checkpoint.py verify CHECKPOINT_PATH

Requires only the Python standard library.
Does not import the R126 experimental engines or estimator modules.
"""

import copy
import hashlib
import json
from pathlib import Path
import re
import runpy
import sys

BASE = "ae69a775f133127f1c4cf99d034448c7da382918"
LINEAGE_SHA = (
    "52ed3aa01e10318092692ee6eee526d4a3cfbffa963a0ca74a0c91b5dca8d713"
)
GENESIS = "0" * 64


class VerificationError(ValueError):
    pass


def need(condition, reason):
    if not condition:
        raise VerificationError("R127_CHECKPOINT_FAIL:" + reason)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(value):
    encoded = (
        json.dumps(
            value,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        ) + "\n"
    ).encode("utf-8")

    return hashlib.sha256(encoded).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_log(path, count, passing=True):
    value = path.read_text(encoding="utf-8")

    need(
        re.search(rf"(?m)^Ran {count} tests in ", value)
        is not None,
        "TEST_COUNT:" + path.name,
    )

    if passing:
        need(
            re.search(r"(?m)^OK$", value) is not None,
            "UNIT_TEST_RESULT:" + path.name,
        )
        need(
            "FAILED" not in value
            and "Traceback" not in value,
            "UNIT_TEST_FAILURE:" + path.name,
        )

    return True


def receipt_chain(items, tip, expected_count):
    need(
        type(items) is list and len(items) == expected_count,
        "RECEIPT_COUNT",
    )

    previous = GENESIS

    for ordinal, item in enumerate(items, 1):
        need(type(item) is dict, "RECEIPT_TYPE")
        need(item.get("ordinal") == ordinal, "RECEIPT_ORDINAL")

        event = (
            "terminal_cancel"
            if ordinal == 1
            else "terminal_retire"
        )

        need(item.get("event") == event, "RECEIPT_EVENT")
        need(
            item.get("previous_sha256") == previous,
            "RECEIPT_LINK",
        )

        payload = {
            k: v for k, v in item.items()
            if k != "linked_sha256"
        }

        need(
            item.get("linked_sha256") == digest(payload),
            "RECEIPT_DIGEST",
        )

        previous = item["linked_sha256"]

    need(previous == tip, "RECEIPT_TIP")
    return True


def validate_c(report):
    need(
        report.get("schema")
        == "trust_robot_r126_external_reference_bypass_v1",
        "C_SCHEMA",
    )
    need(report.get("pass") is True, "C_PASS")
    need(
        report.get("confirmed_stale_reference_bypasses") == 2,
        "C_BYPASSES",
    )
    need(
        report.get("scientific_gates_closed") == 11,
        "C_GATES",
    )

    forks = report.get("fork_cases")
    need(
        type(forks) is dict
        and set(forks) == {"cancel", "retire"},
        "C_FORK_SET",
    )

    for action, count in (
        ("cancel", 1),
        ("retire", 2),
    ):
        row = forks[action]

        for flag in (
            "first_publication_acknowledged",
            "old_facade_operation_accepted_after_publication",
            "old_reference_retained_same_lease_and_owner",
            "old_registry_distinct_from_published_registry",
            "published_observation_unchanged_by_old_operation",
        ):
            need(row.get(flag) is True, "C_WITNESS:" + flag)

        need(row.get("action") == action, "C_ACTION")

        need(
            row["old_terminal_count_after_bypass"] == count,
            "C_OLD_COUNT",
        )
        need(
            row["published_terminal_count"] == count,
            "C_PUBLISHED_COUNT",
        )

        need(
            row["published_observation_before_sha256"]
            == row["published_observation_after_sha256"],
            "C_PUBLISHED_OBSERVATION",
        )

        need(
            row["global_terminal_uniqueness_enforced"] is False,
            "C_GLOBAL_UNIQUENESS_NONCLAIM",
        )
        need(
            row["externally_held_old_facade_revoked"] is False,
            "C_REVOCATION_NONCLAIM",
        )

        receipt_chain(
            row["old_terminal_receipts"],
            row["old_terminal_tip"],
            count,
        )
        receipt_chain(
            row["published_terminal_receipts"],
            row["published_terminal_tip"],
            count,
        )

    rebinding = report["pointer_rebinding_case"]
    need(
        rebinding["unprotected_pointer_rebinding_possible"] is True,
        "C_POINTER_REBINDING",
    )
    need(
        rebinding["visible_phase_after_rebinding"] == "ACTIVE",
        "C_REBOUND_PHASE",
    )

    mutation = report["receipt_mutation_cases"]
    need(
        mutation["old_receipt_tamper_detected"] is True,
        "C_OLD_TAMPER",
    )
    need(
        mutation["published_receipt_tamper_detected"] is True,
        "C_NEW_TAMPER",
    )
    need(
        mutation["private_python_state_write_prevented"] is False,
        "C_PRIVATE_WRITE_NONCLAIM",
    )

    alias = report["selected_alias_case"]
    need(alias["selected_checks_passed"] == 8, "C_ALIAS_COUNT")
    need(
        alias["exhaustive_object_graph_isolation_proven"] is False,
        "C_ALIAS_NONCLAIM",
    )

    for name in (
        "actual_r122_source_modified",
        "R126_B1_source_modified",
        "global_exactly_once_proven",
        "old_facade_revocation_proven",
        "drop_in_atomic_backend_proven",
        "concurrent_publication_proven",
        "durable_recovery_proven",
        "physical_safety_proven",
        "real_sensor_factors_executed",
        "confirmation_test_accessed",
    ):
        need(report.get(name) is False, "C_NONCLAIM:" + name)

    return True


def c_negative_controls(report):
    mutated = copy.deepcopy(report)
    mutated["fork_cases"]["cancel"][
        "old_terminal_receipts"
    ][0]["event"] = "tampered"

    try:
        validate_c(mutated)
    except VerificationError:
        pass
    else:
        raise VerificationError("C_TAMPER_EVENT_ACCEPTED")

    mutated = copy.deepcopy(report)
    mutated["fork_cases"]["retire"][
        "old_terminal_receipts"
    ][1]["linked_sha256"] = GENESIS

    try:
        validate_c(mutated)
    except VerificationError:
        pass
    else:
        raise VerificationError("C_TAMPER_LINK_ACCEPTED")

    return 2


def validate_lineage(root):
    path = root / "source_lineage_v1.json"

    need(sha(path) == LINEAGE_SHA, "LINEAGE_SHA256")

    lineage = load(path)

    need(lineage["base_commit"] == BASE, "LINEAGE_BASE")
    need(lineage["original_evidence_count"] == 28,
         "LINEAGE_EVIDENCE_COUNT")
    need(lineage["byte_identical_evidence_copies"] == 27,
         "LINEAGE_IDENTICAL_COUNT")
    need(lineage["redacted_log_copies"] == 1,
         "LINEAGE_REDACTION_COUNT")
    need(lineage["scientific_gates_closed"] == 11,
         "LINEAGE_GATES")
    need(lineage["actual_r117_r122_atomicity_proven"] is False,
         "LINEAGE_ATOMICITY_NONCLAIM")

    source = lineage["source_sha256"]
    archived = lineage["archive_sha256"]

    need(
        len(source) == len(archived) == 28,
        "LINEAGE_MAP_SIZE",
    )
    need(set(source) == set(archived), "LINEAGE_MAP_KEYS")

    redacted_rel = (
        "evidence/b1/result/"
        "r126_unittest_initial_failure_v1_redacted.log"
    )

    need(
        set(lineage["redactions"]) == {redacted_rel},
        "LINEAGE_REDACTION_SET",
    )

    for relative, expected in archived.items():
        need(
            sha(root / relative) == expected,
            "ARCHIVED_EVIDENCE_SHA256:" + relative,
        )

        if relative != redacted_rel:
            need(
                source[relative] == expected,
                "ORIGINAL_EVIDENCE_SHA256:" + relative,
            )

    need(
        source[redacted_rel] != archived[redacted_rel],
        "REDACTION_NOT_APPLIED",
    )

    redaction = lineage["redactions"][redacted_rel]

    need(
        redaction["original_sha256"] == source[redacted_rel],
        "REDACTED_ORIGINAL_SHA256",
    )
    need(
        redaction["replacement_count"] > 0,
        "REDACTION_COUNT_ZERO",
    )
    need(
        redaction["byte_identical_to_original"] is False,
        "REDACTED_COPY_NONCLAIM",
    )

    redacted_text = (root / redacted_rel).read_text()

    need(
        "<REDACTED_KIOS_HOME>/" in redacted_text,
        "REDACTED_TEXT_MARKER",
    )
    need(
        "FAILED (errors=3)" in redacted_text,
        "ORIGINAL_FAILURE_HISTORY",
    )

    repair = load(
        root /
        "evidence/b1/result/r126_b1_repair_lineage_v1.json"
    )

    need(
        repair["failed_unit_log_sha256"] == source[redacted_rel],
        "REPAIR_FAILED_LOG_LINEAGE",
    )
    need(
        repair["original_engine_sha256"] ==
        source[
            "evidence/b1/dev/"
            "r126_identity_shadow_before_b1_fix_v1.txt"
        ],
        "REPAIR_ORIGINAL_ENGINE",
    )
    need(
        repair["repaired_engine_sha256"] ==
        source["evidence/b1/dev/r126_identity_shadow.py"],
        "REPAIR_CORRECTED_ENGINE",
    )
    need(
        repair["original_test_errors"] == 3
        and repair["unit_tests_passed"] == 18,
        "REPAIR_TEST_LINEAGE",
    )

    return lineage


def validate_reports(root):
    b1_result = root / "evidence/b1/result"
    b1_dev = root / "evidence/b1/dev"
    c_result = root / "evidence/c/result"
    c_dev = root / "evidence/c/dev"
    d_result = root / "evidence/d/result"
    d_dev = root / "evidence/d/dev"

    b1 = load(b1_result / "r126_identity_shadow_audit_v1.json")
    c = load(c_result / "r126_reference_bypass_audit_v1.json")
    d = load(d_result / "r126_d2_fault_audit_v1.json")

    b1_validator = runpy.run_path(
        str(b1_dev / "r126_independent_validate.py")
    )

    d_validator = runpy.run_path(
        str(d_dev / "r126_d2_independent_validate.py")
    )

    need(
        b1_validator["validate"](b1) is True,
        "B1_INDEPENDENT_REPORT",
    )
    need(
        d_validator["validate"](d) is True,
        "D2_INDEPENDENT_REPORT",
    )

    need(validate_c(c), "C_INDEPENDENT_REPORT")

    controls = (
        b1_validator["negative_controls"](b1)
        + c_negative_controls(c)
        + d_validator["negative_controls"](d)
    )

    need(controls == 7, "NEGATIVE_REPORT_CONTROLS")

    vb = load(
        b1_result / "r126_independent_validation_v1.json"
    )
    vc = load(
        c_result / "r126_reference_independent_validation_v1.json"
    )
    vd = load(
        d_result / "r126_d2_independent_validation_v1.json"
    )

    need(
        vb["pass"] is True
        and vb["unit_tests_passed"] == 18
        and vb["fault_cases_verified"] == 10
        and vb["negative_controls_passed"] == 2,
        "B1_VALIDATION_RECORD",
    )
    need(
        vc["pass"] is True
        and vc["unit_tests_passed"] == 15
        and vc["stale_reference_bypasses_confirmed"] == 2
        and vc["negative_tamper_controls_passed"] == 2,
        "C_VALIDATION_RECORD",
    )
    need(
        vd["pass"] is True
        and vd["total_unit_tests_passed"] == 45
        and vd["fault_witnesses_verified"] == 22
        and vd["negative_controls_passed"] == 3,
        "D2_VALIDATION_RECORD",
    )

    for evidence, dev, result, audit_name, log_name in (
        (
            vb, b1_dev, b1_result,
            "r126_identity_shadow_audit_v1.json",
            "r126_unittest_v1.log",
        ),
        (
            vc, c_dev, c_result,
            "r126_reference_bypass_audit_v1.json",
            "r126_reference_unittest_v1.log",
        ),
        (
            vd, d_dev, d_result,
            "r126_d2_fault_audit_v1.json",
            "r126_d2_unittest_v1.log",
        ),
    ):
        pins = evidence["source_sha256"]

        for name, expected in pins.items():
            if (dev / name).is_file():
                path = dev / name
            else:
                path = result / name

            need(
                path.is_file() and sha(path) == expected,
                "VALIDATION_SOURCE_HASH:" + name,
            )

        audit_pin = evidence.get("audit_sha256")
        log_pin = evidence.get("unit_log_sha256",
                               evidence.get("test_log_sha256"))

        if audit_pin is not None:
            need(
                sha(result / audit_name) == audit_pin,
                "VALIDATION_AUDIT_HASH",
            )

        if log_pin is not None:
            need(
                sha(result / log_name) == log_pin,
                "VALIDATION_LOG_HASH",
            )

    for report in (b1, c, d):
        need(
            report["scientific_gates_closed"] == 11,
            "REPORT_SCIENTIFIC_GATES",
        )

    need(
        b1["drop_in_atomic_backend_proven"] is False,
        "B1_ATOMICITY_NONCLAIM",
    )
    need(
        c["global_exactly_once_proven"] is False,
        "C_EXACTLY_ONCE_NONCLAIM",
    )
    need(
        d["actual_r117_r122_atomicity_proven"] is False,
        "D2_ATOMICITY_NONCLAIM",
    )

    return controls


def verify(root):
    need(root.is_dir() and not root.is_symlink(),
         "CHECKPOINT_DIRECTORY")

    manifest_path = root / "checkpoint_manifest_v1.json"
    need(manifest_path.is_file(), "MANIFEST_MISSING")

    m = load(manifest_path)

    need(
        m["schema"] ==
        "TRUST_ROBOT_R126_AUTHORITY_REFERENCE_CHECKPOINT_V1",
        "MANIFEST_SCHEMA",
    )
    need(m["base_commit"] == BASE, "MANIFEST_PARENT")
    need(
        m["branch"] == "kios-isaacsim-v15-integration",
        "MANIFEST_BRANCH",
    )

    need(m["scientific_gates_closed"] == 11,
         "MANIFEST_SCIENTIFIC_GATES")
    need(m["synthetic_only"] is True,
         "MANIFEST_SYNTHETIC_SCOPE")
    need(m["real_factor_admission"] is False,
         "MANIFEST_REAL_FACTOR_NONCLAIM")
    need(
        m["full_r117_r122_transaction_atomicity_proven"] is False,
        "MANIFEST_ATOMICITY_NONCLAIM",
    )
    need(
        m["durable_or_concurrent_safety_proven"] is False,
        "MANIFEST_DURABILITY_NONCLAIM",
    )
    need(
        m["old_facade_revocation_proven"] is False,
        "MANIFEST_REVOCATION_NONCLAIM",
    )
    need(
        m["python_introspection_prevented"] is False,
        "MANIFEST_INTROSPECTION_NONCLAIM",
    )

    need(
        m["test_counts"] == {
            "b1": 18, "c": 15, "d2": 45,
        },
        "MANIFEST_REGRESSION_COUNTS",
    )
    need(
        m["total_distinct_tests"] == 78,
        "MANIFEST_TOTAL_TESTS",
    )
    need(
        m["original_evidence_files"] == 28,
        "MANIFEST_EVIDENCE_COUNT",
    )
    need(
        m["redacted_failure_logs"] == 1,
        "MANIFEST_REDACTIONS",
    )

    need(
        m["source_lineage_sha256"] == LINEAGE_SHA,
        "MANIFEST_LINEAGE_PIN",
    )

    pins = m["file_sha256"]
    need(
        type(pins) is dict and len(pins) == 36,
        "MANIFEST_FILE_COUNT",
    )

    actual = {
        p.relative_to(root).as_posix()
        for p in root.rglob("*")
        if p.is_file()
    }

    need(
        len(actual) == 37
        and actual == (
            set(pins) | {"checkpoint_manifest_v1.json"}
        ),
        "CHECKPOINT_EXACT_FILE_SET",
    )

    blocked = (
        b"/home/" + b"kios/",
        b"/mnt/" + b"hdd16T/",
        b"room_02_" + b"official_gt_candidate.txt",
        b"-----BEGIN " + b"PRIVATE KEY-----",
        b"gh" + b"p_",
    )

    for relative, expected in pins.items():
        path = root / relative

        need(
            path.is_file() and not path.is_symlink(),
            "FILE_TYPE:" + relative,
        )
        need(
            sha(path) == expected,
            "SHA256:" + relative,
        )

    for relative in actual:
        path = root / relative

        need(not path.is_symlink(), "SYMLINK:" + relative)
        raw = path.read_bytes()

        need(
            0 < len(raw) < 5_000_000,
            "FILE_SIZE:" + relative,
        )

        for marker in blocked:
            need(
                marker not in raw,
                "PRIVATE_CONTENT:" + relative,
            )

    lineage = validate_lineage(root)

    need(
        set(lineage["archive_sha256"])
        == {
            relative for relative in pins
            if relative.startswith("evidence/")
        },
        "MANIFEST_EVIDENCE_SET",
    )

    for relative, count in (
        ("evidence/b1/result/r126_unittest_v1.log", 18),
        ("evidence/c/result/r126_reference_unittest_v1.log", 15),
        ("evidence/d/result/r126_d1_unittest_v1.log", 11),
        ("evidence/d/result/r126_d2_unittest_v1.log", 45),
        ("r127_b1_regression.log", 18),
        ("r127_c_regression.log", 15),
        ("r127_d2_regression.log", 45),
    ):
        test_log(root / relative, count)

    controls = validate_reports(root)

    need(
        "All eleven physical/scientific admissibility gates are CLOSED."
        in (root / "scientific_scope_v1.md").read_text(),
        "SCIENTIFIC_SCOPE_DOCUMENT",
    )
    need(
        (root / "verification_status_v1.md").is_file(),
        "VERIFICATION_STATUS_MISSING",
    )

    print("R127_STANDALONE_CHECKPOINT_VERIFIER=PASS")
    print("R127_FILE_SHA256=36_PASS")
    print("R127_SOURCE_LINEAGE=28_PASS")
    print("R127_REDACTED_FAILURE_HISTORY=PASS")
    print("R127_REGRESSION_COUNTS=18_15_45_PASS")
    print("R127_INDEPENDENT_B1_C_D2_REPORTS=PASS")
    print("R127_LINKED_RECEIPT_VALIDATION=PASS")
    print("R127_NEGATIVE_REPORT_CONTROLS=%d_PASS" % controls)
    print("R127_SCIENTIFIC_GATES=11_CLOSED")
    print("R127_REAL_R117_R122_ATOMICITY=NOT_PROVEN")
    print("R127_CONCURRENT_DURABLE_SAFETY=NOT_PROVEN")
    return True


if __name__ == "__main__":
    try:
        need(
            len(sys.argv) == 3 and sys.argv[1] == "verify",
            "USAGE",
        )
        verify(Path(sys.argv[2]).resolve())
    except Exception as exc:
        print("R127_CHECKPOINT_VERIFICATION_FAILED:", str(exc))
        sys.exit(2)
