from dataclasses import FrozenInstanceError
from hashlib import sha256
from pathlib import Path
import ast
import json
import unittest

from trust_robot.controlled_availability_supervision import (
    ControlledAvailabilityCondition,
    ControlledAvailabilityError,
    ControlledAvailabilityReceipt,
    ControlledAvailabilitySplit,
    MeasurementEvidenceRelation,
    build_empty_controlled_availability_registry_manifest,
    prospective_health_state_for_receipt,
)
from trust_robot.health_semantics import HealthState


ROOT = Path(__file__).resolve().parents[2]

CONFIG = (
    ROOT
    / "configs/trust_robot/"
      "phase5_controlled_availability_supervision_candidate_v1.json"
)

MODULE = (
    ROOT
    / "src/trust_robot/controlled_availability_supervision.py"
)

A = "a" * 64
B = "b" * 64
C = "c" * 64
D = "d" * 64
E = "e" * 64


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


def full_receipt(**overrides):
    values = {
        "receipt_id":
            "UNIT_TEST_FULL",

        "source_measurement_id":
            "UNIT_TEST_SOURCE",

        "interval_provenance_id":
            "UNIT_TEST_INTERVAL",

        "modality":
            "lidar",

        "split":
            ControlledAvailabilitySplit.TRAIN,

        "condition":
            ControlledAvailabilityCondition.FULL,

        "evidence_relation":
            MeasurementEvidenceRelation.IDENTICAL,

        "source_point_count":
            10,

        "retained_point_count":
            10,

        "source_measurement_sha256":
            A,

        "retained_measurement_sha256":
            A,

        "baseline_nominality_receipt_sha256":
            B,

        "intervention_execution_receipt_sha256":
            C,

        "relation_verification_receipt_sha256":
            D,

        "baseline_nominality_verified":
            True,

        "intervention_execution_verified":
            True,

        "relation_verified":
            True,

        "independent_of_phase4_features":
            True,

        "independent_of_final_estimator_scoring":
            True,

        "independent_of_confirmation_test":
            True,
    }

    values.update(
        overrides
    )

    return ControlledAvailabilityReceipt(
        **values
    )


def partial_receipt(**overrides):
    values = {
        "receipt_id":
            "UNIT_TEST_PARTIAL",

        "source_measurement_id":
            "UNIT_TEST_SOURCE",

        "interval_provenance_id":
            "UNIT_TEST_INTERVAL",

        "modality":
            "lidar",

        "split":
            ControlledAvailabilitySplit.TRAIN,

        "condition":
            ControlledAvailabilityCondition.PARTIAL,

        "evidence_relation":
            MeasurementEvidenceRelation.STRICT_PROPER_SUBSET,

        "source_point_count":
            10,

        "retained_point_count":
            5,

        "source_measurement_sha256":
            A,

        "retained_measurement_sha256":
            E,

        "baseline_nominality_receipt_sha256":
            B,

        "intervention_execution_receipt_sha256":
            C,

        "relation_verification_receipt_sha256":
            D,

        "baseline_nominality_verified":
            True,

        "intervention_execution_verified":
            True,

        "relation_verified":
            True,

        "independent_of_phase4_features":
            True,

        "independent_of_final_estimator_scoring":
            True,

        "independent_of_confirmation_test":
            True,
    }

    values.update(
        overrides
    )

    return ControlledAvailabilityReceipt(
        **values
    )


def absent_receipt(**overrides):
    values = {
        "receipt_id":
            "UNIT_TEST_ABSENT",

        "source_measurement_id":
            "UNIT_TEST_SOURCE",

        "interval_provenance_id":
            "UNIT_TEST_INTERVAL",

        "modality":
            "lidar",

        "split":
            ControlledAvailabilitySplit.TRAIN,

        "condition":
            ControlledAvailabilityCondition.ABSENT,

        "evidence_relation":
            MeasurementEvidenceRelation.NONE,

        "source_point_count":
            10,

        "retained_point_count":
            None,

        "source_measurement_sha256":
            A,

        "retained_measurement_sha256":
            None,

        "baseline_nominality_receipt_sha256":
            B,

        "intervention_execution_receipt_sha256":
            C,

        "relation_verification_receipt_sha256":
            D,

        "baseline_nominality_verified":
            True,

        "intervention_execution_verified":
            True,

        "relation_verified":
            True,

        "independent_of_phase4_features":
            True,

        "independent_of_final_estimator_scoring":
            True,

        "independent_of_confirmation_test":
            True,
    }

    values.update(
        overrides
    )

    return ControlledAvailabilityReceipt(
        **values
    )


class ControlledAvailabilitySupervisionTests(
    unittest.TestCase
):
    def test_01_config_content_digest_is_exact(self):
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

    def test_02_condition_vocabulary_is_exact(self):
        self.assertEqual(
            [
                item.value
                for item
                in ControlledAvailabilityCondition
            ],
            [
                "full",
                "partial",
                "absent",
            ],
        )

    def test_03_empty_registry_has_no_source_or_labels(self):
        manifest = (
            build_empty_controlled_availability_registry_manifest()
        )

        self.assertEqual(
            manifest[
                "registry"
            ][
                "accepted_source_count"
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
                "baseline_nominality"
            ][
                "clean_identity_alone_sufficient"
            ]
        )

    def test_04_valid_full_receipt_maps_prospectively_to_healthy(self):
        self.assertIs(
            prospective_health_state_for_receipt(
                full_receipt()
            ),
            HealthState.HEALTHY,
        )

    def test_05_valid_partial_receipt_maps_prospectively_to_degraded(self):
        self.assertIs(
            prospective_health_state_for_receipt(
                partial_receipt()
            ),
            HealthState.DEGRADED,
        )

    def test_06_valid_absent_receipt_maps_prospectively_to_unusable(self):
        self.assertIs(
            prospective_health_state_for_receipt(
                absent_receipt()
            ),
            HealthState.UNUSABLE,
        )

    def test_07_receipt_is_immutable(self):
        receipt = full_receipt()

        with self.assertRaises(
            FrozenInstanceError
        ):
            receipt.receipt_id = "changed"

    def test_08_baseline_nominality_is_mandatory(self):
        with self.assertRaises(
            ControlledAvailabilityError
        ):
            full_receipt(
                baseline_nominality_verified=False
            )

    def test_09_phase4_features_cannot_define_condition(self):
        with self.assertRaises(
            ControlledAvailabilityError
        ):
            partial_receipt(
                independent_of_phase4_features=False
            )

    def test_10_estimator_scoring_cannot_define_condition(self):
        with self.assertRaises(
            ControlledAvailabilityError
        ):
            partial_receipt(
                independent_of_final_estimator_scoring=False
            )

    def test_11_confirmation_cannot_define_condition(self):
        with self.assertRaises(
            ControlledAvailabilityError
        ):
            partial_receipt(
                independent_of_confirmation_test=False
            )

    def test_12_zero_vector_substitution_is_rejected(self):
        with self.assertRaises(
            ControlledAvailabilityError
        ):
            absent_receipt(
                zero_vector_substitution_used=True
            )

    def test_13_full_requires_identical_relation(self):
        with self.assertRaises(
            ControlledAvailabilityError
        ):
            full_receipt(
                evidence_relation=
                    MeasurementEvidenceRelation.STRICT_PROPER_SUBSET
            )

    def test_14_full_requires_complete_point_count(self):
        with self.assertRaises(
            ControlledAvailabilityError
        ):
            full_receipt(
                retained_point_count=9
            )

    def test_15_partial_requires_strict_proper_subset(self):
        with self.assertRaises(
            ControlledAvailabilityError
        ):
            partial_receipt(
                retained_point_count=10
            )

    def test_16_partial_must_remain_structurally_admissible(self):
        with self.assertRaises(
            ControlledAvailabilityError
        ):
            partial_receipt(
                retained_point_count=2
            )

    def test_17_partial_measurement_must_differ_from_source(self):
        with self.assertRaises(
            ControlledAvailabilityError
        ):
            partial_receipt(
                retained_measurement_sha256=A
            )

    def test_18_absent_requires_no_retained_measurement(self):
        with self.assertRaises(
            ControlledAvailabilityError
        ):
            absent_receipt(
                retained_point_count=3,
                retained_measurement_sha256=E,
            )

    def test_19_confirmation_split_is_not_in_protocol_vocabulary(self):
        self.assertEqual(
            [
                item.value
                for item
                in ControlledAvailabilitySplit
            ],
            [
                "train",
                "validation",
            ],
        )

        with self.assertRaises(
            ControlledAvailabilityError
        ):
            full_receipt(
                split="confirmation_test"
            )

    def test_20_fingerprint_is_deterministic_and_module_has_no_classifier_api(self):
        first = partial_receipt()
        second = partial_receipt()

        self.assertEqual(
            first.fingerprint_sha256,
            second.fingerprint_sha256,
        )

        self.assertEqual(
            len(
                first.fingerprint_sha256
            ),
            64,
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

        modules = []

        declarations = set()

        for node in ast.walk(tree):
            if isinstance(
                node,
                ast.Import,
            ):
                modules.extend(
                    alias.name
                    for alias
                    in node.names
                )

            elif isinstance(
                node,
                ast.ImportFrom,
            ):
                modules.append(
                    node.module
                    or ""
                )

        for node in tree.body:
            if isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                ),
            ):
                declarations.add(
                    node.name.lower()
                )

        for forbidden in (
            "imu_reliability",
            "torch",
            "sklearn",
            "evo",
            "evaluation",
            "reference",
        ):
            self.assertFalse(
                any(
                    forbidden
                    in module.lower()
                    for module
                    in modules
                )
            )

        for forbidden_api in (
            "classify",
            "predict",
            "fit",
            "train",
            "accept_supervision_source",
        ):
            self.assertNotIn(
                forbidden_api,
                declarations,
            )


if __name__ == "__main__":
    unittest.main()
