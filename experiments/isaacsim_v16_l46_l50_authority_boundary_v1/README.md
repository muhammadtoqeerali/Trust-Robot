# KIOS L46-L50 Trust-Boundary Checkpoint

Date: 2026-10-16
Parent: c2e013f549b87e8646a8e51095a3372df0d09581

Scope: offline synthetic software-engineering tests only.

L46: Two simulated software HMAC roles, 35 denied controls. Coherent fabrication could pass internal verification without real sensor provenance. Isolated registries could both accept one challenge.

L47: Eight concurrent single-host SQLite admissions produced one success and seven denied replays. Two isolated registries both admitted the same nonce. Twenty request mutations and eight ledger faults denied.

L48: Three local receipt chains verified; duplicate nonce quarantined. Twenty-four metadata mutations and ten database/receipt faults rejected.

L49: Eighteen simulated authority failures kept quarantine; twelve false promotions denied; three synthetic receipt-publication paths checked; ten journal faults denied.

L50: Six engineering evidence categories reviewed, sixteen unqualified requirements retained, thirty-two false-promotion controls rejected.

The archive includes 26 frozen SHA-pinned source/report files, five synthetic JSON request/receipt artifacts, one compact SQLite summary, README, manifest and verifier.

No raw SQLite databases, sensor recordings, simulator assets or ephemeral HMAC keys are committed.

The duplicated nonce is UNSAFE. Its quarantine is not proof of globally consistent nonce consumption.

No independent physical witness, hardware attestation, verified exposure synchronization, independently qualified 6DoF reference, real power-loss durability, qualified three-state sensor-health model, or authorized scientific localization pose factors.

No Isaac Sim launch or new sensor acquisitions occurred in L46-L50.

The original M2DGR split and physical-evidence gates remain unchanged.

Verification:

python3 -B experiments/isaacsim_v16_l46_l50_authority_boundary_v1/verify_checkpoint.py

Next: return to core scientific development. Begin with a read-only audit of fixed clean 6DoF estimator readiness and dataset timing, calibration, and independent reference requirements. Preserve KIOS/iot4care workstation separation.
