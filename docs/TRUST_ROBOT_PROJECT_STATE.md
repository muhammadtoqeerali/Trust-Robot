# TRUST-ROBOT Project State

Last Updated: 2026-09-16

Repository: `muhammadtoqeerali/Trust-Robot`

This document is the authoritative implementation-state record for the
TRUST-ROBOT research project.

## Current phase

Phase 3 — Synchronization Verification

Status: IN PROGRESS.

Completed subphase:

**Phase 3A — M2DGR Sensor Timing Characterization and Stream Inventory.**

Phase 3A does not verify cross-stream synchronization.

## Current validated software state

TRUST-ROBOT unit tests:

**75 PASS.**

Implemented Phase-3A components:

- strict M2DGR timing-evidence loader/validator
- hash-bound timing-evidence index
- exact structural header-anomaly validation
- trajectory-specific M2DGR stream admission
- sensor-header-stamp measurement-time basis
- conservative synchronization metadata
- reproducible all-trajectory timing scanner
- reproducible exact-header-anomaly scanner
- reproducible metadata-only Phase-3 finalizer

## M2DGR Phase-3A dataset result

Trajectories audited:

36.

Stream availability:

- handsfree IMU: 36/36
- Velodyne: 36/36
- camera image: 34/36
- camera IMU: 34/36

`street_09` and `street_010` contain neither audited camera stream.

The Phase-3 successor manifest therefore contains 140 admitted stream entries
and 140 corresponding synchronization entries.

## Measurement-time basis

The sensor message header timestamp is the observed measurement-time field.

ROS bag record time is retained as transport/provenance diagnostic
information only.

Observing the header timestamp does not by itself verify synchronization.

## Structural timing findings

Message decode errors:

0.

Strict reversed sensor-header timestamps:

1.

The reversal is:

- trajectory: `hall_05`
- stream: `/camera/imu`
- previous index: 53375
- current index: 53376
- delta: -49.212455 ms

Large monotonic camera-IMU startup/header anomalies were observed in:

- `lift_02`
- `street_06`
- `room_dark_03`
- `walk_01`
- `gate_02`

They remain diagnostic observations only.

No magnitude-based invalidity threshold has been introduced.

## Phase-3A immutable artifacts

Timing evidence index:

`manifests/m2dgr_timing_evidence_index_v1.json`

Content SHA256:

`f2b1a74cb67124ec6fa725a23e3d8be8d2bd3d9d431590ad29ca1235dab149d6`

File SHA256:

`70f8dbf16b2363c55fa180a8180d7fbc322495c25790498ddf64fb4d74c87b3f`

Phase-3 successor manifest:

`manifests/m2dgr_trajectory_manifest_v1_phase3_timing_audited.json`

Content SHA256:

`5f8c4dcb398d684f809333307b2902231e69bb0ab51e596c95b3f62d6f652299`

File SHA256:

`5f7f7b14b89c9e9ef8f13aa3ed627c32b0409baca652238cc27c303554c666ea`

The Phase-2 manifest remains retained and unchanged.

Bag payloads were not rehashed during Phase-3A metadata finalization.
Checksum provenance was instead cross-validated across existing checksum
sidecars, Phase-2 integrity metadata, Phase-3 timing artifacts, and the
timing-evidence index.

## Synchronization state

At this checkpoint:

- measurement-time field observed: TRUE
- trajectory-specific stream presence audited: TRUE
- timing characterization complete: TRUE
- synchronization verified: FALSE
- fixed sensor-time offset estimated: FALSE
- synchronization tolerance frozen: FALSE
- common header-range adopted as validity mask: FALSE
- automatic timestamp repair enabled: FALSE
- automatic timestamp sample exclusion enabled: FALSE
- reference-to-estimator temporal association verified: FALSE
- continuous-time reference coverage verified: FALSE
- evaluation ready: FALSE

Estimator scoring therefore remains blocked.

## Phase-3 scientific rules

Do not:

- use bag record time as sensor measurement time;
- interpret low nearest-neighbor timing error as synchronization proof;
- infer a global fixed offset from the observed startup anomalies;
- convert the numeric common header-range intersection into an automatic
  validity interval;
- automatically repair or drop the `hall_05` reversed timestamp;
- select an association tolerance on confirmation/test data;
- fabricate missing camera streams for `street_09` or `street_010`.

## Remaining Phase-3 work

1. Establish independent or dataset-supported evidence for actual clock
   synchronization semantics.
2. Determine whether streams share a clock domain or require explicit
   clock-domain transformations.
3. Establish reference-to-estimator temporal association policy.
4. Determine whether any fixed offset is scientifically justified.
5. Define any numerical association tolerance only from permitted evidence.
6. Define explicit handling of structurally invalid timestamps such as the
   `hall_05` reversal without tuning on confirmation/test results.
7. Verify that any chosen policy generalizes beyond the observations used to
   construct it.
8. Keep evaluation readiness false until those requirements are satisfied.

## Development rule

Long workstation scans must use a detached process with PID and persistent log.

Short metadata validation and unit-test commands may run interactively.
