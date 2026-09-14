from __future__ import annotations

import ast
import csv
import hashlib
import json
from pathlib import Path

import yaml


ROOT = Path(
    "/mnt/hdd16T/ToqeerHomeBackup/toqeer/IMU_Reliability"
)

SUITE = (
    ROOT
    / "experiments/16_benchmark_suite"
)

SCREEN = (
    ROOT
    / "experiments/17_v25_screening"
)

FINAL = (
    ROOT
    / "experiments/19_v25_final_confirmation"
)

R3 = (
    ROOT
    / "results/stage25_physical_fault_protocol"
    / "protocol_preregistration_r3"
)

R4B1 = (
    ROOT
    / "results/stage25_physical_fault_protocol"
    / "clean_reference_constructor_audit_r4b1"
)

OUT = (
    ROOT
    / "results/stage25_physical_fault_protocol"
    / "exact_constructor_mapping_r4b1b"
)

OUT.mkdir(
    parents=True,
    exist_ok=True,
)


BASELINES = [
    "ReliabilityCNN_v22",
    "CNN1D",
    "LSTM",
    "DeepConvLSTM",
    "Transformer",
    "ReliabilityCNN_v24",
    "DS_CNN",
    "TCN",
    "TinyTransformer",
]

V25_MODEL = (
    "ReliabilityCNN_v25"
)

ALL_MODELS = (
    BASELINES
    +
    [
        V25_MODEL
    ]
)

DATASETS = [
    "UCI_HAR",
    "PAMAP2",
    "DSADS",
    "MotionSense",
]

NUM_CLASSES = {
    "UCI_HAR": 6,
    "PAMAP2": 12,
    "DSADS": 19,
    "MotionSense": 6,
}


RUNNER = (
    SUITE
    / "run_benchmark_v3r1.py"
)

REGISTRY_CODE = (
    SUITE
    / "engine/model_registry.py"
)

REGISTRY_YAML = (
    SUITE
    / "registry/models.yaml"
)

MODEL_FORWARD = (
    SUITE
    / "engine/model_forward.py"
)

INPUT_ADAPTER = (
    SUITE
    / "engine/input_adapter.py"
)

DATASET_LOADER = (
    SUITE
    / "engine/dataset_v3r1.py"
)

V25_SOURCE = (
    SCREEN
    / "v25_candidates.py"
)

V25_RUNNER = (
    FINAL
    / "run_v25_final_r2.py"
)


def sha256_file(
    path: Path,
) -> str:

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


def ast_function_source(
    path: Path,
    function_name: str,
):

    text = path.read_text(
        encoding="utf-8",
        errors="replace",
    )

    tree = ast.parse(
        text
    )

    for node in tree.body:

        if (
            isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                ),
            )
            and
            node.name
            ==
            function_name
        ):

            source = ast.get_source_segment(
                text,
                node,
            )

            return {
                "file":
                    str(
                        path.relative_to(
                            ROOT
                        )
                    ),

                "file_sha256":
                    sha256_file(
                        path
                    ),

                "function":
                    function_name,

                "line_start":
                    node.lineno,

                "line_end":
                    node.end_lineno,

                "source":
                    source,
            }

    raise RuntimeError(
        f"Function {function_name} not found "
        f"in {path}"
    )


def ast_class_exists(
    path: Path,
    class_name: str,
):

    text = path.read_text(
        encoding="utf-8",
        errors="replace",
    )

    tree = ast.parse(
        text
    )

    for node in tree.body:

        if (
            isinstance(
                node,
                ast.ClassDef,
            )
            and
            node.name
            ==
            class_name
        ):

            return {
                "exists":
                    True,

                "line_start":
                    node.lineno,

                "line_end":
                    node.end_lineno,

                "source":
                    ast.get_source_segment(
                        text,
                        node,
                    ),
            }

    return {
        "exists":
            False,
    }


def resolve_module_source(
    module_name: str,
):

    normalized = (
        module_name.replace(
            ".",
            "/",
        )
        +
        ".py"
    )


    candidates = [
        SUITE / normalized,
        ROOT / normalized,
    ]


    if not module_name.startswith(
        "models."
    ):

        candidates.append(
            SUITE
            / "models"
            / (
                module_name.split(
                    "."
                )[-1]
                +
                ".py"
            )
        )


    existing = [
        path
        for path in candidates
        if path.exists()
    ]


    if len(existing) == 1:

        return existing[0]


    # Last-resort deterministic filename search.
    basename = (
        module_name.split(
            "."
        )[-1]
        +
        ".py"
    )


    matches = sorted(
        set(
            path
            for path in SUITE.rglob(
                basename
            )
            if "__pycache__"
            not in path.parts
        )
    )


    if len(matches) == 1:

        return matches[0]


    raise RuntimeError(
        f"Could not uniquely resolve module "
        f"{module_name!r}; "
        f"candidates={existing}, "
        f"matches={matches}"
    )


print(
    "=" * 112
)

print(
    "STAGE25 R4B1b EXACT CONSTRUCTOR MAPPING"
)

print(
    "NO TORCH IMPORT / NO TORCH.LOAD / "
    "NO MODEL CONSTRUCTION / NO FORWARD"
)

print(
    "=" * 112
)


# ============================================================
# 1. R4B1 prerequisite
# ============================================================

b1_receipt_path = (
    R4B1
    / "stage25_clean_reference_constructor_audit_receipt_r4b1.json"
)

b1_receipt = json.loads(
    b1_receipt_path.read_text()
)


if (
    b1_receipt.get(
        "status"
    )
    !=
    "PASS"
):

    raise RuntimeError(
        "R4B1 Python audit is not PASS"
    )


if (
    b1_receipt.get(
        "clean_reference_binding"
    )
    !=
    "PASS_200_OF_200"
):

    raise RuntimeError(
        "R4B1 clean references not bound"
    )


print(
    "R4B1_PREREQUISITE_PASS=True"
)


# ============================================================
# 2. Canonical source SHA manifest
# ============================================================

canonical_sources = [
    RUNNER,
    REGISTRY_CODE,
    REGISTRY_YAML,
    MODEL_FORWARD,
    INPUT_ADAPTER,
    DATASET_LOADER,
    V25_SOURCE,
    V25_RUNNER,
]


for path in canonical_sources:

    if not path.exists():

        raise FileNotFoundError(
            path
        )


source_sha = {
    str(
        path.relative_to(
            ROOT
        )
    ):
        sha256_file(
            path
        )

    for path in canonical_sources
}


write_json(
    OUT
    / "canonical_constructor_source_sha.json",
    source_sha,
)


print(
    "CANONICAL_CONSTRUCTOR_SOURCE_FILES_HASHED=",
    len(
        source_sha
    ),
)


# ============================================================
# 3. Verify canonical V3R1 runner actually uses
#    create_model + model_forward + dataset_v3r1
# ============================================================

runner_text = RUNNER.read_text(
    encoding="utf-8",
    errors="replace",
)


runner_required = [
    "from engine.dataset_v3r1 import",
    "load_dataset_v3r1",
    "from engine.model_registry import",
    "create_model",
    "from engine.model_forward import",
    "model_forward",
]


for token in runner_required:

    if token not in runner_text:

        raise RuntimeError(
            f"Canonical V3R1 runner missing "
            f"required token: {token}"
        )


print(
    "V3R1_CANONICAL_RUNNER_CONSTRUCTOR_ROUTE_PASS=True"
)


# ============================================================
# 4. Freeze exact create_model source
# ============================================================

create_model_evidence = (
    ast_function_source(
        REGISTRY_CODE,
        "create_model",
    )
)


load_registry_evidence = (
    ast_function_source(
        REGISTRY_CODE,
        "load_model_registry",
    )
)


write_json(
    OUT
    / "v3r1_model_registry_function_evidence.json",
    {
        "load_model_registry":
            load_registry_evidence,

        "create_model":
            create_model_evidence,
    },
)


print(
    "V3R1_CREATE_MODEL_FUNCTION_BOUND=True"
)


# ============================================================
# 5. Parse frozen registry YAML and resolve all 9 baselines
# ============================================================

registry = yaml.safe_load(
    REGISTRY_YAML.read_text()
)


if "models" not in registry:

    raise RuntimeError(
        "registry/models.yaml has no 'models'"
    )


registry_models = registry[
    "models"
]


constructor_rows = []


for model in BASELINES:

    if model not in registry_models:

        raise RuntimeError(
            f"Frozen model registry missing {model}"
        )


    entry = registry_models[
        model
    ]


    module_name = entry.get(
        "module"
    )

    class_name = entry.get(
        "class"
    )


    if not module_name:

        raise RuntimeError(
            f"{model}: registry module missing"
        )


    if not class_name:

        raise RuntimeError(
            f"{model}: registry class missing"
        )


    source_path = (
        resolve_module_source(
            module_name
        )
    )


    class_evidence = (
        ast_class_exists(
            source_path,
            class_name,
        )
    )


    if not class_evidence[
        "exists"
    ]:

        raise RuntimeError(
            f"{model}: class {class_name} "
            f"not found in {source_path}"
        )


    row = {
        "model":
            model,

        "constructor_family":
            "V3R1_MODEL_REGISTRY",

        "constructor_call":
            (
                "create_model("
                f"'{model}', "
                "num_classes, "
                "input_channels=6)"
            ),

        "registry_module":
            module_name,

        "registry_class":
            class_name,

        "source_file":
            str(
                source_path.relative_to(
                    ROOT
                )
            ),

        "source_sha256":
            sha256_file(
                source_path
            ),

        "class_line_start":
            class_evidence[
                "line_start"
            ],

        "class_line_end":
            class_evidence[
                "line_end"
            ],
    }


    constructor_rows.append(
        row
    )


    print()
    print(
        "MODEL=",
        model,
    )

    print(
        "CONSTRUCTOR_FAMILY=V3R1_MODEL_REGISTRY"
    )

    print(
        "REGISTRY_MODULE=",
        module_name,
    )

    print(
        "REGISTRY_CLASS=",
        class_name,
    )

    print(
        "SOURCE_FILE=",
        row[
            "source_file"
        ],
    )

    print(
        "SOURCE_SHA256=",
        row[
            "source_sha256"
        ],
    )

    print(
        "CONSTRUCTOR_CALL=",
        row[
            "constructor_call"
        ],
    )


if len(
    constructor_rows
) != 9:

    raise RuntimeError(
        "Expected 9 baseline constructor mappings"
    )


print()
print(
    "V3R1_EXACT_CONSTRUCTOR_MAPPING_PASS_9_OF_9=True"
)


# ============================================================
# 6. V25 exact constructor route
# ============================================================

v25_text = V25_SOURCE.read_text(
    encoding="utf-8",
    errors="replace",
)


v25_runner_text = V25_RUNNER.read_text(
    encoding="utf-8",
    errors="replace",
)


required_v25_source = [
    "class V25Dense64",
    '"V25Dense64"',
    "def create_candidate",
]


for token in required_v25_source:

    if token not in v25_text:

        raise RuntimeError(
            f"V25 source missing {token}"
        )


required_v25_runner = [
    '"ReliabilityCNN_v25"',
    '"V25Dense64"',
    "create_candidate",
]


for token in required_v25_runner:

    if token not in v25_runner_text:

        raise RuntimeError(
            f"V25 final R2 runner missing {token}"
        )


v25_class = (
    ast_class_exists(
        V25_SOURCE,
        "V25Dense64",
    )
)


if not v25_class[
    "exists"
]:

    raise RuntimeError(
        "V25Dense64 class definition missing"
    )


create_candidate_evidence = (
    ast_function_source(
        V25_SOURCE,
        "create_candidate",
    )
)


# Verify CANDIDATES assignment binds key V25Dense64
# to the class V25Dense64.
tree = ast.parse(
    v25_text
)

candidate_binding_pass = False
candidate_binding_source = None


for node in tree.body:

    if not isinstance(
        node,
        ast.Assign,
    ):
        continue


    names = []

    for target in node.targets:

        if isinstance(
            target,
            ast.Name,
        ):

            names.append(
                target.id
            )


    if "CANDIDATES" not in names:

        continue


    segment = ast.get_source_segment(
        v25_text,
        node,
    )


    candidate_binding_source = (
        segment
    )


    if (
        '"V25Dense64"'
        in segment
        and
        "V25Dense64"
        in segment
    ):

        candidate_binding_pass = True


if not candidate_binding_pass:

    raise RuntimeError(
        "Could not prove V25Dense64 CANDIDATES "
        "registry binding"
    )


constructor_rows.append({
    "model":
        V25_MODEL,

    "constructor_family":
        "V25_CANDIDATE_REGISTRY",

    "constructor_call":
        (
            "create_candidate("
            "'V25Dense64', "
            "num_classes, "
            "input_channels=6)"
        ),

    "registry_module":
        "v25_candidates",

    "registry_class":
        "V25Dense64",

    "source_file":
        str(
            V25_SOURCE.relative_to(
                ROOT
            )
        ),

    "source_sha256":
        sha256_file(
            V25_SOURCE
        ),

    "class_line_start":
        v25_class[
            "line_start"
        ],

    "class_line_end":
        v25_class[
            "line_end"
        ],
})


write_json(
    OUT
    / "v25_constructor_function_evidence.json",
    {
        "candidate_binding_source":
            candidate_binding_source,

        "create_candidate":
            create_candidate_evidence,

        "final_r2_runner_sha256":
            sha256_file(
                V25_RUNNER
            ),
    },
)


print()
print(
    "MODEL= ReliabilityCNN_v25"
)

print(
    "CONSTRUCTOR_FAMILY=V25_CANDIDATE_REGISTRY"
)

print(
    "REGISTRY_CLASS= V25Dense64"
)

print(
    "SOURCE_FILE=",
    str(
        V25_SOURCE.relative_to(
            ROOT
        )
    ),
)

print(
    "SOURCE_SHA256=",
    sha256_file(
        V25_SOURCE
    ),
)

print(
    "CONSTRUCTOR_CALL= "
    "create_candidate("
    "'V25Dense64', "
    "num_classes, "
    "input_channels=6)"
)

print(
    "V25_EXACT_CONSTRUCTOR_MAPPING_PASS_1_OF_1=True"
)


# ============================================================
# 7. Exact model-forward/input-adapter functions
# ============================================================

forward_evidence = (
    ast_function_source(
        MODEL_FORWARD,
        "model_forward",
    )
)


prepare_input = None


try:

    prepare_input = (
        ast_function_source(
            MODEL_FORWARD,
            "prepare_input",
        )
    )

except RuntimeError:

    pass


adapter_prepare = None


try:

    adapter_prepare = (
        ast_function_source(
            INPUT_ADAPTER,
            "prepare_model_input",
        )
    )

except RuntimeError:

    pass


write_json(
    OUT
    / "canonical_model_forward_input_evidence.json",
    {
        "model_forward":
            forward_evidence,

        "model_forward_prepare_input":
            prepare_input,

        "input_adapter_prepare_model_input":
            adapter_prepare,
    },
)


print(
    "CANONICAL_MODEL_FORWARD_FUNCTION_BOUND=True"
)


# ============================================================
# 8. Freeze exact 10-model constructor map
# ============================================================

if len(
    constructor_rows
) != 10:

    raise RuntimeError(
        f"Expected 10 constructor rows, "
        f"found {len(constructor_rows)}"
    )


if {
    row[
        "model"
    ]
    for row in constructor_rows
} != set(
    ALL_MODELS
):

    raise RuntimeError(
        "Constructor model set mismatch"
    )


with (
    OUT
    / "exact_constructor_mapping_10.csv"
).open(
    "w",
    newline="",
    encoding="utf-8",
) as f:

    fields = [
        "model",
        "constructor_family",
        "constructor_call",
        "registry_module",
        "registry_class",
        "source_file",
        "source_sha256",
        "class_line_start",
        "class_line_end",
    ]

    writer = csv.DictWriter(
        f,
        fieldnames=fields,
    )

    writer.writeheader()

    writer.writerows(
        constructor_rows
    )


print(
    "EXACT_CONSTRUCTOR_MAPPING_FINALIZED_10_OF_10=True"
)


# ============================================================
# 9. Bind 200 clean references to exact constructor rows
# ============================================================

clean_path = (
    R4B1
    / "canonical_clean_reference_200.csv"
)


with clean_path.open(
    newline="",
    encoding="utf-8",
) as f:

    clean_rows = list(
        csv.DictReader(f)
    )


if len(
    clean_rows
) != 200:

    raise RuntimeError(
        f"Expected 200 clean reference rows; "
        f"found {len(clean_rows)}"
    )


constructor_lookup = {
    row[
        "model"
    ]:
        row

    for row in constructor_rows
}


plan_rows = []


for row in clean_rows:

    model = row[
        "model"
    ]


    if model not in constructor_lookup:

        raise RuntimeError(
            f"No constructor for {model}"
        )


    constructor = (
        constructor_lookup[
            model
        ]
    )


    plan_rows.append({
        **row,

        "constructor_family":
            constructor[
                "constructor_family"
            ],

        "constructor_call":
            constructor[
                "constructor_call"
            ],

        "constructor_source_file":
            constructor[
                "source_file"
            ],

        "constructor_source_sha256":
            constructor[
                "source_sha256"
            ],

        "num_classes":
            NUM_CLASSES[
                row[
                    "dataset"
                ]
            ],

        "input_channels":
            6,
    })


if len(
    plan_rows
) != 200:

    raise RuntimeError(
        "Clean reproduction plan is not 200 rows"
    )


with (
    OUT
    / "clean_reproduction_plan_200.csv"
).open(
    "w",
    newline="",
    encoding="utf-8",
) as f:

    fields = list(
        plan_rows[0].keys()
    )

    writer = csv.DictWriter(
        f,
        fieldnames=fields,
    )

    writer.writeheader()

    writer.writerows(
        plan_rows
    )


print(
    "CLEAN_REPRODUCTION_PLAN_BOUND_200_OF_200=True"
)


# ============================================================
# 10. Final receipt
# ============================================================

receipt = {
    "audit":
        "STAGE25_EXACT_CONSTRUCTOR_MAPPING_R4B1B",

    "status":
        "PASS",

    "v3r1_exact_constructor_mapping":
        "PASS_9_OF_9",

    "v25_exact_constructor_mapping":
        "PASS_1_OF_1",

    "exact_constructor_mapping":
        "FINALIZED_10_OF_10",

    "clean_reproduction_plan":
        "BOUND_200_OF_200",

    "v3r1_constructor":
        (
            "engine.model_registry.create_model("
            "model_name, num_classes, input_channels=6)"
        ),

    "v25_constructor":
        (
            "v25_candidates.create_candidate("
            "'V25Dense64', num_classes, input_channels=6)"
        ),

    "canonical_model_forward_bound":
        True,

    "canonical_dataset_loader_bound":
        str(
            DATASET_LOADER.relative_to(
                ROOT
            )
        ),

    "torch_imported":
        False,

    "torch_load_performed":
        False,

    "model_constructed":
        False,

    "model_deserialization_performed":
        False,

    "model_forward_performed":
        False,

    "training_performed":
        False,

    "checkpoint_modified":
        False,

    "dataset_modified":
        False,

    "next_gate":
        (
            "R4B2 clean-only reproduction: construct and "
            "deserialize exactly 200 frozen checkpoints, "
            "run canonical clean test inference, and require "
            "200/200 accuracy and macro-F1 reproduction "
            "before any corrupted inference."
        ),
}


write_json(
    OUT
    / "stage25_exact_constructor_mapping_receipt_r4b1b.json",
    receipt,
)


print()
print(
    "=" * 112
)

print(
    "STAGE25 R4B1b FINAL RECEIPT"
)

print(
    "=" * 112
)

print(
    json.dumps(
        receipt,
        indent=2,
    )
)


print()
print(
    "STAGE25_EXACT_CONSTRUCTOR_MAPPING_R4B1B_PASS=True"
)

print(
    "V3R1_EXACT_CONSTRUCTOR_MAPPING_PASS_9_OF_9=True"
)

print(
    "V25_EXACT_CONSTRUCTOR_MAPPING_PASS_1_OF_1=True"
)

print(
    "EXACT_CONSTRUCTOR_MAPPING_FINALIZED_10_OF_10=True"
)

print(
    "CLEAN_REPRODUCTION_PLAN_BOUND_200_OF_200=True"
)

print(
    "TORCH_IMPORTED=False"
)

print(
    "TORCH_LOAD_PERFORMED=False"
)

print(
    "MODEL_CONSTRUCTED=False"
)

print(
    "MODEL_FORWARD_PERFORMED=False"
)

print(
    "TRAINING_PERFORMED=False"
)
