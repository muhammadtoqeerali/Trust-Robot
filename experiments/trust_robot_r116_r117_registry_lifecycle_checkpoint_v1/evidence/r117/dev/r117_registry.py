"""R117: synthetic session registry and retirement ledger.

Features:
- In-process opaque object-identity session handles.
- No reuse of retired handles within or across registries.
- Version and owner admission before estimator work.
- SHA-256-linked, bounded retirement receipts.
- Detection of accidental in-memory receipt alteration.

NOT cryptographic authentication, concurrent safety,
durable storage, real memory reclamation, or physical
sensor streaming.
"""

import hashlib
import json
from unittest.mock import patch

import r104_shared_graph as graph
import r107_incremental as r107
import r108_delivery as delivery
import r114_attempts as attempts
import r116_lifecycle as lifecycle

SCHEMA="TRUST_ROBOT_R117_SYNTHETIC_REGISTRY_HARDENING_V1"
GENESIS="0"*64

SCENARIOS=(
    ("clean_joint","clean",True),
    ("lidar_dropout_joint","lidar_dropout",True),
    ("clean_camera_off","clean",False),
)

SCHEDULES={
    "ordered":(1,2,3,4),
    "bounded_reorder":(3,2,1,4),
}

RECEIPT_FIELDS=(
    "handle",
    "terminal_phase",
    "version",
    "attempted_work_units",
    "committed_work_units",
    "committed_digest",
    "retired",
)

class RegistryError(ValueError):
    pass

def need(ok,reason):
    if not ok:
        raise RegistryError(reason)

def canonical(data):
    return (
        json.dumps(
            data,sort_keys=True,
            indent=2,allow_nan=False
        )+"\n"
    ).encode("utf-8")

def sha(data):
    return hashlib.sha256(canonical(data)).hexdigest()

class GuardedRegistry:
    """Single-threaded wrapper over unchanged R116 SessionPool.

    Handles and owners are local object references.
    Private fields are inspectable and mutable by
    other Python code; they are not security barriers.
    """

    def __init__(self,*,max_active=2,max_created=12):
        self._pool=lifecycle.SessionPool(
            max_active=max_active,
            max_created=max_created
        )

        self._active={}
        self._ledger=[]
        self._tip=GENESIS
        self._issued=0

        self._verify()

    def _verify(self):
        previous=GENESIS

        for index,record in enumerate(self._ledger,1):
            need(
                type(record) is dict
                and record.get("issued_index")==index,
                "RETIREMENT_SEQUENCE"
            )

            payload={
                key:value
                for key,value in record.items()
                if key!="linked_sha256"
            }

            need(
                record.get("previous_sha256")==previous
                and record.get("linked_sha256")==sha(payload),
                "RETIREMENT_LEDGER_TAMPER"
            )

            previous=record["linked_sha256"]

            original=self._pool._retired.get(
                record["handle"]
            )

            expected={
                key:record[key]
                for key in RECEIPT_FIELDS
            }

            need(
                original==expected,
                "RETIRED_RECEIPT_MISMATCH"
            )

        need(
            self._tip==previous,
            "RETIREMENT_CHAIN_TIP"
        )

        audit=self._pool.audit()

        active_handles={
            entry["handle"]
            for entry in self._active.values()
        }

        retired_handles={
            record["handle"]
            for record in self._ledger
        }

        need(
            audit["created"]==self._issued
            and audit["active_count"]==len(self._active)
            and audit["retired_count"]==len(self._ledger)
            and self._issued==
                len(self._active)+len(self._ledger),
            "REGISTRY_COUNT_MISMATCH"
        )

        need(
            set(audit["active_handles"])==active_handles
            and set(audit["retired_handles"])==retired_handles
            and not active_handles.intersection(
                retired_handles
            ),
            "REGISTRY_HANDLE_MISMATCH"
        )

        return True

    def audit(self):
        self._verify()
        underlying=self._pool.audit()

        return {
            "created":self._issued,
            "active_count":len(self._active),
            "retired_count":len(self._ledger),
            "peak_active":underlying["peak_active"],
            "retirement_chain_sha256":self._tip,
            "receipt_count":len(self._ledger),
        }

    def open(
        self,g,*,
        recenter=False,
        attempt_budget=14
    ):
        self._verify()

        try:
            handle,owner=self._pool.open(
                g,
                recenter=recenter,
                attempt_budget=attempt_budget
            )
        except lifecycle.LifecycleError as exc:
            raise RegistryError(str(exc)) from exc

        # Object identity prevents accidentally using
        # the same string identifier in a different
        # local registry.
        lease=object()

        self._issued+=1

        self._active[lease]={
            "handle":handle,
            "owner":owner,
            "issued_index":self._issued,
        }

        self._verify()
        return lease,owner

    def _select(self,lease,owner):
        self._verify()

        need(
            type(lease) is object
            and lease in self._active,
            "STALE_OR_UNKNOWN_HANDLE"
        )

        entry=self._active[lease]

        need(
            owner is entry["owner"],
            "OWNER_MISMATCH"
        )

        return entry

    def _version(self,entry,version):
        need(
            type(version) is int
            and self._pool.summary(
                entry["handle"],
                entry["owner"]
            )["version"]==version,
            "STALE_VERSION"
        )

    def summary(self,lease,owner):
        entry=self._select(lease,owner)

        return self._pool.summary(
            entry["handle"],owner
        )

    def submit(self,lease,owner,packet,*,version):
        entry=self._select(lease,owner)
        self._version(entry,version)

        try:
            return self._pool.submit(
                entry["handle"],
                owner,
                packet,
                version=version
            )
        except lifecycle.LifecycleError as exc:
            raise RegistryError(str(exc)) from exc

    def finish(self,lease,owner,*,version):
        entry=self._select(lease,owner)
        self._version(entry,version)

        try:
            return self._pool.finish(
                entry["handle"],
                owner,
                version=version
            )
        except lifecycle.LifecycleError as exc:
            raise RegistryError(str(exc)) from exc

    def cancel(self,lease,owner,*,version):
        entry=self._select(lease,owner)
        self._version(entry,version)

        try:
            return self._pool.cancel(
                entry["handle"],
                owner,
                version=version
            )
        except lifecycle.LifecycleError as exc:
            raise RegistryError(str(exc)) from exc

    def retire(self,lease,owner):
        entry=self._select(lease,owner)

        try:
            receipt=self._pool.retire(
                entry["handle"],owner
            )
        except lifecycle.LifecycleError as exc:
            raise RegistryError(str(exc)) from exc

        need(
            receipt["retired"] is True
            and receipt["terminal_phase"] in (
                "COMPLETED","CANCELLED"
            ),
            "INVALID_TERMINAL_RECEIPT"
        )

        record={
            **receipt,
            "issued_index":entry["issued_index"],
            "previous_sha256":self._tip,
        }

        record["linked_sha256"]=sha(record)

        self._ledger.append(record)
        self._tip=record["linked_sha256"]

        # Release only this registry's active reference.
        del self._active[lease]

        self._verify()
        return dict(record)

def healthy_interleaving():
    jobs=[]

    for name,condition,camera in SCENARIOS:
        for schedule,order in SCHEDULES.items():
            for rebase in (False,True):
                jobs.append({
                    "name":(
                        name+"_"+schedule+
                        ("_recentered" if rebase
                         else "_ordinary")
                    ),
                    "graph":graph.build(
                        condition,camera,13
                    ),
                    "order":order,
                    "recenter":rebase,
                })

    need(len(jobs)==12,"JOB_COUNT")

    registry=GuardedRegistry(
        max_active=2,max_created=12
    )

    rows={}

    for start in range(0,12,2):
        pair=jobs[start:start+2]

        for job in pair:
            lease,owner=registry.open(
                job["graph"],
                recenter=job["recenter"]
            )

            job["lease"]=lease
            job["owner"]=owner

        need(
            registry.audit()["active_count"]==2,
            "PAIR_NOT_ACTIVE"
        )

        for position in range(4):
            for job in pair:
                lease=job["lease"]
                owner=job["owner"]

                state=registry.summary(
                    lease,owner
                )

                ack=registry.submit(
                    lease,owner,
                    delivery.make_packet(
                        job["graph"],
                        job["order"][position]
                    ),
                    version=state["version"]
                )

                need(
                    ack["acknowledged"] is True
                    and ack["sequence"]==position+1,
                    "ACK_SEQUENCE"
                )

        for job in pair:
            lease=job["lease"]
            owner=job["owner"]

            result,ack=registry.finish(
                lease,owner,
                version=4
            )

            error=lifecycle.validate_result(
                job["graph"],
                result,
                job["recenter"]
            )

            state=registry.summary(lease,owner)

            need(
                ack["acknowledged"] is True
                and state["phase"]=="COMPLETED"
                and state["version"]==5
                and state["attempted_work_units"]==14
                and state["committed_work_units"]==14,
                "HEALTHY_COMPLETION"
            )

            record=registry.retire(
                lease,owner
            )

            need(
                record["terminal_phase"]=="COMPLETED",
                "HEALTHY_RETIREMENT"
            )

            rows[job["name"]]={
                "arrival_order":list(job["order"]),
                "recentered":job["recenter"],
                "acknowledged_operations":5,
                "attempted_work_units":14,
                "committed_work_units":14,
                "nonlinear_windows":4,
                "schur_events":3,
                "prior_transfers":
                    3 if job["recenter"] else 0,
                "max_abs_error_vs_s6":error,
                "retired":True,
            }

        need(
            registry.audit()["active_count"]==0,
            "PAIR_NOT_RETIRED"
        )

    final=registry.audit()

    need(
        final["created"]==12
        and final["retired_count"]==12
        and final["active_count"]==0
        and final["peak_active"]==2
        and final["receipt_count"]==12
        and final["retirement_chain_sha256"]!=GENESIS,
        "FINAL_HEALTHY_LEDGER"
    )

    return {
        "runs":rows,
        "healthy_sessions":12,
        "acknowledged_operations":60,
        "attempted_work_units":168,
        "nonlinear_windows":48,
        "schur_events":36,
        "prior_transfers":18,
        "retirement_receipts":12,
        "registry_audit":final,
        "actual_concurrent_threads_tested":False,
    }

def stale_handle_and_capacity():
    g=graph.build("clean",True,13)

    reg=GuardedRegistry(
        max_active=2,max_created=3
    )

    a,oa=reg.open(g)
    b,ob=reg.open(g)

    before=reg.audit()

    try:
        reg.open(g)
    except RegistryError as exc:
        need(
            str(exc)=="ACTIVE_CAPACITY_EXCEEDED",
            "ACTIVE_BOUND_REASON"
        )
    else:
        raise RegistryError(
            "ACTIVE_BOUND_BYPASSED"
        )

    need(
        reg.audit()==before,
        "ACTIVE_REJECTION_MUTATED_REGISTRY"
    )

    reg.cancel(a,oa,version=0)
    first=reg.retire(a,oa)

    c,oc=reg.open(g)

    need(
        c is not a and c is not b,
        "LEASE_IDENTITY_REUSE"
    )

    for lease,owner in ((a,oa),):
        try:
            reg.summary(lease,owner)
        except RegistryError as exc:
            need(
                str(exc)=="STALE_OR_UNKNOWN_HANDLE",
                "STALE_LEASE_DENIAL"
            )
        else:
            raise RegistryError("STALE_LEASE_REUSED")

    for lease,owner in ((b,ob),(c,oc)):
        reg.cancel(lease,owner,version=0)
        reg.retire(lease,owner)

    prior=reg.audit()

    try:
        reg.open(g)
    except RegistryError as exc:
        need(
            str(exc)=="CREATION_LIMIT_EXCEEDED",
            "CREATION_BOUND_REASON"
        )
    else:
        raise RegistryError(
            "CREATION_BOUND_BYPASSED"
        )

    need(
        reg.audit()==prior
        and prior["retired_count"]==3
        and prior["active_count"]==0
        and first["terminal_phase"]=="CANCELLED",
        "CAPACITY_FINAL_STATE"
    )

    return {
        "active_capacity_rejections":1,
        "creation_limit_rejections":1,
        "retired_handles":3,
        "stale_handle_rejections":1,
        "opaque_handle_reuse":False,
        "registry_drained":True,
    }

def cross_registry_and_admission():
    g=graph.build("clean",True,13)
    other=graph.build("lidar_dropout",True,13)

    x=GuardedRegistry(
        max_active=1,max_created=1
    )

    y=GuardedRegistry(
        max_active=1,max_created=1
    )

    lx,ox=x.open(g)
    ly,oy=y.open(g)

    original=delivery.make_packet(g,1)

    patterns=(
        (
            "cross_registry_x",
            lambda:x.submit(
                ly,oy,original,version=0
            ),
            "STALE_OR_UNKNOWN_HANDLE",
        ),
        (
            "cross_registry_y",
            lambda:y.submit(
                lx,ox,original,version=0
            ),
            "STALE_OR_UNKNOWN_HANDLE",
        ),
        (
            "wrong_owner",
            lambda:x.submit(
                lx,object(),original,version=0
            ),
            "OWNER_MISMATCH",
        ),
        (
            "stale_version",
            lambda:x.submit(
                lx,ox,original,version=1
            ),
            "STALE_VERSION",
        ),
        (
            "wrong_graph",
            lambda:x.submit(
                lx,ox,
                delivery.make_packet(other,1),
                version=0
            ),
            "ADMISSION_REJECTED",
        ),
        (
            "future_node",
            lambda:x.submit(
                lx,ox,
                delivery.make_packet(g,4),
                version=0
            ),
            "ADMISSION_REJECTED",
        ),
    )

    names=[]

    for name,action,expected in patterns:
        before_x=x.summary(lx,ox)
        before_y=y.summary(ly,oy)

        try:
            action()
        except RegistryError as exc:
            need(
                str(exc)==expected,
                "ADMISSION_REASON:"+name
            )
            names.append(name)
        else:
            raise RegistryError(
                "INVALID_ADMISSION:"+name
            )

        need(
            x.summary(lx,ox)==before_x
            and y.summary(ly,oy)==before_y,
            "ADMISSION_MUTATED_STATE:"+name
        )

    for reg,lease,owner in (
        (x,lx,ox),
        (y,ly,oy),
    ):
        for node in (1,2,3,4):
            reg.submit(
                lease,owner,
                delivery.make_packet(g,node),
                version=node-1
            )

        result,ack=reg.finish(
            lease,owner,version=4
        )

        need(
            ack["acknowledged"] is True
            and lifecycle.validate_result(
                g,result,False
            )<1e-8,
            "CROSS_REGISTRY_HEALTHY_COMPLETION"
        )

        reg.retire(lease,owner)

    return {
        "rejected_patterns":names,
        "rejection_count":len(names),
        "zero_work_charged_for_invalid_admissions":True,
        "both_registries_completed":True,
        "both_registries_drained":True,
        "cross_registry_handle_reuse_denied":True,
    }

def ledger_corruption_controls():
    g=graph.build("clean",True,13)

    reg=GuardedRegistry(
        max_active=1,max_created=2
    )

    lease,owner=reg.open(g)
    reg.cancel(lease,owner,version=0)
    reg.retire(lease,owner)

    original=reg._ledger[0]["committed_work_units"]

    reg._ledger[0]["committed_work_units"]=999

    detected=0

    try:
        reg.open(g)
    except RegistryError as exc:
        need(
            str(exc)=="RETIREMENT_LEDGER_TAMPER",
            "LINKED_LEDGER_TAMPER_REASON"
        )
        detected+=1
    else:
        raise RegistryError(
            "LINKED_LEDGER_TAMPER_ACCEPTED"
        )

    reg._ledger[0]["committed_work_units"]=original

    reg._verify()

    underlying=reg._pool._retired["S0001"]
    saved=underlying["version"]

    underlying["version"]=999

    try:
        reg.open(g)
    except RegistryError as exc:
        need(
            str(exc)=="RETIRED_RECEIPT_MISMATCH",
            "UNDERLYING_RECEIPT_REASON"
        )
        detected+=1
    else:
        raise RegistryError(
            "UNDERLYING_RECEIPT_TAMPER_ACCEPTED"
        )

    underlying["version"]=saved
    reg._verify()

    another,owner2=reg.open(g)
    reg.cancel(another,owner2,version=0)
    reg.retire(another,owner2)

    need(
        detected==2
        and reg.audit()["retired_count"]==2
        and reg.audit()["active_count"]==0,
        "CORRUPTION_CONTROLS"
    )

    return {
        "linked_ledger_tamper_rejected":True,
        "underlying_receipt_tamper_rejected":True,
        "detected_corruptions":2,
        "subsequent_healthy_registry_operation":True,
        "cryptographic_authentication_proven":False,
        "durable_audit_storage_proven":False,
    }

def failure_exhaustion_isolation():
    bad=graph.build("clean",True,13)
    good=graph.build("lidar_dropout",True,13)

    reg=GuardedRegistry(
        max_active=2,max_created=2
    )

    lb,ob=reg.open(
        bad,attempt_budget=3
    )

    lg,og=reg.open(
        good,attempt_budget=14
    )

    rejected=0

    for node in (1,2,3):
        before=reg.summary(lg,og)

        with patch.object(
            r107,
            "least_squares",
            side_effect=attempts.InjectedFault(
                "R117_SYNTHETIC_SOLVER_FAULT"
            )
        ):
            try:
                reg.submit(
                    lb,ob,
                    delivery.make_packet(bad,1),
                    version=0
                )
            except RegistryError as exc:
                need(
                    str(exc)=="CANDIDATE_ABORTED",
                    "FAULT_REJECTION_REASON"
                )
                rejected+=1
            else:
                raise RegistryError(
                    "FAULTY_CANDIDATE_ACKNOWLEDGED"
                )

        need(
            reg.summary(lg,og)==before,
            "FAULT_LEAKED_TO_HEALTHY_SESSION"
        )

        ack=reg.submit(
            lg,og,
            delivery.make_packet(good,node),
            version=node-1
        )

        need(
            ack["acknowledged"] is True,
            "HEALTHY_SESSION_BLOCKED"
        )

    before=reg.summary(lb,ob)

    try:
        reg.submit(
            lb,ob,
            delivery.make_packet(bad,1),
            version=0
        )
    except RegistryError as exc:
        need(
            str(exc)=="ATTEMPT_TOTAL_BUDGET",
            "EXHAUSTION_REJECTION_REASON"
        )
    else:
        raise RegistryError(
            "EXHAUSTED_SESSION_EXECUTED"
        )

    need(
        reg.summary(lb,ob)==before
        and before["attempted_work_units"]==3
        and before["committed_work_units"]==0
        and rejected==3,
        "FAILED_ATTEMPT_CHARGING"
    )

    reg.cancel(lb,ob,version=0)
    bad_receipt=reg.retire(lb,ob)

    reg.submit(
        lg,og,
        delivery.make_packet(good,4),
        version=3
    )

    result,ack=reg.finish(
        lg,og,version=4
    )

    error=lifecycle.validate_result(
        good,result,False
    )

    good_receipt=reg.retire(lg,og)

    need(
        bad_receipt["terminal_phase"]=="CANCELLED"
        and good_receipt["terminal_phase"]=="COMPLETED"
        and good_receipt["attempted_work_units"]==14
        and ack["acknowledged"] is True
        and reg.audit()["active_count"]==0,
        "FAILURE_ISOLATION_COMPLETION"
    )

    return {
        "charged_failed_attempts":3,
        "fourth_attempt_rejected":True,
        "healthy_peer_completed":True,
        "healthy_peer_max_abs_error_vs_s6":error,
        "failure_retirement_phase":"CANCELLED",
        "healthy_retirement_phase":"COMPLETED",
        "retirement_chain_entries":2,
        "registry_drained":True,
        "actual_concurrent_threads_tested":False,
    }

def prepublication_cancellation():
    g=graph.build("clean",True,13)

    reg=GuardedRegistry(
        max_active=1,max_created=1
    )

    lease,owner=reg.open(g)

    entry=reg._active[lease]
    underlying=reg._pool._active[
        entry["handle"]
    ]["session"]

    before=reg.summary(lease,owner)

    def cancel_at_boundary(current,operation):
        need(
            operation=="submit",
            "PREPUBLICATION_OPERATION"
        )

        reg.cancel(
            lease,owner,version=0
        )

    underlying._inner._publication_hook=(
        cancel_at_boundary
    )

    caught=None

    try:
        reg.submit(
            lease,owner,
            delivery.make_packet(g,1),
            version=0
        )
    except RegistryError as exc:
        caught=exc

    underlying._inner._publication_hook=None

    need(
        caught is not None
        and str(caught)=="CANDIDATE_ABORTED",
        "PREPUBLICATION_ABORT"
    )

    after=reg.summary(lease,owner)

    need(
        after["phase"]=="CANCELLED"
        and after["version"]==0
        and after["committed_digest"]==
            before["committed_digest"]
        and after["committed_work_units"]==0
        and after["attempted_work_units"]==1,
        "PREPUBLICATION_CANCELLATION_STATE"
    )

    record=reg.retire(lease,owner)

    need(
        record["terminal_phase"]=="CANCELLED"
        and record["attempted_work_units"]==1,
        "PREPUBLICATION_RETIREMENT"
    )

    try:
        reg.submit(
            lease,owner,
            delivery.make_packet(g,1),
            version=0
        )
    except RegistryError as exc:
        need(
            str(exc)=="STALE_OR_UNKNOWN_HANDLE",
            "CANCELLED_HANDLE_REJECTION"
        )
    else:
        raise RegistryError(
            "CANCELLED_SESSION_RESUMED"
        )

    return {
        "failed_candidate_attempt_units":1,
        "committed_work_units":0,
        "committed_estimator_unchanged":True,
        "candidate_acknowledged":False,
        "cancelled_and_retired":True,
        "stale_handle_reuse_rejected":True,
    }

def execute():
    healthy=healthy_interleaving()
    capacity=stale_handle_and_capacity()
    admission=cross_registry_and_admission()
    integrity=ledger_corruption_controls()
    isolation=failure_exhaustion_isolation()
    cancellation=prepublication_cancellation()

    need(
        healthy["healthy_sessions"]==12
        and healthy["retirement_receipts"]==12
        and healthy["attempted_work_units"]==168,
        "HEALTHY_TOTALS"
    )

    need(
        integrity["detected_corruptions"]==2
        and isolation["charged_failed_attempts"]==3
        and admission["rejection_count"]==6,
        "HARDENING_TOTALS"
    )

    return {
        "schema":SCHEMA,
        "status":
            "PASS_SYNTHETIC_REGISTRY_HARDENING_SOFTWARE_ONLY",

        "healthy_interleaving":healthy,
        "capacity_and_stale_handles":capacity,
        "cross_registry_admissions":admission,
        "ledger_corruption_controls":integrity,
        "failure_exhaustion_isolation":isolation,
        "prepublication_cancellation":cancellation,

        "healthy_sessions":12,
        "acknowledged_operations":60,
        "healthy_attempted_work_units":168,
        "healthy_retirement_receipts":12,

        "corruption_controls_rejected":2,
        "cross_registry_admissions_rejected":6,
        "charged_failed_attempts":3,

        "linked_retirement_ledger_verified":True,
        "local_opaque_handles_verified":True,
        "retired_handle_reuse_denied":True,
        "committed_failure_isolation_verified":True,

        "authenticated_audit_log_verified":False,
        "durable_audit_log_verified":False,
        "physical_memory_reclamation_verified":False,
        "actual_concurrent_thread_safety_verified":False,
        "direct_private_object_mutation_isolated":False,
        "cryptographic_owner_authentication_verified":False,
        "hardware_streaming_verified":False,
        "physical_resource_deadlines_verified":False,

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

    print("R117_SYNTHETIC_REGISTRY_HARDENING=PASS")
    print("R117_HEALTHY_SESSIONS=12")
    print("R117_ACKNOWLEDGED_OPERATIONS=60")
    print("R117_ATTEMPTED_WORK_UNITS=168")
    print("R117_RETIRED_RECEIPTS=12")
    print("R117_CORRUPTION_CONTROLS_REJECTED=2")
    print("R117_CROSS_REGISTRY_INVALID_ADMISSIONS=6")
    print("R117_FAILED_ATTEMPTS_CHARGED=3")
    print("R117_RETIRED_HANDLE_REUSE=DENIED")
    print("R117_PREPUBLICATION_CANCELLATION=PASS")
    print("R117_DURABLE_AUDIT_LOG=NOT_PROVEN")
    print("R117_CONCURRENT_THREAD_SAFETY=NOT_PROVEN")
