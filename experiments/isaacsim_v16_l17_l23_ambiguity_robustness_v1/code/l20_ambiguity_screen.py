"""L20 conservative synthetic evidence screen.

This is a research diagnostic, not a qualified estimator gate.
Thresholds are exploratory and uncalibrated.
"""

import hashlib
import json
import math
import sys

from pathlib import Path

THRESHOLDS = {
    "closure_rotation_deg": 1.0,
    "closure_translation_m": 0.010,
    "seed_spread_rotation_deg": 2.0,
    "seed_spread_translation_m": 0.030,
    "jackknife_rotation_deg": 1.5,
    "jackknife_translation_m": 0.020,
    "bijective_nn_cost_penalty_m": 0.005,
}

STEPS = (51, 61, 71, 81, 91, 101)


def sha(path):
    assert path.is_file() and not path.is_symlink(), path
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    sha(path)
    return json.loads(path.read_text())


def close(a, b):
    return math.isclose(
        float(a),
        float(b),
        rel_tol=1e-7,
        abs_tol=1e-9,
    )


def evaluate(metric, multiplier=1.0):
    thresholds = {
        key: value * multiplier
        for key, value in THRESHOLDS.items()
    }

    structural = []
    sensitivity = []

    if metric["duplicate_target_assignments"] > 0:
        structural.append(
            "NN_DUPLICATE_TARGET"
        )

    if metric["closure_rotation_deg"] > thresholds[
        "closure_rotation_deg"
    ]:
        structural.append(
            "DIRECT_CHAIN_ROTATION_DISCREPANCY"
        )

    if metric["closure_translation_m"] > thresholds[
        "closure_translation_m"
    ]:
        structural.append(
            "DIRECT_CHAIN_TRANSLATION_DISCREPANCY"
        )

    if metric["seed_spread_rotation_deg"] > thresholds[
        "seed_spread_rotation_deg"
    ]:
        sensitivity.append(
            "MULTISEED_ROTATION_DISAGREEMENT"
        )

    if metric["seed_spread_translation_m"] > thresholds[
        "seed_spread_translation_m"
    ]:
        sensitivity.append(
            "MULTISEED_TRANSLATION_DISAGREEMENT"
        )

    if metric["jackknife_rotation_deg"] > thresholds[
        "jackknife_rotation_deg"
    ]:
        sensitivity.append(
            "ONE_BEAM_ROTATION_SENSITIVITY"
        )

    if metric["jackknife_translation_m"] > thresholds[
        "jackknife_translation_m"
    ]:
        sensitivity.append(
            "ONE_BEAM_TRANSLATION_SENSITIVITY"
        )

    if metric["bijective_nn_cost_penalty_m"] > thresholds[
        "bijective_nn_cost_penalty_m"
    ]:
        sensitivity.append(
            "ALTERNATIVE_OBJECTIVE_CONFLICT"
        )

    if structural:
        decision = "STRUCTURAL_REVIEW"
    elif sensitivity:
        decision = "SENSITIVITY_REVIEW"
    else:
        decision = "NOT_FLAGGED_DIAGNOSTIC_ONLY"

    return {
        "decision": decision,
        "structural_triggers": structural,
        "sensitivity_triggers": sensitivity,
    }


def controls():
    keys = list(THRESHOLDS) + [
        "duplicate_target_assignments"
    ]

    zero = {
        key: 0
        for key in keys
    }

    assert evaluate(zero)["decision"] == (
        "NOT_FLAGGED_DIAGNOSTIC_ONLY"
    )

    for field in keys:
        probe = zero.copy()

        probe[field] = (
            1
            if field == "duplicate_target_assignments"
            else THRESHOLDS[field] * 1.1
        )

        result = evaluate(probe)

        assert result["decision"] != (
            "NOT_FLAGGED_DIAGNOSTIC_ONLY"
        ), field

        if field != "duplicate_target_assignments":
            probe[field] = THRESHOLDS[field]

            assert evaluate(probe)["decision"] == (
                "NOT_FLAGGED_DIAGNOSTIC_ONLY"
            ), field

    changed = {
        **zero,
        "closure_rotation_deg": 1.5,
    }

    assert evaluate(
        changed, 0.5
    )["decision"] == "STRUCTURAL_REVIEW"

    assert evaluate(
        changed, 2.0
    )["decision"] == "NOT_FLAGGED_DIAGNOSTIC_ONLY"

    print(
        "L20_RULE_NEGATIVE_CONTROLS=PASS",
        flush=True,
    )


def evidence(l15, l16, l17, l18, l19):
    assert l16["l15_report_sha256"] == sha(
        l15["path"]
    )

    assert l17["upstream_l16_sha256"] == sha(
        l16["path"]
    )

    assert l17["upstream_l15_sha256"] == sha(
        l15["path"]
    )

    assert l18["upstream_l17_sha256"] == sha(
        l17["path"]
    )

    assert l18["upstream_l16_sha256"] == sha(
        l16["path"]
    )

    assert l19["l18_report_sha256"] == sha(
        l18["path"]
    )

    assert l19["l16_report_sha256"] == sha(
        l16["path"]
    )

    assert l19["l15_report_sha256"] == sha(
        l15["path"]
    )

    for item in (l15, l16, l17, l18, l19):
        assert item["pose_factors_authorized"] == 0

    assert len(l16["all_pairs"]) == 15

    assert (
        len(l17["pair_cases"])
        == len(l18["pair_cases"])
        == 10
    )

    assert len(l19["pair_diagnostics"]) == 15

    assert l17["two_derivations_identical"] is True
    assert l18["two_derivations_identical"] is True

    assert l19[
        "deterministic_two_derivations_identical"
    ] is True

    return {
        "l16": {
            tuple(row["steps"]): row
            for row in l16["all_pairs"]
        },

        "l17": {
            tuple(row["steps"]): row
            for row in l17["pair_cases"]
        },

        "l18": {
            tuple(row["steps"]): row
            for row in l18["pair_cases"]
        },

        "l19": {
            tuple(row["steps"]): row
            for row in l19["pair_diagnostics"]
        },
    }


def derive(groups):
    keys = [
        (STEPS[i], STEPS[j])
        for i in range(6)
        for j in range(i + 2, 6)
    ]

    assert len(keys) == 10

    rows = []

    for pair in keys:
        a, b, c, d = (
            groups[key][pair]
            for key in ("l16", "l17", "l18", "l19")
        )

        assert a["status"] == "DIAGNOSTIC_AVAILABLE"

        direct = a["direct_vs_composed_se3"]

        assert direct is not None

        assert close(
            direct["rotation_deg"],
            b["identity_start"][
                "difference_from_short_chain"
            ]["rotation_deg"],
        )

        assert close(
            direct["translation_m"],
            b["identity_start"][
                "difference_from_short_chain"
            ]["translation_m"],
        )

        assert close(
            direct["rotation_deg"],
            c["frozen_identity"][
                "difference_from_chain"
            ]["rotation_deg"],
        )

        assert close(
            direct["rotation_deg"],
            d["frozen_identity"][
                "direct_vs_chain"
            ]["rotation_deg"],
        )

        assert close(
            a["rmse_m"],
            b["identity_start"]["rmse_m"],
        )

        assert close(
            a["rmse_m"],
            c["frozen_identity"][
                "nearest_neighbor"
            ]["nearest_rmse_m"],
        )

        assert close(
            a["rmse_m"],
            d["frozen_identity"]["nearest_rmse_m"],
        )

        duplicates = b["identity_start"][
            "nearest_neighbor_topology"
        ]["duplicate_target_assignments"]

        assert duplicates == c["frozen_identity"][
            "nearest_neighbor"
        ]["duplicate_nearest_targets"]

        bijective = c[
            "experimental_one_to_one"
        ]["identity"]

        assert bijective["status"] == (
            "DIAGNOSTIC_AVAILABLE"
        )

        assert close(
            bijective["nearest_neighbor"]["nearest_rmse_m"],
            d["l18_bijective_identity_diagnostic"][
                "nearest_rmse_m"
            ],
        )

        jackknife = d[
            "inferred_emitter_index_fit"
        ]["leave_one_emitter_out"]

        spread = b["seed_solution_spread"]

        assert spread["available"] == 7

        metric = {
            "duplicate_target_assignments":
                int(duplicates),

            "closure_rotation_deg":
                float(direct["rotation_deg"]),

            "closure_translation_m":
                float(direct["translation_m"]),

            "seed_spread_rotation_deg":
                float(
                    spread["max_pairwise_rotation_deg"]
                ),

            "seed_spread_translation_m":
                float(
                    spread["max_pairwise_translation_m"]
                ),

            "jackknife_rotation_deg":
                float(
                    jackknife["maximum_rotation_change_deg"]
                ),

            "jackknife_translation_m":
                float(
                    jackknife["maximum_translation_change_m"]
                ),

            "bijective_nn_cost_penalty_m":
                float(
                    bijective["nearest_neighbor"][
                        "nearest_rmse_m"
                    ] - a["rmse_m"]
                ),
        }

        assert all(
            math.isfinite(value)
            for value in metric.values()
        )

        assert metric[
            "duplicate_target_assignments"
        ] >= 0

        rows.append({
            "steps": list(pair),

            "hop_count":
                (pair[1] - pair[0]) // 10,

            "metrics": metric,

            "screen": evaluate(metric),

            "not_scientifically_qualified": True,

            "pose_factor_authorized": False,
        })

    threshold_sensitivity = []

    for name, scale in (
        ("stricter_half_thresholds", 0.5),
        ("nominal_unvalidated_thresholds", 1.0),
        ("looser_double_thresholds", 2.0),
    ):
        outcomes = [
            evaluate(row["metrics"], scale)["decision"]
            for row in rows
        ]

        threshold_sensitivity.append({
            "scenario": name,
            "threshold_multiplier": scale,

            "review_required": sum(
                value != "NOT_FLAGGED_DIAGNOSTIC_ONLY"
                for value in outcomes
            ),

            "structural_review":
                outcomes.count("STRUCTURAL_REVIEW"),
        })

    hop_summary = []

    for hop in range(2, 6):
        group = [
            row for row in rows
            if row["hop_count"] == hop
        ]

        decisions = [
            row["screen"]["decision"]
            for row in group
        ]

        hop_summary.append({
            "hop_count": hop,
            "pair_count": len(group),

            "structural_review":
                decisions.count("STRUCTURAL_REVIEW"),

            "sensitivity_review":
                decisions.count("SENSITIVITY_REVIEW"),

            "not_flagged":
                decisions.count(
                    "NOT_FLAGGED_DIAGNOSTIC_ONLY"
                ),
        })

    return {
        "pair_screens": rows,
        "hop_summary": hop_summary,
        "threshold_sensitivity":
            threshold_sensitivity,
    }


def main():
    assert len(sys.argv) == 7

    a, b, c, d, e, out = map(
        Path, sys.argv[1:]
    )

    assert out.is_dir() and not out.is_symlink()

    objects = []

    for path in (a, b, c, d, e):
        obj = load(path)
        obj["path"] = path
        objects.append(obj)

    controls()

    groups = evidence(*objects)

    first = derive(groups)
    second = derive(groups)

    assert json.dumps(
        first,
        sort_keys=True,
        allow_nan=False,
    ) == json.dumps(
        second,
        sort_keys=True,
        allow_nan=False,
    )

    report = {
        "schema":
            "TRUST_ROBOT_L20_SYNTHETIC_LONG_BASELINE_AMBIGUITY_SCREEN_V1",

        "implementation_sha256":
            sha(Path(__file__)),

        "upstream_sha256": {
            "l15": sha(a),
            "l16": sha(b),
            "l17": sha(c),
            "l18": sha(d),
            "l19": sha(e),
        },

        "thresholds_exploratory_not_calibrated":
            THRESHOLDS,

        "screen_is_diagnostic_only": True,

        "not_flagged_does_not_mean_accurate":
            True,

        "chain_and_beam_associations_are_not_independent_ground_truth":
            True,

        "independent_reference_verified": False,
        "sensor_sync_verified": False,

        "health_labels_generated": 0,
        "pose_factors_authorized": 0,

        "repeated_derivation_identical": True,

        **first,
    }

    target = (
        out / "l20_ambiguity_screen_report_v1.json"
    )

    with target.open("x") as stream:
        json.dump(
            report,
            stream,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        stream.write("\n")

    for row in first["pair_screens"]:
        print(
            "L20_PAIR_SCREEN=",
            json.dumps({
                "steps": row["steps"],
                "hops": row["hop_count"],

                "decision":
                    row["screen"]["decision"],

                "structural":
                    row["screen"]["structural_triggers"],

                "sensitivity":
                    row["screen"]["sensitivity_triggers"],
            }, sort_keys=True),
            flush=True,
        )

    for row in first["hop_summary"]:
        print(
            "L20_HOP_SUMMARY=",
            json.dumps(row, sort_keys=True),
            flush=True,
        )

    for row in first["threshold_sensitivity"]:
        print(
            "L20_THRESHOLD_SENSITIVITY=",
            json.dumps(row, sort_keys=True),
            flush=True,
        )

    print("L20_SOURCE_CHAIN=VERIFIED")
    print("L20_REDERIVATION=PASS")
    print("L20_DIAGNOSTIC_SCREEN=PASS")
    print("QUALIFIED_POSE_FACTORS=0")

    print(
        "L20_REPORT_SHA256=",
        sha(target),
    )


if __name__ == "__main__":
    main()
