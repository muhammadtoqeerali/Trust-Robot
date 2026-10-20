# TRUST-ROBOT R33–R37: TRAIN-only recorded visual / inertial diagnostics

This checkpoint preserves 26 original small R33–R37 source and evidence files. R33 initial failures (`*.py.saved`) and targeted repair provenance are retained byte-for-byte.

Run `python3 -B verify_checkpoint.py` from this archive to check SHA pins, evidence lineage, project documentation and scientific gates without the raw ROS bag.

R33: eight genuine adjacent camera-frame pairs (16 distinct JPEG messages) with feature tracking and independent LK recomputation. Median pixel motions vary between 0.023 and 22.674 pixels.

R34: two IMU streams, 16 two-sample intervals, 32 genuine recorded IMU messages, descriptive trapezoid integrals only.

R35: IMU header-time variation and frame semantics, with 16/16 camera IMU orientation-unknown sentinels and 0/16 HandsFree IMU orientation-unknown sentinels.

R36: 16 three-sample gyro windows using 48 genuine IMU messages, independently verified via quaternion arithmetic.

R37: separately and independently verified no-bag readiness audit.

The original room_02.bag and frozen 22/7/7 trajectory split remain unchanged.

No valid camera metric scale, physical time synchronization, IMU bias/gravity correction, full cross-sensor extrinsics, independent pose accuracy, real 6DoF factors, health model training, M2DGR scoring, or real-robot safety actuation is established.

Results are numerical and descriptive development candidates, NOT scientific localization performance.
