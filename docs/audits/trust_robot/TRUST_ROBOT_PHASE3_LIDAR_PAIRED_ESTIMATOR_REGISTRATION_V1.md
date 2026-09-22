# TRUST-ROBOT Phase-3 Paired LiDAR Estimator Registration V1

## Purpose

This layer proves that the deterministic Phase-3 clean/corrupt LiDAR pair can
be passed through the exact frozen Phase-2 registration kernel.

The frozen function is:

`register_current_scan_to_previous`

from:

`src/trust_robot/lidar_frontend.py`

No alternative registration algorithm is implemented.

## Source

Only the already-frozen first three Velodyne events from TRAIN `Circle_01`
are used.

The already-prospective `EVENT_GAP` specification removes clean origin index
`1`.

No new corruption parameter is selected in this layer.

## Clean registration topology

The clean three-event stream produces two consecutive registration inputs:

- clean origin `0 -> 1`
- clean origin `1 -> 2`

## Corrupted registration topology

The paired corrupted stream contains clean origins:

`[0, 2]`

and therefore produces one registration input:

- clean origin `0 -> 2`

This topology change is the intended mechanical consequence of the event gap.

## Estimator outputs

The frozen registration kernel may emit:

- rigid relative-pose estimates;
- fixed-point iteration counts;
- nearest-neighbor RMSE diagnostics;
- point/correspondence counts.

These values are execution outputs only.

They are not:

- ground-truth errors;
- ATE;
- RPE;
- acceptance thresholds;
- corruption-severity selection criteria;
- evidence that one corruption instance is preferable to another.

The prospective contract explicitly forbids using the observed output of this
smoke to modify its already-frozen corruption specification.

## Scientific boundary

This layer does not:

- access a reference trajectory;
- access confirmation-test data;
- perform reference association;
- align trajectories;
- compute ATE;
- compute RPE;
- score the clean estimator;
- score the corrupted estimator;
- calculate a clean-versus-corrupt accuracy metric;
- select severity;
- select an attack budget;
- modify the independent M2DGR evaluation protocol.

It proves only that controlled corruption deterministically changes the input
pair topology reaching the same frozen registration kernel.

Phase-3 exit evidence remains unsatisfied after this layer.
