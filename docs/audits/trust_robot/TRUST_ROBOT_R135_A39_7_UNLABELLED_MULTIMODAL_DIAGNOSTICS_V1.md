# TRUST-ROBOT | R135-A39-7 | Offline multimodal diagnostics source publication

**Scope:** a deterministic, dependency-light **engineering** utility for bounded offline camera, IMU and LiDAR observations, extracted from privately validated R135-A39-6. The public code and synthetic tests contain no raw robot recordings, camera pixels, point coordinates, device passwords, private trace tables, or dataset partitions.

## Source and reproducibility

- Module: `src/trust_robot/unlabelled_multimodal_diagnostics_v1.py` (byte-identical to A39-6 private candidate, SHA-256 `3e8c56666fc6880783fe2d148f219e5fe72ce17d4032bcb38ccbec40f89d37f2`).
- Tests: `tests/trust_robot/test_unlabelled_multimodal_diagnostics_v1.py` (A39-6 synthetic tests with **only** the source-load path adjusted from the private `candidate/` directory to the public `src/trust_robot/` directory).
- Private R135-A39-6 receipt was checked by SHA-256 `1a9a3a921deed3df198fcb86d3168a68a05f0065f4068dbc1439c0619855b1c0` and exact source/test/manifest hashes before this publication. Private JSON receipts and raw sensor data are never committed.
- Reproduce the public synthetic checks with `PYTHONPATH=src python3 -m unittest discover -s tests/trust_robot -p 'test_unlabelled_multimodal_diagnostics_v1.py' -v`. No ROS installation, physical sensor, reference stream, or robot is needed.

## Observation contracts (not health-state supervision)

- `camera_diagnostics`: strict, bounded per-lane records with integer `header_ns` and separate `recorder_ns` axes plus boolean `zero_payload`. Counts wholly zero payloads and recorder interarrival observations. The thresholds of 10 ms and 50 ms are descriptive counters, **not calibrated fault decision thresholds**.
- `numeric_header_join`: matches **numeric header equality only**. Counts overlap, exclusive header stamps and zero-payload coincidence. Recorder arrival offsets and the 20 ms counter do **not** establish physical synchronization or independently qualified stereo pairs.
- `imu_descriptive_diagnostics`: magnitude summaries for acceleration and angular speed; no physical gravity reference, calibration, or sensor-health inference.
- `lidar_structural_diagnostics`: bounded reported point slots, point record stride and field-count layouts; no geometric validity, LiDAR hardware-model binding, or return-health inference.
- `public_summary_only`: explicit aggregate allowlist without timestamps or raw payload arrays. Input sizes and schemas are bounded; no network, ROS graph, file acquisition or actuator interface is provided.

## Prior observations retained without remeasurement

The **pre-existing, unlabelled** A39-1 through A39-5 Nova stationary-bag diagnostics identified 427 selected IMU envelopes, 165 decoded RGB image payloads (84 left / 81 right, first five zero in each lane), three sampled LiDAR structural envelopes, 81 exact numeric stereo header matches, three left-only header values, and 65/81 matched numerical header arrivals separated by more than 20 ms. These observations are engineering descriptors only; no causal attack, dropped-frame, health state, or sensor synchronization claim follows. No bag was reread for A39-6 or this publication.

## Hard scientific and operating boundaries

Real independently accepted `healthy/degraded/unusable` measurement-role labels: **zero**. Trained calibrated physical health model: **not qualified**. Eleven M2DGR evidence gates: **closed**. Frozen 22 TRAIN / 7 validation_calibration / 7 SEALED confirmation_test partition: **untouched**. No real estimator factor admission, independent physical GT/ATE/RPE, autonomous controller action, return-home command, or physical safety intervention is authorized.

Subsequent offline fault/degradation interventions may use synthetic fixtures or authorized TRAIN data only; their intervention tags are synthetic condition annotations, not independent health labels. Preserve source partitions and frozen protocols. Physical reference-witness acquisition, actuation, and live sensor access require separate approvals.
