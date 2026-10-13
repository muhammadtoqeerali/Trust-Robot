"""M2DGR source and frozen-feature admission for TRUST-ROBOT.

This is a read-only, fail-closed bridge from the published M2DGR
inventory and SE3 low-level feature record format.

It does not perform cross-modal temporal association, interpolation,
pose estimation, calibration, ground-truth scoring, learned health
inference, or information weighting.

It explicitly distinguishes structural recording admissibility from
scientifically qualified factor execution.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from trust_robot.se3_multimodal_feature_extraction import (
    FEATURE_RECORD_SCHEMA,
    feature_names_for_stream,
)

SCHEMA = "TRUST_ROBOT_M2DGR_SENSOR_ADMISSION_DEV_V1"

CAMERA = "/camera/color/image_raw/compressed"
CAMERA_IMU = "/camera/imu"
BODY_IMU = "/handsfree/imu"
LIDAR = "/velodyne_points"

FEATURE_STREAMS = frozenset((CAMERA, CAMERA_IMU, BODY_IMU))
INPUT_STREAMS = frozenset((CAMERA, CAMERA_IMU, BODY_IMU, LIDAR))

# These are the existing frozen manifest file hashes, not new
# measurements, calibration choices, or authorization tokens.
BOUND_FILES = {
    "manifests/m2dgr_trajectory_manifest_v1_split_freeze_v1.json":
        "017a388ef1ce4ad30812669632a022ca37c084871bc949693fd9c0541014238f",
    "manifests/m2dgr_calibration_evidence_v1.json":
        "dd4d4a8a3424460e93ad8a568499da4d94a537457812ae33f096dd7caef823a2",
    "manifests/m2dgr_reference_temporal_association_evidence_v1.json":
        "4f6580c6a0b06b4089990adcc700b5d823a748bacacfc0f00c3dd3b4169d9117",
}

SPLIT_EVIDENCE = "manifests/m2dgr_split_freeze_evidence_v1.json"

RECORD_FIELDS = frozenset((
    "schema", "trajectory_id", "split_role", "source_stream_id",
    "modality", "selected_reader_index", "stream_index",
    "bag_record_time_ns", "header_stamp_ns", "feature_values",
))


class SensorAdmissionError(ValueError):
    """Invalid input or unavailable scientific authorization."""


def digest(data):
    return hashlib.sha256(data).hexdigest()


def _json_file(root, relative, expected_hash=None):
    root = Path(root).resolve()
    path = root / relative

    if (
        not path.is_file()
        or path.is_symlink()
        or path.resolve() != root / relative
    ):
        raise SensorAdmissionError(
            "Missing or unsafe source evidence: " + relative
        )

    blob = path.read_bytes()

    if expected_hash is not None and digest(blob) != expected_hash:
        raise SensorAdmissionError(
            "Frozen source evidence hash mismatch: " + relative
        )

    try:
        return json.loads(blob)
    except (ValueError, UnicodeDecodeError) as exc:
        raise SensorAdmissionError(
            "Invalid source evidence JSON"
        ) from exc


def load_frozen_snapshot(repo):
    """Load the existing scientific boundary without modifying it."""
    data = {
        relative: _json_file(repo, relative, sha)
        for relative, sha in BOUND_FILES.items()
    }

    trajectory = data[
        "manifests/m2dgr_trajectory_manifest_v1_split_freeze_v1.json"
    ]
    calibration = data[
        "manifests/m2dgr_calibration_evidence_v1.json"
    ]
    reference = data[
        "manifests/m2dgr_reference_temporal_association_evidence_v1.json"
    ]
    split = _json_file(repo, SPLIT_EVIDENCE)

    if (
        trajectory.get("dataset_id") != "M2DGR"
        or calibration.get("dataset_id") != "M2DGR"
        or reference.get("dataset_id") != "M2DGR"
        or split.get("dataset_id") != "M2DGR"
    ):
        raise SensorAdmissionError("Dataset identity mismatch")

    assignment = split["split_assignment"]
    categories = (
        "train", "validation_calibration", "confirmation_test"
    )

    if set(assignment) != set(categories):
        raise SensorAdmissionError("Unexpected frozen split categories")

    assigned = {}
    for role in categories:
        for name in assignment[role]:
            if name in assigned:
                raise SensorAdmissionError(
                    "Trajectory reused across frozen splits"
                )
            assigned[name] = role

    records = trajectory["records"]

    if len(records) != 36 or len(assigned) != 36:
        raise SensorAdmissionError("Frozen trajectory count mismatch")

    by_id = {}

    for record in records:
        name = record["trajectory_id"]

        if (
            name in by_id
            or name not in assigned
            or record["split"] != assigned[name]
            or record["base_trajectory_id"] != name
        ):
            raise SensorAdmissionError(
                "Trajectory identity or split violation"
            )

        streams = record["streams"]
        sync = record["synchronization"]

        names = [item["stream_id"] for item in streams]
        sync_names = [item["stream_id"] for item in sync]

        if (
            len(names) != len(set(names))
            or len(sync_names) != len(set(sync_names))
            or set(names) != set(sync_names)
            or not set(names).issubset(INPUT_STREAMS)
        ):
            raise SensorAdmissionError(
                "Stream/synchronization inventory mismatch"
            )

        for stream in streams:
            if (
                stream["reference_only"] is not False
                or stream["estimator_input"] is not True
                or stream["timestamp_unit"] != "nanoseconds"
                or not isinstance(stream["frame_id"], str)
                or not stream["frame_id"]
            ):
                raise SensorAdmissionError(
                    "Invalid estimator source stream contract"
                )

        for entry in sync:
            if (
                entry["verification_status"] != "unverified"
                or entry["measurement_time_basis"]
                   != "sensor_header_stamp"
                or entry["fixed_offset_seconds"] is not None
                or entry["tolerance_seconds"] is not None
                or entry["tolerance_selected_on_split"] is not None
            ):
                raise SensorAdmissionError(
                    "Unexpected physical time qualification"
                )

        by_id[name] = record

    if (
        calibration["interpretation"]["dataset_calibration_verified"]
        is not False
        or calibration["policy"]["evaluation_ready"] is not False
        or reference["policy"][
            "reference_to_estimator_temporal_association_verified"
        ] is not False
        or reference["policy"]["evaluation_ready"] is not False
        or split["authorization"]["split_frozen"] is not True
        or split["authorization"]["estimator_scoring_authorized"]
        is not False
    ):
        raise SensorAdmissionError(
            "Frozen scientific boundary has unexpectedly changed"
        )

    return {
        "schema": SCHEMA,
        "by_id": by_id,
        "split_assignment": assignment,
        "scientific_gates": {
            "sensor_synchronization_verified": False,
            "sensor_extrinsics_independently_verified": False,
            "reference_temporal_association_verified": False,
            "estimator_scoring_authorized": False,
            "camera_relative_motion_factor_qualified": False,
            "real_sensor_factor_execution_authorized": False,
        },
        "bound_files_sha256": dict(BOUND_FILES),
    }


def inventory(snapshot):
    """Summarize existing stream availability, not raw sensor data."""
    by_id = snapshot["by_id"]

    counts = {"camera": 0, "imu": 0, "lidar": 0}
    streams = {name: 0 for name in sorted(INPUT_STREAMS)}
    camera_missing = []

    for name, trajectory in sorted(by_id.items()):
        items = {x["stream_id"] for x in trajectory["streams"]}

        for stream in items:
            streams[stream] += 1

        modalities = {
            row["modality"] for row in trajectory["streams"]
        }

        for modality in counts:
            counts[modality] += modality in modalities

        if CAMERA not in items:
            camera_missing.append(name)

    return {
        "schema": SCHEMA,
        "dataset_id": "M2DGR",
        "trajectory_count": len(by_id),
        "frozen_split_counts": {
            role: len(ids)
            for role, ids in snapshot["split_assignment"].items()
        },
        "modality_trajectory_counts": counts,
        "stream_trajectory_counts": streams,
        "camera_missing_trajectories": camera_missing,
        "scientific_gates": dict(snapshot["scientific_gates"]),
        "raw_sensor_data_opened": False,
        "cross_modal_alignment_performed": False,
        "real_sensor_factors_constructed": False,
        "independent_reference_scored": False,
    }


def require_real_factor_execution(snapshot, trajectory_id):
    """The existing frozen M2DGR evidence does not authorize fusion.

    This API intentionally has no boolean override. A future,
    independently verified and versioned protocol must supply
    a different qualified implementation.
    """
    if trajectory_id not in snapshot["by_id"]:
        raise SensorAdmissionError("Unknown trajectory")

    raise SensorAdmissionError(
        "Real sensor factor execution blocked: physical capture timing, "
        "cross-sensor calibration and approved association remain unverified"
    )


def audit_feature_records(snapshot, trajectory_id, stream_id, records):
    """Admit existing frozen SE3 diagnostics for training-only inspection.

    Header timestamps are characterized individually. No samples are
    time-matched between streams, and bag-record times are never used
    as replacement measurement timestamps.

    Lidar has its own existing diagnostic frontend and cannot be
    represented as a camera/IMU SE3 feature record.
    """
    if trajectory_id not in snapshot["by_id"]:
        raise SensorAdmissionError("Unknown trajectory")

    trajectory = snapshot["by_id"][trajectory_id]

    if trajectory["split"] != "train":
        raise SensorAdmissionError(
            "Frozen SE3 feature record execution is train-only"
        )

    if stream_id not in FEATURE_STREAMS:
        raise SensorAdmissionError(
            "No frozen camera/IMU feature contract for stream"
        )

    source = {
        row["stream_id"]: row
        for row in trajectory["streams"]
    }.get(stream_id)

    if source is None:
        raise SensorAdmissionError(
            "Requested source absent from trajectory"
        )

    features = feature_names_for_stream(stream_id)
    expected_modality = source["modality"]

    seen = 0
    header_present = 0
    header_missing = 0
    header_reversals = 0

    first_header = None
    last_header = None
    previous_header = None
    previous_reader = None

    hasher = hashlib.sha256()

    for item in records:
        if type(item) is not dict or set(item) != RECORD_FIELDS:
            raise SensorAdmissionError(
                "Feature record schema/fields mismatch"
            )

        if (
            item["schema"] != FEATURE_RECORD_SCHEMA
            or item["trajectory_id"] != trajectory_id
            or item["split_role"] != "train"
            or item["source_stream_id"] != stream_id
            or item["modality"] != expected_modality
        ):
            raise SensorAdmissionError(
                "Feature record provenance mismatch"
            )

        if type(item["stream_index"]) is not int or (
            item["stream_index"] != seen
        ):
            raise SensorAdmissionError(
                "Feature indices must be contiguous"
            )

        reader = item["selected_reader_index"]
        bag_time = item["bag_record_time_ns"]
        header = item["header_stamp_ns"]

        if (
            type(reader) is not int or reader < 0
            or type(bag_time) is not int or bag_time < 0
            or (
                previous_reader is not None
                and reader <= previous_reader
            )
        ):
            raise SensorAdmissionError(
                "Invalid stream chronology/provenance"
            )

        if header is not None and (
            type(header) is not int or header < 0
        ):
            raise SensorAdmissionError(
                "Invalid sensor header timestamp"
            )

        values = item["feature_values"]

        if (
            type(values) is not list
            or len(values) != len(features)
            or any(
                type(v) not in (int, float)
                or not math.isfinite(float(v))
                for v in values
            )
        ):
            raise SensorAdmissionError(
                "Invalid frozen diagnostic feature vector"
            )

        if header is None:
            header_missing += 1
        else:
            header_present += 1
            if first_header is None:
                first_header = header
            last_header = header

            if previous_header is not None and header < previous_header:
                header_reversals += 1

            previous_header = header

        blob = json.dumps(
            item,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8") + b"\n"

        hasher.update(blob)
        previous_reader = reader
        seen += 1

        if seen > 20000:
            raise SensorAdmissionError(
                "Bounded feature batch exceeded"
            )

    if seen == 0:
        raise SensorAdmissionError("Empty feature batch")

    return {
        "schema": SCHEMA,
        "trajectory_id": trajectory_id,
        "split_role": "train",
        "stream_id": stream_id,
        "modality": expected_modality,
        "feature_names": list(features),
        "record_count": seen,
        "header_present_count": header_present,
        "header_missing_count": header_missing,
        "header_strict_reversal_count": header_reversals,
        "first_observed_header_ns": first_header,
        "last_observed_header_ns": last_header,
        "canonical_records_sha256": hasher.hexdigest(),
        "status": "SINGLE_STREAM_DIAGNOSTICS_ONLY",
        "bag_record_time_used_as_measurement_time": False,
        "cross_modal_temporal_association_performed": False,
        "relative_motion_factor_created": False,
        "estimator_factor_execution_authorized": False,
        "health_labels_created": False,
        "ground_truth_used": False,
    }
