from dataclasses import FrozenInstanceError
from hashlib import sha256
from pathlib import Path
import ast
import json
import unittest

from trust_robot.baseline_nominality import (
    BaselineNominalitySplit,
)

from trust_robot.acquisition_session_provenance import (
    AcquisitionSessionProvenanceError,
    NoInterventionDeclarationCandidate,
    Vlp32cDeviceIdentityReceiptCandidate,
    build_empty_session_provenance_registry_manifest,
    build_session_provenance_bundle,
)


ROOT = Path(__file__).resolve().parents[2]

CONFIG = (
    ROOT
    / "configs/trust_robot/"
      "phase5_acquisition_session_provenance_candidate_v1.json"
)

MODULE = (
    ROOT
    / "src/trust_robot/acquisition_session_provenance.py"
)

A = "a" * 64
B = "b" * 64
C = "c" * 64


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


def identity(**overrides):
    values = {
        "receipt_id":
            "IDENTITY_001",

        "acquisition_session_id":
            "SESSION_001",

        "split":
            BaselineNominalitySplit.TRAIN,

        "modality":
            "lidar",

        "hardware_vendor":
            "Velodyne",

        "hardware_model":
            "VLP-32C",

        "info_endpoint_path":
            "/cgi/info.json",

        "raw_info_json_sha256":
            A,

        "raw_info_json_byte_count":
            128,

        "capture_metadata_sha256":
            B,

        "parsed_model":
            "VLP-32C",

        "parsed_serial":
            "SERIAL_EXAMPLE",

        "top_firmware_version":
            "4.4.0.0",

        "bottom_firmware_version":
            "4.4.0.0",

        "host_clock_id":
            "host_monotonic_clock",

        "host_capture_start_ns":
            100,

        "host_capture_end_ns":
            200,

        "raw_info_bytes_preserved":
            True,

        "serial_unique_factory_assigned_semantics_bound":
            True,

        "serial_not_user_changeable_semantics_bound":
            True,

        "active_mac_used_as_primary_identity":
            False,

        "network_address_used_as_primary_identity":
            False,

        "host_times_transport_provenance_only":
            True,
    }

    values.update(
        overrides
    )

    return Vlp32cDeviceIdentityReceiptCandidate(
        **values
    )


def declaration(**overrides):
    values = {
        "declaration_id":
            "DECLARATION_001",

        "acquisition_session_id":
            "SESSION_001",

        "split":
            BaselineNominalitySplit.TRAIN,

        "declaration_artifact_sha256":
            C,

        "baseline_condition":
            "full",

        "deliberate_availability_intervention_applied":
            False,

        "prospective_before_controlled_intervention_phase":
            True,

        "declaration_is_physical_sensor_health_truth":
            False,

        "declaration_alone_establishes_baseline_nominality":
            False,

        "reference_data_used":
            False,

        "confirmation_test_data_used":
            False,
    }

    values.update(
        overrides
    )

    return NoInterventionDeclarationCandidate(
        **values
    )


class AcquisitionSessionProvenanceTests(unittest.TestCase):
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

    def test_02_empty_registry_has_zero_receipts_and_labels(self):
        payload = (
            build_empty_session_provenance_registry_manifest()
        )

        self.assertEqual(
            payload[
                "device_identity_receipt_count"
            ],
            0,
        )

        self.assertEqual(
            payload[
                "no_intervention_declaration_count"
            ],
            0,
        )

        self.assertEqual(
            payload[
                "real_health_label_count"
            ],
            0,
        )

        self.assertFalse(
            payload[
                "live_sensor_probe_authorized"
            ]
        )

    def test_03_valid_identity_uses_serial(self):
        payload = identity().to_dict()

        self.assertEqual(
            payload[
                "primary_physical_device_identity_field"
            ],
            "serial",
        )

        self.assertEqual(
            payload[
                "parsed_serial"
            ],
            "SERIAL_EXAMPLE",
        )

    def test_04_identity_is_not_nominality_or_health(self):
        payload = identity().to_dict()

        self.assertFalse(
            payload[
                "baseline_nominality_claimed"
            ]
        )

        self.assertFalse(
            payload[
                "source_acceptance_claimed"
            ]
        )

        self.assertFalse(
            payload[
                "health_label_claimed"
            ]
        )

    def test_05_identity_is_immutable(self):
        value = identity()

        with self.assertRaises(
            FrozenInstanceError
        ):
            value.parsed_serial = "OTHER"

    def test_06_serial_required(self):
        with self.assertRaises(
            AcquisitionSessionProvenanceError
        ):
            identity(
                parsed_serial=""
            )

    def test_07_model_must_match(self):
        with self.assertRaises(
            AcquisitionSessionProvenanceError
        ):
            identity(
                parsed_model="OTHER"
            )

    def test_08_info_endpoint_exact(self):
        with self.assertRaises(
            AcquisitionSessionProvenanceError
        ):
            identity(
                info_endpoint_path="/cgi/status.json"
            )

    def test_09_invalid_digest_rejected(self):
        with self.assertRaises(
            AcquisitionSessionProvenanceError
        ):
            identity(
                raw_info_json_sha256="bad"
            )

    def test_10_raw_info_must_be_nonempty(self):
        with self.assertRaises(
            AcquisitionSessionProvenanceError
        ):
            identity(
                raw_info_json_byte_count=0
            )

    def test_11_host_time_order_validated(self):
        with self.assertRaises(
            AcquisitionSessionProvenanceError
        ):
            identity(
                host_capture_start_ns=200,
                host_capture_end_ns=100,
            )

    def test_12_host_time_transport_only_required(self):
        with self.assertRaises(
            AcquisitionSessionProvenanceError
        ):
            identity(
                host_times_transport_provenance_only=False
            )

    def test_13_serial_manufacturer_semantics_required(self):
        for field in (
            "serial_unique_factory_assigned_semantics_bound",
            "serial_not_user_changeable_semantics_bound",
        ):
            with self.subTest(
                field=field
            ):
                with self.assertRaises(
                    AcquisitionSessionProvenanceError
                ):
                    identity(
                        **{
                            field:
                                False
                        }
                    )

    def test_14_active_mac_cannot_be_primary_identity(self):
        with self.assertRaises(
            AcquisitionSessionProvenanceError
        ):
            identity(
                active_mac_used_as_primary_identity=True
            )

    def test_15_network_address_cannot_be_primary_identity(self):
        with self.assertRaises(
            AcquisitionSessionProvenanceError
        ):
            identity(
                network_address_used_as_primary_identity=True
            )

    def test_16_valid_no_intervention_declaration_not_health_truth(self):
        payload = declaration().to_dict()

        self.assertFalse(
            payload[
                "deliberate_availability_intervention_applied"
            ]
        )

        self.assertFalse(
            payload[
                "declaration_is_physical_sensor_health_truth"
            ]
        )

        self.assertFalse(
            payload[
                "health_label_assigned"
            ]
        )

    def test_17_declaration_requires_full_baseline(self):
        with self.assertRaises(
            AcquisitionSessionProvenanceError
        ):
            declaration(
                baseline_condition="partial"
            )

    def test_18_declaration_rejects_applied_intervention(self):
        with self.assertRaises(
            AcquisitionSessionProvenanceError
        ):
            declaration(
                deliberate_availability_intervention_applied=True
            )

    def test_19_declaration_must_be_prospective(self):
        with self.assertRaises(
            AcquisitionSessionProvenanceError
        ):
            declaration(
                prospective_before_controlled_intervention_phase=False
            )

    def test_20_reference_and_confirmation_prohibited(self):
        for field in (
            "reference_data_used",
            "confirmation_test_data_used",
        ):
            with self.subTest(
                field=field
            ):
                with self.assertRaises(
                    AcquisitionSessionProvenanceError
                ):
                    declaration(
                        **{
                            field:
                                True
                        }
                    )

    def test_21_bundle_requires_same_session_and_split(self):
        with self.assertRaises(
            AcquisitionSessionProvenanceError
        ):
            build_session_provenance_bundle(
                identity(),
                declaration(
                    acquisition_session_id="SESSION_OTHER"
                ),
            )

        with self.assertRaises(
            AcquisitionSessionProvenanceError
        ):
            build_session_provenance_bundle(
                identity(),
                declaration(
                    split=BaselineNominalitySplit.VALIDATION
                ),
            )

    def test_22_bundle_deterministic_and_no_classifier_acceptance_api(self):
        first = build_session_provenance_bundle(
            identity(),
            declaration(),
        )

        second = build_session_provenance_bundle(
            identity(),
            declaration(),
        )

        self.assertEqual(
            first,
            second,
        )

        self.assertFalse(
            first[
                "scientific_nonclaims"
            ][
                "baseline_nominality_established"
            ]
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
