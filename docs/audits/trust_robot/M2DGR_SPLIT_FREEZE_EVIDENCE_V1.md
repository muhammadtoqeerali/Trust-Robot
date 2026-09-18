# M2DGR Split Freeze Evidence V1

## Status

`frozen_prospective_split`

The M2DGR partition is frozen before estimator outcomes are used for split
selection.

## Frozen assignment

### Train — 22

- `Circle_01`
- `door_01`
- `gate_01`
- `hall_01`
- `hall_03`
- `hall_04`
- `hall_05`
- `lift_02`
- `lift_04`
- `room_02`
- `room_dark_01`
- `room_dark_02`
- `room_dark_03`
- `room_dark_04`
- `street_01`
- `street_010`
- `street_03`
- `street_04`
- `street_05`
- `street_07`
- `street_09`
- `walk_01`

### Validation/calibration — 7

- `door_02`
- `gate_03`
- `lift_03`
- `room_03`
- `room_dark_06`
- `street_02`
- `street_08`

### Confirmation test — 7

- `Circle_02`
- `gate_02`
- `hall_02`
- `lift_01`
- `room_01`
- `room_dark_05`
- `street_06`

## Design basis

The accepted V2 candidate uses only:

- reference family;
- author scenario metadata;
- author collection date;
- current estimator-input stream presence.

It does not use estimator outputs, ATE, RPE, timing-correlation outcomes,
calibration scores, reference pose values, author-reporting membership, or
future confirmation outcomes.

The rejected V1 candidate was rejected before estimator outcomes because it
accidentally removed complete scenario and collection-date categories from
training.

V2 preserves every observed scenario and every observed collection date in
training.

## Prospective confirmation semantics

The confirmation split is not described as pristine from all prior dataset
inspection.

All 36 trajectories were previously involved in dataset-level structural,
integrity, timing, and LiDAR/IMU characterization, and a 28-trajectory cohort
was used for earlier sensor-content calibration evidence.

However, confirmation membership was frozen before estimator-score selection.

From this freeze onward, confirmation trajectories may not select:

- estimator/model choices;
- thresholds;
- temporal-association parameters;
- alignment policy;
- evaluation protocol choices.

## Author benchmark subset

The seven author-selected reporting sequences remain an orthogonal reporting
tag and do not control TRUST-ROBOT split membership.

## Successor manifest

`manifests/m2dgr_trajectory_manifest_v1_split_freeze_v1.json`

Content SHA256:

`3a845fb4545607cad09b8be61d445b6b8a238bd3f346fd6b56c8c630d45141a6`

File SHA256:

`017a388ef1ce4ad30812669632a022ca37c084871bc949693fd9c0541014238f`

The successor changes exactly 14 trajectory `split` fields plus the manifest
content digest.

It does not change streams, synchronization, calibration, reference semantics,
reference coverage, or any readiness claim.

## Evaluation readiness

Still false.

No association tolerance, interpolation method, evaluation interval, alignment
mode, or estimator-scoring authorization is introduced by this split freeze.

Evidence content SHA256:

`bc5699504efda7203165adb9b1ceaa62f2639288011cdb875df0a870ee068a2e`
