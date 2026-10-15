"""L3: fail-closed interface for unqualified synthetic LiDAR registration."""

import copy
import hashlib
import json
import math
import sys
from pathlib import Path

STEPS = [51, 61, 71, 81, 91, 101]
CONDITIONS = ("clean", "frame_3_half_sampled")
PAIRS = list(zip(STEPS[:-1], STEPS[1:]))

L1_SHA = "a120e376d7055a19fe5948f0df9b15b8b824399e967583e745da3258c55c553b"
L2_SHA = "4cad184b44bd9d99ebb762a7dcbe04e0c18bd42265568057aaf7f7a1598922c6"
V16_SHA = "ab08f15221e2f977321afc5e4983feaf9d815ca91b97f2034b36317638e78d82"

def require(ok, message):
    if not ok:
        raise ValueError(message)

def digest(path):
    require(
        path.is_file() and not path.is_symlink(),
        "Missing or unsafe source file",
    )
    return hashlib.sha256(path.read_bytes()).hexdigest()

def canon(obj):
    return (
        json.dumps(
            obj, sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ) + "\n"
    ).encode()

def finite_nonnegative(value):
    return (
        type(value) in (int, float)
        and math.isfinite(value)
        and value >= 0
    )

def validate(l1, l2, v16):
    require(
        v16["runtime_pass"] is True
        and v16["offline_sensor_file_validation_pass"] is True,
        "V16 recording not qualified",
    )
    require(
        v16["selected_steps"] == STEPS
        and v16["validation_issues"] == [],
        "V16 sequence changed",
    )
    require(
        v16["cross_sensor_sync_verified"] is False
        and v16["independent_ground_truth_verified"] is False,
        "Unexpected V16 scientific flags",
    )
    require(
        l1["source_evidence_sha256"] == V16_SHA
        and l2["source_v16_evidence_sha256"] == V16_SHA,
        "Source evidence chain mismatch",
    )
    require(
        l2["source_l1_report_sha256"] == L1_SHA,
        "L1-to-L2 provenance mismatch",
    )
    require(
        l1["offline_implementation_pass"] is True
        and l1["repeat_derivation_identical"] is True,
        "L1 not verified",
    )
    require(
        l1["source_steps"] == STEPS
        and l1["source_point_counts"] == [16,16,16,16,16,4],
        "L1 scans mismatch",
    )
    require(
        l1["pair_attempts"] == 10
        and l1["frozen_diagnostics_available"] == 8
        and l1["sparse_pairs_rejected"] == 2,
        "L1 counts mismatch",
    )
    require(
        l1["health_labels_generated"] is False
        and l1["model_training_authorized"] is False,
        "Unexpected L1 authorization",
    )
    require(
        l2["engineering_audit_complete"] is True
        and l2["deterministic_two_derivations_identical"] is True,
        "L2 unverified",
    )

    for key, value in (
        ("pose_factors_accepted", 0),
        ("health_supervision_labels_emitted", 0),
        ("model_training_authorized", False),
        ("cross_sensor_sync_verified", False),
        ("independent_ground_truth_verified", False),
        ("localization_ate_rpe_computed", False),
    ):
        require(
            l2[key] == value and type(l2[key]) is type(value),
            "Unexpected L2 authorization: " + key,
        )

    require(
        len(l2["geometry_summary"]) == 6,
        "Invalid geometry count",
    )

    for step, geometry in zip(
        STEPS, l2["geometry_summary"]
    ):
        require(
            geometry["step"] == step
            and geometry["six_dof_observability_verified"] is False,
            "Geometry evidence mismatch",
        )
        for key in (
            "spatial_smallest_to_largest_ratio",
            "rotational_information_min_to_max_ratio",
        ):
            ratio = geometry[key]
            require(
                finite_nonnegative(ratio) and ratio <= 1,
                "Invalid geometry ratio",
            )

    records = l1["paired_registration"]
    require(len(records) == 10, "Unexpected pair count")

    expected = [
        (condition, previous, current)
        for condition in CONDITIONS
        for previous, current in PAIRS
    ]

    observed = [
        (
            row["condition"],
            row["previous_step"],
            row["current_step"],
        )
        for row in records
    ]

    require(
        observed == expected,
        "Pair order/lineage mismatch",
    )

    l2rows = l2["clean_pairs_analyzed"]

    require(
        len(l2rows) == 4,
        "L2 must characterize four available clean pairs",
    )

    for i, (row, steps) in enumerate(
        zip(l2rows, PAIRS[:4])
    ):
        require(
            (row["previous_step"], row["current_step"])
            == steps,
            "L2 pair order mismatch",
        )
        require(
            row["frozen_frontend_baseline_reproduced"] is True
            and row["rigid_transform_scientifically_qualified"] is False
            and row["pose_factor_authorized"] is False,
            "L2 declared qualified pose",
        )
        require(
            len(row["sensitivity_challenges"]) == 2,
            "L2 challenge count mismatch",
        )

        for challenge, amplitude in zip(
            row["sensitivity_challenges"],
            (0.0005, 0.002),
        ):
            require(
                challenge["max_per_coordinate_perturbation_m"]
                    == amplitude
                and challenge["pose_factor_authorized"] is False
                and challenge["noise_distribution_calibrated"] is False,
                "L2 perturbation contract changed",
            )
            require(
                challenge["outcome_status"] in (
                    "DIAGNOSTIC_AVAILABLE",
                    "REGISTRATION_UNAVAILABLE",
                ),
                "Bad L2 challenge status",
            )

            if challenge["candidate_change"] is not None:
                require(
                    all(
                        finite_nonnegative(
                            challenge["candidate_change"][key]
                        )
                        for key in (
                            "translation_change_m",
                            "rotation_change_deg",
                        )
                    ),
                    "Nonfinite sensitivity",
                )

        clean = records[i]["registration"]

        require(
            clean["status"] == "FROZEN_DIAGNOSTICS_AVAILABLE",
            "L1 clean pair missing",
        )
        require(
            math.isclose(
                float(clean["features"][
                    "final_nearest_neighbor_rmse_m"
                ]),
                row["baseline_icp_rmse_m"],
                rel_tol=1e-10,
                abs_tol=1e-12,
            ),
            "L1/L2 residual mismatch",
        )

    for index, row in enumerate(records):
        registration = row["registration"]
        condition_index = 0 if index < 5 else 1
        j = index % 5

        point_counts = [16,16,16,16,16,4]
        if condition_index:
            point_counts[2] = 8

        require(
            row["previous_points"] == point_counts[j]
            and row["current_points"] == point_counts[j+1],
            "Input point counts changed",
        )

        for key in (
            "camera_lidar_synchronized",
            "independent_ground_truth_used",
            "health_label_generated",
            "localization_accuracy_scored",
        ):
            require(
                row[key] is False,
                "Forbidden claim in L1: " + key,
            )

        require(
            row["source_frame"] == "GMO_SENSOR_CARTESIAN",
            "Unexpected frame",
        )

        require(
            registration["relative_pose_scientifically_qualified"]
                is False,
            "Upstream pose authorization rejected",
        )

        if j == 4:
            require(
                registration["status"]
                    == "SPARSE_ENDPOINT_UNAVAILABLE"
                and registration["relative_pose_candidate"] is None
                and registration["features"] is None,
                "Sparse scan was falsely admitted",
            )
        else:
            require(
                registration["status"]
                    == "FROZEN_DIAGNOSTICS_AVAILABLE"
                and isinstance(
                    registration["features"], dict
                )
                and registration[
                    "relative_pose_candidate"
                ] is not None,
                "Expected diagnostic missing",
            )
            require(
                finite_nonnegative(
                    registration["features"][
                        "final_nearest_neighbor_rmse_m"
                    ]
                ),
                "Bad ICP residual",
            )

    require(
        l2["sparse_pair"]["step_pair"] == [91,101]
        and l2["sparse_pair"]["pose_factor_authorized"] is False,
        "Sparse pair in L2 changed",
    )

    return records

def decisions(l1, l2, v16):
    records = validate(l1, l2, v16)
    rows = []

    for row in records:
        registration = row["registration"]

        sparse = (
            registration["status"]
            == "SPARSE_ENDPOINT_UNAVAILABLE"
        )

        reasons = (
            ["SPARSE_ENDPOINT_UNAVAILABLE"]
            if sparse else [
                "GEOMETRIC_POSE_OBSERVABILITY_UNVERIFIED",
                "REGISTRATION_UNCERTAINTY_NOT_CALIBRATED",
                "PHYSICAL_MEASUREMENT_TIME_UNVERIFIED",
                "DIAGNOSTIC_FIT_NOT_POSE_QUALIFICATION",
            ]
        )

        if row["condition"] != "clean" and not sparse:
            reasons.append(
                "PERTURBED_CONDITION_NOT_L2_QUALIFIED"
            )

        if row["condition"] == "clean" and not sparse:
            reasons.append(
                "L2_PERTURBATION_SENSITIVITY_REQUIRES_QUALIFICATION"
            )

        rows.append({
            "condition": row["condition"],
            "previous_step": row["previous_step"],
            "current_step": row["current_step"],
            "input_registration_status":
                registration["status"],
            "diagnostic_candidate_present":
                registration["relative_pose_candidate"] is not None,
            "admission": "DENIED",
            "reason_codes": reasons,
            "estimator_pose_increment": None,
            "factor_information_matrix": None,
            "physical_timestamp_ns": None,
            "health_label": None,
            "physical_or_reference_accuracy_claim": False,
        })

    return rows

def selftests(l1, l2, v16):
    scenarios = [
        (
            "forge_registration_pose",
            lambda a,b,c:
                a["paired_registration"][0]["registration"].__setitem__(
                    "relative_pose_scientifically_qualified", True
                ),
        ),
        (
            "forge_synchronization",
            lambda a,b,c:
                a["paired_registration"][0].__setitem__(
                    "camera_lidar_synchronized", True
                ),
        ),
        (
            "forge_factor_acceptance",
            lambda a,b,c:
                b.__setitem__("pose_factors_accepted", 1),
        ),
        (
            "forge_l2_geometry",
            lambda a,b,c:
                b["geometry_summary"][0].__setitem__(
                    "six_dof_observability_verified", True
                ),
        ),
        (
            "forge_sparse_pose",
            lambda a,b,c:
                a["paired_registration"][4]["registration"].__setitem__(
                    "relative_pose_candidate", {"fake": "pose"}
                ),
        ),
        (
            "forge_pair_order",
            lambda a,b,c:
                a["paired_registration"][0].__setitem__(
                    "current_step", 999
                ),
        ),
        (
            "forge_source_provenance",
            lambda a,b,c:
                b.__setitem__(
                    "source_l1_report_sha256", "0"*64
                ),
        ),
        (
            "forge_noise_calibration",
            lambda a,b,c:
                b["clean_pairs_analyzed"][0][
                    "sensitivity_challenges"
                ][0].__setitem__(
                    "noise_distribution_calibrated", True
                ),
        ),
    ]

    for name, mutate in scenarios:
        a, b, c = copy.deepcopy((l1, l2, v16))
        mutate(a, b, c)

        try:
            decisions(a, b, c)
        except (ValueError, KeyError, TypeError):
            print("FAIL_CLOSED_TEST=PASS", name)
        else:
            raise AssertionError(
                "Tampered evidence accepted: " + name
            )

    return len(scenarios)

def main():
    require(
        len(sys.argv) == 5,
        "usage: L3.py L1 L2 V16 OUTPUT_DIR",
    )

    l1p, l2p, v16p, out = map(
        Path, sys.argv[1:]
    )

    for path, expected in (
        (l1p, L1_SHA),
        (l2p, L2_SHA),
        (v16p, V16_SHA),
    ):
        require(
            digest(path) == expected,
            "SHA mismatch " + path.name,
        )

    require(
        out.is_dir() and not out.is_symlink(),
        "Unsafe output directory",
    )

    l1, l2, v16 = [
        json.loads(path.read_text())
        for path in (l1p, l2p, v16p)
    ]

    first = decisions(l1, l2, v16)
    second = decisions(l1, l2, v16)

    require(
        canon(first) == canon(second),
        "Non-deterministic decision",
    )

    require(
        len(first) == 10
        and all(
            row["admission"] == "DENIED"
            and row["estimator_pose_increment"] is None
            for row in first
        ),
        "Nonzero pose factor admission",
    )

    tests = selftests(l1, l2, v16)

    result = {
        "schema":
            "TRUST_ROBOT_L3_V16_FAIL_CLOSED_FACTOR_ADMISSION_V1",
        "l1_sha256": L1_SHA,
        "l2_sha256": L2_SHA,
        "v16_sha256": V16_SHA,
        "implementation_sha256":
            digest(Path(__file__)),
        "factor_decisions": first,
        "factor_candidates_examined": len(first),
        "factors_admitted": 0,
        "sparse_pairs_rejected": 2,
        "unqualified_nonsparse_pairs_rejected": 8,
        "negative_tampering_tests_passed": tests,
        "deterministic_rederivation_identical": True,
        "no_scientific_selection_thresholds_introduced": True,
        "phase2_frontend_modified": False,
        "phase4_extractor_modified": False,
        "health_labels_generated": False,
        "health_model_training_authorized": False,
        "physical_sensor_synchronization_verified": False,
        "independent_reference_scoring_performed": False,
        "engineering_gate_pass": True,
    }

    target = out / "l3_factor_admission_report_v1.json"

    with target.open("x") as file:
        json.dump(
            result, file,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        file.write("\n")

    for row in first:
        print(
            "L3_DECISION=",
            json.dumps({
                "condition": row["condition"],
                "steps": [
                    row["previous_step"],
                    row["current_step"],
                ],
                "admission": row["admission"],
                "reason_codes": row["reason_codes"],
            }, sort_keys=True),
        )

    print("FACTOR_CANDIDATES_EXAMINED=", len(first))
    print("FACTORS_ADMITTED=0")
    print("NEGATIVE_TAMPERING_TESTS_PASSED=", tests)
    print("L3_FAIL_CLOSED_GATE=PASS")
    print("L3_REPORT_SHA256=", digest(target))

if __name__ == "__main__":
    main()
