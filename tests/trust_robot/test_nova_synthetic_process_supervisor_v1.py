"""A50-21 synthetic-only KIOS OS process-group tests. No ROS / devices."""
import inspect
import unittest
from trust_robot.nova_synthetic_process_supervisor_v1 import (
    SCHEMA, SupervisorDenied, MAX_TEST_BUDGET_NS, run_synthetic_case,
)

class SyntheticSupervisorTests(unittest.TestCase):
    def test_01_schema(self):
        self.assertIn('A50_21', SCHEMA)

    def test_02_normal_exit(self):
        x = run_synthetic_case('CLEAN_EXIT')
        self.assertEqual(x['outcome'], 'SYNTHETIC_SUCCESS_ONLY')
        self.assertTrue(x['shutdown_verified'])

    def test_03_nonzero_exit_denied(self):
        x = run_synthetic_case('NONZERO_EXIT')
        self.assertEqual(x['outcome'], 'DENIED_NONZERO_CHILD_EXIT')
        self.assertTrue(x['shutdown_verified'])

    def test_04_timeout_cleaned(self):
        x = run_synthetic_case('SLEEP', 1_200_000_000)
        self.assertEqual(x['outcome'], 'DENIED_DEADLINE_EXCEEDED_CLEANED')
        self.assertTrue(x['shutdown_verified'])
        self.assertTrue(x['timeout_detected'])

    def test_05_ignored_term_escalated(self):
        x = run_synthetic_case('IGNORE_TERM', 1_200_000_000)
        self.assertEqual(x['outcome'], 'DENIED_DEADLINE_EXCEEDED_CLEANED')
        self.assertTrue(x['shutdown_verified'])

    def test_06_descendant_cleanup(self):
        x = run_synthetic_case('CHILD_REMAINS')
        self.assertEqual(x['outcome'], 'DENIED_DESCENDANT_CLEANED')
        self.assertTrue(x['shutdown_verified'])

    def test_07_unknown_case_rejected(self):
        with self.assertRaises(SupervisorDenied):
            run_synthetic_case('/bin/bash')

    def test_08_boolean_budget_rejected(self):
        with self.assertRaises(SupervisorDenied):
            run_synthetic_case('CLEAN_EXIT', True)

    def test_09_zero_budget_rejected(self):
        with self.assertRaises(SupervisorDenied):
            run_synthetic_case('CLEAN_EXIT', 0)

    def test_10_above_max_budget_rejected(self):
        with self.assertRaises(SupervisorDenied):
            run_synthetic_case('CLEAN_EXIT', MAX_TEST_BUDGET_NS + 1)

    def test_11_noninteger_budget_rejected(self):
        with self.assertRaises(SupervisorDenied):
            run_synthetic_case('CLEAN_EXIT', 0.2)

    def test_12_no_robot_or_ros_authorization(self):
        x = run_synthetic_case('CLEAN_EXIT')
        self.assertEqual(x['real_factor_admission'], 'DENIED')
        self.assertEqual(x['robot_actuation'], 'DENIED')
        self.assertFalse(x['ros_execution'])
        self.assertFalse(x['jetson_contact'])

if __name__ == '__main__':
    unittest.main()
