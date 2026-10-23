"""R114: conservative, failure-charged synthetic replay budgets.

A work unit denotes one potential R108 candidate-buffer
packet submission.

Every admitted operation reserves its full work units
BEFORE candidate execution. Failures do not refund
these reservations.

This is NOT a wall-clock, RAM, energy or FLOP bound.
"""

import json
from unittest.mock import patch

import r104_shared_graph as graph
import r107_incremental as r107
import r108_delivery as delivery
import r111_transaction as transaction
import r113_bounded as bounded
import s6_joint_fusion as s6

SCHEMA="TRUST_ROBOT_R114_SYNTHETIC_ATTEMPT_BUDGET_V1"

CASES=(
    ("clean_joint","clean",True),
    ("lidar_dropout_joint","lidar_dropout",True),
    ("clean_camera_off","clean",False),
)

ORDERS={
    "ordered":(1,2,3,4),
    "bounded_reorder":(3,2,1,4),
}

FAULTS=(
    "imu_prediction",
    "nonlinear_optimization",
    "schur_marginalization",
    "prior_recentering",
    "pre_publication",
    "finalization",
)

class AttemptError(ValueError):
    pass

class InjectedFault(RuntimeError):
    pass

def need(flag,reason):
    if not flag:
        raise AttemptError(reason)

def canonical(obj):
    return (
        json.dumps(
            obj,
            sort_keys=True,
            indent=2,
            allow_nan=False
        )+"\n"
    ).encode("utf-8")

class AttemptSession:
    """Single-threaded attempt-reserving wrapper around R113.

    The inner R113 committed-work budget remains active.
    This wrapper additionally charges unsuccessful
    candidate attempts.

    Ownership is local Python object identity only.
    Private-object access is not isolated.
    """

    def __init__(
        self,g,owner,*,
        recenter=False,
        max_attempt_operation_units=4,
        max_attempt_total_units=14
    ):
        need(
            type(owner) is object,
            "OWNER_TYPE"
        )

        need(
            type(recenter) is bool,
            "RECENTER_TYPE"
        )

        need(
            type(max_attempt_operation_units) is int
            and 1<=max_attempt_operation_units<=4,
            "ATTEMPT_OPERATION_LIMIT"
        )

        need(
            type(max_attempt_total_units) is int
            and 1<=max_attempt_total_units<=24,
            "ATTEMPT_TOTAL_LIMIT"
        )

        self._owner=owner

        self._inner,self._inner_owner=bounded.open_session(
            g,recenter=recenter
        )

        self._attempt_operation_limit=(
            max_attempt_operation_units
        )

        self._attempt_total_limit=(
            max_attempt_total_units
        )

        self._attempt_units=0
        self._attempt_ledger=[]

    @property
    def phase(self):
        return self._inner.phase

    @property
    def version(self):
        return self._inner.version

    @property
    def attempted_work_units(self):
        return self._attempt_units

    @property
    def committed_work_units(self):
        return self._inner._total_units

    def committed_digest(self):
        return self._inner.committed_digest()

    def summary(self):
        return {
            "phase":self.phase,
            "version":self.version,
            "committed_digest":
                self.committed_digest(),
            "committed_work_units":
                self.committed_work_units,
            "attempted_work_units":
                self._attempt_units,
            "attempt_ledger":[
                dict(entry)
                for entry in self._attempt_ledger
            ],
            "remaining_attempt_units":
                self._attempt_total_limit-
                self._attempt_units,
        }

    def _authorize(self,owner,expected_version):
        need(
            owner is self._owner,
            "OWNER_MISMATCH"
        )

        need(
            self.phase=="ACTIVE",
            "SESSION_NOT_ACTIVE"
        )

        need(
            type(expected_version) is int
            and expected_version==self.version,
            "STALE_VERSION"
        )

    def _reserve(self,operation,node,units):
        need(
            type(units) is int
            and 1<=units<=self._attempt_operation_limit,
            "ATTEMPT_OPERATION_BUDGET"
        )

        need(
            self._attempt_units+units<=
                self._attempt_total_limit,
            "ATTEMPT_TOTAL_BUDGET"
        )

        self._attempt_units+=units

        entry={
            "operation":operation,
            "node":node,
            "reserved_work_units":units,
            "outcome":"RESERVED",
        }

        self._attempt_ledger.append(entry)
        return entry

    def _run_reserved(self,entry,action):
        old_digest=self.committed_digest()
        old_version=self.version
        old_committed_units=self.committed_work_units

        try:
            response=action()
        except Exception as exc:
            entry["outcome"]="ABORTED"

            need(
                self.committed_digest()==old_digest
                and self.version==old_version
                and self.committed_work_units==
                    old_committed_units,
                "FAILED_ATTEMPT_MUTATED_COMMITTED_STATE"
            )

            raise AttemptError(
                "CANDIDATE_ABORTED"
            ) from exc

        entry["outcome"]="COMMITTED"

        need(
            self.version==old_version+1
            and self.committed_work_units==
                old_committed_units+
                entry["reserved_work_units"],
            "COMMIT_WORK_ACCOUNTING"
        )

        return response

    def submit(self,owner,packet,*,expected_version):
        self._authorize(owner,expected_version)

        # R111 admission checks run before reservation,
        # ensuring rejected packets consume no units.
        try:
            self._inner._inner._admission(packet)
        except transaction.TransactionError as exc:
            raise AttemptError(
                "ADMISSION_REJECTED"
            ) from exc

        units=len(self._inner._inner._history)+1

        entry=self._reserve(
            "submit",
            packet.node,
            units
        )

        return self._run_reserved(
            entry,
            lambda:self._inner.submit(
                self._inner_owner,
                packet,
                expected_version=expected_version
            )
        )

    def finish(self,owner,*,expected_version):
        self._authorize(owner,expected_version)

        b=self._inner._inner._committed

        need(
            b.estimator.next_node==5
            and not b.pending
            and b.received=={1,2,3,4},
            "INCOMPLETE_SESSION"
        )

        units=len(self._inner._inner._history)

        entry=self._reserve(
            "finish",
            None,
            units
        )

        return self._run_reserved(
            entry,
            lambda:self._inner.finish(
                self._inner_owner,
                expected_version=expected_version
            )
        )

    def cancel(self,owner,*,expected_version):
        self._authorize(owner,expected_version)

        before=self.committed_digest()
        units=self._attempt_units

        receipt=self._inner.cancel(
            self._inner_owner,
            expected_version=expected_version
        )

        need(
            self.committed_digest()==before
            and self._attempt_units==units
            and self.phase=="CANCELLED",
            "CANCELLATION_CHANGED_COMMITTED_STATE"
        )

        return receipt

def open_session(
    g,*,
    recenter=False,
    max_attempt_operation_units=4,
    max_attempt_total_units=14
):
    owner=object()

    return AttemptSession(
        g,
        owner,
        recenter=recenter,
        max_attempt_operation_units=
            max_attempt_operation_units,
        max_attempt_total_units=
            max_attempt_total_units,
    ),owner

def healthy_case(condition,camera,recenter,order):
    g=graph.build(condition,camera,13)

    session,owner=open_session(
        g,recenter=recenter
    )

    for node in order:
        session.submit(
            owner,
            delivery.make_packet(g,node),
            expected_version=session.version
        )

    result,ack=session.finish(
        owner,
        expected_version=session.version
    )

    need(
        session.phase=="COMPLETED"
        and session.version==5
        and ack["acknowledged"] is True,
        "HEALTHY_COMPLETION"
    )

    need(
        session.attempted_work_units==14
        and session.committed_work_units==14,
        "HEALTHY_WORK_LEDGER"
    )

    need(
        [
            x["reserved_work_units"]
            for x in session._attempt_ledger
        ]==[1,2,3,4,4],
        "HEALTHY_OPERATION_LEDGER"
    )

    need(
        all(
            x["outcome"]=="COMMITTED"
            for x in session._attempt_ledger
        ),
        "UNEXPECTED_HEALTHY_ABORT"
    )

    reference,audit=s6.estimate_joint(
        g["fixture"],
        g["camera_packets"]
    )

    error=delivery.state_error(
        result,reference
    )

    need(
        error<(2e-5 if recenter else 1e-8),
        "S6_EQUIVALENCE"
    )

    need(
        result["consumed_pose_ids"]==
            audit["consumed_pose_ids"]
        and result["remaining_pose_ids"]==
            audit["remaining_pose_ids"]
        and result["admitted_sample_indices"]==
            list(range(8))
        and result["future_factor_usage"] is False
        and result["factor_reuse"] is False,
        "FACTOR_HISTORY"
    )

    need(
        len(result["windows"])==4
        and len(result["eliminations"])==3
        and len(result["transfer_events"])==
            (3 if recenter else 0),
        "WINDOW_COUNTS"
    )

    return {
        "arrival_order":list(order),
        "recentered":recenter,
        "attempted_work_units":14,
        "committed_work_units":14,
        "operation_ledger":[1,2,3,4,4],
        "acknowledged_operations":5,
        "nonlinear_windows":4,
        "marginalizations":3,
        "prior_transfers":3 if recenter else 0,
        "max_abs_error_vs_s6":error,
        "factor_history_validated":True,
    }

def fault_case(kind):
    need(kind in FAULTS,"UNKNOWN_FAULT")

    g=graph.build("clean",True,13)

    recenter=(kind=="prior_recentering")

    session,owner=open_session(
        g,
        recenter=recenter,
        max_attempt_total_units=24
    )

    target=1

    if kind in (
        "schur_marginalization",
        "prior_recentering",
    ):
        session.submit(
            owner,
            delivery.make_packet(g,1),
            expected_version=session.version
        )
        target=2

    if kind=="finalization":
        for node in (1,2,3,4):
            session.submit(
                owner,
                delivery.make_packet(g,node),
                expected_version=session.version
            )

    before_digest=session.committed_digest()
    before_version=session.version
    before_committed=session.committed_work_units
    before_attempted=session.attempted_work_units

    if kind=="imu_prediction":
        context=patch.object(
            r107.s6,
            "predict_imu",
            side_effect=InjectedFault("PREDICTION")
        )

    elif kind=="nonlinear_optimization":
        context=patch.object(
            r107,
            "least_squares",
            side_effect=InjectedFault("OPTIMIZER")
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
        def prepublication_fault(current,operation):
            raise InjectedFault("PRE_PUBLICATION")

        session._inner._publication_hook=(
            prepublication_fault
        )
        context=patch.object(
            session._inner,
            "_publication_hook",
            side_effect=prepublication_fault
        )

    else:
        original=delivery.DeliveryBuffer.finish

        def finalization_fault(buffer):
            original(buffer)
            raise InjectedFault("FINALIZATION")

        context=patch.object(
            delivery.DeliveryBuffer,
            "finish",
            new=finalization_fault
        )

    original_submit=delivery.DeliveryBuffer.submit
    counter=[0]

    def counted_submit(buffer,packet):
        counter[0]+=1
        return original_submit(buffer,packet)

    caught=None

    with patch.object(
        delivery.DeliveryBuffer,
        "submit",
        new=counted_submit
    ):
        with context:
            try:
                if kind=="finalization":
                    session.finish(
                        owner,
                        expected_version=session.version
                    )
                else:
                    session.submit(
                        owner,
                        delivery.make_packet(g,target),
                        expected_version=session.version
                    )
            except AttemptError as exc:
                caught=exc

    if kind=="pre_publication":
        session._inner._publication_hook=None

    need(
        caught is not None
        and str(caught)=="CANDIDATE_ABORTED",
        "FAULT_NOT_ABORTED"
    )

    reserved=session.attempted_work_units-before_attempted

    need(
        reserved==(
            4 if kind=="finalization"
            else 2 if target==2
            else 1
        ),
        "FAILURE_RESERVATION_INCORRECT"
    )

    need(
        0<counter[0]<=reserved,
        "ACTUAL_FAILED_REPLAY_EXCEEDED_RESERVATION"
    )

    need(
        session.committed_digest()==before_digest
        and session.version==before_version
        and session.committed_work_units==before_committed,
        "FAILURE_CHANGED_COMMITTED_ESTIMATOR"
    )

    need(
        session._attempt_ledger[-1]["outcome"]==
            "ABORTED"
        and session.phase=="ACTIVE",
        "FAILED_ATTEMPT_ACCOUNTING"
    )

    # The failed candidate is never reused.
    # A new candidate is constructed on retry.
    if kind=="finalization":
        result,ack=session.finish(
            owner,
            expected_version=session.version
        )
    else:
        session.submit(
            owner,
            delivery.make_packet(g,target),
            expected_version=session.version
        )

        for node in range(target+1,5):
            session.submit(
                owner,
                delivery.make_packet(g,node),
                expected_version=session.version
            )

        result,ack=session.finish(
            owner,
            expected_version=session.version
        )

    need(
        session.phase=="COMPLETED"
        and session.version==5
        and len(result["windows"])==4
        and ack["acknowledged"] is True,
        "FAILED_ATTEMPT_RECOVERY"
    )

    need(
        session.committed_work_units==14
        and session.attempted_work_units==14+reserved,
        "FAILED_ATTEMPT_WAS_REFUNDED"
    )

    return {
        "fault":kind,
        "reserved_failed_units":reserved,
        "observed_failed_candidate_submissions":
            counter[0],
        "failed_units_retained_after_retry":True,
        "committed_state_unchanged_on_failure":True,
        "failed_attempt_acknowledged":False,
        "successful_retry":True,
        "final_attempted_work_units":
            session.attempted_work_units,
        "final_committed_work_units":
            session.committed_work_units,
    }

def repeated_failure_exhaustion():
    """Repeated failed solver calls exhaust the attempt budget."""

    g=graph.build("clean",True,13)

    session,owner=open_session(
        g,max_attempt_total_units=3
    )

    failures=0

    with patch.object(
        r107,
        "least_squares",
        side_effect=InjectedFault("REPEATED_SOLVER_FAILURE")
    ):
        for _ in range(3):
            try:
                session.submit(
                    owner,
                    delivery.make_packet(g,1),
                    expected_version=0
                )
            except AttemptError as exc:
                need(
                    str(exc)=="CANDIDATE_ABORTED",
                    "REPEATED_FAILURE_NOT_ABORTED"
                )
                failures+=1
            else:
                raise AttemptError(
                    "FAILED_CANDIDATE_WAS_ACCEPTED"
                )

    need(
        failures==3
        and session.attempted_work_units==3
        and session.committed_work_units==0
        and session.version==0,
        "REPEATED_FAILURE_ACCOUNTING"
    )

    before=session.summary()

    try:
        session.submit(
            owner,
            delivery.make_packet(g,1),
            expected_version=0
        )
    except AttemptError as exc:
        need(
            str(exc)=="ATTEMPT_TOTAL_BUDGET",
            "EXHAUSTION_DENIAL"
        )
    else:
        raise AttemptError(
            "EXHAUSTED_BUDGET_ACCEPTED_NEW_ATTEMPT"
        )

    need(
        session.summary()==before,
        "EXHAUSTED_BUDGET_CHANGED_STATE"
    )

    session.cancel(
        owner,expected_version=0
    )

    need(
        session.phase=="CANCELLED",
        "EXHAUSTED_SESSION_NOT_CANCELLED"
    )

    return {
        "failed_attempts":3,
        "failed_work_units_charged":3,
        "committed_work_units":0,
        "fourth_attempt_rejected_before_execution":True,
        "exhaustion_rejection_unchanged":True,
        "cancelled_after_exhaustion":True,
    }

def cancellation_during_candidate():
    """Cancellation must not refund work already reserved."""

    g=graph.build("clean",True,13)

    session,owner=open_session(g)

    original_digest=session.committed_digest()

    def cancel_before_publication(current,operation):
        need(
            operation=="submit",
            "CANCELLATION_HOOK_STAGE"
        )

        session.cancel(
            owner,
            expected_version=session.version
        )

    session._inner._publication_hook=(
        cancel_before_publication
    )

    caught=None

    try:
        session.submit(
            owner,
            delivery.make_packet(g,1),
            expected_version=0
        )
    except AttemptError as exc:
        caught=exc

    session._inner._publication_hook=None

    need(
        caught is not None
        and str(caught)=="CANDIDATE_ABORTED",
        "CANCELLATION_NOT_ENFORCED"
    )

    need(
        session.phase=="CANCELLED"
        and session.version==0
        and session.committed_work_units==0
        and session.attempted_work_units==1
        and session.committed_digest()==original_digest,
        "CANCELLED_ATTEMPT_NOT_CHARGED"
    )

    before=session.summary()

    for action in (
        lambda:session.submit(
            owner,
            delivery.make_packet(g,1),
            expected_version=0
        ),
        lambda:session.finish(
            owner,expected_version=0
        ),
        lambda:session.cancel(
            owner,expected_version=0
        ),
    ):
        try:
            action()
        except AttemptError as exc:
            need(
                str(exc)=="SESSION_NOT_ACTIVE",
                "CANCELLED_SESSION_OPERATION_DENIAL"
            )
        else:
            raise AttemptError(
                "CANCELLED_SESSION_REUSED"
            )

    need(
        session.summary()==before,
        "CANCELLED_TERMINAL_STATE_CHANGED"
    )

    return {
        "work_reserved_before_cancellation":1,
        "work_refunded":False,
        "committed_work_units":0,
        "committed_state_unchanged":True,
        "candidate_published":False,
        "session_terminal":True,
        "post_cancel_operations_rejected":3,
    }

def invalid_admissions():
    """No reservation for unauthorized or stale calls."""

    g=graph.build("clean",True,13)
    session,owner=open_session(g)

    packet=delivery.make_packet(g,1)

    invalid=(
        (
            object(),packet,0,
            "OWNER_MISMATCH"
        ),
        (
            owner,packet,1,
            "STALE_VERSION"
        ),
        (
            owner,delivery.make_packet(g,4),0,
            "ADMISSION_REJECTED"
        ),
    )

    rejected=0

    for who,p,v,expected in invalid:
        before=session.summary()

        try:
            session.submit(
                who,p,expected_version=v
            )
        except AttemptError as exc:
            need(
                str(exc)==expected,
                "INVALID_ADMISSION_REASON"
            )
            rejected+=1
        else:
            raise AttemptError(
                "INVALID_ADMISSION_ACCEPTED"
            )

        need(
            session.summary()==before,
            "ADMISSION_CHARGED_REPLAY_WORK"
        )

    session.submit(
        owner,packet,expected_version=0
    )

    before=session.summary()

    try:
        session.submit(
            owner,packet,expected_version=1
        )
    except AttemptError as exc:
        need(
            str(exc)=="ADMISSION_REJECTED",
            "DUPLICATE_ADMISSION"
        )
        rejected+=1
    else:
        raise AttemptError(
            "DUPLICATE_PACKET_ACCEPTED"
        )

    need(
        session.summary()==before,
        "DUPLICATE_CHARGED_ATTEMPT"
    )

    return {
        "invalid_operations_rejected":rejected,
        "work_charged_for_rejected_admission":0,
        "committed_state_unchanged":True,
    }

def actual_dispatch_witness():
    g=graph.build("clean",True,13)

    session,owner=open_session(g)

    original=delivery.DeliveryBuffer.submit
    count=[0]

    def counted(buffer,packet):
        count[0]+=1
        return original(buffer,packet)

    with patch.object(
        delivery.DeliveryBuffer,
        "submit",
        new=counted
    ):
        for node in (1,2,3,4):
            session.submit(
                owner,
                delivery.make_packet(g,node),
                expected_version=session.version
            )

        session.finish(
            owner,
            expected_version=session.version
        )

    need(
        count[0]==14
        and session.attempted_work_units==14
        and session.committed_work_units==14,
        "ACTUAL_DISPATCH_COUNT"
    )

    return {
        "observed_candidate_submit_calls":count[0],
        "reserved_attempt_units":14,
        "committed_work_units":14,
        "accounting_exact":True,
    }

def execute():
    healthy={}

    for name,condition,camera in CASES:
        for order_name,order in ORDERS.items():
            for recenter in (False,True):
                key=(
                    name+"_"+order_name+
                    (
                        "_recentered"
                        if recenter else "_ordinary"
                    )
                )

                healthy[key]=healthy_case(
                    condition,camera,recenter,order
                )

    faults={
        name:fault_case(name)
        for name in FAULTS
    }

    exhaustion=repeated_failure_exhaustion()
    cancellation=cancellation_during_candidate()
    admission=invalid_admissions()
    dispatch=actual_dispatch_witness()

    need(
        len(healthy)==12
        and len(faults)==6,
        "CASE_COUNTS"
    )

    need(
        all(
            c["successful_retry"]
            and c["failed_units_retained_after_retry"]
            for c in faults.values()
        ),
        "FAILURE_CHARGE_INVARIANT"
    )

    return {
        "schema":SCHEMA,
        "status":"PASS_SYNTHETIC_ATTEMPT_BUDGET_ONLY",

        "healthy_cases":healthy,
        "healthy_sessions":12,
        "healthy_committed_operations":60,
        "healthy_attempted_work_units":168,
        "healthy_committed_work_units":168,

        "fault_cases":faults,
        "injected_failure_stages":6,
        "failed_candidates_charged":6,
        "successful_retries":6,

        "repeated_failure_exhaustion":exhaustion,
        "prepublication_cancellation":cancellation,
        "invalid_admissions":admission,
        "actual_dispatch_witness":dispatch,

        "attempt_reservation_before_candidate":True,
        "failed_attempt_reservations_not_refunded":True,
        "committed_state_isolated_from_candidate_failure":True,

        "wall_clock_latency_bound_verified":False,
        "physical_memory_bound_verified":False,
        "floating_point_work_bound_verified":False,
        "concurrent_atomicity_verified":False,
        "durable_attempt_ledger_verified":False,
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
        sys.argv[1],"x",encoding="utf-8"
    ) as f:
        f.write(canonical(report).decode("utf-8"))

    print("R114_FAILURE_CHARGED_ATTEMPT_BUDGET=PASS")
    print("R114_HEALTHY_SESSIONS=12")
    print("R114_HEALTHY_WORK_UNITS=168")
    print("R114_INJECTED_FAILURE_STAGES=6")
    print("R114_FAILED_ATTEMPTS_CHARGED=6")
    print("R114_SAFE_RETRIES=6")
    print("R114_REPEATED_FAILURE_EXHAUSTION=PASS")
    print("R114_PREPUBLICATION_CANCELLATION=PASS")
    print("R114_UNAUTHORIZED_ADMISSION_CHARGE=ZERO")
    print("R114_HARDWARE_RESOURCE_GUARANTEES=NOT_PROVEN")
