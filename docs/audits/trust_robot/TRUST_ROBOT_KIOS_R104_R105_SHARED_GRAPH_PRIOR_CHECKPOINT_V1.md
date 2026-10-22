# TRUST-ROBOT R104-R105 checkpoint audit

Date: 2026-10-22.

Parent:
b20f4b8a89b4521c509f0856d4e3d4aebe90de37

## R104 — Shared manufactured factor graph

48 passing regression tests.

Verified a five-node, eight-IMU-sample,
four-inertial-factor synthetic graph.

Three experimental configurations generated
twelve nonlinear S6 windows and nine Schur
marginalizations.

Camera and LiDAR measurements used distinct
software identities, frame claims and
manufactured covariance assumptions.

All inputs came from the analytic simulator.

## R105 — Local nonlinear prior transfer

33 passing regression tests.

Nine Schur priors produced by the existing S6
nonlinear marginalization routine were recentered
and returned to subsequent S6 optimization windows.

Local square-root residual equivalence,
information preservation, gradient-coordinate
transformation, factor ownership and comparison
with unmodified S6 were checked.

The R105 development sequence required two fixes:

1. Pose-factor lineage excluded measurements
   consumed by earlier marginalizations.
2. R104 graph validation errors were translated
   to the R105 public TransferError type.

Both corrections passed regression testing.

## Scope limitation

This is SAME-GRAPH synthetic prior recentering.
It does not merge R95's incompatible independent
Gaussian prior history into S6.

Local mathematical equivalence does not prove
global nonlinear posterior consistency.

Assumed noise levels do not establish calibrated
probabilistic confidence.

No physical sensor synchronization, extrinsics,
real visual odometry, independent 6DoF GT scoring,
ATE/RPE or calibrated health training is authorized.

The frozen M2DGR split remains 22/7/7.
The confirmation_test partition remains sealed.
Original ROSbags and GT remain outside Git.

All 11 scientific gates remain CLOSED.

## Next phase

Design and validate a bounded synthetic
same-graph incremental estimator interface,
preserving chronological factor ownership,
explicit gauge and local-linearization tokens.

Do not import R95 priors into S6 without
resolving the eight earlier compatibility blockers.
