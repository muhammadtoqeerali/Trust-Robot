"""TRUST-ROBOT L36 acquisition-time integration interface.

Offline engineering preflight and sealing rehearsal.

No GPU execution, new sensor acquisition, physical
synchronization, trusted hardware attestation, independently
measured 6DoF ground truth, or estimator factor admission.
"""

import argparse
import copy
import hashlib
import json

from pathlib import Path


BASE = (
    "0b542e8644f3c4b98ed92c0f83a7c82a4635ae52"
)

CONTRACT = (
    "24e71f94c8acfc3aa59184c49a811d62f54fc93d90178bbebef6c8239912467b"
)

L35_REPORT = (
    "a0f40a5fa2d0c9dff055278305fb05047e1c8c664d4c905d7978086f59fb4991"
)

L35_TRANSCRIPT = (
    "b2fa0728d1aa867d162bae7e463f7bf353b058222d2700eaf392cd271ed97736"
)

CANDIDATE = (
    "993d21523afd54dca39ce6fcf27ba20d430324c5b7b5b9b25939521c0082bb78"
)

SCENE = (
    "43b4ffe0f7af29e435203ac3aa8c2d4c4897434042f37e26586b124b2495d8cf"
)

SESSION = "KIOS_L36_OFFLINE_PREFLIGHT_FIXTURE_V1"
MODE = "OFFLINE_PROTOCOL_FIXTURE_NO_SIMULATOR"

TTL_NS = 30_000_000_000


def need(condition, message):
    if not condition:
        raise ValueError(message)


def compact(value):
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def hash_obj(value):
    return hashlib.sha256(compact(value)).hexdigest()


def hash_file(path):
    return hashlib.sha256(
        Path(path).read_bytes()
    ).hexdigest()


def nonce_hash(challenge):
    nonce = challenge["nonce_hex"]

    need(
        isinstance(nonce, str) and len(nonce) == 64,
        "Invalid nonce length",
    )

    raw = bytes.fromhex(nonce)

    need(len(raw) == 32, "Invalid nonce bytes")

    return hashlib.sha256(raw).hexdigest()


def initial_fixture():
    # Deliberately deterministic offline protocol fixture.
    # Not a fresh security credential or real capture challenge.
    time_ns = 1_000_000_000_000

    challenge = {
        "schema":
            "TRUST_ROBOT_L36_ISSUER_CHALLENGE_V1",

        "session_id": SESSION,

        "issuer_role":
            "SEPARATE_SOFTWARE_ISSUER_UNTRUSTED_HOST",

        "nonce_hex": "a4" * 32,

        "issued_monotonic_ns_untrusted": time_ns,

        "contract_sha256": CONTRACT,
        "capture_source_sha256": CANDIDATE,
        "scene_sha256": SCENE,

        "physical_clock_verified": False,
        "hardware_attestation_verified": False,
    }

    request = {
        "schema":
            "TRUST_ROBOT_L36_CAPTURE_REQUEST_V1",

        "session_id": SESSION,
        "mode": MODE,

        "challenge_sha256": hash_obj(challenge),
        "nonce_sha256": nonce_hash(challenge),

        "contract_sha256": CONTRACT,
        "capture_source_sha256": CANDIDATE,
        "scene_sha256": SCENE,

        "parent_commit": BASE,

        "gpu_launch_requested": False,

        "independent_source_authenticity_verified":
            False,

        "physical_sync_verified": False,
        "pose_factor_authorized": False,
    }

    return challenge, request, time_ns + 1_000_000


def preflight(challenge, request, at_ns, consumed):
    need(
        set(challenge) == {
            "schema",
            "session_id",
            "issuer_role",
            "nonce_hex",
            "issued_monotonic_ns_untrusted",
            "contract_sha256",
            "capture_source_sha256",
            "scene_sha256",
            "physical_clock_verified",
            "hardware_attestation_verified",
        },
        "Challenge fields",
    )

    need(
        set(request) == {
            "schema",
            "session_id",
            "mode",
            "challenge_sha256",
            "nonce_sha256",
            "contract_sha256",
            "capture_source_sha256",
            "scene_sha256",
            "parent_commit",
            "gpu_launch_requested",
            "independent_source_authenticity_verified",
            "physical_sync_verified",
            "pose_factor_authorized",
        },
        "Request fields",
    )

    need(
        challenge["schema"]
        == "TRUST_ROBOT_L36_ISSUER_CHALLENGE_V1",
        "Challenge schema",
    )

    need(
        request["schema"]
        == "TRUST_ROBOT_L36_CAPTURE_REQUEST_V1",
        "Request schema",
    )

    need(
        challenge["issuer_role"]
        == "SEPARATE_SOFTWARE_ISSUER_UNTRUSTED_HOST",
        "Issuer role",
    )

    need(
        challenge["session_id"]
        == request["session_id"]
        == SESSION,
        "Session identity",
    )

    need(
        challenge["contract_sha256"]
        == request["contract_sha256"]
        == CONTRACT,
        "Contract binding",
    )

    need(
        challenge["capture_source_sha256"]
        == request["capture_source_sha256"]
        == CANDIDATE,
        "Acquisition source binding",
    )

    need(
        challenge["scene_sha256"]
        == request["scene_sha256"]
        == SCENE,
        "Scene source binding",
    )

    need(
        request["parent_commit"] == BASE,
        "Parent Git commit",
    )

    need(
        request["mode"] == MODE
        and request["gpu_launch_requested"] is False,
        "Offline-only gate",
    )

    need(
        challenge["hardware_attestation_verified"]
        is False,
        "Unverified hardware claim",
    )

    need(
        challenge["physical_clock_verified"]
        is False,
        "Unverified clock claim",
    )

    for field in (
        "independent_source_authenticity_verified",
        "physical_sync_verified",
        "pose_factor_authorized",
    ):
        need(
            request[field] is False,
            "Invalid request claim: " + field,
        )

    nh = nonce_hash(challenge)

    need(
        nh not in consumed,
        "Previously consumed nonce",
    )

    need(
        request["challenge_sha256"]
        == hash_obj(challenge),
        "Challenge digest mismatch",
    )

    need(
        request["nonce_sha256"] == nh,
        "Nonce digest mismatch",
    )

    issued = challenge[
        "issued_monotonic_ns_untrusted"
    ]

    need(
        type(issued) is int
        and type(at_ns) is int,
        "Invalid clock types",
    )

    need(
        0 <= at_ns - issued <= TTL_NS,
        "Invalid or expired local challenge",
    )

    return {
        "schema":
            "TRUST_ROBOT_L36_PREFLIGHT_RECEIPT_V1",

        "session_id": SESSION,
        "mode": MODE,

        "challenge_sha256": hash_obj(challenge),
        "request_sha256": hash_obj(request),
        "nonce_sha256": nh,

        "preflight_monotonic_ns_untrusted": at_ns,

        "preflight_engineering_status":
            "OFFLINE_REHEARSAL_ADMITTED",

        "simulator_launch_authorized": False,

        "hardware_attestation_verified": False,
        "physical_sync_verified": False,

        "pose_factors_authorized": 0,
    }


def fixture_observation(
    challenge, admission, at_ns
):
    return {
        "schema":
            "TRUST_ROBOT_L36_FIXTURE_OBSERVATION_V1",

        "session_id": SESSION,
        "mode": MODE,

        "challenge_sha256": hash_obj(challenge),
        "admission_sha256": hash_obj(admission),
        "nonce_sha256": nonce_hash(challenge),

        "l35_transcript_sha256": L35_TRANSCRIPT,

        "fixture_camera_references": 6,
        "fixture_lidar_references": 6,

        "new_sensor_measurements": 0,

        "observation_monotonic_ns_untrusted": at_ns,

        "hardware_attestation_verified": False,
        "physical_sync_verified": False,
        "independent_6dof_reference_verified": False,

        "pose_factors_authorized": 0,
        "health_labels_generated": 0,
    }


def seal(challenge, request, admission, obs, at_ns):
    need(
        set(admission) == {
            "schema",
            "session_id",
            "mode",
            "challenge_sha256",
            "request_sha256",
            "nonce_sha256",
            "preflight_monotonic_ns_untrusted",
            "preflight_engineering_status",
            "simulator_launch_authorized",
            "hardware_attestation_verified",
            "physical_sync_verified",
            "pose_factors_authorized",
        },
        "Admission fields",
    )

    need(
        set(obs) == {
            "schema",
            "session_id",
            "mode",
            "challenge_sha256",
            "admission_sha256",
            "nonce_sha256",
            "l35_transcript_sha256",
            "fixture_camera_references",
            "fixture_lidar_references",
            "new_sensor_measurements",
            "observation_monotonic_ns_untrusted",
            "hardware_attestation_verified",
            "physical_sync_verified",
            "independent_6dof_reference_verified",
            "pose_factors_authorized",
            "health_labels_generated",
        },
        "Observation fields",
    )

    need(
        admission["schema"]
        == "TRUST_ROBOT_L36_PREFLIGHT_RECEIPT_V1",
        "Admission schema",
    )

    need(
        obs["schema"]
        == "TRUST_ROBOT_L36_FIXTURE_OBSERVATION_V1",
        "Observation schema",
    )

    need(
        admission["session_id"]
        == obs["session_id"]
        == request["session_id"]
        == SESSION,
        "Session continuity",
    )

    need(
        admission["mode"] == obs["mode"] == MODE,
        "Mode continuity",
    )

    need(
        admission["challenge_sha256"]
        == obs["challenge_sha256"]
        == hash_obj(challenge),
        "Challenge continuity",
    )

    need(
        admission["request_sha256"]
        == hash_obj(request),
        "Request continuity",
    )

    need(
        admission["nonce_sha256"]
        == obs["nonce_sha256"]
        == nonce_hash(challenge),
        "Nonce continuity",
    )

    need(
        obs["admission_sha256"]
        == hash_obj(admission),
        "Admission continuity",
    )

    need(
        admission["preflight_engineering_status"]
        == "OFFLINE_REHEARSAL_ADMITTED",
        "Preflight status",
    )

    need(
        admission["simulator_launch_authorized"]
        is False,
        "Unauthorized simulator launch",
    )

    need(
        obs["l35_transcript_sha256"]
        == L35_TRANSCRIPT,
        "Historical fixture binding",
    )

    need(
        obs["fixture_camera_references"] == 6
        and obs["fixture_lidar_references"] == 6,
        "Fixture reference counts",
    )

    need(
        obs["new_sensor_measurements"] == 0,
        "Unexpected new measurements",
    )

    for flag in (
        "hardware_attestation_verified",
        "physical_sync_verified",
    ):
        need(
            admission[flag] is False
            and obs[flag] is False,
            "Unqualified evidence: " + flag,
        )

    need(
        obs["independent_6dof_reference_verified"]
        is False,
        "Independent reference claim",
    )

    need(
        admission["pose_factors_authorized"]
        == obs["pose_factors_authorized"]
        == 0,
        "Unauthorized pose factors",
    )

    need(
        obs["health_labels_generated"] == 0,
        "Unauthorized health labels",
    )

    issued = challenge[
        "issued_monotonic_ns_untrusted"
    ]

    admitted = admission[
        "preflight_monotonic_ns_untrusted"
    ]

    observed = obs[
        "observation_monotonic_ns_untrusted"
    ]

    need(
        all(
            type(v) is int
            for v in (
                issued, admitted, observed, at_ns
            )
        ),
        "Invalid time types",
    )

    need(
        issued < admitted < observed < at_ns,
        "Invalid software process ordering",
    )

    return {
        "schema":
            "TRUST_ROBOT_L36_OFFLINE_SEAL_RECEIPT_V1",

        "session_id": SESSION,

        "challenge_sha256": hash_obj(challenge),
        "admission_sha256": hash_obj(admission),
        "fixture_observation_sha256": hash_obj(obs),

        "sealing_monotonic_ns_untrusted": at_ns,

        "simulator_launch_authorized": False,
        "new_sensor_measurements": 0,

        "hardware_attestation_verified": False,
        "physical_sync_verified": False,
        "independent_6dof_reference_verified": False,

        "pose_factors_authorized": 0,
        "health_labels_generated": 0,
    }


def negative_tests(ch, req, at, admission, obs, seal_at):
    preflight_cases = [
        (
            "missing_challenge_field",
            "challenge",
            lambda x: x.pop("nonce_hex"),
        ),
        (
            "extra_challenge_field",
            "challenge",
            lambda x: x.update(unexpected=1),
        ),
        (
            "bad_challenge_schema",
            "challenge",
            lambda x: x.update(schema="BAD"),
        ),
        (
            "nonce_too_short",
            "challenge",
            lambda x: x.update(nonce_hex="0a"),
        ),
        (
            "nonce_not_hex",
            "challenge",
            lambda x: x.update(nonce_hex="zx" * 32),
        ),
        (
            "forged_issuer_identity",
            "challenge",
            lambda x: x.update(
                issuer_role="TRUSTED_HARDWARE"
            ),
        ),
        (
            "challenge_wrong_session",
            "challenge",
            lambda x: x.update(session_id="OTHER"),
        ),
        (
            "challenge_wrong_contract",
            "challenge",
            lambda x: x.update(
                contract_sha256="1" * 64
            ),
        ),
        (
            "challenge_wrong_source",
            "challenge",
            lambda x: x.update(
                capture_source_sha256="1" * 64
            ),
        ),
        (
            "challenge_wrong_scene",
            "challenge",
            lambda x: x.update(
                scene_sha256="1" * 64
            ),
        ),
        (
            "challenge_claims_hardware",
            "challenge",
            lambda x: x.update(
                hardware_attestation_verified=True
            ),
        ),
        (
            "future_challenge",
            "challenge",
            lambda x: x.update(
                issued_monotonic_ns_untrusted=at + 1
            ),
        ),
        (
            "expired_challenge",
            "challenge",
            lambda x: x.update(
                issued_monotonic_ns_untrusted=
                at - TTL_NS - 1
            ),
        ),
        (
            "missing_request_field",
            "request",
            lambda x: x.pop("nonce_sha256"),
        ),
        (
            "wrong_request_session",
            "request",
            lambda x: x.update(session_id="OTHER"),
        ),
        (
            "wrong_challenge_binding",
            "request",
            lambda x: x.update(
                challenge_sha256="0" * 64
            ),
        ),
        (
            "wrong_nonce_binding",
            "request",
            lambda x: x.update(
                nonce_sha256="0" * 64
            ),
        ),
        (
            "wrong_parent_commit",
            "request",
            lambda x: x.update(
                parent_commit="0" * 40
            ),
        ),
        (
            "wrong_request_source",
            "request",
            lambda x: x.update(
                capture_source_sha256="0" * 64
            ),
        ),
        (
            "wrong_request_scene",
            "request",
            lambda x: x.update(
                scene_sha256="0" * 64
            ),
        ),
        (
            "gpu_requested",
            "request",
            lambda x: x.update(
                gpu_launch_requested=True
            ),
        ),
        (
            "wrong_request_mode",
            "request",
            lambda x: x.update(
                mode="SIMULATOR_LIVE"
            ),
        ),
        (
            "auth_claim",
            "request",
            lambda x: x.update(
                independent_source_authenticity_verified=True
            ),
        ),
        (
            "sync_claim",
            "request",
            lambda x: x.update(
                physical_sync_verified=True
            ),
        ),
        (
            "pose_factor_claim",
            "request",
            lambda x: x.update(
                pose_factor_authorized=True
            ),
        ),
        (
            "consumed_nonce",
            "consumed",
            lambda x: x.add(nonce_hash(ch)),
        ),
    ]

    rejected = []

    for name, target, mutation in preflight_cases:
        cc = copy.deepcopy(ch)
        rr = copy.deepcopy(req)
        used = set()

        target_obj = {
            "challenge": cc,
            "request": rr,
            "consumed": used,
        }[target]

        mutation(target_obj)

        if target == "challenge":
            # Rebind the changed challenge to isolate
            # substantive gate rules from a hash mismatch.
            rr["challenge_sha256"] = hash_obj(cc)

        try:
            preflight(cc, rr, at, used)
        except (
            ValueError,
            KeyError,
            TypeError,
            OverflowError,
        ):
            rejected.append(name)
        else:
            raise AssertionError(
                "Preflight accepted: " + name
            )

    seal_cases = [
        (
            "missing_admission_field",
            "admission",
            lambda x: x.pop("nonce_sha256"),
        ),
        (
            "admission_claims_launch",
            "admission",
            lambda x: x.update(
                simulator_launch_authorized=True
            ),
        ),
        (
            "admission_wrong_session",
            "admission",
            lambda x: x.update(session_id="OTHER"),
        ),
        (
            "admission_wrong_challenge",
            "admission",
            lambda x: x.update(
                challenge_sha256="0" * 64
            ),
        ),
        (
            "admission_wrong_request",
            "admission",
            lambda x: x.update(
                request_sha256="0" * 64
            ),
        ),
        (
            "admission_claims_sync",
            "admission",
            lambda x: x.update(
                physical_sync_verified=True
            ),
        ),
        (
            "admission_fake_pose_factor",
            "admission",
            lambda x: x.update(
                pose_factors_authorized=1
            ),
        ),
        (
            "admission_time_backwards",
            "admission",
            lambda x: x.update(
                preflight_monotonic_ns_untrusted=
                ch["issued_monotonic_ns_untrusted"]
            ),
        ),
        (
            "missing_observation_field",
            "observation",
            lambda x: x.pop(
                "l35_transcript_sha256"
            ),
        ),
        (
            "observation_wrong_session",
            "observation",
            lambda x: x.update(session_id="OTHER"),
        ),
        (
            "observation_wrong_admission",
            "observation",
            lambda x: x.update(
                admission_sha256="0" * 64
            ),
        ),
        (
            "observation_wrong_nonce",
            "observation",
            lambda x: x.update(
                nonce_sha256="0" * 64
            ),
        ),
        (
            "observation_wrong_fixture",
            "observation",
            lambda x: x.update(
                l35_transcript_sha256="0" * 64
            ),
        ),
        (
            "observation_new_measurements",
            "observation",
            lambda x: x.update(
                new_sensor_measurements=12
            ),
        ),
        (
            "observation_extra_frame",
            "observation",
            lambda x: x.update(
                fixture_camera_references=7
            ),
        ),
        (
            "observation_forged_hardware",
            "observation",
            lambda x: x.update(
                hardware_attestation_verified=True
            ),
        ),
        (
            "observation_forged_reference",
            "observation",
            lambda x: x.update(
                independent_6dof_reference_verified=True
            ),
        ),
        (
            "observation_forged_health",
            "observation",
            lambda x: x.update(
                health_labels_generated=1
            ),
        ),
        (
            "observation_time_before_preflight",
            "observation",
            lambda x: x.update(
                observation_monotonic_ns_untrusted=at
            ),
        ),
        (
            "seal_time_before_record",
            "time",
            lambda x: x.update(
                seal_at=obs[
                    "observation_monotonic_ns_untrusted"
                ]
            ),
        ),
    ]

    for name, target, mutation in seal_cases:
        aa = copy.deepcopy(admission)
        oo = copy.deepcopy(obs)
        times = {"seal_at": seal_at}

        target_obj = {
            "admission": aa,
            "observation": oo,
            "time": times,
        }[target]

        mutation(target_obj)

        if target == "admission":
            # Keep the observation's admission digest
            # consistent while testing the gate itself.
            oo["admission_sha256"] = hash_obj(aa)

        try:
            seal(
                ch, req, aa, oo, times["seal_at"]
            )
        except (
            ValueError,
            KeyError,
            TypeError,
        ):
            rejected.append(name)
        else:
            raise AssertionError(
                "Seal accepted: " + name
            )

    need(
        len(rejected)
        == len(preflight_cases) + len(seal_cases)
        == 46,
        "Negative control count",
    )

    need(
        len(set(rejected)) == len(rejected),
        "Duplicate negative control",
    )

    return rejected


def main(args):
    sources = {
        "published_l33_contract": (
            Path(args.contract),
            CONTRACT,
        ),
        "published_l35_report": (
            Path(args.l35report),
            L35_REPORT,
        ),
        "published_l35_transcript": (
            Path(args.l35transcript),
            L35_TRANSCRIPT,
        ),
    }

    for name, (path, expected) in sources.items():
        need(
            path.is_file() and not path.is_symlink(),
            "Input missing: " + name,
        )

        need(
            hash_file(path) == expected,
            "Pinned input changed: " + name,
        )

    l33 = json.loads(
        sources["published_l33_contract"][0]
        .read_text(encoding="utf-8")
    )

    l35 = json.loads(
        sources["published_l35_report"][0]
        .read_text(encoding="utf-8")
    )

    transcript = (
        sources["published_l35_transcript"][0]
        .read_text(encoding="utf-8")
        .splitlines()
    )

    need(
        l33["schema"]
        == "TRUST_ROBOT_L33_PROSPECTIVE_ACQUISITION_CONTRACT_V1",
        "L33 contract schema",
    )

    need(
        l35["schema"]
        == "TRUST_ROBOT_L35_PROSPECTIVE_ORDER_REHEARSAL_VALIDATION_V1",
        "L35 report schema",
    )

    need(
        l35["negative_controls_count"] == 25
        and l35["rehearsed_new_sensor_measurements"] == 0,
        "L35 scientific restrictions",
    )

    need(len(transcript) == 12, "L35 fixture count")

    need(
        all(
            isinstance(json.loads(line), dict)
            for line in transcript
        ),
        "Invalid L35 transcript",
    )

    challenge, request, time_ns = initial_fixture()

    admission = preflight(
        challenge, request, time_ns, set()
    )

    observation = fixture_observation(
        challenge,
        admission,
        time_ns + 1_000_000,
    )

    sealed = seal(
        challenge,
        request,
        admission,
        observation,
        time_ns + 2_000_000,
    )

    rejected = negative_tests(
        challenge,
        request,
        time_ns,
        admission,
        observation,
        time_ns + 2_000_000,
    )

    contract = {
        "schema":
            "TRUST_ROBOT_L36_ACQUISITION_TIME_INTERFACE_CONTRACT_V1",

        "parent_commit": BASE,

        "goal":
            "Future guarded Isaac Sim preflight and sealing hooks",

        "state_order": [
            "ISSUE_CHALLENGE",
            "PREFLIGHT_GATE",
            "ACQUISITION_HOOK",
            "SEAL_RECEIPT",
        ],

        "scope":
            "ENGINEERING_OFFLINE_INTERFACE_NOT_LIVE_GPU_PERMISSION",

        "nonce_replay_requirement":
            "Persist consumed nonce in independent durable storage before future launch; not implemented or proven here",

        "future_issuer":
            "Independent trusted recording source requires separate qualification; current software issuer is untrusted",

        "preflight_requires": [
            "Preissued unconsumed nonce within untrusted local clock TTL",
            "Exact capture session ID and contract hash",
            "Hash-pinned acquisition source and scene",
            "Validated issuer challenge binding",
            "Separate guarded GPU authorization before any live launch",
        ],

        "future_capture_hook_requires": [
            "Actual payload source digests produced after admission",
            "Capture-session identity bound to every sensor stream",
            "Defined camera LiDAR and IMU measurement-time semantics",
            "Independent calibration and reference evidence",
        ],

        "future_seal_requires": [
            "Captured source payload hashes bound to challenge and admission",
            "Independently controlled immutable witness storage",
            "Power-loss and partial-capture recovery behavior",
            "Challenge replay rejection across process restarts",
        ],

        "not_implemented": [
            "Live Isaac Sim integration",
            "External hardware attestation",
            "Physical exposure or clock verification",
            "Durable independent nonce registry",
            "Scientifically qualified six-DoF reference",
        ],

        "physical_sync_verified": False,
        "independent_source_authenticity_verified": False,
        "pose_factors_authorized": 0,
        "health_labels_generated": 0,
    }

    report = {
        "schema":
            "TRUST_ROBOT_L36_OFFLINE_INTEGRATION_FALSIFICATION_V1",

        "parent_commit": BASE,

        "implementation_sha256":
            hash_file(Path(__file__)),

        "source_sha256": {
            name: expected
            for name, (_, expected) in sources.items()
        },

        "interface_contract_sha256": None,

        "dryrun_preflight_receipt_sha256":
            hash_obj(admission),

        "dryrun_sealing_receipt_sha256":
            hash_obj(sealed),

        "offline_fixture_references": 12,
        "new_sensor_measurements": 0,

        "negative_controls_rejected": rejected,
        "negative_controls_count": len(rejected),

        "offline_preflight_gate_passed": True,
        "offline_seal_gate_passed": True,

        "simulator_launch_authorized": False,

        "software_clock_is_trusted_physical_time":
            False,

        "independent_source_authenticity_verified":
            False,

        "hardware_attestation_verified": False,
        "physical_sync_verified": False,
        "independent_6dof_reference_verified": False,

        "pose_factors_authorized": 0,
        "health_labels_generated": 0,

        "raw_sources_modified": False,
        "git_commit_or_push_performed": False,
    }

    out_contract = Path(args.outputcontract)
    out_report = Path(args.outputreport)

    need(
        not out_contract.exists()
        and not out_report.exists(),
        "Output collision",
    )

    out_contract.write_text(
        json.dumps(
            contract,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        ) + "\n",
        encoding="utf-8",
    )

    report["interface_contract_sha256"] = hash_file(
        out_contract
    )

    out_report.write_text(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        ) + "\n",
        encoding="utf-8",
    )

    print("L36_INTERFACE_CONTRACT=GENERATED")
    print("L36_OFFLINE_PREFLIGHT_AND_SEAL=PASS")
    print("L36_ADVERSARIAL_CONTROLS=", len(rejected))
    print("L36_NEW_SENSOR_MEASUREMENTS=0")
    print("L36_SIMULATOR_LAUNCH_AUTHORIZED=NO")
    print("L36_OFFLINE_GATE_FALSIFICATION=PASS")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("--contract", required=True)
    parser.add_argument("--l35report", required=True)
    parser.add_argument("--l35transcript", required=True)
    parser.add_argument("--outputcontract", required=True)
    parser.add_argument("--outputreport", required=True)

    main(parser.parse_args())
