"""L35 prospective-order rehearsal using frozen L30 metadata.

No new camera, LiDAR, IMU or pose acquisition.
No physical timing, hardware attestation or estimator admission.
"""

import argparse
import hashlib
import json
import secrets
import time

from pathlib import Path

CONTRACT_SHA = (
    "24e71f94c8acfc3aa59184c49a811d62f54fc93d90178bbebef6c8239912467b"
)
EVENT_SHA = (
    "b28c333347ebb9c7262b636c355324b9abfa0b03beeb7c1af5a8b473a7144444"
)
L34_REPORT_SHA = (
    "49d1f4aed8e69ac5cc9ed8018a0340ab8e664cb94668f1e824cc7521b24ca010"
)

BASE = "2ac0a332bf6a5d749f5a75fe7d5a53572ea0e109"

MODE = "ARCHIVED_L30_METADATA_FIXTURE_NOT_NEW_ACQUISITION"


def need(value, message):
    if not value:
        raise ValueError(message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(
            lambda: stream.read(1048576),
            b"",
        ):
            h.update(block)
    return h.hexdigest()


def canonical(value):
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def write_json(path, value):
    with Path(path).open("x", encoding="utf-8") as f:
        f.write(
            json.dumps(
                value,
                indent=2,
                sort_keys=True,
                allow_nan=False,
            ) + "\n"
        )


def load_json(path):
    return json.loads(
        Path(path).read_text(encoding="utf-8")
    )


def check_challenge(path):
    obj = load_json(path)

    need(
        obj["schema"]
        == "TRUST_ROBOT_L35_ISSUER_CHALLENGE_V1",
        "Challenge schema",
    )
    need(obj["mode"] == MODE, "Challenge mode")
    need(
        len(bytes.fromhex(obj["nonce_hex"])) == 32,
        "Challenge nonce",
    )
    need(
        obj["contract_sha256"] == CONTRACT_SHA,
        "Challenge contract",
    )
    need(
        obj["trusted_hardware_attestation"] is False,
        "Hardware attestation claim",
    )
    need(
        obj["pose_factors_authorized"] == 0,
        "Pose factor claim",
    )

    return obj


def read_fixture(path):
    need(
        sha(path) == EVENT_SHA,
        "Frozen L30 event hash",
    )

    all_events = [
        json.loads(line)
        for line in Path(path).read_text(
            encoding="utf-8"
        ).splitlines()
    ]

    need(len(all_events) == 272, "L30 event count")

    selected = [
        e for e in all_events
        if e.get("sensor_modality") in (
            "camera", "lidar"
        )
    ]

    need(len(selected) == 12, "Fixture event count")

    expected = [
        f"{modality}:{i:03d}"
        for i in range(1, 7)
        for modality in ("camera", "lidar")
    ]

    need(
        [x["event_id"] for x in selected] == expected,
        "Fixture event ordering",
    )

    need(
        all(
            x["qualified_physical_exposure_time"]
            is False
            and x["pose_factor_authorized"]
            is False
            for x in selected
        ),
        "Fixture qualification",
    )

    return selected


def issue(args):
    need(
        sha(args.contract) == CONTRACT_SHA,
        "L33 contract hash",
    )
    need(
        sha(args.l34_report) == L34_REPORT_SHA,
        "L34 report hash",
    )

    obj = {
        "schema":
            "TRUST_ROBOT_L35_ISSUER_CHALLENGE_V1",
        "mode": MODE,
        "nonce_hex": secrets.token_hex(32),
        "issued_monotonic_ns_untrusted":
            time.monotonic_ns(),
        "contract_sha256": CONTRACT_SHA,
        "l34_report_sha256": L34_REPORT_SHA,
        "trusted_hardware_attestation": False,
        "pose_factors_authorized": 0,
    }

    write_json(args.output, obj)

    print("L35_PRE_REHEARSAL_CHALLENGE=ISSUED")


def record(args):
    challenge = check_challenge(args.challenge)

    need(
        sha(args.contract) == CONTRACT_SHA,
        "L33 contract",
    )

    challenge_sha = sha(args.challenge)
    start = time.monotonic_ns()

    need(
        challenge[
            "issued_monotonic_ns_untrusted"
        ] < start,
        "Challenge must precede recorder",
    )

    selected = read_fixture(args.events)

    prior = hashlib.sha256(
        ("L35_GENESIS_V1:" + challenge_sha).encode()
    ).hexdigest()

    records = []

    for number, source in enumerate(
        selected, start=1
    ):
        item = {
            "schema":
                "TRUST_ROBOT_L35_EMULATED_EVENT_V1",
            "ordinal": number,
            "source_event_id": source["event_id"],
            "source_run_id": source["run_id"],
            "source_payload_sha256":
                source["payload_sha256"],
            "source_file_sha256":
                source["source_file_sha256"],
            "source_l30_events_sha256": EVENT_SHA,
            "challenge_file_sha256": challenge_sha,
            "previous_record_sha256": prior,
            "local_record_monotonic_ns_untrusted":
                time.monotonic_ns(),
            "mode": MODE,
            "new_sensor_measurement": False,
            "physical_exposure_time_verified": False,
            "independent_source_authenticity_verified":
                False,
            "pose_factor_authorized": False,
        }

        item["record_sha256"] = hashlib.sha256(
            canonical(item)
        ).hexdigest()

        prior = item["record_sha256"]
        records.append(item)

    with Path(args.transcript).open(
        "x", encoding="utf-8"
    ) as stream:
        for item in records:
            stream.write(
                canonical(item).decode("utf-8") + "\n"
            )

    end = time.monotonic_ns()

    manifest = {
        "schema":
            "TRUST_ROBOT_L35_EMULATED_SESSION_V1",
        "mode": MODE,
        "parent_git_commit": BASE,
        "challenge_file_sha256": challenge_sha,
        "contract_sha256": CONTRACT_SHA,
        "source_l30_events_sha256": EVENT_SHA,
        "transcript_sha256":
            sha(args.transcript),
        "record_count": 12,
        "last_record_sha256": prior,
        "writer_start_monotonic_ns_untrusted": start,
        "writer_end_monotonic_ns_untrusted": end,
        "new_sensor_measurements": 0,
        "physical_sync_verified": False,
        "independent_source_authenticity_verified":
            False,
        "pose_factors_authorized": 0,
    }

    write_json(args.manifest, manifest)

    print("L35_EMULATED_RECORDS=12")
    print("L35_PRECHALLENGE_BINDING=RECORDED")


def seal(args):
    start = time.monotonic_ns()

    challenge = check_challenge(args.challenge)

    need(
        sha(args.events) == EVENT_SHA,
        "L30 fixture",
    )

    manifest = load_json(args.manifest)

    records = [
        json.loads(line)
        for line in Path(args.transcript)
        .read_text(encoding="utf-8")
        .splitlines()
    ]

    challenge_sha = sha(args.challenge)

    need(
        manifest["schema"]
        == "TRUST_ROBOT_L35_EMULATED_SESSION_V1",
        "Manifest schema",
    )
    need(
        manifest["challenge_file_sha256"]
        == challenge_sha,
        "Challenge binding",
    )
    need(
        manifest["source_l30_events_sha256"]
        == EVENT_SHA,
        "Fixture binding",
    )
    need(
        manifest["contract_sha256"]
        == CONTRACT_SHA,
        "Contract binding",
    )
    need(manifest["mode"] == MODE, "Mode")
    need(
        manifest["transcript_sha256"]
        == sha(args.transcript),
        "Transcript hash",
    )
    need(
        len(records) == manifest["record_count"] == 12,
        "Record count",
    )

    need(
        challenge["issued_monotonic_ns_untrusted"]
        < manifest["writer_start_monotonic_ns_untrusted"]
        <= manifest["writer_end_monotonic_ns_untrusted"]
        < start,
        "Rehearsal ordering",
    )

    need(
        manifest["new_sensor_measurements"] == 0
        and manifest["physical_sync_verified"] is False,
        "Scientific restrictions",
    )

    selected = read_fixture(args.events)

    prior = hashlib.sha256(
        ("L35_GENESIS_V1:" + challenge_sha).encode()
    ).hexdigest()

    for number, (item, source) in enumerate(
        zip(records, selected), start=1
    ):
        need(
            item["ordinal"] == number
            and item["source_event_id"]
            == source["event_id"],
            "Record ordinal",
        )

        need(
            item["source_payload_sha256"]
            == source["payload_sha256"],
            "Payload lineage",
        )

        need(
            item["source_file_sha256"]
            == source["source_file_sha256"],
            "Source-file lineage",
        )

        need(
            item["source_run_id"] == source["run_id"],
            "Source run",
        )

        need(
            item["previous_record_sha256"] == prior,
            "Hash chain",
        )

        need(
            item["challenge_file_sha256"]
            == challenge_sha,
            "Record challenge",
        )

        need(
            item["source_l30_events_sha256"]
            == EVENT_SHA,
            "Record fixture",
        )

        need(
            item["mode"] == MODE
            and item["new_sensor_measurement"]
            is False,
            "Fixture-only recording",
        )

        need(
            item["physical_exposure_time_verified"]
            is False
            and item[
                "independent_source_authenticity_verified"
            ] is False
            and item["pose_factor_authorized"] is False,
            "Invalid scientific claim",
        )

        need(
            manifest["writer_start_monotonic_ns_untrusted"]
            <= item["local_record_monotonic_ns_untrusted"]
            <= manifest["writer_end_monotonic_ns_untrusted"],
            "Event recording order",
        )

        unsigned = {
            key: value
            for key, value in item.items()
            if key != "record_sha256"
        }

        need(
            hashlib.sha256(
                canonical(unsigned)
            ).hexdigest()
            == item["record_sha256"],
            "Record hash",
        )

        prior = item["record_sha256"]

    need(
        manifest["last_record_sha256"] == prior,
        "Final chain hash",
    )

    receipt = {
        "schema":
            "TRUST_ROBOT_L35_POST_RECORD_SEAL_V1",
        "mode": MODE,
        "challenge_file_sha256": challenge_sha,
        "session_manifest_sha256":
            sha(args.manifest),
        "transcript_sha256":
            sha(args.transcript),
        "source_l30_events_sha256": EVENT_SHA,
        "last_record_sha256": prior,
        "record_count": 12,
        "witness_start_monotonic_ns_untrusted": start,
        "witness_end_monotonic_ns_untrusted":
            time.monotonic_ns(),
        "post_record_software_witness_only": True,
        "physical_exposure_sync_verified": False,
        "independent_source_authenticity_verified":
            False,
        "hardware_attestation_verified": False,
        "independent_6dof_reference_verified": False,
        "pose_factors_authorized": 0,
        "health_labels_generated": 0,
    }

    write_json(args.output, receipt)

    print("L35_SEAL_CHAIN_12_RECORDS=PASS")
    print(
        "L35_CHRONOLOGICAL_REHEARSAL="
        "PASS_UNTRUSTED_LOCAL_CLOCK"
    )


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--mode",
        choices=("issue", "record", "seal"),
        required=True,
    )

    for name in (
        "contract",
        "l34_report",
        "events",
        "challenge",
        "transcript",
        "manifest",
        "output",
    ):
        parser.add_argument(
            "--" + name.replace("_", "-"),
            dest=name,
        )

    args = parser.parse_args()

    required = {
        "issue": (
            "contract", "l34_report", "output"
        ),
        "record": (
            "contract", "events", "challenge",
            "transcript", "manifest"
        ),
        "seal": (
            "challenge", "events",
            "transcript", "manifest", "output"
        ),
    }

    need(
        all(
            getattr(args, name)
            for name in required[args.mode]
        ),
        "Missing arguments",
    )

    {
        "issue": issue,
        "record": record,
        "seal": seal,
    }[args.mode](args)


if __name__ == "__main__":
    main()
