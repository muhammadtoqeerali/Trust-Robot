from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import json


ROOT = Path.home() / "toqeer" / "IMU_Reliability"

COMPACT = (
    ROOT
    / "data/manifests/"
      "p0_development_spec_manifest_v1_compact_candidate.json"
)

OUTPUT = (
    ROOT
    / "data/manifests/"
      "p0_development_spec_receipt_v1_candidate.json"
)


EXPECTED_COMPACT_SHA = (
    "58c00ab35be2e8c34d4a68ca48b379a7ccce83bafa25bcd143a9e221e5628608"
)

EXPECTED_FULL_SHA = (
    "103ef03864457269a348fd304c5f350c408bea02f55a57cff7940e1525f2d69e"
)

EXPECTED_POLICY_SHA = (
    "cb33c32951930453db550dfd02deab67a9eb51e851edf1a186e7faa4a5432220"
)

EXPECTED_TRIAL_COUNT = 4621
EXPECTED_ATTEMPT_COUNT = 69315
EXPECTED_ADMISSIBLE = 65771
EXPECTED_NOT_ADMISSIBLE = 3544


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
            "Internal hash mismatch: "
            f"{stored} != {computed}"
        )

    return stored


def attempt_semantics(row):
    base = {
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
        base.update(
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
        base["reason"] = row["reason"]

    else:
        raise RuntimeError(
            "Unexpected attempt status: "
            f"{row['status']}"
        )

    return base


def main():
    compact = json.loads(
        COMPACT.read_text(
            encoding="utf-8"
        )
    )

    compact_sha = verify_hash(
        compact
    )

    if compact_sha != EXPECTED_COMPACT_SHA:
        raise RuntimeError(
            "Compact candidate differs from reviewed artifact"
        )


    full_sha = (
        compact[
            "source_full_candidate"
        ][
            "content_sha256"
        ]
    )

    if full_sha != EXPECTED_FULL_SHA:
        raise RuntimeError(
            "Full candidate anchor changed"
        )


    policy_sha = (
        compact[
            "source_policy"
        ][
            "content_sha256"
        ]
    )

    if policy_sha != EXPECTED_POLICY_SHA:
        raise RuntimeError(
            "Frozen policy anchor changed"
        )


    if compact["partition"] != "development":
        raise RuntimeError(
            "Receipt source is not development-only"
        )


    if (
        compact["development_trial_count"]
        != EXPECTED_TRIAL_COUNT
    ):
        raise RuntimeError(
            "Trial count changed"
        )

    if (
        compact["attempt_count"]
        != EXPECTED_ATTEMPT_COUNT
    ):
        raise RuntimeError(
            "Attempt count changed"
        )

    if (
        compact["admissible_count"]
        != EXPECTED_ADMISSIBLE
    ):
        raise RuntimeError(
            "Admissible count changed"
        )

    if (
        compact["not_admissible_count"]
        != EXPECTED_NOT_ADMISSIBLE
    ):
        raise RuntimeError(
            "NOT_ADMISSIBLE count changed"
        )


    trials = {
        row["trial_id"]: row
        for row in compact["trials"]
    }

    if len(trials) != EXPECTED_TRIAL_COUNT:
        raise RuntimeError(
            "Duplicate/missing trial IDs"
        )


    grouped = defaultdict(list)

    for row in compact["attempts"]:
        grouped[
            row["trial_id"]
        ].append(
            attempt_semantics(
                row
            )
        )


    if set(grouped) != set(trials):
        raise RuntimeError(
            "Trial set differs between trial and attempt records"
        )


    trial_receipts = []

    total_status = Counter()


    for trial_id in sorted(trials):

        trial = trials[
            trial_id
        ]

        attempts = grouped[
            trial_id
        ]

        attempts.sort(
            key=lambda row: (
                FAMILY_ORDER[
                    row["family"]
                ],
                SEVERITY_ORDER[
                    row["severity"]
                ],
            )
        )


        if len(attempts) != 15:
            raise RuntimeError(
                f"Expected 15 attempts for {trial_id}, "
                f"got {len(attempts)}"
            )


        combinations = {
            (
                row["family"],
                row["severity"],
            )
            for row in attempts
        }

        if len(combinations) != 15:
            raise RuntimeError(
                "Duplicate family/severity combination: "
                f"{trial_id}"
            )


        admissible = sum(
            row["status"] == "ADMISSIBLE"
            for row in attempts
        )

        not_admissible = (
            len(attempts)
            - admissible
        )


        for row in attempts:
            total_status[
                (
                    trial["dataset"],
                    row["family"],
                    row["severity"],
                    row["status"],
                )
            ] += 1


        semantic_payload = {
            "trial_id":
                trial_id,

            "clean_stream_fingerprint":
                trial[
                    "clean_stream_fingerprint"
                ],

            "attempts":
                attempts,
        }


        trial_receipts.append(
            {
                "trial_id":
                    trial_id,

                "dataset":
                    trial["dataset"],

                "historical_windows":
                    int(
                        trial[
                            "historical_windows"
                        ]
                    ),

                "model_coupled_p0_eligible":
                    bool(
                        trial[
                            "model_coupled_p0_eligible"
                        ]
                    ),

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
                        semantic_payload
                    ),
            }
        )


    if sum(
        row["admissible_count"]
        for row in trial_receipts
    ) != EXPECTED_ADMISSIBLE:
        raise RuntimeError(
            "Trial receipt admissible total mismatch"
        )


    if sum(
        row["not_admissible_count"]
        for row in trial_receipts
    ) != EXPECTED_NOT_ADMISSIBLE:
        raise RuntimeError(
            "Trial receipt rejection total mismatch"
        )


    zero_window = sorted(
        row["trial_id"]
        for row in trial_receipts
        if row[
            "historical_windows"
        ] == 0
    )

    if zero_window != [
        "KFALL:106/27/1",
        "KFALL:106/27/5",
    ]:
        raise RuntimeError(
            "Zero-window trial set changed"
        )


    for trial_id in zero_window:
        record = next(
            row
            for row in trial_receipts
            if row["trial_id"] == trial_id
        )

        if record[
            "model_coupled_p0_eligible"
        ]:
            raise RuntimeError(
                "Zero-window trial became model-coupled"
            )


    payload = {
        "receipt_id":
            "P0_DEVELOPMENT_SPEC_RECEIPT_V1",

        "status":
            "candidate_before_development_spec_receipt_freeze",

        "partition":
            "development",

        "source_artifacts": {
            "full_candidate_content_sha256":
                full_sha,

            "compact_candidate_content_sha256":
                compact_sha,

            "policy":
                compact[
                    "source_policy"
                ],

            "registry":
                compact[
                    "source_registry"
                ],

            "lineage":
                compact[
                    "source_lineage"
                ],
        },

        "generation_contract":
            compact[
                "generation_contract"
            ],

        "receipt_contract": {
            "large_candidate_files_required_in_git":
                False,

            "full_candidate_cryptographically_anchored":
                True,

            "compact_candidate_cryptographically_anchored":
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
        },

        "development_trial_count":
            EXPECTED_TRIAL_COUNT,

        "attempt_count":
            EXPECTED_ATTEMPT_COUNT,

        "admissible_count":
            EXPECTED_ADMISSIBLE,

        "not_admissible_count":
            EXPECTED_NOT_ADMISSIBLE,

        "dataset_trial_counts":
            compact[
                "dataset_trial_counts"
            ],

        "historical_zero_window_trials":
            zero_window,

        "status_counts":
            compact[
                "status_counts"
            ],

        "not_admissible_reason_counts":
            compact[
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
    print("P0 DEVELOPMENT SPEC RECEIPT V1")
    print("=" * 100)

    print(
        "full_candidate_sha256 =",
        full_sha,
    )

    print(
        "compact_candidate_sha256 =",
        compact_sha,
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
        EXPECTED_ADMISSIBLE,
    )

    print(
        "not_admissible_count =",
        EXPECTED_NOT_ADMISSIBLE,
    )

    print(
        "zero_window_trials =",
        zero_window,
    )

    print()
    print(
        "receipt_size_bytes =",
        size,
    )

    print(
        "receipt_size_mib =",
        size / (1024 * 1024),
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
        "P0_DEVELOPMENT_SPEC_RECEIPT_V1_CANDIDATE_PASS = True"
    )


if __name__ == "__main__":
    main()
