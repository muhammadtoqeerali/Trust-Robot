from dataclasses import FrozenInstanceError
from hashlib import sha256
from pathlib import Path
import ast
import json
import unittest

from trust_robot.baseline_nominality import (
    BaselineNominalityError,
    BaselineNominalitySplit,
    Vlp32cBaselineNominalityCandidate,
    build_empty_baseline_nominality_registry_manifest,
)


ROOT = Path(__file__).resolve().parents[2]

CONFIG = (
    ROOT
    / "configs/trust_robot/"
      "phase5_baseline_nominality_protocol_candidate_v1.json"
)

MODULE = (
    ROOT
    / "src/trust_robot/baseline_nominality.py"
)

A = "a" * 64
B = "b" * 64
C = "c" * 64
D = "d" * 64


def canonical_sha(payload):
    value = dict(payload)
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


def candidate(**overrides):
    values = {
        "candidate_id":
            "UNIT_BASELINE",

        "acquisition_session_id":
            "SESSION_001",

        "measurement_interval_id":
            "INTERVAL_001",

        "source_measurement_id":
            "MEASUREMENT_001",

        "split":
            BaselineNominalitySplit.TRAIN,

        "modality":
            "lidar",

        "hardware_vendor":
            "Velodyne",

        "hardware_model":
            "VLP-32C",

        "source_measurement_sha256":
            A,

        "raw_operational_status_sha256":
            B,

        "interval_binding_receipt_sha256":
            C,

        "no_intervention_receipt_sha256":
            D,

        "motor_state":
            "ON",

        "laser_state":
            "ON",

        "thermal_status":
            "Ok",

        "operational_status_observed":
            True,

        "operational_status_interval_bound":
            True,

        "interval_binding_semantics_explicit":
            True,

        "no_deliberate_availability_intervention_verified":
            True,

        "manufacturer_semantics_bound":
            True,

        "prospective":
            True,

        "independent_of_phase4_features":
            True,

        "independent_of_final_estimator_scoring":
            True,

        "independent_of_reference_trajectory":
            True,

        "independent_of_confirmation_test":
            True,
    }

    values.update(
        overrides
    )

    return Vlp32cBaselineNominalityCandidate(
        **values
    )


class BaselineNominalityTests(unittest.TestCase):
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

    def test_02_empty_registry(self):
        manifest = (
            build_empty_baseline_nominality_registry_manifest()
        )

        self.assertEqual(
            manifest[
                "registry"
            ][
                "accepted_baseline_nominality_source_count"
            ],
            0,
        )

        self.assertEqual(
            manifest[
                "registry"
            ][
                "real_health_label_count"
            ],
            0,
        )

        self.assertFalse(
            manifest[
                "authorization"
            ][
                "health_label_generation"
            ]
        )

    def test_03_valid_candidate_shape_is_not_acceptance(self):
        payload = candidate().to_dict()

        self.assertTrue(
            payload[
                "candidate_shape_valid"
            ]
        )

        self.assertFalse(
            payload[
                "source_accepted"
            ]
        )

        self.assertFalse(
            payload[
                "healthy_label_assigned"
            ]
        )

    def test_04_immutable(self):
        value = candidate()

        with self.assertRaises(
            FrozenInstanceError
        ):
            value.motor_state = "OFF"

    def test_05_wrong_modality_rejected(self):
        with self.assertRaises(
            BaselineNominalityError
        ):
            candidate(
                modality="imu"
            )

    def test_06_wrong_hardware_rejected(self):
        with self.assertRaises(
            BaselineNominalityError
        ):
            candidate(
                hardware_model="OTHER"
            )

    def test_07_motor_must_be_on(self):
        with self.assertRaises(
            BaselineNominalityError
        ):
            candidate(
                motor_state="OFF"
            )

    def test_08_laser_must_be_on(self):
        with self.assertRaises(
            BaselineNominalityError
        ):
            candidate(
                laser_state="DISABLED"
            )

    def test_09_thermal_must_be_ok(self):
        with self.assertRaises(
            BaselineNominalityError
        ):
            candidate(
                thermal_status="Thermal shutdown"
            )

    def test_10_status_must_be_observed(self):
        with self.assertRaises(
            BaselineNominalityError
        ):
            candidate(
                operational_status_observed=False
            )

    def test_11_status_must_be_interval_bound(self):
        with self.assertRaises(
            BaselineNominalityError
        ):
            candidate(
                operational_status_interval_bound=False
            )

    def test_12_interval_binding_semantics_required(self):
        with self.assertRaises(
            BaselineNominalityError
        ):
            candidate(
                interval_binding_semantics_explicit=False
            )

    def test_13_no_intervention_receipt_required(self):
        with self.assertRaises(
            BaselineNominalityError
        ):
            candidate(
                no_deliberate_availability_intervention_verified=False
            )

    def test_14_phase4_independence_required(self):
        with self.assertRaises(
            BaselineNominalityError
        ):
            candidate(
                independent_of_phase4_features=False
            )

    def test_15_score_reference_confirmation_independence(self):
        for field in (
            "independent_of_final_estimator_scoring",
            "independent_of_reference_trajectory",
            "independent_of_confirmation_test",
        ):
            with self.subTest(
                field=field
            ):
                with self.assertRaises(
                    BaselineNominalityError
                ):
                    candidate(
                        **{
                            field:
                                False
                        }
                    )

    def test_16_timing_selection_is_prohibited_here(self):
        for field in (
            "timing_tolerance_selected",
            "timing_offset_selected",
            "interpolation_selected",
        ):
            with self.subTest(
                field=field
            ):
                with self.assertRaises(
                    BaselineNominalityError
                ):
                    candidate(
                        **{
                            field:
                                True
                        }
                    )

    def test_17_confirmation_split_not_available(self):
        self.assertEqual(
            [
                value.value
                for value
                in BaselineNominalitySplit
            ],
            [
                "train",
                "validation",
            ],
        )

        with self.assertRaises(
            BaselineNominalityError
        ):
            candidate(
                split="confirmation_test"
            )

    def test_18_deterministic_fingerprint_and_no_classifier_api(self):
        first = candidate()
        second = candidate()

        self.assertEqual(
            first.fingerprint_sha256,
            second.fingerprint_sha256,
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
            "accept_source",
            "assign_health",
        ):
            self.assertNotIn(
                forbidden,
                declarations,
            )


if __name__ == "__main__":
    unittest.main()
