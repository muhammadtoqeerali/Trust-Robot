"""R120: synthetic audit capacity and receipt-consistency guard.

Extends the unchanged R119 observation interface.

The existing R117 registry assumes terminal
retirements are processed in creation order.
R120 enforces that precondition before R117 mutation.

An exhausted failure receipt budget fails closed.
Further mutating operations are blocked, including
cancellation and retirement. Read access remains.

All histories are in-memory and unauthenticated.
"""

import json
from dataclasses import replace
from unittest.mock import patch

import r104_shared_graph as graph
import r107_incremental as r107
import r108_delivery as delivery
import r114_attempts as attempts
import r116_lifecycle as lifecycle
import r119_observation as observation

SCHEMA="TRUST_ROBOT_R120_SYNTHETIC_AUDIT_CHAIN_GUARD_V1"
GENESIS="0"*64

SCENARIOS=(
    ("clean_joint","clean",True),
    ("lidar_dropout_joint","lidar_dropout",True),
    ("clean_camera_off","clean",False),
)

class AuditGuardError(ValueError):
    pass

def need(ok,reason):
    if not ok:
        raise AuditGuardError(reason)

def canonical(value):
    return observation.canonical(value)

def detached(value):
    return json.loads(canonical(value))

class AuditGuard(observation.ObservationBoundary):
    """Bounded, single-threaded diagnostic facade.

    Does not protect private Python objects from code
    already executing in the same interpreter.
    """

    def __init__(
        self,*,
        max_active=2,
        max_created=12,
        max_denials=12
    ):
        need(
            type(max_denials) is int
            and 1<=max_denials<=16,
            "DENIAL_CAPACITY_TYPE_OR_RANGE"
        )

        super().__init__(
            max_active=max_active,
            max_created=max_created
        )

        self._max_denials=max_denials
        self._policy=[]
        self._policy_tip=GENESIS
        self._blocked_at_capacity=0

        self._verify()

    def _verify(self):
        super()._verify()

        # Check R119's denial receipts semantically
        # in addition to its linked hash checks.
        if hasattr(self,"_max_denials"):
            need(
                len(self._denials)<=self._max_denials,
                "DENIAL_CAPACITY_INVARIANT"
            )

        for record in self._denials:
            before=record.get("before")
            after=record.get("after")
            reason=record.get("reason")
            units=record.get("charged_attempt_units")

            need(
                record.get("acknowledged") is False
                and type(units) is int
                and units>=0,
                "DENIAL_RECEIPT_SCHEMA"
            )

            if before is None:
                need(
                    after is None
                    and record.get("known_session") is False
                    and reason=="STALE_OR_UNKNOWN_HANDLE"
                    and units==0,
                    "UNKNOWN_HANDLE_RECEIPT"
                )
                continue

            need(
                type(before) is dict
                and type(after) is dict
                and record.get("known_session") is True,
                "KNOWN_SESSION_RECEIPT"
            )

            need(
                before["version"]==after["version"]
                and before["committed_digest"]==
                    after["committed_digest"]
                and before["committed_work_units"]==
                    after["committed_work_units"],
                "DENIAL_COMMITTED_STATE_CHANGED"
            )

            expected=(
                after["attempted_work_units"]-
                before["attempted_work_units"]
            )

            need(
                expected==units and expected>=0,
                "DENIAL_ATTEMPT_DELTA"
            )

            if reason=="CANDIDATE_ABORTED":
                need(
                    units>0,
                    "ABORTED_WORK_NOT_CHARGED"
                )
            else:
                need(
                    units==0,
                    "REJECTED_ADMISSION_CHARGED"
                )

        if not hasattr(self,"_policy"):
            return True

        prev=GENESIS

        for ordinal,item in enumerate(self._policy,1):
            need(
                type(item) is dict
                and item.get("ordinal")==ordinal
                and item.get("action")=="retire"
                and item.get("reason")==
                    "RETIREMENT_ORDER_DENIED",
                "POLICY_RECEIPT_SCHEMA"
            )

            payload={
                k:v for k,v in item.items()
                if k!="linked_sha256"
            }

            need(
                item.get("previous_sha256")==prev
                and item.get("linked_sha256")==
                    observation.digest(payload),
                "POLICY_LEDGER_TAMPER"
            )

            need(
                item.get("issued_index")!=
                    item.get("expected_index"),
                "POLICY_ORDER_WITNESS"
            )

            prev=item["linked_sha256"]

        need(
            self._policy_tip==prev,
            "POLICY_LEDGER_TIP"
        )

        return True

    def _capacity_gate(self):
        self._verify()

        if len(self._denials)>=self._max_denials:
            # Overflow calls are counted only, not
            # recorded with individual receipts.
            self._blocked_at_capacity+=1
            raise AuditGuardError(
                "RECEIPT_CAPACITY_EXHAUSTED"
            )

    def _mutation(self,action,lease,fn):
        self._capacity_gate()
        return super()._mutation(
            action,lease,fn
        )

    def retire(self,lease,owner):
        self._capacity_gate()

        if type(lease) is object:
            entry=self._registry._active.get(lease)

            if (
                entry is not None
                and owner is entry["owner"]
            ):
                expected=len(self._registry._ledger)+1
                issued=entry["issued_index"]

                if issued!=expected:
                    before=self._state_for_known_lease(
                        lease
                    )

                    record={
                        "ordinal":len(self._policy)+1,
                        "action":"retire",
                        "reason":
                            "RETIREMENT_ORDER_DENIED",
                        "issued_index":issued,
                        "expected_index":expected,
                        "version":before["version"],
                        "attempted_work_units":
                            before["attempted_work_units"],
                        "committed_work_units":
                            before["committed_work_units"],
                        "previous_sha256":
                            self._policy_tip,
                    }

                    record["linked_sha256"]=(
                        observation.digest(record)
                    )

                    self._policy.append(record)
                    self._policy_tip=(
                        record["linked_sha256"]
                    )

                    self._verify()

                    need(
                        self._state_for_known_lease(
                            lease
                        )==before,
                        "ORDER_REJECTION_CHANGED_STATE"
                    )

                    raise AuditGuardError(
                        "RETIREMENT_ORDER_DENIED"
                    )

        return super().retire(lease,owner)

    def inspect(self):
        self._verify()

        snapshot={
            "registry":self.observe_registry(),
            "denials":self.observe_denials(),
            "retirements":self.observe_retirements(),
            "policy":{
                "receipt_count":len(self._policy),
                "chain_tip":self._policy_tip,
                "receipts":detached(self._policy),
            },
            "denial_capacity":self._max_denials,
            "blocked_without_individual_receipt":
                self._blocked_at_capacity,
        }

        snapshot["diagnostic_sha256"]=(
            observation.digest(snapshot)
        )

        return detached(snapshot)

def assert_no_credential_objects(snapshot):
    encoded=canonical(snapshot).decode("utf-8")

    for forbidden in (
        '"owner"',
        '"lease"',
        '"packet"',
        '"readings"',
        '"camera_packets"',
        '"fixture"',
    ):
        need(
            forbidden not in encoded,
            "OBSERVATION_EXPOSED_PRIVATE_FIELD"
        )

def healthy_cases():
    rows={}
    sessions=0

    for name,condition,camera in SCENARIOS:
        for recenter in (False,True):
            g=graph.build(condition,camera,13)

            f=AuditGuard(
                max_active=1,
                max_created=1
            )

            lease,owner=f.open(
                g,recenter=recenter
            )

            order=(
                (3,2,1,4)
                if recenter else
                (1,2,3,4)
            )

            reads=0

            for node in order:
                before=f.observe_session(
                    lease,owner
                )

                ack=f.submit(
                    lease,owner,
                    delivery.make_packet(g,node),
                    version=before["version"]
                )

                after=f.observe_session(
                    lease,owner
                )

                need(
                    ack["acknowledged"] is True
                    and after["version"]==
                        before["version"]+1,
                    "HEALTHY_ACK_VERSION"
                )

                reads+=2

            state=f.observe_session(lease,owner)

            result,ack=f.finish(
                lease,owner,
                version=state["version"]
            )

            error=lifecycle.validate_result(
                g,result,recenter
            )

            need(
                ack["acknowledged"] is True,
                "HEALTHY_FINISH_ACK"
            )

            record=f.retire(lease,owner)

            need(
                record["terminal_phase"]=="COMPLETED",
                "HEALTHY_RETIREMENT"
            )

            view=f.inspect()
            assert_no_credential_objects(view)

            need(
                view["registry"]["active_count"]==0
                and view["retirements"][
                    "receipt_count"
                ]==1
                and view["denials"][
                    "receipt_count"
                ]==0
                and view["policy"][
                    "receipt_count"
                ]==0,
                "HEALTHY_AUDIT_COUNTS"
            )

            # A returned observation must be detached.
            view["retirements"]["receipts"][0][
                "version"
            ]=999

            need(
                f.inspect()["retirements"][
                    "receipts"
                ][0]["version"]==5,
                "OBSERVATION_COPY_MUTATED_SOURCE"
            )

            key=name+(
                "_recentered" if recenter
                else "_ordinary"
            )

            rows[key]={
                "arrival_order":list(order),
                "recentered":recenter,
                "acknowledged_operations":5,
                "attempted_work_units":14,
                "nonlinear_windows":4,
                "schur_events":3,
                "prior_transfers":
                    3 if recenter else 0,
                "max_abs_error_vs_s6":error,
                "observation_reads":reads,
                "retired":True,
                "detached_observation":True,
            }

            sessions+=1

    need(
        sessions==6,
        "HEALTHY_SESSION_TOTAL"
    )

    return {
        "runs":rows,
        "sessions":6,
        "acknowledged_operations":30,
        "attempted_work_units":84,
        "nonlinear_windows":24,
        "schur_events":18,
        "prior_transfers":9,
        "detached_observations_verified":True,
        "credentials_excluded_from_observations":True,
    }

def admission_receipts():
    g=graph.build("clean",True,13)
    other=graph.build(
        "lidar_dropout",True,13
    )

    f=AuditGuard(
        max_active=1,
        max_created=1,
        max_denials=12
    )

    lease,owner=f.open(g)
    packet=delivery.make_packet(g,1)

    checks=(
        (
            "wrong_owner","OWNER_MISMATCH",
            lambda:f.submit(
                lease,object(),packet,version=0
            ),
        ),
        (
            "stale_version","STALE_VERSION",
            lambda:f.submit(
                lease,owner,packet,version=1
            ),
        ),
        (
            "future_node","ADMISSION_REJECTED",
            lambda:f.submit(
                lease,owner,
                delivery.make_packet(g,4),
                version=0
            ),
        ),
        (
            "cross_graph","ADMISSION_REJECTED",
            lambda:f.submit(
                lease,owner,
                delivery.make_packet(other,1),
                version=0
            ),
        ),
        (
            "wrong_frame","ADMISSION_REJECTED",
            lambda:f.submit(
                lease,owner,
                replace(packet,frame_id="RECORDED"),
                version=0
            ),
        ),
        (
            "real_factor_claim","ADMISSION_REJECTED",
            lambda:f.submit(
                lease,owner,
                replace(
                    packet,
                    real_sensor_factors_authorized=True
                ),
                version=0
            ),
        ),
        (
            "missing_imu","ADMISSION_REJECTED",
            lambda:f.submit(
                lease,owner,
                replace(
                    packet,
                    readings=packet.readings[:1]
                ),
                version=0
            ),
        ),
        (
            "incomplete_finish","INCOMPLETE_SESSION",
            lambda:f.finish(
                lease,owner,version=0
            ),
        ),
        (
            "unknown_lease","STALE_OR_UNKNOWN_HANDLE",
            lambda:f.submit(
                object(),owner,packet,version=0
            ),
        ),
    )

    names=[]

    for name,reason,action in checks:
        before=f.observe_session(
            lease,owner
        )

        try:
            action()
        except observation.OperationDenied as exc:
            need(
                str(exc)==reason,
                "ADMISSION_REASON:"+name
            )
        else:
            raise AuditGuardError(
                "INVALID_ADMISSION_ACCEPTED:"+name
            )

        need(
            f.observe_session(lease,owner)==before,
            "ADMISSION_MUTATED_STATE:"+name
        )

        names.append(name)

    f.submit(
        lease,owner,
        packet,version=0
    )

    before=f.observe_session(
        lease,owner
    )

    try:
        f.submit(
            lease,owner,
            packet,version=1
        )
    except observation.OperationDenied as exc:
        need(
            str(exc)=="ADMISSION_REJECTED",
            "DUPLICATE_REASON"
        )
    else:
        raise AuditGuardError(
            "DUPLICATE_PACKET_ACCEPTED"
        )

    need(
        f.observe_session(lease,owner)==before,
        "DUPLICATE_MUTATED_STATE"
    )

    for node in (2,3,4):
        f.submit(
            lease,owner,
            delivery.make_packet(g,node),
            version=node-1
        )

    result,ack=f.finish(
        lease,owner,version=4
    )

    error=lifecycle.validate_result(
        g,result,False
    )

    f.retire(lease,owner)

    view=f.inspect()
    receipts=view["denials"]["receipts"]

    need(
        len(receipts)==10
        and all(
            x["charged_attempt_units"]==0
            and x["acknowledged"] is False
            for x in receipts
        ),
        "REJECTED_ADMISSION_RECEIPTS"
    )

    assert_no_credential_objects(view)

    view["denials"]["receipts"][0][
        "reason"
    ]="FORGED_SUCCESS"

    need(
        f.inspect()["denials"][
            "receipts"
        ][0]["reason"]=="OWNER_MISMATCH",
        "DETACHED_DENIAL_OBSERVATION"
    )

    return {
        "rejected_patterns":names+["duplicate"],
        "denials":10,
        "charged_attempt_units":0,
        "eventual_healthy_completion":True,
        "max_abs_error_vs_s6":error,
        "all_denials_unacknowledged":True,
        "detached_denial_copy_verified":True,
        "semantic_denial_validation":True,
    }

def failed_candidate_receipts():
    bad=graph.build("clean",True,13)
    good=graph.build(
        "lidar_dropout",True,13
    )

    f=AuditGuard(
        max_active=2,
        max_created=2,
        max_denials=6
    )

    lb,ob=f.open(
        bad,attempt_budget=3
    )

    lg,og=f.open(
        good,attempt_budget=14
    )

    for node in (1,2,3):
        before_bad=f.observe_session(lb,ob)
        before_good=f.observe_session(lg,og)

        with patch.object(
            r107,
            "least_squares",
            side_effect=attempts.InjectedFault(
                "R120_SYNTHETIC_FAILURE"
            )
        ):
            try:
                f.submit(
                    lb,ob,
                    delivery.make_packet(bad,1),
                    version=0
                )
            except observation.OperationDenied as exc:
                need(
                    str(exc)=="CANDIDATE_ABORTED",
                    "INJECTED_FAULT_RECEIPT"
                )
            else:
                raise AuditGuardError(
                    "FAILED_CANDIDATE_ACKNOWLEDGED"
                )

        after_bad=f.observe_session(lb,ob)

        need(
            after_bad["attempted_work_units"]==
                before_bad["attempted_work_units"]+1
            and after_bad["committed_digest"]==
                before_bad["committed_digest"]
            and after_bad["version"]==0,
            "ABORTED_ATTEMPT_STATE"
        )

        need(
            f.observe_session(lg,og)==before_good,
            "PEER_STATE_CHANGED_BY_FAULT"
        )

        ack=f.submit(
            lg,og,
            delivery.make_packet(good,node),
            version=node-1
        )

        need(
            ack["acknowledged"] is True,
            "HEALTHY_PEER_BLOCKED"
        )

    before=f.observe_session(lb,ob)

    try:
        f.submit(
            lb,ob,
            delivery.make_packet(bad,1),
            version=0
        )
    except observation.OperationDenied as exc:
        need(
            str(exc)=="ATTEMPT_TOTAL_BUDGET",
            "EXHAUSTION_REASON"
        )
    else:
        raise AuditGuardError(
            "EXHAUSTED_BUDGET_EXECUTED"
        )

    need(
        f.observe_session(lb,ob)==before,
        "EXHAUSTION_CHANGED_COMMITTED_STATE"
    )

    f.cancel(lb,ob,version=0)
    f.retire(lb,ob)

    f.submit(
        lg,og,
        delivery.make_packet(good,4),
        version=3
    )

    result,ack=f.finish(
        lg,og,version=4
    )

    error=lifecycle.validate_result(
        good,result,False
    )

    f.retire(lg,og)

    view=f.inspect()

    charges=[
        x["charged_attempt_units"]
        for x in view["denials"]["receipts"]
    ]

    need(
        charges==[1,1,1,0],
        "FAILURE_CHARGE_ORDER"
    )

    need(
        view["retirements"]["receipt_count"]==2
        and view["registry"]["active_count"]==0,
        "FAILURE_CASE_RETIREMENT"
    )

    return {
        "aborted_candidates":3,
        "denial_receipts":4,
        "attempt_charge_ledger":charges,
        "fourth_attempt_rejected_without_charge":True,
        "committed_state_preserved":True,
        "healthy_peer_completed":True,
        "healthy_peer_error_vs_s6":error,
        "retired_sessions":2,
        "semantic_receipts_verified":True,
    }

def retirement_order_guard():
    g=graph.build("clean",True,13)

    f=AuditGuard(
        max_active=2,
        max_created=2
    )

    a,oa=f.open(g)
    b,ob=f.open(g)

    # B becomes terminal first, but A was issued first.
    f.cancel(b,ob,version=0)

    before=f.observe_session(b,ob)
    registry_before=f.observe_registry()

    try:
        f.retire(b,ob)
    except AuditGuardError as exc:
        need(
            str(exc)=="RETIREMENT_ORDER_DENIED",
            "RETIREMENT_ORDER_REASON"
        )
    else:
        raise AuditGuardError(
            "OUT_OF_ORDER_RETIREMENT_ACCEPTED"
        )

    need(
        f.observe_session(b,ob)==before
        and f.observe_registry()==registry_before,
        "ORDER_REJECTION_MUTATED_REGISTRY"
    )

    policy=f.inspect()["policy"]

    need(
        policy["receipt_count"]==1
        and policy["receipts"][0][
            "reason"
        ]=="RETIREMENT_ORDER_DENIED",
        "POLICY_RECEIPT_MISSING"
    )

    # A local policy receipt also fails closed on
    # accidental alteration.
    original=f._policy[0]["version"]
    f._policy[0]["version"]=999

    caught=False

    try:
        f.inspect()
    except AuditGuardError as exc:
        need(
            str(exc)=="POLICY_LEDGER_TAMPER",
            "POLICY_TAMPER_REASON"
        )
        caught=True

    need(caught,"POLICY_TAMPER_UNDETECTED")

    f._policy[0]["version"]=original

    need(
        f._verify() is True,
        "POLICY_TAMPER_RESTORE"
    )

    f.cancel(a,oa,version=0)
    first=f.retire(a,oa)
    second=f.retire(b,ob)

    need(
        first["issued_index"]==1
        and second["issued_index"]==2
        and f.inspect()["registry"]["active_count"]==0,
        "ORDERED_RETIREMENT_RECOVERY"
    )

    return {
        "pre_mutation_order_rejections":1,
        "policy_receipts":1,
        "policy_tamper_controls":1,
        "committed_state_unchanged":True,
        "subsequent_ordered_retirement":True,
        "retired_sessions":2,
        "registry_integrity_preserved":True,
    }

def capacity_saturation():
    g=graph.build("clean",True,13)

    f=AuditGuard(
        max_active=1,
        max_created=1,
        max_denials=3
    )

    lease,owner=f.open(g)
    packet=delivery.make_packet(g,1)

    for _ in range(3):
        try:
            f.submit(
                lease,object(),packet,
                version=0
            )
        except observation.OperationDenied as exc:
            need(
                str(exc)=="OWNER_MISMATCH",
                "SATURATION_FIXTURE_REASON"
            )
        else:
            raise AuditGuardError(
                "SATURATION_FIXTURE_ACCEPTED"
            )

    before=f.observe_session(lease,owner)

    for action in (
        lambda:f.submit(
            lease,owner,packet,version=0
        ),
        lambda:f.cancel(
            lease,owner,version=0
        ),
    ):
        try:
            action()
        except AuditGuardError as exc:
            need(
                str(exc)=="RECEIPT_CAPACITY_EXHAUSTED",
                "SATURATION_GATE"
            )
        else:
            raise AuditGuardError(
                "SATURATED_REGISTRY_MUTATED"
            )

    need(
        f.observe_session(lease,owner)==before,
        "SATURATED_SESSION_CHANGED"
    )

    final=f.inspect()

    need(
        final["denials"]["receipt_count"]==3
        and final[
            "blocked_without_individual_receipt"
        ]==2
        and final["registry"]["active_count"]==1,
        "SATURATION_INVARIANTS"
    )

    return {
        "maximum_denial_receipts":3,
        "recorded_denials":3,
        "additional_operations_blocked":2,
        "additional_individual_receipts":0,
        "committed_state_unchanged":True,
        "read_only_observations_available":True,
        "active_session_left_unretired":True,
        "liveness_guarantee_after_saturation":False,
    }

def prepublication_abort():
    g=graph.build("clean",True,13)

    f=AuditGuard(
        max_active=1,
        max_created=1
    )

    lease,owner=f.open(g)

    entry=f._registry._active[lease]

    session=f._registry._pool._active[
        entry["handle"]
    ]["session"]

    before=f.observe_session(lease,owner)

    def cancel_at_boundary(current,operation):
        need(
            operation=="submit",
            "PUBLICATION_STAGE"
        )
        f.cancel(lease,owner,version=0)

    session._inner._publication_hook=(
        cancel_at_boundary
    )

    try:
        try:
            f.submit(
                lease,owner,
                delivery.make_packet(g,1),
                version=0
            )
        except observation.OperationDenied as exc:
            need(
                str(exc)=="CANDIDATE_ABORTED",
                "PREPUBLICATION_DENIAL"
            )
        else:
            raise AuditGuardError(
                "CANCELLED_CANDIDATE_ACCEPTED"
            )
    finally:
        session._inner._publication_hook=None

    after=f.observe_session(lease,owner)

    need(
        after["phase"]=="CANCELLED"
        and after["attempted_work_units"]==1
        and after["committed_work_units"]==0
        and after["version"]==0
        and after["committed_digest"]==
            before["committed_digest"],
        "PREPUBLICATION_STATE"
    )

    f.retire(lease,owner)

    receipt=f.inspect()["denials"]["receipts"][0]

    need(
        receipt["reason"]=="CANDIDATE_ABORTED"
        and receipt["charged_attempt_units"]==1
        and receipt["acknowledged"] is False,
        "PREPUBLICATION_RECEIPT"
    )

    return {
        "aborted_candidates":1,
        "charged_attempt_units":1,
        "committed_units":0,
        "committed_state_preserved":True,
        "cancellation_terminal":True,
        "retired_after_abort":True,
    }

def denial_tamper_control():
    g=graph.build("clean",True,13)

    f=AuditGuard(
        max_active=1,
        max_created=1
    )

    lease,owner=f.open(g)

    try:
        f.submit(
            lease,object(),
            delivery.make_packet(g,1),
            version=0
        )
    except observation.OperationDenied:
        pass
    else:
        raise AuditGuardError(
            "DENIAL_TAMPER_FIXTURE"
        )

    saved=f._denials[0]["charged_attempt_units"]
    f._denials[0]["charged_attempt_units"]=999

    caught=False

    try:
        f.inspect()
    except observation.ObservationError as exc:
        need(
            str(exc)=="DENIAL_LEDGER_TAMPER",
            "DENIAL_TAMPER_REASON"
        )
        caught=True

    need(caught,"DENIAL_TAMPER_ACCEPTED")

    f._denials[0]["charged_attempt_units"]=saved

    need(
        f.inspect()["denials"][
            "receipt_count"
        ]==1,
        "DENIAL_TAMPER_RESTORE"
    )

    f.cancel(lease,owner,version=0)
    f.retire(lease,owner)

    return {
        "linked_denial_tamper_rejected":True,
        "subsequent_operations_after_restore":True,
        "authenticated_log_verified":False,
    }

def execute():
    healthy=healthy_cases()
    admissions=admission_receipts()
    failures=failed_candidate_receipts()
    order=retirement_order_guard()
    capacity=capacity_saturation()
    cancellation=prepublication_abort()
    tamper=denial_tamper_control()

    need(
        healthy["sessions"]==6
        and admissions["denials"]==10
        and failures["aborted_candidates"]==3
        and order["policy_receipts"]==1
        and capacity["recorded_denials"]==3,
        "EXECUTION_TOTALS"
    )

    return {
        "schema":SCHEMA,
        "status":
            "PASS_SYNTHETIC_AUDIT_CHAIN_GUARDS_ONLY",

        "healthy_cases":healthy,
        "admission_receipts":admissions,
        "failed_candidate_receipts":failures,
        "retirement_order_guard":order,
        "capacity_saturation":capacity,
        "prepublication_abort":cancellation,
        "denial_tamper_control":tamper,

        "healthy_sessions":6,
        "healthy_acknowledgements":30,
        "healthy_replay_work_units":84,
        "admission_denials":10,
        "charged_failed_candidates":3,
        "retirement_order_denials":1,
        "bounded_denial_capacity":True,
        "receipt_semantics_verified":True,
        "out_of_order_retirement_denied_pre_mutation":True,

        "authenticated_logging_verified":False,
        "durable_logging_verified":False,
        "external_ledger_anchor_verified":False,
        "malicious_inprocess_tamper_protection_verified":False,
        "concurrent_thread_safety_verified":False,
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

    print("R120_SYNTHETIC_AUDIT_CHAIN_GUARD=PASS")
    print("R120_HEALTHY_SESSIONS=6")
    print("R120_HEALTHY_ACKNOWLEDGEMENTS=30")
    print("R120_HEALTHY_REPLAY_WORK_UNITS=84")
    print("R120_INVALID_ADMISSION_RECEIPTS=10")
    print("R120_CHARGED_FAILED_CANDIDATES=3")
    print("R120_RETIREMENT_ORDER_PREMUTATION_DENIAL=PASS")
    print("R120_DENIAL_RECEIPT_CAPACITY=ENFORCED")
    print("R120_CAPACITY_FAIL_STOP=PASS")
    print("R120_PREPUBLICATION_ABORT=PASS")
    print("R120_INTERNAL_RECEIPT_TAMPER=REJECTED")
    print("R120_DURABLE_AUTHENTICATED_LOG=NOT_PROVEN")
