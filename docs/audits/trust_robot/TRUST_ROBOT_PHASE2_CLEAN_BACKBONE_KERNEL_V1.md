# TRUST-ROBOT Phase-2 Clean Backbone Kernel V1

## Objective

Phase 2 requires a fixed clean localization/state-estimation backbone whose
eventual exit evidence is a reproducible clean 6-DoF baseline.

The current `src/trust_robot` implementation previously contained data,
evidence, synchronization, reference-quality, split, and fail-closed evaluation
infrastructure but no current clean 6-DoF state-estimation kernel.

The inherited `src/imu_reliability` package remains historical/reference
research code and is not silently reclassified as the current localization
backbone.

## Implemented kernel

`src/trust_robot/clean_backbone.py` implements a deterministic SE(3) pose-chain
backend.

The mathematical convention is explicit:

`prev_body_T_current_body`

For each strictly increasing timestamp, a fixed relative-pose source supplies
one relative rigid transform.

The state update is:

`world_T_current_body = world_T_previous_body * previous_body_T_current_body`

The implementation provides:

- explicit world/body frame identifiers;
- one fixed relative-pose source identifier per backbone configuration;
- deterministic quaternion canonicalization;
- rigid-transform composition;
- rigid-transform inversion;
- deterministic sequential state propagation;
- deterministic run serialization and SHA256 content identity.

## Deliberately not implemented in this checkpoint

This kernel does not yet extract relative pose from raw sensor streams.

It therefore does not yet constitute the final Phase-2 exit artifact.

Still absent:

- raw camera frontend;
- raw LiDAR frontend;
- raw IMU propagation/preintegration frontend;
- fixed clean frontend selection for the current primary dataset;
- real clean-dataset estimator execution;
- reproducible real-data 6-DoF trajectory artifact.

It also deliberately contains no:

- health/reliability weighting;
- fault/degradation logic;
- corruption injection;
- learned model;
- validation-selected threshold;
- reference trajectory use;
- confirmation-test access;
- trajectory alignment;
- ATE;
- RPE;
- estimator scoring.

## Relation to M2DGR evidence gate

This kernel does not modify the frozen M2DGR evaluation protocol.

It does not require a reference trajectory and does not resolve any existing
M2DGR physical timing, calibration, origin, association, or alignment blocker.

Running a clean estimator and scientifically scoring that estimator are separate
operations.

## Current Phase-2 status

Phase-2 implementation has started.

The deterministic 6-DoF mathematical backend exists.

Phase-2 exit evidence remains unsatisfied until a fixed clean frontend is
connected and a reproducible clean real-data baseline run is produced without
violating the frozen data/evaluation rules.
