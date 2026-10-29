import ast
import copy
import inspect
import unittest
from pathlib import Path

from trust_robot.m2dgr_frozen_evidence_readiness_v1 import (
    SCHEMA,
    STATUS,
    SOURCES,
    BLOCKER_CHECKS,
    MetadataReadinessError,
    load_frozen_snapshot,
    review_snapshot,
    run_review,
    report_sha256,
)

from trust_robot.analytic_15d_evidence_review_v1 import (
    BLOCKED_CAPABILITIES,
)

ROOT = Path(__file__).resolve().parents[2]


class FrozenM2DGRReadinessTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.documents, cls.hashes = load_frozen_snapshot()
        cls.report = review_snapshot(
            cls.documents, cls.hashes
        )

    def test_01_schema(self):
        self.assertEqual(self.report["schema"], SCHEMA)
        self.assertEqual(self.report["status"], STATUS)

    def test_02_eight_sources(self):
        self.assertEqual(len(SOURCES), 8)
        self.assertEqual(
            self.report["metadata_source_count"], 8
        )

    def test_03_file_hashes_present(self):
        self.assertEqual(
            set(self.report["metadata_file_sha256"]),
            set(SOURCES),
        )
        self.assertTrue(all(
            len(value) == 64
            for value in self.hashes.values()
        ))

    def test_04_all_logical_digests_match(self):
        for alias, values in SOURCES.items():
            self.assertEqual(
                self.documents[alias]["content_sha256"],
                values[2],
            )

    def test_05_eleven_explicit_diagnostics(self):
        self.assertEqual(len(BLOCKER_CHECKS), 11)
        self.assertEqual(
            self.report["explicit_diagnostic_blocker_count"],
            11,
        )

    def test_06_all_diagnostics_unresolved(self):
        self.assertTrue(all(
            x == "UNRESOLVED"
            for x in self.report[
                "diagnostic_blockers"
            ].values()
        ))

    def test_07_original_gate_distinction(self):
        self.assertIs(
            self.report[
                "diagnostic_checks_are_original_eleven_gates"
            ],
            False,
        )
        self.assertEqual(
            self.report[
                "original_m2dgr_scientific_gates_closed"
            ],
            11,
        )

    def test_08_frozen_split_counts(self):
        self.assertEqual(
            self.report["split_counts"],
            {
                "train": 22,
                "validation_calibration": 7,
                "confirmation_test": 7,
            },
        )
        self.assertEqual(
            self.report["frozen_trajectory_count"], 36
        )

    def test_09_confirmation_not_pristine(self):
        self.assertTrue(
            self.report[
                "confirmation_test_prospectively_closed"
            ]
        )
        self.assertFalse(
            self.report[
                "confirmation_test_pristine_from_prior_inspection"
            ]
        )

    def test_10_provenance_inventory(self):
        self.assertEqual(
            self.report["required_provenance_field_count"],
            17,
        )

        fields = self.documents[
            "PROTOCOL_V2"
        ]["required_provenance"]

        self.assertIs(type(fields), dict)
        self.assertEqual(len(fields), 17)
        self.assertTrue(
            all(value is True for value in fields.values())
        )

        self.assertEqual(
            self.report["required_provenance_field_names"],
            sorted(fields),
        )

    def test_11_execution_choices_unselected(self):
        for name in (
            "association_method_selected",
            "association_tolerance_selected",
            "alignment_mode_selected",
            "evaluation_interval_selected",
        ):
            self.assertIs(self.report[name], False)

    def test_12_scientific_permissions_blocked(self):
        self.assertEqual(
            set(self.report["scientific_permissions"]),
            set(BLOCKED_CAPABILITIES),
        )
        self.assertTrue(all(
            value == "BLOCKED"
            for value in self.report[
                "scientific_permissions"
            ].values()
        ))

    def test_13_zero_recorded_access(self):
        for name in (
            "recorded_data_read",
            "recorded_ground_truth_read",
            "trajectory_scoring_performed",
            "health_inference_performed",
            "real_factor_execution_authorized",
        ):
            self.assertIs(self.report[name], False)

    def test_14_tamper_each_diagnostic(self):
        for name, alias, path in BLOCKER_CHECKS:
            with self.subTest(name=name):
                altered = copy.deepcopy(self.documents)
                node = altered[alias]

                for field in path[:-1]:
                    node = node[field]

                node[path[-1]] = True

                with self.assertRaises(
                    MetadataReadinessError
                ):
                    review_snapshot(
                        altered, self.hashes
                    )

    def test_15_tamper_split(self):
        altered = copy.deepcopy(self.documents)
        altered["SPLIT"]["split_counts"]["train"] = 21

        with self.assertRaises(
            MetadataReadinessError
        ):
            review_snapshot(altered, self.hashes)

    def test_16_tamper_holdout_policy(self):
        altered = copy.deepcopy(self.documents)
        altered["SPLIT"][
            "prospective_holdout_policy"
        ][
            "confirmation_test_pristine_from_all_prior_dataset_inspection"
        ] = True

        with self.assertRaises(
            MetadataReadinessError
        ):
            review_snapshot(altered, self.hashes)

    def test_17_tamper_execution_policy(self):
        altered = copy.deepcopy(self.documents)
        altered["PROTOCOL_V2"]["authorization"][
            "metric_computation_authorized"
        ] = True

        with self.assertRaises(
            MetadataReadinessError
        ):
            review_snapshot(altered, self.hashes)

    def test_18_tamper_source_identity(self):
        altered = copy.deepcopy(self.documents)
        altered["CALIBRATION"]["content_sha256"] = "0"*64

        with self.assertRaises(
            MetadataReadinessError
        ):
            review_snapshot(altered, self.hashes)

        altered = copy.deepcopy(self.documents)
        altered["PROTOCOL_V2"][
            "required_provenance"
        ]["alignment_mode"] = False

        with self.assertRaises(
            MetadataReadinessError
        ):
            review_snapshot(altered, self.hashes)

    def test_19_deterministic_report(self):
        second = run_review()

        self.assertEqual(
            report_sha256(self.report),
            report_sha256(second),
        )

        self.assertEqual(
            self.report["decision"], "NO_ADMISSION"
        )

        with self.assertRaises(
            MetadataReadinessError
        ):
            report_sha256({})

    def test_20_fixed_metadata_only_scope(self):
        self.assertEqual(
            len(inspect.signature(run_review).parameters),
            0,
        )

        self.assertTrue(all(
            item[0].endswith(".json")
            and item[0].startswith((
                "manifests/",
                "configs/trust_robot/",
            ))
            for item in SOURCES.values()
        ))

        path = ROOT / (
            "src/trust_robot/"
            "m2dgr_frozen_evidence_readiness_v1.py"
        )

        tree = ast.parse(path.read_text())

        imports = {
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
            and node.module
        }

        self.assertEqual(imports, {
            "__future__",
            "pathlib",
            "trust_robot.analytic_15d_evidence_review_v1",
        })


if __name__ == "__main__":
    unittest.main(verbosity=2)
