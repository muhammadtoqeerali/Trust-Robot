"""R129-B1: bounded, aggregate-only real sensor diagnostics.

No ground truth, label construction, health classification,
clock fitting, localization scoring, or estimator factor admission.
"""

import copy
import hashlib
import importlib.metadata
import json
import math
import os
import struct
import sys
from pathlib import Path
from statistics import median
from types import SimpleNamespace

import numpy as np

OUT = Path(os.environ["OUT"])
BAG = Path(os.environ["BAG"])
B11 = Path(os.environ["B11"])

LIMIT = 64
MAX_EXAMINED = 10000
MAX_SINGLE_BYTES = 64 * 1024**2
MAX_TOTAL_BYTES = 768 * 1024**2

TOPICS = {
    **{f"/alphasense/cam{i}/image_raw": "camera" for i in range(5)},
    "/alphasense/imu": "imu",
    "/hesai/pandar": "lidar",
}

TYPES = {
    "camera": "sensor_msgs/msg/Image",
    "imu": "sensor_msgs/msg/Imu",
    "lidar": "sensor_msgs/msg/PointCloud2",
}

REPORT_NAME = "r129_b1_aggregate_diagnostics_v1.json"
MANIFEST_NAME = "r129_b1_manifest_v1.json"

SCHEMA = "TRUST_ROBOT_R129_B1_AGGREGATE_DIAGNOSTICS_V1"


def need(ok, reason):
    if not ok:
        raise RuntimeError("R129_B1_DENIED:" + reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def sha_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        while block := f.read(4 * 1024**2):
            h.update(block)
    return h.hexdigest()


def write_json(path, value):
    data = (
        json.dumps(
            value, sort_keys=True, indent=2, allow_nan=False
        ) + "\n"
    ).encode()

    with path.open("xb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())

    return sha(data)


def stamp_ns(header):
    stamp = getattr(header, "stamp", None)
    if stamp is None:
        return None

    sec = getattr(stamp, "sec", getattr(stamp, "secs", None))
    ns = getattr(
        stamp, "nanosec",
        getattr(stamp, "nsec", getattr(stamp, "nsecs", None))
    )

    if not (
        type(sec) is int
        and type(ns) is int
        and sec >= 0
        and 0 <= ns < 1_000_000_000
    ):
        return None

    return sec * 1_000_000_000 + ns


def camera_feature(msg):
    w = int(msg.width)
    h = int(msg.height)
    step = int(msg.step)
    data = memoryview(msg.data).cast("B")

    need(
        w >= 16 and h >= 16
        and step >= w
        and step * h == len(data)
        and str(msg.encoding) == "mono8",
        "CAMERA_LAYOUT",
    )

    image = np.frombuffer(
        data, dtype=np.uint8
    ).reshape(h, step)[:, :w]

    sample = image[::8, ::8].astype(np.float64)
    gx = np.abs(np.diff(sample, axis=1))
    gy = np.abs(np.diff(sample, axis=0))

    return {
        "pixel_mean": float(sample.mean()),
        "pixel_std": float(sample.std()),
        "zero_fraction": float(np.mean(sample == 0)),
        "max_fraction": float(np.mean(sample == 255)),
        "spatial_gradient": float((gx.mean() + gy.mean()) / 2),
    }


def imu_feature(msg):
    need(
        len(msg.orientation_covariance) == 9
        and len(msg.angular_velocity_covariance) == 9
        and len(msg.linear_acceleration_covariance) == 9,
        "IMU_COVARIANCE_LAYOUT",
    )

    a = msg.linear_acceleration
    g = msg.angular_velocity

    av = [float(a.x), float(a.y), float(a.z)]
    gv = [float(g.x), float(g.y), float(g.z)]

    finite = all(math.isfinite(x) for x in av + gv)

    return {
        "finite_components": finite,
        "acceleration_norm": (
            math.sqrt(sum(x*x for x in av)) if finite else None
        ),
        "angular_rate_norm": (
            math.sqrt(sum(x*x for x in gv)) if finite else None
        ),
        "_accel_vector": av if finite else None,
        "_gyro_vector": gv if finite else None,
    }


def lidar_feature(msg):
    fields = {
        str(f.name): (int(f.offset), int(f.datatype), int(f.count))
        for f in msg.fields
    }

    width = int(msg.width)
    height = int(msg.height)
    point_step = int(msg.point_step)
    row_step = int(msg.row_step)
    data = memoryview(msg.data).cast("B")

    need(
        0 < width <= 500000
        and height == 1
        and 12 <= point_step <= 256
        and row_step >= width * point_step
        and len(data) == row_step,
        "LIDAR_LAYOUT",
    )

    offsets = []

    for name in ("x", "y", "z"):
        need(name in fields, "LIDAR_MISSING_XYZ")
        offset, datatype, count = fields[name]

        need(
            datatype == 7
            and count == 1
            and 0 <= offset <= point_step - 4,
            "LIDAR_XYZ_DATATYPE_OR_OFFSET",
        )

        offsets.append(offset)

    need(
        all(
            abs(offsets[i] - offsets[j]) >= 4
            for i in range(3)
            for j in range(i + 1, 3)
        ),
        "LIDAR_OVERLAPPING_XYZ",
    )

    endian = ">" if bool(msg.is_bigendian) else "<"

    dtype = np.dtype({
        "names": ["x", "y", "z"],
        "formats": [endian + "f4"] * 3,
        "offsets": offsets,
        "itemsize": point_step,
    })

    points = np.frombuffer(data, dtype=dtype, count=width)

    xyz = np.column_stack([
        points["x"], points["y"], points["z"]
    ]).astype(np.float64)

    finite = np.all(np.isfinite(xyz), axis=1)
    good = xyz[finite]

    ranges = (
        np.linalg.norm(good, axis=1)
        if len(good) else np.empty(0)
    )

    return {
        "point_count": width,
        "finite_xyz_fraction": float(np.mean(finite)),
        "range_median": (
            float(np.median(ranges)) if len(ranges) else None
        ),
        "range_p95": (
            float(np.percentile(ranges, 95))
            if len(ranges) else None
        ),
        "declared_dense": bool(msg.is_dense),
    }


def expect_reject(action):
    try:
        action()
    except RuntimeError as exc:
        need(
            str(exc).startswith("R129_B1_DENIED:"),
            "UNEXPECTED_REJECTION",
        )
        return
    raise RuntimeError("R129_B1_NEGATIVE_ACCEPTED")


def synthetic_tests():
    cam = SimpleNamespace(
        width=16, height=16, step=16,
        encoding="mono8", data=bytes(range(256)),
    )
    need(camera_feature(cam)["pixel_mean"] >= 0, "VALID_CAMERA")

    bad = copy.copy(cam)
    bad.data = b"x"
    expect_reject(lambda: camera_feature(bad))

    bad = copy.copy(cam)
    bad.encoding = "rgb8"
    expect_reject(lambda: camera_feature(bad))

    vec = SimpleNamespace(x=1.0, y=2.0, z=3.0)
    imu = SimpleNamespace(
        linear_acceleration=vec,
        angular_velocity=vec,
        orientation_covariance=[0] * 9,
        angular_velocity_covariance=[0] * 9,
        linear_acceleration_covariance=[0] * 9,
    )

    need(imu_feature(imu)["finite_components"], "VALID_IMU")

    bad = copy.copy(imu)
    bad.orientation_covariance = [0] * 8
    expect_reject(lambda: imu_feature(bad))

    fields = [
        SimpleNamespace(name=n, offset=i*4, datatype=7, count=1)
        for i, n in enumerate(("x", "y", "z"))
    ]

    raw = bytearray(96)
    struct.pack_into("<fff", raw, 0, 1.0, 2.0, 3.0)
    struct.pack_into("<fff", raw, 48, 4.0, 5.0, 6.0)

    lidar = SimpleNamespace(
        width=2, height=1, point_step=48, row_step=96,
        fields=fields, data=bytes(raw),
        is_bigendian=False, is_dense=True,
    )

    need(
        lidar_feature(lidar)["finite_xyz_fraction"] == 1.0,
        "VALID_LIDAR",
    )

    bad = copy.copy(lidar)
    bad.fields = copy.deepcopy(fields)
    bad.fields[2].datatype = 6
    expect_reject(lambda: lidar_feature(bad))

    bad = copy.copy(lidar)
    bad.fields = copy.deepcopy(fields)
    bad.fields[2].offset = 6
    expect_reject(lambda: lidar_feature(bad))

    bad = copy.copy(lidar)
    bad.data = bytes(raw[:10])
    expect_reject(lambda: lidar_feature(bad))

    return 6


def numeric_stats(values):
    good = [
        float(v) for v in values
        if v is not None and math.isfinite(float(v))
    ]

    return {
        "finite_count": len(good),
        "min": min(good) if good else None,
        "median": median(good) if good else None,
        "max": max(good) if good else None,
    }


def validate_report(report):
    scope = report.get("scientific_boundary", {})

    if not (
        report.get("schema") == SCHEMA
        and report.get("source_bag_sha256")
            == os.environ["BAG_SHA"]
        and report.get("source_b11_manifest_sha256")
            == os.environ["B11_MAN_SHA"]
        and report.get("decoded_messages") == 448
        and report.get("sample_limit_per_topic") == LIMIT
        and set(report.get("topics", {})) == set(TOPICS)
        and scope.get("groundtruth_accessed") is False
        and scope.get("training_performed") is False
        and scope.get("metric_scoring_authorized") is False
        and scope.get("physical_clock_sync_proven") is False
        and scope.get("real_factors_authorized") is False
        and scope.get("m2dgr_scientific_gates_closed") == 11
    ):
        return False

    return all(
        row.get("sample_count") == LIMIT
        and row.get("header_equals_bag_count") == LIMIT
        and row.get("median_interval_ns", 0) > 0
        and len(row.get("frame_ids", [])) == 1
        and isinstance(
            row.get("message_fingerprint_sha256"), str
        )
        and len(row["message_fingerprint_sha256"]) == 64
        for row in report["topics"].values()
    )


def report_negative_tests(report):
    bad = copy.deepcopy(report)
    bad["source_bag_sha256"] = "0" * 64

    bad2 = copy.deepcopy(report)
    bad2["topics"]["/alphasense/imu"]["sample_count"] = 63

    bad3 = copy.deepcopy(report)
    bad3["scientific_boundary"]["metric_scoring_authorized"] = True

    need(
        all(
            not validate_report(x)
            for x in (bad, bad2, bad3)
        ),
        "REPORT_NEGATIVE_CONTROLS",
    )

    return 3


def run():
    need(
        importlib.metadata.version("rosbags") == "0.11.9"
        and np.__version__ == "2.5.4",
        "DEPENDENCY_PINS",
    )

    m = json.loads(
        (B11 / "manifest_v1.json").read_text()
    )
    prior = json.loads(
        (B11 / "r128_b11_sanitized_summary_v1.json").read_text()
    )

    need(
        sha_file(B11 / "manifest_v1.json")
        == os.environ["B11_MAN_SHA"]
        and sha_file(
            B11 / "r128_b11_sanitized_summary_v1.json"
        ) == os.environ["B11_SUM_SHA"],
        "B11_HASHES",
    )

    need(
        m["source_bag_sha256"] == os.environ["BAG_SHA"]
        and prior["sensor_topic_count"] == 7
        and prior["decoded_message_count"] == 896,
        "PREDECESSOR_PROVENANCE",
    )

    negative_count = synthetic_tests()
    print("R129_B1_SYNTHETIC_NEGATIVE_CONTROLS=6_PASS")

    need(
        BAG.stat().st_size == 6260771085
        and sha_file(BAG) == os.environ["BAG_SHA"],
        "SOURCE_BAG_HASH",
    )

    print("R129_B1_FULL_SOURCE_BAG_SHA256=PASS")

    from rosbags.highlevel import AnyReader
    from rosbags.typesys import Stores, get_typestore

    samples = {topic: [] for topic in TOPICS}
    timestamps = {topic: [] for topic in TOPICS}
    frames = {topic: set() for topic in TOPICS}
    fingerprints = {
        topic: hashlib.sha256() for topic in TOPICS
    }

    examined = 0
    decoded_bytes = 0

    store = get_typestore(Stores.ROS1_NOETIC)

    with AnyReader(
        [BAG], default_typestore=store
    ) as reader:

        need(reader.message_count == 45082, "MESSAGE_COUNT")

        connections = [
            c for c in reader.connections if c.topic in TOPICS
        ]

        need(len(connections) == 7, "CONNECTION_COUNT")

        for c in connections:
            need(
                c.msgtype == TYPES[TOPICS[c.topic]],
                "MESSAGE_TYPE",
            )

        for connection, bag_ns, raw in reader.messages(
            connections=connections
        ):
            examined += 1
            need(examined <= MAX_EXAMINED, "SCAN_BUDGET")

            topic = connection.topic

            if len(samples[topic]) == LIMIT:
                continue

            need(
                0 < len(raw) <= MAX_SINGLE_BYTES,
                "SINGLE_MESSAGE_BUDGET",
            )

            decoded_bytes += len(raw)
            need(
                decoded_bytes <= MAX_TOTAL_BYTES,
                "TOTAL_DECODE_BUDGET",
            )

            msg = reader.deserialize(
                raw, connection.msgtype
            )

            header = getattr(msg, "header", None)
            stamp = stamp_ns(header)
            frame = str(getattr(header, "frame_id", ""))

            need(
                stamp is not None and stamp == bag_ns,
                "R128_TIMESTAMP_LINEAGE",
            )

            need(
                frame in prior["topics"][topic]["frame_ids"],
                "FRAME_LINEAGE",
            )

            kind = TOPICS[topic]

            if kind == "camera":
                feature = camera_feature(msg)
            elif kind == "imu":
                feature = imu_feature(msg)
            else:
                feature = lidar_feature(msg)

            samples[topic].append(feature)
            timestamps[topic].append(int(stamp))
            frames[topic].add(frame)

            fingerprint = fingerprints[topic]
            fingerprint.update(hashlib.sha256(raw).digest())
            fingerprint.update(int(bag_ns).to_bytes(8, "big"))
            fingerprint.update(int(stamp).to_bytes(8, "big"))
            fingerprint.update(frame.encode("utf-8") + b"\0")

            if all(
                len(rows) == LIMIT
                for rows in samples.values()
            ):
                break

    need(
        all(len(rows) == LIMIT for rows in samples.values()),
        "INCOMPLETE_SAMPLE",
    )

    aggregates = {}

    for topic, kind in TOPICS.items():
        rows = samples[topic]
        times = timestamps[topic]

        periods = [
            b - a for a, b in zip(times, times[1:])
        ]

        need(
            len(periods) == LIMIT - 1
            and all(x > 0 for x in periods),
            "NONMONOTONIC_SAMPLE",
        )

        if kind == "camera":
            metric_names = (
                "pixel_mean", "pixel_std",
                "zero_fraction", "max_fraction",
                "spatial_gradient",
            )

        elif kind == "imu":
            metric_names = (
                "acceleration_norm", "angular_rate_norm"
            )

        else:
            metric_names = (
                "point_count", "finite_xyz_fraction",
                "range_median", "range_p95",
            )

        stats = {
            key: numeric_stats(row[key] for row in rows)
            for key in metric_names
        }

        flags = {}

        if kind == "imu":
            flags["finite_component_count"] = sum(
                row["finite_components"] for row in rows
            )

            for label, key in (
                ("acceleration_delta_norm", "_accel_vector"),
                ("angular_velocity_delta_norm", "_gyro_vector"),
            ):
                deltas = []

                for left, right in zip(rows, rows[1:]):
                    a = left[key]
                    b = right[key]

                    if a is None or b is None:
                        continue

                    deltas.append(
                        math.sqrt(sum(
                            (x - y)**2 for x, y in zip(a, b)
                        ))
                    )

                stats[label] = numeric_stats(deltas)

        elif kind == "lidar":
            flags["declared_dense_count"] = sum(
                row["declared_dense"] for row in rows
            )

        aggregates[topic] = {
            "modality": kind,
            "sample_count": len(rows),
            "frame_ids": sorted(frames[topic]),
            "header_equals_bag_count": len(rows),
            "min_interval_ns": min(periods),
            "median_interval_ns": median(periods),
            "max_interval_ns": max(periods),
            "message_fingerprint_sha256":
                fingerprints[topic].hexdigest(),
            "feature_statistics": stats,
            "descriptive_flags": flags,
        }

    report = {
        "schema": SCHEMA,
        "dataset": "Hilti-Oxford 2022",
        "recording": "exp14_basement_2",
        "source_bag_sha256": os.environ["BAG_SHA"],
        "source_b11_manifest_sha256":
            os.environ["B11_MAN_SHA"],
        "source_b11_summary_sha256":
            os.environ["B11_SUM_SHA"],
        "reader": "rosbags==0.11.9",
        "numpy": "2.5.4",
        "sampling_rule": "FIRST_64_MESSAGES_PER_SENSOR_TOPIC",
        "sample_limit_per_topic": LIMIT,
        "decoded_messages": 7 * LIMIT,
        "messages_examined": examined,
        "decoded_raw_bytes": decoded_bytes,
        "camera_sampling_stride_pixels": 8,
        "feature_scope": "DESCRIPTIVE_AGGREGATES_ONLY",
        "topics": aggregates,
        "synthetic_negative_controls_passed": negative_count,
        "scientific_boundary": {
            "groundtruth_accessed": False,
            "physical_clock_sync_proven": False,
            "independent_6dof_reference_proven": False,
            "dataset_partition_frozen": False,
            "training_performed": False,
            "health_labels_constructed": False,
            "metric_scoring_authorized": False,
            "real_factors_authorized": False,
            "m2dgr_confirmation_test_accessed": False,
            "m2dgr_scientific_gates_closed": 11,
        },
    }

    need(validate_report(report), "REPORT_VALIDATION")
    report_negative_tests(report)

    need(
        not (OUT / REPORT_NAME).exists()
        and not (OUT / MANIFEST_NAME).exists(),
        "OUTPUT_ALREADY_EXISTS",
    )

    report_hash = write_json(
        OUT / REPORT_NAME, report
    )

    manifest = {
        "schema": "TRUST_ROBOT_R129_B1_MANIFEST_V1",
        "source_bag_sha256": os.environ["BAG_SHA"],
        "source_b11_manifest_sha256":
            os.environ["B11_MAN_SHA"],
        "extractor_sha256": sha_file(__file__),
        "report_sha256": report_hash,
        "report_negative_controls_passed": 3,
        "synthetic_negative_controls_passed": 6,
        "per_message_data_exported": False,
        "groundtruth_included": False,
        "scoring_authorized": False,
        "m2dgr_scientific_gates_closed": 11,
    }

    manifest_hash = write_json(
        OUT / MANIFEST_NAME, manifest
    )

    print("R129_B1_SENSOR_TOPICS=7_PASS")
    print("R129_B1_DECODED_MESSAGES=448_PASS")
    print("R129_B1_MESSAGES_EXAMINED=", examined)
    print("R129_B1_DECODED_RAW_BYTES=", decoded_bytes)
    print("R129_B1_REPORT_NEGATIVE_CONTROLS=3_PASS")

    for topic, row in aggregates.items():
        print(
            "R129_B1_TOPIC", topic,
            "MEDIAN_INTERVAL_NS", row["median_interval_ns"],
            "FEATURES", sorted(row["feature_statistics"]),
        )

    print("R129_B1_REPORT_SHA256=", report_hash)
    print("R129_B1_MANIFEST_SHA256=", manifest_hash)


def verify():
    report_path = OUT / REPORT_NAME
    manifest_path = OUT / MANIFEST_NAME

    need(
        report_path.is_file()
        and manifest_path.is_file(),
        "MISSING_OUTPUT",
    )

    report = json.loads(report_path.read_text())
    manifest = json.loads(manifest_path.read_text())

    need(
        manifest["schema"]
        == "TRUST_ROBOT_R129_B1_MANIFEST_V1",
        "MANIFEST_SCHEMA",
    )

    need(
        sha_file(__file__) == manifest["extractor_sha256"],
        "EXTRACTOR_HASH",
    )

    need(
        sha_file(report_path) == manifest["report_sha256"],
        "REPORT_HASH",
    )

    need(
        manifest["source_bag_sha256"]
        == os.environ["BAG_SHA"]
        and manifest["source_b11_manifest_sha256"]
        == os.environ["B11_MAN_SHA"],
        "SOURCE_LINEAGE",
    )

    need(
        manifest["per_message_data_exported"] is False
        and manifest["groundtruth_included"] is False
        and manifest["scoring_authorized"] is False
        and manifest["m2dgr_scientific_gates_closed"] == 11,
        "MANIFEST_SCOPE",
    )

    need(validate_report(report), "REPORT_SCOPE")

    need(
        report["synthetic_negative_controls_passed"] == 6
        and manifest["report_negative_controls_passed"] == 3,
        "TEST_COUNTS",
    )

    report_negative_tests(report)

    need(
        {
            p.name for p in OUT.iterdir()
        } == {
            "r129_b1_diagnostics.py",
            REPORT_NAME,
            MANIFEST_NAME,
        },
        "UNEXPECTED_OUTPUT_FILE",
    )

    print("R129_B1_VERIFY_SOURCE_HASH=PASS")
    print("R129_B1_VERIFY_REPORT_HASH=PASS")
    print("R129_B1_VERIFY_SEVEN_TOPICS=PASS")
    print("R129_B1_VERIFY_448_MESSAGES=PASS")
    print("R129_B1_VERIFY_REPORT_NEGATIVES=3_PASS")
    print("R129_B1_VERIFY_SCIENTIFIC_GATES=11_CLOSED")
    print("R129_B1_STANDALONE_VERIFIER=PASS")


if __name__ == "__main__":
    need(len(sys.argv) == 2, "COMMAND")
    command = sys.argv[1]

    if command == "run":
        run()
    elif command == "verify":
        verify()
    else:
        raise RuntimeError("R129_B1_INVALID_COMMAND")
