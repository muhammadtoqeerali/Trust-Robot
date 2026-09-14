from pathlib import Path
import hashlib
import json
import sys
import time

import numpy as np
import pandas as pd
import torch


REPO = Path.cwd()

EXP = (
    REPO /
    "experiments" /
    "20_v25_final_efficiency"
)

SUITE = (
    REPO /
    "experiments" /
    "16_benchmark_suite"
)

SCREEN_CODE = (
    REPO /
    "experiments" /
    "17_v25_screening"
)


sys.path.insert(
    0,
    str(SUITE)
)

sys.path.insert(
    0,
    str(SCREEN_CODE)
)


from engine.model_registry import (
    create_model
)

from v25_candidates import (
    create_candidate
)


V25_ROOT = (
    REPO /
    "results" /
    "v25_final_r2"
)

V3_ROOT = (
    REPO /
    "results" /
    "benchmark_v3r1"
)

FINAL_ANALYSIS = (
    V25_ROOT /
    "final_analysis"
)

OUT = (
    V25_ROOT /
    "final_efficiency"
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

V3_RECEIPT = (
    V3_ROOT /
    "final_analysis" /
    "benchmark_v3r1_final_integrity_receipt_r2.json"
)

FULL_RESULTS = (
    FINAL_ANALYSIS /
    "four_dataset_equal_weight_summary_10.csv"
)

HELDOUT_RESULTS = (
    FINAL_ANALYSIS /
    "heldout_equal_dataset_weight_summary_10.csv"
)

PAIRED_STATS = (
    FINAL_ANALYSIS /
    "v25_vs_baselines_paired_stats_144.csv"
)

FAMILY_RESULTS = (
    FINAL_ANALYSIS /
    "corruption_family_summary_40.csv"
)


V25_MODEL = (
    "ReliabilityCNN_v25"
)


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


MODELS = (
    BASELINES
    +
    [
        V25_MODEL
    ]
)


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


def load_json(path):

    return json.loads(
        Path(path).read_text()
    )


def sha256_file(path):

    h = hashlib.sha256()

    with Path(path).open(
        "rb"
    ) as f:

        for block in iter(
            lambda: f.read(
                1024 * 1024
            ),
            b""
        ):

            h.update(
                block
            )

    return h.hexdigest()


errors = []


def require(
    condition,
    message
):

    if not condition:

        errors.append(
            message
        )


print(
    "=" * 94
)

print(
    "V25 FINAL R2 — FINAL EFFICIENCY AND PARETO ANALYSIS"
)

print(
    "=" * 94
)


# ============================================================
# 1. INPUT EVIDENCE INTEGRITY
# ============================================================

print()
print(
    "1. INPUT EVIDENCE INTEGRITY"
)
print(
    "-" * 94
)


for path in [

    V25_RECEIPT,

    V25_MANIFEST,

    V3_RECEIPT,

    FULL_RESULTS,

    HELDOUT_RESULTS,

    PAIRED_STATS,

    FAMILY_RESULTS,

]:

    require(
        path.exists(),
        f"Missing required input: {path}"
    )


if errors:

    for error in errors:

        print(
            "ERROR:",
            error
        )

    raise SystemExit(
        3
    )


v25_receipt = load_json(
    V25_RECEIPT
)


v3_receipt = load_json(
    V3_RECEIPT
)


require(
    v25_receipt.get(
        "integrity_pass"
    )
    is True,
    "V25 final analysis receipt is not PASS"
)


require(
    v3_receipt.get(
        "integrity_pass"
    )
    is True,
    "V3R1 reference receipt is not PASS"
)


manifest = load_json(
    V25_MANIFEST
)


verified_hashes = 0


for relative, expected in (
    manifest[
        "hashes"
    ].items()
):

    path = (
        REPO /
        relative
    )


    require(
        path.exists(),
        f"Frozen input missing: {relative}"
    )


    if not path.exists():
        continue


    actual = sha256_file(
        path
    )


    require(
        actual == expected,
        f"Frozen input changed: {relative}"
    )


    if actual == expected:

        verified_hashes += 1


if errors:

    for error in errors:

        print(
            "ERROR:",
            error
        )

    raise SystemExit(
        4
    )


print(
    "V25_FINAL_FROZEN_HASHES_VERIFIED=",
    verified_hashes,
    "/",
    len(
        manifest[
            "hashes"
        ]
    )
)

print(
    "V25_ANALYSIS_RECEIPT_PASS=True"
)

print(
    "V3R1_REFERENCE_RECEIPT_PASS=True"
)


# ============================================================
# 2. MODEL CONSTRUCTION / CHECKPOINT HELPERS
# ============================================================

def checkpoint_path(
    dataset,
    model
):

    if model == V25_MODEL:

        return (

            V25_ROOT /
            "raw_runs" /
            dataset /
            V25_MODEL /
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


def instantiate(
    dataset,
    model
):

    classes = NUM_CLASSES[
        dataset
    ]


    if model == V25_MODEL:

        instance = create_candidate(

            "V25Dense64",

            classes,

            input_channels=6
        )

    else:

        instance = create_model(

            model,

            classes,

            input_channels=6
        )


    return instance


def load_state(
    path
):

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


# ============================================================
# 3. EFFICIENCY BENCHMARK SETTINGS
# ============================================================

torch.set_num_threads(
    1
)


try:

    torch.set_num_interop_threads(
        1
    )

except RuntimeError:

    pass


torch.backends.cudnn.benchmark = False

torch.backends.cudnn.deterministic = True


if not torch.cuda.is_available():

    raise RuntimeError(
        "CUDA unavailable"
    )


device = torch.device(
    "cuda:0"
)


print()
print(
    "2. BENCHMARK ENVIRONMENT"
)
print(
    "-" * 94
)


print(
    "TORCH_VERSION=",
    torch.__version__
)

print(
    "CUDA_VERSION=",
    torch.version.cuda
)

print(
    "GPU=",
    torch.cuda.get_device_name(
        0
    )
)

print(
    "CPU_THREADS=",
    torch.get_num_threads()
)

print(
    "INPUT_SHAPE=[B,128,6]"
)

print(
    "EFFICIENCY_CHECKPOINT_SEED=42"
)


# ============================================================
# 4. LATENCY FUNCTIONS
# ============================================================

def cpu_latency(
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


    with torch.inference_mode():

        for _ in range(
            warmup
        ):

            model(
                x
            )


        values = []


        for _ in range(
            iterations
        ):

            start = time.perf_counter()

            model(
                x
            )

            end = time.perf_counter()


            values.append(
                (
                    end
                    -
                    start
                )
                *
                1000.0
            )


    values = np.asarray(
        values,
        dtype=float
    )


    return {

        "median_ms":
            float(
                np.median(
                    values
                )
            ),

        "p95_ms":
            float(
                np.percentile(
                    values,
                    95
                )
            ),
    }


def gpu_latency(
    model,
    batch_size,
    warmup=80,
    iterations=300
):

    model.eval()


    x = torch.zeros(
        batch_size,
        128,
        6,
        device=device
    )


    with torch.inference_mode():

        for _ in range(
            warmup
        ):

            model(
                x
            )


        torch.cuda.synchronize()


        values = []


        for _ in range(
            iterations
        ):

            start_event = torch.cuda.Event(
                enable_timing=True
            )

            end_event = torch.cuda.Event(
                enable_timing=True
            )


            start_event.record()

            model(
                x
            )

            end_event.record()

            end_event.synchronize()


            values.append(
                float(
                    start_event.elapsed_time(
                        end_event
                    )
                )
            )


    values = np.asarray(
        values,
        dtype=float
    )


    median = float(
        np.median(
            values
        )
    )


    return {

        "median_ms":
            median,

        "p95_ms":
            float(
                np.percentile(
                    values,
                    95
                )
            ),

        "throughput_samples_per_s":
            float(
                batch_size
                *
                1000.0
                /
                median
            ),
    }


# ============================================================
# 5. RUN SAME-SESSION EFFICIENCY MEASUREMENTS
# ============================================================

print()
print(
    "3. SAME-SESSION EFFICIENCY MEASUREMENTS"
)
print(
    "-" * 94
)


rows = []


for dataset in DATASETS:

    for model_name in MODELS:

        checkpoint = checkpoint_path(
            dataset,
            model_name
        )


        require(
            checkpoint.exists(),
            f"Missing checkpoint: {checkpoint}"
        )


        if not checkpoint.exists():
            continue


        model = instantiate(
            dataset,
            model_name
        )


        state = load_state(
            checkpoint
        )


        model.load_state_dict(
            state,
            strict=True
        )


        parameters = int(
            sum(
                p.numel()
                for p in model.parameters()
            )
        )


        checkpoint_mb = (
            checkpoint.stat().st_size
            /
            1024.0
            /
            1024.0
        )


        cpu = cpu_latency(
            model
        )


        model = model.to(
            device
        )


        torch.cuda.synchronize()


        gpu1 = gpu_latency(
            model,
            batch_size=1
        )


        gpu64 = gpu_latency(
            model,
            batch_size=64
        )


        row = {

            "dataset":
                dataset,

            "model":
                model_name,

            "seed":
                SEED,

            "parameters":
                parameters,

            "checkpoint_mb":
                checkpoint_mb,

            "checkpoint_sha256":
                sha256_file(
                    checkpoint
                ),

            "cpu_b1_median_ms":
                cpu[
                    "median_ms"
                ],

            "cpu_b1_p95_ms":
                cpu[
                    "p95_ms"
                ],

            "gpu_b1_median_ms":
                gpu1[
                    "median_ms"
                ],

            "gpu_b1_p95_ms":
                gpu1[
                    "p95_ms"
                ],

            "gpu_b64_median_ms":
                gpu64[
                    "median_ms"
                ],

            "gpu_b64_throughput":
                gpu64[
                    "throughput_samples_per_s"
                ],
        }


        rows.append(
            row
        )


        print(
            "EFFICIENCY_PASS:",
            dataset,
            model_name,
            "PARAMS=",
            parameters,
            "CPU_B1_MS=",
            f"{cpu['median_ms']:.6f}",
            "GPU_B1_MS=",
            f"{gpu1['median_ms']:.6f}",
            "GPU_B64_TPUT=",
            f"{gpu64['throughput_samples_per_s']:.2f}"
        )


        del model

        torch.cuda.empty_cache()


if errors:

    for error in errors:

        print(
            "ERROR:",
            error
        )

    raise SystemExit(
        5
    )


eff = pd.DataFrame(
    rows
)


require(
    len(
        eff
    )
    ==
    40,
    f"Expected 40 efficiency rows, got {len(eff)}"
)


if errors:

    for error in errors:

        print(
            "ERROR:",
            error
        )

    raise SystemExit(
        6
    )


eff.to_csv(
    OUT /
    "efficiency_per_dataset_40.csv",
    index=False
)


# ============================================================
# 6. MODEL-LEVEL EFFICIENCY SUMMARY
# ============================================================

eff_summary = (
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


eff_summary.to_csv(
    OUT /
    "efficiency_model_summary_10.csv",
    index=False
)


print()
print(
    "4. MODEL-LEVEL EFFICIENCY SUMMARY"
)
print(
    "-" * 94
)


print(
    eff_summary
    .sort_values(
        "parameters"
    )
    .to_string(
        index=False
    )
)


# ============================================================
# 7. MERGE FINAL PERFORMANCE + HELDOUT + EFFICIENCY
# ============================================================

full = pd.read_csv(
    FULL_RESULTS
)


heldout = pd.read_csv(
    HELDOUT_RESULTS
)


full_keep = full[
    [
        "model",
        "clean_accuracy",
        "clean_macro_f1",
        "reliability_score",
        "corrupted_accuracy",
        "corrupted_macro_f1",
        "clean_accuracy_rank",
        "clean_macro_f1_rank",
        "corrupted_accuracy_rank",
        "corrupted_macro_f1_rank",
        "reliability_score_rank",
    ]
].copy()


full_keep = full_keep.rename(
    columns={
        column:
            (
                column
                if column == "model"
                else
                f"full_{column}"
            )
        for column in full_keep.columns
    }
)


heldout_keep = heldout[
    [
        "model",
        "clean_accuracy",
        "clean_macro_f1",
        "reliability_score",
        "corrupted_accuracy",
        "corrupted_macro_f1",
        "clean_accuracy_rank",
        "clean_macro_f1_rank",
        "corrupted_accuracy_rank",
        "corrupted_macro_f1_rank",
        "reliability_score_rank",
    ]
].copy()


heldout_keep = heldout_keep.rename(
    columns={
        column:
            (
                column
                if column == "model"
                else
                f"heldout_{column}"
            )
        for column in heldout_keep.columns
    }
)


position = (
    full_keep
    .merge(
        heldout_keep,
        on="model",
        how="inner"
    )
    .merge(
        eff_summary,
        on="model",
        how="inner"
    )
)


require(
    len(
        position
    )
    ==
    10,
    f"Expected 10 merged models, got {len(position)}"
)


# ============================================================
# 8. PARETO ANALYSIS — NO COMPOSITE SCORE
# ============================================================

def pareto_flags(
    dataframe,
    maximize,
    minimize
):

    result = []


    for index, candidate in (
        dataframe.iterrows()
    ):

        dominated = False


        for challenger_index, challenger in (
            dataframe.iterrows()
        ):

            if index == challenger_index:
                continue


            no_worse = True

            strictly_better = False


            for metric in maximize:

                if (
                    challenger[
                        metric
                    ]
                    <
                    candidate[
                        metric
                    ]
                ):

                    no_worse = False

                    break


                if (
                    challenger[
                        metric
                    ]
                    >
                    candidate[
                        metric
                    ]
                ):

                    strictly_better = True


            if not no_worse:
                continue


            for metric in minimize:

                if (
                    challenger[
                        metric
                    ]
                    >
                    candidate[
                        metric
                    ]
                ):

                    no_worse = False

                    break


                if (
                    challenger[
                        metric
                    ]
                    <
                    candidate[
                        metric
                    ]
                ):

                    strictly_better = True


            if (
                no_worse
                and
                strictly_better
            ):

                dominated = True

                break


        result.append(
            not dominated
        )


    return result


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
    "final_performance_efficiency_position_10.csv",
    index=False
)


print()
print(
    "5. PERFORMANCE–EFFICIENCY POSITION"
)
print(
    "-" * 94
)


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


# ============================================================
# 9. V25 VS EVERY BASELINE — CLAIM MATRIX
# ============================================================

stats = pd.read_csv(
    PAIRED_STATS
)


v25 = (
    position[
        position[
            "model"
        ]
        ==
        V25_MODEL
    ]
    .iloc[
        0
    ]
)


claim_rows = []


for baseline in BASELINES:

    base = (
        position[
            position[
                "model"
            ]
            ==
            baseline
        ]
        .iloc[
            0
        ]
    )


    comparison_stats = stats[
        stats[
            "baseline"
        ]
        ==
        baseline
    ]


    significant_t_wins = int(
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


    significant_t_losses = int(
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


    claim_rows.append(
        {

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

            "heldout_clean_f1_delta":
                (
                    v25[
                        "heldout_clean_macro_f1"
                    ]
                    -
                    base[
                        "heldout_clean_macro_f1"
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
                    v25[
                        "parameters"
                    ]
                    /
                    base[
                        "parameters"
                    ]
                ),

            "v25_parameter_reduction_percent":
                (
                    100.0
                    *
                    (
                        1.0
                        -
                        (
                            v25[
                                "parameters"
                            ]
                            /
                            base[
                                "parameters"
                            ]
                        )
                    )
                ),

            "v25_cpu_latency_ratio":
                (
                    v25[
                        "cpu_b1_median_ms"
                    ]
                    /
                    base[
                        "cpu_b1_median_ms"
                    ]
                ),

            "v25_gpu_latency_ratio":
                (
                    v25[
                        "gpu_b1_median_ms"
                    ]
                    /
                    base[
                        "gpu_b1_median_ms"
                    ]
                ),

            "v25_gpu_b64_throughput_ratio":
                (
                    v25[
                        "gpu_b64_throughput"
                    ]
                    /
                    base[
                        "gpu_b64_throughput"
                    ]
                ),

            "holm_paired_t_significant_wins":
                significant_t_wins,

            "holm_paired_t_significant_losses":
                significant_t_losses,
        }
    )


claim_matrix = pd.DataFrame(
    claim_rows
)


claim_matrix.to_csv(
    OUT /
    "v25_vs_baselines_claim_matrix_9.csv",
    index=False
)


print()
print(
    "6. V25 VS BASELINES — CLAIM MATRIX"
)
print(
    "-" * 94
)


print(
    claim_matrix.to_string(
        index=False
    )
)


# ============================================================
# 10. KEY V25 COMPARISONS
# ============================================================

print()
print(
    "7. KEY V25 COMPARISONS"
)
print(
    "-" * 94
)


for baseline in [

    "ReliabilityCNN_v24",

    "DeepConvLSTM",

    "TCN",

    "CNN1D",

    "DS_CNN",
]:

    row = (
        claim_matrix[
            claim_matrix[
                "baseline"
            ]
            ==
            baseline
        ]
        .iloc[
            0
        ]
    )


    print()

    print(
        "V25_vs_",
        baseline,
        sep=""
    )


    print(
        "  FULL_CORR_ACC_DELTA=",
        f"{row['full_corrupted_accuracy_delta']:+.6f}"
    )

    print(
        "  FULL_CORR_F1_DELTA=",
        f"{row['full_corrupted_f1_delta']:+.6f}"
    )

    print(
        "  HELDOUT_CORR_ACC_DELTA=",
        f"{row['heldout_corrupted_accuracy_delta']:+.6f}"
    )

    print(
        "  HELDOUT_CORR_F1_DELTA=",
        f"{row['heldout_corrupted_f1_delta']:+.6f}"
    )

    print(
        "  PARAMETER_RATIO=",
        f"{row['v25_parameter_ratio']:.4f}"
    )

    print(
        "  PARAMETER_REDUCTION_PERCENT=",
        f"{row['v25_parameter_reduction_percent']:+.2f}"
    )

    print(
        "  CPU_LATENCY_RATIO=",
        f"{row['v25_cpu_latency_ratio']:.4f}"
    )

    print(
        "  GPU_LATENCY_RATIO=",
        f"{row['v25_gpu_latency_ratio']:.4f}"
    )

    print(
        "  GPU_B64_THROUGHPUT_RATIO=",
        f"{row['v25_gpu_b64_throughput_ratio']:.4f}"
    )

    print(
        "  HOLM_T_SIGNIFICANT_WINS=",
        int(
            row[
                "holm_paired_t_significant_wins"
            ]
        )
    )

    print(
        "  HOLM_T_SIGNIFICANT_LOSSES=",
        int(
            row[
                "holm_paired_t_significant_losses"
            ]
        )
    )


# ============================================================
# 11. V25 FAMILY POSITION
# ============================================================

family = pd.read_csv(
    FAMILY_RESULTS
)


v25_family = family[
    family[
        "model"
    ]
    ==
    V25_MODEL
].copy()


v25_family.to_csv(
    OUT /
    "v25_family_position.csv",
    index=False
)


print()
print(
    "8. V25 CORRUPTION-FAMILY POSITION"
)
print(
    "-" * 94
)


print(
    v25_family.to_string(
        index=False
    )
)


# ============================================================
# 12. FINAL RECEIPT
# ============================================================

outputs = [

    OUT /
    "efficiency_per_dataset_40.csv",

    OUT /
    "efficiency_model_summary_10.csv",

    OUT /
    "final_performance_efficiency_position_10.csv",

    OUT /
    "v25_vs_baselines_claim_matrix_9.csv",

    OUT /
    "v25_family_position.csv",
]


receipt = {

    "analysis":
        "v25_final_r2_efficiency_and_pareto",

    "training_executed":
        False,

    "reliability_rerun":
        False,

    "model_execution":
        "inference_only_efficiency_measurement",

    "efficiency_environment":
        {

            "device":
                torch.cuda.get_device_name(
                    0
                ),

            "torch_version":
                torch.__version__,

            "cuda_version":
                torch.version.cuda,

            "cpu_threads":
                torch.get_num_threads(),

            "checkpoint_seed":
                SEED,

            "input_shape":
                [
                    128,
                    6
                ],
        },

    "measurement_boundary":
        (
            "CPU/GPU workstation measurements only. "
            "These results do not constitute MCU or "
            "embedded-device latency evidence."
        ),

    "pareto_boundary":
        (
            "No arbitrary weighted composite score "
            "was used. Pareto fronts are reported "
            "directly over robustness and efficiency "
            "objectives."
        ),

    "v25_final_analysis_receipt_sha256":
        sha256_file(
            V25_RECEIPT
        ),

    "v3r1_reference_receipt_sha256":
        sha256_file(
            V3_RECEIPT
        ),

    "outputs":
        {
            str(
                path.relative_to(
                    REPO
                )
            ):
                sha256_file(
                    path
                )
            for path in outputs
        },
}


receipt_path = (
    OUT /
    "v25_final_efficiency_receipt.json"
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
    "FINAL_EFFICIENCY_RECEIPT=",
    receipt_path
)

print(
    "FINAL_EFFICIENCY_RECEIPT_SHA256=",
    sha256_file(
        receipt_path
    )
)


print()
print(
    "=" * 94
)

print(
    "EFFICIENCY_MEASUREMENTS=40"
)

print(
    "MODEL_SUMMARIES=10"
)

print(
    "CLAIM_MATRIX_ROWS=9"
)

print(
    "TRAINING_RERUN=False"
)

print(
    "RELIABILITY_RERUN=False"
)

print(
    "MCU_CLAIM_ALLOWED=False"
)

print(
    "V25_FINAL_EFFICIENCY_AND_PARETO_PASS=True"
)

print(
    "=" * 94
)
