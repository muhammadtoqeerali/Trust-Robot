# TRUST-ROBOT Project State

Last Updated: 2026-09-18

Repository: `muhammadtoqeerali/Trust-Robot`

This document is the authoritative implementation-state record for the
TRUST-ROBOT research project.

## Current evidence gate

M2DGR Calibration Verification

Status: IN PROGRESS.

The synchronization-verification evidence gate is complete with a conservative
negative/unverified outcome.

Completed synchronization checkpoints:

- **Phase 3A — M2DGR Sensor Timing Characterization and Stream Inventory**
- **Phase 3B — M2DGR Synchronization Evidence and Conservative Clock Semantics**
- **Phase 3C — M2DGR Camera-Image ↔ D435i-IMU Timing Characterization**
- **Phase 3D — M2DGR LiDAR ↔ HandsFree-IMU Timing Characterization**
- **Phase 3E — M2DGR Reference ↔ Estimator Temporal-Association Evidence**

Phases 3C–3E characterize the released timing evidence to its defensible
limits. They do not upgrade physical capture synchronization or
reference-to-estimator temporal association to verified status.

The active calibration gate now has permanent calibration evidence and hardened
artifact semantics, but it does not declare the dataset calibration verified.

## Current validated software state

TRUST-ROBOT unit tests:

**111 PASS.**

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
- strict Phase-3C camera/IMU evidence schema/validator
- frozen visual/gyro zero-lag association method
- 28-trajectory Phase-3C zero-lag generalization cohort
- conservative Phase-3C successor-manifest migration
- reproducible Phase-3C camera/IMU finalizer
- strict Phase-3D LiDAR/IMU evidence schema/validator
- VLP-32C point-time mechanism characterization across all 36 trajectories
- frozen LiDAR/HandsFree zero-lag rotation association method
- 36-trajectory Phase-3D zero-lag generalization cohort
- conservative Phase-3D successor-manifest migration
- reproducible Phase-3D LiDAR/IMU finalizer
- strict Phase-3E reference temporal-association evidence validator
- 36-trajectory reference timestamp-coordinate inventory
- family-specific reference/sensor numeric-overlap characterization
- 25-trajectory rotation-supported reference/HandsFree content cohort
- frozen three-trajectory LiDAR ICP translation characterization
- native-reference/LiDAR translation temporal-support diagnostics
- 16-trajectory RTK/INS ↔ GNSS receiver-UTC coordinate characterization
- explicit Phase-3E policy blocking interpolation, lag fitting, automatic
  exclusions, association-tolerance freezing, and evaluation readiness
- explicit contract rule that equal `clock_domain` strings are not
  synchronization proof
- calibration source-provenance inventory tied to upstream M2DGR revision and
  calibration-file hashes
- frozen 28-trajectory fixed-hypothesis D435i-IMU relative-rotation challenge
- calibration-requirements inventory separating supported versus unresolved
  intrinsic, extrinsic, and reference-origin quantities
- explicit calibration-artifact roles separating raw-file integrity,
  calibration provenance, and sensor-calibration verification
- permanent M2DGR calibration-evidence schema/validator
- historical trajectory-manifest serialization preserved byte-for-byte

## M2DGR stream inventory

Trajectories audited:

36.

Stream availability:

- HandsFree IMU: 36/36
- Velodyne: 36/36
- camera image: 34/36
- camera IMU: 34/36

`street_09` and `street_010` contain neither audited camera stream.

The current Phase-3D successor contains:

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

The Phase-3B manifest remains retained as the immutable predecessor of the
Phase-3C successor.

## Phase-3C immutable artifacts

Camera/IMU synchronization evidence:

`manifests/m2dgr_camera_imu_synchronization_evidence_v1.json`

Content SHA256:

`d765f8ac13ff21dca23e289efef65fed31372189363e7fa61982e122514e190b`

File SHA256:

`95ff9fdcaf2b74a9f7b118334f0fe3626bee3afe0916c3e09df4a7451d8425c7`

Phase-3C successor manifest:

`manifests/m2dgr_trajectory_manifest_v1_phase3c_camera_imu_sync_evidence.json`

Content SHA256:

`f599be5bb1b4d009fe77ff8eb33148880122f92f4bfe00f885ec18015d715387`

File SHA256:

`4453544d437b31cb0ab16b090dfa2e710fab19cb1b90cb65b53d7651166eb156`

The successor changes 68 D435i synchronization `method` fields only.
Clock domains, verification state, offsets, tolerances, stream metadata, and
non-camera synchronization entries are unchanged from Phase 3B.

## Phase-3C camera/IMU findings

The frozen visual/gyro method processed all 28 predeclared clean-cohort
trajectories.

Zero-lag vector correlation:

- minimum: 0.069851642
- median: 0.728267345
- maximum: 0.943895974

Per-trajectory median rotation disagreement:

- minimum: 0.128085942 degrees
- median: 0.257421703 degrees
- maximum: 1.639230858 degrees

The physical-content association is therefore heterogeneous.

A three-trajectory frozen lag pilot produced primary vector-correlation optima:

- `gate_01`: +23 ms
- `hall_01`: -67 ms, at the predeclared scan boundary
- `room_01`: -3 ms

Independent rotation-error diagnostics did not select the same lags.

No common nonzero camera/IMU fixed offset is supported.

No wider lag scan is authorized to force an offset.

Released bags do not retain the RealSense metadata/raw motion topics required
to independently identify the RGB physical capture event represented by the
released ROS image header.

Camera-image-to-IMU timing characterization is therefore complete to the limit
supported by released evidence, while physical capture synchronization remains
unverified.

## Phase-3D LiDAR/IMU findings

The released `/velodyne_points` payload contains a FLOAT32 `time` field.

Across a frozen 36-trajectory payload characterization, its numeric behavior
strongly matches the public VLP-32C firing-time table and is strongly
consistent with a last-packet-referenced relative-time construction.

The exact M2DGR Velodyne driver revision/runtime configuration and physical
PointCloud2-header reference event remain independently unverified.

The frozen LiDAR/HandsFree zero-lag method uses undeskewed whole-scan ICP and
HandsFree gyro integration between LiDAR header timestamps.

Across all 36 trajectories:

- candidate LiDAR intervals: 10764
- admitted intervals with real IMU support: 10758
- unsupported intervals: 6, all leading boundary intervals
- internal unsupported intervals: 0
- failed ICP intervals: 0
- vector-correlation min/median/max:
  0.798444575 / 0.987891015 / 0.998822853
- rotation-angle-correlation min/median/max:
  0.859841312 / 0.988835748 / 0.998959923
- median rotation-error min/median/max:
  0.030531038 / 0.083623408 / 0.251305615 degrees

No quality threshold or evaluation exclusion rule is derived from these
metrics.

A frozen three-trajectory descriptive lag pilot produced vector-correlation
optima of -46 ms, -35 ms, and -54 ms, while median-error optima were -50 ms,
-85 ms, and -99 ms.

Because one undeskewed rotating LiDAR scan spans approximately 100 ms, the
effective temporal support of whole-scan registration confounds interpretation
of these lags as a hardware clock offset.

No wider lag scan is authorized.

No LiDAR/IMU offset or synchronization tolerance is frozen.

LiDAR-to-IMU timing characterization is complete to the limit justified by the
released evidence, while physical capture synchronization remains unverified.

## Phase-3E reference temporal-association findings

Permanent evidence:

`manifests/m2dgr_reference_temporal_association_evidence_v1.json`

Content SHA256:

`505c1b63fc7e74907ce915472b243230a2cc86017248edaca255b5be5bc079fd`

File SHA256:

`4f6580c6a0b06b4089990adcc700b5d823a748bacacfc0f00c3dd3b4169d9117`

The Phase-3D trajectory manifest remains byte-identical and authoritative:

`manifests/m2dgr_trajectory_manifest_v1_phase3d_lidar_imu_sync_evidence.json`

File SHA256:

`67fe08bff676689dd212da03dce8e16ecee277c96f38f752d0d38a5e4e54cf6f`

No Phase-3E successor trajectory manifest is created because the current
trajectory-manifest schema has no explicit reference-to-estimator
temporal-association field. Reusing sensor synchronization fields would
conflate sensor-to-sensor synchronization with reference timing.

Reference timestamp-coordinate inventory covers all 36 trajectories. All
references have numeric overlap with the audited HandsFree and LiDAR sensor
header coordinates, but numeric overlap is not synchronization proof and is
not an evaluation interval.

For the 25 rotation-supported references, a frame-invariant native-interval
rotation-rate comparison produced:

- RTK/INS, 16 trajectories, correlation min/median/max:
  `0.700585994 / 0.970229178 / 0.990359633`
- mocap, 9 trajectories, correlation min/median/max:
  `0.091928138 / 0.174282151 / 0.611117285`

The RTK/INS family therefore has strong nominal-coordinate rotational-content
agreement, while mocap is weak and heterogeneous. Neither result proves
physical synchronization, and the mocap result does not justify lag tuning.

Translation diagnostics were intentionally limited to `gate_01`, `hall_01`,
and `room_01` using the frozen Phase-3D LiDAR ICP frontend.

Reference-step/LiDAR-midpoint correlations were:

- `gate_01`: `0.178972065`
- `hall_01`: `0.707523123`
- `room_01`: `0.866145937`

When temporal support was instead defined by native LiDAR intervals:

- `gate_01`: `0.369118202`
- `hall_01`: not computable for any of 299 pairs without interpolation
- `room_01`: `0.038627360`

The translation result is therefore not robust to a reasonable temporal-support
definition. Undeskewed whole-scan effective time and the unverified
reference-to-LiDAR lever arm remain material confounds. No translation lag
scan is authorized.

Phase 3B independently established that `/ublox/fix` headers exactly reproduce
GNSS receiver UTC on the GNSS-bearing trajectories. Across all 16 RTK/INS
reference trajectories, the reference timestamp range contains the full
receiver-UTC fix range, but zero trajectories have every receiver-UTC fix epoch
exactly present as a released RTK/INS reference timestamp. Exact per-sample
identity is not expected under different native sampling and is not itself a
requirement; the result therefore establishes only broad numeric epoch
compatibility, not RTK pose measurement-time semantics.

Phase-3E conclusion:

- reference-to-estimator temporal association verified: FALSE
- one global reference timing policy justified: FALSE
- reference interpolation authorized: FALSE
- nearest-neighbor pose association authorized: FALSE
- reference fixed offset estimated/applied: FALSE
- association tolerance frozen: FALSE
- evaluation interval created: FALSE
- automatic sample exclusion rule created: FALSE
- synchronization verified: FALSE
- evaluation ready: FALSE

## M2DGR calibration-verification findings

Permanent evidence:

`manifests/m2dgr_calibration_evidence_v1.json`

Content SHA256:

`81b430950c274840c5611f76e9cd0d5be18382f884d1b7870e7d827bd5bdc3b6`

File SHA256:

`dd4d4a8a3424460e93ad8a568499da4d94a537457812ae33f096dd7caef823a2`

The permanent evidence binds three frozen calibration staging artifacts:

- source provenance:
  - content SHA256:
    `94880e9d48a91fa610b24b212f2f076a148214eab92aa6dd3fdc6eba5f870915`
  - file SHA256:
    `ccc265172ceee536079d55649bbe40901ccaba50c82f5b0362bf2e3b9ac449ab`
- D435i-IMU relative-rotation fixed-hypothesis challenge:
  - content SHA256:
    `f3b01ddd77a013aeb16fddf14fe4b65ffff29525e9fa15b63bb8d4b30951f6a8`
  - file SHA256:
    `ab0e4f32ed91ca6045336eec85320108342e7ebc356673a9306ddff6c052b4e2`
- calibration requirements inventory:
  - content SHA256:
    `80bd741e363e9bb2ec4608f7c9db3c5b24955d042546b0e32e0a73530c119c39`
  - file SHA256:
    `86aba0afbbf2c7c0279365632379bf5d96b8fc9739a0a025b9a2fde1b1c5cc3a`

Upstream calibration provenance is anchored to M2DGR revision
`5db59c1fe38d8f1d2fb3a71f1f8c5581b8de00e5`.

The released calibration history contains explicit rectification, and the
current calibration source retains known source-quality flags. No `/tf`,
`/tf_static`, `CameraInfo`, or calibration-like ROS topic was found in the 36
released bags under the frozen connection inventory.

The frozen Phase-3B orientation diagnostic was reused without reopening bags,
fitting a rotation, fitting a lag, choosing a motion threshold, choosing a
score threshold, or changing cohort membership.

Across the predeclared 28-trajectory clean IMU cohort:

- published rotation > identity: 28/28
- published rotation > published-transpose alternative: 28/28
- published rotation > both fixed alternatives: 28/28
- published-minus-best-fixed-alternative:
  - minimum: 0.9030439055777579
  - median: 0.9901506700620717
  - maximum: 1.002646689257515

This is independent released sensor-content support for the published D435i-IMU
relative-rotation convention. It is not full extrinsic-calibration
verification.

Frozen unresolved calibration state:

- independently verified full extrinsics: 0
- independently verified camera intrinsic sets: 0
- independently verified reference sensor-origin-to-LiDAR lever arms: 0
- strongly sensor-content-supported relative rotations: 1
- camera intrinsics independently verified: FALSE
- camera-color ↔ LiDAR extrinsic independently verified: FALSE
- HandsFree ↔ LiDAR full extrinsic independently verified: FALSE
- RTK/INS reference lever-arm applicability independently verified: FALSE
- Leica reference lever-arm applicability independently verified: FALSE
- published mocap ↔ LiDAR transform found: FALSE
- dataset calibration verified: FALSE
- synchronization verified: FALSE
- evaluation ready: FALSE

The existing 36 trajectory-manifest `calibration_artifacts` entries are raw-bag
integrity artifacts. Their `verification_status=verified` verifies artifact
integrity, not sensor calibration.

The hardened contract now distinguishes:

- `artifact_integrity`
- `calibration_provenance`
- `sensor_calibration_verification`

Legacy artifacts decode as `artifact_integrity` and do not establish sensor
calibration. A sensor-calibration verification artifact must be explicitly
scoped to streams or frames and must have verified status.

No calibration successor trajectory manifest is created. The Phase-3D
trajectory manifest remains authoritative and byte-identical:

`manifests/m2dgr_trajectory_manifest_v1_phase3d_lidar_imu_sync_evidence.json`

File SHA256:

`67fe08bff676689dd212da03dce8e16ecee277c96f38f752d0d38a5e4e54cf6f`

## Synchronization state

At the calibration-verification checkpoint:

- measurement-time field observed: TRUE
- trajectory-specific stream presence audited: TRUE
- GNSS receiver UTC independently characterized: TRUE
- host/system-epoch sensor-header behavior observed: TRUE
- IMU near-zero physical-content association observed: TRUE
- camera/IMU physical-content consistency observed on many trajectories: TRUE
- camera/IMU consistency uniform across the clean cohort: FALSE
- unique nonzero camera/IMU fixed offset identified: FALSE
- common physical clock independently verified: FALSE
- camera-image-to-IMU capture timing independently verified: FALSE
- LiDAR-to-IMU timing characterized to released-evidence limit: TRUE
- LiDAR-to-IMU capture timing independently verified: FALSE
- reference timestamp-coordinate inventory complete: TRUE
- RTK/INS nominal-coordinate rotational-content consistency strong: TRUE
- mocap rotational-content consistency uniform: FALSE
- Leica LiDAR-native translation association computable without
  interpolation: FALSE
- RTK/INS pose timestamp physical-event semantics independently verified: FALSE
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
- fabricate missing camera streams for `street_09` or `street_010`;
- freeze the Phase-3D -35 to -54 ms correlation optima as a LiDAR/IMU clock offset;
- use LiDAR/IMU correlation magnitude as an automatic timing-validity threshold;
- widen the LiDAR/IMU lag scan to force a fixed-offset result;
- treat numeric reference/sensor interval overlap as synchronization proof;
- turn numeric reference/sensor overlap into an evaluation interval;
- interpolate Leica reference solely to make a timing diagnostic computable;
- tune a mocap lag scan around weak/heterogeneous reference content;
- convert Phase-3E correlation magnitude into an admission threshold;
- infer RTK pose measurement-time semantics merely from broad receiver-UTC
  coordinate overlap.

## Remaining calibration/evaluation work

1. Preserve the Phase-3C camera/IMU result as unverified physical capture
   synchronization; do not resume lag tuning without new independent evidence.
2. Preserve the Phase-3D LiDAR/IMU result as unverified physical capture
   synchronization; do not reinterpret whole-scan lag optima as clock offsets.
3. Preserve the Phase-3E reference-temporal result as unverified association;
   do not introduce interpolation, lag fitting, or an association tolerance
   without new independent evidence.
4. Preserve the calibration checkpoint distinction between sensor-content
   support for one relative rotation and full calibration verification.
5. Do not fit camera intrinsics, extrinsic translations, reference lever arms,
   calibration tolerances, or admission thresholds on the current all-training
   M2DGR release merely to make evaluation computable.
6. Keep dataset calibration, synchronization, and evaluation readiness false
   until independent evidence resolves the required estimator/reference
   calibration and timing blockers.

## Development rule

Long workstation scans must use a detached process with PID and persistent log.

Short metadata validation, finalization, and unit-test commands may run
interactively.
