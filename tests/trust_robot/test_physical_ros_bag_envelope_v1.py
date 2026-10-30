"""Synthetic-only tests; no physical ROS bag or dataset."""

import unittest

from trust_robot.physical_ros_bag_envelope_v1 import (
    SCHEMA, TOPICS, COUNTS,
    CAPTURE_MANIFEST_SHA256,
    EnvelopeValidationError,
    validate_envelope,
    review_envelopes,
    review_pinned_capture,
    to_fusion_descriptor,
)


def sample(stream="imu", sequence=0, timestamp=1000, **kw):
    data = {
        "stream": stream,
        "sequence": sequence,
        "recorder_stamp_ns": timestamp,
        "serialized_bytes": 128,
        "source_kind": "PHYSICAL_UNQUALIFIED",
        "header_stamp_ns": None,
        "frame_id": None,
    }
    data.update(kw)
    return data


def full_fixture():
    rows = []
    original_topics = {}

    for topic, (stream, typ) in TOPICS.items():
        count = COUNTS[topic]
        original_topics[topic] = {
            "count": count,
            "serialized_bytes": count * 128,
        }
        for seq in range(count):
            rows.append(sample(
                stream=stream,
                sequence=seq,
                timestamp=1000000 + seq * 10000
                + list(TOPICS).index(topic),
            ))

    rows.sort(key=lambda x: x["recorder_stamp_ns"])

    report = {
        "schema": SCHEMA,
        "status": "READ_ONLY_ROSBAG_METADATA_ENVELOPES",
        "capture_manifest_sha256": CAPTURE_MANIFEST_SHA256,
        "raw_payload_columns_selected": False,
        "bag_file_hashes_rechecked": False,
        "bag_total_bytes": 1415126942,
        "topic_types": {
            k: v[1] for k, v in TOPICS.items()
        },
        "envelopes": rows,
    }

    audit = {
        "factor_admission": "DENIED",
        "m2dgr_gates": "11_CLOSED",
        "bag_total_bytes": 1415126942,
        "recorded_total_messages": 843,
        "topics": original_topics,
    }

    return report, audit


class EnvelopeTests(unittest.TestCase):

    def test_01_schema(self):
        self.assertIn("A29_3", SCHEMA)

    def test_02_valid_envelope(self):
        self.assertTrue(validate_envelope(sample()))

    def test_03_reject_header_substitution(self):
        with self.assertRaises(EnvelopeValidationError):
            validate_envelope(sample(header_stamp_ns=1000))

    def test_04_reject_assumed_frame(self):
        with self.assertRaises(EnvelopeValidationError):
            validate_envelope(sample(frame_id="bmi088_frame"))

    def test_05_reject_real_factor(self):
        with self.assertRaises(EnvelopeValidationError):
            validate_envelope(sample(factor_weight=1.0))

    def test_06_reject_invalid_source(self):
        with self.assertRaises(EnvelopeValidationError):
            validate_envelope(sample(source_kind="QUALIFIED"))

    def test_07_reject_boolean_timestamp(self):
        with self.assertRaises(EnvelopeValidationError):
            validate_envelope(sample(recorder_stamp_ns=True))

    def test_08_reject_negative_timestamp(self):
        with self.assertRaises(EnvelopeValidationError):
            validate_envelope(sample(recorder_stamp_ns=-1))

    def test_09_reject_unknown_stream(self):
        with self.assertRaises(EnvelopeValidationError):
            validate_envelope(sample(stream="cmd_vel"))

    def test_10_two_streams(self):
        result = review_envelopes([
            sample("imu", 0, 1000),
            sample("lidar", 0, 1001),
            sample("imu", 1, 1010),
        ])
        self.assertEqual(result["envelope_count"], 3)
        self.assertEqual(result["real_factor_count"], 0)

    def test_11_reject_duplicate_sequence(self):
        with self.assertRaises(EnvelopeValidationError):
            review_envelopes([
                sample(sequence=0),
                sample(sequence=0, timestamp=1100),
            ])

    def test_12_reject_out_of_order_recorder_stamp(self):
        with self.assertRaises(EnvelopeValidationError):
            review_envelopes([
                sample(sequence=0, timestamp=2000),
                sample(sequence=1, timestamp=1000),
            ])

    def test_13_reject_sequence_gap(self):
        with self.assertRaises(EnvelopeValidationError):
            review_envelopes([
                sample(sequence=0, timestamp=1000),
                sample(sequence=2, timestamp=2000),
            ])

    def test_14_full_synthetic_capture_consistency(self):
        report, audit = full_fixture()
        result = review_pinned_capture(report, audit)
        self.assertEqual(result["envelope_count"], 843)
        self.assertEqual(result["real_factor_admission"], "DENIED")
        self.assertFalse(result["original_bag_re_deserialized"])

    def test_15_reject_changed_serialized_bytes(self):
        report, audit = full_fixture()
        audit["topics"]["/front_stereo_imu/imu"][
            "serialized_bytes"
        ] += 1
        with self.assertRaises(EnvelopeValidationError):
            review_pinned_capture(report, audit)

    def test_16_reject_missing_stream(self):
        report, audit = full_fixture()
        report["envelopes"] = [
            r for r in report["envelopes"]
            if r["stream"] != "lidar"
        ]
        with self.assertRaises(EnvelopeValidationError):
            review_pinned_capture(report, audit)

    def test_17_reject_wrong_manifest(self):
        report, audit = full_fixture()
        report["capture_manifest_sha256"] = "a" * 64
        with self.assertRaises(EnvelopeValidationError):
            review_pinned_capture(report, audit)

    def test_18_reject_qualified_source_claim(self):
        report, audit = full_fixture()
        report["envelopes"][0]["source_kind"] = "REAL_QUALIFIED"
        with self.assertRaises(EnvelopeValidationError):
            review_pinned_capture(report, audit)

    def test_19_reject_factor_admission(self):
        report, audit = full_fixture()
        audit["factor_admission"] = "APPROVED"
        with self.assertRaises(EnvelopeValidationError):
            review_pinned_capture(report, audit)

    def test_20_conversion_always_denied(self):
        with self.assertRaises(EnvelopeValidationError):
            to_fusion_descriptor(sample())


if __name__ == "__main__":
    unittest.main()
