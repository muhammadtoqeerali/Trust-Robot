from __future__ import annotations

from collections import Counter
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import json
import subprocess

import numpy as np

from imu_reliability.injection import (
    P0CorruptionKind,
    P0InjectionSpec,
    apply_p0_injection,
)

from build_p0_development_manifest_v1 import (
    arrays_equal_or_none,
    build_spec,
    load_clean_stream,
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

DEV_RECEIPT = (
    ROOT
    / "data/manifests/"
      "p0_development_spec_receipt_v1.json"
)

OUTPUT = (
    ROOT
    / "data/manifests/"
      "p0_calibration_spec_manifest_v1_candidate.json"
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

EXPECTED_DEV_RECEIPT_SHA = (
    "d6f0f26746e80d7bd926f83bea71aaa2f714fd27a7dd73a2af021a09803c479a"
)

EXPECTED_DEV_TAG_COMMIT = (
    "bdf01cf098bcbad98e7a1eed8b30a896f38be4a5"
)

EXPECTED_CALIBRATION_COUNTS = {
    "KFALL": 314,
    "UNIVRFALL": 132,
}

EXPECTED_TRIAL_COUNT = 446
EXPECTED_ATTEMPT_COUNT = 6690


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

    policy_tag_commit = git(
        "rev-parse",
        "p0-corruption-policy-v1^{}",
    )

    if (
        policy_tag_commit
        != EXPECTED_POLICY_TAG_COMMIT
    ):
        raise RuntimeError(
            "P0 policy tag moved"
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
            "Frozen evaluation registry changed"
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


    dev_receipt = json.loads(
        DEV_RECEIPT.read_text(
            encoding="utf-8"
        )
    )

    dev_receipt_sha = verify_hash(
        dev_receipt
    )

    if (
        dev_receipt_sha
        != EXPECTED_DEV_RECEIPT_SHA
    ):
        raise RuntimeError(
            "Frozen development receipt changed"
        )


    dev_tag_commit = git(
        "rev-parse",
        "p0-development-spec-v1^{}",
    )

    if (
        dev_tag_commit
        != EXPECTED_DEV_TAG_COMMIT
    ):
        raise RuntimeError(
            "Development P0 tag moved"
        )


    if dev_receipt[
        "status"
    ] != (
        "frozen_development_spec_generation_receipt_before_calibration_generation"
    ):
        raise RuntimeError(
            "Development P0 receipt has unexpected status"
        )


    if dev_receipt[
        "freeze_contract"
    ][
        "calibration_instances_generated_here"
    ] is not False:
        raise RuntimeError(
            "Development freeze contract unexpectedly "
            "contains calibration generation"
        )


    if dev_receipt[
        "freeze_contract"
    ][
        "final_test_instances_generated_here"
    ] is not False:
        raise RuntimeError(
            "Development freeze contract unexpectedly "
            "contains final-test generation"
        )


    if policy[
        "prospective_constraints"
    ][
        "calibration_may_modify_policy"
    ] is not False:
        raise RuntimeError(
            "Frozen policy allows calibration modification"
        )


    if policy[
        "prospective_constraints"
    ][
        "final_test_may_modify_policy"
    ] is not False:
        raise RuntimeError(
            "Frozen policy allows final-test modification"
        )


    if tuple(
        policy["severity_order"]
    ) != SEVERITY_ORDER:
        raise RuntimeError(
            "Severity ordering changed"
        )

    if set(
        policy["families"]
    ) != set(
        FAMILY_ORDER
    ):
        raise RuntimeError(
            "P0 family set changed"
        )


    selected = [
        row
        for row in registry[
            "records"
        ]
        if (
            row["partition"]
            == "calibration"
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


    if len(
        selected
    ) != EXPECTED_TRIAL_COUNT:
        raise RuntimeError(
            "Unexpected calibration acquisition "
            f"trial count: {len(selected)}"
        )


    dataset_counts = Counter(
        row["dataset"]
        for row in selected
    )

    if dict(
        dataset_counts
    ) != EXPECTED_CALIBRATION_COUNTS:
        raise RuntimeError(
            "Unexpected calibration dataset counts: "
            f"{dict(dataset_counts)}"
        )


    for row in selected:
        constraints = row[
            "prospective_constraints"
        ]

        if constraints[
            "may_define_corruption_policy"
        ] is not False:
            raise RuntimeError(
                "Calibration record may define policy: "
                f"{row['trial_id']}"
            )

        if constraints[
            "may_tune_detector_thresholds"
        ] is not True:
            raise RuntimeError(
                "Calibration record missing threshold "
                f"permission: {row['trial_id']}"
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


    trials = []
    attempts = []

    status_counts = Counter()
    reason_counts = Counter()

    raw_files_opened = 0
    model_coupled_count = 0


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

        if model_coupled:
            model_coupled_count += 1


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


                built, reason, rejected = (
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
                        "calibration",

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
                            rejected,
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
                        "Frozen admissibility implementation "
                        "disagreed with tested injector for "
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
                        "Injector produced no-op fingerprint: "
                        f"{trial_id} "
                        f"{family} "
                        f"{severity}"
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

                    clean_boundary = (
                        clean.timestamps[start]
                        - clean.timestamps[
                            start - 1
                        ]
                    )

                    corrupt_boundary = (
                        pair.corrupt.timestamps[
                            start
                        ]
                        - pair.corrupt.timestamps[
                            start - 1
                        ]
                    )

                    observed_extra_ms = (
                        (
                            corrupt_boundary
                            - clean_boundary
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
                            "Timing-unit conversion mismatch: "
                            f"{trial_id}: "
                            f"observed="
                            f"{observed_extra_ms} ms; "
                            f"expected="
                            f"{expected_extra_ms} ms"
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
            trial_number % 50
        ) == 0:
            print(
                f"processed "
                f"{trial_number}/"
                f"{len(selected)} "
                f"calibration trials",
                flush=True,
            )


    if len(
        attempts
    ) != EXPECTED_ATTEMPT_COUNT:
        raise RuntimeError(
            "Calibration attempt-count mismatch: "
            f"{len(attempts)}"
        )


    if raw_files_opened != EXPECTED_TRIAL_COUNT:
        raise RuntimeError(
            "Unexpected calibration raw-file count"
        )


    if model_coupled_count != EXPECTED_TRIAL_COUNT:
        raise RuntimeError(
            "Unexpected model-coupled calibration "
            f"count: {model_coupled_count}"
        )


    payload = {
        "manifest_id":
            "P0_CALIBRATION_SPEC_MANIFEST_V1",

        "status":
            "candidate_before_calibration_spec_receipt_freeze",

        "partition":
            "calibration",

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
                policy_tag_commit,
        },

        "source_development_receipt": {
            "path":
                str(
                    DEV_RECEIPT.relative_to(
                        ROOT
                    )
                ),

            "content_sha256":
                dev_receipt_sha,

            "tag":
                "p0-development-spec-v1",

            "tag_commit":
                dev_tag_commit,
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
            "calibration_trials_only":
                True,

            "development_raw_files_opened":
                0,

            "calibration_raw_files_opened":
                raw_files_opened,

            "final_test_raw_files_opened":
                0,

            "corruption_policy_already_frozen":
                True,

            "corruption_policy_modified":
                False,

            "severity_grid_modified":
                False,

            "placement_rules_modified":
                False,

            "seed_derivation_modified":
                False,

            "admissibility_rules_modified":
                False,

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

            "selection_implementation_reused_from_development_generator":
                True,

            "timing_offset_converted_to_raw_timestamp_units":
                True,

            "detector_thresholds_selected_during_generation":
                False,

            "persistence_selected_during_generation":
                False,

            "ood_operating_point_selected_during_generation":
                False,

            "task_or_detector_outcomes_evaluated_during_generation":
                False,
        },

        "calibration_trial_count":
            len(
                trials
            ),

        "model_coupled_trial_count":
            model_coupled_count,

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


    OUTPUT.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


    admissible_total = sum(
        value
        for (
            dataset,
            family,
            severity,
            status,
        ), value
        in status_counts.items()
        if status == "ADMISSIBLE"
    )

    rejected_total = (
        EXPECTED_ATTEMPT_COUNT
        - admissible_total
    )


    print()
    print("=" * 108)
    print(
        "P0 CALIBRATION SPECIFICATION SUMMARY"
    )
    print("=" * 108)

    print(
        "calibration_trial_count =",
        len(
            trials
        ),
    )

    print(
        "model_coupled_trial_count =",
        model_coupled_count,
    )

    print(
        "attempt_count =",
        len(
            attempts
        ),
    )

    print(
        "admissible_count =",
        admissible_total,
    )

    print(
        "not_admissible_count =",
        rejected_total,
    )

    print(
        "dataset_trial_counts =",
        dict(
            dataset_counts
        ),
    )

    print(
        "development_raw_files_opened = 0"
    )

    print(
        "calibration_raw_files_opened =",
        raw_files_opened,
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
    print(
        "not_admissible_reason_counts:"
    )

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
        "P0_CALIBRATION_SPEC_MANIFEST_V1_CANDIDATE_PASS = True"
    )


if __name__ == "__main__":
    main()
