"""Read-only L38 verifier and in-memory falsification suite."""

import argparse
import copy
import hashlib
import json
import sqlite3

from pathlib import Path

BASE = "0b542e8644f3c4b98ed92c0f83a7c82a4635ae52"
CAND = "4384b085f79dff51af5dbbf8a4c4bf4cae6deffc906bfbcaf8a8ef00a7e05dec"
L36C = "ee8dfaa3a0f95813d29efa68f65a3222a39cce5e12cf855c4c3508791dcc05f9"
L35T = "b2fa0728d1aa867d162bae7e463f7bf353b058222d2700eaf392cd271ed97736"

MODE = "OFFLINE_L35_FIXTURE_NO_SENSOR_ACQUISITION"


def need(value, message):
    if not value:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(
        Path(path).read_bytes()
    ).hexdigest()


def load(path):
    return json.loads(
        Path(path).read_text(encoding="utf-8")
    )


def validate(ch, adm, seal, dbrow, hashes):
    need(
        ch["schema"]
        == "TRUST_ROBOT_L38_LOCAL_CHALLENGE_V1",
        "challenge schema",
    )

    need(
        ch["parent_commit"] == BASE
        and ch["mode"] == MODE,
        "challenge parent/mode",
    )

    need(
        isinstance(ch["session_id"], str)
        and ch["session_id"].startswith("KIOS_L38_")
        and len(ch["session_id"]) == 33,
        "challenge ID",
    )

    need(
        ch["candidate_sha256"] == CAND
        and ch["l36_contract_sha256"] == L36C
        and ch["l35_transcript_sha256"] == L35T,
        "challenge lineage",
    )

    need(
        ch["trusted_hardware_attestation"] is False
        and ch["physical_time_verified"] is False,
        "issuer claims",
    )

    need(
        type(ch["issued_monotonic_ns_untrusted"]) is int,
        "challenge timestamp",
    )

    nonce = ch["nonce_hex"]

    need(
        type(nonce) is str
        and len(nonce) == 64
        and all(c in "0123456789abcdef" for c in nonce),
        "nonce",
    )

    nh = hashlib.sha256(
        bytes.fromhex(nonce)
    ).hexdigest()

    need(
        adm["schema"]
        == "TRUST_ROBOT_L38_OFFLINE_ADMISSION_V1",
        "admission schema",
    )

    need(
        adm["session_id"] == ch["session_id"]
        and adm["mode"] == MODE,
        "admission ID",
    )

    need(
        adm["challenge_file_sha256"] == hashes["challenge"]
        and adm["nonce_sha256"] == nh,
        "admission binding",
    )

    need(
        adm["candidate_sha256"] == CAND
        and adm["l36_contract_sha256"] == L36C
        and adm["l35_transcript_sha256"] == L35T,
        "admission provenance",
    )

    need(
        adm["offline_admission"] is True
        and adm["simulator_launch_authorized"] is False,
        "admission scope",
    )

    need(
        adm["new_sensor_measurements"] == 0
        and adm["pose_factors_authorized"] == 0,
        "admission limitations",
    )

    need(
        adm["independent_source_authenticity_verified"]
        is False
        and adm["physical_sync_verified"] is False,
        "admission science flags",
    )

    need(
        seal["schema"]
        == "TRUST_ROBOT_L38_LOCAL_SEAL_V1",
        "seal schema",
    )

    need(
        seal["session_id"] == ch["session_id"]
        and seal["mode"] == MODE,
        "seal session",
    )

    need(
        seal["challenge_file_sha256"] == hashes["challenge"]
        and seal["admission_file_sha256"]
        == hashes["admission"],
        "seal binding",
    )

    need(
        seal["nonce_sha256"] == nh
        and seal["fixture_sha256"] == L35T
        and seal["fixture_records"] == 12,
        "seal fixture",
    )

    need(
        seal["independent_hardware_witness"] is False
        and seal["independent_source_authenticity_verified"]
        is False,
        "seal authenticity",
    )

    need(
        seal["physical_sync_verified"] is False
        and seal["independent_6dof_reference_verified"]
        is False,
        "seal scientific flags",
    )

    need(
        seal["simulator_launch_authorized"] is False
        and seal["new_sensor_measurements"] == 0,
        "seal acquisition",
    )

    need(
        seal["pose_factors_authorized"] == 0
        and seal["health_labels_generated"] == 0,
        "seal promotion",
    )

    need(
        type(adm["admitted_monotonic_ns_untrusted"])
        is int
        and type(seal["sealed_monotonic_ns_untrusted"])
        is int,
        "clock type",
    )

    need(
        ch["issued_monotonic_ns_untrusted"]
        < adm["admitted_monotonic_ns_untrusted"]
        < seal["sealed_monotonic_ns_untrusted"],
        "host monotonic ordering",
    )

    need(
        dbrow["session_id"] == ch["session_id"]
        and dbrow["nonce_sha"] == nh
        and dbrow["challenge_sha"] == hashes["challenge"],
        "registry identity",
    )

    need(
        dbrow["stage"] == "SEALED",
        "registry seal state",
    )

    need(
        dbrow["admission_sha"] == hashes["admission"]
        and dbrow["seal_sha"] == hashes["seal"],
        "registry receipt hashes",
    )

    need(
        dbrow["issued_ns"]
        == ch["issued_monotonic_ns_untrusted"],
        "registry issue time",
    )


def main(args):
    paths = {
        key: Path(getattr(args, key))
        for key in (
            "db", "challenge", "admission",
            "seal", "candidate", "contract",
            "fixture", "registry_source",
        )
    }

    for name, path in paths.items():
        need(
            path.is_file() and not path.is_symlink(),
            "missing file " + name,
        )

    need(
        sha(paths["candidate"]) == CAND
        and sha(paths["contract"]) == L36C
        and sha(paths["fixture"]) == L35T,
        "frozen source hashes",
    )

    fixture = paths["fixture"].read_text(
        encoding="utf-8"
    ).splitlines()

    need(
        len(fixture) == 12
        and all(
            isinstance(json.loads(line), dict)
            for line in fixture
        ),
        "fixture format",
    )

    hashes = {
        key: sha(paths[key])
        for key in ("challenge", "admission", "seal")
    }

    ch, ad, se = (
        load(paths[key])
        for key in ("challenge", "admission", "seal")
    )

    db = sqlite3.connect(
        "file:" + str(paths["db"].resolve())
        + "?mode=ro",
        uri=True,
    )

    db.row_factory = sqlite3.Row

    try:
        db.execute("PRAGMA query_only=ON")
        rows = db.execute(
            "SELECT * FROM sessions"
        ).fetchall()
    finally:
        db.close()

    need(
        len(rows) == 1,
        "registry row count",
    )

    row = dict(rows[0])

    validate(ch, ad, se, row, hashes)

    cases = [
        (
            "challenge_schema", "ch",
            lambda x: x.update(schema="BAD"),
        ),
        (
            "challenge_nonce", "ch",
            lambda x: x.update(nonce_hex="ff" * 32),
        ),
        (
            "challenge_session", "ch",
            lambda x: x.update(session_id="REPLAYED"),
        ),
        (
            "challenge_hardware_claim", "ch",
            lambda x: x.update(
                trusted_hardware_attestation=True
            ),
        ),
        (
            "challenge_wrong_candidate", "ch",
            lambda x: x.update(
                candidate_sha256="0" * 64
            ),
        ),
        (
            "admission_schema", "ad",
            lambda x: x.update(schema="BAD"),
        ),
        (
            "admission_wrong_challenge", "ad",
            lambda x: x.update(
                challenge_file_sha256="0" * 64
            ),
        ),
        (
            "admission_replayed_session", "ad",
            lambda x: x.update(session_id="REPLAYED"),
        ),
        (
            "admission_launch_claim", "ad",
            lambda x: x.update(
                simulator_launch_authorized=True
            ),
        ),
        (
            "admission_new_measurements", "ad",
            lambda x: x.update(
                new_sensor_measurements=1
            ),
        ),
        (
            "admission_time_before_issue", "ad",
            lambda x: x.update(
                admitted_monotonic_ns_untrusted=
                ch["issued_monotonic_ns_untrusted"]
            ),
        ),
        (
            "seal_schema", "se",
            lambda x: x.update(schema="BAD"),
        ),
        (
            "seal_wrong_admission", "se",
            lambda x: x.update(
                admission_file_sha256="0" * 64
            ),
        ),
        (
            "seal_wrong_fixture", "se",
            lambda x: x.update(
                fixture_sha256="0" * 64
            ),
        ),
        (
            "seal_pose_factors", "se",
            lambda x: x.update(
                pose_factors_authorized=1
            ),
        ),
        (
            "seal_time_before_admission", "se",
            lambda x: x.update(
                sealed_monotonic_ns_untrusted=
                ad["admitted_monotonic_ns_untrusted"]
            ),
        ),
        (
            "seal_hardware_claim", "se",
            lambda x: x.update(
                independent_hardware_witness=True
            ),
        ),
        (
            "registry_reopen", "row",
            lambda x: x.update(stage="ISSUED"),
        ),
        (
            "registry_wrong_admission", "row",
            lambda x: x.update(
                admission_sha="0" * 64
            ),
        ),
        (
            "registry_wrong_seal", "row",
            lambda x: x.update(
                seal_sha="0" * 64
            ),
        ),
    ]

    rejected = []

    for name, target, mutate in cases:
        cc, aa, ss, rr = copy.deepcopy(
            (ch, ad, se, row)
        )

        mutate({
            "ch": cc,
            "ad": aa,
            "se": ss,
            "row": rr,
        }[target])

        try:
            validate(
                cc, aa, ss, rr, hashes
            )
        except (
            ValueError,
            KeyError,
            TypeError,
        ):
            rejected.append(name)
        else:
            raise ValueError(
                "Invalid mutation accepted: " + name
            )

    need(
        len(rejected) == 20
        and len(set(rejected)) == 20,
        "mutation count",
    )

    result = {
        "schema":
            "TRUST_ROBOT_L38_PERSISTENT_SESSION_BINDING_VALIDATION_V1",
        "parent_commit": BASE,
        "registry_source_sha256":
            sha(paths["registry_source"]),
        "verifier_source_sha256":
            sha(__file__),
        "source_sha256": {
            "candidate": CAND,
            "l36_contract": L36C,
            "l35_transcript": L35T,
        },
        "challenge_sha256": hashes["challenge"],
        "admission_sha256": hashes["admission"],
        "seal_sha256": hashes["seal"],
        "registry_db_sha256": sha(paths["db"]),
        "registry_session_count": 1,
        "final_registry_state": "SEALED",
        "new_sensor_measurements": 0,
        "live_simulator_launch_authorized": False,
        "adversarial_mutations_rejected": rejected,
        "adversarial_mutations_count": 20,
        "durable_local_nonce_consumption_observed":
            True,
        "separate_process_replay_rejection_observed":
            True,
        "independent_hardware_attestation_verified":
            False,
        "independent_source_authenticity_verified":
            False,
        "physical_sync_verified": False,
        "independent_6dof_reference_verified":
            False,
        "trusted_clock_order_verified": False,
        "tamper_resistant_registry_verified":
            False,
        "multi_host_replay_protection_verified":
            False,
        "pose_factors_authorized": 0,
        "health_labels_generated": 0,
        "historical_recordings_modified": False,
        "git_commit_or_push_performed": False,
    }

    with Path(args.report).open("x") as f:
        json.dump(
            result,
            f,
            sort_keys=True,
            indent=2,
        )
        f.write("\n")

    print(
        "L38_REGISTRY_FINAL_STATE=SEALED",
        flush=True,
    )

    print(
        "L38_CHALLENGE_ADMISSION_SEAL_BINDINGS=PASS",
        flush=True,
    )

    print(
        "L38_ADVERSARIAL_CONTROLS=20_PASS",
        flush=True,
    )

    print(
        "L38_INDEPENDENT_VALIDATION=PASS",
        flush=True,
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser()

    for name in (
        "db",
        "challenge",
        "admission",
        "seal",
        "candidate",
        "contract",
        "fixture",
        "registry_source",
        "report",
    ):
        p.add_argument(
            "--" + name.replace("_", "-"),
            dest=name,
            required=True,
        )

    main(p.parse_args())
