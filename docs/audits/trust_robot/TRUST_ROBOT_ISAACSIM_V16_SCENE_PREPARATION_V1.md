# TRUST-ROBOT Isaac Sim V16 offline scene preparation

Status: offline development candidate, not yet
qualified through Isaac Sim rendering or sensor execution.

## Shared workstation protection

All new experiment artifacts are placed under
/home/kios/TRUST_ROBOT_ALI.

The existing Isaac Sim installation, CUDA environment,
ROS installations and original V15 recordings remain
unchanged by this development phase.

No simulator, GPU, network sensor or robot is accessed.

## Implementation

A new deterministic scene generator creates 80
high-contrast geometric markers at three depth levels.

The original V15 USDA scene remains unchanged.

The preserved USDA defines the camera, LiDAR and IMU
mounting structure. The PilotIMU runtime object is
constructed by the original V15 Python simulator script,
rather than being present as a PilotIMU USDA prim.

The new scene is not a validated physical robot model.

## Scientific limitations

Generated marker geometry does not establish actual
camera visibility or eligible image correspondences.

No V16 simulated camera image has been captured.

No camera motion factor, LiDAR registration result,
IMU preintegration output or fused trajectory is claimed.

No measured simulation localization performance exists.

No real sensor-health labels or trained health-model
outputs have been generated.

Physical sensor calibration, timing and real-world
resilience remain unverified.

## Next phase

Perform an isolated Isaac Sim V16 scene load and
camera-observability qualification before implementing
the extended simulation sensor recording.

Runtime caches, logs, crash reports, scratch files and
other writable outputs must stay inside the dedicated
TRUST_ROBOT_ALI workspace.

The published scientific freezes and existing visual
thresholds remain unchanged.
