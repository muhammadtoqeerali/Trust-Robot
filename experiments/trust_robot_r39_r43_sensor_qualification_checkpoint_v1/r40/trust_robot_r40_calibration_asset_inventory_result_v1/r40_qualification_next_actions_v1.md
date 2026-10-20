# R40 — Existing calibration and reference evidence inventory

All findings are provenance or candidate inventory only; NOT QUALIFIED as physical calibration.

## Frozen room_02 reference

- Reference family: mocap (mocap).
- Source reference-quality index reports 90 invalid rotation records and 0 invalid translation records.
- Reference body origin, mocap-to-LiDAR transform and reference timestamp physical-event semantics remain unverified.

## Existing timing evidence

- `/camera/color/image_raw/compressed` uses `camera_color_optical_frame` / `m2dgr_camera_image_header_clock_unverified`; physical clock offset unverified.
- `/camera/imu` uses `camera_imu_optical_frame` / `m2dgr_camera_imu_header_clock_unverified`; physical clock offset unverified.
- `/handsfree/imu` uses `base_link` / `m2dgr_handsfree_header_clock_unverified`; physical clock offset unverified.
- `/velodyne_points` uses `velodyne` / `m2dgr_velodyne_header_clock_unverified`; physical clock offset unverified.

## Local asset observations

- Candidate files discovered: 10
- Explicit room_02 reference path receipts found: 0 of 7

- `repository_configs/embedded/embedded_reference_path_contract_v1.json`: 5666 bytes; SHA256=175059822fa16314e5117fa56557280aec831ed8b1c551cee1163e627d1d9d4f; NOT QUALIFIED
- `repository_configs/integrity/integrity_calibration_protocol_v1.json`: 11114 bytes; SHA256=18adfae600ca69211b9ccbd647fe72658da0209dd9f1d1ae5bd0351f64561e6e; NOT QUALIFIED
- `repository_configs/ood/ood_calibration_protocol_v1.json`: 11357 bytes; SHA256=a118d39cee4847dd86f41662ffd036a8bae8bcc0551ff5572f83d52ea5c2a862; NOT QUALIFIED
- `repository_configs/trust_robot/phase5_camera_imu_diagnostic_channel_contract_candidate_v1.json`: 5988 bytes; SHA256=de6656d35e24162dcd3ff489f21b735396c2457dae526a13be9790bb88bdf485; NOT QUALIFIED
- `repository_configs/trust_robot/phase5_camera_imu_observation_adapter_candidate_v1.json`: 1438 bytes; SHA256=1dd104b036e46b94990600e5484a465081a7f7f95adaa2b17b634838f222d8cd; NOT QUALIFIED
- `repository_configs/trust_robot/phase5_camera_imu_train_ingestion_candidate_v1.json`: 1974 bytes; SHA256=4a1794c81528bcd04165e4da52b60e10b5140a0a276452aa2cf269a4d66c3b9b; NOT QUALIFIED
- `repository_configs/trust_robot/phase6_probabilistic_calibration_contract_candidate_v1.json`: 4376 bytes; SHA256=7761cf8c39620d7166c88092470aeb09e2f5b1120cd0d4be3e1c11118822f367; NOT QUALIFIED
- `repository_configs/v2/imu_reliability_v2_competitor_and_benchmark_protocol_candidate_v1.json`: 19870 bytes; SHA256=575323cd2e65baf4161cb389ec2ec18b2ed7d99962d9aa882d75d2c5acc55379; NOT QUALIFIED
- `repository_configs/v2/imu_reliability_v2_competitor_and_benchmark_protocol_candidate_v1b.json`: 24052 bytes; SHA256=e7e18f31860309e43e91829ede6544060d984f6e24d3b615f3adc5304c12d238; NOT QUALIFIED
- `repository_configs/v2/imu_reliability_v2_competitor_and_benchmark_protocol_v1.json`: 25351 bytes; SHA256=a3a69e182ee1c2bb0744805b4c8a24aab77b0fb573fe26b19e18622e18c55ac1; NOT QUALIFIED

## Blocking qualifications

- camera intrinsics and distortion: UNVERIFIED
- camera to imu extrinsic: UNVERIFIED
- camera to lidar extrinsic: UNVERIFIED
- handsfree imu to lidar extrinsic: UNVERIFIED
- imu bias noise and gravity: UNVERIFIED
- physical capture clock and interstream offset: UNVERIFIED
- lidar scan effective time: UNVERIFIED
- mocap body origin to lidar transform: UNVERIFIED
- room 02 reference data quality and time association: UNVERIFIED

## Next — R41

Inspect the actual in-scope candidate file structure, units, transform direction, clock origin and TRAIN reference validity; preserve all prior frozen judgments and do not infer physical calibration from file presence.

No confirmation-test data or original bag bytes were opened.
