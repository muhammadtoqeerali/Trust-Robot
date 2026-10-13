# TRUST-ROBOT seeded estimator stress development V1

**Status:** offline manufactured-input development evidence.

The actual nonlinear 15D fixed-lag estimator was executed with
synthetically perturbed IMU gyroscope and specific-force readings.
Five-node and 12-node trajectories were studied under clean
and LiDAR-dropout conditions.

The same seeded standardized noise draws were used for paired
mild and severe levels. Existing numerical-support reporting
remained active. Missing or invalid nonlinear solves are counted
as unavailable rather than reported as nominal estimates.

## Execution summary

- `five/clean`: 5 nodes, 12/12 solves accepted, 0 unavailable.
- `five/lidar_dropout`: 5 nodes, 12/12 solves accepted, 0 unavailable.
- `twelve/clean`: 12 nodes, 12/12 solves accepted, 0 unavailable.
- `twelve/lidar_outage`: 12 nodes, 12/12 solves accepted, 0 unavailable.

## Interpretation

Reported trajectory differences measure sensitivity relative to
the unperturbed **estimator output**, NOT independent truth.
Perturbation magnitudes are manufactured and were not selected
from physical sensor-noise calibration.

These results do not establish statistically calibrated estimator
uncertainty, real-world localization accuracy, physical
observability, attack resilience or safe closed-loop behavior.

The health-conditioning execution gates are unchanged and closed.
No Isaac Sim GPU or physical robot was used.

Reproduction:

    PYTHONPATH=src python -B tests/trust_robot/test_analytic_estimator_seeded_stress.py -v

The complete results, seeds, precise noise settings and SHA256
evidence remain in the project-local KIOS experiment directory.
