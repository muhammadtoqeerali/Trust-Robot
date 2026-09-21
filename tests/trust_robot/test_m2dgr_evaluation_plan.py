from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import ast
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
      "m2dgr_evaluation_plan.py"
)


def build_plan():
    return build_nonexecut_m2dgr_evaluation_plan(
        repo_root=ROOT,
        protocol_path=PROTOCOL,
        boundary_path=BOUNDARY,
        split_manifest_path=SPLIT,
        split_evidence_path=SPLIT_EVIDENCE,
        evaluator_gate_path=GATE,
    )


def rehash(
    payload,
):
    payload["content_sha256"] = (
        evaluation_plan_content_sha256(
            payload
        )
    )


class M2DGRNonExecutableEvaluationPlanTests(
    unittest.TestCase
):
    def test_plan_build_is_deterministic(self):
        first = build_plan().to_payload()
        second = build_plan().to_payload()

        self.assertEqual(
            first,
            second,
        )

        self.assertEqual(
            first["content_sha256"],
            evaluation_plan_content_sha256(
                first
            ),
        )

        validate_nonexecut_m2dgr_evaluation_plan(
            first
        )

    def test_plan_binds_expected_frozen_artifacts(self):
        payload = build_plan().to_payload()

        bindings = {
            item["role"]: item
            for item in payload[
                "provenance"
            ][
                "artifact_bindings"
            ]
        }

        self.assertEqual(
            bindings["protocol_v2"]["file_sha256"],
            "4aaec974d9d7b7f0f057a8991dc0486654d58de5f8c2e6ebf239d5d3d313d6d3",
        )

        self.assertEqual(
            bindings[
                "reference_family_boundary_v1"
            ][
                "file_sha256"
            ],
            "7d4cc9e1f7433ddd6b88b391687ca14a245ebf80877c4f4290fc3192ab7494cd",
        )

        self.assertEqual(
            bindings[
                "frozen_split_manifest_v1"
            ][
                "file_sha256"
            ],
            "017a388ef1ce4ad30812669632a022ca37c084871bc949693fd9c0541014238f",
        )

        self.assertEqual(
            bindings[
                "split_freeze_evidence_v1"
            ][
                "file_sha256"
            ],
            "9b1bddff5685f933372049966d9d72dd1162f66f8abfe29bbc80da3cbe38e9a9",
        )

        self.assertEqual(
            bindings[
                "fail_closed_evaluator_gate_v1"
            ][
                "file_sha256"
            ],
            "f53c4f66d649298cfafc20a5026a2567979d5fc3f3360fea2ac148b811c2f035",
        )

    def test_plan_does_not_bind_trajectory_outputs(self):
        provenance = build_plan().to_payload()[
            "provenance"
        ]

        self.assertFalse(
            provenance[
                "per_trajectory_values_populated"
            ]
        )

        self.assertFalse(
            provenance[
                "estimator_trajectory_bound"
            ]
        )

        self.assertFalse(
            provenance[
                "reference_trajectory_bound"
            ]
        )

        self.assertFalse(
            provenance[
                "confirmation_test_raw_data_accessed"
            ]
        )

    def test_required_provenance_fields_are_definitions_only(self):
        payload = build_plan().to_payload()

        protocol = json.loads(
            PROTOCOL.read_text(
                encoding="utf-8"
            )
        )

        expected = sorted(
            key
            for key, required
            in protocol[
                "required_provenance"
            ].items()
            if required is True
        )

        actual = payload[
            "provenance"
        ][
            "required_per_evaluation_fields"
        ]

        self.assertEqual(
            actual,
            expected,
        )

    def test_execution_contract_is_fully_unselected(self):
        execution = build_plan().to_payload()[
            "execution_contract"
        ]

        self.assertEqual(
            execution,
            {
                "association_method":
                    "unselected",

                "association_tolerance_seconds":
                    None,

                "fixed_reference_to_estimator_offset_seconds":
                    None,

                "interpolation_method":
                    "unselected",

                "evaluation_interval_policy":
                    "unselected",

                "alignment_mode":
                    "unselected",
            },
        )

    def test_confirmation_test_remains_closed(self):
        policy = build_plan().to_payload()[
            "confirmation_test_policy"
        ]

        self.assertEqual(
            policy,
            {
                "partition_closed_to_selection":
                    True,

                "used_for_selection":
                    False,

                "raw_data_accessed":
                    False,
            },
        )

    def test_all_12_family_metric_entries_remain_nonexecuting(self):
        metrics = build_plan().to_payload()[
            "metrics"
        ]

        self.assertEqual(
            len(metrics),
            12,
        )

        for metric in metrics:
            self.assertTrue(
                metric[
                    "definition_authorized"
                ]
            )

            self.assertFalse(
                metric[
                    "metric_enabled"
                ]
            )

            self.assertFalse(
                metric[
                    "execution_authorized"
                ]
            )

            self.assertFalse(
                metric[
                    "scoring_authorized"
                ]
            )

    def test_leica_rotation_remains_structurally_unsupported(self):
        metrics = build_plan().to_payload()[
            "metrics"
        ]

        rotation = [
            item
            for item in metrics
            if (
                item["reference_family"]
                == "leica"
                and item["short_name"]
                in {
                    "ATE_rotation",
                    "RPE_rotation",
                }
            )
        ]

        self.assertEqual(
            len(rotation),
            2,
        )

        for metric in rotation:
            self.assertFalse(
                metric[
                    "structural_dimensions_supported"
                ]
            )

    def test_tampered_metric_execution_is_rejected_even_when_rehashed(self):
        payload = deepcopy(
            build_plan().to_payload()
        )

        payload[
            "metrics"
        ][0][
            "execution_authorized"
        ] = True

        rehash(
            payload
        )

        with self.assertRaises(
            M2DGREvaluationPlanError
        ):
            validate_nonexecut_m2dgr_evaluation_plan(
                payload
            )

    def test_tampered_association_choice_is_rejected_even_when_rehashed(self):
        payload = deepcopy(
            build_plan().to_payload()
        )

        payload[
            "execution_contract"
        ][
            "association_method"
        ] = "nearest_neighbor"

        rehash(
            payload
        )

        with self.assertRaises(
            M2DGREvaluationPlanError
        ):
            validate_nonexecut_m2dgr_evaluation_plan(
                payload
            )

    def test_tampered_confirmation_access_is_rejected_even_when_rehashed(self):
        payload = deepcopy(
            build_plan().to_payload()
        )

        payload[
            "confirmation_test_policy"
        ][
            "raw_data_accessed"
        ] = True

        rehash(
            payload
        )

        with self.assertRaises(
            M2DGREvaluationPlanError
        ):
            validate_nonexecut_m2dgr_evaluation_plan(
                payload
            )


    def test_immutable_plan_writer_and_loader_are_deterministic(self):
        payload = build_plan().to_payload()

        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "plan.json"

            first_sha = (
                write_immutable_nonexecut_m2dgr_evaluation_plan(
                    path,
                    payload,
                )
            )

            second_sha = (
                write_immutable_nonexecut_m2dgr_evaluation_plan(
                    path,
                    payload,
                )
            )

            self.assertEqual(
                first_sha,
                second_sha,
            )

            loaded = (
                load_nonexecut_m2dgr_evaluation_plan(
                    path
                )
            )

            self.assertEqual(
                loaded,
                payload,
            )

    def test_immutable_plan_writer_rejects_changed_content(self):
        payload = build_plan().to_payload()

        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "plan.json"

            write_immutable_nonexecut_m2dgr_evaluation_plan(
                path,
                payload,
            )

            changed = deepcopy(
                payload
            )

            changed[
                "remaining_blockers"
            ] = list(
                changed[
                    "remaining_blockers"
                ]
            ) + [
                "synthetic_changed_content"
            ]

            rehash(
                changed
            )

            with self.assertRaises(
                M2DGREvaluationPlanError
            ):
                write_immutable_nonexecut_m2dgr_evaluation_plan(
                    path,
                    changed,
                )

    def test_loader_rejects_tampered_persisted_plan(self):
        payload = build_plan().to_payload()

        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "plan.json"

            write_immutable_nonexecut_m2dgr_evaluation_plan(
                path,
                payload,
            )

            persisted = json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            )

            persisted[
                "scope"
            ][
                "metric_values_computed"
            ] = True

            path.write_text(
                json.dumps(
                    persisted,
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaises(
                M2DGREvaluationPlanError
            ):
                load_nonexecut_m2dgr_evaluation_plan(
                    path
                )

    def test_module_contains_no_trajectory_math_stack_or_execution_functions(self):
        source = MODULE.read_text(
            encoding="utf-8"
        )

        tree = ast.parse(
            source,
            filename=str(MODULE),
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
                isinstance(node, ast.ImportFrom)
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
            for node in ast.walk(tree)
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
