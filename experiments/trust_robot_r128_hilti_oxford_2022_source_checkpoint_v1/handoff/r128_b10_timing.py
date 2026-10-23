"""R128-B10 bounded real-sensor timing observations.

First 128 messages per sensor topic, without clock fitting,
GT access, metric evaluation or estimator execution.
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

OUT = Path(os.environ["B10"])
BAG = Path(os.environ["BAG"])
B9 = Path(os.environ["B9"])

LIMIT = 128
MAX_EXAMINED = 16000
MAX_SINGLE_RAW = 128 * 1024 * 1024
MAX_DECODED_BYTES = 2 * 1024**3

TOPICS = {
    **{
        f"/alphasense/cam{i}/image_raw": "camera"
        for i in range(5)
    },
    "/alphasense/imu": "imu",
    "/hesai/pandar": "lidar",
}

EXPECTED_TYPES = {
    "camera": "sensor_msgs/msg/Image",
    "imu": "sensor_msgs/msg/Imu",
    "lidar": "sensor_msgs/msg/PointCloud2",
}


def need(value, reason):
    if not value:
        raise ValueError("R128_B10_DENIED:" + reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def save(name, obj):
    raw = (
        json.dumps(
            obj, indent=2, sort_keys=True, allow_nan=False
        ) + "\n"
    ).encode()

    with (OUT / name).open("xb") as f:
        f.write(raw)
        f.flush()
        os.fsync(f.fileno())

    return sha(raw)


def header_stamp_ns(header):
    if header is None:
        return None

    stamp = getattr(header, "stamp", None)
    if stamp is None:
        return None

    sec = getattr(stamp, "sec", getattr(stamp, "secs", None))
    nsec = getattr(
        stamp, "nanosec",
        getattr(stamp, "nsec", getattr(stamp, "nsecs", None))
    )

    if (
        type(sec) is not int
        or type(nsec) is not int
        or sec < 0
        or not 0 <= nsec < 1_000_000_000
    ):
        return None

    return sec * 1_000_000_000 + nsec


def structure(message, kind):
    if kind == "camera":
        return {
            "width": int(message.width),
            "height": int(message.height),
            "step": int(message.step),
            "encoding": str(message.encoding),
            "payload_length_matches_layout":
                int(message.step) * int(message.height)
                == len(message.data),
        }

    if kind == "imu":
        a = message.linear_acceleration
        g = message.angular_velocity

        components = [
            float(a.x), float(a.y), float(a.z),
            float(g.x), float(g.y), float(g.z),
        ]

        return {
            "motion_components_finite":
                all(math.isfinite(x) for x in components),
            "orientation_covariance_length":
                len(message.orientation_covariance),
            "angular_covariance_length":
                len(message.angular_velocity_covariance),
            "acceleration_covariance_length":
                len(message.linear_acceleration_covariance),
        }

    if kind == "lidar":
        return {
            "width": int(message.width),
            "height": int(message.height),
            "point_step": int(message.point_step),
            "field_names": [
                str(field.name) for field in message.fields
            ],
            "payload_length_matches_layout":
                int(message.row_step) * int(message.height)
                == len(message.data),
        }

    raise ValueError("INVALID_MODALITY")


def interval_summary(stamps):
    values = [
        b - a
        for a, b in zip(stamps, stamps[1:])
    ]

    if not values:
        return None

    return {
        "count": len(values),
        "min_ns": min(values),
        "median_ns": median(values),
        "max_ns": max(values),
        "zero_count": sum(x == 0 for x in values),
        "negative_count": sum(x < 0 for x in values),
    }


def valid_report(report, original):
    if (
        report.get("schema")
        != "TRUST_ROBOT_R128_B10_TIMING_AUDIT_V1"
        or report.get("bag_sha256") != os.environ["BAG_SHA"]
        or report.get("messages_decoded") != 896
        or set(report.get("samples", {})) != set(TOPICS)
    ):
        return False

    if any(
        len(report["samples"][topic]) != LIMIT
        for topic in TOPICS
    ):
        return False

    for topic, old_rows in original["samples"].items():
        new_rows = report["samples"].get(topic, [])

        if len(old_rows) != 12 or len(new_rows) != LIMIT:
            return False

        for old, new in zip(old_rows, new_rows[:12]):
            for field in (
                "topic", "raw_sha256", "bag_timestamp_ns",
                "header_timestamp_ns", "header_frame_id",
            ):
                if old[field] != new[field]:
                    return False

    scope = report.get("scientific_boundary", {})

    expected_false = (
        "groundtruth_accessed",
        "m2dgr_confirmation_accessed",
        "sensor_clock_sync_verified",
        "physical_capture_event_verified",
        "timing_correction_fitted",
        "dataset_partition_frozen",
        "health_model_trained",
        "real_factors_authorized",
        "ate_rpe_authorized",
    )

    return (
        all(scope.get(key) is False for key in expected_false)
        and scope.get("m2dgr_scientific_gates_closed") == 11
    )


def main():
    original = json.loads(
        (B9 / "r128_b9_sensor_audit_v1.json").read_text()
    )

    need(
        original["bag_sha256"] == os.environ["BAG_SHA"],
        "PREDECESSOR_BAG_SHA",
    )

    samples = {topic: [] for topic in TOPICS}

    examined = 0
    decoded_bytes = 0

    typestore = get_typestore(Stores.ROS1_NOETIC)

    with AnyReader(
        [BAG], default_typestore=typestore
    ) as reader:

        connections = [
            c for c in reader.connections
            if c.topic in TOPICS
        ]

        need(len(connections) == 7, "CONNECTION_COUNT")
        need(
            {c.topic for c in connections} == set(TOPICS),
            "TOPIC_SET",
        )

        for c in connections:
            need(
                c.msgtype == EXPECTED_TYPES[TOPICS[c.topic]],
                "MESSAGE_TYPE",
            )

        need(reader.message_count == 45082, "MESSAGE_COUNT")

        for connection, bag_ns, raw in reader.messages(
            connections=connections
        ):
            examined += 1

            need(
                examined <= MAX_EXAMINED,
                "MESSAGE_SCAN_BUDGET",
            )

            topic = connection.topic

            if len(samples[topic]) == LIMIT:
                continue

            need(
                0 < len(raw) <= MAX_SINGLE_RAW,
                "MESSAGE_SIZE",
            )

            decoded_bytes += len(raw)

            need(
                decoded_bytes <= MAX_DECODED_BYTES,
                "DECODE_BYTE_BUDGET",
            )

            msg = reader.deserialize(
                raw, connection.msgtype
            )

            header = getattr(msg, "header", None)
            stamp = header_stamp_ns(header)

            samples[topic].append({
                "topic": topic,
                "sample_index": len(samples[topic]) + 1,
                "bag_timestamp_ns": int(bag_ns),
                "header_timestamp_ns": stamp,
                "header_frame_id": str(
                    getattr(header, "frame_id", "")
                ),
                "raw_sha256": sha(raw),
                "structure": structure(
                    msg, TOPICS[topic]
                ),
            })

            if all(
                len(rows) == LIMIT
                for rows in samples.values()
            ):
                break

    need(
        all(len(rows) == LIMIT for rows in samples.values()),
        "INSUFFICIENT_SAMPLES",
    )

    summaries = {}

    for topic, rows in samples.items():
        bag_stamps = [
            row["bag_timestamp_ns"] for row in rows
        ]

        header_stamps = [
            row["header_timestamp_ns"]
            for row in rows
            if row["header_timestamp_ns"] is not None
        ]

        differences = [
            row["header_timestamp_ns"]
            - row["bag_timestamp_ns"]
            for row in rows
            if row["header_timestamp_ns"] is not None
        ]

        summaries[topic] = {
            "modality": TOPICS[topic],
            "sample_count": len(rows),
            "header_stamp_count": len(header_stamps),
            "header_equals_bag_count":
                sum(x == 0 for x in differences),
            "header_minus_bag_min_ns":
                min(differences) if differences else None,
            "header_minus_bag_median_ns":
                median(differences) if differences else None,
            "header_minus_bag_max_ns":
                max(differences) if differences else None,
            "bag_intervals": interval_summary(
                bag_stamps
            ),
            "header_intervals": interval_summary(
                header_stamps
            ),
            "frame_ids": sorted({
                row["header_frame_id"] for row in rows
            }),
            "observed_structure_variants":
                sorted({
                    json.dumps(row["structure"], sort_keys=True)
                    for row in rows
                }),
        }

    report = {
        "schema":
            "TRUST_ROBOT_R128_B10_TIMING_AUDIT_V1",
        "bag_sha256": os.environ["BAG_SHA"],
        "reader": "rosbags 0.11.9",
        "sampling_rule":
            "FIRST_128_MESSAGES_PER_SENSOR_TOPIC",
        "messages_examined": examined,
        "decoded_raw_bytes": decoded_bytes,
        "messages_decoded": sum(
            len(rows) for rows in samples.values()
        ),
        "samples": samples,
        "summaries": summaries,
        "predecessor_b9_manifest_sha256":
            os.environ["B9_SHA"],
        "scientific_boundary": {
            "groundtruth_accessed": False,
            "m2dgr_confirmation_accessed": False,
            "sensor_clock_sync_verified": False,
            "physical_capture_event_verified": False,
            "timing_correction_fitted": False,
            "dataset_partition_frozen": False,
            "health_model_trained": False,
            "real_factors_authorized": False,
            "ate_rpe_authorized": False,
            "m2dgr_scientific_gates_closed": 11,
        },
    }

    need(
        valid_report(report, original),
        "PREDECESSOR_LINEAGE_OR_SCOPE",
    )

    # Deliberately corrupt five copies: every one must
    # be rejected by the same validation predicate.
    bad_cases = []

    bad = copy.deepcopy(report)
    bad["bag_sha256"] = "0" * 64
    bad_cases.append(bad)

    bad = copy.deepcopy(report)
    bad["samples"]["/alphasense/imu"].pop()
    bad_cases.append(bad)

    bad = copy.deepcopy(report)
    bad["samples"]["/alphasense/imu"][0][
        "raw_sha256"
    ] = "0" * 64
    bad_cases.append(bad)

    bad = copy.deepcopy(report)
    bad["scientific_boundary"][
        "sensor_clock_sync_verified"
    ] = True
    bad_cases.append(bad)

    bad = copy.deepcopy(report)
    bad["scientific_boundary"][
        "m2dgr_scientific_gates_closed"
    ] = 10
    bad_cases.append(bad)

    need(
        all(not valid_report(x, original) for x in bad_cases),
        "NEGATIVE_CONTROLS",
    )

    report["negative_controls_passed"] = len(bad_cases)

    digest = save(
        "r128_b10_timing_audit_v1.json", report
    )

    print("R128_B10_SENSOR_TOPICS=7_PASS")
    print("R128_B10_DECODED_MESSAGES=896_PASS")
    print("R128_B10_B9_FIRST_12_PER_TOPIC=IDENTICAL")
    print("R128_B10_MESSAGES_EXAMINED=", examined)
    print("R128_B10_NEGATIVE_CONTROLS=5_PASS")

    for topic, summary in summaries.items():
        print(
            "R128_B10_TOPIC",
            topic,
            "HEADER_EQUAL_BAG",
            summary["header_equals_bag_count"],
            "OF",
            summary["header_stamp_count"],
            "MEDIAN_INTERVAL_NS",
            summary["header_intervals"]["median_ns"]
            if summary["header_intervals"] else None,
            "FRAMES",
            summary["frame_ids"],
        )

    print("R128_B10_REPORT_SHA256=", digest)
    print("R128_B10_PHYSICAL_SYNCHRONIZATION=NOT_PROVEN")
    print("R128_B10_SCORING=NOT_AUTHORIZED")


if __name__ == "__main__":
    main()
