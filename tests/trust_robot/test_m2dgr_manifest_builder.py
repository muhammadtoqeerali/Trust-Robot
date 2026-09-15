from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from trust_robot.data_contracts import ReferenceCoverage
from trust_robot.m2dgr_manifest_builder import build_reference
from trust_robot.m2dgr_reference_quality import (
    build_m2dgr_reference_quality_payload,
)
from trust_robot.reference_quality import (
    write_immutable_reference_quality_artifact,
)


class M2DGRManifestBuilderTests(unittest.TestCase):
    def _prepare_reference(self, root: Path, trajectory_id: str, rows: str):
        gt_root = root / "raw" / "ground_truth"
        gt_root.mkdir(parents=True, exist_ok=True)
        gt = gt_root / f"{trajectory_id}.txt"
        gt.write_text(rows, encoding="ascii")

        payload = build_m2dgr_reference_quality_payload(
            gt,
            trajectory_id=trajectory_id,
        )

        quality = (
            root
            / "audit"
            / "reference_quality"
            / f"{trajectory_id}_reference_quality.json"
        )
        write_immutable_reference_quality_artifact(quality, payload)
        return gt, quality

    def test_reference_requires_quality_artifact(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            gt_root = root / "raw" / "ground_truth"
            gt_root.mkdir(parents=True)
            gt = gt_root / "room_01.txt"
            gt.write_text(
                "1.0 0 0 0 0 0 0 1\n"
                "1.02 0 0 0 0 0 0 1\n",
                encoding="ascii",
            )

            with self.assertRaises(FileNotFoundError):
                build_reference(root, gt, "room_01")

    def test_mocap_reference_uses_quality_artifact_and_unknown_coverage(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            gt, quality = self._prepare_reference(
                root,
                "room_01",
                "1.0 0 0 0 0 0 0 1\n"
                "1.02 0 0 0 0 0 0 1\n",
            )

            reference = build_reference(root, gt, "room_01")

            expected = quality.relative_to(root).as_posix()
            self.assertEqual(reference.coverage, ReferenceCoverage.UNKNOWN)
            self.assertEqual(
                reference.translation_coverage,
                ReferenceCoverage.UNKNOWN,
            )
            self.assertEqual(
                reference.rotation_coverage,
                ReferenceCoverage.UNKNOWN,
            )
            self.assertEqual(reference.translation_validity_artifact, expected)
            self.assertEqual(reference.rotation_validity_artifact, expected)

    def test_leica_reference_is_translation_only_without_dummy_interval(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            gt, quality = self._prepare_reference(
                root,
                "lift_01",
                "1.0 0 0 0 0 0 0 0\n"
                "1.14 1 0 0 0 0 0 0\n",
            )

            reference = build_reference(root, gt, "lift_01")

            self.assertTrue(reference.supports_translation)
            self.assertFalse(reference.supports_rotation)
            self.assertEqual(
                reference.translation_validity_artifact,
                quality.relative_to(root).as_posix(),
            )
            self.assertIsNone(reference.rotation_validity_artifact)
            self.assertEqual(reference.coverage, ReferenceCoverage.UNKNOWN)


if __name__ == "__main__":
    unittest.main()
