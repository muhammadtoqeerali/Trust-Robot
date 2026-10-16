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

## KIOS V16 L10-L16 target recovery (2026-10-15)

Read:
experiments/isaacsim_v16_l10_l16_target_recovery_v1/README.md
docs/audits/trust_robot/TRUST_ROBOT_KIOS_V16_L10_L16_TARGET_RECOVERY_V1.md

L14 restored six 16-point synthetic LiDAR scans using a +0.30 m
calibration-target move. L15 established five available consecutive
ICP diagnostics. L16 completed all 15 scan-pair diagnostics but
revealed up to approximately 4.22 degrees of long-baseline
rotational inconsistency.

Preserve all frozen experiments and raw recordings.
Do not claim physical localization validity, calibrated sync,
health labels, or authorized pose factors.

Next: L17 long-baseline correspondence/initialization audit.

## KIOS L17-L23 ambiguity and robustness checkpoint (2026-10-15)

Before continuing synthetic LiDAR ambiguity or multimodal-estimator
research, read:

experiments/isaacsim_v16_l17_l23_ambiguity_robustness_v1/README.md
docs/audits/trust_robot/TRUST_ROBOT_KIOS_L17_L23_AMBIGUITY_ROBUSTNESS_V1.md

L17-L19 evaluated initialization ambiguity, one-to-one matching,
inferred beam associations and per-beam sensitivity.

L20-L21 implemented and challenged a diagnostic-only ambiguity screen.

L22 recomputed 60 small-perturbation pair diagnostics with no changed
warning decisions. L23 recomputed 110 structured-stress pair
diagnostics with five changed decisions.

Some deliberately corrupted inputs remained unflagged, and one
stale-scan substitution reduced a prior warning. Do not promote
these tests to calibrated sensor-failure detection or health labels.

The current next phase is L24: sensor provenance, frame freshness,
and common-mode fault detection.

Keep working phase by phase: generate one guarded implementation,
have the user run it on KIOS, review its full output, and commit only
at substantive validated milestones. Never change frozen raw files
or admit pose factors without the established scientific evidence.

## KIOS L24-L30 multimodal evidence checkpoint (2026-10-16)

Read `experiments/isaacsim_v16_l24_l30_multimodal_evidence_v1/README.md`
and `docs/audits/trust_robot/TRUST_ROBOT_KIOS_L24_L30_MULTIMODAL_EVIDENCE_V1.md`.

L24-L26 exposed provenance/common-mode blind spots and denied
all scientifically unqualified estimator/health admissions.
L27-L29 prepared evidence contracts, a shadow event envelope,
and an instrumented candidate. L30 acquired fresh synthetic
camera/LiDAR/IMU/scripted pose evidence with a validated
272-event provenance envelope and six negative controls.

L30 is a successful guarded engineering capture, not
verified physical synchronization or independent ground truth.
No pose factors or health labels are authorized.

Next: L31 offline provenance and measurement-time assessment.
Never rerun L30 merely to validate this archive.
The KIOS and iot4care workstations are distinct.

## KIOS L31-L35 provenance witness checkpoint (2026-10-16)

Read:
experiments/isaacsim_v16_l31_l35_provenance_witness_v1/README.md
docs/audits/trust_robot/TRUST_ROBOT_KIOS_L31_L35_PROVENANCE_WITNESS_V1.md

L31-L32 verified cross-run source hashes and demonstrated limits
of hash-only freshness/source-independence inference.

L33 produced the prospective evidence acquisition contract.

L34 completed a separate-process post-capture witness dry run.
L35 completed a challenge-before-software-recording rehearsal
with twelve historical fixture references and 25 rejected
adversarial mutations. No new sensor measurements occurred.

None of these results establishes independent source
authenticity, trusted hardware attestation, physical exposure
sync, independent 6DoF ground truth or authorized pose factors.

Next: L36 acquisition-time witness integration design and
offline falsification before any additional guarded GPU work.

Use KIOS for all KIOS-specific local experiments. Do not
confuse iot4care/MioAgent with the KIOS repository.
