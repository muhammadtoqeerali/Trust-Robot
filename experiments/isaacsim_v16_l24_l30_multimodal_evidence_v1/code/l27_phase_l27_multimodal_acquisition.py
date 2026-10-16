"""L27: offline multimodal recording inventory and acquisition contract.

Engineering planning only. Does not qualify exposure timestamps,
cross-sensor synchronization, independent 6DoF reference,
sensor health labels, or estimator pose factors.
"""

import argparse
import hashlib
import json
import math
import statistics
from pathlib import Path

import numpy as np


STEPS = (51, 61, 71, 81, 91, 101)

REQUIRED_ARTIFACTS = {
    "physical_correspondence_validation":
        "physical_correspondence_audit.json",

    "qualified_exposure_synchronization":
        "clock_alignment_validation.json",

    "calibrated_factor_uncertainty":
        "factor_uncertainty_calibration.json",

    "verified_extrinsic_transform":
        "rig_extrinsic_calibration.json",

    "independent_6dof_reference":
        "independent_reference_poses.jsonl",

    "heldout_6dof_accuracy_evaluation":
        "heldout_localization_evaluation.json",

    "adjudicated_sensor_failure_labels":
        "failure_adjudications.jsonl",

    "independent_source_authenticity":
        "capture_provenance_attestation.json",

    "validated_detection_error_rates":
        "heldout_detection_evaluation.json",

    "trusted_hardware_exposure_time":
        "exposure_clock_evidence.json",

    "independently_verified_replay_monitor":
        "replay_monitor_validation.json",
}


def sha(path):
    assert path.is_file() and not path.is_symlink(), str(path)

    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def read_json(path):
    sha(path)
    return json.loads(path.read_text())


def read_jsonl(path):
    sha(path)

    return [
        json.loads(line)
        for line in path.read_text().splitlines()
        if line.strip()
    ]


def canonical(value):
    return (
        json.dumps(
            value,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        ) + "\n"
    )


def finite_vector(value, length):
    if value is None:
        return False

    try:
        arr = np.asarray(value, dtype=float)
    except (TypeError, ValueError):
        return False

    return (
        arr.shape == (length,)
        and bool(np.isfinite(arr).all())
    )


def inventory(run, l15, l24):
    root = run / "multimodal_probe_results_v15"

    index_path = root / "capture_index_v15.json"
    summary_path = root / "summary_v1.json"
    imu_path = root / "imu_v1.jsonl"
    pose_path = root / "base_pose_series_v15.jsonl"

    index = read_json(index_path)
    summary = read_json(summary_path)
    imu = read_jsonl(imu_path)
    poses = read_jsonl(pose_path)

    prior_context = l24["baseline_context"]

    assert sha(index_path) == prior_context[
        "capture_index_sha256"
    ]

    assert sha(imu_path) == prior_context[
        "imu_jsonl_sha256"
    ]

    assert sha(pose_path) == prior_context[
        "pose_jsonl_sha256"
    ]

    assert len(index) == 6
    assert len(imu) == 130
    assert len(poses) == 130

    assert summary["sequence_camera_frames"] == 6
    assert summary["sequence_lidar_frames"] == 6
    assert summary["usd_pose_samples"] == 130

    assert [
        int(x["step"]) for x in index
    ] == list(STEPS)

    assert [
        int(x["step"]) for x in imu
    ] == list(range(1, 131))

    assert [
        int(x["step"]) for x in poses
    ] == list(range(1, 131))

    pose_times = np.array([
        float(x["simulation_step_time_s"])
        for x in poses
    ])

    imu_times = np.array([
        float(x["simulation_step_time_s"])
        for x in imu
    ])

    assert np.isfinite(pose_times).all()
    assert np.isfinite(imu_times).all()

    assert np.all(np.diff(pose_times) > 0)
    assert np.allclose(
        pose_times,
        imu_times,
        rtol=0,
        atol=1e-9,
    )

    assert all(
        x["pose_source"] == "USD_COMPOSED_WORLD_TRANSFORM"
        for x in poses
    )

    assert all(
        x["physics_pose_independently_verified"] is False
        for x in poses
    )

    assert all(
        x["timestamp_semantics_verified"] is False
        for x in imu
    )

    evidence = l15["scan_file_provenance"]

    assert len(evidence) == 6

    assert [
        int(x["step"]) for x in evidence
    ] == list(STEPS)

    captures = []
    camera_hashes = []
    lidar_hashes = []
    nonblank = []

    for k, (step, row, proof) in enumerate(
        zip(STEPS, index, evidence),
        start=1,
    ):
        assert row["lidar_file"] == (
            f"frames_v15/lidar_{k:03d}.npy"
        )

        assert row["camera_file"] == (
            f"frames_v15/camera_{k:03d}.npy"
        )

        assert int(row["lidar_points"]) == 16
        assert int(proof["count"]) == 16

        camera_path = root / row["camera_file"]
        lidar_path = root / row["lidar_file"]

        lidar_sha = sha(lidar_path)
        camera_sha = sha(camera_path)

        assert lidar_sha == proof["cloud_sha256"]

        with lidar_path.open("rb") as stream:
            lidar = np.load(
                stream,
                allow_pickle=False,
            )

        with camera_path.open("rb") as stream:
            camera = np.load(
                stream,
                allow_pickle=False,
            )

        assert lidar.shape == (16, 3)
        assert camera.shape == (120, 160, 4)

        assert np.isfinite(lidar).all()
        assert np.isfinite(camera).all()

        raw_path = (
            run / "qualified_xyz_v1"
            / f"lidar_xyz_step_{step:03d}.npz"
        )

        assert sha(raw_path) == proof[
            "qualified_xyz_sha256"
        ]

        with np.load(
            raw_path,
            allow_pickle=False,
        ) as raw:
            assert np.array_equal(
                raw["xyz"],
                lidar,
            )

            assert np.all(
                (
                    raw["flags"].astype(np.uint64)
                    & 64
                ) != 0
            )

            frame_id = int(raw["frame_id"][0])
            timestamp_ns = int(
                raw["timestamp_ns"][0]
            )

        assert frame_id == proof["gmo_frame_id"]

        assert timestamp_ns == proof[
            "gmo_timestamp_ns_unqualified"
        ]

        assert row["lidar_rendering_time_raw"] == (
            f"GMO_SENSOR_TIMESTAMP_NS:{timestamp_ns}"
        )

        read_time = float(
            pose_times[step - 1]
        )

        assert abs(
            float(row["camera_read_step_time_s"])
            - read_time
        ) < 1e-5

        assert abs(
            float(row["lidar_read_step_time_s"])
            - read_time
        ) < 1e-5

        camera_fraction = float(
            np.mean(
                np.any(
                    camera[:, :, :3] > 0,
                    axis=2,
                )
            )
        )

        camera_hashes.append(camera_sha)
        lidar_hashes.append(lidar_sha)
        nonblank.append(camera_fraction)

        captures.append({
            "step": step,

            "camera_shape":
                list(camera.shape),

            "lidar_return_count":
                int(len(lidar)),

            "camera_sha256_local_baseline":
                camera_sha,

            "lidar_sha256_pinned":
                lidar_sha,

            "qualified_xyz_sha256_pinned":
                sha(raw_path),

            "gmo_frame_id":
                frame_id,

            "gmo_timestamp_ns_unqualified":
                timestamp_ns,

            "camera_nonblank_fraction":
                camera_fraction,

            "camera_read_step_time_s":
                float(
                    row["camera_read_step_time_s"]
                ),

            "lidar_read_step_time_s":
                float(
                    row["lidar_read_step_time_s"]
                ),

            "physical_exposure_sync_verified":
                False,

            "independent_source_authenticity_verified":
                False,
        })

    base_positions = np.asarray([
        x["usd_world_position_m"]
        for x in poses
    ], dtype=float)

    lidar_positions = np.asarray([
        x["lidar_usd_world_position_m"]
        for x in poses
    ], dtype=float)

    assert base_positions.shape == (130, 3)
    assert lidar_positions.shape == (130, 3)

    assert np.isfinite(base_positions).all()
    assert np.isfinite(lidar_positions).all()

    offset = lidar_positions - base_positions

    offset_drift = float(np.max(
        np.linalg.norm(
            offset - offset[0],
            axis=1,
        )
    ))

    def count_vector(field, length):
        return sum(
            finite_vector(x.get(field), length)
            for x in imu
        )

    reported_times = [
        float(x["sensor_reported_time"])
        for x in imu
        if isinstance(
            x.get("sensor_reported_time"),
            (int, float),
        )
        and math.isfinite(
            float(x["sensor_reported_time"])
        )
    ]

    return {
        "source_hashes": {
            "capture_index":
                sha(index_path),

            "runtime_summary":
                sha(summary_path),

            "imu_series":
                sha(imu_path),

            "usd_pose_series":
                sha(pose_path),
        },

        "camera": {
            "frames": 6,

            "shape": [120, 160, 4],

            "unique_payload_hashes":
                len(set(camera_hashes)),

            "minimum_nonblank_fraction":
                min(nonblank),

            "exposure_timing_qualified":
                False,

            "intrinsic_calibration_independently_verified":
                False,

            "source_authenticity_verified":
                False,
        },

        "lidar": {
            "frames": 6,

            "selected_return_counts":
                [16] * 6,

            "unique_pinned_cloud_hashes":
                len(set(lidar_hashes)),

            "raw_gmo_timestamp_count": 6,

            "raw_timestamp_qualified_as_exposure":
                False,

            "physical_correspondence_validated":
                False,
        },

        "imu": {
            "rows": 130,

            "finite_linear_acceleration_rows":
                count_vector("linear_acceleration", 3),

            "finite_angular_velocity_rows":
                count_vector("angular_velocity", 3),

            "finite_orientation_rows":
                count_vector("orientation", 4),

            "finite_reported_timestamp_rows":
                len(reported_times),

            "reported_timestamps_strictly_increasing":
                (
                    len(reported_times) == 130
                    and all(
                        a < b
                        for a, b in zip(
                            reported_times,
                            reported_times[1:],
                        )
                    )
                ),

            "timestamp_units_independently_qualified":
                False,

            "bias_noise_calibration_verified":
                False,
        },

        "usd_pose": {
            "rows": 130,

            "median_scripted_step_s":
                float(statistics.median(
                    np.diff(pose_times).tolist()
                )),

            "base_displacement_m":
                float(np.linalg.norm(
                    base_positions[-1]
                    - base_positions[0]
                )),

            "base_lidar_offset_max_drift_m":
                offset_drift,

            "independent_physical_6dof_ground_truth":
                False,
        },

        "selected_capture_provenance":
            captures,

        "recording_scope": {
            "six_selected_synthetic_observations":
                True,

            "130_scripted_imu_and_pose_steps":
                True,

            "independent_multimodal_synchronization":
                False,

            "scientific_6dof_reference":
                False,

            "calibrated_sensor_health_labels":
                False,
        },
    }


def acquisition_contract(l26):
    ledger = {
        x["requirement"]: x
        for x in l26["requirements"]
    }

    assert len(ledger) == 11
    assert set(ledger) == set(REQUIRED_ARTIFACTS)

    assert all(
        x["status"] in (
            "UNQUALIFIED",
            "NOT_EVIDENCED",
        )
        for x in ledger.values()
    )

    gates = l26["readiness_decisions"]

    assert len(gates) == 4

    stages = [
        {
            "stage": "A",
            "objective":
                "Record independent acquisition provenance",

            "required_outputs": [
                "Unmodified per-sensor payload hashes",
                "Sensor identity and frame sequence",
                "Clock-domain identification",
                "Acquisition-side immutable manifest",
            ],

            "completed": False,
        },

        {
            "stage": "B",
            "objective":
                "Measure exposure timing and calibrations",

            "required_outputs": [
                "Defined camera and LiDAR exposure times",
                "IMU timestamp clock semantics",
                "Measured clock alignment uncertainty",
                "Verified camera-LiDAR-IMU extrinsics",
            ],

            "completed": False,
        },

        {
            "stage": "C",
            "objective":
                "Acquire independent six-DoF reference",

            "required_outputs": [
                "Reference trajectory with orientation",
                "Reference measurement uncertainty",
                "Reference-to-sensor time alignment",
                "Verified physical correspondences",
            ],

            "completed": False,
        },

        {
            "stage": "D",
            "objective":
                "Validate localization and health detection",

            "required_outputs": [
                "Held-out evaluation recordings",
                "Adjudicated fault and healthy controls",
                "Factor covariance calibration",
                "Six-DoF and detection error evaluation",
            ],

            "completed": False,
        },
    ]

    return {
        "schema":
            "TRUST_ROBOT_L27_FUTURE_MULTIMODAL_ACQUISITION_CONTRACT_V1",

        "status":
            "DESIGN_ONLY_NOT_AN_EXECUTED_ACQUISITION",

        "required_modalities": [
            "camera",
            "lidar",
            "imu",
            "independent_6dof_reference",
        ],

        "required_sensor_fields": [
            "run_id",
            "sensor_id",
            "sensor_modality",
            "sensor_frame_id",
            "sequence_number",
            "payload_sha256",
            "sensor_timestamp_raw",
            "sensor_clock_domain",
            "exposure_time_definition",
            "reference_frame_id",
            "calibration_version",
            "provenance_attestation_reference",
        ],

        "required_reference_fields": [
            "run_id",
            "reference_system_id",
            "reference_timestamp_raw",
            "reference_clock_domain",
            "reference_frame_id",
            "position_xyz_m",
            "orientation_quaternion_wxyz",
            "reference_uncertainty",
            "reference_calibration_reference",
        ],

        "scientific_requirements": [
            {
                "requirement": name,

                "previous_status":
                    ledger[name]["status"],

                "proposed_future_artifact":
                    artifact,

                "currently_independently_qualified":
                    False,

                "independent_validation_required":
                    True,
            }
            for name, artifact
            in sorted(REQUIRED_ARTIFACTS.items())
        ],

        "acquisition_stages": stages,

        "current_readiness_denials": gates,

        "existing_recordings_must_remain_unchanged":
            True,

        "raw_recordings_must_remain_local":
            True,

        "physical_timing_qualified": False,

        "independent_6dof_ground_truth_qualified":
            False,

        "sensor_health_labels_authorized": False,

        "estimator_pose_factors_authorized": False,
    }


def main():
    parser = argparse.ArgumentParser()

    for key in ("run", "l15", "l24", "l26", "out"):
        parser.add_argument(
            "--" + key,
            type=Path,
            required=True,
        )

    args = parser.parse_args()

    assert args.run.is_dir()
    assert not args.run.is_symlink()
    assert args.out.is_dir()
    assert not args.out.is_symlink()

    l15 = read_json(args.l15)
    l24 = read_json(args.l24)
    l26 = read_json(args.l26)

    assert l24["l15_report_sha256"] == (
        sha(args.l15)
    )

    assert l26["upstream_sha256"]["l24"] == (
        sha(args.l24)
    )

    assert all(
        x["pose_factors_authorized"] == 0
        for x in (l15, l24, l26)
    )

    first = inventory(
        args.run, l15, l24
    )

    second = inventory(
        args.run, l15, l24
    )

    assert canonical(first) == canonical(second)

    contract = acquisition_contract(l26)

    contract_path = (
        args.out / "l27_acquisition_contract_v1.json"
    )

    with contract_path.open("x") as f:
        f.write(canonical(contract))

    report = {
        "schema":
            "TRUST_ROBOT_L27_MULTIMODAL_EXISTING_EVIDENCE_INVENTORY_V1",

        "implementation_sha256":
            sha(Path(__file__)),

        "upstream_sha256": {
            "l15": sha(args.l15),
            "l24": sha(args.l24),
            "l26": sha(args.l26),
        },

        "contract_sha256":
            sha(contract_path),

        "contract_filename":
            contract_path.name,

        "existing_recording_inventory":
            first,

        "inventory_rederived_identically":
            True,

        "scientific_requirements_unqualified":
            11,

        "readiness_gates_approved":
            0,

        "no_new_sensor_acquisition_performed":
            True,

        "all_original_recordings_preserved":
            True,

        "independent_ground_truth_claim":
            False,

        "cross_sensor_exposure_sync_claim":
            False,

        "health_labels_generated": 0,
        "pose_factors_authorized": 0,
    }

    report_path = (
        args.out / "l27_multimodal_evidence_inventory_v1.json"
    )

    with report_path.open("x") as f:
        f.write(canonical(report))

    for name in (
        "camera",
        "lidar",
        "imu",
        "usd_pose",
    ):
        print(
            "L27_MODALITY=",
            json.dumps({
                "name": name,
                "inventory": first[name],
            }, sort_keys=True),
            flush=True,
        )

    for item in contract["acquisition_stages"]:
        print(
            "L27_ACQUISITION_PRIORITY=",
            json.dumps({
                "stage": item["stage"],
                "objective": item["objective"],
                "completed": False,
            }, sort_keys=True),
            flush=True,
        )

    print("L27_INVENTORY_REDERIVATION=PASS")

    print(
        "L27_REQUIREMENTS_TO_ACQUIRE=",
        len(contract["scientific_requirements"]),
    )

    print(
        "L27_CONTRACT_SHA256=",
        sha(contract_path),
    )

    print(
        "L27_REPORT_SHA256=",
        sha(report_path),
    )

    print("L27_MULTIMODAL_ACQUISITION_PREPARATION=PASS")
    print("QUALIFIED_POSE_FACTORS=0")


if __name__ == "__main__":
    main()
