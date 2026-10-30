import copy
import hashlib
import unittest

from trust_robot.m2dgr_prospective_evidence_packet_v1 import (
    build_packet,
)
from trust_robot.independent_evidence_intake_v1 import (
    EvidenceIntakeError,
    blank_intake_ledger,
    preflight_candidate,
    accept_as_qualified_receipt,
)


PAYLOAD = b"SYNTHETIC_TEST_ARTIFACT_ONLY"


def fixture(request_id="B04"):
    return {
        "request_id": request_id,
        "capture_session_reference": "synthetic-session",
        "acquisition_actor_token": "synthetic-acquirer",
        "witness_actor_token": "synthetic-reviewer",
        "method_version": "synthetic-method-v1",
        "declared_artifact_sha256":
            hashlib.sha256(PAYLOAD).hexdigest(),
        "clock_domain": "synthetic-clock",
        "physical_event_definition":
            "synthetic-test-event",
        "uncertainty_method":
            "synthetic-uncertainty-proposal",
        "transform_direction": None,
        "independent_review_status": "UNREVIEWED",
        "witness_independence_verified": False,
        "scientific_gate_opened": False,
    }


class IntakeTests(unittest.TestCase):

    def mutate(self, change):
        data = fixture()
        change(data)
        with self.assertRaises(EvidenceIntakeError):
            preflight_candidate(data, PAYLOAD)

    def test_01_empty_thirteen_request_ledger(self):
        result = blank_intake_ledger(build_packet())
        self.assertEqual(result["request_count"], 13)
        self.assertEqual(
            result["qualified_evidence_receipts"], 0
        )

    def test_02_hash_bound_candidate(self):
        result = preflight_candidate(
            fixture(), PAYLOAD
        )
        self.assertEqual(
            result["status"],
            "CANDIDATE_ARTIFACT_SHA_MATCH_ONLY",
        )
        self.assertFalse(
            result["witness_independence_verified"]
        )

    def test_03_deterministic_preflight(self):
        self.assertEqual(
            preflight_candidate(fixture(), PAYLOAD),
            preflight_candidate(
                copy.deepcopy(fixture()), PAYLOAD
            ),
        )

    def test_04_modified_payload_rejected(self):
        with self.assertRaises(EvidenceIntakeError):
            preflight_candidate(
                fixture(), PAYLOAD + b"CHANGED"
            )

    def test_05_wrong_request(self):
        self.mutate(lambda x: x.update(
            request_id="UNKNOWN"
        ))

    def test_06_same_actor(self):
        self.mutate(lambda x: x.update(
            witness_actor_token="synthetic-acquirer"
        ))

    def test_07_fake_independence(self):
        self.mutate(lambda x: x.update(
            witness_independence_verified=True
        ))

    def test_08_fake_review(self):
        self.mutate(lambda x: x.update(
            independent_review_status="APPROVED"
        ))

    def test_09_opened_gate(self):
        self.mutate(lambda x: x.update(
            scientific_gate_opened=True
        ))

    def test_10_missing_event_semantics(self):
        self.mutate(lambda x: x.update(
            physical_event_definition=None
        ))

    def test_11_missing_clock(self):
        self.mutate(lambda x: x.update(
            clock_domain=None
        ))

    def test_12_missing_uncertainty_method(self):
        self.mutate(lambda x: x.update(
            uncertainty_method=None
        ))

    def test_13_nonbytes_payload(self):
        with self.assertRaises(EvidenceIntakeError):
            preflight_candidate(fixture(), "text")

    def test_14_empty_payload(self):
        with self.assertRaises(EvidenceIntakeError):
            preflight_candidate(fixture(), b"")

    def test_15_transform_direction_required(self):
        with self.assertRaises(EvidenceIntakeError):
            preflight_candidate(
                fixture("B03"), PAYLOAD
            )

    def test_16_valid_direction_still_unverified(self):
        x = fixture("B03")
        x["transform_direction"] = "T_target_source"
        result = preflight_candidate(x, PAYLOAD)
        self.assertFalse(
            result["metric_calibration_verified"]
        )

    def test_17_extra_field_rejected(self):
        self.mutate(lambda x: x.update(
            qualifying_receipt=True
        ))

    def test_18_admission_always_denied(self):
        with self.assertRaises(EvidenceIntakeError):
            accept_as_qualified_receipt(fixture())

    def test_19_changed_a23_packet_rejected(self):
        p = build_packet()
        p["requests"][0]["scientific_gate_opened"] = True
        with self.assertRaises(EvidenceIntakeError):
            blank_intake_ledger(p)

    def test_20_no_real_factor(self):
        result = preflight_candidate(
            fixture(), PAYLOAD
        )
        self.assertEqual(result["real_factor_count"], 0)
        self.assertEqual(
            result["real_factor_admission"], "DENIED"
        )
        self.assertEqual(result["m2dgr_gates"], "11_CLOSED")


if __name__ == "__main__":
    unittest.main()
