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

from trust_robot.ml_lidar_event_gap_baseline import (
    DEVELOPMENT_CHECK,
    DEVELOPMENT_TRAIN,
    FEATURE_NAMES,
    MODEL_NAMES,
    RESULT_SCHEMA,
    binary_metrics,
    build_models,
    content_sha256,
    load_dataset,
    per_trajectory_metrics,
    positive_probability,
    validate_config,
)


def sha256_file(
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
            digest.update(
                block
            )

    return digest.hexdigest()


def univariate_report(
    X: np.ndarray,
    y: np.ndarray,
) -> dict:
    result = {}

    for index, name in enumerate(
        FEATURE_NAMES
    ):
        raw_auc = float(
            roc_auc_score(
                y,
                X[
                    :,
                    index
                ],
            )
        )

        result[
            name
        ] = {
            "raw_direction_roc_auc":
                raw_auc,

            "direction_agnostic_roc_auc":
                max(
                    raw_auc,
                    1.0 - raw_auc,
                ),
        }

    return result


def main() -> int:
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

    config_path = (
        args.config.resolve()
    )

    train_path = (
        args.development_train.resolve()
    )

    check_path = (
        args.development_check.resolve()
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

    source = config[
        "source_dataset"
    ]

    if sha256_file(
        train_path
    ) != source[
        "development_train_file_sha256"
    ]:
        raise RuntimeError(
            "development-train hash mismatch"
        )

    if sha256_file(
        check_path
    ) != source[
        "development_check_file_sha256"
    ]:
        raise RuntimeError(
            "development-check hash mismatch"
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
            "development-train matrix shape mismatch"
        )

    if check.X.shape != (
        1000,
        5,
    ):
        raise RuntimeError(
            "development-check matrix shape mismatch"
        )

    train_trajectory_set = set(
        train.trajectories
    )

    check_trajectory_set = set(
        check.trajectories
    )

    if train_trajectory_set != set(
        DEVELOPMENT_TRAIN
    ):
        raise RuntimeError(
            "development-train trajectory set mismatch"
        )

    if check_trajectory_set != set(
        DEVELOPMENT_CHECK
    ):
        raise RuntimeError(
            "development-check trajectory set mismatch"
        )

    if train_trajectory_set & check_trajectory_set:
        raise RuntimeError(
            "trajectory leakage detected"
        )

    train_window_set = set(
        train.window_fingerprints
    )

    check_window_set = set(
        check.window_fingerprints
    )

    if train_window_set & check_window_set:
        raise RuntimeError(
            "window fingerprint leakage detected"
        )

    if len(
        train_window_set
    ) != 1700:
        raise RuntimeError(
            "development-train unique window count mismatch"
        )

    if len(
        check_window_set
    ) != 500:
        raise RuntimeError(
            "development-check unique window count mismatch"
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
        results = {
            "schema":
                RESULT_SCHEMA,

            "schema_version":
                1,

            "task":
                "synthetic_EVENT_GAP_registration_diagnostic_discrimination",

            "source": {
                "development_train_file":
                    str(
                        train_path
                    ),

                "development_train_sha256":
                    sha256_file(
                        train_path
                    ),

                "development_check_file":
                    str(
                        check_path
                    ),

                "development_check_sha256":
                    sha256_file(
                        check_path
                    ),

                "config_file":
                    str(
                        config_path
                    ),

                "config_file_sha256":
                    sha256_file(
                        config_path
                    ),

                "config_content_sha256":
                    config[
                        "content_sha256"
                    ],
            },

            "dataset": {
                "development_train_samples":
                    int(
                        train.y.size
                    ),

                "development_check_samples":
                    int(
                        check.y.size
                    ),

                "development_train_unique_windows":
                    len(
                        train_window_set
                    ),

                "development_check_unique_windows":
                    len(
                        check_window_set
                    ),

                "trajectory_overlap_count":
                    0,

                "window_fingerprint_overlap_count":
                    0,

                "feature_names":
                    list(
                        FEATURE_NAMES
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
                "development_train":
                    univariate_report(
                        train.X,
                        train.y,
                    ),

                "development_check":
                    univariate_report(
                        check.X,
                        check.y,
                    ),

                "used_for_model_selection":
                    False,

                "used_for_hyperparameter_selection":
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
                        "Fixed candidate models are reported only. "
                        "Synthetic EVENT_GAP discrimination is not sufficient "
                        "to select the final physical health model."
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
                "model ordering changed"
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

            model.fit(
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

            train_metrics = (
                binary_metrics(
                    train.y,
                    train_probability,
                )
            )

            check_metrics = (
                binary_metrics(
                    check.y,
                    check_probability,
                )
            )

            check_per_trajectory = (
                per_trajectory_metrics(
                    check.y,
                    check_probability,
                    check.trajectories,
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

                "fit_sample_count":
                    int(
                        train.y.size
                    ),

                "evaluation_sample_count":
                    int(
                        check.y.size
                    ),

                "train_metrics":
                    train_metrics,

                "development_check_metrics":
                    check_metrics,

                "development_check_per_trajectory":
                    check_per_trajectory,

                "model_artifact":
                    model_path.name,

                "model_artifact_sha256":
                    sha256_file(
                        model_path
                    ),

                "prediction_artifact":
                    prediction_path.name,

                "prediction_artifact_sha256":
                    sha256_file(
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
                "TRUST_ROBOT_M2DGR_LIDAR_EVENT_GAP_BASELINE_RUN_MANIFEST_V1",

            "schema_version":
                1,

            "baseline_results_sha256":
                sha256_file(
                    results_path
                ),

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
                "model_fit_executed":
                    True,

                "model_fit_count":
                    3,

                "synthetic_EVENT_GAP_benchmark":
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
                "TRUST_ROBOT_M2DGR_LIDAR_EVENT_GAP_BASELINE_SUCCESS_V1",

            "baseline_results_sha256":
                sha256_file(
                    results_path
                ),

            "run_manifest_sha256":
                sha256_file(
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
            shutil.rmtree(
                staging
            )

        raise

    print(
        "hard_baseline_output="
        + str(
            output_dir
        )
    )

    print("model_fit_count=3")
    print("hyperparameter_search_executed=false")
    print("final_health_model_selected=false")
    print("real_health_truth=false")
    print("hard_EVENT_GAP_baseline=PASS")

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
