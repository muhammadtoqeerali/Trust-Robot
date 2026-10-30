# TRUST-ROBOT R135-A27-8 / A30-4 Implementation Audit

## Purpose

Add reusable physical-transform candidate validation and
independent evidence-artifact intake infrastructure.

These components perform structural checks. They cannot
independently establish physical measurement qualification.

## A27-8 transform preflight

The module requires an explicit `T_target_source`
direction convention and checks homogeneous SE(3)
matrix structure, proper SO(3) rotation, and optional
symmetric positive-semidefinite covariance.

Numerically valid covariance is not evidence of
independently measured calibration uncertainty.

Nominal URDF transforms remain nominal.

`bmi088_frame` has not been mapped to an independently
verified robot platform frame.

## A30-4 evidence intake

The intake ledger retains all thirteen frozen A23 requests.

The preflight validates candidate metadata and SHA-256
identity of supplied artifact bytes.

Different self-declared acquisition and witness tokens
cannot establish real witness independence.

A candidate artifact can be structurally consistent while
still being unsuitable for scientific evaluation.

For timing-related evidence, explicit clock domain,
event definition, and uncertainty method are required.

No time offset, association tolerance or physical
clock-accuracy claim is inferred.

## Scientific restrictions

- Qualified independent receipts: zero.
- Real factor admission: DENIED.
- M2DGR scientific gates: 11 CLOSED.
- Frozen split: 22 train, 7 validation-calibration,
  7 confirmation-test sequences.
- No held-out confirmation access or retuning.
- Physical clock accuracy: UNVERIFIED.
- Metric extrinsic calibration: UNVERIFIED.
- Independent six-DoF reference: UNVERIFIED.
- Physical localization accuracy: NOT ESTABLISHED.
- Estimator invoked: NO.

No real measurement receipt is accepted in this phase.

Future independent review is required before any
physical factor or localization scoring decision.
