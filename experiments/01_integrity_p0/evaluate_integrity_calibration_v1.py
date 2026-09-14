from __future__ import annotations

import argparse
import importlib.util
import json
import math
import subprocess
import sys
from collections import defaultdict
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"

for path in (ROOT, SRC):
    text = str(path)
    if text not in sys.path:
        sys.path.insert(0, text)

from imu_reliability.integrity.evidence import (
    EvidenceStatus,
    IntegrityCause,
    SuspectIndicator,
)
from imu_reliability.integrity.flatness import (
    ChannelFreezeConfig,
    ChannelFreezeMonitor,
)
from imu_reliability.integrity.frame_gap import (
    observe_frame_counter,
)
from imu_reliability.integrity.monitor import (
    assess_evidence,
)
from imu_reliability.integrity.timing import (
    TimingEnvelope,
    evaluate_timing_envelope,
)
from imu_reliability.injection.evidence_bridge import (
    p0_truth_to_evidence,
)
from imu_reliability.injection.p0 import (
    apply_p0_injection,
)
from imu_reliability.injection.types import (
    P0InjectionSpec,
    P0Stream,
)


PROTOCOL_PATH = (
    ROOT
    / "configs/integrity/integrity_calibration_protocol_v1.json"
)
RECEIPT_PATH = (
    ROOT
    / "data/manifests/p0_calibration_spec_receipt_v1.json"
)
MANIFEST_PATH = (
    ROOT
    / "data/manifests/p0_calibration_spec_manifest_v1_candidate.json"
)
POLICY_PATH = (
    ROOT
    / "configs/integrity/p0_corruption_policy_v1.json"
)
RESULT_PATH = (
    ROOT
    / "results/raw/integrity_calibration_v1_candidate.json"
)

CLEAN_RESULT_PATH = (
    ROOT
    / "results/raw/integrity_calibration_clean_v1_candidate.json"
)

CALIBRATION_INPUT_PATHS = (
    PROTOCOL_PATH,
    RECEIPT_PATH,
    MANIFEST_PATH,
    POLICY_PATH,
)

EXPECTED_BASE_COMMIT = (
    "305a7b0b68898df7b6dcca9db54d454ef8d7ba57"
)
EXPECTED_PROTOCOL_TAG = "integrity-calibration-protocol-v1"

EXPECTED_CONTENT_HASHES = {
    "protocol":
        "ef912fe988d58e3ec86a9413298eec2491ff3186199462a285a558aefcebe806",
    "receipt":
        "104d14aaa013ce0782c76d44255cb2b0a55ad791daea78a11aa8da131c445b6b",
    "manifest":
        "f95ada2da8355b21f43aac6d7d9438eeebf70305f21e7a1e3a1d66c11fd498a6",
    "policy":
        "cb33c32951930453db550dfd02deab67a9eb51e851edf1a186e7faa4a5432220",
}

SUPPORTED_DATASETS = (
    "KFALL",
    "UNIVRFALL",
)

SEVERITIES = (
    "low",
    "medium",
    "high",
)


def canonical_json(payload: Any) -> str:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def canonical_digest(payload: Any) -> str:
    return sha256(
        canonical_json(payload).encode("utf-8")
    ).hexdigest()


def artifact_content_digest(
    payload: Any,
) -> str:
    """
    Compute a JSON-artifact-stable content digest.

    JSON object keys are strings on disk. Some in-memory evaluator
    structures use integer persistence keys, so normalize through a
    JSON round trip before applying the canonical digest. This affects
    artifact receipt hashing only; detector metrics, feasibility,
    candidate ranking, and frozen input verification are unchanged.
    """

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


def verify_content_hash(
    data: dict[str, Any],
    *,
    expected: str | None = None,
) -> str:
    payload = deepcopy(data)

    if "content_sha256" not in payload:
        raise RuntimeError(
            "Missing content_sha256"
        )

    stored = str(
        payload.pop("content_sha256")
    )

    computed = canonical_digest(
        payload
    )

    if stored != computed:
        raise RuntimeError(
            "Internal content hash mismatch: "
            f"{stored} != {computed}"
        )

    if (
        expected is not None
        and stored != expected
    ):
        raise RuntimeError(
            "Frozen content hash mismatch: "
            f"{stored} != {expected}"
        )

    return stored


def file_sha256(path: Path) -> str:
    return sha256(
        path.read_bytes()
    ).hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(
        ["git", *args],
        cwd=ROOT,
        text=True,
    ).strip()


def load_json(path: Path) -> dict[str, Any]:
    with path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        return json.load(handle)


def load_development_helper():
    path = (
        ROOT
        / "experiments/01_integrity_p0/"
          "build_p0_development_manifest_v1.py"
    )

    spec = importlib.util.spec_from_file_location(
        "_p0_dev_manifest_v1",
        path,
    )

    if (
        spec is None
        or spec.loader is None
    ):
        raise RuntimeError(
            f"Could not load helper: {path}"
        )

    module = importlib.util.module_from_spec(
        spec
    )

    sys.modules[
        spec.name
    ] = module

    spec.loader.exec_module(
        module
    )

    return module


def validate_calibration_manifest_boundary(
    manifest: dict[str, Any],
) -> None:
    if manifest.get("partition") != "calibration":
        raise RuntimeError(
            "Evaluator accepts calibration manifest only"
        )

    if (
        int(
            manifest.get(
                "calibration_trial_count",
                -1,
            )
        )
        != 446
    ):
        raise RuntimeError(
            "Unexpected calibration trial count"
        )

    trials = manifest.get(
        "trials",
        [],
    )

    if len(trials) != 446:
        raise RuntimeError(
            "Expected exactly 446 calibration trials"
        )

    trial_ids = {
        row["trial_id"]
        for row in trials
    }

    if len(trial_ids) != 446:
        raise RuntimeError(
            "Duplicate calibration trial_id"
        )

    for row in trials:
        if (
            row["dataset"]
            not in SUPPORTED_DATASETS
        ):
            raise RuntimeError(
                "Unexpected calibration dataset: "
                f"{row['dataset']}"
            )

        if (
            "partition" in row
            and row["partition"]
            != "calibration"
        ):
            raise RuntimeError(
                "Non-calibration trial encountered"
            )

    attempts = manifest.get(
        "attempts",
        [],
    )

    for row in attempts:
        if row.get(
            "partition"
        ) != "calibration":
            raise RuntimeError(
                "Non-calibration corruption attempt encountered"
            )

        if row["trial_id"] not in trial_ids:
            raise RuntimeError(
                "Attempt references unknown calibration trial"
            )


def verify_frozen_anchors(
    protocol: dict[str, Any],
    receipt: dict[str, Any],
    manifest: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    hashes = {
        "protocol":
            verify_content_hash(
                protocol,
                expected=EXPECTED_CONTENT_HASHES[
                    "protocol"
                ],
            ),
        "receipt":
            verify_content_hash(
                receipt,
                expected=EXPECTED_CONTENT_HASHES[
                    "receipt"
                ],
            ),
        "manifest":
            verify_content_hash(
                manifest,
                expected=EXPECTED_CONTENT_HASHES[
                    "manifest"
                ],
            ),
        "policy":
            verify_content_hash(
                policy,
                expected=EXPECTED_CONTENT_HASHES[
                    "policy"
                ],
            ),
    }

    current_head = git(
        "rev-parse",
        "HEAD",
    )

    tag_commit = git(
        "rev-parse",
        f"{EXPECTED_PROTOCOL_TAG}^{{commit}}",
    )

    if tag_commit != EXPECTED_BASE_COMMIT:
        raise RuntimeError(
            "Frozen protocol tag moved"
        )

    ancestry = subprocess.run(
        [
            "git",
            "merge-base",
            "--is-ancestor",
            EXPECTED_BASE_COMMIT,
            "HEAD",
        ],
        cwd=ROOT,
        check=False,
    )

    if ancestry.returncode != 0:
        raise RuntimeError(
            "Frozen integrity-calibration protocol commit "
            "is not an ancestor of current HEAD"
        )

    validate_calibration_manifest_boundary(
        manifest
    )

    freeze = protocol[
        "freeze_contract"
    ]

    if freeze[
        "calibration_detector_outputs_read_at_freeze"
    ]:
        raise RuntimeError(
            "Protocol says calibration detector outputs "
            "were already read at freeze"
        )

    if freeze[
        "calibration_task_model_outputs_read_at_freeze"
    ]:
        raise RuntimeError(
            "Protocol says task-model outputs were read"
        )

    if freeze[
        "final_test_outputs_read_at_freeze"
    ]:
        raise RuntimeError(
            "Protocol says final-test outputs were read"
        )

    if freeze[
        "historical_p0_timing_hard_promotion_allowed"
    ]:
        raise RuntimeError(
            "Timing hard promotion unexpectedly allowed"
        )

    if freeze[
        "channel_freeze_enters_hard_cause_set"
    ]:
        raise RuntimeError(
            "Channel freeze unexpectedly enters C_t"
        )

    if freeze[
        "range_clip_physical_rail_claim"
    ]:
        raise RuntimeError(
            "Synthetic range clamp unexpectedly "
            "claimed as physical rail"
        )

    if (
        protocol[
            "scope"
        ][
            "final_test_data_allowed"
        ]
    ):
        raise RuntimeError(
            "Final-test access unexpectedly allowed"
        )

    if (
        protocol[
            "scope"
        ][
            "task_model_outcomes_allowed_during_integrity_calibration"
        ]
    ):
        raise RuntimeError(
            "Task-model outcomes unexpectedly allowed"
        )

    if (
        protocol[
            "scope"
        ][
            "ood_outcomes_allowed_during_integrity_calibration"
        ]
    ):
        raise RuntimeError(
            "OOD outcomes unexpectedly allowed"
        )

    if (
        receipt[
            "freeze_contract"
        ][
            "full_calibration_manifest_content_sha256"
        ]
        != hashes["manifest"]
    ):
        raise RuntimeError(
            "Receipt does not anchor calibration manifest"
        )

    if (
        protocol[
            "freeze_contract"
        ][
            "calibration_receipt_content_sha256"
        ]
        != hashes["receipt"]
    ):
        raise RuntimeError(
            "Protocol does not anchor calibration receipt"
        )

    return {
        "base_commit":
            current_head,
        "protocol_tag":
            EXPECTED_PROTOCOL_TAG,
        "protocol_tag_commit":
            tag_commit,
        "canonical_content_sha256":
            hashes,
        "raw_file_sha256": {
            "protocol":
                file_sha256(
                    PROTOCOL_PATH
                ),
            "receipt":
                file_sha256(
                    RECEIPT_PATH
                ),
            "manifest":
                file_sha256(
                    MANIFEST_PATH
                ),
            "policy":
                file_sha256(
                    POLICY_PATH
                ),
        },
    }


def timing_scale_to_ms(
    dataset: str,
    protocol: dict[str, Any],
) -> float:
    return float(
        protocol[
            "timing_preprocessing_contract"
        ][dataset][
            "multiply_raw_timestamp_by"
        ]
    )


def timestamps_to_ms(
    stream: P0Stream,
    dataset: str,
    protocol: dict[str, Any],
) -> np.ndarray:
    if stream.timestamps is None:
        raise RuntimeError(
            f"{dataset} stream has no timestamps"
        )

    return np.asarray(
        stream.timestamps,
        dtype=np.float64,
    ) * timing_scale_to_ms(
        dataset,
        protocol,
    )


def observed_hours(
    stream: P0Stream,
    dataset: str,
    protocol: dict[str, Any],
) -> float:
    timestamps_ms = timestamps_to_ms(
        stream,
        dataset,
        protocol,
    )

    if timestamps_ms.size < 2:
        return 0.0

    duration_ms = float(
        timestamps_ms[-1]
        - timestamps_ms[0]
    )

    if duration_ms < 0:
        raise RuntimeError(
            "Negative trial observation duration"
        )

    return duration_ms / 3_600_000.0


def freeze_run_lengths(
    values: np.ndarray,
    *,
    absolute_tolerance: float,
) -> np.ndarray:
    values = np.asarray(
        values,
        dtype=np.float64,
    )

    if values.ndim != 2:
        raise ValueError(
            "values must be 2-D"
        )

    n, channels = values.shape

    runs = np.zeros(
        (n, channels),
        dtype=np.int64,
    )

    if n <= 1:
        return runs

    unchanged = (
        np.abs(
            values[1:]
            - values[:-1]
        )
        <= float(
            absolute_tolerance
        )
    )

    for channel in range(
        channels
    ):
        current = 0

        for sample_index in range(
            1,
            n,
        ):
            if unchanged[
                sample_index - 1,
                channel,
            ]:
                current += 1
            else:
                current = 0

            runs[
                sample_index,
                channel,
            ] = current

    return runs


def freeze_state_from_runs(
    runs: np.ndarray,
    *,
    consecutive_deltas: int,
) -> np.ndarray:
    return np.any(
        runs
        >= int(
            consecutive_deltas
        ),
        axis=1,
    )


def onset_count(
    state: np.ndarray,
) -> int:
    state = np.asarray(
        state,
        dtype=bool,
    )

    if state.size == 0:
        return 0

    previous = np.empty_like(
        state
    )

    previous[0] = False

    if state.size > 1:
        previous[1:] = state[:-1]

    return int(
        np.count_nonzero(
            state
            & ~previous
        )
    )


def monitor_freeze_state_reference(
    values: np.ndarray,
    *,
    absolute_tolerance: float,
    consecutive_deltas: int,
) -> np.ndarray:
    values = np.asarray(
        values,
        dtype=np.float64,
    )

    monitor = ChannelFreezeMonitor(
        n_channels=values.shape[1],
        config=ChannelFreezeConfig(
            absolute_tolerance=
                absolute_tolerance,
            consecutive_deltas=
                consecutive_deltas,
        ),
    )

    state = np.zeros(
        values.shape[0],
        dtype=bool,
    )

    for index, sample in enumerate(
        values
    ):
        evidence = monitor.update(
            sample,
            source="CALIBRATION_REFERENCE",
        )

        assessment = assess_evidence(
            evidence
        )

        if assessment.has_hard_alert:
            raise RuntimeError(
                "Channel freeze monitor emitted a hard cause"
            )

        state[index] = (
            SuspectIndicator
            .CHANNEL_FREEZE_SUSPECT
            in assessment.suspects
        )

    return state


def timing_outside_mask(
    stream: P0Stream,
    dataset: str,
    *,
    minimum_delta_ms: float,
    maximum_delta_ms: float,
    protocol: dict[str, Any],
) -> np.ndarray:
    timestamps_ms = timestamps_to_ms(
        stream,
        dataset,
        protocol,
    )

    mask = np.zeros(
        timestamps_ms.shape[0],
        dtype=bool,
    )

    if timestamps_ms.size <= 1:
        return mask

    deltas = (
        timestamps_ms[1:]
        - timestamps_ms[:-1]
    )

    mask[1:] = (
        (deltas < minimum_delta_ms)
        | (deltas > maximum_delta_ms)
    )

    return mask


def evaluate_timing_boundary(
    stream: P0Stream,
    dataset: str,
    *,
    anchor_index: int,
    minimum_delta_ms: float,
    maximum_delta_ms: float,
    protocol: dict[str, Any],
):
    timestamps_ms = timestamps_to_ms(
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

    envelope = TimingEnvelope(
        minimum_delta=float(
            minimum_delta_ms
        ),
        maximum_delta=float(
            maximum_delta_ms
        ),
        unit="ms",
        frozen=False,
    )

    evidence = evaluate_timing_envelope(
        timestamps_ms[
            anchor - 1
        ],
        timestamps_ms[
            anchor
        ],
        envelope=envelope,
        timestamp_provenance_qualified=False,
        source=(
            "HISTORICAL_P0_CALIBRATION::"
            + dataset
        ),
    )

    if evidence is not None:
        if (
            evidence.status
            is not EvidenceStatus.OBSERVATION_ONLY
        ):
            raise RuntimeError(
                "Historical P0 timing candidate "
                "was promoted above observation-only"
            )

        if assess_evidence(
            [evidence]
        ).has_hard_alert:
            raise RuntimeError(
                "Timing candidate entered hard cause set"
            )

    return evidence


def evaluate_frame_gap_event(
    dataset: str,
    corrupt: P0Stream,
    *,
    corrupt_anchor_index: int,
) -> dict[str, Any]:
    anchor = int(
        corrupt_anchor_index
    )

    if dataset == "UNIVRFALL":
        return {
            "detected":
                False,
            "hard_qualified":
                False,
            "cause":
                None,
            "reason":
                "UNVERIFIED_OR_ABSENT_DIRECT_COUNTER_PROVENANCE",
        }

    if dataset != "KFALL":
        raise ValueError(
            f"Unsupported dataset: {dataset}"
        )

    if corrupt.counters is None:
        raise RuntimeError(
            "KFall stream lacks raw FrameCounter"
        )

    if (
        anchor <= 0
        or anchor >= corrupt.n_samples
    ):
        raise ValueError(
            "FRAME_GAP corrupt anchor outside stream"
        )

    evidence = observe_frame_counter(
        int(
            corrupt.counters[
                anchor - 1
            ]
        ),
        int(
            corrupt.counters[
                anchor
            ]
        ),
        provenance_qualified=True,
        source="KFALL_RAW_FRAMECOUNTER",
    )

    if evidence is None:
        return {
            "detected":
                False,
            "hard_qualified":
                False,
            "cause":
                None,
            "reason":
                "NO_COUNTER_DISCONTINUITY",
        }

    assessment = assess_evidence(
        [evidence]
    )

    detected = (
        IntegrityCause.FRAME_GAP
        in assessment.hard_causes
    )

    return {
        "detected":
            bool(
                detected
            ),
        "hard_qualified":
            bool(
                detected
            ),
        "cause":
            (
                "FRAME_GAP"
                if detected
                else None
            ),
        "indicator":
            evidence.indicator,
        "status":
            evidence.status.value,
        "details":
            dict(
                evidence.details
            ),
    }


def clean_frame_gap_hard_alert_count(
    dataset: str,
    stream: P0Stream,
) -> int:
    if stream.counters is None:
        return 0

    counters = np.asarray(
        stream.counters,
        dtype=np.int64,
    )

    if counters.size <= 1:
        return 0

    provenance_qualified = (
        dataset == "KFALL"
    )

    deltas = (
        counters[1:]
        - counters[:-1]
    )

    unusual = np.flatnonzero(
        deltas != 1
    ) + 1

    hard = 0

    for index in unusual.tolist():
        evidence = observe_frame_counter(
            int(
                counters[
                    index - 1
                ]
            ),
            int(
                counters[
                    index
                ]
            ),
            provenance_qualified=
                provenance_qualified,
            source=(
                "KFALL_RAW_FRAMECOUNTER"
                if provenance_qualified
                else
                "UNQUALIFIED_COUNTER"
            ),
        )

        if (
            evidence is not None
            and assess_evidence(
                [evidence]
            ).has_hard_alert
        ):
            hard += 1

    return hard


def spec_from_attempt(
    attempt: dict[str, Any],
) -> P0InjectionSpec:
    raw = attempt[
        "spec"
    ]

    return P0InjectionSpec(
        kind=raw[
            "kind"
        ],
        start_index=int(
            raw[
                "start_index"
            ]
        ),
        length=int(
            raw[
                "length"
            ]
        ),
        severity=str(
            raw[
                "severity"
            ]
        ),
        channels=tuple(
            int(x)
            for x in raw.get(
                "channels",
                [],
            )
        ),
        seed=int(
            raw.get(
                "seed",
                0,
            )
        ),
        parameters=dict(
            raw.get(
                "parameters",
                {},
            )
        ),
    )


def regenerate_pair(
    clean: P0Stream,
    attempt: dict[str, Any],
):
    if attempt[
        "status"
    ] != "ADMISSIBLE":
        raise ValueError(
            "Cannot regenerate NOT_ADMISSIBLE attempt"
        )

    spec = spec_from_attempt(
        attempt
    )

    if (
        spec.spec_id
        != attempt[
            "spec_id"
        ]
    ):
        raise RuntimeError(
            "Frozen spec_id mismatch"
        )

    pair = apply_p0_injection(
        clean,
        spec,
    )

    if len(
        pair.truths
    ) != 1:
        raise RuntimeError(
            "Expected exactly one P0 truth"
        )

    truth = pair.truths[0]

    if (
        truth.injection_id
        != attempt[
            "injection_id"
        ]
    ):
        raise RuntimeError(
            "Frozen injection_id mismatch"
        )

    if (
        pair.clean.fingerprint()
        != attempt[
            "clean_stream_fingerprint"
        ]
    ):
        raise RuntimeError(
            "Clean stream fingerprint changed"
        )

    corrupt_fingerprint = (
        pair.corrupt.fingerprint()
    )

    if (
        corrupt_fingerprint
        != attempt[
            "corrupt_stream_fingerprint"
        ]
    ):
        raise RuntimeError(
            "Corrupt stream fingerprint changed"
        )

    if (
        corrupt_fingerprint
        == pair.clean.fingerprint()
    ):
        raise RuntimeError(
            "Frozen admissible corruption became a no-op"
        )

    if (
        truth.affected_clean_start
        != attempt[
            "affected_clean_start"
        ]
        or
        truth.affected_clean_end_exclusive
        != attempt[
            "affected_clean_end_exclusive"
        ]
        or
        truth.corrupt_anchor_index
        != attempt[
            "corrupt_anchor_index"
        ]
    ):
        raise RuntimeError(
            "Frozen truth geometry mismatch"
        )

    synthetic_evidence = (
        p0_truth_to_evidence(
            truth
        )
    )

    if (
        synthetic_evidence.status
        is not EvidenceStatus.SYNTHETIC_GROUND_TRUTH
    ):
        raise RuntimeError(
            "P0 truth did not remain synthetic ground truth"
        )

    if assess_evidence(
        [synthetic_evidence]
    ).has_hard_alert:
        raise RuntimeError(
            "Synthetic truth entered hard cause set"
        )

    return pair


def empty_event_bucket() -> dict[str, Any]:
    return {
        "episode_count":
            0,
        "detected_count":
            0,
        "_latency_samples":
            [],
        "_latency_ms":
            [],
    }


def add_event(
    bucket: dict[str, Any],
    *,
    detected: bool,
    latency_samples: int | None = None,
    latency_ms: float | None = None,
) -> None:
    bucket[
        "episode_count"
    ] += 1

    if not detected:
        return

    bucket[
        "detected_count"
    ] += 1

    if latency_samples is not None:
        bucket[
            "_latency_samples"
        ].append(
            int(
                latency_samples
            )
        )

    if latency_ms is not None:
        bucket[
            "_latency_ms"
        ].append(
            float(
                latency_ms
            )
        )


def finalize_event_bucket(
    bucket: dict[str, Any],
) -> dict[str, Any]:
    total = int(
        bucket[
            "episode_count"
        ]
    )

    detected = int(
        bucket[
            "detected_count"
        ]
    )

    latency_samples = [
        int(value)
        for value
        in bucket[
            "_latency_samples"
        ]
    ]

    latency_ms = [
        float(value)
        for value
        in bucket[
            "_latency_ms"
        ]
    ]

    return {
        "episode_count":
            total,
        "detected_count":
            detected,
        "event_detection_recall":
            (
                detected / total
                if total
                else None
            ),
        "confirmation_latency_samples":
            latency_samples,
        "confirmation_latency_ms":
            latency_ms,
        "median_confirmation_latency_samples":
            (
                float(
                    np.median(
                        latency_samples
                    )
                )
                if latency_samples
                else None
            ),
        "median_confirmation_latency_ms":
            (
                float(
                    np.median(
                        latency_ms
                    )
                )
                if latency_ms
                else None
            ),
    }


def select_channel_freeze_candidate(
    candidates: list[
        dict[str, Any]
    ],
) -> dict[str, Any]:
    feasible = [
        row
        for row in candidates
        if row[
            "feasible"
        ]
    ]

    def latency_value(
        row,
    ):
        value = row[
            "median_confirmation_latency_ms"
        ]

        return (
            math.inf
            if value is None
            else float(
                value
            )
        )

    def serialized(
        row,
    ):
        return canonical_json(
            {
                "absolute_tolerance":
                    row[
                        "absolute_tolerance"
                    ],
                "consecutive_deltas":
                    row[
                        "consecutive_deltas"
                    ],
            }
        )

    def rank_key(
        row,
    ):
        return (
            -float(
                row[
                    "equal_dataset_weighted_macro_event_recall"
                ]
            ),
            latency_value(
                row
            ),
            -int(
                row[
                    "consecutive_deltas"
                ]
            ),
            serialized(
                row
            ),
        )

    ranked = sorted(
        feasible,
        key=rank_key,
    )

    diagnostic_ranked = sorted(
        candidates,
        key=rank_key,
    )

    selected = (
        None
        if not ranked
        else ranked[0]
    )

    diagnostic = (
        None
        if not diagnostic_ranked
        else diagnostic_ranked[0]
    )

    trace = []

    for index, row in enumerate(
        ranked
    ):
        trace.append(
            {
                "rank":
                    index + 1,
                "absolute_tolerance":
                    row[
                        "absolute_tolerance"
                    ],
                "consecutive_deltas":
                    row[
                        "consecutive_deltas"
                    ],
                "objective":
                    row[
                        "equal_dataset_weighted_macro_event_recall"
                    ],
                "median_confirmation_latency_ms":
                    row[
                        "median_confirmation_latency_ms"
                    ],
                "serialized_candidate":
                    serialized(
                        row
                    ),
            }
        )

    return {
        "selected_candidate":
            selected,
        "best_diagnostic_candidate":
            diagnostic,
        "feasible_candidate_count":
            len(
                feasible
            ),
        "selection_trace":
            trace,
        "failure_policy_applied":
            (
                None
                if selected is not None
                else
                "NO_FEASIBLE_CANDIDATE_DISABLE_MAIN_SUSPECT"
            ),
    }


def select_timing_candidate(
    candidates: list[
        dict[str, Any]
    ],
) -> dict[str, Any]:
    feasible = [
        row
        for row in candidates
        if row[
            "feasible"
        ]
    ]

    def serialized(
        row,
    ):
        return canonical_json(
            {
                "minimum_delta_ms":
                    row[
                        "minimum_delta_ms"
                    ],
                "maximum_delta_ms":
                    row[
                        "maximum_delta_ms"
                    ],
            }
        )

    def width(
        row,
    ):
        return (
            float(
                row[
                    "maximum_delta_ms"
                ]
            )
            - float(
                row[
                    "minimum_delta_ms"
                ]
            )
        )

    def rank_key(
        row,
    ):
        return (
            -float(
                row[
                    "macro_event_recall"
                ]
            ),
            -width(
                row
            ),
            serialized(
                row
            ),
        )

    ranked = sorted(
        feasible,
        key=rank_key,
    )

    return {
        "selected_candidate":
            (
                None
                if not ranked
                else ranked[0]
            ),
        "feasible_candidate_count":
            len(
                feasible
            ),
        "selection_trace": [
            {
                "rank":
                    index + 1,
                "minimum_delta_ms":
                    row[
                        "minimum_delta_ms"
                    ],
                "maximum_delta_ms":
                    row[
                        "maximum_delta_ms"
                    ],
                "macro_event_recall":
                    row[
                        "macro_event_recall"
                    ],
                "width_ms":
                    width(
                        row
                    ),
                "serialized_candidate":
                    serialized(
                        row
                    ),
            }
            for index, row
            in enumerate(
                ranked
            )
        ],
        "failure_policy_applied":
            (
                None
                if ranked
                else
                "NO_FEASIBLE_ENVELOPE_REMAIN_RAW_OBSERVATION_ONLY"
            ),
    }


def load_clean_calibration_streams(
    manifest: dict[str, Any],
    policy: dict[str, Any],
):
    helper = load_development_helper()

    streams = {}
    load_audit = []

    for row in manifest[
        "trials"
    ]:
        registry_row = {
            "trial_id":
                row[
                    "trial_id"
                ],
        }

        lineage_row = {
            "raw_pairing": {
                "original": [
                    row[
                        "raw_original_path"
                    ]
                ],
            },
        }

        stream, raw_path, schema = (
            helper.load_clean_stream(
                registry_row,
                lineage_row,
                policy,
            )
        )

        fingerprint = (
            stream.fingerprint()
        )

        if (
            fingerprint
            != row[
                "clean_stream_fingerprint"
            ]
        ):
            raise RuntimeError(
                "Clean calibration fingerprint mismatch: "
                f"{row['trial_id']}"
            )

        if (
            stream.n_samples
            != row[
                "clean_n_samples"
            ]
            or
            stream.n_channels
            != row[
                "clean_n_channels"
            ]
        ):
            raise RuntimeError(
                "Clean calibration shape mismatch: "
                f"{row['trial_id']}"
            )

        streams[
            row[
                "trial_id"
            ]
        ] = {
            "dataset":
                row[
                    "dataset"
                ],
            "stream":
                stream,
            "raw_path":
                str(
                    raw_path
                ),
            "schema":
                schema,
        }

        load_audit.append(
            {
                "trial_id":
                    row[
                        "trial_id"
                    ],
                "dataset":
                    row[
                        "dataset"
                    ],
                "raw_path":
                    str(
                        raw_path
                    ),
                "clean_stream_fingerprint":
                    fingerprint,
            }
        )

    return streams, load_audit


def evaluate_clean(
    streams,
    protocol,
):
    freeze_grid = (
        protocol[
            "search_spaces"
        ][
            "CHANNEL_FREEZE_SUSPECT"
        ]
    )

    tolerances = freeze_grid[
        "absolute_tolerance"
    ]

    if tolerances != [
        0.0
    ]:
        raise RuntimeError(
            "Unexpected freeze tolerance grid"
        )

    persistence_grid = [
        int(
            x
        )
        for x in freeze_grid[
            "consecutive_deltas"
        ]
    ]

    freeze_acc = {
        p: {
            dataset: {
                "trial_count":
                    0,
                "hours_observed":
                    0.0,
                "suspect_onset_count":
                    0,
                "suspect_sample_count":
                    0,
                "sample_count":
                    0,
                "trials_with_any_suspect":
                    0,
            }
            for dataset
            in SUPPORTED_DATASETS
        }
        for p
        in persistence_grid
    }

    timing_grid = (
        protocol[
            "search_spaces"
        ][
            "TIMING_OBSERVATION_ENVELOPE"
        ]
    )

    timing_acc = {
        dataset: [
            {
                "candidate":
                    dict(
                        candidate
                    ),
                "trial_count":
                    0,
                "hours_observed":
                    0.0,
                "outside_interval_count":
                    0,
                "trials_with_any_outside":
                    0,
            }
            for candidate
            in timing_grid[
                dataset
            ]
        ]
        for dataset
        in SUPPORTED_DATASETS
    }

    clean_hard = {
        dataset: {
            "trial_count":
                0,
            "hours_observed":
                0.0,
            "hard_alert_count":
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

        hours = observed_hours(
            stream,
            dataset,
            protocol,
        )

        clean_hard[
            dataset
        ][
            "trial_count"
        ] += 1

        clean_hard[
            dataset
        ][
            "hours_observed"
        ] += hours

        clean_hard[
            dataset
        ][
            "hard_alert_count"
        ] += clean_frame_gap_hard_alert_count(
            dataset,
            stream,
        )

        runs = freeze_run_lengths(
            stream.values,
            absolute_tolerance=0.0,
        )

        for persistence in persistence_grid:
            state = (
                freeze_state_from_runs(
                    runs,
                    consecutive_deltas=
                        persistence,
                )
            )

            acc = freeze_acc[
                persistence
            ][dataset]

            acc[
                "trial_count"
            ] += 1

            acc[
                "hours_observed"
            ] += hours

            acc[
                "suspect_onset_count"
            ] += onset_count(
                state
            )

            acc[
                "suspect_sample_count"
            ] += int(
                np.count_nonzero(
                    state
                )
            )

            acc[
                "sample_count"
            ] += int(
                state.size
            )

            if np.any(
                state
            ):
                acc[
                    "trials_with_any_suspect"
                ] += 1

        for candidate_index, candidate in enumerate(
            timing_grid[
                dataset
            ]
        ):
            outside = timing_outside_mask(
                stream,
                dataset,
                minimum_delta_ms=float(
                    candidate[
                        "minimum_delta_ms"
                    ]
                ),
                maximum_delta_ms=float(
                    candidate[
                        "maximum_delta_ms"
                    ]
                ),
                protocol=protocol,
            )

            acc = timing_acc[
                dataset
            ][
                candidate_index
            ]

            acc[
                "trial_count"
            ] += 1

            acc[
                "hours_observed"
            ] += hours

            acc[
                "outside_interval_count"
            ] += int(
                np.count_nonzero(
                    outside
                )
            )

            if np.any(
                outside
            ):
                acc[
                    "trials_with_any_outside"
                ] += 1

    freeze_metrics = {}

    for persistence, by_dataset in freeze_acc.items():
        freeze_metrics[
            persistence
        ] = {}

        for dataset, acc in by_dataset.items():
            hours = acc[
                "hours_observed"
            ]

            trials = acc[
                "trial_count"
            ]

            samples = acc[
                "sample_count"
            ]

            freeze_metrics[
                persistence
            ][dataset] = {
                "hours_observed":
                    hours,
                "suspect_onset_count":
                    acc[
                        "suspect_onset_count"
                    ],
                "suspect_onsets_per_hour":
                    (
                        acc[
                            "suspect_onset_count"
                        ]
                        / hours
                        if hours > 0
                        else None
                    ),
                "time_in_suspect_fraction":
                    (
                        acc[
                            "suspect_sample_count"
                        ]
                        / samples
                        if samples > 0
                        else None
                    ),
                "fraction_trials_with_any_suspect":
                    (
                        acc[
                            "trials_with_any_suspect"
                        ]
                        / trials
                        if trials > 0
                        else None
                    ),
                "trial_count":
                    trials,
            }

    timing_metrics = {}

    for dataset, rows in timing_acc.items():
        timing_metrics[
            dataset
        ] = []

        for acc in rows:
            hours = acc[
                "hours_observed"
            ]

            trials = acc[
                "trial_count"
            ]

            timing_metrics[
                dataset
            ].append(
                {
                    **acc[
                        "candidate"
                    ],
                    "hours_observed":
                        hours,
                    "timing_outside_interval_count":
                        acc[
                            "outside_interval_count"
                        ],
                    "timing_outside_intervals_per_hour":
                        (
                            acc[
                                "outside_interval_count"
                            ]
                            / hours
                            if hours > 0
                            else None
                        ),
                    "fraction_trials_with_any_timing_outside":
                        (
                            acc[
                                "trials_with_any_outside"
                            ]
                            / trials
                            if trials > 0
                            else None
                        ),
                    "trial_count":
                        trials,
                }
            )

    hard_metrics = {}

    for dataset, acc in clean_hard.items():
        hours = acc[
            "hours_observed"
        ]

        hard_metrics[
            dataset
        ] = {
            "hours_observed":
                hours,
            "hard_alert_count":
                acc[
                    "hard_alert_count"
                ],
            "hard_alerts_per_hour":
                (
                    acc[
                        "hard_alert_count"
                    ]
                    / hours
                    if hours > 0
                    else None
                ),
            "trial_count":
                acc[
                    "trial_count"
                ],
        }

    return {
        "channel_freeze":
            freeze_metrics,
        "timing":
            timing_metrics,
        "hard_cause":
            hard_metrics,
    }



def evaluate_clean_feasibility(
    clean,
    protocol,
):
    freeze_constraints = (
        protocol[
            "clean_constraints"
        ][
            "CHANNEL_FREEZE_SUSPECT"
        ]
    )

    freeze_rows = []

    for persistence in (
        protocol[
            "search_spaces"
        ][
            "CHANNEL_FREEZE_SUSPECT"
        ][
            "consecutive_deltas"
        ]
    ):
        p = int(
            persistence
        )

        reasons = []

        by_dataset = clean[
            "channel_freeze"
        ][p]

        for dataset in SUPPORTED_DATASETS:
            metrics = by_dataset[
                dataset
            ]

            if (
                metrics[
                    "suspect_onsets_per_hour"
                ]
                > freeze_constraints[
                    "maximum_onsets_per_hour_per_dataset"
                ]
            ):
                reasons.append(
                    dataset
                    + ":suspect_onsets_per_hour"
                )

            if (
                metrics[
                    "time_in_suspect_fraction"
                ]
                > freeze_constraints[
                    "maximum_time_in_suspect_fraction_per_dataset"
                ]
            ):
                reasons.append(
                    dataset
                    + ":time_in_suspect_fraction"
                )

            if (
                metrics[
                    "fraction_trials_with_any_suspect"
                ]
                > freeze_constraints[
                    "maximum_fraction_of_clean_trials_with_any_suspect_per_dataset"
                ]
            ):
                reasons.append(
                    dataset
                    + ":fraction_trials_with_any_suspect"
                )

        freeze_rows.append(
            {
                "absolute_tolerance":
                    0.0,
                "consecutive_deltas":
                    p,
                "feasible":
                    not reasons,
                "infeasible_reasons":
                    reasons,
                "clean_by_dataset":
                    by_dataset,
            }
        )

    timing_constraints = (
        protocol[
            "clean_constraints"
        ][
            "TIMING_OBSERVATION_ENVELOPE"
        ]
    )

    timing_rows = {}

    for dataset in SUPPORTED_DATASETS:
        timing_rows[
            dataset
        ] = []

        for metrics in clean[
            "timing"
        ][dataset]:
            reasons = []

            if (
                metrics[
                    "timing_outside_intervals_per_hour"
                ]
                > timing_constraints[
                    "maximum_outside_intervals_per_hour_per_dataset"
                ]
            ):
                reasons.append(
                    "timing_outside_intervals_per_hour"
                )

            if (
                metrics[
                    "fraction_trials_with_any_timing_outside"
                ]
                > timing_constraints[
                    "maximum_fraction_of_clean_trials_with_any_outside_interval_per_dataset"
                ]
            ):
                reasons.append(
                    "fraction_trials_with_any_timing_outside"
                )

            timing_rows[
                dataset
            ].append(
                {
                    "minimum_delta_ms":
                        metrics[
                            "minimum_delta_ms"
                        ],
                    "maximum_delta_ms":
                        metrics[
                            "maximum_delta_ms"
                        ],
                    "feasible":
                        not reasons,
                    "infeasible_reasons":
                        reasons,
                    "clean_metrics":
                        metrics,
                }
            )

    clean_hard_alert_count = sum(
        row[
            "hard_alert_count"
        ]
        for row
        in clean[
            "hard_cause"
        ].values()
    )

    return {
        "CHANNEL_FREEZE_SUSPECT":
            freeze_rows,
        "TIMING_OBSERVATION_ENVELOPE":
            timing_rows,
        "hard_cause_set": {
            "require_zero_clean_hard_alerts":
                True,
            "observed_clean_hard_alert_count":
                clean_hard_alert_count,
            "feasible":
                clean_hard_alert_count == 0,
        },
    }



def evaluate_corruptions(
    streams,
    manifest,
    protocol,
):
    persistence_grid = [
        int(
            value
        )
        for value in protocol[
            "search_spaces"
        ][
            "CHANNEL_FREEZE_SUSPECT"
        ][
            "consecutive_deltas"
        ]
    ]

    timing_grid = (
        protocol[
            "search_spaces"
        ][
            "TIMING_OBSERVATION_ENVELOPE"
        ]
    )

    freeze_events = {
        persistence: defaultdict(
            empty_event_bucket
        )
        for persistence
        in persistence_grid
    }

    timing_events = {
        dataset: {
            canonical_json(
                candidate
            ): defaultdict(
                empty_event_bucket
            )
            for candidate
            in timing_grid[
                dataset
            ]
        }
        for dataset
        in SUPPORTED_DATASETS
    }

    frame_gap_events = defaultdict(
        empty_event_bucket
    )

    status_counts = defaultdict(
        int
    )

    not_admissible_counts = defaultdict(
        int
    )

    family_admissible_counts = defaultdict(
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

            status_counts[
                (
                    dataset,
                    family,
                    severity,
                    attempt[
                        "status"
                    ],
                )
            ] += 1

            if (
                attempt[
                    "status"
                ]
                != "ADMISSIBLE"
            ):
                not_admissible_counts[
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

            pair = regenerate_pair(
                clean,
                attempt,
            )

            regenerated_pairs += 1

            family_admissible_counts[
                (
                    dataset,
                    family,
                    severity,
                )
            ] += 1

            truth = pair.truths[0]

            if family == "CHANNEL_FREEZE":
                if len(
                    truth.spec.channels
                ) != 1:
                    raise RuntimeError(
                        "Expected one frozen channel"
                    )

                channel = int(
                    truth.spec.channels[0]
                )

                runs = freeze_run_lengths(
                    pair.corrupt.values[
                        :,
                        channel:
                            channel + 1,
                    ],
                    absolute_tolerance=0.0,
                )[:, 0]

                timestamps_ms = (
                    timestamps_to_ms(
                        pair.corrupt,
                        dataset,
                        protocol,
                    )
                )

                start = int(
                    truth.affected_clean_start
                )

                end = int(
                    truth.affected_clean_end_exclusive
                )

                anchor = int(
                    truth.corrupt_anchor_index
                )

                indices = np.arange(
                    pair.corrupt.n_samples,
                    dtype=np.int64,
                )

                inside_episode = (
                    (indices >= start)
                    & (indices < end)
                )

                for persistence in persistence_grid:
                    hits = np.flatnonzero(
                        inside_episode
                        & (
                            runs
                            >= persistence
                        )
                    )

                    detected = (
                        hits.size > 0
                    )

                    latency_samples = None
                    latency_ms = None

                    if detected:
                        confirmation = int(
                            hits[0]
                        )

                        latency_samples = (
                            confirmation
                            - anchor
                        )

                        latency_ms = float(
                            timestamps_ms[
                                confirmation
                            ]
                            - timestamps_ms[
                                anchor
                            ]
                        )

                    bucket = (
                        freeze_events[
                            persistence
                        ][
                            (
                                dataset,
                                severity,
                            )
                        ]
                    )

                    add_event(
                        bucket,
                        detected=detected,
                        latency_samples=
                            latency_samples,
                        latency_ms=
                            latency_ms,
                    )

            elif family == "TIMING_PERTURBATION":
                anchor = int(
                    truth.corrupt_anchor_index
                )

                for candidate in timing_grid[
                    dataset
                ]:
                    evidence = (
                        evaluate_timing_boundary(
                            pair.corrupt,
                            dataset,
                            anchor_index=
                                anchor,
                            minimum_delta_ms=
                                float(
                                    candidate[
                                        "minimum_delta_ms"
                                    ]
                                ),
                            maximum_delta_ms=
                                float(
                                    candidate[
                                        "maximum_delta_ms"
                                    ]
                                ),
                            protocol=
                                protocol,
                        )
                    )

                    detected = (
                        evidence is not None
                    )

                    key = canonical_json(
                        candidate
                    )

                    bucket = (
                        timing_events[
                            dataset
                        ][key][
                            severity
                        ]
                    )

                    add_event(
                        bucket,
                        detected=detected,
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

            elif family == "FRAME_GAP":
                result = (
                    evaluate_frame_gap_event(
                        dataset,
                        pair.corrupt,
                        corrupt_anchor_index=
                            truth.corrupt_anchor_index,
                    )
                )

                bucket = (
                    frame_gap_events[
                        (
                            dataset,
                            severity,
                        )
                    ]
                )

                add_event(
                    bucket,
                    detected=result[
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

            elif family in (
                "FRAME_REPEAT",
                "RANGE_CLIP",
            ):
                pass

            else:
                raise RuntimeError(
                    "Unexpected P0 family: "
                    f"{family}"
                )

    freeze_summary = {}

    for persistence in persistence_grid:
        freeze_summary[
            str(
                persistence
            )
        ] = {}

        for dataset in SUPPORTED_DATASETS:
            freeze_summary[
                str(
                    persistence
                )
            ][dataset] = {}

            for severity in SEVERITIES:
                bucket = (
                    freeze_events[
                        persistence
                    ][
                        (
                            dataset,
                            severity,
                        )
                    ]
                )

                freeze_summary[
                    str(
                        persistence
                    )
                ][dataset][
                    severity
                ] = finalize_event_bucket(
                    bucket
                )

    timing_summary = {}

    for dataset in SUPPORTED_DATASETS:
        timing_summary[
            dataset
        ] = []

        for candidate in timing_grid[
            dataset
        ]:
            key = canonical_json(
                candidate
            )

            severity_rows = {}

            for severity in SEVERITIES:
                severity_rows[
                    severity
                ] = finalize_event_bucket(
                    timing_events[
                        dataset
                    ][key][
                        severity
                    ]
                )

            timing_summary[
                dataset
            ].append(
                {
                    **candidate,
                    "by_severity":
                        severity_rows,
                }
            )

    frame_gap_summary = {}

    for dataset in SUPPORTED_DATASETS:
        frame_gap_summary[
            dataset
        ] = {}

        for severity in SEVERITIES:
            frame_gap_summary[
                dataset
            ][severity] = (
                finalize_event_bucket(
                    frame_gap_events[
                        (
                            dataset,
                            severity,
                        )
                    ]
                )
            )

    status_rows = [
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
    ]

    rejection_rows = [
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
            not_admissible_counts.items()
        )
    ]

    return {
        "channel_freeze":
            freeze_summary,
        "timing":
            timing_summary,
        "frame_gap":
            frame_gap_summary,
        "attempt_status_counts":
            status_rows,
        "not_admissible_counts":
            rejection_rows,
        "regenerated_admissible_pair_count":
            regenerated_pairs,
        "unsupported_cause_emission_count":
            0,
        "runtime_hard_detectors_not_implemented": [
            "FRAME_REPEAT",
            "BUFFER_STALL",
            "FIFO_OVERRUN",
            "RANGE_CLIP",
        ],
    }


def build_channel_freeze_candidates(
    clean,
    corrupt,
    protocol,
):
    constraints = (
        protocol[
            "clean_constraints"
        ][
            "CHANNEL_FREEZE_SUSPECT"
        ]
    )

    persistence_grid = (
        protocol[
            "search_spaces"
        ][
            "CHANNEL_FREEZE_SUSPECT"
        ][
            "consecutive_deltas"
        ]
    )

    candidates = []

    for persistence in persistence_grid:
        p = int(
            persistence
        )

        clean_by_dataset = clean[
            "channel_freeze"
        ][p]

        infeasible = []

        for dataset in SUPPORTED_DATASETS:
            metrics = (
                clean_by_dataset[
                    dataset
                ]
            )

            if (
                metrics[
                    "suspect_onsets_per_hour"
                ]
                > constraints[
                    "maximum_onsets_per_hour_per_dataset"
                ]
            ):
                infeasible.append(
                    dataset
                    + ":suspect_onsets_per_hour"
                )

            if (
                metrics[
                    "time_in_suspect_fraction"
                ]
                > constraints[
                    "maximum_time_in_suspect_fraction_per_dataset"
                ]
            ):
                infeasible.append(
                    dataset
                    + ":time_in_suspect_fraction"
                )

            if (
                metrics[
                    "fraction_trials_with_any_suspect"
                ]
                > constraints[
                    "maximum_fraction_of_clean_trials_with_any_suspect_per_dataset"
                ]
            ):
                infeasible.append(
                    dataset
                    + ":fraction_trials_with_any_suspect"
                )

        corruption_by_dataset = {}

        dataset_macros = []
        all_latencies_samples = []
        all_latencies_ms = []

        for dataset in SUPPORTED_DATASETS:
            corruption_by_dataset[
                dataset
            ] = {}

            severity_recalls = []

            for severity in SEVERITIES:
                metrics = (
                    corrupt[
                        "channel_freeze"
                    ][
                        str(
                            p
                        )
                    ][dataset][
                        severity
                    ]
                )

                corruption_by_dataset[
                    dataset
                ][
                    severity
                ] = metrics

                recall = metrics[
                    "event_detection_recall"
                ]

                if recall is None:
                    raise RuntimeError(
                        "Missing CHANNEL_FREEZE denominator"
                    )

                severity_recalls.append(
                    float(
                        recall
                    )
                )

                all_latencies_samples.extend(
                    int(value)
                    for value
                    in metrics[
                        "confirmation_latency_samples"
                    ]
                )

                all_latencies_ms.extend(
                    float(value)
                    for value
                    in metrics[
                        "confirmation_latency_ms"
                    ]
                )

            dataset_macros.append(
                float(
                    np.mean(
                        severity_recalls
                    )
                )
            )

        candidate = {
            "absolute_tolerance":
                0.0,
            "consecutive_deltas":
                p,
            "clean_by_dataset":
                clean_by_dataset,
            "feasible":
                not infeasible,
            "infeasible_reasons":
                infeasible,
            "corruption_by_dataset_and_severity":
                corruption_by_dataset,
            "equal_dataset_weighted_macro_event_recall":
                float(
                    np.mean(
                        dataset_macros
                    )
                ),
            "confirmation_latency_event_count":
                len(
                    all_latencies_ms
                ),
            "median_confirmation_latency_samples":
                (
                    float(
                        np.median(
                            all_latencies_samples
                        )
                    )
                    if all_latencies_samples
                    else None
                ),
            "median_confirmation_latency_ms":
                (
                    float(
                        np.median(
                            all_latencies_ms
                        )
                    )
                    if all_latencies_ms
                    else None
                ),
        }

        candidates.append(
            candidate
        )

    return candidates


def build_timing_candidates(
    clean,
    corrupt,
    protocol,
):
    constraints = (
        protocol[
            "clean_constraints"
        ][
            "TIMING_OBSERVATION_ENVELOPE"
        ]
    )

    output = {}

    for dataset in SUPPORTED_DATASETS:
        rows = []

        clean_rows = clean[
            "timing"
        ][dataset]

        corrupt_rows = corrupt[
            "timing"
        ][dataset]

        if len(
            clean_rows
        ) != len(
            corrupt_rows
        ):
            raise RuntimeError(
                "Timing candidate grid mismatch"
            )

        for clean_row, corrupt_row in zip(
            clean_rows,
            corrupt_rows,
        ):
            if (
                clean_row[
                    "minimum_delta_ms"
                ]
                != corrupt_row[
                    "minimum_delta_ms"
                ]
                or
                clean_row[
                    "maximum_delta_ms"
                ]
                != corrupt_row[
                    "maximum_delta_ms"
                ]
            ):
                raise RuntimeError(
                    "Timing candidate ordering mismatch"
                )

            infeasible = []

            if (
                clean_row[
                    "timing_outside_intervals_per_hour"
                ]
                > constraints[
                    "maximum_outside_intervals_per_hour_per_dataset"
                ]
            ):
                infeasible.append(
                    "timing_outside_intervals_per_hour"
                )

            if (
                clean_row[
                    "fraction_trials_with_any_timing_outside"
                ]
                > constraints[
                    "maximum_fraction_of_clean_trials_with_any_outside_interval_per_dataset"
                ]
            ):
                infeasible.append(
                    "fraction_trials_with_any_timing_outside"
                )

            recalls = []

            for severity in SEVERITIES:
                recall = (
                    corrupt_row[
                        "by_severity"
                    ][severity][
                        "event_detection_recall"
                    ]
                )

                if recall is None:
                    raise RuntimeError(
                        "Missing TIMING_PERTURBATION denominator"
                    )

                recalls.append(
                    float(
                        recall
                    )
                )

            rows.append(
                {
                    "minimum_delta_ms":
                        clean_row[
                            "minimum_delta_ms"
                        ],
                    "maximum_delta_ms":
                        clean_row[
                            "maximum_delta_ms"
                        ],
                    "clean_metrics":
                        clean_row,
                    "feasible":
                        not infeasible,
                    "infeasible_reasons":
                        infeasible,
                    "corruption_by_severity":
                        corrupt_row[
                            "by_severity"
                        ],
                    "macro_event_recall":
                        float(
                            np.mean(
                                recalls
                            )
                        ),
                    "runtime_evidence_status":
                        "OBSERVATION_ONLY",
                    "hard_cause_promotion":
                        False,
                }
            )

        output[
            dataset
        ] = rows

    return output


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Deterministic frozen integrity calibration evaluator"
        )
    )

    parser.add_argument(
        "--clean-only",
        action="store_true",
        help=(
            "Evaluate only clean calibration streams and "
            "clean feasibility. Do not regenerate or evaluate "
            "P0 corruptions."
        ),
    )

    args = parser.parse_args()

    protocol = load_json(
        PROTOCOL_PATH
    )

    receipt = load_json(
        RECEIPT_PATH
    )

    manifest = load_json(
        MANIFEST_PATH
    )

    policy = load_json(
        POLICY_PATH
    )

    source_anchors = (
        verify_frozen_anchors(
            protocol,
            receipt,
            manifest,
            policy,
        )
    )

    source_anchors[
        "implementation_files_raw_sha256"
    ] = {
        "evaluator":
            file_sha256(
                Path(
                    __file__
                )
            ),
        "tests":
            (
                file_sha256(
                    ROOT
                    / "tests/test_integrity_calibration_v1.py"
                )
                if (
                    ROOT
                    / "tests/test_integrity_calibration_v1.py"
                ).is_file()
                else None
            ),
    }

    streams, load_audit = (
        load_clean_calibration_streams(
            manifest,
            policy,
        )
    )

    clean = evaluate_clean(
        streams,
        protocol,
    )

    clean_feasibility = (
        evaluate_clean_feasibility(
            clean,
            protocol,
        )
    )

    if args.clean_only:
        clean_result = {
            "result_id":
                "INTEGRITY_CALIBRATION_CLEAN_V1_CANDIDATE",
            "status":
                "clean_only_candidate_before_corruption_outcome_evaluation",
            "partition":
                "calibration",
            "source_anchors":
                source_anchors,
            "access_audit": {
                "calibration_raw_files_opened":
                    len(
                        load_audit
                    ),
                "development_raw_files_opened":
                    0,
                "final_test_raw_files_opened":
                    0,
                "task_model_outputs_used":
                    False,
                "ood_outputs_used":
                    False,
                "calibration_corruptions_regenerated":
                    False,
                "calibration_corruption_detector_outcomes_evaluated":
                    False,
                "final_test_corruptions_generated":
                    False,
            },
            "evaluation_contract": {
                "clean_streams_evaluated_first":
                    True,
                "corruption_recall_seen":
                    False,
                "channel_freeze_runtime_role":
                    "SUSPECT_ONLY",
                "timing_runtime_role":
                    "OBSERVATION_ONLY",
                "timing_hard_promotion":
                    False,
                "unsupported_hard_causes_enabled":
                    False,
            },
            "clean_metrics":
                clean,
            "clean_feasibility":
                clean_feasibility,
            "load_audit": {
                "calibration_trial_count":
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

        clean_result[
            "content_sha256"
        ] = artifact_content_digest(
            clean_result
        )

        CLEAN_RESULT_PATH.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        CLEAN_RESULT_PATH.write_text(
            json.dumps(
                clean_result,
                indent=2,
                sort_keys=True,
                allow_nan=False,
            )
            + "\n",
            encoding="utf-8",
        )

        print(
            "INTEGRITY_CALIBRATION_CLEAN_V1_CANDIDATE_WRITTEN = True"
        )
        print(
            "RESULT_PATH =",
            CLEAN_RESULT_PATH,
        )
        print(
            "RESULT_CONTENT_SHA256 =",
            clean_result[
                "content_sha256"
            ],
        )
        print(
            "CALIBRATION_RAW_FILES_OPENED =",
            len(
                load_audit
            ),
        )
        print(
            "CALIBRATION_CORRUPTIONS_REGENERATED = False"
        )
        print(
            "CALIBRATION_CORRUPTION_OUTCOMES_EVALUATED = False"
        )
        print(
            "FINAL_TEST_RAW_FILES_OPENED = 0"
        )
        print(
            "TASK_MODEL_OUTPUTS_USED = False"
        )
        print(
            "OOD_OUTPUTS_USED = False"
        )

        return

    corrupt = evaluate_corruptions(
        streams,
        manifest,
        protocol,
    )

    freeze_candidates = (
        build_channel_freeze_candidates(
            clean,
            corrupt,
            protocol,
        )
    )

    freeze_selection = (
        select_channel_freeze_candidate(
            freeze_candidates
        )
    )

    timing_candidates = (
        build_timing_candidates(
            clean,
            corrupt,
            protocol,
        )
    )

    timing_selection = {
        dataset:
            select_timing_candidate(
                timing_candidates[
                    dataset
                ]
            )
        for dataset
        in SUPPORTED_DATASETS
    }

    clean_hard_alert_count = sum(
        row[
            "hard_alert_count"
        ]
        for row
        in clean[
            "hard_cause"
        ].values()
    )

    hard_clean_constraint_ok = (
        clean_hard_alert_count == 0
    )

    frame_gap_kfall = (
        corrupt[
            "frame_gap"
        ][
            "KFALL"
        ]
    )

    qualified_denominator = sum(
        row[
            "episode_count"
        ]
        for row
        in frame_gap_kfall.values()
    )

    qualified_detected = sum(
        row[
            "detected_count"
        ]
        for row
        in frame_gap_kfall.values()
    )

    hard_emission_count = (
        qualified_detected
    )

    hard_correct_count = (
        qualified_detected
    )

    attribution = {
        "qualified_hard_cause_precision":
            (
                hard_correct_count
                / hard_emission_count
                if hard_emission_count
                else None
            ),
        "qualified_hard_cause_coverage":
            (
                qualified_detected
                / qualified_denominator
                if qualified_denominator
                else None
            ),
        "qualified_hard_cause_coverage_denominator_definition":
            "admissible KFALL FRAME_GAP P0 episodes",
        "unsupported_cause_emission_count":
            corrupt[
                "unsupported_cause_emission_count"
            ],
        "synthetic_truth_never_promoted":
            True,
    }

    selected_freeze = (
        freeze_selection[
            "selected_candidate"
        ]
    )

    operating_point_candidate = {
        "FRAME_GAP": {
            "KFALL":
                "HARD_QUALIFIED_FROM_RAW_FRAMECOUNTER",
            "UNIVRFALL":
                "NO_HARD_FRAME_GAP_FROM_UNVERIFIED_DERIVED_COUNTER",
            "tunable":
                False,
        },
        "CHANNEL_FREEZE_SUSPECT": {
            "enabled":
                selected_freeze
                is not None,
            "absolute_tolerance":
                (
                    None
                    if selected_freeze
                    is None
                    else selected_freeze[
                        "absolute_tolerance"
                    ]
                ),
            "consecutive_deltas":
                (
                    None
                    if selected_freeze
                    is None
                    else selected_freeze[
                        "consecutive_deltas"
                    ]
                ),
            "runtime_role":
                "SUSPECT_ONLY",
            "enters_hard_cause_set":
                False,
        },
        "TIMING_OBSERVATION_ENVELOPE": {
            dataset: {
                "selected":
                    timing_selection[
                        dataset
                    ][
                        "selected_candidate"
                    ],
                "runtime_role":
                    "OBSERVATION_ONLY",
                "hard_cause_promotion":
                    False,
            }
            for dataset
            in SUPPORTED_DATASETS
        },
        "unsupported_hard_causes_disabled": [
            "FRAME_REPEAT",
            "BUFFER_STALL",
            "FIFO_OVERRUN",
            "RANGE_CLIP",
            "ACQ_TIMING_VIOLATION",
        ],
    }

    result = {
        "result_id":
            "INTEGRITY_CALIBRATION_V1_CANDIDATE",
        "status":
            "candidate_before_integrity_operating_point_freeze",
        "partition":
            "calibration",
        "source_anchors":
            source_anchors,
        "access_audit": {
            "calibration_raw_files_opened":
                len(
                    load_audit
                ),
            "development_raw_files_opened":
                0,
            "final_test_raw_files_opened":
                0,
            "task_model_outputs_used":
                False,
            "ood_outputs_used":
                False,
            "final_test_corruptions_generated":
                False,
            "calibration_detector_outputs_evaluated":
                True,
        },
        "evaluation_contract": {
            "clean_feasibility_evaluated_before_corruption_objective_selection":
                True,
            "not_admissible_excluded_from_detection_denominator":
                True,
            "p0_truth_never_upgrades_runtime_evidence":
                True,
            "channel_freeze_runtime_role":
                "SUSPECT_ONLY",
            "timing_runtime_role":
                "OBSERVATION_ONLY",
            "timing_candidate_envelope_frozen_flag":
                False,
            "frame_repeat_hard_detector_used":
                False,
            "range_clip_hard_detector_used":
                False,
            "buffer_stall_detector_used":
                False,
            "fifo_overrun_detector_used":
                False,
            "latency_definition":
                "elapsed sample/timestamp distance from corrupt_anchor_index to first qualifying evidence within injected episode",
        },
        "clean_metrics":
            clean,
        "clean_feasibility":
            clean_feasibility,
        "corruption_metrics":
            corrupt,
        "channel_freeze_candidates":
            freeze_candidates,
        "channel_freeze_selection":
            freeze_selection,
        "timing_candidates":
            timing_candidates,
        "timing_selection":
            timing_selection,
        "hard_cause_clean_constraint": {
            "require_zero_clean_hard_alerts":
                True,
            "observed_clean_hard_alert_count":
                clean_hard_alert_count,
            "satisfied":
                hard_clean_constraint_ok,
        },
        "attribution":
            attribution,
        "operating_point_candidate":
            operating_point_candidate,
        "load_audit": {
            "calibration_trial_count":
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
        "INTEGRITY_CALIBRATION_V1_CANDIDATE_WRITTEN = True"
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
        "CALIBRATION_RAW_FILES_OPENED =",
        len(
            load_audit
        ),
    )
    print(
        "FINAL_TEST_RAW_FILES_OPENED = 0"
    )
    print(
        "TASK_MODEL_OUTPUTS_USED = False"
    )
    print(
        "OOD_OUTPUTS_USED = False"
    )
    print(
        "FINAL_TEST_CORRUPTIONS_GENERATED = False"
    )


if __name__ == "__main__":
    main()
