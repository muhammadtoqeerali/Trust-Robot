# TRUST-ROBOT analytic SE(3) geometry benchmark V1

**Status: deterministic development-only fixture passed.**

## Implemented

A deterministic 20-pose, full-overlap, static-3D-landmark
fixture with 96 unique landmarks and nonzero translations
and rotations. It exercises the existing frozen Phase-2
scan frontend, frozen Phase-4 LiDAR feature extractor and
unchanged deterministic SE(3) pose backbone.

## Paired development-fixture results

| Condition | Fixture translation RMSE (m) | Fixture rotation RMSE (deg) |
|---|---:|---:|
| clean | 0.00000000 | 0.00000000 |
| sparse | 0.06336548 | 4.37367424 |
| noise | 0.00483786 | 0.09295135 |
| offset | 0.09124144 | 0.00000000 |

The conditions are clean; retaining every third point
in the perturbation window; additive 0.035 m Gaussian XYZ
noise; and a synthetic XYZ coordinate offset of
(0.12, -0.05, 0.04) m. Perturbations affect only
sample indices 5 through 13.

All four lanes share the same underlying analytic
trajectory and static landmarks. No synthetic condition
is assigned a three-class health label or attack attribution.

## Scientific interpretation

The reference poses are **manufactured by the same analytic
fixture generator**. The estimator never receives these
poses; they are used only in a later evaluation function.

This demonstrates an algorithmic closure and perturbation
regression, **not an independent measured reference**.
The fixture assumes perfect static-landmark visibility,
perfectly ordered synthetic observations, and idealized
geometry except for explicitly declared perturbations.

Its fixture translation/rotation RMSE values are not
official dataset ATE/RPE and must not be interpreted as
held-out localization accuracy or physical robustness.

This does not demonstrate accurate V15 point-cloud motion
physics, sensor synchronization, calibrated extrinsics,
IMU fusion, fixed-lag optimization, learned health
probabilities, factor conditioning, or safety supervision.

Frozen TRAIN/validation/confirmation dataset partitions
were not opened or modified. No M2DGR reference stream
or physical KIOS sensor was used.

## Provenance

Parent commit: `143dcfcfe9b8a7a9ef7a51a67468ab0ebd91d961`

Implementation SHA-256: `d1d6fd3438b04606016eeec64113aefc8c94ccf6abfe8322c8ce572612d07bff`

Test SHA-256: `fe9c342c74d24cbcfa50caeac4c5e34686796aee2f923a06804c4f252632040c`

Local benchmark manifest SHA-256:
`c98414bdb7ab16a35609a8477af5bdc340cf0248b720106d47b9bd28a15a5a36`

The 80 derived pose records remain in the dedicated
local experiment workspace; only compact evidence and
reproducible code are published to Git.

## Reproduction

Use the project-local environment with NumPy 1.26.4
and SciPy 1.13.1:

    PYTHONPATH=src python -B src/trust_robot/analytic_se3_geometry_benchmark.py NEW_OUTPUT_DIR

    PYTHONPATH=src python -B tests/trust_robot/test_analytic_se3_geometry_benchmark.py -v

## Next research dependency

Develop a separately tested fixed-lag optimizer and an
observable reference-backed measurement benchmark before
testing complete TRUST-ROBOT factor fusion.

Empirical three-state modality-health model training
remains blocked by the frozen supervision requirements.
