import unittest

import r104_shared_graph as graph
import r108_delivery as delivery
import r113_bounded as m

class Tests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.report=m.execute()

    def test_schema(self):
        self.assertEqual(
            self.report["schema"],m.SCHEMA
        )

    def test_status(self):
        self.assertEqual(
            self.report["status"],
            "PASS_SYNTHETIC_RESOURCE_AND_CANCELLATION_ONLY"
        )

    def test_twelve_sessions(self):
        self.assertEqual(
            self.report["healthy_sessions"],12
        )

    def test_sixty_commits(self):
        self.assertEqual(
            self.report["healthy_committed_operations"],60
        )

    def test_total_work_units(self):
        self.assertEqual(
            self.report["healthy_total_replay_work_units"],
            168
        )

    def test_session_budget(self):
        self.assertEqual(
            self.report["maximum_work_units_per_session"],
            14
        )

    def test_operation_budget(self):
        self.assertEqual(
            self.report["maximum_work_units_per_operation"],
            4
        )

    def test_actual_replay_count(self):
        self.assertEqual(
            self.report["actual_replay_witness"][
                "actual_candidate_submit_calls"
            ],14
        )

    def test_replay_count_matches_ledger(self):
        self.assertTrue(
            self.report["actual_replay_witness"][
                "accounting_exact"
            ]
        )

    def test_healthy_case_count(self):
        self.assertEqual(
            len(self.report["healthy_cases"]),12
        )

    def test_every_healthy_budget(self):
        for row in self.report["healthy_cases"].values():
            self.assertEqual(
                row["replay_work_units"],14
            )

    def test_operation_ledger(self):
        for row in self.report["healthy_cases"].values():
            self.assertEqual(
                row["operation_work_ledger"],
                [1,2,3,4,4]
            )

    def test_max_operation_units(self):
        for row in self.report["healthy_cases"].values():
            self.assertEqual(
                row["max_operation_work_units"],4
            )

    def test_healthy_factor_ownership(self):
        for row in self.report["healthy_cases"].values():
            self.assertTrue(
                row["factor_ownership_verified"]
            )

    def test_reference_accuracy(self):
        for row in self.report["healthy_cases"].values():
            bound=2e-5 if row["recentered"] else 1e-8
            self.assertLess(
                row["max_abs_error_vs_s6"],
                bound
            )

    def test_ordered_sessions(self):
        count=sum(
            row["arrival_order"]==[1,2,3,4]
            for row in self.report["healthy_cases"].values()
        )
        self.assertEqual(count,6)

    def test_reordered_sessions(self):
        count=sum(
            row["arrival_order"]==[3,2,1,4]
            for row in self.report["healthy_cases"].values()
        )
        self.assertEqual(count,6)

    def test_budget_rejection_count(self):
        self.assertEqual(
            self.report["budget_rejections"][
                "budget_rejections"
            ],3
        )

    def test_budget_rejection_immutability(self):
        self.assertTrue(
            self.report["budget_rejections"][
                "state_unchanged_for_all_rejections"
            ]
        )

    def test_cancel_after_two_packets(self):
        self.assertEqual(
            self.report["ownership_and_cancellation"][
                "cancelled_after_acknowledged_packets"
            ],2
        )

    def test_wrong_owner_rejected(self):
        self.assertEqual(
            self.report["ownership_and_cancellation"][
                "rejected_unauthorized_or_terminal_operations"
            ],7
        )

    def test_cancel_preserves_committed(self):
        self.assertTrue(
            self.report["ownership_and_cancellation"][
                "committed_state_preserved"
            ]
        )

    def test_cancelled_session_cannot_resume(self):
        self.assertTrue(
            self.report["ownership_and_cancellation"][
                "cancelled_session_reuse_denied"
            ]
        )

    def test_prepublication_abort(self):
        self.assertFalse(
            self.report["prepublication_cancellation"][
                "candidate_published"
            ]
        )

    def test_prepublication_snapshot(self):
        self.assertTrue(
            self.report["prepublication_cancellation"][
                "committed_state_unchanged"
            ]
        )

    def test_prepublication_no_ack(self):
        self.assertFalse(
            self.report["prepublication_cancellation"][
                "acknowledgement_issued"
            ]
        )

    def test_prepublication_terminal(self):
        self.assertTrue(
            self.report["prepublication_cancellation"][
                "session_terminal"
            ]
        )

    def test_solver_failure_zero_budget(self):
        self.assertEqual(
            self.report["injected_solver_failure"][
                "failed_candidate_committed_work_units"
            ],0
        )

    def test_solver_failure_retry(self):
        self.assertTrue(
            self.report["injected_solver_failure"][
                "retry_after_fault_removed"
            ]
        )

    def test_solver_retry_budget(self):
        self.assertEqual(
            self.report["injected_solver_failure"][
                "successful_session_work_units"
            ],14
        )

    def test_bad_operation_limit(self):
        g=graph.build("clean",True,13)
        with self.assertRaises(m.BudgetError):
            m.open_session(
                g,max_operation_units=5
            )

    def test_bad_total_limit(self):
        g=graph.build("clean",True,13)
        with self.assertRaises(m.BudgetError):
            m.open_session(
                g,max_total_units=15
            )

    def test_boolean_budget_denied(self):
        g=graph.build("clean",True,13)
        with self.assertRaises(m.BudgetError):
            m.open_session(
                g,max_total_units=True
            )

    def test_wrong_version_denied(self):
        g=graph.build("clean",True,13)
        session,owner=m.open_session(g)

        before=session.summary()

        with self.assertRaises(m.BudgetError):
            session.submit(
                owner,
                delivery.make_packet(g,1),
                expected_version=1
            )

        self.assertEqual(session.summary(),before)

    def test_wrong_owner_denied(self):
        g=graph.build("clean",True,13)
        session,owner=m.open_session(g)

        before=session.summary()

        with self.assertRaises(m.BudgetError):
            session.submit(
                object(),
                delivery.make_packet(g,1),
                expected_version=0
            )

        self.assertEqual(session.summary(),before)

    def test_cancel_version(self):
        g=graph.build("clean",True,13)
        session,owner=m.open_session(g)

        session.submit(
            owner,
            delivery.make_packet(g,1),
            expected_version=0
        )

        receipt=session.cancel(
            owner,
            expected_version=1
        )

        self.assertEqual(receipt["version"],1)
        self.assertEqual(session.version,1)
        self.assertEqual(session.phase,"CANCELLED")

    def test_no_physical_memory_bound(self):
        self.assertFalse(
            self.report["physical_memory_bound_verified"]
        )

    def test_no_wall_clock_guarantee(self):
        self.assertFalse(
            self.report["wall_clock_latency_bound_verified"]
        )

    def test_no_concurrent_cancellation_claim(self):
        self.assertFalse(
            self.report[
                "concurrent_cancellation_safety_verified"
            ]
        )

    def test_no_cryptographic_owner_claim(self):
        self.assertFalse(
            self.report[
                "cryptographic_owner_authentication_verified"
            ]
        )

    def test_no_durable_cancellation_claim(self):
        self.assertFalse(
            self.report["durable_cancellation_verified"]
        )

    def test_no_r95_import(self):
        self.assertFalse(
            self.report["r95_backend_imported"]
        )

    def test_no_real_sensor_factors(self):
        self.assertFalse(
            self.report["real_sensor_factors_authorized"]
        )

    def test_confirmation_sealed(self):
        self.assertFalse(
            self.report["confirmation_test_accessed"]
        )

    def test_no_health_or_ate(self):
        self.assertFalse(
            self.report["health_training_authorized"]
        )
        self.assertFalse(
            self.report["ate_rpe_authorized"]
        )

    def test_scientific_gates(self):
        self.assertEqual(
            self.report["scientific_gates_closed"],11
        )

    def test_deterministic_report(self):
        self.assertEqual(
            m.canonical(self.report),
            m.canonical(m.execute())
        )

if __name__=="__main__":
    unittest.main(verbosity=2)
