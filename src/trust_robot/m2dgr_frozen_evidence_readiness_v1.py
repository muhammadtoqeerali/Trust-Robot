"""R135-A22: frozen M2DGR metadata admission-boundary review.

Reads exactly eight pinned, repository-tracked JSON metadata
artifacts. Does not load ROS bags, trajectory samples, images,
sensor messages, ground-truth poses or dataset files.

Reports current documented scientific blockers. It never
authorizes physical localization, factor execution, scoring,
health inference or confirmation-test selection.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from trust_robot.analytic_15d_evidence_review_v1 import (
    BLOCKED_CAPABILITIES,
    STATUS as A21_STATUS,
)

SCHEMA = "TRUST_ROBOT_R135_A22_M2DGR_READINESS_V1"
STATUS = "METADATA_ONLY_ALL_ADMISSION_GATES_CLOSED"

ROOT = Path(__file__).resolve().parents[2]

# These are published logical content digests, not
# invented calibration or synchronization evidence.
SOURCES = {
    "CALIBRATION": (
        "manifests/m2dgr_calibration_evidence_v1.json",
        "TRUST_ROBOT_M2DGR_CALIBRATION_EVIDENCE_V1",
        "81b430950c274840c5611f76e9cd0d5be18382f884d1b7870e7d827bd5bdc3b6",
    ),
    "SYNCHRONIZATION": (
        "manifests/m2dgr_synchronization_evidence_v1.json",
        "TRUST_ROBOT_M2DGR_SYNCHRONIZATION_EVIDENCE_V1",
        "a4e3e8dd18970a47f5cb50f4bb8ea3cb0e625f5f51d9eb0028bf34d953ee9966",
    ),
    "SPLIT": (
        "manifests/m2dgr_split_freeze_evidence_v1.json",
        "TRUST_ROBOT_M2DGR_SPLIT_FREEZE_EVIDENCE_V1",
        "bc5699504efda7203165adb9b1ceaa62f2639288011cdb875df0a870ee068a2e",
    ),
    "REFERENCE_PHYSICAL": (
        "manifests/m2dgr_reference_physical_semantics_evidence_v1.json",
        "TRUST_ROBOT_M2DGR_REFERENCE_PHYSICAL_SEMANTICS_EVIDENCE_V1",
        "559598c00c8246c1626ae2e01279b59d7baad724a7919df3d4c7a5d5b96ca0a0",
    ),
    "REFERENCE_TEMPORAL": (
        "manifests/m2dgr_reference_temporal_association_evidence_v1.json",
        "TRUST_ROBOT_M2DGR_REFERENCE_TEMPORAL_ASSOCIATION_EVIDENCE_V1",
        "505c1b63fc7e74907ce915472b243230a2cc86017248edaca255b5be5bc079fd",
    ),
    "PROTOCOL_V2": (
        "configs/trust_robot/m2dgr_trajectory_association_evaluation_protocol_candidate_v2.json",
        "TRUST_ROBOT_M2DGR_TRAJECTORY_ASSOCIATION_EVALUATION_PROTOCOL_CANDIDATE_V2",
        "8f60fa3a2303d6a2b8ad8d74719439358e2f7b19ca834c77e6cf09aa1889efbc",
    ),
    "CAMERA_IMU_SYNC": (
        "manifests/m2dgr_camera_imu_synchronization_evidence_v1.json",
        "TRUST_ROBOT_M2DGR_CAMERA_IMU_SYNCHRONIZATION_EVIDENCE_V1",
        "d765f8ac13ff21dca23e289efef65fed31372189363e7fa61982e122514e190b",
    ),
    "LIDAR_IMU_SYNC": (
        "manifests/m2dgr_lidar_imu_synchronization_evidence_v1.json",
        "TRUST_ROBOT_M2DGR_LIDAR_IMU_SYNCHRONIZATION_EVIDENCE_V1",
        "ec5fbed1a386dd17e58fd05df500a45ee0ff4fc1ff40286f08d67410b3ce7c10",
    ),
}


FROZEN_GIT_BLOBS = {
    "CALIBRATION":
        "1f75cab4faa3e1222dca620f63dbc63e1a916679",
    "SYNCHRONIZATION":
        "3c426645987dff5562a590317b22737b1d0c6a3c",
    "SPLIT":
        "747b35492a94f40f15758d97e5593f257957fafc",
    "REFERENCE_PHYSICAL":
        "b1bdac6eda5c4ccc2d552ea5ee665b1bc7dd1984",
    "REFERENCE_TEMPORAL":
        "b0bd6e5ee2f056d25cd8ad07a69f910953ebca76",
    "PROTOCOL_V2":
        "2abc50dd4443a093edfa49d44c7a14d8a92082a8",
    "CAMERA_IMU_SYNC":
        "21f99eae9ffc39c500fadbe3b164870805a6b792",
    "LIDAR_IMU_SYNC":
        "2d237820783cd02be4e668b77464b412f1f02bb8",
}


# Diagnostic evidence checks, NOT aliases for the
# eleven original scientific admission gates.
BLOCKER_CHECKS = (
    ("dataset_calibration",
     "CALIBRATION",
     ("interpretation", "dataset_calibration_verified")),
    ("camera_intrinsics",
     "CALIBRATION",
     ("interpretation", "camera_intrinsics_verified")),
    ("camera_lidar_extrinsics",
     "CALIBRATION",
     ("interpretation", "camera_lidar_extrinsic_verified")),
    ("physical_capture_synchronization",
     "SYNCHRONIZATION",
     ("policy", "physical_capture_synchronization_verified")),
    ("camera_imu_synchronization",
     "CAMERA_IMU_SYNC",
     ("policy", "physical_capture_synchronization_verified")),
    ("lidar_imu_synchronization",
     "LIDAR_IMU_SYNC",
     ("policy", "physical_capture_synchronization_verified")),
    ("reference_temporal_association",
     "REFERENCE_TEMPORAL",
     ("policy", "reference_to_estimator_temporal_association_verified")),
    ("reference_timestamp_event",
     "REFERENCE_PHYSICAL",
     ("interpretation", "reference_timestamp_physical_measurement_event_verified")),
    ("mocap_lidar_extrinsic",
     "REFERENCE_PHYSICAL",
     ("interpretation", "mocap_to_lidar_transform_verified")),
    ("estimator_scoring",
     "PROTOCOL_V2",
     ("authorization", "estimator_scoring_authorized")),
    ("evaluation_readiness",
     "PROTOCOL_V2",
     ("authorization", "evaluation_ready")),
)


class MetadataReadinessError(ValueError):
    """Frozen evidence mismatch or unauthorized state."""


def _require(condition, message):
    if not condition:
        raise MetadataReadinessError(message)


def _field(document, path):
    current = document

    for key in path:
        _require(
            type(current) is dict and key in current,
            "Missing frozen metadata field: " + "/".join(path),
        )
        current = current[key]

    return current


def load_frozen_snapshot():
    """Read only eight repository-local metadata JSON objects."""
    documents = {}
    file_digests = {}

    for alias, (relative, _, _) in SOURCES.items():
        target = ROOT / relative

        _require(
            target.is_file()
            and not target.is_symlink()
            and target.resolve().is_relative_to(ROOT.resolve())
            and target.suffix == ".json"
            and 0 < target.stat().st_size < 128000,
            "Metadata file boundary violation",
        )

        raw = target.read_bytes()

        git_blob = hashlib.sha1(
            b"blob "
            + str(len(raw)).encode("ascii")
            + b"\0"
            + raw
        ).hexdigest()

        _require(
            git_blob == FROZEN_GIT_BLOBS[alias],
            "Frozen metadata bytes changed: " + alias,
        )

        file_digests[alias] = hashlib.sha256(raw).hexdigest()

        try:
            data = json.loads(raw)
        except (ValueError, UnicodeDecodeError) as exc:
            raise MetadataReadinessError(
                "Malformed frozen metadata"
            ) from exc

        documents[alias] = data

    return documents, file_digests


def review_snapshot(documents, file_digests):
    """Check published evidence semantics without admitting data."""
    _require(
        type(documents) is dict
        and set(documents) == set(SOURCES),
        "Incomplete or unexpected metadata source set",
    )

    _require(
        type(file_digests) is dict
        and set(file_digests) == set(SOURCES)
        and all(
            type(digest) is str and len(digest) == 64
            for digest in file_digests.values()
        ),
        "Incomplete metadata file identity receipt",
    )

    for alias, (_, schema, logical_digest) in SOURCES.items():
        value = documents[alias]

        _require(
            type(value) is dict
            and value.get("dataset_id") == "M2DGR"
            and value.get("schema") == schema
            and value.get("content_sha256") == logical_digest,
            "Frozen evidence identity mismatch: " + alias,
        )

    blockers = {}

    for name, alias, path in BLOCKER_CHECKS:
        actual = _field(documents[alias], path)

        _require(
            actual is False,
            "Scientific blocker unexpectedly cleared: " + name,
        )
        blockers[name] = "UNRESOLVED"

    split = documents["SPLIT"]
    protocol = documents["PROTOCOL_V2"]

    counts = split["split_counts"]

    _require(
        counts == {
            "train": 22,
            "validation_calibration": 7,
            "confirmation_test": 7,
        }
        and split["authorization"]["split_frozen"] is True
        and split["authorization"][
            "estimator_scoring_authorized"
        ] is False,
        "Frozen M2DGR split contract changed",
    )

    assignment = split["split_assignment"]
    roles = (
        "train",
        "validation_calibration",
        "confirmation_test",
    )

    _require(
        all(
            len(assignment[role]) == counts[role]
            and len(set(assignment[role]))
            == counts[role]
            for role in roles
        ),
        "Invalid frozen trajectory inventory",
    )

    all_ids = [
        trajectory
        for role in roles
        for trajectory in assignment[role]
    ]

    _require(
        len(all_ids) == 36
        and len(set(all_ids)) == 36,
        "M2DGR trajectory split overlap",
    )

    holdout = split["prospective_holdout_policy"]

    _require(
        holdout[
            "confirmation_test_pristine_from_all_prior_dataset_inspection"
        ] is False
        and holdout[
            "confirmation_test_available_for_future_model_selection"
        ] is False
        and holdout[
            "confirmation_test_available_for_future_threshold_selection"
        ] is False
        and holdout[
            "confirmation_test_available_for_future_alignment_selection"
        ] is False
        and holdout[
            "confirmation_test_available_for_future_association_selection"
        ] is False,
        "Confirmation-test policy was weakened",
    )

    _require(
        type(holdout["reason_not_pristine"]) is str
        and len(holdout["reason_not_pristine"]) > 20,
        "Prior dataset-inspection caveat missing",
    )

    authorization = protocol["authorization"]

    _require(
        authorization["confirmation_test_partition_closed"]
        is True
        and authorization["split_selection_complete"] is True
        and authorization["association_execution_authorized"]
        is False
        and authorization["alignment_execution_authorized"]
        is False
        and authorization["trajectory_scoring_authorized"]
        is False
        and authorization["metric_computation_authorized"]
        is False
        and authorization["reference_interpolation_authorized"]
        is False,
        "Executable evaluation authorization changed",
    )

    temporal = protocol["temporal_association"]
    alignment = protocol["frame_alignment"]
    interval = protocol["evaluation_interval"]

    _require(
        temporal["selected_method"] == "unselected"
        and temporal["association_tolerance_seconds"] is None
        and temporal["nearest_neighbor_authorized"] is False
        and alignment["selected_mode"] == "unselected"
        and alignment["reference_frame_transform_verified"]
        is False
        and interval["selected_policy"] == "unselected"
        and interval["created"] is False,
        "An unresolved evaluation choice was selected",
    )

    fields = protocol["required_provenance"]

    # Protocol V2 stores the seventeen requirements as
    # a mapping of field names to required=True flags.
    _require(
        type(fields) is dict
        and len(fields) == 17
        and all(
            type(name) is str
            and bool(name)
            and required is True
            for name, required in fields.items()
        ),
        "Frozen provenance field inventory changed",
    )

    for alias in (
        "CALIBRATION",
        "SYNCHRONIZATION",
        "CAMERA_IMU_SYNC",
        "LIDAR_IMU_SYNC",
        "REFERENCE_TEMPORAL",
    ):
        _require(
            documents[alias]["policy"]["evaluation_ready"]
            is False,
            "Frozen sensor evidence promoted without proof",
        )

    return {
        "schema": SCHEMA,
        "status": STATUS,
        "source_A21_status": A21_STATUS,
        "source_commit":
            "360c9e78d3885ce265152d221ac693a2601b3135",
        "metadata_source_count": 8,
        "metadata_file_sha256": dict(sorted(file_digests.items())),
        "metadata_logical_sha256": {
            alias: values[2]
            for alias, values in SOURCES.items()
        },
        "explicit_diagnostic_blocker_count": len(blockers),
        "diagnostic_blockers": blockers,
        "diagnostic_checks_are_original_eleven_gates": False,
        "original_m2dgr_scientific_gates_closed": 11,
        "split_counts": dict(counts),
        "frozen_trajectory_count": 36,
        "confirmation_test_prospectively_closed": True,
        "confirmation_test_pristine_from_prior_inspection": False,
        "confirmation_test_prior_inspection_caveat":
            holdout["reason_not_pristine"],
        "required_provenance_field_count": len(fields),
        "required_provenance_field_names": sorted(fields),
        "association_method_selected": False,
        "association_tolerance_selected": False,
        "alignment_mode_selected": False,
        "evaluation_interval_selected": False,
        "recorded_data_read": False,
        "recorded_ground_truth_read": False,
        "trajectory_scoring_performed": False,
        "physical_calibration_verified": False,
        "physical_synchronization_verified": False,
        "health_inference_performed": False,
        "real_factor_execution_authorized": False,
        "scientific_permissions": {
            key: "BLOCKED"
            for key in BLOCKED_CAPABILITIES
        },
        "decision": "NO_ADMISSION",
    }


def run_review():
    """Load frozen metadata and issue a non-executable decision."""
    documents, hashes = load_frozen_snapshot()
    return review_snapshot(documents, hashes)


def report_sha256(report):
    _require(
        type(report) is dict
        and report.get("schema") == SCHEMA
        and report.get("decision") == "NO_ADMISSION"
        and report.get(
            "original_m2dgr_scientific_gates_closed"
        ) == 11,
        "Invalid metadata-readiness report",
    )

    return hashlib.sha256(
        json.dumps(
            report,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()
