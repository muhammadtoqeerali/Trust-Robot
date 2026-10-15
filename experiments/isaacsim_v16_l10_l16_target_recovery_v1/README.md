# TRUST-ROBOT KIOS V16 L10-L16 checkpoint

This checkpoint archives synthetic engineering diagnostics.
It does not establish scientifically validated six-DoF localization.

L10-L12 investigate the sparse final LiDAR scan:
- The last frame contained only two raw GMO returns, both valid.
- Late-trajectory returns progressively declined.
- An additional zero-return event occurred at step 92.
- An azimuth-sign convention difference was identified.

L13 created a separate candidate scene, moving the front calibration
cube +0.30 m while preserving the 16-beam configuration and trajectory.

L14 measured six complete 16-return scans in a guarded Isaac Sim run.
The step-92 zero-return event remained.

L15 reproduced five consecutive ICP registration diagnostics,
including the restored 91-to-101 pair.

L16 attempted all 15 unordered scan pairs. All produced diagnostics,
but four- and five-hop direct registrations disagreed with the
composed shorter-range trajectory.

The archived acquisition source contains KIOS-specific absolute paths.
The archived launcher references its original local verifier.
Do not execute these snapshots directly. Future experiments require
new protected run directories and the GPU-safe execution procedure.

Raw .npy/.npz recordings, camera imagery, IMU streams and runtime logs
remain locally on KIOS. They are not published to GitHub.

Physical exposure timing, calibrated sensor uncertainty,
independent ground truth, scientifically validated localization,
health labels, and estimator pose factors remain unverified.

Verify this checkpoint using:

python3 -B experiments/isaacsim_v16_l10_l16_target_recovery_v1/verify_checkpoint.py

Next phase: L17 long-baseline registration ambiguity investigation.
