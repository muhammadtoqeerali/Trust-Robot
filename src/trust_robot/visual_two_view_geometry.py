"""Development-only calibrated two-view epipolar geometry.

Eight-point essential estimation with Hartley normalization,
rank-two fitting, a calibrated essential constraint, deterministic
RANSAC, cheirality selection and minimum angular parallax.

Known K is explicitly MANUFACTURED, not physically calibrated.
Output rotation and unit translation direction are synthetic
geometry diagnostics, NOT metric SE(3) pose factors.

No depth/translation scale, actual capture-time association,
camera-to-body extrinsic, physical observability, calibrated
covariance, safety command or health probability is inferred.
"""
from __future__ import annotations

import json

import numpy as np
from scipy.spatial.transform import Rotation

SCHEMA = "TRUST_ROBOT_TWO_VIEW_GEOMETRY_DEV_V1"
PROVENANCE = "MANUFACTURED_KNOWN_INTRINSICS"

RANSAC_SEED = 20261013
RANSAC_TRIALS = 384
EPIPOLAR_INLIER_THRESHOLD_NORMALIZED = 0.0025
MIN_CORRESPONDENCES = 36
MIN_INLIER_RATIO = 0.60
MIN_PARALLAX_RAD = 0.01
MIN_POSITIVE_DEPTH_RATIO = 0.70


class TwoViewGeometryError(ValueError):
    pass


def validate_inputs(a, b, K, provenance):
    if provenance != PROVENANCE:
        raise TwoViewGeometryError(
            "Unqualified or physical intrinsics are not authorized"
        )

    x = np.asarray(a, dtype=float)
    y = np.asarray(b, dtype=float)
    k = np.asarray(K, dtype=float)

    if (
        x.ndim != 2 or x.shape[1:] != (2,)
        or x.shape != y.shape
        or len(x) > 300
        or k.shape != (3, 3)
        or not np.isfinite(x).all()
        or not np.isfinite(y).all()
        or not np.isfinite(k).all()
        or k[0, 0] <= 0 or k[1, 1] <= 0
        or not np.allclose(k[2], [0, 0, 1], atol=1e-12)
        or not np.allclose(k[[0, 1], [1, 0]], 0, atol=1e-12)
    ):
        raise TwoViewGeometryError(
            "Malformed synthetic two-view inputs"
        )

    return x, y, k


def _hartley(points):
    center = points.mean(axis=0)
    difference = points-center
    mean_norm = float(
        np.mean(np.linalg.norm(difference, axis=1))
    )

    if mean_norm <= 1e-10:
        raise TwoViewGeometryError("Degenerate 2D point spread")

    scale = np.sqrt(2.0)/mean_norm

    transform = np.array([
        [scale, 0, -scale*center[0]],
        [0, scale, -scale*center[1]],
        [0, 0, 1],
    ])

    return difference*scale, transform


def _eight_point(x1, x2):
    if len(x1) < 8:
        raise TwoViewGeometryError(
            "Eight-point estimation requires eight observations"
        )

    q1, T1 = _hartley(x1)
    q2, T2 = _hartley(x2)

    u, v = q1.T
    p, q = q2.T

    A = np.column_stack((
        p*u, p*v, p,
        q*u, q*v, q,
        u, v, np.ones(len(u)),
    ))

    if np.linalg.matrix_rank(A) < 8:
        raise TwoViewGeometryError(
            "Degenerate epipolar design"
        )

    # Full V is necessary for a minimal 8x9 design.
    _, _, Vt = np.linalg.svd(A, full_matrices=True)

    raw = Vt[-1].reshape(3, 3)

    # In Hartley coordinates this is a fundamental-like
    # matrix: enforce rank TWO, not equal singular values.
    U, s, Vt = np.linalg.svd(raw)
    rank_two = U @ np.diag([s[0], s[1], 0]) @ Vt

    # Return to the originally supplied normalized camera rays.
    E = T2.T @ rank_two @ T1

    # Essential equal-singular-value constraint belongs HERE,
    # after denormalization into calibrated ray coordinates.
    U, s, Vt = np.linalg.svd(E)
    common = float((s[0]+s[1])/2.0)

    if common <= 1e-12:
        raise TwoViewGeometryError(
            "Vanishing essential information"
        )

    E = U @ np.diag([common, common, 0]) @ Vt
    return E/np.linalg.norm(E)


def _sampson(E, x1, x2):
    a = np.column_stack((x1, np.ones(len(x1))))
    b = np.column_stack((x2, np.ones(len(x2))))

    l2 = a @ E.T
    l1 = b @ E

    numerator = np.sum(b*l2, axis=1)**2
    denominator = (
        l1[:, 0]**2 + l1[:, 1]**2
        + l2[:, 0]**2 + l2[:, 1]**2
    )

    return np.sqrt(
        numerator/np.maximum(denominator, 1e-16)
    )


def _triangulate_positive(R, t, x1, x2):
    P1 = np.column_stack((np.eye(3), np.zeros(3)))
    P2 = np.column_stack((R, t))

    A = np.stack((
        x1[:, 0, None]*P1[2]-P1[0],
        x1[:, 1, None]*P1[2]-P1[1],
        x2[:, 0, None]*P2[2]-P2[0],
        x2[:, 1, None]*P2[2]-P2[1],
    ), axis=1)

    _, _, Vt = np.linalg.svd(A)
    homogeneous = Vt[:, -1, :]

    valid = abs(homogeneous[:, 3]) > 1e-12
    xyz = np.zeros((len(x1), 3))
    xyz[valid] = (
        homogeneous[valid, :3]
        / homogeneous[valid, 3, None]
    )

    camera2 = xyz @ R.T + t

    return (
        valid
        & (xyz[:, 2] > 0)
        & (camera2[:, 2] > 0)
    )


def _recover_direction(E, x1, x2):
    U, _, Vt = np.linalg.svd(E)

    if np.linalg.det(U@Vt) < 0:
        Vt[-1] *= -1

    W = np.array([
        [0, -1, 0],
        [1, 0, 0],
        [0, 0, 1],
    ])

    rotations = (U@W@Vt, U@W.T@Vt)
    direction = U[:, 2]

    best = None

    for R in rotations:
        if np.linalg.det(R) < 0:
            continue

        for t in (direction, -direction):
            positive = _triangulate_positive(
                R, t, x1, x2
            )
            count = int(positive.sum())

            if best is None or count > best[0]:
                best = (count, R.copy(), t.copy())

    if best is None:
        return None

    positive_count, R, t = best

    rays1 = np.column_stack((
        x1, np.ones(len(x1))
    ))
    rays2 = np.column_stack((
        x2, np.ones(len(x2))
    ))

    rays1 /= np.linalg.norm(
        rays1, axis=1
    )[:, None]

    rays2 /= np.linalg.norm(
        rays2, axis=1
    )[:, None]

    rays2_in_first = rays2 @ R

    angles = np.arccos(np.clip(
        np.sum(
            rays1*rays2_in_first,
            axis=1,
        ),
        -1, 1,
    ))

    return {
        "positive_count": positive_count,
        "positive_ratio": positive_count/len(x1),
        "median_angular_parallax_rad": float(
            np.median(angles)
        ),
        "rotation_matrix": R.tolist(),
        "translation_direction_unit": t.tolist(),
    }


def estimate_two_view(
    source_px,
    target_px,
    intrinsics,
    *,
    intrinsics_provenance=PROVENANCE,
):
    a, b, K = validate_inputs(
        source_px,
        target_px,
        intrinsics,
        intrinsics_provenance,
    )

    output = {
        "schema": SCHEMA,
        "status": "UNAVAILABLE",
        "correspondence_count": len(a),
        "inlier_count": 0,
        "inlier_ratio": 0.0,
        "median_sampson_error_normalized": None,
        "essential_matrix": None,
        "geometry": None,
        "reason": None,
        "intrinsics_provenance": PROVENANCE,
        "translation_scale_observable": False,
        "metric_translation_estimated": False,
        "physical_camera_calibration_verified": False,
        "physical_pose_factor_created": False,
        "planar_degeneracy_fully_qualified": False,
        "camera_to_body_extrinsics_verified": False,
        "physical_capture_time_verified": False,
    }

    if len(a) < MIN_CORRESPONDENCES:
        output["reason"] = "TOO_FEW_CORRESPONDENCES"
        return output

    focal = K.diagonal()[:2]
    center = K[:2, 2]

    x1 = (a-center)/focal
    x2 = (b-center)/focal

    rng = np.random.default_rng(RANSAC_SEED)
    best = None

    for _ in range(RANSAC_TRIALS):
        chosen = rng.choice(
            len(a), 8, replace=False
        )

        try:
            E = _eight_point(
                x1[chosen], x2[chosen]
            )
        except TwoViewGeometryError:
            continue

        error = _sampson(E, x1, x2)
        accepted = (
            error < EPIPOLAR_INLIER_THRESHOLD_NORMALIZED
        )

        count = int(accepted.sum())

        if count == 0:
            continue

        score = (
            count,
            -float(np.median(error[accepted])),
        )

        if best is None or score > best[0]:
            best = (score, accepted)

    if (
        best is None
        or int(best[1].sum()) < MIN_CORRESPONDENCES
    ):
        output["reason"] = "EPIPOLAR_SUPPORT_UNAVAILABLE"
        return output

    accepted = best[1]

    for _ in range(3):
        if int(accepted.sum()) < MIN_CORRESPONDENCES:
            output["reason"] = "EPIPOLAR_REFINEMENT_UNAVAILABLE"
            return output

        try:
            E = _eight_point(
                x1[accepted],
                x2[accepted],
            )
        except TwoViewGeometryError:
            output["reason"] = "DEGENERATE_EPIPOLAR_GEOMETRY"
            return output

        error = _sampson(E, x1, x2)
        accepted = (
            error < EPIPOLAR_INLIER_THRESHOLD_NORMALIZED
        )

    count = int(accepted.sum())
    ratio = count/len(a)

    output["inlier_count"] = count
    output["inlier_ratio"] = float(ratio)

    if (
        count < MIN_CORRESPONDENCES
        or ratio < MIN_INLIER_RATIO
    ):
        output["reason"] = "INSUFFICIENT_EPIPOLAR_INLIERS"
        return output

    E = _eight_point(
        x1[accepted], x2[accepted]
    )

    error = _sampson(E, x1, x2)

    output["median_sampson_error_normalized"] = float(
        np.median(error[accepted])
    )

    geometry = _recover_direction(
        E, x1[accepted], x2[accepted]
    )

    if geometry is None:
        output["reason"] = "CHEIRALITY_UNAVAILABLE"
        return output

    if (
        geometry["positive_ratio"]
        < MIN_POSITIVE_DEPTH_RATIO
    ):
        output["reason"] = "INSUFFICIENT_POSITIVE_DEPTH_SUPPORT"
        return output

    if (
        geometry["median_angular_parallax_rad"]
        < MIN_PARALLAX_RAD
    ):
        output["reason"] = "INSUFFICIENT_TRANSLATIONAL_PARALLAX"
        return output

    output.update({
        "status": "MANUFACTURED_TWO_VIEW_DIRECTION_RECOVERED",
        "reason": None,
        "essential_matrix": E.tolist(),
        "geometry": geometry,
    })

    return output


def manufacture_case(
    *,
    seed=42,
    outlier_fraction=0.0,
    pure_rotation=False,
    scene_scale=1.0,
):
    """Known synthetic projection with noncoplanar scene depth.

    Matching pixels are generated from 3D points. Estimation
    receives ONLY paired 2D coordinates and manufactured K.
    Truth is for separate mathematical verification only.
    """
    if (
        type(seed) is not int or seed < 0
        or not 0 <= outlier_fraction <= 0.4
        or not 0.2 <= scene_scale <= 4.0
        or type(pure_rotation) is not bool
    ):
        raise TwoViewGeometryError(
            "Invalid manufactured geometry controls"
        )

    rng = np.random.default_rng(seed)
    n = 90

    xyz = np.column_stack((
        rng.uniform(-2.2, 2.2, n),
        rng.uniform(-1.8, 1.8, n),
        rng.uniform(3.0, 5.0, n),
    ))*scene_scale

    R = Rotation.from_rotvec(
        [0.04, -0.065, 0.025]
    ).as_matrix()

    t = np.array([0.8, -0.07, 0.12])
    t = t*scene_scale

    if pure_rotation:
        t = t*0.0

    other = xyz@R.T + t

    camera1 = xyz[:, :2]/xyz[:, 2, None]
    camera2 = other[:, :2]/other[:, 2, None]

    K = np.array([
        [240., 0., 80.],
        [0., 235., 60.],
        [0., 0., 1.],
    ])

    source = (
        camera1*K.diagonal()[:2]+K[:2, 2]
    )

    target = (
        camera2*K.diagonal()[:2]+K[:2, 2]
    )

    source += rng.normal(0, 0.04, source.shape)
    target += rng.normal(0, 0.04, target.shape)

    outliers = int(n*outlier_fraction)

    if outliers:
        target[:outliers] = rng.uniform(
            [10., 10.], [150., 110.],
            (outliers, 2),
        )

    return {
        "K": K,
        "source": source,
        "target": target,
        "R_truth": R,
        "t_truth": t,
        "manufactured_outlier_count": outliers,
    }


def controlled_study():
    scenarios = []

    for name, config in (
        ("known_nonplanar_geometry", {}),
        ("quarter_false_correspondences", {
            "outlier_fraction": 0.25,
        }),
        ("thirtyfive_pct_false_correspondences", {
            "outlier_fraction": 0.35,
        }),
        ("pure_rotation", {
            "pure_rotation": True,
        }),
    ):
        generated = manufacture_case(**config)

        result = estimate_two_view(
            generated["source"],
            generated["target"],
            generated["K"],
        )

        if name == "pure_rotation":
            if result["status"] != "UNAVAILABLE":
                raise ValueError(
                    "Pure rotation incorrectly admitted as translation"
                )
        else:
            if result["status"] != (
                "MANUFACTURED_TWO_VIEW_DIRECTION_RECOVERED"
            ):
                raise ValueError(
                    "Manufactured two-view geometry unavailable"
                )

            R_est = np.asarray(
                result["geometry"]["rotation_matrix"]
            )
            t_est = np.asarray(
                result["geometry"]["translation_direction_unit"]
            )

            angular_error = Rotation.from_matrix(
                R_est@generated["R_truth"].T
            ).magnitude()

            truth_direction = (
                generated["t_truth"]
                / np.linalg.norm(generated["t_truth"])
            )

            if (
                angular_error > np.deg2rad(1)
                or float(t_est@truth_direction) < 0.98
            ):
                raise ValueError(
                    "Manufactured two-view direction inconsistent"
                )

        scenarios.append({
            "scenario": name,
            "measurement": result,
            "truth_used_for_fixture_validation_only": True,
        })

    first = manufacture_case(scene_scale=1)
    scaled = manufacture_case(scene_scale=2)

    if not (
        np.allclose(first["source"], scaled["source"], atol=1e-10)
        and np.allclose(first["target"], scaled["target"], atol=1e-10)
    ):
        raise ValueError(
            "Projective scale ambiguity control failed"
        )

    return {
        "schema": SCHEMA,
        "status": "MANUFACTURED_TWO_VIEW_GEOMETRY_STUDIED",
        "case_count": len(scenarios),
        "cases": scenarios,
        "projective_scene_scale_ambiguity_demonstrated": True,
        "metric_translation_scale_recovered": False,
        "real_camera_intrinsics_verified": False,
        "physical_camera_pose_factors_authorized": False,
        "held_out_real_reference_used": False,
    }


def require_real_camera_pose_factor(*args, **kwargs):
    raise TwoViewGeometryError(
        "Manufactured two-view geometry does not authorize real "
        "metric pose factors, physical intrinsics, extrinsics "
        "or capture-time association"
    )


def canonical(value):
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ) + "\n"
    ).encode("utf-8")
