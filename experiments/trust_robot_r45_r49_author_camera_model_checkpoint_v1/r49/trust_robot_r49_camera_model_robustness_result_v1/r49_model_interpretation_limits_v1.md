# R49 — Synthetic camera-model interpretation and subpixel robustness

Only 64 R48 manufactured pixels and author Git-verified camera model coefficients were used; the 16 recorded R33 frames provide dimensions only. No original sensor image or recording bytes were read.

Author-supplied 3x3 intrinsic matrix appears transposed relative to conventional OpenCV row-major K. Treating raw flattened values as conventional K moves the principal point to (0,0) and yields a substantial **model interpretation error**, not a measured sensor error.

## Numerical effects (angular ray differences only)

- ignore_distortion: median 0.349395331 degrees, maximum 0.630047036 degrees.
- raw_author_K_wrong_standard_intrinsics: median 32.5891183 degrees, maximum 37.0557042 degrees.
- synthetic_half_pixel_xy: median 0.0579078532 degrees, maximum 0.0656412352 degrees.

Radial forward model Jacobian on sampled domain: minimum 0.98922147, maximum 1.04523566 (positive implies local radial monotonicity here only).

Synthetic pixel-noise assumption: four deterministic ±0.5 px offsets per point, 256 numerical ray comparisons. These are not recorded tracking errors, camera calibration residuals, or covariance measurements.

## Scientific restrictions

**NOT QUALIFIED:** Camera model consistency and robustness checks do **not** establish room_02 physical intrinsics, real pose accuracy, physical timing, metric scale, valid cross-sensor extrinsics, or health supervision. Source author intrinsics are candidate parameters. 11 R43 physical admission gates remain closed. No ATE/RPE or confirmation_test use.

## Next R50

SHA-pinned guarded archival of R45–R49, including original and repaired R46 independent verifier and three exact author calibration source files. GitHub commit and push only after complete independent checkpoint verification.
