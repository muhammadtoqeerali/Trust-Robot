# TRUST-ROBOT Phase Plan

This file records the current explicit project sequence. Phase numbering must not change silently.

| Phase | Objective | Exit evidence |
|---|---|---|
| 0 | Project/environment/inherited-code audit | Baseline audit and migration matrix |
| 1 | Dataset registry, synchronization, frames, reference-source rules, trajectory splits, anti-leakage | Frozen data protocol and passing validators |
| 2 | Fixed clean localization/state-estimation backbone | Reproducible clean 6-DoF baseline |
| 3 | Multimodal fault/degradation/attack taxonomy and corruption engine | Deterministic paired corruption framework |
| 4 | Per-modality diagnostics | Validated diagnostic feature extraction |
| 5 | Three-state modality-health model | Healthy/degraded/unusable classifier |
| 6 | Calibration | Frozen validation-only calibration |
| 7 | Auxiliary consistency | Cross-modal/temporal/kinematic consistency evidence |
| 8 | Factor conditioning | Health-aware factor weighting with bounded innovation conditioning |
| 9 | Suppression/recovery/status | Hysteretic modality availability and estimator status |
| 10 | Causal ablations and controlled faults | Same-backbone RQ1/RQ2 evidence |
| 11 | Cross-dataset evaluation | Generalization/stress evidence |
| 12 | Explicit attack evaluation | Threat-model-bounded RQ3 evidence |
| 13 | Resource evaluation | Latency/memory/throughput/power evidence |
| 14 | Guarded real-robot integration | Supervisory/closed-loop evidence |
| 15 | Final confirmation and publication package | Frozen reproducibility and evidence package |

Every phase follows:

objective -> audit -> protocol -> minimum implementation -> tests -> report -> decision gate

## Current M2DGR synchronization-verification ledger

The high-level table above is retained as original planning provenance. The
authoritative active implementation state is maintained in
`docs/TRUST_ROBOT_PROJECT_STATE.md`.

Within the current M2DGR synchronization-verification evidence gate, the
following checkpoints are complete:

- Phase 3A — sensor timing characterization and stream inventory
- Phase 3B — synchronization evidence and conservative clock semantics
- Phase 3C — camera-image ↔ D435i-IMU timing characterization
- Phase 3D — LiDAR ↔ HandsFree-IMU timing characterization
- Phase 3E — reference ↔ estimator temporal-association evidence

The Phase-3E checkpoint does not declare synchronization verified. It records
that the released evidence does not justify a single global reference timing
policy, fixed reference offset, interpolation policy, association tolerance,
or evaluation interval.

Later calibration/evaluation gates must preserve these unresolved timing
semantics unless new independent evidence is introduced.

This ledger is explicit documentation of the active evidence-gated work and
does not silently renumber the retained high-level historical plan.
