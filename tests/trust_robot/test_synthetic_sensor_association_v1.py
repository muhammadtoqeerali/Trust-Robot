import copy
import unittest

from trust_robot.synthetic_sensor_association_v1 import (
    SyntheticAssociationError,
    associate_synthetic_events,
    associate_real_sensor_events,
)

A = 10**18


def ev(t, domain="camera", kind="CAMERA_EXPOSURE", err=0):
    return {
        "domain": domain,
        "event_kind": kind,
        "stamp_ns": t,
        "error_bound_ns": err,
        "status": "SYNTHETIC_UNQUALIFIED",
    }


def mapping(num=1, den=1):
    return {
        "source_domain": "imu",
        "target_domain": "camera",
        "source_anchor_ns": A,
        "target_anchor_ns": A + 5,
        "scale_num": num,
        "scale_den": den,
        "mapping_error_ns": 0,
        "drift_bound_ppb": 0,
        "status": "SYNTHETIC_MODEL_ONLY",
    }


class AssociationTests(unittest.TestCase):

    def test_01_equal_clock_match(self):
        r = associate_synthetic_events(
            [ev(A), ev(A + 10)],
            [ev(A), ev(A + 10)],
            tolerance_ns=0,
        )
        self.assertEqual(r["matched_count"], 2)

    def test_02_large_epoch_with_clock_map(self):
        r = associate_synthetic_events(
            [ev(A + 5), ev(A + 15), ev(A + 25)],
            [
                ev(A, "imu", "IMU_SAMPLE"),
                ev(A + 10, "imu", "IMU_SAMPLE"),
                ev(A + 35, "imu", "IMU_SAMPLE"),
            ],
            tolerance_ns=0,
            right_to_left_mapping=mapping(),
        )
        self.assertEqual(r["matched_count"], 2)
        self.assertEqual(r["unmatched_left_count"], 1)

    def test_03_fractional_exact_gap(self):
        r = associate_synthetic_events(
            [ev(A + 5)],
            [ev(A + 1, "imu", "IMU_SAMPLE")],
            tolerance_ns=1,
            right_to_left_mapping=mapping(1, 2),
        )
        self.assertEqual(
            r["matches"][0]["right_minus_left_ns_denominator"], 2
        )

    def test_04_mapping_uncertainty_conservative(self):
        m = mapping()
        m["mapping_error_ns"] = 1

        r = associate_synthetic_events(
            [ev(A + 5, err=1)],
            [ev(A, "imu", "IMU_SAMPLE", err=1)],
            tolerance_ns=2,
            right_to_left_mapping=m,
        )
        self.assertEqual(r["matched_count"], 0)

    def test_05_uncertainty_at_boundary(self):
        r = associate_synthetic_events(
            [ev(A, err=1)],
            [ev(A, err=2)],
            tolerance_ns=3,
        )
        self.assertEqual(r["matched_count"], 1)

    def test_06_order_preserved_with_ties(self):
        r = associate_synthetic_events(
            [ev(A), ev(A)],
            [ev(A), ev(A)],
            tolerance_ns=0,
        )
        self.assertEqual(
            [(x["left_index"], x["right_index"]) for x in r["matches"]],
            [(0, 0), (1, 1)],
        )

    def test_07_reproducible_digest(self):
        x = [ev(A), ev(A + 1)]
        self.assertEqual(
            associate_synthetic_events(x, x, tolerance_ns=1),
            associate_synthetic_events(
                copy.deepcopy(x),
                copy.deepcopy(x),
                tolerance_ns=1,
            ),
        )

    def test_08_cross_clock_without_map_refused(self):
        with self.assertRaises(SyntheticAssociationError):
            associate_synthetic_events(
                [ev(A)],
                [ev(A, "imu", "IMU_SAMPLE")],
                tolerance_ns=0,
            )

    def test_09_wrong_direction_refused(self):
        m = mapping()
        m["target_domain"] = "lidar"
        with self.assertRaises(SyntheticAssociationError):
            associate_synthetic_events(
                [ev(A)],
                [ev(A, "imu", "IMU_SAMPLE")],
                tolerance_ns=0,
                right_to_left_mapping=m,
            )

    def test_10_nonmonotone_refused(self):
        with self.assertRaises(SyntheticAssociationError):
            associate_synthetic_events(
                [ev(A + 1), ev(A)],
                [ev(A)],
                tolerance_ns=0,
            )

    def test_11_fake_physical_event_refused(self):
        item = ev(A)
        item["status"] = "PHYSICAL"
        with self.assertRaises(SyntheticAssociationError):
            associate_synthetic_events(
                [item], [ev(A)], tolerance_ns=0
            )

    def test_12_boolean_tolerance_refused(self):
        with self.assertRaises(SyntheticAssociationError):
            associate_synthetic_events(
                [ev(A)], [ev(A)], tolerance_ns=True
            )

    def test_13_unbounded_tolerance_refused(self):
        with self.assertRaises(SyntheticAssociationError):
            associate_synthetic_events(
                [ev(A)], [ev(A)],
                tolerance_ns=10**15,
            )

    def test_14_empty_refused(self):
        with self.assertRaises(SyntheticAssociationError):
            associate_synthetic_events(
                [], [ev(A)], tolerance_ns=1
            )

    def test_15_mixed_domains_refused(self):
        with self.assertRaises(SyntheticAssociationError):
            associate_synthetic_events(
                [ev(A), ev(A + 1, "imu", "IMU_SAMPLE")],
                [ev(A)],
                tolerance_ns=1,
            )

    def test_16_factor_denial(self):
        with self.assertRaises(SyntheticAssociationError):
            associate_real_sensor_events()

    def test_17_no_factors(self):
        result = associate_synthetic_events(
            [ev(A)], [ev(A)], tolerance_ns=0
        )
        self.assertEqual(result["real_factor_count"], 0)
        self.assertEqual(result["m2dgr_gates"], "11_CLOSED")


if __name__ == "__main__":
    unittest.main()
