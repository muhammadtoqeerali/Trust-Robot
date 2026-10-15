# TRUST-ROBOT: KIOS Isaac Sim V16.28–V16.29 synthetic recovery freeze (2026-10-15)

**Checkpoint:** six camera frames + six validity-qualified GenericModelOutput LiDAR Cartesian sensor-frame scans + 130 IMU readings + 130 USD-composed poses, with runtime PASS, offline sensor-file PASS and offline provenance PASS. **Not a claim of synchronized physical measurements or scientific localization.**

## Authoritative next-agent location

- Working source/scene and reproduction instructions: `experiments/isaacsim_v16_recovery_v1/README.md`.
- SHA-bound input/output receipt: `experiments/isaacsim_v16_recovery_v1/checkpoint_manifest_v1.json`.
- Source predecessor SHA: `00d04bf69610c36f3bd2bbfb11633a993b9a624f`; local branch `kios-isaacsim-v15-integration`.
- Successful original local RUN: `/home/kios/TRUST_ROBOT_ALI/experiments/isaacsim_v16_readiness_capture_v1` (not in Git); compact reports committed to `experiments/isaacsim_v16_recovery_v1/evidence/`.
- **Do not** use the old `docs/audits/trust_robot/TRUST_ROBOT_ISAACSIM_V16_CAPTURE_RECOVERY_V1.md` as the latest status: it accurately records the earlier PARTIAL recovery, now superseded by this checkpoint. Preserve the old report as history.

## Diagnoses and repairs (do not regress)

- V16.19 GMO decoded nonempty returns on 44 sampled world steps out of 90; later replication could still fail.
- V16.20 before/after Replicator at steps 51/61/71/81: 4 nonempty packets **before**, zero **after**; capture raw GMO before Replicator evaluation.
- V16.21: preserved raw x/y/z arrays and hashes before rendering invalidated the buffer.
- V16.22: all 59 original LiDAR returns project within 1cm of body x=+0.4m; sensor mount nominally inside `Base` visual geometry. Evidence supports **robot self-hits**, not target returns.
- V16.23: mount parent translate `(0,0,0.2)` -> `(1.2,0,1.5)` under a scaled Base. Live composed sensor xyz matched anticipated position; 64/64 forward projections hit external near-face x=1.25m within 3cm; 0 old self-face matches.
- V16.24: raw GMO coordinate semantics explicitly `CoordsType.SPHERICAL`, `FrameOfReference.SENSOR`, `ElementFlags.VALID=64`. 4 valid XYZ frames/64 target points; stationary 55-step rendering alone insufficient.
- V16.25: one `rep.orchestrator.step(rt_subframes=4, delta_time=0, pause_timeline=False)` before stationary warm-up improved camera to 6/6 and LiDAR to 5/6, but startup capture still unreliable; premotion GMO cache empty.
- V16.26/V16.26b: fixed-step six-frame writer failure (`assert [r["step"] for r in lidar_series] == expected_steps`) because step 41 lacked LiDAR. The V16.26 preparation-only source assertion also failed safely. Do not classify exit code zero as success when runtime logs show `AssertionError`.
- **V16.28:** bounded 130-step acquisition, candidates every 10 steps after step 40, choose earliest six consecutive common valid camera/LiDAR samples. Selected **51,61,71,81,91,101**. Saved 6 real RGBA frames and 6 verified sensor-frame XYZ clouds; points **16,16,16,16,16,4**. Target geometry and originating GMO/VALID flags matched; 130 IMU+pose. `MULTIMODAL_RUNTIME=PASS`, offline file checks passed, zero issues.
- **V16.29:** offline audit on exact V16.28 files: pose/IMU read-step time difference 0; LiDAR mount drift ~5.55e-17m; LiDAR timestamp intervals ~0.166666675s; GMO timestamp minus read-step time **+1.033333387s**, stable spread **7.95e-10s**. Timestamp origins not independently calibrated and camera exposure time absent. Audit PASS with zero issues.

## Scientific/safety boundaries

V16.28 recovers a **synthetic proxy** with simplified kinematic movement and a 16-emitter idealized sensor. The final 4-point scan is sparse. Generic LiDAR is not physical Hesai. Sensor clock offset stability is **not proof of absolute clock agreement**, so never silently subtract an offset. Co-indexed read steps are **not proof of camera exposure synchronization**; actual camera exposure time, physical sensor triggering, independent trajectory ground truth, real sensor calibration, and localization/health-model results remain unverified. Do not use the synthetic scans as empirical health labels. No robots were contacted.

Use private read-only `bwrap`, isolated project-local caches, no network, no sudo, no shared installation writes, two GPU checks 15 seconds apart, and bounded execution. All original V15/V16 local experiments must remain immutable. No bulk recordings or raw logs in Git. The next phase is controlled stabilization and separate scientific timestamp/frame validation; only evidence-supported claims should enter future research milestones.
