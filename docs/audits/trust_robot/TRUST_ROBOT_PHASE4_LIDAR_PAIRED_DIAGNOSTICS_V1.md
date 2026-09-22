# TRUST-ROBOT Phase-4 LiDAR Paired Diagnostics V1

## Purpose

This layer validates that the same native Phase-4 LiDAR diagnostic extractor
can consume registration diagnostics from both sides of an already-frozen
Phase-3 clean/corrupt pair.

It does not rerun the estimator and it does not rerun corruption.

## Frozen source

The source is the persistent Phase-3 paired registration receipt from TRAIN
`Circle_01`.

The frozen corruption is `EVENT_GAP` with:

- specification ID `TRC_SPEC_d7fdcb5f67999476d8f0391d`;
- injection ID `TRC_INJ_2413029fc605422de2dd737f`.

## Registration topology

Clean registration inputs:

`[[0, 1], [1, 2]]`

Corrupted registration input:

`[[0, 2]]`

This provenance is preserved exactly.

## Diagnostic extraction

Every registration diagnostic record passes through the same native function:

`extract_lidar_registration_diagnostics`

The five numeric observables remain:

1. source point count;
2. target point count;
3. fixed-point iteration count;
4. final correspondence count;
5. final nearest-neighbor RMSE in metres.

No clean-versus-corrupt subtraction, ratio, delta, score or ranking is
computed.

The corrupted branch is not interpreted as better, worse, healthy, degraded,
unusable, faulty or reliable.

## Relationship to complete TRAIN validation

The same extractor has already been validated on all 90,992 frozen clean
TRAIN registration diagnostics across 22 trajectories.

That extraction has deterministic identity:

`42658bdb5739200f02dc1397f753b78ca60eb22f6bc5d913e42c6a208fc61020`

The paired proof adds controlled-corruption registration-path coverage without
reopening the estimator or raw dataset.

## Scientific boundary

This layer does not:

- open ROS bags;
- decode PointCloud2;
- rerun registration;
- rerun corruption;
- compute descriptive feature statistics;
- normalize features;
- aggregate temporal windows;
- select or apply a threshold;
- emit healthy/degraded/unusable labels;
- emit a fault decision;
- emit a reliability score;
- compare clean and corrupt localization accuracy;
- use reference trajectories;
- use confirmation-test trajectories;
- associate or align trajectories;
- compute ATE/RPE;
- score the estimator.

Phase-4 exit evidence remains formally unsatisfied until the dedicated
closure-scope review evaluates whether this evidence satisfies:

**Validated diagnostic feature extraction.**
