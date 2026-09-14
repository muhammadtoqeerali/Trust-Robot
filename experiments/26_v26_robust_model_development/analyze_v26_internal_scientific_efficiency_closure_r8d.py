from __future__ import annotations

import csv
import json
import statistics
from pathlib import Path


ROOT = Path(
    "/mnt/hdd16T/ToqeerHomeBackup/toqeer/IMU_Reliability"
)

R6B = (
    ROOT
    / "results/v26_primary_confirmation_test_r6b"
)

R7 = (
    ROOT
    / "results/v26_primary_confirmation_scientific_closure_r7"
)

R8C = (
    ROOT
    / "results/v26_efficiency_measurement_r8c"
)

OUT = (
    ROOT
    / "results/v26_internal_scientific_efficiency_closure_r8d"
)

OUT.mkdir(
    parents=True,
    exist_ok=True,
)


V26 = "V26C_DualGateLiteCons"
V25 = "ReliabilityCNN_v25"


SCIENTIFIC_METRICS = [
    "clean_accuracy",
    "clean_macro_f1",
    "all_fault_accuracy",
    "all_fault_macro_f1",
    "recoverable_fault_accuracy",
    "recoverable_fault_macro_f1",
    "family_balanced_accuracy",
    "family_balanced_macro_f1",
]


EFFICIENCY_METRICS = {
    "parameter_count":
        "lower",

    "checkpoint_bytes":
        "lower",

    "cpu_batch1_median_ms":
        "lower",

    "gpu_batch1_median_ms":
        "lower",

    "gpu_batch64_samples_per_second":
        "higher",
}


PRIMARY_ROBUSTNESS = [
    "all_fault_macro_f1",
    "family_balanced_macro_f1",
]


def read_csv(path):

    with Path(path).open(
        newline="",
        encoding="utf-8",
    ) as f:

        return list(
            csv.DictReader(f)
        )


def write_csv(
    path,
    rows,
):

    if not rows:
        raise RuntimeError(
            f"No rows for {path}"
        )

    with Path(path).open(
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


def write_json(
    path,
    obj,
):

    Path(path).write_text(
        json.dumps(
            obj,
            indent=2,
            sort_keys=True,
            default=str,
        )
        + "\n"
    )


def mean(values):

    return float(
        statistics.fmean(
            float(x)
            for x in values
        )
    )


print("=" * 118)
print("V26 INTERNAL SCIENTIFIC + EFFICIENCY CLOSURE R8D")
print("READ-ONLY FROZEN EVIDENCE")
print("=" * 118)


# ============================================================
# 1. Bind R7 scientific result
# ============================================================

r7 = json.loads(
    (
        R7
        / "v26_primary_confirmation_scientific_closure_r7.json"
    ).read_text()
)


required_r7 = {
    "status":
        "PASS",

    "candidate":
        V26,

    "frozen_rank1_metrics":
        8,

    "total_metrics":
        8,

    "predeclared_claim_tier":
        "TIER_A_STRONG_INTERNAL_BENCHMARK_SUPERIORITY",

    "candidate_retraining_allowed":
        False,

    "candidate_hyperparameter_change_allowed":
        False,

    "training_performed":
        False,

    "test_inference_performed":
        False,

    "storm_used":
        False,
}


for key, expected in required_r7.items():

    if r7.get(key) != expected:

        raise RuntimeError(
            f"R7 mismatch: {key}="
            f"{r7.get(key)!r}, expected={expected!r}"
        )


print(
    "R8D_FROZEN_R7_SCIENTIFIC_RESULT_BOUND=True"
)


# ============================================================
# 2. Bind R8C efficiency receipt
# ============================================================

r8c = json.loads(
    (
        R8C
        / "v26_efficiency_measurement_receipt_r8c.json"
    ).read_text()
)


required_r8c = {
    "status":
        "PASS",

    "model_count":
        11,

    "measurement_rows":
        11,

    "batch1_latency_sample_rows":
        22000,

    "synthetic_input_only":
        True,

    "cpu_threads":
        1,

    "latency_timing_performed":
        True,

    "throughput_timing_performed":
        True,

    "protected_test_access":
        False,

    "real_dataset_access":
        False,

    "training_performed":
        False,

    "candidate_modified":
        False,

    "checkpoint_modified":
        False,

    "storm_used":
        False,

    "mac_flop":
        "NOT_COMPARABLE",
}


for key, expected in required_r8c.items():

    if r8c.get(key) != expected:

        raise RuntimeError(
            f"R8C mismatch: {key}="
            f"{r8c.get(key)!r}, expected={expected!r}"
        )


print(
    "R8D_FROZEN_R8C_EFFICIENCY_RESULT_BOUND=True"
)


# ============================================================
# 3. Reconstruct 11-model scientific table
# ============================================================

scientific_rank_rows = read_csv(
    R6B
    / "primary_comparison_rankings_88_recovered.csv"
)


if len(
    scientific_rank_rows
) != 88:

    raise RuntimeError(
        f"Expected 88 scientific ranking rows, "
        f"found {len(scientific_rank_rows)}"
    )


science = {}


for row in scientific_rank_rows:

    model = row[
        "model"
    ]

    metric = row[
        "metric"
    ]

    science.setdefault(
        model,
        {}
    )[
        metric
    ] = float(
        row[
            "value"
        ]
    )


if len(
    science
) != 11:

    raise RuntimeError(
        f"Expected 11 scientific models, "
        f"found {len(science)}"
    )


for model, values in science.items():

    missing = (
        set(
            SCIENTIFIC_METRICS
        )
        -
        set(
            values
        )
    )

    if missing:

        raise RuntimeError(
            f"{model}: missing scientific metrics "
            f"{sorted(missing)}"
        )


# ============================================================
# 4. Frozen 11-model efficiency table
# ============================================================

efficiency_rows = read_csv(
    R8C
    / "efficiency_measurements_11.csv"
)


if len(
    efficiency_rows
) != 11:

    raise RuntimeError(
        f"Expected 11 efficiency rows, "
        f"found {len(efficiency_rows)}"
    )


efficiency = {
    row[
        "model"
    ]:
        row

    for row in efficiency_rows
}


if set(
    efficiency
) != set(
    science
):

    raise RuntimeError(
        "Scientific and efficiency model sets differ"
    )


print(
    "R8D_MODEL_SET_ALIGNMENT_PASS_11=True"
)


# ============================================================
# 5. Integrated table
# ============================================================

integrated = []


for model in sorted(
    science
):

    e = efficiency[
        model
    ]


    row = {
        "model":
            model,
    }


    for metric in SCIENTIFIC_METRICS:

        row[
            metric
        ] = science[
            model
        ][
            metric
        ]


    row.update({
        "parameter_count":
            int(
                e[
                    "parameter_count"
                ]
            ),

        "checkpoint_bytes":
            int(
                e[
                    "checkpoint_bytes"
                ]
            ),

        "checkpoint_mb_decimal":
            float(
                e[
                    "checkpoint_mb_decimal"
                ]
            ),

        "cpu_batch1_median_ms":
            float(
                e[
                    "cpu_batch1_median_ms"
                ]
            ),

        "gpu_batch1_median_ms":
            float(
                e[
                    "gpu_batch1_median_ms"
                ]
            ),

        "gpu_batch64_samples_per_second":
            float(
                e[
                    "gpu_batch64_samples_per_second"
                ]
            ),
    })


    integrated.append(
        row
    )


write_csv(
    OUT
    / "integrated_scientific_efficiency_11.csv",
    integrated,
)


print(
    "R8D_INTEGRATED_TABLE_PASS_11=True"
)


lookup = {
    row[
        "model"
    ]:
        row

    for row in integrated
}


v26 = lookup[
    V26
]

v25 = lookup[
    V25
]


# ============================================================
# 6. Frozen efficiency ranks
# ============================================================

rank_rows = read_csv(
    R8C
    / "efficiency_rankings_55.csv"
)


if len(
    rank_rows
) != 55:

    raise RuntimeError(
        "Efficiency ranking rows != 55"
    )


v26_eff_ranks = {
    row[
        "metric"
    ]:
        int(
            row[
                "rank"
            ]
        )

    for row in rank_rows

    if row[
        "model"
    ]
    ==
    V26
}


if len(
    v26_eff_ranks
) != 5:

    raise RuntimeError(
        "V26 efficiency ranks incomplete"
    )


# ============================================================
# 7. Direct V26C versus V25 efficiency comparison
# ============================================================

v26_vs_v25 = {
    "v26_parameter_count_fixture":
        v26[
            "parameter_count"
        ],

    "v25_parameter_count_fixture":
        v25[
            "parameter_count"
        ],

    "parameter_reduction_fraction":
        (
            1.0
            -
            v26[
                "parameter_count"
            ]
            /
            v25[
                "parameter_count"
            ]
        ),

    "parameter_reduction_percent":
        (
            100.0
            *
            (
                1.0
                -
                v26[
                    "parameter_count"
                ]
                /
                v25[
                    "parameter_count"
                ]
            )
        ),

    "v26_checkpoint_bytes":
        v26[
            "checkpoint_bytes"
        ],

    "v25_checkpoint_bytes":
        v25[
            "checkpoint_bytes"
        ],

    "checkpoint_reduction_fraction":
        (
            1.0
            -
            v26[
                "checkpoint_bytes"
            ]
            /
            v25[
                "checkpoint_bytes"
            ]
        ),

    "checkpoint_reduction_percent":
        (
            100.0
            *
            (
                1.0
                -
                v26[
                    "checkpoint_bytes"
                ]
                /
                v25[
                    "checkpoint_bytes"
                ]
            )
        ),

    "v26_cpu_batch1_median_ms":
        v26[
            "cpu_batch1_median_ms"
        ],

    "v25_cpu_batch1_median_ms":
        v25[
            "cpu_batch1_median_ms"
        ],

    "cpu_latency_ratio_v26_over_v25":
        (
            v26[
                "cpu_batch1_median_ms"
            ]
            /
            v25[
                "cpu_batch1_median_ms"
            ]
        ),

    "v26_gpu_batch1_median_ms":
        v26[
            "gpu_batch1_median_ms"
        ],

    "v25_gpu_batch1_median_ms":
        v25[
            "gpu_batch1_median_ms"
        ],

    "gpu_latency_ratio_v26_over_v25":
        (
            v26[
                "gpu_batch1_median_ms"
            ]
            /
            v25[
                "gpu_batch1_median_ms"
            ]
        ),

    "v26_gpu_batch64_samples_per_second":
        v26[
            "gpu_batch64_samples_per_second"
        ],

    "v25_gpu_batch64_samples_per_second":
        v25[
            "gpu_batch64_samples_per_second"
        ],

    "throughput_ratio_v26_over_v25":
        (
            v26[
                "gpu_batch64_samples_per_second"
            ]
            /
            v25[
                "gpu_batch64_samples_per_second"
            ]
        ),

    "throughput_reduction_percent":
        (
            100.0
            *
            (
                1.0
                -
                v26[
                    "gpu_batch64_samples_per_second"
                ]
                /
                v25[
                    "gpu_batch64_samples_per_second"
                ]
            )
        ),
}


write_json(
    OUT
    / "v26c_vs_v25_efficiency_tradeoff.json",
    v26_vs_v25,
)


# ============================================================
# 8. Pareto membership
#
# For each robustness metric x efficiency metric:
# maximize robustness.
# efficiency is minimized except throughput, which is maximized.
# ============================================================

def dominates(
    a,
    b,
    robust_metric,
    eff_metric,
    direction,
):

    robust_no_worse = (
        a[
            robust_metric
        ]
        >=
        b[
            robust_metric
        ]
    )


    robust_strict = (
        a[
            robust_metric
        ]
        >
        b[
            robust_metric
        ]
    )


    if direction == "lower":

        eff_no_worse = (
            a[
                eff_metric
            ]
            <=
            b[
                eff_metric
            ]
        )

        eff_strict = (
            a[
                eff_metric
            ]
            <
            b[
                eff_metric
            ]
        )

    else:

        eff_no_worse = (
            a[
                eff_metric
            ]
            >=
            b[
                eff_metric
            ]
        )

        eff_strict = (
            a[
                eff_metric
            ]
            >
            b[
                eff_metric
            ]
        )


    return (
        robust_no_worse
        and
        eff_no_worse
        and
        (
            robust_strict
            or
            eff_strict
        )
    )


pareto_membership = []
pareto_summary = []


for robust_metric in PRIMARY_ROBUSTNESS:

    for eff_metric, direction in EFFICIENCY_METRICS.items():

        front = []


        for candidate in integrated:

            dominated = False


            for other in integrated:

                if (
                    other[
                        "model"
                    ]
                    ==
                    candidate[
                        "model"
                    ]
                ):

                    continue


                if dominates(
                    other,
                    candidate,
                    robust_metric,
                    eff_metric,
                    direction,
                ):

                    dominated = True
                    break


            on_front = not dominated


            pareto_membership.append({
                "robustness_metric":
                    robust_metric,

                "efficiency_metric":
                    eff_metric,

                "efficiency_direction":
                    direction,

                "model":
                    candidate[
                        "model"
                    ],

                "on_pareto_front":
                    on_front,
            })


            if on_front:

                front.append(
                    candidate[
                        "model"
                    ]
                )


        pareto_summary.append({
            "robustness_metric":
                robust_metric,

            "efficiency_metric":
                eff_metric,

            "efficiency_direction":
                direction,

            "pareto_front_model_count":
                len(
                    front
                ),

            "pareto_front_models":
                "|".join(
                    sorted(
                        front
                    )
                ),

            "v26c_on_front":
                V26
                in
                front,
        })


if len(
    pareto_membership
) != 110:

    raise RuntimeError(
        "Pareto membership rows != 110"
    )


if len(
    pareto_summary
) != 10:

    raise RuntimeError(
        "Pareto summary rows != 10"
    )


write_csv(
    OUT
    / "robustness_efficiency_pareto_membership_110.csv",
    pareto_membership,
)


write_csv(
    OUT
    / "robustness_efficiency_pareto_summary_10.csv",
    pareto_summary,
)


v26_pareto_count = sum(
    bool(
        row[
            "v26c_on_front"
        ]
    )
    for row in pareto_summary
)


print(
    "R8D_V26C_PARETO_FRONT_COMBINATIONS=",
    f"{v26_pareto_count}/10"
)


# ============================================================
# 9. Strong robustness + compactness dominance
#
# Determine models for which V26C has:
# higher both primary robustness F1s AND fewer parameters.
# ============================================================

dominance_rows = []


for model, other in sorted(
    lookup.items()
):

    if model == V26:
        continue


    stronger_all_fault = (
        v26[
            "all_fault_macro_f1"
        ]
        >
        other[
            "all_fault_macro_f1"
        ]
    )


    stronger_family_bal = (
        v26[
            "family_balanced_macro_f1"
        ]
        >
        other[
            "family_balanced_macro_f1"
        ]
    )


    fewer_params = (
        v26[
            "parameter_count"
        ]
        <
        other[
            "parameter_count"
        ]
    )


    smaller_checkpoint = (
        v26[
            "checkpoint_bytes"
        ]
        <
        other[
            "checkpoint_bytes"
        ]
    )


    dominance_rows.append({
        "comparator":
            model,

        "v26_higher_all_fault_macro_f1":
            stronger_all_fault,

        "v26_higher_family_balanced_macro_f1":
            stronger_family_bal,

        "v26_fewer_parameters":
            fewer_params,

        "v26_smaller_checkpoint":
            smaller_checkpoint,

        "v26_dominates_robustness_plus_parameters":
            (
                stronger_all_fault
                and
                stronger_family_bal
                and
                fewer_params
            ),

        "v26_dominates_robustness_plus_checkpoint":
            (
                stronger_all_fault
                and
                stronger_family_bal
                and
                smaller_checkpoint
            ),
    })


write_csv(
    OUT
    / "v26c_robustness_compactness_dominance_10.csv",
    dominance_rows,
)


param_dominance_count = sum(
    row[
        "v26_dominates_robustness_plus_parameters"
    ]
    for row in dominance_rows
)


checkpoint_dominance_count = sum(
    row[
        "v26_dominates_robustness_plus_checkpoint"
    ]
    for row in dominance_rows
)


# ============================================================
# 10. Claim authorization
# ============================================================

claim_policy = {
    "stage":
        "V26_INTERNAL_SCIENTIFIC_EFFICIENCY_CLOSURE_R8D",

    "status":
        "PASS",

    "candidate":
        V26,

    "scientific_result":
        {
            "rank1_metrics":
                "8_OF_8",

            "comparison_models":
                11,

            "claim_tier":
                r7[
                    "predeclared_claim_tier"
                ],

            "clean_macro_f1":
                r7[
                    "clean_macro_f1"
                ],

            "all_fault_macro_f1":
                r7[
                    "all_fault_macro_f1"
                ],

            "family_balanced_macro_f1":
                r7[
                    "family_balanced_macro_f1"
                ],
        },

    "efficiency_fixture_result":
        {
            "parameter_count":
                v26[
                    "parameter_count"
                ],

            "checkpoint_bytes":
                v26[
                    "checkpoint_bytes"
                ],

            "cpu_batch1_median_ms":
                v26[
                    "cpu_batch1_median_ms"
                ],

            "gpu_batch1_median_ms":
                v26[
                    "gpu_batch1_median_ms"
                ],

            "gpu_batch64_samples_per_second":
                v26[
                    "gpu_batch64_samples_per_second"
                ],

            "ranks_out_of_11":
                v26_eff_ranks,

            "mac_flop":
                "NOT_COMPARABLE",
        },

    "architecture_parameter_reporting":
        {
            "uci_har_6class_fixture_parameters":
                v26[
                    "parameter_count"
                ],

            "maximum_confirmed_parameters_across_four_datasets":
                r7[
                    "max_parameter_count"
                ],

            "reporting_note":
                (
                    "R8C uses the fixed six-class UCI-HAR "
                    "fixture for fair runtime comparison; "
                    "R7 maximum parameter count includes "
                    "dataset-dependent classifier heads."
                ),
        },

    "v26_vs_v25_efficiency":
        v26_vs_v25,

    "robustness_efficiency_pareto_front_combinations":
        v26_pareto_count,

    "total_pareto_combinations":
        10,

    "robustness_plus_parameter_dominance_comparator_count":
        param_dominance_count,

    "robustness_plus_checkpoint_dominance_comparator_count":
        checkpoint_dominance_count,

    "allowed_claims": {
        "internal_rank1_robustness":
            True,

        "predeclared_tier_a_internal_superiority":
            True,

        "parameter_compactness":
            True,

        "checkpoint_compactness":
            True,

        "robustness_model_size_tradeoff":
            True,

        "descriptive_pareto_membership":
            True,

        "cpu_latency_superiority":
            False,

        "gpu_latency_superiority":
            False,

        "gpu_throughput_superiority":
            False,

        "overall_runtime_efficiency_superiority":
            False,

        "mac_flop_superiority":
            False,

        "deployment_superiority":
            False,

        "universal_sota":
            False,

        "external_storm_superiority":
            False,
    },

    "runtime_interpretation":
        (
            "V26C is compact in parameter/checkpoint size "
            "but is not latency- or throughput-leading under "
            "the frozen single-host PyTorch benchmark. "
            "Its dual-branch reliability/fusion graph creates "
            "runtime overhead not captured by parameter count."
        ),

    "timing_scope":
        (
            "Single controlled host/session, synthetic inputs, "
            "PyTorch eager inference, fixed RTX 4090 GPU0 and "
            "single CPU thread. Runtime values are host- and "
            "implementation-specific, not universal hardware claims."
        ),

    "no_post_efficiency_tuning":
        True,

    "candidate_retraining_allowed":
        False,

    "candidate_architecture_modification_allowed":
        False,

    "training_performed":
        False,

    "model_constructed":
        False,

    "test_data_accessed":
        False,

    "timing_performed":
        False,

    "storm_used":
        False,

    "next_gate":
        (
            "Internal V26 evidence is frozen. External STORM "
            "stretch evaluation may now be opened using the "
            "unchanged V26C model and independently frozen "
            "cross-source protocol. No V26C tuning is permitted."
        ),
}


write_json(
    OUT
    / "v26_internal_scientific_efficiency_claim_policy_r8d.json",
    claim_policy,
)


# ============================================================
# 11. Print paper-facing internal result
# ============================================================

print()
print("=" * 118)
print("V26 R8D INTERNAL SCIENTIFIC + EFFICIENCY CLOSURE")
print("=" * 118)


print(
    "V26C_INTERNAL_SCIENTIFIC_RANK1_METRICS=8/8"
)

print(
    "V26C_INTERNAL_CLAIM_TIER=",
    r7[
        "predeclared_claim_tier"
    ],
)

print(
    "V26C_R7_MAX_PARAMETERS=",
    r7[
        "max_parameter_count"
    ],
)

print(
    "V26C_R8C_UCI_FIXTURE_PARAMETERS=",
    v26[
        "parameter_count"
    ],
)

print(
    "V26C_R8C_PARAMETER_RANK=",
    f"{v26_eff_ranks['parameter_count']}/11"
)

print(
    "V26C_R8C_CHECKPOINT_RANK=",
    f"{v26_eff_ranks['checkpoint_bytes']}/11"
)

print(
    "V26C_R8C_CPU_LATENCY_RANK=",
    f"{v26_eff_ranks['cpu_batch1_median_ms']}/11"
)

print(
    "V26C_R8C_GPU_LATENCY_RANK=",
    f"{v26_eff_ranks['gpu_batch1_median_ms']}/11"
)

print(
    "V26C_R8C_GPU_THROUGHPUT_RANK=",
    f"{v26_eff_ranks['gpu_batch64_samples_per_second']}/11"
)


print()
print("=" * 118)
print("V26C VS V25 EFFICIENCY TRADEOFF")
print("=" * 118)

print(
    "V26C_VS_V25_PARAMETER_REDUCTION_PERCENT=",
    f"{v26_vs_v25['parameter_reduction_percent']:.3f}"
)

print(
    "V26C_VS_V25_CHECKPOINT_REDUCTION_PERCENT=",
    f"{v26_vs_v25['checkpoint_reduction_percent']:.3f}"
)

print(
    "V26C_VS_V25_CPU_LATENCY_RATIO=",
    f"{v26_vs_v25['cpu_latency_ratio_v26_over_v25']:.3f}x"
)

print(
    "V26C_VS_V25_GPU_LATENCY_RATIO=",
    f"{v26_vs_v25['gpu_latency_ratio_v26_over_v25']:.3f}x"
)

print(
    "V26C_VS_V25_GPU_THROUGHPUT_RATIO=",
    f"{v26_vs_v25['throughput_ratio_v26_over_v25']:.3f}x"
)


print()
print("=" * 118)
print("PARETO / CLAIM POLICY")
print("=" * 118)

print(
    "V26C_PARETO_FRONT_COMBINATIONS=",
    f"{v26_pareto_count}/10"
)

print(
    "V26C_ROBUSTNESS_PLUS_PARAMETER_DOMINANCE_COUNT=",
    f"{param_dominance_count}/10"
)

print(
    "V26C_ROBUSTNESS_PLUS_CHECKPOINT_DOMINANCE_COUNT=",
    f"{checkpoint_dominance_count}/10"
)

print(
    "ROBUSTNESS_MODEL_SIZE_TRADEOFF_CLAIM_ALLOWED=True"
)

print(
    "CPU_LATENCY_SUPERIORITY_CLAIM_ALLOWED=False"
)

print(
    "GPU_LATENCY_SUPERIORITY_CLAIM_ALLOWED=False"
)

print(
    "GPU_THROUGHPUT_SUPERIORITY_CLAIM_ALLOWED=False"
)

print(
    "OVERALL_RUNTIME_EFFICIENCY_SUPERIORITY_CLAIM_ALLOWED=False"
)

print(
    "MAC_FLOP_SUPERIORITY_CLAIM_ALLOWED=False"
)

print(
    "UNIVERSAL_SOTA_CLAIM_ALLOWED=False"
)

print(
    "EXTERNAL_STORM_SUPERIORITY_CLAIM_ALLOWED=False"
)


print()
print(
    "V26_INTERNAL_SCIENTIFIC_EFFICIENCY_CLOSURE_R8D_PASS=True"
)

print(
    "MODEL_CONSTRUCTED=False"
)

print(
    "TEST_DATA_ACCESSED=False"
)

print(
    "TIMING_PERFORMED=False"
)

print(
    "TRAINING_PERFORMED=False"
)

print(
    "STORM_USED=False"
)
