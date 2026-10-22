# TRUST-ROBOT KIOS R95-R96 Incremental Gaussian Checkpoint V1

Date: 2026-10-22.

Parent Git commit:
`dc82664e3d356ea362097a3b54f10f93f962ca8d`.

## Engineering accomplishment

R95 validated an incremental synthetic Gaussian prior
lifecycle over sixteen prefix evaluations. The tests
cover eleven old-state eliminations and one reset
across a synthetic IMU timestamp gap.

R96 combined the guarded R95 prior construction
with additional manufactured camera and LiDAR
6D Gaussian endpoint constraints.

R96 evaluated 28 synthetic prefixes, 20 old-state
eliminations, and camera-only, LiDAR-only and
inertial-only ablations.

R95: 19 passing tests.
R96: 33 passing tests.
Total: 52 passing regressions.

## Important methodological limitations

The incremental prefixes are recomputed for audit;
this is not proof of a streaming real-time estimator.

The Schur calculations preserve local linearized
Gaussian quadratic information. They do not
relinearize eliminated nonlinear factors or prove
posterior consistency.

R96's camera and LiDAR observations are manufactured
6D tangent-space unaries. The experiment reuses S6
assumed covariance values but does not execute the
S6 nonlinear SE(3) relative-pose measurement model.

The Gaussian information-order check does not verify
physical independence, measured sensor noise, or
real camera-LiDAR-IMU fusion accuracy.

## Scientific boundary

The 11 physical/scientific gates remain CLOSED.

No physical sensor clock, source-specific extrinsics,
independent 6DoF ground truth, real pose factors,
trained health probabilities, ATE/RPE, or
confirmation-test access is qualified.

The frozen M2DGR train/validation/confirmation split
remains unchanged.

Original ROSbags, GT and private source evidence
remain outside GitHub.

## M2DGR author request

The user reported sending a separate author inquiry
on 2026-10-22.

That external action does not alter the historical
R93 draft, does not establish a source receipt,
and does not upgrade physical evidence qualification.

## Next implementation

Develop a synthetic nonlinear same-edge
camera-LiDAR-IMU fixed-lag integration audit,
including factor ownership, proper prior lifecycle,
and negative provenance controls.

Do not substitute manufactured software behavior
for physical evidence.
