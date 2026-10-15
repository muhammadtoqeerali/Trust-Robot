# TRUST-ROBOT Agent Entry Point

Before making any project change, read:

1. `TRUST_ROBOT_MASTER_CONTEXT.md`
2. the TRUST-ROBOT research proposal
3. `README.md`
4. relevant inherited documentation under `docs/`

The current repository was inherited from the RC-RGD-IMU project as a working
research-pipeline scaffold.

Do not assume inherited IMU-HAR scientific choices are valid for TRUST-ROBOT.

The new scientific target is reliability-aware multimodal 6-DoF
localization/state estimation with calibrated modality-health probabilities,
auxiliary consistency evidence, health-aware factor weighting, estimator
status, and rule-based safety supervision.

Work incrementally. Preserve reproducibility, train/validation/test isolation,
protocol freezing, experiment provenance, and independent reference-source
rules.

See `TRUST_ROBOT_MASTER_CONTEXT.md` for the authoritative project context.

## KIOS synthetic sensor recovery — 2026-10-15 Verona checkpoint

Before future Isaac Sim camera/LiDAR/IMU work, read:
`docs/audits/trust_robot/TRUST_ROBOT_ISAACSIM_V16_28_29_VERONA_HANDOFF_V1.md`.
V16.28 yielded six validated camera/LiDAR synthetic pairs with 130 IMU/pose records; V16.29 offline timing/provenance audit passed. The **exact working source and data reports have not yet been imported from KIOS into GitHub**. The documented KIOS-only builder at `scripts/trust_robot/kios_v16_full_checkpoint_builder_20261015.sh` is not executable on Verona. Never claim physical sensor equivalence, independent ground truth, or measured camera–LiDAR synchronization from the synthetic run.

## KIOS Isaac Sim V16 recovered acquisition (2026-10-15)

**Read before any new Isaac Sim camera/LiDAR/IMU work:**
`docs/audits/trust_robot/TRUST_ROBOT_ISAACSIM_V16_28_29_RECOVERY_FREEZE_V1.md`
and `experiments/isaacsim_v16_recovery_v1/README.md`.
The latter contains SHA-pinned successful source, corrected USD mount, compact
experiment reports, local run-preparation utility and offline validator, and KIOS-isolated reproduction launcher.
V16.28 passed 6 synthetic camera / 6 real GMO-derived LiDAR XYZ frame files
plus 130 IMU/pose records; V16.29 provenance audit passed. **Do not claim
cross-sensor exposure synchronization, independently measured ground truth,
physical sensor equivalence or localization performance.** Preserve original
V15/V16 experimental history. No shared-KIOS or physical-robot operations.
