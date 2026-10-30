# TRUST-ROBOT R135 — A27/A28/A29 Offline Readiness Audit V1

## Scope

This audit documents structural calibration inspection,
reproducible validation of a previously completed seven-stream
ROS bag audit report, and the fail-closed fusion-interface boundary.

No new physical capture, robot motion, or independent
ground-truth experiment was performed.

## A27 structural calibration review

The installed calibration contained 12 sensor records.
The inspected nominal URDF contained 37 links and 36 joints.

The nominal calibration used named quaternion components
and named XYZ translation components.

The physical IMU publishes `bmi088_frame`, which was not
declared in the inspected nominal URDF. The relationship
to the expected IMU or robot platform frame remains unresolved.

Neither the original calibration checksums nor internal
geometry checks qualify metric physical accuracy.

## A28 physical bag evidence

The previously recorded stationary ROS 2 bag contains
843 messages across seven streams and approximately
1.415 GB of original recorded bag files.

The original R135-A28-3 audit checked bag-file hashes,
SQLite consistency, ROS deserialization and payload shapes.

The A28-4B validator verifies the SHA-pinned private
A28-3 audit report against a strict, bounded summary contract.

The original report uses the descriptive scope:

`FULL_BAG_INTEGRITY_AND_ROS_DESERIALIZATION_VERIFIED_ONLY`

It does not claim physical clock accuracy, independent
sensor synchronization, calibrated geometry or pose accuracy.

The A28-4B validation examines the existing report.
It does NOT deserialize the original bag again or
independently recheck its message-type records.

Observed exact stereo ROS header-stamp matches do not
prove synchronized hardware exposure.

The original raw bag remains private on the robot SSD.

## A29 integration boundary

The A29-1 implementation accepts restricted
metadata-only descriptors for interface exercises.

It rejects unrecognized input fields and never creates
physical sensor factors or estimates physical poses.

Existing synthetic 15D estimator modules were inspected
at the static interface level. This is not physical
estimator integration or real-world factor admission.

Before physical integration, independent verification
is required for event-time semantics, frame transforms,
intrinsics/extrinsics, clock synchronization and reference pose.

## Scientific restrictions

- M2DGR scientific gates: 11 CLOSED.
- Real factor admission: DENIED.
- Frozen split: 22 train, 7 validation-calibration,
  7 confirmation-test sequences.
- No confirmation-test retuning or held-out access.
- A23 independent evidence qualifications: 0 of 13.
- Physical clock accuracy: UNVERIFIED.
- Metric physical calibration: UNVERIFIED.
- Independent six-DoF ground truth: UNVERIFIED.
- Physical localization accuracy: NOT ESTABLISHED.
- Physical fault-health probability calibration: NOT ESTABLISHED.
- Learned physical sensor factor weighting: NOT AUTHORIZED.

## Next scientific work

Resolve the IMU frame identity and establish a defensible
sensor-frame convention. Obtain independent timing and
metric calibration evidence. Prepare metadata-only
offline replay inputs and a preregistered independent
trajectory evaluation protocol.

No localization accuracy or robot-control claim is made.
