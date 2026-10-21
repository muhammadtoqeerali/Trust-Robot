# R74 — Independent M2DGR source admissibility review

Trajectory: room_02 (TRAIN only).

## Verified evidence

- Original ground-truth recovery and Phase-2 quality replay remain valid.
- 3,831 reference records were structurally audited.
- 90 structurally invalid rotations occur in 61 sample-index runs.
- Published author material describes a Vicon Vero 2.2 system at nominal 50 Hz.
- Published calibration contains 15 LiDAR-extrinsic headings but no explicit
  mocap calibration entry.
- Verona R70, R71A and R72 source reports were SHA-verified after transfer.
- KIOS independently compared those reports with frozen repository evidence.

## Scientific restrictions

- The observed sampling cadence does not qualify physical synchronization.
- No mocap rigid-body physical origin is established.
- No mocap-body-to-LiDAR SE(3) transform is established.
- Reference capture-event and clock/export semantics remain unverified.
- No interpolation, automatic rotation repair, ATE/RPE, real pose factors
  or health training are authorized.
- All 11 scientific gates remain closed.
- confirmation_test remains sealed.

## Publication boundary

This summary and derived R74 reports contain no raw GT, ROS bags,
private file inventories or copied original source excerpts.

The original transferred reports remain private on KIOS.

Next: create a guarded GitHub checkpoint for the sanitized R70–R74
scientific evidence, retaining historical evidence without modification.
