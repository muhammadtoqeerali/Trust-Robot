from hashlib import sha256
from pathlib import Path
import json
import unittest

from trust_robot.corruption import (
    CorruptionSpec,
)
from trust_robot.corruption_selection import (
    CorruptionSelectionError,
    CorruptionSelectionRecord,
    MagnitudeSelectionSource,
    TargetSelectionSource,
    bind_spec_to_selection,
)


ROOT = Path(__file__).resolve().parents[2]

POLICY = (
    ROOT
    / "configs/trust_robot/"
      "phase3_corruption_selection_policy_v1.json"
)

GAP = (
    ROOT
    / "configs/trust_robot/"
      "phase3_lidar_event_gap_real_smoke_v1.json"
)


def policy():
    return json.loads(
        POLICY.read_text(
            encoding="utf-8"
        )
    )


def gap():
    return json.loads(
        GAP.read_text(
            encoding="utf-8"
        )
    )


def real_gap_selection():
    binding = policy()[
        "existing_real_smoke_binding"
    ]

    return CorruptionSelectionRecord(
        plan_name=
            "phase3_lidar_event_gap_real_smoke_v1",

        target_selection_source=
            binding[
                "target_selection_source"
            ],

        target_selection_rationale=
            binding[
                "target_selection_rationale"
            ],

        magnitude_selection_source=
            binding[
                "magnitude_selection_source"
            ],

        magnitude_selection_rationale=
            binding[
                "magnitude_selection_rationale"
            ],

        selection_locked_before_execution=
            binding[
                "selection_locked_before_execution"
            ],

        estimator_output_used=
            binding[
                "estimator_output_used"
            ],

        registration_diagnostic_used=
            binding[
                "registration_diagnostic_used"
            ],

        reference_data_used=
            binding[
                "reference_data_used"
            ],

        validation_metric_used=
            binding[
                "validation_metric_used"
            ],

        confirmation_test_used=
            binding[
                "confirmation_test_used"
            ],

        source_artifacts=(
            str(
                GAP
            ),
        ),
    )


class Phase3CorruptionSelectionPolicyTests(
    unittest.TestCase
):
    def test_01_policy_content_hash_is_valid(self):
        payload = policy()

        stored = payload.pop(
            "content_sha256"
        )

        actual = sha256(
            json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            ).encode(
                "utf-8"
            )
        ).hexdigest()

        self.assertEqual(
            stored,
            actual,
        )

    def test_02_allowed_target_sources_are_explicit(self):
        self.assertEqual(
            set(
                policy()[
                    "allowed_target_selection_sources"
                ]
            ),
            {
                item.value
                for item
                in TargetSelectionSource
            },
        )

    def test_03_allowed_magnitude_sources_are_explicit(self):
        self.assertEqual(
            set(
                policy()[
                    "allowed_magnitude_selection_sources"
                ]
            ),
            {
                item.value
                for item
                in MagnitudeSelectionSource
            },
        )

    def test_04_policy_forbids_performance_selection(self):
        parameter_policy = policy()[
            "parameter_policy"
        ]

        self.assertFalse(
            parameter_policy[
                "performance_based_corruption_selection_allowed"
            ]
        )

        self.assertFalse(
            parameter_policy[
                "validation_metric_may_select_corruption_conditions"
            ]
        )

        self.assertFalse(
            parameter_policy[
                "confirmation_test_may_select_corruption_conditions"
            ]
        )

    def test_05_unlocked_selection_is_rejected(self):
        with self.assertRaises(
            CorruptionSelectionError
        ):
            CorruptionSelectionRecord(
                plan_name="bad",
                target_selection_source=
                    "explicit_pre_execution_literal",
                target_selection_rationale=
                    "declared target",
                magnitude_selection_source=
                    "explicit_pre_execution_literal",
                magnitude_selection_rationale=
                    "declared magnitude",
                selection_locked_before_execution=False,
            )

    def test_06_estimator_output_selection_is_rejected(self):
        with self.assertRaises(
            CorruptionSelectionError
        ):
            CorruptionSelectionRecord(
                plan_name="bad",
                target_selection_source=
                    "explicit_pre_execution_literal",
                target_selection_rationale=
                    "declared target",
                magnitude_selection_source=
                    "explicit_pre_execution_literal",
                magnitude_selection_rationale=
                    "declared magnitude",
                estimator_output_used=True,
            )

    def test_07_reference_and_confirmation_selection_are_rejected(self):
        for key in (
            "reference_data_used",
            "confirmation_test_used",
            "validation_metric_used",
            "registration_diagnostic_used",
            "ground_truth_metric_used",
        ):
            kwargs = {
                "plan_name":
                    "bad",

                "target_selection_source":
                    "explicit_pre_execution_literal",

                "target_selection_rationale":
                    "declared target",

                "magnitude_selection_source":
                    "explicit_pre_execution_literal",

                "magnitude_selection_rationale":
                    "declared magnitude",

                key:
                    True,
            }

            with self.subTest(
                key=key
            ):
                with self.assertRaises(
                    CorruptionSelectionError
                ):
                    CorruptionSelectionRecord(
                        **kwargs
                    )

    def test_08_selection_identity_is_deterministic(self):
        first = real_gap_selection()
        second = real_gap_selection()

        self.assertEqual(
            first.selection_id,
            second.selection_id,
        )

        self.assertTrue(
            first.selection_id.startswith(
                "TRC_SEL_"
            )
        )

    def test_09_existing_gap_binding_matches_exact_file(self):
        payload = policy()[
            "existing_real_smoke_binding"
        ]

        self.assertEqual(
            payload[
                "config_file_sha256"
            ],
            sha256(
                GAP.read_bytes()
            ).hexdigest(),
        )

        self.assertEqual(
            payload[
                "config_content_sha256"
            ],
            gap()[
                "content_sha256"
            ],
        )

    def test_10_existing_gap_selection_is_nonperformance_based(self):
        record = real_gap_selection()

        self.assertFalse(
            record.estimator_output_used
        )

        self.assertFalse(
            record.registration_diagnostic_used
        )

        self.assertFalse(
            record.reference_data_used
        )

        self.assertFalse(
            record.validation_metric_used
        )

        self.assertFalse(
            record.confirmation_test_used
        )

    def test_11_existing_gap_spec_binds_to_selection_record(self):
        spec = CorruptionSpec(
            **gap()[
                "corruption_spec"
            ]
        )

        binding = bind_spec_to_selection(
            spec,
            real_gap_selection(),
        )

        self.assertEqual(
            binding[
                "spec_id"
            ],
            "TRC_SPEC_d7fdcb5f67999476d8f0391d",
        )

        self.assertEqual(
            binding[
                "spec"
            ][
                "start_index"
            ],
            1,
        )

        self.assertEqual(
            binding[
                "spec"
            ][
                "length"
            ],
            1,
        )

    def test_12_binding_never_authorizes_evaluation_or_scoring(self):
        binding = bind_spec_to_selection(
            CorruptionSpec(
                **gap()[
                    "corruption_spec"
                ]
            ),
            real_gap_selection(),
        )

        authorization = binding[
            "execution_authorization"
        ]

        self.assertFalse(
            authorization[
                "missing_parameter_default_allowed"
            ]
        )

        self.assertFalse(
            authorization[
                "engine_parameter_selection_allowed"
            ]
        )

        self.assertFalse(
            authorization[
                "output_driven_spec_modification_allowed"
            ]
        )

        scope = binding[
            "scientific_scope"
        ]

        self.assertFalse(
            scope[
                "ate_or_rpe_authorized"
            ]
        )

        self.assertFalse(
            scope[
                "estimator_scoring_authorized"
            ]
        )


if __name__ == "__main__":
    unittest.main()
