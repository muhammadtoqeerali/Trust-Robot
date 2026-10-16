"""L28 shadow multimodal acquisition envelope, offline only.

Converts archived recordings into self-describing metadata events.
It does not observe new sensor frames or qualify exposure time,
extrinsics, source authenticity, independent reference, or pose factors.
"""

import argparse
import copy
import hashlib
import json
import math

from collections import Counter
from pathlib import Path

import numpy as np


STEPS = (51, 61, 71, 81, 91, 101)
RUN_ID = "KIOS_L13_RECORDED_SHADOW_V1"


def sha(path):
    assert path.is_file() and not path.is_symlink(), str(path)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable(obj):
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


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


def event_check(events, sensor_fields, reference_fields):
    assert len(events) == 272
    assert len({
        event["event_id"]
        for event in events
    }) == 272

    counts = Counter()

    for event in events:
        kind = event["kind"]

        assert kind in (
            "sensor",
            "scripted_reference",
        )

        assert event["run_id"] == RUN_ID

        assert len(event["payload_sha256"]) == 64
        assert int(event["payload_sha256"], 16) >= 0

        assert len(event["source_file_sha256"]) == 64

        assert event[
            "qualified_physical_exposure_time"
        ] is False

        assert event[
            "independent_source_authenticity_verified"
        ] is False

        assert event["pose_factor_authorized"] is False
        assert event["sensor_health_label_authorized"] is False

        if kind == "sensor":
            assert set(sensor_fields).issubset(event)

            assert event["sensor_modality"] in (
                "camera",
                "lidar",
                "imu",
            )

            assert isinstance(
                event["sequence_number"],
                int,
            )

            assert event["sequence_number"] >= 1

            assert event["exposure_time_definition"] is None
            assert event["provenance_attestation_reference"] is None
            assert event["calibration_version"] is None

            counts[event["sensor_modality"]] += 1

        else:
            assert set(reference_fields).issubset(event)

            assert event["reference_system_id"] == (
                "USD_COMPOSED_SCRIPTED_NOT_INDEPENDENT"
            )

            assert event["orientation_quaternion_wxyz"] is None
            assert event["reference_uncertainty"] is None
            assert event["reference_calibration_reference"] is None
            assert event["independent_reference_verified"] is False

            counts["usd_pose"] += 1

    assert dict(counts) == {
        "usd_pose": 130,
        "imu": 130,
        "camera": 6,
        "lidar": 6,
    }

    return dict(counts)


def negative_controls(events, sensor_fields, reference_fields):
    def must_reject(change):
        probe = copy.deepcopy(events)
        change(probe)

        try:
            event_check(
                probe,
                sensor_fields,
                reference_fields,
            )
        except (
            AssertionError,
            KeyError,
            ValueError,
            TypeError,
        ):
            return

        raise AssertionError("Mutation accepted")

    must_reject(
        lambda es: es[1].update(
            event_id=es[0]["event_id"]
        )
    )

    must_reject(
        lambda es: es[2].pop(
            "payload_sha256"
        )
    )

    must_reject(
        lambda es: es[2].update(
            qualified_physical_exposure_time=True
        )
    )

    must_reject(
        lambda es: es[2].update(
            independent_source_authenticity_verified=True
        )
    )

    must_reject(
        lambda es: es[2].update(
            pose_factor_authorized=True
        )
    )

    must_reject(
        lambda es: es[1].update(
            independent_reference_verified=True
        )
    )

    return 6


def make_sensor(
    modality,
    n,
    source_path,
    source_sha,
    digest,
    step,
    stamp,
    domain,
    frame,
    read_time,
    row_index=None,
):
    return {
        "kind": "sensor",
        "event_id": f"{modality}:{n:03d}",

        "run_id": RUN_ID,
        "sensor_id": f"L13_RECORDED_{modality.upper()}",

        "sensor_modality": modality,
        "sensor_frame_id": frame,

        "sequence_number": n,

        "payload_sha256": digest,

        "sensor_timestamp_raw": stamp,
        "sensor_clock_domain": domain,

        "exposure_time_definition": None,
        "reference_frame_id": None,
        "calibration_version": None,
        "provenance_attestation_reference": None,

        "source_relative_path": source_path,
        "source_file_sha256": source_sha,
        "source_row_1based": row_index,

        "scripted_step": step,
        "scripted_read_step_time_s": read_time,

        "qualified_physical_exposure_time": False,
        "independent_source_authenticity_verified": False,

        "pose_factor_authorized": False,
        "sensor_health_label_authorized": False,
    }


def build(run, p15, p24, p27, contract):
    root = run / "multimodal_probe_results_v15"

    paths = {
        "capture_index": root / "capture_index_v15.json",
        "runtime_summary": root / "summary_v1.json",
        "imu_series": root / "imu_v1.jsonl",
        "usd_pose_series": root / "base_pose_series_v15.jsonl",
    }

    inventory = p27["existing_recording_inventory"]

    for key, path in paths.items():
        assert sha(path) == inventory["source_hashes"][key]

    captures = read_json(paths["capture_index"])
    imus = read_jsonl(paths["imu_series"])
    poses = read_jsonl(paths["usd_pose_series"])
    summary = read_json(paths["runtime_summary"])

    assert len(captures) == 6
    assert len(imus) == len(poses) == 130

    assert summary["sequence_camera_frames"] == 6
    assert summary["sequence_lidar_frames"] == 6

    assert [
        x["step"] for x in captures
    ] == list(STEPS)

    assert [
        x["step"] for x in imus
    ] == [
        x["step"] for x in poses
    ] == list(range(1, 131))

    assert len(p15["scan_file_provenance"]) == 6

    assert len(
        inventory["selected_capture_provenance"]
    ) == 6

    events = []
    captured = 0

    for step in range(1, 131):
        imu = imus[step - 1]
        pose = poses[step - 1]

        assert imu["step"] == pose["step"] == step

        assert float(
            imu["simulation_step_time_s"]
        ) == float(
            pose["simulation_step_time_s"]
        )

        assert imu["timestamp_semantics_verified"] is False
        assert pose["physics_pose_independently_verified"] is False

        imu_time = float(
            imu["sensor_reported_time"]
        )

        assert math.isfinite(imu_time)

        events.append(
            make_sensor(
                "imu",
                step,
                "multimodal_probe_results_v15/imu_v1.jsonl",
                sha(paths["imu_series"]),

                hashlib.sha256(
                    stable(imu).encode()
                ).hexdigest(),

                step,
                imu_time,
                "IMU_REPORTED_CLOCK_UNQUALIFIED",
                None,
                float(imu["simulation_step_time_s"]),
                row_index=step,
            )
        )

        xyz = pose["usd_world_position_m"]

        assert len(xyz) == 3
        assert all(
            math.isfinite(float(value))
            for value in xyz
        )

        events.append({
            "kind": "scripted_reference",
            "event_id": f"usd_pose:{step:03d}",

            "run_id": RUN_ID,

            "reference_system_id":
                "USD_COMPOSED_SCRIPTED_NOT_INDEPENDENT",

            "reference_timestamp_raw":
                float(pose["simulation_step_time_s"]),

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

            "source_file_sha256":
                sha(paths["usd_pose_series"]),

            "source_row_1based": step,

            "payload_sha256":
                hashlib.sha256(
                    stable(pose).encode()
                ).hexdigest(),

            "qualified_physical_exposure_time": False,
            "independent_source_authenticity_verified": False,
            "independent_reference_verified": False,

            "pose_factor_authorized": False,
            "sensor_health_label_authorized": False,
        })

        if step not in STEPS:
            continue

        index = STEPS.index(step)

        row = captures[index]
        evidence = p15["scan_file_provenance"][index]

        previous = inventory[
            "selected_capture_provenance"
        ][index]

        assert (
            row["step"]
            == evidence["step"]
            == previous["step"]
            == step
        )

        assert row["lidar_points"] == 16
        assert evidence["count"] == 16

        for modality in ("camera", "lidar"):
            relative = row[f"{modality}_file"]

            assert relative == (
                f"frames_v15/{modality}_{index+1:03d}.npy"
            )

            path = root / relative
            digest = sha(path)

            with path.open("rb") as stream:
                cloud = np.load(
                    stream,
                    allow_pickle=False,
                )

            if modality == "lidar":
                assert cloud.shape == (16, 3)

                assert digest == evidence["cloud_sha256"]
                assert digest == previous["lidar_sha256_pinned"]

                stamp = evidence[
                    "gmo_timestamp_ns_unqualified"
                ]

                assert row["lidar_rendering_time_raw"] == (
                    f"GMO_SENSOR_TIMESTAMP_NS:{stamp}"
                )

                domain = "GMO_TIMESTAMP_NS_UNQUALIFIED"

                frame = (
                    f"GMO_ID:{evidence['gmo_frame_id']}"
                )

            else:
                assert cloud.shape == (120, 160, 4)

                assert digest == previous[
                    "camera_sha256_local_baseline"
                ]

                stamp = None
                domain = None
                frame = None

            assert abs(
                float(
                    row[f"{modality}_read_step_time_s"]
                )
                - float(
                    pose["simulation_step_time_s"]
                )
            ) < 1e-5

            events.append(
                make_sensor(
                    modality,
                    index + 1,
                    "multimodal_probe_results_v15/" + relative,

                    digest,
                    digest,
                    step,
                    stamp,
                    domain,
                    frame,

                    float(
                        row[f"{modality}_read_step_time_s"]
                    ),
                )
            )

        captured += 1

    assert captured == 6

    sensor_fields = contract["required_sensor_fields"]
    reference_fields = contract["required_reference_fields"]

    counts = event_check(
        events,
        sensor_fields,
        reference_fields,
    )

    negatives = negative_controls(
        events,
        sensor_fields,
        reference_fields,
    )

    return events, counts, negatives, paths


def main():
    parser = argparse.ArgumentParser()

    for name in (
        "run", "l15", "l24",
        "l27", "contract", "out",
    ):
        parser.add_argument(
            "--" + name,
            required=True,
            type=Path,
        )

    args = parser.parse_args()

    assert args.out.is_dir()
    assert not args.out.is_symlink()

    l15 = read_json(args.l15)
    l24 = read_json(args.l24)
    l27 = read_json(args.l27)
    contract = read_json(args.contract)

    assert l24["l15_report_sha256"] == sha(args.l15)

    assert l27["upstream_sha256"]["l24"] == sha(args.l24)
    assert l27["upstream_sha256"]["l15"] == sha(args.l15)

    assert l27["contract_sha256"] == sha(args.contract)

    assert l27["pose_factors_authorized"] == 0
    assert l24["pose_factors_authorized"] == 0
    assert l15["pose_factors_authorized"] == 0

    assert len(contract["required_sensor_fields"]) == 12
    assert len(contract["required_reference_fields"]) == 9
    assert len(contract["scientific_requirements"]) == 11

    assert contract["status"] == (
        "DESIGN_ONLY_NOT_AN_EXECUTED_ACQUISITION"
    )

    first, counts, negatives, paths = build(
        args.run,
        l15,
        l24,
        l27,
        contract,
    )

    second, _, _, _ = build(
        args.run,
        l15,
        l24,
        l27,
        contract,
    )

    assert [
        stable(x) for x in first
    ] == [
        stable(x) for x in second
    ]

    events_path = (
        args.out
        / "l28_shadow_acquisition_events_v1.jsonl"
    )

    with events_path.open("x") as stream:
        for event in first:
            stream.write(stable(event) + "\n")

    manifest = {
        "schema":
            "TRUST_ROBOT_L28_SHADOW_ACQUISITION_MANIFEST_V1",

        "run_id": RUN_ID,

        "capture_mode":
            "FROZEN_RECORDED_REPLAY_NOT_NEW_CAPTURE",

        "event_file": events_path.name,
        "event_file_sha256": sha(events_path),

        "event_count": len(first),

        "event_counts_by_modality": counts,

        "upstream_sha256": {
            name: sha(getattr(args, name))
            for name in (
                "l15", "l24", "l27", "contract"
            )
        },

        "input_file_sha256": {
            key: sha(value)
            for key, value in paths.items()
        },

        "evidence_status": {
            "independent_payload_attestation": False,
            "qualified_sensor_exposure_timing": False,
            "qualified_cross_sensor_sync": False,
            "qualified_rig_extrinsics": False,
            "independent_6dof_reference": False,
            "sensor_health_labels_authorized": False,
            "pose_factors_authorized": 0,
        },
    }

    manifest_path = (
        args.out
        / "l28_shadow_acquisition_manifest_v1.json"
    )

    with manifest_path.open("x") as stream:
        stream.write(
            json.dumps(
                manifest,
                indent=2,
                sort_keys=True,
                allow_nan=False,
            ) + "\n"
        )

    report = {
        "schema":
            "TRUST_ROBOT_L28_SHADOW_ACQUISITION_VALIDATION_V1",

        "implementation_sha256":
            sha(Path(__file__)),

        "manifest_file_sha256":
            sha(manifest_path),

        "events_file_sha256":
            sha(events_path),

        "event_counts_by_modality": counts,
        "event_count": len(first),

        "in_memory_negative_controls_rejected":
            negatives,

        "two_derivations_identical": True,

        "raw_recordings_unchanged": True,
        "new_isaac_sim_capture_performed": False,

        "independent_6dof_reference_verified": False,
        "physical_exposure_sync_verified": False,

        "health_labels_generated": 0,
        "pose_factors_authorized": 0,
    }

    report_path = (
        args.out
        / "l28_shadow_acquisition_validation_v1.json"
    )

    with report_path.open("x") as stream:
        stream.write(
            json.dumps(
                report,
                indent=2,
                sort_keys=True,
                allow_nan=False,
            ) + "\n"
        )

    print(
        "L28_EVENT_COUNTS=",
        json.dumps(counts, sort_keys=True),
    )

    print(
        "L28_NEGATIVE_CONTROLS_REJECTED=",
        negatives,
    )

    print("L28_TWO_DERIVATIONS=PASS")

    print(
        "L28_EVENT_FILE_SHA256=",
        sha(events_path),
    )

    print(
        "L28_MANIFEST_SHA256=",
        sha(manifest_path),
    )

    print(
        "L28_REPORT_SHA256=",
        sha(report_path),
    )

    print("L28_SHADOW_ACQUISITION_IMPLEMENTATION=PASS")
    print("QUALIFIED_POSE_FACTORS=0")


if __name__ == "__main__":
    main()
