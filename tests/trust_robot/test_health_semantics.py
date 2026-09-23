from dataclasses import FrozenInstanceError
from hashlib import sha256
from pathlib import Path
import ast
import json
import unittest

from trust_robot.health_semantics import (
    HEALTH_STATE_DEFINITIONS,
    HealthLabelProvenance,
    HealthSemanticContractError,
    HealthState,
    build_health_semantic_manifest,
    validate_health_label_provenance_shape,
)


ROOT = Path(__file__).resolve().parents[2]

CONFIG = (
    ROOT
    / "configs/trust_robot/phase5_health_semantics_candidate_v1.json"
)

MODULE = (
    ROOT
    / "src/trust_robot/health_semantics.py"
)


def canonical_sha(
    payload,
):
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


def valid_provenance():
    return HealthLabelProvenance(
        source_id="UNIT_TEST_EXPLICIT_SOURCE",
        source_kind="explicit_prospective_evidence",
        justification=(
            "Synthetic unit-test provenance used only to validate "
            "the semantic contract shape."
        ),
        prospectively_declared=True,
        independent_of_final_estimator_scoring=True,
        independent_of_confirmation_test=True,
    )


class Phase5HealthSemanticsTests(
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

    def test_02_state_vocabulary_is_exactly_three_states(self):
        self.assertEqual(
            [
                state.value
                for state
                in HealthState
            ],
            [
                "healthy",
                "degraded",
                "unusable",
            ],
        )

    def test_03_each_state_has_nonempty_semantic_definition(self):
        self.assertEqual(
            set(
                HEALTH_STATE_DEFINITIONS
            ),
            set(
                HealthState
            ),
        )

        for state in HealthState:
            definition = HEALTH_STATE_DEFINITIONS[
                state
            ]

            self.assertTrue(
                definition.definition.strip()
            )

            self.assertFalse(
                definition.is_localization_accuracy_score
            )

            self.assertFalse(
                definition.is_suppression_command
            )

    def test_04_manifest_is_exactly_deterministic(self):
        first = build_health_semantic_manifest()
        second = build_health_semantic_manifest()

        self.assertEqual(
            first,
            second,
        )

    def test_05_manifest_assigns_no_real_health_labels(self):
        manifest = build_health_semantic_manifest()

        self.assertFalse(
            manifest[
                "classifier_status"
            ][
                "real_dataset_health_labels_assigned"
            ]
        )

        self.assertFalse(
            manifest[
                "classifier_status"
            ][
                "classifier_implemented"
            ]
        )

        self.assertFalse(
            manifest[
                "classifier_status"
            ][
                "threshold_selected"
            ]
        )

    def test_06_provenance_is_immutable(self):
        provenance = valid_provenance()

        with self.assertRaises(
            FrozenInstanceError
        ):
            provenance.source_id = "changed"

    def test_07_valid_explicit_provenance_shape_is_accepted(self):
        provenance = valid_provenance()

        self.assertIs(
            validate_health_label_provenance_shape(
                provenance
            ),
            provenance,
        )

    def test_08_nonprospective_provenance_is_rejected(self):
        with self.assertRaises(
            HealthSemanticContractError
        ):
            HealthLabelProvenance(
                source_id="source",
                source_kind="kind",
                justification="reason",
                prospectively_declared=False,
                independent_of_final_estimator_scoring=True,
                independent_of_confirmation_test=True,
            )

    def test_09_estimator_score_dependent_provenance_is_rejected(self):
        with self.assertRaises(
            HealthSemanticContractError
        ):
            HealthLabelProvenance(
                source_id="source",
                source_kind="kind",
                justification="reason",
                prospectively_declared=True,
                independent_of_final_estimator_scoring=False,
                independent_of_confirmation_test=True,
            )

    def test_10_confirmation_dependent_provenance_is_rejected(self):
        with self.assertRaises(
            HealthSemanticContractError
        ):
            HealthLabelProvenance(
                source_id="source",
                source_kind="kind",
                justification="reason",
                prospectively_declared=True,
                independent_of_final_estimator_scoring=True,
                independent_of_confirmation_test=False,
            )

    def test_11_clean_identity_only_is_rejected(self):
        with self.assertRaises(
            HealthSemanticContractError
        ):
            HealthLabelProvenance(
                source_id="source",
                source_kind="clean_identity",
                justification="reason",
                prospectively_declared=True,
                independent_of_final_estimator_scoring=True,
                independent_of_confirmation_test=True,
                derived_only_from_clean_identity=True,
            )

    def test_12_corruption_identity_only_is_rejected(self):
        with self.assertRaises(
            HealthSemanticContractError
        ):
            HealthLabelProvenance(
                source_id="source",
                source_kind="corruption_identity",
                justification="reason",
                prospectively_declared=True,
                independent_of_final_estimator_scoring=True,
                independent_of_confirmation_test=True,
                derived_only_from_corruption_identity=True,
            )

    def test_13_diagnostic_threshold_only_is_rejected(self):
        with self.assertRaises(
            HealthSemanticContractError
        ):
            HealthLabelProvenance(
                source_id="source",
                source_kind="diagnostic_threshold",
                justification="reason",
                prospectively_declared=True,
                independent_of_final_estimator_scoring=True,
                independent_of_confirmation_test=True,
                derived_only_from_diagnostic_value_or_threshold=True,
            )

    def test_14_provenance_fingerprint_is_deterministic(self):
        first = valid_provenance()
        second = valid_provenance()

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

    def test_15_module_has_no_historical_or_ml_dependency(self):
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

        for node in ast.walk(
            tree
        ):
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

        for forbidden in (
            "imu_reliability",
            "torch",
            "sklearn",
            "numpy",
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
                ),
                (
                    forbidden,
                    modules,
                ),
            )

    def test_16_module_exposes_no_classifier_prediction_api(self):
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
            for node
            in tree.body
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
            "assign_health_state",
        ):
            self.assertNotIn(
                forbidden,
                declarations,
            )


if __name__ == "__main__":
    unittest.main()
