from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from trust_robot.reference_quality import (
    ReferenceQualityError,
    build_reference_quality_payload,
    load_reference_quality_artifact,
    reference_quality_sha256,
    validate_reference_quality_payload,
    write_immutable_reference_quality_artifact,
)


SOURCE_SHA = "a" * 64


def make_payload(
    *,
    translation=(True, True, True, True),
    rotation_supported=True,
    rotation=(True, True, True, True),
):
    return build_reference_quality_payload(
        trajectory_id="synthetic_001",
        reference_source="mocap",
        source_relative_path="raw/ground_truth/synthetic_001.txt",
        source_sha256=SOURCE_SHA,
        timestamps_seconds=(10.0, 10.02, 10.04, 10.06),
        translation_valid_mask=translation,
        rotation_supported=rotation_supported,
        rotation_valid_mask=rotation if rotation_supported else None,
        timestamp_checks={
            "strictly_increasing": True,
        },
        continuity_checks={
            "diagnostic_only": True,
        },
    )


class ReferenceQualityTests(unittest.TestCase):
    def test_bad_mask_length_is_rejected(self):
        with self.assertRaises(ReferenceQualityError):
            build_reference_quality_payload(
                trajectory_id="synthetic_001",
                reference_source="mocap",
                source_relative_path="raw/ground_truth/synthetic_001.txt",
                source_sha256=SOURCE_SHA,
                timestamps_seconds=(1.0, 2.0),
                translation_valid_mask=(True,),
                rotation_supported=False,
                rotation_valid_mask=None,
                timestamp_checks={},
                continuity_checks={},
            )

    def test_dimension_specific_sample_runs_are_preserved(self):
        payload = make_payload(
            translation=(True, True, False, True),
            rotation=(True, False, False, True),
        )

        translation = payload["translation_validity"]
        rotation = payload["rotation_validity"]

        self.assertEqual(translation["invalid_count"], 1)
        self.assertEqual(rotation["invalid_count"], 2)

        self.assertEqual(
            translation["invalid_sample_runs"],
            [
                {
                    "start_sample_index": 2,
                    "end_sample_index": 2,
                    "start_timestamp_seconds": 10.04,
                    "end_timestamp_seconds": 10.04,
                }
            ],
        )

        self.assertEqual(
            rotation["invalid_sample_runs"][0]["start_sample_index"],
            1,
        )
        self.assertEqual(
            rotation["invalid_sample_runs"][0]["end_sample_index"],
            2,
        )

    def test_sample_runs_do_not_claim_continuous_time_coverage(self):
        payload = make_payload()

        self.assertIn(
            "do not imply valid interpolation",
            payload["sample_run_semantics"],
        )
        self.assertFalse(payload["continuous_time_coverage"]["verified"])
        self.assertIn(
            "continuous_time_reference_coverage_not_verified",
            payload["quality_summary"]["blockers"],
        )

    def test_immutable_writer_digest_and_loader_are_deterministic(self):
        payload = make_payload()
        digest = reference_quality_sha256(payload)

        self.assertEqual(
            digest,
            payload["reference_quality_content_sha256"],
        )

        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "quality.json"
            first = write_immutable_reference_quality_artifact(path, payload)
            second = write_immutable_reference_quality_artifact(path, payload)

            self.assertEqual(first, second)
            loaded = load_reference_quality_artifact(path)
            self.assertEqual(loaded, payload)

            parsed = json.loads(path.read_text(encoding="utf-8"))
            validate_reference_quality_payload(parsed)

    def test_tampered_payload_is_rejected(self):
        payload = make_payload()
        tampered = deepcopy(payload)
        tampered["sample_count"] = 99

        with self.assertRaises(ReferenceQualityError):
            validate_reference_quality_payload(tampered)

    def test_leica_style_rotation_can_be_explicitly_unsupported(self):
        payload = make_payload(
            rotation_supported=False,
            rotation=None,
        )

        rotation = payload["rotation_validity"]
        self.assertFalse(rotation["supported"])
        self.assertIsNone(rotation["valid_count"])
        self.assertEqual(rotation["valid_sample_runs"], [])

    def test_quality_is_not_evaluation_ready_without_independent_evidence(self):
        payload = make_payload()
        summary = payload["quality_summary"]

        self.assertFalse(summary["evaluation_ready"])
        self.assertIn(
            "physical_reference_quality_not_independently_verified",
            summary["blockers"],
        )
        self.assertIn(
            "reference_to_estimator_synchronization_not_verified",
            summary["blockers"],
        )

    def test_verified_claims_require_evidence(self):
        with self.assertRaises(ReferenceQualityError):
            build_reference_quality_payload(
                trajectory_id="synthetic_001",
                reference_source="mocap",
                source_relative_path="raw/ground_truth/synthetic_001.txt",
                source_sha256=SOURCE_SHA,
                timestamps_seconds=(1.0, 2.0),
                translation_valid_mask=(True, True),
                rotation_supported=False,
                rotation_valid_mask=None,
                timestamp_checks={},
                continuity_checks={},
                physical_quality_verified=True,
            )


if __name__ == "__main__":
    unittest.main()
