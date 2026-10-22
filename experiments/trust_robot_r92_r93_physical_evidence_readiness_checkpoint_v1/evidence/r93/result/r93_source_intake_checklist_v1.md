# R93 physical-source intake checklist — no evidence received

This checklist is administrative readiness, not physical verification.
All entries currently require new evidence and independent review.

## Physical timing receipts

- [ ] **camera_color**: capture_event_definition, clock_mapping_method_and_parameters, clock_offset_and_drift_uncertainty, device_model_and_serial_or_export_identifier, header_stamp_timebase_and_epoch, independent_validation_source_sha256, original_publisher_and_version, room_02_applicability_evidence_sha256, source_document_uri, source_sha256
- [ ] **camera_imu**: capture_event_definition, clock_mapping_method_and_parameters, clock_offset_and_drift_uncertainty, device_model_and_serial_or_export_identifier, header_stamp_timebase_and_epoch, independent_validation_source_sha256, original_publisher_and_version, room_02_applicability_evidence_sha256, source_document_uri, source_sha256
- [ ] **handsfree_imu**: capture_event_definition, clock_mapping_method_and_parameters, clock_offset_and_drift_uncertainty, device_model_and_serial_or_export_identifier, header_stamp_timebase_and_epoch, independent_validation_source_sha256, original_publisher_and_version, room_02_applicability_evidence_sha256, source_document_uri, source_sha256
- [ ] **mocap_reference**: capture_event_definition, clock_mapping_method_and_parameters, clock_offset_and_drift_uncertainty, device_model_and_serial_or_export_identifier, header_stamp_timebase_and_epoch, independent_validation_source_sha256, invalid_rotation_resolution_evidence_sha256, mocap_export_file_sha256, mocap_to_lidar_transform_and_direction, mocap_tracked_body_origin_definition, original_publisher_and_version, reference_timestamp_export_semantics, room_02_applicability_evidence_sha256, source_document_uri, source_sha256
- [ ] **velodyne_lidar**: capture_event_definition, clock_mapping_method_and_parameters, clock_offset_and_drift_uncertainty, device_model_and_serial_or_export_identifier, header_stamp_timebase_and_epoch, independent_validation_source_sha256, original_publisher_and_version, room_02_applicability_evidence_sha256, source_document_uri, source_sha256

## Eleven scientific gate receipts

- [ ] **camera_imu_extrinsics_physically_verified**: T_target_source_SE3, independent_validation, rotation_direction, source_frame, target_frame, translation_units_m
- [ ] **camera_intrinsics_physically_verified**: K_3x3, camera_model, capture_resolution_receipt, distortion_model_and_coefficients, image_size_px, independent_reprojection_check
- [ ] **camera_lidar_extrinsics_physically_verified**: T_target_source_SE3, calibration_method, independent_transform_residuals, source_frame, target_frame, translation_units_m
- [ ] **cross_sensor_synchronization_physically_verified**: all_sensor_clock_domains, independent_validation, lidar_scan_effective_time, offset_and_drift_models, offset_sign_convention, physical_event_definitions
- [ ] **health_training_authorized**: TRAIN_only_fit, explicit_scientific_approval, heldout_isolation_test, label_leakage_audit, supervised_health_labels_provenance, validation_only_model_selection
- [ ] **m2dgr_ate_rpe_authorized**: heldout_sealed_scoring_plan, invalid_rotation_mask, mocap_to_estimator_transform, physical_time_association, predeclared_metric_tolerance, qualified_SE3_reference
- [ ] **metric_visual_pose_authorized**: independent_metric_scale, independent_pose_reference, nondegenerate_correspondences, qualified_camera_extrinsics, qualified_camera_intrinsics, uncertainty_check
- [ ] **mocap_body_to_lidar_physically_verified**: T_lidar_mocap_body_SE3, author_or_measurement_receipt, independent_geometry_check, target_lidar_frame, tracked_markers_and_body_frame, translation_units_m
- [ ] **raw_reference_available_locally**: 90_invalid_rotation_handling, file_format_and_timestamp_units, independent_content_check, license_and_provenance, raw_bytes_sha256, room_02_source_uri
- [ ] **real_sensor_factors_authorized**: explicit_safety_approval, independent_consistency_tests, qualified_native_sensor_models, qualified_noise_covariances, qualified_physical_clock, train_validation_predeclared_gates
- [ ] **reference_capture_clock_physically_verified**: export_timebase_mapping, independent_clock_check, offset_sign_convention, per_sequence_or_global_scope, reference_event_definition, timestamp_epoch_and_unit

## On receipt of any new source

- Record the original source and version, acquisition method, applicable TRAIN sequence, bytes and SHA-256 outside Git.
- Independently verify physical event/frame semantics, units, transformation direction, uncertainty and recording applicability.
- Preserve the original evidence without edits; keep raw sources and identifying paths outside Git.
- Distinguish source-format validity from physical qualification and independent scientific authorization.
- Never open confirmation_test or authorize real sensor factors, health training or ATE/RPE from metadata alone.

Historical R43/R53 receipts are frozen. A later independently checked decision must not rewrite them.
Original room_02 GT bytes are already recovered; reference timing, frame semantics and 90 invalid rotations remain unresolved.
