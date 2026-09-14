from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pandas as pd


ROOT = Path(
    "/mnt/hdd16T/ToqeerHomeBackup/toqeer/IMU_Reliability"
)

R6 = (
    ROOT
    / "results"
    / "stage25_physical_fault_protocol"
    / "scientific_analysis_r6"
)

EXP = (
    ROOT
    / "experiments"
    / "26_v26_robust_model_development"
)

OUT = (
    ROOT
    / "results"
    / "v26_development_protocol_r1"
)

OUT.mkdir(
    parents=True,
    exist_ok=True,
)


R6_EXPECTED_SHA = (
    "6f36f44f40346046b0306b933ee0c324"
    "13f5b0bb4f7d70cab0331e9f7fdd0eac"
)


DEVELOPMENT_DATASETS = [
    "UCI_HAR",
    "DSADS",
]

DEVELOPMENT_SEEDS = [
    42,
    123,
    456,
]

SEED_HELDOUT = [
    789,
    2026,
]

SELECTION_HELDOUT_DATASETS = [
    "PAMAP2",
    "MotionSense",
]

ALL_SEEDS = [
    42,
    123,
    456,
    789,
    2026,
]


def sha256_file(path: Path) -> str:

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


print("=" * 118)
print("V26/V27 ROBUST MODEL DEVELOPMENT PROTOCOL R1")
print("PREREGISTRATION BEFORE ANY NEW MODEL TRAINING")
print("=" * 118)


# ============================================================
# 1. Verify frozen R6 receipt
# ============================================================

receipt_path = (
    R6
    / "stage25_scientific_analysis_receipt_r6.json"
)

receipt = json.loads(
    receipt_path.read_text()
)


required = {
    "status":
        "PASS",

    "r5_total_rows_verified":
        7000,

    "post_inference_commuting_controls":
        "PASS_800_OF_800",

    "v25_heldout_matched_primary":
        True,

    "v25_heldout_checkpoint_count":
        14,

    "v25_development_checkpoint_count":
        6,

    "normalization_offset_mechanism_rows":
        52,

    "model_forward_performed":
        False,

    "training_performed":
        False,

    "v25_retrained":
        False,

    "storm_used_for_tuning":
        False,
}


for key, expected in required.items():

    actual = receipt.get(key)

    if actual != expected:

        raise RuntimeError(
            f"R6 prerequisite mismatch: "
            f"{key}={actual!r}, "
            f"expected={expected!r}"
        )


print(
    "R6_SCIENTIFIC_PREREQUISITE_PASS=True"
)


# ============================================================
# 2. Bind R6 findings that motivate V26
# ============================================================

heldout_path = (
    R6
    / "heldout_matched_equal_dataset_summary_20.csv"
)

family_path = (
    R6
    / "heldout_matched_fault_family_summary_120.csv"
)

overall_rank_path = (
    R6
    / "overall_equal_dataset_domain_ranks_120.csv"
)

mechanism_path = (
    R6
    / "normalization_offset_mechanism_correlations_10.csv"
)


for path in [
    heldout_path,
    family_path,
    overall_rank_path,
    mechanism_path,
]:

    if not path.exists():

        raise FileNotFoundError(
            path
        )


heldout = pd.read_csv(
    heldout_path
)

families = pd.read_csv(
    family_path
)

overall = pd.read_csv(
    overall_rank_path
)

mechanism = pd.read_csv(
    mechanism_path
)


PRE = "pre_normalization_sensor_domain"
V25 = "ReliabilityCNN_v25"


v25_heldout = heldout[
    (
        heldout["model"]
        ==
        V25
    )
    &
    (
        heldout["domain"]
        ==
        PRE
    )
]


if len(v25_heldout) != 1:

    raise RuntimeError(
        "Could not bind unique V25 held-out "
        "physical-domain summary"
    )


v25_heldout = v25_heldout.iloc[0]


v25_family = families[
    (
        families["model"]
        ==
        V25
    )
    &
    (
        families["domain"]
        ==
        PRE
    )
].copy()


if len(v25_family) != 6:

    raise RuntimeError(
        "Could not bind V25 six-family "
        "held-out failure map"
    )


motivation = {
    "source":
        "frozen Stage25 R6",

    "r6_sha256sums_sha256":
        R6_EXPECTED_SHA,

    "primary_problem":
        (
            "V25 is strong on the full descriptive "
            "aggregate but falls to rank 4-5 on the "
            "primary 14-checkpoint held-out physical-domain "
            "evaluation. The next model must improve "
            "generalization, not merely development-set "
            "robustness."
        ),

    "v25_heldout": {
        "all_fault_accuracy":
            float(
                v25_heldout[
                    "all_fault_accuracy"
                ]
            ),

        "all_fault_accuracy_rank":
            int(
                v25_heldout[
                    "all_fault_accuracy_rank"
                ]
            ),

        "all_fault_macro_f1":
            float(
                v25_heldout[
                    "all_fault_macro_f1"
                ]
            ),

        "all_fault_macro_f1_rank":
            int(
                v25_heldout[
                    "all_fault_macro_f1_rank"
                ]
            ),

        "recoverable_fault_macro_f1":
            float(
                v25_heldout[
                    "recoverable_fault_macro_f1"
                ]
            ),

        "recoverable_fault_macro_f1_rank":
            int(
                v25_heldout[
                    "recoverable_fault_macro_f1_rank"
                ]
            ),

        "family_balanced_macro_f1":
            float(
                v25_heldout[
                    "family_balanced_macro_f1"
                ]
            ),

        "family_balanced_macro_f1_rank":
            int(
                v25_heldout[
                    "family_balanced_macro_f1_rank"
                ]
            ),
    },

    "v25_fault_family_map":
        (
            v25_family[
                [
                    "family",
                    "accuracy",
                    "accuracy_rank",
                    "macro_f1",
                    "macro_f1_rank",
                ]
            ]
            .sort_values(
                "macro_f1_rank"
            )
            .to_dict(
                orient="records"
            )
        ),

    "mechanism_summary":
        (
            mechanism.to_dict(
                orient="records"
            )
        ),

    "scientific_design_response": [
        (
            "Use physical pre-normalization corruption "
            "during training."
        ),
        (
            "Give corrupted examples an explicit "
            "classification gradient."
        ),
        (
            "Model accelerometer and gyroscope reliability "
            "separately."
        ),
        (
            "Use randomized training severities so the "
            "network does not memorize one Stage25 test "
            "condition."
        ),
        (
            "Optimize robustness on validation data only; "
            "do not access test labels/predictions during "
            "candidate development."
        ),
        (
            "Do not use STORM outcomes to choose model "
            "architecture or hyperparameters."
        ),
    ],
}


write_json(
    OUT
    / "motivation_from_frozen_r6.json",
    motivation,
)


print(
    "R6_MOTIVATION_BINDING_PASS=True"
)


# ============================================================
# 3. Data-access policy
# ============================================================

access_policy = {
    "development_phase":
        "V26_CANDIDATE_SCREENING",

    "architecture_and_training_selection": {
        "datasets":
            DEVELOPMENT_DATASETS,

        "seeds":
            DEVELOPMENT_SEEDS,

        "allowed_indices": [
            "train_idx",
            "val_idx",
        ],

        "test_idx_access":
            "FORBIDDEN_FOR_MODEL_SELECTION",

        "candidate_selection_metrics":
            "validation only",

        "number_of_development_runs_per_candidate":
            6,
    },

    "primary_confirmation_after_candidate_freeze": {
        "seed_heldout": {
            "datasets": [
                "UCI_HAR",
                "DSADS",
            ],

            "seeds":
                SEED_HELDOUT,

            "checkpoint_count":
                4,
        },

        "selection_heldout_datasets": {
            "datasets":
                SELECTION_HELDOUT_DATASETS,

            "seeds":
                ALL_SEEDS,

            "checkpoint_count":
                10,
        },

        "total_primary_confirmation_checkpoints":
            14,
    },

    "full_final_evaluation": {
        "datasets": [
            "UCI_HAR",
            "PAMAP2",
            "DSADS",
            "MotionSense",
        ],

        "seeds":
            ALL_SEEDS,

        "checkpoint_count":
            20,

        "interpretation":
            (
                "All-20 summary is descriptive. "
                "The predeclared 14-checkpoint confirmation "
                "stratum remains primary for direct "
                "continuity with V25."
            ),
    },

    "storm_policy": {
        "available_for_model_selection":
            False,

        "available_for_hyperparameter_selection":
            False,

        "available_for_candidate_rejection":
            False,

        "when_it_may_be_used":
            (
                "Only after the final candidate and training "
                "protocol are frozen."
            ),
    },
}


write_json(
    OUT
    / "development_data_access_policy.json",
    access_policy,
)


print(
    "DEVELOPMENT_DATA_ACCESS_POLICY_FROZEN=True"
)


# ============================================================
# 4. Physical-domain TRAINING fault distribution
#
# Training distributions deliberately differ from the exact
# deterministic Stage25 test instances.
# ============================================================

fault_training = [
    {
        "family":
            "modality_outage",

        "sampling_weight":
            1.0 / 6.0,

        "training_operation":
            (
                "randomly choose accelerometer OR gyroscope; "
                "set selected modality raw values to physical 0"
            ),

        "severity_distribution":
            "complete selected-modality outage",

        "all_sensors_failure_used_for_training":
            False,
    },

    {
        "family":
            "single_axis_outage",

        "sampling_weight":
            1.0 / 6.0,

        "training_operation":
            (
                "uniformly choose one of six raw channels; "
                "set selected channel to physical 0"
            ),

        "severity_distribution":
            "complete selected-axis outage",

        "all_sensors_failure_used_for_training":
            False,
    },

    {
        "family":
            "intermittent_dropout",

        "sampling_weight":
            1.0 / 6.0,

        "training_operation":
            (
                "randomly choose accel or gyro; "
                "independent temporal dropout mask"
            ),

        "severity_distribution":
            "drop_probability ~ Uniform(0.10, 0.50)",

        "all_sensors_failure_used_for_training":
            False,
    },

    {
        "family":
            "gaussian_noise",

        "sampling_weight":
            1.0 / 6.0,

        "training_operation":
            (
                "randomly choose accel or gyro; "
                "add noise in raw domain proportional "
                "to frozen train-only channel std"
            ),

        "severity_distribution":
            (
                "sigma_normalized_units ~ "
                "Uniform(0.10, 0.70)"
            ),

        "all_sensors_failure_used_for_training":
            False,
    },

    {
        "family":
            "stuck_value",

        "sampling_weight":
            1.0 / 6.0,

        "training_operation":
            (
                "randomly choose accel or gyro; "
                "freeze selected modality at an observed "
                "sample value from a random onset onward"
            ),

        "severity_distribution":
            (
                "onset_fraction ~ Uniform(0.20, 0.80)"
            ),

        "all_sensors_failure_used_for_training":
            False,
    },

    {
        "family":
            "scale_drift",

        "sampling_weight":
            1.0 / 6.0,

        "training_operation":
            (
                "randomly choose accel or gyro; "
                "apply linear multiplicative drift in raw domain"
            ),

        "severity_distribution":
            (
                "final_factor ~ Uniform(0.50, 2.00); "
                "start_factor=1.0"
            ),

        "all_sensors_failure_used_for_training":
            False,
    },
]


with (
    OUT
    / "training_fault_distribution.csv"
).open(
    "w",
    newline="",
    encoding="utf-8",
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            fault_training[0].keys()
        ),
    )

    writer.writeheader()
    writer.writerows(
        fault_training
    )


print(
    "PHYSICAL_TRAINING_FAULT_DISTRIBUTION_FROZEN_6_FAMILIES=True"
)


# ============================================================
# 5. Candidate architectures
#
# Fixed BEFORE training.
# ============================================================

candidates = [
    {
        "candidate_id":
            "V26A_V25_PhysCE",

        "role":
            "training-mechanism ablation",

        "architecture":
            "exact V25Dense64 architecture",

        "input_split":
            "none",

        "fusion":
            "existing V25Dense64",

        "training_loss":
            (
                "CE(clean) + 1.0*CE(physical_fault)"
            ),

        "consistency_loss":
            "none",

        "scientific_question":
            (
                "How much of the robustness gap can be "
                "closed by correcting V25 training alone?"
            ),
    },

    {
        "candidate_id":
            "V26B_DualGateLite",

        "role":
            "primary modality-aware candidate",

        "architecture":
            (
                "two independent accel/gyro temporal branches"
            ),

        "input_split":
            (
                "acc=[0,1,2]; gyro=[3,4,5]"
            ),

        "branch_definition":
            (
                "Conv1d(3,24,k5,s1,p2,bias=False)+BN+SiLU; "
                "DSBlock(24->32,k5,s2); "
                "DSBlock(32->48,k5,s2); "
                "DSBlock(48->48,k3,s1); "
                "AdaptiveAvgPool1d(1)"
            ),

        "reliability_gate":
            (
                "per branch: Linear(48,16)+SiLU+"
                "Linear(16,1)+Sigmoid"
            ),

        "fusion":
            (
                "concat(r_acc*h_acc, "
                "r_gyro*h_gyro, "
                "abs(h_acc-h_gyro)) => 144 dims"
            ),

        "classifier":
            (
                "Linear(144,64)+SiLU+Dropout(0.10)+"
                "Linear(64,num_classes)"
            ),

        "training_loss":
            (
                "CE(clean) + 1.0*CE(physical_fault)"
            ),

        "consistency_loss":
            "none",

        "scientific_question":
            (
                "Does explicit modality reliability improve "
                "physical-fault robustness and generalization?"
            ),
    },

    {
        "candidate_id":
            "V26C_DualGateLiteCons",

        "role":
            "consistency ablation",

        "architecture":
            (
                "exactly V26B_DualGateLite"
            ),

        "training_loss":
            (
                "CE(clean) + 1.0*CE(physical_fault) + "
                "0.20*symmetric_KL(clean,fault)"
            ),

        "consistency_scope":
            (
                "recoverable physical training faults only"
            ),

        "scientific_question":
            (
                "Does explicit prediction consistency add "
                "benefit beyond physical corrupted-gradient CE?"
            ),
    },

    {
        "candidate_id":
            "V26D_DualGateCross",

        "role":
            "cross-modal interaction candidate",

        "architecture":
            (
                "same branches and reliability gates as V26B"
            ),

        "fusion":
            (
                "concat(r_acc*h_acc, "
                "r_gyro*h_gyro, "
                "abs(h_acc-h_gyro), "
                "h_acc*h_gyro) => 192 dims"
            ),

        "classifier":
            (
                "Linear(192,64)+SiLU+Dropout(0.10)+"
                "Linear(64,num_classes)"
            ),

        "training_loss":
            (
                "CE(clean) + 1.0*CE(physical_fault) + "
                "0.20*symmetric_KL(clean,fault)"
            ),

        "consistency_scope":
            (
                "recoverable physical training faults only"
            ),

        "scientific_question":
            (
                "Does lightweight cross-modal interaction "
                "improve recovery when one modality degrades?"
            ),
    },
]


write_json(
    OUT
    / "candidate_architectures_r1.json",
    candidates,
)


with (
    OUT
    / "candidate_manifest_r1.csv"
).open(
    "w",
    newline="",
    encoding="utf-8",
) as f:

    fields = [
        "candidate_id",
        "role",
        "architecture",
        "training_loss",
        "scientific_question",
    ]

    writer = csv.DictWriter(
        f,
        fieldnames=fields,
        extrasaction="ignore",
    )

    writer.writeheader()
    writer.writerows(
        candidates
    )


print(
    "CANDIDATE_ARCHITECTURES_FROZEN_4_OF_4=True"
)


# ============================================================
# 6. Training protocol
# ============================================================

training_protocol = {
    "input_representation":
        (
            "pre-normalization sensor-domain "
            "model-window representation"
        ),

    "raw_to_model_pipeline": (
        "raw model-window -> optional physical corruption -> "
        "frozen train-only normalization -> model"
    ),

    "clean_and_fault_pair_per_training_batch":
        True,

    "fault_family_sampling":
        "uniform over six recoverable families",

    "same_ground_truth_label_for_clean_and_fault":
        True,

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

    "checkpoint_selection_data":
        "validation only",

    "test_forward_during_candidate_development":
        False,

    "training_seeds":
        DEVELOPMENT_SEEDS,

    "development_datasets":
        DEVELOPMENT_DATASETS,

    "development_runs_per_candidate":
        6,

    "candidate_count":
        4,

    "maximum_screening_training_runs":
        24,

    "mixed_precision":
        False,

    "all_sensors_failure_training":
        False,

    "reason_all_sensors_failure_excluded":
        (
            "With both modalities absent the label is generally "
            "not recoverable from sensor evidence; retain it as "
            "a final stress condition rather than teach class "
            "priors during robust training."
        ),
}


write_json(
    OUT
    / "training_protocol_r1.json",
    training_protocol,
)


print(
    "TRAINING_PROTOCOL_FROZEN=True"
)


# ============================================================
# 7. Validation protocol
#
# Exact Stage25 test tensors are NOT reused.
# Separate development stochastic root.
# ============================================================

validation_protocol = {
    "domain":
        "pre_normalization_sensor_domain",

    "datasets":
        DEVELOPMENT_DATASETS,

    "seeds":
        DEVELOPMENT_SEEDS,

    "index_split":
        "val_idx only",

    "fault_families":
        6,

    "recoverable_conditions":
        16,

    "all_sensors_failure_in_selection":
        False,

    "validation_fault_definition":
        (
            "same semantic fault families as Stage25, "
            "applied to validation windows only"
        ),

    "stochastic_root_seed":
        26001,

    "relationship_to_stage25_test_randomness":
        "independent",

    "primary_checkpoint_metric":
        (
            "0.50*family_balanced_macro_f1 + "
            "0.30*all_recoverable_fault_macro_f1 + "
            "0.20*clean_macro_f1"
        ),

    "clean_accuracy_used_for_checkpoint_selection":
        False,

    "test_metrics_visible_during_screening":
        False,
}


write_json(
    OUT
    / "validation_protocol_r1.json",
    validation_protocol,
)


print(
    "VALIDATION_SELECTION_PROTOCOL_FROZEN=True"
)


# ============================================================
# 8. Candidate promotion rule
#
# Frozen BEFORE training.
# ============================================================

selection_rule = {
    "baseline":
        "frozen ReliabilityCNN_v25",

    "comparison_scope":
        (
            "UCI_HAR + DSADS validation only, "
            "seeds 42/123/456"
        ),

    "minimum_requirements": {
        "parameter_count_max":
            60000,

        "mean_clean_macro_f1_delta_vs_v25_min":
            -0.015,

        "mean_family_balanced_macro_f1_delta_vs_v25_min":
            0.015,

        "mean_all_recoverable_fault_macro_f1_delta_vs_v25_min":
            0.010,
    },

    "primary_candidate_order":
        (
            "highest mean validation checkpoint-selection "
            "score across the six development runs"
        ),

    "tie_definition":
        (
            "absolute primary-score difference < 0.002"
        ),

    "tie_breaker":
        "lower parameter count",

    "if_no_candidate_meets_minimum_requirements":
        (
            "PROMOTE_NONE. Freeze negative development result "
            "and preregister a new development round before "
            "trying additional architectures."
        ),

    "test_set_use_before_candidate_freeze":
        False,

    "storm_use_before_candidate_freeze":
        False,
}


write_json(
    OUT
    / "candidate_promotion_rule_r1.json",
    selection_rule,
)


print(
    "CANDIDATE_PROMOTION_RULE_FROZEN=True"
)


# ============================================================
# 9. Efficiency constraints
# ============================================================

efficiency = {
    "parameter_hard_ceiling":
        60000,

    "desired_parameter_target":
        50000,

    "final_metrics_required": [
        "parameter_count",
        "checkpoint_size_MB",
        "CPU_batch1_latency_ms",
        "GPU_batch1_latency_ms",
        "GPU_batch64_throughput",
        "MACs_per_window",
    ],

    "final_claim_style":
        (
            "robustness-efficiency Pareto comparison; "
            "do not claim deployment solely from static metrics"
        ),

    "latency_used_during_candidate_screening":
        False,

    "parameter_count_used_during_candidate_screening":
        True,
}


write_json(
    OUT
    / "efficiency_constraints_r1.json",
    efficiency,
)


print(
    "EFFICIENCY_CONSTRAINTS_FROZEN=True"
)


# ============================================================
# 10. Claim boundaries
# ============================================================

claim_policy = {
    "allowed_if_supported": [
        (
            "final candidate improves physical-domain "
            "robustness on the primary held-out stratum"
        ),
        (
            "modality-aware reliability improves specific "
            "fault-family robustness if ablations support it"
        ),
        (
            "physical-domain corrupted-gradient training "
            "improves robustness if V26A supports it"
        ),
        (
            "final model offers a stronger "
            "robustness-efficiency trade-off if Pareto "
            "analysis supports it"
        ),
    ],

    "forbidden_without_new_evidence": [
        "universal SOTA",
        "universal superiority",
        "equivalence from non-significant n=5 tests",
        "deployment readiness",
        "V25 beats STORM",
        "new model beats STORM before final external evaluation",
    ],

    "stage25_results_are_frozen_and_not_tunable":
        True,

    "storm_is_external_evidence_not_development_target":
        True,
}


write_json(
    OUT
    / "claim_policy_r1.json",
    claim_policy,
)


# ============================================================
# 11. Final protocol receipt
# ============================================================

protocol_receipt = {
    "protocol":
        "V26_ROBUST_MODEL_DEVELOPMENT_PROTOCOL_R1",

    "status":
        "FROZEN_BEFORE_NEW_MODEL_TRAINING",

    "scientific_parent":
        "STAGE25_R6",

    "r6_sha256sums_sha256":
        R6_EXPECTED_SHA,

    "development_datasets":
        DEVELOPMENT_DATASETS,

    "development_seeds":
        DEVELOPMENT_SEEDS,

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

    "modality_aware_candidates_present":
        True,

    "independent_validation_fault_randomness":
        True,

    "parameter_hard_ceiling":
        60000,

    "promotion_requires_robustness_improvement":
        True,

    "promotion_can_fail":
        True,

    "primary_confirmation_checkpoint_count":
        14,

    "all20_final_summary_primary":
        False,

    "model_training_performed":
        False,

    "model_forward_performed":
        False,

    "test_inference_performed":
        False,

    "storm_inference_performed":
        False,

    "checkpoint_modified":
        False,

    "dataset_modified":
        False,

    "next_stage":
        (
            "V26 implementation integrity audit: implement "
            "four frozen candidates, physical training-fault "
            "operator, validation evaluator, parameter-count "
            "gate, and unit tests before first training run."
        ),
}


write_json(
    OUT
    / "v26_development_protocol_receipt_r1.json",
    protocol_receipt,
)


print()
print("=" * 118)
print("V26 DEVELOPMENT PROTOCOL FINAL RECEIPT")
print("=" * 118)

print(
    json.dumps(
        protocol_receipt,
        indent=2,
    )
)


print()
print(
    "V26_DEVELOPMENT_PROTOCOL_R1_FROZEN=True"
)

print(
    "DEVELOPMENT_DATASETS=UCI_HAR,DSADS"
)

print(
    "DEVELOPMENT_SEEDS=42,123,456"
)

print(
    "CANDIDATE_COUNT=4"
)

print(
    "MAXIMUM_SCREENING_RUNS=24"
)

print(
    "TEST_INFERENCE_PERFORMED=False"
)

print(
    "MODEL_TRAINING_PERFORMED=False"
)

print(
    "MODEL_FORWARD_PERFORMED=False"
)

print(
    "STORM_USED_FOR_SELECTION=False"
)
