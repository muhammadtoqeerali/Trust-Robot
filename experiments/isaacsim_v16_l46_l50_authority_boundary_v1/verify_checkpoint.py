"""KIOS L46-L50 immutable trust-boundary checkpoint verifier."""

import ast
import hashlib
import json
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent
REPO = ROOT.parents[1]

PARENT = "c2e013f549b87e8646a8e51095a3372df0d09581"

FROZEN = {'code/l46_engine_full.py': '2b4c0b7101cdfbfcc6cf438fe1a3d8f6f7f1421d06e2304309c34e3c9a31d2dd', 'code/l46_verify_full.py': '3bfd795ec00c54d6278a695e6a5bcfee57ed4cfda6f961b35fede1b8100d0010', 'evidence/l46_contract.json': 'f5af31413559d5cbda9d7c415f8f36e248744eb6198ba583d84a7d4849e1697d', 'evidence/l46_report.json': '183bf08ffdf467294027af058ab8e627bcec7d35192c612accff78735c1c7e40', 'evidence/l46_validation.json': '044f98088d885ce4fbce3d7390da270c42286d9ca30f7ac00b94e72d14462ef5', 'code/l47_ledger.py': '63b385edc1bb2945ba62a4cf98b82f81373c58d12e5ede497bcc35e8e4249f27', 'code/l47_independent_verify.py': 'b5120140ca4f428940d9aa3fae7a1a744ae47fd615020af560d8749c465beffa', 'evidence/l47_contract.json': '0b2f968936ecee182f09741b8159a75de199625aa999944b5a104739d0128a13', 'evidence/l47_report.json': '40eccecc0e73b6b718f7b3cb9e7936811c7955f07f021672a23fada71ac64f6e', 'evidence/l47_validation.json': 'd0194e6940305e5d129ebcf107298a139b130f34bc1daa55c5fb2bcc0e7dd682', 'code/l48_reconcile.py': '2d5a79bdcef2f9486abd61dce8fdecf4950fecd4b71b276ed7a4735b665de740', 'code/l48_independent_verify.py': '8c432d471a467fd26e1c60d30a81a2220efaf3cb30c3fea4d692b285bebaaa85', 'evidence/l48_contract.json': '90e6fc5409890a9576876900ce6892f6123f6bf1815944483e73e864abed92d9', 'evidence/l48_report.json': '1bea7f9e612fbd3edb1d14577258b089f82581cd2ce2659118fe8d96e3890283', 'evidence/l48_validation.json': '124a53792eeced5515e5b84855a7602eb2f523a663cfc376694d1423df33f9b9', 'code/l49_recovery.py': 'd15014023621cb31d804c8772e09b211376cd91e8fcfa4df16fafe12c38f2b54', 'code/l49_independent_verify.py': 'bfb1d4318c91b630389d754b13a1b561e481e303e0d94f7a453903996a5e420d', 'evidence/l49_contract.json': 'fa91bd78aadc2b7f0343b9c8929dd77419b2f43c4825c4105621931953b0f87c', 'evidence/l49_report.json': '0edb9cc0eb8d274c3b139ab0bacc2abb69c8a33812a9028e9c4f89e69d47816a', 'evidence/l49_validation.json': 'fe6f0e56e689dddbab220d1a5bb150dc44d6f01c05bc0155a3810cf83d60dcb2', 'code/l50_review.py': '08f4558ea0825bb850cf4150bf69fb4a669a68a5720c88a8ec138669e9157645', 'code/l50_independent_verify.py': '2a8940c4ba0b2b26f6314293cd880a526cb76c868239ce32538b0d54f2f0318f', 'evidence/l50_contract.json': 'b9cf102c1f767f43da81ac88a63105c3f0c5bb7ed46e66686359c3167eb513cf', 'evidence/l50_matrix.json': '9c8012fed6b974790875d63107b84f5c8e9049bb591240bae826c4aaf145bffe', 'evidence/l50_report.json': '207feedbf9ea30046e839ef7f6b6c57dce9df548435fd617fa167a376fa4d4e9', 'evidence/l50_validation.json': '3ceafdae855c90b41727419b12a16508004cc618ec1fca3d9fdec98905f803e7'}

EXTRA = {
    "evidence/l47_synthetic_request.json",
    "evidence/l47_central_receipt.json",
    "evidence/l47_split_left_receipt.json",
    "evidence/l47_split_right_receipt.json",
    "evidence/l49_quarantine_receipt.json",
    "evidence/l47_l49_sqlite_snapshot.json",
}

DOCS = {
    "AGENTS.md",
    "docs/TRUST_ROBOT_PROJECT_STATE.md",
    "docs/audits/trust_robot/TRUST_ROBOT_KIOS_L46_L50_TRUST_BOUNDARY_V1.md",
}


def need(ok, why):
    if not ok:
        raise ValueError("L46_L50_CHECKPOINT_FAIL:" + why)


def hashbytes(data):
    return hashlib.sha256(data).hexdigest()


def digest(path):
    p = pathlib.Path(path)

    need(
        p.is_file()
        and not p.is_symlink(),
        "MISSING_FILE:" + str(p),
    )

    need(
        p.stat().st_nlink == 1
        and p.stat().st_size < 5000000,
        "UNSAFE_FILE:" + str(p),
    )

    return hashbytes(p.read_bytes())


def js(relative):
    return json.loads(
        (ROOT / relative).read_text(encoding="utf-8")
    )


def canonical(value):
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ) + "\n"
    ).encode()


m = js("checkpoint_manifest_v1.json")

need(
    m["schema"]
    == "TRUST_ROBOT_KIOS_L46_L50_CHECKPOINT_V1"
    and m["parent_commit"] == PARENT,
    "CHECKPOINT_IDENTITY",
)

need(
    m["branch"] == "kios-isaacsim-v15-integration",
    "CHECKPOINT_BRANCH",
)

need(
    m["frozen_sha256"] == FROZEN,
    "FROZEN_SOURCE_PINS",
)

need(
    set(m["files_sha256"])
    == set(FROZEN) | EXTRA | {"README.md"},
    "MANIFEST_INVENTORY",
)

need(
    set(m["documentation_sha256"]) == DOCS,
    "DOCUMENTATION_INVENTORY",
)

need(
    [
        len(m["phase_files"][str(i)])
        for i in range(46, 51)
    ] == [5, 5, 5, 5, 6],
    "PHASE_COUNTS",
)

phase_files = [
    x
    for i in range(46, 51)
    for x in m["phase_files"][str(i)]
]

need(
    len(phase_files) == 26
    and set(phase_files) == set(FROZEN),
    "PHASE_FILE_INVENTORY",
)

actual = {
    p.relative_to(ROOT).as_posix()
    for p in ROOT.rglob("*")
    if p.is_file()
}

need(
    actual == set(m["files_sha256"]) | {
        "checkpoint_manifest_v1.json",
        "verify_checkpoint.py",
    },
    "EXACT_ARCHIVE_INVENTORY",
)

need(
    len(actual) == 35,
    "ARCHIVE_FILE_COUNT",
)

for path in ROOT.rglob("*"):
    need(
        not path.is_symlink(),
        "ARCHIVE_SYMLINK",
    )

    if path.is_file():
        need(
            path.suffix.lower() not in {
                ".sqlite", ".db", ".npy", ".npz",
                ".usd", ".usda", ".usdc", ".bin",
                ".so", ".log", ".pt", ".pth",
            },
            "FORBIDDEN_ARCHIVE_TYPE",
        )

for relative, expected in m["files_sha256"].items():
    p = pathlib.PurePosixPath(relative)

    need(
        not p.is_absolute()
        and ".." not in p.parts,
        "UNSAFE_RELATIVE_PATH",
    )

    need(
        digest(ROOT / relative) == expected,
        "FILE_DIGEST:" + relative,
    )

    if relative.endswith(".py"):
        ast.parse(
            (ROOT / relative).read_text(
                encoding="utf-8"
            )
        )

    if relative.endswith(".json"):
        js(relative)

# Historical documentation is checked at the commit
# that first introduced this checkpoint manifest.

manifest_relative = (
    ROOT / "checkpoint_manifest_v1.json"
).relative_to(REPO).as_posix()

commit = subprocess.check_output(
    [
        "git", "-C", str(REPO),
        "rev-list", "-1", "HEAD", "--",
        manifest_relative,
    ],
    text=True,
).strip()

for relative, expected in m["documentation_sha256"].items():
    if commit:
        content = subprocess.check_output(
            [
                "git", "-C", str(REPO),
                "show", commit + ":" + relative,
            ]
        )

        observed = hashbytes(content)

    else:
        observed = digest(REPO / relative)

    need(
        observed == expected,
        "COMMIT_SCOPED_DOCUMENTATION:" + relative,
    )

reports = {
    i: js(f"evidence/l{i}_report.json")
    for i in range(46, 51)
}

validations = {
    i: js(f"evidence/l{i}_validation.json")
    for i in range(46, 51)
}

for i in range(46, 51):
    need(
        reports[i]["contract_sha256"]
        == FROZEN[f"evidence/l{i}_contract.json"],
        f"CONTRACT_LINEAGE_{i}",
    )

    need(
        validations[i]["report_sha256"]
        == FROZEN[f"evidence/l{i}_report.json"],
        f"REPORT_LINEAGE_{i}",
    )

r46 = reports[46]
r47 = reports[47]
r48 = reports[48]
r49 = reports[49]
r50 = reports[50]

need(
    r46["test_results"]["negative_controls_denied"] == 35
    and r46["test_results"][
        "coherent_software_forgery_trusted"
    ] is False
    and r46["test_results"][
        "independent_registry_clone_double_acceptance"
    ] is True,
    "L46_OUTCOME",
)

need(
    r47["central_single_host_successes"] == 1
    and r47["central_single_host_replays_denied"] == 7
    and r47["split_registry_same_nonce_admissions"] == 2
    and r47["globally_unique_admission_proven"] is False
    and r47["invalid_request_control_count"] == 20
    and r47["fault_count"] == 8,
    "L47_OUTCOME",
)

need(
    r48["verified_local_receipts"] == 3
    and r48["detected_duplicate_nonce"] is True
    and r48["quarantine_decision"]
    == "QUARANTINE_REVIEW_REQUIRED"
    and r48["metadata_mutation_count"] == 24
    and r48["ledger_fault_count"] == 10,
    "L48_OUTCOME",
)

need(
    r49["scenario_count"] == 18
    and r49["quarantine_decisions"] == 18
    and r49["negative_claim_count"] == 12
    and len(r49["recovery_windows"]) == 3
    and r49["receipt_fault_count"] == 10
    and r49["global_replay_prevention_verified"] is False,
    "L49_OUTCOME",
)

need(
    r50["offline_prototype_gates"] == 6
    and r50["unqualified_required_gates"] == 16
    and r50["negative_control_count"] == 32
    and r50["decision"]
    == "NO_GO_LIVE_CAPTURE_OR_SCIENTIFIC_POSE_FACTORS"
    and r50["reconciliation_state"]
    == "QUARANTINE_REVIEW_REQUIRED",
    "L50_OUTCOME",
)

matrix = js("evidence/l50_matrix.json")

need(
    matrix["unqualified_required_gates"] == 16
    and len(matrix["gates"]) == 22,
    "L50_GAP_MATRIX",
)

need(
    all(
        validations[50][key] == 0
        for key in (
            "new_sensor_measurements",
            "pose_factors_authorized",
            "health_labels_generated",
        )
    ),
    "L50_SCIENCE_FLAGS",
)

for field in (
    "live_simulator_launch_authorized",
    "independent_source_authenticity_verified",
    "global_replay_protection_verified",
    "physical_sync_verified",
    "physical_power_loss_durability_verified",
    "raw_sqlite_databases_committed",
    "raw_sensor_recordings_committed",
    "real_robot_testing_performed",
):
    need(
        m[field] is False,
        "UNSUPPORTED_SCIENCE_CLAIM:" + field,
    )

for field in (
    "new_sensor_acquisitions",
    "scientific_pose_factors",
    "health_labels",
):
    need(
        m[field] == 0,
        "NONZERO_SCIENCE_CLAIM:" + field,
    )

request_path = ROOT / "evidence/l47_synthetic_request.json"
request = js("evidence/l47_synthetic_request.json")

need(
    digest(request_path) == r47["request_sha256"]
    and request_path.read_bytes() == canonical(request),
    "REQUEST_DIGEST_AND_CANONICAL",
)

need(
    len(request["nonce_hex"]) == 64,
    "NONCE_LENGTH",
)

nonce = hashbytes(
    bytes.fromhex(request["nonce_hex"])
)

need(
    request["issuer_role"] == "UNTRUSTED_TEST_GENERATOR"
    and request["source_origin_verified"] is False
    and request["attestation_verified"] is False,
    "REQUEST_SOURCE_TRUST",
)

snapshot = js("evidence/l47_l49_sqlite_snapshot.json")

need(
    snapshot["schema"]
    == "TRUST_ROBOT_L46_L50_LOCAL_SQLITE_SUMMARY_V1",
    "SNAPSHOT_SCHEMA",
)

for phase in (47, 48, 49):
    need(
        snapshot[f"l{phase}_report_sha256"]
        == FROZEN[f"evidence/l{phase}_report.json"],
        "SNAPSHOT_REPORT_LINEAGE",
    )

need(
    snapshot["raw_sqlite_archived"] is False
    and snapshot["independent_physical_source_witness"]
    is False,
    "SNAPSHOT_SCOPE",
)

labels = (
    "central",
    "split_left",
    "split_right",
)

need(
    [
        x["label"]
        for x in snapshot["l47_ledgers"]
    ] == list(labels),
    "SNAPSHOT_LEDGER_INVENTORY",
)

need(
    len({
        x["nonce_sha256"]
        for x in snapshot["l47_ledgers"]
    }) == 1
    and snapshot["l47_ledgers"][0]["nonce_sha256"]
    == nonce,
    "DUPLICATE_NONCE",
)

originals = [
    r47["central"],
    *r47["split"],
]

for label, source in zip(labels, originals):
    relative = f"evidence/l47_{label}_receipt.json"

    receipt = js(relative)
    receipt_digest = digest(ROOT / relative)

    need(
        receipt_digest == source["receipt_sha256"],
        "LOCAL_RECEIPT_HASH",
    )

    need(
        receipt["decision"] == "LOCALLY_ADMITTED"
        and receipt["nonce_sha256"] == nonce
        and receipt["session_id"]
        == request["session_id"]
        and receipt["independent_physical_witness"]
        is False
        and receipt["cross_host_replay_qualified"]
        is False,
        "LOCAL_RECEIPT_SCOPE",
    )

    summary = next(
        x
        for x in snapshot["l47_ledgers"]
        if x["label"] == label
    )

    need(
        summary["receipt_sha256"]
        == source["receipt_sha256"]
        and summary["database_sha256"]
        == source["database_sha256"]
        and summary["request_sha256"]
        == r47["request_sha256"]
        and summary["decision"]
        == "LOCALLY_ADMITTED",
        "LOCAL_LEDGER_SUMMARY",
    )

quarantine = js(
    "evidence/l49_quarantine_receipt.json"
)

need(
    digest(
        ROOT / "evidence/l49_quarantine_receipt.json"
    ) == snapshot["l49_quarantine"]["receipt_sha256"],
    "QUARANTINE_DIGEST",
)

need(
    quarantine["state"]
    == "QUARANTINE_REVIEW_REQUIRED"
    and quarantine["nonce_sha256"] == nonce
    and quarantine["contract_sha256"]
    == FROZEN["evidence/l49_contract.json"]
    and quarantine["report_sha256"]
    == FROZEN["evidence/l49_report.json"]
    and quarantine["autonomous_merge_authorized"]
    is False
    and quarantine["physical_sensor_origin_verified"]
    is False
    and quarantine["distributed_consensus_verified"]
    is False
    and quarantine["sensor_measurements"] == 0
    and quarantine["scientific_pose_factors"] == 0
    and quarantine["health_labels"] == 0,
    "QUARANTINE_SCOPE",
)

expected_receipts = {
    label: digest(
        ROOT / f"evidence/l47_{label}_receipt.json"
    )
    for label in labels
}

need(
    quarantine["source_receipts_sha256"]
    == expected_receipts,
    "QUARANTINE_SOURCE_BINDING",
)

need(
    snapshot["l49_quarantine"]["state"]
    == "QUARANTINE_REVIEW_REQUIRED"
    and snapshot["l49_quarantine"]["published"]
    is True,
    "QUARANTINE_JOURNAL",
)

print("L46_L50_CHECKPOINT_INTEGRITY=PASS")
print("L46_L50_26_FROZEN_SOURCE_REPORT_HASHES=VERIFIED")
print("L46_L50_SIX_COMPACT_SYNTHETIC_ARTIFACTS=VERIFIED")
print("L46_L50_COMMIT_SCOPED_DOCUMENTATION=VERIFIED")
print("DUPLICATE_NONCE=QUARANTINED")
print("TRUSTED_SENSOR_ORIGINS=0")
print("SCIENTIFIC_POSE_FACTORS=0")
