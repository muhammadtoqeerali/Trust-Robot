from __future__ import annotations

from collections import Counter, defaultdict
from hashlib import sha256
from pathlib import Path
import json
import subprocess


ROOT = Path.home() / "toqeer" / "IMU_Reliability"

LINEAGE = (
    ROOT
    / "data/provenance/"
      "reliability_lineage_v2.json"
)

SPLIT = (
    ROOT
    / "data/manifests/"
      "date2025_cnn400_inferred_split_v1.json"
)

OUTPUT = (
    ROOT
    / "data/manifests/"
      "reliability_eval_registry_v1_candidate.json"
)


EXPECTED_LINEAGE_TAG_COMMIT = (
    "4b32a68cec9f88e73b5f09e22ff3335e1d590962"
)


ROLE_TO_PARTITION = {
    "train":
        "development",

    "validation":
        "calibration",

    "test":
        "final_test",

    "historical_training_augmentation_only":
        "augmentation_only",
}


def git(*args):
    return subprocess.check_output(
        ["git", *args],
        cwd=ROOT,
        text=True,
    ).strip()


def canonical_digest(payload):
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")

    return sha256(raw).hexdigest()


def verify_content_hash(
    payload_with_hash,
):
    payload = dict(
        payload_with_hash
    )

    stored = payload.pop(
        "content_sha256"
    )

    computed = canonical_digest(
        payload
    )

    if stored != computed:
        raise RuntimeError(
            "Frozen lineage content hash mismatch: "
            f"stored={stored}, "
            f"computed={computed}"
        )

    return stored


def acquisition_scope(
    trial,
):
    dataset = trial["dataset"]

    raw = trial[
        "raw_pairing"
    ]

    historical_windows = int(
        trial[
            "historical_windows"
        ]
    )


    raw_pair_verified = (
        raw["status"]
        == "EXACT_FILENAME_PAIR"
    )


    acquisition_p0_eligible = (
        dataset
        in {
            "UNIVRFALL",
            "KFALL",
        }
        and raw_pair_verified
    )


    model_coupled_p0_eligible = (
        acquisition_p0_eligible
        and historical_windows > 0
    )


    # These are provenance qualifications, not detector outcomes.
    # No synthetic corruption truth is allowed to promote a cause.
    if dataset == "KFALL":

        frame_gap_runtime_status = (
            "HARD_QUALIFIED_FROM_RAW_COUNTER"
        )

        timing_runtime_status = (
            "NOT_HARD_UNTIL_DEV_ENVELOPE_IS_FROZEN"
        )

        freeze_runtime_status = (
            "SUSPECT_ONLY"
        )

        range_clip_runtime_status = (
            "NOT_HARD_PHYSICAL_RAIL_UNVERIFIED"
        )

    elif dataset == "UNIVRFALL":

        frame_gap_runtime_status = (
            "NOT_HARD_DERIVED_COUNTER_PROVENANCE_UNVERIFIED"
        )

        timing_runtime_status = (
            "NOT_HARD_UNTIL_PROVENANCE_AND_DEV_ENVELOPE_QUALIFY"
        )

        freeze_runtime_status = (
            "SUSPECT_ONLY"
        )

        range_clip_runtime_status = (
            "NOT_HARD_PHYSICAL_RAIL_UNVERIFIED"
        )

    else:

        frame_gap_runtime_status = (
            "NOT_EVALUATED_RAW_TRIAL_MAPPING_UNVERIFIED"
        )

        timing_runtime_status = (
            "NOT_EVALUATED_RAW_TRIAL_MAPPING_UNVERIFIED"
        )

        freeze_runtime_status = (
            "NOT_EVALUATED_RAW_TRIAL_MAPPING_UNVERIFIED"
        )

        range_clip_runtime_status = (
            "NOT_EVALUATED_RAW_TRIAL_MAPPING_UNVERIFIED"
        )


    return {
        "raw_pair_verified":
            raw_pair_verified,

        "acquisition_p0_eligible":
            acquisition_p0_eligible,

        "model_coupled_p0_eligible":
            model_coupled_p0_eligible,

        "p0_truth_families_allowed": (
            [
                "FRAME_GAP",
                "FRAME_REPEAT",
                "CHANNEL_FREEZE",
                "TIMING_PERTURBATION",
                "RANGE_CLIP",
            ]
            if acquisition_p0_eligible
            else []
        ),

        "runtime_evidence_status": {
            "FRAME_GAP":
                frame_gap_runtime_status,

            "FRAME_REPEAT":
                (
                    "NOT_HARD_WITHOUT_INDEPENDENT_DATA_PATH_EVIDENCE"
                    if acquisition_p0_eligible
                    else
                    "NOT_EVALUATED_RAW_TRIAL_MAPPING_UNVERIFIED"
                ),

            "BUFFER_STALL":
                (
                    "NOT_HARD_WITHOUT_INDEPENDENT_DATA_PATH_EVIDENCE"
                    if acquisition_p0_eligible
                    else
                    "NOT_EVALUATED_RAW_TRIAL_MAPPING_UNVERIFIED"
                ),

            "ACQ_TIMING_VIOLATION":
                timing_runtime_status,

            "RANGE_CLIP":
                range_clip_runtime_status,

            "CHANNEL_FREEZE_SUSPECT":
                freeze_runtime_status,
        },
    }


def main():
    lineage = json.loads(
        LINEAGE.read_text(
            encoding="utf-8"
        )
    )

    lineage_sha = verify_content_hash(
        lineage
    )


    if lineage["status"] != (
        "frozen_before_real_p0_corruption_and_reliability_calibration"
    ):
        raise RuntimeError(
            "Lineage manifest is not in frozen pre-P0 state"
        )


    tag_commit = git(
        "rev-parse",
        "reliability-lineage-v2^{}",
    )

    if tag_commit != EXPECTED_LINEAGE_TAG_COMMIT:
        raise RuntimeError(
            "Unexpected reliability-lineage-v2 tag: "
            f"{tag_commit}"
        )


    split = json.loads(
        SPLIT.read_text(
            encoding="utf-8"
        )
    )


    # --------------------------------------------------------
    # Independent subject-partition cross-check
    # --------------------------------------------------------

    expected_subject_partition = {}

    for subject in split[
        "train_subjects"
    ]:
        expected_subject_partition[
            str(subject)
        ] = "development"

    for subject in split[
        "validation_subjects"
    ]:
        expected_subject_partition[
            str(subject)
        ] = "calibration"

    for subject in split[
        "test_subjects"
    ]:
        expected_subject_partition[
            str(subject)
        ] = "final_test"

    expected_subject_partition[
        "999"
    ] = "augmentation_only"

    expected_subject_partition[
        "1000"
    ] = "augmentation_only"


    records = []

    partition_trial_counts = Counter()
    partition_window_counts = Counter()

    dataset_partition_counts = Counter()

    acquisition_eligible_counts = Counter()
    model_coupled_eligible_counts = Counter()

    zero_window_records = []

    subjects_by_partition = defaultdict(
        set
    )


    for trial in lineage[
        "trials"
    ]:

        role = trial[
            "role"
        ]

        if role not in ROLE_TO_PARTITION:
            raise RuntimeError(
                f"Unknown frozen role: {role}"
            )

        partition = ROLE_TO_PARTITION[
            role
        ]

        subject = str(
            trial[
                "subject"
            ]
        )

        expected_partition = (
            expected_subject_partition.get(
                subject
            )
        )

        if expected_partition != partition:
            raise RuntimeError(
                "Subject partition disagreement: "
                f"subject={subject}, "
                f"lineage={partition}, "
                f"split={expected_partition}"
            )


        historical_windows = int(
            trial[
                "historical_windows"
            ]
        )

        scope = acquisition_scope(
            trial
        )


        if historical_windows == 0:
            zero_window_records.append(
                trial[
                    "relative_trial"
                ]
            )


        record = {
            "trial_id":
                (
                    f"{trial['dataset']}:"
                    f"{trial['relative_trial']}"
                ),

            "dataset":
                trial[
                    "dataset"
                ],

            "subject":
                subject,

            "task":
                int(
                    trial[
                        "task"
                    ]
                ),

            "trial":
                int(
                    trial[
                        "trial"
                    ]
                ),

            "relative_trial":
                trial[
                    "relative_trial"
                ],

            "partition":
                partition,

            "historical_role":
                role,

            "historical_windows":
                historical_windows,

            "signal_lineage":
                trial[
                    "signal_lineage"
                ],

            "raw_pairing_status":
                trial[
                    "raw_pairing"
                ][
                    "status"
                ],

            "acquisition_scope":
                scope,

            "prospective_constraints": {
                "may_define_corruption_policy":
                    partition
                    == "development",

                "may_tune_detector_thresholds":
                    partition
                    == "calibration",

                "may_select_persistence":
                    partition
                    == "calibration",

                "may_select_ood_operating_point":
                    partition
                    == "calibration",

                "may_change_corruption_policy_after_outcome_review":
                    False,

                "final_test_outcomes_available_for_tuning":
                    False,

                "corruption_instance_created_at_registry_freeze":
                    False,
            },
        }


        records.append(
            record
        )


        partition_trial_counts[
            partition
        ] += 1

        partition_window_counts[
            partition
        ] += historical_windows

        dataset_partition_counts[
            (
                partition,
                trial[
                    "dataset"
                ],
            )
        ] += 1


        if scope[
            "acquisition_p0_eligible"
        ]:
            acquisition_eligible_counts[
                (
                    partition,
                    trial[
                        "dataset"
                    ],
                )
            ] += 1


        if scope[
            "model_coupled_p0_eligible"
        ]:
            model_coupled_eligible_counts[
                (
                    partition,
                    trial[
                        "dataset"
                    ],
                )
            ] += 1


        subjects_by_partition[
            partition
        ].add(
            subject
        )


    # --------------------------------------------------------
    # No leakage / partition invariants
    # --------------------------------------------------------

    partition_sets = {
        key:
            set(value)
        for key, value
        in subjects_by_partition.items()
    }


    for a in (
        "development",
        "calibration",
        "final_test",
    ):
        for b in (
            "development",
            "calibration",
            "final_test",
        ):
            if a >= b:
                continue

            overlap = (
                partition_sets[
                    a
                ]
                & partition_sets[
                    b
                ]
            )

            if overlap:
                raise RuntimeError(
                    "Subject leakage between "
                    f"{a} and {b}: "
                    f"{sorted(overlap)}"
                )


    if partition_window_counts[
        "development"
    ] != 510479:
        raise RuntimeError(
            "Development window count changed"
        )

    if partition_window_counts[
        "calibration"
    ] != 89868:
        raise RuntimeError(
            "Calibration window count changed"
        )

    if partition_window_counts[
        "final_test"
    ] != 366507:
        raise RuntimeError(
            "Final-test window count changed"
        )

    if partition_window_counts[
        "augmentation_only"
    ] != 220472:
        raise RuntimeError(
            "Augmentation-only count changed"
        )


    # The frozen historical protected-model dataset contains two
    # zero-window KFall trials.
    #
    # 106/27/1 is empty in both historical and later current processed
    # generations.
    #
    # 106/27/5 is empty in the historical protected-model generation
    # but has 22 windows in the later current processed generation.
    #
    # Both remain part of lineage and partition accounting. Neither may
    # enter model-coupled P0 evaluation because the protected historical
    # CNN has no window for them. Later current-generation windows must
    # not be substituted.
    expected_zero_window_records = [
        "106/27/1",
        "106/27/5",
    ]

    if zero_window_records != expected_zero_window_records:
        raise RuntimeError(
            "Unexpected historical zero-window trial set: "
            f"{zero_window_records}"
        )


    payload = {
        "registry_id":
            "RELIABILITY_EVAL_REGISTRY_V1",

        "status":
            "candidate_before_corruption_policy_freeze",

        "created_from": {
            "lineage_manifest":
                str(
                    LINEAGE.relative_to(
                        ROOT
                    )
                ),

            "lineage_content_sha256":
                lineage_sha,

            "lineage_tag":
                "reliability-lineage-v2",

            "lineage_tag_commit":
                tag_commit,

            "split_manifest":
                str(
                    SPLIT.relative_to(
                        ROOT
                    )
                ),
        },

        "partition_semantics": {
            "development": (
                "Historical training subjects. "
                "May be used for implementation, descriptive "
                "development analysis, and corruption-policy design."
            ),

            "calibration": (
                "Historical validation subjects. "
                "Only partition allowed for reliability threshold, "
                "persistence, and operating-point selection."
            ),

            "final_test": (
                "Historical test subjects. "
                "No integrity/OOD/fusion parameter, severity policy, "
                "or persistence rule may be selected using outcomes "
                "from this partition."
            ),

            "augmentation_only": (
                "Historical OnField training augmentation subjects "
                "999 and 1000. Excluded from reliability calibration "
                "and final testing."
            ),
        },

        "prospective_freeze_rules": {
            "corrupt_after_partitioning":
                True,

            "paired_clean_corrupt_required":
                True,

            "corruption_policy_must_be_fixed_before_final_test_generation":
                True,

            "final_test_corruption_instances_not_generated_yet":
                True,

            "final_test_outcomes_not_used_for_policy_selection":
                True,

            "thresholds_not_selected_in_this_registry":
                True,

            "severity_values_not_selected_in_this_registry":
                True,

            "persistence_not_selected_in_this_registry":
                True,

            "ood_operating_point_not_selected_in_this_registry":
                True,

            "synthetic_truth_does_not_upgrade_runtime_provenance":
                True,

            "multiple_runtime_hard_causes_remain_bitmask_capable":
                True,
        },

        "partition_trial_counts":
            dict(
                partition_trial_counts
            ),

        "partition_window_counts":
            dict(
                partition_window_counts
            ),

        "subjects_by_partition": {
            key:
                sorted(
                    value,
                    key=int,
                )
            for key, value
            in subjects_by_partition.items()
        },

        "dataset_partition_counts": [
            {
                "partition":
                    partition,

                "dataset":
                    dataset,

                "trial_count":
                    count,
            }
            for (
                partition,
                dataset,
            ), count
            in sorted(
                dataset_partition_counts.items()
            )
        ],

        "acquisition_p0_eligible_counts": [
            {
                "partition":
                    partition,

                "dataset":
                    dataset,

                "trial_count":
                    count,
            }
            for (
                partition,
                dataset,
            ), count
            in sorted(
                acquisition_eligible_counts.items()
            )
        ],

        "model_coupled_p0_eligible_counts": [
            {
                "partition":
                    partition,

                "dataset":
                    dataset,

                "trial_count":
                    count,
            }
            for (
                partition,
                dataset,
            ), count
            in sorted(
                model_coupled_eligible_counts.items()
            )
        ],

        "zero_window_trials":
            zero_window_records,

        "records":
            records,
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
    print("=" * 100)
    print("PROSPECTIVE RELIABILITY EVALUATION REGISTRY")
    print("=" * 100)

    print(
        "lineage_tag_commit =",
        tag_commit,
    )

    print(
        "lineage_content_sha256 =",
        lineage_sha,
    )

    print(
        "registry_trial_count =",
        len(
            records
        ),
    )

    print(
        "partition_trial_counts =",
        dict(
            partition_trial_counts
        ),
    )

    print(
        "partition_window_counts =",
        dict(
            partition_window_counts
        ),
    )


    print()
    print("subjects_by_partition:")

    for partition in (
        "development",
        "calibration",
        "final_test",
        "augmentation_only",
    ):
        print(
            " ",
            partition,
            "=",
            sorted(
                subjects_by_partition[
                    partition
                ],
                key=int,
            ),
        )


    print()
    print("dataset_partition_counts:")

    for (
        partition,
        dataset,
    ), count in sorted(
        dataset_partition_counts.items()
    ):
        print(
            " ",
            partition,
            dataset,
            "=",
            count,
        )


    print()
    print("acquisition_p0_eligible_counts:")

    for (
        partition,
        dataset,
    ), count in sorted(
        acquisition_eligible_counts.items()
    ):
        print(
            " ",
            partition,
            dataset,
            "=",
            count,
        )


    print()
    print("model_coupled_p0_eligible_counts:")

    for (
        partition,
        dataset,
    ), count in sorted(
        model_coupled_eligible_counts.items()
    ):
        print(
            " ",
            partition,
            dataset,
            "=",
            count,
        )


    print()
    print(
        "zero_window_trials =",
        zero_window_records,
    )

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
        "RELIABILITY_EVAL_REGISTRY_V1_PASS = True"
    )


if __name__ == "__main__":
    main()
