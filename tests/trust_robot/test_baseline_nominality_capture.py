from dataclasses import FrozenInstanceError
from hashlib import sha256
from pathlib import Path
import ast
import json
import unittest

from trust_robot.baseline_nominality import (
    BaselineNominalitySplit,
)

from trust_robot.baseline_nominality_capture import (
    RawAcquisitionArtifactReceipt,
    RawCaptureError,
    RawEvidenceKind,
    build_empty_raw_capture_registry_manifest,
    build_raw_capture_bundle_manifest,
)


ROOT = Path(__file__).resolve().parents[2]

CONFIG = (
    ROOT
    / "configs/trust_robot/"
      "phase5_baseline_nominality_raw_capture_candidate_v1.json"
)

MODULE = (
    ROOT
    / "src/trust_robot/baseline_nominality_capture.py"
)

A = "a" * 64
B = "b" * 64


def canonical_sha(payload):
    value = dict(
        payload
    )

    value.pop(
        "content_sha256",
        None,
    )

    return sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def receipt(**overrides):
    values = {
        "artifact_id":
            "ARTIFACT_001",

        "acquisition_session_id":
            "SESSION_001",

        "split":
            BaselineNominalitySplit.TRAIN,

        "evidence_kind":
            RawEvidenceKind.SENSOR_STATUS,

        "source_identifier":
            "manufacturer_status_http_response",

        "modality":
            "lidar",

        "hardware_vendor":
            "Velodyne",

        "hardware_model":
            "VLP-32C",

        "raw_sha256":
            A,

        "raw_byte_count":
            128,

        "capture_metadata_sha256":
            B,

        "host_clock_id":
            "host_monotonic_clock",

        "host_capture_start_ns":
            100,

        "host_capture_end_ns":
            200,

        "raw_bytes_preserved":
            True,

        "capture_metadata_preserved":
            True,

        "host_times_transport_provenance_only":
            True,
    }

    values.update(
        overrides
    )

    return RawAcquisitionArtifactReceipt(
        **values
    )


class BaselineNominalityRawCaptureTests(unittest.TestCase):
    def test_01_config_digest(self):
        payload = json.loads(
            CONFIG.read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(
            payload[
                "content_sha256"
            ],
            canonical_sha(
                payload
            ),
        )

    def test_02_evidence_kind_vocabulary_exact(self):
        self.assertEqual(
            [
                value.value
                for value
                in RawEvidenceKind
            ],
            [
                "measurement",
                "sensor_status",
                "sensor_diagnostic",
                "position_packet",
            ],
        )

    def test_03_empty_registry_has_no_capture_or_labels(self):
        manifest = (
            build_empty_raw_capture_registry_manifest()
        )

        self.assertEqual(
            manifest[
                "raw_artifact_count"
            ],
            0,
        )

        self.assertEqual(
            manifest[
                "accepted_baseline_nominality_source_count"
            ],
            0,
        )

        self.assertEqual(
            manifest[
                "real_health_label_count"
            ],
            0,
        )

        self.assertFalse(
            manifest[
                "health_label_generation_authorized"
            ]
        )

    def test_04_valid_status_receipt_is_raw_only(self):
        payload = receipt().to_dict()

        self.assertTrue(
            payload[
                "raw_capture_only"
            ]
        )

        self.assertFalse(
            payload[
                "interval_binding_claimed"
            ]
        )

        self.assertFalse(
            payload[
                "health_label_claimed"
            ]
        )

    def test_05_position_packet_kind_is_supported(self):
        value = receipt(
            evidence_kind=
                RawEvidenceKind.POSITION_PACKET,

            source_identifier=
                "manufacturer_position_packet",
        )

        self.assertIs(
            value.evidence_kind,
            RawEvidenceKind.POSITION_PACKET,
        )

    def test_06_receipt_is_immutable(self):
        value = receipt()

        with self.assertRaises(
            FrozenInstanceError
        ):
            value.raw_byte_count = 1

    def test_07_wrong_modality_rejected(self):
        with self.assertRaises(
            RawCaptureError
        ):
            receipt(
                modality="imu"
            )

    def test_08_invalid_digest_rejected(self):
        with self.assertRaises(
            RawCaptureError
        ):
            receipt(
                raw_sha256="bad"
            )

    def test_09_empty_raw_payload_rejected(self):
        with self.assertRaises(
            RawCaptureError
        ):
            receipt(
                raw_byte_count=0
            )

    def test_10_host_end_before_start_rejected(self):
        with self.assertRaises(
            RawCaptureError
        ):
            receipt(
                host_capture_start_ns=200,
                host_capture_end_ns=100,
            )

    def test_11_raw_bytes_must_be_preserved(self):
        with self.assertRaises(
            RawCaptureError
        ):
            receipt(
                raw_bytes_preserved=False
            )

    def test_12_capture_metadata_must_be_preserved(self):
        with self.assertRaises(
            RawCaptureError
        ):
            receipt(
                capture_metadata_preserved=False
            )

    def test_13_host_time_must_remain_transport_only(self):
        with self.assertRaises(
            RawCaptureError
        ):
            receipt(
                host_times_transport_provenance_only=False
            )

    def test_14_interval_binding_claim_rejected(self):
        with self.assertRaises(
            RawCaptureError
        ):
            receipt(
                interval_binding_claimed=True
            )

    def test_15_physical_measurement_time_claim_rejected(self):
        with self.assertRaises(
            RawCaptureError
        ):
            receipt(
                physical_measurement_time_claimed=True
            )

    def test_16_nominality_acceptance_and_health_claims_rejected(self):
        for field in (
            "baseline_nominality_claimed",
            "source_acceptance_claimed",
            "health_label_claimed",
        ):
            with self.subTest(
                field=field
            ):
                with self.assertRaises(
                    RawCaptureError
                ):
                    receipt(
                        **{
                            field:
                                True
                        }
                    )

    def test_17_confirmation_split_not_available(self):
        with self.assertRaises(
            RawCaptureError
        ):
            receipt(
                split="confirmation_test"
            )

    def test_18_bundle_requires_single_session(self):
        first = receipt(
            artifact_id="A"
        )

        second = receipt(
            artifact_id="B",
            acquisition_session_id="SESSION_002",
        )

        with self.assertRaises(
            RawCaptureError
        ):
            build_raw_capture_bundle_manifest(
                (
                    first,
                    second,
                )
            )

    def test_19_bundle_rejects_duplicate_artifact_ids(self):
        first = receipt()
        second = receipt(
            evidence_kind=
                RawEvidenceKind.SENSOR_DIAGNOSTIC,

            source_identifier=
                "manufacturer_diagnostic_http_response",
        )

        with self.assertRaises(
            RawCaptureError
        ):
            build_raw_capture_bundle_manifest(
                (
                    first,
                    second,
                )
            )

    def test_20_bundle_and_fingerprint_deterministic_no_classifier_api(self):
        measurement = receipt(
            artifact_id="M",
            evidence_kind=
                RawEvidenceKind.MEASUREMENT,

            source_identifier=
                "raw_lidar_measurement",
        )

        status = receipt(
            artifact_id="S",
            evidence_kind=
                RawEvidenceKind.SENSOR_STATUS,

            source_identifier=
                "manufacturer_status_http_response",
        )

        first = build_raw_capture_bundle_manifest(
            (
                status,
                measurement,
            )
        )

        second = build_raw_capture_bundle_manifest(
            (
                measurement,
                status,
            )
        )

        self.assertEqual(
            first,
            second,
        )

        self.assertEqual(
            measurement.fingerprint_sha256,
            receipt(
                artifact_id="M",
                evidence_kind=
                    RawEvidenceKind.MEASUREMENT,

                source_identifier=
                    "raw_lidar_measurement",
            ).fingerprint_sha256,
        )

        source = MODULE.read_text(
            encoding="utf-8"
        )

        tree = ast.parse(
            source,
            filename=str(
                MODULE
            ),
        )

        declarations = {
            node.name.lower()
            for node in tree.body
            if isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                ),
            )
        }

        for forbidden in (
            "classify",
            "predict",
            "fit",
            "train",
            "associate",
            "interpolate",
            "accept_source",
            "assign_health",
        ):
            self.assertNotIn(
                forbidden,
                declarations,
            )


if __name__ == "__main__":
    unittest.main()
