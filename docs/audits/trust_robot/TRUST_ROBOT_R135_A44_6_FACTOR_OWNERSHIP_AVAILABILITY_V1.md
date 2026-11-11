# TRUST-ROBOT | R135-A44-6 | Synthetic LiDAR factor ownership and availability

**Scientific status:** reviewed *synthetic engineering integration*, not real measurement health, qualified physical 6DoF estimation, or robot actuation.

## Why this increment exists

A44-4 published an observation-aware synthetic shadow after showing that a missing manufactured LiDAR node frame can be concealed by otherwise numerically supported optimization windows. R135-A44-5 extends this by enumerating all 32 possible present/missing masks over the five *manufactured* estimator-node frames `(0,2,4,6,8)` and independently verifying six selected configurations against the **actual frozen synthetic frontend and solver implementation**.

## Technical contract and results

`factor_ownership_availability_bridge_v1.py` is an offline importable module which reuses `analytic_preintegrated_fusion.make_factors`, the frozen `analytic_marginalized_fusion` solver, and the separately published `observation_aware_support_shadow_v1` gate. It does not replace the estimator, modify residual weights, change covariance models, reassign Schur-prior ownership, infer causes or access live sensor data.

The LiDAR frontend adds an edge `(i,j)` for `j-i` in `{1,2}` only if both endpoint scans are marked available. On a complete five-node manufactured fixture it creates **7** edges. With frame `4` missing it creates **3** edges and the shadow holds windows `2,3`. With `0,2,4,6,8` all missing it creates **0** LiDAR edges, yet the synthetic inertial/prior-backed optimizer returns a five-state solution. The shadow correctly holds all four windows in that case. This result demonstrates the difference between a *solvable graph* and an *observation-complete graph*, not reliable physical operation. Six selective configurations, not all 32, were executed through the frozen frontend/estimator; all 32 were independently checked at the pure-mask/edge-model level.

A44-5 KIOS passed **137** tests (16 new plus 121 frozen published tests); private A44-5 receipt SHA-256 `f41f9b8340d45070a24dcb22cec9a87812cc202336eadc80ed21d368d6aaff45`. A44-6 retains the identical candidate source, rehomes 16 tests into `trust_robot` and adds three targeted end-to-end synthetic checks. The guarded publication reruns these 19 new tests, 121 frozen tests, and 165 prior A41/A42 private regressions = **305 selected tests**, with exact per-suite counts enforced before any Git staging.

## Safety and reproducibility boundaries

All measurements and masks used by this work are manufactured, and the `ANALYTIC_FIXTURE` origin gate rejects live or recorded sources. Availability masks are assigned synthetic experimental inputs; they are not independently measured device failures or ground-truth `healthy`, `degraded`, `unusable` states. A solver `SOLVED_SYNTHETIC` status does not justify physical tracking, attribution, reliability weights or robot control. No Nova SSH, physical bag, UNIVER dataset, sealed confirmation split, calibration, sensor driver, controller, actuation, return-home or emergency-stop is used.

The existing thirteen prospective physical witness requests remain unresolved, the eleven M2DGR scientific gates are closed, and the frozen 22 TRAIN / 7 validation_calibration / 7 SEALED confirmation_test split is unchanged. This publication contains bounded deterministic software and explanatory evidence only; all private receipts, raw sensor data, workstation paths, credentials and private A41/A42 experimental derivatives remain off GitHub.

**Next:** exercise source-ambiguous interventions and standalone causal-consistency falsification without claiming a real trained health classifier; only after independent physical time/extrinsic/reference qualification may any real factor be considered under separate authorization.
