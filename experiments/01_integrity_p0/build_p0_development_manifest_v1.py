from __future__ import annotations

from collections import Counter
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import json
import subprocess

import numpy as np
import pandas as pd

from imu_reliability.injection import (
    P0CorruptionKind,
    P0InjectionSpec,
    P0Stream,
    apply_p0_injection,
)

from derive_p0_dev_policy_inputs_v1 import (
    numeric,
    schema_for,
)


ROOT = Path.home() / "toqeer" / "IMU_Reliability"

POLICY = (
    ROOT
    / "configs/integrity/"
      "p0_corruption_policy_v1.json"
)

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
    / "data/manifests/"
      "p0_development_spec_manifest_v1_candidate.json"
)


EXPECTED_POLICY_SHA = (
    "cb33c32951930453db550dfd02deab67a9eb51e851edf1a186e7faa4a5432220"
)

EXPECTED_POLICY_TAG_COMMIT = (
    "95f2fdbb9fc27356573f6fcb78df90fa201fe3d5"
)

EXPECTED_REGISTRY_SHA = (
    "a99f3031e2efd388b8dcbf26673c41ae142a3ef3ea1eb8c2a4b609b819a13d71"
)

EXPECTED_LINEAGE_SHA = (
    "d5d792aa74ef4c0e1414c7737bcfde31dca765d3e66175e0f6c51e0295b82e36"
)

EXPECTED_DEVELOPMENT_COUNTS = {
    "KFALL": 3829,
    "UNIVRFALL": 792,
}

EXPECTED_TRIAL_COUNT = 4621
EXPECTED_ATTEMPT_COUNT = 69315


FAMILY_ORDER = (
    "FRAME_GAP",
    "FRAME_REPEAT",
    "CHANNEL_FREEZE",
    "TIMING_PERTURBATION",
    "RANGE_CLIP",
)

SEVERITY_ORDER = (
    "low",
    "medium",
    "high",
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
    payload = deepcopy(data)

    stored = payload.pop(
        "content_sha256"
    )

    computed = canonical_digest(
        payload
    )

    if stored != computed:
        raise RuntimeError(
            "Content hash mismatch: "
            f"{stored} != {computed}"
        )

    return stored


def git(*args):
    return subprocess.check_output(
        ["git", *args],
        cwd=ROOT,
        text=True,
    ).strip()


def seed_material(
    master,
    trial_id,
    family,
    severity,
    replicate_index=0,
):
    text = (
        f"{master}"
        f"||{trial_id}"
        f"||{family}"
        f"||{severity}"
        f"||{replicate_index}"
    )

    digest = sha256(
        text.encode("utf-8")
    ).digest()

    return {
        "text":
            text,

        "digest_hex":
            digest.hex(),

        "digest_bytes":
            digest,

        "seed_uint64":
            int.from_bytes(
                digest[:8],
                byteorder="big",
                signed=False,
            ),
    }


def domain_index(
    base_digest,
    domain,
    count,
):
    if count <= 0:
        raise ValueError(
            "count must be positive"
        )

    digest = sha256(
        domain.encode("utf-8")
        + b"||"
        + base_digest
    ).digest()

    value = int.from_bytes(
        digest[:8],
        byteorder="big",
        signed=False,
    )

    return {
        "domain":
            domain,

        "digest_hex":
            digest.hex(),

        "uint64":
            value,

        "index":
            value % count,
    }


def mutating_starts_from_changes(
    changes,
    length,
):
    changes = np.asarray(
        changes,
        dtype=bool,
    )

    n_samples = (
        changes.size
        + 1
    )

    if n_samples < (
        length + 1
    ):
        return np.empty(
            0,
            dtype=np.int64,
        )

    starts = np.arange(
        1,
        n_samples - length + 1,
        dtype=np.int64,
    )

    cumulative = np.concatenate(
        (
            np.array(
                [0],
                dtype=np.int64,
            ),
            np.cumsum(
                changes,
                dtype=np.int64,
            ),
        )
    )

    left = starts - 1
    right = left + length

    mutating = (
        cumulative[right]
        - cumulative[left]
    ) > 0

    return starts[
        mutating
    ]


def range_clip_starts(
    values,
    *,
    channel,
    low,
    high,
    span,
):
    n = values.shape[0]

    if n < span:
        return np.empty(
            0,
            dtype=np.int64,
        )

    column = values[
        :,
        channel,
    ]

    exceeds = (
        (column < low)
        | (column > high)
    )

    cumulative = np.concatenate(
        (
            np.array(
                [0],
                dtype=np.int64,
            ),
            np.cumsum(
                exceeds,
                dtype=np.int64,
            ),
        )
    )

    starts = np.arange(
        0,
        n - span + 1,
        dtype=np.int64,
    )

    contains_exceedance = (
        cumulative[
            starts + span
        ]
        - cumulative[
            starts
        ]
    ) > 0

    return starts[
        contains_exceedance
    ]


def arrays_equal_or_none(
    a,
    b,
):
    if a is None or b is None:
        return (
            a is None
            and b is None
        )

    return np.array_equal(
        a,
        b,
    )


def load_clean_stream(
    registry_row,
    lineage_row,
    policy,
):
    original = (
        lineage_row[
            "raw_pairing"
        ][
            "original"
        ]
    )

    if len(original) != 1:
        raise RuntimeError(
            "Expected exactly one raw original "
            f"for {registry_row['trial_id']}: "
            f"{original}"
        )

    raw_path = Path(
        original[0]
    )

    if not raw_path.is_file():
        raise RuntimeError(
            f"Missing raw file: {raw_path}"
        )

    schema = schema_for(
        raw_path
    )

    task_channels = tuple(
        policy[
            "channel_policy"
        ][
            "task_channels"
        ]
    )

    sensor_columns = [
        schema[
            "sensor_columns"
        ][channel]
        for channel in task_channels
    ]

    usecols = list(
        sensor_columns
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
        raw_path,
        header=schema[
            "header_row"
        ],
        usecols=usecols,
        low_memory=False,
    )

    values = np.column_stack(
        [
            numeric(
                frame[column]
            )
            for column
            in sensor_columns
        ]
    )

    if not np.all(
        np.isfinite(values)
    ):
        raise RuntimeError(
            "Non-finite sensor value in "
            f"{registry_row['trial_id']}"
        )

    timestamps = numeric(
        frame[
            schema[
                "timestamp_column"
            ]
        ]
    )

    if not np.all(
        np.isfinite(timestamps)
    ):
        raise RuntimeError(
            "Non-finite timestamp in "
            f"{registry_row['trial_id']}"
        )

    counter_column = (
        schema[
            "frame_counter_column"
        ]
    )

    counters = None

    if counter_column is not None:
        raw_counter = numeric(
            frame[
                counter_column
            ]
        )

        if not np.all(
            np.isfinite(
                raw_counter
            )
        ):
            raise RuntimeError(
                "Non-finite frame counter in "
                f"{registry_row['trial_id']}"
            )

        rounded = np.rint(
            raw_counter
        )

        if not np.array_equal(
            raw_counter,
            rounded,
        ):
            raise RuntimeError(
                "Non-integral frame counter in "
                f"{registry_row['trial_id']}"
            )

        counters = rounded.astype(
            np.int64
        )

    source_id = (
        "RAW_ORIGINAL::"
        + registry_row[
            "trial_id"
        ]
    )

    stream = P0Stream(
        values=values,
        timestamps=timestamps,
        counters=counters,
        source_id=source_id,
    )

    return (
        stream,
        raw_path,
        schema,
    )


def build_spec(
    *,
    clean,
    dataset,
    trial_id,
    family,
    severity,
    policy,
):
    family_policy = (
        policy[
            "families"
        ][family]
    )

    master = (
        policy[
            "instance_generation"
        ][
            "master_seed_material"
        ]
    )

    seed = seed_material(
        master,
        trial_id,
        family,
        severity,
        0,
    )

    base_digest = seed[
        "digest_bytes"
    ]

    selection = {
        "seed_digest_hex":
            seed[
                "digest_hex"
            ],

        "seed_uint64":
            seed[
                "seed_uint64"
            ],

        "replicate_index":
            0,
    }

    n = clean.n_samples

    channel = None
    parameters = {}
    operational = {}


    if family == "FRAME_GAP":
        length = int(
            family_policy[
                "severity_values"
            ][severity]
        )

        starts = np.arange(
            1,
            max(
                1,
                n - length,
            ),
            dtype=np.int64,
        )

        if starts.size == 0:
            return (
                None,
                "INSUFFICIENT_SAMPLES_FOR_FRAME_GAP",
                {
                    **selection,
                    "admissible_candidate_count":
                        0,
                },
            )

        chosen = domain_index(
            base_digest,
            "P0_START_SELECTION_V1",
            int(
                starts.size
            ),
        )

        start = int(
            starts[
                chosen["index"]
            ]
        )

        selection.update(
            {
                "admissible_candidate_count":
                    int(
                        starts.size
                    ),

                "start_selection":
                    chosen,
            }
        )


    elif family == "FRAME_REPEAT":
        length = int(
            family_policy[
                "severity_values"
            ][severity]
        )

        row_changes = np.any(
            clean.values[
                1:
            ] != clean.values[
                :-1
            ],
            axis=1,
        )

        starts = (
            mutating_starts_from_changes(
                row_changes,
                length,
            )
        )

        if starts.size == 0:
            reason = (
                "INSUFFICIENT_SAMPLES_FOR_FRAME_REPEAT"
                if n < length + 1
                else
                "NO_MUTATING_FRAME_REPEAT_PLACEMENT"
            )

            return (
                None,
                reason,
                {
                    **selection,
                    "admissible_candidate_count":
                        0,
                },
            )

        chosen = domain_index(
            base_digest,
            "P0_START_SELECTION_V1",
            int(
                starts.size
            ),
        )

        start = int(
            starts[
                chosen["index"]
            ]
        )

        selection.update(
            {
                "admissible_candidate_count":
                    int(
                        starts.size
                    ),

                "start_selection":
                    chosen,
            }
        )


    elif family == "CHANNEL_FREEZE":
        length = int(
            family_policy[
                "severity_values"
            ][severity]
        )

        valid_by_channel = {}

        for ch in range(
            clean.n_channels
        ):
            changes = (
                clean.values[
                    1:,
                    ch,
                ]
                != clean.values[
                    :-1,
                    ch,
                ]
            )

            starts = (
                mutating_starts_from_changes(
                    changes,
                    length,
                )
            )

            if starts.size:
                valid_by_channel[
                    ch
                ] = starts

        eligible_channels = sorted(
            valid_by_channel
        )

        if not eligible_channels:
            reason = (
                "INSUFFICIENT_SAMPLES_FOR_CHANNEL_FREEZE"
                if n < length + 1
                else
                "NO_MUTATING_CHANNEL_FREEZE_PLACEMENT"
            )

            return (
                None,
                reason,
                {
                    **selection,
                    "eligible_channel_count":
                        0,

                    "admissible_candidate_count":
                        0,
                },
            )

        channel_choice = domain_index(
            base_digest,
            "P0_CHANNEL_SELECTION_V1",
            len(
                eligible_channels
            ),
        )

        channel = int(
            eligible_channels[
                channel_choice[
                    "index"
                ]
            ]
        )

        starts = valid_by_channel[
            channel
        ]

        start_choice = domain_index(
            base_digest,
            "P0_START_SELECTION_V1",
            int(
                starts.size
            ),
        )

        start = int(
            starts[
                start_choice[
                    "index"
                ]
            ]
        )

        total_pairs = int(
            sum(
                values.size
                for values
                in valid_by_channel.values()
            )
        )

        selection.update(
            {
                "eligible_channel_count":
                    len(
                        eligible_channels
                    ),

                "eligible_channels":
                    eligible_channels,

                "total_admissible_channel_start_pairs":
                    total_pairs,

                "selected_channel_candidate_count":
                    int(
                        starts.size
                    ),

                "channel_selection":
                    channel_choice,

                "start_selection":
                    start_choice,
            }
        )


    elif family == "TIMING_PERTURBATION":
        length = 1

        if clean.timestamps is None:
            return (
                None,
                "TIMESTAMPS_UNAVAILABLE",
                {
                    **selection,
                    "admissible_candidate_count":
                        0,
                },
            )

        starts = np.arange(
            1,
            n,
            dtype=np.int64,
        )

        if starts.size == 0:
            return (
                None,
                "NO_INTERNAL_TIMING_BOUNDARY",
                {
                    **selection,
                    "admissible_candidate_count":
                        0,
                },
            )

        chosen = domain_index(
            base_digest,
            "P0_START_SELECTION_V1",
            int(
                starts.size
            ),
        )

        start = int(
            starts[
                chosen[
                    "index"
                ]
            ]
        )

        extra_delay_ms = float(
            family_policy[
                "severity_values"
            ][severity]
        )

        selection.update(
            {
                "admissible_candidate_count":
                    int(
                        starts.size
                    ),

                "start_selection":
                    chosen,
            }
        )

        operational[
            "extra_delay_ms"
        ] = extra_delay_ms


    elif family == "RANGE_CLIP":
        length = int(
            family_policy[
                "placement_constraints"
            ][
                "candidate_span_samples"
            ]
        )

        levels = (
            family_policy[
                "per_dataset_channel_levels"
            ][dataset][severity]
        )

        valid_by_channel = {}

        task_channels = tuple(
            policy[
                "channel_policy"
            ][
                "task_channels"
            ]
        )

        for ch, channel_name in enumerate(
            task_channels
        ):
            channel_level = (
                levels[
                    channel_name
                ]
            )

            low = float(
                channel_level[
                    "low"
                ]
            )

            high = float(
                channel_level[
                    "high"
                ]
            )

            starts = range_clip_starts(
                clean.values,
                channel=ch,
                low=low,
                high=high,
                span=length,
            )

            if starts.size:
                valid_by_channel[
                    ch
                ] = starts

        eligible_channels = sorted(
            valid_by_channel
        )

        if not eligible_channels:
            reason = (
                "INSUFFICIENT_SAMPLES_FOR_RANGE_CLIP_SPAN"
                if n < length
                else
                "NO_RANGE_EXCEEDANCE_FOR_SEVERITY"
            )

            return (
                None,
                reason,
                {
                    **selection,
                    "eligible_channel_count":
                        0,

                    "admissible_candidate_count":
                        0,
                },
            )

        channel_choice = domain_index(
            base_digest,
            "P0_CHANNEL_SELECTION_V1",
            len(
                eligible_channels
            ),
        )

        channel = int(
            eligible_channels[
                channel_choice[
                    "index"
                ]
            ]
        )

        starts = valid_by_channel[
            channel
        ]

        start_choice = domain_index(
            base_digest,
            "P0_START_SELECTION_V1",
            int(
                starts.size
            ),
        )

        start = int(
            starts[
                start_choice[
                    "index"
                ]
            ]
        )

        channel_name = (
            task_channels[
                channel
            ]
        )

        level = levels[
            channel_name
        ]

        parameters = {
            "low":
                float(
                    level[
                        "low"
                    ]
                ),

            "high":
                float(
                    level[
                        "high"
                    ]
                ),
        }

        total_pairs = int(
            sum(
                values.size
                for values
                in valid_by_channel.values()
            )
        )

        selection.update(
            {
                "eligible_channel_count":
                    len(
                        eligible_channels
                    ),

                "eligible_channels":
                    eligible_channels,

                "total_admissible_channel_start_pairs":
                    total_pairs,

                "selected_channel_candidate_count":
                    int(
                        starts.size
                    ),

                "channel_selection":
                    channel_choice,

                "start_selection":
                    start_choice,
            }
        )

        operational.update(
            {
                "channel_name":
                    channel_name,

                "source_quantile":
                    level[
                        "source_quantile"
                    ],

                "absolute_clamp_level":
                    float(
                        level[
                            "absolute_clamp_level"
                        ]
                    ),

                "physical_rail_claim":
                    False,
            }
        )


    else:
        raise RuntimeError(
            f"Unsupported policy family: {family}"
        )


    channels = (
        ()
        if channel is None
        else (
            channel,
        )
    )

    return (
        {
            "kind":
                family,

            "start_index":
                start,

            "length":
                length,

            "severity":
                severity,

            "channels":
                channels,

            "seed":
                seed[
                    "seed_uint64"
                ],

            "parameters":
                parameters,

            "selection":
                selection,

            "operational":
                operational,
        },
        None,
        None,
    )


def main():
    policy = json.loads(
        POLICY.read_text(
            encoding="utf-8"
        )
    )

    policy_sha = verify_hash(
        policy
    )

    if policy_sha != EXPECTED_POLICY_SHA:
        raise RuntimeError(
            "Frozen P0 policy changed"
        )

    tag_commit = git(
        "rev-parse",
        "p0-corruption-policy-v1^{}",
    )

    if tag_commit != EXPECTED_POLICY_TAG_COMMIT:
        raise RuntimeError(
            "p0-corruption-policy-v1 tag moved"
        )

    registry = json.loads(
        REGISTRY.read_text(
            encoding="utf-8"
        )
    )

    registry_sha = verify_hash(
        registry
    )

    if registry_sha != EXPECTED_REGISTRY_SHA:
        raise RuntimeError(
            "Frozen reliability registry changed"
        )

    lineage = json.loads(
        LINEAGE.read_text(
            encoding="utf-8"
        )
    )

    lineage_sha = verify_hash(
        lineage
    )

    if lineage_sha != EXPECTED_LINEAGE_SHA:
        raise RuntimeError(
            "Frozen lineage changed"
        )


    if tuple(
        policy["severity_order"]
    ) != SEVERITY_ORDER:
        raise RuntimeError(
            "Unexpected severity ordering"
        )

    if set(
        policy["families"]
    ) != set(
        FAMILY_ORDER
    ):
        raise RuntimeError(
            "Unexpected P0 family set"
        )


    selected = [
        row
        for row
        in registry["records"]
        if (
            row["partition"]
            == "development"
            and row[
                "acquisition_scope"
            ][
                "acquisition_p0_eligible"
            ]
        )
    ]

    selected.sort(
        key=lambda row:
            row["trial_id"]
    )

    dataset_counts = Counter(
        row["dataset"]
        for row in selected
    )

    if len(
        selected
    ) != EXPECTED_TRIAL_COUNT:
        raise RuntimeError(
            "Unexpected development trial count: "
            f"{len(selected)}"
        )

    if dict(
        dataset_counts
    ) != EXPECTED_DEVELOPMENT_COUNTS:
        raise RuntimeError(
            "Unexpected dataset counts: "
            f"{dict(dataset_counts)}"
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


    attempts = []
    trials = []

    status_counts = Counter()
    reason_counts = Counter()

    raw_files_opened = 0


    for trial_number, registry_row in enumerate(
        selected,
        start=1,
    ):
        trial_id = registry_row[
            "trial_id"
        ]

        dataset = registry_row[
            "dataset"
        ]

        lineage_row = lineage_by_id.get(
            trial_id
        )

        if lineage_row is None:
            raise RuntimeError(
                f"Missing lineage record: {trial_id}"
            )


        clean, raw_path, schema = (
            load_clean_stream(
                registry_row,
                lineage_row,
                policy,
            )
        )

        raw_files_opened += 1

        clean_fingerprint = (
            clean.fingerprint()
        )


        model_coupled = bool(
            registry_row[
                "acquisition_scope"
            ][
                "model_coupled_p0_eligible"
            ]
        )


        trials.append(
            {
                "trial_id":
                    trial_id,

                "dataset":
                    dataset,

                "relative_trial":
                    registry_row[
                        "relative_trial"
                    ],

                "historical_windows":
                    int(
                        registry_row[
                            "historical_windows"
                        ]
                    ),

                "model_coupled_p0_eligible":
                    model_coupled,

                "raw_original_path":
                    str(
                        raw_path
                    ),

                "clean_source_id":
                    clean.source_id,

                "clean_n_samples":
                    clean.n_samples,

                "clean_n_channels":
                    clean.n_channels,

                "clean_stream_fingerprint":
                    clean_fingerprint,

                "timestamp_column":
                    schema[
                        "timestamp_column"
                    ],

                "timestamp_scale_to_ms":
                    float(
                        schema[
                            "timestamp_scale_to_ms"
                        ]
                    ),

                "frame_counter_column":
                    schema[
                        "frame_counter_column"
                    ],
            }
        )


        for family in FAMILY_ORDER:
            for severity in SEVERITY_ORDER:

                attempt_key = (
                    f"{trial_id}"
                    f"||{family}"
                    f"||{severity}"
                    f"||0"
                )

                attempt_id = (
                    "P0A_"
                    + sha256(
                        attempt_key.encode(
                            "utf-8"
                        )
                    ).hexdigest()[:24]
                )


                built, reason, not_admissible = (
                    build_spec(
                        clean=clean,
                        dataset=dataset,
                        trial_id=trial_id,
                        family=family,
                        severity=severity,
                        policy=policy,
                    )
                )


                base = {
                    "attempt_id":
                        attempt_id,

                    "trial_id":
                        trial_id,

                    "dataset":
                        dataset,

                    "family":
                        family,

                    "severity":
                        severity,

                    "replicate_index":
                        0,

                    "partition":
                        "development",

                    "model_coupled_p0_eligible":
                        model_coupled,
                }


                if built is None:
                    record = {
                        **base,

                        "status":
                            "NOT_ADMISSIBLE",

                        "reason":
                            reason,

                        "selection":
                            not_admissible,
                    }

                    attempts.append(
                        record
                    )

                    status_counts[
                        (
                            dataset,
                            family,
                            severity,
                            "NOT_ADMISSIBLE",
                        )
                    ] += 1

                    reason_counts[
                        (
                            dataset,
                            family,
                            severity,
                            reason,
                        )
                    ] += 1

                    continue


                parameters = dict(
                    built[
                        "parameters"
                    ]
                )

                operational = dict(
                    built[
                        "operational"
                    ]
                )


                if family == (
                    "TIMING_PERTURBATION"
                ):
                    extra_delay_ms = float(
                        operational[
                            "extra_delay_ms"
                        ]
                    )

                    scale_to_ms = float(
                        schema[
                            "timestamp_scale_to_ms"
                        ]
                    )

                    offset_raw_units = (
                        extra_delay_ms
                        / scale_to_ms
                    )

                    parameters[
                        "offset"
                    ] = offset_raw_units

                    operational.update(
                        {
                            "timestamp_scale_to_ms":
                                scale_to_ms,

                            "offset_in_raw_timestamp_units":
                                offset_raw_units,
                        }
                    )


                spec = P0InjectionSpec(
                    kind=P0CorruptionKind(
                        built[
                            "kind"
                        ]
                    ),

                    start_index=int(
                        built[
                            "start_index"
                        ]
                    ),

                    length=int(
                        built[
                            "length"
                        ]
                    ),

                    severity=built[
                        "severity"
                    ],

                    channels=tuple(
                        built[
                            "channels"
                        ]
                    ),

                    seed=int(
                        built[
                            "seed"
                        ]
                    ),

                    parameters=parameters,
                )


                try:
                    pair = apply_p0_injection(
                        clean,
                        spec,
                    )
                except Exception as exc:
                    raise RuntimeError(
                        "Pre-admissibility disagreed with "
                        "tested injector for "
                        f"{trial_id} "
                        f"{family} "
                        f"{severity}: "
                        f"{type(exc).__name__}: {exc}"
                    ) from exc


                if (
                    pair.clean.fingerprint()
                    != clean_fingerprint
                ):
                    raise RuntimeError(
                        "Clean stream changed during injection"
                    )


                corrupt_fingerprint = (
                    pair.corrupt.fingerprint()
                )

                if (
                    corrupt_fingerprint
                    == clean_fingerprint
                ):
                    raise RuntimeError(
                        "Injector produced a no-op fingerprint: "
                        f"{trial_id} {family} {severity}"
                    )


                if family == "FRAME_GAP":
                    expected_n = (
                        clean.n_samples
                        - spec.length
                    )

                    if (
                        pair.corrupt.n_samples
                        != expected_n
                    ):
                        raise RuntimeError(
                            "FRAME_GAP sample-count mismatch"
                        )

                else:
                    if (
                        pair.corrupt.n_samples
                        != clean.n_samples
                    ):
                        raise RuntimeError(
                            "Unexpected sample-count change "
                            f"for {family}"
                        )


                if family in {
                    "FRAME_REPEAT",
                    "CHANNEL_FREEZE",
                    "RANGE_CLIP",
                }:
                    if not arrays_equal_or_none(
                        pair.corrupt.timestamps,
                        clean.timestamps,
                    ):
                        raise RuntimeError(
                            f"{family} changed timestamps"
                        )

                    if not arrays_equal_or_none(
                        pair.corrupt.counters,
                        clean.counters,
                    ):
                        raise RuntimeError(
                            f"{family} changed counters"
                        )


                if family == (
                    "TIMING_PERTURBATION"
                ):
                    if not np.array_equal(
                        pair.corrupt.values,
                        clean.values,
                    ):
                        raise RuntimeError(
                            "TIMING_PERTURBATION changed values"
                        )

                    if not arrays_equal_or_none(
                        pair.corrupt.counters,
                        clean.counters,
                    ):
                        raise RuntimeError(
                            "TIMING_PERTURBATION changed counters"
                        )

                    start = spec.start_index

                    before_delta = (
                        clean.timestamps[start]
                        - clean.timestamps[
                            start - 1
                        ]
                    )

                    after_delta = (
                        pair.corrupt.timestamps[
                            start
                        ]
                        - pair.corrupt.timestamps[
                            start - 1
                        ]
                    )

                    observed_extra_ms = (
                        (
                            after_delta
                            - before_delta
                        )
                        * float(
                            schema[
                                "timestamp_scale_to_ms"
                            ]
                        )
                    )

                    expected_extra_ms = float(
                        operational[
                            "extra_delay_ms"
                        ]
                    )

                    if not np.isclose(
                        observed_extra_ms,
                        expected_extra_ms,
                        rtol=0.0,
                        atol=1e-8,
                    ):
                        raise RuntimeError(
                            "Timing unit conversion mismatch: "
                            f"{trial_id}: "
                            f"observed={observed_extra_ms} ms, "
                            f"expected={expected_extra_ms} ms"
                        )


                truth = pair.truths[0]

                record = {
                    **base,

                    "status":
                        "ADMISSIBLE",

                    "reason":
                        None,

                    "selection":
                        built[
                            "selection"
                        ],

                    "spec":
                        spec.canonical_dict(),

                    "spec_id":
                        spec.spec_id,

                    "injection_id":
                        truth.injection_id,

                    "clean_stream_fingerprint":
                        clean_fingerprint,

                    "corrupt_stream_fingerprint":
                        corrupt_fingerprint,

                    "affected_clean_start":
                        int(
                            truth[
                                "affected_clean_start"
                            ]
                        )
                        if isinstance(
                            truth,
                            dict,
                        )
                        else int(
                            truth.affected_clean_start
                        ),

                    "affected_clean_end_exclusive":
                        int(
                            truth.affected_clean_end_exclusive
                        ),

                    "corrupt_anchor_index":
                        int(
                            truth.corrupt_anchor_index
                        ),

                    "operational":
                        operational,
                }

                attempts.append(
                    record
                )

                status_counts[
                    (
                        dataset,
                        family,
                        severity,
                        "ADMISSIBLE",
                    )
                ] += 1


        if (
            trial_number % 250
        ) == 0:
            print(
                f"processed "
                f"{trial_number}/"
                f"{len(selected)} "
                f"development trials",
                flush=True,
            )


    if len(
        attempts
    ) != EXPECTED_ATTEMPT_COUNT:
        raise RuntimeError(
            "Attempt count mismatch: "
            f"{len(attempts)}"
        )


    if raw_files_opened != (
        EXPECTED_TRIAL_COUNT
    ):
        raise RuntimeError(
            "Unexpected raw files opened count"
        )


    payload = {
        "manifest_id":
            "P0_DEVELOPMENT_SPEC_MANIFEST_V1",

        "status":
            "candidate_admissibility_audit_before_development_manifest_freeze",

        "partition":
            "development",

        "source_policy": {
            "path":
                str(
                    POLICY.relative_to(
                        ROOT
                    )
                ),

            "content_sha256":
                policy_sha,

            "tag":
                "p0-corruption-policy-v1",

            "tag_commit":
                tag_commit,
        },

        "source_registry": {
            "path":
                str(
                    REGISTRY.relative_to(
                        ROOT
                    )
                ),

            "content_sha256":
                registry_sha,
        },

        "source_lineage": {
            "path":
                str(
                    LINEAGE.relative_to(
                        ROOT
                    )
                ),

            "content_sha256":
                lineage_sha,
        },

        "generation_contract": {
            "development_trials_only":
                True,

            "calibration_raw_files_opened":
                0,

            "final_test_raw_files_opened":
                0,

            "corrupted_files_materialized":
                False,

            "attempt_every_trial_family_severity":
                True,

            "instances_per_trial_family_severity":
                1,

            "failed_admissibility_recorded_not_replaced":
                True,

            "no_op_instances_allowed":
                False,

            "selection_algorithm":
                (
                    "P0 deterministic hierarchical "
                    "SHA256 selection V1"
                ),

            "channel_selection_is_uniform_over_eligible_channels":
                True,

            "start_selection_is_uniform_over_admissible_starts_for_selected_channel":
                True,

            "timing_policy_unit":
                "ms",

            "timing_offset_converted_to_raw_timestamp_units":
                True,
        },

        "development_trial_count":
            len(
                trials
            ),

        "attempt_count":
            len(
                attempts
            ),

        "dataset_trial_counts":
            dict(
                dataset_counts
            ),

        "trials":
            trials,

        "attempts":
            attempts,

        "status_counts": [
            {
                "dataset":
                    key[0],

                "family":
                    key[1],

                "severity":
                    key[2],

                "status":
                    key[3],

                "count":
                    value,
            }
            for key, value
            in sorted(
                status_counts.items()
            )
        ],

        "not_admissible_reason_counts": [
            {
                "dataset":
                    key[0],

                "family":
                    key[1],

                "severity":
                    key[2],

                "reason":
                    key[3],

                "count":
                    value,
            }
            for key, value
            in sorted(
                reason_counts.items()
            )
        ],
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
    print("=" * 110)
    print(
        "P0 DEVELOPMENT ADMISSIBILITY SUMMARY"
    )
    print("=" * 110)

    print(
        "development_trial_count =",
        len(
            trials
        ),
    )

    print(
        "attempt_count =",
        len(
            attempts
        ),
    )

    print(
        "dataset_trial_counts =",
        dict(
            dataset_counts
        ),
    )

    print(
        "raw_files_opened =",
        raw_files_opened,
    )

    print(
        "calibration_raw_files_opened = 0"
    )

    print(
        "final_test_raw_files_opened = 0"
    )

    print()
    print("status_counts:")

    for key, value in sorted(
        status_counts.items()
    ):
        print(
            " ",
            key,
            "=",
            value,
        )

    print()
    print("not_admissible_reason_counts:")

    if reason_counts:
        for key, value in sorted(
            reason_counts.items()
        ):
            print(
                " ",
                key,
                "=",
                value,
            )
    else:
        print("  NONE")

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
        "P0_DEVELOPMENT_SPEC_MANIFEST_V1_CANDIDATE_PASS = True"
    )


if __name__ == "__main__":
    main()
