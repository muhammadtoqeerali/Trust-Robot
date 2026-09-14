from __future__ import annotations

import ast
import csv
import hashlib
import json
import os
import re
import sys
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(
    "/mnt/hdd16T/ToqeerHomeBackup/toqeer/IMU_Reliability"
)

OUT = (
    ROOT
    / "results/stage25_physical_fault_protocol"
    / "feasibility_audit_r1"
)

OUT.mkdir(
    parents=True,
    exist_ok=True,
)

DATASETS = [
    "UCI_HAR",
    "PAMAP2",
    "DSADS",
    "MotionSense",
]

DATASET_ALIASES = {
    "UCI_HAR": [
        "uci_har",
        "uci-har",
        "ucihar",
        "uci har",
    ],
    "PAMAP2": [
        "pamap2",
        "pamap",
    ],
    "DSADS": [
        "dsads",
        "dsad",
    ],
    "MotionSense": [
        "motionsense",
        "motion_sense",
        "motion-sense",
        "motion sense",
    ],
}

RELEVANT_STAGE_NAMES = [
    "16_benchmark_suite",
    "17_v25_screening",
    "18_v25_training_ablation",
    "19_v25_final_confirmation",
    "20_v25_final_efficiency",
    "22_storm_external_benchmark",
    "23_storm_v25_direct_comparison",
    "24_storm_paper_domain_faults",
]

CHECKPOINT_SUFFIXES = {
    ".pt",
    ".pth",
    ".ckpt",
}

CODE_SUFFIXES = {
    ".py",
    ".sh",
}

TEXT_SUFFIXES = {
    ".json",
    ".txt",
    ".csv",
    ".yaml",
    ".yml",
}


# ============================================================
# Utility
# ============================================================

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        for block in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(block)

    return h.hexdigest()


def write_json(
    path: Path,
    obj: Any,
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


def dataset_matches(
    text: str,
):
    low = text.lower()

    hits = []

    for canonical, aliases in DATASET_ALIASES.items():

        if any(
            alias in low
            for alias in aliases
        ):
            hits.append(canonical)

    return hits


def safe_read_text(
    path: Path,
    max_bytes: int = 5_000_000,
):
    try:
        if path.stat().st_size > max_bytes:
            return None

        return path.read_text(
            encoding="utf-8",
            errors="replace",
        )

    except Exception:
        return None


# ============================================================
# 1. Top-level project inventory
# ============================================================

print("=" * 100)
print("STAGE25 PHYSICAL-FAULT PROTOCOL FEASIBILITY AUDIT R1")
print("READ ONLY — NO MODEL LOAD / NO FORWARD / NO TRAINING")
print("=" * 100)

project_inventory = {}

for top in [
    ROOT / "experiments",
    ROOT / "results",
]:

    entries = []

    if top.exists():
        entries = sorted(
            p.name
            for p in top.iterdir()
        )

    project_inventory[
        str(top.relative_to(ROOT))
    ] = entries


write_json(
    OUT / "project_top_level_inventory.json",
    project_inventory,
)


print()
print("RELEVANT EXPERIMENT DIRECTORIES")

for name in RELEVANT_STAGE_NAMES:

    p = ROOT / "experiments" / name

    print(
        name,
        "EXISTS=",
        p.exists(),
    )


# ============================================================
# 2. Discover Stage16/17/18/19 code files
# ============================================================

code_roots = []

for name in RELEVANT_STAGE_NAMES:

    p = ROOT / "experiments" / name

    if p.exists():
        code_roots.append(p)


code_files = []

for base in code_roots:

    for p in sorted(
        base.rglob("*")
    ):

        if (
            p.is_file()
            and p.suffix.lower()
            in CODE_SUFFIXES
        ):
            code_files.append(p)


print()
print("RELEVANT_CODE_FILES=", len(code_files))

with (
    OUT
    / "relevant_code_files.txt"
).open(
    "w",
    encoding="utf-8",
) as f:

    for p in code_files:
        f.write(
            str(
                p.relative_to(ROOT)
            )
            + "\n"
        )


# ============================================================
# 3. Extract high-value dataset/normalization/checkpoint lines
# ============================================================

rx = re.compile(
    r"dataset|uci|pamap|dsads|motion"
    r"|normaliz|standardiz|mean|std"
    r"|train.*split|subject"
    r"|checkpoint|ckpt|best_model|best\.pt"
    r"|input_channels|channels"
    r"|acc|gyro"
    r"|reliability|corrupt",
    re.I,
)

code_evidence = []

for path in code_files:

    text = safe_read_text(path)

    if text is None:
        continue

    for lineno, line in enumerate(
        text.splitlines(),
        1,
    ):

        if rx.search(line):

            code_evidence.append({
                "file":
                    str(
                        path.relative_to(ROOT)
                    ),

                "line":
                    lineno,

                "text":
                    line.rstrip(),
            })


with (
    OUT
    / "code_dataset_normalization_checkpoint_evidence.tsv"
).open(
    "w",
    newline="",
    encoding="utf-8",
) as f:

    w = csv.DictWriter(
        f,
        fieldnames=[
            "file",
            "line",
            "text",
        ],
        delimiter="\t",
    )

    w.writeheader()
    w.writerows(
        code_evidence
    )


print(
    "CODE_EVIDENCE_LINES=",
    len(code_evidence),
)


# ============================================================
# 4. AST function inventory for dataset/model infrastructure
# ============================================================

function_rows = []

function_name_rx = re.compile(
    r"load|dataset|data|split|normal|standard"
    r"|checkpoint|model|candidate|reliab"
    r"|corrupt|fault|evaluate|train",
    re.I,
)

for path in code_files:

    if path.suffix.lower() != ".py":
        continue

    text = safe_read_text(path)

    if text is None:
        continue

    try:
        tree = ast.parse(text)
    except Exception:
        continue

    for node in ast.walk(tree):

        if not isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
                ast.ClassDef,
            ),
        ):
            continue

        if not function_name_rx.search(
            node.name
        ):
            continue

        function_rows.append({
            "file":
                str(
                    path.relative_to(ROOT)
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
        })


with (
    OUT
    / "relevant_function_class_inventory.csv"
).open(
    "w",
    newline="",
    encoding="utf-8",
) as f:

    fields = [
        "file",
        "kind",
        "name",
        "line_start",
        "line_end",
    ]

    w = csv.DictWriter(
        f,
        fieldnames=fields,
    )

    w.writeheader()
    w.writerows(
        function_rows
    )


# ============================================================
# 5. Filesystem artifact discovery
#
# Exclude:
#   external_references/
#   .git/
#
# No file content is loaded except small metadata/text.
# ============================================================

artifact_roots = [
    ROOT / "results",
    ROOT / "experiments",
]

# Include conventional data/cache roots if present.
for candidate in [
    ROOT / "data",
    ROOT / "datasets",
    ROOT / "cache",
    ROOT / "processed_data",
]:

    if candidate.exists():
        artifact_roots.append(
            candidate
        )


artifact_rows = []

seen = set()

for base in artifact_roots:

    if not base.exists():
        continue

    for dirpath, dirnames, filenames in os.walk(base):

        dp = Path(dirpath)

        # Avoid Python caches.
        dirnames[:] = [
            d
            for d in dirnames
            if d not in {
                "__pycache__",
                ".git",
            }
        ]

        for filename in filenames:

            p = dp / filename

            try:
                rel = p.relative_to(ROOT)
            except Exception:
                continue

            key = str(rel)

            if key in seen:
                continue

            seen.add(key)

            datasets = dataset_matches(
                key
            )

            suffix = p.suffix.lower()

            interesting = (
                bool(datasets)
                or suffix
                in (
                    CHECKPOINT_SUFFIXES
                    | TEXT_SUFFIXES
                    | {".npz", ".npy"}
                )
            )

            if not interesting:
                continue

            try:
                size = p.stat().st_size
            except Exception:
                size = None

            artifact_rows.append({
                "path":
                    key,

                "datasets":
                    "|".join(datasets),

                "suffix":
                    suffix,

                "size_bytes":
                    size,
            })


with (
    OUT
    / "artifact_inventory.csv"
).open(
    "w",
    newline="",
    encoding="utf-8",
) as f:

    fields = [
        "path",
        "datasets",
        "suffix",
        "size_bytes",
    ]

    w = csv.DictWriter(
        f,
        fieldnames=fields,
    )

    w.writeheader()
    w.writerows(
        artifact_rows
    )


print(
    "DISCOVERED_INTERESTING_ARTIFACTS=",
    len(artifact_rows),
)


# ============================================================
# 6. Checkpoint inventory
#
# Read only.
# Hash only reasonably sized checkpoint files.
# ============================================================

checkpoint_rows = []

for row in artifact_rows:

    if row["suffix"] not in CHECKPOINT_SUFFIXES:
        continue

    p = ROOT / row["path"]

    if not p.exists():
        continue

    size = p.stat().st_size

    digest = None

    # Protect against accidentally hashing huge unrelated blobs.
    if size <= 100 * 1024 * 1024:
        try:
            digest = sha256_file(p)
        except Exception:
            digest = None

    checkpoint_rows.append({
        "path":
            row["path"],

        "datasets":
            row["datasets"],

        "size_bytes":
            size,

        "sha256":
            digest,

        "likely_stage16":
            "16_" in row["path"]
            or "benchmark" in row["path"].lower(),

        "likely_stage19":
            "19_" in row["path"]
            or "v25_final" in row["path"].lower(),
    })


with (
    OUT
    / "checkpoint_inventory.csv"
).open(
    "w",
    newline="",
    encoding="utf-8",
) as f:

    fields = [
        "path",
        "datasets",
        "size_bytes",
        "sha256",
        "likely_stage16",
        "likely_stage19",
    ]

    w = csv.DictWriter(
        f,
        fieldnames=fields,
    )

    w.writeheader()
    w.writerows(
        checkpoint_rows
    )


print(
    "CHECKPOINT_FILES_DISCOVERED=",
    len(checkpoint_rows),
)


# ============================================================
# 7. NPZ structure inspection WITHOUT loading arrays
#
# Reads .npy headers from inside zip only.
# ============================================================

def inspect_npz_headers(
    path: Path,
):
    result = {
        "path":
            str(
                path.relative_to(ROOT)
            ),

        "members": [],
    }

    try:

        with zipfile.ZipFile(
            path,
            "r",
        ) as zf:

            for name in sorted(
                zf.namelist()
            ):

                if not name.endswith(
                    ".npy"
                ):
                    continue

                member = {
                    "name":
                        name,
                }

                try:
                    with zf.open(
                        name,
                        "r",
                    ) as fh:

                        version = (
                            np.lib.format.read_magic(
                                fh
                            )
                        )

                        if version == (1, 0):
                            shape, fortran, dtype = (
                                np.lib.format.read_array_header_1_0(
                                    fh
                                )
                            )

                        elif version == (2, 0):
                            shape, fortran, dtype = (
                                np.lib.format.read_array_header_2_0(
                                    fh
                                )
                            )

                        else:
                            member[
                                "header_error"
                            ] = (
                                f"unsupported_npy_version_{version}"
                            )

                            result[
                                "members"
                            ].append(
                                member
                            )
                            continue

                        member.update({
                            "shape":
                                list(shape),

                            "dtype":
                                str(dtype),

                            "fortran":
                                bool(fortran),
                        })

                except Exception as e:
                    member[
                        "header_error"
                    ] = (
                        f"{type(e).__name__}: {e}"
                    )

                result[
                    "members"
                ].append(
                    member
                )

    except Exception as e:

        result[
            "zip_error"
        ] = (
            f"{type(e).__name__}: {e}"
        )

    return result


npz_candidates = []

for row in artifact_rows:

    if row["suffix"] != ".npz":
        continue

    p = ROOT / row["path"]

    if not p.exists():
        continue

    # Focus on dataset-related or benchmark/v25 paths.
    low = row["path"].lower()

    if (
        row["datasets"]
        or "benchmark" in low
        or "v25" in low
        or "dataset" in low
        or "data" in low
    ):
        npz_candidates.append(p)


npz_headers = []

# Cap only to protect against pathological repository inventories.
# Prefer dataset-tagged files first.
npz_candidates = sorted(
    npz_candidates,
    key=lambda p: (
        0 if dataset_matches(str(p)) else 1,
        str(p),
    ),
)

for p in npz_candidates[:500]:

    npz_headers.append(
        inspect_npz_headers(p)
    )


write_json(
    OUT / "npz_header_inventory.json",
    npz_headers,
)


print(
    "NPZ_HEADERS_INSPECTED=",
    len(npz_headers),
)


# ============================================================
# 8. Small JSON metadata search
# ============================================================

metadata_hits = []

metadata_key_rx = re.compile(
    r"mean|std|normal|standard"
    r"|dataset|split|subject"
    r"|checkpoint|model|seed"
    r"|channel|acc|gyro",
    re.I,
)


def walk_json(
    obj,
    prefix="",
):
    rows = []

    if isinstance(
        obj,
        dict,
    ):

        for k, v in obj.items():

            keypath = (
                f"{prefix}.{k}"
                if prefix
                else str(k)
            )

            if metadata_key_rx.search(
                str(k)
            ):

                if isinstance(
                    v,
                    (str, int, float, bool)
                ) or v is None:

                    rows.append(
                        (
                            keypath,
                            v,
                        )
                    )

                elif isinstance(
                    v,
                    list,
                ) and len(v) <= 20:

                    rows.append(
                        (
                            keypath,
                            v,
                        )
                    )

            rows.extend(
                walk_json(
                    v,
                    keypath,
                )
            )

    elif isinstance(
        obj,
        list,
    ):

        for i, v in enumerate(obj):

            rows.extend(
                walk_json(
                    v,
                    f"{prefix}[{i}]",
                )
            )

    return rows


for row in artifact_rows:

    if row["suffix"] != ".json":
        continue

    p = ROOT / row["path"]

    if not p.exists():
        continue

    if p.stat().st_size > 5_000_000:
        continue

    try:
        obj = json.loads(
            p.read_text()
        )

    except Exception:
        continue

    hits = walk_json(
        obj
    )

    if not hits:
        continue

    datasets = dataset_matches(
        row["path"]
        + " "
        + json.dumps(
            obj,
            default=str,
        )[:10000]
    )

    for key, value in hits:

        metadata_hits.append({
            "file":
                row["path"],

            "datasets":
                "|".join(datasets),

            "key":
                key,

            "value":
                json.dumps(
                    value,
                    default=str,
                ),
        })


with (
    OUT
    / "json_metadata_evidence.tsv"
).open(
    "w",
    newline="",
    encoding="utf-8",
) as f:

    fields = [
        "file",
        "datasets",
        "key",
        "value",
    ]

    w = csv.DictWriter(
        f,
        fieldnames=fields,
        delimiter="\t",
    )

    w.writeheader()
    w.writerows(
        metadata_hits
    )


print(
    "JSON_METADATA_EVIDENCE_ROWS=",
    len(metadata_hits),
)


# ============================================================
# 9. Dataset-specific evidence summary
# ============================================================

dataset_summary = {}

for dataset in DATASETS:

    aliases = DATASET_ALIASES[
        dataset
    ]

    def relevant_path(
        path: str,
    ):
        low = path.lower()

        return any(
            alias in low
            for alias in aliases
        )

    artifact_subset = [
        r
        for r in artifact_rows
        if dataset
        in r["datasets"].split("|")
    ]

    checkpoint_subset = [
        r
        for r in checkpoint_rows
        if dataset
        in r["datasets"].split("|")
    ]

    json_subset = [
        r
        for r in metadata_hits
        if (
            dataset
            in r["datasets"].split("|")
            or relevant_path(
                r["file"]
            )
        )
    ]

    code_subset = [
        r
        for r in code_evidence
        if relevant_path(
            r["text"]
            + " "
            + r["file"]
        )
    ]

    normalization_json_hits = [
        r
        for r in json_subset
        if re.search(
            r"mean|std|normal|standard",
            r["key"],
            re.I,
        )
    ]

    candidate_npz = [
        x
        for x in npz_headers
        if relevant_path(
            x["path"]
        )
    ]

    dataset_summary[
        dataset
    ] = {
        "artifact_count":
            len(artifact_subset),

        "checkpoint_count_with_dataset_in_path":
            len(checkpoint_subset),

        "json_metadata_rows":
            len(json_subset),

        "normalization_json_rows":
            len(normalization_json_hits),

        "code_evidence_rows":
            len(code_subset),

        "npz_candidates":
            len(candidate_npz),

        "candidate_artifacts":
            [
                r["path"]
                for r in artifact_subset[:100]
            ],

        "candidate_checkpoints":
            [
                r["path"]
                for r in checkpoint_subset[:100]
            ],

        "normalization_metadata_examples":
            normalization_json_hits[:30],

        "npz_header_examples":
            candidate_npz[:20],

        "preliminary_status":
            (
                "EVIDENCE_PRESENT_REQUIRES_MANUAL_RECONCILIATION"
                if (
                    artifact_subset
                    or json_subset
                    or code_subset
                )
                else
                "NO_DATASET_SPECIFIC_ARTIFACT_EVIDENCE_FOUND"
            ),
    }


write_json(
    OUT / "dataset_feasibility_summary.json",
    dataset_summary,
)


# ============================================================
# 10. Compact console report
# ============================================================

print()
print("=" * 100)
print("DATASET FEASIBILITY SUMMARY")
print("=" * 100)

for dataset in DATASETS:

    s = dataset_summary[
        dataset
    ]

    print()
    print(
        dataset
    )

    print(
        " artifact_count=",
        s["artifact_count"],
    )

    print(
        " checkpoint_count_with_dataset_in_path=",
        s[
            "checkpoint_count_with_dataset_in_path"
        ],
    )

    print(
        " json_metadata_rows=",
        s["json_metadata_rows"],
    )

    print(
        " normalization_json_rows=",
        s["normalization_json_rows"],
    )

    print(
        " npz_candidates=",
        s["npz_candidates"],
    )

    print(
        " preliminary_status=",
        s["preliminary_status"],
    )

    print(
        " candidate_checkpoints:"
    )

    for p in s[
        "candidate_checkpoints"
    ][:15]:
        print(
            "   ",
            p,
        )

    print(
        " normalization examples:"
    )

    for r in s[
        "normalization_metadata_examples"
    ][:10]:

        print(
            "   ",
            r["file"],
            "::",
            r["key"],
            "=",
            r["value"][:250],
        )

    print(
        " NPZ examples:"
    )

    for r in s[
        "npz_header_examples"
    ][:8]:

        member_summary = [
            (
                x.get("name"),
                x.get("shape"),
                x.get("dtype"),
            )
            for x in r.get(
                "members",
                [],
            )
        ]

        print(
            "   ",
            r["path"],
            member_summary[:8],
        )


# ============================================================
# 11. Checkpoint pattern summary
# ============================================================

print()
print("=" * 100)
print("CHECKPOINT PATH PATTERN SUMMARY")
print("=" * 100)

pattern_counts = defaultdict(
    int
)

for r in checkpoint_rows:

    parts = Path(
        r["path"]
    ).parts

    # compact final 4 components
    pattern = "/".join(
        parts[-4:]
    )

    pattern_counts[
        pattern
    ] += 1


for pattern, count in sorted(
    pattern_counts.items(),
    key=lambda kv: (
        -kv[1],
        kv[0],
    ),
)[:150]:

    print(
        count,
        pattern,
    )


# ============================================================
# 12. Explicit important code hits
# ============================================================

print()
print("=" * 100)
print("HIGH-VALUE NORMALIZATION / SPLIT / CHECKPOINT CODE HITS")
print("=" * 100)

high_rx = re.compile(
    r"mean|std|normaliz|standardiz"
    r"|best_model|checkpoint|ckpt"
    r"|subject.*split|train.*split",
    re.I,
)

shown = 0

for row in code_evidence:

    if not high_rx.search(
        row["text"]
    ):
        continue

    print(
        f"{row['file']}:{row['line']}: "
        f"{row['text']}"
    )

    shown += 1

    if shown >= 300:
        break


# ============================================================
# 13. Final receipt
# ============================================================

receipt = {
    "audit":
        "STAGE25_PHYSICAL_FAULT_FEASIBILITY_R1",

    "objective": (
        "Recover exact frozen dataset, normalization, and checkpoint "
        "evidence required to evaluate existing models under a "
        "pre-normalization sensor-domain reliability protocol."
    ),

    "datasets":
        DATASETS,

    "models_loaded":
        False,

    "model_forward_performed":
        False,

    "dataset_arrays_loaded":
        False,

    "training_performed":
        False,

    "checkpoints_modified":
        False,

    "existing_results_modified":
        False,

    "checkpoint_files_discovered":
        len(checkpoint_rows),

    "npz_headers_inspected":
        len(npz_headers),

    "scientific_protocol_status":
        "NOT_YET_FROZEN_PENDING_DATASET_SPECIFIC_PROVENANCE_RECONCILIATION",

    "next_gate": (
        "For each dataset prove exact model-input channel semantics, "
        "frozen subject split, affine train normalization, recoverable "
        "pre-normalization window representation, and canonical frozen "
        "checkpoint locator before any evaluation."
    ),

    "stage24_status":
        "FROZEN_COMPLETE",

    "stage24_closure_sha256":
        "15ab874acc4d0420adff73bef32f76b8882a743509682333fdb87fa925060bfa",
}

write_json(
    OUT / "stage25_feasibility_audit_receipt.json",
    receipt,
)


print()
print("=" * 100)
print("STAGE25 FEASIBILITY AUDIT RECEIPT")
print("=" * 100)
print(
    json.dumps(
        receipt,
        indent=2,
    )
)

print()
print(
    "STAGE25_PHYSICAL_FAULT_FEASIBILITY_R1_COMPLETE=True"
)

print(
    "TRAINING_PERFORMED=False"
)

print(
    "MODEL_FORWARD_PERFORMED=False"
)

print(
    "MODEL_LOADED=False"
)

print(
    "DATASET_ARRAYS_LOADED=False"
)

print(
    "CHECKPOINTS_MODIFIED=False"
)

print(
    "EXISTING_RESULTS_MODIFIED=False"
)
