# TRUST-ROBOT analytic rolling nonlinear SE(3) pose window V1

**Status: development-only nonlinear pose-window executed.**

## New implementation

A five-pose rolling nonlinear least-squares window.
The newest state is initialized from the frozen LiDAR
registration frontend. Adjacent and lag-two scan
registration factors are evaluated with the same fixed
residual scaling in all experimental conditions.

The oldest pose in the current window is fixed.
When it leaves the window, its optimized estimate
becomes a historical boundary. No probabilistic
marginalization or Schur-complement prior is claimed.

## Analytic fixture metrics

| Condition | Chain translation RMSE (m) | Window translation RMSE (m) | Successful windows |
|---|---:|---:|---:|
| clean | 0.00000000 | 0.00000000 | 19/19 |
| noise | 0.00483786 | 0.00450287 | 19/19 |
| offset | 0.09124144 | 0.09124144 | 19/19 |
| sparse | 0.06336548 | 0.06336548 | 19/19 |

Metrics compare against manufactured analytic fixture
poses used only for scoring, never as optimizer input.

The experiment does not assert that nonlinear
refinement must outperform the clean chain or
every corrupted condition. Both results are reported.

## Mathematical validity boundaries

A full local Jacobian rank is an algebraic property of
the selected pose-factor system. It does not establish
physical LiDAR observability, accurate extrinsics
or independent sensor-frame calibration.

Translation and rotation residual scales are fixed
development constants, not measured sensor noise
covariances, learned reliability scores or health weights.

## Remaining research requirements

The final TRUST-ROBOT backend requires a fully
specified fixed-lag state with velocity and IMU
biases where applicable, properly modeled inertial
and exteroceptive factors, principled marginalization,
and calibrated timing and extrinsic conventions.

Health-aware factor scaling remains blocked by
the frozen Phase-8 input/authorization contract.
Three-state health-model training remains blocked by
missing admissible empirical TRAIN supervision.

No physical sensor, external reference dataset,
held-out benchmark or robot controller was used.

## Reproducibility

Parent commit: `a8cd154d7fbcb910423b9f011ed845b4f14f01e5`

Module SHA-256: `71e1034b1376ca399317018891b6d138fda93cd5162e55aeb953a5a118e94eca`

Test SHA-256: `608a057b86d4af94af20ceea505c6bdf21e9ed4f1e7aacb098cfabe742f28695`

Local run manifest SHA-256: `1b4fdb37ee89130430e1138c9c1f6bb8c46e2379eda93c2cea49531ae090e05d`

Run with the NumPy 1.26.4 / SciPy 1.13.1
project-local environment:

    PYTHONPATH=src python -B src/trust_robot/analytic_fixed_lag_pose.py NEW_OUTPUT_DIR

    PYTHONPATH=src python -B tests/trust_robot/test_analytic_fixed_lag_pose.py -v

Local generated pose files remain outside Git.
