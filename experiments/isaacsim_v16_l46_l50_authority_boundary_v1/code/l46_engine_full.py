"""L46 simulated software authority boundaries.

Ephemeral HMAC keys are generated in one local test process.
This is NOT an independent physical witness or trusted attestation.
"""

import argparse
import copy
import hashlib
import hmac
import json
import secrets
from pathlib import Path

PARENT = "c2e013f549b87e8646a8e51095a3372df0d09581"

CAND = (
    "4384b085f79dff51af5dbbf8a4c4bf4cae6deffc906bfbcaf8a8ef00a7e05dec"
)

ROOT = (
    "a1291003447394194d299e814f0e12c0e6d84eb37891bedbfa1e3d1264170b86"
)

MODE = "OFFLINE_SYNTHETIC_AUTHORITY_ONLY"


def need(cond, reason):
    if not cond:
        raise ValueError(reason)


def serial(obj):
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def sig(key, role, payload):
    return hmac.new(
        key,
        role.encode() + b"\0" + serial(payload),
        hashlib.sha256,
    ).hexdigest()


class TestAuthority:
    def __init__(self):
        self.issuer_key = secrets.token_bytes(32)
        self.witness_key = secrets.token_bytes(32)

    def issue(self):
        payload = {
            "schema": "L46_CHALLENGE_V1",
            "session_id": "L46_TEST_" + secrets.token_hex(8),
            "nonce_hex": secrets.token_hex(16),
            "candidate_sha256": CAND,
            "issuer_role": "ROLE_A_ISSUER",
            "producer": "SIMULATED_WRITER",
            "logical_deadline": 100,
            "mode": MODE,
        }

        return {
            "payload": payload,
            "mac": sig(
                self.issuer_key,
                "ISSUE_V1",
                payload,
            ),
        }

    def seal(self, issue, event_root):
        payload = {
            "schema": "L46_SEAL_V1",
            "session_id": issue["payload"]["session_id"],
            "nonce_hex": issue["payload"]["nonce_hex"],
            "challenge_sha256": sha(serial(issue)),
            "event_root_sha256": event_root,
            "witness_role": "ROLE_B_SOFTWARE_WITNESS",
            "mode": MODE,
            "source_payloads_witnessed": False,
            "physical_sync_verified": False,
            "new_sensor_measurements": 0,
            "pose_factors_authorized": 0,
            "health_labels_generated": 0,
        }

        return {
            "payload": payload,
            "mac": sig(
                self.witness_key,
                "SEAL_V1",
                payload,
            ),
        }

    def verify(
        self,
        issue,
        seal,
        expected_session,
        expected_root,
        tick=50,
        registry=None,
    ):
        need(
            isinstance(issue, dict)
            and set(issue) == {"payload", "mac"},
            "CHALLENGE_SHAPE",
        )

        need(
            isinstance(seal, dict)
            and set(seal) == {"payload", "mac"},
            "SEAL_SHAPE",
        )

        a = issue["payload"]
        w = seal["payload"]

        issue_fields = {
            "schema",
            "session_id",
            "nonce_hex",
            "candidate_sha256",
            "issuer_role",
            "producer",
            "logical_deadline",
            "mode",
        }

        seal_fields = {
            "schema",
            "session_id",
            "nonce_hex",
            "challenge_sha256",
            "event_root_sha256",
            "witness_role",
            "mode",
            "source_payloads_witnessed",
            "physical_sync_verified",
            "new_sensor_measurements",
            "pose_factors_authorized",
            "health_labels_generated",
        }

        need(
            isinstance(a, dict)
            and set(a) == issue_fields,
            "ISSUE_FIELDS",
        )

        need(
            isinstance(w, dict)
            and set(w) == seal_fields,
            "SEAL_FIELDS",
        )

        need(
            isinstance(issue["mac"], str)
            and isinstance(seal["mac"], str),
            "MAC_TYPES",
        )

        need(
            hmac.compare_digest(
                issue["mac"],
                sig(
                    self.issuer_key,
                    "ISSUE_V1",
                    a,
                ),
            ),
            "ISSUE_MAC",
        )

        need(
            hmac.compare_digest(
                seal["mac"],
                sig(
                    self.witness_key,
                    "SEAL_V1",
                    w,
                ),
            ),
            "SEAL_MAC",
        )

        need(
            type(a["session_id"]) is str
            and a["session_id"] == expected_session
            and a["session_id"].startswith("L46_TEST_"),
            "SESSION",
        )

        need(
            type(a["nonce_hex"]) is str
            and len(a["nonce_hex"]) == 32
            and len(bytes.fromhex(a["nonce_hex"])) == 16,
            "NONCE",
        )

        need(
            a["schema"] == "L46_CHALLENGE_V1"
            and a["candidate_sha256"] == CAND
            and a["issuer_role"] == "ROLE_A_ISSUER"
            and a["producer"] == "SIMULATED_WRITER"
            and a["mode"] == MODE,
            "ISSUE_CONTEXT",
        )

        need(
            type(tick) is int
            and 0 <= tick <= a["logical_deadline"]
            and type(a["logical_deadline"]) is int
            and a["logical_deadline"] == 100,
            "LOGICAL_TICK",
        )

        need(
            w["schema"] == "L46_SEAL_V1"
            and w["session_id"] == a["session_id"]
            and w["nonce_hex"] == a["nonce_hex"]
            and w["challenge_sha256"] == sha(serial(issue)),
            "SEAL_LINK",
        )

        need(
            w["event_root_sha256"] == expected_root
            and type(w["event_root_sha256"]) is str
            and len(bytes.fromhex(w["event_root_sha256"])) == 32,
            "EVENT_ROOT",
        )

        need(
            w["witness_role"] == "ROLE_B_SOFTWARE_WITNESS"
            and w["mode"] == MODE,
            "WITNESS_CONTEXT",
        )

        need(
            w["source_payloads_witnessed"] is False
            and w["physical_sync_verified"] is False
            and type(w["new_sensor_measurements"]) is int
            and w["new_sensor_measurements"] == 0
            and type(w["pose_factors_authorized"]) is int
            and w["pose_factors_authorized"] == 0
            and type(w["health_labels_generated"]) is int
            and w["health_labels_generated"] == 0,
            "SCIENCE_DENIED",
        )

        if registry is not None:
            fingerprint = sha(
                bytes.fromhex(a["nonce_hex"])
            )

            need(
                fingerprint not in registry,
                "REPLAY",
            )

            registry.add(fingerprint)

        return True


def exercise():
    p = TestAuthority()

    ch = p.issue()
    seal = p.seal(ch, ROOT)

    session = ch["payload"]["session_id"]

    need(
        p.verify(
            ch, seal, session, ROOT,
            registry=set(),
        ),
        "GOOD_BASELINE",
    )

    blocked = []

    def deny(
        name,
        issue=None,
        witness=None,
        expected_session=None,
        expected_root=None,
        tick=50,
        reg=None,
    ):
        try:
            p.verify(
                ch if issue is None else issue,
                seal if witness is None else witness,
                session if expected_session is None
                    else expected_session,
                ROOT if expected_root is None
                    else expected_root,
                tick,
                reg,
            )
        except (
            ValueError,
            TypeError,
            KeyError,
            OverflowError,
        ):
            blocked.append(name)
        else:
            raise AssertionError(
                "CONTROL_ACCEPTED:" + name
            )

    issue_mutations = {
        "schema": "BAD",
        "session_id": "ALTERED",
        "nonce_hex": "0" * 32,
        "candidate_sha256": "1" * 64,
        "issuer_role": "ROLE_B_SOFTWARE_WITNESS",
        "producer": "FORGED_PRODUCER",
        "logical_deadline": 101,
        "mode": "FAKE",
    }

    for field, value in issue_mutations.items():
        x = copy.deepcopy(ch)
        x["payload"][field] = value

        deny(
            "issue_" + field,
            issue=x,
        )

    seal_mutations = {
        "schema": "BAD",
        "session_id": "ALTERED",
        "nonce_hex": "f" * 32,
        "challenge_sha256": "2" * 64,
        "event_root_sha256": "3" * 64,
        "witness_role": "ROLE_A_ISSUER",
        "mode": "FAKE",
        "source_payloads_witnessed": True,
        "physical_sync_verified": True,
        "new_sensor_measurements": 1,
        "pose_factors_authorized": 1,
        "health_labels_generated": 1,
    }

    for field, value in seal_mutations.items():
        x = copy.deepcopy(seal)
        x["payload"][field] = value

        deny(
            "seal_" + field,
            witness=x,
        )

    x = copy.deepcopy(ch)
    x["mac"] = "0" * 64
    deny("issue_mac", issue=x)

    x = copy.deepcopy(seal)
    x["mac"] = "0" * 64
    deny("seal_mac", witness=x)

    x = copy.deepcopy(ch)
    del x["payload"]["session_id"]
    deny("issue_missing_field", issue=x)

    x = copy.deepcopy(seal)
    del x["payload"]["event_root_sha256"]
    deny("seal_missing_field", witness=x)

    x = copy.deepcopy(ch)
    x["payload"]["extra"] = "UNEXPECTED"
    deny("issue_extra_field", issue=x)

    x = copy.deepcopy(seal)
    x["payload"]["extra"] = "UNEXPECTED"
    deny("seal_extra_field", witness=x)

    deny("expired_logical_tick", tick=101)
    deny("negative_logical_tick", tick=-1)

    deny(
        "external_session_mismatch",
        expected_session="DIFFERENT",
    )

    deny(
        "external_root_mismatch",
        expected_root="4" * 64,
    )

    consumed = set()

    p.verify(
        ch, seal, session, ROOT,
        registry=consumed,
    )

    deny(
        "same_registry_replay",
        reg=consumed,
    )

    alternate = p.issue()
    alternate_seal = p.seal(
        alternate, ROOT
    )

    deny(
        "swap_seal_between_challenges",
        witness=alternate_seal,
    )

    x = copy.deepcopy(ch)

    x["mac"] = sig(
        p.witness_key,
        "ISSUE_V1",
        x["payload"],
    )

    deny(
        "wrong_role_key_challenge",
        issue=x,
    )

    x = copy.deepcopy(seal)

    x["mac"] = sig(
        p.issuer_key,
        "SEAL_V1",
        x["payload"],
    )

    deny(
        "wrong_role_key_seal",
        witness=x,
    )

    # Even with a valid synthetic test MAC,
    # unsupported physical claims are rejected.
    x = copy.deepcopy(seal)

    x["payload"]["source_payloads_witnessed"] = True

    x["mac"] = sig(
        p.witness_key,
        "SEAL_V1",
        x["payload"],
    )

    deny(
        "signed_false_physical_claim",
        witness=x,
    )

    # A coherent invented transcript can be signed
    # by the same local software test roles.
    forged_root = sha(
        b"L46_SELF_FABRICATED_CONTENT_NOT_SENSOR_DATA"
    )

    forged = p.seal(
        ch, forged_root
    )

    need(
        p.verify(
            ch,
            forged,
            session,
            forged_root,
            registry=set(),
        ),
        "COHERENT_FABRICATION",
    )

    need(
        forged["payload"]["source_payloads_witnessed"]
        is False,
        "PROVENANCE_PROMOTION",
    )

    # Two isolated registries accept the same nonce.
    # This demonstrates lack of global replay protection.
    left = set()
    right = set()

    need(
        p.verify(
            ch, seal, session, ROOT,
            registry=left,
        )
        and p.verify(
            ch, seal, session, ROOT,
            registry=right,
        ),
        "CLONED_REGISTRY_DEMONSTRATION",
    )

    return {
        "negative_control_names": blocked,
        "negative_controls_denied": len(blocked),
        "coherent_software_forgery_internally_accepted": True,
        "coherent_software_forgery_trusted": False,
        "independent_registry_clone_double_acceptance": True,
        "logical_clock_trusted": False,
        "real_physical_witness_verified": False,
        "new_sensor_acquisitions": 0,
        "pose_factors_authorized": 0,
        "health_labels_generated": 0,
        "live_simulator_launch_authorized": False,
    }


def write_json(path, obj):
    with Path(path).open(
        "x",
        encoding="utf-8",
    ) as f:
        f.write(
            json.dumps(
                obj,
                indent=2,
                sort_keys=True,
                allow_nan=False,
            ) + "\n"
        )


def main():
    parser = argparse.ArgumentParser()

    for name in (
        "l41",
        "l45",
        "contract",
        "report",
    ):
        parser.add_argument(
            "--" + name,
            required=True,
        )

    args = parser.parse_args()

    l41 = json.loads(
        Path(args.l41).read_text()
    )

    l45 = json.loads(
        Path(args.l45).read_text()
    )

    need(
        l41["schema"]
        == "TRUST_ROBOT_L41_ACQUISITION_WITNESS_READINESS_V1",
        "L41_SCHEMA",
    )

    need(
        l41["readiness_verdict"]
        == "LIVE_CAPTURE_DENIED_SCIENCE_GATES_CLOSED",
        "L41_GATE",
    )

    need(
        l45["schema"]
        == "TRUST_ROBOT_L45_COHERENT_FORGERY_FALSIFICATION_REPORT_V1",
        "L45_SCHEMA",
    )

    need(
        l45["coherent_rekey_count"] == 12
        and l45["coherent_cases_with_trusted_provenance"]
        == 0,
        "L45_PROVENANCE",
    )

    need(
        l45["new_sensor_measurements"] == 0
        and l45["pose_factors_authorized"] == 0,
        "L45_SCIENCE",
    )

    contract = {
        "schema":
            "TRUST_ROBOT_L46_AUTHORITY_TRUST_BOUNDARY_CONTRACT_V1",
        "parent_commit": PARENT,
        "l41_sha256": sha(
            Path(args.l41).read_bytes()
        ),
        "l45_sha256": sha(
            Path(args.l45).read_bytes()
        ),
        "simulation_source_sha256": sha(
            Path(__file__).read_bytes()
        ),
        "authority_type":
            "TWO_SIMULATED_SOFTWARE_ROLES_ONE_HOST_EPHEMERAL_HMAC",
        "key_material_persisted": False,
        "independent_physical_trust_established": False,
        "required_external_gates": [
            "separately_administered_issuer_and_verifier_identity",
            "independent_capture_source_witness",
            "trusted_real_measurement_time_semantics",
            "independently_controlled_immutable_receipts",
            "cross_host_atomic_nonce_consumption",
            "hardware_backed_key_attestation_if_required",
            "real_power_loss_fault_injection",
            "independent_six_dof_reference_and_calibration",
            "heldout_scientific_evaluation",
        ],
        "live_simulator_launch_authorized": False,
        "pose_factors_authorized": 0,
    }

    write_json(
        args.contract,
        contract,
    )

    tests = exercise()

    need(
        tests["negative_controls_denied"] == 35,
        "NEGATIVE_COUNT",
    )

    report = {
        "schema":
            "TRUST_ROBOT_L46_SYNTHETIC_AUTHORITY_FALSIFICATION_V1",
        "contract_sha256": sha(
            Path(args.contract).read_bytes()
        ),
        "source_sha256": sha(
            Path(__file__).read_bytes()
        ),
        "test_results": tests,
        "ephemeral_key_material_archived": False,
        "physical_source_authenticity_verified": False,
        "hardware_attestation_verified": False,
        "trusted_clock_verified": False,
        "multi_host_replay_protection_verified": False,
        "real_power_loss_durability_verified": False,
        "new_sensor_acquisitions": 0,
        "pose_factors_authorized": 0,
        "health_labels_generated": 0,
        "simulator_launch_authorized": False,
    }

    write_json(
        args.report,
        report,
    )

    print("L46_SYNTHETIC_ROLE_BOUNDARIES=EXERCISED")
    print("L46_NEGATIVE_CONTROLS=35_DENIED")
    print(
        "L46_SIGNED_COHERENT_FABRICATION="
        "INTERNALLY_ACCEPTED_UNTRUSTED"
    )
    print(
        "L46_SPLIT_NONCE_REGISTRY_REPLAY="
        "DEMONSTRATED"
    )
    print(
        "L46_PHYSICAL_SOURCE_AUTHENTICITY="
        "UNVERIFIED"
    )
    print("L46_OFFLINE_AUTHORITY_FALSIFICATION=PASS")


if __name__ == "__main__":
    main()
