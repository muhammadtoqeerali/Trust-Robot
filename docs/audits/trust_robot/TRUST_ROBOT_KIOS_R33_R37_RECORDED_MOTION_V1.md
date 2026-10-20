# TRUST-ROBOT KIOS R33–R37 recorded camera and IMU diagnostics checkpoint

Checkpoint date: 2026-10-20.

Parent Git SHA:
`ebfd02b0ef8ad79b2e6a9810897fcb71efec2e87`

Branch:
`kios-isaacsim-v15-integration`

Archive:
`experiments/trust_robot_r33_r37_recorded_motion_checkpoint_v1/`

Original M2DGR TRAIN recording:
`room_02.bag`

Original bag SHA256:
`ee621ccb1a37cc19edb1424c39de9b9a2223f9dbc9b0b3dcb4e4b849e9f72ac1`

The recording stays outside GitHub.

## Engineering evidence

R33 authenticated 16 JPEG frames across eight pairs and independently checked feature displacement (approximately 0.023–22.674 pixel median range). The original R33 baseline-equality failure and repaired readers remain archived alongside their repair provenance.

R34 authenticated 32 IMU messages in 16 short intervals spanning two sensors.

R35 independently reviewed 16 IMU intervals, preserving different native IMU frames and unknown-orientation covariance sentinels (camera 16/16; HandsFree 0/16).

R36 authenticated 48 IMU messages across 16 three-sample gyro windows, independently recomputing SO(3) numerical candidates with quaternion arithmetic.

R37 SHA-pinned 21 earlier artifacts, independently checked report lineage and rejected 23 negative promotion/readiness controls.

## Scientific gates

The checkpoint is nonfactor development evidence only.

No calibrated camera motion, inertial robot pose, physically verified capture clock, cross-modal synchronization, full extrinsics, pose ground-truth scoring, covariance/health calibration, real estimator factors, trained health models, or robot safety actions are established.

No confirmation-test trajectories were used in these phases.

Next: develop and qualify better-constrained real-data single-modality estimates and physical calibration/timing before any gated real fusion.

Maintain independent verification and the frozen trajectory split. Do not infer sensor trust or pose accuracy from current engineering diagnostics.
