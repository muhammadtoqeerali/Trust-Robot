from pathlib import Path
import hashlib
import json
import platform
import statistics
import sys
import time

import numpy as np
import pandas as pd
import torch


SUITE = Path(
    "experiments/16_benchmark_suite"
).resolve()

if str(SUITE) not in sys.path:
    sys.path.insert(
        0,
        str(SUITE)
    )


from engine.model_registry import (
    create_model
)

from engine.model_forward import (
    model_forward
)


ROOT = Path(
    "results/benchmark_v3r1"
)

RAW = ROOT / "raw_runs"

ANALYSIS = (
    ROOT /
    "final_analysis"
)


DATASETS = {
    "UCI_HAR": 6,
    "PAMAP2": 12,
    "DSADS": 19,
    "MotionSense": 6,
}


MODELS = [
    "ReliabilityCNN_v22",
    "CNN1D",
    "LSTM",
    "DeepConvLSTM",
    "Transformer",
    "ReliabilityCNN_v24",
    "DS_CNN",
    "TCN",
    "TinyTransformer",
]


SEED = 42


def sha256_file(path):

    h = hashlib.sha256()

    with Path(path).open(
        "rb"
    ) as f:

        while True:

            block = f.read(
                1024 * 1024
            )

            if not block:
                break

            h.update(
                block
            )

    return h.hexdigest()


def load_state(path):

    try:

        return torch.load(
            path,
            map_location="cpu",
            weights_only=True
        )

    except TypeError:

        return torch.load(
            path,
            map_location="cpu"
        )


def call_model(
    model,
    x
):

    output = model_forward(
        model,
        x
    )

    if isinstance(
        output,
        (
            tuple,
            list
        )
    ):
        return output[0]

    return output


def percentile(
    values,
    p
):

    return float(
        np.percentile(
            np.asarray(
                values,
                dtype=float
            ),
            p
        )
    )


def benchmark_gpu(
    model,
    batch_size,
    warmup=50,
    iterations=200
):

    device = torch.device(
        "cuda:0"
    )

    x = torch.zeros(
        batch_size,
        128,
        6,
        device=device,
        dtype=torch.float32
    )


    model.eval()


    with torch.inference_mode():

        for _ in range(
            warmup
        ):
            call_model(
                model,
                x
            )


        torch.cuda.synchronize()


        timings = []


        for _ in range(
            iterations
        ):

            start = torch.cuda.Event(
                enable_timing=True
            )

            end = torch.cuda.Event(
                enable_timing=True
            )


            start.record()

            call_model(
                model,
                x
            )

            end.record()


            end.synchronize()


            timings.append(
                float(
                    start.elapsed_time(
                        end
                    )
                )
            )


        torch.cuda.synchronize()


        torch.cuda.reset_peak_memory_stats()


        baseline = (
            torch.cuda.memory_allocated()
        )


        call_model(
            model,
            x
        )


        torch.cuda.synchronize()


        peak = (
            torch.cuda.max_memory_allocated()
        )


    median_ms = float(
        np.median(
            timings
        )
    )


    return {
        "median_ms":
            median_ms,

        "mean_ms":
            float(
                np.mean(
                    timings
                )
            ),

        "std_ms":
            float(
                np.std(
                    timings,
                    ddof=1
                )
            ),

        "p95_ms":
            percentile(
                timings,
                95
            ),

        "throughput_samples_per_s":
            float(
                batch_size
                *
                1000.0
                /
                median_ms
            ),

        "peak_total_memory_mb":
            float(
                peak
                /
                1024
                /
                1024
            ),

        "forward_incremental_memory_mb":
            float(
                max(
                    peak - baseline,
                    0
                )
                /
                1024
                /
                1024
            ),

        "iterations":
            iterations,

        "warmup":
            warmup,
    }


def benchmark_cpu_b1(
    model,
    warmup=20,
    iterations=100
):

    x = torch.zeros(
        1,
        128,
        6,
        dtype=torch.float32
    )


    model.eval()


    with torch.inference_mode():

        for _ in range(
            warmup
        ):

            call_model(
                model,
                x
            )


        timings = []


        for _ in range(
            iterations
        ):

            start = (
                time.perf_counter()
            )


            call_model(
                model,
                x
            )


            elapsed = (
                time.perf_counter()
                -
                start
            )


            timings.append(
                elapsed
                *
                1000.0
            )


    median_ms = float(
        np.median(
            timings
        )
    )


    return {
        "median_ms":
            median_ms,

        "mean_ms":
            float(
                np.mean(
                    timings
                )
            ),

        "std_ms":
            float(
                np.std(
                    timings,
                    ddof=1
                )
            ),

        "p95_ms":
            percentile(
                timings,
                95
            ),

        "throughput_samples_per_s":
            float(
                1000.0
                /
                median_ms
            ),

        "iterations":
            iterations,

        "warmup":
            warmup,
    }


if not torch.cuda.is_available():

    raise RuntimeError(
        "CUDA unavailable"
    )


torch.manual_seed(
    42
)

np.random.seed(
    42
)


torch.set_num_threads(
    1
)

try:
    torch.set_num_interop_threads(
        1
    )
except RuntimeError:
    pass


print(
    "=" * 78
)

print(
    "BENCHMARK V3R1 EFFICIENCY MEASUREMENT"
)

print(
    "=" * 78
)

print(
    "GPU=",
    torch.cuda.get_device_name(
        0
    )
)

print(
    "TORCH=",
    torch.__version__
)

print(
    "CPU=",
    platform.processor()
)

print(
    "CPU_THREADS=",
    torch.get_num_threads()
)


rows = []

checkpoint_hashes = {}


for dataset, classes in (
    DATASETS.items()
):

    print()
    print(
        "DATASET=",
        dataset
    )


    for model_name in MODELS:

        checkpoint = (
            RAW /
            dataset /
            model_name /
            f"seed_{SEED}" /
            "best_model.pt"
        )


        if not checkpoint.exists():

            raise FileNotFoundError(
                checkpoint
            )


        state = load_state(
            checkpoint
        )


        checkpoint_hashes[
            str(
                checkpoint
            )
        ] = sha256_file(
            checkpoint
        )


        cpu_model = create_model(
            model_name,
            classes,
            input_channels=6
        )


        cpu_model.load_state_dict(
            state,
            strict=True
        )


        parameter_count = int(
            sum(
                parameter.numel()
                for parameter
                in cpu_model.parameters()
            )
        )


        trainable_parameter_count = int(
            sum(
                parameter.numel()
                for parameter
                in cpu_model.parameters()
                if parameter.requires_grad
            )
        )


        checkpoint_size_mb = float(
            checkpoint.stat().st_size
            /
            1024
            /
            1024
        )


        cpu_result = benchmark_cpu_b1(
            cpu_model
        )


        gpu_model = cpu_model.to(
            "cuda:0"
        )


        torch.cuda.synchronize()


        gpu_b1 = benchmark_gpu(
            gpu_model,
            1
        )


        gpu_b64 = benchmark_gpu(
            gpu_model,
            64
        )


        rows.append(
            {
                "dataset":
                    dataset,

                "model":
                    model_name,

                "seed":
                    SEED,

                "num_classes":
                    classes,

                "parameters":
                    parameter_count,

                "trainable_parameters":
                    trainable_parameter_count,

                "checkpoint_size_mb":
                    checkpoint_size_mb,

                "cpu_b1_median_ms":
                    cpu_result[
                        "median_ms"
                    ],

                "cpu_b1_mean_ms":
                    cpu_result[
                        "mean_ms"
                    ],

                "cpu_b1_p95_ms":
                    cpu_result[
                        "p95_ms"
                    ],

                "cpu_b1_throughput_samples_per_s":
                    cpu_result[
                        "throughput_samples_per_s"
                    ],

                "gpu_b1_median_ms":
                    gpu_b1[
                        "median_ms"
                    ],

                "gpu_b1_mean_ms":
                    gpu_b1[
                        "mean_ms"
                    ],

                "gpu_b1_p95_ms":
                    gpu_b1[
                        "p95_ms"
                    ],

                "gpu_b1_throughput_samples_per_s":
                    gpu_b1[
                        "throughput_samples_per_s"
                    ],

                "gpu_b1_peak_total_memory_mb":
                    gpu_b1[
                        "peak_total_memory_mb"
                    ],

                "gpu_b1_incremental_memory_mb":
                    gpu_b1[
                        "forward_incremental_memory_mb"
                    ],

                "gpu_b64_median_ms":
                    gpu_b64[
                        "median_ms"
                    ],

                "gpu_b64_mean_ms":
                    gpu_b64[
                        "mean_ms"
                    ],

                "gpu_b64_p95_ms":
                    gpu_b64[
                        "p95_ms"
                    ],

                "gpu_b64_throughput_samples_per_s":
                    gpu_b64[
                        "throughput_samples_per_s"
                    ],

                "gpu_b64_peak_total_memory_mb":
                    gpu_b64[
                        "peak_total_memory_mb"
                    ],

                "gpu_b64_incremental_memory_mb":
                    gpu_b64[
                        "forward_incremental_memory_mb"
                    ],

                "checkpoint_sha256":
                    checkpoint_hashes[
                        str(
                            checkpoint
                        )
                    ],
            }
        )


        print(
            "EFFICIENCY_PASS:",
            dataset,
            model_name,
            "params=",
            parameter_count,
            "CPU_B1_MS=",
            f"{cpu_result['median_ms']:.6f}",
            "GPU_B1_MS=",
            f"{gpu_b1['median_ms']:.6f}",
            "GPU_B64_TPUT=",
            f"{gpu_b64['throughput_samples_per_s']:.2f}",
            flush=True
        )


        del gpu_model
        del cpu_model
        del state


        torch.cuda.empty_cache()


df = pd.DataFrame(
    rows
)


output = (
    ANALYSIS /
    "efficiency_benchmark_36.csv"
)


df.to_csv(
    output,
    index=False
)


receipt = {
    "benchmark":
        "benchmark_v3r1",

    "measurement":
        "comparative_workstation_inference_efficiency",

    "seed_checkpoint":
        SEED,

    "dataset_model_measurements":
        len(df),

    "gpu":
        torch.cuda.get_device_name(
            0
        ),

    "torch_version":
        torch.__version__,

    "cpu_threads":
        torch.get_num_threads(),

    "input_shape":
        [
            128,
            6
        ],

    "gpu_batch_sizes":
        [
            1,
            64
        ],

    "cpu_batch_size":
        1,

    "checkpoint_hashes":
        checkpoint_hashes,

    "important_boundary":
        (
            "These are comparative workstation "
            "latency measurements, not embedded-device "
            "deployment latency."
        ),

    "output_sha256":
        sha256_file(
            output
        ),
}


receipt_path = (
    ANALYSIS /
    "efficiency_benchmark_receipt.json"
)


receipt_path.write_text(
    json.dumps(
        receipt,
        indent=2,
        sort_keys=True
    )
)


print()
print(
    "EFFICIENCY_MEASUREMENTS=",
    len(df)
)

print(
    "EFFICIENCY_OUTPUT=",
    output
)

print(
    "EFFICIENCY_OUTPUT_SHA256=",
    sha256_file(
        output
    )
)

print(
    "BENCHMARK_V3R1_EFFICIENCY_PASS=True"
)
