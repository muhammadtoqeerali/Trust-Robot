#!/usr/bin/env python3
"""Prepare an isolated V16 USD scene without starting Isaac Sim."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from trust_robot.isaacsim_v16_scene_preparation import (
    SCHEMA,
    build_v16_scene,
    validate_output_destination,
)


WORKSPACE = Path("/home/kios/TRUST_ROBOT_ALI")
REPO = Path(__file__).resolve().parents[2]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if REPO.parent != WORKSPACE:
        raise RuntimeError(
            "Project checkout is not under the dedicated workspace"
        )

    destination = validate_output_destination(
        WORKSPACE,
        args.output,
    )

    v15 = REPO / "experiments/isaacsim_v15"

    scene_path = v15 / "multimodal_scene_v5.usda"
    source_path = (
        v15 / "multimodal_probe_candidate_v15.py"
    )
    validation_path = (
        v15 / "multimodal_probe_validation_v15.json"
    )

    validation = json.loads(
        validation_path.read_text()
    )

    original_scene = scene_path.read_bytes()
    original_script = source_path.read_bytes()

    if sha(original_scene) != validation["scene_sha256"]:
        raise RuntimeError(
            "Frozen original USD scene hash mismatch"
        )

    if sha(original_script) != validation["script_sha256"]:
        raise RuntimeError(
            "Frozen original V15 script hash mismatch"
        )

    for relative in (
        "experiments/isaacsim_v15/multimodal_scene_v5.usda",
        "experiments/isaacsim_v15/multimodal_probe_candidate_v15.py",
    ):
        local_blob = subprocess.check_output(
            ["git", "-C", str(REPO),
             "hash-object", "--", relative],
            text=True,
        ).strip()

        published_blob = subprocess.check_output(
            ["git", "-C", str(REPO),
             "rev-parse", f"HEAD:{relative}"],
            text=True,
        ).strip()

        if local_blob != published_blob:
            raise RuntimeError(
                f"Tracked frozen source mismatch: {relative}"
            )

    scene = build_v16_scene(
        original_scene.decode("utf-8")
    ).encode("utf-8")

    manifest = {
        "schema": SCHEMA,
        "status": "OFFLINE_SCENE_PREPARED_NOT_RUNTIME_VERIFIED",
        "data_origin": "SYNTHETIC",
        "source_scene_sha256": sha(original_scene),
        "source_script_sha256": sha(original_script),
        "generated_scene_sha256": sha(scene),
        "marker_rows": 8,
        "marker_columns": 10,
        "marker_count": 80,
        "marker_depth_levels": 3,
        "original_scene_modified": False,
        "original_script_modified": False,
        "visual_corner_eligibility_verified": False,
        "actual_camera_render_verified": False,
        "lidar_runtime_verified": False,
        "imu_runtime_verified": False,
        "cross_modal_sync_verified": False,
        "simulator_launched": False,
        "physical_robot_used": False,
        "health_labels_created": False,
        "physical_calibration_claimed": False,
        "runtime_execution_authorized": False,
    }

    destination.mkdir(mode=0o700)

    scene_file = (
        destination / "v16_feature_scene_candidate.usda"
    )

    with scene_file.open("xb") as handle:
        handle.write(scene)

    manifest_file = (
        destination / "scene_preparation_manifest.json"
    )

    with manifest_file.open("x") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)
        handle.write("\n")

    if sha(scene_file.read_bytes()) != sha(scene):
        raise RuntimeError(
            "Generated scene read-back mismatch"
        )

    print("V15_SOURCE_HASHES=VERIFIED")
    print("V16_MARKER_COUNT=80")
    print("V16_MARKER_DEPTH_LEVELS=3")
    print("GENERATED_SCENE_SHA256=", sha(scene))
    print("GENERATED_SCENE_PATH=", scene_file)
    print("SCENE_PREPARATION=PASS")
    print("SIMULATOR_LAUNCHED=NO")
    print("RUNTIME_RENDER_VERIFIED=NO")


if __name__ == "__main__":
    main()
