"""Frozen, development-only synthetic metric depth-camera source.

Manufactured 3D world points are projected into two virtual
camera frames. Fixed pixel/depth perturbations are applied.
Matched metric-depth observations are aligned by rigid SVD.

No LiDAR registration factor is copied or accessed.

The generator shares the existing analytic motion model.
It is not physically independent sensor evidence.

No real images, camera calibration, sensor health, estimator
execution, physical observability or GT scoring.
"""
from __future__ import annotations

import math

import numpy as np
from scipy.spatial.transform import Rotation

from trust_robot.analytic_inertial_15d import (
    analytic_truth,
    as_rotation,
)
from trust_robot.analytic_preintegrated_fusion import (
    NODE_FRAMES,
)
from trust_robot.clean_backbone import PoseSE3
from trust_robot.multimodal_factor_interface import (
    ANALYTIC_FRAME,
    CAMERA_SOURCE,
    SyntheticPoseFactor,
)

SCHEMA = (
    "TRUST_ROBOT_R135_A9_ANALYTIC_DEPTH_CAMERA_SOURCE_V1"
)

STATUS = "UNTRUSTED_SYNTHETIC_OBSERVATION_ONLY"

MODES = ("ideal", "noisy", "biased")

EDGES = (
    (0, 1),
    (0, 2),
    (1, 2),
    (1, 3),
    (2, 3),
    (2, 4),
    (3, 4),
)

SCENE_SEED = 20261029
SCENE_POINTS = 72

FX = 240.0
FY = 235.0
CX = 80.0
CY = 60.0

WIDTH = 160.0
HEIGHT = 120.0

PIXEL_NOISE_STD = 0.15
DEPTH_NOISE_STD_M = 0.004

BIAS_U_PX = 1.7
BIAS_V_PX = -1.2
BIAS_DEPTH_M = 0.02


class SyntheticDepthCameraError(ValueError):
    """Invalid manufactured depth-camera input or geometry."""


def _scene():
    rng = np.random.default_rng(SCENE_SEED)

    return rng.uniform(
        low=(-0.65, -0.45, 3.0),
        high=(0.65, 0.45, 7.0),
        size=(SCENE_POINTS, 3),
    )


def _observe(frame, mode, *, biased_current):
    state = analytic_truth(frame)

    position = np.asarray(
        state[:3], dtype=np.float64
    )

    rotation = as_rotation(state).as_matrix()

    # Manufactured camera coordinates, no LiDAR data.
    xyz = (_scene() - position) @ rotation

    if (
        xyz.shape != (SCENE_POINTS, 3)
        or not np.isfinite(xyz).all()
        or float(np.min(xyz[:, 2])) <= 2.5
    ):
        raise SyntheticDepthCameraError(
            "Invalid manufactured camera scene"
        )

    u = FX * xyz[:, 0] / xyz[:, 2] + CX
    v = FY * xyz[:, 1] / xyz[:, 2] + CY
    depth = xyz[:, 2].copy()

    if mode != "ideal":
        # Camera-specific fixed noise generator.
        # It is distinct from the LiDAR fixture RNG.
        rng = np.random.default_rng(
            778811 + 100 * frame
        )

        u += rng.normal(
            0.0, PIXEL_NOISE_STD, len(u)
        )

        v += rng.normal(
            0.0, PIXEL_NOISE_STD, len(v)
        )

        depth += rng.normal(
            0.0, DEPTH_NOISE_STD_M, len(depth)
        )

    if mode == "biased" and biased_current:
        # Pair-local bias on the current image.
        # Not a physical time-persistent bias model.
        u += BIAS_U_PX
        v += BIAS_V_PX
        depth += BIAS_DEPTH_M

    if (
        not np.isfinite(u).all()
        or not np.isfinite(v).all()
        or not np.isfinite(depth).all()
        or float(np.min(depth)) <= 0.0
        or not np.all((u > 0.0) & (u < WIDTH))
        or not np.all((v > 0.0) & (v < HEIGHT))
    ):
        raise SyntheticDepthCameraError(
            "Invalid synthetic pixel/depth observations"
        )

    # Synthetic metric depth supplies scale.
    # These are not monocular-only correspondences.
    reconstructed = np.column_stack((
        (u - CX) * depth / FX,
        (v - CY) * depth / FY,
        depth,
    ))

    if (
        reconstructed.shape != (SCENE_POINTS, 3)
        or not np.isfinite(reconstructed).all()
    ):
        raise SyntheticDepthCameraError(
            "Invalid depth reconstruction"
        )

    return reconstructed


def _fit_relative(current, previous):
    """Estimate previous_T_current from depth correspondences."""
    if (
        current.shape != (SCENE_POINTS, 3)
        or previous.shape != (SCENE_POINTS, 3)
        or not np.isfinite(current).all()
        or not np.isfinite(previous).all()
    ):
        raise SyntheticDepthCameraError(
            "Invalid manufactured 3D correspondence shape"
        )

    center_current = current.mean(axis=0)
    center_previous = previous.mean(axis=0)

    H = (
        (current - center_current).T
        @ (previous - center_previous)
    )

    U, singular, Vt = np.linalg.svd(H)

    if (
        not np.isfinite(singular).all()
        or float(np.min(singular)) <= 0.1
    ):
        raise SyntheticDepthCameraError(
            "Degenerate manufactured 3D geometry"
        )

    D = np.eye(3)
    D[-1, -1] = np.linalg.det(U @ Vt)

    row_rotation = U @ D @ Vt

    if not np.linalg.det(row_rotation) > 0.999999:
        raise SyntheticDepthCameraError(
            "Improper fitted rigid rotation"
        )

    translation = (
        center_previous
        - center_current @ row_rotation
    )

    qx, qy, qz, qw = Rotation.from_matrix(
        row_rotation.T
    ).as_quat()

    measurement = PoseSE3(
        translation_m=tuple(
            float(x) for x in translation
        ),
        quaternion_wxyz=(
            float(qw),
            float(qx),
            float(qy),
            float(qz),
        ),
    )

    residual = float(np.mean(
        np.linalg.norm(
            current @ row_rotation
            + translation
            - previous,
            axis=1,
        )
    ))

    if not math.isfinite(residual):
        raise SyntheticDepthCameraError(
            "Non-finite correspondence residual"
        )

    return measurement, residual


def generate_packet(edge, mode):
    """Return a synthetic camera packet and descriptive metadata.

    Accepts only a fixed graph edge and observation mode.
    No external data, truth, pose factors or weights accepted.
    """
    if (
        type(edge) is not tuple
        or len(edge) != 2
        or any(type(i) is not int for i in edge)
        or edge not in EDGES
        or type(mode) is not str
        or mode not in MODES
        or NODE_FRAMES != (0, 2, 4, 6, 8)
    ):
        raise SyntheticDepthCameraError(
            "Only frozen camera edge/mode pairs are allowed"
        )

    i, j = edge

    previous = _observe(
        NODE_FRAMES[i],
        mode,
        biased_current=False,
    )

    current = _observe(
        NODE_FRAMES[j],
        mode,
        biased_current=True,
    )

    measurement, residual = _fit_relative(
        current, previous
    )

    packet = SyntheticPoseFactor(
        modality="camera",
        edge=edge,
        measurement_id=(
            f"r135-a9-depth-{mode}-{i}-{j}"
        ),
        source_id=CAMERA_SOURCE,
        frame_id=ANALYTIC_FRAME,
        measurement=measurement,
    )

    metadata = {
        "schema": SCHEMA,
        "status": STATUS,
        "edge": [i, j],
        "observation_mode": mode,
        "manufactured_correspondence_count":
            SCENE_POINTS,
        "manufactured_scene_seed": SCENE_SEED,
        "synthetic_camera_pixel_noise_std":
            PIXEL_NOISE_STD if mode != "ideal" else 0.0,
        "synthetic_camera_depth_noise_std_m":
            DEPTH_NOISE_STD_M if mode != "ideal" else 0.0,
        "pair_local_current_image_bias":
            mode == "biased",
        "mean_3d_correspondence_residual_m":
            residual,
        "measurement_id": packet.measurement_id,
        "measurement_origin": packet.origin,
        "measurement_source_id": packet.source_id,
        "metric_depth_manufactured": True,
        "monocular_metric_scale_established": False,
        "lidar_pose_factor_copied": False,
        "independent_physical_sensor_evidence": False,
        "physical_calibration_verified": False,
        "physical_clock_verified": False,
        "health_probability_generated": False,
        "health_label_assigned": False,
        "factor_weight_selected": False,
        "estimator_executed": False,
        "real_factor_execution_authorized": False,
        "confirmation_test_accessed": False,
    }

    return packet, metadata


def summarize_all_pairs():
    """Describe 21 fixed manufactured pairs; no estimator calls."""
    return tuple(
        generate_packet(edge, mode)[1]
        for edge in EDGES
        for mode in MODES
    )
