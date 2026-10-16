"""S2 synthetic regression and recorded-source refusal audit."""

import argparse
import ast
import hashlib
import json
import xml.etree.ElementTree as ET

from pathlib import Path

from trust_robot.clean_backbone import PoseSE3
from trust_robot.m2dgr_sensor_admission import (
    CAMERA,
    BODY_IMU,
    LIDAR,
    load_frozen_snapshot,
)
from trust_robot.multimodal_factor_interface import (
    ANALYTIC_FRAME,
    CAMERA_SOURCE,
    MultimodalFactorError,
    SyntheticPoseFactor,
    describe_recorded_claim,
    require_recorded_factor_execution,
)

BASE = "79a2abf6de6ff68df23de8bd04b538ce0c95b46b"

SUITES = (
    "test_analytic_imu_preintegration.py",
    "test_analytic_preintegrated_fusion.py",
    "test_analytic_schur_marginalization.py",
    "test_analytic_marginalized_fusion.py",
    "test_analytic_factor_support.py",
    "test_analytic_marginalization_consistency.py",
    "test_analytic_three_modality_bridge.py",
    "test_multimodal_factor_interface.py",
    "test_m2dgr_sensor_admission.py",
)


def need(value, reason):
    if not value:
        raise AssertionError("S2_AUDIT:" + reason)


def sha(path):
    return hashlib.sha256(
        Path(path).read_bytes()
    ).hexdigest()


def read(path):
    return json.loads(
        Path(path).read_text()
    )


def junit(path):
    cases = list(
        ET.parse(path).getroot().iter("testcase")
    )

    need(
        len(cases) > 0,
        "NO_REGRESSION_TESTS",
    )

    names = {
        (
            case.get("classname"),
            case.get("name"),
        )
        for case in cases
    }

    need(
        len(names) == len(cases),
        "DUPLICATE_CASE_IDENTITIES",
    )

    counts = {
        "passed": 0,
        "failed": 0,
        "errored": 0,
        "skipped": 0,
    }

    for case in cases:
        if case.find("failure") is not None:
            counts["failed"] += 1

        elif case.find("error") is not None:
            counts["errored"] += 1

        elif case.find("skipped") is not None:
            counts["skipped"] += 1

        else:
            counts["passed"] += 1

    need(
        counts["passed"] == len(cases),
        "REGRESSION_NOT_ALL_PASS",
    )

    return len(cases), counts


def gates(repo):
    snapshot = load_frozen_snapshot(repo)

    need(
        len(snapshot["by_id"]) == 36
        and all(
            value is False
            for value in snapshot[
                "scientific_gates"
            ].values()
        ),
        "SOURCE_GATES_CHANGED",
    )

    descriptions = []

    for stream in (CAMERA, BODY_IMU, LIDAR):
        result = describe_recorded_claim(
            snapshot,
            "gate_01",
            stream,
            100,
        )

        need(
            result["status"]
            == "RECORDED_PROVENANCE_ONLY",
            "SOURCE_PROMOTED",
        )

        for key in (
            "factor_execution_authorized",
            "relative_pose_available",
            "header_timestamp_is_sync_proof",
            "physical_extrinsic_verified",
        ):
            need(
                result[key] is False,
                "SOURCE_CLAIM_" + key,
            )

        descriptions.append({
            "stream": stream,
            "status": result["status"],
            "factor_execution_authorized": False,
        })

    probes = (
        (
            "heldout",
            lambda: describe_recorded_claim(
                snapshot,
                "room_01",
                CAMERA,
                100,
            ),
        ),
        (
            "missing_camera",
            lambda: describe_recorded_claim(
                snapshot,
                "street_09",
                CAMERA,
                100,
            ),
        ),
        (
            "boolean_header",
            lambda: describe_recorded_claim(
                snapshot,
                "gate_01",
                CAMERA,
                True,
            ),
        ),
        (
            "negative_header",
            lambda: describe_recorded_claim(
                snapshot,
                "gate_01",
                CAMERA,
                -1,
            ),
        ),
        (
            "unsupported_stream",
            lambda: describe_recorded_claim(
                snapshot,
                "gate_01",
                "/wrong/sensor",
                100,
            ),
        ),
        (
            "recorded_factor",
            lambda: require_recorded_factor_execution(
                snapshot,
                "gate_01",
            ),
        ),
        (
            "forged_authorization",
            lambda: describe_recorded_claim(
                {
                    **snapshot,
                    "scientific_gates": {
                        **snapshot[
                            "scientific_gates"
                        ],
                        "real_sensor_factor_execution_authorized":
                            True,
                    },
                },
                "gate_01",
                CAMERA,
                100,
            ),
        ),
        (
            "recorded_in_synthetic_slot",
            lambda: SyntheticPoseFactor(
                modality="camera",
                edge=(0, 1),
                measurement_id="forgery",
                source_id=CAMERA_SOURCE,
                frame_id=ANALYTIC_FRAME,
                measurement=PoseSE3.identity(),
                origin="M2DGR",
            ),
        ),
    )

    denied = []

    for name, function in probes:
        try:
            function()

        except MultimodalFactorError:
            denied.append(name)

        else:
            raise AssertionError(
                "UNAUTHORIZED_FACTOR_ACCEPTED:"
                + name
            )

    need(
        len(denied) == 8,
        "NEGATIVE_COUNT",
    )

    return {
        "metadata_only_streams": descriptions,
        "negative_controls_denied": denied,
        "negative_control_count": 8,
        "real_factor_execution_authorized": False,
        "sensor_synchronization_verified": False,
        "physical_extrinsics_verified": False,
    }


def main(args):
    s1 = read(args.s1_report)
    validation = read(args.s1_validation)

    need(
        s1["parent_commit"] == BASE
        and s1["analytic_module_count"] == 16
        and s1["m2dgr_sync_qualified"] == 0,
        "S1_READINESS",
    )

    need(
        validation[
            "verified_analytic_source_and_test_pairs"
        ] == 16
        and validation[
            "real_sensor_pose_factors_authorized"
        ] == 0,
        "S1_VALIDATION",
    )

    inventory = []

    for name in SUITES:
        path = (
            Path(args.repo)
            / "tests/trust_robot"
            / name
        )

        need(
            path.is_file()
            and not path.is_symlink(),
            "MISSING_TEST:" + name,
        )

        ast.parse(
            path.read_text()
        )

        inventory.append({
            "name": name,
            "sha256": sha(path),
        })

    count, results = junit(args.xml)
    gate_results = gates(Path(args.repo))

    report = {
        "schema":
            "TRUST_ROBOT_S2_ESTIMATOR_REGRESSION_AND_FACTOR_GATE_V1",
        "parent_commit": BASE,
        "audit_source_sha256": sha(__file__),
        "s1_report_sha256": sha(args.s1_report),
        "s1_validation_sha256": sha(args.s1_validation),
        "pytest_xml_sha256": sha(args.xml),
        "regression_suites": inventory,
        "selected_suite_count": 9,
        "regression_test_count": count,
        "regression_counts": results,
        "factor_gate_probe": gate_results,
        "scientific_interpretation":
            "SYNTHETIC_ESTIMATOR_REGRESSION_ONLY",
        "manufactured_truth_is_physical_reference": False,
        "recorded_camera_relative_pose_qualified": False,
        "recorded_lidar_imu_fusion_qualified": False,
        "camera_lidar_independent_same_edge_fusion_qualified": False,
        "trusted_cross_modal_timing": False,
        "empirical_covariance_calibration": False,
        "m2dgr_scoring_authorized": False,
        "health_training_authorized": False,
        "live_simulator_launch_authorized": False,
        "new_sensor_measurements": 0,
        "scientific_pose_factors_authorized": 0,
        "health_labels_generated": 0,
        "git_commit_or_push": False,
        "numerical_execution_environment":
            "PYTHONNOUSERSITE=1; system NumPy/SciPy; CPU only",
        "next_scientific_task":
            "DEFINE_TRAIN_ONLY_RECORDED_FACTOR_INPUT_BOUNDARY_WITHOUT_ADMISSION",
    }

    with open(
        args.report,
        "x",
        encoding="utf-8",
    ) as stream:
        json.dump(
            report,
            stream,
            sort_keys=True,
            indent=2,
        )
        stream.write("\n")

    print(
        f"S2_ESTIMATOR_REGRESSION_TESTS="
        f"{count}_PASSED"
    )
    print("S2_SELECTED_REGRESSION_SUITES=9_PASS")
    print("S2_METADATA_ONLY_RECORDED_STREAMS=3_VERIFIED")
    print("S2_RECORDED_FACTOR_NEGATIVE_CONTROLS=8_DENIED")
    print("S2_M2DGR_REAL_FACTOR_ADMISSION=DENIED")
    print("S2_ESTIMATOR_AND_FACTOR_GATE_AUDIT=PASS")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    for field in (
        "repo",
        "s1_report",
        "s1_validation",
        "xml",
        "report",
    ):
        parser.add_argument(
            "--" + field.replace("_", "-"),
            dest=field,
            required=True,
        )

    main(parser.parse_args())
