import unittest

from trust_robot.data_contracts import (
    ContractError,
    DatasetReadiness,
    DerivativeKind,
    FrameSpec,
    MeasurementTimeBasis,
    ReferenceCoverage,
    ReferenceSpec,
    SplitRole,
    StreamSpec,
    SynchronizationSpec,
    TrajectoryRecord,
    VerificationStatus,
    validate_trajectory_records,
)


def camera_stream() -> StreamSpec:
    return StreamSpec(
        stream_id="camera_left",
        modality="camera",
        frame_id="camera_left_frame",
        clock_domain="camera_clock",
        timestamp_unit="ns",
        estimator_input=True,
    )


def independent_reference_stream() -> StreamSpec:
    return StreamSpec(
        stream_id="mocap_pose",
        modality="motion_capture",
        frame_id="mocap_world",
        clock_domain="mocap_clock",
        timestamp_unit="ns",
        reference_only=True,
    )


def pose_reference() -> ReferenceSpec:
    return ReferenceSpec(
        source_id="mocap_reference",
        frame_id="mocap_world",
        coverage=ReferenceCoverage.FULL,
        supports_translation=True,
        supports_rotation=True,
        derived_from_stream_ids=("mocap_pose",),
    )


class StreamContractTests(unittest.TestCase):
    def test_one_stream_cannot_be_reference_and_estimator_input(self):
        with self.assertRaises(ContractError):
            StreamSpec(
                stream_id="same_imu",
                modality="imu",
                frame_id="imu",
                clock_domain="imu_clock",
                timestamp_unit="ns",
                estimator_input=True,
                reference_only=True,
            )

    def test_independent_reference_stream_is_valid(self):
        record = TrajectoryRecord(
            dataset_id="synthetic",
            trajectory_id="traj_001",
            base_trajectory_id="traj_001",
            split=SplitRole.TRAIN,
            streams=(camera_stream(), independent_reference_stream()),
            references=(pose_reference(),),
        )
        self.assertEqual(record.split, SplitRole.TRAIN)


class ReferenceLeakageTests(unittest.TestCase):
    def test_reference_derived_from_evaluated_input_is_rejected(self):
        bad_reference = ReferenceSpec(
            source_id="derived_truth",
            frame_id="world",
            coverage=ReferenceCoverage.FULL,
            supports_translation=True,
            supports_rotation=True,
            derived_from_stream_ids=("camera_left",),
        )

        with self.assertRaises(ContractError):
            TrajectoryRecord(
                dataset_id="synthetic",
                trajectory_id="traj_001",
                base_trajectory_id="traj_001",
                split=SplitRole.TRAIN,
                streams=(camera_stream(),),
                references=(bad_reference,),
            )

    def test_position_only_reference_is_explicit(self):
        reference = ReferenceSpec(
            source_id="leica_position",
            frame_id="leica_world",
            coverage=ReferenceCoverage.FULL,
            supports_translation=True,
            supports_rotation=False,
        )
        self.assertTrue(reference.supports_translation)
        self.assertFalse(reference.supports_rotation)


class ReferenceValidityTests(unittest.TestCase):
    def test_full_pose_defaults_dimension_coverage(self):
        reference = ReferenceSpec(
            source_id="rtk_ins_pose",
            frame_id="world",
            coverage=ReferenceCoverage.FULL,
            supports_translation=True,
            supports_rotation=True,
        )

        self.assertEqual(
            reference.translation_coverage,
            ReferenceCoverage.FULL,
        )
        self.assertEqual(
            reference.rotation_coverage,
            ReferenceCoverage.FULL,
        )

    def test_partial_rotation_requires_validity_artifact(self):
        with self.assertRaises(ContractError):
            ReferenceSpec(
                source_id="mocap_pose",
                frame_id="mocap_world",
                coverage=ReferenceCoverage.PARTIAL,
                supports_translation=True,
                supports_rotation=True,
                translation_coverage=ReferenceCoverage.FULL,
                rotation_coverage=ReferenceCoverage.PARTIAL,
            )

    def test_partial_rotation_with_validity_artifact_passes(self):
        reference = ReferenceSpec(
            source_id="mocap_pose",
            frame_id="mocap_world",
            coverage=ReferenceCoverage.PARTIAL,
            supports_translation=True,
            supports_rotation=True,
            translation_coverage=ReferenceCoverage.FULL,
            rotation_coverage=ReferenceCoverage.PARTIAL,
            rotation_validity_artifact=(
                "derived/reference_validity/"
                "room_01_rotation.csv"
            ),
        )

        self.assertEqual(
            reference.translation_coverage,
            ReferenceCoverage.FULL,
        )
        self.assertEqual(
            reference.rotation_coverage,
            ReferenceCoverage.PARTIAL,
        )
        self.assertEqual(
            reference.rotation_validity_artifact,
            "derived/reference_validity/"
            "room_01_rotation.csv",
        )

    def test_unsupported_rotation_rejects_rotation_metadata(self):
        with self.assertRaises(ContractError):
            ReferenceSpec(
                source_id="leica_position",
                frame_id="leica_world",
                coverage=ReferenceCoverage.FULL,
                supports_translation=True,
                supports_rotation=False,
                rotation_coverage=ReferenceCoverage.FULL,
            )


class LineageTests(unittest.TestCase):
    def test_clean_and_corrupted_derivatives_must_share_split(self):
        clean = TrajectoryRecord(
            dataset_id="synthetic",
            trajectory_id="base_clean",
            base_trajectory_id="base",
            split=SplitRole.TRAIN,
            streams=(camera_stream(),),
            references=(),
        )
        corrupted = TrajectoryRecord(
            dataset_id="synthetic",
            trajectory_id="base_corrupt",
            base_trajectory_id="base",
            split=SplitRole.CONFIRMATION_TEST,
            streams=(camera_stream(),),
            references=(),
            derivative_kind=DerivativeKind.CORRUPTED,
            corruption_seed=10,
        )

        with self.assertRaises(ContractError):
            validate_trajectory_records((clean, corrupted))

    def test_clean_and_corrupted_derivatives_same_split_pass(self):
        clean = TrajectoryRecord(
            dataset_id="synthetic",
            trajectory_id="base_clean",
            base_trajectory_id="base",
            split=SplitRole.TRAIN,
            streams=(camera_stream(),),
            references=(),
        )
        corrupted = TrajectoryRecord(
            dataset_id="synthetic",
            trajectory_id="base_corrupt",
            base_trajectory_id="base",
            split=SplitRole.TRAIN,
            streams=(camera_stream(),),
            references=(),
            derivative_kind=DerivativeKind.CORRUPTED,
            corruption_seed=10,
        )
        out = validate_trajectory_records((clean, corrupted))
        self.assertEqual(len(out), 2)

    def test_corrupted_derivative_requires_seed(self):
        with self.assertRaises(ContractError):
            TrajectoryRecord(
                dataset_id="synthetic",
                trajectory_id="corrupt",
                base_trajectory_id="base",
                split=SplitRole.TRAIN,
                streams=(camera_stream(),),
                references=(),
                derivative_kind=DerivativeKind.CORRUPTED,
            )

    def test_corruption_seed_cannot_cross_partitions(self):
        train = TrajectoryRecord(
            dataset_id="synthetic",
            trajectory_id="train_corrupt",
            base_trajectory_id="train_base",
            split=SplitRole.TRAIN,
            streams=(camera_stream(),),
            references=(),
            derivative_kind=DerivativeKind.CORRUPTED,
            corruption_seed=42,
        )
        test = TrajectoryRecord(
            dataset_id="synthetic",
            trajectory_id="test_corrupt",
            base_trajectory_id="test_base",
            split=SplitRole.CONFIRMATION_TEST,
            streams=(camera_stream(),),
            references=(),
            derivative_kind=DerivativeKind.CORRUPTED,
            corruption_seed=42,
        )

        with self.assertRaises(ContractError):
            validate_trajectory_records((train, test))


class FrameAndSyncTests(unittest.TestCase):
    def test_verified_child_frame_requires_transform_provenance(self):
        with self.assertRaises(ContractError):
            FrameSpec(
                frame_id="camera",
                parent_frame_id="body",
                verification_status=VerificationStatus.VERIFIED,
            )

    def test_verified_sync_requires_method(self):
        with self.assertRaises(ContractError):
            SynchronizationSpec(
                stream_id="camera_left",
                clock_domain="camera_clock",
                verification_status=VerificationStatus.VERIFIED,
            )

    def test_verified_sync_with_method_passes(self):
        sync = SynchronizationSpec(
            stream_id="camera_left",
            clock_domain="camera_clock",
            verification_status=VerificationStatus.VERIFIED,
            method="dataset-provided hardware synchronization metadata",
            measurement_time_basis=(
                MeasurementTimeBasis.SENSOR_HEADER_STAMP
            ),
        )

        self.assertEqual(
            sync.verification_status,
            VerificationStatus.VERIFIED,
        )
        self.assertEqual(
            sync.measurement_time_basis,
            MeasurementTimeBasis.SENSOR_HEADER_STAMP,
        )
        self.assertIsNone(
            sync.tolerance_seconds
        )
        self.assertIsNone(
            sync.fixed_offset_seconds
        )

    def test_verified_sync_requires_measurement_time_basis(self):
        with self.assertRaises(ContractError):
            SynchronizationSpec(
                stream_id="camera_left",
                clock_domain="camera_clock",
                verification_status=VerificationStatus.VERIFIED,
                method="dataset-provided synchronization evidence",
            )

    def test_fixed_offset_requires_explicit_evidence(self):
        with self.assertRaises(ContractError):
            SynchronizationSpec(
                stream_id="camera_left",
                clock_domain="camera_clock",
                verification_status=VerificationStatus.CONDITIONAL,
                measurement_time_basis=(
                    MeasurementTimeBasis.SENSOR_HEADER_STAMP
                ),
                fixed_offset_seconds=0.002,
            )

    def test_fixed_offset_with_evidence_passes(self):
        sync = SynchronizationSpec(
            stream_id="camera_left",
            clock_domain="camera_clock",
            verification_status=VerificationStatus.CONDITIONAL,
            measurement_time_basis=(
                MeasurementTimeBasis.SENSOR_HEADER_STAMP
            ),
            fixed_offset_seconds=-0.002,
            fixed_offset_method=(
                "versioned hardware timing calibration artifact"
            ),
        )

        self.assertEqual(
            sync.fixed_offset_seconds,
            -0.002,
        )

    def test_tolerance_requires_explicit_evidence(self):
        with self.assertRaises(ContractError):
            SynchronizationSpec(
                stream_id="camera_left",
                clock_domain="camera_clock",
                verification_status=VerificationStatus.CONDITIONAL,
                measurement_time_basis=(
                    MeasurementTimeBasis.SENSOR_HEADER_STAMP
                ),
                tolerance_seconds=0.005,
            )

    def test_confirmation_data_cannot_select_tolerance(self):
        with self.assertRaises(ContractError):
            SynchronizationSpec(
                stream_id="camera_left",
                clock_domain="camera_clock",
                verification_status=VerificationStatus.CONDITIONAL,
                measurement_time_basis=(
                    MeasurementTimeBasis.SENSOR_HEADER_STAMP
                ),
                tolerance_seconds=0.005,
                tolerance_evidence=(
                    "data-selected association tolerance"
                ),
                tolerance_selected_on_split=(
                    SplitRole.CONFIRMATION_TEST
                ),
            )

    def test_train_data_cannot_select_tolerance(self):
        with self.assertRaises(ContractError):
            SynchronizationSpec(
                stream_id="camera_left",
                clock_domain="camera_clock",
                verification_status=VerificationStatus.CONDITIONAL,
                measurement_time_basis=(
                    MeasurementTimeBasis.SENSOR_HEADER_STAMP
                ),
                tolerance_seconds=0.005,
                tolerance_evidence=(
                    "data-selected association tolerance"
                ),
                tolerance_selected_on_split=(
                    SplitRole.TRAIN
                ),
            )

    def test_validation_data_may_select_documented_tolerance(self):
        sync = SynchronizationSpec(
            stream_id="camera_left",
            clock_domain="camera_clock",
            verification_status=VerificationStatus.CONDITIONAL,
            measurement_time_basis=(
                MeasurementTimeBasis.SENSOR_HEADER_STAMP
            ),
            tolerance_seconds=0.005,
            tolerance_evidence=(
                "selected from validation-calibration timing evidence"
            ),
            tolerance_selected_on_split=(
                SplitRole.VALIDATION_CALIBRATION
            ),
        )

        self.assertEqual(
            sync.tolerance_selected_on_split,
            SplitRole.VALIDATION_CALIBRATION,
        )

    def test_external_tolerance_need_not_name_dataset_split(self):
        sync = SynchronizationSpec(
            stream_id="camera_left",
            clock_domain="camera_clock",
            verification_status=VerificationStatus.CONDITIONAL,
            measurement_time_basis=(
                MeasurementTimeBasis.SENSOR_HEADER_STAMP
            ),
            tolerance_seconds=0.005,
            tolerance_evidence=(
                "external versioned hardware synchronization specification"
            ),
        )

        self.assertIsNone(
            sync.tolerance_selected_on_split
        )


class ReadinessTests(unittest.TestCase):
    def test_readiness_is_false_until_all_checks_pass(self):
        readiness = DatasetReadiness(
            dataset_id="M2DGR",
            local_path_configured=True,
            file_integrity_verified=True,
        )
        self.assertFalse(readiness.ready_for_use)

    def test_readiness_true_when_all_required_checks_pass(self):
        readiness = DatasetReadiness(
            dataset_id="M2DGR",
            local_path_configured=True,
            file_integrity_verified=True,
            required_streams_verified=True,
            timestamps_verified=True,
            calibration_verified=True,
            synchronization_verified=True,
            reference_coverage_verified=True,
            reference_input_independence_verified=True,
            trajectory_identity_verified=True,
        )
        self.assertTrue(readiness.ready_for_use)


if __name__ == "__main__":
    unittest.main()
