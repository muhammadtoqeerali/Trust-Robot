from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from scipy.stats import (
        kendalltau,
        spearmanr,
        wilcoxon,
    )
except Exception as exc:
    raise RuntimeError(
        "SciPy unavailable in controlled environment. "
        "Do not install/change environment automatically. "
        f"Original error: {exc}"
    )


ROOT = Path(
    "/mnt/hdd16T/ToqeerHomeBackup/toqeer/IMU_Reliability"
)

R2 = (
    ROOT
    / "results/stage25_physical_fault_protocol"
    / "canonical_reconstruction_audit_r2"
)

R3 = (
    ROOT
    / "results/stage25_physical_fault_protocol"
    / "protocol_preregistration_r3"
)

R5 = (
    ROOT
    / "results/stage25_physical_fault_protocol"
    / "paired_domain_evaluation_r5"
)

OUT = (
    ROOT
    / "results/stage25_physical_fault_protocol"
    / "scientific_analysis_r6"
)

OUT.mkdir(
    parents=True,
    exist_ok=True,
)


CASES_PATH = (
    R5
    / "paired_domain_cases_7000.csv"
)

CHECKPOINT_DOMAIN_PATH = (
    R5
    / "checkpoint_domain_summary_400.csv"
)

DATASET_MODEL_DOMAIN_PATH = (
    R5
    / "dataset_model_domain_summary_80.csv"
)

EQUAL_DATASET_PATH = (
    R5
    / "equal_dataset_model_domain_summary_20.csv"
)

R5_RECEIPT_PATH = (
    R5
    / "stage25_paired_domain_evaluation_receipt_r5.json"
)

R3_PROTOCOL_PATH = (
    R3
    / "stage25_physical_fault_protocol_r3.json"
)

NORM_PATH = (
    R2
    / "dataset_normalization_receipts.json"
)


PRE = "pre_normalization_sensor_domain"
POST = "post_normalization_domain"

DATASETS = [
    "UCI_HAR",
    "PAMAP2",
    "DSADS",
    "MotionSense",
]

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
    "ReliabilityCNN_v25",
]

V25 = "ReliabilityCNN_v25"

METRICS = [
    "all_fault_accuracy",
    "all_fault_macro_f1",
    "recoverable_fault_accuracy",
    "recoverable_fault_macro_f1",
    "family_balanced_accuracy",
    "family_balanced_macro_f1",
]

COMMUTING_CONTROLS = {
    "acc_noise_sigma0.5",
    "gyro_noise_sigma0.5",
    "acc_stuck_value",
    "gyro_stuck_value",
}

NONCOMMUTING_FAMILIES = {
    "modality_outage",
    "single_axis_outage",
    "intermittent_dropout",
    "scale_drift",
}


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


def safe_spearman(
    x,
    y,
):
    x = np.asarray(
        x,
        dtype=float,
    )

    y = np.asarray(
        y,
        dtype=float,
    )

    if (
        len(x) < 3
        or
        np.all(
            x == x[0]
        )
        or
        np.all(
            y == y[0]
        )
    ):
        return (
            np.nan,
            np.nan,
        )

    result = spearmanr(
        x,
        y,
    )

    return (
        float(result.statistic),
        float(result.pvalue),
    )


def safe_kendall(
    x,
    y,
):
    x = np.asarray(
        x,
        dtype=float,
    )

    y = np.asarray(
        y,
        dtype=float,
    )

    if (
        len(x) < 3
        or
        np.all(
            x == x[0]
        )
        or
        np.all(
            y == y[0]
        )
    ):
        return (
            np.nan,
            np.nan,
        )

    result = kendalltau(
        x,
        y,
    )

    return (
        float(result.statistic),
        float(result.pvalue),
    )


def exactish_wilcoxon(
    pre,
    post,
):
    pre = np.asarray(
        pre,
        dtype=float,
    )

    post = np.asarray(
        post,
        dtype=float,
    )

    delta = pre - post

    nonzero = np.count_nonzero(
        delta
    )

    if nonzero == 0:
        return (
            0.0,
            1.0,
            0,
        )

    try:
        result = wilcoxon(
            pre,
            post,
            zero_method="wilcox",
            correction=False,
            alternative="two-sided",
            method="auto",
        )

        return (
            float(result.statistic),
            float(result.pvalue),
            int(nonzero),
        )

    except ValueError:
        return (
            np.nan,
            np.nan,
            int(nonzero),
        )


print("=" * 118)
print("STAGE25 R6 SCIENTIFIC ANALYSIS")
print("READ-ONLY ANALYSIS OF FROZEN R5")
print("NO MODEL LOAD / NO FORWARD / NO TRAINING")
print("=" * 118)


# ============================================================
# 1. R5 receipt validation
# ============================================================

r5_receipt = json.loads(
    R5_RECEIPT_PATH.read_text()
)

required_r5 = {
    "status":
        "PASS",

    "r4a_tensor_sha":
        "PASS_140_OF_140",

    "canonical_clean_tensor_identity":
        "PASS_4_OF_4",

    "frozen_model_bank":
        "PASS_200_OF_200",

    "clean_baseline_rows":
        200,

    "corrupted_forward_rows":
        6800,

    "total_analysis_rows":
        7000,

    "model_construction_count":
        200,

    "checkpoint_deserialization_count":
        200,

    "corrupted_forward_count":
        6800,

    "training_performed":
        False,

    "fault_definition_modified":
        False,

    "fault_severity_modified":
        False,

    "fault_seed_modified":
        False,

    "aggregation_modified":
        False,

    "v25_retrained":
        False,

    "storm_used_for_tuning":
        False,
}


for key, expected in required_r5.items():

    actual = r5_receipt.get(
        key
    )

    if actual != expected:

        raise RuntimeError(
            f"R5 receipt mismatch: "
            f"{key}={actual!r}, "
            f"expected={expected!r}"
        )


print(
    "R5_RECEIPT_PREREQUISITE_PASS=True"
)


# ============================================================
# 2. Load frozen R5 data
# ============================================================

cases = pd.read_csv(
    CASES_PATH
)

checkpoint_domain = pd.read_csv(
    CHECKPOINT_DOMAIN_PATH
)

dataset_model_domain = pd.read_csv(
    DATASET_MODEL_DOMAIN_PATH
)

equal_dataset = pd.read_csv(
    EQUAL_DATASET_PATH
)


if len(cases) != 7000:
    raise RuntimeError(
        f"Expected 7000 R5 rows, found {len(cases)}"
    )

if len(checkpoint_domain) != 400:
    raise RuntimeError(
        "checkpoint_domain_summary is not 400 rows"
    )

if len(dataset_model_domain) != 80:
    raise RuntimeError(
        "dataset_model_domain_summary is not 80 rows"
    )

if len(equal_dataset) != 20:
    raise RuntimeError(
        "equal_dataset summary is not 20 rows"
    )


identity_counts = (
    cases.groupby(
        [
            "dataset",
            "model",
            "seed",
        ]
    )
    .size()
)


if (
    len(identity_counts) != 200
    or
    not np.all(
        identity_counts.to_numpy()
        ==
        35
    )
):
    raise RuntimeError(
        "R5 checkpoint-case cardinality failed"
    )


domain_counts = (
    cases[
        "domain"
    ]
    .value_counts()
    .to_dict()
)


if int(
    domain_counts.get(
        "shared_clean",
        0,
    )
) != 200:
    raise RuntimeError(
        "Shared-clean row count changed"
    )

if int(
    domain_counts.get(
        PRE,
        0,
    )
) != 3400:
    raise RuntimeError(
        "Pre-domain row count changed"
    )

if int(
    domain_counts.get(
        POST,
        0,
    )
) != 3400:
    raise RuntimeError(
        "Post-domain row count changed"
    )


print(
    "R6_R5_CARDINALITY_GATE_PASS=True"
)


# ============================================================
# 3. POST-INFERENCE COMMUTING CONTROLS
#
# These are critical negative controls:
# identical tensors must produce identical predictions.
# ============================================================

control_rows = []

for (
    dataset,
    model,
    seed,
    condition,
), group in (
    cases[
        cases[
            "condition"
        ].isin(
            COMMUTING_CONTROLS
        )
    ]
    .groupby(
        [
            "dataset",
            "model",
            "seed",
            "condition",
        ]
    )
):

    pre = group[
        group[
            "domain"
        ]
        ==
        PRE
    ]

    post = group[
        group[
            "domain"
        ]
        ==
        POST
    ]


    if (
        len(pre) != 1
        or
        len(post) != 1
    ):
        raise RuntimeError(
            "Commuting-control pair cardinality failure"
        )


    pre = pre.iloc[0]
    post = post.iloc[0]


    tensor_same = (
        pre[
            "input_tensor_sha256"
        ]
        ==
        post[
            "input_tensor_sha256"
        ]
    )

    prediction_same = (
        pre[
            "prediction_sha256"
        ]
        ==
        post[
            "prediction_sha256"
        ]
    )

    accuracy_same = (
        float(
            pre[
                "accuracy"
            ]
        )
        ==
        float(
            post[
                "accuracy"
            ]
        )
    )

    f1_same = (
        float(
            pre[
                "macro_f1"
            ]
        )
        ==
        float(
            post[
                "macro_f1"
            ]
        )
    )


    control_rows.append({
        "dataset":
            dataset,

        "model":
            model,

        "seed":
            int(seed),

        "condition":
            condition,

        "input_tensor_identical":
            tensor_same,

        "prediction_identical":
            prediction_same,

        "accuracy_identical":
            accuracy_same,

        "macro_f1_identical":
            f1_same,
    })


controls = pd.DataFrame(
    control_rows
)


if len(controls) != 800:
    raise RuntimeError(
        f"Expected 800 commuting-control model pairs, "
        f"found {len(controls)}"
    )


for column in [
    "input_tensor_identical",
    "prediction_identical",
    "accuracy_identical",
    "macro_f1_identical",
]:

    if not controls[
        column
    ].all():

        bad = controls[
            ~controls[
                column
            ]
        ]

        raise RuntimeError(
            f"Post-inference commuting control failed "
            f"for {column}: "
            f"{len(bad)} cases"
        )


controls.to_csv(
    OUT
    / "post_inference_commuting_controls_800.csv",
    index=False,
)


print(
    "POST_INFERENCE_COMMUTING_CONTROLS_PASS_800_OF_800=True"
)


# ============================================================
# 4. Overall pre/post rankings
# ============================================================

overall_rank_rows = []

for metric in METRICS:

    for domain in [
        PRE,
        POST,
    ]:

        sub = (
            equal_dataset[
                equal_dataset[
                    "domain"
                ]
                ==
                domain
            ][
                [
                    "model",
                    metric,
                ]
            ]
            .copy()
        )


        if len(sub) != 10:
            raise RuntimeError(
                f"Expected 10 models for "
                f"{domain}/{metric}"
            )


        sub[
            "rank"
        ] = (
            sub[
                metric
            ]
            .rank(
                ascending=False,
                method="min",
            )
            .astype(int)
        )


        for _, row in sub.iterrows():

            overall_rank_rows.append({
                "metric":
                    metric,

                "domain":
                    domain,

                "model":
                    row[
                        "model"
                    ],

                "value":
                    float(
                        row[
                            metric
                        ]
                    ),

                "rank":
                    int(
                        row[
                            "rank"
                        ]
                    ),
            })


overall_ranks = pd.DataFrame(
    overall_rank_rows
)

overall_ranks.to_csv(
    OUT
    / "overall_equal_dataset_domain_ranks_120.csv",
    index=False,
)


rank_shift_rows = []
rank_corr_rows = []


for metric in METRICS:

    pre = (
        overall_ranks[
            (
                overall_ranks[
                    "metric"
                ]
                ==
                metric
            )
            &
            (
                overall_ranks[
                    "domain"
                ]
                ==
                PRE
            )
        ]
        .set_index(
            "model"
        )
        .sort_index()
    )

    post = (
        overall_ranks[
            (
                overall_ranks[
                    "metric"
                ]
                ==
                metric
            )
            &
            (
                overall_ranks[
                    "domain"
                ]
                ==
                POST
            )
        ]
        .set_index(
            "model"
        )
        .sort_index()
    )


    if list(
        pre.index
    ) != list(
        post.index
    ):
        raise RuntimeError(
            "Overall rank model alignment failed"
        )


    rho, rho_p = safe_spearman(
        pre[
            "value"
        ],
        post[
            "value"
        ],
    )

    tau, tau_p = safe_kendall(
        pre[
            "value"
        ],
        post[
            "value"
        ],
    )


    rank_corr_rows.append({
        "metric":
            metric,

        "n_models":
            10,

        "spearman_rho":
            rho,

        "spearman_p":
            rho_p,

        "kendall_tau":
            tau,

        "kendall_p":
            tau_p,

        "models_with_rank_change":
            int(
                np.sum(
                    pre[
                        "rank"
                    ].to_numpy()
                    !=
                    post[
                        "rank"
                    ].to_numpy()
                )
            ),
    })


    for model in pre.index:

        rank_shift_rows.append({
            "metric":
                metric,

            "model":
                model,

            "pre_value":
                float(
                    pre.loc[
                        model,
                        "value"
                    ]
                ),

            "post_value":
                float(
                    post.loc[
                        model,
                        "value"
                    ]
                ),

            "delta_pre_minus_post":
                float(
                    pre.loc[
                        model,
                        "value"
                    ]
                    -
                    post.loc[
                        model,
                        "value"
                    ]
                ),

            "pre_rank":
                int(
                    pre.loc[
                        model,
                        "rank"
                    ]
                ),

            "post_rank":
                int(
                    post.loc[
                        model,
                        "rank"
                    ]
                ),

            "rank_shift_pre_minus_post":
                int(
                    pre.loc[
                        model,
                        "rank"
                    ]
                    -
                    post.loc[
                        model,
                        "rank"
                    ]
                ),

            "rank_changed":
                bool(
                    pre.loc[
                        model,
                        "rank"
                    ]
                    !=
                    post.loc[
                        model,
                        "rank"
                    ]
                ),
        })


rank_shifts = pd.DataFrame(
    rank_shift_rows
)

rank_corr = pd.DataFrame(
    rank_corr_rows
)

rank_shifts.to_csv(
    OUT
    / "overall_domain_rank_shifts_60.csv",
    index=False,
)

rank_corr.to_csv(
    OUT
    / "overall_domain_rank_correlation_6.csv",
    index=False,
)


print(
    "OVERALL_DOMAIN_RANK_ANALYSIS_PASS=True"
)


# ============================================================
# 5. Dataset-specific rank stability
# ============================================================

dataset_rank_corr_rows = []

for dataset in DATASETS:

    for metric in METRICS:

        pre = (
            dataset_model_domain[
                (
                    dataset_model_domain[
                        "dataset"
                    ]
                    ==
                    dataset
                )
                &
                (
                    dataset_model_domain[
                        "domain"
                    ]
                    ==
                    PRE
                )
            ][
                [
                    "model",
                    metric,
                ]
            ]
            .set_index(
                "model"
            )
            .sort_index()
        )

        post = (
            dataset_model_domain[
                (
                    dataset_model_domain[
                        "dataset"
                    ]
                    ==
                    dataset
                )
                &
                (
                    dataset_model_domain[
                        "domain"
                    ]
                    ==
                    POST
                )
            ][
                [
                    "model",
                    metric,
                ]
            ]
            .set_index(
                "model"
            )
            .sort_index()
        )


        rho, rho_p = safe_spearman(
            pre[
                metric
            ],
            post[
                metric
            ],
        )

        tau, tau_p = safe_kendall(
            pre[
                metric
            ],
            post[
                metric
            ],
        )


        pre_rank = (
            pre[
                metric
            ]
            .rank(
                ascending=False,
                method="min",
            )
        )

        post_rank = (
            post[
                metric
            ]
            .rank(
                ascending=False,
                method="min",
            )
        )


        dataset_rank_corr_rows.append({
            "dataset":
                dataset,

            "metric":
                metric,

            "n_models":
                10,

            "spearman_rho":
                rho,

            "spearman_p":
                rho_p,

            "kendall_tau":
                tau,

            "kendall_p":
                tau_p,

            "models_with_rank_change":
                int(
                    np.sum(
                        pre_rank.to_numpy()
                        !=
                        post_rank.to_numpy()
                    )
                ),
        })


dataset_rank_corr = pd.DataFrame(
    dataset_rank_corr_rows
)

dataset_rank_corr.to_csv(
    OUT
    / "dataset_specific_domain_rank_correlation_24.csv",
    index=False,
)


# ============================================================
# 6. Fault-family summaries and family ranks
# ============================================================

fault_rows = cases[
    cases[
        "condition"
    ]
    !=
    "baseline"
].copy()


checkpoint_family = (
    fault_rows
    .groupby(
        [
            "dataset",
            "model",
            "seed",
            "domain",
            "family",
        ],
        as_index=False,
    )
    .agg(
        accuracy=(
            "accuracy",
            "mean",
        ),
        macro_f1=(
            "macro_f1",
            "mean",
        ),
    )
)


dataset_model_family = (
    checkpoint_family
    .groupby(
        [
            "dataset",
            "model",
            "domain",
            "family",
        ],
        as_index=False,
    )
    .agg(
        accuracy=(
            "accuracy",
            "mean",
        ),
        macro_f1=(
            "macro_f1",
            "mean",
        ),
    )
)


equal_family = (
    dataset_model_family
    .groupby(
        [
            "model",
            "domain",
            "family",
        ],
        as_index=False,
    )
    .agg(
        accuracy=(
            "accuracy",
            "mean",
        ),
        macro_f1=(
            "macro_f1",
            "mean",
        ),
    )
)


if len(equal_family) != 120:

    raise RuntimeError(
        f"Expected 120 model/domain/family rows, "
        f"found {len(equal_family)}"
    )


for metric in [
    "accuracy",
    "macro_f1",
]:

    equal_family[
        f"{metric}_rank"
    ] = (
        equal_family
        .groupby(
            [
                "domain",
                "family",
            ]
        )[
            metric
        ]
        .rank(
            ascending=False,
            method="min",
        )
        .astype(int)
    )


equal_family.to_csv(
    OUT
    / "equal_dataset_fault_family_summary_120.csv",
    index=False,
)


family_shift_rows = []

for family in sorted(
    equal_family[
        "family"
    ].unique()
):

    for metric in [
        "accuracy",
        "macro_f1",
    ]:

        pre = (
            equal_family[
                (
                    equal_family[
                        "family"
                    ]
                    ==
                    family
                )
                &
                (
                    equal_family[
                        "domain"
                    ]
                    ==
                    PRE
                )
            ]
            .set_index(
                "model"
            )
            .sort_index()
        )

        post = (
            equal_family[
                (
                    equal_family[
                        "family"
                    ]
                    ==
                    family
                )
                &
                (
                    equal_family[
                        "domain"
                    ]
                    ==
                    POST
                )
            ]
            .set_index(
                "model"
            )
            .sort_index()
        )


        for model in pre.index:

            family_shift_rows.append({
                "family":
                    family,

                "metric":
                    metric,

                "model":
                    model,

                "pre_value":
                    float(
                        pre.loc[
                            model,
                            metric
                        ]
                    ),

                "post_value":
                    float(
                        post.loc[
                            model,
                            metric
                        ]
                    ),

                "delta_pre_minus_post":
                    float(
                        pre.loc[
                            model,
                            metric
                        ]
                        -
                        post.loc[
                            model,
                            metric
                        ]
                    ),

                "pre_rank":
                    int(
                        pre.loc[
                            model,
                            f"{metric}_rank"
                        ]
                    ),

                "post_rank":
                    int(
                        post.loc[
                            model,
                            f"{metric}_rank"
                        ]
                    ),

                "rank_changed":
                    bool(
                        pre.loc[
                            model,
                            f"{metric}_rank"
                        ]
                        !=
                        post.loc[
                            model,
                            f"{metric}_rank"
                        ]
                    ),
            })


family_shifts = pd.DataFrame(
    family_shift_rows
)

family_shifts.to_csv(
    OUT
    / "fault_family_domain_rank_shifts_120.csv",
    index=False,
)


print(
    "FAULT_FAMILY_ANALYSIS_PASS=True"
)


# ============================================================
# 7. Condition-level equal-dataset summary
# ============================================================

checkpoint_condition = (
    fault_rows[
        [
            "dataset",
            "model",
            "seed",
            "domain",
            "condition",
            "family",
            "accuracy",
            "macro_f1",
        ]
    ]
    .copy()
)


dataset_model_condition = (
    checkpoint_condition
    .groupby(
        [
            "dataset",
            "model",
            "domain",
            "condition",
            "family",
        ],
        as_index=False,
    )
    .agg(
        accuracy=(
            "accuracy",
            "mean",
        ),
        macro_f1=(
            "macro_f1",
            "mean",
        ),
    )
)


equal_condition = (
    dataset_model_condition
    .groupby(
        [
            "model",
            "domain",
            "condition",
            "family",
        ],
        as_index=False,
    )
    .agg(
        accuracy=(
            "accuracy",
            "mean",
        ),
        macro_f1=(
            "macro_f1",
            "mean",
        ),
    )
)


if len(equal_condition) != 340:

    raise RuntimeError(
        f"Expected 340 condition summary rows, "
        f"found {len(equal_condition)}"
    )


for metric in [
    "accuracy",
    "macro_f1",
]:

    equal_condition[
        f"{metric}_rank"
    ] = (
        equal_condition
        .groupby(
            [
                "domain",
                "condition",
            ]
        )[
            metric
        ]
        .rank(
            ascending=False,
            method="min",
        )
        .astype(int)
    )


equal_condition.to_csv(
    OUT
    / "equal_dataset_condition_summary_340.csv",
    index=False,
)


# ============================================================
# 8. Five-seed paired pre/post Wilcoxon by dataset/model
#
# IMPORTANT:
# n=5 tests are retained as small-sample evidence.
# Do not interpret non-significance as equivalence.
# ============================================================

wilcoxon_rows = []

for dataset in DATASETS:

    for model in MODELS:

        sub = checkpoint_domain[
            (
                checkpoint_domain[
                    "dataset"
                ]
                ==
                dataset
            )
            &
            (
                checkpoint_domain[
                    "model"
                ]
                ==
                model
            )
        ].copy()


        for metric in METRICS:

            pre = (
                sub[
                    sub[
                        "domain"
                    ]
                    ==
                    PRE
                ][
                    [
                        "seed",
                        metric,
                    ]
                ]
                .sort_values(
                    "seed"
                )
            )

            post = (
                sub[
                    sub[
                        "domain"
                    ]
                    ==
                    POST
                ][
                    [
                        "seed",
                        metric,
                    ]
                ]
                .sort_values(
                    "seed"
                )
            )


            if (
                len(pre) != 5
                or
                len(post) != 5
                or
                list(
                    pre[
                        "seed"
                    ]
                )
                !=
                list(
                    post[
                        "seed"
                    ]
                )
            ):
                raise RuntimeError(
                    f"Five-seed pairing failed: "
                    f"{dataset}/{model}/{metric}"
                )


            pre_values = pre[
                metric
            ].to_numpy(
                dtype=float
            )

            post_values = post[
                metric
            ].to_numpy(
                dtype=float
            )

            delta = (
                pre_values
                -
                post_values
            )


            statistic, pvalue, n_nonzero = (
                exactish_wilcoxon(
                    pre_values,
                    post_values,
                )
            )


            wilcoxon_rows.append({
                "dataset":
                    dataset,

                "model":
                    model,

                "metric":
                    metric,

                "n_seed_pairs":
                    5,

                "n_nonzero_pairs":
                    n_nonzero,

                "mean_pre":
                    float(
                        np.mean(
                            pre_values
                        )
                    ),

                "mean_post":
                    float(
                        np.mean(
                            post_values
                        )
                    ),

                "mean_delta_pre_minus_post":
                    float(
                        np.mean(
                            delta
                        )
                    ),

                "median_delta_pre_minus_post":
                    float(
                        np.median(
                            delta
                        )
                    ),

                "positive_delta_count":
                    int(
                        np.sum(
                            delta > 0
                        )
                    ),

                "negative_delta_count":
                    int(
                        np.sum(
                            delta < 0
                        )
                    ),

                "zero_delta_count":
                    int(
                        np.sum(
                            delta == 0
                        )
                    ),

                "wilcoxon_statistic":
                    statistic,

                "wilcoxon_two_sided_p":
                    pvalue,

                "interpretation_constraint":
                    (
                        "n=5; non-significance is not "
                        "evidence of equivalence"
                    ),
            })


wilcoxon_df = pd.DataFrame(
    wilcoxon_rows
)


if len(wilcoxon_df) != 240:

    raise RuntimeError(
        f"Expected 240 n=5 paired tests, "
        f"found {len(wilcoxon_df)}"
    )


wilcoxon_df.to_csv(
    OUT
    / "dataset_model_domain_wilcoxon_n5_240.csv",
    index=False,
)


print(
    "PAIRED_DOMAIN_WILCOXON_N5_ANALYSIS_PASS_240=True"
)


# ============================================================
# 9. V25 HELD-OUT PRIMARY ANALYSIS
#
# Held-out mask:
# PAMAP2 + MotionSense all five seeds,
# UCI + DSADS seeds 789/2026.
#
# Apply SAME mask to every baseline for matched comparison.
# ============================================================

def heldout_mask(
    frame,
):
    return (
        frame[
            "dataset"
        ].isin(
            [
                "PAMAP2",
                "MotionSense",
            ]
        )
        |
        (
            frame[
                "dataset"
            ].isin(
                [
                    "UCI_HAR",
                    "DSADS",
                ]
            )
            &
            frame[
                "seed"
            ].isin(
                [
                    789,
                    2026,
                ]
            )
        )
    )


def development_mask(
    frame,
):
    return (
        frame[
            "dataset"
        ].isin(
            [
                "UCI_HAR",
                "DSADS",
            ]
        )
        &
        frame[
            "seed"
        ].isin(
            [
                42,
                123,
                456,
            ]
        )
    )


heldout = checkpoint_domain[
    heldout_mask(
        checkpoint_domain
    )
].copy()


# 14 seed/dataset checkpoints × 10 models × 2 domains.
if len(heldout) != 280:

    raise RuntimeError(
        f"Held-out matched checkpoint/domain "
        f"row count expected 280, found {len(heldout)}"
    )


heldout_dataset = (
    heldout
    .groupby(
        [
            "dataset",
            "model",
            "domain",
        ],
        as_index=False,
    )[
        METRICS
    ]
    .mean()
)


heldout_equal = (
    heldout_dataset
    .groupby(
        [
            "model",
            "domain",
        ],
        as_index=False,
    )[
        METRICS
    ]
    .mean()
)


if len(heldout_equal) != 20:

    raise RuntimeError(
        "Held-out equal-dataset summary not 20"
    )


for metric in METRICS:

    heldout_equal[
        f"{metric}_rank"
    ] = (
        heldout_equal
        .groupby(
            "domain"
        )[
            metric
        ]
        .rank(
            ascending=False,
            method="min",
        )
        .astype(int)
    )


heldout_equal.to_csv(
    OUT
    / "heldout_matched_equal_dataset_summary_20.csv",
    index=False,
)


# V25 vs every baseline on primary physical domain.
v25_pre = heldout_equal[
    (
        heldout_equal[
            "model"
        ]
        ==
        V25
    )
    &
    (
        heldout_equal[
            "domain"
        ]
        ==
        PRE
    )
]


if len(v25_pre) != 1:
    raise RuntimeError(
        "Held-out V25 pre-domain row missing"
    )


v25_pre = v25_pre.iloc[0]


heldout_comparison_rows = []

for model in MODELS:

    if model == V25:
        continue


    baseline = heldout_equal[
        (
            heldout_equal[
                "model"
            ]
            ==
            model
        )
        &
        (
            heldout_equal[
                "domain"
            ]
            ==
            PRE
        )
    ]


    if len(baseline) != 1:
        raise RuntimeError(
            f"Held-out baseline missing: {model}"
        )


    baseline = baseline.iloc[0]


    item = {
        "baseline":
            model,
    }


    for metric in METRICS:

        item[
            f"v25_{metric}"
        ] = float(
            v25_pre[
                metric
            ]
        )

        item[
            f"baseline_{metric}"
        ] = float(
            baseline[
                metric
            ]
        )

        item[
            f"v25_minus_baseline_{metric}"
        ] = float(
            v25_pre[
                metric
            ]
            -
            baseline[
                metric
            ]
        )


    heldout_comparison_rows.append(
        item
    )


heldout_comparison = pd.DataFrame(
    heldout_comparison_rows
)

heldout_comparison.to_csv(
    OUT
    / "v25_heldout_pre_domain_vs_baselines_9.csv",
    index=False,
)


# Development stratum descriptive only.
development = checkpoint_domain[
    development_mask(
        checkpoint_domain
    )
].copy()


if len(development) != 120:

    raise RuntimeError(
        "Development matched row count expected 120"
    )


development_dataset = (
    development
    .groupby(
        [
            "dataset",
            "model",
            "domain",
        ],
        as_index=False,
    )[
        METRICS
    ]
    .mean()
)


development_equal = (
    development_dataset
    .groupby(
        [
            "model",
            "domain",
        ],
        as_index=False,
    )[
        METRICS
    ]
    .mean()
)


development_equal.to_csv(
    OUT
    / "development_matched_two_dataset_summary_20.csv",
    index=False,
)


print(
    "V25_HELDOUT_MATCHED_ANALYSIS_PASS=True"
)


# ============================================================
# 10. HELD-OUT FAULT-FAMILY RANKING
# ============================================================

heldout_fault_rows = fault_rows[
    heldout_mask(
        fault_rows
    )
].copy()


heldout_checkpoint_family = (
    heldout_fault_rows
    .groupby(
        [
            "dataset",
            "model",
            "seed",
            "domain",
            "family",
        ],
        as_index=False,
    )
    .agg(
        accuracy=(
            "accuracy",
            "mean",
        ),
        macro_f1=(
            "macro_f1",
            "mean",
        ),
    )
)


heldout_dataset_family = (
    heldout_checkpoint_family
    .groupby(
        [
            "dataset",
            "model",
            "domain",
            "family",
        ],
        as_index=False,
    )
    .agg(
        accuracy=(
            "accuracy",
            "mean",
        ),
        macro_f1=(
            "macro_f1",
            "mean",
        ),
    )
)


heldout_equal_family = (
    heldout_dataset_family
    .groupby(
        [
            "model",
            "domain",
            "family",
        ],
        as_index=False,
    )
    .agg(
        accuracy=(
            "accuracy",
            "mean",
        ),
        macro_f1=(
            "macro_f1",
            "mean",
        ),
    )
)


if len(
    heldout_equal_family
) != 120:

    raise RuntimeError(
        "Held-out family summary expected 120 rows"
    )


for metric in [
    "accuracy",
    "macro_f1",
]:

    heldout_equal_family[
        f"{metric}_rank"
    ] = (
        heldout_equal_family
        .groupby(
            [
                "domain",
                "family",
            ]
        )[
            metric
        ]
        .rank(
            ascending=False,
            method="min",
        )
        .astype(int)
    )


heldout_equal_family.to_csv(
    OUT
    / "heldout_matched_fault_family_summary_120.csv",
    index=False,
)


# ============================================================
# 11. NORMALIZATION-OFFSET MECHANISM
#
# Predictor uses frozen train normalization:
# physical zero in normalized coordinates = -mu / sigma.
#
# For each noncommuting condition:
# outage/single-axis -> |offset|
# dropout -> p * |offset|
# scale drift -> mean_t |a_t - 1| * |offset|
#
# Correlate that preregistered algebraic displacement with
# observed absolute pre/post metric change.
# ============================================================

normalization = json.loads(
    NORM_PATH.read_text()
)

protocol = json.loads(
    R3_PROTOCOL_PATH.read_text()
)

fault_protocol = {
    row[
        "name"
    ]:
        row

    for row in protocol[
        "fault_conditions"
    ]
}


mechanism_rows = []


for dataset in DATASETS:

    mean = np.asarray(
        normalization[
            dataset
        ][
            "mean"
        ],
        dtype=float,
    )

    std = np.asarray(
        normalization[
            dataset
        ][
            "std"
        ],
        dtype=float,
    )

    zero_offset = (
        -mean
        /
        std
    )


    for condition, fault in fault_protocol.items():

        family = fault[
            "family"
        ]


        if family not in NONCOMMUTING_FAMILIES:
            continue


        channels = np.asarray(
            fault[
                "channels"
            ],
            dtype=int,
        )


        base_offset = float(
            np.mean(
                np.abs(
                    zero_offset[
                        channels
                    ]
                )
            )
        )


        if family in {
            "modality_outage",
            "single_axis_outage",
        }:

            algebraic_displacement = (
                base_offset
            )


        elif family == "intermittent_dropout":

            p = float(
                fault[
                    "drop_probability"
                ]
            )

            algebraic_displacement = (
                p
                *
                base_offset
            )


        elif family == "scale_drift":

            factors = np.linspace(
                float(
                    fault[
                        "start_factor"
                    ]
                ),
                float(
                    fault[
                        "end_factor"
                    ]
                ),
                128,
                dtype=float,
            )

            mean_factor_delta = float(
                np.mean(
                    np.abs(
                        factors
                        -
                        1.0
                    )
                )
            )

            algebraic_displacement = (
                mean_factor_delta
                *
                base_offset
            )


        else:
            raise RuntimeError(
                f"Unhandled noncommuting family: {family}"
            )


        sub = fault_rows[
            (
                fault_rows[
                    "dataset"
                ]
                ==
                dataset
            )
            &
            (
                fault_rows[
                    "condition"
                ]
                ==
                condition
            )
        ][
            [
                "model",
                "seed",
                "domain",
                "accuracy",
                "macro_f1",
            ]
        ]


        pivot_acc = sub.pivot(
            index=[
                "model",
                "seed",
            ],
            columns="domain",
            values="accuracy",
        )

        pivot_f1 = sub.pivot(
            index=[
                "model",
                "seed",
            ],
            columns="domain",
            values="macro_f1",
        )


        if (
            len(pivot_acc) != 50
            or
            len(pivot_f1) != 50
        ):
            raise RuntimeError(
                f"{dataset}/{condition}: "
                "expected 50 checkpoint pairs"
            )


        delta_acc = (
            pivot_acc[
                PRE
            ]
            -
            pivot_acc[
                POST
            ]
        )

        delta_f1 = (
            pivot_f1[
                PRE
            ]
            -
            pivot_f1[
                POST
            ]
        )


        mechanism_rows.append({
            "dataset":
                dataset,

            "condition":
                condition,

            "family":
                family,

            "channels":
                ",".join(
                    str(int(x))
                    for x in channels
                ),

            "mean_abs_zero_offset_selected":
                base_offset,

            "algebraic_displacement_predictor":
                algebraic_displacement,

            "n_checkpoint_pairs":
                50,

            "mean_signed_accuracy_delta_pre_minus_post":
                float(
                    delta_acc.mean()
                ),

            "mean_abs_accuracy_delta":
                float(
                    np.abs(
                        delta_acc
                    ).mean()
                ),

            "max_abs_accuracy_delta":
                float(
                    np.abs(
                        delta_acc
                    ).max()
                ),

            "mean_signed_macro_f1_delta_pre_minus_post":
                float(
                    delta_f1.mean()
                ),

            "mean_abs_macro_f1_delta":
                float(
                    np.abs(
                        delta_f1
                    ).mean()
                ),

            "max_abs_macro_f1_delta":
                float(
                    np.abs(
                        delta_f1
                    ).max()
                ),
        })


mechanism = pd.DataFrame(
    mechanism_rows
)


if len(mechanism) != 52:

    raise RuntimeError(
        f"Expected 52 dataset-condition mechanism rows, "
        f"found {len(mechanism)}"
    )


mechanism.to_csv(
    OUT
    / "normalization_offset_mechanism_52.csv",
    index=False,
)


mechanism_corr_rows = []


for family in [
    "ALL_NONCOMMUTING",
    "modality_outage",
    "single_axis_outage",
    "intermittent_dropout",
    "scale_drift",
]:

    if family == "ALL_NONCOMMUTING":

        sub = mechanism

    else:

        sub = mechanism[
            mechanism[
                "family"
            ]
            ==
            family
        ]


    for metric in [
        "mean_abs_accuracy_delta",
        "mean_abs_macro_f1_delta",
    ]:

        rho, rho_p = safe_spearman(
            sub[
                "algebraic_displacement_predictor"
            ],
            sub[
                metric
            ],
        )

        tau, tau_p = safe_kendall(
            sub[
                "algebraic_displacement_predictor"
            ],
            sub[
                metric
            ],
        )


        mechanism_corr_rows.append({
            "family":
                family,

            "metric":
                metric,

            "n_dataset_condition_points":
                len(sub),

            "spearman_rho":
                rho,

            "spearman_p":
                rho_p,

            "kendall_tau":
                tau,

            "kendall_p":
                tau_p,

            "interpretation":
                (
                    "mechanism-consistency analysis; "
                    "not causal proof"
                ),
        })


mechanism_corr = pd.DataFrame(
    mechanism_corr_rows
)

mechanism_corr.to_csv(
    OUT
    / "normalization_offset_mechanism_correlations_10.csv",
    index=False,
)


print(
    "NORMALIZATION_OFFSET_MECHANISM_ANALYSIS_PASS=True"
)


# ============================================================
# 12. V25 held-out family failure map
# ============================================================

v25_heldout_family = (
    heldout_equal_family[
        (
            heldout_equal_family[
                "model"
            ]
            ==
            V25
        )
        &
        (
            heldout_equal_family[
                "domain"
            ]
            ==
            PRE
        )
    ]
    .sort_values(
        "macro_f1",
        ascending=False,
    )
    .copy()
)


if len(v25_heldout_family) != 6:

    raise RuntimeError(
        "V25 held-out physical family map not six rows"
    )


v25_heldout_family.to_csv(
    OUT
    / "v25_heldout_physical_family_failure_map_6.csv",
    index=False,
)


# ============================================================
# 13. Compact scientific printout
# ============================================================

print()
print("=" * 118)
print("PRIMARY PHYSICAL-DOMAIN OVERALL RANKINGS")
print("=" * 118)

for metric in [
    "all_fault_macro_f1",
    "family_balanced_macro_f1",
    "all_fault_accuracy",
]:

    print()
    print(
        "METRIC=",
        metric,
    )

    table = (
        overall_ranks[
            (
                overall_ranks[
                    "metric"
                ]
                ==
                metric
            )
            &
            (
                overall_ranks[
                    "domain"
                ]
                ==
                PRE
            )
        ]
        .sort_values(
            [
                "rank",
                "model",
            ]
        )
    )


    for _, row in table.iterrows():

        print(
            "  RANK",
            int(
                row[
                    "rank"
                ]
            ),
            row[
                "model"
            ],
            f"{row['value']:.9f}",
        )


print()
print("=" * 118)
print("PRE-vs-POST RANK STABILITY")
print("=" * 118)

for _, row in rank_corr.iterrows():

    print(
        "RANK_CORRELATION:",
        row[
            "metric"
        ],
        "SPEARMAN=",
        f"{row['spearman_rho']:.6f}",
        "KENDALL=",
        f"{row['kendall_tau']:.6f}",
        "MODELS_RANK_CHANGED=",
        int(
            row[
                "models_with_rank_change"
            ]
        ),
        "/10",
    )


print()
print("=" * 118)
print("V25 HELD-OUT PRIMARY PHYSICAL-DOMAIN POSITION")
print("=" * 118)

v25_held = heldout_equal[
    (
        heldout_equal[
            "model"
        ]
        ==
        V25
    )
    &
    (
        heldout_equal[
            "domain"
        ]
        ==
        PRE
    )
].iloc[0]


for metric in [
    "all_fault_accuracy",
    "all_fault_macro_f1",
    "recoverable_fault_accuracy",
    "recoverable_fault_macro_f1",
    "family_balanced_accuracy",
    "family_balanced_macro_f1",
]:

    print(
        "V25_HELDOUT:",
        metric,
        "=",
        f"{v25_held[metric]:.9f}",
        "RANK=",
        int(
            v25_held[
                f"{metric}_rank"
            ]
        ),
        "/10",
    )


print()
print("=" * 118)
print("V25 HELD-OUT PHYSICAL FAULT-FAMILY MAP")
print("=" * 118)

for _, row in (
    v25_heldout_family
    .sort_values(
        "macro_f1_rank"
    )
    .iterrows()
):

    print(
        "V25_FAMILY:",
        row[
            "family"
        ],
        "ACC=",
        f"{row['accuracy']:.9f}",
        "ACC_RANK=",
        int(
            row[
                "accuracy_rank"
            ]
        ),
        "F1=",
        f"{row['macro_f1']:.9f}",
        "F1_RANK=",
        int(
            row[
                "macro_f1_rank"
            ]
        ),
    )


print()
print("=" * 118)
print("LARGEST NORMALIZATION-DOMAIN EFFECTS")
print("=" * 118)

for _, row in (
    mechanism
    .sort_values(
        "mean_abs_macro_f1_delta",
        ascending=False,
    )
    .head(
        15
    )
    .iterrows()
):

    print(
        "DOMAIN_EFFECT:",
        row[
            "dataset"
        ],
        row[
            "condition"
        ],
        row[
            "family"
        ],
        "PREDICTOR=",
        f"{row['algebraic_displacement_predictor']:.9f}",
        "MEAN_ABS_DACC=",
        f"{row['mean_abs_accuracy_delta']:.9f}",
        "MEAN_ABS_DF1=",
        f"{row['mean_abs_macro_f1_delta']:.9f}",
    )


print()
print("=" * 118)
print("NORMALIZATION-OFFSET MECHANISM CORRELATIONS")
print("=" * 118)

for _, row in mechanism_corr.iterrows():

    print(
        "MECHANISM_CORR:",
        row[
            "family"
        ],
        row[
            "metric"
        ],
        "N=",
        int(
            row[
                "n_dataset_condition_points"
            ]
        ),
        "SPEARMAN=",
        (
            "nan"
            if pd.isna(
                row[
                    "spearman_rho"
                ]
            )
            else
            f"{row['spearman_rho']:.6f}"
        ),
        "KENDALL=",
        (
            "nan"
            if pd.isna(
                row[
                    "kendall_tau"
                ]
            )
            else
            f"{row['kendall_tau']:.6f}"
        ),
    )


print()
print("=" * 118)
print("N=5 WILCOXON LIMIT")
print("=" * 118)

finite_p = wilcoxon_df[
    "wilcoxon_two_sided_p"
].dropna()


if len(finite_p):

    print(
        "MIN_N5_TWO_SIDED_WILCOXON_P=",
        float(
            finite_p.min()
        ),
    )

else:

    print(
        "MIN_N5_TWO_SIDED_WILCOXON_P=nan"
    )


print(
    "N5_NON_SIGNIFICANCE_IS_NOT_EQUIVALENCE=True"
)


# ============================================================
# 14. Final receipt
# ============================================================

receipt = {
    "analysis":
        "STAGE25_SCIENTIFIC_ANALYSIS_R6",

    "status":
        "PASS",

    "r5_frozen_input":
        "PASS",

    "r5_total_rows_verified":
        7000,

    "post_inference_commuting_controls":
        "PASS_800_OF_800",

    "overall_domain_rank_rows":
        120,

    "overall_rank_shift_rows":
        60,

    "overall_rank_correlation_rows":
        6,

    "dataset_rank_correlation_rows":
        24,

    "equal_dataset_fault_family_rows":
        120,

    "fault_family_rank_shift_rows":
        120,

    "equal_dataset_condition_rows":
        340,

    "paired_domain_wilcoxon_n5_rows":
        240,

    "v25_heldout_matched_primary":
        True,

    "v25_heldout_checkpoint_count":
        14,

    "v25_development_checkpoint_count":
        6,

    "heldout_seed_mask_applied_to_baselines":
        True,

    "normalization_offset_mechanism_rows":
        52,

    "normalization_offset_correlation_rows":
        10,

    "model_deserialization_performed":
        False,

    "model_forward_performed":
        False,

    "training_performed":
        False,

    "optimizer_created":
        False,

    "backward_performed":
        False,

    "checkpoint_modified":
        False,

    "dataset_modified":
        False,

    "fault_protocol_modified":
        False,

    "v25_retrained":
        False,

    "storm_used_for_tuning":
        False,

    "claim_constraints": [
        (
            "V25 held-out 14-checkpoint stratum is primary; "
            "all-20 V25 summary is descriptive."
        ),
        (
            "n=5 Wilcoxon non-significance must not be "
            "presented as equivalence."
        ),
        (
            "Normalization-offset correlation is "
            "mechanism-consistency evidence, not causal proof."
        ),
        (
            "Historical V2, Stage24, and Stage25 fault "
            "protocols remain separate."
        ),
    ],

    "next_gate":
        (
            "Interpret and freeze R6 scientific findings. "
            "Then open a NEW V26/V27 development protocol "
            "using only development data/seeds, with "
            "physical-domain corrupted-gradient training "
            "and no STORM-guided tuning."
        ),
}


write_json(
    OUT
    / "stage25_scientific_analysis_receipt_r6.json",
    receipt,
)


print()
print("=" * 118)
print("STAGE25 R6 FINAL RECEIPT")
print("=" * 118)

print(
    json.dumps(
        receipt,
        indent=2,
    )
)

print()
print(
    "STAGE25_SCIENTIFIC_ANALYSIS_R6_PASS=True"
)

print(
    "POST_INFERENCE_COMMUTING_CONTROLS_PASS_800_OF_800=True"
)

print(
    "V25_HELDOUT_PRIMARY_ANALYSIS_COMPLETE=True"
)

print(
    "NORMALIZATION_OFFSET_MECHANISM_ANALYSIS_COMPLETE=True"
)

print(
    "MODEL_FORWARD_PERFORMED=False"
)

print(
    "TRAINING_PERFORMED=False"
)

print(
    "V25_RETRAINED=False"
)

print(
    "STORM_USED_FOR_TUNING=False"
)
