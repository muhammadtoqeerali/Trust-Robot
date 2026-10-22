# R107 — Synthetic sequential-admission estimator

## Objective

Introduce a bounded incremental software interface
using the same R104 manufactured camera, LiDAR and IMU
factor graph and the existing S6 nonlinear primitives.

R107 does not alter the original S6 source.

## Sequential admission

The new estimator begins with one manufactured
15D gauge-anchored node.

Each ingest operation admits:

- Exactly the next synthetic estimator node.
- The two existing IMU samples for that edge.
- The existing preintegrated factor for that edge.
- All camera/LiDAR factors whose endpoint becomes due.

No future pose factor is included in the current
nonlinear optimization problem.

A maximum of three live states is retained.

## Prior lifecycle

The oldest state is eliminated through the
existing S6 Schur marginalizer.

A second execution mode applies R105's exact
same-graph local 30D prior recentering.

The new priors are then reused by the next
nonlinear optimization window.

## Validation

Run both modes on three manufactured scenarios.

Compare their state estimates and factor ledgers
against the unchanged S6 estimator.

Reject out-of-order node releases, missing
measurements, duplicate factors, wrong source
objects, modified frame claims and real-source
authorization claims.

## Scientific exclusions

The factor graph is constructed offline from the
analytic simulator, then replayed sequentially.

This does not test actual physical online capture,
real-world arrival jitter, out-of-order buffering,
live ROS transport or execution-time deadlines.

No calibrated uncertainty or posterior consistency
is claimed.

No R95 Gaussian priors are imported.

No real camera, LiDAR or IMU factors are authorized.

No health training, ATE/RPE, original ground-truth
access or confirmation-test execution is authorized.

All 11 scientific gates remain CLOSED.
