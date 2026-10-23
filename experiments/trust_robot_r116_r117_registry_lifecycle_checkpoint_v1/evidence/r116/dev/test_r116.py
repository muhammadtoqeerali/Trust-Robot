import unittest

import r104_shared_graph as graph
import r108_delivery as delivery
import r116_lifecycle as m

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
            "PASS_SYNTHETIC_SESSION_LIFECYCLE_SOFTWARE_ONLY"
        )

    def test_twelve_interleaved_sessions(self):
        self.assertEqual(
            self.report["healthy_sessions"],12
        )

    def test_sixty_operations(self):
        self.assertEqual(
            self.report["healthy_committed_operations"],60
        )

    def test_168_replay_units(self):
        self.assertEqual(
            self.report["healthy_replay_work_units"],168
        )

    def test_all_twelve_rows(self):
        self.assertEqual(
            len(self.report["interleaved_sessions"]["runs"]),
            12
        )

    def test_healthy_acknowledgements(self):
        for row in self.report[
            "interleaved_sessions"
        ]["runs"].values():
            self.assertEqual(
                row["acknowledged_operations"],5
            )

    def test_healthy_attempt_charges(self):
        for row in self.report[
            "interleaved_sessions"
        ]["runs"].values():
            self.assertEqual(
                row["attempted_work_units"],14
            )

    def test_healthy_committed_charges(self):
        for row in self.report[
            "interleaved_sessions"
        ]["runs"].values():
            self.assertEqual(
                row["committed_work_units"],14
            )

    def test_healthy_windows(self):
        for row in self.report[
            "interleaved_sessions"
        ]["runs"].values():
            self.assertEqual(
                row["nonlinear_windows"],4
            )

    def test_healthy_marginalizations(self):
        for row in self.report[
            "interleaved_sessions"
        ]["runs"].values():
            self.assertEqual(
                row["schur_marginalizations"],3
            )

    def test_pose_ownership(self):
        for row in self.report[
            "interleaved_sessions"
        ]["runs"].values():
            self.assertTrue(
                row["factor_ownership_verified"]
            )

    def test_s6_reference_accuracy(self):
        for row in self.report[
            "interleaved_sessions"
        ]["runs"].values():
            bound=(
                2e-5 if row["recentered"]
                else 1e-8
            )
            self.assertLess(
                row["max_abs_error_vs_s6"],
                bound
            )

    def test_six_ordered_sessions(self):
        rows=self.report["interleaved_sessions"]["runs"]
        self.assertEqual(
            sum(
                row["arrival_order"]==[1,2,3,4]
                for row in rows.values()
            ),6
        )

    def test_six_reordered_sessions(self):
        rows=self.report["interleaved_sessions"]["runs"]
        self.assertEqual(
            sum(
                row["arrival_order"]==[3,2,1,4]
                for row in rows.values()
            ),6
        )

    def test_peak_active_two(self):
        self.assertEqual(
            self.report[
                "interleaved_sessions"
            ]["pool_audit"]["peak_active"],2
        )

    def test_interleaved_pool_drained(self):
        self.assertEqual(
            self.report[
                "interleaved_sessions"
            ]["pool_audit"]["active_count"],0
        )

    def test_all_interleaved_retired(self):
        self.assertEqual(
            self.report[
                "interleaved_sessions"
            ]["pool_audit"]["retired_count"],12
        )

    def test_active_capacity_denial(self):
        self.assertEqual(
            self.report[
                "capacity_and_retirement"
            ]["active_capacity_denials"],1
        )

    def test_creation_limit_denial(self):
        self.assertEqual(
            self.report[
                "capacity_and_retirement"
            ]["creation_limit_denials"],1
        )

    def test_unique_handles(self):
        self.assertEqual(
            self.report[
                "capacity_and_retirement"
            ]["unique_handles"],3
        )

    def test_reuse_of_retired_handles_denied(self):
        self.assertEqual(
            self.report[
                "capacity_and_retirement"
            ]["retired_handle_reuses_denied"],3
        )

    def test_capacity_pool_drained(self):
        self.assertEqual(
            self.report[
                "capacity_and_retirement"
            ]["active_after_retirement"],0
        )

    def test_three_injected_failures(self):
        self.assertEqual(
            self.report["fault_isolation"][
                "injected_failed_attempts"
            ],3
        )

    def test_three_failed_units_charged(self):
        self.assertEqual(
            self.report["fault_isolation"][
                "charged_failed_work_units"
            ],3
        )

    def test_cross_graph_packet_denied(self):
        self.assertEqual(
            self.report["fault_isolation"][
                "cross_graph_packet_rejections"
            ],1
        )

    def test_fourth_attempt_exhausted(self):
        self.assertTrue(
            self.report["fault_isolation"][
                "exhausted_fourth_attempt_rejected"
            ]
        )

    def test_healthy_session_survived_failure(self):
        self.assertTrue(
            self.report["fault_isolation"][
                "unrelated_session_completed"
            ]
        )

    def test_unrelated_session_reference_accuracy(self):
        self.assertLess(
            self.report["fault_isolation"][
                "unrelated_max_abs_error_vs_s6"
            ],1e-8
        )

    def test_fault_pool_drained(self):
        self.assertEqual(
            self.report["fault_isolation"][
                "registry_active_after"
            ],0
        )

    def test_prepublication_attempt_charged(self):
        self.assertEqual(
            self.report[
                "prepublication_retirement"
            ]["attempted_work_units_charged"],1
        )

    def test_prepublication_not_committed(self):
        self.assertEqual(
            self.report[
                "prepublication_retirement"
            ]["committed_work_units"],0
        )

    def test_prepublication_no_ack(self):
        self.assertFalse(
            self.report[
                "prepublication_retirement"
            ]["candidate_acknowledged"]
        )

    def test_prepublication_cancelled_retired(self):
        self.assertTrue(
            self.report[
                "prepublication_retirement"
            ]["cancelled_session_retired"]
        )

    def test_prepublication_no_reuse(self):
        self.assertTrue(
            self.report[
                "prepublication_retirement"
            ]["retired_handle_reuse_rejected"]
        )

    def test_ten_invalid_event_patterns(self):
        self.assertEqual(
            self.report[
                "admission_fault_patterns"
            ]["rejected_count"],10
        )

    def test_invalid_events_not_charged(self):
        self.assertEqual(
            self.report[
                "admission_fault_patterns"
            ]["attempted_work_charged_for_invalid_operations"],0
        )

    def test_invalid_event_recovery(self):
        self.assertTrue(
            self.report[
                "admission_fault_patterns"
            ]["eventual_successful_completion"]
        )

    def test_capacity_count(self):
        self.assertEqual(
            self.report["capacity_rejections"],2
        )

    def test_registration_bounds(self):
        self.assertTrue(
            self.report[
                "bounded_registry_capacity_verified"
            ]
        )

    def test_wrong_active_bound(self):
        with self.assertRaises(m.LifecycleError):
            m.SessionPool(max_active=3)

    def test_wrong_created_bound(self):
        with self.assertRaises(m.LifecycleError):
            m.SessionPool(
                max_active=2,
                max_created=13
            )

    def test_boolean_active_limit_denied(self):
        with self.assertRaises(m.LifecycleError):
            m.SessionPool(max_active=True)

    def test_nonterminal_retirement_denied(self):
        g=graph.build("clean",True,13)
        p=m.SessionPool(
            max_active=1,
            max_created=1
        )
        h,o=p.open(g)

        before=p.audit()

        with self.assertRaises(m.LifecycleError):
            p.retire(h,o)

        self.assertEqual(p.audit(),before)

        p.cancel(h,o,version=0)
        p.retire(h,o)

    def test_unknown_handle_denied(self):
        g=graph.build("clean",True,13)
        p=m.SessionPool(
            max_active=1,
            max_created=1
        )
        h,o=p.open(g)

        with self.assertRaises(m.LifecycleError):
            p.summary("S9999",o)

        p.cancel(h,o,version=0)
        p.retire(h,o)

    def test_owner_identity_denied(self):
        g=graph.build("clean",True,13)
        p=m.SessionPool(
            max_active=1,
            max_created=1
        )
        h,o=p.open(g)
        before=p.audit()

        with self.assertRaises(m.LifecycleError):
            p.summary(h,object())

        self.assertEqual(before,p.audit())

        p.cancel(h,o,version=0)
        p.retire(h,o)

    def test_stale_version_denied(self):
        g=graph.build("clean",True,13)
        p=m.SessionPool(
            max_active=1,
            max_created=1
        )
        h,o=p.open(g)

        before=p.summary(h,o)

        with self.assertRaises(m.LifecycleError):
            p.submit(
                h,o,
                delivery.make_packet(g,1),
                version=1
            )

        self.assertEqual(
            before,p.summary(h,o)
        )

        p.cancel(h,o,version=0)
        p.retire(h,o)

    def test_no_concurrency_claim(self):
        self.assertFalse(
            self.report[
                "actual_concurrent_thread_safety_verified"
            ]
        )

    def test_no_physical_memory_claim(self):
        self.assertFalse(
            self.report[
                "physical_memory_reclamation_verified"
            ]
        )

    def test_no_durable_recovery_claim(self):
        self.assertFalse(
            self.report[
                "durable_registry_recovery_verified"
            ]
        )

    def test_no_authentication_claim(self):
        self.assertFalse(
            self.report[
                "cryptographic_owner_authentication_verified"
            ]
        )

    def test_no_hardware_streaming(self):
        self.assertFalse(
            self.report["hardware_streaming_verified"]
        )

    def test_no_r95_import(self):
        self.assertFalse(
            self.report["r95_backend_imported"]
        )

    def test_no_real_factors(self):
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

    def test_determinism(self):
        self.assertEqual(
            m.canonical(self.report),
            m.canonical(m.execute())
        )

if __name__=="__main__":
    unittest.main(verbosity=2)
