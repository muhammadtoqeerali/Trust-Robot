# R42 — TRAIN room_02 connection-level calibration gap resolution

All 15 recorded connection headers matched the frozen R17 topic, type, MD5 and message-definition SHA256 receipts.

No sensor-message payload was decompressed.

## Direct bounded evidence

- CameraInfo topic count: 0.
- TF / TF-static topic count: 0.
- Mocap or pose-reference topic count: 0.
- R41 found no local room_02 reference-file candidate.
- R41 verified ten software configuration files; none qualifies physical sensor calibration.
- Existing M2DGR evidence supports a candidate D435i IMU relative rotation, not a complete physical extrinsic.
- The room_02 mocap index reports 90 invalid rotation records. Reference body origin and physical timestamp semantics remain unverified.

A missing ROS topic does not prove that external calibration data never existed.

## Unresolved scientific requirements

- camera intrinsics physically verified: **NOT PHYSICALLY QUALIFIED**.
- camera lidar extrinsics physically verified: **NOT PHYSICALLY QUALIFIED**.
- camera imu extrinsics physically verified: **NOT PHYSICALLY QUALIFIED**.
- mocap body to lidar physically verified: **NOT PHYSICALLY QUALIFIED**.
- reference capture clock physically verified: **NOT PHYSICALLY QUALIFIED**.
- cross sensor synchronization physically verified: **NOT PHYSICALLY QUALIFIED**.
- raw reference available locally: **NOT PHYSICALLY QUALIFIED**.
- metric visual pose authorized: **NOT PHYSICALLY QUALIFIED**.
- real sensor factors authorized: **NOT PHYSICALLY QUALIFIED**.
- health training authorized: **NOT PHYSICALLY QUALIFIED**.
- m2dgr ate rpe authorized: **NOT PHYSICALLY QUALIFIED**.

## R43 — Next evidence requirement

Prepare a physically traceable calibration and reference acquisition protocol covering camera intrinsics, sensor extrinsic transform direction and translation, capture-clock mapping, mocap reference geometry, reference-file receipts and independent validation.

No confirmation-test data, pose factors, health labels or GitHub changes were authorized.
