# KIOS L36-L40 acquisition-witness engineering checkpoint

All results are offline engineering evidence; no new sensor acquisitions.

- L36: 46 preflight/sealing negative controls denied; no live launch permission.
- L37: Nonexecuted L29-derived Isaac Sim candidate; hooks before SimulationApp and after L29 export; 12 static mutations rejected; guard remains fail-closed. Scene and candidate metadata are not staged for execution.
- L38: SQLite single-host persistent nonce consumption across separate process invocations; repeated admission denied; 20 adversarial mutations rejected.
- L39: 20 simulated crash-window scenarios: 1 verified sealed, 2 requiring review, 17 quarantined. No actual power failure performed.
- L40: Committed receipt-byte outbox; 2 publication windows recovered and 7 inconsistencies denied. No power-loss or external attestation tests.

Original binary SQLite databases, fault-copy databases, raw camera/LiDAR/IMU recordings, and simulator assets are deliberately excluded. Archived source programs preserve KIOS-specific paths; treat them as evidence snapshots, not portable execution instructions. Public nonces are not credentials or trusted signatures.

No independent source authenticity, physical exposure-time synchronization, hardware attestation, independent 6DoF GT, scientific ATE/RPE, calibrated sensor-health labels, power-loss durability, or multi-host replay protection is established. Pose factors and health labels stay zero. Physical M2DGR research admission remains closed.

Verify from repo root:

`python3 -B experiments/isaacsim_v16_l36_l40_acquisition_witness_v1/verify_checkpoint.py`

Next L41: acquisition-time integration readiness gaps and targeted offline work before any specifically authorized GPU capture.
