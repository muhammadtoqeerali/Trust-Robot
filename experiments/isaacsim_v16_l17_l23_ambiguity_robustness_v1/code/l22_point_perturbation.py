"""L22: actual deterministic point-coordinate perturbation challenge.

Recompute frozen ICP, chain closure, seven seeded solutions,
bijection objective, and inferred beam leave-one-out sensitivity.

All perturbations are analytic engineering challenges, NOT
calibrated sensor noise. The short-scan chain is not ground truth.
No scientific pose factors or health labels are authorized.
"""

import hashlib
import json
import math
import runpy
import sys

from itertools import combinations
from pathlib import Path

import numpy as np

STEPS = (51, 61, 71, 81, 91, 101)

AMPLITUDES = (0.0005, 0.002)
PATTERNS = (1, 4, 7)

METRIC_KEYS = (
    "duplicate_target_assignments",
    "closure_rotation_deg",
    "closure_translation_m",
    "seed_spread_rotation_deg",
    "seed_spread_translation_m",
    "jackknife_rotation_deg",
    "jackknife_translation_m",
    "bijective_nn_cost_penalty_m",
)

DECISIONS = (
    "NOT_FLAGGED_DIAGNOSTIC_ONLY",
    "SENSITIVITY_REVIEW",
    "STRUCTURAL_REVIEW",
)


def sha(path):
    assert path.is_file() and not path.is_symlink(), path

    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def load(path):
    sha(path)
    return json.loads(path.read_text())


def canonical(value):
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ) + "\n"
    ).encode()


def load_scans(run, l15, l19):
    root = run / "multimodal_probe_results_v15"

    index = load(root / "capture_index_v15.json")

    provenance = l15["scan_file_provenance"]
    mappings = l19["raw_beam_mapping"]

    assert len(index) == len(provenance) == len(mappings) == 6

    scans = []
    orders = []
    hashes = []

    for k, (row, proof, mapping) in enumerate(
        zip(index, provenance, mappings),
        start=1,
    ):
        step = STEPS[k - 1]

        assert row["step"] == step
        assert row["lidar_points"] == 16
        assert proof["step"] == step
        assert mapping["step"] == step

        relative = f"frames_v15/lidar_{k:03d}.npy"

        assert row["lidar_file"] == relative

        path = root / relative

        cloud_sha = sha(path)

        assert cloud_sha == proof["cloud_sha256"]

        with path.open("rb") as stream:
            cloud = np.load(
                stream,
                allow_pickle=False,
            )

        assert cloud.shape == (16, 3)
        assert np.isfinite(cloud).all()

        rawpath = (
            run / "qualified_xyz_v1"
            / f"lidar_xyz_step_{step:03d}.npz"
        )

        rawsha = sha(rawpath)

        assert rawsha == proof["qualified_xyz_sha256"]

        with np.load(
            rawpath,
            allow_pickle=False,
        ) as raw:
            assert np.array_equal(
                raw["xyz"], cloud
            )

            flags = raw["flags"].astype(np.uint64)
            assert np.all((flags & 64) != 0)

            assert int(raw["frame_id"][0]) == (
                proof["gmo_frame_id"]
            )

            assert int(raw["timestamp_ns"][0]) == (
                proof["gmo_timestamp_ns_unqualified"]
            )

        ids = mapping[
            "inferred_emitter_indices_in_gmo_order"
        ]

        assert sorted(ids) == list(range(16))

        order = np.argsort(
            np.asarray(ids, dtype=int)
        )

        assert np.array_equal(
            np.asarray(ids)[order],
            np.arange(16),
        )

        assert mapping["all_configured_indices_present"] is True
        assert mapping["physical_emitter_identity_verified"] is False

        scans.append(cloud.copy())
        orders.append(order)

        hashes.append({
            "step": step,
            "cloud_sha256": cloud_sha,
            "qualified_xyz_sha256": rawsha,
        })

    return scans, orders, hashes


def make_perturbation(scan, amplitude, pattern_id, k):
    """Deterministic, centered coordinate perturbation."""

    i = np.arange(
        1, len(scan) + 1,
        dtype=float,
    )[:, None]

    axis = np.arange(
        1, 4,
        dtype=float,
    )[None, :]

    phase = (
        pattern_id * 0.37
        + (k + 1) * 0.23
    )

    noise = (
        np.sin(
            (i + phase)
            * (axis + 0.31)
            * (pattern_id + 1)
            * 0.43
        )
        +
        0.6 * np.cos(
            (i * 0.41 + phase)
            * (axis + k + 1)
            * 0.67
        )
    )

    noise -= noise.mean(
        axis=0,
        keepdims=True,
    )

    scale = float(np.max(np.abs(noise)))

    assert scale > 0

    delta = amplitude * noise / scale

    assert delta.shape == (16, 3)
    assert np.max(np.abs(delta)) <= amplitude + 1e-12

    assert np.allclose(
        delta.mean(axis=0),
        0,
        atol=1e-14,
    )

    assert not np.all(delta == 0)

    return np.asarray(
        scan,
        dtype=np.float64,
    ) + delta


def challenge_scans(original, amplitude, pattern_id):
    result = [
        make_perturbation(
            scan,
            amplitude,
            pattern_id,
            k,
        )
        for k, scan in enumerate(original)
    ]

    digest = hashlib.sha256()

    for cloud in result:
        assert cloud.shape == (16, 3)
        assert np.isfinite(cloud).all()

        digest.update(
            np.ascontiguousarray(
                cloud,
                dtype=np.float64,
            ).tobytes()
        )

    return result, digest.hexdigest()


def create_chain(scans, api):
    chain = [np.eye(4)]

    for i in range(5):
        pose, rmse, _, error = api["register"](
            scans[i],
            scans[i + 1],
        )

        if pose is None:
            return None, {
                "pair": [STEPS[i], STEPS[i+1]],
                "error": error,
            }

        assert rmse is not None
        assert math.isfinite(rmse)

        chain.append(
            chain[-1] @ pose
        )

    return chain, None


def recompute(scans, orders, api17, api18, api19, api20):
    """Recompute every L20 metric from the supplied point clouds."""

    chain, chain_error = create_chain(
        scans,
        api17,
    )

    pairs = []

    for i, j in combinations(range(6), 2):
        if j - i == 1:
            continue

        pair = [STEPS[i], STEPS[j]]

        if chain is None:
            pairs.append({
                "steps": pair,
                "status": "NOT_EVALUABLE",
                "reason": "ADJACENT_CHAIN_UNAVAILABLE",
                "metrics": None,
                "screen": None,
            })
            continue

        target = scans[i]
        source = scans[j]

        short_chain = (
            api17["inverse"](chain[i])
            @ chain[j]
        )

        direct, direct_rmse, _, direct_error = (
            api17["register"](target, source)
        )

        if direct is None:
            pairs.append({
                "steps": pair,
                "status": "NOT_EVALUABLE",
                "reason": "DIRECT_ICP_" + str(direct_error),
                "metrics": None,
                "screen": None,
            })
            continue

        topology = api17["topology"](
            target,
            source,
            direct,
        )

        assert math.isclose(
            topology["rmse_m"],
            direct_rmse,
            rel_tol=1e-8,
            abs_tol=1e-9,
        )

        closure = api17["discrepancy"](
            direct,
            short_chain,
        )

        solutions = []
        failed_seeds = []

        for name, tx, ty, yaw in api17["SEEDS"]:
            guess = (
                api17["offset"](tx, ty, yaw)
                @ short_chain
            )

            aligned = api17["transform"](
                guess,
                source,
            )

            correction, _, _, err = (
                api17["register"](
                    target,
                    aligned,
                )
            )

            if correction is None:
                failed_seeds.append({
                    "name": name,
                    "error": err,
                })
            else:
                solutions.append(
                    correction @ guess
                )

        if len(solutions) != 7:
            pairs.append({
                "steps": pair,
                "status": "NOT_EVALUABLE",
                "reason": "SEED_REGISTRATION_UNAVAILABLE",
                "failed_seeds": failed_seeds,
                "metrics": None,
                "screen": None,
            })
            continue

        spread = [
            api17["discrepancy"](a, b)
            for a, b in combinations(
                solutions,
                2,
            )
        ]

        # Recompute the L18 alternative objective.
        alternative = api18["one_to_one"](
            target,
            source,
            np.eye(4),
        )

        if alternative["matrix"] is None:
            pairs.append({
                "steps": pair,
                "status": "NOT_EVALUABLE",
                "reason": (
                    "BIJECTIVE_" + alternative["status"]
                ),
                "metrics": None,
                "screen": None,
            })
            continue

        alt_topology = api17["topology"](
            target,
            source,
            alternative["matrix"],
        )

        # Recompute L19 same-inferred-emitter
        # fit and 16 leave-one-out solutions.
        target_by_emitter = np.asarray(
            target[orders[i]],
            dtype=np.float64,
        )

        source_by_emitter = np.asarray(
            source[orders[j]],
            dtype=np.float64,
        )

        reference_pose, _ = api19["fit"](
            source_by_emitter,
            target_by_emitter,
        )

        jackknife = []

        for omitted in range(16):
            keep = np.arange(16) != omitted

            reduced, _ = api19["fit"](
                source_by_emitter[keep],
                target_by_emitter[keep],
            )

            jackknife.append(
                api17["discrepancy"](
                    reference_pose,
                    reduced,
                )
            )

        metric = {
            "duplicate_target_assignments":
                int(
                    topology[
                        "duplicate_target_assignments"
                    ]
                ),

            "closure_rotation_deg":
                float(closure["rotation_deg"]),

            "closure_translation_m":
                float(closure["translation_m"]),

            "seed_spread_rotation_deg":
                float(max(
                    x["rotation_deg"]
                    for x in spread
                )),

            "seed_spread_translation_m":
                float(max(
                    x["translation_m"]
                    for x in spread
                )),

            "jackknife_rotation_deg":
                float(max(
                    x["rotation_deg"]
                    for x in jackknife
                )),

            "jackknife_translation_m":
                float(max(
                    x["translation_m"]
                    for x in jackknife
                )),

            "bijective_nn_cost_penalty_m":
                float(
                    alt_topology["rmse_m"]
                    - direct_rmse
                ),
        }

        assert set(metric) == set(METRIC_KEYS)

        assert all(
            math.isfinite(value)
            for value in metric.values()
        )

        pairs.append({
            "steps": pair,

            "status": "DIAGNOSTIC_RECOMPUTED",
            "reason": None,

            "metrics": metric,
            "screen": api20["evaluate"](metric),

            "pose_factor_authorized": False,
        })

    assert len(pairs) == 10

    return pairs, chain_error


def compare_baseline(actual, expected):
    assert len(actual) == len(expected) == 10

    for row, reference in zip(actual, expected):
        assert row["steps"] == reference["steps"]

        assert row["status"] == "DIAGNOSTIC_RECOMPUTED"

        for key in METRIC_KEYS:
            a = row["metrics"][key]
            b = reference["metrics"][key]

            if key == "duplicate_target_assignments":
                assert a == b
            else:
                assert math.isclose(
                    a, b,
                    rel_tol=1e-5,
                    abs_tol=1e-6,
                ), (
                    row["steps"], key, a, b
                )

        assert row["screen"] == reference["screen"]

    print(
        "L22_UNPERTURBED_L20_REPRODUCTION=PASS",
        flush=True,
    )


def derive(original, orders, l20, api17, api18, api19, api20):
    baseline, failure = recompute(
        original,
        orders,
        api17,
        api18,
        api19,
        api20,
    )

    assert failure is None

    compare_baseline(
        baseline,
        l20["pair_screens"],
    )

    baseline_by_pair = {
        tuple(row["steps"]): row
        for row in baseline
    }

    scenarios = []
    all_trials = []

    for amplitude in AMPLITUDES:
        for pattern_id in PATTERNS:
            modified, digest = challenge_scans(
                original,
                amplitude,
                pattern_id,
            )

            current, chain_failure = recompute(
                modified,
                orders,
                api17,
                api18,
                api19,
                api20,
            )

            assert len(current) == 10

            scenario_trials = []

            for row in current:
                prior = baseline_by_pair[
                    tuple(row["steps"])
                ]

                available = (
                    row["status"] ==
                    "DIAGNOSTIC_RECOMPUTED"
                )

                trial = {
                    "amplitude_m": amplitude,
                    "pattern_id": pattern_id,
                    "steps": row["steps"],

                    "status": row["status"],
                    "reason": row["reason"],

                    "baseline_decision":
                        prior["screen"]["decision"],

                    "perturbed_decision": (
                        row["screen"]["decision"]
                        if available else
                        "NOT_EVALUABLE"
                    ),

                    "perturbed_metrics": (
                        row["metrics"]
                        if available else None
                    ),

                    "metric_delta": (
                        {
                            key:
                                row["metrics"][key]
                                - prior["metrics"][key]
                            for key in METRIC_KEYS
                        }
                        if available else None
                    ),

                    "pose_factor_authorized": False,
                }

                scenario_trials.append(trial)
                all_trials.append(trial)

            available_trials = [
                row
                for row in scenario_trials
                if row["status"] ==
                "DIAGNOSTIC_RECOMPUTED"
            ]

            scenarios.append({
                "amplitude_m": amplitude,
                "pattern_id": pattern_id,

                "perturbed_cloud_bytes_sha256": digest,

                "chain_failure": chain_failure,

                "registration_screens_recomputed":
                    len(available_trials),

                "not_evaluable":
                    10 - len(available_trials),

                "decision_changed":
                    sum(
                        row["baseline_decision"]
                        != row["perturbed_decision"]
                        for row in available_trials
                    ),

                "previously_unflagged_now_flagged":
                    sum(
                        row["baseline_decision"] ==
                        "NOT_FLAGGED_DIAGNOSTIC_ONLY"
                        and row["perturbed_decision"] !=
                        "NOT_FLAGGED_DIAGNOSTIC_ONLY"
                        for row in available_trials
                    ),

                "previously_structural_no_longer_structural":
                    sum(
                        row["baseline_decision"] ==
                        "STRUCTURAL_REVIEW"
                        and row["perturbed_decision"] !=
                        "STRUCTURAL_REVIEW"
                        for row in available_trials
                    ),
            })

    assert len(scenarios) == 6
    assert len(all_trials) == 60

    transitions = {}

    for row in all_trials:
        key = (
            row["baseline_decision"]
            + " -> "
            + row["perturbed_decision"]
        )

        transitions[key] = transitions.get(key, 0) + 1

    assert sum(transitions.values()) == 60

    return {
        "unperturbed_baseline_reproduced":
            True,

        "scenarios": scenarios,
        "perturbation_trials": all_trials,
        "decision_transitions": transitions,

        "total_trials": 60,

        "fully_recomputed":
            sum(
                row["status"] ==
                "DIAGNOSTIC_RECOMPUTED"
                for row in all_trials
            ),

        "not_evaluable":
            sum(
                row["status"] ==
                "NOT_EVALUABLE"
                for row in all_trials
            ),
    }


def main():
    assert len(sys.argv) == 14

    paths = list(
        map(Path, sys.argv[1:])
    )

    (
        run, p15, p16, p17, p18,
        p19, p20, p21,
        s17, s18, s19, s20,
    ) = paths[:12]

    out = paths[12]

    assert out.is_dir() and not out.is_symlink()

    l15, l16, l17, l18, l19, l20, l21 = [
        load(path)
        for path in (
            p15, p16, p17, p18,
            p19, p20, p21
        )
    ]

    assert l16["l15_report_sha256"] == sha(p15)
    assert l17["upstream_l16_sha256"] == sha(p16)
    assert l18["upstream_l17_sha256"] == sha(p17)
    assert l19["l18_report_sha256"] == sha(p18)
    assert l20["upstream_sha256"]["l19"] == sha(p19)
    assert l21["upstream_report_sha256"]["l20"] == sha(p20)

    assert l21["two_derivations_identical"] is True

    for evidence in (
        l15, l16, l17, l18,
        l19, l20, l21
    ):
        assert evidence["pose_factors_authorized"] == 0

    for report, source in (
        (l17, s17),
        (l18, s18),
        (l19, s19),
        (l20, s20),
    ):
        assert report["implementation_sha256"] == sha(source)

    api17 = runpy.run_path(str(s17))
    api18 = runpy.run_path(str(s18))
    api19 = runpy.run_path(str(s19))
    api20 = runpy.run_path(str(s20))

    assert len(api17["SEEDS"]) == 7

    original, orders, provenance = load_scans(
        run,
        l15,
        l19,
    )

    first = derive(
        original, orders, l20,
        api17, api18, api19, api20,
    )

    second = derive(
        original, orders, l20,
        api17, api18, api19, api20,
    )

    assert canonical(first) == canonical(second)

    report = {
        "schema":
            "TRUST_ROBOT_L22_REAL_CLOUD_COORDINATE_PERTURBATION_AUDIT_V1",

        "implementation_sha256":
            sha(Path(__file__)),

        "upstream_report_sha256": {
            "l15": sha(p15),
            "l16": sha(p16),
            "l17": sha(p17),
            "l18": sha(p18),
            "l19": sha(p19),
            "l20": sha(p20),
            "l21": sha(p21),
        },

        "reused_implementation_sha256": {
            "l17": sha(s17),
            "l18": sha(s18),
            "l19": sha(s19),
            "l20": sha(s20),
        },

        "source_cloud_provenance":
            provenance,

        "perturbation_amplitudes_m":
            list(AMPLITUDES),

        "perturbation_pattern_ids":
            list(PATTERNS),

        "all_six_scans_perturbed_per_scenario":
            True,

        "frozen_icp_unchanged":
            True,

        "all_eight_l20_metrics_recomputed":
            True,

        "two_derivations_identical":
            True,

        "perturbations_are_calibrated_noise":
            False,

        "screen_thresholds_scientifically_calibrated":
            False,

        "independent_ground_truth_verified":
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
        out / "l22_point_perturbation_ambiguity_report_v1.json"
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

    for row in first["scenarios"]:
        print(
            "L22_SCENARIO=",
            json.dumps(
                row,
                sort_keys=True,
            ),
            flush=True,
        )

    print(
        "L22_DECISION_TRANSITIONS=",
        json.dumps(
            first["decision_transitions"],
            sort_keys=True,
        ),
        flush=True,
    )

    print(
        "L22_FULLY_RECOMPUTED=",
        first["fully_recomputed"],
    )

    print(
        "L22_NOT_EVALUABLE=",
        first["not_evaluable"],
    )

    print("L22_REDERIVATION=PASS")
    print("L22_OFFLINE_POINT_CHALLENGE=PASS")
    print("QUALIFIED_POSE_FACTORS=0")

    print(
        "L22_REPORT_SHA256=",
        sha(destination),
    )


if __name__ == "__main__":
    main()
