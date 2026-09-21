from pathlib import Path
import ast
import unittest

from trust_robot.m2dgr_evaluation_plan import (
    build_nonexecut_m2dgr_evaluation_plan,
)
from trust_robot.m2dgr_evaluation_readiness import (
    M2DGREvaluationExecutionBlocked,
    build_execution_readiness_report,
    build_provenance_completeness_report,
    require_execution_ready,
)


ROOT = Path(__file__).resolve().parents[2]

PROTOCOL = (
    ROOT
    / "configs/trust_robot/"
      "m2dgr_trajectory_association_evaluation_protocol_candidate_v2.json"
)

BOUNDARY = (
    ROOT
    / "manifests/"
      "m2dgr_reference_family_protocol_boundary_evidence_v1.json"
)

SPLIT = (
    ROOT
    / "manifests/"
      "m2dgr_trajectory_manifest_v1_split_freeze_v1.json"
)

SPLIT_EVIDENCE = (
    ROOT
    / "manifests/"
      "m2dgr_split_freeze_evidence_v1.json"
)

GATE = (
    ROOT
    / "src/trust_robot/"
      "m2dgr_evaluator_gate.py"
)

MODULE = (
    ROOT
    / "src/trust_robot/"
      "m2dgr_evaluation_readiness.py"
)


def payload():
    return build_nonexecut_m2dgr_evaluation_plan(
        repo_root=ROOT,
        protocol_path=PROTOCOL,
        boundary_path=BOUNDARY,
        split_manifest_path=SPLIT,
        split_evidence_path=SPLIT_EVIDENCE,
        evaluator_gate_path=GATE,
    ).to_payload()


class M2DGREvaluationReadinessTests(
    unittest.TestCase
):
    def test_empty_provenance_presence_reports_all_fields_missing(self):
        plan = payload()

        report = build_provenance_completeness_report(
            plan,
            present_fields=(),
        )

        self.assertEqual(
            len(
                report.required_fields
            ),
            17,
        )

        self.assertEqual(
            len(
                report.missing_fields
            ),
            17,
        )

        self.assertFalse(
            report.schema_complete
        )

        self.assertFalse(
            report.semantic_validation_performed
        )

    def test_exact_field_name_presence_can_be_schema_complete_only(self):
        plan = payload()

        required = plan[
            "provenance"
        ][
            "required_per_evaluation_fields"
        ]

        report = build_provenance_completeness_report(
            plan,
            present_fields=required,
        )

        self.assertTrue(
            report.schema_complete
        )

        self.assertEqual(
            report.missing_fields,
            (),
        )

        self.assertEqual(
            report.unknown_fields,
            (),
        )

        self.assertFalse(
            report.semantic_validation_performed
        )

    def test_unknown_provenance_field_prevents_schema_complete(self):
        plan = payload()

        required = list(
            plan[
                "provenance"
            ][
                "required_per_evaluation_fields"
            ]
        )

        required.append(
            "invented_field"
        )

        report = build_provenance_completeness_report(
            plan,
            present_fields=required,
        )

        self.assertFalse(
            report.schema_complete
        )

        self.assertEqual(
            report.unknown_fields,
            (
                "invented_field",
            ),
        )

    def test_complete_provenance_names_do_not_enable_execution(self):
        plan = payload()

        provenance = build_provenance_completeness_report(
            plan,
            present_fields=(
                plan[
                    "provenance"
                ][
                    "required_per_evaluation_fields"
                ]
            ),
        )

        self.assertTrue(
            provenance.schema_complete
        )

        readiness = build_execution_readiness_report(
            plan,
            provenance_report=provenance,
        )

        self.assertFalse(
            readiness.ready
        )

        self.assertTrue(
            readiness.provenance_schema_complete
        )

        self.assertFalse(
            readiness.provenance_semantics_verified
        )

        self.assertEqual(
            readiness.metric_entry_count,
            12,
        )

        self.assertEqual(
            readiness.executable_metric_entry_count,
            0,
        )

        self.assertEqual(
            readiness.scoreable_metric_entry_count,
            0,
        )

    def test_execution_readiness_preserves_all_global_authorization_false(self):
        readiness = build_execution_readiness_report(
            payload()
        )

        self.assertFalse(
            readiness.ready
        )

        self.assertFalse(
            readiness.association_execution_authorized
        )

        self.assertFalse(
            readiness.evaluation_interval_authorized
        )

        self.assertFalse(
            readiness.alignment_execution_authorized
        )

        self.assertFalse(
            readiness.metric_computation_authorized
        )

        self.assertFalse(
            readiness.trajectory_scoring_authorized
        )

        self.assertFalse(
            readiness.estimator_scoring_authorized
        )

        self.assertGreater(
            len(
                readiness.global_blockers
            ),
            0,
        )

    def test_require_execution_ready_always_fails_closed_currently(self):
        plan = payload()

        with self.assertRaises(
            M2DGREvaluationExecutionBlocked
        ):
            require_execution_ready(
                plan
            )

    def test_readiness_module_accepts_field_names_not_values(self):
        source = MODULE.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "does not accept provenance values",
            source,
        )

        self.assertNotIn(
            "provenance_values",
            source,
        )

    def test_readiness_module_contains_no_trajectory_math_stack(self):
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
                        alias.name.split(".")[0]
                    )

            elif (
                isinstance(
                    node,
                    ast.ImportFrom,
                )
                and node.module
                and node.level == 0
            ):
                imported_roots.add(
                    node.module.split(".")[0]
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

        for forbidden in (
            "compute_ate",
            "compute_rpe",
            "associate_trajectories",
            "interpolate_trajectory",
            "align_trajectories",
            "score_trajectory",
            "score_estimator",
            "search_lag",
            "estimate_time_offset",
        ):
            self.assertNotIn(
                forbidden,
                function_names,
            )


if __name__ == "__main__":
    unittest.main()
