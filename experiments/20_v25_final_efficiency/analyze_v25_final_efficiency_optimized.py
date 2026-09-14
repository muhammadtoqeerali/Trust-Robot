from pathlib import Path
import hashlib
import json
import sys
import time

import numpy as np
import pandas as pd
import torch


REPO = Path.cwd()

SUITE = REPO / "experiments" / "16_benchmark_suite"
SCREEN = REPO / "experiments" / "17_v25_screening"

sys.path.insert(0, str(SUITE))
sys.path.insert(0, str(SCREEN))

from engine.model_registry import create_model
from v25_candidates import create_candidate


V25_ROOT = REPO / "results" / "v25_final_r2"
V3_ROOT = REPO / "results" / "benchmark_v3r1"

FINAL_ANALYSIS = V25_ROOT / "final_analysis"
DET_ROOT = V25_ROOT / "final_efficiency"
OUT = DET_ROOT / "optimized_inference"

FULL_RESULTS = (
    FINAL_ANALYSIS /
    "four_dataset_equal_weight_summary_10.csv"
)

HELDOUT_RESULTS = (
    FINAL_ANALYSIS /
    "heldout_equal_dataset_weight_summary_10.csv"
)

STATS = (
    FINAL_ANALYSIS /
    "v25_vs_baselines_paired_stats_144.csv"
)

V25_RECEIPT = (
    FINAL_ANALYSIS /
    "v25_final_r2_analysis_receipt.json"
)

V25_MANIFEST = (
    V25_ROOT /
    "protocol" /
    "protocol_manifest.json"
)

TCN_DIAG = (
    DET_ROOT /
    "tcn_backend_diagnostic" /
    "backend_diagnostic_summary.csv"
)


V25_MODEL = "ReliabilityCNN_v25"

BASELINES = [
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

MODELS = BASELINES + [V25_MODEL]

DATASETS = [
    "UCI_HAR",
    "PAMAP2",
    "DSADS",
    "MotionSense",
]

NUM_CLASSES = {
    "UCI_HAR": 6,
    "PAMAP2": 12,
    "DSADS": 19,
    "MotionSense": 6,
}

SEED = 42


def sha256_file(path):

    h = hashlib.sha256()

    with Path(path).open("rb") as f:

        for block in iter(
            lambda: f.read(1024 * 1024),
            b""
        ):
            h.update(block)

    return h.hexdigest()


def load_json(path):

    return json.loads(
        Path(path).read_text()
    )


def checkpoint_path(dataset, model):

    if model == V25_MODEL:

        return (
            V25_ROOT /
            "raw_runs" /
            dataset /
            model /
            f"seed_{SEED}" /
            "checkpoint.pt"
        )

    return (
        V3_ROOT /
        "raw_runs" /
        dataset /
        model /
        f"seed_{SEED}" /
        "best_model.pt"
    )


def instantiate(dataset, model):

    classes = NUM_CLASSES[dataset]

    if model == V25_MODEL:

        return create_candidate(
            "V25Dense64",
            classes,
            input_channels=6
        )

    return create_model(
        model,
        classes,
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


def cpu_measure(
    model,
    warmup=50,
    iterations=300
):

    model.eval()

    x = torch.zeros(
        1,
        128,
        6
    )

    values = []

    with torch.inference_mode():

        for _ in range(warmup):
            model(x)

        for _ in range(iterations):

            t0 = time.perf_counter()

            model(x)

            t1 = time.perf_counter()

            values.append(
                (t1 - t0) * 1000.0
            )

    arr = np.asarray(
        values,
        dtype=float
    )

    return {
        "median_ms":
            float(np.median(arr)),

        "p95_ms":
            float(np.percentile(arr, 95)),
    }


def gpu_measure(
    model,
    batch_size,
    warmup=100,
    iterations=300
):

    model.eval()

    x = torch.zeros(
        batch_size,
        128,
        6,
        device="cuda"
    )

    values = []

    with torch.inference_mode():

        for _ in range(warmup):
            model(x)

        torch.cuda.synchronize()

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

            values.append(
                float(
                    start.elapsed_time(end)
                )
            )

    arr = np.asarray(
        values,
        dtype=float
    )

    median = float(
        np.median(arr)
    )

    return {
        "median_ms":
            median,

        "p95_ms":
            float(
                np.percentile(arr, 95)
            ),

        "throughput":
            float(
                batch_size *
                1000.0 /
                median
            ),
    }


def pareto_flags(
    dataframe,
    maximize,
    minimize
):

    flags = []

    for i, candidate in dataframe.iterrows():

        dominated = False

        for j, challenger in dataframe.iterrows():

            if i == j:
                continue

            no_worse = True
            strictly_better = False

            for metric in maximize:

                if (
                    challenger[metric]
                    <
                    candidate[metric]
                ):

                    no_worse = False
                    break

                if (
                    challenger[metric]
                    >
                    candidate[metric]
                ):

                    strictly_better = True

            if not no_worse:
                continue

            for metric in minimize:

                if (
                    challenger[metric]
                    >
                    candidate[metric]
                ):

                    no_worse = False
                    break

                if (
                    challenger[metric]
                    <
                    candidate[metric]
                ):

                    strictly_better = True

            if (
                no_worse
                and
                strictly_better
            ):

                dominated = True
                break

        flags.append(
            not dominated
        )

    return flags


print("=" * 96)
print("V25 FINAL R2 — OPTIMIZED INFERENCE EFFICIENCY")
print("=" * 96)


# ------------------------------------------------------------
# Integrity
# ------------------------------------------------------------

receipt = load_json(
    V25_RECEIPT
)

if not receipt.get(
    "integrity_pass",
    False
):

    raise RuntimeError(
        "V25 final analysis receipt is not PASS"
    )


manifest = load_json(
    V25_MANIFEST
)


verified = 0

for relative, expected in (
    manifest["hashes"].items()
):

    path = REPO / relative

    if not path.exists():

        raise FileNotFoundError(
            path
        )

    actual = sha256_file(
        path
    )

    if actual != expected:

        raise RuntimeError(
            f"Frozen input changed: {relative}"
        )

    verified += 1


if not TCN_DIAG.exists():

    raise FileNotFoundError(
        TCN_DIAG
    )


diag = pd.read_csv(
    TCN_DIAG
)


tcn_det = diag[
    (
        diag["model"] == "TCN"
    )
    &
    (
        diag["backend"] == "deterministic"
    )
].iloc[0]


tcn_opt = diag[
    (
        diag["model"] == "TCN"
    )
    &
    (
        diag["backend"] == "optimized"
    )
].iloc[0]


tcn_b1_speedup = (
    tcn_det["gpu_b1_median_ms"]
    /
    tcn_opt["gpu_b1_median_ms"]
)


tcn_tput_ratio = (
    tcn_opt["gpu_b64_throughput"]
    /
    tcn_det["gpu_b64_throughput"]
)


if tcn_b1_speedup < 2.0:

    raise RuntimeError(
        "TCN backend diagnostic did not "
        "confirm large deterministic slowdown"
    )


if tcn_tput_ratio < 20.0:

    raise RuntimeError(
        "TCN backend diagnostic did not "
        "confirm throughput sensitivity"
    )


print(
    "FROZEN_HASHES_VERIFIED=",
    verified,
    "/",
    len(manifest["hashes"])
)

print(
    "TCN_BACKEND_SENSITIVITY_CONFIRMED=True"
)

print(
    "TCN_DIAGNOSTIC_B1_SPEEDUP=",
    tcn_b1_speedup
)

print(
    "TCN_DIAGNOSTIC_B64_TPUT_RATIO=",
    tcn_tput_ratio
)


# ------------------------------------------------------------
# Benchmark configuration
# ------------------------------------------------------------

if not torch.cuda.is_available():

    raise RuntimeError(
        "CUDA unavailable"
    )


torch.set_num_threads(1)

try:
    torch.set_num_interop_threads(1)
except RuntimeError:
    pass


torch.backends.cudnn.deterministic = False
torch.backends.cudnn.benchmark = True


print()
print("BENCHMARK_MODE=optimized_inference")
print(
    "CUDNN_DETERMINISTIC=",
    torch.backends.cudnn.deterministic
)
print(
    "CUDNN_BENCHMARK=",
    torch.backends.cudnn.benchmark
)
print(
    "GPU=",
    torch.cuda.get_device_name(0)
)
print(
    "TORCH=",
    torch.__version__
)
print(
    "CUDA=",
    torch.version.cuda
)
print(
    "CPU_THREADS=",
    torch.get_num_threads()
)
print("CHECKPOINT_SEED=42")
print("INPUT_SHAPE=[B,128,6]")


# ------------------------------------------------------------
# Same-session measurements
# ------------------------------------------------------------

rows = []


for dataset in DATASETS:

    for model_name in MODELS:

        ckpt = checkpoint_path(
            dataset,
            model_name
        )

        if not ckpt.exists():

            raise FileNotFoundError(
                ckpt
            )


        model = instantiate(
            dataset,
            model_name
        )


        model.load_state_dict(
            load_state(ckpt),
            strict=True
        )


        params = int(
            sum(
                p.numel()
                for p in model.parameters()
            )
        )


        checkpoint_mb = (
            ckpt.stat().st_size /
            1024.0 /
            1024.0
        )


        cpu = cpu_measure(
            model
        )


        model = model.cuda()

        torch.cuda.synchronize()


        gpu1 = gpu_measure(
            model,
            batch_size=1
        )


        gpu64 = gpu_measure(
            model,
            batch_size=64
        )


        rows.append({
            "dataset":
                dataset,

            "model":
                model_name,

            "seed":
                SEED,

            "parameters":
                params,

            "checkpoint_mb":
                checkpoint_mb,

            "checkpoint_sha256":
                sha256_file(ckpt),

            "cpu_b1_median_ms":
                cpu["median_ms"],

            "cpu_b1_p95_ms":
                cpu["p95_ms"],

            "gpu_b1_median_ms":
                gpu1["median_ms"],

            "gpu_b1_p95_ms":
                gpu1["p95_ms"],

            "gpu_b64_median_ms":
                gpu64["median_ms"],

            "gpu_b64_throughput":
                gpu64["throughput"],
        })


        print(
            "OPTIMIZED_EFFICIENCY_PASS:",
            dataset,
            model_name,
            "PARAMS=",
            params,
            "CPU_B1_MS=",
            f"{cpu['median_ms']:.6f}",
            "GPU_B1_MS=",
            f"{gpu1['median_ms']:.6f}",
            "GPU_B64_TPUT=",
            f"{gpu64['throughput']:.2f}"
        )


        del model

        torch.cuda.empty_cache()


eff = pd.DataFrame(
    rows
)


if len(eff) != 40:

    raise RuntimeError(
        f"Expected 40 rows, got {len(eff)}"
    )


eff.to_csv(
    OUT /
    "optimized_efficiency_per_dataset_40.csv",
    index=False
)


summary = (
    eff
    .groupby(
        "model",
        as_index=False
    )
    .agg(
        parameters=(
            "parameters",
            "mean"
        ),

        checkpoint_mb=(
            "checkpoint_mb",
            "mean"
        ),

        cpu_b1_median_ms=(
            "cpu_b1_median_ms",
            "mean"
        ),

        cpu_b1_p95_ms=(
            "cpu_b1_p95_ms",
            "mean"
        ),

        gpu_b1_median_ms=(
            "gpu_b1_median_ms",
            "mean"
        ),

        gpu_b1_p95_ms=(
            "gpu_b1_p95_ms",
            "mean"
        ),

        gpu_b64_median_ms=(
            "gpu_b64_median_ms",
            "mean"
        ),

        gpu_b64_throughput=(
            "gpu_b64_throughput",
            "mean"
        ),
    )
)


summary.to_csv(
    OUT /
    "optimized_efficiency_model_summary_10.csv",
    index=False
)


print()
print("=" * 96)
print("OPTIMIZED MODEL EFFICIENCY SUMMARY")
print("=" * 96)

print(
    summary
    .sort_values(
        "parameters"
    )
    .to_string(
        index=False
    )
)


# ------------------------------------------------------------
# Merge performance
# ------------------------------------------------------------

full = pd.read_csv(
    FULL_RESULTS
)

heldout = pd.read_csv(
    HELDOUT_RESULTS
)


full = full[
    [
        "model",
        "clean_macro_f1",
        "corrupted_accuracy",
        "corrupted_macro_f1",
        "reliability_score",
    ]
].rename(
    columns={
        "clean_macro_f1":
            "full_clean_macro_f1",

        "corrupted_accuracy":
            "full_corrupted_accuracy",

        "corrupted_macro_f1":
            "full_corrupted_macro_f1",

        "reliability_score":
            "full_reliability_score",
    }
)


heldout = heldout[
    [
        "model",
        "clean_macro_f1",
        "corrupted_accuracy",
        "corrupted_macro_f1",
        "reliability_score",
    ]
].rename(
    columns={
        "clean_macro_f1":
            "heldout_clean_macro_f1",

        "corrupted_accuracy":
            "heldout_corrupted_accuracy",

        "corrupted_macro_f1":
            "heldout_corrupted_macro_f1",

        "reliability_score":
            "heldout_reliability_score",
    }
)


position = (
    full
    .merge(
        heldout,
        on="model",
        how="inner"
    )
    .merge(
        summary,
        on="model",
        how="inner"
    )
)


if len(position) != 10:

    raise RuntimeError(
        "Expected 10 merged models"
    )


position[
    "pareto_robustness_parameters"
] = pareto_flags(
    position,
    maximize=[
        "full_corrupted_accuracy",
        "full_corrupted_macro_f1",
    ],
    minimize=[
        "parameters",
    ]
)


position[
    "pareto_robustness_cpu"
] = pareto_flags(
    position,
    maximize=[
        "full_corrupted_accuracy",
        "full_corrupted_macro_f1",
    ],
    minimize=[
        "cpu_b1_median_ms",
    ]
)


position[
    "pareto_robustness_gpu"
] = pareto_flags(
    position,
    maximize=[
        "full_corrupted_accuracy",
        "full_corrupted_macro_f1",
    ],
    minimize=[
        "gpu_b1_median_ms",
    ]
)


position[
    "pareto_overall"
] = pareto_flags(
    position,
    maximize=[
        "full_clean_macro_f1",
        "full_corrupted_accuracy",
        "full_corrupted_macro_f1",
    ],
    minimize=[
        "parameters",
        "cpu_b1_median_ms",
        "gpu_b1_median_ms",
    ]
)


position.to_csv(
    OUT /
    "optimized_performance_efficiency_position_10.csv",
    index=False
)


print()
print("=" * 96)
print("OPTIMIZED PERFORMANCE–EFFICIENCY POSITION")
print("=" * 96)

print(
    position[
        [
            "model",
            "full_clean_macro_f1",
            "full_corrupted_accuracy",
            "full_corrupted_macro_f1",
            "heldout_corrupted_accuracy",
            "heldout_corrupted_macro_f1",
            "parameters",
            "cpu_b1_median_ms",
            "gpu_b1_median_ms",
            "gpu_b64_throughput",
            "pareto_robustness_parameters",
            "pareto_robustness_cpu",
            "pareto_robustness_gpu",
            "pareto_overall",
        ]
    ]
    .sort_values(
        "full_corrupted_accuracy",
        ascending=False
    )
    .to_string(
        index=False
    )
)


# ------------------------------------------------------------
# V25 claim matrix under optimized inference
# ------------------------------------------------------------

stats = pd.read_csv(
    STATS
)


v25 = (
    position[
        position["model"] == V25_MODEL
    ]
    .iloc[0]
)


claim_rows = []


for baseline in BASELINES:

    base = (
        position[
            position["model"] == baseline
        ]
        .iloc[0]
    )


    comparison_stats = stats[
        stats["baseline"] == baseline
    ]


    sig_wins = int(
        np.sum(
            (
                comparison_stats[
                    "paired_t_holm"
                ]
                <
                0.05
            )
            &
            (
                comparison_stats[
                    "mean_delta_v25_minus_baseline"
                ]
                >
                0
            )
        )
    )


    sig_losses = int(
        np.sum(
            (
                comparison_stats[
                    "paired_t_holm"
                ]
                <
                0.05
            )
            &
            (
                comparison_stats[
                    "mean_delta_v25_minus_baseline"
                ]
                <
                0
            )
        )
    )


    claim_rows.append({
        "baseline":
            baseline,

        "full_clean_f1_delta":
            (
                v25[
                    "full_clean_macro_f1"
                ]
                -
                base[
                    "full_clean_macro_f1"
                ]
            ),

        "full_corrupted_accuracy_delta":
            (
                v25[
                    "full_corrupted_accuracy"
                ]
                -
                base[
                    "full_corrupted_accuracy"
                ]
            ),

        "full_corrupted_f1_delta":
            (
                v25[
                    "full_corrupted_macro_f1"
                ]
                -
                base[
                    "full_corrupted_macro_f1"
                ]
            ),

        "heldout_corrupted_accuracy_delta":
            (
                v25[
                    "heldout_corrupted_accuracy"
                ]
                -
                base[
                    "heldout_corrupted_accuracy"
                ]
            ),

        "heldout_corrupted_f1_delta":
            (
                v25[
                    "heldout_corrupted_macro_f1"
                ]
                -
                base[
                    "heldout_corrupted_macro_f1"
                ]
            ),

        "v25_parameter_ratio":
            (
                v25["parameters"]
                /
                base["parameters"]
            ),

        "v25_parameter_reduction_percent":
            (
                100.0
                *
                (
                    1.0
                    -
                    v25["parameters"]
                    /
                    base["parameters"]
                )
            ),

        "v25_cpu_latency_ratio":
            (
                v25["cpu_b1_median_ms"]
                /
                base["cpu_b1_median_ms"]
            ),

        "v25_gpu_latency_ratio":
            (
                v25["gpu_b1_median_ms"]
                /
                base["gpu_b1_median_ms"]
            ),

        "v25_gpu_b64_throughput_ratio":
            (
                v25["gpu_b64_throughput"]
                /
                base["gpu_b64_throughput"]
            ),

        "holm_paired_t_significant_wins":
            sig_wins,

        "holm_paired_t_significant_losses":
            sig_losses,
    })


claims = pd.DataFrame(
    claim_rows
)


claims.to_csv(
    OUT /
    "optimized_v25_claim_matrix_9.csv",
    index=False
)


print()
print("=" * 96)
print("OPTIMIZED V25 CLAIM MATRIX")
print("=" * 96)

print(
    claims.to_string(
        index=False
    )
)


# ------------------------------------------------------------
# Key comparisons
# ------------------------------------------------------------

print()
print("=" * 96)
print("KEY OPTIMIZED V25 COMPARISONS")
print("=" * 96)


for baseline in [
    "ReliabilityCNN_v24",
    "DeepConvLSTM",
    "TCN",
    "CNN1D",
    "DS_CNN",
]:

    row = (
        claims[
            claims["baseline"] == baseline
        ]
        .iloc[0]
    )

    print()
    print(
        "V25_vs_",
        baseline,
        sep=""
    )

    print(
        " FULL_CORR_ACC_DELTA=",
        f"{row['full_corrupted_accuracy_delta']:+.6f}"
    )

    print(
        " FULL_CORR_F1_DELTA=",
        f"{row['full_corrupted_f1_delta']:+.6f}"
    )

    print(
        " HELDOUT_CORR_ACC_DELTA=",
        f"{row['heldout_corrupted_accuracy_delta']:+.6f}"
    )

    print(
        " HELDOUT_CORR_F1_DELTA=",
        f"{row['heldout_corrupted_f1_delta']:+.6f}"
    )

    print(
        " PARAM_REDUCTION_PERCENT=",
        f"{row['v25_parameter_reduction_percent']:+.2f}"
    )

    print(
        " CPU_LATENCY_RATIO=",
        f"{row['v25_cpu_latency_ratio']:.4f}"
    )

    print(
        " GPU_LATENCY_RATIO=",
        f"{row['v25_gpu_latency_ratio']:.4f}"
    )

    print(
        " GPU_B64_TPUT_RATIO=",
        f"{row['v25_gpu_b64_throughput_ratio']:.4f}"
    )


# ------------------------------------------------------------
# Receipt
# ------------------------------------------------------------

outputs = [
    OUT /
    "optimized_efficiency_per_dataset_40.csv",

    OUT /
    "optimized_efficiency_model_summary_10.csv",

    OUT /
    "optimized_performance_efficiency_position_10.csv",

    OUT /
    "optimized_v25_claim_matrix_9.csv",
]


receipt = {
    "analysis":
        "v25_final_r2_optimized_inference_efficiency",

    "training_executed":
        False,

    "reliability_rerun":
        False,

    "inference_backend":
        {
            "cudnn_deterministic":
                False,

            "cudnn_benchmark":
                True,
        },

    "reason_for_optimized_table":
        (
            "TCN showed extreme backend sensitivity "
            "under deterministic cuDNN. Diagnostic "
            "confirmed optimized inference restores "
            "TCN performance to the independently "
            "observed ~0.44 ms / ~146k samples/s range."
        ),

    "deterministic_table_status":
        (
            "Retained as backend-sensitivity and "
            "reproducibility evidence, not discarded."
        ),

    "paper_facing_gpu_table":
        "optimized_inference",

    "measurement_boundary":
        (
            "Workstation CPU/GPU inference only. "
            "No MCU or embedded-device claim."
        ),

    "outputs":
        {
            str(
                path.relative_to(REPO)
            ):
                sha256_file(path)
            for path in outputs
        },
}


receipt_path = (
    OUT /
    "optimized_efficiency_receipt.json"
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
    "OPTIMIZED_EFFICIENCY_RECEIPT=",
    receipt_path
)

print(
    "OPTIMIZED_EFFICIENCY_RECEIPT_SHA256=",
    sha256_file(
        receipt_path
    )
)

print()
print("=" * 96)

print("OPTIMIZED_EFFICIENCY_ROWS=40")
print("OPTIMIZED_MODEL_SUMMARIES=10")
print("OPTIMIZED_CLAIM_ROWS=9")
print("TRAINING_RERUN=False")
print("RELIABILITY_RERUN=False")
print("MCU_CLAIM_ALLOWED=False")
print("PAPER_FACING_GPU_MODE=optimized_inference")
print("DETERMINISTIC_BACKEND_TABLE_PRESERVED=True")
print("V25_FINAL_OPTIMIZED_EFFICIENCY_PASS=True")

print("=" * 96)
