"""R126-C: synthetic stale-reference bypass diagnostic.

Uses actual archived R122 instances and the off-Git R126-B1 adapter.
No production state, sensor data or hardware is accessed.
"""
import copy
import hashlib
import json

import r122_terminal as terminal

from r126_identity_shadow import (
    ShadowAdapter,
    clone_preserving_local_identity,
    snapshot,
)

ACTIONS = ("cancel", "retire")


class ReferenceAuditError(RuntimeError):
    pass


def need(ok, reason):
    if not ok:
        raise ReferenceAuditError(reason)


def digest(value):
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True,
            separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    ).hexdigest()


def receipt_view(f):
    return f.inspect_terminal()["terminal"]


def fork_case(action):
    need(action in ACTIONS, "BAD_ACTION")

    h = ShadowAdapter(action)

    old = h.original
    old_registry = old._registry
    old_pool = old_registry._pool

    old_before = snapshot(old, h.lease)

    acknowledgement = h.transact()
    need(acknowledgement["acknowledged"] is True, "NO_PUBLICATION_ACK")

    published = h.published
    need(published is not old, "NO_DISTINCT_PUBLICATION")
    need(published._registry is not old_registry,
         "REGISTRY_ALIAS")
    need(published._registry._pool is not old_pool,
         "POOL_ALIAS")

    # The caller's original owner/lease capabilities remain valid
    # in the old facade after the adapter publishes the candidate.
    need(snapshot(old, h.lease) == old_before,
         "OLD_REFERENCE_CHANGED_DURING_PUBLICATION")

    published_before = snapshot(published, h.lease)
    old_before_bypass = snapshot(old, h.lease)

    old_phase = old_before_bypass["session"]["phase"]
    published_session = published_before["session"]

    if action == "cancel":
        need(old_phase == "ACTIVE", "OLD_CANCEL_PHASE")
        need(published_session["phase"] == "CANCELLED",
             "NEW_CANCEL_PHASE")

        result = old.terminal_cancel(
            h.lease, h.owner, version=0
        )
        expected_old_count = 1
        expected_published_count = 1

    else:
        need(old_phase == "CANCELLED", "OLD_RETIRE_PHASE")
        need(published_session is None,
             "NEW_RETIRED_SESSION_STILL_ACTIVE")

        result = old.terminal_retire(
            h.lease, h.owner
        )
        expected_old_count = 2
        expected_published_count = 2

    need(type(result) is dict, "OLD_OPERATION_NO_RECEIPT")

    # The independently retained old reference performed
    # a second terminal action. The adapter did not control it.
    old_after = snapshot(old, h.lease)
    published_after = snapshot(published, h.lease)

    need(published_after == published_before,
         "PUBLISHED_CHANGED_BY_OLD_FACADE")

    old_receipts = receipt_view(old)
    published_receipts = receipt_view(published)

    need(old_receipts["receipt_count"] == expected_old_count,
         "OLD_RECEIPT_COUNT")
    need(
        published_receipts["receipt_count"]
        == expected_published_count,
        "PUBLISHED_RECEIPT_COUNT",
    )

    need(
        old._registry is old_registry
        and old._registry._pool is old_pool,
        "ORIGINAL_REGISTRY_REPLACED",
    )

    need(
        published._registry is not old_registry,
        "REGISTRY_ISOLATION_LOST",
    )

    need(
        published._terminal is not old._terminal,
        "TERMINAL_LEDGER_ALIAS",
    )

    return {
        "action": action,
        "first_publication_acknowledged": True,
        "old_facade_operation_accepted_after_publication": True,
        "old_reference_retained_same_lease_and_owner": True,
        "old_facade_was_distinct_from_new_facade": True,
        "old_registry_distinct_from_published_registry": True,
        "published_observation_unchanged_by_old_operation": True,
        "old_phase_before_bypass": old_phase,
        "published_phase_before_bypass": (
            published_session["phase"]
            if published_session is not None
            else "RETIRED"
        ),
        "old_terminal_count_before_bypass":
            old_before_bypass["terminal"]["terminal"]["receipt_count"],
        "old_terminal_count_after_bypass":
            old_receipts["receipt_count"],
        "published_terminal_count":
            published_receipts["receipt_count"],
        "old_terminal_receipts": copy.deepcopy(old_receipts["receipts"]),
        "published_terminal_receipts":
            copy.deepcopy(published_receipts["receipts"]),
        "old_terminal_tip": old_receipts["chain_tip"],
        "published_terminal_tip": published_receipts["chain_tip"],
        "published_observation_before_sha256":
            digest(published_before),
        "published_observation_after_sha256":
            digest(published_after),
        "global_terminal_uniqueness_enforced": False,
        "externally_held_old_facade_revoked": False,
    }


def pointer_rebinding_case():
    h = ShadowAdapter("cancel")
    old = h.original

    need(snapshot(old, h.lease)["session"]["phase"] == "ACTIVE",
         "OLD_NOT_ACTIVE")

    h.transact()

    candidate = h.published
    need(candidate is not old, "CANDIDATE_NOT_PUBLISHED")
    need(
        snapshot(candidate, h.lease)["session"]["phase"]
        == "CANCELLED",
        "CANDIDATE_NOT_CANCELLED",
    )

    # Demonstrates lack of an enforced publication authority.
    # Only this disposable synthetic fixture is affected.
    h.published = old

    need(h.published is old, "POINTER_REBIND_DENIED")
    need(
        snapshot(h.published, h.lease)["session"]["phase"]
        == "ACTIVE",
        "REBIND_NOT_VISIBLE",
    )

    need(
        snapshot(candidate, h.lease)["session"]["phase"]
        == "CANCELLED",
        "CANDIDATE_ALTERED_BY_REBIND",
    )

    return {
        "unprotected_pointer_rebinding_possible": True,
        "visible_phase_after_rebinding": "ACTIVE",
        "previous_candidate_phase": "CANCELLED",
        "thread_safe_publication_proven": False,
        "revocation_proven": False,
    }


def receipt_mutation_cases():
    h = ShadowAdapter("retire")
    h.transact()

    published_before = snapshot(h.published, h.lease)

    need(len(h.original._terminal) == 1,
         "ORIGINAL_CANCEL_RECEIPT_MISSING")

    # Mutate old facade's local receipt. Only its own
    # integrity verifier should reject the mutation.
    h.original._terminal[0]["event"] = "invalid_old_event"

    try:
        h.original.inspect_terminal()
    except terminal.TerminalPathError:
        old_tamper_detected = True
    else:
        raise ReferenceAuditError("OLD_TAMPER_NOT_DETECTED")

    need(
        snapshot(h.published, h.lease) == published_before,
        "OLD_TAMPER_AFFECTED_PUBLISHED",
    )

    # A holder of the published private object can also
    # directly mutate it. Integrity checks reject this
    # particular corruption, but cannot prevent the write.
    h2 = ShadowAdapter("cancel")
    h2.transact()

    h2.published._terminal[0]["event"] = "invalid_new_event"

    try:
        h2.published.inspect_terminal()
    except terminal.TerminalPathError:
        published_tamper_detected = True
    else:
        raise ReferenceAuditError("NEW_TAMPER_NOT_DETECTED")

    return {
        "old_receipt_tamper_detected": old_tamper_detected,
        "published_receipt_tamper_detected": published_tamper_detected,
        "old_mutation_isolated_from_published": True,
        "private_python_state_write_prevented": False,
        "cryptographic_authentication_proven": False,
    }


def selected_alias_case():
    h = ShadowAdapter("cancel")
    old = h.published

    clone = clone_preserving_local_identity(
        old, h.lease, h.owner
    )

    checks = {
        "facade_distinct": clone is not old,
        "registry_distinct":
            clone._registry is not old._registry,
        "pool_distinct":
            clone._registry._pool is not old._registry._pool,
        "terminal_ledger_distinct":
            clone._terminal is not old._terminal,
        "denial_ledger_distinct":
            clone._denials is not old._denials,
        "policy_ledger_distinct":
            clone._policy is not old._policy,
        "lease_identity_preserved":
            any(key is h.lease for key in clone._registry._active),
        "owner_identity_preserved":
            clone._registry._active[h.lease]["owner"] is h.owner,
    }

    need(all(checks.values()), "SELECTED_ALIAS_CHECK_FAILED")

    return {
        **checks,
        "selected_checks_passed": len(checks),
        "exhaustive_object_graph_isolation_proven": False,
    }


def execute():
    forks = {
        action: fork_case(action)
        for action in ACTIONS
    }

    rebinding = pointer_rebinding_case()
    mutation = receipt_mutation_cases()
    alias = selected_alias_case()

    need(len(forks) == 2, "FORK_COUNT")

    return {
        "schema": "trust_robot_r126_external_reference_bypass_v1",
        "pass": True,
        "fork_cases": forks,
        "pointer_rebinding_case": rebinding,
        "receipt_mutation_cases": mutation,
        "selected_alias_case": alias,
        "confirmed_stale_reference_bypasses": 2,
        "actual_r122_source_modified": False,
        "R126_B1_source_modified": False,
        "global_exactly_once_proven": False,
        "old_facade_revocation_proven": False,
        "drop_in_atomic_backend_proven": False,
        "concurrent_publication_proven": False,
        "durable_recovery_proven": False,
        "physical_safety_proven": False,
        "real_sensor_factors_executed": False,
        "confirmation_test_accessed": False,
        "scientific_gates_closed": 11,
    }
