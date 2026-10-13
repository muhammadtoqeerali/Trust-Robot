# TRUST-ROBOT visual frontend checkpoint V1

Date: 2026-10-13

**Status: published software-development checkpoint.**
Not qualified 6-DoF visual odometry, physical calibration or
independently referenced localization.

## Engineering implementation

- Image-derived 2D global pixel-shift estimation.
- Bounded uint8 grayscale/RGB/RGBA image admission.
- Fourier phase correlation and local patch consistency.
- Spatially distributed image corner detection.
- Normalized local patch matching.
- Seeded robust two-dimensional affine consistency checks.
- Explicit insufficient-texture and ambiguity rejection.
- Input-image content hashing.
- Hash-verified preserved V15 camera image review.
- Explicit refusal to construct metric camera pose factors.

The published 15D marginalized estimator and previous
multimodal source-specific factor interfaces remain unchanged.

## Controlled development evidence

Global-shift fixture: 7 cases.
Sparse-correspondence fixture: 8 cases.

| Controlled sparse case | Status | Accepted patch matches |
|---|---|---:|
| translated_right | TWO_D_AFFINE_CONSISTENCY_OBSERVED | 70 |
| translated_left | TWO_D_AFFINE_CONSISTENCY_OBSERVED | 70 |
| stationary | TWO_D_AFFINE_CONSISTENCY_OBSERVED | 70 |
| small_shift | TWO_D_AFFINE_CONSISTENCY_OBSERVED | 70 |
| brightness_changed | TWO_D_AFFINE_CONSISTENCY_OBSERVED | 70 |
| different_moving_foreground | TWO_D_AFFINE_CONSISTENCY_OBSERVED | 62 |
| blackout | UNAVAILABLE | 0 |
| unrelated_image | UNAVAILABLE | 0 |

These results establish correctness only under manufactured
image transformations and disturbances.

## Preserved Isaac Sim V15 image evidence

The workstation identified one unambiguous preserved V15
recording and verified its image content hashes against
the existing compact evidence.

Camera frames checked: 6.

Adjacent image pairs attempted: 5.
Pairs passing sparse two-dimensional affine admission:
0.

| V15 image pair | Detected features | Accepted patch matches | Global shift status | 2D affine status |
|---|---:|---:|---|---|
| 1–2 | 0 | 0 | UNAVAILABLE | UNAVAILABLE |
| 2–3 | 0 | 0 | PIXEL_TRANSLATION_OBSERVED | UNAVAILABLE |
| 3–4 | 0 | 0 | PIXEL_TRANSLATION_OBSERVED | UNAVAILABLE |
| 4–5 | 0 | 0 | PIXEL_TRANSLATION_OBSERVED | UNAVAILABLE |
| 5–6 | 0 | 0 | PIXEL_TRANSLATION_OBSERVED | UNAVAILABLE |

**None of the five preserved V15 image pairs produced an
admitted sparse-affine motion estimate.**

This is a genuine negative result for the current algorithm
and these specific preserved synthetic frames. It is not
hidden, overwritten, reclassified as a successful 3D pose,
or used as a health label.

The diagnostic counts help identify whether feature
availability or correspondence/geometric consistency was
limiting, but do not establish the complete physical cause
without further image-specific investigation.

## Scientific limits

- V15 image observations are synthetic simulation captures.
- Simulation read-step times are not verified exposure times.
- No physical inter-sensor synchronization was established.
- No verified camera intrinsics or full extrinsics were used.
- A 2D shift/affine transform is not a metric SE(3) motion.
- No visual relative-pose factors were admitted to the
  15D real-data estimator.
- No independent localization ATE/RPE was computed.
- No real sensor-health training labels were created.
- No empirically calibrated health probabilities, factor
  weights, or safety decisions were generated.

No metric motion scale was inferred.
No frozen scientific authorization gate was changed.

## Validation and reproduction

The final release executed 239 tests across 24 test suites.

    PYTHONPATH=src python -B tests/trust_robot/test_visual_pixel_motion.py -v
    PYTHONPATH=src python -B tests/trust_robot/test_visual_sparse_correspondence.py -v
    PYTHONPATH=src python -B tests/trust_robot/test_v15_sparse_visual_review.py -v

The full V15 result details and canonical source SHA256 evidence
are retained in the KIOS project-local experiment directories.

## Next research and implementation phase

1. Characterize the V15 failures using the verified frame
   content and current matching diagnostics.
2. Avoid threshold changes selected merely to force acceptance.
3. Implement a mathematically valid calibrated two-view
   geometry checker under explicitly manufactured camera
   intrinsics and independent test correspondences.
4. Qualify real camera intrinsic/extrinsic evidence before
   applying such geometry to recorded sensor streams.
5. Treat translation direction and metric scale separately.
6. Require independent reference and temporal association
   evidence before localization scoring or execution.

The next phase should move toward valid camera constraints
rather than treating synthetic image shifts as visual odometry.
