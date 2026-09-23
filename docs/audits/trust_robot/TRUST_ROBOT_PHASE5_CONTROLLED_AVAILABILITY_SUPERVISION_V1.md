# TRUST-ROBOT Phase-5 Controlled Measurement-Availability Supervision V1

## Purpose

The Phase-5 health vocabulary and supervision-source protocol already require
prospective, measurement-role-grounded labels independent of final estimator
performance.

Existing M2DGR provides no LiDAR health/status stream.

The VLP-32C manufacturer manual documents measurement mechanics and supported
availability-changing controls, but does not define TRUST-ROBOT
healthy/degraded/unusable states.

The frozen LiDAR frontend additionally establishes a structural validity
boundary:

- finite XYZ;
- shape `(N,3)`;
- `N >= 3`.

That boundary is algorithmic admissibility, not a health threshold.

This layer defines a prospective controlled measurement-availability
supervision protocol.

It accepts no source and labels no real data.

## Independent baseline nominality

A no-intervention branch is **not sufficient by itself** to establish
`healthy`.

Every controlled receipt requires separate baseline-nominality provenance.

Therefore existing M2DGR clean data are not retroactively labelled healthy.

Phase-4 feature values, final estimator scores and confirmation-test outcomes
cannot provide that baseline-nominality receipt.

## Prospective conditions

### full

Required relation:

**identical measurement evidence**

A future accepted source may map this to `healthy` only when:

- baseline nominality was independently verified;
- the prospective control execution was independently verified;
- the complete measurement object was preserved exactly.

### partial

Required relation:

**strict proper subset**

A future accepted source may map this to `degraded` only when:

- baseline nominality was independently verified;
- intervention execution was independently verified;
- removal of a nonempty strict proper subset was independently verified;
- retained evidence remains structurally admissible to the frozen frontend.

No retained fraction, point count, ring count, azimuth width or concrete
intervention mechanism is selected by this layer.

### absent

Required relation:

**no retained measurement object**

A future accepted source may map this to `unusable` only when:

- baseline nominality was independently verified;
- complete unavailability was independently executed and receipted;
- the prospectively declared interval has no retained measurement object.

Absence may not be encoded as a zero Phase-4 feature vector.

## Phase-4 boundary

The five frozen features remain unchanged:

1. source point count;
2. target point count;
3. fixed-point iterations;
4. final correspondence count;
5. final nearest-neighbor RMSE.

No sixth availability feature is introduced.

The future health-model architecture may eventually require an explicit
availability branch around the five-feature classifier, but that architecture
is not selected here.

## Source acceptance status

Current state:

- baseline nominality source selected: false;
- specific partial intervention selected: false;
- specific absence intervention selected: false;
- numeric severity selected: false;
- accepted supervision sources: 0;
- real health labels: 0.

## Anti-leakage

TRAIN may support model construction where scientifically authorized.

VALIDATION may support prospective model/parameter selection where authorized.

CONFIRMATION_TEST may not define:

- supervision semantics;
- supervision sources;
- intervention severity;
- classifier structure;
- thresholds.

## Scientific boundary

This layer performs no:

- reference association;
- alignment;
- ATE;
- RPE;
- estimator scoring;
- classifier fitting;
- threshold selection;
- calibration.

Phase-5 exit evidence remains **NOT YET SATISFIED**.
