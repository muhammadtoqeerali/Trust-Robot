
import unittest

from trust_robot.reference_coverage import (
    CoverageError,
    ReferenceCoverageArtifact,
    ReferenceDimension,
    ValidInterval,
    validate_leica_reference,
    validate_reference_dimension,
)


class ReferenceCoverageTests(unittest.TestCase):

    def test_translation_reference_passes(self):

        artifact = ReferenceCoverageArtifact(
            trajectory_id="door_01",
            reference_source="Leica",
            translation_valid=True,
            rotation_valid=False,
            valid_intervals=(
                ValidInterval(0,100),
            ),
        )

        validate_reference_dimension(
            artifact,
            ReferenceDimension.TRANSLATION,
        )


    def test_rotation_requires_rotation_reference(self):

        artifact = ReferenceCoverageArtifact(
            trajectory_id="door_01",
            reference_source="Leica",
            translation_valid=True,
            rotation_valid=False,
            valid_intervals=(
                ValidInterval(0,100),
            ),
        )

        with self.assertRaises(CoverageError):

            validate_reference_dimension(
                artifact,
                ReferenceDimension.ROTATION,
            )


    def test_leica_cannot_claim_rotation(self):

        artifact = ReferenceCoverageArtifact(
            trajectory_id="door_01",
            reference_source="Leica",
            translation_valid=True,
            rotation_valid=True,
            valid_intervals=(
                ValidInterval(0,100),
            ),
        )

        with self.assertRaises(CoverageError):

            validate_leica_reference(
                artifact
            )


if __name__ == "__main__":
    unittest.main()
