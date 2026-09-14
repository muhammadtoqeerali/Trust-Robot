# TRUST-ROBOT Data Protocol V1 Candidate

Status: **candidate_not_frozen**

## 1. Purpose

This protocol defines the minimum data, reference, synchronization, coordinate-frame, trajectory-lineage, split, and anti-leakage contracts that must be satisfied before a dataset is admitted into TRUST-ROBOT experiments.

It does not claim that any dataset is locally downloaded, complete, synchronized, calibrated, or ready.

## 2. Dataset roles

### M2DGR

Primary development benchmark.

Proposal-level usable modalities:

- camera
- LiDAR
- IMU

Intended roles include development, validation/calibration, controlled fault injection, and in-distribution confirmation.

Local readiness remains unverified until the actual release is audited.

### EuRoC MAV

Camera-IMU controlled and different-platform evaluation.

Reference-supported metric dimensions must be trajectory/interval specific. Vicon-supported sequences may permit full 6-DoF scoring; Leica-only reference must not be treated as rotational ground truth.

### TUM-VI

Supplementary camera-IMU cross-dataset stress evaluation.

Continuously referenced room sequences and partially referenced longer sequences must be distinguished. Full-trajectory pose metrics are allowed only where reference coverage supports them.

### MUN-FRL

Supplementary camera-IMU-LiDAR cross-platform evaluation.

RTK/PPK position does not automatically provide independent attitude ground truth. Any released odometry/derived estimator output must not silently be treated as independent truth.

### GrandTour

Supplementary quadruped heterogeneous-sensor stress evaluation.

LiDAR, camera, and an admissible IMU may be used. Optional proprioception belongs to a separately justified branch. Streams contributing to reference construction remain reference-only.

### M3DGR

Conditional supplementary degradation evaluation.

Do not admit until download/access, integrity, calibration, timestamps, required streams, and independent reference coverage are all verified.

### KIOS quadruped

Planned local dog/quadruped physical platform and provisional dataset identity.

The local quadruped is the primary eventual physical deployment and validation platform for TRUST-ROBOT. Its actual robot identity, compute hardware, sensor suite, calibration, synchronization, and reference instrumentation must be frozen from evidence when available rather than assumed in advance.

Local quadruped data may later be admitted to development, training, or validation/calibration only through explicit trajectory-disjoint partitions. Separate quadruped trajectories must remain strictly held out for final physical confirmation, onboard resource profiling, supervisory-policy evaluation, and controlled closed-loop testing.

The held-out physical partition must not determine model architecture, learned parameters, calibration temperatures, fault or attack severity grids, health thresholds, suppression/recovery thresholds, fallback thresholds, or other operating points.

The core TRUST-ROBOT estimator remains platform-independent and is based on admissible camera, LiDAR, and IMU streams. Quadruped proprioception is an optional branch only if the actual robot exposes scientifically usable and verified signals such as joint, contact, or leg-odometry information.

### Physical-platform policy

The local dog/quadruped robot is the current primary eventual physical platform.

A drone remains an optional future cross-platform branch. Because the drone platform is not currently committed, drone-specific assumptions must not drive the core estimator, diagnostics, data contracts, or experimental protocol.

Any future drone dataset or experiment must pass the same stream, synchronization, calibration, independent-reference, partition, and anti-leakage gates before admission.

## 3. Required machine-readable objects

Every admitted dataset must eventually provide:

- dataset identifier;
- dataset role;
- local readiness record;
- trajectory identifiers;
- base-trajectory identifiers;
- sensor-stream identifiers;
- sensor modalities;
- coordinate-frame identifiers;
- clock-domain identifiers;
- timestamp units;
- synchronization evidence/status;
- calibration/extrinsic provenance;
- reference-source identifiers;
- reference-supported state dimensions;
- reference coverage;
- split assignment;
- derivative lineage;
- corruption seed when applicable.

## 4. Coordinate-frame rules

1. Every estimator input stream must name a frame.
2. Every reference must name its frame.
3. Any transform used to compare an estimate with reference must have explicit provenance.
4. A transform marked verified must name its verification/source evidence.
5. Frame aliases must not be inferred from similar names.
6. Dataset-native world/map/reference frames must remain explicit rather than being silently collapsed into one global convention.
7. Phase 1 does not choose a universal body-frame convention for every future estimator. It defines the requirement that conversions be explicit and testable.

## 5. Synchronization rules

1. Every stream must name a clock domain.
2. Timestamp unit must be explicit.
3. Synchronization status is one of:
   - verified;
   - unverified;
   - conditional;
   - not_applicable.
4. A stream marked synchronization-verified must record the method/evidence.
5. Unknown offsets, interpolation, time shifts, or clock conversions must not be silently assumed.
6. Future dataset adapters must preserve raw timestamps before resampling/alignment.
7. For audited M2DGR candidate estimator streams, verified sensor `header.stamp` is the measurement-time basis.
8. For those M2DGR streams, the rosbag record timestamp is retained as transport/provenance diagnostic evidence and must not silently replace sensor `header.stamp` as measurement time.
9. M2DGR applies no global fixed sensor time offset by default; any future fixed offset requires explicit evidence and versioned provenance.
10. M2DGR multimodal association and scoring are restricted to the intersection of required-stream sensor-header time coverage and independently valid reference coverage for the required scoring dimensions.

## 6. Reference-source rules

1. A concrete stream used to construct ground truth/reference cannot simultaneously be an evaluated estimator input.
2. A scientifically independent sensor instance must have a different stream identifier and provenance.
3. Derived odometry, maps, contact states, or estimator outputs are not automatically independent ground truth.
4. Supported scoring dimensions are explicit:
   - translation;
   - rotation.
5. Position-only reference does not permit rotational/full-pose claims.
6. Partial reference coverage permits scoring only on supported intervals/dimensions.
7. Coverage is recorded per supported state dimension as well as at reference-source level.
8. A supported dimension with `partial` or `endpoint_only` coverage must name a machine-readable validity artifact identifying admissible samples or intervals.
9. Validity artifacts are derived metadata. Raw reference files remain immutable and checksummed.
10. Structurally invalid reference values, including invalid quaternions, must not be silently normalized or repaired in the raw source.
11. Invalidity in one reference dimension does not automatically invalidate another independently usable dimension from the same reference source.
12. Reference provenance must be retained in experiment receipts/manifests.

## 7. Split and lineage rules

The primary split roles are:

- `train`
- `validation_calibration`
- `confirmation_test`

Mandatory invariants:

1. Base trajectories are disjoint across split roles.
2. All clean/corrupted derivatives of one base trajectory remain in one split.
3. Corruption seeds are not reused across partitions.
4. A trajectory record has exactly one split.
5. Cross-dataset recalibration, when later permitted, uses a calibration-only subset disjoint from final cross-dataset testing.
6. Zero-shot and recalibrated transfer must be reported separately.

## 8. Test-data prohibition

Confirmation/test data must not determine:

- model architecture;
- model hyperparameters;
- fault severity grids;
- attack budgets;
- calibration temperatures;
- health thresholds;
- suppression thresholds;
- recovery thresholds;
- fallback thresholds;
- other validation-selected operating points.

## 9. Readiness gate

A dataset is not `ready_for_use` until all applicable Phase-1 checks are true:

- local path configured;
- file integrity verified;
- required sensor streams verified;
- timestamps verified;
- calibration/extrinsics verified;
- synchronization verified;
- reference coverage verified;
- reference/input independence verified;
- trajectory identity available for split enforcement.

Proposal-level public availability alone is not sufficient.

## 10. Phase-1 freeze gate

This candidate may be frozen only after:

1. local dataset/access audit is completed for the dataset(s) entering Phase 2;
2. machine-readable registry validates;
3. anti-leakage unit tests pass;
4. at least one small synthetic trajectory manifest passes validation;
5. at least one deliberately invalid manifest is rejected for each critical invariant;
6. unresolved reference/synchronization/frame assumptions are documented rather than guessed.

Until then the protocol remains a candidate.
