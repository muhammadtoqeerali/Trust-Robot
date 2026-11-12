"""Offline-only bounded metadata session for a prospective ROS subscriber.

No ROS imports, subscriptions, raw payload access, logs, I/O, actuation,
localization, health probabilities, factors, or physical qualification.
"""
from trust_robot.nova_schema_shadow_v1 import TOPICS
from trust_robot.nova_ros_ingress_shadow_v1 import (
    BY_TOPIC, IngressDenied, project_metadata, review_projected,
)

SCHEMA = 'TRUST_ROBOT_R135_A50_17_BOUNDED_SHADOW_SESSION_V1'
MAX_DURATION_NS = 20_000_000_000
MAX_PER_STREAM = 3

class SessionDenied(ValueError):
    pass

def check(ok, reason):
    if not ok:
        raise SessionDenied(reason)

class BoundedSession:
    def __init__(self, start_ns, duration_ns=MAX_DURATION_NS):
        check(type(start_ns) is int and start_ns >= 0, 'START_CLOCK_INVALID')
        check(type(duration_ns) is int and 0 < duration_ns <= MAX_DURATION_NS,
              'DURATION_LIMIT')
        self.start_ns = start_ns
        self.deadline_ns = start_ns + duration_ns
        self.last_clock_ns = start_ns
        self.closed = False
        self.rows = {k: [] for k in TOPICS}

    def halt(self, reason):
        self.closed = True
        self.rows.clear()
        raise SessionDenied(reason)

    def clock(self, now_ns):
        if self.closed:
            raise SessionDenied('SESSION_CLOSED')
        if type(now_ns) is not int or not self.last_clock_ns <= now_ns <= self.deadline_ns:
            self.halt('MONOTONIC_DEADLINE_VIOLATION')
        self.last_clock_ns = now_ns

    def ingest(self, topic, message, now_ns):
        self.clock(now_ns)
        if type(topic) is not str or topic not in BY_TOPIC:
            self.halt('TOPIC_NOT_ALLOWLISTED')
        stream, _ = BY_TOPIC[topic]
        prior = self.rows[stream]
        if len(prior) >= MAX_PER_STREAM:
            self.halt('STREAM_BUDGET_EXCEEDED')
        try:
            row = project_metadata(topic, message, len(prior))
        except Exception as exc:
            self.halt('PROJECTOR_DENIED_' + type(exc).__name__)
        if prior and row['header_stamp_ns'] <= prior[-1]['header_stamp_ns']:
            self.halt('NONMONOTONIC_SENSOR_HEADER')
        prior.append(row)
        return (stream, len(prior))

    def finish(self, now_ns):
        self.clock(now_ns)
        if any(len(self.rows[k]) != MAX_PER_STREAM for k in TOPICS):
            self.halt('INCOMPLETE_SIX_STREAM_BATCH')
        try:
            result = review_projected([row for k in TOPICS for row in self.rows[k]])
        except Exception as exc:
            self.halt('SCIENTIFIC_BOUNDARY_DENIED_' + type(exc).__name__)
        if (result['record_count'] != 18 or result['real_factor_count'] != 0
                or result['real_factor_admission'] != 'DENIED'
                or result['robot_actuation'] != 'DENIED'
                or result['m2dgr_gates'] != '11_CLOSED'):
            self.halt('SCIENCE_GATE_DRIFT')
        self.closed = True
        self.rows.clear()
        return {'schema': SCHEMA, 'streams': 6, 'messages': 18,
                'source_kind': 'PHYSICAL_UNQUALIFIED',
                'real_factor_admission': 'DENIED',
                'robot_actuation': 'DENIED',
                'physical_qualification': False}

    def abort(self):
        self.closed = True
        self.rows.clear()
