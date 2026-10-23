import unittest

import r104_shared_graph as graph
import r122_terminal as m

class Tests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.report=m.execute()

    def test_schema(self):
        self.assertEqual(self.report["schema"],m.SCHEMA)

    def test_status(self):
        self.assertEqual(
            self.report["status"],
            "PASS_SYNTHETIC_POST_SATURATION_TERMINAL_ONLY"
        )

    def test_six_healthy_baseline_cases(self):
        self.assertEqual(
            self.report["healthy_baseline_sessions"],6
        )

    def test_healthy_baseline_acknowledgements(self):
        self.assertEqual(
            self.report["healthy_baseline_acknowledgements"],30
        )

    def test_healthy_baseline_work(self):
        self.assertEqual(
            self.report["healthy_baseline_work_units"],84
        )

    def test_healthy_baseline_windows(self):
        self.assertEqual(
            self.report["healthy_baseline"]["nonlinear_windows"],24
        )

    def test_healthy_baseline_schur(self):
        self.assertEqual(
            self.report["healthy_baseline"]["schur_events"],18
        )

    def test_healthy_baseline_transfers(self):
        self.assertEqual(
            self.report["healthy_baseline"]["prior_transfers"],9
        )

    def test_healthy_baseline_s6_accuracy(self):
        for row in self.report["healthy_baseline"]["runs"].values():
            threshold=2e-5 if row["recentered"] else 1e-8
            self.assertLess(
                row["max_abs_error_vs_s6"],threshold
            )

    def test_saturated_denial_capacity(self):
        self.assertEqual(
            self.report["saturated_rescue"]["denial_capacity"],3
        )

    def test_four_ordinary_operations_blocked(self):
        self.assertEqual(
            self.report["saturated_rescue"][
                "ordinary_mutations_blocked"
            ],4
        )

    def test_saturated_terminal_events(self):
        self.assertEqual(
            self.report["saturated_rescue"]["terminal_events"],2
        )

    def test_saturated_session_retired(self):
        self.assertTrue(
            self.report["saturated_rescue"]["session_retired"]
        )

    def test_saturated_pool_drained(self):
        self.assertEqual(
            self.report["saturated_rescue"]["active_after"],0
        )

    def test_saturated_committed_state_preserved(self):
        self.assertTrue(
            self.report["saturated_rescue"][
                "committed_state_preserved"
            ]
        )

    def test_saturated_denial_history_unchanged(self):
        self.assertTrue(
            self.report["saturated_rescue"][
                "denial_history_unchanged"
            ]
        )

    def test_retired_handle_reuse_denied(self):
        self.assertTrue(
            self.report["saturated_rescue"][
                "retired_handle_reuse_denied"
            ]
        )

    def test_partial_packets(self):
        self.assertEqual(
            self.report["partial_commit_rescue"][
                "accepted_packets_before_saturation"
            ],2
        )

    def test_partial_committed_work(self):
        self.assertEqual(
            self.report["partial_commit_rescue"][
                "committed_work_units_preserved"
            ],3
        )

    def test_partial_attempted_work(self):
        self.assertEqual(
            self.report["partial_commit_rescue"][
                "attempted_work_units_preserved"
            ],3
        )

    def test_partial_session_retired(self):
        self.assertTrue(
            self.report["partial_commit_rescue"]["session_retired"]
        )

    def test_partial_no_new_execution(self):
        self.assertTrue(
            self.report["partial_commit_rescue"][
                "no_additional_estimator_execution"
            ]
        )

    def test_four_invalid_terminal_attempts(self):
        self.assertEqual(
            self.report["ordering_and_owner_guards"][
                "wrong_owner_version_or_handle_denials"
            ],4
        )

    def test_out_of_order_retirement_denied(self):
        self.assertEqual(
            self.report["ordering_and_owner_guards"][
                "out_of_order_retirements_denied"
            ],1
        )

    def test_order_recovery(self):
        self.assertTrue(
            self.report["ordering_and_owner_guards"][
                "registry_drained"
            ]
        )

    def test_order_terminal_events(self):
        self.assertEqual(
            self.report["ordering_and_owner_guards"][
                "terminal_events"
            ],4
        )

    def test_invalid_terminal_did_not_mutate(self):
        self.assertTrue(
            self.report["ordering_and_owner_guards"][
                "failed_admissions_preserved_state"
            ]
        )

    def test_three_fault_attempts(self):
        self.assertEqual(
            self.report["saturated_fault_rescue"][
                "failed_candidate_attempts"
            ],3
        )

    def test_three_fault_units_charged(self):
        self.assertEqual(
            self.report["saturated_fault_rescue"][
                "failed_work_units_charged"
            ],3
        )

    def test_peer_execution_blocked(self):
        self.assertTrue(
            self.report["saturated_fault_rescue"][
                "ordinary_peer_execution_blocked"
            ]
        )

    def test_faulted_session_terminal(self):
        self.assertTrue(
            self.report["saturated_fault_rescue"][
                "failed_session_terminal"
            ]
        )

    def test_peer_session_terminal(self):
        self.assertTrue(
            self.report["saturated_fault_rescue"][
                "peer_session_terminal"
            ]
        )

    def test_both_fault_sessions_retired(self):
        self.assertEqual(
            self.report["saturated_fault_rescue"][
                "sessions_retired"
            ],2
        )

    def test_no_peer_liveness_claim(self):
        self.assertTrue(
            self.report["saturated_fault_rescue"][
                "no_peer_progress_claim_after_saturation"
            ]
        )

    def test_prepublication_abort_receipt(self):
        self.assertEqual(
            self.report["prepublication_terminal_path"][
                "aborted_candidate_receipts"
            ],1
        )

    def test_prepublication_work_charged(self):
        self.assertEqual(
            self.report["prepublication_terminal_path"][
                "charged_failed_units"
            ],1
        )

    def test_prepublication_no_committed_work(self):
        self.assertEqual(
            self.report["prepublication_terminal_path"][
                "committed_work_units"
            ],0
        )

    def test_prepublication_no_acknowledgement(self):
        self.assertFalse(
            self.report["prepublication_terminal_path"][
                "candidate_acknowledged"
            ]
        )

    def test_prepublication_retired(self):
        self.assertTrue(
            self.report["prepublication_terminal_path"][
                "retired"
            ]
        )

    def test_twelve_terminal_capacity_sessions(self):
        self.assertEqual(
            self.report["full_terminal_capacity"][
                "created_sessions"
            ],12
        )

    def test_twelve_capacity_retirements(self):
        self.assertEqual(
            self.report["full_terminal_capacity"][
                "retired_sessions"
            ],12
        )

    def test_twenty_four_terminal_receipts(self):
        self.assertEqual(
            self.report["full_terminal_capacity"][
                "bounded_terminal_receipts"
            ],24
        )

    def test_terminal_capacity_limit(self):
        self.assertEqual(
            self.report["full_terminal_capacity"][
                "terminal_capacity"
            ],24
        )

    def test_capacity_creation_rejection(self):
        self.assertTrue(
            self.report["full_terminal_capacity"][
                "creation_limit_rejected"
            ]
        )

    def test_full_capacity_registry_drained(self):
        self.assertTrue(
            self.report["full_terminal_capacity"][
                "registry_drained"
            ]
        )

    def test_terminal_internal_tamper(self):
        self.assertTrue(
            self.report["receipt_integrity"][
                "internal_tamper_rejected"
            ]
        )

    def test_terminal_detached_copy(self):
        self.assertTrue(
            self.report["receipt_integrity"][
                "detached_copy_verified"
            ]
        )

    def test_recovered_after_tamper_restore(self):
        self.assertTrue(
            self.report["receipt_integrity"][
                "recovered_after_restoration"
            ]
        )

    def test_terminal_retired_after_tamper(self):
        self.assertTrue(
            self.report["receipt_integrity"][
                "retired_after_control"
            ]
        )

    def test_initial_terminal_observation(self):
        f=m.TerminalPath(max_active=1,max_created=1)
        v=f.inspect_terminal()
        self.assertEqual(v["terminal"]["receipt_count"],0)

    def test_terminal_owner_guard(self):
        g=graph.build("clean",True,13)
        f=m.TerminalPath(max_active=1,max_created=1)
        lease,owner=f.open(g)

        with self.assertRaises(m.TerminalPathError):
            f.terminal_cancel(lease,object(),version=0)

        f.terminal_cancel(lease,owner,version=0)
        f.terminal_retire(lease,owner)

    def test_terminal_stale_version_guard(self):
        g=graph.build("clean",True,13)
        f=m.TerminalPath(max_active=1,max_created=1)
        lease,owner=f.open(g)

        with self.assertRaises(m.TerminalPathError):
            f.terminal_cancel(lease,owner,version=1)

        f.terminal_cancel(lease,owner,version=0)
        f.terminal_retire(lease,owner)

    def test_terminal_boolean_version_denied(self):
        g=graph.build("clean",True,13)
        f=m.TerminalPath(max_active=1,max_created=1)
        lease,owner=f.open(g)

        with self.assertRaises(m.TerminalPathError):
            f.terminal_cancel(lease,owner,version=True)

        f.terminal_cancel(lease,owner,version=0)
        f.terminal_retire(lease,owner)

    def test_terminal_retire_requires_cancellation(self):
        g=graph.build("clean",True,13)
        f=m.TerminalPath(max_active=1,max_created=1)
        lease,owner=f.open(g)

        with self.assertRaises(m.TerminalPathError):
            f.terminal_retire(lease,owner)

        f.terminal_cancel(lease,owner,version=0)
        f.terminal_retire(lease,owner)

    def test_duplicate_terminal_cancel_denied(self):
        g=graph.build("clean",True,13)
        f=m.TerminalPath(max_active=1,max_created=1)
        lease,owner=f.open(g)

        f.terminal_cancel(lease,owner,version=0)

        with self.assertRaises(m.TerminalPathError):
            f.terminal_cancel(lease,owner,version=0)

        f.terminal_retire(lease,owner)

    def test_retired_terminal_handle_denied(self):
        g=graph.build("clean",True,13)
        f=m.TerminalPath(max_active=1,max_created=1)
        lease,owner=f.open(g)

        f.terminal_cancel(lease,owner,version=0)
        f.terminal_retire(lease,owner)

        with self.assertRaises(m.TerminalPathError):
            f.terminal_retire(lease,owner)

    def test_no_hardware_emergency_stop_claim(self):
        self.assertFalse(
            self.report["hardware_emergency_stop_verified"]
        )

    def test_no_process_failure_recovery_claim(self):
        self.assertFalse(
            self.report["process_failure_recovery_verified"]
        )

    def test_no_arbitrary_exception_atomicity_claim(self):
        self.assertFalse(
            self.report["arbitrary_exception_atomicity_verified"]
        )

    def test_no_unconditional_termination_claim(self):
        self.assertFalse(
            self.report["unconditional_termination_guaranteed"]
        )

    def test_no_concurrent_thread_claim(self):
        self.assertFalse(
            self.report["actual_concurrent_thread_safety_verified"]
        )

    def test_no_durable_log_claim(self):
        self.assertFalse(
            self.report["durable_logging_verified"]
        )

    def test_no_authenticated_log_claim(self):
        self.assertFalse(
            self.report["authenticated_logging_verified"]
        )

    def test_no_physical_ram_claim(self):
        self.assertFalse(
            self.report["physical_memory_reclamation_verified"]
        )

    def test_no_real_time_claim(self):
        self.assertFalse(
            self.report["real_time_deadline_verified"]
        )

    def test_no_r95_prior_import(self):
        self.assertFalse(
            self.report["r95_backend_imported"]
        )

    def test_no_real_sensor_factors(self):
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

    def test_serialization(self):
        self.assertEqual(
            m.canonical(self.report),
            m.canonical(self.report)
        )

if __name__=="__main__":
    unittest.main(verbosity=2)
