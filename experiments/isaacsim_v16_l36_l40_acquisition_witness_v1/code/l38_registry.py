"""L38 persistent local challenge registry; offline fixture only."""

import argparse
import hashlib
import json
import secrets
import sqlite3
import sys
import time

from pathlib import Path

BASE = "0b542e8644f3c4b98ed92c0f83a7c82a4635ae52"
CAND = "4384b085f79dff51af5dbbf8a4c4bf4cae6deffc906bfbcaf8a8ef00a7e05dec"
L36C = "ee8dfaa3a0f95813d29efa68f65a3222a39cce5e12cf855c4c3508791dcc05f9"
L35T = "b2fa0728d1aa867d162bae7e463f7bf353b058222d2700eaf392cd271ed97736"

MODE = "OFFLINE_L35_FIXTURE_NO_SENSOR_ACQUISITION"


def need(value, why):
    if not value:
        raise ValueError(why)


def sha(path):
    return hashlib.sha256(
        Path(path).read_bytes()
    ).hexdigest()


def serial(obj):
    return (
        json.dumps(
            obj,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        ) + "\n"
    ).encode()


def load(path):
    return json.loads(
        Path(path).read_text(encoding="utf-8")
    )


def write(path, obj):
    with Path(path).open("xb") as f:
        f.write(serial(obj))


def connect(path):
    db = sqlite3.connect(
        str(path),
        timeout=10,
        isolation_level=None,
    )
    db.execute("PRAGMA synchronous=FULL")
    db.execute("PRAGMA busy_timeout=10000")
    return db


def challenge_check(ch):
    need(
        ch["schema"] ==
        "TRUST_ROBOT_L38_LOCAL_CHALLENGE_V1",
        "challenge schema",
    )

    need(
        ch["parent_commit"] == BASE
        and ch["mode"] == MODE,
        "challenge lineage",
    )

    need(
        ch["candidate_sha256"] == CAND
        and ch["l36_contract_sha256"] == L36C
        and ch["l35_transcript_sha256"] == L35T,
        "challenge source binding",
    )

    need(
        ch["trusted_hardware_attestation"] is False
        and ch["physical_time_verified"] is False,
        "overclaim",
    )

    need(
        isinstance(ch["session_id"], str)
        and ch["session_id"].startswith("KIOS_L38_")
        and len(ch["session_id"]) == 33,
        "session identity",
    )

    nonce = ch["nonce_hex"]

    need(
        type(nonce) is str
        and len(nonce) == 64
        and all(c in "0123456789abcdef" for c in nonce),
        "nonce encoding",
    )

    need(
        type(ch["issued_monotonic_ns_untrusted"]) is int
        and ch["issued_monotonic_ns_untrusted"] > 0,
        "clock",
    )

    return hashlib.sha256(
        bytes.fromhex(nonce)
    ).hexdigest()


def issue(a):
    need(
        sha(a.candidate) == CAND
        and sha(a.contract) == L36C
        and sha(a.fixture) == L35T,
        "frozen source hash",
    )

    ch = {
        "schema":
            "TRUST_ROBOT_L38_LOCAL_CHALLENGE_V1",
        "parent_commit": BASE,
        "mode": MODE,
        "session_id":
            "KIOS_L38_" + secrets.token_hex(12),
        "nonce_hex": secrets.token_hex(32),
        "issued_monotonic_ns_untrusted":
            time.monotonic_ns(),
        "candidate_sha256": CAND,
        "l36_contract_sha256": L36C,
        "l35_transcript_sha256": L35T,
        "trusted_hardware_attestation": False,
        "physical_time_verified": False,
    }

    nonce_hash = challenge_check(ch)

    challenge_hash = hashlib.sha256(
        serial(ch)
    ).hexdigest()

    need(
        not Path(a.db).exists()
        and not Path(a.challenge).exists(),
        "Output collision",
    )

    db = connect(a.db)

    try:
        db.execute(
            """
            CREATE TABLE sessions (
                session_id TEXT PRIMARY KEY,
                nonce_sha TEXT UNIQUE NOT NULL,
                challenge_sha TEXT NOT NULL,
                stage TEXT NOT NULL CHECK(
                    stage IN ('ISSUED','ADMITTED','SEALED')
                ),
                admission_sha TEXT,
                seal_sha TEXT,
                issued_ns INTEGER NOT NULL
            )
            """
        )

        db.execute("BEGIN IMMEDIATE")

        db.execute(
            "INSERT INTO sessions VALUES(?,?,?,?,?,?,?)",
            (
                ch["session_id"],
                nonce_hash,
                challenge_hash,
                "ISSUED",
                None,
                None,
                ch["issued_monotonic_ns_untrusted"],
            ),
        )

        db.commit()
    finally:
        db.close()

    write(a.challenge, ch)

    print("L38_CHALLENGE_ISSUED=PASS", flush=True)


def admit(a):
    need(
        sha(a.candidate) == CAND
        and sha(a.contract) == L36C
        and sha(a.fixture) == L35T,
        "frozen source hash",
    )

    ch = load(a.challenge)
    nonce_hash = challenge_check(ch)
    challenge_hash = sha(a.challenge)

    now = time.monotonic_ns()

    need(
        0 < now - ch["issued_monotonic_ns_untrusted"]
        < 300_000_000_000,
        "expired or future local challenge",
    )

    db = connect(a.db)

    try:
        db.execute("BEGIN IMMEDIATE")

        row = db.execute(
            """
            SELECT nonce_sha, challenge_sha, stage
            FROM sessions WHERE session_id=?
            """,
            (ch["session_id"],),
        ).fetchone()

        need(row is not None, "unknown session")

        need(
            row[0] == nonce_hash
            and row[1] == challenge_hash,
            "challenge registry mismatch",
        )

        need(
            row[2] == "ISSUED",
            "NONCE_ALREADY_CONSUMED",
        )

        receipt = {
            "schema":
                "TRUST_ROBOT_L38_OFFLINE_ADMISSION_V1",
            "session_id": ch["session_id"],
            "mode": MODE,
            "challenge_file_sha256": challenge_hash,
            "nonce_sha256": nonce_hash,
            "candidate_sha256": CAND,
            "l36_contract_sha256": L36C,
            "l35_transcript_sha256": L35T,
            "admitted_monotonic_ns_untrusted": now,
            "offline_admission": True,
            "simulator_launch_authorized": False,
            "new_sensor_measurements": 0,
            "independent_source_authenticity_verified":
                False,
            "physical_sync_verified": False,
            "pose_factors_authorized": 0,
        }

        digest = hashlib.sha256(
            serial(receipt)
        ).hexdigest()

        cur = db.execute(
            """
            UPDATE sessions
            SET stage=?, admission_sha=?
            WHERE session_id=? AND stage=?
            """,
            (
                "ADMITTED",
                digest,
                ch["session_id"],
                "ISSUED",
            ),
        )

        need(
            cur.rowcount == 1,
            "atomic nonce consume failed",
        )

        db.commit()

    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()

    # Persisted consumption precedes publication of
    # this receipt. A crash here fails closed on retry.
    write(a.admission, receipt)

    print("L38_NONCE_DURABLY_CONSUMED=PASS", flush=True)
    print(
        "L38_OFFLINE_PREFLIGHT="
        "PASS_LIVE_LAUNCH_DENIED",
        flush=True,
    )


def seal(a):
    ch = load(a.challenge)
    rec = load(a.admission)

    nonce_hash = challenge_check(ch)
    challenge_hash = sha(a.challenge)

    need(
        rec["schema"] ==
        "TRUST_ROBOT_L38_OFFLINE_ADMISSION_V1"
        and rec["session_id"] == ch["session_id"],
        "admission schema",
    )

    need(
        rec["challenge_file_sha256"] == challenge_hash
        and rec["nonce_sha256"] == nonce_hash,
        "admission binding",
    )

    need(
        rec["candidate_sha256"] == CAND
        and rec["l36_contract_sha256"] == L36C
        and rec["l35_transcript_sha256"] == L35T,
        "admission lineage",
    )

    need(
        rec["simulator_launch_authorized"] is False
        and rec["new_sensor_measurements"] == 0
        and rec["pose_factors_authorized"] == 0,
        "admission safety",
    )

    need(
        sha(a.fixture) == L35T,
        "fixture hash",
    )

    lines = Path(a.fixture).read_text(
        encoding="utf-8"
    ).splitlines()

    need(
        len(lines) == 12
        and all(
            isinstance(json.loads(s), dict)
            for s in lines
        ),
        "fixture count",
    )

    now = time.monotonic_ns()

    need(
        ch["issued_monotonic_ns_untrusted"]
        < rec["admitted_monotonic_ns_untrusted"]
        < now,
        "local event order",
    )

    receipt = {
        "schema":
            "TRUST_ROBOT_L38_LOCAL_SEAL_V1",
        "session_id": ch["session_id"],
        "mode": MODE,
        "challenge_file_sha256": challenge_hash,
        "admission_file_sha256": sha(a.admission),
        "nonce_sha256": nonce_hash,
        "fixture_sha256": L35T,
        "fixture_records": 12,
        "sealed_monotonic_ns_untrusted": now,
        "independent_hardware_witness": False,
        "independent_source_authenticity_verified":
            False,
        "physical_sync_verified": False,
        "independent_6dof_reference_verified":
            False,
        "new_sensor_measurements": 0,
        "simulator_launch_authorized": False,
        "pose_factors_authorized": 0,
        "health_labels_generated": 0,
    }

    digest = hashlib.sha256(
        serial(receipt)
    ).hexdigest()

    db = connect(a.db)

    try:
        db.execute("BEGIN IMMEDIATE")

        row = db.execute(
            """
            SELECT stage, admission_sha
            FROM sessions WHERE session_id=?
            """,
            (ch["session_id"],),
        ).fetchone()

        need(
            row == ("ADMITTED", sha(a.admission)),
            "admission registry mismatch",
        )

        cur = db.execute(
            """
            UPDATE sessions
            SET stage=?, seal_sha=?
            WHERE session_id=? AND stage=?
            """,
            (
                "SEALED",
                digest,
                ch["session_id"],
                "ADMITTED",
            ),
        )

        need(
            cur.rowcount == 1,
            "atomic seal failure",
        )

        db.commit()

    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()

    write(a.seal, receipt)

    print(
        "L38_OFFLINE_SEAL_RECEIPT=PASS",
        flush=True,
    )


def main():
    p = argparse.ArgumentParser()

    p.add_argument(
        "action",
        choices=("issue", "admit", "seal"),
    )

    for name in (
        "db",
        "challenge",
        "candidate",
        "contract",
        "fixture",
        "admission",
        "seal",
    ):
        p.add_argument("--" + name)

    a = p.parse_args()

    required = {
        "issue": (
            "db", "challenge", "candidate",
            "contract", "fixture",
        ),
        "admit": (
            "db", "challenge", "candidate",
            "contract", "fixture", "admission",
        ),
        "seal": (
            "db", "challenge", "admission",
            "fixture", "seal",
        ),
    }

    need(
        all(
            getattr(a, key)
            for key in required[a.action]
        ),
        "missing arguments",
    )

    try:
        {
            "issue": issue,
            "admit": admit,
            "seal": seal,
        }[a.action](a)

    except ValueError as error:
        if (
            a.action == "admit"
            and str(error) == "NONCE_ALREADY_CONSUMED"
        ):
            print(
                "L38_REPLAY_DENIED="
                "NONCE_ALREADY_CONSUMED",
                flush=True,
            )
            sys.exit(3)
        raise


if __name__ == "__main__":
    main()
