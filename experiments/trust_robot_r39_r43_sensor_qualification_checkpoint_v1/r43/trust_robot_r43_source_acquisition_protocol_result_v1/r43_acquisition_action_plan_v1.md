# R43 — Physical calibration and mocap source-acquisition protocol

**Status: no new physical evidence acquired; all 11 gates remain NOT QUALIFIED.**

The frozen room_02 mocap reference receipt has SHA256 `79d2c6d9132ce3cf87bb87445729302cd73709a59344a3dfacc5d7788937589d`, with 90 invalid rotation records. The locally bounded R41 search found no matching room_02 reference file. R42 inspected 15 ROS1 connection headers and found no CameraInfo, TF, or mocap reference topics.

Existing published/released D435i IMU relative-rotation content support is retained, but **does not** establish a full 6DoF extrinsic or physical timing.

## Evidence requirements and future acceptance

- **camera_intrinsics_physically_verified — NOT QUALIFIED.** Required: camera_model, image_size_px, K_3x3, distortion_model_and_coefficients, capture_resolution_receipt, independent_reprojection_check.
- **camera_lidar_extrinsics_physically_verified — NOT QUALIFIED.** Required: source_frame, target_frame, T_target_source_SE3, translation_units_m, calibration_method, independent_transform_residuals.
- **camera_imu_extrinsics_physically_verified — NOT QUALIFIED.** Required: source_frame, target_frame, T_target_source_SE3, translation_units_m, rotation_direction, independent_validation.
- **mocap_body_to_lidar_physically_verified — NOT QUALIFIED.** Required: tracked_markers_and_body_frame, target_lidar_frame, T_lidar_mocap_body_SE3, translation_units_m, author_or_measurement_receipt, independent_geometry_check.
- **reference_capture_clock_physically_verified — NOT QUALIFIED.** Required: reference_event_definition, timestamp_epoch_and_unit, export_timebase_mapping, offset_sign_convention, per_sequence_or_global_scope, independent_clock_check.
- **cross_sensor_synchronization_physically_verified — NOT QUALIFIED.** Required: all_sensor_clock_domains, physical_event_definitions, offset_and_drift_models, offset_sign_convention, lidar_scan_effective_time, independent_validation.
- **raw_reference_available_locally — NOT QUALIFIED.** Required: room_02_source_uri, license_and_provenance, raw_bytes_sha256, file_format_and_timestamp_units, 90_invalid_rotation_handling, independent_content_check.
- **metric_visual_pose_authorized — NOT QUALIFIED.** Required: qualified_camera_intrinsics, qualified_camera_extrinsics, independent_metric_scale, nondegenerate_correspondences, independent_pose_reference, uncertainty_check.
- **real_sensor_factors_authorized — NOT QUALIFIED.** Required: qualified_native_sensor_models, qualified_physical_clock, qualified_noise_covariances, independent_consistency_tests, train_validation_predeclared_gates, explicit_safety_approval.
- **health_training_authorized — NOT QUALIFIED.** Required: supervised_health_labels_provenance, TRAIN_only_fit, validation_only_model_selection, label_leakage_audit, heldout_isolation_test, explicit_scientific_approval.
- **m2dgr_ate_rpe_authorized — NOT QUALIFIED.** Required: qualified_SE3_reference, mocap_to_estimator_transform, physical_time_association, invalid_rotation_mask, predeclared_metric_tolerance, heldout_sealed_scoring_plan.

## Receipt intake and split discipline

Use `r43_unfilled_source_receipts_v1.json` as an **unfilled schema template only**. An independent future qualification phase must bind any legitimately received source to a SHA256, actual provenance and physical validation; do not change any status field in this frozen report.

Collect physical metadata from the dataset author, device manufacturer, original calibration runs, or independently measured equipment. Require native coordinate-frame definitions, transform direction, metres, sensor timebase and sign conventions, per-sequence applicability, and withheld independent checks.

Do not fit reference-to-sensor transforms, time offsets, thresholds or noise models on confirmation_test; use TRAIN for development, validation_calibration for predeclared decisions, and retain confirmation_test sealed until scientific gates permit scoring.

## Next

R44: SHA-pinned audit/archive of R39–R43 with standalone independent verifier and guarded GitHub push. No sensor factors, health labels or ATE/RPE scoring.
