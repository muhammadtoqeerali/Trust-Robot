import unittest

import r104_shared_graph as graph
import r123_terminal_faults as m

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
            "PASS_SYNTHETIC_TERMINAL_FAULT_BOUNDARY_AUDIT"
        )

    def test_eight_stages(self):
        self.assertEqual(
            self.report["fault_injection_stages"],8
        )

    def test_all_stages_present(self):
        self.assertEqual(
            set(self.report["fault_cases"]),
            set(m.STAGES)
        )

    def test_two_premutation_failures(self):
        self.assertEqual(
            self.report["pre_mutation_failures"],2
        )

    def test_two_safe_retries(self):
        self.assertEqual(
            self.report["pre_mutation_safe_retries"],2
        )

    def test_six_postmutation_failures(self):
        self.assertEqual(
            self.report["post_mutation_failures"],6
        )

    def test_six_quarantines(self):
        self.assertEqual(
            self.report["quarantined_ambiguous_sessions"],6
        )

    def test_four_missing_receipt_cases(self):
        self.assertEqual(
            self.report["missing_terminal_receipt_cases"],4
        )

    def test_two_ack_ambiguities(self):
        self.assertEqual(
            self.report["acknowledgement_ambiguity_cases"],2
        )

    def test_baseline_verified(self):
        self.assertTrue(
            self.report["r122_baseline_verified"]
        )

    def test_baseline_six_sessions(self):
        self.assertEqual(
            self.report["r122_baseline_sessions"],6
        )

    def test_baseline_terminal_capacity(self):
        self.assertEqual(
            self.report["r122_bounded_terminal_receipts"],24
        )

    def test_tamper_preflight_rejected(self):
        self.assertTrue(
            self.report["integrity_preflight"][
                "tamper_rejected_pre_mutation"
            ]
        )

    def test_tamper_preserves_registry(self):
        self.assertTrue(
            self.report["integrity_preflight"][
                "registry_unchanged_at_rejection"
            ]
        )

    def test_tamper_restoration(self):
        self.assertTrue(
            self.report["integrity_preflight"][
                "retirement_after_restoration"
            ]
        )

    def test_ordinary_saturation_blocks(self):
        self.assertEqual(
            self.report["saturation_boundary"][
                "ordinary_mutations_blocked"
            ],3
        )

    def test_saturation_terminal_path(self):
        self.assertTrue(
            self.report["saturation_boundary"][
                "terminal_cancel_and_retire_completed"
            ]
        )

    def test_saturation_denials_unchanged(self):
        self.assertTrue(
            self.report["saturation_boundary"][
                "original_denials_preserved"
            ]
        )

    def test_no_terminal_rollback_claim(self):
        self.assertFalse(
            self.report[
                "transactional_terminal_rollback_proven"
            ]
        )

    def test_no_postmutation_retry_claim(self):
        self.assertFalse(
            self.report[
                "postmutation_retry_safety_proven"
            ]
        )

    def test_no_receipt_completion_claim(self):
        self.assertFalse(
            self.report[
                "receipt_completion_after_fault_guaranteed"
            ]
        )

    def test_no_hardware_emergency_stop(self):
        self.assertFalse(
            self.report["hardware_emergency_stop_verified"]
        )

    def test_no_process_crash_recovery(self):
        self.assertFalse(
            self.report["process_failure_recovery_verified"]
        )

    def test_no_concurrent_thread_safety(self):
        self.assertFalse(
            self.report[
                "actual_concurrent_thread_safety_verified"
            ]
        )

    def test_no_durable_logging(self):
        self.assertFalse(
            self.report["durable_logging_verified"]
        )

    def test_no_authenticated_logging(self):
        self.assertFalse(
            self.report["authenticated_logging_verified"]
        )

    def test_no_physical_ram_claim(self):
        self.assertFalse(
            self.report[
                "physical_memory_reclamation_verified"
            ]
        )

    def test_no_real_time_claim(self):
        self.assertFalse(
            self.report["real_time_deadline_verified"]
        )

    def test_no_r95_import(self):
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

    def test_eleven_scientific_gates(self):
        self.assertEqual(
            self.report["scientific_gates_closed"],11
        )

    def test_serialization(self):
        self.assertEqual(
            m.canonical(self.report),
            m.canonical(self.report)
        )

    def test_initial_fault_witness(self):
        f,lease,owner=m.make_saturated_fixture()
        witness=m.FaultWitness(f,lease,owner)

        self.assertFalse(witness.quarantined)
        self.assertEqual(witness.events,[])

        f.terminal_cancel(lease,owner,version=0)
        f.terminal_retire(lease,owner)

    def test_invalid_fault_stage(self):
        with self.assertRaises(m.FaultAuditError):
            m.run_fault_case("INVALID_STAGE")

# Each fault boundary gets five separately named,
# independently asserted regression cases.
def build_case_test(stage,field,expected):
    def check(self):
        actual=self.report["fault_cases"][stage][field]
        self.assertEqual(actual,expected)
    return check

for stage,values in m.EXPECT.items():
    changed,receipts,active,retired=values

    assertions={
        "state_changed":changed,
        "terminal_receipts_after":receipts,
        "active_after":active,
        "retired_after":retired,
        "quarantined":changed,
    }

    for field,expected in assertions.items():
        method=build_case_test(stage,field,expected)

        method.__name__=(
            "test_"+stage+"_"+field
        )

        setattr(Tests,method.__name__,method)

if __name__=="__main__":
    unittest.main(verbosity=2)
