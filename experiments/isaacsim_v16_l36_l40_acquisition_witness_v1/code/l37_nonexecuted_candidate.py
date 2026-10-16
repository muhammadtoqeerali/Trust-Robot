"""TRUST-ROBOT synthetic multimodal runtime candidate V1."""
import hashlib
import json
import os
from pathlib import Path

E = Path("/home/kios/TRUST_ROBOT_ALI/experiments/isaacsim_v16_l37_witness_candidate_v1")
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

# L37 fail-closed pre-simulator integration gate.
from l37_runtime_guard import preflight_gate as _l37_gate
_l37_gate(E, SCENE, META, OUT)

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
        "--/UJITSO/datastore/localCachePath="
        + str(E / "derived_data_cache"),
        "--/app/tokens/cache="
        + str(E / "kit_cache"),
        "--/app/tokens/data="
        + str(E / "kit_data"),
        "--/app/tokens/logs="
        + str(E / "kit_logs"),
        "--/app/userConfigPath="
        + str(E / "kit_data/user.config.json"),
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

    import carb.tokens

    kit_cache_token = (
        carb.tokens.get_tokens_interface()
        .resolve("${cache}")
    )

    print(
        "V16_KIT_CACHE_TOKEN=",
        kit_cache_token,
        flush=True,
    )

    expected_cache = (E / "kit_cache").resolve()
    actual_cache = Path(kit_cache_token).resolve()

    assert (
        actual_cache == expected_cache
        or expected_cache in actual_cache.parents
    ), (
        "Kit cache token did not resolve "
        "inside private workspace: "
        + str(actual_cache)
    )

    print(
        "V16_KIT_CACHE_TOKEN_IS_PROJECT_LOCAL=PASS",
        flush=True,
    )


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
            'omni:sensor:Core:emitterState:s001:elevationDeg': [-10.0, -0.66667, 8.66667, -3.33333, 6.0, -6.0, 3.33333, -8.66667, 0.66667, 10.0, -2.0, 7.33333, -4.66667, 4.66667, -7.33333, 2.0],
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

    expected_lidar_attributes = {'omni:sensor:Core:scanRateBaseHz': 10.0, 'omni:sensor:Core:numberOfEmitters': 16, 'omni:sensor:Core:numberOfChannels': 16, 'omni:sensor:Core:nearRangeM': 0.2, 'omni:sensor:Core:farRangeM': 10.0, 'omni:sensor:Core:scanType': 'SOLID_STATE', 'omni:sensor:Core:rayType': 'IDEALIZED', 'omni:sensor:Core:rotationDirection': 'CW', 'omni:sensor:Core:reportRateBaseHz': 10, 'omni:sensor:Core:stateResolutionStep': 1, 'omni:sensor:Core:numLines': 1, 'omni:sensor:Core:numRaysPerLine': [16], 'omni:sensor:Core:emitterState:s001:azimuthDeg': [-25.0, -21.66667, -18.33333, -15.0, -11.66667, -8.33333, -5.0, -1.66667, 1.66667, 5.0, 8.33333, 11.66667, 15.0, 18.33333, 21.66667, 25.0], 'omni:sensor:Core:emitterState:s001:elevationDeg': [-10.0, -0.66667, 8.66667, -3.33333, 6.0, -6.0, 3.33333, -8.66667, 0.66667, 10.0, -2.0, 7.33333, -4.66667, 4.66667, -7.33333, 2.0], 'omni:sensor:Core:emitterState:s001:fireTimeNs': [0, 10000, 20000, 30000, 40000, 50000, 60000, 70000, 80000, 90000, 100000, 110000, 120000, 130000, 140000, 150000], 'omni:sensor:Core:emitterState:s001:channelId': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16], 'omni:sensor:Core:emitterState:s001:bank': [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]}

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

    # V16.14: additional observation only.
    # Use the NVIDIA-installed GMO API.
    from isaacsim.sensors.rtx import get_gmo_data
    lidar.attach_annotator("GenericModelOutput")

    print("RAW_GMO_ANNOTATOR_ATTACHED=PASS", flush=True)

    def lidar_buffer_snapshot():
        """Read existing buffers; do not trigger rendering."""
        row = {
            "raw_elements": None,
            "raw_frame_id": None,
            "xyz_count": 0,
            "xyz_shape": None,
            "xyz_finite": False,
        }
        try:
            current = lidar.get_current_frame()
            if not isinstance(current, dict):
                row["state"] = "NO_FRAME_DICT"
                return row

            rendering_frame = current.get("rendering_frame")
            if isinstance(rendering_frame, (list, tuple)):
                row["rendering_frame"] = [
                    int(v) for v in rendering_frame
                ]

            packet = current.get("GenericModelOutput")
            if isinstance(packet, np.ndarray):
                row["raw_packet_bytes"] = int(packet.nbytes)

                if (
                    packet.dtype == np.uint8
                    and packet.flags.c_contiguous
                    and 128 <= packet.nbytes <= 8000000
                ):
                    gmo = get_gmo_data(packet)
                    row["raw_elements"] = int(gmo.numElements)
                    row["raw_frame_id"] = int(gmo.frameId)
                    row["timestamp_ns"] = int(
                        gmo.timestampNs
                    )

            payload = current.get(
                "IsaacExtractRTXSensorPointCloudNoAccumulator"
            )

            if isinstance(payload, dict):
                xyz = payload.get("data")

                if xyz is not None:
                    arr = np.asarray(xyz)
                    row["xyz_shape"] = list(arr.shape)

                    if (
                        arr.ndim == 2
                        and arr.shape[1] == 3
                        and arr.shape[0] <= 200000
                        and np.issubdtype(
                            arr.dtype, np.number
                        )
                    ):
                        row["xyz_count"] = int(
                            arr.shape[0]
                        )
                        row["xyz_finite"] = bool(
                            np.all(np.isfinite(arr))
                        )

                        if (
                            row["xyz_count"] > 0
                            and row["xyz_finite"]
                        ):
                            row["first_xyz"] = [
                                round(float(v), 6)
                                for v in arr[0]
                            ]

            row["state"] = "OBSERVED"
        except Exception as exc:
            row["state"] = "ERROR"
            row["error"] = (
                type(exc).__name__
                + ": " + str(exc)[:160]
            )

        return row



    # V16.5 diagnostic: independently observe the
    # already-created camera render product.
    import omni.replicator.core as rep

    camera_rp = camera.get_render_product_path()
    lidar_rp = lidar.get_render_product_path()

    print(
        "CAMERA_RENDER_PRODUCT_PATH=",
        camera_rp,
        flush=True,
    )
    print(
        "LIDAR_RENDER_PRODUCT_PATH=",
        lidar_rp,
        flush=True,
    )

    assert camera_rp and lidar_rp
    assert stage.GetPrimAtPath(camera_rp).IsValid()
    assert stage.GetPrimAtPath(lidar_rp).IsValid()

    direct_rgb_annotator = (
        rep.AnnotatorRegistry.get_annotator("rgb")
    )
    direct_rgb_annotator.attach([camera_rp])

    # V16.8: observe the existing RTX LiDAR annotator
    # through an event-driven Replicator writer.
    # Sensor configuration and acquisition steps
    # are not altered.

    import omni.graph.core as og

    def dispatcher_snapshot():
        path = (
            "/Render/PostProcess/SDGPipeline/"
            "PostProcessDispatcher"
        )
        result = {
            "node": path,
            "numerator": None,
            "denominator": None,
        }

        try:
            node = og.Controller().node(path)

            for key, field in (
                ("outputs:referenceTimeNumerator", "numerator"),
                ("outputs:referenceTimeDenominator", "denominator"),
            ):
                try:
                    value = node.get_attribute(key).get()
                    result[field] = (
                        int(value) if value is not None else None
                    )
                except Exception as exc:
                    result[field + "_error"] = (
                        type(exc).__name__ + ": "
                        + str(exc)[:100]
                    )

        except Exception as exc:
            result["node_error"] = (
                type(exc).__name__ + ": " + str(exc)[:100]
            )

        return result

    import carb.settings

    setting = carb.settings.get_settings()

    print(
        "LIDAR_OUTPUT_BUFFER_ON_GPU=",
        setting.get(
            "/app/sensors/nv/lidar/outputBufferOnGPU"
        ),
        flush=True,
    )

    class V16SDGLidarEventWriter(rep.Writer):
        def __init__(self):
            self.data_structure = "legacy"
            self.annotators = [
                rep.AnnotatorRegistry.get_annotator(
                    "IsaacExtractRTXSensorPointCloudNoAccumulator"
                )
            ]
            self.calls = 0
            self.valid_calls = 0
            self.saved_clouds = 0

        def write(self, data):
            self.calls += 1
            row = {
                "event": int(self.calls),
                "data_keys": (
                    sorted(str(k) for k in data.keys())
                    if isinstance(data, dict) else []
                ),
                "shape": None,
                "valid_geometry": False,
            }

            try:
                packet = None

                if isinstance(data, dict):
                    for key, value in data.items():
                        if (
                            "IsaacExtractRTXSensorPointCloudNoAccumulator"
                            in str(key)
                        ):
                            packet = value
                            break

                if isinstance(packet, dict):
                    packet = packet.get("data")

                if packet is not None:
                    cloud = np.asarray(packet)

                    row["shape"] = list(cloud.shape)
                    row["dtype"] = str(cloud.dtype)

                    if (
                        cloud.ndim == 2
                        and cloud.shape[1] == 3
                        and len(cloud) > 0
                        and np.issubdtype(
                            cloud.dtype, np.number
                        )
                    ):
                        finite = np.all(
                            np.isfinite(cloud), axis=1
                        )

                        xyz = cloud[finite].astype(float)
                        ranges = np.linalg.norm(
                            xyz, axis=1
                        )

                        valid = xyz[
                            (ranges >= 0.05)
                            & (ranges <= 20.0)
                        ]

                        unique = (
                            np.unique(
                                np.round(valid, 3),
                                axis=0,
                            ).shape[0]
                            if len(valid) else 0
                        )

                        row["point_count"] = int(len(cloud))
                        row["finite_count"] = int(
                            np.count_nonzero(finite)
                        )
                        row["plausible_count"] = int(
                            len(valid)
                        )
                        row["unique_points"] = int(unique)

                        row["valid_geometry"] = bool(
                            len(valid) >= 3
                            and unique >= 2
                            and len(valid) == len(cloud)
                        )

                        if row["valid_geometry"]:
                            self.valid_calls += 1

                            if self.saved_clouds < 6:
                                self.saved_clouds += 1
                                name = (
                                    "event_clouds/"
                                    f"cloud_{self.saved_clouds:03d}.npy"
                                )

                                np.save(
                                    E / name,
                                    cloud.copy(),
                                )

                                row["saved_file"] = name

            except Exception as exc:
                row["callback_error"] = (
                    type(exc).__name__ + ": " + str(exc)
                )


            # Record actual SDG timing values.
            # Compact serialization prevents large buffers
            # or opaque objects from entering logs.
            try:
                import math

                def compact(value, depth=0):
                    if depth > 3:
                        return {"truncated": True}

                    if value is None:
                        return None

                    if isinstance(value, (bool, str)):
                        return (
                            value[:120]
                            if isinstance(value, str)
                            else value
                        )

                    if isinstance(value, (int, float)):
                        if isinstance(value, float) and not (
                            math.isfinite(value)
                        ):
                            return "NONFINITE"
                        return value

                    if isinstance(value, np.generic):
                        return compact(
                            value.item(), depth + 1
                        )

                    if isinstance(value, np.ndarray):
                        result = {
                            "shape": list(value.shape),
                            "dtype": str(value.dtype),
                        }
                        if value.size <= 12:
                            result["values"] = compact(
                                value.tolist(), depth + 1
                            )
                        return result

                    if isinstance(value, (list, tuple)):
                        return [
                            compact(x, depth + 1)
                            for x in value[:12]
                        ]

                    if isinstance(value, dict):
                        keys = list(value)[:12]
                        return {
                            str(k)[:80]: compact(
                                value[k], depth + 1
                            )
                            for k in keys
                        }

                    return {
                        "type": type(value).__name__
                    }

                row["timing_reference"] = compact(
                    data.get("reference_time")
                    if isinstance(data, dict)
                    else None
                )

                row["sdg_frame_number"] = compact(
                    data.get("swhFrameNumber")
                    if isinstance(data, dict)
                    else None
                )

                row["writer_world_time_s"] = float(
                    world.current_time
                )

                row["writer_timeline_time_s"] = float(
                    v16_timeline.get_current_time()
                )

                row["writer_timeline_playing"] = bool(
                    v16_timeline.is_playing()
                )

            except Exception as timing_error:
                row["timing_read_error"] = (
                    type(timing_error).__name__
                    + ": "
                    + str(timing_error)[:160]
                )

            row["dispatcher_reference"] = (
                dispatcher_snapshot()
            )

            # All observations remain project-local.
            with (E / "sdg_writer_events.jsonl").open("a") as f:
                f.write(json.dumps(
                    row, sort_keys=True
                ) + "\n")

            if (
                self.calls <= 8
                or row["valid_geometry"]
                or "callback_error" in row
            ):
                print(
                    "SDG_WRITER_EVENT",
                    json.dumps(row, sort_keys=True),
                    flush=True,
                )

    rep.writers.register_writer(V16SDGLidarEventWriter)

    sdg_writer = rep.writers.get(
        "V16SDGLidarEventWriter"
    )
    sdg_writer.initialize()
    sdg_writer.attach([lidar_rp])

    print("SDG_LIDAR_WRITER_ATTACHED=PASS", flush=True)

    import omni.timeline

    v16_timeline = (
        omni.timeline.get_timeline_interface()
    )

    print(
        "LIDAR_TIMING_MONITOR_ATTACHED=PASS",
        flush=True,
    )


    # Explicit, manual Replicator acquisition.
    rep.orchestrator.set_capture_on_play(False)
    print(
        "REPLICATOR_MANUAL_CAPTURE=ENABLED",
        flush=True,
    )

    print(
        "DIRECT_RGB_ANNOTATOR_ATTACHED=PASS",
        flush=True,
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


    # V16.24: stationary renderer warm-up.
    # The commanded 90-step trajectory is unchanged.
    print("WARMUP_STEPS_REQUESTED=55", flush=True)

    # V16.25 controlled intervention:
    # Initialize Replicator while the robot is stationary.
    # Motion, emitter configuration and recording schedule
    # remain unchanged.
    import omni.replicator.core as rep

    print("REPLICATOR_PRIME_REQUESTED=1", flush=True)

    rep.orchestrator.step(
        rt_subframes=4,
        delta_time=0,
        pause_timeline=False,
    )

    print("REPLICATOR_PRIME_COMPLETED=1", flush=True)


    for warmup_step in range(55):
        world.step(render=True)

    assert world.is_playing()
    print("WARMUP_STEPS_COMPLETED=55", flush=True)
    print(
        "WARMUP_WORLD_TIME_S=",
        float(world.current_time),
        flush=True,
    )


    pre_motion_gmo = {
        "state": "NO_BUFFER",
        "num_elements": None,
    }

    try:
        current = lidar.get_current_frame()
        packet = (
            current.get("GenericModelOutput")
            if isinstance(current, dict)
            else None
        )

        if isinstance(packet, np.ndarray):
            pre_motion_gmo["packet_bytes"] = int(
                packet.nbytes
            )

            if (
                packet.dtype == np.uint8
                and packet.flags.c_contiguous
                and 128 <= packet.nbytes <= 8000000
            ):
                decoded = get_gmo_data(packet)

                pre_motion_gmo["state"] = "DECODED"
                pre_motion_gmo["num_elements"] = int(
                    decoded.numElements
                )
                pre_motion_gmo["frame_id"] = int(
                    decoded.frameId
                )
                pre_motion_gmo["timestamp_ns"] = int(
                    decoded.timestampNs
                )
            else:
                pre_motion_gmo["state"] = (
                    "EMPTY_OR_UNSAFE_BUFFER"
                )

    except Exception as exc:
        pre_motion_gmo["state"] = "READ_ERROR"
        pre_motion_gmo["error"] = (
            type(exc).__name__
            + ": " + str(exc)[:150]
        )

    print(
        "PREMOTION_GMO",
        json.dumps(
            pre_motion_gmo,
            sort_keys=True,
            allow_nan=False,
        ),
        flush=True,
    )

    for step in range(130):
        # Scripted kinematic forward translation, 4 mm per step.
        commanded = initial_xyz.copy()
        commanded[0] += 0.004 * (step + 1)

        assert move_op.Set(
            Gf.Vec3d(*[float(v) for v in commanded])
        )

        world.step(render=True)
        t = float(world.current_time)


        if step >= 40 and step % 10 == 0:
            raw_row = {
                "step": step + 1,
                "state": "NO_RAW_RETURN",
                "num_elements": None,
                "coordinate_semantics": "NOT_YET_VERIFIED",
            }

            try:
                current = lidar.get_current_frame()
                packet = (
                    current.get("GenericModelOutput")
                    if isinstance(current, dict)
                    else None
                )

                if (
                    isinstance(packet, np.ndarray)
                    and packet.dtype == np.uint8
                    and packet.flags.c_contiguous
                    and 128 <= packet.nbytes <= 8000000
                ):
                    gmo = get_gmo_data(packet)
                    n = int(gmo.numElements)

                    raw_row["gmo_coordinate_fields"] = [
                        name for name in dir(gmo)
                        if "coord" in name.lower()
                    ]

                    for field in (
                        "coordsType",
                        "coordinateType",
                        "frameOfReference",
                    ):
                        try:
                            raw_row[field] = str(
                                getattr(gmo, field)
                            )[:100]
                        except AttributeError:
                            pass


                    raw_row["num_elements"] = n
                    raw_row["frame_id"] = int(
                        gmo.frameId
                    )
                    raw_row["timestamp_ns"] = int(
                        gmo.timestampNs
                    )

                    if n > 0:
                        if n > 2048:
                            raise ValueError(
                                "Unexpected element count"
                            )

                        axes = {}

                        for field in ("x", "y", "z"):
                            values = np.asarray(
                                getattr(gmo, field),
                                dtype=np.float32,
                            ).reshape(-1)

                            if values.size < n:
                                raise ValueError(
                                    "Incomplete GMO " + field
                                )

                            values = values[:n].copy()

                            if not np.all(
                                np.isfinite(values)
                            ):
                                raise ValueError(
                                    "Nonfinite GMO " + field
                                )

                            axes[field] = values

                            raw_row[field + "_range"] = [
                                float(values.min()),
                                float(values.max()),
                            ]

                        raw_row["first_values"] = {
                            key: axes[key][:4].tolist()
                            for key in ("x", "y", "z")
                        }

                        filename = (
                            "gmo_pre_step_"
                            + f"{step+1:03d}"
                            + ".npz"
                        )

                        destination = (
                            E / "pre_gmo_samples_v1"
                            / filename
                        )

                        with destination.open("xb") as f:
                            np.savez_compressed(
                                f,
                                x=axes["x"],
                                y=axes["y"],
                                z=axes["z"],
                                frame_id=np.array(
                                    [int(gmo.frameId)],
                                    dtype=np.int64,
                                ),
                                timestamp_ns=np.array(
                                    [int(gmo.timestampNs)],
                                    dtype=np.int64,
                                ),
                            )

                        raw_row["file"] = filename

                        # V16.24: qualify source semantics
                        # BEFORE generating Cartesian XYZ.
                        import importlib

                        coord_enum = getattr(
                            gmo, "elementsCoordsType", None
                        )
                        coord_text = str(coord_enum)
                        frame_text = str(
                            getattr(gmo, "frameOfReference", None)
                        )

                        raw_row["elementsCoordsType"] = coord_text
                        raw_row["frameOfReference"] = frame_text
                        raw_row["xyz_qualified"] = False

                        # Probe the VALID bit from the installed
                        # enum, rather than assuming its value.
                        valid_bit = None
                        try:
                            enum_module = importlib.import_module(
                                type(coord_enum).__module__
                            )
                            enum_class = getattr(
                                enum_module, "ElementFlags"
                            )
                            enum_member = getattr(
                                enum_class, "VALID"
                            )
                            valid_bit = int(
                                getattr(
                                    enum_member,
                                    "value",
                                    enum_member,
                                )
                            )
                        except (
                            ImportError,
                            AttributeError,
                            TypeError,
                            ValueError,
                        ):
                            pass

                        raw_row["valid_flag_bit"] = valid_bit

                        raw_flags = np.asarray(
                            gmo.flags,
                            dtype=np.uint8,
                        ).reshape(-1)

                        if len(raw_flags) < n:
                            raise ValueError(
                                "Incomplete GMO flags"
                            )

                        raw_flags = raw_flags[:n].copy()
                        raw_row["flag_values"] = [
                            int(v) for v in np.unique(
                                raw_flags
                            )
                        ]

                        if (
                            coord_text.endswith(".SPHERICAL")
                            and frame_text.endswith(".SENSOR")
                            and valid_bit is not None
                            and 0 < valid_bit <= 255
                        ):
                            valid = (
                                raw_flags & valid_bit
                            ) != 0

                            raw_row["valid_elements"] = int(
                                np.count_nonzero(valid)
                            )

                            if np.any(valid):
                                az = np.deg2rad(
                                    axes["x"][valid].astype(
                                        np.float64
                                    )
                                )
                                el = np.deg2rad(
                                    axes["y"][valid].astype(
                                        np.float64
                                    )
                                )
                                distance = axes["z"][valid].astype(
                                    np.float64
                                )

                                xyz = np.column_stack((
                                    distance * np.cos(el) * np.cos(az),
                                    distance * np.cos(el) * np.sin(az),
                                    distance * np.sin(el),
                                )).astype(np.float32)

                                if not (
                                    xyz.ndim == 2
                                    and xyz.shape[1] == 3
                                    and np.all(np.isfinite(xyz))
                                    and np.all(distance > 0)
                                ):
                                    raise ValueError(
                                        "Invalid spherical conversion"
                                    )

                                expected_forward = (
                                    1.55
                                    - (0.48 + 0.004 * (step + 1))
                                )

                                matching = int(np.count_nonzero(
                                    np.abs(
                                        xyz[:, 0] - expected_forward
                                    ) <= 0.03
                                ))

                                raw_row["target_matches_3cm"] = (
                                    matching
                                )
                                raw_row["xyz_count"] = int(
                                    len(xyz)
                                )

                                xyz_name = (
                                    f"lidar_xyz_step_{step+1:03d}.npz"
                                )

                                xyz_path = (
                                    E / "qualified_xyz_v1" / xyz_name
                                )

                                with xyz_path.open("xb") as f:
                                    np.savez_compressed(
                                        f,
                                        xyz=xyz,
                                        flags=raw_flags[valid],
                                        frame_id=np.array(
                                            [int(gmo.frameId)],
                                            dtype=np.int64,
                                        ),
                                        timestamp_ns=np.array(
                                            [int(gmo.timestampNs)],
                                            dtype=np.int64,
                                        ),
                                        sensor_world_xyz=np.array(
                                            lidar_xyz,
                                            dtype=np.float64,
                                        ),
                                    )

                                raw_row["xyz_file"] = xyz_name
                                raw_row["xyz_qualified"] = True

                                # V16.26b: preserve qualified GMO XYZ
                                # before the Replicator capture.
                                assert (
                                    not lidar_series
                                    or lidar_series[-1]["step"]
                                    != step + 1
                                )

                                points = xyz.copy()
                                lidar_step_time = t

                                lidar_series.append({
                                    "step": step + 1,
                                    "time_s": t,
                                    "rendering_time_raw": (
                                        "GMO_SENSOR_TIMESTAMP_NS:"
                                        + str(int(gmo.timestampNs))
                                    ),
                                    "xyz": points.copy(),
                                    "source": (
                                        "VALID_FLAGGED_GMO_"
                                        "SPHERICAL_TO_CARTESIAN"
                                    ),
                                })

                                print(
                                    "QUALIFIED_LIDAR_INGESTED",
                                    json.dumps({
                                        "step": step + 1,
                                        "points": int(len(points)),
                                        "frame_id": int(gmo.frameId),
                                        "timestamp_ns": int(
                                            gmo.timestampNs
                                        ),
                                    }, sort_keys=True),
                                    flush=True,
                                )

                                raw_row["coordinate_semantics"] = (
                                    "SPHERICAL_SENSOR_FRAME_VERIFIED"
                                )
                        else:
                            raw_row["qualification_blocker"] = (
                                "COORDINATE_OR_FLAG_ENUM_UNVERIFIED"
                            )

                        raw_row["state"] = "RAW_AXES_SAVED"
                    else:
                        raw_row["state"] = "EMPTY_GMO"

            except Exception as exc:
                raw_row["state"] = "CAPTURE_ERROR"
                raw_row["error"] = (
                    type(exc).__name__
                    + ": " + str(exc)[:160]
                )

            print(
                "PRE_GMO_SNAPSHOT",
                json.dumps(
                    raw_row,
                    sort_keys=True,
                    allow_nan=False,
                ),
                flush=True,
            )

        if step >= 40 and step % 10 == 0:
            observation = lidar_buffer_snapshot()
            observation["step"] = step + 1

            print(
                "LIDAR_BEFORE_REPLICATOR",
                json.dumps(
                    observation, sort_keys=True,
                    allow_nan=False,
                ),
                flush=True,
            )


        # V16.19: observe each world step.
        # This does not trigger another render or capture.
        sweep = {
            "step": step + 1,
            "world_time_s": t,
            "state": "NO_BUFFER",
            "num_elements": None,
        }

        try:
            cached = lidar.get_current_frame()
            packet = (
                cached.get("GenericModelOutput")
                if isinstance(cached, dict)
                else None
            )

            if isinstance(packet, np.ndarray):
                sweep["packet_shape"] = list(packet.shape)
                sweep["packet_bytes"] = int(packet.nbytes)

                if (
                    packet.dtype == np.uint8
                    and packet.flags.c_contiguous
                    and 128 <= packet.nbytes <= 8000000
                ):
                    gmo = get_gmo_data(packet)
                    count = int(gmo.numElements)

                    if not 0 <= count <= 500000:
                        raise ValueError(
                            "GMO element count out of bounds"
                        )

                    sweep["state"] = "DECODED"
                    sweep["num_elements"] = count
                    sweep["frame_id"] = int(gmo.frameId)
                    sweep["timestamp_ns"] = int(
                        gmo.timestampNs
                    )
                else:
                    sweep["state"] = "UNSAFE_OR_EMPTY_BUFFER"
            elif packet is not None:
                sweep["state"] = "UNEXPECTED_BUFFER_TYPE"

        except Exception as exc:
            sweep["state"] = "DECODE_ERROR"
            sweep["error"] = (
                type(exc).__name__
                + ": " + str(exc)[:160]
            )

        print(
            "GMO_SWEEP_ROW",
            json.dumps(sweep, sort_keys=True),
            flush=True,
        )


        if step in (0, 30, 40, 50, 60, 70, 80, 89):
            print(
                "DISPATCHER_WORLD_SAMPLE",
                json.dumps({
                    "step": step + 1,
                    "world_time_s": float(world.current_time),
                    "dispatcher": dispatcher_snapshot(),
                }, sort_keys=True),
                flush=True,
            )

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


        if step in (50, 60, 70, 80):
            print(
                "LIVE_MOUNT_GEOMETRY",
                json.dumps({
                    "step": step + 1,
                    "base_world_xyz": base_xyz,
                    "lidar_world_xyz": lidar_xyz,
                    "expected_lidar_world_x": (
                        0.48 + 0.004 * (step + 1)
                    ),
                    "expected_lidar_world_z": 0.525,
                    "target_near_face_world_x": 1.55,
                }, sort_keys=True),
                flush=True,
            )

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

        if step >= 40 and step % 10 == 0:

            # Request a synthetic-data graph evaluation
            # at the existing six observation steps.
            try:
                rep.orchestrator.step(
                    rt_subframes=4,
                    delta_time=0.0,
                    pause_timeline=False,
                )
                print(
                    "REPLICATOR_CAPTURE_STEP=PASS",
                    step + 1,
                    flush=True,
                )
            except Exception as error:
                print(
                    "REPLICATOR_CAPTURE_STEP=ERROR",
                    step + 1,
                    type(error).__name__,
                    repr(error),
                    flush=True,
                )
                raise


            print(
                "V16_TIMING_CAPTURE_STEP",
                json.dumps({
                    "step": step + 1,
                    "world_time_s":
                        float(world.current_time),
                    "timeline_time_s":
                        float(v16_timeline.get_current_time()),
                    "timeline_playing":
                        bool(v16_timeline.is_playing()),
                }, sort_keys=True),
                flush=True,
            )


            print(
                "DISPATCHER_CAPTURE_SAMPLE",
                json.dumps({
                    "step": step + 1,
                    "world_time_s": float(world.current_time),
                    "timeline_time_s": float(
                        v16_timeline.get_current_time()
                    ),
                    "dispatcher": dispatcher_snapshot(),
                }, sort_keys=True),
                flush=True,
            )


            observation = lidar_buffer_snapshot()
            observation["step"] = step + 1

            print(
                "LIDAR_AFTER_REPLICATOR",
                json.dumps(
                    observation, sort_keys=True,
                    allow_nan=False,
                ),
                flush=True,
            )

            frame = camera.get_rgba()

            # Sample the Replicator annotator without
            # changing the original Camera.get_rgba result.
            try:
                direct = direct_rgb_annotator.get_data()

                if isinstance(direct, dict):
                    direct = direct.get("data")

                if direct is None:
                    direct_row = {
                        "step": step + 1,
                        "state": "NONE",
                    }
                else:
                    raw_rgb = np.asarray(direct)

                    direct_row = {
                        "step": step + 1,
                        "state": "ARRAY",
                        "shape": list(raw_rgb.shape),
                        "dtype": str(raw_rgb.dtype),
                    }

                    valid_rgb = (
                        raw_rgb.ndim == 3
                        and raw_rgb.shape[:2] == (120, 160)
                        and raw_rgb.shape[2] in (3, 4)
                        and np.issubdtype(
                            raw_rgb.dtype, np.number
                        )
                        and np.all(np.isfinite(raw_rgb))
                    )

                    direct_row["valid_shape"] = bool(
                        valid_rgb
                    )

                    if valid_rgb:
                        direct_row["rgb_nonzero_fraction"] = float(
                            np.mean(np.any(
                                raw_rgb[:, :, :3] != 0,
                                axis=2,
                            ))
                        )

                        filename = (
                            "direct_rgb_samples/"
                            f"step_{step+1:03d}.npy"
                        )

                        np.save(
                            E / filename,
                            raw_rgb.copy(),
                        )

                        direct_row["saved_file"] = filename

                print(
                    "DIRECT_RGB_SAMPLE",
                    json.dumps(
                        direct_row, sort_keys=True
                    ),
                    flush=True,
                )

            except Exception as direct_error:
                print(
                    "DIRECT_RGB_SAMPLE_ERROR=",
                    type(direct_error).__name__,
                    repr(direct_error),
                    flush=True,
                )

            # V16 camera diagnosis: observation only.
            # Do not alter the acquired frame.
            if frame is None:
                print(
                    "V16_CAMERA_SAMPLE",
                    json.dumps({
                        "step": step + 1,
                        "state": "NONE",
                    }, sort_keys=True),
                    flush=True,
                )
            else:
                try:
                    diagnostic_array = np.asarray(frame)
                    numeric = bool(np.issubdtype(
                        diagnostic_array.dtype,
                        np.number,
                    ))
                    finite = bool(
                        numeric
                        and np.all(np.isfinite(diagnostic_array))
                    )
                    record = {
                        "step": step + 1,
                        "state": "ARRAY",
                        "shape": list(diagnostic_array.shape),
                        "dtype": str(diagnostic_array.dtype),
                        "finite": finite,
                    }
                    if finite and diagnostic_array.size:
                        record["minimum"] = float(
                            diagnostic_array.min()
                        )
                        record["maximum"] = float(
                            diagnostic_array.max()
                        )
                        if (
                            diagnostic_array.ndim == 3
                            and diagnostic_array.shape[2] >= 3
                        ):
                            rgb_view = diagnostic_array[:, :, :3]
                            record["rgb_nonzero_fraction"] = float(
                                np.mean(np.any(
                                    rgb_view != 0,
                                    axis=2,
                                ))
                            )

                    print(
                        "V16_CAMERA_SAMPLE",
                        json.dumps(record, sort_keys=True),
                        flush=True,
                    )
                except Exception as diagnostic_error:
                    print(
                        "V16_CAMERA_SAMPLE_DIAGNOSTIC_ERROR",
                        repr(diagnostic_error),
                        flush=True,
                    )

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

            # Observe raw GMO data independently
            # of the extracted point-cloud payload.
            gmo_row = {
                "step": step + 1,
                "state": "MISSING",
                "num_elements": None,
            }

            try:
                packet = (
                    lidar_frame.get("GenericModelOutput")
                    if isinstance(lidar_frame, dict)
                    else None
                )

                if packet is not None:
                    gmo_row["packet_type"] = (
                        type(packet).__name__
                    )

                    if isinstance(packet, np.ndarray):
                        gmo_row["packet_shape"] = list(
                            packet.shape
                        )
                        gmo_row["packet_dtype"] = str(
                            packet.dtype
                        )
                        gmo_row["packet_bytes"] = int(
                            packet.nbytes
                        )

                        # Never pass an empty, malformed or
                        # unexpectedly large buffer to the
                        # installed native GMO decoder.
                        if (
                            packet.dtype == np.uint8
                            and packet.flags.c_contiguous
                            and 128 <= packet.nbytes <= 8000000
                        ):
                            gmo_row["state"] = "DECODE_ATTEMPT"

                            gmo = get_gmo_data(packet)

                            n = int(gmo.numElements)

                            if not 0 <= n <= 500000:
                                raise ValueError(
                                    "Unexpected GMO element count"
                                )

                            gmo_row["state"] = "DECODED"
                            gmo_row["num_elements"] = n

                            for field in (
                                "frameId",
                                "timestampNs",
                                "sizeInBytes",
                                "magicNumber",
                                "coordsType",
                                "modality",
                            ):
                                try:
                                    value = getattr(gmo, field)
                                    if hasattr(value, "value"):
                                        value = value.value
                                    if isinstance(
                                        value, (int, float, str)
                                    ):
                                        gmo_row[field] = value
                                    else:
                                        gmo_row[field] = str(
                                            value
                                        )[:90]
                                except Exception as exc:
                                    gmo_row[field + "_error"] = (
                                        type(exc).__name__
                                    )
                        else:
                            gmo_row["state"] = (
                                "BUFFER_NOT_SAFE_TO_DECODE"
                            )
                    else:
                        gmo_row["state"] = (
                            "NON_ARRAY_BUFFER_NOT_DECODED"
                        )

            except Exception as exc:
                gmo_row["state"] = "DECODER_ERROR"
                gmo_row["error"] = (
                    type(exc).__name__
                    + ": " + str(exc)[:160]
                )

            print(
                "RAW_GMO_SAMPLE",
                json.dumps(
                    gmo_row,
                    sort_keys=True,
                    allow_nan=False,
                ),
                flush=True,
            )


            if isinstance(lidar_frame, dict):
                print(
                    "DISPATCHER_CACHED_LIDAR",
                    json.dumps({
                        "step": step + 1,
                        "rendering_frame": (
                            list(lidar_frame["rendering_frame"])
                            if isinstance(
                                lidar_frame.get("rendering_frame"),
                                (list, tuple),
                            )
                            else str(
                                lidar_frame.get("rendering_frame")
                            )
                        ),
                        "dispatcher": dispatcher_snapshot(),
                    }, sort_keys=True),
                    flush=True,
                )


            # Observe RTX payload without modifying it.
            if isinstance(lidar_frame, dict):
                payload = lidar_frame.get(
                    "IsaacExtractRTXSensorPointCloudNoAccumulator"
                )
                if isinstance(payload, dict):
                    xyz_raw = payload.get("data")
                    if xyz_raw is not None:
                        xyz_array = np.asarray(xyz_raw)
                        print(
                            "RTX_LIDAR_PAYLOAD",
                            json.dumps({
                                "step": step + 1,
                                "shape": list(xyz_array.shape),
                                "dtype": str(xyz_array.dtype),
                                "size": int(xyz_array.size),
                            }, sort_keys=True),
                            flush=True,
                        )

            if isinstance(lidar_frame, dict):
                lidar_keys = sorted(
                    str(k) for k in lidar_frame.keys()
                )
            else:
                lidar_keys = []

            print(
                "LIDAR_FRAME_KEYS",
                json.dumps({
                    "step": step + 1,
                    "keys": lidar_keys,
                }, sort_keys=True),
                flush=True,
            )

            if False and isinstance(lidar_frame, dict):
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



    print(
        "SDG_WRITER_CALLBACK_COUNT=",
        sdg_writer.calls,
        flush=True,
    )
    print(
        "SDG_WRITER_VALID_CALLBACKS=",
        sdg_writer.valid_calls,
        flush=True,
    )


    candidate_camera_steps = [
        int(r["step"]) for r in camera_series
    ]
    candidate_lidar_steps = [
        int(r["step"]) for r in lidar_series
    ]

    assert len(candidate_camera_steps) == len(
        set(candidate_camera_steps)
    )
    assert len(candidate_lidar_steps) == len(
        set(candidate_lidar_steps)
    )

    common_steps = sorted(
        set(candidate_camera_steps)
        & set(candidate_lidar_steps)
    )

    print(
        "READINESS_CAMERA_CANDIDATES=",
        candidate_camera_steps,
        flush=True,
    )
    print(
        "READINESS_LIDAR_CANDIDATES=",
        candidate_lidar_steps,
        flush=True,
    )
    print(
        "READINESS_COMMON_STEPS=",
        common_steps,
        flush=True,
    )

    selected_capture_steps = []

    for first in common_steps:
        candidate = [
            first + 10 * i for i in range(6)
        ]
        if all(s in common_steps for s in candidate):
            selected_capture_steps = candidate
            break

    print(
        "READINESS_SELECTED_STEPS=",
        selected_capture_steps,
        flush=True,
    )

    assert len(selected_capture_steps) == 6, (
        "No six consecutive qualified camera-LiDAR "
        "pairs were available"
    )

    camera_series = [
        r for r in camera_series
        if r["step"] in selected_capture_steps
    ]

    lidar_series = [
        r for r in lidar_series
        if r["step"] in selected_capture_steps
    ]

    assert [
        r["step"] for r in camera_series
    ] == selected_capture_steps

    assert [
        r["step"] for r in lidar_series
    ] == selected_capture_steps

    # Keep top-level latest sensor variables
    # consistent with the selected recording.
    rgba = camera_series[-1]["rgba"].copy()
    points = lidar_series[-1]["xyz"].copy()
    camera_step_time = camera_series[-1]["time_s"]
    lidar_step_time = lidar_series[-1]["time_s"]

    print(
        "READINESS_PAIR_SELECTION=PASS",
        flush=True,
    )

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


    print(
        "V16_CAMERA_ACCEPTED_FRAME_COUNT=",
        len(camera_series),
        flush=True,
    )
    print(
        "V16_LIDAR_ACCEPTED_SCAN_COUNT=",
        len(lidar_series),
        flush=True,
    )
    print(
        "V16_IMU_ACCEPTED_RECORD_COUNT=",
        len(imu_rows),
        flush=True,
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

    expected_steps = selected_capture_steps
    assert [r["step"] for r in camera_series] == expected_steps
    assert [r["step"] for r in lidar_series] == expected_steps
    assert len(pose_series) == 130

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
    print("TIMESERIES_POSE_SAMPLES=130", flush=True)

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
        "usd_pose_samples": 130,
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


    # L29: post-capture provenance export.
    # No approved pose factors or health labels.
    import sys as _l29_sys
    _l29_sys.path.insert(0, '/home/kios/TRUST_ROBOT_ALI/experiments/trust_robot_l29_runtime_integration_dev_v1')

    from phase_l29_runtime_adapter import export as _l29_export

    _l29_export(
        E,
        OUT / "l29_runtime_envelope_v1",
        "KIOS_L29_INSTRUMENTED_RUNTIME_V1",
        E / "multimodal_probe_candidate_v15.py",
        Path('/home/kios/TRUST_ROBOT_ALI/experiments/trust_robot_l27_multimodal_acquisition_result_v1/l27_acquisition_contract_v1.json'),
        "SIMULATOR_POST_CAPTURE_UNQUALIFIED",
    )

    print("L29_RUNTIME_ENVELOPE=PASS", flush=True)

    # L37 fail-closed post-export sealing interface.
    from l37_runtime_guard import seal_after_capture as _l37_seal
    _l37_seal(E, OUT / "l29_runtime_envelope_v1")

    print("MULTIMODAL_RUNTIME=PASS", flush=True)

except BaseException:
    import traceback
    traceback.print_exc()
    print("SENSOR_RUNTIME_EXCEPTION=YES", flush=True)
    raise
finally:
    app.close()
