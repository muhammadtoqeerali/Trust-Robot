import unittest
from dataclasses import replace

import r104_shared_graph as graph
import r108_delivery as delivery
import r110_failstop as m

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
            "PASS_SYNTHETIC_FAIL_STOP_SOFTWARE_ONLY"
        )

    def test_six_healthy_runs(self):
        self.assertEqual(
            self.report["healthy_solver_executions"],6
        )

    def test_healthy_windows(self):
        self.assertEqual(
            self.report["healthy_nonlinear_windows"],24
        )

    def test_healthy_schur(self):
        self.assertEqual(
            self.report["healthy_schur_marginalizations"],18
        )

    def test_healthy_transfers(self):
        self.assertEqual(
            self.report["healthy_prior_recenterings"],9
        )

    def test_six_fault_types(self):
        self.assertEqual(
            set(self.report["fault_cases"]),
            set(m.FAULTS)
        )

    def test_six_quarantines(self):
        self.assertEqual(
            self.report["faulted_sessions_quarantined"],6
        )

    def test_fault_state_changes_observed(self):
        self.assertGreaterEqual(
            self.report[
                "faults_with_internal_state_change"
            ],4
        )

    def test_prediction_fault(self):
        self.assertTrue(
            self.report["fault_cases"][
                "imu_prediction"
            ]["session_quarantined"]
        )

    def test_optimizer_fault(self):
        self.assertTrue(
            self.report["fault_cases"][
                "nonlinear_optimization"
            ]["session_quarantined"]
        )

    def test_schur_fault(self):
        self.assertTrue(
            self.report["fault_cases"][
                "schur_marginalization"
            ]["session_quarantined"]
        )

    def test_recenter_fault(self):
        self.assertTrue(
            self.report["fault_cases"][
                "prior_recentering"
            ]["session_quarantined"]
        )

    def test_postprocessing_fault(self):
        event=self.report["fault_cases"][
            "post_processing_acknowledgement"
        ]["fault_receipt"]

        self.assertFalse(
            event["successful_acknowledgement_issued"]
        )

        self.assertTrue(
            event["estimator_changed_before_fault"]
        )

    def test_finish_fault(self):
        self.assertTrue(
            self.report["fault_cases"][
                "finalization"
            ]["session_quarantined"]
        )

    def test_all_causes_exact(self):
        for case in self.report["fault_cases"].values():
            self.assertEqual(
                case["fault_receipt"]["exception_type"],
                "InjectedFault"
            )

    def test_no_fault_ack(self):
        for case in self.report["fault_cases"].values():
            self.assertFalse(
                case["fault_receipt"][
                    "successful_acknowledgement_issued"
                ]
            )

    def test_post_fault_operations_denied(self):
        for case in self.report["fault_cases"].values():
            self.assertEqual(
                case["post_fault_operations_rejected"],2
            )
            self.assertTrue(
                case[
                    "post_fault_state_unchanged_on_rejection"
                ]
            )

    def test_no_rollback_claim(self):
        for case in self.report["fault_cases"].values():
            self.assertFalse(
                case["rollback_proven"]
            )
            self.assertFalse(
                case["fault_receipt"][
                    "transactional_rollback_performed"
                ]
            )

    def test_pre_admission_rejections(self):
        self.assertEqual(
            self.report["admission"][
                "pre_admission_rejections"
            ],8
        )

    def test_pre_admission_immutable(self):
        self.assertTrue(
            self.report["admission"][
                "state_unchanged_on_rejection"
            ]
        )

    def test_pre_admission_recoverable(self):
        self.assertTrue(
            self.report["admission"][
                "healthy_session_remained_usable"
            ]
        )

    def test_fresh_recovery(self):
        self.assertTrue(
            self.report["fresh_session_recovery_verified"]
        )

    def test_fresh_recovery_accuracy(self):
        self.assertLess(
            self.report["fresh_session_recovery"][
                "max_abs_error_vs_original_s6"
            ],1e-8
        )

    def test_healthy_s6_equivalence(self):
        for entry in self.report["healthy_cases"].values():
            bound=2e-5 if entry["recenter"] else 1e-8
            self.assertLess(
                entry["max_abs_error_vs_original_s6"],
                bound
            )

    def test_reorder_processing(self):
        for entry in self.report["healthy_cases"].values():
            self.assertEqual(
                entry["arrival_order"],
                [3,2,1,4]
            )

    def test_completing_session_closes_it(self):
        g=graph.build("clean",True,13)
        s=m.FailStopSession(g)

        for node in range(1,5):
            s.submit(delivery.make_packet(g,node))

        s.finish()

        self.assertEqual(s.state,"COMPLETED")

        with self.assertRaises(m.SessionError):
            s.submit(delivery.make_packet(g,4))

    def test_incomplete_finish_not_poisoned(self):
        g=graph.build("clean",True,13)
        s=m.FailStopSession(g)

        with self.assertRaises(m.SessionError):
            s.finish()

        self.assertEqual(s.state,"ACTIVE")
        self.assertIsNone(s.fault_receipt)

    def test_recorded_claim_rejected(self):
        g=graph.build("clean",True,13)
        s=m.FailStopSession(g)

        p=delivery.make_packet(g,1)

        bad=replace(
            p,real_sensor_factors_authorized=True
        )

        before=m.snapshot(s._buffer)

        with self.assertRaises(m.SessionError):
            s.submit(bad)

        self.assertEqual(
            before,m.snapshot(s._buffer)
        )
        self.assertEqual(s.state,"ACTIVE")

    def test_fault_case_reproducibility(self):
        a=m.fault_case("nonlinear_optimization")
        b=m.fault_case("nonlinear_optimization")

        self.assertEqual(m.canonical(a),m.canonical(b))

    def test_determinism(self):
        self.assertEqual(
            m.canonical(self.report),
            m.canonical(m.execute())
        )

    def test_no_real_streaming(self):
        self.assertFalse(
            self.report["hardware_fault_recovery_verified"]
        )

    def test_no_transactional_rollback(self):
        self.assertFalse(
            self.report[
                "new_transactional_rollback_implemented"
            ]
        )

    def test_no_r95_import(self):
        self.assertFalse(
            self.report["r95_gaussian_prior_imported"]
        )

    def test_no_real_factor_execution(self):
        self.assertFalse(
            self.report["real_sensor_factors_authorized"]
        )

    def test_no_health_training(self):
        self.assertFalse(
            self.report["health_training_authorized"]
        )

    def test_no_ate_rpe(self):
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

if __name__=="__main__":
    unittest.main(verbosity=2)
