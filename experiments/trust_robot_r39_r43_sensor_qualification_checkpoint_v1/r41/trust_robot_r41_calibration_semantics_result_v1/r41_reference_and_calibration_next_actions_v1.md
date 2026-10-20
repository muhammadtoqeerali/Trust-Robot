# R41 — Configuration semantics and TRAIN mocap reference receipts

## Evidence scope

Exactly ten KIOS JSON candidates were byte-matched to the GitHub R38 commit. Their presence **does not** verify physical calibration.

## Candidate classification

- `configs/embedded/embedded_reference_path_contract_v1.json` — SEPARATE_SOFTWARE_PROTOCOL_NOT_PHYSICAL_CALIBRATION_RECEIPT
- `configs/integrity/integrity_calibration_protocol_v1.json` — SEPARATE_SOFTWARE_PROTOCOL_NOT_PHYSICAL_CALIBRATION_RECEIPT
- `configs/ood/ood_calibration_protocol_v1.json` — SEPARATE_SOFTWARE_PROTOCOL_NOT_PHYSICAL_CALIBRATION_RECEIPT
- `configs/trust_robot/phase5_camera_imu_diagnostic_channel_contract_candidate_v1.json` — TRUST_ROBOT_SOFTWARE_CONTRACT_NOT_PHYSICAL_CALIBRATION_RECEIPT
- `configs/trust_robot/phase5_camera_imu_observation_adapter_candidate_v1.json` — TRUST_ROBOT_SOFTWARE_CONTRACT_NOT_PHYSICAL_CALIBRATION_RECEIPT
- `configs/trust_robot/phase5_camera_imu_train_ingestion_candidate_v1.json` — TRUST_ROBOT_SOFTWARE_CONTRACT_NOT_PHYSICAL_CALIBRATION_RECEIPT
- `configs/trust_robot/phase6_probabilistic_calibration_contract_candidate_v1.json` — TRUST_ROBOT_SOFTWARE_CONTRACT_NOT_PHYSICAL_CALIBRATION_RECEIPT
- `configs/v2/imu_reliability_v2_competitor_and_benchmark_protocol_candidate_v1.json` — SEPARATE_SOFTWARE_PROTOCOL_NOT_PHYSICAL_CALIBRATION_RECEIPT
- `configs/v2/imu_reliability_v2_competitor_and_benchmark_protocol_candidate_v1b.json` — SEPARATE_SOFTWARE_PROTOCOL_NOT_PHYSICAL_CALIBRATION_RECEIPT
- `configs/v2/imu_reliability_v2_competitor_and_benchmark_protocol_v1.json` — SEPARATE_SOFTWARE_PROTOCOL_NOT_PHYSICAL_CALIBRATION_RECEIPT

## TRAIN room_02 reference search

Frozen reference source: mocap. The reference-quality index reports 90 invalid rotation records and zero invalid translation records.

Bounded filename search: 2 entries scanned, 0 room_02-named candidates found.

Candidates byte-identical to frozen reference checksum: 0

A matching checksum is not proof of mocap tracked origin, frame transform or physically synchronized evaluation.


## Scientific decision

Real factor admission, health training, ATE/RPE and confirmation-test access remain closed.

## R42 acceptance direction

Resolve independent camera intrinsics, cross-sensor transforms, mocap body origin and timestamp semantics from physically traceable sources. Do not infer calibration from software contracts.
