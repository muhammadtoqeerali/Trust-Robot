from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from collections import Counter, defaultdict
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

import numpy as np
import torch


ROOT = Path(
    __file__
).resolve().parents[2]


EVALUATOR_TAG = (
    "ood-final-test-evaluator-v1"
)

FINAL_TEST_PROTOCOL_TAG = (
    "ood-final-test-protocol-v1"
)

FINAL_TEST_PROTOCOL_COMMIT = (
    "39cf47d0d46c4c6e5518794b7ffaa98fa1360ebe"
)

FINAL_TEST_PROTOCOL_CONTENT_SHA256 = (
    "d287f181b3826d7c868ea60f15da187e"
    "86337733a481cbf7732c3afb308ce464"
)

FINAL_TEST_PROTOCOL_RAW_SHA256 = (
    "d04a591bba0f820c21d421b22d5956cb"
    "693f641242af998103d2fb9edc03d6f2"
)

OOD_OPERATING_POINT_COMMIT = (
    "fea9316d8510a5841baba48d273973e0267e4b28"
)

OOD_CALIBRATION_RESULT_COMMIT = (
    "fea9316d8510a5841baba48d273973e0267e4b28"
)

OOD_CALIBRATION_EVALUATOR_V1B_COMMIT = (
    "d879fbbfa512194b67f6a5087d0f76c7baa50227"
)

OOD_CALIBRATION_EVALUATOR_V1B_RAW_SHA256 = (
    "6462829b7ffee3ca19dc25b7a605a3b7"
    "dd38ddf6bfb10a34ca8d098c0ae415df"
)

INTEGRITY_FINAL_RESULT_COMMIT = (
    "b1aaa28a5cd2222bd3acc7d5d86289ba9fd71c74"
)

BASELINE_COMMIT = (
    "d6fe744b292139d18fd4dee37c96066bcf2d38c6"
)

REGISTRY_COMMIT = (
    "416cc9d8895646c38edc6b7be1dfdc042d0c2219"
)

FINAL_OP_RAW_SHA256 = (
    "46e343b5d44898f17942f8ba28257cd1"
    "389fc8bacf3f09026aeb226099ff3081"
)

FINAL_OP_CONTENT_SHA256 = (
    "0f23b8e152058d4f160861348e7fb295"
    "566af6be55083242db783a9a8e387747"
)

FROZEN_THRESHOLD = (
    0.00914505124092102
)

EXPECTED_FINAL_ROWS = (
    1116
)

EXPECTED_FINAL_WINDOWS = (
    366507
)

EXPECTED_DATASET_ROWS = {
    "KFALL":
        932,

    "UNIVRFALL":
        176,

    "ONFIELD":
        8,
}

EXPECTED_DATASET_WINDOWS = {
    "KFALL":
        27068,

    "UNIVRFALL":
        7532,

    "ONFIELD":
        331907,
}

BATCH_SIZE = (
    2048
)


FINAL_TEST_PROTOCOL = (
    ROOT
    / "configs/ood/"
      "ood_final_test_protocol_v1.json"
)

FINAL_OP = (
    ROOT
    / "configs/ood/"
      "ood_operating_point_v1.json"
)

REGISTRY = (
    ROOT
    / "data/manifests/"
      "reliability_eval_registry_v1.json"
)

V1B_SOURCE = (
    ROOT
    / "experiments/03_ood/"
      "evaluate_ood_calibration_v1b.py"
)

RESULT = (
    ROOT
    / "results/raw/"
      "ood_final_test_v1_candidate.json"
)

FINAL_RECEIPT = (
    ROOT
    / "data/manifests/"
      "ood_final_test_result_receipt_v1.json"
)


def canonical_digest(
    payload,
):
    normalized = json.loads(
        json.dumps(
            payload,
            separators=(",", ":"),
            allow_nan=False,
        )
    )

    return sha256(
        json.dumps(
            normalized,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def file_sha256(
    file_path: Path,
) -> str:
    return sha256(
        file_path.read_bytes()
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


def load_v1b_module():
    if not V1B_SOURCE.is_file():
        raise RuntimeError(
            "Frozen calibration evaluator v1b source absent"
        )

    if (
        file_sha256(
            V1B_SOURCE
        )
        != OOD_CALIBRATION_EVALUATOR_V1B_RAW_SHA256
    ):
        raise RuntimeError(
            "Frozen calibration evaluator v1b bytes changed"
        )

    module_name = (
        "_ood_calibration_evaluator_v1b_frozen_dependency"
    )

    existing = sys.modules.get(
        module_name
    )

    if existing is not None:
        return existing

    spec = importlib.util.spec_from_file_location(
        module_name,
        V1B_SOURCE,
    )

    if (
        spec is None
        or spec.loader is None
    ):
        raise RuntimeError(
            "Unable to load frozen evaluator v1b dependency"
        )

    module = importlib.util.module_from_spec(
        spec
    )

    sys.modules[
        module_name
    ] = module

    spec.loader.exec_module(
        module
    )

    return module


def verify_content_hash(
    data,
    expected_content_sha,
):
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
            "Canonical content hash mismatch"
        )

    if stored != expected_content_sha:
        raise RuntimeError(
            "Frozen canonical content changed"
        )

    return stored


def load_final_test_protocol():
    if not FINAL_TEST_PROTOCOL.is_file():
        raise RuntimeError(
            "Frozen final-test OOD protocol absent"
        )

    if (
        file_sha256(
            FINAL_TEST_PROTOCOL
        )
        != FINAL_TEST_PROTOCOL_RAW_SHA256
    ):
        raise RuntimeError(
            "Frozen final-test protocol raw SHA changed"
        )

    data = json.loads(
        FINAL_TEST_PROTOCOL.read_text()
    )

    verify_content_hash(
        data,
        FINAL_TEST_PROTOCOL_CONTENT_SHA256,
    )

    if (
        data[
            "protocol_id"
        ]
        != "OOD_FINAL_TEST_PROTOCOL_V1"
    ):
        raise RuntimeError(
            "Unexpected final-test protocol identity"
        )

    if (
        data[
            "frozen_ood_operating_point"
        ][
            "selected_method"
        ]
        != "top_two_logit_margin"
    ):
        raise RuntimeError(
            "Frozen final-test OOD method changed"
        )

    if float(
        data[
            "frozen_ood_operating_point"
        ][
            "threshold"
        ]
    ) != FROZEN_THRESHOLD:
        raise RuntimeError(
            "Frozen final-test threshold changed"
        )

    boundary = data[
        "exposure_boundary_at_protocol_freeze"
    ]

    for key in (
        "final_test_sensor_arrays_opened",
        "final_test_label_arrays_opened",
        "checkpoint_deserialized_for_final_test_ood",
        "protected_model_loaded_for_final_test_ood",
        "protected_model_forward_executed_for_final_test_ood",
        "final_test_task_logits_read",
        "final_test_features_read",
        "final_test_ood_margins_computed",
        "final_test_ood_states_computed",
        "final_test_ood_outputs_read",
    ):
        if boundary[
            key
        ] is not False:
            raise RuntimeError(
                f"Final-test protocol exposure boundary changed: {key}"
            )

    return data


def load_frozen_operating_point():
    if not FINAL_OP.is_file():
        raise RuntimeError(
            "Frozen OOD operating point absent"
        )

    if (
        file_sha256(
            FINAL_OP
        )
        != FINAL_OP_RAW_SHA256
    ):
        raise RuntimeError(
            "Frozen OOD operating-point raw bytes changed"
        )

    data = json.loads(
        FINAL_OP.read_text()
    )

    verify_content_hash(
        data,
        FINAL_OP_CONTENT_SHA256,
    )

    if (
        data[
            "selected_method"
        ]
        != "top_two_logit_margin"
    ):
        raise RuntimeError(
            "Frozen OOD method changed"
        )

    if float(
        data[
            "threshold"
        ]
    ) != FROZEN_THRESHOLD:
        raise RuntimeError(
            "Frozen OOD threshold changed"
        )

    if (
        data[
            "ties_at_threshold_accepted"
        ]
        is not True
    ):
        raise RuntimeError(
            "Threshold equality rule changed"
        )

    if (
        data[
            "runtime_contract"
        ][
            "task_model_forwards_per_window"
        ]
        != 1
    ):
        raise RuntimeError(
            "One-forward invariant changed"
        )

    if (
        data[
            "runtime_contract"
        ][
            "feature_vector_used_by_selected_score"
        ]
        is not False
    ):
        raise RuntimeError(
            "Feature-vector score use changed"
        )

    if (
        data[
            "runtime_contract"
        ][
            "classifier_bypass_enabled"
        ]
        is not False
    ):
        raise RuntimeError(
            "Classifier bypass enabled unexpectedly"
        )

    return data


def verify_frozen_inputs():
    refs = {
        "ood-final-test-protocol-v1^{commit}":
            FINAL_TEST_PROTOCOL_COMMIT,

        "ood-operating-point-v1^{commit}":
            OOD_OPERATING_POINT_COMMIT,

        "ood-calibration-result-v1^{commit}":
            OOD_CALIBRATION_RESULT_COMMIT,

        "ood-calibration-evaluator-v1b^{commit}":
            OOD_CALIBRATION_EVALUATOR_V1B_COMMIT,

        "integrity-final-test-result-v1^{commit}":
            INTEGRITY_FINAL_RESULT_COMMIT,

        "baseline-date2025-cnn400-v1^{commit}":
            BASELINE_COMMIT,

        "reliability-eval-registry-v1^{commit}":
            REGISTRY_COMMIT,
    }

    for ref, expected in refs.items():
        observed = git(
            "rev-parse",
            ref,
        )

        if observed != expected:
            raise RuntimeError(
                f"Frozen ref moved: {ref}: {observed}"
            )

    for ref in (
        "ood-final-test-protocol-v1",
        "ood-operating-point-v1",
        "ood-calibration-result-v1",
        "ood-calibration-evaluator-v1b",
        "integrity-final-test-result-v1",
        "baseline-date2025-cnn400-v1",
        "reliability-eval-registry-v1",
    ):
        rc = subprocess.run(
            [
                "git",
                "merge-base",
                "--is-ancestor",
                ref,
                "HEAD",
            ],
            cwd=ROOT,
            check=False,
        ).returncode

        if rc != 0:
            raise RuntimeError(
                f"Frozen ref is not an ancestor: {ref}"
            )

    for frozen_file in (
        FINAL_TEST_PROTOCOL,
        FINAL_OP,
        REGISTRY,
        V1B_SOURCE,
    ):
        rc = subprocess.run(
            [
                "git",
                "diff",
                "--quiet",
                "--",
                str(
                    frozen_file.relative_to(
                        ROOT
                    )
                ),
            ],
            cwd=ROOT,
            check=False,
        ).returncode

        if rc != 0:
            raise RuntimeError(
                f"Frozen dependency modified in worktree: "
                f"{frozen_file}"
            )

    load_final_test_protocol()
    load_frozen_operating_point()

    v1b = load_v1b_module()

    v1b.verify_frozen_inputs()


def verify_evaluator_is_frozen():
    tag_commit = git(
        "rev-parse",
        f"{EVALUATOR_TAG}^{{commit}}",
    )

    head = git(
        "rev-parse",
        "HEAD",
    )

    if head != tag_commit:
        raise RuntimeError(
            "HEAD must exactly equal frozen final-test "
            "evaluator tag before protected output exposure"
        )

    evaluator_relative = str(
        Path(
            __file__
        ).resolve().relative_to(
            ROOT
        )
    )

    last_touch = git(
        "log",
        "-1",
        "--format=%H",
        "--",
        evaluator_relative,
    )

    if last_touch != tag_commit:
        raise RuntimeError(
            "Final-test evaluator changed after freeze"
        )

    return tag_commit


def final_test_rows():
    registry = json.loads(
        REGISTRY.read_text()
    )

    rows = [
        row
        for row in registry[
            "records"
        ]
        if row[
            "partition"
        ]
        == "final_test"
    ]

    rows.sort(
        key=lambda row:
            (
                row[
                    "dataset"
                ],
                row[
                    "trial_id"
                ],
            )
    )

    if len(
        rows
    ) != EXPECTED_FINAL_ROWS:
        raise RuntimeError(
            "Protected final-test row count changed"
        )

    row_counts = Counter(
        row[
            "dataset"
        ]
        for row in rows
    )

    if dict(
        row_counts
    ) != EXPECTED_DATASET_ROWS:
        raise RuntimeError(
            "Protected final-test dataset row counts changed"
        )

    window_counts = Counter()

    for row in rows:
        if (
            row[
                "prospective_constraints"
            ][
                "may_select_ood_operating_point"
            ]
            is not False
        ):
            raise RuntimeError(
                "Final-test OOD tuning permission changed"
            )

        window_counts[
            row[
                "dataset"
            ]
        ] += int(
            row[
                "historical_windows"
            ]
        )

    if dict(
        window_counts
    ) != EXPECTED_DATASET_WINDOWS:
        raise RuntimeError(
            "Protected final-test window counts changed"
        )

    if sum(
        window_counts.values()
    ) != EXPECTED_FINAL_WINDOWS:
        raise RuntimeError(
            "Protected final-test total windows changed"
        )

    return rows


def evaluate_final_test(
    model,
):
    v1b = load_v1b_module()

    rows = final_test_rows()

    accepted_by_dataset = Counter()
    unknown_by_dataset = Counter()
    total_by_dataset = Counter()

    accepted_by_class = Counter()
    unknown_by_class = Counter()
    total_by_class = Counter()

    overall_accepted = 0
    overall_unknown = 0
    overall_total = 0

    overall_task = v1b.empty_task_bucket()

    task_by_dataset = defaultdict(
        v1b.empty_task_bucket
    )

    final_trial_array_pairs_opened = 0
    model_batch_forward_calls = 0
    model_windows_forwarded = 0

    for row in rows:
        dataset = row[
            "dataset"
        ]

        trial_id = row[
            "trial_id"
        ]

        trial_dir = (
            v1b.DATA
            / row[
                "relative_trial"
            ]
        )

        x_file = (
            trial_dir
            / "segments.npy"
        )

        y_file = (
            trial_dir
            / "labels.npy"
        )

        if (
            not x_file.is_file()
            or not y_file.is_file()
        ):
            raise RuntimeError(
                f"Protected final-test pair absent: {trial_id}"
            )

        x = np.load(
            x_file,
            mmap_mode="r",
            allow_pickle=False,
        )

        y_raw = np.load(
            y_file,
            allow_pickle=True,
        )

        final_trial_array_pairs_opened += 1

        if (
            x.ndim != 3
            or tuple(
                x.shape[
                    1:
                ]
            )
            != (
                40,
                9,
            )
        ):
            raise RuntimeError(
                f"Unexpected protected final-test shape: "
                f"{trial_id}: {x.shape}"
            )

        if len(
            x
        ) != len(
            y_raw
        ):
            raise RuntimeError(
                f"Protected final-test X/Y mismatch: {trial_id}"
            )

        if len(
            x
        ) != int(
            row[
                "historical_windows"
            ]
        ):
            raise RuntimeError(
                f"Protected final-test registry/window mismatch: "
                f"{trial_id}"
            )

        y = np.asarray(
            [
                v1b.normalize_label(
                    value
                )
                for value in y_raw
            ],
            dtype=np.int64,
        )

        for start in range(
            0,
            len(
                x
            ),
            BATCH_SIZE,
        ):
            end = min(
                start
                + BATCH_SIZE,
                len(
                    x
                ),
            )

            xb = torch.from_numpy(
                np.asarray(
                    x[
                        start:end
                    ],
                    dtype=np.float32,
                )
            )

            with torch.inference_mode():
                logits, features = (
                    model.forward_with_features(
                        xb
                    )
                )

            model_batch_forward_calls += 1

            batch_n = int(
                end
                - start
            )

            model_windows_forwarded += batch_n

            if tuple(
                logits.shape
            ) != (
                batch_n,
                2,
            ):
                raise RuntimeError(
                    "Unexpected protected final-test logits shape"
                )

            if tuple(
                features.shape
            ) != (
                batch_n,
                256,
            ):
                raise RuntimeError(
                    "Unexpected protected final-test feature shape"
                )

            margin = torch.abs(
                logits[
                    :,
                    0
                ]
                - logits[
                    :,
                    1
                ]
            )

            pred = torch.argmax(
                logits,
                dim=1,
            )

            margin_np = (
                margin
                .cpu()
                .numpy()
                .astype(
                    np.float64
                )
            )

            pred_np = (
                pred
                .cpu()
                .numpy()
                .astype(
                    np.int64
                )
            )

            y_batch = y[
                start:end
            ]

            unknown_mask = (
                margin_np
                < FROZEN_THRESHOLD
            )

            accepted_mask = np.logical_not(
                unknown_mask
            )

            accepted_n = int(
                np.sum(
                    accepted_mask
                )
            )

            unknown_n = int(
                np.sum(
                    unknown_mask
                )
            )

            if (
                accepted_n
                + unknown_n
                != batch_n
            ):
                raise RuntimeError(
                    "Protected final-test OOD accounting mismatch"
                )

            overall_total += batch_n
            overall_accepted += accepted_n
            overall_unknown += unknown_n

            total_by_dataset[
                dataset
            ] += batch_n

            accepted_by_dataset[
                dataset
            ] += accepted_n

            unknown_by_dataset[
                dataset
            ] += unknown_n

            v1b.update_task_bucket(
                overall_task,
                y_batch,
                pred_np,
            )

            v1b.update_task_bucket(
                task_by_dataset[
                    dataset
                ],
                y_batch,
                pred_np,
            )

            for offset in range(
                batch_n
            ):
                class_name = v1b.label_name(
                    int(
                        y_batch[
                            offset
                        ]
                    )
                )

                total_by_class[
                    class_name
                ] += 1

                if bool(
                    unknown_mask[
                        offset
                    ]
                ):
                    unknown_by_class[
                        class_name
                    ] += 1
                else:
                    accepted_by_class[
                        class_name
                    ] += 1

        del x
        del y_raw
        del y

    if (
        final_trial_array_pairs_opened
        != EXPECTED_FINAL_ROWS
    ):
        raise RuntimeError(
            "Not every protected final-test trial pair was opened"
        )

    if (
        model_windows_forwarded
        != EXPECTED_FINAL_WINDOWS
    ):
        raise RuntimeError(
            "Not every protected final-test window was forwarded exactly once"
        )

    if (
        overall_total
        != EXPECTED_FINAL_WINDOWS
    ):
        raise RuntimeError(
            "Protected final-test accounting denominator changed"
        )

    if (
        overall_accepted
        + overall_unknown
        != overall_total
    ):
        raise RuntimeError(
            "Protected final-test overall OOD accounting mismatch"
        )

    if dict(
        total_by_dataset
    ) != EXPECTED_DATASET_WINDOWS:
        raise RuntimeError(
            "Protected final-test dataset denominators changed"
        )

    by_dataset = {}

    for dataset in sorted(
        total_by_dataset
    ):
        n = int(
            total_by_dataset[
                dataset
            ]
        )

        accepted = int(
            accepted_by_dataset[
                dataset
            ]
        )

        unknown = int(
            unknown_by_dataset[
                dataset
            ]
        )

        by_dataset[
            dataset
        ] = {
            "n":
                n,

            "accepted_count":
                accepted,

            "ood_unknown_count":
                unknown,

            "empirical_acceptance":
                float(
                    accepted
                    / n
                ),

            "empirical_ood_unknown_rate":
                float(
                    unknown
                    / n
                ),
        }

    by_class = {}

    for class_name in sorted(
        total_by_class
    ):
        n = int(
            total_by_class[
                class_name
            ]
        )

        accepted = int(
            accepted_by_class[
                class_name
            ]
        )

        unknown = int(
            unknown_by_class[
                class_name
            ]
        )

        by_class[
            class_name
        ] = {
            "n":
                n,

            "accepted_count":
                accepted,

            "ood_unknown_count":
                unknown,

            "empirical_acceptance":
                float(
                    accepted
                    / n
                ),

            "empirical_ood_unknown_rate":
                float(
                    unknown
                    / n
                ),
        }

    return {
        "protected_id_metrics": {
            "overall": {
                "n":
                    overall_total,

                "accepted_count":
                    overall_accepted,

                "ood_unknown_count":
                    overall_unknown,

                "empirical_acceptance":
                    float(
                        overall_accepted
                        / overall_total
                    ),

                "empirical_ood_unknown_rate":
                    float(
                        overall_unknown
                        / overall_total
                    ),
            },

            "by_dataset":
                by_dataset,

            "by_task_class":
                by_class,
        },

        "task_metrics_descriptive_only": {
            "overall":
                v1b.finalize_task_bucket(
                    overall_task
                ),

            "by_dataset": {
                dataset:
                    v1b.finalize_task_bucket(
                        bucket
                    )
                for dataset, bucket
                in sorted(
                    task_by_dataset.items()
                )
            },
        },

        "access_audit": {
            "final_test_registry_trial_rows":
                EXPECTED_FINAL_ROWS,

            "final_test_trial_array_pairs_opened":
                final_trial_array_pairs_opened,

            "final_test_windows_forwarded":
                model_windows_forwarded,

            "model_batch_forward_calls":
                model_batch_forward_calls,

            "task_model_forwards_per_window":
                1,

            "checkpoint_deserialized_for_final_test_ood":
                True,

            "protected_model_weights_loaded_for_final_test_ood":
                True,

            "protected_model_forward_executed_for_final_test_ood":
                True,

            "final_test_task_logits_read":
                True,

            "penultimate_feature_tensor_returned":
                True,

            "penultimate_feature_used_by_selected_ood_score":
                False,

            "second_full_task_model_forward_used":
                False,

            "final_test_ood_margins_computed":
                True,

            "final_test_ood_states_computed":
                True,

            "threshold_selection_performed":
                False,

            "method_selection_performed":
                False,

            "threshold_modified":
                False,

            "method_modified":
                False,

            "extra_recordings_used":
                False,

            "true_ood_positive_population_used":
                False,

            "integrity_operating_point_reopened":
                False,
        },
    }


def build_result(
    evaluator_commit: str,
    evaluation,
):
    protocol = load_final_test_protocol()

    result = {
        "result_id":
            "OOD_FINAL_TEST_V1_CANDIDATE",

        "status":
            "protected_final_test_complete_result_candidate_not_yet_frozen",

        "partition":
            "final_test",

        "source_anchors": {
            "ood_final_test_protocol": {
                "tag":
                    FINAL_TEST_PROTOCOL_TAG,

                "tag_commit":
                    FINAL_TEST_PROTOCOL_COMMIT,

                "raw_sha256":
                    FINAL_TEST_PROTOCOL_RAW_SHA256,

                "content_sha256":
                    FINAL_TEST_PROTOCOL_CONTENT_SHA256,
            },

            "ood_final_test_evaluator": {
                "tag":
                    EVALUATOR_TAG,

                "tag_commit":
                    evaluator_commit,

                "raw_sha256":
                    file_sha256(
                        Path(
                            __file__
                        ).resolve()
                    ),
            },

            "ood_operating_point": {
                "tag":
                    "ood-operating-point-v1",

                "tag_commit":
                    OOD_OPERATING_POINT_COMMIT,

                "raw_sha256":
                    FINAL_OP_RAW_SHA256,

                "content_sha256":
                    FINAL_OP_CONTENT_SHA256,
            },

            "ood_calibration_result": {
                "tag":
                    "ood-calibration-result-v1",

                "tag_commit":
                    OOD_CALIBRATION_RESULT_COMMIT,
            },

            "ood_calibration_evaluator_v1b": {
                "tag":
                    "ood-calibration-evaluator-v1b",

                "tag_commit":
                    OOD_CALIBRATION_EVALUATOR_V1B_COMMIT,

                "raw_sha256":
                    OOD_CALIBRATION_EVALUATOR_V1B_RAW_SHA256,

                "role":
                    (
                        "frozen protected-model loading and "
                        "legacy pickle compatibility dependency"
                    ),
            },

            "integrity_final_test_result": {
                "tag":
                    "integrity-final-test-result-v1",

                "tag_commit":
                    INTEGRITY_FINAL_RESULT_COMMIT,
            },

            "protected_baseline": {
                "tag":
                    "baseline-date2025-cnn400-v1",

                "tag_commit":
                    BASELINE_COMMIT,
            },

            "reliability_registry": {
                "tag":
                    "reliability-eval-registry-v1",

                "tag_commit":
                    REGISTRY_COMMIT,
            },
        },

        "frozen_ood_operating_point": {
            "selected_method":
                "top_two_logit_margin",

            "score_formula":
                "abs(logit_0 - logit_1)",

            "threshold":
                FROZEN_THRESHOLD,

            "unknown_rule":
                "margin < threshold",

            "accepted_rule":
                "margin >= threshold",

            "ties_at_threshold_accepted":
                True,

            "threshold_selected_during_final_test":
                False,

            "method_selected_during_final_test":
                False,
        },

        "evaluation_contract": {
            "protected_population_role":
                "historical_ID_generalization_evaluation",

            "single_successful_final_test_exposure":
                True,

            "threshold_modified_after_calibration":
                False,

            "method_modified_after_calibration":
                False,

            "method_comparison_performed":
                False,

            "true_ood_positive_population_used":
                False,

            "true_ood_metrics_claimed":
                False,

            "auroc_claimed":
                False,

            "ood_recall_claimed":
                False,

            "ood_precision_claimed":
                False,

            "tnr_at_tpr_claimed":
                False,

            "external_extra_recordings_used":
                False,

            "feature_vector_used_by_selected_ood_score":
                False,

            "second_full_task_forward_used":
                False,

            "classifier_bypass_enabled":
                False,

            "integrity_operating_point_reopened":
                False,
        },

        "protected_id_metrics":
            evaluation[
                "protected_id_metrics"
            ],

        "task_metrics_descriptive_only":
            evaluation[
                "task_metrics_descriptive_only"
            ],

        "access_audit":
            evaluation[
                "access_audit"
            ],

        "scientific_interpretation": {
            "ood_unknown_rate_means":
                (
                    "protected historical-ID rejection / residual "
                    "task-model unfamiliarity rate under the already-frozen gate"
                ),

            "ood_unknown_rate_does_not_mean":
                [
                    "true_ood_recall",
                    "novel_activity_detection_probability",
                    "sensor_failure_probability",
                    "qualified_integrity_cause_rate",
                ],

            "absence_of_ood_unknown_does_not_establish":
                "ability_to_detect_true_unknown_activity",

            "task_metrics_are":
                "descriptive_argmax_metrics_from_the_same_task_logits",

            "task_metrics_are_not":
                "a_redefinition_of_the_historical_deployed_falling_event_rule",
        },

        "runtime_contract_snapshot":
            protocol[
                "runtime_contract"
            ],
    }

    result[
        "content_sha256"
    ] = canonical_digest(
        result
    )

    return result


def main():
    verify_frozen_inputs()

    evaluator_commit = (
        verify_evaluator_is_frozen()
    )

    if RESULT.exists():
        raise RuntimeError(
            "Refusing to overwrite protected final-test result"
        )

    if FINAL_RECEIPT.exists():
        raise RuntimeError(
            "Final-test receipt unexpectedly preexists"
        )

    v1b = load_v1b_module()

    model = (
        v1b.load_protected_model()
    )

    evaluation = evaluate_final_test(
        model
    )

    result = build_result(
        evaluator_commit,
        evaluation,
    )

    RESULT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    RESULT.write_text(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )

    overall = result[
        "protected_id_metrics"
    ][
        "overall"
    ]

    print(
        "OOD_FINAL_TEST_V1_COMPLETE = True"
    )

    print(
        "FINAL_TEST_WINDOWS_FORWARDED =",
        result[
            "access_audit"
        ][
            "final_test_windows_forwarded"
        ],
    )

    print(
        "MODEL_BATCH_FORWARD_CALLS =",
        result[
            "access_audit"
        ][
            "model_batch_forward_calls"
        ],
    )

    print(
        "FROZEN_METHOD =",
        result[
            "frozen_ood_operating_point"
        ][
            "selected_method"
        ],
    )

    print(
        "FROZEN_THRESHOLD =",
        result[
            "frozen_ood_operating_point"
        ][
            "threshold"
        ],
    )

    print(
        "OVERALL_ACCEPTED =",
        overall[
            "accepted_count"
        ],
    )

    print(
        "OVERALL_OOD_UNKNOWN =",
        overall[
            "ood_unknown_count"
        ],
    )

    print(
        "OVERALL_ACCEPTANCE =",
        overall[
            "empirical_acceptance"
        ],
    )

    print(
        "OVERALL_OOD_UNKNOWN_RATE =",
        overall[
            "empirical_ood_unknown_rate"
        ],
    )

    for dataset, metrics in sorted(
        result[
            "protected_id_metrics"
        ][
            "by_dataset"
        ].items()
    ):
        print(
            "DATASET",
            dataset,
            metrics,
        )

    for class_name, metrics in sorted(
        result[
            "protected_id_metrics"
        ][
            "by_task_class"
        ].items()
    ):
        print(
            "TASK_CLASS",
            class_name,
            metrics,
        )

    print(
        "RESULT_CONTENT_SHA256 =",
        result[
            "content_sha256"
        ],
    )

    print(
        "THRESHOLD_SELECTION_PERFORMED = False"
    )

    print(
        "METHOD_SELECTION_PERFORMED = False"
    )

    print(
        "TRUE_OOD_METRICS_CLAIMED = False"
    )

    print(
        "EXTRA_RECORDINGS_USED = False"
    )

    print(
        "INTEGRITY_OPERATING_POINT_REOPENED = False"
    )


if __name__ == "__main__":
    main()
