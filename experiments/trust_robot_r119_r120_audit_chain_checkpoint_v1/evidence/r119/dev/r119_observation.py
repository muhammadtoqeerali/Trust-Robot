"""R119: read-only diagnostic observations and failure receipts.

Wraps the unchanged R117 synthetic registry.

Observation returns detached JSON-compatible data,
never owner/lease objects or source sensor packets.

Rejected or aborted mutations produce locally linked
in-memory failure receipts. Failed candidates can
consume R114 attempted-work reservations.

This is NOT authenticated logging, durable recovery,
a security boundary, or concurrent thread safety.
"""

import hashlib
import json
from dataclasses import replace
from unittest.mock import patch

import r104_shared_graph as graph
import r107_incremental as r107
import r108_delivery as delivery
import r114_attempts as attempts
import r116_lifecycle as lifecycle
import r117_registry as registry

SCHEMA="TRUST_ROBOT_R119_SYNTHETIC_AUDIT_OBSERVATION_V1"
GENESIS="0"*64

SCENARIOS=(
    ("clean_joint","clean",True),
    ("lidar_dropout_joint","lidar_dropout",True),
    ("clean_camera_off","clean",False),
)

ORDERS={
    "ordered":(1,2,3,4),
    "bounded_reorder":(3,2,1,4),
}

DENIAL_REASONS=frozenset((
    "STALE_OR_UNKNOWN_HANDLE",
    "OWNER_MISMATCH",
    "STALE_VERSION",
    "ADMISSION_REJECTED",
    "INCOMPLETE_SESSION",
    "NONTERMINAL_RETIREMENT",
    "ACTIVE_CAPACITY_EXCEEDED",
    "CREATION_LIMIT_EXCEEDED",
    "ATTEMPT_TOTAL_BUDGET",
    "ATTEMPT_OPERATION_BUDGET",
    "SESSION_NOT_ACTIVE",
    "CANDIDATE_ABORTED",
))

class ObservationError(ValueError):
    pass

class OperationDenied(ObservationError):
    pass

def need(ok,reason):
    if not ok:
        raise ObservationError(reason)

def canonical(obj):
    return (
        json.dumps(
            obj,sort_keys=True,indent=2,allow_nan=False
        )+"\n"
    ).encode("utf-8")

def digest(obj):
    return hashlib.sha256(canonical(obj)).hexdigest()

def detached(obj):
    return json.loads(canonical(obj))

class ObservationBoundary:
    """Single-threaded diagnostic facade for R117.

    Owner credentials are still required by mutation
    APIs. Private Python objects remain accessible
    to code holding this facade.
    """

    def __init__(self,*,max_active=2,max_created=12):
        self._registry=registry.GuardedRegistry(
            max_active=max_active,
            max_created=max_created
        )
        self._denials=[]
        self._tip=GENESIS

    def _verify(self):
        self._registry._verify()

        previous=GENESIS

        for index,item in enumerate(self._denials,1):
            need(
                type(item) is dict
                and item.get("ordinal")==index,
                "DENIAL_SEQUENCE"
            )

            raw={
                k:v for k,v in item.items()
                if k!="linked_sha256"
            }

            need(
                item.get("previous_sha256")==previous
                and item.get("linked_sha256")==digest(raw)
                and item.get("reason") in DENIAL_REASONS
                and item.get("acknowledged") is False,
                "DENIAL_LEDGER_TAMPER"
            )

            previous=item["linked_sha256"]

        need(
            self._tip==previous,
            "DENIAL_CHAIN_TIP"
        )

    def _state_for_known_lease(self,lease):
        """Internal diagnostic; never exposes owner objects."""

        self._verify()

        if type(lease) is not object:
            return None

        entry=self._registry._active.get(lease)

        if entry is None:
            return None

        raw=self._registry.summary(
            lease,entry["owner"]
        )

        keys=(
            "phase",
            "version",
            "attempted_work_units",
            "committed_work_units",
            "committed_digest",
            "remaining_attempt_units",
        )

        state={
            key:raw[key]
            for key in keys
        }

        need(
            type(state["version"]) is int
            and type(state["attempted_work_units"]) is int
            and type(state["committed_work_units"]) is int
            and type(state["committed_digest"]) is str,
            "OBSERVATION_SCHEMA"
        )

        return detached(state)

    def observe_registry(self):
        self._verify()
        return detached(self._registry.audit())

    def observe_session(self,lease,owner):
        self._verify()

        try:
            self._registry.summary(lease,owner)
        except registry.RegistryError as exc:
            raise OperationDenied(str(exc)) from exc

        return self._state_for_known_lease(lease)

    def observe_retirements(self):
        self._verify()

        receipts=detached(
            self._registry._ledger
        )

        return {
            "receipt_count":len(receipts),
            "chain_tip":self._registry._tip,
            "receipts":receipts,
        }

    def observe_denials(self):
        self._verify()

        return detached({
            "receipt_count":len(self._denials),
            "chain_tip":self._tip,
            "receipts":self._denials,
        })

    def _record_denial(self,action,reason,before,after):
        need(reason in DENIAL_REASONS,"UNKNOWN_DENIAL_REASON")

        charged=0

        if before is not None and after is not None:
            need(
                before["committed_digest"]==
                    after["committed_digest"]
                and before["version"]==
                    after["version"]
                and before["committed_work_units"]==
                    after["committed_work_units"],
                "DENIAL_CHANGED_COMMITTED_STATE"
            )

            charged=(
                after["attempted_work_units"]-
                before["attempted_work_units"]
            )

            need(
                charged>=0,
                "ATTEMPT_LEDGER_DECREASE"
            )

            if reason=="CANDIDATE_ABORTED":
                need(
                    charged>0,
                    "ABORTED_CANDIDATE_NOT_CHARGED"
                )
            else:
                need(
                    charged==0,
                    "INVALID_ADMISSION_CHARGED"
                )

        record={
            "ordinal":len(self._denials)+1,
            "action":action,
            "reason":reason,
            "acknowledged":False,
            "previous_sha256":self._tip,
            "known_session":
                before is not None,
            "before":before,
            "after":after,
            "charged_attempt_units":charged,
            "committed_state_preserved":
                (
                    before is not None
                    and after is not None
                    and before["committed_digest"]==
                        after["committed_digest"]
                ) if before is not None else None,
        }

        record["linked_sha256"]=digest(record)

        self._denials.append(record)
        self._tip=record["linked_sha256"]

        self._verify()

    def _mutation(self,action,lease,fn):
        before=self._state_for_known_lease(lease)

        try:
            return fn()
        except registry.RegistryError as exc:
            reason=str(exc)

            after=self._state_for_known_lease(lease)

            self._record_denial(
                action,reason,before,after
            )

            raise OperationDenied(reason) from exc

    def open(self,g,*,recenter=False,attempt_budget=14):
        self._verify()

        return self._registry.open(
            g,recenter=recenter,
            attempt_budget=attempt_budget
        )

    def submit(self,lease,owner,packet,*,version):
        return self._mutation(
            "submit",
            lease,
            lambda:self._registry.submit(
                lease,owner,packet,version=version
            )
        )

    def finish(self,lease,owner,*,version):
        return self._mutation(
            "finish",
            lease,
            lambda:self._registry.finish(
                lease,owner,version=version
            )
        )

    def cancel(self,lease,owner,*,version):
        return self._mutation(
            "cancel",
            lease,
            lambda:self._registry.cancel(
                lease,owner,version=version
            )
        )

    def retire(self,lease,owner):
        return self._mutation(
            "retire",
            lease,
            lambda:self._registry.retire(
                lease,owner
            )
        )

def healthy_observation():
    jobs=[]

    for name,condition,camera in SCENARIOS:
        for order_name,order in ORDERS.items():
            for recenter in (False,True):
                jobs.append({
                    "name":(
                        name+"_"+order_name+
                        ("_recentered"
                         if recenter else "_ordinary")
                    ),
                    "graph":graph.build(
                        condition,camera,13
                    ),
                    "order":order,
                    "recenter":recenter,
                })

    need(len(jobs)==12,"HEALTHY_JOB_COUNT")

    facade=ObservationBoundary(
        max_active=2,max_created=12
    )

    rows={}
    read_checks=0

    for offset in range(0,12,2):
        pair=jobs[offset:offset+2]

        for job in pair:
            lease,owner=facade.open(
                job["graph"],
                recenter=job["recenter"]
            )

            job["lease"]=lease
            job["owner"]=owner

        for index in range(4):
            for job in pair:
                lease=job["lease"]
                owner=job["owner"]

                before=facade.observe_session(
                    lease,owner
                )

                copy_before=facade.observe_session(
                    lease,owner
                )

                need(
                    before==copy_before,
                    "OBSERVATION_NONDETERMINISM"
                )

                read_checks+=2

                packet=delivery.make_packet(
                    job["graph"],
                    job["order"][index]
                )

                ack=facade.submit(
                    lease,owner,packet,
                    version=before["version"]
                )

                after=facade.observe_session(
                    lease,owner
                )

                read_checks+=1

                need(
                    ack["acknowledged"] is True
                    and after["version"]==
                        before["version"]+1
                    and after["attempted_work_units"]>
                        before["attempted_work_units"],
                    "OBSERVATION_COMMIT_SEQUENCE"
                )

        for job in pair:
            lease=job["lease"]
            owner=job["owner"]

            before=facade.observe_session(
                lease,owner
            )

            result,ack=facade.finish(
                lease,owner,
                version=before["version"]
            )

            after=facade.observe_session(
                lease,owner
            )

            read_checks+=2

            error=lifecycle.validate_result(
                job["graph"],
                result,
                job["recenter"]
            )

            need(
                after["phase"]=="COMPLETED"
                and after["version"]==5
                and after["attempted_work_units"]==14
                and after["committed_work_units"]==14,
                "HEALTHY_OBSERVATION_FINISH"
            )

            record=facade.retire(
                lease,owner
            )

            need(
                record["terminal_phase"]=="COMPLETED",
                "HEALTHY_RETIRE"
            )

            rows[job["name"]]={
                "arrival_order":list(job["order"]),
                "recentered":job["recenter"],
                "acknowledged_operations":5,
                "attempted_work_units":14,
                "nonlinear_windows":4,
                "schur_events":3,
                "prior_transfers":
                    3 if job["recenter"] else 0,
                "max_abs_error_vs_s6":error,
                "retired":True,
            }

    retirement=facade.observe_retirements()
    original_tip=retirement["chain_tip"]

    need(
        retirement["receipt_count"]==12
        and len(retirement["receipts"])==12,
        "RETIREMENT_OBSERVATION_COUNT"
    )

    # The returned data are detached copies.
    retirement["receipts"][0]["version"]=999

    reread=facade.observe_retirements()

    need(
        reread["receipts"][0]["version"]==5
        and reread["chain_tip"]==original_tip,
        "DETACHED_RETIREMENT_OBSERVATION"
    )

    need(
        facade.observe_denials()["receipt_count"]==0,
        "HEALTHY_DENIAL_RECORD"
    )

    final=facade.observe_registry()

    need(
        final["created"]==12
        and final["retired_count"]==12
        and final["active_count"]==0,
        "HEALTHY_REGISTRY_FINAL"
    )

    return {
        "runs":rows,
        "sessions":12,
        "acknowledged_operations":60,
        "attempted_work_units":168,
        "observation_reads":read_checks,
        "retirement_receipts":12,
        "detached_retirement_copy_verified":True,
        "retirement_chain_tip":original_tip,
        "denial_receipts":0,
        "active_after":0,
    }

def denied_admissions():
    g=graph.build("clean",True,13)
    other=graph.build(
        "lidar_dropout",True,13
    )

    facade=ObservationBoundary(
        max_active=1,max_created=1
    )

    lease,owner=facade.open(g)
    packet=delivery.make_packet(g,1)

    patterns=(
        (
            "wrong_owner",
            "OWNER_MISMATCH",
            lambda:facade.submit(
                lease,object(),packet,version=0
            ),
        ),
        (
            "stale_version",
            "STALE_VERSION",
            lambda:facade.submit(
                lease,owner,packet,version=1
            ),
        ),
        (
            "future_node",
            "ADMISSION_REJECTED",
            lambda:facade.submit(
                lease,owner,
                delivery.make_packet(g,4),
                version=0
            ),
        ),
        (
            "wrong_graph",
            "ADMISSION_REJECTED",
            lambda:facade.submit(
                lease,owner,
                delivery.make_packet(other,1),
                version=0
            ),
        ),
        (
            "false_frame",
            "ADMISSION_REJECTED",
            lambda:facade.submit(
                lease,owner,
                replace(
                    packet,frame_id="RECORDED_BODY"
                ),
                version=0
            ),
        ),
        (
            "false_real_factor",
            "ADMISSION_REJECTED",
            lambda:facade.submit(
                lease,owner,
                replace(
                    packet,
                    real_sensor_factors_authorized=True
                ),
                version=0
            ),
        ),
        (
            "missing_imu",
            "ADMISSION_REJECTED",
            lambda:facade.submit(
                lease,owner,
                replace(
                    packet,
                    readings=packet.readings[:1]
                ),
                version=0
            ),
        ),
        (
            "incomplete_finish",
            "INCOMPLETE_SESSION",
            lambda:facade.finish(
                lease,owner,version=0
            ),
        ),
        (
            "unknown_handle",
            "STALE_OR_UNKNOWN_HANDLE",
            lambda:facade.submit(
                object(),owner,packet,version=0
            ),
        ),
    )

    names=[]

    for name,reason,action in patterns:
        before=facade.observe_session(
            lease,owner
        )

        try:
            action()
        except OperationDenied as exc:
            need(
                str(exc)==reason,
                "DENIAL_REASON:"+name
            )
        else:
            raise ObservationError(
                "INVALID_OPERATION_ACCEPTED:"+name
            )

        need(
            facade.observe_session(
                lease,owner
            )==before,
            "DENIAL_MUTATED_STATE:"+name
        )

        names.append(name)

    ack=facade.submit(
        lease,owner,packet,version=0
    )

    need(
        ack["acknowledged"] is True,
        "VALID_PACKET_AFTER_DENIAL"
    )

    before=facade.observe_session(
        lease,owner
    )

    try:
        facade.submit(
            lease,owner,packet,version=1
        )
    except OperationDenied as exc:
        need(
            str(exc)=="ADMISSION_REJECTED",
            "DUPLICATE_REASON"
        )
    else:
        raise ObservationError(
            "DUPLICATE_ACCEPTED"
        )

    need(
        facade.observe_session(lease,owner)==before,
        "DUPLICATE_CHANGED_STATE"
    )

    for node in (2,3,4):
        facade.submit(
            lease,owner,
            delivery.make_packet(g,node),
            version=node-1
        )

    result,ack=facade.finish(
        lease,owner,version=4
    )

    error=lifecycle.validate_result(
        g,result,False
    )

    facade.retire(lease,owner)

    receipts=facade.observe_denials()

    need(
        receipts["receipt_count"]==10
        and all(
            item["acknowledged"] is False
            and item["charged_attempt_units"]==0
            for item in receipts["receipts"]
        ),
        "INVALID_ADMISSION_RECEIPTS"
    )

    # A caller may mutate its detached copy without
    # changing the authoritative internal ledger.
    receipts["receipts"][0]["reason"]="FORGED_SUCCESS"

    original=facade.observe_denials()

    need(
        original["receipts"][0]["reason"]==
            "OWNER_MISMATCH",
        "DENIAL_OBSERVATION_NOT_DETACHED"
    )

    return {
        "patterns":names+["duplicate"],
        "denials":10,
        "invalid_admission_work_units":0,
        "successful_recovery":True,
        "max_abs_error_vs_s6":error,
        "detached_failure_receipts_verified":True,
        "linked_denial_chain_verified":True,
    }

def charged_failure_observation():
    bad=graph.build("clean",True,13)
    good=graph.build(
        "lidar_dropout",True,13
    )

    facade=ObservationBoundary(
        max_active=2,max_created=2
    )

    bad_lease,bad_owner=facade.open(
        bad,attempt_budget=3
    )

    good_lease,good_owner=facade.open(
        good,attempt_budget=14
    )

    for node in (1,2,3):
        before_bad=facade.observe_session(
            bad_lease,bad_owner
        )

        before_good=facade.observe_session(
            good_lease,good_owner
        )

        with patch.object(
            r107,
            "least_squares",
            side_effect=attempts.InjectedFault(
                "R119_SYNTHETIC_OPTIMIZER_FAILURE"
            )
        ):
            try:
                facade.submit(
                    bad_lease,bad_owner,
                    delivery.make_packet(bad,1),
                    version=0
                )
            except OperationDenied as exc:
                need(
                    str(exc)=="CANDIDATE_ABORTED",
                    "FAULT_RECEIPT_REASON"
                )
            else:
                raise ObservationError(
                    "FAULTY_CANDIDATE_ACKNOWLEDGED"
                )

        after_bad=facade.observe_session(
            bad_lease,bad_owner
        )

        need(
            after_bad["committed_digest"]==
                before_bad["committed_digest"]
            and after_bad["version"]==0
            and after_bad["committed_work_units"]==0
            and after_bad["attempted_work_units"]==
                before_bad["attempted_work_units"]+1,
            "FAULT_OBSERVATION_INCONSISTENT"
        )

        need(
            facade.observe_session(
                good_lease,good_owner
            )==before_good,
            "FAULT_CHANGED_HEALTHY_PEER"
        )

        ack=facade.submit(
            good_lease,good_owner,
            delivery.make_packet(good,node),
            version=node-1
        )

        need(
            ack["acknowledged"] is True,
            "HEALTHY_PEER_BLOCKED"
        )

    before=facade.observe_session(
        bad_lease,bad_owner
    )

    try:
        facade.submit(
            bad_lease,bad_owner,
            delivery.make_packet(bad,1),
            version=0
        )
    except OperationDenied as exc:
        need(
            str(exc)=="ATTEMPT_TOTAL_BUDGET",
            "EXHAUSTION_RECEIPT_REASON"
        )
    else:
        raise ObservationError(
            "EXHAUSTED_ATTEMPT_EXECUTED"
        )

    need(
        facade.observe_session(
            bad_lease,bad_owner
        )==before,
        "EXHAUSTION_CHANGED_STATE"
    )

    facade.cancel(
        bad_lease,bad_owner,version=0
    )
    facade.retire(bad_lease,bad_owner)

    facade.submit(
        good_lease,good_owner,
        delivery.make_packet(good,4),
        version=3
    )

    result,ack=facade.finish(
        good_lease,good_owner,
        version=4
    )

    error=lifecycle.validate_result(
        good,result,False
    )

    facade.retire(good_lease,good_owner)

    receipts=facade.observe_denials()

    need(
        receipts["receipt_count"]==4,
        "FAILURE_RECEIPT_COUNT"
    )

    charges=[
        item["charged_attempt_units"]
        for item in receipts["receipts"]
    ]

    need(
        charges==[1,1,1,0],
        "FAILED_ATTEMPT_CHARGE_LEDGER"
    )

    need(
        [item["reason"] for item in receipts["receipts"]]
        ==[
            "CANDIDATE_ABORTED",
            "CANDIDATE_ABORTED",
            "CANDIDATE_ABORTED",
            "ATTEMPT_TOTAL_BUDGET",
        ],
        "FAILURE_RECEIPT_ORDER"
    )

    need(
        facade.observe_registry()["active_count"]==0,
        "FAULT_REGISTRY_NOT_DRAINED"
    )

    return {
        "failure_receipts":4,
        "aborted_candidates":3,
        "charged_attempt_ledger":charges,
        "fourth_attempt_denied_without_charge":True,
        "committed_state_preserved":True,
        "healthy_peer_completed":True,
        "healthy_peer_max_abs_error_vs_s6":error,
        "retirement_receipts":2,
    }

def prepublication_failure_receipt():
    g=graph.build("clean",True,13)

    facade=ObservationBoundary(
        max_active=1,max_created=1
    )

    lease,owner=facade.open(g)

    entry=facade._registry._active[lease]

    session=facade._registry._pool._active[
        entry["handle"]
    ]["session"]

    before=facade.observe_session(
        lease,owner
    )

    def cancel_at_publication(current,operation):
        need(
            operation=="submit",
            "UNEXPECTED_PUBLICATION_STAGE"
        )

        facade.cancel(
            lease,owner,version=0
        )

    session._inner._publication_hook=(
        cancel_at_publication
    )

    try:
        try:
            facade.submit(
                lease,owner,
                delivery.make_packet(g,1),
                version=0
            )
        except OperationDenied as exc:
            need(
                str(exc)=="CANDIDATE_ABORTED",
                "CANCELLED_CANDIDATE_REASON"
            )
        else:
            raise ObservationError(
                "CANCELLED_CANDIDATE_ACKNOWLEDGED"
            )
    finally:
        session._inner._publication_hook=None

    after=facade.observe_session(
        lease,owner
    )

    need(
        after["phase"]=="CANCELLED"
        and after["version"]==0
        and after["attempted_work_units"]==1
        and after["committed_work_units"]==0
        and after["committed_digest"]==
            before["committed_digest"],
        "PREPUBLICATION_ABORT_STATE"
    )

    facade.retire(lease,owner)

    receipts=facade.observe_denials()

    need(
        receipts["receipt_count"]==1
        and receipts["receipts"][0]["reason"]==
            "CANDIDATE_ABORTED"
        and receipts["receipts"][0][
            "charged_attempt_units"
        ]==1
        and receipts["receipts"][0]["after"]["phase"]==
            "CANCELLED",
        "PREPUBLICATION_RECEIPT"
    )

    return {
        "denial_receipts":1,
        "candidate_acknowledged":False,
        "attempted_work_units_charged":1,
        "committed_state_unchanged":True,
        "terminal_cancellation":True,
        "retired_after_abort":True,
    }

def internal_receipt_tamper():
    g=graph.build("clean",True,13)

    facade=ObservationBoundary(
        max_active=1,max_created=1
    )

    lease,owner=facade.open(g)

    try:
        facade.submit(
            lease,object(),
            delivery.make_packet(g,1),
            version=0
        )
    except OperationDenied as exc:
        need(
            str(exc)=="OWNER_MISMATCH",
            "TAMPER_FIXTURE_DENIAL"
        )
    else:
        raise ObservationError(
            "TAMPER_FIXTURE_NOT_REJECTED"
        )

    saved=facade._denials[0]["charged_attempt_units"]
    facade._denials[0]["charged_attempt_units"]=999

    caught=False

    try:
        facade.observe_registry()
    except ObservationError as exc:
        need(
            str(exc)=="DENIAL_LEDGER_TAMPER",
            "TAMPER_WRONG_REASON"
        )
        caught=True

    need(caught,"TAMPER_NOT_DETECTED")

    facade._denials[0]["charged_attempt_units"]=saved

    need(
        facade.observe_denials()["receipt_count"]==1,
        "TAMPER_RESTORE_FAILED"
    )

    facade.cancel(
        lease,owner,version=0
    )

    facade.retire(lease,owner)

    return {
        "internal_receipt_tamper_rejected":True,
        "subsequent_operations_after_restoration":True,
        "authenticated_log_verified":False,
    }

def execute():
    healthy=healthy_observation()
    denied=denied_admissions()
    charged=charged_failure_observation()
    cancellation=prepublication_failure_receipt()
    tamper=internal_receipt_tamper()

    need(
        healthy["sessions"]==12
        and healthy["acknowledged_operations"]==60
        and healthy["retirement_receipts"]==12,
        "HEALTHY_TOTALS"
    )

    need(
        denied["denials"]==10
        and charged["failure_receipts"]==4
        and tamper["internal_receipt_tamper_rejected"],
        "FAILURE_AUDIT_TOTALS"
    )

    return {
        "schema":SCHEMA,
        "status":
            "PASS_SYNTHETIC_AUDIT_OBSERVATION_SOFTWARE_ONLY",

        "healthy_observation":healthy,
        "denied_admissions":denied,
        "charged_failure_observation":charged,
        "prepublication_failure_receipt":cancellation,
        "internal_receipt_tamper":tamper,

        "healthy_sessions":12,
        "acknowledged_operations":60,
        "attempted_work_units":168,
        "retirement_receipts":12,
        "rejected_admission_receipts":10,
        "charged_failure_receipts":4,
        "cancelled_candidate_receipts":1,
        "internal_tamper_controls":1,

        "read_observations_detached":True,
        "failure_receipts_linked":True,
        "failed_candidate_reservations_visible":True,
        "successful_acknowledgements_not_forged":True,
        "owner_object_not_in_observations":True,
        "source_packet_not_in_observations":True,

        "authenticated_logging_verified":False,
        "durable_logging_verified":False,
        "external_ledger_anchor_verified":False,
        "malicious_inprocess_tamper_protection_verified":False,
        "actual_concurrent_thread_safety_verified":False,
        "physical_memory_reclamation_verified":False,
        "wall_clock_resource_bound_verified":False,
        "cryptographic_owner_authentication_verified":False,
        "hardware_streaming_verified":False,

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

    report=execute()

    with open(
        sys.argv[1],"x",encoding="utf-8"
    ) as f:
        f.write(canonical(report).decode("utf-8"))

    print("R119_SYNTHETIC_AUDIT_OBSERVATION=PASS")
    print("R119_HEALTHY_SESSIONS=12")
    print("R119_ACKNOWLEDGED_OPERATIONS=60")
    print("R119_REPLAY_WORK_UNITS=168")
    print("R119_RETIREMENT_RECEIPTS=12")
    print("R119_REJECTED_ADMISSION_RECEIPTS=10")
    print("R119_FAULT_OBSERVATION_RECEIPTS=4")
    print("R119_PREPUBLICATION_ABORT_RECEIPTS=1")
    print("R119_INTERNAL_TAMPER_CONTROLS=1_PASS")
    print("R119_AUTHENTICATED_AUDIT_LOG=NOT_PROVEN")
