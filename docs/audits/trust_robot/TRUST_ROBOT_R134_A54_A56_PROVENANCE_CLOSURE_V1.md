# R134-A54–A56: Hilti recording provenance investigation

Status: **local provenance investigation blocked pending
independent primary evidence**.

## Purpose

This checkpoint consolidates three read-only UNIVER audits
of the Hilti-Oxford 2022 `exp14_basement_2.bag` recording.

It is aggregate-only. It contains no camera, IMU, LiDAR,
ground-truth, pose or health-label measurements.

## A54: ROS bag metadata

The 74.013-second bag contained 8 topics and 8 connections.

No configuration or diagnostic topic candidates were found
in the inspected connection metadata.

Publisher caller IDs for the camera and IMU were not
recorded. Six Alphasense connections had no recorded
caller ID.

No ROS message payload was deserialized.

This does not prove the original driver lacked configuration
or synchronization. Those records may exist outside the bag.

## A55: Scoped local support-file inventory

Six Hilti-related directory roots were searched, using
a bounded maximum traversal depth of three.

The audit visited 9 directories and inspected 33 entries.
It identified 14 candidate files, principally prior
TRUST-ROBOT manifests, calibration YAML files and project
sensor-audit artifacts.

No obvious original capture-configuration or PTP log was
identified by this scoped filename inventory.

This is not proof that such files never existed, nor
a comprehensive search of every workstation location.

## A56: Six prior project manifests

Six local manifests were read with size checks and SHA256
hashes. The audit found 29 relevant key occurrences and
reported zero whitelisted scalar values.

The R130 manifest contained source-provenance field names
and scientific-status field names, including
`calibration_physically_validated` and
`physical_clock_sync_independently_proven`.

These are prior project-created evidence records. The
inspection did not establish their field values as primary
hardware attestations.

No original driver log or PTP lock log was inspected.

## Previously established results

- R134-A44: a bounded camera–IMU shadow diagnostic was
  reproduced on selected real Hilti windows.
- R134-A48: publisher-derived URDF and local Kalibr
  transforms were numerically consistent after inversion.
- R134-A51: inspected camera and IMU ROS metadata were
  internally consistent; physical frame aliases and clock
  synchronization remained unresolved.

None of these results authorizes real-factor admission.

## Closure decision

Further repeated searches of the same bag and local
project manifests are not justified without a new
primary-source lead.

Reopen recording-specific provenance investigation only
if trustworthy evidence becomes available, such as the
original driver/firmware configuration, frame mapping,
or capture synchronization logs.

The team may continue synthetic estimator and sensor-health
engineering, separately from physical admission.

All 11 M2DGR scientific gates remain CLOSED. The frozen
22 TRAIN / 7 VALIDATION_CALIBRATION /
7 CONFIRMATION_TEST partition remains unchanged.
No confirmation-test or ground-truth data was accessed.

## Evidence-quality limitation

The companion JSON transcribes user-supplied terminal
results. The tests validate consistency and declared
limits; they do not cryptographically attest the
terminal logs or independently replay UNIVER data.
