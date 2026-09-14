from pathlib import Path
import hashlib
import json
import sys
import time

import numpy as np
import pandas as pd
import torch


REPO = Path.cwd()

SCREEN = (
    REPO /
    "experiments" /
    "17_v25_screening"
)

SUITE = (
    REPO /
    "experiments" /
    "16_benchmark_suite"
)

sys.path.insert(
    0,
    str(SCREEN)
)

sys.path.insert(
    0,
    str(SUITE)
)


from v25_candidates import (
    create_candidate
)

from engine.model_registry import (
    create_model
)


ROOT = (
    REPO /
    "results" /
    "v25_screening_r1"
)

RAW = ROOT / "raw_runs"

REL = ROOT / "reliability_v2"

OUT = ROOT / "final_analysis"


V3ROOT = (
    REPO /
    "results" /
    "benchmark_v3r1"
)


MANIFEST = (
    ROOT /
    "protocol" /
    "protocol_manifest.json"
)


REGISTRY = (
    REPO /
    "configs" /
    "reliability" /
    "corruption_registry_v2.json"
)


DATASETS = [
    "UCI_HAR",
    "DSADS",
]


NUM_CLASSES = {
    "UCI_HAR": 6,
    "DSADS": 19,
}


SEEDS = [
    42,
    123,
    456,
]


CANDIDATES = [
    "V25Dense64",
    "V25DS96",
]


METHODS = [
    "ReliabilityCNN_v24",
    "V25Dense64",
    "V25DS96",
]


FAMILIES = [
    "missing_channel",
    "random_dropout",
    "gaussian_noise",
    "sensor_drift",
]


EXPECTED_FAMILY_CASES = {
    "missing_channel": 6,
    "random_dropout": 9,
    "gaussian_noise": 9,
    "sensor_drift": 9,
}


def load_json(path):

    return json.loads(
        Path(path).read_text()
    )


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


def mean_std(values):

    values = np.asarray(
        values,
        dtype=float
    )

    return (
        float(
            np.mean(values)
        ),
        float(
            np.std(
                values,
                ddof=1
            )
        )
        if len(values) > 1
        else 0.0
    )


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
    "=" * 80
)

print(
    "V25 SCREENING R1 FINAL ANALYSIS"
)

print(
    "=" * 80
)


# ==========================================================
# 1. PROTOCOL INTEGRITY
# ==========================================================

print()
print(
    "1. SCREENING PROTOCOL INTEGRITY"
)
print(
    "-" * 80
)


require(
    MANIFEST.exists(),
    f"Missing manifest: {MANIFEST}"
)


manifest = load_json(
    MANIFEST
)


protocol_sha = sha256_file(
    MANIFEST
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
        f"Missing frozen file: {path}"
    )


    if not path.exists():
        continue


    actual = sha256_file(
        path
    )


    require(
        actual == expected,
        (
            f"Frozen SHA mismatch: "
            f"{relative}"
        )
    )


    if actual == expected:

        verified_hashes += 1


print(
    "PROTOCOL_SHA256=",
    protocol_sha
)

print(
    "FROZEN_HASHES_EXPECTED=",
    len(
        manifest[
            "hashes"
        ]
    )
)

print(
    "FROZEN_HASHES_VERIFIED=",
    verified_hashes
)


# ==========================================================
# 2. SCREENING RUN INTEGRITY
# ==========================================================

print()
print(
    "2. VERIFY 12 TRAINING + 12 RELIABILITY RUNS"
)
print(
    "-" * 80
)


training_verified = 0

reliability_verified = 0


for dataset in DATASETS:

    for candidate in CANDIDATES:

        for seed in SEEDS:

            run_dir = (
                RAW /
                dataset /
                candidate /
                f"seed_{seed}"
            )


            required = [

                run_dir /
                "COMPLETE",

                run_dir /
                "best_model.pt",

                run_dir /
                "metrics.json",

                run_dir /
                "history.json",

                run_dir /
                "receipt.json",
            ]


            for path in required:

                require(
                    path.exists(),
                    f"Missing training artifact: {path}"
                )


            if all(
                path.exists()
                for path in required
            ):

                receipt = load_json(
                    run_dir /
                    "receipt.json"
                )


                require(
                    receipt.get(
                        "protocol_manifest_sha256"
                    )
                    ==
                    protocol_sha,
                    (
                        "Training protocol SHA mismatch: "
                        f"{dataset}/{candidate}/{seed}"
                    )
                )


                require(
                    receipt.get(
                        "checkpoint_sha256"
                    )
                    ==
                    sha256_file(
                        run_dir /
                        "best_model.pt"
                    ),
                    (
                        "Training checkpoint SHA mismatch: "
                        f"{dataset}/{candidate}/{seed}"
                    )
                )


                training_verified += 1


            rel_dir = (
                REL /
                dataset /
                candidate /
                f"seed_{seed}"
            )


            rel_required = [

                rel_dir /
                "COMPLETE",

                rel_dir /
                "reliability_summary_v2.json",

                rel_dir /
                "screening_receipt.json",
            ]


            for path in rel_required:

                require(
                    path.exists(),
                    f"Missing reliability artifact: {path}"
                )


            if all(
                path.exists()
                for path in rel_required
            ):

                receipt = load_json(
                    rel_dir /
                    "screening_receipt.json"
                )


                summary = load_json(
                    rel_dir /
                    "reliability_summary_v2.json"
                )


                require(
                    receipt.get(
                        "protocol_manifest_sha256"
                    )
                    ==
                    protocol_sha,
                    (
                        "Reliability protocol SHA mismatch: "
                        f"{dataset}/{candidate}/{seed}"
                    )
                )


                require(
                    receipt.get(
                        "checkpoint_sha256"
                    )
                    ==
                    sha256_file(
                        run_dir /
                        "best_model.pt"
                    ),
                    (
                        "Reliability checkpoint linkage "
                        f"failure: "
                        f"{dataset}/{candidate}/{seed}"
                    )
                )


                require(
                    receipt.get(
                        "registry_sha256"
                    )
                    ==
                    sha256_file(
                        REGISTRY
                    ),
                    (
                        "Registry SHA mismatch: "
                        f"{dataset}/{candidate}/{seed}"
                    )
                )


                require(
                    receipt.get(
                        "summary_sha256"
                    )
                    ==
                    sha256_file(
                        rel_dir /
                        "reliability_summary_v2.json"
                    ),
                    (
                        "Summary SHA mismatch: "
                        f"{dataset}/{candidate}/{seed}"
                    )
                )


                require(
                    summary.get(
                        "protocol_version"
                    )
                    ==
                    "v2",
                    (
                        "Wrong reliability protocol: "
                        f"{dataset}/{candidate}/{seed}"
                    )
                )


                require(
                    summary.get(
                        "n_corrupted_cases"
                    )
                    ==
                    33,
                    (
                        "Wrong corruption case count: "
                        f"{dataset}/{candidate}/{seed}"
                    )
                )


                families = summary.get(
                    "family_summaries",
                    {}
                )


                for family, expected_count in (
                    EXPECTED_FAMILY_CASES.items()
                ):

                    require(
                        family in families,
                        (
                            "Missing family: "
                            f"{dataset}/{candidate}/{seed}/"
                            f"{family}"
                        )
                    )


                    if family in families:

                        require(
                            families[
                                family
                            ].get(
                                "n_cases"
                            )
                            ==
                            expected_count,
                            (
                                "Wrong family case count: "
                                f"{dataset}/{candidate}/{seed}/"
                                f"{family}"
                            )
                        )


                reliability_verified += 1


print(
    "TRAINING_VERIFIED=",
    training_verified,
    "/12"
)

print(
    "RELIABILITY_VERIFIED=",
    reliability_verified,
    "/12"
)


if errors:

    print(
        "SCREENING_INTEGRITY_PASS=False"
    )

    print(
        "ERROR_COUNT=",
        len(errors)
    )

    for error in errors:

        print(
            "ERROR:",
            error
        )

    raise SystemExit(3)


print(
    "ERROR_COUNT=0"
)

print(
    "SCREENING_INTEGRITY_PASS=True"
)


# ==========================================================
# 3. LOAD SCREEN + SAME-SEED V24 REFERENCE
# ==========================================================

print()
print(
    "3. LOAD SCREEN + EXACT SAME-SEED V24 REFERENCE"
)
print(
    "-" * 80
)


rows = []

family_rows = []


for dataset in DATASETS:

    for method in METHODS:

        for seed in SEEDS:

            if method == "ReliabilityCNN_v24":

                run_dir = (
                    V3ROOT /
                    "raw_runs" /
                    dataset /
                    method /
                    f"seed_{seed}"
                )


                rel_dir = (
                    V3ROOT /
                    "reliability_v2" /
                    dataset /
                    method /
                    f"seed_{seed}"
                )


                training_protocol = (
                    "V3R1_reliability_exposure_"
                    "consistency_unavailable"
                )

            else:

                run_dir = (
                    RAW /
                    dataset /
                    method /
                    f"seed_{seed}"
                )


                rel_dir = (
                    REL /
                    dataset /
                    method /
                    f"seed_{seed}"
                )


                training_protocol = (
                    "clean_CE_architecture_screen"
                )


            metrics = load_json(
                run_dir /
                "metrics.json"
            )


            summary = load_json(
                rel_dir /
                "reliability_summary_v2.json"
            )


            overall = summary[
                "overall"
            ]


            test = metrics[
                "test"
            ]


            rows.append(
                {
                    "dataset":
                        dataset,

                    "method":
                        method,

                    "seed":
                        seed,

                    "training_protocol":
                        training_protocol,

                    "clean_accuracy":
                        float(
                            test[
                                "accuracy"
                            ]
                        ),

                    "clean_macro_f1":
                        float(
                            test[
                                "macro_f1"
                            ]
                        ),

                    "reliability_score":
                        float(
                            overall[
                                "reliability_score"
                            ]
                        ),

                    "corrupted_accuracy":
                        float(
                            overall[
                                "corrupted_accuracy"
                            ]
                        ),

                    "corrupted_macro_f1":
                        float(
                            overall[
                                "corrupted_macro_f1"
                            ]
                        ),

                    "relative_accuracy_degradation":
                        float(
                            overall[
                                "relative_accuracy_degradation"
                            ]
                        ),

                    "relative_macro_f1_degradation":
                        float(
                            overall[
                                "relative_macro_f1_degradation"
                            ]
                        ),

                    "parameters":
                        int(
                            metrics[
                                "parameters"
                            ]
                        ),
                }
            )


            for family in FAMILIES:

                family_data = (
                    summary[
                        "family_summaries"
                    ][
                        family
                    ]
                )


                family_rows.append(
                    {
                        "dataset":
                            dataset,

                        "method":
                            method,

                        "seed":
                            seed,

                        "family":
                            family,

                        "reliability_score":
                            float(
                                family_data[
                                    "reliability_score_mean"
                                ]
                            ),

                        "corrupted_accuracy":
                            float(
                                family_data[
                                    "corrupted_accuracy_mean"
                                ]
                            ),

                        "corrupted_macro_f1":
                            float(
                                family_data[
                                    "corrupted_macro_f1_mean"
                                ]
                            ),

                        "relative_accuracy_degradation":
                            float(
                                family_data[
                                    "relative_accuracy_degradation_mean"
                                ]
                            ),

                        "relative_macro_f1_degradation":
                            float(
                                family_data[
                                    "relative_macro_f1_degradation_mean"
                                ]
                            ),
                    }
                )


per_seed = pd.DataFrame(
    rows
)


family_seed = pd.DataFrame(
    family_rows
)


per_seed.to_csv(
    OUT /
    "screening_per_seed_18.csv",
    index=False
)


family_seed.to_csv(
    OUT /
    "screening_family_per_seed_72.csv",
    index=False
)


print(
    "PER_SEED_ROWS=",
    len(per_seed)
)

print(
    "FAMILY_SEED_ROWS=",
    len(family_seed)
)


# ==========================================================
# 4. DATASET × METHOD SUMMARY
# ==========================================================

summary_rows = []


for (
    dataset,
    method
), group in per_seed.groupby(
    [
        "dataset",
        "method"
    ],
    sort=False
):

    row = {
        "dataset":
            dataset,

        "method":
            method,

        "n_seeds":
            len(group),

        "parameters":
            float(
                group[
                    "parameters"
                ].mean()
            ),
    }


    for metric in [

        "clean_accuracy",

        "clean_macro_f1",

        "reliability_score",

        "corrupted_accuracy",

        "corrupted_macro_f1",

        "relative_accuracy_degradation",

        "relative_macro_f1_degradation",
    ]:

        mean, std = mean_std(
            group[
                metric
            ].to_numpy()
        )


        row[
            f"{metric}_mean"
        ] = mean

        row[
            f"{metric}_std"
        ] = std


    summary_rows.append(
        row
    )


dataset_summary = pd.DataFrame(
    summary_rows
)


dataset_summary.to_csv(
    OUT /
    "dataset_method_summary_6.csv",
    index=False
)


print()
print(
    "4. DATASET × METHOD RESULTS"
)
print(
    "-" * 80
)


print(
    dataset_summary[
        [
            "dataset",
            "method",
            "clean_accuracy_mean",
            "clean_macro_f1_mean",
            "corrupted_accuracy_mean",
            "corrupted_macro_f1_mean",
            "reliability_score_mean",
            "parameters",
        ]
    ]
    .sort_values(
        [
            "dataset",
            "corrupted_accuracy_mean"
        ],
        ascending=[
            True,
            False
        ]
    )
    .to_string(
        index=False
    )
)


# ==========================================================
# 5. EQUAL DATASET WEIGHT SUMMARY
# ==========================================================

cross_rows = []


for method, group in dataset_summary.groupby(
    "method",
    sort=False
):

    row = {
        "method":
            method,

        "dataset_count":
            len(group),

        "parameters":
            float(
                group[
                    "parameters"
                ].mean()
            ),
    }


    for metric in [

        "clean_accuracy_mean",

        "clean_macro_f1_mean",

        "reliability_score_mean",

        "corrupted_accuracy_mean",

        "corrupted_macro_f1_mean",

        "relative_accuracy_degradation_mean",

        "relative_macro_f1_degradation_mean",
    ]:

        row[
            metric.replace(
                "_mean",
                "_dataset_macro_mean"
            )
        ] = float(
            group[
                metric
            ].mean()
        )


    cross_rows.append(
        row
    )


cross = pd.DataFrame(
    cross_rows
)


cross.to_csv(
    OUT /
    "cross_dataset_screening_summary_3.csv",
    index=False
)


print()
print(
    "5. TWO-DATASET SCREENING SUMMARY"
)
print(
    "-" * 80
)


print(
    cross[
        [
            "method",
            "clean_accuracy_dataset_macro_mean",
            "clean_macro_f1_dataset_macro_mean",
            "reliability_score_dataset_macro_mean",
            "corrupted_accuracy_dataset_macro_mean",
            "corrupted_macro_f1_dataset_macro_mean",
            "parameters",
        ]
    ]
    .sort_values(
        "corrupted_accuracy_dataset_macro_mean",
        ascending=False
    )
    .to_string(
        index=False
    )
)


# ==========================================================
# 6. FAMILY SUMMARY
# ==========================================================

family_cross_rows = []


for (
    family,
    method
), group in family_seed.groupby(
    [
        "family",
        "method"
    ],
    sort=False
):

    family_cross_rows.append(
        {
            "family":
                family,

            "method":
                method,

            "n_dataset_seed_points":
                len(group),

            "reliability_score":
                float(
                    group[
                        "reliability_score"
                    ].mean()
                ),

            "corrupted_accuracy":
                float(
                    group[
                        "corrupted_accuracy"
                    ].mean()
                ),

            "corrupted_macro_f1":
                float(
                    group[
                        "corrupted_macro_f1"
                    ].mean()
                ),

            "relative_accuracy_degradation":
                float(
                    group[
                        "relative_accuracy_degradation"
                    ].mean()
                ),

            "relative_macro_f1_degradation":
                float(
                    group[
                        "relative_macro_f1_degradation"
                    ].mean()
                ),
        }
    )


family_cross = pd.DataFrame(
    family_cross_rows
)


family_cross[
    "corrupted_accuracy_rank"
] = (
    family_cross
    .groupby(
        "family"
    )[
        "corrupted_accuracy"
    ]
    .rank(
        ascending=False,
        method="average"
    )
)


family_cross[
    "corrupted_macro_f1_rank"
] = (
    family_cross
    .groupby(
        "family"
    )[
        "corrupted_macro_f1"
    ]
    .rank(
        ascending=False,
        method="average"
    )
)


family_cross.to_csv(
    OUT /
    "family_screening_summary_12.csv",
    index=False
)


print()
print(
    "6. CORRUPTION FAMILY RESULTS"
)
print(
    "-" * 80
)


print(
    family_cross[
        [
            "family",
            "method",
            "corrupted_accuracy",
            "corrupted_macro_f1",
            "reliability_score",
            "corrupted_accuracy_rank",
            "corrupted_macro_f1_rank",
        ]
    ]
    .sort_values(
        [
            "family",
            "corrupted_accuracy_rank"
        ]
    )
    .to_string(
        index=False
    )
)


# ==========================================================
# 7. SAME-SESSION EFFICIENCY
# ==========================================================

print()
print(
    "7. SAME-SESSION EFFICIENCY BENCHMARK"
)
print(
    "-" * 80
)


if not torch.cuda.is_available():

    raise RuntimeError(
        "CUDA unavailable"
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


device = torch.device(
    "cuda:0"
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


def create_method_model(
    method,
    dataset
):

    classes = NUM_CLASSES[
        dataset
    ]


    if method == "ReliabilityCNN_v24":

        model = create_model(
            method,
            classes,
            input_channels=6
        )


        checkpoint = (
            V3ROOT /
            "raw_runs" /
            dataset /
            method /
            "seed_42" /
            "best_model.pt"
        )

    else:

        model = create_candidate(
            method,
            classes,
            input_channels=6
        )


        checkpoint = (
            RAW /
            dataset /
            method /
            "seed_42" /
            "best_model.pt"
        )


    state = load_state(
        checkpoint
    )


    model.load_state_dict(
        state,
        strict=True
    )


    return (
        model,
        checkpoint
    )


def cpu_latency(
    model,
    warmup=30,
    iterations=150
):

    x = torch.zeros(
        1,
        128,
        6
    )


    model.eval()


    with torch.inference_mode():

        for _ in range(
            warmup
        ):

            model(
                x
            )


        measurements = []


        for _ in range(
            iterations
        ):

            start = time.perf_counter()

            model(
                x
            )

            measurements.append(
                (
                    time.perf_counter()
                    -
                    start
                )
                *
                1000.0
            )


    return {

        "median_ms":
            float(
                np.median(
                    measurements
                )
            ),

        "p95_ms":
            float(
                np.percentile(
                    measurements,
                    95
                )
            ),
    }


def gpu_latency(
    model,
    batch_size,
    warmup=40,
    iterations=180
):

    x = torch.zeros(
        batch_size,
        128,
        6,
        device=device
    )


    model.eval()


    with torch.inference_mode():

        for _ in range(
            warmup
        ):

            model(
                x
            )


        torch.cuda.synchronize()


        measurements = []


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

            model(
                x
            )

            end.record()

            end.synchronize()


            measurements.append(
                float(
                    start.elapsed_time(
                        end
                    )
                )
            )


    median = float(
        np.median(
            measurements
        )
    )


    return {

        "median_ms":
            median,

        "p95_ms":
            float(
                np.percentile(
                    measurements,
                    95
                )
            ),

        "throughput":
            float(
                batch_size
                *
                1000.0
                /
                median
            ),
    }


eff_rows = []


for dataset in DATASETS:

    for method in METHODS:

        model, checkpoint = (
            create_method_model(
                method,
                dataset
            )
        )


        parameters = sum(
            p.numel()
            for p in model.parameters()
        )


        checkpoint_mb = (
            checkpoint.stat().st_size
            /
            1024
            /
            1024
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
            1
        )


        gpu64 = gpu_latency(
            model,
            64
        )


        row = {

            "dataset":
                dataset,

            "method":
                method,

            "seed":
                42,

            "parameters":
                parameters,

            "checkpoint_size_mb":
                checkpoint_mb,

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
                    "throughput"
                ],
        }


        eff_rows.append(
            row
        )


        print(
            "EFFICIENCY_PASS:",
            dataset,
            method,
            "PARAMS=",
            parameters,
            "CPU_MS=",
            f"{cpu['median_ms']:.6f}",
            "GPU_MS=",
            f"{gpu1['median_ms']:.6f}",
            "GPU_B64_TPUT=",
            f"{gpu64['throughput']:.2f}"
        )


        del model

        torch.cuda.empty_cache()


eff = pd.DataFrame(
    eff_rows
)


eff.to_csv(
    OUT /
    "same_session_efficiency_6.csv",
    index=False
)


eff_cross = (
    eff
    .groupby(
        "method",
        as_index=False
    )
    .agg(

        parameters=(
            "parameters",
            "mean"
        ),

        checkpoint_size_mb=(
            "checkpoint_size_mb",
            "mean"
        ),

        cpu_b1_median_ms=(
            "cpu_b1_median_ms",
            "mean"
        ),

        gpu_b1_median_ms=(
            "gpu_b1_median_ms",
            "mean"
        ),

        gpu_b64_throughput=(
            "gpu_b64_throughput",
            "mean"
        ),
    )
)


eff_cross.to_csv(
    OUT /
    "same_session_efficiency_summary_3.csv",
    index=False
)


# ==========================================================
# 8. DECISION MATRIX
# ==========================================================

decision = cross.merge(
    eff_cross,
    on="method",
    how="inner",
    suffixes=(
        "",
        "_eff"
    )
)


v24 = decision[
    decision[
        "method"
    ]
    ==
    "ReliabilityCNN_v24"
].iloc[
    0
]


decision[
    "clean_f1_delta_vs_v24"
] = (
    decision[
        "clean_macro_f1_dataset_macro_mean"
    ]
    -
    v24[
        "clean_macro_f1_dataset_macro_mean"
    ]
)


decision[
    "corrupted_accuracy_delta_vs_v24"
] = (
    decision[
        "corrupted_accuracy_dataset_macro_mean"
    ]
    -
    v24[
        "corrupted_accuracy_dataset_macro_mean"
    ]
)


decision[
    "corrupted_f1_delta_vs_v24"
] = (
    decision[
        "corrupted_macro_f1_dataset_macro_mean"
    ]
    -
    v24[
        "corrupted_macro_f1_dataset_macro_mean"
    ]
)


decision[
    "parameter_reduction_vs_v24_percent"
] = (
    100.0
    *
    (
        1.0
        -
        (
            decision[
                "parameters_eff"
            ]
            /
            v24[
                "parameters_eff"
            ]
        )
    )
)


decision[
    "gpu_latency_reduction_vs_v24_percent"
] = (
    100.0
    *
    (
        1.0
        -
        (
            decision[
                "gpu_b1_median_ms"
            ]
            /
            v24[
                "gpu_b1_median_ms"
            ]
        )
    )
)


decision[
    "meets_parameter_target"
] = (
    decision[
        "parameters_eff"
    ]
    <=
    50000
)


decision[
    "meets_gpu_latency_target"
] = (
    decision[
        "gpu_b1_median_ms"
    ]
    <=
    0.20
)


decision.to_csv(
    OUT /
    "screening_decision_matrix.csv",
    index=False
)


print()
print(
    "8. FINAL SCREENING DECISION MATRIX"
)
print(
    "-" * 80
)


display = [

    "method",

    "clean_macro_f1_dataset_macro_mean",

    "corrupted_accuracy_dataset_macro_mean",

    "corrupted_macro_f1_dataset_macro_mean",

    "parameters_eff",

    "gpu_b1_median_ms",

    "clean_f1_delta_vs_v24",

    "corrupted_accuracy_delta_vs_v24",

    "corrupted_f1_delta_vs_v24",

    "parameter_reduction_vs_v24_percent",

    "gpu_latency_reduction_vs_v24_percent",

    "meets_parameter_target",

    "meets_gpu_latency_target",
]


print(
    decision[
        display
    ]
    .sort_values(
        "corrupted_accuracy_dataset_macro_mean",
        ascending=False
    )
    .to_string(
        index=False
    )
)


# ==========================================================
# 9. CANDIDATE-ONLY COMPARISON
# ==========================================================

print()
print(
    "9. DIRECT CANDIDATE-ONLY COMPARISON"
)
print(
    "-" * 80
)


candidate_only = decision[
    decision[
        "method"
    ]
    !=
    "ReliabilityCNN_v24"
][
    display
]


print(
    candidate_only.to_string(
        index=False
    )
)


# ==========================================================
# 10. RECEIPT
# ==========================================================

outputs = [

    OUT /
    "screening_per_seed_18.csv",

    OUT /
    "screening_family_per_seed_72.csv",

    OUT /
    "dataset_method_summary_6.csv",

    OUT /
    "cross_dataset_screening_summary_3.csv",

    OUT /
    "family_screening_summary_12.csv",

    OUT /
    "same_session_efficiency_6.csv",

    OUT /
    "same_session_efficiency_summary_3.csv",

    OUT /
    "screening_decision_matrix.csv",
]


receipt = {

    "protocol":
        "v25_screening_r1",

    "protocol_sha256":
        protocol_sha,

    "integrity_pass":
        True,

    "training_runs_verified":
        training_verified,

    "reliability_runs_verified":
        reliability_verified,

    "screening_candidates":
        CANDIDATES,

    "reference":
        "ReliabilityCNN_v24",

    "reference_seeds":
        SEEDS,

    "reference_datasets":
        DATASETS,

    "important_training_protocol_boundary":
        (
            "V25 screening candidates use clean CE. "
            "V24 reference comes from V3R1 reliability-training "
            "path where feature consistency was unavailable. "
            "This comparison is for development architecture "
            "selection and is not final superiority evidence."
        ),

    "outputs":
        {
            str(path.relative_to(REPO)):
                sha256_file(
                    path
                )
            for path in outputs
        },
}


receipt_path = (
    OUT /
    "v25_screening_r1_analysis_receipt.json"
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
    "FINAL_RECEIPT=",
    receipt_path
)

print(
    "FINAL_RECEIPT_SHA256=",
    sha256_file(
        receipt_path
    )
)


print()
print(
    "=" * 80
)

print(
    "V25_SCREENING_R1_FINAL_ANALYSIS_PASS=True"
)

print(
    "TRAINING_RUNS=12"
)

print(
    "RELIABILITY_RUNS=12"
)

print(
    "REFERENCE_V24_RUNS=6"
)

print(
    "EFFICIENCY_MEASUREMENTS=6"
)

print(
    "=" * 80
)
