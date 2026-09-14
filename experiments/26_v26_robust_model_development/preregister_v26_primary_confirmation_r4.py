from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd


ROOT = Path(
    "/mnt/hdd16T/ToqeerHomeBackup/toqeer/IMU_Reliability"
)

V26_PROTO = (
    ROOT
    / "results/v26_development_protocol_r1"
)

V26_IMPL = (
    ROOT
    / "results/v26_implementation_integrity_r2"
)

V26_R3 = (
    ROOT
    / "results/v26_development_screening_r3"
)

STAGE25_R3 = (
    ROOT
    / "results/stage25_physical_fault_protocol"
    / "protocol_preregistration_r3"
)

R4A = (
    ROOT
    / "results/stage25_physical_fault_protocol"
    / "transform_provenance_preflight_r4a"
)

R6 = (
    ROOT
    / "results/stage25_physical_fault_protocol"
    / "scientific_analysis_r6"
)

OUT = (
    ROOT
    / "results/v26_primary_confirmation_protocol_r4"
)

OUT.mkdir(
    parents=True,
    exist_ok=True,
)


PROMOTED = "V26C_DualGateLiteCons"

ALL_SEEDS = [
    42,
    123,
    456,
    789,
    2026,
]

PRIMARY_CONFIRMATION = {
    "UCI_HAR": [
        789,
        2026,
    ],

    "DSADS": [
        789,
        2026,
    ],

    "PAMAP2":
        ALL_SEEDS,

    "MotionSense":
        ALL_SEEDS,
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


print("=" * 118)
print("V26 PRIMARY CONFIRMATION PROTOCOL R4")
print("PROMOTED MODEL FREEZE BEFORE CONFIRMATION")
print("=" * 118)


# ============================================================
# 1. Verify frozen promotion decision
# ============================================================

promotion = json.loads(
    (
        V26_R3
        / "promotion_decision_r3.json"
    ).read_text()
)


if (
    promotion.get(
        "status"
    )
    !=
    "PASS"
):

    raise RuntimeError(
        "R3 promotion status is not PASS"
    )


if (
    promotion.get(
        "promotion_decision"
    )
    !=
    "PROMOTE_ONE"
):

    raise RuntimeError(
        "R3 did not freeze PROMOTE_ONE"
    )


if (
    promotion.get(
        "promoted_candidate"
    )
    !=
    PROMOTED
):

    raise RuntimeError(
        "Frozen promoted candidate is not V26C"
    )


if (
    promotion.get(
        "test_inference_performed"
    )
    is not False
):

    raise RuntimeError(
        "Protected test was already consumed"
    )


if (
    promotion.get(
        "storm_used_for_selection"
    )
    is not False
):

    raise RuntimeError(
        "STORM was unexpectedly used for selection"
    )


print(
    "PROMOTION_DECISION_BOUND_V26C=True"
)


# ============================================================
# 2. Reconstruct and audit frozen candidate decision
# ============================================================

summary = pd.read_csv(
    V26_R3
    / "candidate_development_summary_4.csv"
)


if len(summary) != 4:

    raise RuntimeError(
        "Expected four candidate summaries"
    )


if not summary[
    "promotion_eligible"
].all():

    raise RuntimeError(
        "Expected all four candidates to be eligible "
        "according to frozen R3 result"
    )


eligible = summary[
    summary[
        "promotion_eligible"
    ]
].copy()


top_score = float(
    eligible[
        "mean_selection_score"
    ].max()
)


tie_set = eligible[
    (
        top_score
        -
        eligible[
            "mean_selection_score"
        ]
    )
    <
    0.002
].copy()


tie_set = tie_set.sort_values(
    [
        "max_parameter_count",
        "mean_selection_score",
        "candidate_id",
    ],
    ascending=[
        True,
        False,
        True,
    ],
)


mechanical_winner = str(
    tie_set.iloc[0][
        "candidate_id"
    ]
)


if mechanical_winner != PROMOTED:

    raise RuntimeError(
        f"Mechanical promotion reconstruction "
        f"gave {mechanical_winner}, expected {PROMOTED}"
    )


v26c = summary[
    summary[
        "candidate_id"
    ]
    ==
    PROMOTED
]


if len(v26c) != 1:

    raise RuntimeError(
        "V26C summary row missing"
    )


v26c = v26c.iloc[0]


decision_audit = {
    "candidate":
        PROMOTED,

    "mean_clean_macro_f1":
        float(
            v26c[
                "mean_clean_macro_f1"
            ]
        ),

    "mean_recoverable_fault_macro_f1":
        float(
            v26c[
                "mean_all_recoverable_fault_macro_f1"
            ]
        ),

    "mean_family_balanced_macro_f1":
        float(
            v26c[
                "mean_family_balanced_macro_f1"
            ]
        ),

    "mean_selection_score":
        float(
            v26c[
                "mean_selection_score"
            ]
        ),

    "mean_delta_clean_macro_f1_vs_v25":
        float(
            v26c[
                "mean_delta_clean_macro_f1_vs_v25"
            ]
        ),

    "mean_delta_recoverable_macro_f1_vs_v25":
        float(
            v26c[
                "mean_delta_all_recoverable_fault_macro_f1_vs_v25"
            ]
        ),

    "mean_delta_family_balanced_macro_f1_vs_v25":
        float(
            v26c[
                "mean_delta_family_balanced_macro_f1_vs_v25"
            ]
        ),

    "max_parameter_count":
        int(
            v26c[
                "max_parameter_count"
            ]
        ),

    "top_selection_score":
        top_score,

    "tie_window":
        0.002,

    "tie_set": (
        tie_set[
            [
                "candidate_id",
                "mean_selection_score",
                "max_parameter_count",
            ]
        ]
        .to_dict(
            orient="records"
        )
    ),

    "mechanical_winner":
        mechanical_winner,

    "selection_rule_changed_after_outcomes":
        False,
}


write_json(
    OUT
    / "promoted_candidate_decision_audit.json",
    decision_audit,
)


print()
print(
    "V26C_MEAN_CLEAN_F1=",
    decision_audit[
        "mean_clean_macro_f1"
    ],
)

print(
    "V26C_MEAN_RECOVERABLE_F1=",
    decision_audit[
        "mean_recoverable_fault_macro_f1"
    ],
)

print(
    "V26C_MEAN_FAMILY_BALANCED_F1=",
    decision_audit[
        "mean_family_balanced_macro_f1"
    ],
)

print(
    "V26C_DELTA_CLEAN_VS_V25=",
    decision_audit[
        "mean_delta_clean_macro_f1_vs_v25"
    ],
)

print(
    "V26C_DELTA_RECOVERABLE_VS_V25=",
    decision_audit[
        "mean_delta_recoverable_macro_f1_vs_v25"
    ],
)

print(
    "V26C_DELTA_FAMILY_BALANCED_VS_V25=",
    decision_audit[
        "mean_delta_family_balanced_macro_f1_vs_v25"
    ],
)

print(
    "V26C_MAX_PARAMETER_COUNT=",
    decision_audit[
        "max_parameter_count"
    ],
)

print(
    "PROMOTION_MECHANICAL_RECONSTRUCTION_PASS=True"
)


# ============================================================
# 3. Bind exact promoted implementation
# ============================================================

source_manifest = json.loads(
    (
        V26_IMPL
        / "implementation_source_sha_manifest.json"
    ).read_text()
)


required_sources = {
    "experiments/26_v26_robust_model_development/"
    "candidate_models_r2.py",

    "experiments/26_v26_robust_model_development/"
    "physical_faults_r2.py",

    "experiments/26_v26_robust_model_development/"
    "losses_r2.py",

    "experiments/26_v26_robust_model_development/"
    "validation_r2.py",
}


manifest_lookup = {
    row[
        "path"
    ]:
        row[
            "sha256"
        ]

    for row in source_manifest
}


missing = (
    required_sources
    -
    set(
        manifest_lookup
    )
)


if missing:

    raise RuntimeError(
        f"Missing frozen implementation sources: "
        f"{sorted(missing)}"
    )


promoted_sources = {
    path:
        manifest_lookup[
            path
        ]

    for path in sorted(
        required_sources
    )
}


write_json(
    OUT
    / "promoted_candidate_source_bindings.json",
    promoted_sources,
)


print(
    "PROMOTED_IMPLEMENTATION_SOURCE_BINDING_PASS=True"
)


# ============================================================
# 4. Freeze exact 14 confirmation training runs
# ============================================================

run_rows = []


for dataset, seeds in (
    PRIMARY_CONFIRMATION.items()
):

    for seed in seeds:

        run_rows.append({
            "dataset":
                dataset,

            "seed":
                int(seed),

            "candidate_id":
                PROMOTED,

            "role":
                (
                    "primary_confirmation"
                ),
        })


if len(run_rows) != 14:

    raise RuntimeError(
        f"Expected 14 confirmation runs, "
        f"found {len(run_rows)}"
    )


run_df = pd.DataFrame(
    run_rows
)

run_df.to_csv(
    OUT
    / "primary_confirmation_training_manifest_14.csv",
    index=False,
)


print(
    "PRIMARY_CONFIRMATION_TRAINING_MANIFEST_PASS_14=True"
)


# ============================================================
# 5. Training protocol freeze
# ============================================================

training_protocol = {
    "candidate":
        PROMOTED,

    "architecture":
        (
            "exact frozen V26C_DualGateLiteCons "
            "implementation from V26 R2"
        ),

    "training_loss":
        (
            "CE(clean) + CE(physical_fault) + "
            "0.20*symmetric_KL(clean,fault)"
        ),

    "fault_domain":
        (
            "pre-normalization sensor-domain "
            "model-window representation"
        ),

    "fault_family_sampling":
        (
            "exact frozen V26 R2 randomized "
            "six-family training operator"
        ),

    "all_sensors_failure_training":
        False,

    "optimizer":
        "AdamW",

    "learning_rate":
        1e-3,

    "weight_decay":
        1e-4,

    "batch_size":
        64,

    "max_epochs":
        100,

    "early_stopping_patience":
        15,

    "gradient_clipping_norm":
        1.0,

    "checkpoint_selection":
        (
            "validation-only frozen score: "
            "0.50 family-balanced macro-F1 + "
            "0.30 recoverable-fault macro-F1 + "
            "0.20 clean macro-F1"
        ),

    "validation_fault_count":
        16,

    "validation_randomness_root":
        26001,

    "training_data":
        "train_idx only",

    "checkpoint_selection_data":
        "val_idx only",

    "test_idx_access_during_training":
        False,

    "critical_execution_order": [
        (
            "train all 14 confirmation checkpoints "
            "using train/validation only"
        ),
        (
            "freeze SHA256 of all 14 checkpoints"
        ),
        (
            "only then open any test_idx/test tensor"
        ),
    ],

    "hyperparameter_changes_permitted":
        False,

    "candidate_changes_permitted":
        False,

    "loss_weight_changes_permitted":
        False,

    "fault_distribution_changes_permitted":
        False,
}


write_json(
    OUT
    / "primary_confirmation_training_protocol.json",
    training_protocol,
)


# ============================================================
# 6. Freeze primary confirmation TEST protocol
#
# Exact Stage25 physical pre-normalization conditions.
# ============================================================

test_protocol = {
    "test_access":
        (
            "FORBIDDEN until all 14 trained checkpoints "
            "are frozen and hashed"
        ),

    "evaluation_domain":
        "pre_normalization_sensor_domain",

    "clean_condition":
        True,

    "fault_condition_count":
        17,

    "conditions_source":
        (
            "frozen Stage25 R3 fault manifest"
        ),

    "tensor_identity_source":
        (
            "frozen Stage25 R4A "
            "dataset_condition_tensor_manifest_140.csv"
        ),

    "required_tensor_identity":
        (
            "clean + 17 pre-normalization tensors for "
            "each of four datasets must match frozen R4A SHA"
        ),

    "confirmation_checkpoints":
        14,

    "rows_per_checkpoint":
        18,

    "expected_test_case_rows":
        252,

    "metrics": [
        "clean_accuracy",
        "clean_macro_f1",
        "all_fault_accuracy",
        "all_fault_macro_f1",
        "recoverable_fault_accuracy",
        "recoverable_fault_macro_f1",
        "family_balanced_accuracy",
        "family_balanced_macro_f1",
    ],

    "aggregation": {
        "within_dataset_model_seed":
            (
                "same Stage25 R3 definitions"
            ),

        "within_dataset":
            "average available confirmation seeds",

        "cross_dataset":
            (
                "equal weight over UCI_HAR, PAMAP2, "
                "DSADS, MotionSense"
            ),

        "sample_pooling_across_datasets":
            False,
    },

    "baseline_comparator_source":
        (
            "frozen Stage25 R6 held-out matched "
            "10-model summaries"
        ),

    "model_count_after_v26":
        11,

    "no_test_based_retraining":
        True,

    "no_test_based_hyperparameter_change":
        True,

    "no_test_based_architecture_change":
        True,

    "storm_not_used_in_this_stage":
        True,
}


write_json(
    OUT
    / "primary_confirmation_test_protocol.json",
    test_protocol,
)


print(
    "PRIMARY_CONFIRMATION_TEST_PROTOCOL_FROZEN=True"
)


# ============================================================
# 7. Predeclare interpretation criteria
#
# These DO NOT control whether results are reported.
# They control claim strength only.
# ============================================================

claim_criteria = {
    "candidate_is_final_before_test":
        True,

    "all_confirmation_results_reported":
        True,

    "primary_metrics": [
        "all_fault_macro_f1",
        "family_balanced_macro_f1",
    ],

    "secondary_metrics": [
        "all_fault_accuracy",
        "recoverable_fault_accuracy",
        "recoverable_fault_macro_f1",
        "family_balanced_accuracy",
        "clean_accuracy",
        "clean_macro_f1",
    ],

    "strong_superiority_tier_A": {
        "family_balanced_macro_f1_rank_max":
            1,

        "all_fault_macro_f1_rank_max":
            1,

        "clean_macro_f1_delta_vs_v25_min":
            -0.015,

        "parameter_count_max":
            30000,
    },

    "strong_tradeoff_tier_B": {
        "require_rank_1_in_at_least_one_of": [
            "all_fault_macro_f1",
            "family_balanced_macro_f1",
        ],

        "other_primary_metric_rank_max":
            2,

        "clean_macro_f1_delta_vs_v25_min":
            -0.015,

        "parameter_count_max":
            30000,
    },

    "if_neither_tier_is_met":
        (
            "Report the result honestly as a robustness-"
            "efficiency trade-off or negative confirmation. "
            "Do not tune V26C using confirmation outcomes."
        ),

    "universal_SOTA_claim_allowed":
        False,

    "storm_superiority_claim_allowed_here":
        False,
}


write_json(
    OUT
    / "primary_confirmation_claim_criteria.json",
    claim_criteria,
)


print(
    "PRIMARY_CONFIRMATION_CLAIM_CRITERIA_FROZEN=True"
)


# ============================================================
# 8. Freeze external-evaluation boundary
# ============================================================

external_policy = {
    "storm_use_before_internal_confirmation":
        False,

    "storm_use_for_v26_tuning":
        False,

    "storm_use_for_candidate_reselection":
        False,

    "storm_external_evaluation_after_internal_confirmation":
        True,

    "external_evaluation_requires":
        (
            "V26C architecture and training procedure "
            "remain unchanged"
        ),
}


write_json(
    OUT
    / "storm_external_boundary_r4.json",
    external_policy,
)


# ============================================================
# 9. Final receipt
# ============================================================

receipt = {
    "protocol":
        "V26_PRIMARY_CONFIRMATION_PROTOCOL_R4",

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

    "confirmation_datasets": [
        "UCI_HAR",
        "DSADS",
        "PAMAP2",
        "MotionSense",
    ],

    "uci_dsads_confirmation_seeds": [
        789,
        2026,
    ],

    "pamap_motionsense_confirmation_seeds":
        ALL_SEEDS,

    "all_checkpoints_frozen_before_test":
        True,

    "expected_confirmation_test_rows":
        252,

    "evaluation_domain":
        "pre_normalization_sensor_domain",

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

    "confirmation_training_performed":
        False,

    "storm_inference_performed":
        False,

    "storm_used_for_selection":
        False,

    "candidate_modified":
        False,

    "training_protocol_modified":
        False,

    "fault_protocol_modified":
        False,

    "next_gate":
        (
            "Implement confirmation-only train/val loader, "
            "train exactly 14 frozen V26C checkpoints with "
            "no test access, verify checkpoint SHA manifest, "
            "then unlock one-time primary test evaluation."
        ),
}


write_json(
    OUT
    / "v26_primary_confirmation_protocol_receipt_r4.json",
    receipt,
)


print()
print("=" * 118)
print("V26 PRIMARY CONFIRMATION R4 FINAL RECEIPT")
print("=" * 118)

print(
    json.dumps(
        receipt,
        indent=2,
    )
)


print()
print(
    "V26_PRIMARY_CONFIRMATION_PROTOCOL_R4_FROZEN=True"
)

print(
    "PROMOTED_CANDIDATE=V26C_DualGateLiteCons"
)

print(
    "CONFIRMATION_TRAINING_RUNS=14"
)

print(
    "EXPECTED_CONFIRMATION_TEST_ROWS=252"
)

print(
    "ALL_CHECKPOINTS_MUST_FREEZE_BEFORE_TEST=True"
)

print(
    "TEST_INFERENCE_PERFORMED=False"
)

print(
    "CONFIRMATION_TRAINING_PERFORMED=False"
)

print(
    "STORM_USED_FOR_SELECTION=False"
)
