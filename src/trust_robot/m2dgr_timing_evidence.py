from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from typing import Iterable
import json
import os
import tempfile


STREAM_TIMING_SCHEMA = "trust_robot.m2dgr_phase3_stream_timing"
STREAM_TIMING_VERSION = 1
EXACT_HEADER_ANOMALY_SCHEMA = "trust_robot.m2dgr_exact_header_anomaly"
EXACT_HEADER_ANOMALY_VERSION = 1
TIMING_INDEX_SCHEMA = "TRUST_ROBOT_M2DGR_TIMING_EVIDENCE_INDEX_V1"
TIMING_INDEX_VERSION = 1

EXPECTED_TARGET_TOPICS = (
    "/camera/color/image_raw/compressed",
    "/camera/imu",
    "/handsfree/imu",
    "/velodyne_points",
)

TIMING_ARTIFACT_ROOT = Path("audit") / "phase3_staging" / "stream_timing_v1"
EXACT_ANOMALY_ROOT = Path("audit") / "phase3_staging" / "exact_anomalies"


class M2DGRTimingEvidenceError(ValueError):
    """Raised when Phase-3 M2DGR timing evidence violates its contract."""


def sha256_file(path: str | Path) -> str:
    source = Path(path)
    digest = sha256()
    with source.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _require_mapping(value: object, label: str) -> dict:
    if not isinstance(value, dict):
        raise M2DGRTimingEvidenceError(f"{label} must be a mapping")
    return value


def _require_exact_keys(payload: dict, expected: set[str], label: str) -> None:
    actual = set(payload)
    if actual != expected:
        raise M2DGRTimingEvidenceError(
            f"{label} keys mismatch: "
            f"missing={sorted(expected - actual)!r}, "
            f"extra={sorted(actual - expected)!r}"
        )


def _require_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise M2DGRTimingEvidenceError(f"{label} must be a non-empty string")
    return value


def _require_relative_path(value: object, label: str) -> str:
    text = _require_text(value, label)
    if Path(text).is_absolute():
        raise M2DGRTimingEvidenceError(f"{label} must be relative")
    return text


def _require_sha256(value: object, label: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise M2DGRTimingEvidenceError(f"{label} must be a SHA256 digest")
    try:
        int(value, 16)
    except ValueError as exc:
        raise M2DGRTimingEvidenceError(f"{label} must be hexadecimal") from exc
    return value.lower()


def _canonical_digest(payload: dict) -> str:
    unhashed = deepcopy(payload)
    unhashed.pop("index_content_sha256", None)
    raw = json.dumps(
        unhashed,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return sha256(raw).hexdigest()


def timing_artifact_path(dataset_root: str | Path, trajectory_id: str) -> Path:
    return (
        Path(dataset_root)
        / TIMING_ARTIFACT_ROOT
        / f"{trajectory_id}_phase3_stream_timing_v1.json"
    )


def validate_m2dgr_stream_timing_payload(payload: dict) -> None:
    payload = _require_mapping(payload, "stream-timing artifact root")
    _require_exact_keys(
        payload,
        {
            "schema",
            "version",
            "trajectory_id",
            "source",
            "reader",
            "policy",
            "available_target_topics",
            "missing_target_topics",
            "total_target_messages",
            "total_decode_errors",
            "common_header_range",
            "streams",
            "pairs",
        },
        "stream-timing artifact",
    )

    if payload["schema"] != STREAM_TIMING_SCHEMA:
        raise M2DGRTimingEvidenceError("unexpected stream-timing schema")
    if payload["version"] != STREAM_TIMING_VERSION:
        raise M2DGRTimingEvidenceError("unexpected stream-timing version")

    trajectory_id = _require_text(payload["trajectory_id"], "trajectory_id")

    source = _require_mapping(payload["source"], "stream-timing source")
    _require_exact_keys(
        source,
        {
            "relative_path",
            "size_bytes",
            "recorded_sha256",
            "checksum_sidecar",
            "raw_modified",
        },
        "stream-timing source",
    )
    if (
        _require_relative_path(source["relative_path"], "source relative_path")
        != f"raw/rosbags/{trajectory_id}.bag"
    ):
        raise M2DGRTimingEvidenceError(
            "stream-timing source path does not match trajectory"
        )
    if (
        _require_relative_path(source["checksum_sidecar"], "source checksum_sidecar")
        != f"checksums/{trajectory_id}.bag.sha256"
    ):
        raise M2DGRTimingEvidenceError(
            "stream-timing checksum sidecar does not match trajectory"
        )
    _require_sha256(source["recorded_sha256"], "source recorded_sha256")
    if not isinstance(source["size_bytes"], int) or source["size_bytes"] <= 0:
        raise M2DGRTimingEvidenceError(
            "source size_bytes must be a positive integer"
        )
    if source["raw_modified"] is not False:
        raise M2DGRTimingEvidenceError(
            "Phase-3 timing evidence must not modify raw data"
        )

    reader = _require_mapping(payload["reader"], "stream-timing reader")
    _require_exact_keys(
        reader,
        {
            "package",
            "version",
            "message_deserialization",
            "targeted_stream_scan",
            "image_pixels_decoded",
            "pointcloud_points_interpreted",
            "scan_completed",
        },
        "stream-timing reader",
    )
    if _require_text(reader["package"], "reader package") != "rosbags":
        raise M2DGRTimingEvidenceError(
            "Phase-3 timing evidence must identify the rosbags reader"
        )
    _require_text(reader["version"], "reader version")
    if reader["message_deserialization"] is not True:
        raise M2DGRTimingEvidenceError(
            "header timing evidence requires message deserialization"
        )
    if reader["targeted_stream_scan"] is not True:
        raise M2DGRTimingEvidenceError("expected a targeted stream scan")
    if reader["scan_completed"] is not True:
        raise M2DGRTimingEvidenceError("timing artifact is not marked complete")
    if reader["image_pixels_decoded"] is not False:
        raise M2DGRTimingEvidenceError("image pixel decoding must not be claimed")
    if reader["pointcloud_points_interpreted"] is not False:
        raise M2DGRTimingEvidenceError(
            "point-cloud point interpretation must not be claimed"
        )

    policy = _require_mapping(payload["policy"], "stream-timing policy")
    required_policy = {
        "characterization_only": True,
        "measurement_time_basis": "sensor_header_stamp",
        "bag_record_time_role": "transport_provenance_diagnostic_only",
        "nearest_neighbor_is_sync_proof": False,
        "common_range_is_sync_proof": False,
        "automatic_sample_exclusion_rule_created": False,
        "fixed_time_offset_estimated": False,
        "fixed_time_offset_applied": False,
        "synchronization_tolerance_frozen": False,
        "synchronization_verified": False,
    }
    _require_exact_keys(policy, set(required_policy), "stream-timing policy")
    for key, expected in required_policy.items():
        if policy[key] != expected:
            raise M2DGRTimingEvidenceError(
                f"unsafe or unexpected Phase-3 timing policy: "
                f"{key}={policy[key]!r}"
            )

    available = payload["available_target_topics"]
    missing = payload["missing_target_topics"]
    if not isinstance(available, list) or not isinstance(missing, list):
        raise M2DGRTimingEvidenceError(
            "available/missing target topics must be lists"
        )
    if len(available) != len(set(available)):
        raise M2DGRTimingEvidenceError(
            "available_target_topics contains duplicates"
        )
    if len(missing) != len(set(missing)):
        raise M2DGRTimingEvidenceError(
            "missing_target_topics contains duplicates"
        )

    expected = set(EXPECTED_TARGET_TOPICS)
    available_set = set(available)
    missing_set = set(missing)
    if available_set & missing_set:
        raise M2DGRTimingEvidenceError(
            "a target topic cannot be both available and missing"
        )
    if available_set | missing_set != expected:
        raise M2DGRTimingEvidenceError(
            "available/missing target topics do not partition "
            "the expected M2DGR stream set"
        )

    streams = _require_mapping(payload["streams"], "stream-timing streams")
    if set(streams) != expected:
        raise M2DGRTimingEvidenceError(
            "stream-timing artifact must contain one block "
            "for every expected target topic"
        )

    total_messages = 0
    total_decode_errors = 0

    required_stream_keys = {
        "message_count",
        "header_count",
        "decode_error_count",
        "message_types",
        "frame_ids",
        "header_time",
        "record_time",
        "record_minus_header_ms",
        "largest_header_intervals",
        "largest_absolute_record_header_offsets",
        "decode_error_examples",
        "common_header_range_diagnostic",
    }
    allowed_stream_keys = required_stream_keys | {
        "record_minus_header_sign_counts",
    }

    for topic in EXPECTED_TARGET_TOPICS:
        stream = _require_mapping(streams[topic], f"stream block {topic}")
        actual_keys = set(stream)
        if (
            not required_stream_keys.issubset(actual_keys)
            or not actual_keys.issubset(allowed_stream_keys)
        ):
            raise M2DGRTimingEvidenceError(
                f"stream block {topic} keys mismatch"
            )

        for count_name in (
            "message_count",
            "header_count",
            "decode_error_count",
        ):
            value = stream[count_name]
            if not isinstance(value, int) or value < 0:
                raise M2DGRTimingEvidenceError(
                    f"{topic} {count_name} must be a non-negative integer"
                )

        if stream["decode_error_count"] != 0:
            raise M2DGRTimingEvidenceError(
                f"{topic} contains message decode failures"
            )

        total_messages += stream["message_count"]
        total_decode_errors += stream["decode_error_count"]

        if topic in available_set:
            if stream["message_count"] <= 0 or stream["header_count"] <= 0:
                raise M2DGRTimingEvidenceError(
                    f"available topic {topic} has no decoded header samples"
                )
            header = _require_mapping(
                stream["header_time"],
                f"{topic} header_time",
            )
            for key in (
                "first_ns",
                "last_ns",
                "min_ns",
                "max_ns",
                "duplicate_count",
                "reverse_count",
                "positive_interval_ms",
            ):
                if key not in header:
                    raise M2DGRTimingEvidenceError(
                        f"{topic} header_time is missing {key!r}"
                    )
            if (
                not isinstance(header["reverse_count"], int)
                or header["reverse_count"] < 0
            ):
                raise M2DGRTimingEvidenceError(
                    f"{topic} reverse_count must be a non-negative integer"
                )
            if (
                not isinstance(header["duplicate_count"], int)
                or header["duplicate_count"] < 0
            ):
                raise M2DGRTimingEvidenceError(
                    f"{topic} duplicate_count must be a non-negative integer"
                )
        else:
            if stream["message_count"] != 0 or stream["header_count"] != 0:
                raise M2DGRTimingEvidenceError(
                    f"missing topic {topic} unexpectedly contains samples"
                )
            if stream["header_time"] is not None:
                raise M2DGRTimingEvidenceError(
                    f"missing topic {topic} unexpectedly has header timing"
                )

    if payload["total_target_messages"] != total_messages:
        raise M2DGRTimingEvidenceError(
            "total_target_messages does not equal the stream-message sum"
        )
    if payload["total_decode_errors"] != total_decode_errors:
        raise M2DGRTimingEvidenceError(
            "total_decode_errors does not equal the stream-error sum"
        )

    common = _require_mapping(
        payload["common_header_range"],
        "common_header_range",
    )
    _require_exact_keys(
        common,
        {
            "start_ns",
            "end_ns",
            "interpretation",
            "synchronization_claim",
        },
        "common_header_range",
    )
    if common["interpretation"] != "numeric_header_range_intersection_only":
        raise M2DGRTimingEvidenceError(
            "common header range has unexpected semantics"
        )
    if common["synchronization_claim"] is not False:
        raise M2DGRTimingEvidenceError(
            "common header range must not claim synchronization"
        )

    _require_mapping(payload["pairs"], "stream-timing pairs")


def load_m2dgr_stream_timing_artifact(path: str | Path) -> dict:
    source = Path(path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    validate_m2dgr_stream_timing_payload(payload)
    return payload


def load_m2dgr_stream_timing_for_trajectory(
    dataset_root: str | Path,
    trajectory_id: str,
) -> dict:
    path = timing_artifact_path(dataset_root, trajectory_id)
    if not path.is_file():
        raise FileNotFoundError(
            "Phase-3 M2DGR stream-timing evidence is required: "
            f"{path}"
        )

    payload = load_m2dgr_stream_timing_artifact(path)
    if payload["trajectory_id"] != trajectory_id:
        raise M2DGRTimingEvidenceError(
            "timing artifact trajectory does not match requested trajectory"
        )
    return payload


def available_stream_ids(payload: dict) -> tuple[str, ...]:
    validate_m2dgr_stream_timing_payload(payload)
    available = set(payload["available_target_topics"])
    return tuple(
        topic
        for topic in EXPECTED_TARGET_TOPICS
        if topic in available
    )


def validate_exact_header_anomaly_payload(payload: dict) -> None:
    payload = _require_mapping(payload, "exact-header-anomaly root")
    _require_exact_keys(
        payload,
        {
            "schema",
            "version",
            "trajectory_id",
            "topic",
            "source",
            "reader",
            "stream",
            "reversals",
            "duplicates",
            "comparison",
            "policy",
        },
        "exact-header-anomaly artifact",
    )
    if payload["schema"] != EXACT_HEADER_ANOMALY_SCHEMA:
        raise M2DGRTimingEvidenceError(
            "unexpected exact-header-anomaly schema"
        )
    if payload["version"] != EXACT_HEADER_ANOMALY_VERSION:
        raise M2DGRTimingEvidenceError(
            "unexpected exact-header-anomaly version"
        )

    trajectory_id = _require_text(
        payload["trajectory_id"],
        "exact anomaly trajectory_id",
    )
    topic = _require_text(payload["topic"], "exact anomaly topic")

    source = _require_mapping(payload["source"], "exact anomaly source")
    _require_exact_keys(
        source,
        {
            "relative_path",
            "recorded_sha256",
            "checksum_sidecar",
            "raw_modified",
        },
        "exact anomaly source",
    )
    if (
        _require_relative_path(
            source["relative_path"],
            "exact anomaly source relative_path",
        )
        != f"raw/rosbags/{trajectory_id}.bag"
    ):
        raise M2DGRTimingEvidenceError(
            "exact anomaly source path does not match trajectory"
        )
    if (
        _require_relative_path(
            source["checksum_sidecar"],
            "exact anomaly checksum sidecar",
        )
        != f"checksums/{trajectory_id}.bag.sha256"
    ):
        raise M2DGRTimingEvidenceError(
            "exact anomaly checksum sidecar does not match trajectory"
        )
    _require_sha256(
        source["recorded_sha256"],
        "exact anomaly recorded_sha256",
    )
    if source["raw_modified"] is not False:
        raise M2DGRTimingEvidenceError(
            "exact anomaly evidence must not modify raw data"
        )

    reader = _require_mapping(payload["reader"], "exact anomaly reader")
    if reader.get("package") != "rosbags":
        raise M2DGRTimingEvidenceError(
            "exact anomaly reader must identify rosbags"
        )
    if reader.get("scan_completed") is not True:
        raise M2DGRTimingEvidenceError(
            "exact anomaly scan is not marked complete"
        )

    stream = _require_mapping(payload["stream"], "exact anomaly stream")
    reversals = payload["reversals"]
    duplicates = payload["duplicates"]
    if not isinstance(reversals, list) or not isinstance(duplicates, list):
        raise M2DGRTimingEvidenceError(
            "reversals and duplicates must be lists"
        )
    if stream.get("reverse_count") != len(reversals):
        raise M2DGRTimingEvidenceError(
            "stream reverse_count does not match reversal records"
        )
    if stream.get("duplicate_count") != len(duplicates):
        raise M2DGRTimingEvidenceError(
            "stream duplicate_count does not match duplicate records"
        )

    for item in reversals:
        item = _require_mapping(item, "reversal record")
        previous = item.get("previous_header_ns")
        current = item.get("current_header_ns")
        delta = item.get("delta_ns")
        if not all(
            isinstance(value, int)
            for value in (previous, current, delta)
        ):
            raise M2DGRTimingEvidenceError(
                "reversal timestamps/delta must be integers"
            )
        if current >= previous:
            raise M2DGRTimingEvidenceError(
                "reversal record does not contain a reversed header timestamp"
            )
        if delta != current - previous:
            raise M2DGRTimingEvidenceError(
                "reversal delta does not match its timestamps"
            )
        if item.get("current_index") != item.get("previous_index") + 1:
            raise M2DGRTimingEvidenceError(
                "reversal indices must be adjacent"
            )

    policy = _require_mapping(payload["policy"], "exact anomaly policy")
    required_policy = {
        "structural_reverse_timestamp": True,
        "threshold_required_to_detect": False,
        "automatic_sample_repair": False,
        "automatic_sample_exclusion_rule_created": False,
        "fixed_time_offset_estimated": False,
        "synchronization_tolerance_frozen": False,
        "synchronization_verified": False,
    }
    for key, expected in required_policy.items():
        if policy.get(key) != expected:
            raise M2DGRTimingEvidenceError(
                f"unsafe or unexpected exact-anomaly policy: "
                f"{key}={policy.get(key)!r}"
            )

    comparison = _require_mapping(
        payload["comparison"],
        "exact anomaly comparison",
    )
    if comparison.get("counts_match") is not True:
        raise M2DGRTimingEvidenceError(
            "exact anomaly scan does not match aggregate evidence"
        )
    if (
        comparison.get("aggregate_reverse_count")
        != comparison.get("targeted_reverse_count")
    ):
        raise M2DGRTimingEvidenceError(
            "aggregate/targeted reversal counts disagree"
        )
    if topic not in EXPECTED_TARGET_TOPICS:
        raise M2DGRTimingEvidenceError(
            f"unexpected exact-anomaly topic {topic!r}"
        )


def load_exact_header_anomaly_artifact(path: str | Path) -> dict:
    source = Path(path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    validate_exact_header_anomaly_payload(payload)
    return payload


def build_m2dgr_timing_evidence_index(
    dataset_root: str | Path,
    trajectory_ids: Iterable[str],
) -> dict:
    dataset_root = Path(dataset_root)
    ordered_ids = sorted(set(trajectory_ids))
    if not ordered_ids:
        raise M2DGRTimingEvidenceError(
            "timing evidence index requires at least one trajectory"
        )

    artifacts = []
    for trajectory_id in ordered_ids:
        path = timing_artifact_path(dataset_root, trajectory_id)
        payload = load_m2dgr_stream_timing_for_trajectory(
            dataset_root,
            trajectory_id,
        )

        stream_structural_counts = {}
        for topic in EXPECTED_TARGET_TOPICS:
            stream = payload["streams"][topic]
            header = stream["header_time"]
            stream_structural_counts[topic] = {
                "header_count": stream["header_count"],
                "reverse_count": (
                    header["reverse_count"]
                    if header is not None
                    else None
                ),
                "duplicate_count": (
                    header["duplicate_count"]
                    if header is not None
                    else None
                ),
            }

        artifacts.append(
            {
                "trajectory_id": trajectory_id,
                "artifact_relative_path": (
                    path.relative_to(dataset_root).as_posix()
                ),
                "artifact_file_sha256": sha256_file(path),
                "raw_bag_sha256": payload["source"]["recorded_sha256"],
                "available_target_topics": list(
                    payload["available_target_topics"]
                ),
                "missing_target_topics": list(
                    payload["missing_target_topics"]
                ),
                "total_decode_errors": payload["total_decode_errors"],
                "stream_structural_counts": stream_structural_counts,
            }
        )

    exact_artifacts = []
    exact_root = dataset_root / EXACT_ANOMALY_ROOT
    if exact_root.is_dir():
        for path in sorted(exact_root.glob("*.json")):
            payload = load_exact_header_anomaly_artifact(path)
            exact_artifacts.append(
                {
                    "trajectory_id": payload["trajectory_id"],
                    "topic": payload["topic"],
                    "artifact_relative_path": (
                        path.relative_to(dataset_root).as_posix()
                    ),
                    "artifact_file_sha256": sha256_file(path),
                    "raw_bag_sha256": payload["source"]["recorded_sha256"],
                    "reverse_count": payload["stream"]["reverse_count"],
                    "duplicate_count": payload["stream"]["duplicate_count"],
                }
            )

    index = {
        "schema": TIMING_INDEX_SCHEMA,
        "schema_version": TIMING_INDEX_VERSION,
        "dataset_id": "M2DGR",
        "trajectory_count": len(ordered_ids),
        "timing_artifact_count": len(artifacts),
        "exact_anomaly_artifact_count": len(exact_artifacts),
        "policy": {
            "measurement_time_basis_observed": "sensor_header_stamp",
            "bag_record_time_role": "transport_provenance_diagnostic_only",
            "characterization_only": True,
            "common_header_range_is_validity_mask": False,
            "automatic_sample_exclusion_rule_created": False,
            "fixed_time_offset_estimated": False,
            "synchronization_tolerance_frozen": False,
            "synchronization_verified": False,
        },
        "artifacts": artifacts,
        "exact_anomaly_artifacts": exact_artifacts,
    }
    index["index_content_sha256"] = _canonical_digest(index)
    return index


def validate_m2dgr_timing_evidence_index(payload: dict) -> None:
    payload = _require_mapping(payload, "timing evidence index")
    _require_exact_keys(
        payload,
        {
            "schema",
            "schema_version",
            "dataset_id",
            "trajectory_count",
            "timing_artifact_count",
            "exact_anomaly_artifact_count",
            "policy",
            "artifacts",
            "exact_anomaly_artifacts",
            "index_content_sha256",
        },
        "timing evidence index",
    )
    if payload["schema"] != TIMING_INDEX_SCHEMA:
        raise M2DGRTimingEvidenceError(
            "unexpected timing evidence index schema"
        )
    if payload["schema_version"] != TIMING_INDEX_VERSION:
        raise M2DGRTimingEvidenceError(
            "unexpected timing evidence index schema_version"
        )
    if payload["dataset_id"] != "M2DGR":
        raise M2DGRTimingEvidenceError(
            "timing evidence index dataset_id must be M2DGR"
        )
    if payload["index_content_sha256"] != _canonical_digest(payload):
        raise M2DGRTimingEvidenceError(
            "timing evidence index content hash mismatch"
        )

    artifacts = payload["artifacts"]
    exact = payload["exact_anomaly_artifacts"]
    if not isinstance(artifacts, list) or not isinstance(exact, list):
        raise M2DGRTimingEvidenceError(
            "timing index artifact collections must be lists"
        )
    if payload["trajectory_count"] != len(artifacts):
        raise M2DGRTimingEvidenceError(
            "trajectory_count must equal timing artifact count"
        )
    if payload["timing_artifact_count"] != len(artifacts):
        raise M2DGRTimingEvidenceError(
            "timing_artifact_count mismatch"
        )
    if payload["exact_anomaly_artifact_count"] != len(exact):
        raise M2DGRTimingEvidenceError(
            "exact_anomaly_artifact_count mismatch"
        )

    policy = _require_mapping(
        payload["policy"],
        "timing evidence index policy",
    )
    if policy.get("synchronization_verified") is not False:
        raise M2DGRTimingEvidenceError(
            "Phase-3 timing evidence index cannot verify synchronization"
        )
    if policy.get("synchronization_tolerance_frozen") is not False:
        raise M2DGRTimingEvidenceError(
            "Phase-3 timing evidence index cannot freeze a tolerance"
        )
    if policy.get("fixed_time_offset_estimated") is not False:
        raise M2DGRTimingEvidenceError(
            "Phase-3 timing evidence index cannot estimate a fixed offset"
        )
    if policy.get("common_header_range_is_validity_mask") is not False:
        raise M2DGRTimingEvidenceError(
            "common header range cannot become a validity mask"
        )


def canonical_m2dgr_timing_evidence_index_json(payload: dict) -> str:
    validate_m2dgr_timing_evidence_index(payload)
    return (
        json.dumps(
            payload,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        + "\n"
    )


def write_immutable_m2dgr_timing_evidence_index(
    path: str | Path,
    payload: dict,
) -> Path:
    destination = Path(path)
    content = canonical_m2dgr_timing_evidence_index_json(payload)

    if destination.exists():
        existing = destination.read_text(encoding="utf-8")
        if existing != content:
            raise FileExistsError(
                "immutable M2DGR timing evidence index already "
                f"exists with different content: {destination}"
            )
        return destination

    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{destination.name}.",
        suffix=".tmp",
        dir=destination.parent,
        text=True,
    )
    temporary = Path(temp_name)

    try:
        with os.fdopen(
            fd,
            "w",
            encoding="utf-8",
            newline="\n",
        ) as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())

        try:
            os.link(temporary, destination)
        except FileExistsError:
            existing = destination.read_text(encoding="utf-8")
            if existing != content:
                raise
    finally:
        temporary.unlink(missing_ok=True)

    return destination
