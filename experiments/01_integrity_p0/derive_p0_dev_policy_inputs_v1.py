from __future__ import annotations

from collections import Counter
from hashlib import sha256
from pathlib import Path
import json
import re

import numpy as np
import pandas as pd


ROOT = Path.home() / "toqeer" / "IMU_Reliability"

REGISTRY = (
    ROOT
    / "data/manifests/"
      "reliability_eval_registry_v1.json"
)

LINEAGE = (
    ROOT
    / "data/provenance/"
      "reliability_lineage_v2.json"
)

OUTPUT = (
    ROOT
    / "data/provenance/"
      "p0_dev_policy_inputs_v1.json"
)


EXPECTED_REGISTRY_TAG_COMMIT = (
    "416cc9d8895646c38edc6b7be1dfdc042d0c2219"
)


SENSOR_KEYS = (
    "acc_x",
    "acc_y",
    "acc_z",
    "gyr_x",
    "gyr_y",
    "gyr_z",
)


ABS_QUANTILES = (
    0.95,
    0.975,
    0.99,
    0.995,
    0.999,
)


POSITIVE_DT_QUANTILES = (
    0.001,
    0.01,
    0.5,
    0.99,
    0.999,
)


def canonical_digest(payload):
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")

    return sha256(raw).hexdigest()


def verify_hash(data):
    payload = dict(data)

    stored = payload.pop(
        "content_sha256"
    )

    computed = canonical_digest(
        payload
    )

    if stored != computed:
        raise RuntimeError(
            "Content hash mismatch"
        )

    return stored


def norm(name):
    return re.sub(
        r"[^a-z0-9]+",
        "",
        str(name).lower(),
    )


def find_sensor_column(
    columns,
    axis,
    kind,
):
    normalized = {
        column:
            norm(column)
        for column in columns
    }

    axis = axis.lower()

    candidates = []

    if kind == "acc":
        pattern = re.compile(
            r"^(?:acc|accelerometer|acceleration)([xyz])"
        )

    elif kind == "gyr":
        pattern = re.compile(
            r"^(?:gyr|gyro|gyroscope)([xyz])"
        )

    else:
        raise RuntimeError(
            f"Unknown sensor kind: {kind}"
        )

    for column, value in normalized.items():

        match = pattern.match(
            value
        )

        if match is None:
            continue

        if match.group(1) != axis:
            continue

        candidates.append(
            column
        )

    if len(candidates) != 1:
        raise RuntimeError(
            f"Could not uniquely resolve "
            f"{kind}{axis}: "
            f"{candidates} "
            f"from {list(columns)}"
        )

    return candidates[0]

def find_time_column(columns):
    candidates = []

    for column in columns:
        value = norm(column)

        if "elapsed" in value:
            continue

        if (
            "timestamp" in value
            or value.startswith("time")
        ):
            candidates.append(
                column
            )

    if len(candidates) != 1:
        raise RuntimeError(
            "Could not uniquely resolve "
            f"sample timestamp: {candidates} "
            f"from {list(columns)}"
        )

    return candidates[0]


def find_counter_column(columns):
    candidates = [
        column
        for column in columns
        if (
            "framecounter"
            in norm(column)
        )
    ]

    if len(candidates) == 1:
        return candidates[0]

    if len(candidates) == 0:
        return None

    raise RuntimeError(
        "Multiple FrameCounter columns: "
        f"{candidates}"
    )


def timestamp_scale_to_ms(
    column,
):
    text = str(
        column
    ).lower()

    if "ms" in text:
        return 1.0

    if (
        "(s)" in text
        or "[s]" in text
    ):
        return 1000.0

    raise RuntimeError(
        "Timestamp unit not recognized: "
        f"{column}"
    )


def detect_header_row(
    path,
    *,
    max_rows=20,
):
    errors = []

    for header_row in range(
        max_rows
    ):
        try:
            header = pd.read_csv(
                path,
                header=header_row,
                nrows=0,
            )

            columns = list(
                header.columns
            )

            find_sensor_column(
                columns,
                "x",
                "acc",
            )

            find_sensor_column(
                columns,
                "y",
                "acc",
            )

            find_sensor_column(
                columns,
                "z",
                "acc",
            )

            find_sensor_column(
                columns,
                "x",
                "gyr",
            )

            find_sensor_column(
                columns,
                "y",
                "gyr",
            )

            find_sensor_column(
                columns,
                "z",
                "gyr",
            )

            find_time_column(
                columns
            )

            return header_row

        except Exception as exc:
            errors.append(
                (
                    header_row,
                    str(exc),
                )
            )

    raise RuntimeError(
        "Could not locate sensor CSV header "
        f"within first {max_rows} rows of {path}. "
        f"Attempts={errors}"
    )


def schema_for(path):

    header_row = detect_header_row(
        path
    )

    header = pd.read_csv(
        path,
        header=header_row,
        nrows=0,
    )

    columns = list(
        header.columns
    )

    sensor_columns = {
        "acc_x":
            find_sensor_column(
                columns,
                "x",
                "acc",
            ),

        "acc_y":
            find_sensor_column(
                columns,
                "y",
                "acc",
            ),

        "acc_z":
            find_sensor_column(
                columns,
                "z",
                "acc",
            ),

        "gyr_x":
            find_sensor_column(
                columns,
                "x",
                "gyr",
            ),

        "gyr_y":
            find_sensor_column(
                columns,
                "y",
                "gyr",
            ),

        "gyr_z":
            find_sensor_column(
                columns,
                "z",
                "gyr",
            ),
    }

    time_column = find_time_column(
        columns
    )

    counter_column = find_counter_column(
        columns
    )

    return {
        "header_row":
            header_row,

        "columns":
            columns,

        "sensor_columns":
            sensor_columns,

        "timestamp_column":
            time_column,

        "timestamp_scale_to_ms":
            timestamp_scale_to_ms(
                time_column
            ),

        "frame_counter_column":
            counter_column,
    }

def numeric(values):
    return pd.to_numeric(
        values,
        errors="coerce",
    ).to_numpy(
        dtype=np.float64,
    )


def main():
    registry = json.loads(
        REGISTRY.read_text(
            encoding="utf-8"
        )
    )

    registry_sha = verify_hash(
        registry
    )

    lineage = json.loads(
        LINEAGE.read_text(
            encoding="utf-8"
        )
    )

    lineage_sha = verify_hash(
        lineage
    )


    if registry["status"] != (
        "frozen_before_p0_corruption_policy_definition"
    ):
        raise RuntimeError(
            "Registry is not frozen in the expected state"
        )


    if (
        registry[
            "created_from"
        ][
            "lineage_content_sha256"
        ]
        != lineage_sha
    ):
        raise RuntimeError(
            "Registry/lineage hash disagreement"
        )


    lineage_by_id = {
        (
            f"{row['dataset']}:"
            f"{row['relative_trial']}"
        ):
            row
        for row in lineage[
            "trials"
        ]
    }


    selected = [
        row
        for row in registry[
            "records"
        ]
        if (
            row[
                "partition"
            ]
            == "development"
            and row[
                "acquisition_scope"
            ][
                "acquisition_p0_eligible"
            ]
        )
    ]


    selected_counts = Counter(
        row["dataset"]
        for row in selected
    )


    expected_counts = {
        "KFALL": 3829,
        "UNIVRFALL": 792,
    }

    if dict(
        selected_counts
    ) != expected_counts:
        raise RuntimeError(
            "Unexpected development acquisition population: "
            f"{dict(selected_counts)}"
        )


    print(
        "development_acquisition_trials =",
        len(selected),
        flush=True,
    )

    print(
        "development_dataset_counts =",
        dict(selected_counts),
        flush=True,
    )


    arrays = {
        dataset: {
            key: []
            for key in SENSOR_KEYS
        }
        for dataset in (
            "KFALL",
            "UNIVRFALL",
        )
    }


    positive_dts_ms = {
        "KFALL": [],
        "UNIVRFALL": [],
    }


    timestamp_counts = {
        dataset:
            Counter()
        for dataset in (
            "KFALL",
            "UNIVRFALL",
        )
    }


    nonfinite_counts = {
        dataset: {
            key: 0
            for key in SENSOR_KEYS
        }
        for dataset in (
            "KFALL",
            "UNIVRFALL",
        )
    }


    row_counts = Counter()

    schema_examples = {}

    files_processed = Counter()


    for index, registry_row in enumerate(
        selected,
        start=1,
    ):
        trial_id = registry_row[
            "trial_id"
        ]

        lineage_row = lineage_by_id.get(
            trial_id
        )

        if lineage_row is None:
            raise RuntimeError(
                f"Lineage record missing: {trial_id}"
            )


        dataset = registry_row[
            "dataset"
        ]

        original_paths = (
            lineage_row[
                "raw_pairing"
            ][
                "original"
            ]
        )

        if len(
            original_paths
        ) != 1:
            raise RuntimeError(
                "Expected exactly one original raw file: "
                f"{trial_id}: {original_paths}"
            )


        path = Path(
            original_paths[0]
        )

        if not path.is_file():
            raise RuntimeError(
                f"Raw file missing: {path}"
            )


        schema = schema_for(
            path
        )

        if dataset not in schema_examples:
            schema_examples[
                dataset
            ] = {
                "example_file":
                    str(path),

                **schema,
            }


        usecols = list(
            schema[
                "sensor_columns"
            ].values()
        )

        usecols.append(
            schema[
                "timestamp_column"
            ]
        )

        if (
            schema[
                "frame_counter_column"
            ]
            is not None
        ):
            usecols.append(
                schema[
                    "frame_counter_column"
                ]
            )


        frame = pd.read_csv(
            path,
            header=schema[
                "header_row"
            ],
            usecols=usecols,
            low_memory=False,
        )


        row_counts[
            dataset
        ] += len(
            frame
        )

        files_processed[
            dataset
        ] += 1


        for key in SENSOR_KEYS:
            column = (
                schema[
                    "sensor_columns"
                ][key]
            )

            values = numeric(
                frame[column]
            )

            finite = np.isfinite(
                values
            )

            nonfinite_counts[
                dataset
            ][key] += int(
                np.count_nonzero(
                    ~finite
                )
            )

            values = values[
                finite
            ]

            arrays[
                dataset
            ][key].append(
                np.abs(
                    values
                )
            )


        timestamp = numeric(
            frame[
                schema[
                    "timestamp_column"
                ]
            ]
        )

        timestamp = timestamp[
            np.isfinite(
                timestamp
            )
        ]

        if len(timestamp) >= 2:
            delta_ms = (
                np.diff(
                    timestamp
                )
                * schema[
                    "timestamp_scale_to_ms"
                ]
            )

            timestamp_counts[
                dataset
            ][
                "transition_count"
            ] += len(
                delta_ms
            )

            timestamp_counts[
                dataset
            ][
                "nonpositive_count"
            ] += int(
                np.count_nonzero(
                    delta_ms <= 0
                )
            )

            positive = delta_ms[
                delta_ms > 0
            ]

            if positive.size:
                positive_dts_ms[
                    dataset
                ].append(
                    positive.astype(
                        np.float64,
                        copy=False,
                    )
                )


        if (
            index % 250
        ) == 0:
            print(
                f"processed "
                f"{index}/"
                f"{len(selected)} "
                f"development raw trials",
                flush=True,
            )


    summaries = {}


    for dataset in (
        "KFALL",
        "UNIVRFALL",
    ):
        sensor_summary = {}

        for key in SENSOR_KEYS:
            if not arrays[
                dataset
            ][key]:
                raise RuntimeError(
                    f"No values for "
                    f"{dataset} {key}"
                )

            values = np.concatenate(
                arrays[
                    dataset
                ][key]
            )

            quantiles = np.quantile(
                values,
                ABS_QUANTILES,
            )

            sensor_summary[
                key
            ] = {
                "finite_value_count":
                    int(
                        values.size
                    ),

                "nonfinite_count":
                    int(
                        nonfinite_counts[
                            dataset
                        ][key]
                    ),

                "absolute_quantiles": {
                    f"q{q:.3f}":
                        float(value)
                    for q, value
                    in zip(
                        ABS_QUANTILES,
                        quantiles,
                    )
                },

                "absolute_max":
                    float(
                        np.max(
                            values
                        )
                    ),
            }


        if not positive_dts_ms[
            dataset
        ]:
            raise RuntimeError(
                "No positive timestamp deltas for "
                f"{dataset}"
            )

        dt = np.concatenate(
            positive_dts_ms[
                dataset
            ]
        )

        dt_quantiles = np.quantile(
            dt,
            POSITIVE_DT_QUANTILES,
        )


        rounded_dt = np.round(
            dt,
            decimals=6,
        )

        unique, counts = np.unique(
            rounded_dt,
            return_counts=True,
        )

        top_indices = np.argsort(
            counts
        )[
            -12:
        ][
            ::-1
        ]


        summaries[
            dataset
        ] = {
            "raw_file_count":
                int(
                    files_processed[
                        dataset
                    ]
                ),

            "raw_row_count":
                int(
                    row_counts[
                        dataset
                    ]
                ),

            "schema_example":
                schema_examples[
                    dataset
                ],

            "sensor_absolute_statistics":
                sensor_summary,

            "timestamp_delta_ms": {
                "transition_count":
                    int(
                        timestamp_counts[
                            dataset
                        ][
                            "transition_count"
                        ]
                    ),

                "nonpositive_count":
                    int(
                        timestamp_counts[
                            dataset
                        ][
                            "nonpositive_count"
                        ]
                    ),

                "positive_count":
                    int(
                        dt.size
                    ),

                "positive_quantiles": {
                    f"q{q:.3f}":
                        float(value)
                    for q, value
                    in zip(
                        POSITIVE_DT_QUANTILES,
                        dt_quantiles,
                    )
                },

                "positive_min":
                    float(
                        np.min(
                            dt
                        )
                    ),

                "positive_max":
                    float(
                        np.max(
                            dt
                        )
                    ),

                "top_rounded_delta_ms": [
                    {
                        "delta_ms":
                            float(
                                unique[i]
                            ),

                        "count":
                            int(
                                counts[i]
                            ),
                    }
                    for i in top_indices
                ],
            },
        }


    payload = {
        "audit_id":
            "P0_DEV_POLICY_INPUTS_V1",

        "status":
            "development_only_policy_design_input",

        "purpose": (
            "Derive development-only empirical inputs for "
            "prospective P0 corruption-policy definition. "
            "No corruption instances or detector thresholds "
            "are created here."
        ),

        "source_registry":
            str(
                REGISTRY.relative_to(
                    ROOT
                )
            ),

        "source_registry_content_sha256":
            registry_sha,

        "source_registry_tag_commit":
            EXPECTED_REGISTRY_TAG_COMMIT,

        "source_lineage":
            str(
                LINEAGE.relative_to(
                    ROOT
                )
            ),

        "source_lineage_content_sha256":
            lineage_sha,

        "partition_used":
            "development",

        "calibration_records_read_for_statistics":
            0,

        "final_test_records_read_for_statistics":
            0,

        "development_acquisition_trial_counts":
            dict(
                selected_counts
            ),

        "absolute_quantiles_requested":
            list(
                ABS_QUANTILES
            ),

        "positive_timestamp_quantiles_requested":
            list(
                POSITIVE_DT_QUANTILES
            ),

        "dataset_statistics":
            summaries,

        "interpretation_constraints": {
            "range_statistics_are_not_physical_sensor_rails":
                True,

            "range_statistics_may_only_define_synthetic_p0_clamps":
                True,

            "timestamp_statistics_do_not_freeze_runtime_timing_threshold":
                True,

            "synthetic_p0_truth_does_not_upgrade_runtime_provenance":
                True,

            "calibration_and_final_test_do_not_define_policy_values":
                True,
        },
    }


    payload[
        "content_sha256"
    ] = canonical_digest(
        payload
    )


    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


    print()
    print(
        "=" * 100
    )

    print(
        "P0 DEVELOPMENT POLICY INPUT SUMMARY"
    )

    print(
        "=" * 100
    )


    for dataset in (
        "UNIVRFALL",
        "KFALL",
    ):
        summary = summaries[
            dataset
        ]

        print()
        print(dataset)

        print(
            " raw_file_count =",
            summary[
                "raw_file_count"
            ],
        )

        print(
            " raw_row_count =",
            summary[
                "raw_row_count"
            ],
        )

        print(
            " timestamp_column =",
            summary[
                "schema_example"
            ][
                "timestamp_column"
            ],
        )

        print(
            " frame_counter_column =",
            summary[
                "schema_example"
            ][
                "frame_counter_column"
            ],
        )


        print(
            " sensor columns =",
            summary[
                "schema_example"
            ][
                "sensor_columns"
            ],
        )


        print(
            " timestamp_delta_ms =",
            summary[
                "timestamp_delta_ms"
            ],
        )


        print(
            " sensor absolute quantiles:"
        )

        for key in SENSOR_KEYS:
            print(
                "  ",
                key,
                "=",
                summary[
                    "sensor_absolute_statistics"
                ][key],
            )


    print()
    print(
        "CONTENT_SHA256 =",
        payload[
            "content_sha256"
        ],
    )

    print(
        "OUTPUT =",
        OUTPUT,
    )

    print(
        "P0_DEV_POLICY_INPUTS_V1_PASS = True"
    )


if __name__ == "__main__":
    main()
