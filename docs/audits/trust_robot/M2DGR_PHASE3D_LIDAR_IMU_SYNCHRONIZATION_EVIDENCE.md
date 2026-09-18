# M2DGR Phase 3D LiDAR/IMU Synchronization Evidence

Date: 2026-09-18

Status: completed LiDAR-to-HandsFree-IMU timing-characterization checkpoint;
physical capture synchronization remains unverified.

## Purpose

Phase 3D asks what timing information is retained in the released M2DGR
Velodyne point clouds and whether LiDAR rotational content provides independent
evidence sufficient to identify a physical LiDAR-to-IMU time relationship.

The objective is not to force a LiDAR-to-IMU offset.

The objective is to distinguish:

- point-cloud ROS header coordinates;
- per-point relative timing;
- generic Velodyne driver mechanisms;
- LiDAR/inertial physical-content consistency;
- whole-scan registration effective time;
- fixed-lag diagnostics;
- physical firing-time semantics;
- synchronization verification.

## Released LiDAR representation

M2DGR identifies the LiDAR as a Velodyne VLP-32C and releases
`/velodyne_points`.

Raw `/velodyne_packets` are not retained in the released bags.

A payload-schema pilot found one stable PointCloud2 layout containing:

- `x`: FLOAT32
- `y`: FLOAT32
- `z`: FLOAT32
- `intensity`: FLOAT32
- `ring`: UINT16
- `time`: FLOAT32

The released representation therefore retains a per-point numeric timing
coordinate even though the raw packet stream is absent.

## VLP-32C timing-mechanism fingerprint

A predeclared 200-cloud pilot on:

- `gate_01`
- `hall_01`
- `room_01`

showed that the point-time field spans approximately one complete 10 Hz LiDAR
revolution.

The point times are predominantly negative relative to the PointCloud2 header.

The observed maximum point-time value reaches:

`+0.000642816 s`

This exactly matches the terminal VLP-32C firing offset produced by the public
Velodyne timing table using:

- full firing cycle: 55.296 microseconds
- single firing interval: 2.304 microseconds
- terminal offset: 642.816 microseconds

A subsequent frozen 36-trajectory characterization used the first 50 clouds
from every trajectory.

Across all 36 trajectories:

- the sampled PointCloud2 schema is consistent;
- no non-finite point-time values were observed;
- no sampled point time exceeds the 642.816 microsecond terminal offset;
- the terminal firing offset appears on every trajectory;
- every sampled cloud contains negative relative point times.

Across trajectories, the median header period is:

- minimum: 100.165128000 ms
- median: 100.196242500 ms
- maximum: 100.210666000 ms

The median point-time span is:

- minimum: 100.064317172 ms
- median: 100.136796420 ms
- maximum: 100.152572122 ms

The candidate `header + point_time` coordinate nearly tiles consecutive scans.

Its median inter-scan gap across trajectories is:

- minimum: 0.048640000 ms
- median: 0.057216000 ms
- maximum: 0.068352000 ms

This is strong dataset-internal evidence for a VLP-32C relative-time mechanism
consistent with a last-packet-referenced scan timestamp.

It is not independent proof of the exact M2DGR Velodyne driver revision,
runtime configuration, scan timestamp option, or physical event represented by
the PointCloud2 header.

The generic public-driver mechanism is provenance/mechanism evidence only.

## Serialized point-time reversals

Adjacent PointCloud2 entries are not strictly increasing in the stored `time`
field.

These reversals were retained as observations.

They are not treated as automatic point invalidity because no evidence
establishes that PointCloud2 serialization order must be strictly chronological.

No points or clouds are excluded using an arbitrary monotonicity rule.

## Frozen LiDAR/HandsFree zero-lag pilot

Before any lag scan, a LiDAR rotational-motion method was frozen.

The pilot used:

- `gate_01`
- `hall_01`
- `room_01`
- first 300 consecutive `/velodyne_points` clouds;
- raw XYZ coordinates;
- deterministic trimmed point-to-point ICP;
- 0.50 m voxel size;
- at most 5000 points per cloud;
- 15 ICP iterations;
- 0.80 correspondence trim fraction;
- identity ICP initialization;
- no deskewing;
- no per-point timing in registration;
- HandsFree gyroscope integration between LiDAR header timestamps;
- no gyroscope-bias estimation;
- author-published HandsFree-to-LiDAR identity rotation;
- no bag-record timestamps;
- no fixed offset.

The author calibration remains independently unverified.

A structural support rule was added after the first pilot attempt revealed one
LiDAR interval before the beginning of `hall_01` HandsFree-IMU coverage.

The repaired rule admits an interval only when both LiDAR header boundaries are
inside real IMU header support.

No IMU extrapolation is permitted.

This is a computability rule, not an evaluation-validity mask.

Pilot zero-lag results:

### `gate_01`

- admitted pairs: 299
- vector correlation: 0.995879175
- rotation-angle correlation: 0.996302006
- median rotation disagreement: 0.076052485 degrees
- raw ICP vector correlation: -0.995879175

### `hall_01`

- admitted pairs: 298
- unsupported pairs: one leading boundary pair
- vector correlation: 0.973041687
- rotation-angle correlation: 0.971277050
- median rotation disagreement: 0.089750958 degrees
- raw ICP vector correlation: -0.973041687

### `room_01`

- admitted pairs: 299
- vector correlation: 0.984972436
- rotation-angle correlation: 0.976412457
- median rotation disagreement: 0.231327956 degrees
- raw ICP vector correlation: -0.984972436

The opposite raw ICP convention produces the opposite correlation sign.

The frozen transpose/body-motion convention is therefore supported by the
physical-content evidence.

Zero-lag agreement remains characterization, not synchronization proof.

## Frozen descriptive lag pilot

The frozen LiDAR rotations were reused without rerunning or retuning ICP.

The predeclared lag grid was:

- minimum: -101 ms
- maximum: +101 ms
- step: 1 ms

The bound corresponds approximately to one native LiDAR revolution.

The same LiDAR pair support was used at every lag.

No lag-specific pair admission and no IMU extrapolation were permitted.

Primary vector-correlation optima:

- `gate_01`: -46 ms
- `hall_01`: -35 ms
- `room_01`: -54 ms

Rotation-angle-correlation optima:

- `gate_01`: -46 ms
- `hall_01`: -34 ms
- `room_01`: -53 ms

Median-rotation-error optima:

- `gate_01`: -50 ms
- `hall_01`: -85 ms
- `room_01`: -99 ms

Best-minus-zero vector-correlation improvements:

- `gate_01`: 0.001963775
- `hall_01`: 0.002143286
- `room_01`: 0.004479343

The correlation objectives cluster at negative shifts roughly comparable to
half of one approximately 100 ms LiDAR revolution.

However, the independent median-error objective does not identify the same
shift, and the three trajectories do not identify one exact common lag.

Because registration uses complete undeskewed rotating scans, the effective
temporal center of scan-to-scan ICP is not independently established.

Therefore the observed lag surface cannot uniquely distinguish:

- a sensor-clock offset;
- scan-header reference semantics;
- per-point acquisition time;
- the effective temporal center of whole-scan registration.

The lag grid is not expanded.

No lag optimum is converted into a physical clock correction.

## 36-trajectory zero-lag generalization cohort

The exact frozen zero-lag frontend was applied to every M2DGR trajectory.

No quality-based admission threshold was introduced.

Total candidate LiDAR intervals:

10764.

Admitted intervals with real HandsFree-IMU support:

10758.

Unsupported intervals:

6.

All six unsupported intervals are leading boundary intervals.

Unsupported internal intervals:

0.

Unsupported trailing intervals:

0.

Failed ICP intervals:

0.

Zero-lag vector correlation across trajectories:

- minimum: 0.798444575
- median: 0.987891015
- maximum: 0.998822853

Zero-lag rotation-angle correlation:

- minimum: 0.859841312
- median: 0.988835748
- maximum: 0.998959923

Per-trajectory median rotation disagreement:

- minimum: 0.030531038 degrees
- median: 0.083623408 degrees
- maximum: 0.251305615 degrees

Per-trajectory p95 rotation disagreement:

- minimum: 0.127250242 degrees
- median: 0.217301382 degrees
- maximum: 0.467316709 degrees

Z-axis component correlation:

- minimum: 0.958338116
- median: 0.996385615
- maximum: 0.999232593

Raw ICP vector correlation:

- minimum: -0.998822853
- median: -0.987891015
- maximum: -0.798444575

The result generalizes strong near-header rotational-content consistency across
the full cohort.

No numeric correlation threshold is promoted into a timing-validity rule.

For example, `gate_03` has the lowest full-vector correlation but still small
median rotational disagreement, and `street_04` has lower correlation than
most trajectories while retaining small median disagreement.

These observations demonstrate why arbitrary correlation cutoffs would be
scientifically unjustified.

## Scientific interpretation

The released M2DGR LiDAR and HandsFree-IMU streams provide strong evidence of:

- a coherent VLP-32C per-point relative-time coordinate;
- near-header LiDAR/inertial rotational-content consistency;
- a correct frozen LiDAR body-rotation convention for this analysis.

The released evidence does not independently establish:

- the exact Velodyne driver revision;
- the exact recorder runtime configuration;
- the physical event represented by the PointCloud2 header;
- `header + time` as independently verified physical firing time;
- an independently verified HandsFree-to-LiDAR calibration;
- a unique LiDAR-to-IMU fixed clock offset;
- a synchronization tolerance;
- a common hardware clock;
- physical LiDAR-to-IMU capture synchronization.

The descriptive lag pilot is explicitly confounded by the effective temporal
support of undeskewed full-scan registration.

A 36-trajectory lag optimization is therefore not run.

Phase 3D stops LiDAR/IMU lag tuning rather than forcing a numerical clock
offset from non-identifiable evidence.

## Permanent evidence artifact

Repository path:

`manifests/m2dgr_lidar_imu_synchronization_evidence_v1.json`

Content SHA256:

`ec5fbed1a386dd17e58fd05df500a45ee0ff4fc1ff40286f08d67410b3ce7c10`

File SHA256:

`44fe629284cad3f92e3109cec60ee2aab799c69c43eeeb67b5461b781d303f45`

The artifact is bound to Phase-3C manifest content SHA256:

`f599be5bb1b4d009fe77ff8eb33148880122f92f4bfe00f885ec18015d715387`

## Phase-3D successor manifest

Repository path:

`manifests/m2dgr_trajectory_manifest_v1_phase3d_lidar_imu_sync_evidence.json`

Content SHA256:

`3daf042328a9c9ee8bab0bbdb777a832bc867075323e39ca1553a6810f975756`

File SHA256:

`67fe08bff676689dd212da03dce8e16ecee277c96f38f752d0d38a5e4e54cf6f`

The successor contains:

- 36 trajectory records
- 140 stream entries
- 140 synchronization entries
- 36 `/velodyne_points` synchronization-method updates

Only the `/velodyne_points` synchronization `method` changes relative to the
Phase-3C manifest.

No stream metadata, clock domains, measurement-time basis, verification
status, offsets, tolerances, reference metadata, or non-LiDAR synchronization
entries change.

## Explicitly not claimed

Phase 3D does not claim:

- verified LiDAR physical firing timestamps;
- verified LiDAR-to-IMU physical capture synchronization;
- verified common physical clock;
- a LiDAR-to-IMU fixed offset;
- a synchronization tolerance;
- a LiDAR timing validity mask;
- independently verified LiDAR/IMU extrinsic calibration;
- verified reference-to-estimator temporal association;
- evaluation readiness.

Synchronization remains `UNVERIFIED`.

Evaluation readiness remains `FALSE`.

## Remaining Phase-3 blockers

- reference-to-estimator temporal association
- common physical clock verification
- independent calibration verification
- scientifically valid validation/calibration partitioning before any
  data-selected synchronization tolerance is frozen
- explicit handling policy for structurally invalid sensor timestamps

LiDAR-to-IMU timing has been characterized to the limit justified by the
released evidence, but physical capture synchronization remains unresolved.
