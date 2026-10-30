import copy
import unittest

from trust_robot.synthetic_event_clock_model_v1 import (
    ClockModelError,
    map_synthetic_event,
    synthetic_event_gap,
    estimate_physical_time_offset,
)


ANCHOR = 10**18


def event(stamp=ANCHOR + 1, domain="camera"):
    return {
        "domain": domain,
        "event_kind": "CAMERA_EXPOSURE",
        "stamp_ns": stamp,
        "error_bound_ns": 2,
        "status": "SYNTHETIC_UNQUALIFIED",
    }


def mapping():
    return {
        "source_domain": "camera",
        "target_domain": "imu",
        "source_anchor_ns": ANCHOR,
        "target_anchor_ns": ANCHOR + 1000,
        "scale_num": 1,
        "scale_den": 2,
        "mapping_error_ns": 3,
        "drift_bound_ppb": 0,
        "status": "SYNTHETIC_MODEL_ONLY",
    }


class SyntheticClockTests(unittest.TestCase):

    def test_01_exact_large_epoch_fraction(self):
        result = map_synthetic_event(event(), mapping())
        self.assertEqual(
            result["mapped_stamp_floor_ns"], ANCHOR + 1000
        )
        self.assertEqual(
            result["mapped_fraction_numerator"], 1
        )
        self.assertEqual(
            result["mapped_fraction_denominator"], 2
        )

    def test_02_conservative_bound(self):
        result = map_synthetic_event(event(), mapping())
        self.assertEqual(result["error_bound_ceiling_ns"], 4)

    def test_03_mapping_deterministic(self):
        self.assertEqual(
            map_synthetic_event(event(), mapping()),
            map_synthetic_event(
                copy.deepcopy(event()),
                copy.deepcopy(mapping()),
            ),
        )

    def test_04_drift_from_anchor(self):
        m = mapping()
        m["scale_num"] = 1
        m["scale_den"] = 1
        m["drift_bound_ppb"] = 10

        result = map_synthetic_event(
            event(ANCHOR + 10**9), m
        )
        self.assertEqual(
            result["error_bound_ceiling_ns"], 15
        )

    def test_05_clock_domain_mismatch(self):
        with self.assertRaises(ClockModelError):
            map_synthetic_event(
                event(domain="lidar"), mapping()
            )

    def test_06_qualified_event_rejected(self):
        e = event()
        e["status"] = "PHYSICALLY_VERIFIED"
        with self.assertRaises(ClockModelError):
            map_synthetic_event(e, mapping())

    def test_07_qualified_mapping_rejected(self):
        m = mapping()
        m["status"] = "CALIBRATED"
        with self.assertRaises(ClockModelError):
            map_synthetic_event(event(), m)

    def test_08_negative_scale_rejected(self):
        m = mapping()
        m["scale_num"] = -1
        with self.assertRaises(ClockModelError):
            map_synthetic_event(event(), m)

    def test_09_boolean_stamp_rejected(self):
        e = event()
        e["stamp_ns"] = True
        with self.assertRaises(ClockModelError):
            map_synthetic_event(e, mapping())

    def test_10_event_gap(self):
        a = event(100)
        b = event(110)
        result = synthetic_event_gap(a, b)
        self.assertEqual(result["nominal_gap_ns"], 10)
        self.assertEqual(result["minimum_gap_ns"], 6)
        self.assertEqual(result["maximum_gap_ns"], 14)

    def test_11_event_gap_domain_mismatch(self):
        with self.assertRaises(ClockModelError):
            synthetic_event_gap(
                event(domain="imu"), event()
            )

    def test_12_no_physical_admission(self):
        result = map_synthetic_event(event(), mapping())
        self.assertFalse(
            result["clock_mapping_independently_verified"]
        )
        self.assertEqual(result["real_factor_count"], 0)
        self.assertEqual(
            result["real_factor_admission"], "DENIED"
        )

    def test_13_physical_offset_fit_denied(self):
        with self.assertRaises(ClockModelError):
            estimate_physical_time_offset(event(), mapping())


if __name__ == "__main__":
    unittest.main()
