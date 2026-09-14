from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import json


ROOT = Path.home() / "toqeer" / "IMU_Reliability"

SOURCE = (
    ROOT
    / "data/manifests/"
      "p0_development_spec_manifest_v1_candidate.json"
)

OUTPUT = (
    ROOT
    / "data/manifests/"
      "p0_development_spec_manifest_v1_compact_candidate.json"
)


EXPECTED_SOURCE_SHA = (
    "103ef03864457269a348fd304c5f350c408bea02f55a57cff7940e1525f2d69e"
)

EXPECTED_TRIAL_COUNT = 4621
EXPECTED_ATTEMPT_COUNT = 69315

EXPECTED_DATASET_COUNTS = {
    "KFALL": 3829,
    "UNIVRFALL": 792,
}

FAMILIES = (
    "FRAME_GAP",
    "FRAME_REPEAT",
    "CHANNEL_FREEZE",
    "TIMING_PERTURBATION",
    "RANGE_CLIP",
)

SEVERITIES = (
    "low",
    "medium",
    "high",
)


EXPECTED_RANGE = {
    ("KFALL", "low"):
        (2181, 1648),

    ("KFALL", "medium"):
        (2864, 965),

    ("KFALL", "high"):
        (3222, 607),

    ("UNIVRFALL", "low"):
        (488, 304),

    ("UNIVRFALL", "medium"):
        (781, 11),

    ("UNIVRFALL", "high"):
        (783, 9),
}


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
            "Source candidate internal hash mismatch: "
            f"{stored} != {computed}"
        )

    return stored


def main():
    source = json.loads(
        SOURCE.read_text(
            encoding="utf-8"
        )
    )

    source_sha = verify_hash(
        source
    )

    if source_sha != EXPECTED_SOURCE_SHA:
        raise RuntimeError(
            "Candidate differs from reviewed development manifest: "
            f"{source_sha}"
        )


    if source[
        "manifest_id"
    ] != "P0_DEVELOPMENT_SPEC_MANIFEST_V1":
        raise RuntimeError(
            "Unexpected manifest ID"
        )

    if source[
        "partition"
    ] != "development":
        raise RuntimeError(
            "Unexpected partition"
        )

    contract = source[
        "generation_contract"
    ]

    required_true = (
        "development_trials_only",
        "failed_admissibility_recorded_not_replaced",
        "no_op_instances_allowed",
        "timing_offset_converted_to_raw_timestamp_units",
    )

    for key in required_true:
        if key == "no_op_instances_allowed":
            if contract[key] is not False:
                raise RuntimeError(
                    "No-op instances must remain forbidden"
                )
        else:
            if contract[key] is not True:
                raise RuntimeError(
                    f"Expected True: {key}"
                )


    if contract[
        "calibration_raw_files_opened"
    ] != 0:
        raise RuntimeError(
            "Calibration raw files were opened"
        )

    if contract[
        "final_test_raw_files_opened"
    ] != 0:
        raise RuntimeError(
            "Final-test raw files were opened"
        )

    if contract[
        "corrupted_files_materialized"
    ] is not False:
        raise RuntimeError(
            "Corrupted full files unexpectedly materialized"
        )


    trials = source[
        "trials"
    ]

    attempts = source[
        "attempts"
    ]


    if len(trials) != EXPECTED_TRIAL_COUNT:
        raise RuntimeError(
            f"Unexpected trial count: {len(trials)}"
        )

    if len(attempts) != EXPECTED_ATTEMPT_COUNT:
        raise RuntimeError(
            f"Unexpected attempt count: {len(attempts)}"
        )


    dataset_counts = Counter(
        row["dataset"]
        for row in trials
    )

    if dict(
        dataset_counts
    ) != EXPECTED_DATASET_COUNTS:
        raise RuntimeError(
            "Dataset trial counts changed: "
            f"{dict(dataset_counts)}"
        )


    trial_by_id = {}

    for row in trials:
        trial_id = row[
            "trial_id"
        ]

        if trial_id in trial_by_id:
            raise RuntimeError(
                f"Duplicate trial_id: {trial_id}"
            )

        trial_by_id[
            trial_id
        ] = row


    zero_window = sorted(
        row["trial_id"]
        for row in trials
        if int(
            row[
                "historical_windows"
            ]
        ) == 0
    )

    expected_zero_window = [
        "KFALL:106/27/1",
        "KFALL:106/27/5",
    ]

    if zero_window != expected_zero_window:
        raise RuntimeError(
            "Historical zero-window set changed: "
            f"{zero_window}"
        )

    for trial_id in zero_window:
        if trial_by_id[
            trial_id
        ][
            "model_coupled_p0_eligible"
        ]:
            raise RuntimeError(
                "Zero-window trial became model-coupled: "
                f"{trial_id}"
            )


    seen_attempt_keys = set()
    seen_attempt_ids = set()
    seen_injection_ids = set()

    per_trial = defaultdict(
        set
    )

    recomputed_status = Counter()
    recomputed_reasons = Counter()

    admissible_count = 0
    not_admissible_count = 0


    timing_expected_raw_offsets = {
        "KFALL": {
            "low": 0.01,
            "medium": 0.04,
            "high": 0.09,
        },

        "UNIVRFALL": {
            "low": 10.0,
            "medium": 40.0,
            "high": 90.0,
        },
    }


    for row in attempts:
        trial_id = row[
            "trial_id"
        ]

        if trial_id not in trial_by_id:
            raise RuntimeError(
                "Attempt references unknown trial: "
                f"{trial_id}"
            )

        if row[
            "partition"
        ] != "development":
            raise RuntimeError(
                "Non-development attempt found"
            )

        family = row[
            "family"
        ]

        severity = row[
            "severity"
        ]

        dataset = row[
            "dataset"
        ]

        if family not in FAMILIES:
            raise RuntimeError(
                f"Unexpected family: {family}"
            )

        if severity not in SEVERITIES:
            raise RuntimeError(
                f"Unexpected severity: {severity}"
            )

        if dataset != trial_by_id[
            trial_id
        ][
            "dataset"
        ]:
            raise RuntimeError(
                "Attempt/trial dataset disagreement: "
                f"{trial_id}"
            )


        key = (
            trial_id,
            family,
            severity,
            int(
                row[
                    "replicate_index"
                ]
            ),
        )

        if key in seen_attempt_keys:
            raise RuntimeError(
                f"Duplicate attempt tuple: {key}"
            )

        seen_attempt_keys.add(
            key
        )


        attempt_id = row[
            "attempt_id"
        ]

        if attempt_id in seen_attempt_ids:
            raise RuntimeError(
                f"Duplicate attempt_id: {attempt_id}"
            )

        seen_attempt_ids.add(
            attempt_id
        )


        per_trial[
            trial_id
        ].add(
            (
                family,
                severity,
            )
        )


        status = row[
            "status"
        ]

        recomputed_status[
            (
                dataset,
                family,
                severity,
                status,
            )
        ] += 1


        if status == "ADMISSIBLE":
            admissible_count += 1

            if row[
                "reason"
            ] is not None:
                raise RuntimeError(
                    "ADMISSIBLE attempt has reason"
                )

            injection_id = row[
                "injection_id"
            ]

            if injection_id in seen_injection_ids:
                raise RuntimeError(
                    "Duplicate injection_id: "
                    f"{injection_id}"
                )

            seen_injection_ids.add(
                injection_id
            )


            clean_fp = row[
                "clean_stream_fingerprint"
            ]

            corrupt_fp = row[
                "corrupt_stream_fingerprint"
            ]

            if clean_fp == corrupt_fp:
                raise RuntimeError(
                    "Admissible injection has clean==corrupt fingerprint"
                )


            trial_fp = trial_by_id[
                trial_id
            ][
                "clean_stream_fingerprint"
            ]

            if clean_fp != trial_fp:
                raise RuntimeError(
                    "Attempt/trial clean fingerprint disagreement"
                )


            spec = row[
                "spec"
            ]

            if spec[
                "kind"
            ] != family:
                raise RuntimeError(
                    "Spec family mismatch"
                )

            if spec[
                "severity"
            ] != severity:
                raise RuntimeError(
                    "Spec severity mismatch"
                )


            if family == (
                "TIMING_PERTURBATION"
            ):
                offset = float(
                    spec[
                        "parameters"
                    ][
                        "offset"
                    ]
                )

                expected_offset = (
                    timing_expected_raw_offsets[
                        dataset
                    ][severity]
                )

                if not np_isclose(
                    offset,
                    expected_offset,
                ):
                    raise RuntimeError(
                        "Timing raw-unit conversion changed: "
                        f"{dataset} {severity}: "
                        f"{offset} != {expected_offset}"
                    )


            if family == "RANGE_CLIP":
                if len(
                    spec[
                        "channels"
                    ]
                ) != 1:
                    raise RuntimeError(
                        "RANGE_CLIP must select one channel"
                    )

                low = float(
                    spec[
                        "parameters"
                    ][
                        "low"
                    ]
                )

                high = float(
                    spec[
                        "parameters"
                    ][
                        "high"
                    ]
                )

                if not np_isclose(
                    low,
                    -high,
                ):
                    raise RuntimeError(
                        "RANGE_CLIP is no longer symmetric"
                    )

                if row[
                    "operational"
                ][
                    "physical_rail_claim"
                ] is not False:
                    raise RuntimeError(
                        "RANGE_CLIP gained physical rail claim"
                    )


        elif status == "NOT_ADMISSIBLE":
            not_admissible_count += 1

            reason = row[
                "reason"
            ]

            if not reason:
                raise RuntimeError(
                    "NOT_ADMISSIBLE lacks reason"
                )

            recomputed_reasons[
                (
                    dataset,
                    family,
                    severity,
                    reason,
                )
            ] += 1

            if family != "RANGE_CLIP":
                raise RuntimeError(
                    "Non-RANGE_CLIP attempt became inadmissible: "
                    f"{trial_id} {family} {severity}"
                )

            if reason != (
                "NO_RANGE_EXCEEDANCE_FOR_SEVERITY"
            ):
                raise RuntimeError(
                    f"Unexpected rejection reason: {reason}"
                )

        else:
            raise RuntimeError(
                f"Unexpected status: {status}"
            )


    expected_per_trial = {
        (
            family,
            severity,
        )
        for family in FAMILIES
        for severity in SEVERITIES
    }

    for trial_id, combinations in (
        per_trial.items()
    ):
        if combinations != expected_per_trial:
            raise RuntimeError(
                "Incomplete family/severity grid for "
                f"{trial_id}"
            )


    if len(
        per_trial
    ) != EXPECTED_TRIAL_COUNT:
        raise RuntimeError(
            "Not every trial received attempts"
        )


    expected_nonrange_admissible = (
        EXPECTED_TRIAL_COUNT
        * 4
        * 3
    )

    actual_nonrange_admissible = sum(
        count
        for (
            dataset,
            family,
            severity,
            status,
        ), count
        in recomputed_status.items()
        if (
            family != "RANGE_CLIP"
            and status == "ADMISSIBLE"
        )
    )

    if (
        actual_nonrange_admissible
        != expected_nonrange_admissible
    ):
        raise RuntimeError(
            "Non-range admissibility changed"
        )


    for (
        dataset,
        severity
    ), (
        expected_admissible,
        expected_not,
    ) in EXPECTED_RANGE.items():

        actual_admissible = (
            recomputed_status[
                (
                    dataset,
                    "RANGE_CLIP",
                    severity,
                    "ADMISSIBLE",
                )
            ]
        )

        actual_not = (
            recomputed_status[
                (
                    dataset,
                    "RANGE_CLIP",
                    severity,
                    "NOT_ADMISSIBLE",
                )
            ]
        )

        if (
            actual_admissible
            != expected_admissible
            or actual_not
            != expected_not
        ):
            raise RuntimeError(
                "Reviewed RANGE_CLIP counts changed: "
                f"{dataset} {severity}: "
                f"{actual_admissible}/{actual_not}"
            )


    if admissible_count != 65771:
        raise RuntimeError(
            "Unexpected admissible total: "
            f"{admissible_count}"
        )

    if not_admissible_count != 3544:
        raise RuntimeError(
            "Unexpected NOT_ADMISSIBLE total: "
            f"{not_admissible_count}"
        )


    compact_trials = []

    for row in trials:
        compact_trials.append(
            {
                "trial_id":
                    row[
                        "trial_id"
                    ],

                "dataset":
                    row[
                        "dataset"
                    ],

                "relative_trial":
                    row[
                        "relative_trial"
                    ],

                "historical_windows":
                    int(
                        row[
                            "historical_windows"
                        ]
                    ),

                "model_coupled_p0_eligible":
                    bool(
                        row[
                            "model_coupled_p0_eligible"
                        ]
                    ),

                "clean_n_samples":
                    int(
                        row[
                            "clean_n_samples"
                        ]
                    ),

                "clean_n_channels":
                    int(
                        row[
                            "clean_n_channels"
                        ]
                    ),

                "clean_stream_fingerprint":
                    row[
                        "clean_stream_fingerprint"
                    ],

                "timestamp_scale_to_ms":
                    float(
                        row[
                            "timestamp_scale_to_ms"
                        ]
                    ),

                "frame_counter_column":
                    row[
                        "frame_counter_column"
                    ],
            }
        )


    compact_attempts = []

    for row in attempts:
        compact = {
            "trial_id":
                row[
                    "trial_id"
                ],

            "family":
                row[
                    "family"
                ],

            "severity":
                row[
                    "severity"
                ],

            "status":
                row[
                    "status"
                ],
        }

        if row[
            "status"
        ] == "ADMISSIBLE":
            compact.update(
                {
                    "spec":
                        row[
                            "spec"
                        ],

                    "spec_id":
                        row[
                            "spec_id"
                        ],

                    "injection_id":
                        row[
                            "injection_id"
                        ],

                    "corrupt_stream_fingerprint":
                        row[
                            "corrupt_stream_fingerprint"
                        ],
                }
            )

        else:
            compact[
                "reason"
            ] = row[
                "reason"
            ]

        compact_attempts.append(
            compact
        )


    payload = {
        "manifest_id":
            "P0_DEVELOPMENT_SPEC_MANIFEST_V1",

        "status":
            "compact_candidate_validated_before_freeze",

        "partition":
            "development",

        "source_full_candidate": {
            "path":
                str(
                    SOURCE.relative_to(
                        ROOT
                    )
                ),

            "content_sha256":
                source_sha,
        },

        "source_policy":
            source[
                "source_policy"
            ],

        "source_registry":
            source[
                "source_registry"
            ],

        "source_lineage":
            source[
                "source_lineage"
            ],

        "generation_contract":
            source[
                "generation_contract"
            ],

        "development_trial_count":
            EXPECTED_TRIAL_COUNT,

        "attempt_count":
            EXPECTED_ATTEMPT_COUNT,

        "admissible_count":
            admissible_count,

        "not_admissible_count":
            not_admissible_count,

        "dataset_trial_counts":
            dict(
                dataset_counts
            ),

        "historical_zero_window_trials":
            zero_window,

        "trials":
            compact_trials,

        "attempts":
            compact_attempts,

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
                recomputed_status.items()
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
                recomputed_reasons.items()
            )
        ],

        "compaction_contract": {
            "selected_specs_preserved":
                True,

            "spec_ids_preserved":
                True,

            "injection_ids_preserved":
                True,

            "corrupt_fingerprints_preserved":
                True,

            "trial_clean_fingerprints_preserved":
                True,

            "verbose_selection_diagnostics_removed":
                True,

            "source_full_candidate_hash_preserved":
                True,

            "no_raw_data_reread_during_compaction":
                True,
        },
    }


    payload[
        "content_sha256"
    ] = canonical_digest(
        payload
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


    size_bytes = OUTPUT.stat().st_size


    print("=" * 100)
    print(
        "P0 DEVELOPMENT COMPACT MANIFEST VALIDATION"
    )
    print("=" * 100)

    print(
        "source_content_sha256 =",
        source_sha,
    )

    print(
        "development_trial_count =",
        EXPECTED_TRIAL_COUNT,
    )

    print(
        "attempt_count =",
        EXPECTED_ATTEMPT_COUNT,
    )

    print(
        "admissible_count =",
        admissible_count,
    )

    print(
        "not_admissible_count =",
        not_admissible_count,
    )

    print(
        "zero_window_trials =",
        zero_window,
    )

    print()
    print(
        "compact_size_bytes =",
        size_bytes,
    )

    print(
        "compact_size_mib =",
        size_bytes
        / (
            1024
            * 1024
        ),
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
        "P0_DEVELOPMENT_COMPACT_MANIFEST_V1_PASS = True"
    )


def np_isclose(
    a,
    b,
):
    return abs(
        float(a)
        - float(b)
    ) <= (
        1e-10
        * max(
            1.0,
            abs(
                float(a)
            ),
            abs(
                float(b)
            ),
        )
    )


if __name__ == "__main__":
    main()
