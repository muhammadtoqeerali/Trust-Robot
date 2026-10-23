"""R123: injected faults around R122 terminal operations.

Purpose:
- Differentiate pre-mutation failures from partial publication.
- Expose missing receipts after underlying state mutation.
- Quarantine ambiguous outcomes in a diagnostic wrapper.
- Never claim transactional rollback where it is unproven.

The original R122 implementation remains unchanged.
"""

import json
from unittest.mock import patch

import r104_shared_graph as graph
import r108_delivery as delivery
import r119_observation as observation
import r120_audit_guard as audit
import r122_terminal as terminal

SCHEMA="TRUST_ROBOT_R123_SYNTHETIC_TERMINAL_FAULT_AUDIT_V1"

STAGES=(
    "cancel_registry_pre",
    "cancel_registry_post",
    "cancel_receipt_pre",
    "cancel_receipt_post",
    "retire_registry_pre",
    "retire_registry_post",
    "retire_receipt_pre",
    "retire_receipt_post",
)

EXPECT={
    "cancel_registry_pre":(False,0,1,0),
    "cancel_registry_post":(True,0,1,0),
    "cancel_receipt_pre":(True,0,1,0),
    "cancel_receipt_post":(True,1,1,0),
    "retire_registry_pre":(False,1,1,0),
    "retire_registry_post":(True,1,0,1),
    "retire_receipt_pre":(True,1,0,1),
    "retire_receipt_post":(True,2,0,1),
}

class FaultAuditError(RuntimeError):
    pass

class InjectedTerminalFault(RuntimeError):
    pass

def need(ok,reason):
    if not ok:
        raise FaultAuditError(reason)

def canonical(value):
    return observation.canonical(value)

def detached(value):
    return json.loads(canonical(value))

def injected_after(original):
    """Perform original mutation and then raise."""

    def function(*args,**kwargs):
        original(*args,**kwargs)
        raise InjectedTerminalFault(
            "AFTER_ORIGINAL_MUTATION"
        )

    return function

def make_saturated_fixture():
    g=graph.build("clean",True,13)

    f=terminal.TerminalPath(
        max_active=1,
        max_created=1,
        max_denials=1
    )

    lease,owner=f.open(g)

    try:
        f.submit(
            lease,object(),
            delivery.make_packet(g,1),
            version=0
        )
    except observation.OperationDenied as exc:
        need(
            str(exc)=="OWNER_MISMATCH",
            "DENIAL_SATURATION_SETUP"
        )
    else:
        raise FaultAuditError(
            "DENIAL_SATURATION_NOT_REACHED"
        )

    need(
        f.observe_denials()["receipt_count"]==1,
        "DENIAL_CAPACITY"
    )

    return f,lease,owner

def committed_digest(f,lease,owner):
    if lease in f._registry._active:
        return f.observe_session(
            lease,owner
        )["committed_digest"]

    ledger=f._registry._ledger

    need(
        len(ledger)>0,
        "NO_TERMINAL_COMMITTED_DIGEST"
    )

    return ledger[-1]["committed_digest"]

class FaultWitness:
    """A diagnostic quarantine wrapper, not a security sandbox."""

    def __init__(self,f,lease,owner):
        self.f=f
        self.lease=lease
        self.owner=owner
        self.quarantined=False
        self.events=[]

    def attempt(self,operation,stage):
        need(
            not self.quarantined,
            "FAULTED_SESSION_QUARANTINED"
        )

        before=self.f.inspect_terminal()
        session_before=self.f._state_for_known_lease(
            self.lease
        )
        digest_before=committed_digest(
            self.f,self.lease,self.owner
        )

        try:
            operation()
        except InjectedTerminalFault:
            pass
        else:
            raise FaultAuditError(
                "EXPECTED_INJECTION_NOT_OBSERVED"
            )

        after=self.f.inspect_terminal()
        session_after=self.f._state_for_known_lease(
            self.lease
        )

        digest_after=committed_digest(
            self.f,self.lease,self.owner
        )

        # Registry counts alone cannot reveal a live
        # session changing ACTIVE -> CANCELLED.
        # Both the session state and linked receipts
        # must be included in the mutation witness.
        session_state_changed=(
            session_before!=session_after
        )

        changed=(
            before!=after
            or session_state_changed
        )

        if changed:
            self.quarantined=True

        record={
            "stage":stage,
            "injection_observed":True,
            "state_changed":changed,
            "session_state_changed":session_state_changed,
            "session_phase_before":(
                session_before["phase"]
                if session_before is not None
                else None
            ),
            "session_phase_after":(
                session_after["phase"]
                if session_after is not None
                else None
            ),
            "quarantined":self.quarantined,
            "safe_retry_verified":False,
            "successful_acknowledgement":False,
            "committed_digest_preserved":
                digest_after==digest_before,
            "terminal_receipts_before":
                before["terminal"]["receipt_count"],
            "terminal_receipts_after":
                after["terminal"]["receipt_count"],
            "active_before":
                before["ordinary_audit"]["registry"][
                    "active_count"
                ],
            "active_after":
                after["ordinary_audit"]["registry"][
                    "active_count"
                ],
            "retired_before":
                before["ordinary_audit"]["registry"][
                    "retired_count"
                ],
            "retired_after":
                after["ordinary_audit"]["registry"][
                    "retired_count"
                ],
            "ordinary_denials_preserved":
                before["ordinary_audit"]["denials"]==
                after["ordinary_audit"]["denials"],
        }

        need(
            record["committed_digest_preserved"],
            "FAULT_MUTATED_COMMITTED_ESTIMATOR"
        )

        need(
            record["ordinary_denials_preserved"],
            "FAULT_MUTATED_DENIAL_RECEIPTS"
        )

        self.events.append(record)
        return record

def run_fault_case(stage):
    need(stage in STAGES,"UNKNOWN_FAULT_STAGE")

    f,lease,owner=make_saturated_fixture()

    retirement=stage.startswith("retire_")

    if retirement:
        f.terminal_cancel(
            lease,owner,version=0
        )

    original=(
        f._registry.retire
        if retirement
        else f._registry.cancel
    )

    operation=(
        lambda:f.terminal_retire(
            lease,owner
        )
        if retirement
        else lambda:f.terminal_cancel(
            lease,owner,version=0
        )
    )

    # Keep this explicit to avoid conditional
    # lambda precedence ambiguity.
    if retirement:
        operation=lambda:f.terminal_retire(
            lease,owner
        )
    else:
        operation=lambda:f.terminal_cancel(
            lease,owner,version=0
        )

    witness=FaultWitness(f,lease,owner)

    if stage.endswith("registry_pre"):
        target=f._registry
        attribute="retire" if retirement else "cancel"
        side_effect=InjectedTerminalFault(
            "BEFORE_REGISTRY_MUTATION"
        )

    elif stage.endswith("registry_post"):
        target=f._registry
        attribute="retire" if retirement else "cancel"
        side_effect=injected_after(original)

    elif stage.endswith("receipt_pre"):
        target=f
        attribute="_append_terminal"
        side_effect=InjectedTerminalFault(
            "BEFORE_RECEIPT_APPEND"
        )

    elif stage.endswith("receipt_post"):
        target=f
        attribute="_append_terminal"
        side_effect=injected_after(
            f._append_terminal
        )

    else:
        raise FaultAuditError(
            "UNRECOGNIZED_INJECTION"
        )

    with patch.object(
        target,attribute,
        side_effect=side_effect
    ):
        record=witness.attempt(
            operation,stage
        )

    expected_changed,receipts,active,retired=(
        EXPECT[stage]
    )

    need(
        record["state_changed"] is expected_changed
        and record["terminal_receipts_after"]==receipts
        and record["active_after"]==active
        and record["retired_after"]==retired,
        "FAULT_BOUNDARY_MISMATCH:"+stage
    )

    if not expected_changed:
        # A proven pre-mutation failure can be
        # retried after the fault has been removed.
        if retirement:
            f.terminal_retire(
                lease,owner
            )
        else:
            f.terminal_cancel(
                lease,owner,version=0
            )
            f.terminal_retire(
                lease,owner
            )

        view=f.inspect_terminal()

        need(
            view["ordinary_audit"]["registry"][
                "active_count"
            ]==0
            and view["terminal"]["receipt_count"]==2,
            "PREMUTATION_RETRY_FAILED"
        )

        record["safe_retry_verified"]=True
        record["retired_after_retry"]=True

    else:
        # Do not invoke R122 again after the
        # underlying mutation might have happened.
        called=[]

        try:
            witness.attempt(
                lambda:called.append("executed"),
                "unsafe_retry"
            )
        except FaultAuditError as exc:
            need(
                str(exc)==
                    "FAULTED_SESSION_QUARANTINED",
                "QUARANTINE_REASON"
            )
        else:
            raise FaultAuditError(
                "AMBIGUOUS_RETRY_PERMITTED"
            )

        need(
            not called,
            "QUARANTINE_EXECUTED_CALLBACK"
        )

        record["unsafe_retry_blocked"]=True
        record["retired_after_retry"]=False

    record["receipt_gap_observed"]=(
        expected_changed
        and stage in (
            "cancel_registry_post",
            "cancel_receipt_pre",
            "retire_registry_post",
            "retire_receipt_pre",
        )
    )

    record["acknowledgement_ambiguity_observed"]=(
        expected_changed
        and stage in (
            "cancel_receipt_post",
            "retire_receipt_post",
        )
    )

    record["no_automatic_rollback_claim"]=True

    return record

def integrity_preflight_fault():
    f,lease,owner=make_saturated_fixture()

    f.terminal_cancel(
        lease,owner,version=0
    )

    before=f.observe_registry()
    original=f._terminal[0]["denial_count"]

    f._terminal[0]["denial_count"]=777

    caught=False

    try:
        f.terminal_retire(
            lease,owner
        )
    except terminal.TerminalPathError as exc:
        need(
            str(exc)=="TERMINAL_LEDGER_TAMPER",
            "TAMPER_DENIAL_REASON"
        )
        caught=True

    need(
        caught,
        "CORRUPT_RECEIPT_ACCEPTED"
    )

    f._terminal[0]["denial_count"]=original

    need(
        f._verify() is True
        and f.observe_registry()==before,
        "CORRUPTION_PREFLIGHT_CHANGED_REGISTRY"
    )

    f.terminal_retire(
        lease,owner
    )

    view=f.inspect_terminal()

    need(
        view["terminal"]["receipt_count"]==2
        and view["ordinary_audit"]["registry"][
            "active_count"
        ]==0,
        "TAMPER_RESTORATION_RETIREMENT"
    )

    return {
        "tamper_rejected_pre_mutation":True,
        "registry_unchanged_at_rejection":True,
        "retirement_after_restoration":True,
        "authenticated_integrity_verified":False,
    }

def saturation_boundary():
    f,lease,owner=make_saturated_fixture()

    before=f.inspect_terminal()

    blocked=0

    for operation in (
        lambda:f.submit(
            lease,owner,
            delivery.make_packet(
                graph.build("clean",True,13),1
            ),
            version=0
        ),
        lambda:f.cancel(
            lease,owner,version=0
        ),
        lambda:f.retire(
            lease,owner
        ),
    ):
        try:
            operation()
        except audit.AuditGuardError as exc:
            need(
                str(exc)=="RECEIPT_CAPACITY_EXHAUSTED",
                "ORDINARY_SATURATION_REASON"
            )
            blocked+=1
        else:
            raise FaultAuditError(
                "ORDINARY_OPERATION_ACCEPTED"
            )

    need(
        f.observe_session(
            lease,owner
        )["version"]==0,
        "SATURATION_EXECUTED_ESTIMATOR"
    )

    f.terminal_cancel(
        lease,owner,version=0
    )
    f.terminal_retire(
        lease,owner
    )

    view=f.inspect_terminal()

    need(
        view["ordinary_audit"]["denials"]==
            before["ordinary_audit"]["denials"]
        and view["ordinary_audit"]["registry"][
            "active_count"
        ]==0,
        "SATURATION_RECOVERY"
    )

    return {
        "ordinary_mutations_blocked":blocked,
        "terminal_cancel_and_retire_completed":True,
        "original_denials_preserved":True,
        "hardware_stop_verified":False,
    }

def execute():
    # Independently execute the actual R122
    # synthetic baseline once.
    baseline=terminal.execute()

    need(
        baseline["status"]==
            "PASS_SYNTHETIC_POST_SATURATION_TERMINAL_ONLY"
        and baseline["healthy_baseline_sessions"]==6
        and baseline["full_terminal_capacity"][
            "bounded_terminal_receipts"
        ]==24,
        "R122_BASELINE"
    )

    cases={
        stage:run_fault_case(stage)
        for stage in STAGES
    }

    pre=[
        row for row in cases.values()
        if not row["state_changed"]
    ]

    post=[
        row for row in cases.values()
        if row["state_changed"]
    ]

    gaps=sum(
        row["receipt_gap_observed"]
        for row in cases.values()
    )

    ambiguous=sum(
        row["acknowledgement_ambiguity_observed"]
        for row in cases.values()
    )

    need(
        len(pre)==2
        and all(
            x["safe_retry_verified"] for x in pre
        )
        and len(post)==6
        and all(
            x["quarantined"] for x in post
        )
        and gaps==4
        and ambiguous==2,
        "FAULT_CLASSIFICATION_TOTALS"
    )

    integrity=integrity_preflight_fault()
    saturation=saturation_boundary()

    return {
        "schema":SCHEMA,
        "status":
            "PASS_SYNTHETIC_TERMINAL_FAULT_BOUNDARY_AUDIT",

        "fault_cases":cases,
        "integrity_preflight":integrity,
        "saturation_boundary":saturation,

        "fault_injection_stages":8,
        "pre_mutation_failures":2,
        "pre_mutation_safe_retries":2,
        "post_mutation_failures":6,
        "quarantined_ambiguous_sessions":6,
        "missing_terminal_receipt_cases":4,
        "acknowledgement_ambiguity_cases":2,

        "r122_baseline_verified":True,
        "r122_baseline_sessions":6,
        "r122_bounded_terminal_receipts":24,
        "original_denial_capacity_enforced":True,

        "transactional_terminal_rollback_proven":False,
        "postmutation_retry_safety_proven":False,
        "receipt_completion_after_fault_guaranteed":False,
        "hardware_emergency_stop_verified":False,
        "unconditional_termination_guaranteed":False,
        "process_failure_recovery_verified":False,
        "actual_concurrent_thread_safety_verified":False,
        "durable_logging_verified":False,
        "authenticated_logging_verified":False,
        "cryptographic_owner_authentication_verified":False,
        "physical_memory_reclamation_verified":False,
        "real_time_deadline_verified":False,

        "r95_backend_imported":False,
        "real_sensor_factors_authorized":False,
        "physical_clock_or_extrinsics_verified":False,
        "health_training_authorized":False,
        "ate_rpe_authorized":False,
        "confirmation_test_accessed":False,
        "raw_gt_or_rosbags_opened":False,

        "scientific_gates_closed":11,
    }

if __name__=="__main__":
    import sys

    result=execute()

    with open(
        sys.argv[1],"x",encoding="utf-8"
    ) as file:
        file.write(
            canonical(result).decode("utf-8")
        )

    print("R123_TERMINAL_FAULT_BOUNDARY=PASS")
    print("R123_INJECTED_STAGES=8")
    print("R123_PREMUTATION_SAFE_RETRIES=2")
    print("R123_POSTMUTATION_QUARANTINES=6")
    print("R123_MISSING_TERMINAL_RECEIPT_CASES=4")
    print("R123_ACKNOWLEDGEMENT_AMBIGUITY_CASES=2")
    print("R123_INTERNAL_RECEIPT_TAMPER=DENIED")
    print("R123_TERMINAL_ROLLBACK=NOT_PROVEN")
    print("R123_AUTOMATIC_RETRY_AFTER_MUTATION=DENIED")
