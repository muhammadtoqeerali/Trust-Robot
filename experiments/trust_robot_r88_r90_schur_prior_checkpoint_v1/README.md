# TRUST-ROBOT R88–R90 synthetic Schur prior integrity checkpoint

Parent Git commit: `c147ccaba711b8a600294b2df2b8f64f6ef6bcd4`.

R88 independently compares a **local linearized Gaussian** Schur-condensed prior against a full-batch least-squares system on four synthetic inertial scenarios (21 tests). R89 verifies exact frozen-quadratic coordinate recentering and measures genuine nonlinear Jacobian drift; it DOES NOT claim to refresh eliminated nonlinear factors (21 tests). R90 exercises a fail-closed synthetic prior admission guard: matrix definiteness/conditioning, provenance, bounded coordinate shifts, stale prior claims and cross-gap reuse (27 tests, 30 adversarial operations rejected, 15 valid recentering trials).

The guard's fingerprint is a deterministic integrity digest, **not** an authentication signature. Synthetic numerical thresholds are development controls, **not** empirical hardware safety thresholds. Information is never copied across timestamp gaps. This is not a complete nonlinear probabilistic marginalizer: no full posterior consistency or physical observability has been established.

The 22/7/7 frozen M2DGR split and all eleven physical/scientific gates remain unchanged. R88–R90 reuses synthetic fixture-only signed IMU packets. It does not import or process real raw IMU axes, original ROSbags, GT, private Verona source reports, or sealed confirmation-test data. No real LiDAR-camera-IMU fusion factors, real health labels, real trust weights, health training, or ATE/RPE were authorized.

Standalone archive verification:

`python3 -B experiments/trust_robot_r88_r90_schur_prior_checkpoint_v1/verify_checkpoint.py verify experiments/trust_robot_r88_r90_schur_prior_checkpoint_v1`

Archived regressions from the Git checkout (NumPy/SciPy required, standard Python test runner):

`A=experiments/trust_robot_r88_r90_schur_prior_checkpoint_v1; P=experiments/trust_robot_r84_r86_synthetic_inertial_rolling_checkpoint_v1; PYTHONPATH="$A/evidence/r90/dev:$A/evidence/r89/dev:$A/evidence/r88/dev:$P/evidence/r86/dev:$P/evidence/r85/dev:$P/evidence/r84/dev:src" python3 -B "$A/evidence/r90/dev/test_r90.py"`

Next: evidence-first physical qualification audit (authoritative clock events, reference frames, signed sensor channels, extrinsics, and source traceability), and only then measured-sensor fusion and reliability research. Further synthetic checks cannot substitute for missing physical receipts.
