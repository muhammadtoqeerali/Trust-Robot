"""Review preserved V15 synthetic camera frames without pose inference."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import numpy as np

from trust_robot.visual_pixel_motion import (
    estimate_pixel_motion,
)

SCHEMA = "TRUST_ROBOT_V15_VISUAL_MOTION_REVIEW_DEV_V1"


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _regular(path):
    if not path.is_file() or path.is_symlink():
        raise ValueError(
            "Missing or unsafe recorded camera input"
        )


def review_v15(recording, compact_evidence):
    recording = Path(recording)
    evidence_path = Path(compact_evidence)

    if not recording.is_dir() or recording.is_symlink():
        raise ValueError("Invalid V15 recording directory")

    _regular(evidence_path)

    evidence = json.loads(evidence_path.read_text())

    if not (
        evidence["schema"]
        == "TRUST_ROBOT_ISAACSIM_V15_COMPACT_EVIDENCE_V1"
        and evidence["data_origin"] == "SYNTHETIC"
        and evidence["camera_frames"] == 6
    ):
        raise ValueError("Unsupported V15 evidence lineage")

    capture = recording / "capture_index_v15.json"
    _regular(capture)

    if _sha(capture) != evidence["capture_index_sha256"]:
        raise ValueError("V15 capture-index hash mismatch")

    index = json.loads(capture.read_text())

    if (
        len(index) != 6
        or [row["step"] for row in index]
           != [31, 41, 51, 61, 71, 81]
    ):
        raise ValueError(
            "Unexpected synthetic camera frame chronology"
        )

    images = []
    times = []
    image_hashes = []

    for i, row in enumerate(index, 1):
        relative = f"frames_v15/camera_{i:03d}.npy"

        if (
            row["camera_file"] != relative
            or row["acquisition_timing_verified"] is not False
            or row["cross_sensor_synchronization_verified"]
               is not False
        ):
            raise ValueError(
                "Unqualified V15 capture metadata changed"
            )

        path = recording / relative
        _regular(path)

        expected = evidence["frame_files"][relative]["sha256"]

        if _sha(path) != expected:
            raise ValueError(
                "V15 camera frame source hash mismatch"
            )

        frame = np.load(path, allow_pickle=False)

        if (
            frame.shape != (120, 160, 4)
            or frame.dtype != np.uint8
        ):
            raise ValueError(
                "Unexpected recorded synthetic camera image"
            )

        t = float(row["camera_read_step_time_s"])

        if not math.isfinite(t):
            raise ValueError(
                "Invalid simulation read-step coordinate"
            )

        images.append(frame)
        times.append(t)
        image_hashes.append(expected)

    if any(b <= a for a, b in zip(times, times[1:])):
        raise ValueError(
            "Nonmonotonic simulation read-step ordering"
        )

    pairs = []

    for i in range(1, len(images)):
        measured = estimate_pixel_motion(
            images[i-1], images[i]
        )

        pairs.append({
            "source_frame_index": i,
            "target_frame_index": i+1,
            "source_camera_npy_sha256": image_hashes[i-1],
            "target_camera_npy_sha256": image_hashes[i],
            "simulation_step_time_source_s": times[i-1],
            "simulation_step_time_target_s": times[i],
            "time_basis": (
                "UNVERIFIED_SIMULATION_READ_STEP_ONLY"
            ),
            "measurement": measured,
        })

    return {
        "schema": SCHEMA,
        "status": "SYNTHETIC_CAMERA_PIXEL_REVIEW_EXECUTED",
        "source_origin": "ISAAC_SIM_V15_SYNTHETIC",
        "compact_evidence_sha256": _sha(evidence_path),
        "capture_index_sha256": _sha(capture),
        "camera_frames_checked": len(images),
        "camera_pairs_attempted": len(pairs),
        "pixel_motion_available_count": sum(
            row["measurement"]["status"]
            == "PIXEL_TRANSLATION_OBSERVED"
            for row in pairs
        ),
        "pixel_motion_unavailable_count": sum(
            row["measurement"]["status"] == "UNAVAILABLE"
            for row in pairs
        ),
        "pairs": pairs,
        "image_pixels_processed": True,
        "physical_capture_time_verified": False,
        "camera_intrinsics_verified": False,
        "physical_extrinsics_verified": False,
        "cross_sensor_synchronization_verified": False,
        "independent_reference_used": False,
        "pose_factors_constructed": False,
        "health_labels_created": False,
    }
