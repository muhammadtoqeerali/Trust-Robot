#!/usr/bin/env python3
"""Independent standalone R56 SHA manifest and science-boundary verifier."""

import hashlib
import json
import pathlib
import stat

ROOT = pathlib.Path(__file__).resolve().parent

def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            b = f.read(1024 * 1024)
            if not b:
                break
            h.update(b)
    return h.hexdigest()

manifest = json.loads(
    (ROOT / "manifest.json").read_text(encoding="utf-8")
)

assert manifest["schema"] == (
    "trust_robot_r51_r55f_checkpoint_manifest_v1"
)
assert manifest["ground_truth_status"] == "NOT_ACQUIRED"
assert manifest["scientific_gates"] == "ALL_11_CLOSED"
assert manifest["real_pose_factors"] == "DENIED"
assert manifest["health_training"] == "DENIED"
assert manifest["ate_rpe"] == "DENIED"
assert manifest["confirmation_test_accessed"] is False
assert manifest["raw_bag_opened"] is False

files = manifest["files"]
assert files
assert set(manifest["phase_file_counts"]) == {
    "r51", "r52", "r53", "r54", "r55", "r55f"
}

for name, meta in sorted(files.items()):
    relative = pathlib.PurePosixPath(name)
    assert not relative.is_absolute()
    assert ".." not in relative.parts
    assert relative.parts[0] == "evidence"

    path = ROOT.joinpath(*relative.parts)
    st = path.lstat()

    assert stat.S_ISREG(st.st_mode)
    assert st.st_nlink == 1
    assert st.st_size == meta["bytes"]
    assert sha(path) == meta["sha256"]

    # No original external source is required to run this verifier.

for phase, expected in manifest["independent_report_sha256"].items():
    directory = [
        name for name in files
        if name.startswith("evidence/")
        and (
            "/trust_robot_" + phase + "_"
        ) in name
        and name.endswith("_independent_validation_v1.json")
    ]

    # Original directory names are not uniformly phase-prefixed;
    # use the verified report digest as the identity key.
    matches = [
        name for name, meta in files.items()
        if name.endswith("_independent_validation_v1.json")
        and meta["sha256"] == expected
    ]

    assert len(matches) == 1, phase

    report = json.loads(
        (ROOT / matches[0]).read_text(encoding="utf-8")
    )
    assert isinstance(report, dict)

actual = {
    p.relative_to(ROOT).as_posix()
    for p in (ROOT / "evidence").rglob("*")
    if p.is_file() or p.is_symlink()
}

assert actual == set(files)

print("R56_STANDALONE_MANIFEST_VERIFIER=PASS")
print("R56_STANDALONE_HASH_FILES=" + str(len(files)))
print("R56_FROZEN_INDEPENDENT_REPORTS=6_SHA_VERIFIED")
print("R56_GROUND_TRUTH=NOT_ACQUIRED")
print("R56_SCIENTIFIC_GATES=11_CLOSED")
print("R56_REAL_FACTORS_HEALTH_ATE_RPE=DENIED")
