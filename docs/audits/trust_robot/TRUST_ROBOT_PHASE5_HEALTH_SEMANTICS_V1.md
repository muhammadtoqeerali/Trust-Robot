# TRUST-ROBOT Phase-5 Three-State Health Semantics V1

## Purpose

Phase 5 requires a three-state modality-health model with exit evidence:

**Healthy/degraded/unusable classifier.**

Before classifier mechanics can exist, the three states and acceptable label
provenance must be defined prospectively.

This layer defines those semantics only.

It does not classify real data.

## Frontier finding

The Phase-5 frontier audit found:

- zero pre-existing exact `healthy/degraded/unusable` literals in the native
  or inherited Python state vocabulary;
- zero native TRUST-ROBOT health-named classifier declarations;
- inherited `imu_reliability` trust/decision machinery with different state
  semantics;
- inherited numeric policy, including an historical OOD threshold.

The inherited runtime policy is not adopted.

Historical numeric values remain inventory evidence only.

## State vocabulary

### healthy

An accepted, prospectively declared health-label provenance source identifies
the modality as nominal for its declared measurement role during the labeled
interval.

### degraded

An accepted, prospectively declared health-label provenance source identifies
a non-nominal impairment of the modality's declared measurement role, without
identifying that role as unusable during the labeled interval.

### unusable

An accepted, prospectively declared health-label provenance source identifies
the modality as unable to provide measurement information suitable for its
declared measurement role during the labeled interval.

## Interpretation boundary

A Phase-5 state is not itself:

- a localization-accuracy score;
- a diagnostic threshold;
- a reliability score;
- a Phase-8 factor weight;
- a Phase-9 suppression command.

Later phases may consume health state, but this semantic contract authorizes no
conditioning or suppression action.

## Label provenance

Future health labels require explicit, prospective provenance.

A candidate provenance source must be independent of:

- final estimator scoring;
- confirmation-test outcomes.

The following are insufficient by themselves:

- clean-branch identity;
- synthetic corruption identity;
- a diagnostic value;
- a diagnostic threshold.

Therefore the existing frozen Phase-4 clean records are not automatically
healthy and the existing Phase-3 EVENT_GAP-corrupted record is not
automatically degraded or unusable.

## Frozen Phase-4 input

The Phase-4 five-feature LiDAR diagnostic contract remains immutable.

This layer does not add, remove, normalize, aggregate or threshold those
features.

## Current classifier status

Not yet selected or implemented:

- classifier structure;
- training-label source;
- threshold;
- model;
- calibration.

No real M2DGR record receives a health label in this layer.

## Scientific boundary

Unchanged:

- reference data used: false;
- confirmation-test data used: false;
- ground-truth association performed: false;
- alignment performed: false;
- ATE computed: false;
- RPE computed: false;
- estimator scoring performed: false;
- evaluation ready: false.

Phase-5 exit evidence remains **NOT YET SATISFIED**.

The next step must establish scientifically admissible health-label provenance
or supervision before classifier mechanics or threshold selection.
