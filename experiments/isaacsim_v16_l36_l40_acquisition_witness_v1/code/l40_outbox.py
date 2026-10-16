"""L40 software-only SQLite outbox and fail-closed receipt publication.

Receipts are stored as byte-exact BLOBs in the same transaction
as each session transition. Pending files may be published from
those bytes, but inconsistent existing files are never overwritten.

No physical power-loss, tamper resistance or hardware guarantees.
"""

import argparse
import hashlib
import json
import os
import secrets
import sqlite3
import sys
from pathlib import Path

BASE = "0b542e8644f3c4b98ed92c0f83a7c82a4635ae52"

PINS = {
    "candidate":
        "4384b085f79dff51af5dbbf8a4c4bf4cae6deffc906bfbcaf8a8ef00a7e05dec",
    "contract":
        "ee8dfaa3a0f95813d29efa68f65a3222a39cce5e12cf855c4c3508791dcc05f9",
    "fixture":
        "b2fa0728d1aa867d162bae7e463f7bf353b058222d2700eaf392cd271ed97736",
}

MODE = "OFFLINE_FIXTURE_NO_NEW_SENSOR_MEASUREMENTS"

NAMES = [
    "challenge_v1.json",
    "admission_v1.json",
    "seal_v1.json",
]

STATES = ["ISSUED", "ADMITTED", "SEALED"]


def need(ok, message):
    if not ok:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def filehash(path):
    return sha(Path(path).read_bytes())


def serial(obj):
    return (
        json.dumps(
            obj, indent=2, sort_keys=True,
            allow_nan=False
        ) + "\n"
    ).encode()


def parse(data):
    return json.loads(data.decode("utf-8"))


def dbopen(path):
    con = sqlite3.connect(
        str(path), timeout=10, isolation_level=None
    )
    con.execute("PRAGMA journal_mode=DELETE")
    con.execute("PRAGMA synchronous=FULL")
    con.execute("PRAGMA busy_timeout=10000")
    return con


def fetch(con):
    need(
        con.execute("PRAGMA quick_check").fetchone()[0]
        == "ok",
        "DB_CORRUPT",
    )

    sessions = con.execute(
        "SELECT session_id,nonce_hash,state FROM sessions"
    ).fetchall()

    need(len(sessions) == 1, "SESSION_COUNT")

    session = sessions[0]

    rows = con.execute(
        """
        SELECT stage,payload,digest,published
        FROM outbox ORDER BY stage
        """
    ).fetchall()

    need(
        len(rows) == STATES.index(session[2]) + 1,
        "OUTBOX_STAGE_COUNT",
    )
    need(
        [x[0] for x in rows] == list(range(len(rows))),
        "OUTBOX_GAP",
    )

    for stage, body, digest, published in rows:
        need(
            isinstance(body, bytes) and sha(body) == digest,
            "OUTBOX_DIGEST_MISMATCH",
        )
        need(published in (0, 1), "BAD_PUBLICATION_FLAG")
        need(
            body == serial(parse(body)),
            "NONCANONICAL_RECEIPT",
        )

        obj = parse(body)

        need(
            obj["stage"] == STATES[stage]
            and obj["session_id"] == session[0]
            and obj["mode"] == MODE,
            "OUTBOX_IDENTITY",
        )
        need(
            obj["parent_commit"] == BASE
            and obj["candidate_sha256"] == PINS["candidate"]
            and obj["contract_sha256"] == PINS["contract"]
            and obj["fixture_sha256"] == PINS["fixture"],
            "OUTBOX_SOURCE_BINDING",
        )
        need(
            obj["new_sensor_measurements"] == 0
            and obj["simulator_launch_authorized"] is False
            and obj["physical_sync_verified"] is False
            and obj["pose_factors_authorized"] == 0
            and obj["health_labels_generated"] == 0,
            "OUTBOX_UNSUPPORTED_CLAIM",
        )

        if stage == 0:
            need(
                obj["nonce_hash"] == session[1]
                and len(bytes.fromhex(obj["nonce_hex"])) == 32,
                "NONCE_IDENTITY",
            )
        else:
            need(
                obj["nonce_hash"] == session[1]
                and obj["prior_receipt_sha256"]
                == rows[stage - 1][2],
                "CHAIN_BINDING",
            )

    return session, rows


def add(con, stage, obj):
    body = serial(obj)
    con.execute(
        """
        INSERT INTO outbox(stage,payload,digest,published)
        VALUES(?,?,?,0)
        """,
        (stage, body, sha(body)),
    )


def existing(path, digest):
    need(
        path.is_file() and not path.is_symlink(),
        "RECEIPT_MISSING_OR_SYMLINKED",
    )
    need(
        filehash(path) == digest,
        "RECEIPT_HASH_MISMATCH",
    )


def published(rows, folder):
    for stage, _, digest, pub in rows:
        if pub:
            existing(folder / NAMES[stage], digest)


def publish(con, folder):
    _, rows = fetch(con)

    # Preflight all existing receipt files before changing any.
    for stage, _, digest, pub in rows:
        path = folder / NAMES[stage]
        if path.exists() or path.is_symlink():
            existing(path, digest)
        elif pub:
            raise ValueError("PUBLISHED_RECEIPT_MISSING")

    for stage, body, digest, pub in rows:
        path = folder / NAMES[stage]

        if not path.exists():
            temp = folder / (
                ".l40_pending_"
                + str(stage)
                + "_"
                + secrets.token_hex(8)
            )

            fd = os.open(
                temp,
                os.O_CREAT | os.O_EXCL
                | os.O_WRONLY | os.O_NOFOLLOW,
                0o600,
            )

            try:
                with os.fdopen(fd, "wb") as stream:
                    stream.write(body)
                    stream.flush()
                    os.fsync(stream.fileno())

                os.replace(temp, path)

                directory_fd = os.open(
                    folder,
                    os.O_RDONLY | os.O_DIRECTORY,
                )
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)

            finally:
                if temp.exists():
                    temp.unlink()

            existing(path, digest)

        if not pub:
            con.execute("BEGIN IMMEDIATE")
            try:
                cursor = con.execute(
                    """
                    UPDATE outbox SET published=1
                    WHERE stage=? AND published=0 AND digest=?
                    """,
                    (stage, digest),
                )
                need(
                    cursor.rowcount == 1,
                    "PUBLICATION_RACE",
                )
                con.commit()
            except BaseException:
                con.rollback()
                raise

    print(
        "L40_RECEIPTS_PUBLISHED_OR_RECONCILED="
        + str(len(rows)),
        flush=True,
    )


def main(args):
    for key, digest in PINS.items():
        path = Path(getattr(args, key))
        need(
            path.is_file()
            and not path.is_symlink()
            and filehash(path) == digest,
            "PINNED_" + key,
        )

    db = Path(args.db)
    folder = Path(args.receipts)

    need(
        folder.is_dir() and not folder.is_symlink(),
        "RECEIPT_DIR",
    )
    need(not db.is_symlink(), "DB_SYMLINK")

    if args.action == "issue":
        need(not db.exists(), "DB_EXISTS")
        con = dbopen(db)

        try:
            con.execute(
                """
                CREATE TABLE sessions (
                    session_id TEXT PRIMARY KEY,
                    nonce_hash TEXT UNIQUE NOT NULL,
                    state TEXT NOT NULL
                )
                """
            )
            con.execute(
                """
                CREATE TABLE outbox (
                    stage INTEGER PRIMARY KEY
                        CHECK(stage IN (0,1,2)),
                    payload BLOB NOT NULL,
                    digest TEXT NOT NULL,
                    published INTEGER NOT NULL
                        CHECK(published IN (0,1))
                )
                """
            )

            nonce = secrets.token_hex(32)
            identity = "KIOS_L40_" + secrets.token_hex(12)

            obj = {
                "schema": "TRUST_ROBOT_L40_RECEIPT_V1",
                "stage": "ISSUED",
                "session_id": identity,
                "mode": MODE,
                "parent_commit": BASE,
                "nonce_hex": nonce,
                "nonce_hash": sha(bytes.fromhex(nonce)),
                "candidate_sha256": PINS["candidate"],
                "contract_sha256": PINS["contract"],
                "fixture_sha256": PINS["fixture"],
                "new_sensor_measurements": 0,
                "simulator_launch_authorized": False,
                "physical_sync_verified": False,
                "pose_factors_authorized": 0,
                "health_labels_generated": 0,
            }

            con.execute("BEGIN IMMEDIATE")
            try:
                con.execute(
                    "INSERT INTO sessions VALUES(?,?,?)",
                    (identity, obj["nonce_hash"], "ISSUED"),
                )
                add(con, 0, obj)
                con.commit()
            except BaseException:
                con.rollback()
                raise

            print(
                "L40_ISSUE_STATE_COMMITTED_BEFORE_PUBLICATION=PASS",
                flush=True,
            )
        finally:
            con.close()
        return

    need(db.is_file(), "DB_MISSING")

    con = dbopen(db)
    try:
        session, rows = fetch(con)
        published(rows, folder)

        if args.action == "publish":
            publish(con, folder)
            return

        if args.action == "status":
            need(
                all(x[3] == 1 for x in rows),
                "PENDING_PUBLICATIONS",
            )
            print(
                "L40_FINAL_STATE=" + session[2],
                flush=True,
            )
            return

        required = (
            "ISSUED" if args.action == "admit"
            else "ADMITTED"
        )

        need(
            session[2] == required,
            "NONCE_OR_SESSION_ALREADY_CONSUMED",
        )
        need(
            all(x[3] == 1 for x in rows),
            "PREVIOUS_RECEIPT_NOT_PUBLISHED",
        )

        stage = 1 if args.action == "admit" else 2

        obj = {
            "schema": "TRUST_ROBOT_L40_RECEIPT_V1",
            "stage": STATES[stage],
            "session_id": session[0],
            "mode": MODE,
            "parent_commit": BASE,
            "nonce_hash": session[1],
            "prior_receipt_sha256": rows[-1][2],
            "candidate_sha256": PINS["candidate"],
            "contract_sha256": PINS["contract"],
            "fixture_sha256": PINS["fixture"],
            "new_sensor_measurements": 0,
            "simulator_launch_authorized": False,
            "physical_sync_verified": False,
            "pose_factors_authorized": 0,
            "health_labels_generated": 0,
        }

        con.execute("BEGIN IMMEDIATE")
        try:
            cursor = con.execute(
                """
                UPDATE sessions SET state=?
                WHERE session_id=? AND state=?
                """,
                (STATES[stage], session[0], required),
            )

            need(
                cursor.rowcount == 1,
                "ATOMIC_TRANSITION_DENIED",
            )

            add(con, stage, obj)
            con.commit()

        except BaseException:
            con.rollback()
            raise

        print(
            "L40_" + STATES[stage]
            + "_COMMITTED_WITH_OUTBOX=PASS",
            flush=True,
        )
    finally:
        con.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "action",
        choices=("issue", "admit", "seal", "publish", "status"),
    )

    for name in (
        "db", "receipts", "candidate",
        "contract", "fixture"
    ):
        parser.add_argument("--" + name, required=True)

    args = parser.parse_args()

    try:
        main(args)
    except (
        ValueError,
        sqlite3.Error,
        OSError,
        KeyError,
        TypeError,
    ) as error:
        print(
            "L40_FAIL_CLOSED="
            + type(error).__name__
            + ":" + str(error),
            flush=True,
        )
        sys.exit(3)
