from __future__ import annotations

import argparse
import csv
import gc
import hashlib
import importlib.util
import json
import statistics
import sys
from pathlib import Path

import numpy as np
import torch


ROOT = Path(
    "/mnt/hdd16T/ToqeerHomeBackup/toqeer/IMU_Reliability"
)

EXP = (
    ROOT
    / "experiments"
    / "26_v26_robust_model_development"
)

R9C = (
    ROOT
    / "results"
    / "v26_external_storm_training_r9c"
)

STAGE24_SNAPSHOT = (
    ROOT
    / "results"
    / "v26_external_storm_test_protocol_r9d2"
    / "stage24_final_closure_source_snapshot.py"
)


if str(EXP) not in sys.path:
    sys.path.insert(
        0,
        str(EXP),
    )


from candidate_models_r2 import (
    create_v26_candidate,
    parameter_count,
)


CANDIDATE = "V26C_DualGateLiteCons"

NUM_CLASSES = 8

SEEDS = [
    42,
    123,
    456,
    789,
    2026,
]

EXPECTED_PARAMS = 23210


def sha256_file(path):

    h = hashlib.sha256()

    with Path(path).open(
        "rb"
    ) as f:

        for block in iter(
            lambda: f.read(
                1024 * 1024
            ),
            b"",
        ):
            h.update(
                block
            )

    return h.hexdigest()


def write_json(
    path,
    obj,
):

    path = Path(path)

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

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
            f"No rows for {path}"
        )

    path = Path(path)

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
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


def load_stage24():

    spec = importlib.util.spec_from_file_location(
        "stage24_frozen_patch2_for_v26_r9d2",
        STAGE24_SNAPSHOT,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            "Could not create frozen Stage24 import spec."
        )


    module = importlib.util.module_from_spec(
        spec
    )

    spec.loader.exec_module(
        module
    )


    required = [
        "load_test_and_normalization",
        "conditions",
        "paper_domain_transform",
        "metrics_from_predictions",
        "evaluate_model",
        "sha256_array",
    ]


    for name in required:

        if not hasattr(
            module,
            name,
        ):
            raise RuntimeError(
                f"Frozen Stage24 function missing: {name}"
            )


    return module


def load_manifest():

    path = (
        R9C
        / "external_v26c_checkpoint_manifest_5.csv"
    )


    with path.open(
        newline="",
        encoding="utf-8",
    ) as f:

        rows = list(
            csv.DictReader(f)
        )


    if len(rows) != 5:
        raise RuntimeError(
            f"Expected 5 checkpoint rows, "
            f"found {len(rows)}"
        )


    if {
        int(row["seed"])
        for row in rows
    } != set(SEEDS):

        raise RuntimeError(
            "External checkpoint seed set mismatch"
        )


    return sorted(
        rows,
        key=lambda row:
            SEEDS.index(
                int(
                    row["seed"]
                )
            ),
    )


def load_model(
    manifest_row,
    device,
):

    seed = int(
        manifest_row[
            "seed"
        ]
    )


    checkpoint = (
        ROOT
        / manifest_row[
            "checkpoint"
        ]
    )


    actual_sha = sha256_file(
        checkpoint
    )


    expected_sha = (
        manifest_row[
            "checkpoint_sha256"
        ]
    )


    if actual_sha != expected_sha:
        raise RuntimeError(
            f"Checkpoint SHA mismatch seed={seed}"
        )


    state = torch.load(
        checkpoint,
        map_location="cpu",
        weights_only=True,
    )


    if not isinstance(
        state,
        dict,
    ):
        raise RuntimeError(
            f"Seed {seed}: checkpoint not state dict"
        )


    model = create_v26_candidate(
        CANDIDATE,
        NUM_CLASSES,
        input_channels=6,
    )


    model.load_state_dict(
        state,
        strict=True,
    )


    params = parameter_count(
        model
    )


    if params != EXPECTED_PARAMS:
        raise RuntimeError(
            f"Seed {seed}: params={params} "
            f"!= {EXPECTED_PARAMS}"
        )


    model.eval()

    model.to(
        device
    )


    return model


def aggregate_seed(
    seed,
    case_rows,
):

    rows = [
        row
        for row in case_rows
        if int(
            row[
                "seed"
            ]
        )
        ==
        seed
    ]


    if len(rows) != 18:
        raise RuntimeError(
            f"seed={seed}: expected 18 cases, "
            f"found {len(rows)}"
        )


    baseline = [
        row
        for row in rows
        if row[
            "condition"
        ]
        ==
        "baseline"
    ]


    if len(baseline) != 1:
        raise RuntimeError(
            "Baseline count mismatch"
        )


    baseline = baseline[0]


    faults = [
        row
        for row in rows
        if row[
            "condition"
        ]
        !=
        "baseline"
    ]


    if len(faults) != 17:
        raise RuntimeError(
            "All-fault count != 17"
        )


    recoverable = [
        row
        for row in faults
        if row[
            "condition"
        ]
        !=
        "all_sensors_failure"
    ]


    if len(recoverable) != 16:
        raise RuntimeError(
            "Recoverable fault count != 16"
        )


    families = [
        "modality_outage",
        "single_axis_outage",
        "intermittent_dropout",
        "gaussian_noise",
        "stuck_value",
        "scale_drift",
    ]


    family_acc = []
    family_f1 = []


    for family in families:

        family_rows = [
            row
            for row in faults
            if row[
                "family"
            ]
            ==
            family
        ]


        if not family_rows:
            raise RuntimeError(
                f"No rows for family {family}"
            )


        family_acc.append(
            statistics.fmean(
                float(
                    row[
                        "accuracy"
                    ]
                )
                for row in family_rows
            )
        )


        family_f1.append(
            statistics.fmean(
                float(
                    row[
                        "macro_f1"
                    ]
                )
                for row in family_rows
            )
        )


    return {
        "seed":
            seed,

        "clean_accuracy":
            float(
                baseline[
                    "accuracy"
                ]
            ),

        "clean_macro_f1":
            float(
                baseline[
                    "macro_f1"
                ]
            ),

        "all_fault_accuracy":
            statistics.fmean(
                float(
                    row[
                        "accuracy"
                    ]
                )
                for row in faults
            ),

        "all_fault_macro_f1":
            statistics.fmean(
                float(
                    row[
                        "macro_f1"
                    ]
                )
                for row in faults
            ),

        "recoverable_fault_accuracy":
            statistics.fmean(
                float(
                    row[
                        "accuracy"
                    ]
                )
                for row in recoverable
            ),

        "recoverable_fault_macro_f1":
            statistics.fmean(
                float(
                    row[
                        "macro_f1"
                    ]
                )
                for row in recoverable
            ),

        "family_balanced_accuracy":
            statistics.fmean(
                family_acc
            ),

        "family_balanced_macro_f1":
            statistics.fmean(
                family_f1
            ),
    }


def run_smoke(
    out_dir,
    device,
):

    stage24 = load_stage24()

    conds = stage24.conditions()


    if len(conds) != 18:
        raise RuntimeError(
            f"Stage24 conditions={len(conds)} != 18"
        )


    expected_names = [
        "baseline",
        "gyro_total_failure",
        "acc_total_failure",
        "all_sensors_failure",

        "single_axis_failure_acc_x",
        "single_axis_failure_acc_y",
        "single_axis_failure_acc_z",
        "single_axis_failure_gyro_x",
        "single_axis_failure_gyro_y",
        "single_axis_failure_gyro_z",

        "acc_intermittent_30pct",
        "gyro_intermittent_30pct",

        "acc_noise_sigma0.5",
        "gyro_noise_sigma0.5",

        "acc_stuck_value",
        "gyro_stuck_value",

        "acc_scale_drift_2.0x",
        "gyro_scale_drift_2.0x",
    ]


    names = [
        condition[
            "name"
        ]
        for condition in conds
    ]


    if names != expected_names:
        raise RuntimeError(
            "Stage24 condition order/name mismatch"
        )


    rng = np.random.RandomState(
        99173
    )


    X = rng.normal(
        size=(
            16,
            64,
            6,
        )
    ).astype(
        np.float32
    )


    y = np.asarray(
        list(
            range(8)
        )
        *
        2,
        dtype=np.int64,
    )


    mu = np.asarray(
        [
            0.7,
            -1.1,
            0.3,
            0.05,
            -0.2,
            0.8,
        ],
        dtype=np.float64,
    )


    sd = np.asarray(
        [
            1.2,
            0.8,
            1.7,
            0.4,
            2.0,
            0.65,
        ],
        dtype=np.float64,
    )


    tensor_rows = []


    for condition in conds:

        transformed = (
            stage24.paper_domain_transform(
                X,
                condition,
                mu,
                sd,
            )
        )


        if transformed.shape != X.shape:
            raise RuntimeError(
                "Smoke transform shape mismatch"
            )


        if not np.all(
            np.isfinite(
                transformed
            )
        ):
            raise RuntimeError(
                "Smoke transform nonfinite"
            )


        tensor_rows.append({
            "condition":
                condition[
                    "name"
                ],

            "family":
                condition[
                    "family"
                ],

            "tensor_sha256":
                stage24.sha256_array(
                    transformed
                ),
        })


    if len({
        row[
            "tensor_sha256"
        ]
        for row in tensor_rows
    }) != 18:

        raise RuntimeError(
            "Synthetic Stage24 condition tensors "
            "are not unique 18/18"
        )


    manifest = load_manifest()


    checkpoint_rows = []


    for row in manifest:

        seed = int(
            row[
                "seed"
            ]
        )


        model = load_model(
            row,
            device,
        )


        metrics = (
            stage24.evaluate_model(
                model,
                X,
                y,
                str(
                    device
                ),
            )
        )


        checkpoint_rows.append({
            "seed":
                seed,

            "parameter_count":
                parameter_count(
                    model
                ),

            "synthetic_accuracy":
                metrics[
                    "accuracy"
                ],

            "synthetic_macro_f1":
                metrics[
                    "macro_f1"
                ],

            "checkpoint_sha256":
                row[
                    "checkpoint_sha256"
                ],
        })


        del model

        if device.type == "cuda":
            torch.cuda.empty_cache()

        gc.collect()


    write_csv(
        out_dir
        / "synthetic_condition_tensor_sha_18.csv",
        tensor_rows,
    )


    write_csv(
        out_dir
        / "checkpoint_synthetic_forward_5.csv",
        checkpoint_rows,
    )


    receipt = {
        "status":
            "PASS",

        "stage24_snapshot_sha256":
            sha256_file(
                STAGE24_SNAPSHOT
            ),

        "condition_count":
            18,

        "condition_tensor_sha_unique":
            18,

        "checkpoint_count":
            5,

        "checkpoint_strict_load":
            "PASS_5_OF_5",

        "synthetic_forward":
            "PASS_5_OF_5",

        "parameter_count":
            EXPECTED_PARAMS,

        "test_data_loaded":
            False,

        "test_inference_performed":
            False,

        "training_performed":
            False,
    }


    write_json(
        out_dir
        / "v26_external_storm_test_smoke_receipt_r9d2.json",
        receipt,
    )


    print(
        "R9D2_STAGE24_CONDITION_MANIFEST_PASS_18=True"
    )

    print(
        "R9D2_SYNTHETIC_CONDITION_TENSOR_SHA_UNIQUE_18_OF_18=True"
    )

    print(
        "R9D2_CHECKPOINT_STRICT_LOAD_PASS_5_OF_5=True"
    )

    print(
        "R9D2_SYNTHETIC_FORWARD_PASS_5_OF_5=True"
    )

    print(
        "R9D2_PARAMETER_COUNT_PASS_23210=True"
    )

    print(
        "EXTERNAL_TEST_LOADED=False"
    )

    print(
        "EXTERNAL_TEST_INFERENCE=False"
    )

    print(
        "V26_EXTERNAL_STORM_TEST_SMOKE_R9D2_PASS=True"
    )


def run_full(
    out_dir,
    device,
):

    marker = (
        out_dir
        / "TEST_CONSUMPTION_STARTED"
    )


    if marker.exists():
        raise RuntimeError(
            "V26 external STORM test already consumed. "
            "Rerun forbidden."
        )


    manifest = load_manifest()

    stage24 = load_stage24()


    conds = stage24.conditions()


    if len(conds) != 18:
        raise RuntimeError(
            "Frozen Stage24 conditions != 18"
        )


    # Irreversible boundary.
    marker.write_text(
        "V26C external STORM test consumption started.\n"
    )


    print(
        "V26_EXTERNAL_STORM_TEST_CONSUMPTION_STARTED=True",
        flush=True,
    )


    # Exact frozen Stage24 test loader and normalization.
    X, y, mu, sd, meta = (
        stage24.load_test_and_normalization()
    )


    if X.shape != (
        13993,
        64,
        6,
    ):
        raise RuntimeError(
            f"Unexpected external test shape "
            f"{X.shape}"
        )


    if y.shape != (
        13993,
    ):
        raise RuntimeError(
            f"Unexpected external y shape "
            f"{y.shape}"
        )


    if set(
        np.unique(
            y
        ).tolist()
    ) != set(
        range(8)
    ):
        raise RuntimeError(
            "External test labels != 0..7"
        )


    print(
        "R9D2_EXTERNAL_TEST_SHAPE_PASS_13993x64x6=True",
        flush=True,
    )


    models = {}


    for row in manifest:

        seed = int(
            row[
                "seed"
            ]
        )


        models[
            seed
        ] = load_model(
            row,
            device,
        )


        print(
            "R9D2_MODEL_BOUND:",
            f"seed={seed}",
            f"params={parameter_count(models[seed])}",
            f"sha={row['checkpoint_sha256']}",
            flush=True,
        )


    case_rows = []
    tensor_rows = []


    for condition_index, condition in enumerate(
        conds,
        start=1,
    ):

        X_condition = (
            stage24.paper_domain_transform(
                X,
                condition,
                mu,
                sd,
            )
        )


        tensor_sha = (
            stage24.sha256_array(
                X_condition
            )
        )


        tensor_rows.append({
            "condition_index":
                condition_index,

            "condition":
                condition[
                    "name"
                ],

            "family":
                condition[
                    "family"
                ],

            "tensor_sha256":
                tensor_sha,
        })


        write_csv(
            out_dir
            / "condition_tensor_sha_partial.csv",
            tensor_rows,
        )


        print(
            "R9D2_CONDITION_START:",
            f"{condition_index}/18",
            condition[
                "name"
            ],
            f"tensor_sha={tensor_sha}",
            flush=True,
        )


        for row in manifest:

            seed = int(
                row[
                    "seed"
                ]
            )


            metrics = (
                stage24.evaluate_model(
                    models[
                        seed
                    ],
                    X_condition,
                    y,
                    str(
                        device
                    ),
                )
            )


            record = {
                "seed":
                    seed,

                "condition_index":
                    condition_index,

                "condition":
                    condition[
                        "name"
                    ],

                "family":
                    condition[
                        "family"
                    ],

                "accuracy":
                    metrics[
                        "accuracy"
                    ],

                "macro_f1":
                    metrics[
                        "macro_f1"
                    ],

                "condition_tensor_sha256":
                    tensor_sha,

                "checkpoint_sha256":
                    row[
                        "checkpoint_sha256"
                    ],
            }


            case_rows.append(
                record
            )


            # Preserve every completed inference case.
            write_csv(
                out_dir
                / "external_v26c_test_cases_partial.csv",
                case_rows,
            )


            print(
                "R9D2_CASE_COMPLETE:",
                f"condition={condition['name']}",
                f"seed={seed}",
                f"acc={metrics['accuracy']:.9f}",
                f"f1={metrics['macro_f1']:.9f}",
                flush=True,
            )


        del X_condition

        gc.collect()


    if len(
        case_rows
    ) != 90:

        raise RuntimeError(
            f"External case rows={len(case_rows)} != 90"
        )


    if len(
        tensor_rows
    ) != 18:

        raise RuntimeError(
            "Condition tensor rows != 18"
        )


    if len({
        row[
            "tensor_sha256"
        ]
        for row in tensor_rows
    }) != 18:

        raise RuntimeError(
            "Condition tensor SHAs not unique 18/18"
        )


    write_csv(
        out_dir
        / "external_v26c_test_cases_90.csv",
        case_rows,
    )


    write_csv(
        out_dir
        / "condition_tensor_sha_18.csv",
        tensor_rows,
    )


    seed_rows = [
        aggregate_seed(
            seed,
            case_rows,
        )
        for seed in SEEDS
    ]


    write_csv(
        out_dir
        / "external_v26c_per_seed_summary_5.csv",
        seed_rows,
    )


    metric_names = [
        "clean_accuracy",
        "clean_macro_f1",
        "all_fault_accuracy",
        "all_fault_macro_f1",
        "recoverable_fault_accuracy",
        "recoverable_fault_macro_f1",
        "family_balanced_accuracy",
        "family_balanced_macro_f1",
    ]


    aggregate = {
        "model":
            CANDIDATE,

        "n_seeds":
            5,

        "parameter_count":
            EXPECTED_PARAMS,
    }


    for metric in metric_names:

        values = [
            float(
                row[
                    metric
                ]
            )
            for row in seed_rows
        ]


        aggregate[
            metric
            +
            "_mean"
        ] = float(
            statistics.fmean(
                values
            )
        )


        aggregate[
            metric
            +
            "_std"
        ] = float(
            statistics.stdev(
                values
            )
        )


    write_json(
        out_dir
        / "external_v26c_aggregate_summary_r9d2.json",
        aggregate,
    )


    write_csv(
        out_dir
        / "external_v26c_aggregate_summary_1.csv",
        [
            aggregate
        ],
    )


    receipt = {
        "stage":
            "V26_EXTERNAL_STORM_TEST_R9D2",

        "status":
            "PASS",

        "candidate":
            CANDIDATE,

        "stage24_snapshot_sha256":
            sha256_file(
                STAGE24_SNAPSHOT
            ),

        "external_checkpoints":
            5,

        "conditions":
            18,

        "case_rows":
            90,

        "condition_tensor_sha_unique":
            18,

        "parameter_count":
            EXPECTED_PARAMS,

        "test_shape":
            [
                13993,
                64,
                6,
            ],

        "test_loaded":
            True,

        "test_inference_performed":
            True,

        "test_consumed":
            True,

        "test_rerun_allowed":
            False,

        "training_performed":
            False,

        "optimizer_created":
            False,

        "candidate_modified":
            False,

        "checkpoint_modified":
            False,

        "storm_model_retrained":
            False,

        "stage24_results_modified":
            False,

        "next_gate":
            (
                "Read-only R9E external scientific closure: "
                "compare frozen V26C R9D2 aggregates/per-seed "
                "results against frozen Stage24 STORM evidence."
            ),
    }


    write_json(
        out_dir
        / "v26_external_storm_test_receipt_r9d2.json",
        receipt,
    )


    print()
    print("=" * 118)
    print("V26 EXTERNAL STORM R9D2 FINAL RESULT")
    print("=" * 118)


    for metric in metric_names:

        print(
            "V26C_EXTERNAL:",
            metric,
            "MEAN=",
            f"{aggregate[metric + '_mean']:.9f}",
            "STD=",
            f"{aggregate[metric + '_std']:.9f}",
        )


    print()
    print(
        "R9D2_EXTERNAL_CASE_ROWS_PASS_90=True"
    )

    print(
        "R9D2_CONDITION_TENSOR_SHA_UNIQUE_18_OF_18=True"
    )

    print(
        "V26_EXTERNAL_STORM_TEST_R9D2_PASS=True"
    )

    print(
        "EXTERNAL_TEST_CONSUMED=True"
    )

    print(
        "EXTERNAL_TEST_RERUN_ALLOWED=False"
    )

    print(
        "TRAINING_PERFORMED=False"
    )

    print(
        "V26C_MODIFIED=False"
    )


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--mode",
        choices=[
            "smoke",
            "full",
        ],
        required=True,
    )

    parser.add_argument(
        "--out-dir",
        required=True,
    )

    parser.add_argument(
        "--device",
        default="cuda:0",
    )

    args = parser.parse_args()


    device = torch.device(
        args.device
    )


    if (
        device.type == "cuda"
        and
        not torch.cuda.is_available()
    ):
        raise RuntimeError(
            "CUDA requested but unavailable"
        )


    out_dir = Path(
        args.out_dir
    )

    out_dir.mkdir(
        parents=True,
        exist_ok=True,
    )


    if args.mode == "smoke":

        run_smoke(
            out_dir,
            device,
        )

    else:

        run_full(
            out_dir,
            device,
        )


if __name__ == "__main__":
    main()
