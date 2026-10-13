# TRUST-ROBOT analytic IMU preintegration V1

**Status: development-only mathematical validation passed.**

## Implementation

Introduced bias-sensitive SO(3) IMU preintegration
with delta rotation, delta velocity and delta position.
The propagated 15x15 error covariance includes IMU
measurement noise and gyro/accelerometer bias random walks.

The 9x6 first-order bias Jacobian is independently
checked using central finite differences.
Short-interval residuals use a 9x9 motion covariance
marginal with an explicit numerical regularizer.
Bias random-walk residuals are handled separately.
Full correlated 15x15 factor whitening is not claimed.

## Controlled analytic results

| Condition | Mean whitened motion residual |
|---|---:|
| clean | 0.00000000 |
| accel_bias | 6.26212397 |
| gyro_bias | 4.48766074 |

The reported values are dimensionless whitened
residuals under declared development-noise parameters,
not physical localization accuracy or health probabilities.

## Numerical verification

Maximum bias-Jacobian finite-difference error: 4.875601034e-10.

First-order bias-correction discrepancy: 2.025088725e-05.

Covariance-noise scaling discrepancy: 0.

Two complete executions were compared byte-for-byte.

## Scientific boundaries

The input is an analytic development fixture, not
the original V15 measured sensor stream or M2DGR.

Input time steps and noise magnitudes are manufactured.
No physical timestamp synchronization, extrinsic
calibration or real sensor noise characterization
has been verified.

The reference trajectory is available only to a
post-integration diagnostic scoring function.

No health class, trust weight, modality suppression,
attack attribution or real robot safety action
is generated.

The new preintegration factors have not yet been
connected to the rolling nonlinear 15D optimizer.
Schur-complement marginalization is also incomplete.

The existing Phase-7/8 scientific authorization
gates are unchanged.

## Provenance

Parent commit: `1a66d42770d56b6262e438e0cbb8fe8e591922bb`

Module SHA-256: `5d1150e1351e205521f7511b7885542199d95a4b9ef34ad618f6f9291bb24b33`

Test SHA-256: `97db13a8c43bc817e7c83df8c0dced0a207c46e54bfa50f309f7f7f8205b709f`

Run manifest SHA-256: `d16b03fad5fd46b431657fe9ee708583cba05e34e77e47f7a70f6dc8d1c91398`

Generated numerical data remain local.

## Reproduction

    PYTHONPATH=src python -B src/trust_robot/analytic_imu_preintegration.py NEW_OUTPUT_DIR

    PYTHONPATH=src python -B tests/trust_robot/test_analytic_imu_preintegration.py -v

## Next milestone

Integrate preintegrated inertial factors into the
15D rolling optimizer; validate bias sensitivity,
covariance-whitened residuals and failure handling.
Then implement and test principled fixed-lag
marginalization with explicit gauge handling.
