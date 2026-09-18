from copy import deepcopy
import unittest

from trust_robot.m2dgr_lidar_imu_synchronization_evidence import (
    EXPECTED_STAGING_POLICY,
    M2DGRLiDARIMUSynchronizationEvidenceError,
    build_m2dgr_lidar_imu_synchronization_evidence,
    lidar_imu_evidence_content_sha256,
    phase3d_lidar_imu_staging_content_sha256,
    validate_m2dgr_lidar_imu_synchronization_evidence,
    validate_phase3d_lidar_imu_staging_evidence,
)


def summary(
    minimum,
    median,
    maximum,
):
    return {
        "count":
            36,

        "min":
            minimum,

        "median":
            median,

        "max":
            maximum,
    }


def make_staging():
    source_names = (
        "lidar_point_time_mechanism",
        "lidar_imu_zero_lag_pilot",
        "lidar_imu_lag_pilot",
        "lidar_imu_zero_lag_full_cohort",
    )

    lag_rows = {}

    best = {
        "gate_01":
            (
                [-46],
                [-46],
                [-50],
            ),

        "hall_01":
            (
                [-35],
                [-34],
                [-85],
            ),

        "room_01":
            (
                [-54],
                [-53],
                [-99],
            ),
    }

    for trajectory_id, (
        vector_lags,
        angle_lags,
        error_lags,
    ) in best.items():
        lag_rows[
            trajectory_id
        ] = {
            "common_support_pair_count":
                298,

            "zero_lag_vector_correlation":
                0.98,

            "best_vector_lags_ms":
                vector_lags,

            "best_minus_zero_vector_correlation":
                0.002,

            "best_angle_lags_ms":
                angle_lags,

            "minimum_error_lags_ms":
                error_lags,

            "zero_minus_best_median_error_deg":
                0.01,
        }

    payload = {
        "schema":
            "trust_robot.m2dgr_phase3d_lidar_imu_synchronization_evidence",

        "version":
            1,

        "dataset_id":
            "M2DGR",

        "source_artifacts": {
            name: {
                "relative_path":
                    f"audit/{name}.json",

                "content_sha256":
                    f"{index + 4:x}" * 64,

                "file_sha256":
                    f"{index:x}" * 64,

                "size_bytes":
                    100 + index,
            }
            for index, name
            in enumerate(
                source_names,
                start=1,
            )
        },

        "mechanism_evidence": {
            "sensor_model":
                "Velodyne VLP-32C",

            "released_pointcloud_topic":
                "/velodyne_points",

            "released_raw_velodyne_packets_present":
                False,

            "released_payload_strongly_matches_vlp32c_timing_table":
                True,

            "released_payload_strongly_consistent_with_last_packet_referenced_relative_point_time":
                True,

            "last_packet_reference_independently_verified":
                False,

            "header_plus_point_time_independently_verified_as_physical_firing_time":
                False,

            "exact_m2dgr_velodyne_driver_revision_identified":
                False,

            "exact_m2dgr_velodyne_runtime_configuration_identified":
                False,
        },

        "zero_lag_full_cohort": {
            "trajectory_count":
                36,

            "candidate_pair_count":
                10764,

            "admitted_pair_count":
                10758,

            "unsupported_pair_count":
                6,

            "unsupported_leading_pair_count":
                6,

            "unsupported_trailing_pair_count":
                0,

            "unsupported_internal_pair_count":
                0,

            "unsupported_trajectories": {
                "door_02":
                    [0],

                "hall_01":
                    [0],

                "hall_03":
                    [0],

                "lift_02":
                    [0],

                "room_dark_06":
                    [0],

                "street_08":
                    [0],
            },

            "failed_pair_count":
                0,

            "vector_correlation":
                summary(
                    0.79,
                    0.98,
                    0.99,
                ),

            "rotation_angle_correlation":
                summary(
                    0.85,
                    0.98,
                    0.99,
                ),

            "median_rotation_error_deg":
                summary(
                    0.03,
                    0.08,
                    0.25,
                ),

            "p95_rotation_error_deg":
                summary(
                    0.12,
                    0.21,
                    0.46,
                ),

            "z_component_correlation":
                summary(
                    0.95,
                    0.99,
                    0.999,
                ),

            "raw_icp_vector_correlation":
                summary(
                    -0.999,
                    -0.98,
                    -0.79,
                ),

            "all_primary_vector_correlations_positive":
                True,

            "all_raw_icp_vector_correlations_negative":
                True,

            "quality_threshold_for_pair_admission":
                None,

            "metric_based_pair_exclusion":
                False,

            "imu_extrapolation_used":
                False,

            "point_time_used":
                False,

            "deskewing_used":
                False,
        },

        "lag_characterization": {
            "trajectory_ids":
                [
                    "gate_01",
                    "hall_01",
                    "room_01",
                ],

            "lag_grid_ms": {
                "min":
                    -101,

                "max":
                    101,

                "step":
                    1,
            },

            "grid_expanded_after_results":
                False,

            "same_pair_support_every_lag":
                True,

            "frontend_changed":
                False,

            "deskewing_used":
                False,

            "per_trajectory":
                lag_rows,

            "exact_common_primary_best_lag_exists":
                False,

            "common_nonzero_fixed_offset_supported":
                False,

            "objectives_identify_unique_common_offset":
                False,

            "scan_expansion_scientifically_justified":
                False,

            "whole_scan_registration_confounds_clock_offset_interpretation":
                True,
        },

        "interpretation": {
            "zero_header_lag_rotational_content_consistency_generalizes_across_full_cohort":
                True,

            "primary_lidar_body_rotation_convention_supported_over_raw_icp_convention":
                True,

            "full_cohort_results_create_timing_validity_threshold":
                False,

            "lower_correlation_trajectories_are_automatically_invalid":
                False,

            "lag_pilot_identifies_unique_sensor_clock_offset":
                False,

            "common_nonzero_lidar_imu_fixed_offset_supported":
                False,

            "released_data_independently_verify_lidar_point_physical_capture_time":
                False,

            "released_data_independently_verify_lidar_to_imu_physical_capture_synchronization":
                False,
        },

        "remaining_blockers": [
            "released_bags_do_not_retain_raw_velodyne_packets",
            "exact_m2dgr_velodyne_driver_revision_not_identified",
            "exact_m2dgr_velodyne_runtime_configuration_not_identified",
            "pointcloud_header_physical_reference_event_not_independently_verified",
            "header_plus_point_time_not_independently_verified_as_physical_firing_time",
            "whole_scan_registration_effective_time_confounds_lag_interpretation",
            "handsfree_to_lidar_calibration_not_independently_verified",
            "unique_lidar_to_imu_fixed_offset_not_identified",
            "no_validation_calibration_split_for_data_selected_sync_tolerance",
        ],

        "policy":
            dict(
                EXPECTED_STAGING_POLICY
            ),
    }

    payload[
        "content_sha256"
    ] = phase3d_lidar_imu_staging_content_sha256(
        payload
    )

    return payload


class M2DGRLiDARIMUSynchronizationEvidenceTests(
    unittest.TestCase
):
    def test_valid_staging_evidence_is_accepted(self):
        validate_phase3d_lidar_imu_staging_evidence(
            make_staging()
        )

    def test_staging_digest_tamper_is_rejected(self):
        payload = make_staging()

        payload[
            "lag_characterization"
        ][
            "lag_grid_ms"
        ][
            "step"
        ] = 2

        with self.assertRaises(
            M2DGRLiDARIMUSynchronizationEvidenceError
        ):
            validate_phase3d_lidar_imu_staging_evidence(
                payload
            )

    def test_fixed_offset_policy_is_rejected(self):
        payload = make_staging()

        payload[
            "policy"
        ][
            "fixed_offset_estimated"
        ] = True

        payload[
            "content_sha256"
        ] = phase3d_lidar_imu_staging_content_sha256(
            payload
        )

        with self.assertRaises(
            M2DGRLiDARIMUSynchronizationEvidenceError
        ):
            validate_phase3d_lidar_imu_staging_evidence(
                payload
            )

    def test_permanent_evidence_binds_phase3c_manifest(self):
        evidence = (
            build_m2dgr_lidar_imu_synchronization_evidence(
                {
                    "dataset_id":
                        "M2DGR",

                    "manifest_content_sha256":
                        "a" * 64,
                },
                make_staging(),
                staging_relative_path=
                    "audit/phase3d_staging/evidence.json",
                staging_file_sha256=
                    "b" * 64,
                staging_size_bytes=
                    123,
            )
        )

        validate_m2dgr_lidar_imu_synchronization_evidence(
            evidence
        )

        self.assertEqual(
            evidence[
                "manifest_semantics"
            ][
                "phase3c_source_manifest_content_sha256"
            ],
            "a" * 64,
        )

    def test_permanent_digest_tamper_is_rejected(self):
        evidence = (
            build_m2dgr_lidar_imu_synchronization_evidence(
                {
                    "dataset_id":
                        "M2DGR",

                    "manifest_content_sha256":
                        "a" * 64,
                },
                make_staging(),
                staging_relative_path=
                    "audit/staging.json",
                staging_file_sha256=
                    "b" * 64,
                staging_size_bytes=
                    123,
            )
        )

        evidence[
            "policy"
        ][
            "synchronization_verified"
        ] = True

        evidence[
            "content_sha256"
        ] = lidar_imu_evidence_content_sha256(
            evidence
        )

        with self.assertRaises(
            M2DGRLiDARIMUSynchronizationEvidenceError
        ):
            validate_m2dgr_lidar_imu_synchronization_evidence(
                evidence
            )


def make_source_manifest():
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
        dataset_id=
            "M2DGR",

        trajectory_id=
            "gate_01",

        base_trajectory_id=
            "gate_01",

        split=
            SplitRole.TRAIN,

        streams=
            streams,

        references=
            (),
    )

    synchronization = tuple(
        SynchronizationSpec(
            stream_id=
                item.stream_id,

            clock_domain=
                item.clock_domain,

            verification_status=
                VerificationStatus.UNVERIFIED,

            method=
                "synthetic Phase-3C synchronization evidence",

            measurement_time_basis=
                MeasurementTimeBasis.SENSOR_HEADER_STAMP,

            tolerance_seconds=
                None,

            fixed_offset_seconds=
                None,

            fixed_offset_method=
                None,

            tolerance_evidence=
                None,

            tolerance_selected_on_split=
                None,
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


class M2DGRPhase3DLiDARIMUSuccessorTests(
    unittest.TestCase
):
    def test_successor_changes_only_velodyne_method(self):
        from trust_robot.m2dgr_manifest_builder import (
            build_phase3d_lidar_imu_successor_payload,
        )

        source = make_source_manifest()

        source_copy = deepcopy(
            source
        )

        evidence = (
            build_m2dgr_lidar_imu_synchronization_evidence(
                source,
                make_staging(),
                staging_relative_path=
                    "audit/phase3d_staging/evidence.json",
                staging_file_sha256=
                    "b" * 64,
                staging_size_bytes=
                    123,
            )
        )

        successor = (
            build_phase3d_lidar_imu_successor_payload(
                source,
                evidence,
            )
        )

        self.assertEqual(
            source,
            source_copy,
        )

        old_record = source[
            "records"
        ][
            0
        ]

        new_record = successor[
            "records"
        ][
            0
        ]

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

        for stream_id in old_by_id:
            old_sync = old_by_id[
                stream_id
            ]

            new_sync = new_by_id[
                stream_id
            ]

            if stream_id == "/velodyne_points":
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
                    "Phase-3D LiDAR/IMU synchronization evidence",
                    new_sync[
                        "method"
                    ],
                )

            else:
                self.assertEqual(
                    old_sync,
                    new_sync,
                )

    def test_successor_rejects_wrong_phase3c_binding(self):
        from trust_robot.m2dgr_manifest_builder import (
            build_phase3d_lidar_imu_successor_payload,
        )

        source = make_source_manifest()

        evidence = (
            build_m2dgr_lidar_imu_synchronization_evidence(
                {
                    "dataset_id":
                        "M2DGR",

                    "manifest_content_sha256":
                        "f" * 64,
                },
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
            build_phase3d_lidar_imu_successor_payload(
                source,
                evidence,
            )


if __name__ == "__main__":
    unittest.main()
