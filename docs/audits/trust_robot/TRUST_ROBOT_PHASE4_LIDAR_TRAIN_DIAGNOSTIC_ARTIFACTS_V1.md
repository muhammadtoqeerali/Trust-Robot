# TRUST-ROBOT Phase-4 LiDAR TRAIN Diagnostic Artifacts V1

## Purpose

This layer materializes the first persistent real-data Phase-4 diagnostic
feature artifacts.

It reuses only the already-frozen Phase-2 TRAIN registration JSONL artifacts.

No ROS bag is opened and the estimator is not rerun.

## Frozen source schema

Every Phase-2 `relative_pose` record contains exactly one diagnostic mapping
at:

`diagnostics`

The real TRAIN set contains:

- 22 trajectories;
- 91,014 LiDAR scans;
- 90,992 consecutive registration records;
- 90,992 diagnostic records.

The Phase-4 preflight validated that every one of those diagnostic mappings is
compatible with the native five-feature extractor.

## Persistent feature records

One compact Phase-4 JSONL feature record is written for each frozen Phase-2
`relative_pose` record.

Each artifact binds:

- trajectory identity;
- source scan index;
- source JSONL line number;
- previous/current header labels;
- header delta;
- the five direct numeric diagnostic values;
- native feature-record fingerprint;
- exact raw source-line SHA256;
- canonical source-pair-record SHA256;
- its own content SHA256.

The source pose estimate itself is not copied into the diagnostic artifact.

## Deterministic real-data identity

The global extraction identity was first established during the read-only
preflight and is required to reproduce exactly during persistent extraction:

`42658bdb5739200f02dc1397f753b78ca60eb22f6bc5d913e42c6a208fc61020`

This digest binds trajectory ordering, source line positions and native
diagnostic feature-record fingerprints.

It is provenance evidence only.

It is not a diagnostic score, localization score, health score, fault score,
ranking or threshold.

## Scientific boundary

This layer does not:

- open ROS bags;
- decode PointCloud2 data;
- rerun registration;
- execute corruption;
- calculate descriptive feature statistics;
- normalize diagnostics;
- aggregate temporal windows;
- apply diagnostic thresholds;
- emit healthy/degraded/unusable states;
- emit fault labels;
- emit reliability scores;
- access reference trajectories;
- access confirmation-test data;
- compute ATE/RPE;
- score the estimator.

Phase-4 exit evidence remains unsatisfied pending validation of the diagnostic
contract on the already-frozen paired clean/corrupt registration evidence and
the subsequent Phase-4 closure review.
