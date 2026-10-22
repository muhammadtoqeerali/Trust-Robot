# TRUST-ROBOT R104-R105 synthetic graph and prior checkpoint

Date: 2026-10-22.

Parent commit:
b20f4b8a89b4521c509f0856d4e3d4aebe90de37

## R104 — Shared synthetic factor graph

48 tests passed.

The existing S6 synthetic generator supplied:

- Five synthetic estimator nodes.
- Eight nonoverlapping IMU samples.
- Four preintegrated IMU factors.
- Independent camera and LiDAR factor identities.
- Twelve nonlinear windows over three scenarios.
- Nine Schur marginalizations.
- Explicit factor chronology, provenance and ownership.

This does not establish physical acquisition-time
synchronization, calibrated extrinsics, real camera
visual odometry or statistical sensor independence.

## R105 — Same-graph nonlinear prior transfer

33 tests passed.

The experiment transferred nine recentered 30D
square-root Schur priors into the existing S6
synthetic nonlinear optimizer across three cases.

The recentering preserved local residuals,
information and transformed gradients.

The instrumented solver agreed with the
unchanged original within tested tolerances.

Two development errors were corrected before
the final successful run:

1. Pose lineage now excludes factors already
   consumed by an earlier marginalized window.
2. Invalid R104 graph admission exceptions are
   translated into R105 TransferError without
   bypassing R104 validation.

Both fixes are included in the archived engine.

## Scientific boundaries

The R95 Gaussian backend was not merged into S6.

The verified operation is a coordinate recentering
of priors produced by the SAME S6 synthetic graph.
It is not a general cross-backend prior import.

The results do not prove full nonlinear posterior
consistency, calibrated uncertainty, physical
localization accuracy or real-time performance.

No recorded camera, LiDAR or IMU factor was executed.
No original ground truth or ROSbags are archived.
No health training, ATE/RPE or confirmation_test
access was authorized.

All 11 scientific gates remain CLOSED.

## Verification

Run from the repository root:

python3 -B experiments/trust_robot_r104_r105_shared_graph_prior_checkpoint_v1/verify_checkpoint.py verify experiments/trust_robot_r104_r105_shared_graph_prior_checkpoint_v1
