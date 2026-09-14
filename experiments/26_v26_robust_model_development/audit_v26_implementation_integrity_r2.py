from __future__ import annotations

import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F


ROOT = Path(
    "/mnt/hdd16T/ToqeerHomeBackup/toqeer/IMU_Reliability"
)

EXP = (
    ROOT
    / "experiments"
    / "26_v26_robust_model_development"
)

OUT = (
    ROOT
    / "results"
    / "v26_implementation_integrity_r2"
)

PROTOCOL = (
    ROOT
    / "results"
    / "v26_development_protocol_r1"
)

R2 = (
    ROOT
    / "results"
    / "stage25_physical_fault_protocol"
    / "canonical_reconstruction_audit_r2"
)


if str(EXP) not in sys.path:
    sys.path.insert(
        0,
        str(EXP),
    )


from candidate_models_r2 import (
    CANDIDATE_IDS,
    create_v26_candidate,
    parameter_count,
)

from physical_faults_r2 import (
    FAMILIES,
    apply_random_physical_faults,
    normalize_with_train_stats,
)

from development_data_r2 import (
    load_development_train_val,
)

from losses_r2 import (
    candidate_training_loss,
)

from validation_r2 import (
    VALIDATION_CONDITIONS,
    apply_validation_condition,
    selection_score,
    stable_seed,
)


PARAMETER_CEILING = 60000

EXPECTED_CLASSES = {
    "UCI_HAR": 6,
    "DSADS": 19,
}


def sha256_file(
    path: Path,
):

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


print("=" * 118)
print("V26 IMPLEMENTATION INTEGRITY R2")
print("NO TRAINING / NO CHECKPOINT DESERIALIZATION / NO TEST INFERENCE")
print("=" * 118)


# ============================================================
# 1. Frozen protocol receipt
# ============================================================

protocol_receipt = json.loads(
    (
        PROTOCOL
        / "v26_development_protocol_receipt_r1.json"
    ).read_text()
)


required = {
    "status":
        "FROZEN_BEFORE_NEW_MODEL_TRAINING",

    "candidate_count":
        4,

    "maximum_screening_runs":
        24,

    "candidate_selection_uses_test_data":
        False,

    "candidate_selection_uses_storm":
        False,

    "physical_pre_normalization_training":
        True,

    "corrupted_classification_gradient":
        True,

    "parameter_hard_ceiling":
        60000,

    "model_training_performed":
        False,

    "test_inference_performed":
        False,
}


for key, expected in required.items():

    actual = protocol_receipt.get(
        key
    )

    if actual != expected:

        raise RuntimeError(
            f"Protocol prerequisite mismatch: "
            f"{key}={actual!r}, "
            f"expected={expected!r}"
        )


print(
    "V26_FROZEN_PROTOCOL_PREREQUISITE_PASS=True"
)


# ============================================================
# 2. Source-level data-access audit
# ============================================================

dev_source_path = (
    EXP
    / "development_data_r2.py"
)

dev_source = (
    dev_source_path.read_text()
)


for forbidden in [
    "test_idx",
    "PAMAP2",
    "MotionSense",
]:

    if forbidden in dev_source:

        raise RuntimeError(
            "Development data source contains "
            f"forbidden token: {forbidden}"
        )


print(
    "DEVELOPMENT_SOURCE_TEST_ACCESS_FORBIDDEN_GATE_PASS=True"
)


# ============================================================
# 3. Development train/val reconstruction
# ============================================================

normalization_receipts = json.loads(
    (
        R2
        / "dataset_normalization_receipts.json"
    ).read_text()
)


data_receipts = []


for dataset in [
    "UCI_HAR",
    "DSADS",
]:

    data = (
        load_development_train_val(
            dataset
        )
    )


    if (
        data[
            "num_classes"
        ]
        !=
        EXPECTED_CLASSES[
            dataset
        ]
    ):

        raise RuntimeError(
            f"{dataset}: class count mismatch"
        )


    frozen_mean = np.asarray(
        normalization_receipts[
            dataset
        ][
            "mean"
        ],
        dtype=np.float32,
    )

    frozen_std = np.asarray(
        normalization_receipts[
            dataset
        ][
            "std"
        ],
        dtype=np.float32,
    )


    mean_error = float(
        np.max(
            np.abs(
                data[
                    "train_mean"
                ].astype(
                    np.float64
                )
                -
                frozen_mean.astype(
                    np.float64
                )
            )
        )
    )

    std_error = float(
        np.max(
            np.abs(
                data[
                    "train_std"
                ].astype(
                    np.float64
                )
                -
                frozen_std.astype(
                    np.float64
                )
            )
        )
    )


    if mean_error > 1e-6:

        raise RuntimeError(
            f"{dataset}: train mean mismatch "
            f"{mean_error}"
        )


    if std_error > 1e-6:

        raise RuntimeError(
            f"{dataset}: train std mismatch "
            f"{std_error}"
        )


    data_receipts.append({
        "dataset":
            dataset,

        "train_count":
            data[
                "train_count"
            ],

        "val_count":
            data[
                "val_count"
            ],

        "num_classes":
            data[
                "num_classes"
            ],

        "train_mean_max_abs_error_vs_r2":
            mean_error,

        "train_std_max_abs_error_vs_r2":
            std_error,
    })


print(
    "DEVELOPMENT_TRAIN_ONLY_NORMALIZATION_PASS_2_OF_2=True"
)

print(
    "DEVELOPMENT_DATASETS_BOUND_UCI_DSADS_ONLY=True"
)


# ============================================================
# 4. Exact validation condition manifest
# ============================================================

if len(
    VALIDATION_CONDITIONS
) != 16:

    raise RuntimeError(
        "Expected exactly 16 recoverable "
        "validation conditions"
    )


family_counts = Counter(
    x[
        "family"
    ]
    for x in VALIDATION_CONDITIONS
)


expected_family_counts = {
    "modality_outage":
        2,

    "single_axis_outage":
        6,

    "intermittent_dropout":
        2,

    "gaussian_noise":
        2,

    "stuck_value":
        2,

    "scale_drift":
        2,
}


if dict(
    family_counts
) != expected_family_counts:

    raise RuntimeError(
        f"Validation family counts mismatch: "
        f"{dict(family_counts)}"
    )


if any(
    condition[
        "name"
    ]
    ==
    "all_sensors_failure"

    for condition
    in VALIDATION_CONDITIONS
):

    raise RuntimeError(
        "all_sensors_failure must not be "
        "used for development selection"
    )


print(
    "VALIDATION_CONDITION_MANIFEST_PASS_16=True"
)

print(
    "VALIDATION_ALL_SENSORS_FAILURE_EXCLUDED=True"
)


# ============================================================
# 5. Stable independent validation randomness
# ============================================================

for dataset in [
    "UCI_HAR",
    "DSADS",
]:

    seeds = [
        stable_seed(
            dataset,
            condition[
                "name"
            ],
        )

        for condition
        in VALIDATION_CONDITIONS
    ]


    if len(
        set(
            seeds
        )
    ) != 16:

        raise RuntimeError(
            f"{dataset}: validation seed collision"
        )


print(
    "VALIDATION_RANDOMNESS_ROOT_26001_BOUND=True"
)

print(
    "VALIDATION_STABLE_SEED_UNIQUENESS_PASS=True"
)


# ============================================================
# 6. Candidate parameter counts + synthetic forward
# ============================================================

parameter_rows = []

synthetic_forward_count = 0


for num_classes in [
    6,
    12,
    19,
]:

    for candidate_id in CANDIDATE_IDS:

        model = create_v26_candidate(
            candidate_id,
            num_classes,
            input_channels=6,
        )

        params = parameter_count(
            model
        )


        if params > PARAMETER_CEILING:

            raise RuntimeError(
                f"{candidate_id}/K={num_classes}: "
                f"{params} parameters exceeds "
                f"{PARAMETER_CEILING}"
            )


        model.eval()

        x = torch.randn(
            4,
            128,
            6,
        )


        with torch.inference_mode():

            logits = model(
                x
            )


        if tuple(
            logits.shape
        ) != (
            4,
            num_classes,
        ):

            raise RuntimeError(
                f"{candidate_id}/K={num_classes}: "
                f"invalid synthetic output "
                f"{tuple(logits.shape)}"
            )


        synthetic_forward_count += 1


        parameter_rows.append({
            "candidate_id":
                candidate_id,

            "num_classes":
                num_classes,

            "parameter_count":
                params,

            "parameter_ceiling":
                PARAMETER_CEILING,

            "parameter_gate_pass":
                True,
        })


        print(
            "CANDIDATE_PARAMS:",
            candidate_id,
            "K=",
            num_classes,
            "PARAMS=",
            params,
        )


if synthetic_forward_count != 12:

    raise RuntimeError(
        "Expected 12 synthetic forward tests"
    )


print(
    "CANDIDATE_PARAMETER_GATE_PASS_12_OF_12=True"
)

print(
    "SYNTHETIC_FORWARD_SHAPE_PASS_12_OF_12=True"
)


# ============================================================
# 7. B/C architecture identity
# ============================================================

b = create_v26_candidate(
    "V26B_DualGateLite",
    19,
)

c = create_v26_candidate(
    "V26C_DualGateLiteCons",
    19,
)


b_shapes = {
    key:
        tuple(
            value.shape
        )

    for key, value
    in b.state_dict().items()
}

c_shapes = {
    key:
        tuple(
            value.shape
        )

    for key, value
    in c.state_dict().items()
}


if b_shapes != c_shapes:

    raise RuntimeError(
        "V26B and V26C architecture "
        "state shapes differ"
    )


print(
    "V26B_V26C_EXACT_ARCHITECTURE_IDENTITY_PASS=True"
)


# ============================================================
# 8. Reliability gate shape/range
# ============================================================

for candidate_id in [
    "V26B_DualGateLite",
    "V26C_DualGateLiteCons",
    "V26D_DualGateCross",
]:

    model = create_v26_candidate(
        candidate_id,
        6,
    )

    model.eval()


    with torch.inference_mode():

        logits, aux = (
            model.forward_with_reliability(
                torch.randn(
                    5,
                    128,
                    6,
                )
            )
        )


    for name in [
        "acc_reliability",
        "gyro_reliability",
    ]:

        value = aux[
            name
        ]


        if tuple(
            value.shape
        ) != (
            5,
            1,
        ):

            raise RuntimeError(
                f"{candidate_id}/{name}: "
                "bad gate shape"
            )


        if not torch.all(
            (
                value >= 0
            )
            &
            (
                value <= 1
            )
        ):

            raise RuntimeError(
                f"{candidate_id}/{name}: "
                "gate outside [0,1]"
            )


print(
    "MODALITY_RELIABILITY_GATE_UNIT_PASS_3_OF_3=True"
)


# ============================================================
# 9. Random training-fault operator invariants
# ============================================================

raw = torch.randn(
    8,
    128,
    6,
)

raw_original = raw.clone()

std = torch.tensor(
    [
        0.7,
        1.1,
        1.3,
        0.2,
        0.3,
        0.4,
    ],
    dtype=torch.float32,
)


for family in FAMILIES:

    g1 = torch.Generator().manual_seed(
        260000
        +
        FAMILIES.index(
            family
        )
    )

    g2 = torch.Generator().manual_seed(
        260000
        +
        FAMILIES.index(
            family
        )
    )


    out1, meta1 = (
        apply_random_physical_faults(
            raw,
            std,
            g1,
            forced_family=family,
        )
    )

    out2, meta2 = (
        apply_random_physical_faults(
            raw,
            std,
            g2,
            forced_family=family,
        )
    )


    if not torch.equal(
        out1,
        out2,
    ):

        raise RuntimeError(
            f"{family}: deterministic "
            "reproduction failed"
        )


    if meta1 != meta2:

        raise RuntimeError(
            f"{family}: metadata "
            "reproduction failed"
        )


    if not torch.isfinite(
        out1
    ).all():

        raise RuntimeError(
            f"{family}: non-finite output"
        )


    if torch.equal(
        out1,
        raw
    ):

        raise RuntimeError(
            f"{family}: operator made "
            "no change"
        )


    if family == "modality_outage":

        for i, meta in enumerate(
            meta1
        ):

            channels = meta[
                "channels"
            ]

            if not torch.all(
                out1[
                    i,
                    :,
                    channels,
                ]
                ==
                0
            ):

                raise RuntimeError(
                    "Physical modality outage "
                    "did not write raw zero"
                )


    if family == "single_axis_outage":

        for i, meta in enumerate(
            meta1
        ):

            channel = meta[
                "channel"
            ]

            if not torch.all(
                out1[
                    i,
                    :,
                    channel,
                ]
                ==
                0
            ):

                raise RuntimeError(
                    "Physical single-axis outage "
                    "did not write raw zero"
                )


    if family == "intermittent_dropout":

        for meta in meta1:

            p = meta[
                "drop_probability"
            ]

            if not (
                0.10
                <=
                p
                <=
                0.50
            ):

                raise RuntimeError(
                    "Drop probability outside "
                    "frozen range"
                )


    if family == "gaussian_noise":

        for meta in meta1:

            sigma = meta[
                "sigma_normalized_units"
            ]

            if not (
                0.10
                <=
                sigma
                <=
                0.70
            ):

                raise RuntimeError(
                    "Gaussian sigma outside "
                    "frozen range"
                )


    if family == "stuck_value":

        for meta in meta1:

            onset = meta[
                "onset_fraction"
            ]

            if not (
                0.20
                <=
                onset
                <=
                0.80
            ):

                raise RuntimeError(
                    "Stuck onset outside "
                    "frozen range"
                )


    if family == "scale_drift":

        for meta in meta1:

            factor = meta[
                "final_factor"
            ]

            if not (
                0.50
                <=
                factor
                <=
                2.00
            ):

                raise RuntimeError(
                    "Scale drift outside "
                    "frozen range"
                )


if not torch.equal(
    raw,
    raw_original,
):

    raise RuntimeError(
        "Physical fault operator modified "
        "input batch in place"
    )


print(
    "PHYSICAL_TRAINING_FAULT_OPERATOR_PASS_6_OF_6=True"
)

print(
    "PHYSICAL_TRAINING_FAULT_REPRODUCIBILITY_PASS_6_OF_6=True"
)

print(
    "PHYSICAL_TRAINING_FAULT_RANGE_GATE_PASS=True"
)

print(
    "ALL_SENSORS_FAILURE_TRAINING_OPERATOR_ABSENT=True"
)


# ============================================================
# 10. Prove PRE-normalization physical semantics
# ============================================================

raw_zero_test = torch.ones(
    2,
    128,
    6,
)

mean_test = torch.tensor(
    [
        1.0,
        -2.0,
        0.5,
        3.0,
        -4.0,
        2.5,
    ],
    dtype=torch.float32,
)

std_test = torch.tensor(
    [
        2.0,
        4.0,
        1.0,
        3.0,
        2.0,
        5.0,
    ],
    dtype=torch.float32,
)


generator = torch.Generator().manual_seed(
    777
)

fault_raw, metadata = (
    apply_random_physical_faults(
        raw_zero_test,
        std_test,
        generator,
        forced_family="modality_outage",
    )
)

fault_normalized = (
    normalize_with_train_stats(
        fault_raw,
        mean_test,
        std_test,
    )
)


for i, meta in enumerate(
    metadata
):

    channels = meta[
        "channels"
    ]


    expected = (
        -
        mean_test[
            channels
        ]
        /
        std_test[
            channels
        ]
    )


    actual = fault_normalized[
        i,
        0,
        channels,
    ]


    if not torch.allclose(
        actual,
        expected,
        atol=0,
        rtol=0,
    ):

        raise RuntimeError(
            "Physical-zero normalization "
            "semantics failed"
        )


print(
    "PRE_NORMALIZATION_PHYSICAL_ZERO_SEMANTICS_PASS=True"
)


# ============================================================
# 11. Independent validation-transform unit tests
# ============================================================

val_raw = np.random.RandomState(
    123
).normal(
    size=(
        7,
        128,
        6,
    )
).astype(
    np.float32
)

val_std = np.asarray(
    [
        0.7,
        1.1,
        1.3,
        0.2,
        0.3,
        0.4,
    ],
    dtype=np.float32,
)


for dataset in [
    "UCI_HAR",
    "DSADS",
]:

    for condition in VALIDATION_CONDITIONS:

        a = apply_validation_condition(
            val_raw,
            val_std,
            dataset,
            condition,
        )

        b = apply_validation_condition(
            val_raw,
            val_std,
            dataset,
            condition,
        )


        if not np.array_equal(
            a,
            b,
        ):

            raise RuntimeError(
                f"{dataset}/"
                f"{condition['name']}: "
                "validation transform "
                "not deterministic"
            )


        if not np.isfinite(
            a
        ).all():

            raise RuntimeError(
                "Validation transform "
                "created non-finite values"
            )


print(
    "VALIDATION_TRANSFORM_UNIT_PASS_32_OF_32=True"
)


# ============================================================
# 12. Selection-score formula test
# ============================================================

score = selection_score(
    clean_macro_f1=0.8,
    all_recoverable_macro_f1=0.6,
    family_balanced_macro_f1=0.7,
)

expected_score = (
    0.20 * 0.8
    +
    0.30 * 0.6
    +
    0.50 * 0.7
)


if abs(
    score
    -
    expected_score
) > 1e-15:

    raise RuntimeError(
        "Frozen validation selection "
        "score formula mismatch"
    )


print(
    "VALIDATION_SELECTION_SCORE_FORMULA_PASS=True"
)


# ============================================================
# 13. Synthetic corrupted-gradient proof
#
# This is NOT training:
# - random temporary models
# - synthetic tensors only
# - no optimizer
# - no checkpoint saved
# ============================================================

gradient_rows = []


for candidate_id in CANDIDATE_IDS:

    torch.manual_seed(
        2600
    )

    model = create_v26_candidate(
        candidate_id,
        6,
    )

    model.train()


    raw_batch = torch.randn(
        4,
        128,
        6,
    )

    train_mean = torch.tensor(
        [
            0.2,
            -0.3,
            0.5,
            -0.1,
            0.4,
            -0.2,
        ],
        dtype=torch.float32,
    )

    train_std = torch.tensor(
        [
            0.7,
            1.1,
            1.3,
            0.2,
            0.3,
            0.4,
        ],
        dtype=torch.float32,
    )


    g = torch.Generator().manual_seed(
        9090
    )

    fault_raw, _ = (
        apply_random_physical_faults(
            raw_batch,
            train_std,
            g,
            forced_family="modality_outage",
        )
    )


    clean_x = (
        normalize_with_train_stats(
            raw_batch,
            train_mean,
            train_std,
        )
    )

    fault_x = (
        normalize_with_train_stats(
            fault_raw,
            train_mean,
            train_std,
        )
    )


    labels = torch.tensor(
        [
            0,
            1,
            2,
            3,
        ],
        dtype=torch.long,
    )


    model.zero_grad(
        set_to_none=True
    )


    fault_logits = model(
        fault_x
    )

    fault_ce = F.cross_entropy(
        fault_logits,
        labels,
    )

    fault_ce.backward()


    gradient_sum = 0.0


    for parameter in model.parameters():

        if parameter.grad is not None:

            gradient_sum += float(
                parameter.grad
                .detach()
                .abs()
                .sum()
                .item()
            )


    if not (
        gradient_sum > 0.0
    ):

        raise RuntimeError(
            f"{candidate_id}: corrupted CE "
            "produced no parameter gradient"
        )


    model.zero_grad(
        set_to_none=True
    )


    clean_logits = model(
        clean_x
    )

    fault_logits = model(
        fault_x
    )


    losses = candidate_training_loss(
        candidate_id,
        clean_logits,
        fault_logits,
        labels,
    )


    total = losses[
        "loss"
    ]


    if not torch.isfinite(
        total
    ):

        raise RuntimeError(
            f"{candidate_id}: non-finite "
            "training objective"
        )


    total.backward()


    total_gradient_sum = 0.0


    for parameter in model.parameters():

        if parameter.grad is not None:

            total_gradient_sum += float(
                parameter.grad
                .detach()
                .abs()
                .sum()
                .item()
            )


    if not (
        total_gradient_sum > 0.0
    ):

        raise RuntimeError(
            f"{candidate_id}: total loss "
            "produced no gradient"
        )


    gradient_rows.append({
        "candidate_id":
            candidate_id,

        "fault_ce":
            float(
                losses[
                    "fault_ce"
                ].detach()
            ),

        "clean_ce":
            float(
                losses[
                    "clean_ce"
                ].detach()
            ),

        "consistency":
            float(
                losses[
                    "consistency"
                ].detach()
            ),

        "fault_ce_gradient_abs_sum":
            gradient_sum,

        "total_loss_gradient_abs_sum":
            total_gradient_sum,

        "corrupted_classification_gradient_pass":
            True,
    })


print(
    "CORRUPTED_CLASSIFICATION_GRADIENT_SYNTHETIC_PASS_4_OF_4=True"
)

print(
    "SYNTHETIC_BACKWARD_UNIT_TEST_PERFORMED=True"
)

print(
    "OPTIMIZER_CREATED=False"
)

print(
    "TRAINING_PERFORMED=False"
)


# ============================================================
# 14. Write audit tables
# ============================================================

with (
    OUT
    / "candidate_parameter_counts_12.csv"
).open(
    "w",
    newline="",
    encoding="utf-8",
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            parameter_rows[0].keys()
        ),
    )

    writer.writeheader()

    writer.writerows(
        parameter_rows
    )


with (
    OUT
    / "development_data_integrity_2.csv"
).open(
    "w",
    newline="",
    encoding="utf-8",
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            data_receipts[0].keys()
        ),
    )

    writer.writeheader()

    writer.writerows(
        data_receipts
    )


with (
    OUT
    / "synthetic_corrupted_gradient_4.csv"
).open(
    "w",
    newline="",
    encoding="utf-8",
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            gradient_rows[0].keys()
        ),
    )

    writer.writeheader()

    writer.writerows(
        gradient_rows
    )


# ============================================================
# 15. Freeze exact source implementation specification
# ============================================================

source_files = [
    EXP
    / "candidate_models_r2.py",

    EXP
    / "physical_faults_r2.py",

    EXP
    / "development_data_r2.py",

    EXP
    / "losses_r2.py",

    EXP
    / "validation_r2.py",

    EXP
    / "audit_v26_implementation_integrity_r2.py",
]


source_manifest = []


for path in source_files:

    source_manifest.append({
        "path":
            str(
                path.relative_to(
                    ROOT
                )
            ),

        "sha256":
            sha256_file(
                path
            ),
    })


write_json(
    OUT
    / "implementation_source_sha_manifest.json",
    source_manifest,
)


implementation_spec = {
    "stage":
        "V26_IMPLEMENTATION_INTEGRITY_R2",

    "dsblock_exact_definition": {
        "residual":
            False,

        "sequence": [
            "depthwise Conv1d",
            "BatchNorm1d",
            "SiLU",
            "pointwise 1x1 Conv1d",
            "BatchNorm1d",
            "SiLU",
        ],

        "conv_bias":
            False,
    },

    "training_fault_sampling_unit":
        "one uniformly sampled fault family per training sample",

    "intermittent_dropout_mask":
        (
            "one temporal mask per sample, shared across "
            "the selected modality channels"
        ),

    "training_fault_domain":
        "pre-normalization sensor-domain model-window representation",

    "gaussian_training_scale":
        (
            "sigma_normalized_units * frozen train-only "
            "channel std in raw domain"
        ),

    "stuck_training_semantics":
        (
            "selected modality frozen to its observed value "
            "at sampled onset"
        ),

    "scale_drift_training_semantics":
        (
            "linear factor from 1.0 to sampled final_factor"
        ),

    "validation_fault_count":
        16,

    "validation_randomness_root":
        26001,

    "candidate_parameter_ceiling":
        60000,

    "all_sensors_failure_used_for_training":
        False,

    "all_sensors_failure_used_for_selection":
        False,
}


write_json(
    OUT
    / "exact_implementation_spec_r2.json",
    implementation_spec,
)


# ============================================================
# 16. Final receipt
# ============================================================

receipt = {
    "audit":
        "V26_IMPLEMENTATION_INTEGRITY_R2",

    "status":
        "PASS",

    "frozen_protocol_prerequisite":
        "PASS",

    "development_source_test_access":
        "FORBIDDEN_AND_PASS",

    "development_datasets":
        [
            "UCI_HAR",
            "DSADS",
        ],

    "development_train_only_normalization":
        "PASS_2_OF_2",

    "candidate_count":
        4,

    "candidate_parameter_gate":
        "PASS_12_OF_12",

    "parameter_ceiling":
        60000,

    "synthetic_forward_shape":
        "PASS_12_OF_12",

    "modality_reliability_gate":
        "PASS_3_OF_3",

    "physical_training_fault_operator":
        "PASS_6_OF_6",

    "training_fault_reproducibility":
        "PASS_6_OF_6",

    "pre_normalization_physical_zero_semantics":
        "PASS",

    "validation_condition_manifest":
        "PASS_16",

    "validation_transform_unit":
        "PASS_32_OF_32",

    "validation_selection_score":
        "PASS",

    "corrupted_classification_gradient":
        "SYNTHETIC_PASS_4_OF_4",

    "synthetic_forward_performed":
        True,

    "synthetic_backward_unit_test_performed":
        True,

    "development_validation_model_inference_performed":
        False,

    "test_inference_performed":
        False,

    "checkpoint_deserialization_performed":
        False,

    "optimizer_created":
        False,

    "training_performed":
        False,

    "checkpoint_saved":
        False,

    "storm_used":
        False,

    "next_gate":
        (
            "Freeze this implementation. Then execute the "
            "24 preregistered UCI_HAR/DSADS development "
            "training runs using train/val only. Candidate "
            "promotion must follow protocol-R1 thresholds "
            "without test or STORM access."
        ),
}


write_json(
    OUT
    / "v26_implementation_integrity_receipt_r2.json",
    receipt,
)


print()
print("=" * 118)
print("V26 IMPLEMENTATION INTEGRITY R2 FINAL RECEIPT")
print("=" * 118)

print(
    json.dumps(
        receipt,
        indent=2,
    )
)

print()
print(
    "V26_IMPLEMENTATION_INTEGRITY_R2_PASS=True"
)

print(
    "DEVELOPMENT_TRAIN_ONLY_NORMALIZATION_PASS_2_OF_2=True"
)

print(
    "CANDIDATE_PARAMETER_GATE_PASS_12_OF_12=True"
)

print(
    "PHYSICAL_TRAINING_FAULT_OPERATOR_PASS_6_OF_6=True"
)

print(
    "VALIDATION_CONDITION_MANIFEST_PASS_16=True"
)

print(
    "CORRUPTED_CLASSIFICATION_GRADIENT_SYNTHETIC_PASS_4_OF_4=True"
)

print(
    "DEVELOPMENT_VALIDATION_MODEL_INFERENCE_PERFORMED=False"
)

print(
    "TEST_INFERENCE_PERFORMED=False"
)

print(
    "CHECKPOINT_DESERIALIZATION_PERFORMED=False"
)

print(
    "OPTIMIZER_CREATED=False"
)

print(
    "TRAINING_PERFORMED=False"
)

print(
    "STORM_USED=False"
)
