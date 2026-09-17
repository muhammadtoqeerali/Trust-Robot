# TRUST-ROBOT Project State

Last Updated: 2026-09-17

Repository: `muhammadtoqeerali/Trust-Robot`

This document is the authoritative implementation-state record for the
TRUST-ROBOT research project.

## Current phase

Phase 3 — Synchronization Verification

Status: IN PROGRESS.

Completed subphases:

- **Phase 3A — M2DGR Sensor Timing Characterization and Stream Inventory**
- **Phase 3B — M2DGR Synchronization Evidence and Conservative Clock Semantics**

Phase 3B does not complete physical capture-time synchronization verification.

## Current validated software state

TRUST-ROBOT unit tests:

**81 PASS.**

Implemented Phase-3 components now include:

- strict M2DGR timing-evidence loader/validator
- hash-bound timing-evidence index
- exact structural header-anomaly validation
- trajectory-specific M2DGR stream admission
- sensor-header-stamp measurement-time basis
- GNSS clock evidence characterization
- clock-domain fingerprint characterization
- within-trajectory record/header/GNSS clock challenge
- content-based IMU temporal association
- author-calibration-based vector-gyro association
- 28-trajectory clean IMU association cohort
- permanent synchronization-evidence schema/validator
- conservative Phase-3B successor-manifest migration
- reproducible Phase-3B finalizer
- explicit contract rule that equal `clock_domain` strings are not
  synchronization proof

## M2DGR stream inventory

Trajectories audited:

36.

Stream availability:

- HandsFree IMU: 36/36
- Velodyne: 36/36
- camera image: 34/36
- camera IMU: 34/36

`street_09` and `street_010` contain neither audited camera stream.

The current Phase-3B successor contains:

- 36 trajectory records
- 140 stream entries
- 140 synchronization entries

## Measurement-time basis

The ROS sensor-header timestamp is the observed measurement-time field.

ROS bag record time is transport/provenance diagnostic information only.

Bag record time is not accepted as a sensor capture timestamp.

## Phase-3A structural timing findings

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

These remain diagnostic observations only.

No magnitude-based invalidity threshold, automatic repair rule, or automatic
sample-exclusion rule has been introduced.

## GNSS clock evidence

Eighteen trajectories contain the audited u-blox GNSS clock topics.

Across all 18:

- `/ublox/fix` header timestamps exactly match independently resolved NavPVT
  receiver UTC for every compared fix sample;
- receiver UTC does not reverse;
- no receiver clock reset was observed;
- all NavPVT UTC epochs used by the audit were resolved.

This is strong evidence for receiver-derived UTC on the GNSS fix stream.

It does not prove that estimator-input sensors use the GNSS receiver clock.

## Bag-record versus GNSS relationship

The bag-record-time minus receiver-UTC relationship varies materially between
trajectories and can vary substantially within one trajectory.

This quantity combines at least:

- host-clock relation
- transport latency
- processing latency
- recording latency

Therefore it is not interpreted as pure clock drift or a directly applicable
sensor offset.

No bag-record-to-GNSS fixed offset has been estimated or applied.

## Sensor-header clock-domain evidence

Across GNSS-bearing trajectories, estimator-input sensor
`record_time - header_time` behavior remains comparatively stable while
`record_time - receiver_UTC` can change by tens or hundreds of milliseconds.

This is consistent with the released sensor headers being expressed in, or
mapped into, a host/system-time epoch.

It is inconsistent with treating the released estimator-input headers as
native GNSS receiver UTC.

This observation does **not** establish:

- a shared physical oscillator;
- common hardware triggering;
- physical capture-time synchronization;
- a fixed sensor-to-sensor offset.

## IMU physical-content association

The final clean-cohort diagnostic uses 28 trajectories selected from
pre-existing structural evidence, not from alignment performance.

Separated before the clean-cohort scan:

- missing camera streams: `street_09`, `street_010`
- known camera-IMU startup/header anomalies:
  `gate_02`, `lift_02`, `room_dark_03`, `street_06`, `walk_01`
- strict camera-IMU reversal: `hall_05`

The separation is diagnostic only and is not an evaluation exclusion policy.

The association signal is full 3-axis angular velocity after rotating the
D435i IMU and HandsFree IMU into the M2DGR author-published LiDAR frame.

The rotation was not estimated from timing data.

The published calibration remains author-provided and independently
unverified.

Clean-cohort results:

- trajectory count: 28
- best HandsFree-minus-camera lag:
  - min: -11 ms
  - median: -4 ms
  - max: 0 ms
- window-median lag:
  - min: -9 ms
  - median: -4 ms
  - max: 0 ms
- window lag range:
  - min: 5 ms
  - median: 16 ms
  - max: 34 ms
- zero-lag vector correlation:
  - min: 0.921775782
  - median: 0.996203211
  - max: 0.998425969
- best-minus-zero correlation:
  - min: 0.000000000
  - median: 0.000086185
  - max: 0.000651473

Interpretation:

There is strong content-based evidence for near-zero temporal association at
approximately native IMU sampling-scale resolution.

The evidence does not resolve a scientifically defensible unique nonzero
fixed offset.

No IMU offset is frozen.

## Clock-domain semantics

The Phase-3A shared literal:

`sensor_clock`

must not be interpreted as proof that all streams share one physical clock.

In Phase 3B, the successor manifest therefore uses distinct conservative
timestamp-domain labels:

- `/handsfree/imu`:
  `m2dgr_handsfree_header_clock_unverified`
- `/camera/imu`:
  `m2dgr_camera_imu_header_clock_unverified`
- `/velodyne_points`:
  `m2dgr_velodyne_header_clock_unverified`
- `/camera/color/image_raw/compressed`:
  `m2dgr_camera_image_header_clock_unverified`

These labels deliberately preserve uncertainty.

Clock-domain equality is not synchronization proof.

## Phase-3A immutable artifacts

Timing evidence index:

`manifests/m2dgr_timing_evidence_index_v1.json`

Content SHA256:

`f2b1a74cb67124ec6fa725a23e3d8be8d2bd3d9d431590ad29ca1235dab149d6`

File SHA256:

`70f8dbf16b2363c55fa180a8180d7fbc322495c25790498ddf64fb4d74c87b3f`

Phase-3A manifest:

`manifests/m2dgr_trajectory_manifest_v1_phase3_timing_audited.json`

Content SHA256:

`5f8c4dcb398d684f809333307b2902231e69bb0ab51e596c95b3f62d6f652299`

File SHA256:

`5f7f7b14b89c9e9ef8f13aa3ed627c32b0409baca652238cc27c303554c666ea`

## Phase-3B immutable artifacts

Synchronization evidence:

`manifests/m2dgr_synchronization_evidence_v1.json`

Content SHA256:

`a4e3e8dd18970a47f5cb50f4bb8ea3cb0e625f5f51d9eb0028bf34d953ee9966`

File SHA256:

`58615c56442485fc488eeb47f72dd074f51c05c64cda258a91a8c4937b83ef91`

Phase-3B successor manifest:

`manifests/m2dgr_trajectory_manifest_v1_phase3b_sync_evidence.json`

Content SHA256:

`5cf660327636174912d5d304972758c1b230fa4446ab584ca4549c76fdd6f4db`

File SHA256:

`95e7c97ae991538c2e7160c935cbaacf784b824eae7feecf1d7b540abe5ebb55`

The Phase-3A manifest remains retained and unchanged.

## Synchronization state

At the Phase-3B checkpoint:

- measurement-time field observed: TRUE
- trajectory-specific stream presence audited: TRUE
- GNSS receiver UTC independently characterized: TRUE
- host/system-epoch sensor-header behavior observed: TRUE
- IMU near-zero physical-content association observed: TRUE
- common physical clock independently verified: FALSE
- camera-image-to-IMU capture timing independently verified: FALSE
- LiDAR-to-IMU capture timing independently verified: FALSE
- reference-to-estimator temporal association verified: FALSE
- fixed sensor-time offset estimated: FALSE
- synchronization tolerance frozen: FALSE
- synchronization verified: FALSE
- calibration independently verified: FALSE
- continuous-time reference coverage verified: FALSE
- evaluation ready: FALSE

Estimator scoring remains blocked.

## Phase-3 scientific rules

Do not:

- use bag record time as sensor measurement time;
- interpret common numeric timestamp epoch as a common physical clock;
- interpret equal `clock_domain` strings as synchronization proof;
- interpret low nearest-neighbor timestamp difference as synchronization proof;
- convert the numeric common header-range intersection into a validity mask;
- automatically repair or drop the `hall_05` reversed timestamp;
- convert the 28-trajectory IMU clean cohort into an evaluation exclusion rule;
- freeze the observed -4 ms median diagnostic lag as a fixed offset;
- select an association tolerance from the current all-training manifest;
- fabricate missing camera streams for `street_09` or `street_010`.

## Remaining Phase-3 work

1. Independently characterize camera-image-to-IMU physical capture timing.
2. Independently characterize LiDAR-to-IMU physical capture timing.
3. Establish reference-to-estimator temporal association.
4. Independently verify calibration needed by evaluation.
5. Establish a scientifically valid validation/calibration split before any
   data-selected synchronization tolerance is frozen.
6. Define explicit handling of structurally invalid timestamps without tuning
   on confirmation/test data.
7. Keep synchronization and evaluation readiness false until required evidence
   is complete.

## Development rule

Long workstation scans must use a detached process with PID and persistent log.

Short metadata validation, finalization, and unit-test commands may run
interactively.
