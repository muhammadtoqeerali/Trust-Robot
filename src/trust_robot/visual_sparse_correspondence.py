"""Development-only, genuine image-derived 2D sparse correspondence.

Harris-style spatial corner scoring, normalized local patch matching,
and seeded robust affine consistency evaluation.

The input is image pixels. This implementation does NOT produce
calibrated epipolar geometry, metric displacement, depth, SE(3)
motion, independent reference, or a real camera estimator factor.

The thresholds are manufactured development guards, not learned
health decisions or empirically calibrated confidence limits.
"""
from __future__ import annotations

import json

import numpy as np
from scipy.ndimage import uniform_filter
from numpy.lib.stride_tricks import sliding_window_view

from trust_robot.visual_pixel_motion import (
    grayscale,
    image_sha256,
    estimate_pixel_motion,
    VisualMotionError,
)

SCHEMA = "TRUST_ROBOT_VISUAL_SPARSE_CORRESPONDENCE_DEV_V1"

PATCH_RADIUS = 4
SEARCH_RADIUS = 10
TILE_SIZE = 14
MAX_FEATURES = 90

MIN_PATCH_CORRELATION = 0.73
MIN_PEAK_SEPARATION = 0.045

MIN_MATCHES = 12
MIN_GEOMETRY_INLIER_RATIO = 0.60
RANSAC_INLIER_ERROR_PX = 1.25

RANSAC_SEED = 20261013
RANSAC_TRIALS = 128


def detect_corners(image):
    gray = grayscale(image)
    values = gray.astype(np.float64)

    if float(values.std()) < 5.0:
        return []

    gx = np.zeros_like(values)
    gy = np.zeros_like(values)

    gx[:, 1:-1] = 0.5*(
        values[:, 2:] - values[:, :-2]
    )
    gy[1:-1, :] = 0.5*(
        values[2:, :] - values[:-2, :]
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
        xx*yy - xy*xy - 0.04*(xx+yy)**2
    )

    cutoff = max(
        2000.0,
        0.02*float(np.max(response)),
    )

    margin = PATCH_RADIUS + SEARCH_RADIUS + 2
    height, width = values.shape

    selected = []

    for y0 in range(
        margin, height-margin, TILE_SIZE
    ):
        for x0 in range(
            margin, width-margin, TILE_SIZE
        ):
            region = response[
                y0:min(y0+TILE_SIZE, height-margin),
                x0:min(x0+TILE_SIZE, width-margin),
            ]

            if not region.size:
                continue

            index = int(np.argmax(region))
            yy0, xx0 = np.unravel_index(
                index, region.shape
            )

            strength = float(region[yy0, xx0])

            if strength < cutoff:
                continue

            selected.append((
                strength,
                int(x0+xx0),
                int(y0+yy0),
            ))

    selected.sort(
        key=lambda row: (-row[0], row[2], row[1])
    )

    return [
        {
            "feature_index": index,
            "x_px": int(x),
            "y_px": int(y),
            "corner_response": float(strength),
        }
        for index, (strength, x, y)
        in enumerate(selected[:MAX_FEATURES])
    ]


def match_patches(previous, current):
    a = grayscale(previous)
    b = grayscale(current)

    if a.shape != b.shape:
        raise VisualMotionError(
            "Sparse camera image dimensions differ"
        )

    features = detect_corners(a)

    if not features:
        return features, []

    radius = PATCH_RADIUS
    search = SEARCH_RADIUS

    target = b.astype(np.float64)

    patch_grid = sliding_window_view(
        target,
        (2*radius+1, 2*radius+1),
    )

    matches = []

    for feature in features:
        x = feature["x_px"]
        y = feature["y_px"]

        source = a[
            y-radius:y+radius+1,
            x-radius:x+radius+1,
        ].astype(np.float64)

        centered_source = source-source.mean()
        source_norm = float(
            np.linalg.norm(centered_source)
        )

        if source_norm <= 1e-9:
            continue

        ystart = y-search-radius
        xstart = x-search-radius

        candidate = patch_grid[
            ystart:ystart+2*search+1,
            xstart:xstart+2*search+1,
        ]

        means = candidate.mean(axis=(-2, -1))

        centered = (
            candidate-means[..., None, None]
        )

        norms = (
            np.sqrt(np.sum(
                centered**2, axis=(-2, -1)
            ))
            * source_norm
        )

        correlations = (
            np.sum(
                centered*centered_source,
                axis=(-2, -1),
            )
            / np.maximum(norms, 1e-9)
        )

        iy, ix = np.unravel_index(
            int(np.argmax(correlations)),
            correlations.shape,
        )

        top = float(correlations[iy, ix])

        if top < MIN_PATCH_CORRELATION:
            continue

        other = correlations.copy()

        other[
            max(0, iy-2):iy+3,
            max(0, ix-2):ix+3,
        ] = -2.0

        second = float(np.max(other))

        if top-second < MIN_PEAK_SEPARATION:
            continue

        dx = int(ix-search)
        dy = int(iy-search)

        matches.append({
            "feature_index": feature["feature_index"],
            "source_xy_px": [x, y],
            "target_xy_px": [x+dx, y+dy],
            "normalized_patch_correlation": top,
            "second_peak_correlation": second,
        })

    return features, matches


def robust_affine_consistency(matches):
    """Fit only a 2D affine image-consistency diagnostic.

    RANSAC is deterministic and model comparisons use 2D pixels.
    No calibrated 3D scene or camera-pose geometry is inferred.
    """
    if len(matches) < MIN_MATCHES:
        return None

    points = np.array([
        row["source_xy_px"] + row["target_xy_px"]
        for row in matches
    ], dtype=np.float64)

    origin = np.column_stack((
        points[:, 0],
        points[:, 1],
        np.ones(len(points)),
    ))

    target = points[:, 2:4]

    rng = np.random.default_rng(RANSAC_SEED)
    best = None

    for _ in range(RANSAC_TRIALS):
        selected = rng.choice(
            len(points),
            size=3,
            replace=False,
        )

        if np.linalg.matrix_rank(
            origin[selected]
        ) != 3:
            continue

        solution = np.linalg.lstsq(
            origin[selected],
            target[selected],
            rcond=None,
        )[0]

        error = np.linalg.norm(
            origin@solution-target, axis=1
        )

        valid = error <= RANSAC_INLIER_ERROR_PX
        count = int(valid.sum())

        if count == 0:
            continue

        median_error = float(
            np.median(error[valid])
        )

        candidate_score = (
            count, -median_error
        )

        if (
            best is None
            or candidate_score > best[0]
        ):
            best = (
                candidate_score, valid
            )

    if best is None:
        return None

    good = best[1]

    for _ in range(2):
        if (
            good.sum() < MIN_MATCHES
            or np.linalg.matrix_rank(
                origin[good]
            ) < 3
        ):
            return None

        solution = np.linalg.lstsq(
            origin[good],
            target[good],
            rcond=None,
        )[0]

        error = np.linalg.norm(
            origin@solution-target,
            axis=1,
        )

        good = error <= RANSAC_INLIER_ERROR_PX

    count = int(good.sum())
    ratio = count/len(matches)

    if (
        count < MIN_MATCHES
        or ratio < MIN_GEOMETRY_INLIER_RATIO
        or np.linalg.matrix_rank(
            origin[good]
        ) < 3
    ):
        return None

    solution = np.linalg.lstsq(
        origin[good],
        target[good],
        rcond=None,
    )[0]

    error = np.linalg.norm(
        origin@solution-target,
        axis=1,
    )

    retained = points[good]

    span_x = float(np.ptp(retained[:, 0]))
    span_y = float(np.ptp(retained[:, 1]))

    if min(span_x, span_y) < 20.0:
        return None

    displacement = (
        retained[:, 2:4]-retained[:, :2]
    )

    median = np.median(
        displacement, axis=0
    )

    return {
        "model": "TWO_D_IMAGE_AFFINE_ONLY",
        "correspondence_count": len(matches),
        "inlier_count": count,
        "inlier_ratio": float(ratio),
        "inlier_threshold_px": RANSAC_INLIER_ERROR_PX,
        "median_dx_px": float(median[0]),
        "median_dy_px": float(median[1]),
        "median_reprojection_error_px": float(
            np.median(error[good])
        ),
        "max_reprojection_error_px": float(
            np.max(error[good])
        ),
        "source_span_xy_px": [span_x, span_y],
        "affine_2x3": [
            solution[:, 0].tolist(),
            solution[:, 1].tolist(),
        ],
        "calibrated_epipolar_geometry": False,
        "physical_camera_pose_estimated": False,
    }


def analyze_sparse_motion(previous, current):
    a = grayscale(previous)
    b = grayscale(current)

    if a.shape != b.shape:
        raise VisualMotionError(
            "Sparse source and target images must match"
        )

    features, matches = match_patches(a, b)
    geometry = robust_affine_consistency(matches)
    global_result = estimate_pixel_motion(a, b)

    row = {
        "schema": SCHEMA,
        "status": (
            "TWO_D_AFFINE_CONSISTENCY_OBSERVED"
            if geometry is not None
            else "UNAVAILABLE"
        ),
        "image_shape_hw": list(a.shape),
        "source_grayscale_sha256": image_sha256(a),
        "target_grayscale_sha256": image_sha256(b),
        "detected_feature_count": len(features),
        "accepted_patch_match_count": len(matches),
        "two_d_affine_geometry": geometry,
        "global_translation_status": global_result["status"],
        "global_dx_px": global_result[
            "pixel_displacement_dx"
        ],
        "global_dy_px": global_result[
            "pixel_displacement_dy"
        ],
        "accepted_correspondence_examples": (
            matches[:32] if geometry is not None else []
        ),
        "camera_intrinsics_used": False,
        "metric_translation_available": False,
        "calibrated_essential_matrix_estimated": False,
        "camera_se3_pose_factor_created": False,
        "physical_capture_time_verified": False,
        "health_labels_generated": False,
        "independent_pose_reference_used": False,
    }

    return row


def require_metric_visual_motion(result):
    raise VisualMotionError(
        "Sparse image correspondences alone do not authorize "
        "metric SE3 camera motion or real-sensor factor fusion"
    )


def controlled_sparse_study():
    rng = np.random.default_rng(20261013)

    image = rng.integers(
        0, 256, (120, 160),
        dtype=np.uint8,
    )

    scenarios = []

    for label, dy, dx in (
        ("translated_right", -3, 5),
        ("translated_left", 4, -6),
        ("stationary", 0, 0),
        ("small_shift", 1, 2),
    ):
        target = np.roll(
            image, (dy, dx), axis=(0, 1)
        )

        result = analyze_sparse_motion(
            image, target
        )

        geometry = result["two_d_affine_geometry"]

        if (
            result["status"]
            != "TWO_D_AFFINE_CONSISTENCY_OBSERVED"
            or geometry is None
            or abs(geometry["median_dx_px"]-dx) > 0.5
            or abs(geometry["median_dy_px"]-dy) > 0.5
        ):
            raise ValueError(
                "Manufactured sparse image shift not recovered"
            )

        scenarios.append({
            "scenario": label,
            "expected_shift_dy_dx": [dy, dx],
            "result": result,
        })

    bright = np.clip(
        image.astype(float)*0.8+15,
        0, 255,
    ).astype(np.uint8)

    bright = np.roll(
        bright, (2, -4), axis=(0, 1)
    )

    result = analyze_sparse_motion(image, bright)

    if result["status"] != (
        "TWO_D_AFFINE_CONSISTENCY_OBSERVED"
    ):
        raise ValueError(
            "Photometric sparse matching failed"
        )

    scenarios.append({
        "scenario": "brightness_changed",
        "expected_shift_dy_dx": [2, -4],
        "result": result,
    })

    mixed = np.roll(
        image, (4, -6), axis=(0, 1)
    )

    mixed[35:75, 40:90] = np.roll(
        image[35:75, 40:90],
        (-5, 7),
        axis=(0, 1),
    )

    result = analyze_sparse_motion(image, mixed)

    if (
        result["status"]
        != "TWO_D_AFFINE_CONSISTENCY_OBSERVED"
        or abs(
            result["two_d_affine_geometry"]["median_dx_px"]+6
        ) > 0.5
        or abs(
            result["two_d_affine_geometry"]["median_dy_px"]-4
        ) > 0.5
    ):
        raise ValueError(
            "Dominant image motion not recovered"
        )

    scenarios.append({
        "scenario": "different_moving_foreground",
        "expected_shift_dy_dx": [4, -6],
        "result": result,
    })

    for label, target in (
        ("blackout", np.zeros_like(image)),
        (
            "unrelated_image",
            rng.integers(
                0, 256, image.shape,
                dtype=np.uint8,
            ),
        ),
    ):
        result = analyze_sparse_motion(
            image, target
        )

        if result["status"] != "UNAVAILABLE":
            raise ValueError(
                "Unrelated or untextured image not rejected"
            )

        scenarios.append({
            "scenario": label,
            "expected_shift_dy_dx": None,
            "result": result,
        })

    return {
        "schema": SCHEMA,
        "status": "CONTROLLED_2D_SPARSE_DEVELOPMENT_VALIDATED",
        "case_count": len(scenarios),
        "cases": scenarios,
        "real_image_pixels_used": True,
        "physical_camera_pose_estimated": False,
        "sensor_calibration_performed": False,
        "health_quality_thresholds_calibrated": False,
    }


def canonical(value):
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ) + "\n"
    ).encode("utf-8")
