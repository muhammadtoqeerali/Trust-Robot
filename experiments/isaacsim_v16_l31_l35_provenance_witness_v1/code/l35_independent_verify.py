"""Independent L35 offline rehearsal and adversarial verifier."""

import argparse
import copy
import hashlib
import json
import time

from pathlib import Path

BASE = "2ac0a332bf6a5d749f5a75fe7d5a53572ea0e109"

EVENT_SHA = (
    "b28c333347ebb9c7262b636c355324b9abfa0b03beeb7c1af5a8b473a7144444"
)
CONTRACT_SHA = (
    "24e71f94c8acfc3aa59184c49a811d62f54fc93d90178bbebef6c8239912467b"
)
L34_REPORT_SHA = (
    "49d1f4aed8e69ac5cc9ed8018a0340ab8e664cb94668f1e824cc7521b24ca010"
)

MODE = "ARCHIVED_L30_METADATA_FIXTURE_NOT_NEW_ACQUISITION"


def need(value, message):
    if not value:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(
        Path(path).read_bytes()
    ).hexdigest()


def canonical(value):
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def main(args):
    files = {
        "challenge": Path(args.challenge),
        "transcript": Path(args.transcript),
        "session_manifest": Path(args.manifest),
        "receipt": Path(args.receipt),
        "frozen_l30_events": Path(args.events),
        "contract": Path(args.contract),
        "l34_report": Path(args.l34_report),
    }

    for key, path in files.items():
        need(
            path.is_file() and not path.is_symlink(),
            "Missing input: " + key,
        )

    need(
        sha(files["frozen_l30_events"]) == EVENT_SHA,
        "Pinned L30 fixture",
    )
    need(
        sha(files["contract"]) == CONTRACT_SHA,
        "Pinned L33 contract",
    )
    need(
        sha(files["l34_report"]) == L34_REPORT_SHA,
        "Pinned L34 report",
    )

    challenge = json.loads(
        files["challenge"].read_text()
    )
    manifest = json.loads(
        files["session_manifest"].read_text()
    )
    receipt = json.loads(
        files["receipt"].read_text()
    )

    records = [
        json.loads(line)
        for line in files["transcript"]
        .read_text().splitlines()
    ]

    fixture = [
        json.loads(line)
        for line in files["frozen_l30_events"]
        .read_text().splitlines()
    ]

    need(len(fixture) == 272, "L30 fixture count")

    source = [
        e for e in fixture
        if e.get("sensor_modality") in (
            "camera", "lidar"
        )
    ]

    need(len(source) == 12, "Fixture count")

    expected_ids = [
        f"{modality}:{i:03d}"
        for i in range(1, 7)
        for modality in ("camera", "lidar")
    ]

    need(
        [e["event_id"] for e in source]
        == expected_ids,
        "Fixture identity sequence",
    )

    hashes = {
        key: sha(value)
        for key, value in files.items()
    }

    exact_bytes = b"".join(
        canonical(x) + b"\n"
        for x in records
    )

    need(
        hashlib.sha256(exact_bytes).hexdigest()
        == hashes["transcript"],
        "Canonical transcript",
    )

    now = time.monotonic_ns()

    row_fields = {
        "schema",
        "ordinal",
        "source_event_id",
        "source_run_id",
        "source_payload_sha256",
        "source_file_sha256",
        "source_l30_events_sha256",
        "challenge_file_sha256",
        "previous_record_sha256",
        "local_record_monotonic_ns_untrusted",
        "mode",
        "new_sensor_measurement",
        "physical_exposure_time_verified",
        "independent_source_authenticity_verified",
        "pose_factor_authorized",
        "record_sha256",
    }

    def validate(c, m, r, rows):
        need(
            c["schema"]
            == "TRUST_ROBOT_L35_ISSUER_CHALLENGE_V1",
            "Challenge schema",
        )
        need(
            c["mode"] == MODE
            and c["contract_sha256"] == CONTRACT_SHA
            and c["l34_report_sha256"]
            == L34_REPORT_SHA,
            "Challenge lineage",
        )
        need(
            len(bytes.fromhex(c["nonce_hex"])) == 32,
            "Challenge nonce",
        )
        need(
            c["trusted_hardware_attestation"]
            is False
            and c["pose_factors_authorized"] == 0,
            "Challenge qualification",
        )

        need(
            m["schema"]
            == "TRUST_ROBOT_L35_EMULATED_SESSION_V1"
            and m["mode"] == MODE,
            "Session schema",
        )
        need(
            m["parent_git_commit"] == BASE
            and m["contract_sha256"]
            == CONTRACT_SHA
            and m["source_l30_events_sha256"]
            == EVENT_SHA,
            "Session lineage",
        )
        need(
            m["challenge_file_sha256"]
            == hashes["challenge"],
            "Challenge binding",
        )
        need(
            m["record_count"] == len(rows) == 12,
            "Record count",
        )
        need(
            m["new_sensor_measurements"] == 0
            and m["physical_sync_verified"] is False
            and m["independent_source_authenticity_verified"]
            is False
            and m["pose_factors_authorized"] == 0,
            "Session scientific gate",
        )

        need(
            c["issued_monotonic_ns_untrusted"]
            < m["writer_start_monotonic_ns_untrusted"]
            <= m["writer_end_monotonic_ns_untrusted"]
            < r["witness_start_monotonic_ns_untrusted"]
            <= r["witness_end_monotonic_ns_untrusted"]
            <= now,
            "Software process ordering",
        )

        bytes_now = b"".join(
            canonical(x) + b"\n"
            for x in rows
        )

        need(
            hashlib.sha256(bytes_now).hexdigest()
            == m["transcript_sha256"],
            "Session transcript hash",
        )

        previous = hashlib.sha256(
            (
                "L35_GENESIS_V1:"
                + hashes["challenge"]
            ).encode()
        ).hexdigest()

        for index, (entry, original) in enumerate(
            zip(rows, source),
            start=1,
        ):
            need(
                set(entry) == row_fields,
                "Record schema",
            )
            need(
                entry["schema"]
                == "TRUST_ROBOT_L35_EMULATED_EVENT_V1"
                and entry["ordinal"] == index,
                "Record ordinal",
            )
            need(
                entry["source_event_id"]
                == original["event_id"]
                and entry["source_run_id"]
                == original["run_id"],
                "Fixture identity",
            )
            need(
                entry["source_payload_sha256"]
                == original["payload_sha256"]
                and entry["source_file_sha256"]
                == original["source_file_sha256"],
                "Fixture payload lineage",
            )
            need(
                entry["source_l30_events_sha256"]
                == EVENT_SHA
                and entry["challenge_file_sha256"]
                == hashes["challenge"],
                "Record source/challenge binding",
            )
            need(
                entry["previous_record_sha256"]
                == previous,
                "Previous record hash",
            )
            need(
                entry["mode"] == MODE
                and entry["new_sensor_measurement"]
                is False
                and entry["physical_exposure_time_verified"]
                is False
                and entry[
                    "independent_source_authenticity_verified"
                ] is False
                and entry["pose_factor_authorized"]
                is False,
                "Record scientific restrictions",
            )
            need(
                m["writer_start_monotonic_ns_untrusted"]
                <= entry[
                    "local_record_monotonic_ns_untrusted"
                ]
                <= m["writer_end_monotonic_ns_untrusted"],
                "Record local timestamp",
            )

            unsigned = {
                key: value
                for key, value in entry.items()
                if key != "record_sha256"
            }

            expected_hash = hashlib.sha256(
                canonical(unsigned)
            ).hexdigest()

            need(
                entry["record_sha256"]
                == expected_hash,
                "Record chain hash",
            )

            previous = entry["record_sha256"]

        need(
            m["last_record_sha256"] == previous,
            "Final session chain",
        )

        need(
            r["schema"]
            == "TRUST_ROBOT_L35_POST_RECORD_SEAL_V1"
            and r["mode"] == MODE,
            "Witness receipt schema",
        )
        need(
            r["challenge_file_sha256"]
            == hashes["challenge"]
            and r["session_manifest_sha256"]
            == hashes["session_manifest"]
            and r["transcript_sha256"]
            == hashes["transcript"],
            "Witness receipt binding",
        )
        need(
            r["source_l30_events_sha256"]
            == EVENT_SHA
            and r["last_record_sha256"]
            == previous
            and r["record_count"] == 12,
            "Witness chain binding",
        )
        need(
            r["post_record_software_witness_only"]
            is True,
            "Witness capability",
        )

        for field in (
            "physical_exposure_sync_verified",
            "independent_source_authenticity_verified",
            "hardware_attestation_verified",
            "independent_6dof_reference_verified",
        ):
            need(
                r[field] is False,
                "Receipt scientific gate: " + field,
            )

        need(
            r["pose_factors_authorized"] == 0
            and r["health_labels_generated"] == 0,
            "Estimator/health gate",
        )

    validate(
        challenge, manifest, receipt, records
    )

    cases = [
        ("challenge_nonce_corrupt", "c",
         lambda x: x.update(nonce_hex="bad")),
        ("challenge_false_hardware", "c",
         lambda x: x.update(
             trusted_hardware_attestation=True)),
        ("challenge_future_issued", "c",
         lambda x: x.update(
             issued_monotonic_ns_untrusted=now + 10**12)),
        ("wrong_writer_challenge", "m",
         lambda x: x.update(
             challenge_file_sha256="0" * 64)),
        ("wrong_contract", "m",
         lambda x: x.update(
             contract_sha256="0" * 64)),
        ("false_new_acquisition", "m",
         lambda x: x.update(
             new_sensor_measurements=12)),
        ("false_sync_claim", "m",
         lambda x: x.update(
             physical_sync_verified=True)),
        ("early_writer", "m",
         lambda x: x.update(
             writer_start_monotonic_ns_untrusted=0)),
        ("wrong_session_transcript_hash", "m",
         lambda x: x.update(
             transcript_sha256="0" * 64)),
        ("wrong_session_count", "m",
         lambda x: x.update(record_count=11)),
        ("lost_record", "e",
         lambda x: x.pop()),
        ("swapped_records", "e",
         lambda x: x.__setitem__(
             slice(0, 2), [x[1], x[0]])),
        ("fake_record_payload", "e",
         lambda x: x[0].update(
             source_payload_sha256="0" * 64)),
        ("duplicate_record_identity", "e",
         lambda x: x[1].update(
             source_event_id=x[0]["source_event_id"])),
        ("record_chain_edited", "e",
         lambda x: x[1].update(
             previous_record_sha256="0" * 64)),
        ("fake_event_new_sensor", "e",
         lambda x: x[0].update(
             new_sensor_measurement=True)),
        ("fake_event_exposure", "e",
         lambda x: x[0].update(
             physical_exposure_time_verified=True)),
        ("fake_event_pose_factor", "e",
         lambda x: x[0].update(
             pose_factor_authorized=True)),
        ("record_future_clock", "e",
         lambda x: x[0].update(
             local_record_monotonic_ns_untrusted=
             now + 10**12)),
        ("receipt_false_hardware", "r",
         lambda x: x.update(
             hardware_attestation_verified=True)),
        ("receipt_false_reference", "r",
         lambda x: x.update(
             independent_6dof_reference_verified=True)),
        ("receipt_wrong_transcript", "r",
         lambda x: x.update(
             transcript_sha256="1" * 64)),
        ("receipt_wrong_chain_end", "r",
         lambda x: x.update(
             last_record_sha256="1" * 64)),
        ("receipt_early_witness", "r",
         lambda x: x.update(
             witness_start_monotonic_ns_untrusted=0)),
        ("receipt_pose_factor", "r",
         lambda x: x.update(
             pose_factors_authorized=1)),
    ]

    rejected = []

    for name, kind, change in cases:
        cc, mm, rr, ee = copy.deepcopy(
            (challenge, manifest, receipt, records)
        )

        target = {
            "c": cc,
            "m": mm,
            "r": rr,
            "e": ee,
        }[kind]

        change(target)

        try:
            validate(cc, mm, rr, ee)
        except (
            ValueError,
            KeyError,
            TypeError,
            IndexError,
        ):
            rejected.append(name)
        else:
            raise ValueError(
                "Accepted invalid mutation: " + name
            )

    need(
        len(rejected) == 25,
        "Adversarial control count",
    )

    report = {
        "schema":
            "TRUST_ROBOT_L35_PROSPECTIVE_ORDER_REHEARSAL_VALIDATION_V1",
        "parent_commit": BASE,
        "workflow_source_sha256":
            sha(args.workflow_source),
        "verifier_source_sha256":
            sha(__file__),
        "challenge_sha256":
            hashes["challenge"],
        "session_manifest_sha256":
            hashes["session_manifest"],
        "transcript_sha256":
            hashes["transcript"],
        "witness_receipt_sha256":
            hashes["receipt"],
        "l33_contract_sha256":
            CONTRACT_SHA,
        "l34_validation_sha256":
            L34_REPORT_SHA,
        "frozen_l30_events_sha256":
            EVENT_SHA,
        "fixture_source_records": 12,
        "rehearsed_new_sensor_measurements": 0,
        "software_order_verified": True,
        "software_order_is_trusted_physical_time":
            False,
        "independent_source_authenticity_verified":
            False,
        "physical_exposure_sync_verified": False,
        "hardware_attestation_verified": False,
        "independent_6dof_reference_verified":
            False,
        "health_labels_generated": 0,
        "pose_factors_authorized": 0,
        "negative_controls_rejected": rejected,
        "negative_controls_count": len(rejected),
        "new_isaacsim_capture_performed": False,
        "prior_recordings_modified": False,
        "github_commit_or_push_performed": False,
        "next":
            "L36_PROSPECTIVE_WITNESS_INTEGRATION_DESIGN_OR_MILESTONE_ARCHIVE",
    }

    with Path(args.output).open(
        "x", encoding="utf-8"
    ) as stream:
        stream.write(
            json.dumps(
                report,
                indent=2,
                sort_keys=True,
                allow_nan=False,
            ) + "\n"
        )

    print("L35_REHEARSAL_ORDER_AND_HASH_CHAIN=PASS")
    print("L35_INDEPENDENT_ADVERSARIAL_CONTROLS=25_PASS")
    print("L35_SCIENTIFIC_GATES=DENIED")
    print("L35_OFFLINE_PROSPECTIVE_REHEARSAL=PASS")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    for name in (
        "workflow_source",
        "challenge",
        "transcript",
        "manifest",
        "receipt",
        "events",
        "contract",
        "l34_report",
        "output",
    ):
        parser.add_argument(
            "--" + name.replace("_", "-"),
            dest=name,
            required=True,
        )

    main(parser.parse_args())
