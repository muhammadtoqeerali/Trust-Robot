"""Offline homography compatibility analysis in 2D image coordinates.

Strong homography support can arise from a planar scene,
pure camera rotation, or a dominant image plane.

Homography support is not proof of planarity, metric depth,
camera translation, calibrated relative pose, or safe fusion.

This module is restricted to explicit development fixtures.
It does not change the published eight-point estimator.
"""
from __future__ import annotations

import json
import numpy as np
from scipy.spatial.transform import Rotation

SCHEMA = "TRUST_ROBOT_VISUAL_HOMOGRAPHY_ROBUSTNESS_DEV_V1"

PROVENANCES = frozenset((
    "MANUFACTURED_3D_PROJECTIONS",
    "CONTROLLED_IMAGE_PIXELS",
))

TRIALS = 256
SEED = 20261013
PIXEL_INLIER_THRESHOLD = 0.8
MIN_CORRESPONDENCES = 36
MIN_RATIO = 0.70


class HomographyAuditError(ValueError):
    pass


def _normalized(points):
    center = points.mean(axis=0)
    delta = points-center

    mean = float(
        np.mean(np.linalg.norm(delta, axis=1))
    )

    if mean < 1e-10:
        raise HomographyAuditError(
            "Degenerate image geometry"
        )

    scale = np.sqrt(2.0)/mean

    transform = np.array([
        [scale, 0, -scale*center[0]],
        [0, scale, -scale*center[1]],
        [0, 0, 1.0],
    ])

    return delta*scale, transform


def _fit(source, target):
    a, Ta = _normalized(source)
    b, Tb = _normalized(target)

    u, v = a.T
    p, q = b.T

    zero = np.zeros(len(a))
    one = np.ones(len(a))

    A = np.empty((2*len(a), 9))

    A[::2] = np.column_stack((
        u, v, one, zero, zero, zero,
        -u*p, -v*p, -p,
    ))

    A[1::2] = np.column_stack((
        zero, zero, zero, u, v, one,
        -u*q, -v*q, -q,
    ))

    if np.linalg.matrix_rank(A) < 8:
        raise HomographyAuditError(
            "Degenerate homography design"
        )

    _, _, Vt = np.linalg.svd(
        A, full_matrices=True
    )

    H = np.linalg.solve(
        Tb, Vt[-1].reshape(3, 3)@Ta
    )

    norm = float(np.linalg.norm(H))

    if not np.isfinite(norm) or norm < 1e-12:
        raise HomographyAuditError(
            "Nonfinite homography"
        )

    return H/norm


def _errors(H, source, target):
    homogeneous = np.column_stack((
        source,
        np.ones(len(source)),
    ))@H.T

    depths = homogeneous[:, 2]

    errors = np.full(
        len(source), np.inf
    )

    valid = (
        np.isfinite(depths)
        & (np.abs(depths) > 1e-12)
    )

    errors[valid] = np.linalg.norm(
        homogeneous[valid, :2]
        / depths[valid, None]
        - target[valid],
        axis=1,
    )

    return errors


def characterize_homography(
    source, target, *, provenance
):
    if provenance not in PROVENANCES:
        raise HomographyAuditError(
            "Unqualified correspondence provenance"
        )

    a = np.asarray(source, dtype=float)
    b = np.asarray(target, dtype=float)

    if (
        a.ndim != 2
        or a.shape[1:] != (2,)
        or a.shape != b.shape
        or len(a) > 300
        or not np.isfinite(a).all()
        or not np.isfinite(b).all()
    ):
        raise HomographyAuditError(
            "Invalid image-coordinate input"
        )

    result = {
        "schema": SCHEMA,
        "status": "UNAVAILABLE",
        "reason": None,
        "correspondence_count": len(a),
        "inlier_count": 0,
        "inlier_ratio": 0.0,
        "median_inlier_error_px": None,
        "homography_matrix": None,
        "source_provenance": provenance,
        "supports_3d_pose_inference": False,
        "scene_planarity_proven": False,
        "physical_camera_calibrated": False,
        "metric_pose_factor_created": False,
        "published_two_view_estimator_modified": False,
    }

    if len(a) < MIN_CORRESPONDENCES:
        result["reason"] = "TOO_FEW_CORRESPONDENCES"
        return result

    rng = np.random.default_rng(SEED)
    best = None

    for _ in range(TRIALS):
        indices = rng.choice(
            len(a), 4, replace=False
        )

        try:
            H = _fit(a[indices], b[indices])
        except HomographyAuditError:
            continue

        errors = _errors(H, a, b)

        inliers = (
            errors <= PIXEL_INLIER_THRESHOLD
        )

        count = int(inliers.sum())

        if count < 4:
            continue

        score = (
            count,
            -float(np.median(errors[inliers])),
        )

        if best is None or score > best[0]:
            best = (score, inliers)

    if best is None:
        result["reason"] = (
            "DEGENERATE_HOMOGRAPHY_SAMPLES"
        )
        return result

    inliers = best[1]

    for _ in range(3):
        if int(inliers.sum()) < 4:
            break

        try:
            H = _fit(a[inliers], b[inliers])
        except HomographyAuditError:
            break

        inliers = (
            _errors(H, a, b)
            <= PIXEL_INLIER_THRESHOLD
        )

    if int(inliers.sum()) >= 4:
        try:
            H = _fit(a[inliers], b[inliers])
        except HomographyAuditError:
            H = None
    else:
        H = None

    if H is None:
        result["reason"] = "REFINEMENT_DEGENERATE"
        return result

    errors = _errors(H, a, b)

    inliers = (
        errors <= PIXEL_INLIER_THRESHOLD
    )

    count = int(inliers.sum())
    ratio = count/len(a)

    result["inlier_count"] = count
    result["inlier_ratio"] = float(ratio)

    if (
        count < MIN_CORRESPONDENCES
        or ratio < MIN_RATIO
    ):
        result["reason"] = (
            "INSUFFICIENT_HOMOGRAPHY_SUPPORT"
        )
        return result

    result.update({
        "status": "TWO_D_HOMOGRAPHY_SUPPORT_OBSERVED",
        "reason": None,
        "median_inlier_error_px": float(
            np.median(errors[inliers])
        ),
        "homography_matrix": H.tolist(),
    })

    return result


def manufacture_pairs(
    kind, *, outlier_fraction=0.0
):
    if (
        kind not in (
            "general_3d",
            "planar",
            "pure_rotation",
            "unrelated",
        )
        or type(outlier_fraction) is not float
        or not 0.0 <= outlier_fraction <= 0.4
    ):
        raise HomographyAuditError(
            "Invalid manufactured scene settings"
        )

    rng = np.random.default_rng(77)
    n = 90

    xyz = np.column_stack((
        rng.uniform(-2.0, 2.0, n),
        rng.uniform(-1.6, 1.6, n),
        rng.uniform(3.0, 5.0, n),
    ))

    if kind == "planar":
        xyz[:, 2] = 4.0

    R = Rotation.from_rotvec(
        [0.04, -0.065, 0.025]
    ).as_matrix()

    t = np.array([0.8, -0.07, 0.12])

    if kind == "pure_rotation":
        t = np.zeros(3)

    other = xyz@R.T+t

    K = np.array([
        [240.0, 0, 80.0],
        [0, 235.0, 60.0],
        [0, 0, 1.0],
    ])

    source = (
        xyz[:, :2]/xyz[:, 2, None]
    )*K.diagonal()[:2]+K[:2, 2]

    target = (
        other[:, :2]/other[:, 2, None]
    )*K.diagonal()[:2]+K[:2, 2]

    source += rng.normal(
        0, 0.04, source.shape
    )
    target += rng.normal(
        0, 0.04, target.shape
    )

    if kind == "unrelated":
        target = rng.uniform(
            [10, 10], [150, 110],
            (n, 2),
        )

    count = int(n*outlier_fraction)

    if count:
        target[:count] = rng.uniform(
            [10, 10], [150, 110],
            (count, 2),
        )

    return source, target


def summarize_v15_corner_failure(record):
    if (
        record.get("status")
        != "EXISTING_V15_CORNER_FAILURE_CHARACTERIZED"
        or record.get("camera_frames_hash_verified") != 6
        or record.get("adjacent_pairs") != 5
        or record.get("accepted_sparse_pairs") != 0
        or record.get(
            "original_detection_thresholds_changed"
        ) is not False
    ):
        raise HomographyAuditError(
            "Incorrect historical V15 checkpoint"
        )

    rows = record.get(
        "per_frame_corner_diagnostics"
    )

    if not isinstance(rows, list) or len(rows) != 6:
        raise HomographyAuditError(
            "Incorrect V15 frame count"
        )

    ratios = []

    for row in rows:
        cutoff = float(
            row["original_harris_cutoff"]
        )
        eligible = float(
            row["eligible_region_max_harris_response"]
        )

        if (
            not np.isfinite(cutoff)
            or not np.isfinite(eligible)
            or cutoff <= 0
            or row["original_corner_count"] != 0
            or eligible >= cutoff
            or row["original_detector_thresholds_changed"]
               is not False
        ):
            raise HomographyAuditError(
                "Original V15 failure not reproduced"
            )

        ratios.append(eligible/cutoff)

    return {
        "schema": SCHEMA,
        "frames_with_no_eligible_corners": 6,
        "eligible_peak_over_original_cutoff": ratios,
        "largest_ratio": float(max(ratios)),
        "detector_thresholds_changed": False,
        "image_content_cause_proven": False,
        "visual_motion_factor_authorized": False,
    }


def controlled_study():
    cases = []

    scenarios = (
        ("general_3d", 0.0),
        ("planar", 0.0),
        ("planar", 0.3),
        ("pure_rotation", 0.0),
        ("unrelated", 0.0),
    )

    for kind, fraction in scenarios:
        source, target = manufacture_pairs(
            kind,
            outlier_fraction=float(fraction),
        )

        result = characterize_homography(
            source, target,
            provenance="MANUFACTURED_3D_PROJECTIONS",
        )

        should_support = kind in (
            "planar", "pure_rotation"
        )

        if (
            result["status"]
            == "TWO_D_HOMOGRAPHY_SUPPORT_OBSERVED"
        ) != should_support:
            raise ValueError(
                "Manufactured homography control mismatch"
            )

        cases.append({
            "scene": kind,
            "manufactured_outlier_fraction": fraction,
            "diagnostic": result,
        })

    return {
        "schema": SCHEMA,
        "status": "SYNTHETIC_HOMOGRAPHY_COMPETITION_STUDIED",
        "cases": cases,
        "scene_planarity_proven": False,
        "metric_pose_factors_created": False,
        "real_sensor_streams_processed": False,
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
