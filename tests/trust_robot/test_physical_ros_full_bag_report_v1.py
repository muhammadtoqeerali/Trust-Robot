"""Synthetic A28-4B metadata tests; no physical bag access."""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from trust_robot.physical_ros_full_bag_report_v1 import (
    CAPTURE_MANIFEST_SHA256,
    EXPECTED_COUNTS,
    FullBagReportError,
    SCHEMA,
    review_report,
    review_report_file,
)


def fixture():
    return {
        "bag_db_count": 1,
        "bag_total_bytes": 1415126942,
        "calibration_validity": "UNVERIFIED",
        "capture_manifest_sha256": CAPTURE_MANIFEST_SHA256,
        "factor_admission": "DENIED",
        "independent_ground_truth": "UNVERIFIED",
        "left_image_matching_info_stamps": 84,
        "left_unmatched_header_stamps": 3,
        "m2dgr_gates": "11_CLOSED",
        "original_metadata_sha256": "a" * 64,
        "phase": "R135-A28-3",
        "physical_clock_accuracy": "UNVERIFIED",
        "raw_images_exported": False,
        "raw_lidar_exported": False,
        "recorded_total_messages": 843,
        "right_image_matching_info_stamps": 76,
        "right_unmatched_header_stamps": 0,
        "sqlite_quick_check": "ok",
        "status": "FULL_BAG_INTEGRITY_AND_ROS_DESERIALIZATION_VERIFIED_ONLY",
        "stereo_exact_header_pairs": 81,
        "topics": {
            name: {
                "message_count": count,
                "message_type": msgtype,
                "payload_shape_mismatches": 0,
                "serialized_bytes": count * 128,
            }
            for name, (count, msgtype)
            in EXPECTED_COUNTS.items()
        },
    }


class FullBagReviewSyntheticTests(unittest.TestCase):

    def test_01_fixed_schema_and_denial(self):
        result = review_report(fixture())

        self.assertEqual(result["schema"], SCHEMA)
        self.assertEqual(result["reported_messages"], 843)
        self.assertFalse(
            result["report_original_bag_re_deserialized"]
        )
        self.assertEqual(
            result["real_factor_admission"], "DENIED"
        )

    def test_02_dict_and_list_topic_forms(self):
        value = fixture()
        value["topics"] = [
            dict(name=k, **v)
            for k, v in value["topics"].items()
        ]
        self.assertEqual(
            review_report(value)["topic_count"], 7
        )

    def test_03_wrong_total_rejected(self):
        value = fixture()
        value["recorded_total_messages"] = 844

        with self.assertRaises(FullBagReportError):
            review_report(value)

    def test_04_wrong_stream_count_rejected(self):
        value = fixture()
        value["topics"]["/front_stereo_imu/imu"][
            "message_count"
        ] = 426

        with self.assertRaises(FullBagReportError):
            review_report(value)

    def test_05_extra_stream_rejected(self):
        value = fixture()
        value["topics"]["/cmd_vel"] = {
            "message_count": 1
        }

        with self.assertRaises(FullBagReportError):
            review_report(value)

    def test_06_missing_stream_rejected(self):
        value = fixture()
        del value["topics"]["/correlated_timestamp"]

        with self.assertRaises(FullBagReportError):
            review_report(value)

    def test_07_real_admission_rejected(self):
        value = fixture()
        value["factor_admission"] = "APPROVED"

        with self.assertRaises(FullBagReportError):
            review_report(value)

    def test_08_changed_m2dgr_gates_rejected(self):
        value = fixture()
        value["m2dgr_gates"] = "OPEN"

        with self.assertRaises(FullBagReportError):
            review_report(value)

    def test_09_fake_clock_qualification_rejected(self):
        value = fixture()
        value["physical_clock_accuracy"] = "VERIFIED"

        with self.assertRaises(FullBagReportError):
            review_report(value)

    def test_10_fake_calibration_qualification_rejected(self):
        value = fixture()
        value["calibration_validity"] = "VERIFIED"

        with self.assertRaises(FullBagReportError):
            review_report(value)

    def test_11_raw_exports_rejected(self):
        value = fixture()
        value["raw_images_exported"] = True

        with self.assertRaises(FullBagReportError):
            review_report(value)

    def test_12_wrong_stereo_account_rejected(self):
        value = fixture()
        value["stereo_exact_header_pairs"] = 82

        with self.assertRaises(FullBagReportError):
            review_report(value)

    def test_13_wrong_type_rejected(self):
        value = fixture()
        value["topics"]["/front_stereo_imu/imu"][
            "message_type"
        ] = "bad"

        with self.assertRaises(FullBagReportError):
            review_report(value)

    def test_14_bogus_report_phase_rejected(self):
        value = fixture()
        value["phase"] = "R135-A28-2"

        with self.assertRaises(FullBagReportError):
            review_report(value)

    def test_15_unexpected_field_rejected(self):
        value = fixture()
        value["physical_localization_accuracy"] = 0.001

        with self.assertRaises(FullBagReportError):
            review_report(value)

    def test_16_digest_integrity_and_mutation(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "synthetic.json"
            path.write_text(json.dumps(fixture()))

            sha = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()

            self.assertEqual(
                review_report_file(
                    path, sha
                )["reported_messages"],
                843,
            )

            changed = fixture()
            changed["bag_db_count"] = 2
            path.write_text(json.dumps(changed))

            with self.assertRaises(FullBagReportError):
                review_report_file(path, sha)

    def test_17_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / "original.json"
            source.write_text(json.dumps(fixture()))

            link = Path(root) / "linked.json"
            link.symlink_to(source)

            sha = hashlib.sha256(
                source.read_bytes()
            ).hexdigest()

            with self.assertRaises(FullBagReportError):
                review_report_file(link, sha)

    def test_18_boolean_counter_rejected(self):
        value = fixture()
        value["bag_db_count"] = True

        with self.assertRaises(FullBagReportError):
            review_report(value)



    def test_19_generic_pass_label_is_not_accepted(self):
        value = fixture()
        value["status"] = "PASS"
        with self.assertRaises(FullBagReportError):
            review_report(value)

    def test_20_payload_shape_mismatch_is_rejected(self):
        value = fixture()
        value["topics"]["/front_3d_lidar/lidar_points"][
            "payload_shape_mismatches"
        ] = 1
        with self.assertRaises(FullBagReportError):
            review_report(value)

    def test_21_missing_serialized_statistic_is_rejected(self):
        value = fixture()
        del value["topics"]["/front_stereo_imu/imu"][
            "serialized_bytes"
        ]
        with self.assertRaises(FullBagReportError):
            review_report(value)

if __name__ == "__main__":
    unittest.main()
