# TRUST-ROBOT R39–R43 recorded-data sensor qualification audit

Checkpoint date: 2026-10-20.

Parent commit: `df78336320b3b026e448a09d39dfc571f922ae00`.

Branch: `kios-isaacsim-v15-integration`.

Archive: `experiments/trust_robot_r39_r43_sensor_qualification_checkpoint_v1/`.

Original TRAIN bag: `room_02.bag`, SHA256 `ee621ccb1a37cc19edb1424c39de9b9a2223f9dbc9b0b3dcb4e4b849e9f72ac1`, not committed.

## Verified development evidence

R39 recomputed historical LiDAR, camera and IMU diagnostic statistics; nine independent scientific qualifications remained unresolved.

R40 verified existing provenance and calibration manifest claims; its initial incorrect mocap-field lookup was repaired using the canonical `mocap_reference_body_origin_verified` field, preserving the initial failed source and exact repair SHA256 evidence. Ten local software candidates but no explicit local room_02 reference files were discovered.

R41 independently verified ten Git-identical software configurations. Four are TRUST-ROBOT contracts and six are other protocols, none a qualified physical sensor calibration. No additional room_02 reference-file candidates or checksum matches were found.

R42 independently verified fifteen authentic ROS1 connection headers with no CameraInfo, TF/TF-static or mocap reference topic; no sensor-message payload decompression occurred. Absence of in-bag topics does not prove external calibration is unavailable.

R43 verified ten frozen dataset manifests and eleven entirely empty physical-evidence receipts, preserving all scientific qualification gates. The existing D435i IMU relative-rotation support does not certify full extrinsics.

## Unresolved science

Physical capture-clock mapping, complete sensor geometry, camera intrinsics/distortion, IMU bias and covariance, mocap tracked-body origin and mocap-to-LiDAR transform, reference timestamp association, valid pose ground truth, real estimator factors and health supervision remain unqualified.

The room_02 reference-quality index reports 90 invalid rotation records.

Confirmation-test trajectories remain sealed. No ATE/RPE scoring or health training occurred.

## Next

R45: examine physically traceable calibration/reference acquisition paths and accept future evidence only with independent source/authenticity, frame, unit, timestamp, and uncertainty verification.
