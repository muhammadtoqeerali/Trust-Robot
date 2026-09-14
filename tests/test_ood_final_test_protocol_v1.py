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
      "build_ood_final_test_protocol_v1.py"
)

SPEC = importlib.util.spec_from_file_location(
    "build_ood_final_test_protocol_v1",
    MODULE_PATH,
)

if (
    SPEC is None
    or SPEC.loader is None
):
    raise RuntimeError(
        "Unable to import final-test OOD protocol builder"
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


class OODFinalTestProtocolV1Tests(
    unittest.TestCase
):

    def test_frozen_anchors(
        self,
    ):
        MOD.verify_frozen_anchors()

    def test_exact_final_population(
        self,
    ):
        rows = MOD.final_registry_rows()

        self.assertEqual(
            len(rows),
            1116,
        )

        self.assertEqual(
            sum(
                int(
                    row[
                        "historical_windows"
                    ]
                )
                for row in rows
            ),
            366507,
        )

    def test_exact_dataset_denominators(
        self,
    ):
        protocol = MOD.build_protocol()

        population = protocol[
            "protected_final_test_population"
        ]

        self.assertEqual(
            population[
                "dataset_trial_rows"
            ],
            {
                "KFALL":
                    932,

                "UNIVRFALL":
                    176,

                "ONFIELD":
                    8,
            },
        )

        self.assertEqual(
            population[
                "dataset_historical_windows"
            ],
            {
                "KFALL":
                    27068,

                "UNIVRFALL":
                    7532,

                "ONFIELD":
                    331907,
            },
        )

    def test_frozen_threshold_and_method(
        self,
    ):
        protocol = MOD.build_protocol()

        op = protocol[
            "frozen_ood_operating_point"
        ]

        self.assertEqual(
            op[
                "selected_method"
            ],
            "top_two_logit_margin",
        )

        self.assertEqual(
            op[
                "threshold"
            ],
            0.00914505124092102,
        )

        self.assertFalse(
            op[
                "threshold_may_change"
            ]
        )

        self.assertFalse(
            op[
                "method_may_change"
            ]
        )

    def test_single_forward_runtime_contract(
        self,
    ):
        protocol = MOD.build_protocol()

        runtime = protocol[
            "runtime_contract"
        ]

        self.assertEqual(
            runtime[
                "task_model_forwards_per_window"
            ],
            1,
        )

        self.assertFalse(
            runtime[
                "second_full_task_forward_allowed"
            ]
        )

        self.assertFalse(
            runtime[
                "feature_vector_used_by_selected_ood_score"
            ]
        )

        self.assertFalse(
            runtime[
                "classifier_bypass_enabled"
            ]
        )

    def test_no_true_ood_metric_claims(
        self,
    ):
        protocol = MOD.build_protocol()

        outputs = protocol[
            "predeclared_final_outputs"
        ]

        self.assertFalse(
            outputs[
                "true_ood_auroc_allowed"
            ]
        )

        self.assertFalse(
            outputs[
                "true_ood_recall_allowed"
            ]
        )

        self.assertFalse(
            outputs[
                "tnr_at_tpr_allowed"
            ]
        )

        self.assertFalse(
            outputs[
                "method_comparison_allowed"
            ]
        )

    def test_final_interpretation_boundary(
        self,
    ):
        protocol = MOD.build_protocol()

        interpretation = protocol[
            "scientific_interpretation"
        ]

        self.assertEqual(
            interpretation[
                "population_role"
            ],
            "protected_historical_ID_generalization_evaluation",
        )

        self.assertFalse(
            interpretation[
                "true_ood_positive_population_present"
            ]
        )

        self.assertFalse(
            interpretation[
                "extra_recordings_used"
            ]
        )

    def test_score_blind_exposure_boundary(
        self,
    ):
        protocol = MOD.build_protocol()

        boundary = protocol[
            "exposure_boundary_at_protocol_freeze"
        ]

        self.assertTrue(
            boundary[
                "final_test_registry_metadata_read"
            ]
        )

        for key in (
            "final_test_sensor_arrays_opened",
            "final_test_label_arrays_opened",
            "checkpoint_deserialized_for_final_test_ood",
            "protected_model_loaded_for_final_test_ood",
            "protected_model_forward_executed_for_final_test_ood",
            "final_test_task_logits_read",
            "final_test_features_read",
            "final_test_ood_margins_computed",
            "final_test_ood_states_computed",
            "final_test_ood_outputs_read",
        ):
            self.assertFalse(
                boundary[
                    key
                ]
            )

    def test_output_artifacts_absent(
        self,
    ):
        self.assertFalse(
            MOD.FINAL_RESULT.exists()
        )

        self.assertFalse(
            MOD.FINAL_RECEIPT.exists()
        )

        self.assertFalse(
            MOD.FINAL_EVALUATOR.exists()
        )

    def test_content_hash_roundtrip(
        self,
    ):
        protocol = MOD.build_protocol()

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
