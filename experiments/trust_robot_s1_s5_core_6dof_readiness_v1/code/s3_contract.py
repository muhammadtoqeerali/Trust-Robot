"""S3 recorded-stream metadata contract.

Uses frozen M2DGR manifest metadata only.

No raw measurement, actual observed timestamp,
cross-modal association, calibration, real pose factor,
or reference trajectory is produced.
"""

import argparse
import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path

from trust_robot.m2dgr_sensor_admission import (
    CAMERA,
    CAMERA_IMU,
    BODY_IMU,
    LIDAR,
    load_frozen_snapshot,
)

SCHEMA = "TRUST_ROBOT_S3_TRAIN_FACTOR_METADATA_ONLY_V1"

STREAMS = (
    CAMERA,
    CAMERA_IMU,
    BODY_IMU,
    LIDAR,
)

FIELDS = (
    "schema",
    "dataset_id",
    "trajectory_id",
    "split_role",
    "stream_id",
    "modality",
    "frame_id",
    "clock_domain",
    "claimed_header_stamp_ns",
    "header_stamp_origin",
    "capture_event_semantics",
    "temporal_association_status",
    "fixed_offset_seconds",
    "association_tolerance_seconds",
    "extrinsic_calibration_verified",
    "body_T_sensor",
    "independent_reference_attested",
    "relative_pose",
    "factor_covariance",
    "qualified_factor_type",
    "real_sensor_factor_execution_authorized",
    "health_supervision_authorized",
    "raw_sensor_payload_opened",
    "disposition",
)


class S3ContractError(ValueError):
    pass


def need(ok, reason):
    if not ok:
        raise S3ContractError(reason)


def canonical(obj):
    return (
        json.dumps(
            obj,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ) + "\n"
    ).encode("utf-8")


def sha(path):
    return hashlib.sha256(
        Path(path).read_bytes()
    ).hexdigest()


def pairs_no_duplicates(pairs):
    out = {}

    for key, value in pairs:
        need(
            key not in out,
            "DUPLICATE_JSON_FIELD",
        )

        out[key] = value

    return out


def reject_constant(value):
    raise S3ContractError(
        "NONFINITE_JSON:" + value
    )


def build_envelope(
    snapshot,
    trajectory_id,
    stream_id,
    claimed_header_stamp_ns,
):
    """Create only an untrusted structural descriptor."""

    need(
        type(claimed_header_stamp_ns) is int
        and 0 <= claimed_header_stamp_ns < 2**63,
        "INVALID_HEADER_CLAIM",
    )

    need(
        type(trajectory_id) is str
        and trajectory_id in snapshot["by_id"],
        "UNKNOWN_TRAJECTORY",
    )

    record = snapshot["by_id"][trajectory_id]

    need(
        record["split"] == "train",
        "HELD_OUT_SOURCE_BLOCKED",
    )

    need(
        stream_id in STREAMS,
        "UNSUPPORTED_STREAM",
    )

    sources = {
        s["stream_id"]: s
        for s in record["streams"]
    }

    clocks = {
        s["stream_id"]: s
        for s in record["synchronization"]
    }

    need(
        stream_id in sources
        and stream_id in clocks,
        "SOURCE_UNAVAILABLE",
    )

    source = sources[stream_id]
    timing = clocks[stream_id]

    need(
        timing["verification_status"] == "unverified"
        and timing["fixed_offset_seconds"] is None
        and timing["tolerance_seconds"] is None
        and source["timestamp_unit"] == "nanoseconds",
        "UNEXPECTED_TIMING_QUALIFICATION",
    )

    need(
        source["clock_domain"].endswith("_unverified"),
        "UNEXPECTED_CLOCK_DOMAIN",
    )

    need(
        source["reference_only"] is False
        and source["estimator_input"] is True,
        "REFERENCE_ORIGIN_EXCLUSION",
    )

    need(
        all(
            value is False
            for value in snapshot["scientific_gates"].values()
        ),
        "SCIENTIFIC_GATE_CHANGED",
    )

    result = {
        "schema": SCHEMA,
        "dataset_id": "M2DGR",
        "trajectory_id": trajectory_id,
        "split_role": "train",
        "stream_id": stream_id,
        "modality": source["modality"],
        "frame_id": source["frame_id"],
        "clock_domain": source["clock_domain"],
        "claimed_header_stamp_ns":
            claimed_header_stamp_ns,
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
        set(result) == set(FIELDS),
        "ENVELOPE_FIELD_CONTRACT",
    )

    return result


def parse_envelope(snapshot, payload):
    """Require canonical bytes and compare to frozen metadata."""

    need(
        type(payload) is bytes
        and 0 < len(payload) < 8192,
        "INVALID_PAYLOAD",
    )

    try:
        obj = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=pairs_no_duplicates,
            parse_constant=reject_constant,
        )

    except (UnicodeError, ValueError, TypeError) as exc:
        raise S3ContractError(
            "INVALID_JSON_ENVELOPE"
        ) from exc

    need(
        type(obj) is dict
        and set(obj) == set(FIELDS),
        "FIELD_SET_MISMATCH",
    )

    need(
        payload == canonical(obj),
        "NONCANONICAL_ENVELOPE",
    )

    expected = build_envelope(
        snapshot,
        obj["trajectory_id"],
        obj["stream_id"],
        obj["claimed_header_stamp_ns"],
    )

    need(
        canonical(obj) == canonical(expected),
        "UNQUALIFIED_METADATA_PROMOTION",
    )

    return expected


def require_real_factor(envelope):
    """No caller-controlled bypass or factor admission."""

    raise S3ContractError(
        "REAL_FACTOR_EXECUTION_BLOCKED:"
        "PHYSICAL_TIME_AND_EXTRINSICS_NOT_VERIFIED"
    )


def test_summary(xml_path):
    cases = list(
        ET.parse(xml_path).getroot().iter(
            "testcase"
        )
    )

    need(
        len(cases) > 0,
        "NO_TEST_CASES",
    )

    need(
        len({
            (
                item.get("classname"),
                item.get("name"),
            )
            for item in cases
        }) == len(cases),
        "DUPLICATE_TEST_IDS",
    )

    need(
        all(
            not any(
                child.tag in (
                    "failure",
                    "error",
                    "skipped",
                )
                for child in item
            )
            for item in cases
        ),
        "TESTS_FAILED_OR_SKIPPED",
    )

    return len(cases)


def output_json(path, obj):
    with Path(path).open(
        "x",
        encoding="utf-8",
    ) as f:
        json.dump(
            obj,
            f,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        f.write("\n")


def main(args):
    root = Path(args.repo)
    snapshot = load_frozen_snapshot(root)

    s2 = json.loads(
        Path(args.s2_report).read_text()
    )

    need(
        s2["regression_test_count"] == 104
        and s2["regression_counts"]["passed"] == 104
        and s2["factor_gate_probe"][
            "negative_control_count"
        ] == 8,
        "S2_VALIDATED_LINEAGE",
    )

    results = []

    for stream in STREAMS:
        packet = build_envelope(
            snapshot,
            "gate_01",
            stream,
            100,
        )

        need(
            parse_envelope(
                snapshot,
                canonical(packet),
            ) == packet,
            "EXAMPLE_ENVELOPE_REJECTED",
        )

        results.append(packet)

    need(
        len(results) == 4,
        "FOUR_DISTINCT_STREAMS",
    )

    need(
        results[1]["stream_id"] == CAMERA_IMU
        and results[2]["stream_id"] == BODY_IMU
        and results[1]["frame_id"]
        != results[2]["frame_id"],
        "IMU_STREAMS_CONFLATED",
    )

    output_json(
        args.metadata,
        {
            "schema":
                "TRUST_ROBOT_S3_FOUR_STREAM_METADATA_EXERCISE_V1",
            "trajectory_id": "gate_01",
            "split_role": "train",
            "illustrative_stamp_only": True,
            "actual_sensor_timestamp_observed": False,
            "envelopes": results,
            "raw_sensor_records_read": False,
            "real_pose_factors_generated": 0,
        },
    )

    tests = test_summary(args.xml)

    report = {
        "schema":
            "TRUST_ROBOT_S3_FACTOR_INPUT_CONTRACT_REPORT_V1",
        "parent_commit":
            "79a2abf6de6ff68df23de8bd04b538ce0c95b46b",
        "engine_sha256": sha(__file__),
        "s2_report_sha256": sha(args.s2_report),
        "s2_validation_sha256": sha(args.s2_validation),
        "test_source_sha256": sha(args.test),
        "test_xml_sha256": sha(args.xml),
        "metadata_sha256": sha(args.metadata),
        "test_cases_passed": tests,
        "supported_stream_count": 4,
        "separate_imu_sources": True,
        "train_only_metadata_boundary": True,
        "header_stamp_source_authenticity_verified": False,
        "physical_capture_timing_verified": False,
        "cross_modal_synchronization_verified": False,
        "physical_extrinsics_verified": False,
        "recorded_camera_pose_factor_authorized": False,
        "recorded_lidar_pose_factor_authorized": False,
        "recorded_imu_factor_authorized": False,
        "real_pose_factor_execution_authorized": False,
        "health_model_training_authorized": False,
        "raw_sensor_records_read": False,
        "independent_reference_used": False,
        "simulator_launch_authorized": False,
        "new_sensor_acquisitions": 0,
        "scientific_pose_factors": 0,
        "health_labels": 0,
        "github_commit_or_push": False,
        "next":
            "S4_FROZEN_FACTOR_SOURCE_LINEAGE_AND_TIMING_REQUIREMENTS",
    }

    output_json(
        args.report,
        report,
    )

    print(
        f"S3_CONTRACT_UNIT_TESTS={tests}_PASSED"
    )
    print("S3_DISTINCT_TRAIN_STREAMS=4_METADATA_ONLY")
    print("S3_CAMERA_AND_HANDSFREE_IMU=SEPARATE")
    print("S3_RECORDED_FACTOR_EXECUTION=DENIED")
    print("S3_TRAIN_FACTOR_INPUT_CONTRACT=PASS")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    for name in (
        "repo",
        "s2_report",
        "s2_validation",
        "test",
        "xml",
        "metadata",
        "report",
    ):
        parser.add_argument(
            "--" + name.replace("_", "-"),
            dest=name,
            required=True,
        )

    main(parser.parse_args())
