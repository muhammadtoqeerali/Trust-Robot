"""Offline image-derived 2D pixel motion.

Phase-only FFT estimates a single integer image-plane shift.
Local normalized patch correlations independently check the
global candidate against spatially distributed image evidence.

This is NOT six-degree-of-freedom visual odometry:
- no intrinsics or extrinsics are assumed;
- no metric depth or translation scale is inferred;
- no camera pose factor is produced;
- no time association across sensors is made;
- numerical test thresholds are not health thresholds.

The model is global 2D translation of image content.
Parallax, occlusion, rotation, dynamic scenes and rolling
shutter require more sophisticated geometrical treatment.
"""
from __future__ import annotations

import hashlib
import json

import numpy as np

SCHEMA = "TRUST_ROBOT_VISUAL_PIXEL_MOTION_DEV_V1"

MIN_IMAGE_STD = 5.0
MIN_PEAK = 0.08
MIN_PEAK_SEPARATION = 0.04
MIN_PATCH_STD = 5.0
MIN_PATCH_CORRELATION = 0.70
MIN_INLIER_FRACTION = 0.60
MIN_VALID_PATCHES = 8


class VisualMotionError(ValueError):
    """Malformed image or unauthorized metric-pose use."""


def grayscale(image):
    x = np.asarray(image)

    if (
        x.dtype != np.uint8
        or x.ndim not in (2, 3)
        or x.shape[0] < 32
        or x.shape[1] < 32
        or x.shape[0] > 512
        or x.shape[1] > 512
    ):
        raise VisualMotionError(
            "Expected bounded uint8 camera image"
        )

    if x.ndim == 3:
        if x.shape[2] not in (3, 4):
            raise VisualMotionError(
                "Expected RGB or RGBA camera image"
            )

        # Defined grayscale conversion; alpha is deliberately
        # ignored. This is not camera radiometric calibration.
        x = np.rint(
            0.299*x[:, :, 0].astype(np.float64)
            + 0.587*x[:, :, 1].astype(np.float64)
            + 0.114*x[:, :, 2].astype(np.float64)
        ).astype(np.uint8)

    return np.ascontiguousarray(x)


def image_sha256(image):
    array = np.ascontiguousarray(image)
    return hashlib.sha256(
        json.dumps(
            {
                "shape": list(array.shape),
                "dtype": str(array.dtype),
            },
            sort_keys=True,
        ).encode()
        + array.tobytes()
    ).hexdigest()


def _patch_evidence(a, b, dy, dx):
    height, width = a.shape
    radius = 4
    considered = 0
    accepted = []
    all_correlations = []

    # Spatially distributed support; no temporal extrapolation.
    for y in range(10, height-10, 14):
        for x in range(10, width-10, 14):
            yy = y+dy
            xx = x+dx

            if not (
                radius <= yy < height-radius
                and radius <= xx < width-radius
            ):
                continue

            pa = a[
                y-radius:y+radius+1,
                x-radius:x+radius+1,
            ]
            pb = b[
                yy-radius:yy+radius+1,
                xx-radius:xx+radius+1,
            ]

            if (
                float(np.std(pa)) < MIN_PATCH_STD
                or float(np.std(pb)) < MIN_PATCH_STD
            ):
                continue

            considered += 1

            aa = pa-pa.mean()
            bb = pb-pb.mean()

            denominator = np.sqrt(
                np.sum(aa*aa)*np.sum(bb*bb)
            )

            if denominator <= 0:
                continue

            corr = float(np.sum(aa*bb)/denominator)
            all_correlations.append(corr)

            if corr >= MIN_PATCH_CORRELATION:
                accepted.append({
                    "source_xy_px": [x, y],
                    "target_xy_px": [xx, yy],
                    "normalized_patch_correlation": corr,
                })

    fraction = (
        len(accepted)/considered
        if considered else 0.0
    )

    return {
        "evaluated_textured_patches": considered,
        "correlated_patch_count": len(accepted),
        "correlated_patch_fraction": float(fraction),
        "mean_evaluated_patch_correlation": (
            float(np.mean(all_correlations))
            if all_correlations else None
        ),
        "sample_correspondences": accepted[:32],
    }


def estimate_pixel_motion(previous, current):
    """Extract a verified 2D image-plane translation candidate.

    Report UNAVAILABLE instead of synthesizing a pixel motion
    when texture or correspondence evidence is inadequate.
    """
    a = grayscale(previous)
    b = grayscale(current)

    if a.shape != b.shape:
        raise VisualMotionError(
            "Camera image shapes must agree"
        )

    height, width = a.shape

    a = a.astype(np.float64)
    b = b.astype(np.float64)

    std_a = float(a.std())
    std_b = float(b.std())

    result = {
        "schema": SCHEMA,
        "image_shape_hw": [height, width],
        "previous_grayscale_sha256": image_sha256(
            a.astype(np.uint8)
        ),
        "current_grayscale_sha256": image_sha256(
            b.astype(np.uint8)
        ),
        "previous_intensity_std": std_a,
        "current_intensity_std": std_b,
        "status": "UNAVAILABLE",
        "pixel_displacement_dx": None,
        "pixel_displacement_dy": None,
        "phase_correlation_peak": None,
        "phase_correlation_second_peak": None,
        "patch_evidence": None,
        "unavailability_reason": None,
        "source_is_image_pixels": True,
        "motion_model": "GLOBAL_INTEGER_2D_PIXEL_TRANSLATION",
        "physical_capture_time_verified": False,
        "metric_translation_scale_available": False,
        "camera_intrinsics_qualified": False,
        "camera_pose_factor_created": False,
        "health_label_created": False,
        "independent_pose_reference_used": False,
    }

    if min(std_a, std_b) < MIN_IMAGE_STD:
        result["unavailability_reason"] = (
            "INSUFFICIENT_IMAGE_TEXTURE"
        )
        return result

    fa = np.fft.fft2(a-a.mean())
    fb = np.fft.fft2(b-b.mean())

    cross = fb*np.conj(fa)
    magnitude = np.abs(cross)

    normalized = cross/np.maximum(magnitude, 1e-12)
    surface = np.fft.ifft2(normalized).real

    iy, ix = np.unravel_index(
        int(np.argmax(surface)), surface.shape
    )

    dy = int(iy if iy <= height//2 else iy-height)
    dx = int(ix if ix <= width//2 else ix-width)

    peak = float(surface[iy, ix])

    other = surface.copy()

    for oy in range(-3, 4):
        for ox in range(-3, 4):
            other[
                (iy+oy) % height,
                (ix+ox) % width,
            ] = -np.inf

    second_peak = float(np.max(other))

    result["phase_correlation_peak"] = peak
    result["phase_correlation_second_peak"] = second_peak

    if (
        abs(dy) > height//3
        or abs(dx) > width//3
        or peak < MIN_PEAK
        or peak-second_peak < MIN_PEAK_SEPARATION
    ):
        result["unavailability_reason"] = (
            "AMBIGUOUS_GLOBAL_IMAGE_SHIFT"
        )
        return result

    patch = _patch_evidence(a, b, dy, dx)
    result["patch_evidence"] = patch

    if (
        patch["evaluated_textured_patches"] < MIN_VALID_PATCHES
        or patch["correlated_patch_fraction"]
           < MIN_INLIER_FRACTION
    ):
        result["unavailability_reason"] = (
            "INSUFFICIENT_LOCAL_PIXEL_CORRESPONDENCE"
        )
        return result

    result.update({
        "status": "PIXEL_TRANSLATION_OBSERVED",
        "pixel_displacement_dx": dx,
        "pixel_displacement_dy": dy,
        "unavailability_reason": None,
    })

    return result


def require_metric_camera_factor(pixel_result):
    """No 6-DoF pose factor may be inferred from a pixel shift."""
    raise VisualMotionError(
        "2D image displacement does not authorize metric camera "
        "pose factors, calibrated geometry, depth or sensor fusion"
    )


def canonical(data):
    return (
        json.dumps(
            data,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ) + "\n"
    ).encode("utf-8")


def controlled_pixel_study():
    """Manufactured image perturbations with known pixel shifts."""
    rng = np.random.default_rng(20261013)

    image = rng.integers(
        0, 256, size=(120, 160), dtype=np.uint8
    )

    scenarios = []

    for name, dy, dx in (
        ("right_and_up", -3, 5),
        ("left_and_down", 4, -6),
        ("stationary", 0, 0),
        ("small_right", 0, 2),
    ):
        shifted = np.roll(
            image, shift=(dy, dx), axis=(0, 1)
        )

        measurement = estimate_pixel_motion(
            image, shifted
        )

        if not (
            measurement["status"]
            == "PIXEL_TRANSLATION_OBSERVED"
            and measurement["pixel_displacement_dx"] == dx
            and measurement["pixel_displacement_dy"] == dy
        ):
            raise ValueError(
                "Manufactured image displacement recovery failed"
            )

        scenarios.append({
            "scenario": name,
            "expected_pixel_shift_dy_dx": [dy, dx],
            "measurement": measurement,
        })

    photometric = np.clip(
        image.astype(float)*0.8+15, 0, 255
    ).astype(np.uint8)

    photometric = np.roll(
        photometric, shift=(-2, 4), axis=(0, 1)
    )

    altered = estimate_pixel_motion(image, photometric)

    if not (
        altered["status"] == "PIXEL_TRANSLATION_OBSERVED"
        and altered["pixel_displacement_dx"] == 4
        and altered["pixel_displacement_dy"] == -2
    ):
        raise ValueError(
            "Photometric pixel-motion study failed"
        )

    scenarios.append({
        "scenario": "affine_brightness_changed",
        "expected_pixel_shift_dy_dx": [-2, 4],
        "measurement": altered,
    })

    for name, other in (
        ("camera_blackout", np.zeros_like(image)),
        ("unrelated_texture", rng.integers(
            0, 256, image.shape, dtype=np.uint8
        )),
    ):
        row = estimate_pixel_motion(image, other)

        if row["status"] != "UNAVAILABLE":
            raise ValueError(
                "Invalid image evidence not rejected"
            )

        scenarios.append({
            "scenario": name,
            "expected_pixel_shift_dy_dx": None,
            "measurement": row,
        })

    return {
        "schema": SCHEMA,
        "status": "CONTROLLED_PIXEL_MOTION_DEVELOPMENT_VALIDATED",
        "case_count": len(scenarios),
        "cases": scenarios,
        "metric_camera_pose_factors_created": False,
        "camera_calibration_applied": False,
        "physical_sensor_evaluation_performed": False,
        "health_thresholds_calibrated": False,
    }
