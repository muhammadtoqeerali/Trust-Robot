from dataclasses import fields
from pathlib import Path
import ast
import unittest

from trust_robot.m2dgr_evaluation_plan import (
    build_nonexecut_m2dgr_evaluation_plan,
)
from trust_robot.m2dgr_evaluation_request import (
    EvaluationInspectionRequest,
    M2DGREvaluationInspectionError,
    inspect_nonexecut_m2dgr_evaluation_request,
    render_evaluation_inspection_report,
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
      "m2dgr_evaluation_request.py"
)


def plan_payload():
    return build_nonexecut_m2dgr_evaluation_plan(
        repo_root=ROOT,
        protocol_path=PROTOCOL,
        boundary_path=BOUNDARY,
        split_manifest_path=SPLIT,
        split_evidence_path=SPLIT_EVIDENCE,
        evaluator_gate_path=GATE,
    ).to_payload()


class M2DGREvaluationInspectionTests(
    unittest.TestCase
):
    def test_request_schema_is_metadata_only(self):
        names = tuple(
            field.name
            for field in fields(
                EvaluationInspectionRequest
            )
        )

        self.assertEqual(
            names,
            (
                "reference_family",
                "metric_name",
                "present_provenance_fields",
            ),
        )

        forbidden_fragments = (
            "trajectory",
            "samples",
            "timestamp",
            "offset",
            "tolerance",
            "alignment",
            "transform",
            "path",
            "metric_value",
        )

        for name in names:
            lowered = name.lower()

            for forbidden in forbidden_fragments:
                self.assertNotIn(
                    forbidden,
                    lowered,
                )

    def test_rtk_translation_request_remains_blocked(self):
        report = inspect_nonexecut_m2dgr_evaluation_request(
            plan_payload(),
            EvaluationInspectionRequest(
                reference_family="rtk_ins",
                metric_name="absolute_translation_trajectory_error",
            ),
        )

        self.assertTrue(
            report.structural_dimensions_supported
        )

        self.assertFalse(
            report.metric_enabled
        )

        self.assertFalse(
            report.execution_authorized
        )

        self.assertFalse(
            report.scoring_authorized
        )

        self.assertFalse(
            report.evaluation_ready
        )

    def test_leica_rotation_reports_structurally_unsupported(self):
        report = inspect_nonexecut_m2dgr_evaluation_request(
            plan_payload(),
            EvaluationInspectionRequest(
                reference_family="leica",
                metric_name="absolute_rotation_trajectory_error",
            ),
        )

        self.assertFalse(
            report.structural_dimensions_supported
        )

        self.assertFalse(
            report.execution_authorized
        )

    def test_complete_field_names_still_do_not_enable_execution(self):
        plan = plan_payload()

        report = inspect_nonexecut_m2dgr_evaluation_request(
            plan,
            EvaluationInspectionRequest(
                reference_family="mocap",
                metric_name="relative_translation_pose_error",
                present_provenance_fields=tuple(
                    plan[
                        "provenance"
                    ][
                        "required_per_evaluation_fields"
                    ]
                ),
            ),
        )

        self.assertTrue(
            report.provenance_schema_complete
        )

        self.assertFalse(
            report.provenance_semantics_verified
        )

        self.assertFalse(
            report.execution_authorized
        )

        self.assertFalse(
            report.scoring_authorized
        )

        self.assertFalse(
            report.evaluation_ready
        )

    def test_unknown_field_is_reported_not_promoted(self):
        report = inspect_nonexecut_m2dgr_evaluation_request(
            plan_payload(),
            EvaluationInspectionRequest(
                reference_family="rtk_ins",
                metric_name="relative_rotation_pose_error",
                present_provenance_fields=(
                    "invented_parameter",
                ),
            ),
        )

        self.assertEqual(
            report.unknown_provenance_fields,
            (
                "invented_parameter",
            ),
        )

        self.assertFalse(
            report.provenance_schema_complete
        )

        self.assertFalse(
            report.evaluation_ready
        )

    def test_unknown_reference_family_is_rejected(self):
        with self.assertRaises(
            M2DGREvaluationInspectionError
        ):
            inspect_nonexecut_m2dgr_evaluation_request(
                plan_payload(),
                EvaluationInspectionRequest(
                    reference_family="unknown",
                    metric_name="absolute_translation_trajectory_error",
                ),
            )

    def test_unknown_metric_is_rejected(self):
        with self.assertRaises(
            M2DGREvaluationInspectionError
        ):
            inspect_nonexecut_m2dgr_evaluation_request(
                plan_payload(),
                EvaluationInspectionRequest(
                    reference_family="rtk_ins",
                    metric_name="invented_metric",
                ),
            )

    def test_renderer_exposes_frozen_unselected_state(self):
        report = inspect_nonexecut_m2dgr_evaluation_request(
            plan_payload(),
            EvaluationInspectionRequest(
                reference_family="rtk_ins",
                metric_name="absolute_translation_trajectory_error",
            ),
        )

        text = render_evaluation_inspection_report(
            report
        )

        self.assertIn(
            "association_method: unselected",
            text,
        )

        self.assertIn(
            "association_tolerance_seconds: None",
            text,
        )

        self.assertIn(
            "interpolation_method: unselected",
            text,
        )

        self.assertIn(
            "evaluation_interval_policy: unselected",
            text,
        )

        self.assertIn(
            "alignment_mode: unselected",
            text,
        )

        self.assertIn(
            "evaluation_ready: False",
            text,
        )

        self.assertIn(
            "RESULT: BLOCKED",
            text,
        )

        self.assertIn(
            "No trajectory data or metric value was processed.",
            text,
        )

    def test_confirmation_policy_remains_closed_in_report(self):
        report = inspect_nonexecut_m2dgr_evaluation_request(
            plan_payload(),
            EvaluationInspectionRequest(
                reference_family="mocap",
                metric_name="absolute_rotation_trajectory_error",
            ),
        )

        self.assertTrue(
            report.confirmation_test_partition_closed
        )

        self.assertFalse(
            report.confirmation_test_used_for_selection
        )

        self.assertFalse(
            report.confirmation_test_raw_data_accessed
        )

    def test_module_contains_no_numeric_trajectory_stack(self):
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

        for node in ast.walk(tree):
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

        functions = {
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
                functions,
            )


if __name__ == "__main__":
    unittest.main()
