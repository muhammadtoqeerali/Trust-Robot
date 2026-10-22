# TRUST-ROBOT R84–R86 synthetic inertial rolling checkpoint

Date: 2026-10-21. Git parent: `885bf22f7454a85cee53b82f5d6a5cbd7d3eff3e`. Publication authorized from KIOS only.

R84: synthetic-only time-admissible signed-axis IMU packet segmentation, no gap interpolation, covariance/bias-corrected preintegration; 21 tests. R85: four-case segmented 15D covariance-whitened inertial factor graph, constructed endpoint consistency, no cross-gap factor; 21 tests. R86: actual SciPy nonlinear 15D rolling solves with a new synthetic fixed anchor per independent segment, local rank and residual-reduction checks; 21 tests. 63 synthetic regression tests plus five disposable tamper controls run at checkpoint time.

Twelve exact SHA-pinned source/test/results files, README, manifest and standalone verifier are archived at `experiments/trust_robot_r84_r86_synthetic_inertial_rolling_checkpoint_v1/`. Upstream frozen TRAIN lineage remains R83; no raw/individual sensor data are archived or reopened. The R86 target is manufactured from its own factor and is NOT independent GT. No physical trajectory validation, Schur-complement marginalization or clock/extrinsic qualification. No real factors, health labels/probabilities, ATE/RPE, private GT/ROSbags, confirmation_test or author-contact prerequisite. Eleven scientific gates CLOSED.
