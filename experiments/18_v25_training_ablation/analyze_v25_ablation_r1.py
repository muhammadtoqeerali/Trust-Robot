from pathlib import Path
import hashlib
import json
import sys

import numpy as np
import pandas as pd


REPO = Path.cwd()

EXP = (
    REPO /
    "experiments" /
    "18_v25_training_ablation"
)

ABL = (
    REPO /
    "results" /
    "v25_ablation_r1"
)

SCREEN = (
    REPO /
    "results" /
    "v25_screening_r1"
)

OUT = (
    ABL /
    "final_analysis"
)

MANIFEST = (
    ABL /
    "protocol" /
    "protocol_manifest.json"
)

SCREEN_RECEIPT = (
    SCREEN /
    "final_analysis" /
    "v25_screening_r1_analysis_receipt.json"
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

SEEDS = [
    42,
    123,
    456,
]

MODES = [
    "clean_ce",
    "exposure",
    "consistency",
]

FAMILIES = [
    "missing_channel",
    "random_dropout",
    "gaussian_noise",
    "sensor_drift",
]

COMPARISONS = [
    (
        "exposure",
        "clean_ce"
    ),
    (
        "consistency",
        "clean_ce"
    ),
    (
        "consistency",
        "exposure"
    ),
]

METRICS = [
    "clean_accuracy",
    "clean_macro_f1",
    "reliability_score",
    "corrupted_accuracy",
    "corrupted_macro_f1",
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
warnings = []


def require(
    condition,
    message
):

    if not condition:

        errors.append(
            message
        )


print(
    "=" * 82
)

print(
    "V25 TRAINING ABLATION R1 — FINAL ANALYSIS"
)

print(
    "=" * 82
)


# ==========================================================
# 1. PROTOCOL INTEGRITY
# ==========================================================

print()
print(
    "1. PROTOCOL + FROZEN HASH INTEGRITY"
)
print(
    "-" * 82
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


expected_hashes = manifest[
    "hashes"
]


verified_hashes = 0


for relative, expected_sha in (
    expected_hashes.items()
):

    path = (
        REPO /
        relative
    )


    require(
        path.exists(),
        f"Missing frozen file: {relative}"
    )


    if not path.exists():
        continue


    actual_sha = sha256_file(
        path
    )


    require(
        actual_sha == expected_sha,
        f"Frozen SHA mismatch: {relative}"
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
        expected_hashes
    )
)

print(
    "FROZEN_HASHES_VERIFIED=",
    verified_hashes
)


# ==========================================================
# 2. SCREENING CONTROL INTEGRITY
# ==========================================================

print()
print(
    "2. CLEAN-CE CONTROL INTEGRITY"
)
print(
    "-" * 82
)


require(
    SCREEN_RECEIPT.exists(),
    f"Missing screening receipt: {SCREEN_RECEIPT}"
)


screen_receipt = load_json(
    SCREEN_RECEIPT
)


require(
    screen_receipt.get(
        "integrity_pass"
    )
    is True,
    "Screening control receipt is not integrity_pass=true"
)


print(
    "SCREENING_CONTROL_INTEGRITY_PASS=",
    screen_receipt.get(
        "integrity_pass"
    )
)


# ==========================================================
# 3. VERIFY 12 NEW TRAINING + 12 RELIABILITY RUNS
# ==========================================================

print()
print(
    "3. VERIFY NEW ABLATION RUNS"
)
print(
    "-" * 82
)


training_verified = 0

reliability_verified = 0


for dataset in DATASETS:

    for mode in [
        "exposure",
        "consistency",
    ]:

        for seed in SEEDS:

            run_dir = (
                ABL /
                "raw_runs" /
                dataset /
                mode /
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
                p.exists()
                for p in required
            ):

                receipt = load_json(
                    run_dir /
                    "receipt.json"
                )


                metrics = load_json(
                    run_dir /
                    "metrics.json"
                )


                require(
                    receipt.get(
                        "protocol_manifest_sha256"
                    )
                    ==
                    protocol_sha,
                    (
                        "Training protocol SHA mismatch: "
                        f"{dataset}/{mode}/{seed}"
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
                        "Checkpoint SHA mismatch: "
                        f"{dataset}/{mode}/{seed}"
                    )
                )


                require(
                    receipt.get(
                        "corruption_schedule_sha256"
                    )
                    ==
                    metrics.get(
                        "corruption_schedule_sha256"
                    ),
                    (
                        "Schedule SHA receipt mismatch: "
                        f"{dataset}/{mode}/{seed}"
                    )
                )


                training_verified += 1


            rel_dir = (
                ABL /
                "reliability_v2" /
                dataset /
                mode /
                f"seed_{seed}"
            )


            rel_required = [

                rel_dir /
                "COMPLETE",

                rel_dir /
                "reliability_summary_v2.json",

                rel_dir /
                "ablation_receipt.json",
            ]


            for path in rel_required:

                require(
                    path.exists(),
                    f"Missing reliability artifact: {path}"
                )


            if all(
                p.exists()
                for p in rel_required
            ):

                rel_receipt = load_json(
                    rel_dir /
                    "ablation_receipt.json"
                )


                rel_summary = load_json(
                    rel_dir /
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
                        f"{dataset}/{mode}/{seed}"
                    )
                )


                require(
                    rel_receipt.get(
                        "registry_sha256"
                    )
                    ==
                    sha256_file(
                        REGISTRY
                    ),
                    (
                        "Registry SHA mismatch: "
                        f"{dataset}/{mode}/{seed}"
                    )
                )


                require(
                    rel_receipt.get(
                        "summary_sha256"
                    )
                    ==
                    sha256_file(
                        rel_dir /
                        "reliability_summary_v2.json"
                    ),
                    (
                        "Reliability summary SHA mismatch: "
                        f"{dataset}/{mode}/{seed}"
                    )
                )


                require(
                    rel_summary.get(
                        "protocol_version"
                    )
                    ==
                    "v2",
                    (
                        "Wrong reliability protocol: "
                        f"{dataset}/{mode}/{seed}"
                    )
                )


                require(
                    rel_summary.get(
                        "n_corrupted_cases"
                    )
                    ==
                    33,
                    (
                        "Wrong reliability case count: "
                        f"{dataset}/{mode}/{seed}"
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


# ==========================================================
# 4. VERIFY SCHEDULE EQUALITY
# ==========================================================

print()
print(
    "4. EXPOSURE ↔ CONSISTENCY CORRUPTION-SCHEDULE EQUALITY"
)
print(
    "-" * 82
)


schedule_rows = []

schedule_matches = 0


for dataset in DATASETS:

    for seed in SEEDS:

        exposure_metrics = load_json(

            ABL /
            "raw_runs" /
            dataset /
            "exposure" /
            f"seed_{seed}" /
            "metrics.json"
        )


        consistency_metrics = load_json(

            ABL /
            "raw_runs" /
            dataset /
            "consistency" /
            f"seed_{seed}" /
            "metrics.json"
        )


        exposure_sha = (
            exposure_metrics[
                "corruption_schedule_sha256"
            ]
        )


        consistency_sha = (
            consistency_metrics[
                "corruption_schedule_sha256"
            ]
        )


        match = (
            exposure_sha
            ==
            consistency_sha
        )


        require(
            match,
            (
                "Exposure/consistency schedule mismatch: "
                f"{dataset}/seed_{seed}"
            )
        )


        if match:
            schedule_matches += 1


        schedule_rows.append(
            {
                "dataset":
                    dataset,

                "seed":
                    seed,

                "exposure_schedule_sha256":
                    exposure_sha,

                "consistency_schedule_sha256":
                    consistency_sha,

                "exact_match":
                    match,
            }
        )


schedule_df = pd.DataFrame(
    schedule_rows
)


schedule_df.to_csv(
    OUT /
    "corruption_schedule_equality_6.csv",
    index=False
)


print(
    schedule_df.to_string(
        index=False
    )
)


print(
    "SCHEDULE_PAIRS_MATCHED=",
    schedule_matches,
    "/6"
)


# ==========================================================
# 5. CONSISTENCY-MECHANISM AUDIT
# ==========================================================

print()
print(
    "5. CONSISTENCY-MECHANISM AUDIT"
)
print(
    "-" * 82
)


mechanism_rows = []


for dataset in DATASETS:

    for mode in [
        "exposure",
        "consistency",
    ]:

        for seed in SEEDS:

            history = load_json(

                ABL /
                "raw_runs" /
                dataset /
                mode /
                f"seed_{seed}" /
                "history.json"
            )


            losses = np.asarray(
                [
                    float(
                        row[
                            "consistency_loss"
                        ]
                    )
                    for row in history
                ],
                dtype=float
            )


            mechanism_rows.append(
                {
                    "dataset":
                        dataset,

                    "mode":
                        mode,

                    "seed":
                        seed,

                    "mean_consistency_loss":
                        float(
                            losses.mean()
                        ),

                    "max_consistency_loss":
                        float(
                            losses.max()
                        ),

                    "nonzero_epochs":
                        int(
                            np.sum(
                                losses
                                >
                                0
                            )
                        ),
                }
            )


            if mode == "exposure":

                require(
                    np.allclose(
                        losses,
                        0.0
                    ),
                    (
                        "Exposure consistency loss "
                        f"is not zero: "
                        f"{dataset}/{seed}"
                    )
                )


            if mode == "consistency":

                require(
                    np.any(
                        losses
                        >
                        0
                    ),
                    (
                        "Consistency loss never active: "
                        f"{dataset}/{seed}"
                    )
                )


mechanism = pd.DataFrame(
    mechanism_rows
)


mechanism.to_csv(
    OUT /
    "consistency_mechanism_audit_12.csv",
    index=False
)


print(
    mechanism.to_string(
        index=False
    )
)


# ==========================================================
# 6. LOAD ALL 18 MODE × DATASET × SEED POINTS
# ==========================================================

print()
print(
    "6. LOAD CLEAN CE + EXPOSURE + CONSISTENCY"
)
print(
    "-" * 82
)


rows = []

family_rows = []


for dataset in DATASETS:

    for mode in MODES:

        for seed in SEEDS:

            if mode == "clean_ce":

                run_dir = (
                    SCREEN /
                    "raw_runs" /
                    dataset /
                    "V25Dense64" /
                    f"seed_{seed}"
                )


                rel_dir = (
                    SCREEN /
                    "reliability_v2" /
                    dataset /
                    "V25Dense64" /
                    f"seed_{seed}"
                )


                metrics = load_json(
                    run_dir /
                    "metrics.json"
                )


                training_seconds = (
                    metrics.get(
                        "training_seconds"
                    )
                )


                best_epoch = (
                    metrics.get(
                        "best_epoch"
                    )
                )


            else:

                run_dir = (
                    ABL /
                    "raw_runs" /
                    dataset /
                    mode /
                    f"seed_{seed}"
                )


                rel_dir = (
                    ABL /
                    "reliability_v2" /
                    dataset /
                    mode /
                    f"seed_{seed}"
                )


                metrics = load_json(
                    run_dir /
                    "metrics.json"
                )


                training_seconds = (
                    metrics.get(
                        "training_seconds"
                    )
                )


                best_epoch = (
                    metrics.get(
                        "best_epoch"
                    )
                )


            summary = load_json(
                rel_dir /
                "reliability_summary_v2.json"
            )


            test = metrics[
                "test"
            ]


            overall = summary[
                "overall"
            ]


            rows.append(
                {
                    "dataset":
                        dataset,

                    "mode":
                        mode,

                    "seed":
                        seed,

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

                    "training_seconds":
                        (
                            float(
                                training_seconds
                            )
                            if training_seconds is not None
                            else np.nan
                        ),

                    "best_epoch":
                        (
                            int(
                                best_epoch
                            )
                            if best_epoch is not None
                            else np.nan
                        ),
                }
            )


            for family in FAMILIES:

                data = (
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

                        "mode":
                            mode,

                        "seed":
                            seed,

                        "family":
                            family,

                        "reliability_score":
                            float(
                                data[
                                    "reliability_score_mean"
                                ]
                            ),

                        "corrupted_accuracy":
                            float(
                                data[
                                    "corrupted_accuracy_mean"
                                ]
                            ),

                        "corrupted_macro_f1":
                            float(
                                data[
                                    "corrupted_macro_f1_mean"
                                ]
                            ),

                        "relative_accuracy_degradation":
                            float(
                                data[
                                    "relative_accuracy_degradation_mean"
                                ]
                            ),

                        "relative_macro_f1_degradation":
                            float(
                                data[
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


require(
    len(
        per_seed
    )
    ==
    18,
    f"Expected 18 per-seed rows, got {len(per_seed)}"
)


require(
    len(
        family_seed
    )
    ==
    72,
    f"Expected 72 family rows, got {len(family_seed)}"
)


per_seed.to_csv(
    OUT /
    "ablation_per_seed_18.csv",
    index=False
)


family_seed.to_csv(
    OUT /
    "ablation_family_per_seed_72.csv",
    index=False
)


print(
    "PER_SEED_ROWS=",
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


# ==========================================================
# 7. DATASET × MODE SUMMARY
# ==========================================================

summary_rows = []


for (
    dataset,
    mode
), group in per_seed.groupby(
    [
        "dataset",
        "mode"
    ],
    sort=False
):

    row = {
        "dataset":
            dataset,

        "mode":
            mode,

        "n_seeds":
            len(
                group
            ),

        "parameters":
            float(
                group[
                    "parameters"
                ].mean()
            ),

        "training_seconds_mean":
            float(
                group[
                    "training_seconds"
                ].mean()
            ),

        "best_epoch_mean":
            float(
                group[
                    "best_epoch"
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
    "dataset_mode_summary_6.csv",
    index=False
)


print()
print(
    "7. DATASET × TRAINING MODE"
)
print(
    "-" * 82
)


print(
    dataset_summary[
        [
            "dataset",
            "mode",
            "clean_accuracy_mean",
            "clean_macro_f1_mean",
            "corrupted_accuracy_mean",
            "corrupted_macro_f1_mean",
            "reliability_score_mean",
            "training_seconds_mean",
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
# 8. EQUAL-DATASET-WEIGHT SUMMARY
# ==========================================================

cross_rows = []


for mode, group in dataset_summary.groupby(
    "mode",
    sort=False
):

    cross_rows.append(
        {
            "mode":
                mode,

            "clean_accuracy":
                float(
                    group[
                        "clean_accuracy_mean"
                    ].mean()
                ),

            "clean_macro_f1":
                float(
                    group[
                        "clean_macro_f1_mean"
                    ].mean()
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

            "training_seconds":
                float(
                    group[
                        "training_seconds_mean"
                    ].mean()
                ),
        }
    )


cross = pd.DataFrame(
    cross_rows
)


cross.to_csv(
    OUT /
    "cross_dataset_mode_summary_3.csv",
    index=False
)


print()
print(
    "8. TWO-DATASET EQUAL-WEIGHT SUMMARY"
)
print(
    "-" * 82
)


print(
    cross
    .sort_values(
        "corrupted_accuracy",
        ascending=False
    )
    .to_string(
        index=False
    )
)


# ==========================================================
# 9. SAME-SEED PAIRED DELTAS
# ==========================================================

paired_rows = []


for dataset in DATASETS:

    subset = per_seed[
        per_seed[
            "dataset"
        ]
        ==
        dataset
    ]


    for left, right in COMPARISONS:

        left_df = (
            subset[
                subset[
                    "mode"
                ]
                ==
                left
            ]
            .set_index(
                "seed"
            )
        )


        right_df = (
            subset[
                subset[
                    "mode"
                ]
                ==
                right
            ]
            .set_index(
                "seed"
            )
        )


        for metric in METRICS:

            diff = (
                left_df.loc[
                    SEEDS,
                    metric
                ].to_numpy(
                    dtype=float
                )
                -
                right_df.loc[
                    SEEDS,
                    metric
                ].to_numpy(
                    dtype=float
                )
            )


            paired_rows.append(
                {
                    "dataset":
                        dataset,

                    "left_mode":
                        left,

                    "right_mode":
                        right,

                    "metric":
                        metric,

                    "mean_delta":
                        float(
                            diff.mean()
                        ),

                    "std_delta":
                        float(
                            diff.std(
                                ddof=1
                            )
                        ),

                    "seed42_delta":
                        float(
                            diff[
                                0
                            ]
                        ),

                    "seed123_delta":
                        float(
                            diff[
                                1
                            ]
                        ),

                    "seed456_delta":
                        float(
                            diff[
                                2
                            ]
                        ),

                    "left_wins":
                        int(
                            np.sum(
                                diff > 0
                            )
                        ),

                    "right_wins":
                        int(
                            np.sum(
                                diff < 0
                            )
                        ),

                    "ties":
                        int(
                            np.sum(
                                diff == 0
                            )
                        ),
                }
            )


paired = pd.DataFrame(
    paired_rows
)


paired.to_csv(
    OUT /
    "paired_seed_deltas_30.csv",
    index=False
)


print()
print(
    "9. SAME-SEED PAIRED DELTAS"
)
print(
    "-" * 82
)


print(
    paired[
        paired[
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


# ==========================================================
# 10. FAMILY SUMMARY
# ==========================================================

family_rows_summary = []


for (
    family,
    mode
), group in family_seed.groupby(
    [
        "family",
        "mode"
    ],
    sort=False
):

    family_rows_summary.append(
        {
            "family":
                family,

            "mode":
                mode,

            "points":
                len(
                    group
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

            "reliability_score":
                float(
                    group[
                        "reliability_score"
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


family_summary = pd.DataFrame(
    family_rows_summary
)


family_summary[
    "accuracy_rank"
] = (
    family_summary
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


family_summary[
    "macro_f1_rank"
] = (
    family_summary
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


family_summary.to_csv(
    OUT /
    "family_mode_summary_12.csv",
    index=False
)


print()
print(
    "10. CORRUPTION-FAMILY SUMMARY"
)
print(
    "-" * 82
)


print(
    family_summary[
        [
            "family",
            "mode",
            "corrupted_accuracy",
            "corrupted_macro_f1",
            "reliability_score",
            "accuracy_rank",
            "macro_f1_rank",
        ]
    ]
    .sort_values(
        [
            "family",
            "accuracy_rank"
        ]
    )
    .to_string(
        index=False
    )
)


# ==========================================================
# 11. PARETO / DOMINANCE
# ==========================================================

print()
print(
    "11. TRAINING-MODE PARETO / DOMINANCE"
)
print(
    "-" * 82
)


maximize = [
    "clean_macro_f1",
    "corrupted_accuracy",
    "corrupted_macro_f1",
]


dominators = {
    mode: []
    for mode in MODES
}


for _, candidate in cross.iterrows():

    for _, challenger in cross.iterrows():

        if (
            candidate[
                "mode"
            ]
            ==
            challenger[
                "mode"
            ]
        ):
            continue


        no_worse = all(

            challenger[
                metric
            ]
            >=
            candidate[
                metric
            ]

            for metric in maximize
        )


        strictly_better = any(

            challenger[
                metric
            ]
            >
            candidate[
                metric
            ]

            for metric in maximize
        )


        if (
            no_worse
            and
            strictly_better
        ):

            dominators[
                candidate[
                    "mode"
                ]
            ].append(
                challenger[
                    "mode"
                ]
            )


pareto_rows = []


for _, row in cross.iterrows():

    mode = row[
        "mode"
    ]


    pareto_rows.append(
        {
            **row.to_dict(),

            "pareto_front":
                len(
                    dominators[
                        mode
                    ]
                )
                ==
                0,

            "dominated_by":
                ";".join(
                    dominators[
                        mode
                    ]
                ),
        }
    )


pareto = pd.DataFrame(
    pareto_rows
)


pareto.to_csv(
    OUT /
    "training_mode_pareto.csv",
    index=False
)


print(
    pareto[
        [
            "mode",
            "clean_macro_f1",
            "corrupted_accuracy",
            "corrupted_macro_f1",
            "pareto_front",
            "dominated_by",
        ]
    ].to_string(
        index=False
    )
)


# ==========================================================
# 12. INTERPRETATION TABLE
# ==========================================================

print()
print(
    "12. FINAL DECISION TABLE"
)
print(
    "-" * 82
)


clean = cross[
    cross[
        "mode"
    ]
    ==
    "clean_ce"
].iloc[
    0
]


decision = cross.copy()


for metric in [

    "clean_macro_f1",

    "corrupted_accuracy",

    "corrupted_macro_f1",

    "reliability_score",
]:

    decision[
        f"{metric}_delta_vs_clean"
    ] = (
        decision[
            metric
        ]
        -
        clean[
            metric
        ]
    )


decision = decision.merge(

    pareto[
        [
            "mode",
            "pareto_front",
            "dominated_by",
        ]
    ],

    on="mode",
    how="left"
)


decision.to_csv(
    OUT /
    "final_training_mode_decision.csv",
    index=False
)


print(
    decision[
        [
            "mode",
            "clean_macro_f1",
            "corrupted_accuracy",
            "corrupted_macro_f1",
            "reliability_score",
            "clean_macro_f1_delta_vs_clean",
            "corrupted_accuracy_delta_vs_clean",
            "corrupted_macro_f1_delta_vs_clean",
            "reliability_score_delta_vs_clean",
            "pareto_front",
            "dominated_by",
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


# ==========================================================
# FINAL INTEGRITY CLASSIFICATION
# ==========================================================

print()
print(
    "13. FINAL INTEGRITY CLASSIFICATION"
)
print(
    "-" * 82
)


print(
    "WARNING_COUNT=",
    len(
        warnings
    )
)

print(
    "ERROR_COUNT=",
    len(
        errors
    )
)


if errors:

    for error in errors:

        print(
            "ERROR:",
            error
        )


    print(
        "V25_ABLATION_R1_FINAL_ANALYSIS_PASS=False"
    )

    raise SystemExit(
        4
    )


# ==========================================================
# RECEIPT
# ==========================================================

outputs = [

    OUT /
    "corruption_schedule_equality_6.csv",

    OUT /
    "consistency_mechanism_audit_12.csv",

    OUT /
    "ablation_per_seed_18.csv",

    OUT /
    "ablation_family_per_seed_72.csv",

    OUT /
    "dataset_mode_summary_6.csv",

    OUT /
    "cross_dataset_mode_summary_3.csv",

    OUT /
    "paired_seed_deltas_30.csv",

    OUT /
    "family_mode_summary_12.csv",

    OUT /
    "training_mode_pareto.csv",

    OUT /
    "final_training_mode_decision.csv",
]


receipt = {

    "protocol":
        "v25_training_ablation_r1",

    "protocol_sha256":
        protocol_sha,

    "integrity_pass":
        True,

    "training_runs_verified":
        training_verified,

    "reliability_runs_verified":
        reliability_verified,

    "schedule_pairs_verified":
        schedule_matches,

    "modes":
        MODES,

    "datasets":
        DATASETS,

    "seeds":
        SEEDS,

    "important_boundary":
        (
            "Development ablation on two datasets "
            "and three seeds. Final four-dataset "
            "confirmation is required before "
            "paper-level superiority claims."
        ),

    "statistical_boundary":
        (
            "Only three seeds are available in this "
            "development ablation, so paired deltas "
            "and win/loss counts are reported rather "
            "than over-interpreting low-powered "
            "inferential tests."
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
    "v25_ablation_r1_final_receipt.json"
)


receipt_path.write_text(
    json.dumps(
        receipt,
        indent=2,
        sort_keys=True
    )
)


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


print(
    "V25_ABLATION_R1_FINAL_ANALYSIS_PASS=True"
)

print(
    "SCHEDULE_PAIRS_VERIFIED=6/6"
)

print(
    "TRAINING_RUNS_VERIFIED=12/12"
)

print(
    "RELIABILITY_RUNS_VERIFIED=12/12"
)

print()
print(
    "=" * 82
)

print(
    "V25_ABLATION_R1_DECISION_ANALYSIS_COMPLETE=True"
)

print(
    "=" * 82
)
