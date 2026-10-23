"""R124 single-session *modeled* shadow-publish terminal experiment.

Does NOT clone R117/R122 Python objects or provide durable/concurrent safety.
No estimator execution or recorded sensor input.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import json

GENESIS = "0" * 64
STAGES = (
    "candidate_create_pre", "candidate_create_post",
    "mutation_pre", "mutation_post", "receipt_pre", "receipt_post",
    "validation_pre", "validation_post", "publication_pre",
    "publication_post", "ack_pre",
)
PREPUBLICATION_STAGES = STAGES[:9]
POSTPUBLICATION_STAGES = STAGES[9:]
ACTIONS = ("cancel", "retire")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def need(condition, code):
    if not condition:
        raise TerminalModelError(code)


class TerminalModelError(RuntimeError):
    pass


class InjectedFault(RuntimeError):
    def __init__(self, stage):
        self.stage = stage
        super().__init__("R124_INJECTED_FAULT:" + stage)


@dataclass(frozen=True, eq=False)
class PublishedState:
    owner: object
    lease: object
    phase: str
    version: int
    active: bool
    retired: bool
    issued_index: int
    attempted_work_units: int
    committed_work_units: int
    committed_digest: str
    revision: int
    registry_receipts: tuple[str, ...]
    registry_tip: str
    terminal_receipts: tuple[str, ...]
    terminal_tip: str


class ShadowTerminal:
    """One local identity-bound lease, immutable records, one pointer publication.

    State is immutable through the provided API. Private-object mutation and
    concurrent writers are OUTSIDE the proof. No copy.deepcopy is performed.
    """

    def __init__(self):
        self._owner = object()
        self._lease = object()
        self._fixture_digest = digest({
            "fixture": "r124_manufactured_single_session",
            "attempted": 5, "committed": 3, "version": 7,
        })
        self._published = PublishedState(
            owner=self._owner, lease=self._lease, phase="ACTIVE",
            version=7, active=True, retired=False, issued_index=1,
            attempted_work_units=5, committed_work_units=3,
            committed_digest=self._fixture_digest, revision=0,
            registry_receipts=(), registry_tip=GENESIS,
            terminal_receipts=(), terminal_tip=GENESIS,
        )
        self._verify(self._published)

    def local_capabilities(self):
        """Only for in-process synthetic fixture; no real authentication."""
        return self._lease, self._owner

    @staticmethod
    def _link(payload):
        return {**payload, "linked_sha256": digest(payload)}

    @staticmethod
    def _pack(record):
        return canonical(record)  # str prevents mutable receipt aliasing

    @staticmethod
    def _unpack(record):
        value = json.loads(record)
        need(type(value) is dict and canonical(value) == record,
             "NONCANONICAL_RECEIPT")
        return value

    def _registry_payload(self, state):
        return {
            "ordinal": 1, "event": "registry_retire",
            "issued_index": 1, "terminal_phase": "CANCELLED",
            "version": 8, "attempted_work_units": state.attempted_work_units,
            "committed_work_units": state.committed_work_units,
            "committed_digest": state.committed_digest,
            "retired": True, "previous_sha256": GENESIS,
        }

    def _terminal_payload(self, state, event, previous, registry_tip=GENESIS):
        payload = {
            "ordinal": 1 if event == "terminal_cancel" else 2,
            "event": event, "issued_index": 1,
            "terminal_phase": "CANCELLED", "version": 8,
            "attempted_work_units": state.attempted_work_units,
            "committed_work_units": state.committed_work_units,
            "committed_digest": state.committed_digest,
            "acknowledged": False, "previous_sha256": previous,
        }
        if event == "terminal_retire":
            payload["registry_linked_sha256"] = registry_tip
        return payload

    def _verify(self, state):
        need(type(state) is PublishedState, "STATE_TYPE")
        need(state.owner is self._owner and state.lease is self._lease,
             "IDENTITY_BINDING")
        need(state.issued_index == 1 and type(state.version) is int,
             "INDEX_VERSION")
        need(type(state.attempted_work_units) is int
             and state.attempted_work_units == 5
             and type(state.committed_work_units) is int
             and state.committed_work_units == 3
             and state.committed_digest == self._fixture_digest,
             "WORK_PRESERVATION")
        need(type(state.registry_receipts) is tuple
             and type(state.terminal_receipts) is tuple,
             "RECEIPT_CONTAINER")
        expected = {
            "ACTIVE": (0, True, False, 7, 0, 0),
            "CANCELLED": (1, True, False, 8, 0, 1),
            "RETIRED": (2, False, True, 8, 1, 2),
        }
        need(state.phase in expected, "UNKNOWN_PHASE")
        need((state.revision, state.active, state.retired, state.version,
              len(state.registry_receipts), len(state.terminal_receipts))
             == expected[state.phase], "STATE_RECEIPT_INCONSISTENCY")
        if state.retired:
            expected_registry = self._link(self._registry_payload(state))
            need(self._unpack(state.registry_receipts[0]) == expected_registry,
                 "REGISTRY_RECEIPT_MISMATCH")
            need(state.registry_tip == expected_registry["linked_sha256"],
                 "REGISTRY_TIP_MISMATCH")
        else:
            need(state.registry_tip == GENESIS, "REGISTRY_EMPTY_TIP")
        previous = GENESIS
        for index, encoded in enumerate(state.terminal_receipts):
            event = ("terminal_cancel", "terminal_retire")[index]
            expected_record = self._link(self._terminal_payload(
                state, event, previous, state.registry_tip
            ))
            need(self._unpack(encoded) == expected_record,
                 "TERMINAL_RECEIPT_MISMATCH")
            previous = expected_record["linked_sha256"]
        need(state.terminal_tip == previous, "TERMINAL_TIP_MISMATCH")
        return True

    def observe(self):
        s = self._published
        self._verify(s)
        payload = {
            "phase": s.phase, "version": s.version,
            "issued_index": s.issued_index,
            "active_count": int(s.active), "retired_count": int(s.retired),
            "attempted_work_units": s.attempted_work_units,
            "committed_work_units": s.committed_work_units,
            "committed_digest": s.committed_digest,
            "revision": s.revision,
            "denial_capacity_saturated": True,
            "terminal_capacity": 2, "registry_capacity": 1,
            "registry_receipts": [self._unpack(x) for x in s.registry_receipts],
            "registry_tip": s.registry_tip,
            "terminal_receipts": [self._unpack(x) for x in s.terminal_receipts],
            "terminal_tip": s.terminal_tip,
        }
        payload["diagnostic_sha256"] = digest(payload)
        return payload

    def submit(self, *_args, **_kwargs):
        raise TerminalModelError("DENIAL_SATURATED_NO_FACTOR_EXECUTION")

    @staticmethod
    def _fault(selected, at):
        if selected == at:
            raise InjectedFault(at)

    def _authorize(self, action, lease, owner, version):
        self._verify(self._published)
        need(type(lease) is object and lease is self._lease,
             "STALE_OR_UNKNOWN_LEASE")
        need(owner is self._owner, "OWNER_MISMATCH")
        s = self._published
        if action == "cancel":
            need(type(version) is int, "VERSION_TYPE")
            need(version == s.version, "STALE_VERSION")
            need(s.phase == "ACTIVE", "CANCEL_PHASE_DENIED")
        else:
            need(s.phase == "CANCELLED", "RETIRE_PHASE_DENIED")
            need(s.issued_index == len(s.registry_receipts) + 1,
                 "RETIRE_ORDER_DENIED")
        need(len(s.terminal_receipts) < 2, "TERMINAL_CAPACITY")
        return s

    def _mutate(self, candidate, action):
        if action == "cancel":
            return replace(candidate, phase="CANCELLED", version=8,
                           revision=1)
        return replace(candidate, phase="RETIRED", active=False,
                       retired=True, revision=2)

    def _attach_receipts(self, candidate, action):
        if action == "cancel":
            item = self._link(self._terminal_payload(
                candidate, "terminal_cancel", candidate.terminal_tip
            ))
            return replace(
                candidate, terminal_receipts=(self._pack(item),),
                terminal_tip=item["linked_sha256"]
            )
        record = self._link(self._registry_payload(candidate))
        terminal = self._link(self._terminal_payload(
            candidate, "terminal_retire", candidate.terminal_tip,
            record["linked_sha256"]
        ))
        return replace(
            candidate,
            registry_receipts=(self._pack(record),),
            registry_tip=record["linked_sha256"],
            terminal_receipts=candidate.terminal_receipts
                              + (self._pack(terminal),),
            terminal_tip=terminal["linked_sha256"],
        )

    def transact(self, action, lease, owner, *, version=None, inject=None):
        need(action in ACTIONS, "UNKNOWN_ACTION")
        need(inject is None or inject in STAGES, "UNKNOWN_FAULT_STAGE")
        published = self._authorize(action, lease, owner, version)
        # Synchronous model: exclusive caller assumption, NOT a lock.
        self._fault(inject, "candidate_create_pre")
        candidate = replace(published)
        need(candidate is not published and candidate.owner is published.owner
             and candidate.lease is published.lease,
             "CANDIDATE_IDENTITY_NOT_PRESERVED")
        self._fault(inject, "candidate_create_post")
        self._fault(inject, "mutation_pre")
        candidate = self._mutate(candidate, action)
        self._fault(inject, "mutation_post")
        self._fault(inject, "receipt_pre")
        candidate = self._attach_receipts(candidate, action)
        self._fault(inject, "receipt_post")
        self._fault(inject, "validation_pre")
        self._verify(candidate)
        self._fault(inject, "validation_post")
        self._fault(inject, "publication_pre")
        # Sole public-state pointer assignment: in-process linearization point.
        self._published = candidate
        self._fault(inject, "publication_post")
        self._fault(inject, "ack_pre")
        return {"acknowledged": True, "revision": candidate.revision,
                "phase": candidate.phase,
                "terminal_tip": candidate.terminal_tip}

    def cancel(self, lease, owner, *, version, inject=None):
        return self.transact("cancel", lease, owner, version=version,
                             inject=inject)

    def retire(self, lease, owner, *, inject=None):
        return self.transact("retire", lease, owner, inject=inject)


def fixture_for(action):
    need(action in ACTIONS, "UNKNOWN_ACTION")
    system = ShadowTerminal()
    lease, owner = system.local_capabilities()
    if action == "retire":
        system.cancel(lease, owner, version=7)
    return system, lease, owner


def invoke(system, action, lease, owner, inject=None):
    if action == "cancel":
        return system.cancel(lease, owner, version=7, inject=inject)
    return system.retire(lease, owner, inject=inject)


def fault_case(action, stage):
    system, lease, owner = fixture_for(action)
    original_pointer = system._published
    before = system.observe()
    try:
        invoke(system, action, lease, owner, stage)
    except InjectedFault as exc:
        need(exc.stage == stage, "FAULT_STAGE_MISMATCH")
    else:
        raise TerminalModelError("EXPECTED_FAULT_MISSING")
    after = system.observe()
    published = stage in POSTPUBLICATION_STAGES
    need((system._published is original_pointer) == (not published),
         "PUBLICATION_IDENTITY_MISMATCH")
    if not published:
        need(after == before, "PREPUBLICATION_MUTATION")
        ack = invoke(system, action, lease, owner)
        need(ack["acknowledged"] is True, "RETRY_NOT_ACKNOWLEDGED")
        retry = "safe_success"
    else:
        need(after != before and after["revision"] == before["revision"] + 1,
             "POSTPUBLICATION_NOT_VISIBLE")
        try:
            invoke(system, action, lease, owner)
        except TerminalModelError:
            retry = "duplicate_denied"
        else:
            raise TerminalModelError("POSTPUBLICATION_REPLAY_ACCEPTED")
    final = system.observe()
    need(final["attempted_work_units"] == before["attempted_work_units"]
         and final["committed_work_units"] == before["committed_work_units"]
         and final["committed_digest"] == before["committed_digest"],
         "WORK_CHANGED")
    return {
        "action": action, "stage": stage,
        "publication_occurred_before_exception": published,
        "caller_acknowledged": False,
        "observation_unchanged_after_fault": after == before,
        "retry_result": retry,
        "revision_before": before["revision"],
        "revision_after_fault": after["revision"],
        "revision_final": final["revision"],
        "terminal_receipts_after_fault": len(after["terminal_receipts"]),
        "terminal_receipts_final": len(final["terminal_receipts"]),
        "registry_receipts_after_fault": len(after["registry_receipts"]),
        "registry_receipts_final": len(final["registry_receipts"]),
        "final_phase": final["phase"],
    }


def execute():
    cases = [fault_case(action, stage)
             for action in ACTIONS for stage in STAGES]
    normal = {}
    for action in ACTIONS:
        system, lease, owner = fixture_for(action)
        ack = invoke(system, action, lease, owner)
        need(ack["acknowledged"], "NORMAL_ACK_MISSING")
        normal[action] = system.observe()
    need(sum(not x["publication_occurred_before_exception"] for x in cases)
         == 18, "PRE_FAULT_CASE_COUNT")
    need(sum(x["publication_occurred_before_exception"] for x in cases)
         == 4, "POST_FAULT_CASE_COUNT")
    return {
        "schema": "trust_robot_r124_shadow_terminal_audit_v1",
        "pass": True, "prototype": "modeled_single_session_not_r117_r122_clone",
        "scenarios": 2, "injection_points_per_action": 11,
        "fault_cases": len(cases), "prepublication_cases": 18,
        "postpublication_ambiguous_cases": 4,
        "successful_prepublication_retries": 18,
        "denied_postpublication_replays": 4,
        "normal_final_states": normal,
        "fault_witnesses": cases,
        "scientific_gates_closed": 11,
        "recorded_sensor_data_accessed": False,
        "sealed_test_accessed": False,
        "physical_factor_admitted": False,
        "physical_gt_scored": False,
        "estimator_or_hardware_executed": False,
        "full_r117_r122_integration_proven": False,
        "concurrent_publication_proven": False,
        "durable_recovery_proven": False,
        "cryptographically_authenticated_ledger": False,
        "physical_safety_proven": False,
    }


if __name__ == "__main__":
    print(canonical(execute()))
