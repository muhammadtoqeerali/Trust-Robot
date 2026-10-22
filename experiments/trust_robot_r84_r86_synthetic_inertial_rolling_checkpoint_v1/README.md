# TRUST-ROBOT R84–R86 gap-aware synthetic inertial rolling checkpoint

Parent Git commit: `885bf22f7454a85cee53b82f5d6a5cbd7d3eff3e` (R83).

- **R84:** Strict synthetic-only timestamp and IMU-axis packet admission, duplicate/out-of-order rejection, gap splitting without interpolation, bounded covariance/bias-corrected preintegration; 21 tests.
- **R85:** Explicit disconnected segment factor graph, fully correlated 15D covariance whitening using existing analytic preintegrator and residuals, manufactured endpoint closure checks, no cross-gap edges; 21 tests.
- **R86:** Synthetic rolling 15D nonlinear least-squares factor solves, one declared fixed gauge anchor per continuous segment, checked residual reduction, local Jacobian rank and gap resets; 21 tests.

The R86 optimizer solves against factor-consistent **constructed endpoints**, not independent reference truth. It does not demonstrate physical observability, measured-sensor localization accuracy, safe deployment, or probabilistic Schur-complement marginalization. The R84–R86 math cannot be applied directly to the previously archived SE3 IMU magnitude-only features: those features omit signed gyro/acceleration axes and unqualified physical timestamp semantics.

Recorded R81/R82 TRAIN summaries are upstream lineage only, not executed factors. Frozen 22/7/7 split unchanged. Eleven scientific gates remain CLOSED. No original GT, raw ROSbags, private reports or confirmation-test data in this checkpoint. No physical extrinsics, clock mapping, real fusion factors, health training, health probabilities or ATE/RPE authorized.

Standalone integrity verifier:

`python3 -B experiments/trust_robot_r84_r86_synthetic_inertial_rolling_checkpoint_v1/verify_checkpoint.py verify experiments/trust_robot_r84_r86_synthetic_inertial_rolling_checkpoint_v1`

Regression tests (from repository root; NumPy and SciPy required):

`PYTHONPATH=experiments/trust_robot_r84_r86_synthetic_inertial_rolling_checkpoint_v1/evidence/r86/dev:experiments/trust_robot_r84_r86_synthetic_inertial_rolling_checkpoint_v1/evidence/r85/dev:experiments/trust_robot_r84_r86_synthetic_inertial_rolling_checkpoint_v1/evidence/r84/dev:src python3 -B experiments/trust_robot_r84_r86_synthetic_inertial_rolling_checkpoint_v1/evidence/r86/dev/test_r86.py`
