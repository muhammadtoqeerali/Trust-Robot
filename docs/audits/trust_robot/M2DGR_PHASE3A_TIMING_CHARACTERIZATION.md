# M2DGR Phase 3A Timing Characterization Audit

Date: 2026-09-16

## Scope

This checkpoint characterizes M2DGR sensor measurement timestamps and
trajectory-specific stream availability.

It is **not** a claim that cross-stream synchronization is verified.

Phase 3 remains in progress.

## Measurement-time basis

Sensor message header timestamps are the measurement-time evidence used by
this audit.

ROS bag record timestamps are retained only as transport/provenance
diagnostics.

No fixed record-to-header offset was estimated or applied.

## Dataset coverage

All 36 M2DGR ROS bags were inspected using the ROS-independent `rosbags`
reader.

Target streams:

- `/camera/color/image_raw/compressed`
- `/camera/imu`
- `/handsfree/imu`
- `/velodyne_points`

Results:

- `/handsfree/imu`: present in 36/36 trajectories
- `/velodyne_points`: present in 36/36 trajectories
- camera image: present in 34/36 trajectories
- `/camera/imu`: present in 34/36 trajectories

`street_09` and `street_010` do not contain either audited camera stream.
The Phase-3 successor manifest therefore removes those nonexistent streams
from those two trajectory records rather than fabricating their presence.

Total admitted estimator-stream entries in the successor manifest: 140.

## Structural timestamp findings

Message decoding errors across the audited target streams: 0.

Exactly one strict reversed sensor-header timestamp was observed:

- trajectory: `hall_05`
- topic: `/camera/imu`
- previous sample index: 53375
- current sample index: 53376
- timestamp delta: -49.212455 ms

A targeted second scan reproduced that exact reversal.

No numerical threshold is required to identify a reversed timestamp.

No automatic repair or sample-exclusion rule has been created.

## Large monotonic camera-IMU startup/header anomalies

Large monotonic `/camera/imu` timestamp discontinuities were observed in:

- `lift_02`
- `street_06`
- `room_dark_03`
- `walk_01`
- `gate_02`

The largest observed discontinuities were approximately:

- `lift_02`: 852.498 s
- `street_06`: 242.019 s
- `room_dark_03`: 107.928 s
- `walk_01`: 91.422 s
- `gate_02`: 76.274 s

These remain diagnostic observations.

Because they are monotonic, this audit does not convert them into invalid
samples merely from their magnitude.

No global fixed timestamp offset is justified by this evidence.

## Pairwise timing characterization

Nearest-neighbor header-time comparisons were computed for selected
camera/IMU/LiDAR pairs.

Typical trajectory-level medians are in the low-millisecond range.

However:

- nearest-neighbor proximity is not synchronization proof;
- the numeric common header-range intersection is not a validity mask;
- common-range-only statistics do not authorize automatic edge/startup
  exclusion;
- observed distributions were not used to select an evaluation tolerance.

## Immutable artifacts

Phase-3 timing evidence index:

`manifests/m2dgr_timing_evidence_index_v1.json`

Index content SHA256:

`f2b1a74cb67124ec6fa725a23e3d8be8d2bd3d9d431590ad29ca1235dab149d6`

Index file SHA256:

`70f8dbf16b2363c55fa180a8180d7fbc322495c25790498ddf64fb4d74c87b3f`

Phase-3 timing-audited successor manifest:

`manifests/m2dgr_trajectory_manifest_v1_phase3_timing_audited.json`

Manifest content SHA256:

`5f8c4dcb398d684f809333307b2902231e69bb0ab51e596c95b3f62d6f652299`

Manifest file SHA256:

`5f7f7b14b89c9e9ef8f13aa3ed627c32b0409baca652238cc27c303554c666ea`

The Phase-2 manifest remains unchanged.

Bag payloads were not rehashed during Phase-3 metadata finalization. Existing
verified bag checksum sidecars and Phase-2 integrity provenance were
cross-checked against all timing artifacts and the timing index.

## Reproducibility tools

Repository tools:

- `tools/audit_m2dgr_phase3_timing.py`
- `tools/audit_m2dgr_exact_header_anomaly.py`
- `tools/finalize_m2dgr_phase3_timing.py`

The expensive all-trajectory audit should be run detached on the workstation.

## Scientific state after Phase 3A

Verified/established:

- actual target-stream presence per trajectory
- sensor header timestamps are readable measurement-time fields
- timing artifacts exist for all 36 trajectories
- bag checksum provenance agrees across Phase-2 and Phase-3 evidence
- exact `hall_05` reversed header timestamp evidence

Still unresolved:

- cross-stream synchronization verification
- reference-to-estimator temporal association
- numerical association tolerance
- any justified fixed time offset
- timestamp/sample repair policy
- continuous-time reference coverage
- evaluation readiness

Therefore:

- synchronization verified: FALSE
- fixed offset estimated: FALSE
- synchronization tolerance frozen: FALSE
- automatic sample-exclusion rule created: FALSE
- evaluation ready: FALSE
