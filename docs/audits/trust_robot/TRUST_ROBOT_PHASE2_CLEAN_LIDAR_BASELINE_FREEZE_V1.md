# TRUST-ROBOT Phase-2 Clean LiDAR Baseline Freeze V1

## Decision

Phase 2 is locally complete.

The frozen baseline identity is:

`trust_robot_phase2_clean_lidar_baseline_v1`

Phase-2 objective:

**Fixed clean localization/state-estimation backbone**

Phase-2 exit evidence:

**Reproducible clean 6-DoF baseline**

Exit evidence status:

**satisfied**

## Real-data execution evidence

The frozen estimator completed all 22 frozen M2DGR TRAIN trajectories.

- total LiDAR scans: 91,014
- total consecutive-scan increments: 90,992
- skipped scans: 0
- skipped trajectories: 0
- fail-closed events: 0
- reference data used: false
- confirmation-test data used: false
- ATE computed: false
- RPE computed: false
- trajectory scoring performed: false

Every Velodyne scan reported by bag metadata was consumed.

Every consecutive scan pair produced exactly one 6-DoF increment.

All trajectory JSONL artifacts are hash-bound in the freeze manifest.

## Frozen estimator definition

The baseline is LiDAR-only consecutive-scan odometry in the `velodyne` frame.

Registration uses:

- current scan as source;
- previous scan as target;
- identity initialization;
- exact nearest-neighbor assignment;
- SVD/Kabsch rigid fitting;
- exact assignment fixed-point convergence;
- no voxel downsampling;
- no correspondence-distance threshold;
- no outlier rejection;
- no keyframe threshold;
- no numeric convergence tolerance;
- no maximum-iteration parameter.

These choices are now part of the frozen Phase-2 estimator identity.

## Timing and deskew boundary

The PointCloud2 header timestamp is used for ordering and state labels.

Its physical meaning as scan start, center, end, or another temporal reference
remains unverified.

The per-point `time` field is not used.

Deskew is not performed.

These facts do **not** prevent the estimator itself from being a fixed,
reproducible baseline because the current single-LiDAR relative-pose algorithm
does not require an external physical timestamp interpretation to define its
pose chain.

They remain material limitations for later:

- reference-trajectory association;
- timing-sensitive ground-truth comparison;
- multi-sensor fusion;
- synchronization claims;
- physical interpretation of estimator state timestamps.

No later phase may silently reinterpret the timestamp or introduce deskew into
this frozen baseline.

Any deskewed estimator is a different estimator variant and requires its own
explicit protocol identity.

## Evaluation boundary

Freezing Phase 2 does not authorize M2DGR evaluation.

The existing evaluation protocol remains blocked.

This freeze does not resolve:

- synchronization verification;
- physical reference origin semantics;
- reference association;
- association tolerance;
- interpolation;
- fixed time offset;
- evaluation interval;
- alignment;
- metric authorization.

No ATE/RPE or final estimator scoring is authorized by this closure.

## Artifact binding

Freeze manifest:

`manifests/trust_robot_phase2_clean_lidar_baseline_freeze_v1.json`

Manifest file SHA256:

`4f1daa871be72714bd257e22b43e551259d989c391230edfaac3c95f579d9da0`

Manifest content SHA256:

`daf189bff7f6758e11e0234f2d7079777de25ec0784561af92704151cee4cc4b`

The manifest binds the exact estimator code, frontend configuration, frozen
TRAIN split, full-run artifacts, all 22 trajectory JSONL hashes, and explicit
scientific limitations.

## Promotion identity

The Git commit containing this audit and the Phase-2 freeze manifest is the
authoritative Phase-2 repository promotion checkpoint. The commit hash is not
embedded here because doing so would make this file self-referential.
