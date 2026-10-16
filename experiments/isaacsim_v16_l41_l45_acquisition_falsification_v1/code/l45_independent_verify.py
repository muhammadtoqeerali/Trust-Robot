"""Independent L45 falsification and frozen-baseline verifier."""

import argparse
import hashlib
import importlib.util
import json
import sqlite3
from pathlib import Path


def sha(path):
    return hashlib.sha256(
        Path(path).read_bytes()
    ).hexdigest()


def need(value, why):
    if not value:
        raise AssertionError(why)


def module(path):
    spec = importlib.util.spec_from_file_location(
        "l44_for_l45_independent", path
    )
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


def main(a):
    b = module(a.core)

    contract = json.loads(
        Path(a.contract).read_text()
    )
    report = json.loads(
        Path(a.report).read_text()
    )

    need(
        contract["schema"]
        == "TRUST_ROBOT_L45_COHERENT_FORGERY_BOUNDARY_CONTRACT_V1",
        "CONTRACT_SCHEMA",
    )

    need(
        contract["assessment_source_sha256"]
        == sha(a.engine),
        "ENGINE_SOURCE",
    )
    need(
        contract["independent_verifier_sha256"]
        == sha(__file__),
        "VERIFIER_SOURCE",
    )
    need(
        contract["l44_core_sha256"] == sha(a.core),
        "L44_SOURCE",
    )
    need(
        contract["l44_report_sha256"]
        == sha(a.l44report),
        "L44_REPORT",
    )

    need(
        contract["actual_external_trusted_witness"]
        is False
        and contract["actual_source_authenticity_verified"]
        is False,
        "CONTRACT_AUTHENTICITY",
    )

    need(
        contract["live_simulator_launch_authorized"]
        is False
        and contract["scientific_pose_factors"] == 0,
        "CONTRACT_PERMISSION",
    )

    need(
        report["schema"]
        == "TRUST_ROBOT_L45_COHERENT_FORGERY_FALSIFICATION_REPORT_V1",
        "REPORT_SCHEMA",
    )

    need(
        report["contract_sha256"] == sha(a.contract),
        "CONTRACT_DIGEST",
    )

    prior = json.loads(
        Path(a.l44report).read_text()
    )
    original = next(
        x for x in prior["case_results"]
        if x["case"] == 0
    )

    need(
        sha(a.db)
        == original["database_sha256"]
        == report["baseline_database_sha256"],
        "ORIGINAL_DB",
    )

    need(
        sha(a.receipt)
        == original["receipt_sha256"]
        == report["baseline_receipt_sha256"],
        "ORIGINAL_RECEIPT",
    )

    db = sqlite3.connect(
        "file:" + str(Path(a.db).resolve()) + "?mode=ro",
        uri=True,
    )

    try:
        db.execute("PRAGMA query_only=ON")

        sid, nonce, state = db.execute(
            "SELECT id,nonce,state FROM session"
        ).fetchone()

        rows = [
            json.loads(x[0])
            for x in db.execute(
                "SELECT payload FROM events ORDER BY pos"
            )
        ]

    finally:
        db.close()

    need(
        state == "COMPLETE_SYNTHETIC"
        and b.assess(rows, sid, nonce)[0] == state,
        "BASELINE_EVENTS",
    )

    tip = rows[-1]["event_digest"]

    need(
        tip == report["original_session_tip_sha256"],
        "BASELINE_TIP",
    )

    derived = []

    for category in (
        "session_only",
        "nonce_only",
        "both",
    ):
        for i in range(4):
            tag = category + "_" + str(i)

            alternate_sid = (
                sid + "_L45_" + tag
                if category != "nonce_only"
                else sid
            )

            alternate_nonce = (
                hashlib.sha256(
                    (sid + nonce + tag).encode()
                ).hexdigest()
                if category != "session_only"
                else nonce
            )

            alternative = b.events_for(
                alternate_sid,
                alternate_nonce,
            )

            decision, counts = b.assess(
                alternative,
                alternate_sid,
                alternate_nonce,
            )

            need(
                decision == "COMPLETE_SYNTHETIC"
                and counts == b.COUNTS,
                "COHERENT_NOT_ACCEPTED",
            )

            need(
                alternative[-1]["event_digest"] != tip,
                "COHERENT_ROOT_EQUAL",
            )

            derived.append({
                "scenario": tag,
                "internal_l44_decision": decision,
                "original_session_pin_matches":
                    alternate_sid == sid,
                "original_nonce_pin_matches":
                    alternate_nonce == nonce,
                "original_event_tip_pin_matches":
                    False,
                "trusted_source_authenticity_verified":
                    False,
            })

    need(
        report["coherent_rekey_cases"] == derived
        and report["coherent_rekey_count"] == 12,
        "COHERENT_CASES",
    )

    need(
        report["coherent_cases_internally_accepted"]
        == 12
        and report["coherent_cases_with_trusted_provenance"]
        == 0,
        "COHERENT_INTERPRETATION",
    )

    independent_mutations = []

    for pos in (0, 6, 12, 129, 141):
        for field in (
            "session_id",
            "event_index",
            "payload_sha256",
            "event_digest",
        ):
            modified = [
                x.copy() for x in rows
            ]

            modified[pos][field] = (
                -1
                if type(modified[pos][field]) is int
                else "ALTERED_WITHOUT_REHASH"
            )

            need(
                b.assess(
                    modified, sid, nonce
                )[0] == "QUARANTINED",
                "MUTATION_ACCEPTED",
            )

            independent_mutations.append(
                f"{pos}:{field}"
            )

    need(
        independent_mutations
        == report["incoherent_event_mutations_rejected"]
        and report["incoherent_rejection_count"] == 20,
        "MUTATIONS",
    )

    root = Path(a.scenarios)

    generated_db = (
        root /
        "coherent_local_generation/session.sqlite"
    )
    generated_receipt = (
        root /
        "coherent_local_generation/decision.json"
    )

    forged = report["new_local_fabricated_session"]

    need(
        sha(generated_db)
        == forged["database_sha256"]
        and sha(generated_receipt)
        == forged["receipt_sha256"],
        "GENERATED_DIGEST",
    )

    need(
        b.verify(
            generated_db,
            generated_receipt,
        ) == "COMPLETE_SYNTHETIC"
        == forged["internal_l44_result"],
        "GENERATED_INTERNAL",
    )

    need(
        forged["real_sensor_measurements"] == 0
        and forged["independent_capture_witness"]
        is False,
        "GENERATED_AUTHENTICITY",
    )

    for name in (
        "rename_before_publication_mark",
        "committed_outbox_missing_file",
    ):
        folder = root / name

        need(
            b.verify(
                folder / "session.sqlite",
                folder / "decision.json",
            ) == "COMPLETE_SYNTHETIC",
            "RECOVERY_INVALID",
        )

        need(
            sha(folder / "decision.json")
            == original["receipt_sha256"],
            "RECOVERY_CONTENT",
        )

    need(
        report["recovery_cases"] == [
            "rename_before_publication_mark",
            "committed_outbox_missing_file",
        ]
        and report["recovery_count"] == 2,
        "RECOVERY_CASES",
    )

    faults = [
        "receipt_missing",
        "receipt_corrupted",
        "cross_session_receipt",
        "database_corrupted",
        "outbox_deleted",
        "outbox_payload_changed",
        "outbox_digest_changed",
        "outbox_published_invalid",
        "session_nonce_changed",
        "session_id_changed",
        "final_event_deleted",
        "event_position_gap",
    ]

    need(
        report["fault_cases"] == faults
        and report["faults_rejected_count"] == 12,
        "FAULT_LIST",
    )

    for name in faults:
        folder = root / ("fault_" + name)

        try:
            b.verify(
                folder / "session.sqlite",
                folder / "decision.json",
            )

        except (
            ValueError,
            sqlite3.DatabaseError,
            KeyError,
            TypeError,
            OSError,
        ):
            pass

        else:
            raise AssertionError(
                "INDEPENDENT_FAULT_ACCEPTED_" + name
            )

    for field in (
        "actual_sensor_acquisition_binding",
        "independent_source_authenticity_verified",
        "trusted_physical_timing_verified",
        "hardware_attestation_verified",
        "real_power_failure_tested",
        "live_simulator_launch_authorized",
        "git_commit_or_push",
    ):
        need(
            report[field] is False,
            "FALSE_CLAIM_" + field,
        )

    for field in (
        "new_sensor_measurements",
        "pose_factors_authorized",
        "health_labels_generated",
    ):
        need(
            report[field] == 0,
            "SCIENTIFIC_" + field,
        )

    validation = {
        "schema":
            "TRUST_ROBOT_L45_INDEPENDENT_VALIDATION_V1",
        "assessment_sha256": sha(a.engine),
        "verifier_sha256": sha(__file__),
        "contract_sha256": sha(a.contract),
        "report_sha256": sha(a.report),
        "frozen_l44_database_sha256": sha(a.db),
        "frozen_l44_receipt_sha256": sha(a.receipt),
        "verified_coherent_internal_acceptances": 12,
        "verified_coherent_trusted_provenance": 0,
        "verified_incoherent_rejections": 20,
        "verified_recoveries": 2,
        "verified_fault_denials": 12,
        "physical_source_authenticity_verified": False,
        "live_simulator_launch_authorized": False,
        "new_sensor_measurements": 0,
        "pose_factors_authorized": 0,
        "health_labels_generated": 0,
    }

    with Path(a.validation).open(
        "x", encoding="utf-8"
    ) as f:
        json.dump(
            validation,
            f,
            sort_keys=True,
            indent=2,
        )
        f.write("\n")

    print(
        "L45_INDEPENDENT_COHERENT_CASES=12_UNTRUSTED"
    )
    print(
        "L45_INDEPENDENT_INCOHERENT_MUTATIONS=20_DENIED"
    )
    print(
        "L45_INDEPENDENT_RECOVERY_CASES=2_PASS"
    )
    print(
        "L45_INDEPENDENT_DATABASE_FAULTS=12_DENIED"
    )
    print(
        "L45_INDEPENDENT_VALIDATION=PASS"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    for name in (
        "core",
        "engine",
        "l44report",
        "db",
        "receipt",
        "contract",
        "report",
        "scenarios",
        "validation",
    ):
        parser.add_argument(
            "--" + name,
            required=True,
        )

    main(parser.parse_args())
