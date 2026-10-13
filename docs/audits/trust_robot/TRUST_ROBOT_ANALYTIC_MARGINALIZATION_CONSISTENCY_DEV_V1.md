# TRUST-ROBOT nonlinear marginalization development V1

**Status:** manufactured mathematical development study; not
real-data or calibrated-uncertainty validation.

The existing 15D Schur marginalizer was evaluated using an affine
control and an SE(3)-inspired nonlinear relative-state residual.
The eliminated state was reoptimized at perturbed retained states.
The change in profiled nonlinear cost was compared with the
fixed-first-estimate retained prior and still-active factor.

- Affine far-point mean absolute cost discrepancy:
  8.82975174e-12
- Nonlinear near-point mean absolute cost discrepancy:
  3.98336458e-05
- Nonlinear far-point mean absolute cost discrepancy:
  0.0133301065
- Manufactured linear Gaussian Monte Carlo trials:
  512
- Matched noise mean NEES:
  14.909730
- Twofold true-noise mismatch mean NEES:
  59.638918

Cost differences use synthetic whitened objective units.
The separate Gaussian experiment's minimized residual chi-square
is not a sequential filter's innovation NIS.

No independent physical reference, empirical sensor covariance,
actual estimator posterior coverage, health supervision or
physical robot measurement was used.

Reproduction:

    PYTHONPATH=src python -B tests/trust_robot/test_analytic_marginalization_consistency.py -v

Detailed outputs are retained only in the project-local KIOS
experiment directory.
