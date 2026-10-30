# TRUST-ROBOT R135-A27-6 / A30-2 Implementation Audit

## Engineering objective

Advance beyond sensor connectivity and report inspection
toward usable frame-transform software and actionable
independent measurement acquisition contracts.

## A27-6 nominal transform algebra

Implements a deterministic URDF frame graph with
T_target_source coordinate transformation semantics.

Rotation follows Rz(yaw) Ry(pitch) Rx(roll).
Fixed transforms can be composed and inverted.

Cycles, disconnected links, duplicate parents,
nonfinite coordinates and malformed joints are rejected.

Dynamic-joint relationships cannot be treated as fixed.

Nominal URDF transforms are engineering geometry,
not independently verified metric sensor calibration.

The physical BMI088 frame identity remains unresolved.

## A30-2 independent acquisition work orders

The implementation generates thirteen work orders
directly from the frozen R135-A23 request inventory.

Each contains the required independent physical fact,
witness requirement, insufficient surrogate,
proposed acquisition method and expected artifact.

Stages remain:

A: source provenance, two requests.
B: calibration and physical timing, six requests.
C: independent pose reference, three requests.
D: evaluation readiness, two requests.

No numerical timing threshold, calibration value,
transform uncertainty or pose ground truth is fabricated.

No independent evidence receipt is accepted by
the software in this phase.

## Dataset and scientific boundaries

M2DGR split remains:
22 train, 7 validation-calibration, 7 confirmation-test.

All eleven historical M2DGR admission gates stay closed.

A different Nova Carter capture cannot retroactively
qualify the historical dataset.

Independent qualifying receipts: zero.
Real sensor factor admission: denied.
Physical clock accuracy: unverified.
Metric sensor calibration: unverified.
Independent six-DoF reference: unverified.
Physical localization accuracy: not established.

No robot motion, new sensor recording, factor
construction or physical pose scoring is performed.

## Next scientific action

Use the independently reviewed work orders to
establish actual sensor frame identity, time-event
definitions, calibration uncertainty and independent
reference geometry before revisiting physical admission.
