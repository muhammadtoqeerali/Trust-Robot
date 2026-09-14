from pathlib import Path
import hashlib
import json
import math

import numpy as np
import pandas as pd
from scipy import stats


ROOT = Path(
    "results/benchmark_v3r1"
)

A = (
    ROOT /
    "final_analysis"
)


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


DATASETS = [
    "UCI_HAR",
    "PAMAP2",
    "DSADS",
    "MotionSense",
]


FAMILIES = [
    "missing_channel",
    "random_dropout",
    "gaussian_noise",
    "sensor_drift",
]


SEEDS = [
    42,
    123,
    456,
    789,
    2026,
]


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


def holm_adjust(
    values
):

    values = np.asarray(
        values,
        dtype=float
    )


    adjusted = np.full(
        len(values),
        np.nan,
        dtype=float
    )


    valid = np.where(
        np.isfinite(
            values
        )
    )[0]


    if len(valid) == 0:
        return adjusted


    ordered = valid[
        np.argsort(
            values[
                valid
            ]
        )
    ]


    m = len(
        ordered
    )


    running = 0.0


    for rank, index in enumerate(
        ordered
    ):

        raw = values[
            index
        ]


        candidate = (
            m - rank
        ) * raw


        running = max(
            running,
            candidate
        )


        adjusted[
            index
        ] = min(
            running,
            1.0
        )


    return adjusted


def apply_holm(
    df,
    group_columns,
    p_column,
    output_column
):

    pieces = []


    for _, group in df.groupby(
        group_columns,
        sort=False,
        dropna=False
    ):

        group = group.copy()


        group[
            output_column
        ] = holm_adjust(
            pd.to_numeric(
                group[
                    p_column
                ],
                errors="coerce"
            ).to_numpy(
                dtype=float
            )
        )


        pieces.append(
            group
        )


    return pd.concat(
        pieces,
        ignore_index=True
    )


def paired_test(
    anchor,
    competitor
):

    anchor = np.asarray(
        anchor,
        dtype=float
    )

    competitor = np.asarray(
        competitor,
        dtype=float
    )


    diff = (
        anchor
        -
        competitor
    )


    mean_diff = float(
        np.mean(
            diff
        )
    )


    sd = float(
        np.std(
            diff,
            ddof=1
        )
    )


    dz = (
        mean_diff
        /
        sd
        if sd > 0
        else np.nan
    )


    t_p = float(
        stats.ttest_rel(
            anchor,
            competitor
        ).pvalue
    )


    if np.allclose(
        diff,
        0
    ):

        w_p = 1.0

    else:

        try:

            w_p = float(
                stats.wilcoxon(
                    diff,
                    zero_method="wilcox",
                    alternative="two-sided"
                ).pvalue
            )

        except Exception:

            w_p = np.nan


    return {
        "n":
            len(diff),

        "mean_difference":
            mean_diff,

        "cohen_dz":
            dz,

        "paired_t_pvalue":
            t_p,

        "wilcoxon_pvalue":
            w_p,

        "anchor_higher_count":
            int(
                np.sum(
                    diff > 0
                )
            ),

        "competitor_higher_count":
            int(
                np.sum(
                    diff < 0
                )
            ),

        "equal_count":
            int(
                np.sum(
                    diff == 0
                )
            ),
    }


def pareto_membership(
    df,
    maximize,
    minimize
):

    models = (
        df[
            "model"
        ]
        .tolist()
    )


    dominated_by = {
        model: []
        for model in models
    }


    for i, row_i in df.iterrows():

        model_i = row_i[
            "model"
        ]


        for j, row_j in df.iterrows():

            if i == j:
                continue


            all_good = True
            strict = False


            for column in maximize:

                if (
                    row_j[
                        column
                    ]
                    <
                    row_i[
                        column
                    ]
                ):

                    all_good = False
                    break


                if (
                    row_j[
                        column
                    ]
                    >
                    row_i[
                        column
                    ]
                ):

                    strict = True


            if not all_good:
                continue


            for column in minimize:

                if (
                    row_j[
                        column
                    ]
                    >
                    row_i[
                        column
                    ]
                ):

                    all_good = False
                    break


                if (
                    row_j[
                        column
                    ]
                    <
                    row_i[
                        column
                    ]
                ):

                    strict = True


            if (
                all_good
                and
                strict
            ):

                dominated_by[
                    model_i
                ].append(
                    row_j[
                        "model"
                    ]
                )


    result = df.copy()


    result[
        "pareto_front"
    ] = result[
        "model"
    ].map(
        lambda model:
            len(
                dominated_by[
                    model
                ]
            )
            ==
            0
    )


    result[
        "dominated_by"
    ] = result[
        "model"
    ].map(
        lambda model:
            ";".join(
                dominated_by[
                    model
                ]
            )
    )


    return result


cross = pd.read_csv(
    A /
    "cross_dataset_model_summary_9.csv"
)


dataset_summary = pd.read_csv(
    A /
    "dataset_model_summary_36.csv"
)


family_summary = pd.read_csv(
    A /
    "reliability_family_summary_144.csv"
)


family_runs = pd.read_csv(
    A /
    "reliability_family_runs_720.csv"
)


paired = pd.read_csv(
    A /
    "paired_seed_tests_v22_v24_vs_competitors.csv"
)


efficiency = pd.read_csv(
    A /
    "efficiency_benchmark_36.csv"
)


print(
    "=" * 78
)

print(
    "V3R1 FINAL METHOD DECISION ANALYSIS"
)

print(
    "=" * 78
)


print()
print(
    "1. HOLM-CORRECT ORIGINAL 320 FIVE-SEED TESTS"
)
print(
    "-" * 78
)


paired = apply_holm(
    paired,
    [
        "dataset",
        "anchor_model",
        "metric"
    ],
    "paired_t_pvalue",
    "paired_t_pvalue_holm"
)


paired = apply_holm(
    paired,
    [
        "dataset",
        "anchor_model",
        "metric"
    ],
    "wilcoxon_pvalue",
    "wilcoxon_pvalue_holm"
)


paired[
    "holm_significant_0_05"
] = (
    paired[
        "wilcoxon_pvalue_holm"
    ]
    <
    0.05
)


paired[
    "direction"
] = np.where(
    paired[
        "mean_difference"
    ]
    >
    0,
    "anchor_higher",
    np.where(
        paired[
            "mean_difference"
        ]
        <
        0,
        "competitor_higher",
        "equal"
    )
)


paired.to_csv(
    A /
    "paired_seed_tests_holm.csv",
    index=False
)


comparison_summary_rows = []


for (
    anchor,
    competitor,
    metric
), group in paired.groupby(
    [
        "anchor_model",
        "competitor_model",
        "metric"
    ],
    sort=False
):

    comparison_summary_rows.append(
        {
            "anchor_model":
                anchor,

            "competitor_model":
                competitor,

            "metric":
                metric,

            "datasets":
                len(
                    group
                ),

            "mean_difference_across_datasets":
                float(
                    group[
                        "mean_difference"
                    ].mean()
                ),

            "anchor_higher_datasets":
                int(
                    (
                        group[
                            "mean_difference"
                        ]
                        >
                        0
                    ).sum()
                ),

            "competitor_higher_datasets":
                int(
                    (
                        group[
                            "mean_difference"
                        ]
                        <
                        0
                    ).sum()
                ),

            "holm_significant_anchor_wins":
                int(
                    (
                        (
                            group[
                                "holm_significant_0_05"
                            ]
                        )
                        &
                        (
                            group[
                                "mean_difference"
                            ]
                            >
                            0
                        )
                    ).sum()
                ),

            "holm_significant_anchor_losses":
                int(
                    (
                        (
                            group[
                                "holm_significant_0_05"
                            ]
                        )
                        &
                        (
                            group[
                                "mean_difference"
                            ]
                            <
                            0
                        )
                    ).sum()
                ),
        }
    )


comparison_summary = pd.DataFrame(
    comparison_summary_rows
)


comparison_summary.to_csv(
    A /
    "paired_comparison_summary.csv",
    index=False
)


print(
    "HOLM_CORRECTED_TEST_ROWS=",
    len(
        paired
    )
)


print()
print(
    "2. FAMILY-LEVEL PAIRED TESTS"
)
print(
    "-" * 78
)


family_test_rows = []


for dataset in DATASETS:

    for family in FAMILIES:

        subset = family_runs[
            (
                family_runs[
                    "dataset"
                ]
                ==
                dataset
            )
            &
            (
                family_runs[
                    "family"
                ]
                ==
                family
            )
        ]


        for anchor in [
            "ReliabilityCNN_v22",
            "ReliabilityCNN_v24",
        ]:

            anchor_df = (
                subset[
                    subset[
                        "model"
                    ]
                    ==
                    anchor
                ]
                .set_index(
                    "seed"
                )
            )


            for competitor in MODELS:

                if competitor == anchor:
                    continue


                competitor_df = (
                    subset[
                        subset[
                            "model"
                        ]
                        ==
                        competitor
                    ]
                    .set_index(
                        "seed"
                    )
                )


                common = sorted(
                    set(
                        anchor_df.index
                    )
                    &
                    set(
                        competitor_df.index
                    )
                )


                if common != SEEDS:

                    raise RuntimeError(
                        "Family seed mismatch: "
                        f"{dataset}/"
                        f"{family}/"
                        f"{anchor}/"
                        f"{competitor}: "
                        f"{common}"
                    )


                for metric in [
                    "reliability_score",
                    "corrupted_accuracy",
                    "corrupted_macro_f1",
                ]:

                    result = paired_test(
                        anchor_df.loc[
                            common,
                            metric
                        ].to_numpy(),

                        competitor_df.loc[
                            common,
                            metric
                        ].to_numpy()
                    )


                    family_test_rows.append(
                        {
                            "dataset":
                                dataset,

                            "family":
                                family,

                            "anchor_model":
                                anchor,

                            "competitor_model":
                                competitor,

                            "metric":
                                metric,

                            **result,
                        }
                    )


family_tests = pd.DataFrame(
    family_test_rows
)


family_tests = apply_holm(
    family_tests,
    [
        "dataset",
        "family",
        "anchor_model",
        "metric"
    ],
    "wilcoxon_pvalue",
    "wilcoxon_pvalue_holm"
)


family_tests[
    "holm_significant_0_05"
] = (
    family_tests[
        "wilcoxon_pvalue_holm"
    ]
    <
    0.05
)


family_tests.to_csv(
    A /
    "family_paired_tests_holm.csv",
    index=False
)


print(
    "FAMILY_PAIRED_TEST_ROWS=",
    len(
        family_tests
    )
)


print()
print(
    "3. CROSS-DATASET FAMILY BEHAVIOUR"
)
print(
    "-" * 78
)


family_cross_rows = []


for (
    family,
    model
), group in family_summary.groupby(
    [
        "family",
        "model"
    ],
    sort=False
):

    family_cross_rows.append(
        {
            "family":
                family,

            "model":
                model,

            "dataset_count":
                len(
                    group
                ),

            "reliability_score":
                float(
                    group[
                        "reliability_score_mean"
                    ].mean()
                ),

            "corrupted_accuracy":
                float(
                    group[
                        "corrupted_accuracy_mean"
                    ].mean()
                ),

            "corrupted_macro_f1":
                float(
                    group[
                        "corrupted_macro_f1_mean"
                    ].mean()
                ),

            "relative_accuracy_degradation":
                float(
                    group[
                        "relative_accuracy_degradation_mean"
                    ].mean()
                ),

            "relative_macro_f1_degradation":
                float(
                    group[
                        "relative_macro_f1_degradation_mean"
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


family_cross[
    "reliability_score_rank"
] = (
    family_cross
    .groupby(
        "family"
    )[
        "reliability_score"
    ]
    .rank(
        ascending=False,
        method="average"
    )
)


family_cross.to_csv(
    A /
    "family_cross_dataset_summary_36.csv",
    index=False
)


family_winners = []


for family in FAMILIES:

    subset = family_cross[
        family_cross[
            "family"
        ]
        ==
        family
    ]


    for metric in [
        "corrupted_accuracy",
        "corrupted_macro_f1",
        "reliability_score",
    ]:

        winner = subset.loc[
            subset[
                metric
            ].idxmax()
        ]


        family_winners.append(
            {
                "family":
                    family,

                "metric":
                    metric,

                "best_model":
                    winner[
                        "model"
                    ],

                "value":
                    float(
                        winner[
                            metric
                        ]
                    ),
            }
        )


family_winners_df = pd.DataFrame(
    family_winners
)


family_winners_df.to_csv(
    A /
    "family_winners_cross_dataset.csv",
    index=False
)


print(
    family_winners_df.to_string(
        index=False
    )
)


print()
print(
    "4. EFFICIENCY MODEL SUMMARY"
)
print(
    "-" * 78
)


eff_model = (
    efficiency
    .groupby(
        "model",
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

        gpu_b64_throughput_samples_per_s=(
            "gpu_b64_throughput_samples_per_s",
            "mean"
        ),

        gpu_b64_peak_total_memory_mb=(
            "gpu_b64_peak_total_memory_mb",
            "mean"
        ),
    )
)


eff_model.to_csv(
    A /
    "efficiency_model_summary_9.csv",
    index=False
)


print(
    eff_model
    .sort_values(
        "gpu_b1_median_ms"
    )
    .to_string(
        index=False
    )
)


print()
print(
    "5. MERGE PERFORMANCE + EFFICIENCY"
)
print(
    "-" * 78
)


decision = cross.merge(
    eff_model,
    on="model",
    how="inner"
)


if len(
    decision
) != 9:

    raise RuntimeError(
        f"Expected 9 merged models, "
        f"got {len(decision)}"
    )


decision.to_csv(
    A /
    "performance_efficiency_summary_9.csv",
    index=False
)


robustness_pareto = pareto_membership(
    decision,
    maximize=[
        "corrupted_accuracy_dataset_macro_mean",
        "corrupted_macro_f1_dataset_macro_mean",
    ],
    minimize=[
        "parameters",
        "gpu_b1_median_ms",
    ]
)


robustness_pareto.to_csv(
    A /
    "pareto_robustness_efficiency.csv",
    index=False
)


overall_pareto = pareto_membership(
    decision,
    maximize=[
        "clean_macro_f1_dataset_macro_mean",
        "corrupted_macro_f1_dataset_macro_mean",
    ],
    minimize=[
        "parameters",
        "gpu_b1_median_ms",
    ]
)


overall_pareto.to_csv(
    A /
    "pareto_overall.csv",
    index=False
)


print(
    "ROBUSTNESS_EFFICIENCY_PARETO_FRONT"
)


print(
    robustness_pareto[
        robustness_pareto[
            "pareto_front"
        ]
    ][
        [
            "model",
            "corrupted_accuracy_dataset_macro_mean",
            "corrupted_macro_f1_dataset_macro_mean",
            "parameters",
            "gpu_b1_median_ms"
        ]
    ]
    .to_string(
        index=False
    )
)


print()
print(
    "OVERALL_PARETO_FRONT"
)


print(
    overall_pareto[
        overall_pareto[
            "pareto_front"
        ]
    ][
        [
            "model",
            "clean_macro_f1_dataset_macro_mean",
            "corrupted_macro_f1_dataset_macro_mean",
            "parameters",
            "gpu_b1_median_ms"
        ]
    ]
    .to_string(
        index=False
    )
)


print()
print(
    "6. V24 KEY COMPETITOR EVIDENCE"
)
print(
    "-" * 78
)


key_competitors = [
    "DeepConvLSTM",
    "TCN",
    "CNN1D",
    "DS_CNN",
    "ReliabilityCNN_v22",
]


v24 = decision[
    decision[
        "model"
    ]
    ==
    "ReliabilityCNN_v24"
].iloc[
    0
]


key_rows = []


for competitor in key_competitors:

    other = decision[
        decision[
            "model"
        ]
        ==
        competitor
    ].iloc[
        0
    ]


    for metric in [
        "clean_accuracy_dataset_macro_mean",
        "clean_macro_f1_dataset_macro_mean",
        "reliability_score_dataset_macro_mean",
        "corrupted_accuracy_dataset_macro_mean",
        "corrupted_macro_f1_dataset_macro_mean",
    ]:

        key_rows.append(
            {
                "competitor":
                    competitor,

                "metric":
                    metric,

                "v24_value":
                    float(
                        v24[
                            metric
                        ]
                    ),

                "competitor_value":
                    float(
                        other[
                            metric
                        ]
                    ),

                "v24_minus_competitor":
                    float(
                        v24[
                            metric
                        ]
                        -
                        other[
                            metric
                        ]
                    ),
            }
        )


    key_rows.append(
        {
            "competitor":
                competitor,

            "metric":
                "parameter_ratio_v24_over_competitor",

            "v24_value":
                float(
                    v24[
                        "parameters"
                    ]
                ),

            "competitor_value":
                float(
                    other[
                        "parameters"
                    ]
                ),

            "v24_minus_competitor":
                float(
                    v24[
                        "parameters"
                    ]
                    /
                    other[
                        "parameters"
                    ]
                ),
        }
    )


    key_rows.append(
        {
            "competitor":
                competitor,

            "metric":
                "gpu_latency_ratio_v24_over_competitor",

            "v24_value":
                float(
                    v24[
                        "gpu_b1_median_ms"
                    ]
                ),

            "competitor_value":
                float(
                    other[
                        "gpu_b1_median_ms"
                    ]
                ),

            "v24_minus_competitor":
                float(
                    v24[
                        "gpu_b1_median_ms"
                    ]
                    /
                    other[
                        "gpu_b1_median_ms"
                    ]
                ),
        }
    )


v24_evidence = pd.DataFrame(
    key_rows
)


v24_evidence.to_csv(
    A /
    "v24_key_competitor_evidence.csv",
    index=False
)


print(
    v24_evidence.to_string(
        index=False
    )
)


print()
print(
    "7. V24 STATISTICAL WIN/LOSS SUMMARY"
)
print(
    "-" * 78
)


v24_stats = comparison_summary[
    comparison_summary[
        "anchor_model"
    ]
    ==
    "ReliabilityCNN_v24"
].copy()


v24_stats = v24_stats[
    v24_stats[
        "metric"
    ].isin(
        [
            "accuracy",
            "macro_f1",
            "corrupted_accuracy",
            "corrupted_macro_f1",
        ]
    )
]


print(
    v24_stats[
        [
            "competitor_model",
            "metric",
            "anchor_higher_datasets",
            "competitor_higher_datasets",
            "holm_significant_anchor_wins",
            "holm_significant_anchor_losses",
            "mean_difference_across_datasets",
        ]
    ]
    .sort_values(
        [
            "metric",
            "competitor_model"
        ]
    )
    .to_string(
        index=False
    )
)


print()
print(
    "8. V24 CORRUPTION-FAMILY RANKS"
)
print(
    "-" * 78
)


v24_family = family_cross[
    family_cross[
        "model"
    ]
    ==
    "ReliabilityCNN_v24"
][
    [
        "family",
        "reliability_score",
        "corrupted_accuracy",
        "corrupted_macro_f1",
        "reliability_score_rank",
        "corrupted_accuracy_rank",
        "corrupted_macro_f1_rank",
    ]
]


print(
    v24_family.to_string(
        index=False
    )
)


print()
print(
    "9. DECISION REPORT"
)
print(
    "-" * 78
)


robust_row = robustness_pareto[
    robustness_pareto[
        "model"
    ]
    ==
    "ReliabilityCNN_v24"
].iloc[
    0
]


overall_row = overall_pareto[
    overall_pareto[
        "model"
    ]
    ==
    "ReliabilityCNN_v24"
].iloc[
    0
]


deep = decision[
    decision[
        "model"
    ]
    ==
    "DeepConvLSTM"
].iloc[
    0
]


tcn = decision[
    decision[
        "model"
    ]
    ==
    "TCN"
].iloc[
    0
]


cnn = decision[
    decision[
        "model"
    ]
    ==
    "CNN1D"
].iloc[
    0
]


report_lines = []


report_lines.append(
    "BENCHMARK V3R1 METHOD-DECISION REPORT"
)

report_lines.append(
    "=" * 72
)

report_lines.append(
    ""
)

report_lines.append(
    "ReliabilityCNN_v24 cross-dataset performance:"
)

report_lines.append(
    (
        f"  clean accuracy      = "
        f"{v24['clean_accuracy_dataset_macro_mean']:.6f}"
    )
)

report_lines.append(
    (
        f"  clean macro-F1      = "
        f"{v24['clean_macro_f1_dataset_macro_mean']:.6f}"
    )
)

report_lines.append(
    (
        f"  corrupted accuracy  = "
        f"{v24['corrupted_accuracy_dataset_macro_mean']:.6f}"
    )
)

report_lines.append(
    (
        f"  corrupted macro-F1  = "
        f"{v24['corrupted_macro_f1_dataset_macro_mean']:.6f}"
    )
)

report_lines.append(
    (
        f"  reliability score   = "
        f"{v24['reliability_score_dataset_macro_mean']:.6f}"
    )
)

report_lines.append(
    ""
)

report_lines.append(
    "ReliabilityCNN_v24 efficiency:"
)

report_lines.append(
    (
        f"  parameters          = "
        f"{v24['parameters']:.0f}"
    )
)

report_lines.append(
    (
        f"  checkpoint MB       = "
        f"{v24['checkpoint_size_mb']:.6f}"
    )
)

report_lines.append(
    (
        f"  CPU B1 median ms    = "
        f"{v24['cpu_b1_median_ms']:.6f}"
    )
)

report_lines.append(
    (
        f"  GPU B1 median ms    = "
        f"{v24['gpu_b1_median_ms']:.6f}"
    )
)

report_lines.append(
    (
        f"  GPU B64 throughput  = "
        f"{v24['gpu_b64_throughput_samples_per_s']:.2f} samples/s"
    )
)

report_lines.append(
    ""
)

report_lines.append(
    "Closest robustness competitors:"
)

for name, row in [
    (
        "DeepConvLSTM",
        deep
    ),
    (
        "TCN",
        tcn
    ),
    (
        "CNN1D",
        cnn
    ),
]:

    report_lines.append(
        (
            f"  {name}: "
            f"corr_acc="
            f"{row['corrupted_accuracy_dataset_macro_mean']:.6f}, "
            f"corr_f1="
            f"{row['corrupted_macro_f1_dataset_macro_mean']:.6f}, "
            f"params="
            f"{row['parameters']:.0f}, "
            f"gpu_b1_ms="
            f"{row['gpu_b1_median_ms']:.6f}"
        )
    )


report_lines.append(
    ""
)

report_lines.append(
    (
        "Robustness-efficiency Pareto front: "
        f"{bool(robust_row['pareto_front'])}"
    )
)

report_lines.append(
    (
        "Overall clean+robustness+efficiency Pareto front: "
        f"{bool(overall_row['pareto_front'])}"
    )
)

report_lines.append(
    (
        "Robustness-efficiency dominated by: "
        f"{robust_row['dominated_by'] or 'NONE'}"
    )
)

report_lines.append(
    (
        "Overall dominated by: "
        f"{overall_row['dominated_by'] or 'NONE'}"
    )
)

report_lines.append(
    ""
)

report_lines.append(
    "Interpretation boundary:"
)

report_lines.append(
    (
        "  Latency measurements are comparative workstation "
        "measurements on this RTX 4090 / CPU environment, "
        "not embedded-device deployment measurements."
    )
)

report_lines.append(
    (
        "  Reliability score is relative to each model's own "
        "clean performance and must not be interpreted without "
        "absolute corrupted accuracy/F1."
    )
)

report_lines.append(
    ""
)

report_lines.append(
    (
        "DECISION_GATE: use paired significance, family-level "
        "behavior, Pareto membership, and efficiency ratios "
        "together before deciding whether v24 is final or "
        "whether a targeted efficiency-focused v25 is justified."
    )
)


report = "\n".join(
    report_lines
)


report_path = (
    A /
    "method_decision_report.txt"
)


report_path.write_text(
    report
    +
    "\n"
)


print(
    report
)


outputs = [
    A /
    "paired_seed_tests_holm.csv",

    A /
    "paired_comparison_summary.csv",

    A /
    "family_paired_tests_holm.csv",

    A /
    "family_cross_dataset_summary_36.csv",

    A /
    "family_winners_cross_dataset.csv",

    A /
    "efficiency_model_summary_9.csv",

    A /
    "performance_efficiency_summary_9.csv",

    A /
    "pareto_robustness_efficiency.csv",

    A /
    "pareto_overall.csv",

    A /
    "v24_key_competitor_evidence.csv",

    A /
    "method_decision_report.txt",
]


receipt = {
    "benchmark":
        "benchmark_v3r1",

    "analysis_stage":
        (
            "paired_statistics_family_behavior_"
            "efficiency_method_decision"
        ),

    "holm_multiple_comparison_correction":
        True,

    "family_level_paired_tests":
        True,

    "pareto_analysis_without_arbitrary_composite_score":
        True,

    "retraining":
        False,

    "outputs":
        {
            str(path):
                sha256_file(
                    path
                )
            for path in outputs
        },
}


receipt_path = (
    A /
    "method_decision_analysis_receipt.json"
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
    "=" * 78
)

print(
    "V3R1_METHOD_DECISION_ANALYSIS_PASS=True"
)

print(
    "HOLM_TEST_ROWS=",
    len(
        paired
    )
)

print(
    "FAMILY_TEST_ROWS=",
    len(
        family_tests
    )
)

print(
    "EFFICIENCY_MODELS=",
    len(
        eff_model
    )
)

print(
    "=" * 78
)
