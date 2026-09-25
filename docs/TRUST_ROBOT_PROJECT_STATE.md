# TRUST-ROBOT Project State

Last Updated: 2026-09-22

Repository: `muhammadtoqeerali/Trust-Robot`

This document is the authoritative implementation-state record for the
TRUST-ROBOT research project.

## Current evidence gate

M2DGR Trajectory Association and Evaluation Protocol

Status: BLOCKED PENDING PHYSICAL EVIDENCE.

Completed evidence checkpoints include:

- **Phase 3A — M2DGR Sensor Timing Characterization and Stream Inventory**
- **Phase 3B — M2DGR Synchronization Evidence and Conservative Clock Semantics**
- **Phase 3C — M2DGR Camera-Image ↔ D435i-IMU Timing Characterization**
- **Phase 3D — M2DGR LiDAR ↔ HandsFree-IMU Timing Characterization**
- **Phase 3E — M2DGR Reference ↔ Estimator Temporal-Association Evidence**
- **M2DGR Calibration Verification**
- **M2DGR Prospective Split Freeze V1**
- **M2DGR Trajectory Association / Evaluation Protocol Candidate V2**

The current authoritative trajectory manifest is:

`manifests/m2dgr_trajectory_manifest_v1_split_freeze_v1.json`

It contains the prospectively frozen `22 / 7 / 7`
train / validation-calibration / confirmation-test partition.

The split freeze changes only trajectory `split` fields relative to the
Phase-3D manifest. It does not upgrade timing, calibration, reference-frame
semantics, reference coverage, synchronization, or evaluation readiness.

A validation/calibration partition now exists for future protocol choices that
are scientifically selectable. Its existence cannot establish missing physical
facts such as timestamp measurement-event semantics, clock synchronization,
reference sensor origin, extrinsics, or continuous reference validity.

Estimator scoring remains blocked.

## Current validated software state

TRUST-ROBOT unit tests:

**344 PASS.**

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
- metadata-only prospective split design with a rejected V1 candidate and
  accepted deterministic V2 candidate
- permanent M2DGR split-freeze evidence and successor trajectory manifest
- 22 train / 7 validation-calibration / 7 confirmation-test frozen partition
- explicit prospective prohibition on confirmation-test use for model,
  threshold, association, alignment, or protocol selection
- blocked trajectory-association/evaluation protocol candidate V2
- validation/calibration-aware protocol semantics that still require
  independent physical timing/frame/calibration evidence before selection

## M2DGR stream inventory

Trajectories audited:

36.

Stream availability:

- HandsFree IMU: 36/36
- Velodyne: 36/36
- camera image: 34/36
- camera IMU: 34/36

`street_09` and `street_010` contain neither audited camera stream.

The current split-frozen successor contains:

- 36 trajectory records
- 140 stream entries
- 140 synchronization entries
- 22 `train` trajectories
- 7 `validation_calibration` trajectories
- 7 `confirmation_test` trajectories

Authoritative manifest:

`manifests/m2dgr_trajectory_manifest_v1_split_freeze_v1.json`

Content SHA256:

`3a845fb4545607cad09b8be61d445b6b8a238bd3f346fd6b56c8c630d45141a6`

File SHA256:

`017a388ef1ce4ad30812669632a022ca37c084871bc949693fd9c0541014238f`

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

At the Phase-3E checkpoint, the Phase-3D trajectory manifest remained
byte-identical and authoritative:

`manifests/m2dgr_trajectory_manifest_v1_phase3d_lidar_imu_sync_evidence.json`

File SHA256:

`67fe08bff676689dd212da03dce8e16ecee277c96f38f752d0d38a5e4e54cf6f`

No Phase-3E successor trajectory manifest was created because the
trajectory-manifest schema has no explicit reference-to-estimator
temporal-association field. Reusing sensor synchronization fields would
conflate sensor-to-sensor synchronization with reference timing.

This historical manifest was later superseded only for prospective split
assignment by
`manifests/m2dgr_trajectory_manifest_v1_split_freeze_v1.json`.

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

No calibration successor trajectory manifest was created. At the
calibration-verification checkpoint, the Phase-3D trajectory manifest remained
authoritative and byte-identical:

`manifests/m2dgr_trajectory_manifest_v1_phase3d_lidar_imu_sync_evidence.json`

File SHA256:

`67fe08bff676689dd212da03dce8e16ecee277c96f38f752d0d38a5e4e54cf6f`

The later split-freeze successor changes only prospective split assignment and
does not alter any calibration conclusion.

## M2DGR prospective split and evaluation-protocol findings

Permanent split-freeze evidence:

`manifests/m2dgr_split_freeze_evidence_v1.json`

Content SHA256:

`bc5699504efda7203165adb9b1ceaa62f2639288011cdb875df0a870ee068a2e`

File SHA256:

`9b1bddff5685f933372049966d9d72dd1162f66f8abfe29bbc80da3cbe38e9a9`

Current authoritative trajectory manifest:

`manifests/m2dgr_trajectory_manifest_v1_split_freeze_v1.json`

Content SHA256:

`3a845fb4545607cad09b8be61d445b6b8a238bd3f346fd6b56c8c630d45141a6`

File SHA256:

`017a388ef1ce4ad30812669632a022ca37c084871bc949693fd9c0541014238f`

Frozen split:

- train: 22
- validation/calibration: 7
- confirmation test: 7

The split was selected from author metadata, reference family, and current
estimator-input stream presence before estimator outcomes were used.

The rejected metadata-split V1 candidate was rejected before estimator outcomes
because it accidentally removed complete scenario and collection-date
categories from training.

The accepted V2 split retains all nine observed scenario categories and all nine
observed collection dates in training.

The confirmation partition is not claimed to be pristine from all prior
dataset-level inspection. All 36 trajectories were previously used for
structural/timing characterization and a 28-trajectory cohort was used for
earlier sensor-content evidence.

However, confirmation data had not been used to select estimator scores,
models, thresholds, association rules, alignment rules, or evaluation protocol
choices when the split was frozen.

From the freeze onward, confirmation data may not select any of those choices.

Current blocked evaluation-protocol candidate:

`configs/trust_robot/m2dgr_trajectory_association_evaluation_protocol_candidate_v2.json`

Content SHA256:

`8f60fa3a2303d6a2b8ad8d74719439358e2f7b19ca834c77e6cf09aa1889efbc`

File SHA256:

`4aaec974d9d7b7f0f057a8991dc0486654d58de5f8c2e6ebf239d5d3d313d6d3`

Protocol V2 recognizes the frozen validation/calibration split, but keeps:

- reference interpolation unauthorized;
- nearest-neighbor pose association unauthorized;
- association tolerance unset;
- fixed reference-to-estimator offset unset;
- evaluation interval uncreated;
- alignment mode unselected;
- ATE/RPE metric families disabled;
- estimator scoring unauthorized;
- dataset calibration unverified;
- synchronization unverified;
- evaluation readiness false.

The presence of validation/calibration data removes only the partition-absence
blocker. It cannot establish a physical fact that is absent from independent
evidence.



## M2DGR reference physical-semantics findings

Permanent additive evidence:

`manifests/m2dgr_reference_physical_semantics_evidence_v1.json`

Content SHA256:

`559598c00c8246c1626ae2e01279b59d7baad724a7919df3d4c7a5d5b96ca0a0`

File SHA256:

`afbc2c50b0facd9c51af2768aba1a3436b32c9102182a9cb886479714e4b7e2a`

Public author provenance now narrows the outdoor reference interpretation:

- the maintainer states that outdoor GT coordinates are ECEF rather than ENU;
- the maintainer states that all outdoor GT frames refer to the Xsens frame;
- the maintainer states that outdoor GT comes from the Xsens MTi 680G
  GNSS-IMU suite.

These are author statements, not independent calibration verification.

They do not establish the exact physical Xsens origin represented by each
released position, whether a published Xsens/GNSS-to-LiDAR candidate transform
applies to the released pose fields, whether such a correction was already
applied, or the physical event/timebase represented by the released timestamps.

The author calibration source still provides a Leica-to-LiDAR candidate
translation, and the paper states that a prism reflector was mounted on the
robot for Leica tracking. The released Leica position is not independently
verified to be exactly that prism-center coordinate, and applicability of the
published candidate transform remains unverified.

For mocap, the maintainer confirms that Room and Roomdark GT comes from mocap
and that occasional tracking loss can produce abrupt quaternion changes.
No published mocap-to-LiDAR transform was identified, no tracked-body origin is
verified, and the maintainer's filtering recommendation does not define an
admissible prospective filter or exclusion rule.

The author-linked toolkit was inspected at commit
`46e75065b45c640e7018443656514c8fbe1bf88b`, tree
`043390ad06e79534a98667d46bcd9ce23c55452c`. Its `export_tum.py`
uses ROS image-message header timestamps but does not export GT poses. No
GT-generation/export path was identified there.

The upstream-repository `hall_03.txt` and downloaded released
`raw/ground_truth/hall_03.txt` are byte-identical with SHA256
`679f821e27f253fc8655f4232aaa39eb635705d42c87e9062cc1d5410940abab`.

Current physical-semantics conclusion:

- outdoor ECEF coordinate representation author-supported: TRUE
- outdoor Xsens GT frame author-supported: TRUE
- exact RTK/INS physical origin verified: FALSE
- RTK/INS reference-to-LiDAR transform applicability verified: FALSE
- Leica tracked-point semantics verified: FALSE
- Leica reference-to-LiDAR transform applicability verified: FALSE
- mocap tracked-body origin verified: FALSE
- mocap-to-LiDAR transform verified: FALSE
- reference timestamp physical-event semantics verified: FALSE
- reference-to-estimator temporal association verified: FALSE
- reference interpolation authorized: FALSE
- association tolerance selected: FALSE
- alignment mode selected: FALSE
- estimator scoring authorized: FALSE
- dataset calibration verified: FALSE
- synchronization verified: FALSE
- evaluation ready: FALSE

The checkpoint is additive. Frozen Phase-3E, calibration, split-freeze, and
Evaluation Protocol V2 bytes are unchanged.


## M2DGR RTK reference geometry/timing-semantics findings

Permanent additive evidence:

`manifests/m2dgr_rtk_reference_geometry_timing_semantics_evidence_v1.json`

Content SHA256:

`84dd60b2b886f01e2377df777b629c360d982bab0737aaa55fa342f59791d201`

File SHA256:

`1cf9bbade44db2d1c35e49ff89984cb7e9a34fdfe99978f9c0213e306135c42b`

A frozen author cross-file check now supports one narrow transform-convention
statement.

The author calibration entry `Handsfree IMU [to LIDAR]` is exactly equal to the
inverse of the author's LIO-SAM transform explicitly labeled
`lidar -> IMU`.

Maximum matrix residual:

`0.0`

This supports the author transform-direction convention for the cross-checked
HandsFree IMU block only.

It is not independent physical calibration verification and is not generalized
to the Xsens IMU, GNSS, Leica, or other calibration blocks.

The author-published Xsens IMU and GNSS candidate translations differ by:

`[-0.2573, 0.00515, 0.89497] m`

with norm:

`0.9312363359534465 m`.

This is author candidate geometry only. It is not promoted to the actual
MTi-680G runtime GNSS lever arm.

Hash-bound Xsens manufacturer documentation establishes that the MTi-680G can
be configured with a GNSS lever arm defined from the MT device measurement
origin to the GPS antenna, and that the algorithm can use it to correct
position and velocity. It also documents an optional position/velocity
smoother.

The actual M2DGR runtime lever-arm value/configuration and smoother setting
remain unknown.

Manufacturer low-level documentation distinguishes `XDI_UtcTime`,
`XDI_SampleTimeFine`, and `XDI_SampleTimeCoarse`. The released M2DGR RTK/INS
GT timestamp source/export path remains unidentified.

Current RTK/INS conclusion:

- HandsFree-block author direction convention cross-file supported: TRUE
- HandsFree physical extrinsic independently verified by this result: FALSE
- all calibration blocks cross-file direction verified: FALSE
- exact released RTK/INS physical origin verified: FALSE
- RTK/INS candidate transform applicability verified: FALSE
- runtime Xsens GNSS lever arm verified: FALSE
- runtime Xsens smoother setting verified: FALSE
- RTK/INS GT timestamp physical-event semantics verified: FALSE
- RTK/INS GT timestamp timebase/export semantics verified: FALSE
- reference-to-estimator temporal association verified: FALSE
- reference interpolation authorized: FALSE
- association tolerance selected: FALSE
- evaluation interval created: FALSE
- alignment mode selected: FALSE
- estimator scoring authorized: FALSE
- dataset calibration verified: FALSE
- synchronization verified: FALSE
- evaluation ready: FALSE

This checkpoint is additive. The frozen physical-semantics evidence and
Evaluation Protocol V2 remain byte-identical.


## M2DGR GT recording/released-stream provenance findings

Permanent additive evidence:

`manifests/m2dgr_gt_recording_stream_provenance_evidence_v1.json`

Content SHA256:

`48d3bac20d621d98e0846fd44545efec9080b0795d55682c9494979bae8b9464`

File SHA256:

`f8cbf76663a027e5487737afb6753eeaed1bc75debbc7c1151d949e809aff814`

Later public M2DGR maintainer replies add useful GT recording provenance.

The maintainer describes GT as the pose of the Xsens 680G or Leica prism.
Separate predecessor evidence supplies the outdoor-Xsens scene-family mapping;
issue 62 alone does not map those reference sources to scene families.

The maintainer also states that:

- Xsens IMU information was used to generate GT;
- ROS hardware triggering for the Xsens path was attempted but unsuccessful;
- MT Manager was used;
- GT is an algorithmic IMU+RTK fusion result;
- timestamp differences were calibrated.

The public evidence still does not provide the timestamp-calibration method,
numerical value, sign convention, per-sequence/global scope, or a reproducible
mapping usable by the evaluator.

A later maintainer reply identifies `/data/imu` as the Xsens IMU result and
states that raw RTK was not recorded.

All ten RTK/INS-family trajectories in the already frozen training split were
checked directly:

- train RTK/INS bags checked: `10`
- `/data/imu` present: `0`
- `/data/imu` absent: `10`

This is explicitly a training-split observation, not a dataset-wide absence
claim. Confirmation-test trajectories were not inspected.

Current interpretation:

- outdoor GT described as Xsens 680G pose by author: TRUE
- Leica GT described as prism pose by author: TRUE
- Xsens IMU used for GT generation according to author: TRUE
- GT described as algorithmic IMU+RTK fusion: TRUE
- MT Manager recording author-supported: TRUE
- author reports timestamp differences calibrated: TRUE
- issue 62 alone maps Xsens/Leica to scene families: FALSE
- exact Xsens physical measurement origin verified: FALSE
- exact Leica prism center verified: FALSE
- timestamp-calibration method verified: FALSE
- timestamp-calibration numerical value verified: FALSE
- timestamp-calibration scope verified: FALSE
- author timing claim supports a single fixed evaluator offset: FALSE
- author timing claim supports an evaluator tolerance: FALSE
- author timing claim reproducible from released material: FALSE
- released train `/data/imu` available: FALSE
- GT timestamp physical-event semantics verified: FALSE
- GT timestamp timebase/export semantics verified: FALSE
- reference-to-estimator temporal association verified: FALSE
- reference interpolation authorized: FALSE
- nearest-neighbor association authorized: FALSE
- association tolerance supported: FALSE
- evaluation interval authorized: FALSE
- alignment selected: FALSE
- estimator scoring authorized: FALSE
- dataset calibration verified: FALSE
- synchronization verified: FALSE
- evaluation ready: FALSE

The issue snapshots are treated as later public maintainer provenance, not
contemporaneous runtime logs.

This checkpoint is additive. Evaluation Protocol V2 and all predecessor
physical/timing/calibration/split evidence remain byte-identical.


## M2DGR platform-geometry evidence findings

Permanent additive evidence:

`manifests/m2dgr_platform_geometry_evidence_v1.json`

Content SHA256:

`6886f60101055363d8aac710d66ebb3b6013226e743071dcc4d1051b5a2ff8e2`

File SHA256:

`e1ba372d38faf32107b2c23ed836ab8a78b783269bab7f89e20f542c57159882`

A hash-bound historical author platform drawing now provides qualitative
physical-layout evidence independent of trajectory outcomes.

The associated author page states:

- drawing units are centimeters;
- red arrows denote X;
- green arrows denote Y;
- blue arrows denote Z.

Relevant drawing labels are:

- `3`: LIDAR;
- `4`: GNSS-IMU;
- `5`: IMU;
- `6`: Antenna.

The drawing explicitly distinguishes GNSS-IMU `#4` from Antenna `#6`.

Explicit annotations include:

- LiDAR height annotation above the middle deck: `15 cm`;
- middle-deck width/depth: `58 cm` / `44 cm`;
- LiDAR center dimension from the left middle-deck boundary: `29 cm`;
- GNSS-IMU `#4` and LiDAR `#3` share the drawn dashed planar centerline;
- upper-platform width/depth: `70 cm` / `50 cm`;
- Antenna `#6` dimension from the left boundary: `42 cm`;
- Antenna `#6` centerline dimension from the top boundary: `25 cm`.

These are preserved as explicit author drawing annotations only.

They are not converted into a new sensor transform.

The `15 cm` drawing annotation is not declared equal to the published
Xsens-to-LiDAR candidate vertical component of `-16.824 cm`.

The drawn centerline is not promoted to an exact zero translation component.

The sensor-axis arrows are not promoted to a calibrated rotation matrix.

Antenna `#6` is not identified as the MTi-680G GNSS antenna or as a GNSS phase
center.

Current interpretation:

- historical author platform drawing hash verified: TRUE
- centimeter drawing units author-supported: TRUE
- axis-color semantics author-supported: TRUE
- GNSS-IMU and antenna are distinct labeled components: TRUE
- explicit LiDAR `15 cm` annotation present: TRUE
- explicit middle-deck `58 cm` / `44 cm` dimensions present: TRUE
- explicit LiDAR `29 cm` center dimension present: TRUE
- GNSS-IMU and LiDAR share drawn planar centerline: TRUE
- qualitative platform-layout support: TRUE
- drawing is independent physical calibration verification: FALSE
- exact Xsens physical measurement origin verified: FALSE
- Xsens-to-LiDAR candidate translation verified: FALSE
- Xsens-to-LiDAR candidate rotation verified: FALSE
- runtime Xsens GNSS lever arm verified: FALSE
- Antenna `#6` identified as MTi-680G GNSS antenna: FALSE
- GNSS antenna phase center verified: FALSE
- GNSS candidate-transform applicability verified: FALSE
- Leica prism reference point verified: FALSE
- Leica candidate-transform applicability verified: FALSE
- mocap body origin verified: FALSE
- GT timestamp physical-event semantics verified: FALSE
- GT timestamp export/timebase semantics verified: FALSE
- reference temporal association verified: FALSE
- fixed reference offset supported: FALSE
- interpolation authorized: FALSE
- nearest-neighbor association authorized: FALSE
- association tolerance supported: FALSE
- evaluation interval authorized: FALSE
- alignment selected: FALSE
- estimator scoring authorized: FALSE
- dataset calibration verified: FALSE
- synchronization verified: FALSE
- evaluation ready: FALSE

This checkpoint is additive. Evaluation Protocol V2 remains byte-identical.


## M2DGR indoor reference-origin semantics findings

Permanent additive evidence:

`manifests/m2dgr_indoor_reference_origin_semantics_evidence_v1.json`

Content SHA256:

`a2044a4ca875618210843bc42ec0eedad0bc4026ebe258099b30cd6733153cd4`

File SHA256:

`1d08a9c164857c827016545e55d7a495f10557dba7e596d8c2fc071d30cd895d`

Public maintainer and manufacturer evidence now constrains the two indoor
reference families more clearly.

Leica:

- maintainer states Leica tracks 3D position rather than 6D pose: TRUE
- maintainer identifies the Leica prism as a GT reference object: TRUE
- Leica released zero quaternion columns are physical rotation: FALSE
- generic Leica reflector standing-axis semantics documented: TRUE
- exact M2DGR prism reference point verified: FALSE
- M2DGR reflector model verified: FALSE
- M2DGR prism constant verified: FALSE
- M2DGR reflector mount/standing-axis configuration verified: FALSE
- Leica candidate-transform applicability verified: FALSE

A direct public question asking for the Leica GT to HandsFree IMU extrinsic
(issue 84) has no recovered maintainer answer. That absence is not treated as
proof that the extrinsic does not exist.

Mocap:

- Room/Roomdark reference comes from mocap according to maintainer: TRUE
- maintainer acknowledges tracking loss can cause abrupt quaternion changes:
  TRUE
- maintainer recommends filtering: TRUE
- exact filter algorithm specified: FALSE
- filter threshold/window specified: FALSE
- prospective sample-exclusion rule specified: FALSE
- mocap tracked-body origin verified: FALSE
- mocap marker pattern recovered: FALSE
- mocap volume origin recovered: FALSE
- mocap-to-LiDAR physical transform verified: FALSE

Vicon manufacturer documentation establishes that tracked-object origin,
tracked-object alignment, and capture-volume origin can be configurable.

The snapshotted Vicon guide is not asserted to be the exact M2DGR runtime
software version or configuration.

No M2DGR Vicon `.vsk`, `.xcp`, marker-pattern definition, tracked-object origin,
or volume-origin configuration was recovered from the inspected public/local
source material.

Current protocol interpretation remains:

- temporal association verified: FALSE
- interpolation authorized: FALSE
- nearest-neighbor pose association authorized: FALSE
- association tolerance supported: FALSE
- evaluation interval authorized: FALSE
- alignment selected: FALSE
- estimator scoring authorized: FALSE
- dataset calibration verified: FALSE
- synchronization verified: FALSE
- evaluation ready: FALSE

No confirmation-test trajectory was inspected or used for selection.

This checkpoint is additive. Evaluation Protocol V2 remains byte-identical.


## M2DGR reference-family protocol-boundary findings

Permanent additive evidence:

`manifests/m2dgr_reference_family_protocol_boundary_evidence_v1.json`

Content SHA256:

`87d48c97aeea22cbcba09bda0dfd1e577c0eef9084435cdd44dfc66146b1ec7c`

File SHA256:

`7d4cc9e1f7433ddd6b88b391687ca14a245ebf80877c4f4290fc3192ab7494cd`

The frozen 36-trajectory corpus decomposes mechanically into:

- RTK/INS: 16 trajectories
- Leica: 11 trajectories
- mocap: 9 trajectories

Frozen split counts by reference family:

- RTK/INS: train 10, validation/calibration 3, confirmation-test 3
- Leica: train 7, validation/calibration 2, confirmation-test 2
- mocap: train 5, validation/calibration 2, confirmation-test 2

Structural dimension status:

- RTK/INS translation: present
- RTK/INS rotation: present
- Leica translation: present
- Leica rotation: unsupported
- mocap translation: present
- mocap rotation: present

Audited structural invalid samples:

- RTK/INS translation: 0
- RTK/INS rotation: 0
- Leica translation: 0
- mocap translation: 0
- mocap rotation: 1274 invalid quaternion samples
- mocap trajectories with invalid rotation samples: 9 of 9

These structural observations do not establish continuous-time coverage or
physical evaluation readiness.

Current family/dimension scoring boundary under frozen Protocol V2:

- RTK/INS translation scoring admissible: FALSE
- RTK/INS rotation scoring admissible: FALSE
- Leica translation-only scoring admissible: FALSE
- Leica rotation scoring admissible: FALSE
- mocap translation-only scoring admissible: FALSE
- mocap rotation scoring admissible: FALSE

Common blockers remain:

- reference frame semantics verified: FALSE
- reference-frame transform verified: FALSE
- continuous reference coverage verified: FALSE
- temporal association method selected: FALSE
- association tolerance frozen: FALSE
- fixed reference offset selected: FALSE
- interpolation method selected: FALSE
- evaluation interval selected: FALSE
- alignment mode selected: FALSE
- dataset calibration independently verified: FALSE
- synchronization independently verified: FALSE
- metric computation authorized: FALSE
- trajectory scoring authorized: FALSE
- estimator scoring authorized: FALSE
- evaluation ready: FALSE

Family-specific blockers remain:

RTK/INS:
- exact released Xsens physical origin unresolved
- runtime GNSS lever arm unresolved
- Xsens/GNSS candidate-transform applicability unresolved

Leica:
- exact released prism reference point unresolved
- reflector model/prism constant/mount unresolved
- Leica candidate-transform applicability unresolved
- rotation reference unsupported

Mocap:
- tracked-body origin unresolved
- marker/local-axis configuration unresolved
- mocap-to-LiDAR/estimator relation unresolved
- invalid quaternion samples occur in every mocap trajectory
- no scientifically specified filtering/exclusion rule

Allowed non-scoring work remains:

- structural inventory
- provenance analysis
- metric-family schema definition
- dimension-gating schema definition
- documentation of unresolved physical requirements

No confirmation-test raw trajectory is inspected by this checkpoint.

No confirmation-test outcome is used for protocol selection.

Protocol V2 remains byte-identical.

This checkpoint does not select Protocol V3 and does not authorize ATE, RPE,
or estimator scoring.


## M2DGR fail-closed evaluator architecture implementation

After the permanent reference-family protocol-boundary checkpoint, evaluator
implementation may proceed only in non-scoring, fail-closed form.

Implementation:

`src/trust_robot/m2dgr_evaluator_gate.py`

Tests:

`tests/trust_robot/test_m2dgr_evaluator_gate.py`

Audit:

`docs/audits/trust_robot/M2DGR_EVALUATOR_FAIL_CLOSED_ARCHITECTURE_V1.md`

The implementation provides:

- Protocol V2 metric-family definitions;
- reference-family/dimension gate inspection;
- permanent boundary-artifact validation;
- explicit fail-closed metric-execution guards;
- explicit fail-closed estimator-scoring guards.

It intentionally does not implement:

- trajectory association;
- interpolation;
- time-offset estimation;
- evaluation-interval construction;
- frame alignment;
- ATE computation;
- RPE computation;
- aggregation;
- trajectory scoring;
- estimator scoring.

Current frozen family/dimension state remains:

- RTK/INS translation structurally present: TRUE
- RTK/INS rotation structurally present: TRUE
- Leica translation structurally present: TRUE
- Leica rotation structurally present: FALSE
- mocap translation structurally present: TRUE
- mocap rotation structurally present: TRUE
- mocap audited invalid quaternion samples: 1274

All current family/metric execution requests must fail closed.

Protocol V2 remains byte-identical.

No raw confirmation-test trajectory is inspected.

No confirmation-test outcome is used for implementation parameter selection.

No physical-evaluation authorization is changed.


## M2DGR non-executable evaluation-plan implementation

The promoted fail-closed evaluator gate is extended with deterministic
provenance-record and non-executable evaluation-plan objects.

Implementation:

`src/trust_robot/m2dgr_evaluation_plan.py`

Tests:

`tests/trust_robot/test_m2dgr_evaluation_plan.py`

Audit:

`docs/audits/trust_robot/M2DGR_NONEXECUTABLE_EVALUATION_PLAN_V1.md`

The plan binds repository-relative identities and SHA256 values for:

- Evaluation Protocol V2
- permanent reference-family protocol-boundary evidence
- frozen split manifest
- split-freeze evidence
- promoted fail-closed evaluator-gate implementation

The plan records Protocol V2 required-provenance field names but does not invent
future per-trajectory values.

Current plan state remains:

- association method: unselected
- association tolerance: null
- fixed reference offset: null
- interpolation method: unselected
- evaluation interval: unselected
- alignment mode: unselected
- metric computation authorized: FALSE
- trajectory scoring authorized: FALSE
- estimator scoring authorized: FALSE
- evaluation ready: FALSE
- per-trajectory provenance populated: FALSE
- estimator trajectory bound: FALSE
- reference trajectory bound: FALSE
- raw confirmation-test data accessed: FALSE
- confirmation-test used for selection: FALSE

The plan contains only provenance, requirements, blockers, and gate state.

It contains no trajectory samples and performs no trajectory mathematics.

Protocol V2 remains byte-identical.

The permanent reference-family boundary remains byte-identical.


## M2DGR evaluation readiness diagnostics implementation

The local non-executable evaluation-plan phase now also includes:

`src/trust_robot/m2dgr_evaluation_readiness.py`

and:

`tests/trust_robot/test_m2dgr_evaluation_readiness.py`

The plan layer now supports deterministic immutable JSON persistence and
validated loading.

The readiness layer provides:

- required-provenance field-name completeness reporting;
- unknown/missing provenance-field reporting;
- global execution-readiness diagnostics;
- explicit fail-closed execution requests.

The provenance diagnostic accepts field names only and does not accept or infer
physical/evaluation parameter values.

Even if all 17 required provenance field names are present:

- provenance semantics verified: FALSE
- executable metric entries: 0
- scoreable metric entries: 0
- evaluation ready: FALSE

This does not change Protocol V2, the permanent family boundary, association,
alignment, calibration, synchronization, or scoring authorization.


## M2DGR metadata-only evaluation inspection interface

The current local evaluator-plumbing phase additionally implements:

`src/trust_robot/m2dgr_evaluation_request.py`

with tests:

`tests/trust_robot/test_m2dgr_evaluation_request.py`

and a local diagnostic CLI:

`scripts/trust_robot/inspect_m2dgr_evaluation_readiness.py`

An inspection request accepts only:

- reference family
- metric family
- names of provenance fields reported present

It does not accept trajectory samples, trajectory paths, timestamps, timing
offsets, tolerances, transforms, alignment parameters, or metric values.

The inspection report exposes the existing frozen gate state and blockers.

It cannot authorize execution.

Current expected result for every defined family/metric pair remains:

- metric enabled: FALSE
- execution authorized: FALSE
- scoring authorized: FALSE
- evaluation ready: FALSE

Leica rotation additionally remains structurally unsupported.

Complete presence of all 17 provenance field names still does not establish
provenance semantic validity and does not change readiness.

The CLI is local diagnostic plumbing only and performs no trajectory
mathematics.


## M2DGR local evaluator-plumbing phase consolidation

The current unpromoted local evaluator-plumbing phase now includes an
end-to-end integration suite:

`tests/trust_robot/test_m2dgr_evaluator_plumbing_integration.py`

The integration layer verifies the complete local chain:

- Protocol V2
- permanent reference-family boundary
- fail-closed evaluator gate
- non-executable plan
- immutable plan persistence
- provenance completeness reporting
- readiness reporting
- metadata-only family/metric inspection

All twelve family/metric pairs remain blocked both with zero provenance field
names and with all seventeen required field names present.

Complete field-name presence remains schema completeness only; it does not
establish semantic validity.

A ten-case tamper matrix is required to remain fail-closed.

Deterministic local phase artifacts are generated only under the dataset audit
staging directory.

No estimator/reference trajectory samples are included.

No association, tolerance, offset, interval, alignment, ATE, RPE, aggregation,
trajectory scoring, or estimator scoring is selected or executed.

This evaluator-plumbing phase was promoted as checkpoint `0aabeca605e69aa56aa5dffc6ce70f76350dc80b`.


## Phase-2 clean localization backbone implementation

Phase-2 implementation has started.

Objective:

**Fixed clean localization/state-estimation backbone.**

Exit evidence remains:

**Reproducible clean 6-DoF baseline.**

Current implementation:

`src/trust_robot/clean_backbone.py`

Tests:

`tests/trust_robot/test_clean_backbone.py`

Audit:

`docs/audits/trust_robot/TRUST_ROBOT_PHASE2_CLEAN_BACKBONE_KERNEL_V1.md`

The implemented kernel is a deterministic SE(3) pose-chain backend with an
explicit transform convention:

`prev_body_T_current_body`

It provides:

- explicit world/body frame identifiers;
- one fixed relative-pose source per configuration;
- deterministic rigid-transform composition and inversion;
- strict monotonically increasing state timestamps;
- deterministic 6-DoF state propagation;
- deterministic run serialization/content identity.

The inherited `src/imu_reliability` package remains historical/reference code
and is not silently reclassified as the Phase-2 localization backbone.

This checkpoint does **not** yet satisfy Phase-2 exit evidence.

Still required before Phase 2 can close:

- select and implement/adopt one fixed clean sensor frontend without using
  confirmation-test outcomes;
- connect that frontend to the SE(3) backbone;
- execute a reproducible clean real-data trajectory run;
- preserve exact estimator input/frame/calibration/timing provenance.

The current clean-backbone kernel does not use reference trajectories and does
not alter the blocked M2DGR evaluation protocol.

It performs no health weighting, corruption injection, ATE, RPE, alignment,
trajectory scoring, or estimator scoring.


## Phase-2 LiDAR frontend candidate

The TRAIN-only structural preflight supports a first real clean frontend
candidate based on Velodyne LiDAR.

Across all 22 frozen TRAIN trajectories:

- `/velodyne_points` coverage: 22/22
- message type: `sensor_msgs/msg/PointCloud2`
- frame ID: `velodyne` on 22/22
- field names: `x,y,z,intensity,ring,time`

The candidate is selected on structural/engineering grounds only.

No reference-error comparison or estimator scoring was used.

Current implementation:

`src/trust_robot/lidar_frontend.py`

Frozen candidate contract:

`configs/trust_robot/phase2_clean_lidar_frontend_candidate_v1.json`

Tests:

`tests/trust_robot/test_lidar_frontend.py`

Mechanical smoke script:

`scripts/trust_robot/run_phase2_lidar_pair_smoke.py`

The candidate registers every current scan directly to the previous scan in the
Velodyne frame using exact nearest-neighbor fixed-point Kabsch registration.

It deliberately uses no:

- voxel-size parameter;
- correspondence-distance threshold;
- outlier threshold;
- keyframe threshold;
- numeric convergence tolerance;
- performance-selected parameter.

The trajectory therefore remains `world_T_velodyne` with the first LiDAR scan
as the arbitrary local origin.

No LiDAR-to-base transform is assumed.

PointCloud2 header stamps are used only as ordering/state timestamps. Their
physical scan-reference semantics remain unverified. Per-point time is not
used and deskew is not performed.

Phase-2 exit evidence remains unsatisfied pending reproducible real-data
trajectory execution and review.


## Phase-2 detached full-TRAIN LiDAR execution

A fail-closed full-TRAIN execution runner now exists:

`scripts/trust_robot/run_phase2_lidar_train_v1.py`

with artifact helpers:

`src/trust_robot/lidar_train_run.py`

and tests:

`tests/trust_robot/test_lidar_train_run.py`

The runner is restricted to the 22 already-frozen TRAIN trajectories and reads
only `/velodyne_points`.

It executes trajectories sequentially and writes persistent dataset-local
progress and trajectory artifacts.

It performs no automatic scan skipping, trajectory skipping, residual
thresholding, registration timeout, iteration cap, or exclusion rule.

Any input or registration failure terminates the run fail-closed.

The execution does not use reference trajectories or confirmation-test data and
does not compute ATE/RPE or estimator scores.

The full-TRAIN execution is a long workstation job and is launched detached
with a persistent PID and log.

Phase-2 exit evidence remains unsatisfied until the resulting real-data
trajectories are reviewed and the remaining timing/deskew limitations are
handled explicitly.


## Phase-2 clean LiDAR baseline freeze

Phase 2 is locally complete.

Objective:

**Fixed clean localization/state-estimation backbone.**

Exit evidence:

**Reproducible clean 6-DoF baseline.**

Current exit-evidence status:

**SATISFIED.**

Frozen baseline identity:

`trust_robot_phase2_clean_lidar_baseline_v1`

Freeze manifest:

`manifests/trust_robot_phase2_clean_lidar_baseline_freeze_v1.json`

Closure audit:

`docs/audits/trust_robot/TRUST_ROBOT_PHASE2_CLEAN_LIDAR_BASELINE_FREEZE_V1.md`

The real-data execution completed all 22 frozen TRAIN trajectories:

- 91,014 Velodyne scans;
- 90,992 consecutive-scan 6-DoF increments;
- zero skipped scans;
- zero skipped trajectories;
- zero fail-closed execution events.

Every Velodyne scan reported by bag metadata was consumed exactly once by the
frozen execution.

No reference trajectory or confirmation-test data were used.

No ground-truth association, alignment, ATE, RPE, trajectory scoring, or
estimator scoring was performed.

The baseline remains in the `velodyne` frame with the first LiDAR scan as its
local trajectory origin.

The PointCloud2 header timestamp is used only for state ordering/labeling.
Its physical scan-reference meaning remains unverified.

Per-point timing is not used and deskew is not performed.

Those limitations are part of the frozen Phase-2 baseline definition. They do
not constitute synchronization evidence and do not authorize timing-sensitive
evaluation or multi-sensor fusion assumptions.

The M2DGR evaluation protocol remains blocked and unchanged.

Phase-2 closure is frozen. The Git commit containing this section and the
Phase-2 freeze manifest is the authoritative repository promotion checkpoint.


## Phase-3 deterministic corruption kernel

Phase 3 is now under local implementation.

Objective:

**Multimodal fault/degradation/attack taxonomy and corruption engine.**

Exit evidence:

**Deterministic paired corruption framework.**

Current exit-evidence status:

**SATISFIED by the Phase-3 framework closure manifest.**

New local candidate taxonomy:

`configs/trust_robot/phase3_corruption_taxonomy_candidate_v1.json`

New native corruption kernel:

`src/trust_robot/corruption.py`

Tests:

`tests/trust_robot/test_corruption.py`

Audit:

`docs/audits/trust_robot/TRUST_ROBOT_PHASE3_CORRUPTION_KERNEL_V1.md`

The adoption audit found useful historical design concepts in
`src/imu_reliability/injection`, including immutable paired clean/corrupt
streams, deterministic SHA identities, no-op rejection, origin mapping, and
immutable manifests.

Those concepts are reimplemented behind a new TRUST-ROBOT-native contract.

The new kernel does not import `imu_reliability` and does not inherit its
historical IMU/HAR corruption severity grids, seed grids, thresholds, or
final-test outcomes.

The V1 native kernel provides deterministic structural corruption mechanisms:

- `EVENT_GAP`;
- `EVENT_REPEAT`;
- `TIMESTAMP_STEP_SHIFT`.

The kernel is modality-labelled and supports arbitrary numerical event payload
shapes so future adapters can represent IMU vectors, camera images, LiDAR point
clouds, depth data, and other modalities without forcing every modality into a
fixed two-dimensional sample matrix.

No severity grid, fault magnitude, attack budget, stochastic-noise parameter,
dropout probability, drift rate, or jitter distribution is selected by this
kernel.

Synthetic mechanism truth remains explicitly separate from physical/runtime
causal evidence.

No real M2DGR corruption has yet been generated.

No confirmation-test data are used.

Phase-2 remains frozen and unchanged.

M2DGR evaluation readiness remains false and no ATE/RPE is authorized.


## Phase-3 LiDAR clean EventStream adapter

A native clean adapter now connects frozen Phase-2 M2DGR Velodyne input
semantics to the Phase-3 generic paired-corruption architecture.

Implementation:

`src/trust_robot/lidar_corruption_adapter.py`

Tests:

`tests/trust_robot/test_lidar_corruption_adapter.py`

Real TRAIN mechanical smoke:

`scripts/trust_robot/run_phase3_lidar_clean_adapter_smoke.py`

Audit:

`docs/audits/trust_robot/TRUST_ROBOT_PHASE3_LIDAR_CLEAN_ADAPTER_V1.md`

The adapter reuses the exact frozen Phase-2 functions:

- `decode_m2dgr_velodyne_xyz`;
- `pointcloud_header_stamp_ns`;
- `pointcloud_field_descriptors`.

It does not duplicate PointCloud2 XYZ parsing.

One PointCloud2 scan becomes one LiDAR `EventStream` event whose payload is
the exact Phase-2 decoded contiguous `float64` XYZ array.

A deterministic adapter receipt preserves structural PointCloud2 metadata,
raw PointCloud2 data hashes, decoded XYZ hashes, and the resulting clean
EventStream fingerprint.

Raw PointCloud2 provenance bytes are accessed through the buffer protocol,
matching the byte-buffer semantics already accepted by the frozen decoder.

The first three `/velodyne_points` messages from frozen TRAIN `Circle_01`
serve only as a clean mechanical reproducibility smoke.

No corruption is applied in that proof.

The PointCloud2 header timestamp remains only an event/state label. Its
physical scan-reference meaning is still unverified.

Per-point time is not used and no deskew is performed.

No reference or confirmation-test data are accessed.

This layer alone did not satisfy Phase-3 exit evidence; the final Phase-3 framework closure manifest records phase-level satisfaction.


## Phase-3 first real controlled LiDAR corruption

The Phase-3 deterministic corruption framework has now produced its first real
TRAIN clean/corrupt pair.

Prospective configuration:

`configs/trust_robot/phase3_lidar_event_gap_real_smoke_v1.json`

Runner:

`scripts/trust_robot/run_phase3_lidar_event_gap_real_smoke_v1.py`

Tests:

`tests/trust_robot/test_lidar_event_gap_real_smoke.py`

Audit:

`docs/audits/trust_robot/TRUST_ROBOT_PHASE3_LIDAR_EVENT_GAP_REAL_SMOKE_V1.md`

The real source is the already-inspected first three `/velodyne_points`
messages from TRAIN `Circle_01`.

The first corruption is `EVENT_GAP` removing clean event index 1.

For the fixed three-event smoke slice, index 1 is the only internal event.
The one-event gap is the minimal non-zero discrete mechanism instance and is
used only to prove real-data corruption plumbing.

It is not a selected benchmark severity and no severity grid has been chosen.

The corrupted EventStream retains clean-origin indices `[0, 2]`.

The source PointCloud2 bytes and clean EventStream remain unchanged.

Repeated application of the same frozen corruption specification reproduces
the same corrupted EventStream and corruption manifest.

Real TRAIN data are used, but no reference trajectory or confirmation-test data
are used.

The estimator is not executed in this smoke.

No ground-truth association, alignment, ATE, RPE, trajectory scoring, or
estimator scoring is performed.

This layer alone did not satisfy Phase-3 exit evidence; the final Phase-3 framework closure manifest records phase-level satisfaction.


## Phase-3 paired clean/corrupt frozen estimator registration

The first real paired clean/corrupt LiDAR EventStreams now pass through the
same frozen Phase-2 registration kernel.

Contract:

`configs/trust_robot/phase3_lidar_paired_estimator_registration_v1.json`

Implementation:

`src/trust_robot/lidar_corruption_estimator.py`

Runner:

`scripts/trust_robot/run_phase3_lidar_paired_estimator_registration_v1.py`

Tests:

`tests/trust_robot/test_lidar_corruption_estimator.py`

Audit:

`docs/audits/trust_robot/TRUST_ROBOT_PHASE3_LIDAR_PAIRED_ESTIMATOR_REGISTRATION_V1.md`

The frozen Phase-2 function used is:

`register_current_scan_to_previous`

The clean three-event stream reaches the registration kernel through origin
pairs:

- `[0, 1]`
- `[1, 2]`

The paired `EVENT_GAP` stream reaches the same kernel through:

- `[0, 2]`

This proves the controlled corruption changes estimator input topology as
intended.

Registration poses and internal diagnostics are execution evidence only.
They are not localization accuracy scores and may not retroactively modify the
frozen corruption specification.

No clean-versus-corrupt error metric is calculated.

No reference or confirmation-test data are used.

No association, alignment, ATE, RPE, trajectory scoring, estimator scoring,
severity selection, or attack-budget selection is performed.

This layer alone did not satisfy Phase-3 exit evidence; the final Phase-3 framework closure manifest records phase-level satisfaction.


## Phase-3 prospective corruption selection policy

Phase 3 now has an explicit prospective policy controlling how corruption
instances may be selected.

Policy:

`configs/trust_robot/phase3_corruption_selection_policy_v1.json`

Implementation:

`src/trust_robot/corruption_selection.py`

Tests:

`tests/trust_robot/test_corruption_selection.py`

Audit:

`docs/audits/trust_robot/TRUST_ROBOT_PHASE3_CORRUPTION_SELECTION_POLICY_V1.md`

Every future controlled corruption must bind both target selection and
magnitude/condition selection before execution.

The corruption engine cannot invent missing event locations, durations,
magnitudes, delays, noise levels, or attack budgets.

Estimator outputs, registration diagnostics, reference trajectories,
ground-truth errors, validation performance metrics, confirmation-test
outcomes, ATE, RPE, and final scores are forbidden as inputs for selecting the
corruption experimental condition.

The existing real TRAIN `EVENT_GAP` smoke is bound to the policy as a
prospectively declared mechanical instance.

Its observed registration outputs cannot retroactively change the corruption
specification.

No new severity or attack budget is selected by this policy.

No reference or confirmation-test data are used.

No evaluation authorization changes.

The subsequent comprehensive Phase-3 closure review found the framework exit
evidence satisfied; the Phase-3 freeze manifest is the authoritative
phase-level closure record.


## Phase-3 deterministic paired corruption framework closure

Phase 3 is complete and frozen.

Objective:

**Multimodal fault/degradation/attack taxonomy and corruption engine.**

Exit evidence:

**Deterministic paired corruption framework.**

Current phase-level status:

**SATISFIED.**

Frozen framework identity:

`trust_robot_phase3_deterministic_paired_corruption_framework_v1`

Authoritative freeze manifest:

`manifests/trust_robot_phase3_deterministic_paired_corruption_framework_freeze_v1.json`

Closure audit:

`docs/audits/trust_robot/TRUST_ROBOT_PHASE3_DETERMINISTIC_PAIRED_CORRUPTION_FRAMEWORK_FREEZE_V1.md`

The framework provides immutable multimodal event streams, explicit paired
clean/corrupt outputs, deterministic SHA specification and injection
identities, origin-index provenance, no-op rejection, immutable manifests and
prospective corruption-selection provenance.

Generic structural mechanisms currently implemented are:

- `EVENT_GAP`;
- `EVENT_REPEAT`;
- `TIMESTAMP_STEP_SHIFT`.

The generic framework is modality-labelled across camera, depth, GNSS, IMU,
LiDAR, proprioception, wheel odometry and other numerical event streams.

The real-data integration proof is currently LiDAR.

A prospectively frozen TRAIN `Circle_01` `EVENT_GAP` instance reproduced
exactly and preserved clean-source immutability.

The paired clean/corrupt EventStreams also reproduced exactly through the same
frozen Phase-2 registration kernel.

Phase-3 closure does not claim a complete modality-specific physical fault or
attack library.

Future modality-specific corruption models require their own prospective
specifications.

No reference or confirmation-test data were used.

No association, alignment, ATE, RPE, trajectory scoring, estimator scoring or
clean-versus-corrupt localization accuracy metric was performed.

Synchronization remains unverified.

M2DGR evaluation readiness remains false.

The existing component artifacts retain their historical pre-closure status
fields; the Phase-3 freeze manifest is the authoritative aggregate
phase-level satisfaction record.

The Git commit containing this closure section and freeze manifest is the
authoritative Phase-3 repository promotion checkpoint.


## Phase-4 first native diagnostic feature extractor

Phase 4 is now active.

Objective:

**Per-modality diagnostics.**

Required exit evidence:

**Validated diagnostic feature extraction.**

Candidate contract:

`configs/trust_robot/phase4_lidar_registration_diagnostics_candidate_v1.json`

Implementation:

`src/trust_robot/diagnostics.py`

Tests:

`tests/trust_robot/test_diagnostics.py`

Audit:

`docs/audits/trust_robot/TRUST_ROBOT_PHASE4_LIDAR_REGISTRATION_DIAGNOSTICS_V1.md`

The first native extractor consumes the frozen Phase-2
`LidarRegistrationDiagnostics` object without modifying or rerunning the
registration algorithm.

It extracts exactly five descriptive numeric observables:

- source point count;
- target point count;
- fixed-point iteration count;
- final correspondence count;
- final nearest-neighbor RMSE in metres.

The frozen convergence rule, correspondence-rejection flag and
voxel-downsampling flag are retained as categorical metadata.

No inherited `src/imu_reliability` runtime decision or threshold machinery is
a dependency of this implementation.

Historical threshold values remain inventory evidence only.

No diagnostic normalization, aggregation, thresholding, health classification,
fault classification, reliability score or localization-accuracy score is
produced.

No reference or confirmation-test data are used.

No ATE/RPE or estimator scoring is performed.

Phase-4 exit evidence remains **NOT YET SATISFIED**. This first contract must
still be validated on the frozen real-data diagnostic path before any
Phase-4 closure decision.


## Phase-4 persistent real TRAIN diagnostic artifacts

The native Phase-4 LiDAR diagnostic extractor has now been applied to the
complete already-frozen Phase-2 TRAIN registration artifact set.

Persistent extraction contract:

`configs/trust_robot/phase4_lidar_train_diagnostic_artifacts_v1.json`

Artifact adapter:

`src/trust_robot/diagnostic_artifacts.py`

Runner:

`scripts/trust_robot/run_phase4_lidar_train_diagnostics_v1.py`

Tests:

`tests/trust_robot/test_diagnostic_artifacts.py`

Audit:

`docs/audits/trust_robot/TRUST_ROBOT_PHASE4_LIDAR_TRAIN_DIAGNOSTIC_ARTIFACTS_V1.md`

The source contains 22 TRAIN trajectories and 90,992 frozen consecutive LiDAR
registration records.

Every source `relative_pose` record contains exactly one diagnostic mapping at
top-level `diagnostics`.

All 90,992 records were converted into deterministic persistent feature
records using the five-value identity/direct extractor.

The persistent extraction reproduces the preflight provenance identity:

`42658bdb5739200f02dc1397f753b78ca60eb22f6bc5d913e42c6a208fc61020`

This digest is provenance evidence only and is not a score or threshold.

The extraction did not open ROS bags, decode new PointCloud2 messages or rerun
the estimator.

No descriptive statistics, normalization, temporal aggregation, thresholding,
health state, fault label, reliability score or localization-accuracy score
was produced.

No reference or confirmation-test data were used.

No ATE/RPE or estimator scoring was performed.

Phase-4 exit evidence remains **NOT YET SATISFIED** pending validation against
the already-frozen paired clean/corrupt registration evidence and a final
Phase-4 closure review.


## Phase-4 paired clean/corrupt diagnostic extraction

The native LiDAR diagnostic extractor has now been validated on both sides of
the already-frozen real TRAIN Phase-3 clean/corrupt registration receipt.

Contract:

`configs/trust_robot/phase4_lidar_paired_diagnostics_v1.json`

Adapter:

`src/trust_robot/paired_diagnostic_artifacts.py`

Runner:

`scripts/trust_robot/run_phase4_lidar_paired_diagnostics_v1.py`

Tests:

`tests/trust_robot/test_paired_diagnostic_artifacts.py`

Audit:

`docs/audits/trust_robot/TRUST_ROBOT_PHASE4_LIDAR_PAIRED_DIAGNOSTICS_V1.md`

The frozen source contains clean registration origin pairs:

- `[0, 1]`
- `[1, 2]`

and paired EVENT_GAP registration origin pair:

- `[0, 2]`

The same five-feature identity/direct extractor is used on all three
registration diagnostics.

No estimator or corruption is rerun.

No clean-versus-corrupt numeric difference, descriptive statistic, threshold,
health state, fault state, reliability score or accuracy score is computed.

This complements the already-materialized validation across all 90,992 frozen
clean TRAIN registration diagnostics.

No reference or confirmation-test data are used.

No ATE/RPE or estimator scoring is performed.

The subsequent Phase-4 closure-scope review found the required exit evidence
satisfied for the current frozen LiDAR estimator scope. The aggregate Phase-4
freeze manifest is the authoritative phase-level closure record.


## Phase-4 validated diagnostic feature extraction closure

Phase 4 is complete for the current frozen estimator scope.

Objective:

**Per-modality diagnostics.**

Required exit evidence:

**Validated diagnostic feature extraction.**

Current phase-level status:

**SATISFIED FOR CURRENT FROZEN ESTIMATOR SCOPE.**

Frozen diagnostic identity:

`trust_robot_phase4_lidar_validated_diagnostic_feature_extraction_v1`

Authoritative freeze manifest:

`manifests/trust_robot_phase4_validated_diagnostic_feature_extraction_freeze_v1.json`

Closure audit:

`docs/audits/trust_robot/TRUST_ROBOT_PHASE4_VALIDATED_DIAGNOSTIC_FEATURE_EXTRACTION_FREEZE_V1.md`

The frozen Phase-2 estimator path is LiDAR.

The Phase-4 extractor preserves exactly five registration observables:

- source point count;
- target point count;
- fixed-point iteration count;
- final correspondence count;
- final nearest-neighbor RMSE in metres.

Validation covers all 90,992 frozen TRAIN registration diagnostics across all
22 TRAIN trajectories.

Persistent Phase-4 feature artifacts are stored under
`features/<trajectory>.jsonl` and are individually SHA-bound to their frozen
Phase-2 source trajectory artifacts.

The same extractor is also validated on the frozen Phase-3 clean/corrupt
EVENT_GAP registration paths.

No normalization, temporal aggregation, thresholding, health classification,
fault classification, reliability scoring or localization-accuracy scoring is
performed.

This closure does not claim a complete diagnostic library for every sensor
modality.

Future non-LiDAR estimator paths require their own validated diagnostic
extraction before entering health modelling or health-aware estimator logic.

The healthy/degraded/unusable classifier remains Phase 5.

No reference or confirmation-test data are used.

No association, alignment, ATE, RPE, trajectory scoring or estimator scoring
is performed.

Synchronization remains unverified.

M2DGR evaluation readiness remains false.

Existing Phase-4 component configs retain their historical pre-closure status
fields. The aggregate Phase-4 freeze manifest is the authoritative phase-level
closure record.

The Git commit containing this closure and freeze manifest will be the
authoritative Phase-4 promotion checkpoint.


## Phase-5 prospective three-state health semantics

Phase 5 is the active implementation frontier.

Objective:

**Three-state modality-health model.**

Required exit evidence:

**Healthy/degraded/unusable classifier.**

The Phase-5 frontier audit found no existing native TRUST-ROBOT three-state
health vocabulary or classifier suitable for adoption.

The inherited `imu_reliability` runtime trust-state and numeric policy are not
adopted as TRUST-ROBOT defaults.

A new prospective semantic contract now defines exactly three states:

- `healthy`;
- `degraded`;
- `unusable`.

These states are semantic health categories, not localization-accuracy scores,
diagnostic thresholds, reliability scores, factor weights or suppression
commands.

Future real-data health labels require explicit prospective provenance
independent of final estimator scoring and confirmation-test outcomes.

Clean-branch identity alone is not a healthy label.

Synthetic corruption identity alone is not a degraded or unusable label.

A diagnostic value or diagnostic threshold alone is not a health label.

No existing Phase-4 diagnostic record has been health-labelled.

No classifier structure, training-label source, diagnostic threshold, health
threshold, model or calibration has been selected.

The frozen Phase-4 five-feature LiDAR diagnostic contract is unchanged.

No reference or confirmation-test data are used.

No association, alignment, ATE, RPE or estimator scoring is performed.

Phase-5 exit evidence remains **NOT YET SATISFIED**.

Current TRUST-ROBOT regression after this semantic layer:

**378 / 378 PASS.**


## Phase-5 prospective health-supervision source protocol

The prospective Phase-5 semantic contract remains label-free.

A subsequent read-only provenance audit found:

- runtime health-label provenance instances: 0;
- real healthy/degraded/unusable assignments: 0;
- accepted health-label supervision sources: 0.

A native supervision-source protocol now defines what any future candidate
source must provide before acceptance can even be considered.

Required candidate evidence includes explicit source identity, modality,
measurement role, source kind, evidence description, supported health states
and documented state criteria.

Candidate evidence must be prospectively declared, grounded in the modality's
measurement role, independent of final estimator scoring and independent of
confirmation-test outcomes.

Clean identity alone is insufficient.

Corruption identity alone is insufficient.

A diagnostic value or threshold alone is insufficient.

Reference metrics and ATE/RPE are prohibited health-label bases.

Historical `imu_reliability` policy remains non-adopted.

A classifier's own output cannot serve as its supervision.

Passing the candidate-source validator does not accept a source and does not
assign a label.

The current accepted supervision-source count remains **0**.

The current real health-label count remains **0**.

No classifier structure, feature selection, threshold, model or calibration
has been selected.

The frozen Phase-4 five-feature LiDAR diagnostic contract is unchanged.

Phase-5 exit evidence remains **NOT YET SATISFIED**.

Current TRUST-ROBOT regression after this protocol layer:

**378 / 378 PASS.**


## Phase-5 prospective controlled measurement-availability supervision

The frozen LiDAR frontend has an explicitly audited structural
measurement-role boundary:

- XYZ shape `(N,3)`;
- finite values;
- at least 3 points.

The `N >= 3` rule is algorithmic structural admissibility and is **not** a
health threshold.

Phase-4 remains exactly five features.

Missing modality evidence may not be represented by a fabricated zero feature
vector.

A prospective controlled measurement-availability supervision protocol now
defines three experimental evidence relations:

- `full`: exact preservation of independently verified nominal source
  measurement evidence;
- `partial`: independently verified removal of a nonempty strict proper
  subset while retained evidence remains structurally admissible;
- `absent`: independently verified complete measurement absence.

If a future supervision source is separately reviewed and accepted, these
relations prospectively map to:

- `full` -> `healthy`;
- `partial` -> `degraded`;
- `absent` -> `unusable`.

Independent baseline nominality is mandatory.

Therefore absence of an intervention alone does not make an arbitrary M2DGR
clean record healthy.

Existing M2DGR clean branches remain unlabelled.

No baseline-nominality source has been selected.

No concrete partial intervention mechanism has been selected.

No complete-unavailability intervention mechanism has been selected.

No retained fraction, point count, ring count, azimuth width or other numeric
severity has been selected.

Accepted supervision-source count remains **0**.

Real health-label count remains **0**.

The five-feature Phase-4 contract remains unchanged.

A fail-closed missing-record branch around the eventual five-feature
classifier remains an architectural possibility, not a selected
implementation.

No classifier structure, threshold, model or calibration has been selected.

No reference or confirmation-test data are used.

No ATE/RPE or estimator scoring is performed.

Phase-5 exit evidence remains **NOT YET SATISFIED**.

Current TRUST-ROBOT regression after this protocol layer:

**398 / 398 PASS.**


## Phase-5 prospective baseline-nominality evidence protocol

The existing evidence audit found no accepted independent interval-bound
baseline-nominality source for the LiDAR modality.

A new prospective evidence protocol therefore defines what a future source
must prove before a controlled `full` condition can contribute a healthy
training label.

For the currently bound Velodyne VLP-32C hardware, the candidate requires
manufacturer-grounded positive operational evidence:

- Motor State = `ON`;
- Laser State = `ON`;
- Thermal Status = `Ok`.

Those discrete operational states are **not** numeric Phase-5 thresholds and
do not make the manufacturer manual itself a runtime receipt.

The candidate additionally requires exact source-measurement identity,
acquisition-session provenance, interval provenance, raw status evidence,
explicit interval-binding evidence and a no-deliberate-intervention receipt.

No temporal tolerance, fixed offset, interpolation or nearest-neighbor
association is selected by this protocol.

The concrete acquisition mechanism remains unselected.

The concrete interval-binding mechanism remains unselected.

No candidate baseline-nominality receipt exists yet.

Accepted baseline-nominality source count remains **0**.

Accepted health-supervision source count remains **0**.

Real health-label count remains **0**.

Controlled corruption generation remains unauthorized.

Health-label generation remains unauthorized.

Classifier training remains unauthorized.

No Phase-4 diagnostic value, localization score, reference trajectory or
confirmation-test result can establish baseline nominality.

Phase-5 exit evidence remains **NOT YET SATISFIED**.

Current TRUST-ROBOT regression after this protocol layer:

**416 / 416 PASS.**


## Phase-5 prospective baseline-nominality raw-capture format

The offline acquisition-feasibility audit found that the local environment has
basic raw-acquisition primitives, while live hardware and interval binding
remain unverified.

A prospective raw-capture format now defines four evidence artifact kinds:

- measurement;
- sensor status;
- sensor diagnostic;
- position packet.

The multi-artifact design is deliberate.

The manufacturer documents `cgi/status.json` for motor/laser state, while
Thermal Status is documented in the position packet at offset `0xCB`.

The audit did not establish an explicit Thermal Status field in the HTTP
status or diagnostic sections.

Each raw artifact receipt preserves exact raw-byte and capture-metadata
SHA-256 identities plus host capture start/end observations.

Host capture timestamps remain transport/provenance evidence only.

They are not treated as physical LiDAR measurement timestamps.

No interval association mechanism is selected.

No timing tolerance, fixed offset or interpolation is selected.

No sensor network address is selected.

No live capture mechanism is selected.

No live sensor has been contacted.

No raw capture artifact exists yet.

No candidate baseline-nominality receipt exists yet.

Accepted baseline-nominality source count remains **0**.

Accepted health-supervision source count remains **0**.

Real health-label count remains **0**.

Raw evidence capture alone does not establish baseline nominality or health.

Controlled corruption generation remains unauthorized.

Health-label generation remains unauthorized.

Classifier training remains unauthorized.

Phase-5 exit evidence remains **NOT YET SATISFIED**.

Current TRUST-ROBOT regression after this raw-capture format layer:

**436 / 436 PASS.**


## Phase-5 prospective acquisition-session provenance

The manufacturer identity audit establishes that the VLP-32C information
interface `/cgi/info.json` exposes sensor model, serial number and firmware
versions.

The manufacturer also states that each sensor has a unique factory-assigned
Serial Number that cannot be changed.

The prospective session-provenance format therefore selects the manufacturer
serial number as the primary physical-device identity field.

The active MAC address is not used as primary identity because the manual
documents a user-configurable MAC override.

A network address is not treated as physical-device identity.

Firmware versions are preserved only as runtime/configuration context.

The manufacturer snapshot `info.serial` field is available as optional future
corroboration but is not required or selected for live capture.

A separate prospective no-intervention declaration format is also defined.

That declaration records that the intended baseline condition is `full` and
that no deliberate availability intervention has been applied before the
controlled-intervention phase.

The declaration is procedural provenance, not physical health truth.

No live sensor has been contacted.

No `/cgi/info.json` response has been captured.

No real serial number has been observed.

No network address has been selected.

Device-identity receipt count remains **0**.

No-intervention declaration count remains **0**.

Session-provenance bundle count remains **0**.

Accepted baseline-nominality source count remains **0**.

Accepted health-supervision source count remains **0**.

Real health-label count remains **0**.

No interval binding, timing tolerance, fixed offset or interpolation is
selected.

Controlled corruption generation remains unauthorized.

Health-label generation remains unauthorized.

Classifier training remains unauthorized.

Phase-5 exit evidence remains **NOT YET SATISFIED**.

Current TRUST-ROBOT regression after this provenance layer:

**458 / 458 PASS.**


## Phase-5 non-executing parameterized live-acquisition plan

A deterministic plan-only tool now exists for a future VLP-32C raw-evidence
acquisition.

The tool requires the future operator to provide explicitly:

- sensor IPv4 address;
- capture interface;
- data UDP port;
- telemetry UDP port;
- capture duration;
- output directory;
- acquisition-session identity;
- TRAIN or VALIDATION split.

The manufacturer example/default address and packet-port defaults are not
adopted by the protocol.

The plan emits argv arrays for read-only `/cgi/info.json`,
`/cgi/status.json`, `/cgi/diag.json`, measurement-packet capture and
position-packet capture.

The implementation performs no subprocess execution and no network I/O.

No sensor has been contacted.

No real sensor address has been selected.

No capture order is selected.

No status polling period is selected.

No interval binding, timing tolerance, fixed offset or interpolation is
selected.

Generating a plan does not establish baseline nominality, accepted
supervision or a health label.

Raw capture artifact count remains **0**.

Device-identity receipt count remains **0**.

No-intervention declaration count remains **0**.

Accepted baseline-nominality source count remains **0**.

Accepted health-supervision source count remains **0**.

Real health-label count remains **0**.

Live execution remains unauthorized.

Controlled corruption generation remains unauthorized.

Health-label generation remains unauthorized.

Classifier training remains unauthorized.

Phase-5 exit evidence remains **NOT YET SATISFIED**.

Current TRUST-ROBOT regression after this plan-only layer:

**484 / 484 PASS.**


## Phase-5 live-executor safety contract

The offline execution-readiness audit exposed four unresolved engineering
boundaries: actual capture permission, crash-safe output publication, bounded
HTTP requests and packet-capture finalization semantics.

A non-networked executor-safety contract now selects a fail-closed local
publication policy.

A future executor must use an explicitly supplied absolute output root and
reserve a fresh acquisition-session directory.

Session-directory collisions are rejected.

Artifacts must be written first to same-directory `.partial` files.

Files are fsynced and hashed before publication, atomically published, the
directory is fsynced, and final SHA-256 must match the prepublication hash.

Existing final artifacts may not be overwritten.

A future invocation must explicitly supply HTTP connection and total-request
timeout values.

No numeric HTTP timeout values are selected by the protocol.

Those engineering bounds are not sensor-time or evaluation-association
tolerances.

A deterministic classic-PCAP structural validation policy is also defined.

Raw PCAP evidence requires recognized PCAP structure, complete packet-record
boundaries and at least one complete packet.

This structural rule does not establish sensor health.

Process return code, deadline expiry, SIGINT request and kill-after-grace
state are preserved separately in a future finalization receipt.

GNU timeout return code `124` alone establishes neither successful nor failed
capture.

Actual tcpdump capture permission remains unverified.

Actual tcpdump SIGINT finalization remains unverified.

Network execution is not implemented.

Subprocess execution is not implemented.

No real output root is selected.

No capture interface is selected.

No sensor network address is selected.

Raw capture artifact count remains **0**.

Accepted baseline-nominality source count remains **0**.

Accepted health-supervision source count remains **0**.

Real health-label count remains **0**.

Live executor implementation ready remains **false**.

Live execution remains unauthorized.

No interval binding, timing tolerance, fixed offset or interpolation is
selected.

Health-label generation remains unauthorized.

Classifier training remains unauthorized.

Phase-5 exit evidence remains **NOT YET SATISFIED**.

Current TRUST-ROBOT regression after this safety-contract layer:

**512 / 512 PASS.**


## Phase-5 unprivileged dual-UDP receiver

The workstation packet-sniffing path is privilege-blocked for the current
account, but a separate loopback audit verified ordinary user-space
`AF_INET` / `SOCK_DGRAM` reception for two simultaneous UDP streams.

A pure user-space dual-UDP receiver is now implemented.

It requires explicit future values for acquisition-session identity, TRAIN
or VALIDATION split, local bind IPv4 address, measurement UDP destination
port, position UDP destination port, capture duration and absolute output
root.

No actual VLP-32C address, port or workstation bind address is selected by
this implementation.

The receiver preserves exact delivered UDP payload bytes in per-stream
archives.

Per-datagram JSONL metadata preserves payload boundaries, SHA-256, source
IPv4/UDP endpoint and host userspace receive timestamps.

Host receive timestamps remain transport provenance only.

Ethernet, IP and UDP headers are not preserved because this is endpoint UDP
reception rather than passive interface sniffing.

Receipt of datagrams does not prove absence of packet loss.

No packet-rate, packet-count or timing health threshold is introduced.

Successful stream artifacts use the frozen same-directory partial-file,
fsync, SHA-256 and atomic-publication contract.

A stream with zero received datagrams is not published as raw evidence by
this receiver; this is fail-closed acquisition handling and not a health
label.

The first targeted test run reached 27/28 PASS. Its sole failure was a test
false positive caused by searching source text for the word `sudo`, which
also occurs in the intended `requires_sudo: false` metadata declaration.

The receiver module and configuration were not changed during recovery. The
test was corrected to validate the actual socket constructor structurally:
`AF_INET` plus `SOCK_DGRAM`, with `SOCK_RAW` and `AF_PACKET` prohibited.

Loopback receiver execution is verified.

Real VLP-32C receiver execution remains unverified.

No real sensor has been contacted.

Raw real-sensor capture artifact count remains **0**.

Accepted baseline-nominality source count remains **0**.

Accepted health-supervision source count remains **0**.

Real health-label count remains **0**.

No interval binding, timing tolerance, fixed offset or interpolation is
selected.

Health-label generation remains unauthorized.

Classifier training remains unauthorized.

Real-sensor execution remains unauthorized.

Phase-5 exit evidence remains **NOT YET SATISFIED**.

Current TRUST-ROBOT regression after this receiver layer and targeted test
recovery:

**540 / 540 PASS.**

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
- reuse pre-split all-training characterization to select an association tolerance;
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
   or other physical quantities merely because a validation/calibration split
   now exists. Physical facts are not tunable protocol parameters.
6. Keep dataset calibration, synchronization, and evaluation readiness false
   until independent evidence resolves the required estimator/reference
   calibration and timing blockers.

## Development rule

Long workstation scans must use a detached process with PID and persistent log.

Short metadata validation, finalization, and unit-test commands may run
interactively.

## Phase 5 multimodal diagnostic foundation candidate V1

Status: **implemented locally; not promoted; empirical health training and
physical multimodal validation remain blocked/deferred.**

The Phase-5 architecture is now explicitly multimodal around the project core:

- camera / vision;
- IMU;
- LiDAR / depth;
- GNSS as optional/platform-dependent input.

A common modality adapter and measurement-availability contract is implemented
without creating health labels from mere stream presence or absence.

The frozen Phase-4 LiDAR diagnostic feature contract remains unchanged and is
bound by its existing freeze SHA-256. Camera, IMU and GNSS diagnostic feature
contracts remain intentionally unselected pending their own validated
diagnostic evidence.

No classifier architecture, learned weights, health threshold, calibration
temperature or real healthy/degraded/unusable assignment has been selected.
Classifier training remains unauthorized. Confirmation-test data remain closed
to model/threshold/calibration/supervision selection. No ATE/RPE or final
trajectory scoring has been performed.

Physical hardware integration is deferred. Later hardware work should populate
the existing adapter/evidence interfaces rather than redefine the common
Phase-5 health architecture.

Artifacts:

- `configs/trust_robot/phase5_multimodal_diagnostic_foundation_candidate_v1.json`
  SHA-256 `37cba4494f1d84b16d3d84d106303bf649874bb3fb58c6b626ea6b5aeb1ce8a3`
- `src/trust_robot/multimodal_diagnostic_foundation.py`
  SHA-256 `429778265826f839bd685a93d77b55d4bb0c18a2aa843c8947af28fef9916b43`
- `tests/trust_robot/test_multimodal_diagnostic_foundation.py`
  SHA-256 `81c6cbe04cb7487d16e56816c1e73229a0e509edc1fbd224c1cdc010373fd471`
- `docs/audits/trust_robot/TRUST_ROBOT_PHASE5_MULTIMODAL_DIAGNOSTIC_FOUNDATION_V1.md`
  SHA-256 `3a16c724647ad7c862c0c10c4953e7705df0b7491515734d47ae7df5ab90d858`

Scientific counters remain:

- accepted baseline-nominality sources: 0;
- accepted health-supervision sources: 0;
- real healthy/degraded/unusable assignments: 0;
- classifier training authorized: false.

## Phase 5 camera / IMU raw observation adapter candidate V1

Status: **implemented locally; not promoted; camera/IMU diagnostic feature
selection remains intentionally deferred.**

The common Phase-5 multimodal foundation now has a concrete raw-observation
adapter for the M2DGR camera and IMU streams:

- `/camera/color/image_raw/compressed`;
- `/camera/imu`;
- `/handsfree/imu`.

The adapter preserves serialized-message digest/size, source stream, split role,
message index, caller-supplied message type, bag record time and optional header
timestamp. It does not decode the payload or select diagnostic features.

Bag record time remains transport/container time only. Header timestamp
presence does not prove physical capture-time semantics, a shared clock,
synchronization, fixed offset or interpolation rule.

No camera or IMU health label, probability, threshold, model, calibration
parameter or training action is enabled. Confirmation-test data remain
prohibited for feature/model/threshold/calibration/supervision selection.

Artifacts:

- `configs/trust_robot/phase5_camera_imu_observation_adapter_candidate_v1.json`
  SHA-256 `1dd104b036e46b94990600e5484a465081a7f7f95adaa2b17b634838f222d8cd`
- `src/trust_robot/camera_imu_observation_adapter.py`
  SHA-256 `1ef9e34e4309fb420d05a8e14671803e5591b1efe7f07257a60ece8d9c611a92`
- `tests/trust_robot/test_camera_imu_observation_adapter.py`
  SHA-256 `97ea89e262ef26ab92fe66a0529f9e6439c023b7d34a8352117bf796df0e6b11`
- `docs/audits/trust_robot/TRUST_ROBOT_PHASE5_CAMERA_IMU_OBSERVATION_ADAPTER_V1.md`
  SHA-256 `4814bf4035bb1ea4fdda8e8c1a356c86fd0cc0dee2f90666e23f50defe5766f5`

Scientific counters remain unchanged:

- accepted baseline-nominality sources: 0;
- accepted health-supervision sources: 0;
- real healthy/degraded/unusable assignments: 0;
- classifier training authorized: false.

## Phase 5 camera / IMU TRAIN ingestion runner candidate V1

Status: **implemented locally; not promoted; complete 22-trajectory TRAIN
execution remains pending.**

A deterministic real-M2DGR ingestion runner now exists for the Phase-5 camera
and IMU raw-observation adapter.

Its execution population is exactly the 22 frozen TRAIN trajectories. It reads
only:

- `/camera/color/image_raw/compressed`;
- `/camera/imu`;
- `/handsfree/imu`.

It does not open validation or confirmation-test bags and does not read
reference/GT/GNSS/pose/odometry/TF streams.

Per-message raw receipts are aggregated into deterministic stream digests plus
counts/byte totals and directly represented first/last timing fields. Missing
streams remain explicit rather than being fabricated.

No camera/IMU feature contract, health label, probability, threshold,
classifier, synchronization offset, interpolation rule, ATE/RPE or final score
is selected or computed.

Artifacts:

- `configs/trust_robot/phase5_camera_imu_train_ingestion_candidate_v1.json`
  SHA-256 `4a1794c81528bcd04165e4da52b60e10b5140a0a276452aa2cf269a4d66c3b9b`
- `src/trust_robot/camera_imu_train_ingestion.py`
  SHA-256 `9d5e75a3122be841cc9e4dfd952e4c97d92769fd2a9ab4e81bd93c213f5681bd`
- `scripts/trust_robot/run_phase5_camera_imu_train_ingestion_v1.py`
  SHA-256 `10c6ecd8d89eb21ae3aa48a4b500ce241ae2ca5621f8de0f48cb84746f454f9d`
- `tests/trust_robot/test_camera_imu_train_ingestion.py`
  SHA-256 `e49fb96f679cc93eefc40446b71656083aea2c37b484d0eb04077c13d2e2955e`
- `docs/audits/trust_robot/TRUST_ROBOT_PHASE5_CAMERA_IMU_TRAIN_INGESTION_V1.md`
  SHA-256 `e931a45690b0edc5e293aa7f6f289bab1e3d6c0e5f413122bfe043040413ae2d`

Scientific counters remain unchanged:

- accepted baseline-nominality sources: 0;
- accepted health-supervision sources: 0;
- real healthy/degraded/unusable assignments: 0;
- classifier training authorized: false.

## Phase 5 camera / IMU frozen TRAIN source evidence V1

Status: **verified real TRAIN source evidence frozen locally; not promoted;
camera/IMU diagnostic feature selection remains pending.**

The complete camera/IMU TRAIN ingestion finished and was independently
verified across all 22 frozen TRAIN trajectories.

Verified total:

- 2,816,957 selected camera/IMU observations;
- 4,320,203,720 serialized payload bytes.

Camera `/camera/color/image_raw/compressed` and D435i `/camera/imu` are present
on 20/22 TRAIN trajectories and absent on `street_010` and `street_09`.

HandsFree `/handsfree/imu` is present on 22/22 TRAIN trajectories.

Representative feasibility inspection additionally established successful
Pillow decoding for 20/20 inspected TRAIN JPEG camera observations and finite
representative inertial fields for both IMU streams.

These observations are source/feasibility evidence only. They do not select a
camera or IMU feature vector and do not create healthy/degraded/unusable
labels.

Artifacts:

- `manifests/trust_robot_phase5_camera_imu_train_source_evidence_v1.json`
  SHA-256 `d4d2a73ddbcf73102cec0d0d4556fa65786a408217fefe1dece0f4d402cce675`
- `src/trust_robot/camera_imu_train_source_evidence.py`
  SHA-256 `4fc2321532b7889d1b356919ee60d9036e4171221607c90d0e34f7ef9e213a73`
- `tests/trust_robot/test_camera_imu_train_source_evidence.py`
  SHA-256 `62eaa35c7ef2c2f89f2f23d4eae5e84185bf64c122fa9e191a3ee1200b4ae3b8`
- `docs/audits/trust_robot/TRUST_ROBOT_PHASE5_CAMERA_IMU_TRAIN_SOURCE_EVIDENCE_V1.md`
  SHA-256 `6e42f8545369337b832a63d0b372dbdabbd5d85854a4e9d5621b423a2c578a62`

Scientific counters remain:

- accepted baseline-nominality sources: 0;
- accepted health-supervision sources: 0;
- real healthy/degraded/unusable assignments: 0;
- classifier training authorized: false.

## Phase 5 camera / IMU diagnostic channel contract V1

Status: **diagnostic-channel architecture implemented locally; exact
camera/IMU numeric feature vectors intentionally remain unselected.**

The project-supported persistent health evidence architecture is now explicit
for both camera and IMU:

1. low-level signal summaries;
2. front-end diagnostics;
3. residual-history evidence.

The feature-basis audit did not identify a project-frozen exact numeric
camera/IMU low-level feature vector. Therefore brightness, blur scores,
acceleration norms, jerk, covariance entries, or similar quantities have not
been silently promoted into the health contract.

Camera visual relative-motion/reprojection diagnostics and IMU preintegration
diagnostics are represented as required interfaces but are not falsely claimed
as implemented.

Phase-3 camera blur/exposure and IMU bias/drift remain controlled stressor
families, not health features or labels.

Current innovation remains explicitly separated from persistent modality health
and reserved for the later short-horizon factor-conditioning pathway.

Artifacts:

- `configs/trust_robot/phase5_camera_imu_diagnostic_channel_contract_candidate_v1.json`
  SHA-256 `de6656d35e24162dcd3ff489f21b735396c2457dae526a13be9790bb88bdf485`
- `src/trust_robot/camera_imu_diagnostic_channels.py`
  SHA-256 `72dd6e4a945dbd90eb84366248bcb4d3460f934b4c5875a541166aaef3282fbf`
- `tests/trust_robot/test_camera_imu_diagnostic_channels.py`
  SHA-256 `161fceb7c3b6498413e7ea247217405b4e181f7da5857f0544023c3ba521b3c8`
- `docs/audits/trust_robot/TRUST_ROBOT_PHASE5_CAMERA_IMU_DIAGNOSTIC_CHANNEL_CONTRACT_V1.md`
  SHA-256 `9c9f44477c157f3bae53608c29fa5b21b37bfef9c813187065c36e9af839fb0a`

Scientific counters remain:

- accepted baseline-nominality sources: 0;
- accepted health-supervision sources: 0;
- real healthy/degraded/unusable assignments: 0;
- classifier training authorized: false.

## Phase 5 multimodal health-model software interface V1

Status: **software interface implemented locally; empirical health-model
selection/training/calibration remains evidence-blocked and deferred.**

The Phase-5 three-state multimodal health-model interface now binds camera,
IMU and LiDAR as core modalities and GNSS as optional.

LiDAR retains its frozen validated Phase-4 five-feature diagnostic contract.

Camera and IMU bind the three persistent-health evidence channels already
implemented by the diagnostic-channel contract, while their exact numeric
feature sets remain intentionally unselected.

The model layer fails closed:

- classifier architecture unselected;
- accepted baseline-nominality sources: 0;
- accepted health-supervision sources: 0;
- real health labels: 0;
- classifier training unauthorized;
- calibration parameter unselected;
- health threshold unselected;
- health inference unauthorized;
- health-state output disabled;
- health-probability output disabled.

Availability remains distinct from health state, missing measurements are not
zero vectors, current innovation remains separate from persistent health, and
confirmation-test data remain closed.

Artifacts:

- `configs/trust_robot/phase5_multimodal_health_model_interface_candidate_v1.json`
  SHA-256 `aa48c67cdcd19aa5af2a297f42b20d1bb4369b5dcd38bdc2c2ca9ae68ceb4ea3`
- `src/trust_robot/multimodal_health_model.py`
  SHA-256 `03a5575ea69631273037db6364ab3b31dc02d27e08a65627246bf92a1dc53871`
- `tests/trust_robot/test_multimodal_health_model.py`
  SHA-256 `c0566dd76b23d93a769ffe72f98b4d23412a7ab967eea8ab73a70976bd94215a`
- `docs/audits/trust_robot/TRUST_ROBOT_PHASE5_MULTIMODAL_HEALTH_MODEL_INTERFACE_V1.md`
  SHA-256 `4d6e003bd94fc29c2dcd816c63f7838078c64aa3c90eb9dcd2c9336bbbfb3727`

This establishes an implemented-but-evidence-blocked Phase-5 software
architecture. It does not claim an empirically trained health classifier.

## Phase 5 multimodal software architecture freeze V1

Status: **software architecture frozen for checkpoint promotion; empirical
health-model completion explicitly deferred.**

The comprehensive Phase-5 closure audit passed with the exact expected
63-path pre-freeze worktree and a 770-test regression.

The repository-resident freeze records:

- camera, IMU and LiDAR as core modalities;
- GNSS as optional;
- healthy/degraded/unusable semantics;
- frozen Phase-4 LiDAR diagnostics unchanged;
- explicit camera/IMU low-level, front-end and residual-history channels;
- fail-closed health-model training and inference gates;
- verified real camera/IMU TRAIN ingestion evidence.

This is not a claim that an empirical health classifier has been trained.

Current empirical gate remains:

- camera exact feature contract selected: false;
- IMU exact feature contract selected: false;
- accepted baseline-nominality sources: 0;
- accepted health-supervision sources: 0;
- real health labels: 0;
- classifier architecture selected: false;
- classifier training authorized: false;
- calibration parameter selected: false;
- health threshold selected: false;
- health inference authorized: false;
- physical validation deferred: true.

Confirmation remains closed.

Freeze artifacts:

- `manifests/trust_robot_phase5_multimodal_software_architecture_freeze_v1.json`
  SHA-256 `457a42c3778731307b1371208407fca6d7cf8e604718f81138034479deb0d09a`
- `tests/trust_robot/test_phase5_multimodal_software_architecture_freeze.py`
  SHA-256 `f41493d1644f9343e495a2397c405a5a32cdbb30581933566f19b8879759740a`
- `docs/audits/trust_robot/TRUST_ROBOT_PHASE5_MULTIMODAL_SOFTWARE_ARCHITECTURE_FREEZE_V1.md`
  SHA-256 `fa02bdd438473a52603c3280040c7bc64ee0511420fef62f899d37407f01cba9`

Closure evidence:

- report SHA-256 `997640c0a4ba316fbaa505f65a959501f2c6e142dfcc9388b716a84458f2a699`
- JSON SHA-256 `07ddfacf44d53788f68147702eafdff5da0d0399e829cedb6a1417869028ca85`

After promotion, Phase-6 software work may proceed behind these gates.

## Phase 6 probabilistic calibration contract V1

Status: **probabilistic calibration software contract implemented locally;
empirical calibration remains evidence-blocked.**

Phase 6 is explicitly separated from physical sensor/geometric calibration.

The project proposal specifies validation-only probabilistic calibration and
names temperature scaling as the current mechanism. The contract therefore
records `temperature_scaling` as the proposal-defined mechanism without
claiming that any temperature has been fitted or selected.

The frozen `validation_calibration` partition contains seven trajectories and
is the only permitted future data-selection partition for this calibration.

The `confirmation_test` partition remains closed to calibration selection.

Current empirical gate:

- Phase-5 empirical health model complete: false;
- trained health model available: false;
- uncalibrated health-model outputs available: false;
- admissible health labels available: false;
- calibration objective selected: false;
- temperature scope selected: false;
- temperature parameter selected: false;
- calibration execution authorized: false;
- calibrated probability output authorized: false.

No health, suppression, recovery or fallback threshold is selected by this
contract.

Artifacts:

- `configs/trust_robot/phase6_probabilistic_calibration_contract_candidate_v1.json`
  SHA-256 `7761cf8c39620d7166c88092470aeb09e2f5b1120cd0d4be3e1c11118822f367`
- `src/trust_robot/probabilistic_calibration.py`
  SHA-256 `81c22be62a4dec6e37cb0a7c5dda90b1b300f6b3a5234c7a605d176c652f23ab`
- `tests/trust_robot/test_probabilistic_calibration.py`
  SHA-256 `ba998071f7dc8cd549b1de139fe51e32ed979a3ab710adb8a93449985d8b1b65`
- `docs/audits/trust_robot/TRUST_ROBOT_PHASE6_PROBABILISTIC_CALIBRATION_CONTRACT_V1.md`
  SHA-256 `dd98159a45ee29c2b98ec18e7eeda7bcb835fcb327be8b6d937d052ab352c1a5`

Frontier audit evidence:

- report SHA-256 `903652150452ec9c006dbbd14981056afd3525f06844358ee2b9437c210db522`
- JSON SHA-256 `4c0eae88b55b9dc14b2e376fa4f6fda329da7edde86236fb05825246afe66310`

No validation or confirmation trajectory is opened by this implementation.
No calibration parameter is selected or fitted.

## Phase 6 probabilistic calibration software freeze V1

Status: **validation-only probabilistic-calibration software architecture
frozen for checkpoint promotion; empirical calibration remains deferred.**

The Phase-6 closure audit passed with the exact five-path pre-freeze worktree
and an 838-test regression.

The freeze records temperature scaling as the proposal-defined probabilistic
calibration mechanism without fitting or selecting a temperature.

Current empirical state remains:

- empirical Phase-5 health model available: false;
- uncalibrated health-model probabilities available: false;
- admissible calibration labels available: false;
- calibration objective selected: false;
- calibration-quality metrics selected: false;
- temperature scope selected: false;
- temperature parameter selected: false;
- parameter fitting performed: false;
- validation bags opened for calibration: false;
- calibrated health-probability output authorized: false.

The frozen validation_calibration partition contains seven trajectories but
remains unopened for empirical calibration in the present evidence state.

The confirmation_test partition remains closed.

Health/suppression/recovery/fallback thresholds remain separate from
temperature calibration and are unselected.

Freeze artifacts:

- `manifests/trust_robot_phase6_probabilistic_calibration_software_freeze_v1.json`
  SHA-256 `a022c1923d340bb2fc40a2c7515199ab92d7745f95546ca055ee63fb11f1f2e6`
- `tests/trust_robot/test_phase6_probabilistic_calibration_software_freeze.py`
  SHA-256 `6632e0c164e7af0ca92b681ed9a6d8299c4ce94ce05d18a05c6c6419e5f1bbce`
- `docs/audits/trust_robot/TRUST_ROBOT_PHASE6_PROBABILISTIC_CALIBRATION_SOFTWARE_FREEZE_V1.md`
  SHA-256 `2838337dcbc9d3cc2f8b7616ea78d5896df898d2c00e27c1eb1054ed816b2a42`

Closure evidence:

- report SHA-256 `2342ee541365c179d89d09ecc3de4ee75b17a8075257d4cc6d5f4a418be41f68`
- JSON SHA-256 `eadfefa1a3267a26cfbc06e0d2f877c6872cc67df643ba66c1c380bec29ff204`

After promotion, Phase-7 software work may proceed behind these gates without
assuming that empirical Phase-6 calibration has been completed.

## Phase 7 auxiliary consistency contract V1

Status: **auxiliary-consistency software architecture implemented locally;
numeric/physical consistency definitions and empirical evidence remain
unselected/deferred.**

Phase 7 is bound to the authoritative project scope:

- visual motion versus LiDAR motion;
- inertial propagation versus exteroceptive odometry;
- temporal pose continuity;
- kinematic/proprioceptive motion;
- platform motion bounds;
- residual histories.

Pairwise disagreement establishes inconsistency but does not by itself identify
the responsible modality.

Responsible-modality attribution may require modality-specific diagnostics,
another sufficiently informative modality, or a trusted physical constraint.

Ambiguous cases must remain explicit rather than receive fabricated confident
attribution.

Current unresolved definitions remain:

- numeric consistency measure;
- temporal tolerance;
- time offset;
- interpolation;
- cross-modal transform;
- kinematic model;
- trusted platform motion bounds;
- residual-history definition.

Accordingly, numeric consistency execution and source attribution fail closed.

Phase-8 factor conditioning and Phase-9 suppression/recovery/status remain
strictly outside this implementation.

Historical IMU-HAR OOD choices are not adopted, and GNSS remains optional.

Artifacts:

- `configs/trust_robot/phase7_auxiliary_consistency_contract_candidate_v1.json`
  SHA-256 `79eb3151344c5dd9e4f4212467f24cc2e956ce16689e808ae1008539f80efce6`
- `src/trust_robot/auxiliary_consistency.py`
  SHA-256 `72e999b63950ff8070a978bcfac81cb54c598d97c0e539c28bfd92648a34124a`
- `tests/trust_robot/test_auxiliary_consistency.py`
  SHA-256 `c18ea0c3a1c914d1f7915a8fed6ef56e477d7e42ea9f01c3140e5e1264eb382b`
- `docs/audits/trust_robot/TRUST_ROBOT_PHASE7_AUXILIARY_CONSISTENCY_CONTRACT_V1.md`
  SHA-256 `f685dfdd64f49db72b95b53e28739e34d9cc895ff0db247600f08613b49891ca`

Authoritative scope evidence:

- report SHA-256 `5b23f88b200c263f98232eb290dd6faed8e1eee584efe26ea414c5cb60ce6d49`
- JSON SHA-256 `0cd1258c3389643d6a0295dfa84cdd9bf10ac74211e4c04f4f77281ff97c67f5`

No validation or confirmation data are opened.
No ATE/RPE or final scoring is performed.

## Phase 7 six-family consistency prerequisite registry V1

Status: **family-by-family prerequisites frozen locally; zero of six auxiliary
consistency families are currently authorized for numerical execution.**

No additional numerical consistency adapter is implemented because each
authoritative family still has unresolved scientific prerequisites.

The six registered families are:

- visual motion versus LiDAR motion;
- inertial propagation versus exteroceptive odometry;
- temporal pose continuity;
- kinematic/proprioceptive motion;
- platform motion bounds;
- residual histories.

Global state:

- execution-ready families: 0;
- numeric consistency measures selected: 0;
- source attribution authorized: false;
- synchronization selected/verified: false;
- temporal tolerance selected: false;
- fixed offset selected: false;
- interpolation selected: false;
- alignment execution authorized: false;
- visual frontend diagnostics implemented: false;
- IMU preintegration diagnostics implemented: false;
- camera residual history implemented: false;
- IMU residual history implemented: false.

Repository candidate matches are not treated as validated prerequisites.

Optional proprioception still requires verified actual robot streams.

Platform-bound mentions are not treated as trusted numeric motion limits.

The prerequisite audit's narrow LiDAR source string indicator was false, but
this does not invalidate the frozen Phase-2 LiDAR baseline.

Artifacts:

- `manifests/trust_robot_phase7_consistency_prerequisite_registry_v1.json`
  SHA-256 `0bef183cdfc960ef4d8f0917d28ff927b4a21e925dd6425a489b91021041c7dd`
- `tests/trust_robot/test_phase7_consistency_prerequisite_registry.py`
  SHA-256 `d5b1ae76e87cf4d46a5442876b43d53c1c8632ea0ae90f8867da982e2be320cd`
- `docs/audits/trust_robot/TRUST_ROBOT_PHASE7_CONSISTENCY_PREREQUISITE_REGISTRY_V1.md`
  SHA-256 `2f01f3517bf8e8af39b5bab4061337dc96f29c98cefd782b4df427fad78468ad`

Prerequisite audit evidence:

- report SHA-256 `64c6def9e8449b39eaac4a86aed205ca431179569c6297426c2dd3b210811fb8`
- JSON SHA-256 `6e4a0103b4ce3434beed301377c0487d8ddac065a4598ec40da2623f35f671d8`

No validation or confirmation data are opened.
No Phase-8 or Phase-9 behavior is introduced.

## Phase 7 auxiliary consistency software freeze V1

Status: **auxiliary-consistency software architecture and six-family
prerequisite registry frozen for checkpoint promotion; numerical/empirical
consistency execution remains deferred.**

The Phase-7 closure passed with the exact eight-path pre-freeze worktree and
928/928 tests.

Frozen authoritative evidence families:

1. visual motion versus LiDAR motion;
2. inertial propagation versus exteroceptive odometry;
3. temporal pose continuity;
4. kinematic/proprioceptive motion;
5. platform motion bounds;
6. residual histories.

Current family state:

- execution-ready families: 0;
- selected numeric consistency measures: 0;
- source attribution authorized: false;
- new numeric consistency adapter implemented: false.

Pairwise disagreement may establish inconsistency but does not by itself
identify a responsible modality.

Unresolved prerequisites remain explicitly recorded rather than filled with
arbitrary timing, transform, kinematic, physical-bound or residual choices.

Phase-8 factor conditioning and Phase-9 suppression/recovery/status remain
outside this checkpoint.

Freeze artifacts:

- `manifests/trust_robot_phase7_auxiliary_consistency_software_freeze_v1.json`
  SHA-256 `5f416186ee8d8b226f0f88c70a0553cf80fe5213592b8df9b07fc1b5503b7280`
- `tests/trust_robot/test_phase7_auxiliary_consistency_software_freeze.py`
  SHA-256 `a34da8d993491a5b15dd169abe261d984a19b5a70be1868b156bfb99d4a14c3c`
- `docs/audits/trust_robot/TRUST_ROBOT_PHASE7_AUXILIARY_CONSISTENCY_SOFTWARE_FREEZE_V1.md`
  SHA-256 `836628959c6199249bf1b366222311dc3352cc3f330394222626b95639494014`

Closure evidence:

- report SHA-256 `5c773ee3987f7fc9763a55cba9a306785b04d650425dc385c34e2501801a807e`
- JSON SHA-256 `504a9fbd1ad3335d5128415db484c33d504b46c455bee2834222a70253657f08`

After promotion, Phase-8 software architecture may proceed but must not assume
that numerical Phase-7 auxiliary consistency evidence exists.

## Phase 8 factor-conditioning contract V1

Status: **fail-closed factor-conditioning software architecture implemented
locally; numerical factor conditioning remains disabled.**

The authoritative conceptual equations are preserved:

- `w_m(t) = p_H_m(t) + alpha_m * p_D_m(t)`
- `lambda_m = clip(w_m * q_m, epsilon_m, 1)`

The persistent-health and current-innovation pathways remain scientifically
separate.

Current state:

- empirical Phase-5 health probabilities available: false;
- calibrated Phase-6 health probabilities available: false;
- Phase-7 numerical auxiliary evidence available: false;
- `alpha_m` selected: false;
- numerical standardized-innovation definition selected: false;
- `q_m` definition selected: false;
- `epsilon_m` selected: false;
- factor-scale execution authorized: false;
- factor-information rescaling implemented: false;
- covariance inflation implemented: false.

`alpha_m` remains reserved for validation selection as required by the project.

No selection policy for `epsilon_m` is invented.

No numerical definition for `q_m` is invented.

No factor in the estimator is modified.

Phase-9 suppression/recovery/status behavior remains outside this
implementation.

Artifacts:

- `configs/trust_robot/phase8_factor_conditioning_contract_candidate_v1.json`
  SHA-256 `cbd137977060f961fb14feaeed6194de40b4e4338e5f6c303edc1993110ea5c2`
- `src/trust_robot/factor_conditioning.py`
  SHA-256 `96d3c179d1690aa75edd0c6a6d8ce8a14d079da02ab225d1da9ffe2bc4a97b6a`
- `tests/trust_robot/test_factor_conditioning.py`
  SHA-256 `b457e2d26cc3a4a9a381016094a7eeee1acfb77cd8867d147c07d879adfae3cd`
- `docs/audits/trust_robot/TRUST_ROBOT_PHASE8_FACTOR_CONDITIONING_CONTRACT_V1.md`
  SHA-256 `0d357d0f1919f43d4f26a1763b4191e2216f5afcfecbb62162384b9a6ffeae8f`

Frontier evidence:

- report SHA-256 `fdd91cac466e01306369e8e312d6ac576cd89f0e8edb2e57bd0113116c0f4819`
- JSON SHA-256 `e171714edcc448c206cadcfb517ca6e9980f09aa352991c622afa7db257eb833`

Validation remains unopened and confirmation remains closed.
No ATE/RPE or final scoring is performed.

## Phase 8 factor-conditioning software freeze V1

Status: **factor-conditioning software architecture frozen for checkpoint
promotion; numerical factor conditioning and estimator modification remain
deferred.**

The authoritative conceptual equations remain:

- `w_m(t) = p_H_m(t) + alpha_m * p_D_m(t)`
- `lambda_m = clip(w_m * q_m, epsilon_m, 1)`

The persistent-health and current-innovation pathways remain distinct.

Current numeric state:

- runtime health probabilities available: false;
- calibrated runtime health probabilities available: false;
- `alpha_m` selected: false;
- standardized-innovation definition selected: false;
- `q_m` definition selected: false;
- `epsilon_m` selected: false;
- factor-scale execution authorized: false;
- factor-information rescaling authorized: false;
- covariance inflation authorized: false;
- estimator factor modified: false.

No default values are invented for `alpha_m`, `q_m`, or `epsilon_m`.

Phase-9 suppression/recovery/status behavior remains outside this checkpoint.

Freeze artifacts:

- `manifests/trust_robot_phase8_factor_conditioning_software_freeze_v1.json`
  SHA-256 `9b4934404b97f1726b0acbd1e8b6eaa77bc2c3cb6ab6be38b4eb87a0800c337c`
- `tests/trust_robot/test_phase8_factor_conditioning_software_freeze.py`
  SHA-256 `39d9bb5d06ae54642b0516ded5632f9908330018fc34c92e259af866ddf1e9ee`
- `docs/audits/trust_robot/TRUST_ROBOT_PHASE8_FACTOR_CONDITIONING_SOFTWARE_FREEZE_V1.md`
  SHA-256 `9ae6c034f88d0691d283d2bb61d7ce1a3fa245af4bb207b710b69d701714744c`

Closure evidence:

- report SHA-256 `af74baecc4127c48cd1eb4be642d3c8e9428250c4b3f712a67823d0260842ccf`
- JSON SHA-256 `0218adda03ef707e06365a9fc07d2ef55717ac0d02b74c41833ee2ae793040b4`

After promotion, Phase-9 software architecture may proceed but must not assume
that a numerical Phase-8 factor scale exists.

## Phase 9 suppression/recovery/status contract V1

Status: **fail-closed hysteretic suppression/recovery and estimator-status
software architecture implemented locally; runtime decisions remain
disabled.**

The authoritative Phase-9 structure requires:

- unusable-probability entry threshold;
- consecutive-window entry requirement;
- lower recovery threshold;
- consecutive-window recovery requirement;
- remaining-factor-support assessment before hard suppression.

No numeric threshold or window count is selected.

No single-frame arbitrary hard suppression is allowed.

Remaining-factor-support sufficiency remains undefined and no minimum modality
count or observability test is invented.

When support is insufficient, the project requires a degraded or unavailable
estimator state rather than forcing a nominal estimate.

The degraded-versus-unavailable decision rule remains unselected.

Current state:

- Phase-8 numeric factor scale available: false;
- suppression entry threshold selected: false;
- entry consecutive-window count selected: false;
- recovery threshold selected: false;
- recovery consecutive-window count selected: false;
- remaining-support definition selected: false;
- suppression execution authorized: false;
- recovery execution authorized: false;
- estimator-status execution authorized: false.

Fallback appears elsewhere in broader project safety planning but is not
defined by the authoritative Phase-9 section. No fallback policy or threshold
is invented here.

Artifacts:

- `configs/trust_robot/phase9_suppression_recovery_status_contract_candidate_v1.json`
  SHA-256 `41be6fd118e99c2e990462c54aad44edba67d80b109ee4c756f6bd750546f1a1`
- `src/trust_robot/suppression_recovery_status.py`
  SHA-256 `38122e409875700f04a26b41420ed45485393ca1f9a35b89e3bc41a496fa0471`
- `tests/trust_robot/test_suppression_recovery_status.py`
  SHA-256 `21422eee6b518b30dd073f1911a4ecf9443e8e606b9ac88043fdfeeec5ae9edb`
- `docs/audits/trust_robot/TRUST_ROBOT_PHASE9_SUPPRESSION_RECOVERY_STATUS_CONTRACT_V1.md`
  SHA-256 `89b979eb930f65f58f9fdf259397532b10da7ef951449c9073ae712c2b5a4b27`

Frontier evidence:

- report SHA-256 `b2b7eedc7ccbd50af8ef2d05e66ccbccf0ee9c2f6ef5e9015f68537723c0ac24`
- JSON SHA-256 `3d3612e34bac2ef08469f0a4942ad9b49cb78b064fa6c1711766729ef9fb2be7`

Validation remains unopened and confirmation remains closed.
No ATE/RPE or final scoring is performed.

## Phase 9 suppression/recovery/status software freeze V1

Status: **hysteretic suppression/recovery and estimator-status software
architecture frozen for checkpoint promotion; runtime execution and numerical
operating points remain deferred.**

Authoritative Phase-9 structure:

- hard suppression cannot be a single-frame arbitrary decision;
- entry uses unusable probability;
- an entry threshold is required but remains unselected;
- a consecutive-window entry requirement is required but remains unselected;
- recovery requires a lower threshold, still unselected;
- recovery requires a consecutive-window requirement, still unselected;
- remaining factor support must be assessed before hard suppression.

Current runtime state:

- hard suppression executed: false;
- recovery executed: false;
- estimator-status execution authorized: false;
- remaining-support definition selected: false;
- degraded-versus-unavailable rule selected: false;
- unsupported observability guarantee claimed: false;
- nominal estimate forced under insufficient support: false.

Fallback remains outside the authoritative Phase-9 section and no fallback
policy or threshold is introduced.

Freeze artifacts:

- `manifests/trust_robot_phase9_suppression_recovery_status_software_freeze_v1.json`
  SHA-256 `9c84e85ed6789e01e6eb8d6d25cf40bcdec8b436af879cf54aa3e1b1df80122d`
- `tests/trust_robot/test_phase9_suppression_recovery_status_software_freeze.py`
  SHA-256 `bf76f8a41924a87d8e0faf3d9449b21aade29f4b86388e92e0d3b7632f8a2bb9`
- `docs/audits/trust_robot/TRUST_ROBOT_PHASE9_SUPPRESSION_RECOVERY_STATUS_SOFTWARE_FREEZE_V1.md`
  SHA-256 `c39fa9b3c927189c78c799a8592a4a8e624e531657d12261a94a00ee32e314b9`

Closure evidence:

- report SHA-256 `7bf66483f9cd1f5e1dd33a8490ed9c50c520fc1653707d0e2c4e28e6309ced8a`
- JSON SHA-256 `d442efa2e590a5d10852d1ae7b6759dbb32175eac66faf1d045c9ff3717fdb9f`

After promotion, Phase-10 software architecture may proceed but must not assume
that Phase-9 runtime suppression, recovery, or estimator-status execution is
available.

## Phase 10 controlled-fault / causal-ablation contract V1

Status: **fail-closed same-backbone RQ1/RQ2 controlled-fault and causal-ablation
software architecture implemented locally; experiment execution remains
disabled.**

Phase-10 scope is `Causal ablations and controlled faults`, with
`Same-backbone RQ1/RQ2 evidence`.

Current state:

- same-backbone operational definition selected: false;
- ablation variants selected: false;
- RQ1 proxy reliability definition selected: false;
- RQ1 executable: false;
- RQ2 executable: false;
- numeric fault severity selected: false;
- severity grid selected: false;
- attack budget selected: false;
- fault schedule selected: false;
- partition seed schedule selected: false;
- controlled fault execution authorized: false;
- physical fault execution authorized: false.

The frozen Phase-3 native mechanisms are named as:

- `EVENT_GAP`;
- `EVENT_REPEAT`;
- `TIMESTAMP_STEP_SHIFT`.

They are bound as admissible native mechanism identities only. No Phase-10
fault execution occurs.

Synthetic corruption truth is not promoted to a health label, physical-fault
proof, or runtime causal evidence.

The Phase-5 controlled-availability interface is retained as a potential
evidence interface, but it is not an accepted health-supervision source and
contains zero real health labels.

Validation remains unopened and confirmation remains closed.

No ATE/RPE or final scoring is performed.

Artifacts:

- `configs/trust_robot/phase10_controlled_fault_ablation_contract_candidate_v1.json`
  SHA-256 `7739dfd406635ec55cce54a0c58af02f1da427d768d41361232aa3ac2546eb99`
- `src/trust_robot/controlled_fault_ablations.py`
  SHA-256 `4322842cce824ad933c4ac0388142408a986877ac743a367a31251b7e7bd83b4`
- `tests/trust_robot/test_controlled_fault_ablations.py`
  SHA-256 `fbaebd2618b368d09d17eeb8ad11cad930135cacaa048291af36bbd1b3222586`
- `docs/audits/trust_robot/TRUST_ROBOT_PHASE10_CONTROLLED_FAULT_ABLATION_CONTRACT_V1.md`
  SHA-256 `224740abed83226c1c79946a780a3069d99099408047d2331f00411f4aad3ad2`

Scope-resolution evidence:

- report SHA-256 `960f298aa8159ad4c4a0a57c9b7fa2a77e7b5e99c43d4be9c2f21ead7a955eb3`
- JSON SHA-256 `ab5655fd1f2844dcad76c100d36d48085c65ad019aa9a024a77ebe61d2855ae7`

RQ1/RQ2 basis evidence:

- report SHA-256 `d3939b9f3af7f90cfc16f715b09562cac99215e94e4cc2162c24368b88ea5ef8`
- JSON SHA-256 `64e13c8e7b015aadbe43cecbfeaa5a9b7fde3193810a7fc728875cfed2f1923a`

## Phase 10 controlled-fault / causal-ablation software freeze V1

Status: **same-backbone RQ1/RQ2 controlled-fault and causal-ablation software
architecture frozen for checkpoint promotion; empirical experiment execution
remains deferred.**

Current state:

- same-backbone operational definition selected: false;
- ablation variants selected: false;
- RQ1 proxy reliability definition selected: false;
- RQ1 executable: false;
- RQ1 answer available: false;
- RQ2 executable: false;
- RQ2 answer available: false;
- new fault family selected: false;
- numeric fault severity selected: false;
- severity grid selected: false;
- attack budget selected: false;
- fault schedule selected: false;
- partition seed schedule selected: false;
- controlled-fault execution authorized: false;
- physical-fault execution authorized: false.

Frozen native Phase-3 identities remain:

- `EVENT_GAP`;
- `EVENT_REPEAT`;
- `TIMESTAMP_STEP_SHIFT`.

Synthetic corruption truth remains distinct from health labels, physical-fault
proof, and runtime causal evidence.

Validation remains unopened and confirmation remains closed.

Freeze artifacts:

- `manifests/trust_robot_phase10_controlled_fault_ablation_software_freeze_v1.json`
  SHA-256 `23a69b642fc0e4bd878c7323aeb2975f4eba4e65e6b017ff78f219019ce2a470`
- `tests/trust_robot/test_phase10_controlled_fault_ablation_software_freeze.py`
  SHA-256 `340769212254269fae9769c0cc5ca3a4d2e345932751ac95e46d550e02e01ffb`
- `docs/audits/trust_robot/TRUST_ROBOT_PHASE10_CONTROLLED_FAULT_ABLATION_SOFTWARE_FREEZE_V1.md`
  SHA-256 `1609c3fb3c54a02f68550c42995fe04b456d93dee6c16ecf96d3405ea55ba766`

Closure evidence:

- report SHA-256 `c570b2600b4bdb43d5db7b0a31614c54c8f0d609476b2fe16b7f99c41df96772`
- JSON SHA-256 `a2b9a3d02e545245a17341549c291e80db4698887a5f682f65a6d4bdb4ebd1b2`

After promotion, Phase-11 software architecture may proceed but must not assume
that Phase-10 experiments were executed or that RQ1/RQ2 answers exist.

## Phase 11 cross-dataset compatibility contract V1

Status: **fail-closed cross-dataset compatibility software architecture
implemented locally; secondary-dataset readiness and evaluation remain
disabled.**

Phase-11 scope is `Cross-dataset evaluation` with
`Generalization/stress evidence`.

Dataset-role boundary:

- M2DGR remains the primary development benchmark;
- EuRoC is project-declared for camera-IMU controlled testing and
  different-platform comparison;
- TUM-VI is project-declared for supplementary camera-IMU cross-dataset stress
  testing;
- proposal-level role is not local readiness;
- proposal-level role is not evaluation authorization.

Current readiness:

- EuRoC local readiness verified: false;
- EuRoC local path present: false;
- TUM-VI local readiness verified: false;
- TUM-VI local path present: false;
- secondary dataset selected for evaluation: false;
- secondary dataset data opened: false.

Compatibility:

- proposal-level common camera/IMU overlap named: true;
- proposal overlap proves modality compatibility: false;
- modality compatibility verified: false;
- reference compatibility verified: false;
- timing semantics verified: false;
- frame semantics verified: false;
- cross-dataset adapter implemented: false.

Transfer/evaluation:

- secondary dataset split selected: false;
- cross-dataset recalibration authorized: false;
- model refit authorized: false;
- threshold refit authorized: false;
- probability-calibration refit authorized: false;
- alignment selected: false;
- association selected: false;
- interpolation selected: false;
- cross-dataset evaluation authorized: false.

Validation remains unopened and confirmation remains closed.

No ATE/RPE or final scoring is performed.

Artifacts:

- `configs/trust_robot/phase11_cross_dataset_compatibility_contract_candidate_v1.json`
  SHA-256 `45e4ed026fb0555e2be8ff7498ec3289ca99e51fd38bf066a26f530d4359e7bf`
- `src/trust_robot/cross_dataset_compatibility.py`
  SHA-256 `93e2e8d8879e346b41bc9bd19daf34c04f88f7ad1e55dace9f3e189be5be63cc`
- `tests/trust_robot/test_cross_dataset_compatibility.py`
  SHA-256 `909e1f0e6e973c35bc0ddce1edf860283ec5073699c12e5ddd35f9090dc51f65`
- `docs/audits/trust_robot/TRUST_ROBOT_PHASE11_CROSS_DATASET_COMPATIBILITY_CONTRACT_V1.md`
  SHA-256 `d0102ea90cf44886eb1b5e5269e8fb7cde3d124c73a630f29becc4a8c52a2561`

Frontier evidence:

- report SHA-256 `1fd1a54297c0915aac9b57d91b464b9748a52f93b6cd32aee17aec73009d8b75`
- JSON SHA-256 `5b8e55c7deff85fea4c9e0394c8504709802f9ac9a4cc5764481ca160b1e5eeb`

Dataset-role evidence:

- report SHA-256 `c87c02ebe731be0598e2b38200eaa47af7a72b5f01a0fbe2409ce77cbfd81df1`
- JSON SHA-256 `72b194c713893dac372f83d8c44c3ab153a64ba000f655baebf964b356f6194b`

## Phase 11 cross-dataset compatibility software freeze V1

Status: **cross-dataset compatibility software architecture frozen for
checkpoint promotion; secondary-dataset access and empirical evaluation remain
deferred.**

Dataset roles:

- M2DGR remains the primary development benchmark;
- EuRoC remains declared for camera-IMU controlled testing and
  different-platform comparison;
- TUM-VI remains declared for supplementary cross-dataset stress testing.

Current state:

- EuRoC local readiness verified: false;
- EuRoC evaluation available: false;
- TUM-VI local readiness verified: false;
- TUM-VI evaluation available: false;
- secondary dataset selected: false;
- secondary dataset data opened: false;
- modality compatibility verified: false;
- reference compatibility verified: false;
- cross-dataset adapter implemented: false;
- timing semantics verified: false;
- frame semantics verified: false;
- secondary dataset split selected: false;
- cross-dataset recalibration authorized: false;
- model refit authorized: false;
- threshold refit authorized: false;
- probability-calibration refit authorized: false;
- cross-dataset evaluation authorized: false.

Freeze artifacts:

- `manifests/trust_robot_phase11_cross_dataset_compatibility_software_freeze_v1.json`
  SHA-256 `842860e2fb17079853f6a07877b4b717deb16c5425bdcf3aefaa9314294bbc61`
- `tests/trust_robot/test_phase11_cross_dataset_compatibility_software_freeze.py`
  SHA-256 `b36e99715b6c4ce6ca4f2025898821be35b902a91fababbad4df694c01bd178d`
- `docs/audits/trust_robot/TRUST_ROBOT_PHASE11_CROSS_DATASET_COMPATIBILITY_SOFTWARE_FREEZE_V1.md`
  SHA-256 `6ab092f9e23e548825ae1caa9cb1c256eed627990747d34c5eb8c99f22efc168`

Closure evidence:

- report SHA-256 `e90a796b9b08f1ee95d24ae42367c5f4ac7a644f684f597ee32c4ce24808bd0e`
- JSON SHA-256 `c007b99915eb57488f193ac309d5a61544f05842c8dca0fa545fdf38aaf1072b`

After promotion, Phase-12 software architecture may proceed but must not assume
that Phase-11 cross-dataset evaluation, EuRoC evaluation, or TUM-VI evaluation
is available.

## Phase 12 threat-model contract V1

Status: **fail-closed explicit attack / threat-model software architecture
implemented locally; no attack protocol is instantiated and no attack
execution is authorized.**

Phase-12 scope is `Explicit attack evaluation` with
`Threat-model-bounded RQ3 evidence`.

Planned attack taxonomy:

- false-data injection / spoofing;
- bounded adversarial image or point-cloud perturbation;
- replay;
- timestamp manipulation;
- coordinated two-modality corruption;
- adaptive white-box digital evasion.

These are planned taxonomy identities, not executable protocols.

Every eventual attack protocol must bind attacker knowledge, writable
modalities, writable fields, duration, magnitude/rate/norm budget, objective,
protected-source assumptions, and identifiability assumptions.

Current state:

- instantiated attack protocol count: 0;
- threat model selected: false;
- attacker knowledge model selected: false;
- writable modalities selected: false;
- writable fields selected: false;
- attack objective selected: false;
- protected-source assumptions selected: false;
- identifiability assumptions selected: false;
- attack family selected: false;
- attack target pipeline layer selected: false;
- attack duration selected: false;
- attack budget selected: false;
- attack magnitude/rate/norm selected: false;
- attack schedule selected: false;
- attack threshold selected: false;
- single-sensor operational definition selected: false;
- coordinated operational definition selected: false;
- adaptive operational definition selected: false;
- RQ3 executable: false;
- RQ3 answer available: false;
- synthetic attack execution authorized: false;
- physical attack execution authorized: false;
- attack evaluation authorized: false.

Fault, environmental degradation, and attack evidence remain distinct.

Phase-3 taxonomy identity does not establish Phase-12 attack execution.
Phase-10 controlled-fault evidence does not establish Phase-12 attack evidence.

Validation remains unopened and confirmation remains closed.

No ATE/RPE or final scoring is performed.

Artifacts:

- `configs/trust_robot/phase12_threat_model_contract_candidate_v1.json`
  SHA-256 `b81f4fa6ddeac61775fdc017dc70effa875ceeffe4c017c7b57489f0aa431e73`
- `src/trust_robot/attack_threat_model.py`
  SHA-256 `03b7ebcc468b8b798f9240e8105ceec88b3c2b919a5bc78dad6d6554617d5983`
- `tests/trust_robot/test_attack_threat_model.py`
  SHA-256 `e663bd9fb3cedd0a80615bc3844c4a91af8ebc4b41f6e0475d18bf2c32ad5bdc`
- `docs/audits/trust_robot/TRUST_ROBOT_PHASE12_THREAT_MODEL_CONTRACT_V1.md`
  SHA-256 `2fe029e5ee3d0d8310f72d00e68d0d4fff214ea7766fd0a68d3e582e7a0ebc7c`

Frontier evidence:

- report SHA-256 `5fca5b0e4d9822381190a98faa14abeffa9247a2e400c3225fc7bc844a3eb959`
- JSON SHA-256 `9944764551a402cad59b3c7bb1c26b29d08ab9bde3250b6ea45eb7b484033da9`

Attack-protocol basis evidence:

- report SHA-256 `4eb113eab4a8c4290922ec903afaad6b046c8853d2a903c218ee222c467cbd78`
- JSON SHA-256 `409a9c94dbfcb6d998e7d9f974426c7b7b58bc25e7908c66ec8e1a134873b00c`

## Phase 12 threat-model software freeze V1

Status: **explicit threat-model / attack-evaluation software architecture
frozen for checkpoint promotion; attack-protocol instantiation and empirical
attack evaluation remain deferred.**

Current state:

- planned attack taxonomy bound: true;
- planned attack identity count: 6;
- mandatory protocol field count: 8;
- instantiated attack protocol count: 0;
- threat model selected: false;
- attacker knowledge model selected: false;
- writable modalities selected: false;
- writable fields selected: false;
- attack objective selected: false;
- protected-source assumptions selected: false;
- identifiability assumptions selected: false;
- attack family selected: false;
- attack target pipeline layer selected: false;
- attack duration selected: false;
- attack budget selected: false;
- attack magnitude/rate/norm selected: false;
- attack schedule selected: false;
- attack threshold selected: false;
- single-sensor operational definition selected: false;
- coordinated operational definition selected: false;
- adaptive operational definition selected: false;
- RQ3 executable: false;
- RQ3 answer available: false;
- synthetic attack execution authorized: false;
- physical attack execution authorized: false;
- attack evaluation authorized: false;
- attack-resilience claim authorized: false;
- source-attribution claim authorized: false.

Fault, environmental degradation, and attack evidence remain distinct.

Phase-3 taxonomy identity does not establish a Phase-12 executable attack
protocol.

Phase-10 controlled-fault truth does not establish Phase-12 attack truth.

Validation remains unopened and confirmation remains closed.

No ATE/RPE or final scoring is performed.

Freeze artifacts:

- `manifests/trust_robot_phase12_threat_model_software_freeze_v1.json`
  SHA-256 `bf95425b257d486510c16cdea1d2907d64480bc00a6fe07b088316c4333bbf05`
- `tests/trust_robot/test_phase12_threat_model_software_freeze.py`
  SHA-256 `be86a3b2d1e57553cbbcfbff2bcff3fe347177ec46f8ef7a845694360b79368a`
- `docs/audits/trust_robot/TRUST_ROBOT_PHASE12_THREAT_MODEL_SOFTWARE_FREEZE_V1.md`
  SHA-256 `c12f3453eafec187fdb0a5a83bbcd7ff81579eaa030e6a5b4d43da872b8a6240`

Closure evidence:

- report SHA-256 `75ecde459bb64245a4a61bc49eb33244eb0bab9fa375c6864ec38a10033f928a`
- JSON SHA-256 `53e84343a7ae9f6bf6608c675661d183b359943061f6aed7f711cc8309244b54`

After promotion, Phase-13 software architecture may proceed but must not assume
that Phase-12 attack evaluation was executed, that RQ3 was answered, or that
an attack-resilience/source-attribution claim is available.

## Phase 13 resource-evaluation contract V1

Status: **fail-closed resource-evaluation software architecture implemented
locally; concrete measurement policy and empirical resource claims remain
deferred.**

Authoritative cost views:

- complete-system cost;
- incremental trust-layer overhead.

Required future resource evidence:

- mean latency;
- P95 latency;
- deadline misses;
- throughput;
- processor utilization where measurable;
- peak memory;
- storage;
- average power;
- peak power;
- energy per update or trajectory.

Required future measurement metadata:

- hardware versions;
- software versions;
- power/clock mode;
- sensor rates;
- estimator window size;
- warm-up policy;
- measurement method.

Current state:

- exact latency definition selected: false;
- timing clock source selected: false;
- deadline definition selected: false;
- throughput definition selected: false;
- processor-utilization measurement selected: false;
- peak-memory measurement selected: false;
- storage scope selected: false;
- power measurement method selected: false;
- energy measurement method selected: false;
- update-vs-trajectory energy scope selected: false;
- measurement scope selected: false;
- warm-up policy selected: false;
- repetition policy selected: false;
- aggregation policy selected: false;
- hardware profile frozen: false;
- software runtime profile frozen: false;
- power/clock mode frozen: false;
- sensor-rate profile frozen: false;
- estimator window size frozen: false;
- measurement method frozen: false;
- CPU-specific metric selected: false;
- GPU-specific metric selected: false;
- real-time acceptance threshold selected: false;
- resource measurement execution authorized: false;
- resource claim authorized: false;
- RQ4 resource answer available: false.

Historical \`RUNTIME_RESOURCE_OVERHEAD_PROTOCOL_V1\` exists but is not adopted as
TRUST-ROBOT Phase-13 policy.

Historical warm-up counts, repetition counts, timing clock, median-primary
statistic, RSS/tracemalloc policy, latency targets, and reference-host results
remain non-adopted.

Reference-host evidence may not be relabeled as onboard-robot or STM32
resource evidence.

Target-specific claims require target-specific measurement.

The closed-loop safety component of RQ4 remains deferred to Phase 14.

Validation remains unopened and confirmation remains closed.

No ATE/RPE or final scoring is performed.

Artifacts:

- `configs/trust_robot/phase13_resource_evaluation_contract_candidate_v1.json`
  SHA-256 `999034456e4ab8eb62e36f08e769e670a8777d52f60876856f1bdc8caa71040b`
- `src/trust_robot/resource_evaluation.py`
  SHA-256 `409b84eccba8d89009c5311ba4727ec3479a7bc55fc2881dd28b72b5adfb9620`
- `tests/trust_robot/test_resource_evaluation.py`
  SHA-256 `76371bbb25b84053be2263a659067b0d3a24017fc9345fc8f71bf6f6239739ae`
- `docs/audits/trust_robot/TRUST_ROBOT_PHASE13_RESOURCE_EVALUATION_CONTRACT_V1.md`
  SHA-256 `ecd20f6b6689982f7075c4fe2670c58b5eba7475cd77324d4429d525520cffad`

Frontier evidence:

- report SHA-256 `4120763b090e7b2e3a1d0bdf92aa55323abb675e261d07ebde94f27f6268077b`
- JSON SHA-256 `71a8ea7d900a72780a06c9d1d174c2a43df79dd462d6064279c56b97cc075bdb`

Resource-measurement basis evidence:

- report SHA-256 `222661b5977a371d11d332f9e53d2ea147d87791d8f8db4d8f47f29b4a92e5c1`
- JSON SHA-256 `7eca5a47174e29f77b739bcc6a8552b29940ac98e56eedca11e713cb87062147`

## Phase 13 resource-evaluation software freeze V1

Status: **resource-evaluation software architecture frozen for checkpoint
promotion; concrete measurement policy and empirical resource evidence remain
deferred.**

Frozen requirements:

- cost views: complete-system cost and incremental trust-layer overhead;
- ten resource evidence families;
- seven mandatory future measurement metadata categories.

Current state:

- exact latency definition selected: false;
- timing clock source selected: false;
- deadline definition selected: false;
- throughput definition selected: false;
- processor-utilization measurement selected: false;
- peak-memory measurement selected: false;
- storage scope selected: false;
- power measurement method selected: false;
- energy measurement method selected: false;
- warm-up policy selected: false;
- repetition policy selected: false;
- aggregation policy selected: false;
- hardware profile frozen: false;
- software runtime profile frozen: false;
- power/clock mode frozen: false;
- sensor-rate profile frozen: false;
- estimator-window size frozen: false;
- measurement method frozen: false;
- CPU/GPU-specific metrics selected: false;
- real-time acceptance threshold selected: false;
- historical resource protocol adopted: false;
- historical reference-host results adopted: false;
- resource measurement execution authorized: false;
- resource claim authorized: false;
- RQ4 resource answer available: false.

Reference-host evidence is not onboard-robot evidence.

Host/native evidence is not STM32 evidence.

Target-specific resource claims require target-specific measurements.

The guarded closed-loop safety component of RQ4 remains deferred to Phase 14.

Validation remains unopened and confirmation remains closed.

No ATE/RPE or final scoring is performed.

Freeze artifacts:

- `manifests/trust_robot_phase13_resource_evaluation_software_freeze_v1.json`
  SHA-256 `18e8ae494281a3d20567aa7e7404909ccccc832c7426cf0b0ba5ff683f9ffac8`
- `tests/trust_robot/test_phase13_resource_evaluation_software_freeze.py`
  SHA-256 `262812bdaad349a6b8c4b08fe45e8923526f4764bd4260b740afed4f0dc9c71a`
- `docs/audits/trust_robot/TRUST_ROBOT_PHASE13_RESOURCE_EVALUATION_SOFTWARE_FREEZE_V1.md`
  SHA-256 `dd87afa202bb9d26e08b32b0f1d9471f4de8569007bd8a274f9939344b58ac1b`

Closure evidence:

- report SHA-256 `09cec194a9db777f8175f6ae32651b042abb39a983eb1c74ce4cc788a49597cb`
- JSON SHA-256 `6dc463bc22e7dc80dfed37ff12c814e53f78ab7e4fc3582417a72c7a3dcc05eb`

After promotion, Phase-14 software architecture may proceed but must not assume
that Phase-13 resource measurement was executed, that onboard resource
constraints were verified, that fallback thresholds were frozen, or that the
RQ4 resource component was answered.

## Phase 14 supervisory / physical-integration contract V1

Status: **fail-closed guarded supervisory / physical-integration software
architecture implemented locally; robot action semantics and empirical
physical testing remain deferred.**

Authoritative supervisor-input identities:

- calibrated modality-health probabilities;
- estimator covariance/status;
- tracking availability;
- residual consistency;
- solver validity;
- frozen validation-selected thresholds.

Planned policy-comparison identities:

- nominal continuation;
- always-stop;
- health-triggered policy;
- oracle-health policy.

These names do not define robot commands and do not select an operational
policy.

Current state:

- learned health model is robot controller: false;
- separate rule-based supervisory layer required: true;
- all candidate supervisor inputs runtime verified: false;
- operational supervisory policy selected: false;
- controller interface selected: false;
- robot action mapping selected: false;
- safe-stop definition present: false;
- emergency definition present: false;
- stopping-distance definition present: false;
- control-command semantics present: false;
- fallback threshold selected: false;
- safety threshold selected: false;
- physical-test protocol selected: false;
- physical-test partition instantiated: false;
- actual quadruped identity frozen: false;
- physical compute hardware frozen: false;
- physical sensor suite frozen: false;
- physical calibration frozen: false;
- physical synchronization frozen: false;
- physical reference instrumentation frozen: false;
- physical controller semantics verified: false;
- proprioception verified: false;
- robot integration execution authorized: false;
- physical test execution authorized: false;
- closed-loop safety measurement authorized: false;
- closed-loop safety claim authorized: false;
- guarded physical test executed: false;
- RQ4 closed-loop safety answer available: false;
- full RQ4 answer available: false.

The eventual primary physical platform remains the local quadruped and the
provisional dataset identity remains `KIOS_QUADRUPED`, whose current local
readiness is `not_collected`.

Final held-out physical data may not select models, calibration, thresholds,
fault/attack operating points, fallback policy, or safety operating points.

Phase-9 runtime suppression/recovery/status execution remains unavailable.

Phase-13 empirical resource measurements and verified onboard constraints
remain unavailable.

Phase-5 acquisition/filesystem safety and inherited IMU runtime safety are not
adopted as Phase-14 robot supervisory semantics.

Validation remains unopened and confirmation remains closed.

No ATE/RPE or final scoring is performed.

Artifacts:

- `configs/trust_robot/phase14_supervisory_physical_integration_contract_candidate_v1.json`
  SHA-256 `d5bfc1cd75a2a2dfcc41954856b10163ca9c6f8f66f44b454c88a037269907e3`
- `src/trust_robot/supervisory_physical_integration.py`
  SHA-256 `e0a89e0e69bb8c58d7e754569a341010543b7dc6e674129995f2df7c8f7eb9c1`
- `tests/trust_robot/test_supervisory_physical_integration.py`
  SHA-256 `cbcf423ff43140b4b68cab1826b5b359e92b4a61c0561d428749091802fa48c1`
- `docs/audits/trust_robot/TRUST_ROBOT_PHASE14_SUPERVISORY_PHYSICAL_INTEGRATION_CONTRACT_V1.md`
  SHA-256 `3635e8fbc941edebe074e4115c8ca82ccf1d68f8f0388ec89ff467a481b75410`

Frontier evidence:

- report SHA-256 `34e307d58a03a612c95caece4cb9b5f7ce1670b333e8c66aba3543256e626942`
- JSON SHA-256 `ee4e7be9b62fe4a2126f1f7758b837ff031928ec00d9867efc8b800109a96627`

Supervisory-basis evidence:

- report SHA-256 `3c139828a42d4607136c77f04d1df60adf0a422544f98e7d51493f9e7c8c89d1`
- JSON SHA-256 `88d1378dffa70ce512ae7d84b59f3e15e11cef11a270b94ff1a931415bb60899`

After a future Phase-14 checkpoint, Phase-15 software preparation may proceed,
but final confirmation execution remains closed until all upstream empirical
obligations and permitted selections are complete and frozen.

## Phase 14 supervisory / physical-integration software freeze V1

Status: **guarded supervisory / physical-integration software architecture
frozen for checkpoint promotion; empirical physical execution remains
deferred.**

Frozen architectural requirements:

- the learned health model is not the robot controller;
- the safety response is a separate rule-based supervisory layer;
- six authoritative candidate supervisor-input identities are bound;
- four planned policy-comparison identities are bound;
- physical experiments must remain guarded and progressively validated;
- final held-out physical data cannot select model/calibration/threshold or
  safety operating-point parameters.

Current state:

- all candidate supervisor inputs runtime verified: false;
- operational policy selected: false;
- controller interface selected: false;
- robot action mapping selected: false;
- safe-stop semantics selected: false;
- emergency semantics selected: false;
- stopping-distance metric selected: false;
- fallback threshold selected: false;
- safety threshold selected: false;
- actual physical robot identity frozen: false;
- physical compute hardware frozen: false;
- physical sensor suite frozen: false;
- physical calibration frozen: false;
- physical synchronization frozen: false;
- physical reference instrumentation frozen: false;
- physical-test protocol selected: false;
- physical-test partition instantiated: false;
- robot integration execution authorized: false;
- physical test execution authorized: false;
- closed-loop safety measurement authorized: false;
- closed-loop safety claim authorized: false;
- RQ4 closed-loop safety answer available: false;
- full RQ4 answer available: false;
- final confirmation execution authorized: false.

The eventual platform role remains `local_quadruped_robot`; the provisional
dataset identity remains `KIOS_QUADRUPED`; local readiness remains
`not_collected`.

Phase-9 runtime actions are not assumed.

Phase-13 resource measurements/onboard constraints are not assumed.

Validation remains unopened and confirmation remains closed.

No ATE/RPE or final scoring is performed.

Freeze artifacts:

- `manifests/trust_robot_phase14_supervisory_physical_integration_software_freeze_v1.json`
  SHA-256 `65bc22d6bd627c13edc20f9d671f59dc557e24b2de9f0560580b2354ca1d3d7d`
- `tests/trust_robot/test_phase14_supervisory_physical_integration_software_freeze.py`
  SHA-256 `224e885ce18a8da5252fb3c64e3de4f3186f80b5e1202a78a8234f0e8ee26351`
- `docs/audits/trust_robot/TRUST_ROBOT_PHASE14_SUPERVISORY_PHYSICAL_INTEGRATION_SOFTWARE_FREEZE_V1.md`
  SHA-256 `0b33b9c23aee31eae4aabab743e0f0aca3bee243e1cade8289f1096ee7e91c1e`

Closure evidence:

- report SHA-256 `646a5428ad293fdad659234ad61e3c3edd6f5c7e6e21515a9540c3a4a48df3a7`
- JSON SHA-256 `09b7a5e571049a618927606cf58ca5aa31fd27751880703c057be002d62fc1a5`

After promotion, Phase-15 software preparation may proceed, but confirmation
execution remains closed until the deferred empirical obligations from
Phases 5 through 14 are satisfied and all permitted selections are frozen.

## Software Evidence Completion Track — SE0 plan V1

Status: **SE0–SE10 software evidence-completion governance implemented
locally; SE1 deterministic multimodal replay is the next execution stage.**

Purpose:

- complete deferred empirical obligations from Phases 5–14 using recorded
  datasets as virtual sensors;
- train, validate and test without partition leakage;
- obtain quantitative software-level health, robustness, localization and
  resource evidence before physical hardware integration;
- keep final confirmation closed until all permitted choices are frozen.

Frozen M2DGR split:

- TRAIN: 22 trajectories;
- VALIDATION/CALIBRATION: 7 trajectories;
- CONFIRMATION/TEST: 7 trajectories;
- trajectory overlap: none.

Current execution state:

- SE0 readiness audit: complete;
- SE0 plan implementation: complete locally;
- SE1 replay execution: not started;
- model training: not executed;
- validation selection: not executed;
- probability calibration: not executed;
- threshold selection: not executed;
- end-to-end numerical runtime: not executed;
- controlled fault/ablation experiments: not executed;
- attack experiments: not executed;
- cross-dataset evaluation: not executed;
- TRUST-ROBOT resource benchmark: not executed;
- confirmation opened: false;
- ATE/RPE computed: false;
- final score computed: false.

Health-supervision protections:

- availability is not a health label;
- clean data is not automatically healthy;
- synthetic corruption identity is not automatically a health label;
- final localization error may not define health supervision.

SE1 may use TRAIN to implement deterministic virtual-sensor replay.

SE1 may not open validation or confirmation, train the health model, select
scientific thresholds, or compute final localization scores.

SE9 remains closed until all confirmation-visible choices and evaluation rules
are frozen.

Software-level success will not be relabeled as physical robot evidence.

Artifacts:

- `configs/trust_robot/software_evidence_completion_plan_v1.json`
  SHA-256 `5624c4b6e28172859122abec121735314d317d613bded01a0ce18501ea715cdb`
- `src/trust_robot/software_evidence_completion.py`
  SHA-256 `35c2a01e72bbd4ca74e99bbe4a2652a3c63af70e6b2092a56220de68520dd458`
- `tests/trust_robot/test_software_evidence_completion.py`
  SHA-256 `d1fe55fc862c5e2a30926d4dafee33bb77bde999853efddf1118de7dede395cf`
- `docs/TRUST_ROBOT_SOFTWARE_EVIDENCE_COMPLETION_PLAN.md`
  SHA-256 `c6803fa0c08c5f2117e702d075db9cb5dde8190d990f480f0f783a4c9d963ab4`
- `docs/audits/trust_robot/TRUST_ROBOT_SE0_SOFTWARE_EVIDENCE_COMPLETION_PLAN_V1.md`
  SHA-256 `95260e519ee5af50627f8a69119fca681ecff55f5a0420fce20a2eec3c82ca4d`

SE0 readiness evidence:

- report SHA-256 `152bad0555eab25c98fed494739479f1c2a33aa2fa75b9d8bff7665f84146496`
- JSON SHA-256 `dbdf2fbde4ae6aed2f0867fbca8587f8fef64bda8ceb056566c2926aeb662b20`

## SE0 software evidence completion plan freeze V1

Status: **software evidence-completion governance plan frozen for checkpoint
promotion; SE1 deterministic TRAIN-only replay may proceed after promotion.**

Frozen stage order:

`SE0 -> SE1 -> SE2 -> SE3 -> SE4 -> SE5 -> SE6 -> SE7 -> SE8 -> SE9 -> SE10`

Current boundary:

- TRAIN trajectories: 22;
- VALIDATION_CALIBRATION trajectories: 7;
- CONFIRMATION_TEST trajectories: 7;
- partition overlap: false;
- SE1 TRAIN access: true;
- SE1 validation access: false;
- SE1 confirmation access: false;
- SE1 model training authorized: false;
- SE1 feature selection authorized: false;
- SE1 threshold selection authorized: false;
- SE1 probability calibration authorized: false;
- SE1 ATE/RPE authorized: false;
- SE1 final scoring authorized: false;
- SE9 confirmation execution authorized: false.

Clean data is not automatically a healthy label.

Synthetic corruption identity is not automatically a health label.

SE2 health-supervision resolution is required before SE4 model training.

Confirmation remains closed and cannot select model, features, calibration,
thresholds, fault severity, attack budgets, alignment, association,
interpolation, evaluation intervals, or metric operating choices.

Freeze artifacts:

- `manifests/trust_robot_se0_software_evidence_completion_plan_freeze_v1.json`
  SHA-256 `62838e41f0ffb47c02c517ac302a127b4cc2aba13ef86b7979c4d1e92bc20b33`
- `tests/trust_robot/test_se0_software_evidence_completion_plan_freeze.py`
  SHA-256 `1995ecb7ad90587c67a570e19867b67f82dd271005e6a0e34ad76dc3060de8c1`
- `docs/audits/trust_robot/TRUST_ROBOT_SE0_SOFTWARE_EVIDENCE_COMPLETION_PLAN_FREEZE_V1.md`
  SHA-256 `d9fa287dc345dbb5cc91ed36503ac76de9f662b7e1518c63a99dab1306c69844`

Closure evidence:

- report SHA-256 `72ffdd32cbbecb664cf0be6ac97c008a4884a2fe6e4dbe427ec9ec6eded91970`
- JSON SHA-256 `e804f0cb019ed96b15f3bda0c63efadd0c0fdf6dc666ecc563973ee344d1d0a9`

After promotion, SE1 may implement deterministic multimodal dataset replay
against TRAIN only. It may not perform scientific model/feature/threshold
selection or access VALIDATION_CALIBRATION or CONFIRMATION_TEST.


## SE1 deterministic multimodal dataset replay freeze V1

Status: **SE1 deterministic TRAIN-only virtual-sensor replay complete and frozen locally for checkpoint promotion.**

The exact frozen 22-trajectory M2DGR TRAIN partition was replayed using
`rosbags.highlevel.AnyReader` without opening validation or confirmation.

The completed empirical run contains:

- 22 TRAIN trajectories;
- 2,907,971 selected replay messages;
- 103,450,808,700 serialized replay payload bytes;
- 20 four-stream trajectories;
- 2 reduced-stream trajectories: `street_010` and `street_09`.

The two reduced trajectories contain only HandsFree IMU and Velodyne among the
SE1-supported replay streams. Camera and D435i IMU remain absent and are not
fabricated.

The replay preserves reader emission order, per-stream message order, raw
serialized payload identity, source topic/modality identity, bag provenance,
bag record time as transport provenance, and directly represented header
timestamps when structurally present.

Bag record time is not physical capture-time proof.

Header timestamp presence is not shared-clock or synchronization proof.

No timestamp sorting, synchronization fitting, fixed offset, interpolation,
reference association, health labelling, feature selection, model training,
probability calibration, threshold selection, ATE/RPE, or final scoring was
performed.

Availability is not a health label.

Missing measurement is not a zero feature vector.

Clean data is not automatically healthy.

Synthetic corruption identity is not automatically a health label.

Final localization error may not define health supervision.

Empirical replay bindings:

- candidate contract file SHA-256:
  `866059a3f15a05b21f76acc9fafffa531aa460f55c4e4447a04ff2ad4b2ca53d`
- run manifest file SHA-256:
  `3fcb3ce8a6698545be7b18774d3cf666bb3a8174e08321ca3a868ecd9f351d0f`
- run manifest content SHA-256:
  `1eeb1704a16631e9a47f4263a659ffcbdd6c8e3e6496f1d1f7924fb6559f7e37`
- SUCCESS file SHA-256:
  `4ec6ec05aa51188d1aa2938815f3da2c4e817b2f046bcd1187010b9c2a6d9d07`
- aggregate trajectory-record SHA-256:
  `28812bc95af309184aaa3530d4fbfa5ebcc83713589f81b143047cf1e544be3d`

Repository implementation:

- `src/trust_robot/deterministic_multimodal_dataset_replay.py`
- `src/trust_robot/deterministic_multimodal_dataset_replay_run.py`
- `scripts/trust_robot/run_se1_deterministic_multimodal_dataset_replay_v1.py`
- `tests/trust_robot/test_deterministic_multimodal_dataset_replay.py`
- `tests/trust_robot/test_deterministic_multimodal_dataset_replay_run.py`

Freeze artifacts:

- `manifests/trust_robot_se1_deterministic_multimodal_dataset_replay_freeze_v1.json`
  SHA-256 `46224af94a07787883b9bd76e0df88cb43f60e834484add04b64933afdbafb02`
- `tests/trust_robot/test_se1_deterministic_multimodal_dataset_replay_freeze.py`
  SHA-256 `5c8968e1999583eac802e7e19ed6553f7ce1f1e668936c6c6d12e885fb875499`
- `docs/audits/trust_robot/TRUST_ROBOT_SE1_DETERMINISTIC_MULTIMODAL_DATASET_REPLAY_FREEZE_V1.md`
  SHA-256 `ac525bd4ee6471ffc29efeb48e98ab476df2ce198329eb9882795c9da34799dd`

Pre-freeze regression:

**1506 / 1506 PASS.**

SE2 `health_supervision_protocol` is the next software-evidence stage.

SE2 may use TRAIN only at this frontier. Validation and confirmation remain
closed. Model training remains deferred to the later authorized stage.

SE9 confirmation remains closed and cannot reopen selection after results.

## SE2 health supervision protocol freeze V1

Status: **SE2 health-supervision protocol resolved and frozen locally for checkpoint promotion.**

SE2 freezes the admissibility rules for `healthy`, `degraded`, and
`unusable` health supervision.

The protocol requires prospective, measurement-role-grounded, explicitly
provenance-bound evidence independent of diagnostic features, reference
trajectories, final estimator scoring, and confirmation-test outcomes.

Availability is not a health label.

Clean data are not automatically healthy.

Synthetic corruption identity is not automatically a health label.

Missing measurement is not a zero feature vector.

Final localization error may not define health supervision.

Current empirical readiness remains intentionally fail-closed:

- accepted baseline-nominality sources: 0;
- accepted health-supervision sources: 0;
- real health labels: 0;
- health-label generation authorized: false;
- empirical health supervision available: false.

SE2 did not open validation or confirmation, did not read reference
trajectories, did not assign health labels, and did not perform feature
selection, model training, probability calibration, threshold selection,
ATE/RPE, or final scoring.

SE2 implementation:

- `src/trust_robot/health_supervision_resolution.py`
- `configs/trust_robot/se2_health_supervision_protocol_v1.json`
- `tests/trust_robot/test_se2_health_supervision_protocol.py`

SE2 freeze artifacts:

- `manifests/trust_robot_se2_health_supervision_protocol_freeze_v1.json`
  SHA-256 `63da52c788208ae715abc7e0b8eb0ba6777cc16d33d90466332779c630618230`
- `tests/trust_robot/test_se2_health_supervision_protocol_freeze.py`
  SHA-256 `911bb403c7f5593c7eb94ce77821828baf418217dcb0b559195a69a538cdfdb4`
- `docs/audits/trust_robot/TRUST_ROBOT_SE2_HEALTH_SUPERVISION_PROTOCOL_FREEZE_V1.md`
  SHA-256 `24514683c55f382c696f5f664c48c0f35593d8df9699fcf03b0adad25a3a182e`

SE3 `multimodal_feature_pipeline` is the next software-evidence stage and may
proceed TRAIN-only.

SE4 health-model training remains blocked until admissible empirical TRAIN
supervision and real health labels are available.

Validation and confirmation remain closed.

SE9 remains closed.

## SE3 multimodal feature pipeline freeze V1

Status: **SE3 exact multimodal diagnostic feature contracts resolved, complete
frozen-TRAIN extraction empirically validated, and stage frozen locally for
checkpoint promotion.**

SE3 preserves the frozen Phase-4 LiDAR diagnostic feature contract unchanged
and prospectively resolves exact camera and IMU low-level diagnostic feature
contracts.

Camera features per message:

- `gray_mean_intensity_8bit`;
- `gray_std_intensity_8bit`;
- `gray_mean_abs_neighbor_difference_8bit`.

IMU features per message, with D435i and HandsFree streams kept separate:

- `angular_speed_norm_rad_s`;
- `linear_acceleration_norm_m_s2`.

IMU orientation and covariance are excluded from the SE3 vector.

The complete frozen 22-trajectory TRAIN extraction produced:

- 2,816,957 total feature records;
- 107,675 camera records;
- 1,404,805 D435i IMU records;
- 1,304,477 HandsFree IMU records;
- 4,320,203,720 source serialized payload bytes.

Camera and D435i IMU remain absent on `street_010` and `street_09`.
HandsFree IMU is present on all 22 TRAIN trajectories.

Missing measurements remain absent and are not converted to zero vectors or
cross-modal imputations.

The empirical population exactly matches the previously frozen Phase-5
camera/IMU TRAIN source evidence.

All emitted feature JSONL hashes and line counts were independently validated,
and all feature values/statistics are finite.

SE3 used TRAIN only.

Validation remained closed.

Confirmation remained closed.

Reference trajectories were not read.

No cross-modal alignment or physical synchronization inference was performed.

No health labels, health probabilities, supervised feature selection,
classifier training, probability calibration, threshold selection, ATE/RPE or
final scoring was performed.

Health-supervision state remains:

- accepted baseline-nominality sources: 0;
- accepted health-supervision sources: 0;
- real health labels: 0.

SE3 is complete.

SE4 `health_model_training` is the next stage in the frozen stage order, but
SE4 health-model training remains blocked until admissible empirical TRAIN
supervision and real health labels are available.

Validation and confirmation remain closed.

SE9 remains closed.

The prospective SE3 component config retains its historical
`SE3_complete=false` value. It is not rewritten after the fact. The aggregate
SE3 freeze manifest is the authoritative stage-level closure record.

SE3 implementation artifacts:

- `configs/trust_robot/se3_multimodal_feature_contract_v1.json`
- `src/trust_robot/se3_multimodal_feature_contract.py`
- `tests/trust_robot/test_se3_multimodal_feature_contract.py`
- `src/trust_robot/se3_multimodal_feature_extraction.py`
- `scripts/trust_robot/run_se3_multimodal_feature_extraction_v1.py`
- `tests/trust_robot/test_se3_multimodal_feature_extraction.py`

SE3 freeze artifacts:

- `manifests/trust_robot_se3_multimodal_feature_pipeline_freeze_v1.json`
  SHA-256 `a987f9793b60ea674991577a189711f2e535961796b1d74dfd6454e60de8e994`
- `tests/trust_robot/test_se3_multimodal_feature_pipeline_freeze.py`
  SHA-256 `d91e8b8a657561a4d0319b0b14e60494bd077a1dcae341cda3a382fa8ac148d5`
- `docs/audits/trust_robot/TRUST_ROBOT_SE3_MULTIMODAL_FEATURE_PIPELINE_FREEZE_V1.md`
  SHA-256 `e82eec77ec79b35de3df08f73fa0eab80dc87580492467612622dcbb0848bbcd`

Empirical run bindings:

- candidate file SHA-256:
  `04e6a6c452a69cce672571e162962cf97f4bcb487e962bf70dd0209c7e8feae5`
- run manifest file SHA-256:
  `c8eba6d6798ca66a341adc3a872fe53f0268968d903f211b0142e25a3270ad7e`
- run manifest content SHA-256:
  `e3461848f32033f4f44e4226c4ec88506c7fee9906e40929c96b0a4de94f53e4`
- SUCCESS file SHA-256:
  `e6d62f4441ede9db4d4f5947234a279b8998f2d6a2c61e5f717770023082c28d`
- aggregate trajectory-record SHA-256:
  `61be2e163607ee7984c1e6a1fa13c0386802d78e5f406a7edf1643e43e37060c`

## SE4 health-model training blocked-frontier freeze V1

Status: **SE4 blocked frontier frozen; SE4 remains incomplete.**

SE4 is the stage intended to train the actual healthy/degraded/unusable
modality-health model using admissible TRAIN supervision.

Training cannot currently execute because the frozen admissibility state is:

- accepted baseline-nominality sources: 0;
- accepted health-supervision sources: 0;
- real health labels: 0;
- empirical health supervision available: false.

The exact camera and IMU feature contracts from the promoted SE3 freeze are
now bound prospectively as the SE4 diagnostic inputs.

Camera features:

- `gray_mean_intensity_8bit`
- `gray_std_intensity_8bit`
- `gray_mean_abs_neighbor_difference_8bit`

IMU features:

- `angular_speed_norm_rad_s`
- `linear_acceleration_norm_m_s2`

The frozen Phase-4 LiDAR contract remains unchanged.

The historical Phase-5 health-model interface is not rewritten. It predates
SE3 exact camera/IMU feature resolution and remains hash-frozen in its
historical evidence-blocked form.

At this frontier:

- classifier architecture selected: false;
- model-family selection executed: false;
- hyperparameter selection executed: false;
- model training authorized: false;
- model training executed: false;
- trained model artifact: none;
- health inference authorized: false;
- probability calibration executed: false;
- threshold selection executed: false.

No validation or confirmation data was opened.

No reference trajectory or localization score was used as supervision.

SE4 remains incomplete.

SE5 remains blocked because no legitimate frozen TRAIN health-model output
exists.

Validation remains closed.

Confirmation remains closed.

SE9 remains closed.

The required next event is admissible empirical TRAIN health-supervision
evidence and real healthy/degraded/unusable labels satisfying the frozen SE2
protocol.

SE4 blocked-frontier artifacts:

- `src/trust_robot/se4_health_model_training_resolution.py`
  SHA-256 `38105bdeff480e627506f63a5f4e932b0ffed2243c86246f98dee360b9a1dfc3`
- `configs/trust_robot/se4_health_model_training_resolution_v1.json`
  SHA-256 `8d68167359b95d978ad9c39b8c9cfc87204b28def090f0fb3c2c640b61d4cfaa`
- `tests/trust_robot/test_se4_health_model_training_resolution.py`
  SHA-256 `8e9f8430c117afcae8724719f28ed0e70a49ffa8b52b1de9e7520673d79743be`
- `manifests/trust_robot_se4_health_model_training_blocked_frontier_freeze_v1.json`
  SHA-256 `8ced2b97595a541fb152b5fd012d83c6c8d8b99a770a0cd1e1a6e7c55d6f248d`
- `tests/trust_robot/test_se4_health_model_training_blocked_frontier_freeze.py`
  SHA-256 `a96e43d9110b2bab6d865f52e43aeadddf0c74151ff8d9f8a0f64139c27e3bab`
- `docs/audits/trust_robot/TRUST_ROBOT_SE4_HEALTH_MODEL_TRAINING_BLOCKED_FRONTIER_FREEZE_V1.md`
  SHA-256 `23cae48ecda67e4073141baa2a4e74a047fd692e9cfca9bff25408d58bbca65d`

## SE4 supervision acquisition mechanism freeze V1

Status: **prospective software acquisition mechanism resolved; live execution remains unauthorized.**

The software mechanism for future prospective LiDAR TRAIN supervision-evidence
acquisition is now frozen.

Selected future raw-evidence mechanisms are:

- one-shot HTTP GET `/cgi/info.json` for manufacturer-grounded device identity;
- one-shot HTTP GET `/cgi/status.json` for raw sensor status;
- one-shot HTTP GET `/cgi/diag.json` for raw diagnostic evidence;
- bounded classic-PCAP capture of measurement UDP packets;
- bounded classic-PCAP capture of position/telemetry UDP packets.

The physical-device primary identity remains manufacturer serial.

No real sensor IPv4 address, capture interface, UDP ports, capture duration,
output root, HTTP timeout values, shutdown grace, polling period, retry policy,
capture order, timing tolerance, fixed offset, interpolation or physical
interval-binding mechanism is selected.

Those values require a future real TRAIN execution environment and are not
inferred or fabricated from software evidence.

No network I/O was executed.

No subprocess was executed.

No sensor was contacted.

Raw capture artifacts remain 0.

Device identity receipts remain 0.

Accepted baseline-nominality sources remain 0.

Accepted health-supervision sources remain 0.

Real health labels remain 0.

Raw status, diagnostics and packet capture are not automatically health truth.

Host capture timestamps remain transport provenance only and do not establish
physical measurement time.

Live execution remains unauthorized.

Source acceptance remains unauthorized.

SE4 remains incomplete.

SE4 model training remains unauthorized.

SE5 remains blocked.

Validation remains closed.

Confirmation remains closed.

SE9 remains closed.

Frozen acquisition-mechanism artifacts:

- `src/trust_robot/se4_supervision_acquisition_mechanism_resolution.py`
  SHA-256 `4c63e450facef3353d0ae1b3cd16eefd66bc14c9e6ddc04ef9dcd4df68ec6869`
- `configs/trust_robot/se4_supervision_acquisition_mechanism_resolution_v1.json`
  SHA-256 `6150971b4a16e5ba2ad51c754174a7fd37df287763559f1fc4f60b481758e464`
- `tests/trust_robot/test_se4_supervision_acquisition_mechanism_resolution.py`
  SHA-256 `84a2dd880aa2e83a74acf903705cda2241eb17b3701fd88c241f1f376c8e33dd`
- `manifests/trust_robot_se4_supervision_acquisition_mechanism_freeze_v1.json`
  SHA-256 `18df2dd2a88d60939f31b844f584a21d090f3a15026369e511c2cb4d39dd20f4`
- `tests/trust_robot/test_se4_supervision_acquisition_mechanism_freeze.py`
  SHA-256 `e4eec16c925386e1a1d0b72be58ab869c64de2b397642c0986f977bbbcfc83d1`
- `docs/audits/trust_robot/TRUST_ROBOT_SE4_SUPERVISION_ACQUISITION_MECHANISM_FREEZE_V1.md`
  SHA-256 `27f6c9ee0c5e90990f61c4ca610cbec836af6989ed5e340e79d8c8be0e9e9a97`

## SE4 live-execution transport freeze V1

Status: **future executable UDP transport resolved; real-sensor execution remains unauthorized.**

The future executable VLP-32C UDP payload-acquisition transport is now the
existing ordinary user-space dual UDP receiver.

The selected receiver uses `AF_INET` / `SOCK_DGRAM` sockets and does not
require passive interface sniffing, raw packet sockets, `tcpdump`, root,
sudo, or `CAP_NET_RAW`.

Loopback dual-stream execution is already verified.

Real VLP-32C execution is not yet verified.

The earlier classic-PCAP / `tcpdump` acquisition mechanism remains historical
and hash-frozen and is not rewritten.

The selected ordinary UDP receiver preserves exact delivered UDP payload
bytes, datagram boundaries, per-datagram SHA-256, stream identity, source
endpoint, destination bind endpoint, and host userspace receive timestamps.

It does not preserve Ethernet, IP or UDP headers and does not prove zero
packet loss.

Host receive timestamps remain transport provenance only and do not establish
physical measurement time or interval binding.

No real bind IPv4, VLP-32C ports, sensor IPv4, capture duration, output root,
session identity, HTTP timeout values or destination configuration is selected.

No network or sensor execution occurred in this resolution.

Raw real-sensor capture artifacts remain 0.

Device identity receipts remain 0.

Accepted baseline-nominality sources remain 0.

Accepted health-supervision sources remain 0.

Real health labels remain 0.

Real-sensor execution remains unauthorized.

Source acceptance remains unauthorized.

Health-label generation remains unauthorized.

SE4 remains incomplete.

SE4 model training remains unauthorized.

SE5 remains blocked.

Validation remains closed.

Confirmation remains closed.

SE9 remains closed.

Frozen live-execution transport artifacts:

- `src/trust_robot/se4_live_execution_transport_resolution.py`
  SHA-256 `f02709f221148f68351aebdc2bbbf8fd567acf13d09e2f5d568ebe2a465d5c9c`
- `configs/trust_robot/se4_live_execution_transport_resolution_v1.json`
  SHA-256 `ee737340b0b6d2d262b39ce05bd3a23dc9bf2b082e3ad974a5c7e413a044ee64`
- `tests/trust_robot/test_se4_live_execution_transport_resolution.py`
  SHA-256 `ba08f31a4d7e9c77af99102282fcf7757ffeecd0afcc93c06b5794eb0680adfb`
- `manifests/trust_robot_se4_live_execution_transport_freeze_v1.json`
  SHA-256 `c086398420cf9187aba0defaa3fce54a34eb5f57dbef457aa30e3fae290cd0b0`
- `tests/trust_robot/test_se4_live_execution_transport_freeze.py`
  SHA-256 `baec23676142c09b1cb06029b848f54c6d829d3aa56e35e0f094a59b2c30f684`
- `docs/audits/trust_robot/TRUST_ROBOT_SE4_LIVE_EXECUTION_TRANSPORT_FREEZE_V1.md`
  SHA-256 `9680ddea2c4d3c1902c9b74c7e616489ac8a0caf2fd7f1be4508ddacd4926a3c`

## SE4 real TRAIN runtime-input binding freeze V1

Status: **runtime-input binding protocol resolved; no real physical runtime values are bound.**

A deterministic no-default protocol now defines how one future operator-supplied
real TRAIN runtime binding must be represented and hash-addressed before any
network or sensor execution.

A real binding must explicitly supply:

- acquisition-session identity;
- TRAIN split role;
- receiver bind IPv4;
- measurement and position UDP ports;
- sensor IPv4;
- capture duration;
- absolute output root;
- HTTP connect and total timeout values;
- VLP-32C destination IPv4;
- VLP-32C measurement and position destination ports;
- explicit VLP-32C destination-configuration verification;
- prospective declaration before execution.

The protocol supplies no physical defaults.

Each valid binding receives a canonical SHA-256 digest.

A valid binding is still not execution authorization, physical evidence,
interval binding, baseline nominality, health supervision or a health label.

Real runtime bindings remain 0.

Real runtime values bound remain false.

No bind IPv4 is selected.

No measurement or position UDP ports are selected.

No sensor IPv4 is selected.

No capture duration is selected.

No output root is selected.

No acquisition-session identity is selected.

No HTTP timeout values are selected.

No VLP-32C destination configuration is verified.

No network I/O occurred.

No sensor was contacted.

Raw real-sensor capture artifacts remain 0.

Accepted baseline-nominality sources remain 0.

Accepted health-supervision sources remain 0.

Real health labels remain 0.

Interval binding remains unestablished.

Real-sensor execution remains unauthorized.

Source acceptance remains unauthorized.

Health-label generation remains unauthorized.

SE4 remains incomplete.

SE4 model training remains unauthorized.

SE5 remains blocked.

Validation remains closed.

Confirmation remains closed.

SE9 remains closed.

Frozen runtime-input binding artifacts:

- `src/trust_robot/se4_real_train_runtime_input_binding.py`
  SHA-256 `1c9626481d4f01be63c4c7e9d833cc32dcc4b17c07c90611be2a6a671c47597f`
- `configs/trust_robot/se4_real_train_runtime_input_binding_v1.json`
  SHA-256 `ff293fa62bab7d1ce72f8a2f130130c5b66826c74a8d1853a7f1ac63e9fc14e7`
- `tests/trust_robot/test_se4_real_train_runtime_input_binding.py`
  SHA-256 `326a00e41d67c4804277b1e5d11ff873539eac4737570129e158be589d7d9566`
- `manifests/trust_robot_se4_real_train_runtime_input_binding_freeze_v1.json`
  SHA-256 `28bf88aa87f6c527f16fa3144e94d70fadc64379f0e90529f04c46e7364d6afc`
- `tests/trust_robot/test_se4_real_train_runtime_input_binding_freeze.py`
  SHA-256 `9fb09cbfef05c61b008e4a494eac0a827c8b0ecf5ed8e416b288b671be9ec04a`
- `docs/audits/trust_robot/TRUST_ROBOT_SE4_REAL_TRAIN_RUNTIME_INPUT_BINDING_FREEZE_V1.md`
  SHA-256 `aefbe1912759aee6932c04d1ea5f757d1379350e555eca305c81828c49ec0c11`

## SE4 HTTP evidence executor freeze V1

Status: **HTTP execution software implemented and loopback verified; real-sensor execution remains unauthorized.**

The software-only HTTP execution gap is now resolved for the frozen VLP-32C
read-only evidence endpoints:

- `/cgi/info.json`;
- `/cgi/status.json`;
- `/cgi/diag.json`.

The executor uses one-shot `GET` requests via `curl` with `shell=False`.

HTTP connect timeout is explicit.

HTTP total timeout is explicit.

HTTP port is explicit.

The protocol supplies no physical HTTP-port default.

The executor's `None` port value is fail-closed and is rejected before network
execution.

No real HTTP port is selected.

Response body and response headers are preserved separately, hash-verified,
fsynced and atomically published without overwriting existing final artifacts.

Loopback HTTP execution is verified.

Loopback ports are ephemeral software-test values only and are not real runtime
selections.

No real VLP-32C HTTP execution occurred.

Real runtime bindings remain 0.

Real runtime values bound remain false.

No real sensor IPv4 is selected.

No real HTTP port is selected.

Real-sensor network I/O remains false.

Real-sensor contact remains false.

Raw real-sensor HTTP artifacts remain 0.

Real device identity receipts remain 0.

Accepted baseline-nominality sources remain 0.

Accepted health-supervision sources remain 0.

Real health labels remain 0.

Interval binding remains unestablished.

Physical measurement time remains unestablished.

HTTP implementation is not execution authorization.

Loopback verification is not physical evidence.

HTTP status and diagnostics are not health labels.

HTTP identity evidence is not automatically baseline nominality.

Real-sensor HTTP execution remains unauthorized.

Source acceptance remains unauthorized.

Health-label generation remains unauthorized.

SE4 remains incomplete.

SE4 model training remains unauthorized.

SE5 remains blocked.

Validation remains closed.

Confirmation remains closed.

SE9 remains closed.

Frozen HTTP executor artifacts:

- `src/trust_robot/se4_http_evidence_executor.py`
  SHA-256 `98d82acca2308aea76537de4a9cc4fa0eb94e8fd9bc4aa9bde048382f5b69dd9`
- `configs/trust_robot/se4_http_evidence_executor_resolution_v1.json`
  SHA-256 `51f98b3424d1db7bd2706f49e399954b007dfd8c2897d495462c7c7edd921aac`
- `tests/trust_robot/test_se4_http_evidence_executor.py`
  SHA-256 `5af405448611cf616a95078fc5ab96f7bb02d13f82a99eece57758c9b3493dad`
- `manifests/trust_robot_se4_http_evidence_executor_freeze_v1.json`
  SHA-256 `29639601503a8d7c0b9db879939a8960b2f0a69ca10e378fc07f0b031aeadc10`
- `tests/trust_robot/test_se4_http_evidence_executor_freeze.py`
  SHA-256 `226a9b1e447b81ec7017effbf12a914c44e43f928bdee678fc25e16d5b77134c`
- `docs/audits/trust_robot/TRUST_ROBOT_SE4_HTTP_EVIDENCE_EXECUTOR_FREEZE_V1.md`
  SHA-256 `3754d7c73076ad544db7f5ce0abeb906a2f5bf42bec4aba2d1112a2a8217f786`

## SE4 real TRAIN runtime-input binding V2 freeze V1

Status: **V2 runtime-binding contract resolved; HTTP-port cross-contract gap closed; no real runtime binding exists.**

The previously promoted V1 runtime-binding protocol remains historical and
unchanged.

The promoted HTTP executor later established that real HTTP execution requires
an explicit HTTP port and that no physical HTTP-port default may be supplied.

The V1 runtime-binding schema had 15 required fields and could not represent
that value.

V2 adds exactly one required field:

- `http_port`.

The V2 required-field count is 16.

No V1 required field was removed.

No other physical runtime field was changed.

`http_port` must be externally supplied and must be an exact integer in
`1..65535`.

The V2 protocol supplies no physical HTTP-port default.

Real V2 runtime bindings remain 0.

Real runtime values bound remain false.

No real HTTP port is selected.

No real sensor IPv4 is selected.

No network I/O occurred.

No sensor was contacted.

Raw real-sensor capture artifacts remain 0.

Accepted baseline-nominality sources remain 0.

Accepted health-supervision sources remain 0.

Real health labels remain 0.

Interval binding remains unestablished.

Physical measurement time remains unestablished.

A V2 binding is not execution authorization.

A V2 binding is not source acceptance.

A V2 binding is not a health label.

The composite binding + HTTP + UDP live-session orchestrator remains unresolved.

Real-sensor execution remains unauthorized.

SE4 remains incomplete.

SE4 model training remains unauthorized.

SE5 remains blocked.

Validation remains closed.

Confirmation remains closed.

SE9 remains closed.

Frozen V2 runtime-binding artifacts:

- `src/trust_robot/se4_real_train_runtime_input_binding_v2.py`
  SHA-256 `f00fb0571a9fb4ac1a078a6789941741b68bbf066a7a6f01028f2450bc820212`
- `configs/trust_robot/se4_real_train_runtime_input_binding_v2.json`
  SHA-256 `740705b97fa088f31efe3e603e9c25d3c005d9cae1b757479377cc7aabe517fb`
- `tests/trust_robot/test_se4_real_train_runtime_input_binding_v2.py`
  SHA-256 `86c574577b4c6c4cb85b2181ee41ae41304b73b36f32df545737d301d32a1f8e`
- `manifests/trust_robot_se4_real_train_runtime_input_binding_v2_freeze_v1.json`
  SHA-256 `81f1d22674a4ca1ef4a8b5c9c4d16e446423eb3e6a76981fa7d6f99b08477388`
- `tests/trust_robot/test_se4_real_train_runtime_input_binding_v2_freeze.py`
  SHA-256 `7238f8e7f9f8bd6ddd638e997badbdcf69b87edf9a869eb97afc2945aac96a3e`
- `docs/audits/trust_robot/TRUST_ROBOT_SE4_REAL_TRAIN_RUNTIME_INPUT_BINDING_V2_FREEZE_V1.md`
  SHA-256 `215aa5d13bf53befe4de4501ab3521dee7f7708ddfc6070a546fc7ca9c0a3ed1`

## SE4 composite live-session orchestrator freeze V1

Status: **composite orchestration software resolved; injected software-only execution order verified; real execution remains blocked.**

The composite binding + HTTP + UDP orchestration software is resolved.

A validated V2 real TRAIN runtime binding is required.

A separate execution-authorization artifact is required and must be SHA-256
bound to that exact runtime binding.

Authorization must be established before the UDP receiver is invoked.

The UDP receiver remains the owner of fresh session-directory creation.

The orchestrator does not pre-create the session directory.

The HTTP executor consumes the existing directory returned by the UDP receiver.

The frozen sequential execution order is:

1. validate V2 runtime binding;
2. validate execution authorization;
3. filesystem preflight;
4. invoke dual-UDP receiver;
5. validate returned session directory;
6. identity HTTP;
7. status HTTP;
8. diagnostic HTTP;
9. publish composite session receipt.

HTTP/UDP concurrency is not required.

Successful execution selects `composite_session_receipt.json`.

Post-session failure selects a best-effort
`composite_session_failure.json`.

Software verification uses injected non-network component functions.

No literal loopback real-binding bypass is used because the frozen V2 real TRAIN
binding correctly rejects loopback physical endpoints.

Component injection is not real sensor execution and is not physical evidence.

Real runtime bindings remain 0.

Real runtime values bound remain false.

Real execution authorizations remain 0.

Real-sensor execution remains unauthorized.

Real sensor network I/O remains false.

Real sensor contact remains false.

Raw real-sensor capture artifacts remain 0.

Real composite session receipts remain 0.

Accepted baseline-nominality sources remain 0.

Accepted health-supervision sources remain 0.

Real health labels remain 0.

Interval binding remains unestablished.

Physical measurement time remains unestablished.

Execution authorization does not authorize source acceptance.

Execution authorization does not authorize health-label generation.

UDP capture is not automatically baseline nominality.

HTTP evidence is not automatically health supervision.

SE4 remains incomplete.

SE4 model training remains unauthorized.

SE5 remains blocked.

Validation remains closed.

Confirmation remains closed.

SE9 remains closed.

Frozen composite-orchestrator artifacts:

- `src/trust_robot/se4_composite_live_session_orchestrator.py`
  SHA-256 `ca23e6a2cca37c3af5ebeeae39bfdf6cc4ba4b9669b4a25135e6e15810081b2d`
- `configs/trust_robot/se4_composite_live_session_orchestrator_resolution_v1.json`
  SHA-256 `1564aaa7c261d37219ede56d42daa428a754c089a420d988b2cfb5c818eb41ff`
- `tests/trust_robot/test_se4_composite_live_session_orchestrator.py`
  SHA-256 `a7a8e2804afaa0040a5486ca3c7f4d64abc6b037c0cfcbba7d533025432715e2`
- `manifests/trust_robot_se4_composite_live_session_orchestrator_freeze_v1.json`
  SHA-256 `7ee319bc88c33541923df1d73971a8703af29d177f98a05160a99655a9b51e04`
- `tests/trust_robot/test_se4_composite_live_session_orchestrator_freeze.py`
  SHA-256 `820a16e1e633b01f532b83c36e8d236d016edeb810a69cfc85cb779f2311fde2`
- `docs/audits/trust_robot/TRUST_ROBOT_SE4_COMPOSITE_LIVE_SESSION_ORCHESTRATOR_FREEZE_V1.md`
  SHA-256 `3fab86846cafac1ad54f84045ec84a5cc83c3d71e8fde7ac14184ec4ae65a6cd`
