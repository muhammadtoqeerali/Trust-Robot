import unittest

import r104_shared_graph as graph
import r108_delivery as delivery
import r114_attempts as m

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
            "PASS_SYNTHETIC_ATTEMPT_BUDGET_ONLY"
        )

    def test_twelve_sessions(self):
        self.assertEqual(
            self.report["healthy_sessions"],12
        )

    def test_sixty_operations(self):
        self.assertEqual(
            self.report["healthy_committed_operations"],60
        )

    def test_healthy_attempt_units(self):
        self.assertEqual(
            self.report["healthy_attempted_work_units"],168
        )

    def test_healthy_committed_units(self):
        self.assertEqual(
            self.report["healthy_committed_work_units"],168
        )

    def test_healthy_cases(self):
        self.assertEqual(
            len(self.report["healthy_cases"]),12
        )

    def test_fourteen_units_per_healthy_run(self):
        for row in self.report["healthy_cases"].values():
            self.assertEqual(
                row["attempted_work_units"],14
            )

    def test_healthy_work_ledger(self):
        for row in self.report["healthy_cases"].values():
            self.assertEqual(
                row["operation_ledger"],
                [1,2,3,4,4]
            )

    def test_healthy_committed_equals_attempted(self):
        for row in self.report["healthy_cases"].values():
            self.assertEqual(
                row["committed_work_units"],
                row["attempted_work_units"]
            )

    def test_healthy_s6_equivalence(self):
        for row in self.report["healthy_cases"].values():
            threshold=2e-5 if row["recentered"] else 1e-8
            self.assertLess(
                row["max_abs_error_vs_s6"],
                threshold
            )

    def test_healthy_factor_ownership(self):
        for row in self.report["healthy_cases"].values():
            self.assertTrue(
                row["factor_history_validated"]
            )

    def test_six_fault_stages(self):
        self.assertEqual(
            set(self.report["fault_cases"]),
            set(m.FAULTS)
        )

    def test_six_failed_attempt_charges(self):
        self.assertEqual(
            self.report["failed_candidates_charged"],6
        )

    def test_six_safe_retries(self):
        self.assertEqual(
            self.report["successful_retries"],6
        )

    def test_no_refunds(self):
        for row in self.report["fault_cases"].values():
            self.assertTrue(
                row["failed_units_retained_after_retry"]
            )

    def test_committed_state_isolation(self):
        for row in self.report["fault_cases"].values():
            self.assertTrue(
                row["committed_state_unchanged_on_failure"]
            )

    def test_no_failed_acknowledgement(self):
        for row in self.report["fault_cases"].values():
            self.assertFalse(
                row["failed_attempt_acknowledged"]
            )

    def test_retry_completed(self):
        for row in self.report["fault_cases"].values():
            self.assertTrue(
                row["successful_retry"]
            )

    def test_failed_attempt_costs(self):
        for row in self.report["fault_cases"].values():
            self.assertEqual(
                row["final_attempted_work_units"],
                14+row["reserved_failed_units"]
            )

    def test_committed_cost_after_retry(self):
        for row in self.report["fault_cases"].values():
            self.assertEqual(
                row["final_committed_work_units"],14
            )

    def test_failed_dispatch_within_reservation(self):
        for row in self.report["fault_cases"].values():
            self.assertLessEqual(
                row["observed_failed_candidate_submissions"],
                row["reserved_failed_units"]
            )

    def test_three_repeated_failures(self):
        self.assertEqual(
            self.report["repeated_failure_exhaustion"][
                "failed_attempts"
            ],3
        )

    def test_failed_attempts_consume_budget(self):
        self.assertEqual(
            self.report["repeated_failure_exhaustion"][
                "failed_work_units_charged"
            ],3
        )

    def test_exhaustion_denies_fourth_attempt(self):
        self.assertTrue(
            self.report["repeated_failure_exhaustion"][
                "fourth_attempt_rejected_before_execution"
            ]
        )

    def test_exhaustion_preserves_committed_state(self):
        self.assertEqual(
            self.report["repeated_failure_exhaustion"][
                "committed_work_units"
            ],0
        )

    def test_cancelled_exhausted_session(self):
        self.assertTrue(
            self.report["repeated_failure_exhaustion"][
                "cancelled_after_exhaustion"
            ]
        )

    def test_prepublication_charge(self):
        self.assertEqual(
            self.report["prepublication_cancellation"][
                "work_reserved_before_cancellation"
            ],1
        )

    def test_prepublication_not_refunded(self):
        self.assertFalse(
            self.report["prepublication_cancellation"][
                "work_refunded"
            ]
        )

    def test_prepublication_not_published(self):
        self.assertFalse(
            self.report["prepublication_cancellation"][
                "candidate_published"
            ]
        )

    def test_cancelled_session_terminal(self):
        self.assertTrue(
            self.report["prepublication_cancellation"][
                "session_terminal"
            ]
        )

    def test_unauthorized_admissions_not_charged(self):
        self.assertEqual(
            self.report["invalid_admissions"][
                "work_charged_for_rejected_admission"
            ],0
        )

    def test_unauthorized_admission_count(self):
        self.assertEqual(
            self.report["invalid_admissions"][
                "invalid_operations_rejected"
            ],4
        )

    def test_actual_dispatch_witness(self):
        self.assertEqual(
            self.report["actual_dispatch_witness"][
                "observed_candidate_submit_calls"
            ],14
        )

    def test_exact_dispatch_accounting(self):
        self.assertTrue(
            self.report["actual_dispatch_witness"][
                "accounting_exact"
            ]
        )

    def test_initial_budget(self):
        g=graph.build("clean",True,13)
        session,owner=m.open_session(g)

        self.assertEqual(
            session.attempted_work_units,0
        )
        self.assertEqual(
            session.committed_work_units,0
        )

    def test_first_submit_charge(self):
        g=graph.build("clean",True,13)
        session,owner=m.open_session(g)

        session.submit(
            owner,
            delivery.make_packet(g,1),
            expected_version=0
        )

        self.assertEqual(
            session.attempted_work_units,1
        )
        self.assertEqual(
            session.committed_work_units,1
        )

    def test_bad_attempt_limit(self):
        g=graph.build("clean",True,13)

        with self.assertRaises(m.AttemptError):
            m.open_session(
                g,max_attempt_operation_units=5
            )

    def test_bad_total_attempt_limit(self):
        g=graph.build("clean",True,13)

        with self.assertRaises(m.AttemptError):
            m.open_session(
                g,max_attempt_total_units=25
            )

    def test_boolean_limit_denied(self):
        g=graph.build("clean",True,13)

        with self.assertRaises(m.AttemptError):
            m.open_session(
                g,max_attempt_total_units=True
            )

    def test_wrong_owner_denied(self):
        g=graph.build("clean",True,13)
        session,owner=m.open_session(g)

        before=session.summary()

        with self.assertRaises(m.AttemptError):
            session.submit(
                object(),
                delivery.make_packet(g,1),
                expected_version=0
            )

        self.assertEqual(
            session.summary(),before
        )

    def test_wrong_version_denied(self):
        g=graph.build("clean",True,13)
        session,owner=m.open_session(g)

        before=session.summary()

        with self.assertRaises(m.AttemptError):
            session.submit(
                owner,
                delivery.make_packet(g,1),
                expected_version=1
            )

        self.assertEqual(
            session.summary(),before
        )

    def test_no_wall_clock_claim(self):
        self.assertFalse(
            self.report["wall_clock_latency_bound_verified"]
        )

    def test_no_memory_claim(self):
        self.assertFalse(
            self.report["physical_memory_bound_verified"]
        )

    def test_no_floating_point_work_claim(self):
        self.assertFalse(
            self.report["floating_point_work_bound_verified"]
        )

    def test_no_concurrency_claim(self):
        self.assertFalse(
            self.report["concurrent_atomicity_verified"]
        )

    def test_no_durable_ledger_claim(self):
        self.assertFalse(
            self.report["durable_attempt_ledger_verified"]
        )

    def test_no_authentication_claim(self):
        self.assertFalse(
            self.report[
                "cryptographic_owner_authentication_verified"
            ]
        )

    def test_no_r95_import(self):
        self.assertFalse(
            self.report["r95_backend_imported"]
        )

    def test_no_real_sensor_factors(self):
        self.assertFalse(
            self.report["real_sensor_factors_authorized"]
        )

    def test_no_health_or_ate(self):
        self.assertFalse(
            self.report["health_training_authorized"]
        )
        self.assertFalse(
            self.report["ate_rpe_authorized"]
        )

    def test_confirmation_sealed(self):
        self.assertFalse(
            self.report["confirmation_test_accessed"]
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
