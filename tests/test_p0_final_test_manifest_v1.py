from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(
    __file__
).resolve().parents[1]

MODULE_PATH = (
    ROOT
    / "experiments/01_integrity_p0/"
      "build_p0_final_test_manifest_v1.py"
)

SPEC = (
    importlib.util
    .spec_from_file_location(
        "build_p0_final_test_manifest_v1",
        MODULE_PATH,
    )
)

if (
    SPEC is None
    or SPEC.loader is None
):
    raise RuntimeError(
        "Unable to import final-test generator"
    )

MOD = (
    importlib.util
    .module_from_spec(
        SPEC
    )
)

sys.modules[
    SPEC.name
] = MOD

SPEC.loader.exec_module(
    MOD
)


class P0FinalTestManifestV1Tests(
    unittest.TestCase
):

    def test_repository_src_bootstrap_is_active(
        self,
    ):
        import sys

        expected_src = str(
            MOD.ROOT
            / "src"
        )

        expected_experiment_dir = str(
            MOD.ROOT
            / "experiments/01_integrity_p0"
        )

        self.assertIn(
            expected_src,
            sys.path,
        )

        self.assertIn(
            expected_experiment_dir,
            sys.path,
        )

        self.assertTrue(
            hasattr(
                MOD.DEV,
                "load_clean_stream",
            )
        )

        self.assertTrue(
            hasattr(
                MOD.DEV,
                "build_spec",
            )
        )

    def test_corrected_generator_tag_does_not_rewrite_failed_tag(
        self,
    ):
        self.assertEqual(
            MOD.FAILED_PREFLIGHT_GENERATOR_TAG,
            "p0-final-test-generator-v1",
        )

        self.assertEqual(
            MOD.EXPECTED_FAILED_PREFLIGHT_COMMIT,
            "6c0bc4a942e55c769c61a1c1d3503707e9ef4132",
        )

        self.assertEqual(
            MOD.PREVIOUS_PREFLIGHT_GENERATOR_TAG,
            "p0-final-test-generator-v1b",
        )

        self.assertEqual(
            MOD.EXPECTED_PREVIOUS_PREFLIGHT_COMMIT,
            "122dd635aff580a88370941fa24b5321a0916cea",
        )

        self.assertEqual(
            MOD.GENERATOR_TAG,
            "p0-final-test-generator-v1c",
        )

    def test_dependency_provenance_matches_calibration_freeze(
        self,
    ):
        anchors = (
            MOD
            .PREIMPORT_DEPENDENCY_ANCHORS
        )

        self.assertEqual(
            anchors[
                "calibration_spec_tag_commit"
            ],
            "2bbd0c771601fcc9ced578e389deb42df46ffc33",
        )

        self.assertTrue(
            anchors[
                "dependencies_identical_to_calibration_freeze"
            ]
        )

        self.assertEqual(
            anchors[
                "dependency_raw_sha256"
            ],
            MOD.EXPECTED_DEPENDENCY_RAW_SHA256,
        )

    def test_reconstructed_lineage_trial_id(
        self,
    ):
        row = {
            "dataset":
                "KFALL",
            "relative_trial":
                "108/1/1",
        }

        self.assertEqual(
            MOD.reconstructed_trial_id(
                row
            ),
            "KFALL:108/1/1",
        )

    def test_build_lineage_index(
        self,
    ):
        lineage = {
            "trials": [
                {
                    "dataset":
                        "KFALL",
                    "relative_trial":
                        "108/1/1",
                },
                {
                    "dataset":
                        "UNIVRFALL",
                    "relative_trial":
                        "17/1/1",
                },
            ],
        }

        index = (
            MOD
            .build_lineage_index(
                lineage
            )
        )

        self.assertEqual(
            set(
                index
            ),
            {
                "KFALL:108/1/1",
                "UNIVRFALL:17/1/1",
            },
        )

    def test_duplicate_lineage_rejected(
        self,
    ):
        lineage = {
            "trials": [
                {
                    "dataset":
                        "KFALL",
                    "relative_trial":
                        "108/1/1",
                },
                {
                    "dataset":
                        "KFALL",
                    "relative_trial":
                        "108/1/1",
                },
            ],
        }

        with self.assertRaises(
            RuntimeError
        ):
            MOD.build_lineage_index(
                lineage
            )

    def test_final_test_selection_excludes_unverified(
        self,
    ):
        registry = {
            "records": [
                {
                    "trial_id":
                        "KFALL:108/1/1",
                    "partition":
                        "final_test",
                    "acquisition_scope": {
                        "acquisition_p0_eligible":
                            True,
                    },
                },
                {
                    "trial_id":
                        "ONFIELD:1001/88/1",
                    "partition":
                        "final_test",
                    "acquisition_scope": {
                        "acquisition_p0_eligible":
                            False,
                    },
                },
                {
                    "trial_id":
                        "KFALL:1/1/1",
                    "partition":
                        "development",
                    "acquisition_scope": {
                        "acquisition_p0_eligible":
                            True,
                    },
                },
            ],
        }

        (
            final_rows,
            selected,
            excluded,
        ) = MOD.select_final_test_rows(
            registry
        )

        self.assertEqual(
            len(
                final_rows
            ),
            2,
        )

        self.assertEqual(
            [
                row[
                    "trial_id"
                ]
                for row in selected
            ],
            [
                "KFALL:108/1/1"
            ],
        )

        self.assertEqual(
            [
                row[
                    "trial_id"
                ]
                for row in excluded
            ],
            [
                "ONFIELD:1001/88/1"
            ],
        )

    def test_final_test_tuning_permission_rejected(
        self,
    ):
        row = {
            "trial_id":
                "KFALL:108/1/1",

            "prospective_constraints": {
                "corruption_instance_created_at_registry_freeze":
                    False,
                "final_test_outcomes_available_for_tuning":
                    False,
                "may_change_corruption_policy_after_outcome_review":
                    False,
                "may_define_corruption_policy":
                    False,
                "may_select_ood_operating_point":
                    False,
                "may_select_persistence":
                    False,
                "may_tune_detector_thresholds":
                    True,
            },

            "acquisition_scope": {
                "raw_pair_verified":
                    True,
                "p0_truth_families_allowed":
                    list(
                        MOD.FAMILY_ORDER
                    ),
            },
        }

        with self.assertRaises(
            RuntimeError
        ):
            (
                MOD
                .validate_final_test_constraints(
                    row
                )
            )

    def test_valid_final_test_contract_accepted(
        self,
    ):
        row = {
            "trial_id":
                "UNIVRFALL:17/1/1",

            "prospective_constraints": {
                "corruption_instance_created_at_registry_freeze":
                    False,
                "final_test_outcomes_available_for_tuning":
                    False,
                "may_change_corruption_policy_after_outcome_review":
                    False,
                "may_define_corruption_policy":
                    False,
                "may_select_ood_operating_point":
                    False,
                "may_select_persistence":
                    False,
                "may_tune_detector_thresholds":
                    False,
            },

            "acquisition_scope": {
                "raw_pair_verified":
                    True,
                "p0_truth_families_allowed":
                    list(
                        MOD.FAMILY_ORDER
                    ),
            },
        }

        MOD.validate_final_test_constraints(
            row
        )

    def test_expected_attempt_arithmetic(
        self,
    ):
        self.assertEqual(
            MOD.EXPECTED_TRIAL_COUNT
            * len(
                MOD.FAMILY_ORDER
            )
            * len(
                MOD.SEVERITY_ORDER
            ),
            MOD.EXPECTED_ATTEMPT_COUNT,
        )

        self.assertEqual(
            MOD.EXPECTED_ATTEMPT_COUNT,
            16620,
        )

    def test_artifact_hash_survives_roundtrip(
        self,
    ):
        import json

        payload = {
            "x": {
                2:
                    "a",
                10:
                    "b",
            },
        }

        stored = (
            MOD
            .artifact_content_digest(
                payload
            )
        )

        reloaded = json.loads(
            json.dumps(
                payload
            )
        )

        self.assertEqual(
            stored,
            MOD.canonical_digest(
                reloaded
            ),
        )


if __name__ == "__main__":
    unittest.main()
