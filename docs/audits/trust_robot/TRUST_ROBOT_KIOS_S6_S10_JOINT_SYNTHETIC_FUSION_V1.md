# KIOS S6–S10 manufactured 6DoF joint-fusion audit

Date: 2026-10-19. Parent commit: `ebe97e3ee3d3c9872b2b5643de5124bb0cfacf43`.
Archive: `experiments/trust_robot_s6_s10_joint_synthetic_fusion_v1/`.

S6 added separate synthetic camera + LiDAR factors to the 15D fixed-lag estimator at the same pose edge, preserving Schur factor ownership. Twenty-three tests passed; four scenarios yielded 16 accepted window solves. Covariances are assumed—not empirically identified.

S7 checked local additive information under an assumed independence model, covariance sensitivity and deliberate 0.08 m manufactured camera perturbation. The initial 21-pass/1-failure JUnit is preserved alongside the repaired 22-pass JUnit; the engine was repaired for a missing imported canonical JSON helper.

S8 evaluated three 12D assumed correlation models (-0.25, 0, +0.35) and a manufactured 0.2 m conflict. Twenty-seven tests passed. No sensor suppression or three-state health decision occurred.

S9 independently recalculated a 15-case manufactured correlation/offset grid, three nonlinear stress solves and rejected four runtime actions. Forty-three tests passed.

S10 reran all nine original estimator suites and S6–S9 tests: 219/219 passed (104 + 23 + 22 + 27 + 43). The clean synthetic trajectory fingerprints matched across S6, S7 and S9. Independent S10 validation passed.

Thirty SHA-pinned source, test, report and XML evidence artifacts are archived with a self-verifier and immutable documentation hashes. No physical sensor synchronization, real camera/LiDAR pose factors, full extrinsics, empirical noise independence, measured GT, ATE/RPE, health labels, training or live simulator authorization. No raw data or SQLite archived.

Next: research implementation with genuinely recorded sensor-derived factor measurement paths, gated behind physical calibration, timestamp and independent reference qualification; synthetic code readiness must not be promoted to real-world accuracy evidence.
