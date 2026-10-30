"""Synthetic-only A30 tests; no robot or dataset access."""

import copy
import unittest

from trust_robot.m2dgr_prospective_evidence_packet_v1 import (
    REQUEST_SPECS,
    SCHEMA as A23_SCHEMA,
    STATUS as A23_STATUS,
)
from trust_robot.analytic_15d_evidence_review_v1 import (
    BLOCKED_CAPABILITIES,
)
from trust_robot.physical_measurement_readiness_v1 import (
    EXPECTED_PINS,
    MeasurementReadinessError,
    review_readiness,
    admit_physical_measurements,
)


def fixture():
    requests = []

    for ident, stage, *_ in REQUEST_SPECS:
        requests.append({
            "request_id": ident,
            "stage": stage,
            "request_status": "UNFULFILLED",
            "independent_review_status": "NOT_YET_VERIFIED",
            "qualifying_receipt_received": False,
            "scientific_gate_opened": False,
            "evidence_artifact_sha256": None,
            "physical_parameter_value": None,
        })

    packet = {
        "schema": A23_SCHEMA,
        "status": A23_STATUS,
        "original_m2dgr_gates_closed": 11,
        "qualified_physical_receipt_count": 0,
        "frozen_m2dgr_split": {
            "train": 22,
            "validation_calibration": 7,
            "confirmation_test": 7,
        },
        "confirmation_test_pristine_from_prior_inspection": False,
        "confirmation_test_prospectively_closed": True,
        "scientific_permissions": {
            x: "BLOCKED" for x in BLOCKED_CAPABILITIES
        },
        "requests": requests,
        "stages": [
            {
                "stage": stage,
                "stage_authorized": False,
                "completed_independent_receipts": 0,
                "l33_qualification": "NOT_YET_VERIFIED",
            }
            for stage in ("A", "B", "C", "D")
        ],
    }

    frame = {
        "status": "FRAME_IDENTITY_REVIEW_ONLY",
        "physical_imu_frame_id": "bmi088_frame",
        "physical_imu_frame_in_nominal_urdf": False,
        "bmi088_to_platform_transform": None,
        "bmi088_to_front_stereo_imu_equivalence": "UNVERIFIED",
        "real_factor_admission": "DENIED",
        "m2dgr_gates": "11_CLOSED",
    }

    installed = {
        "schema":
            "TRUST_ROBOT_R135_A27_5_STATIC_SOURCE_INSPECTION_V1",
        "status": "STATIC_PINNED_FILE_INSPECTION_ONLY",
        "pinned_sha256": dict(EXPECTED_PINS),
        "urdf_links": 37,
        "urdf_joints": 36,
        "calibration_sensor_count": 12,
        "bmi088_frame_declared_in_nominal_urdf": False,
        "frame_alias_proven": False,
        "metric_extrinsic_qualified": False,
        "timestamp_event_semantics_qualified": False,
        "physical_clock_accuracy": "UNVERIFIED",
        "real_factor_admission": "DENIED",
        "m2dgr_gates": "11_CLOSED",
    }

    return packet, frame, installed


class ReadinessTests(unittest.TestCase):

    def mutate(self, fn):
        packet, frame, installed = fixture()
        fn(packet, frame, installed)

        with self.assertRaises(MeasurementReadinessError):
            review_readiness(packet, frame, installed)

    def test_01_all_thirteen_requests_closed(self):
        result = review_readiness(*fixture())
        self.assertEqual(result["a23_request_count"], 13)
        self.assertEqual(
            result["request_counts_by_stage"],
            {"A": 2, "B": 6, "C": 3, "D": 2},
        )
        self.assertEqual(result["real_factor_count"], 0)

    def test_02_deterministic(self):
        self.assertEqual(
            review_readiness(*fixture()),
            review_readiness(*copy.deepcopy(fixture())),
        )

    def test_03_reject_fake_receipt(self):
        self.mutate(lambda p, f, s:
                    p["requests"][0].update(
                        qualifying_receipt_received=True))

    def test_04_reject_stage_authorization(self):
        self.mutate(lambda p, f, s:
                    p["stages"][0].update(stage_authorized=True))

    def test_05_reject_gate_opening(self):
        self.mutate(lambda p, f, s:
                    p["requests"][1].update(
                        scientific_gate_opened=True))

    def test_06_reject_physical_parameter(self):
        self.mutate(lambda p, f, s:
                    p["requests"][2].update(
                        physical_parameter_value=0.01))

    def test_07_reject_altered_request_count(self):
        self.mutate(lambda p, f, s:
                    p["requests"].pop())

    def test_08_reject_altered_request_id(self):
        self.mutate(lambda p, f, s:
                    p["requests"][0].update(
                        request_id="UNKNOWN"))

    def test_09_reject_independent_review_claim(self):
        self.mutate(lambda p, f, s:
                    p["requests"][0].update(
                        independent_review_status="VERIFIED"))

    def test_10_reject_changed_split(self):
        self.mutate(lambda p, f, s:
                    p["frozen_m2dgr_split"].update(
                        confirmation_test=6))

    def test_11_reject_holdout_claim(self):
        self.mutate(lambda p, f, s:
                    p.update(
                        confirmation_test_pristine_from_prior_inspection=True))

    def test_12_reject_scientific_permission(self):
        self.mutate(lambda p, f, s:
                    p["scientific_permissions"].update(
                        real_sensor_factor_admission="APPROVED"))

    def test_13_reject_invented_imu_transform(self):
        self.mutate(lambda p, f, s:
                    f.update(
                        bmi088_to_platform_transform=[0, 0, 0]))

    def test_14_reject_false_imu_equivalence(self):
        self.mutate(lambda p, f, s:
                    f.update(
                        bmi088_to_front_stereo_imu_equivalence="VERIFIED"))

    def test_15_reject_calibration_hash_drift(self):
        self.mutate(lambda p, f, s:
                    s["pinned_sha256"].update(
                        calibration_json="a" * 64))

    def test_16_reject_source_alias_proof(self):
        self.mutate(lambda p, f, s:
                    s.update(frame_alias_proven=True))

    def test_17_reject_clock_qualification(self):
        self.mutate(lambda p, f, s:
                    s.update(
                        timestamp_event_semantics_qualified=True))

    def test_18_reject_physical_extrinsic_claim(self):
        self.mutate(lambda p, f, s:
                    s.update(metric_extrinsic_qualified=True))

    def test_19_factor_admission_always_denied(self):
        with self.assertRaises(MeasurementReadinessError):
            admit_physical_measurements(*fixture())

    def test_20_no_ground_truth_claim(self):
        result = review_readiness(*fixture())
        self.assertFalse(result["physical_measurements_qualified"])
        self.assertEqual(
            result["independent_6dof_reference"], "UNVERIFIED"
        )
        self.assertEqual(result["real_factor_admission"], "DENIED")


if __name__ == "__main__":
    unittest.main()
