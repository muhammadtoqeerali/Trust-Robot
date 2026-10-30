"""R135-A28-4B: offline review of pinned A28-3 report.

This checks internal consistency of the already-completed
physical ROS bag audit. It is not a second ROS deserialization.

No robot, ROS, network, dataset, estimator, raw image or
pointcloud access. No physical factor admission.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

SCHEMA = "TRUST_ROBOT_R135_A28_4B_FULL_BAG_REPORT_REVIEW_V1"

EXPECTED_COUNTS = {
    "/correlated_timestamp":
        (9, "isaac_ros_nova_interfaces/msg/CorrelatedTimestamp"),
    "/front_3d_lidar/lidar_points":
        (82, "sensor_msgs/msg/PointCloud2"),
    "/front_stereo_camera/left/camera_info":
        (84, "sensor_msgs/msg/CameraInfo"),
    "/front_stereo_camera/left/image_raw":
        (84, "sensor_msgs/msg/Image"),
    "/front_stereo_camera/right/camera_info":
        (76, "sensor_msgs/msg/CameraInfo"),
    "/front_stereo_camera/right/image_raw":
        (81, "sensor_msgs/msg/Image"),
    "/front_stereo_imu/imu":
        (427, "sensor_msgs/msg/Imu"),
}

EXPECTED_FIELDS = frozenset({
    "bag_db_count",
    "bag_total_bytes",
    "calibration_validity",
    "capture_manifest_sha256",
    "factor_admission",
    "independent_ground_truth",
    "left_image_matching_info_stamps",
    "left_unmatched_header_stamps",
    "m2dgr_gates",
    "original_metadata_sha256",
    "phase",
    "physical_clock_accuracy",
    "raw_images_exported",
    "raw_lidar_exported",
    "recorded_total_messages",
    "right_image_matching_info_stamps",
    "right_unmatched_header_stamps",
    "sqlite_quick_check",
    "status",
    "stereo_exact_header_pairs",
    "topics",
})

CAPTURE_MANIFEST_SHA256 = (
    "1bbff251e52bef4699ee068f096ac9dbff0b8b59eea5632e6f99ee1e3e34d696"
)

COUNT_KEYS = (
    "message_count",
    "recorded_count",
    "messages_recorded",
    "recorded_messages",
    "messages",
    "count",
    "bag_count",
    "deserialized_count",
    "deserialized_messages",
    "decoded_count",
    "verified_count",
)

NAME_KEYS = ("name", "topic", "topic_name")
TYPE_KEYS = ("type", "message_type", "msg_type", "ros_type")


class FullBagReportError(ValueError):
    """A private-report contract or scientific gate failed."""


def require(condition, message):
    if not condition:
        raise FullBagReportError(message)


def integer(value, name, expected):
    require(
        type(value) is int and value == expected,
        f"{name} must equal {expected}",
    )


def digest_ok(value):
    return (
        type(value) is str
        and len(value) == 64
        and all(c in "0123456789abcdef" for c in value)
    )


def _topic_records(topics):
    if isinstance(topics, dict):
        if set(topics) == set(EXPECTED_COUNTS):
            return topics
        rows = list(topics.values())
    elif isinstance(topics, list):
        rows = topics
    else:
        raise FullBagReportError("Unexpected topics container")

    found = {}

    for entry in rows:
        require(isinstance(entry, dict), "Invalid topic entry")

        names = [
            entry.get(k)
            for k in NAME_KEYS
            if type(entry.get(k)) is str
        ]

        require(
            len(set(names)) == 1 and bool(names),
            "Topic entry missing unambiguous name",
        )

        name = names[0]

        require(name not in found, "Duplicate topic name")
        found[name] = entry

    return found


def _topic_count(entry):
    if type(entry) is int:
        return entry

    require(
        isinstance(entry, dict),
        "Topic record must be object or integer",
    )

    values = [
        (key, entry[key])
        for key in COUNT_KEYS
        if key in entry and type(entry[key]) is int
    ]

    require(
        bool(values),
        "Topic count key not recognized: " + repr(sorted(entry)),
    )

    require(
        all(n == values[0][1] for _, n in values),
        "Conflicting topic counts",
    )

    return values[0][1]


def review_report(report):
    """Validate known audit summary, not original ROS bag."""

    require(
        type(report) is dict
        and set(report) == EXPECTED_FIELDS,
        "Unexpected A28-3 report schema",
    )

    require(
        report["phase"] in ("R135-A28-3", "R135_A28_3"),
        "Wrong original audit phase",
    )

    require(
        report["status"] ==
        "FULL_BAG_INTEGRITY_AND_ROS_DESERIALIZATION_VERIFIED_ONLY",
        "Unexpected original A28-3 status or scientific scope",
    )

    require(
        report["factor_admission"] == "DENIED"
        and report["m2dgr_gates"] == "11_CLOSED",
        "Scientific gate changed",
    )

    for field in (
        "physical_clock_accuracy",
        "calibration_validity",
    ):
        require(
            report[field] == "UNVERIFIED",
            field + " was upgraded",
        )

    require(
        report["independent_ground_truth"]
        in (False, "UNVERIFIED", "ABSENT"),
        "Unsupported independent reference claim",
    )

    require(
        report["raw_images_exported"] is False
        and report["raw_lidar_exported"] is False,
        "Raw export declaration changed",
    )

    require(
        report["sqlite_quick_check"] in ("ok", "PASS", True),
        "SQLite check not reported as passing",
    )

    require(
        report["capture_manifest_sha256"]
        == CAPTURE_MANIFEST_SHA256,
        "Capture manifest identity differs",
    )

    require(
        digest_ok(report["original_metadata_sha256"]),
        "Malformed metadata digest",
    )

    expected_values = (
        ("bag_db_count", 1),
        ("bag_total_bytes", 1415126942),
        ("recorded_total_messages", 843),
        ("stereo_exact_header_pairs", 81),
        ("left_unmatched_header_stamps", 3),
        ("right_unmatched_header_stamps", 0),
        ("left_image_matching_info_stamps", 84),
        ("right_image_matching_info_stamps", 76),
    )

    for key, value in expected_values:
        integer(report[key], key, value)

    rows = _topic_records(report["topics"])

    require(
        set(rows) == set(EXPECTED_COUNTS),
        "Seven topic names differ",
    )

    counts = {}

    for name, (expected_count, expected_type) \
            in EXPECTED_COUNTS.items():

        entry = rows[name]
        count = _topic_count(entry)

        integer(count, "count:" + name, expected_count)

        require(
            isinstance(entry, dict),
            "Original topic record must be an object",
        )

        require(
            type(entry.get("payload_shape_mismatches")) is int
            and entry["payload_shape_mismatches"] == 0,
            "Reported payload-shape mismatch: " + name,
        )

        require(
            type(entry.get("serialized_bytes")) is int
            and entry["serialized_bytes"] > 0,
            "Missing positive serialized-byte statistic: " + name,
        )

        if isinstance(entry, dict):
            present = [
                entry[k] for k in TYPE_KEYS if k in entry
            ]

            require(
                all(
                    type(v) is str and v == expected_type
                    for v in present
                ),
                "Topic message type differs: " + name,
            )

        counts[name] = count

    require(
        sum(counts.values()) == 843,
        "Topic count total mismatch",
    )

    return {
        "schema": SCHEMA,
        "status": "PINNED_REPORT_INTERNAL_CONSISTENCY_ONLY",
        "source_phase": "R135-A28-3",
        "topic_counts": counts,
        "topic_count": len(counts),
        "reported_messages": 843,
        "reported_bytes": 1415126942,
        "reported_exact_stereo_header_pairs": 81,
        "report_original_bag_re_deserialized": False,
        "reported_payload_shape_mismatches": 0,
        "original_message_types_independently_rechecked": False,
        "original_bag_hashes_independently_rechecked": False,
        "physical_sync_verified": False,
        "metric_extrinsics_verified": False,
        "independent_reference_verified": False,
        "real_factor_admission": "DENIED",
        "m2dgr_gates": "11_CLOSED",
    }


def review_report_file(path, expected_sha256):
    """Require a small, regular, SHA-pinned local report."""

    source = Path(path)

    require(
        digest_ok(expected_sha256),
        "Invalid expected SHA-256",
    )

    require(
        source.is_file() and not source.is_symlink(),
        "Not a regular report",
    )

    require(
        0 < source.stat().st_size <= 8_000_000,
        "Report size invalid",
    )

    data = source.read_bytes()

    require(
        hashlib.sha256(data).hexdigest() == expected_sha256,
        "A28-3 audit-report SHA-256 differs",
    )

    try:
        payload = json.loads(data)
    except (ValueError, UnicodeDecodeError) as exc:
        raise FullBagReportError("Invalid audit JSON") from exc

    answer = review_report(payload)
    answer["source_report_sha256"] = expected_sha256

    return answer
