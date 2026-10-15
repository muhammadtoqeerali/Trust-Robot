"""L23 structured synthetic LiDAR corruption audit.

Reuses the exact L22 recomputation logic for all eight
uncalibrated L20 ambiguity metrics.

All transformations affect in-memory copies only.
No physical sensor errors, calibrated noise, independent
ground truth, health labels or authorized pose factors.
"""

import hashlib
import json
import math
import runpy
import sys

from collections import Counter
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation


SCENARIOS = (
    ("single_return_20mm_101", "single_return", 5, 0.020),
    ("single_return_80mm_101", "single_return", 5, 0.080),
    ("single_return_80mm_91", "single_return", 4, 0.080),

    ("nonrigid_shear_3pct", "shear", 5, 0.03),
    ("nonrigid_shear_15pct", "shear", 5, 0.15),

    ("coherent_rotation_3deg", "rotation", 5, 3.0),
    ("coherent_rotation_10deg", "rotation", 5, 10.0),

    ("coherent_translation_80mm", "translation", 5, 0.080),

    ("stale_scan_101_from_91", "stale_scan", 5, 0.0),

    (
        "point_order_changed_mapping_corrected",
        "permutation_corrected",
        5,
        0.0,
    ),

    (
        "point_order_changed_mapping_stale",
        "permutation_stale",
        5,
        0.0,
    ),
)

STEPS = (51, 61, 71, 81, 91, 101)

VALID_DECISIONS = {
    "NOT_FLAGGED_DIAGNOSTIC_ONLY",
    "SENSITIVITY_REVIEW",
    "STRUCTURAL_REVIEW",
    "NOT_EVALUABLE",
}


def sha(path):
    assert path.is_file() and not path.is_symlink(), path

    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def load(path):
    sha(path)

    return json.loads(
        path.read_text()
    )


def canonical(value):
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ) + "\n"
    ).encode()


def cloud_digest(clouds):
    digest = hashlib.sha256()

    for cloud in clouds:
        assert cloud.shape == (16, 3)
        assert np.isfinite(cloud).all()

        digest.update(
            np.ascontiguousarray(
                cloud,
                dtype=np.float64,
            ).tobytes()
        )

    return digest.hexdigest()


def build_case(original, orders, specification):
    name, kind, index, magnitude = specification

    assert index == 5 or index == 4

    clouds = [
        np.asarray(x, dtype=np.float64).copy()
        for x in original
    ]

    mapping = [
        np.asarray(x, dtype=np.int64).copy()
        for x in orders
    ]

    before = clouds[index].copy()

    association_only = False
    geometry_pointset_preserved = False

    if kind == "single_return":
        row = 7 if index == 5 else 4

        clouds[index][row] += np.array([
            magnitude,
            0.0,
            0.0,
        ])

    elif kind == "shear":
        centered_x = (
            clouds[index][:, 0]
            - clouds[index][:, 0].mean()
        )

        clouds[index][:, 1] += (
            magnitude * centered_x
        )

    elif kind == "rotation":
        center = clouds[index].mean(axis=0)

        rotation = Rotation.from_euler(
            "z",
            magnitude,
            degrees=True,
        ).as_matrix()

        clouds[index] = (
            (clouds[index] - center)
            @ rotation.T
            + center
        )

    elif kind == "translation":
        clouds[index] += np.array([
            magnitude,
            0.0,
            0.0,
        ])

    elif kind == "stale_scan":
        assert index == 5

        clouds[5] = clouds[4].copy()

    elif kind in (
        "permutation_corrected",
        "permutation_stale",
    ):
        assert index == 5

        permutation = np.arange(16)

        permutation[[3, 12]] = (
            permutation[[12, 3]]
        )

        clouds[index] = clouds[index][permutation]

        geometry_pointset_preserved = True
        association_only = True

        if kind == "permutation_corrected":
            inverse_permutation = np.argsort(
                permutation
            )

            mapping[index] = (
                inverse_permutation[mapping[index]]
            )

            # The beam-indexed point cloud must be
            # bitwise identical to the original.
            assert np.array_equal(
                clouds[index][mapping[index]],
                original[index][orders[index]],
            )

    else:
        raise AssertionError(
            "Unknown scenario " + name
        )

    for cloud, order in zip(clouds, mapping):
        assert cloud.shape == (16, 3)
        assert np.isfinite(cloud).all()

        assert sorted(
            map(int, order)
        ) == list(range(16))

    change = clouds[index] - before

    max_row_displacement = float(
        np.max(
            np.linalg.norm(
                change,
                axis=1,
            )
        )
    )

    return clouds, mapping, {
        "scenario": name,
        "type": kind,

        "affected_recorded_step": STEPS[index],

        "nominal_parameter": float(magnitude),

        "maximum_rowwise_difference_m":
            max_row_displacement,

        "pointset_preserved":
            geometry_pointset_preserved,

        "association_only":
            association_only,

        "original_sensor_files_modified":
            False,

        "altered_clouds_sha256":
            cloud_digest(clouds),
    }


def compare_rows(actual, baseline, scenario_name):
    assert len(actual) == len(baseline) == 10

    original_by_pair = {
        tuple(row["steps"]): row
        for row in baseline
    }

    assert len(original_by_pair) == 10

    trials = []

    for row in actual:
        pair = tuple(row["steps"])
        old = original_by_pair[pair]

        status = row["status"]

        if status == "DIAGNOSTIC_RECOMPUTED":
            decision = row["screen"]["decision"]

            assert decision in VALID_DECISIONS
            assert decision != "NOT_EVALUABLE"

            assert row["pose_factor_authorized"] is False

            metrics = row["metrics"]

            assert len(metrics) == 8

            assert all(
                math.isfinite(float(value))
                for value in metrics.values()
            )

        else:
            assert status == "NOT_EVALUABLE"

            decision = "NOT_EVALUABLE"

            assert row["metrics"] is None
            assert row["screen"] is None

        previous = old["screen"]["decision"]

        # A registration that cannot be evaluated
        # must never be treated as an acceptable pose.
        manual_review = (
            decision != "NOT_FLAGGED_DIAGNOSTIC_ONLY"
        )

        trials.append({
            "scenario": scenario_name,

            "steps": list(pair),

            "status": status,

            "not_evaluable_reason":
                row.get("reason"),

            "baseline_decision": previous,
            "new_decision": decision,

            "decision_changed":
                decision != previous,

            "manual_review_required":
                manual_review,

            "previously_not_flagged_now_review":
                (
                    previous ==
                    "NOT_FLAGGED_DIAGNOSTIC_ONLY"
                    and manual_review
                ),

            "previously_review_now_not_flagged":
                (
                    previous !=
                    "NOT_FLAGGED_DIAGNOSTIC_ONLY"
                    and not manual_review
                ),

            "pose_factor_authorized": False,
        })

    assert len(trials) == 10

    return trials


def derive(
    original,
    orders,
    baseline,
    api17,
    api18,
    api19,
    api20,
    api22,
):
    scenario_results = []
    all_trials = []

    for spec in SCENARIOS:
        clouds, mappings, descriptor = build_case(
            original,
            orders,
            spec,
        )

        recomputed, chain_failure = (
            api22["recompute"](
                clouds,
                mappings,
                api17,
                api18,
                api19,
                api20,
            )
        )

        trials = compare_rows(
            recomputed,
            baseline,
            descriptor["scenario"],
        )

        all_trials.extend(trials)

        counts = Counter(
            row["new_decision"]
            for row in trials
        )

        summary = {
            **descriptor,

            "chain_failure": chain_failure,

            "attempted_pairs": len(trials),

            "recomputed_pairs":
                len(trials) - counts["NOT_EVALUABLE"],

            "not_evaluable":
                counts["NOT_EVALUABLE"],

            "structural_review":
                counts["STRUCTURAL_REVIEW"],

            "sensitivity_review":
                counts["SENSITIVITY_REVIEW"],

            "not_flagged":
                counts["NOT_FLAGGED_DIAGNOSTIC_ONLY"],

            "decision_changes": sum(
                x["decision_changed"]
                for x in trials
            ),

            "new_review_from_unflagged": sum(
                x["previously_not_flagged_now_review"]
                for x in trials
            ),

            "review_to_unflagged": sum(
                x["previously_review_now_not_flagged"]
                for x in trials
            ),
        }

        assert (
            summary["recomputed_pairs"]
            + summary["not_evaluable"]
        ) == 10

        assert (
            summary["structural_review"]
            + summary["sensitivity_review"]
            + summary["not_flagged"]
            + summary["not_evaluable"]
        ) == 10

        scenario_results.append(summary)

    assert len(scenario_results) == len(SCENARIOS)
    assert len(all_trials) == 10 * len(SCENARIOS)

    corrected = next(
        x for x in scenario_results
        if x["type"] == "permutation_corrected"
    )

    stale_mapping = next(
        x for x in scenario_results
        if x["type"] == "permutation_stale"
    )

    assert corrected["pointset_preserved"] is True
    assert stale_mapping["pointset_preserved"] is True

    decision_transitions = Counter(
        (
            row["baseline_decision"]
            + " -> "
            + row["new_decision"]
        )
        for row in all_trials
    )

    return {
        "scenario_summaries": scenario_results,

        "pair_trials": all_trials,

        "decision_transitions": dict(
            sorted(decision_transitions.items())
        ),

        "scenario_count": len(SCENARIOS),

        "total_pair_trials": len(all_trials),

        "recomputed_pairs": sum(
            x["recomputed_pairs"]
            for x in scenario_results
        ),

        "not_evaluable_pairs": sum(
            x["not_evaluable"]
            for x in scenario_results
        ),

        "decision_changes": sum(
            x["decision_changes"]
            for x in scenario_results
        ),

        "point_permutation_control_decision_changes":
            corrected["decision_changes"],

        "stale_mapping_decision_changes":
            stale_mapping["decision_changes"],

        "not_evaluable_treated_as_review":
            True,

        "severe_corruption_can_remain_unflagged":
            any(
                row["not_flagged"] > 0
                and row["type"] not in (
                    "permutation_corrected",
                    "permutation_stale",
                )
                for row in scenario_results
            ),
    }


def main():
    # 11 positional arguments plus program name.
    assert len(sys.argv) == 12

    (
        run,
        p15,
        p19,
        p20,
        p22,
        s17,
        s18,
        s19,
        s20,
        s22,
        out,
    ) = map(Path, sys.argv[1:])

    assert run.is_dir() and not run.is_symlink()
    assert out.is_dir() and not out.is_symlink()

    l15 = load(p15)
    l19 = load(p19)
    l20 = load(p20)
    l22 = load(p22)

    assert l22["upstream_report_sha256"]["l15"] == sha(
        p15
    )

    assert l22["upstream_report_sha256"]["l19"] == sha(
        p19
    )

    assert l22["upstream_report_sha256"]["l20"] == sha(
        p20
    )

    assert l22["implementation_sha256"] == sha(s22)

    for name, path in (
        ("l17", s17),
        ("l18", s18),
        ("l19", s19),
        ("l20", s20),
    ):
        assert l22[
            "reused_implementation_sha256"
        ][name] == sha(path)

    assert (
        l15["pose_factors_authorized"]
        == l19["pose_factors_authorized"]
        == l20["pose_factors_authorized"]
        == l22["pose_factors_authorized"]
        == 0
    )

    assert l22["unperturbed_baseline_reproduced"] is True
    assert l22["two_derivations_identical"] is True

    api17 = runpy.run_path(str(s17))
    api18 = runpy.run_path(str(s18))
    api19 = runpy.run_path(str(s19))
    api20 = runpy.run_path(str(s20))
    api22 = runpy.run_path(str(s22))

    original, orders, cloud_provenance = (
        api22["load_scans"](
            run,
            l15,
            l19,
        )
    )

    unmodified, failure = api22["recompute"](
        original,
        orders,
        api17,
        api18,
        api19,
        api20,
    )

    assert failure is None

    api22["compare_baseline"](
        unmodified,
        l20["pair_screens"],
    )

    first = derive(
        original,
        orders,
        unmodified,
        api17,
        api18,
        api19,
        api20,
        api22,
    )

    second = derive(
        original,
        orders,
        unmodified,
        api17,
        api18,
        api19,
        api20,
        api22,
    )

    assert canonical(first) == canonical(second)

    report = {
        "schema":
            "TRUST_ROBOT_L23_STRUCTURED_CLOUD_STRESS_DIAGNOSTIC_V1",

        "implementation_sha256":
            sha(Path(__file__)),

        "upstream_sha256": {
            "l15": sha(p15),
            "l19": sha(p19),
            "l20": sha(p20),
            "l22": sha(p22),
        },

        "reused_source_sha256": {
            "l17": sha(s17),
            "l18": sha(s18),
            "l19": sha(s19),
            "l20": sha(s20),
            "l22": sha(s22),
        },

        "recorded_scan_provenance":
            cloud_provenance,

        "unmodified_l20_baseline_reproduced":
            True,

        "two_derivations_identical":
            True,

        "all_eight_metrics_recomputed":
            True,

        "all_corruptions_applied_in_memory":
            True,

        "original_recordings_modified":
            False,

        "injected_corruptions_are_calibrated_sensor_faults":
            False,

        "experiment_is_independent_failure_validation":
            False,

        "thresholds_scientifically_calibrated":
            False,

        "physical_localization_accuracy_verified":
            False,

        "false_positive_rate_estimated":
            False,

        "false_negative_rate_estimated":
            False,

        "health_labels_generated": 0,
        "pose_factors_authorized": 0,

        **first,
    }

    destination = (
        out / "l23_structured_stress_diagnostic_v1.json"
    )

    with destination.open("x") as stream:
        json.dump(
            report,
            stream,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )

        stream.write("\n")

    for row in first["scenario_summaries"]:
        print(
            "L23_SCENARIO=",
            json.dumps(
                row,
                sort_keys=True,
            ),
            flush=True,
        )

    print(
        "L23_DECISION_TRANSITIONS=",
        json.dumps(
            first["decision_transitions"],
            sort_keys=True,
        ),
        flush=True,
    )

    print(
        "L23_RECOMPUTED_PAIRS=",
        first["recomputed_pairs"],
    )

    print(
        "L23_NOT_EVALUABLE_PAIRS=",
        first["not_evaluable_pairs"],
    )

    print(
        "L23_TOTAL_DECISION_CHANGES=",
        first["decision_changes"],
    )

    print(
        "L23_CORRECTED_PERMUTATION_DECISION_CHANGES=",
        first[
            "point_permutation_control_decision_changes"
        ],
    )

    print(
        "L23_STALE_MAPPING_DECISION_CHANGES=",
        first["stale_mapping_decision_changes"],
    )

    print("L23_DETERMINISTIC_REDERIVATION=PASS")
    print("L23_STRUCTURED_STRESS_AUDIT=PASS")
    print("QUALIFIED_POSE_FACTORS=0")

    print(
        "L23_REPORT_SHA256=",
        sha(destination),
    )


if __name__ == "__main__":
    main()
