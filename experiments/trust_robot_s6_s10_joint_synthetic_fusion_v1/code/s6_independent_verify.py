"""S6 independent evidence, JUnit and factor-ledger verifier."""

import argparse
import hashlib
import json
import xml.etree.ElementTree as ET

from pathlib import Path


def need(ok, reason):
    if not ok:
        raise AssertionError(
            "S6_INDEPENDENT_FAIL:" + reason
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
    report = load(args.report)
    s5 = load(args.s5_matrix)

    need(
        report["schema"]
        == "TRUST_ROBOT_S6_JOINT_SYNTHETIC_FUSION_V1",
        "SCHEMA",
    )

    need(
        report["source_sha256"] == sha(args.engine)
        and report["junit_sha256"] == sha(args.xml)
        and report["s5_matrix_sha256"]
        == sha(args.s5_matrix),
        "SOURCE_CHAIN",
    )

    need(
        s5["next_implementation"]["work_id"]
        == "S6_CPU_ONLY_INDEPENDENT_CAMERA_LIDAR_SAME_EDGE_FUSION",
        "S5_DECISION",
    )

    cases = list(
        ET.parse(args.xml).getroot().iter(
            "testcase"
        )
    )

    need(
        len(cases) >= 12
        and len(cases) == report["test_cases_passed"]
        and not any(
            child.tag in ("failure", "error", "skipped")
            for case in cases
            for child in case
        ),
        "UNIT_TESTS",
    )

    scenarios = report["scenarios"]

    need(
        len(scenarios) == report["scenario_count"] == 4,
        "SCENARIO_COUNT",
    )

    for row in scenarios:
        audit = row["factor_audit"]
        enabled = row["camera_enabled"]

        need(
            audit["accepted_window_count"] == 4
            and audit["schur_elimination_count"] == 3
            and audit["camera_factor_count"]
            == (2 if enabled else 0)
            and audit["unaccounted_factor_count"] == 0
            and audit["factor_reuse_after_marginalization"]
            is False,
            "SOLVER_CHRONOLOGY",
        )

        ledger = audit["factor_ledger"]

        names = [
            f["measurement_id"]
            for f in ledger
        ]

        need(
            len(names) == len(set(names))
            and len(names)
            == audit["total_pose_factor_count"],
            "UNIQUE_MEASUREMENT_IDS",
        )

        consumed = set(
            audit["consumed_pose_ids"]
        )

        remaining = set(
            audit["remaining_pose_ids"]
        )

        need(
            consumed.isdisjoint(remaining)
            and consumed | remaining == set(names),
            "FACTOR_PRIOR_OWNERSHIP",
        )

        owners = [
            (
                f["modality"],
                tuple(f["edge"]),
            )
            for f in ledger
        ]

        need(
            len(owners) == len(set(owners)),
            "DUPLICATE_MODALITY_EDGE",
        )

        both = {
            tuple(f["edge"])
            for f in ledger
            if f["modality"] == "camera"
        } & {
            tuple(f["edge"])
            for f in ledger
            if f["modality"] == "lidar"
        }

        need(
            len(both)
            == audit["same_edge_camera_lidar_count"]
            and len(both) == (
                2 if enabled and row["condition"] == "clean"
                else 1 if enabled else 0
            ),
            "SAME_EDGE_NOT_RETAINED",
        )

        need(
            all(
                f["origin"] == "ANALYTIC_FIXTURE"
                and len(f["covariance_diagonal"]) == 6
                and all(
                    isinstance(x, (int, float))
                    and x > 0
                    for x in f["covariance_diagonal"]
                )
                for f in ledger
            ),
            "FACTOR_PROVENANCE_OR_COVARIANCE",
        )

        need(
            row["reference_passed_to_solver"] is False
            and row["scientific_pose_accuracy_claim"] is False,
            "REFERENCE_LEAK_OR_SCORE",
        )

    for key in (
        "assumed_cross_modal_noise_independence_verified",
        "camera_motion_from_real_images",
        "physical_sensor_time_verified",
        "real_sensor_extrinsics_verified",
        "empirical_noise_covariance_calibrated",
        "real_sensor_factor_execution_authorized",
        "independent_real_6dof_truth_scored",
        "health_model_trained",
        "raw_sensor_recordings_read",
        "git_commit_or_push",
    ):
        need(
            report[key] is False,
            "UNSUPPORTED_SCIENCE_CLAIM:" + key,
        )

    for key in (
        "new_sensor_acquisitions",
        "scientific_pose_factors",
        "health_labels",
    ):
        need(
            type(report[key]) is int
            and report[key] == 0,
            "NONZERO_SCIENTIFIC_COUNT",
        )

    result = {
        "schema":
            "TRUST_ROBOT_S6_INDEPENDENT_VALIDATION_V1",
        "engine_sha256": sha(args.engine),
        "test_sha256": sha(args.test),
        "verifier_sha256": sha(__file__),
        "junit_sha256": sha(args.xml),
        "report_sha256": sha(args.report),
        "unit_tests_verified": len(cases),
        "nonlinear_joint_scenarios_verified": 4,
        "all_factor_ownership_verified": True,
        "same_edge_independent_factor_slots_verified": True,
        "source_specific_assumed_covariances_verified": True,
        "empirical_independence_established": False,
        "real_sensor_factor_execution_authorized": False,
        "new_sensor_acquisitions": 0,
        "scientific_pose_factors": 0,
        "health_labels": 0,
    }

    with Path(args.validation).open(
        "x",
        encoding="utf-8",
    ) as f:
        json.dump(
            result,
            f,
            indent=2,
            sort_keys=True,
        )
        f.write("\n")

    print(
        "S6_INDEPENDENT_UNIT_TESTS="
        f"{len(cases)}_VERIFIED"
    )
    print("S6_INDEPENDENT_NONLINEAR_SCENARIOS=4_VERIFIED")
    print("S6_INDEPENDENT_SCHUR_FACTOR_OWNERSHIP=VERIFIED")
    print("S6_INDEPENDENT_SAME_EDGE_FUSION=VERIFIED")
    print("S6_INDEPENDENT_VALIDATION=PASS")


if __name__ == "__main__":
    p = argparse.ArgumentParser()

    for name in (
        "engine",
        "test",
        "xml",
        "s5_matrix",
        "report",
        "validation",
    ):
        p.add_argument(
            "--" + name.replace("_", "-"),
            dest=name,
            required=True,
        )

    main(p.parse_args())
