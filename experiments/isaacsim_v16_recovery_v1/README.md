# Isaac Sim V16.28–V16.29 KIOS six-frame recovery

**Status: reproducible source/scene snapshot of a SUCCESSFUL local synthetic runtime and offline-file validation; NOT a scientifically synchronized or physically validated dataset.**

Read [`AGENTS.md`](../../AGENTS.md), [`TRUST_ROBOT_MASTER_CONTEXT.md`](../../TRUST_ROBOT_MASTER_CONTEXT.md), and the [recovery audit](../../docs/audits/trust_robot/TRUST_ROBOT_ISAACSIM_V16_28_29_RECOVERY_FREEZE_V1.md) first.

## Working recipe (must retain all components)

1. Corrected LiDAR mounting Xform: `Lidar3DMount` translation `(1.2,0,1.5)` under the scaled `Base` cube (nominal world LiDAR position relative to base origin: `(+0.48,0,+0.225)` metres). The original V15 mount `(0,0,0.2)` was inside robot geometry and all 59 original returns were consistent with a front-face self-hit.
2. Keep the **original 16-emitter SOLID_STATE generic OmniLidar** attributes; do not silently swap sensor models.
3. Initialize Replicator with `rep.orchestrator.step(rt_subframes=4, delta_time=0, pause_timeline=False)` **before** 55 stationary `world.step(render=True)` warm-up steps.
4. Use the 130-step scripted robot motion, sampling every ten steps from step 41. Save **raw GMO before** `rep.orchestrator.step` during each candidate capture: later Replicator evaluation was observed to clear previously populated buffers.
5. Interpret `gmo.elementsCoordsType == CoordsType.SPHERICAL`, `frameOfReference == SENSOR`, and the installed `ElementFlags.VALID` bit `64`. GMO x/y/z mean **azimuth degrees / elevation degrees / radius metres**. Convert to sensor-frame Cartesian XYZ with `x=r cos(elev) cos(az)`, `y=r cos(elev) sin(az)`, `z=r sin(elev)`; save only finite VALID returns. No world-frame claim.
6. Collect candidate camera images and qualified LiDAR XYZ separately. **Select the first six consecutive common capture steps spaced ten steps apart** rather than requiring the startup step to work. V16.28 chose `[51,61,71,81,91,101]`.
7. Keep the legacy `IsaacExtractRTXSensorPointCloudNoAccumulator` attachment for diagnostic compatibility, but do **not** use its empty output as the recorder LiDAR input. The qualified GMO-to-XYZ path is the working source.
8. Assert and independently validate six genuine nonblack RGBA images (120x160x4), six sensor-frame XYZ arrays matching source validity-flagged GMO data and calibration-target ranges, 130 IMU and 130 USD pose samples, and persisted index/summary files. Simulator exit code zero alone is not success; require `MULTIMODAL_RUNTIME=PASS` and absence of `SENSOR_RUNTIME_EXCEPTION=YES`.

## Committed files

- `multimodal_probe_candidate_v15.py`: exact SHA-256-pinned V16.28 successful script. The historical KIOS absolute `E` path is preserved intentionally; do not run this file directly from the repository.
- `multimodal_scene_v5.usda`: exact corrected-mount scene from V16.28.
- `multimodal_probe_validation_v15.json` plus `pilot_results_v1/summary_v1.json`: original local source integrity/preflight dependencies.
- `evidence/*.json`: hash-checked compact prior diagnosis, success and timing reports. No raw `.npy`/`.npz` sensor recordings, GPU logs, cache files or secrets are committed.
- `checkpoint_manifest_v1.json`: results and source/report hashes.
- `run_isolated.sh`: guarded KIOS-only sandbox, two GPU checks, 240-second bounded run, and offline validator.
- `prepare_local_run.py`: builds a **new local project-scoped** run copy and updates its source hash, without touching the shared simulator or starting it.
- `verify_local_recording.py`: offline array/flag/geometry/timestamp validator; **does not** establish camera exposure timing or physical synchronization.

## Prepare and independently validate (KIOS only)

```bash
W=/home/kios/TRUST_ROBOT_ALI
R=$W/github_checkout_v15
PY=$W/venvs/isaac_v15_odometry_v1/bin/python
$PY -B $R/experiments/isaacsim_v16_recovery_v1/prepare_local_run.py $W/experiments/isaacsim_v16_recovery_reproduction_NEW_v1
$PY -B $R/experiments/isaacsim_v16_recovery_v1/verify_local_recording.py $W/experiments/isaacsim_v16_readiness_capture_v1
# After preparing a NEW RUN directory, launch it via:
# bash $R/experiments/isaacsim_v16_recovery_v1/run_isolated.sh NEW_RUN_DIR NEW_RESULT_DIR
```

**Preparation is not execution.** Before launching the prepared copy, follow the shared-KIOS GPU/namespace restrictions: `kios` user only; two 15-second-separated GPU checks (>=10,500 MiB free and <=10% utilization); no competing compute except verified immutable GNOME Remote Desktop; new independent RUN/OUT directories; private `bwrap --unshare-net --unshare-user --unshare-pid --unshare-ipc`, read-only root/repo/installation, only RUN/OUT writable; redirected HOME, XDG, TMP, OptiX/CUDA caches; 240s interrupt + 30s kill cap; no sudo, no physical robot, no unisolated simulation. Use the committed `run_isolated.sh` launcher for a new prepared RUN and new OUT. Do not execute the pinned candidate inside this GitHub checkout.

## Explicit limitations and next work

- **V16.28 validated 6 pairs: LiDAR valid-point counts `[16,16,16,16,16,4]`**; the last sample is sparse and remains a quality limitation. Selected startup step 41 was missing in V16.26b; collecting longer and selecting verified pairs resolved the bounded smoke-test requirement.
- **V16.29 timing/provenance audit PASS**, zero issues. Six LiDAR stamps advance at ~0.166666675s per ten motion steps. The GMO minus USD read-step clock difference is ~**+1.033333387 s**, with spread <1e-9s. This is an observed clock-domain relation, **not a calibrated offset**. Never automatically subtract it or claim physical synchronization.
- Camera independent exposure timestamps were **not captured**. Camera–LiDAR cross-sensor sync, calibration quality, moving-ray-time consistency, independent physical ground truth, actual Hesai equivalence, learned sensor-health labels, and localization estimator performance remain **unverified**.
- USD-composed kinematic poses are *not* independently measured reference trajectories.
- Do not overwrite older V15 or V16 experiments. Future development should use new directory names and independent local validation, with versioned evidence and clear gating before claims or further commits.
