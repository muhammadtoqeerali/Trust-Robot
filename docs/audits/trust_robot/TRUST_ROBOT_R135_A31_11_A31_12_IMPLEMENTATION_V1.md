# TRUST-ROBOT R135-A31-11 / A31-12 Implementation

## Scope

Audit independent experimental condition counts in
prior synthetic ensembles.

Perform fixed-seed synthetic sensitivity comparisons
without modifying any physical evidence or dataset.

## A31-11 Paired-seed comparison

Five software replay scenario labels are represented
by only two distinct six-step synthetic delivery masks.

Replicated masks with identical seed and synthetic noise
must not be counted as independent failure experiments.

The audit verifies:

- Frozen synthetic seed correspondence
- Exact delivery-mask agreement
- Per-policy synthetic update accounting
- Recomputed descriptive ensemble summaries
- Identical toy outcomes for identical paired conditions

It reports paired toy RMSE/NEES differences and
synthetic update-count differences.

No statistical significance or physical generalization
is claimed.

## A31-12 Sensitivity analysis

A deterministic synthetic comparison varies:

- Three injected outlier magnitudes
- Two toy innovation thresholds
- Two toy process variances
- Three distinct synthetic availability profiles
- Four fixed synthetic seeds

The grid contains 36 parameter/profile cells and
144 paired synthetic trajectory runs.

The synthetic noise draw for each seed remains
identical across declared experimental conditions.

The three profiles distinguish continuous delivery,
injected dropout/recovery, and fully withheld delivery.

All results are toy algorithm sensitivity diagnostics.

## Physical and dataset restrictions

- A23 independent qualifying receipts: 0 of 13.
- Physical BMI088 frame mapping: UNVERIFIED.
- Physical event-time clock accuracy: UNVERIFIED.
- Capture-applicable calibration: UNVERIFIED.
- Independent six-DoF reference: UNVERIFIED.
- Physical localization accuracy: NOT ESTABLISHED.
- Real factor count: ZERO.
- Real factor admission: DENIED.
- Historical M2DGR admission gates: 11 CLOSED.

M2DGR frozen split remains 22 training,
7 validation-calibration and 7 confirmation-test.

No held-out dataset tuning is performed.
No robot motion, new capture, estimator execution,
or Git publication occurs.
