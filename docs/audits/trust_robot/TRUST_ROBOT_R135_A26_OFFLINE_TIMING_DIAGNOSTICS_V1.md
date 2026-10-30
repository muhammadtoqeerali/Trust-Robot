# TRUST-ROBOT R135-A26 — Offline timing diagnostics (unqualified)

**Decision:** INTEGRITY-VERIFIED DESCRIPTIVE DATA ONLY; NOT physical clock or calibration qualification.

## Source provenance

- Private metadata SHA-256: `3e74331a8884ec0f7ef0fbed31b78cabefd203c8d6e9ae610a3c0ea52179afc4`.
- Private transfer manifest SHA-256: `4e5e29aad3a2d5c17bcaa85dff185e3390804c114c7b6315ea6d516edc850771`.
- This public audit contains aggregates only; source logs, images, timestamps and host network configuration are not committed.
- The source manifest verifies copy integrity and metadata consistency, not independent physical origin.

## Recorded stream intervals (descriptive only)

| ROS stream | Recorded callbacks | Header median interval (ms) | Header max gap (ms) | Header span (s) | Arrival span (s) |
|---|---:|---:|---:|---:|---:|
| imu | 848 | 10.02224 | 40.08832 | 8.75942 | 8.13594 |
| left | 16 | 33.328 | 66.674 | 0.56665 | 0.45868 |
| right | 16 | 33.329 | 100.002 | 0.66664 | 0.54577 |
| left_info | 208 | 33.328 | 66.675 | 7.13314 | 6.93085 |
| right_info | 212 | 33.328 | 66.675 | 7.09981 | 6.88862 |
| lidar | 139 | 99.998 | 199.98383 | 13.89983 | 13.89865 |

Values are computed from ROS message headers and subscriber callback timestamps. They are NOT independently validated sample, event, or transport latencies.
Thresholded gaps reflect differences from the sample median; they do NOT prove hardware dropout.

## Stereo and clock-field observations

- Shared numeric left/right image headers: **13**; unmatched headers: left **3**, right **3**.
- Matched-image callback arrival gap median: **74.91558 ms** (not exposure-time offset).
- Clock correlation record count: **13**.
- Raw clock-field integer differences and reported `phc_latency` are NOT assigned physical units or interpreted as clock accuracy.
- Header agreement alone never establishes stereo exposure synchronization or LiDAR-to-IMU alignment.

## Explicit outstanding qualification requirements

1. Independent clock-domain documentation and event-time definitions for IMU samples, camera exposure, LiDAR cloud/point timestamps, and reference sensors.
2. Independent camera intrinsic and sensor-to-sensor metric-extrinsic validation with uncertainties, not only checksum-matching calibration files.
3. Bounded raw multi-sensor ROS bag capture with provenance, rate/drop monitoring, disk capacity and safe cleanup. No motion during initial capture.
4. Separate independent six-DoF reference and prospective scoring protocol before any accuracy or scientific admission claim.

## Research status and safeguards

- All 13 original A23 independent-evidence requests remain unfulfilled and all 11 original M2DGR gates remain CLOSED.
- The Nova Carter recording does not modify the M2DGR frozen 22/7/7 partition or the held-out confirmation restrictions.
- Real localization factors: **DENIED**. Clock accuracy, calibration, independent ground truth: **UNVERIFIED**.
- No robot sensor process or movement command was run by this offline audit.
- No web portal or Vercel deployment is modified. Future read-only monitoring requires authenticated telemetry and stream access.
