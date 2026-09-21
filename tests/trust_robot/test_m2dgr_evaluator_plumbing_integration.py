from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from trust_robot.m2dgr_evaluation_plan import (
    M2DGREvaluationPlanError,
    build_nonexecut_m2dgr_evaluation_plan,
    evaluation_plan_content_sha256,
    load_nonexecut_m2dgr_evaluation_plan,
    validate_nonexecut_m2dgr_evaluation_plan,
    write_immutable_nonexecut_m2dgr_evaluation_plan,
)
from trust_robot.m2dgr_evaluation_readiness import (
    M2DGREvaluationExecutionBlocked,
    build_execution_readiness_report,
    build_provenance_completeness_report,
    require_execution_ready,
)
from trust_robot.m2dgr_evaluation_request import (
    EvaluationInspectionRequest,
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


def payload():
    return build_nonexecut_m2dgr_evaluation_plan(
        repo_root=ROOT,
        protocol_path=PROTOCOL,
        boundary_path=BOUNDARY,
        split_manifest_path=SPLIT,
        split_evidence_path=SPLIT_EVIDENCE,
        evaluator_gate_path=GATE,
    ).to_payload()


def rehash(value):
    value["content_sha256"] = (
        evaluation_plan_content_sha256(
            value
        )
    )


class M2DGREvaluatorPlumbingIntegrationTests(
    unittest.TestCase
):
    def test_plan_roundtrip_across_immutable_artifact_boundary(self):
        original = payload()

        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "plan.json"

            written_sha = (
                write_immutable_nonexecut_m2dgr_evaluation_plan(
                    path,
                    original,
                )
            )

            loaded = load_nonexecut_m2dgr_evaluation_plan(
                path
            )

            self.assertEqual(
                loaded,
                original,
            )

            self.assertEqual(
                len(written_sha),
                64,
            )

    def test_plan_artifact_bindings_are_repository_relative(self):
        plan = payload()

        for item in (
            plan[
                "provenance"
            ][
                "artifact_bindings"
            ]
        ):
            path = Path(
                item[
                    "relative_path"
                ]
            )

            self.assertFalse(
                path.is_absolute()
            )

            self.assertNotIn(
                "..",
                path.parts,
            )

    def test_complete_provenance_names_do_not_make_plan_ready(self):
        plan = payload()

        required = plan[
            "provenance"
        ][
            "required_per_evaluation_fields"
        ]

        provenance = build_provenance_completeness_report(
            plan,
            present_fields=required,
        )

        readiness = build_execution_readiness_report(
            plan,
            provenance_report=provenance,
        )

        self.assertTrue(
            provenance.schema_complete
        )

        self.assertFalse(
            provenance.semantic_validation_performed
        )

        self.assertFalse(
            readiness.ready
        )

        self.assertEqual(
            readiness.executable_metric_entry_count,
            0,
        )

        self.assertEqual(
            readiness.scoreable_metric_entry_count,
            0,
        )

        with self.assertRaises(
            M2DGREvaluationExecutionBlocked
        ):
            require_execution_ready(
                plan,
                provenance_report=provenance,
            )

    def test_all_12_metric_pairs_block_with_empty_provenance(self):
        plan = payload()

        count = 0

        for metric in plan["metrics"]:
            report = inspect_nonexecut_m2dgr_evaluation_request(
                plan,
                EvaluationInspectionRequest(
                    reference_family=
                        metric["reference_family"],

                    metric_name=
                        metric["metric_name"],
                ),
            )

            self.assertFalse(
                report.provenance_schema_complete
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

            count += 1

        self.assertEqual(
            count,
            12,
        )

    def test_all_12_metric_pairs_block_with_complete_field_names(self):
        plan = payload()

        required = tuple(
            plan[
                "provenance"
            ][
                "required_per_evaluation_fields"
            ]
        )

        count = 0

        for metric in plan["metrics"]:
            report = inspect_nonexecut_m2dgr_evaluation_request(
                plan,
                EvaluationInspectionRequest(
                    reference_family=
                        metric["reference_family"],

                    metric_name=
                        metric["metric_name"],

                    present_provenance_fields=
                        required,
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

            count += 1

        self.assertEqual(
            count,
            12,
        )

    def test_leica_rotation_is_structurally_blocked_end_to_end(self):
        plan = payload()

        for metric_name in (
            "absolute_rotation_trajectory_error",
            "relative_rotation_pose_error",
        ):
            report = inspect_nonexecut_m2dgr_evaluation_request(
                plan,
                EvaluationInspectionRequest(
                    reference_family="leica",
                    metric_name=metric_name,
                ),
            )

            self.assertFalse(
                report.structural_dimensions_supported
            )

            self.assertFalse(
                report.execution_authorized
            )

    def test_confirmation_test_policy_remains_closed_end_to_end(self):
        plan = payload()

        for metric in plan["metrics"]:
            report = inspect_nonexecut_m2dgr_evaluation_request(
                plan,
                EvaluationInspectionRequest(
                    reference_family=
                        metric["reference_family"],

                    metric_name=
                        metric["metric_name"],
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

    def test_every_rendered_report_explicitly_says_blocked(self):
        plan = payload()

        for metric in plan["metrics"]:
            report = inspect_nonexecut_m2dgr_evaluation_request(
                plan,
                EvaluationInspectionRequest(
                    reference_family=
                        metric["reference_family"],

                    metric_name=
                        metric["metric_name"],
                ),
            )

            rendered = render_evaluation_inspection_report(
                report
            )

            self.assertIn(
                "RESULT: BLOCKED",
                rendered,
            )

            self.assertIn(
                "No trajectory data or metric value was processed.",
                rendered,
            )

    def test_tamper_matrix_is_rejected_even_when_rehashed(self):
        mutations = []

        def mutate_association(plan):
            plan[
                "execution_contract"
            ][
                "association_method"
            ] = "nearest_neighbor"

        mutations.append(
            (
                "association_method",
                mutate_association,
            )
        )

        def mutate_tolerance(plan):
            plan[
                "execution_contract"
            ][
                "association_tolerance_seconds"
            ] = 0.1

        mutations.append(
            (
                "association_tolerance",
                mutate_tolerance,
            )
        )

        def mutate_alignment(plan):
            plan[
                "execution_contract"
            ][
                "alignment_mode"
            ] = "se3"

        mutations.append(
            (
                "alignment",
                mutate_alignment,
            )
        )

        def mutate_metric_execution(plan):
            plan[
                "metrics"
            ][0][
                "execution_authorized"
            ] = True

        mutations.append(
            (
                "metric_execution",
                mutate_metric_execution,
            )
        )

        def mutate_metric_scoring(plan):
            plan[
                "metrics"
            ][0][
                "scoring_authorized"
            ] = True

        mutations.append(
            (
                "metric_scoring",
                mutate_metric_scoring,
            )
        )

        def mutate_global_metric_auth(plan):
            plan[
                "execution_authorization"
            ][
                "metric_computation_authorized"
            ] = True

        mutations.append(
            (
                "global_metric_authorization",
                mutate_global_metric_auth,
            )
        )

        def mutate_confirmation_access(plan):
            plan[
                "confirmation_test_policy"
            ][
                "raw_data_accessed"
            ] = True

        mutations.append(
            (
                "confirmation_access",
                mutate_confirmation_access,
            )
        )

        def mutate_estimator_binding(plan):
            plan[
                "provenance"
            ][
                "estimator_trajectory_bound"
            ] = True

        mutations.append(
            (
                "estimator_trajectory_binding",
                mutate_estimator_binding,
            )
        )

        def mutate_reference_binding(plan):
            plan[
                "provenance"
            ][
                "reference_trajectory_bound"
            ] = True

        mutations.append(
            (
                "reference_trajectory_binding",
                mutate_reference_binding,
            )
        )

        def mutate_metric_values(plan):
            plan[
                "scope"
            ][
                "metric_values_computed"
            ] = True

        mutations.append(
            (
                "metric_values_computed",
                mutate_metric_values,
            )
        )

        rejected = 0

        for label, mutation in mutations:
            with self.subTest(
                mutation=label
            ):
                candidate = deepcopy(
                    payload()
                )

                mutation(
                    candidate
                )

                rehash(
                    candidate
                )

                with self.assertRaises(
                    M2DGREvaluationPlanError
                ):
                    validate_nonexecut_m2dgr_evaluation_plan(
                        candidate
                    )

                rejected += 1

        self.assertEqual(
            rejected,
            10,
        )

    def test_plan_digest_is_deterministic(self):
        first = payload()
        second = payload()

        self.assertEqual(
            first[
                "content_sha256"
            ],
            second[
                "content_sha256"
            ],
        )

        self.assertEqual(
            json.dumps(
                first,
                sort_keys=True,
            ),
            json.dumps(
                second,
                sort_keys=True,
            ),
        )


if __name__ == "__main__":
    unittest.main()
