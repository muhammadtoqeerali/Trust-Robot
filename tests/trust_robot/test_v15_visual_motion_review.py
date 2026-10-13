import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from trust_robot.v15_visual_motion_review import (
    review_v15,
)


def make_v15(folder):
    root = Path(folder)
    recording = root / "recording"
    recording.mkdir()

    frames = recording / "frames_v15"
    frames.mkdir()

    rng = np.random.default_rng(321)
    base = rng.integers(
        0, 256, (120, 160, 3), dtype=np.uint8
    )

    rows = []
    hashes = {}

    for i in range(1, 7):
        rgb = np.roll(
            base, (0, i-1), axis=(0, 1)
        )
        rgba = np.concatenate(
            (
                rgb,
                np.full(
                    (120, 160, 1),
                    255,
                    dtype=np.uint8,
                ),
            ),
            axis=2,
        )

        name = f"frames_v15/camera_{i:03d}.npy"
        path = recording / name

        np.save(path, rgba, allow_pickle=False)

        hashes[name] = {
            "sha256": hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
        }

        rows.append({
            "step": 21+10*i,
            "camera_file": name,
            "camera_read_step_time_s": float(i),
            "acquisition_timing_verified": False,
            "cross_sensor_synchronization_verified": False,
        })

    index_path = recording / "capture_index_v15.json"

    index_path.write_text(
        json.dumps(rows, sort_keys=True) + "\n"
    )

    evidence_path = root / "compact_evidence.json"

    evidence_path.write_text(json.dumps({
        "schema": (
            "TRUST_ROBOT_ISAACSIM_V15_COMPACT_EVIDENCE_V1"
        ),
        "data_origin": "SYNTHETIC",
        "camera_frames": 6,
        "capture_index_sha256": hashlib.sha256(
            index_path.read_bytes()
        ).hexdigest(),
        "frame_files": hashes,
    }, sort_keys=True) + "\n")

    return recording, evidence_path


class V15VisualReviewTests(unittest.TestCase):

    def test_six_actual_image_arrays_reviewed(self):
        with tempfile.TemporaryDirectory() as folder:
            recording, evidence = make_v15(folder)
            row = review_v15(recording, evidence)
            self.assertEqual(
                row["camera_pairs_attempted"], 5
            )
            self.assertEqual(
                row["pixel_motion_available_count"], 5
            )
            self.assertTrue(row["image_pixels_processed"])
            self.assertFalse(
                row["pose_factors_constructed"]
            )

    def test_tampered_camera_array_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            recording, evidence = make_v15(folder)

            path = (
                recording / "frames_v15/camera_003.npy"
            )
            with path.open("ab") as f:
                f.write(b"tampered")

            with self.assertRaisesRegex(
                ValueError, "hash mismatch"
            ):
                review_v15(recording, evidence)

    def test_tampered_capture_index_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            recording, evidence = make_v15(folder)

            path = (
                recording / "capture_index_v15.json"
            )
            path.write_text(
                path.read_text() + " "
            )

            with self.assertRaisesRegex(
                ValueError, "hash mismatch"
            ):
                review_v15(recording, evidence)

    def test_no_independent_reference_claim(self):
        with tempfile.TemporaryDirectory() as folder:
            recording, evidence = make_v15(folder)
            row = review_v15(recording, evidence)
            self.assertFalse(
                row["independent_reference_used"]
            )
            self.assertFalse(
                row["physical_capture_time_verified"]
            )
            self.assertFalse(
                row["cross_sensor_synchronization_verified"]
            )

    def test_repeat_exactly_deterministic(self):
        with tempfile.TemporaryDirectory() as folder:
            recording, evidence = make_v15(folder)
            a = review_v15(recording, evidence)
            b = review_v15(recording, evidence)
            self.assertEqual(a, b)

    def test_source_requires_actual_files(self):
        with tempfile.TemporaryDirectory() as folder:
            recording, evidence = make_v15(folder)
            (
                recording / "frames_v15/camera_006.npy"
            ).unlink()

            with self.assertRaises(ValueError):
                review_v15(recording, evidence)


if __name__ == "__main__":
    unittest.main(verbosity=2)
