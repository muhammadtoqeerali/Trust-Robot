import copy
import unittest

from trust_robot.replay_observability_v1 import (
    ReplayObservabilityError,
    review_software_observability,
    generate_physical_health_weights,
    STREAMS,
)


def fixture():
    src = {s: 0 for s in sorted(STREAMS)}
    src["imu"] = 8
    src["lidar"] = 2

    return {
        "schema": "TRUST_ROBOT_R135_A29_4_OFFLINE_REPLAY_V1",
        "status": "OFFLINE_RECORDER_ORDER_SIMULATION_ONLY",
        "input_count": 10,
        "source_counts": src,
        "synthetic_suppressed_counts": {s: 0 for s in src},
        "queue_overflow_counts": {s: 0 for s in src},
        "delivered_counts": dict(src),
        "queue_capacity": 8,
        "peak_queued_envelopes": 8,
        "suppressed_streams": [],
        "real_factor_admission": "DENIED",
        "m2dgr_gates": "11_CLOSED",
        "real_factor_count": 0,
        "estimator_invoked": False,
        "payload_decoded": False,
        "header_timestamp_inferred": False,
        "frame_id_inferred": False,
        "time_axis": "ORDINAL_SOFTWARE_TICKS_NOT_PHYSICAL_SECONDS",
    }


class ObservabilityTests(unittest.TestCase):

    def test_01_reference(self):
        r = review_software_observability(fixture())
        self.assertEqual(
            r["stream_labels"]["imu"]["software_label"],
            "SOFTWARE_DELIVERY_WITHIN_DECLARED_THRESHOLD",
        )

    def test_02_empty_stream(self):
        r = review_software_observability(fixture())
        self.assertEqual(
            r["stream_labels"]["left_image"]["software_label"],
            "NO_SOURCE_ENVELOPES",
        )

    def test_03_suppressed(self):
        x = fixture()
        x["synthetic_suppressed_counts"]["lidar"] = 2
        x["delivered_counts"]["lidar"] = 0
        x["suppressed_streams"] = ["lidar"]

        r = review_software_observability(x)

        self.assertEqual(
            r["stream_labels"]["lidar"]["software_label"],
            "INTENTIONALLY_SUPPRESSED_IN_SOFTWARE",
        )

    def test_04_overflow(self):
        x = fixture()
        x["queue_overflow_counts"]["imu"] = 4
        x["delivered_counts"]["imu"] = 4

        r = review_software_observability(x)

        self.assertEqual(
            r["stream_labels"]["imu"]["software_label"],
            "SOFTWARE_QUEUE_OVERFLOW",
        )

    def test_05_determinism(self):
        self.assertEqual(
            review_software_observability(fixture()),
            review_software_observability(
                copy.deepcopy(fixture())
            ),
        )

    def test_06_forged_admission_refused(self):
        x = fixture()
        x["real_factor_admission"] = "APPROVED"
        with self.assertRaises(ReplayObservabilityError):
            review_software_observability(x)

    def test_07_forged_factor_refused(self):
        x = fixture()
        x["real_factor_count"] = 1
        with self.assertRaises(ReplayObservabilityError):
            review_software_observability(x)

    def test_08_inferred_timestamp_refused(self):
        x = fixture()
        x["header_timestamp_inferred"] = True
        with self.assertRaises(ReplayObservabilityError):
            review_software_observability(x)

    def test_09_accounting_tamper_refused(self):
        x = fixture()
        x["delivered_counts"]["imu"] = 9
        with self.assertRaises(ReplayObservabilityError):
            review_software_observability(x)

    def test_10_bad_queue_refused(self):
        x = fixture()
        x["peak_queued_envelopes"] = 9
        with self.assertRaises(ReplayObservabilityError):
            review_software_observability(x)

    def test_11_invalid_stream_refused(self):
        x = fixture()
        x["source_counts"]["unknown"] = 1
        with self.assertRaises(ReplayObservabilityError):
            review_software_observability(x)

    def test_12_malformed_suppression_refused(self):
        x = fixture()
        x["suppressed_streams"] = ["unknown"]
        with self.assertRaises(ReplayObservabilityError):
            review_software_observability(x)

    def test_13_invalid_fraction_refused(self):
        with self.assertRaises(ReplayObservabilityError):
            review_software_observability(
                fixture(),
                minimum_delivered_num=2,
                minimum_delivered_den=1,
            )

    def test_14_health_denied(self):
        with self.assertRaises(ReplayObservabilityError):
            generate_physical_health_weights()

    def test_15_no_health_labels_or_weights(self):
        r = review_software_observability(fixture())
        self.assertFalse(r["physical_health_probabilities_generated"])
        self.assertFalse(r["factor_weights_computed"])


if __name__ == "__main__":
    unittest.main()
