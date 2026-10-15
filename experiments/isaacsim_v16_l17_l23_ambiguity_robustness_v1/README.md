# TRUST-ROBOT KIOS L17-L23 Ambiguity and Robustness Checkpoint

This package is a compact, SHA-pinned engineering research archive.

## Research completed

- L17: Identity-started and chain-seeded ICP with seven fixed seeds.
- L18: Experimental one-to-one Hungarian correspondence comparison.
- L19: Inferred beam association and leave-one-beam-out sensitivity.
- L20: Eight-feature exploratory ambiguity screen.
- L21: Rule boundary, adverse-metric and evidence-tampering challenges.
- L22: Six point-perturbation scenarios, 60 registration screens.
- L23: Eleven structured-stress scenarios, 110 registration screens.

## L23 finding

All 110 structured-stress pair evaluations were recomputed.

Five decisions changed. Correcting the point-index mapping after
permuting point storage preserved every decision. Leaving the mapping
stale changed one decision.

Some deliberate geometry changes, including coherent rotation and
translation, did not alter the screen classification. Replacing step
101 with the step-91 scan could even reduce an existing warning.

This illustrates a major limitation: the short-range trajectory and
direct registration may be affected together, making the disagreement
metric unable to identify a common-mode fault.

A classification that is NOT_FLAGGED_DIAGNOSTIC_ONLY does not certify
a correct pose, healthy sensor, or scientifically accurate localization.

## Provenance

L21 and L22 source snapshots contain the validated corrections to
their original assertion bugs. The original pre-repair source backups
remain locally on KIOS; their hashes are recorded in the manifest.

Only implementation snapshots and compact JSON evidence are archived.
No raw camera, LiDAR, IMU or runtime recordings are committed.

The experimental algorithms do not replace the frozen LiDAR frontend.

## Scientific restrictions

- No independently verified localization ground truth
- No calibrated sensor-fault detection thresholds
- No physical exposure synchronization claim
- No validated false-positive or false-negative rates
- No authorized sensor-health labels
- No qualified estimator pose factors

## Verify the checkpoint

Run from the GitHub repository root:

python3 -B experiments/isaacsim_v16_l17_l23_ambiguity_robustness_v1/verify_checkpoint.py

## Next research phase

L24: examine frame freshness, sensor-provenance checks and
common-mode failure detection independently of the ICP chain.
