"""Offline SHA-bound Isaac Sim V16.6-V16.8 evidence audit."""

import hashlib
import json
import sys
from pathlib import Path

SCENE_SHA = (
    "bad5b801ea0d3d7fe046342bcd25bd5a2d91d9c35ad9071745156ef65a055e3d"
)

CASES = {
    "v16_6": {
        "run": "isaacsim_v16_orchestrator_probe_v1",
        "results": "isaacsim_v16_orchestrator_result_v1",
        "report": "replicator_capture_report_v1.json",
        "script_sha": (
            "b55257852ce6079131f882764372be8bab4c5611de18baf6fcb127a70889075e"
        ),
        "report_sha": (
            "087a188c38f29d019edf63fd39ce43f6bc229890b5a922b0ae57fec138f253cd"
        ),
    },
    "v16_7": {
        "run": "isaacsim_v16_lidar_invalid_point_probe_v1",
        "results": "isaacsim_v16_lidar_invalid_point_result_v1",
        "report": "lidar_workaround_report_v1.json",
        "script_sha": (
            "bbbddc567bf2010679e33103848c863c131ba647b99234d0fe88b91d10cb9111"
        ),
        "report_sha": (
            "3d3216bb0a32fb97ca1b9b325768eb38608d66b244e46f06444de67cb0e10b5e"
        ),
    },
    "v16_8": {
        "run": "isaacsim_v16_sdg_lidar_writer_v1",
        "results": "isaacsim_v16_sdg_lidar_writer_result_v1",
        "report": "sdg_writer_report_v1.json",
        "script_sha": (
            "22013defdb5b827468bb7f2097013aa08b0b12bf43a68850f76a3d8136e51e51"
        ),
        "report_sha": (
            "2a608789481dda0cd537445d202003dbf00a502a699ac4f07080ae3b5866d835"
        ),
    },
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def valid_camera(row):
    return (
        row.get("shape") == [120, 160, 4]
        and row.get("valid_shape") is True
        and row.get("rgb_nonzero_fraction", 0) > 0.01
    )


def qualify(a, b, c):
    """Validate known experimental outcomes, not causality."""

    require(
        a.get("schema")
        == "TRUST_ROBOT_V16_REPLICATOR_CAPTURE_V1",
        "Unexpected V16.6 schema",
    )
    require(
        a.get("intervention")
        == "MANUAL_REPLICATOR_CAPTURE_RT_SUBFRAMES_4",
        "Unexpected V16.6 intervention",
    )
    require(
        len(a.get("manual_capture_events", [])) == 6,
        "Expected six Replicator capture events",
    )

    direct = a.get("direct_rgb_samples", [])

    require(
        len(direct) == 6,
        "Expected six direct RGB samples",
    )
    require(
        sum(valid_camera(x) for x in direct) == 5,
        "Expected five valid direct RGB frames",
    )
    require(
        direct[0].get("shape") == [0],
        "First camera frame should be empty",
    )
    require(
        a.get("valid_direct_rgb_frames") == 5,
        "V16.6 direct camera count mismatch",
    )
    require(
        a.get("accepted_camera_frames") == 5,
        "V16.6 camera count mismatch",
    )
    require(
        a.get("accepted_lidar_scans") == 0,
        "V16.6 LiDAR count mismatch",
    )
    require(
        a.get("accepted_imu_records") == 90,
        "V16.6 IMU count mismatch",
    )
    require(
        a.get("runtime_success_marker") is False,
        "V16.6 must not be marked qualified",
    )

    require(
        b.get("schema")
        == "TRUST_ROBOT_V16_LIDAR_WORKAROUND_V1",
        "Unexpected V16.7 schema",
    )
    require(
        b.get("intervention")
        == "RTX_LIDAR_SKIP_DROPPING_INVALID_POINTS_TRUE",
        "Unexpected V16.7 intervention",
    )
    require(
        b.get("result")
        == "LIDAR_WORKAROUND_NOT_EFFECTIVE",
        "Unexpected V16.7 result",
    )
    require(
        b.get("camera_frames_accepted") == 5,
        "V16.7 camera count mismatch",
    )
    require(
        b.get("lidar_scans_accepted") == 0,
        "V16.7 LiDAR count mismatch",
    )
    require(
        b.get("lidar_geometry_valid_samples") == 0,
        "Unexpected V16.7 valid geometry",
    )
    require(
        b.get("imu_records_accepted") == 90,
        "V16.7 IMU count mismatch",
    )
    require(
        b.get("full_runtime_pass") is False,
        "V16.7 must not be marked qualified",
    )

    geometry = b.get("lidar_geometry_samples", [])

    require(
        len(geometry) == 6,
        "Expected six V16.7 LiDAR samples",
    )
    require(
        all(x.get("shape") == [0] for x in geometry),
        "Unexpected V16.7 LiDAR payload",
    )

    require(
        c.get("schema")
        == "TRUST_ROBOT_V16_SDG_WRITER_TEST_V1",
        "Unexpected V16.8 schema",
    )
    require(
        c.get("intervention")
        == "EVENT_WRITER_ON_EXISTING_LIDAR_ANNOTATOR",
        "Unexpected V16.8 intervention",
    )
    require(
        c.get("classification")
        == "EVENT_WRITER_EXECUTED_WITHOUT_VALID_LIDAR",
        "Unexpected writer classification",
    )
    require(
        c.get("sdg_writer_callback_count") == 5,
        "Expected five LiDAR writer callbacks",
    )
    require(
        c.get("valid_geometry_callback_count") == 0,
        "Unexpected valid writer geometry",
    )
    require(
        c.get("accepted_camera_frames") == 5,
        "V16.8 camera count mismatch",
    )
    require(
        c.get("accepted_cached_lidar_scans") == 0,
        "V16.8 LiDAR count mismatch",
    )
    require(
        c.get("accepted_imu_records") == 90,
        "V16.8 IMU count mismatch",
    )
    require(
        c.get("full_runtime_qualified") is False,
        "V16.8 must not be marked qualified",
    )
    require(
        not c.get("saved_event_clouds"),
        "Unexpected saved LiDAR clouds",
    )

    events = c.get("event_samples", [])

    require(
        len(events) == 5,
        "Expected five stored writer callback records",
    )

    for row in events:
        require(
            row.get("shape") == [0],
            "Unexpected nonempty LiDAR writer payload",
        )
        require(
            row.get("valid_geometry") is False,
            "Unexpected LiDAR geometry status",
        )
        keys = row.get("data_keys", [])
        require(
            "reference_time" in keys
            and "swhFrameNumber" in keys,
            "Missing SDG timing metadata keys",
        )

    return {
        "v16_6": {
            "camera_frames": 5,
            "lidar_scans": 0,
            "imu_records": 90,
            "replicator_capture_events": 6,
        },
        "v16_7": {
            "camera_frames": 5,
            "lidar_scans": 0,
            "imu_records": 90,
            "invalid_point_workaround_effective": False,
        },
        "v16_8": {
            "camera_frames": 5,
            "lidar_scans": 0,
            "imu_records": 90,
            "sdg_writer_callbacks": 5,
            "valid_cloud_callbacks": 0,
        },
        "camera_recovery": "PARTIAL",
        "lidar_recovery": "NOT_ACHIEVED",
        "root_cause": "UNRESOLVED",
        "synchronization_verified": False,
        "complete_runtime_qualified": False,
    }


def load_verified(path, expected_sha):
    require(
        path.is_file() and not path.is_symlink(),
        f"Missing or unsafe input: {path}",
    )
    require(
        sha(path) == expected_sha,
        f"SHA mismatch: {path}",
    )
    return path.read_bytes()


def main():
    if len(sys.argv) != 4:
        raise SystemExit(
            "Usage: auditor WORKSPACE REPO NEW_REPORT_JSON"
        )

    workspace, repo, destination = map(
        Path, sys.argv[1:]
    )

    require(
        workspace == Path("/home/kios/TRUST_ROBOT_ALI"),
        "Unexpected project workspace",
    )
    require(
        repo == workspace / "github_checkout_v15",
        "Unexpected GitHub checkout",
    )
    require(
        destination.parent ==
        workspace / "experiments/"
        "isaacsim_v16_capture_checkpoint_v1",
        "Output must remain inside new checkpoint",
    )
    require(
        not destination.exists()
        and not destination.is_symlink(),
        "Output must be new",
    )

    original_scene = (
        repo / "experiments/isaacsim_v15/"
        "multimodal_scene_v5.usda"
    )
    load_verified(original_scene, SCENE_SHA)

    reports = {}
    provenance = {}

    for label, spec in CASES.items():
        run = workspace / "experiments" / spec["run"]
        result = workspace / "experiments" / spec["results"]

        script_path = (
            run / "multimodal_probe_candidate_v15.py"
        )
        scene_path = run / "multimodal_scene_v5.usda"
        report_path = result / spec["report"]

        load_verified(
            script_path, spec["script_sha"]
        )
        load_verified(scene_path, SCENE_SHA)

        report_data = load_verified(
            report_path, spec["report_sha"]
        )

        reports[label] = json.loads(report_data)

        provenance[label] = {
            "script_path": str(
                script_path.relative_to(workspace)
            ),
            "script_sha256": spec["script_sha"],
            "report_path": str(
                report_path.relative_to(workspace)
            ),
            "report_sha256": spec["report_sha"],
            "scene_sha256": SCENE_SHA,
        }

    findings = qualify(
        reports["v16_6"],
        reports["v16_7"],
        reports["v16_8"],
    )

    result = {
        "schema": (
            "TRUST_ROBOT_ISAACSIM_V16_"
            "CAPTURE_CHECKPOINT_V1"
        ),
        "status": (
            "PARTIAL_CAMERA_RECOVERY_"
            "LIDAR_UNQUALIFIED"
        ),
        "source_commit": (
            "e0d23dae57787df8c9b7727d9db1db3bf27b99f9"
        ),
        "data_origin": "SYNTHETIC",
        "historical_v15_scene_sha256": SCENE_SHA,
        "findings": findings,
        "source_provenance": provenance,
        "gpu_simulator_executed_by_auditor": False,
        "existing_data_modified": False,
        "physical_robot_contact": False,
        "independent_ground_truth_verified": False,
        "v16_scene_qualified": False,
    }

    with destination.open("x") as f:
        json.dump(
            result, f,
            indent=2, sort_keys=True,
            allow_nan=False,
        )
        f.write("\n")

    print("V16_6_CAMERA_RECOVERY=5_OF_6")
    print("V16_7_LIDAR_WORKAROUND=INEFFECTIVE")
    print("V16_8_WRITER_CALLBACKS=5")
    print("V16_8_VALID_LIDAR_CLOUDS=0")
    print("ORIGINAL_V15_SCENE_HASH=VERIFIED")
    print("EXPERIMENT_SOURCE_HASHES=VERIFIED")
    print("EXPERIMENT_REPORT_HASHES=VERIFIED")
    print("CAUSE=UNRESOLVED")
    print("CAPTURE_EVIDENCE_AUDIT=PASS")
    print("REPORT_SHA256=", sha(destination))


if __name__ == "__main__":
    main()
