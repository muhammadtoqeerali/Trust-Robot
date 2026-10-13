# TRUST-ROBOT analytic preintegrated LiDAR-IMU fusion V1

**Status: development-only fusion milestone validated.**

## New implementation

The existing rolling 15D state-estimation architecture
now has a separate preintegrated-factor implementation.

It uses the unchanged frozen LiDAR registration frontend
and the previously validated IMU preintegration module.

Estimator nodes correspond to original synthetic frames
0, 2, 4, 6 and 8.

Four disjoint inertial intervals use exactly eight IMU
samples without overlapping-measurement double counting.

Each inertial residual has 15 components: position,
velocity, rotation, gyroscope bias change and
accelerometer bias change.

A regularized Cholesky factor of the complete propagated
15x15 covariance whitens the coupled inertial residual.

The covariance floor is a declared numerical stabilizer
and not an empirically fitted physical sensor covariance.

## Analytic development-fixture results

| Condition | Position RMSE (m) | Rotation RMSE (deg) | Velocity RMSE (m/s) | LiDAR factors |
|---|---:|---:|---:|---:|
| clean | 0.00000000 | 0.00000000 | 0.00000000 | 7 |
| accel_bias | 0.02076773 | 0.00052657 | 0.07928620 | 7 |
| lidar_dropout | 0.00000000 | 0.00000000 | 0.00000000 | 3 |

These results compare against the manufactured
analytic trajectory strictly after estimation.

No improvement is presumed under synthetic bias.
Solver convergence does not imply estimation accuracy.

## Current estimator limitations

The oldest state in each rolling window is held fixed.
This is not Schur-complement marginalization.

The initial velocity and zero IMU biases are synthetic
development anchors, not independently measured inputs.

The preintegration linearization uses zero initial
bias and first-order bias correction within the solver.
Large-bias relinearization has not been validated.

The timing, sensor frames, LiDAR visibility model,
noise statistics and analytic reference are manufactured.

A full-rank local numerical Jacobian is not proof
of physical 6-DoF or IMU-bias observability.

The reference is never passed to the estimator.

No M2DGR benchmark, KIOS physical sensor, health
probability, factor-information conditioning or
safety supervisor has been evaluated.

Frozen Phase-7 and Phase-8 authorization gates
remain unchanged and closed.

## Provenance

Parent commit: `dcbd92e789e336e535057749cf39663195cbf973`

Module SHA-256: `396fc5171f3db972a2cebcd020f189e8a9c91979ada820a69ab8cd1b954efd79`

Test SHA-256: `07c5b089beb5be643c4b2f6c51d4d442f3630f937b97930dff7be218b4f5aab6`

Local run manifest SHA-256: `498322a3aed17d4c851944732ef051c499cdded9796eb1a4f890d3d34c72f0ad`

Generated state trajectories remain outside Git.

## Reproduction

    PYTHONPATH=src python -B src/trust_robot/analytic_preintegrated_fusion.py NEW_OUTPUT_DIR

    PYTHONPATH=src python -B tests/trust_robot/test_analytic_preintegrated_fusion.py -v

## Next priority

Implement a principled fixed-lag information prior
through Schur-complement marginalization, including
gauge treatment, covariance checks and regression tests.

Then qualify recorded sensor timestamps, reference
independence and estimator interfaces on external data
before attempting the final trust-layer experiments.
