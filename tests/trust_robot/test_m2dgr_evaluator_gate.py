from copy import deepcopy
from pathlib import Path
import ast
import json
import unittest

from trust_robot.m2dgr_evaluation_protocol_v2 import (
    evaluation_protocol_v2_content_sha256,
)

from trust_robot.m2dgr_evaluator_gate import (
    M2DGREstimatorScoringBlocked,
    M2DGREvaluationGateError,
    M2DGRFailClosedEvaluationGate,
    M2DGRMetricExecutionBlocked,
    load_fail_closed_m2dgr_evaluation_gate,
    reference_family_protocol_boundary_content_sha256,
    validate_m2dgr_reference_family_protocol_boundary,
)


ROOT = Path(__file__).resolve().parents[2]

PROTOCOL = (
    ROOT
    / "configs"
    / "trust_robot"
    / "m2dgr_trajectory_association_evaluation_protocol_candidate_v2.json"
)

BOUNDARY = (
    ROOT
    / "manifests"
    / "m2dgr_reference_family_protocol_boundary_evidence_v1.json"
)

MODULE = (
    ROOT
    / "src"
    / "trust_robot"
    / "m2dgr_evaluator_gate.py"
)


def load_json(
    path,
):
    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def load_gate():
    return M2DGRFailClosedEvaluationGate(
        protocol=load_json(
            PROTOCOL
        ),
        boundary=load_json(
            BOUNDARY
        ),
    )


def rehash_boundary(
    payload,
):
    payload[
        "content_sha256"
    ] = (
        reference_family_protocol_boundary_content_sha256(
            payload
        )
    )


def rehash_protocol(
    payload,
):
    payload[
        "content_sha256"
    ] = (
        evaluation_protocol_v2_content_sha256(
            payload
        )
    )


class M2DGRFailClosedEvaluatorGateTests(
    unittest.TestCase
):
    def test_current_frozen_boundary_validates(self):
        payload = load_json(
            BOUNDARY
        )

        validate_m2dgr_reference_family_protocol_boundary(
            payload
        )

    def test_loader_builds_gate_from_frozen_artifacts(self):
        gate = (
            load_fail_closed_m2dgr_evaluation_gate(
                protocol_path=PROTOCOL,
                boundary_path=BOUNDARY,
            )
        )

        self.assertIsInstance(
            gate,
            M2DGRFailClosedEvaluationGate,
        )

    def test_metric_definitions_are_available_but_not_enabled(self):
        gate = load_gate()

        definitions = {
            item.short_name:
                item.required_dimensions
            for item
            in gate.metric_definitions
        }

        self.assertEqual(
            definitions,
            {
                "ATE_rotation":
                    ("rotation",),

                "ATE_translation":
                    ("translation",),

                "RPE_rotation":
                    ("rotation",),

                "RPE_translation":
                    ("translation",),
            },
        )

        protocol = load_json(
            PROTOCOL
        )

        for metric in protocol[
            "metric_families"
        ].values():
            self.assertFalse(
                metric["enabled"]
            )

    def test_rtk_translation_is_structural_but_execution_blocked(self):
        gate = load_gate()

        dimension = gate.dimension_gate(
            "rtk_ins",
            "translation",
        )

        self.assertTrue(
            dimension.structural_dimension_present
        )

        self.assertTrue(
            dimension.all_audited_samples_structurally_valid
        )

        self.assertFalse(
            dimension.scoring_admissible
        )

        metric = gate.metric_gate(
            "rtk_ins",
            "absolute_translation_trajectory_error",
        )

        self.assertTrue(
            metric.definition_authorized
        )

        self.assertTrue(
            metric.structural_dimensions_supported
        )

        self.assertFalse(
            metric.metric_enabled
        )

        self.assertFalse(
            metric.execution_authorized
        )

        self.assertFalse(
            metric.scoring_authorized
        )

    def test_leica_rotation_is_structurally_unavailable(self):
        gate = load_gate()

        dimension = gate.dimension_gate(
            "leica",
            "rotation",
        )

        self.assertFalse(
            dimension.structural_dimension_present
        )

        metric = gate.metric_gate(
            "leica",
            "absolute_rotation_trajectory_error",
        )

        self.assertFalse(
            metric.structural_dimensions_supported
        )

        self.assertFalse(
            metric.execution_authorized
        )

        self.assertFalse(
            metric.scoring_authorized
        )

    def test_mocap_rotation_invalid_count_is_preserved(self):
        gate = load_gate()

        dimension = gate.dimension_gate(
            "mocap",
            "rotation",
        )

        self.assertTrue(
            dimension.structural_dimension_present
        )

        self.assertEqual(
            dimension.audited_invalid_sample_count_total,
            1274,
        )

        self.assertFalse(
            dimension.all_audited_samples_structurally_valid
        )

        self.assertFalse(
            dimension.scoring_admissible
        )

    def test_every_current_family_metric_execution_request_fails_closed(self):
        gate = load_gate()

        for family in (
            "rtk_ins",
            "leica",
            "mocap",
        ):
            for definition in gate.metric_definitions:
                with self.subTest(
                    family=family,
                    metric=definition.name,
                ):
                    with self.assertRaises(
                        M2DGRMetricExecutionBlocked
                    ):
                        gate.require_metric_execution_authorized(
                            family,
                            definition.name,
                        )

    def test_estimator_scoring_request_fails_closed(self):
        gate = load_gate()

        with self.assertRaises(
            M2DGREstimatorScoringBlocked
        ):
            gate.require_estimator_scoring_authorized()

    def test_boundary_cannot_be_mutated_to_admit_scoring(self):
        boundary = deepcopy(
            load_json(
                BOUNDARY
            )
        )

        boundary[
            "family_dimension_matrix"
        ][
            "rtk_ins"
        ][
            "translation"
        ][
            "scoring_admissible_under_frozen_protocol_v2_now"
        ] = True

        rehash_boundary(
            boundary
        )

        with self.assertRaises(
            M2DGREvaluationGateError
        ):
            validate_m2dgr_reference_family_protocol_boundary(
                boundary
            )

    def test_protocol_metric_cannot_be_enabled_through_gate(self):
        protocol = deepcopy(
            load_json(
                PROTOCOL
            )
        )

        protocol[
            "metric_families"
        ][
            "absolute_translation_trajectory_error"
        ][
            "enabled"
        ] = True

        rehash_protocol(
            protocol
        )

        with self.assertRaises(
            ValueError
        ):
            M2DGRFailClosedEvaluationGate(
                protocol=protocol,
                boundary=load_json(
                    BOUNDARY
                ),
            )

    def test_module_contains_no_metric_math_or_external_numeric_stack(self):
        source = MODULE.read_text(
            encoding="utf-8"
        )

        tree = ast.parse(
            source,
            filename=str(
                MODULE
            ),
        )

        imported_roots = set()

        for node in ast.walk(
            tree
        ):
            if isinstance(
                node,
                ast.Import,
            ):
                for alias in node.names:
                    imported_roots.add(
                        alias.name.split(
                            "."
                        )[0]
                    )

            elif isinstance(
                node,
                ast.ImportFrom,
            ):
                if (
                    node.module
                    and not node.module.startswith(
                        "."
                    )
                ):
                    imported_roots.add(
                        node.module.split(
                            "."
                        )[0]
                    )

        for forbidden in (
            "numpy",
            "scipy",
            "pandas",
            "evo",
            "torch",
            "open3d",
        ):
            self.assertNotIn(
                forbidden,
                imported_roots,
            )

        function_names = {
            node.name
            for node in ast.walk(
                tree
            )
            if isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                ),
            )
        }

        for forbidden_name in (
            "compute_ate",
            "compute_rpe",
            "associate_trajectories",
            "align_trajectories",
            "score_trajectory",
            "score_estimator",
        ):
            self.assertNotIn(
                forbidden_name,
                function_names,
            )


if __name__ == "__main__":
    unittest.main()
