import unittest
from test_nova_schema_shadow_v1 import example
from test_nova_ros_ingress_shadow_v1 import fake
from trust_robot.nova_schema_shadow_v1 import TOPICS
from trust_robot.nova_bounded_session_shadow_v1 import (
    BoundedSession, SessionDenied, MAX_DURATION_NS, SCHEMA,
)

def packet(stream='LEFT_IMAGE', stamp=1_000_000_000):
    row = example(stream, 0, stamp)
    return row['topic'], fake(row)

def completed():
    s = BoundedSession(100)
    tick = 100
    for stream in TOPICS:
        for i in range(3):
            topic, msg = packet(stream, 1_000_000_000 + i * 10_000_000)
            tick += 1_000_000
            s.ingest(topic, msg, tick)
    return s, tick

class BoundedSessionTests(unittest.TestCase):
    def test_01_schema(self):
        self.assertIn('A50_17', SCHEMA)
        self.assertEqual(MAX_DURATION_NS, 20_000_000_000)

    def test_02_all_six_streams(self):
        self.assertEqual(len(TOPICS), 6)

    def test_03_single_message(self):
        s = BoundedSession(0)
        topic, msg = packet()
        self.assertEqual(s.ingest(topic, msg, 1), ('LEFT_IMAGE', 1))

    def test_04_complete_manufactured_batch(self):
        s, t = completed()
        result = s.finish(t + 1)
        self.assertEqual(result['messages'], 18)
        self.assertEqual(result['real_factor_admission'], 'DENIED')
        self.assertFalse(result['physical_qualification'])
        self.assertEqual(s.rows, {})

    def test_05_incomplete_batch_denied(self):
        s = BoundedSession(0)
        with self.assertRaises(SessionDenied): s.finish(1)
        self.assertEqual(s.rows, {})

    def test_06_unknown_topic_denied(self):
        s = BoundedSession(0)
        with self.assertRaises(SessionDenied): s.ingest('/cmd_vel', object(), 1)
        self.assertTrue(s.closed)

    def test_07_invalid_message_denied(self):
        s = BoundedSession(0)
        topic, _ = packet()
        with self.assertRaises(SessionDenied): s.ingest(topic, object(), 1)
        self.assertTrue(s.closed)

    def test_08_expired_clock_denied(self):
        s = BoundedSession(0, 10)
        topic, msg = packet()
        with self.assertRaises(SessionDenied): s.ingest(topic, msg, 11)

    def test_09_reversed_clock_denied(self):
        s = BoundedSession(0)
        topic, msg = packet()
        s.ingest(topic, msg, 20)
        with self.assertRaises(SessionDenied): s.ingest(topic, msg, 19)

    def test_10_repeated_header_denied(self):
        s = BoundedSession(0)
        topic, msg = packet()
        s.ingest(topic, msg, 1)
        with self.assertRaises(SessionDenied): s.ingest(topic, msg, 2)

    def test_11_reversed_header_denied(self):
        s = BoundedSession(0)
        topic, msg = packet('LIDAR', 2_000_000_000)
        s.ingest(topic, msg, 1)
        topic2, msg2 = packet('LIDAR', 1_000_000_000)
        with self.assertRaises(SessionDenied): s.ingest(topic2, msg2, 2)

    def test_12_per_stream_budget(self):
        s = BoundedSession(0)
        for i in range(3):
            topic, msg = packet('IMU', 1_000_000_000 + i)
            s.ingest(topic, msg, i + 1)
        topic, msg = packet('IMU', 1_000_000_003)
        with self.assertRaises(SessionDenied): s.ingest(topic, msg, 4)

    def test_13_abort_erases_metadata(self):
        s = BoundedSession(0)
        topic, msg = packet()
        s.ingest(topic, msg, 1)
        s.abort()
        self.assertTrue(s.closed)
        self.assertEqual(s.rows, {})

    def test_14_no_reuse_after_finish(self):
        s, t = completed()
        s.finish(t + 1)
        topic, msg = packet()
        with self.assertRaises(SessionDenied): s.ingest(topic, msg, t + 2)

    def test_15_unbounded_duration_denied(self):
        with self.assertRaises(SessionDenied):
            BoundedSession(0, MAX_DURATION_NS + 1)

    def test_16_boolean_time_denied(self):
        with self.assertRaises(SessionDenied): BoundedSession(True)

    def test_17_no_payload_field_access(self):
        s = BoundedSession(0)
        topic, msg = packet('RIGHT_IMAGE')  # fake .data raises on access
        self.assertEqual(s.ingest(topic, msg, 1), ('RIGHT_IMAGE', 1))

    def test_18_inferred_health_not_emitted(self):
        s, t = completed()
        result = s.finish(t + 1)
        self.assertNotIn('health_probability', result)
        self.assertNotIn('pose', result)
        self.assertNotIn('weights', result)

if __name__ == '__main__': unittest.main()
