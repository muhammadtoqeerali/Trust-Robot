"""R113: deterministic replay-budget and cancellation audit.

A constrained wrapper around the original R111 shadow
transaction session.

Resource units count candidate packet submissions:
- submit cost = acknowledged history length + 1
- finish cost = acknowledged history length

This bounds replay dispatches, NOT elapsed time,
RAM, FLOPs, energy, or real-time performance.

Local object-identity ownership is not authentication.
"""

import json
from unittest.mock import patch

import r104_shared_graph as graph
import r108_delivery as delivery
import r111_transaction as transaction
import s6_joint_fusion as s6

SCHEMA="TRUST_ROBOT_R113_SYNTHETIC_BOUNDED_REPLAY_V1"

CASES=(
    ("clean_joint","clean",True),
    ("lidar_dropout_joint","lidar_dropout",True),
    ("clean_camera_off","clean",False),
)

ORDERS={
    "ordered":(1,2,3,4),
    "bounded_reorder":(3,2,1,4),
}

class BudgetError(ValueError):
    pass

class CancelledBeforePublication(RuntimeError):
    pass

def need(ok,reason):
    if not ok:
        raise BudgetError(reason)

def canonical(obj):
    return (
        json.dumps(
            obj,sort_keys=True,indent=2,allow_nan=False
        )+"\n"
    ).encode("utf-8")

class BoundedSession:
    """Single-process resource and cancellation boundary.

    Mutation requires the same local owner object
    supplied at creation. Direct access to private
    Python fields is NOT protected.
    """

    def __init__(
        self,g,owner,*,
        recenter=False,
        max_operation_units=4,
        max_total_units=14
    ):
        need(
            type(owner) is object,
            "OWNER_TYPE"
        )

        need(
            type(max_operation_units) is int
            and 1<=max_operation_units<=4,
            "OPERATION_LIMIT"
        )

        need(
            type(max_total_units) is int
            and 1<=max_total_units<=14,
            "TOTAL_LIMIT"
        )

        self._owner=owner

        self._inner=transaction.TransactionalSession(
            g,recenter=recenter
        )

        self._phase="ACTIVE"

        self._operation_limit=max_operation_units
        self._total_limit=max_total_units

        self._total_units=0
        self._max_observed_operation_units=0
        self._work_ledger=[]

        self._publication_hook=None

        # R111 executes this hook immediately before
        # publishing a completed candidate.
        self._inner._before_publish=self._publication_gate

    @property
    def phase(self):
        return self._phase

    @property
    def version(self):
        return self._inner.version

    def _authorize(self,owner):
        need(
            owner is self._owner,
            "OWNER_MISMATCH"
        )

    def _active(self):
        need(
            self._phase=="ACTIVE",
            "SESSION_NOT_ACTIVE"
        )

    def _expected_version(self,version):
        need(
            type(version) is int
            and version==self.version,
            "STALE_VERSION"
        )

    def committed_digest(self):
        return self._inner.digest()

    def summary(self):
        """Diagnostic data only; not an auth receipt."""
        return {
            "phase":self._phase,
            "version":self.version,
            "committed_digest":
                self.committed_digest(),
            "total_work_units":self._total_units,
            "max_operation_units_seen":
                self._max_observed_operation_units,
            "work_ledger":list(self._work_ledger),
            "history_length":len(self._inner._history),
        }

    def _budget(self,units):
        need(
            type(units) is int
            and 1<=units<=self._operation_limit,
            "OPERATION_WORK_BUDGET"
        )

        need(
            self._total_units+units<=self._total_limit,
            "TOTAL_WORK_BUDGET"
        )

    def _publication_gate(self,candidate,operation):
        """Runs while candidate is still uncommitted."""

        if self._publication_hook is not None:
            self._publication_hook(self,operation)

        if self._phase!="ACTIVE":
            raise CancelledBeforePublication(
                "CANCELLED_BEFORE_PUBLICATION"
            )

    def submit(self,owner,packet,*,expected_version):
        self._authorize(owner)
        self._active()
        self._expected_version(expected_version)

        # Enforce R111 admission before any candidate work.
        self._inner._admission(packet)

        units=len(self._inner._history)+1
        self._budget(units)

        before=self.committed_digest()
        previous_version=self.version
        previous_units=self._total_units

        # The R111 method discards failed candidates.
        acknowledgement=self._inner.submit(packet)

        need(
            self._phase=="ACTIVE"
            and self.version==previous_version+1
            and acknowledgement["acknowledged"] is True,
            "UNEXPECTED_PUBLICATION_STATE"
        )

        self._total_units=previous_units+units

        self._max_observed_operation_units=max(
            self._max_observed_operation_units,
            units
        )

        self._work_ledger.append(units)

        need(
            self.committed_digest()!=before,
            "COMMIT_DIGEST_NOT_ADVANCED"
        )

        return {
            **acknowledgement,
            "work_units":units,
            "total_committed_work_units":self._total_units,
        }

    def finish(self,owner,*,expected_version):
        self._authorize(owner)
        self._active()
        self._expected_version(expected_version)

        b=self._inner._committed

        need(
            b.estimator.next_node==5
            and not b.pending
            and b.received=={1,2,3,4},
            "INCOMPLETE_SESSION"
        )

        units=len(self._inner._history)
        self._budget(units)

        before=self.committed_digest()
        previous_version=self.version
        previous_units=self._total_units

        result,acknowledgement=self._inner.finish()

        need(
            self._phase=="ACTIVE"
            and self.version==previous_version+1
            and acknowledgement["acknowledged"] is True,
            "UNEXPECTED_FINISH_PUBLICATION"
        )

        self._total_units=previous_units+units

        self._max_observed_operation_units=max(
            self._max_observed_operation_units,
            units
        )

        self._work_ledger.append(units)

        self._phase="COMPLETED"

        need(
            self.committed_digest()!=before,
            "FINAL_COMMIT_DIGEST_NOT_ADVANCED"
        )

        return result,{
            **acknowledgement,
            "work_units":units,
            "total_committed_work_units":self._total_units,
        }

    def cancel(self,owner,*,expected_version):
        self._authorize(owner)
        self._active()
        self._expected_version(expected_version)

        committed_before=self.committed_digest()
        version_before=self.version
        units_before=self._total_units

        self._phase="CANCELLED"

        need(
            self.committed_digest()==committed_before
            and self.version==version_before
            and self._total_units==units_before,
            "CANCELLATION_MUTATED_COMMITTED_STATE"
        )

        return {
            "cancelled":True,
            "version":version_before,
            "committed_digest":committed_before,
            "committed_work_units":units_before,
            "new_candidate_published":False,
            "physical_cancellation_verified":False,
        }

def open_session(
    g,*,recenter=False,
    max_operation_units=4,
    max_total_units=14
):
    """Return a session plus a local identity lease.

    This lease is NOT an authenticated security token.
    """
    owner=object()

    session=BoundedSession(
        g,
        owner,
        recenter=recenter,
        max_operation_units=max_operation_units,
        max_total_units=max_total_units,
    )

    return session,owner

def run_case(condition,camera,recenter,order):
    g=graph.build(condition,camera,13)

    session,owner=open_session(
        g,recenter=recenter
    )

    acknowledgements=[]

    for node in order:
        acknowledgements.append(
            session.submit(
                owner,
                delivery.make_packet(g,node),
                expected_version=session.version
            )
        )

    result,final_ack=session.finish(
        owner,
        expected_version=session.version
    )

    acknowledgements.append(final_ack)

    need(
        session.phase=="COMPLETED"
        and session.version==5,
        "HEALTHY_SESSION_COMPLETION"
    )

    need(
        session._total_units==14
        and session._work_ledger==[1,2,3,4,4]
        and session._max_observed_operation_units==4,
        "WORK_BUDGET_ACCOUNTING"
    )

    reference,audit=s6.estimate_joint(
        g["fixture"],
        g["camera_packets"]
    )

    error=delivery.state_error(result,reference)

    need(
        error<(2e-5 if recenter else 1e-8),
        "ORIGINAL_S6_EQUIVALENCE"
    )

    need(
        result["consumed_pose_ids"]==
            audit["consumed_pose_ids"]
        and result["remaining_pose_ids"]==
            audit["remaining_pose_ids"],
        "POSE_FACTOR_OWNERSHIP"
    )

    need(
        result["admitted_sample_indices"]==
            list(range(8))
        and result["future_factor_usage"] is False
        and result["factor_reuse"] is False,
        "IMU_AND_FUTURE_FACTOR_BOUNDARY"
    )

    need(
        len(result["windows"])==4
        and len(result["eliminations"])==3
        and len(result["transfer_events"])==
            (3 if recenter else 0),
        "SOLVER_EVENT_COUNTS"
    )

    need(
        [a["sequence"] for a in acknowledgements]
        ==[1,2,3,4,5],
        "ACK_SEQUENCE"
    )

    return {
        "arrival_order":list(order),
        "recentered":recenter,
        "acknowledged_operations":5,
        "replay_work_units":14,
        "operation_work_ledger":[1,2,3,4,4],
        "max_operation_work_units":4,
        "nonlinear_windows":4,
        "marginalizations":3,
        "prior_transfers":3 if recenter else 0,
        "max_abs_error_vs_s6":error,
        "factor_ownership_verified":True,
        "synthetic_only":True,
    }

def actual_replay_witness():
    """Count actual R108 candidate submission calls."""

    g=graph.build("clean",True,13)
    session,owner=open_session(g)

    original=delivery.DeliveryBuffer.submit
    counter=[0]

    def counted(buffer,packet):
        counter[0]+=1
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
        counter[0]==14,
        "ACTUAL_REPLAY_DISPATCH_MISMATCH"
    )

    need(
        session._total_units==counter[0],
        "RESOURCE_LEDGER_MISMATCH"
    )

    return {
        "actual_candidate_submit_calls":counter[0],
        "recorded_work_units":session._total_units,
        "accounting_exact":True,
    }

def budget_rejections():
    g=graph.build("clean",True,13)

    # Total budget is insufficient for node three.
    session,owner=open_session(
        g,max_total_units=3
    )

    for node in (1,2):
        session.submit(
            owner,
            delivery.make_packet(g,node),
            expected_version=session.version
        )

    before=session.summary()
    rejected=0

    try:
        session.submit(
            owner,
            delivery.make_packet(g,3),
            expected_version=session.version
        )
    except BudgetError as exc:
        need(
            str(exc)=="TOTAL_WORK_BUDGET",
            "TOTAL_BUDGET_REJECTION"
        )
        rejected+=1
    else:
        raise BudgetError("TOTAL_BUDGET_BYPASSED")

    need(
        session.summary()==before,
        "TOTAL_BUDGET_MUTATED_STATE"
    )

    # Per-operation budget blocks node four.
    other,lease=open_session(
        g,max_operation_units=3
    )

    for node in (1,2,3):
        other.submit(
            lease,
            delivery.make_packet(g,node),
            expected_version=other.version
        )

    prior=other.summary()

    try:
        other.submit(
            lease,
            delivery.make_packet(g,4),
            expected_version=other.version
        )
    except BudgetError as exc:
        need(
            str(exc)=="OPERATION_WORK_BUDGET",
            "OPERATION_BUDGET_REJECTION"
        )
        rejected+=1
    else:
        raise BudgetError("OPERATION_BUDGET_BYPASSED")

    need(
        other.summary()==prior,
        "OPERATION_BUDGET_MUTATED_STATE"
    )

    # A budget permitting four submits but not finish.
    final,final_owner=open_session(
        g,max_total_units=13
    )

    for node in (1,2,3,4):
        final.submit(
            final_owner,
            delivery.make_packet(g,node),
            expected_version=final.version
        )

    prior=final.summary()

    try:
        final.finish(
            final_owner,
            expected_version=final.version
        )
    except BudgetError as exc:
        need(
            str(exc)=="TOTAL_WORK_BUDGET",
            "FINISH_BUDGET_REJECTION"
        )
        rejected+=1
    else:
        raise BudgetError("FINISH_BUDGET_BYPASSED")

    need(
        final.summary()==prior,
        "FINISH_BUDGET_MUTATED_STATE"
    )

    return {
        "budget_rejections":rejected,
        "state_unchanged_for_all_rejections":True,
        "wall_clock_deadline_verified":False,
        "physical_memory_limit_verified":False,
    }

def ownership_and_cancellation():
    g=graph.build("clean",True,13)

    session,owner=open_session(g)
    intruder=object()

    before=session.summary()
    rejected=0

    for action in (
        lambda:session.submit(
            intruder,
            delivery.make_packet(g,1),
            expected_version=0
        ),
        lambda:session.cancel(
            intruder,expected_version=0
        ),
        lambda:session.finish(
            intruder,expected_version=0
        ),
        lambda:session.submit(
            owner,
            delivery.make_packet(g,1),
            expected_version=1
        ),
    ):
        try:
            action()
        except BudgetError as exc:
            need(
                str(exc) in (
                    "OWNER_MISMATCH",
                    "STALE_VERSION",
                ),
                "WRONG_OWNERSHIP_REJECTION"
            )
            rejected+=1
        else:
            raise BudgetError(
                "UNAUTHORIZED_OPERATION_ACCEPTED"
            )

        need(
            session.summary()==before,
            "OWNERSHIP_REJECTION_MUTATED_STATE"
        )

    for node in (1,2):
        session.submit(
            owner,
            delivery.make_packet(g,node),
            expected_version=session.version
        )

    before_digest=session.committed_digest()
    before_version=session.version
    before_units=session._total_units

    receipt=session.cancel(
        owner,
        expected_version=session.version
    )

    need(
        receipt["cancelled"] is True
        and session.phase=="CANCELLED"
        and session.committed_digest()==before_digest
        and session.version==before_version
        and session._total_units==before_units,
        "CANCELLATION_ATOMICITY"
    )

    for action in (
        lambda:session.submit(
            owner,
            delivery.make_packet(g,3),
            expected_version=session.version
        ),
        lambda:session.finish(
            owner,expected_version=session.version
        ),
        lambda:session.cancel(
            owner,expected_version=session.version
        ),
    ):
        try:
            action()
        except BudgetError as exc:
            need(
                str(exc)=="SESSION_NOT_ACTIVE",
                "CANCELLED_OPERATION_DENIAL"
            )
            rejected+=1
        else:
            raise BudgetError(
                "CANCELLED_SESSION_REUSED"
            )

    need(
        session.committed_digest()==before_digest
        and session.version==before_version,
        "CANCELLED_SESSION_CHANGED"
    )

    return {
        "rejected_unauthorized_or_terminal_operations":
            rejected,
        "cancelled_after_acknowledged_packets":2,
        "committed_state_preserved":True,
        "cancelled_session_reuse_denied":True,
    }

def cancellation_before_publication():
    """Cancel at R111's pre-publication seam."""

    g=graph.build("clean",True,13)
    session,owner=open_session(g)

    before=session.committed_digest()
    before_version=session.version
    before_units=session._total_units

    def cancel_at_ready(current,operation):
        need(
            operation=="submit",
            "INJECTION_OPERATION"
        )

        current.cancel(
            owner,
            expected_version=current.version
        )

    session._publication_hook=cancel_at_ready

    caught=None

    try:
        session.submit(
            owner,
            delivery.make_packet(g,1),
            expected_version=0
        )
    except transaction.TransactionError as exc:
        caught=exc

    session._publication_hook=None

    need(
        caught is not None
        and str(caught)=="TRANSACTION_ABORTED_NO_ACK"
        and isinstance(
            caught.__cause__,
            CancelledBeforePublication
        ),
        "CANCELLATION_DID_NOT_ABORT_CANDIDATE"
    )

    need(
        session.phase=="CANCELLED"
        and session.version==before_version
        and session._total_units==before_units
        and session.committed_digest()==before,
        "PREPUBLICATION_COMMITTED_STATE_MUTATED"
    )

    need(
        len(session._inner._history)==0,
        "CANCELLED_CANDIDATE_PUBLISHED"
    )

    try:
        session.submit(
            owner,
            delivery.make_packet(g,1),
            expected_version=0
        )
    except BudgetError as exc:
        need(
            str(exc)=="SESSION_NOT_ACTIVE",
            "CANCELLED_RETRY_DENIAL"
        )
    else:
        raise BudgetError(
            "CANCELLED_SESSION_ADMITTED_RETRY"
        )

    return {
        "candidate_executed_before_cancellation":True,
        "candidate_published":False,
        "committed_state_unchanged":True,
        "acknowledgement_issued":False,
        "session_terminal":True,
    }

def injected_solver_failure():
    """A failed candidate must consume no committed budget."""

    import r107_incremental as r107

    g=graph.build("clean",True,13)
    session,owner=open_session(g)

    before=session.summary()

    with patch.object(
        r107,
        "least_squares",
        side_effect=RuntimeError("R113_INJECTED_SOLVER")
    ):
        caught=None

        try:
            session.submit(
                owner,
                delivery.make_packet(g,1),
                expected_version=0
            )
        except transaction.TransactionError as exc:
            caught=exc

    need(
        caught is not None
        and str(caught)=="TRANSACTION_ABORTED_NO_ACK"
        and session.summary()==before,
        "FAILED_CANDIDATE_MUTATED_COMMITTED_STATE"
    )

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
        session.phase=="COMPLETED"
        and session._total_units==14,
        "SOLVER_RETRY_FAILURE"
    )

    return {
        "failed_candidate_committed_work_units":0,
        "original_committed_state_preserved":True,
        "retry_after_fault_removed":True,
        "successful_session_work_units":14,
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

                healthy[key]=run_case(
                    condition,camera,recenter,order
                )

    witness=actual_replay_witness()
    budgets=budget_rejections()
    ownership=ownership_and_cancellation()
    prepublication=cancellation_before_publication()
    failure=injected_solver_failure()

    need(
        len(healthy)==12,
        "HEALTHY_CASE_COUNT"
    )

    need(
        all(
            row["replay_work_units"]==14
            for row in healthy.values()
        ),
        "HEALTHY_WORK_ACCOUNTING"
    )

    return {
        "schema":SCHEMA,
        "status":"PASS_SYNTHETIC_RESOURCE_AND_CANCELLATION_ONLY",
        "healthy_cases":healthy,
        "healthy_sessions":12,
        "healthy_committed_operations":60,
        "healthy_total_replay_work_units":168,
        "maximum_work_units_per_session":14,
        "maximum_work_units_per_operation":4,
        "actual_replay_witness":witness,
        "budget_rejections":budgets,
        "ownership_and_cancellation":ownership,
        "prepublication_cancellation":prepublication,
        "injected_solver_failure":failure,
        "bounded_candidate_dispatches_verified":True,
        "local_owner_identity_enforced":True,
        "cancellation_prevents_publication":True,
        "wall_clock_latency_bound_verified":False,
        "physical_memory_bound_verified":False,
        "concurrent_cancellation_safety_verified":False,
        "durable_cancellation_verified":False,
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
        f.write(canonical(report).decode())

    print("R113_BOUNDED_SHADOW_REPLAY=PASS")
    print("R113_HEALTHY_SESSIONS=12")
    print("R113_COMMITTED_OPERATIONS=60")
    print("R113_TOTAL_REPLAY_WORK_UNITS=168")
    print("R113_WORK_UNITS_PER_SESSION=14")
    print("R113_ACTUAL_REPLAY_WITNESS=14")
    print("R113_RESOURCE_BUDGET_REJECTIONS=3")
    print("R113_CANCELLATION_BEFORE_PUBLICATION=PASS")
    print("R113_INJECTED_SOLVER_RETRY=PASS")
    print("R113_PHYSICAL_TIMING_OR_MEMORY_BOUNDS=NOT_PROVEN")
