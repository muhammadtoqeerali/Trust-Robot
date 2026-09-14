from __future__ import annotations

import csv
import hashlib
import json
import math
import statistics
from pathlib import Path

import numpy as np

try:
    from scipy import stats
except Exception as exc:
    raise RuntimeError(
        f"SciPy required for frozen read-only "
        f"paired statistics: {exc}"
    )


ROOT = Path(
    "/mnt/hdd16T/ToqeerHomeBackup/toqeer/IMU_Reliability"
)

R9D2 = (
    ROOT
    / "results"
    / "v26_external_storm_test_r9d2"
)

STAGE24_ROOT = (
    ROOT
    / "results"
    / "storm_paper_domain_r1"
)

OUT = (
    ROOT
    / "results"
    / "v26_external_storm_scientific_closure_r9e"
)


SEEDS = [
    42,
    123,
    456,
    789,
    2026,
]


METRICS = [
    "clean_accuracy",
    "clean_macro_f1",
    "all_fault_accuracy",
    "all_fault_macro_f1",
    "recoverable_fault_accuracy",
    "recoverable_fault_macro_f1",
    "family_balanced_accuracy",
    "family_balanced_macro_f1",
]


ROBUSTNESS_METRICS = [
    "all_fault_accuracy",
    "all_fault_macro_f1",
    "recoverable_fault_accuracy",
    "recoverable_fault_macro_f1",
    "family_balanced_accuracy",
    "family_balanced_macro_f1",
]


FAMILIES = [
    "modality_outage",
    "single_axis_outage",
    "intermittent_dropout",
    "gaussian_noise",
    "stuck_value",
    "scale_drift",
]


V26_PARAMS = 23210
STORM_PARAMS = 19753


def sha256_file(
    path: Path,
) -> str:

    h = hashlib.sha256()

    with path.open("rb") as f:

        for block in iter(
            lambda: f.read(
                1024 * 1024
            ),
            b"",
        ):
            h.update(block)

    return h.hexdigest()


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
        writer.writerows(rows)


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


def find_column(
    fields,
    candidates,
):

    lookup = {
        str(field).lower():
            field
        for field in fields
    }

    for candidate in candidates:

        if candidate.lower() in lookup:
            return lookup[
                candidate.lower()
            ]

    raise KeyError(
        f"No field among {candidates}; "
        f"available={list(fields)}"
    )


def locate_stage24_cases():

    candidates = []

    for path in sorted(
        STAGE24_ROOT.rglob(
            "*.csv"
        )
    ):

        try:
            rows = read_csv(path)
        except Exception:
            continue

        if len(rows) != 180:
            continue

        if not rows:
            continue

        fields = rows[0].keys()

        try:
            model_col = find_column(
                fields,
                [
                    "model",
                    "model_name",
                ],
            )

            seed_col = find_column(
                fields,
                [
                    "seed",
                ],
            )

            condition_col = find_column(
                fields,
                [
                    "condition",
                    "condition_name",
                    "fault",
                    "fault_name",
                ],
            )

            family_col = find_column(
                fields,
                [
                    "family",
                    "fault_family",
                ],
            )

            acc_col = find_column(
                fields,
                [
                    "accuracy",
                    "acc",
                ],
            )

            f1_col = find_column(
                fields,
                [
                    "macro_f1",
                    "f1",
                ],
            )

        except KeyError:
            continue


        models = {
            str(
                row[
                    model_col
                ]
            )
            for row in rows
        }


        if not {
            "STORM_native",
            "V25_native",
        }.issubset(
            models
        ):
            continue


        candidates.append(
            (
                path,
                rows,
                {
                    "model":
                        model_col,

                    "seed":
                        seed_col,

                    "condition":
                        condition_col,

                    "family":
                        family_col,

                    "accuracy":
                        acc_col,

                    "macro_f1":
                        f1_col,
                },
            )
        )


    if not candidates:

        raise RuntimeError(
            "Could not locate frozen Stage24 "
            "180-row case CSV."
        )


    # Multiple byte-identical copies are harmless.
    by_sha = {}

    for item in candidates:

        digest = sha256_file(
            item[
                0
            ]
        )

        by_sha.setdefault(
            digest,
            [],
        ).append(
            item
        )


    if len(by_sha) != 1:

        print(
            "STAGE24_CASE_CANDIDATES="
        )

        for digest, items in by_sha.items():

            for item in items:

                print(
                    digest,
                    item[0],
                )


        raise RuntimeError(
            "Multiple scientifically distinct "
            "Stage24 180-row case CSVs found."
        )


    digest = next(
        iter(
            by_sha
        )
    )

    item = sorted(
        by_sha[
            digest
        ],
        key=lambda x:
            str(
                x[
                    0
                ]
            ),
    )[0]


    return (
        item[
            0
        ],
        item[
            1
        ],
        item[
            2
        ],
        digest,
    )


def canonical_cases(
    rows,
    columns,
    model_name,
):

    selected = []


    for row in rows:

        if str(
            row[
                columns[
                    "model"
                ]
            ]
        ) != model_name:
            continue


        selected.append({
            "model":
                model_name,

            "seed":
                int(
                    row[
                        columns[
                            "seed"
                        ]
                    ]
                ),

            "condition":
                str(
                    row[
                        columns[
                            "condition"
                        ]
                    ]
                ),

            "family":
                str(
                    row[
                        columns[
                            "family"
                        ]
                    ]
                ),

            "accuracy":
                float(
                    row[
                        columns[
                            "accuracy"
                        ]
                    ]
                ),

            "macro_f1":
                float(
                    row[
                        columns[
                            "macro_f1"
                        ]
                    ]
                ),
        })


    if len(
        selected
    ) != 90:

        raise RuntimeError(
            f"{model_name}: expected 90 Stage24 "
            f"cases, found {len(selected)}"
        )


    return selected


def load_v26_cases():

    path = (
        R9D2
        / "external_v26c_test_cases_90.csv"
    )


    rows = read_csv(
        path
    )


    if len(rows) != 90:

        raise RuntimeError(
            f"V26 external case rows={len(rows)}"
        )


    required = {
        "seed",
        "condition",
        "family",
        "accuracy",
        "macro_f1",
    }


    if not required.issubset(
        rows[
            0
        ].keys()
    ):

        raise RuntimeError(
            "V26 case schema mismatch"
        )


    return [
        {
            "model":
                "V26C_DualGateLiteCons",

            "seed":
                int(
                    row[
                        "seed"
                    ]
                ),

            "condition":
                row[
                    "condition"
                ],

            "family":
                row[
                    "family"
                ],

            "accuracy":
                float(
                    row[
                        "accuracy"
                    ]
                ),

            "macro_f1":
                float(
                    row[
                        "macro_f1"
                    ]
                ),
        }

        for row in rows
    ]


def aggregate_seed(
    rows,
    seed,
):

    x = [
        row
        for row in rows
        if row[
            "seed"
        ]
        ==
        seed
    ]


    if len(x) != 18:
        raise RuntimeError(
            f"seed={seed}: cases={len(x)} != 18"
        )


    baseline = [
        row
        for row in x
        if row[
            "condition"
        ]
        ==
        "baseline"
    ]


    if len(
        baseline
    ) != 1:
        raise RuntimeError(
            f"seed={seed}: baseline count mismatch"
        )


    baseline = baseline[
        0
    ]


    faults = [
        row
        for row in x
        if row[
            "condition"
        ]
        !=
        "baseline"
    ]


    recoverable = [
        row
        for row in faults
        if row[
            "condition"
        ]
        !=
        "all_sensors_failure"
    ]


    if len(faults) != 17:
        raise RuntimeError(
            "All-fault count != 17"
        )


    if len(
        recoverable
    ) != 16:
        raise RuntimeError(
            "Recoverable count != 16"
        )


    family_acc = []
    family_f1 = []


    for family in FAMILIES:

        fr = [
            row
            for row in faults
            if row[
                "family"
            ]
            ==
            family
        ]


        if not fr:
            raise RuntimeError(
                f"No {family} cases"
            )


        family_acc.append(
            statistics.fmean(
                row[
                    "accuracy"
                ]
                for row in fr
            )
        )


        family_f1.append(
            statistics.fmean(
                row[
                    "macro_f1"
                ]
                for row in fr
            )
        )


    return {
        "seed":
            seed,

        "clean_accuracy":
            baseline[
                "accuracy"
            ],

        "clean_macro_f1":
            baseline[
                "macro_f1"
            ],

        "all_fault_accuracy":
            statistics.fmean(
                row[
                    "accuracy"
                ]
                for row in faults
            ),

        "all_fault_macro_f1":
            statistics.fmean(
                row[
                    "macro_f1"
                ]
                for row in faults
            ),

        "recoverable_fault_accuracy":
            statistics.fmean(
                row[
                    "accuracy"
                ]
                for row in recoverable
            ),

        "recoverable_fault_macro_f1":
            statistics.fmean(
                row[
                    "macro_f1"
                ]
                for row in recoverable
            ),

        "family_balanced_accuracy":
            statistics.fmean(
                family_acc
            ),

        "family_balanced_macro_f1":
            statistics.fmean(
                family_f1
            ),
    }


def aggregate_model(
    seed_rows,
):

    result = {}


    for metric in METRICS:

        values = [
            row[
                metric
            ]
            for row in seed_rows
        ]


        result[
            metric
            +
            "_mean"
        ] = statistics.fmean(
            values
        )


        result[
            metric
            +
            "_std"
        ] = statistics.stdev(
            values
        )


    return result


def holm_adjust(
    pvalues,
):

    indexed = sorted(
        enumerate(
            pvalues
        ),
        key=lambda item:
            item[
                1
            ],
    )


    adjusted = [
        None
    ] * len(
        pvalues
    )


    running = 0.0
    m = len(
        pvalues
    )


    for rank, (
        original_index,
        p,
    ) in enumerate(
        indexed
    ):

        candidate = min(
            1.0,
            (
                m
                -
                rank
            )
            *
            p,
        )


        running = max(
            running,
            candidate,
        )


        adjusted[
            original_index
        ] = running


    return adjusted


stage24_path, stage24_rows, stage24_cols, stage24_case_sha = (
    locate_stage24_cases()
)


storm_cases = canonical_cases(
    stage24_rows,
    stage24_cols,
    "STORM_native",
)


v26_cases = load_v26_cases()


# ============================================================
# Condition-manifest identity
# ============================================================

storm_manifest = sorted({
    (
        row[
            "condition"
        ],
        row[
            "family"
        ],
    )
    for row in storm_cases
})


v26_manifest = sorted({
    (
        row[
            "condition"
        ],
        row[
            "family"
        ],
    )
    for row in v26_cases
})


if storm_manifest != v26_manifest:

    raise RuntimeError(
        "V26/STORM condition-family manifest mismatch"
    )


if len(
    storm_manifest
) != 18:

    raise RuntimeError(
        "Matched external condition manifest != 18"
    )


if (
    "all_sensors_failure",
    "modality_outage",
) not in storm_manifest:

    raise RuntimeError(
        "all_sensors_failure missing"
    )


print(
    "R9E_MATCHED_CONDITION_MANIFEST_PASS_18=True"
)


# ============================================================
# Per-seed aggregate reconstruction
# ============================================================

storm_seed = [
    aggregate_seed(
        storm_cases,
        seed,
    )
    for seed in SEEDS
]


v26_seed = [
    aggregate_seed(
        v26_cases,
        seed,
    )
    for seed in SEEDS
]


storm_model = aggregate_model(
    storm_seed
)

v26_model = aggregate_model(
    v26_seed
)


# Frozen Stage24 reference gates.
STAGE24_EXPECTED = {
    "clean_accuracy_mean":
        0.7212892160365898,

    "clean_macro_f1_mean":
        0.7275078003715905,

    "all_fault_accuracy_mean":
        0.5937145043109789,

    "all_fault_macro_f1_mean":
        0.5803210615250318,

    "recoverable_fault_accuracy_mean":
        0.6201109483313084,

    "recoverable_fault_macro_f1_mean":
        0.6143051935161276,

    "family_balanced_accuracy_mean":
        0.5859592494660028,

    "family_balanced_macro_f1_mean":
        0.5706786243615531,
}


for key, expected in STAGE24_EXPECTED.items():

    actual = storm_model[
        key
    ]


    if abs(
        actual
        -
        expected
    ) > 1e-12:

        raise RuntimeError(
            f"STORM reconstruction mismatch "
            f"{key}: {actual} vs {expected}"
        )


print(
    "R9E_STAGE24_STORM_AGGREGATE_RECONSTRUCTION_PASS_8_OF_8=True"
)


# Frozen R9D2 reference gate.
R9D2_AGG = json.loads(
    (
        R9D2
        / "external_v26c_aggregate_summary_r9d2.json"
    ).read_text()
)


for metric in METRICS:

    key = (
        metric
        +
        "_mean"
    )

    actual = v26_model[
        key
    ]

    expected = float(
        R9D2_AGG[
            key
        ]
    )


    if abs(
        actual
        -
        expected
    ) > 1e-12:

        raise RuntimeError(
            f"V26 R9D2 reconstruction mismatch "
            f"{key}: {actual} vs {expected}"
        )


print(
    "R9E_R9D2_V26_AGGREGATE_RECONSTRUCTION_PASS_8_OF_8=True"
)


# ============================================================
# Aggregate comparison
# ============================================================

aggregate_rows = []


for metric in METRICS:

    storm_mean = storm_model[
        metric
        +
        "_mean"
    ]

    storm_std = storm_model[
        metric
        +
        "_std"
    ]

    v26_mean = v26_model[
        metric
        +
        "_mean"
    ]

    v26_std = v26_model[
        metric
        +
        "_std"
    ]

    delta = (
        v26_mean
        -
        storm_mean
    )


    aggregate_rows.append({
        "metric":
            metric,

        "storm_mean":
            storm_mean,

        "storm_std":
            storm_std,

        "v26c_mean":
            v26_mean,

        "v26c_std":
            v26_std,

        "delta_v26c_minus_storm":
            delta,

        "delta_percentage_points":
            100.0
            *
            delta,

        "higher_model":
            (
                "V26C"
                if delta > 0
                else
                (
                    "STORM"
                    if delta < 0
                    else
                    "TIE"
                )
            ),
    })


write_csv(
    OUT
    / "v26c_vs_storm_aggregate_comparison_8.csv",
    aggregate_rows,
)


# ============================================================
# Paired seed statistics
# ============================================================

paired_detail = []
stat_rows = []

t_raw = []
w_raw = []


for metric in METRICS:

    storm_values = np.asarray(
        [
            row[
                metric
            ]
            for row in storm_seed
        ],
        dtype=np.float64,
    )


    v26_values = np.asarray(
        [
            row[
                metric
            ]
            for row in v26_seed
        ],
        dtype=np.float64,
    )


    delta = (
        v26_values
        -
        storm_values
    )


    for i, seed in enumerate(
        SEEDS
    ):

        paired_detail.append({
            "metric":
                metric,

            "seed":
                seed,

            "storm":
                float(
                    storm_values[
                        i
                    ]
                ),

            "v26c":
                float(
                    v26_values[
                        i
                    ]
                ),

            "delta_v26c_minus_storm":
                float(
                    delta[
                        i
                    ]
                ),
        })


    t_result = stats.ttest_rel(
        v26_values,
        storm_values,
    )


    try:

        w_result = stats.wilcoxon(
            delta,
            zero_method="wilcox",
            correction=False,
            alternative="two-sided",
            method="exact",
        )

        w_p = float(
            w_result.pvalue
        )

        w_stat = float(
            w_result.statistic
        )

    except Exception:

        w_result = stats.wilcoxon(
            delta,
            zero_method="wilcox",
            correction=False,
            alternative="two-sided",
            method="auto",
        )

        w_p = float(
            w_result.pvalue
        )

        w_stat = float(
            w_result.statistic
        )


    t_p = float(
        t_result.pvalue
    )


    t_raw.append(
        t_p
    )

    w_raw.append(
        w_p
    )


    stat_rows.append({
        "metric":
            metric,

        "mean_delta_v26c_minus_storm":
            float(
                np.mean(
                    delta
                )
            ),

        "v26_wins":
            int(
                np.sum(
                    delta > 0
                )
            ),

        "storm_wins":
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

        "paired_t_statistic":
            float(
                t_result.statistic
            ),

        "paired_t_p_raw":
            t_p,

        "wilcoxon_statistic":
            w_stat,

        "wilcoxon_p_raw":
            w_p,
    })


t_holm = holm_adjust(
    t_raw
)

w_holm = holm_adjust(
    w_raw
)


for index, row in enumerate(
    stat_rows
):

    row[
        "paired_t_p_holm"
    ] = t_holm[
        index
    ]

    row[
        "wilcoxon_p_holm"
    ] = w_holm[
        index
    ]


write_csv(
    OUT
    / "v26c_vs_storm_paired_seed_detail_40.csv",
    paired_detail,
)


write_csv(
    OUT
    / "v26c_vs_storm_paired_statistics_8.csv",
    stat_rows,
)


# ============================================================
# Family comparison
# ============================================================

family_rows = []


for family in FAMILIES:

    storm_family = [
        row
        for row in storm_cases
        if (
            row[
                "family"
            ]
            ==
            family
            and
            row[
                "condition"
            ]
            !=
            "baseline"
        )
    ]


    v26_family = [
        row
        for row in v26_cases
        if (
            row[
                "family"
            ]
            ==
            family
            and
            row[
                "condition"
            ]
            !=
            "baseline"
        )
    ]


    storm_acc = statistics.fmean(
        row[
            "accuracy"
        ]
        for row in storm_family
    )

    storm_f1 = statistics.fmean(
        row[
            "macro_f1"
        ]
        for row in storm_family
    )

    v26_acc = statistics.fmean(
        row[
            "accuracy"
        ]
        for row in v26_family
    )

    v26_f1 = statistics.fmean(
        row[
            "macro_f1"
        ]
        for row in v26_family
    )


    family_rows.append({
        "family":
            family,

        "storm_accuracy":
            storm_acc,

        "v26c_accuracy":
            v26_acc,

        "delta_accuracy_v26c_minus_storm":
            v26_acc
            -
            storm_acc,

        "storm_macro_f1":
            storm_f1,

        "v26c_macro_f1":
            v26_f1,

        "delta_macro_f1_v26c_minus_storm":
            v26_f1
            -
            storm_f1,
    })


write_csv(
    OUT
    / "v26c_vs_storm_family_comparison_6.csv",
    family_rows,
)


# ============================================================
# Condition-level comparison
# ============================================================

condition_rows = []


for condition, family in storm_manifest:

    storm_values = [
        row
        for row in storm_cases
        if row[
            "condition"
        ]
        ==
        condition
    ]


    v26_values = [
        row
        for row in v26_cases
        if row[
            "condition"
        ]
        ==
        condition
    ]


    if (
        len(
            storm_values
        )
        !=
        5
        or
        len(
            v26_values
        )
        !=
        5
    ):

        raise RuntimeError(
            f"{condition}: expected 5+5 rows"
        )


    storm_acc = statistics.fmean(
        row[
            "accuracy"
        ]
        for row in storm_values
    )

    storm_f1 = statistics.fmean(
        row[
            "macro_f1"
        ]
        for row in storm_values
    )

    v26_acc = statistics.fmean(
        row[
            "accuracy"
        ]
        for row in v26_values
    )

    v26_f1 = statistics.fmean(
        row[
            "macro_f1"
        ]
        for row in v26_values
    )


    condition_rows.append({
        "condition":
            condition,

        "family":
            family,

        "storm_accuracy":
            storm_acc,

        "v26c_accuracy":
            v26_acc,

        "delta_accuracy_v26c_minus_storm":
            v26_acc
            -
            storm_acc,

        "storm_macro_f1":
            storm_f1,

        "v26c_macro_f1":
            v26_f1,

        "delta_macro_f1_v26c_minus_storm":
            v26_f1
            -
            storm_f1,
    })


write_csv(
    OUT
    / "v26c_vs_storm_condition_comparison_18.csv",
    condition_rows,
)


# ============================================================
# Scientific gates
# ============================================================

aggregate_by_metric = {
    row[
        "metric"
    ]:
        row
    for row in aggregate_rows
}


robustness_positive = all(
    aggregate_by_metric[
        metric
    ][
        "delta_v26c_minus_storm"
    ]
    >
    0
    for metric in ROBUSTNESS_METRICS
)


v26_family_f1_wins = sum(
    row[
        "delta_macro_f1_v26c_minus_storm"
    ]
    >
    0
    for row in family_rows
)


v26_family_acc_wins = sum(
    row[
        "delta_accuracy_v26c_minus_storm"
    ]
    >
    0
    for row in family_rows
)


robust_stat_rows = [
    row
    for row in stat_rows
    if row[
        "metric"
    ]
    in ROBUSTNESS_METRICS
]


robust_all_five_wins = all(
    row[
        "v26_wins"
    ]
    ==
    5
    for row in robust_stat_rows
)


minimum_wilcoxon = min(
    row[
        "wilcoxon_p_raw"
    ]
    for row in stat_rows
)


param_delta = (
    V26_PARAMS
    -
    STORM_PARAMS
)


param_ratio = (
    V26_PARAMS
    /
    STORM_PARAMS
)


param_increase_percent = (
    param_ratio
    -
    1.0
) * 100.0


claim_policy = {
    "status":
        "PASS",

    "comparison":
        (
            "Frozen V26C versus frozen released-code "
            "STORM_native under the exact matched Stage24 "
            "18-condition pre-normalization physical-fault "
            "external benchmark."
        ),

    "v26_external_test_rerun_allowed":
        False,

    "v26_post_external_tuning_allowed":
        False,

    "matched_external_robustness_superiority_descriptive":
        robustness_positive,

    "all_six_aggregate_robustness_metrics_higher":
        robustness_positive,

    "all_five_seed_robustness_wins_for_all_six_metrics":
        robust_all_five_wins,

    "clean_accuracy_superiority_allowed":
        False,

    "clean_macro_f1_descriptively_higher":
        (
            aggregate_by_metric[
                "clean_macro_f1"
            ][
                "delta_v26c_minus_storm"
            ]
            >
            0
        ),

    "external_parameter_superiority_allowed":
        False,

    "external_runtime_superiority_allowed":
        False,

    "external_efficiency_superiority_allowed":
        False,

    "external_robustness_at_similarly_compact_scale_allowed":
        True,

    "exact_storm_paper_replication_claim_allowed":
        False,

    "published_storm_model_superiority_claim_allowed":
        False,

    "released_code_storm_baseline_comparison_allowed":
        True,

    "universal_sota_claim_allowed":
        False,

    "deployment_superiority_claim_allowed":
        False,

    "statistical_significance_from_exact_wilcoxon_claim_allowed":
        (
            minimum_wilcoxon
            <
            0.05
        ),

    "n5_non_significance_is_equivalence":
        False,

    "parameter_comparison": {
        "storm_parameters":
            STORM_PARAMS,

        "v26c_parameters":
            V26_PARAMS,

        "v26c_minus_storm_parameters":
            param_delta,

        "v26c_to_storm_parameter_ratio":
            param_ratio,

        "v26c_parameter_increase_percent":
            param_increase_percent,
    },

    "family_results": {
        "v26c_accuracy_family_wins_out_of_6":
            v26_family_acc_wins,

        "v26c_macro_f1_family_wins_out_of_6":
            v26_family_f1_wins,
    },
}


write_json(
    OUT
    / "v26_external_storm_claim_policy_r9e.json",
    claim_policy,
)


source_binding = {
    "stage24_case_csv":
        str(
            stage24_path.relative_to(
                ROOT
            )
        ),

    "stage24_case_csv_sha256":
        stage24_case_sha,

    "r9d2_case_csv":
        str(
            (
                R9D2
                / "external_v26c_test_cases_90.csv"
            ).relative_to(
                ROOT
            )
        ),

    "r9d2_case_csv_sha256":
        sha256_file(
            R9D2
            / "external_v26c_test_cases_90.csv"
        ),

    "matched_condition_manifest_count":
        18,

    "storm_case_rows":
        90,

    "v26c_case_rows":
        90,
}


write_json(
    OUT
    / "v26_external_storm_source_binding_r9e.json",
    source_binding,
)


receipt = {
    "stage":
        "V26_EXTERNAL_STORM_SCIENTIFIC_CLOSURE_R9E",

    "status":
        "PASS",

    "analysis_only":
        True,

    "model_constructed":
        False,

    "checkpoint_loaded":
        False,

    "dataset_loaded":
        False,

    "test_inference_performed":
        False,

    "training_performed":
        False,

    "external_test_already_consumed":
        True,

    "external_test_rerun_allowed":
        False,

    "stage24_recomputed_from_frozen_case_rows":
        True,

    "r9d2_recomputed_from_frozen_case_rows":
        True,

    "matched_condition_manifest":
        "PASS_18_OF_18",

    "aggregate_metric_comparisons":
        8,

    "paired_seed_metrics":
        8,

    "paired_seed_pairs":
        40,

    "family_comparisons":
        6,

    "condition_comparisons":
        18,

    "all_six_aggregate_robustness_metrics_v26c_higher":
        robustness_positive,

    "robustness_all_five_seed_direction_gate":
        robust_all_five_wins,

    "minimum_exact_wilcoxon_p":
        minimum_wilcoxon,

    "v26c_parameters":
        V26_PARAMS,

    "storm_parameters":
        STORM_PARAMS,

    "v26c_parameter_increase_percent":
        param_increase_percent,
}


write_json(
    OUT
    / "v26_external_storm_scientific_closure_receipt_r9e.json",
    receipt,
)


print()
print("=" * 118)
print("V26 EXTERNAL STORM SCIENTIFIC CLOSURE R9E")
print("=" * 118)


for row in aggregate_rows:

    print(
        "R9E_AGGREGATE:",
        row[
            "metric"
        ],
        f"STORM={row['storm_mean']:.9f}",
        f"V26C={row['v26c_mean']:.9f}",
        f"DELTA={row['delta_v26c_minus_storm']:+.9f}",
        f"PP={row['delta_percentage_points']:+.3f}",
    )


print()
print("=" * 118)
print("PAIRED FIVE-SEED STATISTICS")
print("=" * 118)


for row in stat_rows:

    print(
        "R9E_PAIRED:",
        row[
            "metric"
        ],
        f"V26wins={row['v26_wins']}",
        f"STORMwins={row['storm_wins']}",
        f"ties={row['ties']}",
        f"t_p={row['paired_t_p_raw']:.9g}",
        f"t_holm={row['paired_t_p_holm']:.9g}",
        f"wilcoxon_p={row['wilcoxon_p_raw']:.9g}",
        f"wilcoxon_holm={row['wilcoxon_p_holm']:.9g}",
    )


print()
print("=" * 118)
print("FAULT FAMILY COMPARISON")
print("=" * 118)


for row in family_rows:

    print(
        "R9E_FAMILY:",
        row[
            "family"
        ],
        f"ACC_DELTA={row['delta_accuracy_v26c_minus_storm']:+.9f}",
        f"F1_DELTA={row['delta_macro_f1_v26c_minus_storm']:+.9f}",
    )


print()
print("=" * 118)
print("EXTERNAL CLAIM POLICY")
print("=" * 118)


print(
    "V26C_EXTERNAL_ROBUSTNESS_AGGREGATE_WINS=",
    f"{sum(aggregate_by_metric[m]['delta_v26c_minus_storm'] > 0 for m in ROBUSTNESS_METRICS)}/6"
)

print(
    "V26C_EXTERNAL_ROBUSTNESS_ALL_FIVE_SEED_GATE=",
    robust_all_five_wins
)

print(
    "V26C_EXTERNAL_FAMILY_F1_WINS=",
    f"{v26_family_f1_wins}/6"
)

print(
    "V26C_EXTERNAL_FAMILY_ACCURACY_WINS=",
    f"{v26_family_acc_wins}/6"
)

print(
    "V26C_VS_STORM_PARAMETER_RATIO=",
    f"{param_ratio:.6f}x"
)

print(
    "V26C_VS_STORM_PARAMETER_INCREASE_PERCENT=",
    f"{param_increase_percent:.3f}"
)

print(
    "MATCHED_EXTERNAL_ROBUSTNESS_SUPERIORITY_DESCRIPTIVE_ALLOWED=",
    robustness_positive
)

print(
    "CLEAN_ACCURACY_SUPERIORITY_CLAIM_ALLOWED=False"
)

print(
    "EXTERNAL_PARAMETER_SUPERIORITY_CLAIM_ALLOWED=False"
)

print(
    "EXTERNAL_RUNTIME_SUPERIORITY_CLAIM_ALLOWED=False"
)

print(
    "EXACT_STORM_PAPER_REPLICATION_CLAIM_ALLOWED=False"
)

print(
    "UNIVERSAL_SOTA_CLAIM_ALLOWED=False"
)

print(
    "EXTERNAL_TEST_RERUN_ALLOWED=False"
)


print()
print(
    "V26_EXTERNAL_STORM_SCIENTIFIC_CLOSURE_R9E_PASS=True"
)

print(
    "MODEL_CONSTRUCTED=False"
)

print(
    "CHECKPOINT_LOADED=False"
)

print(
    "DATASET_LOADED=False"
)

print(
    "TEST_INFERENCE_PERFORMED=False"
)

print(
    "TRAINING_PERFORMED=False"
)
