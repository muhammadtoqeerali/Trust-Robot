"""L33 prospective TRUST-ROBOT acquisition-evidence protocol.

Engineering protocol design only. Neither hashes nor self-reported
attestation fields qualify physical provenance or synchronization.
"""

import argparse
import collections
import copy
import hashlib
import json
from pathlib import Path

BASE = "2ac0a332bf6a5d749f5a75fe7d5a53572ea0e109"
STEPS = (51, 61, 71, 81, 91, 101)

COUNTS = {
    "camera": 6,
    "lidar": 6,
    "imu": 130,
    "usd_pose": 130,
}

def need(ok, message):
    if not ok:
        raise ValueError(message)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load(path):
    return json.loads(path.read_text(encoding="utf-8"))

def save(path, obj):
    need(not path.exists(), "Output already exists")
    path.write_text(
        json.dumps(
            obj, indent=2, sort_keys=True, allow_nan=False
        ) + "\n",
        encoding="utf-8",
    )

def expected_ids():
    result = []
    for step in range(1, 131):
        result += [
            f"imu:{step:03d}",
            f"usd_pose:{step:03d}",
        ]
        if step in STEPS:
            n = STEPS.index(step) + 1
            result += [
                f"camera:{n:03d}",
                f"lidar:{n:03d}",
            ]
    return result

def validate_l30(events):
    need(len(events) == 272, "Event count")
    need(
        [x["event_id"] for x in events] == expected_ids(),
        "Event identity, order or sequence",
    )

    counts = collections.Counter()

    for e in events:
        modality, index = e["event_id"].split(":")
        number = int(index)

        need(
            e["run_id"] == "KIOS_L29_INSTRUMENTED_RUNTIME_V1",
            "Run identity",
        )
        need(e["pose_factor_authorized"] is False, "Pose admission")
        need(
            e["sensor_health_label_authorized"] is False,
            "Health admission",
        )
        need(
            e["qualified_physical_exposure_time"] is False,
            "Physical timing claim",
        )
        need(
            e["independent_source_authenticity_verified"] is False,
            "Authenticity claim",
        )

        for field in ("payload_sha256", "source_file_sha256"):
            digest = e[field]
            need(
                isinstance(digest, str)
                and len(digest) == 64
                and all(c in "0123456789abcdef" for c in digest),
                "Digest format",
            )

        if modality == "usd_pose":
            need(e["kind"] == "scripted_reference", "Reference kind")
            need(
                e["independent_reference_verified"] is False,
                "Independent reference claim",
            )
            need(
                e["orientation_quaternion_wxyz"] is None,
                "Unverified orientation",
            )
            need(e["reference_uncertainty"] is None, "Reference uncertainty")
            need(
                e["reference_clock_domain"] == "SCRIPTED_SIM_STEP_SECONDS",
                "Reference clock",
            )
            need(e["source_row_1based"] == number, "Reference row")
        else:
            need(e["kind"] == "sensor", "Sensor kind")
            need(e["sensor_modality"] == modality, "Sensor modality")
            need(e["sequence_number"] == number, "Sensor sequence")
            need(
                e["exposure_time_definition"] is None,
                "Unqualified exposure semantics",
            )
            need(e["calibration_version"] is None, "Calibration claim")
            need(
                e["provenance_attestation_reference"] is None,
                "Attestation claim",
            )

            if modality == "camera":
                need(e["sensor_timestamp_raw"] is None, "Camera timestamp")
                need(e["sensor_clock_domain"] is None, "Camera clock")
            elif modality == "lidar":
                need(
                    e["sensor_clock_domain"] == "GMO_TIMESTAMP_NS_UNQUALIFIED",
                    "LiDAR clock",
                )
            elif modality == "imu":
                need(
                    e["sensor_clock_domain"] == "IMU_REPORTED_CLOCK_UNQUALIFIED",
                    "IMU clock",
                )
                need(e["source_row_1based"] == number, "IMU row")

        counts[modality] += 1

    need(dict(counts) == COUNTS, "Modality totals")
    return dict(counts)

def challenges(events):
    def select(rows, modality):
        return next(
            x for x in rows
            if x["event_id"].startswith(modality + ":")
        )

    cases = [
        ("missing_event", lambda e: e.pop()),
        ("duplicate_id", lambda e: e[1].update(event_id=e[0]["event_id"])),
        ("event_reorder", lambda e: e.reverse()),
        ("foreign_run", lambda e: e[0].update(run_id="FOREIGN")),
        ("invalid_payload_sha", lambda e: e[0].update(payload_sha256="bad")),
        ("invalid_source_sha", lambda e: e[0].update(source_file_sha256="bad")),
        ("forged_authenticity", lambda e: e[0].update(
            independent_source_authenticity_verified=True)),
        ("forged_exposure", lambda e: e[0].update(
            qualified_physical_exposure_time=True)),
        ("forged_factor", lambda e: e[0].update(pose_factor_authorized=True)),
        ("forged_health", lambda e: e[0].update(
            sensor_health_label_authorized=True)),
        ("wrong_sequence", lambda e: e[0].update(sequence_number=999)),
        ("wrong_imu_clock", lambda e: e[0].update(
            sensor_clock_domain="VERIFIED_CLOCK")),
        ("fake_exposure_definition", lambda e: e[0].update(
            exposure_time_definition="hardware_verified")),
        ("fake_calibration", lambda e: e[0].update(
            calibration_version="verified")),
        ("fake_attestation", lambda e: e[0].update(
            provenance_attestation_reference="self_reported")),
        ("fake_camera_time", lambda e: select(e, "camera").update(
            sensor_timestamp_raw=1.0)),
        ("fake_lidar_clock", lambda e: select(e, "lidar").update(
            sensor_clock_domain="QUALIFIED")),
        ("fake_reference", lambda e: select(e, "usd_pose").update(
            independent_reference_verified=True)),
        ("fake_orientation", lambda e: select(e, "usd_pose").update(
            orientation_quaternion_wxyz=[1, 0, 0, 0])),
        ("fake_reference_uncertainty", lambda e: select(e, "usd_pose").update(
            reference_uncertainty={"sigma": 0.001})),
    ]

    rejected = []

    for name, change in cases:
        trial = copy.deepcopy(events)
        change(trial)
        try:
            validate_l30(trial)
        except (ValueError, KeyError, TypeError, IndexError):
            rejected.append(name)
        else:
            raise ValueError("Challenge accepted: " + name)

    need(len(rejected) == len(cases), "Challenge count")
    return rejected

def main(args):
    archive = Path(args.archive).resolve(strict=True)
    l31path = Path(args.l31).resolve(strict=True)
    l32path = Path(args.l32).resolve(strict=True)
    contract_out = Path(args.contract)
    report_out = Path(args.report)

    event_path = archive / "evidence/l30_fresh_runtime_events_v1.jsonl"
    manifest_path = archive / "evidence/l30_fresh_runtime_manifest_v1.json"
    l27path = archive / "evidence/l27_acquisition_contract_v1.json"

    pinned = {
        "l31": (l31path, "4a54a1ece6b5a6fcab6c61001983fb9c69f0be8cf9a4928dade3c28d5846a24b"),
        "l32": (l32path, "949eaa79cf967a4c910dd54e69c5c03194a68aaa819137c415124cdcacbc9585"),
        "l30_events": (event_path, "b28c333347ebb9c7262b636c355324b9abfa0b03beeb7c1af5a8b473a7144444"),
        "l30_manifest": (manifest_path, "cd202b19dd86a1b00871c2ec55690cab30898b7120906d064390009363138d80"),
        "l27_contract": (l27path, "7078da5e5c9ba0db5052f2ecb8d02544379b4d70cb319a3d7cab3e6a8fd52931"),
    }

    for key, (path, expected) in pinned.items():
        need(path.is_file() and not path.is_symlink(), key)
        need(sha(path) == expected, "Pinned input mismatch " + key)

    l31 = load(l31path)
    l32 = load(l32path)
    l27 = load(l27path)
    manifest = load(manifest_path)
    events = [
        json.loads(line)
        for line in event_path.read_text(encoding="utf-8").splitlines()
    ]

    counts = validate_l30(events)
    rejected = challenges(events)

    need(l31["event_counts"] == COUNTS, "L31 counts")
    need(l31["unique_raw_source_files_verified"] == 14, "L31 sources")
    need(l32["source_file_pairs_verified"] == 14, "L32 file pairs")
    need(l32["events_verified_each_run"] == 272, "L32 events")
    need(
        l32["coherent_in_memory_rehash_challenge"][
            "unsigned_envelope_file_manifest_hash_self_consistent"
        ] is True,
        "L32 hash falsification",
    )
    need(manifest["event_file_sha256"] == sha(event_path), "L30 binding")
    need(manifest["source_authenticity_verified"] is False, "L30 authenticity")
    need(manifest["qualified_exposure_sync"] is False, "L30 exposure")
    need(manifest["independent_reference"] is False, "L30 reference")

    overlap = {}
    for modality, expected in (
        ("camera", 0), ("lidar", 6),
        ("imu", 130), ("usd_pose", 130)
    ):
        value = l32["cross_run"][modality]
        need(
            value["identical_payload_sha256"] == expected,
            "Cross-run fingerprint mismatch",
        )
        need(value["same_device_inode"] == 0, "Source inode overlap")
        overlap[modality] = {
            "identical_payloads": expected,
            "total": COUNTS[modality],
            "same_inode": 0,
        }

    sensor = [e for e in events if e["kind"] == "sensor"]
    pose = [e for e in events if e["kind"] == "scripted_reference"]

    need(len(sensor) == 142 and len(pose) == 130, "Event types")

    gaps = {
        "sensor_exposure_definition_missing": sum(
            e["exposure_time_definition"] is None for e in sensor
        ),
        "sensor_calibration_version_missing": sum(
            e["calibration_version"] is None for e in sensor
        ),
        "sensor_independent_attestation_missing": sum(
            e["provenance_attestation_reference"] is None for e in sensor
        ),
        "camera_measurement_timestamp_missing": sum(
            e["sensor_timestamp_raw"] is None
            for e in sensor if e["sensor_modality"] == "camera"
        ),
        "reference_orientation_missing": sum(
            e["orientation_quaternion_wxyz"] is None for e in pose
        ),
        "reference_uncertainty_missing": sum(
            e["reference_uncertainty"] is None for e in pose
        ),
        "source_authenticity_unverified": sum(
            e["independent_source_authenticity_verified"] is False
            for e in events
        ),
        "physical_exposure_unqualified": sum(
            e["qualified_physical_exposure_time"] is False
            for e in events
        ),
    }

    need(gaps == {
        "sensor_exposure_definition_missing": 142,
        "sensor_calibration_version_missing": 142,
        "sensor_independent_attestation_missing": 142,
        "camera_measurement_timestamp_missing": 6,
        "reference_orientation_missing": 130,
        "reference_uncertainty_missing": 130,
        "source_authenticity_unverified": 272,
        "physical_exposure_unqualified": 272,
    }, "Unexpected evidence-gap counts")

    scientific = l27["scientific_requirements"]
    need(len(scientific) == 11, "Original requirements")
    need(
        all(x["currently_independently_qualified"] is False
            for x in scientific),
        "Unexpected qualification",
    )

    contract = {
        "schema": "TRUST_ROBOT_L33_PROSPECTIVE_ACQUISITION_CONTRACT_V1",
        "parent_commit": BASE,
        "protocol_status": "ENGINEERING_PROPOSAL_NOT_SCIENTIFIC_QUALIFICATION",
        "prior_l27_contract_sha256": sha(l27path),
        "requirements_preserved": [
            x["requirement"] for x in scientific
        ],
        "future_capture_stages": [
            {
                "stage": "A",
                "name": "source_provenance",
                "required": [
                    "A pre-capture challenge identifier originating outside the capture writer",
                    "Independent verification of acquisition identity and source attribution",
                    "Per-modality source identity, counters, content hashes and immutable evidence roots",
                    "Documented independent witness trust boundary and replay challenge procedure",
                ],
                "qualification": "NOT_YET_VERIFIED",
            },
            {
                "stage": "B",
                "name": "exposure_timing_and_calibration",
                "required": [
                    "Camera physical exposure start/end semantics and uncertainty",
                    "LiDAR scan or firing event time origin and uncertainty",
                    "IMU sample or integration time semantics and clock domain",
                    "Measured cross-clock mapping, uncertainty and time-varying error bounds",
                    "Verified intrinsic/extrinsic transforms with independently reviewed provenance",
                ],
                "qualification": "NOT_YET_VERIFIED",
            },
            {
                "stage": "C",
                "name": "independent_six_dof_reference",
                "required": [
                    "Externally referenced position and orientation",
                    "Reference uncertainty, coverage and frame provenance",
                    "Independently verified reference-to-sensor time association",
                    "Physical correspondence and reference-sensor extrinsics",
                ],
                "qualification": "NOT_YET_VERIFIED",
            },
            {
                "stage": "D",
                "name": "prospective_heldout_validation",
                "required": [
                    "Frozen train, validation and confirmation-test policies",
                    "Held-out 6DoF localization error analysis",
                    "Calibrated factor uncertainty",
                    "Adjudicated healthy/fault controls and false-alarm/miss evaluation",
                ],
                "qualification": "NOT_YET_VERIFIED",
            },
        ],
        "future_acquisition_engineering_checks": [
            "Fail closed on duplicated or omitted event identities",
            "Bind each event to an immutable source payload and run identity",
            "Check independent capture-session challenge and receipt provenance",
            "Preserve explicit sensor event type and measurement-time definition",
            "Reject unverified physical synchronization and calibration claims",
            "Separate content equality from independent recording-origin evidence",
            "Reject self-rehashed metadata as sufficient authenticity proof",
        ],
        "limitations": [
            "An independent software process does not necessarily constitute an independent trusted physical witness",
            "A signature or nonce alone does not prove a physical sensor exposure",
            "Deterministic identical sensor payloads do not by themselves prove replay",
            "Simulator read-time consistency does not prove physical exposure synchronization",
            "Scripted USD translation does not qualify as independent 6DoF ground truth",
        ],
        "source_authenticity_verified": False,
        "physical_exposure_sync_verified": False,
        "independent_reference_verified": False,
        "calibrated_health_probabilities": False,
        "pose_factors_authorized": 0,
        "health_labels_generated": 0,
    }

    save(contract_out, contract)

    report = {
        "schema": "TRUST_ROBOT_L33_EVIDENCE_GAP_ASSESSMENT_V1",
        "parent_commit": BASE,
        "implementation_sha256": sha(Path(__file__)),
        "contract_sha256": sha(contract_out),
        "input_sha256": {
            k: expected for k, (_, expected) in pinned.items()
        },
        "verified_event_counts": counts,
        "verified_cross_run_overlap": overlap,
        "missing_evidence_counts": gaps,
        "l30_source_authenticity": "UNQUALIFIED",
        "l30_exposure_sync": "UNQUALIFIED",
        "l30_reference": "SCRIPTED_NOT_INDEPENDENT",
        "evidence_requirements_independently_qualified": 0,
        "evidence_requirements_total": 11,
        "scientific_admission_decisions": {
            "lidar_pose_factor": "DENIED_INSUFFICIENT_EVIDENCE",
            "scientific_6dof_accuracy": "DENIED_INSUFFICIENT_EVIDENCE",
            "supervised_health_labels": "DENIED_INSUFFICIENT_EVIDENCE",
            "live_freshness": "DENIED_INSUFFICIENT_EVIDENCE",
        },
        "adversarial_mutations_rejected": rejected,
        "adversarial_mutations_rejected_count": len(rejected),
        "prospective_protocol_scientifically_qualified": False,
        "historical_raw_recordings_modified": False,
        "new_simulator_run": False,
        "pose_factors_authorized": 0,
        "health_labels_generated": 0,
        "git_commit_or_push_performed": False,
        "next": "L34_DESIGN_AND_TEST_SEPARATE_CAPTURE_WITNESS_INSTRUMENTATION",
    }

    save(report_out, report)

    print("L33_L30_EVIDENCE_GAPS=VERIFIED")
    print("L33_CROSS_RUN_FINDINGS=RECONCILED")
    print("L33_FUTURE_ACQUISITION_CONTRACT=GENERATED")
    print("L33_NEGATIVE_CONTROLS=", len(rejected))
    print("L33_SCIENTIFIC_GATES=4_DENIED")
    print("L33_OFFLINE_PROTOCOL_ASSESSMENT=PASS")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    for name in ("archive", "l31", "l32", "contract", "report"):
        p.add_argument("--" + name, required=True)
    main(p.parse_args())
