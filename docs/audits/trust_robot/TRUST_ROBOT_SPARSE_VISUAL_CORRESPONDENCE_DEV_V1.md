# TRUST-ROBOT sparse image correspondence development V1

**Status:** offline 2D image-feature development validation.

This implementation adds actual pixel-feature correspondences and
a robust two-dimensional affine image-consistency diagnostic.
It does not implement metric 6-DoF visual odometry.

## Implemented

- Spatially distributed image corner detection.
- Local 9x9 normalized grayscale patch correlation.
- Explicit patch-match ambiguity rejection.
- Seeded robust 2D affine consistency estimation.
- Spatial support and reprojection-error reporting.
- Controlled image shift and photometric experiments.
- Rejection of unrelated images and missing texture.
- Hash-verified offline V15 image-review integration.
- Explicit metric SE(3) camera-factor execution blocker.

The code uses the established frozen visual pixel frontend,
without modifying that frontend or the published estimator.

## Controlled image cases

| Case | Status | Corner features | Patch matches |
|---|---|---:|---:|
| translated_right | TWO_D_AFFINE_CONSISTENCY_OBSERVED | 70 | 70 |
| translated_left | TWO_D_AFFINE_CONSISTENCY_OBSERVED | 70 | 70 |
| stationary | TWO_D_AFFINE_CONSISTENCY_OBSERVED | 70 | 70 |
| small_shift | TWO_D_AFFINE_CONSISTENCY_OBSERVED | 70 | 70 |
| brightness_changed | TWO_D_AFFINE_CONSISTENCY_OBSERVED | 70 | 70 |
| different_moving_foreground | TWO_D_AFFINE_CONSISTENCY_OBSERVED | 70 | 62 |
| blackout | UNAVAILABLE | 70 | 0 |
| unrelated_image | UNAVAILABLE | 70 | 0 |

There were 8 controlled development cases.

All numeric thresholds remain implementation-test settings,
not physically validated sensor-health or trust thresholds.

## Preserved V15 image evaluation

Status: `HASH_VERIFIED_V15_SPARSE_REVIEW`.

Recording candidates identified: 1.
Search truncated: False.

A successful recorded-image review requires unambiguous,
content-hash-verified preserved V15 camera files.

The V15 camera is synthetic. Simulation read-step timestamps
do not prove actual sensor capture-time synchronization.

If review was not executed, no preserved-image result is
claimed from the controlled tests.

## Scientific limits

A coherent 2D affine image transform does not establish:

- calibrated epipolar geometry;
- depth or metric translation scale;
- physical camera extrinsics;
- rolling-shutter compensation;
- robust scene-level visual odometry;
- real cross-modal temporal association;
- independent reference localization accuracy;
- a calibrated three-class sensor health label;
- an admissible camera factor for the 15D real-data estimator.

No physical robot, GPU Isaac Sim session, empirical health
classifier, learned reliability weighting or safety control
was used in this development experiment.

All frozen scientific authorization boundaries remain closed.

## Reproduction

    PYTHONPATH=src python -B tests/trust_robot/test_visual_sparse_correspondence.py -v
    PYTHONPATH=src python -B tests/trust_robot/test_v15_sparse_visual_review.py -v

For an existing, verified V15 recording:

    PYTHONPATH=src python -B scripts/trust_robot/run_v15_sparse_visual_review_v1.py --recording RECORDING --compact-evidence EVIDENCE

## Next steps

Qualify multi-view geometry using actual image correspondences,
with explicitly known or independently verified camera intrinsics.

Distinguish image translation, rotation, parallax and moving
objects before generating visual motion constraints.

Metric pose-factor construction must remain disabled until
depth/scale, calibration and temporal provenance are justified.
