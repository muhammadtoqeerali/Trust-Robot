import math
import tempfile
import unittest
from pathlib import Path

from trust_robot.m2dgr_reference import (
    M2DGRReferenceError,
    M2DGRReferenceFamily,
    audit_m2dgr_reference,
    infer_reference_family,
    reference_validity_artifact_dict,
    write_reference_validity_artifact,
)


class TemporaryReference:
    def __init__(
        self,
        testcase,
        name,
        rows,
    ):
        self._testcase = testcase
        self._tmp = tempfile.TemporaryDirectory()

        self.path = (
            Path(self._tmp.name)
            / name
        )

        self.path.write_text(
            "\n".join(rows) + "\n",
            encoding="ascii",
        )

        testcase.addCleanup(
            self._tmp.cleanup
        )


class FamilyTests(unittest.TestCase):
    def test_rtk_ins_families(self):
        for name in (
            "street_01",
            "Circle_01",
            "gate_03",
            "walk_01",
        ):
            self.assertEqual(
                infer_reference_family(name),
                M2DGRReferenceFamily.RTK_INS,
            )

    def test_leica_families(self):
        for name in (
            "hall_01",
            "door_02",
            "lift_04",
        ):
            self.assertEqual(
                infer_reference_family(name),
                M2DGRReferenceFamily.LEICA,
            )

    def test_mocap_families(self):
        for name in (
            "room_01",
            "room_dark_06",
            "roomdark_06",
        ):
            self.assertEqual(
                infer_reference_family(name),
                M2DGRReferenceFamily.MOCAP,
            )

    def test_unknown_family_is_rejected(self):
        with self.assertRaises(
            M2DGRReferenceError
        ):
            infer_reference_family(
                "mystery_01"
            )


class StructuralAuditTests(unittest.TestCase):
    def test_valid_full_pose_reference(self):
        ref = TemporaryReference(
            self,
            "gate_01.txt",
            (
                "1.00 1 2 3 0 0 0 1",
                "1.01 2 3 4 0 0 0 1",
            ),
        )

        audit = audit_m2dgr_reference(
            ref.path
        )

        self.assertEqual(
            audit.row_count,
            2,
        )

        self.assertEqual(
            audit.invalid_translation_sample_indices,
            (),
        )

        self.assertEqual(
            audit.invalid_rotation_sample_indices,
            (),
        )

        self.assertEqual(
            audit.rotation_valid_count,
            2,
        )

    def test_leica_zero_quaternion_is_unsupported_not_invalid(self):
        ref = TemporaryReference(
            self,
            "door_02.txt",
            (
                "1.00 1 2 3 0 0 0 0",
                "1.10 2 3 4 0 0 0 0",
            ),
        )

        audit = audit_m2dgr_reference(
            ref.path
        )

        self.assertEqual(
            audit.family,
            M2DGRReferenceFamily.LEICA,
        )

        self.assertTrue(
            audit.translation_supported
        )

        self.assertFalse(
            audit.rotation_supported
        )

        self.assertEqual(
            audit.invalid_rotation_sample_indices,
            (),
        )

        self.assertIsNone(
            audit.rotation_valid_count
        )

    def test_bad_qnorm_invalidates_rotation_only(self):
        ref = TemporaryReference(
            self,
            "room_01.txt",
            (
                "1.00 1 2 3 0 0 0 1",
                "1.02 4 5 6 0 0 5 1",
                "1.04 7 8 9 0 0 0 1",
            ),
        )

        audit = audit_m2dgr_reference(
            ref.path
        )

        self.assertEqual(
            audit.invalid_translation_sample_indices,
            (),
        )

        self.assertEqual(
            audit.invalid_rotation_sample_indices,
            (1,),
        )

        self.assertEqual(
            audit.translation_valid_count,
            3,
        )

        self.assertEqual(
            audit.rotation_valid_count,
            2,
        )

    def test_nonfinite_position_does_not_invalidate_good_rotation(self):
        ref = TemporaryReference(
            self,
            "room_01.txt",
            (
                "1.00 1 2 3 0 0 0 1",
                "1.02 nan 5 6 0 0 0 1",
            ),
        )

        audit = audit_m2dgr_reference(
            ref.path
        )

        self.assertEqual(
            audit.invalid_translation_sample_indices,
            (1,),
        )

        self.assertEqual(
            audit.invalid_rotation_sample_indices,
            (),
        )

    def test_nonfinite_quaternion_does_not_invalidate_position(self):
        ref = TemporaryReference(
            self,
            "room_01.txt",
            (
                "1.00 1 2 3 0 0 0 1",
                "1.02 4 5 6 0 nan 0 1",
            ),
        )

        audit = audit_m2dgr_reference(
            ref.path
        )

        self.assertEqual(
            audit.invalid_translation_sample_indices,
            (),
        )

        self.assertEqual(
            audit.invalid_rotation_sample_indices,
            (1,),
        )

    def test_nonmonotonic_timestamp_is_rejected(self):
        ref = TemporaryReference(
            self,
            "gate_01.txt",
            (
                "1.00 1 2 3 0 0 0 1",
                "1.00 2 3 4 0 0 0 1",
            ),
        )

        with self.assertRaises(
            M2DGRReferenceError
        ):
            audit_m2dgr_reference(
                ref.path
            )

    def test_wrong_field_count_is_rejected(self):
        ref = TemporaryReference(
            self,
            "gate_01.txt",
            (
                "1.00 1 2 3 0 0 1",
            ),
        )

        with self.assertRaises(
            M2DGRReferenceError
        ):
            audit_m2dgr_reference(
                ref.path
            )

    def test_q_and_negative_q_have_zero_rotation_step(self):
        ref = TemporaryReference(
            self,
            "room_01.txt",
            (
                "1.00 1 2 3 0 0 0 1",
                "1.02 1 2 3 0 0 0 -1",
            ),
        )

        audit = audit_m2dgr_reference(
            ref.path
        )

        self.assertIsNotNone(
            audit.rotation_step_max_deg
        )

        self.assertTrue(
            math.isclose(
                audit.rotation_step_max_deg,
                0.0,
                abs_tol=1e-12,
            )
        )

    def test_qnorm_tolerance_is_explicit(self):
        ref = TemporaryReference(
            self,
            "room_01.txt",
            (
                "1.00 1 2 3 0 0 0 1.0005",
            ),
        )

        accepted = audit_m2dgr_reference(
            ref.path,
            qnorm_tolerance=1e-3,
        )

        rejected = audit_m2dgr_reference(
            ref.path,
            qnorm_tolerance=1e-4,
        )

        self.assertEqual(
            accepted.invalid_rotation_sample_indices,
            (),
        )

        self.assertEqual(
            rejected.invalid_rotation_sample_indices,
            (0,),
        )



class ArtifactTests(unittest.TestCase):
    def test_artifact_is_dimension_specific(self):
        ref = TemporaryReference(
            self,
            "room_01.txt",
            (
                "1.00 1 2 3 0 0 0 1",
                "1.02 4 5 6 0 0 5 1",
            ),
        )

        audit = audit_m2dgr_reference(
            ref.path
        )

        artifact = (
            reference_validity_artifact_dict(
                audit,
                source_relpath=(
                    "raw/ground_truth/"
                    "room_01.txt"
                ),
            )
        )

        self.assertEqual(
            artifact["translation"][
                "invalid_sample_indices"
            ],
            [],
        )

        self.assertEqual(
            artifact["rotation"][
                "invalid_sample_indices"
            ],
            [1],
        )

        self.assertFalse(
            artifact["policy"][
                "raw_source_modified"
            ]
        )

        self.assertTrue(
            artifact["policy"][
                "rotation_continuity_is_diagnostic_only"
            ]
        )

    def test_absolute_source_path_is_rejected(self):
        ref = TemporaryReference(
            self,
            "gate_01.txt",
            (
                "1.00 1 2 3 0 0 0 1",
            ),
        )

        audit = audit_m2dgr_reference(
            ref.path
        )

        with self.assertRaises(
            M2DGRReferenceError
        ):
            reference_validity_artifact_dict(
                audit,
                source_relpath=(
                    "/machine/specific/"
                    "gate_01.txt"
                ),
            )

    def test_artifact_writer_is_deterministic(self):
        import hashlib

        ref = TemporaryReference(
            self,
            "gate_01.txt",
            (
                "1.00 1 2 3 0 0 0 1",
                "1.01 2 3 4 0 0 0 1",
            ),
        )

        audit = audit_m2dgr_reference(
            ref.path
        )

        with tempfile.TemporaryDirectory() as tmp:
            destination = (
                Path(tmp)
                / "gate_01.json"
            )

            write_reference_validity_artifact(
                audit,
                destination,
                source_relpath=(
                    "raw/ground_truth/"
                    "gate_01.txt"
                ),
            )

            first = hashlib.sha256(
                destination.read_bytes()
            ).hexdigest()

            write_reference_validity_artifact(
                audit,
                destination,
                source_relpath=(
                    "raw/ground_truth/"
                    "gate_01.txt"
                ),
            )

            second = hashlib.sha256(
                destination.read_bytes()
            ).hexdigest()

            self.assertEqual(
                first,
                second,
            )


if __name__ == "__main__":
    unittest.main()
