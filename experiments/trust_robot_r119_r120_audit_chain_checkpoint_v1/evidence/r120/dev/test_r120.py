import unittest

import r104_shared_graph as graph
import r108_delivery as delivery
import r120_audit_guard as m

class Tests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.report=m.execute()

    def test_schema(self):
        self.assertEqual(self.report["schema"],m.SCHEMA)

    def test_status(self):
        self.assertEqual(
            self.report["status"],
            "PASS_SYNTHETIC_AUDIT_CHAIN_GUARDS_ONLY"
        )

    def test_six_sessions(self):
        self.assertEqual(self.report["healthy_sessions"],6)

    def test_thirty_acknowledgements(self):
        self.assertEqual(self.report["healthy_acknowledgements"],30)

    def test_eighty_four_work_units(self):
        self.assertEqual(self.report["healthy_replay_work_units"],84)

    def test_six_healthy_rows(self):
        self.assertEqual(
            len(self.report["healthy_cases"]["runs"]),6
        )

    def test_healthy_window_total(self):
        self.assertEqual(
            self.report["healthy_cases"]["nonlinear_windows"],24
        )

    def test_healthy_schur_total(self):
        self.assertEqual(
            self.report["healthy_cases"]["schur_events"],18
        )

    def test_healthy_prior_transfers(self):
        self.assertEqual(
            self.report["healthy_cases"]["prior_transfers"],9
        )

    def test_healthy_ack_per_case(self):
        for row in self.report["healthy_cases"]["runs"].values():
            self.assertEqual(row["acknowledged_operations"],5)

    def test_healthy_replay_per_case(self):
        for row in self.report["healthy_cases"]["runs"].values():
            self.assertEqual(row["attempted_work_units"],14)

    def test_healthy_windows_per_case(self):
        for row in self.report["healthy_cases"]["runs"].values():
            self.assertEqual(row["nonlinear_windows"],4)

    def test_healthy_schur_per_case(self):
        for row in self.report["healthy_cases"]["runs"].values():
            self.assertEqual(row["schur_events"],3)

    def test_healthy_s6_equivalence(self):
        for row in self.report["healthy_cases"]["runs"].values():
            limit=2e-5 if row["recentered"] else 1e-8
            self.assertLess(row["max_abs_error_vs_s6"],limit)

    def test_all_retired(self):
        for row in self.report["healthy_cases"]["runs"].values():
            self.assertTrue(row["retired"])

    def test_detached_healthy_observation(self):
        self.assertTrue(
            self.report["healthy_cases"][
                "detached_observations_verified"
            ]
        )

    def test_no_credentials_in_healthy_observation(self):
        self.assertTrue(
            self.report["healthy_cases"][
                "credentials_excluded_from_observations"
            ]
        )

    def test_ten_admission_denials(self):
        self.assertEqual(self.report["admission_denials"],10)

    def test_admission_receipt_count(self):
        self.assertEqual(
            self.report["admission_receipts"]["denials"],10
        )

    def test_admission_zero_charge(self):
        self.assertEqual(
            self.report["admission_receipts"][
                "charged_attempt_units"
            ],0
        )

    def test_admission_unacknowledged(self):
        self.assertTrue(
            self.report["admission_receipts"][
                "all_denials_unacknowledged"
            ]
        )

    def test_admission_recovery(self):
        self.assertTrue(
            self.report["admission_receipts"][
                "eventual_healthy_completion"
            ]
        )

    def test_admission_s6_accuracy(self):
        self.assertLess(
            self.report["admission_receipts"][
                "max_abs_error_vs_s6"
            ],1e-8
        )

    def test_denial_copy_detached(self):
        self.assertTrue(
            self.report["admission_receipts"][
                "detached_denial_copy_verified"
            ]
        )

    def test_semantic_receipts(self):
        self.assertTrue(
            self.report["admission_receipts"][
                "semantic_denial_validation"
            ]
        )

    def test_three_aborted_candidates(self):
        self.assertEqual(
            self.report["charged_failed_candidates"],3
        )

    def test_four_failure_receipts(self):
        self.assertEqual(
            self.report["failed_candidate_receipts"][
                "denial_receipts"
            ],4
        )

    def test_failed_attempt_charge_ledger(self):
        self.assertEqual(
            self.report["failed_candidate_receipts"][
                "attempt_charge_ledger"
            ],[1,1,1,0]
        )

    def test_fourth_attempt_denied(self):
        self.assertTrue(
            self.report["failed_candidate_receipts"][
                "fourth_attempt_rejected_without_charge"
            ]
        )

    def test_aborted_candidate_preserves_committed(self):
        self.assertTrue(
            self.report["failed_candidate_receipts"][
                "committed_state_preserved"
            ]
        )

    def test_peer_completion(self):
        self.assertTrue(
            self.report["failed_candidate_receipts"][
                "healthy_peer_completed"
            ]
        )

    def test_peer_s6_accuracy(self):
        self.assertLess(
            self.report["failed_candidate_receipts"][
                "healthy_peer_error_vs_s6"
            ],1e-8
        )

    def test_failure_sessions_retired(self):
        self.assertEqual(
            self.report["failed_candidate_receipts"][
                "retired_sessions"
            ],2
        )

    def test_order_preflight_denial(self):
        self.assertEqual(
            self.report["retirement_order_guard"][
                "pre_mutation_order_rejections"
            ],1
        )

    def test_order_policy_receipt(self):
        self.assertEqual(
            self.report["retirement_order_guard"][
                "policy_receipts"
            ],1
        )

    def test_policy_tamper_rejected(self):
        self.assertEqual(
            self.report["retirement_order_guard"][
                "policy_tamper_controls"
            ],1
        )

    def test_order_rejection_unchanged(self):
        self.assertTrue(
            self.report["retirement_order_guard"][
                "committed_state_unchanged"
            ]
        )

    def test_ordered_retirement_recovery(self):
        self.assertTrue(
            self.report["retirement_order_guard"][
                "subsequent_ordered_retirement"
            ]
        )

    def test_order_registry_integrity(self):
        self.assertTrue(
            self.report["retirement_order_guard"][
                "registry_integrity_preserved"
            ]
        )

    def test_capacity_three_receipts(self):
        self.assertEqual(
            self.report["capacity_saturation"][
                "recorded_denials"
            ],3
        )

    def test_capacity_two_blocks(self):
        self.assertEqual(
            self.report["capacity_saturation"][
                "additional_operations_blocked"
            ],2
        )

    def test_capacity_no_extra_receipts(self):
        self.assertEqual(
            self.report["capacity_saturation"][
                "additional_individual_receipts"
            ],0
        )

    def test_capacity_read_only_remains(self):
        self.assertTrue(
            self.report["capacity_saturation"][
                "read_only_observations_available"
            ]
        )

    def test_capacity_strands_active_session(self):
        self.assertTrue(
            self.report["capacity_saturation"][
                "active_session_left_unretired"
            ]
        )

    def test_no_liveness_claim_after_saturation(self):
        self.assertFalse(
            self.report["capacity_saturation"][
                "liveness_guarantee_after_saturation"
            ]
        )

    def test_prepublication_one_charge(self):
        self.assertEqual(
            self.report["prepublication_abort"][
                "charged_attempt_units"
            ],1
        )

    def test_prepublication_zero_commit(self):
        self.assertEqual(
            self.report["prepublication_abort"][
                "committed_units"
            ],0
        )

    def test_prepublication_state_preserved(self):
        self.assertTrue(
            self.report["prepublication_abort"][
                "committed_state_preserved"
            ]
        )

    def test_prepublication_retired(self):
        self.assertTrue(
            self.report["prepublication_abort"][
                "retired_after_abort"
            ]
        )

    def test_linked_denial_tamper(self):
        self.assertTrue(
            self.report["denial_tamper_control"][
                "linked_denial_tamper_rejected"
            ]
        )

    def test_tamper_restored(self):
        self.assertTrue(
            self.report["denial_tamper_control"][
                "subsequent_operations_after_restore"
            ]
        )

    def test_initial_inspection(self):
        f=m.AuditGuard(max_active=1,max_created=1)
        self.assertEqual(f.inspect()["denials"]["receipt_count"],0)

    def test_invalid_capacity_bool(self):
        with self.assertRaises(m.AuditGuardError):
            m.AuditGuard(max_denials=True)

    def test_invalid_capacity_large(self):
        with self.assertRaises(m.AuditGuardError):
            m.AuditGuard(max_denials=17)

    def test_invalid_capacity_zero(self):
        with self.assertRaises(m.AuditGuardError):
            m.AuditGuard(max_denials=0)

    def test_normal_session_inspection(self):
        g=graph.build("clean",True,13)
        f=m.AuditGuard(max_active=1,max_created=1)
        lease,owner=f.open(g)
        self.assertEqual(f.observe_session(lease,owner)["version"],0)
        f.cancel(lease,owner,version=0)
        f.retire(lease,owner)

    def test_wrong_owner_observation_denied(self):
        g=graph.build("clean",True,13)
        f=m.AuditGuard(max_active=1,max_created=1)
        lease,owner=f.open(g)
        with self.assertRaises(m.observation.OperationDenied):
            f.observe_session(lease,object())
        f.cancel(lease,owner,version=0)
        f.retire(lease,owner)

    def test_no_authenticated_log_claim(self):
        self.assertFalse(
            self.report["authenticated_logging_verified"]
        )

    def test_no_durable_log_claim(self):
        self.assertFalse(
            self.report["durable_logging_verified"]
        )

    def test_no_external_anchor_claim(self):
        self.assertFalse(
            self.report["external_ledger_anchor_verified"]
        )

    def test_no_concurrent_thread_claim(self):
        self.assertFalse(
            self.report["concurrent_thread_safety_verified"]
        )

    def test_no_physical_memory_claim(self):
        self.assertFalse(
            self.report["physical_memory_reclamation_verified"]
        )

    def test_no_hardware_streaming(self):
        self.assertFalse(
            self.report["hardware_streaming_verified"]
        )

    def test_no_r95_prior_import(self):
        self.assertFalse(
            self.report["r95_backend_imported"]
        )

    def test_no_real_factors(self):
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
        self.assertEqual(self.report["scientific_gates_closed"],11)

    def test_report_serialization(self):
        self.assertEqual(
            m.canonical(self.report),
            m.canonical(self.report)
        )

if __name__=="__main__":
    unittest.main(verbosity=2)
