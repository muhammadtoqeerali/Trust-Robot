from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import json
import unittest

from trust_robot.m2dgr_reference_temporal_association_evidence import (
    M2DGRReferenceTemporalAssociationEvidenceError,
    reference_temporal_association_evidence_content_sha256,
    validate_m2dgr_reference_temporal_association_evidence,
)


ROOT = Path(__file__).resolve().parents[2]

EVIDENCE = (
    ROOT
    / "manifests"
    / "m2dgr_reference_temporal_association_evidence_v1.json"
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


def file_sha256(path: Path) -> str:
    digest = sha256()

    with path.open("rb") as handle:
        for block in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(block)

    return digest.hexdigest()


class M2DGRReferenceTemporalAssociationEvidenceTests(
    unittest.TestCase
):
    def test_permanent_evidence_validates(self):
        payload = json.loads(
            EVIDENCE.read_text(
                encoding="utf-8"
            )
        )

        validate_m2dgr_reference_temporal_association_evidence(
            payload
        )

    def test_unsafe_policy_tamper_is_rejected(self):
        payload = json.loads(
            EVIDENCE.read_text(
                encoding="utf-8"
            )
        )

        payload = deepcopy(
            payload
        )

        payload[
            "policy"
        ][
            "evaluation_ready"
        ] = True

        payload[
            "content_sha256"
        ] = (
            reference_temporal_association_evidence_content_sha256(
                payload
            )
        )

        with self.assertRaises(
            M2DGRReferenceTemporalAssociationEvidenceError
        ):
            validate_m2dgr_reference_temporal_association_evidence(
                payload
            )

    def test_phase3d_manifest_remains_byte_identical(self):
        self.assertEqual(
            file_sha256(
                PHASE3D_MANIFEST
            ),
            EXPECTED_PHASE3D_FILE_SHA256,
        )

        payload = json.loads(
            EVIDENCE.read_text(
                encoding="utf-8"
            )
        )

        self.assertFalse(
            payload[
                "manifest_semantics"
            ][
                "trajectory_manifest_modified"
            ]
        )

        self.assertFalse(
            payload[
                "manifest_semantics"
            ][
                "successor_manifest_created"
            ]
        )


if __name__ == "__main__":
    unittest.main()
