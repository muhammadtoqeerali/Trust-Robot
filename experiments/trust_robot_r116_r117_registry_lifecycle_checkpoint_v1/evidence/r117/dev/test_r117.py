import unittest

import r104_shared_graph as graph
import r108_delivery as delivery
import r117_registry as m

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
            "PASS_SYNTHETIC_REGISTRY_HARDENING_SOFTWARE_ONLY"
        )

    def test_healthy_sessions(self):
        self.assertEqual(
            self.report["healthy_sessions"],12
        )

    def test_sixty_acks(self):
        self.assertEqual(
            self.report["acknowledged_operations"],60
        )

    def test_168_units(self):
        self.assertEqual(
            self.report["healthy_attempted_work_units"],168
        )

    def test_twelve_retirements(self):
        self.assertEqual(
            self.report["healthy_retirement_receipts"],12
        )

    def test_healthy_rows(self):
        self.assertEqual(
            len(self.report["healthy_interleaving"]["runs"]),
            12
        )

    def test_healthy_versions(self):
        for row in self.report[
            "healthy_interleaving"
        ]["runs"].values():
            self.assertEqual(
                row["acknowledged_operations"],5
            )

    def test_healthy_attempts(self):
        for row in self.report[
            "healthy_interleaving"
        ]["runs"].values():
            self.assertEqual(
                row["attempted_work_units"],14
            )

    def test_healthy_commits(self):
        for row in self.report[
            "healthy_interleaving"
        ]["runs"].values():
            self.assertEqual(
                row["committed_work_units"],14
            )

    def test_healthy_windows(self):
        for row in self.report[
            "healthy_interleaving"
        ]["runs"].values():
            self.assertEqual(
                row["nonlinear_windows"],4
            )

    def test_healthy_schur(self):
        for row in self.report[
            "healthy_interleaving"
        ]["runs"].values():
            self.assertEqual(
                row["schur_events"],3
            )

    def test_healthy_equivalence(self):
        for row in self.report[
            "healthy_interleaving"
        ]["runs"].values():
            threshold=(
                2e-5 if row["recentered"]
                else 1e-8
            )
            self.assertLess(
                row["max_abs_error_vs_s6"],
                threshold
            )

    def test_six_ordered(self):
        rows=self.report[
            "healthy_interleaving"
        ]["runs"].values()

        self.assertEqual(
            sum(
                x["arrival_order"]==[1,2,3,4]
                for x in rows
            ),6
        )

    def test_six_reordered(self):
        rows=self.report[
            "healthy_interleaving"
        ]["runs"].values()

        self.assertEqual(
            sum(
                x["arrival_order"]==[3,2,1,4]
                for x in rows
            ),6
        )

    def test_pool_drained(self):
        self.assertEqual(
            self.report["healthy_interleaving"][
                "registry_audit"
            ]["active_count"],0
        )

    def test_pool_peak(self):
        self.assertEqual(
            self.report["healthy_interleaving"][
                "registry_audit"
            ]["peak_active"],2
        )

    def test_retirement_tip(self):
        self.assertNotEqual(
            self.report["healthy_interleaving"][
                "registry_audit"
            ]["retirement_chain_sha256"],
            m.GENESIS
        )

    def test_active_capacity(self):
        self.assertEqual(
            self.report["capacity_and_stale_handles"][
                "active_capacity_rejections"
            ],1
        )

    def test_creation_capacity(self):
        self.assertEqual(
            self.report["capacity_and_stale_handles"][
                "creation_limit_rejections"
            ],1
        )

    def test_stale_handle_rejection(self):
        self.assertEqual(
            self.report["capacity_and_stale_handles"][
                "stale_handle_rejections"
            ],1
        )

    def test_no_opaque_handle_reuse(self):
        self.assertFalse(
            self.report["capacity_and_stale_handles"][
                "opaque_handle_reuse"
            ]
        )

    def test_capacity_registry_drained(self):
        self.assertTrue(
            self.report["capacity_and_stale_handles"][
                "registry_drained"
            ]
        )

    def test_cross_registry_rejections(self):
        self.assertEqual(
            self.report["cross_registry_admissions"][
                "rejection_count"
            ],6
        )

    def test_cross_registry_handle_denial(self):
        self.assertTrue(
            self.report["cross_registry_admissions"][
                "cross_registry_handle_reuse_denied"
            ]
        )

    def test_cross_registry_eventual_success(self):
        self.assertTrue(
            self.report["cross_registry_admissions"][
                "both_registries_completed"
            ]
        )

    def test_cross_registry_no_charge(self):
        self.assertTrue(
            self.report["cross_registry_admissions"][
                "zero_work_charged_for_invalid_admissions"
            ]
        )

    def test_ledger_tamper_rejected(self):
        self.assertTrue(
            self.report["ledger_corruption_controls"][
                "linked_ledger_tamper_rejected"
            ]
        )

    def test_receipt_tamper_rejected(self):
        self.assertTrue(
            self.report["ledger_corruption_controls"][
                "underlying_receipt_tamper_rejected"
            ]
        )

    def test_two_corruption_controls(self):
        self.assertEqual(
            self.report["corruption_controls_rejected"],2
        )

    def test_recovery_after_tamper_restored(self):
        self.assertTrue(
            self.report["ledger_corruption_controls"][
                "subsequent_healthy_registry_operation"
            ]
        )

    def test_three_faults_charged(self):
        self.assertEqual(
            self.report["charged_failed_attempts"],3
        )

    def test_fourth_fault_denied(self):
        self.assertTrue(
            self.report["failure_exhaustion_isolation"][
                "fourth_attempt_rejected"
            ]
        )

    def test_healthy_peer_isolated(self):
        self.assertTrue(
            self.report["failure_exhaustion_isolation"][
                "healthy_peer_completed"
            ]
        )

    def test_healthy_peer_accuracy(self):
        self.assertLess(
            self.report["failure_exhaustion_isolation"][
                "healthy_peer_max_abs_error_vs_s6"
            ],1e-8
        )

    def test_fault_ledger_retirement(self):
        self.assertEqual(
            self.report["failure_exhaustion_isolation"][
                "retirement_chain_entries"
            ],2
        )

    def test_cancel_attempt_charged(self):
        self.assertEqual(
            self.report["prepublication_cancellation"][
                "failed_candidate_attempt_units"
            ],1
        )

    def test_cancel_no_commit(self):
        self.assertEqual(
            self.report["prepublication_cancellation"][
                "committed_work_units"
            ],0
        )

    def test_cancel_no_ack(self):
        self.assertFalse(
            self.report["prepublication_cancellation"][
                "candidate_acknowledged"
            ]
        )

    def test_cancel_state_preserved(self):
        self.assertTrue(
            self.report["prepublication_cancellation"][
                "committed_estimator_unchanged"
            ]
        )

    def test_cancel_retired(self):
        self.assertTrue(
            self.report["prepublication_cancellation"][
                "cancelled_and_retired"
            ]
        )

    def test_initial_registry(self):
        r=m.GuardedRegistry(
            max_active=1,max_created=1
        )
        self.assertEqual(r.audit()["created"],0)
        self.assertEqual(r.audit()["active_count"],0)

    def test_new_handle_is_opaque_object(self):
        g=graph.build("clean",True,13)
        r=m.GuardedRegistry(
            max_active=1,max_created=1
        )
        lease,owner=r.open(g)
        self.assertIs(type(lease),object)
        r.cancel(lease,owner,version=0)
        r.retire(lease,owner)

    def test_string_handle_denied(self):
        g=graph.build("clean",True,13)
        r=m.GuardedRegistry(
            max_active=1,max_created=1
        )
        lease,owner=r.open(g)

        with self.assertRaises(m.RegistryError):
            r.summary("S0001",owner)

        r.cancel(lease,owner,version=0)
        r.retire(lease,owner)

    def test_wrong_owner_denied(self):
        g=graph.build("clean",True,13)
        r=m.GuardedRegistry(
            max_active=1,max_created=1
        )
        lease,owner=r.open(g)

        with self.assertRaises(m.RegistryError):
            r.summary(lease,object())

        r.cancel(lease,owner,version=0)
        r.retire(lease,owner)

    def test_stale_version_denied(self):
        g=graph.build("clean",True,13)
        r=m.GuardedRegistry(
            max_active=1,max_created=1
        )
        lease,owner=r.open(g)

        before=r.summary(lease,owner)

        with self.assertRaises(m.RegistryError):
            r.submit(
                lease,owner,
                delivery.make_packet(g,1),
                version=1
            )

        self.assertEqual(
            before,r.summary(lease,owner)
        )

        r.cancel(lease,owner,version=0)
        r.retire(lease,owner)

    def test_nonterminal_retirement_denied(self):
        g=graph.build("clean",True,13)
        r=m.GuardedRegistry(
            max_active=1,max_created=1
        )
        lease,owner=r.open(g)

        with self.assertRaises(m.RegistryError):
            r.retire(lease,owner)

        r.cancel(lease,owner,version=0)
        r.retire(lease,owner)

    def test_retired_handle_denied(self):
        g=graph.build("clean",True,13)
        r=m.GuardedRegistry(
            max_active=1,max_created=1
        )
        lease,owner=r.open(g)

        r.cancel(lease,owner,version=0)
        r.retire(lease,owner)

        with self.assertRaises(m.RegistryError):
            r.summary(lease,owner)

    def test_bad_active_limit(self):
        with self.assertRaises(ValueError):
            m.GuardedRegistry(max_active=3)

    def test_bad_created_limit(self):
        with self.assertRaises(ValueError):
            m.GuardedRegistry(
                max_active=2,max_created=13
            )

    def test_no_authenticated_log_claim(self):
        self.assertFalse(
            self.report[
                "authenticated_audit_log_verified"
            ]
        )

    def test_no_durable_ledger_claim(self):
        self.assertFalse(
            self.report[
                "durable_audit_log_verified"
            ]
        )

    def test_no_memory_reclamation_claim(self):
        self.assertFalse(
            self.report[
                "physical_memory_reclamation_verified"
            ]
        )

    def test_no_concurrency_claim(self):
        self.assertFalse(
            self.report[
                "actual_concurrent_thread_safety_verified"
            ]
        )

    def test_no_private_isolation_claim(self):
        self.assertFalse(
            self.report[
                "direct_private_object_mutation_isolated"
            ]
        )

    def test_no_hardware_streaming(self):
        self.assertFalse(
            self.report[
                "hardware_streaming_verified"
            ]
        )

    def test_no_r95_import(self):
        self.assertFalse(
            self.report[
                "r95_backend_imported"
            ]
        )

    def test_no_real_sensor_factors(self):
        self.assertFalse(
            self.report[
                "real_sensor_factors_authorized"
            ]
        )

    def test_no_health_or_ate(self):
        self.assertFalse(
            self.report[
                "health_training_authorized"
            ]
        )
        self.assertFalse(
            self.report[
                "ate_rpe_authorized"
            ]
        )

    def test_confirmation_sealed(self):
        self.assertFalse(
            self.report[
                "confirmation_test_accessed"
            ]
        )

    def test_scientific_gates(self):
        self.assertEqual(
            self.report["scientific_gates_closed"],
            11
        )

    def test_determinism(self):
        self.assertEqual(
            m.canonical(self.report),
            m.canonical(m.execute())
        )

if __name__=="__main__":
    unittest.main(verbosity=2)
