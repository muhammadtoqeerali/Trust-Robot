# TRUST-ROBOT Phase-4 LiDAR Registration Diagnostics V1

## Phase boundary

Phase 4 objective:

**Per-modality diagnostics**

Phase 4 exit evidence:

**Validated diagnostic feature extraction**

The three-state healthy/degraded/unusable classifier belongs to Phase 5 and is
not implemented by this layer.

## Adoption decision

The Phase-4 frontier audit found useful historical reliability/integrity
machinery under `src/imu_reliability`, including integrity evidence, channel
freeze monitoring, reliability decisions and runtime trust states.

Those implementations are not imported into the native Phase-4 diagnostic
path.

They contain concepts belonging to later stages such as detector thresholds,
trust states and reliability decisions.

Historical values and thresholds therefore remain inventory evidence only.

## Frozen LiDAR source contract

The first native Phase-4 extractor consumes the already-frozen Phase-2 type:

`LidarRegistrationDiagnostics`

from:

`src/trust_robot/lidar_frontend.py`

It does not rerun or modify registration.

It extracts exactly five numeric observables in fixed order:

1. `source_point_count`
2. `target_point_count`
3. `fixed_point_iterations`
4. `final_correspondence_count`
5. `final_nearest_neighbor_rmse_m`

Units are respectively:

`count, count, count, count, m`

## Preserved categorical semantics

The diagnostic record additionally preserves:

- convergence rule;
- correspondence-rejection-used flag;
- voxel-downsampling-used flag.

For the frozen Phase-2 estimator these must remain:

- convergence rule:
  `exact_nearest_neighbor_assignment_unchanged`
- correspondence rejection:
  false
- voxel downsampling:
  false

A change to these estimator semantics fails this extractor contract rather
than being silently interpreted as the same diagnostic source.

## Interpretation boundary

Nearest-neighbor RMSE is an estimator-internal registration diagnostic.

It is not:

- reference error;
- ATE;
- RPE;
- localization accuracy;
- a health score;
- a fault threshold;
- a severity threshold.

Likewise, point counts, correspondence count and fixed-point iteration count
are descriptive observables only.

No threshold is selected in this layer.

No normalization or temporal-window aggregation is introduced.

No healthy/degraded/unusable state is emitted.

No modality suppression is authorized.

## Scientific boundary

This implementation uses synthetic unit construction only.

It does not:

- open M2DGR data;
- execute corruption;
- execute a new estimator run;
- access reference trajectories;
- access confirmation-test trajectories;
- associate or align trajectories;
- compute ATE/RPE;
- train a health model;
- select a diagnostic threshold;
- select a health threshold;
- perform estimator scoring;
- change evaluation readiness.

Phase-4 exit evidence remains unsatisfied after this first extractor because
real-data diagnostic extraction and broader validation have not yet been
performed.
