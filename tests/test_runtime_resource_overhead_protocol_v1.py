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
    / "experiments/04_runtime/"
      "build_runtime_resource_overhead_protocol_v1.py"
)

SPEC = importlib.util.spec_from_file_location(
    "build_runtime_resource_overhead_protocol_v1",
    MODULE_PATH,
)

if (
    SPEC is None
    or SPEC.loader is None
):
    raise RuntimeError(
        "Unable to import resource-overhead protocol builder"
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


class RuntimeResourceOverheadProtocolV1Tests(
    unittest.TestCase
):

    def test_frozen_anchors(
        self,
    ):
        MOD.verify_anchors()

    def test_measurement_not_started(
        self,
    ):
        MOD.verify_measurement_not_started()

    def test_synthetic_input_only(
        self,
    ):
        protocol = MOD.build_protocol()

        scope = protocol[
            "measurement_scope"
        ]

        self.assertEqual(
            scope[
                "input_source"
            ],
            "deterministic_synthetic_only",
        )

        self.assertFalse(
            scope[
                "protected_dataset_used"
            ]
        )

        self.assertFalse(
            scope[
                "final_test_dataset_used"
            ]
        )

    def test_exact_synthetic_window_shape(
        self,
    ):
        protocol = MOD.build_protocol()

        self.assertEqual(
            protocol[
                "measurement_scope"
            ][
                "window_shape"
            ],
            [
                1,
                40,
                9,
            ],
        )

    def test_task_only_and_integrated_each_one_forward(
        self,
    ):
        protocol = MOD.build_protocol()

        variants = protocol[
            "latency_protocol"
        ][
            "variants"
        ]

        self.assertEqual(
            variants[
                "task_only_reference"
            ][
                "full_task_model_calls_per_iteration"
            ],
            1,
        )

        self.assertEqual(
            variants[
                "integrated_reliability"
            ][
                "full_task_model_calls_per_iteration"
            ],
            1,
        )

    def test_fixed_measurement_counts(
        self,
    ):
        protocol = MOD.build_protocol()

        latency = protocol[
            "latency_protocol"
        ]

        self.assertEqual(
            latency[
                "warmup_iterations"
            ],
            500,
        )

        self.assertEqual(
            latency[
                "measurement_blocks"
            ],
            7,
        )

        self.assertEqual(
            latency[
                "measured_iterations_per_block"
            ],
            1000,
        )

        self.assertEqual(
            latency[
                "total_measured_calls_per_variant"
            ],
            7000,
        )

    def test_primary_increment_is_predeclared(
        self,
    ):
        protocol = MOD.build_protocol()

        latency = protocol[
            "latency_protocol"
        ]

        self.assertIn(
            "median_integrated_reliability_ns",
            latency[
                "primary_incremental_latency_definition"
            ],
        )

        self.assertIn(
            "median_task_only_reference_ns",
            latency[
                "primary_incremental_latency_definition"
            ],
        )

    def test_negative_increment_not_clamped(
        self,
    ):
        protocol = MOD.build_protocol()

        self.assertIn(
            "do_not_clamp_to_zero",
            protocol[
                "latency_protocol"
            ][
                "negative_measured_increment"
            ],
        )

    def test_post_logit_three_state_microbenchmarks(
        self,
    ):
        protocol = MOD.build_protocol()

        variants = protocol[
            "latency_protocol"
        ][
            "variants"
        ]

        for name in (
            "post_logit_valid",
            "post_logit_ood_unknown",
            "post_logit_integrity_alert",
        ):
            self.assertIn(
                name,
                variants,
            )

            self.assertEqual(
                variants[
                    name
                ][
                    "full_task_model_calls_per_iteration"
                ],
                0,
            )

    def test_no_statistical_reopening(
        self,
    ):
        protocol = MOD.build_protocol()

        scope = protocol[
            "measurement_scope"
        ]

        self.assertFalse(
            scope[
                "scientific_selection_allowed"
            ]
        )

        self.assertFalse(
            scope[
                "ood_threshold_may_change"
            ]
        )

        self.assertFalse(
            scope[
                "integrity_operating_point_may_change"
            ]
        )

    def test_no_stm32_claim_from_reference_host_protocol(
        self,
    ):
        protocol = MOD.build_protocol()

        boundary = protocol[
            "claim_boundary"
        ]

        forbidden = set(
            boundary[
                "not_allowed_from_this_protocol"
            ]
        )

        self.assertIn(
            "stm32f722_latency",
            forbidden,
        )

        self.assertIn(
            "stm32f722_flash_overhead",
            forbidden,
        )

        self.assertIn(
            "stm32f722_ram_overhead",
            forbidden,
        )

        self.assertTrue(
            boundary[
                "target_mcu_measurement_required_before_embedded_claims"
            ]
        )

    def test_python_source_bytes_not_flash(
        self,
    ):
        protocol = MOD.build_protocol()

        static = protocol[
            "static_footprint_protocol"
        ]

        self.assertFalse(
            static[
                "python_source_bytes_may_be_called_embedded_flash"
            ]
        )

        self.assertFalse(
            static[
                "python_source_bytes_may_be_called_mcu_code_size"
            ]
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
