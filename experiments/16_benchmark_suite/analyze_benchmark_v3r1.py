from pathlib import Path
import hashlib
import itertools
import json
import math

import numpy as np
import pandas as pd

try:
    from scipy import stats
    SCIPY_AVAILABLE = True
except Exception:
    SCIPY_AVAILABLE = False


ROOT = Path(
    "results/benchmark_v3r1"
)

RAW = ROOT / "raw_runs"

REL = ROOT / "reliability_v2"

ANALYSIS = ROOT / "final_analysis"

PROTOCOL_MANIFEST = (
    ROOT /
    "protocol" /
    "protocol_manifest.json"
)

FROZEN_CORRUPTION = (
    ROOT /
    "protocol" /
    "corruption_registry_v2.json"
)


DATASETS = [
    "UCI_HAR",
    "PAMAP2",
    "DSADS",
    "MotionSense",
]


MODELS = [
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


SEEDS = [
    42,
    123,
    456,
    789,
    2026,
]


FAMILIES = [
    "missing_channel",
    "random_dropout",
    "gaussian_noise",
    "sensor_drift",
]


EXPECTED_FAMILY_CASES = {
    "missing_channel": 6,
    "random_dropout": 9,
    "gaussian_noise": 9,
    "sensor_drift": 9,
}


EXPECTED_CASES = sum(
    EXPECTED_FAMILY_CASES.values()
)


def sha256_file(path):

    path = Path(path)

    h = hashlib.sha256()

    with path.open("rb") as f:

        while True:

            block = f.read(
                1024 * 1024
            )

            if not block:
                break

            h.update(block)

    return h.hexdigest()


def load_json(path):

    return json.loads(
        Path(path).read_text()
    )


def scalar_float(value):

    if value is None:
        return np.nan

    try:
        return float(value)
    except Exception:
        return np.nan


def require(condition, message, errors):

    if not condition:
        errors.append(message)


def mean_std(series):

    values = (
        pd.to_numeric(
            series,
            errors="coerce"
        )
        .dropna()
        .to_numpy(
            dtype=float
        )
    )

    if len(values) == 0:
        return np.nan, np.nan

    mean = float(
        np.mean(values)
    )

    std = (
        float(
            np.std(
                values,
                ddof=1
            )
        )
        if len(values) > 1
        else 0.0
    )

    return mean, std


def find_numeric(
    obj,
    candidate_paths
):

    for path in candidate_paths:

        current = obj

        ok = True

        for key in path:

            if not isinstance(
                current,
                dict
            ):
                ok = False
                break

            if key not in current:
                ok = False
                break

            current = current[
                key
            ]

        if ok:

            try:
                return float(current)
            except Exception:
                pass

    return np.nan


def paired_test(
    a,
    b
):

    a = np.asarray(
        a,
        dtype=float
    )

    b = np.asarray(
        b,
        dtype=float
    )

    valid = (
        np.isfinite(a)
        &
        np.isfinite(b)
    )

    a = a[valid]
    b = b[valid]

    difference = (
        a - b
    )

    result = {
        "n":
            int(
                len(
                    difference
                )
            ),

        "mean_difference":
            np.nan,

        "difference_std":
            np.nan,

        "cohen_dz":
            np.nan,

        "paired_t_pvalue":
            np.nan,

        "wilcoxon_pvalue":
            np.nan,

        "anchor_higher_count":
            0,

        "competitor_higher_count":
            0,

        "equal_count":
            0,
    }


    if len(
        difference
    ) == 0:

        return result


    result[
        "mean_difference"
    ] = float(
        np.mean(
            difference
        )
    )


    if len(
        difference
    ) > 1:

        sd = float(
            np.std(
                difference,
                ddof=1
            )
        )

        result[
            "difference_std"
        ] = sd

        if sd > 0:

            result[
                "cohen_dz"
            ] = float(
                np.mean(
                    difference
                )
                /
                sd
            )


    result[
        "anchor_higher_count"
    ] = int(
        np.sum(
            difference > 0
        )
    )

    result[
        "competitor_higher_count"
    ] = int(
        np.sum(
            difference < 0
        )
    )

    result[
        "equal_count"
    ] = int(
        np.sum(
            difference == 0
        )
    )


    if (
        SCIPY_AVAILABLE
        and
        len(
            difference
        ) >= 2
    ):

        try:

            result[
                "paired_t_pvalue"
            ] = float(
                stats.ttest_rel(
                    a,
                    b
                ).pvalue
            )

        except Exception:
            pass


        try:

            if not np.allclose(
                difference,
                0
            ):

                result[
                    "wilcoxon_pvalue"
                ] = float(
                    stats.wilcoxon(
                        difference,
                        zero_method="wilcox",
                        alternative="two-sided"
                    ).pvalue
                )

        except Exception:
            pass


    return result


ANALYSIS.mkdir(
    parents=True,
    exist_ok=True
)


errors = []

warnings = []


print(
    "=" * 78
)

print(
    "BENCHMARK V3R1 FINAL INTEGRITY + AGGREGATION"
)

print(
    "=" * 78
)


require(
    PROTOCOL_MANIFEST.exists(),
    f"Missing {PROTOCOL_MANIFEST}",
    errors
)

require(
    FROZEN_CORRUPTION.exists(),
    f"Missing {FROZEN_CORRUPTION}",
    errors
)


if errors:

    for error in errors:
        print(
            "ERROR:",
            error
        )

    raise SystemExit(2)


protocol = load_json(
    PROTOCOL_MANIFEST
)


protocol_sha = sha256_file(
    PROTOCOL_MANIFEST
)


corruption_sha = sha256_file(
    FROZEN_CORRUPTION
)


print(
    "PROTOCOL_MANIFEST_SHA256=",
    protocol_sha
)

print(
    "FROZEN_CORRUPTION_SHA256=",
    corruption_sha
)


print()
print(
    "1. VERIFY FROZEN PROTOCOL INPUT HASHES"
)
print(
    "-" * 78
)


hash_inventory = protocol.get(
    "hashes",
    {}
)


hash_verified = 0


for path_text, expected_sha in hash_inventory.items():

    path = Path(
        path_text
    )

    require(
        path.exists(),
        f"Frozen input missing: {path}",
        errors
    )

    if not path.exists():
        continue

    actual = sha256_file(
        path
    )

    require(
        actual == expected_sha,
        (
            f"Frozen input SHA mismatch: "
            f"{path} "
            f"expected={expected_sha} "
            f"actual={actual}"
        ),
        errors
    )

    if actual == expected_sha:

        hash_verified += 1


print(
    "FROZEN_HASHES_EXPECTED=",
    len(
        hash_inventory
    )
)

print(
    "FROZEN_HASHES_VERIFIED=",
    hash_verified
)


clean_rows = []

reliability_rows = []

family_rows = []

case_rows = []


expected_combinations = set(
    itertools.product(
        DATASETS,
        MODELS,
        SEEDS
    )
)


clean_seen = set()

rel_seen = set()


print()
print(
    "2. VERIFY 180 CLEAN RUN ARTIFACTS"
)
print(
    "-" * 78
)


for dataset, model, seed in sorted(
    expected_combinations
):

    run_dir = (
        RAW /
        dataset /
        model /
        f"seed_{seed}"
    )


    required_files = [
        "COMPLETE",
        "best_model.pt",
        "checkpoint.pt",
        "metrics.json",
        "config.json",
        "dataset_summary.json",
        "training_history.json",
        "receipt.json",
    ]


    for filename in required_files:

        require(
            (
                run_dir /
                filename
            ).exists(),
            (
                f"Missing clean artifact: "
                f"{run_dir / filename}"
            ),
            errors
        )


    if not all(
        (
            run_dir /
            filename
        ).exists()
        for filename
        in required_files
    ):

        continue


    clean_seen.add(
        (
            dataset,
            model,
            seed
        )
    )


    metrics = load_json(
        run_dir /
        "metrics.json"
    )

    receipt = load_json(
        run_dir /
        "receipt.json"
    )

    dataset_summary = load_json(
        run_dir /
        "dataset_summary.json"
    )


    best_sha = sha256_file(
        run_dir /
        "best_model.pt"
    )

    checkpoint_sha = sha256_file(
        run_dir /
        "checkpoint.pt"
    )

    metrics_sha = sha256_file(
        run_dir /
        "metrics.json"
    )

    config_sha = sha256_file(
        run_dir /
        "config.json"
    )


    require(
        best_sha
        ==
        checkpoint_sha,
        (
            f"best_model/checkpoint mismatch: "
            f"{dataset}/{model}/seed_{seed}"
        ),
        errors
    )


    require(
        receipt.get(
            "protocol_manifest_sha256"
        )
        ==
        protocol_sha,
        (
            f"Protocol receipt mismatch: "
            f"{dataset}/{model}/seed_{seed}"
        ),
        errors
    )


    require(
        receipt.get(
            "best_model_sha256"
        )
        ==
        best_sha,
        (
            f"best_model receipt mismatch: "
            f"{dataset}/{model}/seed_{seed}"
        ),
        errors
    )


    require(
        receipt.get(
            "checkpoint_sha256"
        )
        ==
        checkpoint_sha,
        (
            f"checkpoint receipt mismatch: "
            f"{dataset}/{model}/seed_{seed}"
        ),
        errors
    )


    require(
        receipt.get(
            "metrics_sha256"
        )
        ==
        metrics_sha,
        (
            f"metrics receipt mismatch: "
            f"{dataset}/{model}/seed_{seed}"
        ),
        errors
    )


    require(
        receipt.get(
            "config_sha256"
        )
        ==
        config_sha,
        (
            f"config receipt mismatch: "
            f"{dataset}/{model}/seed_{seed}"
        ),
        errors
    )


    test = metrics.get(
        "test",
        {}
    )


    accuracy = scalar_float(
        test.get(
            "accuracy"
        )
    )

    macro_f1 = scalar_float(
        test.get(
            "macro_f1"
        )
    )


    require(
        np.isfinite(
            accuracy
        ),
        (
            f"Invalid clean accuracy: "
            f"{dataset}/{model}/{seed}"
        ),
        errors
    )

    require(
        np.isfinite(
            macro_f1
        ),
        (
            f"Invalid clean macro-F1: "
            f"{dataset}/{model}/{seed}"
        ),
        errors
    )


    clean_rows.append(
        {

            "dataset":
                dataset,

            "model":
                model,

            "seed":
                seed,

            "accuracy":
                accuracy,

            "macro_f1":
                macro_f1,

            "parameters":
                scalar_float(
                    metrics.get(
                        "parameters"
                    )
                ),

            "checkpoint_size_mb":
                scalar_float(
                    metrics.get(
                        "checkpoint_size_mb"
                    )
                ),

            "training_seconds":
                scalar_float(
                    metrics.get(
                        "training_seconds"
                    )
                ),

            "best_epoch":
                scalar_float(
                    metrics.get(
                        "best_epoch"
                    )
                ),

            "best_validation_macro_f1":
                scalar_float(
                    metrics.get(
                        "best_validation_macro_f1"
                    )
                ),

            "reliability_training":
                bool(
                    metrics.get(
                        "reliability_training",
                        False
                    )
                ),

            "consistency_feature_available":
                bool(
                    metrics.get(
                        "consistency_feature_available",
                        False
                    )
                ),

            "train_samples":
                dataset_summary.get(
                    "train_samples"
                ),

            "validation_samples":
                dataset_summary.get(
                    "validation_samples"
                ),

            "test_samples":
                dataset_summary.get(
                    "test_samples"
                ),

            "best_model_sha256":
                best_sha,
        }
    )


print(
    "CLEAN_EXPECTED=",
    len(
        expected_combinations
    )
)

print(
    "CLEAN_VERIFIED=",
    len(
        clean_seen
    )
)


print()
print(
    "3. VERIFY 180 RELIABILITY-V2 RUNS + 5940 CASES"
)
print(
    "-" * 78
)


for dataset, model, seed in sorted(
    expected_combinations
):

    output_dir = (
        REL /
        dataset /
        model /
        f"seed_{seed}"
    )


    summary_path = (
        output_dir /
        "reliability_summary_v2.json"
    )

    receipt_path = (
        output_dir /
        "receipt.json"
    )

    complete_path = (
        output_dir /
        "COMPLETE"
    )


    for path in [
        summary_path,
        receipt_path,
        complete_path,
    ]:

        require(
            path.exists(),
            (
                f"Missing reliability artifact: "
                f"{path}"
            ),
            errors
        )


    if not (
        summary_path.exists()
        and
        receipt_path.exists()
        and
        complete_path.exists()
    ):

        continue


    rel_seen.add(
        (
            dataset,
            model,
            seed
        )
    )


    summary = load_json(
        summary_path
    )

    receipt = load_json(
        receipt_path
    )


    summary_sha = sha256_file(
        summary_path
    )


    clean_checkpoint = (
        RAW /
        dataset /
        model /
        f"seed_{seed}" /
        "best_model.pt"
    )


    clean_checkpoint_sha = (
        sha256_file(
            clean_checkpoint
        )
    )


    require(
        receipt.get(
            "protocol_manifest_sha256"
        )
        ==
        protocol_sha,
        (
            f"Reliability protocol receipt "
            f"mismatch: "
            f"{dataset}/{model}/{seed}"
        ),
        errors
    )


    require(
        receipt.get(
            "clean_checkpoint_sha256"
        )
        ==
        clean_checkpoint_sha,
        (
            f"Reliability checkpoint receipt "
            f"mismatch: "
            f"{dataset}/{model}/{seed}"
        ),
        errors
    )


    require(
        receipt.get(
            "corruption_registry_sha256"
        )
        ==
        corruption_sha,
        (
            f"Reliability registry receipt "
            f"mismatch: "
            f"{dataset}/{model}/{seed}"
        ),
        errors
    )


    require(
        receipt.get(
            "summary_sha256"
        )
        ==
        summary_sha,
        (
            f"Reliability summary receipt "
            f"mismatch: "
            f"{dataset}/{model}/{seed}"
        ),
        errors
    )


    require(
        summary.get(
            "protocol_version"
        )
        ==
        "v2",
        (
            f"Wrong reliability protocol: "
            f"{dataset}/{model}/{seed}"
        ),
        errors
    )


    cases = summary.get(
        "cases",
        []
    )


    require(
        isinstance(
            cases,
            list
        ),
        (
            f"Reliability cases are not a list: "
            f"{dataset}/{model}/{seed}"
        ),
        errors
    )


    require(
        len(
            cases
        )
        ==
        EXPECTED_CASES,
        (
            f"Reliability case count mismatch: "
            f"{dataset}/{model}/{seed}: "
            f"{len(cases)} != {EXPECTED_CASES}"
        ),
        errors
    )


    clean_metrics = load_json(
        RAW /
        dataset /
        model /
        f"seed_{seed}" /
        "metrics.json"
    ).get(
        "test",
        {}
    )


    clean_accuracy = scalar_float(
        clean_metrics.get(
            "accuracy"
        )
    )

    clean_macro_f1 = scalar_float(
        clean_metrics.get(
            "macro_f1"
        )
    )


    family_case_map = {
        family: []
        for family
        in FAMILIES
    }


    for case_index, case in enumerate(
        cases
    ):

        family = case.get(
            "family"
        )


        require(
            family
            in
            FAMILIES,
            (
                f"Unknown corruption family: "
                f"{dataset}/{model}/{seed}: "
                f"{family}"
            ),
            errors
        )


        if family not in family_case_map:
            continue


        family_case_map[
            family
        ].append(
            case
        )


        case_clean_accuracy = find_numeric(
            case,
            [
                (
                    "clean_metrics",
                    "accuracy"
                ),
            ]
        )

        case_clean_f1 = find_numeric(
            case,
            [
                (
                    "clean_metrics",
                    "macro_f1"
                ),
            ]
        )


        if np.isfinite(
            case_clean_accuracy
        ):

            require(
                abs(
                    case_clean_accuracy
                    -
                    clean_accuracy
                )
                <
                1e-8,
                (
                    f"Clean accuracy parity failure: "
                    f"{dataset}/{model}/{seed}/"
                    f"{family}/case_{case_index}"
                ),
                errors
            )


        if np.isfinite(
            case_clean_f1
        ):

            require(
                abs(
                    case_clean_f1
                    -
                    clean_macro_f1
                )
                <
                1e-8,
                (
                    f"Clean macro-F1 parity "
                    f"failure: "
                    f"{dataset}/{model}/{seed}/"
                    f"{family}/case_{case_index}"
                ),
                errors
            )


        reliability_score = find_numeric(
            case,
            [
                (
                    "reliability_score",
                ),
            ]
        )


        corrupted_accuracy = find_numeric(
            case,
            [
                (
                    "corrupted_metrics",
                    "accuracy"
                ),
            ]
        )


        corrupted_macro_f1 = find_numeric(
            case,
            [
                (
                    "corrupted_metrics",
                    "macro_f1"
                ),
            ]
        )


        accuracy_degradation = find_numeric(
            case,
            [
                (
                    "degradation",
                    "accuracy_degradation"
                ),
            ]
        )


        macro_f1_degradation = find_numeric(
            case,
            [
                (
                    "degradation",
                    "macro_f1_degradation"
                ),
            ]
        )


        require(
            np.isfinite(
                reliability_score
            ),
            (
                f"Missing reliability_score: "
                f"{dataset}/{model}/{seed}/"
                f"case_{case_index}"
            ),
            errors
        )


        require(
            np.isfinite(
                corrupted_accuracy
            ),
            (
                f"Missing corrupted accuracy: "
                f"{dataset}/{model}/{seed}/"
                f"case_{case_index}"
            ),
            errors
        )


        require(
            np.isfinite(
                corrupted_macro_f1
            ),
            (
                f"Missing corrupted macro-F1: "
                f"{dataset}/{model}/{seed}/"
                f"case_{case_index}"
            ),
            errors
        )


        case_rows.append(
            {

                "dataset":
                    dataset,

                "model":
                    model,

                "seed":
                    seed,

                "family":
                    family,

                "condition_id":
                    case.get(
                        "condition_id"
                    ),

                "condition_value":
                    case.get(
                        "condition_value"
                    ),

                "corruption_seed":
                    case.get(
                        "corruption_seed"
                    ),

                "clean_accuracy":
                    clean_accuracy,

                "clean_macro_f1":
                    clean_macro_f1,

                "reliability_score":
                    reliability_score,

                "corrupted_accuracy":
                    corrupted_accuracy,

                "corrupted_macro_f1":
                    corrupted_macro_f1,

                "relative_accuracy_degradation":
                    accuracy_degradation,

                "relative_macro_f1_degradation":
                    macro_f1_degradation,
            }
        )


    seed_family_rows = []


    for family in FAMILIES:

        family_cases = (
            family_case_map[
                family
            ]
        )


        require(
            len(
                family_cases
            )
            ==
            EXPECTED_FAMILY_CASES[
                family
            ],
            (
                f"Family case count mismatch: "
                f"{dataset}/{model}/{seed}/"
                f"{family}: "
                f"{len(family_cases)} != "
                f"{EXPECTED_FAMILY_CASES[family]}"
            ),
            errors
        )


        if not family_cases:
            continue


        reliability_values = [
            find_numeric(
                case,
                [
                    (
                        "reliability_score",
                    )
                ]
            )
            for case
            in family_cases
        ]


        corrupted_accuracy_values = [
            find_numeric(
                case,
                [
                    (
                        "corrupted_metrics",
                        "accuracy"
                    )
                ]
            )
            for case
            in family_cases
        ]


        corrupted_f1_values = [
            find_numeric(
                case,
                [
                    (
                        "corrupted_metrics",
                        "macro_f1"
                    )
                ]
            )
            for case
            in family_cases
        ]


        accuracy_degradation_values = [
            find_numeric(
                case,
                [
                    (
                        "degradation",
                        "accuracy_degradation"
                    )
                ]
            )
            for case
            in family_cases
        ]


        f1_degradation_values = [
            find_numeric(
                case,
                [
                    (
                        "degradation",
                        "macro_f1_degradation"
                    )
                ]
            )
            for case
            in family_cases
        ]


        row = {

            "dataset":
                dataset,

            "model":
                model,

            "seed":
                seed,

            "family":
                family,

            "n_cases":
                len(
                    family_cases
                ),

            "reliability_score":
                float(
                    np.mean(
                        reliability_values
                    )
                ),

            "corrupted_accuracy":
                float(
                    np.mean(
                        corrupted_accuracy_values
                    )
                ),

            "corrupted_macro_f1":
                float(
                    np.mean(
                        corrupted_f1_values
                    )
                ),

            "relative_accuracy_degradation":
                float(
                    np.mean(
                        accuracy_degradation_values
                    )
                ),

            "relative_macro_f1_degradation":
                float(
                    np.mean(
                        f1_degradation_values
                    )
                ),
        }


        seed_family_rows.append(
            row
        )

        family_rows.append(
            row
        )


    require(
        len(
            seed_family_rows
        )
        ==
        4,
        (
            f"Expected four family summaries: "
            f"{dataset}/{model}/{seed}"
        ),
        errors
    )


    if len(
        seed_family_rows
    ) == 4:

        reliability_rows.append(
            {

                "dataset":
                    dataset,

                "model":
                    model,

                "seed":
                    seed,

                "clean_accuracy":
                    clean_accuracy,

                "clean_macro_f1":
                    clean_macro_f1,

                "reliability_score":
                    float(
                        np.mean(
                            [
                                row[
                                    "reliability_score"
                                ]
                                for row
                                in seed_family_rows
                            ]
                        )
                    ),

                "corrupted_accuracy":
                    float(
                        np.mean(
                            [
                                row[
                                    "corrupted_accuracy"
                                ]
                                for row
                                in seed_family_rows
                            ]
                        )
                    ),

                "corrupted_macro_f1":
                    float(
                        np.mean(
                            [
                                row[
                                    "corrupted_macro_f1"
                                ]
                                for row
                                in seed_family_rows
                            ]
                        )
                    ),

                "relative_accuracy_degradation":
                    float(
                        np.mean(
                            [
                                row[
                                    "relative_accuracy_degradation"
                                ]
                                for row
                                in seed_family_rows
                            ]
                        )
                    ),

                "relative_macro_f1_degradation":
                    float(
                        np.mean(
                            [
                                row[
                                    "relative_macro_f1_degradation"
                                ]
                                for row
                                in seed_family_rows
                            ]
                        )
                    ),

                "case_count":
                    len(
                        cases
                    ),

                "summary_sha256":
                    summary_sha,
            }
        )


print(
    "RELIABILITY_EXPECTED=",
    len(
        expected_combinations
    )
)

print(
    "RELIABILITY_VERIFIED=",
    len(
        rel_seen
    )
)

print(
    "CORRUPTION_CASES_EXPECTED=",
    len(
        expected_combinations
    )
    *
    EXPECTED_CASES
)

print(
    "CORRUPTION_CASES_PARSED=",
    len(
        case_rows
    )
)


print()
print(
    "4. FINAL INTEGRITY CLASSIFICATION"
)
print(
    "-" * 78
)


if clean_seen != expected_combinations:

    missing = sorted(
        expected_combinations
        -
        clean_seen
    )

    errors.append(
        f"Missing clean combinations: {missing}"
    )


if rel_seen != expected_combinations:

    missing = sorted(
        expected_combinations
        -
        rel_seen
    )

    errors.append(
        f"Missing reliability combinations: "
        f"{missing}"
    )


if errors:

    print(
        "BENCHMARK_V3R1_INTEGRITY_PASS=False"
    )

    print(
        "ERROR_COUNT=",
        len(
            errors
        )
    )

    for error in errors:

        print(
            "ERROR:",
            error
        )


    (
        ANALYSIS /
        "integrity_errors.txt"
    ).write_text(
        "\n".join(
            errors
        )
        +
        "\n"
    )


    raise SystemExit(3)


print(
    "ERROR_COUNT=0"
)

print(
    "BENCHMARK_V3R1_INTEGRITY_PASS=True"
)


clean_df = pd.DataFrame(
    clean_rows
).sort_values(
    [
        "dataset",
        "model",
        "seed"
    ]
)


reliability_df = pd.DataFrame(
    reliability_rows
).sort_values(
    [
        "dataset",
        "model",
        "seed"
    ]
)


family_df = pd.DataFrame(
    family_rows
).sort_values(
    [
        "dataset",
        "model",
        "seed",
        "family"
    ]
)


case_df = pd.DataFrame(
    case_rows
).sort_values(
    [
        "dataset",
        "model",
        "seed",
        "family",
        "condition_id"
    ]
)


clean_df.to_csv(
    ANALYSIS /
    "clean_runs_180.csv",
    index=False
)


reliability_df.to_csv(
    ANALYSIS /
    "reliability_runs_180.csv",
    index=False
)


family_df.to_csv(
    ANALYSIS /
    "reliability_family_runs_720.csv",
    index=False
)


case_df.to_csv(
    ANALYSIS /
    "reliability_cases_5940.csv",
    index=False
)


print()
print(
    "5. DATASET × MODEL AGGREGATION"
)
print(
    "-" * 78
)


clean_summary_rows = []


for (
    dataset,
    model
), group in clean_df.groupby(
    [
        "dataset",
        "model"
    ],
    sort=False
):

    accuracy_mean, accuracy_std = (
        mean_std(
            group[
                "accuracy"
            ]
        )
    )

    f1_mean, f1_std = mean_std(
        group[
            "macro_f1"
        ]
    )

    training_mean, training_std = (
        mean_std(
            group[
                "training_seconds"
            ]
        )
    )

    params_mean, _ = mean_std(
        group[
            "parameters"
        ]
    )

    size_mean, _ = mean_std(
        group[
            "checkpoint_size_mb"
        ]
    )


    clean_summary_rows.append(
        {

            "dataset":
                dataset,

            "model":
                model,

            "n_seeds":
                len(
                    group
                ),

            "accuracy_mean":
                accuracy_mean,

            "accuracy_std":
                accuracy_std,

            "macro_f1_mean":
                f1_mean,

            "macro_f1_std":
                f1_std,

            "training_seconds_mean":
                training_mean,

            "training_seconds_std":
                training_std,

            "parameters_mean":
                params_mean,

            "checkpoint_size_mb_mean":
                size_mean,
        }
    )


clean_summary = pd.DataFrame(
    clean_summary_rows
)


reliability_summary_rows = []


for (
    dataset,
    model
), group in reliability_df.groupby(
    [
        "dataset",
        "model"
    ],
    sort=False
):

    row = {
        "dataset":
            dataset,

        "model":
            model,

        "n_seeds":
            len(
                group
            ),
    }


    for metric in [
        "reliability_score",
        "corrupted_accuracy",
        "corrupted_macro_f1",
        "relative_accuracy_degradation",
        "relative_macro_f1_degradation",
    ]:

        mean, std = mean_std(
            group[
                metric
            ]
        )

        row[
            f"{metric}_mean"
        ] = mean

        row[
            f"{metric}_std"
        ] = std


    reliability_summary_rows.append(
        row
    )


reliability_summary = pd.DataFrame(
    reliability_summary_rows
)


dataset_model = clean_summary.merge(
    reliability_summary,
    on=[
        "dataset",
        "model"
    ],
    how="inner",
    suffixes=(
        "_clean",
        "_reliability"
    )
)


dataset_model.to_csv(
    ANALYSIS /
    "dataset_model_summary_36.csv",
    index=False
)


family_summary_rows = []


for (
    dataset,
    model,
    family
), group in family_df.groupby(
    [
        "dataset",
        "model",
        "family"
    ],
    sort=False
):

    row = {
        "dataset":
            dataset,

        "model":
            model,

        "family":
            family,

        "n_seeds":
            len(
                group
            ),
    }


    for metric in [
        "reliability_score",
        "corrupted_accuracy",
        "corrupted_macro_f1",
        "relative_accuracy_degradation",
        "relative_macro_f1_degradation",
    ]:

        mean, std = mean_std(
            group[
                metric
            ]
        )

        row[
            f"{metric}_mean"
        ] = mean

        row[
            f"{metric}_std"
        ] = std


    family_summary_rows.append(
        row
    )


family_summary = pd.DataFrame(
    family_summary_rows
)


family_summary.to_csv(
    ANALYSIS /
    "reliability_family_summary_144.csv",
    index=False
)


print(
    "DATASET_MODEL_ROWS=",
    len(
        dataset_model
    )
)

print(
    "FAMILY_SUMMARY_ROWS=",
    len(
        family_summary
    )
)


print()
print(
    "6. EQUAL-DATASET-WEIGHT CROSS-DATASET SUMMARY"
)
print(
    "-" * 78
)


cross_rows = []


for model, group in dataset_model.groupby(
    "model",
    sort=False
):

    row = {
        "model":
            model,

        "dataset_count":
            len(
                group
            ),
    }


    metric_map = {

        "clean_accuracy":
            "accuracy_mean",

        "clean_macro_f1":
            "macro_f1_mean",

        "reliability_score":
            "reliability_score_mean",

        "corrupted_accuracy":
            "corrupted_accuracy_mean",

        "corrupted_macro_f1":
            "corrupted_macro_f1_mean",

        "relative_accuracy_degradation":
            "relative_accuracy_degradation_mean",

        "relative_macro_f1_degradation":
            "relative_macro_f1_degradation_mean",

        "parameters":
            "parameters_mean",

        "checkpoint_size_mb":
            "checkpoint_size_mb_mean",

        "training_seconds":
            "training_seconds_mean",
    }


    for output_name, column in metric_map.items():

        values = pd.to_numeric(
            group[
                column
            ],
            errors="coerce"
        ).to_numpy(
            dtype=float
        )


        row[
            f"{output_name}_dataset_macro_mean"
        ] = float(
            np.nanmean(
                values
            )
        )


        row[
            f"{output_name}_dataset_std"
        ] = (
            float(
                np.nanstd(
                    values,
                    ddof=1
                )
            )
            if len(
                values
            ) > 1
            else 0.0
        )


    cross_rows.append(
        row
    )


cross_summary = pd.DataFrame(
    cross_rows
)


cross_summary.to_csv(
    ANALYSIS /
    "cross_dataset_model_summary_9.csv",
    index=False
)


print(
    cross_summary[
        [
            "model",
            "clean_accuracy_dataset_macro_mean",
            "clean_macro_f1_dataset_macro_mean",
            "reliability_score_dataset_macro_mean",
            "corrupted_accuracy_dataset_macro_mean",
            "parameters_dataset_macro_mean",
        ]
    ]
    .sort_values(
        "clean_macro_f1_dataset_macro_mean",
        ascending=False
    )
    .to_string(
        index=False
    )
)


print()
print(
    "7. PER-DATASET RANKS"
)
print(
    "-" * 78
)


rank_rows = []


for dataset in DATASETS:

    group = dataset_model[
        dataset_model[
            "dataset"
        ]
        ==
        dataset
    ].copy()


    group[
        "clean_accuracy_rank"
    ] = group[
        "accuracy_mean"
    ].rank(
        ascending=False,
        method="average"
    )


    group[
        "clean_macro_f1_rank"
    ] = group[
        "macro_f1_mean"
    ].rank(
        ascending=False,
        method="average"
    )


    group[
        "reliability_rank"
    ] = group[
        "reliability_score_mean"
    ].rank(
        ascending=False,
        method="average"
    )


    group[
        "corrupted_accuracy_rank"
    ] = group[
        "corrupted_accuracy_mean"
    ].rank(
        ascending=False,
        method="average"
    )


    group[
        "corrupted_macro_f1_rank"
    ] = group[
        "corrupted_macro_f1_mean"
    ].rank(
        ascending=False,
        method="average"
    )


    group[
        "parameter_rank"
    ] = group[
        "parameters_mean"
    ].rank(
        ascending=True,
        method="average"
    )


    for _, row in group.iterrows():

        rank_rows.append(
            {

                "dataset":
                    dataset,

                "model":
                    row[
                        "model"
                    ],

                "clean_accuracy_rank":
                    row[
                        "clean_accuracy_rank"
                    ],

                "clean_macro_f1_rank":
                    row[
                        "clean_macro_f1_rank"
                    ],

                "reliability_rank":
                    row[
                        "reliability_rank"
                    ],

                "corrupted_accuracy_rank":
                    row[
                        "corrupted_accuracy_rank"
                    ],

                "corrupted_macro_f1_rank":
                    row[
                        "corrupted_macro_f1_rank"
                    ],

                "parameter_rank":
                    row[
                        "parameter_rank"
                    ],
            }
        )


rank_df = pd.DataFrame(
    rank_rows
)


rank_df.to_csv(
    ANALYSIS /
    "dataset_model_ranks.csv",
    index=False
)


average_ranks = (
    rank_df
    .groupby(
        "model",
        as_index=False
    )
    .agg(
        clean_accuracy_rank_mean=(
            "clean_accuracy_rank",
            "mean"
        ),

        clean_macro_f1_rank_mean=(
            "clean_macro_f1_rank",
            "mean"
        ),

        reliability_rank_mean=(
            "reliability_rank",
            "mean"
        ),

        corrupted_accuracy_rank_mean=(
            "corrupted_accuracy_rank",
            "mean"
        ),

        corrupted_macro_f1_rank_mean=(
            "corrupted_macro_f1_rank",
            "mean"
        ),

        parameter_rank_mean=(
            "parameter_rank",
            "mean"
        ),
    )
)


average_ranks.to_csv(
    ANALYSIS /
    "cross_dataset_average_ranks.csv",
    index=False
)


print(
    average_ranks
    .sort_values(
        [
            "corrupted_accuracy_rank_mean",
            "clean_macro_f1_rank_mean"
        ]
    )
    .to_string(
        index=False
    )
)


print()
print(
    "8. PAIRED 5-SEED TESTS WITHIN EACH DATASET"
)
print(
    "-" * 78
)


merged_seed = clean_df[
    [
        "dataset",
        "model",
        "seed",
        "accuracy",
        "macro_f1",
    ]
].merge(

    reliability_df[
        [
            "dataset",
            "model",
            "seed",
            "reliability_score",
            "corrupted_accuracy",
            "corrupted_macro_f1",
        ]
    ],

    on=[
        "dataset",
        "model",
        "seed"
    ],

    how="inner"
)


paired_rows = []


ANCHORS = [
    "ReliabilityCNN_v22",
    "ReliabilityCNN_v24",
]


METRICS = [
    "accuracy",
    "macro_f1",
    "reliability_score",
    "corrupted_accuracy",
    "corrupted_macro_f1",
]


for dataset in DATASETS:

    subset = merged_seed[
        merged_seed[
            "dataset"
        ]
        ==
        dataset
    ]


    for anchor in ANCHORS:

        for competitor in MODELS:

            if competitor == anchor:
                continue


            anchor_df = (
                subset[
                    subset[
                        "model"
                    ]
                    ==
                    anchor
                ]
                .set_index(
                    "seed"
                )
            )


            competitor_df = (
                subset[
                    subset[
                        "model"
                    ]
                    ==
                    competitor
                ]
                .set_index(
                    "seed"
                )
            )


            common = sorted(
                set(
                    anchor_df.index
                )
                &
                set(
                    competitor_df.index
                )
            )


            require(
                common
                ==
                SEEDS,
                (
                    f"Paired seed mismatch: "
                    f"{dataset}/"
                    f"{anchor}/"
                    f"{competitor}: "
                    f"{common}"
                ),
                errors
            )


            for metric in METRICS:

                result = paired_test(

                    anchor_df.loc[
                        common,
                        metric
                    ].to_numpy(),

                    competitor_df.loc[
                        common,
                        metric
                    ].to_numpy()
                )


                paired_rows.append(
                    {

                        "dataset":
                            dataset,

                        "anchor_model":
                            anchor,

                        "competitor_model":
                            competitor,

                        "metric":
                            metric,

                        **result,
                    }
                )


paired_df = pd.DataFrame(
    paired_rows
)


paired_df.to_csv(
    ANALYSIS /
    "paired_seed_tests_v22_v24_vs_competitors.csv",
    index=False
)


print(
    "PAIRED_TEST_ROWS=",
    len(
        paired_df
    )
)

print(
    "SCIPY_AVAILABLE=",
    SCIPY_AVAILABLE
)


print()
print(
    "9. EXPLORATORY FRIEDMAN TEST ACROSS FOUR DATASETS"
)
print(
    "-" * 78
)


friedman_rows = []


if SCIPY_AVAILABLE:

    for metric in [
        "accuracy_mean",
        "macro_f1_mean",
        "reliability_score_mean",
        "corrupted_accuracy_mean",
        "corrupted_macro_f1_mean",
    ]:

        vectors = []


        for model in MODELS:

            values = (
                dataset_model[
                    dataset_model[
                        "model"
                    ]
                    ==
                    model
                ]
                .set_index(
                    "dataset"
                )
                .loc[
                    DATASETS,
                    metric
                ]
                .to_numpy(
                    dtype=float
                )
            )


            vectors.append(
                values
            )


        try:

            statistic, pvalue = (
                stats.friedmanchisquare(
                    *vectors
                )
            )


            friedman_rows.append(
                {

                    "metric":
                        metric,

                    "dataset_blocks":
                        4,

                    "model_count":
                        9,

                    "friedman_statistic":
                        float(
                            statistic
                        ),

                    "pvalue":
                        float(
                            pvalue
                        ),

                    "interpretation_boundary":
                        (
                            "exploratory only; "
                            "only four dataset blocks"
                        ),
                }
            )

        except Exception as exc:

            warnings.append(
                f"Friedman failed for "
                f"{metric}: {exc}"
            )


friedman_df = pd.DataFrame(
    friedman_rows
)


friedman_df.to_csv(
    ANALYSIS /
    "friedman_cross_dataset_exploratory.csv",
    index=False
)


if len(
    friedman_df
):

    print(
        friedman_df.to_string(
            index=False
        )
    )

else:

    print(
        "NO_FRIEDMAN_RESULTS"
    )


print()
print(
    "10. BEST MODEL PER DATASET / METRIC"
)
print(
    "-" * 78
)


best_rows = []


BEST_METRICS = {

    "clean_accuracy":
        (
            "accuracy_mean",
            False
        ),

    "clean_macro_f1":
        (
            "macro_f1_mean",
            False
        ),

    "reliability_score":
        (
            "reliability_score_mean",
            False
        ),

    "corrupted_accuracy":
        (
            "corrupted_accuracy_mean",
            False
        ),

    "corrupted_macro_f1":
        (
            "corrupted_macro_f1_mean",
            False
        ),

    "parameters":
        (
            "parameters_mean",
            True
        ),
}


for dataset in DATASETS:

    subset = dataset_model[
        dataset_model[
            "dataset"
        ]
        ==
        dataset
    ]


    for label, (
        column,
        lower_better
    ) in BEST_METRICS.items():

        if lower_better:

            index = subset[
                column
            ].idxmin()

        else:

            index = subset[
                column
            ].idxmax()


        winner = subset.loc[
            index
        ]


        best_rows.append(
            {

                "dataset":
                    dataset,

                "metric":
                    label,

                "best_model":
                    winner[
                        "model"
                    ],

                "value":
                    float(
                        winner[
                            column
                        ]
                    ),
            }
        )


best_df = pd.DataFrame(
    best_rows
)


best_df.to_csv(
    ANALYSIS /
    "best_model_by_dataset_metric.csv",
    index=False
)


print(
    best_df.to_string(
        index=False
    )
)


print()
print(
    "11. FINAL EVIDENCE FREEZE RECEIPT"
)
print(
    "-" * 78
)


analysis_files = [

    ANALYSIS /
    "clean_runs_180.csv",

    ANALYSIS /
    "reliability_runs_180.csv",

    ANALYSIS /
    "reliability_family_runs_720.csv",

    ANALYSIS /
    "reliability_cases_5940.csv",

    ANALYSIS /
    "dataset_model_summary_36.csv",

    ANALYSIS /
    "reliability_family_summary_144.csv",

    ANALYSIS /
    "cross_dataset_model_summary_9.csv",

    ANALYSIS /
    "dataset_model_ranks.csv",

    ANALYSIS /
    "cross_dataset_average_ranks.csv",

    ANALYSIS /
    "paired_seed_tests_v22_v24_vs_competitors.csv",

    ANALYSIS /
    "friedman_cross_dataset_exploratory.csv",

    ANALYSIS /
    "best_model_by_dataset_metric.csv",
]


analysis_hashes = {

    str(
        path
    ):
        sha256_file(
            path
        )

    for path in analysis_files
    if path.exists()
}


execution_receipt = {

    "benchmark":
        "benchmark_v3r1",

    "integrity_pass":
        True,

    "protocol_manifest_sha256":
        protocol_sha,

    "frozen_corruption_registry_sha256":
        corruption_sha,

    "expected_clean_runs":
        180,

    "verified_clean_runs":
        len(
            clean_seen
        ),

    "expected_reliability_runs":
        180,

    "verified_reliability_runs":
        len(
            rel_seen
        ),

    "expected_corruption_cases":
        180 * 33,

    "verified_corruption_cases":
        len(
            case_rows
        ),

    "dataset_count":
        4,

    "model_count":
        9,

    "seed_count":
        5,

    "reliability_family_count":
        4,

    "aggregation_policy":
        (
            "seed -> family mean; "
            "family-balanced seed reliability; "
            "5-seed dataset/model mean; "
            "equal-dataset-weight cross-dataset mean"
        ),

    "statistical_boundary":
        (
            "paired tests are within-dataset "
            "five-seed development comparisons; "
            "Friedman across four datasets is "
            "exploratory due to only four blocks"
        ),

    "analysis_hashes":
        analysis_hashes,

    "warnings":
        warnings,
}


receipt_path = (
    ANALYSIS /
    "benchmark_v3r1_final_integrity_receipt.json"
)


receipt_path.write_text(
    json.dumps(
        execution_receipt,
        indent=2,
        sort_keys=True
    )
)


print(
    "FINAL_RECEIPT=",
    receipt_path
)

print(
    "FINAL_RECEIPT_SHA256=",
    sha256_file(
        receipt_path
    )
)


print()
print(
    "=" * 78
)

print(
    "BENCHMARK_V3R1_FINAL_INTEGRITY_AND_AGGREGATION_PASS=True"
)

print(
    "CLEAN_RUNS=180"
)

print(
    "RELIABILITY_RUNS=180"
)

print(
    "RELIABILITY_CASES=5940"
)

print(
    "DATASET_MODEL_SUMMARIES=36"
)

print(
    "CROSS_DATASET_MODELS=9"
)

print(
    "=" * 78
)
