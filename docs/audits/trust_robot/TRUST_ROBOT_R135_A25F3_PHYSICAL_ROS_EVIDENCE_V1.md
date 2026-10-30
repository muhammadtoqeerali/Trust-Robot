# TRUST-ROBOT R135-A25F-3 — Physical ROS evidence diagnostic audit

**Status:** offline integrity and internal-consistency review only; no independent physical qualification.

## Provenance

- Nova Carter A25E-3 metadata SHA-256: `3e74331a8884ec0f7ef0fbed31b78cabefd203c8d6e9ae610a3c0ea52179afc4`.
- Private transfer manifest SHA-256: `4e5e29aad3a2d5c17bcaa85dff185e3390804c114c7b6315ea6d516edc850771`.
- Physical source bytes, raw launch logs, and host-specific network details are **not committed**. Evidence remains in the private KIOS inbox outside the Git checkout.
- Source launch files were pinned at capture. A prior Jetson test reported clean launch-group, ROS graph, and driver-process shutdown. This report does not independently attest the physical robot or operator.

## Observations (not validated performance)

- Concurrent physical ROS publishers: 848 BMI088 IMU messages, 16 left and 16 right Hawk RGB images, 208/212 camera-info messages, 139 Hesai point clouds, and 13 correlated-timestamp messages.
- Median observed header intervals: IMU 10.02224 ms; left/right images 33.328/33.329 ms; left/right camera info 33.328 ms; LiDAR 99.998 ms.
- 13 distinct left/right image header timestamps match exactly; 3 observed timestamps on each side were unmatched. Receive latency differences do not establish physical camera desynchronization.
- Header/ROS-arrival spans differ. IMU maximum observed header gap was 40.08832 ms; LiDAR maximum was 199.98383 ms. Buffering, missed samples, and timestamp semantics are not resolved.
- Recorded PHC-related fields are internally ordered, but field units, physical clock accuracy, sensor timestamp semantics, PTP performance and cross-sensor synchronization are **not validated**.
- ROS `orientation_covariance[0] = -1` in earlier BMI088 testing indicated no orientation estimate; zero covariance values do not prove calibrated uncertainty.

## Verification semantics

`physical_ros_evidence_v1.py` checks the original manifest, copied artifact hashes and sizes, declared ROS measurement counts, timestamp monotonicity, stereo timestamp accounting, and explicit closed-gate boundaries. Its synthetic unit tests use no private sensor data and no ROS, network or dataset access.

The transfer manifest and original metadata were both generated within the acquisition/transfer workflow; **matching hashes and internal consistency do not establish independent origin, calibration, clock synchronization, ground truth, or scientific admission**. The 13 original A23 prospective independent-evidence requests remain unfulfilled unless separately independently witnessed. The original 11 M2DGR gates remain **CLOSED**. This Nova Carter evidence must never be substituted for M2DGR dataset ground truth or held-out confirmation evidence.

No real measurement factors, health interpretations, autonomous navigation, robot motions, or localization accuracy claims are authorized by this audit.
