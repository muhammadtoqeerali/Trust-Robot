"""S4 frozen recorded-source requirements.

All inputs are pre-existing manifest and synthetic metadata.
This module does not create sensor measurements or pose factors.
"""

import argparse
import copy
import hashlib
import json
import xml.etree.ElementTree as ET

from pathlib import Path

from trust_robot.m2dgr_sensor_admission import (
    load_frozen_snapshot,
)

from s3_contract import (
    build_envelope,
    canonical,
    parse_envelope,
)

SCHEMA = "TRUST_ROBOT_S4_SOURCE_REQUIREMENTS_V1"

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

REQUIREMENTS = {
    "physical_capture_event_verified":
        "Independent source-specific measurement-event semantics",
    "sensor_clock_domain_verified":
        "Physically supported capture clock and epoch relation",
    "cross_stream_offset_verified":
        "Independent modality-to-modality time-offset evidence",
    "association_tolerance_qualified":
        "Predeclared justified cross-modal association policy",
    "full_body_sensor_extrinsic_verified":
        "Complete physically applicable body-to-sensor transform",
    "independent_reference_origin_and_time_verified":
        "Independent reference origin, timebase and association",
    "factor_covariance_empirically_calibrated":
        "Supported modality-specific factor noise model",
    "recorded_factor_execution_authorized":
        "Separate versioned scientific admission authorization",
}


class S4Error(ValueError):
    pass


def need(value, reason):
    if not value:
        raise S4Error(reason)


def sha(path):
    return hashlib.sha256(
        Path(path).read_bytes()
    ).hexdigest()


def read(path):
    p = Path(path)

    need(
        p.is_file()
        and not p.is_symlink()
        and p.stat().st_size < 5000000,
        "UNSAFE_INPUT",
    )

    return json.loads(
        p.read_text(encoding="utf-8")
    )


def write(path, value):
    with Path(path).open(
        "x",
        encoding="utf-8",
    ) as f:
        json.dump(
            value,
            f,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        f.write("\n")


def lineage(repo, s3_metadata):
    repo = Path(repo)

    paths = {
        "trajectory":
            "manifests/m2dgr_trajectory_manifest_v1_split_freeze_v1.json",
        "calibration":
            "manifests/m2dgr_calibration_evidence_v1.json",
        "reference":
            "manifests/m2dgr_reference_temporal_association_evidence_v1.json",
        "protocol":
            "configs/trust_robot/m2dgr_trajectory_association_evaluation_protocol_candidate_v2.json",
    }

    files = {
        key: repo / relative
        for key, relative in paths.items()
    }

    data = {
        key: read(path)
        for key, path in files.items()
    }

    snapshot = load_frozen_snapshot(repo)

    s3 = read(s3_metadata)

    need(
        s3["schema"]
        == "TRUST_ROBOT_S3_FOUR_STREAM_METADATA_EXERCISE_V1"
        and s3["trajectory_id"] == "gate_01"
        and s3["split_role"] == "train"
        and s3["illustrative_stamp_only"] is True
        and s3["actual_sensor_timestamp_observed"] is False,
        "S3_SOURCE_SCOPE",
    )

    need(
        len(s3["envelopes"]) == 4,
        "S3_STREAM_COUNT",
    )

    cal = data["calibration"]
    ref = data["reference"]
    prot = data["protocol"]

    need(
        cal["interpretation"]["dataset_calibration_verified"]
        is False
        and cal["interpretation"][
            "camera_intrinsics_verified"
        ] is False
        and cal["interpretation"][
            "camera_lidar_extrinsic_verified"
        ] is False
        and cal["interpretation"][
            "handsfree_lidar_full_extrinsic_verified"
        ] is False,
        "UNEXPECTED_CALIBRATION",
    )

    need(
        cal["interpretation"][
            "d435i_imu_relative_rotation_has_independent_released_sensor_content_support"
        ] is True
        and cal["interpretation"][
            "d435i_imu_relative_rotation_support_is_full_extrinsic_verification"
        ] is False,
        "PARTIAL_ROTATION_EVIDENCE",
    )

    need(
        ref["policy"][
            "reference_to_estimator_temporal_association_verified"
        ] is False
        and ref["policy"][
            "association_tolerance_frozen"
        ] is False,
        "REFERENCE_ASSOCIATION_UNQUALIFIED",
    )

    need(
        prot["status"]
        == "blocked_pending_physical_evidence"
        and prot["authorization"][
            "estimator_scoring_authorized"
        ] is False
        and prot["authorization"][
            "association_execution_authorized"
        ] is False
        and prot["authorization"][
            "confirmation_test_partition_closed"
        ] is True,
        "PROTOCOL_UNEXPECTEDLY_OPEN",
    )

    need(
        all(
            v is False
            for v in snapshot["scientific_gates"].values()
        ),
        "SNAPSHOT_GATE",
    )

    records = data["trajectory"]["records"]

    named = [
        x for x in records
        if x["base_trajectory_id"] == "gate_01"
    ]

    need(
        len(named) == 1
        and named[0]["split"] == "train",
        "FROZEN_TRAIN_IDENTITY",
    )

    bag = named[0]["calibration_artifacts"]

    need(
        len(bag) == 1
        and bag[0]["artifact_id"] == "gate_01_bag_sha256"
        and bag[0]["verification_status"] == "verified"
        and bag[0]["applies_to_stream_ids"] == []
        and bag[0]["applies_to_frame_ids"] == []
        and len(bag[0]["sha256"]) == 64,
        "RAW_BAG_INTEGRITY_NOT_CALIBRATION",
    )

    fingerprints = {
        key: sha(path)
        for key, path in files.items()
    }

    fingerprints["s3_metadata"] = sha(s3_metadata)

    return snapshot, named[0], s3, fingerprints


def build_rows(repo, s3_metadata):
    snapshot, trajectory, s3, hashes = lineage(
        repo,
        s3_metadata,
    )

    sources = {
        x["stream_id"]: x
        for x in trajectory["streams"]
    }

    timing = {
        x["stream_id"]: x
        for x in trajectory["synchronization"]
    }

    bag = trajectory["calibration_artifacts"][0]

    rows = []

    for packet in s3["envelopes"]:
        stream = packet["stream_id"]

        need(
            stream in sources
            and stream in timing,
            "UNREGISTERED_STREAM",
        )

        # Re-run the frozen S3 structural validation.
        need(
            parse_envelope(
                snapshot,
                canonical(packet),
            ) == packet,
            "S3_ENVELOPE_REVALIDATION",
        )

        need(
            build_envelope(
                snapshot,
                "gate_01",
                stream,
                100,
            ) == packet,
            "S3_FROZEN_SAMPLE",
        )

        source = sources[stream]
        clock = timing[stream]

        need(
            clock["verification_status"] == "unverified"
            and clock["fixed_offset_seconds"] is None
            and clock["tolerance_seconds"] is None
            and clock["tolerance_selected_on_split"] is None,
            "TIMING_PROMOTION",
        )

        need(
            source["clock_domain"]
            == clock["clock_domain"]
            and source["frame_id"] == packet["frame_id"]
            and source["modality"] == packet["modality"],
            "SOURCE_IDENTITY",
        )

        row = {
            "trajectory_id": "gate_01",
            "split_role": "train",
            "stream_id": stream,
            "modality": source["modality"],
            "frame_id": source["frame_id"],
            "clock_domain": source["clock_domain"],
            "timestamp_unit": source["timestamp_unit"],
            "header_timestamp_basis":
                clock["measurement_time_basis"],
            "illustrative_header_stamp_ns": 100,
            "actual_header_observed": False,
            "header_stamp_authenticated": False,
            "sensor_sync_status": "unverified",
            "fixed_offset_seconds": None,
            "association_tolerance_seconds": None,
            "bag_integrity_sha256": bag["sha256"],
            "bag_integrity_verified": True,
            "bag_integrity_proves_calibration": False,
            "sensor_payload_read": False,
            "camera_intrinsics_verified": False,
            "d435i_relative_rotation_content_supported":
                source["stream_id"] == "/camera/imu",
            "partial_rotation_proves_full_extrinsic": False,
            "physical_body_T_sensor": None,
            "relative_pose_factor": None,
            "factor_covariance": None,
            "requirement_gates": {
                key: False
                for key in GATES
            },
            "disposition":
                "UNQUALIFIED_RECORDED_FACTOR_INPUT",
        }

        rows.append(row)

    need(
        len(rows) == 4
        and len({
            x["stream_id"]
            for x in rows
        }) == 4,
        "DISTINCT_STREAMS",
    )

    return rows, hashes


def check_rows(repo, s3_metadata, candidate):
    rows, _ = build_rows(
        repo,
        s3_metadata,
    )

    need(
        type(candidate) is list
        and candidate == rows,
        "UNSUPPORTED_SOURCE_OR_SCIENCE_PROMOTION",
    )

    return True


def require_factor_execution(candidate):
    raise S4Error(
        "RECORDED_FACTOR_EXECUTION_REMAINS_BLOCKED"
    )


def junit_count(path):
    cases = list(
        ET.parse(path).getroot().iter(
            "testcase"
        )
    )

    need(
        len(cases) >= 40,
        "INSUFFICIENT_TEST_COVERAGE",
    )

    need(
        all(
            not any(
                child.tag in ("failure", "error", "skipped")
                for child in case
            )
            for case in cases
        ),
        "TEST_FAILURE",
    )

    return len(cases)


def main(a):
    rows, hashes = build_rows(
        a.repo,
        a.s3_metadata,
    )

    matrix = {
        "schema": SCHEMA,
        "parent_commit":
            "79a2abf6de6ff68df23de8bd04b538ce0c95b46b",
        "frozen_sources_sha256": hashes,
        "trajectory_id": "gate_01",
        "split_role": "train",
        "requirement_definitions": REQUIREMENTS,
        "streams": rows,
        "stream_count": 4,
        "gate_count_per_stream": len(GATES),
        "unqualified_gate_instances": 32,
        "physical_time_qualified": False,
        "full_extrinsics_qualified": False,
        "recorded_factor_admission_authorized": False,
    }

    write(a.matrix, matrix)

    tests = junit_count(a.xml)

    report = {
        "schema":
            "TRUST_ROBOT_S4_SOURCE_LINEAGE_REVIEW_V1",
        "parent_commit": matrix["parent_commit"],
        "engine_sha256": sha(__file__),
        "test_sha256": sha(a.test),
        "s3_report_sha256": sha(a.s3_report),
        "s3_validation_sha256": sha(a.s3_validation),
        "matrix_sha256": sha(a.matrix),
        "junit_sha256": sha(a.xml),
        "tests_passed": tests,
        "distinct_source_streams": 4,
        "unqualified_gate_instances": 32,
        "raw_bag_hash_means_calibration": False,
        "camera_intrinsics_verified": False,
        "camera_lidar_full_extrinsic_verified": False,
        "handsfree_lidar_full_extrinsic_verified": False,
        "d435i_relative_rotation_supported_but_incomplete":
            True,
        "real_capture_timestamp_observed": False,
        "cross_modal_time_association_performed": False,
        "calibration_values_created": False,
        "recorded_sensor_factors_generated": 0,
        "reference_scoring_performed": False,
        "health_training_performed": False,
        "new_sensor_acquisitions": 0,
        "scientific_pose_factors": 0,
        "health_labels": 0,
        "git_commit_or_push": False,
        "next":
            "S5_CONTROLLED_RESEARCH_INTEGRATION_READINESS_REVIEW",
    }

    write(a.report, report)

    print(
        f"S4_REQUIREMENT_TESTS={tests}_PASSED"
    )
    print("S4_DISTINCT_SENSOR_STREAMS=4_VERIFIED")
    print("S4_UNQUALIFIED_GATE_INSTANCES=32_CLOSED")
    print("S4_RAW_BAG_INTEGRITY_NOT_CALIBRATION=VERIFIED")
    print("S4_PARTIAL_ROTATION_NOT_FULL_EXTRINSIC=VERIFIED")
    print("S4_RECORDED_FACTOR_EXECUTION=DENIED")
    print("S4_SOURCE_LINEAGE_REVIEW=PASS")


if __name__ == "__main__":
    p = argparse.ArgumentParser()

    for name in (
        "repo",
        "s3_metadata",
        "s3_report",
        "s3_validation",
        "test",
        "xml",
        "matrix",
        "report",
    ):
        p.add_argument(
            "--" + name.replace("_", "-"),
            dest=name,
            required=True,
        )

    main(p.parse_args())
