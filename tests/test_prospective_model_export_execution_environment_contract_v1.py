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

BUILDER = (
    ROOT
    / "experiments/05_embedded/"
      "build_model_export_execution_environment_contract_v1.py"
)

BLOCKER = (
    ROOT
    / "data/manifests/"
      "prospective_model_export_dependency_blocker_v1.json"
)

CONTRACT = (
    ROOT
    / "configs/embedded/"
      "prospective_model_export_execution_environment_contract_v1.json"
)


SPEC = importlib.util.spec_from_file_location(
    "build_model_export_execution_environment_contract_v1",
    BUILDER,
)

if SPEC is None or SPEC.loader is None:
    raise RuntimeError(
        "Unable to import execution-environment builder"
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


def verify_content(
    data,
):
    payload = deepcopy(
        data
    )

    stored = payload.pop(
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

    return (
        stored,
        computed,
    )


class ProspectiveModelExportExecutionEnvironmentContractV1Tests(
    unittest.TestCase
):

    @classmethod
    def setUpClass(
        cls,
    ):
        cls.blocker = json.loads(
            BLOCKER.read_text()
        )

        cls.contract = json.loads(
            CONTRACT.read_text()
        )

    def test_git_anchors(
        self,
    ):
        MOD.verify_git_anchors()

    def test_frozen_inputs(
        self,
    ):
        MOD.verify_frozen_inputs()

    def test_export_outputs_still_absent(
        self,
    ):
        MOD.verify_export_outputs_absent()

    def test_live_environment_snapshot_matches_blocker(
        self,
    ):
        records = (
            MOD.environment_snapshot()
        )

        MOD.validate_current_blocker(
            records
        )

    def test_blocker_hash(
        self,
    ):
        stored, computed = verify_content(
            self.blocker
        )

        self.assertEqual(
            stored,
            computed,
        )

    def test_contract_hash(
        self,
    ):
        stored, computed = verify_content(
            self.contract
        )

        self.assertEqual(
            stored,
            computed,
        )

    def test_three_known_interpreters(
        self,
    ):
        self.assertEqual(
            self.blocker[
                "observed_interpreter_count"
            ],
            3,
        )

    def test_no_qualifying_environment(
        self,
    ):
        self.assertEqual(
            self.blocker[
                "qualifying_environment_count"
            ],
            0,
        )

        self.assertEqual(
            self.blocker[
                "status"
            ],
            "active",
        )

    def test_export_execution_blocked(
        self,
    ):
        effect = self.blocker[
            "effect"
        ]

        self.assertFalse(
            effect[
                "exporter_execution_allowed"
            ]
        )

        self.assertFalse(
            effect[
                "checkpoint_deserialization_allowed"
            ]
        )

        self.assertFalse(
            effect[
                "model_forward_allowed"
            ]
        )

        self.assertFalse(
            effect[
                "onnx_export_allowed"
            ]
        )

    def test_single_environment_required(
        self,
    ):
        capabilities = self.contract[
            "required_execution_capabilities"
        ]

        self.assertTrue(
            capabilities[
                "single_python_interpreter"
            ]
        )

        self.assertTrue(
            capabilities[
                "all_required_modules_from_same_interpreter_environment"
            ]
        )

        self.assertFalse(
            capabilities[
                "cross_environment_package_mixing_allowed"
            ]
        )

    def test_required_modules_exact(
        self,
    ):
        self.assertEqual(
            self.blocker[
                "required_modules"
            ],
            [
                "torch",
                "onnx",
                "onnxruntime",
            ],
        )

    def test_cpu_execution_provider_required(
        self,
    ):
        self.assertTrue(
            self.contract[
                "required_execution_capabilities"
            ][
                "onnxruntime_cpu_execution_provider_required"
            ]
        )

    def test_qualification_before_export_required(
        self,
    ):
        qualification = self.contract[
            "environment_qualification_before_first_export"
        ]

        self.assertTrue(
            qualification[
                "required"
            ]
        )

        self.assertTrue(
            qualification[
                "must_freeze_before_exporter_execution"
            ]
        )

        self.assertFalse(
            qualification[
                "checkpoint_deserialization_during_qualification"
            ]
        )

        self.assertFalse(
            qualification[
                "model_forward_during_qualification"
            ]
        )

        self.assertFalse(
            qualification[
                "onnx_export_during_qualification"
            ]
        )

    def test_no_environment_selected(
        self,
    ):
        selection = self.contract[
            "current_environment_selection"
        ]

        self.assertIsNone(
            selection[
                "selected_interpreter"
            ]
        )

        self.assertFalse(
            selection[
                "selected_environment_qualified"
            ]
        )

    def test_no_environment_mutation_policy(
        self,
    ):
        policy = self.contract[
            "package_and_environment_policy"
        ]

        for key in (
            "install_packages_as_part_of_this_contract",
            "modify_protechto311",
            "modify_miniforge_base",
            "modify_opensim_scripting",
            "copy_packages_between_environments",
            "inject_foreign_site_packages",
            "silently_change_python_interpreter",
        ):
            self.assertFalse(
                policy[
                    key
                ]
            )

    def test_export_semantics_unchanged(
        self,
    ):
        frozen = self.contract[
            "frozen_export_semantics"
        ]

        self.assertEqual(
            frozen[
                "format"
            ],
            "ONNX",
        )

        self.assertEqual(
            frozen[
                "precision"
            ],
            "float32",
        )

        self.assertEqual(
            frozen[
                "opset_version"
            ],
            13,
        )

        self.assertEqual(
            frozen[
                "input_shape"
            ],
            [1, 40, 9],
        )

        self.assertEqual(
            frozen[
                "output_shape"
            ],
            [1, 2],
        )

        self.assertEqual(
            frozen[
                "parity_vector_count"
            ],
            68,
        )

        self.assertEqual(
            frozen[
                "absolute_tolerance"
            ],
            1.0e-5,
        )

        self.assertEqual(
            frozen[
                "relative_tolerance"
            ],
            1.0e-5,
        )

        self.assertEqual(
            frozen[
                "decision_mismatch_tolerance"
            ],
            0,
        )

        self.assertEqual(
            frozen[
                "ood_threshold"
            ],
            0.00914505124092102,
        )

    def test_no_stm32_claim(
        self,
    ):
        claims = self.contract[
            "claim_boundary"
        ]

        for key in (
            "export_executed",
            "prospective_onnx_validated",
            "stm32_importability_claimed",
            "stm32_numerical_parity_claimed",
            "stm32_latency_claimed",
            "stm32_flash_claimed",
            "stm32_ram_claimed",
        ):
            self.assertFalse(
                claims[
                    key
                ]
            )


if __name__ == "__main__":
    unittest.main()
