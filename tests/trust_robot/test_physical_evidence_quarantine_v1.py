import hashlib
import tempfile
import unittest
from pathlib import Path

from trust_robot.physical_evidence_quarantine_v1 import (
    EvidenceQuarantineError,
    review_quarantined_candidate,
    release_physical_evidence,
)

DATA = b"SYNTHETIC_CANDIDATE_BYTES_ONLY"


def candidate(data=DATA, request="B04"):
    return {
        "request_id": request,
        "capture_session_reference": "synthetic-session",
        "acquisition_actor_token": "synthetic-acquirer",
        "witness_actor_token": "synthetic-witness",
        "method_version": "synthetic-method",
        "declared_artifact_sha256":
            hashlib.sha256(data).hexdigest(),
        "clock_domain": "synthetic-clock",
        "physical_event_definition": "synthetic-event",
        "uncertainty_method": "synthetic-method",
        "transform_direction": None,
        "independent_review_status": "UNREVIEWED",
        "witness_independence_verified": False,
        "scientific_gate_opened": False,
    }


class QuarantineTests(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "synthetic.bin").write_bytes(DATA)

    def review(self, candidate_data=None):
        return review_quarantined_candidate(
            str(self.root),
            "synthetic.bin",
            candidate() if candidate_data is None
            else candidate_data,
        )

    def test_01_sha_preflight(self):
        result = self.review()
        self.assertEqual(
            result["status"],
            "READ_ONLY_CANDIDATE_BYTE_PREFLIGHT_ONLY",
        )

    def test_02_source_unmodified(self):
        self.review()
        self.assertEqual(
            (self.root / "synthetic.bin").read_bytes(),
            DATA,
        )

    def test_03_no_qualification(self):
        result = self.review()
        self.assertFalse(
            result["independent_witness_verified"]
        )
        self.assertFalse(
            result["candidate_receipt_qualified"]
        )

    def test_04_deterministic(self):
        self.assertEqual(self.review(), self.review())

    def test_05_reject_wrong_digest(self):
        with self.assertRaises(EvidenceQuarantineError):
            self.review(candidate(b"ALTERED"))

    def test_06_reject_forged_review(self):
        c = candidate()
        c["independent_review_status"] = "APPROVED"

        with self.assertRaises(EvidenceQuarantineError):
            self.review(c)

    def test_07_reject_forged_independence(self):
        c = candidate()
        c["witness_independence_verified"] = True

        with self.assertRaises(EvidenceQuarantineError):
            self.review(c)

    def test_08_reject_opened_gate(self):
        c = candidate()
        c["scientific_gate_opened"] = True

        with self.assertRaises(EvidenceQuarantineError):
            self.review(c)

    def test_09_reject_path_traversal(self):
        with self.assertRaises(EvidenceQuarantineError):
            review_quarantined_candidate(
                str(self.root), "../outside", candidate()
            )

    def test_10_reject_absolute_filename(self):
        with self.assertRaises(EvidenceQuarantineError):
            review_quarantined_candidate(
                str(self.root), "/etc/passwd", candidate()
            )

    def test_11_reject_symlink_file(self):
        (self.root / "link.bin").symlink_to(
            self.root / "synthetic.bin"
        )

        with self.assertRaises(EvidenceQuarantineError):
            review_quarantined_candidate(
                str(self.root), "link.bin", candidate()
            )

    def test_12_reject_symlink_root(self):
        link = self.root.parent / (
            self.root.name + "_alias"
        )
        link.symlink_to(self.root, target_is_directory=True)
        self.addCleanup(link.unlink)

        with self.assertRaises(EvidenceQuarantineError):
            review_quarantined_candidate(
                str(link), "synthetic.bin", candidate()
            )

    def test_13_reject_empty_file(self):
        (self.root / "synthetic.bin").write_bytes(b"")

        with self.assertRaises(EvidenceQuarantineError):
            self.review()

    def test_14_reject_missing_file(self):
        with self.assertRaises(EvidenceQuarantineError):
            review_quarantined_candidate(
                str(self.root), "missing.bin", candidate()
            )

    def test_15_reject_same_actor(self):
        c = candidate()
        c["witness_actor_token"] = c["acquisition_actor_token"]

        with self.assertRaises(EvidenceQuarantineError):
            self.review(c)

    def test_16_no_real_factor(self):
        result = self.review()
        self.assertEqual(result["real_factor_count"], 0)
        self.assertEqual(
            result["real_factor_admission"],
            "DENIED",
        )

    def test_17_release_refused(self):
        with self.assertRaises(EvidenceQuarantineError):
            release_physical_evidence()


if __name__ == "__main__":
    unittest.main()
