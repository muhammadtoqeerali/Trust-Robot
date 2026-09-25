from hashlib import sha256
from pathlib import Path
import ast
import json
import struct
import unittest

from trust_robot.se3_multimodal_feature_extraction import (
    CAMERA_FEATURE_NAMES,
    CAMERA_STREAM,
    CANDIDATE_SCHEMA,
    FEATURE_RECORD_SCHEMA,
    IMU_FEATURE_NAMES,
    IMU_STREAMS,
    RUN_ID,
    SUPPORTED_STREAMS,
    TRAIN_TRAJECTORIES,
    FeatureRecord,
    FeatureStreamAccumulator,
    SE3FeatureExtractionError,
    build_candidate_manifest,
    canonical_json_bytes,
    content_sha256,
    feature_names_for_stream,
    feature_record_line,
    feature_record_payload,
    stream_file_name,
    validate_candidate_manifest,
)


ROOT = Path(__file__).resolve().parents[2]

RUNNER = (
    ROOT
    / "scripts/trust_robot/"
      "run_se3_multimodal_feature_extraction_v1.py"
)


class SE3MultimodalFeatureExtractionTests(
    unittest.TestCase
):
    def test_01_candidate_schema(self):
        payload = (
            build_candidate_manifest()
        )

        self.assertEqual(
            payload[
                "schema"
            ],
            CANDIDATE_SCHEMA,
        )

        self.assertEqual(
            payload[
                "run_id"
            ],
            RUN_ID,
        )

    def test_02_candidate_digest(self):
        payload = (
            build_candidate_manifest()
        )

        self.assertEqual(
            payload[
                "content_sha256"
            ],
            content_sha256(
                payload
            ),
        )

    def test_03_exact_train_population(self):
        payload = (
            build_candidate_manifest()
        )

        self.assertEqual(
            tuple(
                payload[
                    "train_trajectories"
                ]
            ),
            TRAIN_TRAJECTORIES,
        )

        self.assertEqual(
            payload[
                "train_trajectory_count"
            ],
            22,
        )

    def test_04_supported_streams_exact(self):
        self.assertEqual(
            SUPPORTED_STREAMS,
            (
                "/camera/color/image_raw/compressed",
                "/camera/imu",
                "/handsfree/imu",
            ),
        )

    def test_05_feature_names_exact(self):
        self.assertEqual(
            feature_names_for_stream(
                CAMERA_STREAM
            ),
            CAMERA_FEATURE_NAMES,
        )

        for stream in IMU_STREAMS:
            self.assertEqual(
                feature_names_for_stream(
                    stream
                ),
                IMU_FEATURE_NAMES,
            )

    def test_06_unknown_stream_rejected(self):
        with self.assertRaises(
            SE3FeatureExtractionError
        ):
            feature_names_for_stream(
                "/unknown"
            )

    def test_07_stream_file_names_are_deterministic(self):
        self.assertEqual(
            stream_file_name(
                CAMERA_STREAM
            ),
            "camera_color_image_raw_compressed.jsonl",
        )

        self.assertEqual(
            stream_file_name(
                "/camera/imu"
            ),
            "camera_imu.jsonl",
        )

        self.assertEqual(
            stream_file_name(
                "/handsfree/imu"
            ),
            "handsfree_imu.jsonl",
        )

    def test_08_camera_feature_record(self):
        record = FeatureRecord(
            trajectory_id="Circle_01",
            source_stream_id=CAMERA_STREAM,
            selected_reader_index=7,
            stream_index=2,
            bag_record_time_ns=100,
            header_stamp_ns=90,
            feature_values=(
                1.0,
                2.0,
                3.0,
            ),
        )

        payload = feature_record_payload(
            record
        )

        self.assertEqual(
            payload[
                "schema"
            ],
            FEATURE_RECORD_SCHEMA,
        )

        self.assertEqual(
            payload[
                "split_role"
            ],
            "train",
        )

        self.assertEqual(
            payload[
                "modality"
            ],
            "camera",
        )

        self.assertNotIn(
            "health_label",
            payload,
        )

    def test_09_imu_feature_record(self):
        record = FeatureRecord(
            trajectory_id="Circle_01",
            source_stream_id="/camera/imu",
            selected_reader_index=8,
            stream_index=3,
            bag_record_time_ns=101,
            header_stamp_ns=None,
            feature_values=(
                4.0,
                9.8,
            ),
        )

        self.assertEqual(
            feature_record_payload(
                record
            )[
                "modality"
            ],
            "imu",
        )

    def test_10_wrong_feature_count_rejected(self):
        with self.assertRaises(
            SE3FeatureExtractionError
        ):
            FeatureRecord(
                trajectory_id="Circle_01",
                source_stream_id=CAMERA_STREAM,
                selected_reader_index=0,
                stream_index=0,
                bag_record_time_ns=0,
                header_stamp_ns=None,
                feature_values=(
                    1.0,
                ),
            )

    def test_11_nonfinite_feature_rejected(self):
        with self.assertRaises(
            SE3FeatureExtractionError
        ):
            FeatureRecord(
                trajectory_id="Circle_01",
                source_stream_id="/camera/imu",
                selected_reader_index=0,
                stream_index=0,
                bag_record_time_ns=0,
                header_stamp_ns=None,
                feature_values=(
                    float("nan"),
                    1.0,
                ),
            )

    def test_12_line_serialization_is_canonical(self):
        record = FeatureRecord(
            trajectory_id="Circle_01",
            source_stream_id="/camera/imu",
            selected_reader_index=0,
            stream_index=0,
            bag_record_time_ns=11,
            header_stamp_ns=10,
            feature_values=(
                1.0,
                2.0,
            ),
        )

        line = feature_record_line(
            record
        )

        self.assertTrue(
            line.endswith(
                b"\n"
            )
        )

        self.assertEqual(
            line,
            canonical_json_bytes(
                feature_record_payload(
                    record
                )
            )
            + b"\n",
        )

    def test_13_accumulator_contiguous_stream_index(self):
        accumulator = (
            FeatureStreamAccumulator(
                trajectory_id="Circle_01",
                source_stream_id="/camera/imu",
            )
        )

        record = FeatureRecord(
            trajectory_id="Circle_01",
            source_stream_id="/camera/imu",
            selected_reader_index=0,
            stream_index=1,
            bag_record_time_ns=11,
            header_stamp_ns=10,
            feature_values=(
                1.0,
                2.0,
            ),
        )

        with self.assertRaises(
            SE3FeatureExtractionError
        ):
            accumulator.add(
                raw_serialized_payload=b"abc",
                record=record,
                serialized_line=feature_record_line(
                    record
                ),
            )

    def test_14_accumulator_present_summary(self):
        accumulator = (
            FeatureStreamAccumulator(
                trajectory_id="Circle_01",
                source_stream_id="/camera/imu",
            )
        )

        raw = b"abc"

        record = FeatureRecord(
            trajectory_id="Circle_01",
            source_stream_id="/camera/imu",
            selected_reader_index=0,
            stream_index=0,
            bag_record_time_ns=11,
            header_stamp_ns=10,
            feature_values=(
                3.0,
                4.0,
            ),
        )

        line = feature_record_line(
            record
        )

        accumulator.add(
            raw_serialized_payload=raw,
            record=record,
            serialized_line=line,
        )

        summary = accumulator.summary(
            feature_file_relative_path="features/x.jsonl"
        )

        expected_raw = sha256()
        expected_raw.update(
            struct.pack(
                ">Q",
                len(raw),
            )
        )
        expected_raw.update(
            raw
        )

        self.assertEqual(
            summary[
                "availability"
            ],
            "observed_present",
        )

        self.assertEqual(
            summary[
                "feature_record_count"
            ],
            1,
        )

        self.assertEqual(
            summary[
                "source_raw_sequence_sha256"
            ],
            expected_raw.hexdigest(),
        )

        self.assertEqual(
            summary[
                "feature_file_sha256"
            ],
            sha256(
                line
            ).hexdigest(),
        )

        self.assertEqual(
            summary[
                "feature_statistics"
            ][
                "angular_speed_norm_rad_s"
            ][
                "mean"
            ],
            3.0,
        )

    def test_15_accumulator_absent_summary(self):
        accumulator = (
            FeatureStreamAccumulator(
                trajectory_id="street_010",
                source_stream_id=CAMERA_STREAM,
            )
        )

        summary = accumulator.summary(
            feature_file_relative_path=None
        )

        self.assertEqual(
            summary[
                "availability"
            ],
            "observed_absent",
        )

        self.assertEqual(
            summary[
                "feature_record_count"
            ],
            0,
        )

        self.assertIsNone(
            summary[
                "feature_file_relative_path"
            ]
        )

        self.assertIsNone(
            summary[
                "feature_statistics"
            ]
        )

    def test_16_absent_stream_cannot_claim_file(self):
        accumulator = (
            FeatureStreamAccumulator(
                trajectory_id="street_010",
                source_stream_id=CAMERA_STREAM,
            )
        )

        with self.assertRaises(
            SE3FeatureExtractionError
        ):
            accumulator.summary(
                feature_file_relative_path="fake.jsonl"
            )

    def test_17_candidate_missing_policy(self):
        output = (
            build_candidate_manifest()[
                "output_contract"
            ]
        )

        self.assertFalse(
            output[
                "missing_stream_file_fabricated"
            ]
        )

        self.assertFalse(
            output[
                "missing_stream_zero_vector_fabricated"
            ]
        )

    def test_18_candidate_timing_boundary(self):
        timing = (
            build_candidate_manifest()[
                "timing_boundary"
            ]
        )

        self.assertFalse(
            timing[
                "shared_clock_domain_verified"
            ]
        )

        self.assertFalse(
            timing[
                "fixed_offset_selected"
            ]
        )

        self.assertFalse(
            timing[
                "interpolation_rule_selected"
            ]
        )

        self.assertFalse(
            timing[
                "cross_modal_alignment_performed"
            ]
        )

    def test_19_candidate_science_boundary(self):
        boundary = (
            build_candidate_manifest()[
                "scientific_boundary"
            ]
        )

        self.assertTrue(
            boundary[
                "train_only"
            ]
        )

        for key, value in boundary.items():
            if key != "train_only":
                self.assertFalse(
                    value,
                    key,
                )

    def test_20_candidate_validator(self):
        payload = (
            build_candidate_manifest()
        )

        validate_candidate_manifest(
            payload
        )

        changed = json.loads(
            json.dumps(
                payload
            )
        )

        changed[
            "scientific_boundary"
        ][
            "model_training_authorized"
        ] = True

        with self.assertRaises(
            SE3FeatureExtractionError
        ):
            validate_candidate_manifest(
                changed
            )

    def test_21_runner_parses(self):
        ast.parse(
            RUNNER.read_text(
                encoding="utf-8"
            ),
            filename=str(
                RUNNER
            ),
        )

    def test_22_runner_uses_anyreader(self):
        text = RUNNER.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "AnyReader",
            text,
        )

        self.assertIn(
            "resolve_train_bag_path",
            text,
        )

    def test_22b_runner_uses_frozen_train_replay_source(self):
        tree = ast.parse(
            RUNNER.read_text(
                encoding="utf-8"
            ),
            filename=str(
                RUNNER
            ),
        )

        load_calls = []
        resolve_calls = []

        for node in ast.walk(
            tree
        ):
            if not isinstance(
                node,
                ast.Call,
            ):
                continue

            function = node.func

            if not isinstance(
                function,
                ast.Name,
            ):
                continue

            if (
                function.id
                == "load_train_replay_source_from_manifest_file"
            ):
                load_calls.append(
                    node
                )

            if (
                function.id
                == "resolve_train_bag_path"
            ):
                resolve_calls.append(
                    node
                )

        self.assertEqual(
            len(
                load_calls
            ),
            1,
        )

        self.assertEqual(
            len(
                resolve_calls
            ),
            1,
        )

        load_call = load_calls[0]

        self.assertGreaterEqual(
            len(
                load_call.args
            ),
            2,
        )

        self.assertIsInstance(
            load_call.args[0],
            ast.Name,
        )

        self.assertEqual(
            load_call.args[0].id,
            "SPLIT_MANIFEST",
        )

        self.assertIsInstance(
            load_call.args[1],
            ast.Name,
        )

        self.assertEqual(
            load_call.args[1].id,
            "trajectory_id",
        )

        expected_hash_keywords = [
            keyword
            for keyword
            in load_call.keywords
            if (
                keyword.arg
                == "expected_file_sha256"
            )
        ]

        self.assertEqual(
            len(
                expected_hash_keywords
            ),
            1,
        )

        self.assertIsInstance(
            expected_hash_keywords[
                0
            ].value,
            ast.Name,
        )

        self.assertEqual(
            expected_hash_keywords[
                0
            ].value.id,
            "FROZEN_SPLIT_SHA256",
        )

        resolve_call = resolve_calls[0]

        self.assertEqual(
            len(
                resolve_call.args
            ),
            2,
        )

        self.assertIsInstance(
            resolve_call.args[0],
            ast.Name,
        )

        self.assertEqual(
            resolve_call.args[0].id,
            "dataset_root",
        )

        self.assertIsInstance(
            resolve_call.args[1],
            ast.Name,
        )

        self.assertEqual(
            resolve_call.args[1].id,
            "source",
        )

        text = RUNNER.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "actual_bag_sha256",
            text,
        )

        self.assertIn(
            "source.bag_sha256",
            text,
        )

    def test_23_runner_atomic_partial_completion(self):
        text = RUNNER.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            '".partial"',
            text,
        )

        self.assertIn(
            "os.replace",
            text,
        )

        self.assertIn(
            "shutil.rmtree",
            text,
        )

    def test_24_runner_writes_success_last(self):
        text = RUNNER.read_text(
            encoding="utf-8"
        )

        success_position = text.find(
            'success_path ='
        )

        replace_position = text.find(
            'os.replace'
        )

        self.assertGreater(
            success_position,
            0,
        )

        self.assertGreater(
            replace_position,
            success_position,
        )

    def test_25_runner_has_no_model_dependency(self):
        tree = ast.parse(
            RUNNER.read_text(
                encoding="utf-8"
            ),
            filename=str(
                RUNNER
            ),
        )

        modules = []

        for node in ast.walk(
            tree
        ):
            if isinstance(
                node,
                ast.Import,
            ):
                modules.extend(
                    alias.name
                    for alias in node.names
                )

            elif isinstance(
                node,
                ast.ImportFrom,
            ):
                modules.append(
                    node.module
                    or ""
                )

        for forbidden in (
            "sklearn",
            "torch",
            "multimodal_health_model",
            "health_supervision",
            "evo",
        ):
            self.assertFalse(
                any(
                    forbidden
                    in module
                    for module in modules
                ),
                (
                    forbidden,
                    modules,
                ),
            )

    def test_26_no_reference_or_score_fields_in_feature_record(self):
        record = FeatureRecord(
            trajectory_id="Circle_01",
            source_stream_id="/camera/imu",
            selected_reader_index=0,
            stream_index=0,
            bag_record_time_ns=1,
            header_stamp_ns=None,
            feature_values=(
                1.0,
                2.0,
            ),
        )

        payload = feature_record_payload(
            record
        )

        for forbidden in (
            "health_label",
            "reference",
            "ate",
            "rpe",
            "score",
            "probability",
            "threshold",
        ):
            self.assertFalse(
                any(
                    forbidden
                    in key.lower()
                    for key
                    in payload
                )
            )


if __name__ == "__main__":
    unittest.main()
