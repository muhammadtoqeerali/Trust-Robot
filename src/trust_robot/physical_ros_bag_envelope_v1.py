"""R135-A29-3: ROS bag recorder metadata envelopes.

No ROS dependencies, robot I/O, M2DGR access or estimation.
Recorded SQLite timestamps are never promoted to physical
sensor event timestamps, calibrated time or real factors.
"""

from __future__ import annotations

SCHEMA = "TRUST_ROBOT_R135_A29_3_BAG_ENVELOPES_V1"

TOPICS = {
    "/correlated_timestamp": (
        "clock_correlation",
        "isaac_ros_nova_interfaces/msg/CorrelatedTimestamp",
    ),
    "/front_3d_lidar/lidar_points": (
        "lidar", "sensor_msgs/msg/PointCloud2",
    ),
    "/front_stereo_camera/left/camera_info": (
        "left_camera_info", "sensor_msgs/msg/CameraInfo",
    ),
    "/front_stereo_camera/left/image_raw": (
        "left_image", "sensor_msgs/msg/Image",
    ),
    "/front_stereo_camera/right/camera_info": (
        "right_camera_info", "sensor_msgs/msg/CameraInfo",
    ),
    "/front_stereo_camera/right/image_raw": (
        "right_image", "sensor_msgs/msg/Image",
    ),
    "/front_stereo_imu/imu": (
        "imu", "sensor_msgs/msg/Imu",
    ),
}

COUNTS = {
    "/correlated_timestamp": 9,
    "/front_3d_lidar/lidar_points": 82,
    "/front_stereo_camera/left/camera_info": 84,
    "/front_stereo_camera/left/image_raw": 84,
    "/front_stereo_camera/right/camera_info": 76,
    "/front_stereo_camera/right/image_raw": 81,
    "/front_stereo_imu/imu": 427,
}

CAPTURE_MANIFEST_SHA256 = (
    "1bbff251e52bef4699ee068f096ac9dbff0b8b59eea5632e6f99ee1e3e34d696"
)

ENVELOPE_FIELDS = frozenset({
    "stream",
    "sequence",
    "recorder_stamp_ns",
    "serialized_bytes",
    "source_kind",
    "header_stamp_ns",
    "frame_id",
})


class EnvelopeValidationError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise EnvelopeValidationError(message)


def validate_envelope(row):
    require(
        type(row) is dict and set(row) == ENVELOPE_FIELDS,
        "Unexpected envelope fields",
    )

    require(
        row["stream"] in {value[0] for value in TOPICS.values()},
        "Unknown stream",
    )

    require(
        row["source_kind"] == "PHYSICAL_UNQUALIFIED",
        "Unsupported source identity",
    )

    for field in (
        "sequence",
        "recorder_stamp_ns",
        "serialized_bytes",
    ):
        value = row[field]
        require(
            type(value) is int and
            value >= (0 if field == "sequence" else 1),
            "Invalid integer: " + field,
        )

    require(
        row["header_stamp_ns"] is None,
        "Header timestamp was not extracted",
    )

    require(
        row["frame_id"] is None,
        "Frame ID was not extracted",
    )

    return True


def review_envelopes(rows):
    require(
        type(rows) is list and 0 < len(rows) <= 10000,
        "Invalid bounded envelope set",
    )

    counts = {
        stream: 0
        for stream, _ in TOPICS.values()
    }

    sizes = dict.fromkeys(counts, 0)
    previous_timestamp = None
    last_per_stream = {}

    for row in rows:
        validate_envelope(row)

        stream = row["stream"]
        sequence = row["sequence"]
        timestamp = row["recorder_stamp_ns"]

        if previous_timestamp is not None:
            require(
                timestamp >= previous_timestamp,
                "Recorder timestamp list not ordered",
            )

        previous_timestamp = timestamp

        require(
            sequence == counts[stream],
            "Noncontiguous stream sequence",
        )

        if stream in last_per_stream:
            require(
                timestamp >= last_per_stream[stream],
                "Per-stream recorder time reversed",
            )

        last_per_stream[stream] = timestamp
        counts[stream] += 1
        sizes[stream] += row["serialized_bytes"]

    return {
        "schema": SCHEMA,
        "status": "RECORDER_ENVELOPES_ONLY",
        "envelope_count": len(rows),
        "stream_counts": counts,
        "stream_serialized_bytes": sizes,
        "header_stamps_extracted": False,
        "frame_ids_extracted": False,
        "sensor_event_times_qualified": False,
        "estimator_invoked": False,
        "real_factor_count": 0,
        "real_factor_admission": "DENIED",
        "m2dgr_gates": "11_CLOSED",
    }


def review_pinned_capture(envelope_report, original_audit):
    """Compare envelope metadata to the earlier pinned bag audit.

    The caller must separately SHA-verify the original audit.
    This function does not verify original bag file hashes.
    """
    require(
        type(envelope_report) is dict
        and type(original_audit) is dict,
        "Invalid report objects",
    )

    require(
        envelope_report.get("schema") == SCHEMA
        and envelope_report.get("status")
        == "READ_ONLY_ROSBAG_METADATA_ENVELOPES",
        "Unexpected extraction contract",
    )

    require(
        envelope_report.get("capture_manifest_sha256")
        == CAPTURE_MANIFEST_SHA256,
        "Original capture manifest differs",
    )

    require(
        envelope_report.get("raw_payload_columns_selected") is False
        and envelope_report.get("bag_file_hashes_rechecked") is False,
        "Unexpected extraction scope",
    )

    require(
        original_audit.get("factor_admission") == "DENIED"
        and original_audit.get("m2dgr_gates") == "11_CLOSED",
        "Original scientific gate differs",
    )

    require(
        envelope_report.get("bag_total_bytes")
        == original_audit.get("bag_total_bytes")
        == 1415126942,
        "Recorded bag size differs",
    )

    require(
        envelope_report.get("topic_types")
        == {k: v[1] for k, v in TOPICS.items()},
        "ROS message types differ",
    )

    rows = envelope_report.get("envelopes")
    result = review_envelopes(rows)

    require(
        result["envelope_count"]
        == original_audit.get("recorded_total_messages")
        == 843,
        "Message count differs",
    )

    original_topics = original_audit.get("topics")
    require(
        type(original_topics) is dict
        and set(original_topics) == set(TOPICS),
        "Original topic inventory differs",
    )

    for topic, (stream, _) in TOPICS.items():
        old = original_topics[topic]

        require(
            type(old) is dict
            and type(old.get("count")) is int
            and old["count"] == COUNTS[topic]
            and result["stream_counts"][stream] == COUNTS[topic],
            "Topic count mismatch: " + topic,
        )

        require(
            type(old.get("serialized_bytes")) is int
            and result["stream_serialized_bytes"][stream]
            == old["serialized_bytes"],
            "Serialized-size mismatch: " + topic,
        )

    result["status"] = "PINNED_A28_REPORT_ENVELOPE_CONSISTENCY"
    result["original_bag_re_deserialized"] = False
    result["original_bag_hashes_rechecked"] = False
    result["physical_sync_verified"] = False
    result["metric_calibration_verified"] = False
    result["independent_pose_reference_verified"] = False

    return result


def to_fusion_descriptor(*args, **kwargs):
    """Never manufacture missing event stamps or frame IDs."""
    raise EnvelopeValidationError(
        "Unqualified recorder envelopes cannot become "
        "physical fusion descriptors"
    )
