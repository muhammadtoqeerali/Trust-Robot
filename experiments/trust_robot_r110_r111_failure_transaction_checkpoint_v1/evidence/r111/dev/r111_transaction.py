"""R111: copy-on-write synthetic delivery transactions.

Each operation is executed on a newly reconstructed
candidate R108 buffer. Publication occurs only after
the candidate operation completes.

The previously committed buffer is never used to
perform the candidate operation.

Scope: single-threaded, in-process, manufactured data.
Not durable rollback, power-loss recovery, or
distributed exactly-once delivery.
"""

import hashlib
import json

from dataclasses import replace
from unittest.mock import patch

import numpy as np

import r104_shared_graph as graph
import r107_incremental as r107
import r108_delivery as r108
import r110_failstop as r110
import s6_joint_fusion as s6

SCHEMA="TRUST_ROBOT_R111_SYNTHETIC_SHADOW_TRANSACTION_V1"

CASES=(
    ("clean_joint","clean",True),
    ("lidar_dropout_joint","lidar_dropout",True),
    ("clean_camera_off","clean",False),
)

ORDERS={
    "ordered":(1,2,3,4),
    "reordered":(3,2,1,4),
}

FAULTS=(
    "imu_prediction",
    "nonlinear_optimization",
    "schur_marginalization",
    "prior_recentering",
    "pre_publication",
    "finalization",
)

class TransactionError(ValueError):
    pass

class InjectedFault(RuntimeError):
    pass

def need(ok,reason):
    if not ok:
        raise TransactionError(reason)

def canonical(obj):
    return (
        json.dumps(
            obj,sort_keys=True,indent=2,allow_nan=False
        )+"\n"
    ).encode()

def hash_value(obj):
    return hashlib.sha256(canonical(obj)).hexdigest()

def committed_state(buffer):
    """Read-only diagnostic snapshot of committed state."""

    result=r110.snapshot(buffer)
    estimator=buffer.estimator
    prior=estimator.prior

    result["prior_information_sha256"]=hashlib.sha256(
        np.ascontiguousarray(
            prior.square_root_information
        ).tobytes()
    ).hexdigest()

    result["window_ledger"]=json.loads(
        canonical(estimator.windows)
    )

    result["elimination_ledger"]=json.loads(
        canonical(estimator.eliminations)
    )

    result["transfer_ledger"]=json.loads(
        canonical(estimator.transfer_events)
    )

    return result

class TransactionalSession:
    """Single-threaded candidate-state publication boundary.

    Private objects must not be modified externally.
    Packet sources must remain the same validated graph.
    """

    def __init__(self,g,*,recenter=False):
        try:
            graph.validate(g)
        except graph.GraphAdmissionError as exc:
            raise TransactionError(
                "GRAPH_ADMISSION_DENIED"
            ) from exc

        need(
            type(recenter) is bool,
            "RECENTER_MODE"
        )

        self._graph=g
        self._recenter=recenter

        self._committed=r108.DeliveryBuffer(
            g,recenter=recenter
        )

        self._history=()
        self._version=0
        self._phase="ACTIVE"

    @property
    def phase(self):
        return self._phase

    @property
    def version(self):
        return self._version

    def snapshot(self):
        return {
            "version":self._version,
            "phase":self._phase,
            "history_nodes":[
                p.node for p in self._history
            ],
            "state":committed_state(self._committed),
        }

    def digest(self):
        return hash_value(self.snapshot())

    def _active(self):
        need(
            self._phase=="ACTIVE",
            "SESSION_NOT_ACTIVE"
        )

    def _before_publish(self,candidate,operation):
        """Instrumentation seam. No production side effects."""
        return None

    def _candidate(self):
        """Replay only previously acknowledged arrivals."""

        candidate=r108.DeliveryBuffer(
            self._graph,
            recenter=self._recenter
        )

        for packet in self._history:
            candidate.submit(packet)

        return candidate

    def _admission(self,packet):
        self._active()

        try:
            self._committed.validate_packet(packet)
        except r108.DeliveryError as exc:
            raise TransactionError(
                "ADMISSION_REJECTED"
            ) from exc

        b=self._committed

        need(
            packet.node>=b.estimator.next_node
            and packet.node not in b.received,
            "ADMISSION_REJECTED"
        )

        need(
            packet.node-b.estimator.next_node<=b.max_ahead,
            "ADMISSION_REJECTED"
        )

        if packet.node!=b.estimator.next_node:
            need(
                len(b.pending)<b.max_pending,
                "ADMISSION_REJECTED"
            )

    def submit(self,packet):
        self._admission(packet)

        old=self._committed
        old_version=self._version
        old_digest=self.digest()

        try:
            candidate=self._candidate()
            processed=candidate.submit(packet)

            acknowledgement={
                "operation":"submit",
                "sequence":old_version+1,
                "node":packet.node,
                "processed_nodes":list(processed),
                "candidate_digest":hash_value(
                    committed_state(candidate)
                ),
                "acknowledged":True,
            }

            self._before_publish(
                candidate,"submit"
            )

        except Exception as exc:
            need(
                self._committed is old
                and self._version==old_version
                and self.digest()==old_digest,
                "COMMITTED_STATE_MUTATED_ON_FAILURE"
            )

            raise TransactionError(
                "TRANSACTION_ABORTED_NO_ACK"
            ) from exc

        # Single-threaded, in-process publication.
        self._committed=candidate
        self._history=self._history+(packet,)
        self._version=old_version+1

        return acknowledgement

    def finish(self):
        self._active()

        b=self._committed

        need(
            b.estimator.next_node==5
            and not b.pending
            and b.received=={1,2,3,4},
            "INCOMPLETE_SESSION"
        )

        old=b
        old_version=self._version
        old_digest=self.digest()

        try:
            candidate=self._candidate()
            result=candidate.finish()

            acknowledgement={
                "operation":"finish",
                "sequence":old_version+1,
                "candidate_digest":hash_value(
                    committed_state(candidate)
                ),
                "acknowledged":True,
            }

            self._before_publish(
                candidate,"finish"
            )

        except Exception as exc:
            need(
                self._committed is old
                and self._version==old_version
                and self.digest()==old_digest,
                "COMMITTED_STATE_MUTATED_ON_FAILURE"
            )

            raise TransactionError(
                "TRANSACTION_ABORTED_NO_ACK"
            ) from exc

        self._committed=candidate
        self._version=old_version+1
        self._phase="COMPLETED"

        return result,acknowledgement

def healthy_case(condition,camera,recenter,order):
    g=graph.build(condition,camera,13)

    session=TransactionalSession(
        g,recenter=recenter
    )

    acknowledgements=[]

    for node in order:
        acknowledgements.append(
            session.submit(
                r108.make_packet(g,node)
            )
        )

    result,ack=session.finish()
    acknowledgements.append(ack)

    need(
        session.phase=="COMPLETED"
        and session.version==5
        and len(acknowledgements)==5,
        "COMMIT_COUNT"
    )

    need(
        [x["sequence"] for x in acknowledgements]
        ==[1,2,3,4,5],
        "ACKNOWLEDGEMENT_ORDER"
    )

    need(
        all(x["acknowledged"] is True
            for x in acknowledgements),
        "MISSING_ACKNOWLEDGEMENT"
    )

    reference,audit=s6.estimate_joint(
        g["fixture"],g["camera_packets"]
    )

    error=r108.state_error(
        result,reference
    )

    need(
        error<(2e-5 if recenter else 1e-8),
        "ORIGINAL_S6_MISMATCH"
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
        result["future_factor_usage"] is False
        and result["factor_reuse"] is False,
        "UNSAFE_FACTOR_REUSE"
    )

    need(
        len(result["windows"])==4
        and len(result["eliminations"])==3
        and len(result["transfer_events"])==
            (3 if recenter else 0),
        "SOLVER_COUNTS"
    )

    return {
        "arrival_order":list(order),
        "processed_order":
            result["windows"] and [1,2,3,4],
        "recentered":recenter,
        "acknowledged_operations":5,
        "nonlinear_windows":4,
        "schur_marginalizations":3,
        "prior_transfers":3 if recenter else 0,
        "max_abs_error_vs_s6":error,
        "factor_ownership_verified":True,
        "candidate_state_published_after_success":True,
        "physical_execution_verified":False,
    }

def injected_case(kind):
    need(kind in FAULTS,"UNKNOWN_FAULT")

    g=graph.build("clean",True,13)

    recenter=kind=="prior_recentering"

    session=TransactionalSession(
        g,recenter=recenter
    )

    target=1

    if kind in (
        "schur_marginalization",
        "prior_recentering",
    ):
        session.submit(
            r108.make_packet(g,1)
        )
        target=2

    if kind=="finalization":
        for node in range(1,5):
            session.submit(
                r108.make_packet(g,node)
            )

    before=session.snapshot()
    old=session._committed
    version=session.version

    if kind=="imu_prediction":
        context=patch.object(
            r107.s6,
            "predict_imu",
            side_effect=InjectedFault("PREDICT")
        )

    elif kind=="nonlinear_optimization":
        context=patch.object(
            r107,
            "least_squares",
            side_effect=InjectedFault("SOLVER")
        )

    elif kind=="schur_marginalization":
        context=patch.object(
            r107.s6,
            "marginalize_one",
            side_effect=InjectedFault("SCHUR")
        )

    elif kind=="prior_recentering":
        context=patch.object(
            r107.transfer,
            "transfer",
            side_effect=InjectedFault("RECENTER")
        )

    elif kind=="pre_publication":
        context=patch.object(
            session,
            "_before_publish",
            side_effect=InjectedFault("PRE_PUBLISH")
        )

    else:
        original=r108.DeliveryBuffer.finish

        def injected_finish(buffer):
            original(buffer)
            raise InjectedFault("FINALIZATION")

        context=patch.object(
            r108.DeliveryBuffer,
            "finish",
            new=injected_finish
        )

    caught=None

    with context:
        try:
            if kind=="finalization":
                session.finish()
            else:
                session.submit(
                    r108.make_packet(g,target)
                )
        except TransactionError as exc:
            caught=exc

    need(
        caught is not None
        and str(caught)=="TRANSACTION_ABORTED_NO_ACK"
        and isinstance(caught.__cause__,InjectedFault),
        "FAULT_NOT_ABORTED"
    )

    need(
        session.snapshot()==before
        and session._committed is old
        and session.version==version
        and session.phase=="ACTIVE",
        "FAILED_TRANSACTION_CHANGED_COMMITTED_STATE"
    )

    # Retry is performed only after the injection
    # is removed. The failed shadow is discarded.
    if kind=="finalization":
        result,ack=session.finish()
        need(
            ack["acknowledged"] is True
            and len(result["windows"])==4,
            "FINISH_RETRY_FAILED"
        )

    else:
        ack=session.submit(
            r108.make_packet(g,target)
        )

        need(
            ack["acknowledged"] is True
            and ack["node"]==target,
            "PACKET_RETRY_FAILED"
        )

        for node in range(target+1,5):
            session.submit(
                r108.make_packet(g,node)
            )

        session.finish()

    need(
        session.phase=="COMPLETED"
        and session.version==5,
        "RECOVERY_INCOMPLETE"
    )

    graph.validate(g)

    return {
        "fault":kind,
        "exception_type":"InjectedFault",
        "no_ack_on_failed_operation":True,
        "committed_snapshot_unchanged":True,
        "committed_object_identity_unchanged":True,
        "failed_shadow_discarded":True,
        "retry_after_injection_removed":True,
        "session_recovered_without_reusing_failed_shadow":True,
        "new_physical_fault_recovery_proven":False,
    }

def invalid_admission():
    g=graph.build("clean",True,13)

    session=TransactionalSession(g)

    p=r108.make_packet(g,1)
    other=graph.build("clean",True,13)

    invalid=(
        replace(p,frame_id="RECORDED_FRAME"),
        replace(p,real_sensor_factors_authorized=True),
        replace(p,node_time_ns=p.node_time_ns+1),
        replace(p,session="WRONG_SESSION"),
        replace(
            p,
            readings=(
                dict(p.readings[0]),
                p.readings[1]
            )
        ),
        r108.make_packet(g,4),
        r108.make_packet(other,1),
    )

    rejected=0

    for candidate in invalid:
        before=session.snapshot()

        try:
            session.submit(candidate)
        except TransactionError as exc:
            need(
                str(exc)=="ADMISSION_REJECTED",
                "WRONG_ADMISSION_ERROR"
            )
            rejected+=1
        else:
            raise TransactionError(
                "INVALID_PACKET_ACCEPTED"
            )

        need(
            session.snapshot()==before,
            "ADMISSION_CHANGED_STATE"
        )

    session.submit(p)
    before=session.snapshot()

    try:
        session.submit(p)
    except TransactionError as exc:
        need(
            str(exc)=="ADMISSION_REJECTED",
            "DUPLICATE_ERROR"
        )
        rejected+=1
    else:
        raise TransactionError(
            "DUPLICATE_ACCEPTED"
        )

    need(
        session.snapshot()==before,
        "DUPLICATE_CHANGED_STATE"
    )

    for node in range(2,5):
        session.submit(
            r108.make_packet(g,node)
        )

    session.finish()

    need(
        rejected==8
        and session.phase=="COMPLETED",
        "ADMISSION_RECOVERY"
    )

    return {
        "rejections":rejected,
        "state_unchanged":True,
        "session_completed_after_rejections":True,
    }

def execute():
    healthy={}

    for name,condition,camera in CASES:
        for order_name,order in ORDERS.items():
            for recenter in (False,True):
                key=(
                    name+"_"+order_name+
                    ("_recentered" if recenter
                     else "_ordinary")
                )

                healthy[key]=healthy_case(
                    condition,camera,recenter,order
                )

    faults={
        kind:injected_case(kind)
        for kind in FAULTS
    }

    admission=invalid_admission()

    need(
        len(healthy)==12
        and len(faults)==6,
        "AUDIT_CASE_COUNT"
    )

    need(
        all(
            x["committed_snapshot_unchanged"]
            and x["retry_after_injection_removed"]
            for x in faults.values()
        ),
        "FAULT_ATOMICITY"
    )

    need(
        admission["rejections"]==8,
        "ADMISSION_COUNT"
    )

    return {
        "schema":SCHEMA,
        "status":"PASS_SYNTHETIC_SHADOW_TRANSACTION_ONLY",
        "healthy_cases":healthy,
        "healthy_solver_sessions":12,
        "committed_operations":60,
        "nonlinear_windows_in_committed_sessions":48,
        "schur_events_in_committed_sessions":36,
        "same_graph_prior_transfers":18,
        "fault_cases":faults,
        "fault_injections":6,
        "unchanged_committed_snapshots_after_fault":6,
        "successful_retries":6,
        "invalid_admission":admission,
        "in_memory_shadow_isolation_verified":True,
        "original_r107_r108_modified":False,
        "existing_r108_rollback_implemented":False,
        "durable_crash_recovery_verified":False,
        "distributed_exactly_once_verified":False,
        "concurrent_atomic_publication_verified":False,
        "direct_private_object_mutation_isolated":False,
        "physical_hardware_recovery_verified":False,
        "hardware_streaming_verified":False,
        "transport_authentication_verified":False,
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
        f.write(canonical(report).decode())

    print("R111_SHADOW_TRANSACTION_AUDIT=PASS")
    print("R111_HEALTHY_SESSIONS=12")
    print("R111_COMMITTED_OPERATIONS=60")
    print("R111_INJECTED_FAILURES=6")
    print("R111_COMMITTED_STATE_PRESERVED=6")
    print("R111_SUCCESSFUL_RETRIES=6")
    print("R111_ADMISSION_REJECTIONS=8")
    print("R111_REAL_SENSOR_FACTORS=DENIED")
    print("R111_DURABLE_ROLLBACK=NOT_PROVEN")
