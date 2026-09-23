from dataclasses import FrozenInstanceError
from hashlib import sha256
from pathlib import Path
import ast
import json
import unittest

from trust_robot.health_semantics import (
    HealthState,
)
from trust_robot.health_supervision import (
    HealthSupervisionContractError,
    HealthSupervisionSourceCandidate,
    build_empty_health_supervision_registry_manifest,
    validate_health_supervision_source_candidate,
)


ROOT = Path(__file__).resolve().parents[2]

CONFIG = (
    ROOT
    / "configs/trust_robot/"
      "phase5_health_supervision_protocol_candidate_v1.json"
)

MODULE = (
    ROOT
    / "src/trust_robot/health_supervision.py"
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


def candidate(**overrides):
    values = {
        "source_id":
            "UNIT_TEST_PROSPECTIVE_SOURCE",

        "modality":
            "lidar",

        "measurement_role":
            "range_observation_source",

        "source_kind":
            "explicit_independent_measurement_role_evidence",

        "evidence_description":
            (
                "Synthetic test-only evidence declaration used to "
                "validate the source protocol."
            ),

        "protocol_version":
            "UNIT_TEST_V1",

        "supported_states":
            (
                HealthState.HEALTHY,
                HealthState.DEGRADED,
                HealthState.UNUSABLE,
            ),

        "state_criteria":
            (
                (
                    HealthState.HEALTHY,
                    "Test-only nominal-role criterion.",
                ),
                (
                    HealthState.DEGRADED,
                    "Test-only impaired-but-usable criterion.",
                ),
                (
                    HealthState.UNUSABLE,
                    "Test-only unsuitable-for-role criterion.",
                ),
            ),

        "prospectively_declared":
            True,

        "measurement_role_grounded":
            True,

        "independent_of_final_estimator_scoring":
            True,

        "independent_of_confirmation_test":
            True,
    }

    values.update(overrides)

    return HealthSupervisionSourceCandidate(
        **values
    )


class Phase5HealthSupervisionProtocolTests(
    unittest.TestCase
):
    def test_01_config_content_digest_is_exact(self):
        payload = json.loads(
            CONFIG.read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(
            payload[
                "content_sha256"
            ],
            canonical_sha(
                payload
            ),
        )

    def test_02_empty_registry_is_deterministic(self):
        self.assertEqual(
            build_empty_health_supervision_registry_manifest(),
            build_empty_health_supervision_registry_manifest(),
        )

    def test_03_empty_registry_accepts_no_source_and_assigns_no_label(self):
        manifest = (
            build_empty_health_supervision_registry_manifest()
        )

        registry = manifest[
            "registry"
        ]

        self.assertEqual(
            registry[
                "accepted_source_count"
            ],
            0,
        )

        self.assertEqual(
            registry[
                "accepted_source_ids"
            ],
            [],
        )

        self.assertEqual(
            registry[
                "real_health_label_count"
            ],
            0,
        )

        self.assertFalse(
            registry[
                "real_dataset_health_labels_assigned"
            ]
        )

    def test_04_valid_candidate_shape_is_valid_but_not_registered(self):
        source = candidate()

        self.assertIs(
            validate_health_supervision_source_candidate(
                source
            ),
            source,
        )

        manifest = (
            build_empty_health_supervision_registry_manifest()
        )

        self.assertEqual(
            manifest[
                "registry"
            ][
                "accepted_source_count"
            ],
            0,
        )

    def test_05_candidate_is_immutable(self):
        source = candidate()

        with self.assertRaises(
            FrozenInstanceError
        ):
            source.source_id = "changed"

    def test_06_supported_states_must_not_be_empty(self):
        with self.assertRaises(
            HealthSupervisionContractError
        ):
            candidate(
                supported_states=(),
                state_criteria=(),
            )

    def test_07_supported_states_must_be_health_states(self):
        with self.assertRaises(
            HealthSupervisionContractError
        ):
            candidate(
                supported_states=(
                    "healthy",
                ),
                state_criteria=(
                    (
                        HealthState.HEALTHY,
                        "criterion",
                    ),
                ),
            )

    def test_08_duplicate_supported_state_is_rejected(self):
        with self.assertRaises(
            HealthSupervisionContractError
        ):
            candidate(
                supported_states=(
                    HealthState.HEALTHY,
                    HealthState.HEALTHY,
                ),
                state_criteria=(
                    (
                        HealthState.HEALTHY,
                        "criterion",
                    ),
                ),
            )

    def test_09_state_criteria_must_match_supported_states(self):
        with self.assertRaises(
            HealthSupervisionContractError
        ):
            candidate(
                supported_states=(
                    HealthState.HEALTHY,
                    HealthState.DEGRADED,
                ),
                state_criteria=(
                    (
                        HealthState.HEALTHY,
                        "criterion",
                    ),
                ),
            )

    def test_10_nonprospective_source_is_rejected(self):
        with self.assertRaises(
            HealthSupervisionContractError
        ):
            candidate(
                prospectively_declared=False
            )

    def test_11_measurement_role_ungrounded_source_is_rejected(self):
        with self.assertRaises(
            HealthSupervisionContractError
        ):
            candidate(
                measurement_role_grounded=False
            )

    def test_12_estimator_score_dependent_source_is_rejected(self):
        with self.assertRaises(
            HealthSupervisionContractError
        ):
            candidate(
                independent_of_final_estimator_scoring=False
            )

    def test_13_confirmation_dependent_source_is_rejected(self):
        with self.assertRaises(
            HealthSupervisionContractError
        ):
            candidate(
                independent_of_confirmation_test=False
            )

    def test_14_identity_or_diagnostic_only_sources_are_rejected(self):
        cases = (
            {
                "derived_only_from_clean_identity":
                    True,
            },
            {
                "derived_only_from_corruption_identity":
                    True,
            },
            {
                "derived_only_from_diagnostic_value_or_threshold":
                    True,
            },
        )

        for values in cases:
            with self.subTest(
                values=values
            ):
                with self.assertRaises(
                    HealthSupervisionContractError
                ):
                    candidate(
                        **values
                    )

    def test_15_reference_or_ate_rpe_sources_are_rejected(self):
        for key in (
            "uses_reference_trajectory_metric",
            "uses_ate_or_rpe",
        ):
            with self.subTest(
                key=key
            ):
                with self.assertRaises(
                    HealthSupervisionContractError
                ):
                    candidate(
                        **{
                            key:
                                True
                        }
                    )

    def test_16_historical_policy_or_self_supervision_is_rejected(self):
        for key in (
            "historical_imu_reliability_policy_adopted",
            "classifier_output_used_as_supervision",
            "numeric_diagnostic_threshold_selected",
        ):
            with self.subTest(
                key=key
            ):
                with self.assertRaises(
                    HealthSupervisionContractError
                ):
                    candidate(
                        **{
                            key:
                                True
                        }
                    )

    def test_17_candidate_fingerprint_and_provenance_shape_are_deterministic(self):
        first = candidate()
        second = candidate()

        self.assertEqual(
            first.fingerprint_sha256,
            second.fingerprint_sha256,
        )

        self.assertEqual(
            len(
                first.fingerprint_sha256
            ),
            64,
        )

        first_provenance = (
            first.to_provenance_shape()
        )

        second_provenance = (
            second.to_provenance_shape()
        )

        self.assertEqual(
            first_provenance.fingerprint_sha256,
            second_provenance.fingerprint_sha256,
        )

    def test_18_module_has_no_historical_ml_or_assignment_dependency(self):
        source = MODULE.read_text(
            encoding="utf-8"
        )

        tree = ast.parse(
            source,
            filename=str(
                MODULE
            ),
        )

        modules = []

        declarations = set()

        for node in ast.walk(tree):
            if isinstance(
                node,
                ast.Import,
            ):
                modules.extend(
                    alias.name
                    for alias
                    in node.names
                )

            elif isinstance(
                node,
                ast.ImportFrom,
            ):
                modules.append(
                    node.module
                    or ""
                )

        for node in tree.body:
            if isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                ),
            ):
                declarations.add(
                    node.name.lower()
                )

        for forbidden in (
            "imu_reliability",
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
                    for module
                    in modules
                ),
                (
                    forbidden,
                    modules,
                ),
            )

        for forbidden_api in (
            "assign_health_state",
            "classify",
            "predict",
            "fit",
            "train",
            "accept_supervision_source",
        ):
            self.assertNotIn(
                forbidden_api,
                declarations,
            )


if __name__ == "__main__":
    unittest.main()
