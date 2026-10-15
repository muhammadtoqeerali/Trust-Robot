# TRUST-ROBOT KIOS V16 L4-L9 checkpoint

This versioned checkpoint contains synthetic LiDAR geometry and registration
engineering studies, not scientifically validated localization.

Read AGENTS.md, docs/TRUST_ROBOT_PROJECT_STATE.md, and:
docs/audits/trust_robot/TRUST_ROBOT_KIOS_V16_L4_L9_GEOMETRY_STABILITY_V1.md

L4: 16-emitter analytic beam-layout comparison.
L5: preserved candidate USD scene, acquisition source and guarded launcher.
L6: successful isolated Isaac Sim capture and sparse-aware geometry analysis.
L7: controlled perturbation-sensitivity comparison.
L8: 192 deterministic perturbation registrations per derivation.
L9: bidirectional and skip-frame SE(3) closure diagnostics.

Only source code, scene, launcher, metadata and compact JSON are published.
No raw .npy/.npz arrays, simulator logs, caches or crash dumps are included.

The L5 acquisition source contains its original absolute KIOS experiment path
for provenance. Do NOT directly execute the repository snapshot.
The L5 launcher is an archived KIOS-local run recipe, not a generic launcher.
Never overwrite previously recorded experiments.

Verify compact checkpoint integrity with:

python3 -B experiments/isaacsim_v16_l4_l9_geometry_stability_v1/verify_checkpoint.py

Raw recordings remain in their original KIOS experiment directories.

The final candidate LiDAR scan contains only two VALID returns.
Physical measurement time, cross-sensor synchronization, calibrated
extrinsics/uncertainty and independent reference ground truth remain
unverified. No ATE/RPE, health labels, scientifically qualified localization
or estimator factor admission is authorized.

Next engineering phase: L10 sparse-final-scan coverage investigation.
