from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(
    "/mnt/hdd16T/ToqeerHomeBackup/toqeer/IMU_Reliability"
)

OUT = (
    ROOT
    / "results"
    / "stage25_physical_fault_protocol"
    / "protocol_preregistration_r3"
)

R2 = (
    ROOT
    / "results"
    / "stage25_physical_fault_protocol"
    / "canonical_reconstruction_audit_r2"
)

V3 = (
    ROOT
    / "results"
    / "benchmark_v3r1"
)

V25 = (
    ROOT
    / "results"
    / "v25_final_r2"
)

OUT.mkdir(
    parents=True,
    exist_ok=True,
)


R2_SHA256SUMS_SHA = (
    "1adee59fa04c865266f58a58344af264"
    "e20a49b1fcaf800ab795c165bdb041ed"
)

STAGE24_CLOSURE_SHA = (
    "15ab874acc4d0420adff73bef32f76b"
    "8882a743509682333fdb87fa925060bfa"
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

V3_MODELS = [
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

V25_MODEL = (
    "ReliabilityCNN_v25"
)

CHANNELS = [
    "accel_x",
    "accel_y",
    "accel_z",
    "gyro_x",
    "gyro_y",
    "gyro_z",
]

CHANNEL_INDEX = {
    name: i
    for i, name in enumerate(
        CHANNELS
    )
}

ACC = [
    0,
    1,
    2,
]

GYRO = [
    3,
    4,
    5,
]

ALL_CHANNELS = list(
    range(6)
)


# ============================================================
# Utility
# ============================================================

def sha256_file(
    path: Path,
) -> str:

    h = hashlib.sha256()

    with path.open(
        "rb"
    ) as f:

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


def deterministic_fault_seed(
    dataset: str,
    condition: str,
) -> int:
    """
    Dataset-condition seed frozen before outcome evaluation.

    Root seed 42 is retained for continuity, but SHA derivation
    prevents stochastic tensors for different dataset/condition
    pairs from accidentally sharing identical streams.
    """

    token = (
        "STAGE25_R3"
        "|ROOT_SEED=42"
        f"|DATASET={dataset}"
        f"|CONDITION={condition}"
    )

    digest = hashlib.sha256(
        token.encode(
            "utf-8"
        )
    ).digest()

    return int.from_bytes(
        digest[:4],
        byteorder="little",
        signed=False,
    )


# ============================================================
# Header
# ============================================================

print(
    "=" * 110
)

print(
    "STAGE25 R3 PHYSICAL-vs-POSTNORMALIZATION "
    "FAULT PROTOCOL PRE-REGISTRATION"
)

print(
    "NO MODEL DESERIALIZATION / NO FORWARD / NO TRAINING"
)

print(
    "=" * 110
)


# ============================================================
# 1. Verify successful R2 receipt
# ============================================================

r2_receipt_path = (
    R2
    / "stage25_canonical_reconstruction_receipt_r2.json"
)

if not r2_receipt_path.exists():

    raise FileNotFoundError(
        r2_receipt_path
    )


r2 = json.loads(
    r2_receipt_path.read_text()
)


required_r2 = {
    "status":
        "PASS",

    "canonical_dataset_reconstruction":
        "PASS_4_OF_4",

    "pre_normalization_signal_recoverable":
        "PASS_4_OF_4",

    "train_normalization_recomputed":
        "PASS_4_OF_4",

    "v3r1_checkpoint_pair_sha":
        "PASS_180_OF_180",
}


for key, expected in required_r2.items():

    actual = r2.get(
        key
    )

    if actual != expected:

        raise RuntimeError(
            f"R2 prerequisite failed: "
            f"{key}={actual!r}, "
            f"expected {expected!r}"
        )


print(
    "R2_SCIENTIFIC_PREREQUISITES_PASS=True"
)


# ============================================================
# 2. Freeze exact V3R1 checkpoint bank from R2
# ============================================================

v3_manifest_path = (
    R2
    / "v3r1_checkpoint_integrity_180.csv"
)

if not v3_manifest_path.exists():

    raise FileNotFoundError(
        v3_manifest_path
    )


with v3_manifest_path.open(
    newline="",
    encoding="utf-8",
) as f:

    v3_rows = list(
        csv.DictReader(f)
    )


if len(v3_rows) != 180:

    raise RuntimeError(
        f"Expected 180 V3R1 model-bank rows, "
        f"found {len(v3_rows)}"
    )


model_bank = []


for row in v3_rows:

    dataset = row[
        "dataset"
    ]

    model = row[
        "model"
    ]

    seed = int(
        row[
            "seed"
        ]
    )


    if dataset not in DATASETS:

        raise RuntimeError(
            f"Unexpected V3 dataset: {dataset}"
        )


    if model not in V3_MODELS:

        raise RuntimeError(
            f"Unexpected V3 model: {model}"
        )


    if seed not in SEEDS:

        raise RuntimeError(
            f"Unexpected V3 seed: {seed}"
        )


    if str(
        row[
            "byte_identical"
        ]
    ).lower() not in {
        "true",
        "1",
    }:

        raise RuntimeError(
            "V3 model-bank row not SHA verified"
        )


    best = (
        ROOT
        / row[
            "best_model"
        ]
    )


    if not best.exists():

        raise FileNotFoundError(
            best
        )


    digest = sha256_file(
        best
    )


    if digest != row[
        "sha256"
    ]:

        raise RuntimeError(
            "V3 checkpoint changed since R2: "
            f"{best}"
        )


    model_bank.append({
        "bank_source":
            "V3R1",

        "dataset":
            dataset,

        "model":
            model,

        "seed":
            seed,

        "checkpoint":
            str(
                best.relative_to(
                    ROOT
                )
            ),

        "checkpoint_sha256":
            digest,

        "v25_analysis_stratum":
            "not_applicable",
    })


print(
    "V3R1_MODEL_BANK_BOUND_180_OF_180=True"
)


# ============================================================
# 3. Freeze exact V25 final checkpoint bank
#
# Only canonical raw_runs/best_model.pt is eligible.
# Traced MCU artifacts are deliberately excluded.
# ============================================================

v25_rows = []


for dataset in DATASETS:

    for seed in SEEDS:

        run_dir = (
            V25
            / "raw_runs"
            / dataset
            / V25_MODEL
            / f"seed_{seed}"
        )


        best = (
            run_dir
            / "best_model.pt"
        )

        checkpoint = (
            run_dir
            / "checkpoint.pt"
        )


        if not best.exists():

            raise FileNotFoundError(
                best
            )


        if not checkpoint.exists():

            raise FileNotFoundError(
                checkpoint
            )


        best_sha = (
            sha256_file(
                best
            )
        )

        checkpoint_sha = (
            sha256_file(
                checkpoint
            )
        )


        if (
            best_sha
            !=
            checkpoint_sha
        ):

            raise RuntimeError(
                "V25 best_model/checkpoint mismatch: "
                f"{dataset}/seed_{seed}"
            )


        # Preserve the already-frozen development / held-out
        # distinction from V25 final confirmation.
        if (
            dataset
            in {
                "UCI_HAR",
                "DSADS",
            }
            and
            seed
            in {
                42,
                123,
                456,
            }
        ):

            stratum = (
                "development"
            )

        else:

            stratum = (
                "selection_held_out"
            )


        entry = {
            "bank_source":
                "V25_FINAL_R2",

            "dataset":
                dataset,

            "model":
                V25_MODEL,

            "seed":
                seed,

            "checkpoint":
                str(
                    best.relative_to(
                        ROOT
                    )
                ),

            "checkpoint_sha256":
                best_sha,

            "v25_analysis_stratum":
                stratum,
        }


        v25_rows.append(
            entry
        )

        model_bank.append(
            entry
        )


if len(
    v25_rows
) != 20:

    raise RuntimeError(
        "Expected 20 canonical V25 checkpoints"
    )


strata = Counter(
    row[
        "v25_analysis_stratum"
    ]
    for row in v25_rows
)


if strata != {
    "development": 6,
    "selection_held_out": 14,
}:

    raise RuntimeError(
        f"Unexpected V25 stratum counts: {strata}"
    )


print(
    "V25_FINAL_MODEL_BANK_SHA_PASS_20_OF_20=True"
)

print(
    "V25_DEVELOPMENT_CHECKPOINTS=6"
)

print(
    "V25_SELECTION_HELD_OUT_CHECKPOINTS=14"
)


# ============================================================
# 4. Global 200-checkpoint bank integrity
# ============================================================

if len(
    model_bank
) != 200:

    raise RuntimeError(
        f"Expected total model bank 200, "
        f"got {len(model_bank)}"
    )


keyset = {
    (
        row[
            "dataset"
        ],
        row[
            "model"
        ],
        row[
            "seed"
        ],
    )
    for row in model_bank
}


if len(
    keyset
) != 200:

    raise RuntimeError(
        "Duplicate dataset/model/seed in model bank"
    )


dataset_bank_counts = Counter(
    row[
        "dataset"
    ]
    for row in model_bank
)


if dataset_bank_counts != {
    dataset: 50
    for dataset in DATASETS
}:

    raise RuntimeError(
        "Expected exactly 50 checkpoint cases per dataset: "
        f"{dataset_bank_counts}"
    )


with (
    OUT
    / "frozen_model_bank_200.csv"
).open(
    "w",
    newline="",
    encoding="utf-8",
) as f:

    fields = [
        "bank_source",
        "dataset",
        "model",
        "seed",
        "checkpoint",
        "checkpoint_sha256",
        "v25_analysis_stratum",
    ]

    writer = csv.DictWriter(
        f,
        fieldnames=fields,
    )

    writer.writeheader()

    writer.writerows(
        sorted(
            model_bank,
            key=lambda r: (
                DATASETS.index(
                    r["dataset"]
                ),
                r["model"],
                r["seed"],
            ),
        )
    )


print(
    "FROZEN_MODEL_BANK_PASS_200_OF_200=True"
)


# ============================================================
# 5. Pre-register exact 17 fault conditions
#
# These are taken from the already-frozen Stage24
# paper-domain condition set, before any Stage25 outcomes.
# ============================================================

faults = [
    {
        "name":
            "gyro_total_failure",

        "family":
            "modality_outage",

        "channels":
            GYRO,

        "stochastic":
            False,
    },

    {
        "name":
            "acc_total_failure",

        "family":
            "modality_outage",

        "channels":
            ACC,

        "stochastic":
            False,
    },

    {
        "name":
            "all_sensors_failure",

        "family":
            "modality_outage",

        "channels":
            ALL_CHANNELS,

        "stochastic":
            False,
    },

    {
        "name":
            "single_axis_failure_acc_x",

        "family":
            "single_axis_outage",

        "channels":
            [0],

        "stochastic":
            False,
    },

    {
        "name":
            "single_axis_failure_acc_y",

        "family":
            "single_axis_outage",

        "channels":
            [1],

        "stochastic":
            False,
    },

    {
        "name":
            "single_axis_failure_acc_z",

        "family":
            "single_axis_outage",

        "channels":
            [2],

        "stochastic":
            False,
    },

    {
        "name":
            "single_axis_failure_gyro_x",

        "family":
            "single_axis_outage",

        "channels":
            [3],

        "stochastic":
            False,
    },

    {
        "name":
            "single_axis_failure_gyro_y",

        "family":
            "single_axis_outage",

        "channels":
            [4],

        "stochastic":
            False,
    },

    {
        "name":
            "single_axis_failure_gyro_z",

        "family":
            "single_axis_outage",

        "channels":
            [5],

        "stochastic":
            False,
    },

    {
        "name":
            "acc_intermittent_30pct",

        "family":
            "intermittent_dropout",

        "channels":
            ACC,

        "stochastic":
            True,

        "drop_probability":
            0.30,
    },

    {
        "name":
            "gyro_intermittent_30pct",

        "family":
            "intermittent_dropout",

        "channels":
            GYRO,

        "stochastic":
            True,

        "drop_probability":
            0.30,
    },

    {
        "name":
            "acc_noise_sigma0.5",

        "family":
            "gaussian_noise",

        "channels":
            ACC,

        "stochastic":
            True,

        "sigma_normalized_units":
            0.5,
    },

    {
        "name":
            "gyro_noise_sigma0.5",

        "family":
            "gaussian_noise",

        "channels":
            GYRO,

        "stochastic":
            True,

        "sigma_normalized_units":
            0.5,
    },

    {
        "name":
            "acc_stuck_value",

        "family":
            "stuck_value",

        "channels":
            ACC,

        "stochastic":
            True,

        "tau_min_fraction":
            0.25,

        "tau_max_fraction":
            0.75,
    },

    {
        "name":
            "gyro_stuck_value",

        "family":
            "stuck_value",

        "channels":
            GYRO,

        "stochastic":
            True,

        "tau_min_fraction":
            0.25,

        "tau_max_fraction":
            0.75,
    },

    {
        "name":
            "acc_scale_drift_2.0x",

        "family":
            "scale_drift",

        "channels":
            ACC,

        "stochastic":
            False,

        "start_factor":
            1.0,

        "end_factor":
            2.0,
    },

    {
        "name":
            "gyro_scale_drift_2.0x",

        "family":
            "scale_drift",

        "channels":
            GYRO,

        "stochastic":
            False,

        "start_factor":
            1.0,

        "end_factor":
            2.0,
    },
]


if len(
    faults
) != 17:

    raise RuntimeError(
        "Fault manifest must contain exactly 17 conditions"
    )


if len({
    x["name"]
    for x in faults
}) != 17:

    raise RuntimeError(
        "Duplicate fault condition name"
    )


family_counts = Counter(
    x[
        "family"
    ]
    for x in faults
)


expected_family_counts = {
    "modality_outage": 3,
    "single_axis_outage": 6,
    "intermittent_dropout": 2,
    "gaussian_noise": 2,
    "stuck_value": 2,
    "scale_drift": 2,
}


if family_counts != expected_family_counts:

    raise RuntimeError(
        f"Unexpected family counts: {family_counts}"
    )


print(
    "FAULT_CONDITION_MANIFEST_PASS_17=True"
)


# ============================================================
# 6. Pre-register the paired-domain experiment
#
# Baseline is evaluated once.
# Every fault is evaluated in BOTH domains.
#
#   1 + (17 × 2) = 35 condition-domain cases
# ============================================================

DOMAINS = [
    "pre_normalization_sensor_domain",
    "post_normalization_domain",
]


domain_rows = [
    {
        "pair_condition":
            "baseline",

        "domain":
            "shared_clean",

        "family":
            "baseline",

        "commutation_class":
            "identity",

        "channels":
            "",

        "stochastic":
            False,
    }
]


COMMUTING_FAMILIES = {
    "gaussian_noise",
    "stuck_value",
}


NONCOMMUTING_FAMILIES = {
    "modality_outage",
    "single_axis_outage",
    "intermittent_dropout",
    "scale_drift",
}


for fault in faults:

    family = fault[
        "family"
    ]


    if family in COMMUTING_FAMILIES:

        commutation_class = (
            "expected_affine_commuting_control"
        )

    elif family in NONCOMMUTING_FAMILIES:

        commutation_class = (
            "expected_noncommuting"
        )

    else:

        raise RuntimeError(
            f"Unclassified family: {family}"
        )


    for domain in DOMAINS:

        domain_rows.append({
            "pair_condition":
                fault[
                    "name"
                ],

            "domain":
                domain,

            "family":
                family,

            "commutation_class":
                commutation_class,

            "channels":
                ",".join(
                    str(x)
                    for x in fault[
                        "channels"
                    ]
                ),

            "stochastic":
                fault[
                    "stochastic"
                ],
        })


if len(
    domain_rows
) != 35:

    raise RuntimeError(
        f"Expected 35 paired-domain cases, "
        f"got {len(domain_rows)}"
    )


with (
    OUT
    / "condition_domain_manifest_35.csv"
).open(
    "w",
    newline="",
    encoding="utf-8",
) as f:

    fields = [
        "pair_condition",
        "domain",
        "family",
        "commutation_class",
        "channels",
        "stochastic",
    ]

    writer = csv.DictWriter(
        f,
        fieldnames=fields,
    )

    writer.writeheader()

    writer.writerows(
        domain_rows
    )


print(
    "PAIRED_DOMAIN_MANIFEST_PASS_35=True"
)


# ============================================================
# 7. Freeze stochastic seed contract
#
# One stochastic realization per dataset/condition.
# The SAME realization must be used for physical and
# post-normalization domains, and for every model/seed.
# ============================================================

seed_rows = []


for dataset in DATASETS:

    for fault in faults:

        if not fault[
            "stochastic"
        ]:

            continue


        seed = deterministic_fault_seed(
            dataset,
            fault[
                "name"
            ],
        )


        seed_rows.append({
            "dataset":
                dataset,

            "condition":
                fault[
                    "name"
                ],

            "family":
                fault[
                    "family"
                ],

            "numpy_rng":
                "numpy.random.RandomState",

            "seed":
                seed,

            "shared_between_domains":
                True,

            "shared_across_models":
                True,

            "shared_across_model_seeds":
                True,
        })


# 6 stochastic conditions × 4 datasets
if len(
    seed_rows
) != 24:

    raise RuntimeError(
        f"Expected 24 stochastic seed bindings, "
        f"got {len(seed_rows)}"
    )


with (
    OUT
    / "stochastic_fault_seed_manifest_24.csv"
).open(
    "w",
    newline="",
    encoding="utf-8",
) as f:

    fields = [
        "dataset",
        "condition",
        "family",
        "numpy_rng",
        "seed",
        "shared_between_domains",
        "shared_across_models",
        "shared_across_model_seeds",
    ]

    writer = csv.DictWriter(
        f,
        fieldnames=fields,
    )

    writer.writeheader()

    writer.writerows(
        seed_rows
    )


print(
    "STOCHASTIC_SEED_MANIFEST_PASS_24=True"
)


# ============================================================
# 8. Exact transformation contract
# ============================================================

transform_contract = {
    "clean_normalization": (
        "N(x) = (x - train_mean) / train_std"
    ),

    "domains": {
        "pre_normalization_sensor_domain": {
            "ordering":
                "fault(x) first, then frozen N(.)",

            "interpretation":
                (
                    "sensor-domain model-window fault; "
                    "not necessarily untouched ADC acquisition"
                ),
        },

        "post_normalization_domain": {
            "ordering":
                "frozen N(x) first, then syntactic fault",

            "interpretation":
                (
                    "standardized-feature-space corruption "
                    "used as methodological contrast"
                ),
        },
    },

    "modality_outage_and_single_axis_outage": {
        "pre_normalization":
            "selected raw/model-window channels := 0.0, then N(.)",

        "post_normalization":
            "selected normalized channels := 0.0",

        "commutes_with_affine_normalization":
            False,

        "reason":
            (
                "N(0) = -mean/std, which is generally not zero"
            ),
    },

    "intermittent_dropout": {
        "mask":
            (
                "Bernoulli temporal mask with p=0.30, "
                "shape [N_test,T], shared across selected "
                "modality channels"
            ),

        "pre_normalization":
            (
                "masked selected raw/model-window values := 0.0, "
                "then N(.)"
            ),

        "post_normalization":
            (
                "masked selected normalized values := 0.0"
            ),

        "commutes_with_affine_normalization":
            False,
    },

    "gaussian_noise": {
        "epsilon":
            (
                "same standard-normal epsilon tensor in both domains"
            ),

        "pre_normalization":
            (
                "selected raw channel += "
                "0.5 * train_std[channel] * epsilon, then N(.)"
            ),

        "post_normalization":
            (
                "selected normalized channel += 0.5 * epsilon"
            ),

        "commutes_with_affine_normalization":
            True,

        "required_tensor_equivalence_tolerance":
            1e-6,
    },

    "stuck_value": {
        "tau":
            (
                "per-window tau sampled uniformly as integer "
                "randint(T//4, 3*T//4)"
            ),

        "operation":
            (
                "from tau onward repeat value at tau "
                "for selected channels"
            ),

        "same_tau_between_domains":
            True,

        "commutes_with_affine_normalization":
            True,

        "required_tensor_equivalence_tolerance":
            1e-6,
    },

    "scale_drift": {
        "factor":
            (
                "linear factor from 1.0 at first timestep "
                "to 2.0 at final timestep"
            ),

        "pre_normalization":
            "selected raw values *= factor, then N(.)",

        "post_normalization":
            "selected normalized values *= factor",

        "commutes_with_affine_normalization":
            False,

        "algebraic_difference":
            (
                "N(a*x) - a*N(x) = (a-1)*mean/std"
            ),
    },
}


write_json(
    OUT
    / "transform_contract.json",
    transform_contract,
)


# ============================================================
# 9. Mathematical commutation controls
# ============================================================

commutation_contract = {
    "purpose": (
        "Use mathematically commuting fault operators as "
        "negative controls for the domain-effect experiment."
    ),

    "expected_equal_between_domains": [
        "baseline",
        "acc_noise_sigma0.5",
        "gyro_noise_sigma0.5",
        "acc_stuck_value",
        "gyro_stuck_value",
    ],

    "expected_noncommuting": [
        x[
            "name"
        ]
        for x in faults
        if x[
            "family"
        ]
        in NONCOMMUTING_FAMILIES
    ],

    "pre_inference_gate": (
        "For every dataset, paired transformed tensors for "
        "baseline/Gaussian-noise/stuck controls must match "
        "between domains to max absolute error <= 1e-6 "
        "before model inference is accepted."
    ),

    "scientific_interpretation": (
        "If commuting controls differ materially between domains, "
        "the evaluator is incorrect rather than the models."
    ),
}


write_json(
    OUT
    / "commutation_control_contract.json",
    commutation_contract,
)


print(
    "COMMUTATION_CONTROL_PROTOCOL_FROZEN=True"
)


# ============================================================
# 10. Aggregation contract
# ============================================================

aggregation_contract = {
    "case_level_metrics": [
        "accuracy",
        "macro_f1",
    ],

    "baseline":
        "one clean case per dataset/model/seed",

    "domain_specific_all_fault": (
        "equal condition weight across all 17 faults"
    ),

    "domain_specific_recoverable_fault": (
        "equal condition weight across 16 faults, "
        "excluding all_sensors_failure"
    ),

    "family_balanced": (
        "first average conditions within each of six families, "
        "then give each family equal weight"
    ),

    "families": [
        "modality_outage",
        "single_axis_outage",
        "intermittent_dropout",
        "gaussian_noise",
        "stuck_value",
        "scale_drift",
    ],

    "commuting_control_aggregate": [
        "gaussian_noise",
        "stuck_value",
    ],

    "noncommuting_aggregate": [
        "modality_outage",
        "single_axis_outage",
        "intermittent_dropout",
        "scale_drift",
    ],

    "domain_delta_definition": (
        "pre_normalization_sensor_domain "
        "minus post_normalization_domain"
    ),

    "cross_dataset_aggregation": (
        "equal dataset weight; never pool samples across datasets"
    ),

    "seed_aggregation": (
        "average the five frozen model-training seeds within "
        "each dataset/model before equal-dataset aggregation"
    ),

    "relative_reliability":
        "secondary only",

    "primary_absolute_metrics": [
        "clean_accuracy",
        "clean_macro_f1",
        "all_fault_accuracy",
        "all_fault_macro_f1",
        "recoverable_fault_accuracy",
        "recoverable_fault_macro_f1",
        "family_balanced_accuracy",
        "family_balanced_macro_f1",
    ],
}


write_json(
    OUT
    / "aggregation_contract.json",
    aggregation_contract,
)


# ============================================================
# 11. V25 claim/analysis strata
# ============================================================

v25_analysis_contract = {
    "development": {
        "datasets": {
            "UCI_HAR": [
                42,
                123,
                456,
            ],

            "DSADS": [
                42,
                123,
                456,
            ],
        },

        "n_checkpoints":
            6,

        "claim_role":
            "development_secondary",
    },

    "selection_held_out": {
        "datasets": {
            "UCI_HAR": [
                789,
                2026,
            ],

            "DSADS": [
                789,
                2026,
            ],

            "PAMAP2":
                SEEDS,

            "MotionSense":
                SEEDS,
        },

        "n_checkpoints":
            14,

        "claim_role":
            "primary_for_v25_generalization",
    },

    "all_20": {
        "n_checkpoints":
            20,

        "claim_role":
            "descriptive_full_summary",

        "independent_confirmation_claim_allowed":
            False,
    },

    "no_external_test_driven_tuning":
        True,

    "stage24_or_storm_outcomes_may_not_trigger_v25_retraining":
        True,
}


write_json(
    OUT
    / "v25_analysis_strata_contract.json",
    v25_analysis_contract,
)


# ============================================================
# 12. Clean-baseline gate
#
# Must pass BEFORE any corrupted score is accepted.
# Reference extraction itself may be performed in the next
# read-only harness stage, but the rule is frozen here.
# ============================================================

clean_gate = {
    "required_cases":
        200,

    "required_result":
        "PASS_200_OF_200",

    "rule": (
        "Every newly loaded frozen checkpoint must reproduce "
        "its canonical frozen clean test accuracy and macro-F1 "
        "before fault inference results are accepted."
    ),

    "reference_sources": {
        "V3R1":
            (
                "canonical frozen V3R1 clean-result receipts/"
                "analysis tied to the same checkpoint SHA"
            ),

        "V25_FINAL_R2":
            (
                "canonical frozen V25 final R2 clean-result "
                "receipts tied to the same checkpoint SHA"
            ),
    },

    "metric_computation":
        (
            "reuse canonical project accuracy/macro-F1 "
            "definition; do not substitute a new label convention"
        ),

    "failure_policy": (
        "if any clean case fails, abort before accepting "
        "any corrupted result; classify harness/provenance "
        "before modifying evaluator"
    ),

    "tolerance_policy": (
        "do not weaken tolerance after observing a failure; "
        "first reconcile predictions, label mapping, loader, "
        "checkpoint and metric implementation"
    ),
}


write_json(
    OUT
    / "clean_baseline_gate_contract.json",
    clean_gate,
)


print(
    "CLEAN_BASELINE_GATE_PREREGISTERED_200_OF_200=True"
)


# ============================================================
# 13. Historical V2 separation
# ============================================================

historical_bridge = {
    "V3R1_reliability_v2":
        (
            "frozen historical normalized-space 33-condition suite"
        ),

    "Stage25_post_normalization":
        (
            "new 17-condition paired-domain contrast using "
            "the exact same semantic conditions as Stage25 "
            "pre-normalization evaluation"
        ),

    "merged":
        False,

    "reason": (
        "Stage25 must isolate fault domain while holding condition "
        "semantics fixed; historical V2 remains separate evidence."
    ),

    "historical_V2_rerun_required":
        False,

    "historical_V2_results_modified":
        False,
}


write_json(
    OUT
    / "historical_v2_bridge_contract.json",
    historical_bridge,
)


# ============================================================
# 14. Pre-register primary research questions
# ============================================================

analysis_plan = {
    "RQ1": (
        "How much does moving identical sensor-failure semantics "
        "from post-normalization space to the pre-normalization "
        "sensor-domain model-window representation change "
        "absolute HAR robustness?"
    ),

    "RQ2": (
        "Do model rankings change between the two fault domains?"
    ),

    "RQ3": (
        "Are domain effects concentrated in mathematically "
        "noncommuting fault operators?"
    ),

    "RQ4": (
        "Do commuting controls (Gaussian noise and stuck-value) "
        "produce equivalent transformed tensors and model outcomes "
        "across domains as predicted algebraically?"
    ),

    "RQ5": (
        "Under the physically meaningful pre-normalization "
        "protocol, where does V25 lie on the clean-performance, "
        "absolute-robustness, parameter-count and efficiency "
        "tradeoff relative to all nine frozen V3R1 baselines?"
    ),

    "anti_cherrypicking": {
        "all_10_models_reported":
            True,

        "all_6_families_reported":
            True,

        "both_accuracy_and_macro_f1_reported":
            True,

        "negative_results_preserved":
            True,

        "no_severity_change_after_outcomes":
            True,

        "no_condition_deletion_after_outcomes":
            True,

        "no_model_retraining":
            True,
    },
}


write_json(
    OUT
    / "analysis_plan_preregistered.json",
    analysis_plan,
)


# ============================================================
# 15. Expected evaluation cardinalities
# ============================================================

expected = {
    "datasets":
        4,

    "models":
        10,

    "training_seeds_per_dataset_model":
        5,

    "frozen_checkpoints":
        200,

    "fault_conditions":
        17,

    "domains_per_fault":
        2,

    "baseline_cases_per_checkpoint":
        1,

    "condition_domain_cases_per_checkpoint":
        35,

    "expected_model_condition_case_rows":
        7000,

    "expected_dataset_condition_tensors": (
        4 * 35
    ),

    "expected_dataset_condition_tensors_value":
        140,

    "stochastic_dataset_condition_bindings":
        24,
}


if (
    expected[
        "expected_model_condition_case_rows"
    ]
    !=
    200
    *
    35
):

    raise RuntimeError(
        "Expected-case arithmetic failed"
    )


print(
    "EXPECTED_STAGE25_CASE_ROWS=7000"
)

print(
    "EXPECTED_DATASET_CONDITION_TENSORS=140"
)


# ============================================================
# 16. Freeze full scientific protocol
# ============================================================

protocol = {
    "protocol":
        "STAGE25_PHYSICAL_FAULT_PROTOCOL_R3",

    "status":
        "FROZEN_BEFORE_CORRUPTED_INFERENCE",

    "scientific_scope": (
        "cross-dataset paired-domain IMU sensor-failure "
        "robustness evaluation"
    ),

    "datasets":
        DATASETS,

    "input_shape":
        [
            128,
            6,
        ],

    "channels":
        CHANNELS,

    "model_bank":
        {
            "total":
                200,

            "V3R1":
                180,

            "V25_FINAL_R2":
                20,
        },

    "domains":
        DOMAINS,

    "baseline_shared":
        True,

    "fault_conditions":
        faults,

    "fault_condition_count":
        17,

    "condition_domain_count_per_checkpoint":
        35,

    "expected_case_rows":
        7000,

    "fault_root_seed":
        42,

    "fault_rng":
        "numpy.random.RandomState",

    "stochastic_realization_policy": (
        "one fixed realization per dataset/condition, "
        "shared across domains, architectures and model seeds"
    ),

    "fault_source_provenance": (
        "same six-family/17-fault semantic set already frozen "
        "in Stage24 before Stage25 outcomes"
    ),

    "stage24_closure_sha256":
        STAGE24_CLOSURE_SHA,

    "stage25_r2_sha256sums_sha256":
        R2_SHA256SUMS_SHA,

    "commutation_controls": {
        "commuting": [
            "gaussian_noise",
            "stuck_value",
        ],

        "noncommuting": [
            "modality_outage",
            "single_axis_outage",
            "intermittent_dropout",
            "scale_drift",
        ],
    },

    "aggregation":
        aggregation_contract,

    "clean_gate":
        clean_gate,

    "historical_v2_separation":
        historical_bridge,

    "training_allowed":
        False,

    "checkpoint_modification_allowed":
        False,

    "severity_tuning_after_outcomes_allowed":
        False,

    "condition_selection_after_outcomes_allowed":
        False,

    "model_selection_after_outcomes_allowed":
        False,

    "stage25_fault_protocol_frozen":
        True,
}


write_json(
    OUT
    / "stage25_physical_fault_protocol_r3.json",
    protocol,
)


# ============================================================
# 17. Receipt
# ============================================================

receipt = {
    "audit":
        "STAGE25_PROTOCOL_PREREGISTRATION_R3",

    "status":
        "PASS",

    "protocol_frozen_before_corrupted_inference":
        True,

    "model_bank_frozen":
        "PASS_200_OF_200",

    "v3r1_model_bank":
        "PASS_180_OF_180",

    "v25_final_model_bank":
        "PASS_20_OF_20",

    "v25_development":
        6,

    "v25_selection_held_out":
        14,

    "fault_conditions":
        17,

    "paired_domains":
        2,

    "condition_domain_cases_per_checkpoint":
        35,

    "expected_case_rows":
        7000,

    "stochastic_seed_bindings":
        24,

    "clean_baseline_gate":
        "PREREGISTERED_PASS_200_OF_200_REQUIRED",

    "commutation_control_gate":
        "PREREGISTERED",

    "historical_v2_results_merged":
        False,

    "corrupted_inference_performed":
        False,

    "clean_model_inference_performed":
        False,

    "model_deserialization_performed":
        False,

    "training_performed":
        False,

    "checkpoints_modified":
        False,

    "dataset_arrays_modified":
        False,

    "v3r1_results_modified":
        False,

    "v25_results_modified":
        False,

    "scientific_classification": (
        "PAIRED_DOMAIN_PROTOCOL_FROZEN_BEFORE_OUTCOMES"
    ),

    "next_gate": (
        "Read-only clean-reference provenance resolution, "
        "model-loader audit, transform-only commutation preflight, "
        "then clean baseline reproduction before corrupted inference."
    ),
}


write_json(
    OUT
    / "stage25_protocol_preregistration_receipt_r3.json",
    receipt,
)


print()
print(
    "=" * 110
)

print(
    "STAGE25 R3 FINAL RECEIPT"
)

print(
    "=" * 110
)

print(
    json.dumps(
        receipt,
        indent=2,
    )
)


print()
print(
    "STAGE25_PROTOCOL_R3_PREREGISTRATION_PASS=True"
)

print(
    "PROTOCOL_FROZEN_BEFORE_CORRUPTED_INFERENCE=True"
)

print(
    "FROZEN_MODEL_BANK_PASS_200_OF_200=True"
)

print(
    "FAULT_CONDITION_MANIFEST_PASS_17=True"
)

print(
    "PAIRED_DOMAIN_MANIFEST_PASS_35=True"
)

print(
    "STOCHASTIC_SEED_MANIFEST_PASS_24=True"
)

print(
    "COMMUTATION_CONTROL_PROTOCOL_FROZEN=True"
)

print(
    "CLEAN_BASELINE_GATE_PREREGISTERED_200_OF_200=True"
)

print(
    "EXPECTED_STAGE25_CASE_ROWS=7000"
)

print(
    "CORRUPTED_INFERENCE_PERFORMED=False"
)

print(
    "CLEAN_MODEL_INFERENCE_PERFORMED=False"
)

print(
    "MODEL_DESERIALIZATION_PERFORMED=False"
)

print(
    "TRAINING_PERFORMED=False"
)

print(
    "CHECKPOINTS_MODIFIED=False"
)

print(
    "DATASET_ARRAYS_MODIFIED=False"
)
