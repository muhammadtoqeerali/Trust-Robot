from __future__ import annotations

import ast
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(
    "/mnt/hdd16T/ToqeerHomeBackup/toqeer/IMU_Reliability"
)

R3 = (
    ROOT
    / "results/stage25_physical_fault_protocol"
    / "protocol_preregistration_r3"
)

R4A = (
    ROOT
    / "results/stage25_physical_fault_protocol"
    / "transform_provenance_preflight_r4a"
)

OUT = (
    ROOT
    / "results/stage25_physical_fault_protocol"
    / "clean_reference_constructor_audit_r4b1"
)

OUT.mkdir(
    parents=True,
    exist_ok=True,
)


MODELS = [
    "ReliabilityCNN_v22",
    "CNN1D",
    "LSTM",
    "DeepConvLSTM",
    "Transformer",
    "ReliabilityCNN_v24",
    "DS_CNN",
    "TCN",
    "TinyTransformer",
    "ReliabilityCNN_v25",
]


DATASETS = [
    "UCI_HAR",
    "PAMAP2",
    "DSADS",
    "MotionSense",
]


SEEDS = [
    42,
    123,
    456,
    789,
    2026,
]


SOURCE_ROOTS = [
    ROOT / "experiments/16_benchmark_suite",
    ROOT / "experiments/17_v25_screening",
    ROOT / "experiments/18_v25_training_ablation",
    ROOT / "experiments/19_v25_final_confirmation",
    ROOT / "experiments/20_v25_final_efficiency",
]


def sha256_file(path: Path) -> str:

    h = hashlib.sha256()

    with path.open("rb") as f:

        for block in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(block)

    return h.hexdigest()


def write_json(path, obj):

    path.write_text(
        json.dumps(
            obj,
            indent=2,
            sort_keys=True,
            default=str,
        )
        + "\n"
    )


print("=" * 112)

print(
    "STAGE25 R4B1 CLEAN REFERENCE + "
    "EXACT CONSTRUCTOR PROVENANCE AUDIT"
)

print(
    "NO TORCH.LOAD / NO MODEL CONSTRUCTION / "
    "NO FORWARD / NO TRAINING"
)

print("=" * 112)


# ============================================================
# 1. Verify R4A receipt
# ============================================================

r4a_receipt_path = (
    R4A
    / "stage25_transform_provenance_preflight_receipt_r4a.json"
)


if not r4a_receipt_path.exists():

    raise FileNotFoundError(
        r4a_receipt_path
    )


r4a = json.loads(
    r4a_receipt_path.read_text()
)


required = {
    "status":
        "PASS",

    "model_bank_sha_verified":
        "PASS_200_OF_200",

    "dataset_condition_tensor_manifest":
        "PASS_140",

    "paired_fault_transform_comparisons":
        "PASS_68",

    "commutation_controls":
        "PASS_16_OF_16",

    "model_deserialization_performed":
        False,

    "clean_model_inference_performed":
        False,

    "corrupted_model_inference_performed":
        False,
}


for key, expected in required.items():

    actual = r4a.get(key)

    if actual != expected:

        raise RuntimeError(
            f"R4A prerequisite mismatch: "
            f"{key}={actual!r}, "
            f"expected={expected!r}"
        )


print(
    "R4A_CANONICAL_PREREQUISITES_PASS=True"
)


# ============================================================
# 2. Load frozen 200-checkpoint bank
# ============================================================

bank_path = (
    R3
    / "frozen_model_bank_200.csv"
)


if not bank_path.exists():

    raise FileNotFoundError(
        bank_path
    )


with bank_path.open(
    newline="",
    encoding="utf-8",
) as f:

    bank = list(
        csv.DictReader(f)
    )


if len(bank) != 200:

    raise RuntimeError(
        f"Expected 200 frozen bank rows; "
        f"found {len(bank)}"
    )


# Re-hash again.
for row in bank:

    checkpoint = (
        ROOT
        / row["checkpoint"]
    )

    if not checkpoint.exists():

        raise FileNotFoundError(
            checkpoint
        )


    digest = sha256_file(
        checkpoint
    )


    if digest != row[
        "checkpoint_sha256"
    ]:

        raise RuntimeError(
            "Checkpoint changed after R3/R4A: "
            f"{checkpoint}"
        )


print(
    "R4B1_CHECKPOINT_SHA_PASS_200_OF_200=True"
)


# ============================================================
# 3. Exact clean-reference binding
# ============================================================

print()
print("=" * 112)
print("CLEAN REFERENCE BINDING")
print("=" * 112)


clean_rows = []


for row in bank:

    checkpoint = (
        ROOT
        / row["checkpoint"]
    )

    run_dir = (
        checkpoint.parent
    )

    metrics_path = (
        run_dir
        / "metrics.json"
    )


    if not metrics_path.exists():

        raise FileNotFoundError(
            metrics_path
        )


    metrics = json.loads(
        metrics_path.read_text()
    )


    if "test" not in metrics:

        raise RuntimeError(
            f"{metrics_path}: missing test object"
        )


    test = metrics[
        "test"
    ]


    if "accuracy" not in test:

        raise RuntimeError(
            f"{metrics_path}: missing test.accuracy"
        )


    if "macro_f1" not in test:

        raise RuntimeError(
            f"{metrics_path}: missing test.macro_f1"
        )


    accuracy = float(
        test["accuracy"]
    )

    macro_f1 = float(
        test["macro_f1"]
    )


    if not (
        0.0
        <= accuracy
        <= 1.0
    ):

        raise RuntimeError(
            f"{metrics_path}: invalid accuracy {accuracy}"
        )


    if not (
        0.0
        <= macro_f1
        <= 1.0
    ):

        raise RuntimeError(
            f"{metrics_path}: invalid macro_f1 {macro_f1}"
        )


    clean_rows.append({
        "bank_source":
            row["bank_source"],

        "dataset":
            row["dataset"],

        "model":
            row["model"],

        "seed":
            int(row["seed"]),

        "v25_analysis_stratum":
            row["v25_analysis_stratum"],

        "checkpoint":
            row["checkpoint"],

        "checkpoint_sha256":
            row["checkpoint_sha256"],

        "metrics_file":
            str(
                metrics_path.relative_to(
                    ROOT
                )
            ),

        "metrics_sha256":
            sha256_file(
                metrics_path
            ),

        "reference_accuracy":
            accuracy,

        "reference_macro_f1":
            macro_f1,
    })


if len(clean_rows) != 200:

    raise RuntimeError(
        "Clean-reference row count not 200"
    )


keys = {
    (
        x["dataset"],
        x["model"],
        x["seed"],
    )
    for x in clean_rows
}


if len(keys) != 200:

    raise RuntimeError(
        "Duplicate clean-reference identity"
    )


with (
    OUT
    / "canonical_clean_reference_200.csv"
).open(
    "w",
    newline="",
    encoding="utf-8",
) as f:

    fields = [
        "bank_source",
        "dataset",
        "model",
        "seed",
        "v25_analysis_stratum",
        "checkpoint",
        "checkpoint_sha256",
        "metrics_file",
        "metrics_sha256",
        "reference_accuracy",
        "reference_macro_f1",
    ]

    writer = csv.DictWriter(
        f,
        fieldnames=fields,
    )

    writer.writeheader()

    writer.writerows(
        clean_rows
    )


print(
    "CANONICAL_CLEAN_REFERENCE_BOUND_200_OF_200=True"
)

print(
    "REFERENCE_ACCURACY_FIELD=metrics.json::test.accuracy"
)

print(
    "REFERENCE_MACRO_F1_FIELD=metrics.json::test.macro_f1"
)


# ============================================================
# 4. Clean-reference descriptive integrity
#
# This is not new inference. It only summarizes frozen values.
# ============================================================

summary = defaultdict(
    lambda: {
        "accuracy": [],
        "macro_f1": [],
    }
)


for row in clean_rows:

    key = (
        row["dataset"],
        row["model"],
    )

    summary[key][
        "accuracy"
    ].append(
        row[
            "reference_accuracy"
        ]
    )

    summary[key][
        "macro_f1"
    ].append(
        row[
            "reference_macro_f1"
        ]
    )


print()
print(
    "CLEAN_REFERENCE_GROUPS=",
    len(summary),
)


if len(summary) != 40:

    raise RuntimeError(
        f"Expected 40 dataset/model groups; "
        f"found {len(summary)}"
    )


for (
    dataset,
    model,
), values in sorted(
    summary.items()
):

    if len(
        values["accuracy"]
    ) != 5:

        raise RuntimeError(
            f"{dataset}/{model}: "
            "expected five clean reference seeds"
        )


print(
    "CLEAN_REFERENCE_GROUP_CARDINALITY_PASS_40_OF_40=True"
)


# ============================================================
# 5. Source inventory and SHA
# ============================================================

python_files = []


for base in SOURCE_ROOTS:

    if not base.exists():
        continue

    for path in sorted(
        base.rglob("*.py")
    ):

        if "__pycache__" in path.parts:
            continue

        if path.stat().st_size > 5_000_000:
            continue

        python_files.append(
            path
        )


source_manifest = []


for path in python_files:

    source_manifest.append({
        "path":
            str(
                path.relative_to(
                    ROOT
                )
            ),

        "sha256":
            sha256_file(
                path
            ),

        "size_bytes":
            path.stat().st_size,
    })


write_json(
    OUT
    / "model_source_sha_manifest.json",
    source_manifest,
)


print(
    "PYTHON_SOURCE_FILES_HASHED=",
    len(source_manifest),
)


# ============================================================
# 6. AST constructor / factory / registry discovery
# ============================================================

print()
print("=" * 112)
print("MODEL CONSTRUCTOR / FACTORY DISCOVERY")
print("=" * 112)


interesting_name_rx = re.compile(
    r"model|build|create|factory|registry|"
    r"architecture|network|constructor|classifier",
    re.I,
)


all_model_token_rx = re.compile(
    "|".join(
        re.escape(x)
        for x in sorted(
            MODELS,
            key=len,
            reverse=True,
        )
    )
)


blocks = []


for path in python_files:

    try:

        text = path.read_text(
            encoding="utf-8",
            errors="replace",
        )

        tree = ast.parse(
            text
        )

    except Exception:
        continue


    lines = text.splitlines(
        keepends=True
    )


    # --------------------------------------------------------
    # Top-level imports
    # --------------------------------------------------------

    imports = []

    for node in tree.body:

        if isinstance(
            node,
            (
                ast.Import,
                ast.ImportFrom,
            ),
        ):

            segment = ast.get_source_segment(
                text,
                node,
            )

            if (
                segment
                and
                (
                    all_model_token_rx.search(
                        segment
                    )
                    or
                    re.search(
                        r"model|network|architecture",
                        segment,
                        re.I,
                    )
                )
            ):

                imports.append({
                    "line":
                        node.lineno,

                    "source":
                        segment,
                })


    # --------------------------------------------------------
    # Functions / classes
    # --------------------------------------------------------

    for node in tree.body:

        if not isinstance(
            node,
            (
                ast.FunctionDef,
                ast.ClassDef,
            ),
        ):
            continue


        segment = ast.get_source_segment(
            text,
            node,
        )


        if not segment:
            continue


        models_mentioned = [
            model
            for model in MODELS
            if model in segment
        ]


        relevant = (
            bool(
                models_mentioned
            )
            or
            bool(
                interesting_name_rx.search(
                    node.name
                )
            )
            or
            (
                isinstance(
                    node,
                    ast.ClassDef,
                )
                and
                node.name in MODELS
            )
        )


        if not relevant:
            continue


        blocks.append({
            "file":
                str(
                    path.relative_to(
                        ROOT
                    )
                ),

            "kind":
                type(node).__name__,

            "name":
                node.name,

            "line_start":
                node.lineno,

            "line_end":
                getattr(
                    node,
                    "end_lineno",
                    None,
                ),

            "models_mentioned":
                models_mentioned,

            "source":
                segment,

            "relevant_imports":
                imports,
        })


# ------------------------------------------------------------
# Top-level assignments/dicts containing model names
# ------------------------------------------------------------

assignments = []


for path in python_files:

    try:

        text = path.read_text(
            encoding="utf-8",
            errors="replace",
        )

        tree = ast.parse(
            text
        )

    except Exception:
        continue


    for node in tree.body:

        if not isinstance(
            node,
            (
                ast.Assign,
                ast.AnnAssign,
            ),
        ):
            continue


        segment = ast.get_source_segment(
            text,
            node,
        )


        if not segment:
            continue


        models_mentioned = [
            model
            for model in MODELS
            if model in segment
        ]


        if not models_mentioned:
            continue


        assignments.append({
            "file":
                str(
                    path.relative_to(
                        ROOT
                    )
                ),

            "line_start":
                node.lineno,

            "line_end":
                getattr(
                    node,
                    "end_lineno",
                    None,
                ),

            "models_mentioned":
                models_mentioned,

            "source":
                segment,
        })


write_json(
    OUT
    / "constructor_factory_ast_blocks.json",
    blocks,
)

write_json(
    OUT
    / "model_registry_assignment_blocks.json",
    assignments,
)


print(
    "CONSTRUCTOR_FACTORY_AST_BLOCKS=",
    len(blocks),
)

print(
    "MODEL_REGISTRY_ASSIGNMENT_BLOCKS=",
    len(assignments),
)


# ============================================================
# 7. Per-model provenance resolution evidence
# ============================================================

per_model = {}


for model in MODELS:

    block_hits = [
        x
        for x in blocks
        if (
            model
            in x[
                "models_mentioned"
            ]
            or
            (
                x[
                    "kind"
                ]
                ==
                "ClassDef"
                and
                x[
                    "name"
                ]
                ==
                model
            )
        )
    ]


    assignment_hits = [
        x
        for x in assignments
        if model
        in x[
            "models_mentioned"
        ]
    ]


    raw_file_hits = []


    for path in python_files:

        try:

            text = path.read_text(
                encoding="utf-8",
                errors="replace",
            )

        except Exception:
            continue


        if model in text:

            raw_file_hits.append(
                str(
                    path.relative_to(
                        ROOT
                    )
                )
            )


    per_model[
        model
    ] = {
        "ast_blocks":
            block_hits,

        "registry_assignments":
            assignment_hits,

        "raw_file_hits":
            sorted(
                set(
                    raw_file_hits
                )
            ),
    }


    if not raw_file_hits:

        raise RuntimeError(
            f"No source provenance for {model}"
        )


    print()
    print(
        "MODEL=",
        model,
    )

    print(
        "RAW_SOURCE_FILES=",
        len(
            raw_file_hits
        ),
    )

    print(
        "AST_BLOCKS=",
        len(
            block_hits
        ),
    )

    print(
        "REGISTRY_BLOCKS=",
        len(
            assignment_hits
        ),
    )


    for hit in (
        block_hits[:8]
    ):

        print(
            "  BLOCK:",
            hit["file"],
            hit["kind"],
            hit["name"],
            f"lines={hit['line_start']}-{hit['line_end']}",
        )


    for hit in (
        assignment_hits[:8]
    ):

        print(
            "  REGISTRY:",
            hit["file"],
            f"lines={hit['line_start']}-{hit['line_end']}",
        )


write_json(
    OUT
    / "per_model_constructor_provenance.json",
    per_model,
)


print()
print(
    "MODEL_CONSTRUCTOR_PROVENANCE_EVIDENCE_PASS_10_OF_10=True"
)


# ============================================================
# 8. Strong direct search for canonical runner/factory files
# ============================================================

canonical_search_terms = [
    "def build_model",
    "def create_model",
    "def get_model",
    "MODEL_REGISTRY",
    "MODEL_FACTORY",
    "model_registry",
    "model_factory",
    "ReliabilityCNN_v25",
    "V25Dense64",
]


direct_hits = []


for path in python_files:

    try:

        text = path.read_text(
            encoding="utf-8",
            errors="replace",
        )

    except Exception:
        continue


    matched = [
        term
        for term in canonical_search_terms
        if term in text
    ]


    if not matched:
        continue


    lines = text.splitlines()


    line_hits = []


    for i, line in enumerate(
        lines,
        1,
    ):

        terms_here = [
            term
            for term in matched
            if term in line
        ]


        if not terms_here:
            continue


        lo = max(
            1,
            i - 8,
        )

        hi = min(
            len(lines),
            i + 25,
        )


        context = "\n".join(
            f"{j:04d}: {lines[j-1]}"
            for j in range(
                lo,
                hi + 1,
            )
        )


        line_hits.append({
            "line":
                i,

            "terms":
                terms_here,

            "context":
                context,
        })


    direct_hits.append({
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

        "matched_terms":
            matched,

        "line_hits":
            line_hits,
    })


write_json(
    OUT
    / "canonical_factory_direct_search.json",
    direct_hits,
)


print()
print(
    "CANONICAL_FACTORY_DIRECT_SEARCH_FILES=",
    len(
        direct_hits
    ),
)


for item in direct_hits:

    print()
    print(
        "FACTORY_FILE=",
        item[
            "file"
        ],
    )

    print(
        "FACTORY_FILE_SHA256=",
        item[
            "file_sha256"
        ],
    )

    print(
        "MATCHED_TERMS=",
        item[
            "matched_terms"
        ],
    )


    for hit in item[
        "line_hits"
    ][:12]:

        print(
            hit[
                "context"
            ]
        )

        print(
            "-" * 80
        )


# ============================================================
# 9. Final receipt
# ============================================================

receipt = {
    "audit":
        "STAGE25_CLEAN_REFERENCE_CONSTRUCTOR_AUDIT_R4B1",

    "status":
        "PASS",

    "checkpoint_sha":
        "PASS_200_OF_200",

    "clean_reference_binding":
        "PASS_200_OF_200",

    "clean_accuracy_reference":
        "metrics.json::test.accuracy",

    "clean_macro_f1_reference":
        "metrics.json::test.macro_f1",

    "clean_reference_groups":
        "PASS_40_OF_40",

    "model_constructor_provenance_evidence":
        "PASS_10_OF_10",

    "constructor_factory_ast_blocks":
        len(blocks),

    "registry_assignment_blocks":
        len(assignments),

    "canonical_factory_search_files":
        len(direct_hits),

    "exact_constructor_mapping_finalized":
        False,

    "reason_not_finalized":
        (
            "This stage inventories exact source/factory evidence. "
            "The next interpretation step must select the canonical "
            "constructor path from frozen runner provenance before "
            "model loading."
        ),

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

    "r3_modified":
        False,

    "r4a_modified":
        False,

    "next_gate":
        (
            "Select and freeze exact canonical model constructor "
            "mapping for all 10 architectures, then execute "
            "clean-only reproduction against the 200 bound "
            "accuracy/macro-F1 references."
        ),
}


write_json(
    OUT
    / "stage25_clean_reference_constructor_audit_receipt_r4b1.json",
    receipt,
)


print()
print("=" * 112)
print("STAGE25 R4B1 FINAL RECEIPT")
print("=" * 112)

print(
    json.dumps(
        receipt,
        indent=2,
    )
)


print()
print(
    "STAGE25_CLEAN_REFERENCE_CONSTRUCTOR_AUDIT_R4B1_PASS=True"
)

print(
    "CANONICAL_CLEAN_REFERENCE_BOUND_200_OF_200=True"
)

print(
    "MODEL_CONSTRUCTOR_PROVENANCE_EVIDENCE_PASS_10_OF_10=True"
)

print(
    "EXACT_CONSTRUCTOR_MAPPING_FINALIZED=False"
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

print(
    "CHECKPOINTS_MODIFIED=False"
)

print(
    "DATASET_ARRAYS_MODIFIED=False"
)
