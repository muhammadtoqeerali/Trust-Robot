from pathlib import Path
import hashlib
import itertools
import json
import math
import sys

import numpy as np
import pandas as pd

try:
    from scipy import stats
    SCIPY_AVAILABLE = True
except Exception:
    SCIPY_AVAILABLE = False


SUITE = Path(
    "experiments/16_benchmark_suite"
).resolve()

if str(SUITE) not in sys.path:
    sys.path.insert(
        0,
        str(SUITE)
    )


from engine.reliability_score import (
    create_reliability_summary
)


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

FROZEN_REGISTRY = (
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


EXPECTED_CASES_PER_RUN = 33

EXPECTED_RUNS = (
    len(DATASETS)
    *
    len(MODELS)
    *
    len(SEEDS)
)

EXPECTED_CASES_TOTAL = (
    EXPECTED_RUNS
    *
    EXPECTED_CASES_PER_RUN
)


def load_json(path):

    return json.loads(
        Path(path).read_text()
    )


def sha256_file(path):

    h = hashlib.sha256()

    with Path(path).open(
        "rb"
    ) as f:

        while True:

            block = f.read(
                1024 * 1024
            )

            if not block:
                break

            h.update(
                block
            )

    return h.hexdigest()


def save_json(path, data):

    path = Path(path)

    path.write_text(
        json.dumps(
            data,
            indent=2,
            sort_keys=True
        )
    )


def numeric(value):

    try:
        return float(value)
    except Exception:
        return np.nan


def require(
    condition,
    message,
    errors
):

    if not condition:
        errors.append(
            message
        )


def mean_std(values):

    values = np.asarray(
        [
            float(x)
            for x in values
            if np.isfinite(
                float(x)
            )
        ],
        dtype=float
    )

    if len(values) == 0:
        return np.nan, np.nan

    mean = float(
        values.mean()
    )

    std = (
        float(
            values.std(
                ddof=1
            )
        )
        if len(values) > 1
        else 0.0
    )

    return mean, std


def find_family_summary(
    obj,
    family
):

    if isinstance(
        obj,
        dict
    ):

        value = obj.get(
            family
        )

        if (
            isinstance(
                value,
                dict
            )
            and
            "reliability_score_mean"
            in value
        ):
            return value


        if (
            obj.get(
                "family"
            )
            ==
            family
            and
            "reliability_score_mean"
            in obj
        ):
            return obj


        for value in obj.values():

            result = (
                find_family_summary(
                    value,
                    family
                )
            )

            if result is not None:
                return result


    elif isinstance(
        obj,
        list
    ):

        for value in obj:

            result = (
                find_family_summary(
                    value,
                    family
                )
            )

            if result is not None:
                return result


    return None


def case_specs(
    registry
):

    channels = registry[
        "channels"
    ]

    corruption_seeds = registry[
        "corruption_seeds"
    ]

    corruptions = registry[
        "corruptions"
    ]


    specs = []


    for channel in (
        corruptions[
            "missing_channel"
        ][
            "channel_indices"
        ]
    ):

        label = channels[
            int(channel)
        ]

        specs.append(
            {
                "family":
                    "missing_channel",

                "condition_id":
                    (
                        f"channel_"
                        f"{int(channel)}_"
                        f"{label}"
                    ),

                "condition_value":
                    (
                        f"channel_"
                        f"{int(channel)}_"
                        f"{label}"
                    ),

                "corruption_seed":
                    None,

                "relative_metrics_path":
                    Path(
                        "missing_channel"
                    )
                    /
                    (
                        f"channel_"
                        f"{int(channel)}_"
                        f"{label}"
                    )
                    /
                    "metrics.json",
            }
        )


    for ratio in (
        corruptions[
            "random_dropout"
        ][
            "drop_ratio"
        ]
    ):

        for corruption_seed in (
            corruption_seeds
        ):

            specs.append(
                {
                    "family":
                        "random_dropout",

                    "condition_id":
                        (
                            f"drop_{ratio}_"
                            f"seed_{corruption_seed}"
                        ),

                    "condition_value":
                        float(
                            ratio
                        ),

                    "corruption_seed":
                        int(
                            corruption_seed
                        ),

                    "relative_metrics_path":
                        Path(
                            "random_dropout"
                        )
                        /
                        f"drop_{ratio}"
                        /
                        (
                            f"seed_"
                            f"{corruption_seed}"
                        )
                        /
                        "metrics.json",
                }
            )


    for snr_db in (
        corruptions[
            "gaussian_noise"
        ][
            "snr_db"
        ]
    ):

        for corruption_seed in (
            corruption_seeds
        ):

            specs.append(
                {
                    "family":
                        "gaussian_noise",

                    "condition_id":
                        (
                            f"snr_{snr_db}db_"
                            f"seed_{corruption_seed}"
                        ),

                    "condition_value":
                        float(
                            snr_db
                        ),

                    "corruption_seed":
                        int(
                            corruption_seed
                        ),

                    "relative_metrics_path":
                        Path(
                            "gaussian_noise"
                        )
                        /
                        f"snr_{snr_db}db"
                        /
                        (
                            f"seed_"
                            f"{corruption_seed}"
                        )
                        /
                        "metrics.json",
                }
            )


    for bias_scale in (
        corruptions[
            "sensor_drift"
        ][
            "bias_scale"
        ]
    ):

        for corruption_seed in (
            corruption_seeds
        ):

            specs.append(
                {
                    "family":
                        "sensor_drift",

                    "condition_id":
                        (
                            f"bias_{bias_scale}_"
                            f"seed_{corruption_seed}"
                        ),

                    "condition_value":
                        float(
                            bias_scale
                        ),

                    "corruption_seed":
                        int(
                            corruption_seed
                        ),

                    "relative_metrics_path":
                        Path(
                            "sensor_drift"
                        )
                        /
                        f"bias_{bias_scale}"
                        /
                        (
                            f"seed_"
                            f"{corruption_seed}"
                        )
                        /
                        "metrics.json",
                }
            )


    return specs


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

    mask = (
        np.isfinite(a)
        &
        np.isfinite(b)
    )

    a = a[mask]
    b = b[mask]

    diff = a - b


    result = {
        "n":
            int(
                len(diff)
            ),

        "mean_difference":
            np.nan,

        "cohen_dz":
            np.nan,

        "paired_t_pvalue":
            np.nan,

        "wilcoxon_pvalue":
            np.nan,

        "anchor_higher_count":
            int(
                np.sum(
                    diff > 0
                )
            ),

        "competitor_higher_count":
            int(
                np.sum(
                    diff < 0
                )
            ),

        "equal_count":
            int(
                np.sum(
                    diff == 0
                )
            ),
    }


    if len(diff) == 0:
        return result


    result[
        "mean_difference"
    ] = float(
        np.mean(
            diff
        )
    )


    if len(diff) > 1:

        sd = float(
            np.std(
                diff,
                ddof=1
            )
        )

        if sd > 0:

            result[
                "cohen_dz"
            ] = float(
                np.mean(
                    diff
                )
                /
                sd
            )


    if (
        SCIPY_AVAILABLE
        and
        len(diff) >= 2
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
                diff,
                0
            ):

                result[
                    "wilcoxon_pvalue"
                ] = float(
                    stats.wilcoxon(
                        diff
                    ).pvalue
                )

        except Exception:
            pass


    return result


print(
    "=" * 78
)

print(
    "BENCHMARK V3R1 FINAL ANALYSIS R2"
)

print(
    "CASE-LEVEL RECONSTRUCTION FROM FROZEN METRICS"
)

print(
    "=" * 78
)


errors = []

warnings = []


require(
    PROTOCOL_MANIFEST.exists(),
    (
        "Missing protocol manifest: "
        f"{PROTOCOL_MANIFEST}"
    ),
    errors
)

require(
    FROZEN_REGISTRY.exists(),
    (
        "Missing frozen registry: "
        f"{FROZEN_REGISTRY}"
    ),
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

registry = load_json(
    FROZEN_REGISTRY
)


require(
    registry.get(
        "version"
    )
    ==
    "v2",
    "Frozen corruption registry is not V2",
    errors
)


protocol_sha = sha256_file(
    PROTOCOL_MANIFEST
)

registry_sha = sha256_file(
    FROZEN_REGISTRY
)


print(
    "PROTOCOL_SHA256=",
    protocol_sha
)

print(
    "REGISTRY_SHA256=",
    registry_sha
)


print()
print(
    "1. FROZEN INPUT HASH VERIFICATION"
)
print(
    "-" * 78
)


hash_inventory = protocol.get(
    "hashes",
    {}
)

hash_verified = 0


for path_text, expected in (
    hash_inventory.items()
):

    path = Path(
        path_text
    )

    require(
        path.exists(),
        (
            "Missing frozen input: "
            f"{path}"
        ),
        errors
    )

    if not path.exists():
        continue


    actual = sha256_file(
        path
    )


    require(
        actual == expected,
        (
            "Frozen SHA mismatch: "
            f"{path}"
        ),
        errors
    )


    if actual == expected:
        hash_verified += 1


print(
    "FROZEN_HASHES_EXPECTED=",
    len(hash_inventory)
)

print(
    "FROZEN_HASHES_VERIFIED=",
    hash_verified
)


print()
print(
    "2. ACTUAL RELIABILITY SUMMARY SCHEMA"
)
print(
    "-" * 78
)


example_summary_path = (
    REL /
    "UCI_HAR" /
    "CNN1D" /
    "seed_42" /
    "reliability_summary_v2.json"
)


example_summary = load_json(
    example_summary_path
)


print(
    "EXAMPLE_SUMMARY=",
    example_summary_path
)

print(
    "TOP_LEVEL_KEYS=",
    sorted(
        example_summary.keys()
    )
)


def schema_view(
    value,
    depth=0,
    max_depth=3
):

    prefix = "  " * depth

    if depth > max_depth:
        return

    if isinstance(
        value,
        dict
    ):

        for key, child in value.items():

            print(
                f"{prefix}{key}: "
                f"{type(child).__name__}"
            )

            if isinstance(
                child,
                (
                    dict,
                    list
                )
            ):
                schema_view(
                    child,
                    depth + 1,
                    max_depth
                )


    elif isinstance(
        value,
        list
    ):

        print(
            f"{prefix}LIST_LEN={len(value)}"
        )

        if value:
            schema_view(
                value[0],
                depth + 1,
                max_depth
            )


schema_view(
    example_summary
)


specs = case_specs(
    registry
)


print()
print(
    "3. FROZEN CASE SPECIFICATION"
)
print(
    "-" * 78
)

print(
    "CASES_PER_RELIABILITY_RUN=",
    len(specs)
)


family_spec_counts = {
    family:
        sum(
            1
            for spec in specs
            if spec[
                "family"
            ]
            ==
            family
        )
    for family in FAMILIES
}


print(
    "FAMILY_CASE_COUNTS=",
    family_spec_counts
)


require(
    len(specs)
    ==
    EXPECTED_CASES_PER_RUN,
    (
        f"Registry defines {len(specs)} "
        "cases instead of 33"
    ),
    errors
)


require(
    family_spec_counts
    ==
    EXPECTED_FAMILY_CASES,
    (
        "Registry family case counts "
        "do not match frozen expectation"
    ),
    errors
)


clean_rows = []

case_rows = []

family_rows = []

reliability_rows = []


expected_combinations = list(
    itertools.product(
        DATASETS,
        MODELS,
        SEEDS
    )
)


print()
print(
    "4. VERIFY + LOAD 180 CLEAN RUNS"
)
print(
    "-" * 78
)


for (
    dataset,
    model,
    seed
) in expected_combinations:

    run_dir = (
        RAW /
        dataset /
        model /
        f"seed_{seed}"
    )


    required = [
        run_dir /
        "COMPLETE",

        run_dir /
        "best_model.pt",

        run_dir /
        "checkpoint.pt",

        run_dir /
        "metrics.json",

        run_dir /
        "config.json",

        run_dir /
        "dataset_summary.json",

        run_dir /
        "receipt.json",
    ]


    for path in required:

        require(
            path.exists(),
            (
                "Missing clean artifact: "
                f"{path}"
            ),
            errors
        )


    if not all(
        path.exists()
        for path in required
    ):
        continue


    metrics = load_json(
        run_dir /
        "metrics.json"
    )

    receipt = load_json(
        run_dir /
        "receipt.json"
    )


    best_sha = sha256_file(
        run_dir /
        "best_model.pt"
    )

    checkpoint_sha = sha256_file(
        run_dir /
        "checkpoint.pt"
    )


    require(
        best_sha
        ==
        checkpoint_sha,
        (
            "Checkpoint copy mismatch: "
            f"{dataset}/{model}/{seed}"
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
            "Clean protocol receipt mismatch: "
            f"{dataset}/{model}/{seed}"
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
            "Clean best-model SHA mismatch: "
            f"{dataset}/{model}/{seed}"
        ),
        errors
    )


    test = metrics.get(
        "test",
        {}
    )


    accuracy = numeric(
        test.get(
            "accuracy"
        )
    )

    macro_f1 = numeric(
        test.get(
            "macro_f1"
        )
    )


    require(
        np.isfinite(
            accuracy
        ),
        (
            "Invalid clean accuracy: "
            f"{dataset}/{model}/{seed}"
        ),
        errors
    )


    require(
        np.isfinite(
            macro_f1
        ),
        (
            "Invalid clean macro-F1: "
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
                numeric(
                    metrics.get(
                        "parameters"
                    )
                ),

            "checkpoint_size_mb":
                numeric(
                    metrics.get(
                        "checkpoint_size_mb"
                    )
                ),

            "training_seconds":
                numeric(
                    metrics.get(
                        "training_seconds"
                    )
                ),

            "best_epoch":
                numeric(
                    metrics.get(
                        "best_epoch"
                    )
                ),

            "best_validation_macro_f1":
                numeric(
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
        }
    )


print(
    "CLEAN_ROWS=",
    len(clean_rows),
    "/",
    EXPECTED_RUNS
)


print()
print(
    "5. VERIFY 180 RELIABILITY RECEIPTS"
)
print(
    "-" * 78
)


rel_receipt_verified = 0


for (
    dataset,
    model,
    seed
) in expected_combinations:

    rel_dir = (
        REL /
        dataset /
        model /
        f"seed_{seed}"
    )


    summary_path = (
        rel_dir /
        "reliability_summary_v2.json"
    )

    receipt_path = (
        rel_dir /
        "receipt.json"
    )

    complete_path = (
        rel_dir /
        "COMPLETE"
    )


    require(
        summary_path.exists(),
        (
            "Missing reliability summary: "
            f"{summary_path}"
        ),
        errors
    )

    require(
        receipt_path.exists(),
        (
            "Missing reliability receipt: "
            f"{receipt_path}"
        ),
        errors
    )

    require(
        complete_path.exists(),
        (
            "Missing reliability COMPLETE: "
            f"{complete_path}"
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


    receipt = load_json(
        receipt_path
    )


    require(
        receipt.get(
            "protocol_manifest_sha256"
        )
        ==
        protocol_sha,
        (
            "Reliability protocol SHA mismatch: "
            f"{dataset}/{model}/{seed}"
        ),
        errors
    )


    require(
        receipt.get(
            "corruption_registry_sha256"
        )
        ==
        registry_sha,
        (
            "Reliability registry SHA mismatch: "
            f"{dataset}/{model}/{seed}"
        ),
        errors
    )


    require(
        receipt.get(
            "summary_sha256"
        )
        ==
        sha256_file(
            summary_path
        ),
        (
            "Reliability summary SHA mismatch: "
            f"{dataset}/{model}/{seed}"
        ),
        errors
    )


    clean_checkpoint = (
        RAW /
        dataset /
        model /
        f"seed_{seed}" /
        "best_model.pt"
    )


    require(
        receipt.get(
            "clean_checkpoint_sha256"
        )
        ==
        sha256_file(
            clean_checkpoint
        ),
        (
            "Reliability checkpoint linkage "
            "mismatch: "
            f"{dataset}/{model}/{seed}"
        ),
        errors
    )


    rel_receipt_verified += 1


print(
    "RELIABILITY_RECEIPTS_VERIFIED=",
    rel_receipt_verified,
    "/",
    EXPECTED_RUNS
)


print()
print(
    "6. RECONSTRUCT 5,940 CASES FROM FROZEN METRICS"
)
print(
    "-" * 78
)


for index, (
    dataset,
    model,
    seed
) in enumerate(
    expected_combinations,
    start=1
):

    raw_metrics = load_json(
        RAW /
        dataset /
        model /
        f"seed_{seed}" /
        "metrics.json"
    )


    raw_test = raw_metrics[
        "test"
    ]


    rel_dir = (
        REL /
        dataset /
        model /
        f"seed_{seed}"
    )


    clean_metrics_path = (
        rel_dir /
        "clean" /
        "metrics.json"
    )


    require(
        clean_metrics_path.exists(),
        (
            "Missing reliability clean metrics: "
            f"{clean_metrics_path}"
        ),
        errors
    )


    if not clean_metrics_path.exists():
        continue


    rel_clean = load_json(
        clean_metrics_path
    )


    require(
        abs(
            numeric(
                raw_test[
                    "accuracy"
                ]
            )
            -
            numeric(
                rel_clean[
                    "accuracy"
                ]
            )
        )
        <
        1e-12,
        (
            "Clean accuracy mismatch between "
            "training test and reliability clean: "
            f"{dataset}/{model}/{seed}"
        ),
        errors
    )


    require(
        abs(
            numeric(
                raw_test[
                    "macro_f1"
                ]
            )
            -
            numeric(
                rel_clean[
                    "macro_f1"
                ]
            )
        )
        <
        1e-12,
        (
            "Clean macro-F1 mismatch between "
            "training test and reliability clean: "
            f"{dataset}/{model}/{seed}"
        ),
        errors
    )


    reconstructed_cases = []


    for spec in specs:

        metrics_path = (
            rel_dir /
            spec[
                "relative_metrics_path"
            ]
        )


        require(
            metrics_path.exists(),
            (
                "Missing corruption metrics: "
                f"{metrics_path}"
            ),
            errors
        )


        if not metrics_path.exists():
            continue


        corrupted = load_json(
            metrics_path
        )


        case = create_reliability_summary(
            rel_clean,
            corrupted,
            spec[
                "family"
            ],
            spec[
                "condition_value"
            ]
        )


        case = dict(
            case
        )


        case.update(
            {
                "protocol_version":
                    "v2",

                "family":
                    spec[
                        "family"
                    ],

                "condition_id":
                    spec[
                        "condition_id"
                    ],

                "condition_value":
                    spec[
                        "condition_value"
                    ],

                "corruption_seed":
                    spec[
                        "corruption_seed"
                    ],

                "clean_metrics":
                    {
                        "accuracy":
                            numeric(
                                rel_clean[
                                    "accuracy"
                                ]
                            ),

                        "macro_f1":
                            numeric(
                                rel_clean[
                                    "macro_f1"
                                ]
                            ),
                    },

                "corrupted_metrics":
                    {
                        "accuracy":
                            numeric(
                                corrupted[
                                    "accuracy"
                                ]
                            ),

                        "macro_f1":
                            numeric(
                                corrupted[
                                    "macro_f1"
                                ]
                            ),
                    },
            }
        )


        reconstructed_cases.append(
            case
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
                    spec[
                        "family"
                    ],

                "condition_id":
                    spec[
                        "condition_id"
                    ],

                "condition_value":
                    spec[
                        "condition_value"
                    ],

                "corruption_seed":
                    spec[
                        "corruption_seed"
                    ],

                "clean_accuracy":
                    numeric(
                        rel_clean[
                            "accuracy"
                        ]
                    ),

                "clean_macro_f1":
                    numeric(
                        rel_clean[
                            "macro_f1"
                        ]
                    ),

                "corrupted_accuracy":
                    numeric(
                        corrupted[
                            "accuracy"
                        ]
                    ),

                "corrupted_macro_f1":
                    numeric(
                        corrupted[
                            "macro_f1"
                        ]
                    ),

                "reliability_score":
                    numeric(
                        case[
                            "reliability_score"
                        ]
                    ),

                "relative_accuracy_degradation":
                    numeric(
                        case[
                            "degradation"
                        ][
                            "accuracy_degradation"
                        ]
                    ),

                "relative_macro_f1_degradation":
                    numeric(
                        case[
                            "degradation"
                        ][
                            "macro_f1_degradation"
                        ]
                    ),

                "metrics_path":
                    str(
                        metrics_path
                    ),

                "metrics_sha256":
                    sha256_file(
                        metrics_path
                    ),
            }
        )


    require(
        len(
            reconstructed_cases
        )
        ==
        EXPECTED_CASES_PER_RUN,
        (
            "Reconstructed case count mismatch: "
            f"{dataset}/{model}/{seed}: "
            f"{len(reconstructed_cases)}"
        ),
        errors
    )


    seed_family_rows = []


    for family in FAMILIES:

        family_cases = [
            case
            for case
            in reconstructed_cases
            if case[
                "family"
            ]
            ==
            family
        ]


        require(
            len(
                family_cases
            )
            ==
            EXPECTED_FAMILY_CASES[
                family
            ],
            (
                "Reconstructed family count "
                "mismatch: "
                f"{dataset}/{model}/{seed}/"
                f"{family}"
            ),
            errors
        )


        if not family_cases:
            continue


        family_row = {
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
                        [
                            numeric(
                                case[
                                    "reliability_score"
                                ]
                            )
                            for case
                            in family_cases
                        ]
                    )
                ),

            "corrupted_accuracy":
                float(
                    np.mean(
                        [
                            numeric(
                                case[
                                    "corrupted_metrics"
                                ][
                                    "accuracy"
                                ]
                            )
                            for case
                            in family_cases
                        ]
                    )
                ),

            "corrupted_macro_f1":
                float(
                    np.mean(
                        [
                            numeric(
                                case[
                                    "corrupted_metrics"
                                ][
                                    "macro_f1"
                                ]
                            )
                            for case
                            in family_cases
                        ]
                    )
                ),

            "relative_accuracy_degradation":
                float(
                    np.mean(
                        [
                            numeric(
                                case[
                                    "degradation"
                                ][
                                    "accuracy_degradation"
                                ]
                            )
                            for case
                            in family_cases
                        ]
                    )
                ),

            "relative_macro_f1_degradation":
                float(
                    np.mean(
                        [
                            numeric(
                                case[
                                    "degradation"
                                ][
                                    "macro_f1_degradation"
                                ]
                            )
                            for case
                            in family_cases
                        ]
                    )
                ),
        }


        family_rows.append(
            family_row
        )

        seed_family_rows.append(
            family_row
        )


    require(
        len(
            seed_family_rows
        )
        ==
        4,
        (
            "Missing reconstructed family "
            "summaries: "
            f"{dataset}/{model}/{seed}"
        ),
        errors
    )


    summary = load_json(
        rel_dir /
        "reliability_summary_v2.json"
    )


    for family_row in (
        seed_family_rows
    ):

        stored = (
            find_family_summary(
                summary,
                family_row[
                    "family"
                ]
            )
        )


        if stored is None:

            warnings.append(
                (
                    "Stored summary family "
                    "aggregate not discoverable "
                    f"for {dataset}/{model}/{seed}/"
                    f"{family_row['family']}; "
                    "case metrics remain authoritative"
                )
            )

            continue


        pairs = [
            (
                "n_cases",
                family_row[
                    "n_cases"
                ]
            ),

            (
                "reliability_score_mean",
                family_row[
                    "reliability_score"
                ]
            ),

            (
                "corrupted_accuracy_mean",
                family_row[
                    "corrupted_accuracy"
                ]
            ),

            (
                "corrupted_macro_f1_mean",
                family_row[
                    "corrupted_macro_f1"
                ]
            ),

            (
                "relative_accuracy_degradation_mean",
                family_row[
                    "relative_accuracy_degradation"
                ]
            ),

            (
                "relative_macro_f1_degradation_mean",
                family_row[
                    "relative_macro_f1_degradation"
                ]
            ),
        ]


        for key, reconstructed in pairs:

            if key not in stored:
                continue


            stored_value = numeric(
                stored[
                    key
                ]
            )


            require(
                abs(
                    stored_value
                    -
                    float(
                        reconstructed
                    )
                )
                <
                1e-10,
                (
                    "Stored/reconstructed "
                    "family aggregate mismatch: "
                    f"{dataset}/{model}/{seed}/"
                    f"{family_row['family']}/"
                    f"{key}: "
                    f"stored={stored_value}, "
                    f"reconstructed={reconstructed}"
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
                    numeric(
                        rel_clean[
                            "accuracy"
                        ]
                    ),

                "clean_macro_f1":
                    numeric(
                        rel_clean[
                            "macro_f1"
                        ]
                    ),

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
                        reconstructed_cases
                    ),

                "summary_sha256":
                    sha256_file(
                        rel_dir /
                        "reliability_summary_v2.json"
                    ),
            }
        )


    if (
        index % 20 == 0
        or
        index == EXPECTED_RUNS
    ):

        print(
            "RECONSTRUCTION_PROGRESS=",
            f"{index}/{EXPECTED_RUNS}",
            "CASES=",
            len(case_rows)
        )


print()
print(
    "7. INTEGRITY CLASSIFICATION"
)
print(
    "-" * 78
)


print(
    "CLEAN_RUNS_PARSED=",
    len(clean_rows),
    "/",
    EXPECTED_RUNS
)

print(
    "RELIABILITY_RUNS_PARSED=",
    len(reliability_rows),
    "/",
    EXPECTED_RUNS
)

print(
    "CASE_ROWS_PARSED=",
    len(case_rows),
    "/",
    EXPECTED_CASES_TOTAL
)

print(
    "FAMILY_ROWS_PARSED=",
    len(family_rows),
    "/",
    EXPECTED_RUNS * 4
)

print(
    "WARNING_COUNT=",
    len(warnings)
)

print(
    "ERROR_COUNT=",
    len(errors)
)


if warnings:

    (
        ANALYSIS /
        "analysis_r2_warnings.txt"
    ).write_text(
        "\n".join(
            warnings
        )
        +
        "\n"
    )


if errors:

    (
        ANALYSIS /
        "analysis_r2_errors.txt"
    ).write_text(
        "\n".join(
            errors
        )
        +
        "\n"
    )


    print(
        "BENCHMARK_V3R1_R2_INTEGRITY_PASS=False"
    )


    for error in errors[:100]:

        print(
            "ERROR:",
            error
        )


    if len(errors) > 100:

        print(
            "ADDITIONAL_ERRORS=",
            len(errors) - 100
        )


    raise SystemExit(3)


require(
    len(clean_rows)
    ==
    EXPECTED_RUNS,
    "Clean row count != 180",
    errors
)

require(
    len(reliability_rows)
    ==
    EXPECTED_RUNS,
    "Reliability row count != 180",
    errors
)

require(
    len(case_rows)
    ==
    EXPECTED_CASES_TOTAL,
    "Case row count != 5940",
    errors
)

require(
    len(family_rows)
    ==
    EXPECTED_RUNS * 4,
    "Family row count != 720",
    errors
)


if errors:

    for error in errors:
        print(
            "ERROR:",
            error
        )

    raise SystemExit(4)


print(
    "BENCHMARK_V3R1_R2_INTEGRITY_PASS=True"
)


clean_df = (
    pd.DataFrame(
        clean_rows
    )
    .sort_values(
        [
            "dataset",
            "model",
            "seed"
        ]
    )
)


rel_df = (
    pd.DataFrame(
        reliability_rows
    )
    .sort_values(
        [
            "dataset",
            "model",
            "seed"
        ]
    )
)


family_df = (
    pd.DataFrame(
        family_rows
    )
    .sort_values(
        [
            "dataset",
            "model",
            "seed",
            "family"
        ]
    )
)


case_df = (
    pd.DataFrame(
        case_rows
    )
    .sort_values(
        [
            "dataset",
            "model",
            "seed",
            "family",
            "condition_id"
        ]
    )
)


clean_df.to_csv(
    ANALYSIS /
    "clean_runs_180.csv",
    index=False
)


rel_df.to_csv(
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
    "8. DATASET × MODEL SUMMARY"
)
print(
    "-" * 78
)


summary_rows = []


for dataset in DATASETS:

    for model in MODELS:

        clean_group = clean_df[
            (
                clean_df[
                    "dataset"
                ]
                ==
                dataset
            )
            &
            (
                clean_df[
                    "model"
                ]
                ==
                model
            )
        ]


        rel_group = rel_df[
            (
                rel_df[
                    "dataset"
                ]
                ==
                dataset
            )
            &
            (
                rel_df[
                    "model"
                ]
                ==
                model
            )
        ]


        row = {
            "dataset":
                dataset,

            "model":
                model,

            "n_seeds":
                len(
                    clean_group
                ),
        }


        for source, column, out in [
            (
                clean_group,
                "accuracy",
                "accuracy"
            ),

            (
                clean_group,
                "macro_f1",
                "macro_f1"
            ),

            (
                clean_group,
                "training_seconds",
                "training_seconds"
            ),

            (
                clean_group,
                "parameters",
                "parameters"
            ),

            (
                clean_group,
                "checkpoint_size_mb",
                "checkpoint_size_mb"
            ),

            (
                rel_group,
                "reliability_score",
                "reliability_score"
            ),

            (
                rel_group,
                "corrupted_accuracy",
                "corrupted_accuracy"
            ),

            (
                rel_group,
                "corrupted_macro_f1",
                "corrupted_macro_f1"
            ),

            (
                rel_group,
                "relative_accuracy_degradation",
                "relative_accuracy_degradation"
            ),

            (
                rel_group,
                "relative_macro_f1_degradation",
                "relative_macro_f1_degradation"
            ),
        ]:

            mean, std = mean_std(
                source[
                    column
                ].tolist()
            )

            row[
                f"{out}_mean"
            ] = mean

            row[
                f"{out}_std"
            ] = std


        summary_rows.append(
            row
        )


dataset_model_df = (
    pd.DataFrame(
        summary_rows
    )
)


dataset_model_df.to_csv(
    ANALYSIS /
    "dataset_model_summary_36.csv",
    index=False
)


print(
    "DATASET_MODEL_ROWS=",
    len(dataset_model_df)
)


print()
print(
    "9. FAMILY SUMMARY"
)
print(
    "-" * 78
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
            len(group),
    }


    for column in [
        "reliability_score",
        "corrupted_accuracy",
        "corrupted_macro_f1",
        "relative_accuracy_degradation",
        "relative_macro_f1_degradation",
    ]:

        mean, std = mean_std(
            group[
                column
            ].tolist()
        )

        row[
            f"{column}_mean"
        ] = mean

        row[
            f"{column}_std"
        ] = std


    family_summary_rows.append(
        row
    )


family_summary_df = (
    pd.DataFrame(
        family_summary_rows
    )
)


family_summary_df.to_csv(
    ANALYSIS /
    "reliability_family_summary_144.csv",
    index=False
)


print(
    "FAMILY_SUMMARY_ROWS=",
    len(
        family_summary_df
    )
)


print()
print(
    "10. EQUAL-DATASET-WEIGHT CROSS-DATASET SUMMARY"
)
print(
    "-" * 78
)


cross_rows = []


for model in MODELS:

    group = dataset_model_df[
        dataset_model_df[
            "model"
        ]
        ==
        model
    ]


    row = {
        "model":
            model,

        "dataset_count":
            len(group),
    }


    mappings = {
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


    for output, column in (
        mappings.items()
    ):

        values = group[
            column
        ].to_numpy(
            dtype=float
        )


        row[
            f"{output}_dataset_macro_mean"
        ] = float(
            np.mean(
                values
            )
        )


        row[
            f"{output}_dataset_std"
        ] = float(
            np.std(
                values,
                ddof=1
            )
        )


    cross_rows.append(
        row
    )


cross_df = pd.DataFrame(
    cross_rows
)


cross_df.to_csv(
    ANALYSIS /
    "cross_dataset_model_summary_9.csv",
    index=False
)


display_columns = [
    "model",
    "clean_accuracy_dataset_macro_mean",
    "clean_macro_f1_dataset_macro_mean",
    "reliability_score_dataset_macro_mean",
    "corrupted_accuracy_dataset_macro_mean",
    "corrupted_macro_f1_dataset_macro_mean",
    "parameters_dataset_macro_mean",
]


print(
    cross_df[
        display_columns
    ]
    .sort_values(
        "corrupted_accuracy_dataset_macro_mean",
        ascending=False
    )
    .to_string(
        index=False
    )
)


print()
print(
    "11. DATASET WINNERS"
)
print(
    "-" * 78
)


winner_rows = []


winner_metrics = {
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

    subset = dataset_model_df[
        dataset_model_df[
            "dataset"
        ]
        ==
        dataset
    ]


    for metric, (
        column,
        lower_better
    ) in winner_metrics.items():

        if lower_better:

            idx = subset[
                column
            ].idxmin()

        else:

            idx = subset[
                column
            ].idxmax()


        winner = subset.loc[
            idx
        ]


        winner_rows.append(
            {
                "dataset":
                    dataset,

                "metric":
                    metric,

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


winner_df = pd.DataFrame(
    winner_rows
)


winner_df.to_csv(
    ANALYSIS /
    "best_model_by_dataset_metric.csv",
    index=False
)


print(
    winner_df.to_string(
        index=False
    )
)


print()
print(
    "12. AVERAGE DATASET RANKS"
)
print(
    "-" * 78
)


rank_rows = []


for dataset in DATASETS:

    subset = dataset_model_df[
        dataset_model_df[
            "dataset"
        ]
        ==
        dataset
    ].copy()


    rank_specs = {
        "clean_accuracy_rank":
            (
                "accuracy_mean",
                False
            ),

        "clean_macro_f1_rank":
            (
                "macro_f1_mean",
                False
            ),

        "reliability_rank":
            (
                "reliability_score_mean",
                False
            ),

        "corrupted_accuracy_rank":
            (
                "corrupted_accuracy_mean",
                False
            ),

        "corrupted_macro_f1_rank":
            (
                "corrupted_macro_f1_mean",
                False
            ),

        "parameter_rank":
            (
                "parameters_mean",
                True
            ),
    }


    for rank_name, (
        column,
        ascending
    ) in rank_specs.items():

        subset[
            rank_name
        ] = subset[
            column
        ].rank(
            ascending=ascending,
            method="average"
        )


    for _, row in subset.iterrows():

        rank_rows.append(
            {
                "dataset":
                    dataset,

                "model":
                    row[
                        "model"
                    ],

                **{
                    rank_name:
                        float(
                            row[
                                rank_name
                            ]
                        )
                    for rank_name
                    in rank_specs
                },
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


avg_rank_df = (
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


avg_rank_df.to_csv(
    ANALYSIS /
    "cross_dataset_average_ranks.csv",
    index=False
)


print(
    avg_rank_df
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
    "13. PAIRED FIVE-SEED TESTS: V22/V24 VS ALL COMPETITORS"
)
print(
    "-" * 78
)


paired_source = (
    clean_df[
        [
            "dataset",
            "model",
            "seed",
            "accuracy",
            "macro_f1",
        ]
    ]
    .merge(
        rel_df[
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
)


paired_rows = []


for dataset in DATASETS:

    dataset_df = paired_source[
        paired_source[
            "dataset"
        ]
        ==
        dataset
    ]


    for anchor in [
        "ReliabilityCNN_v22",
        "ReliabilityCNN_v24",
    ]:

        anchor_df = (
            dataset_df[
                dataset_df[
                    "model"
                ]
                ==
                anchor
            ]
            .set_index(
                "seed"
            )
        )


        for competitor in MODELS:

            if competitor == anchor:
                continue


            comp_df = (
                dataset_df[
                    dataset_df[
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
                    comp_df.index
                )
            )


            require(
                common == SEEDS,
                (
                    "Seed pairing mismatch: "
                    f"{dataset}/{anchor}/"
                    f"{competitor}"
                ),
                errors
            )


            for metric in [
                "accuracy",
                "macro_f1",
                "reliability_score",
                "corrupted_accuracy",
                "corrupted_macro_f1",
            ]:

                result = paired_test(
                    anchor_df.loc[
                        common,
                        metric
                    ].to_numpy(),

                    comp_df.loc[
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
    len(paired_df)
)

print(
    "SCIPY_AVAILABLE=",
    SCIPY_AVAILABLE
)


print()
print(
    "14. EXPLORATORY CROSS-DATASET FRIEDMAN"
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

        model_vectors = []


        for model in MODELS:

            values = (
                dataset_model_df[
                    dataset_model_df[
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


            model_vectors.append(
                values
            )


        try:

            statistic, pvalue = (
                stats.friedmanchisquare(
                    *model_vectors
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

                    "boundary":
                        (
                            "exploratory: "
                            "only four dataset blocks"
                        ),
                }
            )

        except Exception as exc:

            warnings.append(
                (
                    "Friedman failed for "
                    f"{metric}: {exc}"
                )
            )


friedman_df = pd.DataFrame(
    friedman_rows
)


friedman_df.to_csv(
    ANALYSIS /
    "friedman_cross_dataset_exploratory.csv",
    index=False
)


if len(friedman_df):

    print(
        friedman_df.to_string(
            index=False
        )
    )


print()
print(
    "15. FINAL ANALYSIS RECEIPT"
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
    "best_model_by_dataset_metric.csv",

    ANALYSIS /
    "dataset_model_ranks.csv",

    ANALYSIS /
    "cross_dataset_average_ranks.csv",

    ANALYSIS /
    "paired_seed_tests_v22_v24_vs_competitors.csv",

    ANALYSIS /
    "friedman_cross_dataset_exploratory.csv",
]


analysis_hashes = {
    str(path):
        sha256_file(
            path
        )
    for path in analysis_files
}


receipt = {
    "benchmark":
        "benchmark_v3r1",

    "analysis_revision":
        "r2_case_reconstruction",

    "integrity_pass":
        True,

    "protocol_manifest_sha256":
        protocol_sha,

    "frozen_corruption_registry_sha256":
        registry_sha,

    "frozen_hashes_verified":
        hash_verified,

    "clean_runs_verified":
        len(clean_df),

    "reliability_runs_verified":
        len(rel_df),

    "family_rows_verified":
        len(family_df),

    "corruption_cases_reconstructed":
        len(case_df),

    "expected_corruption_cases":
        EXPECTED_CASES_TOTAL,

    "case_reconstruction_method":
        (
            "frozen corruption registry "
            "+ existing per-condition metrics.json "
            "+ original create_reliability_summary()"
        ),

    "no_model_execution":
        True,

    "no_reliability_rerun":
        True,

    "no_training_rerun":
        True,

    "aggregation_policy":
        (
            "case -> family mean; "
            "equal family weight within seed; "
            "five-seed dataset/model mean; "
            "equal dataset weight cross-dataset"
        ),

    "warnings":
        warnings,

    "analysis_hashes":
        analysis_hashes,
}


receipt_path = (
    ANALYSIS /
    "benchmark_v3r1_final_integrity_receipt_r2.json"
)


save_json(
    receipt_path,
    receipt
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
    "BENCHMARK_V3R1_FINAL_INTEGRITY_AND_AGGREGATION_R2_PASS=True"
)

print(
    "CLEAN_RUNS=180"
)

print(
    "RELIABILITY_RUNS=180"
)

print(
    "FAMILY_ROWS=720"
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
