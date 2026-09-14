from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from trust_robot.data_contracts import (
    ContractError,
    DerivativeKind,
    MeasurementTimeBasis,
    ReferenceCoverage,
    ReferenceSpec,
    SplitRole,
    StreamSpec,
    SynchronizationSpec,
    TrajectoryRecord,
    VerificationStatus,
)
from trust_robot.trajectory_manifest import (
    SCHEMA,
    build_trajectory_manifest,
    load_manifest,
    validate_manifest_payload,
    write_immutable_manifest,
)


def make_record(
    trajectory_id="synthetic_001",
    base_trajectory_id="synthetic_001",
    split=SplitRole.TRAIN,
    derivative_kind=DerivativeKind.CLEAN,
    corruption_seed=None,
):
    camera = StreamSpec(
        stream_id="camera",
        modality="camera",
        frame_id="camera_frame",
        clock_domain="camera_clock",
        timestamp_unit="ns",
        estimator_input=True,
    )

    mocap = StreamSpec(
        stream_id="mocap_pose",
        modality="motion_capture",
        frame_id="mocap_world",
        clock_domain="mocap_clock",
        timestamp_unit="ns",
        reference_only=True,
    )

    reference = ReferenceSpec(
        source_id="mocap_reference",
        frame_id="mocap_world",
        coverage=ReferenceCoverage.FULL,
        supports_translation=True,
        supports_rotation=True,
        derived_from_stream_ids=(
            "mocap_pose",
        ),
    )

    return TrajectoryRecord(
        dataset_id="SYNTHETIC_TRUST_ROBOT",
        trajectory_id=trajectory_id,
        base_trajectory_id=base_trajectory_id,
        split=split,
        streams=(
            camera,
            mocap,
        ),
        references=(
            reference,
        ),
        derivative_kind=derivative_kind,
        corruption_seed=corruption_seed,
    )


def make_sync():
    return (
        SynchronizationSpec(
            stream_id="camera",
            clock_domain="camera_clock",
            verification_status=(
                VerificationStatus.CONDITIONAL
            ),
            method=(
                "synthetic manifest contract test"
            ),
            measurement_time_basis=(
                MeasurementTimeBasis.SENSOR_HEADER_STAMP
            ),
        ),
        SynchronizationSpec(
            stream_id="mocap_pose",
            clock_domain="mocap_clock",
            verification_status=(
                VerificationStatus.CONDITIONAL
            ),
            method=(
                "synthetic reference clock contract test"
            ),
            measurement_time_basis=(
                MeasurementTimeBasis.DATASET_NATIVE
            ),
        ),
    )


class TrajectoryManifestTests(
    unittest.TestCase
):
    def test_build_is_deterministic_and_valid(self):
        record = make_record()

        sync = {
            record.trajectory_id:
                make_sync()
        }

        first = build_trajectory_manifest(
            (record,),
            sync,
        )

        second = build_trajectory_manifest(
            (record,),
            sync,
        )

        self.assertEqual(
            first,
            second,
        )

        decoded = validate_manifest_payload(
            first
        )

        self.assertEqual(
            decoded,
            (record,),
        )

    def test_manifest_contains_required_contract_fields(self):
        record = make_record()

        payload = build_trajectory_manifest(
            (record,),
            {
                record.trajectory_id:
                    make_sync()
            },
        )

        self.assertEqual(
            payload["schema"],
            SCHEMA,
        )

        row = payload[
            "records"
        ][0]

        for key in (
            "dataset_id",
            "trajectory_id",
            "base_trajectory_id",
            "split",
            "derivative_kind",
            "corruption_seed",
            "streams",
            "references",
            "synchronization",
        ):
            self.assertIn(
                key,
                row,
            )

        self.assertIsNone(
            row[
                "synchronization"
            ][0][
                "tolerance_seconds"
            ]
        )

    def test_missing_sync_is_rejected(self):
        record = make_record()

        with self.assertRaises(
            ContractError
        ):
            build_trajectory_manifest(
                (record,),
                {
                    record.trajectory_id:
                        make_sync()[:1]
                },
            )

    def test_extra_sync_is_rejected(self):
        record = make_record()

        extra = SynchronizationSpec(
            stream_id="ghost_stream",
            clock_domain="ghost_clock",
            verification_status=(
                VerificationStatus.UNVERIFIED
            ),
        )

        with self.assertRaises(
            ContractError
        ):
            build_trajectory_manifest(
                (record,),
                {
                    record.trajectory_id:
                        (
                            *make_sync(),
                            extra,
                        )
                },
            )

    def test_duplicate_sync_is_rejected(self):
        record = make_record()

        camera_sync = make_sync()[0]

        with self.assertRaises(
            ContractError
        ):
            build_trajectory_manifest(
                (record,),
                {
                    record.trajectory_id:
                        (
                            *make_sync(),
                            camera_sync,
                        )
                },
            )

    def test_clock_domain_mismatch_is_rejected(self):
        record = make_record()

        bad_camera_sync = (
            SynchronizationSpec(
                stream_id="camera",
                clock_domain="wrong_clock",
                verification_status=(
                    VerificationStatus.CONDITIONAL
                ),
                measurement_time_basis=(
                    MeasurementTimeBasis.SENSOR_HEADER_STAMP
                ),
            )
        )

        with self.assertRaises(
            ContractError
        ):
            build_trajectory_manifest(
                (record,),
                {
                    record.trajectory_id:
                        (
                            bad_camera_sync,
                            make_sync()[1],
                        )
                },
            )

    def test_cross_split_derivative_is_rejected(self):
        clean = make_record(
            trajectory_id="base_clean",
            base_trajectory_id="base",
            split=SplitRole.TRAIN,
        )

        corrupt = make_record(
            trajectory_id="base_corrupt",
            base_trajectory_id="base",
            split=SplitRole.CONFIRMATION_TEST,
            derivative_kind=(
                DerivativeKind.CORRUPTED
            ),
            corruption_seed=17,
        )

        with self.assertRaises(
            ContractError
        ):
            build_trajectory_manifest(
                (
                    clean,
                    corrupt,
                ),
                {
                    clean.trajectory_id:
                        make_sync(),
                    corrupt.trajectory_id:
                        make_sync(),
                },
            )

    def test_tampered_payload_is_rejected(self):
        record = make_record()

        payload = build_trajectory_manifest(
            (record,),
            {
                record.trajectory_id:
                    make_sync()
            },
        )

        tampered = deepcopy(
            payload
        )

        tampered[
            "records"
        ][0][
            "split"
        ] = "confirmation_test"

        with self.assertRaises(
            ContractError
        ):
            validate_manifest_payload(
                tampered
            )

    def test_immutable_writer_allows_identical_rewrite(self):
        record = make_record()

        sync = {
            record.trajectory_id:
                make_sync()
        }

        with TemporaryDirectory() as tmp:
            path = (
                Path(tmp)
                / "manifest.json"
            )

            first = write_immutable_manifest(
                path,
                (record,),
                sync,
            )

            original = first.read_bytes()

            second = write_immutable_manifest(
                path,
                (record,),
                sync,
            )

            self.assertEqual(
                second.read_bytes(),
                original,
            )

            load_manifest(
                path
            )

    def test_immutable_writer_rejects_changed_content(self):
        first_record = make_record(
            trajectory_id="synthetic_001",
            base_trajectory_id="synthetic_001",
        )

        second_record = make_record(
            trajectory_id="synthetic_002",
            base_trajectory_id="synthetic_002",
        )

        with TemporaryDirectory() as tmp:
            path = (
                Path(tmp)
                / "manifest.json"
            )

            write_immutable_manifest(
                path,
                (first_record,),
                {
                    first_record.trajectory_id:
                        make_sync()
                },
            )

            with self.assertRaises(
                FileExistsError
            ):
                write_immutable_manifest(
                    path,
                    (second_record,),
                    {
                        second_record.trajectory_id:
                            make_sync()
                    },
                )

    def test_synthetic_fixture_validates_and_is_not_m2dgr(self):
        fixture = (
            Path(__file__).resolve()
            .parents[1]
            / "fixtures"
            / "trust_robot"
            / "synthetic_trajectory_manifest_v1.json"
        )

        payload = load_manifest(
            fixture
        )

        self.assertEqual(
            payload[
                "dataset_id"
            ],
            "SYNTHETIC_TRUST_ROBOT",
        )

        raw = fixture.read_text(
            encoding="utf-8"
        )

        self.assertNotIn(
            '"M2DGR"',
            raw,
        )


if __name__ == "__main__":
    unittest.main()
