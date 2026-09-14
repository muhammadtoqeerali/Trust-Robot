from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import os
import platform
import subprocess
from pathlib import Path


ROOT = Path(
    "/mnt/hdd16T/ToqeerHomeBackup/toqeer/IMU_Reliability"
)

R7 = (
    ROOT
    / "results/v26_primary_confirmation_scientific_closure_r7"
)

R6B = (
    ROOT
    / "results/v26_primary_confirmation_test_r6b"
)

V26_R5 = (
    ROOT
    / "results/v26_primary_confirmation_training_r5"
)

S25_R5 = (
    ROOT
    / "results/stage25_physical_fault_protocol"
    / "paired_domain_evaluation_r5"
)

S25_R4B1B = (
    ROOT
    / "results/stage25_physical_fault_protocol"
    / "exact_constructor_mapping_r4b1b"
)

OUT = (
    ROOT
    / "results/v26_efficiency_protocol_r8a"
)

OUT.mkdir(
    parents=True,
    exist_ok=True,
)


PROMOTED = "V26C_DualGateLiteCons"

REPRESENTATIVE_DATASET = "UCI_HAR"

REPRESENTATIVE_SEED = 789

INPUT_LENGTH = 128

INPUT_CHANNELS = 6

NUM_CLASSES = 6


def read_csv(
    path: Path,
):

    with path.open(
        newline="",
        encoding="utf-8",
    ) as f:

        return list(
            csv.DictReader(f)
        )


def write_csv(
    path: Path,
    rows,
):

    if not rows:
        raise RuntimeError(
            f"No rows for {path}"
        )

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


def sha256_file(
    path: Path,
):

    h = hashlib.sha256()

    with path.open("rb") as f:

        for block in iter(
            lambda: f.read(
                1024 * 1024
            ),
            b"",
        ):
            h.update(block)

    return h.hexdigest()


print("=" * 118)
print("V26 EFFICIENCY / COMPLEXITY PROTOCOL R8A")
print("NO MODEL FORWARD")
print("=" * 118)


# ============================================================
# 1. Bind scientific closure
# ============================================================

r7 = json.loads(
    (
        R7
        / "v26_primary_confirmation_scientific_closure_r7.json"
    ).read_text()
)


required = {
    "status":
        "PASS",

    "candidate":
        PROMOTED,

    "frozen_rank1_metrics":
        8,

    "total_metrics":
        8,

    "predeclared_claim_tier":
        "TIER_A_STRONG_INTERNAL_BENCHMARK_SUPERIORITY",

    "candidate_retraining_allowed":
        False,

    "candidate_hyperparameter_change_allowed":
        False,

    "training_performed":
        False,

    "test_inference_performed":
        False,

    "storm_used":
        False,
}


for key, expected in required.items():

    actual = r7.get(
        key
    )

    if actual != expected:

        raise RuntimeError(
            f"R7 scientific closure mismatch: "
            f"{key}={actual!r}, expected={expected!r}"
        )


print(
    "FROZEN_V26_SCIENTIFIC_CLOSURE_BOUND=True"
)


# ============================================================
# 2. Frozen comparator model set
#
# Use all ten models already in the frozen internal comparison.
# Add V26C = 11 total.
# ============================================================

baseline_path = (
    R6B
    / "frozen_primary_baseline_complete_10_recovered.csv"
)


baseline_rows = read_csv(
    baseline_path
)


if len(
    baseline_rows
) != 10:

    raise RuntimeError(
        f"Expected 10 frozen baseline models, "
        f"found {len(baseline_rows)}"
    )


baseline_models = sorted(
    row[
        "model"
    ]
    for row in baseline_rows
)


if len(
    set(
        baseline_models
    )
) != 10:

    raise RuntimeError(
        "Baseline model identities not unique"
    )


required_models = {
    "ReliabilityCNN_v25",
    "ReliabilityCNN_v24",
    "DS_CNN",
    "DeepConvLSTM",
    "TCN",
}


missing_required = (
    required_models
    -
    set(
        baseline_models
    )
)


if missing_required:

    raise RuntimeError(
        f"Expected comparator models missing: "
        f"{sorted(missing_required)}"
    )


all_models = (
    baseline_models
    +
    [
        PROMOTED
    ]
)


if len(
    all_models
) != 11:

    raise RuntimeError(
        "Efficiency comparison model count != 11"
    )


print(
    "EFFICIENCY_COMPARATOR_MODEL_SET_PASS_11=True"
)


# ============================================================
# 3. Bind representative UCI_HAR seed789 checkpoints
#
# Same input geometry and K=6 for every model.
# This is an efficiency fixture, not performance selection.
# ============================================================

stage25_cases = read_csv(
    S25_R5
    / "paired_domain_cases_7000.csv"
)


if len(
    stage25_cases
) != 7000:

    raise RuntimeError(
        "Stage25 R5 case count != 7000"
    )


checkpoint_manifest = []


for model in baseline_models:

    rows = [
        row

        for row in stage25_cases

        if (
            row[
                "model"
            ]
            ==
            model

            and
            row[
                "dataset"
            ]
            ==
            REPRESENTATIVE_DATASET

            and
            int(
                row[
                    "seed"
                ]
            )
            ==
            REPRESENTATIVE_SEED
        )
    ]


    identities = {
        (
            row[
                "checkpoint"
            ],
            row[
                "checkpoint_sha256"
            ],
            int(
                float(
                    row[
                        "parameter_count"
                    ]
                )
            ),
        )

        for row in rows
    }


    if len(
        identities
    ) != 1:

        raise RuntimeError(
            f"{model}: expected one unique frozen "
            f"UCI_HAR seed789 checkpoint identity, "
            f"found {len(identities)}"
        )


    (
        checkpoint_rel,
        expected_sha,
        params,
    ) = next(
        iter(
            identities
        )
    )


    checkpoint = (
        ROOT
        / checkpoint_rel
    )


    if not checkpoint.exists():

        raise FileNotFoundError(
            checkpoint
        )


    actual_sha = sha256_file(
        checkpoint
    )


    if actual_sha != expected_sha:

        raise RuntimeError(
            f"{model}: checkpoint SHA mismatch"
        )


    checkpoint_manifest.append({
        "model":
            model,

        "dataset":
            REPRESENTATIVE_DATASET,

        "seed":
            REPRESENTATIVE_SEED,

        "num_classes":
            NUM_CLASSES,

        "input_length":
            INPUT_LENGTH,

        "input_channels":
            INPUT_CHANNELS,

        "checkpoint":
            checkpoint_rel,

        "checkpoint_sha256":
            actual_sha,

        "parameter_count_frozen":
            params,

        "checkpoint_bytes":
            checkpoint.stat().st_size,

        "source":
            "FROZEN_STAGE25_R5_MODEL_BANK",
    })


# ============================================================
# 4. V26C representative checkpoint
# ============================================================

v26_manifest = read_csv(
    V26_R5
    / "frozen_confirmation_checkpoint_manifest_14.csv"
)


matches = [
    row

    for row in v26_manifest

    if (
        row[
            "candidate_id"
        ]
        ==
        PROMOTED

        and
        row[
            "dataset"
        ]
        ==
        REPRESENTATIVE_DATASET

        and
        int(
            row[
                "seed"
            ]
        )
        ==
        REPRESENTATIVE_SEED
    )
]


if len(
    matches
) != 1:

    raise RuntimeError(
        f"Expected one V26C UCI_HAR seed789 checkpoint, "
        f"found {len(matches)}"
    )


row = matches[
    0
]


checkpoint = (
    ROOT
    / row[
        "checkpoint"
    ]
)


if not checkpoint.exists():

    raise FileNotFoundError(
        checkpoint
    )


actual_sha = sha256_file(
    checkpoint
)


if actual_sha != row[
    "checkpoint_sha256"
]:

    raise RuntimeError(
        "V26C representative checkpoint SHA mismatch"
    )


checkpoint_manifest.append({
    "model":
        PROMOTED,

    "dataset":
        REPRESENTATIVE_DATASET,

    "seed":
        REPRESENTATIVE_SEED,

    "num_classes":
        NUM_CLASSES,

    "input_length":
        INPUT_LENGTH,

    "input_channels":
        INPUT_CHANNELS,

    "checkpoint":
        row[
            "checkpoint"
        ],

    "checkpoint_sha256":
        actual_sha,

    "parameter_count_frozen":
        int(
            row[
                "parameter_count"
            ]
        ),

    "checkpoint_bytes":
        checkpoint.stat().st_size,

    "source":
        "FROZEN_V26_R5_PRIMARY_CONFIRMATION",
})


if len(
    checkpoint_manifest
) != 11:

    raise RuntimeError(
        "Efficiency checkpoint manifest != 11"
    )


if len({
    row[
        "model"
    ]
    for row in checkpoint_manifest
}) != 11:

    raise RuntimeError(
        "Efficiency checkpoint model identities not unique"
    )


write_csv(
    OUT
    / "efficiency_checkpoint_manifest_11.csv",
    checkpoint_manifest,
)


print(
    "EFFICIENCY_FROZEN_CHECKPOINT_SHA_PASS_11_OF_11=True"
)


# ============================================================
# 5. Freeze benchmark protocol
# ============================================================

protocol = {
    "stage":
        "V26_EFFICIENCY_PROTOCOL_R8A",

    "status":
        "FROZEN_BEFORE_TIMING",

    "scientific_model":
        PROMOTED,

    "comparison_models":
        all_models,

    "comparison_model_count":
        11,

    "representative_fixture": {
        "dataset":
            REPRESENTATIVE_DATASET,

        "seed":
            REPRESENTATIVE_SEED,

        "input_shape_batch1": [
            1,
            INPUT_LENGTH,
            INPUT_CHANNELS,
        ],

        "input_shape_batch64": [
            64,
            INPUT_LENGTH,
            INPUT_CHANNELS,
        ],

        "num_classes":
            NUM_CLASSES,

        "fixture_role":
            (
                "architecture/runtime benchmarking only; "
                "not scientific model selection"
            ),
    },

    "primary_efficiency_metrics": [
        "parameter_count",
        "checkpoint_bytes",
        "checkpoint_megabytes",
        "cpu_batch1_latency_ms",
        "gpu_batch1_latency_ms",
        "gpu_batch64_samples_per_second",
        "macs_or_flops_if_supported_without_methodological_ambiguity",
    ],

    "cpu_protocol": {
        "device":
            "cpu",

        "torch_num_threads":
            1,

        "batch_size":
            1,

        "warmup_iterations":
            200,

        "measurement_iterations":
            1000,

        "statistic":
            "median_and_mean_per_forward_latency_ms",

        "input_creation_outside_timed_region":
            True,

        "inference_mode":
            True,

        "model_eval":
            True,
    },

    "gpu_batch1_protocol": {
        "device":
            "cuda:0",

        "batch_size":
            1,

        "warmup_iterations":
            200,

        "measurement_iterations":
            1000,

        "synchronize_before_and_after_timing":
            True,

        "input_creation_outside_timed_region":
            True,

        "host_to_device_transfer_in_timed_region":
            False,

        "inference_mode":
            True,

        "model_eval":
            True,
    },

    "gpu_batch64_protocol": {
        "device":
            "cuda:0",

        "batch_size":
            64,

        "warmup_iterations":
            100,

        "measurement_iterations":
            500,

        "metric":
            "samples_per_second",

        "synchronize_before_and_after_timing":
            True,

        "input_creation_outside_timed_region":
            True,

        "host_to_device_transfer_in_timed_region":
            False,

        "inference_mode":
            True,

        "model_eval":
            True,
    },

    "timing_input": {
        "distribution":
            "deterministic synthetic float32 zeros",

        "reason":
            (
                "runtime depends on shape/model graph, "
                "not activity-label content; prevents "
                "any further protected-data access"
            ),
    },

    "ordering":
        (
            "fixed alphabetical baseline model order "
            "followed by V26C; no result-dependent reranking "
            "before measurements complete"
        ),

    "parameter_validation":
        (
            "constructed model count must exactly match "
            "frozen manifest parameter_count_frozen"
        ),

    "checkpoint_validation":
        "SHA256 must match manifest before model load",

    "model_changes_allowed":
        False,

    "checkpoint_changes_allowed":
        False,

    "graph_optimization_allowed":
        False,

    "torch_compile_allowed":
        False,

    "quantization_allowed":
        False,

    "mixed_precision_allowed":
        False,

    "training_allowed":
        False,

    "test_data_access_allowed":
        False,

    "storm_allowed":
        False,

    "deployment_claim_allowed_from_this_stage":
        False,

    "mac_policy":
        (
            "R8B implementation must first inventory available "
            "complexity tools and existing project profilers. "
            "A MAC/FLOP number is reported only if one frozen "
            "method can support every architecture consistently. "
            "Otherwise MAC/FLOP is explicitly marked not-comparable; "
            "latency/throughput/parameters remain primary."
        ),
}


write_json(
    OUT
    / "v26_efficiency_protocol_r8a.json",
    protocol,
)


print(
    "EFFICIENCY_TIMING_PROTOCOL_FROZEN=True"
)


# ============================================================
# 6. Complexity-tool environment inventory
#
# No models instantiated.
# ============================================================

packages = [
    "thop",
    "fvcore",
    "ptflops",
    "torchprofile",
    "onnx",
]


tool_rows = []


for package in packages:

    spec = importlib.util.find_spec(
        package
    )


    tool_rows.append({
        "package":
            package,

        "available":
            spec is not None,
    })


write_csv(
    OUT
    / "complexity_tool_availability.csv",
    tool_rows,
)


print(
    "COMPLEXITY_TOOL_ENVIRONMENT_INVENTORIED=True"
)


# ============================================================
# 7. Existing project efficiency/profiling source inventory
# ============================================================

patterns = [
    "*efficien*.py",
    "*latency*.py",
    "*throughput*.py",
    "*profile*.py",
    "*mac*.py",
    "*flop*.py",
]


inventory = []


seen = set()


for pattern in patterns:

    for path in ROOT.rglob(
        pattern
    ):

        if not path.is_file():
            continue

        rel = str(
            path.relative_to(
                ROOT
            )
        )

        if rel in seen:
            continue

        seen.add(
            rel
        )

        inventory.append({
            "path":
                rel,

            "sha256":
                sha256_file(
                    path
                ),

            "bytes":
                path.stat().st_size,
        })


inventory.sort(
    key=lambda row:
        row[
            "path"
        ]
)


if inventory:

    write_csv(
        OUT
        / "existing_efficiency_source_inventory.csv",
        inventory,
    )

else:

    write_json(
        OUT
        / "existing_efficiency_source_inventory.json",
        [],
    )


print(
    "EXISTING_EFFICIENCY_SOURCE_INVENTORY_COUNT=",
    len(
        inventory
    ),
)


# ============================================================
# 8. Constructor-mapping artifact inventory
#
# This prepares R8B without loading any model.
# ============================================================

constructor_inventory = []


for path in sorted(
    S25_R4B1B.rglob(
        "*"
    )
):

    if not path.is_file():
        continue

    if path.name in {
        "SHA256SUMS.txt",
        "COMPLETE",
    }:
        continue

    constructor_inventory.append({
        "path":
            str(
                path.relative_to(
                    ROOT
                )
            ),

        "suffix":
            path.suffix,

        "bytes":
            path.stat().st_size,

        "sha256":
            sha256_file(
                path
            ),
    })


if not constructor_inventory:

    raise RuntimeError(
        "Exact constructor-mapping artifact inventory is empty"
    )


write_csv(
    OUT
    / "constructor_mapping_artifact_inventory.csv",
    constructor_inventory,
)


print(
    "CONSTRUCTOR_MAPPING_ARTIFACT_INVENTORY_COUNT=",
    len(
        constructor_inventory
    ),
)


# ============================================================
# 9. Runtime environment metadata
#
# Torch may be imported only for environment metadata.
# No model is constructed and no tensor is created.
# ============================================================

runtime = {
    "python":
        platform.python_version(),

    "platform":
        platform.platform(),

    "machine":
        platform.machine(),

    "processor":
        platform.processor(),

    "cpu_count_logical":
        os.cpu_count(),

    "torch_metadata_import_attempted":
        True,

    "model_constructed":
        False,

    "tensor_created":
        False,

    "forward_performed":
        False,
}


try:

    import torch

    runtime[
        "torch_version"
    ] = torch.__version__

    runtime[
        "cuda_available"
    ] = bool(
        torch.cuda.is_available()
    )


    if torch.cuda.is_available():

        runtime[
            "cuda_device_0"
        ] = torch.cuda.get_device_name(
            0
        )

        runtime[
            "cuda_device_count"
        ] = torch.cuda.device_count()

    else:

        runtime[
            "cuda_device_0"
        ] = None

        runtime[
            "cuda_device_count"
        ] = 0


except Exception as exc:

    runtime[
        "torch_metadata_error"
    ] = repr(
        exc
    )


write_json(
    OUT
    / "runtime_environment_r8a.json",
    runtime,
)


# ============================================================
# 10. Final receipt
# ============================================================

receipt = {
    "stage":
        "V26_EFFICIENCY_PROTOCOL_R8A",

    "status":
        "FROZEN_BEFORE_EFFICIENCY_PROFILING",

    "candidate":
        PROMOTED,

    "scientific_closure_bound":
        True,

    "comparison_model_count":
        11,

    "representative_dataset":
        REPRESENTATIVE_DATASET,

    "representative_seed":
        REPRESENTATIVE_SEED,

    "representative_num_classes":
        NUM_CLASSES,

    "input_length":
        INPUT_LENGTH,

    "input_channels":
        INPUT_CHANNELS,

    "checkpoint_manifest":
        "PASS_11_OF_11",

    "checkpoint_sha_verified":
        "PASS_11_OF_11",

    "timing_protocol_frozen":
        True,

    "cpu_batch1_measurement_iterations":
        1000,

    "gpu_batch1_measurement_iterations":
        1000,

    "gpu_batch64_measurement_iterations":
        500,

    "synthetic_input_only":
        True,

    "protected_test_access":
        False,

    "model_constructed":
        False,

    "checkpoint_deserialized":
        False,

    "tensor_created":
        False,

    "forward_performed":
        False,

    "training_performed":
        False,

    "candidate_modified":
        False,

    "storm_used":
        False,

    "deployment_claim_allowed":
        False,

    "next_gate":
        (
            "R8B implementation-integrity preflight: bind exact "
            "constructors for all 11 frozen checkpoints, verify "
            "strict checkpoint loading and parameter counts using "
            "synthetic inputs only, select one consistent complexity "
            "counter if available, then freeze the profiler before "
            "latency measurements."
        ),
}


write_json(
    OUT
    / "v26_efficiency_protocol_receipt_r8a.json",
    receipt,
)


print()
print("=" * 118)
print("V26 R8A FINAL RECEIPT")
print("=" * 118)

print(
    json.dumps(
        receipt,
        indent=2,
    )
)


print()
print(
    "V26_EFFICIENCY_PROTOCOL_R8A_PASS=True"
)

print(
    "EFFICIENCY_COMPARATOR_MODEL_SET_PASS_11=True"
)

print(
    "EFFICIENCY_FROZEN_CHECKPOINT_SHA_PASS_11_OF_11=True"
)

print(
    "EFFICIENCY_TIMING_PROTOCOL_FROZEN=True"
)

print(
    "MODEL_CONSTRUCTED=False"
)

print(
    "CHECKPOINT_DESERIALIZED=False"
)

print(
    "TENSOR_CREATED=False"
)

print(
    "FORWARD_PERFORMED=False"
)

print(
    "TEST_DATA_ACCESSED=False"
)

print(
    "TRAINING_PERFORMED=False"
)

print(
    "STORM_USED=False"
)
