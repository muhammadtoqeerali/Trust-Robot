from pathlib import Path
import hashlib
import importlib.util
import json
import sys

import pandas as pd
import torch
import torch.nn as nn


REPO = Path.cwd()

SCREEN = (
    REPO /
    "experiments" /
    "17_v25_screening"
)

sys.path.insert(
    0,
    str(SCREEN)
)

from v25_candidates import create_candidate


FINAL_ROOT = (
    REPO /
    "results" /
    "v25_final_r2"
)

OUT = (
    FINAL_ROOT /
    "mcu_readiness_r1"
)

MANIFEST = (
    FINAL_ROOT /
    "protocol" /
    "protocol_manifest.json"
)

FINAL_RECEIPT = (
    FINAL_ROOT /
    "final_analysis" /
    "v25_final_r2_analysis_receipt.json"
)


MODEL_NAME = "ReliabilityCNN_v25"

ARCHITECTURE = "V25Dense64"


DATASETS = {
    "UCI_HAR": 6,
    "PAMAP2": 12,
    "DSADS": 19,
    "MotionSense": 6,
}


SEED = 42


def load_json(path):

    return json.loads(
        Path(path).read_text()
    )


def sha256_file(path):

    h = hashlib.sha256()

    with Path(path).open("rb") as f:

        for block in iter(
            lambda: f.read(1024 * 1024),
            b""
        ):
            h.update(block)

    return h.hexdigest()


print("=" * 94)
print("RELIABILITYCNN V25 — MCU DEPLOYMENT READINESS AUDIT R1")
print("=" * 94)


# ----------------------------------------------------------
# 1. Final evidence integrity
# ----------------------------------------------------------

receipt = load_json(
    FINAL_RECEIPT
)

if not receipt.get(
    "integrity_pass",
    False
):
    raise RuntimeError(
        "Final V25 evidence receipt is not PASS"
    )


manifest = load_json(
    MANIFEST
)


verified = 0


for relative, expected in (
    manifest["hashes"].items()
):

    path = REPO / relative

    if not path.exists():
        raise FileNotFoundError(path)

    actual = sha256_file(path)

    if actual != expected:
        raise RuntimeError(
            f"Frozen input changed: {relative}"
        )

    verified += 1


print(
    "FINAL_FROZEN_HASHES_VERIFIED=",
    verified,
    "/",
    len(manifest["hashes"])
)

print(
    "FINAL_ANALYSIS_RECEIPT_PASS=True"
)


# ----------------------------------------------------------
# 2. Audit helpers
# ----------------------------------------------------------

def checkpoint(dataset):

    return (
        FINAL_ROOT /
        "raw_runs" /
        dataset /
        MODEL_NAME /
        f"seed_{SEED}" /
        "checkpoint.pt"
    )


def load_state(path):

    try:
        return torch.load(
            path,
            map_location="cpu",
            weights_only=True
        )
    except TypeError:
        return torch.load(
            path,
            map_location="cpu"
        )


def tensor_count(obj):

    if torch.is_tensor(obj):
        return obj.numel()

    if isinstance(obj, (list, tuple)):
        return sum(
            tensor_count(x)
            for x in obj
        )

    return 0


# ----------------------------------------------------------
# 3. Model footprint + MAC audit
# ----------------------------------------------------------

rows = []

all_operator_kinds = set()


for dataset, classes in DATASETS.items():

    ckpt = checkpoint(dataset)

    if not ckpt.exists():
        raise FileNotFoundError(ckpt)


    model = create_candidate(
        ARCHITECTURE,
        classes,
        input_channels=6
    )


    model.load_state_dict(
        load_state(ckpt),
        strict=True
    )

    model.eval()


    params = sum(
        p.numel()
        for p in model.parameters()
    )


    parameter_bytes_fp32 = sum(
        p.numel() * p.element_size()
        for p in model.parameters()
    )


    buffer_bytes_fp32 = sum(
        b.numel() * b.element_size()
        for b in model.buffers()
    )


    # Conservative lower bound only:
    # 1 byte per learned scalar.
    int8_parameter_payload_lower_bound = params


    macs = 0

    largest_activation_elements = 0

    activation_records = []


    def hook(module, inputs, output):

        nonlocal_state = None

        elements = tensor_count(output)

        activation_records.append(
            {
                "module":
                    module.__class__.__name__,

                "elements":
                    elements,
            }
        )


    hooks = []


    for module in model.modules():

        if module is model:
            continue

        hooks.append(
            module.register_forward_hook(
                hook
            )
        )


    mac_holder = {
        "macs": 0
    }


    def conv_hook(module, inputs, output):

        x = inputs[0]

        out = output

        batch = out.shape[0]

        out_channels = out.shape[1]

        out_length = out.shape[2]

        kernel = module.kernel_size[0]

        cin_per_group = (
            module.in_channels
            //
            module.groups
        )

        mac_holder["macs"] += (
            batch
            *
            out_channels
            *
            out_length
            *
            cin_per_group
            *
            kernel
        )


    def linear_hook(module, inputs, output):

        output_elements = output.numel()

        mac_holder["macs"] += (
            output_elements
            *
            module.in_features
        )


    mac_hooks = []


    for module in model.modules():

        if isinstance(
            module,
            nn.Conv1d
        ):
            mac_hooks.append(
                module.register_forward_hook(
                    conv_hook
                )
            )

        elif isinstance(
            module,
            nn.Linear
        ):
            mac_hooks.append(
                module.register_forward_hook(
                    linear_hook
                )
            )


    x = torch.zeros(
        1,
        128,
        6
    )


    with torch.inference_mode():

        logits = model(x)


    for h in hooks + mac_hooks:
        h.remove()


    if tuple(logits.shape) != (
        1,
        classes
    ):
        raise RuntimeError(
            f"Output shape mismatch: {dataset}"
        )


    largest_activation_elements = max(
        row["elements"]
        for row in activation_records
    )


    # Tensor-level lower bound only.
    largest_activation_fp32_bytes = (
        largest_activation_elements * 4
    )

    largest_activation_int8_bytes = (
        largest_activation_elements
    )


    # Trace the real forward graph and record
    # all ATen operators used by the model.
    traced = torch.jit.trace(
        model,
        x,
        strict=True
    )


    traced(x)


    operator_kinds = sorted({
        node.kind()
        for node in traced.inlined_graph.nodes()
    })


    all_operator_kinds.update(
        operator_kinds
    )


    trace_path = (
        OUT /
        f"{dataset}_seed42_traced.pt"
    )


    traced.save(
        str(trace_path)
    )


    # Optional ONNX export. Do not alter the
    # environment just to satisfy this audit.
    onnx_available = (
        importlib.util.find_spec(
            "onnx"
        )
        is not None
    )


    onnx_exported = False

    onnx_error = None

    onnx_path = (
        OUT /
        f"{dataset}_seed42.onnx"
    )


    if onnx_available:

        try:

            torch.onnx.export(
                model,
                x,
                str(onnx_path),
                input_names=["imu"],
                output_names=["logits"],
                opset_version=17,
                do_constant_folding=True,
                dynamic_axes=None,
            )

            onnx_exported = (
                onnx_path.exists()
            )

        except Exception as exc:

            onnx_error = (
                type(exc).__name__
                +
                ": "
                +
                str(exc)
            )


    rows.append({
        "dataset":
            dataset,

        "classes":
            classes,

        "parameters":
            params,

        "parameter_bytes_fp32":
            parameter_bytes_fp32,

        "buffer_bytes_fp32":
            buffer_bytes_fp32,

        "estimated_int8_parameter_payload_lower_bound_bytes":
            int8_parameter_payload_lower_bound,

        "macs_per_window":
            int(
                mac_holder["macs"]
            ),

        "largest_single_activation_elements":
            largest_activation_elements,

        "largest_single_activation_fp32_bytes":
            largest_activation_fp32_bytes,

        "largest_single_activation_int8_bytes":
            largest_activation_int8_bytes,

        "checkpoint_bytes":
            ckpt.stat().st_size,

        "checkpoint_sha256":
            sha256_file(ckpt),

        "torchscript_trace_pass":
            True,

        "torchscript_bytes":
            trace_path.stat().st_size,

        "onnx_package_available":
            onnx_available,

        "onnx_exported":
            onnx_exported,

        "onnx_error":
            onnx_error,

        "operator_count":
            len(operator_kinds),

        "operator_kinds":
            ";".join(operator_kinds),
    })


    print()
    print(
        "MCU_READINESS_PASS:",
        dataset
    )

    print(
        " PARAMS=",
        params
    )

    print(
        " FP32_PARAMETER_BYTES=",
        parameter_bytes_fp32
    )

    print(
        " INT8_WEIGHT_LOWER_BOUND_BYTES=",
        int8_parameter_payload_lower_bound
    )

    print(
        " MACS_PER_WINDOW=",
        int(mac_holder["macs"])
    )

    print(
        " MAX_SINGLE_ACTIVATION_FP32_BYTES=",
        largest_activation_fp32_bytes
    )

    print(
        " MAX_SINGLE_ACTIVATION_INT8_BYTES=",
        largest_activation_int8_bytes
    )

    print(
        " TORCHSCRIPT_TRACE_PASS=True"
    )

    print(
        " ONNX_AVAILABLE=",
        onnx_available
    )

    print(
        " ONNX_EXPORTED=",
        onnx_exported
    )


df = pd.DataFrame(
    rows
)


df.to_csv(
    OUT /
    "v25_mcu_readiness_per_dataset_4.csv",
    index=False
)


# ----------------------------------------------------------
# 4. Worst-case deployment envelope
# ----------------------------------------------------------

worst = {
    "max_parameters":
        int(df["parameters"].max()),

    "max_fp32_parameter_bytes":
        int(
            df[
                "parameter_bytes_fp32"
            ].max()
        ),

    "max_estimated_int8_parameter_payload_lower_bound_bytes":
        int(
            df[
                "estimated_int8_parameter_payload_lower_bound_bytes"
            ].max()
        ),

    "max_macs_per_window":
        int(
            df[
                "macs_per_window"
            ].max()
        ),

    "max_single_activation_fp32_bytes":
        int(
            df[
                "largest_single_activation_fp32_bytes"
            ].max()
        ),

    "max_single_activation_int8_bytes":
        int(
            df[
                "largest_single_activation_int8_bytes"
            ].max()
        ),

    "important_memory_boundary":
        (
            "Single-activation values are lower bounds, "
            "not compiler-measured peak SRAM. Real MCU "
            "peak memory must be measured after graph "
            "conversion, buffer planning, and kernel fusion."
        ),

    "important_int8_boundary":
        (
            "One-byte-per-parameter is a payload lower "
            "bound only. Biases, scales, alignment and "
            "runtime metadata increase deployed flash."
        ),
}


(
    OUT /
    "v25_mcu_worst_case_envelope.json"
).write_text(
    json.dumps(
        worst,
        indent=2,
        sort_keys=True
    )
)


(
    OUT /
    "v25_torchscript_operator_inventory.txt"
).write_text(
    "\n".join(
        sorted(all_operator_kinds)
    )
    +
    "\n"
)


# ----------------------------------------------------------
# 5. Final receipt
# ----------------------------------------------------------

receipt = {
    "audit":
        "v25_mcu_readiness_r1",

    "training_executed":
        False,

    "reliability_executed":
        False,

    "scientific_checkpoint_modified":
        False,

    "checkpoint_seed":
        SEED,

    "datasets":
        list(DATASETS),

    "model":
        MODEL_NAME,

    "architecture":
        ARCHITECTURE,

    "worst_case_envelope":
        worst,

    "operator_inventory":
        sorted(all_operator_kinds),

    "deployment_claim_allowed":
        False,

    "reason_deployment_claim_not_yet_allowed":
        (
            "No physical MCU latency, peak SRAM, "
            "flash footprint, or energy measurement "
            "has yet been performed."
        ),
}


receipt_path = (
    OUT /
    "v25_mcu_readiness_receipt.json"
)


receipt_path.write_text(
    json.dumps(
        receipt,
        indent=2,
        sort_keys=True
    )
)


print()
print("=" * 94)
print("WORST-CASE MCU READINESS ENVELOPE")
print("=" * 94)

for key, value in worst.items():
    print(key, "=", value)


print()
print(
    "OPERATOR_INVENTORY="
)

for op in sorted(all_operator_kinds):
    print(" ", op)


print()
print(
    "MCU_READINESS_RECEIPT=",
    receipt_path
)

print(
    "MCU_READINESS_RECEIPT_SHA256=",
    sha256_file(receipt_path)
)

print()
print("=" * 94)

print("MCU_READINESS_DATASETS=4")
print("TRAINING_RERUN=False")
print("RELIABILITY_RERUN=False")
print("SCIENTIFIC_CHECKPOINT_MODIFIED=False")
print("DEPLOYMENT_CLAIM_ALLOWED=False")
print("V25_MCU_READINESS_R1_PASS=True")

print("=" * 94)
