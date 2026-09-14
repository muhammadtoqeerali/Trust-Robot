from __future__ import annotations

import gc
import importlib.util
import json
import os
import platform
import resource
import statistics
import sys
import time
import tracemalloc
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from typing import Callable

import numpy as np
import torch

from imu_reliability.baseline.historical_decision import (
    decision_from_logits,
)
from imu_reliability.integrity import (
    EvidenceStatus,
    IntegrityCause,
    IntegrityEvidence,
    assess_evidence,
)
from imu_reliability.runtime import (
    OOD_THRESHOLD,
    TrustState,
    decide_from_logits,
    run_reliability_window,
)


ROOT = Path(
    __file__
).resolve().parents[2]


PROTOCOL = (
    ROOT
    / "configs/runtime/"
      "runtime_resource_overhead_protocol_v1.json"
)

RESULT = (
    ROOT
    / "results/raw/"
      "runtime_resource_overhead_v1_candidate.json"
)

V1B = (
    ROOT
    / "experiments/03_ood/"
      "evaluate_ood_calibration_v1b.py"
)

CHECKPOINT = Path(
    "/mnt/hdd16T/protechto/checkpoints/CNN/400ms/"
    "2025-02-25_12_24_47/best-checkpoint.ckpt"
)


RESOURCE_PROTOCOL_TAG = (
    "runtime-resource-overhead-protocol-v1"
)

RESOURCE_PROTOCOL_COMMIT = (
    "1f0580763d227ab336528f9f412a18a2b66894e0"
)

REFERENCE_RUNTIME_TAG = (
    "runtime-reference-implementation-v1"
)

REFERENCE_RUNTIME_COMMIT = (
    "4755a74fe558021576934674e338865a36df5b55"
)

RUNTIME_CONTRACT_COMMIT = (
    "c2b7ae52b163afb33c828218e5c76f0686ad391a"
)


PROTOCOL_RAW_SHA256 = (
    "2063c44ba8108f1875e902fe112ee1c764155a347dbb2f9d6618cacfaaf9ba87"
)

PROTOCOL_CONTENT_SHA256 = (
    "f251abd253010c0694cd85b20eaf849f6d2751cac2f0e240ff78df4af9e1be9d"
)

V1B_RAW_SHA256 = (
    "6462829b7ffee3ca19dc25b7a605a3b7dd38ddf6bfb10a34ca8d098c0ae415df"
)

CHECKPOINT_SHA256 = (
    "ee7c0079bfb8555bff45c3077cc24eaa4373c57729045d92a831a1d7a3ea9bb1"
)

RUNTIME_INIT_SHA256 = (
    "f8b125ffb9e1c217bc2eb0c2aac197e64ca8cfc47d6f31ddf92068af575ef3e0"
)

RUNTIME_DECISION_SHA256 = (
    "00391737a5f2d167ded6e302031b2a354baf2eeb41ee3bc49a1f055e3a40e384"
)

RUNTIME_RELIABILITY_SHA256 = (
    "aa8fe189301c4dd2b67f501872d060a29e8e5e8e5cc518590e028a79068eda7b"
)


WARMUP_ITERATIONS = 500
MEASUREMENT_BLOCKS = 7
ITERATIONS_PER_BLOCK = 1000
TOTAL_MEASURED_CALLS_PER_VARIANT = 7000
MEMORY_ITERATIONS = 100

EXPECTED_WINDOW_SHAPE = (
    1,
    40,
    9,
)


def raw_sha256(
    path: Path,
) -> str:
    return sha256(
        path.read_bytes()
    ).hexdigest()


def canonical_digest(
    payload,
) -> str:
    normalized = json.loads(
        json.dumps(
            payload,
            separators=(",", ":"),
            allow_nan=False,
        )
    )

    return sha256(
        json.dumps(
            normalized,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def git(
    *args: str,
) -> str:
    import subprocess

    return subprocess.check_output(
        [
            "/usr/bin/git",
            *args,
        ],
        cwd=ROOT,
        text=True,
    ).strip()


def verify_protocol() -> dict:
    if raw_sha256(
        PROTOCOL
    ) != PROTOCOL_RAW_SHA256:
        raise RuntimeError(
            "Frozen resource protocol raw bytes changed"
        )

    data = json.loads(
        PROTOCOL.read_text()
    )

    payload = deepcopy(
        data
    )

    stored = payload.pop(
        "content_sha256"
    )

    computed = canonical_digest(
        payload
    )

    if not (
        stored
        == computed
        == PROTOCOL_CONTENT_SHA256
    ):
        raise RuntimeError(
            "Frozen resource protocol content changed"
        )

    if (
        data[
            "latency_protocol"
        ][
            "warmup_iterations"
        ]
        != WARMUP_ITERATIONS
    ):
        raise RuntimeError(
            "Warmup count changed"
        )

    if (
        data[
            "latency_protocol"
        ][
            "measurement_blocks"
        ]
        != MEASUREMENT_BLOCKS
    ):
        raise RuntimeError(
            "Measurement-block count changed"
        )

    if (
        data[
            "latency_protocol"
        ][
            "measured_iterations_per_block"
        ]
        != ITERATIONS_PER_BLOCK
    ):
        raise RuntimeError(
            "Iteration count changed"
        )

    if (
        data[
            "latency_protocol"
        ][
            "total_measured_calls_per_variant"
        ]
        != TOTAL_MEASURED_CALLS_PER_VARIANT
    ):
        raise RuntimeError(
            "Measured-call total changed"
        )

    if (
        data[
            "measurement_scope"
        ][
            "input_source"
        ]
        != "deterministic_synthetic_only"
    ):
        raise RuntimeError(
            "Input-source contract changed"
        )

    if (
        data[
            "measurement_scope"
        ][
            "protected_dataset_used"
        ]
        is not False
    ):
        raise RuntimeError(
            "Protected dataset unexpectedly allowed"
        )

    return data


def verify_frozen_source_anchors() -> None:
    refs = {
        (
            RESOURCE_PROTOCOL_TAG
            + "^{commit}"
        ):
            RESOURCE_PROTOCOL_COMMIT,

        (
            REFERENCE_RUNTIME_TAG
            + "^{commit}"
        ):
            REFERENCE_RUNTIME_COMMIT,

        "runtime-integration-contract-v1^{commit}":
            RUNTIME_CONTRACT_COMMIT,
    }

    for ref, expected in refs.items():
        observed = git(
            "rev-parse",
            ref,
        )

        if observed != expected:
            raise RuntimeError(
                f"Frozen ref moved: {ref}"
            )

    for ref in (
        RESOURCE_PROTOCOL_TAG,
        REFERENCE_RUNTIME_TAG,
        "runtime-integration-contract-v1",
    ):
        import subprocess

        rc = subprocess.run(
            [
                "/usr/bin/git",
                "merge-base",
                "--is-ancestor",
                ref,
                "HEAD",
            ],
            cwd=ROOT,
            check=False,
        ).returncode

        if rc != 0:
            raise RuntimeError(
                f"Frozen ref is not an ancestor: {ref}"
            )

    source_hashes = {
        (
            ROOT
            / "src/imu_reliability/runtime/"
              "__init__.py"
        ):
            RUNTIME_INIT_SHA256,

        (
            ROOT
            / "src/imu_reliability/runtime/"
              "decision.py"
        ):
            RUNTIME_DECISION_SHA256,

        (
            ROOT
            / "src/imu_reliability/runtime/"
              "reliability.py"
        ):
            RUNTIME_RELIABILITY_SHA256,

        V1B:
            V1B_RAW_SHA256,
    }

    for path, expected in source_hashes.items():
        observed = raw_sha256(
            path
        )

        if observed != expected:
            raise RuntimeError(
                f"Frozen source changed: {path}"
            )


def verify_checkpoint_hash() -> None:
    if not CHECKPOINT.is_file():
        raise RuntimeError(
            "Protected checkpoint is absent"
        )

    observed = raw_sha256(
        CHECKPOINT
    )

    if observed != CHECKPOINT_SHA256:
        raise RuntimeError(
            "Protected checkpoint hash changed"
        )


def load_protected_model():
    if raw_sha256(
        V1B
    ) != V1B_RAW_SHA256:
        raise RuntimeError(
            "Pinned V1b loader source changed"
        )

    spec = importlib.util.spec_from_file_location(
        "runtime_resource_v1b_loader",
        V1B,
    )

    if (
        spec is None
        or spec.loader is None
    ):
        raise RuntimeError(
            "Unable to load pinned V1b module"
        )

    module = importlib.util.module_from_spec(
        spec
    )

    sys.modules[
        spec.name
    ] = module

    spec.loader.exec_module(
        module
    )

    loaded = module.load_protected_model()

    if isinstance(
        loaded,
        torch.nn.Module,
    ):
        model = loaded

    elif (
        isinstance(
            loaded,
            tuple,
        )
        and len(
            loaded
        ) >= 1
        and isinstance(
            loaded[
                0
            ],
            torch.nn.Module,
        )
    ):
        model = loaded[
            0
        ]

    else:
        raise RuntimeError(
            "Pinned loader did not return a protected torch model"
        )

    model.eval()

    return model


def configure_host_runtime() -> None:
    torch.set_num_threads(
        1
    )

    try:
        torch.set_num_interop_threads(
            1
        )
    except RuntimeError:
        if torch.get_num_interop_threads() != 1:
            raise

    if torch.get_num_threads() != 1:
        raise RuntimeError(
            "Torch intra-op thread count is not one"
        )

    if torch.get_num_interop_threads() != 1:
        raise RuntimeError(
            "Torch inter-op thread count is not one"
        )


def synthetic_window() -> torch.Tensor:
    window = torch.linspace(
        -1.0,
        1.0,
        steps=360,
        dtype=torch.float32,
    ).reshape(
        1,
        40,
        9,
    )

    if tuple(
        window.shape
    ) != EXPECTED_WINDOW_SHAPE:
        raise RuntimeError(
            "Synthetic benchmark window shape changed"
        )

    return window


def empty_assessment():
    return assess_evidence(
        []
    )


def frame_gap_assessment():
    evidence = IntegrityEvidence(
        indicator="FRAME_COUNTER_GAP",
        status=EvidenceStatus.HARD_QUALIFIED,
        candidate_cause=IntegrityCause.FRAME_GAP,
        source="benchmark_preconstructed_qualified_frame_gap",
    )

    return assess_evidence(
        [
            evidence,
        ]
    )


def fixed_post_logit_inputs():
    valid_logits = torch.tensor(
        [
            [
                1.0,
                0.0,
            ],
        ],
        dtype=torch.float64,
    )

    unknown_logits = torch.tensor(
        [
            [
                0.0,
                0.0,
            ],
        ],
        dtype=torch.float64,
    )

    return {
        "post_logit_valid": (
            valid_logits,
            empty_assessment(),
            TrustState.VALID,
        ),

        "post_logit_ood_unknown": (
            unknown_logits,
            empty_assessment(),
            TrustState.OOD_UNKNOWN,
        ),

        "post_logit_integrity_alert": (
            unknown_logits,
            frame_gap_assessment(),
            TrustState.INTEGRITY_ALERT,
        ),
    }


def percentile_ns(
    values: list[int],
    percentile: float,
) -> float:
    return float(
        np.percentile(
            np.asarray(
                values,
                dtype=np.float64,
            ),
            percentile,
            method="linear",
        )
    )


def summarize_latency(
    values: list[int],
) -> dict:
    if not values:
        raise ValueError(
            "Latency list is empty"
        )

    return {
        "count":
            len(
                values
            ),

        "minimum_ns":
            int(
                min(
                    values
                )
            ),

        "median_ns":
            float(
                statistics.median(
                    values
                )
            ),

        "mean_ns":
            float(
                statistics.fmean(
                    values
                )
            ),

        "p95_ns":
            percentile_ns(
                values,
                95.0,
            ),

        "p99_ns":
            percentile_ns(
                values,
                99.0,
            ),

        "maximum_ns":
            int(
                max(
                    values
                )
            ),
    }


def warmup(
    fn: Callable[[], object],
) -> None:
    for _ in range(
        WARMUP_ITERATIONS
    ):
        fn()


def timed_block(
    fn: Callable[[], object],
) -> list[int]:
    values: list[int] = []

    gc_was_enabled = (
        gc.isenabled()
    )

    gc.disable()

    try:
        for _ in range(
            ITERATIONS_PER_BLOCK
        ):
            start = (
                time.perf_counter_ns()
            )

            fn()

            stop = (
                time.perf_counter_ns()
            )

            values.append(
                stop
                - start
            )

    finally:
        if gc_was_enabled:
            gc.enable()

    return values


def measure_python_allocations(
    fn: Callable[[], object],
) -> dict:
    gc.collect()

    tracemalloc.start()

    try:
        for _ in range(
            MEMORY_ITERATIONS
        ):
            fn()

        current, peak = (
            tracemalloc.get_traced_memory()
        )

    finally:
        tracemalloc.stop()

    return {
        "iterations":
            MEMORY_ITERATIONS,

        "current_bytes":
            int(
                current
            ),

        "peak_bytes":
            int(
                peak
            ),
    }


def rss_snapshot() -> dict:
    value = int(
        resource.getrusage(
            resource.RUSAGE_SELF
        ).ru_maxrss
    )

    system = (
        platform.system()
    )

    if system == "Linux":
        unit = "KiB"
    elif system == "Darwin":
        unit = "bytes"
    else:
        unit = (
            "platform_specific_ru_maxrss_units"
        )

    return {
        "ru_maxrss":
            value,

        "unit":
            unit,

        "platform_system":
            system,
    }


def runtime_source_footprint() -> dict:
    paths = [
        (
            ROOT
            / "src/imu_reliability/runtime/"
              "__init__.py"
        ),
        (
            ROOT
            / "src/imu_reliability/runtime/"
              "decision.py"
        ),
        (
            ROOT
            / "src/imu_reliability/runtime/"
              "reliability.py"
        ),
    ]

    files = {}

    total = 0

    for path in paths:
        size = len(
            path.read_bytes()
        )

        total += size

        files[
            str(
                path.relative_to(
                    ROOT
                )
            )
        ] = {
            "raw_bytes":
                size,

            "raw_sha256":
                raw_sha256(
                    path
                ),
        }

    return {
        "files":
            files,

        "total_raw_python_source_bytes":
            total,

        "is_embedded_flash_measurement":
            False,

        "is_mcu_code_size_measurement":
            False,
    }


def environment_metadata() -> dict:
    return {
        "python_version":
            sys.version,

        "torch_version":
            torch.__version__,

        "numpy_version":
            np.__version__,

        "platform":
            platform.platform(),

        "machine":
            platform.machine(),

        "processor":
            platform.processor(),

        "cpu_count":
            os.cpu_count(),

        "torch_num_threads":
            torch.get_num_threads(),

        "torch_num_interop_threads":
            torch.get_num_interop_threads(),

        "pid":
            os.getpid(),
    }


def run_measurements(
    model,
) -> dict:
    window = synthetic_window()

    empty = empty_assessment()

    def task_only():
        with torch.inference_mode():
            logits = model(
                window
            )

        return decision_from_logits(
            logits
        )

    def integrated():
        return run_reliability_window(
            model,
            window,
            empty,
        )

    post_inputs = (
        fixed_post_logit_inputs()
    )

    post_functions = {}

    for (
        name,
        (
            logits,
            assessment,
            expected_state,
        ),
    ) in post_inputs.items():

        def make_fn(
            logits=logits,
            assessment=assessment,
            expected_state=expected_state,
        ):
            def fn():
                result = decide_from_logits(
                    logits,
                    assessment,
                )

                if (
                    result.trust_state
                    is not expected_state
                ):
                    raise RuntimeError(
                        "Post-logit benchmark state changed"
                    )

                return result

            return fn

        post_functions[
            name
        ] = make_fn()

    warmup(
        task_only
    )

    warmup(
        integrated
    )

    for fn in post_functions.values():
        warmup(
            fn
        )

    task_latencies: list[int] = []
    integrated_latencies: list[int] = []

    pair_block_order = []

    for block_index in range(
        MEASUREMENT_BLOCKS
    ):
        if block_index % 2 == 0:
            order = [
                "task_only_reference",
                "integrated_reliability",
            ]
        else:
            order = [
                "integrated_reliability",
                "task_only_reference",
            ]

        pair_block_order.append(
            {
                "block_index":
                    block_index,

                "order":
                    order,
            }
        )

        for name in order:
            if (
                name
                == "task_only_reference"
            ):
                task_latencies.extend(
                    timed_block(
                        task_only
                    )
                )

            else:
                integrated_latencies.extend(
                    timed_block(
                        integrated
                    )
                )

    post_latencies = {
        name:
            []
        for name in post_functions
    }

    for _ in range(
        MEASUREMENT_BLOCKS
    ):
        for (
            name,
            fn,
        ) in post_functions.items():
            post_latencies[
                name
            ].extend(
                timed_block(
                    fn
                )
            )

    if (
        len(
            task_latencies
        )
        != TOTAL_MEASURED_CALLS_PER_VARIANT
    ):
        raise RuntimeError(
            "Task-only measured-call count mismatch"
        )

    if (
        len(
            integrated_latencies
        )
        != TOTAL_MEASURED_CALLS_PER_VARIANT
    ):
        raise RuntimeError(
            "Integrated measured-call count mismatch"
        )

    for (
        name,
        values,
    ) in post_latencies.items():
        if (
            len(
                values
            )
            != TOTAL_MEASURED_CALLS_PER_VARIANT
        ):
            raise RuntimeError(
                f"Post-logit measured-call count mismatch: {name}"
            )

    task_summary = summarize_latency(
        task_latencies
    )

    integrated_summary = summarize_latency(
        integrated_latencies
    )

    incremental_ns = (
        integrated_summary[
            "median_ns"
        ]
        - task_summary[
            "median_ns"
        ]
    )

    relative = (
        incremental_ns
        / task_summary[
            "median_ns"
        ]
    )

    with torch.inference_mode():
        actual_logits = model(
            window
        )

    actual_task_prediction = (
        decision_from_logits(
            actual_logits
        )
    )

    actual_integrated = (
        decide_from_logits(
            actual_logits,
            empty,
        )
    )

    if (
        int(
            actual_task_prediction[
                0
            ].item()
        )
        != actual_integrated.task_prediction
    ):
        raise RuntimeError(
            "Integrated task prediction differs from task-only prediction"
        )

    memory = {
        "task_only_reference":
            measure_python_allocations(
                task_only
            ),

        "integrated_reliability":
            measure_python_allocations(
                integrated
            ),
    }

    for (
        name,
        fn,
    ) in post_functions.items():
        memory[
            name
        ] = (
            measure_python_allocations(
                fn
            )
        )

    return {
        "latency": {
            "task_only_reference": {
                "summary":
                    task_summary,

                "per_iteration_ns":
                    task_latencies,
            },

            "integrated_reliability": {
                "summary":
                    integrated_summary,

                "per_iteration_ns":
                    integrated_latencies,
            },

            "post_logit": {
                name: {
                    "summary":
                        summarize_latency(
                            values
                        ),

                    "per_iteration_ns":
                        values,
                }
                for (
                    name,
                    values,
                ) in post_latencies.items()
            },

            "pair_block_order":
                pair_block_order,

            "primary_incremental_latency_ns":
                float(
                    incremental_ns
                ),

            "primary_relative_overhead":
                float(
                    relative
                ),

            "negative_increment_preserved":
                (
                    incremental_ns
                    < 0
                ),
        },

        "python_allocations":
            memory,

        "functional_snapshot": {
            "synthetic_task_prediction":
                int(
                    actual_integrated
                    .task_prediction
                ),

            "synthetic_trust_state":
                actual_integrated
                .trust_state
                .value,

            "synthetic_ood_margin":
                float(
                    actual_integrated
                    .ood_margin
                ),

            "ood_threshold":
                OOD_THRESHOLD,

            "task_only_and_integrated_prediction_match":
                True,
        },
    }


def build_result(
    protocol: dict,
    measurements: dict,
    rss_before_model_load: dict,
    rss_after_model_load: dict,
    rss_after_measurement: dict,
) -> dict:
    payload = {
        "result_id":
            "RUNTIME_RESOURCE_OVERHEAD_V1_CANDIDATE",

        "status":
            "reference_host_measurement_complete_candidate_not_yet_frozen",

        "scope":
            "reference_host_engineering_measurement",

        "source_anchors": {
            "resource_protocol": {
                "tag":
                    RESOURCE_PROTOCOL_TAG,

                "tag_commit":
                    RESOURCE_PROTOCOL_COMMIT,

                "raw_sha256":
                    PROTOCOL_RAW_SHA256,

                "content_sha256":
                    PROTOCOL_CONTENT_SHA256,
            },

            "reference_runtime": {
                "tag":
                    REFERENCE_RUNTIME_TAG,

                "tag_commit":
                    REFERENCE_RUNTIME_COMMIT,

                "runtime_init_raw_sha256":
                    RUNTIME_INIT_SHA256,

                "decision_raw_sha256":
                    RUNTIME_DECISION_SHA256,

                "reliability_raw_sha256":
                    RUNTIME_RELIABILITY_SHA256,
            },

            "protected_model_loader": {
                "source":
                    str(
                        V1B.relative_to(
                            ROOT
                        )
                    ),

                "raw_sha256":
                    V1B_RAW_SHA256,
            },

            "checkpoint": {
                "path":
                    str(
                        CHECKPOINT
                    ),

                "sha256":
                    CHECKPOINT_SHA256,

                "loading_time_included_in_latency_measurement":
                    False,
            },
        },

        "measurement_contract_snapshot": {
            "input_source":
                "deterministic_synthetic_only",

            "window_shape":
                [
                    1,
                    40,
                    9,
                ],

            "warmup_iterations":
                WARMUP_ITERATIONS,

            "measurement_blocks":
                MEASUREMENT_BLOCKS,

            "iterations_per_block":
                ITERATIONS_PER_BLOCK,

            "measured_calls_per_variant":
                TOTAL_MEASURED_CALLS_PER_VARIANT,

            "memory_iterations":
                MEMORY_ITERATIONS,

            "torch_device":
                "cpu",

            "batch_size":
                1,

            "protected_dataset_used":
                False,

            "calibration_dataset_used":
                False,

            "final_test_dataset_used":
                False,

            "external_domain_shift_dataset_used":
                False,
        },

        "environment":
            environment_metadata(),

        "rss_snapshots":
            {
                "before_model_load":
                    rss_before_model_load,

                "after_model_load":
                    rss_after_model_load,

                "after_measurement":
                    rss_after_measurement,
            },

        "measurements":
            measurements,

        "static_runtime_source_footprint":
            runtime_source_footprint(),

        "functional_invariants": {
            "one_full_task_model_call_per_end_to_end_iteration":
                True,

            "historical_prediction_bias":
                0.9,

            "ood_threshold":
                OOD_THRESHOLD,

            "ood_score":
                "abs(logit_0 - logit_1)",

            "feature_vector_used_by_ood":
                False,

            "second_task_forward_used":
                False,

            "task_prediction_always_returned":
                True,

            "integrity_precedes_ood":
                True,
        },

        "claim_boundary": {
            "reference_host_measurement_only":
                True,

            "stm32f722_latency_claimed":
                False,

            "stm32f722_cycle_count_claimed":
                False,

            "stm32f722_flash_overhead_claimed":
                False,

            "stm32f722_ram_overhead_claimed":
                False,

            "stm32f722_energy_overhead_claimed":
                False,

            "deployed_firmware_performance_claimed":
                False,

            "python_source_bytes_are_embedded_flash":
                False,

            "tracemalloc_bytes_are_stm32_ram":
                False,

            "ru_maxrss_is_stm32_ram":
                False,
        },

        "scientific_boundary": {
            "ood_threshold_modified":
                False,

            "ood_method_modified":
                False,

            "integrity_operating_point_modified":
                False,

            "protected_final_test_recomputed":
                False,

            "ood_final_test_evaluator_rerun":
                False,

            "integrity_final_test_evaluator_rerun":
                False,

            "resource_result_used_for_scientific_selection":
                False,
        },
    }

    payload[
        "content_sha256"
    ] = canonical_digest(
        payload
    )

    return payload


def main() -> None:
    if RESULT.exists():
        raise RuntimeError(
            "Refusing to overwrite resource-overhead candidate result"
        )

    protocol = verify_protocol()

    verify_frozen_source_anchors()

    configure_host_runtime()

    rss_before_model_load = (
        rss_snapshot()
    )

    verify_checkpoint_hash()

    model = load_protected_model()

    rss_after_model_load = (
        rss_snapshot()
    )

    measurements = run_measurements(
        model
    )

    rss_after_measurement = (
        rss_snapshot()
    )

    result = build_result(
        protocol,
        measurements,
        rss_before_model_load,
        rss_after_model_load,
        rss_after_measurement,
    )

    RESULT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    RESULT.write_text(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )

    latency = result[
        "measurements"
    ][
        "latency"
    ]

    print(
        "RUNTIME_RESOURCE_OVERHEAD_V1_COMPLETE = True"
    )

    print(
        "TASK_ONLY_MEDIAN_NS =",
        latency[
            "task_only_reference"
        ][
            "summary"
        ][
            "median_ns"
        ],
    )

    print(
        "INTEGRATED_MEDIAN_NS =",
        latency[
            "integrated_reliability"
        ][
            "summary"
        ][
            "median_ns"
        ],
    )

    print(
        "PRIMARY_INCREMENTAL_LATENCY_NS =",
        latency[
            "primary_incremental_latency_ns"
        ],
    )

    print(
        "PRIMARY_RELATIVE_OVERHEAD =",
        latency[
            "primary_relative_overhead"
        ],
    )

    print(
        "RESULT_CONTENT_SHA256 =",
        result[
            "content_sha256"
        ],
    )

    print(
        "PROTECTED_DATASET_USED = False"
    )

    print(
        "FINAL_TEST_EVALUATOR_RERUN = False"
    )

    print(
        "STM32_PERFORMANCE_CLAIMED = False"
    )


if __name__ == "__main__":
    main()
