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

## KIOS V16 L1-L3 registration gate checkpoint (2026-10-15)

Engineering-only deterministic diagnostics and a fail-closed factor-admission
interface are now versioned in
`experiments/isaacsim_v16_l123_registration_gate_v1/` and
`docs/audits/trust_robot/TRUST_ROBOT_KIOS_V16_L1_L2_L3_REGISTRATION_GATE_V1.md`.
L1: 8/10 registration diagnostics available; two sparse pairs refused.
L2: weak scan geometry and strongly perturbation-sensitive ICP pose estimates.
L3: 10/10 factors DENIED, eight evidence-tampering tests passed.
No localization pose factor, calibration, health label, cross-sensor sync,
independently referenced pose, or scientific accuracy claim is established.
These source/report copies are hash-bound and reproducibility-tested; frozen
Phase-2/Phase-4, M2DGR, historical V15/V16 data and SE4/SE5/SE9 scientific
gates remain unchanged. Read the package README before further LiDAR work.

## KIOS V16 L4-L9 geometry and registration stability (2026-10-15)

Before further synthetic LiDAR development, read
experiments/isaacsim_v16_l4_l9_geometry_stability_v1/README.md
and docs/audits/trust_robot/TRUST_ROBOT_KIOS_V16_L4_L9_GEOMETRY_STABILITY_V1.md.

The improved 16-emitter configuration increased synthetic geometric
conditioning and improved deterministic registration stability and
bidirectional/skip-frame consistency. The final scan has only two returns.

These engineering results do not establish real localization accuracy,
independent ground truth, cross-sensor synchronization or trained
health supervision. No estimator factors are authorized.

Preserve historical V16 recordings. Continue with L10 sparse coverage.
