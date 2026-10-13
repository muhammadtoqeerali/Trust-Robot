# TRUST-ROBOT visual geometry robustness checkpoint V1

Date: 2026-10-13

**Status:** offline scientific development, not qualified
real-camera localization or physical calibration.

## Implemented

- Manufactured calibrated two-view essential estimation.
- Robust epipolar fitting and cheirality checks.
- Synthetic translation-direction and rotation tests.
- Projective metric-scale ambiguity verification.
- Pure-rotation translation rejection.
- Separate robust image homography diagnostic.
- Planar, pure-rotation, general-3D and outlier controls.
- Controlled image-pixel correspondence integration.
- Original preserved V15 corner-bottleneck characterization.

## Homography compatibility study

| Manufactured scene | Outlier fraction | 2D status | Inliers |
|---|---:|---|---:|
| general_3d | 0.0 | UNAVAILABLE | 14 |
| planar | 0.0 | TWO_D_HOMOGRAPHY_SUPPORT_OBSERVED | 90 |
| planar | 0.3 | TWO_D_HOMOGRAPHY_SUPPORT_OBSERVED | 63 |
| pure_rotation | 0.0 | TWO_D_HOMOGRAPHY_SUPPORT_OBSERVED | 90 |
| unrelated | 0.0 | UNAVAILABLE | 4 |

A strong homography may be produced by a plane, pure
rotation or a dominant image plane. It is not independent
proof of a specific physical scene geometry.

Conversely, weak single-homography support does not
independently certify a valid general-3D camera pose.

The numerical thresholds are development-only and have
not been calibrated as reliability/health thresholds.

## Original V15 visual limitation

Verified synthetic camera frames: 6.
Adjacent sparse image pairs admitted: 0 of 5.

Frames without eligible original detector corners:
6.

Largest interior Harris-response-to-original-cutoff ratio:
3.2182e-05.

This explains the original detector's fail-closed corner
admission on these images, without identifying a unique
physical/rendering root cause.

The original corner thresholds are unchanged.
No recorded frame has been modified or relabelled.

## Regression evidence

The combined phase passed 268 tests across 27 suites,
including the prior 256-test checkpoint.

The previous estimator API, source admission, visual
feature frontends and frozen scientific protocols remain
unchanged.

## Critical scientific restrictions

- M2DGR camera intrinsics are not independently verified.
- Camera exposure and cross-modal timing are not qualified.
- Camera-to-body and camera-to-LiDAR extrinsics remain blocked.
- No metric monocular translation scale is available.
- The synthetic known-K experiment is not real calibration.
- No real camera pose factor was constructed.
- No physical estimator localization scoring occurred.
- No real health labels or calibrated reliability weights
  were generated.
- No GPU Isaac Sim runtime or physical robot was used.

Physical fusion and independently referenced evaluation
remain subject to the previously frozen evidence gates.

## Next development milestone

Advance toward a visual motion frontend using admissible
geometric scene structure, image tracking and independent
camera calibration evidence.

Do not force the five unavailable V15 pairs to pass by
lowering thresholds. Evaluate better feature tracking
or camera acquisition only with separately justified
development criteria and provenance.

Once new source and geometry qualifications are available,
connect only admissible constraints to the already published
source-specific 15D estimator.
