"""L21: falsification tests for the experimental L20 screen.

All mutations are in memory. This tests rule behavior and
evidence consistency, not sensor health classification.
"""

import copy
import hashlib
import json
import math
import runpy
import sys
from pathlib import Path

STEPS = (51, 61, 71, 81, 91, 101)

PINNED = {
    "l15":
        "da5a45d217d6c27d565acabef8c6c454d7d3f691d5d7dd375c780c0b37f6b1c9",
    "l16":
        "2a1ebca297ca4d58ab2d2ff0a9aa3104673e12aef9dd6e1f43ce5167617cfdaf",
    "l17":
        "1161a181982b3af155626ed889ab5a21010e86ea3fa64eadbf9bb4cbf1f722da",
    "l18":
        "787117369a6e5bda511325343916f5c8d3d93cd4a4db92f04b0fb49e4b413bac",
    "l19":
        "5762341d44de5771508c5689bd636aff49a9368e363aa1d3d3a686f1e18fb0cf",
    "l20":
        "e93519d92257180bcfca3ca8b0aca781da89bcb000612c02d1f3202a4c1cbae6",
}

REFERENCE_THRESHOLDS = {
    "closure_rotation_deg": 1.0,
    "closure_translation_m": 0.010,
    "seed_spread_rotation_deg": 2.0,
    "seed_spread_translation_m": 0.030,
    "jackknife_rotation_deg": 1.5,
    "jackknife_translation_m": 0.020,
    "bijective_nn_cost_penalty_m": 0.005,
}

STRUCTURAL = (
    ("closure_rotation_deg",
     "DIRECT_CHAIN_ROTATION_DISCREPANCY"),
    ("closure_translation_m",
     "DIRECT_CHAIN_TRANSLATION_DISCREPANCY"),
)

SENSITIVITY = (
    ("seed_spread_rotation_deg",
     "MULTISEED_ROTATION_DISAGREEMENT"),
    ("seed_spread_translation_m",
     "MULTISEED_TRANSLATION_DISAGREEMENT"),
    ("jackknife_rotation_deg",
     "ONE_BEAM_ROTATION_SENSITIVITY"),
    ("jackknife_translation_m",
     "ONE_BEAM_TRANSLATION_SENSITIVITY"),
    ("bijective_nn_cost_penalty_m",
     "ALTERNATIVE_OBJECTIVE_CONFLICT"),
)


def sha(path):
    assert path.is_file() and not path.is_symlink()
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    sha(path)
    return json.loads(path.read_text())


def stable(obj):
    return (
        json.dumps(
            obj,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ) + "\n"
    ).encode()


def shadow_evaluate(metric, multiplier=1.0):
    """Independent reference implementation of L20 rules."""

    structural = []
    sensitivity = []

    if metric["duplicate_target_assignments"] > 0:
        structural.append("NN_DUPLICATE_TARGET")

    for key, name in STRUCTURAL:
        if metric[key] > (
            REFERENCE_THRESHOLDS[key] * multiplier
        ):
            structural.append(name)

    for key, name in SENSITIVITY:
        if metric[key] > (
            REFERENCE_THRESHOLDS[key] * multiplier
        ):
            sensitivity.append(name)

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


def metric_from_upstream(pair, upstream):
    l16, l17, l18, l19 = upstream

    a = l16[pair]
    b = l17[pair]
    c = l18[pair]
    d = l19[pair]

    assert a["status"] == "DIAGNOSTIC_AVAILABLE"

    direct = a["direct_vs_composed_se3"]
    assert direct is not None

    topology = b["identity_start"][
        "nearest_neighbor_topology"
    ]

    alternative = c["experimental_one_to_one"][
        "identity"
    ]

    assert alternative["status"] == (
        "DIAGNOSTIC_AVAILABLE"
    )

    spread = b["seed_solution_spread"]

    assert spread["available"] == 7

    jackknife = d["inferred_emitter_index_fit"][
        "leave_one_emitter_out"
    ]

    return {
        "duplicate_target_assignments":
            int(topology["duplicate_target_assignments"]),

        "closure_rotation_deg":
            float(direct["rotation_deg"]),

        "closure_translation_m":
            float(direct["translation_m"]),

        "seed_spread_rotation_deg":
            float(spread["max_pairwise_rotation_deg"]),

        "seed_spread_translation_m":
            float(spread["max_pairwise_translation_m"]),

        "jackknife_rotation_deg":
            float(jackknife["maximum_rotation_change_deg"]),

        "jackknife_translation_m":
            float(jackknife["maximum_translation_change_m"]),

        "bijective_nn_cost_penalty_m":
            float(
                alternative["nearest_neighbor"]["nearest_rmse_m"]
                - a["rmse_m"]
            ),
    }


def prepare_upstream(docs):
    indexed = []

    for name, field in (
        ("l16", "all_pairs"),
        ("l17", "pair_cases"),
        ("l18", "pair_cases"),
        ("l19", "pair_diagnostics"),
    ):
        rows = {
            tuple(row["steps"]): row
            for row in docs[name][field]
        }

        indexed.append(rows)

    assert len(indexed[0]) == 15
    # L17 and L18 contain ten nonadjacent pairs.
    # L19 includes all fifteen unordered pairs.
    assert len(indexed[1]) == 10
    assert len(indexed[2]) == 10
    assert len(indexed[3]) == 15

    # Every screened pair must exist in all sources.
    assert set(indexed[1]) == set(indexed[2])
    assert set(indexed[1]).issubset(set(indexed[3]))

    return indexed


def screen_consistent(doc, docs, hashes, engine):
    """Fail closed on any rule, lineage or metric mismatch."""

    assert doc["implementation_sha256"] == hashes[
        "source"
    ]

    assert doc["upstream_sha256"] == {
        name: hashes[name]
        for name in ("l15", "l16", "l17", "l18", "l19")
    }

    assert doc["thresholds_exploratory_not_calibrated"] == (
        REFERENCE_THRESHOLDS
    )

    assert doc["screen_is_diagnostic_only"] is True
    assert doc["not_flagged_does_not_mean_accurate"] is True
    assert doc["independent_reference_verified"] is False
    assert doc["sensor_sync_verified"] is False

    assert doc["pose_factors_authorized"] == 0
    assert doc["health_labels_generated"] == 0

    indexed = prepare_upstream(docs)

    expected_pairs = [
        (STEPS[i], STEPS[j])
        for i in range(6)
        for j in range(i + 2, 6)
    ]

    rows = doc["pair_screens"]

    assert len(rows) == 10
    assert [
        tuple(row["steps"]) for row in rows
    ] == expected_pairs

    for row in rows:
        pair = tuple(row["steps"])

        assert row["hop_count"] == (
            (pair[1] - pair[0]) // 10
        )

        assert row["pose_factor_authorized"] is False
        assert row["not_scientifically_qualified"] is True

        metric = row["metrics"]

        assert set(metric) == {
            "duplicate_target_assignments",
            *REFERENCE_THRESHOLDS,
        }

        assert all(
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
            for value in metric.values()
        )

        assert (
            metric["duplicate_target_assignments"] >= 0
        )

        # Independent source-derived metric verification.
        assert metric == metric_from_upstream(
            pair, indexed
        ), pair

        assert row["screen"] == engine(metric)
        assert row["screen"] == shadow_evaluate(metric)

    for scale, expected_name in (
        (0.5, "stricter_half_thresholds"),
        (1.0, "nominal_unvalidated_thresholds"),
        (2.0, "looser_double_thresholds"),
    ):
        entry = next(
            x for x in doc["threshold_sensitivity"]
            if x["scenario"] == expected_name
        )

        results = [
            shadow_evaluate(x["metrics"], scale)[
                "decision"
            ]
            for x in rows
        ]

        assert entry["review_required"] == sum(
            x != "NOT_FLAGGED_DIAGNOSTIC_ONLY"
            for x in results
        )

        assert entry["structural_review"] == (
            results.count("STRUCTURAL_REVIEW")
        )

    return True


def run_challenges(docs, hashes, engine):
    l20 = docs["l20"]

    assert screen_consistent(
        l20, docs, hashes, engine
    )

    zero = {
        "duplicate_target_assignments": 0,
        **{
            key: 0.0
            for key in REFERENCE_THRESHOLDS
        },
    }

    assert engine(zero) == shadow_evaluate(zero)
    assert engine(zero)["decision"] == (
        "NOT_FLAGGED_DIAGNOSTIC_ONLY"
    )

    boundary_count = 0

    # Each uncalibrated numeric threshold is probed
    # immediately below, at and above its value.
    for key, threshold in REFERENCE_THRESHOLDS.items():
        for factor in (0.9999, 1.0, 1.0001):
            sample = dict(zero)
            sample[key] = threshold * factor

            actual = engine(sample)
            expected = shadow_evaluate(sample)

            assert actual == expected

            should_flag = factor > 1

            assert (
                actual["decision"]
                != "NOT_FLAGGED_DIAGNOSTIC_ONLY"
            ) is should_flag

            boundary_count += 1

    for duplicate in (0, 1):
        sample = dict(zero)
        sample["duplicate_target_assignments"] = (
            duplicate
        )

        assert engine(sample) == shadow_evaluate(sample)

        if duplicate:
            assert engine(sample)["decision"] == (
                "STRUCTURAL_REVIEW"
            )
        else:
            assert engine(sample)["decision"] == (
                "NOT_FLAGGED_DIAGNOSTIC_ONLY"
            )

        boundary_count += 1

    severity = {
        "NOT_FLAGGED_DIAGNOSTIC_ONLY": 0,
        "SENSITIVITY_REVIEW": 1,
        "STRUCTURAL_REVIEW": 2,
    }

    mutation_count = 0

    # Apply every adverse feature independently
    # to every real observed scan-pair diagnostic.
    for row in l20["pair_screens"]:
        baseline = row["metrics"]
        before = engine(baseline)

        for key in baseline:
            modified = dict(baseline)

            if key == "duplicate_target_assignments":
                modified[key] = max(
                    1,
                    int(modified[key]) + 1,
                )
            else:
                modified[key] = max(
                    modified[key],
                    REFERENCE_THRESHOLDS[key] * 1.01,
                )

            after = engine(modified)

            assert after == shadow_evaluate(modified)

            assert severity[after["decision"]] >= (
                severity[before["decision"]]
            )

            assert set(
                after["structural_triggers"]
            ).issuperset(
                before["structural_triggers"]
            )

            assert set(
                after["sensitivity_triggers"]
            ).issuperset(
                before["sensitivity_triggers"]
            )

            # Restore original diagnostic and ensure
            # the original classification is recovered.
            assert engine(baseline) == before

            mutation_count += 1

    def expect_rejection(mutant):
        try:
            screen_consistent(
                mutant, docs, hashes, engine
            )
        except AssertionError:
            return True

        raise AssertionError(
            "Altered evidence was not rejected"
        )

    tamper_count = 0

    structural_pair = next(
        row for row in l20["pair_screens"]
        if row["steps"] == [51, 101]
    )

    assert structural_pair["screen"]["decision"] == (
        "STRUCTURAL_REVIEW"
    )

    # Tamper 1: Change only the reported decision.
    mutant = copy.deepcopy(l20)

    selected = next(
        x for x in mutant["pair_screens"]
        if x["steps"] == [51, 101]
    )

    selected["screen"]["decision"] = (
        "NOT_FLAGGED_DIAGNOSTIC_ONLY"
    )

    expect_rejection(mutant)
    tamper_count += 1

    # Tamper 2: Suppress a source-derived closure metric.
    mutant = copy.deepcopy(l20)

    selected = next(
        x for x in mutant["pair_screens"]
        if x["steps"] == [51, 101]
    )

    selected["metrics"]["closure_rotation_deg"] = 0.0

    expect_rejection(mutant)
    tamper_count += 1

    # Tamper 3: Suppress ALL adverse metrics and
    # recompute the screen so it looks internally
    # consistent. Cross-phase checks must still reject.
    mutant = copy.deepcopy(l20)

    selected = next(
        x for x in mutant["pair_screens"]
        if x["steps"] == [51, 101]
    )

    selected["metrics"] = dict(zero)
    selected["screen"] = engine(zero)

    assert selected["screen"]["decision"] == (
        "NOT_FLAGGED_DIAGNOSTIC_ONLY"
    )

    expect_rejection(mutant)
    tamper_count += 1

    # Tamper 4: Forged upstream digest.
    mutant = copy.deepcopy(l20)
    mutant["upstream_sha256"]["l19"] = "0" * 64

    expect_rejection(mutant)
    tamper_count += 1

    # Tamper 5: Unauthorized factor admission.
    mutant = copy.deepcopy(l20)
    mutant["pose_factors_authorized"] = 1

    expect_rejection(mutant)
    tamper_count += 1

    # Tamper 6: Claim unflagged means accurate.
    mutant = copy.deepcopy(l20)

    mutant[
        "not_flagged_does_not_mean_accurate"
    ] = False

    expect_rejection(mutant)
    tamper_count += 1

    scenarios = []

    for scale in (0.5, 1.0, 2.0):
        decisions = [
            engine(row["metrics"], scale)["decision"]
            for row in l20["pair_screens"]
        ]

        assert decisions == [
            shadow_evaluate(
                row["metrics"], scale
            )["decision"]
            for row in l20["pair_screens"]
        ]

        scenarios.append({
            "threshold_multiplier": scale,
            "structural_review":
                decisions.count("STRUCTURAL_REVIEW"),
            "sensitivity_review":
                decisions.count("SENSITIVITY_REVIEW"),
            "not_flagged":
                decisions.count(
                    "NOT_FLAGGED_DIAGNOSTIC_ONLY"
                ),
        })

    assert scenarios == [
        {
            "threshold_multiplier": 0.5,
            "structural_review": 3,
            "sensitivity_review": 6,
            "not_flagged": 1,
        },
        {
            "threshold_multiplier": 1.0,
            "structural_review": 3,
            "sensitivity_review": 3,
            "not_flagged": 4,
        },
        {
            "threshold_multiplier": 2.0,
            "structural_review": 3,
            "sensitivity_review": 1,
            "not_flagged": 6,
        },
    ]

    return {
        "baseline_pairs_verified": 10,

        "independent_rule_shadow_agreement": True,

        "numeric_and_duplicate_boundary_probes":
            boundary_count,

        "observed_pair_adverse_metric_mutations":
            mutation_count,

        "in_memory_evidence_tampering_rejected":
            tamper_count,

        "threshold_scenarios":
            scenarios,

        "zero_metric_probe_remains_not_flagged":
            True,

        "zero_metric_probe_is_not_scientifically_accurate":
            True,

        "cross_phase_metrics_rederived":
            True,

        "mutation_tests_do_not_establish_detection_rates":
            True,

        "unflagged_factors_admitted":
            0,
    }


def main():
    assert len(sys.argv) == 9

    paths = dict(zip(
        ("l15", "l16", "l17", "l18", "l19", "l20"),
        map(Path, sys.argv[1:7]),
    ))

    screen_source = Path(sys.argv[7])
    out = Path(sys.argv[8])

    assert out.is_dir() and not out.is_symlink()

    hashes = {}

    docs = {}

    for name, path in paths.items():
        hashes[name] = sha(path)

        assert hashes[name] == PINNED[name]

        docs[name] = load(path)

        assert docs[name]["pose_factors_authorized"] == 0

    hashes["source"] = sha(screen_source)

    assert docs["l20"]["implementation_sha256"] == (
        hashes["source"]
    )

    loaded = runpy.run_path(
        str(screen_source)
    )

    engine = loaded["evaluate"]

    assert loaded["THRESHOLDS"] == (
        REFERENCE_THRESHOLDS
    )

    first = run_challenges(
        docs, hashes, engine
    )

    second = run_challenges(
        docs, hashes, engine
    )

    assert stable(first) == stable(second)

    report = {
        "schema":
            "TRUST_ROBOT_L21_AMBIGUITY_RULE_FALSIFICATION_V1",

        "implementation_sha256":
            sha(Path(__file__)),

        "l20_rule_source_sha256":
            hashes["source"],

        "upstream_report_sha256": {
            name: hashes[name]
            for name in paths
        },

        "two_derivations_identical": True,

        "evidence_mutated_on_disk": False,

        "actual_sensor_data_mutated": False,

        "experimental_thresholds_calibrated": False,

        "scientific_reliability_established": False,

        "sensor_failure_ground_truth_available": False,

        "false_positive_rate_estimated": False,
        "false_negative_rate_estimated": False,

        "health_labels_generated": 0,
        "pose_factors_authorized": 0,

        **first,
    }

    target = (
        out / "l21_ambiguity_challenge_report_v1.json"
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

    print(
        "L21_BOUNDARY_PROBES=",
        first[
            "numeric_and_duplicate_boundary_probes"
        ],
    )

    print(
        "L21_ADVERSE_METRIC_MUTATIONS=",
        first[
            "observed_pair_adverse_metric_mutations"
        ],
    )

    print(
        "L21_TAMPER_CASES_REJECTED=",
        first[
            "in_memory_evidence_tampering_rejected"
        ],
    )

    for case in first["threshold_scenarios"]:
        print(
            "L21_THRESHOLD_SCENARIO=",
            json.dumps(case, sort_keys=True),
            flush=True,
        )

    print("L21_INDEPENDENT_RULE_COMPARISON=PASS")
    print("L21_CROSS_PHASE_EVIDENCE_VERIFICATION=PASS")
    print("L21_DETERMINISTIC_REDERIVATION=PASS")
    print("L21_OFFLINE_CHALLENGE=PASS")
    print("QUALIFIED_POSE_FACTORS=0")

    print("L21_REPORT_SHA256=", sha(target))


if __name__ == "__main__":
    main()
