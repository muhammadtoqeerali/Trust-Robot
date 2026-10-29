"""R135-A23: prospective independent physical-evidence requests.

This module constructs an unfulfilled evidence-request packet
from the frozen A22 readiness audit and the original L33
prospective acquisition proposal.

It never accepts or qualifies physical measurements, performs
sensor capture, opens dataset files, selects synchronization
parameters, authorizes health inference or executes factors.

The packet is an engineering planning artifact only.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from trust_robot.m2dgr_frozen_evidence_readiness_v1 import (
    run_review as run_a22,
    BLOCKER_CHECKS,
)

from trust_robot.analytic_15d_evidence_review_v1 import (
    BLOCKED_CAPABILITIES,
)

SCHEMA = "TRUST_ROBOT_R135_A23_PROSPECTIVE_EVIDENCE_PACKET_V1"
STATUS = "REQUEST_ONLY_NO_PHYSICAL_QUALIFICATION"

ROOT = Path(__file__).resolve().parents[2]

L33_PATH = (
    "experiments/"
    "isaacsim_v16_l31_l35_provenance_witness_v1/"
    "evidence/l33_prospective_acquisition_contract.json"
)

PACKET_PATH = (
    "configs/trust_robot/"
    "m2dgr_prospective_evidence_packet_v1.json"
)

L33_BLOB = "e597d61008105ef3cfa32ec441b4fb132380f9e6"

A22_COMMIT = "92b4f91981b091399d7d7e28434a3e2f54d9b2e5"

STAGES = (
    ("A", "source_provenance"),
    ("B", "exposure_timing_and_calibration"),
    ("C", "independent_six_dof_reference"),
    ("D", "prospective_heldout_validation"),
)

# Request ID, acquisition stage, A22 diagnostic blocker,
# independently needed fact, proposed independent witness,
# and a specifically insufficient substitute.
#
# These are proposals; none is a completed receipt.
REQUEST_SPECS = (
    (
        "A01", "A", None,
        "Pre-capture challenge bound to session identity and source bytes",
        "Witness independent of the capture writer",
        "Self-declared session identifier or self-signed nonce",
    ),
    (
        "A02", "A", None,
        "Physical device identity and acquisition configuration provenance",
        "Manufacturer-backed identity plus independent capture review",
        "Network address, synthetic source name or firmware alone",
    ),
    (
        "B01", "B", "dataset_calibration",
        "Capture-applicable full metric calibration with uncertainty",
        "Independent calibration and coordinate-frame reviewer",
        "Published calibration file integrity alone",
    ),
    (
        "B02", "B", "camera_intrinsics",
        "Camera intrinsic model and capture-applicable configuration",
        "Independent optical calibration evidence",
        "Author metadata or guessed camera parameters",
    ),
    (
        "B03", "B", "camera_lidar_extrinsics",
        "Metric camera-to-LiDAR transform and direction convention",
        "Independent geometric calibration and transform verification",
        "Transform copied from a synthetic common motion model",
    ),
    (
        "B04", "B", "physical_capture_synchronization",
        "Physical event-time definitions and cross-clock uncertainty",
        "Independent clock-domain and capture-event witness",
        "Matching ROS epochs or numerical header equality",
    ),
    (
        "B05", "B", "camera_imu_synchronization",
        "Camera exposure-to-IMU sample time relationship",
        "Independent exposure and inertial clock measurement",
        "High visual-gyro correlation or fitted lag alone",
    ),
    (
        "B06", "B", "lidar_imu_synchronization",
        "LiDAR firing-to-IMU event timing and uncertainty",
        "Independent firing-time and inertial clock measurement",
        "Point-time tiling or ICP/gyro agreement alone",
    ),
    (
        "C01", "C", "reference_temporal_association",
        "Reference-to-estimator physical time correspondence",
        "Independent reference clock and event validation",
        "Nearest-neighbor pairing selected to improve ATE",
    ),
    (
        "C02", "C", "reference_timestamp_event",
        "Exact event and origin represented by each reference timestamp",
        "Independent reference-system documentation and witness",
        "Numeric timestamp overlap or export format alone",
    ),
    (
        "C03", "C", "mocap_lidar_extrinsic",
        "Tracked-body origin and verified transform to LiDAR",
        "Independent mocap/reference geometry verification",
        "Assumed shared sensor origin or visual alignment alone",
    ),
    (
        "D01", "D", "estimator_scoring",
        "Predeclared scoring policy supported by valid reference evidence",
        "Independent protocol reviewer before held-out use",
        "Optimizer convergence or baseline-relative position change",
    ),
    (
        "D02", "D", "evaluation_readiness",
        "Complete validated evaluation provenance and locked selection",
        "Independent assessment with held-out selection separation",
        "Complete field names without verified physical values",
    ),
)


class EvidencePacketError(ValueError):
    """Unverified acquisition proposal or packet mutation."""


def _require(ok, message):
    if not ok:
        raise EvidencePacketError(message)


def _git_blob(raw):
    return hashlib.sha1(
        b"blob "
        + str(len(raw)).encode("ascii")
        + b"\0"
        + raw
    ).hexdigest()


def _canonical_bytes(document):
    return json.dumps(
        document,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
        ensure_ascii=True,
    ).encode("ascii")


def _load_l33():
    path = ROOT / L33_PATH

    _require(
        path.is_file()
        and not path.is_symlink()
        and path.resolve().is_relative_to(ROOT.resolve())
        and 0 < path.stat().st_size < 50000,
        "L33 frozen source boundary violation",
    )

    raw = path.read_bytes()

    _require(
        _git_blob(raw) == L33_BLOB,
        "L33 source bytes changed",
    )

    try:
        data = json.loads(raw)
    except (ValueError, UnicodeDecodeError) as exc:
        raise EvidencePacketError(
            "Malformed L33 source contract"
        ) from exc

    _require(
        type(data) is dict
        and data["schema"]
        == "TRUST_ROBOT_L33_PROSPECTIVE_ACQUISITION_CONTRACT_V1"
        and data["protocol_status"]
        == "ENGINEERING_PROPOSAL_NOT_SCIENTIFIC_QUALIFICATION"
        and data["source_authenticity_verified"] is False
        and data["physical_exposure_sync_verified"] is False
        and data["independent_reference_verified"] is False
        and data["calibrated_health_probabilities"] is False
        and data["health_labels_generated"] == 0
        and data["pose_factors_authorized"] == 0,
        "L33 scientific denials changed",
    )

    observed = data["future_capture_stages"]

    _require(
        type(observed) is list
        and tuple(
            (stage["stage"], stage["name"])
            for stage in observed
        ) == STAGES
        and all(
            stage["qualification"] == "NOT_YET_VERIFIED"
            and type(stage["required"]) is list
            and len(stage["required"]) >= 2
            for stage in observed
        ),
        "L33 acquisition stages changed",
    )

    return data


def build_packet():
    """Construct a deterministic, unfulfilled request packet."""
    a22 = run_a22()
    l33 = _load_l33()

    _require(
        a22["decision"] == "NO_ADMISSION"
        and a22["metadata_source_count"] == 8
        and a22["explicit_diagnostic_blocker_count"] == 11
        and a22["original_m2dgr_scientific_gates_closed"]
        == 11
        and a22["required_provenance_field_count"] == 17
        and a22[
            "confirmation_test_pristine_from_prior_inspection"
        ] is False
        and all(
            state == "UNRESOLVED"
            for state in a22["diagnostic_blockers"].values()
        ),
        "Frozen A22 readiness decision changed",
    )

    blockers = set(a22["diagnostic_blockers"])

    _require(
        blockers == {
            entry[0] for entry in BLOCKER_CHECKS
        },
        "Readiness diagnostics changed",
    )

    _require(
        len(REQUEST_SPECS) == 13
        and len({r[0] for r in REQUEST_SPECS}) == 13
        and set(
            row[2]
            for row in REQUEST_SPECS
            if row[2] is not None
        ) == blockers
        and len([
            row for row in REQUEST_SPECS
            if row[2] is None
        ]) == 2,
        "Incomplete or duplicate evidence crosswalk",
    )

    requests = []

    for ident, stage, blocker, fact, witness, surrogate in (
        REQUEST_SPECS
    ):
        _require(
            stage in {name for name, _ in STAGES}
            and all(
                type(value) is str and value
                for value in (
                    ident, stage, fact, witness, surrogate
                )
            ),
            "Invalid prospective evidence request",
        )

        requests.append({
            "request_id": ident,
            "stage": stage,
            "a22_diagnostic_blocker": blocker,
            "physical_fact_required": fact,
            "independent_witness_required": witness,
            "insufficient_substitute": surrogate,
            "request_status": "UNFULFILLED",
            "independent_review_status": "NOT_YET_VERIFIED",
            "capture_session_identity": None,
            "evidence_artifact_sha256": None,
            "physical_parameter_value": None,
            "qualifying_receipt_received": False,
            "scientific_gate_opened": False,
        })

    stage_rows = []

    for index, (stage, name) in enumerate(STAGES):
        previous = [
            item[0] for item in STAGES[:index]
        ]

        stage_rows.append({
            "stage": stage,
            "name": name,
            "l33_qualification": "NOT_YET_VERIFIED",
            "stage_authorized": False,
            "completed_independent_receipts": 0,
            "previous_stages_to_verify": previous,
            "prospective_request_ids": [
                row["request_id"]
                for row in requests
                if row["stage"] == stage
            ],
        })

    _require(
        all(row["prospective_request_ids"] for row in stage_rows)
        and len(requests) == sum(
            len(row["prospective_request_ids"])
            for row in stage_rows
        ),
        "Requests not assigned to acquisition stages",
    )

    return {
        "schema": SCHEMA,
        "status": STATUS,
        "prior_a22_commit": A22_COMMIT,
        "prior_a22_decision": a22["decision"],
        "l33_contract_blob": L33_BLOB,
        "l33_source_status": l33["protocol_status"],
        "physical_evidence_received": False,
        "qualified_physical_receipt_count": 0,
        "real_sensor_contact_performed": False,
        "recorded_dataset_accessed": False,
        "ground_truth_scoring_performed": False,
        "capture_time_offset_selected": False,
        "capture_time_offset_seconds": None,
        "capture_time_tolerance_selected": False,
        "capture_time_tolerance_seconds": None,
        "physical_extrinsics_verified": False,
        "physical_reference_verified": False,
        "health_inference_authorized": False,
        "factor_weights_modified": False,
        "real_factor_execution_authorized": False,
        "original_m2dgr_gates_closed": 11,
        "diagnostic_checks_are_original_gates": False,
        "unresolved_diagnostic_blockers":
            sorted(blockers),
        "frozen_m2dgr_split": a22["split_counts"],
        "confirmation_test_pristine_from_prior_inspection":
            False,
        "confirmation_test_prospectively_closed": True,
        "future_acquisition_is_retroactive_m2dgr_proof":
            False,
        "required_evaluation_provenance_names":
            a22["required_provenance_field_names"],
        "stages": stage_rows,
        "requests": requests,
        "scientific_permissions": {
            name: "BLOCKED"
            for name in BLOCKED_CAPABILITIES
        },
        "decision": "REQUEST_ONLY_NO_ADMISSION",
    }


def validate_packet(candidate):
    """Reject every mutation or asserted qualification."""
    _require(
        type(candidate) is dict
        and candidate == build_packet(),
        "Proposed evidence packet differs from frozen contract",
    )
    return True


def packet_sha256(packet):
    validate_packet(packet)
    return hashlib.sha256(
        _canonical_bytes(packet)
    ).hexdigest()


def load_committed_packet():
    """Read only the repository-local request JSON."""
    target = ROOT / PACKET_PATH

    _require(
        target.is_file()
        and not target.is_symlink()
        and target.resolve().is_relative_to(ROOT.resolve())
        and 0 < target.stat().st_size < 100000,
        "Request packet path is unauthorized",
    )

    try:
        payload = json.loads(target.read_bytes())
    except (ValueError, UnicodeDecodeError) as exc:
        raise EvidencePacketError(
            "Malformed request packet"
        ) from exc

    validate_packet(payload)
    return payload
