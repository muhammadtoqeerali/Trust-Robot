import copy
import unittest

from trust_robot.m2dgr_prospective_evidence_packet_v1 import (
    build_packet,
)
from trust_robot.physical_acquisition_contract_v1 import (
    AcquisitionContractError,
    build_acquisition_contract,
    admit_acquisition_result,
)


class AcquisitionTests(unittest.TestCase):

    def report(self):
        return build_acquisition_contract(build_packet())

    def test_01_thirteen_tasks(self):
        self.assertEqual(self.report()["task_count"], 13)

    def test_02_stages(self):
        self.assertEqual(
            self.report()["stage_counts"],
            {"A": 2, "B": 6, "C": 3, "D": 2},
        )

    def test_03_priority_requests(self):
        self.assertEqual(
            len(self.report()["priority_task_ids"]), 7
        )

    def test_04_all_tasks_unacquired(self):
        self.assertTrue(all(
            t["request_status"] == "NOT_ACQUIRED"
            for t in self.report()["tasks"]
        ))

    def test_05_no_measurement_values(self):
        self.assertTrue(all(
            t["measurement_values"] is None
            and t["measurement_uncertainty"] is None
            for t in self.report()["tasks"]
        ))

    def test_06_no_witness_claim(self):
        self.assertTrue(all(
            t["witness_independence_verified"] is False
            for t in self.report()["tasks"]
        ))

    def test_07_required_technical_fields(self):
        self.assertTrue(all(
            len(t["required_field_names"]) >= 3
            for t in self.report()["tasks"]
        ))

    def test_08_b04_clock(self):
        tasks = {
            t["request_id"]: t
            for t in self.report()["tasks"]
        }
        self.assertIn(
            "clock_mapping_uncertainty",
            tasks["B04"]["required_field_names"],
        )

    def test_09_c03_geometry(self):
        tasks = {
            t["request_id"]: t
            for t in self.report()["tasks"]
        }
        self.assertIn(
            "T_target_source",
            tasks["C03"]["required_field_names"],
        )

    def test_10_deterministic(self):
        self.assertEqual(
            self.report(),
            build_acquisition_contract(
                copy.deepcopy(build_packet())
            ),
        )

    def test_11_reject_fake_receipt(self):
        packet = build_packet()
        packet["requests"][0][
            "qualifying_receipt_received"
        ] = True

        with self.assertRaises(AcquisitionContractError):
            build_acquisition_contract(packet)

    def test_12_reject_opened_gate(self):
        packet = build_packet()
        packet["requests"][0]["scientific_gate_opened"] = True

        with self.assertRaises(AcquisitionContractError):
            build_acquisition_contract(packet)

    def test_13_no_real_factor(self):
        self.assertEqual(
            self.report()["real_factor_count"], 0
        )
        self.assertEqual(
            self.report()["real_factor_admission"],
            "DENIED",
        )

    def test_14_admission_refused(self):
        with self.assertRaises(AcquisitionContractError):
            admit_acquisition_result()


if __name__ == "__main__":
    unittest.main()
