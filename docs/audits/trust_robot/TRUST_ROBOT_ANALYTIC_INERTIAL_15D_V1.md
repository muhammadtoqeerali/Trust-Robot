# TRUST-ROBOT analytic 15D inertial state milestone

**Status: analytic development prototype validated.**

## Implementation

The state is position xyz, orientation SO(3), velocity xyz,
gyro bias xyz and accelerometer bias xyz: 15 dimensions.

A rolling three-pose nonlinear least-squares problem combines
frozen LiDAR registration factors with first-order discrete
inertial motion factors and bias-continuity residuals.

The initial velocity and initial zero bias are declared
development calibration anchors; they are not real
independent sensor measurements.

The oldest state is held fixed when a window advances.
There is no probabilistic marginalization or covariance
propagation. Full local numerical Jacobian rank does not
prove physical sensor observability.

## Three controlled synthetic conditions

| Condition | Position RMSE (m) | Rotation RMSE (deg) | Velocity RMSE (m/s) |
|---|---:|---:|---:|
| clean | 0.00000000 | 0.00000000 | 0.00000000 |
| accel_bias | 0.00061977 | 0.00547832 | 0.06865129 |
| lidar_dropout | 0.00000000 | 0.00000000 | 0.00000000 |

The conditions are unaltered analytic sensor observations,
a finite accelerometer measurement bias over three intervals,
and one unavailable synthetic LiDAR frame.

The reference used for scoring is analytically manufactured.
It is not an independently recorded external ground truth.

The estimator consumes synthetic LiDAR scans, synthetic IMU
readings and declared initial calibration assumptions.
Fixture truth is not passed to the estimator API.

## Scientific boundaries

These discrete inertial residuals are not a substitute for
bias-Jacobian and covariance-propagating IMU preintegration.

The fixed residual scales have not been identified
empirically or selected under the final protocol.

The bias random-walk and initial-bias anchors influence
algebraic identifiability. Physical bias observability
and bias-estimation accuracy are not established.

There is no physical synchronization, independent extrinsic
calibration, fixed-lag Schur marginalization, visual
reprojection factor, calibrated health probability,
factor conditioning or safety supervision.

No clean synthetic condition is promoted to an empirical
healthy health label. Interventions are known simulation
operations, not accepted three-class health supervision.

Frozen Phase-7 and Phase-8 runtime gates remain closed.
No held-out M2DGR or physical KIOS data were opened.

## Provenance

Parent commit: `faa8d0917a7bcb46668b3f69a04007865b5a8d70`

Module SHA-256: `e077d3d294f22130450a34b9ac42932d5bfcf1af552ed4653b864211a5e39c74`

Test SHA-256: `f7dd38aa1e71e9ff3d08e33fc926bf9460de665490c8156a4a72d4449ae57f5d`

Execution manifest SHA-256: `1312c2aff7bf97bdd2c19e287670a92440527f09b107121a976e4c5b13a008ed`

Generated numerical records remain local.

## Reproduction

    PYTHONPATH=src python -B src/trust_robot/analytic_inertial_15d.py NEW_OUTPUT_DIR

    PYTHONPATH=src python -B tests/trust_robot/test_analytic_inertial_15d.py -v

## Next dependencies

Develop covariance/Jacobian-aware IMU preintegration,
principled fixed-lag marginalization and verified
sensor timing/extrinsic interfaces.

Admissible health-supervision data remain necessary
before health-model training and trust-layer evaluation.
