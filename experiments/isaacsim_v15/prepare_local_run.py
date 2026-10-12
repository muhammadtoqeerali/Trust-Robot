#!/usr/bin/env python3
"""Create an isolated runnable copy; never launch Isaac Sim."""
import argparse
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WORK = Path("/home/kios/TRUST_ROBOT_ALI").resolve()
ANCHOR = 'E = Path("/home/kios/TRUST_ROBOT_ALI/experiments/nova_clean_baseline_v1")'

def sha(b):
    return hashlib.sha256(b).hexdigest()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    dest = args.destination.absolute()

    permitted_parent = WORK / "experiments"
    if dest.parent != permitted_parent:
        parser.error("destination must be a new direct child of " + str(permitted_parent))
    if not permitted_parent.is_dir() or permitted_parent.is_symlink():
        parser.error("unsafe experiment parent")
    if dest.exists() or dest.is_symlink():
        parser.error("destination already exists")

    src = ROOT / "multimodal_probe_candidate_v15.py"
    usd = ROOT / "multimodal_scene_v5.usda"
    meta = ROOT / "multimodal_probe_validation_v15.json"

    old = json.loads(meta.read_text())
    source = src.read_text()
    assert sha(src.read_bytes()) == old["script_sha256"]
    assert sha(usd.read_bytes()) == old["scene_sha256"]
    assert source.count(ANCHOR) == 1

    adapted = source.replace(
        ANCHOR,
        "E = Path(" + repr(str(dest)) + ")",
        1
    )
    ast.parse(adapted)

    new = dict(old)
    new["script_sha256"] = sha(adapted.encode())
    new["status"] = "OFFLINE_ADAPTED_NOT_RUNTIME_VERIFIED"

    derivation = {
        "schema": "TRUST_ROBOT_ISAACSIM_V15_LOCAL_DERIVATION_V1",
        "original_script_sha256": old["script_sha256"],
        "adapted_script_sha256": new["script_sha256"],
        "unchanged_scene_sha256": old["scene_sha256"],
        "runtime_verified": False,
        "reason": "local output and scene root relocation only"
    }

    dest.mkdir(mode=0o700)
    (dest / src.name).write_text(adapted)
    (dest / usd.name).write_bytes(usd.read_bytes())
    (dest / meta.name).write_text(
        json.dumps(new, indent=2) + "\n"
    )
    (dest / "local_derivation_v15.json").write_text(
        json.dumps(derivation, indent=2) + "\n"
    )

    print("LOCAL_REPRODUCTION_PREPARATION=PASS")
    print("SIMULATOR_LAUNCHED=NO")
    print("ADAPTED_SOURCE_SHA256=", new["script_sha256"])
    print("DESTINATION=", dest)

if __name__ == "__main__":
    main()
