# TRUST-ROBOT — KIOS V16 L1–L3 registration diagnostics and fail-closed admission checkpoint

Date: 2026-10-15. Scope: offline synthetic engineering qualification only.

## Predecessor

Branch: `kios-isaacsim-v15-integration`; parent Git commit:
`555edb8c0c0490c3791c0bdc3bc8a771ab11309c`.
V16.28–V16.29 source and SHA-bound reports reside in
`experiments/isaacsim_v16_recovery_v1/`. The actual recorded sensor
arrays remain local on KIOS and were not published.

## L1 outcome

The frozen Phase-2 nearest-neighbor/Kabsch frontend and frozen Phase-4
five-field diagnostic extractor processed genuine pre-Replicator GMO-derived,
VALID-flagged sensor-frame XYZ scans from V16.28. Six scan frames at steps
`[51,61,71,81,91,101]` provided `[16,16,16,16,16,4]` samples: 84 points.
For clean and frame-3 every-other-point sparsified conditions, eight of ten
registration pairs yielded deterministic algorithm diagnostics. Two pairs
incident on the four-point final scan were refused under an eight-point
**engineering-only** availability rule. Source bytes and original recordings
were unchanged. L1 derived report SHA-256:
`a120e376d7055a19fe5948f0df9b15b8b824399e967583e745da3258c55c553b`.

## L2 outcome

All four nonsparse clean pairwise registration baselines were reproduced.
Spatial smallest/largest singular-value ratios of initial five scans were
about 0.0041–0.0042. Simple locally linearized rotational information
ratios for the six scan sets were about 0.00023–0.00084; no calibrated
measurement covariance or complete 6-DoF observability was established.
With deterministic *synthetic*, explicitly uncalibrated, maximum 2-mm
per-coordinate perturbations, candidate rotations changed by about 10.3,
20.5, 31.1, and 71.6 degrees across four analyzed pairs while nearest-
neighbor RMSE remained around centimetre scale. Convergence and small fit
residuals do **not** validate the estimated transforms. USD scripted base
motion (about 0.04 m between frames) was inspected only as a synthetic
internal-consistency diagnostic, **not independent reference ground truth**.
L2 derived report SHA-256:
`4cad184b44bd9d99ebb762a7dcbe04e0c18bd42265568057aaf7f7a1598922c6`.

## L3 outcome

All ten registration candidates were denied admission: eight nonsparse
unqualified candidates and two sparse endpoint cases. No estimator pose
increment, information matrix, physical measurement timestamp or health
label was emitted from this gate. Eight intentional mutations of provenance,
synchronization flags, candidate admission, geometric claims, sparse-pose
status and noise-calibration claims were rejected. L3 source and report are
SHA-bound; negative tests are re-executable. L3 derived report SHA-256:
`14aacc536ee224e7ca2cfcc42fceb5486b448d588ea4c344b50f102c68ad81d6`.

## Reproducibility and future-agent rules

Read `experiments/isaacsim_v16_l123_registration_gate_v1/README.md` and
`checkpoint_manifest_v1.json`. The three source files in `code/` are
**byte-exact copies of the locally executed candidates**. Versioned reports
in `evidence/` match local SHA-256 results. The offline package verifier
rechecks source/report SHA hashes, lineage, L3 denial decisions, and eight
negative tests. The checkpoint itself also required rerunning L1, L2, and
L3 with the versioned copies and exactly comparing newly generated report
SHA-256s before publication. Do not modify the historical source, scene,
recordings, V15/V16 experiments, or frozen Phase-2/Phase-4 interfaces.

This is **not** a positive factor-admission qualification, a confidence
calibrator, a trained health classifier, a proper six-degree-of-freedom
localization score, a real-world fault/attack-resilience evaluation, or
physical sensor synchronization evidence. Missing camera exposure metadata,
point firing-time calibration, independently validated extrinsics, robust
observable geometry and independent reference pose remain unresolved.
Do not promote registration RMSE into ATE/RPE or synthesize health labels.
Existing M2DGR split, evaluation, SE4 training, SE5 and SE9 gates remain
unchanged and blocked where previously blocked.

Next: separate new evidence-gated acquisition geometry design and scientific
timestamp/frame/reference qualifications from the already-frozen L1–L3
engineering diagnostics. Any new estimator admission policy must require
additional independent, predeclared evidence and cannot be inferred from
synthetic perturbation tests alone.
