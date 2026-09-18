from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import json
import unittest

from trust_robot.m2dgr_split_freeze_evidence import (
    M2DGRSplitFreezeEvidenceError,
    split_freeze_evidence_content_sha256,
    validate_m2dgr_split_freeze_evidence,
)
from trust_robot.trajectory_manifest import (
    validate_manifest_payload,
)


ROOT = Path(__file__).resolve().parents[2]

SOURCE = (
    ROOT
    / "manifests"
    / "m2dgr_trajectory_manifest_v1_phase3d_lidar_imu_sync_evidence.json"
)

SUCCESSOR = (
    ROOT
    / "manifests"
    / "m2dgr_trajectory_manifest_v1_split_freeze_v1.json"
)

EVIDENCE = (
    ROOT
    / "manifests"
    / "m2dgr_split_freeze_evidence_v1.json"
)


EXPECTED_SOURCE_FILE_SHA = (
    "67fe08bff676689dd212da03dce8e16e"
    "cee277c96f38f752d0d38a5e4e54cf6f"
)


def load(path):
    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def file_sha256(path):
    digest = sha256()

    digest.update(
        path.read_bytes()
    )

    return digest.hexdigest()


class M2DGRSplitFreezeEvidenceTests(
    unittest.TestCase
):
    def test_permanent_evidence_validates(self):
        validate_m2dgr_split_freeze_evidence(
            load(EVIDENCE)
        )

    def test_successor_manifest_validates(self):
        validate_manifest_payload(
            load(SUCCESSOR)
        )

    def test_historical_source_remains_byte_identical(self):
        self.assertEqual(
            file_sha256(SOURCE),
            EXPECTED_SOURCE_FILE_SHA,
        )

    def test_successor_changes_only_split_fields(self):
        source = load(SOURCE)
        successor = load(SUCCESSOR)

        source.pop(
            "manifest_content_sha256"
        )

        successor.pop(
            "manifest_content_sha256"
        )

        source_records = {
            row["trajectory_id"]:
                row
            for row in source["records"]
        }

        successor_records = {
            row["trajectory_id"]:
                row
            for row in successor["records"]
        }

        self.assertEqual(
            set(source_records),
            set(successor_records),
        )

        changed = []

        for trajectory_id in sorted(
            source_records
        ):
            left = deepcopy(
                source_records[
                    trajectory_id
                ]
            )

            right = deepcopy(
                successor_records[
                    trajectory_id
                ]
            )

            if (
                left["split"]
                != right["split"]
            ):
                changed.append(
                    trajectory_id
                )

            left.pop("split")
            right.pop("split")

            self.assertEqual(
                left,
                right,
            )

        self.assertEqual(
            len(changed),
            14,
        )

    def test_successor_matches_frozen_assignment(self):
        evidence = load(EVIDENCE)
        successor = load(SUCCESSOR)

        observed = {
            role:
                sorted(
                    row["trajectory_id"]
                    for row in successor[
                        "records"
                    ]
                    if row["split"]
                    == role
                )
            for role in (
                "train",
                "validation_calibration",
                "confirmation_test",
            )
        }

        expected = {
            role:
                sorted(ids)
            for role, ids in (
                evidence[
                    "split_assignment"
                ].items()
            )
        }

        self.assertEqual(
            observed,
            expected,
        )

    def test_confirmation_cannot_be_reopened_for_selection(self):
        payload = deepcopy(
            load(EVIDENCE)
        )

        payload[
            "prospective_holdout_policy"
        ][
            "confirmation_test_available_for_future_protocol_selection"
        ] = True

        payload[
            "content_sha256"
        ] = (
            split_freeze_evidence_content_sha256(
                payload
            )
        )

        with self.assertRaises(
            M2DGRSplitFreezeEvidenceError
        ):
            validate_m2dgr_split_freeze_evidence(
                payload
            )

    def test_split_does_not_make_evaluation_ready(self):
        payload = deepcopy(
            load(EVIDENCE)
        )

        payload[
            "authorization"
        ][
            "evaluation_ready"
        ] = True

        payload[
            "content_sha256"
        ] = (
            split_freeze_evidence_content_sha256(
                payload
            )
        )

        with self.assertRaises(
            M2DGRSplitFreezeEvidenceError
        ):
            validate_m2dgr_split_freeze_evidence(
                payload
            )


if __name__ == "__main__":
    unittest.main()
