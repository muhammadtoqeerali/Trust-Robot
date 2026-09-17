from copy import deepcopy
import unittest

from trust_robot.data_contracts import (
    MeasurementTimeBasis,
    SplitRole,
    SynchronizationSpec,
    TrajectoryRecord,
    VerificationStatus,
)
from trust_robot.m2dgr_manifest_builder import (
    build_phase3b_synchronization_successor_payload,
    build_streams,
)
from trust_robot.m2dgr_synchronization_evidence import (
    CONSERVATIVE_CLOCK_DOMAINS,
    M2DGRSynchronizationEvidenceError,
    synchronization_evidence_content_sha256,
    validate_m2dgr_synchronization_evidence,
)
from trust_robot.trajectory_manifest import (
    build_trajectory_manifest,
)


def make_evidence(
    phase3_content_sha: str = "1" * 64,
):
    sources = {}

    for index, key in enumerate(
        (
            "connection_inventory",
            "gnss_clock",
            "clock_domain_fingerprint",
            "within_trajectory_clock_drift",
            "vector_gyro_clean_cohort",
            "phase3_timing_index",
            "phase3_manifest",
        ),
        start=1,
    ):
        sources[
            key
        ] = {
            "relative_path":
                f"audit/source_{index}.json",
            "file_sha256":
                f"{index:x}" * 64,
            "size_bytes":
                index,
        }

    payload = {
        "schema":
            "TRUST_ROBOT_M2DGR_SYNCHRONIZATION_EVIDENCE_V1",

        "schema_version":
            1,

        "dataset_id":
            "M2DGR",

        "source_artifacts":
            sources,

        "observations": {
            "connection_inventory": {
                "trajectory_count": 36,
                "gnss_clock_topics_present_trajectory_count": 18,
                "velodyne_packets_present_trajectory_count": 0,
                "rosout_present_trajectory_count": 0,
                "diagnostics_present_trajectory_count": 0,
                "clock_topic_present_trajectory_count": 0,
            },

            "gnss_receiver_clock": {
                "trajectory_count": 18,
                "all_fix_headers_exact_receiver_utc": True,
                "receiver_clock_reset_count": 0,
                "unresolved_pvt_utc_count": 0,
                "reverse_receiver_utc_count": 0,
                "interpretation": "synthetic",
            },

            "bag_record_clock": {
                "stable_fixed_offset_to_gnss_receiver_utc": False,
                "transport_latency_separated_from_clock_offset": False,
                "interpretation": "synthetic",
            },

            "sensor_header_epoch": {
                "host_system_epoch_behavior_observed": True,
                "native_gnss_device_utc_behavior_supported": False,
                "verified_common_physical_clock": False,
                "interpretation": "synthetic",
            },

            "imu_content_association": {
                "clean_trajectory_count": 28,
                "signal": "three_axis_angular_velocity_in_author_published_lidar_frame",
                "rotation_estimated_from_timing_data": False,
                "author_calibration_independently_verified": False,
                "best_lag_ms": {
                    "min": -11.0,
                    "median": -4.0,
                    "max": 0.0,
                },
                "window_median_lag_ms": {
                    "min": -9.0,
                    "median": -4.0,
                    "max": 0.0,
                },
                "window_lag_range_ms": {
                    "min": 5.0,
                    "median": 16.0,
                    "max": 34.0,
                },
                "zero_lag_vector_correlation": {
                    "min": 0.92,
                    "median": 0.996,
                    "max": 0.999,
                },
                "best_minus_zero_vector_correlation": {
                    "min": 0.0,
                    "median": 0.00008,
                    "max": 0.0007,
                },
                "near_zero_temporal_association_observed": True,
                "nonzero_fixed_offset_supported": False,
                "interpretation": "synthetic",
            },
        },

        "manifest_semantics": {
            "phase3_source_manifest_content_sha256":
                phase3_content_sha,
            "phase3_timing_index_content_sha256":
                "2" * 64,
            "current_shared_sensor_clock_label_is_physical_clock_proof":
                False,
            "recommended_conservative_clock_domains":
                dict(
                    CONSERVATIVE_CLOCK_DOMAINS
                ),
            "clock_domain_equality_may_be_used_as_sync_proof":
                False,
        },

        "remaining_blockers": [
            "camera_image_to_imu_physical_capture_timing_not_independently_verified",
            "lidar_to_imu_physical_capture_timing_not_independently_verified",
            "reference_to_estimator_temporal_association_not_independently_verified",
            "common_physical_clock_not_independently_verified",
            "no_validation_calibration_split_for_data_selected_sync_tolerance",
            "calibration_not_independently_verified",
        ],

        "policy": {
            "characterization_only": True,
            "raw_data_modified": False,
            "phase3_manifest_modified": False,
            "automatic_sample_exclusion_rule_created": False,
            "alignment_based_exclusion_rule_created": False,
            "fixed_offset_estimated": False,
            "fixed_offset_applied": False,
            "synchronization_tolerance_frozen": False,
            "clock_domain_verified": False,
            "physical_capture_synchronization_verified": False,
            "synchronization_verified": False,
            "evaluation_ready": False,
        },
    }

    payload[
        "content_sha256"
    ] = synchronization_evidence_content_sha256(
        payload
    )

    return payload


class M2DGRSynchronizationEvidenceTests(
    unittest.TestCase
):
    def test_valid_evidence_is_accepted(self):
        validate_m2dgr_synchronization_evidence(
            make_evidence()
        )

    def test_digest_tamper_is_rejected(self):
        payload = make_evidence()
        payload[
            "observations"
        ][
            "gnss_receiver_clock"
        ][
            "trajectory_count"
        ] = 17

        with self.assertRaises(
            M2DGRSynchronizationEvidenceError
        ):
            validate_m2dgr_synchronization_evidence(
                payload
            )

    def test_verified_sync_policy_is_rejected(self):
        payload = make_evidence()
        payload[
            "policy"
        ][
            "synchronization_verified"
        ] = True
        payload[
            "content_sha256"
        ] = synchronization_evidence_content_sha256(
            payload
        )

        with self.assertRaises(
            M2DGRSynchronizationEvidenceError
        ):
            validate_m2dgr_synchronization_evidence(
                payload
            )

    def test_shared_clock_domain_mapping_is_rejected(self):
        payload = make_evidence()
        payload[
            "manifest_semantics"
        ][
            "recommended_conservative_clock_domains"
        ][
            "/camera/imu"
        ] = (
            payload[
                "manifest_semantics"
            ][
                "recommended_conservative_clock_domains"
            ][
                "/handsfree/imu"
            ]
        )

        payload[
            "content_sha256"
        ] = synchronization_evidence_content_sha256(
            payload
        )

        with self.assertRaises(
            M2DGRSynchronizationEvidenceError
        ):
            validate_m2dgr_synchronization_evidence(
                payload
            )

    def test_phase3b_successor_changes_only_clock_semantics_and_method(self):
        streams = build_streams()

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
                stream_id=stream.stream_id,
                clock_domain=stream.clock_domain,
                verification_status=VerificationStatus.UNVERIFIED,
                measurement_time_basis=(
                    MeasurementTimeBasis.SENSOR_HEADER_STAMP
                ),
            )
            for stream in streams
        )

        phase3 = build_trajectory_manifest(
            (
                record,
            ),
            {
                "gate_01":
                    synchronization,
            },
        )

        original = deepcopy(
            phase3
        )

        evidence = make_evidence(
            phase3[
                "manifest_content_sha256"
            ]
        )

        successor = (
            build_phase3b_synchronization_successor_payload(
                phase3,
                evidence,
            )
        )

        self.assertEqual(
            phase3,
            original,
        )

        row = successor[
            "records"
        ][0]

        for stream in row[
            "streams"
        ]:
            self.assertEqual(
                stream[
                    "clock_domain"
                ],
                CONSERVATIVE_CLOCK_DOMAINS[
                    stream[
                        "stream_id"
                    ]
                ],
            )

        for sync in row[
            "synchronization"
        ]:
            self.assertEqual(
                sync[
                    "clock_domain"
                ],
                CONSERVATIVE_CLOCK_DOMAINS[
                    sync[
                        "stream_id"
                    ]
                ],
            )

            self.assertEqual(
                sync[
                    "verification_status"
                ],
                "unverified",
            )

            self.assertIsNone(
                sync[
                    "fixed_offset_seconds"
                ]
            )

            self.assertIsNone(
                sync[
                    "tolerance_seconds"
                ]
            )

            self.assertIn(
                "Phase-3B synchronization evidence",
                sync[
                    "method"
                ],
            )

    def test_phase3b_successor_rejects_wrong_source_manifest(self):
        streams = build_streams()

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
                stream_id=stream.stream_id,
                clock_domain=stream.clock_domain,
                verification_status=VerificationStatus.UNVERIFIED,
                measurement_time_basis=(
                    MeasurementTimeBasis.SENSOR_HEADER_STAMP
                ),
            )
            for stream in streams
        )

        phase3 = build_trajectory_manifest(
            (
                record,
            ),
            {
                "gate_01":
                    synchronization,
            },
        )

        with self.assertRaises(
            ValueError
        ):
            build_phase3b_synchronization_successor_payload(
                phase3,
                make_evidence(
                    "f" * 64
                ),
            )


if __name__ == "__main__":
    unittest.main()
