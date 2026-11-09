import copy
import unittest

from trust_robot.prospective_health_evidence_intake_v1 import (
    SCHEMA, MODALITIES, LIDAR_ROLES, GENERIC_ROLES,
    HealthIntakeError, build_empty_candidate,
    audit_candidate, build_three_modality_gap_report, content_sha256,
)


class ProspectiveHealthIntakeTests(unittest.TestCase):
    def base(self, modality="lidar"):
        return build_empty_candidate("candidate_01", modality)

    def bad(self, patch, modality="lidar"):
        obj = self.base(modality)
        patch(obj)
        with self.assertRaises(HealthIntakeError):
            audit_candidate(obj)

    def test_lidar_no_evidence_is_blocked(self):
        result = audit_candidate(self.base())
        self.assertEqual(len(result["evidence_roles_missing"]), len(LIDAR_ROLES))
        self.assertFalse(result["model_training_authorized"])

    def test_camera_no_evidence_is_blocked(self):
        r = audit_candidate(self.base("camera"))
        self.assertEqual(len(r["evidence_roles_missing"]), len(GENERIC_ROLES))
        self.assertIn("NOT_RESOLVED", r["source_specific_protocol_status"])

    def test_imu_no_evidence_is_blocked(self):
        self.assertFalse(audit_candidate(self.base("imu"))["health_supervision_source_accepted"])

    def test_all_modalities_listed(self):
        self.assertEqual(MODALITIES, ("camera", "imu", "lidar"))

    def test_candidate_complete_shapes_never_accepts(self):
        obj = self.base()
        for i, role in enumerate(LIDAR_ROLES):
            obj["independent_artifact_sha256_by_role"][role] = f"{i + 1:064x}"
        r = audit_candidate(obj)
        self.assertEqual(r["evidence_roles_missing"], [])
        self.assertFalse(r["artifact_bytes_verified"])
        self.assertFalse(r["evidence_independence_verified"])
        self.assertFalse(r["health_supervision_source_accepted"])
        self.assertFalse(r["model_training_authorized"])

    def test_one_digest_remains_missing(self):
        obj = self.base()
        obj["independent_artifact_sha256_by_role"][LIDAR_ROLES[0]] = "a" * 64
        self.assertEqual(len(audit_candidate(obj)["evidence_roles_missing"]), 6)

    def test_duplicate_digest_rejected(self):
        def p(x):
            x["independent_artifact_sha256_by_role"][LIDAR_ROLES[0]] = "a" * 64
            x["independent_artifact_sha256_by_role"][LIDAR_ROLES[1]] = "a" * 64
        self.bad(p)

    def test_short_digest_rejected(self):
        self.bad(lambda x: x["independent_artifact_sha256_by_role"].update({LIDAR_ROLES[0]:"a" * 63}))

    def test_uppercase_digest_rejected(self):
        self.bad(lambda x: x["independent_artifact_sha256_by_role"].update({LIDAR_ROLES[0]:"A" * 64}))

    def test_unsafe_source_identifier_rejected(self):
        self.bad(lambda x: x.update(source_id="/private/path"))

    def test_unknown_source_id_rejected(self):
        self.bad(lambda x: x.update(source_id=""))

    def test_confirmation_forbidden(self):
        self.bad(lambda x: x.update(split_role="confirmation_test"))

    def test_validation_forbidden(self):
        self.bad(lambda x: x.update(split_role="validation_calibration"))

    def test_fake_health_label_claim_forbidden(self):
        self.bad(lambda x: x.update(real_health_labels_assigned=True))

    def test_source_acceptance_claim_forbidden(self):
        self.bad(lambda x: x.update(source_accepted=True))

    def test_robot_action_claim_forbidden(self):
        self.bad(lambda x: x.update(physical_action_authorized=True))

    def test_unexpected_role_rejected(self):
        self.bad(lambda x: x["independent_artifact_sha256_by_role"].update(fake="0" * 64))

    def test_missing_role_rejected(self):
        self.bad(lambda x: x["independent_artifact_sha256_by_role"].pop(LIDAR_ROLES[0]))

    def test_other_sensor_uses_different_protocol(self):
        self.bad(lambda x: x.update(source_protocol="vlp32c_controlled_availability_prospective"), "camera")

    def test_nova_lidar_not_assumed_vlp(self):
        self.bad(lambda x: x.update(source_protocol="unspecified_robot_lidar"))

    def test_non_mapping_rejected(self):
        with self.assertRaises(HealthIntakeError):
            audit_candidate([])

    def test_extra_field_rejected(self):
        self.bad(lambda x: x.update(health_label="healthy"))

    def test_schema_changed_rejected(self):
        self.bad(lambda x: x.update(schema="FAKE"))

    def test_boolean_digest_rejected(self):
        self.bad(lambda x: x["independent_artifact_sha256_by_role"].update({LIDAR_ROLES[0]:True}))

    def test_report_deterministic_and_content_bound(self):
        a = build_three_modality_gap_report()
        b = build_three_modality_gap_report()
        self.assertEqual(a, b)
        self.assertEqual(a["content_sha256"], content_sha256(a))
        self.assertEqual(len(a["candidate_reviews"]), 3)

    def test_report_never_claims_evidence(self):
        r = build_three_modality_gap_report()
        self.assertEqual(r["real_health_labels"], 0)
        self.assertEqual(r["health_model_training"], "BLOCKED")
        self.assertEqual(r["operational_supervisor_execution"], "DENIED")
        self.assertFalse(r["confirmation_access"])

    def test_original_candidate_not_mutated(self):
        x = self.base(); y = copy.deepcopy(x)
        audit_candidate(x)
        self.assertEqual(x, y)


if __name__ == "__main__":
    unittest.main()
