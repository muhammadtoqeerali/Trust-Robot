"""Read-only V15/V16 Isaac Sim regression audit.

The audit does not launch Isaac Sim or access a robot.
It creates exactly one new, project-local JSON report.
"""

import hashlib
import json
import re
import sys
from pathlib import Path

WORKSPACE = Path("/home/kios/TRUST_ROBOT_ALI")
BASELINE = (
    WORKSPACE
    / "experiments/nova_clean_baseline_v1/"
    "multimodal_runtime_v15.log"
)
CONTROL = (
    WORKSPACE
    / "experiments/isaacsim_v16_v15_scene_control_result_v1/"
    "logs/runtime.log"
)
V16 = (
    WORKSPACE
    / "experiments/isaacsim_v16_kit_cache_probe_v1/"
    "logs/runtime.log"
)
TIMELINE = (
    WORKSPACE
    / "experiments/isaacsim_v16_timeline_probe_result_v1/"
    "logs/runtime.log"
)

EXPECTED_CONTROL_SHA = (
    "13fab8d9dd612b58e9fde06cecc5ca9a57f1e46fae66a7bae085a68c0f2b7356"
)
EXPECTED_V16_SHA = (
    "5832af0787cf36e3adb1a6702c68acf0e535db42ef42375765c782902868fe7e"
)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def count_marker(content, marker):
    match = re.search(
        re.escape(marker) + r"\s*(\d+)",
        content,
    )
    return int(match.group(1)) if match else None


def json_lines(content, marker):
    items = []
    for line in content.splitlines():
        if marker not in line:
            continue
        fragment = line.split(marker, 1)[1].strip()
        try:
            items.append(json.loads(fragment))
        except json.JSONDecodeError:
            raise ValueError(
                f"Malformed JSON after {marker}"
            ) from None
    return items


def summarize(content):
    samples = json_lines(
        content, "V16_CAMERA_SAMPLE "
    )
    timeline = json_lines(
        content, "TIMELINE_SAMPLE "
    )

    world_span = None
    timeline_span = None

    if len(timeline) >= 2:
        world_times = [
            float(x["world_time_s"])
            for x in timeline
        ]
        clock_times = [
            float(x["timeline_time_s"])
            for x in timeline
        ]
        world_span = max(world_times) - min(world_times)
        timeline_span = (
            max(clock_times) - min(clock_times)
        )

    return {
        "runtime_pass": (
            "MULTIMODAL_RUNTIME=PASS" in content
            and "SENSOR_RUNTIME_EXCEPTION=YES"
            not in content
        ),
        "historical_camera_success_marker": (
            "TIMESERIES_CAMERA_FRAMES=6" in content
        ),
        "historical_lidar_success_marker": (
            "TIMESERIES_LIDAR_FRAMES=6" in content
        ),
        "camera_samples": samples,
        "empty_camera_samples": sum(
            x.get("shape") == [0]
            for x in samples
        ),
        "accepted_cameras": count_marker(
            content, "V16_CAMERA_ACCEPTED_FRAME_COUNT="
        ),
        "accepted_lidar_scans": count_marker(
            content, "V16_LIDAR_ACCEPTED_SCAN_COUNT="
        ),
        "accepted_imu_records": count_marker(
            content, "V16_IMU_ACCEPTED_RECORD_COUNT="
        ),
        "lidar_invalid_reference_warnings":
            content.count("Reference time is 0/0"),
        "timeline_samples": len(timeline),
        "timeline_playing_in_all_samples": (
            all(x["timeline_playing"] for x in timeline)
            if timeline else None
        ),
        "world_clock_span_s": world_span,
        "timeline_clock_span_s": timeline_span,
        "glfw_warning": (
            "GLFW initialization failed" in content
        ),
        "cache_write_error": (
            "Failed to create local file data store"
            in content
            or (
                "material_cache.json" in content
                and "Read-only file system" in content
            )
        ),
    }


def compare(historical, control, v16, timeline):
    h = summarize(historical)
    c = summarize(control)
    v = summarize(v16)
    t = summarize(timeline)

    assert h["runtime_pass"]
    assert h["historical_camera_success_marker"]
    assert h["historical_lidar_success_marker"]

    assert not c["runtime_pass"]
    assert not v["runtime_pass"]
    assert not t["runtime_pass"]

    for item in (c, v, t):
        assert item["empty_camera_samples"] == 6
        assert item["accepted_cameras"] == 0
        assert item["accepted_lidar_scans"] == 0
        assert item["accepted_imu_records"] == 90
        assert (
            item["lidar_invalid_reference_warnings"]
            == 90
        )

    assert t["timeline_samples"] == 8
    assert t["timeline_playing_in_all_samples"]
    assert t["world_clock_span_s"] > 1.0
    assert abs(t["timeline_clock_span_s"]) < 0.001

    return {
        "schema": (
            "TRUST_ROBOT_ISAACSIM_V16_"
            "REGRESSION_CHECKPOINT_V1"
        ),
        "data_origin": "SYNTHETIC_SIMULATOR_DIAGNOSTIC",
        "status": "REGRESSION_CONFIRMED_CAUSE_UNRESOLVED",
        "historical_v15": h,
        "current_v15_scene_control": c,
        "current_v16": v,
        "timeline_intervention": t,
        "observations": {
            "historical_v15_sensor_acquisition":
                "VERIFIED_PREVIOUSLY",
            "scene_enrichment_necessary_for_failure":
                False,
            "cache_redirection_resolved_sensor_failure":
                False,
            "explicit_timeline_play_resolved_failure":
                False,
            "reported_timeline_clock_nearly_stationary":
                True,
            "timeline_clock_causality_established":
                False,
            "sensor_pipeline_timing_causality_established":
                False,
        },
        "next_hypothesis": (
            "CURRENT_RUNTIME_APPLICATION_UPDATE_"
            "AND_RTX_SENSOR_PIPELINE_TIMING"
        ),
        "gpu_simulator_executed_by_audit": False,
        "existing_recordings_modified": False,
        "physical_robot_contact": False,
        "empirical_health_training_performed": False,
        "complete_v16_qualification": False,
    }


def main():
    if len(sys.argv) != 3:
        raise SystemExit(
            "Usage: script FROZEN_EVIDENCE_JSON NEW_REPORT_JSON"
        )

    frozen_path = Path(sys.argv[1])
    destination = Path(sys.argv[2])

    assert (
        frozen_path.is_file()
        and not frozen_path.is_symlink()
    )
    assert (
        destination.parent
        == WORKSPACE
        / "experiments/isaacsim_v16_regression_checkpoint_v1"
    )
    assert not destination.exists()
    assert not destination.is_symlink()

    frozen = json.loads(frozen_path.read_text())

    assert frozen["camera_frames"] == 6
    assert frozen["lidar_scans"] == 6
    assert frozen["imu_records"] == 90
    assert frozen["usd_pose_samples"] == 90

    paths = [BASELINE, CONTROL, V16, TIMELINE]

    for path in paths:
        assert path.is_file() and not path.is_symlink()

    assert sha(BASELINE) == frozen["runtime_log_sha256"]
    assert sha(CONTROL) == EXPECTED_CONTROL_SHA
    assert sha(V16) == EXPECTED_V16_SHA

    content = [
        path.read_text(errors="replace")
        for path in paths
    ]

    report = compare(*content)

    report["input_sha256"] = {
        str(path.relative_to(WORKSPACE)): sha(path)
        for path in paths
    }
    report["frozen_evidence_sha256"] = sha(frozen_path)
    report["historical_runtime_sha256_verified"] = True

    with destination.open("x") as handle:
        json.dump(
            report, handle,
            indent=2, sort_keys=True,
            allow_nan=False,
        )
        handle.write("\n")

    print("HISTORICAL_V15_EVIDENCE=VERIFIED")
    print("SCENE_ONLY_CAUSE=NOT_SUPPORTED")
    print("CACHE_ONLY_CAUSE=NOT_SUPPORTED")
    print("EXPLICIT_TIMELINE_PLAY=NO_RECOVERY")
    print("TIMELINE_CLOCK_MISMATCH=OBSERVED")
    print("TIMELINE_CAUSALITY=UNPROVEN")
    print("RUNTIME_REGRESSION_AUDIT=PASS")
    print("REPORT_SHA256=", sha(destination))


if __name__ == "__main__":
    main()
