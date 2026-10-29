# R135-A19 — Twelve-node combined synthetic sensor faults

Status: UNTRUSTED_SYNTHETIC_LONG_HORIZON_DIAGNOSTIC_ONLY.

## Motivation

R135-A18 showed numerical acceptance of all 256
five-node manufactured IMU/LiDAR fault combinations.

The next question is whether a longer trajectory
and sustained missing LiDAR measurements expose
different estimator and numerical-support behavior.

## Frozen experiment

Twelve estimator nodes at manufactured frames
0,2,4,...,22.

Eleven preintegrated inertial factors, comprising
22 manufactured IMU readings.

Three IMU conditions:
- clean;
- accelerometer bias at sample indices 6 through 14;
- gyroscope bias at sample indices 8 through 17.

Five LiDAR availability schedules:
- none;
- mid_four: 8,10,12,14;
- mid_six: 8,10,12,14,16,18;
- late_five: 14,16,18,20,22;
- complete: all twelve estimator frames.

Total: 15 manufactured configurations.

## Important scientific boundaries

The manufactured trajectory and scene geometry
are fixed. The fault schedules modify only the
declared sensor fields.

All IMU factor information scales, LiDAR residual
weights and Schur marginalization rules remain unchanged.

The generated trajectory reference is discarded.
No independent ground truth is used for scoring.

The final-position deltas are differences between
manufactured estimator outputs. They are not ATE,
RPE, localization accuracy, drift rate or recovery
metrics.

Optimizer convergence and numerical Jacobian rank
do not establish physical observability.

No sensor-health labels, probabilities, learned
weights or physical uncertainty calibration are
introduced.

## Audited outcomes

Every accepted solve reports:
- eleven accepted optimization windows;
- ten Schur eliminations;
- exact inertial and LiDAR factor ownership;
- numerical support status for every window;
- active LiDAR availability;
- summed numerical optimizer cost;
- synthetic final-state digest;
- baseline-relative synthetic position differences.

Expected numeric solver rejections are recorded.
Unexpected failures stop the implementation.

The strict current-LiDAR availability policy is
tested separately and must reject full LiDAR loss.

## Protected data

No recorded M2DGR or Hilti sensor data is accessed.
No recorded ground truth or confirmation-test
sequence is accessed.

Frozen split:
22 TRAIN / 7 VALIDATION_CALIBRATION /
7 CONFIRMATION_TEST.

All 11 M2DGR scientific admission gates remain CLOSED.

## Next research direction

Use the 12-node support and estimator diagnostics
to identify harder synthetic failure mechanisms,
longer outages and conditions that genuinely
differentiate solver success from sensor support.

Physical localization and health-controlled
sensor fusion remain future scientific work.
