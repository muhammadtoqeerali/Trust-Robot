from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from collections import Counter, defaultdict
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(
    __file__
).resolve().parents[2]

SRC = (
    ROOT
    / "src"
)

EXPERIMENT_DIR = (
    ROOT
    / "experiments/01_integrity_p0"
)

for import_root in (
    SRC,
    EXPERIMENT_DIR,
):
    value = str(
        import_root
    )

    if value not in sys.path:
        sys.path.insert(
            0,
            value,
        )


CALIBRATION_EVALUATOR = (
    ROOT
    / "experiments/01_integrity_p0/"
      "evaluate_integrity_calibration_v1.py"
)

FINAL_MANIFEST_PATH = (
    ROOT
    / "data/manifests/"
      "p0_final_test_spec_manifest_v1_candidate.json"
)

FINAL_RECEIPT_PATH = (
    ROOT
    / "data/manifests/"
      "p0_final_test_spec_receipt_v1.json"
)

OPERATING_POINT_PATH = (
    ROOT
    / "configs/integrity/"
      "integrity_operating_point_v1.json"
)

PROTOCOL_PATH = (
    ROOT
    / "configs/integrity/"
      "integrity_calibration_protocol_v1.json"
)

POLICY_PATH = (
    ROOT
    / "configs/integrity/"
      "p0_corruption_policy_v1.json"
)

RESULT_PATH = (
    ROOT
    / "results/raw/"
      "integrity_final_test_v1_candidate.json"
)


EXPECTED_FINAL_SPEC_COMMIT = (
    "d9d6e0a7c1799f67499f2847604aa3968146683e"
)

EXPECTED_FINAL_MANIFEST_CONTENT_SHA256 = (
    "f29298997e3bc99698d6206ebd5d7a9e3f987f2f93da61f199313f37bb580546"
)

EXPECTED_FINAL_MANIFEST_RAW_SHA256 = (
    "b56a41c5603036661dfcea39df9e7712c7d4a2e875aaf1d82f63256b3fcd8717"
)

EXPECTED_FINAL_RECEIPT_CONTENT_SHA256 = (
    "39623c0c1db9e3b413de35dc272714e520b60ba69820530e051feb7746e098bf"
)

EXPECTED_FINAL_RECEIPT_RAW_SHA256 = (
    "5a07707c6ff277915c2706915724e9a8a76e0bd91d1ded224f1c8845aa357778"
)

EXPECTED_OPERATING_POINT_COMMIT = (
    "9ac878ea6a40e8c01a60e42e602a1fa9fc688d3b"
)

EXPECTED_OPERATING_POINT_CONTENT_SHA256 = (
    "02c7d6dabb5951409dd34491384fc2a800ef02a7b1ad0006098845925d847f59"
)

EXPECTED_CALIBRATION_EVALUATOR_COMMIT = (
    "dc948845a8d172f30755791d49419a3c445e31fe"
)

EXPECTED_PROTOCOL_CONTENT_SHA256 = (
    "ef912fe988d58e3ec86a9413298eec2491ff3186199462a285a558aefcebe806"
)

EXPECTED_POLICY_CONTENT_SHA256 = (
    "cb33c32951930453db550dfd02deab67a9eb51e851edf1a186e7faa4a5432220"
)

EXPECTED_TRIAL_COUNT = 1108
EXPECTED_ATTEMPT_COUNT = 16620
EXPECTED_ADMISSIBLE_COUNT = 15806
EXPECTED_NOT_ADMISSIBLE_COUNT = 814

SUPPORTED_DATASETS = (
    "KFALL",
    "UNIVRFALL",
)

SEVERITIES = (
    "low",
    "medium",
    "high",
)

FINAL_EVALUATOR_TAG = (
    "integrity-final-test-evaluator-v1"
)


CALIBRATION_RUNTIME_DEPENDENCIES = (
    "experiments/01_integrity_p0/evaluate_integrity_calibration_v1.py",
    "experiments/01_integrity_p0/build_p0_development_manifest_v1.py",
    "experiments/01_integrity_p0/derive_p0_dev_policy_inputs_v1.py",
    "src/imu_reliability/integrity/evidence.py",
    "src/imu_reliability/integrity/flatness.py",
    "src/imu_reliability/integrity/frame_gap.py",
    "src/imu_reliability/integrity/monitor.py",
    "src/imu_reliability/integrity/timing.py",
    "src/imu_reliability/injection/evidence_bridge.py",
    "src/imu_reliability/injection/p0.py",
    "src/imu_reliability/injection/types.py",
)


def canonical_json(
    payload: Any,
) -> str:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def canonical_digest(
    payload: Any,
) -> str:
    return sha256(
        canonical_json(
            payload
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def artifact_content_digest(
    payload: Any,
) -> str:
    normalized = json.loads(
        json.dumps(
            payload,
            separators=(",", ":"),
            allow_nan=False,
        )
    )

    return canonical_digest(
        normalized
    )


def file_sha256(
    path: Path,
) -> str:
    return sha256(
        path.read_bytes()
    ).hexdigest()


def git(
    *args: str,
) -> str:
    return subprocess.check_output(
        [
            "git",
            *args,
        ],
        cwd=ROOT,
        text=True,
    ).strip()


def load_json(
    path: Path,
) -> dict[str, Any]:
    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def verify_content_hash(
    data: dict[str, Any],
    *,
    expected: str,
) -> str:
    payload = deepcopy(
        data
    )

    stored = payload.pop(
        "content_sha256"
    )

    computed = canonical_digest(
        payload
    )

    if stored != computed:
        raise RuntimeError(
            "Canonical content hash mismatch: "
            f"{stored} != {computed}"
        )

    if stored != expected:
        raise RuntimeError(
            "Unexpected frozen content hash: "
            f"{stored} != {expected}"
        )

    return stored


def verify_preimport_calibration_dependencies():
    tag_commit = git(
        "rev-parse",
        "integrity-calibration-evaluator-v1-hashfix^{commit}",
    )

    if (
        tag_commit
        != EXPECTED_CALIBRATION_EVALUATOR_COMMIT
    ):
        raise RuntimeError(
            "Calibration evaluator hash-fix tag moved"
        )

    diff = subprocess.run(
        [
            "git",
            "diff",
            "--quiet",
            EXPECTED_CALIBRATION_EVALUATOR_COMMIT,
            "HEAD",
            "--",
            *CALIBRATION_RUNTIME_DEPENDENCIES,
        ],
        cwd=ROOT,
        check=False,
    )

    if diff.returncode != 0:
        raise RuntimeError(
            "Calibration-era evaluation primitives changed "
            "after their frozen evaluator epoch"
        )

    status = subprocess.check_output(
        [
            "git",
            "status",
            "--porcelain",
            "--",
            *CALIBRATION_RUNTIME_DEPENDENCIES,
        ],
        cwd=ROOT,
        text=True,
    )

    if status.strip():
        raise RuntimeError(
            "Calibration-era evaluation dependency worktree "
            "is dirty: "
            + status.strip()
        )

    return {
        "tag":
            "integrity-calibration-evaluator-v1-hashfix",

        "tag_commit":
            tag_commit,

        "runtime_dependencies_identical_to_hashfix_epoch":
            True,

        "runtime_dependency_raw_sha256": {
            rel:
                file_sha256(
                    ROOT
                    / rel
                )
            for rel
            in CALIBRATION_RUNTIME_DEPENDENCIES
        },
    }


PREIMPORT_CALIBRATION_DEPENDENCY_ANCHORS = (
    verify_preimport_calibration_dependencies()
)


def load_calibration_evaluator():
    spec = (
        importlib.util
        .spec_from_file_location(
            "_integrity_calibration_v1_frozen_for_final",
            CALIBRATION_EVALUATOR,
        )
    )

    if (
        spec is None
        or spec.loader is None
    ):
        raise RuntimeError(
            "Unable to import frozen calibration evaluator"
        )

    module = (
        importlib.util
        .module_from_spec(
            spec
        )
    )

    sys.modules[
        spec.name
    ] = module

    spec.loader.exec_module(
        module
    )

    return module


CAL = load_calibration_evaluator()


def verify_final_manifest_boundary(
    manifest: dict[str, Any],
    receipt: dict[str, Any],
) -> None:
    if (
        manifest.get(
            "partition"
        )
        != "final_test"
    ):
        raise RuntimeError(
            "Evaluator accepts final-test manifest only"
        )

    if (
        manifest[
            "final_test_trial_count"
        ]
        != EXPECTED_TRIAL_COUNT
    ):
        raise RuntimeError(
            "Unexpected final-test trial count"
        )

    if (
        manifest[
            "attempt_count"
        ]
        != EXPECTED_ATTEMPT_COUNT
    ):
        raise RuntimeError(
            "Unexpected final-test attempt count"
        )

    trials = manifest[
        "trials"
    ]

    if len(
        trials
    ) != EXPECTED_TRIAL_COUNT:
        raise RuntimeError(
            "Final-test trial list length mismatch"
        )

    trial_ids = {
        row[
            "trial_id"
        ]
        for row in trials
    }

    if len(
        trial_ids
    ) != EXPECTED_TRIAL_COUNT:
        raise RuntimeError(
            "Duplicate final-test trial IDs"
        )

    dataset_counts = Counter(
        row[
            "dataset"
        ]
        for row in trials
    )

    if dataset_counts != Counter(
        {
            "KFALL":
                932,
            "UNIVRFALL":
                176,
        }
    ):
        raise RuntimeError(
            "Unexpected final-test dataset counts"
        )

    attempts = manifest[
        "attempts"
    ]

    if len(
        attempts
    ) != EXPECTED_ATTEMPT_COUNT:
        raise RuntimeError(
            "Final-test attempt list length mismatch"
        )

    status_counts = Counter(
        row[
            "status"
        ]
        for row in attempts
    )

    if status_counts != Counter(
        {
            "ADMISSIBLE":
                EXPECTED_ADMISSIBLE_COUNT,
            "NOT_ADMISSIBLE":
                EXPECTED_NOT_ADMISSIBLE_COUNT,
        }
    ):
        raise RuntimeError(
            "Final-test admissibility accounting changed"
        )

    for row in attempts:
        if (
            row[
                "partition"
            ]
            != "final_test"
        ):
            raise RuntimeError(
                "Non-final-test attempt encountered"
            )

        if (
            row[
                "trial_id"
            ]
            not in trial_ids
        ):
            raise RuntimeError(
                "Attempt references unknown final-test trial"
            )

    if (
        receipt[
            "source_manifest"
        ][
            "content_sha256"
        ]
        != EXPECTED_FINAL_MANIFEST_CONTENT_SHA256
    ):
        raise RuntimeError(
            "Final receipt does not anchor final manifest"
        )

    if (
        receipt[
            "attempt_accounting"
        ][
            "admissible_count"
        ]
        != EXPECTED_ADMISSIBLE_COUNT
    ):
        raise RuntimeError(
            "Final receipt admissible count changed"
        )

    boundary = receipt[
        "generation_boundary"
    ]

    if (
        boundary[
            "detector_outcomes_evaluated"
        ]
        is not False
    ):
        raise RuntimeError(
            "Final detector outcomes were already evaluated "
            "before final evaluator freeze"
        )

    if (
        boundary[
            "final_test_outcomes_used_for_tuning"
        ]
        is not False
    ):
        raise RuntimeError(
            "Final-test outcomes were used for tuning"
        )

    if (
        boundary[
            "integrity_operating_point_modified"
        ]
        is not False
    ):
        raise RuntimeError(
            "Integrity operating point changed"
        )


def verify_operating_point(
    operating_point: dict[str, Any],
) -> None:
    if (
        operating_point[
            "scope"
        ]
        != "historical_p0_v1"
    ):
        raise RuntimeError(
            "Unexpected operating-point scope"
        )

    if (
        operating_point[
            "FRAME_GAP"
        ][
            "KFALL"
        ][
            "enabled"
        ]
        is not True
    ):
        raise RuntimeError(
            "KFall FRAME_GAP no longer enabled"
        )

    if (
        operating_point[
            "FRAME_GAP"
        ][
            "KFALL"
        ][
            "enters_hard_cause_set"
        ]
        is not True
    ):
        raise RuntimeError(
            "KFall FRAME_GAP no longer hard-qualified"
        )

    if (
        operating_point[
            "FRAME_GAP"
        ][
            "UNIVRFALL"
        ][
            "hard_detection_enabled"
        ]
        is not False
    ):
        raise RuntimeError(
            "UniVR FRAME_GAP hard detection unexpectedly enabled"
        )

    freeze = operating_point[
        "CHANNEL_FREEZE_SUSPECT"
    ]

    if freeze[
        "enabled"
    ] is not False:
        raise RuntimeError(
            "CHANNEL_FREEZE_SUSPECT was re-enabled"
        )

    if freeze[
        "enters_hard_cause_set"
    ] is not False:
        raise RuntimeError(
            "CHANNEL_FREEZE entered hard cause set"
        )

    expected_timing = {
        "KFALL": (
            5.0,
            15.0,
            1000.0,
        ),
        "UNIVRFALL": (
            -0.5,
            20.5,
            1.0,
        ),
    }

    for dataset, expected in expected_timing.items():
        row = operating_point[
            "TIMING_OBSERVATION_ENVELOPE"
        ][dataset]

        observed = (
            float(
                row[
                    "minimum_delta_ms"
                ]
            ),
            float(
                row[
                    "maximum_delta_ms"
                ]
            ),
            float(
                row[
                    "timestamp_scale_to_ms"
                ]
            ),
        )

        if observed != expected:
            raise RuntimeError(
                f"Frozen timing operating point changed for "
                f"{dataset}: {observed}"
            )

        if (
            row[
                "runtime_role"
            ]
            != "OBSERVATION_ONLY"
        ):
            raise RuntimeError(
                "Timing runtime role changed"
            )

        if (
            row[
                "hard_cause_promotion"
            ]
            is not False
        ):
            raise RuntimeError(
                "Timing hard promotion unexpectedly enabled"
            )

    supported = (
        operating_point[
            "hard_cause_set_contract"
        ][
            "historical_p0_v1_supported_external_causes"
        ]
    )

    if supported != [
        "FRAME_GAP"
    ]:
        raise RuntimeError(
            "Historical hard-cause set changed"
        )


def verify_frozen_anchors(
    manifest,
    receipt,
    operating_point,
    protocol,
    policy,
):
    hashes = {
        "final_manifest":
            verify_content_hash(
                manifest,
                expected=
                    EXPECTED_FINAL_MANIFEST_CONTENT_SHA256,
            ),

        "final_receipt":
            verify_content_hash(
                receipt,
                expected=
                    EXPECTED_FINAL_RECEIPT_CONTENT_SHA256,
            ),

        "operating_point":
            verify_content_hash(
                operating_point,
                expected=
                    EXPECTED_OPERATING_POINT_CONTENT_SHA256,
            ),

        "protocol":
            verify_content_hash(
                protocol,
                expected=
                    EXPECTED_PROTOCOL_CONTENT_SHA256,
            ),

        "policy":
            verify_content_hash(
                policy,
                expected=
                    EXPECTED_POLICY_CONTENT_SHA256,
            ),
    }

    if (
        file_sha256(
            FINAL_MANIFEST_PATH
        )
        != EXPECTED_FINAL_MANIFEST_RAW_SHA256
    ):
        raise RuntimeError(
            "Final manifest raw-file hash changed"
        )

    if (
        file_sha256(
            FINAL_RECEIPT_PATH
        )
        != EXPECTED_FINAL_RECEIPT_RAW_SHA256
    ):
        raise RuntimeError(
            "Final receipt raw-file hash changed"
        )

    if (
        git(
            "rev-parse",
            "p0-final-test-spec-v1^{commit}",
        )
        != EXPECTED_FINAL_SPEC_COMMIT
    ):
        raise RuntimeError(
            "Final-test specification tag moved"
        )

    if (
        git(
            "rev-parse",
            "integrity-operating-point-v1^{commit}",
        )
        != EXPECTED_OPERATING_POINT_COMMIT
    ):
        raise RuntimeError(
            "Integrity operating-point tag moved"
        )

    for ancestor in (
        EXPECTED_FINAL_SPEC_COMMIT,
        EXPECTED_OPERATING_POINT_COMMIT,
        EXPECTED_CALIBRATION_EVALUATOR_COMMIT,
    ):
        rc = subprocess.run(
            [
                "git",
                "merge-base",
                "--is-ancestor",
                ancestor,
                "HEAD",
            ],
            cwd=ROOT,
            check=False,
        ).returncode

        if rc != 0:
            raise RuntimeError(
                "Frozen ancestor missing from HEAD: "
                + ancestor
            )

    verify_final_manifest_boundary(
        manifest,
        receipt,
    )

    verify_operating_point(
        operating_point
    )

    return {
        "canonical_content_sha256":
            hashes,

        "raw_file_sha256": {
            "final_manifest":
                file_sha256(
                    FINAL_MANIFEST_PATH
                ),

            "final_receipt":
                file_sha256(
                    FINAL_RECEIPT_PATH
                ),

            "operating_point":
                file_sha256(
                    OPERATING_POINT_PATH
                ),

            "protocol":
                file_sha256(
                    PROTOCOL_PATH
                ),

            "policy":
                file_sha256(
                    POLICY_PATH
                ),
        },

        "final_test_spec_tag":
            "p0-final-test-spec-v1",

        "final_test_spec_tag_commit":
            EXPECTED_FINAL_SPEC_COMMIT,

        "operating_point_tag":
            "integrity-operating-point-v1",

        "operating_point_tag_commit":
            EXPECTED_OPERATING_POINT_COMMIT,

        "calibration_runtime_dependency_anchor":
            PREIMPORT_CALIBRATION_DEPENDENCY_ANCHORS,
    }


def verify_evaluator_is_frozen() -> str:
    tag_commit = git(
        "rev-parse",
        f"{FINAL_EVALUATOR_TAG}^{{commit}}",
    )

    script_commit = git(
        "log",
        "-1",
        "--format=%H",
        "--",
        str(
            Path(
                __file__
            ).relative_to(
                ROOT
            )
        ),
    )

    current_head = git(
        "rev-parse",
        "HEAD",
    )

    if (
        tag_commit
        != script_commit
    ):
        raise RuntimeError(
            "Final evaluator source differs from frozen tag"
        )

    if (
        current_head
        != tag_commit
    ):
        raise RuntimeError(
            "First final-test evaluator execution requires "
            "HEAD exactly at the frozen evaluator tag"
        )

    return tag_commit


def selected_timing_bounds(
    operating_point,
    dataset: str,
):
    row = (
        operating_point[
            "TIMING_OBSERVATION_ENVELOPE"
        ][dataset]
    )

    return (
        float(
            row[
                "minimum_delta_ms"
            ]
        ),
        float(
            row[
                "maximum_delta_ms"
            ]
        ),
    )


def evaluate_frozen_timing_observation(
    stream,
    dataset: str,
    *,
    anchor_index: int,
    operating_point,
    protocol,
):
    minimum_delta_ms, maximum_delta_ms = (
        selected_timing_bounds(
            operating_point,
            dataset,
        )
    )

    timestamps_ms = CAL.timestamps_to_ms(
        stream,
        dataset,
        protocol,
    )

    anchor = int(
        anchor_index
    )

    if (
        anchor <= 0
        or anchor >= timestamps_ms.size
    ):
        raise ValueError(
            "Timing anchor must be an internal boundary"
        )

    envelope = CAL.TimingEnvelope(
        minimum_delta=
            minimum_delta_ms,

        maximum_delta=
            maximum_delta_ms,

        unit="ms",

        frozen=True,
    )

    evidence = CAL.evaluate_timing_envelope(
        timestamps_ms[
            anchor - 1
        ],
        timestamps_ms[
            anchor
        ],
        envelope=envelope,
        timestamp_provenance_qualified=False,
        source=(
            "HISTORICAL_P0_FINAL_TEST::"
            + dataset
        ),
    )

    if evidence is not None:
        if (
            evidence.status
            is not CAL.EvidenceStatus.OBSERVATION_ONLY
        ):
            raise RuntimeError(
                "Frozen timing envelope was promoted above "
                "observation-only"
            )

        if CAL.assess_evidence(
            [
                evidence
            ]
        ).has_hard_alert:
            raise RuntimeError(
                "Frozen timing observation entered hard cause set"
            )

    return evidence


def inactive_event_summary(
    episode_count: int,
    *,
    runtime_role: str,
    reason: str,
):
    return {
        "episode_count":
            int(
                episode_count
            ),

        "detected_count":
            0,

        "event_detection_recall":
            None,

        "confirmation_latency_samples":
            [],

        "confirmation_latency_ms":
            [],

        "median_confirmation_latency_samples":
            None,

        "median_confirmation_latency_ms":
            None,

        "runtime_active":
            False,

        "runtime_role":
            runtime_role,

        "reason":
            reason,
    }


def load_clean_final_test_streams(
    manifest,
    policy,
):
    streams, load_audit = (
        CAL.load_clean_calibration_streams(
            manifest,
            policy,
        )
    )

    if len(
        streams
    ) != EXPECTED_TRIAL_COUNT:
        raise RuntimeError(
            "Unexpected final-test clean stream count"
        )

    if len(
        load_audit
    ) != EXPECTED_TRIAL_COUNT:
        raise RuntimeError(
            "Unexpected final-test raw-file load count"
        )

    dataset_counts = Counter(
        row[
            "dataset"
        ]
        for row in load_audit
    )

    if dataset_counts != Counter(
        {
            "KFALL":
                932,

            "UNIVRFALL":
                176,
        }
    ):
        raise RuntimeError(
            "Unexpected loaded final-test dataset counts"
        )

    return streams, load_audit


def evaluate_clean_fixed_operating_point(
    streams,
    operating_point,
    protocol,
):
    accumulator = {
        dataset: {
            "trial_count":
                0,

            "hours_observed":
                0.0,

            "hard_alert_count":
                0,

            "timing_outside_interval_count":
                0,

            "trials_with_any_timing_outside":
                0,
        }
        for dataset
        in SUPPORTED_DATASETS
    }

    for record in streams.values():
        dataset = record[
            "dataset"
        ]

        stream = record[
            "stream"
        ]

        hours = CAL.observed_hours(
            stream,
            dataset,
            protocol,
        )

        row = accumulator[
            dataset
        ]

        row[
            "trial_count"
        ] += 1

        row[
            "hours_observed"
        ] += hours

        row[
            "hard_alert_count"
        ] += (
            CAL.clean_frame_gap_hard_alert_count(
                dataset,
                stream,
            )
        )

        minimum_delta_ms, maximum_delta_ms = (
            selected_timing_bounds(
                operating_point,
                dataset,
            )
        )

        outside = CAL.timing_outside_mask(
            stream,
            dataset,
            minimum_delta_ms=
                minimum_delta_ms,
            maximum_delta_ms=
                maximum_delta_ms,
            protocol=protocol,
        )

        outside_count = int(
            np.count_nonzero(
                outside
            )
        )

        row[
            "timing_outside_interval_count"
        ] += outside_count

        if outside_count:
            row[
                "trials_with_any_timing_outside"
            ] += 1

    output = {}

    for dataset, row in accumulator.items():
        hours = row[
            "hours_observed"
        ]

        trials = row[
            "trial_count"
        ]

        output[
            dataset
        ] = {
            "trial_count":
                trials,

            "hours_observed":
                hours,

            "hard_alert_count":
                row[
                    "hard_alert_count"
                ],

            "hard_alerts_per_hour":
                (
                    row[
                        "hard_alert_count"
                    ]
                    / hours
                    if hours > 0
                    else None
                ),

            "timing_observation_envelope": {
                "minimum_delta_ms":
                    selected_timing_bounds(
                        operating_point,
                        dataset,
                    )[0],

                "maximum_delta_ms":
                    selected_timing_bounds(
                        operating_point,
                        dataset,
                    )[1],

                "runtime_role":
                    "OBSERVATION_ONLY",

                "hard_cause_promotion":
                    False,

                "outside_interval_count":
                    row[
                        "timing_outside_interval_count"
                    ],

                "outside_intervals_per_hour":
                    (
                        row[
                            "timing_outside_interval_count"
                        ]
                        / hours
                        if hours > 0
                        else None
                    ),

                "fraction_trials_with_any_outside_interval":
                    (
                        row[
                            "trials_with_any_timing_outside"
                        ]
                        / trials
                        if trials > 0
                        else None
                    ),
            },

            "channel_freeze_suspect": {
                "runtime_active":
                    False,

                "runtime_role":
                    "DISABLED_BY_FROZEN_OPERATING_POINT",

                "events_evaluated":
                    False,
            },
        }

    return output


def evaluate_final_corruptions(
    streams,
    manifest,
    operating_point,
    protocol,
):
    frame_gap_events = defaultdict(
        CAL.empty_event_bucket
    )

    timing_events = defaultdict(
        CAL.empty_event_bucket
    )

    inactive_counts = defaultdict(
        int
    )

    status_counts = defaultdict(
        int
    )

    rejection_counts = defaultdict(
        int
    )

    regenerated_pairs = 0

    attempts_by_trial = defaultdict(
        list
    )

    for attempt in manifest[
        "attempts"
    ]:
        attempts_by_trial[
            attempt[
                "trial_id"
            ]
        ].append(
            attempt
        )

    for trial_id, attempts in attempts_by_trial.items():
        record = streams[
            trial_id
        ]

        dataset = record[
            "dataset"
        ]

        clean = record[
            "stream"
        ]

        for attempt in attempts:
            family = attempt[
                "family"
            ]

            severity = attempt[
                "severity"
            ]

            status = attempt[
                "status"
            ]

            status_counts[
                (
                    dataset,
                    family,
                    severity,
                    status,
                )
            ] += 1

            if status != "ADMISSIBLE":
                rejection_counts[
                    (
                        dataset,
                        family,
                        severity,
                        attempt[
                            "reason"
                        ],
                    )
                ] += 1

                continue

            pair = CAL.regenerate_pair(
                clean,
                attempt,
            )

            regenerated_pairs += 1

            truth = pair.truths[
                0
            ]

            if family == "FRAME_GAP":
                result = CAL.evaluate_frame_gap_event(
                    dataset,
                    pair.corrupt,
                    corrupt_anchor_index=
                        truth.corrupt_anchor_index,
                )

                CAL.add_event(
                    frame_gap_events[
                        (
                            dataset,
                            severity,
                        )
                    ],
                    detected=
                        result[
                            "detected"
                        ],
                    latency_samples=(
                        0
                        if result[
                            "detected"
                        ]
                        else None
                    ),
                    latency_ms=(
                        0.0
                        if result[
                            "detected"
                        ]
                        else None
                    ),
                )

            elif family == "TIMING_PERTURBATION":
                evidence = (
                    evaluate_frozen_timing_observation(
                        pair.corrupt,
                        dataset,
                        anchor_index=
                            truth.corrupt_anchor_index,
                        operating_point=
                            operating_point,
                        protocol=
                            protocol,
                    )
                )

                detected = (
                    evidence is not None
                )

                CAL.add_event(
                    timing_events[
                        (
                            dataset,
                            severity,
                        )
                    ],
                    detected=
                        detected,
                    latency_samples=(
                        0
                        if detected
                        else None
                    ),
                    latency_ms=(
                        0.0
                        if detected
                        else None
                    ),
                )

            elif family == "CHANNEL_FREEZE":
                inactive_counts[
                    (
                        family,
                        dataset,
                        severity,
                    )
                ] += 1

            elif family in (
                "FRAME_REPEAT",
                "RANGE_CLIP",
            ):
                inactive_counts[
                    (
                        family,
                        dataset,
                        severity,
                    )
                ] += 1

            else:
                raise RuntimeError(
                    "Unexpected P0 family: "
                    + family
                )

    if (
        regenerated_pairs
        != EXPECTED_ADMISSIBLE_COUNT
    ):
        raise RuntimeError(
            "Regenerated admissible-pair count mismatch"
        )

    frame_gap_summary = {}

    for dataset in SUPPORTED_DATASETS:
        frame_gap_summary[
            dataset
        ] = {}

        for severity in SEVERITIES:
            metrics = CAL.finalize_event_bucket(
                frame_gap_events[
                    (
                        dataset,
                        severity,
                    )
                ]
            )

            if dataset == "KFALL":
                metrics.update(
                    {
                        "runtime_role":
                            "HARD_QUALIFIED",

                        "enters_hard_cause_set":
                            True,

                        "counter_provenance":
                            "QUALIFIED_DIRECT_RAW_FRAMECOUNTER",
                    }
                )

            else:
                metrics.update(
                    {
                        "runtime_role":
                            "NO_HARD_DETECTION",

                        "enters_hard_cause_set":
                            False,

                        "counter_provenance":
                            "UNVERIFIED_OR_ABSENT_DIRECT_COUNTER",
                    }
                )

            frame_gap_summary[
                dataset
            ][severity] = metrics

    timing_summary = {}

    for dataset in SUPPORTED_DATASETS:
        minimum_delta_ms, maximum_delta_ms = (
            selected_timing_bounds(
                operating_point,
                dataset,
            )
        )

        timing_summary[
            dataset
        ] = {
            "minimum_delta_ms":
                minimum_delta_ms,

            "maximum_delta_ms":
                maximum_delta_ms,

            "runtime_role":
                "OBSERVATION_ONLY",

            "hard_cause_promotion":
                False,

            "by_severity": {
                severity:
                    CAL.finalize_event_bucket(
                        timing_events[
                            (
                                dataset,
                                severity,
                            )
                        ]
                    )
                for severity
                in SEVERITIES
            },
        }

    channel_freeze_summary = {
        "enabled":
            False,

        "runtime_role":
            "DISABLED_BY_FROZEN_OPERATING_POINT",

        "enters_hard_cause_set":
            False,

        "selection_reopened":
            False,

        "by_dataset": {
            dataset: {
                severity:
                    inactive_event_summary(
                        inactive_counts[
                            (
                                "CHANNEL_FREEZE",
                                dataset,
                                severity,
                            )
                        ],
                        runtime_role=
                            "DISABLED_BY_FROZEN_OPERATING_POINT",
                        reason=
                            "NO_FROZEN_CALIBRATION_CANDIDATE_MET_ALL_CLEAN_CONSTRAINTS",
                    )
                for severity
                in SEVERITIES
            }
            for dataset
            in SUPPORTED_DATASETS
        },
    }

    unsupported = {}

    for family, reason in (
        (
            "FRAME_REPEAT",
            "NO_HARD_CAUSE_IN_HISTORICAL_P0_V1",
        ),
        (
            "RANGE_CLIP",
            "PHYSICAL_RAIL_NOT_VERIFIED_NO_HARD_CAUSE_CONFIGURED",
        ),
    ):
        unsupported[
            family
        ] = {
            "runtime_role":
                "NO_HARD_DETECTOR_CONFIGURED",

            "enters_hard_cause_set":
                False,

            "by_dataset": {
                dataset: {
                    severity:
                        inactive_event_summary(
                            inactive_counts[
                                (
                                    family,
                                    dataset,
                                    severity,
                                )
                            ],
                            runtime_role=
                                "NO_HARD_DETECTOR_CONFIGURED",
                            reason=
                                reason,
                        )
                    for severity
                    in SEVERITIES
                }
                for dataset
                in SUPPORTED_DATASETS
            },
        }

    return {
        "frame_gap":
            frame_gap_summary,

        "timing_observation":
            timing_summary,

        "channel_freeze_suspect":
            channel_freeze_summary,

        "unsupported_hard_cause_families":
            unsupported,

        "attempt_status_counts": [
            {
                "dataset":
                    key[
                        0
                    ],

                "family":
                    key[
                        1
                    ],

                "severity":
                    key[
                        2
                    ],

                "status":
                    key[
                        3
                    ],

                "count":
                    value,
            }
            for key, value
            in sorted(
                status_counts.items()
            )
        ],

        "not_admissible_counts": [
            {
                "dataset":
                    key[
                        0
                    ],

                "family":
                    key[
                        1
                    ],

                "severity":
                    key[
                        2
                    ],

                "reason":
                    key[
                        3
                    ],

                "count":
                    value,
            }
            for key, value
            in sorted(
                rejection_counts.items()
            )
        ],

        "regenerated_admissible_pair_count":
            regenerated_pairs,

        "unsupported_cause_emission_count":
            0,
    }


def build_attribution(
    corrupt_metrics,
):
    kfall = corrupt_metrics[
        "frame_gap"
    ][
        "KFALL"
    ]

    denominator = sum(
        int(
            kfall[
                severity
            ][
                "episode_count"
            ]
        )
        for severity
        in SEVERITIES
    )

    detected = sum(
        int(
            kfall[
                severity
            ][
                "detected_count"
            ]
        )
        for severity
        in SEVERITIES
    )

    hard_emission_count = detected
    hard_correct_count = detected

    return {
        "qualified_hard_cause_precision":
            (
                hard_correct_count
                / hard_emission_count
                if hard_emission_count
                else None
            ),

        "qualified_hard_cause_coverage":
            (
                detected
                / denominator
                if denominator
                else None
            ),

        "qualified_hard_cause_coverage_denominator_definition":
            "admissible KFALL FRAME_GAP final-test P0 episodes",

        "unsupported_cause_emission_count":
            corrupt_metrics[
                "unsupported_cause_emission_count"
            ],

        "synthetic_truth_never_promoted":
            True,

        "selection_or_threshold_change_after_final_outcomes":
            False,
    }


def summarize_attempt_accounting(
    manifest,
):
    counts = Counter(
        row[
            "status"
        ]
        for row in manifest[
            "attempts"
        ]
    )

    return {
        "attempt_count":
            len(
                manifest[
                    "attempts"
                ]
            ),

        "admissible_count":
            counts[
                "ADMISSIBLE"
            ],

        "not_admissible_count":
            counts[
                "NOT_ADMISSIBLE"
            ],

        "not_admissible_excluded_from_detection_denominator":
            True,
    }


def main():
    evaluator_commit = (
        verify_evaluator_is_frozen()
    )

    manifest = load_json(
        FINAL_MANIFEST_PATH
    )

    receipt = load_json(
        FINAL_RECEIPT_PATH
    )

    operating_point = load_json(
        OPERATING_POINT_PATH
    )

    protocol = load_json(
        PROTOCOL_PATH
    )

    policy = load_json(
        POLICY_PATH
    )

    source_anchors = verify_frozen_anchors(
        manifest,
        receipt,
        operating_point,
        protocol,
        policy,
    )

    source_anchors[
        "final_evaluator"
    ] = {
        "tag":
            FINAL_EVALUATOR_TAG,

        "tag_commit":
            evaluator_commit,

        "evaluator_raw_sha256":
            file_sha256(
                Path(
                    __file__
                )
            ),

        "tests_raw_sha256":
            (
                file_sha256(
                    ROOT
                    / "tests/test_integrity_final_test_v1.py"
                )
                if (
                    ROOT
                    / "tests/test_integrity_final_test_v1.py"
                ).is_file()
                else None
            ),
    }

    streams, load_audit = (
        load_clean_final_test_streams(
            manifest,
            policy,
        )
    )

    clean_metrics = (
        evaluate_clean_fixed_operating_point(
            streams,
            operating_point,
            protocol,
        )
    )

    corruption_metrics = (
        evaluate_final_corruptions(
            streams,
            manifest,
            operating_point,
            protocol,
        )
    )

    attribution = build_attribution(
        corruption_metrics
    )

    attempt_accounting = (
        summarize_attempt_accounting(
            manifest
        )
    )

    result = {
        "result_id":
            "INTEGRITY_FINAL_TEST_V1_CANDIDATE",

        "status":
            "single_use_final_test_integrity_evaluation_candidate_before_result_receipt_freeze",

        "partition":
            "final_test",

        "source_anchors":
            source_anchors,

        "evaluation_contract": {
            "operating_point_frozen_before_final_test_generation":
                True,

            "operating_point_frozen_before_final_test_outcome_evaluation":
                True,

            "operating_point_modified_during_final_evaluation":
                False,

            "calibration_selection_reopened":
                False,

            "channel_freeze_candidate_grid_evaluated":
                False,

            "channel_freeze_selection_reopened":
                False,

            "timing_candidate_grid_evaluated":
                False,

            "timing_selection_reopened":
                False,

            "only_frozen_timing_envelope_evaluated":
                True,

            "channel_freeze_runtime_enabled":
                False,

            "timing_runtime_role":
                "OBSERVATION_ONLY",

            "timing_hard_promotion":
                False,

            "not_admissible_excluded_from_detection_denominator":
                True,

            "p0_truth_never_upgrades_runtime_evidence":
                True,

            "frame_repeat_hard_detector_used":
                False,

            "range_clip_hard_detector_used":
                False,

            "buffer_stall_detector_used":
                False,

            "fifo_overrun_detector_used":
                False,

            "task_model_outputs_used":
                False,

            "ood_outputs_used":
                False,

            "final_test_outcomes_used_for_tuning":
                False,

            "latency_definition":
                "elapsed sample/timestamp distance from corrupt_anchor_index to first qualifying configured evidence within injected episode",
        },

        "access_audit": {
            "final_test_raw_files_opened":
                len(
                    load_audit
                ),

            "additional_final_test_raw_file_open_count_for_evaluation":
                len(
                    load_audit
                ),

            "development_raw_files_opened":
                0,

            "calibration_raw_files_opened":
                0,

            "regenerated_admissible_pair_count":
                corruption_metrics[
                    "regenerated_admissible_pair_count"
                ],

            "final_test_detector_outputs_evaluated":
                True,

            "task_model_outputs_used":
                False,

            "ood_outputs_used":
                False,
        },

        "attempt_accounting":
            attempt_accounting,

        "clean_metrics":
            clean_metrics,

        "corruption_metrics":
            corruption_metrics,

        "attribution":
            attribution,

        "load_audit": {
            "final_test_trial_count":
                len(
                    load_audit
                ),

            "trial_ids_sha256":
                canonical_digest(
                    sorted(
                        row[
                            "trial_id"
                        ]
                        for row
                        in load_audit
                    )
                ),
        },
    }

    result[
        "content_sha256"
    ] = artifact_content_digest(
        result
    )

    RESULT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    RESULT_PATH.write_text(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        "INTEGRITY_FINAL_TEST_V1_CANDIDATE_WRITTEN = True"
    )

    print(
        "RESULT_PATH =",
        RESULT_PATH,
    )

    print(
        "RESULT_CONTENT_SHA256 =",
        result[
            "content_sha256"
        ],
    )

    print(
        "FINAL_TEST_RAW_FILES_OPENED =",
        len(
            load_audit
        ),
    )

    print(
        "REGENERATED_ADMISSIBLE_PAIR_COUNT =",
        corruption_metrics[
            "regenerated_admissible_pair_count"
        ],
    )

    print(
        "FINAL_TEST_DETECTOR_OUTCOMES_EVALUATED = True"
    )

    print(
        "TASK_MODEL_OUTPUTS_USED = False"
    )

    print(
        "OOD_OUTPUTS_USED = False"
    )

    print(
        "OPERATING_POINT_MODIFIED = False"
    )

    print(
        "CALIBRATION_SELECTION_REOPENED = False"
    )


if __name__ == "__main__":
    main()
