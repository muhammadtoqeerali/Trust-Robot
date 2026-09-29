#!/usr/bin/env python3

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import os
import platform
import shutil

import joblib
import numpy as np
import sklearn

from trust_robot.lidar_noise_sensitive_diagnostics import (
    NOISE_SENSITIVE_FEATURE_NAMES,
)

from trust_robot.ml_lidar_extended_13_feature_multidegradation_baseline import (
    DEGRADATION_FAMILIES,
    FEATURE_NAMES,
    MODEL_NAMES,
    RESULT_SCHEMA,
    assert_exact_parent_pairing,
    binary_metrics,
    build_models,
    fit_with_binary_class_weights,
    load_extended_dataset,
    load_parent_five_feature_index,
    per_family_metrics,
    per_family_univariate_report,
    per_trajectory_metrics,
    positive_probability,
    univariate_report,
    validate_config,
)


def file_sha(
    path: Path,
) -> str:
    digest = sha256()

    with path.open(
        "rb"
    ) as handle:
        for block in iter(
            lambda: handle.read(
                1024 * 1024
            ),
            b"",
        ):
            digest.update(block)

    return digest.hexdigest()


def metric_deltas(
    old,
    new,
):
    result = {}

    for name in (
        "balanced_accuracy",
        "precision",
        "recall",
        "f1",
        "roc_auc",
        "average_precision",
        "brier_score",
    ):
        result[name] = (
            float(
                new[name]
            )
            - float(
                old[name]
            )
        )

    return result


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--config",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--extended-train",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--extended-check",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--parent-train",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--parent-check",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--five-feature-results",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
    )

    args = parser.parse_args()

    config_path = (
        args.config.resolve()
    )

    train_path = (
        args.extended_train.resolve()
    )

    check_path = (
        args.extended_check.resolve()
    )

    parent_train = (
        args.parent_train.resolve()
    )

    parent_check = (
        args.parent_check.resolve()
    )

    five_results_path = (
        args.five_feature_results.resolve()
    )

    output_dir = (
        args.output_dir.resolve()
    )

    config = json.loads(
        config_path.read_text(
            encoding="utf-8"
        )
    )

    validate_config(
        config
    )

    expected_extended = config[
        "extended_dataset"
    ]

    expected_parent = config[
        "parent_five_feature_dataset"
    ]

    expected_five = config[
        "frozen_five_feature_baseline"
    ]

    if file_sha(
        train_path
    ) != expected_extended[
        "development_train_sha256"
    ]:
        raise RuntimeError(
            "extended train hash mismatch"
        )

    if file_sha(
        check_path
    ) != expected_extended[
        "development_check_sha256"
    ]:
        raise RuntimeError(
            "extended check hash mismatch"
        )

    if file_sha(
        parent_train
    ) != expected_parent[
        "development_train_sha256"
    ]:
        raise RuntimeError(
            "parent train hash mismatch"
        )

    if file_sha(
        parent_check
    ) != expected_parent[
        "development_check_sha256"
    ]:
        raise RuntimeError(
            "parent check hash mismatch"
        )

    if file_sha(
        five_results_path
    ) != expected_five[
        "results_sha256"
    ]:
        raise RuntimeError(
            "frozen five-feature results hash mismatch"
        )

    train = load_extended_dataset(
        train_path,
        expected_partition=
            "development_train",
    )

    check = load_extended_dataset(
        check_path,
        expected_partition=
            "development_check",
    )

    if train.X.shape != (
        3400,
        13,
    ):
        raise RuntimeError(
            "extended train shape mismatch"
        )

    if check.X.shape != (
        1000,
        13,
    ):
        raise RuntimeError(
            "extended check shape mismatch"
        )

    if int(
        np.sum(
            train.y == 0
        )
    ) != 850:
        raise RuntimeError(
            "extended train clean count mismatch"
        )

    if int(
        np.sum(
            train.y == 1
        )
    ) != 2550:
        raise RuntimeError(
            "extended train degraded count mismatch"
        )

    if int(
        np.sum(
            check.y == 0
        )
    ) != 250:
        raise RuntimeError(
            "extended check clean count mismatch"
        )

    if int(
        np.sum(
            check.y == 1
        )
    ) != 750:
        raise RuntimeError(
            "extended check degraded count mismatch"
        )

    parent_index = (
        load_parent_five_feature_index(
            parent_train,
            parent_check,
        )
    )

    if len(
        parent_index
    ) != 4400:
        raise RuntimeError(
            "parent semantic sample count mismatch"
        )

    assert_exact_parent_pairing(
        train,
        parent_index,
    )

    assert_exact_parent_pairing(
        check,
        parent_index,
    )

    if set(
        train.sample_ids
    ) & set(
        check.sample_ids
    ):
        raise RuntimeError(
            "sample identity leakage"
        )

    if set(
        train.trajectories
    ) & set(
        check.trajectories
    ):
        raise RuntimeError(
            "trajectory leakage"
        )

    if set(
        train.window_keys
    ) & set(
        check.window_keys
    ):
        raise RuntimeError(
            "window leakage"
        )

    if len(
        set(
            train.window_keys
        )
    ) != 850:
        raise RuntimeError(
            "train window count mismatch"
        )

    if len(
        set(
            check.window_keys
        )
    ) != 250:
        raise RuntimeError(
            "check window count mismatch"
        )

    five_results = json.loads(
        five_results_path.read_text(
            encoding="utf-8"
        )
    )

    if five_results[
        "model_selection"
    ][
        "executed"
    ] is not False:
        raise RuntimeError(
            "five-feature baseline selection state changed"
        )

    if output_dir.exists():
        raise RuntimeError(
            "output directory already exists"
        )

    staging = output_dir.with_name(
        "."
        + output_dir.name
        + ".partial"
    )

    if staging.exists():
        raise RuntimeError(
            "staging directory already exists"
        )

    staging.mkdir(
        parents=True,
        exist_ok=False,
    )

    try:
        check_univariate = (
            univariate_report(
                check
            )
        )

        check_per_family_univariate = (
            per_family_univariate_report(
                check
            )
        )

        results = {
            "schema":
                RESULT_SCHEMA,

            "schema_version":
                1,

            "task":
                "paired_5_feature_vs_13_feature_representation_ablation",

            "pairing": {
                "same_semantic_samples":
                    True,

                "same_sample_ids":
                    True,

                "same_labels":
                    True,

                "same_windows":
                    True,

                "same_trajectory_split":
                    True,

                "legacy_first_five_features_reproduce_parent":
                    True,

                "parent_sample_count":
                    4400,
            },

            "dataset": {
                "development_train_samples":
                    3400,

                "development_train_windows":
                    850,

                "development_train_trajectories":
                    17,

                "development_check_samples":
                    1000,

                "development_check_windows":
                    250,

                "development_check_trajectories":
                    5,

                "feature_count":
                    13,

                "legacy_feature_count":
                    5,

                "new_residual_feature_count":
                    8,

                "feature_names":
                    list(
                        FEATURE_NAMES
                    ),

                "trajectory_overlap_count":
                    0,

                "window_overlap_count":
                    0,

                "sample_id_overlap_count":
                    0,
            },

            "environment": {
                "python":
                    platform.python_version(),

                "numpy":
                    np.__version__,

                "scikit_learn":
                    sklearn.__version__,

                "joblib":
                    joblib.__version__,
            },

            "univariate_feature_report": {
                "development_check_overall_binary":
                    check_univariate,

                "development_check_per_family":
                    check_per_family_univariate,

                "used_for_feature_selection":
                    False,

                "used_for_model_selection":
                    False,
            },

            "models":
                {},

            "paired_comparison_to_frozen_5_feature_baseline":
                {},

            "model_selection": {
                "executed":
                    False,

                "selected_model":
                    None,

                "reason":
                    (
                        "This is a fixed paired feature-representation "
                        "development comparison, not final model selection."
                    ),
            },

            "scientific_boundary": {
                "synthetic_intervention_truth":
                    True,

                "real_physical_health_truth":
                    False,

                "real_health_label_count":
                    0,

                "final_health_model_training":
                    False,

                "final_health_model_selected":
                    False,

                "VALIDATION_open":
                    False,

                "CONFIRMATION_open":
                    False,

                "reference_data_used":
                    False,

                "ATE_RPE":
                    False,
            },

            "created_utc":
                datetime.now(
                    timezone.utc
                ).isoformat(
                    timespec="seconds"
                ).replace(
                    "+00:00",
                    "Z",
                ),
        }

        models = build_models()

        if tuple(
            models.keys()
        ) != MODEL_NAMES:
            raise RuntimeError(
                "frozen model-family order changed"
            )

        for model_name in MODEL_NAMES:
            model = models[
                model_name
            ]

            print(
                "FIT_BEGIN="
                + model_name,
                flush=True,
            )

            fit_with_binary_class_weights(
                model,
                train.X,
                train.y,
            )

            print(
                "FIT_COMPLETE="
                + model_name,
                flush=True,
            )

            train_probability = (
                positive_probability(
                    model,
                    train.X,
                )
            )

            check_probability = (
                positive_probability(
                    model,
                    check.X,
                )
            )

            train_metrics = binary_metrics(
                train.y,
                train_probability,
            )

            check_metrics = binary_metrics(
                check.y,
                check_probability,
            )

            family_metrics = (
                per_family_metrics(
                    check,
                    check_probability,
                )
            )

            trajectory_metrics = (
                per_trajectory_metrics(
                    check,
                    check_probability,
                )
            )

            model_path = (
                staging
                / (
                    model_name
                    + ".joblib"
                )
            )

            prediction_path = (
                staging
                / (
                    model_name
                    + "_development_check_predictions.npz"
                )
            )

            joblib.dump(
                model,
                model_path,
                compress=3,
            )

            np.savez_compressed(
                prediction_path,

                probability=
                    check_probability.astype(
                        np.float64
                    ),

                predicted_label=
                    (
                        check_probability
                        >= 0.5
                    ).astype(
                        np.int8
                    ),

                true_label=
                    check.y.astype(
                        np.int8
                    ),
            )

            results[
                "models"
            ][
                model_name
            ] = {
                "representation":
                    "13_features",

                "fit_partition":
                    "development_train",

                "evaluation_partition":
                    "development_check",

                "train_metrics":
                    train_metrics,

                "development_check_metrics":
                    check_metrics,

                "development_check_per_family":
                    family_metrics,

                "development_check_per_trajectory":
                    trajectory_metrics,

                "model_artifact":
                    model_path.name,

                "model_artifact_sha256":
                    file_sha(
                        model_path
                    ),

                "prediction_artifact":
                    prediction_path.name,

                "prediction_artifact_sha256":
                    file_sha(
                        prediction_path
                    ),

                "hyperparameter_search_executed":
                    False,

                "final_health_model_selected":
                    False,
            }

            old_model = five_results[
                "models"
            ][
                model_name
            ]

            comparison = {
                "five_feature_development_check_metrics":
                    old_model[
                        "development_check_metrics"
                    ],

                "thirteen_feature_development_check_metrics":
                    check_metrics,

                "thirteen_minus_five_overall_metric_delta":
                    metric_deltas(
                        old_model[
                            "development_check_metrics"
                        ],
                        check_metrics,
                    ),

                "per_family":
                    {},
            }

            for family in (
                DEGRADATION_FAMILIES
            ):
                old_family = old_model[
                    "development_check_per_family"
                ][
                    family
                ]

                new_family = family_metrics[
                    family
                ]

                comparison[
                    "per_family"
                ][
                    family
                ] = {
                    "five_feature":
                        old_family,

                    "thirteen_feature":
                        new_family,

                    "thirteen_minus_five_delta":
                        metric_deltas(
                            old_family,
                            new_family,
                        ),
                }

            results[
                "paired_comparison_to_frozen_5_feature_baseline"
            ][
                model_name
            ] = comparison

            print(
                "MODEL="
                + model_name
                + " 13f_train_BA="
                + f"{train_metrics['balanced_accuracy']:.9f}"
                + " 13f_check_BA="
                + f"{check_metrics['balanced_accuracy']:.9f}"
                + " 13f_check_F1="
                + f"{check_metrics['f1']:.9f}"
                + " 13f_check_AUC="
                + f"{check_metrics['roc_auc']:.9f}"
                + " 13f_check_AP="
                + f"{check_metrics['average_precision']:.9f}",
                flush=True,
            )

            old_overall = old_model[
                "development_check_metrics"
            ]

            print(
                "PAIRED_OVERALL="
                + model_name
                + " five_BA="
                + f"{old_overall['balanced_accuracy']:.9f}"
                + " thirteen_BA="
                + f"{check_metrics['balanced_accuracy']:.9f}"
                + " delta_BA="
                + f"{check_metrics['balanced_accuracy'] - old_overall['balanced_accuracy']:+.9f}"
                + " five_AUC="
                + f"{old_overall['roc_auc']:.9f}"
                + " thirteen_AUC="
                + f"{check_metrics['roc_auc']:.9f}"
                + " delta_AUC="
                + f"{check_metrics['roc_auc'] - old_overall['roc_auc']:+.9f}",
                flush=True,
            )

            for family in (
                DEGRADATION_FAMILIES
            ):
                old_family = old_model[
                    "development_check_per_family"
                ][
                    family
                ]

                new_family = family_metrics[
                    family
                ]

                print(
                    "PAIRED_FAMILY="
                    + family
                    + " MODEL="
                    + model_name
                    + " five_recall="
                    + f"{old_family['recall']:.9f}"
                    + " thirteen_recall="
                    + f"{new_family['recall']:.9f}"
                    + " delta_recall="
                    + f"{new_family['recall'] - old_family['recall']:+.9f}"
                    + " five_AUC="
                    + f"{old_family['roc_auc']:.9f}"
                    + " thirteen_AUC="
                    + f"{new_family['roc_auc']:.9f}"
                    + " delta_AUC="
                    + f"{new_family['roc_auc'] - old_family['roc_auc']:+.9f}",
                    flush=True,
                )

        results_path = (
            staging
            / "baseline_results.json"
        )

        results_path.write_text(
            json.dumps(
                results,
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

        manifest = {
            "schema":
                "TRUST_ROBOT_M2DGR_LIDAR_EXTENDED_13_FEATURE_MULTIDEGRADATION_BASELINE_RUN_V1",

            "schema_version":
                1,

            "baseline_results_sha256":
                file_sha(
                    results_path
                ),

            "model_fit_count":
                3,

            "representation":
                "13_features",

            "paired_to_frozen_5_feature_population":
                True,

            "models": {
                model_name: {
                    "model_sha256":
                        results[
                            "models"
                        ][
                            model_name
                        ][
                            "model_artifact_sha256"
                        ],

                    "prediction_sha256":
                        results[
                            "models"
                        ][
                            model_name
                        ][
                            "prediction_artifact_sha256"
                        ],
                }
                for model_name
                in MODEL_NAMES
            },

            "scientific_boundary": {
                "real_health_truth":
                    False,

                "final_health_model_selected":
                    False,

                "VALIDATION_open":
                    False,

                "CONFIRMATION_open":
                    False,
            },
        }

        manifest_path = (
            staging
            / "run_manifest.json"
        )

        manifest_path.write_text(
            json.dumps(
                manifest,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        success = {
            "schema":
                "TRUST_ROBOT_M2DGR_LIDAR_EXTENDED_13_FEATURE_MULTIDEGRADATION_BASELINE_SUCCESS_V1",

            "baseline_results_sha256":
                file_sha(
                    results_path
                ),

            "run_manifest_sha256":
                file_sha(
                    manifest_path
                ),

            "model_fit_count":
                3,

            "feature_count":
                13,

            "sample_count":
                4400,

            "paired_parent_population_changed":
                False,

            "hyperparameter_search_executed":
                False,

            "model_family_selection_executed":
                False,

            "real_health_truth":
                False,

            "final_health_model_selected":
                False,

            "complete":
                True,
        }

        (
            staging
            / "SUCCESS.json"
        ).write_text(
            json.dumps(
                success,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        os.replace(
            staging,
            output_dir,
        )

    except Exception:
        if staging.exists():
            shutil.rmtree(
                staging
            )

        raise

    print(
        "paired_13_feature_baseline=PASS"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
