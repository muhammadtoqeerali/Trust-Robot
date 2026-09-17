# M2DGR Phase 3B Synchronization Evidence

Date: 2026-09-17

Status: completed evidence checkpoint; synchronization remains unverified.

## Purpose

Phase 3B evaluates what can and cannot be justified about M2DGR timing after
the Phase-3A header-timing characterization.

The objective is not to force a synchronization verdict.

The objective is to preserve evidence provenance and explicitly separate:

- timestamp representation
- clock-domain hypotheses
- transport timing
- physical-content association
- physical capture synchronization
- tolerance/offset decisions

## Evidence hierarchy

The Phase-3B work distinguishes:

1. dataset-author synchronization claims;
2. released configuration assumptions;
3. external driver/source-code semantics;
4. bag metadata observations;
5. independent dataset clock evidence;
6. physical-content temporal association.

Author claims and released configurations are provenance, not independent
verification.

## Connection inventory

All 36 M2DGR bags were inspected at the ROS connection-metadata level.

Observed:

- u-blox GNSS clock-related topics: 18/36
- `/clock`: 0/36
- `/diagnostics`: 0/36
- `/rosout`: 0/36
- `/velodyne_packets`: 0/36

Consequences:

- no raw Velodyne packet timestamp-mode reconstruction is available from the
  released bags;
- no startup ROS log evidence is available in-bag;
- GNSS clock evidence exists only for the GNSS-bearing half of the dataset and
  must not be extrapolated to indoor trajectories.

## GNSS receiver UTC evidence

On all 18 GNSS-bearing trajectories, every compared `/ublox/fix` header
timestamp exactly matched the independently resolved NavPVT receiver UTC.

Also observed:

- zero receiver clock resets;
- zero reverse receiver-UTC transitions;
- no unresolved NavPVT UTC epochs in the audit.

This independently establishes a coherent GNSS receiver UTC reference on those
18 trajectories.

It does not establish the clock used by the camera, LiDAR, or estimator IMUs.

## Bag-record relationship

Bag record time minus GNSS receiver UTC varies substantially across
trajectories and, for selected trajectories, materially within a trajectory.

This observation includes transport and processing latency and therefore must
not be interpreted as pure host-clock drift.

Bag record time remains transport/provenance diagnostic information only.

## Clock-domain fingerprint

Across GNSS-bearing trajectories:

- HandsFree `record - header` remains approximately sub-millisecond;
- Velodyne `record - header` remains approximately tens of milliseconds;
- camera image `record - header` remains approximately tens of milliseconds;
- camera IMU remains near the bag-record epoch but has greater timing
  variability.

Meanwhile `record - GNSS receiver UTC` changes by tens to hundreds of
milliseconds.

This pattern is consistent with the released estimator-input headers being
expressed in, or mapped into, a host/system-time epoch rather than retaining
native GNSS receiver UTC.

This is a timestamp-epoch observation, not a common-hardware-clock proof.

## Within-trajectory clock challenge

Three trajectories with substantial record-to-GNSS relationship variation were
examined:

- `street_02`
- `street_04`
- `street_05`

Observed first-to-last GNSS `record - receiver UTC` changes:

- `street_02`: -148.419640 ms
- `street_04`: -26.268762 ms
- `street_05`: -86.625338 ms

HandsFree `record - header` changed by only approximately:

- +0.010136 ms
- +0.001536 ms
- -0.002950 ms

Velodyne and camera streams were also far more stable relative to bag-record
time than the GNSS relationship.

This strengthens the host/system-epoch interpretation but does not establish
physical synchronization.

## Scalar IMU association pilots

Gyroscope-magnitude correlation between D435i IMU and HandsFree IMU was very
high, demonstrating common observed motion.

However, scalar magnitude produced broad/flat lag surfaces and inconsistent
window optima.

Gyro-magnitude derivatives had lower correlation and did not produce stable
lag estimates.

Therefore scalar association was not used to freeze an offset.

## Vector IMU association

The final association method used full 3-axis angular velocity after applying
the M2DGR author-published D435i-IMU-to-LiDAR rotation.

The HandsFree-IMU-to-LiDAR rotation published by M2DGR is identity.

The rotation was not estimated from timing data.

The published calibration is still author-provided and independently
unverified.

A three-trajectory pilot showed strong common-frame vector correlation and
narrower lag behavior than scalar magnitude.

The exact same frozen method was then applied to a predeclared 28-trajectory
structurally clean cohort.

## Clean-cohort definition

Excluded before alignment analysis:

Missing camera streams:

- `street_09`
- `street_010`

Known camera-IMU startup/header anomalies:

- `gate_02`
- `lift_02`
- `room_dark_03`
- `street_06`
- `walk_01`

Strict camera-IMU header reversal:

- `hall_05`

These separations are diagnostic only.

They are not an evaluation exclusion policy.

## Clean-cohort result

Trajectory count:

28.

Best HandsFree-minus-camera lag:

- minimum: -11 ms
- median: -4 ms
- maximum: 0 ms

Window-median lag:

- minimum: -9 ms
- median: -4 ms
- maximum: 0 ms

Window lag range:

- minimum: 5 ms
- median: 16 ms
- maximum: 34 ms

Zero-lag vector correlation:

- minimum: 0.921775782
- median: 0.996203211
- maximum: 0.998425969

Best-minus-zero vector-correlation improvement:

- minimum: 0.000000000
- median: 0.000086185
- maximum: 0.000651473

## Scientific interpretation

The IMU signals provide strong physical-content evidence for near-zero
temporal association at approximately the native IMU sample scale.

The evidence does not identify a stable, unique, scientifically justified
nonzero fixed offset.

In particular, the diagnostic cohort median of -4 ms is not frozen as an
offset.

No synchronization tolerance is selected.

## Conservative clock semantics

The Phase-3A manifest used the shared nominal string:

`sensor_clock`

for all estimator-input streams.

Because no common physical clock has been independently established, Phase 3B
retires that ambiguous shared label in the successor manifest.

The successor uses:

- `/handsfree/imu`:
  `m2dgr_handsfree_header_clock_unverified`
- `/camera/imu`:
  `m2dgr_camera_imu_header_clock_unverified`
- `/velodyne_points`:
  `m2dgr_velodyne_header_clock_unverified`
- `/camera/color/image_raw/compressed`:
  `m2dgr_camera_image_header_clock_unverified`

The data contract explicitly documents that equal clock-domain strings cannot
be treated as synchronization proof.

## Immutable evidence artifact

Repository path:

`manifests/m2dgr_synchronization_evidence_v1.json`

Content SHA256:

`a4e3e8dd18970a47f5cb50f4bb8ea3cb0e625f5f51d9eb0028bf34d953ee9966`

File SHA256:

`58615c56442485fc488eeb47f72dd074f51c05c64cda258a91a8c4937b83ef91`

## Phase-3B successor manifest

Repository path:

`manifests/m2dgr_trajectory_manifest_v1_phase3b_sync_evidence.json`

Content SHA256:

`5cf660327636174912d5d304972758c1b230fa4446ab584ca4549c76fdd6f4db`

File SHA256:

`95e7c97ae991538c2e7160c935cbaacf784b824eae7feecf1d7b540abe5ebb55`

Source Phase-3A manifest content SHA256:

`5f8c4dcb398d684f809333307b2902231e69bb0ab51e596c95b3f62d6f652299`

## Explicitly not claimed

Phase 3B does not claim:

- verified common physical clock;
- verified camera-image capture synchronization;
- verified LiDAR capture synchronization;
- verified reference-to-estimator association;
- independently verified calibration;
- a fixed sensor offset;
- a synchronization tolerance;
- an evaluation-validity exclusion mask;
- evaluation readiness.

## Remaining blockers

- camera-image-to-IMU physical capture timing
- LiDAR-to-IMU physical capture timing
- reference-to-estimator temporal association
- common physical clock verification
- validation/calibration split for any data-selected tolerance
- independent calibration verification

Synchronization remains `UNVERIFIED`.

Evaluation readiness remains `FALSE`.
