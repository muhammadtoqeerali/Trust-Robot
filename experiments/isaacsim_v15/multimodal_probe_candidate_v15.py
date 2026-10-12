"""TRUST-ROBOT synthetic multimodal runtime candidate V1."""
import hashlib
import json
import os
from pathlib import Path

E = Path("/home/kios/TRUST_ROBOT_ALI/experiments/nova_clean_baseline_v1")
SCENE = E / "multimodal_scene_v5.usda"
META = E / "multimodal_probe_validation_v15.json"
OUT = E / "multimodal_probe_results_v15"

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

# This file is not approved for automatic execution.
assert os.environ.get("TRUST_ROBOT_SENSOR_PROBE_ENABLE") == "1"
host_netns = os.environ.get("TRUST_ROBOT_HOST_NETNS")
assert host_netns and host_netns.startswith("net:[")
assert os.readlink("/proc/self/ns/net") != host_netns

import socket
assert {name for _, name in socket.if_nameindex()} == {"lo"}, (
    "Unexpected network interface detected"
)
assert not OUT.exists() and not OUT.is_symlink()

validation = json.loads(META.read_text())
assert sha(SCENE) == validation["scene_sha256"]

physics = json.loads(
    (E / "pilot_results_v1/summary_v1.json").read_text()
)
assert physics["samples"] == 60

from isaacsim import SimulationApp

app = SimulationApp({
    "headless": True,
    "width": 160,
    "height": 120,
    "multi_gpu": False,
    "extra_args": [
        "--/crashreporter/dumpDir="
        + str(E / "crash_reports_v15"),
    ],
})

try:
    import carb.settings
    actual_crash_dir = carb.settings.get_settings().get(
        "/crashreporter/dumpDir"
    )
    assert actual_crash_dir == str(E / "crash_reports_v15"), (
        f"Unexpected crash directory: {actual_crash_dir}"
    )
    print("CRASH_DUMP_REDIRECTION=PASS", flush=True)

    import numpy as np
    import omni.usd

    from isaacsim.core.api import World
    from isaacsim.sensors.camera import Camera
    from isaacsim.sensors.physics import IMUSensor
    from isaacsim.sensors.rtx import LidarRtx

    context = omni.usd.get_context()
    assert context.open_stage(str(SCENE))

    stage = context.get_stage()
    assert stage is not None

    base = "/World/RobotProxy/Base"
    mounts = base + "/SensorMounts"

    world = World(
        physics_dt=1.0 / 60.0,
        rendering_dt=1.0 / 60.0,
        stage_units_in_meters=1.0,
    )

    camera = Camera(
        prim_path=mounts + "/FrontCamera",
        resolution=(160, 120),
        frequency=10,
    )

    imu = IMUSensor(
        prim_path=base + "/PilotIMU",
        name="trust_robot_pilot_imu",
        frequency=60,
        translation=np.zeros(3),
        orientation=np.array([1.0, 0.0, 0.0, 0.0]),
    )

    mount_path = (
        mounts + "/Lidar3DMount/PilotRTX"
    )
    assert stage.GetPrimAtPath(mount_path).IsValid()

    lidar = LidarRtx(
        prim_path=mount_path,
        translation=np.zeros(3),
        orientation=np.array([1.0, 0.0, 0.0, 0.0]),
        config_file_name=None,
        **{
            "omni:sensor:Core:scanRateBaseHz": 10.0,
            "omni:sensor:Core:numberOfEmitters": 16,
            "omni:sensor:Core:numberOfChannels": 16,
            "omni:sensor:Core:nearRangeM": 0.2,
            "omni:sensor:Core:farRangeM": 10.0,
            'omni:sensor:Core:scanType': 'SOLID_STATE',
            'omni:sensor:Core:rayType': 'IDEALIZED',
            'omni:sensor:Core:rotationDirection': 'CW',
            'omni:sensor:Core:reportRateBaseHz': 10,
            'omni:sensor:Core:stateResolutionStep': 1,
            'omni:sensor:Core:numLines': 1,
            'omni:sensor:Core:numRaysPerLine': [16],
            'omni:sensor:Core:emitterState:s001:azimuthDeg': [-25.0, -21.66667, -18.33333, -15.0, -11.66667, -8.33333, -5.0, -1.66667, 1.66667, 5.0, 8.33333, 11.66667, 15.0, 18.33333, 21.66667, 25.0],
            'omni:sensor:Core:emitterState:s001:elevationDeg': [-10.0, -8.66667, -7.33333, -6.0, -4.66667, -3.33333, -2.0, -0.66667, 0.66667, 2.0, 3.33333, 4.66667, 6.0, 7.33333, 8.66667, 10.0],
            'omni:sensor:Core:emitterState:s001:fireTimeNs': [0, 10000, 20000, 30000, 40000, 50000, 60000, 70000, 80000, 90000, 100000, 110000, 120000, 130000, 140000, 150000],
            'omni:sensor:Core:emitterState:s001:channelId': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16],
            'omni:sensor:Core:emitterState:s001:bank': [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        },
    )

    lidar_candidates = [
        prim for prim in stage.TraverseAll()
        if prim.GetTypeName() == "OmniLidar"
    ]
    assert len(lidar_candidates) == 1, (
        f"Expected one OmniLidar, found {len(lidar_candidates)}"
    )
    lidar_prim = lidar_candidates[0]
    print(
        "GENERIC_LIDAR_ACTUAL_PATH=" + str(lidar_prim.GetPath()),
        flush=True,
    )
    assert lidar_prim.IsValid(), "Generic RTX LiDAR prim missing"
    assert lidar_prim.GetTypeName() == "OmniLidar", (
        "Unexpected LiDAR prim type"
    )
    assert lidar_prim.HasAPI("OmniSensorGenericLidarCoreAPI"), (
        "Generic LiDAR schema missing"
    )
    assert str(lidar_prim.GetPath()) == mount_path
    assert lidar_prim.GetParent().GetPath().pathString == (
        mounts + "/Lidar3DMount"
    )
    print("ROBOT_MOUNTED_LIDAR_PRIM=PASS", flush=True)
    print("GENERIC_OMNILIDAR_CREATED=PASS", flush=True)



    # Repair the Replicator-generated numRaysPerLine array.
    from pxr import Vt

    rays = lidar_prim.GetAttribute(
        "omni:sensor:Core:numRaysPerLine"
    )
    assert rays.IsValid()
    assert rays.Set(Vt.UIntArray([16]))
    assert list(rays.Get()) == [16]

    print("LIDAR_RAYS_PER_LINE_CORRECTED=PASS", flush=True)

    n_emitters = int(
        lidar_prim.GetAttribute(
            "omni:sensor:Core:numberOfEmitters"
        ).Get()
    )
    n_lines = int(
        lidar_prim.GetAttribute(
            "omni:sensor:Core:numLines"
        ).Get()
    )

    assert n_emitters == 16
    assert n_lines == 1
    assert sum(rays.Get()) == n_emitters

    checked = 0
    for attribute in lidar_prim.GetAttributes():
        name = attribute.GetName()

        if not name.startswith(
            "omni:sensor:Core:emitterState:"
        ):
            continue

        value = attribute.Get()

        if value is None or isinstance(value, (str, bytes)):
            continue

        if hasattr(value, "__len__"):
            assert len(value) in (0, n_emitters), (
                f"Invalid emitter array length: "
                f"{name}={len(value)}"
            )
            checked += 1

    assert checked >= 5

    print(
        f"LIDAR_EMITTER_ARRAYS_CHECKED={checked}",
        flush=True,
    )
    print("LIDAR_ALL_ARRAY_LENGTHS=PASS", flush=True)

    expected_lidar_attributes = {'omni:sensor:Core:scanRateBaseHz': 10.0, 'omni:sensor:Core:numberOfEmitters': 16, 'omni:sensor:Core:numberOfChannels': 16, 'omni:sensor:Core:nearRangeM': 0.2, 'omni:sensor:Core:farRangeM': 10.0, 'omni:sensor:Core:scanType': 'SOLID_STATE', 'omni:sensor:Core:rayType': 'IDEALIZED', 'omni:sensor:Core:rotationDirection': 'CW', 'omni:sensor:Core:reportRateBaseHz': 10, 'omni:sensor:Core:stateResolutionStep': 1, 'omni:sensor:Core:numLines': 1, 'omni:sensor:Core:numRaysPerLine': [16], 'omni:sensor:Core:emitterState:s001:azimuthDeg': [-25.0, -21.66667, -18.33333, -15.0, -11.66667, -8.33333, -5.0, -1.66667, 1.66667, 5.0, 8.33333, 11.66667, 15.0, 18.33333, 21.66667, 25.0], 'omni:sensor:Core:emitterState:s001:elevationDeg': [-10.0, -8.66667, -7.33333, -6.0, -4.66667, -3.33333, -2.0, -0.66667, 0.66667, 2.0, 3.33333, 4.66667, 6.0, 7.33333, 8.66667, 10.0], 'omni:sensor:Core:emitterState:s001:fireTimeNs': [0, 10000, 20000, 30000, 40000, 50000, 60000, 70000, 80000, 90000, 100000, 110000, 120000, 130000, 140000, 150000], 'omni:sensor:Core:emitterState:s001:channelId': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16], 'omni:sensor:Core:emitterState:s001:bank': [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]}

    applied = lidar_prim.GetAppliedSchemas()
    assert "OmniSensorGenericLidarCoreEmitterStateAPI:s001" in applied, (
        f"Emitter-state schema not applied: {applied}"
    )

    for key, wanted in expected_lidar_attributes.items():
        attr = lidar_prim.GetAttribute(key)
        assert attr.IsValid(), f"Missing LiDAR attribute: {key}"
        actual = attr.Get()
        assert actual is not None, f"Unset LiDAR attribute: {key}"

        if isinstance(wanted, list):
            np.testing.assert_allclose(
                list(actual), wanted, rtol=1e-5, atol=1e-4,
                err_msg=key,
            )
        elif isinstance(wanted, (float, int)):
            np.testing.assert_allclose(
                actual, wanted, rtol=1e-5, atol=1e-4,
                err_msg=key,
            )
        else:
            assert str(actual) == wanted, (
                f"Unexpected {key}: {actual!r} != {wanted!r}"
            )

    print("LIDAR_USD_ATTRIBUTES=PASS", flush=True)
    print("LIDAR_EMITTER_ARRAYS=16", flush=True)

    world.reset()

    camera.initialize()
    imu.initialize()
    lidar.initialize()

    lidar.attach_annotator(
        "IsaacExtractRTXSensorPointCloudNoAccumulator"
    )

    rgba = None
    points = None
    imu_rows = []
    camera_step_time = None
    lidar_step_time = None
    lidar_rendering_time = None

    from pxr import Usd, UsdGeom
    camera_series = []
    lidar_series = []
    pose_series = []
    base_prim = stage.GetPrimAtPath(base)
    assert base_prim.IsValid()

    from pxr import Gf, UsdPhysics

    assert bool(
        UsdPhysics.RigidBodyAPI(
            base_prim
        ).GetKinematicEnabledAttr().Get()
    )

    movement_ops = [
        op for op in UsdGeom.Xformable(
            base_prim
        ).GetOrderedXformOps()
        if op.GetOpType() == UsdGeom.XformOp.TypeTranslate
    ]
    assert len(movement_ops) == 1

    move_op = movement_ops[0]
    # Diagnose the actual USD value after world.reset().
    live_raw = move_op.Get()

    print(
        "RUNTIME_TRANSLATION_TYPE=",
        type(live_raw).__name__,
        flush=True
    )
    print(
        "RUNTIME_TRANSLATION_REPR=",
        repr(live_raw),
        flush=True
    )
    print(
        "RUNTIME_TRANSLATION_ATTR_TYPE=",
        str(move_op.GetAttr().GetTypeName()),
        flush=True
    )

    try:
        live_components = [
            float(component) for component in live_raw
        ]
        print(
            "RUNTIME_TRANSLATION_COMPONENTS=",
            live_components,
            flush=True
        )
        print(
            "RUNTIME_TRANSLATION_COMPONENT_COUNT=",
            len(live_components),
            flush=True
        )
    except Exception as exc:
        print(
            "RUNTIME_TRANSLATION_READ_ERROR=",
            repr(exc),
            flush=True
        )

    # Controlled motion origin comes from the independently
    # inspected and hashed USD scene, not the runtime read.
    initial_xyz = np.array(
        [0.0, 0.0, 0.3],
        dtype=np.float64
    )
    assert initial_xyz.shape == (3,)
    assert np.all(np.isfinite(initial_xyz))

    print(
        "INITIAL_KINEMATIC_TRANSLATION_M=",
        initial_xyz.tolist(),
        flush=True
    )
    print("KINEMATIC_TRANSLATION_SHAPE=PASS", flush=True)

    mounted_lidar_prim = stage.GetPrimAtPath(mount_path)
    assert mounted_lidar_prim.IsValid()

    for step in range(90):
        # Scripted kinematic forward translation, 4 mm per step.
        commanded = initial_xyz.copy()
        commanded[0] += 0.004 * (step + 1)

        assert move_op.Set(
            Gf.Vec3d(*[float(v) for v in commanded])
        )

        world.step(render=True)
        t = float(world.current_time)
        assert np.isfinite(t)

        transform = UsdGeom.XformCache(
            Usd.TimeCode.Default()
        ).GetLocalToWorldTransform(base_prim)

        position = transform.ExtractTranslation()
        xyz_world = [float(v) for v in position]
        assert np.all(np.isfinite(xyz_world))

        pose_series.append({
            "step": step + 1,
            "simulation_step_time_s": t,
            "usd_world_position_m": xyz_world,
            "pose_source": "USD_COMPOSED_WORLD_TRANSFORM",
            "physics_pose_independently_verified": False,
        })

        fresh_cache = UsdGeom.XformCache(
            Usd.TimeCode.Default()
        )

        lidar_position = fresh_cache.GetLocalToWorldTransform(
            mounted_lidar_prim
        ).ExtractTranslation()

        lidar_xyz = [float(v) for v in lidar_position]
        base_xyz = pose_series[-1]["usd_world_position_m"]

        assert np.all(np.isfinite(lidar_xyz))

        relative_xyz = [
            lidar_xyz[i] - base_xyz[i]
            for i in range(3)
        ]

        pose_series[-1]["lidar_usd_world_position_m"] = (
            lidar_xyz
        )
        pose_series[-1]["base_to_lidar_usd_offset_m"] = (
            relative_xyz
        )

        reading = imu.get_current_frame()

        if reading and reading.get("time") is not None:
            def vector(key):
                value = reading.get(key)
                if value is None:
                    return None
                array = np.asarray(value, dtype=float)
                return array.tolist() if np.all(
                    np.isfinite(array)
                ) else None

            imu_rows.append({
                "step": step + 1,
                "simulation_step_time_s": t,
                "sensor_reported_time": float(reading["time"]),
                "linear_acceleration": vector("lin_acc"),
                "angular_velocity": vector("ang_vel"),
                "orientation": vector("orientation"),
                "frame": base + "/PilotIMU",
                "timestamp_semantics_verified": False,
            })

        if step >= 30 and step % 10 == 0:
            frame = camera.get_rgba()

            if frame is not None:
                arr = np.asarray(frame)
                if (
                    arr.shape == (120, 160, 4)
                    and np.issubdtype(arr.dtype, np.number)
                    and np.all(np.isfinite(arr))
                ):
                    if np.issubdtype(arr.dtype, np.floating):
                        if arr.min() >= 0 and arr.max() <= 1.001:
                            converted = np.rint(
                                np.clip(arr, 0, 1) * 255
                            ).astype(np.uint8)
                        elif arr.min() >= 0 and arr.max() <= 255:
                            converted = np.rint(
                                np.clip(arr, 0, 255)
                            ).astype(np.uint8)
                        else:
                            converted = None
                    else:
                        converted = np.clip(
                            arr, 0, 255
                        ).astype(np.uint8)

                    if converted is not None:
                        rgba = converted.copy()
                        camera_step_time = t
                        camera_series.append({
                            "step": step + 1,
                            "time_s": t,
                            "rgba": rgba.copy(),
                        })

            lidar_frame = lidar.get_current_frame()

            if isinstance(lidar_frame, dict):
                data = lidar_frame.get(
                    "IsaacExtractRTXSensorPointCloudNoAccumulator"
                )

                if isinstance(data, dict):
                    xyz = data.get("data")

                    if xyz is not None:
                        xyz = np.asarray(xyz)

                        if (
                            xyz.ndim == 2
                            and xyz.shape[1] == 3
                            and 0 < len(xyz) <= 200000
                            and np.all(np.isfinite(xyz))
                        ):
                            points = xyz.astype(np.float32).copy()
                            lidar_step_time = t
                            lidar_rendering_time = lidar_frame.get(
                                "rendering_time"
                            )
                            lidar_series.append({
                                "step": step + 1,
                                "time_s": t,
                                "rendering_time_raw": (
                                    str(lidar_rendering_time)
                                    if lidar_rendering_time is not None
                                    else None
                                ),
                                "xyz": points.copy(),
                            })


    robot_dx = (
        pose_series[-1]["usd_world_position_m"][0]
        - pose_series[0]["usd_world_position_m"][0]
    )

    lidar_dx = (
        pose_series[-1]["lidar_usd_world_position_m"][0]
        - pose_series[0]["lidar_usd_world_position_m"][0]
    )

    offsets = np.asarray([
        row["base_to_lidar_usd_offset_m"]
        for row in pose_series
    ], dtype=float)

    offset_drift = float(np.max(
        np.linalg.norm(offsets - offsets[0], axis=1)
    ))

    assert robot_dx >= 0.20, (
        f"Robot did not follow kinematic trajectory: {robot_dx}"
    )
    assert abs(lidar_dx - robot_dx) < 0.01, (
        "LiDAR world transform did not follow robot"
    )
    assert offset_drift < 0.001, (
        "Robot-to-LiDAR USD transform changed"
    )

    print(
        "KINEMATIC_ROBOT_DX_M=", robot_dx, flush=True
    )
    print(
        "MOUNTED_LIDAR_DX_M=", lidar_dx, flush=True
    )
    print(
        "LIDAR_RELATIVE_OFFSET_DRIFT_M=",
        offset_drift, flush=True
    )
    print(
        "DYNAMIC_USD_MOUNT_CONSISTENCY=PASS",
        flush=True
    )

    if rgba is not None:
        rgb = rgba[:, :, :3]
        rgb_colors = int(
            np.unique(rgb.reshape(-1, 3), axis=0).shape[0]
        )
        nonblack = float(
            np.mean(np.any(rgb > 0, axis=2))
        )
    else:
        rgb_colors = 0
        nonblack = 0.0

    print("CAMERA_RGB_UNIQUE_COLORS=", rgb_colors, flush=True)
    print("CAMERA_NONBLACK_FRACTION=", nonblack, flush=True)

    assert rgb_colors >= 2 and nonblack >= 0.01, (
        "Camera RGB remains black or uniform"
    )

    expected_steps = list(range(31, 82, 10))
    assert [r["step"] for r in camera_series] == expected_steps
    assert [r["step"] for r in lidar_series] == expected_steps
    assert len(pose_series) == 90

    for record in camera_series:
        rgb = record["rgba"][:, :, :3]
        assert np.mean(np.any(rgb > 0, axis=2)) >= 0.01

    for record in lidar_series:
        cloud = record["xyz"]
        assert cloud.ndim == 2 and cloud.shape[1] == 3
        assert len(cloud) > 0
        assert np.all(np.isfinite(cloud))

    print("TIMESERIES_CAMERA_FRAMES=6", flush=True)
    print("TIMESERIES_LIDAR_FRAMES=6", flush=True)
    print("TIMESERIES_POSE_SAMPLES=90", flush=True)

    print("=== SENSOR RESULTS ===", flush=True)
    print("camera_valid=", rgba is not None, flush=True)
    print("lidar_valid=", points is not None, flush=True)
    print("imu_readings=", len(imu_rows), flush=True)

    assert rgba is not None, "Camera capture missing"
    assert points is not None, "LiDAR capture missing"
    assert imu_rows, "IMU capture missing"

    OUT.mkdir(mode=0o700)

    np.save(OUT / "camera_rgba_v1.npy", rgba)
    np.save(OUT / "lidar_xyz_v1.npy", points)

    frame_dir = OUT / "frames_v15"
    frame_dir.mkdir(mode=0o700)
    capture_index = []

    for index, (cam, lid) in enumerate(
        zip(camera_series, lidar_series), start=1
    ):
        assert cam["step"] == lid["step"]

        camera_file = f"camera_{index:03d}.npy"
        lidar_file = f"lidar_{index:03d}.npy"

        np.save(frame_dir / camera_file, cam["rgba"])
        np.save(frame_dir / lidar_file, lid["xyz"])

        capture_index.append({
            "step": cam["step"],
            "camera_file": "frames_v15/" + camera_file,
            "lidar_file": "frames_v15/" + lidar_file,
            "camera_read_step_time_s": cam["time_s"],
            "lidar_read_step_time_s": lid["time_s"],
            "lidar_rendering_time_raw": lid["rendering_time_raw"],
            "lidar_points": int(len(lid["xyz"])),
            "acquisition_timing_verified": False,
            "cross_sensor_synchronization_verified": False,
        })

    with (OUT / "capture_index_v15.json").open("x") as f:
        json.dump(capture_index, f, indent=2)
        f.write("\n")

    with (OUT / "base_pose_series_v15.jsonl").open("x") as f:
        for record in pose_series:
            f.write(json.dumps(record) + "\n")

    with (OUT / "imu_v1.jsonl").open("x") as f:
        for row in imu_rows:
            f.write(json.dumps(row) + "\n")

    result = {
        "schema": "TRUST_ROBOT_MULTIMODAL_PROBE_V1",
        "status": "RUNTIME_SMOKE_TEST_ONLY",
        "sequence_camera_frames": 6,
        "sequence_lidar_frames": 6,
        "usd_pose_samples": 90,
        "lidar_mounted_to_robot": True,
        "dynamic_lidar_mount_verified": False,
        "usd_mount_motion_consistency_verified": True,
        "kinematic_robot_dx_m": float(robot_dx),
        "lidar_usd_dx_m": float(lidar_dx),
        "relative_offset_max_drift_m": offset_drift,
        "physical_motion_equivalence_verified": False,
        "independent_ground_truth_verified": False,
        "robot_model": "SIMPLIFIED_PROXY",
        "data_origin": "SYNTHETIC",
        "camera_shape": list(rgba.shape),
        "lidar_point_count": int(len(points)),
        "imu_reading_count": len(imu_rows),
        "camera_step_time_s": camera_step_time,
        "lidar_step_time_s": lidar_step_time,
        "lidar_rendering_time": (
            str(lidar_rendering_time)
            if lidar_rendering_time is not None else None
        ),
        "lidar_configuration": "GenericOmniLidar_16Emitter_Test",
        "lidar_prim_path": str(lidar_prim.GetPath()),
        "lidar_mounted_to_robot": True,
        "physical_hesai_equivalence": False,
        "timestamp_semantics_verified": False,
        "cross_sensor_synchronization_verified": False,
        "calibration_verified": False,
        "scientific_validation_complete": False,
    }

    with (OUT / "summary_v1.json").open("x") as f:
        json.dump(result, f, indent=2)
        f.write("\n")

    print("MULTIMODAL_RUNTIME=PASS", flush=True)

except BaseException:
    import traceback
    traceback.print_exc()
    print("SENSOR_RUNTIME_EXCEPTION=YES", flush=True)
    raise
finally:
    app.close()
