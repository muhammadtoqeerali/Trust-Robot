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
from sklearn.metrics import roc_auc_score

from trust_robot.ml_lidar_point_level_multidegradation_baseline import (
    DEGRADATION_FAMILIES,
    FEATURE_NAMES,
    MODEL_NAMES,
    RESULT_SCHEMA,
    binary_metrics,
    build_models,
    content_sha256,
    fit_with_binary_class_weights,
    load_dataset,
    per_family_metrics,
    per_trajectory_metrics,
    positive_probability,
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


def univariate_report(
    X,
    y,
):
    result = {}

    for index, name in enumerate(
        FEATURE_NAMES
    ):
        raw_auc = float(
            roc_auc_score(
                y,
                X[:, index],
            )
        )

        result[name] = {
            "raw_direction_roc_auc":
                raw_auc,

            "direction_agnostic_roc_auc":
                max(
                    raw_auc,
                    1.0 - raw_auc,
                ),
        }

    return result


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--config",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--development-train",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--development-check",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
    )

    args = parser.parse_args()

    config_path = args.config.resolve()
    train_path = args.development_train.resolve()
    check_path = args.development_check.resolve()
    output_dir = args.output_dir.resolve()

    config = json.loads(
        config_path.read_text(
            encoding="utf-8"
        )
    )

    validate_config(config)

    source = config[
        "source_dataset"
    ]

    if file_sha(
        train_path
    ) != source[
        "development_train_sha256"
    ]:
        raise RuntimeError(
            "development_train hash mismatch"
        )

    if file_sha(
        check_path
    ) != source[
        "development_check_sha256"
    ]:
        raise RuntimeError(
            "development_check hash mismatch"
        )

    train = load_dataset(
        train_path,
        expected_partition=
            "development_train",
    )

    check = load_dataset(
        check_path,
        expected_partition=
            "development_check",
    )

    if train.X.shape != (
        3400,
        5,
    ):
        raise RuntimeError(
            "train matrix shape mismatch"
        )

    if check.X.shape != (
        1000,
        5,
    ):
        raise RuntimeError(
            "check matrix shape mismatch"
        )

    if int(
        np.sum(
            train.y == 0
        )
    ) != 850:
        raise RuntimeError(
            "train clean count mismatch"
        )

    if int(
        np.sum(
            train.y == 1
        )
    ) != 2550:
        raise RuntimeError(
            "train degraded count mismatch"
        )

    if int(
        np.sum(
            check.y == 0
        )
    ) != 250:
        raise RuntimeError(
            "check clean count mismatch"
        )

    if int(
        np.sum(
            check.y == 1
        )
    ) != 750:
        raise RuntimeError(
            "check degraded count mismatch"
        )

    train_trajectories = set(
        train.trajectories
    )

    check_trajectories = set(
        check.trajectories
    )

    if train_trajectories & check_trajectories:
        raise RuntimeError(
            "trajectory leakage"
        )

    train_windows = set(
        train.window_keys
    )

    check_windows = set(
        check.window_keys
    )

    if train_windows & check_windows:
        raise RuntimeError(
            "window leakage"
        )

    if len(
        train_windows
    ) != 850:
        raise RuntimeError(
            "train window count mismatch"
        )

    if len(
        check_windows
    ) != 250:
        raise RuntimeError(
            "check window count mismatch"
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
            "staging directory exists"
        )

    staging.mkdir(
        parents=True,
        exist_ok=False,
    )

    try:
        results = {
            "schema":
                RESULT_SCHEMA,

            "schema_version":
                1,

            "task":
                "binary_clean_vs_point_level_synthetic_degraded",

            "source": {
                "development_train_sha256":
                    file_sha(
                        train_path
                    ),

                "development_check_sha256":
                    file_sha(
                        check_path
                    ),

                "config_file_sha256":
                    file_sha(
                        config_path
                    ),

                "config_content_sha256":
                    config[
                        "content_sha256"
                    ],
            },

            "dataset": {
                "development_train_samples":
                    3400,

                "development_train_clean":
                    850,

                "development_train_degraded":
                    2550,

                "development_check_samples":
                    1000,

                "development_check_clean":
                    250,

                "development_check_degraded":
                    750,

                "development_train_windows":
                    850,

                "development_check_windows":
                    250,

                "trajectory_overlap_count":
                    0,

                "window_overlap_count":
                    0,

                "feature_names":
                    list(
                        FEATURE_NAMES
                    ),

                "degradation_families":
                    list(
                        DEGRADATION_FAMILIES
                    ),
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
                    univariate_report(
                        check.X,
                        check.y,
                    ),

                "used_for_model_selection":
                    False,
            },

            "models":
                {},

            "model_selection": {
                "executed":
                    False,

                "selected_model":
                    None,

                "reason":
                    (
                        "Fixed models are development baselines only. "
                        "No final TRUST-ROBOT health model is selected."
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
                "model order changed"
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

            joblib.dump(
                model,
                model_path,
                compress=3,
            )

            prediction_path = (
                staging
                / (
                    model_name
                    + "_development_check_predictions.npz"
                )
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
                "fit_partition":
                    "development_train",

                "evaluation_partition":
                    "development_check",

                "binary_class_weighting":
                    "balanced_training_sample_weights",

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

            print(
                "MODEL="
                + model_name
                + " train_balanced_accuracy="
                + f"{train_metrics['balanced_accuracy']:.9f}"
                + " check_balanced_accuracy="
                + f"{check_metrics['balanced_accuracy']:.9f}"
                + " check_f1="
                + f"{check_metrics['f1']:.9f}"
                + " check_roc_auc="
                + f"{check_metrics['roc_auc']:.9f}"
                + " check_average_precision="
                + f"{check_metrics['average_precision']:.9f}"
                + " check_brier="
                + f"{check_metrics['brier_score']:.9f}",
                flush=True,
            )

            for family in (
                DEGRADATION_FAMILIES
            ):
                metrics = family_metrics[
                    family
                ]

                print(
                    "FAMILY="
                    + family
                    + " MODEL="
                    + model_name
                    + " balanced_accuracy="
                    + f"{metrics['balanced_accuracy']:.9f}"
                    + " recall="
                    + f"{metrics['recall']:.9f}"
                    + " f1="
                    + f"{metrics['f1']:.9f}"
                    + " roc_auc="
                    + f"{metrics['roc_auc']:.9f}",
                    flush=True,
                )

        results[
            "content_sha256"
        ] = content_sha256(
            results
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
                "TRUST_ROBOT_M2DGR_LIDAR_POINT_LEVEL_MULTIDEGRADATION_BASELINE_RUN_V1",

            "schema_version":
                1,

            "baseline_results_sha256":
                file_sha(
                    results_path
                ),

            "model_fit_count":
                3,

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
                "synthetic_multidegradation_benchmark":
                    True,

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

        manifest[
            "content_sha256"
        ] = content_sha256(
            manifest
        )

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
                "TRUST_ROBOT_M2DGR_LIDAR_POINT_LEVEL_MULTIDEGRADATION_BASELINE_SUCCESS_V1",

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

            "development_train_samples":
                3400,

            "development_check_samples":
                1000,

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
            shutil.rmtree(staging)

        raise

    print(
        "multi_degradation_output="
        + str(output_dir)
    )

    print("model_fit_count=3")
    print("hyperparameter_search=false")
    print("model_family_selection=false")
    print("final_health_model_selected=false")
    print("real_health_truth=false")
    print("multi_degradation_baseline=PASS")

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
