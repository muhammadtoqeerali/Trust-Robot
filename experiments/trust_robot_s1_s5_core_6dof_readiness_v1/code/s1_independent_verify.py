"""Independent read-only review of S1 code and evidence inventory."""

import argparse
import ast
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(
        Path(path).read_bytes()
    ).hexdigest()


def check(ok, reason):
    if not ok:
        raise AssertionError(reason)


def main():
    p = argparse.ArgumentParser()

    for name in (
        "repo",
        "engine",
        "report",
        "validation",
    ):
        p.add_argument(
            "--" + name,
            required=True,
        )

    a = p.parse_args()

    root = Path(a.repo)

    r = json.loads(
        Path(a.report).read_text()
    )

    check(
        r["schema"]
        == "TRUST_ROBOT_S1_CORE_6DOF_READINESS_AUDIT_V1",
        "SCHEMA",
    )

    check(
        r["audit_source_sha256"] == sha(a.engine),
        "AUDIT_SOURCE",
    )

    check(
        r["m2dgr_trajectory_count"] == 36
        and r["m2dgr_split_counts"] == {
            "train": 22,
            "validation_calibration": 7,
            "confirmation_test": 7,
        },
        "FROZEN_SPLITS",
    )

    manifest = json.loads(
        (
            root /
            "manifests/m2dgr_trajectory_manifest_v1_split_freeze_v1.json"
        ).read_text()
    )

    check(
        len(manifest["records"]) == 36,
        "MANIFEST_TRAJECTORIES",
    )

    actual_sync = [
        x
        for record in manifest["records"]
        for x in record["synchronization"]
    ]

    check(
        len(actual_sync) == 140
        and all(
            x["verification_status"] == "unverified"
            for x in actual_sync
        ),
        "INDEPENDENT_SYNC",
    )

    protocol = json.loads(
        (
            root /
            "configs/trust_robot/m2dgr_trajectory_association_evaluation_protocol_candidate_v2.json"
        ).read_text()
    )

    health = json.loads(
        (
            root /
            "manifests/trust_robot_se4_health_model_training_blocked_frontier_freeze_v1.json"
        ).read_text()
    )

    check(
        protocol["authorization"][
            "estimator_scoring_authorized"
        ] is False
        and protocol["authorization"]["evaluation_ready"]
        is False
        and protocol["authorization"][
            "confirmation_test_partition_closed"
        ] is True,
        "INDEPENDENT_PROTOCOL",
    )

    check(
        health["stage"]["SE4_complete"] is False
        and health["supervision_state"][
            "real_health_label_count"
        ] == 0
        and health["model_state"][
            "classifier_training_authorized"
        ] is False,
        "INDEPENDENT_HEALTH",
    )

    for relative, digest in r["frozen_source_sha256"].items():
        f = root / relative

        check(
            f.is_file()
            and not f.is_symlink()
            and sha(f) == digest,
            "SOURCE_HASH:" + relative,
        )

    inv = r["analytic_implementation_inventory"]

    check(
        len(inv) == 16
        and len({
            x["module"]
            for x in inv
        }) == 16,
        "MODULE_LIST",
    )

    for item in inv:
        for key in ("source", "test"):
            f = root / item[key]

            ast.parse(
                f.read_text(encoding="utf-8")
            )

            check(
                sha(f) == item[key + "_sha256"],
                "MODULE_HASH",
            )

        check(
            item["unit_test_executed_in_s1"] is False
            and item["real_sensor_qualified_in_s1"] is False,
            "MISSTATED_TEST_COMPLETION",
        )

    for flag in (
        "raw_bag_read",
        "confirmation_sensor_data_read",
        "estimator_executed",
        "scientific_metrics_computed",
        "live_simulator_launch_authorized",
        "git_modified",
    ):
        check(
            r[flag] is False,
            "FALSE_AUTHORIZATION:" + flag,
        )

    check(
        r["real_sensor_pose_factors_authorized"] == 0
        and r["health_labels_generated"] == 0,
        "SCIENCE_GATE",
    )

    validation = {
        "schema":
            "TRUST_ROBOT_S1_INDEPENDENT_VALIDATION_V1",
        "audit_source_sha256": sha(a.engine),
        "verifier_source_sha256": sha(__file__),
        "report_sha256": sha(a.report),
        "independently_verified_trajectories": 36,
        "independently_verified_sync_entries": 140,
        "verified_analytic_source_and_test_pairs": 16,
        "real_sensor_scoring_authorized": False,
        "empirical_health_training_authorized": False,
        "real_sensor_pose_factors_authorized": 0,
        "new_sensor_acquisitions": 0,
        "scientific_metrics_computed": 0,
        "live_simulator_launch_authorized": False,
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

    print("S1_INDEPENDENT_M2DGR_GATES=VERIFIED")
    print("S1_INDEPENDENT_ESTIMATOR_INVENTORY=16_VERIFIED")
    print("S1_INDEPENDENT_VALIDATION=PASS")


if __name__ == "__main__":
    main()
