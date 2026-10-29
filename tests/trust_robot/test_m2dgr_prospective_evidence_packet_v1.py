import ast
import copy
import hashlib
import inspect
import json
import unittest
from pathlib import Path

from trust_robot.m2dgr_prospective_evidence_packet_v1 import (
    ROOT,
    SCHEMA,
    STATUS,
    STAGES,
    REQUEST_SPECS,
    L33_PATH,
    L33_BLOB,
    PACKET_PATH,
    EvidencePacketError,
    build_packet,
    validate_packet,
    packet_sha256,
    load_committed_packet,
)

from trust_robot.m2dgr_frozen_evidence_readiness_v1 import (
    run_review as a22_review,
)

from trust_robot.analytic_15d_evidence_review_v1 import (
    BLOCKED_CAPABILITIES,
)


class ProspectiveEvidencePacketTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.packet = build_packet()
        cls.a22 = a22_review()

    def test_01_schema_and_status(self):
        self.assertEqual(self.packet["schema"], SCHEMA)
        self.assertEqual(self.packet["status"], STATUS)

    def test_02_l33_source_identity(self):
        raw = (ROOT / L33_PATH).read_bytes()

        blob = hashlib.sha1(
            b"blob "
            + str(len(raw)).encode()
            + b"\0"
            + raw
        ).hexdigest()

        self.assertEqual(blob, L33_BLOB)

    def test_03_four_existing_stages(self):
        self.assertEqual(len(STAGES), 4)
        self.assertEqual(
            [s["stage"] for s in self.packet["stages"]],
            ["A", "B", "C", "D"],
        )

    def test_04_no_stage_qualified(self):
        for stage in self.packet["stages"]:
            self.assertEqual(
                stage["l33_qualification"],
                "NOT_YET_VERIFIED",
            )
            self.assertIs(stage["stage_authorized"], False)
            self.assertEqual(
                stage["completed_independent_receipts"], 0
            )

    def test_05_thirteen_requests(self):
        self.assertEqual(len(REQUEST_SPECS), 13)
        self.assertEqual(len(self.packet["requests"]), 13)

    def test_06_unique_request_identity(self):
        ids = [
            r["request_id"]
            for r in self.packet["requests"]
        ]
        self.assertEqual(len(ids), len(set(ids)))

    def test_07_all_eleven_blockers_covered(self):
        covered = {
            r["a22_diagnostic_blocker"]
            for r in self.packet["requests"]
            if r["a22_diagnostic_blocker"] is not None
        }
        self.assertEqual(
            covered,
            set(self.a22["diagnostic_blockers"]),
        )

    def test_08_two_independent_provenance_requests(self):
        initial = [
            r for r in self.packet["requests"]
            if r["stage"] == "A"
        ]
        self.assertEqual(len(initial), 2)
        self.assertTrue(all(
            r["a22_diagnostic_blocker"] is None
            for r in initial
        ))

    def test_09_stage_dependency_order(self):
        for index, stage in enumerate(
            self.packet["stages"]
        ):
            self.assertEqual(
                stage["previous_stages_to_verify"],
                ["A", "B", "C", "D"][:index],
            )

    def test_10_request_assignment_exact(self):
        actual = [
            ident
            for s in self.packet["stages"]
            for ident in s["prospective_request_ids"]
        ]
        expected = [
            r["request_id"]
            for r in self.packet["requests"]
        ]
        self.assertEqual(set(actual), set(expected))
        self.assertEqual(len(actual), len(expected))

    def test_11_no_fabricated_receipts(self):
        for request in self.packet["requests"]:
            self.assertEqual(
                request["request_status"], "UNFULFILLED"
            )
            self.assertIs(
                request["qualifying_receipt_received"],
                False,
            )
            self.assertIsNone(
                request["evidence_artifact_sha256"]
            )
            self.assertIsNone(
                request["physical_parameter_value"]
            )

    def test_12_no_timing_selection(self):
        for key in (
            "capture_time_offset_selected",
            "capture_time_tolerance_selected",
            "physical_extrinsics_verified",
            "physical_reference_verified",
        ):
            self.assertIs(self.packet[key], False)

        self.assertIsNone(
            self.packet["capture_time_offset_seconds"]
        )
        self.assertIsNone(
            self.packet["capture_time_tolerance_seconds"]
        )

    def test_13_original_gates_closed(self):
        self.assertEqual(
            self.packet["original_m2dgr_gates_closed"],
            11,
        )
        self.assertIs(
            self.packet[
                "diagnostic_checks_are_original_gates"
            ],
            False,
        )

    def test_14_holdout_caveat_retained(self):
        self.assertIs(
            self.packet[
                "confirmation_test_pristine_from_prior_inspection"
            ],
            False,
        )
        self.assertIs(
            self.packet[
                "confirmation_test_prospectively_closed"
            ],
            True,
        )
        self.assertEqual(
            self.packet["frozen_m2dgr_split"],
            {
                "train": 22,
                "validation_calibration": 7,
                "confirmation_test": 7,
            },
        )

    def test_15_all_scientific_permissions_blocked(self):
        self.assertEqual(
            set(self.packet["scientific_permissions"]),
            set(BLOCKED_CAPABILITIES),
        )
        self.assertTrue(all(
            v == "BLOCKED"
            for v in self.packet[
                "scientific_permissions"
            ].values()
        ))

    def test_16_packet_digest_determinism(self):
        first = packet_sha256(self.packet)
        second = packet_sha256(build_packet())
        self.assertEqual(first, second)
        self.assertEqual(len(first), 64)

    def test_17_committed_packet_matches_builder(self):
        disk = load_committed_packet()
        self.assertEqual(disk, self.packet)
        self.assertEqual(
            packet_sha256(disk),
            packet_sha256(self.packet),
        )

    def test_18_reject_fabricated_witness(self):
        altered = copy.deepcopy(self.packet)
        altered["requests"][0][
            "independent_review_status"
        ] = "VERIFIED"

        with self.assertRaises(EvidencePacketError):
            validate_packet(altered)

    def test_19_reject_fabricated_qualification(self):
        altered = copy.deepcopy(self.packet)
        altered["requests"][2][
            "qualifying_receipt_received"
        ] = True

        with self.assertRaises(EvidencePacketError):
            validate_packet(altered)

        altered = copy.deepcopy(self.packet)
        altered["stages"][1]["stage_authorized"] = True

        with self.assertRaises(EvidencePacketError):
            validate_packet(altered)

        altered = copy.deepcopy(self.packet)
        altered["scientific_permissions"][
            "real_sensor_factor_admission"
        ] = "AUTHORIZED"

        with self.assertRaises(EvidencePacketError):
            validate_packet(altered)

    def test_20_no_real_data_or_execution_scope(self):
        for key in (
            "physical_evidence_received",
            "real_sensor_contact_performed",
            "recorded_dataset_accessed",
            "ground_truth_scoring_performed",
            "health_inference_authorized",
            "factor_weights_modified",
            "real_factor_execution_authorized",
            "future_acquisition_is_retroactive_m2dgr_proof",
        ):
            self.assertIs(self.packet[key], False)

        self.assertEqual(
            self.packet["decision"],
            "REQUEST_ONLY_NO_ADMISSION",
        )

        self.assertEqual(
            len(inspect.signature(
                build_packet
            ).parameters),
            0,
        )

        self.assertTrue(
            PACKET_PATH.startswith(
                "configs/trust_robot/"
            )
        )

        source = ROOT / (
            "src/trust_robot/"
            "m2dgr_prospective_evidence_packet_v1.py"
        )

        modules = {
            node.module
            for node in ast.walk(
                ast.parse(source.read_text())
            )
            if isinstance(node, ast.ImportFrom)
            and node.module is not None
        }

        self.assertEqual(modules, {
            "__future__",
            "pathlib",
            "trust_robot.m2dgr_frozen_evidence_readiness_v1",
            "trust_robot.analytic_15d_evidence_review_v1",
        })


if __name__ == "__main__":
    unittest.main(verbosity=2)
