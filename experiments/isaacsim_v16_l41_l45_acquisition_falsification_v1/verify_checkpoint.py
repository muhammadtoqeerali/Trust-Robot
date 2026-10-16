"""KIOS L41-L45 immutable checkpoint verifier."""

import ast
import hashlib
import json
import pathlib
import subprocess

root = pathlib.Path(__file__).resolve().parent
repo = root.parents[1]

BASE = "8d5a1701df3e9d755ac0a4b5adda2845873f52eb"

PINS = {'code/l41_readiness_assess.py': '0d29394a4774eb93bb7133206a6052161be170f1964eb60bbc880014e3a7f34c', 'code/l41_independent_verify.py': 'aa86693f71291a0e6dd9f6a4269eac1c0eca833da400134498c7bc9f05695b64', 'evidence/l41_readiness.json': '67e0be9b1da5944cf41a3bfeccdfdd5110e5e672de6c4fc7370bf3fa1914e798', 'evidence/l41_validation.json': 'e1507fa4233bc918246a518c4a3b56c474149f843030cd238d7887fcc91a3a84', 'code/l42_offline_bridge.py': '604aab4d79548261b0ab7c99abfa8b4ba2f77b07b9a2447c8a61627a4aee4981', 'code/l42_independent_verify.py': '47eb2ca0696986f456a78d59c5eb85fbab232c656f70e743dd6c24a5f9feb0d9', 'evidence/l42_contract.json': '1b4acef236b12b58d912b20a8c920835e44f44f23fc517fe325f799b5638836d', 'evidence/l42_report.json': 'cb4beb8acb5888e93aa1b041adf6971290f76b25840953ca7b747472caaa2573', 'evidence/l42_validation.json': 'be450eee7acc97b10e17acb8bf826e3958196ba7bbb46af5613c413ef4fe40ac', 'code/l43_offline_session_assessor.py': '1511632b1e8fcbabfa84dd35ffbbd8b0760bcd2893682f7af2334b4ddae5aafd', 'code/l43_independent_verify.py': 'ea38119a46ed4ebb927e6d9371ceba039b826f73213a26d144c30a228869a600', 'evidence/l43_manifest.json': 'aeb1af103fa04fd5b494997b20bb53debc3d2e82bf10bb5e2d95c6397ec1a213', 'evidence/l43_report.json': '4158836e2f1b32a54813cbc17e8ac90812ffa76f598f3210ed467ae9278a0c77', 'evidence/l43_validation.json': '50b541b0f1a595fd6d4e5c94bc6fcbdde20c89b7af7fc92ef8a2acd251f60d3e', 'code/l44_capture_boundary.py': 'f9eb0917972a14ee5f80d64122d23619ede37b589062e1c30200c0bb1d9dae49', 'code/l44_exercise.py': '570ccdb7961d4687a756187f5ac07696a6db9f5d1bf4f55f7b80a2abe87e5620', 'code/l44_independent_verify.py': '9662acca5536d47e659ce1c36c658991b9e8a314f1f924467d82925989cc5269', 'evidence/l44_contract.json': '21620dd3d4220b604fc7e534e5bd9d0ff00aed05d61f4acb15c6366b12f02c5e', 'evidence/l44_report.json': '6742e4630ab3a8d3b0714b854d27639d67220169acb4d2296111e56ad0243340', 'evidence/l44_validation.json': '6aabc031b26ec2bf624a207a5c7e5d5c183fa230a4134ec6f5991fb3085bff5f', 'code/l45_forgery_assessment.py': 'de3729413a5650d673a213d42e42bda08db393a621ca990e19e07d3c948fe532', 'code/l45_independent_verify.py': '6fe61c4844902bbc2fe9c165c8f81b5e37574ce604ee6116e35905875ac7f240', 'evidence/l45_contract.json': '4e51c3199f45fbbaf056385eb64f369a55601982907b42460be57ce356001673', 'evidence/l45_report.json': '9d39841e6942c5ee57346d8ebbafebba291a94239e86f570dd1eff622eb2dd31', 'evidence/l45_validation.json': 'caa547a5f82d1968fa913af85df8c8dbd255282a4ee7bf0a6b06f46ac64a0a6d'}

DYNAMIC = {
    "evidence/l44_complete_receipt.json",
    "evidence/l44_sqlite_snapshot.json",
    "evidence/l45_fabricated_receipt.json",
    "README.md",
}

DOCS = {
    "AGENTS.md",
    "docs/TRUST_ROBOT_PROJECT_STATE.md",
    "docs/audits/trust_robot/TRUST_ROBOT_KIOS_L41_L45_ACQUISITION_FALSIFICATION_V1.md",
}


def need(ok, reason):
    if not ok:
        raise ValueError(reason)


def digest_bytes(data):
    return hashlib.sha256(data).hexdigest()


def digest(path):
    path = pathlib.Path(path)

    need(
        path.is_file()
        and not path.is_symlink()
        and path.stat().st_nlink == 1
        and path.stat().st_size <= 5_000_000,
        "UNSAFE_FILE:" + str(path),
    )

    return digest_bytes(path.read_bytes())


def load(path):
    return json.loads(
        (root / path).read_text(encoding="utf-8")
    )


m = load("checkpoint_manifest_v1.json")

need(
    m["schema"] == "TRUST_ROBOT_KIOS_L41_L45_CHECKPOINT_V1"
    and m["parent_commit"] == BASE,
    "CHECKPOINT_ID",
)

need(
    m["branch"] == "kios-isaacsim-v15-integration",
    "BRANCH",
)

need(
    m["pinned_sha256"] == PINS,
    "IMMUTABLE_PINS",
)

need(
    set(m["files_sha256"]) == set(PINS) | DYNAMIC,
    "CONTENT_INVENTORY",
)

actual = {
    p.relative_to(root).as_posix()
    for p in root.rglob("*")
    if p.is_file()
}

need(
    actual == set(m["files_sha256"]) | {
        "checkpoint_manifest_v1.json",
        "verify_checkpoint.py",
    },
    "ARCHIVE_CONTENT",
)

for rel, expected in m["files_sha256"].items():
    path = pathlib.Path(rel)

    need(
        not path.is_absolute()
        and ".." not in path.parts,
        "UNSAFE_PATH",
    )

    need(
        digest(root / rel) == expected,
        "BAD_HASH:" + rel,
    )

    if rel.endswith(".py"):
        ast.parse(
            (root / rel).read_text(encoding="utf-8")
        )

    if rel.endswith(".json"):
        load(rel)

need(
    set(m["documentation_sha256"]) == DOCS,
    "DOC_INVENTORY",
)

manifest_path = (
    root / "checkpoint_manifest_v1.json"
).relative_to(repo).as_posix()

committed = subprocess.check_output(
    [
        "git", "-C", str(repo),
        "rev-list", "-1", "HEAD", "--",
        manifest_path,
    ],
    text=True,
).strip()

for rel, expected in m["documentation_sha256"].items():
    if committed:
        data = subprocess.check_output(
            [
                "git", "-C", str(repo),
                "show", committed + ":" + rel,
            ]
        )
        observed = digest_bytes(data)
    else:
        observed = digest(repo / rel)

    need(
        observed == expected,
        "HISTORICAL_DOC_PIN:" + rel,
    )

need(
    [
        len(m["phase_files"][str(n)])
        for n in range(41, 46)
    ] == [4, 5, 5, 8, 6],
    "PHASE_COUNTS",
)

phase_files = [
    path
    for n in range(41, 46)
    for path in m["phase_files"][str(n)]
]

need(
    len(phase_files) == 28
    and len(set(phase_files)) == 28
    and set(phase_files)
    == set(m["files_sha256"]) - {"README.md"},
    "PHASE_FILES",
)

r44 = load("evidence/l44_report.json")
r45 = load("evidence/l45_report.json")

need(
    r44["completed_cases"] == 1
    and r44["partial_review_cases"] == 7
    and r44["event_mutation_count"] == 36
    and r44["fault_count"] == 8
    and r44["publication_recovery_verified"] is True,
    "L44_TESTS",
)

need(
    r45["coherent_rekey_count"] == 12
    and r45["coherent_cases_internally_accepted"] == 12
    and r45["coherent_cases_with_trusted_provenance"] == 0
    and r45["incoherent_rejection_count"] == 20
    and r45["recovery_count"] == 2
    and r45["faults_rejected_count"] == 12,
    "L45_TESTS",
)

snapshot = load("evidence/l44_sqlite_snapshot.json")

need(
    snapshot["schema"]
    == "TRUST_ROBOT_L44_SYNTHETIC_SQLITE_SUMMARY_V1"
    and snapshot["source_report_sha256"]
    == PINS["evidence/l44_report.json"]
    and snapshot["raw_sqlite_archived"] is False
    and snapshot["independent_physical_sensor_witness"] is False
    and snapshot["scientific_pose_factors"] == 0,
    "L44_SNAPSHOT",
)

results = snapshot["case_results"]

need(
    len(results) == 8
    and [x["case"] for x in results] == list(range(8)),
    "L44_EIGHT_CASES",
)

need(
    results[0]["receipt_sha256"]
    == digest(root / "evidence/l44_complete_receipt.json"),
    "L44_RECEIPT",
)

for i in range(8):
    item = results[i]
    original = r44["case_results"][i]

    need(
        item["receipt_sha256"]
        == original["receipt_sha256"]
        and item["database_sha256"]
        == original["database_sha256"]
        and item["state"] == original["decision"]
        and item["event_count"]
        == original["synthetic_event_count"]
        and item["outbox_published"] is True,
        "L44_REPORT_BINDING",
    )

need(
    digest(root / "evidence/l45_fabricated_receipt.json")
    == r45["new_local_fabricated_session"]["receipt_sha256"],
    "L45_SYNTHETIC_RECEIPT",
)

need(
    load("evidence/l45_fabricated_receipt.json")["decision"]
    == "COMPLETE_SYNTHETIC",
    "L45_SYNTHETIC_DECISION",
)

for key in (
    "new_sensor_acquisitions",
    "pose_factors_authorized",
    "health_labels_generated",
):
    need(
        m[key] == 0,
        "SCIENCE_ZERO:" + key,
    )

for key in (
    "live_simulator_launch_authorized",
    "independent_source_authenticity_verified",
    "physical_sync_verified",
    "hardware_attestation_verified",
    "raw_sqlite_databases_committed",
    "raw_sensor_recordings_committed",
    "real_power_loss_durability_verified",
):
    need(
        m[key] is False,
        "SCIENCE_CLOSED:" + key,
    )

for path in root.rglob("*"):
    need(
        not path.is_symlink(),
        "ARCHIVE_SYMLINK",
    )

    if path.is_file():
        need(
            path.suffix.lower() not in {
                ".sqlite", ".db", ".npy", ".npz",
                ".usda", ".usd", ".usdc",
                ".bin", ".so", ".log", ".pt", ".pth",
            },
            "UNSAFE_ARCHIVE_TYPE",
        )

print("L41_L45_CHECKPOINT_INTEGRITY=PASS")
print("L41_L45_25_FROZEN_SOURCE_REPORT_HASHES=VERIFIED")
print("L44_L45_COMPACT_SYNTHETIC_EVIDENCE=VERIFIED")
print("L41_L45_COMMIT_SCOPED_DOCUMENTATION=VERIFIED")
print("TRUSTED_SENSOR_ORIGINS=0")
print("SCIENTIFIC_POSE_FACTORS=0")
