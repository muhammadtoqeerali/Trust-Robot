"""A30-2 prospective work-order tests; no real dataset access."""

import copy
import unittest

from trust_robot.m2dgr_prospective_evidence_packet_v1 import (
    build_packet,
)

from trust_robot.independent_acquisition_plan_v1 import (
    AcquisitionPlanError,
    build_work_orders,
    accept_independent_receipt,
)


class AcquisitionPlanTests(unittest.TestCase):

    def test_01_exact_thirteen(self):
        result = build_work_orders(build_packet())
        self.assertEqual(result["request_count"], 13)
        self.assertEqual(len(result["work_orders"]), 13)

    def test_02_four_stages(self):
        result = build_work_orders(build_packet())
        self.assertEqual(
            result["stage_counts"],
            {"A": 2, "B": 6, "C": 3, "D": 2},
        )

    def test_03_deterministic(self):
        p = build_packet()
        self.assertEqual(
            build_work_orders(p),
            build_work_orders(copy.deepcopy(p)),
        )

    def test_04_no_receipt_claims(self):
        result = build_work_orders(build_packet())
        self.assertTrue(all(
            item["received_receipt"] is None
            for item in result["work_orders"]
        ))

    def test_05_no_qualified_values(self):
        result = build_work_orders(build_packet())
        self.assertTrue(all(
            item["measurement_value"] is None
            and item["uncertainty_value"] is None
            for item in result["work_orders"]
        ))

    def test_06_preserve_blockers(self):
        result = build_work_orders(build_packet())
        self.assertEqual(
            len([
                item
                for item in result["work_orders"]
                if item["a22_diagnostic_blocker"] is not None
            ]),
            11,
        )

    def test_07_reject_fake_receipt(self):
        p = build_packet()
        p["requests"][0]["qualifying_receipt_received"] = True
        with self.assertRaises(AcquisitionPlanError):
            build_work_orders(p)

    def test_08_reject_fake_physical_parameter(self):
        p = build_packet()
        p["requests"][2]["physical_parameter_value"] = 0.1
        with self.assertRaises(AcquisitionPlanError):
            build_work_orders(p)

    def test_09_reject_opened_gate(self):
        p = build_packet()
        p["requests"][0]["scientific_gate_opened"] = True
        with self.assertRaises(AcquisitionPlanError):
            build_work_orders(p)

    def test_10_reject_reordered_requests(self):
        p = build_packet()
        p["requests"][0], p["requests"][1] = (
            p["requests"][1], p["requests"][0]
        )
        with self.assertRaises(AcquisitionPlanError):
            build_work_orders(p)

    def test_11_reject_changed_holdout(self):
        p = build_packet()
        p["confirmation_test_prospectively_closed"] = False
        with self.assertRaises(AcquisitionPlanError):
            build_work_orders(p)

    def test_12_reject_wrong_source_schema(self):
        p = build_packet()
        p["schema"] = "MUTATED"
        with self.assertRaises(AcquisitionPlanError):
            build_work_orders(p)

    def test_13_no_factor_admission(self):
        result = build_work_orders(build_packet())
        self.assertEqual(result["real_factor_count"], 0)
        self.assertEqual(
            result["real_factor_admission"], "DENIED"
        )
        self.assertEqual(result["m2dgr_gates"], "11_CLOSED")

    def test_14_receipt_acceptance_denied(self):
        with self.assertRaises(AcquisitionPlanError):
            accept_independent_receipt({})

    def test_15_proposed_methods_nonempty(self):
        result = build_work_orders(build_packet())
        self.assertTrue(all(
            item["proposed_acquisition_method"]
            and item["expected_independent_artifact"]
            for item in result["work_orders"]
        ))

    def test_16_not_retroactive_m2dgr_proof(self):
        result = build_work_orders(build_packet())
        self.assertFalse(
            result["retroactive_m2dgr_qualification"]
        )
        self.assertFalse(result["confirmation_test_accessed"])


if __name__ == "__main__":
    unittest.main()
