"""Additional manufactured adversarial tests. No ROS runtime or private sensor files."""
import inspect
import unittest
from unittest.mock import patch
from test_nova_schema_shadow_v1 import example
from test_nova_ros_ingress_shadow_v1 import fake
import trust_robot.nova_bounded_session_shadow_v1 as mod


def example_message(stream='LEFT_IMAGE', stamp=1_000_000_000):
    row = example(stream, 0, stamp)
    return row['topic'], fake(row)

class A5018AdversarialTests(unittest.TestCase):
    def setUp(self):
        self.s = mod.BoundedSession(100, 50)

    def tearDown(self):
        self.s.abort()

    def test_01_unexpected_runtime_error_is_fail_closed(self):
        topic, msg = example_message()
        def boom(_): raise RuntimeError('manufactured access failure')
        type(msg).width = property(boom)
        with self.assertRaises(mod.SessionDenied): self.s.ingest(topic, msg, 101)
        self.assertTrue(self.s.closed)
        self.assertEqual(self.s.rows, {})

    def test_02_os_error_is_fail_closed(self):
        topic, msg = example_message('LEFT_INFO')
        def boom(_): raise OSError('manufactured metadata failure')
        type(msg).k = property(boom)
        with self.assertRaises(mod.SessionDenied): self.s.ingest(topic, msg, 101)
        self.assertTrue(self.s.closed)
        self.assertEqual(self.s.rows, {})

    def test_03_clock_at_exact_boundary_allowed(self):
        topic, msg = example_message()
        self.assertEqual(self.s.ingest(topic, msg, 150), ('LEFT_IMAGE', 1))

    def test_04_clock_beyond_boundary_halts(self):
        topic, msg = example_message()
        with self.assertRaises(mod.SessionDenied): self.s.ingest(topic, msg, 151)
        self.assertTrue(self.s.closed)

    def test_05_boolean_now_rejected(self):
        topic, msg = example_message()
        with self.assertRaises(mod.SessionDenied): self.s.ingest(topic, msg, True)
        self.assertEqual(self.s.rows, {})

    def test_06_reordered_wall_clock_halts(self):
        topic, msg = example_message()
        self.s.ingest(topic, msg, 102)
        with self.assertRaises(mod.SessionDenied): self.s.ingest(topic, msg, 101)
        self.assertEqual(self.s.rows, {})

    def test_07_budget_violation_clears_other_streams(self):
        topic1, msg1 = example_message('LEFT_IMAGE')
        self.s.ingest(topic1, msg1, 101)
        for i in range(3):
            topic, msg = example_message('IMU', 1_000_000_000 + i)
            self.s.ingest(topic, msg, 102 + i)
        topic, msg = example_message('IMU', 1_000_000_003)
        with self.assertRaises(mod.SessionDenied): self.s.ingest(topic, msg, 105)
        self.assertEqual(self.s.rows, {})

    def test_08_boundary_exception_on_finish_clears_rows(self):
        for index, stream in enumerate(mod.TOPICS):
            for j in range(3):
                topic, msg = example_message(stream, 1_000_000_000 + j)
                self.s.ingest(topic, msg, 101 + index*3 + j)
        with patch.object(mod, 'review_projected', side_effect=RuntimeError('manufactured')):
            with self.assertRaises(mod.SessionDenied): self.s.finish(121)
        self.assertTrue(self.s.closed)
        self.assertEqual(self.s.rows, {})

    def test_09_abort_is_idempotent(self):
        self.s.abort()
        self.s.abort()
        self.assertTrue(self.s.closed)
        self.assertEqual(self.s.rows, {})

    def test_10_session_cannot_reuse_after_abort(self):
        self.s.abort()
        topic, msg = example_message()
        with self.assertRaises(mod.SessionDenied): self.s.ingest(topic, msg, 101)

    def test_11_clock_is_injected_not_a_real_watchdog(self):
        self.assertIn('now_ns', inspect.signature(mod.BoundedSession.ingest).parameters)
        self.assertEqual(mod.MAX_DURATION_NS, 20_000_000_000)

    def test_12_no_live_ros_imports(self):
        source = inspect.getsource(mod)
        self.assertNotIn('import rclpy', source)
        self.assertNotIn('import rospy', source)
        self.assertNotIn('.data', source)
        self.assertNotIn('subprocess', source)

if __name__ == '__main__': unittest.main()
