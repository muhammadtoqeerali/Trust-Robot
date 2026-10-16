"""L44 synthetic-only capture commit and receipt publication."""

import hashlib
import json
import os
import secrets
import sqlite3
from pathlib import Path

BASE = "8d5a1701df3e9d755ac0a4b5adda2845873f52eb"
CAND = "4384b085f79dff51af5dbbf8a4c4bf4cae6deffc906bfbcaf8a8ef00a7e05dec"
L43 = "aeb1af103fa04fd5b494997b20bb53debc3d2e82bf10bb5e2d95c6397ec1a213"

COUNTS = {"camera": 6, "lidar": 6, "imu": 130}
ORDER = ("camera", "lidar", "imu")
ZERO = "0" * 64
MODE = "SYNTHETIC_METADATA_NO_PHYSICAL_CAPTURE"


def need(test, why):
    if not test:
        raise ValueError(why)


def enc(obj):
    return (
        json.dumps(
            obj,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ) + "\n"
    ).encode()


def h(data):
    return hashlib.sha256(data).hexdigest()


def conn(path, create=False):
    p = Path(path)

    if not create:
        need(
            p.is_file() and not p.is_symlink(),
            "NO_DATABASE",
        )

    c = sqlite3.connect(
        str(p),
        timeout=10,
        isolation_level=None,
    )

    c.execute("PRAGMA journal_mode=DELETE")
    c.execute("PRAGMA synchronous=FULL")

    return c


def events_for(session, nonce, limit=142):
    rows = []
    tip = ZERO

    for sensor in ORDER:
        for counter in range(1, COUNTS[sensor] + 1):
            index = len(rows)

            row = {
                "schema": "L44_SYNTHETIC_EVENT_V1",
                "mode": MODE,
                "session_id": session,
                "nonce_sha256": nonce,
                "l43_manifest_sha256": L43,
                "candidate_sha256": CAND,
                "sensor": sensor,
                "counter": counter,
                "event_index": index,
                "read_tick_ns_untrusted": (index + 1) * 1000,
                "payload_sha256": h(
                    f"NOT_SENSOR_DATA:{session}:{sensor}:{counter}".encode()
                ),
                "previous_event_digest": tip,
            }

            row["event_digest"] = h(enc(row))
            tip = row["event_digest"]
            rows.append(row)

    return rows[:limit]


def assess(rows, session, nonce):
    counts = {x: 0 for x in ORDER}
    prior = ZERO
    order = -1

    try:
        need(
            type(rows) is list and len(rows) <= 142,
            "EVENT_COUNT",
        )

        expected_rows = events_for(
            session,
            nonce,
            len(rows),
        )

        for i, row in enumerate(rows):
            expected = expected_rows[i]

            need(
                type(row) is dict and row == expected,
                "EVENT_INTEGRITY_OR_SEQUENCE",
            )

            sensor = row["sensor"]
            k = ORDER.index(sensor)

            need(k >= order, "ORDER")
            order = k

            need(
                row["previous_event_digest"] == prior,
                "EVENT_CHAIN",
            )

            counts[sensor] += 1
            prior = row["event_digest"]

        need(
            all(counts[x] <= COUNTS[x] for x in ORDER),
            "EVENT_OVERRUN",
        )

    except (ValueError, TypeError, KeyError, IndexError):
        return "QUARANTINED", None

    return (
        "COMPLETE_SYNTHETIC"
        if counts == COUNTS
        else "REVIEW_REQUIRED"
    ), counts


def read(c):
    need(
        c.execute("PRAGMA quick_check").fetchone()[0] == "ok",
        "SQLITE_CORRUPT",
    )

    sessions = c.execute(
        "SELECT id,nonce,state FROM session"
    ).fetchall()

    need(len(sessions) == 1, "SESSION_COUNT")

    sid, nonce, state = sessions[0]

    data = c.execute(
        "SELECT pos,payload FROM events ORDER BY pos"
    ).fetchall()

    need(
        all(pos == i for i, (pos, _) in enumerate(data)),
        "EVENT_POSITIONS",
    )

    rows = [json.loads(payload) for _, payload in data]

    classification, counts = assess(
        rows,
        sid,
        nonce,
    )

    need(
        classification != "QUARANTINED",
        "BAD_EVENTS",
    )

    out = c.execute(
        "SELECT payload,digest,published FROM outbox"
    ).fetchall()

    need(
        len(out) == (0 if state == "RECORDING" else 1),
        "OUTBOX_COUNT",
    )

    if state != "RECORDING":
        blob, digest, published = out[0]

        need(
            type(blob) is bytes
            and h(blob) == digest
            and published in (0, 1),
            "OUTBOX_CORRUPT",
        )

        obj = json.loads(blob)

        need(
            blob == enc(obj),
            "OUTBOX_CANONICAL",
        )

        need(
            obj["schema"] == "L44_DECISION_RECEIPT_V1"
            and obj["decision"] == state == classification,
            "STATE_DECISION",
        )

        need(
            obj["session_id"] == sid
            and obj["nonce_sha256"] == nonce,
            "OUTBOX_SESSION",
        )

        need(
            obj["candidate_sha256"] == CAND
            and obj["l43_manifest_sha256"] == L43,
            "OUTBOX_SOURCE",
        )

        need(
            obj["event_count"] == len(rows)
            and obj["sensor_counts"] == counts,
            "OUTBOX_EVENT_COUNT",
        )

        need(
            obj["event_chain_tip"] ==
            (rows[-1]["event_digest"] if rows else ZERO),
            "OUTBOX_CHAIN",
        )

        need(
            obj["simulator_launch_authorized"] is False
            and obj["seal_authorized"] is False,
            "OUTBOX_PERMISSION",
        )

        need(
            obj["new_sensor_measurements"] == 0
            and obj["pose_factors_authorized"] == 0
            and obj["health_labels_generated"] == 0,
            "OUTBOX_SCIENCE",
        )

    return sid, nonce, state, rows, out


def create(db):
    need(
        not Path(db).exists(),
        "DATABASE_EXISTS",
    )

    c = conn(db, True)

    try:
        c.execute(
            "CREATE TABLE session("
            "id TEXT PRIMARY KEY,"
            "nonce TEXT NOT NULL,"
            "state TEXT NOT NULL)"
        )

        c.execute(
            "CREATE TABLE events("
            "pos INTEGER PRIMARY KEY,"
            "payload TEXT NOT NULL)"
        )

        c.execute(
            "CREATE TABLE outbox("
            "payload BLOB,"
            "digest TEXT,"
            "published INTEGER)"
        )

        sid = "KIOS_L44_" + secrets.token_hex(12)
        nonce = h(secrets.token_bytes(32))

        c.execute(
            "INSERT INTO session VALUES(?,?,?)",
            (sid, nonce, "RECORDING"),
        )

    finally:
        c.close()


def capture(db, n):
    c = conn(db)

    try:
        c.execute("BEGIN IMMEDIATE")

        sid, nonce, state, old, _ = read(c)

        need(
            state == "RECORDING"
            and len(old) == 0
            and 0 <= n <= 142,
            "CAPTURE_REENTRY",
        )

        for pos, row in enumerate(events_for(sid, nonce, n)):
            c.execute(
                "INSERT INTO events VALUES(?,?)",
                (pos, enc(row).decode()),
            )

        c.commit()

    except BaseException:
        c.rollback()
        raise

    finally:
        c.close()


def finalize(db):
    c = conn(db)

    try:
        c.execute("BEGIN IMMEDIATE")

        sid, nonce, state, rows, _ = read(c)

        need(
            state == "RECORDING",
            "ALREADY_FINALIZED",
        )

        classification, counts = assess(
            rows,
            sid,
            nonce,
        )

        need(
            classification in (
                "COMPLETE_SYNTHETIC",
                "REVIEW_REQUIRED",
            ),
            "INVALID_CAPTURE",
        )

        obj = {
            "schema": "L44_DECISION_RECEIPT_V1",
            "parent_commit": BASE,
            "session_id": sid,
            "nonce_sha256": nonce,
            "candidate_sha256": CAND,
            "l43_manifest_sha256": L43,
            "decision": classification,
            "sensor_counts": counts,
            "event_count": len(rows),
            "event_chain_tip": (
                rows[-1]["event_digest"] if rows else ZERO
            ),
            "simulator_launch_authorized": False,
            "seal_authorized": False,
            "physical_sync_verified": False,
            "new_sensor_measurements": 0,
            "pose_factors_authorized": 0,
            "health_labels_generated": 0,
        }

        body = enc(obj)

        updated = c.execute(
            "UPDATE session SET state=? "
            "WHERE id=? AND state=?",
            (classification, sid, "RECORDING"),
        )

        need(
            updated.rowcount == 1,
            "STATE_RACE",
        )

        c.execute(
            "INSERT INTO outbox VALUES(?,?,0)",
            (body, h(body)),
        )

        c.commit()

    except BaseException:
        c.rollback()
        raise

    finally:
        c.close()

    return classification


def publish(db, receipt):
    path = Path(receipt)

    need(
        path.parent.is_dir()
        and not path.parent.is_symlink(),
        "BAD_OUTPUT_DIRECTORY",
    )

    c = conn(db)

    try:
        sid, nonce, state, rows, out = read(c)

        need(
            state != "RECORDING",
            "UNCOMMITTED_DECISION",
        )

        body, digest, mark = out[0]

        if path.exists() or path.is_symlink():
            need(
                path.is_file()
                and not path.is_symlink()
                and h(path.read_bytes()) == digest,
                "CONFLICTING_RECEIPT",
            )

        else:
            need(
                mark == 0,
                "PUBLISHED_FILE_MISSING",
            )

            tmp = path.parent / (
                ".l44_tmp_" + secrets.token_hex(8)
            )

            fd = os.open(
                tmp,
                os.O_CREAT
                | os.O_EXCL
                | os.O_WRONLY
                | os.O_NOFOLLOW,
                0o600,
            )

            try:
                with os.fdopen(fd, "wb") as f:
                    f.write(body)
                    f.flush()
                    os.fsync(f.fileno())

                # No-replace publication.
                os.link(
                    tmp,
                    path,
                    follow_symlinks=False,
                )

                d = os.open(
                    path.parent,
                    os.O_RDONLY | os.O_DIRECTORY,
                )

                try:
                    os.fsync(d)
                finally:
                    os.close(d)

            finally:
                tmp.unlink(missing_ok=True)

        need(
            h(path.read_bytes()) == digest,
            "RECEIPT_HASH",
        )

        if mark == 0:
            c.execute("BEGIN IMMEDIATE")

            try:
                updated = c.execute(
                    "UPDATE outbox SET published=1 "
                    "WHERE published=0 AND digest=?",
                    (digest,),
                )

                need(
                    updated.rowcount == 1,
                    "PUBLICATION_RACE",
                )

                c.commit()

            except BaseException:
                c.rollback()
                raise

    finally:
        c.close()


def verify(db, receipt):
    c = conn(db)

    try:
        sid, nonce, state, rows, out = read(c)

        need(
            state != "RECORDING"
            and len(out) == 1,
            "NOT_FINAL",
        )

        body, digest, mark = out[0]
        path = Path(receipt)

        need(
            mark == 1
            and path.is_file()
            and not path.is_symlink()
            and h(path.read_bytes()) == digest,
            "MISSING_OR_TAMPERED_PUBLICATION",
        )

        need(
            path.read_bytes() == body,
            "RECEIPT_BYTES",
        )

        return state

    finally:
        c.close()


if __name__ == "__main__":
    import sys

    action, db = sys.argv[1:3]

    if action == "create":
        create(db)

    elif action == "capture":
        capture(db, int(sys.argv[3]))

    elif action == "finalize":
        print(finalize(db))

    elif action == "publish":
        publish(db, sys.argv[4])

    elif action == "verify":
        print(verify(db, sys.argv[4]))

    else:
        raise ValueError("BAD_ACTION")
