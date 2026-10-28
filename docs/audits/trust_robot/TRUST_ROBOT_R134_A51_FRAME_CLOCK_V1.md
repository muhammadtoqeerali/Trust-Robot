# R134-A51 recorded frame and clock provenance

Status: **metadata audited; physical frame and capture-clock
certification remain unresolved**.

## Recorded metadata

The R134-A51 read-only UNIVER audit examined Hilti-Oxford 2022
`exp14_basement_2.bag`, without opening ground truth.

- 76 inspected camera headers consistently named
  `cam0_sensor_frame`.
- 11,003 inspected Alphasense IMU headers consistently named
  `imu_sensor_frame`; no nonmonotonic IMU header timestamps
  were found in the inspected interval.
- Neither `/tf` nor `/tf_static` was present in the bag.
- No cam0 `CameraInfo` connection was present.
- The existing Kalibr YAML declared `timeshift_cam_imu`
  as 1.90712 ms; no offset was fitted.

In all four inspected groups, the minimum, median and maximum
differences between bag-recording time and message-header
time printed as 0.0 ms at four decimal places.

This does not establish independent nanosecond equality,
clock traceability, latency, or PTP lock. In particular, the
bag-recording timestamp is not a separately certified hardware
capture-time reference.

Observed median intervals in the early bag segment:

| Stream | Median interval | Approximate rate |
|---|---:|---:|
| cam0 | 24.9973 ms | 40 Hz |
| Alphasense IMU | 2.505 ms | 399 Hz |

These are recorded intervals, not certified acquisition settings.

## Publisher and manufacturer documentation

The Hilti 2022 FAQ calls the camera frames C0-C4 and
the Alphasense IMU frame I. It does not provide a
recording-specific mapping from those labels to the
observed ROS `header.frame_id` strings.

The manufacturer's Core Research documentation describes
three possible timestamp modes:

1. Raw internal device time.
2. Device time translated into the host time frame.
3. PTP-synchronized device time.

It also describes camera timestamps at exposure midpoint
and configurable IMU operation at 400 Hz.

The manufacturer documentation is pinned to revision
`6280dd64b7271b8a26a21c1703f38086d636a2b2`:

- `pages/time_synchronization.md`
  Git blob `b6115e8a4c8cd6ac567d5fd53c0ab20c3e082f2f`
- `pages/sensor_settings.md`
  Git blob `d048ee893aa3a90dcdf852d0413594632477dc9a`

Reference:
https://github.com/sevensense-robotics/core_research_manual

This describes manufacturer capabilities only. The exact
driver/firmware revision, configuration, selected time mode
and PTP lock state for the 2022 recording remain unknown.
Do not assume example/default settings were active.

The Hilti 2023 hardware documentation uses a different
camera-frame spelling and cannot certify the 2022 aliases.

## Scientific decision

The previously published A48 result supports numerical
consistency between the publisher's URDF calibration and
the local Kalibr transform. That result remains valid
as source-consistency evidence.

A51 adds internal ROS metadata consistency, but does not
complete the remaining physical-frame or clock provenance.

No real metric pose, uncertainty, estimator factor,
health label or new calibration was produced.

All 11 M2DGR scientific gates remain CLOSED. The frozen
22 TRAIN / 7 CAL-VAL / 7 confirmation-test partition
is unchanged; confirmation-test data was not accessed.

## Evidence quality and next step

The accompanying JSON transcribes user-supplied A51 terminal
results and pinned manufacturer document identities. The
tests verify transcription and declared scientific limits,
not independent bag reproduction or signed provenance.

A future physical admission decision requires
recording-specific frame mapping and timing evidence,
such as the original 2022 driver/rig configuration and
verified synchronization records.

Neither same-field timestamp values nor manufacturer
documentation alone can supply that certification.
