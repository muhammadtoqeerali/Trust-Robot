# TRUST-ROBOT R135-A31-9 / A31-10 Implementation

## Objective

Resolve synthetic event-time inconsistencies and implement
fixed-seed comparisons of toy trust-aware estimation.

## A31-9 exact synthetic event axis

The validator checks that every synthetic observation
timestamp equals the starting anchor plus cumulative
synthetic propagation intervals.

Timestamp arithmetic uses exact integer nanoseconds.

The validation rejects altered timestamps, propagation
interval mismatches, nonmonotone sequences, mixed clock
domains, physical-source claims, and invalid availability.

No ROS recorder stamp is treated as a physical event time.

No camera exposure, IMU sampling event, LiDAR firing
instant or real cross-clock accuracy is inferred.

## A31-10 seeded toy ensemble

The evaluation uses a fixed synthetic constant-velocity
truth sequence and explicit Gaussian noise generation.

Declared seeds are used to produce reproducible trials.

An artificial outlier is injected at a fixed recovery step.

Four toy policies are compared:
- counterfactual all-candidate updates
- counterfactual NIS screening
- scheduled delivery screening
- combined synthetic screening

Five existing software replay scenario classifications
select deliberately invented six-step delivery masks.

The masks are not reconstructed physical capture events.

The results summarize descriptive toy position RMSE,
toy NEES and numbers of toy state updates.

A small fixed-seed ensemble does not establish statistical
calibration, physical accuracy or generalization.

## Scientific boundaries

- Real factor admission: DENIED.
- Historical M2DGR gates: 11 CLOSED.
- Independently qualified A23 receipts: 0 of 13.
- Physical BMI088 frame relationship: UNVERIFIED.
- Metric physical calibration: UNVERIFIED.
- Physical clock accuracy: UNVERIFIED.
- Independent six-DoF reference: UNVERIFIED.
- Physical localization accuracy: NOT ESTABLISHED.

M2DGR frozen split remains 22 training, 7 validation-
calibration, and 7 confirmation-test sequences.

The original ROS bag is not modified.

No physical estimator invocation, robot motion, new
sensor recording, or Git publication occurs in this phase.
