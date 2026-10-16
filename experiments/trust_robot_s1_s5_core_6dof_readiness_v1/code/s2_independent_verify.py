"""S2 independent JUnit, source and scientific gate verification."""

import argparse
import ast
import hashlib
import json
import xml.etree.ElementTree as ET

from pathlib import Path


def need(ok, reason):
    if not ok:
        raise AssertionError(
            "S2_VERIFY:" + reason
        )


def sha(path):
    return hashlib.sha256(
        Path(path).read_bytes()
    ).hexdigest()


def load(path):
    return json.loads(
        Path(path).read_text()
    )


def main(args):
    root = Path(args.repo)

    report = load(args.report)
    s1 = load(args.s1_report)

    need(
        report["schema"]
        == "TRUST_ROBOT_S2_ESTIMATOR_REGRESSION_AND_FACTOR_GATE_V1",
        "REPORT_SCHEMA",
    )

    for key, path in (
        ("audit_source_sha256", args.engine),
        ("s1_report_sha256", args.s1_report),
        ("s1_validation_sha256", args.s1_validation),
        ("pytest_xml_sha256", args.xml),
    ):
        need(
            report[key] == sha(path),
            "HASH:" + key,
        )

    need(
        s1["m2dgr_split_counts"] == {
            "train": 22,
            "validation_calibration": 7,
            "confirmation_test": 7,
        },
        "SPLIT",
    )

    suites = report["regression_suites"]

    need(
        len(suites)
        == report["selected_suite_count"]
        == 9
        and len({
            item["name"]
            for item in suites
        }) == 9,
        "SUITE_LIST",
    )

    for item in suites:
        path = (
            root
            / "tests/trust_robot"
            / item["name"]
        )

        need(
            path.is_file()
            and not path.is_symlink()
            and sha(path) == item["sha256"],
            "SOURCE_HASH",
        )

        ast.parse(
            path.read_text()
        )

    cases = list(
        ET.parse(args.xml).getroot().iter(
            "testcase"
        )
    )

    need(
        len(cases) > 0
        and len(cases)
        == report["regression_test_count"],
        "TEST_COUNT",
    )

    need(
        not any(
            child.tag in (
                "failure",
                "error",
                "skipped",
            )
            for case in cases
            for child in case
        ),
        "FAILED_OR_SKIPPED",
    )

    need(
        report["regression_counts"] == {
            "passed": len(cases),
            "failed": 0,
            "errored": 0,
            "skipped": 0,
        },
        "COUNTS",
    )

    gate = report["factor_gate_probe"]

    need(
        gate["negative_control_count"]
        == len(gate["negative_controls_denied"])
        == 8
        and len(set(
            gate["negative_controls_denied"]
        )) == 8,
        "NEGATIVE_CONTROLS",
    )

    need(
        len(gate["metadata_only_streams"]) == 3
        and all(
            item["status"]
            == "RECORDED_PROVENANCE_ONLY"
            and item[
                "factor_execution_authorized"
            ] is False
            for item in gate[
                "metadata_only_streams"
            ]
        ),
        "METADATA_ONLY",
    )

    for key in (
        "real_factor_execution_authorized",
        "sensor_synchronization_verified",
        "physical_extrinsics_verified",
    ):
        need(
            gate[key] is False,
            "GATE_DENIED",
        )

    dataset = load(
        root /
        "manifests/m2dgr_trajectory_manifest_v1_split_freeze_v1.json"
    )

    protocol = load(
        root /
        "configs/trust_robot/m2dgr_trajectory_association_evaluation_protocol_candidate_v2.json"
    )

    need(
        len(dataset["records"]) == 36
        and all(
            item["verification_status"]
            == "unverified"
            for trajectory in dataset["records"]
            for item in trajectory[
                "synchronization"
            ]
        ),
        "TIMING_GATE",
    )

    need(
        protocol["authorization"][
            "estimator_scoring_authorized"
        ] is False
        and protocol["authorization"][
            "evaluation_ready"
        ] is False,
        "SCORING_GATE",
    )

    for key in (
        "manufactured_truth_is_physical_reference",
        "recorded_camera_relative_pose_qualified",
        "recorded_lidar_imu_fusion_qualified",
        "camera_lidar_independent_same_edge_fusion_qualified",
        "trusted_cross_modal_timing",
        "empirical_covariance_calibration",
        "m2dgr_scoring_authorized",
        "health_training_authorized",
        "live_simulator_launch_authorized",
        "git_commit_or_push",
    ):
        need(
            report[key] is False,
            "FALSE_CLAIM:" + key,
        )

    for key in (
        "new_sensor_measurements",
        "scientific_pose_factors_authorized",
        "health_labels_generated",
    ):
        need(
            type(report[key]) is int
            and report[key] == 0,
            "NONZERO:" + key,
        )

    validation = {
        "schema":
            "TRUST_ROBOT_S2_INDEPENDENT_VALIDATION_V1",
        "engine_sha256": sha(args.engine),
        "verifier_sha256": sha(__file__),
        "report_sha256": sha(args.report),
        "junit_xml_sha256": sha(args.xml),
        "verified_selected_suites": 9,
        "verified_test_count": len(cases),
        "verified_failed_tests": 0,
        "verified_skipped_tests": 0,
        "verified_recorded_factor_denials": 8,
        "real_sensor_factors_authorized": 0,
        "m2dgr_scoring_authorized": False,
        "health_training_authorized": False,
        "live_simulator_launch_authorized": False,
        "new_sensor_measurements": 0,
        "health_labels_generated": 0,
    }

    with open(
        args.validation,
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
        f"S2_INDEPENDENT_REGRESSION_TESTS="
        f"{len(cases)}_VERIFIED"
    )
    print("S2_INDEPENDENT_FACTOR_DENIALS=8_VERIFIED")
    print("S2_INDEPENDENT_VALIDATION=PASS")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    for field in (
        "repo",
        "engine",
        "s1_report",
        "s1_validation",
        "xml",
        "report",
        "validation",
    ):
        parser.add_argument(
            "--" + field.replace("_", "-"),
            dest=field,
            required=True,
        )

    main(parser.parse_args())
