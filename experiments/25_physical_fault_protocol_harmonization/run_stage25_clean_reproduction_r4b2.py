from __future__ import annotations

import csv
import gc
import hashlib
import inspect
import json
import os
import sys
import time
from pathlib import Path

import numpy as np


ROOT = Path(
    "/mnt/hdd16T/ToqeerHomeBackup/toqeer/IMU_Reliability"
)

SUITE = (
    ROOT
    / "experiments"
    / "16_benchmark_suite"
)

SCREEN = (
    ROOT
    / "experiments"
    / "17_v25_screening"
)

R4B1 = (
    ROOT
    / "results"
    / "stage25_physical_fault_protocol"
    / "clean_reference_constructor_audit_r4b1"
)

R4B1B = (
    ROOT
    / "results"
    / "stage25_physical_fault_protocol"
    / "exact_constructor_mapping_r4b1b"
)

OUT = (
    ROOT
    / "results"
    / "stage25_physical_fault_protocol"
    / "clean_reproduction_r4b2"
)

OUT.mkdir(
    parents=True,
    exist_ok=True,
)


# Frozen before any clean outcome is computed.
METRIC_TOLERANCE = 1e-12

BATCH_SIZE = 64

DATASETS = [
    "UCI_HAR",
    "PAMAP2",
    "DSADS",
    "MotionSense",
]

DATASET_ORDER = {
    name: i
    for i, name in enumerate(
        DATASETS
    )
}

V25_MODEL = (
    "ReliabilityCNN_v25"
)


def sha256_file(
    path: Path,
) -> str:

    h = hashlib.sha256()

    with path.open(
        "rb"
    ) as f:

        for block in iter(
            lambda: f.read(
                1024 * 1024
            ),
            b"",
        ):
            h.update(block)

    return h.hexdigest()


def sha256_int64_array(
    values,
) -> str:

    arr = np.ascontiguousarray(
        np.asarray(
            values,
            dtype=np.int64,
        )
    )

    h = hashlib.sha256()

    h.update(
        str(
            arr.shape
        ).encode(
            "utf-8"
        )
    )

    h.update(
        arr.tobytes()
    )

    return h.hexdigest()


def write_json(
    path: Path,
    obj,
):

    path.write_text(
        json.dumps(
            obj,
            indent=2,
            sort_keys=True,
            default=str,
        )
        + "\n"
    )


def write_rows(
    path: Path,
    rows,
):

    if not rows:

        return

    with path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=list(
                rows[0].keys()
            ),
        )

        writer.writeheader()

        writer.writerows(
            rows
        )


# ============================================================
# 0. Working directory and controlled imports
# ============================================================

os.chdir(
    ROOT
)

sys.path.insert(
    0,
    str(SUITE),
)

sys.path.insert(
    0,
    str(SCREEN),
)


import torch

try:

    from sklearn.metrics import (
        accuracy_score,
        f1_score,
    )

except Exception as exc:

    raise RuntimeError(
        "Controlled environment cannot import "
        "sklearn.metrics; do NOT install anything. "
        f"Original error: {exc}"
    )


from engine.dataset_v3r1 import (
    load_dataset_v3r1,
)

from engine.model_registry import (
    create_model,
)

from engine.model_forward import (
    model_forward,
)

from v25_candidates import (
    create_candidate,
)


print(
    "=" * 116
)

print(
    "STAGE25 R4B2 CLEAN-ONLY REPRODUCTION"
)

print(
    "200 FROZEN CHECKPOINTS — NO CORRUPTED INFERENCE"
)

print(
    "=" * 116
)


# ============================================================
# 1. Environment
# ============================================================

print(
    "PYTHON_VERSION=",
    sys.version.replace(
        "\n",
        " ",
    ),
)

print(
    "TORCH_VERSION=",
    torch.__version__,
)

print(
    "CUDA_AVAILABLE=",
    torch.cuda.is_available(),
)

print(
    "CLEAN_REPRODUCTION_METRIC_TOLERANCE=",
    METRIC_TOLERANCE,
)

print(
    "CLEAN_REPRODUCTION_BATCH_SIZE=",
    BATCH_SIZE,
)


if not torch.cuda.is_available():

    raise RuntimeError(
        "CUDA unavailable in controlled environment. "
        "Classify as environment failure before "
        "changing the protocol."
    )


device = torch.device(
    "cuda:0"
)


print(
    "DEVICE=",
    str(device),
)

print(
    "GPU_NAME=",
    torch.cuda.get_device_name(
        0
    ),
)


torch.backends.cudnn.benchmark = False
torch.backends.cudnn.deterministic = True


# ============================================================
# 2. Frozen clean reproduction plan
# ============================================================

plan_path = (
    R4B1B
    / "clean_reproduction_plan_200.csv"
)

constructor_path = (
    R4B1B
    / "exact_constructor_mapping_10.csv"
)


for path in [
    plan_path,
    constructor_path,
]:

    if not path.exists():

        raise FileNotFoundError(
            path
        )


with plan_path.open(
    newline="",
    encoding="utf-8",
) as f:

    plan = list(
        csv.DictReader(f)
    )


with constructor_path.open(
    newline="",
    encoding="utf-8",
) as f:

    constructor_rows = list(
        csv.DictReader(f)
    )


if len(
    plan
) != 200:

    raise RuntimeError(
        f"Expected 200 clean reproduction cases, "
        f"found {len(plan)}"
    )


if len(
    constructor_rows
) != 10:

    raise RuntimeError(
        f"Expected 10 constructor rows, "
        f"found {len(constructor_rows)}"
    )


print(
    "CLEAN_REPRODUCTION_PLAN_GATE_PASS_200_OF_200=True"
)

print(
    "EXACT_CONSTRUCTOR_MAP_GATE_PASS_10_OF_10=True"
)


# ============================================================
# 3. Re-verify checkpoint + metric + constructor source SHAs
# ============================================================

for row in plan:

    checkpoint = (
        ROOT
        / row[
            "checkpoint"
        ]
    )

    metrics = (
        ROOT
        / row[
            "metrics_file"
        ]
    )

    constructor_source = (
        ROOT
        / row[
            "constructor_source_file"
        ]
    )


    for path in [
        checkpoint,
        metrics,
        constructor_source,
    ]:

        if not path.exists():

            raise FileNotFoundError(
                path
            )


    if (
        sha256_file(
            checkpoint
        )
        !=
        row[
            "checkpoint_sha256"
        ]
    ):

        raise RuntimeError(
            "Checkpoint SHA changed before R4B2: "
            f"{checkpoint}"
        )


    if (
        sha256_file(
            metrics
        )
        !=
        row[
            "metrics_sha256"
        ]
    ):

        raise RuntimeError(
            "Clean-reference metrics file SHA changed "
            f"before R4B2: {metrics}"
        )


    if (
        sha256_file(
            constructor_source
        )
        !=
        row[
            "constructor_source_sha256"
        ]
    ):

        raise RuntimeError(
            "Constructor source SHA changed "
            f"before R4B2: {constructor_source}"
        )


print(
    "R4B2_INPUT_SHA_GATE_PASS_200_OF_200=True"
)


# ============================================================
# 4. Freeze canonical model_forward API before construction
# ============================================================

forward_signature = (
    inspect.signature(
        model_forward
    )
)

forward_source = (
    inspect.getsource(
        model_forward
    )
)


print(
    "MODEL_FORWARD_SIGNATURE=",
    str(
        forward_signature
    ),
)


write_json(
    OUT
    / "canonical_model_forward_runtime_evidence.json",
    {
        "signature":
            str(
                forward_signature
            ),

        "source":
            forward_source,

        "source_file":
            str(
                (
                    SUITE
                    / "engine"
                    / "model_forward.py"
                ).relative_to(
                    ROOT
                )
            ),

        "source_sha256":
            sha256_file(
                SUITE
                / "engine"
                / "model_forward.py"
            ),
    },
)


parameters = list(
    forward_signature.parameters.values()
)


required_positional = [
    p
    for p in parameters
    if (
        p.kind
        in {
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        }
        and
        p.default
        is
        inspect.Parameter.empty
    )
]


if len(
    required_positional
) not in {
    2,
    3,
}:

    raise RuntimeError(
        "Unexpected canonical model_forward API: "
        f"{forward_signature}. "
        "Abort before model construction."
    )


print(
    "MODEL_FORWARD_API_PREFLIGHT_PASS=True"
)


# ============================================================
# 5. Forward dispatcher
#
# Baselines use exact canonical V3R1 model_forward().
# V25 uses its frozen architecture's direct forward(), exactly
# as trained in its V25 candidate/final pipeline.
# ============================================================

def forward_baseline(
    model,
    x,
    model_name,
):

    if len(
        required_positional
    ) == 2:

        return model_forward(
            model,
            x,
        )


    third_name = (
        required_positional[
            2
        ].name
    )


    if third_name in {
        "model_name",
        "name",
        "architecture",
        "architecture_name",
    }:

        return model_forward(
            model,
            x,
            model_name,
        )


    raise RuntimeError(
        "Canonical model_forward has an unsupported "
        "required third parameter: "
        f"{third_name!r}"
    )


def forward_case(
    model,
    x,
    model_name,
):

    if (
        model_name
        ==
        V25_MODEL
    ):

        logits = model(
            x
        )

    else:

        logits = forward_baseline(
            model,
            x,
            model_name,
        )


    if isinstance(
        logits,
        (
            tuple,
            list,
        ),
    ):

        if not logits:

            raise RuntimeError(
                f"{model_name}: empty forward tuple/list"
            )

        logits = logits[
            0
        ]


    if not torch.is_tensor(
        logits
    ):

        raise RuntimeError(
            f"{model_name}: forward output is not Tensor: "
            f"{type(logits)}"
        )


    return logits


# ============================================================
# 6. Strict checkpoint deserialization helper
# ============================================================

def load_direct_state_dict(
    checkpoint: Path,
):

    try:

        state = torch.load(
            checkpoint,
            map_location="cpu",
            weights_only=True,
        )

    except TypeError:

        state = torch.load(
            checkpoint,
            map_location="cpu",
        )


    if not isinstance(
        state,
        dict,
    ):

        raise RuntimeError(
            f"{checkpoint}: expected direct state_dict mapping, "
            f"got {type(state)}"
        )


    if not state:

        raise RuntimeError(
            f"{checkpoint}: empty checkpoint mapping"
        )


    if not all(
        torch.is_tensor(
            value
        )
        for value in state.values()
    ):

        raise RuntimeError(
            f"{checkpoint}: checkpoint is not a direct "
            "tensor-valued state_dict. "
            "Do not guess a wrapper key; reconcile provenance."
        )


    return state


# ============================================================
# 7. Dataset caching
#
# Exact canonical V3R1 loader, batch size 64.
# No reliability-training corruption.
# ============================================================

dataset_cache = {}


def get_dataset(
    dataset_name,
):

    if dataset_name in dataset_cache:

        return dataset_cache[
            dataset_name
        ]


    data = load_dataset_v3r1(
        dataset_name,
        batch_size=BATCH_SIZE,
        reliability_training=False,
    )


    if data[
        "num_classes"
    ] <= 1:

        raise RuntimeError(
            f"{dataset_name}: invalid num_classes"
        )


    dataset_cache[
        dataset_name
    ] = data


    print()
    print(
        "DATASET_LOADED:",
        dataset_name,
        "TEST_SAMPLES=",
        data[
            "summary"
        ][
            "test_samples"
        ],
        "NUM_CLASSES=",
        data[
            "num_classes"
        ],
    )


    return data


# ============================================================
# 8. Sort plan deterministically
# ============================================================

plan = sorted(
    plan,
    key=lambda row: (
        DATASET_ORDER[
            row[
                "dataset"
            ]
        ],
        row[
            "model"
        ],
        int(
            row[
                "seed"
            ]
        ),
    ),
)


# ============================================================
# 9. Clean-only inference
# ============================================================

rows = []

partial_path = (
    OUT
    / "clean_reproduction_cases_partial.csv"
)

final_path = (
    OUT
    / "clean_reproduction_cases_200.csv"
)


pass_count = 0
fail_count = 0

model_construction_count = 0
checkpoint_deserialization_count = 0
forward_case_count = 0

start_all = time.perf_counter()


for case_index, row in enumerate(
    plan,
    1,
):

    dataset_name = row[
        "dataset"
    ]

    model_name = row[
        "model"
    ]

    seed = int(
        row[
            "seed"
        ]
    )

    num_classes = int(
        row[
            "num_classes"
        ]
    )

    checkpoint = (
        ROOT
        / row[
            "checkpoint"
        ]
    )


    print()
    print(
        "-" * 116
    )

    print(
        f"CLEAN_CASE={case_index}/200",
        "DATASET=",
        dataset_name,
        "MODEL=",
        model_name,
        "SEED=",
        seed,
    )

    print(
        "-" * 116
    )


    data = get_dataset(
        dataset_name
    )


    if (
        data[
            "num_classes"
        ]
        !=
        num_classes
    ):

        raise RuntimeError(
            f"{dataset_name}/{model_name}/seed_{seed}: "
            f"plan num_classes={num_classes}, "
            f"loader={data['num_classes']}"
        )


    # --------------------------------------------------------
    # Exact constructor
    # --------------------------------------------------------

    if (
        model_name
        ==
        V25_MODEL
    ):

        model = create_candidate(
            "V25Dense64",
            num_classes,
            input_channels=6,
        )

        constructor_used = (
            "create_candidate('V25Dense64', "
            "num_classes, input_channels=6)"
        )

    else:

        model = create_model(
            model_name,
            num_classes,
            input_channels=6,
        )

        constructor_used = (
            f"create_model('{model_name}', "
            "num_classes, input_channels=6)"
        )


    model_construction_count += 1


    expected_constructor = row[
        "constructor_call"
    ]


    if (
        constructor_used
        !=
        expected_constructor
    ):

        raise RuntimeError(
            "Runtime constructor differs from frozen plan: "
            f"runtime={constructor_used!r}, "
            f"frozen={expected_constructor!r}"
        )


    # --------------------------------------------------------
    # Strict state load
    # --------------------------------------------------------

    state = load_direct_state_dict(
        checkpoint
    )

    checkpoint_deserialization_count += 1


    incompatible = model.load_state_dict(
        state,
        strict=True,
    )


    if (
        list(
            incompatible.missing_keys
        )
        or
        list(
            incompatible.unexpected_keys
        )
    ):

        raise RuntimeError(
            f"{dataset_name}/{model_name}/seed_{seed}: "
            f"strict load incompatibility "
            f"missing={incompatible.missing_keys}, "
            f"unexpected={incompatible.unexpected_keys}"
        )


    model = model.to(
        device
    )

    model.eval()


    # --------------------------------------------------------
    # Clean forward only
    # --------------------------------------------------------

    y_true = []
    y_pred = []


    case_start = time.perf_counter()


    with torch.inference_mode():

        for batch in data[
            "test_loader"
        ]:

            if not isinstance(
                batch,
                (
                    tuple,
                    list,
                ),
            ):

                raise RuntimeError(
                    "Canonical test loader returned "
                    "non-sequence batch"
                )


            if len(
                batch
            ) != 2:

                raise RuntimeError(
                    "Canonical clean test loader expected "
                    f"(x,y), got length {len(batch)}"
                )


            x, y = batch


            x = x.to(
                device,
                non_blocking=True,
            )


            logits = forward_case(
                model,
                x,
                model_name,
            )


            if logits.ndim != 2:

                raise RuntimeError(
                    f"{dataset_name}/{model_name}: "
                    f"expected logits [B,K], "
                    f"got {tuple(logits.shape)}"
                )


            if (
                logits.shape[
                    1
                ]
                !=
                num_classes
            ):

                raise RuntimeError(
                    f"{dataset_name}/{model_name}: "
                    f"logit classes={logits.shape[1]}, "
                    f"expected={num_classes}"
                )


            pred = torch.argmax(
                logits,
                dim=1,
            )


            y_true.extend(
                y.detach()
                .cpu()
                .numpy()
                .astype(
                    np.int64,
                    copy=False,
                )
                .tolist()
            )


            y_pred.extend(
                pred.detach()
                .cpu()
                .numpy()
                .astype(
                    np.int64,
                    copy=False,
                )
                .tolist()
            )


    forward_case_count += 1


    elapsed = (
        time.perf_counter()
        -
        case_start
    )


    y_true_np = np.asarray(
        y_true,
        dtype=np.int64,
    )

    y_pred_np = np.asarray(
        y_pred,
        dtype=np.int64,
    )


    if len(
        y_true_np
    ) != data[
        "summary"
    ][
        "test_samples"
    ]:

        raise RuntimeError(
            f"{dataset_name}/{model_name}/seed_{seed}: "
            "clean inference sample count mismatch"
        )


    reproduced_accuracy = float(
        accuracy_score(
            y_true_np,
            y_pred_np,
        )
    )


    reproduced_macro_f1 = float(
        f1_score(
            y_true_np,
            y_pred_np,
            labels=list(
                range(
                    num_classes
                )
            ),
            average="macro",
            zero_division=0,
        )
    )


    reference_accuracy = float(
        row[
            "reference_accuracy"
        ]
    )

    reference_macro_f1 = float(
        row[
            "reference_macro_f1"
        ]
    )


    accuracy_error = abs(
        reproduced_accuracy
        -
        reference_accuracy
    )

    macro_f1_error = abs(
        reproduced_macro_f1
        -
        reference_macro_f1
    )


    case_pass = (
        accuracy_error
        <=
        METRIC_TOLERANCE
        and
        macro_f1_error
        <=
        METRIC_TOLERANCE
    )


    if case_pass:

        pass_count += 1

    else:

        fail_count += 1


    result = {
        "case_index":
            case_index,

        "dataset":
            dataset_name,

        "model":
            model_name,

        "seed":
            seed,

        "v25_analysis_stratum":
            row[
                "v25_analysis_stratum"
            ],

        "checkpoint":
            row[
                "checkpoint"
            ],

        "checkpoint_sha256":
            row[
                "checkpoint_sha256"
            ],

        "constructor":
            constructor_used,

        "num_classes":
            num_classes,

        "n_test":
            int(
                len(
                    y_true_np
                )
            ),

        "reference_accuracy":
            reference_accuracy,

        "reproduced_accuracy":
            reproduced_accuracy,

        "accuracy_abs_error":
            accuracy_error,

        "reference_macro_f1":
            reference_macro_f1,

        "reproduced_macro_f1":
            reproduced_macro_f1,

        "macro_f1_abs_error":
            macro_f1_error,

        "metric_tolerance":
            METRIC_TOLERANCE,

        "prediction_sha256":
            sha256_int64_array(
                y_pred_np
            ),

        "clean_forward_seconds":
            elapsed,

        "clean_reproduction_pass":
            case_pass,
    }


    rows.append(
        result
    )


    write_rows(
        partial_path,
        rows,
    )


    print(
        "CLEAN_CASE_RESULT:",
        dataset_name,
        model_name,
        seed,
        "REF_ACC=",
        f"{reference_accuracy:.12f}",
        "NEW_ACC=",
        f"{reproduced_accuracy:.12f}",
        "D_ACC=",
        f"{accuracy_error:.3e}",
        "REF_F1=",
        f"{reference_macro_f1:.12f}",
        "NEW_F1=",
        f"{reproduced_macro_f1:.12f}",
        "D_F1=",
        f"{macro_f1_error:.3e}",
        "PASS=",
        case_pass,
    )


    # --------------------------------------------------------
    # Mandatory immediate stop on first clean mismatch.
    # No corrupted inference follows from this script anyway.
    # --------------------------------------------------------

    if not case_pass:

        failure_receipt = {
            "audit":
                "STAGE25_CLEAN_REPRODUCTION_R4B2",

            "status":
                "ABORTED_CLEAN_REPRODUCTION_MISMATCH",

            "failed_case":
                result,

            "cases_completed_before_abort":
                len(
                    rows
                ),

            "cases_passed":
                pass_count,

            "cases_failed":
                fail_count,

            "metric_tolerance":
                METRIC_TOLERANCE,

            "corrupted_inference_performed":
                False,

            "training_performed":
                False,

            "checkpoint_modified":
                False,

            "dataset_modified":
                False,

            "failure_policy":
                (
                    "Stop and classify model/input/metric/"
                    "checkpoint provenance before any "
                    "corrupted inference. Do not weaken "
                    "the frozen tolerance post hoc."
                ),
        }


        write_json(
            OUT
            / "CLEAN_REPRODUCTION_ABORT_RECEIPT.json",
            failure_receipt,
        )


        raise RuntimeError(
            "CLEAN_REPRODUCTION_GATE_FAILED: "
            f"{dataset_name}/{model_name}/seed_{seed}; "
            f"accuracy_error={accuracy_error}, "
            f"macro_f1_error={macro_f1_error}"
        )


    # --------------------------------------------------------
    # Cleanup
    # --------------------------------------------------------

    del state
    del model
    del y_true
    del y_pred
    del y_true_np
    del y_pred_np

    gc.collect()

    torch.cuda.empty_cache()


# ============================================================
# 10. Full acceptance
# ============================================================

elapsed_all = (
    time.perf_counter()
    -
    start_all
)


if len(
    rows
) != 200:

    raise RuntimeError(
        f"Expected 200 completed clean cases, "
        f"found {len(rows)}"
    )


if pass_count != 200:

    raise RuntimeError(
        f"Expected clean pass 200/200, "
        f"got {pass_count}/200"
    )


if fail_count != 0:

    raise RuntimeError(
        f"Unexpected clean failures: "
        f"{fail_count}"
    )


if model_construction_count != 200:

    raise RuntimeError(
        "Model construction count mismatch"
    )


if checkpoint_deserialization_count != 200:

    raise RuntimeError(
        "Checkpoint deserialization count mismatch"
    )


if forward_case_count != 200:

    raise RuntimeError(
        "Clean forward case count mismatch"
    )


write_rows(
    final_path,
    rows,
)


if partial_path.exists():

    partial_path.unlink()


max_accuracy_error = max(
    row[
        "accuracy_abs_error"
    ]
    for row in rows
)

max_macro_f1_error = max(
    row[
        "macro_f1_abs_error"
    ]
    for row in rows
)


# ============================================================
# 11. Dataset/model summary
# ============================================================

grouped = {}


for row in rows:

    key = (
        row[
            "dataset"
        ],
        row[
            "model"
        ],
    )

    grouped.setdefault(
        key,
        [],
    ).append(
        row
    )


summary_rows = []


for (
    dataset,
    model,
), cases in sorted(
    grouped.items()
):

    if len(
        cases
    ) != 5:

        raise RuntimeError(
            f"{dataset}/{model}: "
            f"expected 5 clean seeds, "
            f"found {len(cases)}"
        )


    summary_rows.append({
        "dataset":
            dataset,

        "model":
            model,

        "n_seeds":
            5,

        "reference_accuracy_mean":
            float(
                np.mean(
                    [
                        x[
                            "reference_accuracy"
                        ]
                        for x in cases
                    ]
                )
            ),

        "reproduced_accuracy_mean":
            float(
                np.mean(
                    [
                        x[
                            "reproduced_accuracy"
                        ]
                        for x in cases
                    ]
                )
            ),

        "reference_macro_f1_mean":
            float(
                np.mean(
                    [
                        x[
                            "reference_macro_f1"
                        ]
                        for x in cases
                    ]
                )
            ),

        "reproduced_macro_f1_mean":
            float(
                np.mean(
                    [
                        x[
                            "reproduced_macro_f1"
                        ]
                        for x in cases
                    ]
                )
            ),

        "max_accuracy_abs_error":
            max(
                x[
                    "accuracy_abs_error"
                ]
                for x in cases
            ),

        "max_macro_f1_abs_error":
            max(
                x[
                    "macro_f1_abs_error"
                ]
                for x in cases
            ),
    })


if len(
    summary_rows
) != 40:

    raise RuntimeError(
        f"Expected 40 dataset/model summaries, "
        f"found {len(summary_rows)}"
    )


write_rows(
    OUT
    / "clean_reproduction_summary_40.csv",
    summary_rows,
)


# ============================================================
# 12. Final receipt
# ============================================================

receipt = {
    "audit":
        "STAGE25_CLEAN_REPRODUCTION_R4B2",

    "status":
        "PASS",

    "clean_reproduction":
        "PASS_200_OF_200",

    "checkpoint_sha_verified":
        "PASS_200_OF_200",

    "constructor_mapping":
        "FROZEN_10_OF_10",

    "canonical_dataset_loader":
        (
            "experiments/16_benchmark_suite/"
            "engine/dataset_v3r1.py"
        ),

    "baseline_forward_route":
        (
            "experiments/16_benchmark_suite/"
            "engine/model_forward.py::model_forward"
        ),

    "v25_forward_route":
        "V25Dense64.forward",

    "batch_size":
        BATCH_SIZE,

    "device":
        str(
            device
        ),

    "metric_tolerance":
        METRIC_TOLERANCE,

    "max_accuracy_abs_error":
        max_accuracy_error,

    "max_macro_f1_abs_error":
        max_macro_f1_error,

    "model_construction_count":
        model_construction_count,

    "checkpoint_deserialization_count":
        checkpoint_deserialization_count,

    "clean_forward_case_count":
        forward_case_count,

    "clean_test_evaluations":
        200,

    "elapsed_seconds":
        elapsed_all,

    "corrupted_inference_performed":
        False,

    "corrupted_case_count":
        0,

    "training_performed":
        False,

    "optimizer_created":
        False,

    "backward_performed":
        False,

    "checkpoint_modified":
        False,

    "dataset_modified":
        False,

    "v3r1_training_rerun":
        False,

    "v25_training_rerun":
        False,

    "next_gate":
        (
            "Stage25 frozen paired-domain corrupted "
            "evaluation may begin only after this "
            "R4B2 PASS is frozen."
        ),
}


write_json(
    OUT
    / "stage25_clean_reproduction_receipt_r4b2.json",
    receipt,
)


print()
print(
    "=" * 116
)

print(
    "STAGE25 R4B2 FINAL RECEIPT"
)

print(
    "=" * 116
)

print(
    json.dumps(
        receipt,
        indent=2,
    )
)


print()
print(
    "STAGE25_CLEAN_REPRODUCTION_R4B2_PASS=True"
)

print(
    "CLEAN_REPRODUCTION_PASS_200_OF_200=True"
)

print(
    "MAX_ACCURACY_ABS_ERROR=",
    max_accuracy_error,
)

print(
    "MAX_MACRO_F1_ABS_ERROR=",
    max_macro_f1_error,
)

print(
    "MODEL_CONSTRUCTION_COUNT=200"
)

print(
    "CHECKPOINT_DESERIALIZATION_COUNT=200"
)

print(
    "CLEAN_FORWARD_CASE_COUNT=200"
)

print(
    "CORRUPTED_INFERENCE_PERFORMED=False"
)

print(
    "CORRUPTED_CASE_COUNT=0"
)

print(
    "TRAINING_PERFORMED=False"
)

print(
    "BACKWARD_PERFORMED=False"
)

print(
    "CHECKPOINTS_MODIFIED=False"
)

print(
    "DATASET_ARRAYS_MODIFIED=False"
)
