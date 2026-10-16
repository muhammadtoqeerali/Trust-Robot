"""L29 runtime envelope adapter for unqualified synthetic observations.

Runs after sensor files have been written. It validates their
content and emits a self-describing provenance envelope.

No independent source attestation, verified exposure times,
qualified extrinsics, scientific ground truth, health labels,
or estimator pose factors.
"""

import argparse
import copy
import hashlib
import json

from collections import Counter
from pathlib import Path

import numpy as np


STEPS = (51, 61, 71, 81, 91, 101)


def sha(path):
    assert path.is_file() and not path.is_symlink(), str(path)

    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def compact(value):
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def load(path):
    sha(path)
    return json.loads(path.read_text())


def read_rows(path):
    sha(path)

    return [
        json.loads(line)
        for line in path.read_text().splitlines()
        if line.strip()
    ]


def sensor(
    run_id,
    modality,
    number,
    step,
    relative_path,
    digest,
    timestamp,
    clock_domain,
    frame_id,
    read_time,
    row_number=None,
):
    return {
        "kind": "sensor",

        "event_id":
            f"{modality}:{number:03d}",

        "run_id": run_id,

        "sensor_id":
            f"L29_RECORDED_{modality.upper()}",

        "sensor_modality": modality,
        "sensor_frame_id": frame_id,

        "sequence_number": number,

        "payload_sha256": digest,

        "sensor_timestamp_raw": timestamp,
        "sensor_clock_domain": clock_domain,

        "exposure_time_definition": None,
        "reference_frame_id": None,

        "calibration_version": None,
        "provenance_attestation_reference": None,

        "source_relative_path": relative_path,
        "source_file_sha256": None,

        "source_row_1based": row_number,
        "scripted_step": step,

        "scripted_read_step_time_s": read_time,

        "qualified_physical_exposure_time": False,

        "independent_source_authenticity_verified":
            False,

        "pose_factor_authorized": False,

        "sensor_health_label_authorized": False,
    }


def validate_events(events, contract):
    assert len(events) == 272

    assert len({
        item["event_id"]
        for item in events
    }) == 272

    counts = Counter()

    for item in events:
        assert len(item["payload_sha256"]) == 64
        assert len(item["source_file_sha256"]) == 64

        assert item["qualified_physical_exposure_time"] is False

        assert item[
            "independent_source_authenticity_verified"
        ] is False

        assert item["pose_factor_authorized"] is False
        assert item["sensor_health_label_authorized"] is False

        if item["kind"] == "sensor":
            assert set(
                contract["required_sensor_fields"]
            ).issubset(item)

            assert item["sensor_modality"] in (
                "camera",
                "lidar",
                "imu",
            )

            assert item["exposure_time_definition"] is None
            assert item["calibration_version"] is None

            assert item[
                "provenance_attestation_reference"
            ] is None

            counts[item["sensor_modality"]] += 1

        else:
            assert item["kind"] == "scripted_reference"

            assert set(
                contract["required_reference_fields"]
            ).issubset(item)

            assert item[
                "independent_reference_verified"
            ] is False

            assert item[
                "orientation_quaternion_wxyz"
            ] is None

            assert item["reference_uncertainty"] is None

            counts["usd_pose"] += 1

    assert dict(counts) == {
        "imu": 130,
        "usd_pose": 130,
        "camera": 6,
        "lidar": 6,
    }

    return dict(counts)


def negative_controls(events, contract):
    def reject(change):
        test = copy.deepcopy(events)
        change(test)

        try:
            validate_events(test, contract)
        except (
            AssertionError,
            KeyError,
            TypeError,
            ValueError,
        ):
            return

        raise AssertionError(
            "Negative control was incorrectly accepted"
        )

    reject(
        lambda e: e[1].update(
            event_id=e[0]["event_id"]
        )
    )

    reject(
        lambda e: e[2].pop("payload_sha256")
    )

    reject(
        lambda e: e[2].update(
            qualified_physical_exposure_time=True
        )
    )

    reject(
        lambda e: e[2].update(
            independent_source_authenticity_verified=True
        )
    )

    reject(
        lambda e: e[2].update(
            pose_factor_authorized=True
        )
    )

    reject(
        lambda e: e[1].update(
            independent_reference_verified=True
        )
    )

    return 6


def export(
    run,
    output,
    run_id,
    source_script,
    contract_path,
    mode,
):
    assert run.is_absolute()
    assert run.is_dir() and not run.is_symlink()

    assert output.is_absolute()
    assert not output.exists()
    assert not output.is_symlink()

    assert output.parent.is_dir()
    assert not output.parent.is_symlink()

    assert mode in (
        "FROZEN_REPLAY_DRYRUN",
        "SIMULATOR_POST_CAPTURE_UNQUALIFIED",
    )

    assert len(run_id) > 8
    assert all(
        c.isalnum() or c in "_-"
        for c in run_id
    )

    contract = load(contract_path)

    assert len(contract["required_sensor_fields"]) == 12
    assert len(contract["required_reference_fields"]) == 9

    assert contract[
        "estimator_pose_factors_authorized"
    ] is False

    script_hash = sha(source_script)

    scene = run / "multimodal_scene_v5.usda"

    metadata = load(
        run / "multimodal_probe_validation_v15.json"
    )

    assert metadata["scene_sha256"] == sha(scene)
    assert metadata["script_sha256"] == script_hash

    root = run / "multimodal_probe_results_v15"

    index_path = root / "capture_index_v15.json"
    imu_path = root / "imu_v1.jsonl"
    pose_path = root / "base_pose_series_v15.jsonl"
    summary_path = root / "summary_v1.json"

    index = load(index_path)
    imu = read_rows(imu_path)
    poses = read_rows(pose_path)
    summary = load(summary_path)

    assert len(index) == 6
    assert len(imu) == len(poses) == 130

    assert summary["sequence_camera_frames"] == 6
    assert summary["sequence_lidar_frames"] == 6
    assert summary["usd_pose_samples"] == 130

    assert [
        item["step"] for item in index
    ] == list(STEPS)

    assert [
        item["step"] for item in imu
    ] == [
        item["step"] for item in poses
    ] == list(range(1, 131))

    events = []

    for step, (imu_row, pose_row) in enumerate(
        zip(imu, poses),
        start=1,
    ):
        step_time = float(
            pose_row["simulation_step_time_s"]
        )

        assert abs(
            step_time
            - float(imu_row["simulation_step_time_s"])
        ) < 1e-9

        assert imu_row[
            "timestamp_semantics_verified"
        ] is False

        assert pose_row[
            "physics_pose_independently_verified"
        ] is False

        imu_path_relative = (
            "multimodal_probe_results_v15/imu_v1.jsonl"
        )

        imu_event = sensor(
            run_id,
            "imu",
            step,
            step,
            imu_path_relative,

            hashlib.sha256(
                compact(imu_row).encode()
            ).hexdigest(),

            float(imu_row["sensor_reported_time"]),

            "IMU_REPORTED_CLOCK_UNQUALIFIED",
            None,
            step_time,
            row_number=step,
        )

        imu_event["source_file_sha256"] = sha(imu_path)

        events.append(imu_event)

        xyz = pose_row["usd_world_position_m"]

        assert len(xyz) == 3

        assert bool(
            np.isfinite(
                np.asarray(xyz, dtype=float)
            ).all()
        )

        events.append({
            "kind": "scripted_reference",

            "event_id": f"usd_pose:{step:03d}",

            "run_id": run_id,

            "reference_system_id":
                "USD_COMPOSED_SCRIPTED_NOT_INDEPENDENT",

            "reference_timestamp_raw":
                step_time,

            "reference_clock_domain":
                "SCRIPTED_SIM_STEP_SECONDS",

            "reference_frame_id":
                "USD_STAGE_WORLD_NOT_PHYSICALLY_VALIDATED",

            "position_xyz_m": xyz,

            "orientation_quaternion_wxyz": None,

            "reference_uncertainty": None,

            "reference_calibration_reference": None,

            "source_relative_path":
                "multimodal_probe_results_v15/base_pose_series_v15.jsonl",

            "source_file_sha256": sha(pose_path),

            "source_row_1based": step,

            "payload_sha256":
                hashlib.sha256(
                    compact(pose_row).encode()
                ).hexdigest(),

            "qualified_physical_exposure_time": False,

            "independent_source_authenticity_verified":
                False,

            "independent_reference_verified": False,

            "pose_factor_authorized": False,

            "sensor_health_label_authorized": False,
        })

        if step not in STEPS:
            continue

        index_number = STEPS.index(step)
        capture = index[index_number]

        for modality in ("camera", "lidar"):
            relative = (
                f"frames_v15/{modality}_{index_number+1:03d}.npy"
            )

            assert capture[
                f"{modality}_file"
            ] == relative

            data_path = root / relative

            with data_path.open("rb") as stream:
                array = np.load(
                    stream,
                    allow_pickle=False,
                )

            assert array.shape == (
                (120, 160, 4)
                if modality == "camera"
                else (16, 3)
            )

            assert np.isfinite(array).all()

            digest = sha(data_path)

            if modality == "lidar":
                raw_path = (
                    run / "qualified_xyz_v1"
                    / f"lidar_xyz_step_{step:03d}.npz"
                )

                with np.load(
                    raw_path,
                    allow_pickle=False,
                ) as raw:
                    assert np.array_equal(
                        array,
                        raw["xyz"],
                    )

                    assert np.all(
                        (
                            raw["flags"].astype(np.uint64)
                            & 64
                        ) != 0
                    )

                    stamp = int(
                        raw["timestamp_ns"][0]
                    )

                    frame_number = int(
                        raw["frame_id"][0]
                    )

                assert capture[
                    "lidar_rendering_time_raw"
                ] == (
                    f"GMO_SENSOR_TIMESTAMP_NS:{stamp}"
                )

                frame_id = f"GMO_ID:{frame_number}"
                clock = "GMO_TIMESTAMP_NS_UNQUALIFIED"

            else:
                stamp = None
                frame_id = None
                clock = None

            read_time = float(
                capture[
                    f"{modality}_read_step_time_s"
                ]
            )

            assert abs(
                read_time - step_time
            ) < 1e-5

            item = sensor(
                run_id,
                modality,
                index_number + 1,
                step,

                "multimodal_probe_results_v15/"
                + relative,

                digest,
                stamp,
                clock,
                frame_id,
                read_time,
            )

            item["source_file_sha256"] = digest

            events.append(item)

    counts = validate_events(events, contract)

    negative_count = negative_controls(
        events,
        contract,
    )

    output.mkdir(mode=0o700)

    events_path = output / "observations_v1.jsonl"

    with events_path.open("x") as stream:
        for item in events:
            stream.write(compact(item) + "\n")

    manifest = {
        "schema":
            "TRUST_ROBOT_L29_MULTIMODAL_RUNTIME_ENVELOPE_V1",

        "capture_mode": mode,
        "run_id": run_id,

        "event_file": events_path.name,

        "event_file_sha256":
            sha(events_path),

        "event_count": len(events),

        "event_counts_by_modality":
            counts,

        "negative_controls_rejected":
            negative_count,

        "source_acquisition_script_sha256":
            script_hash,

        "scene_sha256":
            sha(scene),

        "contract_sha256":
            sha(contract_path),

        "runtime_file_sha256": {
            "capture_index":
                sha(index_path),

            "summary":
                sha(summary_path),

            "imu_series":
                sha(imu_path),

            "usd_pose_series":
                sha(pose_path),
        },

        "qualified_exposure_sync": False,

        "independent_reference": False,

        "source_authenticity_verified": False,

        "pose_factors_authorized": 0,
    }

    manifest_path = output / "manifest_v1.json"

    with manifest_path.open("x") as stream:
        json.dump(
            manifest,
            stream,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )

        stream.write("\n")

    return {
        "events": str(events_path),
        "manifest": str(manifest_path),
        "count": len(events),
        "counts": counts,
    }


def main():
    parser = argparse.ArgumentParser()

    for key in (
        "run",
        "output",
        "source",
        "contract",
        "run-id",
        "mode",
    ):
        parser.add_argument(
            "--" + key,
            required=True,
        )

    args = parser.parse_args()

    result = export(
        Path(args.run),
        Path(args.output),
        args.run_id,
        Path(args.source),
        Path(args.contract),
        args.mode,
    )

    print(
        "L29_ENVELOPE_RECORDS=",
        result["count"],
        flush=True,
    )

    print(
        "L29_ENVELOPE_COUNTS=",
        json.dumps(
            result["counts"],
            sort_keys=True,
        ),
        flush=True,
    )

    print(
        "L29_ENVELOPE_MANIFEST_SHA256=",
        sha(Path(result["manifest"])),
        flush=True,
    )

    print("L29_ENVELOPE=PASS", flush=True)


if __name__ == "__main__":
    main()
