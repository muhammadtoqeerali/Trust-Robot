"""TRUST-ROBOT R128-B9.

Read at most twelve real messages per selected sensor topic.
No GT reading, training, synchronization fitting or scoring.
"""

import copy
import hashlib
import json
import math
import os
from pathlib import Path
from statistics import median

from rosbags.highlevel import AnyReader
from rosbags.typesys import Stores, get_typestore

BAG = Path(os.environ["BAG"])
OUT = Path(os.environ["B9"])

LIMIT = 12
MAX_EXAMINED = 20000
MAX_RAW_BYTES = 128 * 1024 * 1024

TOPICS = {
    **{
        f"/alphasense/cam{i}/image_raw": "camera"
        for i in range(5)
    },
    "/alphasense/imu": "imu",
    "/hesai/pandar": "lidar",
}

TYPES = {
    "camera": "sensor_msgs/msg/Image",
    "imu": "sensor_msgs/msg/Imu",
    "lidar": "sensor_msgs/msg/PointCloud2",
}


def need(value, reason):
    if not value:
        raise ValueError("R128_B9_DENIED:" + reason)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(name, obj):
    raw = (
        json.dumps(
            obj,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        ) + "\n"
    ).encode()

    path = OUT / name

    with path.open("xb") as f:
        f.write(raw)
        f.flush()
        os.fsync(f.fileno())

    return sha(raw)


def stamp_ns(header):
    stamp = getattr(header, "stamp", None)

    if stamp is None:
        return None

    seconds = getattr(
        stamp, "sec",
        getattr(stamp, "secs", None),
    )

    nanoseconds = getattr(
        stamp, "nanosec",
        getattr(
            stamp, "nsec",
            getattr(stamp, "nsecs", None),
        ),
    )

    if not (
        isinstance(seconds, int)
        and isinstance(nanoseconds, int)
        and seconds >= 0
        and 0 <= nanoseconds < 1_000_000_000
    ):
        return None

    return seconds * 1_000_000_000 + nanoseconds


def finite_vector(obj):
    values = [float(obj.x), float(obj.y), float(obj.z)]

    if all(math.isfinite(v) for v in values):
        return values

    return None


def describe_message(msg, kind):
    if kind == "camera":
        width = int(msg.width)
        height = int(msg.height)
        step = int(msg.step)
        size = len(msg.data)

        return {
            "width": width,
            "height": height,
            "encoding": str(msg.encoding),
            "step_bytes": step,
            "data_bytes": size,
            "step_times_height_matches_data":
                step * height == size,
            "positive_dimensions":
                width > 0 and height > 0,
        }

    if kind == "imu":
        acceleration = finite_vector(
            msg.linear_acceleration
        )
        angular_velocity = finite_vector(
            msg.angular_velocity
        )

        q = msg.orientation

        orientation = [
            float(q.x), float(q.y),
            float(q.z), float(q.w),
        ]

        orientation_norm = (
            math.sqrt(sum(x*x for x in orientation))
            if all(math.isfinite(x) for x in orientation)
            else None
        )

        return {
            "acceleration_finite":
                acceleration is not None,
            "angular_velocity_finite":
                angular_velocity is not None,
            "acceleration_norm":
                math.sqrt(sum(x*x for x in acceleration))
                if acceleration is not None else None,
            "angular_rate_norm":
                math.sqrt(sum(x*x for x in angular_velocity))
                if angular_velocity is not None else None,
            "orientation_quaternion_norm":
                orientation_norm,
            "orientation_covariance_elements":
                len(msg.orientation_covariance),
            "angular_velocity_covariance_elements":
                len(msg.angular_velocity_covariance),
            "linear_acceleration_covariance_elements":
                len(msg.linear_acceleration_covariance),
        }

    if kind == "lidar":
        point_fields = [
            {
                "name": str(f.name),
                "offset": int(f.offset),
                "datatype": int(f.datatype),
                "count": int(f.count),
            }
            for f in msg.fields
        ]

        height = int(msg.height)
        width = int(msg.width)
        row_step = int(msg.row_step)

        return {
            "height": height,
            "width": width,
            "point_step": int(msg.point_step),
            "row_step": row_step,
            "data_bytes": len(msg.data),
            "row_step_times_height_matches_data":
                row_step * height == len(msg.data),
            "is_bigendian": bool(msg.is_bigendian),
            "is_dense": bool(msg.is_dense),
            "fields": point_fields,
        }

    raise ValueError("UNKNOWN_MODALITY")


def valid_record(record):
    return (
        record.get("topic") in TOPICS
        and record.get("kind")
            == TOPICS.get(record.get("topic"))
        and type(record.get("sample_index")) is int
        and 1 <= record["sample_index"] <= LIMIT
        and type(record.get("bag_timestamp_ns")) is int
        and record["bag_timestamp_ns"] >= 0
        and (
            record.get("header_timestamp_ns") is None
            or (
                type(record["header_timestamp_ns"]) is int
                and record["header_timestamp_ns"] >= 0
            )
        )
        and isinstance(record.get("raw_sha256"), str)
        and len(record["raw_sha256"]) == 64
        and all(
            c in "0123456789abcdef"
            for c in record["raw_sha256"]
        )
    )


def reject_negative_controls(sample):
    cases = []

    a = copy.deepcopy(sample)
    a["topic"] = "/unauthorized"
    cases.append(a)

    a = copy.deepcopy(sample)
    a["kind"] = "groundtruth"
    cases.append(a)

    a = copy.deepcopy(sample)
    a["sample_index"] = 0
    cases.append(a)

    a = copy.deepcopy(sample)
    a["bag_timestamp_ns"] = -1
    cases.append(a)

    a = copy.deepcopy(sample)
    a["raw_sha256"] = "not-a-valid-hash"
    cases.append(a)

    need(
        all(not valid_record(a) for a in cases),
        "NEGATIVE_CONTROL_ACCEPTED",
    )

    return len(cases)


def main():
    samples = {topic: [] for topic in TOPICS}
    examined = 0

    store = get_typestore(Stores.ROS1_NOETIC)

    with AnyReader(
        [BAG], default_typestore=store
    ) as reader:

        connections = [
            c for c in reader.connections
            if c.topic in TOPICS
        ]

        need(len(connections) == 7, "SENSOR_CONNECTION_COUNT")
        need(
            {c.topic for c in connections} == set(TOPICS),
            "SENSOR_TOPIC_SET",
        )

        for connection in connections:
            need(
                connection.msgtype
                == TYPES[TOPICS[connection.topic]],
                "SENSOR_MESSAGE_TYPE",
            )

        bag_start = int(reader.start_time)
        bag_end = int(reader.end_time)
        bag_message_count = int(reader.message_count)

        need(
            bag_start < bag_end
            and bag_message_count == 45082,
            "BAG_METADATA",
        )

        for connection, bag_ns, raw in reader.messages(
            connections=connections
        ):
            examined += 1

            need(
                examined <= MAX_EXAMINED,
                "SCAN_BUDGET_EXCEEDED",
            )

            topic = connection.topic

            if len(samples[topic]) >= LIMIT:
                continue

            need(
                0 < len(raw) <= MAX_RAW_BYTES,
                "RAW_MESSAGE_SIZE",
            )

            message = reader.deserialize(
                raw, connection.msgtype
            )

            header = getattr(message, "header", None)

            header_ns = (
                stamp_ns(header)
                if header is not None else None
            )

            row = {
                "topic": topic,
                "kind": TOPICS[topic],
                "sample_index": len(samples[topic]) + 1,
                "bag_timestamp_ns": int(bag_ns),
                "header_timestamp_ns": header_ns,
                "header_minus_bag_ns":
                    header_ns - int(bag_ns)
                    if header_ns is not None else None,
                "header_frame_id":
                    str(getattr(header, "frame_id", ""))
                    if header is not None else "",
                "raw_bytes": len(raw),
                "raw_sha256": sha(raw),
                "structure": describe_message(
                    message, TOPICS[topic]
                ),
            }

            need(valid_record(row), "SAMPLE_RECORD_INVALID")
            samples[topic].append(row)

            if all(
                len(rows) == LIMIT
                for rows in samples.values()
            ):
                break

    need(
        all(len(rows) == LIMIT for rows in samples.values()),
        "INSUFFICIENT_BOUNDED_SAMPLES",
    )

    summaries = {}

    for topic, rows in samples.items():
        bag_stamps = [x["bag_timestamp_ns"] for x in rows]
        header_stamps = [
            x["header_timestamp_ns"]
            for x in rows
            if x["header_timestamp_ns"] is not None
        ]

        differences = [
            x["header_minus_bag_ns"]
            for x in rows
            if x["header_minus_bag_ns"] is not None
        ]

        gaps = [
            b - a for a, b in
            zip(bag_stamps, bag_stamps[1:])
        ]

        summaries[topic] = {
            "kind": TOPICS[topic],
            "decoded_samples": len(rows),
            "first_bag_timestamp_ns": bag_stamps[0],
            "last_bag_timestamp_ns": bag_stamps[-1],
            "median_sample_gap_ns": median(gaps),
            "nonpositive_sample_gaps":
                sum(x <= 0 for x in gaps),
            "valid_header_stamps": len(header_stamps),
            "median_header_minus_bag_ns":
                median(differences)
                if differences else None,
            "header_bag_difference_min_ns":
                min(differences)
                if differences else None,
            "header_bag_difference_max_ns":
                max(differences)
                if differences else None,
            "frame_ids": sorted(set(
                x["header_frame_id"] for x in rows
            )),
        }

    negatives = reject_negative_controls(
        samples["/alphasense/imu"][0]
    )

    report = {
        "schema":
            "TRUST_ROBOT_R128_B9_SENSOR_SAMPLE_AUDIT_V1",
        "recording": "exp14_basement_2",
        "dataset": "Hilti-Oxford 2022",
        "bag_sha256":
            os.environ["BAG_SHA"],
        "bag_bytes":
            int(os.environ["BAG_BYTES"]),
        "reader": "rosbags 0.11.9",
        "max_samples_per_topic": LIMIT,
        "max_messages_examined": MAX_EXAMINED,
        "messages_examined": examined,
        "bag_metadata": {
            "start_ns": bag_start,
            "end_ns_exclusive": bag_end,
            "message_count": bag_message_count,
        },
        "samples": samples,
        "summaries": summaries,
        "negative_controls_passed": negatives,
        "scientific_boundary": {
            "recording_data_deserialized": True,
            "bounded_sensor_sample_count": 84,
            "groundtruth_accessed": False,
            "m2dgr_data_accessed": False,
            "m2dgr_confirmation_accessed": False,
            "timestamp_physical_event_verified": False,
            "clock_synchronization_verified": False,
            "calibration_physically_verified": False,
            "full_independent_6dof_gt_verified": False,
            "dataset_partition_frozen": False,
            "health_model_trained": False,
            "real_sensor_factors_authorized": False,
            "ate_rpe_scoring_authorized": False,
            "m2dgr_scientific_gates_closed": 11,
        },
    }

    report_sha = save(
        "r128_b9_sensor_audit_v1.json", report
    )

    print("R128_B9_DECODED_SENSOR_TOPICS=7_PASS")
    print("R128_B9_DECODED_SENSOR_MESSAGES=84_PASS")
    print("R128_B9_MESSAGES_EXAMINED=", examined)
    print("R128_B9_NEGATIVE_CONTROLS=5_PASS")

    for topic, summary in summaries.items():
        print(
            "R128_B9_TOPIC",
            topic,
            "SAMPLES",
            summary["decoded_samples"],
            "HEADER_STAMPS",
            summary["valid_header_stamps"],
            "MEDIAN_HEADER_MINUS_BAG_NS",
            summary["median_header_minus_bag_ns"],
            "FRAMES",
            summary["frame_ids"],
        )

    print("R128_B9_REPORT_SHA256=", report_sha)
    print("R128_B9_SYNCHRONIZATION=NOT_PROVEN")
    print("R128_B9_SCORING=NOT_AUTHORIZED")


if __name__ == "__main__":
    main()
