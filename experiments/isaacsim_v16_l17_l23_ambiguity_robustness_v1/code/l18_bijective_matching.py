"""L18 experimental one-to-one assignment vs frozen NN ICP.

No scientifically qualified correspondence, localization,
health labels or pose-factor admission.
"""

import hashlib
import json
import math
import signal
import sys

from itertools import combinations
from pathlib import Path

import numpy as np

from scipy.optimize import linear_sum_assignment
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation

from trust_robot.lidar_frontend import (
    register_current_scan_to_previous,
    rigid_transform_kabsch,
)

STEPS = (51, 61, 71, 81, 91, 101)
MAX_ITER = 80


def sha(path):
    assert path.is_file() and not path.is_symlink()
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    sha(path)
    return json.loads(path.read_text())


def canon(obj):
    return (
        json.dumps(
            obj,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ) + "\n"
    ).encode()


def mat(pose):
    q = np.asarray(
        pose["quaternion_wxyz"],
        dtype=float,
    )

    t = np.asarray(
        pose["translation_m"],
        dtype=float,
    )

    assert q.shape == (4,)
    assert t.shape == (3,)

    assert np.isfinite(q).all()
    assert np.isfinite(t).all()

    assert abs(float(np.linalg.norm(q)) - 1) < 1e-5

    m = np.eye(4)

    m[:3, :3] = Rotation.from_quat([
        q[1], q[2], q[3], q[0]
    ]).as_matrix()

    m[:3, 3] = t

    return m


def inv(a):
    b = np.eye(4)

    b[:3, :3] = a[:3, :3].T
    b[:3, 3] = -b[:3, :3] @ a[:3, 3]

    return b


def apply(a, xyz):
    return (
        xyz @ a[:3, :3].T
        + a[:3, 3]
    )


def difference(a, b):
    d = inv(a) @ b

    return {
        "rotation_deg": float(
            np.degrees(
                Rotation.from_matrix(
                    d[:3, :3]
                ).magnitude()
            )
        ),

        "translation_m": float(
            np.linalg.norm(d[:3, 3])
        ),
    }


def nn_info(target, source, pose):
    distances, indices = cKDTree(target).query(
        apply(pose, source),
        k=1,
        workers=1,
    )

    assert np.isfinite(distances).all()

    unique = len(np.unique(indices))

    return {
        "nearest_rmse_m": float(
            np.sqrt(
                np.mean(distances ** 2)
            )
        ),

        "unique_nearest_targets": int(unique),

        "duplicate_nearest_targets":
            int(len(source) - unique),
    }


def one_to_one(previous, current, initial):
    """Alternating Hungarian assignments and frozen Kabsch.

    Enforcing a bijection does not establish that two
    LiDAR returns represent the same physical surface point.
    """

    assert previous.shape == (16, 3)
    assert current.shape == (16, 3)

    estimate = initial.copy()

    last_assignment = None
    seen = set()

    for iteration in range(1, MAX_ITER + 1):
        moved = apply(estimate, current)

        cost = np.sum(
            (
                moved[:, None, :]
                - previous[None, :, :]
            ) ** 2,
            axis=2,
        )

        assert np.isfinite(cost).all()

        rows, columns = linear_sum_assignment(cost)

        assert np.array_equal(
            rows, np.arange(16)
        )

        assert len(set(map(int, columns))) == 16

        assignment = tuple(
            int(x) for x in columns
        )

        pose = rigid_transform_kabsch(
            current,
            previous[columns],
        )

        candidate = mat(pose.to_dict())

        if last_assignment == assignment:
            residuals = np.linalg.norm(
                apply(candidate, current)
                - previous[columns],
                axis=1,
            )

            return {
                "status": "DIAGNOSTIC_AVAILABLE",
                "matrix": candidate,
                "iterations": iteration,

                "matched_rmse_m": float(
                    np.sqrt(
                        np.mean(residuals ** 2)
                    )
                ),

                "reason": None,
            }

        if assignment in seen:
            return {
                "status": "ASSIGNMENT_CYCLE",
                "matrix": None,
                "iterations": iteration,
                "matched_rmse_m": None,
                "reason": "assignment_cycle",
            }

        seen.add(assignment)

        last_assignment = assignment
        estimate = candidate

    return {
        "status": "ITERATION_LIMIT",
        "matrix": None,
        "iterations": MAX_ITER,
        "matched_rmse_m": None,
        "reason": "iteration_limit",
    }


def guarded_frozen(previous, current):
    def alarm(_signum, _frame):
        raise TimeoutError(
            "Frozen ICP time budget exceeded"
        )

    old = signal.signal(
        signal.SIGALRM, alarm
    )

    signal.setitimer(
        signal.ITIMER_REAL, 5
    )

    try:
        result = register_current_scan_to_previous(
            previous, current
        )

        return (
            mat(
                result.previous_lidar_T_current_lidar.to_dict()
            ),

            float(
                result.diagnostics
                .final_nearest_neighbor_rmse_m
            ),
        )

    finally:
        signal.setitimer(
            signal.ITIMER_REAL, 0
        )

        signal.signal(
            signal.SIGALRM, old
        )


def selftest():
    xyz = np.array([
        [
            0.2 + 0.15 * i,
            0.06 * np.sin(1.7 * i),
            0.13 * np.cos(0.9 * i) + 0.02 * i,
        ]
        for i in range(16)
    ])

    truth = np.eye(4)

    truth[:3, :3] = Rotation.from_euler(
        "xyz", [0.03, -0.05, 0.02]
    ).as_matrix()

    truth[:3, 3] = [0.08, 0.02, -0.01]

    matched = one_to_one(
        apply(truth, xyz),
        xyz,
        truth,
    )

    assert matched["status"] == "DIAGNOSTIC_AVAILABLE"

    assert difference(
        matched["matrix"], truth
    )["translation_m"] < 1e-10

    assert difference(
        matched["matrix"], truth
    )["rotation_deg"] < 1e-6

    # Deliberate duplicate-target negative control.
    duplicated = nn_info(
        np.array([
            [0., 0., 0.],
            [1., 0., 0.],
            [2., 0., 0.],
        ]),

        np.array([
            [0., 0., 0.],
            [0., 0.01, 0.],
            [0., 0.02, 0.],
        ]),

        np.eye(4),
    )

    assert duplicated[
        "duplicate_nearest_targets"
    ] == 2

    print(
        "L18_BIJECTION_AND_NEGATIVE_CONTROL=PASS",
        flush=True,
    )


def read_clouds(run, l15):
    root = run / "multimodal_probe_results_v15"

    index = load(
        root / "capture_index_v15.json"
    )

    assert [
        int(x["step"]) for x in index
    ] == list(STEPS)

    assert [
        int(x["lidar_points"]) for x in index
    ] == [16] * 6

    evidence = l15["scan_file_provenance"]

    assert [
        int(x["step"]) for x in evidence
    ] == list(STEPS)

    clouds = []

    for k, (item, recorded) in enumerate(
        zip(index, evidence),
        start=1,
    ):
        assert item["lidar_file"] == (
            f"frames_v15/lidar_{k:03d}.npy"
        )

        path = root / item["lidar_file"]

        assert sha(path) == recorded[
            "cloud_sha256"
        ]

        with path.open("rb") as stream:
            xyz = np.load(
                stream,
                allow_pickle=False,
            )

        assert xyz.shape == (16, 3)
        assert np.isfinite(xyz).all()

        raw_path = (
            run / "qualified_xyz_v1"
            / f"lidar_xyz_step_{STEPS[k-1]:03d}.npz"
        )

        assert sha(raw_path) == recorded[
            "qualified_xyz_sha256"
        ]

        with np.load(
            raw_path,
            allow_pickle=False,
        ) as raw:
            assert np.array_equal(
                raw["xyz"], xyz
            )

            assert np.all(
                (raw["flags"].astype(np.uint64) & 64) != 0
            )

        clouds.append(
            np.asarray(xyz, dtype=float)
        )

    return clouds


def derive(clouds, l15, l16, l17):
    chain = [np.eye(4)]

    for item in l15["forward"]:
        assert item["status"] == "DIAGNOSTIC_AVAILABLE"

        chain.append(
            chain[-1] @ mat(item["pose"])
        )

    old16 = {
        tuple(r["steps"]): r
        for r in l16["all_pairs"]
    }

    old17 = {
        tuple(r["steps"]): r
        for r in l17["pair_cases"]
    }

    assert len(old16) == 15
    assert len(old17) == 10

    output = []

    for i, j in combinations(range(6), 2):
        if j - i == 1:
            continue

        steps = (STEPS[i], STEPS[j])

        target = clouds[i]
        source = clouds[j]

        guess = inv(chain[i]) @ chain[j]

        identity, identity_rmse = guarded_frozen(
            target, source
        )

        correction, seeded_rmse = guarded_frozen(
            target,
            apply(guess, source),
        )

        seeded = correction @ guess

        previous16 = old16[steps]
        previous17 = old17[steps]

        assert previous16["status"] == (
            "DIAGNOSTIC_AVAILABLE"
        )

        assert math.isclose(
            identity_rmse,
            previous16["rmse_m"],
            rel_tol=1e-8,
            abs_tol=1e-10,
        )

        assert math.isclose(
            seeded_rmse,
            previous17["chain_start"]["rmse_m"],
            rel_tol=1e-8,
            abs_tol=1e-10,
        )

        for actual, reference in (
            (
                identity,
                previous17["identity_start"],
            ),
            (
                seeded,
                previous17["chain_start"],
            ),
        ):
            topology = nn_info(
                target, source, actual
            )

            assert math.isclose(
                topology["nearest_rmse_m"],
                reference["rmse_m"],
                rel_tol=1e-8,
                abs_tol=1e-10,
            )

            assert topology[
                "duplicate_nearest_targets"
            ] == reference[
                "nearest_neighbor_topology"
            ]["duplicate_target_assignments"]

        tests = {}

        for label, initial in (
            ("identity", np.eye(4)),
            ("chain", guess),
        ):
            experimental = one_to_one(
                target,
                source,
                initial,
            )

            estimated = experimental["matrix"]

            tests[label] = {
                "status": experimental["status"],
                "iterations": experimental["iterations"],

                "assignment_rmse_m":
                    experimental["matched_rmse_m"],

                "nearest_neighbor": (
                    nn_info(
                        target, source, estimated
                    )
                    if estimated is not None
                    else None
                ),

                "difference_from_chain": (
                    difference(
                        estimated, guess
                    )
                    if estimated is not None
                    else None
                ),

                "difference_from_frozen_identity": (
                    difference(
                        estimated, identity
                    )
                    if estimated is not None
                    else None
                ),

                "physical_correspondence_verified":
                    False,

                "factor_authorized": False,
            }

        output.append({
            "steps": list(steps),
            "hop_count": j - i,

            "frozen_identity": {
                "nearest_neighbor":
                    nn_info(target, source, identity),

                "difference_from_chain":
                    difference(identity, guess),
            },

            "frozen_chain_seeded": {
                "nearest_neighbor":
                    nn_info(target, source, seeded),

                "difference_from_chain":
                    difference(seeded, guess),
            },

            "experimental_one_to_one": tests,
            "pose_factor_authorized": False,
        })

    assert len(output) == 10

    summaries = []

    for hop in range(2, 6):
        cases = [
            c for c in output
            if c["hop_count"] == hop
        ]

        successes = [
            c for c in cases
            if all(
                t["status"] == "DIAGNOSTIC_AVAILABLE"
                for t in c["experimental_one_to_one"].values()
            )
        ]

        improved = sum(
            c["experimental_one_to_one"]["identity"][
                "nearest_neighbor"
            ] is not None
            and c["experimental_one_to_one"]["identity"][
                "nearest_neighbor"
            ]["nearest_rmse_m"]
            < c["frozen_identity"][
                "nearest_neighbor"
            ]["nearest_rmse_m"] - 1e-10
            for c in cases
        )

        summaries.append({
            "hop_count": hop,
            "attempted_pairs": len(cases),

            "both_bijective_variants_available":
                len(successes),

            "identity_frozen_duplication_pairs":
                sum(
                    c["frozen_identity"][
                        "nearest_neighbor"
                    ]["duplicate_nearest_targets"] > 0
                    for c in cases
                ),

            "chain_seeded_frozen_duplication_pairs":
                sum(
                    c["frozen_chain_seeded"][
                        "nearest_neighbor"
                    ]["duplicate_nearest_targets"] > 0
                    for c in cases
                ),

            "one_to_one_better_nearest_rmse_than_frozen_identity":
                improved,
        })

    return {
        "pair_cases": output,
        "hop_summary": summaries,
    }


def main():
    assert len(sys.argv) == 6

    run, l15path, l16path, l17path, out = map(
        Path, sys.argv[1:]
    )

    assert run.is_dir() and not run.is_symlink()
    assert out.is_dir() and not out.is_symlink()

    l15, l16, l17 = map(
        load,
        (l15path, l16path, l17path),
    )

    assert l16["l15_report_sha256"] == sha(l15path)

    assert l17["upstream_l16_sha256"] == sha(l16path)
    assert l17["upstream_l15_sha256"] == sha(l15path)

    assert (
        l15["pose_factors_authorized"]
        == l16["pose_factors_authorized"]
        == l17["pose_factors_authorized"]
        == 0
    )

    assert l17["two_derivations_identical"] is True

    selftest()

    clouds = read_clouds(run, l15)

    first = derive(clouds, l15, l16, l17)
    second = derive(clouds, l15, l16, l17)

    assert canon(first) == canon(second)

    report = {
        "schema":
            "TRUST_ROBOT_L18_EXPERIMENTAL_BIJECTIVE_CORRESPONDENCE_COMPARISON_V1",

        "implementation_sha256":
            sha(Path(__file__)),

        "upstream_l15_sha256": sha(l15path),
        "upstream_l16_sha256": sha(l16path),
        "upstream_l17_sha256": sha(l17path),

        "nonadjacent_pairs": 10,

        "one_to_one_trials_per_derivation": 20,
        "frozen_control_registrations_per_derivation": 20,

        "two_derivations_identical": True,

        "one_to_one_assignment_is_not_verified_feature_correspondence":
            True,

        "short_chain_is_not_independent_ground_truth":
            True,

        "experimental_algorithm_not_admitted_to_frontend":
            True,

        "independent_ground_truth_verified": False,
        "cross_sensor_synchronization_verified": False,
        "scientific_ate_rpe_computed": False,

        "health_labels_generated": 0,
        "pose_factors_authorized": 0,

        **first,
    }

    destination = (
        out / "l18_bijective_correspondence_diagnostic_v1.json"
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

    for case in first["pair_cases"]:
        identity = case["experimental_one_to_one"]["identity"]
        chain = case["experimental_one_to_one"]["chain"]

        print(
            "L18_PAIR=",
            json.dumps({
                "steps": case["steps"],
                "hops": case["hop_count"],

                "frozen_identity_nn_rmse_m":
                    case["frozen_identity"][
                        "nearest_neighbor"
                    ]["nearest_rmse_m"],

                "frozen_identity_duplicate_targets":
                    case["frozen_identity"][
                        "nearest_neighbor"
                    ]["duplicate_nearest_targets"],

                "frozen_identity_from_chain_rotation_deg":
                    case["frozen_identity"][
                        "difference_from_chain"
                    ]["rotation_deg"],

                "bijective_identity_status":
                    identity["status"],

                "bijective_identity_nn_rmse_m":
                    (
                        identity["nearest_neighbor"] or {}
                    ).get("nearest_rmse_m"),

                "bijective_identity_from_chain_rotation_deg":
                    (
                        identity["difference_from_chain"] or {}
                    ).get("rotation_deg"),

                "bijective_chain_status":
                    chain["status"],

                "bijective_chain_nn_rmse_m":
                    (
                        chain["nearest_neighbor"] or {}
                    ).get("nearest_rmse_m"),

                "bijective_chain_from_chain_rotation_deg":
                    (
                        chain["difference_from_chain"] or {}
                    ).get("rotation_deg"),
            }, sort_keys=True),
            flush=True,
        )

    for summary in first["hop_summary"]:
        print(
            "L18_HOP_SUMMARY=",
            json.dumps(
                summary,
                sort_keys=True,
            ),
            flush=True,
        )

    print("L18_FROZEN_AND_BIJECTIVE_COMPARISON=PASS")
    print("L18_REPORT_SHA256=", sha(destination))
    print("QUALIFIED_POSE_FACTORS=0")
    print(
        "NEXT=REVIEW_L18_CORRESPONDENCE_AMBIGUITY_AND_DECIDE_L19"
    )


if __name__ == "__main__":
    main()
