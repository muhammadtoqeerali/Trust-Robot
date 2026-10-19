# TRUST-ROBOT R22–R25 authenticated TRAIN diagnostic archive

Contents: **25 SHA-pinned** small source, test, JSON evidence and JUnit files from off-Git KIOS R22–R25. This archive is additive to the prior R17–R20 checkpoint; neither checkpoint contains the original ~15 GB M2DGR ROS bag.

Run `python3 -B verify_checkpoint.py` in this directory or by absolute path after cloning GitHub. The verifier is independent of the experiment engines and requires no raw recording, ROS installation, or pytest. Documentation hashes are commit-scoped to preserve earlier archives after future commits.

These are descriptive diagnostics from 8 and 32 bounded TRAIN samples, in-memory negative controls, and 197 existing software regression tests. They are **not** physical camera/LiDAR/IMU synchronization evidence, statistically representative sensor-health diagnostics, real 6DoF pose estimation, qualified estimator factors, independent GT scoring, ATE/RPE, calibrated model probabilities or permission for live robot/simulator use.

Source recording: `room_02.bag`; TRAIN only; immutable SHA256: `ee621ccb1a37cc19edb1424c39de9b9a2223f9dbc9b0b3dcb4e4b849e9f72ac1`.
