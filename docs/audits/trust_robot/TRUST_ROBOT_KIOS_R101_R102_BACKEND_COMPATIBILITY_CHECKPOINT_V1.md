# TRUST-ROBOT R101–R102 prior-representation and compatibility checkpoint

Date: 2026-10-22. Parent Git commit `10ee70fb423930fce30eff919f7a5cb735771f60`.

## Verified engineering

R101: 28 regression tests; 16 manufactured prior conversions across
four scenarios and five independent gap-isolated segments. Reconstructed
Gaussian information/gradient and local quadratic energy with a square-root
information prior plus explicit additive constant. Direct S6 binding denied.

R102: 27 regression tests. Actual R95 and S6 prior objects exposed eight
integration blockers: coordinate namespace, clock epoch mapping, window
duration (100 vs 200 ms), synthetic gauge origin, retained prior dimension
(15 vs 30), node identity, stabilization versus anchor policy, and
cross-backend factor lineage.

The correct outcome is **integration blocked** pending a single-source,
coherent synthetic factor-graph design; matrix shape agreement cannot
substitute for frame, chronology, gauge, covariance, or factor ownership.

## Scientific restrictions

R95 is NOT merged with S6. The R101 fingerprint is not a digital signature.
R102 checks synthetic artifacts, not independent physical calibration.
No real sensor factors, verified physical time or extrinsics, independent
GT scoring, health training, ATE/RPE, raw ROSbag/GT data, or confirmation
access. The frozen 22/7/7 M2DGR split remains unchanged. All 11 gates CLOSED.
A user-reported M2DGR author email does not qualify physical sources;
no verified author response has been ingested.

## Next phase

Construct a shared synthetic estimator input source, with one coherent
chronology and factor ledger, before testing nonlinear backend transfer.
