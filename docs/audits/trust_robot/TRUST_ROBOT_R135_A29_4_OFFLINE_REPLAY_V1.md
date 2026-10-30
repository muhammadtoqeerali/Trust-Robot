# TRUST-ROBOT R135-A29-4 — Deterministic Offline Replay V1

## Purpose

This phase builds a reproducible software-only replay
scheduler for previously validated Nova Carter ROS 2 bag
metadata envelopes.

The source recording contains 843 messages across seven
ROS streams. The original data and detailed evidence
remain private.

## Source integrity

The scheduler operates on the A29-3 metadata envelopes,
which were independently cross-checked with the pinned
A28-3 full-bag audit report.

The replay phase does not re-deserialize the original
ROS bag or revalidate its original file hashes.

## Scheduling semantics

Input records are ordered by recorded SQLite timestamps
and source order. Equal timestamps retain source order.

A replay tick is an arbitrary software iteration, not
a physical time interval or robot sensor period.

No sensor-header timestamps, frame IDs, physical
exposure times or cross-sensor time offsets are inferred.

## Bounded queue design

The simulator uses a bounded FIFO envelope queue.

A full queue causes explicitly counted drop-tail
overflow. No silent overwrite of queued records occurs.

The output reports source counts, delivered counts,
intentional synthetic suppression, queue overflow,
peak queue occupancy and a deterministic trace digest.

The complete input envelope list is loaded into memory;
the bounded queue applies to scheduling, not to total
input storage.

## Synthetic scenario matrix

The five fixed simulations are:

1. Lossless metadata replay.
2. Synthetic LiDAR suppression.
3. Synthetic stereo-image suppression.
4. Synthetic IMU suppression.
5. Synthetic bounded-queue pressure.

These are software perturbations of envelope metadata,
not observations of actual physical sensor failures.

The scenario outputs cannot be interpreted as robot
localization recovery rates, sensor health probabilities
or physical synchronization accuracy.

## A27 frame boundary

The actual physical IMU reports `bmi088_frame`.

The inspected nominal URDF does not declare that frame,
and equivalence with the nominal camera IMU frame
remains unverified.

No physical IMU-to-platform transform is assigned.

## Scientific restrictions

- Real sensor-factor admission: DENIED.
- Original M2DGR scientific gates: 11 CLOSED.
- Frozen split: 22 train / 7 validation-calibration /
  7 confirmation-test sequences.
- No held-out confirmation-test access or fitting.
- A23 qualified independent evidence receipts: 0 of 13.
- Physical clock accuracy: UNVERIFIED.
- Metric sensor calibration: UNVERIFIED.
- Independent six-DoF reference: UNVERIFIED.
- Real localization accuracy: NOT ESTABLISHED.
- Physical sensor health calibration: NOT ESTABLISHED.
- Estimator invoked by this phase: NO.
- Real factors created by this phase: ZERO.

## Next research requirements

Resolve sensor-frame identity and extrinsic provenance;
independently qualify time and calibration conventions;
then define a physically referenced evaluation protocol.

No robot movement, physical localization accuracy,
or navigation-control claim is made by this audit.
