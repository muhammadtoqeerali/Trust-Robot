# R126-C — External-reference bypass boundary

This is a synthetic, bounded adversarial audit of the R126-B1
identity-aware shadow adapter using actual archived R122 classes.

The experiment deliberately retains an external reference to the
old R122 TerminalPath before a candidate pointer is published.

After publication, the retained facade is challenged with the
same local lease and owner token:

- Cancellation: the old ACTIVE facade can still cancel.
- Retirement: the old CANCELLED facade can still retire.

These are separate facade states for the same original synthetic
session identity. The shadow adapter does not guarantee a single
globally authoritative state.

Additional controls demonstrate that the adapter publication pointer
can be rebound by Python code holding its object, and that direct
private receipt mutation can corrupt a facade until detected by a
subsequent integrity check.

The deliberately mutated cases are disposable synthetic fixtures.
No previous R122, R125 or R126-B1 artifacts are changed.

This is a diagnostic of the limits of identity-aware copying,
NOT a verified repair or a concurrent transaction mechanism.

No real camera/LiDAR/IMU factor admission, M2DGR data, raw GT,
sealed confirmation_test, physical synchronization, calibrated
health model, independently scored ATE/RPE, crash durability,
authenticated receipts or robot safety capability is established.

All 11 physical/scientific admissibility gates remain CLOSED.
