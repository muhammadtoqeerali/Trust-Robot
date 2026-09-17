from copy import deepcopy
import unittest

from trust_robot.m2dgr_camera_imu_synchronization_evidence import (
    EXPECTED_STAGING_POLICY,
    M2DGRCameraIMUSynchronizationEvidenceError,
    build_m2dgr_camera_imu_synchronization_evidence,
    camera_imu_evidence_content_sha256,
    phase3c_staging_content_sha256,
    validate_m2dgr_camera_imu_synchronization_evidence,
    validate_phase3c_camera_imu_staging_evidence,
)


def summary(
    minimum,
    median,
    maximum,
):
    return {
        "count":
            28,
        "min":
            minimum,
        "p25":
            (
                minimum
                + median
            ) / 2.0,
        "median":
            median,
        "p75":
            (
                median
                + maximum
            ) / 2.0,
        "max":
            maximum,
    }


def make_staging():
    source_names = (
        "accel_affine_fingerprint_pilot",
        "camera_connection_inventory",
        "united_imu_fingerprint_pilot",
        "visual_gyro_lag_pilot",
        "visual_gyro_zero_lag_clean_cohort",
        "visual_gyro_zero_lag_pilot",
    )

    payload = {
        "schema":
            "trust_robot.m2dgr_phase3c_camera_imu_synchronization_evidence",

        "version":
            1,

        "dataset_id":
            "M2DGR",

        "source_artifacts": {
            name: {
                "relative_path":
                    f"audit/{name}.json",
                "file_sha256":
                    f"{index:x}" * 64,
                "content_sha256":
                    f"{index + 6:x}" * 64,
            }
            for index, name
            in enumerate(
                source_names,
                start=1,
            )
        },

        "released_topic_evidence": {
            "trajectory_count": 36,
            "camera_metadata_topics_present": False,
            "raw_camera_gyro_topics_present": False,
            "raw_camera_accel_topics_present": False,
            "camera_info_topics_present": False,
            "united_camera_imu_topic_present": True,
            "compressed_d435i_color_topic_present": True,
            "exact_driver_configuration_recoverable_from_bag_topics": False,
        },

        "united_imu_characterization": {
            "pilot_trajectory_ids": [
                "gate_01",
                "hall_01",
                "room_01",
            ],

            "median_header_period_ms": {
                "gate_01": 4.98,
                "hall_01": 4.99,
                "room_01": 4.99,
            },

            "exact_consecutive_acceleration_repeat_count": {
                "gate_01": 0,
                "hall_01": 0,
                "room_01": 0,
            },

            "copy_style_sample_hold_supported":
                False,

            "linear_interpolation_or_other_processing_resolved":
                False,

            "affine_pilot_used_to_reject_linear_interpolation":
                False,
        },

        "zero_lag_visual_gyro_clean_cohort": {
            "trajectory_count":
                28,

            "successful_trajectory_count":
                28,

            "failed_trajectory_count":
                0,

            "selection_basis":
                "pre-existing Phase-3A structural evidence only",

            "method_changed_after_pilot":
                False,

            "lag_search_performed":
                False,

            "visual_success_fraction":
                summary(
                    0.05,
                    0.50,
                    0.99,
                ),

            "usable_visual_imu_pair_count":
                summary(
                    160.0,
                    1085.0,
                    11453.0,
                ),

            "vector_correlation":
                summary(
                    0.07,
                    0.73,
                    0.94,
                ),

            "rotation_angle_correlation":
                summary(
                    0.06,
                    0.71,
                    0.97,
                ),

            "median_rotation_error_deg":
                summary(
                    0.12,
                    0.26,
                    1.64,
                ),

            "dark_room_frontend_success_counterexample": {
                trajectory_id: {
                    "visual_success_fraction":
                        0.99,

                    "usable_pair_count":
                        1000,

                    "zero_lag_vector_correlation":
                        0.1,

                    "zero_lag_rotation_angle_correlation":
                        0.1,

                    "median_rotation_error_deg":
                        1.0,
                }
                for trajectory_id in (
                    "room_dark_04",
                    "room_dark_05",
                    "room_dark_06",
                )
            },

            "interpretation":
                "synthetic",
        },

        "lag_pilot": {
            "trajectory_ids": [
                "gate_01",
                "hall_01",
                "room_01",
            ],

            "visual_method_changed_after_zero_lag_pilot":
                False,

            "common_support_across_all_lags":
                True,

            "lag_specific_sample_admission":
                False,

            "lag_step_ms":
                1,

            "best_vector_correlation_lags_ms": {
                "gate_01": [23],
                "hall_01": [-67],
                "room_01": [-3],
            },

            "best_minus_zero_vector_correlation": {
                "gate_01": 0.000588,
                "hall_01": 0.005890,
                "room_01": 0.000058,
            },

            "minimum_median_rotation_error_lags_ms": {
                "gate_01": [8],
                "hall_01": [48],
                "room_01": [-16],
            },

            "primary_best_lag_hits_scan_boundary": {
                "gate_01": False,
                "hall_01": True,
                "room_01": False,
            },

            "common_nonzero_fixed_offset_supported":
                False,

            "scan_expansion_scientifically_justified":
                False,
        },

        "remaining_blockers": [
            "rgb_image_header_physical_capture_event_not_independently_verified",
            "released_bags_do_not_retain_realsense_frame_metadata",
            "exact_realsense_driver_revision_and_runtime_configuration_not_identified",
            "camera_calibration_not_independently_verified",
            "visual_content_association_is_heterogeneous_across_trajectories",
            "unique_camera_to_imu_fixed_offset_not_identified",
            "no_validation_calibration_split_for_data_selected_sync_tolerance",
        ],

        "conclusion": {
            "camera_and_d435i_imu_show_zero_lag_physical_content_consistency_on_many_trajectories":
                True,

            "consistency_is_uniform_across_clean_cohort":
                False,

            "released_data_identify_unique_camera_to_imu_fixed_offset":
                False,

            "released_data_independently_verify_rgb_physical_capture_synchronization":
                False,

            "recommended_next_action":
                "stop camera/IMU lag tuning",
        },

        "policy":
            dict(
                EXPECTED_STAGING_POLICY
            ),
    }

    payload[
        "content_sha256"
    ] = phase3c_staging_content_sha256(
        payload
    )

    return payload


class M2DGRCameraIMUSynchronizationEvidenceTests(
    unittest.TestCase
):
    def test_valid_staging_evidence_is_accepted(self):
        validate_phase3c_camera_imu_staging_evidence(
            make_staging()
        )

    def test_staging_digest_tamper_is_rejected(self):
        payload = make_staging()

        payload[
            "lag_pilot"
        ][
            "lag_step_ms"
        ] = 2

        with self.assertRaises(
            M2DGRCameraIMUSynchronizationEvidenceError
        ):
            validate_phase3c_camera_imu_staging_evidence(
                payload
            )

    def test_fixed_offset_policy_is_rejected(self):
        payload = make_staging()

        payload[
            "policy"
        ][
            "unique_fixed_camera_imu_offset_supported"
        ] = True

        payload[
            "content_sha256"
        ] = phase3c_staging_content_sha256(
            payload
        )

        with self.assertRaises(
            M2DGRCameraIMUSynchronizationEvidenceError
        ):
            validate_phase3c_camera_imu_staging_evidence(
                payload
            )

    def test_observed_best_lag_change_is_rejected(self):
        payload = make_staging()

        payload[
            "lag_pilot"
        ][
            "best_vector_correlation_lags_ms"
        ][
            "gate_01"
        ] = [
            22
        ]

        payload[
            "content_sha256"
        ] = phase3c_staging_content_sha256(
            payload
        )

        with self.assertRaises(
            M2DGRCameraIMUSynchronizationEvidenceError
        ):
            validate_phase3c_camera_imu_staging_evidence(
                payload
            )

    def test_permanent_evidence_binds_phase3b_manifest(self):
        staging = make_staging()

        phase3b = {
            "dataset_id":
                "M2DGR",

            "manifest_content_sha256":
                "a" * 64,
        }

        evidence = (
            build_m2dgr_camera_imu_synchronization_evidence(
                phase3b,
                staging,
                staging_relative_path=(
                    "audit/phase3c_staging/"
                    "camera_imu_synchronization_evidence_v1/"
                    "phase3c_camera_imu_synchronization_evidence_v1.json"
                ),
                staging_file_sha256="b" * 64,
                staging_size_bytes=123,
            )
        )

        validate_m2dgr_camera_imu_synchronization_evidence(
            evidence
        )

        self.assertEqual(
            evidence[
                "manifest_semantics"
            ][
                "phase3b_source_manifest_content_sha256"
            ],
            "a" * 64,
        )

    def test_permanent_digest_tamper_is_rejected(self):
        staging = make_staging()

        evidence = (
            build_m2dgr_camera_imu_synchronization_evidence(
                {
                    "dataset_id":
                        "M2DGR",

                    "manifest_content_sha256":
                        "a" * 64,
                },
                staging,
                staging_relative_path="audit/staging.json",
                staging_file_sha256="b" * 64,
                staging_size_bytes=123,
            )
        )

        evidence[
            "policy"
        ][
            "synchronization_verified"
        ] = True

        evidence[
            "content_sha256"
        ] = camera_imu_evidence_content_sha256(
            evidence
        )

        with self.assertRaises(
            M2DGRCameraIMUSynchronizationEvidenceError
        ):
            validate_m2dgr_camera_imu_synchronization_evidence(
                evidence
            )


def make_phase3b_manifest():
    from trust_robot.data_contracts import (
        MeasurementTimeBasis,
        SplitRole,
        StreamSpec,
        SynchronizationSpec,
        TrajectoryRecord,
        VerificationStatus,
    )
    from trust_robot.m2dgr_manifest_builder import (
        build_streams,
    )
    from trust_robot.m2dgr_synchronization_evidence import (
        CONSERVATIVE_CLOCK_DOMAINS,
    )
    from trust_robot.trajectory_manifest import (
        build_trajectory_manifest,
    )

    nominal = build_streams()

    streams = tuple(
        StreamSpec(
            stream_id=
                item.stream_id,
            modality=
                item.modality,
            frame_id=
                item.frame_id,
            clock_domain=
                CONSERVATIVE_CLOCK_DOMAINS[
                    item.stream_id
                ],
            timestamp_unit=
                item.timestamp_unit,
            estimator_input=
                item.estimator_input,
            reference_only=
                item.reference_only,
        )
        for item in nominal
    )

    record = TrajectoryRecord(
        dataset_id="M2DGR",
        trajectory_id="gate_01",
        base_trajectory_id="gate_01",
        split=SplitRole.TRAIN,
        streams=streams,
        references=(),
    )

    synchronization = tuple(
        SynchronizationSpec(
            stream_id=
                item.stream_id,
            clock_domain=
                item.clock_domain,
            verification_status=
                VerificationStatus.UNVERIFIED,
            method=(
                "Phase-3B synthetic "
                "synchronization evidence"
            ),
            measurement_time_basis=(
                MeasurementTimeBasis.SENSOR_HEADER_STAMP
            ),
            tolerance_seconds=None,
            fixed_offset_seconds=None,
            fixed_offset_method=None,
            tolerance_evidence=None,
            tolerance_selected_on_split=None,
        )
        for item in streams
    )

    return build_trajectory_manifest(
        (
            record,
        ),
        {
            "gate_01":
                synchronization,
        },
    )


class M2DGRPhase3CCameraIMUSuccessorTests(
    unittest.TestCase
):
    def test_successor_changes_only_camera_imu_methods(self):
        from trust_robot.m2dgr_camera_imu_synchronization_evidence import (
            build_m2dgr_camera_imu_synchronization_evidence,
        )
        from trust_robot.m2dgr_manifest_builder import (
            build_phase3c_camera_imu_successor_payload,
        )

        source_manifest = (
            make_phase3b_manifest()
        )

        source_copy = deepcopy(
            source_manifest
        )

        permanent_evidence = (
            build_m2dgr_camera_imu_synchronization_evidence(
                source_manifest,
                make_staging(),
                staging_relative_path=(
                    "audit/phase3c_staging/"
                    "camera_imu_synchronization_evidence_v1/"
                    "phase3c_camera_imu_synchronization_evidence_v1.json"
                ),
                staging_file_sha256=
                    "b" * 64,
                staging_size_bytes=
                    123,
            )
        )

        successor = (
            build_phase3c_camera_imu_successor_payload(
                source_manifest,
                permanent_evidence,
            )
        )

        self.assertEqual(
            source_manifest,
            source_copy,
        )

        old_record = source_manifest[
            "records"
        ][0]

        new_record = successor[
            "records"
        ][0]

        self.assertEqual(
            old_record[
                "streams"
            ],
            new_record[
                "streams"
            ],
        )

        old_by_id = {
            item[
                "stream_id"
            ]:
                item
            for item in old_record[
                "synchronization"
            ]
        }

        new_by_id = {
            item[
                "stream_id"
            ]:
                item
            for item in new_record[
                "synchronization"
            ]
        }

        camera_ids = {
            "/camera/color/image_raw/compressed",
            "/camera/imu",
        }

        for stream_id in old_by_id:
            old_sync = old_by_id[
                stream_id
            ]

            new_sync = new_by_id[
                stream_id
            ]

            if stream_id in camera_ids:
                for key in old_sync:
                    if key == "method":
                        continue

                    self.assertEqual(
                        old_sync[
                            key
                        ],
                        new_sync[
                            key
                        ],
                    )

                self.assertNotEqual(
                    old_sync[
                        "method"
                    ],
                    new_sync[
                        "method"
                    ],
                )

                self.assertIn(
                    "Phase-3C camera/IMU synchronization evidence",
                    new_sync[
                        "method"
                    ],
                )

            else:
                self.assertEqual(
                    old_sync,
                    new_sync,
                )

        self.assertNotEqual(
            source_manifest[
                "manifest_content_sha256"
            ],
            successor[
                "manifest_content_sha256"
            ],
        )

    def test_successor_rejects_wrong_phase3b_binding(self):
        from trust_robot.m2dgr_camera_imu_synchronization_evidence import (
            build_m2dgr_camera_imu_synchronization_evidence,
        )
        from trust_robot.m2dgr_manifest_builder import (
            build_phase3c_camera_imu_successor_payload,
        )

        source_manifest = (
            make_phase3b_manifest()
        )

        wrong_source = {
            "dataset_id":
                "M2DGR",

            "manifest_content_sha256":
                "f" * 64,
        }

        permanent_evidence = (
            build_m2dgr_camera_imu_synchronization_evidence(
                wrong_source,
                make_staging(),
                staging_relative_path=
                    "audit/staging.json",
                staging_file_sha256=
                    "b" * 64,
                staging_size_bytes=
                    123,
            )
        )

        with self.assertRaises(
            ValueError
        ):
            build_phase3c_camera_imu_successor_payload(
                source_manifest,
                permanent_evidence,
            )



if __name__ == "__main__":
    unittest.main()
