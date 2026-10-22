# R92 physical-source qualification: what is still missing

Status: evidence-gap decision only. Nothing was physically requalified.

## Findings

- Eleven original scientific receipts remain historically unfilled; no later authorization was established.
- Five sensor capture-time receipts remain historically unfilled.
- Original room_02 GT bytes were recovered locally; access is resolved, but reference-frame/time/quality qualification is NOT.
- The recovered reference has 3,831 records, including 90 structurally invalid rotations.
- The latest reviewed runtime gate still denies real recorded factors.
- No sealed confirmation-test access or new physical source intake occurred.

## Physical evidence acquisition priorities

### 1. Obtain independently checkable capture-event and clock-mapping receipts for five streams

Affected gates: cross_sensor_synchronization_physically_verified, reference_capture_clock_physically_verified

### 2. Identify tracked mocap rigid-body origin and measured mocap-to-LiDAR SE3 transform with direction, units and validation

Affected gates: mocap_body_to_lidar_physically_verified

### 3. Independently qualify camera intrinsics, camera-to-IMU and camera-to-LiDAR extrinsics, including applicable sensor frames

Affected gates: camera_intrinsics_physically_verified, camera_imu_extrinsics_physically_verified, camera_lidar_extrinsics_physically_verified

### 4. Predeclare how 90 invalid GT rotations and discontinuous reference coverage will be handled; verify temporal association and evaluation protocol

Affected gates: raw_reference_available_locally, m2dgr_ate_rpe_authorized

### 5. Only after independent qualifications, review measured factors, metric visual pose and scientifically justified health training

Affected gates: metric_visual_pose_authorized, real_sensor_factors_authorized, health_training_authorized

## Five unqualified timing streams

| Stream | Required receipt fields (historical inventory) |
|---|---|
| `camera_color` | capture_event_definition, clock_mapping_method_and_parameters, clock_offset_and_drift_uncertainty, device_model_and_serial_or_export_identifier, header_stamp_timebase_and_epoch, independent_validation_source_sha256, original_publisher_and_version, room_02_applicability_evidence_sha256, source_document_uri, source_sha256 |
| `camera_imu` | capture_event_definition, clock_mapping_method_and_parameters, clock_offset_and_drift_uncertainty, device_model_and_serial_or_export_identifier, header_stamp_timebase_and_epoch, independent_validation_source_sha256, original_publisher_and_version, room_02_applicability_evidence_sha256, source_document_uri, source_sha256 |
| `handsfree_imu` | capture_event_definition, clock_mapping_method_and_parameters, clock_offset_and_drift_uncertainty, device_model_and_serial_or_export_identifier, header_stamp_timebase_and_epoch, independent_validation_source_sha256, original_publisher_and_version, room_02_applicability_evidence_sha256, source_document_uri, source_sha256 |
| `mocap_reference` | capture_event_definition, clock_mapping_method_and_parameters, clock_offset_and_drift_uncertainty, device_model_and_serial_or_export_identifier, header_stamp_timebase_and_epoch, independent_validation_source_sha256, invalid_rotation_resolution_evidence_sha256, mocap_export_file_sha256, mocap_to_lidar_transform_and_direction, mocap_tracked_body_origin_definition, original_publisher_and_version, reference_timestamp_export_semantics, room_02_applicability_evidence_sha256, source_document_uri, source_sha256 |
| `velodyne_lidar` | capture_event_definition, clock_mapping_method_and_parameters, clock_offset_and_drift_uncertainty, device_model_and_serial_or_export_identifier, header_stamp_timebase_and_epoch, independent_validation_source_sha256, original_publisher_and_version, room_02_applicability_evidence_sha256, source_document_uri, source_sha256 |

## Eleven original gate receipts

| Gate | Latest supported interpretation |
|---|---|
| `camera_imu_extrinsics_physically_verified` | NOT_INDEPENDENTLY_QUALIFIED |
| `camera_intrinsics_physically_verified` | NOT_INDEPENDENTLY_QUALIFIED |
| `camera_lidar_extrinsics_physically_verified` | NOT_INDEPENDENTLY_QUALIFIED |
| `cross_sensor_synchronization_physically_verified` | NOT_INDEPENDENTLY_QUALIFIED |
| `health_training_authorized` | NOT_INDEPENDENTLY_QUALIFIED |
| `m2dgr_ate_rpe_authorized` | NOT_INDEPENDENTLY_QUALIFIED |
| `metric_visual_pose_authorized` | NOT_INDEPENDENTLY_QUALIFIED |
| `mocap_body_to_lidar_physically_verified` | NOT_INDEPENDENTLY_QUALIFIED |
| `raw_reference_available_locally` | LOCAL_BYTES_RECOVERED; FULL_PHYSICAL_QUALIFICATION_INCOMPLETE |
| `real_sensor_factors_authorized` | NOT_INDEPENDENTLY_QUALIFIED |
| `reference_capture_clock_physically_verified` | NOT_INDEPENDENTLY_QUALIFIED |

## Reviewed immutable repository evidence

- `calibration_doc`: `docs/audits/trust_robot/M2DGR_CALIBRATION_EVIDENCE.md` — SHA256 `8d8d4c82e6992303cae3db0ee8b7fd01251674154f3f657c4f8e5b7e3878a8ae`
- `camera_doc`: `docs/audits/trust_robot/M2DGR_PHASE3C_CAMERA_IMU_SYNCHRONIZATION_EVIDENCE.md` — SHA256 `33feb99eddc07c8728335542309fdfb50d2f0f4faa6d32f551e42aaa2901f6ef`
- `lidar_doc`: `docs/audits/trust_robot/M2DGR_PHASE3D_LIDAR_IMU_SYNCHRONIZATION_EVIDENCE.md` — SHA256 `55b33e0ad675006ce3fd7ff07e7b55ad23097e2eb767a9f8dde91ee6da587c59`
- `r43`: `experiments/trust_robot_r39_r43_sensor_qualification_checkpoint_v1/r43/trust_robot_r43_source_acquisition_protocol_result_v1/r43_unfilled_source_receipts_v1.json` — SHA256 `260f799a3d1494052416ba83652c6de79165ba2b29e7b28f9cd14bfd6c5bc622`
- `r53`: `experiments/trust_robot_r51_r55f_evidence_checkpoint_v1/evidence/trust_robot_r53_timing_receipt_boundary_result_v1/r53_unfilled_physical_timing_receipts_v1.json` — SHA256 `f4e2d70c8e39d88ee3d6df62c0e7998488dc900398cdc8bd41733b7c1b9548f2`
- `r68`: `experiments/trust_robot_r64_r68_original_gt_recovery_checkpoint_v1/evidence/r68/result/r68_physical_gate_reconciliation_v1.json` — SHA256 `304840f59df0c9bc16c40822bc169ec078692de043e7494b5164fd391e631f05`
- `r74`: `experiments/trust_robot_r70_r74_scientific_admissibility_checkpoint_v1/evidence/result/r74_scientific_admissibility_v1.json` — SHA256 `22b02194a8899a263484a90e30afd3f95a3fb45d2ccdd7dec8bb8908d59fc98b`
- `r76`: `experiments/trust_robot_r76_r78_physical_intake_runtime_checkpoint_v1/evidence/r76/result/r76_source_intake_contract_v1.json` — SHA256 `c3d18535c4b622620c35aad4e839f89793d4eb3b1fbddf4828ee8103144f8be6`
- `r77`: `experiments/trust_robot_r76_r78_physical_intake_runtime_checkpoint_v1/evidence/r77/result/r77_intake_sensor_factor_boundary_v1.json` — SHA256 `3bf5764305f10d68a3d3c43f6b371d4338337cebf483d4b2599dbdcd261ae75c`
- `r78`: `experiments/trust_robot_r76_r78_physical_intake_runtime_checkpoint_v1/evidence/r78/result/r78_runtime_boundary_decision_v1.json` — SHA256 `ea36b5aab3360d12edf71f1ecae3ddfbf76d2a489caa9584073821c94fb1e24e`
- `r87_manifest`: `experiments/trust_robot_r84_r86_synthetic_inertial_rolling_checkpoint_v1/checkpoint_manifest_v1.json` — SHA256 `6df9cedbaac3fbcf875a8144ff81a13b0e3a8d9d9981848c0c1ffacb55c70168`
- `r91_manifest`: `experiments/trust_robot_r88_r90_schur_prior_checkpoint_v1/checkpoint_manifest_v1.json` — SHA256 `ba265abc2222c5eb972b7eb65a0b19210555f2dcd9b388ebce65ee5fb215a9dc`
- `sync_doc`: `docs/audits/trust_robot/M2DGR_PHASE3B_SYNCHRONIZATION_EVIDENCE.md` — SHA256 `6abb0b088b160f9ccd6f3ee2de036d47e9d404b27d2f494d62598364dd378d38`

## Decision

**Do not authorize measured fusion factors, trust/health training, GT scoring or ATE/RPE.**

Next work should obtain and independently validate authoritative physical evidence, not refit offsets from unqualified observations.
