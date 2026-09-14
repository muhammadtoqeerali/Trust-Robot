from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from collections import Counter
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

CALIBRATION_MANIFEST = (
    ROOT
    / "data/manifests/"
      "p0_calibration_spec_manifest_v1_candidate.json"
)

OPERATING_POINT = (
    ROOT
    / "configs/integrity/"
      "integrity_operating_point_v1.json"
)

OUTPUT = (
    ROOT
    / "data/manifests/"
      "p0_final_test_spec_manifest_v1_candidate.json"
)

DEV_GENERATOR = (
    ROOT
    / "experiments/01_integrity_p0/"
      "build_p0_development_manifest_v1.py"
)

EXPECTED_OPERATING_POINT_CONTENT_SHA256 = (
    "02c7d6dabb5951409dd34491384fc2a800ef02a7b1ad0006098845925d847f59"
)

EXPECTED_OPERATING_POINT_TAG_COMMIT = (
    "9ac878ea6a40e8c01a60e42e602a1fa9fc688d3b"
)

EXPECTED_CALIBRATION_MANIFEST_CONTENT_SHA256 = (
    "f95ada2da8355b21f43aac6d7d9438eeebf70305f21e7a1e3a1d66c11fd498a6"
)

EXPECTED_CALIBRATION_SPEC_TAG_COMMIT = (
    "2bbd0c771601fcc9ced578e389deb42df46ffc33"
)

DEV_POLICY_INPUTS = (
    ROOT
    / "experiments/01_integrity_p0/"
      "derive_p0_dev_policy_inputs_v1.py"
)

INJECTION_P0 = (
    ROOT
    / "src/imu_reliability/injection/"
      "p0.py"
)

INJECTION_TYPES = (
    ROOT
    / "src/imu_reliability/injection/"
      "types.py"
)

EXPECTED_DEPENDENCY_RAW_SHA256 = {
    "experiments/01_integrity_p0/build_p0_development_manifest_v1.py":
        "b3c5b87474efaf0517986bfbbe72bf2755679e24b948c871cfdd78765bdfbe91",

    "experiments/01_integrity_p0/derive_p0_dev_policy_inputs_v1.py":
        "8451ae3e43ebd345598c363e7fd6539a30234889f01aa04e3863d8d10055f8cc",

    "src/imu_reliability/injection/p0.py":
        "dfacc36671b556f121cf39b0b2c1b720b1b1ad372cc44fb381173f8b7a0bb367",

    "src/imu_reliability/injection/types.py":
        "b8c1808de1f4a7e3635d5aac8de8462964d8004036c24da46f7627aa55e5fe61",
}

EXPECTED_POLICY_CONTENT_SHA256 = (
    "cb33c32951930453db550dfd02deab67a9eb51e851edf1a186e7faa4a5432220"
)

EXPECTED_FINAL_TEST_TOTAL = 1116
EXPECTED_TRIAL_COUNT = 1108
EXPECTED_EXCLUDED_COUNT = 8
EXPECTED_ATTEMPT_COUNT = 16620

EXPECTED_DATASET_COUNTS = {
    "KFALL":
        932,
    "UNIVRFALL":
        176,
}

EXPECTED_EXCLUDED_DATASET_COUNTS = {
    "ONFIELD":
        8,
}

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

FAILED_PREFLIGHT_GENERATOR_TAG = (
    "p0-final-test-generator-v1"
)

EXPECTED_FAILED_PREFLIGHT_COMMIT = (
    "6c0bc4a942e55c769c61a1c1d3503707e9ef4132"
)

PREVIOUS_PREFLIGHT_GENERATOR_TAG = (
    "p0-final-test-generator-v1b"
)

EXPECTED_PREVIOUS_PREFLIGHT_COMMIT = (
    "122dd635aff580a88370941fa24b5321a0916cea"
)

GENERATOR_TAG = (
    "p0-final-test-generator-v1c"
)


def raw_file_sha256(
    path: Path,
) -> str:
    return sha256(
        path.read_bytes()
    ).hexdigest()


def verify_preimport_dependency_provenance():
    dependencies = (
        DEV_GENERATOR,
        DEV_POLICY_INPUTS,
        INJECTION_P0,
        INJECTION_TYPES,
    )

    observed = {}

    for dependency in dependencies:
        relative = str(
            dependency.relative_to(
                ROOT
            )
        )

        if not dependency.is_file():
            raise RuntimeError(
                "Missing frozen generation dependency: "
                + relative
            )

        actual = raw_file_sha256(
            dependency
        )

        expected = (
            EXPECTED_DEPENDENCY_RAW_SHA256[
                relative
            ]
        )

        if actual != expected:
            raise RuntimeError(
                "Generation dependency changed before "
                "final-test raw access: "
                f"{relative}: "
                f"{actual} != {expected}"
            )

        observed[
            relative
        ] = actual

    calibration_tag_commit = (
        subprocess.check_output(
            [
                "git",
                "rev-parse",
                "p0-calibration-spec-v1^{commit}",
            ],
            cwd=ROOT,
            text=True,
        ).strip()
    )

    if (
        calibration_tag_commit
        != EXPECTED_CALIBRATION_SPEC_TAG_COMMIT
    ):
        raise RuntimeError(
            "p0-calibration-spec-v1 tag moved"
        )

    relative_paths = [
        str(
            dependency.relative_to(
                ROOT
            )
        )
        for dependency
        in dependencies
    ]

    diff = subprocess.run(
        [
            "git",
            "diff",
            "--quiet",
            EXPECTED_CALIBRATION_SPEC_TAG_COMMIT,
            "HEAD",
            "--",
            *relative_paths,
        ],
        cwd=ROOT,
        check=False,
    )

    if diff.returncode != 0:
        raise RuntimeError(
            "Generation dependencies differ from "
            "the calibration-spec freeze"
        )

    status = subprocess.check_output(
        [
            "git",
            "status",
            "--porcelain",
            "--",
            *relative_paths,
        ],
        cwd=ROOT,
        text=True,
    )

    if status.strip():
        raise RuntimeError(
            "Generation dependency worktree is dirty: "
            + status.strip()
        )

    return {
        "calibration_spec_tag":
            "p0-calibration-spec-v1",

        "calibration_spec_tag_commit":
            calibration_tag_commit,

        "dependencies_identical_to_calibration_freeze":
            True,

        "dependency_raw_sha256":
            observed,
    }


PREIMPORT_DEPENDENCY_ANCHORS = (
    verify_preimport_dependency_provenance()
)


def load_dev_generator():
    spec = (
        importlib.util
        .spec_from_file_location(
            "p0_development_generator_v1_for_final_test",
            DEV_GENERATOR,
        )
    )

    if (
        spec is None
        or spec.loader is None
    ):
        raise RuntimeError(
            "Unable to load frozen development P0 generator"
        )

    module = (
        importlib.util
        .module_from_spec(
            spec
        )
    )

    spec.loader.exec_module(
        module
    )

    return module


DEV = load_dev_generator()


def canonical_digest(
    payload: Any,
) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode(
        "utf-8"
    )

    return sha256(
        raw
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


def verify_hash(
    data: dict[str, Any],
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
            "Content hash mismatch: "
            f"{stored} != {computed}"
        )

    return stored


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


def reconstructed_trial_id(
    lineage_row: dict[str, Any],
) -> str:
    return (
        str(
            lineage_row[
                "dataset"
            ]
        )
        + ":"
        + str(
            lineage_row[
                "relative_trial"
            ]
        )
    )


def build_lineage_index(
    lineage: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    rows = lineage[
        "trials"
    ]

    if not isinstance(
        rows,
        list,
    ):
        raise RuntimeError(
            "Frozen lineage trials are not a list"
        )

    index = {}

    for row in rows:
        trial_id = (
            reconstructed_trial_id(
                row
            )
        )

        if trial_id in index:
            raise RuntimeError(
                "Duplicate lineage trial: "
                + trial_id
            )

        index[
            trial_id
        ] = row

    return index


def select_final_test_rows(
    registry: dict[str, Any],
):
    final_rows = [
        row
        for row in registry[
            "records"
        ]
        if row[
            "partition"
        ]
        == "final_test"
    ]

    selected = [
        row
        for row in final_rows
        if row[
            "acquisition_scope"
        ][
            "acquisition_p0_eligible"
        ]
    ]

    excluded = [
        row
        for row in final_rows
        if not row[
            "acquisition_scope"
        ][
            "acquisition_p0_eligible"
        ]
    ]

    selected.sort(
        key=lambda row:
            row[
                "trial_id"
            ]
    )

    excluded.sort(
        key=lambda row:
            row[
                "trial_id"
            ]
    )

    return (
        final_rows,
        selected,
        excluded,
    )


def validate_final_test_constraints(
    row: dict[str, Any],
) -> None:
    constraints = row[
        "prospective_constraints"
    ]

    required_false = (
        "final_test_outcomes_available_for_tuning",
        "may_change_corruption_policy_after_outcome_review",
        "may_define_corruption_policy",
        "may_select_ood_operating_point",
        "may_select_persistence",
        "may_tune_detector_thresholds",
    )

    for key in required_false:
        if constraints[
            key
        ] is not False:
            raise RuntimeError(
                f"{row['trial_id']} unexpectedly allows "
                f"{key}"
            )

    if constraints[
        "corruption_instance_created_at_registry_freeze"
    ] is not False:
        raise RuntimeError(
            "Final-test corruption was already created "
            "at registry freeze for "
            + row[
                "trial_id"
            ]
        )

    scope = row[
        "acquisition_scope"
    ]

    if scope[
        "raw_pair_verified"
    ] is not True:
        raise RuntimeError(
            "Selected final-test trial lacks verified raw pair: "
            + row[
                "trial_id"
            ]
        )

    if set(
        scope[
            "p0_truth_families_allowed"
        ]
    ) != set(
        FAMILY_ORDER
    ):
        raise RuntimeError(
            "Selected final-test trial has changed P0 family set: "
            + row[
                "trial_id"
            ]
        )


def arrays_equal_or_none(
    left,
    right,
) -> bool:
    if (
        left is None
        or right is None
    ):
        return (
            left is None
            and right is None
        )

    return np.array_equal(
        left,
        right,
    )


def verify_frozen_sources(
    *,
    policy,
    registry,
    lineage,
    calibration_manifest,
    operating_point,
):
    policy_sha = verify_hash(
        policy
    )

    if (
        policy_sha
        != EXPECTED_POLICY_CONTENT_SHA256
    ):
        raise RuntimeError(
            "Frozen P0 policy changed"
        )

    calibration_manifest_sha = (
        verify_hash(
            calibration_manifest
        )
    )

    if (
        calibration_manifest_sha
        != EXPECTED_CALIBRATION_MANIFEST_CONTENT_SHA256
    ):
        raise RuntimeError(
            "Frozen calibration P0 manifest changed"
        )

    registry_sha = verify_hash(
        registry
    )

    lineage_sha = verify_hash(
        lineage
    )

    expected_registry_sha = (
        calibration_manifest[
            "source_registry"
        ][
            "content_sha256"
        ]
    )

    expected_lineage_sha = (
        calibration_manifest[
            "source_lineage"
        ][
            "content_sha256"
        ]
    )

    expected_policy_from_calibration = (
        calibration_manifest[
            "source_policy"
        ][
            "content_sha256"
        ]
    )

    if (
        registry_sha
        != expected_registry_sha
    ):
        raise RuntimeError(
            "Evaluation registry differs from "
            "frozen calibration source"
        )

    if (
        lineage_sha
        != expected_lineage_sha
    ):
        raise RuntimeError(
            "Lineage differs from frozen calibration source"
        )

    if (
        policy_sha
        != expected_policy_from_calibration
    ):
        raise RuntimeError(
            "P0 policy differs from frozen calibration source"
        )

    operating_point_sha = (
        verify_hash(
            operating_point
        )
    )

    if (
        operating_point_sha
        != EXPECTED_OPERATING_POINT_CONTENT_SHA256
    ):
        raise RuntimeError(
            "Frozen integrity operating point changed"
        )

    op_tag_commit = git(
        "rev-parse",
        "integrity-operating-point-v1^{commit}",
    )

    if (
        op_tag_commit
        != EXPECTED_OPERATING_POINT_TAG_COMMIT
    ):
        raise RuntimeError(
            "integrity-operating-point-v1 tag moved"
        )

    ancestry = subprocess.run(
        [
            "git",
            "merge-base",
            "--is-ancestor",
            EXPECTED_OPERATING_POINT_TAG_COMMIT,
            "HEAD",
        ],
        cwd=ROOT,
        check=False,
    )

    if ancestry.returncode != 0:
        raise RuntimeError(
            "Frozen operating point is not an ancestor of HEAD"
        )

    if operating_point[
        "freeze_contract"
    ][
        "final_test_data_used_for_selection"
    ] is not False:
        raise RuntimeError(
            "Operating point says final-test data influenced selection"
        )

    if operating_point[
        "freeze_contract"
    ][
        "final_test_raw_files_opened"
    ] != 0:
        raise RuntimeError(
            "Operating-point freeze boundary already violated"
        )

    if operating_point[
        "freeze_contract"
    ][
        "final_test_corruptions_generated"
    ] is not False:
        raise RuntimeError(
            "Operating point says final-test corruptions "
            "already existed at freeze"
        )

    if operating_point[
        "CHANNEL_FREEZE_SUSPECT"
    ][
        "enabled"
    ] is not False:
        raise RuntimeError(
            "Frozen CHANNEL_FREEZE main decision changed"
        )

    kfall_timing = operating_point[
        "TIMING_OBSERVATION_ENVELOPE"
    ][
        "KFALL"
    ]

    univr_timing = operating_point[
        "TIMING_OBSERVATION_ENVELOPE"
    ][
        "UNIVRFALL"
    ]

    if (
        kfall_timing[
            "minimum_delta_ms"
        ],
        kfall_timing[
            "maximum_delta_ms"
        ],
    ) != (
        5.0,
        15.0,
    ):
        raise RuntimeError(
            "Frozen KFall timing envelope changed"
        )

    if (
        univr_timing[
            "minimum_delta_ms"
        ],
        univr_timing[
            "maximum_delta_ms"
        ],
    ) != (
        -0.5,
        20.5,
    ):
        raise RuntimeError(
            "Frozen UniVR timing envelope changed"
        )

    if (
        kfall_timing[
            "hard_cause_promotion"
        ]
        or
        univr_timing[
            "hard_cause_promotion"
        ]
    ):
        raise RuntimeError(
            "Timing was promoted to a hard cause"
        )

    policy_tag_commit = git(
        "rev-parse",
        "p0-corruption-policy-v1^{}",
    )

    return {
        "policy_content_sha256":
            policy_sha,
        "policy_tag_commit":
            policy_tag_commit,
        "registry_content_sha256":
            registry_sha,
        "lineage_content_sha256":
            lineage_sha,
        "calibration_manifest_content_sha256":
            calibration_manifest_sha,
        "operating_point_content_sha256":
            operating_point_sha,
        "operating_point_tag_commit":
            op_tag_commit,
    }


def verify_generator_is_frozen() -> str:
    failed_preflight_commit = git(
        "rev-parse",
        f"{FAILED_PREFLIGHT_GENERATOR_TAG}^{{commit}}",
    )

    if (
        failed_preflight_commit
        != EXPECTED_FAILED_PREFLIGHT_COMMIT
    ):
        raise RuntimeError(
            "Failed preflight generator provenance tag moved"
        )

    previous_preflight_commit = git(
        "rev-parse",
        f"{PREVIOUS_PREFLIGHT_GENERATOR_TAG}^{{commit}}",
    )

    if (
        previous_preflight_commit
        != EXPECTED_PREVIOUS_PREFLIGHT_COMMIT
    ):
        raise RuntimeError(
            "v1b preflight generator provenance tag moved"
        )

    tag_commit = git(
        "rev-parse",
        f"{GENERATOR_TAG}^{{commit}}",
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

    if (
        tag_commit
        != script_commit
    ):
        raise RuntimeError(
            "Final-test generator is not frozen at "
            f"{GENERATOR_TAG}"
        )

    return tag_commit


def main():
    generator_tag_commit = (
        verify_generator_is_frozen()
    )

    policy = json.loads(
        POLICY.read_text(
            encoding="utf-8"
        )
    )

    registry = json.loads(
        REGISTRY.read_text(
            encoding="utf-8"
        )
    )

    lineage = json.loads(
        LINEAGE.read_text(
            encoding="utf-8"
        )
    )

    calibration_manifest = json.loads(
        CALIBRATION_MANIFEST.read_text(
            encoding="utf-8"
        )
    )

    operating_point = json.loads(
        OPERATING_POINT.read_text(
            encoding="utf-8"
        )
    )

    anchors = verify_frozen_sources(
        policy=policy,
        registry=registry,
        lineage=lineage,
        calibration_manifest=
            calibration_manifest,
        operating_point=
            operating_point,
    )

    if tuple(
        policy[
            "severity_order"
        ]
    ) != SEVERITY_ORDER:
        raise RuntimeError(
            "Frozen severity ordering changed"
        )

    if set(
        policy[
            "families"
        ]
    ) != set(
        FAMILY_ORDER
    ):
        raise RuntimeError(
            "Frozen P0 family set changed"
        )

    if policy[
        "prospective_constraints"
    ][
        "final_test_may_modify_policy"
    ] is not False:
        raise RuntimeError(
            "Frozen policy unexpectedly allows "
            "final-test modification"
        )

    (
        final_rows,
        selected,
        excluded,
    ) = select_final_test_rows(
        registry
    )

    if len(
        final_rows
    ) != EXPECTED_FINAL_TEST_TOTAL:
        raise RuntimeError(
            "Unexpected total final-test trial count: "
            f"{len(final_rows)}"
        )

    if len(
        selected
    ) != EXPECTED_TRIAL_COUNT:
        raise RuntimeError(
            "Unexpected acquisition-P0-eligible "
            "final-test count: "
            f"{len(selected)}"
        )

    if len(
        excluded
    ) != EXPECTED_EXCLUDED_COUNT:
        raise RuntimeError(
            "Unexpected excluded final-test count: "
            f"{len(excluded)}"
        )

    dataset_counts = Counter(
        row[
            "dataset"
        ]
        for row in selected
    )

    if dict(
        dataset_counts
    ) != EXPECTED_DATASET_COUNTS:
        raise RuntimeError(
            "Unexpected eligible dataset counts: "
            f"{dict(dataset_counts)}"
        )

    excluded_dataset_counts = Counter(
        row[
            "dataset"
        ]
        for row in excluded
    )

    if dict(
        excluded_dataset_counts
    ) != EXPECTED_EXCLUDED_DATASET_COUNTS:
        raise RuntimeError(
            "Unexpected excluded dataset counts: "
            f"{dict(excluded_dataset_counts)}"
        )

    for row in selected:
        validate_final_test_constraints(
            row
        )

    for row in excluded:
        if row[
            "dataset"
        ] != "ONFIELD":
            raise RuntimeError(
                "Unexpected excluded final-test dataset"
            )

        if row[
            "acquisition_scope"
        ][
            "raw_pair_verified"
        ] is not False:
            raise RuntimeError(
                "Excluded OnField row unexpectedly has "
                "verified raw pairing"
            )

        if row[
            "acquisition_scope"
        ][
            "p0_truth_families_allowed"
        ] != []:
            raise RuntimeError(
                "Excluded OnField row unexpectedly allows "
                "P0 truth families"
            )

    lineage_by_id = (
        build_lineage_index(
            lineage
        )
    )

    missing = [
        row[
            "trial_id"
        ]
        for row in selected
        if row[
            "trial_id"
        ]
        not in lineage_by_id
    ]

    if missing:
        raise RuntimeError(
            "Missing final-test lineage records: "
            f"{missing[:10]}"
        )

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

        lineage_row = lineage_by_id[
            trial_id
        ]

        original = lineage_row[
            "raw_pairing"
        ][
            "original"
        ]

        if len(
            original
        ) != 1:
            raise RuntimeError(
                "Expected exactly one raw original for "
                + trial_id
            )

        expected_counter_qualified = (
            dataset
            == "KFALL"
        )

        if bool(
            lineage_row[
                "raw_pairing"
            ].get(
                "frame_counter_hard_qualified",
                False,
            )
        ) != expected_counter_qualified:
            raise RuntimeError(
                "Frozen frame-counter provenance changed for "
                + trial_id
            )

        (
            clean,
            raw_path,
            schema,
        ) = DEV.load_clean_stream(
            registry_row,
            lineage_row,
            policy,
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

        if not model_coupled:
            raise RuntimeError(
                "Selected final-test trial is not "
                "model-coupled eligible: "
                + trial_id
            )

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
                "frame_counter_hard_qualified":
                    expected_counter_qualified,
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

                (
                    built,
                    reason,
                    rejected,
                ) = DEV.build_spec(
                    clean=clean,
                    dataset=dataset,
                    trial_id=trial_id,
                    family=family,
                    severity=severity,
                    policy=policy,
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
                        "final_test",
                    "model_coupled_p0_eligible":
                        model_coupled,
                }

                if built is None:
                    attempts.append(
                        {
                            **base,
                            "status":
                                "NOT_ADMISSIBLE",
                            "reason":
                                reason,
                            "selection":
                                rejected,
                        }
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

                if family == "TIMING_PERTURBATION":
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

                spec = DEV.P0InjectionSpec(
                    kind=DEV.P0CorruptionKind(
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
                    pair = DEV.apply_p0_injection(
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
                            "Unexpected sample-count change for "
                            + family
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
                            family
                            + " changed timestamps"
                        )

                    if not arrays_equal_or_none(
                        pair.corrupt.counters,
                        clean.counters,
                    ):
                        raise RuntimeError(
                            family
                            + " changed counters"
                        )

                if family == "TIMING_PERTURBATION":
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
                        clean.timestamps[
                            start
                        ]
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
                            f"{trial_id}: observed="
                            f"{observed_extra_ms} ms; expected="
                            f"{expected_extra_ms} ms"
                        )

                truth = pair.truths[
                    0
                ]

                attempts.append(
                    {
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
                f"processed {trial_number}/"
                f"{len(selected)} "
                "final-test trials",
                flush=True,
            )

    if len(
        attempts
    ) != EXPECTED_ATTEMPT_COUNT:
        raise RuntimeError(
            "Final-test attempt-count mismatch: "
            f"{len(attempts)}"
        )

    if (
        raw_files_opened
        != EXPECTED_TRIAL_COUNT
    ):
        raise RuntimeError(
            "Unexpected final-test raw-file count"
        )

    if (
        model_coupled_count
        != EXPECTED_TRIAL_COUNT
    ):
        raise RuntimeError(
            "Unexpected model-coupled final-test count"
        )

    payload = {
        "manifest_id":
            "P0_FINAL_TEST_SPEC_MANIFEST_V1",

        "status":
            "candidate_before_final_test_spec_receipt_freeze",

        "partition":
            "final_test",

        "source_operating_point": {
            "path":
                str(
                    OPERATING_POINT.relative_to(
                        ROOT
                    )
                ),
            "content_sha256":
                anchors[
                    "operating_point_content_sha256"
                ],
            "tag":
                "integrity-operating-point-v1",
            "tag_commit":
                anchors[
                    "operating_point_tag_commit"
                ],
        },

        "source_policy": {
            "path":
                str(
                    POLICY.relative_to(
                        ROOT
                    )
                ),
            "content_sha256":
                anchors[
                    "policy_content_sha256"
                ],
            "tag":
                "p0-corruption-policy-v1",
            "tag_commit":
                anchors[
                    "policy_tag_commit"
                ],
        },

        "source_calibration_manifest": {
            "path":
                str(
                    CALIBRATION_MANIFEST.relative_to(
                        ROOT
                    )
                ),
            "content_sha256":
                anchors[
                    "calibration_manifest_content_sha256"
                ],
        },

        "source_registry": {
            "path":
                str(
                    REGISTRY.relative_to(
                        ROOT
                    )
                ),
            "content_sha256":
                anchors[
                    "registry_content_sha256"
                ],
        },

        "source_lineage": {
            "path":
                str(
                    LINEAGE.relative_to(
                        ROOT
                    )
                ),
            "content_sha256":
                anchors[
                    "lineage_content_sha256"
                ],
        },

        "source_generator": {
            "path":
                str(
                    Path(
                        __file__
                    ).relative_to(
                        ROOT
                    )
                ),
            "tag":
                GENERATOR_TAG,
            "tag_commit":
                generator_tag_commit,
            "supersedes_failed_preflight_tag":
                FAILED_PREFLIGHT_GENERATOR_TAG,
            "failed_preflight_tag_commit":
                EXPECTED_FAILED_PREFLIGHT_COMMIT,
            "failed_preflight_reason":
                "TEST_IMPORT_PATH_BOOTSTRAP_MISSING_NO_FINAL_TEST_RAW_ACCESS",

            "previous_preflight_tag":
                PREVIOUS_PREFLIGHT_GENERATOR_TAG,

            "previous_preflight_tag_commit":
                EXPECTED_PREVIOUS_PREFLIGHT_COMMIT,

            "dependency_provenance":
                PREIMPORT_DEPENDENCY_ANCHORS,
        },

        "generation_contract": {
            "final_test_trials_only":
                True,
            "total_final_test_registry_trials":
                EXPECTED_FINAL_TEST_TOTAL,
            "excluded_unverified_onfield_trials":
                EXPECTED_EXCLUDED_COUNT,
            "development_raw_files_opened":
                0,
            "calibration_raw_files_opened":
                0,
            "final_test_raw_files_opened":
                raw_files_opened,
            "integrity_operating_point_already_frozen":
                True,
            "integrity_operating_point_modified":
                False,
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
            "attempt_every_eligible_trial_family_severity":
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
            "final_test_outcomes_used_for_tuning":
                False,
            "channel_freeze_runtime_suspect_remains_disabled":
                True,
            "timing_runtime_role_remains_observation_only":
                True,
        },

        "final_test_registry_trial_count":
            len(
                final_rows
            ),

        "final_test_trial_count":
            len(
                trials
            ),

        "excluded_final_test_trial_count":
            len(
                excluded
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

        "excluded_dataset_trial_counts":
            dict(
                excluded_dataset_counts
            ),

        "excluded_trials": [
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
                "raw_pairing_status":
                    row[
                        "raw_pairing_status"
                    ],
                "reason":
                    "ACQUISITION_P0_NOT_ELIGIBLE_RAW_TRIAL_MAPPING_UNVERIFIED",
            }
            for row in excluded
        ],

        "trials":
            trials,

        "attempts":
            attempts,

        "status_counts": [
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

        "not_admissible_reason_counts": [
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
                reason_counts.items()
            )
        ],
    }

    payload[
        "content_sha256"
    ] = artifact_content_digest(
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
            allow_nan=False,
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
        if status
        == "ADMISSIBLE"
    )

    rejected_total = (
        EXPECTED_ATTEMPT_COUNT
        - admissible_total
    )

    print()
    print(
        "=" * 108
    )
    print(
        "P0 FINAL-TEST SPECIFICATION SUMMARY"
    )
    print(
        "=" * 108
    )

    print(
        "final_test_registry_trial_count =",
        len(
            final_rows
        ),
    )
    print(
        "final_test_trial_count =",
        len(
            trials
        ),
    )
    print(
        "excluded_final_test_trial_count =",
        len(
            excluded
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
        "excluded_dataset_trial_counts =",
        dict(
            excluded_dataset_counts
        ),
    )
    print(
        "development_raw_files_opened = 0"
    )
    print(
        "calibration_raw_files_opened = 0"
    )
    print(
        "final_test_raw_files_opened =",
        raw_files_opened,
    )

    print()
    print(
        "status_counts:"
    )

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
        print(
            "  NONE"
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
        "P0_FINAL_TEST_SPEC_MANIFEST_V1_CANDIDATE_PASS = True"
    )


if __name__ == "__main__":
    main()
