# TRUST-ROBOT R135-A27-4 / A29-3 Offline Envelope Audit

## Purpose

Prepare a bounded metadata-only replay layer for the
previously verified seven-stream stationary Nova Carter
ROS 2 SQLite3 bag.

The extraction reads ROS bag topic identifiers, recorded
timestamps and serialized message sizes. It does not select
the serialized image, pointcloud or IMU payload columns.

The original capture contains 843 messages in seven streams.
The private envelope analysis is cross-checked against the
SHA-pinned R135-A28-3 full-bag audit report.

## Scientific timestamp boundary

A SQLite rosbag recorder timestamp must not be substituted
for a sensor message header timestamp.

The envelope records deliberately contain null
`header_stamp_ns` and null `frame_id` fields.

The timing origin, physical event definition, clock
correlation, hardware exposure synchronization and
LiDAR per-point time semantics are not qualified.

## Frame boundary

The physical IMU publishes `bmi088_frame`. An equivalent
frame declaration was not found in the inspected nominal
URDF. No IMU-to-platform mapping is assumed.

Named calibration quaternions and finite structural
transforms are not independent proof of metric extrinsics.

## Estimator integration

The A29-3 adapter validates metadata envelopes only.

It explicitly refuses to convert an unqualified recorder
envelope into a physical fusion descriptor.

No 15D estimator invocation, sensor-factor creation,
physical pose estimation or localization scoring occurs.

## Scientific constraints

- M2DGR scientific gates: 11 CLOSED.
- Real factor admission: DENIED.
- Frozen split: 22 train, 7 validation-calibration,
  7 confirmation-test sequences.
- No confirmation-test inspection or retuning.
- A23 qualified independent evidence receipts: 0 of 13.
- Physical clock accuracy: UNVERIFIED.
- Metric calibration validity: UNVERIFIED.
- Independent trajectory ground truth: UNVERIFIED.
- Real localization accuracy: NOT ESTABLISHED.
- Physical health probability calibration: NOT ESTABLISHED.

## Evidence limitations

The original full-bag audit remains the authoritative
source for completed file-hash and deserialization checks.

A29-3 separately checks a metadata-only SQLite view
against its pinned aggregate report. It does not recompute
full original bag-file hashes or deserialize all messages.

Raw physical envelopes and detailed geometry remain
outside the Git repository in private evidence storage.

Future physical measurement admission requires independent
clock, transform, reference and uncertainty qualification.
