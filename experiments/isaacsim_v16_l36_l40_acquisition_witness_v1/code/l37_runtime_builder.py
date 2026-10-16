"""Prepare and statically falsify the L37 Isaac Sim candidate.

No Isaac Sim import, launch, sensor read, or raw file modification.
"""

import argparse
import ast
import hashlib
import importlib.util
import json
import shutil
from pathlib import Path

ORIGINAL_SHA = (
    "993d21523afd54dca39ce6fcf27ba20d430324c5b7b5b9b25939521c0082bb78"
)

L36_CONTRACT_SHA = (
    "ee8dfaa3a0f95813d29efa68f65a3222a39cce5e12cf855c4c3508791dcc05f9"
)

L36_REPORT_SHA = (
    "18ba0c5ee8644581987321a955133518481e86f5c702600b11cf2d9dc904ba96"
)

BASE = "0b542e8644f3c4b98ed92c0f83a7c82a4635ae52"

OLD_ROOT = (
    'E = Path("/home/kios/TRUST_ROBOT_ALI/experiments/'
    'isaacsim_v16_l29_instrumented_candidate_v1")'
)

PREFLIGHT_ANCHOR = (
    "validation = json.loads(META.read_text())\n"
)

SUCCESS_ANCHOR = (
    '    print("MULTIMODAL_RUNTIME=PASS", flush=True)\n'
)

PRE_HOOK = (
    "# L37 fail-closed pre-simulator integration gate.\n"
    "from l37_runtime_guard import preflight_gate as _l37_gate\n"
    "_l37_gate(E, SCENE, META, OUT)\n\n"
)

POST_HOOK = (
    "    # L37 fail-closed post-export sealing interface.\n"
    "    from l37_runtime_guard import seal_after_capture as _l37_seal\n"
    '    _l37_seal(E, OUT / "l29_runtime_envelope_v1")\n\n'
)


def need(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_patch(original, candidate, new_root):
    new_declaration = "E = Path(" + json.dumps(new_root) + ")"

    need(
        candidate.count(new_declaration) == 1,
        "Candidate root declaration",
    )
    need(
        candidate.count(PRE_HOOK) == 1,
        "Preflight hook missing or duplicated",
    )
    need(
        candidate.count(POST_HOOK) == 1,
        "Sealing hook missing or duplicated",
    )

    need(
        candidate.index(PRE_HOOK)
        < candidate.index("from isaacsim import SimulationApp"),
        "Preflight gate must precede simulator initialization",
    )
    need(
        candidate.index(POST_HOOK)
        > candidate.index("    _l29_export("),
        "Sealing hook must follow L29 metadata export",
    )
    need(
        candidate.index(POST_HOOK)
        < candidate.index(SUCCESS_ANCHOR),
        "Sealing hook must precede success marker",
    )

    restored = candidate.replace(PRE_HOOK, "", 1)
    restored = restored.replace(POST_HOOK, "", 1)
    restored = restored.replace(new_declaration, OLD_ROOT, 1)

    need(
        restored == original,
        "Original sensor acquisition code was modified",
    )

    ast.parse(candidate)
    return True


def main(args):
    original_path = Path(args.original)
    guard_path = Path(args.guard)
    probe_path = Path(args.probe)
    candidate_guard = Path(args.candidate_guard)

    need(
        sha(original_path) == ORIGINAL_SHA,
        "Frozen L29 acquisition source",
    )
    need(
        sha(args.l36contract) == L36_CONTRACT_SHA,
        "L36 contract mismatch",
    )
    need(
        sha(args.l36report) == L36_REPORT_SHA,
        "L36 report mismatch",
    )

    l36 = json.loads(Path(args.l36report).read_text())
    need(l36["negative_controls_count"] == 46, "L36 controls")
    need(
        l36["simulator_launch_authorized"] is False,
        "L36 authorization",
    )

    source = original_path.read_text(encoding="utf-8")
    guard = guard_path.read_text(encoding="utf-8")

    ast.parse(source)
    ast.parse(guard)

    need(source.count(OLD_ROOT) == 1, "Old root anchor")
    need(source.count(PREFLIGHT_ANCHOR) == 1, "Preflight anchor")
    need(source.count(SUCCESS_ANCHOR) == 1, "Final success anchor")

    new_root = str(probe_path.parent)
    new_declaration = "E = Path(" + json.dumps(new_root) + ")"

    patched = source.replace(
        OLD_ROOT, new_declaration, 1
    )
    patched = patched.replace(
        PREFLIGHT_ANCHOR,
        PRE_HOOK + PREFLIGHT_ANCHOR,
        1,
    )
    patched = patched.replace(
        SUCCESS_ANCHOR,
        POST_HOOK + SUCCESS_ANCHOR,
        1,
    )

    verify_patch(source, patched, new_root)

    need(not probe_path.exists(), "Candidate exists")
    need(not candidate_guard.exists(), "Candidate guard exists")

    probe_path.write_text(patched, encoding="utf-8")
    shutil.copyfile(guard_path, candidate_guard)

    need(sha(candidate_guard) == sha(guard_path), "Guard copy mismatch")

    spec = importlib.util.spec_from_file_location(
        "l37_offline_guard_test", str(candidate_guard)
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    root = probe_path.parent

    try:
        module.preflight_gate(
            root,
            root / "multimodal_scene_v5.usda",
            root / "multimodal_probe_validation_v15.json",
            root / "multimodal_probe_results_v15",
        )
    except PermissionError as exc:
        need(
            str(exc) == "L37_LIVE_SIMULATOR_LAUNCH_NOT_AUTHORIZED",
            "Unexpected preflight denial",
        )
    else:
        raise ValueError("Preflight incorrectly authorized live launch")

    try:
        module.seal_after_capture(
            root,
            root / "multimodal_probe_results_v15"
            / "l29_runtime_envelope_v1",
        )
    except PermissionError as exc:
        need(
            str(exc) == "L37_LIVE_CAPTURE_SEAL_NOT_QUALIFIED",
            "Unexpected sealing denial",
        )
    else:
        raise ValueError("Sealing incorrectly admitted live capture")

    # Mutation testing operates entirely in memory.
    # The original and generated source files remain unchanged.
    mutations = {
        "missing_preflight": patched.replace(PRE_HOOK, "", 1),
        "missing_seal": patched.replace(POST_HOOK, "", 1),
        "altered_root": patched.replace(
            new_declaration, OLD_ROOT, 1
        ),
        "modified_step_count": patched.replace(
            "for step in range(130):",
            "for step in range(129):", 1
        ),
        "modified_world_step": patched.replace(
            "world.step(render=True)",
            "world.step(render=False)", 1
        ),
        "removed_enable_guard": patched.replace(
            'assert os.environ.get("TRUST_ROBOT_SENSOR_PROBE_ENABLE") == "1"',
            'assert True', 1
        ),
        "changed_network_guard": patched.replace(
            'assert os.readlink("/proc/self/ns/net") != host_netns',
            'assert True', 1
        ),
        "changed_capture_mode": patched.replace(
            '"SIMULATOR_POST_CAPTURE_UNQUALIFIED"',
            '"UNVERIFIED_REPLACEMENT"', 1
        ),
        "removed_adapter_export": patched.replace(
            "    _l29_export(", "    _l29_export_disabled(", 1
        ),
        "altered_success_marker": patched.replace(
            SUCCESS_ANCHOR,
            '    print("UNVERIFIED_SUCCESS", flush=True)\n', 1
        ),
        "duplicated_preflight": patched.replace(
            PRE_HOOK, PRE_HOOK + PRE_HOOK, 1
        ),
        "duplicated_seal": patched.replace(
            POST_HOOK, POST_HOOK + POST_HOOK, 1
        ),
    }

    rejected = []

    for name, modified in mutations.items():
        need(modified != patched, "Mutation did not change source: " + name)

        try:
            verify_patch(source, modified, new_root)
        except (ValueError, SyntaxError):
            rejected.append(name)
        else:
            raise ValueError("Mutation incorrectly accepted: " + name)

    need(len(rejected) == 12, "Mutation count")

    plan = {
        "schema": "TRUST_ROBOT_L37_RUNTIME_INTEGRATION_PLAN_V1",
        "parent_git_commit": BASE,
        "candidate_script_sha256": sha(probe_path),
        "runtime_guard_sha256": sha(candidate_guard),
        "frozen_l29_source_sha256": ORIGINAL_SHA,
        "l36_contract_sha256": L36_CONTRACT_SHA,
        "l36_report_sha256": L36_REPORT_SHA,
        "preflight_location": "BEFORE_SIMULATIONAPP_IMPORT",
        "sealing_location": "AFTER_L29_EXPORT_BEFORE_SUCCESS",
        "source_preservation": "EXACT_EXCEPT_ROOT_AND_TWO_HOOKS",
        "live_simulator_launch_enabled": False,
        "live_sealing_enabled": False,
        "scene_and_runtime_assets_staged": False,
        "candidate_metadata_rebound_to_new_script_hash": False,
        "legacy_l29_run_id_migrated": False,
        "durable_nonce_replay_registry_implemented": False,
        "independent_witness_storage_implemented": False,
        "scientific_sensor_authenticity_verified": False,
        "physical_exposure_synchronization_verified": False,
        "independent_6dof_reference_verified": False,
        "pose_factors_authorized": 0,
        "health_labels_generated": 0,
        "next": "L38_PRECAPTURE_SESSION_BINDING_AND_SEALING_DESIGN",
    }

    report = {
        "schema": "TRUST_ROBOT_L37_NONEXECUTED_RUNTIME_INTEGRATION_VALIDATION_V1",
        "parent_git_commit": BASE,
        "builder_source_sha256": sha(__file__),
        "guard_source_sha256": sha(guard_path),
        "candidate_source_sha256": sha(probe_path),
        "candidate_guard_sha256": sha(candidate_guard),
        "original_l29_source_sha256": ORIGINAL_SHA,
        "plan_sha256": None,
        "pre_simulator_gate_position_verified": True,
        "post_export_seal_position_verified": True,
        "original_acquisition_logic_preserved": True,
        "runtime_preflight_denied": True,
        "runtime_seal_denied": True,
        "static_mutations_rejected": rejected,
        "static_mutations_rejected_count": len(rejected),
        "candidate_executed": False,
        "simulator_executed": False,
        "new_sensor_measurements": 0,
        "raw_recordings_modified": False,
        "git_commit_or_push_performed": False,
        "independent_source_authenticity_verified": False,
        "physical_exposure_sync_verified": False,
        "pose_factors_authorized": 0,
        "health_labels_generated": 0,
    }

    plan_path = Path(args.plan)
    report_path = Path(args.report)

    need(not plan_path.exists(), "Plan exists")
    need(not report_path.exists(), "Report exists")

    plan_path.write_text(
        json.dumps(plan, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    report["plan_sha256"] = sha(plan_path)

    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print("L37_CANDIDATE_SOURCE_GENERATED=PASS")
    print("L37_PRE_SIMULATOR_GATE=VERIFIED")
    print("L37_POST_EXPORT_SEAL_HOOK=VERIFIED")
    print("L37_ORIGINAL_SENSOR_LOGIC=BYTE_PRESERVED")
    print("L37_RUNTIME_LAUNCH=DENIED")
    print("L37_STATIC_MUTATION_CONTROLS=12_PASS")
    print("L37_OFFLINE_INTEGRATION=PASS")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    for name in (
        "original",
        "guard",
        "probe",
        "candidate_guard",
        "l36contract",
        "l36report",
        "plan",
        "report",
    ):
        parser.add_argument(
            "--" + name.replace("_", "-"),
            dest=name,
            required=True,
        )

    main(parser.parse_args())
