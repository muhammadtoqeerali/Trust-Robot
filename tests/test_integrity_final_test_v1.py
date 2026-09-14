from __future__ import annotations

import ast
import importlib.util
import json
import sys
import unittest
from pathlib import Path

import numpy as np


ROOT = Path(
    __file__
).resolve().parents[1]

MODULE_PATH = (
    ROOT
    / "experiments/01_integrity_p0/"
      "evaluate_integrity_final_test_v1.py"
)

SPEC = (
    importlib.util
    .spec_from_file_location(
        "evaluate_integrity_final_test_v1",
        MODULE_PATH,
    )
)

if (
    SPEC is None
    or SPEC.loader is None
):
    raise RuntimeError(
        "Unable to import final-test evaluator"
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


class IntegrityFinalTestV1Tests(
    unittest.TestCase
):

    def test_artifact_hash_survives_json_roundtrip(
        self,
    ):
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

    def test_calibration_runtime_dependencies_are_frozen(
        self,
    ):
        anchors = (
            MOD
            .PREIMPORT_CALIBRATION_DEPENDENCY_ANCHORS
        )

        self.assertEqual(
            anchors[
                "tag_commit"
            ],
            "dc948845a8d172f30755791d49419a3c445e31fe",
        )

        self.assertTrue(
            anchors[
                "runtime_dependencies_identical_to_hashfix_epoch"
            ]
        )

    def test_final_manifest_boundary(
        self,
    ):
        manifest = MOD.load_json(
            MOD.FINAL_MANIFEST_PATH
        )

        receipt = MOD.load_json(
            MOD.FINAL_RECEIPT_PATH
        )

        MOD.verify_final_manifest_boundary(
            manifest,
            receipt,
        )

    def test_frozen_operating_point_exact(
        self,
    ):
        op = MOD.load_json(
            MOD.OPERATING_POINT_PATH
        )

        MOD.verify_operating_point(
            op
        )

        self.assertEqual(
            MOD.selected_timing_bounds(
                op,
                "KFALL",
            ),
            (
                5.0,
                15.0,
            ),
        )

        self.assertEqual(
            MOD.selected_timing_bounds(
                op,
                "UNIVRFALL",
            ),
            (
                -0.5,
                20.5,
            ),
        )

    def test_no_calibration_selection_calls_exist(
        self,
    ):
        source = (
            MODULE_PATH
            .read_text()
        )

        tree = ast.parse(
            source
        )

        called = set()

        for node in ast.walk(
            tree
        ):
            if not isinstance(
                node,
                ast.Call,
            ):
                continue

            if isinstance(
                node.func,
                ast.Name,
            ):
                called.add(
                    node.func.id
                )

            elif isinstance(
                node.func,
                ast.Attribute,
            ):
                called.add(
                    node.func.attr
                )

        forbidden = {
            "select_channel_freeze_candidate",
            "select_timing_candidate",
            "build_channel_freeze_candidates",
            "build_timing_candidates",
            "evaluate_corruptions",
            "evaluate_clean_feasibility",
        }

        self.assertTrue(
            called.isdisjoint(
                forbidden
            ),
            sorted(
                called
                & forbidden
            ),
        )

    def test_frozen_timing_remains_observation_only(
        self,
    ):
        op = MOD.load_json(
            MOD.OPERATING_POINT_PATH
        )

        protocol = MOD.load_json(
            MOD.PROTOCOL_PATH
        )

        stream = MOD.CAL.P0Stream(
            values=np.zeros(
                (
                    3,
                    6,
                ),
                dtype=np.float64,
            ),
            timestamps=np.array(
                [
                    0.0,
                    0.010,
                    0.030,
                ],
                dtype=np.float64,
            ),
            counters=np.array(
                [
                    1,
                    2,
                    3,
                ],
                dtype=np.int64,
            ),
            source_id=
                "TEST_KFALL_TIMING",
        )

        evidence = (
            MOD
            .evaluate_frozen_timing_observation(
                stream,
                "KFALL",
                anchor_index=2,
                operating_point=op,
                protocol=protocol,
            )
        )

        self.assertIsNotNone(
            evidence
        )

        self.assertIs(
            evidence.status,
            MOD.CAL.EvidenceStatus.OBSERVATION_ONLY,
        )

        self.assertFalse(
            MOD.CAL.assess_evidence(
                [
                    evidence
                ]
            ).has_hard_alert
        )

    def test_kfall_gap_hard_univr_not_hard(
        self,
    ):
        values = np.zeros(
            (
                3,
                6,
            ),
            dtype=np.float64,
        )

        kfall = MOD.CAL.P0Stream(
            values=values,
            timestamps=np.array(
                [
                    0.0,
                    0.01,
                    0.02,
                ]
            ),
            counters=np.array(
                [
                    1,
                    2,
                    4,
                ],
                dtype=np.int64,
            ),
            source_id=
                "TEST_KFALL",
        )

        univr = MOD.CAL.P0Stream(
            values=values,
            timestamps=np.array(
                [
                    0.0,
                    10.0,
                    20.0,
                ]
            ),
            counters=None,
            source_id=
                "TEST_UNIVR",
        )

        kfall_result = (
            MOD.CAL.evaluate_frame_gap_event(
                "KFALL",
                kfall,
                corrupt_anchor_index=2,
            )
        )

        univr_result = (
            MOD.CAL.evaluate_frame_gap_event(
                "UNIVRFALL",
                univr,
                corrupt_anchor_index=2,
            )
        )

        self.assertTrue(
            kfall_result[
                "detected"
            ]
        )

        self.assertTrue(
            kfall_result[
                "hard_qualified"
            ]
        )

        self.assertFalse(
            univr_result[
                "detected"
            ]
        )

        self.assertFalse(
            univr_result[
                "hard_qualified"
            ]
        )

    def test_inactive_family_has_no_recall_claim(
        self,
    ):
        row = MOD.inactive_event_summary(
            123,
            runtime_role=
                "NO_HARD_DETECTOR_CONFIGURED",
            reason=
                "TEST_REASON",
        )

        self.assertEqual(
            row[
                "episode_count"
            ],
            123,
        )

        self.assertEqual(
            row[
                "detected_count"
            ],
            0,
        )

        self.assertIsNone(
            row[
                "event_detection_recall"
            ]
        )

        self.assertFalse(
            row[
                "runtime_active"
            ]
        )

    def test_not_admissible_accounting_excluded(
        self,
    ):
        manifest = MOD.load_json(
            MOD.FINAL_MANIFEST_PATH
        )

        accounting = (
            MOD
            .summarize_attempt_accounting(
                manifest
            )
        )

        self.assertEqual(
            accounting[
                "attempt_count"
            ],
            16620,
        )

        self.assertEqual(
            accounting[
                "admissible_count"
            ],
            15806,
        )

        self.assertEqual(
            accounting[
                "not_admissible_count"
            ],
            814,
        )

        self.assertTrue(
            accounting[
                "not_admissible_excluded_from_detection_denominator"
            ]
        )

    def test_final_evaluator_tag_name(
        self,
    ):
        self.assertEqual(
            MOD.FINAL_EVALUATOR_TAG,
            "integrity-final-test-evaluator-v1",
        )


if __name__ == "__main__":
    unittest.main()
