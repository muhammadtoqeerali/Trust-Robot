"""Sparse 2D analysis of already qualified V15 synthetic image files."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from trust_robot.v15_visual_motion_review import (
    review_v15,
)
from trust_robot.visual_sparse_correspondence import (
    analyze_sparse_motion,
)

SCHEMA = "TRUST_ROBOT_V15_SPARSE_VISUAL_REVIEW_DEV_V1"


def review_v15_sparse(recording, compact_evidence):
    """Reject unverified files; never create metric pose constraints."""
    recording = Path(recording)
    evidence_path = Path(compact_evidence)

    # Reuse the established content-integrity, chronology and
    # timing-provenance checks before opening the image series.
    previous = review_v15(
        recording, evidence_path
    )

    evidence = json.loads(
        evidence_path.read_text()
    )

    images = []

    for i in range(1, 7):
        relative = f"frames_v15/camera_{i:03d}.npy"
        path = recording / relative

        if not path.is_file() or path.is_symlink():
            raise ValueError(
                "Unsafe recorded camera frame"
            )

        digest = hashlib.sha256(
            path.read_bytes()
        ).hexdigest()

        assert digest == evidence[
            "frame_files"
        ][relative]["sha256"]

        images.append(
            np.load(path, allow_pickle=False)
        )

    pairs = []

    for index in range(1, len(images)):
        measured = analyze_sparse_motion(
            images[index-1],
            images[index],
        )

        original = previous["pairs"][index-1]

        pairs.append({
            "source_frame_index": index,
            "target_frame_index": index+1,
            "source_sha256": original[
                "source_camera_npy_sha256"
            ],
            "target_sha256": original[
                "target_camera_npy_sha256"
            ],
            "time_basis": (
                "UNVERIFIED_SIMULATION_READ_STEP_ONLY"
            ),
            "sparse_motion": measured,
        })

    return {
        "schema": SCHEMA,
        "status": "SYNTHETIC_V15_SPARSE_REVIEW_EXECUTED",
        "source_origin": "ISAAC_SIM_V15_SYNTHETIC",
        "camera_frames_checked": 6,
        "pair_count": 5,
        "two_d_geometry_available_count": sum(
            row["sparse_motion"]["status"]
            == "TWO_D_AFFINE_CONSISTENCY_OBSERVED"
            for row in pairs
        ),
        "two_d_geometry_unavailable_count": sum(
            row["sparse_motion"]["status"] == "UNAVAILABLE"
            for row in pairs
        ),
        "pairs": pairs,
        "sensor_physical_capture_time_verified": False,
        "camera_intrinsics_independently_verified": False,
        "extrinsic_calibration_verified": False,
        "metric_visual_odometry_generated": False,
        "physical_robot_contact": False,
    }
