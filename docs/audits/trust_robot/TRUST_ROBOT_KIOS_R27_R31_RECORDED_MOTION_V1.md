# TRUST-ROBOT KIOS R27–R31 recorded motion audit

Date: 2026-10-19.
Parent commit: `d1c8aa7811619d096865f9b5f23a0ca7e940fa81`.

Archive:
`experiments/trust_robot_r27_r31_recorded_motion_checkpoint_v1/`

## Input identity

Original M2DGR `room_02.bag` SHA256:

`ee621ccb1a37cc19edb1424c39de9b9a2223f9dbc9b0b3dcb4e4b849e9f72ac1`

The trajectory belongs to frozen TRAIN. Raw ROS bag data remain off-GitHub. No confirmation-test sequences were used.

## Engineering findings

R27: authentic LiDAR scans with 50,957 and 50,954 points. A fixed 512-point, 10-iteration registration produced initial NN RMSE 0.329971 m and candidate RMSE 0.328280 m. Independent brute-force matching agreed.

R28: twelve subset/initialization tests showed translation variation up to 0.057863 m and rotation variation up to 2.291 degrees. Artificial planar and collinear geometry controls passed.

R29: eight adjacent LiDAR scan pairs, distributed across TRAIN, involving 16 original scans. Every pair had lower final nearest-neighbor residual. Source identities and numeric outputs were independently verified.

R30: sixteen directional registrations for eight pairs. Round-trip translation discrepancies were 0.022946–0.107653 m; rotation discrepancies were 0.972847–2.527491 degrees. Geometry and directional results were independently recomputed.

R31: two consecutive authenticated 640x480 camera frames. GFTT/LK produced 400 initial features, 400 forward/backward-consistent tracks and median displacement 0.023073415420015515 pixels. Source JPEG hashes and tracking were independently verified.

## Scientific restrictions

These are descriptive engineering diagnostics. They do not establish metric camera or LiDAR pose accuracy, physically verified capture timestamps, cross-modal synchronization, complete verified extrinsics, independent ground-truth association, calibrated sensor covariance, health labels, or robust localization.

No real pose factors, M2DGR ATE/RPE scoring, health-model training, or robot safety actions are authorized.

Preserve the original recording and frozen S1–S10, R17–R20 and R22–R25 checkpoints. Next: multi-pair camera tracking and IMU motion diagnostics, with real factor admission still closed.
