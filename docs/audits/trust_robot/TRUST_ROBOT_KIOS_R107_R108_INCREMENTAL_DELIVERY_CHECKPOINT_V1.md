# TRUST-ROBOT R107-R108 incremental delivery checkpoint

Date: 2026-10-22.

Parent Git commit:
ab108fb5913373de44b9ba9b08c1254607c59521

## R107 — Synthetic sequential nonlinear integration

38 regression tests passed.

A separate incremental estimator admits manufactured
factor bundles in strict increasing node order.

It reuses the S6 nonlinear residuals, least-squares
optimization and Schur marginalization primitives.

The original S6 source remains unchanged.

Across three manufactured scenarios:

- 12 ordinary nonlinear estimator windows.
- 12 recentered nonlinear estimator windows.
- 9 Schur operations in each mode.
- 9 same-graph prior recentering transfers.

Factor ownership and exclusion of future factors
were tested, with numerical comparisons to S6.

## R108 — Bounded delivery and fault injection

42 regression tests passed.

The in-process buffer tests two event arrival
schedules and two estimator modes for each of
three manufactured scenarios.

Total across the 12 runs:

- 48 nonlinear windows.
- 36 Schur marginalizations.
- 18 same-graph prior recentering transfers.

Duplicate, missing, altered, future, cross-graph
and unauthorized delivery attempts are rejected.

Accepted packet processing preserves chronological
node order and factor ownership.

## Scientific interpretation

This is an offline-manufactured synthetic factor
graph replayed through software interfaces.

It does not measure physical arrival-time jitter,
actual robot sensor capture, ROS/network delivery,
execution deadlines or authenticated transport.

Rejection before queue mutation is tested.
Transactional rollback after internal numerical
solver failure has NOT been proven.

No real camera, LiDAR or IMU factors are authorized.
No physical synchronization or extrinsic calibration
has been established.

R95 Gaussian prior history remains incompatible
with direct S6 nonlinear prior import.

The original 22/7/7 M2DGR partition stays frozen.
The confirmation_test subset remains sealed.

No physical localization ATE/RPE results,
health-model training or original raw GT/ROSBags
are included in this checkpoint.

All 11 scientific gates remain CLOSED.

## Next development

Evaluate fail-stop behavior of internal solver
failures, duplicate queue deliveries and bounded
buffer recovery using manufactured injection.

Do not claim transactional recovery without
explicit rollback-state verification.
