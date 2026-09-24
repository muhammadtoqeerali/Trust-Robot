# TRUST-ROBOT Phase-7 Auxiliary Consistency Contract V1

Status: software architecture implemented locally; numeric consistency
definitions and empirical consistency evidence remain unselected/deferred.

## Authoritative Phase-7 scope

The project defines Phase 7 as auxiliary cross-modal and
kinematic/temporal consistency evidence.

The authoritative evidence families are:

- visual motion versus LiDAR motion;
- inertial propagation versus exteroceptive odometry;
- temporal pose continuity;
- kinematic/proprioceptive motion;
- platform motion bounds;
- residual histories.

These are represented as evidence-family interfaces only.

No numeric consistency metric is selected.

## Inconsistency versus attribution

The authoritative semantics are preserved:

- pairwise disagreement establishes inconsistency;
- pairwise disagreement alone does not identify the responsible modality.

Attribution may require:

- modality-specific diagnostics;
- another sufficiently informative modality;
- a trusted physical constraint.

Current responsible-modality attribution remains unauthorized.

Ambiguous evidence must remain explicit rather than receive a fabricated
confident label.

The project also names estimator-degraded reporting for ambiguous cases, but
Phase-9 estimator-status logic is not implemented here.

## Missing physical/numeric definitions

This contract does not select:

- a numeric consistency measure;
- temporal tolerance;
- time offset;
- interpolation rule;
- cross-modal transform;
- kinematic model;
- trusted platform motion bound;
- residual-history definition or window.

Therefore consistency computation is fail closed in the current state.

## Phase boundaries

Phase 7 does not implement:

- the Phase-8 health-aware factor weight;
- current-innovation factor conditioning;
- information/covariance rescaling;
- Phase-9 suppression;
- recovery;
- fallback;
- hysteresis;
- estimator availability logic.

The historical IMU-HAR OOD method and threshold are not adopted.

GNSS remains optional and is not promoted to a core modality.

## Data and evaluation boundary

No validation or confirmation data are opened.

No reference data are used.

No ATE/RPE or final scoring is authorized.

No physical hardware is accessed.

## Artifact hashes

- config: `79eb3151344c5dd9e4f4212467f24cc2e956ce16689e808ae1008539f80efce6`
- module: `72e999b63950ff8070a978bcfac81cb54c598d97c0e539c28bfd92648a34124a`
- tests: `c18ea0c3a1c914d1f7915a8fed6ef56e477d7e42ea9f01c3140e5e1264eb382b`
- Phase-6 freeze: `a022c1923d340bb2fc40a2c7515199ab92d7745f95546ca055ee63fb11f1f2e6`
- Phase-5 freeze: `457a42c3778731307b1371208407fca6d7cf8e604718f81138034479deb0d09a`
- Phase-5 diagnostic-channel config: `de6656d35e24162dcd3ff489f21b735396c2457dae526a13be9790bb88bdf485`
- authoritative master context: `84a4dfebc38cb38d9d3d91bb20ce4134b53d03843108433adee468a995ca4e48`
- phase plan: `de26e1f0dd5029b014b9ac2412f21543ce782a4f22141d0f63f534d2763633b3`
- Phase-7 frontier report: `21dee84f459f7c50d637826dffd7b237aa8b640e07f13e859f62063b246db54a`
- Phase-7 frontier JSON: `6a4fb99843600674b963f484f70bb245ec0758aa7139fa46101a1ce7cab8599a`
- authoritative scope report: `5b23f88b200c263f98232eb290dd6faed8e1eee584efe26ea414c5cb60ce6d49`
- authoritative scope JSON: `0cd1258c3389643d6a0295dfa84cdd9bf10ac74211e4c04f4f77281ff97c67f5`
