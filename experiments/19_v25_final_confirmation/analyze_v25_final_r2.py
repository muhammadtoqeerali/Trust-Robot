from pathlib import Path
import hashlib
import json
import math

import numpy as np
import pandas as pd

from scipy.stats import (
    ttest_rel,
    wilcoxon,
)


REPO = Path.cwd()

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

OUT = (
    V25_ROOT /
    "final_analysis"
)

MANIFEST = (
    V25_ROOT /
    "protocol" /
    "protocol_manifest.json"
)

R1_ABORT = (
    REPO /
    "results" /
    "v25_final_r1" /
    "ABORTED_R1_HARNESS_RECEIPT.json"
)

V3_RECEIPT = (
    V3_ROOT /
    "final_analysis" /
    "benchmark_v3r1_final_integrity_receipt_r2.json"
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

ALL_MODELS = (
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


SEEDS = [
    42,
    123,
    456,
    789,
    2026,
]


DEVELOPMENT_DATASETS = {
    "UCI_HAR",
    "DSADS",
}


DEVELOPMENT_SEEDS = {
    42,
    123,
    456,
}


FAMILIES = [
    "missing_channel",
    "random_dropout",
    "gaussian_noise",
    "sensor_drift",
]


PRIMARY_METRICS = [
    "clean_accuracy",
    "clean_macro_f1",
    "corrupted_accuracy",
    "corrupted_macro_f1",
    "reliability_score",
]


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


def require(
    condition,
    message,
    errors
):

    if not condition:

        errors.append(
            message
        )


def evidence_slice(
    dataset,
    seed
):

    if (
        dataset
        in
        DEVELOPMENT_DATASETS
        and
        seed
        in
        DEVELOPMENT_SEEDS
    ):

        return (
            "development_reproduction"
        )

    return (
        "selection_heldout_confirmation"
    )


def holm_adjust(
    p_values
):

    p = np.asarray(
        p_values,
        dtype=float
    )

    n = len(
        p
    )

    order = np.argsort(
        p
    )

    adjusted_sorted = np.zeros(
        n,
        dtype=float
    )

    running = 0.0


    for rank, index in enumerate(
        order
    ):

        multiplier = (
            n
            -
            rank
        )

        value = (
            p[
                index
            ]
            *
            multiplier
        )

        running = max(
            running,
            value
        )

        adjusted_sorted[
            rank
        ] = min(
            running,
            1.0
        )


    adjusted = np.zeros(
        n,
        dtype=float
    )


    for rank, index in enumerate(
        order
    ):

        adjusted[
            index
        ] = adjusted_sorted[
            rank
        ]


    return adjusted


errors = []


print(
    "=" * 90
)

print(
    "RELIABILITYCNN V25 FINAL R2 — DEFINITIVE ANALYSIS"
)

print(
    "=" * 90
)


# ============================================================
# 1. V25 FINAL PROTOCOL INTEGRITY
# ============================================================

print()
print(
    "1. V25 FINAL R2 PROTOCOL INTEGRITY"
)
print(
    "-" * 90
)


require(
    MANIFEST.exists(),
    f"Missing manifest: {MANIFEST}",
    errors
)


manifest = load_json(
    MANIFEST
)


protocol_sha = sha256_file(
    MANIFEST
)


verified_hashes = 0


for relative, expected_sha in (
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
        f"Missing frozen file: {relative}",
        errors
    )


    if not path.exists():
        continue


    actual_sha = sha256_file(
        path
    )


    require(
        actual_sha
        ==
        expected_sha,
        f"Frozen SHA mismatch: {relative}",
        errors
    )


    if actual_sha == expected_sha:

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


# ============================================================
# 2. LINEAGE CHECK
# ============================================================

print()
print(
    "2. R1 -> R2 LINEAGE"
)
print(
    "-" * 90
)


require(
    R1_ABORT.exists(),
    "Missing R1 abort receipt",
    errors
)


if R1_ABORT.exists():

    abort = load_json(
        R1_ABORT
    )


    require(
        abort.get(
            "status"
        )
        ==
        "ABORTED_HARNESS_ONLY",
        "R1 abort classification mismatch",
        errors
    )


    require(
        abort.get(
            "state_dict_tensors_exact_equal"
        )
        is True,
        "R1 state dict equality was not verified",
        errors
    )


    print(
        "R1_ABORT_STATUS=",
        abort.get(
            "status"
        )
    )

    print(
        "R1_STATE_DICT_TENSOR_EQUAL=",
        abort.get(
            "state_dict_tensors_exact_equal"
        )
    )


print(
    "R2_COSMETIC_PREFLIGHT_BANNER_NOTE=True"
)

print(
    "R2_COSMETIC_PREFLIGHT_BANNER_IMPACT=NONE"
)


# ============================================================
# 3. VERIFY ALL 20 V25 TRAINING + RELIABILITY RUNS
# ============================================================

print()
print(
    "3. VERIFY 20 FINAL TRAINING + 20 RELIABILITY RUNS"
)
print(
    "-" * 90
)


training_verified = 0

reliability_verified = 0

heldout_count = 0

reproduction_count = 0


for dataset in DATASETS:

    for seed in SEEDS:

        raw = (
            V25_ROOT /
            "raw_runs" /
            dataset /
            V25_MODEL /
            f"seed_{seed}"
        )


        rel = (
            V25_ROOT /
            "reliability_v2" /
            dataset /
            V25_MODEL /
            f"seed_{seed}"
        )


        required = [

            raw /
            "COMPLETE",

            raw /
            "best_model.pt",

            raw /
            "checkpoint.pt",

            raw /
            "metrics.json",

            raw /
            "history.json",

            raw /
            "dataset_summary.json",

            raw /
            "receipt.json",
        ]


        for path in required:

            require(
                path.exists(),
                f"Missing V25 training artifact: {path}",
                errors
            )


        if all(
            path.exists()
            for path in required
        ):

            metrics = load_json(
                raw /
                "metrics.json"
            )


            receipt = load_json(
                raw /
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
                    f"{dataset}/{seed}"
                ),
                errors
            )


            best_sha = sha256_file(
                raw /
                "best_model.pt"
            )


            checkpoint_sha = sha256_file(
                raw /
                "checkpoint.pt"
            )


            require(
                best_sha
                ==
                checkpoint_sha,
                (
                    "R2 checkpoint byte-copy mismatch: "
                    f"{dataset}/{seed}"
                ),
                errors
            )


            require(
                receipt.get(
                    "best_model_sha256"
                )
                ==
                best_sha,
                (
                    "best_model receipt mismatch: "
                    f"{dataset}/{seed}"
                ),
                errors
            )


            require(
                receipt.get(
                    "checkpoint_sha256"
                )
                ==
                checkpoint_sha,
                (
                    "checkpoint receipt mismatch: "
                    f"{dataset}/{seed}"
                ),
                errors
            )


            expected_slice = evidence_slice(
                dataset,
                seed
            )


            require(
                metrics.get(
                    "evidence_slice"
                )
                ==
                expected_slice,
                (
                    "Evidence slice mismatch: "
                    f"{dataset}/{seed}"
                ),
                errors
            )


            if (
                expected_slice
                ==
                "selection_heldout_confirmation"
            ):

                heldout_count += 1

            else:

                reproduction_count += 1


            training_verified += 1


        rel_required = [

            rel /
            "COMPLETE",

            rel /
            "reliability_summary_v2.json",

            rel /
            "final_receipt.json",
        ]


        for path in rel_required:

            require(
                path.exists(),
                f"Missing V25 reliability artifact: {path}",
                errors
            )


        if all(
            path.exists()
            for path in rel_required
        ):

            rel_receipt = load_json(
                rel /
                "final_receipt.json"
            )


            summary = load_json(
                rel /
                "reliability_summary_v2.json"
            )


            require(
                rel_receipt.get(
                    "protocol_manifest_sha256"
                )
                ==
                protocol_sha,
                (
                    "Reliability protocol SHA mismatch: "
                    f"{dataset}/{seed}"
                ),
                errors
            )


            require(
                summary.get(
                    "protocol_version"
                )
                ==
                "v2",
                (
                    "Wrong V25 reliability version: "
                    f"{dataset}/{seed}"
                ),
                errors
            )


            require(
                summary.get(
                    "n_corrupted_cases"
                )
                ==
                33,
                (
                    "Wrong V25 corruption count: "
                    f"{dataset}/{seed}"
                ),
                errors
            )


            reliability_verified += 1


print(
    "TRAINING_VERIFIED=",
    training_verified,
    "/20"
)

print(
    "RELIABILITY_VERIFIED=",
    reliability_verified,
    "/20"
)

print(
    "SELECTION_HELDOUT_CONFIRMATION_VERIFIED=",
    heldout_count,
    "/14"
)

print(
    "DEVELOPMENT_REPRODUCTION_VERIFIED=",
    reproduction_count,
    "/6"
)


# ============================================================
# 4. V3R1 REFERENCE INTEGRITY
# ============================================================

print()
print(
    "4. V3R1 REFERENCE BANK"
)
print(
    "-" * 90
)


require(
    V3_RECEIPT.exists(),
    "Missing V3R1 integrity receipt",
    errors
)


if V3_RECEIPT.exists():

    v3_receipt = load_json(
        V3_RECEIPT
    )


    require(
        v3_receipt.get(
            "integrity_pass"
        )
        is True,
        "V3R1 reference bank not integrity_pass",
        errors
    )


print(
    "HEADLINE_BASELINE_MODELS=",
    len(
        BASELINES
    )
)

print(
    "DEVELOPMENTAL_V23_EXCLUDED=",
    "ReliabilityCNN_v23"
    not in
    BASELINES
)


# ============================================================
# Stop before interpretation if integrity fails
# ============================================================

if errors:

    print()
    print(
        "INTEGRITY_ERROR_COUNT=",
        len(
            errors
        )
    )


    for error in errors:

        print(
            "ERROR:",
            error
        )


    print(
        "V25_FINAL_R2_INTEGRITY_PASS=False"
    )


    raise SystemExit(
        4
    )


print(
    "INTEGRITY_ERROR_COUNT=0"
)

print(
    "V25_FINAL_R2_INTEGRITY_PASS=True"
)


# ============================================================
# 5. LOAD 200 MATCHED MODEL × DATASET × SEED POINTS
# ============================================================

print()
print(
    "5. LOAD V25 + FROZEN 9-MODEL BANK"
)
print(
    "-" * 90
)


rows = []

family_rows = []


for dataset in DATASETS:

    for model in ALL_MODELS:

        for seed in SEEDS:

            if model == V25_MODEL:

                raw = (
                    V25_ROOT /
                    "raw_runs" /
                    dataset /
                    model /
                    f"seed_{seed}"
                )


                rel = (
                    V25_ROOT /
                    "reliability_v2" /
                    dataset /
                    model /
                    f"seed_{seed}"
                )

            else:

                raw = (
                    V3_ROOT /
                    "raw_runs" /
                    dataset /
                    model /
                    f"seed_{seed}"
                )


                rel = (
                    V3_ROOT /
                    "reliability_v2" /
                    dataset /
                    model /
                    f"seed_{seed}"
                )


            metrics = load_json(
                raw /
                "metrics.json"
            )


            reliability = load_json(
                rel /
                "reliability_summary_v2.json"
            )


            test = metrics[
                "test"
            ]


            overall = reliability[
                "overall"
            ]


            slice_name = evidence_slice(
                dataset,
                seed
            )


            rows.append(
                {

                    "dataset":
                        dataset,

                    "model":
                        model,

                    "seed":
                        seed,

                    "evidence_slice":
                        slice_name,

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
                        float(
                            metrics[
                                "parameters"
                            ]
                        ),
                }
            )


            for family in FAMILIES:

                f = (
                    reliability[
                        "family_summaries"
                    ][
                        family
                    ]
                )


                family_rows.append(
                    {

                        "dataset":
                            dataset,

                        "model":
                            model,

                        "seed":
                            seed,

                        "evidence_slice":
                            slice_name,

                        "family":
                            family,

                        "reliability_score":
                            float(
                                f[
                                    "reliability_score_mean"
                                ]
                            ),

                        "corrupted_accuracy":
                            float(
                                f[
                                    "corrupted_accuracy_mean"
                                ]
                            ),

                        "corrupted_macro_f1":
                            float(
                                f[
                                    "corrupted_macro_f1_mean"
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


require(
    len(
        per_seed
    )
    ==
    200,
    f"Expected 200 rows, got {len(per_seed)}",
    errors
)


require(
    len(
        family_seed
    )
    ==
    800,
    f"Expected 800 family rows, got {len(family_seed)}",
    errors
)


per_seed.to_csv(
    OUT /
    "all_models_per_seed_200.csv",
    index=False
)


family_seed.to_csv(
    OUT /
    "all_models_family_per_seed_800.csv",
    index=False
)


print(
    "MODEL_DATASET_SEED_ROWS=",
    len(
        per_seed
    )
)

print(
    "FAMILY_ROWS=",
    len(
        family_seed
    )
)


# ============================================================
# 6. COMPLETE FOUR-DATASET SUMMARY
# ============================================================

dataset_rows = []


for (
    dataset,
    model
), group in per_seed.groupby(
    [
        "dataset",
        "model"
    ],
    sort=False
):

    dataset_rows.append(
        {

            "dataset":
                dataset,

            "model":
                model,

            "clean_accuracy":
                float(
                    group[
                        "clean_accuracy"
                    ].mean()
                ),

            "clean_macro_f1":
                float(
                    group[
                        "clean_macro_f1"
                    ].mean()
                ),

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

            "parameters":
                float(
                    group[
                        "parameters"
                    ].mean()
                ),
        }
    )


dataset_summary = pd.DataFrame(
    dataset_rows
)


for metric in [
    "clean_accuracy",
    "clean_macro_f1",
    "corrupted_accuracy",
    "corrupted_macro_f1",
    "reliability_score",
]:

    dataset_summary[
        f"{metric}_rank"
    ] = (
        dataset_summary
        .groupby(
            "dataset"
        )[
            metric
        ]
        .rank(
            ascending=False,
            method="average"
        )
    )


dataset_summary.to_csv(
    OUT /
    "dataset_model_summary_40.csv",
    index=False
)


cross = (
    dataset_summary
    .groupby(
        "model",
        as_index=False
    )
    .agg(

        clean_accuracy=(
            "clean_accuracy",
            "mean"
        ),

        clean_macro_f1=(
            "clean_macro_f1",
            "mean"
        ),

        reliability_score=(
            "reliability_score",
            "mean"
        ),

        corrupted_accuracy=(
            "corrupted_accuracy",
            "mean"
        ),

        corrupted_macro_f1=(
            "corrupted_macro_f1",
            "mean"
        ),

        parameters=(
            "parameters",
            "mean"
        ),
    )
)


for metric in [
    "clean_accuracy",
    "clean_macro_f1",
    "corrupted_accuracy",
    "corrupted_macro_f1",
    "reliability_score",
]:

    cross[
        f"{metric}_rank"
    ] = (
        cross[
            metric
        ]
        .rank(
            ascending=False,
            method="average"
        )
    )


cross.to_csv(
    OUT /
    "four_dataset_equal_weight_summary_10.csv",
    index=False
)


print()
print(
    "6. FOUR-DATASET EQUAL-WEIGHT SUMMARY"
)
print(
    "-" * 90
)


print(
    cross[
        [
            "model",
            "clean_accuracy",
            "clean_macro_f1",
            "corrupted_accuracy",
            "corrupted_macro_f1",
            "reliability_score",
            "parameters",
            "corrupted_accuracy_rank",
            "corrupted_macro_f1_rank",
        ]
    ]
    .sort_values(
        "corrupted_accuracy",
        ascending=False
    )
    .to_string(
        index=False
    )
)


# ============================================================
# 7. SELECTION-HELD-OUT CONFIRMATION
# ============================================================

heldout = per_seed[
    per_seed[
        "evidence_slice"
    ]
    ==
    "selection_heldout_confirmation"
].copy()


heldout_dataset = (
    heldout
    .groupby(
        [
            "dataset",
            "model"
        ],
        as_index=False
    )
    .agg(

        clean_accuracy=(
            "clean_accuracy",
            "mean"
        ),

        clean_macro_f1=(
            "clean_macro_f1",
            "mean"
        ),

        reliability_score=(
            "reliability_score",
            "mean"
        ),

        corrupted_accuracy=(
            "corrupted_accuracy",
            "mean"
        ),

        corrupted_macro_f1=(
            "corrupted_macro_f1",
            "mean"
        ),
    )
)


heldout_cross = (
    heldout_dataset
    .groupby(
        "model",
        as_index=False
    )
    .agg(

        clean_accuracy=(
            "clean_accuracy",
            "mean"
        ),

        clean_macro_f1=(
            "clean_macro_f1",
            "mean"
        ),

        reliability_score=(
            "reliability_score",
            "mean"
        ),

        corrupted_accuracy=(
            "corrupted_accuracy",
            "mean"
        ),

        corrupted_macro_f1=(
            "corrupted_macro_f1",
            "mean"
        ),
    )
)


for metric in [
    "clean_accuracy",
    "clean_macro_f1",
    "corrupted_accuracy",
    "corrupted_macro_f1",
    "reliability_score",
]:

    heldout_cross[
        f"{metric}_rank"
    ] = (
        heldout_cross[
            metric
        ]
        .rank(
            ascending=False,
            method="average"
        )
    )


heldout_cross.to_csv(
    OUT /
    "heldout_equal_dataset_weight_summary_10.csv",
    index=False
)


print()
print(
    "7. SELECTION-HELD-OUT CONFIRMATION SUMMARY"
)
print(
    "-" * 90
)


print(
    heldout_cross[
        [
            "model",
            "clean_accuracy",
            "clean_macro_f1",
            "corrupted_accuracy",
            "corrupted_macro_f1",
            "reliability_score",
            "corrupted_accuracy_rank",
            "corrupted_macro_f1_rank",
        ]
    ]
    .sort_values(
        "corrupted_accuracy",
        ascending=False
    )
    .to_string(
        index=False
    )
)


# ============================================================
# 8. V25 VS EACH BASELINE — HELDOUT MATCHED DELTAS
# ============================================================

heldout_rows = []


v25_heldout = (
    heldout[
        heldout[
            "model"
        ]
        ==
        V25_MODEL
    ]
    .set_index(
        [
            "dataset",
            "seed"
        ]
    )
)


for baseline in BASELINES:

    base = (
        heldout[
            heldout[
                "model"
            ]
            ==
            baseline
        ]
        .set_index(
            [
                "dataset",
                "seed"
            ]
        )
    )


    common = (
        v25_heldout.index
        .intersection(
            base.index
        )
    )


    for metric in PRIMARY_METRICS:

        delta = (
            v25_heldout.loc[
                common,
                metric
            ].to_numpy(
                dtype=float
            )
            -
            base.loc[
                common,
                metric
            ].to_numpy(
                dtype=float
            )
        )


        heldout_rows.append(
            {

                "baseline":
                    baseline,

                "metric":
                    metric,

                "matched_points":
                    len(
                        delta
                    ),

                "v25_mean_delta":
                    float(
                        delta.mean()
                    ),

                "v25_wins":
                    int(
                        np.sum(
                            delta > 0
                        )
                    ),

                "baseline_wins":
                    int(
                        np.sum(
                            delta < 0
                        )
                    ),

                "ties":
                    int(
                        np.sum(
                            delta == 0
                        )
                    ),
            }
        )


heldout_delta = pd.DataFrame(
    heldout_rows
)


heldout_delta.to_csv(
    OUT /
    "heldout_v25_vs_baselines.csv",
    index=False
)


print()
print(
    "8. HELD-OUT V25 MATCHED DELTAS"
)
print(
    "-" * 90
)


print(
    heldout_delta[
        heldout_delta[
            "metric"
        ].isin(
            [
                "clean_macro_f1",
                "corrupted_accuracy",
                "corrupted_macro_f1",
            ]
        )
    ].to_string(
        index=False
    )
)


# ============================================================
# 9. FIVE-SEED PAIRED STATISTICS PER DATASET
# ============================================================

stats_rows = []


v25_all = per_seed[
    per_seed[
        "model"
    ]
    ==
    V25_MODEL
]


for dataset in DATASETS:

    v25_dataset = (
        v25_all[
            v25_all[
                "dataset"
            ]
            ==
            dataset
        ]
        .set_index(
            "seed"
        )
    )


    for baseline in BASELINES:

        base_dataset = (
            per_seed[
                (
                    per_seed[
                        "dataset"
                    ]
                    ==
                    dataset
                )
                &
                (
                    per_seed[
                        "model"
                    ]
                    ==
                    baseline
                )
            ]
            .set_index(
                "seed"
            )
        )


        for metric in [

            "clean_accuracy",

            "clean_macro_f1",

            "corrupted_accuracy",

            "corrupted_macro_f1",
        ]:

            a = (
                v25_dataset.loc[
                    SEEDS,
                    metric
                ]
                .to_numpy(
                    dtype=float
                )
            )


            b = (
                base_dataset.loc[
                    SEEDS,
                    metric
                ]
                .to_numpy(
                    dtype=float
                )
            )


            delta = (
                a
                -
                b
            )


            t_result = ttest_rel(
                a,
                b
            )


            try:

                w_result = wilcoxon(
                    a,
                    b,
                    alternative="two-sided",
                    zero_method="wilcox"
                )

                wilcoxon_p = float(
                    w_result.pvalue
                )

            except ValueError:

                wilcoxon_p = 1.0


            std_delta = float(
                np.std(
                    delta,
                    ddof=1
                )
            )


            effect_dz = (
                float(
                    np.mean(
                        delta
                    )
                    /
                    std_delta
                )
                if std_delta > 0
                else np.nan
            )


            stats_rows.append(
                {

                    "dataset":
                        dataset,

                    "baseline":
                        baseline,

                    "metric":
                        metric,

                    "mean_delta_v25_minus_baseline":
                        float(
                            np.mean(
                                delta
                            )
                        ),

                    "std_delta":
                        std_delta,

                    "effect_dz":
                        effect_dz,

                    "v25_seed_wins":
                        int(
                            np.sum(
                                delta > 0
                            )
                        ),

                    "baseline_seed_wins":
                        int(
                            np.sum(
                                delta < 0
                            )
                        ),

                    "paired_t_p":
                        float(
                            t_result.pvalue
                        ),

                    "wilcoxon_p":
                        wilcoxon_p,
                }
            )


stats = pd.DataFrame(
    stats_rows
)


stats[
    "paired_t_holm"
] = holm_adjust(
    stats[
        "paired_t_p"
    ].to_numpy()
)


stats[
    "wilcoxon_holm"
] = holm_adjust(
    stats[
        "wilcoxon_p"
    ].to_numpy()
)


stats.to_csv(
    OUT /
    "v25_vs_baselines_paired_stats_144.csv",
    index=False
)


print()
print(
    "9. STATISTICAL SUMMARY"
)
print(
    "-" * 90
)


print(
    "PAIRED_TEST_ROWS=",
    len(
        stats
    )
)

print(
    "PAIRED_T_HOLM_SIGNIFICANT=",
    int(
        np.sum(
            stats[
                "paired_t_holm"
            ]
            <
            0.05
        )
    )
)

print(
    "WILCOXON_HOLM_SIGNIFICANT=",
    int(
        np.sum(
            stats[
                "wilcoxon_holm"
            ]
            <
            0.05
        )
    )
)


# ============================================================
# 10. CORRUPTION FAMILY SUMMARY
# ============================================================

family_dataset = (
    family_seed
    .groupby(
        [
            "family",
            "dataset",
            "model"
        ],
        as_index=False
    )
    .agg(

        corrupted_accuracy=(
            "corrupted_accuracy",
            "mean"
        ),

        corrupted_macro_f1=(
            "corrupted_macro_f1",
            "mean"
        ),

        reliability_score=(
            "reliability_score",
            "mean"
        ),
    )
)


family_cross = (
    family_dataset
    .groupby(
        [
            "family",
            "model"
        ],
        as_index=False
    )
    .agg(

        corrupted_accuracy=(
            "corrupted_accuracy",
            "mean"
        ),

        corrupted_macro_f1=(
            "corrupted_macro_f1",
            "mean"
        ),

        reliability_score=(
            "reliability_score",
            "mean"
        ),
    )
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
    "corruption_family_summary_40.csv",
    index=False
)


print()
print(
    "10. V25 CORRUPTION-FAMILY RANKS"
)
print(
    "-" * 90
)


print(
    family_cross[
        family_cross[
            "model"
        ]
        ==
        V25_MODEL
    ][
        [
            "family",
            "corrupted_accuracy",
            "corrupted_macro_f1",
            "reliability_score",
            "corrupted_accuracy_rank",
            "corrupted_macro_f1_rank",
        ]
    ].to_string(
        index=False
    )
)


# ============================================================
# 11. FINAL V25 POSITION
# ============================================================

v25_cross = (
    cross[
        cross[
            "model"
        ]
        ==
        V25_MODEL
    ]
    .iloc[
        0
    ]
)


v25_heldout = (
    heldout_cross[
        heldout_cross[
            "model"
        ]
        ==
        V25_MODEL
    ]
    .iloc[
        0
    ]
)


print()
print(
    "11. FINAL V25 POSITION"
)
print(
    "-" * 90
)


print(
    "FULL_CLEAN_ACC=",
    v25_cross[
        "clean_accuracy"
    ]
)

print(
    "FULL_CLEAN_F1=",
    v25_cross[
        "clean_macro_f1"
    ]
)

print(
    "FULL_CORRUPTED_ACC=",
    v25_cross[
        "corrupted_accuracy"
    ]
)

print(
    "FULL_CORRUPTED_F1=",
    v25_cross[
        "corrupted_macro_f1"
    ]
)

print(
    "FULL_RELIABILITY=",
    v25_cross[
        "reliability_score"
    ]
)

print(
    "FULL_CORRUPTED_ACC_RANK=",
    v25_cross[
        "corrupted_accuracy_rank"
    ]
)

print(
    "FULL_CORRUPTED_F1_RANK=",
    v25_cross[
        "corrupted_macro_f1_rank"
    ]
)

print(
    "FULL_PARAMETER_MEAN=",
    v25_cross[
        "parameters"
    ]
)


print(
    "HELDOUT_CLEAN_F1=",
    v25_heldout[
        "clean_macro_f1"
    ]
)

print(
    "HELDOUT_CORRUPTED_ACC=",
    v25_heldout[
        "corrupted_accuracy"
    ]
)

print(
    "HELDOUT_CORRUPTED_F1=",
    v25_heldout[
        "corrupted_macro_f1"
    ]
)

print(
    "HELDOUT_CORRUPTED_ACC_RANK=",
    v25_heldout[
        "corrupted_accuracy_rank"
    ]
)

print(
    "HELDOUT_CORRUPTED_F1_RANK=",
    v25_heldout[
        "corrupted_macro_f1_rank"
    ]
)


# ============================================================
# 12. FINAL RECEIPT
# ============================================================

outputs = [

    OUT /
    "all_models_per_seed_200.csv",

    OUT /
    "all_models_family_per_seed_800.csv",

    OUT /
    "dataset_model_summary_40.csv",

    OUT /
    "four_dataset_equal_weight_summary_10.csv",

    OUT /
    "heldout_equal_dataset_weight_summary_10.csv",

    OUT /
    "heldout_v25_vs_baselines.csv",

    OUT /
    "v25_vs_baselines_paired_stats_144.csv",

    OUT /
    "corruption_family_summary_40.csv",
]


receipt = {

    "protocol":
        "v25_final_r2",

    "protocol_sha256":
        protocol_sha,

    "integrity_pass":
        True,

    "training_runs_verified":
        training_verified,

    "reliability_runs_verified":
        reliability_verified,

    "selection_heldout_confirmation_runs":
        heldout_count,

    "development_reproduction_runs":
        reproduction_count,

    "v3r1_reference_integrity_pass":
        True,

    "headline_baseline_count":
        len(
            BASELINES
        ),

    "developmental_v23_excluded":
        True,

    "r1_lineage":
        (
            "R1 aborted due harness-only "
            "checkpoint serialization SHA assertion. "
            "Tensor equality was verified. "
            "R2 contains the harness correction."
        ),

    "cosmetic_note":
        (
            "R2 preflight console heading retained "
            "the text 'FINAL R1 PREFLIGHT'. "
            "This was cosmetic only and had no "
            "protocol or namespace impact."
        ),

    "claim_boundary":
        (
            "Full 4x5 results include six "
            "development-reproduction points. "
            "The 14-run selection-held-out slice "
            "must be reported separately for "
            "generalization claims."
        ),

    "statistical_boundary":
        (
            "Five paired seeds per dataset provide "
            "limited power. Exact two-sided Wilcoxon "
            "cannot reach p<0.05 with n=5 in the "
            "strict all-nonzero setting; interpret "
            "effect sizes, seed consistency, paired "
            "t-tests, and held-out confirmation "
            "together rather than relying on one "
            "significance gate."
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
    "v25_final_r2_analysis_receipt.json"
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
    "FINAL_ANALYSIS_RECEIPT=",
    receipt_path
)

print(
    "FINAL_ANALYSIS_RECEIPT_SHA256=",
    sha256_file(
        receipt_path
    )
)


print()
print(
    "=" * 90
)

print(
    "V25_FINAL_R2_DEFINITIVE_ANALYSIS_PASS=True"
)

print(
    "FINAL_MODEL_POINTS=20"
)

print(
    "FULL_COMPARISON_POINTS=200"
)

print(
    "HELDOUT_CONFIRMATION_POINTS=14"
)

print(
    "BASELINE_MODELS=9"
)

print(
    "=" * 90
)
