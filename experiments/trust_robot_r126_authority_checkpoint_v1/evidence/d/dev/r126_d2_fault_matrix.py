"""R126-D2 fault matrix over cooperative synthetic authority API.

Private backend identity is inspected ONLY in diagnostic tests.
This is not production isolation, security or concurrency evidence.
"""
import hashlib
import json

from r126_single_authority import (
    AuthorityError,
    InjectedAuthorityFault,
    TerminalAuthority,
    STAGES,
    PREPUBLICATION,
    POSTPUBLICATION,
)

ACTIONS = ("cancel", "retire")


def need(ok, reason):
    if not ok:
        raise AssertionError("R126_D2:" + reason)


def digest(value):
    return hashlib.sha256(
        (
            json.dumps(
                value, sort_keys=True, indent=2,
                allow_nan=False
            ) + "\n"
        ).encode("utf-8")
    ).hexdigest()


def make(action):
    need(action in ACTIONS, "UNKNOWN_ACTION")

    authority, lease, owner = TerminalAuthority.create()

    if action == "retire":
        receipt = authority.terminal_cancel(
            lease, owner, version=0
        )
        need(receipt["acknowledged"] is True,
             "RETIRE_SETUP_CANCEL")

    return authority, lease, owner


def data(view):
    observation = view["observation"]
    audit = observation["ordinary_audit"]
    terminal = observation["terminal"]
    registry = audit["registry"]
    retirements = audit["retirements"]
    denials = audit["denials"]

    return {
        "phase": view["phase"],
        "terminal_count": terminal["receipt_count"],
        "terminal_tip": terminal["chain_tip"],
        "terminal_receipts": terminal["receipts"],
        "active_count": registry["active_count"],
        "retired_count": registry["retired_count"],
        "retirement_count": retirements["receipt_count"],
        "retirement_tip": retirements["chain_tip"],
        "retirement_receipts": retirements["receipts"],
        "denial_count": denials["receipt_count"],
        "denial_tip": denials["chain_tip"],
        "denial_receipts": denials["receipts"],
    }


def expected_final(action, view):
    v = data(view)
    retired = action == "retire"

    need(
        v["phase"] == ("RETIRED" if retired else "CANCELLED"),
        "FINAL_PHASE",
    )
    need(
        v["terminal_count"] == (2 if retired else 1),
        "FINAL_TERMINAL_COUNT",
    )
    need(
        v["active_count"] == (0 if retired else 1),
        "FINAL_ACTIVE_COUNT",
    )
    need(
        v["retired_count"] == int(retired),
        "FINAL_RETIRED_COUNT",
    )
    need(
        v["retirement_count"] == int(retired),
        "FINAL_RETIREMENT_RECEIPTS",
    )
    need(v["denial_count"] == 1, "DENIAL_PRESERVATION")

    return v


def call(authority, action, lease, owner):
    if action == "cancel":
        return authority.terminal_cancel(
            lease, owner, version=0
        )
    return authority.terminal_retire(lease, owner)


def normal_case(action):
    a, lease, owner = make(action)

    before = a.inspect()

    receipt = call(a, action, lease, owner)
    need(receipt["acknowledged"] is True, "NORMAL_ACK")

    final = a.inspect()
    record = expected_final(action, final)

    need(final != before, "NORMAL_PUBLICATION_MISSING")

    return {
        "action": action,
        "acknowledged": True,
        "before_phase": before["phase"],
        "final_observation_sha256": digest(final),
        **record,
    }


def fault_case(action, stage):
    need(action in ACTIONS, "BAD_ACTION")
    need(stage in STAGES, "BAD_STAGE")

    a, lease, owner = make(action)

    before = a.inspect()
    old_pointer = getattr(a, "_TerminalAuthority__published")

    try:
        a._diagnostic_fault(
            action, lease, owner,
            version=0 if action == "cancel" else None,
            stage=stage,
        )
    except InjectedAuthorityFault as exc:
        need(str(exc) == stage, "WRONG_FAULT_STAGE")
    else:
        raise AssertionError("INJECTION_NOT_OBSERVED")

    at_fault = a.inspect()
    pointer_after_fault = getattr(
        a, "_TerminalAuthority__published"
    )

    post = stage in POSTPUBLICATION

    need(
        (pointer_after_fault is old_pointer) is (not post),
        "POINTER_PUBLICATION_BOUNDARY",
    )

    need(
        (at_fault == before) is (not post),
        "OBSERVATION_PUBLICATION_BOUNDARY",
    )

    if stage in PREPUBLICATION:
        acknowledgement = call(a, action, lease, owner)
        need(
            acknowledgement["acknowledged"] is True,
            "PREPUBLICATION_RETRY_FAILED",
        )
        recovery = "safe_retry_succeeded"
    else:
        expected_error = (
            "AUTHORITY_CANCEL_PHASE_DENIED"
            if action == "cancel"
            else "AUTHORITY_RETIRE_PHASE_DENIED"
        )

        try:
            call(a, action, lease, owner)
        except AuthorityError as exc:
            need(
                str(exc) == expected_error,
                "WRONG_DUPLICATE_DENIAL",
            )
        else:
            raise AssertionError("DUPLICATE_OPERATION_ACCEPTED")

        need(
            a.inspect() == at_fault,
            "REPLAY_CHANGED_PUBLISHED_STATE",
        )

        recovery = "duplicate_denied"

    final = a.inspect()
    record = expected_final(action, final)

    need(
        digest(final) != digest(before),
        "FINAL_OBSERVATION_UNCHANGED",
    )

    return {
        "action": action,
        "stage": stage,
        "exception_observed": True,
        "caller_acknowledged_at_fault": False,
        "published_before_exception": post,
        "published_observation_unchanged_at_fault": not post,
        "pointer_unchanged_at_fault": not post,
        "before_phase": before["phase"],
        "phase_at_fault": at_fault["phase"],
        "before_terminal_count":
            data(before)["terminal_count"],
        "terminal_count_at_fault":
            data(at_fault)["terminal_count"],
        "before_observation_sha256": digest(before),
        "fault_observation_sha256": digest(at_fault),
        "final_observation_sha256": digest(final),
        "recovery": recovery,
        **record,
    }


def execute():
    normal = {
        action: normal_case(action)
        for action in ACTIONS
    }

    rows = [
        fault_case(action, stage)
        for action in ACTIONS
        for stage in STAGES
    ]

    need(len(rows) == 22, "FAULT_COUNT")

    pre = sum(
        not row["published_before_exception"]
        for row in rows
    )
    post = sum(
        row["published_before_exception"]
        for row in rows
    )

    need(pre == 18, "PREPUBLICATION_COUNT")
    need(post == 4, "POSTPUBLICATION_COUNT")

    return {
        "schema": "trust_robot_r126_d2_authority_fault_matrix_v1",
        "pass": True,
        "actual_archived_r122_objects": True,
        "fault_witnesses": rows,
        "normal_cases": normal,
        "fault_cases": 22,
        "prepublication_cases": 18,
        "postpublication_acknowledgement_ambiguities": 4,
        "supported_api_exposes_raw_backend": False,
        "private_backend_accessible_by_python_introspection": True,
        "arbitrary_python_mutation_prevented": False,
        "old_facade_revocation_proven": False,
        "exhaustive_alias_isolation_proven": False,
        "actual_r122_source_modified": False,
        "actual_r117_r122_atomicity_proven": False,
        "concurrent_linearizability_proven": False,
        "durable_recovery_proven": False,
        "cryptographic_authentication_proven": False,
        "physical_robot_safety_proven": False,
        "real_sensor_factors_executed": False,
        "sealed_confirmation_test_accessed": False,
        "scientific_gates_closed": 11,
    }
