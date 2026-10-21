# R51 — TRAIN room_02 sampled timestamp and reference-evidence audit

These are header and bag-record **timestamp coordinate differences**, not measured hardware clock offsets or verified nonnegative transport latencies. Only previously decoded frozen TRAIN samples were accessed; no ROS bag bytes were reopened.

## Sampled record-time minus header-time residuals (milliseconds)

| Stream | N | Median | Min | Max | Negative residuals |
|---|---:|---:|---:|---:|---:|
| `/camera/color/image_raw/compressed` | 16 | 80.464823 | 65.466529 | 136.478633 | 0 |
| `/camera/imu` | 16 | -1.073698 | -17.287823 | 31.518415 | 9 |
| `/handsfree/imu` | 16 | 1.214427 | 0.263291 | 15.947759 | 0 |

The camera-IMU sample includes negative bag-minus-header residuals. A nonnegative transport-delay interpretation therefore fails without verified physical clock domains, event semantics and recorder mapping.

## Sparse camera-to-IMU header distances

The following are **nearest distances between only 16 preselected camera stamps and 16 sparse IMU stamps per topic**. Do not use these to estimate a fixed clock offset, fit drift, or choose temporal association tolerance.

- `/camera/imu`: median 913.530946 ms; range 28.855562–2695.799112 ms (sparse samples only)
- `/handsfree/imu`: median 881.050825 ms; range 19.579173–2643.317938 ms (sparse samples only)

## Author and frozen reference semantics

- Published camera application has `td=0` and `estimate_td=0`; these are settings, **not capture-clock calibration**.
- Original frozen TRAIN manifest lists four **unverified** sensor clock domains and supplies no fixed physical offset or tolerance.
- Frozen reference-temporal evidence does not authorize nearest-neighbor evaluation association, a fixed mocap offset or interpolation.
- Mocap index reports 90 invalid rotation records, and its body origin and timestamp event still require physical qualification.
- Camera color, camera IMU and HandsFree IMU are distinct native sensor-frame receipts.

## Next R52

If source timing metadata is obtained, qualify measurement-event definitions and independent clock mappings before calibration-driven factor fusion. Existing numerical camera and IMU diagnostics remain engineering-only.

No confirmation-test data, real pose factors, health labels, ATE/RPE, Git changes or autonomous robot actions are authorized.
