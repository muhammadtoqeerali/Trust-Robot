# TRUST-ROBOT R39–R43: Recorded sensor qualification checkpoint

This checkpoint preserves 33 SHA256-pinned R39–R43 sources, tests, and evidence artifacts. The initial R40 failed reader and targeted repair provenance are included.

- R39: Diagnostic LiDAR/camera/IMU motion statistics and nine unqualified physical calibration requirements.
- R40: Eleven frozen provenance manifests; ten local software candidates; zero explicit room_02 reference paths. Frozen mocap quality records 90 invalid rotations. Original failed and repaired readers preserved.
- R41: Ten Git-identical software contracts/protocols, but no physical calibration; no room_02 reference candidate or matching reference checksum found.
- R42: Fifteen independently verified ROS1 connection headers, no CameraInfo, TF/TF-static or embedded mocap reference topics. No sensor payload decompressed.
- R43: Ten Git-frozen manifests, eleven unresolved physical-evidence gates, eleven fully unfilled source receipts; zero new external sources.

Run `python3 -B verify_checkpoint.py` to verify this archive and its scientific gates without opening the original bag.

The original TRAIN room_02.bag remains outside GitHub. The frozen 22 TRAIN / 7 validation_calibration / 7 confirmation_test trajectory split is unchanged.

No physical capture-time verification, complete extrinsics, metric real-pose accuracy, independently qualified mocap reference, real estimator factors, health labels/training, ATE/RPE scoring or autonomous safety action is established.

Next: seek physically traceable calibration/reference evidence and independently validate it before any scientific sensor-factor admission.
