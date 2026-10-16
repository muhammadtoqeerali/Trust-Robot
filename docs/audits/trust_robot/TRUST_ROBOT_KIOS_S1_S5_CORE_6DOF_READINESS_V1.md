# KIOS S1–S5 core 6DoF readiness audit

Date: 2026-10-16
Parent commit: `79a2abf6de6ff68df23de8bd04b538ce0c95b46b`
Archive: `experiments/trust_robot_s1_s5_core_6dof_readiness_v1/`

S1: 36 M2DGR trajectories, frozen TRAIN/VALIDATION/CONFIRMATION 22/7/7; 140 unverified sync entries; 16 existing estimator module/test pairs inventoried; no scoring or empirical health training authorization.

S2: system Python NumPy 1.21.5, SciPy 1.8.0, pytest 6.2.5; nine selected regression suites, 104 passing synthetic tests; eight recorded factor rejections.

S3: four distinct TRAIN metadata-only camera, camera-IMU, handsfree-IMU and LiDAR streams; 41 unit tests passed; no raw sensor records or pose factors.

S4: 55 tests passed and corrected verifier passed; 32 sensor/time/calibration/reference/factor-noise requirements remain closed. Bag integrity is not calibration, partial relative rotation is not a complete extrinsic transform.

S5: verified S1–S4 evidence and 32 refused scientific promotions; S5 docstring check repaired with unchanged Git estimator code.

All 28 source/test/report/JUnit artifacts are SHA-pinned in the archive manifest; superseded verifier backups, raw bags and databases excluded. No new acquisitions, real pose factors, GT scoring, learned health labels, live simulation, or physical-robot tests from S1–S5.

Next S6: extend synthetic same-edge independent camera and LiDAR factor representation with separate covariances, with regression and spoofed recorded-origin negatives. Do not permit real-sensor factor admission or M2DGR scoring.
