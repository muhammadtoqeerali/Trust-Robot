"""R124: 29 contract tests plus 22 independent fault-case tests."""
import json
import unittest
from dataclasses import replace

from r124_shadow_terminal import (
    ACTIONS, STAGES, PREPUBLICATION_STAGES,
    POSTPUBLICATION_STAGES, GENESIS,
    ShadowTerminal, TerminalModelError,
    canonical, digest, execute, fault_case,
)


class TestR124Contract(unittest.TestCase):

    def setUp(self):
        self.model = ShadowTerminal()
        self.lease, self.owner = self.model.local_capabilities()

    def deny(self, code, fn, *args, **kwargs):
        with self.assertRaises(TerminalModelError) as cm:
            fn(*args, **kwargs)
        self.assertEqual(str(cm.exception), code)

    def cancel(self):
        return self.model.cancel(self.lease, self.owner, version=7)

    def retire(self):
        return self.model.retire(self.lease, self.owner)

    def test_initial_state(self):
        s = self.model.observe()
        self.assertEqual((s["phase"], s["version"], s["revision"]),
                         ("ACTIVE", 7, 0))
        self.assertEqual((s["active_count"], s["retired_count"]), (1, 0))
        self.assertEqual((s["attempted_work_units"],
                          s["committed_work_units"]), (5, 3))
        self.assertEqual(s["terminal_receipts"], [])
        self.assertEqual(s["registry_receipts"], [])
        self.assertEqual(s["terminal_tip"], GENESIS)

    def test_lease_owner_unique_objects(self):
        self.assertIsNot(self.lease, self.owner)
        self.assertIs(self.model._published.lease, self.lease)
        self.assertIs(self.model._published.owner, self.owner)

    def test_healthy_cancel(self):
        ack = self.cancel()
        s = self.model.observe()
        self.assertEqual(ack["phase"], "CANCELLED")
        self.assertTrue(ack["acknowledged"])
        self.assertEqual((s["version"], s["revision"]), (8, 1))

    def test_healthy_retire(self):
        self.cancel()
        ack = self.retire()
        self.assertTrue(ack["acknowledged"])
        self.assertEqual(self.model.observe()["phase"], "RETIRED")

    def test_receipt_capacity(self):
        self.cancel()
        self.retire()
        s = self.model.observe()
        self.assertEqual(len(s["terminal_receipts"]), 2)
        self.assertEqual(len(s["registry_receipts"]), 1)
        self.assertEqual(s["terminal_capacity"], 2)
        self.assertEqual(s["registry_capacity"], 1)

    def test_cancel_receipt_chain(self):
        self.cancel()
        s = self.model.observe()
        rec = s["terminal_receipts"][0]
        payload = {k: v for k, v in rec.items()
                   if k != "linked_sha256"}
        self.assertEqual(rec["linked_sha256"], digest(payload))
        self.assertEqual(rec["previous_sha256"], GENESIS)
        self.assertEqual(rec["event"], "terminal_cancel")
        self.assertEqual(s["terminal_tip"], rec["linked_sha256"])

    def test_retirement_cross_chain(self):
        self.cancel()
        self.retire()
        s = self.model.observe()
        registry = s["registry_receipts"][0]
        cancel, retirement = s["terminal_receipts"]
        self.assertEqual(registry["event"], "registry_retire")
        self.assertEqual(registry["previous_sha256"], GENESIS)
        self.assertEqual(retirement["previous_sha256"],
                         cancel["linked_sha256"])
        self.assertEqual(retirement["registry_linked_sha256"],
                         registry["linked_sha256"])
        self.assertEqual(s["registry_tip"], registry["linked_sha256"])
        self.assertEqual(s["terminal_tip"], retirement["linked_sha256"])

    def test_work_preservation(self):
        before = self.model.observe()
        self.cancel()
        self.retire()
        after = self.model.observe()
        for key in ("attempted_work_units", "committed_work_units",
                    "committed_digest"):
            self.assertEqual(before[key], after[key])

    def test_denied_submit_active(self):
        self.deny("DENIAL_SATURATED_NO_FACTOR_EXECUTION",
                  self.model.submit, {"factor": "synthetic"})

    def test_denied_submit_cancelled(self):
        self.cancel()
        self.deny("DENIAL_SATURATED_NO_FACTOR_EXECUTION",
                  self.model.submit, {"factor": "synthetic"})

    def test_denied_submit_retired(self):
        self.cancel()
        self.retire()
        self.deny("DENIAL_SATURATED_NO_FACTOR_EXECUTION",
                  self.model.submit, {"factor": "synthetic"})

    def test_unknown_lease(self):
        self.deny("STALE_OR_UNKNOWN_LEASE", self.model.cancel,
                  object(), self.owner, version=7)

    def test_cross_instance_lease(self):
        second = ShadowTerminal()
        alien_lease, _ = second.local_capabilities()
        self.deny("STALE_OR_UNKNOWN_LEASE", self.model.cancel,
                  alien_lease, self.owner, version=7)

    def test_wrong_owner(self):
        self.deny("OWNER_MISMATCH", self.model.cancel,
                  self.lease, object(), version=7)

    def test_stale_cancel_version(self):
        self.deny("STALE_VERSION", self.model.cancel,
                  self.lease, self.owner, version=6)

    def test_boolean_cancel_version(self):
        self.deny("VERSION_TYPE", self.model.cancel,
                  self.lease, self.owner, version=True)

    def test_premature_retirement(self):
        self.deny("RETIRE_PHASE_DENIED", self.retire)

    def test_duplicate_cancel(self):
        self.cancel()
        self.deny("STALE_VERSION", self.model.cancel,
                  self.lease, self.owner, version=7)

    def test_duplicate_retire(self):
        self.cancel()
        self.retire()
        self.deny("RETIRE_PHASE_DENIED", self.retire)

    def test_cancel_after_retirement(self):
        self.cancel()
        self.retire()
        self.deny("CANCEL_PHASE_DENIED", self.model.cancel,
                  self.lease, self.owner, version=8)

    def test_unknown_action(self):
        self.deny("UNKNOWN_ACTION", self.model.transact,
                  "invalid_action", self.lease, self.owner)

    def test_unknown_fault_stage(self):
        self.deny("UNKNOWN_FAULT_STAGE", self.model.cancel,
                  self.lease, self.owner, version=7,
                  inject="invalid_stage")

    def test_detached_observation(self):
        self.cancel()
        first = self.model.observe()
        original_hash = first["diagnostic_sha256"]
        first["terminal_receipts"][0]["event"] = "tampered_view"
        second = self.model.observe()
        self.assertEqual(second["terminal_receipts"][0]["event"],
                         "terminal_cancel")
        self.assertEqual(second["diagnostic_sha256"], original_hash)

    def test_incomplete_candidate_denied(self):
        self.cancel()
        original = self.model._published
        invalid = replace(original, phase="ACTIVE")
        self.deny("STATE_RECEIPT_INCONSISTENCY",
                  self.model._verify, invalid)
        self.assertIs(self.model._published, original)

    def test_registry_receipt_tamper_denied(self):
        self.cancel()
        self.retire()
        s = self.model._published
        rec = json.loads(s.registry_receipts[0])
        rec["version"] = 999
        invalid = replace(s, registry_receipts=(canonical(rec),))
        self.deny("REGISTRY_RECEIPT_MISMATCH",
                  self.model._verify, invalid)

    def test_terminal_receipt_tamper_denied(self):
        self.cancel()
        s = self.model._published
        rec = json.loads(s.terminal_receipts[0])
        rec["event"] = "unauthorized_event"
        invalid = replace(s, terminal_receipts=(canonical(rec),))
        self.deny("TERMINAL_RECEIPT_MISMATCH",
                  self.model._verify, invalid)

    def test_candidate_identity_tamper_denied(self):
        s = self.model._published
        invalid = replace(s, owner=object())
        self.deny("IDENTITY_BINDING", self.model._verify, invalid)

    def test_wrong_receipt_container_denied(self):
        s = self.model._published
        invalid = replace(s, terminal_receipts=[])
        self.deny("RECEIPT_CONTAINER", self.model._verify, invalid)

    def test_aggregate_execution_negative_gates(self):
        result = execute()
        self.assertTrue(result["pass"])
        self.assertEqual(result["fault_cases"], 22)
        self.assertEqual(result["prepublication_cases"], 18)
        self.assertEqual(result["postpublication_ambiguous_cases"], 4)
        self.assertEqual(result["scientific_gates_closed"], 11)
        for key in (
            "recorded_sensor_data_accessed",
            "sealed_test_accessed",
            "physical_factor_admitted",
            "physical_gt_scored",
            "estimator_or_hardware_executed",
            "full_r117_r122_integration_proven",
            "concurrent_publication_proven",
            "durable_recovery_proven",
            "cryptographically_authenticated_ledger",
            "physical_safety_proven",
        ):
            self.assertIs(result[key], False, key)


class TestR124FaultMatrix(unittest.TestCase):
    """Each action/stage combination is one independently named test."""
    pass


def make_fault_test(action, stage):
    def check(self):
        row = fault_case(action, stage)
        self.assertEqual(row["action"], action)
        self.assertEqual(row["stage"], stage)
        self.assertIs(row["caller_acknowledged"], False)
        self.assertEqual(
            row["publication_occurred_before_exception"],
            stage in POSTPUBLICATION_STAGES,
        )
        self.assertEqual(
            row["observation_unchanged_after_fault"],
            stage in PREPUBLICATION_STAGES,
        )
        self.assertEqual(
            row["retry_result"],
            "safe_success" if stage in PREPUBLICATION_STAGES
            else "duplicate_denied",
        )
        self.assertEqual(
            row["final_phase"],
            "CANCELLED" if action == "cancel" else "RETIRED",
        )
    return check


for action in ACTIONS:
    for stage in STAGES:
        setattr(
            TestR124FaultMatrix,
            "test_" + action + "_" + stage,
            make_fault_test(action, stage),
        )


contract_tests = [
    n for n in vars(TestR124Contract)
    if n.startswith("test_")
]
fault_tests = [
    n for n in vars(TestR124FaultMatrix)
    if n.startswith("test_")
]

assert len(contract_tests) == 29, (
    "WRONG_CONTRACT_TEST_COUNT", len(contract_tests)
)
assert len(fault_tests) == 22, (
    "WRONG_FAULT_TEST_COUNT", len(fault_tests)
)
assert len(contract_tests) + len(fault_tests) == 51


if __name__ == "__main__":
    unittest.main()
