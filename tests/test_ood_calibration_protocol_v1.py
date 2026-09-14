from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from copy import deepcopy
from hashlib import sha256
from pathlib import Path


ROOT = Path(
    __file__
).resolve().parents[1]

MODULE_PATH = (
    ROOT
    / "experiments/03_ood/"
      "build_ood_calibration_protocol_v1.py"
)

SPEC = importlib.util.spec_from_file_location(
    "build_ood_calibration_protocol_v1",
    MODULE_PATH,
)

if (
    SPEC is None
    or SPEC.loader is None
):
    raise RuntimeError(
        "Unable to import OOD protocol builder"
    )

MOD = importlib.util.module_from_spec(
    SPEC
)

sys.modules[
    SPEC.name
] = MOD

SPEC.loader.exec_module(
    MOD
)


class OODCalibrationProtocolV1Tests(
    unittest.TestCase
):

    def test_expected_calibration_totals(
        self,
    ):
        self.assertEqual(
            sum(
                MOD.EXPECTED_CALIBRATION_WINDOWS.values()
            ),
            89868,
        )

        self.assertEqual(
            sum(
                row[
                    "n"
                ]
                for row
                in MOD.EXPECTED_CALIBRATION_STRATA
            ),
            89868,
        )

    def test_exact_nonempty_strata(
        self,
    ):
        observed = {
            (
                row[
                    "dataset"
                ],
                row[
                    "class"
                ],
            ):
                row[
                    "n"
                ]
            for row
            in MOD.EXPECTED_CALIBRATION_STRATA
        }

        self.assertEqual(
            observed,
            {
                (
                    "KFALL",
                    "Activity",
                ):
                    9342,

                (
                    "KFALL",
                    "Falling",
                ):
                    243,

                (
                    "UNIVRFALL",
                    "Activity",
                ):
                    5870,

                (
                    "UNIVRFALL",
                    "Falling",
                ):
                    81,

                (
                    "ONFIELD",
                    "Activity",
                ):
                    74332,
            },
        )

    def test_small_stratum_rank_is_zero(
        self,
    ):
        self.assertEqual(
            MOD.stratum_rank(
                81,
                0.01,
            ),
            0,
        )

        self.assertEqual(
            MOD.stratum_rank(
                243,
                0.01,
            ),
            2,
        )

    def test_global_threshold_is_minimum_boundary(
        self,
    ):
        strata = {
            "a":
                [
                    0.1,
                    0.2,
                    0.3,
                    0.4,
                ],

            "b":
                [
                    0.05,
                    0.6,
                    0.7,
                    0.8,
                ],
        }

        threshold = (
            MOD
            .finite_sample_global_threshold(
                strata,
                rejection_fraction=0.25,
            )
        )

        self.assertEqual(
            threshold,
            0.2,
        )

    def test_threshold_ties_are_accepted(
        self,
    ):
        margins = [
            0.1,
            0.2,
            0.2,
            0.3,
        ]

        self.assertEqual(
            MOD.empirical_acceptance(
                margins,
                0.2,
            ),
            0.75,
        )

    def test_finite_sample_acceptance_constraint(
        self,
    ):
        strata = {
            "s1":
                [
                    float(
                        value
                    )
                    for value
                    in range(
                        1,
                        101,
                    )
                ],

            "s2":
                [
                    float(
                        value
                    )
                    for value
                    in range(
                        50,
                        250,
                    )
                ],
        }

        threshold = (
            MOD
            .finite_sample_global_threshold(
                strata,
                rejection_fraction=0.01,
            )
        )

        for margins in strata.values():
            self.assertGreaterEqual(
                MOD.empirical_acceptance(
                    margins,
                    threshold,
                ),
                0.99,
            )

    def test_protocol_claim_boundary(
        self,
    ):
        protocol = (
            MOD
            .build_protocol()
        )

        self.assertEqual(
            protocol[
                "score"
            ][
                "selected_method"
            ],
            "top_two_logit_margin",
        )

        self.assertFalse(
            protocol[
                "score"
            ][
                "requires_second_task_model_forward"
            ]
        )

        self.assertFalse(
            protocol[
                "calibration_outputs_predeclared"
            ][
                "true_ood_detection_metrics_allowed"
            ]
        )

        self.assertFalse(
            protocol[
                "final_test_contract"
            ][
                "may_select_threshold"
            ]
        )

        self.assertFalse(
            protocol[
                "external_domain_shift_contract"
            ][
                "extra_recordings_used_for_calibration"
            ]
        )

    def test_protocol_content_hash_roundtrip(
        self,
    ):
        protocol = (
            MOD
            .build_protocol()
        )

        stored = protocol[
            "content_sha256"
        ]

        payload = deepcopy(
            protocol
        )

        payload.pop(
            "content_sha256"
        )

        normalized = json.loads(
            json.dumps(
                payload,
                separators=(",", ":"),
                allow_nan=False,
            )
        )

        computed = sha256(
            json.dumps(
                normalized,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode(
                "utf-8"
            )
        ).hexdigest()

        self.assertEqual(
            stored,
            computed,
        )


if __name__ == "__main__":
    unittest.main()
