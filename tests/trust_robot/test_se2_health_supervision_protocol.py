from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import ast
import json
import unittest

from trust_robot.health_supervision_resolution import (
    FROZEN_INPUT_SHA256,
    HEALTH_STATES,
    SE2_HEALTH_SUPERVISION_PROTOCOL_ID,
    SE2_HEALTH_SUPERVISION_SCHEMA,
    SE2HealthSupervisionProtocolError,
    assert_health_model_training_authorized,
    assert_se3_entry_authorized,
    build_se2_health_supervision_protocol_manifest,
    validate_se2_health_supervision_protocol_manifest,
)


ROOT = Path(__file__).resolve().parents[2]

CONFIG = (
    ROOT
    / "configs/trust_robot/se2_health_supervision_protocol_v1.json"
)

MODULE = (
    ROOT
    / "src/trust_robot/health_supervision_resolution.py"
)


def canonical_sha(payload):
    value = dict(payload)
    value.pop(
        "content_sha256",
        None,
    )

    return sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode(
            "utf-8"
        )
    ).hexdigest()


class SE2HealthSupervisionProtocolTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(
            CONFIG.read_text(
                encoding="utf-8"
            )
        )

    def test_01_schema_and_protocol_identity(self):
        self.assertEqual(
            self.payload["schema"],
            SE2_HEALTH_SUPERVISION_SCHEMA,
        )

        self.assertEqual(
            self.payload["protocol_id"],
            SE2_HEALTH_SUPERVISION_PROTOCOL_ID,
        )

        self.assertEqual(
            self.payload["schema_version"],
            1,
        )

    def test_02_content_digest_is_canonical(self):
        self.assertEqual(
            self.payload["content_sha256"],
            canonical_sha(
                self.payload
            ),
        )

    def test_03_builder_exactly_reproduces_config(self):
        self.assertEqual(
            self.payload,
            build_se2_health_supervision_protocol_manifest(),
        )

    def test_04_stage_identity_is_se2(self):
        stage = self.payload["stage"]

        self.assertEqual(
            stage["stage_id"],
            "SE2",
        )

        self.assertEqual(
            stage["stage_name"],
            "health_supervision_protocol",
        )

        self.assertEqual(
            stage["status"],
            "protocol_resolved_no_accepted_empirical_source_ready_for_SE3",
        )

    def test_05_state_vocabulary_is_exact(self):
        self.assertEqual(
            tuple(
                self.payload["state_vocabulary"]
            ),
            HEALTH_STATES,
        )

    def test_06_all_three_states_have_semantics(self):
        self.assertEqual(
            set(
                self.payload["state_semantics"]
            ),
            set(
                HEALTH_STATES
            ),
        )

        for state in HEALTH_STATES:
            self.assertTrue(
                self.payload[
                    "state_semantics"
                ][
                    state
                ].strip()
            )

    def test_07_supervision_must_be_prospective_and_role_grounded(self):
        admissible = self.payload[
            "admissible_supervision"
        ]

        self.assertTrue(
            admissible[
                "prospective_declaration_required"
            ]
        )

        self.assertTrue(
            admissible[
                "measurement_role_grounding_required"
            ]
        )

    def test_08_independent_baseline_and_intervention_are_required(self):
        admissible = self.payload[
            "admissible_supervision"
        ]

        self.assertTrue(
            admissible[
                "independent_baseline_nominality_required"
            ]
        )

        self.assertTrue(
            admissible[
                "independent_intervention_or_state_evidence_required"
            ]
        )

        self.assertTrue(
            admissible[
                "independent_measurement_relation_verification_required"
            ]
        )

    def test_09_candidate_validity_does_not_accept_source(self):
        self.assertFalse(
            self.payload[
                "admissible_supervision"
            ][
                "candidate_shape_validity_implies_source_acceptance"
            ]
        )

    def test_10_controlled_availability_mapping_is_prospective_only(self):
        mapping = self.payload[
            "controlled_availability_mapping"
        ]

        self.assertEqual(
            mapping["full"],
            "healthy",
        )

        self.assertEqual(
            mapping["partial"],
            "degraded",
        )

        self.assertEqual(
            mapping["absent"],
            "unusable",
        )

        self.assertTrue(
            mapping[
                "mapping_applies_only_after_source_acceptance"
            ]
        )

    def test_11_availability_is_not_health_label(self):
        mapping = self.payload[
            "controlled_availability_mapping"
        ]

        self.assertFalse(
            mapping[
                "availability_identity_alone_is_health_label"
            ]
        )

        self.assertFalse(
            mapping[
                "missing_measurement_encoded_as_zero_feature_vector"
            ]
        )

    def test_12_prohibited_label_bases_are_exact(self):
        prohibited = self.payload[
            "prohibited_label_basis"
        ]

        required = {
            "clean_dataset_identity_alone",
            "synthetic_corruption_identity_alone",
            "measurement_availability_identity_alone",
            "diagnostic_value_or_threshold_alone",
            "reference_trajectory_metric",
            "ate_or_rpe",
            "final_localization_error",
            "final_estimator_score",
            "confirmation_test_outcome",
            "classifier_output_as_own_supervision",
            "historical_imu_reliability_policy",
        }

        self.assertEqual(
            set(
                prohibited
            ),
            required,
        )

        self.assertTrue(
            all(
                prohibited.values()
            )
        )

    def test_13_current_source_and_label_counts_are_zero(self):
        readiness = self.payload[
            "current_empirical_readiness"
        ]

        self.assertEqual(
            readiness[
                "accepted_baseline_nominality_source_count"
            ],
            0,
        )

        self.assertEqual(
            readiness[
                "accepted_health_supervision_source_count"
            ],
            0,
        )

        self.assertEqual(
            readiness[
                "real_health_label_count"
            ],
            0,
        )

    def test_14_required_empirical_receipts_are_absent(self):
        readiness = self.payload[
            "current_empirical_readiness"
        ]

        for key in (
            "baseline_nominality_receipt_available",
            "controlled_intervention_receipt_available",
            "measurement_relation_verification_receipt_available",
        ):
            self.assertFalse(
                readiness[key]
            )

    def test_15_health_label_generation_remains_unauthorized(self):
        readiness = self.payload[
            "current_empirical_readiness"
        ]

        self.assertFalse(
            readiness[
                "health_label_generation_authorized"
            ]
        )

        self.assertFalse(
            readiness[
                "empirical_health_supervision_available"
            ]
        )

    def test_16_partition_access_is_train_only(self):
        access = self.payload[
            "partition_access"
        ]

        self.assertTrue(
            access[
                "train_authorized"
            ]
        )

        self.assertFalse(
            access[
                "validation_authorized"
            ]
        )

        self.assertFalse(
            access[
                "confirmation_authorized"
            ]
        )

        self.assertFalse(
            access[
                "reference_trajectory_authorized"
            ]
        )

        self.assertFalse(
            access[
                "cross_partition_supervision_allowed"
            ]
        )

    def test_17_no_training_selection_calibration_or_scoring_executed(self):
        execution = self.payload[
            "execution_boundary"
        ]

        for value in execution.values():
            self.assertFalse(
                value
            )

    def test_18_se3_is_authorized_train_only(self):
        transition = self.payload[
            "transition_policy"
        ]

        self.assertTrue(
            transition[
                "SE2_protocol_definition_resolved"
            ]
        )

        self.assertTrue(
            transition[
                "SE3_may_proceed"
            ]
        )

        self.assertTrue(
            transition[
                "SE3_train_access_only"
            ]
        )

        assert_se3_entry_authorized(
            self.payload
        )

    def test_19_se4_training_remains_blocked(self):
        transition = self.payload[
            "transition_policy"
        ]

        self.assertFalse(
            transition[
                "SE4_health_model_training_may_proceed"
            ]
        )

        with self.assertRaises(
            SE2HealthSupervisionProtocolError
        ):
            assert_health_model_training_authorized(
                self.payload
            )

    def test_20_validation_confirmation_and_se9_remain_closed(self):
        transition = self.payload[
            "transition_policy"
        ]

        self.assertTrue(
            transition[
                "validation_remains_closed"
            ]
        )

        self.assertTrue(
            transition[
                "confirmation_remains_closed"
            ]
        )

        self.assertTrue(
            transition[
                "SE9_remains_closed"
            ]
        )

    def test_21_frozen_input_bindings_are_exact(self):
        self.assertEqual(
            self.payload[
                "frozen_input_sha256"
            ],
            dict(
                FROZEN_INPUT_SHA256
            ),
        )

    def test_22_se1_freeze_binding_is_exact(self):
        self.assertEqual(
            self.payload[
                "frozen_input_sha256"
            ][
                "se1_freeze_manifest"
            ],
            "46224af94a07787883b9bd76e0df88cb43f60e834484add04b64933afdbafb02",
        )

    def test_23_validator_accepts_only_exact_frozen_manifest(self):
        self.assertIs(
            validate_se2_health_supervision_protocol_manifest(
                self.payload
            ),
            self.payload,
        )

        changed = deepcopy(
            self.payload
        )

        changed[
            "current_empirical_readiness"
        ][
            "real_health_label_count"
        ] = 1

        with self.assertRaises(
            SE2HealthSupervisionProtocolError
        ):
            validate_se2_health_supervision_protocol_manifest(
                changed
            )

    def test_24_validator_rejects_fake_source_acceptance(self):
        changed = deepcopy(
            self.payload
        )

        changed[
            "current_empirical_readiness"
        ][
            "accepted_health_supervision_source_count"
        ] = 1

        with self.assertRaises(
            SE2HealthSupervisionProtocolError
        ):
            validate_se2_health_supervision_protocol_manifest(
                changed
            )

    def test_25_module_has_no_ml_reference_or_evaluation_dependency(self):
        tree = ast.parse(
            MODULE.read_text(
                encoding="utf-8"
            ),
            filename=str(
                MODULE
            ),
        )

        modules = []

        for node in ast.walk(tree):
            if isinstance(
                node,
                ast.Import,
            ):
                modules.extend(
                    alias.name
                    for alias in node.names
                )

            elif isinstance(
                node,
                ast.ImportFrom,
            ):
                modules.append(
                    node.module
                    or ""
                )

        for forbidden in (
            "torch",
            "sklearn",
            "numpy",
            "evo",
            "evaluation",
            "reference",
        ):
            self.assertFalse(
                any(
                    forbidden
                    in module.lower()
                    for module in modules
                ),
                (
                    forbidden,
                    modules,
                ),
            )

    def test_26_module_exposes_no_label_assignment_or_training_api(self):
        tree = ast.parse(
            MODULE.read_text(
                encoding="utf-8"
            ),
            filename=str(
                MODULE
            ),
        )

        declarations = {
            node.name.lower()
            for node in tree.body
            if isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                ),
            )
        }

        for forbidden in (
            "assign_health_label",
            "assign_health_state",
            "fit",
            "train",
            "predict",
            "classify",
            "calibrate",
        ):
            self.assertNotIn(
                forbidden,
                declarations,
            )


if __name__ == "__main__":
    unittest.main()
