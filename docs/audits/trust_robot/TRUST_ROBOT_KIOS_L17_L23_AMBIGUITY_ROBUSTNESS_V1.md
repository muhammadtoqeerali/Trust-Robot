# TRUST-ROBOT KIOS — L17-L23 Research Audit

Date: 2026-10-15

Parent GitHub commit:
cd8ce09f169d1942eb44c28e460be4d78a3fcf77

## Context

The L10-L16 milestone restored all six selected synthetic LiDAR
scans to 16 valid returns and obtained diagnostic registrations for
all fifteen pairs. Longer-baseline ICP was inconsistent.

## L17 — Initialization

Seven chain-based seeds were tested on each of ten nonadjacent pairs.
Longer-baseline estimates remained sensitive to initialization and
could converge to different correspondence configurations.

## L18 — Bijective correspondence

A Hungarian one-to-one assignment experiment reduced direct-vs-chain
rotational disagreement on problematic pairs.

However, its nearest-neighbor fitting error could be worse than
that of the frozen identity-started ICP.

It is not a scientifically qualified replacement.

## L19 — Beam association

Each of the six scans had sixteen inferable configuration indices.

Using an inferred emitter index as a correspondence gave synthetic
geometric consistency with the short-range chain but does not prove
the same physical surface point was observed.

Leave-one-beam-out fits exposed sensitivity to individual returns.

## L20 — Ambiguity screen

An eight-feature exploratory diagnostic screen classified ten pairs:

- Three STRUCTURAL_REVIEW
- Three SENSITIVITY_REVIEW
- Four NOT_FLAGGED_DIAGNOSTIC_ONLY

Thresholds were not calibrated with independent sensor-failure data.

## L21 — Rule challenges

Passed 23 boundary probes, 80 adverse-metric mutations, six
in-memory evidence-tampering rejection tests and repeated derivation.

The original L21 pair-count assertion was corrected, with its
original source preserved locally.

These checks test software consistency, not failure-detection
accuracy.

## L22 — Point perturbations

All 60 pair evaluations from six deterministic point-coordinate
perturbation scenarios were recomputed.

No ambiguity-screen decision changed.

These perturbations are not calibrated physical noise.

The original L22 command-line argument assertion was corrected,
with its original source preserved locally.

## L23 — Structured stress

Eleven scenarios yielded 110 evaluable pair diagnostics.

Only five decisions changed.

- 20 mm single-return alteration: no decision changes.
- 80 mm single-return alterations: one decision change each.
- Tested shears: no decision changes.
- Tested coherent rotations: no decision changes.
- 80 mm coherent translation: no decision changes.
- Stale step-101 scan substitution: two decisions changed, including
  one reviewed pair becoming not flagged.
- Corrected point-order permutation: zero decision changes.
- Point-order permutation with stale emitter mapping: one changed.

The point-order negative control helps distinguish actual point
geometry from inferred-emitter association bookkeeping.

This does not establish successful physical sensor-fault detection.
The observed invariances reveal important blind spots, including
common-mode transformations affecting both direct registrations
and their chain reference.

## No scientific promotion

Do not treat unflagged pairs as valid estimator factors.

No independent ground-truth 6-DoF evaluation, cross-sensor exposure
synchronization, calibrated failure probabilities, sensor-health
labels or valid false-positive/false-negative estimates exist.

Do not alter the frozen Phase-2 frontend, prior sensor recordings,
historical evaluation split, or scientific gating rules.

## Archive and next work

Complete source snapshots and compact reports are in:

experiments/isaacsim_v16_l17_l23_ambiguity_robustness_v1/

Next: L24 sensor freshness/provenance and common-mode failure audit,
followed by evidence-driven choices about the multimodal estimator.
