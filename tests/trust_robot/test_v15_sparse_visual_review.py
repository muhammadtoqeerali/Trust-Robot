import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from trust_robot.v15_sparse_visual_review import (
    review_v15_sparse,
)


def make_recording(folder):
    root = Path(folder)
    recording = root / "recording"
    recording.mkdir()

    frames = recording / "frames_v15"
    frames.mkdir()

    base = np.random.default_rng(
        777
    ).integers(
        0, 256, (120, 160, 3),
        dtype=np.uint8,
    )

    records = []
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

        records.append({
            "step": 21+10*i,
            "camera_file": name,
            "camera_read_step_time_s": float(i),
            "acquisition_timing_verified": False,
            "cross_sensor_synchronization_verified": False,
        })

    index = recording / "capture_index_v15.json"

    index.write_text(
        json.dumps(records, sort_keys=True) + "\n"
    )

    evidence = root / "compact_evidence.json"

    evidence.write_text(
        json.dumps({
            "schema":
                "TRUST_ROBOT_ISAACSIM_V15_COMPACT_EVIDENCE_V1",
            "data_origin": "SYNTHETIC",
            "camera_frames": 6,
            "capture_index_sha256": hashlib.sha256(
                index.read_bytes()
            ).hexdigest(),
            "frame_files": hashes,
        }, sort_keys=True) + "\n"
    )

    return recording, evidence


class SparseV15ReviewTests(unittest.TestCase):

    def test_all_five_image_pairs_reviewed(self):
        with tempfile.TemporaryDirectory() as folder:
            recording, evidence = make_recording(folder)
            row = review_v15_sparse(
                recording, evidence
            )
            self.assertEqual(row["pair_count"], 5)
            self.assertEqual(
                row["two_d_geometry_available_count"], 5
            )
            self.assertFalse(
                row["metric_visual_odometry_generated"]
            )

    def test_tampered_source_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            recording, evidence = make_recording(folder)
            path = (
                recording / "frames_v15/camera_004.npy"
            )
            with path.open("ab") as handle:
                handle.write(b"tamper")

            with self.assertRaises(ValueError):
                review_v15_sparse(recording, evidence)

    def test_repeat_deterministic(self):
        with tempfile.TemporaryDirectory() as folder:
            recording, evidence = make_recording(folder)
            first = review_v15_sparse(
                recording, evidence
            )
            second = review_v15_sparse(
                recording, evidence
            )
            self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main(verbosity=2)
