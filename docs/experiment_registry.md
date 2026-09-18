

## Reliability evaluation registry V1

The reliability evaluation population is frozen before corruption-policy
definition.

The historical subject partitions are reused prospectively as follows:

- historical train -> development;
- historical validation -> calibration;
- historical test -> final test;
- OnField subjects 999 and 1000 -> augmentation-only.

Frozen trial counts are:

- development: 4,628 trials;
- calibration: 447 trials;
- final test: 1,116 trials;
- augmentation-only: 2 trials.

Frozen historical protected-model window counts are:

- development: 510,479;
- calibration: 89,868;
- final test: 366,507;
- augmentation-only: 220,472.

Development is the only partition allowed to define the P0 corruption
policy, including corruption families, severity values, admissibility,
placement rules, and deterministic generation rules.

Calibration is not allowed to redefine that corruption policy. It is
reserved for reliability threshold, persistence, and operating-point
selection after the corruption policy is frozen.

Final-test outcomes may not influence corruption-policy design,
thresholds, persistence, OOD operating points, or other reliability
parameters.

Corruption is applied only after partitioning and must preserve paired
clean/corrupt evaluation.

UniVRFall and KFall trials with verified raw filename pairing are
eligible for acquisition-level P0 evaluation. OnField is excluded from
acquisition-level P0 because raw trial mapping remains unverified.

Historical KFall trials `106/27/1` and `106/27/5` contain zero protected
historical CNN windows. They remain part of provenance and
acquisition-level accounting but are excluded from model-coupled P0
evaluation. Later current-generation windows must not substitute for
the protected historical representation.

Synthetic P0 truth does not upgrade runtime acquisition provenance.

The machine-readable frozen registry is
`data/manifests/reliability_eval_registry_v1.json`.

## P0 corruption policy V1

The P0 synthetic corruption policy is frozen using development-partition
statistics only.

Calibration and final-test statistics were not used to define corruption
families, severity values, placement rules, channel-selection rules, or
deterministic seed generation.

The frozen severity grid is:

- FRAME_GAP: remove 1 / 4 / 8 samples;
- FRAME_REPEAT: repeat 2 / 5 / 10 samples;
- CHANNEL_FREEZE: freeze 5 / 10 / 20 samples;
- TIMING_PERTURBATION: add 10 / 40 / 90 ms at one internal boundary;
- RANGE_CLIP: symmetric per-channel clamps derived respectively from
  development absolute q0.999 / q0.995 / q0.990.

For RANGE_CLIP, lower quantile means stronger clipping.

The RANGE_CLIP values are synthetic development-derived empirical clamps.
They are not verified physical sensor rails and must not be reported as
hardware clipping limits.

Corruption placement is deterministic and domain-separated using SHA-256.
No-op instances are forbidden. A trial/severity combination that has no
valid mutating placement is recorded as NOT_ADMISSIBLE rather than being
silently replaced by another corruption.

All corruptions are generated after partitioning and retain paired
clean/corrupt evaluation.

Runtime attribution remains provenance-gated:

- KFall FRAME_GAP may become a hard runtime cause from qualified raw
  FrameCounter discontinuity;
- UniVR synthetic FRAME_GAP truth does not qualify its derived counter;
- FRAME_REPEAT remains non-hard without independent data-path evidence;
- CHANNEL_FREEZE remains suspect-only;
- RANGE_CLIP synthetic truth does not establish a physical rail;
- timing truth does not by itself establish a hard timing cause.

No calibration or final-test corruption instances exist at this policy
freeze.

The machine-readable policy is
`configs/integrity/p0_corruption_policy_v1.json`.

## P0 development specification V1

The frozen P0 corruption policy was applied prospectively to the
development acquisition population only.

Development population:

- KFall: 3,829 trials;
- UniVRFall: 792 trials;
- total: 4,621 trials.

Every acquisition-eligible development trial received one attempted
specification for each of five corruption families at each of three
severity levels, for 69,315 attempted trial-family-severity combinations.

No calibration or final-test raw files were opened during development
specification generation.

No complete corrupted datasets were materialized. Each admissible
specification was validated against the tested P0 injector and retained
as a deterministic, regenerable specification.

Development admissibility result:

- admissible: 65,771 / 69,315;
- not admissible: 3,544 / 69,315.

All FRAME_GAP, FRAME_REPEAT, CHANNEL_FREEZE, and TIMING_PERTURBATION
attempts were admissible at all three severities.

All 3,544 inadmissible attempts were RANGE_CLIP and had reason
`NO_RANGE_EXCEEDANCE_FOR_SEVERITY`.

RANGE_CLIP admissibility was:

- KFall low: 2,181 admissible / 1,648 not admissible;
- KFall medium: 2,864 / 965;
- KFall high: 3,222 / 607;
- UniVRFall low: 488 / 304;
- UniVRFall medium: 781 / 11;
- UniVRFall high: 783 / 9.

The frozen severity policy was not changed in response to these
admissibility results. Inapplicable trial/severity combinations remain
explicitly NOT_ADMISSIBLE rather than being replaced by another
severity or placement rule.

Historical KFall trials `106/27/1` and `106/27/5` remain eligible for
acquisition-level P0 analysis but are not model-coupled because the
protected historical dataset contains zero CNN windows for those trials.

The full generated development manifest is a reproducible local
artifact rather than a tracked repository object. Its content SHA-256 is
`103ef03864457269a348fd304c5f350c408bea02f55a57cff7940e1525f2d69e`.

The validated compact derivative has content SHA-256
`58c00ab35be2e8c34d4a68ca48b379a7ccce83bafa25bcd143a9e221e5628608`.

The repository tracks a per-trial cryptographic generation receipt at
`data/manifests/p0_development_spec_receipt_v1.json`. The receipt
preserves each clean-stream fingerprint and a digest of the exact 15
family/severity outcomes for every development trial, including
specifications, specification IDs, injection IDs, corrupt-stream
fingerprints, and rejection reasons.

Calibration and final-test corruption generation had not occurred at
this freeze.

## P0 calibration specification V1

The frozen P0 corruption policy was reused unchanged to generate the
calibration corruption specifications.

Calibration acquisition population:

- KFall: 314 trials;
- UniVRFall: 132 trials;
- total: 446 trials.

The calibration OnField trial remains excluded from acquisition-level
P0 because its raw trial mapping is unverified.

All 446 acquisition-eligible calibration trials are also eligible for
model-coupled evaluation.

Every eligible calibration trial received one attempted specification
for each of five corruption families at each of three severity levels,
for 6,690 attempted combinations.

Generation reused the development implementation for deterministic
SHA-256 placement, channel selection, admissibility, timing-unit
conversion, and validation against the tested P0 injector.

The frozen corruption policy, severity grid, placement rules, seed
derivation, and admissibility rules were not modified using calibration
data.

No development raw files and no final-test raw files were opened during
calibration specification generation.

No task predictions, detector outcomes, detector thresholds,
persistence settings, or OOD operating points were evaluated or
selected during specification generation.

Calibration admissibility result:

- admissible: 6,352 / 6,690;
- not admissible: 338 / 6,690.

All FRAME_GAP, FRAME_REPEAT, CHANNEL_FREEZE, and TIMING_PERTURBATION
attempts were admissible at every severity.

All 338 inadmissible attempts were RANGE_CLIP with reason
`NO_RANGE_EXCEEDANCE_FOR_SEVERITY`.

RANGE_CLIP calibration admissibility was:

- KFall low: 171 admissible / 143 not admissible;
- KFall medium: 234 / 80;
- KFall high: 250 / 64;
- UniVRFall low: 83 / 49;
- UniVRFall medium: 130 / 2;
- UniVRFall high: 132 / 0.

These calibration admissibility outcomes do not modify the already
frozen corruption policy.

The complete generated calibration specification manifest is retained
as a reproducible local artifact with content SHA-256
`f95ada2da8355b21f43aac6d7d9438eeebf70305f21e7a1e3a1d66c11fd498a6`.

The repository tracks the cryptographic calibration generation receipt
at `data/manifests/p0_calibration_spec_receipt_v1.json`.

Integrity detector thresholds and persistence had not been selected at
this freeze, and final-test corruption generation had not occurred.

## Integrity calibration protocol V1

Before reading calibration detector outcomes, the integrity calibration
search space, clean-data feasibility constraints, selection rules,
failure policy, and runtime evidence boundary were frozen.

The protocol keeps KFall raw FrameCounter FRAME_GAP as the only
historical-P0 hard integrity cause available from the current recovered
metadata.

CHANNEL_FREEZE remains suspect-only.

Timing-envelope calibration is diagnostic/observation-only in
historical P0 V1 and cannot promote ACQ_TIMING_VIOLATION into the hard
cause set.

FRAME_REPEAT, BUFFER_STALL, FIFO_OVERRUN, and RANGE_CLIP remain
unsupported as hard historical-P0 causes under the frozen provenance
contract.

Calibration is forbidden from changing the corruption policy,
calibration corruption specifications, search grid, clean constraints,
or causal qualification rules after detector outcomes are observed.

Final-test data and final-test P0 generation remain unavailable until
the selected calibration operating point is frozen.

The machine-readable protocol is
`configs/integrity/integrity_calibration_protocol_v1.json`.

The human-readable freeze record is
`docs/operating_point_freeze.md`.


## M2DGR Phase-3E reference temporal-association evidence

Phase-3E reference-to-estimator temporal-association characterization is frozen
as a conservative evidence checkpoint.

Permanent evidence:

`manifests/m2dgr_reference_temporal_association_evidence_v1.json`

Content SHA-256:

`505c1b63fc7e74907ce915472b243230a2cc86017248edaca255b5be5bc079fd`

File SHA-256:

`4f6580c6a0b06b4089990adcc700b5d823a748bacacfc0f00c3dd3b4169d9117`

The evidence binds nine frozen Phase-3E staging artifacts covering timestamp
coordinates, interval overlap, rotation association, translation diagnostics,
and RTK/INS receiver-UTC coordinate characterization.

The Phase-3D trajectory manifest remains authoritative and byte-identical with
file SHA-256:

`67fe08bff676689dd212da03dce8e16ecee277c96f38f752d0d38a5e4e54cf6f`

No Phase-3E successor trajectory manifest exists.

Frozen scientific interpretation:

- numeric timestamp overlap is not synchronization proof;
- RTK/INS rotation content is strongly consistent at nominal timestamp
  coordinates across the 16-trajectory cohort;
- mocap rotation content is weak and heterogeneous across the 9-trajectory
  cohort;
- translation-content results are not robust to temporal-support definition;
- Leica does not support the approximately 100 ms LiDAR-native translation
  construction without interpolation;
- RTK/INS reference ranges numerically contain receiver-UTC fix ranges on all
  16 trajectories, but this does not establish RTK pose measurement-time
  semantics;
- no lag search, fixed offset, association tolerance, interpolation policy,
  evaluation interval, or automatic exclusion rule is selected;
- reference-to-estimator temporal association remains unverified;
- synchronization remains unverified;
- evaluation readiness remains false.

Post-checkpoint TRUST-ROBOT test gate:

- 99 tests run;
- 99 passed;
- Phase-3D manifest immutability check passed;
- Phase-3E permanent evidence validation passed.
