"""L17: frozen identity ICP vs deterministic chain-seeded ICP diagnostics.

Chain seeding is not independent reference evidence or a qualified pose factor.
"""

import hashlib
import json
import math
import signal
import statistics
import sys

from itertools import combinations
from pathlib import Path

import numpy as np

from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation

from trust_robot.lidar_frontend import (
    LidarFrontendError,
    register_current_scan_to_previous,
)

from trust_robot.diagnostics import (
    DiagnosticFeatureError,
    extract_lidar_registration_diagnostics,
)

STEPS = [51, 61, 71, 81, 91, 101]

FEATURES = (
    "source_point_count",
    "target_point_count",
    "fixed_point_iterations",
    "final_correspondence_count",
    "final_nearest_neighbor_rmse_m",
)

# Prespecified engineering seeds, not calibrated noise.
# The chain is derived from the same recorded scans.

SEEDS = (
    ("chain", 0.0, 0.0, 0.0),
    ("tx_plus_10mm", .01, 0.0, 0.0),
    ("tx_minus_10mm", -.01, 0.0, 0.0),
    ("ty_plus_10mm", 0.0, .01, 0.0),
    ("ty_minus_10mm", 0.0, -.01, 0.0),
    ("yaw_plus_2deg", 0.0, 0.0, 2.0),
    ("yaw_minus_2deg", 0.0, 0.0, -2.0),
)


def sha(path):
    assert path.is_file() and not path.is_symlink(), str(path)
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def matrix(pose):
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


def inverse(m):
    n = np.eye(4)

    n[:3, :3] = m[:3, :3].T
    n[:3, 3] = -n[:3, :3] @ m[:3, 3]

    return n


def transform(m, xyz):
    return (
        xyz @ m[:3, :3].T
        + m[:3, 3]
    )


def discrepancy(a, b):
    delta = inverse(a) @ b

    return {
        "translation_m": float(
            np.linalg.norm(delta[:3, 3])
        ),

        "rotation_deg": float(
            np.degrees(
                Rotation.from_matrix(
                    delta[:3, :3]
                ).magnitude()
            )
        ),
    }


def selftest():
    t = np.eye(4)

    t[:3, :3] = Rotation.from_euler(
        "xyz",
        [.04, -.02, .03],
    ).as_matrix()

    t[:3, 3] = [.11, -.05, .07]

    assert discrepancy(t, t)["translation_m"] < 1e-12
    assert discrepancy(t, t)["rotation_deg"] < 1e-8

    points = np.array([
        [.2, .1, .7],
        [.4, .3, .2],
        [1., .7, .1],
        [.9, .2, .8],
    ])

    assert np.allclose(
        transform(
            inverse(t),
            transform(t, points),
        ),
        points,
        atol=1e-12,
    )

    altered = t.copy()
    altered[0, 3] += .025

    assert math.isclose(
        discrepancy(t, altered)["translation_m"],
        .025,
        abs_tol=1e-12,
    )

    print(
        "L17_SE3_AND_NEGATIVE_CONTROL=PASS",
        flush=True,
    )


def register(previous, current):
    def alarm(_signum, _frame):
        raise TimeoutError(
            "Frozen ICP time budget exceeded"
        )

    old = signal.signal(
        signal.SIGALRM,
        alarm,
    )

    signal.setitimer(
        signal.ITIMER_REAL,
        5.0,
    )

    try:
        result = register_current_scan_to_previous(
            previous,
            current,
        )

        diag = extract_lidar_registration_diagnostics(
            result.diagnostics
        )

        features = {
            f.name: f.value
            for f in diag.features
        }

        assert tuple(features) == FEATURES

        return (
            matrix(
                result.previous_lidar_T_current_lidar.to_dict()
            ),

            float(
                features[
                    "final_nearest_neighbor_rmse_m"
                ]
            ),

            int(
                features[
                    "fixed_point_iterations"
                ]
            ),

            None,
        )

    except (
        LidarFrontendError,
        DiagnosticFeatureError,
        TimeoutError,
        np.linalg.LinAlgError,
    ) as exc:
        return (
            None,
            None,
            None,
            type(exc).__name__,
        )

    finally:
        signal.setitimer(
            signal.ITIMER_REAL,
            0,
        )

        signal.signal(
            signal.SIGALRM,
            old,
        )


def offset(tx, ty, yaw_deg):
    m = np.eye(4)

    m[:3, :3] = Rotation.from_euler(
        "z",
        yaw_deg,
        degrees=True,
    ).as_matrix()

    m[:3, 3] = [tx, ty, 0]

    return m


def cloud_inputs(run, l15):
    root = (
        run / "multimodal_probe_results_v15"
    )

    index = load(
        root / "capture_index_v15.json"
    )

    assert [
        int(x["step"]) for x in index
    ] == STEPS

    assert [
        int(x["lidar_points"]) for x in index
    ] == [16] * 6

    provenance = l15["scan_file_provenance"]

    assert [
        x["step"] for x in provenance
    ] == STEPS

    clouds = []

    for k, (item, proof) in enumerate(
        zip(index, provenance),
        start=1,
    ):
        step = STEPS[k - 1]

        assert item["lidar_file"] == (
            f"frames_v15/lidar_{k:03d}.npy"
        )

        path = root / item["lidar_file"]

        assert sha(path) == proof["cloud_sha256"]

        with path.open("rb") as stream:
            xyz = np.load(
                stream,
                allow_pickle=False,
            )

        assert xyz.shape == (16, 3)
        assert np.isfinite(xyz).all()

        raw_path = (
            run / "qualified_xyz_v1"
            / f"lidar_xyz_step_{step:03d}.npz"
        )

        assert sha(raw_path) == (
            proof["qualified_xyz_sha256"]
        )

        with np.load(
            raw_path,
            allow_pickle=False,
        ) as raw:
            assert np.array_equal(
                raw["xyz"],
                xyz,
            )

            flags = raw["flags"].astype(
                np.uint64
            )

            assert np.all(
                (flags & 64) != 0
            )

        clouds.append(xyz.copy())

    return clouds


def topology(target, source, pose):
    distances, indices = (
        cKDTree(target).query(
            transform(pose, source),
            k=1,
            workers=1,
        )
    )

    assert np.isfinite(distances).all()

    unique_count = len(np.unique(indices))

    return {
        "unique_target_nearest_neighbors":
            unique_count,

        "duplicate_target_assignments":
            len(source) - unique_count,

        "rmse_m": float(
            np.sqrt(
                np.mean(
                    distances * distances
                )
            )
        ),
    }


def derive(clouds, l15, l16):
    chain = [np.eye(4)]

    for row in l15["forward"]:
        assert row["status"] == (
            "DIAGNOSTIC_AVAILABLE"
        )

        chain.append(
            chain[-1]
            @ matrix(row["pose"])
        )

    source_by_pair = {
        tuple(row["steps"]): row
        for row in l16["all_pairs"]
    }

    assert len(source_by_pair) == 15

    cases = []

    for i, j in combinations(range(6), 2):
        if j - i == 1:
            continue

        target = clouds[i]
        source = clouds[j]

        reference = source_by_pair[
            (STEPS[i], STEPS[j])
        ]

        short_chain = (
            inverse(chain[i]) @ chain[j]
        )

        baseline, baseline_rmse, baseline_iter, baseline_error = (
            register(target, source)
        )

        assert baseline is not None
        assert baseline_error is None

        assert reference["status"] == (
            "DIAGNOSTIC_AVAILABLE"
        )

        assert math.isclose(
            baseline_rmse,
            reference["rmse_m"],
            rel_tol=1e-8,
            abs_tol=1e-10,
        )

        baseline_closure = discrepancy(
            baseline,
            short_chain,
        )

        for key in (
            "translation_m",
            "rotation_deg",
        ):
            assert math.isclose(
                baseline_closure[key],
                reference[
                    "direct_vs_composed_se3"
                ][key],
                rel_tol=1e-6,
                abs_tol=1e-7,
            )

        baseline_topology = topology(
            target,
            source,
            baseline,
        )

        assert math.isclose(
            baseline_topology["rmse_m"],
            baseline_rmse,
            rel_tol=1e-8,
            abs_tol=1e-10,
        )

        tests = []
        solved = []

        for name, tx, ty, yaw in SEEDS:
            guess = (
                offset(tx, ty, yaw)
                @ short_chain
            )

            aligned = transform(
                guess,
                source,
            )

            correction, rmse, iterations, err = (
                register(target, aligned)
            )

            solution = (
                correction @ guess
                if correction is not None
                else None
            )

            details = (
                topology(
                    target,
                    source,
                    solution,
                )
                if solution is not None
                else None
            )

            if details is not None:
                assert math.isclose(
                    details["rmse_m"],
                    rmse,
                    rel_tol=1e-8,
                    abs_tol=1e-10,
                )

                solved.append(solution)

            tests.append({
                "seed": name,

                "status": (
                    "DIAGNOSTIC_AVAILABLE"
                    if solution is not None
                    else "REGISTRATION_UNAVAILABLE"
                ),

                "error_type": err,
                "icp_iterations": iterations,
                "rmse_m": rmse,

                "difference_from_short_chain": (
                    discrepancy(
                        solution,
                        short_chain,
                    )
                    if solution is not None
                    else None
                ),

                "difference_from_identity_start": (
                    discrepancy(
                        solution,
                        baseline,
                    )
                    if solution is not None
                    else None
                ),

                "nearest_neighbor_topology": details,

                "factor_authorized": False,
            })

        pairwise = [
            discrepancy(a, b)
            for a, b in combinations(
                solved,
                2,
            )
        ]

        spread = {
            "available": len(solved),

            "max_pairwise_translation_m": (
                max(
                    x["translation_m"]
                    for x in pairwise
                )
                if pairwise else (
                    0.0 if solved else None
                )
            ),

            "max_pairwise_rotation_deg": (
                max(
                    x["rotation_deg"]
                    for x in pairwise
                )
                if pairwise else (
                    0.0 if solved else None
                )
            ),
        }

        center = tests[0]

        cases.append({
            "steps": [
                STEPS[i],
                STEPS[j],
            ],

            "hops": j - i,

            "identity_start": {
                "rmse_m": baseline_rmse,

                "icp_iterations":
                    baseline_iter,

                "difference_from_short_chain":
                    baseline_closure,

                "nearest_neighbor_topology":
                    baseline_topology,
            },

            "chain_start": center,

            "fixed_offset_starts":
                tests[1:],

            "seed_solution_spread":
                spread,

            "chain_start_has_lower_rmse_than_identity": (
                center["rmse_m"] < baseline_rmse
                if center["rmse_m"] is not None
                else None
            ),

            "no_independent_pose_accuracy_or_factor_admission":
                True,
        })

    assert len(cases) == 10

    hop_summary = []

    for hop in range(2, 6):
        rows = [
            x for x in cases
            if x["hops"] == hop
        ]

        available = [
            x for x in rows
            if x["chain_start"]["rmse_m"] is not None
        ]

        hop_summary.append({
            "hops": hop,
            "attempts": len(rows),

            "chain_start_available":
                len(available),

            "chain_start_lower_rmse_count":
                sum(
                    x[
                        "chain_start_has_lower_rmse_than_identity"
                    ] is True
                    for x in rows
                ),

            "identity_median_rotation_from_chain_deg":
                float(statistics.median(
                    x["identity_start"][
                        "difference_from_short_chain"
                    ]["rotation_deg"]
                    for x in rows
                )),

            "chain_start_median_rotation_from_chain_deg":
                (
                    float(statistics.median(
                        x["chain_start"][
                            "difference_from_short_chain"
                        ]["rotation_deg"]
                        for x in available
                    ))
                    if available else None
                ),

            "identity_median_rmse_m":
                float(statistics.median(
                    x["identity_start"]["rmse_m"]
                    for x in rows
                )),

            "chain_start_median_rmse_m":
                (
                    float(statistics.median(
                        x["chain_start"]["rmse_m"]
                        for x in available
                    ))
                    if available else None
                ),
        })

    return {
        "pair_cases": cases,
        "hop_summary": hop_summary,
    }


def main():
    assert len(sys.argv) == 5

    run, l15path, l16path, out = map(
        Path,
        sys.argv[1:],
    )

    assert out.is_dir() and not out.is_symlink()

    l15 = load(l15path)
    l16 = load(l16path)

    assert l16["l15_report_sha256"] == sha(
        l15path
    )

    assert l16[
        "repeated_derivation_identical"
    ] is True

    assert l16[
        "consecutive_l15_baselines_reproduced"
    ] == 5

    assert l15[
        "deterministic_two_derivations_identical"
    ] is True

    assert (
        l15["pose_factors_authorized"]
        == l16["pose_factors_authorized"]
        == 0
    )

    clouds = cloud_inputs(run, l15)

    selftest()

    first = derive(
        clouds,
        l15,
        l16,
    )

    second = derive(
        clouds,
        l15,
        l16,
    )

    assert canonical(first) == canonical(second)

    report = {
        "schema":
            "TRUST_ROBOT_L17_CHAIN_SEEDED_LONG_BASELINE_ICP_DIAGNOSTIC_V1",

        "implementation_sha256":
            sha(Path(__file__)),

        "upstream_l15_sha256":
            sha(l15path),

        "upstream_l16_sha256":
            sha(l16path),

        "nonadjacent_pairs": 10,
        "seed_variants_per_pair": len(SEEDS),

        "chain_seeded_attempts_per_derivation": 70,
        "baseline_identity_attempts_per_derivation": 10,

        "two_derivations_identical": True,
        "frozen_icp_unchanged": True,

        "short_chain_seed_reuses_same_sensor_scans": True,
        "chain_closeness_is_independent_accuracy": False,

        "no_pose_selection_authorized": True,

        "calibrated_sensor_noise": False,
        "cross_sensor_sync_verified": False,
        "independent_ground_truth_verified": False,

        "ate_rpe_computed": False,
        "health_labels_generated": 0,
        "pose_factors_authorized": 0,

        **first,
    }

    destination = (
        out / "l17_chain_seeded_registration_report_v1.json"
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

    for item in first["pair_cases"]:
        center = item["chain_start"]

        print(
            "L17_PAIR=",
            json.dumps({
                "steps": item["steps"],
                "hops": item["hops"],

                "identity_rmse_m":
                    item["identity_start"]["rmse_m"],

                "chain_seeded_status":
                    center["status"],

                "chain_seeded_rmse_m":
                    center["rmse_m"],

                "identity_rotation_discrepancy_deg":
                    item["identity_start"][
                        "difference_from_short_chain"
                    ]["rotation_deg"],

                "chain_seeded_rotation_discrepancy_deg":
                    (
                        center[
                            "difference_from_short_chain"
                        ]["rotation_deg"]
                        if center[
                            "difference_from_short_chain"
                        ] is not None
                        else None
                    ),

                "identity_duplicate_assignments":
                    item["identity_start"][
                        "nearest_neighbor_topology"
                    ]["duplicate_target_assignments"],

                "chain_seeded_duplicate_assignments":
                    (
                        center[
                            "nearest_neighbor_topology"
                        ]["duplicate_target_assignments"]
                        if center[
                            "nearest_neighbor_topology"
                        ] is not None
                        else None
                    ),

                "multi_seed_spread":
                    item["seed_solution_spread"],
            }, sort_keys=True),
            flush=True,
        )

    for item in first["hop_summary"]:
        print(
            "L17_HOP_SUMMARY=",
            json.dumps(
                item,
                sort_keys=True,
            ),
            flush=True,
        )

    print(
        "L17_REPORT_SHA256=",
        sha(destination),
    )

    print("QUALIFIED_POSE_FACTORS=0")
    print("L17_OFFLINE_INITIALIZATION_AUDIT=PASS")


if __name__ == "__main__":
    main()
