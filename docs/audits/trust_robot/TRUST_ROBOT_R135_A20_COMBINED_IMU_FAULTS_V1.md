# R135-A20 — Combined manufactured IMU fault interactions

Status: UNTRUSTED_SYNTHETIC_COMBINED_IMU_DIAGNOSTIC_ONLY.

## Purpose

Extend the published 12-node synthetic estimator
study to simultaneous accelerometer and gyroscope
measurement corruption.

## Frozen conditions

Four IMU modes:
- clean;
- accelerometer bias;
- gyroscope bias;
- combined accelerometer and gyroscope bias.

Five LiDAR schedules:
- none;
- mid_four;
- mid_six;
- late_five;
- complete.

Total: 20 synthetic configurations.

The combined condition copies only the independently
manufactured accelerometer and gyroscope fields
from the two frozen single-fault fixtures.

Accelerometer corruption: samples 6 through 14.
Gyroscope corruption: samples 8 through 17.

The analytic motion, LiDAR scans, timestamps,
sensor origin and fixed estimator scales
remain unchanged.

## Interaction diagnostic

For a common outage schedule, let:

P0 = clean estimated final position
Pa = accelerometer-bias estimated final position
Pg = gyroscope-bias estimated final position
Pag = combined-bias estimated final position

The manufactured interaction diagnostic is:

norm(Pag - Pa - Pg + P0).

This quantifies nonadditivity in estimator output
under these fixed synthetic conditions.

It is not a localization accuracy metric,
calibrated fault-risk score, causal health
probability or independently measured error.

When any required solver output is rejected,
the interaction remains unavailable rather
than being invented.

## Numerical accounting

Accepted solves require:
- 12 synthetic state nodes;
- 11 preintegrated inertial factors;
- 22 unique synthetic IMU samples;
- 11 accepted optimizer windows;
- 10 Schur eliminations;
- no lost or duplicated graph factors;
- numeric support and current LiDAR availability
  reported independently from solver acceptance.

## Protected scientific restrictions

The manufactured trajectory reference is never
passed to the estimator or used for scoring.

No M2DGR or Hilti recorded input is accessed.

No health probability, label or learned model
is introduced.

No factor weight, measurement covariance or
physical sensor calibration is changed.

No real sensor factors are authorized.

The frozen M2DGR partition remains:
22 TRAIN / 7 VALIDATION_CALIBRATION /
7 CONFIRMATION_TEST.

All 11 admission gates remain CLOSED.

## Subsequent research

Evaluate which manufactured fault combinations
create large estimator-output sensitivity and
which numerical support diagnostics expose
missing sensor constraints.

Physical accuracy, trust-model validation and
sensor-recovery claims require independent
evidence in later admitted studies.
