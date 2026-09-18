from hashlib import sha256
from pathlib import Path
import json
import unittest

from trust_robot.data_contracts import (
    CalibrationArtifactRole,
    CalibrationArtifactSpec,
    ContractError,
    VerificationStatus,
)
from trust_robot.trajectory_manifest import (
    _calibration_dict,
    _decode_calibration_artifact,
    validate_manifest_payload,
)


ROOT = Path(__file__).resolve().parents[2]

PHASE3D_MANIFEST = (
    ROOT
    / "manifests"
    / "m2dgr_trajectory_manifest_v1_phase3d_lidar_imu_sync_evidence.json"
)

EXPECTED_PHASE3D_FILE_SHA256 = (
    "67fe08bff676689dd212da03dce8e16ec"
    "ee277c96f38f752d0d38a5e4e54cf6f"
)


def file_sha256(
    path: Path,
) -> str:
    digest = sha256()

    with path.open("rb") as handle:
        for block in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(block)

    return digest.hexdigest()


def legacy_artifact() -> CalibrationArtifactSpec:
    return CalibrationArtifactSpec(
        artifact_id="bag_sha256",
        source_path="raw/example.bag",
        sha256="0" * 64,
        verification_status=VerificationStatus.VERIFIED,
        notes="raw bag integrity artifact",
    )


class CalibrationArtifactSemanticsTests(
    unittest.TestCase
):
    def test_legacy_default_is_integrity_only(self):
        artifact = legacy_artifact()

        self.assertEqual(
            artifact.role,
            CalibrationArtifactRole.ARTIFACT_INTEGRITY,
        )

        self.assertFalse(
            artifact.establishes_sensor_calibration
        )

    def test_calibration_provenance_does_not_establish_calibration(
        self,
    ):
        artifact = CalibrationArtifactSpec(
            artifact_id="author_calibration",
            source_path="metadata/calibration.txt",
            sha256="1" * 64,
            verification_status=VerificationStatus.VERIFIED,
            role=CalibrationArtifactRole.CALIBRATION_PROVENANCE,
        )

        self.assertFalse(
            artifact.establishes_sensor_calibration
        )

    def test_sensor_calibration_verification_requires_verified_status(
        self,
    ):
        with self.assertRaises(
            ContractError
        ):
            CalibrationArtifactSpec(
                artifact_id="candidate",
                source_path="audit/calibration.json",
                sha256="2" * 64,
                verification_status=VerificationStatus.UNVERIFIED,
                applies_to_stream_ids=(
                    "/camera/imu",
                ),
                role=(
                    CalibrationArtifactRole.
                    SENSOR_CALIBRATION_VERIFICATION
                ),
            )

    def test_sensor_calibration_verification_requires_scope(
        self,
    ):
        with self.assertRaises(
            ContractError
        ):
            CalibrationArtifactSpec(
                artifact_id="candidate",
                source_path="audit/calibration.json",
                sha256="3" * 64,
                verification_status=VerificationStatus.VERIFIED,
                role=(
                    CalibrationArtifactRole.
                    SENSOR_CALIBRATION_VERIFICATION
                ),
            )

    def test_scoped_verified_sensor_calibration_establishes_calibration(
        self,
    ):
        artifact = CalibrationArtifactSpec(
            artifact_id="imu_rotation_verification",
            source_path="audit/calibration.json",
            sha256="4" * 64,
            verification_status=VerificationStatus.VERIFIED,
            applies_to_stream_ids=(
                "/camera/imu",
                "/handsfree/imu",
            ),
            role=(
                CalibrationArtifactRole.
                SENSOR_CALIBRATION_VERIFICATION
            ),
        )

        self.assertTrue(
            artifact.establishes_sensor_calibration
        )

    def test_legacy_serializer_omits_role(self):
        payload = _calibration_dict(
            legacy_artifact()
        )

        self.assertNotIn(
            "role",
            payload,
        )

        decoded = _decode_calibration_artifact(
            payload
        )

        self.assertEqual(
            decoded.role,
            CalibrationArtifactRole.ARTIFACT_INTEGRITY,
        )

        self.assertFalse(
            decoded.establishes_sensor_calibration
        )

    def test_role_aware_serializer_is_additive(self):
        artifact = CalibrationArtifactSpec(
            artifact_id="published_calibration",
            source_path="metadata/calibration.txt",
            sha256="5" * 64,
            verification_status=VerificationStatus.VERIFIED,
            applies_to_frame_ids=(
                "camera_imu_optical_frame",
            ),
            role=CalibrationArtifactRole.CALIBRATION_PROVENANCE,
        )

        payload = _calibration_dict(
            artifact
        )

        self.assertEqual(
            payload[
                "role"
            ],
            "calibration_provenance",
        )

        decoded = _decode_calibration_artifact(
            payload
        )

        self.assertEqual(
            decoded,
            artifact,
        )

        self.assertFalse(
            decoded.establishes_sensor_calibration
        )

    def test_phase3d_manifest_remains_byte_identical_and_integrity_only(
        self,
    ):
        self.assertEqual(
            file_sha256(
                PHASE3D_MANIFEST
            ),
            EXPECTED_PHASE3D_FILE_SHA256,
        )

        payload = json.loads(
            PHASE3D_MANIFEST.read_text(
                encoding="utf-8"
            )
        )

        records = validate_manifest_payload(
            payload
        )

        artifacts = [
            artifact
            for record in records
            for artifact in record.calibration_artifacts
        ]

        self.assertEqual(
            len(
                artifacts
            ),
            36,
        )

        self.assertTrue(
            all(
                artifact.role
                is CalibrationArtifactRole.ARTIFACT_INTEGRITY
                for artifact in artifacts
            )
        )

        self.assertFalse(
            any(
                artifact.establishes_sensor_calibration
                for artifact in artifacts
            )
        )


if __name__ == "__main__":
    unittest.main()
