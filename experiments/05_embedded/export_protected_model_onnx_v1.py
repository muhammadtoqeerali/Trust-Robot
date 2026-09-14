from __future__ import annotations

import importlib
import importlib.util
import json
import math
import subprocess
import sys
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

import numpy as np
import torch

from imu_reliability.baseline.historical_decision import (
    decision_from_logits,
)
from imu_reliability.integrity import (
    assess_evidence,
)
from imu_reliability.runtime import (
    TrustState,
    decide_from_logits,
)


ROOT = Path(
    __file__
).resolve().parents[2]


PROTOCOL = (
    ROOT
    / "configs/embedded/"
      "prospective_protected_model_export_protocol_v1.json"
)

LOADER = (
    ROOT
    / "experiments/03_ood/"
      "evaluate_ood_calibration_v1b.py"
)

MODEL_SOURCE = (
    ROOT
    / "src/imu_reliability/baseline/"
      "date2025_cnn400.py"
)

CHECKPOINT = Path(
    "/mnt/hdd16T/protechto/checkpoints/CNN/400ms/"
    "2025-02-25_12_24_47/best-checkpoint.ckpt"
)

ONNX_ARTIFACT = (
    ROOT
    / "artifacts/embedded/prospective/"
      "date2025_cnn400_fp32_v1.onnx"
)

RESULT = (
    ROOT
    / "results/raw/"
      "prospective_model_export_v1_candidate.json"
)


EXPORT_PROTOCOL_COMMIT = (
    "7229081206d0b4cfe3249792282f0aa87abb9220"
)

PORTABLE_C_IMPLEMENTATION_COMMIT = (
    "3f0db77158cc59e4273f75b076fef53aa6b1f413"
)

REFERENCE_RUNTIME_COMMIT = (
    "4755a74fe558021576934674e338865a36df5b55"
)


PROTOCOL_RAW_SHA256 = (
    "5574278d42584f03ec39274c287c4832"
    "9b2dbbad49f25e77024d1b17ad94fdf3"
)

PROTOCOL_CONTENT_SHA256 = (
    "714eda4d82caf56de2b023cfc04bac0d"
    "e0f400323a3cefc9077db3ecfdc122ee"
)

LOADER_RAW_SHA256 = (
    "6462829b7ffee3ca19dc25b7a605a3b7"
    "dd38ddf6bfb10a34ca8d098c0ae415df"
)

MODEL_SOURCE_RAW_SHA256 = (
    "def71b3cebc0649c0d909e4ffd5dc04f"
    "177fcb795ff6ebfd13f90e214c67581d"
)

CHECKPOINT_SHA256 = (
    "ee7c0079bfb8555bff45c3077cc24eaa"
    "4373c57729045d92a831a1d7a3ea9bb1"
)


OPSET_VERSION = 13

ATOL = 1.0e-5
RTOL = 1.0e-5

OOD_THRESHOLD = (
    0.00914505124092102
)

HISTORICAL_BIAS = (
    0.9
)

INPUT_NAME = (
    "imu_window"
)

OUTPUT_NAME = (
    "logits"
)

INPUT_SHAPE = (
    1,
    40,
    9,
)

OUTPUT_SHAPE = (
    1,
    2,
)

STRUCTURED_VECTOR_COUNT = 4
MODULAR_VECTOR_COUNT = 64
TOTAL_VECTOR_COUNT = 68


def raw_sha256(
    path: Path,
) -> str:
    return sha256(
        path.read_bytes()
    ).hexdigest()


def canonical_digest(
    payload,
) -> str:
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


def git(
    *args: str,
) -> str:
    return subprocess.check_output(
        [
            "/usr/bin/git",
            *args,
        ],
        cwd=ROOT,
        text=True,
    ).strip()


def verify_git_anchors() -> None:
    expected = {
        "prospective-protected-model-export-protocol-v1^{commit}":
            EXPORT_PROTOCOL_COMMIT,

        "portable-c-runtime-implementation-v1^{commit}":
            PORTABLE_C_IMPLEMENTATION_COMMIT,

        "runtime-reference-implementation-v1^{commit}":
            REFERENCE_RUNTIME_COMMIT,
    }

    for ref, expected_commit in expected.items():
        observed = git(
            "rev-parse",
            ref,
        )

        if observed != expected_commit:
            raise RuntimeError(
                f"Frozen ref moved: {ref}"
            )

    for ref in (
        "prospective-protected-model-export-protocol-v1",
        "portable-c-runtime-implementation-v1",
        "runtime-reference-implementation-v1",
    ):
        rc = subprocess.run(
            [
                "/usr/bin/git",
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
                f"Frozen ref is not ancestor: {ref}"
            )


def verify_protocol() -> dict:
    if raw_sha256(
        PROTOCOL
    ) != PROTOCOL_RAW_SHA256:
        raise RuntimeError(
            "Frozen export protocol raw bytes changed"
        )

    protocol = json.loads(
        PROTOCOL.read_text()
    )

    payload = deepcopy(
        protocol
    )

    stored = payload.pop(
        "content_sha256"
    )

    computed = canonical_digest(
        payload
    )

    if not (
        stored
        == computed
        == PROTOCOL_CONTENT_SHA256
    ):
        raise RuntimeError(
            "Frozen export protocol content changed"
        )

    if (
        protocol[
            "export_scope"
        ][
            "format"
        ]
        != "ONNX"
    ):
        raise RuntimeError(
            "Export format changed"
        )

    if (
        protocol[
            "export_scope"
        ][
            "precision"
        ]
        != "float32"
    ):
        raise RuntimeError(
            "Export precision changed"
        )

    if (
        protocol[
            "export_scope"
        ][
            "opset_version"
        ]
        != OPSET_VERSION
    ):
        raise RuntimeError(
            "ONNX opset changed"
        )

    if (
        tuple(
            protocol[
                "tensor_contract"
            ][
                "input_shape"
            ]
        )
        != INPUT_SHAPE
    ):
        raise RuntimeError(
            "Input shape changed"
        )

    if (
        tuple(
            protocol[
                "tensor_contract"
            ][
                "output_shape"
            ]
        )
        != OUTPUT_SHAPE
    ):
        raise RuntimeError(
            "Output shape changed"
        )

    if (
        protocol[
            "deterministic_parity_input_contract"
        ][
            "total_vector_count"
        ]
        != TOTAL_VECTOR_COUNT
    ):
        raise RuntimeError(
            "Parity vector count changed"
        )

    return protocol


def verify_source_anchors() -> None:
    expected = {
        LOADER:
            LOADER_RAW_SHA256,

        MODEL_SOURCE:
            MODEL_SOURCE_RAW_SHA256,

        CHECKPOINT:
            CHECKPOINT_SHA256,
    }

    for path, expected_sha in expected.items():
        if not path.is_file():
            raise RuntimeError(
                f"Required source absent: {path}"
            )

        observed = raw_sha256(
            path
        )

        if observed != expected_sha:
            raise RuntimeError(
                f"Source anchor changed: {path}"
            )


def load_export_dependencies():
    missing = []

    for name in (
        "onnx",
        "onnxruntime",
    ):
        if importlib.util.find_spec(
            name
        ) is None:
            missing.append(
                name
            )

    if missing:
        raise RuntimeError(
            "Required pre-existing export dependencies absent: "
            + ", ".join(
                missing
            )
        )

    onnx = importlib.import_module(
        "onnx"
    )

    ort = importlib.import_module(
        "onnxruntime"
    )

    return (
        onnx,
        ort,
    )


def load_protected_model():
    verify_source_anchors()

    spec = importlib.util.spec_from_file_location(
        "prospective_export_v1b_loader",
        LOADER,
    )

    if (
        spec is None
        or spec.loader is None
    ):
        raise RuntimeError(
            "Unable to import pinned V1b loader"
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

    loaded = module.load_protected_model()

    if isinstance(
        loaded,
        torch.nn.Module,
    ):
        model = loaded

    elif (
        isinstance(
            loaded,
            tuple,
        )
        and len(
            loaded
        ) >= 1
        and isinstance(
            loaded[
                0
            ],
            torch.nn.Module,
        )
    ):
        model = loaded[
            0
        ]

    else:
        raise RuntimeError(
            "Pinned loader did not return torch model"
        )

    model.cpu()
    model.eval()

    if model.training:
        raise RuntimeError(
            "Protected model is not in eval mode"
        )

    return model


def structured_vectors() -> list[np.ndarray]:
    vectors = [
        np.zeros(
            INPUT_SHAPE,
            dtype=np.float32,
        ),

        np.ones(
            INPUT_SHAPE,
            dtype=np.float32,
        ),

        -np.ones(
            INPUT_SHAPE,
            dtype=np.float32,
        ),

        np.linspace(
            -1.0,
            1.0,
            num=360,
            dtype=np.float32,
        ).reshape(
            INPUT_SHAPE
        ),
    ]

    if len(
        vectors
    ) != STRUCTURED_VECTOR_COUNT:
        raise RuntimeError(
            "Structured-vector count mismatch"
        )

    return vectors


def modular_vectors() -> list[np.ndarray]:
    vectors = []

    for i in range(
        MODULAR_VECTOR_COUNT
    ):
        window = np.empty(
            INPUT_SHAPE,
            dtype=np.float32,
        )

        for t in range(
            40
        ):
            for c in range(
                9
            ):
                numerator = (
                    (
                        i * 37
                        + t * 17
                        + c * 13
                    )
                    % 257
                ) - 128

                window[
                    0,
                    t,
                    c,
                ] = np.float32(
                    numerator
                    / 64.0
                )

        vectors.append(
            window
        )

    if len(
        vectors
    ) != MODULAR_VECTOR_COUNT:
        raise RuntimeError(
            "Modular-vector count mismatch"
        )

    return vectors


def parity_vectors() -> list[np.ndarray]:
    vectors = (
        structured_vectors()
        + modular_vectors()
    )

    if len(
        vectors
    ) != TOTAL_VECTOR_COUNT:
        raise RuntimeError(
            "Total parity-vector count mismatch"
        )

    for vector in vectors:
        if (
            vector.dtype
            != np.float32
        ):
            raise RuntimeError(
                "Parity vector dtype changed"
            )

        if tuple(
            vector.shape
        ) != INPUT_SHAPE:
            raise RuntimeError(
                "Parity vector shape changed"
            )

    return vectors


def export_model(
    model,
) -> None:
    if ONNX_ARTIFACT.exists():
        raise RuntimeError(
            "Refusing to overwrite prospective ONNX artifact"
        )

    ONNX_ARTIFACT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    dummy = torch.from_numpy(
        structured_vectors()[
            0
        ]
    )

    with torch.inference_mode():
        torch.onnx.export(
            model,
            (
                dummy,
            ),
            str(
                ONNX_ARTIFACT
            ),
            export_params=True,
            verbose=False,
            input_names=[
                INPUT_NAME,
            ],
            output_names=[
                OUTPUT_NAME,
            ],
            opset_version=OPSET_VERSION,
            dynamic_axes=None,
            keep_initializers_as_inputs=False,
            dynamo=False,
            external_data=False,
            training=(
                torch.onnx
                .TrainingMode
                .EVAL
            ),
            do_constant_folding=True,
        )

    if not ONNX_ARTIFACT.is_file():
        raise RuntimeError(
            "ONNX export did not produce artifact"
        )


def tensor_shape(
    value_info,
) -> list[int]:
    tensor_type = (
        value_info
        .type
        .tensor_type
    )

    dims = []

    for dim in (
        tensor_type
        .shape
        .dim
    ):
        if dim.dim_param:
            raise RuntimeError(
                "Dynamic ONNX dimension found"
            )

        if not dim.HasField(
            "dim_value"
        ):
            raise RuntimeError(
                "ONNX dimension lacks fixed value"
            )

        dims.append(
            int(
                dim.dim_value
            )
        )

    return dims


def validate_graph(
    onnx,
) -> dict:
    graph_model = onnx.load(
        str(
            ONNX_ARTIFACT
        ),
        load_external_data=False,
    )

    onnx.checker.check_model(
        graph_model
    )

    graph = (
        graph_model
        .graph
    )

    if len(
        graph.input
    ) != 1:
        raise RuntimeError(
            "Expected exactly one ONNX graph input"
        )

    if len(
        graph.output
    ) != 1:
        raise RuntimeError(
            "Expected exactly one ONNX graph output"
        )

    graph_input = graph.input[
        0
    ]

    graph_output = graph.output[
        0
    ]

    if (
        graph_input.name
        != INPUT_NAME
    ):
        raise RuntimeError(
            "ONNX input name mismatch"
        )

    if (
        graph_output.name
        != OUTPUT_NAME
    ):
        raise RuntimeError(
            "ONNX output name mismatch"
        )

    input_shape = tensor_shape(
        graph_input
    )

    output_shape = tensor_shape(
        graph_output
    )

    if input_shape != list(
        INPUT_SHAPE
    ):
        raise RuntimeError(
            "ONNX fixed input shape mismatch"
        )

    if output_shape != list(
        OUTPUT_SHAPE
    ):
        raise RuntimeError(
            "ONNX fixed output shape mismatch"
        )

    float_type = (
        onnx.TensorProto.FLOAT
    )

    if (
        graph_input
        .type
        .tensor_type
        .elem_type
        != float_type
    ):
        raise RuntimeError(
            "ONNX input dtype is not float32"
        )

    if (
        graph_output
        .type
        .tensor_type
        .elem_type
        != float_type
    ):
        raise RuntimeError(
            "ONNX output dtype is not float32"
        )

    for initializer in graph.initializer:
        if (
            initializer.data_location
            == onnx.TensorProto.EXTERNAL
        ):
            raise RuntimeError(
                "External ONNX tensor data found"
            )

        if len(
            initializer.external_data
        ) != 0:
            raise RuntimeError(
                "External ONNX tensor metadata found"
            )

    op_types = [
        node.op_type
        for node in graph.node
    ]

    return {
        "graph_input_name":
            graph_input.name,

        "graph_output_name":
            graph_output.name,

        "graph_input_shape":
            input_shape,

        "graph_output_shape":
            output_shape,

        "graph_node_count":
            len(
                graph.node
            ),

        "graph_initializer_count":
            len(
                graph.initializer
            ),

        "graph_op_types":
            sorted(
                set(
                    op_types
                )
            ),

        "external_data_used":
            False,
    }


def empty_assessment():
    return assess_evidence(
        []
    )


def relative_error(
    candidate: np.ndarray,
    reference: np.ndarray,
) -> np.ndarray:
    denominator = np.maximum(
        np.abs(
            reference.astype(
                np.float64
            )
        ),
        np.finfo(
            np.float32
        ).tiny,
    )

    return (
        np.abs(
            candidate.astype(
                np.float64
            )
            - reference.astype(
                np.float64
            )
        )
        / denominator
    )


def decision_snapshot(
    logits: np.ndarray,
) -> tuple[int, str, float]:
    tensor = torch.from_numpy(
        logits.astype(
            np.float32,
            copy=False,
        )
    )

    task = decision_from_logits(
        tensor
    )

    reliability = decide_from_logits(
        tensor,
        empty_assessment(),
    )

    return (
        int(
            task[
                0
            ].item()
        ),
        reliability.trust_state.value,
        float(
            reliability.ood_margin
        ),
    )


def validate_numerical_parity(
    model,
    ort,
) -> dict:
    session = ort.InferenceSession(
        str(
            ONNX_ARTIFACT
        ),
        providers=[
            "CPUExecutionProvider",
        ],
    )

    inputs = session.get_inputs()
    outputs = session.get_outputs()

    if len(
        inputs
    ) != 1:
        raise RuntimeError(
            "ONNX Runtime input-count mismatch"
        )

    if len(
        outputs
    ) != 1:
        raise RuntimeError(
            "ONNX Runtime output-count mismatch"
        )

    if inputs[
        0
    ].name != INPUT_NAME:
        raise RuntimeError(
            "ONNX Runtime input-name mismatch"
        )

    if outputs[
        0
    ].name != OUTPUT_NAME:
        raise RuntimeError(
            "ONNX Runtime output-name mismatch"
        )

    max_abs_error = 0.0
    max_relative_error = 0.0

    worst_abs_vector_index = None
    worst_relative_vector_index = None

    historical_task_mismatches = 0
    ood_trust_mismatches = 0

    compared_logit_elements = 0

    vectors = parity_vectors()

    for index, window in enumerate(
        vectors
    ):
        with torch.inference_mode():
            reference_tensor = model(
                torch.from_numpy(
                    window
                )
            )

        reference = (
            reference_tensor
            .detach()
            .cpu()
            .numpy()
            .astype(
                np.float32,
                copy=False,
            )
        )

        candidate = session.run(
            [
                OUTPUT_NAME,
            ],
            {
                INPUT_NAME:
                    window,
            },
        )[
            0
        ]

        candidate = np.asarray(
            candidate,
            dtype=np.float32,
        )

        if tuple(
            reference.shape
        ) != OUTPUT_SHAPE:
            raise RuntimeError(
                "Reference output shape mismatch"
            )

        if tuple(
            candidate.shape
        ) != OUTPUT_SHAPE:
            raise RuntimeError(
                "Candidate output shape mismatch"
            )

        if not np.isfinite(
            reference
        ).all():
            raise RuntimeError(
                "Nonfinite PyTorch reference logits"
            )

        if not np.isfinite(
            candidate
        ).all():
            raise RuntimeError(
                "Nonfinite ONNX candidate logits"
            )

        abs_error = np.abs(
            candidate.astype(
                np.float64
            )
            - reference.astype(
                np.float64
            )
        )

        rel_error = relative_error(
            candidate,
            reference,
        )

        vector_max_abs = float(
            abs_error.max()
        )

        vector_max_rel = float(
            rel_error.max()
        )

        if (
            vector_max_abs
            > max_abs_error
        ):
            max_abs_error = (
                vector_max_abs
            )

            worst_abs_vector_index = (
                index
            )

        if (
            vector_max_rel
            > max_relative_error
        ):
            max_relative_error = (
                vector_max_rel
            )

            worst_relative_vector_index = (
                index
            )

        allowed = (
            ATOL
            + RTOL
            * np.abs(
                reference.astype(
                    np.float64
                )
            )
        )

        if not np.all(
            abs_error
            <= allowed
        ):
            raise RuntimeError(
                "Frozen ONNX numerical tolerance failed "
                f"at vector {index}"
            )

        reference_decision = (
            decision_snapshot(
                reference
            )
        )

        candidate_decision = (
            decision_snapshot(
                candidate
            )
        )

        if (
            candidate_decision[
                0
            ]
            != reference_decision[
                0
            ]
        ):
            historical_task_mismatches += 1

        if (
            candidate_decision[
                1
            ]
            != reference_decision[
                1
            ]
        ):
            ood_trust_mismatches += 1

        compared_logit_elements += (
            candidate.size
        )

    if historical_task_mismatches != 0:
        raise RuntimeError(
            "Historical task decision mismatch detected"
        )

    if ood_trust_mismatches != 0:
        raise RuntimeError(
            "OOD trust-state mismatch detected"
        )

    return {
        "parity_vector_count":
            len(
                vectors
            ),

        "compared_logit_elements":
            compared_logit_elements,

        "absolute_tolerance":
            ATOL,

        "relative_tolerance":
            RTOL,

        "max_absolute_error":
            max_abs_error,

        "max_relative_error":
            max_relative_error,

        "worst_absolute_error_vector_index":
            worst_abs_vector_index,

        "worst_relative_error_vector_index":
            worst_relative_vector_index,

        "historical_task_prediction_mismatch_count":
            historical_task_mismatches,

        "ood_trust_state_mismatch_count":
            ood_trust_mismatches,

        "all_logit_elements_within_tolerance":
            True,

        "exact_historical_task_decision_parity":
            True,

        "exact_ood_trust_state_parity":
            True,
    }


def build_result(
    protocol: dict,
    onnx,
    ort,
    graph: dict,
    parity: dict,
) -> dict:
    result = {
        "result_id":
            "PROSPECTIVE_MODEL_EXPORT_V1_CANDIDATE",

        "status":
            "prospective_fp32_onnx_export_validated_candidate_not_yet_frozen",

        "lineage":
            "prospective_protected_model_export",

        "source_anchors": {
            "export_protocol_tag":
                "prospective-protected-model-export-protocol-v1",

            "export_protocol_commit":
                EXPORT_PROTOCOL_COMMIT,

            "export_protocol_raw_sha256":
                PROTOCOL_RAW_SHA256,

            "export_protocol_content_sha256":
                PROTOCOL_CONTENT_SHA256,

            "checkpoint_path":
                str(
                    CHECKPOINT
                ),

            "checkpoint_sha256":
                CHECKPOINT_SHA256,

            "loader_raw_sha256":
                LOADER_RAW_SHA256,

            "model_source_raw_sha256":
                MODEL_SOURCE_RAW_SHA256,
        },

        "artifact": {
            "path":
                str(
                    ONNX_ARTIFACT.relative_to(
                        ROOT
                    )
                ),

            "raw_sha256":
                raw_sha256(
                    ONNX_ARTIFACT
                ),

            "bytes":
                ONNX_ARTIFACT.stat().st_size,

            "format":
                "ONNX",

            "precision":
                "float32",

            "opset_version":
                OPSET_VERSION,

            "external_data_used":
                False,
        },

        "environment": {
            "python_version":
                sys.version,

            "torch_version":
                torch.__version__,

            "numpy_version":
                np.__version__,

            "onnx_version":
                getattr(
                    onnx,
                    "__version__",
                    "UNKNOWN",
                ),

            "onnxruntime_version":
                getattr(
                    ort,
                    "__version__",
                    "UNKNOWN",
                ),
        },

        "graph_validation":
            graph,

        "numerical_and_decision_parity":
            parity,

        "scientific_boundary": {
            "protected_dataset_used":
                False,

            "calibration_dataset_used":
                False,

            "final_test_dataset_used":
                False,

            "ood_threshold_modified":
                False,

            "ood_method_modified":
                False,

            "historical_task_rule_modified":
                False,

            "integrity_operating_point_modified":
                False,

            "protected_final_test_reopened":
                False,

            "host_resource_benchmark_rerun":
                False,

            "quantization_executed":
                False,

            "result_used_for_scientific_selection":
                False,
        },

        "claim_boundary": {
            "prospective_model_export_validated":
                True,

            "exact_historical_deployed_model_claimed":
                False,

            "exact_historical_firmware_claimed":
                False,

            "stm32_importability_claimed":
                False,

            "stm32_numerical_parity_claimed":
                False,

            "stm32_latency_claimed":
                False,

            "stm32_flash_claimed":
                False,

            "stm32_ram_claimed":
                False,

            "stm32_energy_claimed":
                False,
        },
    }

    result[
        "content_sha256"
    ] = canonical_digest(
        result
    )

    return result


def main() -> None:
    if RESULT.exists():
        raise RuntimeError(
            "Refusing to overwrite prospective export result"
        )

    if ONNX_ARTIFACT.exists():
        raise RuntimeError(
            "Refusing to overwrite prospective ONNX artifact"
        )

    verify_git_anchors()

    protocol = verify_protocol()

    verify_source_anchors()

    onnx, ort = (
        load_export_dependencies()
    )

    model = load_protected_model()

    export_model(
        model
    )

    graph = validate_graph(
        onnx
    )

    parity = validate_numerical_parity(
        model,
        ort,
    )

    result = build_result(
        protocol,
        onnx,
        ort,
        graph,
        parity,
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

    print(
        "PROSPECTIVE_FP32_ONNX_EXPORT_V1_COMPLETE = True"
    )

    print(
        "ONNX_ARTIFACT_SHA256 =",
        result[
            "artifact"
        ][
            "raw_sha256"
        ],
    )

    print(
        "ONNX_ARTIFACT_BYTES =",
        result[
            "artifact"
        ][
            "bytes"
        ],
    )

    print(
        "PARITY_VECTOR_COUNT =",
        parity[
            "parity_vector_count"
        ],
    )

    print(
        "MAX_ABSOLUTE_ERROR =",
        parity[
            "max_absolute_error"
        ],
    )

    print(
        "MAX_RELATIVE_ERROR =",
        parity[
            "max_relative_error"
        ],
    )

    print(
        "HISTORICAL_TASK_MISMATCH_COUNT =",
        parity[
            "historical_task_prediction_mismatch_count"
        ],
    )

    print(
        "OOD_TRUST_MISMATCH_COUNT =",
        parity[
            "ood_trust_state_mismatch_count"
        ],
    )

    print(
        "RESULT_CONTENT_SHA256 =",
        result[
            "content_sha256"
        ],
    )

    print(
        "PROTECTED_DATASET_USED = False"
    )

    print(
        "QUANTIZATION_EXECUTED = False"
    )

    print(
        "STM32_IMPORTABILITY_CLAIMED = False"
    )

    print(
        "STM32_PERFORMANCE_CLAIMED = False"
    )


if __name__ == "__main__":
    main()
