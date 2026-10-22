# TRUST-ROBOT R107-R108 incremental delivery checkpoint

Date: 2026-10-22.

Parent Git commit:
ab108fb5913373de44b9ba9b08c1254607c59521

## R107 — Sequential synthetic nonlinear estimator

38 regression tests passed.

R107 implements a separate bounded synthetic
sequential-admission estimator using the existing
R104 manufactured factor graph and S6 numerical
optimization and marginalization primitives.

Verified:
- Three manufactured scenarios.
- Five nodes and four preintegrated IMU edges per graph.
- Twelve ordinary nonlinear windows.
- Twelve recentered nonlinear windows.
- Nine Schur events per execution mode.
- Nine same-graph prior recentering transfers.
- Sequential factor admission and ownership.
- Numerical agreement with unchanged S6.

## R108 — Bounded event-order and fault testing

42 regression tests passed.

R108 implements a deterministic in-process buffer
around the R107 incremental estimator.

Verified:
- Three manufactured scenarios.
- Ordered and bounded-reordered arrival schedules.
- Ordinary and recentered estimator modes.
- Twelve solver executions.
- Forty-eight nonlinear windows.
- Thirty-six Schur marginalizations.
- Eighteen prior recentering transfers.
- Rejection of duplicate, incomplete, future,
  altered, cross-graph and unauthorized deliveries.
- Numerical agreement with unchanged S6.

## Limits of evidence

All measurements originate from the analytic
manufactured graph.

Sequential admission and reordering are software
replay experiments, not measured physical streaming.

Neither phase establishes hardware arrival
latency, real-time deadlines, transport security,
authenticated packet provenance, online sensor
calibration, or transactional rollback after
internal solver failure.

R95 Gaussian priors remain separate from S6.
No physical sensor factor has been executed.

The sealed confirmation_test partition is not used.
Original ROSbags and independent ground-truth
data remain outside this checkpoint.

No calibrated health training or ATE/RPE.

All 11 scientific gates remain CLOSED.

## Standalone verification

Run from repository root:

python3 -B experiments/trust_robot_r107_r108_incremental_delivery_checkpoint_v1/verify_checkpoint.py verify experiments/trust_robot_r107_r108_incremental_delivery_checkpoint_v1
