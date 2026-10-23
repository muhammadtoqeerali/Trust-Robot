"""R116 synthetic resource lifecycle and fault-pattern audit.

A small bounded registry manages R114 attempt-budget
sessions and permits explicit terminal retirement.

The registry's capacity limits are Python-level
reference counts, NOT physical memory limits.

Interleaving is deterministic and single-threaded,
not a concurrency or distributed-systems proof.
"""

import json
from dataclasses import replace
from unittest.mock import patch

import r104_shared_graph as graph
import r107_incremental as r107
import r108_delivery as delivery
import r114_attempts as attempts
import s6_joint_fusion as s6

SCHEMA="TRUST_ROBOT_R116_SYNTHETIC_SESSION_LIFECYCLE_V1"

SCENARIOS=(
    ("clean_joint","clean",True),
    ("lidar_dropout_joint","lidar_dropout",True),
    ("clean_camera_off","clean",False),
)

SCHEDULES={
    "ordered":(1,2,3,4),
    "bounded_reorder":(3,2,1,4),
}

class LifecycleError(ValueError):
    pass

def need(flag,reason):
    if not flag:
        raise LifecycleError(reason)

def canonical(obj):
    return (
        json.dumps(
            obj,
            sort_keys=True,
            indent=2,
            allow_nan=False
        )+"\n"
    ).encode("utf-8")

class SessionPool:
    """Bounded registry of R114 synthetic sessions.

    A retired handle cannot be activated again.
    Retirement drops the registry's live reference.

    Garbage collection, secure erasure, memory
    reclamation and isolation are NOT demonstrated.
    """

    def __init__(self,*,max_active=2,max_created=12):
        need(
            type(max_active) is int
            and 1<=max_active<=2,
            "ACTIVE_CAPACITY"
        )
        need(
            type(max_created) is int
            and max_active<=max_created<=12,
            "CREATION_CAPACITY"
        )

        self.max_active=max_active
        self.max_created=max_created

        self._active={}
        self._retired={}
        self._issued=0
        self._peak_active=0

    def audit(self):
        return {
            "created":self._issued,
            "active_count":len(self._active),
            "retired_count":len(self._retired),
            "peak_active":self._peak_active,
            "active_handles":sorted(self._active),
            "retired_handles":sorted(self._retired),
        }

    def open(
        self,g,*,
        recenter=False,
        attempt_budget=14
    ):
        need(
            len(self._active)<self.max_active,
            "ACTIVE_CAPACITY_EXCEEDED"
        )

        need(
            self._issued<self.max_created,
            "CREATION_LIMIT_EXCEEDED"
        )

        try:
            graph.validate(g)
        except graph.GraphAdmissionError as exc:
            raise LifecycleError(
                "GRAPH_ADMISSION_DENIED"
            ) from exc

        session,owner=attempts.open_session(
            g,
            recenter=recenter,
            max_attempt_total_units=attempt_budget
        )

        next_id=self._issued+1
        handle="S%04d"%next_id

        need(
            handle not in self._active
            and handle not in self._retired,
            "HANDLE_REUSE"
        )

        self._active[handle]={
            "session":session,
            "owner":owner,
        }

        self._issued=next_id

        self._peak_active=max(
            self._peak_active,
            len(self._active)
        )

        return handle,owner

    def _select(self,handle,owner):
        need(
            type(handle) is str
            and handle in self._active,
            "HANDLE_NOT_ACTIVE"
        )

        entry=self._active[handle]

        need(
            owner is entry["owner"],
            "OWNER_MISMATCH"
        )

        return entry["session"]

    def summary(self,handle,owner):
        return self._select(handle,owner).summary()

    def submit(self,handle,owner,packet,*,version):
        session=self._select(handle,owner)

        try:
            return session.submit(
                owner,
                packet,
                expected_version=version
            )
        except attempts.AttemptError as exc:
            raise LifecycleError(str(exc)) from exc

    def finish(self,handle,owner,*,version):
        session=self._select(handle,owner)

        try:
            return session.finish(
                owner,
                expected_version=version
            )
        except attempts.AttemptError as exc:
            raise LifecycleError(str(exc)) from exc

    def cancel(self,handle,owner,*,version):
        session=self._select(handle,owner)

        try:
            return session.cancel(
                owner,
                expected_version=version
            )
        except attempts.AttemptError as exc:
            raise LifecycleError(str(exc)) from exc

    def retire(self,handle,owner):
        session=self._select(handle,owner)

        need(
            session.phase in ("COMPLETED","CANCELLED"),
            "NONTERMINAL_RETIREMENT"
        )

        state=session.summary()

        receipt={
            "handle":handle,
            "terminal_phase":session.phase,
            "version":session.version,
            "attempted_work_units":
                session.attempted_work_units,
            "committed_work_units":
                session.committed_work_units,
            "committed_digest":
                session.committed_digest(),
            "retired":True,
        }

        need(
            len(self._retired)<self.max_created,
            "RETIREMENT_LEDGER_FULL"
        )

        self._retired[handle]=receipt

        # This releases the pool's reference, but
        # does not guarantee Python memory erasure.
        del self._active[handle]

        need(
            handle not in self._active
            and handle in self._retired,
            "RETIREMENT_FAILED"
        )

        return dict(receipt)

def validate_result(g,result,recenter):
    reference,audit=s6.estimate_joint(
        g["fixture"],
        g["camera_packets"]
    )

    error=delivery.state_error(
        result,reference
    )

    need(
        error<(2e-5 if recenter else 1e-8),
        "ORIGINAL_S6_DISAGREEMENT"
    )

    need(
        result["consumed_pose_ids"]==
            audit["consumed_pose_ids"]
        and result["remaining_pose_ids"]==
            audit["remaining_pose_ids"]
        and result["admitted_sample_indices"]==
            list(range(8)),
        "FACTOR_OWNERSHIP"
    )

    need(
        len(result["windows"])==4
        and len(result["eliminations"])==3
        and len(result["transfer_events"])==
            (3 if recenter else 0)
        and result["future_factor_usage"] is False
        and result["factor_reuse"] is False,
        "WINDOW_OR_FACTOR_REUSE"
    )

    return error

def interleaved_sessions():
    """Sequential interleaving, never simultaneous threads."""

    jobs=[]

    for name,condition,camera in SCENARIOS:
        for schedule,order in SCHEDULES.items():
            for recenter in (False,True):
                jobs.append({
                    "name":(
                        name+"_"+schedule+
                        ("_recentered" if recenter else "_ordinary")
                    ),
                    "graph":graph.build(
                        condition,camera,13
                    ),
                    "order":order,
                    "recenter":recenter,
                })

    need(len(jobs)==12,"JOB_COUNT")

    pool=SessionPool(
        max_active=2,
        max_created=12
    )

    rows={}

    for start in range(0,len(jobs),2):
        pair=jobs[start:start+2]

        for job in pair:
            h,owner=pool.open(
                job["graph"],
                recenter=job["recenter"]
            )
            job["handle"]=h
            job["owner"]=owner

        need(
            pool.audit()["active_count"]==2,
            "PAIR_CAPACITY"
        )

        # Deliberate interleaving, but no threads.
        for position in range(4):
            for job in pair:
                h=job["handle"]
                lease=job["owner"]

                version=pool.summary(
                    h,lease
                )["version"]

                response=pool.submit(
                    h,
                    lease,
                    delivery.make_packet(
                        job["graph"],
                        job["order"][position]
                    ),
                    version=version
                )

                need(
                    response["acknowledged"] is True
                    and response["sequence"]==
                        position+1,
                    "INTERLEAVED_ACK"
                )

        for job in pair:
            h=job["handle"]
            owner=job["owner"]

            result,ack=pool.finish(
                h,
                owner,
                version=4
            )

            need(
                ack["acknowledged"] is True
                and ack["sequence"]==5,
                "FINALIZATION_ACK"
            )

            error=validate_result(
                job["graph"],
                result,
                job["recenter"]
            )

            before=pool.summary(
                h,owner
            )

            need(
                before["phase"]=="COMPLETED"
                and before["version"]==5
                and before["attempted_work_units"]==14
                and before["committed_work_units"]==14,
                "COMPLETED_BUDGET_LEDGER"
            )

            retired=pool.retire(
                h,owner
            )

            need(
                retired["terminal_phase"]=="COMPLETED",
                "RETIRE_COMPLETED_SESSION"
            )

            rows[job["name"]]={
                "arrival_order":list(job["order"]),
                "recentered":job["recenter"],
                "acknowledged_operations":5,
                "attempted_work_units":14,
                "committed_work_units":14,
                "nonlinear_windows":4,
                "schur_marginalizations":3,
                "prior_transfers":
                    3 if job["recenter"] else 0,
                "max_abs_error_vs_s6":error,
                "retired":True,
                "factor_ownership_verified":True,
            }

        need(
            pool.audit()["active_count"]==0,
            "PAIR_REFS_NOT_RELEASED"
        )

    final=pool.audit()

    need(
        final["created"]==12
        and final["retired_count"]==12
        and final["active_count"]==0
        and final["peak_active"]==2,
        "INTERLEAVED_LIFECYCLE_LEDGER"
    )

    return {
        "runs":rows,
        "session_count":12,
        "acknowledged_operations":60,
        "attempted_work_units":168,
        "nonlinear_windows":48,
        "schur_marginalizations":36,
        "same_graph_prior_transfers":18,
        "pool_audit":final,
        "simultaneous_threads_executed":False,
    }

def capacity_and_retirement():
    g=graph.build("clean",True,13)

    pool=SessionPool(
        max_active=2,
        max_created=3
    )

    h1,o1=pool.open(g)
    h2,o2=pool.open(g)

    before=pool.audit()

    try:
        pool.open(g)
    except LifecycleError as exc:
        need(
            str(exc)=="ACTIVE_CAPACITY_EXCEEDED",
            "WRONG_ACTIVE_CAPACITY_DENIAL"
        )
    else:
        raise LifecycleError(
            "CAPACITY_EXCEEDED_BUT_ADMITTED"
        )

    need(
        pool.audit()==before,
        "REJECTED_OPEN_MUTATED_REGISTRY"
    )

    pool.cancel(h1,o1,version=0)
    pool.retire(h1,o1)

    h3,o3=pool.open(g)

    need(
        len({h1,h2,h3})==3,
        "HANDLE_REISSUED"
    )

    for handle,owner in (
        (h2,o2),
        (h3,o3),
    ):
        pool.cancel(
            handle,owner,version=0
        )
        pool.retire(handle,owner)

    before=pool.audit()

    try:
        pool.open(g)
    except LifecycleError as exc:
        need(
            str(exc)=="CREATION_LIMIT_EXCEEDED",
            "WRONG_CREATION_LIMIT_DENIAL"
        )
    else:
        raise LifecycleError(
            "CREATION_LIMIT_BYPASSED"
        )

    need(
        before==pool.audit()
        and before["created"]==3
        and before["retired_count"]==3
        and before["active_count"]==0,
        "RETIREMENT_CAPACITY_HISTORY"
    )

    for handle,owner in (
        (h1,o1),
        (h2,o2),
        (h3,o3),
    ):
        try:
            pool.summary(handle,owner)
        except LifecycleError as exc:
            need(
                str(exc)=="HANDLE_NOT_ACTIVE",
                "RETIRED_HANDLE_DENIAL"
            )
        else:
            raise LifecycleError(
                "RETIRED_HANDLE_REUSED"
            )

    return {
        "active_capacity_denials":1,
        "creation_limit_denials":1,
        "unique_handles":3,
        "retired_handles":3,
        "peak_active":2,
        "active_after_retirement":0,
        "retired_handle_reuses_denied":3,
        "physical_memory_reclamation_verified":False,
    }

def fault_isolation():
    """Faulty and healthy sessions share only a registry."""

    bad=graph.build("clean",True,13)
    good=graph.build(
        "lidar_dropout",True,13
    )

    pool=SessionPool(
        max_active=2,
        max_created=2
    )

    hb,ob=pool.open(
        bad,
        attempt_budget=3
    )

    hg,og=pool.open(
        good,
        attempt_budget=14
    )

    # A packet manufactured for another graph
    # must be rejected before budget charging.
    before_bad=pool.summary(hb,ob)

    try:
        pool.submit(
            hb,ob,
            delivery.make_packet(good,1),
            version=0
        )
    except LifecycleError as exc:
        need(
            str(exc)=="ADMISSION_REJECTED",
            "CROSS_SESSION_DENIAL"
        )
    else:
        raise LifecycleError(
            "CROSS_SESSION_PACKET_ACCEPTED"
        )

    need(
        pool.summary(hb,ob)==before_bad,
        "CROSS_GRAPH_PACKET_CHARGED"
    )

    failures=0

    for node in (1,2,3):
        good_before=pool.summary(hg,og)

        with patch.object(
            r107,
            "least_squares",
            side_effect=attempts.InjectedFault(
                "R116_SYNTHETIC_SOLVER_FAULT"
            )
        ):
            try:
                pool.submit(
                    hb,ob,
                    delivery.make_packet(bad,1),
                    version=0
                )
            except LifecycleError as exc:
                need(
                    str(exc)=="CANDIDATE_ABORTED",
                    "INJECTED_FAULT_DENIAL"
                )
                failures+=1
            else:
                raise LifecycleError(
                    "FAULTY_PACKET_ACKNOWLEDGED"
                )

        need(
            pool.summary(hg,og)==good_before,
            "FAULT_LEAKED_TO_OTHER_SESSION"
        )

        response=pool.submit(
            hg,og,
            delivery.make_packet(good,node),
            version=node-1
        )

        need(
            response["acknowledged"] is True,
            "UNRELATED_HEALTHY_SESSION_BLOCKED"
        )

    fault_state=pool.summary(hb,ob)

    need(
        failures==3
        and fault_state["attempted_work_units"]==3
        and fault_state["committed_work_units"]==0
        and fault_state["version"]==0,
        "FAULT_BUDGET_ACCOUNTING"
    )

    before=pool.summary(hb,ob)

    try:
        pool.submit(
            hb,ob,
            delivery.make_packet(bad,1),
            version=0
        )
    except LifecycleError as exc:
        need(
            str(exc)=="ATTEMPT_TOTAL_BUDGET",
            "EXHAUSTION_DENIAL"
        )
    else:
        raise LifecycleError(
            "EXHAUSTED_SESSION_EXECUTED"
        )

    need(
        pool.summary(hb,ob)==before,
        "EXHAUSTION_CHANGED_STATE"
    )

    pool.cancel(hb,ob,version=0)
    bad_receipt=pool.retire(hb,ob)

    response=pool.submit(
        hg,og,
        delivery.make_packet(good,4),
        version=3
    )

    need(
        response["acknowledged"] is True,
        "HEALTHY_FINISH_PACKET_FAILED"
    )

    result,ack=pool.finish(
        hg,og,version=4
    )

    error=validate_result(
        good,result,False
    )

    good_receipt=pool.retire(hg,og)

    need(
        ack["acknowledged"] is True
        and bad_receipt["terminal_phase"]=="CANCELLED"
        and bad_receipt["attempted_work_units"]==3
        and good_receipt["terminal_phase"]=="COMPLETED"
        and good_receipt["attempted_work_units"]==14,
        "INDEPENDENT_RETIREMENT_LEDGER"
    )

    final=pool.audit()

    need(
        final["active_count"]==0
        and final["retired_count"]==2,
        "FAULT_SESSION_POOL_NOT_DRAINED"
    )

    return {
        "injected_failed_attempts":3,
        "charged_failed_work_units":3,
        "cross_graph_packet_rejections":1,
        "exhausted_fourth_attempt_rejected":True,
        "unrelated_session_completed":True,
        "unrelated_max_abs_error_vs_s6":error,
        "faulty_session_retired":True,
        "healthy_session_retired":True,
        "registry_active_after":0,
        "actual_parallel_threads_tested":False,
    }

def prepublication_retirement():
    """Simulated cancellation at a candidate publication seam."""

    g=graph.build("clean",True,13)

    pool=SessionPool(
        max_active=1,
        max_created=1
    )

    handle,owner=pool.open(g)

    # Instrument the local candidate hook; no threads.
    session=pool._active[handle]["session"]

    before=pool.summary(
        handle,owner
    )

    def cancel_at_boundary(current,operation):
        need(
            operation=="submit",
            "WRONG_PUBLICATION_STAGE"
        )

        pool.cancel(
            handle,owner,version=0
        )

    session._inner._publication_hook=cancel_at_boundary

    caught=None

    try:
        pool.submit(
            handle,
            owner,
            delivery.make_packet(g,1),
            version=0
        )
    except LifecycleError as exc:
        caught=exc

    session._inner._publication_hook=None

    need(
        caught is not None
        and str(caught)=="CANDIDATE_ABORTED",
        "CANCELLATION_NOT_PROPAGATED"
    )

    after=pool.summary(
        handle,owner
    )

    need(
        after["phase"]=="CANCELLED"
        and after["version"]==0
        and after["attempted_work_units"]==1
        and after["committed_work_units"]==0
        and after["committed_digest"]==
            before["committed_digest"],
        "CANCELLATION_PUBLISHED_FAILED_CANDIDATE"
    )

    receipt=pool.retire(handle,owner)

    need(
        receipt["terminal_phase"]=="CANCELLED"
        and receipt["attempted_work_units"]==1
        and pool.audit()["active_count"]==0,
        "CANCELLED_ATTEMPT_RETIREMENT"
    )

    try:
        pool.submit(
            handle,owner,
            delivery.make_packet(g,1),
            version=0
        )
    except LifecycleError as exc:
        need(
            str(exc)=="HANDLE_NOT_ACTIVE",
            "RETIRED_SESSION_DENIAL"
        )
    else:
        raise LifecycleError(
            "CANCELLED_SESSION_RESUMED"
        )

    return {
        "attempted_work_units_charged":1,
        "committed_work_units":0,
        "committed_state_unchanged":True,
        "candidate_acknowledged":False,
        "cancelled_session_retired":True,
        "retired_handle_reuse_rejected":True,
        "concurrent_cancellation_verified":False,
    }

def admission_fault_patterns():
    g=graph.build("clean",True,13)

    other=graph.build(
        "lidar_dropout",True,13
    )

    pool=SessionPool(
        max_active=1,
        max_created=1
    )

    h,owner=pool.open(g)
    packet=delivery.make_packet(g,1)

    faults=(
        (
            "wrong_owner",
            object(),
            packet,
            0,
            "OWNER_MISMATCH"
        ),
        (
            "stale_version",
            owner,
            packet,
            1,
            "STALE_VERSION"
        ),
        (
            "future_node",
            owner,
            delivery.make_packet(g,4),
            0,
            "ADMISSION_REJECTED"
        ),
        (
            "cross_graph",
            owner,
            delivery.make_packet(other,1),
            0,
            "ADMISSION_REJECTED"
        ),
        (
            "false_frame",
            owner,
            replace(
                packet,
                frame_id="RECORDED_BODY"
            ),
            0,
            "ADMISSION_REJECTED"
        ),
        (
            "false_real_sensor",
            owner,
            replace(
                packet,
                real_sensor_factors_authorized=True
            ),
            0,
            "ADMISSION_REJECTED"
        ),
        (
            "missing_imu",
            owner,
            replace(
                packet,
                readings=packet.readings[:1]
            ),
            0,
            "ADMISSION_REJECTED"
        ),
        (
            "bad_node_time",
            owner,
            replace(
                packet,
                node_time_ns=packet.node_time_ns+1
            ),
            0,
            "ADMISSION_REJECTED"
        ),
    )

    rejected=[]

    for name,who,p,version,expected in faults:
        before=pool.summary(h,owner)

        try:
            pool.submit(
                h,who,p,version=version
            )
        except LifecycleError as exc:
            need(
                str(exc)==expected,
                "INVALID_ADMISSION_ERROR:"+name
            )
            rejected.append(name)
        else:
            raise LifecycleError(
                "INVALID_DELIVERY_ACCEPTED:"+name
            )

        need(
            pool.summary(h,owner)==before,
            "REJECTION_CHANGED_STATE:"+name
        )

    pool.submit(h,owner,packet,version=0)

    for name,action,expected in (
        (
            "duplicate",
            lambda:pool.submit(
                h,owner,packet,version=1
            ),
            "ADMISSION_REJECTED"
        ),
        (
            "incomplete_finish",
            lambda:pool.finish(
                h,owner,version=1
            ),
            "INCOMPLETE_SESSION"
        ),
    ):
        before=pool.summary(h,owner)

        try:
            action()
        except LifecycleError as exc:
            need(
                str(exc)==expected,
                "POST_ADMISSION_DENIAL:"+name
            )
            rejected.append(name)
        else:
            raise LifecycleError(
                "UNSAFE_OPERATION_ACCEPTED:"+name
            )

        need(
            pool.summary(h,owner)==before,
            "POST_ADMISSION_MUTATED:"+name
        )

    for node in (2,3,4):
        pool.submit(
            h,owner,
            delivery.make_packet(g,node),
            version=node-1
        )

    result,ack=pool.finish(
        h,owner,version=4
    )

    error=validate_result(
        g,result,False
    )

    receipt=pool.retire(h,owner)

    need(
        len(rejected)==10
        and receipt["attempted_work_units"]==14
        and receipt["committed_work_units"]==14
        and ack["acknowledged"] is True,
        "INVALID_ADMISSION_RECOVERY"
    )

    return {
        "rejected_fault_patterns":rejected,
        "rejected_count":10,
        "attempted_work_charged_for_invalid_operations":0,
        "eventual_successful_completion":True,
        "max_abs_error_vs_s6":error,
        "session_retired":True,
    }

def execute():
    healthy=interleaved_sessions()
    capacity=capacity_and_retirement()
    isolation=fault_isolation()
    cancellation=prepublication_retirement()
    admissions=admission_fault_patterns()

    need(
        healthy["session_count"]==12
        and healthy["attempted_work_units"]==168
        and len(healthy["runs"])==12,
        "HEALTHY_TOTALS"
    )

    need(
        isolation["injected_failed_attempts"]==3
        and admissions["rejected_count"]==10,
        "FAULT_PATTERN_TOTALS"
    )

    return {
        "schema":SCHEMA,
        "status":
            "PASS_SYNTHETIC_SESSION_LIFECYCLE_SOFTWARE_ONLY",

        "interleaved_sessions":healthy,
        "capacity_and_retirement":capacity,
        "fault_isolation":isolation,
        "prepublication_retirement":cancellation,
        "admission_fault_patterns":admissions,

        "healthy_sessions":12,
        "healthy_committed_operations":60,
        "healthy_replay_work_units":168,

        "capacity_rejections":2,
        "failed_attempts_charged":3,
        "invalid_admission_patterns_rejected":10,

        "bounded_registry_capacity_verified":True,
        "retired_handle_reuse_rejected":True,
        "unrelated_session_failure_isolation_verified":True,

        "actual_concurrent_thread_safety_verified":False,
        "physical_memory_reclamation_verified":False,
        "wall_clock_resource_bound_verified":False,
        "durable_registry_recovery_verified":False,
        "cryptographic_owner_authentication_verified":False,
        "private_python_object_isolation_verified":False,
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
        sys.argv[1],
        "x",
        encoding="utf-8"
    ) as f:
        f.write(canonical(report).decode("utf-8"))

    print("R116_SYNTHETIC_SESSION_LIFECYCLE=PASS")
    print("R116_HEALTHY_INTERLEAVED_SESSIONS=12")
    print("R116_HEALTHY_ACKNOWLEDGED_OPERATIONS=60")
    print("R116_HEALTHY_REPLAY_WORK_UNITS=168")
    print("R116_POOL_PEAK_ACTIVE=2")
    print("R116_CAPACITY_REJECTIONS=2")
    print("R116_INJECTED_FAILURES_CHARGED=3")
    print("R116_INVALID_EVENT_PATTERNS_DENIED=10")
    print("R116_PREPUBLICATION_CANCELLATION=PASS")
    print("R116_RETIRED_HANDLE_REUSE=DENIED")
    print("R116_CONCURRENT_THREAD_SAFETY=NOT_PROVEN")
