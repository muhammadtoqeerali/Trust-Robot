from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np


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

OUT = (
    ROOT
    / "results/stage25_physical_fault_protocol"
    / "gaussian_precision_diagnostic_r4a_n1"
)

OUT.mkdir(
    parents=True,
    exist_ok=True,
)


DATA_ROOT = (
    ROOT
    / "data/processed/harmonized"
)

SPLIT_ROOT = (
    ROOT
    / "data/processed/splits"
)


DATASETS = [
    "UCI_HAR",
    "PAMAP2",
    "DSADS",
    "MotionSense",
]


GAUSSIAN = {
    "acc_noise_sigma0.5": [
        0,
        1,
        2,
    ],

    "gyro_noise_sigma0.5": [
        3,
        4,
        5,
    ],
}


TOL = 1e-6


def write_json(
    path,
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


def max_abs(
    a,
    b,
):
    return float(
        np.max(
            np.abs(
                np.asarray(
                    a,
                    dtype=np.float64,
                )
                -
                np.asarray(
                    b,
                    dtype=np.float64,
                )
            )
        )
    )


def diff_stats(
    a,
    b,
):
    d = np.abs(
        np.asarray(
            a,
            dtype=np.float64,
        )
        -
        np.asarray(
            b,
            dtype=np.float64,
        )
    )

    flat = d.reshape(-1)

    return {
        "max":
            float(
                np.max(flat)
            ),

        "mean":
            float(
                np.mean(flat)
            ),

        "p99":
            float(
                np.quantile(
                    flat,
                    0.99,
                )
            ),

        "p999":
            float(
                np.quantile(
                    flat,
                    0.999,
                )
            ),

        "p9999":
            float(
                np.quantile(
                    flat,
                    0.9999,
                )
            ),

        "nonzero":
            int(
                np.count_nonzero(
                    flat
                )
            ),

        "total":
            int(
                flat.size
            ),

        "fraction_nonzero":
            float(
                np.count_nonzero(
                    flat
                )
                /
                flat.size
            ),
    }


def normalize32(
    raw,
    mean,
    std,
):
    return np.asarray(
        (
            raw
            -
            mean.reshape(
                1,
                1,
                6,
            )
        )
        /
        std.reshape(
            1,
            1,
            6,
        ),
        dtype=np.float32,
    )


def normalize64(
    raw,
    mean,
    std,
):
    return (
        np.asarray(
            raw,
            dtype=np.float64,
        )
        -
        np.asarray(
            mean,
            dtype=np.float64,
        ).reshape(
            1,
            1,
            6,
        )
    ) / (
        np.asarray(
            std,
            dtype=np.float64,
        ).reshape(
            1,
            1,
            6,
        )
    )


print(
    "=" * 112
)

print(
    "STAGE25 R4A-N1 GAUSSIAN PRECISION DECOMPOSITION"
)

print(
    "NO MODEL DESERIALIZATION / NO FORWARD / NO TRAINING"
)

print(
    "=" * 112
)


# ============================================================
# Frozen provenance
# ============================================================

norm_path = (
    R2
    / "dataset_normalization_receipts.json"
)

seed_path = (
    R3
    / "stochastic_fault_seed_manifest_24.csv"
)

protocol_path = (
    R3
    / "stage25_physical_fault_protocol_r3.json"
)


for path in [
    norm_path,
    seed_path,
    protocol_path,
]:

    if not path.exists():
        raise FileNotFoundError(
            path
        )


normalization = json.loads(
    norm_path.read_text()
)

protocol = json.loads(
    protocol_path.read_text()
)


if (
    protocol[
        "fault_condition_count"
    ]
    != 17
):
    raise RuntimeError(
        "Frozen R3 fault protocol changed"
    )


with seed_path.open(
    newline="",
    encoding="utf-8",
) as f:

    seeds = list(
        csv.DictReader(f)
    )


seed_lookup = {
    (
        row[
            "dataset"
        ],
        row[
            "condition"
        ],
    ):
        int(
            row[
                "seed"
            ]
        )

    for row in seeds
}


rows = []


# ============================================================
# Main diagnostic
# ============================================================

for dataset in DATASETS:

    print()
    print(
        "=" * 100
    )

    print(
        "DATASET=",
        dataset
    )

    print(
        "=" * 100
    )


    X_path = (
        DATA_ROOT
        / dataset
        / "X.npy"
    )

    test_path = (
        SPLIT_ROOT
        / dataset
        / "test_idx.npy"
    )


    X = np.load(
        X_path,
        mmap_mode="r",
        allow_pickle=False,
    )

    test_idx = np.load(
        test_path,
        allow_pickle=False,
    )


    # This mirrors frozen dataset_v3r1:
    # X is converted to float32 before normalization.
    raw32 = np.asarray(
        X[
            np.asarray(
                test_idx,
                dtype=np.int64,
            )
        ],
        dtype=np.float32,
    )


    mean32 = np.asarray(
        normalization[
            dataset
        ][
            "mean"
        ],
        dtype=np.float32,
    )

    std32 = np.asarray(
        normalization[
            dataset
        ][
            "std"
        ],
        dtype=np.float32,
    )


    mean64 = mean32.astype(
        np.float64
    )

    std64 = std32.astype(
        np.float64
    )


    # Canonical current clean normalization.
    clean32 = normalize32(
        raw32,
        mean32,
        std32,
    )


    # Same mathematical clean normalization evaluated in float64,
    # then rounded once to model dtype.
    clean64 = normalize64(
        raw32,
        mean64,
        std64,
    )

    clean64_cast32 = clean64.astype(
        np.float32
    )


    clean_precision = diff_stats(
        clean32,
        clean64_cast32,
    )


    print(
        "CLEAN32_VS_FLOAT64CAST32_MAX=",
        clean_precision[
            "max"
        ],
    )

    print(
        "CLEAN32_VS_FLOAT64CAST32_MEAN=",
        clean_precision[
            "mean"
        ],
    )


    for condition, channels in GAUSSIAN.items():

        key = (
            dataset,
            condition,
        )


        if key not in seed_lookup:

            raise RuntimeError(
                f"Frozen stochastic seed missing: {key}"
            )


        seed = seed_lookup[
            key
        ]


        rng = np.random.RandomState(
            seed
        )


        epsilon32 = rng.normal(
            loc=0.0,
            scale=1.0,
            size=(
                raw32.shape[0],
                raw32.shape[1],
                len(
                    channels
                ),
            ),
        ).astype(
            np.float32
        )


        epsilon64 = epsilon32.astype(
            np.float64
        )


        # =====================================================
        # A. CURRENT R4A FLOAT32 IMPLEMENTATION
        # =====================================================

        pre_raw32 = np.array(
            raw32,
            copy=True,
        )


        for local_i, channel in enumerate(
            channels
        ):

            pre_raw32[
                :,
                :,
                channel,
            ] += (
                np.float32(
                    0.5
                )
                *
                std32[
                    channel
                ]
                *
                epsilon32[
                    :,
                    :,
                    local_i,
                ]
            )


        current_pre32 = normalize32(
            pre_raw32,
            mean32,
            std32,
        )


        current_post32 = np.array(
            clean32,
            copy=True,
        )


        for local_i, channel in enumerate(
            channels
        ):

            current_post32[
                :,
                :,
                channel,
            ] += (
                np.float32(
                    0.5
                )
                *
                epsilon32[
                    :,
                    :,
                    local_i,
                ]
            )


        current_diff = diff_stats(
            current_pre32,
            current_post32,
        )


        # =====================================================
        # B. EXACT SAME FROZEN OPERATOR EVALUATED IN FLOAT64
        #
        # Epsilon values themselves remain the SAME epsilon32
        # values; they are merely promoted to isolate arithmetic
        # roundoff.
        # =====================================================

        raw64 = raw32.astype(
            np.float64
        )


        pre_raw64 = np.array(
            raw64,
            copy=True,
        )


        for local_i, channel in enumerate(
            channels
        ):

            pre_raw64[
                :,
                :,
                channel,
            ] += (
                0.5
                *
                std64[
                    channel
                ]
                *
                epsilon64[
                    :,
                    :,
                    local_i,
                ]
            )


        pre64 = normalize64(
            pre_raw64,
            mean64,
            std64,
        )


        post64 = normalize64(
            raw64,
            mean64,
            std64,
        )


        for local_i, channel in enumerate(
            channels
        ):

            post64[
                :,
                :,
                channel,
            ] += (
                0.5
                *
                epsilon64[
                    :,
                    :,
                    local_i,
                ]
            )


        exact64_diff = diff_stats(
            pre64,
            post64,
        )


        # =====================================================
        # C. FLOAT64 EVALUATION, THEN ONE ROUND TO FLOAT32
        # =====================================================

        pre64_cast32 = pre64.astype(
            np.float32
        )

        post64_cast32 = post64.astype(
            np.float32
        )


        cast32_pair_diff = diff_stats(
            pre64_cast32,
            post64_cast32,
        )


        # =====================================================
        # D. Minimum-change candidates
        #
        # Can we keep canonical post-normalization float32 and
        # only evaluate the pre-normalization pathway more
        # accurately?
        # =====================================================

        highprecision_pre_vs_current_post = (
            diff_stats(
                pre64_cast32,
                current_post32,
            )
        )


        current_pre_vs_highprecision_post = (
            diff_stats(
                current_pre32,
                post64_cast32,
            )
        )


        current_pre_vs_reference_pre = (
            diff_stats(
                current_pre32,
                pre64_cast32,
            )
        )


        current_post_vs_reference_post = (
            diff_stats(
                current_post32,
                post64_cast32,
            )
        )


        print()
        print(
            "CONDITION=",
            condition,
        )

        print(
            "FROZEN_SEED=",
            seed,
        )

        print(
            "CURRENT_FLOAT32_PAIR_MAX=",
            current_diff[
                "max"
            ],
        )

        print(
            "CURRENT_FLOAT32_PAIR_MEAN=",
            current_diff[
                "mean"
            ],
        )

        print(
            "CURRENT_FLOAT32_PAIR_NONZERO=",
            current_diff[
                "nonzero"
            ],
            "/",
            current_diff[
                "total"
            ],
        )

        print(
            "FLOAT64_EXACT_PAIR_MAX=",
            exact64_diff[
                "max"
            ],
        )

        print(
            "FLOAT64_TO_FLOAT32_PAIR_MAX=",
            cast32_pair_diff[
                "max"
            ],
        )

        print(
            "FLOAT64_PRE_TO_CURRENT_POST_MAX=",
            highprecision_pre_vs_current_post[
                "max"
            ],
        )

        print(
            "CURRENT_PRE_TO_FLOAT64_POST_MAX=",
            current_pre_vs_highprecision_post[
                "max"
            ],
        )

        print(
            "CURRENT_PRE_TO_REFERENCE_PRE_MAX=",
            current_pre_vs_reference_pre[
                "max"
            ],
        )

        print(
            "CURRENT_POST_TO_REFERENCE_POST_MAX=",
            current_post_vs_reference_post[
                "max"
            ],
        )


        # Scientific/numerical classification.
        if (
            exact64_diff[
                "max"
            ]
            <=
            1e-12
        ):

            math_gate = True

        else:

            math_gate = False


        if (
            cast32_pair_diff[
                "max"
            ]
            <=
            TOL
        ):

            one_round_gate = True

        else:

            one_round_gate = False


        if not math_gate:

            classification = (
                "NOT_PURE_FLOAT32_ROUNDOFF_"
                "REQUIRES_TRANSFORM_RECONCILIATION"
            )

        elif one_round_gate:

            classification = (
                "PURE_FLOAT32_OPERATION_ORDER_ROUNDOFF_"
                "HIGH_PRECISION_OPERATOR_EVALUATION_"
                "PRESERVES_FROZEN_1E6_GATE"
            )

        else:

            classification = (
                "MATHEMATICALLY_COMMUTING_BUT_"
                "FLOAT32_QUANTIZATION_STILL_EXCEEDS_"
                "FROZEN_GATE_REQUIRES_FURTHER_REVIEW"
            )


        print(
            "NUMERICAL_CLASSIFICATION=",
            classification,
        )


        rows.append({
            "dataset":
                dataset,

            "condition":
                condition,

            "seed":
                seed,

            "current_float32_pair_max":
                current_diff[
                    "max"
                ],

            "current_float32_pair_mean":
                current_diff[
                    "mean"
                ],

            "current_float32_pair_p9999":
                current_diff[
                    "p9999"
                ],

            "current_float32_pair_nonzero":
                current_diff[
                    "nonzero"
                ],

            "float64_exact_pair_max":
                exact64_diff[
                    "max"
                ],

            "float64_to_float32_pair_max":
                cast32_pair_diff[
                    "max"
                ],

            "float64_pre_to_current_post_max":
                highprecision_pre_vs_current_post[
                    "max"
                ],

            "current_pre_to_float64_post_max":
                current_pre_vs_highprecision_post[
                    "max"
                ],

            "current_pre_to_reference_pre_max":
                current_pre_vs_reference_pre[
                    "max"
                ],

            "current_post_to_reference_post_max":
                current_post_vs_reference_post[
                    "max"
                ],

            "clean32_vs_float64cast32_max":
                clean_precision[
                    "max"
                ],

            "mathematical_commutation_1e12_pass":
                math_gate,

            "float64_then_float32_1e6_pass":
                one_round_gate,

            "classification":
                classification,
        })


# ============================================================
# Aggregate decision
# ============================================================

if len(
    rows
) != 8:

    raise RuntimeError(
        f"Expected 8 Gaussian diagnostic rows, "
        f"found {len(rows)}"
    )


all_math = all(
    row[
        "mathematical_commutation_1e12_pass"
    ]
    for row in rows
)


all_single_round = all(
    row[
        "float64_then_float32_1e6_pass"
    ]
    for row in rows
)


print()
print(
    "=" * 112
)

print(
    "R4A-N1 NUMERICAL DECISION"
)

print(
    "=" * 112
)

print(
    "GAUSSIAN_MATHEMATICAL_COMMUTATION_PASS_8_OF_8=",
    all_math,
)

print(
    "GAUSSIAN_FLOAT64_THEN_FLOAT32_FROZEN_1E6_GATE_PASS_8_OF_8=",
    all_single_round,
)


if all_math and all_single_round:

    final_classification = (
        "FLOAT32_OPERATION_ORDER_ROUNDOFF_CONFIRMED_"
        "NO_SCIENTIFIC_PROTOCOL_CHANGE_REQUIRED"
    )

elif all_math:

    final_classification = (
        "MATHEMATICAL_COMMUTATION_CONFIRMED_"
        "BUT_FROZEN_NUMERICAL_GATE_NEEDS_FURTHER_"
        "IMPLEMENTATION_RECONCILIATION"
    )

else:

    final_classification = (
        "TRANSFORM_SEMANTICS_RECONCILIATION_REQUIRED"
    )


print(
    "FINAL_NUMERICAL_CLASSIFICATION=",
    final_classification,
)


with (
    OUT
    / "gaussian_precision_diagnostic_8.csv"
).open(
    "w",
    newline="",
    encoding="utf-8",
) as f:

    fields = list(
        rows[0].keys()
    )

    writer = csv.DictWriter(
        f,
        fieldnames=fields,
    )

    writer.writeheader()

    writer.writerows(
        rows
    )


receipt = {
    "audit":
        "STAGE25_R4A_GAUSSIAN_PRECISION_DIAGNOSTIC_N1",

    "status":
        "PASS_DIAGNOSTIC_COMPLETE",

    "r3_protocol_modified":
        False,

    "r4a_evaluator_modified":
        False,

    "commutation_tolerance_modified":
        False,

    "fault_severity_modified":
        False,

    "fault_seed_modified":
        False,

    "model_bank_modified":
        False,

    "gaussian_cases_diagnosed":
        8,

    "mathematical_commutation_all_cases":
        all_math,

    "float64_then_float32_frozen_gate_all_cases":
        all_single_round,

    "final_classification":
        final_classification,

    "model_deserialization_performed":
        False,

    "model_forward_performed":
        False,

    "training_performed":
        False,

    "checkpoint_modified":
        False,

    "dataset_modified":
        False,
}


write_json(
    OUT
    / "stage25_r4a_gaussian_precision_diagnostic_receipt_n1.json",
    receipt,
)


print()
print(
    json.dumps(
        receipt,
        indent=2,
    )
)

print()
print(
    "STAGE25_R4A_GAUSSIAN_PRECISION_DIAGNOSTIC_N1_COMPLETE=True"
)

print(
    "R3_PROTOCOL_MODIFIED=False"
)

print(
    "R4A_EVALUATOR_MODIFIED=False"
)

print(
    "COMMUTATION_TOLERANCE_MODIFIED=False"
)

print(
    "MODEL_DESERIALIZATION_PERFORMED=False"
)

print(
    "MODEL_FORWARD_PERFORMED=False"
)

print(
    "TRAINING_PERFORMED=False"
)
