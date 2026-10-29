# R135-A17 — Exhaustive synthetic LiDAR dropout and support

Status: UNTRUSTED_SYNTHETIC_NUMERICAL_SUPPORT_ONLY.

## Objective

Evaluate all 128 possible LiDAR pose-factor availability
patterns in the published five-node analytic 15D estimator.

The experiment tests numerical optimizer behavior and
explicit current-LiDAR support availability, rather
than assuming optimization success means localization safety.

## Frozen experiment

The graph has seven LiDAR relative-pose edges.

All combinations of 0 through 7 removed edges are
tested: 1 + 7 + 21 + 35 + 35 + 21 + 7 + 1 = 128.

Four manufactured preintegrated IMU factors and the
synthetic initial anchor remain unchanged.

No camera measurement is injected in this experiment.

## Numerical-support audit

The existing opt-in marginalized support interface
examines fitted whitened Jacobians, the inherited Schur
prior and active factors.

Each accepted estimator window reports:
- numerical support status;
- fitted Jacobian rank;
- numerical condition diagnostic;
- current LiDAR factor availability;
- active IMU/LiDAR factor counts;
- explicit physical-observability denials.

The existing strict current-LiDAR requirement is tested
to confirm that complete LiDAR absence is rejected.

A numerically accepted optimizer result does not prove
sensor availability, physical observability, uncertainty
calibration or real-world recovery.

## Scientific restrictions

No recorded M2DGR or Hilti measurement is read.
No recorded or confirmation-test ground truth is accessed.

No health model inference or labels are generated.
No factor weights, covariances or physical thresholds
are selected or altered.

The 22 TRAIN / 7 VALIDATION_CALIBRATION /
7 CONFIRMATION_TEST split remains unchanged.

All 11 M2DGR scientific admission gates remain CLOSED.

## Future development

Use the availability and numerical-support evidence to
select appropriately challenging manufactured outage
studies. Do not report optimizer cost as localization
accuracy or declare physical sensor recovery.
