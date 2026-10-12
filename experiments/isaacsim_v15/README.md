# TRUST-ROBOT Isaac Sim V15 synthetic multimodal pilot

## Scope

This package preserves the first-party KIOS V15 Isaac Sim 5.1
synthetic proxy experiment and compact evidence.

The original recorded experiment produced:
- 6 valid camera frames at 120 x 160 RGBA
- 6 generic 16-emitter LiDAR scans
- 90 IMU readings
- 90 USD robot pose samples
- 0.356 m robot and LiDAR world-frame translation
- 0.000 m measured robot-to-LiDAR offset drift

These are USD-composed transform and runtime smoke-test results,
not independent physical ground truth.

## Files

- `multimodal_probe_candidate_v15.py`: unchanged original source
- `multimodal_scene_v5.usda`: unchanged synthetic USD scene
- `multimodal_probe_validation_v15.json`: original source hashes
- `compact_evidence_v15.json`: derived local evidence and file hashes
- `prepare_local_run.py`: prepares a separately versioned local run
- `validate_recording_v15.py`: offline recording validation

The original experiment was executed on the shared KIOS workstation,
with private network isolation, GPU-availability gating and a bounded
Isaac Sim runtime. No physical robot or networked sensor was contacted.

## Reproduction

The original script intentionally contains the verified KIOS path.
It is preserved unchanged for provenance.

Prepare a copy with locally adjusted paths:

    python3 -B experiments/isaacsim_v15/prepare_local_run.py \
      /home/kios/TRUST_ROBOT_ALI/experiments/isaacsim_v15_reproduction_v1

The preparation utility never starts Isaac Sim.

The resulting candidate script has a new SHA-256 recorded in its
local validation manifest. Do not confuse it with the exact original
runtime-verified source.

Actual simulator execution requires the original operating
safeguards: two idle-GPU checks 15 seconds apart, free GPU memory
>=10500 MiB, GPU utilization <=10%, no competing compute processes,
private network namespace, project-local HOME/XDG/TMPDIR, redirected
crash dumps, and a 240-second timeout.

No rerun of the prepared portable copy is claimed here.

Offline validation of an existing original recording:

    python3 -B experiments/isaacsim_v15/validate_recording_v15.py \
      /home/kios/TRUST_ROBOT_ALI/experiments/nova_clean_baseline_v1/multimodal_probe_results_v15

## Scientific limitations

The robot is a simplified scripted kinematic proxy, not a verified
Nova Carter mechanical or dynamical model.

The generic 16-emitter LiDAR is not a validated physical Hesai or
Velodyne device model. Moving-scan physical correctness remains
unverified, including the MotionBVH warning in the runtime log.

Capture read-step times do not demonstrate cross-sensor
synchronization. USD-composed poses are not independent reference
measurements. No factor-graph 6-DoF estimator or trained
modality-health classifier was evaluated.

The V12-V14 failed kinematic pilots remain preserved locally as
historical diagnostics. V15 corrected an erroneous NumPy shape
assertion `(3)` to `(3,)`.

Do not use synthetic pilot results as empirical health labels or
as physical fault/attack-resilience evidence.

Original sensor payloads and runtime logs remain local and are not
part of this source-publication package.
