# TRUST-ROBOT KIOS L31-L35 Provenance and Witness Audit

Date: 2026-10-16
Branch: kios-isaacsim-v15-integration
Parent commit: 2ac0a332bf6a5d749f5a75fe7d5a53572ea0e109

## L31: Fresh multimodal integrity and timing diagnostics

L30's 272 archived metadata events were checked against KIOS
source files. Fourteen distinct L30 source files were verified,
and sixteen in-memory adversarial mutations rejected.

Cross-run identical payload fingerprints:
camera 0/6, LiDAR 6/6, IMU 130/130,
scripted USD reference 130/130.

Timestamp differences were computed as software diagnostics,
not evidence of measured physical exposure synchronization.

## L32: Historical versus new source files

Twenty-eight files across original L13 and L30 were verified.
Matching content fingerprints corresponded to distinct file
inodes. Hash equality cannot distinguish deterministic
simulator output from a replay without additional evidence.

A coherently altered, self-rehashed unsigned metadata envelope
was shown insufficient for independent source authentication.

## L33: Prospective acquisition contract

All eleven scientific readiness requirements remained
independently unqualified. Four readiness/admission gates
remained denied.

Existing evidence lacked 142 sensor exposure definitions,
142 independent attestation references, six camera measurement
timestamps, and 130 independent reference orientations and
uncertainties. The contract specified source, timing,
calibration, independent 6DoF reference and held-out
evaluation requirements. Twenty challenges were rejected.

## L34: Separate post-capture software witness

An issuer produced a local challenge. A separate read-only
userspace witness verified sixteen L30 source files, while an
independent verifier rejected sixteen adverse receipt mutations.

The challenge was issued after the historical acquisition.
The witness therefore cannot retrospectively establish
physical acquisition authenticity.

## L35: Prospective software-order rehearsal

A fresh challenge preceded a twelve-record emulated transcript.
Source events were references to archived L30 camera and LiDAR
metadata. A separate process sealed the chain, and twenty-five
adversarial mutations were rejected.

The challenge, recorder and sealing-witness monotonic ordering
was checked on one untrusted host clock. This does not establish
cross-sensor capture-time synchronization or trusted chronology.

## Provenance

The package archives eight Python implementation snapshots and
twelve compact JSON/JSONL evidence artifacts, plus the README,
checkpoint manifest, independent verifier and updated project
documentation. Original L30 recordings remain outside the
repository and upstream hash-pinned evidence is preserved.

Challenges/nonces are historical public verification values,
not secret credentials or independently trusted attestations.

## Scientific status and next work

No physical sensor equivalence, independent six-DoF reference,
calibrated localization covariance, scientific ATE/RPE result,
health labels, validated fault-detection rates or estimator
pose factors are established.

Pose factors authorized: 0.
Health labels generated: 0.

L36 will design and falsify acquisition-time witness integration
before an actual instrumented Isaac Sim acquisition is attempted.
