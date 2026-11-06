import copy
import unittest

from trust_robot.synthetic_event_axis_v1 import (
    SyntheticAxisError,
    check_synthetic_event_axis,
    qualify_real_event_axis,
)

from trust_robot.synthetic_trajectory_ensemble_v1 import (
    ANCHOR_NS,
    build_seeded_trial,
)


def fixture():
    return build_seeded_trial(
        11,
        [True, True, False, False, True, True],
    )


class EventAxisTests(unittest.TestCase):

    def test_01_exact_six_step_axis(self):
        result = check_synthetic_event_axis(
            fixture(), anchor_ns=ANCHOR_NS
        )
        self.assertEqual(result["step_count"], 6)

    def test_02_large_epoch_preserved(self):
        result = check_synthetic_event_axis(
            fixture(), anchor_ns=ANCHOR_NS
        )
        self.assertEqual(
            result["final_event_stamp_ns"],
            ANCHOR_NS + 6 * 10**9,
        )

    def test_03_exact_intervals(self):
        result = check_synthetic_event_axis(
            fixture(), anchor_ns=ANCHOR_NS
        )
        self.assertTrue(all(
            row["observed_event_delta_ns"] == 10**9
            for row in result["synthetic_trace"]
        ))

    def test_04_reject_one_nanosecond_drift(self):
        steps = fixture()
        steps[3]["candidate"]["event_stamp_ns"] += 1

        with self.assertRaises(SyntheticAxisError):
            check_synthetic_event_axis(
                steps, anchor_ns=ANCHOR_NS
            )

    def test_05_reject_wrong_first_interval(self):
        steps = fixture()
        steps[0]["dt_ns"] += 1

        with self.assertRaises(SyntheticAxisError):
            check_synthetic_event_axis(
                steps, anchor_ns=ANCHOR_NS
            )

    def test_06_reject_wrong_middle_interval(self):
        steps = fixture()
        steps[2]["dt_ns"] -= 1

        with self.assertRaises(SyntheticAxisError):
            check_synthetic_event_axis(
                steps, anchor_ns=ANCHOR_NS
            )

    def test_07_reject_boolean_interval(self):
        steps = fixture()
        steps[0]["dt_ns"] = True

        with self.assertRaises(SyntheticAxisError):
            check_synthetic_event_axis(
                steps, anchor_ns=ANCHOR_NS
            )

    def test_08_reject_boolean_anchor(self):
        with self.assertRaises(SyntheticAxisError):
            check_synthetic_event_axis(
                fixture(), anchor_ns=True
            )

    def test_09_reject_sequence_change(self):
        steps = fixture()
        steps[1]["candidate"]["sequence"] = 0

        with self.assertRaises(SyntheticAxisError):
            check_synthetic_event_axis(
                steps, anchor_ns=ANCHOR_NS
            )

    def test_10_reject_mixed_clocks(self):
        steps = fixture()
        steps[1]["candidate"]["clock_domain"] = "other"

        with self.assertRaises(SyntheticAxisError):
            check_synthetic_event_axis(
                steps, anchor_ns=ANCHOR_NS
            )

    def test_11_reject_physical_candidate(self):
        steps = fixture()
        steps[0]["candidate"]["source_kind"] = "PHYSICAL"

        with self.assertRaises(SyntheticAxisError):
            check_synthetic_event_axis(
                steps, anchor_ns=ANCHOR_NS
            )

    def test_12_reject_invalid_availability(self):
        steps = fixture()
        steps[0]["software_available"] = 1

        with self.assertRaises(SyntheticAxisError):
            check_synthetic_event_axis(
                steps, anchor_ns=ANCHOR_NS
            )

    def test_13_determinism(self):
        first = check_synthetic_event_axis(
            fixture(), anchor_ns=ANCHOR_NS
        )
        second = check_synthetic_event_axis(
            copy.deepcopy(fixture()),
            anchor_ns=ANCHOR_NS,
        )
        self.assertEqual(first, second)

    def test_14_no_physical_clock_qualification(self):
        result = check_synthetic_event_axis(
            fixture(), anchor_ns=ANCHOR_NS
        )
        self.assertFalse(
            result["physical_clock_mapping_verified"]
        )
        self.assertEqual(result["real_factor_count"], 0)

        with self.assertRaises(SyntheticAxisError):
            qualify_real_event_axis()


if __name__ == "__main__":
    unittest.main()
