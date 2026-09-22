# TRUST-ROBOT Phase-3 Real LiDAR EVENT_GAP Smoke V1

## Purpose

This is the first controlled corruption applied to real M2DGR TRAIN sensor
data in the new TRUST-ROBOT Phase-3 architecture.

It is a mechanical clean-to-corrupt integration proof.

It is not a localization accuracy experiment.

## Prospective source slice

The source is frozen TRAIN trajectory:

`Circle_01`

Topic:

`/velodyne_points`

Only the first three Velodyne messages in bag order are used.

Their header timestamps and raw PointCloud2 data hashes were already observed
during the preceding clean-adapter compatibility work and are frozen in:

`configs/trust_robot/phase3_lidar_event_gap_real_smoke_v1.json`

No source event is selected from estimator output or reference error.

## Prospective corruption instance

The mechanism is:

`EVENT_GAP`

with:

- `start_index = 1`
- `length = 1`
- `scenario_context = unattributed`
- no seed
- no severity ID
- no attack threat model
- no mechanism parameters

A three-event clean stream has exactly one internal event.

Removing that internal event therefore requires no search over event location.

The one-event removal is the minimal non-zero discrete instance required to
mechanically exercise `EVENT_GAP`.

It is not adopted as a general corruption severity or benchmark level.

No severity grid is selected by this smoke.

## Expected structural result

Clean origin mapping:

`[0, 1, 2]`

Corrupted origin mapping:

`[0, 2]`

Clean event 1 is removed.

Clean events 0 and 2 must remain byte/content equivalent at the decoded XYZ
payload level.

## Required determinism

The real smoke requires:

- raw PointCloud2 source bytes remain unchanged;
- clean EventStream remains unchanged;
- repeated clean adaptation is exact;
- repeated application of the same corruption specification produces the same
  corrupted EventStream fingerprint;
- repeated corruption produces the same pair manifest;
- specification and injection identity remain deterministic.

## Scientific boundary

The smoke uses real TRAIN sensor data but does not:

- use reference trajectories;
- use confirmation-test data;
- execute the estimator;
- associate to ground truth;
- align trajectories;
- compute ATE;
- compute RPE;
- score localization;
- select corruption severity from performance;
- verify synchronization;
- assign a physical meaning to the PointCloud2 header timestamp;
- perform deskew.

Synthetic corruption truth means only that TRUST-ROBOT deliberately removed
the specified event.

It is not evidence that any naturally occurring sensor observation had the
same physical cause.

Phase-3 exit evidence remains unsatisfied after this smoke.
