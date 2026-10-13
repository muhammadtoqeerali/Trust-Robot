# TRUST-ROBOT three-modality factor bridge development V1

**Status:** manufactured factor-interface and nonlinear-estimator
integration validated. Physical three-modality localization is NOT
verified or authorized by this milestone.

## Implementation

An explicit typed synthetic pose-factor packet now distinguishes:

- camera-style manufactured relative-motion observations;
- existing analytic LiDAR registration observations;
- existing analytic preintegrated IMU factors.

The project uses its published 15D Schur marginalized estimator
without modifying that estimator or its original public API.

A dedicated compatibility adapter places manufactured camera
relative-motion factors into the existing relative-pose solver
slot. The slot is historically named LiDAR; its residual scaling
is unchanged. To avoid duplicate use of an edge, the adapter
replaces its LiDAR observation when assigning that edge to a
camera-style observation.

This does **not** implement independent camera/LiDAR residual
weights or simultaneous independent same-edge camera/LiDAR
factors. It is a limited factor-interface integration, not the
complete future multimodal estimator.

## Manufactured experiment results

| Condition | Seed | Camera enabled | Camera factors | LiDAR factors | IMU factors | Solved windows |
|---|---:|---|---:|---:|---:|---:|
| clean | 13 | False | 0 | 7 | 4 | 4 |
| clean | 13 | True | 2 | 5 | 4 | 4 |
| clean | 31 | False | 0 | 7 | 4 | 4 |
| clean | 31 | True | 2 | 5 | 4 | 4 |
| clean | 71 | False | 0 | 7 | 4 | 4 |
| clean | 71 | True | 2 | 5 | 4 | 4 |
| lidar_dropout | 13 | False | 0 | 3 | 4 | 4 |
| lidar_dropout | 13 | True | 2 | 2 | 4 | 4 |
| lidar_dropout | 31 | False | 0 | 3 | 4 | 4 |
| lidar_dropout | 31 | True | 2 | 2 | 4 | 4 |
| lidar_dropout | 71 | False | 0 | 3 | 4 | 4 |
| lidar_dropout | 71 | True | 2 | 2 | 4 | 4 |

All 12 cases completed.
The previously implemented estimator regressions and
M2DGR source admission tests remain unchanged.

## Scientific limitations

The manufactured camera observations are generated from
synthetic trajectory states with seeded noise.

No camera images, visual tracking, optical flow, reprojection
factor or actual visual odometry frontend was used.

The estimator receives synthetic relative-pose measurements,
not independent reference trajectories. The simulator uses
manufactured truth only to produce these measurements.

The LiDAR factors use the existing analytic registration
frontend. The IMU factors use existing synthetic preintegration.

These experiments do not establish:
- camera motion measurement accuracy;
- real RGB/IMU/LiDAR capture synchronization;
- independent physical sensor extrinsics;
- calibrated inter-modality covariance;
- real three-modality localization;
- held-out pose accuracy;
- health-aware reliability weighting;
- safe physical robot behavior.

The recorded M2DGR factor-execution gate remains closed.
Recorded metadata inspection does not authorize a factor.

Existing Phase-7 and Phase-8 scientific authorization contracts
remain unchanged.

## Reproduction

    PYTHONPATH=src python -B tests/trust_robot/test_multimodal_factor_interface.py -v
    PYTHONPATH=src python -B tests/trust_robot/test_analytic_three_modality_bridge.py -v

Generated results and checksums remain in the dedicated
project-local KIOS experiment directory.

## Next implementation

Replace the manufactured camera-style relative-pose generator
with a separately validated visual motion frontend, while
preserving the original image/camera frame and capture-time
provenance.

Extend the backend's typed residual structure to represent
camera and LiDAR factors independently, with source-specific
measurement identities and scientifically justified covariance.

Physical execution and scoring must remain blocked until
independent timing, extrinsic and reference-source evidence
meet the project's existing authorization requirements.
