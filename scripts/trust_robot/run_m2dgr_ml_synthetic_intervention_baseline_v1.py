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

from trust_robot.ml_synthetic_intervention_baseline import (
    MODEL_NAMES,
    PROBABILITY_THRESHOLD,
    RESULT_SCHEMA,
    build_models,
    build_result_contract,
    compute_binary_metrics,
    compute_per_trajectory_metrics,
    content_sha256,
    load_dataset,
    mechanism_signature_probability,
    predict_positive_probability,
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

    config_path = args.config.resolve()
    train_path = args.development_train.resolve()
    check_path = args.development_check.resolve()
    output_dir = args.output_dir.resolve()

    config = json.loads(
        config_path.read_text(
            encoding="utf-8"
        )
    )

    validate_config(
        config
    )

    expected = config[
        "source_dataset"
    ]

    if sha256_file(
        train_path
    ) != expected[
        "development_train_file_sha256"
    ]:
        raise RuntimeError(
            "development-train dataset hash mismatch"
        )

    if sha256_file(
        check_path
    ) != expected[
        "development_check_file_sha256"
    ]:
        raise RuntimeError(
            "development-check dataset hash mismatch"
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
        128790,
        10,
    ):
        raise RuntimeError(
            "development-train feature matrix shape mismatch"
        )

    if check.X.shape != (
        53150,
        10,
    ):
        raise RuntimeError(
            "development-check feature matrix shape mismatch"
        )

    if set(
        train.trajectories
    ) & set(
        check.trajectories
    ):
        raise RuntimeError(
            "trajectory leakage detected"
        )

    if output_dir.exists():
        raise RuntimeError(
            "baseline output directory already exists"
        )

    staging = output_dir.with_name(
        "."
        + output_dir.name
        + ".partial"
    )

    if staging.exists():
        raise RuntimeError(
            "baseline staging directory already exists"
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

            "result_contract":
                build_result_contract(),

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

                "baseline_config_file":
                    str(
                        config_path
                    ),

                "baseline_config_file_sha256":
                    sha256_file(
                        config_path
                    ),

                "baseline_config_content_sha256":
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

                "feature_count":
                    int(
                        train.X.shape[
                            1
                        ]
                    ),

                "development_train_trajectory_count":
                    len(
                        set(
                            train.trajectories
                        )
                    ),

                "development_check_trajectory_count":
                    len(
                        set(
                            check.trajectories
                        )
                    ),

                "trajectory_overlap_count":
                    len(
                        set(
                            train.trajectories
                        )
                        & set(
                            check.trajectories
                        )
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

            "mechanism_signature_baseline": {},

            "models": {},

            "model_selection": {
                "selected_final_model":
                    None,

                "selection_executed":
                    False,

                "reason":
                    (
                        "This run compares fixed development baselines only; "
                        "synthetic intervention performance cannot select the "
                        "final physical health model."
                    ),
            },

            "scientific_boundary": {
                "synthetic_intervention_benchmark":
                    True,

                "real_physical_health_truth":
                    False,

                "real_health_label_count":
                    0,

                "final_health_model_training":
                    False,

                "health_state_assignment":
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

        signature_probability = (
            mechanism_signature_probability(
                check.X
            )
        )

        signature_metrics = (
            compute_binary_metrics(
                check.y,
                signature_probability,
            )
        )

        signature_metrics[
            "per_trajectory"
        ] = compute_per_trajectory_metrics(
            check.y,
            signature_probability,
            check.trajectories,
        )

        results[
            "mechanism_signature_baseline"
        ] = {
            "definition":
                "all five current features exactly equal all five previous features",

            "metrics":
                signature_metrics,

            "model_fit_executed":
                False,

            "is_health_model":
                False,
        }

        print(
            "mechanism_signature_balanced_accuracy="
            + f"{signature_metrics['balanced_accuracy']:.9f}"
        )

        print(
            "mechanism_signature_f1="
            + f"{signature_metrics['f1']:.9f}"
        )

        models = build_models()

        if tuple(
            models.keys()
        ) != MODEL_NAMES:
            raise RuntimeError(
                "model ordering differs from frozen contract"
            )

        for model_name in MODEL_NAMES:
            model = models[
                model_name
            ]

            print(
                "FIT_BEGIN="
                + model_name
            )

            model.fit(
                train.X,
                train.y,
            )

            print(
                "FIT_COMPLETE="
                + model_name
            )

            train_probability = (
                predict_positive_probability(
                    model,
                    train.X,
                )
            )

            check_probability = (
                predict_positive_probability(
                    model,
                    check.X,
                )
            )

            train_metrics = (
                compute_binary_metrics(
                    train.y,
                    train_probability,
                )
            )

            check_metrics = (
                compute_binary_metrics(
                    check.y,
                    check_probability,
                )
            )

            per_trajectory = (
                compute_per_trajectory_metrics(
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

            predicted_label = (
                check_probability
                >= PROBABILITY_THRESHOLD
            ).astype(
                np.int8
            )

            np.savez_compressed(
                prediction_path,
                probability=
                    check_probability.astype(
                        np.float64
                    ),

                predicted_label=
                    predicted_label,

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

                "train_metrics":
                    train_metrics,

                "development_check_metrics":
                    check_metrics,

                "development_check_per_trajectory":
                    per_trajectory,

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
                + f"{check_metrics['brier_score']:.9f}"
            )

        results[
            "content_sha256"
        ] = content_sha256(
            results
        )

        result_path = (
            staging
            / "baseline_results.json"
        )

        result_path.write_text(
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
                "TRUST_ROBOT_M2DGR_SYNTHETIC_INTERVENTION_BASELINE_RUN_MANIFEST_V1",

            "schema_version":
                1,

            "baseline_results_file":
                "baseline_results.json",

            "baseline_results_sha256":
                sha256_file(
                    result_path
                ),

            "model_files": {
                model_name:
                    {
                        "file":
                            results[
                                "models"
                            ][
                                model_name
                            ][
                                "model_artifact"
                            ],

                        "sha256":
                            results[
                                "models"
                            ][
                                model_name
                            ][
                                "model_artifact_sha256"
                            ],
                    }
                for model_name
                in MODEL_NAMES
            },

            "prediction_files": {
                model_name:
                    {
                        "file":
                            results[
                                "models"
                            ][
                                model_name
                            ][
                                "prediction_artifact"
                            ],

                        "sha256":
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

                "fits_are_synthetic_development_benchmarks":
                    True,

                "final_health_model_training":
                    False,

                "real_health_truth":
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
                "TRUST_ROBOT_M2DGR_SYNTHETIC_INTERVENTION_BASELINE_SUCCESS_V1",

            "baseline_results_sha256":
                sha256_file(
                    result_path
                ),

            "run_manifest_sha256":
                sha256_file(
                    manifest_path
                ),

            "model_fit_count":
                len(
                    MODEL_NAMES
                ),

            "development_train_samples":
                int(
                    train.y.size
                ),

            "development_check_samples":
                int(
                    check.y.size
                ),

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
        "baseline_output_dir="
        + str(
            output_dir
        )
    )

    print(
        "model_fit_count=3"
    )

    print(
        "final_health_model_selected=false"
    )

    print(
        "real_health_truth=false"
    )

    print(
        "baseline_training_and_evaluation=PASS"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
