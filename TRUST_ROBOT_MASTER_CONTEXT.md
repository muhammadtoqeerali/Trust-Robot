# TRUST-ROBOT Master Project Context

## 1. Project identity

Project name:

TRUST-ROBOT

Full title:

Reliability-Aware Multimodal Edge AI for Fault- and Attack-Resilient Autonomous Robots

This directory was initialized from the working RC-RGD-IMU research pipeline.

IMPORTANT:

The inherited RC-RGD-IMU files are a SOFTWARE, EXPERIMENTAL, TESTING,
REPRODUCIBILITY, AND PROJECT-ORGANIZATION SCAFFOLD.

They are NOT the final scientific implementation of TRUST-ROBOT.

Do not assume that an inherited IMU-HAR model, dataset, experiment stage,
configuration, metric, corruption definition, class label, training procedure,
or benchmark remains scientifically valid for TRUST-ROBOT.

The objective is to reuse the engineering structure and proven research
workflow while progressively replacing the scientific contents according to
the TRUST-ROBOT proposal.

---

## 2. Primary scientific objective

TRUST-ROBOT develops a compact reliability-aware multimodal Edge AI framework
for robust 6-DoF localization and state estimation.

The principal scientific question is not activity recognition.

The target task is:

    multimodal sensing
        ->
    modality diagnostics
        ->
    calibrated modality-health estimation
        ->
    auxiliary consistency evidence
        ->
    reliability-aware factor conditioning
        ->
    fixed-lag 6-DoF state estimation
        ->
    estimator and modality-health status
        ->
    rule-based safety supervision

The trust layer must improve graceful degradation when sensor information is:

- degraded
- missing
- inconsistent
- faulty
- desynchronized
- miscalibrated
- environmentally degraded
- intentionally manipulated

---

## 3. Main sensing modalities

Core sensing modalities are expected to include:

- IMU
- camera / vision
- LiDAR or depth

Optional/platform-dependent modalities may include:

- joint states
- contact information
- proprioception
- wheel odometry
- GNSS

Only modalities actually available, synchronized, calibrated, and scientifically
appropriate for a dataset/platform should be used.

Do not fabricate missing modalities.

---

## 4. Target estimator architecture

TRUST-ROBOT uses a hybrid learned-probabilistic architecture.

The learned component does NOT directly regress the robot pose.

Conventional localization front ends generate measurement/factor information.

Expected factor sources include:

- IMU preintegration
- visual relative-motion / reprojection information
- LiDAR scan-matching information
- optional kinematic/contact information
- optional other technically justified localization factors

The backend is intended to be a fixed-lag sliding-window nonlinear state
estimator.

The state should support the project's required 6-DoF localization/state
estimation quantities, including where applicable:

- orientation
- position
- velocity
- IMU gyroscope bias
- IMU accelerometer bias

The estimator backend and relevant optimization settings must remain fixed
across causal trust-layer ablations unless a protocol explicitly states
otherwise.

---

## 5. Modality-health mechanism

Each modality m should ultimately have a compact health-specific diagnostic
adapter or encoder E_m.

The health pathway should consume appropriate low-level signal summaries,
front-end diagnostics, and residual-history evidence.

The modality-health head should produce calibrated probabilities over:

    H_m(t) in {
        healthy,
        degraded,
        unusable
    }

The health head identifies functional usability.

It must NOT automatically claim whether degradation was caused by:

- benign fault
- environmental degradation
- malicious attack

Cause attribution is a separate scientific question and must only be claimed
when explicitly evaluated.

Health labels must be defined independently from final localization error.

---

## 6. Calibration and freezing discipline

The modality-health network should be trained using supervised three-class
classification.

Calibration should use validation/calibration data only.

Temperature scaling is the current proposal mechanism.

Before held-out testing, freeze:

- trained network weights
- calibration temperatures
- health thresholds
- suppression/recovery thresholds
- fault severity ranges
- attack budgets
- fallback/safety thresholds
- other validation-selected operating points

Test data must not be used for model selection or threshold tuning.

---

## 7. Reliability-aware factor weighting

The proposal defines a health-derived modality weight conceptually as:

    w_m(t) = p_H_m(t) + alpha_m * p_D_m(t)

where alpha_m is selected on validation data.

Current standardized innovation provides an additional bounded short-horizon
factor-conditioning term q_m.

The final factor scale is conceptually:

    lambda_m = clip(w_m * q_m, epsilon_m, 1)

which rescales factor information or equivalently inflates covariance.

The persistent health pathway and current-innovation conditioning pathway must
remain scientifically distinguishable.

Do not collapse them into one unexplained reliability score.

---

## 8. Auxiliary consistency evidence

TRUST-ROBOT should investigate consistency between technically compatible
sources, including where applicable:

- visual motion versus LiDAR motion
- inertial propagation versus exteroceptive odometry
- temporal pose continuity
- kinematic/proprioceptive motion
- platform motion bounds
- residual histories

Pairwise disagreement establishes inconsistency.

Pairwise disagreement alone does NOT necessarily identify which modality is
responsible.

Attribution may require:

- modality-specific diagnostics
- another sufficiently informative modality
- a trusted physical constraint

Ambiguous cases must be reported as ambiguous or estimator-degraded rather
than assigned a fabricated confident label.

---

## 9. Suppression and recovery

Hard modality suppression must not be a single-frame arbitrary decision.

The proposal expects hysteretic behavior using:

- unusable-probability entry threshold
- consecutive-window entry requirement
- lower recovery threshold
- consecutive-window recovery requirement

Before suppressing a modality, the estimator should assess whether the
remaining factor support is sufficient.

If the remaining system cannot adequately support the state, report:

- degraded estimator state
or
- unavailable estimator state

instead of forcing a nominal estimate.

No unsupported observability guarantee should be claimed.

---

## 10. Safety supervision

The learned health model is NOT the robot controller.

Safety response is intended to be a separate rule-based supervisory layer.

The supervisor may use:

- calibrated modality-health probabilities
- estimator covariance/status
- tracking availability
- residual consistency
- solver validity
- frozen validation-selected thresholds

Planned policy comparisons include:

- nominal continuation
- always-stop
- health-triggered policy
- oracle-health policy

Physical experiments must remain guarded and progressively validated.

---

## 11. Dataset progression

Current proposal-level dataset roles:

### M2DGR

Primary development benchmark.

Expected roles:

- development
- validation
- calibration
- controlled fault injection
- in-distribution testing

Primary relevant sensors:

- camera
- LiDAR
- IMU

Trajectory-disjoint splitting is required.

All clean and corrupted derivatives of a base trajectory must stay in the
same partition.

Independent reference streams must not also be used as evaluated estimator
inputs.

### EuRoC MAV

Camera-IMU controlled testing and different-platform evaluation.

Use full 6-DoF metrics only where reference coverage supports them.

### TUM-VI

Supplementary camera-IMU cross-dataset stress testing.

Only score intervals and metrics supported by independent reference coverage.

### MUN-FRL

Supplementary camera-IMU-LiDAR cross-platform testing.

Reference-source independence must be verified before use.

### GrandTour

Quadruped heterogeneous-sensor stress testing.

Potential sensor subsets include:

- LiDAR
- camera
- IMU
- optional proprioception in a separate branch

Reference and evaluated-input streams must remain separated.

### M3DGR

Conditional supplementary degradation evaluation.

Do not use until release availability, file integrity, calibration,
timestamps, sensor streams, and reference coverage are verified.

### KIOS quadruped data

Planned local physical collection.

Expected roles:

- held-out physical-system testing
- onboard profiling
- safety-supervisor evaluation
- controlled closed-loop testing

Development/calibration runs must remain separate from final held-out physical
tests.

---

## 12. Anti-leakage rules

The following are mandatory unless formally revised by a later frozen protocol.

1. Base trajectories must be disjoint across train, validation/calibration,
   and test.

2. Clean and corrupted versions of one base sequence must remain within the
   same split.

3. Corruption random seeds must not be reused across partitions.

4. Test data must not determine:
   - model architecture
   - thresholds
   - severity levels
   - attack budgets
   - calibration temperatures
   - fallback settings

5. A sensor/reference stream used to construct ground truth must not
   simultaneously be used as an evaluated estimator input unless a scientifically
   independent instance is explicitly available.

6. Cross-dataset recalibration, when allowed, must use a separate
   calibration-only subset and must be reported separately from zero-shot
   transfer.

---

## 13. Fault evaluation

Fault evaluation must remain separate from attack evaluation.

Planned accidental sensor/communication faults include:

- complete outage
- intermittent dropout
- additive measurement noise
- bias / gradual drift
- frozen / stuck measurements
- timestamp shift / desynchronization
- calibration / extrinsic drift
- encoder/contact faults where applicable

Fault injection must occur at the scientifically appropriate layer.

Raw-sensor corruption and factor-level corruption must never be presented as
equivalent.

---

## 14. Environmental degradation

Environmental/non-attack degradation should remain its own evidence category.

Examples include:

- low light
- motion blur
- partial occlusion
- texture loss
- LiDAR sparsity
- LiDAR sector loss
- geometric degeneracy
- wheel slip where applicable
- foot slip/contact ambiguity
- GNSS denial/multipath where applicable

Environmental degradation must not automatically be labelled as malicious
attack.

---

## 15. Attack evaluation

Attack experiments must operate under an explicit threat model.

Potential planned attacks include:

- false-data injection / spoofing
- bounded adversarial image or point-cloud perturbation
- replay
- timestamp manipulation
- coordinated two-modality corruption
- adaptive white-box digital evasion

Every attack protocol should specify:

- attacker knowledge
- writable modality/modalities
- writable fields
- attack duration
- magnitude/rate/norm budget
- objective
- protected-source assumptions
- identifiability assumptions

Attack budgets and thresholds must be fixed before held-out testing.

The project should not claim successful source attribution in regimes where
the available uncompromised information is insufficient.

---

## 16. Core research questions

RQ1:
Can explicitly supervised and calibrated healthy/degraded/unusable modality
probabilities outperform fair validation-calibrated proxy reliability scores?

RQ2:
Does health-aware factor weighting improve localization/state-estimation
robustness and graceful degradation under increasing fault severity?

RQ3:
Under explicitly stated identifiability assumptions, does auxiliary
cross-modal and kinematic/temporal consistency improve handling of
single-sensor, coordinated, and adaptive attacks?

RQ4:
Can the trust layer meet onboard resource constraints and improve guarded
closed-loop safety when fallback thresholds are frozen before physical tests?

---

## 17. Evaluation families

Evaluation should remain separated into:

1. localization/state estimation
2. modality-health discrimination
3. calibration quality
4. controlled fault robustness
5. attack robustness
6. graceful degradation
7. estimator availability/failure
8. computational/resource cost
9. closed-loop safety

Do not combine these into a single undocumented aggregate score.

---

## 18. Localization metrics

Depending on valid reference support, expected metrics include:

- translational ATE
- rotational ATE
- translational RPE
- rotational RPE
- translational drift
- rotational drift
- tracking availability
- estimator failure duration
- absolute error increase
- relative error inflation
- severity-AUC
- worst-family performance
- complete-modality-loss performance

Metrics must only be used where the reference source supports the required
state dimension.

---

## 19. Health metrics

Expected modality-health metrics include:

- three-class Macro-F1
- macro one-vs-rest AUPRC
- multiclass Brier score
- classwise adaptive ECE
- false-alarm rate
- detection delay

Health calibration and localization performance are distinct evidence streams.

---

## 20. Statistical unit

Overlapping windows are not independent samples for final statistical
inference.

Uncertainty analysis should account for parent trajectory/sequence structure.

Corruption realizations are nested within their source sequence.

Sequence/trajectory-level clustered or paired procedures should be used where
specified by the final protocol.

---

## 21. Primary causal ablations

The proposal expects same-backbone causal comparisons such as:

- fixed fusion
- modality dropout
- proxy gating
- health-only
- consistency-only
- full TRUST-ROBOT
- oracle health

These comparisons should keep compatible:

- localization backend
- front ends
- partitions
- corruption instances
- estimator settings

This is stronger causal evidence than comparing unrelated end-to-end systems.

---

## 22. External comparison systems

Potential task-compatible systems mentioned in the proposal include:

- VINS-Mono
- LIO-SAM
- FAST-LIO2
- LVI-SAM
- MIMOSA
- SelectFusion
- Kheirandish et al. fault-tolerant fusion
- Huang et al. degradation-aware fusion
- DAMS-LIO
- Switch-SLAM
- Ground-Fusion++
- VILENS
- MUSE
- Nistico et al. quadruped estimator
- Ultra-Fusion

Do not automatically download or integrate all of them.

A comparator should be executed only when:

- source code is available
- licensing permits use
- required sensor streams exist
- output is compatible with the target metric
- a technically defensible configuration can be reproduced

Otherwise keep it as literature or reported-results context.

---

## 23. Resource evaluation

TRUST-ROBOT must measure both:

1. complete-system cost
2. incremental trust-layer overhead

Expected resource evidence includes:

- mean latency
- P95 latency
- deadline misses
- throughput
- processor utilization where measurable
- peak memory
- storage
- average power
- peak power
- energy per update or trajectory

Record hardware/software versions, power/clock mode, sensor rates, estimator
window size, warm-up policy, and measurement method.

---

## 24. Inherited RC-RGD-IMU structure

The current project initially contains inherited directories such as:

    configs/
    docs/
    embedded/
    experiments/
    models/
    requirements/
    src/
    tests/

These should be treated as reusable engineering infrastructure.

Potentially reusable patterns include:

- protocol freezing
- configuration registries
- manifest generation
- development/calibration/test separation
- corruption registries
- reproducibility controls
- experiment stages
- baseline locking
- test infrastructure
- runtime benchmarking
- embedded/deployment measurement
- integrity audits
- scientific evidence matrices
- final confirmation workflow

Do not blindly retain:

- IMU HAR class semantics
- HAR-specific models
- old dataset assumptions
- DATE-era baseline assumptions
- STORM-specific comparison logic
- old paper evidence
- old fault magnitudes
- old operating points
- historical workstation paths
- old final-model naming/version conventions

These should be replaced progressively.

---

## 25. Migration principle

Do NOT rewrite the entire inherited project at once.

Adapt TRUST-ROBOT incrementally.

For each stage:

1. identify what engineering infrastructure is reusable
2. identify what scientific assumptions are IMU-HAR-specific
3. freeze the TRUST-ROBOT replacement protocol
4. implement the new component
5. test it
6. validate against synthetic/small-scale data
7. document provenance
8. only then deprecate or remove the inherited version

The inherited pipeline is valuable because it already encodes a disciplined
research workflow.

Preserve that discipline while replacing the scientific task.

---

## 26. Recommended high-level development order

The intended development sequence is approximately:

Phase 0:
Project integrity, environment, dataset/access audit, proposal freeze.

Phase 1:
Dataset registry, synchronization, reference-source rules, trajectory split
and anti-leakage protocol.

Phase 2:
Fixed clean localization/state-estimation backbone.

Phase 3:
Multimodal fault/degradation/attack taxonomy and corruption engine.

Phase 4:
Per-modality diagnostic feature extraction.

Phase 5:
Three-state modality-health model.

Phase 6:
Validation-only probabilistic calibration.

Phase 7:
Auxiliary cross-modal and kinematic/temporal consistency evidence.

Phase 8:
Health-aware factor weighting and bounded innovation conditioning.

Phase 9:
Suppression/recovery and estimator-status logic.

Phase 10:
Causal ablations and controlled fault experiments.

Phase 11:
Cross-dataset evaluation.

Phase 12:
Attack/threat-model evaluation.

Phase 13:
Efficiency, latency, memory and power characterization.

Phase 14:
Guarded real-robot integration and supervisory testing.

Phase 15:
Frozen final confirmation and publication evidence generation.

This phase numbering is provisional and may later replace the inherited
RC-RGD-IMU experiment numbering.

---

## 27. Rules for AI agents

Before modifying this project, an AI agent must:

1. Read this file completely.

2. Read the TRUST-ROBOT proposal.

3. Inspect the inherited pipeline before deleting or rewriting components.

4. Distinguish:
   - reusable engineering infrastructure
   - inherited IMU-HAR scientific assumptions
   - new TRUST-ROBOT scientific requirements

5. Never use test data for parameter selection.

6. Never invent dataset availability, calibration, synchronization or ground
   truth.

7. Never claim physical-robot evidence before physical experiments exist.

8. Never claim attack resilience outside the explicitly tested threat model.

9. Never claim modality attribution where identifiability is insufficient.

10. Never silently modify frozen protocols after held-out evaluation.

11. Preserve reproducibility:
    - seeds
    - manifests
    - checksums where appropriate
    - environment information
    - configurations
    - data provenance
    - experiment provenance

12. Prefer small validated migration steps over large uncontrolled refactors.

13. Treat generated results separately from source code.

14. Preserve a clear distinction among:
    - development
    - calibration
    - confirmation/test
    - cross-dataset stress testing
    - physical evaluation

15. Do not treat inherited experiment-stage numbers as the final TRUST-ROBOT
    scientific pipeline.

---

## 28. Immediate project status

Current state:

- TRUST_ROBOT directory created locally on workstation.
- RC-RGD-IMU first-party source tree copied as the initial scaffold.
- Original Git history was not copied.
- External RC-RGD-IMU comparison submodules were not copied.
- No TRUST-ROBOT Git repository is required at this stage.
- No TRUST-ROBOT dataset has yet been configured in this new workspace.
- No TRUST-ROBOT scientific implementation should yet be considered final.
- The next task is to inspect and redesign the inherited pipeline stage by
  stage against the TRUST-ROBOT proposal.

---

## 2026-09-15 Phase-2 Reference Quality Checkpoint

M2DGR Phase-2 reference-quality auditing is complete.

Validated state:

- 36 trajectories
- 16 RTK/INS references
- 11 Leica translation-only references
- 9 motion-capture references
- zero structurally invalid translation samples
- all 9 mocap trajectories contain structurally invalid rotation samples
- sample-index validity runs do not authorize interpolation
- synthetic `[0,1] ns` coverage retired
- audited current-schema successor manifest generated
- reference-quality index generated
- 66 TRUST-ROBOT tests passing

Unresolved and intentionally blocking evaluation:

- synchronization verification
- continuous-time reference coverage verification
- physical reference-quality verification
- numerical association tolerance selection

Next implementation phase:

Phase 3 — Synchronization Verification.


---

## Phase-3A checkpoint — 2026-09-16

M2DGR sensor timing characterization is complete across all 36 trajectories.

Important Phase-3A facts:

- sensor header timestamps are the observed measurement-time fields;
- ROS bag record time remains transport/provenance diagnostic only;
- `/handsfree/imu` and `/velodyne_points` are present in 36/36 trajectories;
- camera image and `/camera/imu` are present in 34/36 trajectories;
- `street_09` and `street_010` do not contain the audited camera streams;
- `hall_05 /camera/imu` has one strict header reversal at sample indices
  53375 -> 53376 with delta -49.212455 ms;
- large monotonic `/camera/imu` startup/header anomalies occur in
  `lift_02`, `street_06`, `room_dark_03`, `walk_01`, and `gate_02`;
- those monotonic anomalies are diagnostic only and do not create automatic
  invalid-sample masks;
- nearest-neighbor timing and common header-range intersection do not prove
  synchronization;
- no fixed offset has been estimated;
- no synchronization tolerance has been selected;
- synchronization remains UNVERIFIED;
- evaluation remains blocked.

Phase-3A immutable repository artifacts:

- `manifests/m2dgr_timing_evidence_index_v1.json`
- `manifests/m2dgr_trajectory_manifest_v1_phase3_timing_audited.json`

Phase 3 remains in progress. The next scientific task is actual synchronization
semantics and reference-to-estimator temporal association, not estimator
scoring.

---

## Phase-3B checkpoint — 2026-09-17

M2DGR synchronization-evidence characterization has reached a permanent
checkpoint.

Evidence now established:

- u-blox receiver UTC is independently observable on 18 GNSS-bearing
  trajectories;
- all compared `/ublox/fix` headers on those trajectories exactly match
  resolved receiver UTC;
- bag record time is not accepted as measurement time and does not exhibit a
  simple dataset-wide fixed relation to receiver UTC;
- estimator-input sensor headers behave consistently with a host/system-time
  epoch or mapping rather than native GNSS receiver UTC;
- this epoch behavior does not prove a shared physical oscillator;
- calibrated full-vector D435i/HandsFree gyro content provides strong evidence
  for near-zero IMU temporal association at native sample-scale resolution;
- the 28-trajectory clean cohort has best-lag range -11 to 0 ms and median
  -4 ms;
- zero-lag vector correlation has median 0.996203211;
- the median best-over-zero correlation gain is only 0.000086185;
- no scientifically defensible unique nonzero IMU fixed offset was identified.

Phase-3B therefore does NOT freeze the diagnostic -4 ms cohort median as an
offset.

The shared Phase-3A `sensor_clock` label was semantically ambiguous.
The Phase-3B successor replaces it with four distinct conservative per-stream
clock-domain labels.

These labels express uncertainty and are not a claim that the streams use
different physical clocks.

The data contract now explicitly states that equality of `clock_domain`
strings is not synchronization proof.

Phase-3B immutable repository artifacts:

- `manifests/m2dgr_synchronization_evidence_v1.json`
  - content SHA256:
    `a4e3e8dd18970a47f5cb50f4bb8ea3cb0e625f5f51d9eb0028bf34d953ee9966`
  - file SHA256:
    `58615c56442485fc488eeb47f72dd074f51c05c64cda258a91a8c4937b83ef91`
- `manifests/m2dgr_trajectory_manifest_v1_phase3b_sync_evidence.json`
  - content SHA256:
    `5cf660327636174912d5d304972758c1b230fa4446ab584ca4549c76fdd6f4db`
  - file SHA256:
    `95e7c97ae991538c2e7160c935cbaacf784b824eae7feecf1d7b540abe5ebb55`

Validated software state at this checkpoint:

- 81 TRUST-ROBOT unit tests passing;
- direct Phase-3B finalizer CLI works;
- Phase-3B successor contains 36 trajectories, 140 stream entries, and
  140 synchronization entries;
- synchronization remains `UNVERIFIED`;
- no fixed offset is stored;
- no synchronization tolerance is stored;
- evaluation readiness remains false.

Remaining Phase-3 work:

- camera-image-to-IMU physical capture timing;
- LiDAR-to-IMU physical capture timing;
- reference-to-estimator temporal association;
- independent calibration verification;
- scientifically valid validation/calibration partitioning before any
  data-selected synchronization tolerance is frozen.

Do not begin estimator scoring until these blockers are resolved by explicit
evidence and policy.

---

## Phase-3C checkpoint — 2026-09-17

M2DGR camera-image-to-D435i-IMU timing characterization has reached a
permanent evidence checkpoint.

Released-bag provenance findings:

- D435i color and united `/camera/imu` streams exist on 34/36 trajectories;
- released bags retain no RealSense metadata topics;
- released bags retain no raw camera gyro/accelerometer topics;
- exact RealSense driver revision/runtime configuration is not recoverable
  from the released topic set.

United-IMU pilot:

- `/camera/imu` runs at approximately 200 Hz;
- consecutive acceleration vectors do not show the simple held-last/copy
  fingerprint on `gate_01`, `hall_01`, or `room_01`;
- exact united-IMU construction remains unresolved.

A visual/gyro zero-lag method was frozen before lag analysis and then applied
unchanged to the predeclared 28-trajectory clean cohort.

All 28 trajectories processed successfully.

Aggregate zero-lag results:

- vector-correlation min/median/max:
  0.069851642 / 0.728267345 / 0.943895974;
- rotation-angle-correlation median:
  0.710193493;
- per-trajectory median rotation-error min/median/max:
  0.128085942 / 0.257421703 / 1.639230858 degrees.

Agreement is heterogeneous.

In particular, `room_dark_04`, `room_dark_05`, and `room_dark_06` demonstrate
that successful visual front-end processing is not sufficient evidence of
correct physical timing.

The frozen three-trajectory lag pilot produced primary vector-correlation
optima:

- `gate_01`: +23 ms;
- `hall_01`: -67 ms and at the scan boundary;
- `room_01`: -3 ms.

The improvements over zero lag are small/inconsistent and independent
rotation-error diagnostics select different lags.

No common nonzero camera-to-IMU fixed offset is scientifically supported.

The scan is not expanded to force an offset.

Phase-3C immutable repository artifacts:

- `manifests/m2dgr_camera_imu_synchronization_evidence_v1.json`
  - content SHA256:
    `d765f8ac13ff21dca23e289efef65fed31372189363e7fa61982e122514e190b`
  - file SHA256:
    `95ff9fdcaf2b74a9f7b118334f0fe3626bee3afe0916c3e09df4a7451d8425c7`
- `manifests/m2dgr_trajectory_manifest_v1_phase3c_camera_imu_sync_evidence.json`
  - content SHA256:
    `f599be5bb1b4d009fe77ff8eb33148880122f92f4bfe00f885ec18015d715387`
  - file SHA256:
    `4453544d437b31cb0ab16b090dfa2e710fab19cb1b90cb65b53d7651166eb156`

The Phase-3C successor is bound to the Phase-3B manifest content SHA256:

`5cf660327636174912d5d304972758c1b230fa4446ab584ca4549c76fdd6f4db`

Only 68 synchronization `method` fields for the two D435i streams change.
Clock domains, verification status, measurement-time basis, offsets,
tolerances, stream metadata, and non-camera synchronization entries remain
unchanged.

Validated software state:

- 89 TRUST-ROBOT unit tests passing;
- synchronization remains `UNVERIFIED`;
- fixed camera/IMU offset remains unset;
- synchronization tolerance remains unset;
- physical RGB capture synchronization remains unverified;
- evaluation readiness remains false.

Remaining Phase-3 blockers include:

- LiDAR-to-IMU physical capture timing;
- reference-to-estimator temporal association;
- common physical-clock verification;
- independent calibration verification;
- a valid validation/calibration split before any data-selected synchronization
  tolerance is frozen.

Do not resume camera/IMU lag tuning without new independent evidence that
resolves the released image-header physical capture semantics.
