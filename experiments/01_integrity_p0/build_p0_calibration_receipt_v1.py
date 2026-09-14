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
      "p0_calibration_spec_manifest_v1_candidate.json"
)

OUTPUT = (
    ROOT
    / "data/manifests/"
      "p0_calibration_spec_receipt_v1_candidate.json"
)


EXPECTED_SOURCE_SHA = (
    "f95ada2da8355b21f43aac6d7d9438eeebf70305f21e7a1e3a1d66c11fd498a6"
)

EXPECTED_POLICY_SHA = (
    "cb33c32951930453db550dfd02deab67a9eb51e851edf1a186e7faa4a5432220"
)

EXPECTED_DEV_RECEIPT_SHA = (
    "d6f0f26746e80d7bd926f83bea71aaa2f714fd27a7dd73a2af021a09803c479a"
)

EXPECTED_REGISTRY_SHA = (
    "a99f3031e2efd388b8dcbf26673c41ae142a3ef3ea1eb8c2a4b609b819a13d71"
)

EXPECTED_LINEAGE_SHA = (
    "d5d792aa74ef4c0e1414c7737bcfde31dca765d3e66175e0f6c51e0295b82e36"
)

EXPECTED_TRIAL_COUNT = 446
EXPECTED_ATTEMPT_COUNT = 6690
EXPECTED_ADMISSIBLE = 6352
EXPECTED_NOT_ADMISSIBLE = 338

EXPECTED_DATASET_COUNTS = {
    "KFALL": 314,
    "UNIVRFALL": 132,
}


FAMILY_ORDER = {
    "FRAME_GAP": 0,
    "FRAME_REPEAT": 1,
    "CHANNEL_FREEZE": 2,
    "TIMING_PERTURBATION": 3,
    "RANGE_CLIP": 4,
}

SEVERITY_ORDER = {
    "low": 0,
    "medium": 1,
    "high": 2,
}


EXPECTED_RANGE = {
    ("KFALL", "low"):
        (171, 143),

    ("KFALL", "medium"):
        (234, 80),

    ("KFALL", "high"):
        (250, 64),

    ("UNIVRFALL", "low"):
        (83, 49),

    ("UNIVRFALL", "medium"):
        (130, 2),

    ("UNIVRFALL", "high"):
        (132, 0),
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
            "Internal content hash mismatch: "
            f"{stored} != {computed}"
        )

    return stored


def semantic_attempt(row):
    result = {
        "trial_id":
            row["trial_id"],

        "family":
            row["family"],

        "severity":
            row["severity"],

        "status":
            row["status"],
    }

    if row["status"] == "ADMISSIBLE":
        result.update(
            {
                "spec":
                    row["spec"],

                "spec_id":
                    row["spec_id"],

                "injection_id":
                    row["injection_id"],

                "corrupt_stream_fingerprint":
                    row[
                        "corrupt_stream_fingerprint"
                    ],
            }
        )

    elif row["status"] == "NOT_ADMISSIBLE":
        result[
            "reason"
        ] = row[
            "reason"
        ]

    else:
        raise RuntimeError(
            "Unexpected attempt status: "
            f"{row['status']}"
        )

    return result


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
            "Calibration candidate differs from reviewed artifact"
        )


    if source[
        "manifest_id"
    ] != "P0_CALIBRATION_SPEC_MANIFEST_V1":
        raise RuntimeError(
            "Unexpected calibration manifest ID"
        )

    if source[
        "partition"
    ] != "calibration":
        raise RuntimeError(
            "Manifest is not calibration-only"
        )


    if source[
        "source_policy"
    ][
        "content_sha256"
    ] != EXPECTED_POLICY_SHA:
        raise RuntimeError(
            "Frozen policy anchor changed"
        )

    if source[
        "source_development_receipt"
    ][
        "content_sha256"
    ] != EXPECTED_DEV_RECEIPT_SHA:
        raise RuntimeError(
            "Development receipt anchor changed"
        )

    if source[
        "source_registry"
    ][
        "content_sha256"
    ] != EXPECTED_REGISTRY_SHA:
        raise RuntimeError(
            "Registry anchor changed"
        )

    if source[
        "source_lineage"
    ][
        "content_sha256"
    ] != EXPECTED_LINEAGE_SHA:
        raise RuntimeError(
            "Lineage anchor changed"
        )


    contract = source[
        "generation_contract"
    ]

    required_true = (
        "calibration_trials_only",
        "corruption_policy_already_frozen",
        "attempt_every_trial_family_severity",
        "failed_admissibility_recorded_not_replaced",
        "selection_implementation_reused_from_development_generator",
        "timing_offset_converted_to_raw_timestamp_units",
    )

    for key in required_true:
        if contract[key] is not True:
            raise RuntimeError(
                f"Expected True: {key}"
            )


    required_false = (
        "corruption_policy_modified",
        "severity_grid_modified",
        "placement_rules_modified",
        "seed_derivation_modified",
        "admissibility_rules_modified",
        "corrupted_files_materialized",
        "no_op_instances_allowed",
        "detector_thresholds_selected_during_generation",
        "persistence_selected_during_generation",
        "ood_operating_point_selected_during_generation",
        "task_or_detector_outcomes_evaluated_during_generation",
    )

    for key in required_false:
        if contract[key] is not False:
            raise RuntimeError(
                f"Expected False: {key}"
            )


    if contract[
        "development_raw_files_opened"
    ] != 0:
        raise RuntimeError(
            "Development raw files entered calibration generation"
        )

    if contract[
        "calibration_raw_files_opened"
    ] != EXPECTED_TRIAL_COUNT:
        raise RuntimeError(
            "Unexpected calibration raw-file count"
        )

    if contract[
        "final_test_raw_files_opened"
    ] != 0:
        raise RuntimeError(
            "Final-test raw files entered calibration generation"
        )


    if source[
        "calibration_trial_count"
    ] != EXPECTED_TRIAL_COUNT:
        raise RuntimeError(
            "Calibration trial count changed"
        )

    if source[
        "model_coupled_trial_count"
    ] != EXPECTED_TRIAL_COUNT:
        raise RuntimeError(
            "Calibration model-coupled count changed"
        )

    if source[
        "attempt_count"
    ] != EXPECTED_ATTEMPT_COUNT:
        raise RuntimeError(
            "Attempt count changed"
        )

    if source[
        "dataset_trial_counts"
    ] != EXPECTED_DATASET_COUNTS:
        raise RuntimeError(
            "Dataset counts changed"
        )


    trials = source[
        "trials"
    ]

    attempts = source[
        "attempts"
    ]


    if len(
        trials
    ) != EXPECTED_TRIAL_COUNT:
        raise RuntimeError(
            "Trial-record count changed"
        )

    if len(
        attempts
    ) != EXPECTED_ATTEMPT_COUNT:
        raise RuntimeError(
            "Attempt-record count changed"
        )


    trial_by_id = {}

    for row in trials:
        trial_id = row[
            "trial_id"
        ]

        if trial_id in trial_by_id:
            raise RuntimeError(
                f"Duplicate trial ID: {trial_id}"
            )

        if row[
            "model_coupled_p0_eligible"
        ] is not True:
            raise RuntimeError(
                "Unexpected non-model-coupled calibration trial: "
                f"{trial_id}"
            )

        if int(
            row[
                "historical_windows"
            ]
        ) <= 0:
            raise RuntimeError(
                "Calibration trial has no protected windows: "
                f"{trial_id}"
            )

        trial_by_id[
            trial_id
        ] = row


    grouped = defaultdict(
        list
    )

    observed_status = Counter()
    observed_reasons = Counter()

    seen_attempt_ids = set()
    seen_injection_ids = set()


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
        ] != "calibration":
            raise RuntimeError(
                "Non-calibration attempt found"
            )


        attempt_id = row[
            "attempt_id"
        ]

        if attempt_id in seen_attempt_ids:
            raise RuntimeError(
                f"Duplicate attempt ID: {attempt_id}"
            )

        seen_attempt_ids.add(
            attempt_id
        )


        dataset = row[
            "dataset"
        ]

        family = row[
            "family"
        ]

        severity = row[
            "severity"
        ]

        status = row[
            "status"
        ]


        if dataset != trial_by_id[
            trial_id
        ][
            "dataset"
        ]:
            raise RuntimeError(
                "Attempt/trial dataset disagreement"
            )


        grouped[
            trial_id
        ].append(
            semantic_attempt(
                row
            )
        )


        observed_status[
            (
                dataset,
                family,
                severity,
                status,
            )
        ] += 1


        if status == "ADMISSIBLE":
            if row[
                "reason"
            ] is not None:
                raise RuntimeError(
                    "ADMISSIBLE record has rejection reason"
                )

            injection_id = row[
                "injection_id"
            ]

            if injection_id in seen_injection_ids:
                raise RuntimeError(
                    "Duplicate injection ID: "
                    f"{injection_id}"
                )

            seen_injection_ids.add(
                injection_id
            )


            if row[
                "clean_stream_fingerprint"
            ] != trial_by_id[
                trial_id
            ][
                "clean_stream_fingerprint"
            ]:
                raise RuntimeError(
                    "Clean fingerprint mismatch"
                )


            if row[
                "clean_stream_fingerprint"
            ] == row[
                "corrupt_stream_fingerprint"
            ]:
                raise RuntimeError(
                    "No-op admissible injection"
                )


        elif status == "NOT_ADMISSIBLE":
            reason = row[
                "reason"
            ]

            observed_reasons[
                (
                    dataset,
                    family,
                    severity,
                    reason,
                )
            ] += 1

            if family != "RANGE_CLIP":
                raise RuntimeError(
                    "Non-RANGE_CLIP rejection found"
                )

            if reason != (
                "NO_RANGE_EXCEEDANCE_FOR_SEVERITY"
            ):
                raise RuntimeError(
                    "Unexpected rejection reason"
                )

        else:
            raise RuntimeError(
                f"Unexpected status: {status}"
            )


    expected_grid = {
        (
            family,
            severity,
        )
        for family
        in FAMILY_ORDER
        for severity
        in SEVERITY_ORDER
    }


    trial_receipts = []

    total_admissible = 0
    total_not = 0


    for trial_id in sorted(
        trial_by_id
    ):
        trial = trial_by_id[
            trial_id
        ]

        rows = grouped[
            trial_id
        ]

        rows.sort(
            key=lambda row: (
                FAMILY_ORDER[
                    row[
                        "family"
                    ]
                ],
                SEVERITY_ORDER[
                    row[
                        "severity"
                    ]
                ],
            )
        )


        if len(rows) != 15:
            raise RuntimeError(
                "Expected 15 calibration attempts for "
                f"{trial_id}; got {len(rows)}"
            )


        actual_grid = {
            (
                row["family"],
                row["severity"],
            )
            for row in rows
        }

        if actual_grid != expected_grid:
            raise RuntimeError(
                "Incomplete family/severity grid: "
                f"{trial_id}"
            )


        admissible = sum(
            row[
                "status"
            ] == "ADMISSIBLE"
            for row in rows
        )

        not_admissible = (
            15
            - admissible
        )

        total_admissible += (
            admissible
        )

        total_not += (
            not_admissible
        )


        semantics = {
            "trial_id":
                trial_id,

            "clean_stream_fingerprint":
                trial[
                    "clean_stream_fingerprint"
                ],

            "attempts":
                rows,
        }


        trial_receipts.append(
            {
                "trial_id":
                    trial_id,

                "dataset":
                    trial[
                        "dataset"
                    ],

                "historical_windows":
                    int(
                        trial[
                            "historical_windows"
                        ]
                    ),

                "model_coupled_p0_eligible":
                    True,

                "clean_n_samples":
                    int(
                        trial[
                            "clean_n_samples"
                        ]
                    ),

                "clean_n_channels":
                    int(
                        trial[
                            "clean_n_channels"
                        ]
                    ),

                "clean_stream_fingerprint":
                    trial[
                        "clean_stream_fingerprint"
                    ],

                "attempt_count":
                    15,

                "admissible_count":
                    admissible,

                "not_admissible_count":
                    not_admissible,

                "attempt_semantics_sha256":
                    canonical_digest(
                        semantics
                    ),
            }
        )


    if total_admissible != EXPECTED_ADMISSIBLE:
        raise RuntimeError(
            "Reviewed admissible total changed: "
            f"{total_admissible}"
        )

    if total_not != EXPECTED_NOT_ADMISSIBLE:
        raise RuntimeError(
            "Reviewed rejection total changed: "
            f"{total_not}"
        )


    for (
        dataset,
        severity
    ), (
        expected_admissible,
        expected_not,
    ) in EXPECTED_RANGE.items():

        actual_admissible = (
            observed_status.get(
                (
                    dataset,
                    "RANGE_CLIP",
                    severity,
                    "ADMISSIBLE",
                ),
                0,
            )
        )

        actual_not = (
            observed_status.get(
                (
                    dataset,
                    "RANGE_CLIP",
                    severity,
                    "NOT_ADMISSIBLE",
                ),
                0,
            )
        )

        if (
            actual_admissible
            != expected_admissible
            or actual_not
            != expected_not
        ):
            raise RuntimeError(
                "Reviewed RANGE_CLIP counts changed: "
                f"{dataset}/{severity}: "
                f"{actual_admissible}/"
                f"{actual_not}"
            )


    nonrange_admissible = sum(
        count
        for (
            dataset,
            family,
            severity,
            status,
        ), count
        in observed_status.items()
        if (
            family != "RANGE_CLIP"
            and status == "ADMISSIBLE"
        )
    )

    expected_nonrange = (
        EXPECTED_TRIAL_COUNT
        * 4
        * 3
    )

    if (
        nonrange_admissible
        != expected_nonrange
    ):
        raise RuntimeError(
            "Non-range admissibility changed"
        )


    payload = {
        "receipt_id":
            "P0_CALIBRATION_SPEC_RECEIPT_V1",

        "status":
            "candidate_before_calibration_spec_receipt_freeze",

        "partition":
            "calibration",

        "source_artifacts": {
            "full_candidate_content_sha256":
                source_sha,

            "policy":
                source[
                    "source_policy"
                ],

            "development_receipt":
                source[
                    "source_development_receipt"
                ],

            "registry":
                source[
                    "source_registry"
                ],

            "lineage":
                source[
                    "source_lineage"
                ],
        },

        "generation_contract":
            source[
                "generation_contract"
            ],

        "receipt_contract": {
            "large_candidate_required_in_git":
                False,

            "full_candidate_cryptographically_anchored":
                True,

            "each_trial_clean_stream_fingerprint_preserved":
                True,

            "each_trial_exact_attempt_semantics_cryptographically_anchored":
                True,

            "selected_specs_included_in_trial_digest":
                True,

            "spec_ids_included_in_trial_digest":
                True,

            "injection_ids_included_in_trial_digest":
                True,

            "corrupt_fingerprints_included_in_trial_digest":
                True,

            "rejection_reasons_included_in_trial_digest":
                True,

            "raw_data_reread_while_building_receipt":
                False,

            "thresholds_selected_while_building_receipt":
                False,
        },

        "calibration_trial_count":
            EXPECTED_TRIAL_COUNT,

        "model_coupled_trial_count":
            EXPECTED_TRIAL_COUNT,

        "attempt_count":
            EXPECTED_ATTEMPT_COUNT,

        "admissible_count":
            EXPECTED_ADMISSIBLE,

        "not_admissible_count":
            EXPECTED_NOT_ADMISSIBLE,

        "dataset_trial_counts":
            source[
                "dataset_trial_counts"
            ],

        "status_counts":
            source[
                "status_counts"
            ],

        "not_admissible_reason_counts":
            source[
                "not_admissible_reason_counts"
            ],

        "trial_receipts":
            trial_receipts,
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


    size = OUTPUT.stat().st_size


    print("=" * 100)
    print(
        "P0 CALIBRATION SPEC RECEIPT V1"
    )
    print("=" * 100)

    print(
        "full_candidate_sha256 =",
        source_sha,
    )

    print(
        "calibration_trial_count =",
        EXPECTED_TRIAL_COUNT,
    )

    print(
        "attempt_count =",
        EXPECTED_ATTEMPT_COUNT,
    )

    print(
        "admissible_count =",
        EXPECTED_ADMISSIBLE,
    )

    print(
        "not_admissible_count =",
        EXPECTED_NOT_ADMISSIBLE,
    )

    print()
    print(
        "receipt_size_bytes =",
        size,
    )

    print(
        "receipt_size_mib =",
        size / (
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
        "P0_CALIBRATION_SPEC_RECEIPT_V1_CANDIDATE_PASS = True"
    )


if __name__ == "__main__":
    main()
