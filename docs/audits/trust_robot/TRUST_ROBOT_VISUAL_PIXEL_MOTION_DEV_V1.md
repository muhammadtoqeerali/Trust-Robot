# TRUST-ROBOT visual pixel motion development V1

**Status:** image-derived 2D motion frontend developed and
validated on controlled synthetic image transformations.

The experiment is not metric 6-DoF visual odometry.

## Engineering implementation

A new offline frontend uses genuine image pixel intensities:

1. Grayscale conversion from uint8 image arrays.
2. Fourier phase correlation for global integer pixel shift.
3. Local normalized image-patch correspondence checks.
4. Deterministic evidence and input SHA256 reporting.
5. Texture/ambiguity rejection with explicit unavailable status.
6. Read-only, hash-verified preserved V15 camera review.
7. An explicit prohibition on converting pixel shift directly
   into a metric visual pose factor.

No existing estimator or Phase-7/8 protocol was modified.

## Controlled image experiments

| Case | Output status | DX (pixels) | DY (pixels) |
|---|---|---:|---:|
| right_and_up | PIXEL_TRANSLATION_OBSERVED | 5 | -3 |
| left_and_down | PIXEL_TRANSLATION_OBSERVED | -6 | 4 |
| stationary | PIXEL_TRANSLATION_OBSERVED | 0 | 0 |
| small_right | PIXEL_TRANSLATION_OBSERVED | 2 | 0 |
| affine_brightness_changed | PIXEL_TRANSLATION_OBSERVED | 4 | -2 |
| camera_blackout | UNAVAILABLE | None | None |
| unrelated_texture | UNAVAILABLE | None | None |

These artificial image operations were used to verify
implementation correctness. Numeric acceptance thresholds
are internal development guards, not calibrated health
decision thresholds or physically selected visual quality gates.

## Local V15 camera frame review

Status: `NO_UNAMBIGUOUS_LOCAL_V15_RECORDING`.

The existing V15 frame arrays are synthetic Isaac Sim
recordings, not M2DGR camera measurements.

When one unambiguous local recording exists, the script
checks all camera-frame content hashes and evaluates adjacent
camera frames using only their image pixels.

When absent or ambiguous, the review is explicitly reported
as not executed, rather than inventing missing results.

The V15 simulation read-step times are not verified
physical capture times or camera/LiDAR synchronization.

## Remaining science and engineering

- Implement richer, independently verified 2D feature tracking.
- Qualify camera intrinsics and relative-motion geometry.
- Resolve metric scale and camera-to-body transformations.
- Associate sensor capture times only with evidence-backed rules.
- Convert eligible visual constraints to properly modelled
  camera factors, with source-specific covariance.
- Preserve independent camera and LiDAR factors when
  scientifically justified.
- Keep reference scoring and runtime health conditioning
  disabled until their frozen conditions are satisfied.

No pose estimate, metric visual odometry, independent
reference score, health label, physical calibration, or
safety action is produced in this phase.

## Reproduction

    PYTHONPATH=src python -B tests/trust_robot/test_visual_pixel_motion.py -v
    PYTHONPATH=src python -B tests/trust_robot/test_v15_visual_motion_review.py -v

An optional preserved V15 image review can be repeated with:

    PYTHONPATH=src python -B scripts/trust_robot/run_v15_visual_motion_v1.py --recording RECORDING --compact-evidence EVIDENCE

Detailed results and input-provenance evidence remain in
the dedicated KIOS experiment directory.
