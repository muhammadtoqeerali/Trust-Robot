"""Descriptive V15 corner-detection bottleneck audit.

Measures the published detector's original fixed responses,
contrast and threshold. It does not tune or rewrite thresholds,
change source images or create camera pose factors.
"""
from __future__ import annotations

import numpy as np
from scipy.ndimage import uniform_filter

from trust_robot.visual_pixel_motion import (
    grayscale,
    image_sha256,
)
from trust_robot.visual_sparse_correspondence import (
    detect_corners,
    PATCH_RADIUS,
    SEARCH_RADIUS,
    TILE_SIZE,
)

SCHEMA = "TRUST_ROBOT_V15_VISUAL_CORNER_AUDIT_DEV_V1"


def audit_image_corners(image):
    gray = grayscale(image)
    values = gray.astype(float)

    gx = np.zeros_like(values)
    gy = np.zeros_like(values)

    gx[:, 1:-1] = 0.5*(
        values[:, 2:]-values[:, :-2]
    )
    gy[1:-1, :] = 0.5*(
        values[2:, :]-values[:-2, :]
    )

    xx = uniform_filter(
        gx*gx, size=5, mode="constant"
    )
    yy = uniform_filter(
        gy*gy, size=5, mode="constant"
    )
    xy = uniform_filter(
        gx*gy, size=5, mode="constant"
    )

    response = (
        xx*yy-xy*xy-0.04*(xx+yy)**2
    )

    threshold = max(
        2000.0,
        0.02*float(np.max(response)),
    )

    margin = PATCH_RADIUS+SEARCH_RADIUS+2
    eligible = response[
        margin:values.shape[0]-margin,
        margin:values.shape[1]-margin,
    ]

    selected = detect_corners(image)

    return {
        "schema": SCHEMA,
        "image_shape_hw": list(gray.shape),
        "image_sha256": image_sha256(gray),
        "minimum_intensity": int(gray.min()),
        "maximum_intensity": int(gray.max()),
        "mean_intensity": float(values.mean()),
        "global_intensity_std": float(values.std()),
        "mean_absolute_x_gradient": float(
            np.mean(np.abs(gx))
        ),
        "mean_absolute_y_gradient": float(
            np.mean(np.abs(gy))
        ),
        "global_max_harris_response": float(
            np.max(response)
        ),
        "eligible_region_max_harris_response": float(
            np.max(eligible)
        ),
        "original_harris_cutoff": float(threshold),
        "original_corner_count": len(selected),
        "original_global_std_minimum": 5.0,
        "original_detector_thresholds_changed": False,
        "camera_geometry_qualified": False,
        "camera_pose_factor_created": False,
        "health_label_created": False,
    }
