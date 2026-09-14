from pathlib import Path
import sys
import time
import json

import numpy as np
import pandas as pd
import torch


REPO = Path.cwd()

SUITE = (
    REPO /
    "experiments" /
    "16_benchmark_suite"
)

SCREEN = (
    REPO /
    "experiments" /
    "17_v25_screening"
)

sys.path.insert(0, str(SUITE))
sys.path.insert(0, str(SCREEN))

from engine.model_registry import create_model
from v25_candidates import create_candidate


V3 = REPO / "results" / "benchmark_v3r1"
V25 = REPO / "results" / "v25_final_r2"

OUT = (
    V25 /
    "final_efficiency" /
    "tcn_backend_diagnostic"
)

DATASET = "UCI_HAR"
SEED = 42
CLASSES = 6

MODELS = [
    "TCN",
    "DeepConvLSTM",
    "ReliabilityCNN_v24",
    "ReliabilityCNN_v25",
]


def checkpoint(model):

    if model == "ReliabilityCNN_v25":
        return (
            V25 /
            "raw_runs" /
            DATASET /
            model /
            f"seed_{SEED}" /
            "checkpoint.pt"
        )

    return (
        V3 /
        "raw_runs" /
        DATASET /
        model /
        f"seed_{SEED}" /
        "best_model.pt"
    )


def make_model(name):

    if name == "ReliabilityCNN_v25":

        return create_candidate(
            "V25Dense64",
            CLASSES,
            input_channels=6
        )

    return create_model(
        name,
        CLASSES,
        input_channels=6
    )


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


def measure(model, batch_size, warmup=80, iterations=150):

    x = torch.zeros(
        batch_size,
        128,
        6,
        device="cuda"
    )

    model.eval()

    with torch.inference_mode():

        for _ in range(warmup):
            model(x)

        torch.cuda.synchronize()

        samples = []

        for _ in range(iterations):

            start = torch.cuda.Event(
                enable_timing=True
            )

            end = torch.cuda.Event(
                enable_timing=True
            )

            start.record()
            model(x)
            end.record()

            end.synchronize()

            samples.append(
                float(
                    start.elapsed_time(end)
                )
            )

    arr = np.asarray(
        samples,
        dtype=float
    )

    median = float(
        np.median(arr)
    )

    return {
        "median_ms": median,
        "p95_ms": float(
            np.percentile(arr, 95)
        ),
        "throughput": float(
            batch_size * 1000.0 / median
        ),
    }


if not torch.cuda.is_available():
    raise RuntimeError("CUDA unavailable")


torch.set_num_threads(1)

try:
    torch.set_num_interop_threads(1)
except RuntimeError:
    pass


print("=" * 90)
print("TCN CUDA BACKEND DIAGNOSTIC")
print("=" * 90)

print("TORCH=", torch.__version__)
print("CUDA=", torch.version.cuda)
print("CUDNN=", torch.backends.cudnn.version())
print("GPU=", torch.cuda.get_device_name(0))


backend_modes = [
    {
        "name": "deterministic",
        "deterministic": True,
        "benchmark": False,
    },
    {
        "name": "optimized",
        "deterministic": False,
        "benchmark": True,
    },
]


rows = []


for backend in backend_modes:

    torch.backends.cudnn.deterministic = (
        backend["deterministic"]
    )

    torch.backends.cudnn.benchmark = (
        backend["benchmark"]
    )

    print()
    print("-" * 90)

    print(
        "BACKEND=",
        backend["name"],
        "DETERMINISTIC=",
        torch.backends.cudnn.deterministic,
        "BENCHMARK=",
        torch.backends.cudnn.benchmark,
    )

    print("-" * 90)


    for name in MODELS:

        ckpt = checkpoint(name)

        if not ckpt.exists():
            raise FileNotFoundError(ckpt)

        model = make_model(name)

        model.load_state_dict(
            load_state(ckpt),
            strict=True
        )

        model = model.cuda()

        # Run multiple rounds so one transient cannot
        # decide the conclusion.
        for repeat in range(1, 4):

            b1 = measure(
                model,
                batch_size=1
            )

            b64 = measure(
                model,
                batch_size=64
            )

            row = {
                "backend": backend["name"],
                "model": name,
                "repeat": repeat,
                "gpu_b1_median_ms":
                    b1["median_ms"],
                "gpu_b1_p95_ms":
                    b1["p95_ms"],
                "gpu_b64_median_ms":
                    b64["median_ms"],
                "gpu_b64_throughput":
                    b64["throughput"],
            }

            rows.append(row)

            print(
                "RESULT:",
                backend["name"],
                name,
                "REPEAT=",
                repeat,
                "B1_MS=",
                f"{b1['median_ms']:.6f}",
                "B64_MS=",
                f"{b64['median_ms']:.6f}",
                "B64_TPUT=",
                f"{b64['throughput']:.2f}",
            )

        del model
        torch.cuda.empty_cache()


df = pd.DataFrame(rows)

df.to_csv(
    OUT /
    "backend_diagnostic_raw.csv",
    index=False
)


summary = (
    df
    .groupby(
        [
            "backend",
            "model",
        ],
        as_index=False
    )
    .agg(
        gpu_b1_median_ms=(
            "gpu_b1_median_ms",
            "median"
        ),
        gpu_b64_median_ms=(
            "gpu_b64_median_ms",
            "median"
        ),
        gpu_b64_throughput=(
            "gpu_b64_throughput",
            "median"
        ),
    )
)


summary.to_csv(
    OUT /
    "backend_diagnostic_summary.csv",
    index=False
)


print()
print("=" * 90)
print("SUMMARY")
print("=" * 90)

print(
    summary.to_string(
        index=False
    )
)


tcn = (
    summary[
        summary["model"] == "TCN"
    ]
    .set_index("backend")
)


det_b1 = float(
    tcn.loc[
        "deterministic",
        "gpu_b1_median_ms"
    ]
)

opt_b1 = float(
    tcn.loc[
        "optimized",
        "gpu_b1_median_ms"
    ]
)

det_tput = float(
    tcn.loc[
        "deterministic",
        "gpu_b64_throughput"
    ]
)

opt_tput = float(
    tcn.loc[
        "optimized",
        "gpu_b64_throughput"
    ]
)


print()
print(
    "TCN_OPTIMIZED_VS_DETERMINISTIC_B1_SPEEDUP=",
    det_b1 / opt_b1
)

print(
    "TCN_OPTIMIZED_VS_DETERMINISTIC_B64_TPUT_RATIO=",
    opt_tput / det_tput
)


receipt = {
    "training_executed": False,
    "reliability_executed": False,
    "checkpoint_seed": SEED,
    "dataset": DATASET,
    "models": MODELS,
    "repeat_count": 3,
    "purpose":
        (
            "Diagnose large TCN GPU efficiency "
            "difference between previous and "
            "current efficiency measurements."
        ),
}


(
    OUT /
    "diagnostic_receipt.json"
).write_text(
    json.dumps(
        receipt,
        indent=2,
        sort_keys=True
    )
)


print()
print("TRAINING_RERUN=False")
print("RELIABILITY_RERUN=False")
print("TCN_BACKEND_DIAGNOSTIC_PASS=True")
