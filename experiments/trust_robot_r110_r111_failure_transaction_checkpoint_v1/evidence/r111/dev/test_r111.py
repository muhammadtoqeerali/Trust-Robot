import unittest
from unittest.mock import patch

import r104_shared_graph as graph
import r108_delivery as delivery
import r111_transaction as m

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
            "PASS_SYNTHETIC_SHADOW_TRANSACTION_ONLY"
        )

    def test_twelve_sessions(self):
        self.assertEqual(
            self.report["healthy_solver_sessions"],12
        )

    def test_sixty_commits(self):
        self.assertEqual(
            self.report["committed_operations"],60
        )

    def test_forty_eight_windows(self):
        self.assertEqual(
            self.report[
                "nonlinear_windows_in_committed_sessions"
            ],48
        )

    def test_thirty_six_schur(self):
        self.assertEqual(
            self.report[
                "schur_events_in_committed_sessions"
            ],36
        )

    def test_eighteen_transfers(self):
        self.assertEqual(
            self.report["same_graph_prior_transfers"],18
        )

    def test_six_injections(self):
        self.assertEqual(
            set(self.report["fault_cases"]),
            set(m.FAULTS)
        )

    def test_six_snapshots_preserved(self):
        self.assertEqual(
            self.report[
                "unchanged_committed_snapshots_after_fault"
            ],6
        )

    def test_six_retries(self):
        self.assertEqual(
            self.report["successful_retries"],6
        )

    def test_eight_admission_rejections(self):
        self.assertEqual(
            self.report["invalid_admission"]["rejections"],8
        )

    def test_prediction_injection(self):
        self.assertTrue(
            self.report["fault_cases"][
                "imu_prediction"
            ]["failed_shadow_discarded"]
        )

    def test_optimizer_injection(self):
        self.assertTrue(
            self.report["fault_cases"][
                "nonlinear_optimization"
            ]["committed_snapshot_unchanged"]
        )

    def test_schur_injection(self):
        self.assertTrue(
            self.report["fault_cases"][
                "schur_marginalization"
            ]["retry_after_injection_removed"]
        )

    def test_recenter_injection(self):
        self.assertTrue(
            self.report["fault_cases"][
                "prior_recentering"
            ]["retry_after_injection_removed"]
        )

    def test_pre_publication_injection(self):
        self.assertTrue(
            self.report["fault_cases"][
                "pre_publication"
            ]["no_ack_on_failed_operation"]
        )

    def test_finalization_injection(self):
        self.assertTrue(
            self.report["fault_cases"][
                "finalization"
            ]["committed_object_identity_unchanged"]
        )

    def test_no_ack_on_failure(self):
        for c in self.report["fault_cases"].values():
            self.assertTrue(
                c["no_ack_on_failed_operation"]
            )

    def test_recovery_after_each_fault(self):
        for c in self.report["fault_cases"].values():
            self.assertTrue(
                c["session_recovered_without_reusing_failed_shadow"]
            )

    def test_all_commit_versions(self):
        for c in self.report["healthy_cases"].values():
            self.assertEqual(
                c["acknowledged_operations"],5
            )

    def test_all_pose_ownership(self):
        for c in self.report["healthy_cases"].values():
            self.assertTrue(
                c["factor_ownership_verified"]
            )

    def test_all_reference_accuracy(self):
        for c in self.report["healthy_cases"].values():
            threshold=2e-5 if c["recentered"] else 1e-8
            self.assertLess(
                c["max_abs_error_vs_s6"],threshold
            )

    def test_reordered_delivery(self):
        names=[
            v for v in self.report["healthy_cases"].values()
            if v["arrival_order"]==[3,2,1,4]
        ]
        self.assertEqual(len(names),6)

    def test_ordered_delivery(self):
        names=[
            v for v in self.report["healthy_cases"].values()
            if v["arrival_order"]==[1,2,3,4]
        ]
        self.assertEqual(len(names),6)

    def test_no_physical_data(self):
        self.assertFalse(
            self.report["real_sensor_factors_authorized"]
        )

    def test_no_health(self):
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

    def test_no_durable_claim(self):
        self.assertFalse(
            self.report["durable_crash_recovery_verified"]
        )

    def test_no_distributed_exactly_once(self):
        self.assertFalse(
            self.report["distributed_exactly_once_verified"]
        )

    def test_no_concurrency_claim(self):
        self.assertFalse(
            self.report[
                "concurrent_atomic_publication_verified"
            ]
        )

    def test_no_private_object_isolation(self):
        self.assertFalse(
            self.report[
                "direct_private_object_mutation_isolated"
            ]
        )

    def test_no_r95_import(self):
        self.assertFalse(
            self.report["r95_backend_imported"]
        )

    def test_scientific_gates(self):
        self.assertEqual(
            self.report["scientific_gates_closed"],11
        )

    def test_initial_transaction_version(self):
        g=graph.build("clean",True,13)
        session=m.TransactionalSession(g)

        self.assertEqual(session.version,0)
        self.assertEqual(session.phase,"ACTIVE")

    def test_success_ack(self):
        g=graph.build("clean",True,13)
        session=m.TransactionalSession(g)

        ack=session.submit(
            delivery.make_packet(g,1)
        )

        self.assertEqual(ack["sequence"],1)
        self.assertTrue(ack["acknowledged"])
        self.assertEqual(session.version,1)

    def test_rejected_delivery_keeps_snapshot(self):
        g=graph.build("clean",True,13)
        session=m.TransactionalSession(g)

        before=session.digest()

        with self.assertRaises(m.TransactionError):
            session.submit(
                delivery.make_packet(g,4)
            )

        self.assertEqual(session.digest(),before)

    def test_incomplete_finish_preserves_session(self):
        g=graph.build("clean",True,13)
        session=m.TransactionalSession(g)

        before=session.digest()

        with self.assertRaises(m.TransactionError):
            session.finish()

        self.assertEqual(session.digest(),before)
        self.assertEqual(session.phase,"ACTIVE")

    def test_completed_session_rejects_reuse(self):
        g=graph.build("clean",True,13)
        session=m.TransactionalSession(g)

        for node in range(1,5):
            session.submit(delivery.make_packet(g,node))

        session.finish()

        self.assertEqual(session.phase,"COMPLETED")

        with self.assertRaises(m.TransactionError):
            session.submit(delivery.make_packet(g,4))

    def test_prepublication_fault_keeps_identity(self):
        g=graph.build("clean",True,13)
        session=m.TransactionalSession(g)

        original=session._committed
        before=session.digest()

        with patch.object(
            session,
            "_before_publish",
            side_effect=m.InjectedFault("TEST")
        ):
            with self.assertRaises(m.TransactionError):
                session.submit(
                    delivery.make_packet(g,1)
                )

        self.assertIs(session._committed,original)
        self.assertEqual(session.digest(),before)
        self.assertEqual(session.version,0)

        session.submit(delivery.make_packet(g,1))
        self.assertEqual(session.version,1)

    def test_snapshot_digest_stable(self):
        g=graph.build("clean",True,13)
        session=m.TransactionalSession(g)

        self.assertEqual(
            session.digest(),
            session.digest()
        )

    def test_receipt_is_not_authentication(self):
        self.assertFalse(
            self.report[
                "transport_authentication_verified"
            ]
        )

    def test_no_rollback_claim_for_r108(self):
        self.assertFalse(
            self.report[
                "existing_r108_rollback_implemented"
            ]
        )

if __name__=="__main__":
    unittest.main(verbosity=2)
