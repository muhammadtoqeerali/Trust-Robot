from __future__ import annotations

import ast
import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(
    __file__
).resolve().parents[1]

BENCHMARK = (
    ROOT
    / "experiments/04_runtime/"
      "benchmark_runtime_resource_overhead_v1.py"
)

RESULT = (
    ROOT
    / "results/raw/"
      "runtime_resource_overhead_v1_candidate.json"
)


SPEC = importlib.util.spec_from_file_location(
    "benchmark_runtime_resource_overhead_v1",
    BENCHMARK,
)

if (
    SPEC is None
    or SPEC.loader is None
):
    raise RuntimeError(
        "Unable to import resource benchmark"
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


class RuntimeResourceOverheadBenchmarkV1Tests(
    unittest.TestCase
):

    def test_protocol_and_runtime_anchors(
        self,
    ):
        protocol = MOD.verify_protocol()

        self.assertEqual(
            protocol[
                "protocol_id"
            ],
            "RUNTIME_RESOURCE_OVERHEAD_PROTOCOL_V1",
        )

        MOD.verify_frozen_source_anchors()

    def test_result_absent_before_measurement(
        self,
    ):
        self.assertFalse(
            RESULT.exists()
        )

    def test_exact_measurement_counts(
        self,
    ):
        self.assertEqual(
            MOD.WARMUP_ITERATIONS,
            500,
        )

        self.assertEqual(
            MOD.MEASUREMENT_BLOCKS,
            7,
        )

        self.assertEqual(
            MOD.ITERATIONS_PER_BLOCK,
            1000,
        )

        self.assertEqual(
            MOD.TOTAL_MEASURED_CALLS_PER_VARIANT,
            7000,
        )

    def test_exact_synthetic_window_source(
        self,
    ):
        source = BENCHMARK.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "torch.linspace(",
            source,
        )

        self.assertIn(
            "-1.0",
            source,
        )

        self.assertIn(
            "steps=360",
            source,
        )

        self.assertIn(
            "1,\n        40,\n        9,",
            source,
        )

    def test_no_dataset_array_loading(
        self,
    ):
        source = BENCHMARK.read_text(
            encoding="utf-8"
        )

        self.assertNotIn(
            "np.load(",
            source,
        )

        self.assertNotIn(
            "numpy.load(",
            source,
        )

        self.assertNotIn(
            "segments.npy",
            source,
        )

        self.assertNotIn(
            "labels.npy",
            source,
        )

    def test_no_direct_checkpoint_deserialization(
        self,
    ):
        source = BENCHMARK.read_text(
            encoding="utf-8"
        )

        self.assertNotIn(
            "torch.load(",
            source,
        )

        self.assertIn(
            "module.load_protected_model()",
            source,
        )

    def test_no_forward_with_features(
        self,
    ):
        source = BENCHMARK.read_text(
            encoding="utf-8"
        )

        self.assertNotIn(
            "forward_with_features",
            source,
        )

    def test_task_only_contains_one_model_call_site(
        self,
    ):
        source = BENCHMARK.read_text(
            encoding="utf-8"
        )

        tree = ast.parse(
            source
        )

        target = None

        for node in ast.walk(
            tree
        ):
            if (
                isinstance(
                    node,
                    ast.FunctionDef,
                )
                and node.name
                == "task_only"
            ):
                target = node
                break

        self.assertIsNotNone(
            target
        )

        calls = []

        for node in ast.walk(
            target
        ):
            if (
                isinstance(
                    node,
                    ast.Call,
                )
                and isinstance(
                    node.func,
                    ast.Name,
                )
                and node.func.id
                == "model"
            ):
                calls.append(
                    node
                )

        self.assertEqual(
            len(
                calls
            ),
            1,
        )

    def test_integrated_uses_frozen_runtime_wrapper(
        self,
    ):
        source = BENCHMARK.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "run_reliability_window(",
            source,
        )

    def test_post_logit_variants_have_no_model_forward(
        self,
    ):
        source = BENCHMARK.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "post_logit_valid",
            source,
        )

        self.assertIn(
            "post_logit_ood_unknown",
            source,
        )

        self.assertIn(
            "post_logit_integrity_alert",
            source,
        )

    def test_negative_increment_not_clamped(
        self,
    ):
        source = BENCHMARK.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "integrated_summary[\n            \"median_ns\"\n        ]\n        - task_summary[",
            source,
        )

        self.assertNotIn(
            "max(\n            0",
            source,
        )

    def test_memory_measurement_is_host_only(
        self,
    ):
        source = BENCHMARK.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "tracemalloc",
            source,
        )

        self.assertIn(
            "resource.getrusage",
            source,
        )

        self.assertIn(
            '"tracemalloc_bytes_are_stm32_ram":\n                False',
            source,
        )

    def test_embedded_claims_explicitly_false(
        self,
    ):
        source = BENCHMARK.read_text(
            encoding="utf-8"
        )

        for term in (
            "stm32f722_latency_claimed",
            "stm32f722_cycle_count_claimed",
            "stm32f722_flash_overhead_claimed",
            "stm32f722_ram_overhead_claimed",
            "stm32f722_energy_overhead_claimed",
        ):
            self.assertIn(
                term,
                source,
            )

    def test_result_builder_keeps_operating_points_immutable(
        self,
    ):
        source = BENCHMARK.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            '"ood_threshold_modified":\n                False',
            source,
        )

        self.assertIn(
            '"ood_method_modified":\n                False',
            source,
        )

        self.assertIn(
            '"integrity_operating_point_modified":\n                False',
            source,
        )

        self.assertIn(
            '"resource_result_used_for_scientific_selection":\n                False',
            source,
        )

    def test_import_does_not_run_measurement(
        self,
    ):
        self.assertFalse(
            RESULT.exists()
        )


if __name__ == "__main__":
    unittest.main()
