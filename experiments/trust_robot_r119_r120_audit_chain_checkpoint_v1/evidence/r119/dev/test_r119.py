import unittest

import r104_shared_graph as graph
import r108_delivery as delivery
import r119_observation as m

class Tests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.report=m.execute()

    def test_schema(self):
        self.assertEqual(self.report["schema"],m.SCHEMA)

    def test_status(self):
        self.assertEqual(
            self.report["status"],
            "PASS_SYNTHETIC_AUDIT_OBSERVATION_SOFTWARE_ONLY"
        )

    def test_twelve_healthy_sessions(self):
        self.assertEqual(self.report["healthy_sessions"],12)

    def test_sixty_acknowledgements(self):
        self.assertEqual(self.report["acknowledged_operations"],60)

    def test_168_replay_units(self):
        self.assertEqual(self.report["attempted_work_units"],168)

    def test_twelve_retirements(self):
        self.assertEqual(self.report["retirement_receipts"],12)

    def test_healthy_rows(self):
        self.assertEqual(
            len(self.report["healthy_observation"]["runs"]),
            12
        )

    def test_healthy_per_run_units(self):
        for row in self.report["healthy_observation"]["runs"].values():
            self.assertEqual(row["attempted_work_units"],14)

    def test_healthy_ack_count(self):
        for row in self.report["healthy_observation"]["runs"].values():
            self.assertEqual(row["acknowledged_operations"],5)

    def test_healthy_windows(self):
        for row in self.report["healthy_observation"]["runs"].values():
            self.assertEqual(row["nonlinear_windows"],4)

    def test_healthy_schur(self):
        for row in self.report["healthy_observation"]["runs"].values():
            self.assertEqual(row["schur_events"],3)

    def test_healthy_reference_equivalence(self):
        for row in self.report["healthy_observation"]["runs"].values():
            bound=2e-5 if row["recentered"] else 1e-8
            self.assertLess(row["max_abs_error_vs_s6"],bound)

    def test_healthy_retired(self):
        for row in self.report["healthy_observation"]["runs"].values():
            self.assertTrue(row["retired"])

    def test_healthy_no_denials(self):
        self.assertEqual(
            self.report["healthy_observation"]["denial_receipts"],0
        )

    def test_healthy_registry_drained(self):
        self.assertEqual(
            self.report["healthy_observation"]["active_after"],0
        )

    def test_observation_detached(self):
        self.assertTrue(
            self.report["healthy_observation"][
                "detached_retirement_copy_verified"
            ]
        )

    def test_retirement_chain_tip(self):
        self.assertNotEqual(
            self.report["healthy_observation"][
                "retirement_chain_tip"
            ],
            m.GENESIS
        )

    def test_ten_admission_denials(self):
        self.assertEqual(
            self.report["denied_admissions"]["denials"],10
        )

    def test_admission_no_charge(self):
        self.assertEqual(
            self.report["denied_admissions"][
                "invalid_admission_work_units"
            ],0
        )

    def test_admission_eventual_recovery(self):
        self.assertTrue(
            self.report["denied_admissions"][
                "successful_recovery"
            ]
        )

    def test_admission_reference_accuracy(self):
        self.assertLess(
            self.report["denied_admissions"][
                "max_abs_error_vs_s6"
            ],1e-8
        )

    def test_detached_denial_copy(self):
        self.assertTrue(
            self.report["denied_admissions"][
                "detached_failure_receipts_verified"
            ]
        )

    def test_denial_chain_verified(self):
        self.assertTrue(
            self.report["denied_admissions"][
                "linked_denial_chain_verified"
            ]
        )

    def test_four_fault_receipts(self):
        self.assertEqual(
            self.report["charged_failure_observation"][
                "failure_receipts"
            ],4
        )

    def test_three_aborted_candidates(self):
        self.assertEqual(
            self.report["charged_failure_observation"][
                "aborted_candidates"
            ],3
        )

    def test_fault_charge_ledger(self):
        self.assertEqual(
            self.report["charged_failure_observation"][
                "charged_attempt_ledger"
            ],
            [1,1,1,0]
        )

    def test_exhausted_attempt_denied(self):
        self.assertTrue(
            self.report["charged_failure_observation"][
                "fourth_attempt_denied_without_charge"
            ]
        )

    def test_fault_committed_state_preserved(self):
        self.assertTrue(
            self.report["charged_failure_observation"][
                "committed_state_preserved"
            ]
        )

    def test_healthy_peer_survived(self):
        self.assertTrue(
            self.report["charged_failure_observation"][
                "healthy_peer_completed"
            ]
        )

    def test_healthy_peer_reference_accuracy(self):
        self.assertLess(
            self.report["charged_failure_observation"][
                "healthy_peer_max_abs_error_vs_s6"
            ],1e-8
        )

    def test_fault_session_retirements(self):
        self.assertEqual(
            self.report["charged_failure_observation"][
                "retirement_receipts"
            ],2
        )

    def test_prepublication_no_ack(self):
        self.assertFalse(
            self.report["prepublication_failure_receipt"][
                "candidate_acknowledged"
            ]
        )

    def test_prepublication_charge(self):
        self.assertEqual(
            self.report["prepublication_failure_receipt"][
                "attempted_work_units_charged"
            ],1
        )

    def test_prepublication_no_committed_mutation(self):
        self.assertTrue(
            self.report["prepublication_failure_receipt"][
                "committed_state_unchanged"
            ]
        )

    def test_prepublication_terminal(self):
        self.assertTrue(
            self.report["prepublication_failure_receipt"][
                "terminal_cancellation"
            ]
        )

    def test_prepublication_retired(self):
        self.assertTrue(
            self.report["prepublication_failure_receipt"][
                "retired_after_abort"
            ]
        )

    def test_internal_tamper_rejection(self):
        self.assertTrue(
            self.report["internal_receipt_tamper"][
                "internal_receipt_tamper_rejected"
            ]
        )

    def test_recovery_after_tamper_restored(self):
        self.assertTrue(
            self.report["internal_receipt_tamper"][
                "subsequent_operations_after_restoration"
            ]
        )

    def test_initial_observations(self):
        f=m.ObservationBoundary(
            max_active=1,max_created=1
        )
        self.assertEqual(
            f.observe_denials()["receipt_count"],0
        )
        self.assertEqual(
            f.observe_retirements()["receipt_count"],0
        )

    def test_observation_stable(self):
        f=m.ObservationBoundary(
            max_active=1,max_created=1
        )
        before=f.observe_registry()
        self.assertEqual(before,f.observe_registry())

    def test_wrong_owner_observation_denied(self):
        f=m.ObservationBoundary(
            max_active=1,max_created=1
        )
        g=graph.build("clean",True,13)
        lease,owner=f.open(g)

        with self.assertRaises(m.OperationDenied):
            f.observe_session(lease,object())

        f.cancel(lease,owner,version=0)
        f.retire(lease,owner)

    def test_unknown_lease_observation_denied(self):
        f=m.ObservationBoundary(
            max_active=1,max_created=1
        )
        g=graph.build("clean",True,13)
        lease,owner=f.open(g)

        with self.assertRaises(m.OperationDenied):
            f.observe_session(object(),owner)

        f.cancel(lease,owner,version=0)
        f.retire(lease,owner)

    def test_no_owner_objects_exposed(self):
        self.assertTrue(
            self.report["owner_object_not_in_observations"]
        )

    def test_no_source_packets_exposed(self):
        self.assertTrue(
            self.report["source_packet_not_in_observations"]
        )

    def test_no_forged_ack(self):
        self.assertTrue(
            self.report["successful_acknowledgements_not_forged"]
        )

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

    def test_no_malicious_actor_claim(self):
        self.assertFalse(
            self.report[
                "malicious_inprocess_tamper_protection_verified"
            ]
        )

    def test_no_concurrent_safety_claim(self):
        self.assertFalse(
            self.report["actual_concurrent_thread_safety_verified"]
        )

    def test_no_memory_claim(self):
        self.assertFalse(
            self.report["physical_memory_reclamation_verified"]
        )

    def test_no_hardware_claim(self):
        self.assertFalse(
            self.report["hardware_streaming_verified"]
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

    def test_deterministic_serialization(self):
        self.assertEqual(
            m.canonical(self.report),
            m.canonical(self.report)
        )

if __name__=="__main__":
    unittest.main(verbosity=2)
