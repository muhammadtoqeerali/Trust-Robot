"""Verify the L31-L35 engineering provenance and witness checkpoint."""

import ast
import hashlib
import json
from pathlib import Path, PurePosixPath

root = Path(__file__).resolve().parent
repo = root.parent.parent

BASE = "2ac0a332bf6a5d749f5a75fe7d5a53572ea0e109"

PINS = {
    "code/l31_multimodal_provenance.py":
        "dbb86672c8d6f9940a73f78b1b75e83ee217047ea0451df4c4274fd1b152eb6a",
    "evidence/l31_provenance_timing_audit.json":
        "4a54a1ece6b5a6fcab6c61001983fb9c69f0be8cf9a4928dade3c28d5846a24b",
    "code/l32_cross_run_independence.py":
        "194214c9fcf03eca3e347d2516b6bd39686617b66e5229a69618d6f39cdb626a",
    "evidence/l32_cross_run_independence_audit.json":
        "949eaa79cf967a4c910dd54e69c5c03194a68aaa819137c415124cdcacbc9585",
    "code/l33_future_acquisition_contract.py":
        "1c2b3ce3639b922e7db599ebee9ace484fc023d9d731e5c2ddd82c82ac501baf",
    "evidence/l33_prospective_acquisition_contract.json":
        "24e71f94c8acfc3aa59184c49a811d62f54fc93d90178bbebef6c8239912467b",
    "evidence/l33_evidence_gap_assessment.json":
        "092cbe6e986ee7e44207d20226a731b237c37b3b01b0770df4aa466d6f184a32",
    "code/l34_issue_challenge.py":
        "1bbb737b11bf902421f17a99527272deb29648b004305c61c89bd9176ea4e397",
    "code/l34_snapshot_witness.py":
        "2edeb1637b8775da9ccf62a251e3d5b2bf1c632616e9d0917985069bb91afe73",
    "code/l34_verify_receipt.py":
        "fa94947030bd3637904fe871f0b701528b6c2c64b2df22989c37c1c34c5238e5",
    "evidence/l34_challenge.json":
        "464d02f9e8a1376124e79590ed0bd3d0210fe07ea20c4eb8f5f428c6b0f691db",
    "evidence/l34_witness_receipt.json":
        "8beeaeba0eb931b3a4f7e6ac4eb688cbf97b19564865cbac133b7f806f91b20a",
    "evidence/l34_witness_validation.json":
        "49d1f4aed8e69ac5cc9ed8018a0340ab8e664cb94668f1e824cc7521b24ca010",
    "code/l35_workflow.py":
        "ffbb13927eb0d5a6c9ec04970952eed93995d3ed6dc2d93f464d4e098fa804ad",
    "code/l35_independent_verify.py":
        "57bbad8ff4fefb6d821984eba67bafd02a7b1a3c7b61a666120ad3b4090a6199",
    "evidence/l35_challenge.json":
        "13cc5aacfe4158578a6fd0faeb5f4e82c7ee4fb40fdcb9ccbb3d138cd2b9d316",
    "evidence/l35_transcript.jsonl":
        "b2fa0728d1aa867d162bae7e463f7bf353b058222d2700eaf392cd271ed97736",
    "evidence/l35_session_manifest.json":
        "ee23238ba3df2beff518c08973cf5e73aea69f1ce7dad1985d5369e31295d479",
    "evidence/l35_seal_receipt.json":
        "8b8a27fddd70c39d3864263e1bb78c309bd5649717ac533bf7261113dae73783",
    "evidence/l35_rehearsal_validation.json":
        "a0f40a5fa2d0c9dff055278305fb05047e1c8c664d4c905d7978086f59fb4991",
}

def sha(path):
    assert path.is_file() and not path.is_symlink(), path
    assert path.stat().st_nlink == 1, path
    assert path.stat().st_size <= 3_000_000, path
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load(relative):
    return json.loads((root / relative).read_text(encoding="utf-8"))

manifest = load("checkpoint_manifest_v1.json")

assert manifest["schema"] == "TRUST_ROBOT_KIOS_L31_L35_CHECKPOINT_V1"
assert manifest["parent_commit"] == BASE
assert manifest["branch"] == "kios-isaacsim-v15-integration"
assert set(manifest["phases"]) == {"31", "32", "33", "34", "35"}

files = manifest["files_sha256"]
assert set(files) == set(PINS) | {"README.md"}

actual = {
    p.relative_to(root).as_posix()
    for p in root.rglob("*")
    if p.is_file()
}

assert actual == set(files) | {
    "checkpoint_manifest_v1.json",
    "verify_checkpoint.py",
}, "Unexpected or missing archive file"

for relative, expected in files.items():
    p = PurePosixPath(relative)
    assert not p.is_absolute()
    assert ".." not in p.parts
    assert p.parts[0] in ("code", "evidence", "README.md")

    f = root / relative
    assert sha(f) == expected, relative

    if relative in PINS:
        assert expected == PINS[relative], relative

    if f.suffix == ".py":
        ast.parse(f.read_text(encoding="utf-8"))
    elif f.suffix == ".json":
        json.loads(f.read_text(encoding="utf-8"))
    elif f.suffix == ".jsonl":
        assert all(
            isinstance(json.loads(line), dict)
            for line in f.read_text(encoding="utf-8").splitlines()
        )

for phase, entries in manifest["phases"].items():
    assert entries
    assert all(name in PINS for name in entries)

assert sum(len(x) for x in manifest["phases"].values()) == 20
assert len(set(
    f for entries in manifest["phases"].values() for f in entries
)) == 20

l31 = load("evidence/l31_provenance_timing_audit.json")
l32 = load("evidence/l32_cross_run_independence_audit.json")
l33c = load("evidence/l33_prospective_acquisition_contract.json")
l33r = load("evidence/l33_evidence_gap_assessment.json")
l34c = load("evidence/l34_challenge.json")
l34w = load("evidence/l34_witness_receipt.json")
l34r = load("evidence/l34_witness_validation.json")
l35c = load("evidence/l35_challenge.json")
l35m = load("evidence/l35_session_manifest.json")
l35w = load("evidence/l35_seal_receipt.json")
l35r = load("evidence/l35_rehearsal_validation.json")

assert l31["implementation_sha256"] == sha(
    root / "code/l31_multimodal_provenance.py"
)
assert l32["implementation_sha256"] == sha(
    root / "code/l32_cross_run_independence.py"
)
assert l33r["implementation_sha256"] == sha(
    root / "code/l33_future_acquisition_contract.py"
)
assert l33r["contract_sha256"] == sha(
    root / "evidence/l33_prospective_acquisition_contract.json"
)
assert l34r["witness_source_sha256"] == sha(
    root / "code/l34_snapshot_witness.py"
)
assert l34r["verifier_source_sha256"] == sha(
    root / "code/l34_verify_receipt.py"
)
assert l34r["challenge_sha256"] == sha(
    root / "evidence/l34_challenge.json"
)
assert l34r["receipt_sha256"] == sha(
    root / "evidence/l34_witness_receipt.json"
)
assert l35r["workflow_source_sha256"] == sha(
    root / "code/l35_workflow.py"
)
assert l35r["verifier_source_sha256"] == sha(
    root / "code/l35_independent_verify.py"
)

assert l35r["challenge_sha256"] == sha(
    root / "evidence/l35_challenge.json"
)
assert l35r["transcript_sha256"] == sha(
    root / "evidence/l35_transcript.jsonl"
)
assert l35r["session_manifest_sha256"] == sha(
    root / "evidence/l35_session_manifest.json"
)
assert l35r["witness_receipt_sha256"] == sha(
    root / "evidence/l35_seal_receipt.json"
)

counts = {"camera": 6, "lidar": 6, "imu": 130, "usd_pose": 130}
assert l31["event_counts"] == counts
assert l31["adversarial_mutations_rejected_count"] == 16
assert l32["events_verified_each_run"] == 272
assert l32["raw_source_files_sha256_verified"] == 28

for mod, identical in (
    ("camera", 0),
    ("lidar", 6),
    ("imu", 130),
    ("usd_pose", 130),
):
    assert l32["cross_run"][mod]["identical_payload_sha256"] == identical
    assert l32["cross_run"][mod]["same_device_inode"] == 0

assert l33r["adversarial_mutations_rejected_count"] == 20
assert l33r["evidence_requirements_independently_qualified"] == 0
assert l33r["evidence_requirements_total"] == 11
assert all(
    v == "DENIED_INSUFFICIENT_EVIDENCE"
    for v in l33r["scientific_admission_decisions"].values()
)

assert len(l33c["future_capture_stages"]) == 4
assert l34r["source_files_rehashed"] == 16
assert l34r["adversarial_mutations_rejected_count"] == 16
assert l34w["file_count"] == 16
assert l34w["challenge_file_sha256"] == sha(
    root / "evidence/l34_challenge.json"
)

assert l34w["challenge_nonce_sha256"] == hashlib.sha256(
    bytes.fromhex(l34c["nonce_hex"])
).hexdigest()

assert l35r["fixture_source_records"] == 12
assert l35r["rehearsed_new_sensor_measurements"] == 0
assert l35r["negative_controls_count"] == 25
assert l35r["software_order_verified"] is True
assert l35r["software_order_is_trusted_physical_time"] is False

assert l35m["challenge_file_sha256"] == sha(
    root / "evidence/l35_challenge.json"
)
assert l35m["transcript_sha256"] == sha(
    root / "evidence/l35_transcript.jsonl"
)
assert l35w["session_manifest_sha256"] == sha(
    root / "evidence/l35_session_manifest.json"
)

assert (
    l35c["issued_monotonic_ns_untrusted"]
    < l35m["writer_start_monotonic_ns_untrusted"]
    <= l35m["writer_end_monotonic_ns_untrusted"]
    < l35w["witness_start_monotonic_ns_untrusted"]
    <= l35w["witness_end_monotonic_ns_untrusted"]
)

transcript = [
    json.loads(line)
    for line in (
        root / "evidence/l35_transcript.jsonl"
    ).read_text(encoding="utf-8").splitlines()
]

assert len(transcript) == 12

def compact(obj):
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")

previous = hashlib.sha256(
    ("L35_GENESIS_V1:" + sha(
        root / "evidence/l35_challenge.json"
    )).encode("utf-8")
).hexdigest()

for n, entry in enumerate(transcript, 1):
    assert entry["ordinal"] == n
    assert entry["previous_record_sha256"] == previous
    assert entry["new_sensor_measurement"] is False
    assert entry["pose_factor_authorized"] is False

    unsigned = {
        k: v for k, v in entry.items()
        if k != "record_sha256"
    }
    assert hashlib.sha256(compact(unsigned)).hexdigest() == (
        entry["record_sha256"]
    )
    previous = entry["record_sha256"]

assert previous == l35m["last_record_sha256"]
assert previous == l35w["last_record_sha256"]

upstream = repo / "experiments/isaacsim_v16_l24_l30_multimodal_evidence_v1"

upstream_pins = {
    "evidence/l30_fresh_runtime_events_v1.jsonl":
        "b28c333347ebb9c7262b636c355324b9abfa0b03beeb7c1af5a8b473a7144444",
    "evidence/l30_fresh_runtime_manifest_v1.json":
        "cd202b19dd86a1b00871c2ec55690cab30898b7120906d064390009363138d80",
    "evidence/l27_acquisition_contract_v1.json":
        "7078da5e5c9ba0db5052f2ecb8d02544379b4d70cb319a3d7cab3e6a8fd52931",
}

assert manifest["upstream_sha256"] == upstream_pins

for relative, expected in upstream_pins.items():
    assert sha(upstream / relative) == expected

assert l31["input_sha256"]["l30_events"] == upstream_pins[
    "evidence/l30_fresh_runtime_events_v1.jsonl"
]

for relative, expected in manifest["documentation_sha256"].items():
    assert relative in (
        "AGENTS.md",
        "docs/TRUST_ROBOT_PROJECT_STATE.md",
        "docs/audits/trust_robot/TRUST_ROBOT_KIOS_L31_L35_PROVENANCE_WITNESS_V1.md",
    )
    assert sha(repo / relative) == expected

for flag in (
    "independent_source_authenticity_verified",
    "hardware_attestation_verified",
    "physical_exposure_sync_verified",
    "independent_6dof_reference_verified",
    "calibrated_health_probabilities",
    "raw_recordings_published",
    "frozen_frontend_modified",
):
    assert manifest[flag] is False

assert manifest["pose_factors_authorized"] == 0
assert manifest["health_labels_generated"] == 0
assert manifest["new_sensor_acquisitions"] == 0

for p in root.rglob("*"):
    assert not p.is_symlink()
    if p.is_file():
        sha(p)
        assert p.suffix.lower() not in (
            ".npy", ".npz", ".usd", ".usda", ".usdc",
            ".log", ".bin", ".so", ".pt", ".pth",
        )

print("L31_L35_CHECKPOINT_INTEGRITY=PASS")
print("L31_L35_ALL_SOURCE_HASHES=VERIFIED")
print("L31_L35_FULL_EVIDENCE_CHAIN=PASS")
print("L34_WITNESS_ARCHIVE=VERIFIED")
print("L35_CHALLENGE_AND_CHAIN=VERIFIED")
print("L31_L35_SCIENTIFIC_RESTRICTIONS=ENFORCED")
print("SCIENTIFIC_POSE_FACTORS=0")
