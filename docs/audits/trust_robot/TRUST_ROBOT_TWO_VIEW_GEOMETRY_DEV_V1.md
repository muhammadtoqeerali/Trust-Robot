# TRUST-ROBOT two-view geometry development V1

**Status:** offline mathematical qualification of manufactured
calibrated image correspondences; V15 feature-failure audit.

No physical camera calibration or authorized real-data visual
odometry is established.

## New mathematical implementation

- Eight-point essential-matrix estimation.
- Hartley coordinate conditioning and rank-two fitting.
- Essential equal-singular-value constraint in camera rays.
- Deterministic outlier-resistant epipolar model selection.
- Source-specific inlier and Sampson-error reporting.
- Four candidate relative-motion decomposition.
- Cheirality and minimum-parallax checks.
- Unavailable output for unsupported translation direction.
- Explicit projective metric-scale ambiguity demonstration.

The camera intrinsics are **manufactured and known in the
synthetic experiment only**.

A relative rotation and unit translation direction are not
a metrically scaled camera-to-body SE(3) pose factor.

## Manufactured mathematical experiments

| Experiment | Diagnostic status | Epipolar inliers |
|---|---|---:|
| known_nonplanar_geometry | MANUFACTURED_TWO_VIEW_DIRECTION_RECOVERED | 90 |
| quarter_false_correspondences | MANUFACTURED_TWO_VIEW_DIRECTION_RECOVERED | 69 |
| thirtyfive_pct_false_correspondences | MANUFACTURED_TWO_VIEW_DIRECTION_RECOVERED | 60 |
| pure_rotation | UNAVAILABLE | 90 |

Projective scene-scale ambiguity demonstrated:
True.

This experiment does not establish performance against
real image tracking errors, radial distortion, rolling
shutter, planar degeneracy or general dynamic environments.

## Preserved V15 image bottleneck

Six original V15 synthetic camera frames were revalidated
by the published content hashes.

The unchanged sparse detector produced the following
per-image measurements:

| Frame | Intensity std | Eligible Harris peak | Original threshold | Corners |
|---|---:|---:|---:|---:|
| 1 | 48.124 | 0.064364 | 2000 | 0 |
| 2 | 67.486 | 0.015824 | 2000 | 0 |
| 3 | 67.585 | 0.049136 | 2000 | 0 |
| 4 | 67.952 | 0.054836 | 2000 | 0 |
| 5 | 67.697 | 0.009264 | 2000 | 0 |
| 6 | 67.477 | 0.033584 | 2000 | 0 |

All five adjacent V15 pairs remain unavailable to the
published sparse-affine frontend.

This phase **does not alter existing threshold values**.
The measured intensity, gradient and corner responses
provide a factual explanation of the software admission
path, not a definitive external scene-capture diagnosis.

No fabricated visual feature, pose or health label is used
to replace unavailable V15 measurements.

## Scientific boundaries

- Real M2DGR intrinsics remain unverified.
- Physical camera capture timing remains unverified.
- Camera/LiDAR/IMU extrinsics are not fully qualified.
- Translation scale remains unavailable from this
  monocular mathematical construction.
- Pure rotation does not justify a translation direction.
- Recorded sensor factors and real-data scoring remain blocked.
- Independent reference measurements are not introduced.
- Health model training and reliability weighting do not run.
- No physical robot, ROS stream or GPU session was used.
- All frozen scientific authorization protocols remain intact.

## Reproduction

    PYTHONPATH=src python -B tests/trust_robot/test_visual_two_view_geometry.py -v
    PYTHONPATH=src python -B tests/trust_robot/test_v15_visual_corner_audit.py -v

Detailed results, frame-level diagnostics and source
hashes remain in the dedicated KIOS experiment directory.

## Next implementation

Introduce a rigorously characterized matching frontend
that handles low-texture and general motion more reliably,
while preserving unavailable decisions when justified.

Use real, independently qualified camera calibration before
applying epipolar geometry to recorded imagery.

Before metric camera factors become admissible, separately
resolve translation scale, extrinsics and capture-time
association under frozen evaluation rules.
