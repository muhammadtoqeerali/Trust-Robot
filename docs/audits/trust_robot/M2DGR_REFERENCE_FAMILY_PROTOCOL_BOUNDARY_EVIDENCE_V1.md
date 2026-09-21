# M2DGR Reference-Family Protocol Boundary Evidence V1

## Status

`blocked_pending_physical_evidence`

Permanent evidence:

`manifests/m2dgr_reference_family_protocol_boundary_evidence_v1.json`

Content SHA256:

`87d48c97aeea22cbcba09bda0dfd1e577c0eef9084435cdd44dfc66146b1ec7c`

File SHA256:

`7d4cc9e1f7433ddd6b88b391687ca14a245ebf80877c4f4290fc3192ab7494cd`

This additive checkpoint mechanically combines already frozen structural,
physical-semantics, calibration, synchronization, split, and protocol evidence.

It does not inspect new raw confirmation-test data and does not run trajectory
metrics.

## Mechanical reference-family inventory

The frozen 36-trajectory corpus contains:

- RTK/INS: 16 trajectories;
- Leica: 11 trajectories;
- mocap: 9 trajectories.

The frozen prospective split distributes these as:

- RTK/INS: train 10, validation/calibration 3, confirmation-test 3;
- Leica: train 7, validation/calibration 2, confirmation-test 2;
- mocap: train 5, validation/calibration 2, confirmation-test 2.

These counts are metadata inventory only. Confirmation-test trajectories remain
closed to outcome-based protocol selection.

## Structural metric dimensions

RTK/INS:

- translation structurally present: TRUE;
- rotation structurally present: TRUE;
- audited translation invalid samples: 0;
- audited rotation invalid samples: 0.

Leica:

- translation structurally present: TRUE;
- rotation structurally present: FALSE;
- released zero quaternion columns are not treated as physical rotation.

Mocap:

- translation structurally present: TRUE;
- rotation structurally present: TRUE;
- audited translation invalid samples: 0;
- audited invalid quaternion samples: `1274`;
- mocap trajectories containing invalid quaternion samples:
  `9` of 9.

Structural availability is not treated as physical evaluation readiness.

A zero audited invalid count is not treated as proof of continuous-time
reference coverage.

## Common frozen physical/protocol boundary

Across the current physical-evaluation objective:

- all frozen reference frame IDs known: FALSE;
- continuous reference coverage verified: FALSE;
- reference frame semantics verified: FALSE;
- reference-frame transform verified: FALSE;
- temporal association method: `unselected`;
- association tolerance: `null`;
- fixed reference-to-estimator time offset: `null`;
- interpolation method: `unselected`;
- evaluation interval: `unselected`;
- alignment mode: `unselected`;
- dataset calibration independently verified: FALSE;
- synchronization independently verified: FALSE;
- metric computation authorized: FALSE;
- trajectory scoring authorized: FALSE;
- estimator scoring authorized: FALSE;
- evaluation ready: FALSE.

## RTK/INS boundary

RTK/INS has structurally available translation and rotation.

It remains blocked for physical scoring because the frozen evidence does not
verify:

- the exact released Xsens physical measurement origin;
- runtime GNSS lever-arm configuration;
- applicability of published Xsens/GNSS candidate transforms to released GT;
- reference timestamp physical-event semantics;
- reference timestamp export/timebase semantics;
- reference-to-estimator temporal association;
- evaluation interval;
- alignment policy.

Therefore:

- RTK/INS translation scoring admissible now: FALSE;
- RTK/INS rotation scoring admissible now: FALSE.

## Leica boundary

Leica is author-supported as 3D prism position only.

Rotation is therefore structurally unsupported.

Translation remains blocked because the frozen evidence does not verify:

- the exact released prism reference point;
- reflector model / prism constant / mount configuration;
- applicability of the published Leica-to-LiDAR candidate transform;
- reference timestamp physical-event semantics;
- reference timestamp export/timebase semantics;
- reference-to-estimator temporal association;
- evaluation interval;
- alignment policy.

Therefore:

- Leica translation-only scoring admissible now: FALSE;
- Leica rotation scoring admissible now: FALSE.

## Mocap boundary

Mocap structurally supplies translation and rotation.

Translation remains blocked by unresolved:

- tracked-body origin;
- mocap-to-estimator/LiDAR physical relation;
- reference timestamp physical-event semantics;
- reference timestamp export/timebase semantics;
- reference-to-estimator temporal association;
- evaluation interval;
- alignment policy.

Rotation has those same blockers and also contains structurally invalid samples
on every mocap trajectory.

No scientifically reproducible filter algorithm, threshold, window, or
prospective exclusion rule has been authorized.

Therefore:

- mocap translation-only scoring admissible now: FALSE;
- mocap rotation scoring admissible now: FALSE.

## Allowed non-scoring work

The frozen Protocol V2 permits definition-level work without executing the
evaluation.

Currently admissible work includes:

- structural reference inventory;
- provenance analysis;
- metric-family schema definition;
- dimension-gating schema definition;
- documentation of unresolved physical requirements.

These activities do not produce estimator-performance claims.

## Not authorized

This checkpoint does not authorize:

- exact, nearest-neighbor, or interpolated trajectory association execution;
- an association tolerance;
- a fixed timing offset;
- an evaluation interval;
- SE(3), Sim(3), or no-alignment selection;
- promotion of candidate calibration transforms to verified applicability;
- a mocap filtering/exclusion rule;
- ATE computation;
- RPE computation;
- trajectory scoring;
- estimator scoring.

## Protocol conclusion

Under the current frozen physical-evaluation objective:

- any reference-family translation scoring admissible now: FALSE;
- any reference-family rotation scoring admissible now: FALSE;
- any ATE/RPE scoring admissible now: FALSE;
- RTK/INS restricted scoring admissible now: FALSE;
- Leica translation-only restricted scoring admissible now: FALSE;
- mocap translation-only restricted scoring admissible now: FALSE;
- mocap rotation restricted scoring admissible now: FALSE.

Protocol V2 remains byte-identical.

This checkpoint does not select Protocol V3.

A differently scoped reproduction of an author's evaluation procedure would
require a separate prospectively declared protocol and scientific objective.
Confirmation-test outcomes may not be used to choose that future protocol.

Future genuinely new physical evidence could change this boundary.

## Frozen-evidence handling

No frozen predecessor artifact is modified.

No confirmation-test raw trajectory is inspected.

No ATE or RPE value is produced.
