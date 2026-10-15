"""L15: offline restored-sixth-scan registration diagnostic.

Engineering-only ICP / SE(3) internal consistency; no calibrated noise,
physical synchronization, health labels, ground truth or pose-factor admission.
"""

import hashlib
import json
import signal
import statistics
import sys
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation

from trust_robot.lidar_frontend import (
    LidarFrontendError,
    register_current_scan_to_previous,
)

from trust_robot.diagnostics import (
    DiagnosticFeatureError,
    extract_lidar_registration_diagnostics,
)

STEPS = (51, 61, 71, 81, 91, 101)

FEATURES = (
    "source_point_count",
    "target_point_count",
    "fixed_point_iterations",
    "final_correspondence_count",
    "final_nearest_neighbor_rmse_m",
)

AMPLITUDES = (0.0005, 0.002)
PATTERNS = tuple(range(1, 13))


def sha(path):
    assert path.is_file() and not path.is_symlink(), path
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path):
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


def clouds_from_run(run, counts):
    root = run / "multimodal_probe_results_v15"

    index = read_json(
        root / "capture_index_v15.json"
    )

    summary = read_json(
        root / "summary_v1.json"
    )

    assert [
        row["step"] for row in index
    ] == list(STEPS)

    assert [
        row["lidar_points"] for row in index
    ] == counts

    assert summary["sequence_lidar_frames"] == 6
    assert summary["sequence_camera_frames"] == 6
    assert summary["usd_pose_samples"] == 130

    clouds = []
    provenance = []

    for i, (step, count, row) in enumerate(
        zip(STEPS, counts, index),
        1,
    ):
        relative = f"frames_v15/lidar_{i:03d}.npy"

        assert row["lidar_file"] == relative

        path = root / relative
        cloud_sha = sha(path)

        with path.open("rb") as stream:
            arr = np.load(
                stream,
                allow_pickle=False,
            )

        assert arr.shape == (count, 3)
        assert np.isfinite(arr).all()

        raw_path = (
            run / "qualified_xyz_v1"
            / f"lidar_xyz_step_{step:03d}.npz"
        )

        raw_sha = sha(raw_path)

        with np.load(
            raw_path,
            allow_pickle=False,
        ) as raw:
            assert np.array_equal(
                raw["xyz"],
                arr,
            )

            flags = raw["flags"].astype(np.uint64)

            assert len(flags) == count
            assert np.all((flags & 64) != 0)

            stamp = int(raw["timestamp_ns"][0])
            frame_id = int(raw["frame_id"][0])

        assert row["lidar_rendering_time_raw"] == (
            f"GMO_SENSOR_TIMESTAMP_NS:{stamp}"
        )

        provenance.append({
            "step": step,
            "count": count,
            "cloud_sha256": cloud_sha,
            "qualified_xyz_sha256": raw_sha,
            "gmo_frame_id": frame_id,
            "gmo_timestamp_ns_unqualified": stamp,
        })

        clouds.append(arr)

    return clouds, provenance


def geometry(cloud):
    centered = cloud - cloud.mean(axis=0)

    sv = np.linalg.svd(
        centered,
        compute_uv=False,
    )

    h = (
        np.eye(3) * np.sum(centered * centered)
        - centered.T @ centered
    )

    eig = np.linalg.eigvalsh(
        (h + h.T) / 2
    )

    assert np.isfinite(eig).all()
    assert eig[-1] > 0
    assert eig[0] >= -1e-10

    eig = np.maximum(eig, 0)

    return {
        "point_count": int(len(cloud)),

        "spatial_numeric_rank": int(
            np.linalg.matrix_rank(centered)
        ),

        "spatial_singular_ratio": float(
            sv[-1] / sv[0]
        ),

        "rotational_information_ratio": float(
            eig[0] / eig[-1]
        ),

        "physical_six_dof_observability_verified":
            False,
    }


def register(previous, current):
    def alarm(_signum, _frame):
        raise TimeoutError("Registration timeout")

    old = signal.signal(
        signal.SIGALRM,
        alarm,
    )

    signal.setitimer(
        signal.ITIMER_REAL,
        6.0,
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

        return {
            "status": "DIAGNOSTIC_AVAILABLE",

            "pose":
                result.previous_lidar_T_current_lidar.to_dict(),

            "rmse_m": float(
                features["final_nearest_neighbor_rmse_m"]
            ),

            "error": None,
        }

    except (
        LidarFrontendError,
        DiagnosticFeatureError,
        TimeoutError,
        np.linalg.LinAlgError,
    ) as exc:
        return {
            "status": "REGISTRATION_UNAVAILABLE",
            "pose": None,
            "rmse_m": None,
            "error": type(exc).__name__,
        }

    finally:
        signal.setitimer(
            signal.ITIMER_REAL,
            0,
        )

        signal.signal(
            signal.SIGALRM,
            old,
        )


def pose_matrix(pose):
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

    assert abs(np.linalg.norm(q) - 1.0) < 1e-5

    matrix = np.eye(4)

    matrix[:3, :3] = Rotation.from_quat([
        q[1], q[2], q[3], q[0]
    ]).as_matrix()

    matrix[:3, 3] = t

    return matrix


def inverse(matrix):
    result = np.eye(4)

    result[:3, :3] = matrix[:3, :3].T

    result[:3, 3] = (
        -result[:3, :3] @ matrix[:3, 3]
    )

    return result


def residual(matrix):
    return {
        "translation_closure_m": float(
            np.linalg.norm(matrix[:3, 3])
        ),

        "rotation_closure_deg": float(
            np.degrees(
                Rotation.from_matrix(
                    matrix[:3, :3]
                ).magnitude()
            )
        ),
    }


def perturb(xyz, amplitude, pattern_id):
    i = np.arange(
        1, len(xyz) + 1,
        dtype=float,
    )[:, None]

    j = np.arange(
        1, 4,
        dtype=float,
    )[None, :]

    pattern = (
        np.sin(
            i * j * (pattern_id + 1) * 0.311
        )
        + 0.55 * np.cos(
            (i + pattern_id * 1.7)
            * (j + 0.4) * 0.679
        )
    )

    pattern -= pattern.mean(
        axis=0,
        keepdims=True,
    )

    scale = np.max(
        np.abs(pattern)
    )

    assert scale > 0

    return xyz + amplitude * pattern / scale


def derive(clouds):
    geometric = [
        {
            "step": step,
            **geometry(cloud),
        }
        for step, cloud in zip(STEPS, clouds)
    ]

    forward = [
        register(
            clouds[i],
            clouds[i + 1],
        )
        for i in range(5)
    ]

    reverse = [
        register(
            clouds[i + 1],
            clouds[i],
        )
        for i in range(5)
    ]

    bidirectional = []

    for i, (a, b) in enumerate(
        zip(forward, reverse)
    ):
        closure = (
            residual(
                pose_matrix(a["pose"])
                @ pose_matrix(b["pose"])
            )
            if (
                a["pose"] is not None
                and b["pose"] is not None
            )
            else None
        )

        bidirectional.append({
            "steps": [
                STEPS[i],
                STEPS[i + 1],
            ],

            "forward_status": a["status"],
            "reverse_status": b["status"],

            "closure": closure,
            "pose_factor_authorized": False,
        })

    skips = []

    for i in range(4):
        direct = register(
            clouds[i],
            clouds[i + 2],
        )

        closure = None

        if (
            direct["pose"] is not None
            and forward[i]["pose"] is not None
            and forward[i + 1]["pose"] is not None
        ):
            chain = (
                pose_matrix(forward[i]["pose"])
                @ pose_matrix(forward[i + 1]["pose"])
            )

            closure = residual(
                inverse(
                    pose_matrix(direct["pose"])
                ) @ chain
            )

        skips.append({
            "steps": [
                STEPS[i],
                STEPS[i + 1],
                STEPS[i + 2],
            ],

            "direct_status": direct["status"],
            "direct_rmse_m": direct["rmse_m"],

            "direct_vs_chain": closure,
            "pose_factor_authorized": False,
        })

    challenges = []
    final_forward = forward[-1]

    for amplitude in AMPLITUDES:
        for pattern_id in PATTERNS:
            trial = register(
                clouds[-2],
                perturb(
                    clouds[-1],
                    amplitude,
                    pattern_id,
                ),
            )

            change = (
                residual(
                    inverse(
                        pose_matrix(
                            final_forward["pose"]
                        )
                    )
                    @ pose_matrix(trial["pose"])
                )
                if (
                    final_forward["pose"] is not None
                    and trial["pose"] is not None
                )
                else None
            )

            challenges.append({
                "amplitude_m": amplitude,
                "pattern_id": pattern_id,
                "status": trial["status"],
                "error": trial["error"],
                "pose_change": change,
                "calibrated_noise": False,
            })

    summaries = []

    for amplitude in AMPLITUDES:
        rows = [
            r for r in challenges
            if r["amplitude_m"] == amplitude
        ]

        good = [
            r["pose_change"]
            for r in rows
            if r["pose_change"] is not None
        ]

        summaries.append({
            "amplitude_m": amplitude,
            "available_count": len(good),
            "unavailable_count":
                len(rows) - len(good),

            "median_rotation_change_deg": (
                float(statistics.median(
                    r["rotation_closure_deg"]
                    for r in good
                ))
                if good else None
            ),

            "maximum_rotation_change_deg": (
                float(max(
                    r["rotation_closure_deg"]
                    for r in good
                ))
                if good else None
            ),

            "median_translation_change_m": (
                float(statistics.median(
                    r["translation_closure_m"]
                    for r in good
                ))
                if good else None
            ),
        })

    return {
        "geometry": geometric,
        "forward": forward,
        "reverse": reverse,
        "bidirectional": bidirectional,
        "skip_pair": skips,
        "final_pair_perturbations": challenges,
        "final_pair_perturbation_summaries": summaries,
    }


def main():
    assert len(sys.argv) == 5

    run, l14_path, l9_path, out = map(
        Path,
        sys.argv[1:],
    )

    assert out.is_dir() and not out.is_symlink()

    l14 = read_json(l14_path)
    l9 = read_json(l9_path)

    assert l14["step101_outcome"] == "RESTORED_16"

    assert l14["shifted_selected_valid_counts"] == [
        16, 16, 16, 16, 16, 16
    ]

    assert l14["baseline_selected_valid_counts"] == [
        16, 16, 16, 16, 16, 2
    ]

    assert l14["pose_factors_authorized"] == 0
    assert l9["pose_factors_authorized"] == 0

    assert l14["scene_sha256"] == sha(
        run / "multimodal_scene_v5.usda"
    )

    assert l14["acquisition_source_sha256"] == sha(
        run / "multimodal_probe_candidate_v15.py"
    )

    clouds, hashes = clouds_from_run(
        run,
        [16, 16, 16, 16, 16, 16],
    )

    first = derive(clouds)
    second = derive(clouds)

    assert canonical(first) == canonical(second)

    report = {
        "schema":
            "TRUST_ROBOT_L15_RESTORED_FINAL_SCAN_REGISTRATION_V1",

        "implementation_sha256":
            sha(Path(__file__)),

        "upstream_l14_sha256":
            sha(l14_path),

        "upstream_l9_sha256":
            sha(l9_path),

        "scan_file_provenance": hashes,

        "deterministic_two_derivations_identical":
            True,

        "synthetic_not_physical": True,

        "cross_sensor_sync_verified": False,
        "independent_ground_truth_verified": False,
        "sensor_noise_calibrated": False,
        "localization_accuracy_scored": False,

        "health_labels_generated": 0,
        "pose_factors_authorized": 0,

        "final_pair_included_in_engineering_diagnostics":
            True,

        **first,
    }

    target = (
        out / "l15_restored_final_scan_registration_v1.json"
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

    for row in first["geometry"]:
        print(
            "L15_SCAN_GEOMETRY=",
            json.dumps(
                row,
                sort_keys=True,
            ),
            flush=True,
        )

    for i, row in enumerate(first["forward"]):
        print(
            "L15_FORWARD=",
            json.dumps({
                "steps": list(STEPS[i:i + 2]),
                "status": row["status"],
                "rmse_m": row["rmse_m"],

                "translation_norm_m": (
                    float(np.linalg.norm(
                        row["pose"]["translation_m"]
                    ))
                    if row["pose"] is not None
                    else None
                ),
            }, sort_keys=True),
            flush=True,
        )

    for row in first["bidirectional"]:
        print(
            "L15_REVERSE_CLOSURE=",
            json.dumps(
                row,
                sort_keys=True,
            ),
            flush=True,
        )

    for row in first["skip_pair"]:
        print(
            "L15_SKIP_CLOSURE=",
            json.dumps(
                row,
                sort_keys=True,
            ),
            flush=True,
        )

    for row in first[
        "final_pair_perturbation_summaries"
    ]:
        print(
            "L15_FINAL_PAIR_PERTURBATION=",
            json.dumps(
                row,
                sort_keys=True,
            ),
            flush=True,
        )

    print(
        "L15_FINAL_PAIR_REGISTRATION_STATUS=",
        first["forward"][-1]["status"],
        flush=True,
    )

    print("L15_DETERMINISTIC_REDERIVATION=PASS")
    print("L15_OFFLINE_DIAGNOSTICS=PASS")
    print("L15_REPORT_SHA256=", sha(target))


if __name__ == "__main__":
    main()
