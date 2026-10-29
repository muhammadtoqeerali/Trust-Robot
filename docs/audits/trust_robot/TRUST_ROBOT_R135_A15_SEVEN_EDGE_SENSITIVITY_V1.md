# R135-A15: Seven-edge synthetic 15D estimator sensitivity

Status: UNTRUSTED_SYNTHETIC_NUMERICAL_DIAGNOSTIC_ONLY.

## Research question of this development experiment

How does the unchanged analytic Schur-marginalized 15D
estimator respond to removing one LiDAR pose factor
and restoring that edge with manufactured depth-camera
observations under fixed ideal, noisy and biased modes?

This is a numerical software study, not a physical
sensor-robustness result.

## Experimental matrix

- 1 synthetic LiDAR-only baseline.
- 7 single-edge LiDAR removals.
- 21 synthetic camera restorations:
  7 edges times 3 manufactured observation modes.
- 29 unique configurations in total.

All configurations use the same manufactured motion
model, five state nodes and four preintegrated IMU factors.

## Source provenance

LiDAR relative-pose factors originate from the frozen
analytic LiDAR fixture.

Camera factors originate from the separately manufactured
72-point metric-depth camera scene and SVD alignment.

No LiDAR factor is copied into the camera generator.
However, shared manufactured motion does not establish
independent physical sensing.

There is at most one relative-pose factor per edge.
The legacy backend cannot assign independent same-edge
camera and LiDAR factor weights.

## Audited invariants

- Four nonoverlapping IMU factors.
- Four accepted 15D optimizer windows.
- Three Schur marginalizations.
- No reused or unaccounted pose factors.
- No duplicate camera/LiDAR same-edge factors.
- Analytic factor source labels and IDs maintained.
- No real-factor admission or health inference.
- No calibration or measurement weighting changes.

## Numerical outputs

Each configuration reports:
- selected pose-factor counts and source ledger;
- window-objective cost sum;
- final estimated synthetic position;
- baseline-relative position difference;
- deterministic synthetic estimator state digest.

These values do not represent ATE, RPE, physically
calibrated uncertainty, independent ground-truth
accuracy or validated sensor recovery.

The frozen bias scenario is pair-local and is not
a physically calibrated sensor failure model.

## Data boundaries

No recorded M2DGR or Hilti measurements are read.
No recorded GT or held-out sequences are accessed.

The protected split remains 22 TRAIN /
7 VALIDATION_CALIBRATION / 7 CONFIRMATION_TEST.

All 11 M2DGR admission gates remain CLOSED.

## Future scientific work

More informative synthetic failure mechanisms and
multiple-seed/cross-condition analyses should follow.
Any claims of fault tolerance will require legitimate
reference evaluation, sufficiently challenging failures,
and justified factor information/health semantics.

Real factor execution and health-controlled weighting
remain prohibited until their respective evidence
and admission requirements are satisfied.
