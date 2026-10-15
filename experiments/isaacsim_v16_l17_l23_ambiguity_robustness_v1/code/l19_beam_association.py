"""L19: synthetic same-emitter association vs rigid registration.

Emitter association is inferred from spherical elevation and
azimuth conventions. Matching an emitter across frames does NOT
establish that the return comes from the same physical surface point.

No estimator factor admission, health labels, calibrated noise,
or independent ground-truth localization evaluation.
"""

import hashlib
import json
import math
import re
import statistics
import sys
from itertools import combinations
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation

from trust_robot.lidar_frontend import rigid_transform_kabsch

STEPS = (51, 61, 71, 81, 91, 101)

SCENE_SHA = (
    "43b4ffe0f7af29e435203ac3aa8c2d4c4897434042f37e26586b124b2495d8cf"
)


def sha(path):
    assert path.is_file() and not path.is_symlink(), str(path)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    sha(path)
    return json.loads(path.read_text())


def canonical(obj):
    return (
        json.dumps(
            obj,
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
    assert abs(np.linalg.norm(q) - 1) < 1e-5

    m = np.eye(4)

    m[:3, :3] = Rotation.from_quat([
        q[1], q[2], q[3], q[0]
    ]).as_matrix()

    m[:3, 3] = t
    return m


def inverse(a):
    b = np.eye(4)

    b[:3, :3] = a[:3, :3].T
    b[:3, 3] = -b[:3, :3] @ a[:3, 3]

    return b


def apply(pose, xyz):
    return (
        xyz @ pose[:3, :3].T
        + pose[:3, 3]
    )


def residual(a, b):
    d = inverse(a) @ b

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


def fit(source, target):
    assert source.shape == target.shape
    assert source.ndim == 2
    assert source.shape[1] == 3
    assert len(source) >= 3

    pose = matrix(
        rigid_transform_kabsch(
            source,
            target,
        ).to_dict()
    )

    errors = np.linalg.norm(
        apply(pose, source) - target,
        axis=1,
    )

    return pose, float(
        np.sqrt(np.mean(errors ** 2))
    )


def nearest(target, source, pose):
    d, ids = cKDTree(target).query(
        apply(pose, source),
        k=1,
        workers=1,
    )

    assert np.isfinite(d).all()

    return {
        "rmse_m": float(
            np.sqrt(np.mean(d ** 2))
        ),

        "duplicate_target_assignments":
            int(len(source) - len(np.unique(ids))),
    }


def selftest():
    xyz = np.array([
        [
            0.13 * i + 0.012 * np.sin(i),
            0.09 * np.cos(i * 1.3),
            0.045 * np.sin(i * 0.7) + 0.02 * i,
        ]
        for i in range(16)
    ])

    truth = np.eye(4)
    truth[:3, :3] = Rotation.from_euler(
        "xyz",
        [0.04, -0.03, 0.06],
    ).as_matrix()
    truth[:3, 3] = [0.11, -0.025, 0.017]

    target = apply(truth, xyz)

    estimated, rmse = fit(xyz, target)

    assert rmse < 1e-12
    assert residual(
        truth,
        estimated,
    )["translation_m"] < 1e-10

    # Negative control: shuffled indices must not be
    # interpreted as valid same-emitter correspondences.
    scrambled = target[
        np.roll(np.arange(16), 4)
    ]

    _, bad_rmse = fit(xyz, scrambled)

    assert bad_rmse > 1e-3

    print(
        "L19_RIGID_FIT_AND_SHUFFLED_ID_NEGATIVE_CONTROL=PASS",
        flush=True,
    )


def scene_angles(path):
    assert sha(path) == SCENE_SHA

    text = path.read_text()
    result = []

    for field in ("azimuthDeg", "elevationDeg"):
        pattern = (
            r"emitterState:s001:"
            + field
            + r"\s*=\s*\[([^]]+)\]"
        )

        match = re.search(pattern, text)

        assert match is not None, field

        values = np.array([
            float(x)
            for x in match.group(1).split(",")
        ])

        assert values.shape == (16,)
        assert np.isfinite(values).all()

        result.append(values)

    assert len(np.unique(result[1])) == 16

    return result


def recorded_clouds(run, l15):
    root = run / "multimodal_probe_results_v15"

    index = load(
        root / "capture_index_v15.json"
    )

    assert [
        int(x["step"])
        for x in index
    ] == list(STEPS)

    assert [
        int(x["lidar_points"])
        for x in index
    ] == [16] * 6

    provenance = l15["scan_file_provenance"]

    assert [
        int(x["step"])
        for x in provenance
    ] == list(STEPS)

    az_expected, el_expected = scene_angles(
        run / "multimodal_scene_v5.usda"
    )

    clouds = []
    mappings = []

    for index_number, (item, proof) in enumerate(
        zip(index, provenance),
        1,
    ):
        step = STEPS[index_number - 1]

        path = (
            root / f"frames_v15/lidar_{index_number:03d}.npy"
        )

        assert item["lidar_file"] == (
            f"frames_v15/lidar_{index_number:03d}.npy"
        )

        assert sha(path) == proof["cloud_sha256"]

        with path.open("rb") as stream:
            cloud = np.load(
                stream,
                allow_pickle=False,
            )

        assert cloud.shape == (16, 3)
        assert np.isfinite(cloud).all()

        xyz_path = (
            run / "qualified_xyz_v1"
            / f"lidar_xyz_step_{step:03d}.npz"
        )

        assert sha(xyz_path) == (
            proof["qualified_xyz_sha256"]
        )

        with np.load(
            xyz_path,
            allow_pickle=False,
        ) as data:
            assert np.array_equal(
                data["xyz"],
                cloud,
            )

            flags = data["flags"].astype(
                np.uint64
            )

            assert len(flags) == 16
            assert np.all((flags & 64) != 0)

            assert int(data["frame_id"][0]) == (
                proof["gmo_frame_id"]
            )

            assert int(data["timestamp_ns"][0]) == (
                proof["gmo_timestamp_ns_unqualified"]
            )

        pre = (
            run / "pre_gmo_samples_v1"
            / f"gmo_pre_step_{step:03d}.npz"
        )

        pre_sha = sha(pre)

        with np.load(
            pre,
            allow_pickle=False,
        ) as data:
            az = np.asarray(
                data["x"],
                dtype=np.float64,
            )

            el = np.asarray(
                data["y"],
                dtype=np.float64,
            )

            rr = np.asarray(
                data["z"],
                dtype=np.float64,
            )

            assert int(data["frame_id"][0]) == (
                proof["gmo_frame_id"]
            )

            assert int(data["timestamp_ns"][0]) == (
                proof["gmo_timestamp_ns_unqualified"]
            )

        assert az.shape == el.shape == rr.shape == (16,)
        assert np.isfinite(az).all()
        assert np.isfinite(el).all()
        assert np.isfinite(rr).all()
        assert np.all(rr > 0)

        # Independently reproduce GMO spherical-to-XYZ
        # conversion; no points are removed here.
        a_rad = np.deg2rad(az)
        e_rad = np.deg2rad(el)

        reconstructed = np.column_stack((
            rr * np.cos(e_rad) * np.cos(a_rad),
            rr * np.cos(e_rad) * np.sin(a_rad),
            rr * np.sin(e_rad),
        )).astype(np.float32)

        assert np.allclose(
            reconstructed,
            cloud,
            rtol=0,
            atol=2e-6,
        )

        # Elevation values are unique in this synthetic
        # candidate, so infer configuration index.
        ids = []
        elevation_errors = []
        azimuth_errors = []

        for a, e in zip(az, el):
            beam_id = int(
                np.argmin(
                    np.abs(el_expected - e)
                )
            )

            ids.append(beam_id)

            elevation_errors.append(
                abs(float(el_expected[beam_id] - e))
            )

            # Observed azimuth is inverted relative to
            # configured azimuth, as identified by L12.
            azimuth_errors.append(
                abs(float(az_expected[beam_id] + a))
            )

        assert sorted(ids) == list(range(16))

        max_e = max(elevation_errors)
        max_a = max(azimuth_errors)

        assert max_e < 0.05
        assert max_a < 0.05

        # Reorder actual XYZ by inferred emitter index.
        order = np.argsort(ids)

        clouds.append(
            np.asarray(
                cloud[order],
                dtype=np.float64,
            )
        )

        mappings.append({
            "step": step,

            "pre_gmo_sha256": pre_sha,

            "raw_return_count": 16,

            "inferred_emitter_indices_in_gmo_order":
                ids,

            "all_configured_indices_present":
                True,

            "maximum_elevation_residual_deg":
                float(max_e),

            "maximum_inverted_azimuth_residual_deg":
                float(max_a),

            "physical_emitter_identity_verified":
                False,
        })

    assert len(clouds) == 6

    return clouds, mappings


def derive(clouds, l15, l16, l18):
    chain = [np.eye(4)]

    for item in l15["forward"]:
        assert item["status"] == (
            "DIAGNOSTIC_AVAILABLE"
        )

        chain.append(
            chain[-1] @ matrix(item["pose"])
        )

    old16 = {
        tuple(row["steps"]): row
        for row in l16["all_pairs"]
    }

    old18 = {
        tuple(row["steps"]): row
        for row in l18["pair_cases"]
    }

    assert len(old16) == 15
    assert len(old18) == 10

    pairs = []

    for i, j in combinations(range(6), 2):
        steps = (STEPS[i], STEPS[j])

        target = clouds[i]
        source = clouds[j]

        expected_chain = (
            inverse(chain[i]) @ chain[j]
        )

        estimate, matched_rmse = fit(
            source,
            target,
        )

        info = nearest(
            target,
            source,
            estimate,
        )

        previous = old16[steps]

        assert previous["status"] == (
            "DIAGNOSTIC_AVAILABLE"
        )

        reference_bijective = (
            old18.get(steps)
        )

        # Sixteen deterministic leave-one-emitter-out
        # fits. This checks fit sensitivity, not
        # calibrated estimator uncertainty.
        jackknife = []

        for omitted in range(16):
            keep = np.arange(16) != omitted

            reduced, _ = fit(
                source[keep],
                target[keep],
            )

            jackknife.append(
                residual(estimate, reduced)
            )

        previous_bijective = None

        if reference_bijective is not None:
            trial = reference_bijective[
                "experimental_one_to_one"
            ]["identity"]

            assert trial["status"] == (
                "DIAGNOSTIC_AVAILABLE"
            )

            previous_bijective = {
                "nearest_rmse_m":
                    trial["nearest_neighbor"]["nearest_rmse_m"],

                "difference_from_short_chain":
                    trial["difference_from_chain"],

                "physical_correspondence_verified":
                    False,
            }

        pairs.append({
            "steps": list(steps),
            "hop_count": j - i,

            "frozen_identity": {
                "nearest_rmse_m":
                    float(previous["rmse_m"]),

                "direct_vs_chain":
                    previous["direct_vs_composed_se3"],
            },

            "inferred_emitter_index_fit": {
                "matched_emitter_rmse_m":
                    matched_rmse,

                "nearest_neighbor_diagnostic":
                    info,

                "difference_from_short_chain":
                    residual(estimate, expected_chain),

                "leave_one_emitter_out": {
                    "trials": 16,

                    "maximum_rotation_change_deg":
                        float(max(
                            x["rotation_deg"]
                            for x in jackknife
                        )),

                    "median_rotation_change_deg":
                        float(statistics.median(
                            x["rotation_deg"]
                            for x in jackknife
                        )),

                    "maximum_translation_change_m":
                        float(max(
                            x["translation_m"]
                            for x in jackknife
                        )),

                    "median_translation_change_m":
                        float(statistics.median(
                            x["translation_m"]
                            for x in jackknife
                        )),
                },

                "same_emitter_means_same_physical_point":
                    False,
            },

            "l18_bijective_identity_diagnostic":
                previous_bijective,

            "pose_factor_authorized":
                False,
        })

    assert len(pairs) == 15

    summaries = []

    for hop in range(1, 6):
        group = [
            x for x in pairs
            if x["hop_count"] == hop
        ]

        summaries.append({
            "hop_count": hop,
            "pair_count": len(group),

            "median_emitter_fit_from_chain_rotation_deg":
                float(statistics.median(
                    x["inferred_emitter_index_fit"][
                        "difference_from_short_chain"
                    ]["rotation_deg"]
                    for x in group
                )),

            "maximum_emitter_fit_jackknife_rotation_deg":
                float(max(
                    x["inferred_emitter_index_fit"][
                        "leave_one_emitter_out"
                    ]["maximum_rotation_change_deg"]
                    for x in group
                )),

            "median_emitter_fit_nn_rmse_m":
                float(statistics.median(
                    x["inferred_emitter_index_fit"][
                        "nearest_neighbor_diagnostic"
                    ]["rmse_m"]
                    for x in group
                )),

            "median_frozen_nn_rmse_m":
                float(statistics.median(
                    x["frozen_identity"]["nearest_rmse_m"]
                    for x in group
                )),
        })

    return {
        "pair_diagnostics": pairs,
        "hop_summaries": summaries,
    }


def main():
    assert len(sys.argv) == 6

    run, l15path, l16path, l18path, out = map(
        Path, sys.argv[1:]
    )

    assert run.is_dir() and not run.is_symlink()
    assert out.is_dir() and not out.is_symlink()

    l15, l16, l18 = map(
        load,
        (l15path, l16path, l18path),
    )

    assert l16["l15_report_sha256"] == (
        sha(l15path)
    )

    assert l18["upstream_l15_sha256"] == (
        sha(l15path)
    )

    assert l18["upstream_l16_sha256"] == (
        sha(l16path)
    )

    assert (
        l15["pose_factors_authorized"]
        == l16["pose_factors_authorized"]
        == l18["pose_factors_authorized"]
        == 0
    )

    selftest()

    clouds, mappings = recorded_clouds(
        run,
        l15,
    )

    first = derive(
        clouds, l15, l16, l18
    )

    second = derive(
        clouds, l15, l16, l18
    )

    assert canonical(first) == canonical(second)

    report = {
        "schema":
            "TRUST_ROBOT_L19_SYNTHETIC_BEAM_ASSOCIATION_STABILITY_V1",

        "implementation_sha256":
            sha(Path(__file__)),

        "l15_report_sha256":
            sha(l15path),

        "l16_report_sha256":
            sha(l16path),

        "l18_report_sha256":
            sha(l18path),

        "raw_beam_mapping":
            mappings,

        "deterministic_two_derivations_identical":
            True,

        "six_scans_have_all_16_inferred_indices":
            True,

        "all_unordered_pair_diagnostics": 15,

        "jackknife_fits_per_derivation":
            240,

        "inferred_emitter_association_not_physical_feature_tracking":
            True,

        "physical_emitter_identity_verified":
            False,

        "experimental_method_not_admitted_to_frontend":
            True,

        "independent_ground_truth_verified":
            False,

        "cross_sensor_sync_verified":
            False,

        "ate_rpe_computed":
            False,

        "health_labels_generated": 0,
        "pose_factors_authorized": 0,

        **first,
    }

    target = (
        out / "l19_beam_association_stability_report_v1.json"
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

    for mapping in mappings:
        print(
            "L19_BEAM_MAPPING=",
            json.dumps({
                "step": mapping["step"],

                "indices_complete":
                    mapping["all_configured_indices_present"],

                "max_azimuth_error_deg":
                    mapping[
                        "maximum_inverted_azimuth_residual_deg"
                    ],

                "max_elevation_error_deg":
                    mapping[
                        "maximum_elevation_residual_deg"
                    ],
            }, sort_keys=True),
            flush=True,
        )

    for row in first["pair_diagnostics"]:
        if row["hop_count"] < 2:
            continue

        fit_row = row[
            "inferred_emitter_index_fit"
        ]

        print(
            "L19_PAIR=",
            json.dumps({
                "steps": row["steps"],
                "hops": row["hop_count"],

                "frozen_nn_rmse_m":
                    row["frozen_identity"]["nearest_rmse_m"],

                "emitter_fit_nn_rmse_m":
                    fit_row[
                        "nearest_neighbor_diagnostic"
                    ]["rmse_m"],

                "emitter_fit_matched_rmse_m":
                    fit_row["matched_emitter_rmse_m"],

                "emitter_fit_from_chain_rotation_deg":
                    fit_row[
                        "difference_from_short_chain"
                    ]["rotation_deg"],

                "emitter_fit_from_chain_translation_m":
                    fit_row[
                        "difference_from_short_chain"
                    ]["translation_m"],

                "jackknife_max_rotation_deg":
                    fit_row["leave_one_emitter_out"][
                        "maximum_rotation_change_deg"
                    ],

                "jackknife_max_translation_m":
                    fit_row["leave_one_emitter_out"][
                        "maximum_translation_change_m"
                    ],
            }, sort_keys=True),
            flush=True,
        )

    for row in first["hop_summaries"]:
        print(
            "L19_HOP_SUMMARY=",
            json.dumps(row, sort_keys=True),
            flush=True,
        )

    print("L19_BEAM_ASSOCIATION_AUDIT=PASS")
    print("L19_REPEATED_DERIVATION=PASS")

    print(
        "L19_REPORT_SHA256=",
        sha(target),
    )

    print("QUALIFIED_POSE_FACTORS=0")


if __name__ == "__main__":
    main()
