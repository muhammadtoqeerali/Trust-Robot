from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(
    "/mnt/hdd16T/ToqeerHomeBackup/toqeer/IMU_Reliability"
)

V26_R4 = (
    ROOT
    / "results/v26_primary_confirmation_protocol_r4"
)

V26_R5 = (
    ROOT
    / "results/v26_primary_confirmation_training_r5"
)

V26_IMPL = (
    ROOT
    / "results/v26_implementation_integrity_r2"
)

S25_R3 = (
    ROOT
    / "results/stage25_physical_fault_protocol"
    / "protocol_preregistration_r3"
)

S25_R4A = (
    ROOT
    / "results/stage25_physical_fault_protocol"
    / "transform_provenance_preflight_r4a"
)

S25_R5 = (
    ROOT
    / "results/stage25_physical_fault_protocol"
    / "paired_domain_evaluation_r5"
)

S25_R6 = (
    ROOT
    / "results/stage25_physical_fault_protocol"
    / "scientific_analysis_r6"
)

OUT = (
    ROOT
    / "results/v26_primary_confirmation_test_preflight_r6a"
)

OUT.mkdir(
    parents=True,
    exist_ok=True,
)


PROMOTED = "V26C_DualGateLiteCons"

PRE = "pre_normalization_sensor_domain"

DATASETS = [
    "UCI_HAR",
    "PAMAP2",
    "DSADS",
    "MotionSense",
]


EXPECTED_CONFIRMATION_PAIRS = {
    ("UCI_HAR", 789),
    ("UCI_HAR", 2026),

    ("DSADS", 789),
    ("DSADS", 2026),

    ("PAMAP2", 42),
    ("PAMAP2", 123),
    ("PAMAP2", 456),
    ("PAMAP2", 789),
    ("PAMAP2", 2026),

    ("MotionSense", 42),
    ("MotionSense", 123),
    ("MotionSense", 456),
    ("MotionSense", 789),
    ("MotionSense", 2026),
}


def sha256_file(
    path: Path,
):

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


def write_csv(
    path,
    rows,
):

    if not rows:
        raise RuntimeError(
            f"No rows supplied for {path}"
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

        writer.writerows(
            rows
        )


print("=" * 118)
print("V26 PRIMARY CONFIRMATION TEST PREFLIGHT R6A")
print("METADATA ONLY — PROTECTED TEST STILL LOCKED")
print("=" * 118)


# ============================================================
# 1. V26 R4 protocol boundary
# ============================================================

r4_receipt = json.loads(
    (
        V26_R4
        / "v26_primary_confirmation_protocol_receipt_r4.json"
    ).read_text()
)


required_r4 = {
    "status":
        "FROZEN_BEFORE_PRIMARY_CONFIRMATION",

    "promoted_candidate":
        PROMOTED,

    "promotion_reconstructed_mechanically":
        True,

    "selection_rule_modified":
        False,

    "confirmation_training_runs":
        14,

    "all_checkpoints_frozen_before_test":
        True,

    "expected_confirmation_test_rows":
        252,

    "evaluation_domain":
        PRE,

    "stage25_fault_conditions":
        17,

    "r4a_tensor_sha_required":
        True,

    "baseline_model_count":
        10,

    "comparison_model_count_with_v26":
        11,

    "test_inference_performed":
        False,

    "storm_inference_performed":
        False,

    "candidate_modified":
        False,

    "training_protocol_modified":
        False,

    "fault_protocol_modified":
        False,
}


for key, expected in required_r4.items():

    actual = r4_receipt.get(
        key
    )

    if actual != expected:

        raise RuntimeError(
            f"V26 R4 mismatch: "
            f"{key}={actual!r}; "
            f"expected={expected!r}"
        )


print(
    "V26_R4_PROTECTED_TEST_PROTOCOL_GATE_PASS=True"
)


# ============================================================
# 2. R5 training receipt: protected test still untouched
# ============================================================

r5_receipt = json.loads(
    (
        V26_R5
        / "v26_primary_confirmation_training_receipt_r5.json"
    ).read_text()
)


required_r5 = {
    "status":
        "PASS",

    "promoted_candidate":
        PROMOTED,

    "confirmation_training_manifest":
        "PASS_14_OF_14",

    "confirmation_training_runs":
        "PASS_14_OF_14",

    "confirmation_checkpoints":
        "FROZEN_SHA_PASS_14_OF_14",

    "training_run_count":
        14,

    "train_only_normalization":
        "PASS_4_OF_4",

    "validation_only_checkpoint_selection":
        True,

    "candidate_modified":
        False,

    "training_protocol_modified":
        False,

    "fault_protocol_modified":
        False,

    "loss_weight_modified":
        False,

    "protected_test_split_loaded":
        False,

    "protected_test_inference_performed":
        False,

    "storm_inference_performed":
        False,

    "storm_used_for_selection":
        False,

    "all_14_checkpoints_frozen_before_test":
        True,
}


for key, expected in required_r5.items():

    actual = r5_receipt.get(
        key
    )

    if actual != expected:

        raise RuntimeError(
            f"V26 R5 mismatch: "
            f"{key}={actual!r}; "
            f"expected={expected!r}"
        )


print(
    "V26_R5_PROTECTED_TEST_UNTOUCHED_GATE_PASS=True"
)


# ============================================================
# 3. Verify exact 14 frozen checkpoint files + SHA
# ============================================================

checkpoint_manifest_path = (
    V26_R5
    / "frozen_confirmation_checkpoint_manifest_14.csv"
)


with checkpoint_manifest_path.open(
    newline="",
    encoding="utf-8",
) as f:

    checkpoint_rows = list(
        csv.DictReader(f)
    )


if len(checkpoint_rows) != 14:

    raise RuntimeError(
        f"Expected 14 checkpoint rows, "
        f"found {len(checkpoint_rows)}"
    )


pairs = set()

checkpoint_audit_rows = []


for row in checkpoint_rows:

    if row[
        "candidate_id"
    ] != PROMOTED:

        raise RuntimeError(
            "Checkpoint manifest contains "
            "non-promoted candidate"
        )


    dataset = row[
        "dataset"
    ]

    seed = int(
        row[
            "seed"
        ]
    )


    pairs.add(
        (
            dataset,
            seed,
        )
    )


    path = (
        ROOT
        / row[
            "checkpoint"
        ]
    )


    if not path.exists():

        raise FileNotFoundError(
            path
        )


    actual_sha = sha256_file(
        path
    )


    if actual_sha != row[
        "checkpoint_sha256"
    ]:

        raise RuntimeError(
            f"Frozen checkpoint SHA mismatch: "
            f"{dataset}/seed_{seed}"
        )


    checkpoint_audit_rows.append({
        "candidate_id":
            PROMOTED,

        "dataset":
            dataset,

        "seed":
            seed,

        "num_classes":
            int(
                row[
                    "num_classes"
                ]
            ),

        "parameter_count":
            int(
                row[
                    "parameter_count"
                ]
            ),

        "best_epoch":
            int(
                row[
                    "best_epoch"
                ]
            ),

        "checkpoint":
            row[
                "checkpoint"
            ],

        "checkpoint_sha256":
            actual_sha,

        "sha_gate_pass":
            True,
    })


if pairs != EXPECTED_CONFIRMATION_PAIRS:

    raise RuntimeError(
        "Frozen confirmation checkpoint identity "
        "set does not match R4"
    )


write_csv(
    OUT
    / "confirmation_checkpoint_sha_audit_14.csv",
    checkpoint_audit_rows,
)


print(
    "V26_FROZEN_CONFIRMATION_CHECKPOINT_SHA_PASS_14_OF_14=True"
)


# ============================================================
# 4. Verify frozen implementation source has not drifted
# ============================================================

source_manifest = json.loads(
    (
        V26_IMPL
        / "implementation_source_sha_manifest.json"
    ).read_text()
)


source_audit = []


for row in source_manifest:

    path = (
        ROOT
        / row[
            "path"
        ]
    )


    if not path.exists():

        raise FileNotFoundError(
            path
        )


    actual = sha256_file(
        path
    )


    if actual != row[
        "sha256"
    ]:

        raise RuntimeError(
            f"Frozen source drift: {path}"
        )


    source_audit.append({
        "path":
            row[
                "path"
            ],

        "sha256":
            actual,

        "sha_gate_pass":
            True,
    })


if len(source_audit) != 6:

    raise RuntimeError(
        f"Expected six frozen source bindings, "
        f"found {len(source_audit)}"
    )


write_csv(
    OUT
    / "frozen_implementation_source_audit_6.csv",
    source_audit,
)


print(
    "V26_IMPLEMENTATION_SOURCE_SHA_PASS_6_OF_6=True"
)


# ============================================================
# 5. Frozen Stage25 fault manifest
# ============================================================

stage25_protocol = json.loads(
    (
        S25_R3
        / "stage25_physical_fault_protocol_r3.json"
    ).read_text()
)


faults = stage25_protocol[
    "fault_conditions"
]


if len(faults) != 17:

    raise RuntimeError(
        f"Expected 17 Stage25 faults, "
        f"found {len(faults)}"
    )


names = [
    row[
        "name"
    ]
    for row in faults
]


if len(
    set(
        names
    )
) != 17:

    raise RuntimeError(
        "Stage25 fault condition names not unique"
    )


family_counts = Counter(
    row[
        "family"
    ]
    for row in faults
)


expected_family_counts = {
    "modality_outage":
        3,

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
        f"Stage25 family counts changed: "
        f"{dict(family_counts)}"
    )


print(
    "STAGE25_FAULT_MANIFEST_PASS_17=True"
)

print(
    "STAGE25_FAULT_FAMILY_COUNTS_PASS=True"
)


# ============================================================
# 6. Derive exact 72 protected tensor identities from the
#    already-frozen Stage25 R5 evidence.
#
# 4 clean + 4*17 pre-normalization faults.
#
# This reads only old CSV metadata/hashes.
# It does NOT load any tensor or test index.
# ============================================================

cases_path = (
    S25_R5
    / "paired_domain_cases_7000.csv"
)


with cases_path.open(
    newline="",
    encoding="utf-8",
) as f:

    case_reader = csv.DictReader(f)

    case_columns = (
        case_reader.fieldnames
        or
        []
    )

    required_columns = {
        "dataset",
        "domain",
        "condition",
        "input_tensor_sha256",
    }


    missing = (
        required_columns
        -
        set(
            case_columns
        )
    )


    if missing:

        raise RuntimeError(
            f"Stage25 R5 cases missing columns: "
            f"{sorted(missing)}; "
            f"found={case_columns}"
        )


    cases = list(
        case_reader
    )


if len(cases) != 7000:

    raise RuntimeError(
        f"Expected 7000 frozen Stage25 R5 rows, "
        f"found {len(cases)}"
    )


tensor_identity_rows = []


for dataset in DATASETS:

    # --------------------------------------------------------
    # clean
    # --------------------------------------------------------

    clean_rows = [
        row
        for row in cases
        if (
            row[
                "dataset"
            ]
            ==
            dataset
            and
            row[
                "domain"
            ]
            ==
            "shared_clean"
            and
            row[
                "condition"
            ]
            ==
            "baseline"
        )
    ]


    clean_hashes = {
        row[
            "input_tensor_sha256"
        ]
        for row in clean_rows
    }


    if len(clean_hashes) != 1:

        raise RuntimeError(
            f"{dataset}: shared-clean tensor identity "
            f"not unique: {len(clean_hashes)}"
        )


    tensor_identity_rows.append({
        "dataset":
            dataset,

        "condition":
            "baseline",

        "family":
            "baseline",

        "domain":
            "shared_clean",

        "input_tensor_sha256":
            next(
                iter(
                    clean_hashes
                )
            ),
    })


    # --------------------------------------------------------
    # 17 protected physical pre-normalization conditions
    # --------------------------------------------------------

    for fault in faults:

        condition = fault[
            "name"
        ]


        selected = [
            row
            for row in cases
            if (
                row[
                    "dataset"
                ]
                ==
                dataset
                and
                row[
                    "domain"
                ]
                ==
                PRE
                and
                row[
                    "condition"
                ]
                ==
                condition
            )
        ]


        hashes = {
            row[
                "input_tensor_sha256"
            ]
            for row in selected
        }


        if len(hashes) != 1:

            raise RuntimeError(
                f"{dataset}/{condition}: "
                f"pre-domain tensor hash count "
                f"is {len(hashes)}, expected 1"
            )


        tensor_identity_rows.append({
            "dataset":
                dataset,

            "condition":
                condition,

            "family":
                fault[
                    "family"
                ],

            "domain":
                PRE,

            "input_tensor_sha256":
                next(
                    iter(
                        hashes
                    )
                ),
        })


if len(
    tensor_identity_rows
) != 72:

    raise RuntimeError(
        f"Expected 72 protected tensor identities, "
        f"found {len(tensor_identity_rows)}"
    )


if len({
    (
        row[
            "dataset"
        ],
        row[
            "condition"
        ],
    )
    for row in tensor_identity_rows
}) != 72:

    raise RuntimeError(
        "Protected tensor identity key set "
        "is not unique"
    )


write_csv(
    OUT
    / "protected_stage25_tensor_identity_manifest_72.csv",
    tensor_identity_rows,
)


print(
    "PROTECTED_STAGE25_TENSOR_IDENTITY_MANIFEST_PASS_72=True"
)


# ============================================================
# 7. Cross-bind those 72 hashes to the frozen R4A 140-tensor
#    manifest without assuming R4A column naming.
# ============================================================

r4a_manifest_path = (
    S25_R4A
    / "dataset_condition_tensor_manifest_140.csv"
)


with r4a_manifest_path.open(
    newline="",
    encoding="utf-8",
) as f:

    r4a_reader = csv.DictReader(f)

    r4a_rows = list(
        r4a_reader
    )


if len(
    r4a_rows
) != 140:

    raise RuntimeError(
        f"Expected 140 R4A tensor-manifest rows, "
        f"found {len(r4a_rows)}"
    )


sha_pattern = re.compile(
    r"^[0-9a-f]{64}$"
)


r4a_sha_values = set()


for row in r4a_rows:

    for value in row.values():

        if value is None:
            continue

        value = value.strip().lower()

        if sha_pattern.fullmatch(
            value
        ):

            r4a_sha_values.add(
                value
            )


missing_r4a_hashes = [
    row
    for row in tensor_identity_rows
    if row[
        "input_tensor_sha256"
    ].lower()
    not in
    r4a_sha_values
]


if missing_r4a_hashes:

    raise RuntimeError(
        "Protected tensor identities are not all "
        "present in frozen R4A manifest. "
        f"Missing count={len(missing_r4a_hashes)}"
    )


print(
    "PROTECTED_72_TENSOR_SHA_BOUND_TO_R4A_PASS_72_OF_72=True"
)


# ============================================================
# 8. Bind frozen old-model comparator evidence
# ============================================================

baseline_path = (
    S25_R6
    / "heldout_matched_equal_dataset_summary_20.csv"
)


with baseline_path.open(
    newline="",
    encoding="utf-8",
) as f:

    baseline_rows = list(
        csv.DictReader(f)
    )


if len(
    baseline_rows
) != 20:

    raise RuntimeError(
        f"Expected 20 held-out baseline summary rows, "
        f"found {len(baseline_rows)}"
    )


pre_baselines = [
    row
    for row in baseline_rows
    if row[
        "domain"
    ]
    ==
    PRE
]


if len(
    pre_baselines
) != 10:

    raise RuntimeError(
        f"Expected 10 frozen physical-domain baseline models, "
        f"found {len(pre_baselines)}"
    )


if len({
    row[
        "model"
    ]
    for row in pre_baselines
}) != 10:

    raise RuntimeError(
        "Frozen baseline model identities not unique"
    )


write_csv(
    OUT
    / "frozen_primary_baseline_summary_10.csv",
    pre_baselines,
)


print(
    "FROZEN_PRIMARY_BASELINE_MODEL_SUMMARY_PASS_10=True"
)


# ============================================================
# 9. Predeclare exact one-time evaluation cardinality
# ============================================================

checkpoint_count = len(
    checkpoint_rows
)

condition_count = (
    1
    +
    len(
        faults
    )
)

expected_rows = (
    checkpoint_count
    *
    condition_count
)


if checkpoint_count != 14:

    raise RuntimeError(
        "Confirmation checkpoint count changed"
    )


if condition_count != 18:

    raise RuntimeError(
        "Confirmation condition count changed"
    )


if expected_rows != 252:

    raise RuntimeError(
        f"Expected 252 test rows, got {expected_rows}"
    )


print(
    "ONE_TIME_CONFIRMATION_CARDINALITY_14x18_EQUALS_252=True"
)


# ============================================================
# 10. Write final preflight receipt
# ============================================================

receipt = {
    "stage":
        "V26_PRIMARY_CONFIRMATION_TEST_PREFLIGHT_R6A",

    "status":
        "PASS",

    "promoted_candidate":
        PROMOTED,

    "frozen_confirmation_checkpoints":
        "PASS_14_OF_14",

    "implementation_source_sha":
        "PASS_6_OF_6",

    "stage25_fault_manifest":
        "PASS_17",

    "stage25_fault_family_counts":
        "PASS",

    "protected_tensor_identity_manifest":
        "PASS_72",

    "protected_tensor_sha_bound_to_r4a":
        "PASS_72_OF_72",

    "frozen_baseline_models":
        10,

    "comparison_model_count_after_v26":
        11,

    "confirmation_checkpoints":
        14,

    "conditions_per_checkpoint":
        18,

    "expected_confirmation_rows":
        252,

    "evaluation_domain":
        PRE,

    "torch_imported":
        False,

    "model_constructed":
        False,

    "checkpoint_deserialized":
        False,

    "test_index_loaded":
        False,

    "test_tensor_loaded":
        False,

    "test_inference_performed":
        False,

    "training_performed":
        False,

    "optimizer_created":
        False,

    "candidate_modified":
        False,

    "training_protocol_modified":
        False,

    "fault_protocol_modified":
        False,

    "storm_used":
        False,

    "next_gate":
        (
            "Unlock exactly one V26 protected confirmation "
            "evaluation: 14 frozen V26C checkpoints x "
            "18 frozen Stage25 physical-domain conditions "
            "= 252 rows. Every regenerated tensor must match "
            "this R6A 72-tensor SHA manifest before inference."
        ),
}


write_json(
    OUT
    / "v26_primary_confirmation_test_preflight_receipt_r6a.json",
    receipt,
)


print()
print("=" * 118)
print("V26 R6A PREFLIGHT FINAL RECEIPT")
print("=" * 118)

print(
    json.dumps(
        receipt,
        indent=2,
    )
)


print()
print(
    "V26_PRIMARY_CONFIRMATION_TEST_PREFLIGHT_R6A_PASS=True"
)

print(
    "V26_FROZEN_CONFIRMATION_CHECKPOINT_SHA_PASS_14_OF_14=True"
)

print(
    "PROTECTED_STAGE25_TENSOR_IDENTITY_MANIFEST_PASS_72=True"
)

print(
    "PROTECTED_72_TENSOR_SHA_BOUND_TO_R4A_PASS_72_OF_72=True"
)

print(
    "FROZEN_PRIMARY_BASELINE_MODEL_SUMMARY_PASS_10=True"
)

print(
    "ONE_TIME_CONFIRMATION_CARDINALITY_14x18_EQUALS_252=True"
)

print(
    "TORCH_IMPORTED=False"
)

print(
    "MODEL_CONSTRUCTED=False"
)

print(
    "CHECKPOINT_DESERIALIZED=False"
)

print(
    "TEST_INDEX_LOADED=False"
)

print(
    "TEST_TENSOR_LOADED=False"
)

print(
    "TEST_INFERENCE_PERFORMED=False"
)

print(
    "TRAINING_PERFORMED=False"
)

print(
    "STORM_USED=False"
)
