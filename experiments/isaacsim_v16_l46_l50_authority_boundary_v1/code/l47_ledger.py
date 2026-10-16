"""L47 synthetic local nonce ledger and split-registry falsification.

No remote authority, real sensor origin, or physical witness is proven.
"""

import argparse
import concurrent.futures
import copy
import hashlib
import json
import secrets
import shutil
import sqlite3
import subprocess
import sys

from pathlib import Path

BASE = "c2e013f549b87e8646a8e51095a3372df0d09581"

CAND = (
    "4384b085f79dff51af5dbbf8a4c4bf4cae6deffc906bfbcaf8a8ef00a7e05dec"
)

L46_REPORT = (
    "183bf08ffdf467294027af058ab8e627bcec7d35192c612accff78735c1c7e40"
)

MODE = "OFFLINE_SINGLE_HOST_SYNTHETIC_NONCE_REPLAY_TEST"


def need(value, reason):
    if not value:
        raise ValueError(reason)


def canonical(obj):
    return (
        json.dumps(
            obj,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ) + "\n"
    ).encode()


def hashbytes(data):
    return hashlib.sha256(data).hexdigest()


def filehash(path):
    return hashbytes(Path(path).read_bytes())


def jsonsave(path, obj):
    with Path(path).open("x", encoding="utf-8") as stream:
        stream.write(
            json.dumps(
                obj,
                indent=2,
                sort_keys=True,
                allow_nan=False,
            ) + "\n"
        )


def safe_file(path):
    p = Path(path)

    need(
        p.is_file()
        and not p.is_symlink()
        and p.stat().st_nlink == 1,
        "UNSAFE_FILE",
    )

    return p


def request_validate(r, expected=None, tick=50):
    fields = {
        "schema",
        "session_id",
        "nonce_hex",
        "candidate_sha256",
        "l46_report_sha256",
        "parent_commit",
        "mode",
        "issuer_role",
        "not_before_tick",
        "deadline_tick",
        "source_origin_verified",
        "physical_sync_verified",
        "attestation_verified",
        "new_sensor_measurements",
        "pose_factors_authorized",
        "health_labels_generated",
    }

    need(
        type(r) is dict and set(r) == fields,
        "REQUEST_FIELDS",
    )

    need(
        r["schema"] == "TRUST_ROBOT_L47_TEST_REQUEST_V1",
        "REQUEST_SCHEMA",
    )

    need(
        type(r["session_id"]) is str
        and r["session_id"].startswith("L47_SYNTH_")
        and 15 <= len(r["session_id"]) <= 60,
        "SESSION_ID",
    )

    need(
        type(r["nonce_hex"]) is str
        and len(r["nonce_hex"]) == 64,
        "NONCE_LENGTH",
    )

    need(
        len(bytes.fromhex(r["nonce_hex"])) == 32,
        "NONCE_HEX",
    )

    if expected is not None:
        need(
            r["session_id"] == expected[0]
            and r["nonce_hex"] == expected[1],
            "REQUEST_IDENTITY",
        )

    need(
        r["candidate_sha256"] == CAND
        and r["l46_report_sha256"] == L46_REPORT,
        "SOURCE_BINDINGS",
    )

    need(
        r["parent_commit"] == BASE
        and r["mode"] == MODE
        and r["issuer_role"] == "UNTRUSTED_TEST_GENERATOR",
        "REQUEST_CONTEXT",
    )

    need(
        type(tick) is int
        and type(r["not_before_tick"]) is int
        and type(r["deadline_tick"]) is int
        and r["not_before_tick"] == 0
        and r["deadline_tick"] == 100
        and 0 <= tick <= 100,
        "UNTRUSTED_LOGICAL_TICK",
    )

    for key in (
        "source_origin_verified",
        "physical_sync_verified",
        "attestation_verified",
    ):
        need(
            r[key] is False,
            "FALSE_AUTHORITY_CLAIM:" + key,
        )

    for key in (
        "new_sensor_measurements",
        "pose_factors_authorized",
        "health_labels_generated",
    ):
        need(
            type(r[key]) is int and r[key] == 0,
            "FALSE_SCIENCE_CLAIM:" + key,
        )

    return True


def receipt_for(r):
    return {
        "schema": "TRUST_ROBOT_L47_LOCAL_ADMISSION_RECEIPT_V1",
        "session_id": r["session_id"],
        "nonce_sha256": hashbytes(
            bytes.fromhex(r["nonce_hex"])
        ),
        "request_sha256": hashbytes(canonical(r)),
        "candidate_sha256": CAND,
        "l46_report_sha256": L46_REPORT,
        "parent_commit": BASE,
        "decision": "LOCALLY_ADMITTED",
        "independent_physical_witness": False,
        "cross_host_replay_qualified": False,
        "new_sensor_measurements": 0,
        "pose_factors_authorized": 0,
        "health_labels_generated": 0,
    }


def dbconn(path, readonly=False):
    p = Path(path)

    if readonly:
        safe_file(p)

        c = sqlite3.connect(
            f"file:{p.resolve()}?mode=ro",
            uri=True,
            timeout=20,
        )

        c.execute("PRAGMA query_only=ON")

    else:
        need(
            p.is_file() and not p.is_symlink(),
            "NO_DATABASE",
        )

        c = sqlite3.connect(
            str(p),
            timeout=20,
            isolation_level=None,
        )

        c.execute("PRAGMA busy_timeout=20000")
        c.execute("PRAGMA synchronous=FULL")

    return c


def dbinit(path):
    p = Path(path)

    need(
        not p.exists() and not p.is_symlink(),
        "DB_EXISTS",
    )

    c = sqlite3.connect(str(p), timeout=20)

    try:
        c.execute("PRAGMA journal_mode=DELETE")
        c.execute("PRAGMA synchronous=FULL")

        c.execute(
            "CREATE TABLE admissions ("
            "nonce_hash TEXT PRIMARY KEY,"
            "session_id TEXT NOT NULL UNIQUE,"
            "request_digest TEXT NOT NULL,"
            "receipt BLOB NOT NULL,"
            "receipt_digest TEXT NOT NULL)"
        )

        c.commit()

    finally:
        c.close()


def admit(db, request_file):
    data = safe_file(request_file).read_bytes()
    r = json.loads(data)

    request_validate(r)

    need(
        data == canonical(r),
        "NONCANONICAL_REQUEST",
    )

    body = canonical(receipt_for(r))

    nonce_hash = hashbytes(
        bytes.fromhex(r["nonce_hex"])
    )

    c = dbconn(db)

    try:
        c.execute("BEGIN IMMEDIATE")

        need(
            c.execute(
                "PRAGMA quick_check"
            ).fetchone()[0] == "ok",
            "CORRUPT_DB",
        )

        seen = c.execute(
            "SELECT COUNT(*) FROM admissions "
            "WHERE nonce_hash=? OR session_id=?",
            (nonce_hash, r["session_id"]),
        ).fetchone()[0]

        need(
            seen == 0,
            "NONCE_OR_SESSION_ALREADY_CONSUMED",
        )

        c.execute(
            "INSERT INTO admissions VALUES(?,?,?,?,?)",
            (
                nonce_hash,
                r["session_id"],
                hashbytes(data),
                body,
                hashbytes(body),
            ),
        )

        c.commit()

    except BaseException:
        c.rollback()
        raise

    finally:
        c.close()


def audit(db, request_path, receipt_path):
    rfile = safe_file(request_path)
    output = safe_file(receipt_path)

    raw = rfile.read_bytes()
    r = json.loads(raw)

    request_validate(r)

    need(
        raw == canonical(r),
        "NONCANONICAL_REQUEST",
    )

    c = dbconn(db, readonly=True)

    try:
        need(
            c.execute(
                "PRAGMA quick_check"
            ).fetchone()[0] == "ok",
            "CORRUPT_DB",
        )

        rows = c.execute(
            "SELECT nonce_hash,session_id,request_digest,"
            "receipt,receipt_digest FROM admissions"
        ).fetchall()

    finally:
        c.close()

    need(
        len(rows) == 1,
        "ADMISSION_COUNT",
    )

    nonce_hash, sid, request_digest, payload, digest = rows[0]

    need(
        nonce_hash == hashbytes(
            bytes.fromhex(r["nonce_hex"])
        )
        and sid == r["session_id"]
        and request_digest == hashbytes(raw),
        "ADMISSION_IDENTITY",
    )

    need(
        type(payload) is bytes
        and payload == canonical(receipt_for(r))
        and digest == hashbytes(payload),
        "OUTBOX_RECEIPT_BINDING",
    )

    need(
        output.read_bytes() == payload,
        "EXPORTED_RECEIPT_MISMATCH",
    )

    return {
        "nonce_sha256": nonce_hash,
        "session_id": sid,
        "database_sha256": filehash(db),
        "receipt_sha256": filehash(receipt_path),
    }


def export(db, receipt_path):
    c = dbconn(db, readonly=True)

    try:
        rows = c.execute(
            "SELECT receipt FROM admissions"
        ).fetchall()

        need(
            len(rows) == 1,
            "EXPORT_COUNT",
        )

        body = rows[0][0]

    finally:
        c.close()

    with Path(receipt_path).open("xb") as stream:
        stream.write(body)


def process(command, *args):
    switches = {
        "admit": ("--db", "--request"),
        "export": ("--db", "--receipt"),
    }

    need(
        command in switches and len(args) == 2,
        "SUBPROCESS_ARGUMENTS",
    )

    commandline = [
        sys.executable,
        "-B",
        str(Path(__file__).resolve()),
        command,
    ]

    for flag, value in zip(switches[command], args):
        commandline.extend((flag, str(value)))

    return subprocess.run(
        commandline,
        capture_output=True,
        text=True,
        timeout=30,
    )


def invalid_requests(r):
    mutations = {
        "schema": "BAD",
        "session_id": "BAD",
        "nonce_hex": "0" * 64,
        "candidate_sha256": "1" * 64,
        "l46_report_sha256": "2" * 64,
        "parent_commit": "3" * 64,
        "mode": "WRONG",
        "issuer_role": "TRUSTED_ISSUER",
        "not_before_tick": 1,
        "deadline_tick": 101,
        "source_origin_verified": True,
        "physical_sync_verified": True,
        "attestation_verified": True,
        "new_sensor_measurements": 1,
        "pose_factors_authorized": 1,
        "health_labels_generated": 1,
    }

    out = []

    for key, value in mutations.items():
        m = copy.deepcopy(r)
        m[key] = value

        out.append(
            ("mutation_" + key, m, 50)
        )

    m = copy.deepcopy(r)
    m.pop("mode")
    out.append(("missing_mode", m, 50))

    m = copy.deepcopy(r)
    m["unexpected"] = 1
    out.append(("extra_field", m, 50))

    m = copy.deepcopy(r)
    m["nonce_hex"] = "nothex" * 10 + "abcd"
    out.append(("malformed_nonce", m, 50))

    out.append(
        ("expired_logical_tick", copy.deepcopy(r), 101)
    )

    need(
        len(out) == 20,
        "CONTROL_LIST",
    )

    return out


def run_exercise(
    out,
    contract_path,
    report_path,
    l46_contract,
    l46_report,
    l46_validation,
):
    c46 = json.loads(
        safe_file(l46_contract).read_text()
    )

    r46 = json.loads(
        safe_file(l46_report).read_text()
    )

    v46 = json.loads(
        safe_file(l46_validation).read_text()
    )

    need(
        c46["independent_physical_trust_established"] is False
        and r46["test_results"]["negative_controls_denied"] == 35
        and r46["test_results"][
            "independent_registry_clone_double_acceptance"
        ] is True
        and v46["shared_registry_qualified"] is False,
        "L46_LIMITATION_BINDING",
    )

    folder = Path(out) / "synthetic"

    need(
        not folder.exists(),
        "SYNTHETIC_OUTPUT_COLLISION",
    )

    folder.mkdir(mode=0o700)

    request = {
        "schema": "TRUST_ROBOT_L47_TEST_REQUEST_V1",
        "session_id": "L47_SYNTH_" + secrets.token_hex(12),
        "nonce_hex": secrets.token_hex(32),
        "candidate_sha256": CAND,
        "l46_report_sha256": L46_REPORT,
        "parent_commit": BASE,
        "mode": MODE,
        "issuer_role": "UNTRUSTED_TEST_GENERATOR",
        "not_before_tick": 0,
        "deadline_tick": 100,
        "source_origin_verified": False,
        "physical_sync_verified": False,
        "attestation_verified": False,
        "new_sensor_measurements": 0,
        "pose_factors_authorized": 0,
        "health_labels_generated": 0,
    }

    req = folder / "synthetic_request.json"

    with req.open("xb") as f:
        f.write(canonical(request))

    request_validate(request)

    controls = []

    for name, changed, tick in invalid_requests(request):
        try:
            request_validate(
                changed,
                expected=(
                    request["session_id"],
                    request["nonce_hex"],
                ),
                tick=tick,
            )

        except (
            ValueError,
            TypeError,
            KeyError,
        ):
            controls.append(name)

        else:
            raise AssertionError(
                "UNSAFE_REQUEST_ACCEPTED:" + name
            )

    need(
        len(controls) == 20,
        "CONTROL_COUNT",
    )

    central = folder / "central.sqlite"
    dbinit(central)

    # Eight separate processes compete for one nonce
    # within one shared single-host SQLite database.

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=8
    ) as pool:

        jobs = [
            pool.submit(
                process,
                "admit",
                central,
                req,
            )
            for _ in range(8)
        ]

        results = [
            job.result()
            for job in jobs
        ]

    wins = sum(
        x.returncode == 0
        for x in results
    )

    losses = sum(
        x.returncode == 3
        and "NONCE_OR_SESSION_ALREADY_CONSUMED" in x.stdout
        for x in results
    )

    need(
        wins == 1 and losses == 7,
        "CENTRAL_LEDGER_RACE",
    )

    receipt = folder / "central_receipt.json"

    need(
        process(
            "export",
            central,
            receipt,
        ).returncode == 0,
        "EXPORT_FAILURE",
    )

    main = audit(
        central,
        req,
        receipt,
    )

    # Two isolated databases deliberately admit
    # the same synthetic challenge.

    split = []

    for suffix in ("left", "right"):
        db = folder / (
            "split_" + suffix + ".sqlite"
        )

        dbinit(db)

        need(
            process(
                "admit",
                db,
                req,
            ).returncode == 0,
            "SPLIT_ADMIT_DENIED",
        )

        path = folder / (
            "split_" + suffix + "_receipt.json"
        )

        need(
            process(
                "export",
                db,
                path,
            ).returncode == 0,
            "SPLIT_EXPORT",
        )

        split.append(
            audit(db, req, path)
        )

    need(
        split[0]["nonce_sha256"]
        == split[1]["nonce_sha256"]
        == main["nonce_sha256"],
        "SPLIT_NONCE_IDENTITY",
    )

    need(
        split[0]["session_id"]
        == split[1]["session_id"],
        "SPLIT_SESSION",
    )

    fault_specs = [
        "receipt_missing",
        "receipt_altered",
        "db_receipt_payload",
        "db_receipt_digest",
        "db_nonce",
        "db_session",
        "db_request_digest",
        "db_row_deleted",
    ]

    for name in fault_specs:
        root = folder / (
            "fault_" + name
        )

        root.mkdir(mode=0o700)

        db = root / "ledger.sqlite"
        rec = root / "receipt.json"

        shutil.copyfile(central, db)
        shutil.copyfile(receipt, rec)

        if name == "receipt_missing":
            rec.unlink()

        elif name == "receipt_altered":
            rec.write_bytes(
                b"MALICIOUS\n"
            )

        else:
            c = sqlite3.connect(db)

            try:
                mutations = {
                    "db_receipt_payload": (
                        "UPDATE admissions SET receipt=?",
                        (b"FORGED",),
                    ),
                    "db_receipt_digest": (
                        "UPDATE admissions SET receipt_digest=?",
                        ("0" * 64,),
                    ),
                    "db_nonce": (
                        "UPDATE admissions SET nonce_hash=?",
                        ("1" * 64,),
                    ),
                    "db_session": (
                        "UPDATE admissions SET session_id=?",
                        ("L47_UNEXPECTED",),
                    ),
                    "db_request_digest": (
                        "UPDATE admissions SET request_digest=?",
                        ("2" * 64,),
                    ),
                    "db_row_deleted": (
                        "DELETE FROM admissions",
                        (),
                    ),
                }

                sql, params = mutations[name]

                c.execute(
                    sql,
                    params,
                )

                c.commit()

            finally:
                c.close()

        try:
            audit(
                db,
                req,
                rec,
            )

        except (
            ValueError,
            sqlite3.DatabaseError,
            OSError,
            KeyError,
            TypeError,
        ):
            pass

        else:
            raise AssertionError(
                "UNDETECTED_FAULT:" + name
            )

    contract = {
        "schema":
            "TRUST_ROBOT_L47_SINGLE_HOST_NONCE_AUTHORITY_CONTRACT_V1",
        "parent_commit": BASE,
        "engine_sha256": filehash(__file__),
        "l46_contract_sha256": filehash(l46_contract),
        "l46_report_sha256": filehash(l46_report),
        "l46_validation_sha256": filehash(l46_validation),
        "authority_scope":
            "ONE_SQLITE_FILE_ONE_HOST_NOT_CROSS_HOST",
        "issuer_independently_trusted": False,
        "quorum_or_distributed_consensus_implemented": False,
        "cross_host_replay_security_verified": False,
        "trusted_clock_established": False,
        "independent_sensor_provenance_established": False,
        "live_simulator_launch_authorized": False,
        "pose_factors_authorized": 0,
    }

    jsonsave(
        contract_path,
        contract,
    )

    report = {
        "schema":
            "TRUST_ROBOT_L47_SPLIT_REGISTRY_FALSIFICATION_V1",
        "contract_sha256": filehash(contract_path),
        "engine_sha256": filehash(__file__),
        "request_sha256": filehash(req),
        "central_single_host_successes": wins,
        "central_single_host_replays_denied": losses,
        "split_registry_same_nonce_admissions": len(split),
        "split_registry_detected_unsafe":
            "DUPLICATE_NONCE_REQUIRES_QUARANTINE",
        "globally_unique_admission_proven": False,
        "invalid_request_controls_rejected": controls,
        "invalid_request_control_count": 20,
        "faults_rejected": fault_specs,
        "fault_count": 8,
        "central": main,
        "split": split,
        "synthetic_request_issuer_trusted": False,
        "physical_source_authenticity_verified": False,
        "new_sensor_measurements": 0,
        "pose_factors_authorized": 0,
        "health_labels_generated": 0,
        "live_simulator_launch_authorized": False,
        "git_commit_or_push": False,
    }

    jsonsave(
        report_path,
        report,
    )

    print("L47_CENTRAL_SINGLE_HOST_NONCE_ADMISSIONS=1")
    print("L47_CENTRAL_SINGLE_HOST_REPLAYS=7_DENIED")
    print("L47_SPLIT_REGISTRY_DUPLICATE_ADMISSION=2_UNSAFE")
    print("L47_ADVERSARIAL_REQUEST_CONTROLS=20_DENIED")
    print("L47_LEDGER_AND_RECEIPT_FAULTS=8_DENIED")
    print("L47_OFFLINE_REPLAY_BOUNDARY=PASS")


def cli():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "action",
        choices=(
            "init",
            "admit",
            "export",
            "exercise",
        ),
    )

    for name in (
        "db",
        "request",
        "receipt",
        "out",
        "contract",
        "report",
        "l46-contract",
        "l46-report",
        "l46-validation",
    ):
        parser.add_argument(
            "--" + name
        )

    args = parser.parse_args()

    if args.action == "exercise":
        run_exercise(
            args.out,
            args.contract,
            args.report,
            args.l46_contract,
            args.l46_report,
            args.l46_validation,
        )
        return

    try:
        if args.action == "init":
            dbinit(args.db)

        elif args.action == "admit":
            admit(
                args.db,
                args.request,
            )
            print("L47_LOCAL_ADMISSION=PASS")

        elif args.action == "export":
            export(
                args.db,
                args.receipt,
            )

    except (
        ValueError,
        sqlite3.Error,
        OSError,
        TypeError,
        KeyError,
    ) as exc:
        print(
            "L47_FAIL_CLOSED=" + str(exc),
            flush=True,
        )
        raise SystemExit(3)


if __name__ == "__main__":
    cli()
