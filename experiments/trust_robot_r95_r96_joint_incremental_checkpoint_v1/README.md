# TRUST-ROBOT R95-R96 Synthetic Incremental Gaussian Checkpoint

Date: 2026-10-22.

Parent Git commit:
`dc82664e3d356ea362097a3b54f10f93f962ca8d`.

## R95

Integrated the existing manufactured 15D inertial factor
linearizations with a guarded Schur-prior lifecycle.

Results:

- 19 regression tests passed.
- Four synthetic scenarios.
- Sixteen prefix evaluations.
- Eleven old-state eliminations.
- One timestamp gap.
- Zero cross-gap prior transfers.
- Independent full-batch Gaussian comparisons.

R95 recomputes prefixes for validation. It is not a
validated real-time nonlinear marginalizer.

## R96

Integrated additional manufactured camera and LiDAR
6D tangent-space unary constraints with the R95
Gaussian inertial prior.

Results:

- 33 regression tests passed.
- Four synthetic scenarios.
- Three continuous-sequence ablations.
- Twenty-eight prefix evaluations in total.
- Twenty old-state eliminations.
- Independent Gaussian full-batch comparisons.
- Distinct assumed camera and LiDAR covariances.
- Zero cross-gap prior transfers.

The camera and LiDAR constraints are manufactured
Gaussian endpoint observations. They are not
physical camera images, LiDAR registrations, or
S6 nonlinear SE(3) relative-pose factors.

The information-order comparison concerns
assumed Gaussian constraints, not empirical
sensor independence or calibrated uncertainty.

## Scientific restrictions

All 11 scientific gates remain CLOSED.

This checkpoint does not authorize:

- recorded sensor pose factors;
- physical clock or extrinsic verification;
- real multimodal localization claims;
- calibrated health probabilities or training;
- ATE/RPE evaluation;
- reference association or interpolation;
- confirmation-test access.

No raw ROSbags, original GT, private evidence,
or recorded sensor streams are archived.

The R93 author-request draft remains an unchanged
historical artifact. The user subsequently reported
sending a separate inquiry to the M2DGR authors;
no author response or qualified source is included
in this software checkpoint.

## Verification

From the repository root:

`python3 -B experiments/trust_robot_r95_r96_joint_incremental_checkpoint_v1/verify_checkpoint.py verify experiments/trust_robot_r95_r96_joint_incremental_checkpoint_v1`

The archive contains SHA-pinned R95/R96 source,
tests, reports, validation receipts, and its
standalone integrity verifier.
