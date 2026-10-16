"""S3 independent manifest-based metadata and test verification.

Reconstructs expected envelopes directly from the frozen manifest.
Does not import or trust the S3 builder.
"""

import argparse
import hashlib
import json
import xml.etree.ElementTree as ET

from pathlib import Path


def sha(path):
    return hashlib.sha256(
        Path(path).read_bytes()
    ).hexdigest()


def need(ok, reason):
    if not ok:
        raise AssertionError(
            "S3_INDEPENDENT_FAIL:" + reason
        )


def read(path):
    return json.loads(
        Path(path).read_text()
    )


def main(a):
    root = Path(a.repo)
    result = read(a.report)
    bundle = read(a.metadata)
    s2 = read(a.s2_report)

    need(
        result["schema"]
        == "TRUST_ROBOT_S3_FACTOR_INPUT_CONTRACT_REPORT_V1",
        "REPORT_SCHEMA",
    )

    for key, path in (
        ("engine_sha256", a.engine),
        ("test_source_sha256", a.test),
        ("s2_report_sha256", a.s2_report),
        ("s2_validation_sha256", a.s2_validation),
        ("test_xml_sha256", a.xml),
        ("metadata_sha256", a.metadata),
    ):
        need(
            result[key] == sha(path),
            "SHA_BINDING:" + key,
        )

    need(
        s2["regression_test_count"] == 104
        and s2["regression_counts"]["passed"] == 104,
        "S2_LINEAGE",
    )

    tests = list(
        ET.parse(a.xml).getroot().iter(
            "testcase"
        )
    )

    need(
        len(tests) >= 30
        and len(tests) == result["test_cases_passed"],
        "TEST_COUNT",
    )

    need(
        not any(
            child.tag in (
                "failure",
                "error",
                "skipped",
            )
            for case in tests
            for child in case
        ),
        "TEST_FAILURE",
    )

    manifest = read(
        root /
        "manifests/m2dgr_trajectory_manifest_v1_split_freeze_v1.json"
    )

    matched = [
        record
        for record in manifest["records"]
        if record["base_trajectory_id"] == "gate_01"
    ]

    need(
        len(matched) == 1
        and matched[0]["split"] == "train",
        "FROZEN_TRAIN_SOURCE",
    )

    record = matched[0]

    sources = {
        entry["stream_id"]: entry
        for entry in record["streams"]
    }

    timing = {
        entry["stream_id"]: entry
        for entry in record["synchronization"]
    }

    need(
        bundle["schema"]
        == "TRUST_ROBOT_S3_FOUR_STREAM_METADATA_EXERCISE_V1"
        and bundle["trajectory_id"] == "gate_01"
        and bundle["split_role"] == "train"
        and bundle["illustrative_stamp_only"] is True
        and bundle["actual_sensor_timestamp_observed"] is False
        and bundle["raw_sensor_records_read"] is False
        and bundle["real_pose_factors_generated"] == 0,
        "METADATA_EXERCISE_SCOPE",
    )

    packets = bundle["envelopes"]

    streams = (
        "/camera/color/image_raw/compressed",
        "/camera/imu",
        "/handsfree/imu",
        "/velodyne_points",
    )

    need(
        len(packets) == 4
        and [p["stream_id"] for p in packets] == list(streams),
        "STREAM_INVENTORY",
    )

    for packet in packets:
        stream = packet["stream_id"]
        src = sources[stream]
        clock = timing[stream]

        need(
            clock["verification_status"] == "unverified"
            and clock["fixed_offset_seconds"] is None
            and clock["tolerance_seconds"] is None,
            "UNVERIFIED_TIMING",
        )

        expected = {
            "schema":
                "TRUST_ROBOT_S3_TRAIN_FACTOR_METADATA_ONLY_V1",
            "dataset_id": "M2DGR",
            "trajectory_id": "gate_01",
            "split_role": "train",
            "stream_id": stream,
            "modality": src["modality"],
            "frame_id": src["frame_id"],
            "clock_domain": src["clock_domain"],
            "claimed_header_stamp_ns": 100,
            "header_stamp_origin":
                "CALLER_ASSERTION_NOT_OBSERVED",
            "capture_event_semantics": "UNVERIFIED",
            "temporal_association_status": "UNSELECTED",
            "fixed_offset_seconds": None,
            "association_tolerance_seconds": None,
            "extrinsic_calibration_verified": False,
            "body_T_sensor": None,
            "independent_reference_attested": False,
            "relative_pose": None,
            "factor_covariance": None,
            "qualified_factor_type": "NONE",
            "real_sensor_factor_execution_authorized": False,
            "health_supervision_authorized": False,
            "raw_sensor_payload_opened": False,
            "disposition":
                "STRUCTURAL_METADATA_ONLY_FACTOR_DENIED",
        }

        need(
            packet == expected
            and json.dumps(
                packet,
                sort_keys=True,
                separators=(",", ":"),
            ) == json.dumps(
                expected,
                sort_keys=True,
                separators=(",", ":"),
            ),
            "ENVELOPE_NOT_FROZEN_MANIFEST_BOUND",
        )

    need(
        packets[1]["frame_id"] != packets[2]["frame_id"]
        and packets[1]["clock_domain"]
        != packets[2]["clock_domain"],
        "IMU_SOURCE_CONFLATION",
    )

    for key in (
        "header_stamp_source_authenticity_verified",
        "physical_capture_timing_verified",
        "cross_modal_synchronization_verified",
        "physical_extrinsics_verified",
        "recorded_camera_pose_factor_authorized",
        "recorded_lidar_pose_factor_authorized",
        "recorded_imu_factor_authorized",
        "real_pose_factor_execution_authorized",
        "health_model_training_authorized",
        "raw_sensor_records_read",
        "independent_reference_used",
        "simulator_launch_authorized",
        "github_commit_or_push",
    ):
        need(
            result[key] is False,
            "UNSUPPORTED_CLAIM:" + key,
        )

    for key in (
        "new_sensor_acquisitions",
        "scientific_pose_factors",
        "health_labels",
    ):
        need(
            type(result[key]) is int
            and result[key] == 0,
            "SCIENTIFIC_GATE:" + key,
        )

    validation = {
        "schema":
            "TRUST_ROBOT_S3_INDEPENDENT_VALIDATION_V1",
        "engine_sha256": sha(a.engine),
        "test_source_sha256": sha(a.test),
        "verifier_sha256": sha(__file__),
        "metadata_sha256": sha(a.metadata),
        "report_sha256": sha(a.report),
        "junit_sha256": sha(a.xml),
        "verified_unit_tests": len(tests),
        "verified_train_streams": 4,
        "separate_imu_sources_verified": True,
        "real_sensor_factors_authorized": 0,
        "cross_modal_time_qualified": False,
        "physical_extrinsics_qualified": False,
        "simulator_launch_authorized": False,
        "new_sensor_acquisitions": 0,
        "scientific_pose_factors": 0,
        "health_labels": 0,
    }

    with Path(a.validation).open(
        "x",
        encoding="utf-8",
    ) as stream:
        json.dump(
            validation,
            stream,
            sort_keys=True,
            indent=2,
        )
        stream.write("\n")

    print(
        "S3_INDEPENDENT_UNIT_TESTS="
        f"{len(tests)}_VERIFIED"
    )
    print("S3_INDEPENDENT_TRAIN_STREAMS=4_VERIFIED")
    print("S3_INDEPENDENT_SCIENCE_GATES=CLOSED")
    print("S3_INDEPENDENT_VALIDATION=PASS")


if __name__ == "__main__":
    p = argparse.ArgumentParser()

    for name in (
        "repo",
        "engine",
        "test",
        "s2_report",
        "s2_validation",
        "xml",
        "metadata",
        "report",
        "validation",
    ):
        p.add_argument(
            "--" + name.replace("_", "-"),
            dest=name,
            required=True,
        )

    main(p.parse_args())
