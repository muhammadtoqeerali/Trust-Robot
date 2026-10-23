import unittest

from r126_reference_bypass import (
    execute,
    fork_case,
    pointer_rebinding_case,
    receipt_mutation_cases,
    selected_alias_case,
)


class TestR126ExternalReferences(unittest.TestCase):

    def test_cancel_old_reference_bypass(self):
        row = fork_case("cancel")
        self.assertTrue(
            row["old_facade_operation_accepted_after_publication"]
        )

    def test_cancel_old_phase(self):
        row = fork_case("cancel")
        self.assertEqual(row["old_phase_before_bypass"], "ACTIVE")

    def test_cancel_published_phase(self):
        row = fork_case("cancel")
        self.assertEqual(
            row["published_phase_before_bypass"], "CANCELLED"
        )

    def test_cancel_dual_receipts(self):
        row = fork_case("cancel")
        self.assertEqual(
            row["old_terminal_count_after_bypass"], 1
        )
        self.assertEqual(row["published_terminal_count"], 1)

    def test_cancel_new_publication_unchanged(self):
        row = fork_case("cancel")
        self.assertEqual(
            row["published_observation_before_sha256"],
            row["published_observation_after_sha256"],
        )

    def test_retire_old_reference_bypass(self):
        row = fork_case("retire")
        self.assertTrue(
            row["old_facade_operation_accepted_after_publication"]
        )

    def test_retire_old_phase(self):
        row = fork_case("retire")
        self.assertEqual(
            row["old_phase_before_bypass"], "CANCELLED"
        )

    def test_retire_published_phase(self):
        row = fork_case("retire")
        self.assertEqual(
            row["published_phase_before_bypass"], "RETIRED"
        )

    def test_retire_dual_receipts(self):
        row = fork_case("retire")
        self.assertEqual(
            row["old_terminal_count_after_bypass"], 2
        )
        self.assertEqual(row["published_terminal_count"], 2)

    def test_retire_new_publication_unchanged(self):
        row = fork_case("retire")
        self.assertTrue(
            row["published_observation_unchanged_by_old_operation"]
        )

    def test_pointer_rebinding(self):
        row = pointer_rebinding_case()
        self.assertTrue(
            row["unprotected_pointer_rebinding_possible"]
        )
        self.assertEqual(
            row["visible_phase_after_rebinding"], "ACTIVE"
        )

    def test_original_receipt_mutation_detected(self):
        row = receipt_mutation_cases()
        self.assertTrue(row["old_receipt_tamper_detected"])

    def test_published_receipt_mutation_detected(self):
        row = receipt_mutation_cases()
        self.assertTrue(row["published_receipt_tamper_detected"])

    def test_selected_mutable_aliases_distinct(self):
        row = selected_alias_case()
        self.assertEqual(row["selected_checks_passed"], 8)
        self.assertFalse(
            row["exhaustive_object_graph_isolation_proven"]
        )

    def test_aggregate_nonclaims(self):
        report = execute()
        self.assertTrue(report["pass"])
        self.assertEqual(
            report["confirmed_stale_reference_bypasses"], 2
        )
        self.assertEqual(report["scientific_gates_closed"], 11)
        for name in (
            "actual_r122_source_modified",
            "R126_B1_source_modified",
            "global_exactly_once_proven",
            "old_facade_revocation_proven",
            "drop_in_atomic_backend_proven",
            "concurrent_publication_proven",
            "durable_recovery_proven",
            "physical_safety_proven",
            "real_sensor_factors_executed",
            "confirmation_test_accessed",
        ):
            self.assertIs(report[name], False, name)


if __name__ == "__main__":
    unittest.main()
