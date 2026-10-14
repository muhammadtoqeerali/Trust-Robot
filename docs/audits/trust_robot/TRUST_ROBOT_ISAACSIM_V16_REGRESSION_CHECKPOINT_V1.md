# TRUST-ROBOT — Isaac Sim V16 runtime regression checkpoint

Status: **diagnostic regression confirmed; cause unresolved**.

## Verified GitHub predecessor

Branch: `kios-isaacsim-v15-integration`

V16.1 predecessor:
`cfe72a35b1854dc3562e68613ab84f714443a272`

V16.1 published offline scene preparation: 80 deterministic
high-contrast synthetic markers. Scene rendering has **not**
been qualified.

## Successful historical V15 (October 12, 2026)

Preserved log:

`/home/kios/TRUST_ROBOT_ALI/experiments/nova_clean_baseline_v1/multimodal_runtime_v15.log`

SHA-256:

`b7c0e5b64186ab619173ceb7f0b2869334de7ccbd120b8928a35fa2902d31878`

Recorded and offline-validated synthetic data:

- 6 camera frames, 120 x 160 RGBA
- 6 generic RTX LiDAR scans
- 90 IMU records
- 90 composed USD pose samples
- 0.356 m scripted motion
- 0.0 m LiDAR mount-offset drift

Original source and compact evidence are preserved in
`experiments/isaacsim_v15/`.

Historical GLFW/display warnings were present despite success.
Do not attribute the new failure to these warnings alone.

## October 14, 2026 regression

The **original V15 scene**, run inside the current sandbox,
also fails.

Observed current-runtime results:

- 6 camera samples with shape `[0]`, not black images
- 0 accepted camera frames
- 0 accepted LiDAR scans
- 90 accepted IMU readings
- 90 LiDAR `Reference time is 0/0` warnings
- 0 complete successful recordings

The V16 enriched scene fails similarly.

The sandbox entropy-device repair successfully allowed Isaac Sim
to start. Project-local Kit and derived-data caches eliminated
identified cache-write errors but did not recover sensors.

Explicit `timeline.play()` did not recover the sensors.

Timeline experiment:

- `timeline.is_playing()`: true before and after intervention
- Reported timeline time: approximately -0.016667 seconds
- `world.current_time`: advanced to 1.5333 seconds
- No sensor recovery

The clocks were not jointly captured in the historical
successful run. Their divergence is **observed**, not proven
causal.

Current focus: application updates, asynchronous RTX sensor
capture, and reproducibility of historical launch behavior.

The original V15 launch command and exact namespace configuration
are not preserved as a verified GitHub executable recipe.
Do not invent or claim to have reproduced them.

## Safety and scientific boundaries

All new local artifacts must remain in
`/home/kios/TRUST_ROBOT_ALI`.

Do not change shared Isaac Sim installations or host settings.
Do not use sudo, kill other users' processes, or contact robots.

Maintain private network, read-only shared filesystem, bounded
GPU execution, and two fresh GPU-resource checks separated by
15 seconds. GNOME Remote Desktop is the only independently
qualified background context, not an unrestricted GPU exception.

The V15 sensor recording remains valid historical synthetic
evidence. It is not physical ground truth.

No metric camera odometry, fused localization performance,
real-world health labels or physical robot tests are established.

## Next work

1. Run the versioned offline regression auditor.
2. Commit the tested diagnostic checkpoint.
3. Develop a fresh, isolated **single-variable** test of
   application-update and sensor capture timing.
4. Require actual camera and LiDAR payload validation before
   advancing V16 visual geometry or multimodal localization.

Do not repeatedly regenerate V15 data or alter the V16 scene
without new evidence.
