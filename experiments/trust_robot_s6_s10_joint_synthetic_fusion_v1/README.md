# KIOS S6–S10 synthetic joint camera–LiDAR fusion checkpoint

Date: 2026-10-19. Parent Git commit: `ebe97e3ee3d3c9872b2b5643de5124bb0cfacf43`.

This archive extends the already published S1–S5 readiness checkpoint while preserving all scientific exclusions.

- S6: opt-in manufactured-fixture 15D nonlinear fixed-lag estimator retains independent camera and LiDAR constraints on the same edge, distinct assumed covariance, unique measurement identities and Schur prior factor ownership. 23 tests pass; four synthetic scenarios and 16 accepted windows.
- S7: local six-dimensional camera/LiDAR information, assumed covariance scaling, synthetic camera perturbation and nonlinear response. 22 tests pass after a one-line missing `canonical` import repair. Both failed original JUnit (21 pass, 1 fail) and corrected 22-pass JUnit retained.
- S8: assumed correlated 12D cross-modal covariance and manufactured camera conflict; three correlation scenarios; 27 tests pass; no automatic sensor suppression, health inference or physical threshold.
- S9: 15-case synthetic correlation/offset stress grid, three independent nonlinear stress solves and four runtime action refusals. 43 tests pass.
- S10: combined 219-case regression (104 legacy + 23 + 22 + 27 + 43), independent frozen evidence and cross-phase clean-trajectory SHA match across S6, S7 and S9.

All 30 frozen S6–S10 source/test/report/JUnit files are stored in `code/` and `evidence/`, pinned in `checkpoint_manifest_v1.json`, and checked by `verify_checkpoint.py`. The checkpoint intentionally excludes raw sensor bags, SQL databases, simulator assets, superseded repair scripts, and health labels.

**Scientific boundary:** manufactured data and assumed statistical independence do not verify real sensor relative-pose factors, extrinsics, capture timing, cross-modal synchronization, measured covariances, ATE/RPE, empirical health training, or physical fault-detection thresholds.

Next: separate post-checkpoint planning and implementation of physical camera/IMU/LiDAR sensor inputs with independently measured provenance, physical timing/extrinsic requirements, and source-specific factor/noise models. Preserve the M2DGR split and fail-closed gates. Do not enable real factor execution without independently verified evidence and authorization.

Verify: `python3 -B experiments/trust_robot_s6_s10_joint_synthetic_fusion_v1/verify_checkpoint.py`.
