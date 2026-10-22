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

## KIOS L36-L40 offline witness checkpoint (2026-10-16)

Archive: experiments/isaacsim_v16_l36_l40_acquisition_witness_v1/.
L36 46 negative tests; L37 isolated fail-closed nonexecuted candidate, 12 static mutations; L38 persistent local nonce rejection and 20 negative tests; L39 20 simulated crash windows; L40 committed receipt outbox with 2 recoveries and 7 denied faults.
Do not launch L37 or promote it to trusted source authenticity, physical exposure timing, independent 6DoF GT, calibrated health labels or scientific factors. Raw SQLite DBs and sensor files are not committed. Next L41 readiness audit. KIOS and iot4care are distinct workstations.

## KIOS L41-L45 acquisition falsification checkpoint (2026-10-16)

Read `experiments/isaacsim_v16_l41_l45_acquisition_falsification_v1/README.md` and `docs/audits/trust_robot/TRUST_ROBOT_KIOS_L41_L45_ACQUISITION_FALSIFICATION_V1.md`.

L41: 20 readiness gates and 26 negative controls. L42: offline hook/outbox compatibility and 25 negative controls. L43: 50 session mutations and 7 incomplete captures. L44: atomic synthetic decision outbox, 36 event faults, 8 database faults. L45: 12 coherent internal acceptances but ZERO independently trusted sensor origins; 20 incoherent denials, 12 database/receipt faults, 2 simulated recoveries.

No real sensor acquisition, trusted physical timing, independent 6DoF GT, calibrated health labels or pose factors. Preserve frozen KIOS evidence and Git history.

Next L46: offline independent-witness authority design and adversarial checks. L37 live launch remains denied.

## KIOS L46-L50 witness-authority checkpoint (2026-10-16)

Read `experiments/isaacsim_v16_l46_l50_authority_boundary_v1/README.md` and `docs/audits/trust_robot/TRUST_ROBOT_KIOS_L46_L50_TRUST_BOUNDARY_V1.md`.

L46 simulated role signing cannot establish sensor authenticity. L47 single-host SQLite exclusion worked only inside one ledger, while two isolated registries admitted the same nonce. L48-L49 retained quarantine without automatic promotion. L50 documented six engineering capabilities and sixteen unqualified requirements.

No trusted physical source, exposure-time verification, independent 6DoF GT, calibrated health model or scientific pose-factor authorization. Raw SQLite, sensors and test HMAC secrets remain outside GitHub.

Next: return to core clean 6DoF estimator and scientifically supportable dataset evidence. Do not pursue additional trust prototypes without a demonstrated research dependency. KIOS and iot4care are distinct workstations.

## KIOS S1–S5 core 6DoF scientific readiness checkpoint (2026-10-16)

See `experiments/trust_robot_s1_s5_core_6dof_readiness_v1/README.md` and `docs/audits/trust_robot/TRUST_ROBOT_KIOS_S1_S5_CORE_6DOF_READINESS_V1.md`.

S1: 36 M2DGR trajectories and 140 unqualified synchronization entries; frozen 22/7/7 split. S2: 104/104 selected synthetic estimator regression tests passed in compatible system Python, eight recorded factor denials. S3: 41 metadata-only contract tests. S4: 55 tests and 32 closed sensor science gates; corrected order-independent verifier. S5: 32 rejected false promotions and next-step integration decision. S1–S5 did not qualify real sensor capture, scoring, extrinsics, synchronization, health labels, or pose factors.

Next S6: CPU-only manufactured-fixture same-edge independent camera and LiDAR factor support with distinct covariance and factor identity, while retaining the recorded-source fail-closed gate and prior test baseline. Never unfreeze historical M2DGR calibration, split, ground-truth, or scientific-evidence gates. Work with KIOS and iot4care as separate machines; do not silently run the live simulator.

## KIOS S6–S10 joint synthetic fusion checkpoint — 2026-10-19

Archive: `experiments/trust_robot_s6_s10_joint_synthetic_fusion_v1/`; audit: `docs/audits/trust_robot/TRUST_ROBOT_KIOS_S6_S10_JOINT_SYNTHETIC_FUSION_V1.md`.

S6 implemented independent manufactured camera and LiDAR pose factors on shared edges in a 15D nonlinear Schur window (23 tests). S7 verified local information and perturbation response (22 passed; original failed JUnit retained). S8 tested assumed 12D correlated noise and conflict flags (27 tests). S9 stressed 15 manufactured conflict cases and 3 solver trajectories (43 tests). S10 reran the 104 legacy tests plus S6–S9 (219/219) and independently matched a clean synthetic trajectory across S6, S7, S9.

Preserve source SHA256 and proof boundaries. Historical M2DGR split and sensor gates unchanged. Do not claim physical covariance calibration, real six-DoF localization accuracy, empirical health labels, or enable live hardware/simulator/risk-based sensor suppression. KIOS and iot4care are separate workstations; use KIOS for current CPU development. Further real sensor data paths need independent scientific qualification before factor admission.

## KIOS R17–R20 authenticated M2DGR TRAIN input checkpoint — 2026-10-19

Archive: `experiments/trust_robot_r17_r20_recorded_input_checkpoint_v1/`.
Audit: `docs/audits/trust_robot/TRUST_ROBOT_KIOS_R17_R20_RECORDED_INPUT_V1.md`.
R16 authenticated the original `room_02.bag` TRAIN recording by SHA256; the raw bag is stored outside GitHub. R17 independently verified the ROS1 index (15 topics, 5182 chunks, 26149 messages over four required streams). R18 independently sampled eight serialized messages; its initial inability to handle embedded connection records and the targeted patch are preserved. R19 created six existing camera/IMU adapter receipts and two LiDAR layout-only nonfactor records. R20 passed 197 targeted frontend regressions and verified nonfactor provenance readiness. **No scientific real pose factor, cross-modal synchronization, full physical extrinsics, capture-time semantics, reference GT scoring, calibrated health label, or training is authorized.** Never upload raw ROS bags. Use KIOS for recorded-data development; iot4care is a distinct workstation.

## KIOS R22–R25 authenticated TRAIN signal diagnostic checkpoint — 2026-10-19

Archive: `experiments/trust_robot_r22_r25_recorded_diagnostics_checkpoint_v1/`.
Audit: `docs/audits/trust_robot/TRUST_ROBOT_KIOS_R22_R25_RECORDED_DIAGNOSTICS_V1.md`.
R22 decoded 8 authentic TRAIN messages; R23 sampled 32 across 30 ROS bag chunks; R24 rejected 128 in-memory provenance and 8 payload mutations, preserving original bag; R25 replayed three independent verifiers and passed 197 targeted frontend tests. The 25 small-source/report evidence files are SHA pinned, and the archive has a no-raw-data standalone verifier. **This is recorded diagnostic readiness, not verified localization or sensor-health classification.** `room_02.bag` is strictly off Git and the original 22/7/7 split remains frozen. Real pose factors, calibrated health, capture-clock synchronization, full extrinsics, independent GT scoring and live simulator activation remain denied. Next: implement bounded single-modality candidate motion diagnostics from TRAIN data, with independent numeric verification and no science promotion.

## KIOS R27–R31 recorded-motion engineering checkpoint — 2026-10-19

Before further recorded-sensor development, read `experiments/trust_robot_r27_r31_recorded_motion_checkpoint_v1/README.md` and `docs/audits/trust_robot/TRUST_ROBOT_KIOS_R27_R31_RECORDED_MOTION_V1.md`.

R27–R30 developed diagnostic-only LiDAR registration on authenticated TRAIN data: eight distributed adjacent scan pairs, sixteen genuine scans, and independently verified geometric/directional sensitivity. Bidirectional round-trip mismatch reached 10.8 cm and 2.53 degrees. R31 independently verified two genuine camera JPEGs and pixel-space optical flow (400 consistent tracks, approximately 0.023 pixel median displacement).

No calibrated real 6DoF pose, real sensor factor, physical capture synchronization, full extrinsics, independent ground-truth scoring, or health labels. Keep raw bags outside GitHub. Do not inspect confirmation_test for development. Next: multi-pair camera and IMU diagnostic candidates before scientific factor qualification.

## KIOS R33–R37 recorded camera / IMU checkpoint — 2026-10-20

Read `experiments/trust_robot_r33_r37_recorded_motion_checkpoint_v1/README.md` and `docs/audits/trust_robot/TRUST_ROBOT_KIOS_R33_R37_RECORDED_MOTION_V1.md` before further recorded-data development.

SHA-frozen R33–R37 artifacts preserve the initial R33 failure and patch, authentic 8-pair camera tracking, 16 two-sample IMU intervals, 16 three-sample gyro windows, and R37 independent readiness review.

All work uses M2DGR `room_02` TRAIN. No physical time/extrinsic qualification, pose accuracy, factor admission, health labels/training, or M2DGR scoring.

Never commit raw bag bytes or use confirmation_test for development.

Next pursue scientific sensor-motion qualification rather than treating numerical diagnostics as localization performance.

## R39–R43 sensor qualification checkpoint — KIOS, 2026-10-20

The frozen archive is `experiments/trust_robot_r39_r43_sensor_qualification_checkpoint_v1/`, with standalone `verify_checkpoint.py`. Audit: `docs/audits/trust_robot/TRUST_ROBOT_KIOS_R39_R43_SENSOR_QUALIFICATION_V1.md`.

33 frozen source/report/test artifacts, including original R40 failed Python code and targeted canonical-field repair. R39–R43 establish scientific evidence gaps, not qualified real sensor measurements. R41 found ten software contracts/protocols and no local room_02 reference payload; R42 confirmed 15 ROS1 connections with no CameraInfo/TF/mocap reference topics; R43 preserved 11 unfilled evidence receipts.

Never infer complete extrinsics from the partial D435i IMU relative rotation, physical clock alignment from message headers, or ground-truth scoring eligibility from a reference filename. Keep TRAIN/validation/test splits frozen, confirmation_test sealed, bag files out of Git. Real pose factors, health training, ATE/RPE scoring and robot safety actions remain DENIED.

Next R45: physical evidence intake and independent scientific qualification readiness.

## R45–R49 KIOS author calibration and camera-model archive — 2026-10-20

Checkpoint: `experiments/trust_robot_r45_r49_author_camera_model_checkpoint_v1/`, standalone `verify_checkpoint.py`. Audit: `docs/audits/trust_robot/TRUST_ROBOT_KIOS_R45_R49_AUTHOR_CAMERA_MODEL_V1.md`.

R45–R49 retain upstream Git-authenticated author parameter content, numeric comparisons, recorded topic/dimension compatibility, synthetic projection and model-robustness results; include original failing R46 independent verifier, targeted repair provenance, and offline author-file transfer evidence. Never promote matching configuration values, synthetically generated rays or small parameter differences to physical intrinsics/extrinsics accuracy, independently verified time synchronization or real robot pose factors. Continue TRAIN-only investigation, keep confirmation_test sealed, bag data off-Git and original split frozen. All eleven R43 missing-physical-evidence gates remain unqualified. Next R51: independent sensor/clock/reference applicability and evidence intake.

## KIOS R51–R55F evidence and R57/R57A replay checkpoint — 2026-10-21

Read `experiments/trust_robot_r51_r55f_evidence_checkpoint_v1/README.md`,
`experiments/trust_robot_r57_r57a_replay_checkpoint_v1/README.md`, and
`docs/audits/trust_robot/TRUST_ROBOT_KIOS_R51_R55F_EVIDENCE_V1.md`.
R51–R55F preserve authentic TRAIN timestamp diagnostics, clock sensitivity,
physical-evidence admission denials, author-source candidate and two HTTP-302
fetch attempts, and an offline manual download fallback. Ground truth was NOT
ACQUIRED. R56 pinned 39 source/test/report artifacts; R57 compared 39 archived
source bytes and rejected two tamper controls, then failed from a launcher
argument omission. R57A preserved that failure, repaired only the copied
launcher and replayed six synthetic/negative test programs successfully.

These engineering passes are not physical sensor synchronization, independent
reference GT, qualified metric 6-DoF, trained health estimation or ATE/RPE.
All eleven R43 scientific gates remain CLOSED. Keep the 22/7/7 split frozen,
confirmation_test sealed, raw bag and GT source off GitHub. Next science work:
obtain author-authorized original room_02 reference bytes and independently
audit their format, pose frames, clock and invalid rotations. No automatic
third identical SharePoint fetch; do not infer source acquisition from 302.

## KIOS R59–R61 author-source identity and quarantine checkpoint — 2026-10-21

R59 authenticated the exact author M2DGR README Git blob and its single
`room_02` published GT link, **not** actual ground-truth bytes. R60 preserved
an independently reviewed author GitHub issue/request DRAFT, NOT SENT.
R61 evaluated bounded offline GT quarantine: synthetic-positive allowed only
as unverified, 10 negative controls rejected, official GT staging ABSENT.
R62/R62A archived 17 exact SHA256-pinned R59–R61 artifacts and preserved the
original R62 one-nibble checksum typo and its targeted repair off Git.
R63 independently rejected five disposable-copy archive tamper challenges and
replayed five offline synthetic/independent validators. The off-Git replay
receipt SHA256 is `48d1ec9997bfb1fc07f8995193209b8db88187f47b0960f442d772ee10217766`.

Checkpoint: `experiments/trust_robot_r59_r61_author_source_quarantine_checkpoint_v1/`;
audit: `docs/audits/trust_robot/TRUST_ROBOT_KIOS_R59_R61_AUTHOR_SOURCE_QUARANTINE_V1.md`.
Reference acquisition and physical clock/frame/calibration remain blocked;
all 11 R43 science gates CLOSED. No real sensor factors, health training,
ATE/RPE scoring, rosbag or confirmation_test access. Next scientific step:
author-authorized GT bytes or authoritative response; never invent GT from the
public link or repeat denied SharePoint fetches.

## R64–R68 original M2DGR GT recovery — 2026-10-21

Original M2DGR data already exists on Verona:
`/mnt/hdd16T/ToqeerHomeBackup/toqeer/datasets/TRUST_ROBOT/M2DGR/`.
The Verona project is `~/toqeer/TRUST_ROBOT` (resolved location
`/mnt/hdd16T/ToqeerHomeBackup/toqeer/TRUST_ROBOT`).
KIOS active Git checkout: `/home/kios/TRUST_ROBOT_ALI/github_checkout_v15`
(branch `kios-isaacsim-v15-integration`). Existing TRAIN `room_02.txt` GT
was securely copied Verona → Windows → KIOS and kept OUTSIDE Git at
`/home/kios/TRUST_ROBOT_ALI/manual_official_gt_staging_v1/room_02_official_gt_candidate.txt`.
The 504403-byte copy matches historical GT SHA256 `79d2c6d9132ce3cf87bb87445729302cd73709a59344a3dfacc5d7788937589d`.
This is a project-historical checksum, not a separately author-certified hash.
No new GT download is necessary.

R65 found 3831 eight-column records, monotonically increasing first-column
values over 77.82016110420227, and 90 substantial quaternion-norm anomalies.
R66 original 0.001 quaternion-norm rule and independent replay agree:
90 invalid rotations in 61 sample-index runs; 3741 structurally valid
rotations and no structurally invalid translations. R67 reproduced the
historical Phase-2 quality report byte-for-byte: SHA256 `8b27f25c02d04e838a88eb62980b1f2e94d0e1ed13defd0c6fa0f0b07c6bed49`.
R68 compared the recovered GT against the immutable original R43 and R53
receipts. Historical R61 `GT=ABSENT` reflects earlier KIOS staging only,
not current dataset availability. The revised author inquiry is DRAFT, NOT SENT.

SHA-pinned 22-source-file checkpoint: `experiments/trust_robot_r64_r68_original_gt_recovery_checkpoint_v1/`.
Audit: `docs/audits/trust_robot/TRUST_ROBOT_KIOS_R64_R68_ORIGINAL_GT_RECOVERY_V1.md`. The raw GT is not committed. The 22/7/7 split stays frozen;
`confirmation_test` remains sealed. All 11 scientific gates remain CLOSED:
physical mocap tracked-body origin, mocap-body-to-LiDAR SE(3), timestamp
capture event/timebase and physical cross-sensor clocks are not independently
qualified. No real pose factors, health training or ATE/RPE scoring.
Next seek authoritative recording/frame/timing/calibration evidence; do not
recreate already available GT or infer physical calibration from file shape.

## KIOS R70–R74 Verona source admissibility checkpoint — 2026-10-21

R70 on Verona discovered 91 read-only metadata candidates; R71A verified
three source documents and corrected a research-manifest path error; R72
classified author calibration, 50 Hz Vicon description and recovered GT
cadence without claiming synchronization. R73 passed SHA-verified transfer
of exactly three private reports via Windows to KIOS; R74 completed positive,
eight negative, and independent validation. The six SHA-pinned R74 derived
artifacts and executable verifier reside in `experiments/trust_robot_r70_r74_scientific_admissibility_checkpoint_v1/`.
Source/private handoff report bytes stay off Git; only their checksums are
recorded. The previous R64–R68 original GT recovery checkpoint remains
authoritative for the 3,831 row/90 invalid rotation/61 run results. Physical
mocap origin, mocap-to-LiDAR geometry, event timestamps and physical clock
mapping remain UNVERIFIED. Eleven gates CLOSED, 22/7/7 split frozen, no raw
GT or bag, no confirmation_test, no real factors, health training or ATE/RPE.
Audit: `docs/audits/trust_robot/TRUST_ROBOT_KIOS_R70_R74_SOURCE_ADMISSIBILITY_V1.md`. Next: seek original physical recording/calibration
receipts and design a prospectively declared protocol; never infer physical
clock agreement from numeric sampling rate.

## KIOS R76–R78 physical source intake and runtime denial checkpoint — 2026-10-21

Parent commit `c1f59bb5e38bdfece14798031c0d911441b28de8`. R76 created 11-claim/5-timing-receipt format-only
evidence intake, with 12 rejected negative controls and an UNSENT author
physical-evidence request. R77 tested format-only candidates against both
existing M2DGR real-factor admission gates (8 new tests and 30 existing
regressions). R78 hard-denied real execution for 11 forged complete
author-like candidates, with 9 new tests, prior regressions, SHA-pinned
lineage and independent receipt. Archive: `experiments/trust_robot_r76_r78_physical_intake_runtime_checkpoint_v1/`, including 15
SHA-pinned code, tests and derived results; see `docs/audits/trust_robot/TRUST_ROBOT_KIOS_R76_R78_INTAKE_RUNTIME_GATE_V1.md`. This does not
qualify mocap-body origin, mocap-to-LiDAR SE(3), GT export event/timebase,
clock offset/drift or a rotation-repair policy. The recovered room_02 GT
is preserved off Git; historical R43 no-source receipts are immutable and
not assertions of current GT availability. All 11 scientific gates CLOSED;
no real factors, health training, ATE/RPE, raw bags, confirmation_test or
author request transmission. Next: obtain authoritative physical receipts
and independently validate them; no synthetic input grants authorization.

## R83C — R80–R82 recorded multimodal engineering checkpoint (2026-10-21)

Parent Git revision `aa4c06bdc2eac5cff7352157beef9ec534f2f455`. R80 (KIOS) verified eight separated real TRAIN LiDAR 6-DoF diagnostic pairs and 13 tests. R81 (Verona) implemented a typed read-only adapter, SHA-authenticated and replayed 90,992 recorded LiDAR increments across all 22 frozen TRAIN trajectories (91,014 scans), with 13 synthetic regression tests. R82 (Verona) reused the existing frozen SE3 camera/IMU low-level features and implemented stream-local 256-record descriptive windows over 2,816,957 TRAIN records across 62 source feature files (13 synthetic tests); missing camera/D435i streams remain absent in street_010 and street_09.

The R83A/B transfer delivered eight checksum-verified, sanitized R81/R82 code/report files to KIOS, in addition to four local SHA-verified R80 artifacts. The repository checkpoint archives 13 sources including the transfer manifest, a standalone verifier, and compact reports. Original Phase-2 LiDAR JSONL, SE3 per-record camera/IMU features, 62 R82 window JSONL, GT, ROSbags, private Verona reports, calibration secrets, and confirmation-test data stay off Git. The 22/7/7 split remains frozen. No new physical timing/frame qualification, camera-IMU-LiDAR alignment, real pose factors, health training, calibration or ATE/RPE was authorized; all 11 scientific gates remain CLOSED. Author contact is optional, not a blocker to continued TRAIN-only engineering.

Archive: `experiments/trust_robot_r80_r82_recorded_multimodal_checkpoint_v1/`. Audit: `docs/audits/trust_robot/TRUST_ROBOT_KIOS_R80_R82_RECORDED_MULTIMODAL_CHECKPOINT_V1.md`. Next: build a genuinely new, synthetic-testable visual-motion or IMU-preintegration frontend while preserving fail-closed real factor execution, rather than re-extracting already frozen observations.

## R87 — R84–R86 synthetic gap-aware inertial rolling checkpoint (2026-10-21)

Parent `885bf22f7454a85cee53b82f5d6a5cbd7d3eff3e`. R84 implements strict synthetic IMU source admission, timestamp gap segmentation and bounded bias/covariance preintegration (21 tests). R85 connects safe continuous intervals to 15D covariance-whitened synthetic inertial graph edges, with zero cross-gap factors and manufactured endpoint residual closure (21 tests). R86 executes controlled nonlinear least-squares rolling 15D state updates with independent synthetic fixed anchors at each segment boundary, checks Jacobian rank/residual reduction, and refuses factor continuity across gaps (21 tests). The six code/test files and six compact result/validation reports are SHA-pinned in `experiments/trust_robot_r84_r86_synthetic_inertial_rolling_checkpoint_v1/`, with an independent verifier and five disposable tamper controls.

The constructed endpoints are not independent reference truth or a measured localization benchmark. The archived SE3 IMU norms do not provide signed axes or verified physical capture time, so no real inertial factors were derived. No Schur-complement marginalization, physical synchronization, independent extrinsic calibration, health model training, or ATE/RPE is claimed. Original GT, ROSbags, private Verona evidence and confirmation_test stay excluded; the frozen 22/7/7 split and all eleven closed scientific gates are preserved. Next: synthetic Schur-complement fixed-lag marginalization with gauge-sensitive numerical tests before any further new real-data factor admission.

## R91 — R88–R90 Schur prior integrity checkpoint (2026-10-22)

Parent `c147ccaba711b8a600294b2df2b8f64f6ef6bcd4`.

R88 implements 15D local linearized Gaussian Schur-complement information elimination with independent full-batch state, covariance and cost checks (21 synthetic tests).

R89 verifies exact frozen-prior coordinate recentering and measures nonlinear Jacobian drift without claiming unauthorized relinearization of eliminated factors (21 tests).

R90 supplies a fail-closed prior admission guard. Twenty-seven regression tests pass, including typed rejection of nonfinite matrices. Across four synthetic scenarios, 30 adversarial operations are rejected and 15 valid recentering trials pass.

The checkpoint `experiments/trust_robot_r88_r90_schur_prior_checkpoint_v1/` contains 12 exact SHA-pinned code/test/result artifacts, compact independent validation receipts, a standalone verifier and five disposable archive tamper controls.

Scientific status: synthetic mathematical engineering only. Fixed synthetic anchors, regularization and numerical thresholds do not prove physical accuracy or safety. No cross-gap information transfer, real sensor fusion factors, real health labels, training or ATE/RPE. Original ROSbags, GT, private Verona evidence and sealed confirmation data remain excluded. The frozen 22/7/7 split is unchanged; all 11 scientific gates remain CLOSED.

Next priority: evidence-first physical source, clock-domain, sensor-frame and extrinsic qualification, followed by authorized measured-sensor engineering only when sufficient independent evidence exists.

## R94 — R92–R93 physical evidence readiness checkpoint (2026-10-22)

Parent `8b6024cc7c09568fc1e5485abdc0a5aa2bb72cd9`. R92 inspected 13 exact Git-tracked historical evidence records, verified the 11 historical scientific-gate receipts and 5 physical timing receipts, recognized the already recovered original room_02 GT while leaving physical semantics unqualified, and documented five acquisition priorities (18 tests). R93 generated the evidence author outreach **DRAFT NOT SENT** and a strict metadata-only source intake checklist, with no contacts made or new sources acquired (23 tests). The SHA-pinned checkpoint `experiments/trust_robot_r92_r93_physical_evidence_readiness_checkpoint_v1/` contains eleven code/test/report/document artifacts, standalone verifier and five disposable tamper controls (41 tests). The earlier R76 unsent draft is acknowledged and not overwritten.

All 11 scientific gates remain CLOSED. No real fusion factors, qualified physical clocks/extrinsics, actual GT scoring/ATE/RPE, health labels/training, confirmation_test access, original raw GT or ROSbags in Git. External next step: user reviews draft, identifies proper dataset source contact and requests recording-specific physical metadata or plans independent measurement; no gate can open without independent physical verification.

## KIOS R95-R96 synthetic incremental checkpoint — 2026-10-22

Read `experiments/trust_robot_r95_r96_joint_incremental_checkpoint_v1/README.md`
and `docs/audits/trust_robot/TRUST_ROBOT_KIOS_R95_R96_INCREMENTAL_JOINT_GAUSSIAN_CHECKPOINT_V1.md`
before extending the rolling estimator.

R95 passed 19 regression tests and checked 16 synthetic
Gaussian prior prefixes. R96 passed 33 regression tests
and checked 28 Gaussian prefixes with manufactured
camera/LiDAR endpoint unaries and distinct assumed covariances.

These are mathematical software checks, not a validated
real-time nonlinear estimator, physical camera/LiDAR factors,
independently measured synchronization, or calibrated health
estimation. All 11 scientific gates remain CLOSED.

A separate M2DGR author inquiry was reportedly sent by
the user; no author response or new qualified physical
evidence has been ingested.

Continue phased KIOS-only implementation, validate before
a guarded exact-manifest Git push, and preserve frozen data.

## KIOS R98-R99 nonlinear Schur lifecycle checkpoint — 2026-10-22

The archived checkpoint is:
`experiments/trust_robot_r98_r99_nonlinear_prior_checkpoint_v1/`.

Read its README, standalone verifier, and
`docs/audits/trust_robot/TRUST_ROBOT_KIOS_R98_R99_NONLINEAR_PRIOR_CHECKPOINT_V1.md`.

R98 passed 22 synthetic regression tests, checking
the S6 nonlinear SE(3) estimator, factor ownership,
and one independent local Schur calculation.

R99 passed 33 tests and checked all nine successive
S6 Schur marginalizations over three synthetic runs.
Prior inheritance, local normal equations, energy
differences, source restrictions and estimator
equivalence were independently tested.

The R95 Gaussian backend has NOT been integrated
into S6. The event digest chain is not trusted
physical provenance. The numerical checks do
not establish nonlinear posterior consistency.

All 11 scientific gates remain CLOSED. The
M2DGR author inquiry is awaiting independently
qualifiable evidence; do not infer approval from it.

Next: guarded nonlinear estimator integration
design and implementation, one phase at a time.

## KIOS R101–R102 prior conversion and compatibility checkpoint — 2026-10-22

Read `experiments/trust_robot_r101_r102_backend_compatibility_checkpoint_v1/README.md`
and `docs/audits/trust_robot/TRUST_ROBOT_KIOS_R101_R102_BACKEND_COMPATIBILITY_CHECKPOINT_V1.md`.

R101: 28 synthetic regression tests and 16 R95 Gaussian-to-square-root
conversions. The converted priors belong to an isolated R95 local namespace,
not live S6 nodes. R102: 27 tests and eight independent compatibility blockers
from actual R95 and S6 priors. Direct nonlinear prior binding remains denied.

These phases do not establish a nonlinear R95/S6 backend merger or any
physical source qualification. All 11 scientific gates remain CLOSED.
Do not alter the frozen 22/7/7 M2DGR split or sealed confirmation data.
Next: a single-source synthetic graph with explicit clock, gauge, frame,
noise, prior dimension, node IDs and factor ownership.

## KIOS R104-R105 synthetic graph and local-prior checkpoint — 2026-10-22

Archive:
`experiments/trust_robot_r104_r105_shared_graph_prior_checkpoint_v1/`

Scientific audit:
`docs/audits/trust_robot/TRUST_ROBOT_KIOS_R104_R105_SHARED_GRAPH_PRIOR_CHECKPOINT_V1.md`

R104 passed 48 tests, validating a single-source
synthetic five-node graph with four IMU factors,
independent camera/LiDAR identities and exact
synthetic factor ownership.

R105 passed 33 tests after two validated repairs.
It returned nine recentered, same-graph S6 Schur
priors to later nonlinear windows and checked
local residual equivalence and estimator comparison.

R95's Gaussian backend remains SEPARATE.
Do not equate matching state dimensions with
matching chronology, gauge, frame or factor history.

These are manufactured software experiments.
All 11 scientific gates remain CLOSED.

Continue with phased KIOS-only development,
source hashing, fail-closed admission,
independent validation and guarded Git pushes.

## KIOS R107-R108 synthetic incremental-delivery checkpoint — 2026-10-22

Archive:
`experiments/trust_robot_r107_r108_incremental_delivery_checkpoint_v1/`

Scientific audit:
`docs/audits/trust_robot/TRUST_ROBOT_KIOS_R107_R108_INCREMENTAL_DELIVERY_CHECKPOINT_V1.md`

R107 passed 38 regression tests and created a
separate synthetic sequential-admission nonlinear
estimator using the original S6 factor mathematics.
Twelve ordinary and twelve recentered windows
were validated, including nine prior transfers.

R108 passed 42 regression tests, checking ordered
and bounded-reordered manufactured packet delivery.
Across 12 solver runs, 48 nonlinear windows,
36 Schur marginalizations and 18 same-graph
prior transfers were exercised.

Neither phase modifies the original S6 source.
R95 Gaussian priors remain incompatible with
direct S6 import.

The session digest is a local identifier, not
authenticated source provenance. These are
in-process software tests, not real-time or
physical sensor transport measurements.

All 11 scientific gates remain CLOSED.

Next: synthetic failure-state handling and
explicit fail-stop versus rollback guarantees.

## KIOS R110-R111 failure isolation checkpoint — 2026-10-22

Archive:
`experiments/trust_robot_r110_r111_failure_transaction_checkpoint_v1/`

Audit:
`docs/audits/trust_robot/TRUST_ROBOT_KIOS_R110_R111_FAILURE_TRANSACTION_CHECKPOINT_V1.md`

R110 passed 39 tests. Six manufactured internal
failures were injected and quarantined; five
showed internal mutation before failure.

R111 passed 43 tests. Its shadow-state wrapper
preserved committed in-memory state across six
injected failures and completed six subsequent
retries using fresh candidate buffers.

Together the phases provide 82 archived tests.

R111 isolation is single-threaded and in-process.
It does not establish power-loss recovery,
concurrent publication safety, distributed
exactly-once delivery or bounded runtime latency.

Original S6 and R107/R108 remain unchanged.
Direct R95 Gaussian prior import remains denied.

All 11 scientific gates remain CLOSED.

Continue phased KIOS-only engineering with
source SHA-256 pins, fail-closed testing and
guarded validated GitHub publication.
