"""R110 — manufactured failure atomicity and fail-stop audit.

R108 may mutate buffer and estimator state before a numerical
failure. R110 quarantines that session rather than retrying.

This does NOT implement transactional solver rollback.
No hardware, real factor, network or physical timing evidence.
"""

import hashlib
import json
from dataclasses import replace
from unittest.mock import patch

import numpy as np

import r104_shared_graph as graph
import r107_incremental as r107
import r108_delivery as r108
import s6_joint_fusion as s6

SCHEMA="TRUST_ROBOT_R110_SYNTHETIC_FAIL_STOP_AUDIT_V1"

CASES=(
    ("clean_joint","clean",True),
    ("lidar_dropout_joint","lidar_dropout",True),
    ("clean_camera_off","clean",False),
)

FAULTS=(
    "imu_prediction",
    "nonlinear_optimization",
    "schur_marginalization",
    "prior_recentering",
    "post_processing_acknowledgement",
    "finalization",
)

class SessionError(ValueError):
    pass

class InjectedFault(RuntimeError):
    pass

def need(ok,reason):
    if not ok:
        raise SessionError(reason)

def canonical(obj):
    return (
        json.dumps(
            obj,sort_keys=True,indent=2,allow_nan=False
        )+"\n"
    ).encode()

def digest(obj):
    return hashlib.sha256(canonical(obj)).hexdigest()

def snapshot(buffer):
    """Read-only snapshot for fault-state comparison.

    This is a diagnostic observation, not a rollback image.
    """
    e=buffer.estimator

    estimator={
        "next_node":e.next_node,
        "live_nodes":list(e.live),
        "admitted_imu_edges":[
            list(edge)
            for edge in sorted(e.admitted_imu)
        ],
        "admitted_pose_ids":sorted(e.admitted_pose),
        "admitted_samples":sorted(e.admitted_samples),
        "consumed_imu_edges":[
            list(edge)
            for edge in sorted(e.consumed_imu)
        ],
        "consumed_pose_ids":sorted(e.consumed_pose),
        "window_count":len(e.windows),
        "marginalization_count":len(e.eliminations),
        "transfer_count":len(e.transfer_events),
        "states":{
            str(node):np.asarray(value).tolist()
            for node,value in sorted(e.states.items())
        },
        "prior_node_ids":list(e.prior.node_ids),
        "prior_reference":
            np.asarray(e.prior.reference).tolist(),
        "prior_offset":
            np.asarray(e.prior.residual_offset).tolist(),
    }

    queue={
        "pending_nodes":sorted(buffer.pending),
        "received_nodes":sorted(buffer.received),
        "arrival_order":list(buffer.arrival_order),
        "processed_order":list(buffer.processed_order),
        "peak_pending":buffer.peak_pending,
        "closed":buffer.closed,
    }

    return {
        "queue":queue,
        "estimator":estimator,
        "queue_sha256":digest(queue),
        "estimator_sha256":digest(estimator),
    }

class FailStopSession:
    """Public fail-stop boundary around R108.

    Admission failures are rejected without poisoning.
    Internal execution failures poison the session.

    All operations through this wrapper are denied once
    faulted. Direct private-object access is not isolated.
    """

    def __init__(self,g,*,recenter=False):
        self._buffer=r108.DeliveryBuffer(
            g,recenter=recenter
        )
        self.state="ACTIVE"
        self.fault_receipt=None

    def _active(self):
        need(
            self.state=="ACTIVE",
            "SESSION_NOT_ACTIVE"
        )

    def _admit_without_mutation(self,p):
        """Validate before calling R108.submit."""
        try:
            self._buffer.validate_packet(p)

            b=self._buffer
            next_node=b.estimator.next_node

            r108.need(
                not b.closed
                and p.node>=next_node
                and p.node not in b.received,
                "DUPLICATE_OR_STALE"
            )

            r108.need(
                p.node-next_node<=b.max_ahead,
                "REORDER_HORIZON"
            )

            if p.node!=next_node:
                r108.need(
                    len(b.pending)<b.max_pending,
                    "BUFFER_FULL"
                )

        except r108.DeliveryError as exc:
            raise SessionError(
                "ADMISSION_REJECTED"
            ) from exc

    def _poison(self,operation,before,exc):
        after=snapshot(self._buffer)

        self.state="FAULTED"

        self.fault_receipt={
            "operation":operation,
            "exception_type":type(exc).__name__,
            "queue_changed_before_fault":
                before["queue_sha256"]!=
                after["queue_sha256"],
            "estimator_changed_before_fault":
                before["estimator_sha256"]!=
                after["estimator_sha256"],
            "pre_queue_sha256":
                before["queue_sha256"],
            "post_queue_sha256":
                after["queue_sha256"],
            "pre_estimator_sha256":
                before["estimator_sha256"],
            "post_estimator_sha256":
                after["estimator_sha256"],
            "next_node_after_failure":
                self._buffer.estimator.next_node,
            "continued_execution_authorized":False,
            "successful_acknowledgement_issued":False,
            "transactional_rollback_performed":False,
        }

    def submit(self,p):
        self._active()
        self._admit_without_mutation(p)

        before=snapshot(self._buffer)

        try:
            return self._buffer.submit(p)
        except Exception as exc:
            self._poison("submit",before,exc)

            raise SessionError(
                "SESSION_FAULTED_NO_ACK"
            ) from exc

    def finish(self):
        self._active()

        b=self._buffer

        need(
            b.estimator.next_node==5
            and not b.pending
            and b.received=={1,2,3,4},
            "INCOMPLETE_SESSION"
        )

        before=snapshot(b)

        try:
            result=b.finish()
        except Exception as exc:
            self._poison("finish",before,exc)

            raise SessionError(
                "SESSION_FAULTED_NO_ACK"
            ) from exc

        self.state="COMPLETED"
        return result

def fresh_success(condition="clean",camera=True,
                  recenter=False,order=(3,2,1,4)):
    """Fresh state only. Never resume a failed buffer."""
    g=graph.build(condition,camera,13)
    session=FailStopSession(g,recenter=recenter)

    for node in order:
        session.submit(
            r108.make_packet(g,node)
        )

    result=session.finish()

    need(
        session.state=="COMPLETED"
        and session.fault_receipt is None,
        "FRESH_SESSION_NOT_COMPLETED"
    )

    expected,audit=s6.estimate_joint(
        g["fixture"],g["camera_packets"]
    )

    error=r108.state_error(result,expected)

    need(
        error<(2e-5 if recenter else 1e-8),
        "UNMODIFIED_S6_DISAGREEMENT"
    )

    need(
        result["consumed_pose_ids"]==
            audit["consumed_pose_ids"]
        and result["remaining_pose_ids"]==
            audit["remaining_pose_ids"],
        "POSE_OWNERSHIP_MISMATCH"
    )

    need(
        result["admitted_sample_indices"]==
            list(range(8))
        and len(result["windows"])==4
        and len(result["eliminations"])==3
        and len(result["transfer_events"])==
            (3 if recenter else 0),
        "FRESH_ESTIMATOR_COUNTS"
    )

    return {
        "recenter":recenter,
        "arrival_order":list(order),
        "max_abs_error_vs_original_s6":error,
        "windows":4,
        "marginalizations":3,
        "prior_transfers":3 if recenter else 0,
        "completed":True,
        "source":"ANALYTIC_FIXTURE",
        "physical_streaming_verified":False,
    }

def fault_case(kind):
    need(kind in FAULTS,"UNKNOWN_FAULT")

    g=graph.build("clean",True,13)

    recenter=(kind=="prior_recentering")
    session=FailStopSession(g,recenter=recenter)

    if kind in (
        "schur_marginalization",
        "prior_recentering",
    ):
        session.submit(
            r108.make_packet(g,1)
        )

    target=(
        2 if kind in (
            "schur_marginalization",
            "prior_recentering",
        ) else 1
    )

    error=None

    if kind=="imu_prediction":
        context=patch.object(
            r107.s6,
            "predict_imu",
            side_effect=InjectedFault("PREDICT_INJECTED")
        )

    elif kind=="nonlinear_optimization":
        context=patch.object(
            r107,
            "least_squares",
            side_effect=InjectedFault("OPTIMIZER_INJECTED")
        )

    elif kind=="schur_marginalization":
        context=patch.object(
            r107.s6,
            "marginalize_one",
            side_effect=InjectedFault("SCHUR_INJECTED")
        )

    elif kind=="prior_recentering":
        context=patch.object(
            r107.transfer,
            "transfer",
            side_effect=InjectedFault("RECENTER_INJECTED")
        )

    elif kind=="post_processing_acknowledgement":
        original=session._buffer.submit

        def post_processing_fault(p):
            original(p)
            raise InjectedFault("POST_PROCESSING_INJECTED")

        context=patch.object(
            session._buffer,
            "submit",
            side_effect=post_processing_fault
        )

    else:
        # Finish-stage failure after four accepted nodes.
        for node in range(1,5):
            session.submit(
                r108.make_packet(g,node)
            )

        context=patch.object(
            session._buffer,
            "finish",
            side_effect=InjectedFault("FINISH_INJECTED")
        )

    with context:
        try:
            if kind=="finalization":
                session.finish()
            else:
                session.submit(
                    r108.make_packet(g,target)
                )
        except SessionError as exc:
            error=exc

    need(
        error is not None
        and str(error)=="SESSION_FAULTED_NO_ACK"
        and isinstance(error.__cause__,InjectedFault),
        "FAULT_NOT_CONTAINED"
    )

    need(
        session.state=="FAULTED"
        and type(session.fault_receipt) is dict,
        "FAIL_STOP_NOT_ENTERED"
    )

    receipt=session.fault_receipt

    need(
        receipt["exception_type"]=="InjectedFault"
        and receipt["continued_execution_authorized"] is False
        and receipt["successful_acknowledgement_issued"] is False
        and receipt["transactional_rollback_performed"] is False,
        "FAULT_RECEIPT_BOUNDARY"
    )

    # Neither retry nor finish may use the failed session.
    before=snapshot(session._buffer)

    rejected=0

    for call in (
        lambda:session.submit(
            r108.make_packet(g,4)
        ),
        lambda:session.finish(),
    ):
        try:
            call()
        except SessionError as exc:
            need(
                str(exc)=="SESSION_NOT_ACTIVE",
                "WRONG_FAULTED_STATE_DENIAL"
            )
            rejected+=1
        else:
            raise SessionError(
                "FAULTED_SESSION_REUSED"
            )

    after=snapshot(session._buffer)

    need(
        rejected==2
        and before==after,
        "FAULTED_STATE_CHANGED_ON_RETRY"
    )

    graph.validate(g)

    return {
        "injection_point":kind,
        "fault_receipt":receipt,
        "session_quarantined":True,
        "post_fault_operations_rejected":2,
        "post_fault_state_unchanged_on_rejection":True,
        "original_graph_still_valid":True,
        "rollback_proven":False,
    }

def admission_case():
    """Invalid packets must not poison a healthy session."""

    g=graph.build("clean",True,13)
    session=FailStopSession(g)

    p=r108.make_packet(g,1)

    other=graph.build("clean",True,13)

    rejected=0

    invalid=(
        replace(p,frame_id="RECORDED_BODY"),
        replace(
            p,real_sensor_factors_authorized=True
        ),
        replace(
            p,node_time_ns=p.node_time_ns+1
        ),
        replace(
            p,session="UNTRUSTED_SESSION"
        ),
        replace(
            p,
            readings=(
                dict(p.readings[0]),
                p.readings[1],
            )
        ),
        r108.make_packet(g,4),
        r108.make_packet(other,1),
    )

    for candidate in invalid:
        before=snapshot(session._buffer)

        try:
            session.submit(candidate)
        except SessionError as exc:
            need(
                str(exc)=="ADMISSION_REJECTED",
                "WRONG_ADMISSION_DENIAL"
            )
            rejected+=1
        else:
            raise SessionError(
                "INVALID_DELIVERY_ADMITTED"
            )

        need(
            session.state=="ACTIVE"
            and snapshot(session._buffer)==before,
            "PRE_ADMISSION_STATE_MUTATED"
        )

    session.submit(p)

    before=snapshot(session._buffer)

    try:
        session.submit(p)
    except SessionError as exc:
        need(
            str(exc)=="ADMISSION_REJECTED",
            "DUPLICATE_DENIAL"
        )
        rejected+=1
    else:
        raise SessionError(
            "DUPLICATE_DELIVERY_ACCEPTED"
        )

    need(
        session.state=="ACTIVE"
        and snapshot(session._buffer)==before,
        "DUPLICATE_CHANGED_STATE"
    )

    for node in range(2,5):
        session.submit(
            r108.make_packet(g,node)
        )

    result=session.finish()

    need(
        rejected==8
        and session.state=="COMPLETED"
        and len(result["windows"])==4,
        "PRE_ADMISSION_RECOVERY"
    )

    return {
        "pre_admission_rejections":rejected,
        "state_unchanged_on_rejection":True,
        "healthy_session_remained_usable":True,
        "rollback_required":False,
    }

def execute():
    healthy={}

    for name,condition,camera in CASES:
        for recenter in (False,True):
            key=name+(
                "_recentered" if recenter
                else "_ordinary"
            )
            healthy[key]=fresh_success(
                condition,camera,recenter
            )

    faults={
        kind:fault_case(kind)
        for kind in FAULTS
    }

    admission=admission_case()

    # Recovery means a completely new, clean estimator
    # and delivery buffer, never reuse of a faulted one.
    new_session=fresh_success(
        "clean",True,False,(1,2,3,4)
    )

    need(
        len(healthy)==6
        and len(faults)==6,
        "RUN_COUNT"
    )

    need(
        all(x["session_quarantined"]
            for x in faults.values()),
        "QUARANTINE_COUNT"
    )

    non_atomic=sum(
        bool(
            item["fault_receipt"][
                "queue_changed_before_fault"
            ] or item["fault_receipt"][
                "estimator_changed_before_fault"
            ]
        )
        for item in faults.values()
    )

    need(
        non_atomic>=4,
        "NON_ATOMIC_FAILURE_NOT_OBSERVED"
    )

    return {
        "schema":SCHEMA,
        "status":"PASS_SYNTHETIC_FAIL_STOP_SOFTWARE_ONLY",
        "healthy_cases":healthy,
        "healthy_solver_executions":6,
        "healthy_nonlinear_windows":24,
        "healthy_schur_marginalizations":18,
        "healthy_prior_recenterings":9,
        "fault_cases":faults,
        "fault_injection_count":6,
        "faulted_sessions_quarantined":6,
        "faults_with_internal_state_change":
            non_atomic,
        "admission":admission,
        "fresh_session_recovery":new_session,
        "fresh_session_recovery_verified":True,
        "existing_r108_transactional_rollback_proven":False,
        "new_transactional_rollback_implemented":False,
        "faulted_session_resume_authorized":False,
        "hardware_fault_recovery_verified":False,
        "real_time_deadlines_verified":False,
        "transport_authentication_verified":False,
        "r95_gaussian_prior_imported":False,
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
        f.write(canonical(report).decode())

    print("R110_FAIL_STOP_FAULT_AUDIT=PASS")
    print("R110_HEALTHY_SOLVER_RUNS=6")
    print("R110_INJECTED_FAILURES=6")
    print("R110_FAULTED_SESSIONS_QUARANTINED=6")
    print(
        "R110_FAULTS_WITH_STATE_CHANGE="+
        str(report["faults_with_internal_state_change"])
    )
    print("R110_PRE_ADMISSION_REJECTIONS=8")
    print("R110_FRESH_SESSION_RECOVERY=PASS")
    print("R110_TRANSACTIONAL_ROLLBACK=NOT_PROVEN")
    print("R110_PHYSICAL_FAILURE_RECOVERY=NOT_TESTED")
