# KIOS R22–R25: authenticated TRAIN-only diagnostic evidence

Date: 2026-10-19. Parent Git commit: `76685f1a6a97fb8e0750224bb927f1b094e63203`.
Archive: `experiments/trust_robot_r22_r25_recorded_diagnostics_checkpoint_v1/`.

## Source and evaluation boundary

M2DGR `room_02.bag` original TRAIN recording matched the frozen manifest SHA256 `ee621ccb1a37cc19edb1424c39de9b9a2223f9dbc9b0b3dcb4e4b849e9f72ac1`. The ~15 GB raw recording is NOT committed. The split remains 22 TRAIN / 7 validation_calibration / 7 confirmation_test. No confirmation-test raw sequence was read or used.

## Verified technical results

R22: eight authentic samples (2 per required camera, camera IMU, HandsFree IMU and LiDAR stream) independently decoded and recomputed. Both sampled RGB images were 640x480; two LiDAR scans yielded 50,957 and 50,954 finite XYZ points. Diagnostics only, not learned features or factors.

R23: deterministic, index-spaced bounded 32-message audit, eight samples per stream from 30 distinct chunks. Actual sampling coverage: camera 0.7188%, camera IMU 0.0577%, HandsFree IMU 0.0767%, LiDAR 1.0638%. Statistical stability NOT established; no extrapolation to entire dataset or to fault detection.

R24: 32 original TRAIN message bytes relocated independently; 128 in-memory provenance mutations and 8 semantic payload challenges rejected. Two nonfinite LiDAR examples demonstrated that descriptive statistics are not localization-frontend input admission. Never mutate the original bag or confuse metadata mutation rejection with calibrated real sensor-health detection.

R25: independent R22, R23, R24 replay files hash-identical to earlier corresponding validators; 197 targeted existing frontend regressions passed (two pytest warnings), 18 promotion/coverage negative controls rejected. Independent checkpoint readiness passed. Decision: `READY_FOR_SHA_PINNED_R22_R25_NONFACTOR_GIT_ARCHIVAL` only.

## Frozen provenance and science gates

25 small code/test/report artifacts have SHA256 pins and a standalone verifier requiring no ROS bag. R17–R20 prior archive, original R18 failure/repair, S1–S10, frozen manifest and data remain unchanged. No actual camera odometry, LiDAR scan registration, IMU preintegration, scientific recorded motion factors, measured real 6DoF pose accuracy, ATE/RPE, physical capture semantics, cross-sensor synchronization, complete verified extrinsics, independent reference-temporal qualification, learned/calibrated health labels or real risk-based suppression has been demonstrated.

## Next research implementation

Prioritize *TRAIN-only* real recorded **single-modality motion frontend candidate development** (e.g. bounded LiDAR scan pair diagnostics and/or camera relative-motion candidates) with explicit source identity, temporal/frame caveats and independent tests. Preserve factor execution DENIAL until physical science gates are established. No metadata-only loop or artificial factor admission.
