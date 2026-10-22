# TRUST-ROBOT R88–R90 Schur prior checkpoint

Date: 2026-10-22
Git parent: `c147ccaba711b8a600294b2df2b8f64f6ef6bcd4`
Publication workstation: KIOS only

## Verified implementation

R88: real Schur elimination of local 15D synthetic Gaussian information, compared with independently assembled full-batch least squares. Twenty-one regression tests.

R89: exact coordinate recentering of a frozen marginal prior; measured nonlinear Jacobian changes but no false claim that eliminated factors were relinearized. Twenty-one regression tests.

R90: typed validation of marginal-prior inputs, synthetic matrix conditioning, bounded recentering, fingerprint checks, stale-linearization rejection and cross-gap reuse denial. Twenty-seven regression tests, 30 adversarial rejections and 15 accepted recentering trials.

The publication checkpoint contains 12 SHA-256-pinned source artifacts, a verifier and compact validation receipts. Five disposable archive tamper controls are rejected.

## Research boundaries

These are development-only, local Gaussian mathematical results, not physically validated robot localization, trust inference, or a complete nonlinear probabilistic marginalizer.

No qualified physical clock alignment, independently verified sensor frames/extrinsics, real LiDAR-camera-IMU fusion, health training, independent ATE/RPE, original GT/ROSbags or confirmation-test access. The eleven scientific gates remain CLOSED.

## Checkpoint

`experiments/trust_robot_r88_r90_schur_prior_checkpoint_v1/`

Next: targeted physical qualification gap analysis using existing evidence, without repeating completed TRAIN data extraction.
