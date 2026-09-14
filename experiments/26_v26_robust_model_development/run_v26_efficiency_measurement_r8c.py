from __future__ import annotations

import csv
import gc
import hashlib
import json
import os
import platform
import statistics
import sys
import time
from pathlib import Path

import torch


ROOT = Path(
    "/mnt/hdd16T/ToqeerHomeBackup/toqeer/IMU_Reliability"
)

SUITE = (
    ROOT
    / "experiments"
    / "16_benchmark_suite"
)

SCREEN = (
    ROOT
    / "experiments"
    / "17_v25_screening"
)

V26_EXP = (
    ROOT
    / "experiments"
    / "26_v26_robust_model_development"
)

R8A = (
    ROOT
    / "results"
    / "v26_efficiency_protocol_r8a"
)

R8B = (
    ROOT
    / "results"
    / "v26_efficiency_implementation_integrity_r8b"
)

OUT = (
    ROOT
    / "results"
    / "v26_efficiency_measurement_r8c"
)

OUT.mkdir(
    parents=True,
    exist_ok=True,
)


for path in [
    SUITE,
    SCREEN,
    V26_EXP,
]:

    if str(path) not in sys.path:
        sys.path.insert(
            0,
            str(path),
        )


from engine.model_registry import (
    create_model,
)

from engine.model_forward import (
    model_forward,
)

from v25_candidates import (
    create_candidate,
)

from candidate_models_r2 import (
    create_v26_candidate,
)


V25 = "ReliabilityCNN_v25"

V26 = "V26C_DualGateLiteCons"

NUM_CLASSES = 6
INPUT_CHANNELS = 6
INPUT_LENGTH = 128

CPU_WARMUP = 200
CPU_ITERATIONS = 1000

GPU_B1_WARMUP = 200
GPU_B1_ITERATIONS = 1000

GPU_B64_WARMUP = 100
GPU_B64_ITERATIONS = 500


def sha256_file(
    path: Path,
):

    h = hashlib.sha256()

    with path.open(
        "rb"
    ) as f:

        for block in iter(
            lambda: f.read(
                1024 * 1024
            ),
            b"",
        ):

            h.update(
                block
            )

    return h.hexdigest()


def read_csv(
    path: Path,
):

    with path.open(
        newline="",
        encoding="utf-8",
    ) as f:

        return list(
            csv.DictReader(f)
        )


def write_csv(
    path: Path,
    rows,
):

    if not rows:

        raise RuntimeError(
            f"No rows for {path}"
        )


    with path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=list(
                rows[0].keys()
            ),
        )

        writer.writeheader()

        writer.writerows(
            rows
        )


def write_json(
    path: Path,
    obj,
):

    path.write_text(
        json.dumps(
            obj,
            indent=2,
            sort_keys=True,
            default=str,
        )
        + "\n"
    )


def load_state(
    path: Path,
):

    try:

        state = torch.load(
            path,
            map_location="cpu",
            weights_only=True,
        )

    except TypeError:

        state = torch.load(
            path,
            map_location="cpu",
        )


    if not isinstance(
        state,
        dict,
    ):

        raise RuntimeError(
            f"{path}: checkpoint is not a state dict"
        )


    if not state:

        raise RuntimeError(
            f"{path}: checkpoint is empty"
        )


    if not all(
        torch.is_tensor(
            value
        )
        for value in state.values()
    ):

        raise RuntimeError(
            f"{path}: non-tensor checkpoint entry"
        )


    return state


def instantiate(
    model_name: str,
):

    if model_name == V25:

        return create_candidate(
            "V25Dense64",
            NUM_CLASSES,
            input_channels=INPUT_CHANNELS,
        )


    if model_name == V26:

        return create_v26_candidate(
            V26,
            NUM_CLASSES,
            input_channels=INPUT_CHANNELS,
        )


    return create_model(
        model_name,
        NUM_CLASSES,
        input_channels=INPUT_CHANNELS,
    )


def forward(
    model_name,
    model,
    x,
):

    if model_name == V26:

        output = model(
            x
        )

    else:

        output = model_forward(
            model,
            x,
        )


    if isinstance(
        output,
        (
            tuple,
            list,
        ),
    ):

        output = output[
            0
        ]


    return output


def mean(
    values,
):

    return float(
        statistics.fmean(
            values
        )
    )


def median(
    values,
):

    return float(
        statistics.median(
            values
        )
    )


print("=" * 118)
print("V26 R8C ONE-SHOT FROZEN EFFICIENCY MEASUREMENT")
print("=" * 118)


# ============================================================
# 1. Frozen protocol / implementation binding
# ============================================================

protocol = json.loads(
    (
        R8A
        / "v26_efficiency_protocol_r8a.json"
    ).read_text()
)

contract = json.loads(
    (
        R8B
        / "timing_implementation_contract_r8b.json"
    ).read_text()
)


if protocol[
    "status"
] != "FROZEN_BEFORE_TIMING":

    raise RuntimeError(
        "R8A timing protocol is not frozen"
    )


if contract[
    "status"
] != "READY_TO_FREEZE_PROFILER":

    raise RuntimeError(
        "R8B timing implementation contract invalid"
    )


if contract[
    "mac_flop"
] != "NOT_COMPARABLE":

    raise RuntimeError(
        "MAC/FLOP policy drift"
    )


required_numeric = {
    "cpu_warmup":
        (
            contract[
                "cpu"
            ][
                "warmup"
            ],
            CPU_WARMUP,
        ),

    "cpu_iterations":
        (
            contract[
                "cpu"
            ][
                "iterations"
            ],
            CPU_ITERATIONS,
        ),

    "gpu_b1_warmup":
        (
            contract[
                "gpu_batch1"
            ][
                "warmup"
            ],
            GPU_B1_WARMUP,
        ),

    "gpu_b1_iterations":
        (
            contract[
                "gpu_batch1"
            ][
                "iterations"
            ],
            GPU_B1_ITERATIONS,
        ),

    "gpu_b64_warmup":
        (
            contract[
                "gpu_batch64"
            ][
                "warmup"
            ],
            GPU_B64_WARMUP,
        ),

    "gpu_b64_iterations":
        (
            contract[
                "gpu_batch64"
            ][
                "iterations"
            ],
            GPU_B64_ITERATIONS,
        ),
}


for name, (
    actual,
    expected,
) in required_numeric.items():

    if int(
        actual
    ) != expected:

        raise RuntimeError(
            f"Frozen timing mismatch {name}: "
            f"{actual} != {expected}"
        )


print(
    "R8C_FROZEN_PROTOCOL_AND_CONTRACT_BOUND=True"
)


# ============================================================
# 2. Runtime environment
# ============================================================

if not torch.cuda.is_available():

    raise RuntimeError(
        "CUDA unavailable"
    )


torch.set_num_threads(
    1
)

torch.set_num_interop_threads(
    1
)


device = torch.device(
    "cuda:0"
)


try:

    affinity = sorted(
        os.sched_getaffinity(
            0
        )
    )

except Exception:

    affinity = None


cpu_model = None

try:

    for line in Path(
        "/proc/cpuinfo"
    ).read_text().splitlines():

        if line.startswith(
            "model name"
        ):

            cpu_model = (
                line.split(
                    ":",
                    1,
                )[
                    1
                ].strip()
            )

            break

except Exception:

    pass


governor = None

governor_path = Path(
    "/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"
)

if governor_path.exists():

    try:
        governor = governor_path.read_text().strip()
    except Exception:
        governor = None


environment = {
    "python_version":
        platform.python_version(),

    "torch_version":
        torch.__version__,

    "torch_cuda_version":
        torch.version.cuda,

    "platform":
        platform.platform(),

    "cpu_model":
        cpu_model,

    "logical_cpu_count":
        os.cpu_count(),

    "process_cpu_affinity":
        affinity,

    "cpu0_scaling_governor":
        governor,

    "torch_num_threads":
        torch.get_num_threads(),

    "torch_num_interop_threads":
        torch.get_num_interop_threads(),

    "cuda_device_index":
        0,

    "cuda_device_name":
        torch.cuda.get_device_name(
            0
        ),

    "cuda_device_count":
        torch.cuda.device_count(),

    "cudnn_version":
        torch.backends.cudnn.version(),

    "cudnn_benchmark":
        torch.backends.cudnn.benchmark,

    "cudnn_deterministic":
        torch.backends.cudnn.deterministic,

    "cuda_matmul_allow_tf32":
        torch.backends.cuda.matmul.allow_tf32,

    "cudnn_allow_tf32":
        torch.backends.cudnn.allow_tf32,

    "synthetic_inputs_only":
        True,

    "test_data_access":
        False,
}


write_json(
    OUT
    / "runtime_environment_r8c.json",
    environment,
)


print(
    "R8C_DEVICE=",
    environment[
        "cuda_device_name"
    ],
)

print(
    "R8C_CPU_MODEL=",
    environment[
        "cpu_model"
    ],
)


# ============================================================
# 3. Manifest
# ============================================================

manifest = read_csv(
    R8A
    / "efficiency_checkpoint_manifest_11.csv"
)


if len(
    manifest
) != 11:

    raise RuntimeError(
        "R8C manifest count != 11"
    )


expected_order = contract[
    "model_order"
]


actual_order = [
    row[
        "model"
    ]
    for row in manifest
]


if actual_order != expected_order:

    raise RuntimeError(
        "Frozen R8C model order mismatch"
    )


# ============================================================
# 4. Mark irreversible timing start
# ============================================================

(
    OUT
    / "TIMING_STARTED"
).write_text(
    "V26 R8C frozen efficiency timing started.\n"
)


print(
    "R8C_TIMING_STARTED=True",
    flush=True,
)


# ============================================================
# 5. Measure all 11 models
# ============================================================

summary_rows = []

latency_samples = []


for index, row in enumerate(
    manifest,
    start=1,
):

    model_name = row[
        "model"
    ]


    print()
    print("=" * 118)
    print(
        f"R8C_MODEL_START={index}/11 {model_name}"
    )
    print("=" * 118)


    checkpoint = (
        ROOT
        / row[
            "checkpoint"
        ]
    )


    actual_sha = sha256_file(
        checkpoint
    )


    if actual_sha != row[
        "checkpoint_sha256"
    ]:

        raise RuntimeError(
            f"{model_name}: checkpoint SHA mismatch"
        )


    model = instantiate(
        model_name
    )

    model.eval()


    params = int(
        sum(
            p.numel()
            for p in model.parameters()
        )
    )


    expected_params = int(
        row[
            "parameter_count_frozen"
        ]
    )


    if params != expected_params:

        raise RuntimeError(
            f"{model_name}: parameter mismatch"
        )


    state = load_state(
        checkpoint
    )


    model.load_state_dict(
        state,
        strict=True,
    )


    del state


    # --------------------------------------------------------
    # CPU batch1
    # --------------------------------------------------------

    model.to(
        "cpu"
    )

    model.eval()


    x_cpu = torch.zeros(
        (
            1,
            INPUT_LENGTH,
            INPUT_CHANNELS,
        ),
        dtype=torch.float32,
        device="cpu",
    )


    with torch.inference_mode():

        for _ in range(
            CPU_WARMUP
        ):

            _ = forward(
                model_name,
                model,
                x_cpu,
            )


        cpu_samples = []


        for iteration in range(
            CPU_ITERATIONS
        ):

            t0 = time.perf_counter()

            _ = forward(
                model_name,
                model,
                x_cpu,
            )

            elapsed_ms = (
                time.perf_counter()
                -
                t0
            ) * 1000.0


            cpu_samples.append(
                elapsed_ms
            )


            latency_samples.append({
                "model":
                    model_name,

                "device":
                    "cpu",

                "batch_size":
                    1,

                "iteration":
                    iteration + 1,

                "latency_ms":
                    elapsed_ms,
            })


    cpu_mean_ms = mean(
        cpu_samples
    )

    cpu_median_ms = median(
        cpu_samples
    )


    # --------------------------------------------------------
    # GPU batch1
    # --------------------------------------------------------

    model.to(
        device
    )

    model.eval()


    x_gpu_1 = torch.zeros(
        (
            1,
            INPUT_LENGTH,
            INPUT_CHANNELS,
        ),
        dtype=torch.float32,
        device=device,
    )


    with torch.inference_mode():

        for _ in range(
            GPU_B1_WARMUP
        ):

            _ = forward(
                model_name,
                model,
                x_gpu_1,
            )


        torch.cuda.synchronize(
            device
        )


        gpu_samples = []


        for iteration in range(
            GPU_B1_ITERATIONS
        ):

            torch.cuda.synchronize(
                device
            )

            t0 = time.perf_counter()


            _ = forward(
                model_name,
                model,
                x_gpu_1,
            )


            torch.cuda.synchronize(
                device
            )


            elapsed_ms = (
                time.perf_counter()
                -
                t0
            ) * 1000.0


            gpu_samples.append(
                elapsed_ms
            )


            latency_samples.append({
                "model":
                    model_name,

                "device":
                    "cuda:0",

                "batch_size":
                    1,

                "iteration":
                    iteration + 1,

                "latency_ms":
                    elapsed_ms,
            })


    gpu_mean_ms = mean(
        gpu_samples
    )

    gpu_median_ms = median(
        gpu_samples
    )


    # --------------------------------------------------------
    # GPU batch64 throughput
    # --------------------------------------------------------

    x_gpu_64 = torch.zeros(
        (
            64,
            INPUT_LENGTH,
            INPUT_CHANNELS,
        ),
        dtype=torch.float32,
        device=device,
    )


    with torch.inference_mode():

        for _ in range(
            GPU_B64_WARMUP
        ):

            _ = forward(
                model_name,
                model,
                x_gpu_64,
            )


        torch.cuda.synchronize(
            device
        )


        t0 = time.perf_counter()


        for _ in range(
            GPU_B64_ITERATIONS
        ):

            _ = forward(
                model_name,
                model,
                x_gpu_64,
            )


        torch.cuda.synchronize(
            device
        )


        throughput_elapsed_s = (
            time.perf_counter()
            -
            t0
        )


    throughput_samples_total = (
        GPU_B64_ITERATIONS
        *
        64
    )


    gpu_b64_samples_per_second = (
        throughput_samples_total
        /
        throughput_elapsed_s
    )


    checkpoint_bytes = int(
        row[
            "checkpoint_bytes"
        ]
    )


    result = {
        "model":
            model_name,

        "parameter_count":
            params,

        "checkpoint_bytes":
            checkpoint_bytes,

        "checkpoint_mb_decimal":
            (
                checkpoint_bytes
                /
                1_000_000.0
            ),

        "checkpoint_mib":
            (
                checkpoint_bytes
                /
                (
                    1024.0
                    *
                    1024.0
                )
            ),

        "cpu_batch1_mean_ms":
            cpu_mean_ms,

        "cpu_batch1_median_ms":
            cpu_median_ms,

        "gpu_batch1_mean_ms":
            gpu_mean_ms,

        "gpu_batch1_median_ms":
            gpu_median_ms,

        "gpu_batch64_samples_per_second":
            gpu_b64_samples_per_second,

        "gpu_batch64_elapsed_seconds":
            throughput_elapsed_s,

        "gpu_batch64_total_samples":
            throughput_samples_total,

        "mac_flop":
            "NOT_COMPARABLE",

        "checkpoint_sha256":
            actual_sha,
    }


    summary_rows.append(
        result
    )


    # Incremental preservation.
    write_csv(
        OUT
        / "efficiency_measurements_partial.csv",
        summary_rows,
    )


    print(
        "R8C_MODEL_TIMING_COMPLETE:",
        model_name,
        "PARAMS=",
        params,
        "CKPT_MB=",
        f"{result['checkpoint_mb_decimal']:.6f}",
        "CPU_B1_MEDIAN_MS=",
        f"{cpu_median_ms:.6f}",
        "GPU_B1_MEDIAN_MS=",
        f"{gpu_median_ms:.6f}",
        "GPU_B64_SAMPLES_PER_S=",
        f"{gpu_b64_samples_per_second:.3f}",
        flush=True,
    )


    del x_cpu
    del x_gpu_1
    del x_gpu_64
    del model

    gc.collect()

    torch.cuda.empty_cache()


if len(
    summary_rows
) != 11:

    raise RuntimeError(
        "R8C measurement rows != 11"
    )


write_csv(
    OUT
    / "efficiency_measurements_11.csv",
    summary_rows,
)


write_csv(
    OUT
    / "batch1_latency_samples_22000.csv",
    latency_samples,
)


if len(
    latency_samples
) != (
    11
    *
    (
        CPU_ITERATIONS
        +
        GPU_B1_ITERATIONS
    )
):

    raise RuntimeError(
        "R8C latency sample count != 22000"
    )


print(
    "R8C_EFFICIENCY_MEASUREMENT_ROWS_PASS_11_OF_11=True"
)

print(
    "R8C_BATCH1_LATENCY_SAMPLE_ROWS_PASS_22000=True"
)


# ============================================================
# 6. Rankings
# ============================================================

ranking_specs = [
    (
        "parameter_count",
        "lower",
    ),

    (
        "checkpoint_bytes",
        "lower",
    ),

    (
        "cpu_batch1_median_ms",
        "lower",
    ),

    (
        "gpu_batch1_median_ms",
        "lower",
    ),

    (
        "gpu_batch64_samples_per_second",
        "higher",
    ),
]


ranking_rows = []

v26_ranks = {}


for metric, direction in ranking_specs:

    ordered = sorted(
        summary_rows,
        key=(
            (
                lambda row:
                    (
                        float(
                            row[
                                metric
                            ]
                        ),
                        row[
                            "model"
                        ],
                    )
            )
            if direction
            ==
            "lower"
            else
            (
                lambda row:
                    (
                        -
                        float(
                            row[
                                metric
                            ]
                        ),
                        row[
                            "model"
                        ],
                    )
            )
        ),
    )


    for rank, row in enumerate(
        ordered,
        start=1,
    ):

        ranking_rows.append({
            "metric":
                metric,

            "direction":
                direction,

            "rank":
                rank,

            "model":
                row[
                    "model"
                ],

            "value":
                row[
                    metric
                ],
        })


        if row[
            "model"
        ] == V26:

            v26_ranks[
                metric
            ] = rank


if len(
    ranking_rows
) != 55:

    raise RuntimeError(
        "R8C ranking rows != 55"
    )


write_csv(
    OUT
    / "efficiency_rankings_55.csv",
    ranking_rows,
)


print(
    "R8C_EFFICIENCY_RANKINGS_PASS_55=True"
)


# ============================================================
# 7. V26C matched efficiency comparison
# ============================================================

lookup = {
    row[
        "model"
    ]:
        row

    for row in summary_rows
}


v26 = lookup[
    V26
]


comparators = {}


for name in [
    V25,
    "ReliabilityCNN_v24",
    "DS_CNN",
    "DeepConvLSTM",
]:

    base = lookup[
        name
    ]


    comparators[
        name
    ] = {
        "parameter_ratio_v26_over_comparator":
            (
                v26[
                    "parameter_count"
                ]
                /
                base[
                    "parameter_count"
                ]
            ),

        "parameter_reduction_fraction":
            (
                1.0
                -
                (
                    v26[
                        "parameter_count"
                    ]
                    /
                    base[
                        "parameter_count"
                    ]
                )
            ),

        "checkpoint_size_ratio_v26_over_comparator":
            (
                v26[
                    "checkpoint_bytes"
                ]
                /
                base[
                    "checkpoint_bytes"
                ]
            ),

        "cpu_batch1_speed_ratio_comparator_over_v26":
            (
                base[
                    "cpu_batch1_median_ms"
                ]
                /
                v26[
                    "cpu_batch1_median_ms"
                ]
            ),

        "gpu_batch1_speed_ratio_comparator_over_v26":
            (
                base[
                    "gpu_batch1_median_ms"
                ]
                /
                v26[
                    "gpu_batch1_median_ms"
                ]
            ),

        "gpu_batch64_throughput_ratio_v26_over_comparator":
            (
                v26[
                    "gpu_batch64_samples_per_second"
                ]
                /
                base[
                    "gpu_batch64_samples_per_second"
                ]
            ),
    }


v26_summary = {
    "model":
        V26,

    "parameter_count":
        v26[
            "parameter_count"
        ],

    "checkpoint_bytes":
        v26[
            "checkpoint_bytes"
        ],

    "checkpoint_mb_decimal":
        v26[
            "checkpoint_mb_decimal"
        ],

    "cpu_batch1_mean_ms":
        v26[
            "cpu_batch1_mean_ms"
        ],

    "cpu_batch1_median_ms":
        v26[
            "cpu_batch1_median_ms"
        ],

    "gpu_batch1_mean_ms":
        v26[
            "gpu_batch1_mean_ms"
        ],

    "gpu_batch1_median_ms":
        v26[
            "gpu_batch1_median_ms"
        ],

    "gpu_batch64_samples_per_second":
        v26[
            "gpu_batch64_samples_per_second"
        ],

    "ranks_out_of_11":
        v26_ranks,

    "matched_comparator_ratios":
        comparators,

    "mac_flop":
        "NOT_COMPARABLE",
}


write_json(
    OUT
    / "v26c_efficiency_summary_r8c.json",
    v26_summary,
)


# ============================================================
# 8. Final receipt
# ============================================================

receipt = {
    "stage":
        "V26_EFFICIENCY_MEASUREMENT_R8C",

    "status":
        "PASS",

    "model_count":
        11,

    "measurement_rows":
        11,

    "batch1_latency_sample_rows":
        22000,

    "cpu_batch1_warmup":
        CPU_WARMUP,

    "cpu_batch1_iterations":
        CPU_ITERATIONS,

    "gpu_batch1_warmup":
        GPU_B1_WARMUP,

    "gpu_batch1_iterations":
        GPU_B1_ITERATIONS,

    "gpu_batch64_warmup":
        GPU_B64_WARMUP,

    "gpu_batch64_iterations":
        GPU_B64_ITERATIONS,

    "synthetic_input_only":
        True,

    "input_shape_batch1":
        [
            1,
            128,
            6,
        ],

    "input_shape_batch64":
        [
            64,
            128,
            6,
        ],

    "cpu_threads":
        1,

    "model_eval":
        True,

    "inference_mode":
        True,

    "torch_compile":
        False,

    "mixed_precision":
        False,

    "quantization":
        False,

    "mac_flop":
        "NOT_COMPARABLE",

    "checkpoint_sha_verified":
        "PASS_11_OF_11",

    "parameter_count_verified":
        "PASS_11_OF_11",

    "latency_timing_performed":
        True,

    "throughput_timing_performed":
        True,

    "protected_test_access":
        False,

    "real_dataset_access":
        False,

    "training_performed":
        False,

    "optimizer_created":
        False,

    "candidate_modified":
        False,

    "checkpoint_modified":
        False,

    "storm_used":
        False,

    "deployment_claim_allowed":
        False,

    "v26c_efficiency_ranks":
        v26_ranks,

    "next_gate":
        (
            "R8D read-only efficiency/scientific integration: "
            "combine frozen R7 robustness evidence with frozen "
            "R8C efficiency results, identify Pareto placement "
            "and freeze paper-facing internal claims before "
            "external STORM evaluation."
        ),
}


write_json(
    OUT
    / "v26_efficiency_measurement_receipt_r8c.json",
    receipt,
)


print()
print("=" * 118)
print("V26C R8C EFFICIENCY RESULT")
print("=" * 118)

print(
    "V26C_EFFICIENCY_PARAMS=",
    v26[
        "parameter_count"
    ],
)

print(
    "V26C_EFFICIENCY_CHECKPOINT_MB=",
    f"{v26['checkpoint_mb_decimal']:.6f}",
)

print(
    "V26C_CPU_BATCH1_MEAN_MS=",
    f"{v26['cpu_batch1_mean_ms']:.6f}",
)

print(
    "V26C_CPU_BATCH1_MEDIAN_MS=",
    f"{v26['cpu_batch1_median_ms']:.6f}",
)

print(
    "V26C_GPU_BATCH1_MEAN_MS=",
    f"{v26['gpu_batch1_mean_ms']:.6f}",
)

print(
    "V26C_GPU_BATCH1_MEDIAN_MS=",
    f"{v26['gpu_batch1_median_ms']:.6f}",
)

print(
    "V26C_GPU_BATCH64_SAMPLES_PER_SECOND=",
    f"{v26['gpu_batch64_samples_per_second']:.3f}",
)


for metric, rank in v26_ranks.items():

    print(
        "V26C_EFFICIENCY_RANK:",
        metric,
        "=",
        f"{rank}/11",
    )


print()
print(
    "V26_EFFICIENCY_MEASUREMENT_R8C_PASS=True"
)

print(
    "LATENCY_TIMING_PERFORMED=True"
)

print(
    "THROUGHPUT_TIMING_PERFORMED=True"
)

print(
    "TEST_DATA_ACCESSED=False"
)

print(
    "REAL_DATASET_ACCESSED=False"
)

print(
    "TRAINING_PERFORMED=False"
)

print(
    "STORM_USED=False"
)
