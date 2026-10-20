# TRUST-ROBOT R39: Recorded sensor-motion qualification plan

Based only on frozen TRAIN `room_02` engineering evidence. **Do not treat any item below as calibrated pose accuracy.**

## Measured engineering evidence

| Stream | Observed diagnostic | Qualification |
|---|---|---|
| LiDAR | 8 adjacent scan pairs; median NN RMSE reduction 0.007394 m; maximum forward/reverse round-trip discrepancy 0.107653 m, 2.527491 deg | Not independently pose-scored |
| Camera | 8 frame pairs, 16 frames; median-of-pairs pixel displacement 9.256030 px; minimum tracked fraction 0.895000 | Not a metric camera pose |
| Camera IMU | Native frame `camera_imu_optical_frame`; header interval median 4.978776 ms; orientation-unknown 16/16 | Capture clock and calibration unverified |
| HandsFree IMU | Native frame `base_link`; header interval median 6.909012 ms; orientation-unknown 0/16 | Capture clock and calibration unverified |

## Blocking scientific qualifications

- **physical capture clock: NOT QUALIFIED.**
- **camera intrinsics distortion: NOT QUALIFIED.**
- **camera metric scale: NOT QUALIFIED.**
- **lidar registration accuracy and covariance: NOT QUALIFIED.**
- **imu bias noise gravity: NOT QUALIFIED.**
- **cross sensor extrinsics: NOT QUALIFIED.**
- **independent SE3 reference: NOT QUALIFIED.**
- **validation calibrated factor covariance: NOT QUALIFIED.**
- **health label supervision: NOT QUALIFIED.**

## Prioritized next implementation phases

- **R40:** Inspect native calibration, camera intrinsics/distortion, LiDAR-IMU-camera extrinsics, TF frames, clock sources and independent TRAIN references; log exact provenance and missing items without promoting filename matches. **Acceptance evidence:** Create asset inventory and explicit unverified-calibration ledger on TRAIN-only data.
- **R41:** Establish separate message-header vs acquisition-clock semantics and estimate inter-stream offset/drift using TRAIN only; verify capture-time basis independently. **Acceptance evidence:** Document time-domain conversion, residual statistics, sensitivity and rejection criteria before motion factors.
- **R42:** Verify camera intrinsics and distortion; develop outlier-robust image correspondence/epipolar geometry and an independent metric scale source. **Acceptance evidence:** Evaluate relative geometry without asserting metric motion until scale and external reference pass.
- **R43:** Develop LiDAR correspondence robustness, initialization and degeneracy rejection across multiple TRAIN trajectories, with independent registration reference and covariance diagnostics. **Acceptance evidence:** Predeclare factor rejection criteria using calibration/validation only.
- **R44:** Estimate gyro/accelerometer bias and noise, gravitational frame conventions and IMU extrinsics; compare calibrated inertial windows against independently verified references. **Acceptance evidence:** Only then implement covariance-aware preintegration with numerical and physical checks.
- **R45:** Qualify independent timestamp-associated SE3 reference, coordinate transforms, validation-calibrated factor covariance and frozen estimator variants. **Acceptance evidence:** Begin limited TRAIN/validation real-backbone trial only after prior gates; leave confirmation_test held out.

## Safety and split restrictions

The original 15 GB bag was not reopened in R39. TRAIN and calibration may support engineering and model selection; the original confirmation-test split must remain untouched. No real factors, health labels/model training, ATE/RPE scoring, or robot safety claims are authorized.
