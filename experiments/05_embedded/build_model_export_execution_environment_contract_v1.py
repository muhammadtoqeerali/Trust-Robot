from __future__ import annotations

import json
import subprocess
from copy import deepcopy
from hashlib import sha256
from pathlib import Path


ROOT = Path(
    __file__
).resolve().parents[2]


PRE_ENVIRONMENT_CONTRACT_HEAD = (
    "4050f610bc037aa854a066af5ad935df8dd22b45"
)

EXPORTER_COMMIT = (
    "4050f610bc037aa854a066af5ad935df8dd22b45"
)

EXPORT_PROTOCOL_COMMIT = (
    "7229081206d0b4cfe3249792282f0aa87abb9220"
)

PORTABLE_C_COMMIT = (
    "3f0db77158cc59e4273f75b076fef53aa6b1f413"
)

EMBEDDED_PATH_COMMIT = (
    "c36a60aed60766162fb7cd3755c1f5040d9a072c"
)

REFERENCE_RUNTIME_COMMIT = (
    "4755a74fe558021576934674e338865a36df5b55"
)


EXPORTER = (
    ROOT
    / "experiments/05_embedded/"
      "export_protected_model_onnx_v1.py"
)

EXPORT_TEST = (
    ROOT
    / "tests/"
      "test_protected_model_onnx_export_v1.py"
)

EXPORT_PROTOCOL = (
    ROOT
    / "configs/embedded/"
      "prospective_protected_model_export_protocol_v1.json"
)

BLOCKER = (
    ROOT
    / "data/manifests/"
      "prospective_model_export_dependency_blocker_v1.json"
)

CONTRACT = (
    ROOT
    / "configs/embedded/"
      "prospective_model_export_execution_environment_contract_v1.json"
)


ONNX_ARTIFACT = (
    ROOT
    / "artifacts/embedded/prospective/"
      "date2025_cnn400_fp32_v1.onnx"
)

EXPORT_RESULT = (
    ROOT
    / "results/raw/"
      "prospective_model_export_v1_candidate.json"
)

EXPORT_RECEIPT = (
    ROOT
    / "data/manifests/"
      "prospective_model_export_result_receipt_v1.json"
)


EXPECTED_RAW_HASHES = {
    EXPORTER:
        "3319c9321c953c198af4f345cbb8ac55b7d1e207f8025bb74423a386b776ee55",

    EXPORT_TEST:
        "a5be24cac8f381ea6cc090730fa79ad6bebdf27589134554626ab75e4547b19d",

    EXPORT_PROTOCOL:
        "5574278d42584f03ec39274c287c48329b2dbbad49f25e77024d1b17ad94fdf3",
}


EXPORT_PROTOCOL_CONTENT_SHA256 = (
    "714eda4d82caf56de2b023cfc04bac0d"
    "e0f400323a3cefc9077db3ecfdc122ee"
)


KNOWN_INTERPRETERS = (
    Path(
        "/mnt/hdd16T/ToqeerHomeBackup/"
        "miniforge3/bin/python"
    ),

    Path(
        "/mnt/hdd16T/ToqeerHomeBackup/"
        "miniforge3/envs/opensim_scripting/bin/python"
    ),

    Path(
        "/mnt/hdd16T/ToqeerHomeBackup/"
        "miniforge3/envs/protechto311/bin/python"
    ),
)


def raw_hash(
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


def canonical_existing(
    path: Path,
) -> str:
    data = json.loads(
        path.read_text()
    )

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
            f"Canonical content mismatch: {path}"
        )

    return stored


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
    if git(
        "rev-parse",
        "HEAD",
    ) != PRE_ENVIRONMENT_CONTRACT_HEAD:
        raise RuntimeError(
            "HEAD changed before execution-environment freeze"
        )

    expected = {
        "prospective-fp32-onnx-exporter-v1^{commit}":
            EXPORTER_COMMIT,

        "prospective-protected-model-export-protocol-v1^{commit}":
            EXPORT_PROTOCOL_COMMIT,

        "portable-c-runtime-implementation-v1^{commit}":
            PORTABLE_C_COMMIT,

        "embedded-reference-path-contract-v1^{commit}":
            EMBEDDED_PATH_COMMIT,

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


def verify_frozen_inputs() -> dict:
    for path, expected in EXPECTED_RAW_HASHES.items():
        if not path.is_file():
            raise RuntimeError(
                f"Frozen artifact absent: {path}"
            )

        if raw_hash(
            path
        ) != expected:
            raise RuntimeError(
                f"Frozen artifact changed: {path}"
            )

    protocol = json.loads(
        EXPORT_PROTOCOL.read_text()
    )

    if (
        canonical_existing(
            EXPORT_PROTOCOL
        )
        != EXPORT_PROTOCOL_CONTENT_SHA256
    ):
        raise RuntimeError(
            "Frozen export protocol content changed"
        )

    return protocol


def verify_export_outputs_absent() -> None:
    for path in (
        ONNX_ARTIFACT,
        EXPORT_RESULT,
        EXPORT_RECEIPT,
    ):
        if path.exists():
            raise RuntimeError(
                f"Export output already exists: {path}"
            )


PROBE = r'''
import importlib.util
import inspect
import json
import sys

record = {
    "python_executable":
        sys.executable,

    "python_version":
        sys.version.split()[0],

    "modules": {},
}

for name in (
    "torch",
    "onnx",
    "onnxruntime",
):
    spec = importlib.util.find_spec(
        name
    )

    entry = {
        "available":
            spec is not None,

        "origin":
            None
            if spec is None
            else spec.origin,
    }

    if spec is not None:
        try:
            module = __import__(
                name
            )

            entry[
                "importable"
            ] = True

            entry[
                "version"
            ] = getattr(
                module,
                "__version__",
                "UNKNOWN",
            )

            if name == "torch":
                entry[
                    "torch_onnx_export_available"
                ] = hasattr(
                    module.onnx,
                    "export",
                )

                if hasattr(
                    module.onnx,
                    "export",
                ):
                    signature = inspect.signature(
                        module.onnx.export
                    )

                    entry[
                        "torch_onnx_export_parameters"
                    ] = sorted(
                        signature.parameters
                    )

            if name == "onnxruntime":
                entry[
                    "available_providers"
                ] = list(
                    module.get_available_providers()
                )

        except Exception as exc:
            entry[
                "importable"
            ] = False

            entry[
                "import_error"
            ] = repr(
                exc
            )

    else:
        entry[
            "importable"
        ] = False

    record[
        "modules"
    ][
        name
    ] = entry

print(
    json.dumps(
        record,
        sort_keys=True,
    )
)
'''


def probe_interpreter(
    interpreter: Path,
) -> dict:
    record = {
        "requested_interpreter":
            str(
                interpreter
            ),

        "exists":
            interpreter.is_file(),
    }

    if not interpreter.is_file():
        return record

    completed = subprocess.run(
        [
            str(
                interpreter
            ),
            "-c",
            PROBE,
        ],
        text=True,
        capture_output=True,
        timeout=60,
        check=False,
    )

    record[
        "returncode"
    ] = completed.returncode

    if completed.returncode != 0:
        record[
            "stderr"
        ] = completed.stderr[
            -2000:
        ]

        return record

    parsed = json.loads(
        completed.stdout.strip()
    )

    record.update(
        parsed
    )

    modules = record[
        "modules"
    ]

    record[
        "qualifies_for_export_execution"
    ] = all(
        modules[
            name
        ][
            "available"
        ]
        is True
        and modules[
            name
        ][
            "importable"
        ]
        is True
        for name in (
            "torch",
            "onnx",
            "onnxruntime",
        )
    )

    return record


def environment_snapshot() -> list[dict]:
    records = [
        probe_interpreter(
            interpreter
        )
        for interpreter in KNOWN_INTERPRETERS
    ]

    records.sort(
        key=lambda row: row[
            "requested_interpreter"
        ]
    )

    return records


def qualifying_environments(
    records: list[dict],
) -> list[dict]:
    return [
        row
        for row in records
        if row.get(
            "qualifies_for_export_execution"
        )
        is True
    ]


def validate_current_blocker(
    records: list[dict],
) -> None:
    if len(
        records
    ) != 3:
        raise RuntimeError(
            "Known environment inventory changed"
        )

    expected = {
        "/mnt/hdd16T/ToqeerHomeBackup/miniforge3/bin/python":
            {
                "python_version":
                    "3.13.12",

                "torch_version":
                    "2.12.0+cu130",

                "torch_available":
                    True,

                "onnx_available":
                    False,

                "onnxruntime_available":
                    False,
            },

        "/mnt/hdd16T/ToqeerHomeBackup/miniforge3/envs/"
        "opensim_scripting/bin/python":
            {
                "python_version":
                    "3.11.15",

                "torch_version":
                    None,

                "torch_available":
                    False,

                "onnx_available":
                    False,

                "onnxruntime_available":
                    False,
            },

        "/mnt/hdd16T/ToqeerHomeBackup/miniforge3/envs/"
        "protechto311/bin/python":
            {
                "python_version":
                    "3.11.15",

                "torch_version":
                    "2.5.1+cu124",

                "torch_available":
                    True,

                "onnx_available":
                    False,

                "onnxruntime_available":
                    False,
            },
    }

    observed_paths = {
        row[
            "requested_interpreter"
        ]
        for row in records
    }

    if observed_paths != set(
        expected
    ):
        raise RuntimeError(
            "Known interpreter paths changed"
        )

    for row in records:
        requested = row[
            "requested_interpreter"
        ]

        target = expected[
            requested
        ]

        if row.get(
            "returncode"
        ) != 0:
            raise RuntimeError(
                f"Interpreter probe failed: {requested}"
            )

        if (
            row[
                "python_version"
            ]
            != target[
                "python_version"
            ]
        ):
            raise RuntimeError(
                f"Python version changed: {requested}"
            )

        modules = row[
            "modules"
        ]

        if (
            modules[
                "torch"
            ][
                "available"
            ]
            is not target[
                "torch_available"
            ]
        ):
            raise RuntimeError(
                f"Torch availability changed: {requested}"
            )

        if (
            modules[
                "onnx"
            ][
                "available"
            ]
            is not target[
                "onnx_available"
            ]
        ):
            raise RuntimeError(
                f"ONNX availability changed: {requested}"
            )

        if (
            modules[
                "onnxruntime"
            ][
                "available"
            ]
            is not target[
                "onnxruntime_available"
            ]
        ):
            raise RuntimeError(
                f"ONNX Runtime availability changed: {requested}"
            )

        expected_torch_version = target[
            "torch_version"
        ]

        if expected_torch_version is not None:
            if (
                modules[
                    "torch"
                ].get(
                    "version"
                )
                != expected_torch_version
            ):
                raise RuntimeError(
                    f"Torch version changed: {requested}"
                )

    if qualifying_environments(
        records
    ):
        raise RuntimeError(
            "A qualifying export environment now exists; "
            "do not freeze obsolete blocker"
        )


def build_blocker(
    records: list[dict],
) -> dict:
    payload = {
        "blocker_id":
            "PROSPECTIVE_MODEL_EXPORT_DEPENDENCY_BLOCKER_V1",

        "status":
            "active",

        "observation_scope":
            "known_existing_python_environments_on_workstation",

        "observed_interpreter_count":
            len(
                records
            ),

        "qualifying_environment_count":
            len(
                qualifying_environments(
                    records
                )
            ),

        "required_modules": [
            "torch",
            "onnx",
            "onnxruntime",
        ],

        "environment_records":
            records,

        "blocking_condition":
            (
                "no observed existing interpreter can import "
                "torch, onnx, and onnxruntime together"
            ),

        "effect": {
            "exporter_execution_allowed":
                False,

            "checkpoint_deserialization_allowed":
                False,

            "model_forward_allowed":
                False,

            "onnx_export_allowed":
                False,
        },

        "package_policy": {
            "package_install_performed":
                False,

            "modify_existing_environment_to_remove_blocker":
                False,

            "cross_environment_site_packages_mixing_allowed":
                False,

            "manual_site_packages_copy_allowed":
                False,

            "PYTHONPATH_package_injection_allowed":
                False,
        },

        "scientific_boundary": {
            "export_protocol_modified":
                False,

            "exporter_modified":
                False,

            "parity_tolerance_modified":
                False,

            "ood_threshold_modified":
                False,

            "historical_task_rule_modified":
                False,

            "integrity_operating_point_modified":
                False,

            "protected_final_test_reopened":
                False,
        },
    }

    payload[
        "content_sha256"
    ] = canonical_digest(
        payload
    )

    return payload


def build_contract(
    blocker: dict,
    protocol: dict,
) -> dict:
    payload = {
        "contract_id":
            "PROSPECTIVE_MODEL_EXPORT_EXECUTION_ENVIRONMENT_CONTRACT_V1",

        "status":
            "frozen_while_export_execution_blocked",

        "source_blocker": {
            "path":
                "data/manifests/"
                "prospective_model_export_dependency_blocker_v1.json",

            "blocker_id":
                blocker[
                    "blocker_id"
                ],

            "content_sha256":
                blocker[
                    "content_sha256"
                ],
        },

        "frozen_lineage": {
            "exporter_tag":
                "prospective-fp32-onnx-exporter-v1",

            "exporter_commit":
                EXPORTER_COMMIT,

            "exporter_raw_sha256":
                EXPECTED_RAW_HASHES[
                    EXPORTER
                ],

            "export_protocol_tag":
                "prospective-protected-model-export-protocol-v1",

            "export_protocol_commit":
                EXPORT_PROTOCOL_COMMIT,

            "export_protocol_raw_sha256":
                EXPECTED_RAW_HASHES[
                    EXPORT_PROTOCOL
                ],

            "export_protocol_content_sha256":
                EXPORT_PROTOCOL_CONTENT_SHA256,

            "portable_c_runtime_tag":
                "portable-c-runtime-implementation-v1",

            "portable_c_runtime_commit":
                PORTABLE_C_COMMIT,
        },

        "required_execution_capabilities": {
            "single_python_interpreter":
                True,

            "torch_importable":
                True,

            "onnx_importable":
                True,

            "onnxruntime_importable":
                True,

            "torch_onnx_export_available":
                True,

            "onnx_checker_available":
                True,

            "onnxruntime_cpu_execution_provider_required":
                True,

            "all_required_modules_from_same_interpreter_environment":
                True,

            "cross_environment_package_mixing_allowed":
                False,
        },

        "torch_onnx_export_api_requirements": {
            "required_parameters": [
                "model",
                "args",
                "f",
                "export_params",
                "training",
                "input_names",
                "output_names",
                "opset_version",
                "do_constant_folding",
                "dynamic_axes",
                "keep_initializers_as_inputs",
            ],

            "exporter_specific_parameters_that_must_be_supported_or_audited":
                [
                    "dynamo",
                    "external_data",
                ],

            "required_opset_version":
                13,

            "dynamic_axes":
                None,

            "precision":
                "float32",

            "input_shape":
                [
                    1,
                    40,
                    9,
                ],

            "output_shape":
                [
                    1,
                    2,
                ],
        },

        "environment_qualification_before_first_export": {
            "required":
                True,

            "must_freeze_before_exporter_execution":
                True,

            "must_record_interpreter_realpath":
                True,

            "must_record_python_version":
                True,

            "must_record_torch_version":
                True,

            "must_record_onnx_version":
                True,

            "must_record_onnxruntime_version":
                True,

            "must_record_module_origins":
                True,

            "must_record_onnxruntime_available_providers":
                True,

            "must_confirm_cpu_execution_provider":
                True,

            "must_confirm_torch_onnx_export_signature":
                True,

            "must_confirm_frozen_exporter_imports":
                True,

            "checkpoint_deserialization_during_qualification":
                False,

            "model_forward_during_qualification":
                False,

            "onnx_export_during_qualification":
                False,
        },

        "current_environment_selection": {
            "selected_interpreter":
                None,

            "selected_environment_qualified":
                False,

            "reason":
                (
                    "no observed existing interpreter currently provides "
                    "torch + onnx + onnxruntime together"
                ),
        },

        "package_and_environment_policy": {
            "install_packages_as_part_of_this_contract":
                False,

            "modify_protechto311":
                False,

            "modify_miniforge_base":
                False,

            "modify_opensim_scripting":
                False,

            "copy_packages_between_environments":
                False,

            "inject_foreign_site_packages":
                False,

            "silently_change_python_interpreter":
                False,

            "future_preexisting_environment_must_be_qualified_first":
                True,
        },

        "blocker_release_rule": {
            "blocker_can_be_released_when":
                (
                    "a pre-existing single interpreter environment satisfying "
                    "all execution capabilities is discovered and separately "
                    "qualified/frozen before exporter execution"
                ),

            "discovery_alone_allows_export":
                False,

            "qualification_receipt_required":
                True,

            "exporter_may_run_before_qualification_receipt":
                False,
        },

        "frozen_export_semantics": {
            "format":
                protocol[
                    "export_scope"
                ][
                    "format"
                ],

            "precision":
                protocol[
                    "export_scope"
                ][
                    "precision"
                ],

            "opset_version":
                protocol[
                    "export_scope"
                ][
                    "opset_version"
                ],

            "input_shape":
                protocol[
                    "tensor_contract"
                ][
                    "input_shape"
                ],

            "output_shape":
                protocol[
                    "tensor_contract"
                ][
                    "output_shape"
                ],

            "parity_vector_count":
                protocol[
                    "deterministic_parity_input_contract"
                ][
                    "total_vector_count"
                ],

            "absolute_tolerance":
                protocol[
                    "numerical_parity_contract"
                ][
                    "absolute_tolerance"
                ],

            "relative_tolerance":
                protocol[
                    "numerical_parity_contract"
                ][
                    "relative_tolerance"
                ],

            "decision_mismatch_tolerance":
                protocol[
                    "decision_parity_contract"
                ][
                    "decision_mismatch_tolerance"
                ],

            "ood_threshold":
                protocol[
                    "decision_parity_contract"
                ][
                    "ood_threshold"
                ],
        },

        "claim_boundary": {
            "export_executed":
                False,

            "prospective_onnx_validated":
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
        },

        "freeze_boundary": {
            "package_install_performed":
                False,

            "checkpoint_deserialized":
                False,

            "model_forward_executed":
                False,

            "onnx_export_executed":
                False,

            "onnx_artifact_created":
                False,

            "protected_dataset_opened":
                False,

            "quantization_executed":
                False,

            "arm_toolchain_used":
                False,

            "stm32_hardware_measured":
                False,
        },
    }

    payload[
        "content_sha256"
    ] = canonical_digest(
        payload
    )

    return payload


def main() -> None:
    if BLOCKER.exists():
        raise RuntimeError(
            "Refusing to overwrite dependency blocker"
        )

    if CONTRACT.exists():
        raise RuntimeError(
            "Refusing to overwrite execution-environment contract"
        )

    verify_git_anchors()

    protocol = verify_frozen_inputs()

    verify_export_outputs_absent()

    records = environment_snapshot()

    validate_current_blocker(
        records
    )

    blocker = build_blocker(
        records
    )

    contract = build_contract(
        blocker,
        protocol,
    )

    BLOCKER.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    CONTRACT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    BLOCKER.write_text(
        json.dumps(
            blocker,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )

    CONTRACT.write_text(
        json.dumps(
            contract,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        "MODEL_EXPORT_DEPENDENCY_BLOCKER_V1_WRITTEN = True"
    )

    print(
        "MODEL_EXPORT_EXECUTION_ENVIRONMENT_CONTRACT_V1_WRITTEN = True"
    )

    print(
        "OBSERVED_INTERPRETER_COUNT =",
        blocker[
            "observed_interpreter_count"
        ],
    )

    print(
        "QUALIFYING_ENVIRONMENT_COUNT =",
        blocker[
            "qualifying_environment_count"
        ],
    )

    print(
        "BLOCKER_ACTIVE =",
        blocker[
            "status"
        ]
        == "active",
    )

    print(
        "BLOCKER_CONTENT_SHA256 =",
        blocker[
            "content_sha256"
        ],
    )

    print(
        "CONTRACT_CONTENT_SHA256 =",
        contract[
            "content_sha256"
        ],
    )

    print(
        "SELECTED_INTERPRETER =",
        contract[
            "current_environment_selection"
        ][
            "selected_interpreter"
        ],
    )

    print(
        "PACKAGE_INSTALL_PERFORMED = False"
    )

    print(
        "CHECKPOINT_DESERIALIZED = False"
    )

    print(
        "MODEL_FORWARD_EXECUTED = False"
    )

    print(
        "ONNX_EXPORT_EXECUTED = False"
    )


if __name__ == "__main__":
    main()
