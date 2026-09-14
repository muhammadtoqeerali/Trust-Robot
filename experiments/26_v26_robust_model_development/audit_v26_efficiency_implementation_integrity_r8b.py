from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

import torch


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

V26_EXP = (
    ROOT
    / "experiments"
    / "26_v26_robust_model_development"
)

R8A = (
    ROOT
    / "results"
    / "v26_efficiency_protocol_r8a"
)

IMPL = (
    ROOT
    / "results"
    / "v26_implementation_integrity_r2"
)

OUT = (
    ROOT
    / "results"
    / "v26_efficiency_implementation_integrity_r8b"
)

OUT.mkdir(
    parents=True,
    exist_ok=True,
)


for path in [
    SUITE,
    SCREEN,
    V26_EXP,
]:

    if str(path) not in sys.path:
        sys.path.insert(
            0,
            str(path),
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

from candidate_models_r2 import (
    create_v26_candidate,
    parameter_count,
)


V25 = "ReliabilityCNN_v25"

V26 = "V26C_DualGateLiteCons"

NUM_CLASSES = 6

INPUT_CHANNELS = 6

INPUT_LENGTH = 128


def sha256_file(
    path: Path,
):

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

            h.update(
                block
            )

    return h.hexdigest()


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
        +
        "\n"
    )


def load_state(
    path: Path,
):

    try:

        state = torch.load(
            path,
            map_location="cpu",
            weights_only=True,
        )

    except TypeError:

        state = torch.load(
            path,
            map_location="cpu",
        )


    if not isinstance(
        state,
        dict,
    ):

        raise RuntimeError(
            f"{path}: checkpoint is not dict"
        )


    if not state:

        raise RuntimeError(
            f"{path}: checkpoint is empty"
        )


    if not all(
        torch.is_tensor(
            value
        )
        for value in state.values()
    ):

        raise RuntimeError(
            f"{path}: checkpoint is not a direct "
            "tensor state_dict"
        )


    return state


def instantiate(
    model_name: str,
):

    if model_name == V25:

        return create_candidate(
            "V25Dense64",
            NUM_CLASSES,
            input_channels=INPUT_CHANNELS,
        )


    if model_name == V26:

        return create_v26_candidate(
            V26,
            NUM_CLASSES,
            input_channels=INPUT_CHANNELS,
        )


    return create_model(
        model_name,
        NUM_CLASSES,
        input_channels=INPUT_CHANNELS,
    )


def call_model(
    model_name,
    model,
    x,
):

    if model_name == V26:

        output = model(
            x
        )

    else:

        # Exact Stage25/V3R1 canonical input adaptation.
        output = model_forward(
            model,
            x,
        )


    if isinstance(
        output,
        (
            tuple,
            list,
        ),
    ):

        output = output[
            0
        ]


    return output


print("=" * 118)
print("V26 EFFICIENCY IMPLEMENTATION INTEGRITY R8B")
print("STRICT LOAD + SYNTHETIC FORWARD ONLY")
print("=" * 118)


# ============================================================
# 1. Bind R8A protocol
# ============================================================

protocol = json.loads(
    (
        R8A
        / "v26_efficiency_protocol_r8a.json"
    ).read_text()
)


required_protocol = {
    "status":
        "FROZEN_BEFORE_TIMING",

    "scientific_model":
        V26,

    "comparison_model_count":
        11,

    "model_changes_allowed":
        False,

    "checkpoint_changes_allowed":
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
}


for key, expected in required_protocol.items():

    actual = protocol.get(
        key
    )

    if actual != expected:

        raise RuntimeError(
            f"R8A protocol mismatch: "
            f"{key}={actual!r}; "
            f"expected={expected!r}"
        )


print(
    "R8A_FROZEN_TIMING_PROTOCOL_BOUND=True"
)


# ============================================================
# 2. Verify six frozen V26 implementation sources
# ============================================================

source_manifest = json.loads(
    (
        IMPL
        / "implementation_source_sha_manifest.json"
    ).read_text()
)


if len(
    source_manifest
) != 6:

    raise RuntimeError(
        f"Expected six frozen V26 source files, "
        f"found {len(source_manifest)}"
    )


for row in source_manifest:

    path = (
        ROOT
        / row[
            "path"
        ]
    )


    if not path.exists():

        raise FileNotFoundError(
            path
        )


    actual = sha256_file(
        path
    )


    if actual != row[
        "sha256"
    ]:

        raise RuntimeError(
            f"V26 frozen source drift: {path}"
        )


print(
    "V26_IMPLEMENTATION_SOURCE_SHA_PASS_6_OF_6=True"
)


# ============================================================
# 3. Frozen 11-checkpoint efficiency manifest
# ============================================================

manifest = read_csv(
    R8A
    / "efficiency_checkpoint_manifest_11.csv"
)


if len(
    manifest
) != 11:

    raise RuntimeError(
        f"Expected 11 efficiency checkpoints, "
        f"found {len(manifest)}"
    )


if len({
    row[
        "model"
    ]
    for row in manifest
}) != 11:

    raise RuntimeError(
        "Efficiency model identities not unique"
    )


# Preserve exact frozen order.
models = [
    row[
        "model"
    ]
    for row in manifest
]


print(
    "R8B_FROZEN_MODEL_ORDER=",
    ",".join(
        models
    ),
)


# ============================================================
# 4. MAC/FLOP methodological decision
# ============================================================

tool_rows = read_csv(
    R8A
    / "complexity_tool_availability.csv"
)


available_tools = [
    row[
        "package"
    ]

    for row in tool_rows

    if str(
        row[
            "available"
        ]
    ).lower()
    ==
    "true"
]


if available_tools:

    raise RuntimeError(
        "R8A recorded an available external "
        f"complexity tool unexpectedly: {available_tools}"
    )


mac_decision = {
    "status":
        "NOT_COMPARABLE",

    "reason":
        (
            "No preregistered architecture-consistent MAC/FLOP "
            "counter is available in the controlled environment, "
            "and existing frozen project profilers measure "
            "parameters/checkpoint bytes/runtime rather than "
            "one universal MAC/FLOP definition."
        ),

    "external_packages_available":
        [],

    "package_install_performed":
        False,

    "custom_mac_counter_created":
        False,

    "post_result_counter_selection":
        False,

    "report_mac_flop_number":
        False,

    "paper_field":
        (
            "MAC/FLOP not compared under the frozen host "
            "efficiency protocol; parameters, checkpoint bytes, "
            "CPU latency, GPU latency and throughput reported."
        ),
}


write_json(
    OUT
    / "mac_flop_comparability_decision.json",
    mac_decision,
)


print(
    "R8B_MAC_FLOP_COMPARABILITY_STATUS=NOT_COMPARABLE"
)

print(
    "R8B_PACKAGE_INSTALL_PERFORMED=False"
)

print(
    "R8B_CUSTOM_MAC_COUNTER_CREATED=False"
)


# ============================================================
# 5. Strict construction/load/forward integrity
#
# CPU only.
# Synthetic zeros only.
# No timings recorded.
# ============================================================

torch.set_num_threads(
    1
)

torch.set_num_interop_threads(
    1
)


x1 = torch.zeros(
    (
        1,
        INPUT_LENGTH,
        INPUT_CHANNELS,
    ),
    dtype=torch.float32,
)


x64 = torch.zeros(
    (
        64,
        INPUT_LENGTH,
        INPUT_CHANNELS,
    ),
    dtype=torch.float32,
)


results = []


for row in manifest:

    model_name = row[
        "model"
    ]


    checkpoint = (
        ROOT
        / row[
            "checkpoint"
        ]
    )


    expected_sha = row[
        "checkpoint_sha256"
    ]


    actual_sha = sha256_file(
        checkpoint
    )


    if actual_sha != expected_sha:

        raise RuntimeError(
            f"{model_name}: frozen checkpoint SHA mismatch"
        )


    model = instantiate(
        model_name
    )


    model.eval()


    actual_params = int(
        sum(
            parameter.numel()
            for parameter
            in model.parameters()
        )
    )


    expected_params = int(
        row[
            "parameter_count_frozen"
        ]
    )


    if actual_params != expected_params:

        raise RuntimeError(
            f"{model_name}: parameter mismatch; "
            f"expected={expected_params}; "
            f"actual={actual_params}"
        )


    state = load_state(
        checkpoint
    )


    incompat = model.load_state_dict(
        state,
        strict=True,
    )


    if (
        list(
            incompat.missing_keys
        )
        or
        list(
            incompat.unexpected_keys
        )
    ):

        raise RuntimeError(
            f"{model_name}: strict state load mismatch"
        )


    with torch.inference_mode():

        y1 = call_model(
            model_name,
            model,
            x1,
        )


        y64 = call_model(
            model_name,
            model,
            x64,
        )


    expected_shape_1 = (
        1,
        NUM_CLASSES,
    )

    expected_shape_64 = (
        64,
        NUM_CLASSES,
    )


    if tuple(
        y1.shape
    ) != expected_shape_1:

        raise RuntimeError(
            f"{model_name}: batch1 output "
            f"shape={tuple(y1.shape)}, "
            f"expected={expected_shape_1}"
        )


    if tuple(
        y64.shape
    ) != expected_shape_64:

        raise RuntimeError(
            f"{model_name}: batch64 output "
            f"shape={tuple(y64.shape)}, "
            f"expected={expected_shape_64}"
        )


    if not torch.isfinite(
        y1
    ).all():

        raise RuntimeError(
            f"{model_name}: nonfinite batch1 output"
        )


    if not torch.isfinite(
        y64
    ).all():

        raise RuntimeError(
            f"{model_name}: nonfinite batch64 output"
        )


    if model_name == V26:

        v26_helper_params = int(
            parameter_count(
                model
            )
        )


        if v26_helper_params != actual_params:

            raise RuntimeError(
                "V26 parameter_count helper mismatch"
            )

    else:

        v26_helper_params = ""


    result = {
        "model":
            model_name,

        "checkpoint":
            row[
                "checkpoint"
            ],

        "checkpoint_sha256":
            actual_sha,

        "expected_parameter_count":
            expected_params,

        "constructed_parameter_count":
            actual_params,

        "parameter_count_match":
            True,

        "strict_checkpoint_load":
            True,

        "batch1_input_shape":
            str(
                tuple(
                    x1.shape
                )
            ),

        "batch1_output_shape":
            str(
                tuple(
                    y1.shape
                )
            ),

        "batch1_forward_pass":
            True,

        "batch64_input_shape":
            str(
                tuple(
                    x64.shape
                )
            ),

        "batch64_output_shape":
            str(
                tuple(
                    y64.shape
                )
            ),

        "batch64_forward_pass":
            True,

        "output_finite":
            True,

        "v26_parameter_helper_count":
            v26_helper_params,
    }


    results.append(
        result
    )


    print(
        "R8B_MODEL_INTEGRITY_PASS:",
        model_name,
        "PARAMS=",
        actual_params,
        "B1=",
        tuple(
            y1.shape
        ),
        "B64=",
        tuple(
            y64.shape
        ),
        flush=True,
    )


    del state
    del model
    del y1
    del y64


if len(
    results
) != 11:

    raise RuntimeError(
        "R8B model integrity count != 11"
    )


write_csv(
    OUT
    / "model_integrity_manifest_11.csv",
    results,
)


print(
    "R8B_MODEL_CONSTRUCTION_PASS_11_OF_11=True"
)

print(
    "R8B_PARAMETER_COUNT_PASS_11_OF_11=True"
)

print(
    "R8B_STRICT_CHECKPOINT_LOAD_PASS_11_OF_11=True"
)

print(
    "R8B_SYNTHETIC_BATCH1_FORWARD_PASS_11_OF_11=True"
)

print(
    "R8B_SYNTHETIC_BATCH64_FORWARD_PASS_11_OF_11=True"
)


# ============================================================
# 6. Freeze timing implementation contract
#
# This does NOT execute timing.
# ============================================================

timing_contract = {
    "stage":
        "V26_EFFICIENCY_R8B_TIMING_IMPLEMENTATION_CONTRACT",

    "status":
        "READY_TO_FREEZE_PROFILER",

    "model_count":
        11,

    "model_order":
        models,

    "constructors": {
        "v3r1_9_models":
            (
                "engine.model_registry.create_model("
                "model_name, 6, input_channels=6)"
            ),

        "v25":
            (
                "v25_candidates.create_candidate("
                "'V25Dense64', 6, input_channels=6)"
            ),

        "v26c":
            (
                "candidate_models_r2.create_v26_candidate("
                "'V26C_DualGateLiteCons', 6, input_channels=6)"
            ),
    },

    "forward_adapter": {
        "v3r1_and_v25":
            "engine.model_forward.model_forward",

        "v26c":
            "direct frozen model forward",
    },

    "synthetic_inputs": {
        "dtype":
            "float32",

        "batch1_shape":
            [
                1,
                128,
                6,
            ],

        "batch64_shape":
            [
                64,
                128,
                6,
            ],

        "values":
            "zeros",
    },

    "cpu": {
        "threads":
            1,

        "batch":
            1,

        "warmup":
            200,

        "iterations":
            1000,

        "latency_statistics": [
            "mean_ms",
            "median_ms",
        ],

        "clock":
            "time.perf_counter",

        "input_transfer_timed":
            False,
    },

    "gpu_batch1": {
        "device":
            "cuda:0",

        "batch":
            1,

        "warmup":
            200,

        "iterations":
            1000,

        "latency_statistics": [
            "mean_ms",
            "median_ms",
        ],

        "synchronization":
            (
                "CUDA synchronize before each measured "
                "forward and immediately after each "
                "measured forward"
            ),

        "input_transfer_timed":
            False,
    },

    "gpu_batch64": {
        "device":
            "cuda:0",

        "batch":
            64,

        "warmup":
            100,

        "iterations":
            500,

        "metric":
            "samples_per_second",

        "measurement":
            (
                "one synchronized wall-clock region "
                "covering exactly 500 forwards"
            ),

        "input_transfer_timed":
            False,
    },

    "model_eval":
        True,

    "inference_mode":
        True,

    "torch_compile":
        False,

    "amp":
        False,

    "quantization":
        False,

    "graph_optimization":
        False,

    "mac_flop":
        "NOT_COMPARABLE",

    "test_data_access":
        False,

    "training":
        False,

    "storm":
        False,

    "deployment_claim":
        False,
}


write_json(
    OUT
    / "timing_implementation_contract_r8b.json",
    timing_contract,
)


print(
    "R8B_TIMING_IMPLEMENTATION_CONTRACT_FROZEN=True"
)


# ============================================================
# 7. Final receipt
# ============================================================

receipt = {
    "stage":
        "V26_EFFICIENCY_IMPLEMENTATION_INTEGRITY_R8B",

    "status":
        "PASS",

    "comparison_models":
        11,

    "model_construction":
        "PASS_11_OF_11",

    "parameter_count":
        "PASS_11_OF_11",

    "checkpoint_sha":
        "PASS_11_OF_11",

    "strict_checkpoint_load":
        "PASS_11_OF_11",

    "synthetic_batch1_forward":
        "PASS_11_OF_11",

    "synthetic_batch64_forward":
        "PASS_11_OF_11",

    "output_shape":
        "PASS_22_OF_22",

    "mac_flop_comparability":
        "NOT_COMPARABLE",

    "external_complexity_package_install":
        False,

    "custom_mac_counter_created":
        False,

    "protected_test_access":
        False,

    "real_dataset_access":
        False,

    "synthetic_tensor_only":
        True,

    "model_constructed":
        True,

    "checkpoint_deserialized":
        True,

    "forward_performed":
        True,

    "latency_timing_performed":
        False,

    "throughput_timing_performed":
        False,

    "training_performed":
        False,

    "optimizer_created":
        False,

    "candidate_modified":
        False,

    "checkpoint_modified":
        False,

    "storm_used":
        False,

    "deployment_claim_allowed":
        False,

    "next_gate":
        (
            "Create and freeze R8C timing profiler exactly "
            "from timing_implementation_contract_r8b.json, "
            "then run the fixed CPU batch1, GPU batch1 and "
            "GPU batch64 measurements once for all 11 models."
        ),
}


write_json(
    OUT
    / "v26_efficiency_implementation_integrity_receipt_r8b.json",
    receipt,
)


print()
print("=" * 118)
print("V26 R8B FINAL RECEIPT")
print("=" * 118)

print(
    json.dumps(
        receipt,
        indent=2,
    )
)


print()
print(
    "V26_EFFICIENCY_IMPLEMENTATION_INTEGRITY_R8B_PASS=True"
)

print(
    "LATENCY_TIMING_PERFORMED=False"
)

print(
    "THROUGHPUT_TIMING_PERFORMED=False"
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
