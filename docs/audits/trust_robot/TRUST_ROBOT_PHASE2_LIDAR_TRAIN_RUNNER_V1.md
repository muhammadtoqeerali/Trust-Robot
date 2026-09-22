# TRUST-ROBOT Phase-2 LiDAR TRAIN Runner V1

## Purpose

This runner executes the current non-tuned LiDAR frontend candidate over all
22 frozen TRAIN trajectories, sequentially.

It is an estimator execution run, not an evaluation run.

## Frozen scope

The trajectory order is fixed to the already-frozen TRAIN partition.

The runner exposes no trajectory-selection command-line option.

It opens only:

`raw/rosbags/<TRAIN_TRAJECTORY>.bag`

and only reads:

`/velodyne_points`

with message type:

`sensor_msgs/msg/PointCloud2`

No reference, GNSS, RTK, Leica, mocap, odometry, pose, or confirmation-test
stream is requested.

## Fail-closed behavior

The runner performs no scan skipping and no trajectory skipping.

Any input-contract or registration error terminates the run and creates a
failure artifact identifying the exact trajectory and scan index.

There is deliberately no automatic:

- residual acceptance threshold;
- registration timeout;
- iteration cap;
- outlier-exclusion rule;
- scan exclusion rule;
- trajectory exclusion rule.

A failure therefore cannot silently alter the clean estimator definition.

## Persistent artifacts

The dataset-local run directory contains:

- deterministic run manifest;
- append-only per-trajectory JSONL state/increment records;
- per-trajectory completion summaries;
- atomic progress state;
- final summary on successful completion;
- explicit failure artifact on fail-closed termination;
- persistent stdout/stderr log;
- PID file.

The JSONL trajectory records include registration diagnostics such as nearest
neighbor RMSE and fixed-point iteration count. These values are diagnostics,
not acceptance thresholds or evaluation scores.

## Scientific boundary

The run does not resolve the PointCloud2 physical scan-reference ambiguity.

Per-point time remains unused and no deskew is performed.

The run does not perform:

- ground-truth association;
- trajectory alignment;
- ATE;
- RPE;
- trajectory scoring;
- estimator scoring.

Completion of this execution is therefore evidence that the clean frontend can
produce deterministic real-data 6-DoF trajectories. It does not by itself
authorize the separate blocked M2DGR evaluation protocol or satisfy Phase-2
exit evidence.
