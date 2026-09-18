from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import json
import unittest

from trust_robot.data_contracts import (
    CalibrationArtifactRole,
)
from trust_robot.m2dgr_calibration_evidence import (
    M2DGRCalibrationEvidenceError,
    calibration_evidence_content_sha256,
    validate_m2dgr_calibration_evidence,
)
from trust_robot.trajectory_manifest import (
    validate_manifest_payload,
)


ROOT = Path(__file__).resolve().parents[2]

EVIDENCE = (
    ROOT
    / "manifests"
    / "m2dgr_calibration_evidence_v1.json"
)

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


class M2DGRCalibrationEvidenceTests(
    unittest.TestCase
):
    def test_permanent_evidence_validates(self):
        payload = json.loads(
            EVIDENCE.read_text(
                encoding="utf-8"
            )
        )

        validate_m2dgr_calibration_evidence(
            payload
        )

    def test_unsafe_calibration_upgrade_is_rejected(self):
        payload = json.loads(
            EVIDENCE.read_text(
                encoding="utf-8"
            )
        )

        payload = deepcopy(
            payload
        )

        payload[
            "interpretation"
        ][
            "dataset_calibration_verified"
        ] = True

        payload[
            "content_sha256"
        ] = (
            calibration_evidence_content_sha256(
                payload
            )
        )

        with self.assertRaises(
            M2DGRCalibrationEvidenceError
        ):
            validate_m2dgr_calibration_evidence(
                payload
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

    def test_rotation_support_does_not_become_full_calibration(
        self,
    ):
        payload = json.loads(
            EVIDENCE.read_text(
                encoding="utf-8"
            )
        )

        rotation = payload[
            "observations"
        ][
            "d435i_imu_relative_rotation"
        ]

        self.assertEqual(
            rotation[
                "published_greater_than_both_fixed_alternatives_count"
            ],
            28,
        )

        self.assertTrue(
            rotation[
                "sensor_content_support_observed"
            ]
        )

        self.assertFalse(
            rotation[
                "full_extrinsic_verified"
            ]
        )

        self.assertFalse(
            payload[
                "policy"
            ][
                "evaluation_ready"
            ]
        )


if __name__ == "__main__":
    unittest.main()
