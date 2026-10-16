"""S4 independent comparison to the frozen source manifests.

Does not import the S4 assessment builder.
"""

import argparse
import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path

GATES = (
    "physical_capture_event_verified",
    "sensor_clock_domain_verified",
    "cross_stream_offset_verified",
    "association_tolerance_qualified",
    "full_body_sensor_extrinsic_verified",
    "independent_reference_origin_and_time_verified",
    "factor_covariance_empirically_calibrated",
    "recorded_factor_execution_authorized",
)


def sha(path):
    return hashlib.sha256(
        Path(path).read_bytes()
    ).hexdigest()


def load(path):
    return json.loads(
        Path(path).read_text()
    )


def need(value, reason):
    if not value:
        raise AssertionError(
            "S4_INDEPENDENT_FAIL:" + reason
        )


def main(a):
    root = Path(a.repo)
    matrix = load(a.matrix)
    report = load(a.report)
    s3 = load(a.s3_metadata)

    source_paths = {
        "trajectory":
            "manifests/m2dgr_trajectory_manifest_v1_split_freeze_v1.json",
        "calibration":
            "manifests/m2dgr_calibration_evidence_v1.json",
        "reference":
            "manifests/m2dgr_reference_temporal_association_evidence_v1.json",
        "protocol":
            "configs/trust_robot/m2dgr_trajectory_association_evaluation_protocol_candidate_v2.json",
    }

    for key, relative in source_paths.items():
        need(
            matrix["frozen_sources_sha256"][key]
            == sha(root / relative),
            "FROZEN_SOURCE_SHA:" + key,
        )

    need(
        matrix["frozen_sources_sha256"]["s3_metadata"]
        == sha(a.s3_metadata),
        "S3_LINEAGE",
    )

    manifest = load(
        root / source_paths["trajectory"]
    )

    cal = load(
        root / source_paths["calibration"]
    )

    ref = load(
        root / source_paths["reference"]
    )

    protocol = load(
        root / source_paths["protocol"]
    )

    train = [
        x for x in manifest["records"]
        if x["base_trajectory_id"] == "gate_01"
    ]

    need(
        len(train) == 1
        and train[0]["split"] == "train",
        "TRAIN_SOURCE",
    )

    record = train[0]

    sources = {
        x["stream_id"]: x
        for x in record["streams"]
    }

    clocks = {
        x["stream_id"]: x
        for x in record["synchronization"]
    }

    bag = record["calibration_artifacts"]

    need(
        len(bag) == 1
        and bag[0]["verification_status"] == "verified"
        and bag[0]["applies_to_stream_ids"] == []
        and bag[0]["applies_to_frame_ids"] == [],
        "BAG_INTEGRITY_NOT_CALIBRATION",
    )

    need(
        cal["interpretation"][
            "dataset_calibration_verified"
        ] is False
        and cal["interpretation"][
            "d435i_imu_relative_rotation_support_is_full_extrinsic_verification"
        ] is False,
        "CALIBRATION_GATE",
    )

    need(
        ref["policy"][
            "reference_to_estimator_temporal_association_verified"
        ] is False
        and protocol["authorization"][
            "estimator_scoring_authorized"
        ] is False,
        "REFERENCE_GATE",
    )

    rows = matrix["streams"]
    packets = s3["envelopes"]

    need(
        len(rows) == len(packets) == 4
        and matrix["stream_count"] == 4
        and matrix["gate_count_per_stream"] == 8
        and matrix["unqualified_gate_instances"] == 32,
        "MATRIX_COUNTS",
    )

    for row, packet in zip(rows, packets):
        sid = packet["stream_id"]
        src = sources[sid]
        sync = clocks[sid]

        need(
            row["trajectory_id"] == "gate_01"
            and row["split_role"] == "train"
            and row["stream_id"] == sid
            and row["modality"] == src["modality"]
            and row["frame_id"] == src["frame_id"]
            and row["clock_domain"] == src["clock_domain"]
            and row["timestamp_unit"] == "nanoseconds",
            "STREAM_LINEAGE",
        )

        need(
            sync["verification_status"] == "unverified"
            and sync["fixed_offset_seconds"] is None
            and sync["tolerance_seconds"] is None
            and row["header_timestamp_basis"]
            == "sensor_header_stamp"
            and row["sensor_sync_status"] == "unverified"
            and row["fixed_offset_seconds"] is None
            and row["association_tolerance_seconds"] is None,
            "TIME_GATE",
        )

        need(
            row["illustrative_header_stamp_ns"] == 100
            and row["actual_header_observed"] is False
            and row["header_stamp_authenticated"] is False
            and row["sensor_payload_read"] is False,
            "HEADER_PROVENANCE",
        )

        need(
            row["bag_integrity_sha256"] == bag[0]["sha256"]
            and row["bag_integrity_verified"] is True
            and row["bag_integrity_proves_calibration"] is False,
            "BAG_OR_CALIBRATION_CLAIM",
        )

        need(
            row["camera_intrinsics_verified"] is False
            and row["partial_rotation_proves_full_extrinsic"]
            is False
            and row["physical_body_T_sensor"] is None
            and row["relative_pose_factor"] is None
            and row["factor_covariance"] is None,
            "UNVERIFIED_PHYSICAL_FACTOR",
        )

        need(
            row["d435i_relative_rotation_content_supported"]
            is (sid == "/camera/imu"),
            "PARTIAL_ROTATION_INTERPRETATION",
        )

        need(
            set(row["requirement_gates"]) == set(GATES)
            and all(
                value is False
                for value in row["requirement_gates"].values()
            )
            and row["disposition"]
            == "UNQUALIFIED_RECORDED_FACTOR_INPUT",
            "GATE_PROMOTION",
        )

    need(
        matrix["physical_time_qualified"] is False
        and matrix["full_extrinsics_qualified"] is False
        and matrix["recorded_factor_admission_authorized"]
        is False,
        "OVERALL_QUALIFICATION",
    )

    need(
        report["schema"]
        == "TRUST_ROBOT_S4_SOURCE_LINEAGE_REVIEW_V1"
        and report["engine_sha256"] == sha(a.engine)
        and report["test_sha256"] == sha(a.test)
        and report["s3_report_sha256"] == sha(a.s3_report)
        and report["s3_validation_sha256"]
        == sha(a.s3_validation)
        and report["matrix_sha256"] == sha(a.matrix)
        and report["junit_sha256"] == sha(a.xml),
        "REPORT_LINEAGE",
    )

    tests = list(
        ET.parse(a.xml).getroot().iter(
            "testcase"
        )
    )

    need(
        len(tests) >= 40
        and len(tests) == report["tests_passed"]
        and all(
            not any(
                child.tag in ("failure", "error", "skipped")
                for child in test
            )
            for test in tests
        ),
        "UNIT_TESTS",
    )

    need(
        report["recorded_sensor_factors_generated"] == 0
        and report["new_sensor_acquisitions"] == 0
        and report["scientific_pose_factors"] == 0
        and report["health_labels"] == 0,
        "SCIENCE_COUNTS",
    )

    for key in (
        "raw_bag_hash_means_calibration",
        "camera_intrinsics_verified",
        "camera_lidar_full_extrinsic_verified",
        "handsfree_lidar_full_extrinsic_verified",
        "real_capture_timestamp_observed",
        "cross_modal_time_association_performed",
        "calibration_values_created",
        "reference_scoring_performed",
        "health_training_performed",
        "git_commit_or_push",
    ):
        need(
            report[key] is False,
            "UNSUPPORTED_CLAIM:" + key,
        )

    validation = {
        "schema":
            "TRUST_ROBOT_S4_INDEPENDENT_VALIDATION_V1",
        "engine_sha256": sha(a.engine),
        "test_sha256": sha(a.test),
        "verifier_sha256": sha(__file__),
        "matrix_sha256": sha(a.matrix),
        "report_sha256": sha(a.report),
        "junit_sha256": sha(a.xml),
        "verified_tests": len(tests),
        "verified_source_streams": 4,
        "verified_closed_gate_instances": 32,
        "bag_integrity_not_calibration": True,
        "partial_rotation_not_full_extrinsic": True,
        "physical_sensor_time_verified": False,
        "full_extrinsics_verified": False,
        "recorded_factor_execution_authorized": False,
        "new_sensor_acquisitions": 0,
        "scientific_pose_factors": 0,
        "health_labels": 0,
    }

    with Path(a.validation).open(
        "x",
        encoding="utf-8",
    ) as f:
        json.dump(
            validation,
            f,
            sort_keys=True,
            indent=2,
        )
        f.write("\n")

    print(
        f"S4_INDEPENDENT_TESTS={len(tests)}_VERIFIED"
    )
    print("S4_INDEPENDENT_STREAMS=4_VERIFIED")
    print("S4_INDEPENDENT_CLOSED_GATES=32_VERIFIED")
    print("S4_INDEPENDENT_VALIDATION=PASS")


if __name__ == "__main__":
    p = argparse.ArgumentParser()

    for name in (
        "repo",
        "engine",
        "test",
        "s3_metadata",
        "s3_report",
        "s3_validation",
        "xml",
        "matrix",
        "report",
        "validation",
    ):
        p.add_argument(
            "--" + name.replace("_", "-"),
            dest=name,
            required=True,
        )

    main(p.parse_args())
